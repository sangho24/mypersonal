"""T3 — Gait quality z-score check.

Apple Health 보행 지표 4종 (walking_speed, step_length, asymmetry, double_support)
을 개인 베이스라인 평균/표준편차와 비교해 z-score 산출.
asymmetry/double_support 는 높을수록 나쁨 → z 부호를 그대로 사용,
walking_speed/step_length 는 낮을수록 나쁨 → 부호를 뒤집어 "악화 방향" 으로 통일.
"""

from __future__ import annotations

import math

_METRICS = ("walking_speed", "step_length", "asymmetry", "double_support")
# 부호 정렬: +1 이면 "값이 클수록 악화", -1 이면 "값이 작을수록 악화"
_BAD_DIRECTION = {
    "walking_speed": -1,
    "step_length": -1,
    "asymmetry": +1,
    "double_support": +1,
}


def _verdict_from_z(zs: dict[str, float]) -> str:
    """가장 나쁜 (부호정렬 후 큰 양수) z 를 기준으로 verdict."""
    bad_zs = [
        _BAD_DIRECTION[m] * zs.get(f"{m}_z", 0.0)
        for m in _METRICS
        if not math.isnan(zs.get(f"{m}_z", float("nan")))
    ]
    if not bad_zs:
        return "insufficient_data"
    worst = max(bad_zs)
    if worst >= 2.0:
        return "concern"
    if worst >= 1.0:
        return "watch"
    return "normal"


def check_gait_quality(
    window_metrics: dict[str, float],
    baseline_means: dict[str, float],
    baseline_sds: dict[str, float],
) -> dict:
    """4-지표 z-score + 종합 판정.

    Parameters
    ----------
    window_metrics : dict[str, float]
        최근 윈도우의 평균값. 키는 _METRICS 중 일부 또는 전부.
    baseline_means / baseline_sds : dict[str, float]
        개인 베이스라인 통계.

    Returns
    -------
    dict
        {walking_speed_z, step_length_z, asymmetry_z, double_support_z,
         quality_verdict, n_days}
    """
    zs: dict[str, float] = {}
    for m in _METRICS:
        x = window_metrics.get(m, float("nan"))
        mu = baseline_means.get(m, float("nan"))
        sd = baseline_sds.get(m, float("nan"))
        if math.isnan(x) or math.isnan(mu) or math.isnan(sd) or sd <= 0:
            zs[f"{m}_z"] = float("nan")
        else:
            zs[f"{m}_z"] = float((x - mu) / sd)
    out: dict = dict(zs)
    out["quality_verdict"] = _verdict_from_z(zs)
    out["n_days"] = int(window_metrics.get("n_days", 14))
    return out


def _smoke() -> int:
    # 합성: walking_speed 가 베이스라인보다 1.5 SD 낮고, asymmetry 가 2 SD 높음 → "concern"
    baseline_means = {
        "walking_speed": 1.20,
        "step_length": 0.70,
        "asymmetry": 3.0,
        "double_support": 27.0,
    }
    baseline_sds = {
        "walking_speed": 0.10,
        "step_length": 0.05,
        "asymmetry": 1.0,
        "double_support": 2.0,
    }
    window = {
        "walking_speed": 1.05,   # -1.5 SD  → 부호반전 후 +1.5
        "step_length": 0.66,     # -0.8 SD  → +0.8
        "asymmetry": 5.0,        # +2.0 SD
        "double_support": 28.5,  # +0.75 SD
        "n_days": 14,
    }
    out = check_gait_quality(window, baseline_means, baseline_sds)
    print("[T3 smoke]", out)
    assert out["quality_verdict"] == "concern"
    return 0


if __name__ == "__main__":
    raise SystemExit(_smoke())
