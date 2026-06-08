"""Figure F08 — 발견 2: Paris 라는 한 사건이 세 채널에 다른 위상으로 새겨졌다.

3 panel 세로 stack:
  Top    : 월별 활동량 (steps + distance + flights), Paris 음영 + 귀국 vertical line
  Middle : 월별 audio listen-minutes Paris monotonic 증가 (71→251)
  Bottom : 월별 walking_speed (baseline & Seoul_rec mean ± band) + Maps explore-day count

데이터 출처:
  - data/processed/personal/personal_daily*.parquet
  - results/personal/finding2.json (Paris 통계)
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

from src.personal.anchors import PARIS_END, PARIS_START, PRE_MIL_BASELINE, SEOUL_REC_START

PROJECT = Path(__file__).parents[2]
DATA_JSON = PROJECT / "results" / "personal" / "finding2.json"
OUT = PROJECT / "results" / "personal" / "figures" / "F08_paris_phase.png"


def _korean_font() -> None:
    for n in ("AppleGothic", "NanumGothic", "Malgun Gothic", "Noto Sans CJK KR"):
        if n in {f.name for f in mpl.font_manager.fontManager.ttflist}:
            mpl.rc("font", family=n); break
    mpl.rcParams["axes.unicode_minus"] = False


def main() -> None:
    _korean_font()
    j = json.loads(DATA_JSON.read_text())
    a = pd.read_parquet(PROJECT / "data/processed/personal/personal_daily.parquet")
    h = pd.read_parquet(PROJECT / "data/processed/personal/personal_daily_hmm.parquet")
    df = h.merge(a[["date", "flights", "active_energy_kcal"]], on="date", how="left")
    df["date"] = pd.to_datetime(df["date"])
    df["ym"] = df["date"].dt.to_period("M").dt.to_timestamp()

    monthly = df.groupby("ym").agg(
        steps=("steps", "mean"),
        distance_km=("distance_km", "mean"),
        flights=("flights", "mean"),
        walking_speed=("walking_speed", "mean"),
        audio_listen_min=("audio_listen_min", "mean"),
    )

    paris_s = pd.Timestamp(PARIS_START); paris_e = pd.Timestamp(PARIS_END)
    seoul_s = pd.Timestamp(SEOUL_REC_START)
    base_s = pd.Timestamp(PRE_MIL_BASELINE.start); base_e = pd.Timestamp(PRE_MIL_BASELINE.end)

    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True, gridspec_kw={"hspace": 0.30})

    # ─── Panel 1: 활동량 (steps + distance scaled + flights scaled) ───
    ax = axes[0]
    ax.plot(monthly.index, monthly["steps"], lw=2, color="#3A6EA5", marker="o", ms=4, label="steps/day (좌축)")
    ax.set_ylabel("steps/day", color="#3A6EA5", fontsize=11)
    ax.tick_params(axis="y", labelcolor="#3A6EA5")
    ax2 = ax.twinx()
    ax2.plot(monthly.index, monthly["distance_km"], lw=1.5, color="#D88C2A", marker="^", ms=3.5, alpha=0.85, label="distance km/day (우축, scaled)")
    ax2.plot(monthly.index, monthly["flights"], lw=1.5, color="#3F8A56", marker="s", ms=3.5, alpha=0.85, label="flights/day (우축)")
    ax2.set_ylabel("distance (km) / flights", fontsize=11)
    ax.axvspan(paris_s, paris_e, color="#FFE0B2", alpha=0.35, label="Paris 체류")
    ax.axvline(seoul_s, color="#3F8A56", lw=1.5, ls="--", alpha=0.8, label="귀국")
    c1 = j["channel1_activity"]["activity_channels"]
    ax.set_title(f"채널 1 — Paris 중 활동량 일제 상승 "
                 f"(steps {c1['steps']['pct_change']:+.0f}%, distance {c1['distance_km']['pct_change']:+.0f}%, flights {c1['flights']['pct_change']:+.0f}%, 모두 p<0.05)",
                 fontsize=11, fontweight="bold")
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8, framealpha=0.85)
    ax.grid(alpha=0.3)

    # ─── Panel 2: audio listen-minutes Paris monotonic ───
    ax = axes[1]
    ax.plot(monthly.index, monthly["audio_listen_min"], lw=2, color="#7B4FA8", marker="D", ms=4)
    ax.axvspan(paris_s, paris_e, color="#FFE0B2", alpha=0.35)
    ax.axvline(seoul_s, color="#3F8A56", lw=1.5, ls="--", alpha=0.8)
    # annotate Paris first/last month numbers
    c2 = j["channel2_audio_monotonic"]
    first = c2["first_month_mean_min"]; last = c2["last_month_mean_min"]; ratio = c2["ratio_last_vs_first"]; rho = c2["spearman_rho"]
    paris_months = monthly[(monthly.index >= paris_s) & (monthly.index <= paris_e)]
    if len(paris_months):
        ax.scatter([paris_months.index[0]], [paris_months["audio_listen_min"].iloc[0]], s=120, color="#7B4FA8", edgecolor="black", zorder=5)
        ax.scatter([paris_months.index[-1]], [paris_months["audio_listen_min"].iloc[-1]], s=120, color="#7B4FA8", edgecolor="black", zorder=5)
        ax.annotate(f"Paris 12월\n{first:.0f}분/일", xy=(paris_months.index[0], first), xytext=(-30, 25), textcoords="offset points",
                    fontsize=9, ha="center", arrowprops=dict(arrowstyle="-", color="black"))
        ax.annotate(f"Paris 6월\n{last:.0f}분/일\n({ratio:.1f}배)", xy=(paris_months.index[-1], last), xytext=(20, 10), textcoords="offset points",
                    fontsize=9, ha="left", arrowprops=dict(arrowstyle="-", color="black"))
    ax.set_ylabel("월별 평균 청취시간 (분/일)", fontsize=11)
    ax.set_title(f"채널 2 — Paris 6개월 동안 청취시간 단조 증가 (Spearman ρ={rho:.2f}) — '적응=의존 감소' 가설 정반대",
                 fontsize=11, fontweight="bold")
    ax.grid(alpha=0.3)

    # ─── Panel 3: walking_speed monthly + baseline & Seoul_rec mean bands ───
    ax = axes[2]
    ws = monthly["walking_speed"]
    ax.plot(ws.index, ws, lw=1.5, color="#1A1A1A", marker="o", ms=3.5)
    # baseline band (pre-MIL)
    base_window = df[(df["date"] >= base_s) & (df["date"] <= base_e)]["walking_speed"].dropna()
    if len(base_window):
        b_mu, b_sd = float(base_window.mean()), float(base_window.std(ddof=1))
        ax.axhspan(b_mu - b_sd, b_mu + b_sd, color="#3A6EA5", alpha=0.18, label=f"pre-MIL baseline {b_mu:.2f}±{b_sd:.2f}")
    sr_window = df[df["date"] >= seoul_s]["walking_speed"].dropna()
    if len(sr_window):
        s_mu, s_sd = float(sr_window.mean()), float(sr_window.std(ddof=1))
        ax.axhspan(s_mu - s_sd, s_mu + s_sd, color="#3F8A56", alpha=0.18, label=f"Seoul_rec mean {s_mu:.2f}±{s_sd:.2f}")
    ax.axvspan(paris_s, paris_e, color="#FFE0B2", alpha=0.35)
    ax.axvline(seoul_s, color="#3F8A56", lw=1.5, ls="--", alpha=0.8)
    c3 = j["channel3_post_paris_remodel"]
    wsd = c3["gait_remodel_vs_baseline"]["walking_speed"]
    explore = c3["explore_day_timing_in_Paris"]
    ax.set_ylabel("walking_speed (m/s)", fontsize=11)
    ax.set_title(f"채널 3 — gait remodel: Seoul_rec vs baseline d={wsd['cohens_d']:.2f} (p<0.001) "
                 f"| Paris explore-day (Searched ≥2): early {explore['early_third']} / mid {explore['mid_third']} / late {explore['late_third']}",
                 fontsize=11, fontweight="bold")
    ax.legend(loc="lower right", fontsize=8, framealpha=0.85)
    ax.grid(alpha=0.3)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    fig.suptitle("발견 2 — 'Paris' 라는 한 사건이 세 채널에 다른 위상으로 새겨졌다",
                 fontsize=14, fontweight="bold", y=1.00)

    plt.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"saved → {OUT}")


if __name__ == "__main__":
    main()
