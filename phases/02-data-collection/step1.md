# Step 1 — 본 수집 + 정제 파이프라인

## Read first
- `src/scraping/wineandmore.py` (phase 01 결과물)
- `data/processed/category_candidates.json`
- `docs/PRD.md` 스크래핑 보완 방안 6가지

## Goal
와인앤모어에서 1,500병 이상 수집. 정제하여 `data/processed/wines.parquet`로 저장.

## Tasks
1. `src/scraping/wineandmore.py`의 `fetch_catalog`를 `limit=2000` (또는 사이트 상황에 따라) 호출. 실패 URL은 `failures.jsonl`에 기록.
2. `src/scraping/normalize.py` 생성. 다음 함수:
   ```python
   def normalize(records: list[WineRecord]) -> pandas.DataFrame: ...
   ```
   처리 항목:
   - 가격 단위 통일 (KRW int)
   - 빈티지 이상치 제거 (현재 연도 +2 초과, 1900 미만은 None)
   - 품종/지역 표기 통일 (대소문자, 영문/한글 매핑 — `src/scraping/lexicon.py`에 dict로)
   - 결측치 보완 (`PRD.md` 보완 방안 적용: 정규식 추출, 카테고리 평균/중앙값)
3. 결과를 `data/processed/wines.parquet`로 저장. 컬럼: `wine_id`, `name`, `region`, `varietal`, `vintage`, `price_krw`, `rating_avg`, `rating_count`, `tasting_note`, `source_url`.

## Don't
- 차단 시 바로 포기하지 말 것. **이유**: `PRD.md`에 헤더·간격 조정 방안이 있음. 24시간 cool-down 후 재시도.
- 결측치를 전부 평균으로 imputation하지 말 것. **이유**: rating_avg는 평균이 의미 있지만 vintage는 의미 없음. 필드별 다른 전략.

## Acceptance Criteria
```bash
python -m src.scraping.normalize --input data/raw/wineandmore --output data/processed/wines.parquet
python -c "import pandas as pd; df = pd.read_parquet('data/processed/wines.parquet'); print(len(df), 'wines'); assert len(df) >= 1500, len(df); print(df.isna().mean())"
```
1500 이상, 컬럼별 결측률 출력.
