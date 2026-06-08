"""Daily personal-data loaders. Cache-first, XML-fallback documented.

Cached parquet 위치: data/processed/personal/
- personal_daily.parquet         (7 col: steps, walking_speed+n, dist_walk_m, flights, active_energy_kcal)
- personal_daily_hmm.parquet     (9 col: steps, distance_km, gait 4, audio_max_dB, audio_listen_min)
- personal_daily_merged.parquet  (13 col: + maps distinct_places/visit_count/walking_dist_m/walking_frac)

캐시 부재 시 src/scripts 의 XML iterparse loader 로 재생성 (216MB XML 스트리밍, ~2분).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parents[2] / "data" / "processed" / "personal"


def load_daily_merged() -> pd.DataFrame:
    """가장 풍부한 일별 테이블 (gait + audio + maps). 결측은 NaN 유지."""
    return pd.read_parquet(DATA_DIR / "personal_daily_merged.parquet")


def load_daily_9ch() -> pd.DataFrame:
    """K-means 입력용 9채널 일별 테이블 — personal_daily(flights/active) + hmm(gait/audio) merge."""
    a = pd.read_parquet(DATA_DIR / "personal_daily.parquet")
    b = pd.read_parquet(DATA_DIR / "personal_daily_hmm.parquet")
    merged = b.merge(
        a[["date", "flights", "active_energy_kcal"]],
        on="date",
        how="left",
    )
    cols = [
        "date",
        "steps",
        "distance_km",
        "active_energy_kcal",
        "flights",
        "walking_speed",
        "step_length",
        "asymmetry",
        "double_support",
        "audio_max_dB",
    ]
    return merged[cols].copy()


def zscore_within_baseline(
    df: pd.DataFrame, channel: str, baseline_start, baseline_end
) -> pd.Series:
    """채널의 baseline window mean/std 로 전체 시리즈를 z-score 변환."""
    mask = (df["date"] >= pd.Timestamp(baseline_start)) & (
        df["date"] <= pd.Timestamp(baseline_end)
    )
    base = df.loc[mask, channel].dropna()
    if len(base) < 3:
        return pd.Series(np.nan, index=df.index)
    mu = float(base.mean())
    sigma = float(base.std(ddof=1))
    if sigma == 0:
        return pd.Series(np.nan, index=df.index)
    return (df[channel] - mu) / sigma
