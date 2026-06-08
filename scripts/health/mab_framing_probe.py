"""Honest MAB framing probe — evaluate three candidate MAB formulations against the data.

Framings tested:
  (a) Workout intervention bandit:   arms={run, basketball, cycle, rest}
  (b) Hour-of-day exploration bandit: arms={morning, afternoon, evening}
  (c) Place-category bandit:          arms={home, school, cafe, transit, novel}

For each: arm-exploration entropy, reward identifiability, and counterfactual feasibility.
"""
from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import mean, stdev

HEALTH_XML = Path("/Users/sangho/Downloads/apple_health_export/내보내기.xml")
TIMELINE_JSON = Path("/Users/sangho/Downloads/location-history.json")

WINDOW_START = date(2024, 12, 1)
WINDOW_END = date(2025, 12, 31)

SEOUL_BOX = (37.3, 37.7, 126.7, 127.3)
PARIS_BOX = (48.7, 49.0, 2.1, 2.5)


# ---------------------------- helpers ----------------------------
def parse_geo(s: str):
    if not s or not s.startswith("geo:"):
        return None
    try:
        a, b = s[4:].split(",")
        return float(a), float(b)
    except ValueError:
        return None


def in_box(lat, lon, b):
    return b[0] <= lat <= b[1] and b[2] <= lon <= b[3]


def classify_city(lat, lon):
    if in_box(lat, lon, SEOUL_BOX):
        return "Seoul"
    if in_box(lat, lon, PARIS_BOX):
        return "Paris"
    return None


def parse_apple_date(s):
    try:
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def parse_iso(s):
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


# ---------------------------- (1) workout arms ----------------------------
def workout_inventory():
    counts_all = Counter()
    counts_win = Counter()
    type_by_day = defaultdict(set)
    for _, elem in ET.iterparse(HEALTH_XML, events=("end",)):
        if elem.tag != "Workout":
            elem.clear()
            continue
        atype = elem.get("workoutActivityType", "").replace("HKWorkoutActivityType", "")
        sd = parse_apple_date(elem.get("startDate", ""))
        counts_all[atype] += 1
        if sd and WINDOW_START <= sd.date() <= WINDOW_END:
            counts_win[atype] += 1
            type_by_day[sd.date()].add(atype)
        elem.clear()
    return counts_all, counts_win, type_by_day


# ---------------------------- (2) hour-bin arms ----------------------------
def hourly_steps_in_window():
    """Aggregate StepCount records into (date, hour_bin) -> steps. Bins: 0=morn(5-12), 1=aft(12-18), 2=eve(18-24), 3=night(0-5)."""
    bins = defaultdict(float)
    for _, elem in ET.iterparse(HEALTH_XML, events=("end",)):
        if elem.tag != "Record":
            elem.clear()
            continue
        if elem.get("type") != "HKQuantityTypeIdentifierStepCount":
            elem.clear()
            continue
        sd = parse_apple_date(elem.get("startDate", ""))
        if not sd:
            elem.clear()
            continue
        d = sd.date()
        if d < WINDOW_START or d > WINDOW_END:
            elem.clear()
            continue
        try:
            v = float(elem.get("value", "nan"))
        except ValueError:
            elem.clear()
            continue
        h = sd.hour
        if 5 <= h < 12:
            b = "morning"
        elif 12 <= h < 18:
            b = "afternoon"
        elif 18 <= h < 24:
            b = "evening"
        else:
            b = "night"
        bins[(d, b)] += v
        elem.clear()
    return bins


# ---------------------------- (3) place arms ----------------------------
def place_inventory():
    """Mine semanticType / placeId distribution from visit records inside the window."""
    semantic_counts = Counter()
    place_counts = Counter()
    place_city_count = defaultdict(Counter)
    visit_days = set()
    with TIMELINE_JSON.open() as f:
        records = json.load(f)
    for rec in records:
        if "visit" not in rec:
            continue
        sd = parse_iso(rec.get("startTime", ""))
        if not sd:
            continue
        d = sd.astimezone(timezone.utc).date()
        if d < WINDOW_START or d > WINDOW_END:
            continue
        top = rec["visit"].get("topCandidate", {})
        st = top.get("semanticType", "UNKNOWN")
        pid = top.get("placeId", "UNKNOWN")
        geo = parse_geo(top.get("placeLocation", ""))
        city = classify_city(*geo) if geo else "Other"
        semantic_counts[st] += 1
        place_counts[pid] += 1
        place_city_count[city][st] += 1
        visit_days.add(d)
    return semantic_counts, place_counts, place_city_count, visit_days


# ---------------------------- (4) daily steps ----------------------------
def daily_steps_in_window():
    daily = defaultdict(float)
    for _, elem in ET.iterparse(HEALTH_XML, events=("end",)):
        if elem.tag != "Record":
            elem.clear()
            continue
        if elem.get("type") != "HKQuantityTypeIdentifierStepCount":
            elem.clear()
            continue
        sd = parse_apple_date(elem.get("startDate", ""))
        if not sd:
            elem.clear()
            continue
        d = sd.date()
        if d < WINDOW_START or d > WINDOW_END:
            elem.clear()
            continue
        try:
            v = float(elem.get("value", "nan"))
        except ValueError:
            elem.clear()
            continue
        daily[d] += v
        elem.clear()
    return daily


