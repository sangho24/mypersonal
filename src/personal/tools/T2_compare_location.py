"""T2 — Compare activity between two locations (Welch t-test + Cohen's d).

두 장소 (예: 헬스장 A vs 헬스장 B) 에서 측정된 일별 걸음 수 분포를 비교.
- Welch's t-test (unequal variance) — scipy.stats.ttest_ind(equal_var=False)
- Cohen's d (pooled SD, manual) — 효과 크기 라벨
"""

from __future__ import annotations

import numpy as np
from scipy import stats


def _cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    """Cohen's d — pooled SD 분모 (수동 계산)."""
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return float("nan")
    va = float(a.var(ddof=1))
    vb = float(b.var(ddof=1))
    pooled = np.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2))
    if pooled == 0:
        return float("nan")
    return float((a.mean() - b.mean()) / pooled)


def _effect_label(d: float) -> str:
    """Cohen 관습 — |d| < .2 negligible, .2~.5 small, .5~.8 medium, ≥.8 large."""
    ad = abs(d)
    if np.isnan(d):
        return "n/a"
    if ad < 0.2:
        return "negligible"
    if ad < 0.5:
        return "small"
    if ad < 0.8:
        return "medium"
    return "large"


def compare_location_activity(
    loc_a_steps: list[int],
    loc_b_steps: list[int],
    loc_a_name: str,
    loc_b_name: str,
) -> dict:
    """두 장소의 활동량 비교 (Welch t + Cohen's d).

    Returns
    -------
    dict
        {loc_a, loc_b, mean_a, mean_b, n_a, n_b, welch_t, p_value,
         cohens_d, effect_label}
    """
    a = np.asarray(loc_a_steps, dtype=np.float64)
    b = np.asarray(loc_b_steps, dtype=np.float64)
    if len(a) < 2 or len(b) < 2:
        return {
            "loc_a": loc_a_name,
            "loc_b": loc_b_name,
            "mean_a": float(a.mean()) if len(a) else float("nan"),
            "mean_b": float(b.mean()) if len(b) else float("nan"),
            "n_a": int(len(a)),
            "n_b": int(len(b)),
            "welch_t": float("nan"),
            "p_value": float("nan"),
            "cohens_d": float("nan"),
            "effect_label": "n/a",
        }
    t, p = stats.ttest_ind(a, b, equal_var=False)
    d = _cohens_d(a, b)
    return {
        "loc_a": loc_a_name,
        "loc_b": loc_b_name,
        "mean_a": float(a.mean()),
        "mean_b": float(b.mean()),
        "n_a": int(len(a)),
        "n_b": int(len(b)),
        "welch_t": float(t),
        "p_value": float(p),
        "cohens_d": d,
        "effect_label": _effect_label(d),
    }


def _smoke() -> int:
    rng = np.random.default_rng(1)
    a = rng.normal(4000, 600, 14).astype(int).tolist()  # 헬스장 A — 낮음
    b = rng.normal(6700, 800, 14).astype(int).tolist()  # 헬스장 B — 정상
    out = compare_location_activity(a, b, "헬스장 A", "헬스장 B")
    print("[T2 smoke]", out)
    assert out["p_value"] < 0.05, "분명한 차이인데 p ≥ 0.05"
    assert out["cohens_d"] < -0.8, "큰 음의 효과여야 함"
    return 0


if __name__ == "__main__":
    raise SystemExit(_smoke())
