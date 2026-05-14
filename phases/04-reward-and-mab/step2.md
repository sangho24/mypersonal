# Step 2 — MAB 정책 직접 구현

## Read first
- `docs/ADR.md` ADR-003 (numpy only)
- `docs/PRD.md` 4.4절

## Goal
ε-greedy, UCB1, Thompson Sampling을 동일 인터페이스로 numpy로 직접 구현.

## Tasks
1. `src/mab/policies.py` 생성:
   ```python
   class Policy:
       def __init__(self, n_arms: int, rng: numpy.random.Generator): ...
       def select_arm(self, t: int) -> int: ...
       def update(self, arm: int, reward: float) -> None: ...

   class EpsilonGreedy(Policy):
       def __init__(self, n_arms, rng, *, epsilon: float = 0.1): ...

   class UCB1(Policy):
       # confidence bound = mean + sqrt(2 * ln(t) / n_arm)
       ...

   class ThompsonSampling(Policy):
       # Beta posterior on reward (reward를 0~1로 clipping 후 Beta)
       ...
   ```
2. 각 정책은 내부 상태(`counts: np.ndarray`, `sums: np.ndarray`, `alphas/betas: np.ndarray`)를 가진다.
3. `select_arm`은 t (0-indexed)를 받아 arm index 반환. cold start(`counts == 0`인 arm이 있으면 우선 그것을 선택)는 모든 정책에 공통 적용.

## Don't
- `scipy.stats.beta` 의존하지 말 것. **이유**: numpy `default_rng().beta` 사용 가능.
- 모든 정책이 동일한 seed를 공유하지 말 것. **이유**: 실험 간 비교 시 noise. 정책별 독립 rng를 받거나, runner에서 정책별 sub-stream 분리.

## Acceptance Criteria
```bash
python -c "
import numpy as np
from src.mab.policies import EpsilonGreedy, UCB1, ThompsonSampling
for cls in (EpsilonGreedy, UCB1, ThompsonSampling):
    rng = np.random.default_rng(0)
    p = cls(n_arms=5, rng=rng) if cls is not EpsilonGreedy else cls(n_arms=5, rng=rng, epsilon=0.1)
    for t in range(20):
        a = p.select_arm(t)
        assert 0 <= a < 5
        p.update(a, reward=rng.random())
    print(cls.__name__, 'ok')
"
```
