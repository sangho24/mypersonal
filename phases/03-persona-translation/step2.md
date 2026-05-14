# Step 2 — 방법 A — 클러스터 기반 선호 벡터 매핑

## Read first
- `data/personas/clusters.parquet`
- `data/processed/category_final.json` (지역/품종 차원)
- `docs/PRD.md` 4.2절 방법 A

## Goal
각 클러스터의 demographic 특성을 보고 와인 도메인 선호 벡터를 손으로 설계 + JSON으로 저장. 출력은 페르소나 단위 선호 (페르소나는 자기 클러스터의 prefs를 상속).

## Tasks
1. `notebooks/03_cluster_profile.ipynb` 생성:
   - 각 클러스터의 평균 연령, 지역 top3, 직업 top3, 소득 분포 출력
   - 클러스터별 demographic narrative 2~3줄 메모 (예: "30대 후반 수도권 전문직, 가격에 둔감")
2. `data/personas/cluster_prefs.json` 작성. 형식:
   ```json
   {
     "0": {
       "region_weights": {"Bordeaux": 0.6, "Burgundy": 0.9, "Italy": 0.4, "...": 0.3},
       "varietal_weights": {"Pinot Noir": 0.9, "Cabernet Sauvignon": 0.6, "...": 0.5},
       "price_sensitivity": 0.3,
       "alpha": 0.7
     }
   }
   ```
3. `src/personas/translate_cluster.py` 생성:
   ```python
   def build_preferences(personas: pandas.DataFrame, clusters: pandas.DataFrame, prefs_path: str) -> pandas.DataFrame: ...
   ```
   페르소나 단위 선호를 `data/personas/preferences.parquet`로 저장.

## Don't
- 모든 클러스터에 동일한 선호 벡터를 부여하지 말 것. **이유**: 페르소나별 최적 정책이 달라야 본 연구의 가설이 검증됨. 적어도 region_weights와 alpha는 클러스터마다 의도적으로 다르게.

## Acceptance Criteria
```bash
python -c "
import pandas as pd, json
prefs = pd.read_parquet('data/personas/preferences.parquet')
assert {'persona_id','cluster_id','alpha','price_sensitivity','region_weights','varietal_weights'}.issubset(prefs.columns)
cp = json.load(open('data/personas/cluster_prefs.json'))
assert len(cp) >= 6
print('ok')
"
```
