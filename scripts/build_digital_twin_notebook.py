"""Build the comprehensive digital-twin final-report notebook.

산출물: notebooks/digital_twin_report.ipynb
- 자기완결 (base64-embedded figures, no external file deps)
- 35~40 cells (markdown + code), 강의 §1~§4 + 7-tool + LLM orchestrator 구조
- 와인 트랙은 §8 보조 자산으로 잔존 (T7 UCB1 차용 출처 disclosure)

실행:
    uv run python scripts/build_digital_twin_notebook.py
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

ROOT = Path(__file__).resolve().parent.parent


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def read_source(rel_path: str) -> str:
    """Read a source file relative to project root."""
    p = ROOT / rel_path
    return p.read_text(encoding="utf-8")


def fig_embed(rel_path: str, alt: str, max_width: int = 900) -> str:
    """Return a markdown <img> tag with base64-embedded PNG."""
    p = ROOT / rel_path
    raw = p.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    return (
        f'<img alt="{alt}" '
        f'src="data:image/png;base64,{b64}" '
        f'style="max-width:{max_width}px;width:100%;height:auto;" />'
    )


def md(text: str) -> nbformat.NotebookNode:
    return new_markdown_cell(text)


def code(src: str) -> nbformat.NotebookNode:
    return new_code_cell(src)


# ----------------------------------------------------------------------
# Assemble cells
# ----------------------------------------------------------------------
cells: list[nbformat.NotebookNode] = []

# ===== 헤더 + 메타 =====
cells.append(
    md(
        """# 나의 디지털 트윈 — 기말 보고서

**과목:** 빅데이터 컴퓨팅 (2026-1)
**발표자:** 20200572 엄상호
**제출일:** 2026-06-24
**스택:** Python 3.12 · numpy · scipy.stats · matplotlib · anthropic SDK (claude-opus-4-7 tool_use API)
**원칙:** ML primitives (K-means / MAB UCB1 / LinearRegression slope) 는 numpy 로 직접 구현 — sklearn `LinearRegression` 만 강의 §3 정합을 위해 추세 slope 계산에 한정 사용.

---

> **한 줄 스파인:** *AI 시대에 나만의 특수성과 능력을 함께 고민해 줄 디지털 트윈을, 내 6년치 행동 데이터 위에서 7개의 데이터 사이언스 도구를 LLM이 취사선택해 호출하는 구조로 시작해 봅니다.*
"""
    )
)

cells.append(
    md(
        """## 목차

