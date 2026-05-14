"""크롤링 결과(records.jsonl)가 정의한 WineRecord 테이블대로 뽑혔는지 검증.

CI 데이터 게이트의 핵심 로직. `validate_records` 는 순수 함수 — 네트워크 없음.
"""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

from src.scraping.schema import WineRecord

# 결측을 허용하지 않는 필드 (사용자 결정: tasting_note·rating 도 필수)
REQUIRED_FIELDS = (
    "name",
    "region",
    "varietal",
    "price_krw",
    "rating_avg",
    "rating_count",
    "tasting_note",
    "source",
    "source_url",
)
# 결측 허용 — 와인에 따라 "NA" 빈티지가 정상적으로 존재
OPTIONAL_FIELDS = ("vintage", "scraped_at")

_TYPES = {
    "name": str,
    "region": str,
    "varietal": str,
    "vintage": int,
    "price_krw": int,
    "rating_avg": (int, float),
    "rating_count": int,
    "tasting_note": str,
    "source": str,
    "source_url": str,
    "scraped_at": str,
}


def validate_record(rec: dict, idx: int) -> list[str]:
    """레코드 1개 검증 → 오류 메시지 리스트 (빈 리스트면 통과)."""
    errors: list[str] = []
    schema_keys = {f.name for f in fields(WineRecord)}

    missing_keys = schema_keys - rec.keys()
    if missing_keys:
        errors.append(f"[{idx}] 스키마 키 누락: {sorted(missing_keys)}")
    extra_keys = rec.keys() - schema_keys
    if extra_keys:
        errors.append(f"[{idx}] 정의되지 않은 키: {sorted(extra_keys)}")

    for field_name in REQUIRED_FIELDS:
        val = rec.get(field_name)
        if val is None or (isinstance(val, str) and not val.strip()):
            errors.append(f"[{idx}] 필수 필드 결측: {field_name}")

    for field_name, expected in _TYPES.items():
        val = rec.get(field_name)
        if val is not None and not isinstance(val, expected):
            errors.append(f"[{idx}] 타입 불일치: {field_name}={val!r} (기대 {expected})")

    if rec.get("source") not in (None, "wine21"):
        errors.append(f"[{idx}] source 가 'wine21' 이 아님: {rec.get('source')!r}")

    price = rec.get("price_krw")
    if isinstance(price, int) and price <= 0:
        errors.append(f"[{idx}] price_krw 가 양수가 아님: {price}")

    rating = rec.get("rating_avg")
    if isinstance(rating, (int, float)) and not (0 <= rating <= 5):
        errors.append(f"[{idx}] rating_avg 가 0~5 범위 밖: {rating}")

    return errors


def validate_records(records: list[dict]) -> list[str]:
    """레코드 목록 전체 검증 → 오류 메시지 리스트 (빈 리스트면 통과)."""
    errors: list[str] = []
    if not records:
        errors.append("레코드가 0건 — 수집 결과가 비어 있음")
    for i, rec in enumerate(records):
        errors.extend(validate_record(rec, i))
    return errors


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def latest_records_path(raw_dir: Path = Path("data/raw/wine21")) -> Path | None:
    """data/raw/wine21/{YYYYMMDD}/records.jsonl 중 가장 최근 것."""
    if not raw_dir.exists():
        return None
    candidates = sorted(raw_dir.glob("*/records.jsonl"))
    return candidates[-1] if candidates else None


def main() -> int:
    """CLI 진입점 — 최신 records.jsonl 검증. 통과 0, 실패 1."""
    path = latest_records_path()
    if path is None:
        print("검증할 records.jsonl 이 없음 — 먼저 크롤링을 실행하세요.")
        return 1
    records = load_jsonl(path)
    errors = validate_records(records)
    print(f"검증 대상: {path} ({len(records)} records)")
    if errors:
        print(f"검증 실패 — 오류 {len(errors)}건:")
        for e in errors[:50]:
            print(f"  {e}")
        if len(errors) > 50:
            print(f"  ... 외 {len(errors) - 50}건")
        return 1
    print("검증 통과 — 모든 레코드가 WineRecord 테이블 정의를 만족.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
