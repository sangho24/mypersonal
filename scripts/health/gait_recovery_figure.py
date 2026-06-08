"""Plot the gait quality recovery story (single 6-panel figure).

Panels:
  1. walking_speed monthly (m/s)
  2. step_length monthly (cm)
  3. asymmetry monthly (fraction)  — lower=better
  4. double_support monthly (fraction) — lower=better
  5. walking_steadiness monthly (%) — higher=better
  6. step_count monthly (mean daily)

Each panel overlays:
  - baseline mean (dashed)
  - bottom-out month (red dot)
  - baseline-cross month (green dot)
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

ARTIFACT = Path("/Users/sangho/Desktop/빅데이터컴퓨팅/wine-mab-project/results/logs/gait_recovery.json")
OUT_DIR = Path("/Users/sangho/Desktop/빅데이터컴퓨팅/wine-mab-project/results/figures/eda")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "gait_recovery_v2.png"

PANELS = [
    ("walking_speed",      "Walking speed (m/s)",        +1),
    ("step_length",        "Step length (cm)",           +1),
    ("asymmetry",          "Asymmetry (fraction)",       -1),
    ("double_support",     "Double-support (fraction)",  -1),
    ("walking_steadiness", "Walking steadiness (%)",     +1),
    ("step_count",         "Step count (daily mean)",    +1),
]

ENLIST = datetime(2022, 3, 1)
DISCHARGE = datetime(2023, 12, 1)


def to_dt(ym: str) -> datetime:
    y, m = ym.split("-")
    return datetime(int(y), int(m), 1)


def main() -> None:
    payload = json.loads(ARTIFACT.read_text())
    monthly = payload["monthly"]
    recovery = payload["recovery"]

    fig, axes = plt.subplots(3, 2, figsize=(13, 11), sharex=False)
    axes = axes.flatten()

    for ax, (name, label, direction) in zip(axes, PANELS):
        if name not in monthly:
            ax.set_visible(False); continue
        series = sorted(monthly[name].items())
        xs = [to_dt(k) for k, _ in series]
        ys = [v for _, v in series]
        ax.plot(xs, ys, color="#1f77b4", lw=1.4, marker="o", ms=2.5, label="monthly")
        # Baseline line
        r = recovery.get(name, {})
        if r.get("baseline") is not None:
            ax.axhline(float(r["baseline"]), color="#444", ls="--", lw=0.9,
                       label=f"baseline={float(r['baseline']):.3f}")
        # Bottom & cross markers
        if r.get("bottom_month"):
            bm = to_dt(str(r["bottom_month"]))
            bv = float(r["bottom_value"])
            ax.scatter([bm], [bv], color="#d62728", s=80, zorder=5,
                       label=f"bottom {r['bottom_month']}")
        if r.get("cross_month"):
            cm = to_dt(str(r["cross_month"]))
            cv = float(r["cross_value"])
            ax.scatter([cm], [cv], color="#2ca02c", s=80, zorder=5,
                       label=f"cross {r['cross_month']}")
        # Service shading
        ax.axvspan(ENLIST, DISCHARGE, color="orange", alpha=0.12,
                   label="military service")
        ax.set_title(label, fontsize=11)
        ax.grid(alpha=0.3)
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.legend(fontsize=7, loc="best")

    fig.suptitle("Gait quality recovery — V-curve across 5 gait metrics + step count\n"
                 "(2020-09 .. 2026-06; orange=service span 2021-11-15 to 2023-05-14)",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(OUT_PATH, dpi=150)
    print(f"[ok] figure → {OUT_PATH}")


if __name__ == "__main__":
    main()
