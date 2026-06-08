"""Stream-parse Apple Health XML and aggregate to daily features.

Extracts: steps, walking_speed, step_length, asymmetry, double_support,
audio_max_dB, audio_listening_minutes.

Caches to /tmp/personal_daily.parquet.
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime

import numpy as np
import pandas as pd

XML_PATH = "/Users/sangho/Downloads/apple_health_export/내보내기.xml"
OUT = "/tmp/personal_daily_hmm.parquet"

# Feature -> Apple Health type identifier
TYPES = {
    "steps": "HKQuantityTypeIdentifierStepCount",
    "distance_km": "HKQuantityTypeIdentifierDistanceWalkingRunning",
    "walking_speed": "HKQuantityTypeIdentifierWalkingSpeed",                    # km/h
    "step_length": "HKQuantityTypeIdentifierWalkingStepLength",                 # cm
    "asymmetry": "HKQuantityTypeIdentifierWalkingAsymmetryPercentage",          # %
    "double_support": "HKQuantityTypeIdentifierWalkingDoubleSupportPercentage", # %
    "audio_env": "HKQuantityTypeIdentifierEnvironmentalAudioExposure",          # dB
    "audio_hp": "HKQuantityTypeIdentifierHeadphoneAudioExposure",               # dB
    "audio_hp_dur": "HKQuantityTypeIdentifierHeadphoneAudioExposureEvent",      # event count
}
INVERSE = {v: k for k, v in TYPES.items()}


def _parse_dt(s: str) -> datetime | None:
    # "2024-01-15 09:23:45 +0900"
    try:
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def main() -> int:
    # per-day per-feature accumulators
    sums: dict[str, dict[pd.Timestamp, float]] = defaultdict(lambda: defaultdict(float))
    counts: dict[str, dict[pd.Timestamp, int]] = defaultdict(lambda: defaultdict(int))
    maxes: dict[str, dict[pd.Timestamp, float]] = defaultdict(lambda: defaultdict(float))
    audio_listen_seconds: dict[pd.Timestamp, float] = defaultdict(float)

    ctx = ET.iterparse(XML_PATH, events=("end",))
    n = 0
    for ev, el in ctx:
        if el.tag == "Record":
            t = el.get("type")
            feat = INVERSE.get(t)
            if feat is None:
                el.clear()
                continue
            sd = el.get("startDate")
            ed = el.get("endDate")
            val_s = el.get("value")
            if sd is None or val_s is None:
                el.clear()
                continue
            try:
                v = float(val_s)
            except ValueError:
                el.clear()
                continue
            sdt = _parse_dt(sd)
            if sdt is None:
                el.clear()
                continue
            day = pd.Timestamp(sdt.date())

            if feat in ("steps", "distance_km"):
                sums[feat][day] += v
            elif feat in ("walking_speed", "step_length", "asymmetry", "double_support"):
                sums[feat][day] += v
                counts[feat][day] += 1
            elif feat in ("audio_env", "audio_hp"):
                # max dB of day across both env and headphone — combined audio_max_dB
                if v > maxes["audio_max_dB"][day]:
                    maxes["audio_max_dB"][day] = v
                # listening minutes: only headphones with duration
                if feat == "audio_hp" and ed is not None:
                    edt = _parse_dt(ed)
                    if edt is not None:
                        dur_s = max(0.0, (edt - sdt).total_seconds())
                        audio_listen_seconds[day] += dur_s
            n += 1
            if n % 200000 == 0:
                print(f"  ...{n:,} records", file=sys.stderr)
        el.clear()

    # Assemble dataframe
    all_days: set[pd.Timestamp] = set()
    for d in sums.values():
        all_days |= d.keys()
    for d in maxes.values():
        all_days |= d.keys()
    all_days |= audio_listen_seconds.keys()
    days = sorted(all_days)

    rows = []
    for day in days:
        rows.append(
            {
                "date": day,
                "steps": sums["steps"].get(day, np.nan),
                "distance_km": sums["distance_km"].get(day, np.nan) / 1000.0
                if sums["distance_km"].get(day) is not None and sums["distance_km"].get(day, 0) > 100
                else sums["distance_km"].get(day, np.nan),
                "walking_speed": (sums["walking_speed"].get(day, np.nan) / counts["walking_speed"][day])
                if counts["walking_speed"].get(day, 0) > 0 else np.nan,
                "step_length": (sums["step_length"].get(day, np.nan) / counts["step_length"][day])
                if counts["step_length"].get(day, 0) > 0 else np.nan,
                "asymmetry": (sums["asymmetry"].get(day, np.nan) / counts["asymmetry"][day])
                if counts["asymmetry"].get(day, 0) > 0 else np.nan,
                "double_support": (sums["double_support"].get(day, np.nan) / counts["double_support"][day])
                if counts["double_support"].get(day, 0) > 0 else np.nan,
                "audio_max_dB": maxes["audio_max_dB"].get(day, np.nan)
                if day in maxes["audio_max_dB"] else np.nan,
                "audio_listen_min": audio_listen_seconds.get(day, 0.0) / 60.0,
            }
        )
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    df.to_parquet(OUT, index=False)
    print(f"wrote {OUT}  shape={df.shape}")
    print(df.describe(include="all").T[["count", "mean", "std", "min", "max"]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
