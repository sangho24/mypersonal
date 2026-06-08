# CONTEXT_HANDOFF.md — 데스크톱 Claude 컨텍스트 이어받기

> 본 문서는 `https://github.com/sangho24/mypersonal` clone 후 데스크톱 Claude 가 *프로젝트 상태를 빠르게 복원* 하기 위한 entry-point.
> 작성: 2026-06-08 (rev5.1 + 디자이너 rev7_proposal 검증 완료 시점)
> 작성 도구: Claude Code (Opus 4.7) + Workflow 다중 agent

---

## 1. 한 줄 상태
**디지털 트윈 personal-data 트랙 deck rev5.1 완성** + 디자이너 rev7_proposal pptx 검증 통과 (수치 50/50, 폐기 narrative 0건). 발표 준비 90% 완료. 발표일까지 P1 잔여 4건 + 발화 다이어트만 남음.

---

## 2. 핵심 파일 지도 — 데스크톱에서 가장 먼저 읽을 것

| 우선순위 | 파일 | 역할 |
|---|---|---|
| **1** | [`docs/personal/DECK_PLAN.md`](DECK_PLAN.md) | rev5 changelog § 7 에 폐기/신규/CI 게이트 전체 요약 |
| **2** | [`docs/personal/SLIDES.md`](SLIDES.md) | 본문 11 슬라이드 + Appendix 1 = 발표 narrative source-of-truth |
| **3** | [`docs/personal/REPORT.md`](REPORT.md) | 1인칭 스피커 대본 |
| **4** | [`docs/personal/QA_CARDS.md`](QA_CARDS.md) | Q&A 12카드 (Card 11 = "양/질 narrative 왜 폐기?" 메타) |
| **5** | [`src/personal/anchors.py`](../../src/personal/anchors.py) | 단일 진실 출처 — 모든 모듈 import |
| **6** | [`scripts/personal/sanity_anchors.py`](../../scripts/personal/sanity_anchors.py) | CI 게이트 — 폐기 narrative grep |

---

## 3. 분석 module 지도

```
src/personal/
├── anchors.py                    # SoT (MIL 2021-11-15~2023-05-14, ACL 2024-01, Paris 2024-12~2025-06)
├── data.py                       # parquet loader + zscore_within_baseline
├── finding1_label_vs_data.py     # K-means c0 (numpy 직구현) + Simpson stratification
├── finding2_paris_phase.py       # 3채널 시간 위상 (활동량/청취량/gait remodel)
├── finding3_injury.py            # appendix: Walking Steadiness + asymmetry + Running
├── tools/T1~T7                   # LLM tool_use API 용 wrap
└── agent/orchestrator.py         # plan → 병렬 호출 → 한국어 합성 + 가드

scripts/personal/
├── build_fig_07_label_vs_data.py        # 발견 1 figure
├── build_fig_08_paris_phase.py          # 발견 2 figure
├── build_fig_09_injury_signals.py       # appendix figure
├── build_fig_10_hero_paris_orchestration.py  # Hero figure
├── export_designer_csvs.py              # PowerPoint native chart 용 CSV pack
├── build_deck_pptx.py                   # SLIDES.md → editable .pptx (python-pptx)
└── sanity_anchors.py                    # CI 게이트
```

---

## 4. 발견 인벤토리 (rev5.1)

| 슬라이드 | 발견 | rubric ①②③④ | figure |
|---|---|---|---|
| 7 | K-means c0 학부=군복무 Δ=−1.2pp + 도시 효과 day-type 의존 | ✓✓✓△ | F07_label_vs_data.png |
| 8 | Paris 3채널 시간 위상 (steps +28%/d=.38, distance +35%/d=.44, audio 71→251분 ρ=.86, gait remodel d=.85~1.30) | ✓✓✓✓ | F08_paris_phase.png |
| 10 (Hero) | T1 단독 (+28% 활동적) vs T1+T2+T3+T4 (Paris=원료/귀국후=가공 2단계) | ✓✓✓✓ | F10_hero_paris_orchestration.png |
| 12 (Appendix) | Walking Steadiness 4개월 선행 + asymmetry z=+5.58σ + Running 91일 폭주 | ✓✓✓✓ | F09_injury_signals.png |

---

## 5. 폐기된 narrative (sanity_anchors 가 grep 차단)

