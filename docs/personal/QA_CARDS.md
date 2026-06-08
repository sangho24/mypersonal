# QA Cards — 발표 대비 예상 질문 12선 (rev5)

> 빅데이터컴퓨팅 기말 발표 Q&A 대비용. 각 카드는 1줄 질문 + 3~5줄 답변.
> rev5 (2026-06-08) — 양/질 narrative 폐기 (코드 하드코딩 산물로 데이터 재계산에 의해 기각됨), 새 발견 = (1) 라벨이 데이터를 자르지 않는다 + 도시 효과 day-type 의존, (2) Paris 사건의 다채널 시간 위상, Hero = Paris orchestration 시연. 4항목 rubric (통계 분리도 / 단일지표 모순성 / 채널 교차 / 행동 가능) 명문화.
> 작성: 20200572 엄상호

---

## Card 1. N=1로 무엇을 일반화하나?

**Q.** N=1 자기-실험인데 통계적으로 무엇을 일반화하려는 건가?

**A.**
- 일반화는 **명시적으로 미주장**. 본 작업은 *self-experiment prototype*이고, 외적 타당도(external validity)는 future work로 분리해 둠.
- 대신 청구하는 건 **방법론적 시연**: 7개 도구를 LLM이 오케스트레이션해서 단일 도구 false positive를 도구 조합으로 *교정*할 수 있다는 *qualitative defense*.
- Hero S1 시연도 *내 6년치 데이터 1개 시나리오*에 한정 — 통계적 일반화는 cohort study 단계로 분리, 본 발표 스코프 아님.

---

## Card 2. 왜 와인 안 하고 개인 데이터?

**Q.** 학기 초 wine-mab 트랙에서 왜 개인 데이터 디지털 트윈으로 피벗했나?

**A.**
- Slide 2 배경에서 깔았듯 "데이터 과학자 = 세상 보는 안경 → 나부터 분석하고 싶었다"가 1차 동기. 남의 시장(와인)보다 *내 6년치 행동 데이터*가 모티베이션과 정합.
- Slide 3에서 와인 트랙 회고는 **1줄로 압축** — 와인은 *남의 시장이라 진정성 부족 + 강의 §1~§4 7기법이 개인 데이터에 1:1로 더 자연스럽게 wrap*되기 때문에 pivot.
- 와인 자산은 폐기 아니고 **`src/mab/UCB1`을 T7 알림 선택기로 재배치** — 차용 자산 칸에서 1줄로만 등장.

---

## Card 3. 도구 선택 평가 기준이 정성적이라는데, 정량적 평가는 정말 불가능한가?

**Q.** "LLM이 도구를 잘 골랐다"를 정성적 시연으로만 평가한다는데, precision/recall 같은 정량 지표는 정말 못 내나?

