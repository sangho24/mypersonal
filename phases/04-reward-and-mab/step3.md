# Step 3 — 정책 sanity check (toy bandit)

## Read first
- `src/mab/policies.py`

## Goal
와인 도메인과 무관한 toy 5-arm Bernoulli bandit에서 모든 정책이 "optimal arm을 점점 더 자주 뽑는다"는 기본 성질을 만족하는지 확인.

## Tasks
1. `src/mab/verify.py` 생성:
   - 5-arm Bernoulli bandit, true means = `[0.1, 0.2, 0.5, 0.7, 0.9]`
   - T = 500, runs = 30
   - 각 정책의 평균 cumulative regret 곡선과 optimal arm 선택률을 print + plot 저장 (`results/figures/sanity/`)
2. UCB1, Thompson은 ε-greedy(0.1)보다 후반(T=400 이후) 평균 regret이 낮아야 한다.

## Don't
- 결과를 보지 않고 시뮬레이션 phase로 넘어가지 말 것. **이유**: 정책 구현 버그를 본 시뮬레이션에서 발견하면 phase 03~04 재작업 비용 큼.

## Acceptance Criteria
```bash
python -m src.mab.verify
ls results/figures/sanity/*.png
```
표준 출력에 정책별 final regret과 "UCB1 < EpsilonGreedy: True", "Thompson < EpsilonGreedy: True" 라인이 있어야 한다.

## Phase exit
`phases/index.json`의 `04-reward-and-mab.status`를 `"completed"`로.
