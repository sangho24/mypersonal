"""
v2 cross-modal analysis with confound control.
- 2-way / 3-way ANOVA: mode x country x time-of-day
- Per-country mode-effect ordering
- Walking speed x city x season (Feb-Jun Paris-2025 vs Seoul-2026), bootstrap CI
- Workout (Nike runs) x Timeline place_label join, Paris vs Seoul counts
- distinct_places_per_day by country with bootstrap CI

Outputs: results/health_v2/v2_summary.json
"""

import json
import os
import re
import math
import random
from collections import defaultdict, Counter
from datetime import datetime, timezone, timedelta
from xml.etree.ElementTree import iterparse

import numpy as np

XML_PATH = "/Users/sangho/Downloads/apple_health_export/내보내기.xml"
LOC_PATH = "/Users/sangho/Downloads/location-history.json"
OUT_DIR = "/Users/sangho/Desktop/빅데이터컴퓨팅/wine-mab-project/results/health_v2"
os.makedirs(OUT_DIR, exist_ok=True)

random.seed(0)
np.random.seed(0)

# ---------------------------------------------------------------- helpers

DT_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) ([+-]\d{4})$")

def parse_apple_dt(s):
    """Apple Health export uses 'YYYY-MM-DD HH:MM:SS +ZZZZ'."""
    m = DT_RE.match(s)
    if not m:
        return None
    naive = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
    tz = m.group(2)
    off = int(tz[:3]) * 3600 + int(tz[0] + tz[3:5]) * 60
    return naive.replace(tzinfo=timezone(timedelta(seconds=off)))

