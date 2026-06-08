"""T5 — Today's step count anomaly vs peer (weekday-conditioned).

오늘의 걸음 수를 같은 요일의 과거 분포 (peer_steps) 와 비교해 z-score 와 percentile 산출.
호출자가 weekday-conditioned 표본을 미리 추려서 peer_steps 로 넘기면, 본 함수는
numpy 만으로 z-score / percentile / anomaly flag 를 계산.
"""

from __future__ import annotations

import numpy as np


def detect_step_anomaly(today_steps: int, peer_steps: list[int]) -> dict:
    """오늘 걸음수 vs 같은 요일 peer 분포.

    Parameters
    ----------
    today_steps : int
        오늘 걸음 수.
    peer_steps : list[int]
        비교 대상 (같은 요일 과거 N 주, 또는 동년배 cohort).

    Returns
    -------
    dict
        {today_steps, peer_mean, peer_sd, z_score, percentile, is_anomaly}
        is_anomaly == True iff |z| >= 2.0
    """
    peer = np.asarray(peer_steps, dtype=np.float64)
    if peer.size < 3:
        return {
            "today_steps": int(today_steps),
            "peer_mean": float("nan"),
            "peer_sd": float("nan"),
            "z_score": float("nan"),
            "percentile": float("nan"),
            "is_anomaly": False,
        }
    mu = float(peer.mean())
    sd = float(peer.std(ddof=1))
    z = float((today_steps - mu) / sd) if sd > 0 else 0.0
    pct = float((peer < today_steps).mean() * 100.0)
    return {
        "today_steps": int(today_steps),
        "peer_mean": mu,
        "peer_sd": sd,
        "z_score": z,
        "percentile": pct,
        "is_anomaly": bool(abs(z) >= 2.0),
    }


def _smoke() -> int:
    rng = np.random.default_rng(3)
    peer = rng.normal(7000, 1200, 50).astype(int).tolist()
    out_low = detect_step_anomaly(2500, peer)
    out_mid = detect_step_anomaly(7100, peer)
    print("[T5 smoke low ]", out_low)
    print("[T5 smoke mid ]", out_mid)
    assert out_low["is_anomaly"] is True
    assert out_low["z_score"] < -2.0
    assert out_mid["is_anomaly"] is False
    return 0


if __name__ == "__main__":
    raise SystemExit(_smoke())
