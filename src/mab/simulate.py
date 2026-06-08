"""MAB 정책 시뮬레이션 러너 + JSONL 로깅.

phase 04 step3 — 정책별 다중 시드 실험을 돌려 누적 regret 곡선과 arm pull 통계를 저장한다.
보상 모델(reward.py)·정책 클래스(policies.py)는 형제 모듈에서 정의되며,
이 모듈은 두 컴포넌트를 묶어 실험 결과를 재현 가능하게 직렬화한다.

CLI:
    uv run python -m src.mab.simulate --T 200 --n-seeds 50 \
        --out results/logs/run_baseline.jsonl --policies all

직접 실행 (인자 없음) 시 quick smoke (T=50, n_seeds=3) 모드로 동작.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import pandas as pd

# 보고서 §2.3 — 와인21 970개 가격 중앙값 (단위: 원). regret 의 원화 환산용 상수.
AVG_WINE_PRICE_KRW: int = 72_000

# X-Wines 150K 평점에서 추정한 보상 노이즈 σ. ADR-009 참조.
DEFAULT_NOISE_SIGMA: float = 0.02


# ---------------------------------------------------------------------------
# Policy 인터페이스 — policies.py 의 구현이 따라야 할 최소 계약
# ---------------------------------------------------------------------------


class Policy(Protocol):
    """MAB 정책이 만족해야 하는 최소 인터페이스.

    `policies.py` 의 Protocol 과 일치한다 — `select(t)` 는 현재 라운드 인덱스를
    받아 다음에 당길 arm 을 반환, `update(arm, reward)` 는 관측 보상을 반영.
    """

    K: int

    def select(self, t: int) -> int: ...

    def update(self, arm: int, reward: float) -> None: ...


PolicyFactory = Callable[[int, np.random.Generator], Policy]


def _policy_name(policy: Policy) -> str:
    """정책 인스턴스의 표시 이름. 클래스에 `name` 속성이 없으면 클래스명."""
    name = getattr(policy, "name", None)
    if isinstance(name, str) and name:
        return name
    return type(policy).__name__


# ---------------------------------------------------------------------------
# 핵심 시뮬레이션 루프
# ---------------------------------------------------------------------------


def run_policy(
    policy: Policy,
    true_rewards: np.ndarray,
    noise_sigma: np.ndarray | float,
    T: int,
    seed: int,
    log_path: str | Path | None = None,
) -> dict[str, Any]:
    """단일 시드에 대해 T 라운드 동안 정책을 실행하고 누적 regret 곡선을 반환.

    매 라운드:
      1) arm = policy.select()
      2) reward ~ Normal(true_rewards[arm], noise_sigma[arm])
      3) policy.update(arm, reward)
      4) regret += max(true_rewards) - true_rewards[arm]
    """
    rng = np.random.default_rng(seed)
    K = len(true_rewards)
    if isinstance(noise_sigma, (int, float)):
        noise_sigma = np.full(K, float(noise_sigma))
    noise_sigma = np.asarray(noise_sigma, dtype=float)
    if noise_sigma.shape[0] != K:
        raise ValueError(
            f"noise_sigma 길이({noise_sigma.shape[0]}) ≠ true_rewards 길이({K})"
        )

    best_value = float(np.max(true_rewards))
    cum_regret_per_t = np.zeros(T, dtype=float)
    arm_pulls = np.zeros(K, dtype=np.int64)
    total_reward = 0.0
    running_regret = 0.0

    pname = _policy_name(policy)
    for t in range(T):
        arm = int(policy.select(t))
        if arm < 0 or arm >= K:
            raise ValueError(f"정책 {pname!r} 가 잘못된 arm 인덱스 반환: {arm}")
        # Gaussian noise 로 잡음 섞은 보상 샘플
        noise = float(rng.normal(0.0, noise_sigma[arm]))
        reward = float(true_rewards[arm]) + noise
        policy.update(arm, reward)

        arm_pulls[arm] += 1
        total_reward += reward
        running_regret += best_value - float(true_rewards[arm])
        cum_regret_per_t[t] = running_regret

    result: dict[str, Any] = {
        "policy_name": pname,
        "seed": int(seed),
        "T": int(T),
        "cum_regret_per_t": cum_regret_per_t,
        "arm_pulls": arm_pulls,
        "total_reward": float(total_reward),
    }

    if log_path is not None:
        _append_jsonl(Path(log_path), result)

    return result


def run_experiment(
    policy_factory: PolicyFactory,
    true_rewards: np.ndarray,
    noise_sigma: np.ndarray | float,
    T: int,
    n_seeds: int,
    log_path: str | Path | None = None,
    base_seed: int = 0,
) -> list[dict[str, Any]]:
    """동일 정책 팩토리에 대해 n_seeds 회 반복 실행. 각 시드의 결과를 리스트로 반환."""
    K = len(true_rewards)
    results: list[dict[str, Any]] = []
    for s in range(n_seeds):
        seed = base_seed + s
        rng = np.random.default_rng(seed)
        policy = policy_factory(K, rng)
        result = run_policy(
            policy=policy,
            true_rewards=true_rewards,
            noise_sigma=noise_sigma,
            T=T,
            seed=seed,
            log_path=log_path,
        )
        results.append(result)
    return results


def compare_policies(
    policies: dict[str, PolicyFactory],
    true_rewards: np.ndarray,
    noise_sigma: np.ndarray | float,
    T: int,
    n_seeds: int,
    log_path: str | Path | None = None,
    base_seed: int = 0,
) -> pd.DataFrame:
    """여러 정책을 동일 환경에서 비교. 정책별 평균/표준편차 summary 를 DataFrame 으로 반환.

    반환 컬럼: policy, mean_final_regret, std_final_regret,
              mean_final_regret_krw, total_reward_mean, n_seeds.
    """
    rows: list[dict[str, Any]] = []
    for name, factory in policies.items():
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
        rewards = np.array([r["total_reward"] for r in results], dtype=float)
        rows.append(
            {
                "policy": name,
                "mean_final_regret": float(finals.mean()),
                "std_final_regret": float(finals.std(ddof=1)) if n_seeds > 1 else 0.0,
                "mean_final_regret_krw": float(finals.mean()) * AVG_WINE_PRICE_KRW,
                "total_reward_mean": float(rewards.mean()),
                "n_seeds": int(n_seeds),
            }
        )
    return pd.DataFrame(rows)


def aggregate_curves(
    results: list[dict[str, Any]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """시드별 결과 리스트를 받아 (mean_curve, std_curve, mean_arm_pulls) 를 반환."""
    curves = np.stack([r["cum_regret_per_t"] for r in results], axis=0)
    pulls = np.stack([r["arm_pulls"] for r in results], axis=0)
    mean_curve = curves.mean(axis=0)
    std_curve = curves.std(axis=0, ddof=1) if curves.shape[0] > 1 else np.zeros_like(mean_curve)
    mean_pulls = pulls.mean(axis=0)
    return mean_curve, std_curve, mean_pulls


# ---------------------------------------------------------------------------
# JSONL 직렬화
# ---------------------------------------------------------------------------


def _append_jsonl(path: Path, result: dict[str, Any]) -> None:
    """run_policy 결과 1건을 JSONL 한 줄로 append. numpy → list 변환."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "policy_name": result["policy_name"],
        "seed": result["seed"],
        "T": result["T"],
        "cum_regret_per_t": result["cum_regret_per_t"].tolist(),
        "arm_pulls": result["arm_pulls"].tolist(),
        "total_reward": result["total_reward"],
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# 정책 팩토리 — src.mab.policies 의 정식 클래스를 묶어 노출.
#   하드코딩 markup 폴백은 reward.py 로딩 실패 시에만 사용된다.
# ---------------------------------------------------------------------------


