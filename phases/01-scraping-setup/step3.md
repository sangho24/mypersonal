# Step 3 — 리스트 페이지 → 상세 페이지 크롤 흐름 (50병 sample)

## Read first
- `src/scraping/schema.py`, `src/scraping/wineandmore.py`
- `docs/ARCHITECTURE.md` 데이터 흐름 1번 (raw 저장 경로)
- `docs/PRD.md` 스크래핑 보완 방안 (차단/누락 대응)

## Goal
와인앤모어 리스트 페이지에서 상세 URL 50개를 모으고, 각 상세를 다운로드해 `WineRecord` 50개를 JSONL로 덤프한다.

## Tasks
1. `src/scraping/wineandmore.py`에 다음 함수 추가:
   ```python
   def collect_detail_urls(start_url: str, limit: int = 50) -> list[str]: ...
   def fetch_html(url: str, *, sleep_sec: float = 1.5) -> str: ...
   def fetch_catalog(limit: int = 50) -> list[WineRecord]: ...
   ```
2. `fetch_html`은 User-Agent 헤더 포함, 요청 간 `sleep_sec` 대기. 4xx/5xx면 1회 재시도, 그래도 실패면 빈 문자열 반환.
3. `fetch_catalog`는 raw HTML을 `data/raw/wineandmore/{YYYYMMDD}/`에 `{slug}.html`로 저장하고, parse 결과 `list[WineRecord]`도 `records.jsonl`로 저장.
4. `src/scraping/smoke_test.py` 생성. `fetch_catalog(limit=50)` 호출 후 결과 개수와 결측률 출력.

## Don't
- `time.sleep` 없이 연속 요청하지 말 것. **이유**: 차단 위험. 1.5초가 너무 빠르면 늘릴 것.
- 본 수집(1,500병)을 시작하지 말 것. **이유**: 카테고리 후보 확정(step4) 후 phase 02에서 진행.
- 파싱 실패한 페이지를 조용히 버리지 말 것. **이유**: 보완 방안 결정 근거가 필요. 실패 URL은 `failures.jsonl`에 기록.

## Acceptance Criteria
```bash
python -m src.scraping.smoke_test
ls data/raw/wineandmore/$(date +%Y%m%d)/records.jsonl
wc -l data/raw/wineandmore/$(date +%Y%m%d)/records.jsonl   # 50에 근접 (>= 40)
```
출력에 "결측률 by field"가 보여야 한다.
