# Step 1 — wine21 폭넓은 본수집 (전 국가·전 카테고리, 실가격)

## Read first
- `src/scraping/wine21.py` (phase 01 결과물 — `collect_detail_urls`, `fetch_catalog`)
- `src/scraping/validate.py` (데이터 검증 게이트)
- `docs/ADR.md` ADR-008 (universe = wine21 폭넓은 수집, 가격은 실값)

## Goal
wine21 에서 **전 국가·전 카테고리에 걸쳐 3,000~5,000병**을 수집한다. phase 01 의
평점순(POINT2|DESC) 슬라이스는 무명 와인 편중이었으므로 — 이번엔 국가별로 골고루 모아
다양성을 확보한다. 결과는 `data/raw/wine21/{YYYYMMDD}/records.jsonl`.

## Tasks
1. `src/scraping/wine21.py` 에 국가 필터 수집 함수 추가:
   ```python
   # WINE_NATION 필터 코드: 프랑스 P09000000, 이탈리아 P15000000, 스페인 P24000000,
   # 미국 P28000000, 칠레 P08000000, 호주 P02000000, 독일 P11000000, 뉴질랜드 P18000000,
   # 아르헨티나 P01000000, 포르투갈 P19000000, 남아공 P23000000
   def collect_by_nation(nation_code: str, limit: int, sort: str = "a.CREATE_DATE|DESC") -> list[str]: ...
   def fetch_broad_catalog(per_nation: int = 400) -> list[WineRecord]: ...
   ```
   `fetch_broad_catalog` 는 주요 11개국 각각에서 `per_nation` 병씩 모아 머지 → 국가 다양성 보장.
2. 정렬은 평점순 금지 — `최신등록순` 또는 `가격순`을 섞어 가격대도 골고루 들어오게 한다.
3. 각 와인은 phase 01 과 동일하게 상세 HTML 저장 + `parse_detail` + 시음노트/평점 AJAX 보강.
4. 검증 실패 레코드는 `failures.jsonl` 로 라우팅 (phase 01 `fetch_catalog` 로직 재사용).
5. 수집은 백그라운드 배치 — 요청 간 `sleep` 유지 (차단 방지).

## Don't
- 평점순(`POINT2|DESC`)으로 수집하지 말 것. **이유**: phase 01 에서 평점순 상위 = 평점자
  1~2명짜리 무명 수입와인으로 확인됨. 다양성·대표성이 깨진다 (ADR-008).
- `time.sleep` 없이 연속 요청 금지. **이유**: 차단 위험. 3,000+ 요청이라 특히 주의.
- 본 수집 결과를 git 에 커밋하지 말 것. **이유**: `.gitignore` 가 `data/raw/` 제외.

## Acceptance Criteria
```bash
uv run python -m src.scraping.validate   # 최신 records.jsonl 검증, 종료코드 0
uv run python -c "
import json, glob
from collections import Counter
p = sorted(glob.glob('data/raw/wine21/*/records.jsonl'))[-1]
recs = [json.loads(l) for l in open(p)]
print(len(recs), 'wines')
assert len(recs) >= 3000, len(recs)
ctry = Counter(r['region'].split('(')[0].strip() for r in recs if r['region'])
print('국가 분포:', dict(ctry))
assert len(ctry) >= 8, '국가 다양성 부족'
"
```
3,000병 이상, 8개국 이상 분포, 검증 게이트 통과.
