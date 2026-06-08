"""UCB1 c-constant sensitivity sweep — phase 04 / 05 후속 분석.

Day 1 베이스라인에서 UCB1 (c=√2≈1.414) 의 mean_cum_regret 이 13.67 로 Random(14.86)
과 유사한 수준이었다. 11-arm × T=200 × 고-SNR (σ≈0.02) 환경에서는 c=√2 가 과도하게
탐험(over-exploration)한다는 가설을 검증하기 위해 c ∈ [0.1, 5.0] 범위를 sweep 한다.

Algorithm:
  1) src.mab.reward 에서 실제 mark-up 기반 (true_rewards, noise_sigma, arm_names) 로딩
     - 데이터 부재 시 simulate._load_rewards_from_reward_module 의 폴백 사용
  2) c ∈ {0.1, 0.25, 0.5, 0.7, 1.0, √2, 2.0, 3.0, 5.0} (9 values)
  3) 각 c 마다 n_seeds=20 × T=200 으로 run_experiment → final cum_regret 통계
  4) 비교용 베이스라인 (ε-greedy, ThompsonGauss, RandomPolicy, OraclePolicy) 도 동시 실행
  5) JSONL (raw) + JSON (summary) 저장
  6) c* = argmin(mean_cum_regret) 식별, KRW 환산 overpay 표시 (×72,000)

Outputs:
  - results/logs/ucb_csweep.jsonl       (시드별 raw 결과 — run_experiment 로깅)
  - results/data/ucb_csweep_summary.json (c-별 + 베이스라인 summary)

Usage:
    uv run python scripts/analyze_ucb_csweep.py
    uv run python scripts/analyze_ucb_csweep.py --smoke   # T=50, n_seeds=3 quick
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

# 프로젝트 루트를 sys.path 에 추가 — `uv run python scripts/...` 호출용
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.mab.policies import (  # noqa: E402
    EpsilonGreedy,
    OraclePolicy,
    RandomPolicy,
    ThompsonGauss,
    UCB1,
)
from src.mab.simulate import (  # noqa: E402
    AVG_WINE_PRICE_KRW,
    _load_rewards_from_reward_module,
    run_experiment,
)

# 보고서 §3.7 본문 / Day 2 plan 의 기본 sweep 그리드
DEFAULT_C_GRID: list[float] = [
    0.1,
    0.25,
    0.5,
    0.7,
    1.0,
    float(np.sqrt(2.0)),  # ≈ 1.4142 — Auer et al. 2002 기본값
    2.0,
    3.0,
    5.0,
]


def _summarize_finals(finals: np.ndarray) -> dict[str, float]:
    """final cumulative regret 배열 → 평균/표준편차/KRW overpay summary."""
    mean = float(finals.mean())
    std = float(finals.std(ddof=1)) if finals.size > 1 else 0.0
    return {
        "mean_cum_regret": mean,
        "std_cum_regret": std,
        "min_cum_regret": float(finals.min()),
        "max_cum_regret": float(finals.max()),
        "mean_overpay_krw": mean * AVG_WINE_PRICE_KRW,
    }


def _run_ucb_for_c(
    c: float,
    true_rewards: np.ndarray,
    noise_sigma: np.ndarray,
    T: int,
    n_seeds: int,
    log_path: Path | None,
    base_seed: int,
) -> dict[str, Any]:
    """단일 c 값에 대해 n_seeds × T 실험 후 summary dict 반환."""
    def factory(K: int, rng: np.random.Generator) -> UCB1:
        return UCB1(K=K, c=c, rng=rng)

    results = run_experiment(
        policy_factory=factory,
        true_rewards=true_rewards,
        noise_sigma=noise_sigma,
        T=T,
        n_seeds=n_seeds,
        log_path=log_path,
        base_seed=base_seed,
    )
    finals = np.array([r["cum_regret_per_t"][-1] for r in results], dtype=float)
    summary = _summarize_finals(finals)
    summary["c"] = float(c)
    summary["policy_name"] = f"ucb1_c{c:.4f}"
    summary["n_seeds"] = int(n_seeds)
    summary["T"] = int(T)
    return summary


def _run_baseline(
    name: str,
    factory: Any,
    true_rewards: np.ndarray,
    noise_sigma: np.ndarray,
    T: int,
    n_seeds: int,
    log_path: Path | None,
    base_seed: int,
) -> dict[str, Any]:
    """베이스라인(ε-greedy / Thompson / Random / Oracle) summary."""
    results = run_experiment(
        policy_factory=factory,
        true_rewards=true_rewards,
        noise_sigma=noise_sigma,
        T=T,
        n_seeds=n_seeds,
        log_path=log_path,
        base_seed=base_seed,
    )
    finals = np.array([r["cum_regret_per_t"][-1] for r in results], dtype=float)
    summary = _summarize_finals(finals)
    summary["policy_name"] = name
    summary["n_seeds"] = int(n_seeds)
    summary["T"] = int(T)
    return summary


def run_sweep(
    c_grid: list[float],
    T: int = 200,
    n_seeds: int = 20,
    base_seed: int = 0,
    out_jsonl: Path | None = None,
    out_summary: Path | None = None,
    include_baselines: bool = True,
) -> dict[str, Any]:
    """UCB c-sweep 본체. 모든 c 와 (옵션) 베이스라인을 동일 환경에서 비교."""
    true_rewards, noise_sigma, arm_names = _load_rewards_from_reward_module()
    K = len(true_rewards)
    best_arm = int(np.argmax(true_rewards))
    print(f"[csweep] K={K} arms — best=[{best_arm}] {arm_names[best_arm]}")
    print(
        f"[csweep] reward range=[{true_rewards.min():.4f}, {true_rewards.max():.4f}], "
        f"σ range=[{noise_sigma.min():.4f}, {noise_sigma.max():.4f}]"
    )
    print(f"[csweep] T={T}, n_seeds={n_seeds}, c_grid={[round(c, 4) for c in c_grid]}")

    # 로그 파일은 sweep 시작 시 초기화 (기존 파일 덮어쓰기)
    if out_jsonl is not None:
        out_jsonl.parent.mkdir(parents=True, exist_ok=True)
        if out_jsonl.exists():
            out_jsonl.unlink()

    # ----- 1) UCB1 c-sweep -----
    ucb_rows: list[dict[str, Any]] = []
    for i, c in enumerate(c_grid):
        # c 별 base_seed 를 다르게 두어 동일 시드 재사용 시 노이즈 상쇄 방지
        # (단, 환경 자체는 고정 — 결과를 c 간 직접 비교 가능)
        c_base_seed = base_seed + i * n_seeds
        summary = _run_ucb_for_c(
            c=c,
            true_rewards=true_rewards,
            noise_sigma=noise_sigma,
            T=T,
            n_seeds=n_seeds,
            log_path=out_jsonl,
            base_seed=c_base_seed,
        )
        ucb_rows.append(summary)
        print(
            f"[csweep] c={c:>6.4f}  mean_regret={summary['mean_cum_regret']:7.4f} "
            f"± {summary['std_cum_regret']:.4f}  overpay_krw={summary['mean_overpay_krw']:>12,.0f}"
        )

    # ----- 2) Baselines -----
    baseline_rows: list[dict[str, Any]] = []
    if include_baselines:
        baseline_specs: dict[str, Any] = {
            "epsilon_greedy_0.1": lambda K, rng: EpsilonGreedy(K=K, epsilon=0.1, rng=rng),
            "thompson_gauss": lambda K, rng: ThompsonGauss(K=K, rng=rng),
            "random": lambda K, rng: RandomPolicy(K=K, rng=rng),
            "oracle": lambda K, rng: OraclePolicy(K=K, true_rewards=true_rewards, rng=rng),
        }
        offset = len(c_grid) * n_seeds
        for j, (name, fac) in enumerate(baseline_specs.items()):
            b_seed = base_seed + offset + j * n_seeds
            summary = _run_baseline(
                name=name,
                factory=fac,
                true_rewards=true_rewards,
                noise_sigma=noise_sigma,
                T=T,
                n_seeds=n_seeds,
                log_path=out_jsonl,
                base_seed=b_seed,
            )
            baseline_rows.append(summary)
            print(
                f"[csweep] {name:>20s}  mean_regret={summary['mean_cum_regret']:7.4f} "
                f"± {summary['std_cum_regret']:.4f}  "
                f"overpay_krw={summary['mean_overpay_krw']:>12,.0f}"
            )

    # ----- 3) Optimal c -----
    means = np.array([row["mean_cum_regret"] for row in ucb_rows], dtype=float)
    c_arr = np.array([row["c"] for row in ucb_rows], dtype=float)
    best_idx = int(np.argmin(means))
    c_star = float(c_arr[best_idx])
    best_mean = float(means[best_idx])
    sqrt2_idx = int(np.argmin(np.abs(c_arr - np.sqrt(2.0))))
    sqrt2_mean = float(means[sqrt2_idx])
    improvement = sqrt2_mean - best_mean
    improvement_pct = 100.0 * improvement / sqrt2_mean if sqrt2_mean > 0 else 0.0

    print()
    print(
        f"[csweep] c* = {c_star} → mean_cum_regret = {best_mean:.4f} "
        f"(overpay = {best_mean * AVG_WINE_PRICE_KRW:,.0f} KRW)"
    )
    print(
        f"[csweep] vs c=√2 ({np.sqrt(2.0):.4f}): {sqrt2_mean:.4f} → "
        f"개선 = {improvement:+.4f} ({improvement_pct:+.1f}%)"
    )

    payload: dict[str, Any] = {
        "config": {
            "T": int(T),
            "n_seeds": int(n_seeds),
            "base_seed": int(base_seed),
            "c_grid": [float(c) for c in c_grid],
            "K": int(K),
            "arm_names": arm_names,
            "true_rewards": [float(x) for x in true_rewards],
            "noise_sigma": [float(x) for x in noise_sigma],
            "best_arm_idx": best_arm,
            "best_arm_name": arm_names[best_arm],
            "avg_wine_price_krw": int(AVG_WINE_PRICE_KRW),
        },
        "ucb_sweep": ucb_rows,
        "baselines": baseline_rows,
        "optimal": {
            "c_star": c_star,
            "mean_cum_regret_at_c_star": best_mean,
            "overpay_krw_at_c_star": best_mean * AVG_WINE_PRICE_KRW,
            "c_sqrt2_mean_cum_regret": sqrt2_mean,
            "improvement_vs_sqrt2": improvement,
            "improvement_pct_vs_sqrt2": improvement_pct,
        },
    }

    if out_summary is not None:
        out_summary.parent.mkdir(parents=True, exist_ok=True)
        with out_summary.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"[csweep] summary → {out_summary}")
    if out_jsonl is not None:
        print(f"[csweep] raw log → {out_jsonl}")

    return payload


def _print_table(payload: dict[str, Any]) -> None:
    """최종 결과 콘솔 테이블 출력 — UCB c-별 + 베이스라인 비교."""
    print()
    print("=" * 78)
    print("UCB1 c-constant Sensitivity Sweep — Final Results")
    print("=" * 78)
    cfg = payload["config"]
    print(
        f"K={cfg['K']}  T={cfg['T']}  n_seeds={cfg['n_seeds']}  "
        f"best_arm={cfg['best_arm_name']}"
    )
    print("-" * 78)
    print(f"{'policy':<24s} {'mean_regret':>12s} {'std':>8s} {'overpay_KRW':>14s}")
    print("-" * 78)
    for row in payload["ucb_sweep"]:
        c = row["c"]
        label = f"ucb1 c={c:.4f}"
        print(
            f"{label:<24s} {row['mean_cum_regret']:>12.4f} "
            f"{row['std_cum_regret']:>8.4f} {row['mean_overpay_krw']:>14,.0f}"
        )
    print("-" * 78)
    for row in payload["baselines"]:
        print(
            f"{row['policy_name']:<24s} {row['mean_cum_regret']:>12.4f} "
            f"{row['std_cum_regret']:>8.4f} {row['mean_overpay_krw']:>14,.0f}"
        )
    print("-" * 78)
    opt = payload["optimal"]
    print(
        f"★ c* = {opt['c_star']}  mean_cum_regret = {opt['mean_cum_regret_at_c_star']:.4f}  "
        f"overpay = {opt['overpay_krw_at_c_star']:,.0f} KRW"
    )
    print(
        f"  vs c=√2: {opt['c_sqrt2_mean_cum_regret']:.4f} → "
        f"improvement {opt['improvement_vs_sqrt2']:+.4f} "
        f"({opt['improvement_pct_vs_sqrt2']:+.1f}%)"
    )
    print("=" * 78)


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python scripts/analyze_ucb_csweep.py",
        description="UCB1 c-constant sensitivity sweep — 11 arms × T=200 × 20 seeds.",
    )
    p.add_argument("--T", type=int, default=200, help="라운드 수 (default 200)")
    p.add_argument("--n-seeds", type=int, default=20, help="시드 수 (default 20)")
    p.add_argument("--base-seed", type=int, default=0)
    p.add_argument(
        "--out-jsonl",
        type=str,
        default="results/logs/ucb_csweep.jsonl",
        help="시드별 raw 결과 JSONL",
    )
    p.add_argument(
        "--out-summary",
        type=str,
        default="results/data/ucb_csweep_summary.json",
        help="c-별 summary JSON",
    )
    p.add_argument(
        "--no-baselines",
        action="store_true",
        help="ε-greedy/Thompson/Random/Oracle 비교 생략",
    )
    p.add_argument(
        "--smoke",
        action="store_true",
        help="smoke run: T=50, n_seeds=3, c_grid 축소",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)

    if args.smoke:
        c_grid = [0.25, 1.0, float(np.sqrt(2.0)), 3.0]
        T = 50
        n_seeds = 3
        out_jsonl = Path("results/logs/ucb_csweep_smoke.jsonl")
        out_summary = Path("results/data/ucb_csweep_summary_smoke.json")
        print("[csweep] SMOKE MODE — T=50, n_seeds=3, c_grid 축소")
    else:
        c_grid = DEFAULT_C_GRID
        T = args.T
        n_seeds = args.n_seeds
        out_jsonl = Path(args.out_jsonl)
        out_summary = Path(args.out_summary)

    payload = run_sweep(
        c_grid=c_grid,
        T=T,
        n_seeds=n_seeds,
        base_seed=args.base_seed,
        out_jsonl=out_jsonl,
        out_summary=out_summary,
        include_baselines=not args.no_baselines,
    )

    _print_table(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
