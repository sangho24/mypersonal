"""For framing (a), the workout-intervention bandit:
- only 17 workout-days in 13 months → no statistical power for arm comparison
- arms are nearly degenerate: 16 Running, 1 Cycling, 0 Basketball, 0 Rest-as-arm
- so test whether even Running ↔ Rest contrast on next-day steps is identifiable.

Also probe a *passive-activity* recasting:
  arm = dominant transport mode of the day (walking / subway / bus / car)
  reward = daily steps
  context = (city, weekday, season)
This is the most defensible MAB-like framing IF arms are identifiable from location data.
"""
from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, stdev

HEALTH_XML = Path("/Users/sangho/Downloads/apple_health_export/내보내기.xml")
TIMELINE_JSON = Path("/Users/sangho/Downloads/location-history.json")

WINDOW_START = date(2024, 12, 1)
WINDOW_END = date(2025, 12, 31)

SEOUL_BOX = (37.3, 37.7, 126.7, 127.3)
PARIS_BOX = (48.7, 49.0, 2.1, 2.5)


def parse_geo(s):
    if not s or not s.startswith("geo:"):
        return None
    try:
        a, b = s[4:].split(",")
        return float(a), float(b)
    except ValueError:
        return None


def classify_city(lat, lon):
    if SEOUL_BOX[0] <= lat <= SEOUL_BOX[1] and SEOUL_BOX[2] <= lon <= SEOUL_BOX[3]:
        return "Seoul"
    if PARIS_BOX[0] <= lat <= PARIS_BOX[1] and PARIS_BOX[2] <= lon <= PARIS_BOX[3]:
        return "Paris"
    return None


def parse_iso(s):
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def parse_apple(s):
    try:
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S").date()
    except Exception:
        return None


def daily_steps():
    out = defaultdict(float)
    for _, el in ET.iterparse(HEALTH_XML, events=("end",)):
        if el.tag != "Record":
            el.clear(); continue
        if el.get("type") != "HKQuantityTypeIdentifierStepCount":
            el.clear(); continue
        d = parse_apple(el.get("startDate", ""))
        if not d or d < WINDOW_START or d > WINDOW_END:
            el.clear(); continue
        try:
            out[d] += float(el.get("value", "nan"))
        except ValueError:
            pass
        el.clear()
    return out


def workout_days():
    out = defaultdict(list)
    for _, el in ET.iterparse(HEALTH_XML, events=("end",)):
        if el.tag != "Workout":
            el.clear(); continue
        d = parse_apple(el.get("startDate", ""))
        if not d or d < WINDOW_START or d > WINDOW_END:
            el.clear(); continue
        a = el.get("workoutActivityType", "").replace("HKWorkoutActivityType", "")
        out[d].append(a)
        el.clear()
    return out


def day_transport_mode():
    """For each in-window day, mine activity segments and assign dominant transport label."""
    with TIMELINE_JSON.open() as f:
        recs = json.load(f)
    day_mode_secs = defaultdict(lambda: defaultdict(float))
    day_city_secs = defaultdict(lambda: defaultdict(float))
    for r in recs:
        sd = parse_iso(r.get("startTime", ""))
        ed = parse_iso(r.get("endTime", ""))
        if not sd or not ed:
            continue
        d = sd.astimezone(timezone.utc).date()
        if d < WINDOW_START or d > WINDOW_END:
            continue
        secs = max(0.0, (ed - sd).total_seconds())
        if "activity" in r:
            act = r["activity"]
            mode = act.get("topCandidate", {}).get("type", "unknown")
            day_mode_secs[d][mode] += secs
            g = parse_geo(act.get("start", ""))
            if g:
                c = classify_city(*g)
                if c:
                    day_city_secs[d][c] += secs
        elif "visit" in r:
            g = parse_geo(r["visit"].get("topCandidate", {}).get("placeLocation", ""))
            if g:
                c = classify_city(*g)
                if c:
                    day_city_secs[d][c] += secs
    day_mode = {}
    for d, m in day_mode_secs.items():
        if m:
            day_mode[d] = max(m.items(), key=lambda kv: kv[1])[0]
    day_city = {d: max(c.items(), key=lambda kv: kv[1])[0] for d, c in day_city_secs.items() if c}
    return day_mode, day_city


