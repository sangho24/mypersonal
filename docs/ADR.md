# ADR — Architecture Decision Records

## 철학
- 수업 평가 기준 우선: MAB / K-means는 외부 라이브러리 없이 numpy로 직접 구현한다.
- 시뮬레이션과 시각화는 분리한다 — log를 매개로.
- "동작하는 최소 구현"을 먼저 만들고 단계적으로 풍부하게 한다.

---

## ADR-001 — 와인 리테일 사이트로 wine21을 1차 대상으로 선정 (2026-05-14 갱신)
- **결정 (갱신)**: wine21.com을 메인 스크래핑 대상으로 한다. 데이터 부족 또는 카테고리 편중 시 winenara, 와인서처 등에서 보강.
- **원래 결정**: 와인앤모어를 1차 대상으로 했으나, 정찰 단계에서 환경(IP/UA)에 무관하게 접근이 차단됨을 확인. 사용자 로컬 수동 수집보다 자동화 가능 경로를 우선.
- **이유**: wine21.com은 한국 시장 데이터·한글 시음 노트·카테고리 구조가 명확하고 HTTP 200으로 접근 가능. winenara.com은 보조.
- **트레이드오프**: 와인앤모어 대비 가격 정보의 신선도·구매 가능성 정보가 약할 수 있음. 가격은 winesearcher 또는 winenara로 보완 가능.
- **결정 (2026-05-14, step4)**: 카테고리 축은 (지역 × 가격대)로 확정. 사유: 50병 sample에서 (지역×품종색)은 프랑스-레드 12병 쏠림 + 단발 셀 6개로 꼬리가 길지만, (지역×가격대)는 ≥2병 셀이 10개로 고르게 분포. 가격은 "합리적 취향 탐색"의 핵심 결정 축이기도 함. 10개 카테고리를 `data/processed/category_candidates.json`에 저장. 가격대 임계: 저가 < 6만 / 중가 6만~15만 / 고가 ≥ 15만.

## ADR-002 — Persona Translation Layer 방법 A를 기본, 방법 B를 선택적 비교로
- **결정**: 클러스터 기반 매핑 (방법 A)을 메인 경로로 구현. 시간 여유가 있으면 LLM 기반 매핑 (방법 B)을 추가 비교 실험으로 진행.
- **이유**: 해석성이 높고 외부 API 의존이 없어 안정적. LLM 호출은 비용·일관성 검증 부담이 있음.
- **트레이드오프**: 방법 A는 개별 페르소나의 미묘한 차이를 잃을 수 있음. 결정은 phase 03에서 클러스터링 결과의 해석 가능성을 본 뒤 재확인.

## ADR-003 — MAB / K-means를 numpy로 직접 구현 (sklearn 등 금지)
- **결정**: ε-greedy, UCB1, Thompson Sampling, K-means 모두 numpy로 직접 구현한다.
- **이유**: 수업 평가 기준 — 직접 구현이 핵심 기여. 시뮬레이션이 작은 규모(T=50, 페르소나 200~500, 정책 3~5개)라 numpy 벡터화로 충분.
- **트레이드오프**: 정책 후보를 확장할 때 직접 구현 비용 발생. 외부 라이브러리의 검증된 변형은 사용하지 못함.

## ADR-004 — 시뮬레이션 결과는 JSONL append 로그로 저장
- **결정**: `results/logs/{run_id}.jsonl`에 한 줄당 한 (persona, policy, t) record를 append.
- **이유**: 시뮬레이션과 분석 분리. 재실행 없이 다양한 시각화 가능. 디스크 footprint 작음.
- **트레이드오프**: 대규모 확장 시 parquet 전환 고려 필요. 현재 규모에서는 JSONL이 검토 용이.

## ADR-005 — 시각화 라이브러리는 matplotlib only
- **결정**: 모든 figure는 matplotlib으로 작성. seaborn, plotly, altair 금지.
- **이유**: 계획서에 명시. 출력 일관성과 PDF 변환 안정성.
- **트레이드오프**: 히트맵·산점도 코드를 약간 길게 써야 함.

## ADR-006 — 보상 모델은 X-Wines 실데이터로 grounding (2026-05-14)
- **배경**: wine21 소비자 평점은 전부 5.0(평점자 1~2명)이라 변별력 0. vivino 보강은
  explore API·Playwright 모두 매칭률 14% — wine21 평점순 슬라이스가 무명 수입와인이라
  어디에도 없음이 확인됨. 평점 커버리지를 쫓는 것은 과투자로 판단.
- **결정**: 보상 모델을 두 층으로 분리한다.
  1. **와인 속성 벡터**는 X-Wines 데이터셋(rogerioxavier/X-Wines, CC0, MDPI BDCC 2023)에서
     도출. 10만 와인의 `Body`(5단계)·`Acidity`(3단계)·`Grapes`로 품종→프로파일 통계표를
     만들어 wine21 와인에 적용. (검증: 품종별 표준편차 ~0.5/5, wine21 49병 품종 조인 86%)
  2. **취향 아키타입**은 X-Wines 21M 평점에서 사용자를 K-means 클러스터링해 도출.
     Nemotron 페르소나는 Persona Translation Layer로 이 아키타입에 매핑.
