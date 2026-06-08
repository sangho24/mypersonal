"""Gait Quality Recovery Mining (v1 underexplored angle).

Mines the walking-quality recovery story:
- Monthly time series of 5 gait metrics: walking_speed, step_length,
  asymmetry, double_support, walking_steadiness, plus step_count.
- Bottom-out and baseline-cross detection per metric.
- Pairwise Pearson correlation matrix across the gait metrics.
- Paris vs Seoul cross-modal contrast with bootstrap CI on the difference.
- Workout-day vs sedentary-day contrast (running days vs zero-distance days).

Pure stdlib + math. No pandas. iterparse for memory.
"""
from __future__ import annotations

import json
import math
import random
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Iterable

HEALTH_XML = Path("/Users/sangho/Downloads/apple_health_export/내보내기.xml")
TIMELINE_JSON = Path("/Users/sangho/Downloads/location-history.json")

# Workout activity types we care about for the running-day contrast
RUNNING_WORKOUT_TYPES = {
    "HKWorkoutActivityTypeRunning",
    "HKWorkoutActivityTypeWalking",  # treat brisk walking too
}

# Gait quality metrics + step count
METRIC_MAP = {
    "HKQuantityTypeIdentifierStepCount":              ("step_count",          "sum"),
    "HKQuantityTypeIdentifierWalkingSpeed":           ("walking_speed",       "mean"),  # km/hr -> m/s
    "HKQuantityTypeIdentifierWalkingStepLength":      ("step_length",         "mean"),  # cm
    "HKQuantityTypeIdentifierWalkingAsymmetryPercentage":     ("asymmetry",            "mean"),  # %
    "HKQuantityTypeIdentifierWalkingDoubleSupportPercentage": ("double_support",       "mean"),  # %
    "HKQuantityTypeIdentifierAppleWalkingSteadiness":         ("walking_steadiness",   "mean"),  # 0..1
}

# Higher-is-better direction
DIRECTION = {
    "walking_speed":     +1,
    "step_length":       +1,
    "walking_steadiness": +1,
    # Lower-is-better — recovery means going DOWN
    "asymmetry":         -1,
    "double_support":    -1,
    "step_count":        +1,
}


def parse_apple_date(s: str) -> date | None:
    try:
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S").date()
    except Exception:
        return None


