"""Personal-data LLM orchestrator skeleton.

본 모듈은 Anthropic SDK 를 **mock 모드로만** 시연한다 — notebook 재현성을 위해
default 는 live API call 없음. 실제 호출은 pseudocode 주석으로 보존.

Hero S1 시나리오: trigger.location_id == 'gym_A' 이면 T1+T2+T3+T7 순으로 도구를
호출하는 canned tool_use sequence 를 재생.
"""

from __future__ import annotations

from typing import Any

from src.personal.tools.T1_step_trend import get_recent_step_trend
from src.personal.tools.T2_compare_location import compare_location_activity
from src.personal.tools.T3_gait_quality import check_gait_quality
from src.personal.tools.T7_mab_alert import mab_recommend_alert


class PersonalAgent:
    """LLM-driven Personal Data Agent (mock-first).

    Parameters
    ----------
    api_key : str | None
        Anthropic API key. mock=True 일 때는 무시.
    mock : bool
        True 면 live API call 없이 canned tool_use sequence 재생.
        False + api_key 가 있을 때만 실제 호출 (현재는 NotImplementedError).
    """

    def __init__(self, api_key: str | None = None, mock: bool = True) -> None:
        self.api_key = api_key
        self.mock = mock

    def run(self, trigger: dict[str, Any]) -> dict[str, Any]:
        """Trigger dict 를 받아 tool_use sequence + 최종 응답을 반환.

        trigger 예: {"location_id": "gym_A", "today": "2026-06-08", ...}
        반환: {"tool_calls": [...], "final_response": str, "mab_chosen_arm": str}
        """
        if trigger.get("location_id") == "gym_A":
            return self._hero_s1_canned(trigger)
        if self.mock:
            return {
                "tool_calls": [],
                "final_response": "(mock) 알려진 시나리오가 아닙니다.",
                "mab_chosen_arm": "silence",
            }
        raise NotImplementedError(
            "Live Anthropic call path 는 아직 구현되지 않았습니다. "
            "mock=True 로 실행하세요. (pseudocode 는 _live_run 주석 참조)"
        )

    # ------------------------------------------------------------------
    # Canned playbacks
    # ------------------------------------------------------------------

    def _hero_s1_canned(self, trigger: dict[str, Any]) -> dict[str, Any]:
        """Hero S1 — 헬스장 A 트리거 시 T1→T2→T3→T7 재생."""
        ctx = trigger.get("ctx", {})

        # T1 — recent step trend
        t1_out = get_recent_step_trend(
            ctx.get("daily_steps", {}),
            window_days=ctx.get("window_days", 14),
            baseline_mean=ctx.get("baseline_mean", 6445.0),
        )
        # T2 — gym_A vs gym_B
        t2_out = compare_location_activity(
            ctx.get("loc_a_steps", []),
            ctx.get("loc_b_steps", []),
            ctx.get("loc_a_name", "헬스장 A"),
            ctx.get("loc_b_name", "헬스장 B"),
        )
        # T3 — gait quality
        t3_out = check_gait_quality(
            ctx.get("gait_window", {}),
            ctx.get("gait_baseline_means", {}),
            ctx.get("gait_baseline_sds", {}),
        )
        # T7 — MAB
        mab_ctx = {
            "gait_z": max(
                t3_out.get("walking_speed_z", 0.0) * -1,
                t3_out.get("asymmetry_z", 0.0),
            ),
            "location_d": t2_out.get("cohens_d", 0.0),
            "audio_verdict": "safe",
            "trend_pct": t1_out.get("trend_pct", 0.0),
            "cluster_label": "유산소",
        }
        t7_out = mab_recommend_alert(mab_ctx, mab_state=None, seed=0)

        # canned Korean response
        final = (
            f"헬스장 A에서 막 나오셨네요. 지난 2주 이곳 활동량이 평소의 "
            f"{100 + t1_out['trend_pct']:.0f}%까지 떨어졌고"
            f"(d={t2_out['cohens_d']:.2f}, p={t2_out['p_value']:.3f}), "
            f"보행 품질도 {t3_out['quality_verdict']} 입니다. "
            f"권장 액션: {t7_out['chosen_arm']}"
        )

        return {
            "tool_calls": [
                {"tool": "T1_step_trend", "output": t1_out},
                {"tool": "T2_compare_location", "output": t2_out},
                {"tool": "T3_gait_quality", "output": t3_out},
                {"tool": "T7_mab_alert", "output": t7_out},
            ],
            "final_response": final,
            "mab_chosen_arm": t7_out["chosen_arm"],
        }

    # ------------------------------------------------------------------
    # Live Anthropic call — pseudocode only
    # ------------------------------------------------------------------
    # def _live_run(self, trigger: dict) -> dict:
    #     import anthropic
    #     client = anthropic.Anthropic(api_key=self.api_key)
    #     tools = [
    #         {"name": "T1_step_trend", "description": "...", "input_schema": {...}},
    #         {"name": "T2_compare_location", ...},
    #         ...
    #     ]
    #     messages = [{"role": "user", "content": _format_trigger(trigger)}]
    #     while True:
    #         resp = client.messages.create(
    #             model="claude-opus-4-7",
    #             max_tokens=1024,
    #             tools=tools,
    #             messages=messages,
    #         )
    #         if resp.stop_reason != "tool_use":
    #             break
    #         for block in resp.content:
    #             if block.type == "tool_use":
    #                 result = _dispatch(block.name, block.input)
    #                 messages.append({"role": "assistant", "content": resp.content})
    #                 messages.append({"role": "user", "content": [
    #                     {"type": "tool_result", "tool_use_id": block.id, "content": str(result)}
    #                 ]})
    #     return {"final_response": resp.content[0].text, ...}
