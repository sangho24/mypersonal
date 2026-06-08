"""발견 2 — "Paris 라는 한 사건이 세 채널에 다른 위상으로 새겨졌다" 산출 모듈.

채널 1 (활동량, Paris 중): steps / distance_km / flights — Paris vs 직전 Seoul 비교
채널 2 (청취량, Paris 중 monotonic): 일평균 headphone 청취시간 + 새벽 점유율
채널 3 (gait remodel + 능동 탐색, 귀국 후): Seoul_rec vs pre-MIL baseline gait 4채널 + Maps 'Searched' 폭발 timing

결과 JSON 위치: results/personal/finding2.json
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from src.personal.anchors import (
    PARIS_END,
    PARIS_START,
    PRE_MIL_BASELINE,
    SEOUL_REC_START,
)
from src.personal.data import load_daily_9ch, load_daily_merged
from src.personal.finding1_label_vs_data import welch_t_and_d

MAPS_JSON = Path("/Users/sangho/Downloads/location-history.json")
OUT_JSON = Path(__file__).parents[2] / "results" / "personal" / "finding2.json"

# Paris 직전 6 개월 = Seoul "before Paris" baseline (2024-06 ~ 2024-11)
PRE_PARIS_START = date(2024, 6, 1)
PRE_PARIS_END = date(2024, 11, 30)


def _monthly_mean(df: pd.DataFrame, col: str, start: date, end: date) -> pd.Series:
    m = (df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))
    return df.loc[m].groupby(df.loc[m, "date"].dt.to_period("M"))[col].mean()


def run_channel1_activity() -> dict:
    """Paris 중 활동량 3채널 vs 직전 Seoul 6개월 + gait 4채널 (위상차)."""
    df = load_daily_9ch()
    paris_mask = (df["date"] >= pd.Timestamp(PARIS_START)) & (df["date"] <= pd.Timestamp(PARIS_END))
    pre_mask = (df["date"] >= pd.Timestamp(PRE_PARIS_START)) & (df["date"] <= pd.Timestamp(PRE_PARIS_END))
    activity = ["steps", "distance_km", "flights"]
    gait = ["walking_speed", "step_length", "asymmetry", "double_support"]
    rows = {}
    for col in activity + gait:
        p = df.loc[paris_mask, col].dropna().to_numpy()
        s = df.loc[pre_mask, col].dropna().to_numpy()
        if len(p) < 5 or len(s) < 5:
            continue
        t, p_val, d = welch_t_and_d(p, s)
        rows[col] = {
            "n_Paris_days": int(len(p)),
            "n_PreParisSeoul_days": int(len(s)),
            "mean_Paris": round(float(p.mean()), 3),
            "mean_PreParisSeoul": round(float(s.mean()), 3),
            "pct_change": round((p.mean() - s.mean()) / max(abs(s.mean()), 1e-9) * 100, 1),
            "welch_t": round(t, 3), "p_value": round(p_val, 4), "cohens_d": round(d, 3),
        }
    return {
        "Paris_window": {"start": str(PARIS_START), "end": str(PARIS_END)},
        "PreParisSeoul_window": {"start": str(PRE_PARIS_START), "end": str(PRE_PARIS_END)},
        "activity_channels": {c: rows[c] for c in activity if c in rows},
        "gait_channels": {c: rows[c] for c in gait if c in rows},
        "interpretation": "활동량 3채널 d>0.4 + gait 4채널 d≈0 이면 'Paris 중 활동량만 부과, gait 변화 없음'.",
    }


def run_channel2_audio_monotonic() -> dict:
    """Paris 6개월 동안 일평균 headphone 청취시간 단조 증가 + 새벽 0~5시 점유율."""
    merged = load_daily_merged()
    paris_mask = (merged["date"] >= pd.Timestamp(PARIS_START)) & (merged["date"] <= pd.Timestamp(PARIS_END))
    paris_daily = merged.loc[paris_mask, ["date", "audio_minutes", "audio_mean_dB"]].copy()
    # 월별 평균
    paris_daily["ym"] = paris_daily["date"].dt.to_period("M")
    monthly = paris_daily.groupby("ym")["audio_minutes"].mean()
    # Spearman rank correlation (numpy)
    if len(monthly) >= 3:
        ranks_x = np.argsort(np.argsort(np.arange(len(monthly)))) + 1
        ranks_y = np.argsort(np.argsort(monthly.to_numpy())) + 1
        # Pearson on ranks
        cov = np.cov(ranks_x, ranks_y, ddof=1)[0, 1]
        spearman = cov / (ranks_x.std(ddof=1) * ranks_y.std(ddof=1))
    else:
        spearman = float("nan")
    monthly_dict = {str(k): round(float(v), 1) for k, v in monthly.items()}

    # 새벽 0~5시 점유율은 hourly raw 가 필요하므로 cached daily aggregate 만으로는 불가
    # → cached daily audio_minutes 의 단조성만 보고, 새벽 점유는 별도 처리 권장으로 명시
    return {
        "Paris_monthly_audio_minutes": monthly_dict,
        "first_month_mean_min": round(float(monthly.iloc[0]), 1) if len(monthly) else float("nan"),
        "last_month_mean_min": round(float(monthly.iloc[-1]), 1) if len(monthly) else float("nan"),
        "ratio_last_vs_first": round(float(monthly.iloc[-1]) / max(float(monthly.iloc[0]), 1e-9), 2) if len(monthly) >= 2 else float("nan"),
        "spearman_rho": round(float(spearman), 3) if not np.isnan(spearman) else None,
        "interpretation": "spearman_rho > 0.7 이면 단조 증가 — '적응=음악 의존 감소' 가설 정반대.",
        "caveat": "새벽 0~5시 점유율 36.5% 는 hourly raw 가 필요해 본 cached 모듈에서는 산출 안 함 — XML 재파싱 시 별도 산출 가능.",
    }


def run_channel3_post_paris_remodel() -> dict:
    """귀국 후 (Seoul_rec) gait 4채널 vs pre-MIL baseline + Maps explore-day 폭발 timing."""
    df = load_daily_9ch()
    base_mask = (df["date"] >= pd.Timestamp(PRE_MIL_BASELINE.start)) & (
        df["date"] <= pd.Timestamp(PRE_MIL_BASELINE.end)
    )
    sr_mask = df["date"] >= pd.Timestamp(SEOUL_REC_START)
    gait = ["walking_speed", "step_length", "asymmetry", "double_support"]
    rows = {}
    for col in gait:
        b = df.loc[base_mask, col].dropna().to_numpy()
        r = df.loc[sr_mask, col].dropna().to_numpy()
        if len(b) < 5 or len(r) < 5:
            continue
        t, p_val, d = welch_t_and_d(r, b)
        rows[col] = {
            "n_baseline_days": int(len(b)), "n_SeoulRec_days": int(len(r)),
            "mean_baseline": round(float(b.mean()), 3),
            "mean_SeoulRec": round(float(r.mean()), 3),
            "welch_t": round(t, 3), "p_value": round(p_val, 4), "cohens_d": round(d, 3),
        }

    # Maps explore-day timing in Paris (early/mid/late 1/3)
    explore_timing: dict[str, int] = {"early_third": 0, "mid_third": 0, "late_third": 0}
    if MAPS_JSON.exists():
        with open(MAPS_JSON) as f:
            data = json.load(f)
        segments = data.get("semanticSegments", data) if isinstance(data, dict) else data
        by_date_searched: dict[str, int] = defaultdict(int)
        for seg in segments:
            ts = (seg.get("startTime") or "")[:10]
            if not ts: continue
            visit = seg.get("visit") or {}
            topc = visit.get("topCandidate") or {}
            sem = topc.get("semanticType", "")
            if "SEARCHED" in sem.upper():
                by_date_searched[ts] += 1
        paris_start = pd.Timestamp(PARIS_START); paris_end = pd.Timestamp(PARIS_END)
        span_days = (paris_end - paris_start).days
        for d_str, n in by_date_searched.items():
            if n < 2: continue
            d_ts = pd.Timestamp(d_str)
            if not (paris_start <= d_ts <= paris_end): continue
            day_offset = (d_ts - paris_start).days
            third = day_offset / max(span_days, 1)
            if third < 1/3: explore_timing["early_third"] += 1
            elif third < 2/3: explore_timing["mid_third"] += 1
            else: explore_timing["late_third"] += 1
    return {
        "gait_remodel_vs_baseline": rows,
        "explore_day_timing_in_Paris": explore_timing,
        "interpretation": "gait d>1 + explore_day 가 late_third 에 폭증 이면 'Paris 자체는 원료, 귀국 후 가공' 2단계 구조.",
    }


def run() -> dict:
    out = {
        "channel1_activity": run_channel1_activity(),
        "channel2_audio_monotonic": run_channel2_audio_monotonic(),
        "channel3_post_paris_remodel": run_channel3_post_paris_remodel(),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    return out


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
