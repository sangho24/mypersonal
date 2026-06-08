"""Figure F05 — 데이터 수집/정제/저장 파이프라인 다이어그램.

필수항목 2 시각화 자료. 박스 + 화살표 다이어그램으로 raw → processed 흐름을
세 단(수집/정제/저장)으로 표현한다. 외부 데이터 없이 matplotlib만으로 그린다.

- Top row "수집":
  Apple Health (export.xml, 216MB), Google Maps Timeline (4.1MB JSON),
  GPX 10개 (workout-routes/)
- Middle row "정제": 5단계 처리 파이프라인
- Bottom row "저장": data/raw/ (원본, .gitignore) → data/processed/personal/*.parquet

Output: results/personal/figures/F05_data_pipeline.png  (11x6 in, 300 dpi)
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


def _setup_korean_font() -> None:
    """Configure matplotlib for Korean labels (macOS/Linux/Windows fallback chain)."""
    candidates = ["AppleGothic", "NanumGothic", "Malgun Gothic", "Noto Sans CJK KR"]
    available = {f.name for f in mpl.font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            mpl.rc("font", family=name)
            break
    mpl.rcParams["axes.unicode_minus"] = False

OUT_DIR = Path(
    "/Users/sangho/Desktop/빅데이터컴퓨팅/wine-mab-project/results/personal/figures"
)
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "F05_data_pipeline.png"

# 색상 팔레트 (수집/정제/저장 = 청/주황/녹)
C_COLLECT = "#3A6EA5"
C_REFINE = "#D88C2A"
C_STORE = "#3F8A56"
C_TEXT = "#1A1A1A"
C_LIGHT_COLLECT = "#E6EEF7"
C_LIGHT_REFINE = "#FBEEDC"
C_LIGHT_STORE = "#E3F1E8"
C_ARROW = "#555555"


def draw_box(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    body: str,
    edgecolor: str,
    facecolor: str,
    title_fontsize: int = 10,
    body_fontsize: int = 8,
) -> None:
    """Rounded box with bold title on top and body text underneath."""
    box = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.4,
        edgecolor=edgecolor,
        facecolor=facecolor,
    )
    ax.add_patch(box)
    ax.text(
        x + w / 2,
        y + h - 0.22,
        title,
        ha="center",
        va="top",
        fontsize=title_fontsize,
        fontweight="bold",
        color=edgecolor,
    )
    ax.text(
        x + w / 2,
        y + h - 0.55,
        body,
        ha="center",
        va="top",
        fontsize=body_fontsize,
        color=C_TEXT,
    )


def draw_arrow(ax, x1: float, y1: float, x2: float, y2: float, *, style: str = "-|>") -> None:
    arr = FancyArrowPatch(
        (x1, y1),
        (x2, y2),
        arrowstyle=style,
        mutation_scale=14,
        linewidth=1.4,
        color=C_ARROW,
    )
    ax.add_patch(arr)


def draw_row_band(
    ax, y: float, h: float, color: str, label: str
) -> None:
    """Faint band behind a row + left label."""
    band = patches.Rectangle(
        (0.0, y),
        16.0,
        h,
        linewidth=0,
        facecolor=color,
        alpha=0.35,
        zorder=0,
    )
    ax.add_patch(band)
    ax.text(
        0.18,
        y + h / 2,
        label,
        ha="left",
        va="center",
        fontsize=12,
        fontweight="bold",
        color="#333333",
        rotation=90,
    )


def main() -> None:
    _setup_korean_font()
    fig, ax = plt.subplots(figsize=(11, 6), dpi=300)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.set_aspect("auto")
    ax.axis("off")

    # ──────────────────────────────────────────────────────────────────────
    # Row bands (top → bottom): 수집 / 정제 / 저장
    # ──────────────────────────────────────────────────────────────────────
    draw_row_band(ax, 6.55, 2.05, C_LIGHT_COLLECT, "수집")
    draw_row_band(ax, 2.55, 3.85, C_LIGHT_REFINE, "정제")
    draw_row_band(ax, 0.20, 2.10, C_LIGHT_STORE, "저장")

    # ──────────────────────────────────────────────────────────────────────
    # Title
    # ──────────────────────────────────────────────────────────────────────
    ax.text(
        8.0,
        8.72,
        "F05 — 개인 데이터 수집·정제·저장 파이프라인",
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
        color="#222222",
    )

    # ──────────────────────────────────────────────────────────────────────
    # Top row: 수집 (3개 소스)
    # ──────────────────────────────────────────────────────────────────────
    src_y = 6.80
    src_h = 1.55
    src_w = 4.20

    draw_box(
        ax,
        x=1.10,
        y=src_y,
        w=src_w,
        h=src_h,
        title="Apple Health (건강앱)",
        body=("export.xml 다운로드\n216 MB · iOS 내보내기\n(HKQuantity / HKWorkout)"),
        edgecolor=C_COLLECT,
        facecolor="white",
    )

    draw_box(
        ax,
        x=5.90,
        y=src_y,
        w=src_w,
        h=src_h,
        title="Google Maps Timeline",
        body=("Location-History.json\n4.1 MB · 위경도 로그\n(국가 판정 입력)"),
        edgecolor=C_COLLECT,
        facecolor="white",
    )

    draw_box(
        ax,
        x=10.70,
        y=src_y,
        w=src_w,
        h=src_h,
        title="GPX 워크아웃 (10개)",
        body=("Apple Health export 내\nworkout-routes/*.gpx\n(러닝/걷기 경로)"),
        edgecolor=C_COLLECT,
        facecolor="white",
    )

    # ──────────────────────────────────────────────────────────────────────
    # Arrows: 수집 → 정제
    # ──────────────────────────────────────────────────────────────────────
    draw_arrow(ax, 3.20, 6.78, 3.20, 6.40)
    draw_arrow(ax, 8.00, 6.78, 8.00, 6.40)
    draw_arrow(ax, 12.80, 6.78, 12.80, 6.40)

    # ──────────────────────────────────────────────────────────────────────
    # Middle row: 정제 (5단계)
    # ──────────────────────────────────────────────────────────────────────
    step_w = 2.85
    step_h = 1.70
    step_y = 3.50
    step_gap = 0.20
    step_x0 = 1.10

    steps = [
        (
            "1. 스트리밍 파싱",
            "xml.etree.iterparse\n(메모리 상수 O(1))\n216 MB → 청크 처리",
        ),
        (
            "2. 일별 aggregate",
            "steps, walking_speed,\nstep_length, asymmetry,\ndouble_support",
        ),
        (
            "3. TZ + 국가 판정",
            "timezone-aware datetime\n좌표 → country\n(bbox hardcode)",
        ),
        (
            "4. sourceName 필터",
            "Sangho / Nike Run Club\n중복 stepCount 차단\n(de-duplication)",
        ),
        (
            "5. 결측 NaN 보존",
            "pre-2020-09 gait 센서\n부재 구간 NaN 유지\n(impute 금지)",
        ),
    ]
    for i, (title, body) in enumerate(steps):
        x = step_x0 + i * (step_w + step_gap)
        draw_box(
            ax,
            x=x,
            y=step_y,
            w=step_w,
            h=step_h,
            title=title,
            body=body,
            edgecolor=C_REFINE,
            facecolor="white",
            title_fontsize=9,
            body_fontsize=7.5,
        )
        # arrows between successive refine steps
        if i < len(steps) - 1:
            x_right = x + step_w
            x_next = x_right + step_gap
            draw_arrow(ax, x_right + 0.01, step_y + step_h / 2, x_next - 0.01, step_y + step_h / 2)

    # ──────────────────────────────────────────────────────────────────────
    # Arrows: 정제 → 저장
    # ──────────────────────────────────────────────────────────────────────
    draw_arrow(ax, 4.50, 3.48, 4.50, 2.30)
    draw_arrow(ax, 11.50, 3.48, 11.50, 2.30)

    # ──────────────────────────────────────────────────────────────────────
    # Bottom row: 저장
    # ──────────────────────────────────────────────────────────────────────
    store_y = 0.55
    store_h = 1.65

    draw_box(
        ax,
        x=1.10,
        y=store_y,
        w=6.60,
        h=store_h,
        title="data/raw/",
        body=(
            "원본 그대로 보존 (재정제 가능성 보장)\n"
            "apple_health/export.xml · google_maps/*.json · gpx/*.gpx\n"
            ".gitignore 처리 — 저장소 외부 보관"
        ),
        edgecolor=C_STORE,
        facecolor="white",
    )

    draw_box(
        ax,
        x=8.30,
        y=store_y,
        w=6.60,
        h=store_h,
        title="data/processed/personal/*.parquet",
        body=(
            "정제 결과 (재현성 보장 / 컬럼형 압축)\n"
            "daily_steps.parquet · gait_daily.parquet ·\n"
            "country_daily.parquet · workouts.parquet"
        ),
        edgecolor=C_STORE,
        facecolor="white",
    )

    # raw → processed 화살표 (저장 단 내부)
    draw_arrow(ax, 7.72, 1.38, 8.28, 1.38)
    ax.text(
        8.00,
        1.62,
        "정제 적용",
        ha="center",
        va="bottom",
        fontsize=7.5,
        color="#555555",
        style="italic",
    )

    # ──────────────────────────────────────────────────────────────────────
    # Footer note
    # ──────────────────────────────────────────────────────────────────────
    ax.text(
        8.0,
        0.18,
        "Architecture rule: data/raw/{site}/{YYYYMMDD}/ 에 원본 보존 · 정제는 data/processed/ 로 분리",
        ha="center",
        va="bottom",
        fontsize=7.5,
        color="#666666",
        style="italic",
    )

    fig.tight_layout(pad=0.4)
    fig.savefig(OUT_PATH, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"saved → {OUT_PATH}")


if __name__ == "__main__":
    main()
