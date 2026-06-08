"""Seoul vs Paris within-subject quasi-experiment — statistical power scout.

Outputs are printed to stdout; no I/O side effects elsewhere.
"""
from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, median

HEALTH_XML = Path("/Users/sangho/Downloads/apple_health_export/내보내기.xml")
TIMELINE_JSON = Path("/Users/sangho/Downloads/location-history.json")

# Recent window for matching life-stage (per prompt: 2024-12 onwards)
WINDOW_START = date(2024, 12, 1)
WINDOW_END = date(2025, 12, 31)

# Approx country boxes (lat, lon) — coarse but adequate for Seoul vs Paris.
SEOUL_BOX = (37.3, 37.7, 126.7, 127.3)   # lat_min, lat_max, lon_min, lon_max
PARIS_BOX = (48.7, 49.0, 2.1, 2.5)


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


def classify_city(lat: float, lon: float) -> str | None:
    if in_box(lat, lon, SEOUL_BOX):
        return "Seoul"
    if in_box(lat, lon, PARIS_BOX):
        return "Paris"
    return None


def parse_iso(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def load_timeline_city_map() -> tuple[dict[date, str], dict[str, dict[str, int]]]:
    """Return (date -> dominant city) and (city -> activity_type -> count_segments)."""
    with TIMELINE_JSON.open() as f:
        records = json.load(f)

    # date -> city -> seconds
    day_city_secs: dict[date, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    activity_mix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for rec in records:
        start = parse_iso(rec.get("startTime", ""))
        end = parse_iso(rec.get("endTime", ""))
        if not start or not end:
            continue
        # localize to record-local date (naive based on tz offset already in iso)
        d = start.astimezone(timezone.utc).date()
        secs = max(0.0, (end - start).total_seconds())

        city: str | None = None
        if "visit" in rec:
            top = rec["visit"].get("topCandidate", {})
            geo = parse_geo(top.get("placeLocation", ""))
            if geo:
                city = classify_city(*geo)
        elif "activity" in rec:
            act = rec["activity"]
            geo_s = parse_geo(act.get("start", ""))
            geo_e = parse_geo(act.get("end", ""))
            cities = [classify_city(*g) for g in (geo_s, geo_e) if g]
            cities = [c for c in cities if c]
            if cities:
                city = cities[0]
            atype = act.get("topCandidate", {}).get("type", "unknown")
            if city:
                activity_mix[city][atype] += 1
        if city:
            day_city_secs[d][city] += secs

    day_to_city: dict[date, str] = {}
    for d, city_secs in day_city_secs.items():
        dominant = max(city_secs.items(), key=lambda kv: kv[1])[0]
        day_to_city[d] = dominant
    return day_to_city, dict(activity_mix)


# ----------------------------- Apple Health parsing -----------------------------

METRIC_MAP = {
    "HKQuantityTypeIdentifierStepCount": ("daily_steps", "sum"),
    "HKQuantityTypeIdentifierWalkingSpeed": ("walking_speed", "mean"),
    "HKQuantityTypeIdentifierWalkingStepLength": ("step_length", "mean"),
    "HKQuantityTypeIdentifierHeadphoneAudioExposure": ("daily_audio", "both"),
}


def parse_apple_date(s: str) -> date | None:
    # Apple format: 2025-02-25 09:42:14 +0900
    try:
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S").date()
    except Exception:
        return None


def load_health_daily() -> dict[str, dict[date, float]]:
    """Return metric_name -> day -> aggregated_value."""
    sums: dict[str, dict[date, float]] = defaultdict(lambda: defaultdict(float))
    means_data: dict[str, dict[date, list[float]]] = defaultdict(lambda: defaultdict(list))
    audio_data: dict[date, list[float]] = defaultdict(list)

    # iterparse to keep memory low
    for _, elem in ET.iterparse(HEALTH_XML, events=("end",)):
        if elem.tag != "Record":
            elem.clear()
            continue
        rtype = elem.get("type", "")
        if rtype not in METRIC_MAP:
            elem.clear()
            continue
        sd = elem.get("startDate", "")
        d = parse_apple_date(sd)
        if not d or d < WINDOW_START or d > WINDOW_END:
            elem.clear()
            continue
        try:
            val = float(elem.get("value", "nan"))
        except ValueError:
            elem.clear()
            continue
        name, agg = METRIC_MAP[rtype]
        if agg == "sum":
            sums[name][d] += val
        elif agg == "mean":
            means_data[name][d].append(val)
        elif agg == "both":
            audio_data[d].append(val)
        elem.clear()

    result: dict[str, dict[date, float]] = {}
    for name, dct in sums.items():
        result[name] = dict(dct)
    for name, dct in means_data.items():
        result[name] = {d: sum(vs) / len(vs) for d, vs in dct.items() if vs}
    if audio_data:
        result["daily_audio_max_dB"] = {d: max(vs) for d, vs in audio_data.items()}
        result["daily_audio_mean_dB"] = {d: sum(vs) / len(vs) for d, vs in audio_data.items()}
    return result


# ----------------------------- Statistics (no scipy) -----------------------------

def stats_summary(xs: list[float]) -> dict[str, float]:
    if not xs:
        return {"n": 0, "mean": float("nan"), "median": float("nan"),
                "q1": float("nan"), "q3": float("nan"), "sd": float("nan")}
    xs_sorted = sorted(xs)
    n = len(xs_sorted)
    m = mean(xs_sorted)
    med = median(xs_sorted)
    q1 = xs_sorted[int(0.25 * (n - 1))]
    q3 = xs_sorted[int(0.75 * (n - 1))]
    if n > 1:
        var = sum((x - m) ** 2 for x in xs_sorted) / (n - 1)
        sd = math.sqrt(var)
    else:
        sd = float("nan")
    return {"n": n, "mean": m, "median": med, "q1": q1, "q3": q3, "sd": sd}


def welch_t(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """Return (t-stat, df, two-sided p-value approx)."""
    nx, ny = len(xs), len(ys)
    if nx < 2 or ny < 2:
        return float("nan"), float("nan"), float("nan")
    mx, my = mean(xs), mean(ys)
    vx = sum((x - mx) ** 2 for x in xs) / (nx - 1)
    vy = sum((y - my) ** 2 for y in ys) / (ny - 1)
    se = math.sqrt(vx / nx + vy / ny)
    if se == 0:
        return float("nan"), float("nan"), float("nan")
    t = (mx - my) / se
    # Welch-Satterthwaite df
    num = (vx / nx + vy / ny) ** 2
    den = (vx ** 2) / ((nx ** 2) * (nx - 1)) + (vy ** 2) / ((ny ** 2) * (ny - 1))
    df = num / den if den > 0 else float("nan")
    # two-sided p via Student's t cdf approximation (Abramowitz-like)
    p = 2 * (1 - student_t_cdf(abs(t), df))
    return t, df, p


def student_t_cdf(t: float, df: float) -> float:
    """Approximate Student's t CDF using incomplete beta."""
    if math.isnan(t) or math.isnan(df) or df <= 0:
        return float("nan")
    x = df / (df + t * t)
    # regularized incomplete beta I_x(df/2, 1/2)
    ib = reg_incomplete_beta(x, df / 2.0, 0.5)
    return 1.0 - 0.5 * ib


def reg_incomplete_beta(x: float, a: float, b: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    # continued fraction (Lentz) — see Numerical Recipes 6.4
    bt = math.exp(a * math.log(x) + b * math.log(1 - x) - lbeta)
    if x < (a + 1) / (a + b + 2):
        return bt * betacf(x, a, b) / a
    return 1 - bt * betacf(1 - x, b, a) / b


def betacf(x: float, a: float, b: float, maxit: int = 200, eps: float = 3e-7) -> float:
    qab = a + b
    qap = a + 1
    qam = a - 1
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, maxit + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            return h
    return h


def cohens_d(xs: list[float], ys: list[float]) -> float:
    nx, ny = len(xs), len(ys)
    if nx < 2 or ny < 2:
        return float("nan")
    mx, my = mean(xs), mean(ys)
    vx = sum((x - mx) ** 2 for x in xs) / (nx - 1)
    vy = sum((y - my) ** 2 for y in ys) / (ny - 1)
    pooled = math.sqrt(((nx - 1) * vx + (ny - 1) * vy) / (nx + ny - 2))
    return (mx - my) / pooled if pooled > 0 else float("nan")


def chi2_test(observed: list[list[float]]) -> tuple[float, int, float]:
    """Pearson chi-square on 2xk contingency. Returns (chi2, df, p)."""
    rows = len(observed)
    cols = len(observed[0])
    row_tot = [sum(r) for r in observed]
    col_tot = [sum(observed[i][j] for i in range(rows)) for j in range(cols)]
    grand = sum(row_tot)
    chi2 = 0.0
    for i in range(rows):
        for j in range(cols):
            expected = row_tot[i] * col_tot[j] / grand if grand else 0.0
            if expected > 0:
                chi2 += (observed[i][j] - expected) ** 2 / expected
    df = (rows - 1) * (cols - 1)
    p = 1 - chi2_cdf(chi2, df)
    return chi2, df, p


def chi2_cdf(x: float, k: int) -> float:
    if x <= 0 or k <= 0:
        return 0.0
    return reg_gamma_lower(k / 2.0, x / 2.0)


def reg_gamma_lower(a: float, x: float) -> float:
    if x < 0 or a <= 0:
        return 0.0
    if x < a + 1:
        # series
        term = 1.0 / a
        s = term
        ap = a
        for _ in range(500):
            ap += 1
            term *= x / ap
            s += term
            if abs(term) < abs(s) * 1e-10:
                break
        return s * math.exp(-x + a * math.log(x) - math.lgamma(a))
    # continued fraction for upper
    b = x + 1.0 - a
    c = 1e30
    d = 1.0 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < 1e-30:
            d = 1e-30
        c = b + an / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-10:
            break
    upper = math.exp(-x + a * math.log(x) - math.lgamma(a)) * h
    return 1.0 - upper


# ----------------------------- Main analysis -----------------------------

def main() -> None:
    print(f"[load] timeline {TIMELINE_JSON.name}")
    day_to_city, activity_mix = load_timeline_city_map()
    n_seoul_days = sum(1 for c in day_to_city.values() if c == "Seoul")
    n_paris_days = sum(1 for c in day_to_city.values() if c == "Paris")
    print(f"[timeline] total labeled days = {len(day_to_city)}, Seoul={n_seoul_days}, Paris={n_paris_days}")

    # Window-filter day -> city
    day_to_city = {d: c for d, c in day_to_city.items()
                   if WINDOW_START <= d <= WINDOW_END}
    n_seoul_days = sum(1 for c in day_to_city.values() if c == "Seoul")
    n_paris_days = sum(1 for c in day_to_city.values() if c == "Paris")
    print(f"[timeline] after window filter Seoul={n_seoul_days}, Paris={n_paris_days}")

    # date ranges actually present
    seoul_dates = sorted(d for d, c in day_to_city.items() if c == "Seoul")
    paris_dates = sorted(d for d, c in day_to_city.items() if c == "Paris")
    if seoul_dates:
        print(f"[seoul range] {seoul_dates[0]} .. {seoul_dates[-1]}")
    if paris_dates:
        print(f"[paris range] {paris_dates[0]} .. {paris_dates[-1]}")

    print(f"[load] apple health {HEALTH_XML.name}")
    metrics = load_health_daily()
    for name, dct in metrics.items():
        print(f"[health] {name}: n_days={len(dct)}")

    print("\n=== METRIC COMPARISONS ===")
    results = []
    for name in ["daily_steps", "walking_speed", "step_length",
                 "daily_audio_max_dB", "daily_audio_mean_dB"]:
        dct = metrics.get(name)
        if not dct:
            print(f"[{name}] METRIC MISSING in export")
            continue
        seoul_vals = [dct[d] for d in seoul_dates if d in dct]
        paris_vals = [dct[d] for d in paris_dates if d in dct]
        s = stats_summary(seoul_vals)
        p = stats_summary(paris_vals)
        t, df, pval = welch_t(seoul_vals, paris_vals)
        d_eff = cohens_d(seoul_vals, paris_vals)
        results.append((name, s, p, t, df, pval, d_eff))
        print(f"\n[{name}]")
        print(f"  Seoul: n={s['n']:>3}  mean={s['mean']:.2f}  median={s['median']:.2f}  "
              f"IQR=[{s['q1']:.2f},{s['q3']:.2f}]  sd={s['sd']:.2f}")
        print(f"  Paris: n={p['n']:>3}  mean={p['mean']:.2f}  median={p['median']:.2f}  "
              f"IQR=[{p['q1']:.2f},{p['q3']:.2f}]  sd={p['sd']:.2f}")
        print(f"  Welch t={t:.3f}  df={df:.1f}  p={pval:.4g}  |  Cohen's d={d_eff:.3f}")

    # Effect-size summary
    big = [name for name, *_, d_eff in results if abs(d_eff) > 0.5]
    print(f"\n[summary] metrics with |Cohen's d|>0.5 = {len(big)} of {len(results)}: {big}")

    # Chi-square on mode mix
    print("\n=== ACTIVITY MODE MIX ===")
    target_modes = ["walking", "in subway", "in bus", "cycling"]
    seoul_counts = [activity_mix.get("Seoul", {}).get(m, 0) for m in target_modes]
    paris_counts = [activity_mix.get("Paris", {}).get(m, 0) for m in target_modes]
    print(f"  modes      : {target_modes}")
    print(f"  Seoul cnt  : {seoul_counts}  total={sum(seoul_counts)}")
    print(f"  Paris cnt  : {paris_counts}  total={sum(paris_counts)}")
    if sum(seoul_counts) > 0 and sum(paris_counts) > 0:
        chi2, df, p = chi2_test([seoul_counts, paris_counts])
        print(f"  chi2={chi2:.3f}  df={df}  p={p:.4g}")
        # Also report shares
        ss = sum(seoul_counts) or 1
        ps = sum(paris_counts) or 1
        print(f"  Seoul share: {[round(c/ss,3) for c in seoul_counts]}")
        print(f"  Paris share: {[round(c/ps,3) for c in paris_counts]}")
    # raw mix dump
    for city, mix in activity_mix.items():
        total = sum(mix.values())
        top = sorted(mix.items(), key=lambda kv: -kv[1])[:8]
        print(f"  [{city}] total_segments={total}  top={top}")


if __name__ == "__main__":
    main()
