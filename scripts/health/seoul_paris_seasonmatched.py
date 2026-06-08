"""Season-matched contrast: Paris Feb-Jun 2025 vs Seoul Feb-Jun 2026.

Addresses the season confound in the naive contrast (Paris=spring vs Seoul=fall).
Re-uses the helpers from seoul_paris_power.py.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from seoul_paris_power import (  # type: ignore
    cohens_d,
    load_health_daily,
    load_timeline_city_map,
    stats_summary,
    welch_t,
)
import seoul_paris_power as _spp


def main() -> None:
    # Override window for health loader: we need both 2025 and 2026 in-window
    _spp.WINDOW_START = date(2025, 2, 1)
    _spp.WINDOW_END = date(2026, 6, 30)

    day_to_city, _ = load_timeline_city_map()
    paris_dates = sorted(d for d, c in day_to_city.items()
                         if c == "Paris" and date(2025, 2, 1) <= d <= date(2025, 6, 30))
    seoul_dates = sorted(d for d, c in day_to_city.items()
                         if c == "Seoul" and date(2026, 2, 1) <= d <= date(2026, 6, 30))
    print(f"[season-matched] Paris(2025 Feb-Jun)={len(paris_dates)}, "
          f"Seoul(2026 Feb-Jun)={len(seoul_dates)}")

    metrics = load_health_daily()
    print("\n=== SEASON-MATCHED COMPARISONS ===")
    big = 0
    total = 0
    for name in ["daily_steps", "walking_speed", "step_length",
                 "daily_audio_max_dB", "daily_audio_mean_dB"]:
        dct = metrics.get(name)
        if not dct:
            continue
        s_vals = [dct[d] for d in seoul_dates if d in dct]
        p_vals = [dct[d] for d in paris_dates if d in dct]
        if len(s_vals) < 5 or len(p_vals) < 5:
            print(f"[{name}] insufficient: Seoul n={len(s_vals)}, Paris n={len(p_vals)}")
            continue
        ss = stats_summary(s_vals)
        ps = stats_summary(p_vals)
        t, df, pval = welch_t(s_vals, p_vals)
        d_eff = cohens_d(s_vals, p_vals)
        total += 1
        if abs(d_eff) > 0.5:
            big += 1
        print(f"\n[{name}]")
        print(f"  Seoul(26): n={ss['n']:>3}  mean={ss['mean']:.2f}  med={ss['median']:.2f}  sd={ss['sd']:.2f}")
        print(f"  Paris(25): n={ps['n']:>3}  mean={ps['mean']:.2f}  med={ps['median']:.2f}  sd={ps['sd']:.2f}")
        print(f"  Welch t={t:.3f}  df={df:.1f}  p={pval:.4g}  |  Cohen's d={d_eff:.3f}")
    print(f"\n[summary] season-matched |d|>0.5: {big}/{total}")


if __name__ == "__main__":
    main()
