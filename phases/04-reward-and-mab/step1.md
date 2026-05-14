# Step 1 — Reward Function 구현 (핵심 기여 2)

## Read first
- `docs/PRD.md` 4.3절 (R(w|p) 수식)
- `data/processed/wines_labeled.parquet`
- `data/personas/preferences.parquet`

## Goal
페르소나 p가 arm a(카테고리)에 속한 와인 한 잔을 마셨을 때의 reward를 numpy로 구현.

## 수식
```
R(w | p) = α_p · MATCH(p, w.attributes) + (1 − α_p) · Q(w.rating_distribution) + ε
```
- `MATCH(p, w)`: p의 region_weight[w.region]와 varietal_weight[w.varietal]의 평균 (0~1)
- `Q(w)`: w의 rating_avg를 0~1로 스케일링 (또는 rating 분포에서 Beta 샘플)
- `ε ~ Normal(0, σ)`, σ는 설정값

## Tasks
1. `src/simulation/reward.py` 생성:
   ```python
   def match_score(persona_prefs: dict, wine_row: pandas.Series) -> float: ...
   def quality_sample(wine_row: pandas.Series, rng: numpy.random.Generator) -> float: ...
   def reward(persona_prefs: dict, wine_row: pandas.Series, *, sigma: float, rng: numpy.random.Generator) -> float: ...
   def pull_arm(persona_prefs: dict, wines_in_arm: pandas.DataFrame, *, sigma: float, rng: numpy.random.Generator) -> tuple[int, float]: ...
   ```
   `pull_arm`은 arm에 속한 와인 중 1병을 무작위로 뽑고 reward 반환. (wine_id, reward).
2. quality_sample은 rating_avg가 있으면 Beta(α=rating_avg*10+1, β=(1-rating_avg)*10+1) 샘플. rating_count가 충분하면 분산 축소.
3. 모든 무작위성은 `rng: numpy.random.Generator`를 통해서만 — global numpy random 사용 금지.

## Don't
- MATCH 계산을 wine의 모든 속성에 대한 곱으로 만들지 말 것. **이유**: 결측 속성이 있으면 0 전파. region·varietal 가중치 평균이 안전.
- alpha를 모든 페르소나에 0.5로 고정하지 말 것. **이유**: 페르소나별 alpha 다양성이 분석 결과의 핵심.

## Acceptance Criteria
```bash
python -c "
import numpy as np, pandas as pd
from src.simulation.reward import pull_arm
wines = pd.read_parquet('data/processed/wines_labeled.parquet')
prefs = pd.read_parquet('data/personas/preferences.parquet').iloc[0].to_dict()
rng = np.random.default_rng(42)
arm0 = wines[wines['category_id']==0]
wid, r = pull_arm(prefs, arm0, sigma=0.05, rng=rng)
assert 0 <= r <= 1.5
# 동일 seed → 동일 결과
rng2 = np.random.default_rng(42)
wid2, r2 = pull_arm(prefs, arm0, sigma=0.05, rng=rng2)
assert wid == wid2 and abs(r - r2) < 1e-9
print('ok', wid, r)
"
```
