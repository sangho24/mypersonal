"""Figure F09 — 부상 시리즈 (appendix).

2x2 panel:
  TL: Apple Walking Steadiness 2023-08 ~ 2024-05 단조 하락 + 회복 (4개월 선행 신호)
  TR: 수술월(2024-01) 채널별 z-score bar (asymmetry +5.58σ 가 시계열 최댓값)
  BL: Running workout timeline 2023-2025 (gap 296일 + 2024-04 8건 cluster)
  BR: 2024 월별 Running 빈도 (4월 spike)

데이터: results/personal/finding3.json
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.personal.anchors import ACL_INJURY, ACL_SURGERY

PROJECT = Path(__file__).parents[2]
DATA_JSON = PROJECT / "results" / "personal" / "finding3.json"
OUT = PROJECT / "results" / "personal" / "figures" / "F09_injury_signals.png"


def _korean_font() -> None:
    for n in ("AppleGothic", "NanumGothic", "Malgun Gothic", "Noto Sans CJK KR"):
        if n in {f.name for f in mpl.font_manager.fontManager.ttflist}:
            mpl.rc("font", family=n); break
    mpl.rcParams["axes.unicode_minus"] = False


def main() -> None:
    _korean_font()
    j = json.loads(DATA_JSON.read_text())
    fig, axes = plt.subplots(2, 2, figsize=(13, 8.5), gridspec_kw={"hspace": 0.40, "wspace": 0.30})

    # ─── TL: walking_steadiness 단조 하락 + 회복 ───
    ax = axes[0, 0]
    ws = j["walking_steadiness_lead"]
    series = ws["monthly_steadiness_pct"]
    # window 2023-08 ~ 2024-08 만 그리기
    plot_x, plot_y = [], []
    for m, v in series.items():
        if "2023-08" <= m <= "2024-08":
            plot_x.append(pd.Timestamp(m + "-15")); plot_y.append(v * 100)
    ax.plot(plot_x, plot_y, lw=2, color="#C44E4E", marker="o", ms=6)
    ax.axvline(pd.Timestamp(ACL_INJURY), color="#D88C2A", lw=1.5, ls=":", label=f"부상 추정 {ACL_INJURY}")
    ax.axvline(pd.Timestamp(ACL_SURGERY), color="#C44E4E", lw=1.8, ls="--", label=f"수술 {ACL_SURGERY}")
    ax.set_ylabel("Walking Steadiness (%)", fontsize=11)
    ax.set_title("부상 4개월 전부터 보행 안정성 단조 하락\n(2023-09 100% → 2024-01 90%, 그 후 회복)",
                 fontsize=11, fontweight="bold")
    ax.legend(loc="lower left", fontsize=9)
    ax.grid(alpha=0.3)

    # ─── TR: 수술월 z-score bar ───
    ax = axes[0, 1]
    surg = j["surgery_month_anomaly"]["channel_extremes"]
    chans = ["steps", "distance_km", "walking_speed", "step_length", "asymmetry", "double_support"]
    surg_zs = [surg[c]["surgery_month_z"] for c in chans]
    extreme_match = [surg[c]["surgery_is_extreme"] for c in chans]
    colors = ["#C44E4E" if m else "#888888" for m in extreme_match]
    bars = ax.barh(chans[::-1], surg_zs[::-1], color=colors[::-1], edgecolor="black")
    for i, (z, c, m) in enumerate(zip(surg_zs[::-1], chans[::-1], extreme_match[::-1])):
        tag = " ← 시계열 최댓값" if m else ""
        x_off = 0.15 if z >= 0 else -0.15
        ha = "left" if z >= 0 else "right"
        ax.text(z + x_off, i, f"z={z:+.2f}{tag}", va="center", ha=ha, fontsize=9, fontweight="bold")
    ax.axvline(0, color="black", lw=0.8)
    ax.axvline(2, color="gray", lw=0.5, ls=":"); ax.axvline(-2, color="gray", lw=0.5, ls=":")
    xlim = max(max(surg_zs), abs(min(surg_zs))) + 2.5
    ax.set_xlim(-xlim, xlim)
    ax.set_xlabel("z-score (vs pre-MIL baseline)", fontsize=11)
    ax.set_title("수술월 (2024-01) z-score — asymmetry +5.58σ 가 시계열 6년 최댓값\n('급성 부상' 의 단일 signature 는 비대칭에 가장 강하게 새겨짐)",
                 fontsize=11, fontweight="bold")
    ax.grid(axis="x", alpha=0.3)

    # ─── BL: Running workout timeline ───
    ax = axes[1, 0]
    rr = j["running_resume"]
    # 시점만 표시 (먼 옛날부터 최근까지)
    # finding3 json 에는 first_after / last_before 만 있어서 monthly_count 사용
    # 추가로 last_before, first_after 마커
    last_before = pd.Timestamp(rr["last_running_before_surgery"]["startDate"])
    first_after = pd.Timestamp(rr["first_running_after_surgery"]["startDate"])
    gap = rr["gap_days_between_last_before_and_first_after"]
    days_first = rr["days_from_surgery_to_first_run"]
    window_count = rr["running_sessions_90_to_180d_window"]
    ax.axvline(pd.Timestamp(ACL_SURGERY), color="#C44E4E", lw=2.5, ls="--", label=f"수술 {ACL_SURGERY}")
    ax.axvspan(pd.Timestamp(ACL_SURGERY) + pd.Timedelta(days=90), pd.Timestamp(ACL_SURGERY) + pd.Timedelta(days=180),
               color="#FFE0B2", alpha=0.45, label=f"90~180일 권장 재활 window ({window_count} sessions)")
    ax.scatter([last_before], [1], s=160, color="#3F8A56", edgecolor="black", zorder=5, label=f"부상 전 마지막 Run\n{last_before.date()} (전역 후 1개월)")
    ax.scatter([first_after], [1], s=160, color="#C44E4E", edgecolor="black", zorder=5, label=f"수술 후 첫 Run\n{first_after.date()} (D+{days_first})")
    ax.annotate(f"공백 {gap}일", xy=((last_before + (first_after - last_before) / 2), 1),
                xytext=(0, 25), textcoords="offset points", ha="center", fontsize=10, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", fc="#FFFDE7", ec="black", lw=0.8))
    ax.set_ylim(0.4, 1.6); ax.set_yticks([])
    ax.set_title(f"Running 공백 {gap}일 → 수술 후 정확히 {days_first}일에 첫 Run\n(권장 재활 window 90~180일 중 4월에만 {window_count}건 폭주)",
                 fontsize=11, fontweight="bold")
    ax.legend(loc="upper left", fontsize=8, framealpha=0.85)
    ax.grid(axis="x", alpha=0.3)

    # ─── BR: 2024 월별 Running count ───
    ax = axes[1, 1]
    mc = rr["monthly_count_2024"]
    months = list(mc.keys()); counts = list(mc.values())
    bar_colors = ["#C44E4E" if int(m[5:]) == 4 else "#3A6EA5" for m in months]
    ax.bar(months, counts, color=bar_colors, edgecolor="black")
    for m, c in zip(months, counts):
        ax.text(m, c + 0.2, str(c), ha="center", fontsize=10, fontweight="bold")
    ax.set_ylim(0, max(counts) + 2)
    ax.set_ylabel("Running session 수", fontsize=11)
    ax.set_title(f"2024년 월별 Running 빈도 — {months[0]} 한 달에만 {counts[0]}건 폭주\n(권장 재활 기간 절반 시점에 너무 많이)",
                 fontsize=11, fontweight="bold")
    ax.grid(axis="y", alpha=0.3)

    fig.suptitle("발견 (Appendix) — 부상 시리즈: 보행 안정성이 4개월 선행, asymmetry 가 시계열 최강 단일 signature, Running 90일 폭주",
                 fontsize=13, fontweight="bold", y=1.00)

    plt.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"saved → {OUT}")


if __name__ == "__main__":
    main()
