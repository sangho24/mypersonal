# Step 4 — Figure 4: 페르소나 클러스터 분포 산점도

## Read first
- `data/personas/sample.parquet`, `data/personas/clusters.parquet`
- `src/personas/cluster.py` (encoded features)

## Goal
페르소나 클러스터를 2D로 산점도. PCA 또는 t-SNE로 차원 축소.

## Tasks
1. `src/viz/persona_scatter.py` 생성. PCA를 numpy로 직접 구현(SVD 또는 공분산 eigendecomp). 또는 옵션으로 t-SNE는 외부 의존 — sklearn 사용 금지면 PCA로.
2. 클러스터별 색상, 마커.
3. 클러스터 중심에 클러스터 id 텍스트 라벨.
4. `results/figures/fig4_persona_scatter.{png,pdf}`.

## Don't
- sklearn PCA 사용하지 말 것. **이유**: ADR-003.

## Acceptance Criteria
```bash
python -m src.viz.persona_scatter --out results/figures/fig4_persona_scatter
test -f results/figures/fig4_persona_scatter.png
```