def main():
    ds = daily_steps()
    wd = workout_days()
    dmode, dcity = day_transport_mode()

    print("=" * 60)
    print("FRAMING (a) — workout arms next-day reward identifiability")
    print("=" * 60)
    # next-day steps after Running vs after Rest-day
    run_days = [d for d, lst in wd.items() if "Running" in lst]
    rest_days = [d for d in ds.keys() if d not in wd]
    next_run = [ds.get(d + timedelta(days=1)) for d in run_days]
    next_run = [v for v in next_run if v is not None]
    next_rest = [ds.get(d + timedelta(days=1)) for d in rest_days]
    next_rest = [v for v in next_rest if v is not None]
    print(f"Running days: n={len(run_days)}; next-day steps: mean={mean(next_run):.1f} sd={stdev(next_run):.1f}" if next_run else "no run-next data")
    print(f"Rest    days: n={len(rest_days)}; next-day steps: mean={mean(next_rest):.1f} sd={stdev(next_rest):.1f}" if next_rest else "no rest-next data")
    # crude effect size
    if len(next_run) > 2 and len(next_rest) > 2:
        pooled = math.sqrt(((stdev(next_run))**2 + (stdev(next_rest))**2) / 2)
        d_eff = (mean(next_run) - mean(next_rest)) / pooled if pooled > 0 else float("nan")
        print(f"Cohen's d (next-day steps, Run vs Rest) = {d_eff:.3f}")
        # MDE at 80% power, alpha 0.05, two-sided: n needed ~ 2 * ((z_a/2 + z_b)/d)^2 per group
        za = 1.96; zb = 0.84
        n_needed = 2 * ((za + zb) / max(abs(d_eff), 0.1))**2
        print(f"per-arm n needed for 80% power at this effect: ~{n_needed:.0f}; have n={len(run_days)} run-days")

    print()
    print("=" * 60)
    print("PASSIVE FRAMING — transport-mode arms, daily steps reward")
    print("=" * 60)
    print(f"days with mode labeled: {len(dmode)}")
    by_mode = defaultdict(list)
    for d, m in dmode.items():
        if d in ds:
            by_mode[m].append(ds[d])
    for m, vals in sorted(by_mode.items(), key=lambda kv: -len(kv[1])):
        if len(vals) >= 3:
            print(f"  {m:25s} n={len(vals):>3}  mean={mean(vals):>7.1f}  sd={stdev(vals):>7.1f}")
        else:
            print(f"  {m:25s} n={len(vals):>3}  (too small)")

    print()
    print("[Cross-city x mode] daily steps")
    by_city_mode = defaultdict(lambda: defaultdict(list))
    for d, m in dmode.items():
        if d in ds and d in dcity:
            by_city_mode[dcity[d]][m].append(ds[d])
    for c in ("Seoul", "Paris"):
        print(f"--- {c} ---")
        for m, vals in sorted(by_city_mode[c].items(), key=lambda kv: -len(kv[1])):
            if len(vals) >= 5:
                print(f"  {m:25s} n={len(vals):>3}  mean={mean(vals):>7.1f}  sd={stdev(vals):>7.1f}")

    # arm-exploration entropy (across all in-window days)
    cnt = Counter(dmode.values())
    tot = sum(cnt.values())
    H = -sum((c/tot)*math.log2(c/tot) for c in cnt.values() if c>0)
    print(f"\nTransport-mode arm entropy: H={H:.3f} bits  (max={math.log2(len(cnt)):.3f})")
    print(f"Arm distribution: {cnt.most_common()}")


if __name__ == "__main__":
    main()