- "양 vs 질 회복 분리" / "24개월 vs 8개월" / "양은 늦게, 질은 먼저"
- 폐기 사유: `quality_cross_dt = 2022-12 / quantity_cross_dt = 2024-04` 는 **데이터 계산이 아니라 잘못된 `MIL_END=2022-04`** 에 +8m/+24m 산술 *하드코딩 string*. 정확한 anchor 로 재계산 시 양/질 5채널이 두 회복 이벤트 모두 +1~2m 동조 회복 → 분리 가설 기각.

---

## 6. 외부 산출물 (~/Downloads/)

이 repo 에는 없는 외부 파일 — 데스크톱으로 옮기려면 별도 복사:

| 파일 | 출처 |
|---|---|
| `digital_twin_deck_rev5_python.pptx` | `build_deck_pptx.py` 산출 (1.4 MB, editable shapes) |
| `digital_twin_deck_rev7_proposal.pptx` | **디자이너 산출** (535 KB, native PowerPoint chart). 검증 50/50 통과 → 발표 권장본 |
| `slide8_slide12_csv_pack.zip` | 디자이너 전달용 (이 repo 의 `results/personal/csv_exports/` zip) |
| `apple_health_export/내보내기.xml` | 216 MB raw — finding 모듈 재실행 시 필요 (`/Users/sangho/Downloads/apple_health_export/`) |
| `location-history.json` | Google Timeline raw (4.3 MB) |

---

## 7. 잔여 작업 (Opus 6-lens review P1 — 발표 직전 또는 Q&A 대비)

- **p-value 계산 결함**: `finding1_label_vs_data.py:welch_t_and_d()` 가 normal-approx → `p=0.0000` underflow. `scipy.stats.ttest_ind(equal_var=False)` 로 교체 권고.
- **RQ-rubric 동어반복 방어**: Slide 6 에 "rubric 으로 *기각된* 발견 후보 예시 = 양/질 narrative" 한 줄 추가.
- **K-means c0 matching 자기-순환**: K/seed/imputation sensitivity 1줄 보고.
- **발화시간 +55s 초과**: REPORT.md 압축 (S2/S3/S4/S10/S11 각 −5s + S8 발화 480→320자).

상세는 워크플로우 결과 (`wf_9f975ccb-533` synthesis JSON):
`/private/tmp/claude-501/.../tasks/wdj3rtn4c.output`

---

## 8. 재실행 명령

```bash
# 환경
uv sync

# 모든 finding 재계산
PYTHONPATH=. uv run python -m src.personal.finding1_label_vs_data
PYTHONPATH=. uv run python -m src.personal.finding2_paris_phase
PYTHONPATH=. uv run python -m src.personal.finding3_injury

# 모든 figure 재생성
for n in 07 08 09 10; do
  PYTHONPATH=. uv run python scripts/personal/build_fig_${n}_*.py
done

# 디자이너 CSV pack
PYTHONPATH=. uv run python scripts/personal/export_designer_csvs.py

# editable pptx 빌드
PYTHONPATH=. uv run python scripts/personal/build_deck_pptx.py

# CI 게이트 (폐기 narrative grep)
PYTHONPATH=. uv run python scripts/personal/sanity_anchors.py  # exit 0 통과
```

---

## 9. Git remote 구성

- `origin` = `https://github.com/sangho24/mypersonal.git` (private, personal data 포함)
- `wine-mab-public` = `https://github.com/sangho24/wine-mab-project.git` (public, 차단됨 — push 금지)

데스크톱 clone:
```bash
git clone https://github.com/sangho24/mypersonal.git wine-mab-project
cd wine-mab-project
uv sync
# Apple Health export 만 별도 다운로드 → /Users/sangho/Downloads/apple_health_export/
```

---

## 10. 사용자 확정 사실 (절대 변경 금지)

- 군 복무: **2021-11-15 ~ 2023-05-14**
- 무릎 부상 (전방십자인대): **2023-10** (±2주)
- ACL 수술: **2024-01** 초
- 교환학생 Paris: **2024-12 ~ 2025-06**
- baseline window: **pre-MIL 2020-09 ~ 2021-10**

전부 [`src/personal/anchors.py`](../../src/personal/anchors.py) 의 SoT. 코드/문서 어디든 다른 날짜가 나오면 sanity_anchors 가 catch.
