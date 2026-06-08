"""분석용 데이터 로딩 헬퍼.

raw → pandas DataFrame 으로 변환 + 국가명 정규화 (관세청 ↔ wine21 표기 불일치 처리).
노트북은 이 모듈만 호출하면 분석 시작 가능.
"""

from __future__ import annotations

import glob
import json
import re
from pathlib import Path

import pandas as pd

# 관세청·wine21 ↔ 표준 표기 정규화 (조인용)
COUNTRY_NORMALIZE: dict[str, str] = {
    "포루투갈": "포르투갈",          # 관세청 오타
    "남아프리카공화국": "남아프리카",  # 관세청 표기
    "남아프리카 공화국": "남아프리카",  # 변형
}

# 신대륙·구대륙 분류 (분석용 파생 컬럼)
NEW_WORLD = {"미국", "칠레", "호주", "뉴질랜드", "아르헨티나", "남아프리카"}


def _norm_country(c: str | None) -> str | None:
    if not c:
        return None
    return COUNTRY_NORMALIZE.get(c, c)


def load_wines(records_path: str | Path | None = None) -> pd.DataFrame:
    """wine21 records.jsonl → DataFrame. 최신 디렉터리 자동 선택."""
    if records_path is None:
        candidates = sorted(glob.glob("data/raw/wine21/2026*/records.jsonl"))
        if not candidates:
            raise FileNotFoundError("data/raw/wine21/ 에 records.jsonl 없음")
        records_path = candidates[-1]
    with open(records_path, encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]
    df = pd.DataFrame(records)

    # 파생 컬럼
    df["country"] = (
        df["region"]
        .fillna("")
        .str.extract(r"^([^()]+)\(", expand=False)
        .str.strip()
        .replace("", None)
        .map(_norm_country)
    )
    df["world"] = df["country"].apply(
        lambda c: "신대륙" if c in NEW_WORLD else ("구대륙" if c else None)
    )
    df["wine_type"] = df["varietal"].apply(_infer_wine_type)
    df["price_tier"] = pd.cut(
        df["price_krw"],
        bins=[0, 30000, 80000, 200000, float("inf")],
        labels=["저가", "중가", "고가", "프리미엄"],
    )
    return df


def _infer_wine_type(varietal: str | None) -> str | None:
    """varietal 텍스트에서 와인 타입(레드/화이트/스파클링/로제) 추정."""
    if not varietal:
        return None
    v = varietal.lower()
    # 스파클링 키워드
    if any(k in v for k in ["sparkling", "샴페인", "프로세코", "카바", "스파클"]):
        return "스파클링"
    # 로제
    if "rose" in v or "로제" in v or "rosé" in v:
        return "로제"
    # 화이트 품종
    white_grapes = [
        "chardonnay",
        "sauvignon blanc",
        "riesling",
        "pinot grigio",
        "pinot gris",
        "gewurztraminer",
        "viognier",
        "muscat",
        "moscato",
        "semillon",
        "샤르도네",
        "소비뇽 블랑",
        "리슬링",
        "피노 그리지오",
        "모스카토",
        "비오니에",
    ]
    if any(k in v for k in white_grapes):
        return "화이트"
    # 레드 품종 (디폴트)
    red_grapes = [
        "cabernet",
        "merlot",
        "pinot noir",
        "syrah",
        "shiraz",
        "malbec",
        "tempranillo",
        "sangiovese",
        "nebbiolo",
        "grenache",
        "zinfandel",
        "카베르네",
        "메를로",
        "피노 누아",
        "시라",
        "쉬라즈",
        "말벡",
        "템프라니요",
        "산지오베제",
        "네비올로",
    ]
    if any(k in v for k in red_grapes):
        return "레드"
    return None


def load_imports(path: str | Path = "data/processed/wine_imports.csv") -> pd.DataFrame:
    """관세청 와인 수입 통계 → DataFrame. 국가명 정규화 적용."""
    df = pd.read_csv(path)
    df["country"] = df["country"].map(_norm_country)
    # year_month "2024.10" 같은 월별 행만 유지 (연간 총계 행/결측 제외)
    df["year_month"] = df["year_month"].astype(str)
    monthly = df["year_month"].str.match(r"^\d{4}\.\d{1,2}$")
    df = df[monthly].copy()
    # "2024.1" → "2024.01" 정규화 (zero-pad 월)
    df["year_month"] = df["year_month"].str.replace(
        r"^(\d{4})\.(\d)$", r"\1.0\2", regex=True
    )
    df["year_month_dt"] = pd.to_datetime(df["year_month"], format="%Y.%m")
    return df


def country_summary(wines: pd.DataFrame, imports: pd.DataFrame) -> pd.DataFrame:
    """wine21 카탈로그 분포 × 관세청 수입액 비교 테이블."""
    cat = (
        wines.groupby("country", dropna=True)
        .agg(catalog_count=("name", "count"), catalog_avg_price=("price_krw", "mean"))
        .reset_index()
    )
    imp = (
        imports.groupby("country")
        .agg(import_usd_12m=("import_usd", "sum"), import_kg_12m=("import_kg", "sum"))
        .reset_index()
    )
    merged = cat.merge(imp, on="country", how="outer")
    merged["catalog_share_pct"] = (
        merged["catalog_count"] / merged["catalog_count"].sum() * 100
    ).round(1)
    merged["import_share_pct"] = (
        merged["import_usd_12m"] / merged["import_usd_12m"].sum() * 100
    ).round(1)
    return merged.sort_values("import_usd_12m", ascending=False, na_position="last")
