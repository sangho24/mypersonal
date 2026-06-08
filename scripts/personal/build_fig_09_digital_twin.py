"""Figure F09 — Digital Twin Vision Diagram.

중앙에 "나"를 두고 6개 위성 라벨이 둘러싸며, 바깥 링에 LLM + 도구 조합 메시지,
하단에 비전 슬로건을 배치한 다이어그램.

- Center: "나"
- 6 satellites: 신체 / 위치 / 일상 패턴 / 환경 노출 / 목표·관심사 / 시간 사용
- Outer ring: "LLM 에이전트 + 7 데이터 사이언스 도구가 조합·해석"
- Bottom slogan: "AI 시대, 나만의 특수성·능력을 함께 고민하는 시스템"
- 9 x 7 in, 300 dpi, warm palette.

Output: results/personal/figures/F09_digital_twin.png
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch

OUT_DIR = Path(
    "/Users/sangho/Desktop/빅데이터컴퓨팅/wine-mab-project/results/personal/figures"
)
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "F09_digital_twin.png"

# Warm palette
C_BG = "#FFF8F0"          # warm cream background
C_CENTER = "#B23A1F"      # deep terracotta (center fill)
C_CENTER_EDGE = "#7A2412"
C_SATELLITE = "#E8A05C"   # warm amber (satellite fill)
C_SAT_EDGE = "#B86B1E"
C_LINE = "#C97B3A"        # connector line (warm)
C_RING = "#D89460"        # outer ring
C_RING_TEXT = "#8B4A1E"
C_SLOGAN = "#5C2A0E"      # dark sepia
C_WHITE = "#FFFFFF"
C_TEXT_DARK = "#3A1F0E"


def _setup_korean_font() -> None:
    candidates = ["AppleGothic", "NanumGothic", "Malgun Gothic", "Noto Sans CJK KR"]
    available = {f.name for f in mpl.font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            mpl.rc("font", family=name)
            break
    mpl.rcParams["axes.unicode_minus"] = False


def _draw() -> None:
    fig, ax = plt.subplots(figsize=(9, 7), dpi=300)
    ax.set_xlim(-5.0, 5.0)
    ax.set_ylim(-4.0, 4.0)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(C_BG)
    ax.set_facecolor(C_BG)

    # ──────────────────────────────────────────────────────────────────────
    # Outer ring (text ring) — drawn as a faint annular band
    # ──────────────────────────────────────────────────────────────────────
    outer_r = 3.55
    inner_r = 3.15
    ring = Circle(
        (0.0, 0.0),
        outer_r,
        facecolor=C_RING,
        edgecolor=C_RING_TEXT,
        linewidth=1.2,
        alpha=0.18,
        zorder=0,
    )
    inner_hole = Circle(
        (0.0, 0.0),
        inner_r,
        facecolor=C_BG,
        edgecolor=C_RING_TEXT,
        linewidth=0.8,
        alpha=1.0,
        zorder=1,
    )
    ax.add_patch(ring)
    ax.add_patch(inner_hole)

    # Outer ring label (top of the ring)
    ax.text(
        0.0,
        outer_r - 0.20,
        "LLM 에이전트 + 7 데이터 사이언스 도구가 조합·해석",
        ha="center",
        va="center",
        fontsize=10.5,
        fontweight="bold",
        color=C_RING_TEXT,
        zorder=3,
    )

    # ──────────────────────────────────────────────────────────────────────
    # Satellites — 6 around center
    # ──────────────────────────────────────────────────────────────────────
    satellites = [
        "내 신체 데이터",
        "내 위치 데이터",
        "내 일상 패턴",
        "내 환경 노출",
        "내 목표·관심사",
        "내 시간 사용",
    ]
    sat_radius = 2.35  # distance from center to satellite center
    box_w, box_h = 1.70, 0.62

    # Place satellites starting at 90° (top) going clockwise
    n = len(satellites)
    angles_deg = [90 - i * (360 / n) for i in range(n)]

    # Draw connector lines first (so they sit beneath the boxes)
    center_xy = (0.0, 0.0)
    for ang in angles_deg:
        rad = math.radians(ang)
        x_end = sat_radius * math.cos(rad)
        y_end = sat_radius * math.sin(rad)
        # connector from edge of center circle (~0.75) to edge of satellite box (~0.55 inward)
        cx = 0.78 * math.cos(rad)
        cy = 0.78 * math.sin(rad)
        sx = (sat_radius - 0.45) * math.cos(rad)
        sy = (sat_radius - 0.45) * math.sin(rad)
        ax.plot(
            [cx, sx],
            [cy, sy],
            color=C_LINE,
            linewidth=1.8,
            alpha=0.85,
            solid_capstyle="round",
            zorder=2,
        )
        # subtle dot at satellite end
        ax.plot(
            [x_end],
            [y_end],
            marker="o",
            markersize=4.5,
            markerfacecolor=C_LINE,
            markeredgecolor=C_SAT_EDGE,
            markeredgewidth=0.6,
            zorder=2,
        )

    # Draw satellite boxes
    for ang, label in zip(angles_deg, satellites):
        rad = math.radians(ang)
        x = sat_radius * math.cos(rad)
        y = sat_radius * math.sin(rad)
        box = FancyBboxPatch(
            (x - box_w / 2, y - box_h / 2),
            box_w,
            box_h,
            boxstyle="round,pad=0.02,rounding_size=0.14",
            linewidth=1.4,
            edgecolor=C_SAT_EDGE,
            facecolor=C_SATELLITE,
            alpha=0.95,
            zorder=4,
        )
        ax.add_patch(box)
        ax.text(
            x,
            y,
            label,
            ha="center",
            va="center",
            fontsize=10.5,
            fontweight="bold",
            color=C_TEXT_DARK,
            zorder=5,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Center "나"
    # ──────────────────────────────────────────────────────────────────────
    # subtle outer halo
    halo = Circle(
        (0.0, 0.0),
        0.95,
        facecolor=C_CENTER,
        edgecolor="none",
        alpha=0.18,
        zorder=5,
    )
    ax.add_patch(halo)
    center = Circle(
        (0.0, 0.0),
        0.72,
        facecolor=C_CENTER,
        edgecolor=C_CENTER_EDGE,
        linewidth=2.0,
        zorder=6,
    )
    ax.add_patch(center)
    ax.text(
        0.0,
        0.0,
        "나",
        ha="center",
        va="center",
        fontsize=30,
        fontweight="bold",
        color=C_WHITE,
        zorder=7,
    )

    # ──────────────────────────────────────────────────────────────────────
    # Bottom slogan
    # ──────────────────────────────────────────────────────────────────────
    ax.text(
        0.0,
        -3.78,
        "AI 시대, 나만의 특수성·능력을 함께 고민하는 시스템",
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        color=C_SLOGAN,
        zorder=8,
    )

    fig.tight_layout(pad=0.4)
    fig.savefig(OUT_PATH, dpi=300, bbox_inches="tight", facecolor=C_BG)
    plt.close(fig)


def main() -> int:
    _setup_korean_font()
    _draw()
    print(f"[F09] wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
