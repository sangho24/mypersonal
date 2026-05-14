"""wine21 파서 순수 함수 단위 테스트 (네트워크 없음, 커밋된 fixture 사용)."""

from pathlib import Path

from src.scraping.wine21 import (
    SOURCE,
    parse_detail,
    parse_makersnote,
    parse_tastingnote_count,
)

FIXTURES = Path(__file__).parent / "fixtures"
DETAIL_URL = "https://www.wine21.com/13_search/wine_view.html?Idx=181145"


def test_parse_detail_basic_fields():
    html = (FIXTURES / "wine21_detail.html").read_text(encoding="utf-8")
    rec = parse_detail(html, DETAIL_URL)
    assert rec.name  # 비어있지 않음
    assert rec.source == SOURCE
    assert rec.source_url == DETAIL_URL
    assert rec.region and ">" in rec.region  # "미국 > 오리건 > ..." 다층 구조
    assert rec.varietal
    # tasting_note 는 정적 아로마/스타일 필드로 baseline 을 잡는다 (fetch_catalog 가 보강)
    assert rec.tasting_note and "아로마:" in rec.tasting_note
    # 평점 개수는 정적 HTML 에 없으므로 None — AJAX 보강 대상
    assert rec.rating_count is None


def test_parse_detail_price_excludes_volume():
    """가격 파싱이 '750ml' 의 750 을 흡수하지 않아야 한다."""
    html = (FIXTURES / "wine21_detail.html").read_text(encoding="utf-8")
    rec = parse_detail(html, DETAIL_URL)
    # 이 fixture 는 '가격정보없음' 케이스 → None 이어야 (750 같은 오염값 금지)
    assert rec.price_krw is None or rec.price_krw >= 1000


def test_parse_makersnote_extracts_text():
    html = (FIXTURES / "wine21_makersnote1_rated.html").read_text(encoding="utf-8")
    note = parse_makersnote(html)
    assert note and len(note) > 5


def test_parse_makersnote_empty_returns_none():
    assert parse_makersnote("<div class='board-list'></div>") is None
    assert parse_makersnote("") is None


def test_parse_tastingnote_count():
    html = (FIXTURES / "wine21_makersnote2_rated.html").read_text(encoding="utf-8")
    count = parse_tastingnote_count(html)
    assert isinstance(count, int) and count >= 0


def test_parse_tastingnote_count_absent_returns_none():
    assert parse_tastingnote_count("<div>no script here</div>") is None
