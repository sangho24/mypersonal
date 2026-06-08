"""Figure F02 — Two-track pivot diagram (Track A 와인 → Track B 개인 행동).

Schematic figure for the personal-reflection report. Two horizontal branches
share a left node ("발표"); top branch shows what Track A (wine market)
delivered, bottom branch shows what Track B (personal behavior data) became.
A vertical arrow from the shared root highlights the pivot into Track B.

Output: results/personal/figures/F02_two_track.png (9×5 in, 300 dpi).

Run:
    uv run python scripts/personal/build_fig_02_two_track.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_PATH = ROOT / "results" / "personal" / "figures" / "F02_two_track.png"

# Palette — muted, print-friendly
COLOR_ROOT = "#2c3e50"
COLOR_TRACK_A = "#1f4e79"  # navy (wine track)
COLOR_TRACK_A_FILL = "#e7eef5"
COLOR_TRACK_B = "#7a4f8a"  # purple (personal behavior track)
COLOR_TRACK_B_FILL = "#efe8f3"
COLOR_PIVOT = "#c0392b"  # red pivot arrow
COLOR_TEXT = "#1c1c1c"


def _setup_korean_font() -> None:
    """Force AppleGothic for Korean labels (per spec)."""
    candidates = ["AppleGothic", "NanumGothic", "Malgun Gothic", "Noto Sans CJK KR"]
    available = {f.name for f in mpl.font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            mpl.rc("font", family=name)
            break
    mpl.rcParams["axes.unicode_minus"] = False


def _draw_box(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    *,
    edge: str,
    fill: str,
    fontsize: int = 10,
    fontweight: str = "normal",
) -> tuple[float, float, float, float]:
    """Draw a rounded box with centered text; return (x, y, w, h)."""
    box = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.4,
        edgecolor=edge,
        facecolor=fill,
    )
    ax.add_patch(box)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight=fontweight,
        color=COLOR_TEXT,
    )
    return (x, y, w, h)


def _arrow(ax, x1: float, y1: float, x2: float, y2: float, *, color: str, lw: float = 1.6, style: str = "-|>") -> None:
    """Draw an arrow from (x1,y1) to (x2,y2)."""
    arr = FancyArrowPatch(
        (x1, y1),
        (x2, y2),
        arrowstyle=style,
        mutation_scale=14,
        color=color,
        linewidth=lw,
    )
    ax.add_patch(arr)


def _draw() -> None:
    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 10)
    ax.axis("off")

    # --- Root node — 발표 ---
    root_x, root_y, root_w, root_h = 0.4, 4.1, 2.0, 1.8
    _draw_box(
        ax,
        root_x,
        root_y,
        root_w,
        root_h,
        "발표",
        edge=COLOR_ROOT,
        fill="#f4f4f4",
        fontsize=13,
        fontweight="bold",
    )
    root_right_x = root_x + root_w
    root_center_y = root_y + root_h / 2

    # --- Track A — 와인 시장 (top branch) ---
    track_a_y = 7.4
    label_a_x = 3.0
    ax.text(
        label_a_x,
        track_a_y + 1.05,
        "트랙 A — 와인 시장",
        fontsize=11,
        fontweight="bold",
        color=COLOR_TRACK_A,
    )
    a_boxes_text = [
        "관세청 11개국\n+ wine21 970개",
        "r = -0.752",
        "MAB 87% 절감\n(₩909K)",
    ]
    box_w_a, box_h_a = 3.7, 1.5
    gap_a = 0.6
    a_positions = []
    for i, txt in enumerate(a_boxes_text):
        bx = label_a_x + i * (box_w_a + gap_a)
        _draw_box(
            ax,
            bx,
            track_a_y,
            box_w_a,
            box_h_a,
            txt,
            edge=COLOR_TRACK_A,
            fill=COLOR_TRACK_A_FILL,
            fontsize=10,
        )
        a_positions.append((bx, bx + box_w_a))

    # Root → Track A first box
    _arrow(
        ax,
        root_right_x,
        root_center_y + 0.3,
        a_positions[0][0],
        track_a_y + box_h_a / 2,
        color=COLOR_TRACK_A,
        lw=1.8,
    )
    # Inter-box arrows in Track A
    for i in range(len(a_positions) - 1):
        _arrow(
            ax,
            a_positions[i][1],
            track_a_y + box_h_a / 2,
            a_positions[i + 1][0],
            track_a_y + box_h_a / 2,
            color=COLOR_TRACK_A,
            lw=1.6,
        )

    # --- Track B — 개인 행동 데이터 (bottom branch) ---
    track_b_y = 1.1
    label_b_x = 3.0
    ax.text(
        label_b_x,
        track_b_y - 0.55,
        "트랙 B — 개인 행동 데이터",
        fontsize=11,
        fontweight="bold",
        color=COLOR_TRACK_B,
    )
    b_boxes_text = [
        "Apple Health 6년\n+ Timeline 1.3년",
        "7 도구\n+ LLM 오케스트레이터",
        "Hero S1\n부상 감지",
    ]
    box_w_b, box_h_b = 3.7, 1.5
    gap_b = 0.6
    b_positions = []
    for i, txt in enumerate(b_boxes_text):
        bx = label_b_x + i * (box_w_b + gap_b)
        _draw_box(
            ax,
            bx,
            track_b_y,
            box_w_b,
            box_h_b,
            txt,
            edge=COLOR_TRACK_B,
            fill=COLOR_TRACK_B_FILL,
            fontsize=10,
        )
        b_positions.append((bx, bx + box_w_b))

    # Pivot arrow: from root downward into Track B first box (red, highlighted)
    pivot_x_start = root_x + root_w / 2
    pivot_y_start = root_y
    pivot_x_end = b_positions[0][0] + box_w_b / 2
    pivot_y_end = track_b_y + box_h_b
    # Draw an L-shaped pivot route using two arrows for visual clarity
    _arrow(
        ax,
        pivot_x_start,
        pivot_y_start,
        pivot_x_start,
        pivot_y_end + 0.2,
        color=COLOR_PIVOT,
        lw=2.2,
        style="-",
    )
    _arrow(
        ax,
        pivot_x_start,
        pivot_y_end + 0.2,
        pivot_x_end,
        pivot_y_end,
        color=COLOR_PIVOT,
        lw=2.2,
    )
    # Pivot label
    ax.text(
        (pivot_x_start + pivot_x_end) / 2,
        pivot_y_end + 0.45,
        "피벗",
        ha="center",
        va="bottom",
        fontsize=11,
        fontweight="bold",
        color=COLOR_PIVOT,
    )

    # Inter-box arrows in Track B
    for i in range(len(b_positions) - 1):
        _arrow(
            ax,
            b_positions[i][1],
            track_b_y + box_h_b / 2,
            b_positions[i + 1][0],
            track_b_y + box_h_b / 2,
            color=COLOR_TRACK_B,
            lw=1.6,
        )

    # Title
    ax.text(
        9.0,
        9.55,
        "두 트랙의 분기 — 발표 이후 개인 행동 데이터로 피벗",
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
        color=COLOR_TEXT,
    )

    fig.tight_layout()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    _setup_korean_font()
    _draw()
    print(f"[F02] wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
