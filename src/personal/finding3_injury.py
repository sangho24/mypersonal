"""보조 발견 (appendix) — 부상 시리즈.

(a) walking_steadiness 가 ACL 부상 전 단조 하락하는가
(b) ACL 수술월(2024-01)이 시계열 전체에서 가장 깊은 단일월 anomaly 인가
(c) Running workout 이 수술 후 정확히 N개월 후 재개되는가

결과 JSON: results/personal/finding3.json
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from src.personal.anchors import ACL_INJURY, ACL_SURGERY, PRE_MIL_BASELINE
from src.personal.data import load_daily_9ch

OUT_JSON = Path(__file__).parents[2] / "results" / "personal" / "finding3.json"
APPLE_XML = Path("/Users/sangho/Downloads/apple_health_export/내보내기.xml")


def run_walking_steadiness_lead() -> dict:
    """Apple Walking Steadiness % 가 부상 전 단조 하락하는가."""
    if not APPLE_XML.exists():
        return {"error": "Apple Health XML 없음", "path": str(APPLE_XML)}
    monthly: dict[str, list[float]] = defaultdict(list)
    target_type = "HKQuantityTypeIdentifierAppleWalkingSteadiness"
    for _, elem in ET.iterparse(str(APPLE_XML), events=("end",)):
        if elem.tag == "Record" and elem.get("type") == target_type:
            ts = elem.get("startDate", "")[:7]
            try:
                v = float(elem.get("value", "nan"))
                monthly[ts].append(v)
            except (TypeError, ValueError):
                pass
            elem.clear()
        elif elem.tag == "Record":
            elem.clear()
    series = {m: round(float(np.mean(vs)), 4) for m, vs in sorted(monthly.items()) if vs}
    # 2023-09 ~ 2024-01 단조 하락 검정
    window = [(m, v) for m, v in series.items() if "2023-09" <= m <= "2024-01"]
    monotone = all(window[i][1] >= window[i + 1][1] for i in range(len(window) - 1)) if len(window) >= 2 else False
    return {
        "monthly_steadiness_pct": series,
        "window_2023_09_to_2024_01": dict(window),
        "is_strictly_monotone_decreasing": monotone,
        "min_month": min(series.items(), key=lambda kv: kv[1]) if series else None,
        "interpretation": "2023-09 부터 2024-01 까지 단조 하락이면 '보행안정성이 부상/수술 4개월 선행 신호'.",
    }


def run_surgery_month_anomaly() -> dict:
    """2024-01 (수술월) 의 채널별 z-score 가 시계열에서 가장 강한가."""
    df = load_daily_9ch()
    # 월별 평균
    df["ym"] = df["date"].dt.to_period("M")
    chans = ["steps", "distance_km", "walking_speed", "step_length", "asymmetry", "double_support"]
    monthly = df.groupby("ym")[chans].mean()
    base_period_start = pd.Period(str(PRE_MIL_BASELINE.start)[:7])
    base_period_end = pd.Period(str(PRE_MIL_BASELINE.end)[:7])
    base = monthly.loc[base_period_start:base_period_end]
    mu = base.mean(); sd = base.std(ddof=1)
    zmat = (monthly - mu) / sd
    surg_period = pd.Period(str(ACL_SURGERY)[:7])
    if surg_period not in zmat.index:
        return {"error": f"수술월 {surg_period} 가 monthly index 에 없음"}
    surg_z = zmat.loc[surg_period].to_dict()
    # 각 채널의 가장 극단 월 (|z| 최대)
    extreme = {}
    for c in chans:
        s = zmat[c].dropna()
        if len(s) == 0: continue
        idx = s.abs().idxmax()
        extreme[c] = {
            "extreme_month": str(idx),
            "z": round(float(s.loc[idx]), 2),
            "surgery_month_z": round(float(surg_z[c]) if not np.isnan(surg_z[c]) else float("nan"), 2),
            "surgery_is_extreme": str(idx) == str(surg_period),
        }
    return {
        "surgery_month": str(surg_period),
        "channel_extremes": extreme,
        "interpretation": "여러 채널의 extreme_month 가 수술월과 일치하면 '6년 시계열 유일한 대칭형 붕괴 fingerprint'.",
    }


def run_running_resume_after_surgery() -> dict:
    """Running workout 의 수술 후 재개 시점 + cluster."""
    if not APPLE_XML.exists():
        return {"error": "Apple Health XML 없음"}
    workouts = []
    for _, elem in ET.iterparse(str(APPLE_XML), events=("end",)):
        if elem.tag == "Workout":
            wt = elem.get("workoutActivityType", "")
            sd = elem.get("startDate", "")
            dur_min_raw = elem.get("duration", "0")
            try:
                dur_min = float(dur_min_raw)
            except ValueError:
                dur_min = 0.0
            workouts.append({"type": wt, "startDate": sd[:10], "duration_min": dur_min})
            elem.clear()
        elif elem.tag in ("Record",):
            elem.clear()
    running = [w for w in workouts if "Running" in w["type"]]
    running.sort(key=lambda w: w["startDate"])
    surg = ACL_SURGERY
    # 수술 후 첫 Running
    after = [w for w in running if pd.Timestamp(w["startDate"]).date() > surg]
    first_after = after[0] if after else None
    days_until_first = (pd.Timestamp(first_after["startDate"]).date() - surg).days if first_after else None
    # 수술 직후 90~180일 window 안 sessions
    window_count = sum(
        1 for w in after
        if 90 <= (pd.Timestamp(w["startDate"]).date() - surg).days <= 180
    )
    # 수술 직전 마지막 Running (= 부상 직전 활동 종료 시점)
    before = [w for w in running if pd.Timestamp(w["startDate"]).date() <= surg]
    last_before = before[-1] if before else None
    gap_days = None
    if last_before and first_after:
        gap_days = (pd.Timestamp(first_after["startDate"]).date() - pd.Timestamp(last_before["startDate"]).date()).days
    # 월별 Running 빈도 (2024 전반)
    monthly_count: dict[str, int] = defaultdict(int)
    for w in running:
        if w["startDate"][:4] == "2024":
            monthly_count[w["startDate"][:7]] += 1
    return {
        "total_running_workouts": len(running),
        "first_running_after_surgery": first_after,
        "days_from_surgery_to_first_run": days_until_first,
        "running_sessions_90_to_180d_window": window_count,
        "last_running_before_surgery": last_before,
        "gap_days_between_last_before_and_first_after": gap_days,
        "monthly_count_2024": dict(sorted(monthly_count.items())),
        "interpretation": "90~180d window 에 다수 session 이 몰리면 '권장 재활기간 절반에 폭주 시작'.",
    }


def run() -> dict:
    out = {
        "walking_steadiness_lead": run_walking_steadiness_lead(),
        "surgery_month_anomaly": run_surgery_month_anomaly(),
        "running_resume": run_running_resume_after_surgery(),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    return out


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
