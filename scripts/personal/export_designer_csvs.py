"""Slide 8 (Paris 3-channel) + Slide 12 (Appendix injury) 의 native-chart 용 CSV 추출.

디자이너가 PowerPoint 차트 마법사로 그대로 가져갈 수 있도록 panel 별 CSV + 핵심 수치 요약.

산출:
    results/personal/csv_exports/
        slide8_panel1_monthly_activity.csv      (steps/distance/flights monthly + Paris flag)
        slide8_panel2_paris_audio_monthly.csv   (Paris 6개월 audio_listen_min 단조 증가)
        slide8_panel3_walking_speed_monthly.csv (gait remodel 시계열 + baseline / Seoul_rec band)
        slide8_panel3_explore_timing.csv        (Paris early/mid/late explore-day count)
        slide8_key_numbers.csv                  (callout box 용 핵심 수치)
        slide12_panel1_steadiness.csv           (Walking Steadiness 4개월 선행)
        slide12_panel2_surgery_zscores.csv      (수술월 채널별 z + 시계열 extreme)
        slide12_panel3_running_timeline.csv     (Running 47건 timeline)
        slide12_panel4_2024_monthly_running.csv (2024 월별 Running 빈도)
        slide12_key_numbers.csv                 (callout box 용)
"""
from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date
from pathlib import Path

import pandas as pd

from src.personal.anchors import (
    ACL_INJURY,
    ACL_SURGERY,
    MIL_END,
    MIL_START,
    PARIS_END,
    PARIS_START,
    PRE_MIL_BASELINE,
    SEOUL_REC_START,
)
from src.personal.data import load_daily_9ch, load_daily_merged

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "personal" / "csv_exports"
OUT.mkdir(parents=True, exist_ok=True)
APPLE_XML = Path("/Users/sangho/Downloads/apple_health_export/내보내기.xml")

F2 = json.loads((ROOT / "results/personal/finding2.json").read_text())
F3 = json.loads((ROOT / "results/personal/finding3.json").read_text())


