"""Figure 11 — UCB1 c-constant sensitivity curve.

입력: results/data/ucb_csweep_summary.json (scripts/analyze_ucb_csweep.py 산출물)
출력: results/figures/mab/11_ucb_csweep.png

Spec:
  - Figure 6×4 inch, 300dpi
  - log-scaled x = c, y = mean_cum_regret (std error bars)
  - horizontal dashed: ε-greedy / Random regret level
  - vertical: c* (optimal) + √2 (default)
  - 한글 타이틀 — AppleGothic
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

# 한글 폰트 + 마이너스 기호
mpl.rc("font", family="AppleGothic")
mpl.rcParams["axes.unicode_minus"] = False

_ROOT = Path(__file__).resolve().parents[1]
_INPUT = _ROOT / "results" / "data" / "ucb_csweep_summary.json"
_OUTPUT = _ROOT / "results" / "figures" / "mab" / "11_ucb_csweep.png"


def _baseline_regret(baselines: list[dict], name_prefix: str) -> float | None:
    for b in baselines:
        if b["policy_name"].startswith(name_prefix):
            return float(b["mean_cum_regret"])
    return None


def main() -> Path:
    with _INPUT.open("r", encoding="utf-8") as fh:
        summary = json.load(fh)

    sweep = summary["ucb_sweep"]
    baselines = summary["baselines"]
    optimal = summary["optimal"]

    cs = np.array([row["c"] for row in sweep], dtype=float)
    means = np.array([row["mean_cum_regret"] for row in sweep], dtype=float)
    stds = np.array([row["std_cum_regret"] for row in sweep], dtype=float)

    eps_regret = _baseline_regret(baselines, "epsilon_greedy")
    random_regret = _baseline_regret(baselines, "random")

    c_star = float(optimal["c_star"])
    regret_at_c_star = float(optimal["mean_cum_regret_at_c_star"])
    sqrt2 = float(np.sqrt(2.0))

    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6, 4), dpi=300)

    # main curve — UCB1 sweep
    ax.errorbar(
        cs,
        means,
        yerr=stds,
        marker="o",
        markersize=5,
        linewidth=1.8,
        capsize=3,
        color="#1f77b4",
        label="UCB1 (sweep)",
        zorder=3,
    )

    # horizontal reference lines (ε-greedy, Random)
    if eps_regret is not None:
        ax.axhline(
            eps_regret,
            color="#2ca02c",
            linestyle="--",
            linewidth=1.2,
            alpha=0.85,
            label=f"ε-greedy = {eps_regret:.2f}",
            zorder=2,
        )
    if random_regret is not None:
        ax.axhline(
            random_regret,
            color="#7f7f7f",
            linestyle="--",
            linewidth=1.2,
            alpha=0.85,
            label=f"Random = {random_regret:.2f}",
            zorder=2,
        )

    # vertical line at c* (optimal)
    ax.axvline(c_star, color="#d62728", linestyle="-", linewidth=1.2, alpha=0.85, zorder=2)
    ax.annotate(
        f"c* = {c_star:g}, regret = {regret_at_c_star:.2f}",
        xy=(c_star, regret_at_c_star),
        xytext=(8, 14),
        textcoords="offset points",
        fontsize=8,
        color="#d62728",
        arrowprops=dict(arrowstyle="->", color="#d62728", lw=0.8),
    )

    # vertical line at default √2
    ax.axvline(sqrt2, color="#ff7f0e", linestyle=":", linewidth=1.2, alpha=0.85, zorder=2)
    # find regret at √2 for annotation positioning
    sqrt2_idx = int(np.argmin(np.abs(cs - sqrt2)))
    ax.annotate(
        "default √2 = 1.414",
        xy=(sqrt2, means[sqrt2_idx]),
        xytext=(-95, -28),
        textcoords="offset points",
        fontsize=8,
        color="#ff7f0e",
        arrowprops=dict(arrowstyle="->", color="#ff7f0e", lw=0.8),
    )

    ax.set_xscale("log")
    ax.set_xlim(0.08, 6.5)
    ax.set_xlabel("c (탐색 상수, log-scale)")
    ax.set_ylabel("mean cumulative regret @ T=200")
    ax.set_title(
        "UCB1 c-constant 민감도 — 기본값 √2는 11-arm × T=200 환경에서 과탐색",
        fontsize=10,
    )
    ax.grid(True, which="both", linestyle=":", linewidth=0.5, alpha=0.5)
    ax.legend(loc="lower right", fontsize=8, framealpha=0.9)

    fig.tight_layout()
    fig.savefig(_OUTPUT, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"saved: {_OUTPUT}")
    return _OUTPUT


if __name__ == "__main__":
    main()
