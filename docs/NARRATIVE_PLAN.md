# 발표 Narrative 기반 분석 재설계 플랜

> 작성일: 2026-06-05
> 목적: 단발 finding 모음이 아니라, 발표 narrative가 처음부터 끝까지 한 줄로 흐르도록 분석을 재설계.
> 컨텍스트: `results/report/report.md` (rev1) 검토 후 도출된 narrative 약점 진단 + 보강 계획.

---

## 1. 현재 분석의 narrative 약점 (7분 발표 기준)

| # | 발표 중 받게 될 질문 | 현재 답할 수 있나? | 비고 |
|---|---|---|---|
| 1 | "Cohen's d=0.56 의 *경제적* 의미는?" | △ | 기술통계로만 — *왜 중요한지* 약함 |
| 2 | "Mark-up 4.4~12배의 *원인 가설*은?" | △ | "정보 비대칭"이라 했지만 *기제* 미증명 |
| 3 | "왜 *하필* MAB? 분석에서 MAB이 나온 게 아니라 그냥 붙인 것 아닌가?" | ✗ | **치명적** — MAB 보상이 합성 데이터 |
| 4 | "France 4.4 / Spain 12 의 *구체적* 이유는?" | ✗ | 케이스 부재 |
| 5 | "샘플 기간 의존성은?" | ✗ | 1개 12개월만 검정 |
| 6 | "이게 한국에만 있는 현상인가, 글로벌 패턴인가?" | ✗ | 비교 baseline 부재 |
| 7 | "그래서 *소비자에게* 어떤 actionable insight?" | △ | 추상적 |

---

## 2. 발표 narrative 한 줄 (제안)

> **"한국 와인 시장에는 4.4~12배의 mark-up 격차가 있고 (정량화), 이 격차는 원가가 낮을수록 크다 (기제). 소비자는 이 정보 비대칭 하에서 *탐색해야* 한다. MAB은 이 탐색 문제의 수학적 정식화이며, 실제 mark-up 데이터로 보상을 모수화한 시뮬레이션이 합리적 전략을 보인다."**

이 한 줄이 *끝까지 무너지지 않게* 하려면 아래 추가 분석이 필요.

---

## 3. 추가 리서치·분석 계획 (narrative-driven)

### 🅐 Mark-up 분석 심화 (현재 §3.4 보강)
- **케이스 스터디 3개**: France(낮은 mark-up) / Spain(최고 mark-up) / Chile(신대륙 vs 가격) — 가격대별 라인업, 대표 와인 예시
- **샘플 기간 robustness**: 12개월 → 6개월×2 분할 비교 (rolling consistency)
- **카테고리별 mark-up**: HS 220421(병와인) vs 220410(스파클링) 분리 — *왜 mark-up이 다른가*

### 🅑 정보 비대칭 *기제* 입증 (현재 §3.2 + §3.5 강화)
- **카탈로그 가격대 ↔ mark-up 회귀**: 고가 카탈로그 비중이 큰 국가일수록 mark-up이 큰가?
- **세그먼트 분해**: 저가($/kg 낮음) vs 프리미엄 국가 분리 — Akerlof 메커니즘이 *어디서* 작동하는지
- **wine21 tasting note 어휘 분석**: 카탈로그가 어떻게 "프리미엄"으로 포지셔닝하는지 (워드클라우드 + 가격대별 keyword)

### 🅒 ★MAB을 분석과 *진짜로* 연결 (가장 중요)
- **MAB 보상 = 실제 mark-up 데이터로 모수화**: 각 arm = 11개 국가, reward = `1 / mark-up` (가성비), 잡음은 X-Wines rating 분산
- **현실 정렬 시뮬레이션**: 소비자가 "어느 국가 와인을 시도할지" MAB로 학습 → ε-greedy / UCB / Thompson 비교
- **반사실(counterfactual)**: "wholesale 가격을 알았다면" oracle baseline → regret 측정
- 이러면 *MAB이 분석의 **연장선**에 위치*

### 🅓 글로벌 baseline 비교 (질문 #6)
- 관세청 데이터로 한국 *이외* 와인 시장 비교는 불가 → 대신 **OIV / Wine Intelligence 공개 통계 인용**으로 한국 mark-up이 비정상인지 normal인지 contextualize