def _write_csv(path: Path, rows: list[dict], cols: list[str]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    print(f"  → {path.relative_to(ROOT)} ({len(rows)} rows)")


# ─── Slide 8 ───
def slide8_panel1_monthly_activity() -> None:
    df = load_daily_9ch()
    df["date"] = pd.to_datetime(df["date"])
    df["ym"] = df["date"].dt.to_period("M").dt.to_timestamp()
    monthly = df.groupby("ym").agg(
        steps_mean=("steps", "mean"),
        distance_km_mean=("distance_km", "mean"),
        flights_mean=("flights", "mean"),
    ).round(2).reset_index()
    rows = []
    for _, r in monthly.iterrows():
        m = r["ym"]
        if pd.isna(r["steps_mean"]):
            continue
        in_paris = pd.Timestamp(PARIS_START) <= m <= pd.Timestamp(PARIS_END)
        is_seoul_rec = m >= pd.Timestamp(SEOUL_REC_START)
        rows.append({
            "month": m.strftime("%Y-%m"),
            "steps_per_day": r["steps_mean"],
            "distance_km_per_day": r["distance_km_mean"],
            "flights_per_day": r["flights_mean"],
            "phase": "Paris" if in_paris else ("Seoul_rec" if is_seoul_rec else ("MIL" if pd.Timestamp(MIL_START) <= m <= pd.Timestamp(MIL_END) else "other")),
        })
    _write_csv(OUT / "slide8_panel1_monthly_activity.csv", rows,
               ["month", "steps_per_day", "distance_km_per_day", "flights_per_day", "phase"])


def slide8_panel2_paris_audio() -> None:
    audio = F2["channel2_audio_monotonic"]["Paris_monthly_audio_minutes"]
    rows = [{"month": m, "audio_listen_min_per_day": v} for m, v in sorted(audio.items())]
    _write_csv(OUT / "slide8_panel2_paris_audio_monthly.csv", rows,
               ["month", "audio_listen_min_per_day"])


def slide8_panel3_walking_speed() -> None:
    df = load_daily_9ch()
    df["date"] = pd.to_datetime(df["date"])
    df["ym"] = df["date"].dt.to_period("M").dt.to_timestamp()
    monthly = df.groupby("ym")["walking_speed"].mean().round(3).reset_index()

    base_mask = (df["date"] >= pd.Timestamp(PRE_MIL_BASELINE.start)) & (df["date"] <= pd.Timestamp(PRE_MIL_BASELINE.end))
    sr_mask = df["date"] >= pd.Timestamp(SEOUL_REC_START)
    base_mean = float(df.loc[base_mask, "walking_speed"].dropna().mean())
    base_sd = float(df.loc[base_mask, "walking_speed"].dropna().std(ddof=1))
    sr_mean = float(df.loc[sr_mask, "walking_speed"].dropna().mean())
    sr_sd = float(df.loc[sr_mask, "walking_speed"].dropna().std(ddof=1))

    rows = []
    for _, r in monthly.iterrows():
        m = r["ym"]
        if pd.isna(r["walking_speed"]):
            continue
        rows.append({
            "month": m.strftime("%Y-%m"),
            "walking_speed_kmh": r["walking_speed"],
            "baseline_pre_MIL_mean": round(base_mean, 3),
            "baseline_pre_MIL_low_1sd": round(base_mean - base_sd, 3),
            "baseline_pre_MIL_high_1sd": round(base_mean + base_sd, 3),
            "Seoul_rec_mean": round(sr_mean, 3),
            "Seoul_rec_low_1sd": round(sr_mean - sr_sd, 3),
            "Seoul_rec_high_1sd": round(sr_mean + sr_sd, 3),
        })
    _write_csv(OUT / "slide8_panel3_walking_speed_monthly.csv", rows,
               ["month", "walking_speed_kmh", "baseline_pre_MIL_mean",
                "baseline_pre_MIL_low_1sd", "baseline_pre_MIL_high_1sd",
                "Seoul_rec_mean", "Seoul_rec_low_1sd", "Seoul_rec_high_1sd"])


def slide8_explore_timing() -> None:
    et = F2["channel3_post_paris_remodel"]["explore_day_timing_in_Paris"]
    rows = [
        {"paris_third": "early (12월~2월)", "explore_day_count": et["early_third"]},
        {"paris_third": "mid (2월~4월)", "explore_day_count": et["mid_third"]},
        {"paris_third": "late (4월~6월)", "explore_day_count": et["late_third"]},
    ]
    _write_csv(OUT / "slide8_panel3_explore_timing.csv", rows,
               ["paris_third", "explore_day_count"])


def slide8_key_numbers() -> None:
    ch1 = F2["channel1_activity"]["activity_channels"]
    ch2 = F2["channel2_audio_monotonic"]
    ch3 = F2["channel3_post_paris_remodel"]["gait_remodel_vs_baseline"]
    rows = [
        {"channel": "1 활동량 (Paris 중)", "metric": "steps", "value": f"{ch1['steps']['pct_change']:+.1f}% (d={ch1['steps']['cohens_d']:+.2f}, n_Paris={ch1['steps']['n_Paris_days']}, n_pre={ch1['steps']['n_PreParisSeoul_days']})", "p_value": ch1["steps"]["p_value"]},
        {"channel": "1 활동량 (Paris 중)", "metric": "distance_km", "value": f"{ch1['distance_km']['pct_change']:+.1f}% (d={ch1['distance_km']['cohens_d']:+.2f})", "p_value": ch1["distance_km"]["p_value"]},
        {"channel": "1 활동량 (Paris 중)", "metric": "flights", "value": f"{ch1['flights']['pct_change']:+.1f}% (d={ch1['flights']['cohens_d']:+.2f})", "p_value": ch1["flights"]["p_value"]},
        {"channel": "2 청취량 (Paris 중)", "metric": "first → last month", "value": f"{ch2['first_month_mean_min']:.0f}분/일 → {ch2['last_month_mean_min']:.0f}분/일 ({ch2['ratio_last_vs_first']:.1f}배)", "p_value": ""},
        {"channel": "2 청취량 (Paris 중)", "metric": "Spearman ρ (단조)", "value": f"{ch2['spearman_rho']:.2f}", "p_value": ""},
        {"channel": "3 gait remodel (귀국 후)", "metric": "walking_speed", "value": f"d={ch3['walking_speed']['cohens_d']:+.2f} (Seoul_rec n={ch3['walking_speed']['n_SeoulRec_days']} vs baseline n={ch3['walking_speed']['n_baseline_days']})", "p_value": ch3["walking_speed"]["p_value"]},
        {"channel": "3 gait remodel (귀국 후)", "metric": "step_length", "value": f"d={ch3['step_length']['cohens_d']:+.2f}", "p_value": ch3["step_length"]["p_value"]},
        {"channel": "3 gait remodel (귀국 후)", "metric": "double_support", "value": f"d={ch3['double_support']['cohens_d']:+.2f}", "p_value": ch3["double_support"]["p_value"]},
    ]
    _write_csv(OUT / "slide8_key_numbers.csv", rows, ["channel", "metric", "value", "p_value"])


# ─── Slide 12 ───
def slide12_panel1_steadiness() -> None:
    series = F3["walking_steadiness_lead"]["monthly_steadiness_pct"]
    rows = []
    for m, v in sorted(series.items()):
        if "2023-08" <= m <= "2024-08":
            rows.append({
                "month": m,
                "walking_steadiness_pct": round(v * 100, 2),
                "event": ("ACL 부상 추정" if m == "2023-10" else ("ACL 수술" if m == "2024-01" else "")),
            })
    _write_csv(OUT / "slide12_panel1_steadiness.csv", rows,
               ["month", "walking_steadiness_pct", "event"])


def slide12_panel2_surgery_zscores() -> None:
    surg = F3["surgery_month_anomaly"]["channel_extremes"]
    chans = ["steps", "distance_km", "walking_speed", "step_length", "asymmetry", "double_support"]
    rows = []
    for c in chans:
        s = surg[c]
        rows.append({
            "channel": c,
            "surgery_month_z": s["surgery_month_z"],
            "is_timeseries_extreme": "Yes" if s["surgery_is_extreme"] else "No",
            "extreme_month": s["extreme_month"],
            "extreme_z": s["z"],
        })
    _write_csv(OUT / "slide12_panel2_surgery_zscores.csv", rows,
               ["channel", "surgery_month_z", "is_timeseries_extreme", "extreme_month", "extreme_z"])


def slide12_panel3_running_timeline() -> None:
    """Apple Health XML 의 모든 Running workout 시점·길이."""
    if not APPLE_XML.exists():
        print(f"  ! XML 없음: {APPLE_XML}")
        return
    workouts = []
    for _, elem in ET.iterparse(str(APPLE_XML), events=("end",)):
        if elem.tag == "Workout" and "Running" in elem.get("workoutActivityType", ""):
            workouts.append({
                "date": elem.get("startDate", "")[:10],
                "duration_min": round(float(elem.get("duration", "0")), 1),
                "source": elem.get("sourceName", ""),
            })
            elem.clear()
        elif elem.tag in ("Record",):
            elem.clear()
    workouts.sort(key=lambda w: w["date"])
    surg = ACL_SURGERY
    for w in workouts:
        d = pd.Timestamp(w["date"]).date()
        w["days_from_surgery"] = (d - surg).days
        w["phase"] = "before_surgery" if d <= surg else "after_surgery"
    _write_csv(OUT / "slide12_panel3_running_timeline.csv", workouts,
               ["date", "duration_min", "source", "days_from_surgery", "phase"])


def slide12_panel4_2024_monthly() -> None:
    mc = F3["running_resume"]["monthly_count_2024"]
    rows = [{"month": m, "running_session_count": c} for m, c in sorted(mc.items())]
    # 모든 2024 월 채우기 (0 도 명시)
    months_all = [f"2024-{i:02d}" for i in range(1, 13)]
    present = {r["month"]: r["running_session_count"] for r in rows}
    rows = [{"month": m, "running_session_count": present.get(m, 0)} for m in months_all]
    _write_csv(OUT / "slide12_panel4_2024_monthly_running.csv", rows,
               ["month", "running_session_count"])


def slide12_key_numbers() -> None:
    s = F3["walking_steadiness_lead"]
    ws = F3["surgery_month_anomaly"]["channel_extremes"]
    rr = F3["running_resume"]
    rows = [
        {"finding": "Walking Steadiness 4개월 선행 신호", "metric": "2023-09 → 2024-01 단조 하락", "value": f"{s['window_2023_09_to_2024_01']['2023-09']*100:.0f}% → {s['window_2023_09_to_2024_01']['2024-01']*100:.0f}%"},
        {"finding": "수술월 (2024-01) 최강 signature", "metric": "asymmetry z-score", "value": f"+{ws['asymmetry']['z']:.2f}σ (시계열 6년 최댓값)"},
        {"finding": "수술월 (2024-01) 동반 anomaly", "metric": "walking_speed / steps z", "value": f"{ws['walking_speed']['surgery_month_z']:.2f}σ / {ws['steps']['surgery_month_z']:.2f}σ"},
        {"finding": "Running 공백", "metric": "부상 전 마지막 → 수술 후 첫 재개", "value": f"{rr['last_running_before_surgery']['startDate']} → {rr['first_running_after_surgery']['startDate']} ({rr['gap_days_between_last_before_and_first_after']}일)"},
        {"finding": "Running 재개", "metric": "수술 후 첫 Run 시점", "value": f"D+{rr['days_from_surgery_to_first_run']}일"},
        {"finding": "Running 폭주", "metric": "권장 재활 90~180일 window", "value": f"{rr['running_sessions_90_to_180d_window']} sessions (2024-04 한 달 집중)"},
    ]
    _write_csv(OUT / "slide12_key_numbers.csv", rows, ["finding", "metric", "value"])


def main() -> None:
    print("=== Slide 8 (Paris 3-channel) ===")
    slide8_panel1_monthly_activity()
    slide8_panel2_paris_audio()
    slide8_panel3_walking_speed()
    slide8_explore_timing()
    slide8_key_numbers()
    print()
    print("=== Slide 12 (Appendix injury) ===")
    slide12_panel1_steadiness()
    slide12_panel2_surgery_zscores()
    slide12_panel3_running_timeline()
    slide12_panel4_2024_monthly()
    slide12_key_numbers()
    print()
    print(f"전체 산출 위치: {OUT}")


if __name__ == "__main__":
    main()