def parse_iso(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def parse_geo(s: str) -> tuple[float, float] | None:
    if not s or not s.startswith("geo:"):
        return None
    try:
        lat_s, lon_s = s[4:].split(",")
        return float(lat_s), float(lon_s)
    except ValueError:
        return None


SEOUL_BOX = (37.3, 37.7, 126.7, 127.3)
PARIS_BOX = (48.7, 49.0, 2.1, 2.5)


def in_box(lat: float, lon: float, box: tuple[float, float, float, float]) -> bool:
    return box[0] <= lat <= box[1] and box[2] <= lon <= box[3]


def classify_city(lat: float, lon: float) -> str | None:
    if in_box(lat, lon, SEOUL_BOX):
        return "Seoul"
    if in_box(lat, lon, PARIS_BOX):
        return "Paris"
    return None


# ----------------------------- Apple Health load -----------------------------

def load_health_daily() -> tuple[dict[str, dict[date, float]], dict[date, set[str]]]:
    """Return (metric -> day -> value, day -> set(workout_types))."""
    sums: dict[str, dict[date, float]] = defaultdict(lambda: defaultdict(float))
    means_data: dict[str, dict[date, list[float]]] = defaultdict(lambda: defaultdict(list))
    workouts_by_day: dict[date, set[str]] = defaultdict(set)

    for _, elem in ET.iterparse(HEALTH_XML, events=("end",)):
        tag = elem.tag
        if tag == "Workout":
            wt = elem.get("workoutActivityType", "")
            sd = elem.get("startDate", "")
            d = parse_apple_date(sd)
            if d:
                workouts_by_day[d].add(wt)
            elem.clear()
            continue
        if tag != "Record":
            elem.clear()
            continue
        rtype = elem.get("type", "")
        if rtype not in METRIC_MAP:
            elem.clear()
            continue
        sd = elem.get("startDate", "")
        d = parse_apple_date(sd)
        if not d:
            elem.clear()
            continue
        try:
            val = float(elem.get("value", "nan"))
        except ValueError:
            elem.clear()
            continue
        unit = elem.get("unit", "")
        name, agg = METRIC_MAP[rtype]
        # Normalize units
        if name == "walking_speed" and unit == "km/hr":
            val = val * 1000.0 / 3600.0  # m/s
        if name == "walking_steadiness" and val <= 1.0:
            val = val * 100.0  # to percent for human reading
        if agg == "sum":
            sums[name][d] += val
        else:
            means_data[name][d].append(val)
        elem.clear()

    out: dict[str, dict[date, float]] = {}
    for name, daily in sums.items():
        out[name] = dict(daily)
    for name, daily in means_data.items():
        out[name] = {d: mean(v) for d, v in daily.items() if v}
    return out, dict(workouts_by_day)


# ----------------------------- Timeline -----------------------------

def load_timeline_city_map() -> dict[date, str]:
    if not TIMELINE_JSON.exists():
        return {}
    try:
        with TIMELINE_JSON.open() as f:
            records = json.load(f)
    except Exception:
        return {}
    day_city_secs: dict[date, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for rec in records:
        start = parse_iso(rec.get("startTime", ""))
        end = parse_iso(rec.get("endTime", ""))
        if not start or not end:
            continue
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
            for g in (geo_s, geo_e):
                if g:
                    c = classify_city(*g)
                    if c:
                        city = c
                        break
        if city:
            day_city_secs[d][city] += secs
    return {d: max(c.items(), key=lambda kv: kv[1])[0] for d, c in day_city_secs.items()}


# ----------------------------- Stats helpers -----------------------------

def monthly_aggregate(daily: dict[date, float], how: str = "mean") -> dict[str, float]:
    bucket: dict[str, list[float]] = defaultdict(list)
    for d, v in daily.items():
        key = f"{d.year:04d}-{d.month:02d}"
        bucket[key].append(v)
    if how == "mean":
        return {k: mean(v) for k, v in bucket.items() if v}
    if how == "median":
        return {k: median(v) for k, v in bucket.items() if v}
    if how == "sum":
        return {k: sum(v) for k, v in bucket.items() if v}
    raise ValueError(how)


def yearly_aggregate(daily: dict[date, float], how: str = "mean") -> dict[int, float]:
    bucket: dict[int, list[float]] = defaultdict(list)
    for d, v in daily.items():
        bucket[d.year].append(v)
    if how == "mean":
        return {k: mean(v) for k, v in bucket.items() if v}
    if how == "sum":
        return {k: sum(v) for k, v in bucket.items() if v}
    raise ValueError(how)


def pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 3 or len(ys) < 3 or len(xs) != len(ys):
        return float("nan")
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return float("nan")
    return num / (dx * dy)


def bootstrap_diff_ci(
    a: list[float], b: list[float], iters: int = 5000, seed: int = 0,
) -> tuple[float, float, float]:
    """Return (point_diff_mean(a)-mean(b), lo95, hi95)."""
    if len(a) < 5 or len(b) < 5:
        return float("nan"), float("nan"), float("nan")
    rng = random.Random(seed)
    point = mean(a) - mean(b)
    diffs: list[float] = []
    na, nb = len(a), len(b)
    for _ in range(iters):
        sa = [a[rng.randrange(na)] for _ in range(na)]
        sb = [b[rng.randrange(nb)] for _ in range(nb)]
        diffs.append(mean(sa) - mean(sb))
    diffs.sort()
    lo = diffs[int(0.025 * iters)]
    hi = diffs[int(0.975 * iters)]
    return point, lo, hi


# ----------------------------- Recovery detection -----------------------------

def detect_bottom_and_cross(
    monthly: dict[str, float], direction: int, baseline_months: list[str],
) -> dict[str, object]:
    """direction +1 if higher-is-better, -1 if lower-is-better.

    Baseline = mean over baseline_months (e.g. 2020 + 2021 pre-enlistment).
    Bottom = worst monthly value (min if +1, max if -1).
    Cross  = first month AFTER the bottom whose value is on the 'good side' of baseline.
    """
    if not monthly:
        return {"baseline": None, "bottom_month": None, "bottom_value": None,
                "cross_month": None, "cross_value": None, "recovered": False}
    base_vals = [monthly[m] for m in baseline_months if m in monthly]
    baseline = mean(base_vals) if base_vals else None
    keys = sorted(monthly.keys())
    if direction == +1:
        bottom_month = min(keys, key=lambda k: monthly[k])
    else:
        bottom_month = max(keys, key=lambda k: monthly[k])
    bottom_value = monthly[bottom_month]

    cross_month = None
    cross_value = None
    if baseline is not None:
        post = [k for k in keys if k > bottom_month]
        for k in post:
            v = monthly[k]
            if direction == +1 and v >= baseline:
                cross_month, cross_value = k, v
                break
            if direction == -1 and v <= baseline:
                cross_month, cross_value = k, v
                break
    return {
        "baseline": baseline,
        "bottom_month": bottom_month,
        "bottom_value": bottom_value,
        "cross_month": cross_month,
        "cross_value": cross_value,
        "recovered": cross_month is not None,
    }


def monotone_recovery_score(monthly: dict[str, float], direction: int, since: str) -> float:
    """Fraction of consecutive monthly steps after `since` that improve (toward better).

    1.0 means strictly monotone recovery, 0.0 = never improving.
    """
    keys = sorted(k for k in monthly if k > since)
    if len(keys) < 2:
        return float("nan")
    improves = 0
    total = 0
    for prev, nxt in zip(keys[:-1], keys[1:]):
        total += 1
        delta = monthly[nxt] - monthly[prev]
        if direction == +1 and delta > 0:
            improves += 1
        if direction == -1 and delta < 0:
            improves += 1
    return improves / total if total else float("nan")


# ----------------------------- Main -----------------------------

def main() -> None:
    print("[load] parsing Apple Health XML…")
    metrics, workouts_by_day = load_health_daily()
    for name in ["walking_speed", "step_length", "asymmetry",
                 "double_support", "walking_steadiness", "step_count"]:
        if name in metrics:
            print(f"  {name:20s} daily-records={len(metrics[name])}")

    # ---------- Per-year baseline summary (sanity) ----------
    print("\n=== YEARLY MEANS (sanity check vs v1 scout) ===")
    for name in ["walking_speed", "step_length", "asymmetry",
                 "double_support", "walking_steadiness", "step_count"]:
        if name not in metrics:
            continue
        how = "sum" if name == "step_count" else "mean"
        if how == "sum":
            # per-day step counts already summed; take mean across days per year
            ydict = {y: mean(list(g)) for y, g in _group_by_year(metrics[name]).items()}
        else:
            ydict = yearly_aggregate(metrics[name], how="mean")
        ys = sorted(ydict.keys())
        vs = " ".join(f"{y}={ydict[y]:.3f}" for y in ys)
        print(f"  {name:20s} {vs}")

    # ---------- Monthly time series ----------
    monthly_data: dict[str, dict[str, float]] = {}
    for name in ["walking_speed", "step_length", "asymmetry",
                 "double_support", "walking_steadiness", "step_count"]:
        if name not in metrics:
            continue
        how = "mean" if name != "step_count" else "mean"  # per-day mean of daily totals
        monthly_data[name] = monthly_aggregate(metrics[name], how=how)

    # ---------- Recovery trajectory ----------
    baseline_months = [f"2020-{m:02d}" for m in range(9, 13)] + \
                      [f"2021-{m:02d}" for m in range(1, 13)]
    print("\n=== RECOVERY TRAJECTORY (bottom & baseline-cross) ===")
    print(f"baseline window = 2020-09 through 2021-10 (pre-enlistment; MIL_START=2021-11-15)")
    recovery: dict[str, dict[str, object]] = {}
    for name, mdict in monthly_data.items():
        direction = DIRECTION[name]
        result = detect_bottom_and_cross(mdict, direction, baseline_months)
        recovery[name] = result
        base = result["baseline"]; bm = result["bottom_month"]; bv = result["bottom_value"]
        cm = result["cross_month"]; cv = result["cross_value"]
        base_s = f"{base:.3f}" if isinstance(base, float) else "n/a"
        cm_s = cm if cm else "NOT YET"
        cv_s = f"{cv:.3f}" if isinstance(cv, float) else "n/a"
        print(f"  {name:20s} base={base_s:>9s}  bottom={bm}@{bv:.3f}  "
              f"cross→{cm_s}@{cv_s}  recovered={result['recovered']}")

    # ---------- Post-bottom monotonicity ----------
    print("\n=== POST-BOTTOM MONOTONICITY SCORE (fraction of months that improved) ===")
    for name, r in recovery.items():
        if r["bottom_month"]:
            score = monotone_recovery_score(monthly_data[name], DIRECTION[name],
                                            str(r["bottom_month"]))
            print(f"  {name:20s} bottom={r['bottom_month']}  monotone={score:.3f}")

    # ---------- Correlation matrix across gait metrics over time ----------
    print("\n=== MONTHLY GAIT-METRIC CORRELATION (Pearson) ===")
    names = ["walking_speed", "step_length", "asymmetry",
             "double_support", "walking_steadiness", "step_count"]
    names = [n for n in names if n in monthly_data]
    common_months = sorted(set.intersection(*[set(monthly_data[n].keys()) for n in names]))
    print(f"  n_months_common = {len(common_months)}")
    header = "                     " + " ".join(f"{n[:8]:>10s}" for n in names)
    print(header)
    corr: dict[str, dict[str, float]] = {n: {} for n in names}
    for ni in names:
        xs = [monthly_data[ni][m] for m in common_months]
        row = []
        for nj in names:
            ys = [monthly_data[nj][m] for m in common_months]
            r = pearson(xs, ys)
            corr[ni][nj] = r
            row.append(f"{r:>10.3f}")
        print(f"  {ni:20s}" + " ".join(row))

    # ---------- City contrast: Paris vs Seoul ----------
    print("\n=== CITY CONTRAST: Paris vs Seoul (per-day gait, bootstrap 95% CI) ===")
    day_to_city = load_timeline_city_map()
    if day_to_city:
        print(f"  timeline-classified days: {len(day_to_city)} "
              f"(Paris={sum(1 for v in day_to_city.values() if v=='Paris')}, "
              f"Seoul={sum(1 for v in day_to_city.values() if v=='Seoul')})")
        for name in names:
            if name not in metrics:
                continue
            daily = metrics[name]
            paris = [daily[d] for d, c in day_to_city.items() if c == "Paris" and d in daily]
            seoul = [daily[d] for d, c in day_to_city.items() if c == "Seoul" and d in daily]
            if len(paris) < 5 or len(seoul) < 5:
                print(f"  {name:20s} insufficient: Paris n={len(paris)}, Seoul n={len(seoul)}")
                continue
            d, lo, hi = bootstrap_diff_ci(paris, seoul, iters=4000, seed=42)
            paris_m = mean(paris); seoul_m = mean(seoul)
            print(f"  {name:20s} Paris(n={len(paris)})={paris_m:.3f}  "
                  f"Seoul(n={len(seoul)})={seoul_m:.3f}  "
                  f"Δ(Paris-Seoul)={d:.3f} [95% CI {lo:.3f}, {hi:.3f}]")
    else:
        print("  (no timeline)")

    # ---------- Running-day vs sedentary-day ----------
    print("\n=== WORKOUT × GAIT: running/walking-workout days vs sedentary days ===")
    running_days = {d for d, ws in workouts_by_day.items() if ws & RUNNING_WORKOUT_TYPES}
    # Define sedentary day: <3000 steps that day
    step_daily = metrics.get("step_count", {})
    sedentary_days = {d for d, s in step_daily.items() if s < 3000}
    print(f"  running/walking-workout days: {len(running_days)}, "
          f"sedentary (<3000 steps) days: {len(sedentary_days)}")
    for name in ["walking_speed", "step_length", "asymmetry",
                 "double_support", "walking_steadiness"]:
        if name not in metrics:
            continue
        daily = metrics[name]
        a = [daily[d] for d in running_days if d in daily]
        b = [daily[d] for d in sedentary_days if d in daily]
        if len(a) < 5 or len(b) < 5:
            print(f"  {name:20s} insufficient: run={len(a)}, sed={len(b)}")
            continue
        d, lo, hi = bootstrap_diff_ci(a, b, iters=4000, seed=7)
        print(f"  {name:20s} run(n={len(a)})={mean(a):.3f}  "
              f"sed(n={len(b)})={mean(b):.3f}  "
              f"Δ(run-sed)={d:.3f} [95% CI {lo:.3f}, {hi:.3f}]")

    # ---------- Persist artifacts ----------
    out_dir = Path("/Users/sangho/Desktop/빅데이터컴퓨팅/wine-mab-project/results/logs")
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "yearly": {
            n: yearly_aggregate(metrics[n], how="mean")
            for n in names if n in metrics
        },
        "monthly": {
            n: dict(sorted(monthly_data[n].items())) for n in names if n in monthly_data
        },
        "recovery": {n: r for n, r in recovery.items()},
        "correlation": corr,
    }
    # JSON-safe (years are ints, but dict-keys ints OK in json)
    out_path = out_dir / "gait_recovery.json"
    with out_path.open("w") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"\n[ok] artifacts → {out_path}")


def _group_by_year(daily: dict[date, float]) -> dict[int, list[float]]:
    g: dict[int, list[float]] = defaultdict(list)
    for d, v in daily.items():
        g[d.year].append(v)
    return g


if __name__ == "__main__":
    main()