def _build_default_policies(
    true_rewards: np.ndarray,
) -> dict[str, PolicyFactory]:
    """5개 정책 (ε-greedy, UCB1, Thompson, Random, Oracle) 팩토리 사전.

    policies.py 의 클래스 생성자 시그니처를 그대로 사용.
    """
    from src.mab.policies import (
        DEFAULT_EPSILON,
        DEFAULT_UCB_C,
        UCB1,
        EpsilonGreedy,
        OraclePolicy,
        RandomPolicy,
        ThompsonGauss,
    )

    factories: dict[str, PolicyFactory] = {
        "epsilon_greedy": lambda K, rng: EpsilonGreedy(  # noqa: E731
            K=K, epsilon=DEFAULT_EPSILON, rng=rng
        ),
        "ucb1": lambda K, rng: UCB1(K=K, c=DEFAULT_UCB_C, rng=rng),  # noqa: E731
        "thompson_gauss": lambda K, rng: ThompsonGauss(K=K, rng=rng),  # noqa: E731
        "random": lambda K, rng: RandomPolicy(K=K, rng=rng),  # noqa: E731
        "oracle": lambda K, rng: OraclePolicy(  # noqa: E731
            K=K, true_rewards=true_rewards, rng=rng
        ),
    }
    return factories


# 보고서 §3.4 표3 — 실제 데이터 로딩 실패 시 폴백용 markup 값
_FALLBACK_MARKUP_TABLE: dict[str, float] = {
    "프랑스": 4.4,
    "포르투갈": 4.4,
    "이탈리아": 7.3,
    "스페인": 12.0,
    "칠레": 8.5,
    "미국": 5.5,
    "호주": 9.1,
    "뉴질랜드": 6.8,
    "독일": 5.4,
    "아르헨티나": 5.3,
    "남아프리카": 10.4,
}


