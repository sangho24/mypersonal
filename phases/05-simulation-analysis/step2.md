# Step 2 — 메인 시뮬레이션

## Read first
- `src/simulation/runner.py` (quick run 통과 확인)
- `data/personas/preferences.parquet`
- `data/processed/wines_labeled.parquet`

## Goal
전체 페르소나 × 정책 셋 × runs=20 × T=50 시뮬레이션 실행.

## Tasks
1. `src/simulation/run.py`에 `--full` 모드 추가:
   - 모든 페르소나 (200~500)
   - 정책: EpsilonGreedy(0.05), EpsilonGreedy(0.1), UCB1, ThompsonSampling
   - T = 50, runs = 20, seed = 42
   - sigma = 0.05
2. 결과는 `results/logs/main_{YYYYMMDD}.jsonl`로 저장.
3. 실행 시간을 stderr로 출력. 예상보다 너무 길면(>30분) 페르소나를 클러스터별 대표로 줄이는 변형 옵션 `--per-cluster K`도 추가.

## Don't
- 한 번에 다 돌리고 결과를 안 살펴보지 말 것. **이유**: 정책 버그·reward 분포 이상이 후반에 발견되면 손실 큼. 페르소나 30개 우선 → 확인 → 전체.

## Acceptance Criteria
```bash
python -m src.simulation.run --full --out results/logs/main_$(date +%Y%m%d).jsonl
wc -l results/logs/main_*.jsonl   # = N_personas * N_policies * T * runs
python -c "
import pandas as pd
df = pd.read_json([p for p in __import__('glob').glob('results/logs/main_*.jsonl')][-1], lines=True)
print(df.groupby('policy_name')['cumulative_regret'].mean())
"
```