def parse_iso(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None

def geo_parse(g):
    if not g or not g.startswith("geo:"):
        return None
    try:
        a, b = g[4:].split(",")
        return float(a), float(b)
    except Exception:
        return None

def country_for_latlon(lat, lon):
    """Coarse bbox: Korea, France, Other."""
    if 33.0 <= lat <= 39.5 and 124.0 <= lon <= 131.5:
        return "Korea"
    if 41.0 <= lat <= 51.5 and -5.5 <= lon <= 9.6:
        return "France"
    return "Other"

def country_for_tz_offset_seconds(off):
    """Fallback when no coordinate. KST=+0900, CET/CEST=+0100/+0200."""
    h = off // 3600
    if h == 9:
        return "Korea"
    if h in (1, 2):
        return "France"
    return "Other"

# ---------------------------------------------------------------- load location history

print("[loc] loading...", flush=True)
with open(LOC_PATH) as f:
    loc = json.load(f)
print(f"[loc] {len(loc)} segments", flush=True)

# Build activity segments with mode + country + start/end time
activity_segs = []   # list of dicts: start, end, mode, country, dist_m, dur_s
visit_segs = []      # list of dicts: start, end, country, place_id, lat, lon

MODE_MAP = {
    "in subway": "subway",
    "in passenger vehicle": "car",
    "in vehicle": "car",
    "in bus": "bus",
    "walking": "walking",
    "running": "running",
    "cycling": "cycling",
    "in train": "train",
}

for seg in loc:
    st = parse_iso(seg.get("startTime", ""))
    et = parse_iso(seg.get("endTime", ""))
    if not st or not et:
        continue
    if "activity" in seg:
        a = seg["activity"]
        top = a.get("topCandidate", {})
        mode_raw = top.get("type", "")
        mode = MODE_MAP.get(mode_raw, None)
        end_geo = geo_parse(a.get("end", ""))
        start_geo = geo_parse(a.get("start", ""))
        country = None
        if start_geo:
            country = country_for_latlon(*start_geo)
        elif end_geo:
            country = country_for_latlon(*end_geo)
        else:
            country = country_for_tz_offset_seconds(int(st.utcoffset().total_seconds()))
        try:
            dist = float(a.get("distanceMeters", "0"))
        except Exception:
            dist = 0.0
        dur = (et - st).total_seconds()
        activity_segs.append(dict(
            start=st, end=et, mode=mode, mode_raw=mode_raw, country=country,
            dist_m=dist, dur_s=dur,
            lat=start_geo[0] if start_geo else (end_geo[0] if end_geo else None),
            lon=start_geo[1] if start_geo else (end_geo[1] if end_geo else None),
        ))
    elif "visit" in seg:
        v = seg["visit"]
        top = v.get("topCandidate", {})
        pgeo = geo_parse(top.get("placeLocation", ""))
        country = country_for_latlon(*pgeo) if pgeo else country_for_tz_offset_seconds(
            int(st.utcoffset().total_seconds())
        )
        visit_segs.append(dict(
            start=st, end=et, country=country,
            place_id=top.get("placeID", ""),
            lat=pgeo[0] if pgeo else None,
            lon=pgeo[1] if pgeo else None,
            semantic=top.get("semanticType", ""),
        ))

print(f"[loc] activity={len(activity_segs)} visit={len(visit_segs)}", flush=True)
mode_counts = Counter(s["mode"] for s in activity_segs)
print(f"[loc] mode dist (mapped): {mode_counts}", flush=True)
country_counts = Counter(s["country"] for s in activity_segs)
print(f"[loc] country dist: {country_counts}", flush=True)

# Sort for fast lookup
activity_segs.sort(key=lambda s: s["start"])
seg_starts = [s["start"] for s in activity_segs]

# ---------------------------------------------------------------- parse Apple Health XML

print("[xml] streaming parse...", flush=True)
audio_records = []          # (start, end, value_dBASPL)
walking_speed = []          # (start, end, value_kmh)
workouts = []               # (start, end, kind, dur_min, dist_km, energy_kcal)
distinct_places_visits = []  # for distinct_places_per_day

# We also collect daily series of distinct places by country (from visit_segs we already have)
ctx = iterparse(XML_PATH, events=("end",))
n = 0
for ev, elem in ctx:
    tag = elem.tag
    if tag == "Record":
        rtype = elem.get("type", "")
        if rtype == "HKQuantityTypeIdentifierHeadphoneAudioExposure":
            st = parse_apple_dt(elem.get("startDate", ""))
            et = parse_apple_dt(elem.get("endDate", ""))
            try:
                v = float(elem.get("value", "0"))
            except Exception:
                v = None
            if st and et and v is not None:
                audio_records.append((st, et, v))
        elif rtype == "HKQuantityTypeIdentifierWalkingSpeed":
            st = parse_apple_dt(elem.get("startDate", ""))
            et = parse_apple_dt(elem.get("endDate", ""))
            unit = elem.get("unit", "")
            try:
                v = float(elem.get("value", "0"))
            except Exception:
                v = None
            if st and et and v is not None:
                # normalize to km/h
                if unit.startswith("km/hr"):
                    pass
                elif unit.startswith("mi/hr"):
                    v *= 1.609344
                elif unit == "m/s":
                    v *= 3.6
                walking_speed.append((st, et, v))
        elem.clear()
    elif tag == "Workout":
        wtype = elem.get("workoutActivityType", "")
        st = parse_apple_dt(elem.get("startDate", ""))
        et = parse_apple_dt(elem.get("endDate", ""))
        try:
            dur = float(elem.get("duration", "0"))
        except Exception:
            dur = 0.0
        # totalDistance + totalEnergyBurned legacy; modern uses Statistics children
        try:
            dist = float(elem.get("totalDistance", "0"))
        except Exception:
            dist = 0.0
        try:
            kcal = float(elem.get("totalEnergyBurned", "0"))
        except Exception:
            kcal = 0.0
        # also walk statistics children for distance/energy if attrs are empty
        if dist == 0.0 or kcal == 0.0:
            for child in elem:
                if child.tag == "WorkoutStatistics":
                    t = child.get("type", "")
                    try:
                        s = float(child.get("sum", "0"))
                    except Exception:
                        s = 0.0
                    if t == "HKQuantityTypeIdentifierDistanceWalkingRunning" and dist == 0.0:
                        dist = s
                    if t == "HKQuantityTypeIdentifierActiveEnergyBurned" and kcal == 0.0:
                        kcal = s
        if st and et:
            workouts.append(dict(start=st, end=et, kind=wtype, dur_min=dur,
                                dist_km=dist, kcal=kcal, source=elem.get("sourceName", "")))
        elem.clear()
    n += 1
    if n % 500000 == 0:
        print(f"[xml] {n} elements, audio={len(audio_records)} walk={len(walking_speed)} workouts={len(workouts)}", flush=True)

print(f"[xml] DONE. audio={len(audio_records)} walk_speed={len(walking_speed)} workouts={len(workouts)}", flush=True)

# ---------------------------------------------------------------- temporal join: audio x mode x country

# For each audio record, find any activity_seg that overlaps the (start,end) midpoint.
# Use binary search via seg_starts.

import bisect

def find_segment_for(ts):
    # find largest seg whose start <= ts; check overlap
    i = bisect.bisect_right(seg_starts, ts) - 1
    if i < 0:
        return None
    s = activity_segs[i]
    if s["start"] <= ts <= s["end"]:
        return s
    return None

joined = []   # (audio_db, mode, country, hour_of_day)
for st, et, db in audio_records:
    mid = st + (et - st) / 2
    s = find_segment_for(mid)
    if s is None or s["mode"] is None:
        continue
    # restrict to 4 focal modes
    if s["mode"] not in ("subway", "car", "bus", "walking"):
        continue
    h = mid.astimezone(timezone(timedelta(seconds=int(mid.utcoffset().total_seconds())))).hour
    joined.append((db, s["mode"], s["country"], h))

print(f"[join] audio-x-mode joined N = {len(joined)}", flush=True)
mode_country = Counter((m, c) for _, m, c, _ in joined)
print(f"[join] mode x country counts: {dict(mode_country)}", flush=True)

# ---------------------------------------------------------------- ANOVA helpers (numpy only)

def f_dist_sf(F, df1, df2):
    """Survival function for F-distribution via regularized incomplete beta.
    Returns p = P(F_{df1,df2} > F)."""
    if F <= 0 or df1 <= 0 or df2 <= 0 or not math.isfinite(F):
        return 1.0
    x = df2 / (df2 + df1 * F)
    # p = I_x(df2/2, df1/2)
    a = df2 / 2.0
    b = df1 / 2.0
    return betai(a, b, x)

def betai(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                  + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return bt * betacf(a, b, x) / a
    else:
        return 1 - bt * betacf(b, a, 1 - x) / b

def betacf(a, b, x, maxit=200, eps=3e-7):
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
            break
    return h

def anova_factorial(y, factors):
    """Type-I (sequential) factorial ANOVA on balanced/unbalanced data.
    factors: list of arrays, each is the level label per obs.
    Returns dict of factor -> (SS, df, F, p), plus residual & total.

    For 2-way / 3-way we use Type-I with main effects then interactions in
    listed order. This is the same approach as a 'sequential SS' decomposition.
    """
    y = np.asarray(y, dtype=float)
    n = len(y)
    gm = y.mean()
    ss_tot = ((y - gm) ** 2).sum()

    # group means by combination of all factors (cell means)
    keys = list(zip(*factors))
    cell_means = {}
    cell_n = Counter(keys)
    for k in cell_n:
        idx = [i for i, kk in enumerate(keys) if kk == k]
        cell_means[k] = y[idx].mean()
    # full model SS (between cells)
    ss_cells = sum(cell_n[k] * (cell_means[k] - gm) ** 2 for k in cell_n)
    ss_resid = ss_tot - ss_cells
    n_cells = len(cell_n)
    df_resid = n - n_cells

    def grand_ss(group_labels):
        """SS between groups defined by tuple labels."""
        gm_loc = y.mean()
        groups = defaultdict(list)
        for i, g in enumerate(group_labels):
            groups[g].append(y[i])
        ss = 0.0
        for g, vs in groups.items():
            vs = np.array(vs)
            ss += len(vs) * (vs.mean() - gm_loc) ** 2
        return ss, len(groups) - 1

    # marginal levels per factor
    levels = [sorted(set(f)) for f in factors]
    k = len(factors)

    results = {}

    if k == 2:
        a_labels = factors[0]
        b_labels = factors[1]
        ss_a, df_a = grand_ss(a_labels)
        ss_b, df_b = grand_ss(b_labels)
        # interaction = SS_cells - SS_a - SS_b
        ss_ab = ss_cells - ss_a - ss_b
        df_ab = (len(levels[0]) - 1) * (len(levels[1]) - 1)
        ms_resid = ss_resid / df_resid if df_resid > 0 else float("nan")
        for name, ss, df in [("A", ss_a, df_a), ("B", ss_b, df_b), ("AB", ss_ab, df_ab)]:
            ms = ss / df if df > 0 else float("nan")
            F = ms / ms_resid if ms_resid > 0 else float("nan")
            p = f_dist_sf(F, df, df_resid)
            results[name] = dict(SS=ss, df=df, F=F, p=p)
    elif k == 3:
        a_labels = factors[0]
        b_labels = factors[1]
        c_labels = factors[2]
        ss_a, df_a = grand_ss(a_labels)
        ss_b, df_b = grand_ss(b_labels)
        ss_c, df_c = grand_ss(c_labels)
        ss_ab_grp, _ = grand_ss(list(zip(a_labels, b_labels)))
        ss_ac_grp, _ = grand_ss(list(zip(a_labels, c_labels)))
        ss_bc_grp, _ = grand_ss(list(zip(b_labels, c_labels)))
        ss_ab = ss_ab_grp - ss_a - ss_b
        ss_ac = ss_ac_grp - ss_a - ss_c
        ss_bc = ss_bc_grp - ss_b - ss_c
        ss_abc = ss_cells - ss_a - ss_b - ss_c - ss_ab - ss_ac - ss_bc
        df_ab = (len(levels[0]) - 1) * (len(levels[1]) - 1)
        df_ac = (len(levels[0]) - 1) * (len(levels[2]) - 1)
        df_bc = (len(levels[1]) - 1) * (len(levels[2]) - 1)
        df_abc = (len(levels[0]) - 1) * (len(levels[1]) - 1) * (len(levels[2]) - 1)
        ms_resid = ss_resid / df_resid if df_resid > 0 else float("nan")
        for name, ss, df in [
            ("A", ss_a, df_a),
            ("B", ss_b, df_b),
            ("C", ss_c, df_c),
            ("AB", ss_ab, df_ab),
            ("AC", ss_ac, df_ac),
            ("BC", ss_bc, df_bc),
            ("ABC", ss_abc, df_abc),
        ]:
            ms = ss / df if df > 0 else float("nan")
            F = ms / ms_resid if ms_resid > 0 else float("nan")
            p = f_dist_sf(F, df, df_resid)
            results[name] = dict(SS=ss, df=df, F=F, p=p)

    results["resid"] = dict(SS=ss_resid, df=df_resid)
    results["total"] = dict(SS=ss_tot, df=n - 1)
    results["n"] = n
    return results

# ---------------------------------------------------------------- 2-way ANOVA mode x country

# We restrict to countries with sufficient N per mode
print("[anova] computing 2-way mode x country ...", flush=True)
db = np.array([j[0] for j in joined])
mode_lbl = [j[1] for j in joined]
country_lbl = [j[2] for j in joined]
hour_lbl = [j[3] for j in joined]

# filter to Korea+France (since v1 caveat was mixing countries)
keep = [i for i, c in enumerate(country_lbl) if c in ("Korea", "France")]
db_kf = db[keep]
mode_kf = [mode_lbl[i] for i in keep]
country_kf = [country_lbl[i] for i in keep]
hour_kf = [hour_lbl[i] for i in keep]

aov2 = anova_factorial(db_kf, [mode_kf, country_kf])
print(f"[anova2] {aov2}", flush=True)

# ---------------------------------------------------------------- per-country mode means + ordering

per_country_mode = {}
for c in ("Korea", "France", "Other"):
    cmodes = defaultdict(list)
    for d, m, cc, _ in joined:
        if cc != c:
            continue
        cmodes[m].append(d)
    summary = {}
    for m, vs in cmodes.items():
        vs = np.array(vs)
        if len(vs) >= 5:
            summary[m] = dict(n=len(vs), mean=float(vs.mean()), std=float(vs.std(ddof=1)),
                              median=float(np.median(vs)))
    per_country_mode[c] = summary
print(f"[per-country] {json.dumps(per_country_mode, indent=2)}", flush=True)

# pairwise Cohen's d (subway vs car) within each country
def cohen_d(a, b):
    a = np.array(a)
    b = np.array(b)
    sp = math.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1))
                   / max(len(a) + len(b) - 2, 1))
    return (a.mean() - b.mean()) / sp if sp > 0 else float("nan")

