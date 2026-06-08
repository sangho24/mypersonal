"""v2 rigor pass for the Paris-19h phase-shift / audio-peak findings.

Fixes v1 caveats:
  (1) TZ-aware hourly profiles, per-day TZ inferred from Timeline-dominant country.
  (2) Bootstrap CIs on the Paris/Seoul 19h ratio (1000 resamples of days).
  (3) Add Spain, UK, Italy as additional cities (with actual day counts noted).
  (4) Annual cycle (YoY) — Feb 2024 vs Feb 2025 vs Feb 2026 same-month comparison.
  (5) Weekend-effect bootstrap CIs (Sunday vs weekday) for Seoul and Paris.
  (6) Audio listening peak hour: TZ-corrected, bootstrap CI on the 18h-peak value
      and on the arg-max-hour distribution.

Output: prints summary to stdout AND writes a JSON dump to
        results/health/seoul_paris_v2.json for downstream figure code.

Hard-coded inputs (same as v1):
  /Users/sangho/Downloads/apple_health_export/내보내기.xml
  /Users/sangho/Downloads/location-history.json
"""
from __future__ import annotations

import json
import math
import random
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date, datetime, time, timezone, timedelta
from pathlib import Path
from statistics import mean, median

HEALTH_XML = Path("/Users/sangho/Downloads/apple_health_export/내보내기.xml")
TIMELINE_JSON = Path("/Users/sangho/Downloads/location-history.json")
OUT_JSON = Path("/Users/sangho/Desktop/빅데이터컴퓨팅/wine-mab-project/results/health/seoul_paris_v2.json")

# Country-level bounding boxes (broad — covers full mainland)
KR_BOX = (33.0, 39.5, 124.0, 132.0)
FR_BOX = (41.0, 51.5,  -5.5,   9.5)
UK_BOX = (49.5, 60.5,  -8.5,   2.0)
SP_BOX = (35.5, 44.0, -10.0,   4.5)
IT_BOX = (36.0, 47.5,   6.0,  19.0)

# Country -> IANA tz offset (hours from UTC). We use fixed offsets per record
# rather than IANA to stay scipy/pytz-free; Apple Health timestamps already
# carry a numeric offset in their string so we honour THAT directly when
# parsing. The country->offset map below is only used when we need the
# "local-day timezone" for hourly binning of records whose own offset matches
# the day's dominant country.
COUNTRY_TZ_OFFSET_HOURS = {
    "KR": 9.0,   # KST, no DST
    "FR": 1.0,   # CET (+1 winter, +2 summer); we resolve from record offset
    "UK": 0.0,   # GMT (+0 winter, +1 BST summer); resolved from record offset
    "SP": 1.0,   # CET
    "IT": 1.0,   # CET
}

# Reproducibility
random.seed(20200572)


# ----------------------------- Timeline parsing -----------------------------

def parse_geo(s: str) -> tuple[float, float] | None:
    if not s or not s.startswith("geo:"):
        return None
    try:
        lat_s, lon_s = s[4:].split(",")
        return float(lat_s), float(lon_s)
    except ValueError:
        return None


def in_box(lat: float, lon: float, box: tuple[float, float, float, float]) -> bool:
    return box[0] <= lat <= box[1] and box[2] <= lon <= box[3]


def classify_country(lat: float, lon: float) -> str | None:
    # Check KR first (no overlap risk), then EU boxes — note FR box overlaps
    # nothing relevant in our data.
    if in_box(lat, lon, KR_BOX):
        return "KR"
    if in_box(lat, lon, FR_BOX):
        return "FR"
    if in_box(lat, lon, UK_BOX):
        return "UK"
    if in_box(lat, lon, SP_BOX):
        return "SP"
    if in_box(lat, lon, IT_BOX):
        return "IT"
    return None


