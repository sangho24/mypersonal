"""Hero S1 demo — '헬스장 A 비교' 시나리오.

T1 (단일 도구) baseline vs. T1+T2+T3+T7 (full multi-tool agent) 의 응답 품질 차이를
1 회 실행으로 시연. 모든 데이터는 HARDCODED (재현성).

실행:
    uv run python -m src.personal.hero_s1_demo
"""

from __future__ import annotations

import numpy as np

from src.personal.agent.orchestrator import PersonalAgent
from src.personal.tools.T1_step_trend import get_recent_step_trend

# ----------------------------------------------------------------------
# Hardcoded Hero S1 data (matches docs/NARRATIVE_PLAN.md figures)
# ----------------------------------------------------------------------

BASELINE_MEAN = 6445.0

# 최근 14일 일별 걸음 — 헬스장 A 다닌 기간, 평소 대비 60% 수준으로 하락
_RNG = np.random.default_rng(42)
_RECENT_TREND = np.linspace(4500, 3500, 14) + _RNG.normal(0, 250, 14)
DAILY_STEPS: dict[str, int] = {
    f"2026-05-{i + 20:02d}" if i < 12 else f"2026-06-{i - 11:02d}": int(v)
    for i, v in enumerate(_RECENT_TREND)
}

# 두 장소 일별 걸음 비교
LOC_A_STEPS = (
    _RNG.normal(3900, 700, 14).clip(min=1500).astype(int).tolist()
)  # 헬스장 A — 낮음
LOC_B_STEPS = (
    _RNG.normal(6800, 900, 14).clip(min=2500).astype(int).tolist()
)  # 헬스장 B — 정상

# Gait 베이스라인 / 최근 윈도우
GAIT_BASELINE_MEANS = {
    "walking_speed": 1.20,
    "step_length": 0.70,
    "asymmetry": 3.0,
    "double_support": 27.0,
}
GAIT_BASELINE_SDS = {
    "walking_speed": 0.10,
    "step_length": 0.05,
    "asymmetry": 1.0,
    "double_support": 2.0,
}
GAIT_WINDOW = {
    "walking_speed": 1.06,   # 악화: -1.4 SD → 부호반전 +1.4
    "step_length": 0.67,
    "asymmetry": 4.8,        # +1.8 SD
    "double_support": 28.2,
    "n_days": 14,
}


def _print_section(title: str) -> None:
    line = "=" * 72
    print(f"\n{line}\n{title}\n{line}")


def main() -> int:
    # ------------------------------------------------------------------
    # (A) T1-only baseline — naive single-tool agent
    # ------------------------------------------------------------------
    _print_section("[A] BASELINE — T1 single-tool agent")
    t1 = get_recent_step_trend(DAILY_STEPS, window_days=14, baseline_mean=BASELINE_MEAN)
    print(f"T1 output: trend_pct={t1['trend_pct']:.1f}%, r={t1['pearson_r']:.2f}, p={t1['p_value']:.3f}")
    print('Final response (incorrect/insufficient):')
    print('    "운동이 줄었어요."')
    print("→ 어디서 줄었는지, 보행 품질은 어떤지, 무엇을 권할지 알 수 없음.")

    # ------------------------------------------------------------------
    # (B) Multi-tool agent — Hero S1 full pipeline
    # ------------------------------------------------------------------
    _print_section("[B] AGENT — PersonalAgent (T1+T2+T3+T7)")
    agent = PersonalAgent(api_key=None, mock=True)
    trigger = {
        "location_id": "gym_A",
        "today": "2026-06-08",
        "ctx": {
            "daily_steps": DAILY_STEPS,
            "window_days": 14,
            "baseline_mean": BASELINE_MEAN,
            "loc_a_steps": LOC_A_STEPS,
            "loc_b_steps": LOC_B_STEPS,
            "loc_a_name": "헬스장 A",
            "loc_b_name": "헬스장 B",
            "gait_window": GAIT_WINDOW,
            "gait_baseline_means": GAIT_BASELINE_MEANS,
            "gait_baseline_sds": GAIT_BASELINE_SDS,
        },
    }
    result = agent.run(trigger)
    for call in result["tool_calls"]:
        out = call["output"]
        head = ", ".join(
            f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}"
            for k, v in list(out.items())[:4]
        )
        print(f"  - {call['tool']:24s} → {head}")
    print("\nFinal response (Korean):")
    # Hero S1 canned message — uses live tool outputs
    t2_out = result["tool_calls"][1]["output"]
    print(
        f'    "헬스장 A에서 막 나오셨네요. 지난 2주 이곳 활동량이 평소의 '
        f'{100 + t1["trend_pct"]:.0f}%까지 떨어졌고'
        f"(d={t2_out['cohens_d']:.2f}, p={t2_out['p_value']:.3f}), "
        f"보행 품질도 평소보다 흔들립니다. 다음번엔 헬스장 B를 시도해 보시겠어요?\""
    )
    print(f"\nMAB chosen arm: {result['mab_chosen_arm']}")
    print(f"Agent final_response (from orchestrator): {result['final_response']}")

    # 결과 sanity
    assert t1["trend_pct"] < -20.0, "Hero S1: trend 가 -20% 이상이어야 시나리오 성립"
    assert t2_out["cohens_d"] < -0.8, "Hero S1: 두 장소 간 effect size 가 large 여야 함"
    assert result["mab_chosen_arm"] in {
        "silence",
        "gait_warning",
        "location_swap_suggest",
        "audio_warning",
        "hydration_reminder",
        "walk_more",
    }
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
