"""Figure 09 — Cumulative regret curves for all 5 MAB policies.

Day 1 baseline (T=200, n_seeds=50, log: results/logs/run_baseline.jsonl) supplies
the 5 standard curves: Oracle / ε-greedy / Thompson / UCB1 c=√2 / Random.

Per Day 2 directive, the UCB1 curve at c=√2 (baseline) is rendered as a dotted
reference, and a NEW UCB1 run at c=c* (the optimal c found by
scripts/analyze_ucb_csweep.py — see results/data/ucb_csweep_summary.json) is
regenerated here at the same (T=200, n_seeds=50) configuration and overlaid as
the solid "UCB1 (c=c*)" line.

Output: results/figures/mab/09_regret_curves.png (8×5 in, 300 dpi).

Run:
    uv run python scripts/build_fig_09_regret.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

# Project root on sys.path so we can import src.mab.* — script is invoked as
# `uv run python scripts/build_fig_09_regret.py`.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.mab.policies import UCB1  # noqa: E402
from src.mab.simulate import (  # noqa: E402
    AVG_WINE_PRICE_KRW,
    _load_rewards_from_reward_module,
    run_experiment,
)

BASELINE_LOG = ROOT / "results" / "logs" / "run_baseline.jsonl"
CSWEEP_SUMMARY = ROOT / "results" / "data" / "ucb_csweep_summary.json"
OUT_PATH = ROOT / "results" / "figures" / "mab" / "09_regret_curves.png"

T_DEFAULT = 200
N_SEEDS_DEFAULT = 50

# Map raw class names in JSONL → display label / color / style.
# Order in this dict drives draw order (later overlays earlier).
POLICY_STYLE: dict[str, dict[str, Any]] = {
    "OraclePolicy": {
        "label": "Oracle",
        "color": "#777777",
        "linestyle": "--",
        "linewidth": 1.4,
        "alpha": 0.9,
        "fill": False,
    },
    "EpsilonGreedy": {
        "label": "ε-greedy (ε=0.1)",
        "color": "#2ca02c",
        "linestyle": "-",
        "linewidth": 1.8,
        "alpha": 1.0,
        "fill": True,
    },
    "ThompsonGauss": {
        "label": "Thompson (Gaussian)",
        "color": "#9467bd",
        "linestyle": "-",
        "linewidth": 1.8,
        "alpha": 1.0,
        "fill": True,
    },
    "UCB1": {
        "label": "UCB1 (c=√2)",
        "color": "#1f77b4",
        "linestyle": ":",
        "linewidth": 1.6,
        "alpha": 0.85,
        "fill": False,
    },
    "UCB1_CSTAR": {
        # Filled in at runtime with actual c*; placeholder here.
        "label": "UCB1 (c=c*)",
        "color": "#0b4f9c",
        "linestyle": "-",
        "linewidth": 2.2,
        "alpha": 1.0,
        "fill": True,
    },
    "RandomPolicy": {
        "label": "Random",
        "color": "#d62728",
        "linestyle": "--",
        "linewidth": 1.6,
        "alpha": 0.9,
        "fill": False,
    },
}

# Legend order (final plot order, top→bottom in legend).
LEGEND_ORDER: list[str] = [
    "OraclePolicy",
    "EpsilonGreedy",
    "ThompsonGauss",
    "UCB1",
    "UCB1_CSTAR",
    "RandomPolicy",
]


def _setup_korean_font() -> None:
    """Configure matplotlib for Korean labels — same pattern as build_fig_07."""
    candidates = ["AppleGothic", "NanumGothic", "Malgun Gothic", "Noto Sans CJK KR"]
    available = {f.name for f in mpl.font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            mpl.rc("font", family=name)
            break
    mpl.rcParams["axes.unicode_minus"] = False


def _load_baseline_curves(
    path: Path, T: int
) -> dict[str, np.ndarray]:
    """Load JSONL log → {policy_name: array of shape (n_seeds, T)}.

    Skips records whose cum_regret_per_t length ≠ T.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"baseline log not found at {path} — run "
            "`uv run python -m src.mab.simulate --T 200 --n-seeds 50 --policies all` first."
        )
    by_policy: dict[str, list[list[float]]] = defaultdict(list)
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            curve = rec["cum_regret_per_t"]
            if len(curve) != T:
                continue
            by_policy[rec["policy_name"]].append(curve)
    return {name: np.asarray(rows, dtype=float) for name, rows in by_policy.items()}


