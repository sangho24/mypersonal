# Step 2 — X-Wines 품종 프로파일 정제 + wine_catalog 조인 + arm 확정

## Read first
- step1 결과 `data/raw/wine21/{YYYYMMDD}/records.jsonl`
- `data/raw/xwines/drive/last/XWines_Full_100K_wines.csv` (X-Wines 10만 와인, CC0)
- `docs/ADR.md` ADR-006 (X-Wines 속성 grounding), ADR-008 (arm = country × price_tier)

## Goal
X-Wines 10만 와인에서 `품종 → (Body, Acidity)` 통계 프로파일을 도출하고, wine21 와인에
조인해 통합 와인 테이블 `data/processed/wine_catalog.jsonl` 을 만든다. arm(=country ×
price_tier)을 확정한다.

## Tasks
1. `src/scraping/xwines.py` 생성:
   ```python
   def build_grape_profile(xwines_csv: str) -> dict: ...   # 품종 → {body_mean, acidity_mean, n}
   ```
   - `Body` 5단계(Very light~Very full) → 1~5, `Acidity` 3단계(Low/Medium/High) → 1~3 로 수치화.
   - `Grapes` 컬럼은 `"['Merlot', ...]"` 형태 — `ast.literal_eval` 로 파싱.
   - `n < 20` 인 희소 품종은 제외. 결과를 `data/processed/grape_profile.json` 으로 저장.
2. `src/scraping/build_catalog.py` 생성:
   ```python
   def build_wine_catalog(records_jsonl: str, grape_profile_json: str) -> list[dict]: ...
   ```
   - wine21 `varietal` 의 괄호 안 영문(`"메를로 (Merlot) 100%"` → `Merlot`)으로 grape_profile 조인.
   - `country` = `region` 첫 토큰. `price_tier` = `price_krw` 분위수(저/중/고).
   - `arm_id` = `f"{country_group}-{price_tier}"`. country_group 은 주요국 + 신대륙/구대륙 묶음.
   - 컬럼: `wine_id, name, country, region, varietal, grape_norm, vintage, price_krw,
     price_tier, body, acidity, tasting_note, arm_id, source`.
   - 결과를 `data/processed/wine_catalog.jsonl` 로 저장.
3. arm별 빈도 확인 — 30병 미만 arm 은 인접 arm 과 병합. 최종 arm 정의를
   `data/processed/arms.json` 에 저장 (8~15개).
4. `tests/test_build_catalog.py` 추가 — grape_profile/조인/arm 로직 단위 테스트.

## Don't
- 개별 와인 단위로 X-Wines 와 조인하려 하지 말 것. **이유**: wine21·X-Wines 는 서로 다른
  와인 집합 — 품종 레벨 aggregate 조인만 유효 (ADR-008).
- body/acidity 조인 실패 와인을 조용히 버리지 말 것. **이유**: 품종 미매칭(~14%)은
  품종명 정규화(끝 공백 등)로 상당수 회복 가능. 회복 후에도 실패면 `category_other` 표시.

## Acceptance Criteria
```bash
uv run python -m src.scraping.xwines
uv run python -m src.scraping.build_catalog
uv run python -c "
import json
cat = [json.loads(l) for l in open('data/processed/wine_catalog.jsonl')]
arms = json.load(open('data/processed/arms.json'))
print(len(cat), 'wines,', len(arms), 'arms')
assert 8 <= len(arms) <= 15
joined = sum(1 for w in cat if w['body'] is not None)
print(f'body/acidity 조인: {joined}/{len(cat)} ({joined/len(cat):.0%})')
assert joined / len(cat) >= 0.80
"
uv run pytest tests/test_build_catalog.py -q
```
body/acidity 조인율 ≥ 80%, arm 8~15개, 단위 테스트 통과.
