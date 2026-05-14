"""WineRecord 스키마 단위 테스트."""

import dataclasses
from dataclasses import fields
from typing import Any

from src.scraping.schema import WineRecord

_BASE = WineRecord(
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


def _make(**overrides: Any) -> WineRecord:
    return dataclasses.replace(_BASE, **overrides)


def test_schema_has_expected_fields():
    names = {f.name for f in fields(WineRecord)}
    assert names == {
        "name",
        "region",
        "varietal",
        "vintage",
        "price_krw",
        "rating_avg",
        "rating_count",
        "tasting_note",
        "source",
        "source_url",
        "scraped_at",
    }


def test_to_dict_roundtrip():
    rec = _make()
    d = rec.to_dict()
    assert d["name"] == "테스트 와인"
    assert d["source"] == "wine21"
    assert WineRecord(**d).to_dict() == d


def test_optional_fields_accept_none():
    rec = _make(vintage=None, price_krw=None, tasting_note=None)
    assert rec.vintage is None
    assert rec.to_dict()["price_krw"] is None
