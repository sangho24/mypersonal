# PRD — wine-mab-project

## 목표 (Goal)
와인 선택을 multi-armed bandit 문제로 정식화하고, 다양한 탐색 정책(ε-greedy, UCB1, Thompson Sampling 등)의 누적 후회(cumulative regret) 성능을 한국 합성 페르소나 위에서 비교하여 "어떤 사람에게는 어떤 탐색 전략이 합리적인가"를 정량적으로 제시한다.

## 사용자 (Users)
- 1차: 본 프로젝트 평가자 (교수/조교) — 데이터 과학 6단계 방법론 충실도와 main contribution 명료성 평가
- 2차: 본인 — 코드 자산으로 재활용 (cold-start 추천 시스템 연구 등)
- 잠재: 와인 입문자, 추천 시스템 설계자

## 핵심 기능 (Core Features)
1. **데이터 파이프라인** — 한국 와인 리테일 사이트(와인앤모어 주축) 스크래핑 → 카테고리 분류 → MAB arm 정의. 1,500 ~ 3,000병 목표. Nemotron-Personas-Korea에서 200 ~ 500개 페르소나 샘플링.
2. **Persona Translation Layer (핵심 기여 1)** — Nemotron의 일반 demographic 페르소나를 와인 도메인 선호 벡터(지역 가중치, 품종 가중치, 가격 민감도, α)로 매핑. 방법 A(클러스터 기반)와 방법 B(LLM 기반)를 모두 준비, 진행 추이에 따라 선택 또는 비교.
3. **Reward Function + MAB 시뮬레이터 (핵심 기여 2)** — 취향 매치 vs 객관 품질을 분리한 reward 정의, 페르소나 클러스터 × 정책 × 반복 시뮬레이션 (T=50 정도), numpy 벡터화.

## MVP 제외 사항 (Out of Scope)
- 실제 사용자 대상 UI/추천 앱 (시뮬레이션 결과 분석에 집중)
- 협업 필터링 / 콘텐츠 기반 추천 베이스라인 (본 연구의 빈 공간은 탐색-활용 의사결정 구조 자체임)
- 글로벌 시장 데이터 (한국 시장 한정 — 글로벌 데이터셋은 attribute 보강에만 사용)
- 실시간 데이터 업데이트 / 정기 크롤링
- 모바일·웹 인터페이스
- 와인 외 다른 도메인의 실제 데이터 적용 (transfer 가능성은 발표 메시지로만 다룸)

## 디자인 (Design)
- 모든 시각화는 **matplotlib only** — seaborn/plotly 금지
- 색상은 의미 기반: 정책별 고유색 (cb-friendly palette), 페르소나 클러스터별 고유색
- 산출물: cumulative regret 곡선, 페르소나×정책 승률 히트맵, arm pull stacked area chart, 페르소나 클러스터 산점도
- 발표/보고서용 figure는 `results/figures/`에 PNG + PDF 양식으로 저장