within_country = {}
for c in ("Korea", "France"):
    a = [d for d, m, cc, _ in joined if cc == c and m == "subway"]
    b = [d for d, m, cc, _ in joined if cc == c and m == "car"]
    if len(a) >= 5 and len(b) >= 5:
        within_country[c] = dict(
            n_subway=len(a), n_car=len(b),
            mean_subway=float(np.mean(a)), mean_car=float(np.mean(b)),
            cohen_d_subway_vs_car=float(cohen_d(a, b)),
        )
print(f"[within] {within_country}", flush=True)

# ---------------------------------------------------------------- 3-way: mode x country x time-of-day bin

def tod_bin(h):
    if 6 <= h < 12: return "morning"
    if 12 <= h < 18: return "afternoon"
    if 18 <= h < 24: return "evening"
    return "night"

tod_kf = [tod_bin(h) for h in hour_kf]
aov3 = anova_factorial(db_kf, [mode_kf, country_kf, tod_kf])
print(f"[anova3] {aov3}", flush=True)

# ---------------------------------------------------------------- walking speed x city x season

# Restrict to Feb–Jun, country in {Korea, France}, two years (Paris 2025 vs Seoul 2026)
def in_feb_jun(d):
    return 2 <= d.month <= 6

# A walking_speed record's country: look up the activity segment overlap; otherwise tz fallback.
ws_by_group = defaultdict(list)   # key: (city, year)
for st, et, kmh in walking_speed:
    if not in_feb_jun(st):
        continue
    mid = st + (et - st) / 2
    s = find_segment_for(mid)
    if s and s["country"] in ("Korea", "France"):
        country = s["country"]
    else:
        country = country_for_tz_offset_seconds(int(st.utcoffset().total_seconds()))
    if country == "Korea":
        city = "Seoul"
    elif country == "France":
        city = "Paris"
    else:
        continue
    ws_by_group[(city, st.year)].append(kmh)