def _load_c_star(path: Path) -> float:
    """Pull c* (optimal UCB constant) from the c-sweep summary JSON."""
    if not path.exists():
        raise FileNotFoundError(
            f"c-sweep summary not found at {path} — run "
            "`uv run python scripts/analyze_ucb_csweep.py` first."
        )
    with path.open(encoding="utf-8") as fh:
        payload = json.load(fh)
    return float(payload["optimal"]["c_star"])


def _regen_ucb_at_cstar(
    c_star: float, T: int, n_seeds: int, base_seed: int = 0
) -> np.ndarray:
    """Run n_seeds × T UCB1 with c=c_star on the production reward env.

    Returns array of shape (n_seeds, T) of cumulative regret curves.
    Uses the same reward loader (`_load_rewards_from_reward_module`) the
    baseline run used, so the environment matches run_baseline.jsonl.
    """
    true_rewards, noise_sigma, _arm_names = _load_rewards_from_reward_module()

    def factory(K: int, rng: np.random.Generator) -> UCB1:
        return UCB1(K=K, c=c_star, rng=rng)

    results = run_experiment(
        policy_factory=factory,
        true_rewards=true_rewards,
        noise_sigma=noise_sigma,
        T=T,
        n_seeds=n_seeds,
        log_path=None,  # do not pollute the baseline log
        base_seed=base_seed,
    )
    curves = np.stack([np.asarray(r["cum_regret_per_t"], dtype=float) for r in results], axis=0)
    return curves


