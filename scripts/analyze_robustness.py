"""6개월 split robustness 테스트 — wine21 mark-up 랭킹의 시간적 안정성.

배경 (ADR-009 / report §3.4):
12개월 (2024.05 ~ 2025.04) 관세청 수입통계로 도매원가 → mark-up 11개국을 추정한 결과는
Pearson r = -0.752 (p = 0.0076). 이 단일 결과가 "특정 6개월 anomaly가 만든 우연" 인지,
아니면 시기를 잘라도 같은 랭킹이 보존되는 *시스템적* 신호인지 확인한다.

설계:
- H1 = 2024-05 ~ 2024-10 (6개월)
- H2 = 2024-11 ~ 2025-04 (6개월)
- 각 반기에 대해 src/mab/reward.py 의 도매원가 환산식을 동일하게 적용:
    wholesale_krw = (Σ import_usd / Σ import_kg) × KG_PER_BOTTLE (1.2) × KRW_PER_USD (1350)
    markup = wine21 retail median KRW / wholesale_krw
- 11개국 (TARGET_COUNTRIES) 에 대해 markup_H1 / markup_H2 산출 → 순위 상관 검정

산출:
- results/data/robustness.json: H1·H2 markup dict, statistics (Pearson r·p / Spearman ρ·p),
  top-3 overlap (set intersection).
- stdout: pretty table.

Run:
    uv run python scripts/analyze_robustness.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from scipy.stats import pearsonr, spearmanr

# repo root 를 sys.path 에 추가 — `uv run python scripts/analyze_robustness.py` 직접 실행 지원
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.data.load import load_imports, load_wines  # noqa: E402
from src.mab.reward import (  # noqa: E402
    KG_PER_BOTTLE,
    KRW_PER_USD,
    TARGET_COUNTRIES,
)

# 반기 경계 — H1 = 6 months, H2 = 6 months (12 months total = 2024.05 ~ 2025.04)
H1_MONTHS: list[str] = [
    "2024.05",
    "2024.06",
    "2024.07",
    "2024.08",
    "2024.09",
    "2024.10",
]
H2_MONTHS: list[str] = [
    "2024.11",
    "2024.12",
    "2025.01",
    "2025.02",
    "2025.03",
    "2025.04",
]

OUTPUT_PATH = Path("results/data/robustness.json")


def _half_markup_table(
    imports_half: pd.DataFrame,
    retail_median: pd.DataFrame,
) -> pd.DataFrame:
    """반기 imports 부분집합 → 11개국 markup 테이블.

    src/mab/reward.py 의 load_markup_table 환산식과 동일하게 유지 (단, 기간만 6개월).
    """
    agg = (
        imports_half.groupby("country")
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

    table = agg.merge(retail_median, on="country", how="inner")
    table["markup"] = table["retail_median_krw"] / table["wholesale_krw"]

    # 11개국 필터 + 고정 순서
    table = table[table["country"].isin(TARGET_COUNTRIES)].copy()
    table["country"] = pd.Categorical(
        table["country"], categories=TARGET_COUNTRIES, ordered=True
    )
    table = table.sort_values("country").reset_index(drop=True)
    table["country"] = table["country"].astype(str)
    return table[
        ["country", "markup", "wholesale_krw", "retail_median_krw", "n_months"]
    ]


def _print_pretty(
    h1: pd.DataFrame,
    h2: pd.DataFrame,
    stats: dict[str, Any],
) -> None:
    """반기별 markup + 통계를 콘솔에 표 형태로 출력."""
    merged = (
        h1[["country", "markup"]]
        .rename(columns={"markup": "markup_H1"})
        .merge(
            h2[["country", "markup"]].rename(columns={"markup": "markup_H2"}),
            on="country",
            how="outer",
        )
    )
    merged["country"] = pd.Categorical(
        merged["country"], categories=TARGET_COUNTRIES, ordered=True
    )
    merged = merged.sort_values("markup_H1", ascending=False).reset_index(drop=True)
    merged["rank_H1"] = merged["markup_H1"].rank(ascending=False, method="min").astype("Int64")
    merged["rank_H2"] = merged["markup_H2"].rank(ascending=False, method="min").astype("Int64")
    merged["Δ_rank"] = (merged["rank_H1"] - merged["rank_H2"]).astype("Int64")

    print("=" * 72)
    print("6-month split robustness — wine21 mark-up ranking")
    print("=" * 72)
    print(
        f"H1 = {H1_MONTHS[0]} ~ {H1_MONTHS[-1]}  |  "
        f"H2 = {H2_MONTHS[0]} ~ {H2_MONTHS[-1]}"
    )
    print(f"n countries = {len(merged)}  |  formula: src/mab/reward.load_markup_table")
    print("-" * 72)
    print(
        f"{'country':<12s} {'markup_H1':>10s} {'markup_H2':>10s} "
        f"{'rank_H1':>8s} {'rank_H2':>8s} {'Δ_rank':>7s}"
    )
    for _, row in merged.iterrows():
        m1 = f"{row.markup_H1:.2f}" if pd.notna(row.markup_H1) else "  n/a "
        m2 = f"{row.markup_H2:.2f}" if pd.notna(row.markup_H2) else "  n/a "
        r1 = str(row.rank_H1) if pd.notna(row.rank_H1) else " - "
        r2 = str(row.rank_H2) if pd.notna(row.rank_H2) else " - "
        dr = str(row["Δ_rank"]) if pd.notna(row["Δ_rank"]) else " - "
        print(f"{row.country:<12s} {m1:>10s} {m2:>10s} {r1:>8s} {r2:>8s} {dr:>7s}")
    print("-" * 72)
    print(f"Pearson  r = {stats['pearson_r']:+.4f}   p = {stats['pearson_p']:.4f}")
    print(f"Spearman ρ = {stats['spearman_rho']:+.4f}   p = {stats['spearman_p']:.4f}")
    print(f"Top-3 H1: {stats['top3_H1']}")
    print(f"Top-3 H2: {stats['top3_H2']}")
    print(
        f"Top-3 overlap: {len(stats['top3_overlap'])}/3  "
        f"→ {stats['top3_overlap']}"
    )
    print("=" * 72)


def analyze() -> dict[str, Any]:
    """H1/H2 markup 산출 + 순위 상관 검정 + JSON 저장."""
    imports = load_imports()
    wines = load_wines()

    # wine21 retail median 은 한 번만 계산 (시점 비의존 — 카탈로그 스냅샷 가정)
    retail_median = (
        wines.dropna(subset=["country", "price_krw"])
        .groupby("country")["price_krw"]
        .median()
        .rename("retail_median_krw")
        .reset_index()
    )

    imp_h1 = imports[imports["year_month"].isin(H1_MONTHS)].copy()
    imp_h2 = imports[imports["year_month"].isin(H2_MONTHS)].copy()

    tab_h1 = _half_markup_table(imp_h1, retail_median)
    tab_h2 = _half_markup_table(imp_h2, retail_median)

    # 두 반기 모두 markup 이 존재하는 국가만 검정 대상
    joined = tab_h1[["country", "markup"]].rename(columns={"markup": "markup_H1"}).merge(
        tab_h2[["country", "markup"]].rename(columns={"markup": "markup_H2"}),
        on="country",
        how="inner",
    )
    x = joined["markup_H1"].to_numpy()
    y = joined["markup_H2"].to_numpy()

    pear_r, pear_p = pearsonr(x, y)
    sp_rho, sp_p = spearmanr(x, y)

    top3_h1 = joined.sort_values("markup_H1", ascending=False).head(3)["country"].tolist()
    top3_h2 = joined.sort_values("markup_H2", ascending=False).head(3)["country"].tolist()
    overlap = sorted(set(top3_h1) & set(top3_h2))

    stats: dict[str, Any] = {
        "pearson_r": float(pear_r),
        "pearson_p": float(pear_p),
        "spearman_rho": float(sp_rho),
        "spearman_p": float(sp_p),
        "n_countries": int(len(joined)),
        "top3_H1": top3_h1,
        "top3_H2": top3_h2,
        "top3_overlap": overlap,
        "top3_overlap_count": len(overlap),
    }

    payload: dict[str, Any] = {
        "design": {
            "H1_months": H1_MONTHS,
            "H2_months": H2_MONTHS,
            "kg_per_bottle": KG_PER_BOTTLE,
            "krw_per_usd": KRW_PER_USD,
            "target_countries": TARGET_COUNTRIES,
            "retail_source": "wine21 records.jsonl median(price_krw) per country",
            "imports_source": "data/processed/wine_imports.csv (관세청)",
            "formula": (
                "wholesale_krw = (Σ import_usd / Σ import_kg) × 1.2 × 1350; "
                "markup = retail_median_krw / wholesale_krw"
            ),
        },
        "markup_H1": {
            row.country: float(row.markup) for _, row in tab_h1.iterrows()
        },
        "markup_H2": {
            row.country: float(row.markup) for _, row in tab_h2.iterrows()
        },
        "wholesale_krw_H1": {
            row.country: float(row.wholesale_krw) for _, row in tab_h1.iterrows()
        },
        "wholesale_krw_H2": {
            row.country: float(row.wholesale_krw) for _, row in tab_h2.iterrows()
        },
        "statistics": stats,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    _print_pretty(tab_h1, tab_h2, stats)
    print(f"\nsaved → {OUTPUT_PATH}")
    return payload


if __name__ == "__main__":
    analyze()