def parse_iso(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def load_day_to_country() -> dict[date, str]:
    """Day (UTC date) -> dominant country code based on Timeline segment seconds.

    A day's "dominant country" is the country with the most segment-seconds
    that day. We use this to set the per-day local timezone for hourly binning.
    """
    with TIMELINE_JSON.open() as f:
        records = json.load(f)

    day_country_secs: dict[date, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for rec in records:
        start = parse_iso(rec.get("startTime", ""))
        end = parse_iso(rec.get("endTime", ""))
        if not start or not end:
            continue
        # Day key: anchor to the start instant's local (record-offset) date.
        # This is more honest than UTC-date for places like Korea (UTC+9 means
        # a local-midnight ≠ UTC-midnight).
        d_local = start.date()
        secs = max(0.0, (end - start).total_seconds())
        country: str | None = None
        if "visit" in rec:
            g = parse_geo(rec["visit"].get("topCandidate", {}).get("placeLocation", ""))
            if g:
                country = classify_country(*g)
        elif "activity" in rec:
            for k in ("start", "end"):
                g = parse_geo(rec["activity"].get(k, ""))
                if g:
                    c = classify_country(*g)
                    if c:
                        country = c
                        break
        if country:
            day_country_secs[d_local][country] += secs

    day_to_country: dict[date, str] = {}
    for d, m in day_country_secs.items():
        day_to_country[d] = max(m.items(), key=lambda kv: kv[1])[0]
    return day_to_country


# ----------------------------- Apple Health hourly parsing -----------------------------

def parse_apple_dt(s: str) -> datetime | None:
    """Apple format: '2025-02-25 09:42:14 +0900'  ->  tz-aware datetime."""
    if not s:
        return None
    try:
        # Strip into base + offset
        base = s[:19]
        off = s[20:25] if len(s) >= 25 else "+0000"
        sign = 1 if off[0] == "+" else -1
        hh = int(off[1:3]); mm = int(off[3:5])
        delta = timedelta(hours=hh, minutes=mm) * sign
        dt = datetime.strptime(base, "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone(delta))
    except Exception:
        return None


def load_health_hourly_audio_and_steps() -> tuple[
    dict[date, list[tuple[int, float]]],  # audio: day -> [(hour_local, dB)]
    dict[date, list[tuple[int, float]]],  # steps: day -> [(hour_local, steps)]
    dict[date, float],                    # daily_steps_sum
    dict[date, float],                    # daily_audio_max
    dict[date, float],                    # daily_audio_mean
]:
    """Stream Apple Health XML; for audio + steps records keep (local-hour, value).

    Local-hour is computed from the record's own tz-offset (the +0900-style
    suffix). That offset is reliable: it's what the iPhone wrote at the time
    the sample was recorded, so it already encodes whether the user was in
    Seoul, Paris (CET / CEST), etc. We use the *record's* offset directly,
    NOT the Timeline-dominant country, to avoid double-correction.

    The Timeline-dominant country is still used at the day-level to label
    each day's country (for grouping into Seoul / Paris / etc cohorts).
    """
    audio_hourly: dict[date, list[tuple[int, float]]] = defaultdict(list)
    steps_hourly: dict[date, list[tuple[int, float]]] = defaultdict(list)
    steps_sum: dict[date, float] = defaultdict(float)
    audio_vals: dict[date, list[float]] = defaultdict(list)

    target = {
        "HKQuantityTypeIdentifierStepCount",
        "HKQuantityTypeIdentifierHeadphoneAudioExposure",
    }

    for _, elem in ET.iterparse(HEALTH_XML, events=("end",)):
        if elem.tag != "Record":
            elem.clear()
            continue
        rtype = elem.get("type", "")
        if rtype not in target:
            elem.clear()
            continue
        sd = elem.get("startDate", "")
        dt = parse_apple_dt(sd)
        if not dt:
            elem.clear()
            continue
        local_date = dt.date()
        local_hour = dt.hour
        try:
            val = float(elem.get("value", "nan"))
        except ValueError:
            elem.clear()
            continue
        if rtype == "HKQuantityTypeIdentifierStepCount":
            steps_hourly[local_date].append((local_hour, val))
            steps_sum[local_date] += val
        else:  # audio
            audio_hourly[local_date].append((local_hour, val))
            audio_vals[local_date].append(val)
        elem.clear()

    daily_audio_max = {d: max(v) for d, v in audio_vals.items() if v}
    daily_audio_mean = {d: sum(v) / len(v) for d, v in audio_vals.items() if v}
    return dict(audio_hourly), dict(steps_hourly), dict(steps_sum), daily_audio_max, daily_audio_mean


# ----------------------------- Hourly profile -----------------------------

def hourly_profile(per_day: dict[date, list[tuple[int, float]]],
                   day_set: set[date],
                   agg: str = "sum") -> list[float]:
    """Build hour-of-day profile (24 bins) summed/meaned across the given days.

    For audio (a level metric) we use mean. For steps (count metric) we use sum.
    """
    bins = [0.0] * 24
    counts = [0] * 24
    for d in day_set:
        if d not in per_day:
            continue
        for h, v in per_day[d]:
            if agg == "sum":
                bins[h] += v
            else:
                bins[h] += v
                counts[h] += 1
    if agg == "mean":
        bins = [bins[h] / counts[h] if counts[h] else 0.0 for h in range(24)]
    else:
        # normalize to per-day average so cohorts of different sizes are comparable
        n = max(1, len(day_set))
        bins = [b / n for b in bins]
    return bins


# ----------------------------- Bootstrap helpers -----------------------------

def bootstrap_ratio(per_day_metric: dict[date, list[tuple[int, float]]],
                    days_num: list[date], days_den: list[date],
                    hour: int, n_boot: int = 1000,
                    agg: str = "sum") -> tuple[float, float, float]:
    """Bootstrap CI on ratio (mean-per-day @ hour, group_num) / (... group_den).

    Returns (point_estimate, ci_lo_2.5, ci_hi_97.5).
    Resampling is over DAYS (the natural i.i.d. unit) — within each day we
    sum/mean the values at the target hour.
    """
    def per_day_value(d: date) -> float:
        if d not in per_day_metric:
            return 0.0
        vals = [v for h, v in per_day_metric[d] if h == hour]
        if not vals:
            return 0.0
        return sum(vals) if agg == "sum" else sum(vals) / len(vals)

    nv = [per_day_value(d) for d in days_num]
    dv = [per_day_value(d) for d in days_den]

    def ratio(nv: list[float], dv: list[float]) -> float:
        mn = sum(nv) / len(nv) if nv else 0.0
        md = sum(dv) / len(dv) if dv else 0.0
        return mn / md if md > 0 else float("nan")

    point = ratio(nv, dv)
    boots = []
    rng = random.Random(20200572)
    for _ in range(n_boot):
        nb = [nv[rng.randrange(len(nv))] for _ in range(len(nv))] if nv else []
        db = [dv[rng.randrange(len(dv))] for _ in range(len(dv))] if dv else []
        boots.append(ratio(nb, db))
    boots = [b for b in boots if not math.isnan(b)]
    boots.sort()
    if not boots:
        return point, float("nan"), float("nan")
    lo = boots[int(0.025 * len(boots))]
    hi = boots[int(0.975 * len(boots))]
    return point, lo, hi


def bootstrap_diff_share(per_day_metric: dict[date, list[tuple[int, float]]],
                         days_a: list[date], days_b: list[date],
                         hour: int, n_boot: int = 1000,
                         agg: str = "sum") -> tuple[float, float, float]:
    """Bootstrap CI on (share-at-hour A) - (share-at-hour B), where share =
    value-at-hour / day-total. Useful for distinguishing "everyone walks more
    in city X" from "city X concentrates activity into hour h".
    """
    def per_day_share(d: date) -> float | None:
        if d not in per_day_metric:
            return None
        bins = [0.0] * 24
        cnts = [0] * 24
        for h, v in per_day_metric[d]:
            bins[h] += v
            cnts[h] += 1
        if agg == "mean":
            tot_bins = [bins[h] / cnts[h] if cnts[h] else 0.0 for h in range(24)]
        else:
            tot_bins = bins
        total = sum(tot_bins)
        if total <= 0:
            return None
        return tot_bins[hour] / total

    a = [s for s in (per_day_share(d) for d in days_a) if s is not None]
    b = [s for s in (per_day_share(d) for d in days_b) if s is not None]
    if not a or not b:
        return float("nan"), float("nan"), float("nan")
    point = (sum(a) / len(a)) - (sum(b) / len(b))
    boots = []
    rng = random.Random(20200572 + 1)
    for _ in range(n_boot):
        ab = [a[rng.randrange(len(a))] for _ in range(len(a))]
        bb = [b[rng.randrange(len(b))] for _ in range(len(b))]
        boots.append(sum(ab) / len(ab) - sum(bb) / len(bb))
    boots.sort()
    return point, boots[int(0.025 * len(boots))], boots[int(0.975 * len(boots))]


def bootstrap_peak_hour(per_day_metric: dict[date, list[tuple[int, float]]],
                        days: list[date], n_boot: int = 1000,
                        agg: str = "mean") -> tuple[int, dict[int, float]]:
    """Bootstrap distribution of arg-max-hour across resampled day-sets.

    Returns (point_estimate_peak_hour, hist of fractions for each hour).
    """
    def profile_of(ds: list[date]) -> list[float]:
        bins = [0.0] * 24
        cnts = [0] * 24
        n_days = len(ds)
        for d in ds:
            if d not in per_day_metric:
                continue
            for h, v in per_day_metric[d]:
                bins[h] += v
                cnts[h] += 1
        if agg == "mean":
            return [bins[h] / cnts[h] if cnts[h] else 0.0 for h in range(24)]
        return [b / max(1, n_days) for b in bins]

    point = profile_of(days)
    point_peak = max(range(24), key=lambda h: point[h])
    rng = random.Random(20200572 + 2)
    hist = Counter()
    for _ in range(n_boot):
        ds = [days[rng.randrange(len(days))] for _ in range(len(days))]
        prof = profile_of(ds)
        peak = max(range(24), key=lambda h: prof[h])
        hist[peak] += 1
    hist_frac = {h: hist[h] / n_boot for h in sorted(hist.keys())}
    return point_peak, hist_frac


def bootstrap_value_at_hour(per_day_metric: dict[date, list[tuple[int, float]]],
                            days: list[date], hour: int,
                            n_boot: int = 1000, agg: str = "mean") -> tuple[float, float, float]:
    """Bootstrap CI on the value (mean dB or steps) at the given hour."""
    def per_day_value(d: date) -> float | None:
        if d not in per_day_metric:
            return None
        vals = [v for h, v in per_day_metric[d] if h == hour]
        if not vals:
            return None
        return sum(vals) if agg == "sum" else sum(vals) / len(vals)

    xs = [v for v in (per_day_value(d) for d in days) if v is not None]
    if not xs:
        return float("nan"), float("nan"), float("nan")
    point = sum(xs) / len(xs)
    boots = []
    rng = random.Random(20200572 + 3)
    for _ in range(n_boot):
        b = [xs[rng.randrange(len(xs))] for _ in range(len(xs))]
        boots.append(sum(b) / len(b))
    boots.sort()
    return point, boots[int(0.025 * len(boots))], boots[int(0.975 * len(boots))]


# ----------------------------- Main -----------------------------

def main() -> None:
    print("[v2] loading timeline …")
    day_to_country = load_day_to_country()
    by_country: dict[str, list[date]] = defaultdict(list)
    for d, c in day_to_country.items():
        by_country[c].append(d)
    for c in sorted(by_country):
        by_country[c].sort()
        print(f"  {c}: {len(by_country[c])} days  "
              f"[{by_country[c][0]} .. {by_country[c][-1]}]")

    print("[v2] streaming Apple Health …")
    audio_hourly, steps_hourly, steps_sum, audio_max, audio_mean = load_health_hourly_audio_and_steps()
    print(f"  audio days={len(audio_hourly)}  steps days={len(steps_hourly)}")

    # -------- weekday / weekend split helpers --------
    def weekday(d: date) -> bool: return d.weekday() < 5
    def sunday(d: date) -> bool: return d.weekday() == 6

    seoul = by_country.get("KR", [])
    paris = by_country.get("FR", [])
    spain = by_country.get("SP", [])
    uk    = by_country.get("UK", [])
    italy = by_country.get("IT", [])

    seoul_wd = [d for d in seoul if weekday(d)]
    paris_wd = [d for d in paris if weekday(d)]
    seoul_sun = [d for d in seoul if sunday(d)]
    paris_sun = [d for d in paris if sunday(d)]

    out: dict = {
        "meta": {
            "generated": datetime.now().isoformat(timespec="seconds"),
            "tz_strategy": "per-record offset from Apple Health string (e.g. +0900)",
            "day_country_strategy": "Timeline-dominant country per LOCAL-start-date",
            "n_boot": 1000,
            "seed": 20200572,
        },
        "n_days_by_country": {c: len(ds) for c, ds in by_country.items()},
    }

    # ============================================================
    # (1)+(2) Paris 19h vs Seoul 19h ratio, TZ-corrected + bootstrap
    # ============================================================
    print("\n=== (1)+(2) Paris-19h vs Seoul-19h ratio (TZ-aware, bootstrap) ===")
    # We use steps as the activity metric (v1's "phase-shift" was about
    # evening activity intensity). The v1 ratio 2.53 was on per-day-mean
    # steps at hour=19 (local).
    pt, lo, hi = bootstrap_ratio(steps_hourly, paris_wd, seoul_wd, hour=19, agg="sum")
    print(f"  steps@19h ratio Paris/Seoul (weekday): {pt:.3f}  95% CI [{lo:.3f}, {hi:.3f}]"
          f"  n_paris_wd={len(paris_wd)}  n_seoul_wd={len(seoul_wd)}")
    out["paris_19h_ratio"] = {
        "metric": "steps_at_hour19_per_day_sum",
        "subset": "weekday",
        "point": pt, "ci_lo": lo, "ci_hi": hi,
        "n_paris_wd": len(paris_wd), "n_seoul_wd": len(seoul_wd),
    }

    # Share-based variant: factor out overall activity level
    pt2, lo2, hi2 = bootstrap_diff_share(steps_hourly, paris_wd, seoul_wd, hour=19, agg="sum")
    print(f"  steps@19h SHARE-diff (Paris - Seoul): {pt2:+.4f}  95% CI [{lo2:+.4f}, {hi2:+.4f}]")
    out["paris_19h_share_diff"] = {
        "point": pt2, "ci_lo": lo2, "ci_hi": hi2,
        "interpretation": "diff in (steps_at_19 / day_total); positive => Paris concentrates evening more",
    }

    # ============================================================
    # (3) Generalize to Spain, UK, Italy
    # ============================================================
    print("\n=== (3) Evening-peak generalization to other EU cities ===")
    extras = {"SP": spain, "UK": uk, "IT": italy}
    out["other_eu_19h_ratio_vs_seoul"] = {}
    for name, days in extras.items():
        if len(days) < 2:
            print(f"  {name}: only {len(days)} day(s), skipping")
            out["other_eu_19h_ratio_vs_seoul"][name] = {"n": len(days), "skipped": True}
            continue
        wd = [d for d in days if weekday(d)]
        if len(wd) < 2:
            wd = days  # too small to require weekday-only
            note = "no weekday-only filter (n too small)"
        else:
            note = "weekday-only"
        pt_x, lo_x, hi_x = bootstrap_ratio(steps_hourly, wd, seoul_wd, hour=19, agg="sum")
        print(f"  {name} steps@19h / Seoul-wd : {pt_x:.3f}  95% CI [{lo_x:.3f}, {hi_x:.3f}]"
              f"  ({note}, n={len(wd)})")
        out["other_eu_19h_ratio_vs_seoul"][name] = {
            "point": pt_x, "ci_lo": lo_x, "ci_hi": hi_x, "n": len(wd), "note": note,
        }

    # ============================================================
    # (4) Annual cycle / YoY same-month
    # ============================================================
    print("\n=== (4) YoY same-month profiles: Feb 2024 vs Feb 2025 vs Feb 2026 ===")
    def in_month(d: date, y: int, m: int) -> bool:
        return d.year == y and d.month == m
    feb24_all = [d for d in steps_hourly.keys() if in_month(d, 2024, 2)]
    feb25_all = [d for d in steps_hourly.keys() if in_month(d, 2024, 2)] # filled below
    feb25 = [d for d in day_to_country if in_month(d, 2025, 2)]
    feb26 = [d for d in day_to_country if in_month(d, 2026, 2)]
    feb25_FR = [d for d in feb25 if day_to_country.get(d) == "FR"]
    feb25_KR = [d for d in feb25 if day_to_country.get(d) == "KR"]
    feb26_KR = [d for d in feb26 if day_to_country.get(d) == "KR"]

    print(f"  Feb 2024: timeline-labeled days = {sum(1 for d in day_to_country if in_month(d,2024,2))}; "
          f"health-records days = {len(feb24_all)}")
    print(f"  Feb 2025: total={len(feb25)}, FR={len(feb25_FR)}, KR={len(feb25_KR)}")
    print(f"  Feb 2026: total={len(feb26)}, KR={len(feb26_KR)}")
    out["yoy_feb"] = {
        "feb2024_n": sum(1 for d in day_to_country if in_month(d, 2024, 2)),
        "feb2025_FR_n": len(feb25_FR),
        "feb2025_KR_n": len(feb25_KR),
        "feb2026_KR_n": len(feb26_KR),
    }

    if len(feb25_FR) >= 2 and len(feb26_KR) >= 5:
        prof_FR25 = hourly_profile(steps_hourly, set(feb25_FR), agg="sum")
        prof_KR26 = hourly_profile(steps_hourly, set(feb26_KR), agg="sum")
        # Ratio at 19h, FR-Feb25 vs KR-Feb26 (same month, different country)
        pt_y, lo_y, hi_y = bootstrap_ratio(steps_hourly, feb25_FR, feb26_KR, hour=19, agg="sum")
        print(f"  Feb-only ratio FR2025/KR2026 @19h: {pt_y:.3f}  95% CI [{lo_y:.3f}, {hi_y:.3f}]")
        out["yoy_feb"]["feb_ratio_FR25_vs_KR26_at19"] = {"point": pt_y, "ci_lo": lo_y, "ci_hi": hi_y}
        out["yoy_feb"]["profile_FR_feb2025"] = prof_FR25
        out["yoy_feb"]["profile_KR_feb2026"] = prof_KR26

    # Same-country YoY (only feasible for Korea: Feb 2026 is in data, but
    # Feb 2025 has no KR days, Feb 2024 has no data at all).
    if len(feb25_KR) >= 5 and len(feb26_KR) >= 5:
        pt_kr, lo_kr, hi_kr = bootstrap_ratio(steps_hourly, feb26_KR, feb25_KR, hour=19, agg="sum")
        print(f"  Same-city YoY KR Feb2026/Feb2025 @19h: {pt_kr:.3f}  95% CI [{lo_kr:.3f}, {hi_kr:.3f}]")
        out["yoy_feb"]["KR_feb_yoy_ratio_2026_over_2025"] = {
            "point": pt_kr, "ci_lo": lo_kr, "ci_hi": hi_kr,
        }
    else:
        print("  SAME-CITY YoY for Feb is INFEASIBLE: KR-Feb2025 n="
              f"{len(feb25_KR)}, KR-Feb2024 n=0 (no data prior to 2025-06).")
        out["yoy_feb"]["same_city_yoy_feasible"] = False

    # ============================================================
    # (5) Weekend-effect bootstrap CIs
    # ============================================================
    print("\n=== (5) Weekend effect bootstrap CIs ===")
    # We bootstrap the ratio (Sunday steps@19h) / (Weekday steps@19h) per city
    for label, sun, wd in [("Seoul", seoul_sun, seoul_wd),
                            ("Paris", paris_sun, paris_wd)]:
        if len(sun) >= 2 and len(wd) >= 5:
            pt_s, lo_s, hi_s = bootstrap_ratio(steps_hourly, sun, wd, hour=19, agg="sum")
            print(f"  {label} Sun/Weekday @19h: {pt_s:.3f}  95% CI [{lo_s:.3f}, {hi_s:.3f}]"
                  f"  (n_sun={len(sun)}, n_wd={len(wd)})")
            out.setdefault("weekend_effect", {})[label] = {
                "ratio_sun_over_wd_at19": {"point": pt_s, "ci_lo": lo_s, "ci_hi": hi_s,
                                            "n_sun": len(sun), "n_wd": len(wd)}
            }
        else:
            print(f"  {label}: insufficient (n_sun={len(sun)}, n_wd={len(wd)})")

    # ============================================================
    # (6) Audio listening peak hour: TZ-corrected, bootstrap CI
    # ============================================================
    print("\n=== (6) Audio listening peak hour (TZ-corrected, bootstrap) ===")
    # All days with audio data, by country
    audio_days = set(audio_hourly.keys())
    seoul_audio = [d for d in seoul if d in audio_days]
    paris_audio = [d for d in paris if d in audio_days]
    all_audio = sorted(audio_days)
    print(f"  audio coverage: total={len(all_audio)}, Seoul={len(seoul_audio)}, Paris={len(paris_audio)}")

    peak_all, hist_all = bootstrap_peak_hour(audio_hourly, all_audio, agg="mean")
    print(f"  ALL-days audio peak hour: point={peak_all}  bootstrap arg-max dist (top 5):")
    for h, frac in sorted(hist_all.items(), key=lambda kv: -kv[1])[:5]:
        print(f"      hour={h:>2}h  frac={frac:.3f}")
    out["audio_peak_hour"] = {
        "all_days": {"point_peak": peak_all, "hist": hist_all, "n": len(all_audio)},
    }

    # Bootstrap dB level CI at the 18h v1-peak
    pt_18, lo_18, hi_18 = bootstrap_value_at_hour(audio_hourly, all_audio, hour=18, agg="mean")
    print(f"  Audio @18h (mean dB across all days): {pt_18:.2f}  95% CI [{lo_18:.2f}, {hi_18:.2f}]")
    out["audio_peak_hour"]["value_at_18h"] = {
        "point_mean_dB": pt_18, "ci_lo": lo_18, "ci_hi": hi_18, "n": len(all_audio),
    }

    if len(seoul_audio) >= 5:
        peak_s, hist_s = bootstrap_peak_hour(audio_hourly, seoul_audio, agg="mean")
        pt_s18, lo_s18, hi_s18 = bootstrap_value_at_hour(audio_hourly, seoul_audio, 18, agg="mean")
        print(f"  Seoul-only peak hour: {peak_s}; 18h dB CI [{lo_s18:.2f},{hi_s18:.2f}]")
        out["audio_peak_hour"]["seoul"] = {
            "point_peak": peak_s, "hist": hist_s,
            "value_at_18h": {"point_mean_dB": pt_s18, "ci_lo": lo_s18, "ci_hi": hi_s18},
            "n": len(seoul_audio),
        }
    if len(paris_audio) >= 5:
        peak_p, hist_p = bootstrap_peak_hour(audio_hourly, paris_audio, agg="mean")
        pt_p18, lo_p18, hi_p18 = bootstrap_value_at_hour(audio_hourly, paris_audio, 18, agg="mean")
        pt_p19, lo_p19, hi_p19 = bootstrap_value_at_hour(audio_hourly, paris_audio, 19, agg="mean")
        print(f"  Paris-only peak hour: {peak_p}; 18h dB CI [{lo_p18:.2f},{hi_p18:.2f}]; "
              f"19h dB CI [{lo_p19:.2f},{hi_p19:.2f}]")
        out["audio_peak_hour"]["paris"] = {
            "point_peak": peak_p, "hist": hist_p,
            "value_at_18h": {"point_mean_dB": pt_p18, "ci_lo": lo_p18, "ci_hi": hi_p18},
            "value_at_19h": {"point_mean_dB": pt_p19, "ci_lo": lo_p19, "ci_hi": hi_p19},
            "n": len(paris_audio),
        }

    # ============================================================
    # Dump full hourly profiles for figure rendering downstream
    # ============================================================
    out["hourly_profiles"] = {
        "steps_seoul_wd": hourly_profile(steps_hourly, set(seoul_wd), agg="sum"),
        "steps_paris_wd": hourly_profile(steps_hourly, set(paris_wd), agg="sum"),
        "audio_seoul_all": hourly_profile(audio_hourly, set(seoul_audio), agg="mean"),
        "audio_paris_all": hourly_profile(audio_hourly, set(paris_audio), agg="mean"),
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\n[v2] wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
