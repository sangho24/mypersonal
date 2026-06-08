# DECK_PLAN.md — Personal-Data Final Project Deck (rev5, 2026-06-08)

> 빅데이터컴퓨팅 기말 발표 (5분 + Q&A 1분). 발표자: 20200572 엄상호.
> **rev5 변경 (2026-06-08)**: 양/질 narrative 전면 폐기 (코드 하드코딩 산물로 데이터 재계산에서 기각됨), hypothesis-free 데이터 탐색 (workflow `wf_8eb0cb02-770` 진단 + `wf_ff0ce1c2-2a8` 발굴 + 본 에이전트 finding 모듈 재계산) 으로 새 발견 2개 + Hero 1개 + appendix 1개 채택. 4항목 rubric (통계 분리도 / 단일지표 모순성 / 채널 교차 / 행동 가능) 명문화. mock·하드코딩 잔재 `rm` 완료, `sanity_anchors.py` 가 CI 게이트.

---

## 1. Final Spine (rev5)

### 1.1 한 줄 발표 thesis
> **"자전적 라벨이 데이터를 자르지 않는다 — 단일 도구 직관으로는 보이지 않는 유의미한 패턴을 다축 도구 조합 + LLM 오케스트레이션으로 발견할 수 있는가?"**

### 1.2 Research Question
> 내 6년치 개인 행동 로그 (Apple Health 216 MB + Google Maps Timeline JSON) 에서, **단일 지표 직관만으로는 보이지 않는 유의미한 패턴**을 발견할 수 있는가?

**HOW (RQ 본문에서 분리)**: 7 도구 (T1 Pearson · T2 Welch · T3 baseline z-score · T4 ANOVA · T5 weekday-z · T6 K-means · T7 UCB1) 를 Anthropic `tool_use` API 위에서 LLM 이 상황 따라 조합 호출.

