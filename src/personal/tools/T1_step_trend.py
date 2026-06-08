"""T1 — Recent step-count trend vs personal baseline.

DS 도구. Apple Health `StepCount` 일별 합계를 입력으로,
- Pearson r(day_index, steps) — 추세 방향성/유의성
- mean vs baseline_mean — 평균 대비 변화율 (trend_pct)
- anomaly_score — (mean - baseline) / baseline 절댓값
을 산출. LLM 오케스트레이터가 이 결과를 자연어로 통합.

스택: numpy + scipy.stats 만. sklearn 금지.
"""

from __future__ import annotations

import numpy as np
from scipy import stats


def get_recent_step_trend(
    daily_steps: dict[str, int],
    window_days: int = 14,
    baseline_mean: float = 6445.0,
) -> dict:
    """최근 window_days 일의 걸음 추세를 베이스라인과 비교.

    Parameters
    ----------
    daily_steps : dict[str, int]
        ISO 날짜(YYYY-MM-DD) → 일별 걸음 수. **정렬은 호출자 책임**.
    window_days : int
        분석 윈도우 (꼬리 기준).
    baseline_mean : float
        장기 평균 (Phase 1 에서 산출한 개인 베이스라인).

    Returns
    -------
    dict
        {window_days, mean_steps, baseline_mean, trend_pct, pearson_r,
         p_value, anomaly_score, n}
    """
    # 날짜 정렬 후 꼬리 window_days
    items = sorted(daily_steps.items())[-window_days:]
    if len(items) < 3:
        return {
            "window_days": window_days,
            "mean_steps": float("nan"),
            "baseline_mean": baseline_mean,
            "trend_pct": float("nan"),
            "pearson_r": float("nan"),
            "p_value": float("nan"),
            "anomaly_score": float("nan"),
            "n": len(items),
        }

    steps = np.array([s for _, s in items], dtype=np.float64)
    days = np.arange(len(steps), dtype=np.float64)
    r, p = stats.pearsonr(days, steps)
    mean_steps = float(steps.mean())
    trend_pct = float((mean_steps - baseline_mean) / baseline_mean * 100.0)
    anomaly_score = float(abs(mean_steps - baseline_mean) / baseline_mean)

    return {
        "window_days": window_days,
        "mean_steps": mean_steps,
        "baseline_mean": float(baseline_mean),
        "trend_pct": trend_pct,
        "pearson_r": float(r),
        "p_value": float(p),
        "anomaly_score": anomaly_score,
        "n": int(len(steps)),
    }


def _smoke() -> int:
    """합성 데이터로 함수가 형식 통과/하강 추세를 잡는지 확인."""
    rng = np.random.default_rng(0)
    # 14일 하강 추세: 7000 → 3800
    base = np.linspace(7000, 3800, 14) + rng.normal(0, 200, 14)
    daily = {f"2026-05-{i + 1:02d}": int(v) for i, v in enumerate(base)}
    out = get_recent_step_trend(daily, window_days=14, baseline_mean=6445.0)
    print("[T1 smoke]", out)
    assert out["n"] == 14
    assert out["pearson_r"] < 0, "하강 추세인데 r >= 0 — 버그"
    assert out["trend_pct"] < 0, "베이스라인보다 낮아야 함"
    return 0


if __name__ == "__main__":
    raise SystemExit(_smoke())
