# Step 1 — K-means 클러스터링 numpy 직접 구현

## Read first
- `docs/ADR.md` ADR-003 (sklearn 금지)
- `data/personas/sample.parquet`

## Goal
페르소나 demographic 속성 위에서 K = 6 ~ 8 클러스터로 나누는 K-means를 numpy로 직접 구현.

## Tasks
1. `src/personas/cluster.py` 생성:
   ```python
   def encode_features(df: pandas.DataFrame) -> numpy.ndarray: ...   # 연령(수치), 지역(one-hot), 직업(one-hot), 소득 수준(서수) 결합
   def kmeans(X: numpy.ndarray, k: int, *, max_iter: int = 100, seed: int = 42) -> tuple[numpy.ndarray, numpy.ndarray]: ...   # (labels, centroids)
   ```
2. 초기 centroid는 K-means++ 방식 직접 구현. random init fallback도 옵션으로.
3. `data/personas/clusters.parquet`로 저장. 컬럼: `persona_id`, `cluster_id`.

## Don't
- `sklearn.cluster.KMeans` 사용하지 말 것. **이유**: ADR-003 — 직접 구현이 평가 기준.
- 카테고리 변수를 그대로 정수 라벨로 거리 계산에 쓰지 말 것. **이유**: 지역 "서울"-"부산"의 거리가 정수 차이로 결정되면 의미 왜곡. one-hot 필수.

## Acceptance Criteria
```bash
python -c "
from src.personas.cluster import encode_features, kmeans
import pandas as pd, numpy as np
df = pd.read_parquet('data/personas/sample.parquet')
X = encode_features(df)
labels, C = kmeans(X, k=7, seed=42)
assert labels.shape[0] == len(df)
assert C.shape == (7, X.shape[1])
print('cluster sizes:', np.bincount(labels))
"
```
모든 클러스터 size > 0. 가장 작은 클러스터도 sample size의 5% 이상.