### 1.3 "유의미함" 의 조작적 정의 — 4 항목 rubric
- ① **통계 분리도**: p + effect size (Cohen's d 또는 z) + sample size n 세 숫자 모두 보고
- ② **단일지표 모순성**: 합계 지표 단독으로는 안 보이거나 *반대* 결론, 다축 조합에서 교정 (single-tool false positive 가 이 항목의 한 sub-measure)
- ③ **채널 교차 일관성**: 같은 결론이 ≥ 2 독립 채널에서 같은 방향 재현
- ④ **행동 가능성**: "개입 가능한 권유 한 줄" 까지 이어짐

> Discover 단계에서 5번째 항목 (직관 위반도/surprise) 도 후보였으나 N=1 회고 편향 우려로 제외. 최종 4 항목.

### 1.4 한계 (정직 선언)
- **N=1** · ground truth 라벨 없음 (자가 검증) · 시나리오 1개 (Hero S1 only) · precision/recall/F1 미산출 → **qualitative defense only**
- Apple Watch 미보유 → HeartRate / HRV / VO2Max / SleepAnalysis 전 채널 0건 → 자율신경 가설 답 불가능
- Google Timeline 은 2025-02 이후 15개월치만 (Apple Health 만 6년) → semantic 분석은 Paris/Seoul_rec window 한정
- ACL 부상일 ±2주, Paris 일자 ±1주 추정. day-type ↔ 도시 부분 동어반복 위험

---

## 2. 발견 인벤토리 (deck 매핑)

| 슬라이드 | 발견 | rubric ①②③④ | figure | 데이터 출처 |
|---|---|---|---|---|
| 7 | (A) K-means c0 학부=군복무 Δ=−1.2pp + (B) 도시 효과 day-type 의존 (home_only d=+1.04 / outing d=+1.36 / explore d=−0.80) | ✓✓✓△ | F07_label_vs_data.png | `src/personal/finding1_label_vs_data.py` |
| 8 | Paris 사건 3채널 시간 위상 — 활동량 (Paris 중) + 청취량 (Paris 중 monotonic 3.5배) + gait remodel (귀국 후 d=0.85~1.30) | ✓✓✓✓ | F08_paris_phase.png | `src/personal/finding2_paris_phase.py` |
| 10 (Hero) | 동일 trigger "Paris 효과 어땠어?" 에 T1 단독 = "+28% 더 활동적" (false positive) vs T1+T2+T3+T4 = "원료 투입 / 귀국 후 가공의 2단계 구조" | ✓✓✓✓ | F10_hero_paris_orchestration.png | finding2.json 도구 출력 그대로 |
| Appendix | 부상 시리즈 — Walking Steadiness 4개월 선행 + 수술월 asymmetry z=+5.58σ + Running 91일 후 8건 폭주 | ✓✓✓✓ | F09_injury_signals.png | `src/personal/finding3_injury.py` |

---

## 3. Slide Blueprint (11 + 1 appendix)

> 합계 300초 + Q&A 60초. matplotlib only (seaborn/plotly 금지, CLAUDE.md 정합).

| # | 제목 | 시간 | role |
|---|---|---|---|
| 1 | 나의 디지털 트윈 — 6년치 행동 데이터로 만드는 첫 prototype | 15s | Hook |
| 2 | 배경: 데이터 과학자라는 안경 | 25s | 동기 |
| 3 | [필수항목 1] 이전 연구 차용 / 본 기말프로젝트 신규 | 25s | wine 1줄 회고 + 신규 자산 |
| 4 | [필수항목 2] 데이터 수집 + raw data 정제 | 30s | 2 source (실사용) + iterparse + 9 metric + anchors SoT |
| 5 | 내 인생 타임라인 — 데이터의 chapter | 25s | 사용자 확정 7개 anchor |
| 6 | 연구 질문 + "유의미함"의 정의 | 30s | RQ + HOW 분리 + 4 rubric + 한계 |
| 7 | 발견 1 — 자전적 라벨이 데이터를 자르지 않는다 / 도시 효과는 단순하지 않다 | 45s | K-means + Simpson stratification |
| 8 | 발견 2 — 'Paris' 라는 한 사건이 세 채널에 다른 위상으로 | 45s | 3채널 시간 위상 |
| 9 | Hero S1 — 동일 trigger 에 도구 단독 답 vs 조합 답 | 50s | 평가 기준의 실증 (climax) |
| 10 | Vision — 디지털 트윈 + 함께 만들 분 | 30s | call to action |
| 11 | 한계 + Q&A | 30s | 정직 선언 + 진입 |
| 12 | Appendix — 부상 시리즈 (질문 시 활용) | — | walking_steadiness + asymmetry + Running |

---

## 4. System Architecture (한 줄 + 다이어그램)

```
┌────────────────────────────────────────────────────────────────────────┐
│  RAW (data/raw/, .gitignore)                                            │
│  • Apple Health export.xml (216 MB)  • Google Timeline JSON              │
│    (GPX workout-routes 10건 수집됐으나 분석 미사용 — slide 11 참조)     │
└────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼  iterparse 스트리밍 + 좌표 dropping
┌────────────────────────────────────────────────────────────────────────┐
│  PROCESSED (data/processed/personal/*.parquet)                          │
│  personal_daily.parquet · personal_daily_hmm.parquet · _merged          │
└────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼  src/personal/data.py load_*()
┌────────────────────────────────────────────────────────────────────────┐
│  FINDING MODULES (src/personal/finding*.py)                             │
│  finding1_label_vs_data  · finding2_paris_phase  · finding3_injury     │
│  → results/personal/finding{1,2,3}.json                                 │
└────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼  scripts/personal/build_fig_*.py
┌────────────────────────────────────────────────────────────────────────┐
│  FIGURES (results/personal/figures/*.png)  + SLIDES.md                  │
└────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼  Anthropic tool_use orchestrator
┌────────────────────────────────────────────────────────────────────────┐
│  SURFACE (Hero S1 시연)                                                  │
│  T1 단독 vs T1+T2+T3+T4 조합 → 한국어 합성 → user                       │
└────────────────────────────────────────────────────────────────────────┘
```

### 4.1 책임 분담 원칙
- **src/personal/** — 모든 시뮬레이션/통계 로직 (CLAUDE.md 정합). `anchors.py` 가 단일 진실 출처, 다른 모듈은 import 만.
- **scripts/personal/** — figure 생성·실험 entry. src/ 의 finding 모듈을 호출만.
- **docs/personal/** — SLIDES.md (marp) + REPORT.md (스피커 노트) + QA_CARDS.md + DECK_PLAN.md.
- **results/personal/** — finding{1,2,3}.json (data) + figures/*.png (산출물).

---

## 5. 도구 인벤토리 (T1~T7)

| 도구 | 이름 | 강의 §  | 입력 | 출력 |
|---|---|---|---|---|
| T1 | get_recent_step_trend | §1 Pearson | (start, end) | trend, slope, n |
| T2 | compare_location_activity | §2 Welch | (loc_A, loc_B, metric) | mean_A, mean_B, t, p, d |
| T3 | check_gait_quality | §3 z-score | (start, end, baseline) | z per metric |
| T4 | audio_summary | §3 ANOVA | (start, end, group_by) | F, p, group means |
| T5 | weekday_anomaly | §3 weekday-z | (start, end, channel) | weekday z 7개 |
| T6 | archetype_day | §4 K-means | (date) | cluster id + interpretation |
| T7 | mab_recommend | §4 UCB1 (wine-mab 1줄) | (context, arms, history) | selected arm + UCB |

> **CLAUDE.md 정합**: T6 K-means / T7 UCB1 은 numpy 직구현 (sklearn 금지). T1~T5 는 scipy.stats wrap.

---

## 6. Privacy Guardrails

- 좌표 (lat/lon) **0회 저장** — Google Timeline raw 에서 city-level granularity 로만 추출, `location_id` (masked: gym_A, home, office) 만 기록
- 모든 외부 도구 read-only (Gmail / Calendar / Drive / Naver / YouTube 검색만, 쓰기 권한 없음)
- 데이터는 git 미커밋 (`.gitignore` 로 `data/raw/`, `data/processed/` 제외)
- 발표 자료는 익명화된 집계치만 노출
- IRB 면제 사유: 본인 데이터 · 본인 분석 · 외부 배포 없음
- **LLM 가드**: system prompt 4 rules (도구 결과 외 지식 금지 / 수치는 도구 출력 그대로 / 도구 호출 없으면 "데이터 없음" / 불확실하면 confidence 표기) + 환각 정규식 후처리 (final_text 숫자 토큰 vs tool_result raw 매칭)

---

## 7. rev5 변경 changelog (mock-purge 포함)

### 7.1 폐기된 narrative (절대 사용 금지)
- "양(Quantity) vs 질(Quality) 회복 분리" / "8개월 vs 24개월" / "양은 늦게, 질은 먼저"
- 이유: `quality_cross_dt = 2022-12 / quantity_cross_dt = 2024-04` 는 데이터에서 계산된 값이 아니라 잘못된 `MIL_END = 2022-04` (실제 2023-05-14) 에 +8m/+24m 산술 *하드코딩 string*. 정확한 baseline 으로 재계산 시 양/질 5채널이 두 회복 이벤트 (전역·ACL) 모두에서 +1~2m 동조 회복 → 분리 가설 기각.
- 이 narrative 의 *변주* ("충격 강도 비대칭" / "활동성 vs 보행 질") 도 모두 폐기. 같은 프레임의 재포장 금지.

### 7.2 삭제된 파일 (`rm` 완료)
- `scripts/personal/build_fig_06_v_curve.py`, `build_fig_06_v_curve_v2.py` (양/질 V-curve)
- `scripts/personal/build_fig_07_paris_seoul.py`, `build_fig_07_paris_seoul_v2.py` (옛 발견 2)
- `scripts/personal/build_fig_08_hero_demo.py` (mock 대화 본문)
- `results/personal/figures/F06_v_curve*.png`, `F07_paris_seoul*.png`, `F08_hero_demo*.png`
- `docs/personal/DECK_PLAN_v1.md` (legacy)

### 7.3 신규 자산
- `src/personal/anchors.py` — SoT 단일 진실 출처 (입대 2021-11-15, 전역 2023-05-14, ACL 부상 2023-10, 수술 2024-01, Paris 2024-12~2025-06)
- `src/personal/data.py` — parquet loader + zscore_within_baseline
- `src/personal/finding1_label_vs_data.py` — K-means K=4 numpy 직구현 + Simpson stratification
- `src/personal/finding2_paris_phase.py` — 3채널 위상 계산
- `src/personal/finding3_injury.py` — walking_steadiness + asymmetry z-score + Running resume
- `scripts/personal/build_fig_07_label_vs_data.py` + `build_fig_08_paris_phase.py` + `build_fig_09_injury_signals.py` + `build_fig_10_hero_paris_orchestration.py`
- `scripts/personal/sanity_anchors.py` — CI 게이트, 폐기 anchor 문자열 grep

### 7.4 CI gate (sanity_anchors)
- (a) `src/personal/anchors.py` 값이 사용자 확정 사실과 일치
- (b) docs/personal/*.md 와 scripts/personal/*.py 에 `2020-07`, `2022-04`, `8개월`, `24개월`, `quality_cross`, `quantity_cross`, `MIL_END.*2022-04`, `양은 늦게`, `질은 먼저` grep 결과 0건
- (c) deprecated 파일 (build_fig_06_v_curve*.py, build_fig_07_paris_seoul*.py, build_fig_08_hero_demo.py) 미존재 확인
- 실패 시 exit 1.

---

## 8. 발표 직전 체크리스트

- [ ] `uv run python -m src.personal.finding1_label_vs_data` 통과
- [ ] `uv run python -m src.personal.finding2_paris_phase` 통과
- [ ] `uv run python -m src.personal.finding3_injury` 통과
- [ ] `PYTHONPATH=. uv run python scripts/personal/build_fig_{07,08,09,10}_*.py` 4개 figure 모두 산출
- [ ] `uv run python scripts/personal/sanity_anchors.py` exit 0
- [ ] `docs/personal/SLIDES.md` marp 빌드 → pptx
- [ ] Hero S1 라이브 시연 dry-run 1회 (LLM 호출, 90초 안)