def entropy(counts):
    tot = sum(counts.values())
    if tot == 0:
        return 0.0
    return -sum((c / tot) * math.log2(c / tot) for c in counts.values() if c > 0)


def main():
    print("=" * 60)
    print("FRAMING (a) — Workout intervention bandit")
    print("=" * 60)
    all_w, win_w, by_day = workout_inventory()
    print("[all-time workouts]")
    for k, v in all_w.most_common():
        print(f"  {k:25s} {v}")
    print(f"\n[in-window workouts: {WINDOW_START}..{WINDOW_END}]")
    for k, v in win_w.most_common():
        print(f"  {k:25s} {v}")
    print(f"\nworkout-days in window: {len(by_day)}")
    arm_counts_a = Counter()
    for d, types in by_day.items():
        for t in types:
            arm_counts_a[t] += 1
    print(f"arm distribution (days): {arm_counts_a}")
    H_a = entropy(arm_counts_a)
    print(f"arm-day Shannon entropy: H={H_a:.3f} bits  (max={math.log2(max(1,len(arm_counts_a))):.3f})")

    print()
    print("=" * 60)
    print("FRAMING (b) — Hour-of-day bandit")
    print("=" * 60)
    bins = hourly_steps_in_window()
    by_city_bin = defaultdict(lambda: defaultdict(list))
    # need day->city map
    day_to_city = {}
    with TIMELINE_JSON.open() as f:
        for rec in json.load(f):
            sd = parse_iso(rec.get("startTime", ""))
            if not sd:
                continue
            d = sd.astimezone(timezone.utc).date()
            if d < WINDOW_START or d > WINDOW_END:
                continue
            geo = None
            if "visit" in rec:
                geo = parse_geo(rec["visit"].get("topCandidate", {}).get("placeLocation", ""))
            elif "activity" in rec:
                geo = parse_geo(rec["activity"].get("start", ""))
            if geo:
                c = classify_city(*geo)
                if c:
                    day_to_city.setdefault(d, []).append(c)
    day_to_city = {d: Counter(cs).most_common(1)[0][0] for d, cs in day_to_city.items()}
    for (d, b), v in bins.items():
        city = day_to_city.get(d)
        if city:
            by_city_bin[city][b].append(v)

    for city in ("Seoul", "Paris"):
        print(f"\n[{city}] hour-bin step-share & mean steps/bin")
        totals = {b: sum(by_city_bin[city][b]) for b in ("morning", "afternoon", "evening", "night")}
        grand = sum(totals.values()) or 1
        for b in ("morning", "afternoon", "evening", "night"):
            vals = by_city_bin[city][b]
            sh = totals[b] / grand
            m = mean(vals) if vals else 0
            sd_ = stdev(vals) if len(vals) > 1 else 0
            print(f"  {b:10s} share={sh:.3f}  n_days={len(vals):>3}  mean_steps={m:.1f}  sd={sd_:.1f}")
        share_arms = Counter({b: totals[b] for b in totals if totals[b] > 0})
        H_b = entropy(share_arms)
        print(f"  hour-bin Shannon entropy: H={H_b:.3f} bits (max={math.log2(len(share_arms)):.3f})")

    print()
    print("=" * 60)
    print("FRAMING (c) — Place-category bandit")
    print("=" * 60)
    sem, plc, by_city, vd = place_inventory()
    print("[semanticType in window]")
    for k, v in sem.most_common():
        print(f"  {k:35s} {v}")
    print(f"\ntotal visit-days: {len(vd)}")
    print(f"unique placeId: {len(plc)}")
    top_places = plc.most_common(10)
    tot_visits = sum(plc.values())
    print(f"top10 placeId share of all visits: {sum(c for _, c in top_places)/tot_visits:.3f}")
    H_c_sem = entropy(sem)
    print(f"semanticType entropy: H={H_c_sem:.3f} bits (max={math.log2(max(1,len(sem))):.3f})")
    H_c_pid = entropy(plc)
    print(f"placeId entropy:      H={H_c_pid:.3f} bits (max={math.log2(max(1,len(plc))):.3f})")
    print("[city x semanticType]")
    for c in by_city:
        print(f"  {c}: {dict(by_city[c])}")

    print()
    print("=" * 60)
    print("DAILY STEPS — basic reward sanity")
    print("=" * 60)
    ds = daily_steps_in_window()
    vals = list(ds.values())
    print(f"n_days={len(vals)}  mean={mean(vals):.1f}  sd={stdev(vals):.1f}")
    # daily auto-correlation lag-1
    sorted_d = sorted(ds.keys())
    pairs = [(ds[sorted_d[i]], ds[sorted_d[i + 1]]) for i in range(len(sorted_d) - 1)
             if (sorted_d[i + 1] - sorted_d[i]).days == 1]
    if pairs:
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        mx = mean(xs); my = mean(ys)
        num = sum((x - mx) * (y - my) for x, y in pairs)
        den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
        r1 = num / den if den else 0.0
        print(f"step-count lag-1 autocorr: r={r1:.3f}  (high autocorr ⇒ reward not iid)")


if __name__ == "__main__":
    main()