**A.**
- 솔직히 **현재 스코프에서는 불가능**하다고 정직하게 인정. 이유 두 가지: (1) **N=1** — 단일 발표자, 단일 시나리오라 false positive rate를 통계량으로 환산할 표본이 없음. (2) **ground truth 라벨 부재** — "운동량 감소가 false positive다"라는 판정은 발표자 자가 검증(실제 동네 산책은 정상)에 의존하지, 의료 진단/외부 어노테이터가 라벨링한 dataset이 없음.
- 그래서 본 발표는 §1.2.1에 *qualitative defense*만 청구한다고 *RQ 안에 미리 박아 둠* — 평가 기준 자체를 "single-tool 결론 vs 도구조합 결론의 정성적 차이"로 좁힘.
- **Future work으로 제안하는 정량화 경로**: ① N>=10 cohort에서 동일 trigger를 baseline run/full run으로 2회 돌려 응답 라벨링 → precision/recall 산출, ② **인간 expert(예: 보행 분석 전문가/임상 PT)의 tool selection 시퀀스와 LLM tool selection 시퀀스를 비교**해 inter-rater agreement(Cohen's κ) 측정. 이 두 가지가 들어가야 정량 청구가 honest해짐.

---

## Card 4. LLM hallucination은 어떻게 막나?

**Q.** LLM이 도구 호출 결과를 잘못 해석하거나 환각하면 어떻게 되나?

**A.**
- **4-rule system prompt** 가드: (1) 도구 결과 외 외부 지식 사용 금지, (2) 수치는 도구 출력에서 *그대로* 인용, (3) 도구 호출 없으면 "데이터 없음" 명시, (4) 불확실하면 confidence 표기.
- 추가로 **정규식 후처리**: LLM 응답에서 숫자/날짜/단위 토큰을 추출해 tool_result raw output과 대조 — 불일치 시 재호출 또는 응답 폐기.
- prototype 단계에서는 충분하다 보지만, false negative(가드를 통과한 미세한 환각)는 인정 — 이건 평가 기준 정량화(Card 3)와 같은 후속 작업 항목.

---

## Card 5. 발견 1의 "K-means cluster" 와 "Simpson" 결합이 정확히 뭔가?

**Q.** 발견 1이 두 가지가 묶여 있는데, K-means 결과와 도시 효과 분해를 다시 정리해 달라?

**A.**
- **K-means 부분**: 9채널 일별 (steps · distance_km · active_energy_kcal · flights · walking_speed · step_length · asymmetry · double_support · audio_max_dB) 을 numpy K-means K=4 (sklearn 미사용, k-means++ init + Lloyd, 15 seed best-of) 로 학습. 학부 baseline (2020-09~2021-10, n=343d) 의 majority cluster 를 c0 로 라벨링. c0 비중을 군복무 window (2021-11-15~2023-05-14, n=435d) 에서 다시 계산 — **61.2% vs 60.0%, Δ=−1.22pp**. 즉 두 시기가 *데이터 차원에선 같은 분포*. 자전적 라벨이 데이터를 자르지 않음.
- **도시 효과 부분**: Paris (n=197d, Maps Timeline dominant Paris 라벨) vs Seoul_rec (n=340d, 2025-07 이후) 의 일일 steps. 전체 비교는 Welch t=5.09, p<0.001, d=+0.50 — 도시차 강함. *그러나* Maps day-category (home_only/routine/outing/explore) 로 stratify 하면 — home_only d=+1.04 (p<0.001), outing d=+1.36 (p<0.001) — Paris ↑↑, routine d=+0.36 (p=0.08, marginal), explore d=−0.80 (p=0.01) — **Seoul > Paris (반대 방향)**.
- **종합 메시지**: 자전적 라벨(군복무·Paris)이 데이터 라벨이 아니다. 단일 지표(steps 전체 평균)는 day-type 별로 방향·강도가 *반대*로 가는 풍부한 패턴을 평균으로 가린다. rubric ②(단일지표 모순성) ✓ + ③(채널 교차) ✓.

---

## Card 6. 라이브 API 시연 위험은?

**Q.** 발표 중 LLM API 호출이 실패하거나 느리면?

**A.**
- 2중 백업: (1) **mp4 데모 영상** 사전 녹화 — 라이브 실패 시 즉시 전환. (2) **`--mock` 모드** — 도구 호출을 cached fixture로 대체해 네트워크 없이 동일 흐름 재현.
- 라이브 시연은 Hero S1(부상 감지) 1건만 시도, 시간 예산 90초 초과 시 자동으로 mp4 fallback.
- API 키는 `.env` 로드, 발표 직전 `--mock` dry-run 1회 검증.

---

## Card 7. 왜 T1 단독으로는 Hero 의 결론이 안 나오는가?

**Q.** Hero S1 trigger "2025-06 Paris 효과 어땠어?" 에 T1 단독으로 답하면 뭐가 부족한가?

**A.**
- T1 (get_recent_step_trend) 단독 호출 결과: Paris 평균 9196 vs pre-Paris Seoul 평균 7161, Welch t=3.71 p=0.0002 d=+0.38, pct_change +28%. 한 숫자만 본 LLM 답: *"Paris 에서 일일 걸음수가 +28% 증가, 더 활동적이었음"*. → **단일 채널 false positive** — 활동량 한 축만 보니 *긍정적 사건* 으로만 결론.
- T1+T2+T3+T4 조합 호출 시 LLM 이 plan 단계에서 T4(audio_summary)·T2(compare_location)·T3(baseline_zscore)를 추가 호출 → 채널 1(활동량 Paris 중 d=0.25~0.74) + 채널 2(청취량 12월 71분→6월 251분, Spearman 0.86 단조) + 채널 3(귀국 후 gait remodel d=0.85~1.30, Maps explore-day Paris 후반 1/3 에 11건 폭발) 을 모두 잡음 → 답이 *"Paris=원료 투입 trigger, 귀국 후=가공 완료, 2단계 구조"* 로 교정.
- 핵심: **도구 조합 ≠ 도구 합집합**. 각 도구 출력을 *잇는* 것 (시간 위상 + 채널 간 상관) 이 LLM 의 역할. 단일 도구 출력은 정량적이지만 *해석 axis 한 개*만 보여줘 false positive 위험.

---

## Card 8. Privacy는?

**Q.** 6년치 개인 행동 로그를 다루는데 privacy 보호는?

**A.**
- 좌표(lat/lon) **0회 저장** — Google Timeline raw에서 city-level granularity로만 추출, 위치는 `location_id` (masked hash, 예: `gym_A`, `home`, `office`)로만 기록.
- 모든 외부 도구는 **read-only** — Gmail/Calendar/Drive/Naver/YouTube 도구는 검색·조회만, 쓰기 권한 없음.
- 데이터는 git 미커밋(`.gitignore`로 `data/raw/` `data/processed/` 제외). 발표 자료는 익명화된 집계치만 노출.
- IRB 면제 사유: 본인 데이터·본인 분석·외부 배포 없음.

---

## Card 9. 디지털 트윈이 자기 추적 앱과 뭐가 다른가?

**Q.** 이미 Apple Health, Samsung Health 같은 자기 추적 앱이 있는데 차별점은?

**A.**
- 기존 앱: **단일 도메인 대시보드**(걸음만, 심박만) + hard-coded rule 알림. 도구 *선택*이라는 행동 자체가 없음.
- 본 시스템: **LLM 오케스트레이션** — 자연어 질의 또는 proactive trigger → plan → 1~3개 도구 *조합* 호출 → tool_result → 한국어 1~3문장 합성. **도구 조합으로 단일 도구 false positive를 차단**(Hero S1 사례)하는 게 핵심.
- 즉 "추적"이 아니라 "**오케스트레이션 + 도구 선택 평가 기준 정합**"이 차별점.

---

## Card 10. [필수항목 1] 차용 vs 신규를 다시?

**Q.** 어디까지가 차용 자산이고 어디부터가 이번 기말의 신규 기여인가?

**A.**
- **차용(borrowed)**:
  - 학기 초 wine-mab 트랙에서 본인이 직접 구현해 둔 `src/mab/UCB1` numpy 모듈 — T7 알림 선택기로 포팅 (wine 트랙은 이 줄에서 마지막 등장)
  - 외부 표준 라이브러리: `scipy.stats`(가설검정 t-test/Pearson/ANOVA), `numpy`, `matplotlib`, `anthropic` SDK(LLM tool_use), Apple/Google 공식 export 스키마
- **신규(newly-done, 이번 기말에서 처음 한 것)**:
  - `src/personal/` 패키지 *전체* — `anchors.py`(SoT 단일 진실 출처), `data.py`(parquet loader), 7개 DS 도구(T1~T7) LLM 호출 형태 wrap, `agent/orchestrator.py` Anthropic `tool_use` 루프, 3개 finding 모듈 (`finding1_label_vs_data.py` K-means + Simpson, `finding2_paris_phase.py` 3채널 시간 위상, `finding3_injury.py` walking_steadiness 선행 등)
  - **§1.2.1 4항목 rubric** (통계 분리도 / 단일지표 모순성 / 채널 교차 / 행동 가능) — false positive 감소는 ② 의 sub-measure 로 격하
  - Hero S1 = **Paris 사건의 다채널 시간 위상 해부** 시나리오 설계 + figure F10
  - figure 5종 (F03 timeline, F05 pipeline, F07 label_vs_data, F08 paris_phase, F09 injury appendix, F10 hero orchestration) — matplotlib only, dynamic data binding
  - **CI 게이트** `scripts/personal/sanity_anchors.py` — 폐기된 anchor 문자열 grep 검출
  - DECK_PLAN/SLIDES/REPORT/QA_CARDS 문서 전부
- 즉 *알고리즘 한 줄과 표준 라이브러리는 차용*이지만 *도구화·LLM 결합·평가 기준·시나리오·발표 narrative*는 100% 신규.

---

## Card 11. "양/질 narrative" 를 폐기했다는데 왜?

**Q.** 이전 버전에 있던 "양은 늦게 질은 먼저" 발견이 사라졌는데 무슨 일?

**A.**
- *데이터 재계산 결과 narrative 가 데이터로 기각됨*. 옛 `build_fig_06_v_curve_v2.py` 가 결론으로 인용하던 "양 24개월 / 질 8개월" 은 코드 내 `quality_cross_dt = 2022-12` / `quantity_cross_dt = 2024-04` 라는 *하드코딩 string* 이었고, 그것도 잘못된 MIL_END (2022-04, 실제 2023-05-14) 에 +8m/+24m 를 단순 산술한 값.
- 정확한 baseline (pre-MIL 2020-09~2021-10) 으로 cross-month 를 *계산해서* 다시 보면, 전역 (2023-05) 후엔 5채널 모두 +1개월 (2023-06), ACL 수술 (2024-01) 후엔 5채널 모두 +1~2개월에 baseline ±1σ 재진입 — *양과 질의 회복 속도가 사실상 동조*. 분리 가설이 데이터에 의해 기각됨.
- 그래서 옛 narrative 를 폐기하고 hypothesis-free 데이터 탐색 (workflow 2단계 fan-out) 으로 새 발견 후보 산출 → 위 발견 1 (K-means + Simpson) + 발견 2 (Paris 다채널 위상) + Hero (Paris orchestration) 으로 deck 전체 재작성. 옛 figure/스크립트는 모두 `rm` 정리, 잔재 검출은 sanity_anchors CI 가게이트.

---

## Card 12. 부상 시리즈 (Appendix) 가 따로 있는 이유?

**Q.** ACL 수술 관련 분석이 발표 본문이 아니라 appendix 인 이유는?

**A.**
- 부상 시리즈 자체는 매우 robust — (a) Walking Steadiness 가 2023-09 100% → 10월 96.8% → 11월 95.5% → 12월 93.1% → 수술월 2024-01 90.0% 로 **단조 하락** (사용자 통증 자각 4개월 전부터 데이터 신호), (b) 수술월 asymmetry z=+5.58σ 는 6년 시계열 6채널 통틀어 단일월 최강 단일-channel signature, (c) Running workout 공백 296일 → 수술 후 정확히 91일 만에 첫 재개 + 2024-04 한 달에만 8건 폭주.
- 본문에 넣지 않은 이유: (1) 발표 시간 5분 제약 — 발견 1/2/Hero 만으로 이미 빠듯, (2) 부상 narrative 는 *임상 색채* 가 강해 N=1 의료 진단 오해 위험, (3) 본 발표 thesis ("자전적 라벨이 데이터를 자르지 않는다" + "도구 조합") 와 *직접* 정합도가 약함.
- Q&A 에서 부상 관련 질문 나오면 F09 figure 한 장 꺼내 30초 답변 가능. rubric ① (z=+5.58σ 시계열 max 명시) + ② (사용자 자각 < 데이터 신호) + ③ (steadiness + asymmetry + workout 3 채널) + ④ (조기 정형외과 권유) 모두 ✓ 한 발견 — 본문에 넣어도 무방하지만 시간 압박에 의한 선택.
