"""vivino.com 평점 보강 소스.

wine21 의 소비자 평점은 전부 5.0 (평점자 1~2명) 이라 MAB 보상 신호로 못 쓴다.
vivino 내부 explore API (`/api/explore/explore`) 는 인증 없이 평점 평균·개수를
반환하므로, wine21 의 영문 와인명으로 검색해 fuzzy match 로 평점을 join 한다.

검색은 winery 토큰 위주의 부분일치라 exact match 가 아니다 — 신뢰도 점수를
함께 내보내고, 임계 미만은 매칭 실패로 처리한다 (잘못된 평점을 붙이지 않음).
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from difflib import SequenceMatcher

import requests

EXPLORE_API = "https://www.vivino.com/api/explore/explore"
SOURCE = "vivino"

HEADERS: dict[str, str | bytes] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}

# 매칭 임계
WINE_THRESHOLD = 0.62  # 전체 신뢰도 — 와인 단위 일치로 인정
WINERY_THRESHOLD = 0.80  # winery 유사도 — winery 대표 평점을 proxy 로 사용


@dataclass
class VivinoCandidate:
    name: str
    winery: str
    year: str | None
    rating_avg: float | None
    rating_count: int | None


@dataclass
class MatchResult:
    matched: bool
    confidence: float
    rating_avg: float | None
    rating_count: int | None
    vivino_name: str | None
    vivino_winery: str | None
    # "wine": 와인 단위 일치 / "winery": winery 일치(대표 와인 평점) / "none"
    match_level: str = "none"
    winery_sim: float = 0.0


def _norm(text: str) -> str:
    """비교용 정규화 — 소문자, 영숫자만, 공백 1칸."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def winery_of(en_name: str) -> str:
    """wine21 영문명에서 winery 부분 추출 — 보통 첫 콤마 앞."""
    head = en_name.split(",")[0]
    return _norm(head)


def _similarity(a: str, b: str) -> float:
    """토큰 집합 기반 유사도 (0~1). 외부 라이브러리 없이 difflib + 토큰 overlap."""
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return 0.0
    seq = SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(na.split()), set(nb.split())
    jaccard = len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0
    return 0.5 * seq + 0.5 * jaccard


def search(query: str, *, per_page: int = 8, timeout: int = 20) -> list[VivinoCandidate]:
    """explore API 검색 → 후보 목록. (min_rating 필터 1개 이상 필수 — 없으면 400)"""
    resp = requests.get(
        EXPLORE_API,
        params={"search_term": query, "min_rating": 1, "per_page": per_page},
        headers=HEADERS,
        timeout=timeout,
    )
    if resp.status_code != 200:
        return []
    try:
        payload = resp.json()
    except ValueError:
        return []
    matches = payload.get("explore_vintage", {}).get("matches", [])
    out: list[VivinoCandidate] = []
    for m in matches:
        vintage = m.get("vintage", {}) or {}
        wine = vintage.get("wine", {}) or {}
        stats = vintage.get("statistics", {}) or wine.get("statistics", {}) or {}
        out.append(
            VivinoCandidate(
                name=wine.get("name", "") or "",
                winery=(wine.get("winery") or {}).get("name", "") or "",
                year=str(vintage.get("year")) if vintage.get("year") else None,
                rating_avg=stats.get("ratings_average"),
                rating_count=stats.get("ratings_count"),
            )
        )
    return out


def best_match(en_name: str, candidates: list[VivinoCandidate]) -> MatchResult:
    """wine21 영문명에 가장 가까운 vivino 후보를 신뢰도와 함께 반환.

    vivino explore 검색은 "그 winery 의 와인"을 주지 정확히 같은 와인을 주지
    않는 경우가 많다. 그래서 두 단계로 본다:
    - confidence(winery+name 결합) 가 높으면 → 와인 단위 일치
    - winery 유사도만 높으면 → winery 대표 평점을 proxy 로 (match_level="winery")
    """
    w21_winery = winery_of(en_name)
    best = MatchResult(False, 0.0, None, None, None, None)
    for c in candidates:
        if c.rating_avg is None:
            continue
        winery_sim = _similarity(w21_winery, c.winery)
        full_sim = _similarity(en_name, f"{c.winery} {c.name}")
        confidence = round(0.6 * winery_sim + 0.4 * full_sim, 3)
        if confidence > best.confidence or (
            winery_sim > best.winery_sim and confidence >= best.confidence - 0.05
        ):
            if confidence >= WINE_THRESHOLD:
                level = "wine"
            elif winery_sim >= WINERY_THRESHOLD:
                level = "winery"
            else:
                level = "none"
            best = MatchResult(
                matched=level != "none",
                confidence=confidence,
                rating_avg=c.rating_avg,
                rating_count=c.rating_count,
                vivino_name=c.name,
                vivino_winery=c.winery,
                match_level=level,
                winery_sim=round(winery_sim, 3),
            )
    return best