print(f"[ws] groups: {[(k, len(v)) for k, v in ws_by_group.items()]}", flush=True)

def bootstrap_ci(arr, n_boot=2000, ci=0.95, stat=np.mean, rng=None):
    arr = np.asarray(arr, dtype=float)
    if len(arr) < 5:
        return float("nan"), float("nan"), float("nan")
    rng = rng or np.random.default_rng(0)
    idx = rng.integers(0, len(arr), size=(n_boot, len(arr)))
    samples = np.array([stat(arr[i]) for i in idx])
    lo = float(np.quantile(samples, (1 - ci) / 2))
    hi = float(np.quantile(samples, 1 - (1 - ci) / 2))
    return float(stat(arr)), lo, hi

ws_summary = {}
for k, v in ws_by_group.items():
    m, lo, hi = bootstrap_ci(v)
    ws_summary[f"{k[0]}_{k[1]}"] = dict(n=len(v), mean_kmh=m, ci95=[lo, hi],
                                         median=float(np.median(v)) if v else None)
print(f"[ws] summary {ws_summary}", flush=True)

# Diff Paris2025 vs Seoul2026 if both present
ws_diff = None
key_paris = ("Paris", 2025)
key_seoul = ("Seoul", 2026)
if key_paris in ws_by_group and key_seoul in ws_by_group:
    a = np.array(ws_by_group[key_paris])
    b = np.array(ws_by_group[key_seoul])
    rng = np.random.default_rng(0)
    boot_diffs = []
    for _ in range(2000):
        sa = rng.choice(a, size=len(a), replace=True)
        sb = rng.choice(b, size=len(b), replace=True)
        boot_diffs.append(sa.mean() - sb.mean())
    boot_diffs = np.array(boot_diffs)
    ws_diff = dict(
        n_paris=len(a), n_seoul=len(b),
        mean_diff_paris_minus_seoul=float(a.mean() - b.mean()),
        ci95=[float(np.quantile(boot_diffs, 0.025)), float(np.quantile(boot_diffs, 0.975))],
        cohen_d=float(cohen_d(a, b)),
    )
