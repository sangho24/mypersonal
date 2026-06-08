"""Figure F10 — Hero S1: 'Paris 효과 어땠어?' 한 trigger 에 도구 단독 vs 조합 답.

Left  : T1 (Pearson trend on steps) 단독 호출 답 — 짧고 한 방향
Right : T1 + T2 (Welch city compare) + T3 (z-score window) + T4 (audio) 조합 답 — 3채널 위상차

본 figure 는 mock 대화가 아니라 *실제 finding2.json 의 도구 출력 + 한국어 해설*.
'LLM이 이렇게 말했다' 같은 attribution 금지 — 인용은 도구 출력 + 사람-작성 paraphrase.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

PROJECT = Path(__file__).parents[2]
DATA_JSON = PROJECT / "results" / "personal" / "finding2.json"
OUT = PROJECT / "results" / "personal" / "figures" / "F10_hero_paris_orchestration.png"

C_BG_SINGLE = "#FBEEDC"
C_BG_COMBO = "#E3F1E8"
C_BAD = "#C44E4E"
C_OK = "#3F8A56"
C_TEXT = "#1A1A1A"


def _korean_font() -> None:
    for n in ("AppleGothic", "NanumGothic", "Malgun Gothic", "Noto Sans CJK KR"):
        if n in {f.name for f in mpl.font_manager.fontManager.ttflist}:
            mpl.rc("font", family=n); break
    mpl.rcParams["axes.unicode_minus"] = False


def _box(ax, x, y, w, h, text, fc, ec=C_TEXT, fs=10, fw="normal", va="center"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02",
                                 fc=fc, ec=ec, lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va=va, fontsize=fs, fontweight=fw,
            color=C_TEXT, wrap=True)


def main() -> None:
    _korean_font()
    j = json.loads(DATA_JSON.read_text())

    fig = plt.figure(figsize=(15, 8.5))
    fig.suptitle("Hero S1 — 동일 trigger '2025-06 Paris 효과 어땠어?' 에 도구 단독 vs 조합 답",
                 fontsize=14, fontweight="bold", y=0.99)

    ax = fig.add_subplot(111)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")

    # Trigger box (위 중앙)
    _box(ax, 32, 90, 36, 6, "Trigger: \"2025-06 Paris 효과 어땠어?\"", fc="#FFFDE7", fs=11, fw="bold")

    # ─── Left column: T1 단독 ───
    _box(ax, 2, 80, 47, 6, "단일 도구 호출 (T1 = steps 평균 비교)", fc="#FFE0B2", fs=11, fw="bold")

    s = j["channel1_activity"]["activity_channels"]["steps"]
    t1_out = (
        f"T1 도구 출력:\n"
        f"  Paris(n={s['n_Paris_days']}d) mean = {s['mean_Paris']:.0f}\n"
        f"  pre-Paris Seoul(n={s['n_PreParisSeoul_days']}d) mean = {s['mean_PreParisSeoul']:.0f}\n"
        f"  Welch t = {s['welch_t']:.2f}, p = {s['p_value']:.4f}, d = {s['cohens_d']:+.2f}\n"
        f"  pct change = {s['pct_change']:+.1f}%"
    )
    _box(ax, 2, 56, 47, 22, t1_out, fc="#FFFFFF", fs=9.5)

    t1_paraphrase = (
        "단일 도구의 답:\n"
        f"\"Paris 에서 일일 걸음수가 {s['pct_change']:+.0f}% 증가. 더 활동적이었음.\""
    )
    _box(ax, 2, 42, 47, 10, t1_paraphrase, fc=C_BG_SINGLE, ec=C_BAD, fs=11)

    t1_issue = (
        "× 단일 채널 false positive 위험:\n"
        "활동량 한 축만 보니 Paris=긍정적 사건으로만 결론.\n"
        "사실은 Paris 체류 중 음악 의존(+3.5배 단조 증가)도 같이 있었고\n"
        "gait remodel 의 진짜 완성은 Paris 가 아니라 귀국 후."
    )
    _box(ax, 2, 18, 47, 20, t1_issue, fc="#FBE9E7", ec=C_BAD, fs=10)

    # ─── Right column: T1+T2+T3+T4 조합 ───
    _box(ax, 51, 80, 47, 6, "도구 조합 호출 (T1 + T2 + T3 + T4)", fc="#C8E6C9", fs=11, fw="bold")

    c2 = j["channel2_audio_monotonic"]
    c3 = j["channel3_post_paris_remodel"]
    g_ws = c3["gait_remodel_vs_baseline"]["walking_speed"]
    g_ds = c3["gait_remodel_vs_baseline"]["double_support"]
    g_sl = c3["gait_remodel_vs_baseline"]["step_length"]

    combo_out = (
        f"채널 1 (T1 활동량, Paris 중):\n"
        f"  steps d={s['cohens_d']:+.2f}, distance d={j['channel1_activity']['activity_channels']['distance_km']['cohens_d']:+.2f}, flights d={j['channel1_activity']['activity_channels']['flights']['cohens_d']:+.2f}\n"
        f"\n"
        f"채널 2 (T4 audio, Paris 중 monotonic):\n"
        f"  12월 {c2['first_month_mean_min']:.0f}분/일 → 6월 {c2['last_month_mean_min']:.0f}분/일 ({c2['ratio_last_vs_first']:.1f}배)\n"
        f"  Spearman ρ = {c2['spearman_rho']:.2f} (단조)\n"
        f"\n"
        f"채널 3 (T2/T3 gait, 귀국 후):\n"
        f"  walking_speed Seoul_rec vs baseline d={g_ws['cohens_d']:+.2f}\n"
        f"  step_length d={g_sl['cohens_d']:+.2f}, double_support d={g_ds['cohens_d']:+.2f}\n"
        f"  explore-day timing (Maps Searched ≥2):\n"
        f"  early {c3['explore_day_timing_in_Paris']['early_third']} / mid {c3['explore_day_timing_in_Paris']['mid_third']} / late {c3['explore_day_timing_in_Paris']['late_third']}"
    )
    _box(ax, 51, 44, 47, 34, combo_out, fc="#FFFFFF", fs=9, va="center")

    combo_paraphrase = (
        "도구 조합의 답:\n"
        "\"Paris 는 활동량을 부과한 trigger 다. 청취 의존도 같이 늘었고\n"
        "gait remodel 의 완성과 능동 탐색은 귀국 후 / Paris 후반에 출현.\n"
        "→ Paris=원료 투입, 귀국 후=가공 완료 의 2단계 구조.\""
    )
    _box(ax, 51, 24, 47, 18, combo_paraphrase, fc=C_BG_COMBO, ec=C_OK, fs=10.5)

    _box(ax, 51, 8, 47, 12,
         "✓ 도구 조합 = false positive 차단:\n"
         "활동량 단일 축으로는 안 보이는 시간 위상 (Paris 중 vs 귀국 후) 과\n"
         "교차 채널 (활동 vs 청취 vs gait) 의 상호작용이 보존됨.",
         fc=C_BG_COMBO, ec=C_OK, fs=10)

    # 아래 한 줄 fine print
    fig.text(0.5, -0.01,
             "도구 출력은 src/personal/finding2_paris_phase.py 실측 결과 그대로. 'Paraphrase' 블록은 사람-작성 (LLM 미사용). "
             "실제 도구 조합 → LLM orchestrator 출력은 src/personal/agent/orchestrator.py 참조.",
             ha="center", fontsize=8, color="#555555", style="italic")

    plt.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"saved → {OUT}")


if __name__ == "__main__":
    main()
