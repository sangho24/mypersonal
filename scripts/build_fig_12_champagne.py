"""Figure 12 — France Champagne mechanism visualization.

Akerlof 정보 비대칭 가설의 직접 입증: HS 코드를 분해해서 보면
프랑스 샴페인 (HS 220410) 도매가는 11개국 스파클링 시장에서 1위이지만
markup 은 2.82× 로 가장 낮다. 같은 HS 안에서 남아프리카 (markup 11.36×) 와
4배 격차 — 도매가 prior 가 투명할수록 retail premium 이 압축된다.

Input:
  - results/data/hs_split.json        # 22 cells (11 countries × 2 HS codes)
  - results/data/champagne_case.json  # France HS 220410 단일 케이스 요약

Output:
  - results/figures/eda/12_champagne_mechanism.png
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HS_SPLIT = ROOT / "results" / "data" / "hs_split.json"
CASE = ROOT / "results" / "data" / "champagne_case.json"
OUT = ROOT / "results" / "figures" / "eda" / "12_champagne_mechanism.png"

# 색상 / 마커 — CLAUDE.md: matplotlib only
COLOR_STILL = "#1f3a93"     # navy — HS 220421 (still)
COLOR_SPARK = "#d4a017"     # gold — HS 220410 (sparkling)
COLOR_HIGHLIGHT = "#d72631"  # red — France Champagne ring
COLOR_BAR_FR = "#1f3a93"
COLOR_BAR_ZA = "#a85432"


def _setup_korean_font() -> None:
    """OS 별 한글 폰트 폴백. (PRD 따라 matplotlib only)."""
    candidates = ["AppleGothic", "Malgun Gothic", "NanumGothic", "DejaVu Sans"]
    available = {f.name for f in mpl.font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            mpl.rcParams["font.family"] = name
            break
    mpl.rcParams["axes.unicode_minus"] = False


def _load_rows() -> list[dict]:
    payload = json.loads(HS_SPLIT.read_text(encoding="utf-8"))
    return payload["rows"]


def _load_case() -> dict:
    return json.loads(CASE.read_text(encoding="utf-8"))


def build_figure() -> Path:
    _setup_korean_font()
    rows = _load_rows()
    case = _load_case()

    # ---- panel data ----
    sparkling = [r for r in rows if r["hs_code"] == 220410]
    still = [r for r in rows if r["hs_code"] == 220421]

    fr_sp = next(r for r in sparkling if r["country"] == "프랑스")
    za_sp = next(r for r in sparkling if r["country"] == "남아프리카")

    fig, (axL, axR) = plt.subplots(
        1, 2, figsize=(15, 6.5), gridspec_kw={"width_ratios": [1.5, 1.0]}
    )

    # =================== Panel A — scatter ===================
    # still 점들
    axL.scatter(
        [r["wholesale_krw_per_bottle"] for r in still],
        [r["markup"] for r in still],
        c=COLOR_STILL,
        marker="o",
        s=110,
        alpha=0.78,
        edgecolors="white",
        linewidths=1.2,
        label="HS 220421 (still wine)",
        zorder=3,
    )
    # sparkling 점들 (프랑스 제외하고 plot — France 는 강조용으로 따로)
    spark_others = [r for r in sparkling if r["country"] != "프랑스"]
    axL.scatter(
        [r["wholesale_krw_per_bottle"] for r in spark_others],
        [r["markup"] for r in spark_others],
        c=COLOR_SPARK,
        marker="s",
        s=110,
        alpha=0.85,
        edgecolors="white",
        linewidths=1.2,
        label="HS 220410 (sparkling)",
        zorder=3,
    )

    # France Champagne 강조 — gold square + red ring
    fr_x = fr_sp["wholesale_krw_per_bottle"]
    fr_y = fr_sp["markup"]
    axL.scatter(
        [fr_x], [fr_y],
        c=COLOR_SPARK, marker="s", s=160,
        edgecolors="white", linewidths=1.2, zorder=4,
    )
    axL.scatter(
        [fr_x], [fr_y],
        s=520, facecolors="none", edgecolors=COLOR_HIGHLIGHT,
        linewidths=2.6, zorder=5,
    )

    # 화살표 + 주석 박스
    annot_text = (
        "France Champagne\n"
        f"도매 {fr_x/1000:.1f}k KRW, markup {fr_y:.2f}×\n"
        "(11개국 스파클링 중 도매 1위)\n\n"
        "Akerlof 메커니즘:\n"
        "투명한 prior → 압축된 마진"
    )
    axL.annotate(
        annot_text,
        xy=(fr_x, fr_y),
        xytext=(fr_x * 0.18, fr_y + 4.2),
        fontsize=10.5,
        ha="left",
        va="center",
        bbox=dict(
            boxstyle="round,pad=0.55",
            fc="#fff6e0",
            ec=COLOR_HIGHLIGHT,
            lw=1.6,
        ),
        arrowprops=dict(
            arrowstyle="->",
            color=COLOR_HIGHLIGHT,
            lw=1.8,
            connectionstyle="arc3,rad=-0.18",
        ),
        zorder=6,
    )

    axL.set_xscale("log")
    axL.set_xlabel("도매가 (KRW / bottle, log scale)", fontsize=12)
    axL.set_ylabel("Markup (retail / wholesale)", fontsize=12)
    axL.set_title(
        "(A) 22 cells — 도매가 vs Markup (11개국 × 2 HS)",
        fontsize=12.5, pad=10,
    )
    axL.grid(True, which="both", alpha=0.25, linestyle="--", linewidth=0.7)
    axL.legend(loc="lower left", fontsize=10, framealpha=0.92)
    axL.set_ylim(0, axL.get_ylim()[1] + 1.5)

    # =================== Panel B — bar (France vs S.Africa @ 220410) ===================
    labels = ["프랑스\n(HS 220410)", "남아프리카\n(HS 220410)"]
    values = [fr_sp["markup"], za_sp["markup"]]
    colors = [COLOR_BAR_FR, COLOR_BAR_ZA]

    bars = axR.bar(
        labels, values, color=colors, edgecolor="white", linewidth=1.5, width=0.62,
    )
    # 값 라벨
    for b, v in zip(bars, values):
        axR.text(
            b.get_x() + b.get_width() / 2,
            v + 0.25,
            f"{v:.2f}×",
            ha="center", va="bottom",
            fontsize=14, fontweight="bold",
        )

    # 4배 격차 annotation — 두 막대 위 양쪽 화살표
    y_top = max(values) + 1.6
    axR.annotate(
        "",
        xy=(0, y_top), xytext=(1, y_top),
        arrowprops=dict(arrowstyle="<->", color="#333333", lw=1.6),
    )
    ratio = values[1] / values[0]
    axR.text(
        0.5, y_top + 0.35,
        f"동일 카테고리 내 {ratio:.1f}배 격차",
        ha="center", va="bottom",
        fontsize=12, fontweight="bold",
        color="#222222",
        bbox=dict(boxstyle="round,pad=0.35", fc="#fff6e0", ec="#d72631", lw=1.2),
    )

    # 도매가 부주석
    axR.text(
        0,
        -0.9,
        f"도매 {fr_sp['wholesale_krw_per_bottle']/1000:.1f}k KRW",
        ha="center", va="top", fontsize=9.5, color="#444444",
    )
    axR.text(
        1,
        -0.9,
        f"도매 {za_sp['wholesale_krw_per_bottle']/1000:.1f}k KRW",
        ha="center", va="top", fontsize=9.5, color="#444444",
    )

    axR.set_ylabel("Markup (retail / wholesale)", fontsize=12)
    axR.set_title(
        "(B) HS 220410 동일 카테고리 — France vs South Africa",
        fontsize=12.5, pad=10,
    )
    axR.set_ylim(0, y_top + 2.0)
    axR.grid(True, axis="y", alpha=0.25, linestyle="--", linewidth=0.7)
    axR.set_axisbelow(True)

    # =================== 전체 타이틀 + 캡션 ===================
    fig.suptitle(
        f"France Champagne {fr_y:.2f}× — Akerlof 정보 비대칭 가설의 직접 입증",
        fontsize=15.5, fontweight="bold", y=0.995,
    )

    caption = (
        "데이터: hs_split.json (11개국 × HS 220410/220421, n=22) — "
        "도매가 = 관세청 USD/kg × 1.2 kg/bottle × 1350 KRW/USD, "
        "소매가 = wine21 국가별 중위가. "
        "동일 HS 220410 안에서 도매가 prior 가 강한 France(1위)가 markup 최저, "
        "도매가 최약자인 South Africa 가 markup 최고 — lemon-market 메커니즘과 정합."
    )
    fig.text(0.5, 0.01, caption, ha="center", fontsize=8.8, color="#555555",
             wrap=True)

    fig.tight_layout(rect=[0, 0.04, 1, 0.95])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return OUT


def main() -> int:
    path = build_figure()
    print(f"Saved: {path}")
    # sanity
    case = _load_case()
    print(
        f"France 220410 markup={case['france_sparkling']['markup']:.3f}×  "
        f"vs S.Africa 220410 markup={case['south_africa_sparkling']['markup']:.3f}×"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