def lookup(en_name: str, *, sleep_sec: float = 1.0) -> MatchResult:
    """영문 와인명 → vivino 평점 매칭. 전체명 검색 후 실패 시 winery 만으로 재시도.

    explore API 기반 — 후보를 거의 못 찾는 한계가 있어 측정용. 실제 보강은
    VivinoBrowser (Playwright) 를 쓴다.
    """
    candidates = search(en_name)
    result = best_match(en_name, candidates)
    if not result.matched:
        time.sleep(sleep_sec)
        winery = en_name.split(",")[0].strip()
        if winery and winery.lower() != en_name.lower():
            result2 = best_match(en_name, search(winery))
            if result2.confidence > result.confidence:
                result = result2
    time.sleep(sleep_sec)
    return result


# --- Playwright 기반 검색 (explore API 가 후보를 거의 못 찾아 실제 보강은 이쪽) ---

SEARCH_URL = "https://www.vivino.com/search/wines?q={q}"
_RATINGS_RE = re.compile(r"\(([\d,]+)\s*ratings?\)")


def _parse_card_text(text: str) -> tuple[str, str, float | None, int | None]:
    """vivino 검색 카드의 inner_text → (winery, name, rating_avg, rating_count).

    카드 텍스트는 줄 단위로 'winery / name+year / region / ... / rating / (N ratings)'.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    winery = lines[0] if lines else ""
    name = lines[1] if len(lines) > 1 else ""
    name = re.sub(r"\s*(19|20)\d{2}\s*$", "", name).strip()  # 끝의 빈티지 제거

    rating_avg: float | None = None
    for ln in lines:
        m = re.fullmatch(r"([0-5]\.\d)", ln)
        if m:
            rating_avg = float(m.group(1))
            break

    rating_count: int | None = None
    m = _RATINGS_RE.search(text)
    if m:
        rating_count = int(m.group(1).replace(",", ""))
    return winery, name, rating_avg, rating_count


class VivinoBrowser:
    """Playwright 로 vivino 검색 페이지를 렌더링해 와인 카드를 수집한다.

    explore API 와 달리 사람이 쓰는 그 검색이라 후보를 제대로 반환한다.
    브라우저를 1회만 띄우고 여러 와인을 연속 조회하도록 context manager 로 사용.
    """

    def __init__(self, *, headless: bool = True) -> None:
        self._headless = headless
        self._pw = None
        self._browser = None
        self._page = None

    def __enter__(self) -> VivinoBrowser:
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self._headless)
        self._page = self._browser.new_page(user_agent=str(HEADERS["User-Agent"]))
        return self

    def __exit__(self, *exc: object) -> None:
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()

    def search(self, query: str, *, max_cards: int = 8) -> list[VivinoCandidate]:
        """검색어로 vivino 검색 → 와인 후보 목록."""
        assert self._page is not None, "VivinoBrowser 는 with 블록 안에서 사용"
        page = self._page
        url = SEARCH_URL.format(q=query.replace(" ", "%20"))
        try:
            page.goto(url, wait_until="networkidle", timeout=40000)
        except Exception:
            return []
        page.wait_for_timeout(2000)
        if page.locator("[class*=noResultsMessage]").count():
            return []
        cards = page.locator("[class*=wineCard__wineCard]")
        out: list[VivinoCandidate] = []
        seen: set[str] = set()
        for i in range(min(max_cards, cards.count())):
            card = cards.nth(i)
            try:
                text = card.inner_text()
            except Exception:
                continue
            winery, name, rating_avg, rating_count = _parse_card_text(text)
            key = f"{winery}|{name}"
            if key in seen:
                continue
            seen.add(key)
            out.append(VivinoCandidate(name, winery, None, rating_avg, rating_count))
        return out

    def lookup(self, en_name: str) -> MatchResult:
        """영문 와인명 → vivino 평점 매칭 (전체명 → 실패 시 winery 재시도)."""
        result = best_match(en_name, self.search(en_name))
        if not result.matched:
            winery = en_name.split(",")[0].strip()
            if winery and winery.lower() != en_name.lower():
                alt = best_match(en_name, self.search(winery))
                if alt.confidence > result.confidence:
                    result = alt
        return result
