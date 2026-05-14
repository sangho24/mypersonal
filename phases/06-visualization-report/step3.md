# Step 3 — Figure 3: arm pull 시간 경과 (stacked area)

## Read first
- `results/analysis/arm_pulls.parquet`

## Goal
정책 1개를 선택해서, t에 따라 각 arm이 선택되는 비율을 stacked area chart로. 탐색→활용 전환을 시각화.

## Tasks
1. `src/viz/arm_pulls.py` 생성. 정책 4개를 2×2 facet으로 그리거나, 정책 1개를 main figure로 + 나머지는 appendix.
2. x=t, y=arm 선택 비율 (0~1 합), 영역별로 arm id.
3. 색상 팔레트는 카테고리 수에 맞춰.
4. `results/figures/fig3_armpulls.{png,pdf}` 저장.

## Don't
- 모든 arm을 한 plot에 욱여넣지 말 것 (8~15개면 식별 어려움). **이유**: top-5 arm은 색으로, 나머지는 회색으로 묶는 것도 옵션.

## Acceptance Criteria
```bash
python -m src.viz.arm_pulls --in results/analysis/arm_pulls.parquet --out results/figures/fig3_armpulls --policy UCB1
test -f results/figures/fig3_armpulls.png
```
