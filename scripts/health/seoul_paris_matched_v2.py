"""V2: Matched-pair Seoul/Paris contrast with covariate stratification.

Addresses v1's "only 1/5 metrics survived" failure by:
  1. Within-season matched pairs (each Paris day paired with the nearest Seoul day
     within +/-30 days of *seasonal offset*, i.e., same day-of-year +/- 30).
  2. Paired tests: Wilcoxon signed-rank + paired t.
  3. Bootstrap CIs (1000 paired resamples) on the median paired delta.
  4. Weekend/weekday stratifier.
  5. Tourist-novelty stratifier: first 30 days vs rest of Paris stay.
  6. New metric: daily_step_intensity = steps / hours_with_recorded_movement.
  7. Six metrics tested.

No scipy: paired t-cdf reuses seoul_paris_power Student-t helpers.
"""
from __future__ import annotations

import math
import random
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, median

sys.path.insert(0, str(Path(__file__).parent))
from seoul_paris_power import (  # type: ignore
    HEALTH_XML,
    TIMELINE_JSON,
    load_timeline_city_map,
    student_t_cdf,
    parse_apple_date,
    parse_iso,
    parse_geo,
    classify_city,
)
import seoul_paris_power as _spp


# ----------------------------- Health loader (extended) -----------------------------

METRIC_MAP_V2 = {
    "HKQuantityTypeIdentifierStepCount":
        ("daily_steps", "sum"),
    "HKQuantityTypeIdentifierWalkingSpeed":
        ("walking_speed", "mean"),
    "HKQuantityTypeIdentifierWalkingStepLength":
        ("step_length", "mean"),
    "HKQuantityTypeIdentifierHeadphoneAudioExposure":
        ("headphone_dB_mean", "mean"),
    "HKCategoryTypeIdentifierAudioExposureEvent":
        ("audio_event_count", "count"),
    # Optional: audio_listening_minutes via durations on AudioExposure records is not
    # directly exposed; we approximate via per-day audio-record span (start..end).
}


def load_health_extended() -> tuple[dict[str, dict[date, float]], dict[date, set[int]]]:
    """Return (metric -> day -> value, day -> set of distinct active hours).

    Active hour set comes from any motion-related record (steps, walking speed, step length)
    -> used to compute hours_with_recorded_movement.
    Also collects audio_listening_minutes = sum of audio record durations (endDate-startDate).
    """
    sums: dict[str, dict[date, float]] = defaultdict(lambda: defaultdict(float))
    means_data: dict[str, dict[date, list[float]]] = defaultdict(lambda: defaultdict(list))
    audio_minutes: dict[date, float] = defaultdict(float)
    active_hours: dict[date, set[int]] = defaultdict(set)

    # Widen window: we need 2024 thru 2026
    win_start = date(2024, 1, 1)
    win_end = date(2026, 12, 31)

    for _, elem in ET.iterparse(HEALTH_XML, events=("end",)):
        if elem.tag != "Record":
            elem.clear()
            continue
        rtype = elem.get("type", "")
        sd = elem.get("startDate", "")
        ed = elem.get("endDate", sd)
        d = parse_apple_date(sd)
        if not d or d < win_start or d > win_end:
            elem.clear()
            continue

        # Active hours (motion proxy): step counts, walking speed, step length
        if rtype in (
            "HKQuantityTypeIdentifierStepCount",
            "HKQuantityTypeIdentifierWalkingSpeed",
            "HKQuantityTypeIdentifierWalkingStepLength",
            "HKQuantityTypeIdentifierDistanceWalkingRunning",
        ):
            try:
                hr = int(sd[11:13])
                active_hours[d].add(hr)
            except Exception:
                pass

        # Audio listening minutes (HeadphoneAudioExposure has start..end span)
        if rtype == "HKQuantityTypeIdentifierHeadphoneAudioExposure":
            try:
                t0 = datetime.strptime(sd[:19], "%Y-%m-%d %H:%M:%S")
                t1 = datetime.strptime(ed[:19], "%Y-%m-%d %H:%M:%S")
                dur_min = max(0.0, (t1 - t0).total_seconds() / 60.0)
                # Cap absurd durations (>60min per record is unusual)
                if dur_min <= 120.0:
                    audio_minutes[d] += dur_min
            except Exception:
                pass

        if rtype not in METRIC_MAP_V2:
            elem.clear()
            continue
        try:
            val = float(elem.get("value", "nan"))
        except ValueError:
            elem.clear()
            continue
        name, agg = METRIC_MAP_V2[rtype]
        if agg == "sum":
            sums[name][d] += val
        elif agg == "mean":
            means_data[name][d].append(val)
        elif agg == "count":
            sums[name][d] += 1
        elem.clear()

    result: dict[str, dict[date, float]] = {}
    for name, dct in sums.items():
        result[name] = dict(dct)
    for name, dct in means_data.items():
        result[name] = {d: sum(vs) / len(vs) for d, vs in dct.items() if vs}
    result["audio_listening_minutes"] = dict(audio_minutes)

    # daily_step_intensity = steps / hours_with_recorded_movement
    intensity: dict[date, float] = {}
    steps = result.get("daily_steps", {})
    for d, st in steps.items():
        h = len(active_hours.get(d, set()))
        if h >= 3 and st > 0:  # require >=3 active hours (drops sparse days)
            intensity[d] = st / h
    result["daily_step_intensity"] = intensity

    return result, active_hours