### 🅔 Actionable insight (질문 #7)
- "한국 소비자가 mark-up 4.4배(France)를 선택했을 때 *얼마의 잉여 가치*를 가져가는가?" → 정량화
- "탐색 비용 vs 정보 이득 trade-off"로 정식화

---

## 4. 실행 단위 (Wave 단위 진행)

| Wave | 작업 | 산출물 | 시간 추정 |
|---|---|---|---|
| **W1** | 🅒 *우선* — MAB 재설계 (real data 모수화 + counterfactual) | 새 `src/mab/realistic.py` + figure | 2시간 |
| **W2** | 🅐 Mark-up 심화 (case 3 + 기간 robustness + 카테고리별) | report §3.4 확장 | 2시간 |
| **W3** | 🅑 정보 비대칭 기제 (회귀 + 텍스트 분석) | report §3.5 + §3.8 신설 | 2시간 |
| **W4** | 🅓 + 🅔 글로벌 비교 + actionable insight | report §5 확장 + slides 준비 | 1시간 |
| **W5** | 발표 narrative 슬라이드 12장 | `results/slides/` | 2시간 |

---

## 5. 의사결정 핵심 (진행 전 확인)

이 narrative arc (정보 비대칭 → Mark-up 정량화 → MAB 탐색 전략) 으로 가도 될지, 아니면 다른 축 (예: 소비자 후생 / 시장 효율성 / 와인 등급 신호) 으로 바꿀지 확정 후 **W1부터** 진입.

특히 **W1(MAB 재설계)** 가 narrative 전체를 떠받치는 *기둥*. 여기서 "MAB은 *분석의 산물*" 이라는 위상이 안 잡히면 발표 끝까지 약함.

---

## 6. 현재 보고서 (rev1) 기준 robust 자산 (보존)

이 결과들은 narrative 재설계 후에도 *그대로 살아남는* 핵심 통계:

- **Mark-up ↔ wholesale**: r = -0.752, p = 0.0076, Bootstrap 95% CI [-0.935, -0.549]
- **카탈로그 vs 수입 분포**: Welch t = -7.37, p < 0.0001, **Cohen's d = 0.558** (medium)
- **민감도**: kg/병 및 환율 ±15% → Spearman ρ = 1.000 (순위 불변)
- **Mark-up 범위**: 4.4 (FR) ~ 12.0 (??) 11개국
- **MAB 현재 결과**: Thompson 30.8 < ε-greedy 44.4 < UCB1 49.3 (재설계 후 다시 측정)

## 7. 파일·코드 위치 (다음 세션 이어받기용)

- 보고서: [results/report/report.md](../results/report/report.md)
- 노트북: [notebooks/final_report.ipynb](../notebooks/final_report.ipynb) (executed: `final_report_executed.ipynb`)
- 노트북 빌더: [scripts/build_notebook.py](../scripts/build_notebook.py)
- 데이터 로더: [src/data/load.py](../src/data/load.py) (`load_wines`, `load_imports`, `country_summary`)
- 스크래퍼: [src/scraping/wine21.py](../src/scraping/wine21.py) (broad mode, 970 wines)
- 공공 API: [src/scraping/public_data.py](../src/scraping/public_data.py) (관세청, 470 rows × 11개국 × 12개월)
- 그림: `results/figures/eda/` (6개)
- PRD: [docs/PRD.md](PRD.md) (rev2)
- 기획서: [빅데이터컴퓨팅_기말프로젝트_계획서_rev2_20200572_엄상호.md](../빅데이터컴퓨팅_기말프로젝트_계획서_rev2_20200572_엄상호.md)
- ADR: [docs/ADR.md](ADR.md) (ADR-006~008 추가됨)

## 8. 발표·제출 일정 (역산)

- **6/9 (화) & 6/11 (목)**: 발표 7분
- **6/24 (수)**: 제출 (발표자료 + ipynb + 보고서)
- 오늘 기준 발표까지 약 4일 → W1~W3은 발표 전 필수, W4~W5는 제출 전까지

---

> 다음 세션 시작 시 이 문서를 먼저 읽고 W1부터 진입.
