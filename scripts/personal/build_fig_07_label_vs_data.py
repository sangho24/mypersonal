"""Figure F07 — 발견 1: 라벨이 데이터를 자르지 않는다 + 도시 효과는 day-type 의 함수.

2 panel:
  Left  : K-means c0 비중 pre-MIL vs MIL (Δ pp 강조)
  Right : 도시 × day-type stratified Cohen's d (Paris vs Seoul-rec)

데이터 출처: results/personal/finding1.json (src.personal.finding1_label_vs_data)
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

PROJECT = Path(__file__).parents[2]
DATA = PROJECT / "results" / "personal" / "finding1.json"
OUT = PROJECT / "results" / "personal" / "figures" / "F07_label_vs_data.png"


def _korean_font() -> None:
    for n in ("AppleGothic", "NanumGothic", "Malgun Gothic", "Noto Sans CJK KR"):
        if n in {f.name for f in mpl.font_manager.fontManager.ttflist}:
            mpl.rc("font", family=n); break
    mpl.rcParams["axes.unicode_minus"] = False


def main() -> None:
    _korean_font()
    j = json.loads(DATA.read_text())
    km = j["kmeans_chapter"]
    sim = j["simpson_stratification"]

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(13, 5.5), gridspec_kw={"width_ratios": [1, 1.4]})

    # ─── Left: c0 비중 pre-MIL vs MIL ───
    pre = km["pre_MIL_window"]["c0_pct"]; mil = km["MIL_window"]["c0_pct"]
    delta = km["delta_pp"]
    bars = axL.bar(["학부 baseline\n(2020-09~2021-10)", "군 복무\n(2021-11~2023-05)"],
                   [pre, mil], color=["#3A6EA5", "#D88C2A"], edgecolor="black")
    for b, v, n in zip(bars, [pre, mil], [km["pre_MIL_window"]["n_days"], km["MIL_window"]["n_days"]]):
        axL.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.1f}%\n(n={n}d)",
                 ha="center", va="bottom", fontsize=11, fontweight="bold")
    axL.set_ylim(0, max(pre, mil) + 12)
    axL.set_ylabel("c0 cluster 비중 (%)", fontsize=12)
    axL.set_title(f"K-means K=4, 9채널 일별 → cluster c0\nΔ = {delta:+.2f}pp ('학부 ≈ 군복무' 데이터 분기 안 됨)",
                  fontsize=12, fontweight="bold")
    axL.axhline(50, ls=":", color="gray", lw=0.8)
    axL.grid(axis="y", alpha=0.3)
    axL.spines[["top", "right"]].set_visible(False)

    # ─── Right: 도시 × day-type stratified Cohen's d ───
    overall_d = sim["overall"]["cohens_d"]; overall_p = sim["overall"]["p_value"]
    cats = ["home_only", "routine", "outing", "explore"]
    ds = [sim["stratified_by_day_category"][c]["cohens_d"] for c in cats]
    ps = [sim["stratified_by_day_category"][c]["p_value"] for c in cats]
    ns = [(sim["stratified_by_day_category"][c]["n_Paris"], sim["stratified_by_day_category"][c]["n_Seoul_rec"]) for c in cats]
    colors = ["#3F8A56" if d > 0 else "#C44E4E" for d in ds]
    edge = ["black" if p < 0.05 else "#888888" for p in ps]
    ypos = np.arange(len(cats) + 1)[::-1]
    labels = ["전체\n(stratify 전)"] + [f"{c}\n(n_P={n[0]}, n_S={n[1]})" for c, n in zip(cats, ns)]
    vals = [overall_d] + ds
    col_all = "#3F8A56" if overall_d > 0 else "#C44E4E"
    edge_all = "black"
    bar_colors = [col_all] + colors
    bar_edges = [edge_all] + edge
    bars = axR.barh(ypos, vals, color=bar_colors, edgecolor=bar_edges, linewidth=1.5)
    # marker for the "overall" row
    axR.barh(ypos[0], vals[0], color=col_all, edgecolor="black", linewidth=2.5, hatch="///")
    for i, (v, p) in enumerate(zip(vals, [overall_p] + ps)):
        x_off = 0.05 if v >= 0 else -0.05
        ha = "left" if v >= 0 else "right"
        sig = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "ns"))
        axR.text(v + x_off, ypos[i], f"d={v:+.2f} {sig}", va="center", ha=ha, fontsize=10, fontweight="bold")
    axR.axvline(0, color="black", lw=0.8)
    axR.set_yticks(ypos); axR.set_yticklabels(labels, fontsize=10)
    axR.set_xlabel("Cohen's d  (Paris − Seoul_rec, daily_steps)", fontsize=12)
    axR.set_title("도시 효과는 day-type 의 함수 — 한 방향이 아니다\n(전체로 보면 +d, 카테고리별로는 +d / ns / −d 가 섞임)",
                  fontsize=12, fontweight="bold")
    xlim_max = max(abs(min(vals)), abs(max(vals))) + 0.8
    axR.set_xlim(-xlim_max, xlim_max)
    axR.grid(axis="x", alpha=0.3)
    axR.spines[["top", "right"]].set_visible(False)

    fig.suptitle("발견 1 — 자전적 라벨이 데이터를 자르지 않는다 / 도시 효과는 단순하지 않다",
                 fontsize=14, fontweight="bold", y=1.00)
    fig.text(0.5, -0.02,
             f"좌: K-means 9채널(steps/distance/active/flights/walking_speed/step_length/asymmetry/double_support/audio_max_dB), 일별 n={km['n_days_used']}, baseline mean imputation. "
             f"우: 도시 = Maps Timeline dominant 라벨 (Paris {PROJECT.name}: 2024-12~2025-06 vs Seoul_rec: 2025-07~), day_category = Maps visit 기반.",
             ha="center", fontsize=8, color="#555555")

    plt.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"saved → {OUT}")


if __name__ == "__main__":
    main()
