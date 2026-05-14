from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class WineRecord:
    name: str
    region: str | None
    varietal: str | None
    vintage: int | None
    price_krw: int | None
    rating_avg: float | None
    rating_count: int | None
    tasting_note: str | None
    source: str
    source_url: str
    scraped_at: str

    def to_dict(self) -> dict:
        return asdict(self)
