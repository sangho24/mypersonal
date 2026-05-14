# Step 2 — Figure 2: 페르소나 × 정책 승률 히트맵

## Read first
- `results/analysis/winrate.parquet`

## Goal
행=페르소나 클러스터, 열=정책, 셀=해당 클러스터에서 그 정책이 winner였던 비율. 한눈에 "클러스터마다 최적 정책이 다르다"를 보여줄 figure.

## Tasks
1. `src/viz/winrate_heatmap.py` 생성. matplotlib `imshow` 또는 `pcolormesh` 사용.
2. 셀 안에 수치 annotate (소수점 2자리).
3. 컬러바는 0~1.
4. PDF + PNG 저장 `results/figures/fig2_winrate.{png,pdf}`.

## Don't
- 색상에 의존해서 수치를 읽게 만들지 말 것. **이유**: 인쇄/흑백 시 식별 불가. 셀에 수치 annotate 필수.

## Acceptance Criteria
```bash
python -m src.viz.winrate_heatmap --in results/analysis/winrate.parquet --out results/figures/fig2_winrate
test -f results/figures/fig2_winrate.png
```
