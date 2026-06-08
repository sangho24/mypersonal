"""Figure 08 — H1 vs H2 mark-up scatter (6-month split robustness).

Source: results/data/robustness.json  (see scripts/analyze_robustness.py)

Plots 11개국 markup_H1 (x) vs markup_H2 (y) as a scatter with:
  - dashed gray y=x reference line
  - per-point Korean country label
  - upper-left annotation: Spearman ρ, p, top-3 overlap (Spain + South Africa fixed)
  - title in Korean

Output: results/figures/eda/08_h1h2_robustness.png  (6×6 inch, 300 dpi)

Run:
    uv run python scripts/build_fig_08_robustness.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

PROJECT_ROOT = Path("/Users/sangho/Desktop/빅데이터컴퓨팅/wine-mab-project")
DATA_PATH = PROJECT_ROOT / "results" / "data" / "robustness.json"
OUT_DIR = PROJECT_ROOT / "results" / "figures" / "eda"
OUT_PATH = OUT_DIR / "08_h1h2_robustness.png"

# Korean font (macOS-friendly; fall back to NanumGothic / Malgun Gothic on other OS).
mpl.rc("font", family="AppleGothic")
mpl.rcParams["axes.unicode_minus"] = False


# --- Per-country label offsets (axis-data units) ----------------------------
# Hand-tuned to avoid overlap between adjacent points on the scatter.
# (dx, dy, ha, va). Defaults to (+0.15, +0.15, "left", "bottom") when missing.
LABEL_OFFSETS: dict[str, tuple[float, float, str, str]] = {
    "프랑스": (+0.20, -0.05, "left", "center"),
    "포르투갈": (-0.20, -0.05, "right", "center"),
    "이탈리아": (+0.20, +0.10, "left", "bottom"),
    "스페인": (-0.20, +0.10, "right", "bottom"),
    "칠레": (+0.20, -0.20, "left", "top"),
    "미국": (+0.20, +0.10, "left", "bottom"),
    "호주": (+0.20, +0.10, "left", "bottom"),
    "뉴질랜드": (+0.20, +0.10, "left", "bottom"),
    "독일": (+0.20, -0.20, "left", "top"),
    "아르헨티나": (-0.20, +0.10, "right", "bottom"),
    "남아프리카": (-0.20, +0.10, "right", "bottom"),
}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    markup_h1: dict[str, float] = payload["markup_H1"]
    markup_h2: dict[str, float] = payload["markup_H2"]
    stats = payload["statistics"]

    countries = list(markup_h1.keys())
    xs = [markup_h1[c] for c in countries]
    ys = [markup_h2[c] for c in countries]

    fig, ax = plt.subplots(figsize=(6, 6), dpi=300)

    # y=x diagonal reference (light gray dashed). Range covers both axes.
    lo = min(min(xs), min(ys)) - 0.5
    hi = max(max(xs), max(ys)) + 0.8
    ax.plot([lo, hi], [lo, hi], color="gray", ls="--", lw=0.9,
            label="y = x (perfect agreement)", zorder=1)

    # Scatter — single accent color, modest size.
    ax.scatter(xs, ys, s=55, color="#1f77b4", edgecolor="white",
               linewidth=0.8, zorder=3)

    # Per-point labels (Korean country names).
    for country, x, y in zip(countries, xs, ys):
        dx, dy, ha, va = LABEL_OFFSETS.get(
            country, (+0.15, +0.15, "left", "bottom")
        )
        ax.annotate(country, xy=(x, y), xytext=(x + dx, y + dy),
                    fontsize=9, ha=ha, va=va, color="#222222", zorder=4)

    # Upper-left annotation — ρ, p, top-3 overlap.
    rho = float(stats["spearman_rho"])
    p = float(stats["spearman_p"])
    overlap_n = int(stats["top3_overlap_count"])
    txt = (
        f"ρ = {rho:.3f}, p = {p:.4f}\n"
        f"top-3 overlap: {overlap_n}/3 (Spain, South Africa fixed)"
    )
    ax.text(0.03, 0.97, txt, transform=ax.transAxes,
            fontsize=9.5, ha="left", va="top",
            bbox=dict(boxstyle="round,pad=0.45", facecolor="white",
                      edgecolor="#888888", linewidth=0.8, alpha=0.92),
            zorder=5)

    # Axes formatting.
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("H1 mark-up (2024.05–2024.10)", fontsize=10.5)
    ax.set_ylabel("H2 mark-up (2024.11–2025.04)", fontsize=10.5)
    ax.set_title("Mark-up 순위 robustness — 6개월 분할 비교",
                 fontsize=12, pad=10)
    ax.grid(True, ls=":", lw=0.5, color="#cccccc", zorder=0)
    ax.tick_params(labelsize=9)

    fig.tight_layout()
    fig.savefig(OUT_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"[OK] wrote {OUT_PATH}  (n={len(countries)} countries, "
          f"ρ={rho:.3f}, p={p:.4f}, top-3 overlap={overlap_n}/3)")


if __name__ == "__main__":
    main()
