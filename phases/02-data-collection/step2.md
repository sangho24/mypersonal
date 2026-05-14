# Step 2 — 카테고리 라벨링 및 MAB arms 확정

## Read first
- `data/processed/wines.parquet`
- `data/processed/category_candidates.json`

## Goal
모든 와인에 카테고리 라벨을 붙이고, arm별 빈도가 충분한지 확인 후 최종 8 ~ 15 arms를 확정.

## Tasks
1. `src/scraping/categorize.py` 생성:
   ```python
   def assign_category(wine: dict, candidates: list[dict]) -> int | None: ...
   def label_dataset(df: pandas.DataFrame, candidates_path: str) -> pandas.DataFrame: ...
   ```
2. `wines.parquet`에 `category_id` 컬럼을 붙여 `wines_labeled.parquet`로 저장.
3. arm별 빈도가 30 미만이면 인접 카테고리와 병합 — `data/processed/category_final.json`에 최종 정의 저장.

## Don't
- `None` 카테고리(매칭 실패)를 그대로 두지 말 것. **이유**: MAB arm 후보가 됨. 매칭 실패 와인은 별도 `category_other`로 묶거나, lexicon 보강 후 재라벨링.

## Acceptance Criteria
```bash
python -m src.scraping.categorize
python -c "
import pandas as pd, json
df = pd.read_parquet('data/processed/wines_labeled.parquet')
cats = json.load(open('data/processed/category_final.json'))
assert 8 <= len(cats) <= 15
assert df['category_id'].notna().mean() > 0.95
print(df['category_id'].value_counts().describe())
"
```
arm별 최소 30개 이상.