1. [§1 필수항목 — 차용 vs 신규 / 데이터 수집·정제](#section-1)
2. [§2 데이터 — Apple Health · Timeline · GPX](#section-2)
3. [§3 방법론 — 강의 §1~§4 + Anthropic SDK 매핑](#section-3)
4. [§4 T1~T7 도구 구현 (7 cells)](#section-4)
5. [§5 LLM 오케스트레이터 + Hero S1 demo](#section-5)
6. [§6 발견 — V-curve · Paris vs Seoul · Hero S1 · 디지털 트윈 vision](#section-6)
7. [§7 평가 기준 + N=1 한계](#section-7)
8. [§8 와인 트랙 — 보조 자산 (T7 UCB1 출처)](#section-8)
9. [§9 부록 — pivot 다이어그램 / ADR / 감사](#section-9)
"""
    )
)

cells.append(
    md(
        """## 프로젝트 동기 — *데이터 과학자 = 세상을 보는 안경*

데이터 과학을 공부한다는 건 *세상을 보는 새로운 안경*을 하나 더 쓰는 일이라고 생각합니다.
저는 그중에서도 **모델링** — 현실을 수식과 알고리즘으로 다시 쓰는 일에 관심이 있고,
그 안경을 *어디에 가장 먼저 들이대고 싶은가* 자문했을 때 답은 **나 자신**이었습니다.
남의 데이터로 모델을 돌리기 전에, 나부터 분석하고 싶었습니다.

### 두 트랙 회고

| Track | Status | 자산 |
|---|---|---|
| **wine-mab** (한국 와인 시장 합리적 취향 탐색) | retired (소스 차용) | numpy UCB1 구현 → T7 로 흡수 |
| **personal-llm-orchestrator** (디지털 트윈) | **본 기말** | T1~T7 + Anthropic tool_use 루프 |

### Pivot 3 사유 (wine → personal)

1. **모티베이션 정합** — *나부터 분석하고 싶다* 라는 동기와 personal-data가 정확히 일치 (와인은 *남의 시장*).
2. **데이터의 진정성** — 6년치 자기 행동 데이터 (N=1) 는 *실재하는 변동성*을 가지며 발표자가 직접 검증 가능.
3. **강의 기법 1:1 매핑** — 개인 데이터 트랙은 강의 §1~§4 의 7 기법을 그대로 7개 도구로 wrap. 와인은 단일 MAB 알고리즘에 머묾.

(ADR-010 갱신 + ADR-011 신설 으로 결정 박제. 자세한 회고는 §9 부록.)
"""
    )
)

# ===== §1 필수항목 =====
cells.append(
    md(
        """<a id="section-1"></a>
## §1 필수항목

### 필수항목 1 — 차용 vs 본 기말 신규 (prior-work disclosure)

본 발표는 학기 중 wine-mab 트랙에서 만든 자산 중 **단 하나** — `src/mab/policies.py::UCB1` numpy 구현 — 만을 차용해 T7 (`mab_recommend_alert`) 내부에서 알림 종류 추천에 재사용했습니다. 그 외 모든 자산 (T1~T6, orchestrator, 5 데이터 소스 ingestion, 발견 1/2 figures) 은 **본 기말에서 신규 작성**입니다.

| 자산 | 출처 | 본 기말 역할 |
|---|---|---|
| UCB1 알고리즘 (numpy) | wine-mab `src/mab/policies.py` | T7 알림 arm 선택 |
| T1~T6 도구 6개 | **신규** (본 기말) | 강의 §1~§4 기법 1:1 wrap |
| LLM 오케스트레이터 (Anthropic tool_use) | **신규** (본 기말) | 7 도구 취사선택 + 합성 |
| Apple Health export ingestion (216 MB XML) | **신규** | T1·T3·T4 입력 |
| Google Timeline JSON ingestion (6년치) | **신규** | T2 입력 (location_id) |
| GPX 트랙 (Strava/Garmin) | **신규** | T1 cross-check |
| Hero S1 demo + 평가 기준 | **신규** | RQ operational definition |
| F02~F09 figures 8장 | **신규** | 발견 시각화 |

### 필수항목 2 — 데이터 수집 + raw → processed 정제 5단계

- **Source 1 — Apple Health export.zip** (216 MB, 2020-09 ~ 2026-05) → `data/raw/apple_health/export.xml`
- **Source 2 — Google Timeline JSON** (6년치, 위치/모달리티) → `data/raw/timeline/Records.json`
- **Source 3 — Strava/Garmin GPX 트랙** (cross-check 용) → `data/raw/gpx/*.gpx`
- **Source 4 — Nemotron-Personas-Korea** (HuggingFace, prior wine-track 잔존) → `data/raw/hf/`
- **Source 5 — 수동 인생 chapter 라벨** (7개 굵직한 사건) → `data/raw/timeline_labels.csv`

**정제 5단계:**
1. **Parse** — XML/JSON → pandas DataFrame (long format)
2. **Window slice** — baseline (2020-09 ~ 2021-12) vs recent (rolling 14d)
3. **Aggregate** — daily steps / weekday-normalized speed / hourly audio dB / location_id × day count
4. **Z-score** — gait 4 메트릭은 baseline_mean/sd 로 z-score 변환
5. **Persist** — `data/processed/{phase}/{slice}.parquet` 으로 정제본 분리 (raw는 손상 금지)
"""
    )
)

cells.append(
    md(
        """### 필수항목 충족 체크리스트

- [x] **(1) 차용 vs 신규 disclosure** — 위 표 참고. 차용 = UCB1 1개, 신규 = T1~T6 + orchestrator + 데이터 ingestion + figures.
- [x] **(2) 데이터 수집 + raw 정제** — 5 source × 5 단계 정제 파이프라인 (§9 부록의 F05 다이어그램 참고).
- [x] **(3) 강의 §1~§4 기법 활용** — T1 Pearson r / T2 Welch t / T3 z-score / T4 ANOVA / T5 weekday-z / T6 K-means / T7 UCB1 + LinearRegression slope.
- [x] **(4) 직접 구현 원칙** — K-means / MAB / slope-break 모두 numpy. sklearn은 단일 `LinearRegression` (T1 slope 계산) 만 사용.
- [x] **(5) 재현성** — 모든 figure 는 `scripts/personal/build_fig_*.py` 로 재생산 가능. 본 노트북은 figure 를 base64-embed 하여 자기완결.
"""
    )
)

# ===== §2 데이터 =====
cells.append(
    md(
        """<a id="section-2"></a>
## §2 데이터 — 6년치 행동 데이터

### 데이터 소스 요약

| Source | Format | 기간 | 크기 | 주요 필드 |
|---|---|---|---|---|
| Apple Health export | XML (gzip) | 2020-09 ~ 2026-05 | 216 MB | StepCount, WalkingSpeed, StepLength, WalkingAsymmetryPercentage, WalkingDoubleSupportPercentage, EnvironmentalAudioExposure |
| Google Timeline | JSON | 2019-12 ~ 2026-05 | ~40 MB | timestamp, latitudeE7/longitudeE7, activity (WALKING/IN_VEHICLE/...) |
| Strava/Garmin GPX | XML | sparse (운동 세션) | ~15 MB | trkpt lat/lon/time/ele |
| Nemotron-Personas-Korea (잔존) | parquet | static | ~80 MB | persona 텍스트 (wine 트랙 차용) |
| 인생 chapter 라벨 | CSV | 7 events | <1 KB | date, label, chapter |

**baseline window:** 2020-09 ~ 2021-12 (iOS 14 gait 센서 도입 직후 안정기) — T3 z-score 의 기준점.

**recent window:** rolling 14 일 (도구 호출 시점 기준 꼬리).
"""
    )
)

cells.append(
    md(
        f"""### F03 — 내 인생 굵직한 타임라인 (6년치 chapter 마커)

학부 입학(2019-03) → iOS 14 gait 센서 도입(2020-09, **baseline 시작**) →
baseline 종료(2021-10) → 군 입대(2021-11-15) → 전역(2023-05-14) → 무릎 부상(2023-10) → ACL 수술(2024-01) →
프랑스 교환학생 출국(2024-12, **Paris window 시작**) → 한국 귀국(2025-06, Seoul_rec 재진입).

> 내 데이터는 *그냥 시계열*이 아니라 *인생 chapter 가 박힌 시계열*. 발견 1에서 이 자전적 chapter 들이 진짜 데이터 분기점인지를 K-means 가 검증한다.

{fig_embed("results/personal/figures/F03_personal_timeline.png", "F03 personal timeline")}
"""
    )
)

# ===== §3 방법론 =====
cells.append(
    md(
        """<a id="section-3"></a>
## §3 방법론 — 강의 §1~§4 + Anthropic SDK → 7 도구 매핑

| 도구 | 강의 기법 | API signature 핵심 | 역할 |
|---|---|---|---|
| **T1** `get_recent_step_trend` | §3 Pearson r + sklearn LinearRegression slope | `(daily_steps, window_days=14, baseline_mean=6445)` | 추세 방향성 + 평균 대비 변화율 |
| **T2** `compare_location_activity` | §3 Welch's t-test, Cohen d | `(loc_a_steps, loc_b_steps, names)` | 두 장소 활동량 차이 검정 |
| **T3** `check_gait_quality` | §3 z-score + bad-direction map | `(window_metrics, baseline_means, baseline_sds)` | 보행 4 메트릭 (속도/보폭/비대칭/양발지지) 이상 감지 |
| **T4** `audio_exposure_summary` | §3 ANOVA (one-way) | `(audio_db_records, n_minutes=60, mode_groups)` | 청각 노출 평균 dB + 모달리티별 차이 |
| **T5** `detect_step_anomaly` | §3 weekday-z (peer 분포 대비) | `(today_steps, peer_steps)` | 오늘 걸음의 이상치 z-score |
| **T6** `cluster_today_archetype` | §4 K-means + cosine similarity | `(today_vector, fitted_centroids, labels, past_vectors)` | 오늘의 라이프스타일 archetype 분류 |
| **T7** `mab_recommend_alert` | §4 MAB UCB1 (numpy 직접 구현) | `(context, mab_state=None, seed=0)` | 푸시 알림 종류 추천 (arm = 알림 타입) |

### LLM 오케스트레이터 (Anthropic tool_use 루프)

```
user_query OR proactive_trigger
        │
        ▼
  [Claude opus-4-7] ── plan ──▶ tool_use(T1, T2, ...) 병렬
        ▲                              │
        │                              ▼
        └──────── tool_result ◀── 도구 실행 (numpy/scipy)
        │
        ▼
   한국어 1~3문장 합성 (system prompt: 도구 수치만 인용, 환각 금지)
```

**책임 분담:** 통계는 도구가, *선택과 표현*은 LLM이.
"""
    )
)

# ===== §4 T1~T7 (7 code cells) =====
cells.append(
    md(
        """<a id="section-4"></a>
## §4 T1~T7 도구 구현

각 도구는 자기완결적 함수 1개. numpy + scipy.stats 만. LLM 은 도구 결과 dict 의 필드만 인용.

### T1 — `get_recent_step_trend` (Pearson r + slope, 88 lines)
"""
    )
)
cells.append(code(read_source("src/personal/tools/T1_step_trend.py")))

cells.append(
    md(
        """### T2 — `compare_location_activity` (Welch t + Cohen d, 98 lines)"""
    )
)
cells.append(code(read_source("src/personal/tools/T2_compare_location.py")))

cells.append(
    md(
        """### T3 — `check_gait_quality` (z-score + bad-direction, 103 lines)

> 4 메트릭 (walking_speed / step_length / asymmetry / double_support) 의 bad-direction 매핑이 load-bearing 이라 타깃 40-80 줄을 약간 초과. 강의 §3 정합을 우선.
"""
    )
)
cells.append(code(read_source("src/personal/tools/T3_gait_quality.py")))

cells.append(
    md("""### T4 — `audio_exposure_summary` (ANOVA, 98 lines)""")
)
cells.append(code(read_source("src/personal/tools/T4_audio_summary.py")))

cells.append(
    md(
        """### T5 — `detect_step_anomaly` (weekday-z, 67 lines)"""
    )
)
cells.append(code(read_source("src/personal/tools/T5_anomaly.py")))

cells.append(
    md(
        """### T6 — `cluster_today_archetype` (K-means + cosine, 97 lines)"""
    )
)
cells.append(code(read_source("src/personal/tools/T6_archetype.py")))

cells.append(
    md(
        """### T7 — `mab_recommend_alert` (UCB1 + context_boost, 136 lines)

> wine-mab 트랙의 `src/mab/policies.py::UCB1` 을 차용해 알림 arm 선택에 재사용 (필수항목 1). context_boost 매트릭스가 강의 §4 MAB exploration/exploitation 데모로 load-bearing 이라 타깃 40-80 줄을 초과.
"""
    )
)
cells.append(code(read_source("src/personal/tools/T7_mab_alert.py")))

# ===== §5 오케스트레이터 + Hero demo =====
cells.append(
    md(
        """<a id="section-5"></a>
## §5 LLM 오케스트레이터 + Hero S1 demo

### `PersonalAgent` — Anthropic tool_use 루프 (143 lines)

mock=True 가 기본값 — `gym_A` trigger 에 대한 canned tool_use 시퀀스로 노트북 재현성 보장. 실제 Anthropic API 호출은 `_live_run` 에 pseudocode 로 남겨 둠 (API key 누설 방지).
"""
    )
)
cells.append(code(read_source("src/personal/agent/orchestrator.py")))

cells.append(
    md(
        """### Hero S1 demo run — 단일 도구 vs 도구 조합

> trigger: `location_id == "gym_A"` (헬스장 A 활동량 -39.9%)
> baseline run = T1 단독 → *"운동량 줄음, 다시 늘려라"* (false positive — 동네 산책은 정상)
> full run = T1 + T2 + T3 + T7 → *"한쪽 다리 보행 패턴 — 무릎/발목 확인 권유"* (교정됨)
"""
    )
)
cells.append(code(read_source("src/personal/hero_s1_demo.py")))

# ===== §6 발견 =====
cells.append(
    md(
        f"""<a id="section-6"></a>
## §6 발견

### 발견 1 — V-curve "양은 늦게, 질은 먼저" (Pearson r=+0.638)

**양** = 일별 걸음 수 (7일 이동평균). **질** = walking_speed (보행속도, m/s).

V-curve 관측 — 2020-09 baseline 이후 **질 (walking_speed)** 은 **2022 봄 (24개월)** 후 회복 시작했지만 **양 (steps)** 은 더 늦게 따라옴. 두 시계열의 Pearson r = **+0.638** (p < 0.001) — 질이 양을 *선행* 한다는 가설과 정합.

> **회복의 신호는 양이 아니라 질이 먼저 보낸다** — 24개월 만의 walking_speed 회복이 8개월 후의 steps 회복을 *예고*.

{fig_embed("results/personal/figures/F06_v_curve_v2.png", "F06 V-curve: 양 vs 질")}
"""
    )
)

cells.append(
    md(
        f"""### 발견 2 — Paris vs Seoul (Welch t-test, Cohen d = +0.43)

**자연 실험:** 2024-12 Sorbonne 교환학생 → 2025-06-29 귀국. 도시 modality (지하철·도보 비중) 가 다른 두 baseline 을 비교.

Welch's t-test: t = 4.21, p < 0.0001, **Cohen d = +0.43** (Paris > Seoul, +2,118 steps/day).

> 도시는 신체활동의 *자연적 push factor* — Paris (조밀한 지하철 + 도보 friendly) vs Seoul (자가용/광역버스 의존) 의 *환경 자체*가 일별 걸음에 0.43σ 만큼 차이를 만든다.

{fig_embed("results/personal/figures/F07_paris_seoul.png", "F07 Paris vs Seoul")}
"""
    )
)

cells.append(
    md(
        f"""### 발견 3 — Hero S1 부상 조기 감지 (single-tool vs multi-tool 정성 비교)

**baseline run (T1 only):**
> trend = -39.9% (gym_A 위치) → LLM 응답: *"운동량이 줄었어요, 다시 늘려보세요"* (**false positive**)

**full run (T1 + T2 + T3 + T7):**
> T1 trend = -39.9% / T2 d = -1.12 (gym_A vs home) / T3 asymmetry_z = +1.73, double_support_z = +1.52 / T7 arm = `safety_check`
> LLM 응답: *"운동량 감소가 아니라 한쪽 다리 보행 패턴 — 무릎/발목 확인 권유"* (**교정됨**)

이게 우리 RQ 의 *operational definition* — **도구 조합이 single-tool false positive 를 정성적으로 교정**.

{fig_embed("results/personal/figures/F08_hero_demo_v2.png", "F08 Hero S1 demo")}
"""
    )
)

cells.append(
    md(
        f"""### 발견 4 — 디지털 트윈 vision

AI 시대가 본격적으로 열리고 취업을 앞두면서, *나만의 특수성과 능력*이 무엇인지를 진지하게 고민하게 됐습니다. 오늘 보여드린 **7개의 도구 + LLM 오케스트레이터** 는, 그 고민을 *함께* 해 줄 **디지털 트윈**의 첫 부팅 단계입니다.

학교 프로젝트로 끝나는 게 아니라, 6년치 행동 데이터 위에서 천천히 자라나서 **내가 모르는 내 패턴**을 먼저 짚어 주는 비서로 키우는 게 다음 단계입니다.

> *여러분도 자기 데이터로 한번 시도해 보세요 — 5 source · 7 tool · 1 LLM 이면 충분히 시작됩니다.*

{fig_embed("results/personal/figures/F09_digital_twin.png", "F09 디지털 트윈 vision")}
"""
    )
)

# ===== §7 평가 기준 + 한계 =====
cells.append(
    md(
        """<a id="section-7"></a>
## §7 평가 기준 + N=1 한계 (정직 선언)

### Research Question (rev4)

> *"내 6년치 행동 데이터에서, LLM 이 적절한 도구 조합을 통해 단일 도구 호출만으로는 발생하는 false positive 를 줄일 수 있는가?"*

### 도구 선택 평가 기준 (operational definition)

| 항목 | 정의 |
|---|---|
| **Criterion** | 단일 도구 호출 시 발생하는 false positive 를, 도구 조합 호출이 줄이는가 |
| **baseline run** | Hero S1 trigger 에 대해 T1 단독 호출만 강제 |
| **full run** | 동일 trigger 에 T1+T2+T3+T7 조합 호출 |
| **비교 단위** | 두 LLM 응답의 *정성적 차이* (1 도구 결론 vs 4 도구 결론) |
| **합격 기준** | full run 응답이 baseline run 의 false positive 를 *교정* |

### N=1 한계 — 정직 인정

- **N=1** — 발표자 단일 사례, 시나리오 1개 (Hero S1). 통계적 false positive rate 산출 불가.
- **ground truth 라벨 없음** — "운동량 감소"가 false positive 라는 판정은 *발표자 자가 검증*. 의료 진단 아님.
- **정성적 시연 only** — precision / recall / F1 산출 안 함. *qualitative defense* 만 청구.
- **시나리오 1개** — S2 (city rebaseline), S3 (hearing safety) 도 같은 패턴을 보일 것이라 *기대* 하지만 본 발표는 S1 만 시연.

**그럼에도 충분한 평가 기준인가:** 강의 §3 추론통계의 *Type I error* 개념을 LLM-as-tool-orchestrator 맥락으로 가져와, 도구 *선택*이라는 행동의 옳고 그름을 강의 정합 어휘로 평가. N=1 한계는 RQ 안에 *"정성적 차이를 시연한다"* 로 미리 scope 를 좁혀 두었으므로 honest.
"""
    )
)

# ===== §8 와인 트랙 보조 자산 =====
cells.append(
    md(
        """<a id="section-8"></a>
## §8 와인 트랙 — 보조 자산 (T7 UCB1 출처 disclosure)

본 기말은 personal-llm-orchestrator 트랙이지만, 학기 중반까지 진행한 **wine-mab 트랙**에서 만든 **numpy MAB 구현**이 T7 에서 살아남았습니다. 여기서는 그 출처를 투명하게 공개하고, wine-mab 트랙의 핵심 자산 (3 모듈 + 6 figures + 3 analysis scripts) 을 보조 자산으로 첨부합니다.

> **본 노트북의 평가 대상은 §4~§7 (personal 트랙) 입니다.** §8 은 차용 자산의 *출처 disclosure* 와 강의 §4 MAB 직접 구현 증빙용.
"""
    )
)

cells.append(
    md(
        """### `src/mab/policies.py` — Epsilon-Greedy / UCB1 / Thompson Sampling (numpy, 229 lines)"""
    )
)
cells.append(code(read_source("src/mab/policies.py")))

cells.append(md("""### `src/mab/reward.py` — Reward function (223 lines)"""))
cells.append(code(read_source("src/mab/reward.py")))

cells.append(
    md("""### `src/mab/simulate.py` — 시뮬레이션 루프 (414 lines)""")
)
cells.append(code(read_source("src/mab/simulate.py")))

cells.append(
    md(
        f"""### 와인 EDA figures — H/S split · H1/H2 robustness · Champagne mechanism

{fig_embed("results/figures/eda/07_hs_split.png", "07 H/S split", max_width=820)}

{fig_embed("results/figures/eda/08_h1h2_robustness.png", "08 H1/H2 robustness", max_width=820)}

{fig_embed("results/figures/eda/12_champagne_mechanism.png", "12 Champagne mechanism", max_width=820)}
"""
    )
)

cells.append(
    md(
        f"""### 와인 MAB figures — Regret curves · Pull heatmap · UCB1 c-sweep

{fig_embed("results/figures/mab/09_regret_curves.png", "09 MAB regret curves", max_width=820)}

{fig_embed("results/figures/mab/10_pull_heatmap.png", "10 pull heatmap", max_width=820)}

{fig_embed("results/figures/mab/11_ucb_csweep.png", "11 UCB1 c-sweep", max_width=820)}
"""
    )
)

cells.append(
    md(
        """### `scripts/analyze_robustness.py` — H1/H2 robustness 요약 (245 lines)"""
    )
)
cells.append(code(read_source("scripts/analyze_robustness.py")))

cells.append(
    md(
        """### `scripts/analyze_champagne.py` — Champagne mechanism 분해 (360 lines)"""
    )
)
cells.append(code(read_source("scripts/analyze_champagne.py")))

# ===== §9 부록 =====
cells.append(
    md(
        f"""<a id="section-9"></a>
## §9 부록 — pivot 다이어그램 / ADR / 감사

### F02 / F04 / F05 — two-track / prior vs new / data pipeline

{fig_embed("results/personal/figures/F02_two_track.png", "F02 two track", max_width=820)}

{fig_embed("results/personal/figures/F04_prior_vs_new.png", "F04 prior vs new", max_width=820)}

{fig_embed("results/personal/figures/F05_data_pipeline.png", "F05 data pipeline", max_width=820)}
"""
    )
)

cells.append(
    md(
        """### ADR 요약 — 본 기말의 두 개 결정

**ADR-009 — wine-mab 트랙 retirement + 자산 차용 범위 한정**
- *결정:* wine-mab 트랙은 발표 메인 트랙에서 제외. 단 `src/mab/policies.py::UCB1` 구현만 T7 으로 차용 (강의 §4 MAB 직접 구현 증빙).
- *사유:* 동기 정합 (나부터 분석) + 데이터 진정성 (6년치 자기) + 강의 1:1 매핑 (7 도구 wrap).
- *대안 기각:* 두 트랙 모두 발표 시도 → 6분 budget 초과 / 메시지 분산.

**ADR-010 — Persona Translation Layer 제외**
- *결정:* Nemotron-Personas-Korea → wine catalog 매핑 (방법 B, LLM) 은 personal 트랙으로 pivot 하면서 제외.
- *사유:* personal 트랙의 LLM 사용 ()`tool_use` 오케스트레이터) 이 강의 평가 기준에 더 정합.

**ADR-011 — Anthropic tool_use 루프 채택**
- *결정:* LLM 은 `claude-opus-4-7`, tool_use API. mock=True 가 기본값 (노트북 재현성).
- *사유:* 발표 시점 가장 강력한 도구 호출 정확도 + 본 발표의 핵심 contribution (도구 *선택*) 을 평가 가능한 형태로 분리.
"""
    )
)

cells.append(
    md(
        """### 다시 한 번 — 차용 vs 신규 / 감사

| 자산 | 출처 | 본 기말 역할 |
|---|---|---|
| `UCB1` numpy 구현 | wine-mab `src/mab/policies.py` (학기 중반 작성) | T7 알림 arm 선택 |
| **그 외 모든 자산** | **본 기말 신규** | T1~T6 / orchestrator / 5 데이터 ingestion / Hero S1 / F02~F09 |

### 감사 인사

- **강의 §1~§4** 의 7 기법이 7개 도구로 1:1 wrap 되는 구조 덕분에 본 발표의 spine 이 성립했습니다.
- 학기 중반 wine-mab 트랙에서 만든 numpy MAB 코드가 retirement 후에도 T7 으로 *살아남은* 게 본 발표의 *재사용성 사례* 입니다 — 강의 평가 기준 (직접 구현) 을 우회하지 않고 *재배치* 한 사례.
- N=1 한계는 정직하게 인정하되, RQ 안에 *"정성적 차이를 시연한다"* 로 미리 scope 를 박아 honest evaluation 을 청구합니다.

---

**제출:** 2026-06-24
**문의:** 20200572 엄상호 / sam9787@naver.com
"""
    )
)


# ----------------------------------------------------------------------
# Write notebook
# ----------------------------------------------------------------------
nb = new_notebook()
nb["cells"] = cells
nb["metadata"] = {
    "kernelspec": {
        "display_name": "Python 3 (uv .venv)",
        "language": "python",
        "name": "python3",
    },
    "language_info": {"name": "python", "version": "3.12"},
    "authors": [
        {"name": "20200572 엄상호", "email": "sam9787@naver.com"}
    ],
    "title": "나의 디지털 트윈 — 기말 보고서",
}

out_path = ROOT / "notebooks" / "digital_twin_report.ipynb"
out_path.parent.mkdir(parents=True, exist_ok=True)
nbformat.write(nb, out_path)

size_kb = os.path.getsize(out_path) // 1024
n_total = len(cells)
n_code = sum(1 for c in cells if c.get("cell_type") == "code")
n_md = n_total - n_code
print(f"[OK] wrote {out_path}")
print(f"     cells: total={n_total} markdown={n_md} code={n_code}")
print(f"     size:  {size_kb} KB")
