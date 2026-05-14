# Step 1 — 시뮬레이션 러너 구현 + quick run

## Read first
- `src/simulation/reward.py`
- `src/mab/policies.py`
- `docs/ARCHITECTURE.md` 데이터 흐름 5번 (logs JSONL 스키마)

## Goal
한 페르소나 × 한 정책 × T 회를 돌리는 시뮬레이션 함수 + 전체를 곱집합으로 도는 러너 구현.

## Tasks
1. `src/simulation/runner.py` 생성:
   ```python
   def run_episode(prefs: dict, wines: pandas.DataFrame, policy, *, T: int, sigma: float, rng) -> list[dict]: ...
   def compute_optimal_reward(prefs: dict, wines: pandas.DataFrame, *, sigma: float, mc_samples: int = 1000, rng) -> tuple[int, float]: ...   # (optimal_arm, expected_reward)
   def run_grid(personas: pandas.DataFrame, wines: pandas.DataFrame, policies: dict, *, T: int, sigma: float, runs: int, seed: int, out_path: str) -> None: ...
   ```
2. `run_episode` 한 회는 한 줄당 dict (run_id, persona_id, cluster_id, policy_name, t, arm, wine_id, reward, instant_regret, cumulative_regret)를 `out_path`에 JSONL append.
3. `instant_regret = optimal_expected_reward - reward_actual`. optimal은 페르소나별 사전 계산 (모든 arm에서 mc_samples회 reward 평균 → 최댓값).
4. CLI 진입점 `python -m src.simulation.run --quick`은 페르소나 5개 × 정책 3개 × T=50 × runs=3 빠르게.

## Don't
- 전체 시뮬레이션을 메모리에 다 들고 있다가 마지막에 쓰지 말 것. **이유**: 300 personas × 3 policies × T=50 × 20 runs = 900K rows. JSONL append가 안전.
- 정책 객체를 재사용해 여러 episode를 돌리지 말 것. **이유**: 정책 내부 상태(`counts`, `sums`)가 누적되어 결과 오염. episode마다 새 인스턴스.

## Acceptance Criteria
```bash
python -m src.simulation.run --quick --out results/logs/quick.jsonl
wc -l results/logs/quick.jsonl   # 5 * 3 * 50 * 3 = 2250
python -c "
import pandas as pd
df = pd.read_json('results/logs/quick.jsonl', lines=True)
assert set(df.columns) >= {'run_id','persona_id','policy_name','t','arm','reward','cumulative_regret'}
assert (df['cumulative_regret'] >= -1e-6).all()
print('ok', len(df))
"
```
