"""크롤링 결과 검증 로직(validate_records) 단위 테스트 + 실제 수집 데이터 게이트."""

import pytest

from src.scraping.validate import (
    latest_records_path,
    load_jsonl,
    validate_record,
    validate_records,
)

VALID = dict(
    name="테스트 와인",
    region="프랑스 > 보르도",
    varietal="메를로 100%",
    vintage=2020,
    price_krw=50000,
    rating_avg=4.2,
    rating_count=10,
    tasting_note="체리, 자두 향",
    source="wine21",
    source_url="https://www.wine21.com/13_search/wine_view.html?Idx=1",
    scraped_at="2026-05-14T00:00:00",
)


def test_valid_record_passes():
    assert validate_record(VALID, 0) == []


def test_vintage_may_be_none():
    """vintage 는 'NA' 와인이 정상 존재 — 결측 허용."""
    rec = {**VALID, "vintage": None}
    assert validate_record(rec, 0) == []


@pytest.mark.parametrize(
    "field",
    [
        "name",
        "region",
        "varietal",
        "price_krw",
        "rating_avg",
        "rating_count",
        "tasting_note",
    ],
)
def test_required_field_missing_fails(field):
    rec = {**VALID, field: None}
    errors = validate_record(rec, 0)
    assert any(field in e for e in errors)


def test_empty_string_required_field_fails():
    rec = {**VALID, "name": "   "}
    assert any("name" in e for e in validate_record(rec, 0))


def test_wrong_source_fails():
    rec = {**VALID, "source": "winenara"}
    assert any("source" in e for e in validate_record(rec, 0))


def test_type_mismatch_fails():
    rec = {**VALID, "price_krw": "50000"}
    assert any("price_krw" in e for e in validate_record(rec, 0))


def test_rating_out_of_range_fails():
    rec = {**VALID, "rating_avg": 7.0}
    assert any("rating_avg" in e for e in validate_record(rec, 0))


def test_negative_price_fails():
    rec = {**VALID, "price_krw": -100}
    assert any("price_krw" in e for e in validate_record(rec, 0))


def test_extra_key_fails():
    rec = {**VALID, "unexpected": 1}
    assert any("unexpected" in e for e in validate_record(rec, 0))


def test_empty_records_list_fails():
    assert validate_records([]) != []


def test_validate_records_aggregates():
    bad = {**VALID, "name": None}
    errors = validate_records([VALID, bad, VALID])
    assert len(errors) == 1 and "[1]" in errors[0]


# --- 실제 수집 데이터 게이트 (data/raw 는 gitignore 되므로 CI 에선 skip) ---


def test_latest_crawl_records_pass_validation():
    path = latest_records_path()
    if path is None:
        pytest.skip("수집된 records.jsonl 없음 — 로컬에서 크롤링 후 실행되는 게이트")
    records = load_jsonl(path)
    errors = validate_records(records)
    assert errors == [], f"{path} 검증 실패 ({len(errors)}건):\n" + "\n".join(errors[:20])
