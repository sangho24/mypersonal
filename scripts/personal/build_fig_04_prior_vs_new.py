"""Figure F04 — Prior (차용) vs New (신규) contributions for the personal track.

A two-column comparison panel that makes the *boundary* between reused assets
and this final project's actual contribution explicit. Left column lists
prior work that is carried over verbatim from the wine-mab track plus the
canonical SciPy / Anthropic SDK pieces; right column lists the new modules,
tools, orchestrator pieces, and report deliverables that this final project
adds.

Output: results/personal/figures/F04_prior_vs_new.png (11x6 in, 300 dpi).

Run:
    uv run python scripts/personal/build_fig_04_prior_vs_new.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_PATH = ROOT / "results" / "personal" / "figures" / "F04_prior_vs_new.png"

# Color spec — muted slate-blue for prior, warm coral for new contribution
COLOR_PRIOR_BG = "#eef2f7"
COLOR_PRIOR_BORDER = "#37527a"
COLOR_PRIOR_HEADER = "#37527a"
COLOR_PRIOR_TEXT = "#1a2740"

COLOR_NEW_BG = "#fdecea"
COLOR_NEW_BORDER = "#c0392b"
COLOR_NEW_HEADER = "#c0392b"
COLOR_NEW_TEXT = "#6b1a14"

COLOR_FOOTER = "#444444"

PRIOR_TITLE = "차용 (Prior)"
NEW_TITLE = "신규 (New in this final project)"

PRIOR_ITEMS: list[tuple[str, str]] = [
    ("wine-mab src/mab UCB1", "직접 구현된 numpy 기반 UCB1 (와인 트랙 phase 4)"),
    ("scipy.stats / numpy / sklearn LinearRegression", "통계 검정 · 수치 연산 · 회귀 표준 라이브러리"),
    ("Apple Health / Google Timeline export 포맷", "외부 표준 export 스키마 — 그대로 파싱"),
    ("Anthropic SDK", "wine PRD에 optional로 명시된 LLM 호출 인터페이스"),
]

NEW_ITEMS: list[tuple[str, str]] = [
    ("src/personal/ 전체 모듈", "data 로더 + 7개 tool + agent 오케스트레이터"),
    ("T1~T7 callable tools", "강의 §3.1/§3.2/§3.3/§3.6/§4 + UCB1 흡수"),
    ("LLM 오케스트레이터", "Anthropic tool_use loop + system prompt 설계"),
    ("Hero S1 시나리오 + 6 figure", "DECK_PLAN / SLIDES / REPORT 산출물"),
]

FOOTER_TEXT = "와인 자산은 명시적으로 *재사용*, 본 프로젝트 *기여*는 개인 트랙 전체"


def _setup_korean_font() -> None:
    """Configure matplotlib for Korean labels."""
    candidates = ["AppleGothic", "NanumGothic", "Malgun Gothic", "Noto Sans CJK KR"]
    available = {f.name for f in mpl.font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            mpl.rc("font", family=name)
            break
    mpl.rcParams["axes.unicode_minus"] = False


def _draw_column(
    ax: plt.Axes,
    title: str,
    items: list[tuple[str, str]],
    bg: str,
    border: str,
    header: str,
    text: str,
) -> None:
    """Render a single column (title header + N item cards) onto ax.

    ax is expected to span [0, 1] x [0, 1] in axis coords; we lay items out
    top-to-bottom inside that box.
    """
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_axis_off()

    # Outer panel
    panel = mpatches.FancyBboxPatch(
        (0.02, 0.02),
        0.96,
        0.96,
        boxstyle="round,pad=0.01,rounding_size=0.02",
        linewidth=1.6,
        edgecolor=border,
        facecolor="white",
    )
    ax.add_patch(panel)

    # Header band
    header_band = mpatches.FancyBboxPatch(
        (0.04, 0.86),
        0.92,
        0.10,
        boxstyle="round,pad=0.005,rounding_size=0.015",
        linewidth=0,
        facecolor=header,
    )
    ax.add_patch(header_band)
    ax.text(
        0.5,
        0.91,
        title,
        ha="center",
        va="center",
        fontsize=15,
        fontweight="bold",
        color="white",
    )

    # Item cards
    n = len(items)
    region_top = 0.82
    region_bottom = 0.06
    gap = 0.018
    card_h = (region_top - region_bottom - gap * (n - 1)) / n

    for i, (name, detail) in enumerate(items):
        top = region_top - i * (card_h + gap)
        bottom = top - card_h
        card = mpatches.FancyBboxPatch(
            (0.05, bottom),
            0.90,
            card_h,
            boxstyle="round,pad=0.005,rounding_size=0.012",
            linewidth=0.8,
            edgecolor=border,
            facecolor=bg,
        )
        ax.add_patch(card)
        mid = (top + bottom) / 2
        # Title line
        ax.text(
            0.08,
            mid + card_h * 0.18,
            f"• {name}",
            ha="left",
            va="center",
            fontsize=11.5,
            fontweight="bold",
            color=text,
        )
        # Detail line
        ax.text(
            0.10,
            mid - card_h * 0.22,
            detail,
            ha="left",
            va="center",
            fontsize=9.8,
            color=text,
        )


def _draw() -> None:
    fig = plt.figure(figsize=(11, 6), dpi=300)

    # Suptitle
    fig.suptitle(
        "필수항목 1 — 차용 자산(좌) vs 본 프로젝트 신규 기여(우)",
        fontsize=14,
        fontweight="bold",
        y=0.97,
    )

    # Two column axes, leaving room for footer
    left_ax = fig.add_axes((0.03, 0.10, 0.46, 0.83))
    right_ax = fig.add_axes((0.51, 0.10, 0.46, 0.83))

    _draw_column(
        left_ax,
        PRIOR_TITLE,
        PRIOR_ITEMS,
        bg=COLOR_PRIOR_BG,
        border=COLOR_PRIOR_BORDER,
        header=COLOR_PRIOR_HEADER,
        text=COLOR_PRIOR_TEXT,
    )
    _draw_column(
        right_ax,
        NEW_TITLE,
        NEW_ITEMS,
        bg=COLOR_NEW_BG,
        border=COLOR_NEW_BORDER,
        header=COLOR_NEW_HEADER,
        text=COLOR_NEW_TEXT,
    )

    # Footer line
    fig.text(
        0.5,
        0.045,
        FOOTER_TEXT,
        ha="center",
        va="center",
        fontsize=10.5,
        color=COLOR_FOOTER,
        style="italic",
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> int:
    _setup_korean_font()
    _draw()
    print(f"[figF04] wrote {OUT_PATH}")
    print(f"  prior items: {len(PRIOR_ITEMS)}")
    print(f"  new items:   {len(NEW_ITEMS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
