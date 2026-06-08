"""Figure F03 — Personal life timeline 2019-2026.

Horizontal timeline marking major personal life events on a single x-axis,
shared as scaffolding for the per-slide behavioral signals that follow.
모든 날짜는 src.personal.anchors 의 SoT 에서 import — 하드코딩 금지.

Privacy: no coordinates, no 부대명.

Output: results/personal/figures/F03_personal_timeline.png (12×4 in, 300 dpi).

Run:
    PYTHONPATH=. uv run python scripts/personal/build_fig_03_personal_timeline.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import matplotlib as mpl
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from src.personal.anchors import (
    ACL_INJURY,
    ACL_SURGERY,
    ENROLLMENT,
    MIL_END,
    MIL_START,
    PARIS_END,
    PARIS_START,
    SEOUL_REC_START,
)

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_PATH = ROOT / "results" / "personal" / "figures" / "F03_personal_timeline.png"

# Palette
COLOR_AXIS = "#1c1c1c"
COLOR_EVENT = "#2c3e50"
COLOR_MILITARY = "#7a4f8a"  # purple — service period
COLOR_MILITARY_FILL = "#efe8f3"
COLOR_FRANCE = "#1f4e79"  # navy — exchange period
COLOR_FRANCE_FILL = "#e7eef5"
COLOR_PREP = "#c0392b"  # red — grad/job prep period
COLOR_PREP_FILL = "#fbeae6"
COLOR_TEXT = "#1c1c1c"
COLOR_TAKEAWAY = "#555555"


def _setup_korean_font() -> None:
    """Force AppleGothic for Korean labels (per spec)."""
    candidates = ["AppleGothic", "NanumGothic", "Malgun Gothic", "Noto Sans CJK KR"]
    available = {f.name for f in mpl.font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            mpl.rc("font", family=name)
            break
    mpl.rcParams["axes.unicode_minus"] = False


def _draw() -> None:
    fig, ax = plt.subplots(figsize=(12, 4), dpi=300)

    # Date range
    t_start = date(2019, 1, 1)
    t_end = date(2026, 12, 31)
    today = date(2026, 6, 8)

    ax.set_xlim(mdates.date2num(t_start), mdates.date2num(t_end))
    ax.set_ylim(-1.0, 1.6)

    # Spine — only bottom (the timeline axis itself)
    for side in ("top", "left", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(COLOR_AXIS)
    ax.spines["bottom"].set_linewidth(1.2)
    ax.spines["bottom"].set_position(("data", 0))

    # Yearly ticks
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(axis="x", colors=COLOR_AXIS, labelsize=10, length=5)
    ax.set_yticks([])

    # --- Period shadings (light) — anchors.py SoT 그대로 ---
    # Military service: MIL_START ~ MIL_END
    mil_start = mdates.date2num(MIL_START)
    mil_end = mdates.date2num(MIL_END)
    ax.add_patch(
        Rectangle(
            (mil_start, -0.5),
            mil_end - mil_start,
            1.0,
            facecolor=COLOR_MILITARY_FILL,
            edgecolor="none",
            alpha=0.7,
            zorder=0,
        )
    )
    ax.text(
        (mil_start + mil_end) / 2,
        -0.78,
        "군 복무",
        ha="center",
        va="top",
        fontsize=9,
        color=COLOR_MILITARY,
        fontweight="bold",
    )

    # France exchange: PARIS_START ~ PARIS_END
    fr_start = mdates.date2num(PARIS_START)
    fr_end = mdates.date2num(PARIS_END)
    ax.add_patch(
        Rectangle(
            (fr_start, -0.5),
            fr_end - fr_start,
            1.0,
            facecolor=COLOR_FRANCE_FILL,
            edgecolor="none",
            alpha=0.8,
            zorder=0,
        )
    )
    ax.text(
        (fr_start + fr_end) / 2,
        -0.78,
        "프랑스 교환",
        ha="center",
        va="top",
        fontsize=9,
        color=COLOR_FRANCE,
        fontweight="bold",
    )

    # Grad/job prep: SEOUL_REC_START ~ now
    prep_start = mdates.date2num(SEOUL_REC_START)
    prep_end = mdates.date2num(today)
    ax.add_patch(
        Rectangle(
            (prep_start, -0.5),
            prep_end - prep_start,
            1.0,
            facecolor=COLOR_PREP_FILL,
            edgecolor="none",
            alpha=0.7,
            zorder=0,
        )
    )
    ax.text(
        (prep_start + prep_end) / 2,
        -0.78,
        "졸업/취업 준비기",
        ha="center",
        va="top",
        fontsize=9,
        color=COLOR_PREP,
        fontweight="bold",
    )

    # --- Event markers (vertical lines + labels above axis) — anchors.py SoT ---
    events: list[tuple[date, str, float, str]] = [
        (ENROLLMENT, "대학 입학\n(1학년 시작)", 1.30, "left"),
        (MIL_START, "군 입대", 0.55, "center"),
        (MIL_END, "군 전역", 1.05, "center"),
        (ACL_INJURY, "ACL 부상", 0.55, "left"),
        (ACL_SURGERY, "ACL 수술", 1.30, "left"),
        (PARIS_START, "프랑스 교환 출국", 0.55, "right"),
        (PARIS_END, "한국 귀국", 1.05, "left"),
        (today, "현재", 0.55, "right"),
    ]

    for ev_date, label, y_label, ha in events:
        x = mdates.date2num(ev_date)
        # Vertical marker line (above axis up to label)
        ax.plot(
            [x, x],
            [0, y_label - 0.06],
            color=COLOR_EVENT,
            linewidth=1.0,
            linestyle="-",
            alpha=0.7,
            zorder=2,
        )
        # Marker dot on the axis
        ax.plot(
            x,
            0,
            marker="o",
            markersize=5,
            markerfacecolor=COLOR_EVENT,
            markeredgecolor="white",
            markeredgewidth=0.8,
            zorder=3,
        )
        # Label above, anchored to event date in data coords
        ax.text(
            x,
            y_label,
            label,
            ha=ha,
            va="bottom",
            fontsize=9,
            color=COLOR_TEXT,
            fontweight="bold",
            zorder=4,
        )

    # Title
    ax.set_title(
        "개인 생애 타임라인 (2019 - 2026)",
        fontsize=13,
        fontweight="bold",
        color=COLOR_TEXT,
        pad=12,
    )

    # One-line takeaway at bottom
    fig.text(
        0.5,
        0.02,
        "이 timeline 위에서 *데이터로 어떤 신호가 보이는가*를 다음 슬라이드부터",
        ha="center",
        va="bottom",
        fontsize=10,
        color=COLOR_TAKEAWAY,
        style="italic",
    )

    fig.tight_layout(rect=(0, 0.05, 1, 1))
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    _setup_korean_font()
    _draw()
    print(f"[F03] wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
