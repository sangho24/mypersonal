"""MAB 정책 모듈 — numpy 기반 직접 구현.

phase 04 / step (MAB 알고리즘) — notebooks/final_report.ipynb §5 코드를 모듈화.
노트북에서는 정책 함수가 `arm_pool` (dict[str, pd.DataFrame]) 과 `value_of()` 헬퍼를
클로저로 참조했으나, 본 모듈에서는 외부 의존성을 끊고 `Policy.select(t)` + `Policy.update(arm, reward)`
인터페이스만 노출한다 (보상 샘플링은 호출자가 담당 — `src.mab.simulate` 참조).

스택 제약: numpy 만 사용 (sklearn, scipy 금지). 수업 평가 기준 — 직접 구현이 핵심.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np

# 정책 기본 하이퍼파라미터 — 노트북 §5 기본값과 일치
DEFAULT_EPSILON: float = 0.1                # ε-greedy 탐험 확률
DEFAULT_UCB_C: float = float(np.sqrt(2.0))  # UCB1 표준 상수 (Auer et al., 2002)
DEFAULT_PRIOR_MEAN: float = 0.5             # Thompson Gaussian prior μ₀
DEFAULT_PRIOR_VAR: float = 1.0              # Thompson Gaussian prior σ₀²
DEFAULT_NOISE_VAR: float = 0.05**2          # 관측 노이즈 분산 (ADR-009 σ≈0.02 와 호환)


class Policy(Protocol):
    """MAB 정책 공통 인터페이스 (Protocol — 명목적 상속 불요).

    - `select(t)` 는 라운드 t (0-indexed) 에서 당길 arm 인덱스를 반환.
    - `update(arm, reward)` 는 관측된 보상으로 내부 통계를 갱신.
    """

    K: int

    def select(self, t: int) -> int: ...

    def update(self, arm: int, reward: float) -> None: ...


class EpsilonGreedy:
    """ε-greedy 정책 — 확률 ε 으로 무작위, (1-ε) 로 현재 추정 최적 arm."""

    def __init__(
        self,
        K: int,
        epsilon: float = DEFAULT_EPSILON,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.K = K
        self.epsilon = epsilon
        self.rng = rng if rng is not None else np.random.default_rng()
        self.N: np.ndarray = np.zeros(K, dtype=np.int64)
        self.Q: np.ndarray = np.zeros(K, dtype=np.float64)

    def select(self, t: int) -> int:  # noqa: ARG002 — t 미사용은 의도적
        """ε 확률로 explore, 그 외 argmax(Q)."""
        if self.rng.random() < self.epsilon:
            return int(self.rng.integers(self.K))
        return int(np.argmax(self.Q))

    def update(self, arm: int, reward: float) -> None:
        """점진 평균 업데이트: Q ← Q + (r - Q)/N."""
        self.N[arm] += 1
        self.Q[arm] += (reward - self.Q[arm]) / self.N[arm]


class UCB1:
    """UCB1 — Q + c·√(ln t / N) 상한 신뢰구간 최대화 (Auer et al., 2002)."""

    def __init__(
        self,
        K: int,
        c: float = DEFAULT_UCB_C,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.K = K
        self.c = c
        self.rng = rng if rng is not None else np.random.default_rng()
        self.N: np.ndarray = np.zeros(K, dtype=np.int64)
        self.Q: np.ndarray = np.zeros(K, dtype=np.float64)

    def select(self, t: int) -> int:
        """미선택 arm 우선, 그 외 UCB 최대 arm."""
        unexplored = np.where(self.N == 0)[0]
        if unexplored.size > 0:
            return int(unexplored[0])
        ucb = self.Q + self.c * np.sqrt(np.log(t + 1) / self.N)
        return int(np.argmax(ucb))

    def update(self, arm: int, reward: float) -> None:
        """점진 평균 업데이트."""
        self.N[arm] += 1
        self.Q[arm] += (reward - self.Q[arm]) / self.N[arm]


class ThompsonGauss:
    """Thompson Sampling — Gaussian-Gaussian 켤레사전. 노이즈 분산은 알려져 있다고 가정."""

    def __init__(
        self,
        K: int,
        prior_mean: float = DEFAULT_PRIOR_MEAN,
        prior_var: float = DEFAULT_PRIOR_VAR,
        noise_var: float = DEFAULT_NOISE_VAR,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.K = K
        self.noise_var = noise_var
        self.rng = rng if rng is not None else np.random.default_rng()
        self.mu: np.ndarray = np.full(K, prior_mean, dtype=np.float64)
        self.var: np.ndarray = np.full(K, prior_var, dtype=np.float64)
        self.N: np.ndarray = np.zeros(K, dtype=np.int64)

    def select(self, t: int) -> int:  # noqa: ARG002
        """각 arm 의 사후분포에서 1개 표본 추출 후 argmax."""
        sample = self.rng.normal(self.mu, np.sqrt(self.var))
        return int(np.argmax(sample))

    def update(self, arm: int, reward: float) -> None:
        """Gaussian conjugate posterior update.

        σ²_post = 1 / (1/σ²_prior + 1/σ²_noise)
        μ_post  = σ²_post · (μ_prior/σ²_prior + r/σ²_noise)
        """
        prior_var = self.var[arm]
        prior_mean = self.mu[arm]
        post_var = 1.0 / (1.0 / prior_var + 1.0 / self.noise_var)
        post_mean = post_var * (prior_mean / prior_var + reward / self.noise_var)
        self.var[arm] = post_var
        self.mu[arm] = post_mean
        self.N[arm] += 1


class RandomPolicy:
    """무작위 baseline — 균등 분포로 arm 선택 (탐험만, 학습 없음)."""

    def __init__(self, K: int, rng: np.random.Generator | None = None) -> None:
        self.K = K
        self.rng = rng if rng is not None else np.random.default_rng()
        self.N: np.ndarray = np.zeros(K, dtype=np.int64)

    def select(self, t: int) -> int:  # noqa: ARG002
        """매 라운드 균등 무작위."""
        return int(self.rng.integers(self.K))

    def update(self, arm: int, reward: float) -> None:  # noqa: ARG002
        """학습 없음 — 카운트만 유지 (디버깅용)."""
        self.N[arm] += 1


class OraclePolicy:
    """오라클 baseline — 진짜 기대보상 argmax 를 매번 선택 (upper-bound).

    실험에서는 절대 도달 불가능하지만 regret 곡선의 0 기준선을 제공.
    """

    def __init__(
        self,
        K: int,
        true_rewards: np.ndarray,
        rng: np.random.Generator | None = None,
    ) -> None:
        if true_rewards.shape != (K,):
            raise ValueError(
                f"true_rewards 길이 {true_rewards.shape} ≠ K={K}"
            )
        self.K = K
        self.true_rewards = np.asarray(true_rewards, dtype=np.float64)
        self.best_arm: int = int(np.argmax(self.true_rewards))
        self.rng = rng if rng is not None else np.random.default_rng()
        self.N: np.ndarray = np.zeros(K, dtype=np.int64)

    def select(self, t: int) -> int:  # noqa: ARG002
        """항상 진짜 최적 arm."""
        return self.best_arm

    def update(self, arm: int, reward: float) -> None:  # noqa: ARG002
        """오라클은 학습 불요 — 카운트만 유지."""
        self.N[arm] += 1


def _toy_smoke_test() -> int:
    """4-arm 가우시안 토이 밴딧 T=100 — 각 정책이 예외 없이 돌아가는지 확인."""
    rng = np.random.default_rng(42)
    K = 4
    T = 100
    # 진짜 기대보상: arm 2 가 최적
    true_rewards = np.array([0.10, 0.15, 0.25, 0.20], dtype=np.float64)
    noise_sigma = 0.05

    def sample_reward(arm: int, sampler: np.random.Generator) -> float:
        return float(true_rewards[arm] + sampler.normal(0.0, noise_sigma))

    policies: dict[str, Policy] = {
        "epsilon_greedy": EpsilonGreedy(K, epsilon=0.1, rng=np.random.default_rng(0)),
        "ucb1": UCB1(K, c=DEFAULT_UCB_C, rng=np.random.default_rng(1)),
        "thompson_gauss": ThompsonGauss(K, rng=np.random.default_rng(2)),
        "random": RandomPolicy(K, rng=np.random.default_rng(3)),
        "oracle": OraclePolicy(K, true_rewards, rng=np.random.default_rng(4)),
    }

    print(f"[smoke] 4-arm toy bandit, true_rewards={true_rewards.tolist()}, T={T}")
    print(f"[smoke] best_arm = {int(np.argmax(true_rewards))} (expected = 2)")

    for name, policy in policies.items():
        cum_reward = 0.0
        pulls: list[int] = []
        for t in range(T):
            arm = policy.select(t)
            r = sample_reward(arm, rng)
            policy.update(arm, r)
            cum_reward += r
            pulls.append(arm)
        oracle_cum = float(true_rewards[int(np.argmax(true_rewards))] * T)
        regret = oracle_cum - cum_reward
        best_pct = 100.0 * sum(1 for p in pulls if p == int(np.argmax(true_rewards))) / T
        print(
            f"[smoke] {name:>16s}  cum_reward={cum_reward:7.3f}  "
            f"regret={regret:6.3f}  best_arm_pulls={best_pct:5.1f}%"
        )

    # 정책별 sanity 체크 — oracle 은 무조건 best_arm 만 당겨야 함
    oracle = policies["oracle"]
    assert isinstance(oracle, OraclePolicy)
    assert int(oracle.N[oracle.best_arm]) == T, "oracle 이 best_arm 외 다른 arm 을 당김"
    return 0


if __name__ == "__main__":
    raise SystemExit(_toy_smoke_test())
