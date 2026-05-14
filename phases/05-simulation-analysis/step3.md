# Step 3 — 지표 계산 및 결과 분석

## Read first
- `results/logs/main_*.jsonl`
- `docs/PRD.md` 4.5절 분석 지표 4종

## Goal
4가지 분석 지표를 계산해서 분석용 parquet으로 저장:
1. 시간에 따른 cumulative regret 곡선 (policy × cluster)
2. 페르소나별 정책 승률 매트릭스 (winner = lowest cumulative_regret at T=50)
3. 탐색-활용 비율의 시간적 변화 (arm pull 분포 엔트로피)
4. arm pull 분포 (시간 경과)

## Tasks
1. `src/simulation/analyze.py` 생성:
   ```python
   def regret_curves(log_df) -> pandas.DataFrame: ...    # (t, cluster_id, policy, mean_regret, se)
   def winrate_matrix(log_df) -> pandas.DataFrame: ...   # rows=cluster, cols=policy, values=win frequency
   def exploration_entropy(log_df, *, window: int = 10) -> pandas.DataFrame: ...   # (t, cluster, policy, entropy)
   def arm_pull_distribution(log_df) -> pandas.DataFrame: ...                       # (t, cluster, policy, arm, count)
   ```
2. 모든 결과를 `results/analysis/`에 parquet으로 저장.
3. `notebooks/05_main_analysis.ipynb` 생성 — 결과 표/그림 + 인사이트 노트 (특히 "페르소나 클러스터마다 최적 정책이 다른가" 질문에 답).

## Don't
- run 단위 평균만 보지 말 것. **이유**: 분산이 중요. SE 또는 분위수 추가.

## Acceptance Criteria
```bash
python -m src.simulation.analyze --log $(ls -t results/logs/main_*.jsonl | head -1)
ls results/analysis/{regret_curves,winrate,entropy,arm_pulls}.parquet
python -c "
import pandas as pd
w = pd.read_parquet('results/analysis/winrate.parquet')
# 클러스터마다 winner가 동일하지 않다 → main 가설 지지
assert w.idxmax(axis=1).nunique() >= 2, 'winning policy is same across all clusters — suspicious'
print(w)
"
```
