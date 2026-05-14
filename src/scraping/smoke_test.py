"""Phase 01 smoke test — wine21 50병 sample 수집 후 결측률 출력.

AC: python -m src.scraping.smoke_test
"""

from __future__ import annotations

from src.scraping.wine21 import WineRecord, fetch_catalog

FIELDS = [
    "name",
    "region",
    "varietal",
    "vintage",
    "price_krw",
    "rating_avg",
    "rating_count",
    "tasting_note",
]


def _missing_rate(records: list[WineRecord]) -> dict[str, float]:
    n = len(records)
    if n == 0:
        return {f: 1.0 for f in FIELDS}
    out: dict[str, float] = {}
    for f in FIELDS:
        missing = sum(1 for r in records if getattr(r, f) in (None, ""))
        out[f] = missing / n
    return out


def main() -> None:
    records = fetch_catalog(limit=50)
    print(f"수집된 레코드 수: {len(records)}")
    print("결측률 by field:")
    for field, rate in _missing_rate(records).items():
        print(f"  {field}: {rate:.1%}")
    assert len(records) >= 40, f"50병에 근접해야 함 — 실제 {len(records)}"
    print("OK")


if __name__ == "__main__":
    main()
