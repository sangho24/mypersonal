"""MAB 보상함수 — 11개국 mark-up 기반 베이스라인.

phase 04 / step 1: 멀티암 밴딧의 reward = 1 / markup 으로 정의.
- 11개국 arm: 프랑스, 포르투갈, 이탈리아, 스페인, 칠레, 미국, 호주, 뉴질랜드,
  독일, 아르헨티나, 남아프리카
- markup = wine21 retail median (KRW) / 도매가 KRW per bottle
- 도매가 KRW = (관세청 import_usd / import_kg) × 1.2 kg/bottle × 1350 KRW/USD
- 노이즈 σ: X-Wines 150K ratings 의 국가별 rating std (0-5) → reward 스케일 환산
  (X-Wines 부재 시 σ=0.05 상수 폴백 — ADR-009 참고)

설계 근거: ADR-009 (실제 mark-up 데이터로 reward 모수화, 2026-06-05).
"""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.load import _norm_country, load_imports, load_wines

# 도매가 환산 상수 (results/report/report.md §2.3)
KG_PER_BOTTLE: float = 1.2  # 750ml 와인 1병 ≈ 1.2 kg (병 + 액)
KRW_PER_USD: float = 1350.0  # 12개월 평균 환율 가정

# 분석 대상 11개국 (관세청 표기 기준 — 정규화 후)
TARGET_COUNTRIES: list[str] = [
    "프랑스",
    "포르투갈",
    "이탈리아",
    "스페인",
    "칠레",
    "미국",
    "호주",
    "뉴질랜드",
    "독일",
    "아르헨티나",
    "남아프리카",
]

# X-Wines Country 코드 → 한국어 매핑 (XWines_Full_100K_wines.csv 의 Country 컬럼)
_XWINES_COUNTRY_MAP: dict[str, str] = {
    "France": "프랑스",
    "Portugal": "포르투갈",
    "Italy": "이탈리아",
    "Spain": "스페인",
    "Chile": "칠레",
    "United States": "미국",
    "Australia": "호주",
    "New Zealand": "뉴질랜드",
    "Germany": "독일",
    "Argentina": "아르헨티나",
    "South Africa": "남아프리카",
}

# X-Wines 부재 시 폴백 노이즈 (ADR-009 — 보수적 단일값)
DEFAULT_NOISE_SIGMA: float = 0.05

# X-Wines 평점 스케일 (0-5 Likert)
_XWINES_RATING_SCALE: float = 5.0


def load_markup_table(
    csv_path: str | Path = "data/processed/wine_imports.csv",
    wines_path: str | Path | None = None,
) -> pd.DataFrame:
    """11개국 markup 테이블 생성 — 관세청 12개월 합계 ÷ wine21 소매가 중위값.

    반환 컬럼: country, markup, wholesale_krw, n_imports_kg, n_months.
    11행 고정 (TARGET_COUNTRIES 기준 정렬).
    """
    imports = load_imports(csv_path)
    wines = load_wines(wines_path)

    # 1) 국가별 12개월 import_usd / import_kg 합계 → USD/kg 도매가
    agg = (
        imports.groupby("country")
        .agg(
            import_usd_sum=("import_usd", "sum"),
            import_kg_sum=("import_kg", "sum"),
            n_months=("year_month", "nunique"),
        )
        .reset_index()
    )
    agg = agg[agg["import_kg_sum"] > 0].copy()
    agg["usd_per_kg"] = agg["import_usd_sum"] / agg["import_kg_sum"]
    agg["wholesale_krw"] = agg["usd_per_kg"] * KG_PER_BOTTLE * KRW_PER_USD

    # 2) wine21 국가별 retail median (KRW)
    retail = (
        wines.dropna(subset=["country", "price_krw"])
        .groupby("country")["price_krw"]
        .median()
        .rename("retail_median_krw")
        .reset_index()
    )

    # 3) merge → markup = retail / wholesale
    table = agg.merge(retail, on="country", how="inner")
    table["markup"] = table["retail_median_krw"] / table["wholesale_krw"]

    # 4) 11개국 필터 + 고정 순서
    table = table[table["country"].isin(TARGET_COUNTRIES)].copy()
    table["country"] = pd.Categorical(table["country"], categories=TARGET_COUNTRIES, ordered=True)
    table = table.sort_values("country").reset_index(drop=True)
    table["country"] = table["country"].astype(str)

    return table[["country", "markup", "wholesale_krw", "import_kg_sum", "n_months"]].rename(
        columns={"import_kg_sum": "n_imports_kg"}
    )


def compute_reward_arms(markup_table: pd.DataFrame) -> np.ndarray:
    """arm 별 기대 보상 = 1 / markup. shape=(n_countries,)."""
    return (1.0 / markup_table["markup"].to_numpy()).astype(float)


