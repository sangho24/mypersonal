"""wine21.com 스크래퍼.

step2: parse_detail — 단일 상세 페이지 HTML → WineRecord (네트워크 없음)
step3: collect_detail_urls / fetch_html / fetch_catalog — 리스트 AJAX → 상세 크롤

보강(2026-05-14): 상세 페이지 초기 HTML 에는 시음 노트·평점 개수가 비어 있다.
- tasting_note 는 `load_wine_view_makersnote_list1.php` (메이커스노트) AJAX 로 채운다.
- rating_count 는 `load_wine_view_makersnote_list2.php` (테이스팅노트) 의 `tastingnote_count`.
- rating_avg 는 정적 HTML 의 별점 width% 에서 나오므로, 신호가 있는 와인을 얻으려면
  리스트를 평점순(POINT2|DESC)으로 수집한다. (ADR-001 참고)

NOTES.md (data/raw/wine21/probe/NOTES.md) 의 정찰 결과를 따른다.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from src.scraping.schema import WineRecord
from src.scraping.validate import validate_record

SOURCE = "wine21"
BASE = "https://www.wine21.com"
LIST_AJAX = f"{BASE}/13_search/proc/ajax_wine_list.php"
MAKERSNOTE1 = f"{BASE}/13_search/proc/load_wine_view_makersnote_list1.php"
MAKERSNOTE2 = f"{BASE}/13_search/proc/load_wine_view_makersnote_list2.php"
DETAIL_URL = f"{BASE}/13_search/wine_view.html?Idx={{idx}}"
RAW_DIR = Path("data/raw/wine21")

# 평점순 — rating_avg / rating_count 신호가 있는 와인부터 수집
DEFAULT_SORT = "POINT2|DESC"

HEADERS: dict[str, str | bytes] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": f"{BASE}/13_search/wine_list.html",
    "X-Requested-With": "XMLHttpRequest",
}


def _wine_idx(url: str) -> str | None:
    m = re.search(r"Idx=(\d+)", url)
    return m.group(1) if m else None


def _dl_map(soup: BeautifulSoup) -> dict[str, str]:
    """상세 페이지의 모든 dl(dt/dd) 쌍을 dict로."""
    out: dict[str, str] = {}
    for dl in soup.select("dl"):
        dt = dl.select_one("dt")
        dd = dl.select_one("dd")
        if dt and dd:
            key = dt.get_text(strip=True)
            out.setdefault(key, dd.get_text(" ", strip=True))
    return out


def _parse_price(soup: BeautifulSoup) -> int | None:
    price_el = soup.select_one(".wine-price")
    if price_el is None:
        return None
    if price_el.select_one(".wine-price-none"):
        return None
    # "880,000원 ( 750ml ) ..." → '원' 앞의 숫자만. (750ml 용량이 섞이지 않게)
    text = price_el.get_text(" ", strip=True)
    m = re.search(r"([\d,]+)\s*원", text)
    if not m:
        return None
    digits = m.group(1).replace(",", "")
    return int(digits) if digits else None


def _parse_vintage(soup: BeautifulSoup) -> int | None:
    for el in soup.select(".vintage-list .swiper-slide"):
        txt = el.get_text(strip=True)
        m = re.search(r"(19|20)\d{2}", txt)
        if m:
            return int(m.group(0))
    return None


def _parse_consumer_rating(soup: BeautifulSoup) -> float | None:
    """star-rating em 의 width% (0~100) → 0~5 점 환산."""
    em = soup.select_one(".wine-score .score-display .star-rating em")
    if em is None:
        return None
    style = str(em.get("style", "") or "")
    m = re.search(r"width\s*:\s*([0-9.]+)%", style)
    if not m:
        return None
    pct = float(m.group(1))
    if pct <= 0:
        return None
    return round(pct / 20.0, 2)


def parse_makersnote(html: str) -> str | None:
    """메이커스노트(list1) AJAX fragment → 시음 노트 텍스트. (순수 함수)"""
    soup = BeautifulSoup(html, "lxml")
    parts = [
        el.get_text(" ", strip=True)
        for el in soup.select(".makers-item-txt")
        if el.get_text(strip=True)
    ]
    return " ".join(parts) if parts else None


def parse_tastingnote_count(html: str) -> int | None:
    """테이스팅노트(list2) AJAX fragment → 소비자 평점 개수. (순수 함수)"""
    m = re.search(r"tastingnote_count\s*=\s*'(\d+)'", html)
    return int(m.group(1)) if m else None


def _static_tasting_note(dl_map: dict[str, str]) -> str | None:
    """정적 상세 페이지의 아로마/스타일 dl 필드로 시음 노트 baseline 을 구성.

    메이커스노트 AJAX 가 비어 있는 와인(약 20%)을 위한 폴백.
    """
    parts: list[str] = []
    aroma = dl_map.get("아로마")
    if aroma:
        parts.append(f"아로마: {aroma}")
    style = dl_map.get("스타일")
    if style:
        parts.append(f"스타일: {style}")
    return " / ".join(parts) if parts else None


def parse_detail(html: str, url: str) -> WineRecord:
    """상세 페이지 HTML 1개를 WineRecord 1개로 변환하는 순수 함수.

    tasting_note 는 정적 아로마/스타일 필드로 baseline 을 잡고,
    fetch_catalog 가 메이커스노트 AJAX 로 더 풍부한 노트가 있으면 덮어쓴다.
    rating_count 는 초기 HTML 에 없으므로 None — fetch_catalog 가 AJAX 로 보강한다.
    """
    soup = BeautifulSoup(html, "lxml")
    dl_map = _dl_map(soup)

    name_el = soup.select_one("dt.wine-name")
    name = name_el.get_text(strip=True) if name_el else ""

    return WineRecord(
        name=name,
        region=dl_map.get("국가/생산지역") or None,
        varietal=dl_map.get("주요품종") or None,
        vintage=_parse_vintage(soup),
        price_krw=_parse_price(soup),
        rating_avg=_parse_consumer_rating(soup),
        rating_count=None,  # AJAX 보강
        tasting_note=_static_tasting_note(dl_map),  # AJAX 보강 시 덮어씀
        source=SOURCE,
        source_url=url,
        scraped_at=datetime.now().isoformat(timespec="seconds"),
    )


def collect_detail_urls(
    start_page: int = 1, limit: int = 50, sort: str = DEFAULT_SORT
) -> list[str]:
    """ajax_wine_list.php 에 POST 페이지네이션 → 상세 URL 목록.

    엔드포인트는 `filter`/`option` JSON 파라미터를 받고(GET·단순 파라미터는 500),
    응답 HTML fragment 안의 와인 ID는 `goWineViewWithParam(<id>)` 형태로 노출된다.
    (카드 1개당 ID가 여러 번 나오므로 등장 순서 유지하며 dedupe.)
    """
    urls: list[str] = []
    page = start_page
    while len(urls) < limit:
        option = {"page": page, "pageSize": 10, "sort": sort}
        flt = {"KEY_WORD": "", "NO_PRICE": False}
        resp = requests.post(
            LIST_AJAX,
            data={"filter": json.dumps(flt), "option": json.dumps(option)},
            headers=HEADERS,
            timeout=15,
        )
        if resp.status_code != 200:
            break
        try:
            # 응답에 UTF-8 BOM 이 붙어 오는 경우가 있어 utf-8-sig 로 직접 디코드
            payload = json.loads(resp.content.decode("utf-8-sig"))
        except (ValueError, UnicodeDecodeError):
            break
        fragment = payload.get("html", "")
        ids = re.findall(r"goWineViewWithParam\((\d+)\)", fragment)
        if not ids:
            break
        for wid in ids:
            url = DETAIL_URL.format(idx=wid)
            if url not in urls:
                urls.append(url)
            if len(urls) >= limit:
                break
        if not payload.get("moreFlag", False):
            break
        page += 1
        time.sleep(1.5)
    return urls[:limit]


def fetch_html(url: str, *, sleep_sec: float = 1.5) -> str:
    """User-Agent 포함 GET. 4xx/5xx면 1회 재시도, 그래도 실패면 빈 문자열."""
    for _ in range(2):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                time.sleep(sleep_sec)
                return resp.text
        except requests.RequestException:
            pass
        time.sleep(sleep_sec)
    return ""


def _post_fragment(endpoint: str, wine_idx: str) -> str:
    """메이커스노트/테이스팅노트 AJAX fragment 를 받는다. 실패 시 빈 문자열."""
    try:
        resp = requests.post(
            endpoint,
            data={"WineIdx": wine_idx, "Year": "All"},
            headers=HEADERS,
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.content.decode("utf-8-sig", errors="replace")
    except requests.RequestException:
        pass
    return ""


def fetch_notes(wine_idx: str, *, sleep_sec: float = 1.0) -> tuple[str | None, int | None]:
    """상세 페이지에 비어 있는 (tasting_note, rating_count) 를 AJAX 로 보강."""
    note_html = _post_fragment(MAKERSNOTE1, wine_idx)
    time.sleep(sleep_sec)
    count_html = _post_fragment(MAKERSNOTE2, wine_idx)
    time.sleep(sleep_sec)
    return parse_makersnote(note_html), parse_tastingnote_count(count_html)


def fetch_catalog(limit: int = 50, sort: str = DEFAULT_SORT) -> list[WineRecord]:
    """리스트→상세 크롤 + 노트/평점 AJAX 보강 후 raw HTML·records.jsonl·failures.jsonl 저장."""
    day = datetime.now().strftime("%Y%m%d")
    out_dir = RAW_DIR / day
    out_dir.mkdir(parents=True, exist_ok=True)

    urls = collect_detail_urls(limit=limit, sort=sort)
    records: list[WineRecord] = []
    failures: list[dict] = []

    for url in urls:
        html = fetch_html(url)
        if not html:
            failures.append({"url": url, "reason": "fetch_failed"})
            continue
        idx = _wine_idx(url) or str(len(records))
        (out_dir / f"{idx}.html").write_text(html, encoding="utf-8")
        try:
            rec = parse_detail(html, url)
        except Exception as exc:  # 파싱 실패도 조용히 버리지 않음
            failures.append({"url": url, "reason": f"parse_error: {exc}"})
            continue
        if not rec.name:
            failures.append({"url": url, "reason": "empty_name"})
            continue
        # AJAX 보강 — 메이커스노트가 있으면 정적 아로마 baseline 을 덮어씀
        makersnote, rating_count = fetch_notes(idx)
        if makersnote:
            rec.tasting_note = makersnote
        rec.rating_count = rating_count

        # 테이블 계약 강제 — 필수 필드가 빠진 레코드는 records.jsonl 에 넣지 않고
        # failures.jsonl 로 보낸다. (조용히 버리지 않음)
        validation_errors = validate_record(rec.to_dict(), len(records))
        if validation_errors:
            failures.append(
                {"url": url, "reason": "validation_failed", "errors": validation_errors}
            )
            continue
        records.append(rec)

    with (out_dir / "records.jsonl").open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")
    with (out_dir / "failures.jsonl").open("w", encoding="utf-8") as f:
        for fail in failures:
            f.write(json.dumps(fail, ensure_ascii=False) + "\n")

    return records


def smoke_test() -> None:
    """probe HTML 1개를 parse_detail로 변환해 출력 (네트워크 없음)."""
    probe = RAW_DIR / "probe" / "detail_1.html"
    html = probe.read_text(encoding="utf-8")
    url = f"{BASE}/13_search/wine_view.html?Idx=PROBE"
    rec = parse_detail(html, url)
    print("parse_detail smoke_test →")
    for k, v in rec.to_dict().items():
        print(f"  {k}: {v!r}")
    assert rec.name, "name 이 비어있음"
    assert rec.source == SOURCE
    assert rec.source_url
    print("OK")


if __name__ == "__main__":
    smoke_test()