print(f"[ws] paris vs seoul diff: {ws_diff}", flush=True)

# ---------------------------------------------------------------- workouts (Nike runs) x location

nike_runs = [w for w in workouts if w["kind"] == "HKWorkoutActivityTypeRunning"]
print(f"[wo] total workouts={len(workouts)} running={len(nike_runs)}", flush=True)

# For each run, find Timeline place_label at midpoint
run_country_counts = Counter()
run_records = []
for w in nike_runs:
    mid = w["start"] + (w["end"] - w["start"]) / 2
    # try activity overlap first; else visit overlap
    s = find_segment_for(mid)
    country = None
    if s:
        country = s["country"]
    else:
        # search visit
        for v in visit_segs:
            if v["start"] <= mid <= v["end"]:
                country = v["country"]
                break
    if country is None:
        country = country_for_tz_offset_seconds(int(mid.utcoffset().total_seconds()))
    run_country_counts[country] += 1
    run_records.append(dict(start=w["start"].isoformat(), country=country,
                            dur_min=w["dur_min"], dist_km=w["dist_km"]))

print(f"[wo] run country: {run_country_counts}", flush=True)

def summarize_runs(country):
    rs = [r for r in run_records if r["country"] == country]
    if not rs:
        return None
    durs = np.array([r["dur_min"] for r in rs])
    dists = np.array([r["dist_km"] for r in rs])
    return dict(
        n=len(rs),
        dur_min_mean=float(durs.mean()), dur_min_median=float(np.median(durs)),
        dist_km_mean=float(dists.mean()), dist_km_median=float(np.median(dists)),
    )