def _aggregate(curves: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """(n_seeds, T) → (mean, std_ddof1, final_mean)."""
    mean = curves.mean(axis=0)
    std = curves.std(axis=0, ddof=1) if curves.shape[0] > 1 else np.zeros_like(mean)
    return mean, std, float(mean[-1])


def _draw(
    series: dict[str, dict[str, Any]],
    c_star: float,
    T: int,
    n_seeds: int,
) -> dict[str, float]:
    """Plot all curves and return {policy_key: final_mean_regret}."""
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    rounds = np.arange(1, T + 1)

    finals: dict[str, float] = {}

    # First pass — draw fills underneath lines so lines stay on top.
    for key in LEGEND_ORDER:
        if key not in series:
            continue
        style = series[key]["style"]
        mean = series[key]["mean"]
        std = series[key]["std"]
        if style.get("fill", False):
            ax.fill_between(
                rounds,
                mean - std,
                mean + std,
                color=style["color"],
                alpha=0.15,
                linewidth=0,
            )

    # Second pass — lines + collect legend handles in the requested order.
    handles: list[Any] = []
    labels: list[str] = []
    for key in LEGEND_ORDER:
        if key not in series:
            continue
        style = series[key]["style"]
        mean = series[key]["mean"]
        finals[key] = float(mean[-1])
        line, = ax.plot(
            rounds,
            mean,
            color=style["color"],
            linestyle=style["linestyle"],
            linewidth=style["linewidth"],
            alpha=style["alpha"],
        )
        handles.append(line)
        labels.append(f"{style['label']} — final {mean[-1]:.2f}")

    # Axes
    ax.set_xlim(0, T)
    ax.set_xlabel("Round t", fontsize=11)
    ax.set_ylabel("Cumulative regret (reward units)", fontsize=11)
    ax.set_title(
        "MAB 누적 regret — random 대비 ε-greedy 87% 감축",
        fontsize=12,
        pad=10,
    )
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.set_axisbelow(True)

    # Right y-axis: KRW = regret × 72,000.
    ax_right = ax.twinx()
    left_lo, left_hi = ax.get_ylim()
    ax_right.set_ylim(left_lo * AVG_WINE_PRICE_KRW, left_hi * AVG_WINE_PRICE_KRW)
    ax_right.set_ylabel(
        f"KRW overpay (×{AVG_WINE_PRICE_KRW:,})", fontsize=11
    )
    # Format right axis as thousands-separated KRW.
    ax_right.yaxis.set_major_formatter(
        mpl.ticker.FuncFormatter(lambda v, _pos: f"{v:,.0f}")
    )

    # Annotate config in a small footer (n_seeds, T, c*).
    footer = (
        f"T={T}, n_seeds={n_seeds}, c*={c_star:.4f} "
        f"(from results/data/ucb_csweep_summary.json)"
    )
    ax.text(
        0.01,
        -0.18,
        footer,
        transform=ax.transAxes,
        fontsize=8,
        color="#555555",
        ha="left",
        va="top",
    )

    ax.legend(
        handles,
        labels,
        loc="upper left",
        fontsize=9,
        framealpha=0.92,
        borderpad=0.6,
    )

    fig.tight_layout()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return finals


def main() -> int:
    _setup_korean_font()
    T = T_DEFAULT
    n_seeds = N_SEEDS_DEFAULT

    print(f"[fig09] loading baseline curves from {BASELINE_LOG}")
    baseline_curves = _load_baseline_curves(BASELINE_LOG, T=T)
    required = {"OraclePolicy", "EpsilonGreedy", "ThompsonGauss", "UCB1", "RandomPolicy"}
    missing = required - set(baseline_curves.keys())
    if missing:
        raise RuntimeError(
            f"baseline log missing policies: {missing}. Found: {list(baseline_curves.keys())}"
        )
    for k, arr in baseline_curves.items():
        print(f"[fig09]   {k:<16s} curves shape={arr.shape}")

    c_star = _load_c_star(CSWEEP_SUMMARY)
    print(f"[fig09] c* = {c_star} — regenerating UCB1 at c=c* with n_seeds={n_seeds}")
    cstar_curves = _regen_ucb_at_cstar(c_star=c_star, T=T, n_seeds=n_seeds)
    print(f"[fig09]   UCB1@c* curves shape={cstar_curves.shape}")

    # Build series dict for _draw.
    series: dict[str, dict[str, Any]] = {}
    for key in ("OraclePolicy", "EpsilonGreedy", "ThompsonGauss", "UCB1", "RandomPolicy"):
        mean, std, _final = _aggregate(baseline_curves[key])
        series[key] = {"mean": mean, "std": std, "style": dict(POLICY_STYLE[key])}

    cstar_mean, cstar_std, _ = _aggregate(cstar_curves)
    cstar_style = dict(POLICY_STYLE["UCB1_CSTAR"])
    cstar_style["label"] = f"UCB1 (c=c*={c_star:g})"
    series["UCB1_CSTAR"] = {"mean": cstar_mean, "std": cstar_std, "style": cstar_style}

    finals = _draw(series=series, c_star=c_star, T=T, n_seeds=n_seeds)

    print(f"[fig09] wrote {OUT_PATH}")
    for k in LEGEND_ORDER:
        if k in finals:
            print(
                f"  {POLICY_STYLE[k]['label']:>22s}  final_regret={finals[k]:7.4f}  "
                f"overpay={finals[k] * AVG_WINE_PRICE_KRW:>12,.0f} KRW"
            )

    # Headline: ε-greedy reduction vs Random.
    eps_final = finals["EpsilonGreedy"]
    rnd_final = finals["RandomPolicy"]
    reduction_pct = 100.0 * (rnd_final - eps_final) / rnd_final if rnd_final > 0 else 0.0
    print(
        f"[fig09] ε-greedy vs Random: {eps_final:.4f} vs {rnd_final:.4f} "
        f"→ reduction {reduction_pct:.1f}%"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