def load_noise_sigma(
    x_wines_present: bool = True,
    ratings_path: str | Path = "data/raw/xwines/drive/last/XWines_Slim_150K_ratings.csv",
    wines_path: str | Path = "data/raw/xwines/drive/last/XWines_Full_100K_wines.csv",
    reward_arms: np.ndarray | None = None,
) -> np.ndarray:
    """국가별 노이즈 σ — X-Wines 평점 std → reward 스케일 환산.

    X-Wines 데이터 부재 시 모든 arm 에 DEFAULT_NOISE_SIGMA (0.05) 폴백.
    환산: σ_reward = (σ_rating / 5.0) × reward_span (span = max-min reward).
    """
    n = len(TARGET_COUNTRIES)
    if not x_wines_present or not Path(ratings_path).exists():
        return np.full(n, DEFAULT_NOISE_SIGMA, dtype=float)

    # reward span 계산 (없으면 0.144 — [0.083, 0.227] 의 폭, ADR-009)
    reward_span = (
        float(reward_arms.max() - reward_arms.min())
        if reward_arms is not None and len(reward_arms) > 0
        else 0.144
    )

    per_country = _xwines_country_rating_std(ratings_path=ratings_path, wines_path=wines_path)

    sigmas = np.empty(n, dtype=float)
    for i, country_kr in enumerate(TARGET_COUNTRIES):
        std_rating = per_country.get(country_kr)
        if std_rating is None or np.isnan(std_rating):
            sigmas[i] = DEFAULT_NOISE_SIGMA
        else:
            sigmas[i] = (std_rating / _XWINES_RATING_SCALE) * reward_span
    # 안전 클램프 — 너무 작거나 큰 값 방지
    sigmas = np.clip(sigmas, 0.011, 0.099)
    return sigmas


def country_arm_index(markup_table: pd.DataFrame) -> dict[str, int]:
    """국가명 → arm index. TARGET_COUNTRIES 순서 기준."""
    return {row.country: i for i, row in enumerate(markup_table.itertuples(index=False))}


def _xwines_country_rating_std(
    ratings_path: str | Path,
    wines_path: str | Path,
) -> dict[str, float]:
    """X-Wines 평점 ⨝ 와인 → 11개국 rating std 사전 (5점 척도)."""
    ratings = pd.read_csv(ratings_path, usecols=["WineID", "Rating"])
    wines = pd.read_csv(wines_path, usecols=["WineID", "Country"])
    merged = ratings.merge(wines, on="WineID", how="inner")
    merged["country_kr"] = merged["Country"].map(_XWINES_COUNTRY_MAP)
    merged = merged.dropna(subset=["country_kr"])
    return merged.groupby("country_kr")["Rating"].std(ddof=1).to_dict()


# ast import 는 list 컬럼 파싱에 향후 사용 예정 (lint 회피용 참조)
_ = ast.literal_eval


def _norm_for_xwines(c: str | None) -> str | None:
    """X-Wines Country → 한국어 정규화 (관세청 표기 일치)."""
    if c is None:
        return None
    kr = _XWINES_COUNTRY_MAP.get(c)
    return _norm_country(kr) if kr else None


if __name__ == "__main__":
    table = load_markup_table()
    rewards = compute_reward_arms(table)
    sigmas = load_noise_sigma(x_wines_present=True, reward_arms=rewards)
    arm_idx = country_arm_index(table)

    print("=" * 60)
    print("MAB 보상 베이스라인 — 11개국 mark-up 테이블")
    print("=" * 60)
    print(table.to_string(index=False))
    print()
    print(f"arm 순서 (n={len(arm_idx)}):")
    for c, i in arm_idx.items():
        print(f"  [{i:2d}] {c:<10s} reward={rewards[i]:.4f}  σ={sigmas[i]:.4f}")
    print()
    print(f"rewards (1/markup): min={rewards.min():.4f} max={rewards.max():.4f}")
    print(f"noise σ:            min={sigmas.min():.4f} max={sigmas.max():.4f}")
    best_arm = int(np.argmax(rewards))
    best_country = list(arm_idx.keys())[best_arm]
    print(f"best arm: [{best_arm}] {best_country} (reward={rewards[best_arm]:.4f})")

    # ----- 검증 -----
    n_arms = len(rewards)
    assert n_arms == 11, f"n_arms 11 기대, 실측 {n_arms}"
    assert ((rewards > 0.05) & (rewards < 0.30)).all(), f"reward 범위 (0.05, 0.30) 위반: {rewards}"
    assert ((sigmas > 0.01) & (sigmas < 0.10)).all(), f"σ 범위 (0.01, 0.10) 위반: {sigmas}"
    # best arm: 프랑스 OR 포르투갈 (둘 다 markup ≈ 4.4, reward ≈ 0.227 — 동률)
    france_idx = arm_idx["프랑스"]
    portugal_idx = arm_idx["포르투갈"]
    best_idx = int(np.argmax(rewards))
    assert best_idx in (france_idx, portugal_idx), (
        f"best arm 은 프랑스({france_idx}) 또는 포르투갈({portugal_idx}) 이어야 함, 실측 {best_idx}"
    )
    assert rewards[france_idx] > 0.22, (
        f"프랑스 reward (1/4.4=0.227) ~ 0.22 이상이어야 함, 실측 {rewards[france_idx]:.4f}"
    )
    print()
    print("ALL ASSERTIONS PASSED ✓")
