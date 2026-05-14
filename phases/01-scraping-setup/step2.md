# Step 2 — 단일 상세 페이지 파서 구현

## Read first
- `phases/01-scraping-setup/step1.md` (완료된 결과)
- `data/raw/wineandmore/probe/NOTES.md` (step1에서 작성한 selector 메모)
- `src/scraping/schema.py`

## Goal
단일 상세 페이지 HTML 1개를 받아 `WineRecord` 1개로 변환하는 순수 함수를 구현한다.

## Tasks
1. `src/scraping/wineandmore.py` 생성. 다음 함수 시그니처를 노출:
   ```python
   def parse_detail(html: str, url: str) -> WineRecord: ...
   ```
2. BeautifulSoup(`lxml` 파서)로 필드를 추출한다. 누락 필드는 `None` 그대로 둔다 (정제 단계에서 보완 — `docs/PRD.md` 보완 방안 참고).
3. 가격은 "₩57,000" 같은 문자열을 정수 KRW로 정규화한다. 변환 실패 시 `None`.
4. `src/scraping/wineandmore.py` 안에 `parse_detail`을 import해서 동작하는 `smoke_test()` 함수를 만든다. step1의 probe 파일 중 1개를 읽어 출력.

## Don't
- 사이트에 네트워크 요청을 하지 말 것. **이유**: 이 step은 파서 단위 검증. 네트워크는 step3에서.
- `re`만으로 가격을 파싱하면서 천 단위 구분이 다른 케이스(예: `₩ 57000`)를 빼먹지 말 것. **이유**: 누락 시 정제 단계에서 또 손봐야 함.

## Acceptance Criteria
```bash
python -m src.scraping.wineandmore   # smoke_test() 호출 — WineRecord 출력
```
출력에 `name`이 비어있지 않고, `source == 'wineandmore'`, `source_url`이 채워져 있어야 한다.