- **핵심 원칙**: 전문가/외부 평점은 **reward 자체가 아니라 input feature/prior**. reward 는
  `persona_fit(페르소나 취향 × 와인 속성)` 가 주가 되어야 페르소나마다 최적 arm 이 갈리고
  다중 페르소나 MAB 비교가 성립한다. (reward = 전역평점이면 전 페르소나가 한 arm 으로 수렴 → 붕괴)
- **트레이드오프**: X-Wines Full(21M, 1.1GB)·Slim 은 git 밖 Google Drive 의존 —
  재현 시 별도 다운로드 필요. X-Wines 사용자는 익명(인구통계 없음)이라 페르소나는
  여전히 Nemotron 에 의존. wine21↔X-Wines 는 개별 와인이 아닌 품종/타입/국가 aggregate
  레벨 조인.
- **라이선스**: X-Wines CC0(제약 없음, 논문 인용 의무). vivino 평점은 보조 anchor 로만 잔존.

## ADR-007 — vivino 평점 보강은 sparse quality-prior 로만 사용 (2026-05-14)
- **결정**: vivino Playwright 스크레이퍼(`src/scraping/vivino.py`)는 유지하되, 매칭되는
  ~15% 와인의 평점을 보상 모델의 보조 quality-prior feature 로만 쓴다. 100% 커버리지를
  목표하지 않는다.
- **이유**: ADR-006 참고 — 보상의 주축은 persona_fit. vivino 는 "객관적 품질" anchor 보조항.
- **트레이드오프**: 보강 평점이 희소(~15%)하므로 결측 시 prior 무정보 처리.

## ADR-008 — 와인 universe = wine21 폭넓은 수집, 가격은 wine21 실값 (2026-05-14)
- **배경 (탐색 경위)**:
  - X-Wines 를 universe 로 쓰려 했으나 **가격 컬럼이 없음** (17속성 중 가격 0).
  - vivino 를 가격원으로 검토 → X-Wines 와인의 vivino 재조회 매칭률 **13%** (X-Wines 가
    vivino 2022 스크랩인데도). vivino 검색은 평점·가격 모두 13~14% 가 천장 — 막다른 길.
  - wine21 평점순 슬라이스가 무명 와인이라 다채롭지 못했던 것이지, wine21 전체와인
    (~15K~35K병) 은 충분히 다양함을 확인.
- **결정**:
  - 와인 universe = **wine21 폭넓은 수집** (평점순 1,500 슬라이스가 아니라 전 국가·전
    카테고리에서 3,000~5,000병). wine21 의 실제 ₩가격을 그대로 사용 — 가격 모델링 불필요.
  - arm = `country × price_tier` (price_tier 는 wine21 price_krw 분위수).
  - X-Wines 의 역할 = 와인 속성(품종→Body/Acidity 프로파일)·취향 아키타입 제공 (universe 아님).
- **이유**: 실데이터 100%·모델링 0·vivino 의존 0. "다채로움" 은 wine21 전체에서 폭넓게
  뽑으면 해결되고(병목은 평점순 정렬이었지 wine21 크기가 아니었음), 한국 시장·실가격이라는
  프로젝트 전제도 지킴.
- **트레이드오프**: wine21 3,000~5,000병 수집은 백그라운드 배치 2~4시간. wine21↔X-Wines 는
  품종 레벨 aggregate 조인(개별 와인 조인 아님, 커버리지 86%).

## ADR-009 — 발표 범위(2026-06-09) = mark-up→MAB 단일 spine, 페르소나/K-means는 보고서 only (2026-06-05)

**결정**: 7분 발표의 narrative spine을 "mark-up 정량화(r=-0.752) → Akerlof 기제(Champagne 2.82x) → MAB 탐색 전략"으로 확정한다. 페르소나 layer(ADR-002), K-means 취향 아키타입(ADR-003/006), Persona Translation(phase 03)은 발표 범위에서 제외하되 phase 03/04 산출물은 6/24 제출 보고서·notebook에 부록으로 잔존시킨다.

**이유**: NARRATIVE_PLAN.md가 진단한 "왜 MAB?" 치명적 약점은 reward를 mark-up 실값으로 파라미터화(W1)하면 해소된다. 페르소나 multi-arm 비교는 발표 7분에 들어가지 못하고, K-means는 arm = country × price_tier 라는 자연 분할이 사실상 대체. 즉 *기획서_rev2의 분석 깊이는 유지하되 발표 prioritization*.

**MAB이 분석의 산물이라는 위상**: reward = 1/mark-up_arm 은 §3.4 발견의 직접 함수. noise = X-Wines 국가별 평점 분산(ADR-006의 X-Wines grounding 재활용). arm 정의 = ADR-008의 country × price_tier 분할. MAB은 발견의 *연장선*임이 명시적.