# ----------------------------- Matched-pair construction -----------------------------

def day_of_year(d: date) -> int:
    return d.timetuple().tm_yday


def build_matched_pairs(
    paris_dates: list[date],
    seoul_dates: list[date],
    metric: dict[date, float],
    max_offset_doy: int = 30,
) -> list[tuple[date, date, float, float]]:
    """For each Paris day with metric, find Seoul day with the smallest
    |day-of-year delta| (circular) such that metric exists. Each Seoul day
    may be reused (with replacement) to keep all Paris days that match.

    Returns list of (paris_date, seoul_date, paris_val, seoul_val).
    """
    pairs: list[tuple[date, date, float, float]] = []
    seoul_with_metric = [d for d in seoul_dates if d in metric]
    if not seoul_with_metric:
        return pairs
    for pd in paris_dates:
        if pd not in metric:
            continue
        pdoy = day_of_year(pd)
        # circular doy distance (year wrap)
        def circ_diff(s: date) -> int:
            a = abs(day_of_year(s) - pdoy)
            return min(a, 366 - a)
        best = min(seoul_with_metric, key=circ_diff)
        if circ_diff(best) <= max_offset_doy:
            pairs.append((pd, best, metric[pd], metric[best]))
    return pairs


# ----------------------------- Stats (paired) -----------------------------

def paired_t(diffs: list[float]) -> tuple[float, float, float]:
    n = len(diffs)
    if n < 2:
        return float("nan"), float("nan"), float("nan")
    m = mean(diffs)
    var = sum((x - m) ** 2 for x in diffs) / (n - 1)
    sd = math.sqrt(var) if var > 0 else 0.0
    if sd == 0:
        return float("nan"), float(n - 1), float("nan")
    se = sd / math.sqrt(n)
    t = m / se
    df = n - 1
    p = 2 * (1 - student_t_cdf(abs(t), df))
    return t, df, p


def cohens_dz(diffs: list[float]) -> float:
    """Paired-design Cohen's dz = mean(diff) / sd(diff)."""
    n = len(diffs)
    if n < 2:
        return float("nan")
    m = mean(diffs)
    var = sum((x - m) ** 2 for x in diffs) / (n - 1)
    sd = math.sqrt(var) if var > 0 else 0.0
    return m / sd if sd > 0 else float("nan")


def wilcoxon_signed_rank(diffs: list[float]) -> tuple[float, float]:
    """Return (W+, asymptotic-z two-sided p). Drops zeros, average ranks for ties."""
    nz = [d for d in diffs if d != 0.0]
    n = len(nz)
    if n < 6:
        return float("nan"), float("nan")
    abs_sorted = sorted(range(n), key=lambda i: abs(nz[i]))
    # ranks with average for ties on absolute value
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(nz[abs_sorted[j + 1]]) == abs(nz[abs_sorted[i]]):
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0  # 1-indexed ranks
        for k in range(i, j + 1):
            ranks[abs_sorted[k]] = avg_rank
        i = j + 1
    w_plus = sum(r for r, d in zip(ranks, nz) if d > 0)
    mu = n * (n + 1) / 4.0
    sigma = math.sqrt(n * (n + 1) * (2 * n + 1) / 24.0)
    if sigma == 0:
        return w_plus, float("nan")
    z = (w_plus - mu) / sigma
    # standard normal two-sided p
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return w_plus, p


def bootstrap_ci_median_delta(
    diffs: list[float], n_boot: int = 1000, alpha: float = 0.05, seed: int = 42
) -> tuple[float, float, float]:
    """Bootstrap percentile CI on median(diff). Returns (median_obs, lo, hi)."""
    if len(diffs) < 5:
        return float("nan"), float("nan"), float("nan")
    rng = random.Random(seed)
    n = len(diffs)
    obs = median(diffs)
    boots: list[float] = []
    for _ in range(n_boot):
        sample = [diffs[rng.randint(0, n - 1)] for _ in range(n)]
        boots.append(median(sample))
    boots.sort()
    lo = boots[int((alpha / 2) * n_boot)]
    hi = boots[int((1 - alpha / 2) * n_boot) - 1]
    return obs, lo, hi


