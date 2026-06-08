"""T7 — MAB alert recommender (UCB1, wine asset reuse).

본 도구는 `src.mab.policies.UCB1` (Phase 4 에서 직접 구현한 numpy MAB) 을
그대로 가져다 쓴다 — wine-mab → personal-mab asset reuse 가 핵심.

6 arms: silence, gait_warning, location_swap_suggest, audio_warning,
hydration_reminder, walk_more. context_features 가 "특정 신호 강함" 을 들고 오면
해당 arm 의 UCB 점수에 가산점 (rule-based prior) 을 주어 cold-start 를 완화.
"""

from __future__ import annotations

import numpy as np

from src.mab.policies import UCB1

ARMS: tuple[str, ...] = (
    "silence",
    "gait_warning",
    "location_swap_suggest",
    "audio_warning",
    "hydration_reminder",
    "walk_more",
)


def _context_boost(context: dict) -> np.ndarray:
    """context 가 시그널을 강하게 들고 오면 해당 arm 에 prior bonus."""
    bonus = np.zeros(len(ARMS), dtype=np.float64)
    # gait 위험
    if float(context.get("gait_z", 0.0)) > 1.5:
        bonus[ARMS.index("gait_warning")] += 0.5
    # 위치 비교에서 |d| 가 크고 음의 효과 → swap 권유
    if float(context.get("location_d", 0.0)) < -0.8:
        bonus[ARMS.index("location_swap_suggest")] += 0.4
    # 오디오 노출 verdict == concern
    if str(context.get("audio_verdict", "")) == "concern":
        bonus[ARMS.index("audio_warning")] += 0.5
    # 걸음 추세 큰 하강
    if float(context.get("trend_pct", 0.0)) < -20.0:
        bonus[ARMS.index("walk_more")] += 0.3
    # 평균 dB 가 낮고 휴식 cluster → silence
    if context.get("cluster_label") == "휴식":
        bonus[ARMS.index("silence")] += 0.2
    return bonus


def mab_recommend_alert(
    context: dict,
    mab_state: dict | None = None,
    seed: int = 0,
) -> dict:
    """현재 context 기반으로 6 arms 중 하나를 UCB1 으로 선택.

    Parameters
    ----------
    context : dict
        T1~T6 결과를 요약한 dict. 예: {gait_z, location_d, audio_verdict,
        trend_pct, cluster_label}.
    mab_state : dict | None
        {"N": list[int], "Q": list[float], "t": int} — 누적 통계.
        None 이면 cold-start (전 arm 미선택).
    seed : int
        재현용 RNG seed (UCB1 자체는 deterministic 이지만 미선택 arm 선정에 사용).

    Returns
    -------
    dict
        {chosen_arm, ucb_per_arm, confidence, rationale}
    """
    K = len(ARMS)
    policy = UCB1(K=K, rng=np.random.default_rng(seed))
    if mab_state is not None:
        N = np.asarray(mab_state.get("N", [0] * K), dtype=np.int64)
        Q = np.asarray(mab_state.get("Q", [0.0] * K), dtype=np.float64)
        if N.shape == (K,) and Q.shape == (K,):
            policy.N = N.copy()
            policy.Q = Q.copy()
        t = int(mab_state.get("t", int(N.sum())))
    else:
        t = 0

    # UCB1 raw score (미탐험 처리는 select 가 담당하지만 여기서는 점수도 노출)
    with np.errstate(divide="ignore", invalid="ignore"):
        raw_ucb = policy.Q + policy.c * np.sqrt(np.log(max(t, 1) + 1) / np.maximum(policy.N, 1))
    raw_ucb = np.where(policy.N == 0, np.inf, raw_ucb)
    boost = _context_boost(context)
    final = np.where(np.isinf(raw_ucb), 1e6 + boost, raw_ucb + boost)  # 미탐험에도 boost 반영
    chosen = int(np.argmax(final))

    # confidence: top-2 gap 정규화
    sorted_final = np.sort(final)[::-1]
    gap = float(sorted_final[0] - sorted_final[1]) if K >= 2 else 0.0
    confidence = float(min(max(gap / (abs(sorted_final[0]) + 1e-6), 0.0), 1.0))

    rationale_bits: list[str] = []
    if boost[chosen] > 0:
        rationale_bits.append(f"context_boost={boost[chosen]:.2f}")
    if policy.N[chosen] == 0:
        rationale_bits.append("cold_start_arm")
    rationale_bits.append(f"raw_ucb={float(raw_ucb[chosen]) if not np.isinf(raw_ucb[chosen]) else 'inf'}")

    return {
        "chosen_arm": ARMS[chosen],
        "ucb_per_arm": {ARMS[i]: float(final[i]) for i in range(K)},
        "confidence": confidence,
        "rationale": "; ".join(rationale_bits),
    }


def _smoke() -> int:
    # cold-start + context 가 gait_warning 을 강하게 가리킬 때
    ctx = {
        "gait_z": 2.1,
        "location_d": -1.12,
        "audio_verdict": "safe",
        "trend_pct": -35.0,
        "cluster_label": "유산소",
    }
    out = mab_recommend_alert(ctx, mab_state=None, seed=0)
    print("[T7 smoke cold]", out["chosen_arm"], out["rationale"])
    # 워밍업된 상태 — N>0 모두, Q 가 audio_warning 우세
    state = {
        "N": [5, 5, 5, 5, 5, 5],
        "Q": [0.1, 0.2, 0.3, 0.7, 0.2, 0.4],
        "t": 30,
    }
    ctx2 = {"audio_verdict": "concern", "gait_z": 0.2}
    out2 = mab_recommend_alert(ctx2, mab_state=state, seed=1)
    print("[T7 smoke warm]", out2["chosen_arm"], out2["rationale"])
    assert out2["chosen_arm"] == "audio_warning"
    return 0


if __name__ == "__main__":
    raise SystemExit(_smoke())