**K-means에 대한 입장**: numpy 직접 구현은 X-Wines 사용자 아키타입 도출용으로 phase 03 코드로 잔존(scripts/build_archetypes.py). 발표에서 미시연하나 보고서 부록 §B에 결과만 인용. 평가 기준 "직접 구현"은 보고서로 만족.

**개인 데이터 pivot 기각**: Apple Health + Google Timeline 각도(P1~P4)는 N=1, 도메인 전환 시 PRD/기획서_rev2/ADR-001~008 전면 폐기 및 4일 안 재합리화 불가. 별도 연구 프로젝트로 분기.

**트레이드오프**: 페르소나 다양성(기획서_rev2의 핵심 차별점)이 발표에서 보이지 않음 → 보고서 §4에서 별도 다룸. Q&A에서 이 부분 질문 시 "6/24 제출 보고서에 포함됨"으로 답변.

**Hero 단위**: regret은 KRW 환산("소비자 추가 부담액")으로 보고. 가정 = 평균 와인가 70K KRW, T=200 = 가상 소비 횟수. 가성비(1/markup) 단위는 부록.

## ADR-010 — Personal-data digital-twin 트랙 채택 + 발표 시간 5분 + 필수항목 1/2 반영 (2026-06-08)

**결정**: 6/9 발표 spine을 "내 6년치 행동 데이터 → 강의 7기법 도구화 → LLM 오케스트레이터 → 디지털 트윈 prototype"으로 확정. 와인 트랙(ADR-009)은 보고서 부록으로 보존, 발표는 Slide 2 "투 트랙 회고"에서 1줄 + Slide 3 "차용 자산"에서 UCB1 출처로 명시.

**이유**:
1. AI 시대 + 취업 시기 개인 동기 — "나만의 특수성·능력을 함께 고민해주는 시스템"이 와인 시장 분석보다 발표자에게 본질적
2. 와인 트랙 src/mab/ UCB1 자산 폐기 없이 T7로 흡수 → 강의 평가 기준(numpy 직접 구현) 유지
3. 학교 프로젝트 너머 collaboration 의도 → 발표 자체가 동료 모집 함수

**발표 instruction 반영**:
- 5분 발표 + 1분 Q&A (총 6분) → 10 슬라이드 × 평균 30s
- **필수항목 1 (이전 연구 차용 vs 본 프로젝트 신규)** → Slide 3 전용 슬라이드 신설
- **필수항목 2 (데이터 수집 + raw data 정제)** → Slide 4 전용 슬라이드 신설

**구조 변화**:
- src/personal/{data,tools,agent}.py 신설 — 7 DS tools + LLM orchestrator (본 프로젝트로 신규)
- docs/personal/{SLIDES,REPORT,QA_CARDS,DECK_PLAN}.md 신설
- 6 figures (F02 two-track / F04 prior-vs-new / F05 data pipeline / F06 V-curve / F07 Paris-Seoul / F08 hero / F09 digital-twin)
- Privacy: city-level only, masked location_id, ANTHROPIC_API_KEY env, OCR 자동 검수 0 hit

**Trade-off**:
- Wine 트랙 r=-0.752 / ₩909K 절감 hero 슬라이드 미점유 → Slide 2 회고로 처리. 보고서 본문 유지.
- N=1 한계 → 학술 발표 아닌 prototype 시연 + 디지털 트윈 vision으로 framing

**rev4 update (2026-06-08 사용자 피드백)**:

사용자가 deck rev3 검토 후 4가지 피드백을 줌. 반영 결정:

1. **타임라인 시각화 추가** — Slide 5에 인생 굵직한 사건 6~8개 (대학 입학 / 군 입대 2020-07 / 군 전역 2022-03 / 복학 / 프랑스 교환 2024-12 / 한국 귀국 2025-06-29) figure F03 신설. 발견 1·2 전에 청중이 *맥락*을 이해하도록 함.

2. **발견 1 양 vs 질 정의 명확화** — Slide 7에 "양 = 걸음 수(steps/day)" / "질 = 보행 속도, 보폭, 비대칭성, 양발 지지 비율" 명시 + 회복 비유 추가. Figure F06 양/질 라벨 annotation 보강.

3. **와인 트랙 톤다운** — Slide 2 배경에서 와인 0회 등장. Slide 3 트랙 회고는 1줄 + 차용 자산 1줄로만 (Slide 2 새로 배경 추가).

4. **배경 슬라이드 신설** — Slide 2 "데이터 과학자 = 세상 보는 안경 / 모델링 관심 → 나부터 분석 → 나를 설명하는 데이터" — 연구 질문 정당화.

5. **도구 선택 평가 기준 명시 + RQ 수정** — 평가 기준 = "도구 조합으로 single-tool false positive 감소". RQ가 이 기준을 명시. Hero S1이 T1 단독(틀린 결론) vs T1+T2+T3 조합(정확한 결론)을 정성적 비교로 시연. N=1 + ground truth 부재로 정량 precision/recall 불가 — 한계 정직 인정.

**구조 변화**: 10 slides 300s → 11 slides 300s. 추가 figure F03 personal timeline. 기존 F06/F08 annotation 보강.
