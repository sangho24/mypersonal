# Step 1 — Figure 1: 정책별 cumulative regret 곡선

## Read first
- `results/analysis/regret_curves.parquet`
- `docs/ADR.md` ADR-005 (matplotlib only)

## Goal
페르소나 클러스터별로 facet된 cumulative regret 곡선. x=t, y=mean regret, line=policy, shaded band=±SE.

## Tasks
1. `src/viz/regret_curve.py` 생성:
   ```python
   def plot_regret_curves(curves_df: pandas.DataFrame, out_path: str, *, clusters: list[int] | None = None) -> None: ...
   ```
2. cluster 개수에 따라 2×3 또는 2×4 grid. y축은 공유, x축은 0..T.
3. 정책별 색상 고정 (cb-friendly 팔레트). 범례는 figure 전체에서 1개.
4. PDF + PNG 두 형식으로 저장.

## Don't
- y축을 자동으로 두면 클러스터 간 비교가 어렵다. **이유**: shared y로 강제.

## Acceptance Criteria
```bash
python -m src.viz.regret_curve --in results/analysis/regret_curves.parquet --out results/figures/fig1_regret
test -f results/figures/fig1_regret.png && test -f results/figures/fig1_regret.pdf
```