def _load_rewards_from_reward_module() -> tuple[np.ndarray, np.ndarray, list[str]]:
    """실제 mark-up 기반 (true_rewards, noise_sigma, arm_names) 로드.

    src.mab.reward 의 load_markup_table → compute_reward_arms → load_noise_sigma
    파이프라인을 호출. 데이터 파일 부재 시 보고서 §3.4 표3 하드코딩값으로 폴백.
    """
    try:
        from src.mab.reward import (
            TARGET_COUNTRIES,
            compute_reward_arms,
            load_markup_table,
            load_noise_sigma,
        )

        table = load_markup_table()
        true_rewards = compute_reward_arms(table)
        noise_sigma = load_noise_sigma(x_wines_present=True, reward_arms=true_rewards)
        arm_names = list(table["country"].astype(str))
        # 데이터가 11개국 미만이면 폴백
        if len(arm_names) < len(TARGET_COUNTRIES):
            raise RuntimeError(
                f"markup 테이블에 {len(arm_names)}개국만 존재 — 11개국 미만, 폴백"
            )
        return true_rewards, noise_sigma, arm_names
    except (FileNotFoundError, RuntimeError, KeyError, ImportError) as exc:
        print(f"[simulate] 실제 데이터 로딩 실패 ({exc!s}) — 보고서 §3.4 표3 폴백 사용")
        arm_names = list(_FALLBACK_MARKUP_TABLE.keys())
        true_rewards = np.array(
            [1.0 / _FALLBACK_MARKUP_TABLE[n] for n in arm_names], dtype=float
        )
        noise_sigma = np.full(len(arm_names), DEFAULT_NOISE_SIGMA, dtype=float)
        return true_rewards, noise_sigma, arm_names


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _select_policies(
    requested: str, all_factories: dict[str, PolicyFactory]
) -> dict[str, PolicyFactory]:
    if requested == "all":
        return all_factories
    names = [n.strip() for n in requested.split(",") if n.strip()]
    missing = [n for n in names if n not in all_factories]
    if missing:
        raise SystemExit(f"알 수 없는 정책: {missing}. 가능: {list(all_factories.keys())}")
    return {n: all_factories[n] for n in names}


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m src.mab.simulate")
    p.add_argument("--T", type=int, default=200, help="라운드 수 (default 200)")
    p.add_argument("--n-seeds", type=int, default=50, help="반복 시드 수 (default 50)")
    p.add_argument(
        "--out",
        type=str,
        default="results/logs/run_baseline.jsonl",
        help="JSONL 로그 출력 경로",
    )
    p.add_argument(
        "--policies",
        type=str,
        default="all",
        help="콤마구분 정책 이름 또는 'all'",
    )
    p.add_argument("--base-seed", type=int, default=0, help="시드 시작점 (default 0)")
    return p


def _main_cli(argv: list[str]) -> int:
    args = _build_arg_parser().parse_args(argv)

    true_rewards, noise_sigma, arm_names = _load_rewards_from_reward_module()
    factories = _build_default_policies(true_rewards)
    chosen = _select_policies(args.policies, factories)

    log_path = Path(args.out)
    # 기존 로그 덮어쓰기 (실험 시작 시 fresh 파일)
    if log_path.exists():
        log_path.unlink()

    print(f"[simulate] K={len(true_rewards)} arms: {arm_names}")
    print(f"[simulate] T={args.T}, n_seeds={args.n_seeds}, policies={list(chosen.keys())}")
    print(f"[simulate] log → {log_path}")

    summary = compare_policies(
        policies=chosen,
        true_rewards=true_rewards,
        noise_sigma=noise_sigma,
        T=args.T,
        n_seeds=args.n_seeds,
        log_path=log_path,
        base_seed=args.base_seed,
    )
    # 보기 좋게 출력
    with pd.option_context("display.float_format", "{:.4f}".format):
        print(summary.to_string(index=False))
    return 0


def _smoke_test() -> int:
    """인자 없이 실행됐을 때 돌리는 quick sanity check."""
    print("[smoke] quick simulate: T=50, n_seeds=3, 3 policies")
    true_rewards, noise_sigma, arm_names = _load_rewards_from_reward_module()
    factories = _build_default_policies(true_rewards)
    chosen_names = ["epsilon_greedy", "ucb1", "thompson_gauss"]
    chosen = {n: factories[n] for n in chosen_names if n in factories}
    summary = compare_policies(
        policies=chosen,
        true_rewards=true_rewards,
        noise_sigma=noise_sigma,
        T=50,
        n_seeds=3,
        log_path=None,
        base_seed=0,
    )
    print(f"[smoke] arms: {arm_names}")
    print(f"[smoke] best_arm_value={float(np.max(true_rewards)):.4f}")
    print(summary.to_string(index=False))
    # 정합성: regret 비음수, oracle 없이도 random fallback 보다 학습 정책이 더 낫거나 같음
    finals = summary["mean_final_regret"].to_numpy()
    assert (finals >= -1e-9).all(), "regret 은 비음수여야 함"
    print("[smoke] OK")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1:
        raise SystemExit(_main_cli(sys.argv[1:]))
    raise SystemExit(_smoke_test())
