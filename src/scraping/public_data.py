"""관세청 공공데이터 API — 와인(HS 2204) 국가별 수입 통계.

강의 PDF 7·8 의 표준 패턴(`requests.get(url, params={..., 'serviceKey': KEY})` → XML → pandas)
을 그대로 따른다. wine21 카탈로그의 국가 분포와 비교해 한국 시장 맥락을 확인하는 용도.

API: 관세청 품목별 국가별 수출입실적(GW), data.go.kr/15100475
응답: XML
"""

from __future__ import annotations

import csv
import os
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

import requests
from dotenv import load_dotenv

ENDPOINT = "https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList"
RAW_DIR = Path("data/raw/customs")
PROCESSED_DIR = Path("data/processed")

# HS 코드 2204 = 와인 (포도주). 하위 5개 코드:
WINE_HS_DESC: dict[str, str] = {
    "220410": "스파클링",
    "220421": "병와인_2L이하",
    "220422": "병와인_2-10L",
    "220429": "벌크와인_10L초과",
    "220430": "기타_강화와인등",
}

# wine21 11개국 ↔ ISO 2-letter 국가코드 (관세청 statCd)
COUNTRY_CODES: dict[str, str] = {
    "프랑스": "FR",
    "이탈리아": "IT",
    "스페인": "ES",
    "포르투갈": "PT",
    "독일": "DE",
    "미국": "US",
    "뉴질랜드": "NZ",
    "호주": "AU",
    "칠레": "CL",
    "아르헨티나": "AR",
    "남아프리카 공화국": "ZA",
}

# 출력 컬럼 (한글 통일 — 분석 노트북에서 바로 쓰기 위함)
CSV_FIELDS = [
    "year_month",
    "country_code",
    "country",
    "hs_code",
    "hs_desc",
    "import_usd",
    "import_kg",
    "export_usd",
    "export_kg",
]


def _service_key() -> str:
    load_dotenv()
    key = os.environ.get("DATA_GO_KR_SERVICE_KEY")
    if not key:
        raise RuntimeError("DATA_GO_KR_SERVICE_KEY 환경변수가 비어 있다. .env 파일을 확인하라.")
    return key


def fetch_imports(
    start_yymm: str, end_yymm: str, country_code: str, *, timeout: int = 20
) -> tuple[str, list[dict]]:
    """단일 국가에 대해 와인(HS 2204) 수출입 통계 조회.

    반환: (원본 XML 문자열, 정제된 record 리스트)
    """
    resp = requests.get(
        ENDPOINT,
        params={
            "serviceKey": _service_key(),
            "strtYymm": start_yymm,
            "endYymm": end_yymm,
            "hsSgn": "2204",
            "cntyCd": country_code,
            # 12개월 × 5 HS코드 ≈ 60건 + 총계 → 페이지 크기 키워 한 번에 받음
            "numOfRows": 500,
            "pageNo": 1,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    xml = resp.text
    root = ET.fromstring(xml)
    records: list[dict] = []
    for item in root.findall(".//item"):

        def get(tag: str) -> str:
            el = item.find(tag)
            return (el.text or "").strip() if el is not None else ""

        year = get("year")
        hs = get("hsCd")
        # 총계 행(year="총계", hsCd="-")과 결측 행 제외
        if year == "총계" or hs == "-" or not hs:
            continue
        records.append(
            {
                "year_month": year,  # 예: "2024.10"
                "country_code": get("statCd"),
                "country": get("statCdCntnKor1"),
                "hs_code": hs,
                "hs_desc": WINE_HS_DESC.get(hs, get("statKor")),
                "import_usd": int(get("impDlr") or 0),
                "import_kg": int(get("impWgt") or 0),
                "export_usd": int(get("expDlr") or 0),
                "export_kg": int(get("expWgt") or 0),
            }
        )
    return xml, records


def fetch_all_countries(
    start_yymm: str, end_yymm: str, countries: dict[str, str] | None = None
) -> list[dict]:
    """11개 와인 생산국 전체에 대해 수입 통계 조회 + raw XML 저장 + CSV 정제."""
    countries = countries or COUNTRY_CODES
    day = datetime.now().strftime("%Y%m%d")
    raw_out = RAW_DIR / day
    raw_out.mkdir(parents=True, exist_ok=True)

    all_records: list[dict] = []
    for name, code in countries.items():
        xml, records = fetch_imports(start_yymm, end_yymm, code)
        (raw_out / f"{code}_{start_yymm}_{end_yymm}.xml").write_text(xml, encoding="utf-8")
        all_records.extend(records)
        print(f"  [{name:8s} {code}] records {len(records):4d}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = PROCESSED_DIR / "wine_imports.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(all_records)
    print(f"저장: {csv_path} ({len(all_records)} rows)")
    return all_records


def smoke_test() -> None:
    """프랑스 1개월치 조회로 동작 확인 (네트워크)."""
    xml, records = fetch_imports("202504", "202504", "FR")
    print(f"smoke_test → 프랑스 2025.04 records: {len(records)}")
    for r in records[:3]:
        print(f"  {r}")
    assert records, "응답이 비어 있음 — 인증키/엔드포인트 확인 필요"
    print("OK")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "all":
        # API 제약: 조회기간 1년 이내 → 정확히 12개월 (end의 11개월 전 ~ end)
        end = sys.argv[2] if len(sys.argv) > 2 else "202504"
        ey, em = int(end[:4]), int(end[4:6])
        sm = em - 11
        sy = ey
        if sm <= 0:
            sm += 12
            sy -= 1
        start = f"{sy:04d}{sm:02d}"
        print(f"수집 범위: {start} ~ {end}")
        fetch_all_countries(start, end)
    else:
        smoke_test()
