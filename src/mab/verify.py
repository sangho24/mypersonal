"""MAB 모듈 통합 sanity check.

phase 04 / 마무리 게이트 — `policies.py` + `reward.py` + `simulate.py` 가
한 파이프라인으로 묶였을 때 다음이 성립하는지 확인한다:

  1) markup_table 이 11개 arm 으로 로딩되고 reward 범위가 (0.083, 0.227) 안.
  2) 5개 정책 (ε-greedy, UCB1, Thompson, Random, Oracle) 이 T=200, n_seeds=10
     의 작은 예산에서 예외 없이 완주.
  3) Thompson, ε-greedy, UCB1 의 평균 누적 regret < Random.
  4) Oracle 의 평균 누적 regret ≈ 0 (수치적 잡음 허용).

본 모듈은 메인 실험의 baseline 이 아니라 통합 검증용이므로 예산이 작다.
실패 시 root cause 만 stdout 으로 보고 — assertion 우회는 금지.

CLI:
    uv run python -m src.mab.verify
"""

from __future__ import annotations

import sys
import traceback

import numpy as np
import pandas as pd

from src.mab.reward import compute_reward_arms, load_markup_table, load_noise_sigma
from src.mab.simulate import _build_default_policies, run_experiment

# 통합 검증 파라미터 — 작은 예산, sanity 전용
T: int = 200
N_SEEDS: int = 10
BASE_SEED: int = 0

# reward 범위 — ADR-009 / report §3.4 표3 기준 (1/markup 이므로 약 [0.083, 0.227])
REWARD_MIN_EXPECTED: float = 0.083
REWARD_MAX_EXPECTED: float = 0.227
REWARD_RANGE_TOL: float = 0.005  # markup 변동에 따른 허용 폭

# Oracle 누적 regret 허용 한계 (수치 잡음). 이론값은 0.
ORACLE_REGRET_TOL: float = 1e-9


def _evaluate_policies(
    true_rewards: np.ndarray,
    noise_sigma: np.ndarray,
) -> pd.DataFrame:
    """5개 정책을 동일 환경에서 T·N_SEEDS 회 실행하고 평균 누적 regret 을 집계."""
    factories = _build_default_policies(true_rewards)
    rows: list[dict[str, float | str]] = []
    for name, factory in factories.items():
        results = run_experiment(
            policy_factory=factory,
            true_rewards=true_rewards,
            noise_sigma=noise_sigma,
            T=T,
            n_seeds=N_SEEDS,
            log_path=None,
            base_seed=BASE_SEED,
        )
        finals = np.array([r["cum_regret_per_t"][-1] for r in results], dtype=float)
        total_rewards = np.array([r["total_reward"] for r in results], dtype=float)
        rows.append(
            {
                "policy": name,
                "mean_cum_regret": float(finals.mean()),
                "std_cum_regret": (
                    float(finals.std(ddof=1)) if N_SEEDS > 1 else 0.0
                ),
                "mean_total_reward": float(total_rewards.mean()),
                "n_seeds": int(N_SEEDS),
            }
        )
    return pd.DataFrame(rows)


def _print_summary(summary: pd.DataFrame) -> None:
    """단일 summary 표를 보기 좋게 출력."""
    with pd.option_context("display.float_format", "{:.6f}".format):
        print(summary.to_string(index=False))


def main() -> int:
    print("=" * 70)
    print("MAB 통합 sanity check (T=%d, n_seeds=%d)" % (T, N_SEEDS))
    print("=" * 70)

    # ---- 1) markup_table → arm 보상 ----
    table = load_markup_table()
    true_rewards = compute_reward_arms(table)
    noise_sigma = load_noise_sigma(x_wines_present=True, reward_arms=true_rewards)
    n_arms = len(true_rewards)

    print(f"[verify] n_arms={n_arms}")
    print(
        "[verify] reward range: "
        f"min={float(true_rewards.min()):.4f} "
        f"max={float(true_rewards.max()):.4f}"
    )
    print(
        "[verify] noise σ:      "
        f"min={float(noise_sigma.min()):.4f} "
        f"max={float(noise_sigma.max()):.4f}"
    )

    # arm 수 검증
    assert n_arms == 11, f"arm 수는 11이어야 함, 실측 {n_arms}"

    # reward 범위 검증 — 허용폭 포함
    r_min = float(true_rewards.min())
    r_max = float(true_rewards.max())
    assert r_min >= REWARD_MIN_EXPECTED - REWARD_RANGE_TOL, (
        f"reward 최솟값 {r_min:.4f} 이 기대치 {REWARD_MIN_EXPECTED} 아래"
    )
    assert r_max <= REWARD_MAX_EXPECTED + REWARD_RANGE_TOL, (
        f"reward 최댓값 {r_max:.4f} 이 기대치 {REWARD_MAX_EXPECTED} 위"
    )

    # ---- 2) 정책 실행 + 결과 표 ----
    summary = _evaluate_policies(true_rewards, noise_sigma)
    print()
    _print_summary(summary)
    print()

    # 정책별 평균 누적 regret 사전화
    means = {
        str(row["policy"]): float(row["mean_cum_regret"])
        for _, row in summary.iterrows()
    }

    # 5개 정책 모두 완주했는지 — summary 에 5행 있어야 함
    expected_policies = {
        "epsilon_greedy",
        "ucb1",
        "thompson_gauss",
        "random",
        "oracle",
    }
    assert set(means.keys()) == expected_policies, (
        f"정책 누락/추가: {set(means.keys())} ≠ {expected_policies}"
    )

    # 3) 학습 정책이 Random 보다 strictly less regret
    random_regret = means["random"]
    for learner in ("thompson_gauss", "epsilon_greedy", "ucb1"):
        assert means[learner] < random_regret, (
            f"{learner} regret({means[learner]:.4f}) 가 random({random_regret:.4f}) 보다 "
            "낮지 않음 — 정책이 학습을 못 하고 있음"
        )

    # 4) Oracle 은 누적 regret ≈ 0
    oracle_regret = means["oracle"]
    assert abs(oracle_regret) <= ORACLE_REGRET_TOL, (
        f"oracle regret {oracle_regret:.6e} 가 0 이 아님 — best_arm 외 다른 arm 을 당김"
    )

    print("[verify] ALL ASSERTIONS PASSED ✓")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"\n[verify] ASSERTION FAILED: {exc}", file=sys.stderr)
        traceback.print_exc()
        raise SystemExit(1) from exc
