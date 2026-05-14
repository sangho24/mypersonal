# Step 4 — 민감도 분석

## Read first
- `src/simulation/run.py`
- `docs/PRD.md` 4.5절 (α 값과 노이즈 σ 민감도)

## Goal
α (페르소나의 취향-품질 비중)와 σ (reward 노이즈)를 grid로 변화시키며 결과 변화를 측정.

## Tasks
1. `src/simulation/sweep.py` 생성. 한 페르소나 클러스터의 대표를 골라:
   - α ∈ {0.2, 0.4, 0.6, 0.8}, σ ∈ {0.02, 0.05, 0.1, 0.2}
   - 각 grid 점에서 정책 4종 × runs=10 × T=50 실행
2. 결과 `results/logs/sweep.jsonl` → `results/analysis/sensitivity.parquet`.
3. notebook `06_sensitivity.ipynb` — heatmap 2개 (α×policy의 final regret, σ×policy의 final regret).

## Don't
- α가 작은 페르소나(품질 중심)에서도 같은 정책이 최선이라고 결론짓지 말 것. **이유**: α 변화에 따른 winner 변화가 본 연구의 흥미로운 지점.

## Acceptance Criteria
```bash
python -m src.simulation.sweep --out results/logs/sweep.jsonl
python -m src.simulation.analyze --sweep results/logs/sweep.jsonl --out results/analysis/sensitivity.parquet
test -f results/analysis/sensitivity.parquet
```

## Phase exit
`phases/index.json`의 `05-simulation-analysis.status`를 `"completed"`로.
