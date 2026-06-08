"""T4 — Audio exposure summary (headphone/environmental dB).

Apple Health `HeadphoneAudioExposure` / `EnvironmentalAudioExposure` 분단위
샘플(dB)을 입력으로,
- mean / p95 / max
- hours_above_80dB (NIOSH 권고 — 1 분 단위 가정)
- (옵션) mode_groups (헬스장 vs 카페 vs 출퇴근 등) 가 주어지면 one-way ANOVA hook.
"""

from __future__ import annotations

import numpy as np
from scipy import stats


def audio_exposure_summary(
    audio_db_records: list[float],
    n_minutes: int = 60,
    mode_groups: dict[str, list[float]] | None = None,
) -> dict:
    """헤드폰/환경 소음 노출 요약.

    Parameters
    ----------
    audio_db_records : list[float]
        분단위 dB 샘플 (1 record = 1 minute 로 가정).
    n_minutes : int
        분석 윈도우 길이(분). 메타데이터로만 사용.
    mode_groups : dict[str, list[float]] | None
        주어지면 그룹별 평균 차이에 대해 one-way ANOVA 실행.

    Returns
    -------
    dict
        {mean_db, p95_db, max_db, hours_above_80db, n_minutes, verdict,
         (anova_f, anova_p)?}
    """
    if not audio_db_records:
        return {
            "mean_db": float("nan"),
            "p95_db": float("nan"),
            "max_db": float("nan"),
            "hours_above_80db": 0.0,
            "n_minutes": int(n_minutes),
            "verdict": "insufficient_data",
        }
    arr = np.asarray(audio_db_records, dtype=np.float64)
    mean_db = float(arr.mean())
    p95_db = float(np.percentile(arr, 95))
    max_db = float(arr.max())
    minutes_above_80 = int((arr >= 80.0).sum())
    hours_above_80 = minutes_above_80 / 60.0

    # NIOSH 기준 거칠게 — p95 ≥ 85 또는 ≥1h above 80 → concern
    if p95_db >= 85.0 or hours_above_80 >= 1.0:
        verdict = "concern"
    elif p95_db >= 80.0:
        verdict = "watch"
    else:
        verdict = "safe"

    out: dict = {
        "mean_db": mean_db,
        "p95_db": p95_db,
        "max_db": max_db,
        "hours_above_80db": float(hours_above_80),
        "n_minutes": int(n_minutes),
        "verdict": verdict,
    }
    if mode_groups and len(mode_groups) >= 2:
        groups = [np.asarray(v, dtype=np.float64) for v in mode_groups.values() if len(v) >= 2]
        if len(groups) >= 2:
            f, p = stats.f_oneway(*groups)
            out["anova_f"] = float(f)
            out["anova_p"] = float(p)
    return out


def _smoke() -> int:
    rng = np.random.default_rng(2)
    # 60분 중 절반은 75 dB, 절반은 88 dB (지하철/헬스장 BGM 가정)
    rec = np.concatenate(
        [rng.normal(75, 2, 30), rng.normal(88, 3, 30)]
    ).tolist()
    out = audio_exposure_summary(rec, n_minutes=60)
    print("[T4 smoke]", out)
    assert out["verdict"] in ("concern", "watch")
    assert out["max_db"] > 80
    # ANOVA hook 확인
    groups = {"quiet": rng.normal(60, 2, 30).tolist(), "loud": rng.normal(85, 3, 30).tolist()}
    out2 = audio_exposure_summary(rec, n_minutes=60, mode_groups=groups)
    assert "anova_p" in out2
    print("[T4 smoke anova]", {"f": out2["anova_f"], "p": out2["anova_p"]})
    return 0


if __name__ == "__main__":
    raise SystemExit(_smoke())