run_summary = {c: summarize_runs(c) for c in run_country_counts}
print(f"[wo] run summary: {run_summary}", flush=True)

# ---------------------------------------------------------------- distinct places per day by country

# A "place" is a visit's place_id; "day" is local date
places_by_day = defaultdict(set)   # (country, date) -> set of place_id
for v in visit_segs:
    if v["country"] not in ("Korea", "France"):
        continue
    d = v["start"].date().isoformat()
    if v["place_id"]:
        places_by_day[(v["country"], d)].add(v["place_id"])

per_day_counts = defaultdict(list)
for (c, d), places in places_by_day.items():
    per_day_counts[c].append(len(places))

place_summary = {}
for c, vals in per_day_counts.items():
    m, lo, hi = bootstrap_ci(vals)
    place_summary[c] = dict(
        n_days=len(vals),
        mean_distinct_places=m, ci95=[lo, hi],
        median=float(np.median(vals)),
    )
print(f"[places] {place_summary}", flush=True)

# Diff
place_diff = None
if "Korea" in per_day_counts and "France" in per_day_counts:
    a = np.array(per_day_counts["France"])
    b = np.array(per_day_counts["Korea"])
    rng = np.random.default_rng(0)
    boots = []
    for _ in range(2000):
        sa = rng.choice(a, size=len(a), replace=True)
        sb = rng.choice(b, size=len(b), replace=True)
        boots.append(sa.mean() - sb.mean())
    boots = np.array(boots)
    place_diff = dict(
        mean_diff_france_minus_korea=float(a.mean() - b.mean()),
        ci95=[float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))],
        cohen_d=float(cohen_d(a, b)),
    )
print(f"[places] diff: {place_diff}", flush=True)

# ---------------------------------------------------------------- save

out = dict(
    n_audio_joined=len(joined),
    mode_country_counts={f"{k[0]}|{k[1]}": v for k, v in mode_country.items()},
    anova2_mode_x_country=aov2,
    anova3_mode_x_country_x_tod=aov3,
    per_country_mode_means=per_country_mode,
    within_country_subway_vs_car=within_country,
    walking_speed_seasonmatched=ws_summary,
    walking_speed_paris_vs_seoul_diff=ws_diff,
    nike_runs_total=len(nike_runs),
    nike_runs_country=dict(run_country_counts),
    nike_runs_per_country_summary=run_summary,
    distinct_places_per_day=place_summary,
    distinct_places_diff_france_minus_korea=place_diff,
)

with open(os.path.join(OUT_DIR, "v2_summary.json"), "w") as f:
    json.dump(out, f, indent=2, default=str)

print("\n[done] wrote", os.path.join(OUT_DIR, "v2_summary.json"))
