# Step 1 — 와인앤모어 사이트 구조 정찰 및 스키마 정의

## Read first
- `docs/PRD.md` (수집 항목)
- `docs/ARCHITECTURE.md` (데이터 흐름 1번 항목)
- `docs/ADR.md` ADR-001

## Goal
wine21.com (ADR-001 갱신 결과)의 리스트/상세 페이지 HTML을 직접 받아 구조를 파악하고, WineRecord 스키마(dataclass)를 확정한다.

## Tasks
1. `data/raw/wine21/probe/`를 만들고 리스트 페이지 1개, 상세 페이지 3개를 `requests`로 받아 `.html`로 저장한다. 동적 로딩이라 빈 결과면 Playwright fallback이 필요한지 메모.
2. `src/scraping/schema.py`에 `WineRecord` dataclass를 정의한다. 필드: `name: str`, `region: str | None`, `varietal: str | None`, `vintage: int | None`, `price_krw: int | None`, `rating_avg: float | None`, `rating_count: int | None`, `tasting_note: str | None`, `source: str`, `source_url: str`, `scraped_at: str` (ISO8601).
3. `src/scraping/__init__.py`, `src/scraping/schema.py`를 생성하고 `WineRecord`를 export.

## Don't
- 실제 본 수집을 시작하지 말 것. **이유**: 카테고리 후보가 확정되기 전에 수집하면 재작업 발생.
- HTML을 git에 커밋하지 말 것. **이유**: `.gitignore`가 `data/raw/`를 제외함 — probe는 로컬용.

## Acceptance Criteria
```bash
python -c "from src.scraping.schema import WineRecord; r = WineRecord(name='t', region=None, varietal=None, vintage=None, price_krw=None, rating_avg=None, rating_count=None, tasting_note=None, source='probe', source_url='https://x', scraped_at='2026-05-13T00:00:00'); print(r.name)"
ls data/raw/wine21/probe/*.html | wc -l   # >= 4
```
출력: `t`, 그리고 파일 개수 >= 4.

## Notes for next step
- 발견한 CSS selector / DOM 구조를 `data/raw/wine21/probe/NOTES.md`에 적어두면 step2에서 바로 활용 가능.
