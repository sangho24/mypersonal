"""Figure 07 — Mark-up by Country × HS code (still 220421 vs sparkling 220410).

Reads results/data/hs_split.json (produced by scripts/analyze_champagne.py),
emits a grouped horizontal bar chart with 11 countries × 2 HS codes.

Output: results/figures/eda/07_hs_split.png (8×6 in, 300 dpi).

Run:
    uv run python scripts/build_fig_07_hs_split.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "results" / "data" / "hs_split.json"
OUT_PATH = ROOT / "results" / "figures" / "eda" / "07_hs_split.png"

# Color spec — navy still, gold sparkling
COLOR_STILL = "#1f4e79"
COLOR_SPARKLING = "#d4a017"

# HS code constants (per data dictionary)
HS_STILL = 220421
HS_SPARKLING = 220410


def _setup_korean_font() -> None:
    """Configure matplotlib for Korean labels.

    Tries platform-typical Korean fonts in order; the first one that resolves
    is used. ``axes.unicode_minus`` is disabled so the minus sign renders.
    """
    candidates = ["AppleGothic", "NanumGothic", "Malgun Gothic", "Noto Sans CJK KR"]
    available = {f.name for f in mpl.font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            mpl.rc("font", family=name)
            break
    mpl.rcParams["axes.unicode_minus"] = False


def _load_rows() -> list[dict]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"hs_split.json not found at {DATA_PATH}. "
            "Run `uv run python scripts/analyze_champagne.py` first."
        )
    with DATA_PATH.open(encoding="utf-8") as fh:
        payload = json.load(fh)
    return payload["rows"]


def _build_country_table(rows: list[dict]) -> list[dict]:
    """Collapse rows -> per-country dict with still + sparkling markup."""
    by_country: dict[str, dict[str, float]] = {}
    for row in rows:
        country = row["country"]
        slot = by_country.setdefault(country, {})
        if row["hs_code"] == HS_STILL:
            slot["still"] = float(row["markup"])
        elif row["hs_code"] == HS_SPARKLING:
            slot["sparkling"] = float(row["markup"])
    table = [
        {"country": c, "still": v.get("still", np.nan), "sparkling": v.get("sparkling", np.nan)}
        for c, v in by_country.items()
    ]
    # Sort by still markup DESCENDING — top of plot (y largest) = highest still markup
    table.sort(key=lambda r: r["still"], reverse=True)
    return table


def _draw(table: list[dict]) -> None:
    countries = [r["country"] for r in table]
    still_vals = np.array([r["still"] for r in table])
    sparkling_vals = np.array([r["sparkling"] for r in table])

    n = len(countries)
    # y positions: 0..n-1; for horizontal sorting "Spain at top" we flip so
    # index 0 (highest still markup) ends up at the top of the figure.
    y_base = np.arange(n)[::-1].astype(float)
    bar_height = 0.38
    offset = bar_height / 2

    fig, ax = plt.subplots(figsize=(8, 6), dpi=300)

    ax.barh(
        y_base + offset,
        still_vals,
        height=bar_height,
        color=COLOR_STILL,
        label="Still (HS 220421)",
        edgecolor="white",
        linewidth=0.5,
    )
    ax.barh(
        y_base - offset,
        sparkling_vals,
        height=bar_height,
        color=COLOR_SPARKLING,
        label="Sparkling (HS 220410)",
        edgecolor="white",
        linewidth=0.5,
    )

    ax.set_yticks(y_base)
    ax.set_yticklabels(countries, fontsize=10)
    ax.set_xlim(0, 13)
    ax.set_xlabel("Mark-up (retail ÷ wholesale, ×)", fontsize=11)
    ax.set_title(
        "Mark-up by Country × HS code (still 220421 vs sparkling 220410)",
        fontsize=12,
        pad=12,
    )
    ax.grid(axis="x", linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="lower right", fontsize=10, framealpha=0.9)

    # Annotation 1 — France sparkling = lowest sparkling markup
    france_idx = next(i for i, r in enumerate(table) if r["country"] == "프랑스")
    fr_y = y_base[france_idx] - offset
    fr_x = sparkling_vals[france_idx]
    ax.annotate(
        "2.82× — lowest",
        xy=(fr_x, fr_y),
        xytext=(fr_x + 3.5, fr_y - 0.55),
        fontsize=9,
        color="#c0392b",
        arrowprops={
            "arrowstyle": "->",
            "color": "#c0392b",
            "lw": 1.2,
            "connectionstyle": "arc3,rad=0.15",
        },
    )

    # Annotation 2 — South Africa sparkling = 11.53× (highest sparkling)
    sa_idx = next(i for i, r in enumerate(table) if r["country"] == "남아프리카")
    sa_y = y_base[sa_idx] - offset
    sa_x = sparkling_vals[sa_idx]
    ax.annotate(
        "11.53×",
        xy=(sa_x, sa_y),
        xytext=(sa_x - 4.0, sa_y - 0.6),
        fontsize=9,
        color="#7a5c00",
        arrowprops={
            "arrowstyle": "->",
            "color": "#7a5c00",
            "lw": 1.2,
            "connectionstyle": "arc3,rad=-0.2",
        },
    )

    fig.tight_layout()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    _setup_korean_font()
    rows = _load_rows()
    table = _build_country_table(rows)
    _draw(table)
    print(f"[fig07] wrote {OUT_PATH} (countries={len(table)})")
    for r in table:
        print(
            f"  {r['country']:>6s}  still={r['still']:5.2f}x  sparkling={r['sparkling']:5.2f}x"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