def bootstrap_ci_dz(
    diffs: list[float], n_boot: int = 1000, alpha: float = 0.05, seed: int = 7
) -> tuple[float, float, float]:
    if len(diffs) < 5:
        return float("nan"), float("nan"), float("nan")
    rng = random.Random(seed)
    n = len(diffs)
    obs = cohens_dz(diffs)
    boots: list[float] = []
    for _ in range(n_boot):
        sample = [diffs[rng.randint(0, n - 1)] for _ in range(n)]
        boots.append(cohens_dz(sample))
    boots.sort()
    lo = boots[int((alpha / 2) * n_boot)]
    hi = boots[int((1 - alpha / 2) * n_boot) - 1]
    return obs, lo, hi


# ----------------------------- Analysis driver -----------------------------

METRICS_V2 = [
    "daily_steps",
    "walking_speed",
    "step_length",
    "headphone_dB_mean",
    "daily_step_intensity",
    "audio_listening_minutes",
]


def main() -> None:
    _spp.WINDOW_START = date(2024, 1, 1)
    _spp.WINDOW_END = date(2026, 12, 31)

    print("[load] timeline ...")
    day_to_city, _ = load_timeline_city_map()
    paris_all = sorted(d for d, c in day_to_city.items() if c == "Paris")
    seoul_all = sorted(d for d, c in day_to_city.items() if c == "Seoul")
    print(f"  Paris labeled days={len(paris_all)} "
          f"range={paris_all[0]}..{paris_all[-1]}" if paris_all else "")
    print(f"  Seoul labeled days={len(seoul_all)} "
          f"range={seoul_all[0]}..{seoul_all[-1]}" if seoul_all else "")

    print("[load] health (extended)...")
    metrics, active_hours = load_health_extended()
    for name in METRICS_V2:
        dct = metrics.get(name) or {}
        print(f"  {name}: n_days={len(dct)}")

    # Restrict Paris to the actual stay window Feb-Jun 2025
    paris_window = [d for d in paris_all if date(2025, 2, 1) <= d <= date(2025, 6, 30)]
    print(f"\n[window] Paris stay window: n={len(paris_window)} days "
          f"{paris_window[0] if paris_window else '-'}..{paris_window[-1] if paris_window else '-'}")
    if paris_window:
        paris_start = paris_window[0]
        print(f"[novelty] tourist novelty cutoff: first 30 days = "
              f"{paris_start}..{paris_start + timedelta(days=29)}")

    print("\n=== MATCHED-PAIR RESULTS (6 metrics) ===")
    big_count = 0
    total = 0
    summary_rows = []
    novelty_rows = []
    weekday_rows = []
    for name in METRICS_V2:
        metric = metrics.get(name)
        if not metric:
            print(f"\n[{name}] METRIC MISSING")
            continue
        pairs = build_matched_pairs(paris_window, seoul_all, metric, max_offset_doy=30)
        n_pairs = len(pairs)
        if n_pairs < 10:
            print(f"\n[{name}] insufficient matched pairs (n={n_pairs})")
            continue
        diffs = [pv - sv for _, _, pv, sv in pairs]  # Paris - Seoul
        t, df, pval = paired_t(diffs)
        w_plus, w_p = wilcoxon_signed_rank(diffs)
        dz = cohens_dz(diffs)
        med_obs, med_lo, med_hi = bootstrap_ci_median_delta(diffs)
        dz_obs, dz_lo, dz_hi = bootstrap_ci_dz(diffs)
        total += 1
        if abs(dz) > 0.5:
            big_count += 1
        seoul_mean = mean([sv for _, _, _, sv in pairs])
        paris_mean = mean([pv for _, _, pv, _ in pairs])
        print(f"\n[{name}]  n_pairs={n_pairs}")
        print(f"  Paris mean={paris_mean:.3f}   Seoul mean={seoul_mean:.3f}")
        print(f"  median(Paris-Seoul)={med_obs:.3f}  95% boot CI [{med_lo:.3f}, {med_hi:.3f}]")
        print(f"  paired t={t:.3f}  df={df:.0f}  p={pval:.4g}")
        print(f"  Wilcoxon W+={w_plus:.1f}  p_asymp={w_p:.4g}")
        print(f"  Cohen's dz={dz:.3f}  95% boot CI [{dz_lo:.3f}, {dz_hi:.3f}]")
        summary_rows.append((name, n_pairs, paris_mean, seoul_mean, med_obs,
                             med_lo, med_hi, dz, dz_lo, dz_hi, pval, w_p))

        # ---- Stratifier 1: weekend (Sat=5, Sun=6) vs weekday ----
        wknd = [d for d in diffs if False]  # placeholder
        wknd_diffs = [pv - sv for (pd, sd, pv, sv) in pairs if pd.weekday() >= 5]
        wkdy_diffs = [pv - sv for (pd, sd, pv, sv) in pairs if pd.weekday() < 5]
        if len(wknd_diffs) >= 6 and len(wkdy_diffs) >= 10:
            dz_wknd = cohens_dz(wknd_diffs)
            dz_wkdy = cohens_dz(wkdy_diffs)
            print(f"  [weekend strat]   weekend dz={dz_wknd:.3f}  (n={len(wknd_diffs)})"
                  f"  weekday dz={dz_wkdy:.3f}  (n={len(wkdy_diffs)})")
            weekday_rows.append((name, dz_wknd, len(wknd_diffs), dz_wkdy, len(wkdy_diffs)))

        # ---- Stratifier 2: tourist novelty — first 30 Paris days vs rest ----
        if paris_window:
            cut = paris_start + timedelta(days=30)
            early = [pv - sv for (pd, sd, pv, sv) in pairs if pd < cut]
            late = [pv - sv for (pd, sd, pv, sv) in pairs if pd >= cut]
            if len(early) >= 6 and len(late) >= 6:
                dz_e = cohens_dz(early)
                dz_l = cohens_dz(late)
                ratio = (dz_l / dz_e) if dz_e != 0 else float("nan")
                # Halving test: late/early < 0.5 supports novelty hypothesis
                halves = (abs(dz_l) < 0.5 * abs(dz_e)) if dz_e != 0 else False
                # Bootstrap CI for (late - early) of dz
                rng = random.Random(11)
                boots = []
                ne, nl = len(early), len(late)
                for _ in range(1000):
                    s_e = [early[rng.randint(0, ne - 1)] for _ in range(ne)]
                    s_l = [late[rng.randint(0, nl - 1)] for _ in range(nl)]
                    boots.append(cohens_dz(s_l) - cohens_dz(s_e))
                boots.sort()
                d_lo, d_hi = boots[25], boots[974]
                print(f"  [novelty strat]   early(<30d) dz={dz_e:.3f} (n={ne})  "
                      f"late(>=30d) dz={dz_l:.3f} (n={nl})  ratio late/early={ratio:.2f}  "
                      f"halves={halves}  Δdz CI=[{d_lo:.2f},{d_hi:.2f}]")
                novelty_rows.append((name, dz_e, ne, dz_l, nl, ratio, halves,
                                     d_lo, d_hi))

    print(f"\n=== SUMMARY ===")
    print(f"Metrics with |Cohen's dz|>0.5 (matched-pair): {big_count}/{total}")
    halve_yes = sum(1 for r in novelty_rows if r[6])
    halve_total = len(novelty_rows)
    print(f"Tourist-novelty 'effect halves in late period' supported: {halve_yes}/{halve_total} metrics")

    # Per-metric summary table
    print("\nmetric | n | Paris | Seoul | med(P-S) [95% CI] | dz [95% CI] | p_paired | p_wilcox")
    for row in summary_rows:
        name, n, pm, sm, mo, ml, mh, dz, dl, dh, pp, pw = row
        print(f"  {name:>26s} | {n:3d} | {pm:9.2f} | {sm:9.2f} | "
              f"{mo:8.2f} [{ml:7.2f},{mh:7.2f}] | "
              f"{dz:5.2f} [{dl:5.2f},{dh:5.2f}] | {pp:7.4g} | {pw:7.4g}")

    # Save CSV-style for the report
    out_dir = Path("/Users/sangho/Desktop/빅데이터컴퓨팅/wine-mab-project/results/health")
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "matched_pair_summary_v2.csv").open("w") as f:
        f.write("metric,n_pairs,paris_mean,seoul_mean,median_diff,med_lo,med_hi,dz,dz_lo,dz_hi,p_paired,p_wilcox\n")
        for row in summary_rows:
            f.write(",".join(str(x) for x in row) + "\n")
    with (out_dir / "novelty_strat_v2.csv").open("w") as f:
        f.write("metric,dz_early,n_early,dz_late,n_late,ratio_late_over_early,halves,delta_dz_lo,delta_dz_hi\n")
        for row in novelty_rows:
            f.write(",".join(str(x) for x in row) + "\n")
    with (out_dir / "weekday_strat_v2.csv").open("w") as f:
        f.write("metric,dz_weekend,n_weekend,dz_weekday,n_weekday\n")
        for row in weekday_rows:
            f.write(",".join(str(x) for x in row) + "\n")
    print(f"\n[saved] {out_dir}/matched_pair_summary_v2.csv (+novelty,+weekday)")


if __name__ == "__main__":
    main()
