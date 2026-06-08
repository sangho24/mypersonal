# PRD — wine-mab-project (rev2)

> rev2: 정현정 조교님 피드백 + 수업 방법론 채점 제약 + 남은 시간(5/27 기준 발표 13~15일,
> 제출 28일)을 반영한 엔지니어링 스펙. 모든 결정은 계획서 rev2 와 `docs/COURSE_NOTES.md`
> 메서드 체크리스트에 정렬.

## 1. 목표 (Goal)

수업이 다룬 데이터 과학 방법론(크롤링, pandas/numpy, 기술통계, t검정·상관, matplotlib
시각화, 공공데이터 API)을 **한국 와인 시장 데이터에 충실히 적용**한 채점 본론을 만들고,
그 위에 numpy 직접 구현한 MAB 시뮬레이션을 응용 레이어로 얹어 이해도를 증명한다.

## 2. 사용자 (Users)
- 1차: 평가자(서경희 교수, 정현정 조교) — 수업 방법론 충실도가 1차 평가 기준
- 2차: 본인 — 데이터·코드 자산 재활용

## 3. 범위 (Scope) — Tier 구조

**Tier 0 (반드시, 발표·제출 산출물의 70%):**
- wine21 BeautifulSoup 수집 + 공공데이터 API(KOSIS 또는 관세청)
- pandas 정제·describe·groupby·corr
- numpy 벡터화·boolean indexing 패턴
- **EDA 후 확정될 흥미로운 가설**에 대한 `scipy.stats.ttest_ind` (가설은 W1 수집 직후 결정)
- matplotlib 히스토그램·산점도·박스플롯·막대그래프 + seaborn heatmap
- 각 시각화 뒤 수치 print + 한국어 해석 1문장

**Tier 1 (표준 — 시간 허락 시 추가, 13주차 sklearn 패턴):**
- **sklearn 회귀** (가격 회귀 등 EDA 후 확정될 흥미로운 예측 문제) + 계수·잔류 해석
- **sklearn 분류** (가격 등급/라벨 분류 등) + feature importance 해석
- numpy 직접 구현 K-means + MAB(ε-greedy, UCB1, Gaussian TS)
- 페르소나 × 정책 cumulative regret 곡선, 승률 히트맵
- 와인 시음노트 워드클라우드 (11주차 패턴)
- GeoPandas/Folium 생산지 지도 (12주차 패턴)

**Tier 2 (스트레치, 미달성 시 보고서에 명시):**
- LLM 방법 B와 방법 A 비교 ablation
- X-Wines 21M 평점 K-means 아키타입 클러스터링
- 다른 도메인 transfer 논의

**Out of scope:**
- 실시간 UI/추천 앱, 협업필터링 베이스라인, 글로벌 시장 데이터로의 한국 *대체*
  (Kaggle은 속성 한 칸 보강만), Playwright 브라우저 자동화(Selenium으로 대체 또는 ADR 정당화),
  X-Wines 전이학습

## 4. 수업 방법론 체크리스트 → 노트북 출력 매핑 (채점표)

발표 노트북 `notebooks/final_report.ipynb` 의 각 셀이 어느 방법을 시연하는지 1:1 매핑.

| # | 수업 방법 (출처) | 노트북 셀 | 산출물 |
|---|---|---|---|
| 1 | `requests` + 공공데이터 API + `params=` (PDF 7·8) | §1.2 | DataFrame: 국가별 와인 수입량 |
| 2 | `csv` / `pd.read_csv` 적재 (PDF 6) | §1.3 | wine21 records → DataFrame |
| 3 | `requests` + `BeautifulSoup('html.parser')` + `find_all`/`select` (PDF 9) | §1.1 (인용) | wine21 스크래퍼 코드 발췌 + 샘플 출력 |
| 4 | pandas: `loc`/`iloc`/`describe`/`value_counts`/`groupby`/`corr` (PDF 6·10) | §2.1~2.3 | 표 + print |
| 5 | numpy: 벡터화·boolean indexing·axis 인자 (PDF 5) | §2.2, §4.2 | 코드 셀에 주석으로 명시 |
| 6 | `scipy.stats.ttest_ind(a, b, equal_var=False)` + p값 해석 (PDF 10) | §3.1 | **EDA 후 확정될 흥미로운 가설**의 t통계량 + p값 + 한국어 결론 |
| 7 | `df.corr()` + `sns.heatmap(annot=True, cmap='RdBu')` (PDF 10) | §3.2 | 상관행렬 + 히트맵 |
| 8 | matplotlib: hist/scatter/box/bar + title/xlabel/ylabel/legend | §3.3 | 4개 figure |
| 9 | `plt.rc('font', family='Malgun Gothic')` 한글 폰트 | §0 (setup) | 모든 figure 한글 정상 |
| 10 | 각 시각화 뒤 print + 한국어 해석 1문장 | §3 전반 | 각 figure 뒤 markdown 셀 |
| 11 | `np.polyfit` 추세선 (PDF 4) | §3.3 산점도 | 가격↔평점에 추세선 |
| 12 | **sklearn 회귀** (13주차) — EDA 후 확정될 흥미로운 예측 문제 | §3.6, `src/stats/regression.py` | 모델 + 계수/잔류 해석 |
| 13 | **sklearn 분류** (13주차) — EDA 후 확정될 분류 문제 | §3.7, `src/stats/classify.py` | 모델 + feature importance + 혼동행렬 |
| 14 | (가산) 워드클라우드 (11주차) | §3.4 | 시음노트 단어 빈도 + 클라우드 |
| 15 | (가산) GeoPandas/Folium (12주차) | §3.5 | 생산지 지도 |
| 16 | (응용) numpy K-means 직접 구현 | §4.1, `src/mab/kmeans.py` | 페르소나 클러스터 결과 |
| 17 | (응용) numpy MAB 직접 구현 (ε-greedy/UCB1/Gaussian TS) | §4.2~4.3, `src/mab/policies.py` | regret 곡선 |

**Selenium 처리**: 강의는 Selenium 표준이었으나 wine21은 정적이라 BS4만으로 충분 →
`docs/ADR.md` 에 "정적 HTML 확인 후 BS4 채택" 명시 (감점 방어).

**seaborn 사용**: 10주차 heatmap에 등장하므로 §3.2 의 heatmap 1회는 seaborn 사용
(matplotlib only 원칙은 ADR-005 에서 § "예외: 수업 정렬용 seaborn.heatmap 1회 허용" 으로 갱신).

## 5. 노트북 구조 `notebooks/final_report.ipynb`

```
§0  Setup — import, 한글 폰트, 시드 고정, src/ 경로 설정
§1  데이터 수집
    §1.1 wine21 스크래퍼 코드 발췌 + 1건 파싱 결과 출력
    §1.2 공공데이터 API 호출 + 응답 파싱 (KOSIS/관세청)
    §1.3 통합 DataFrame 적재 (records.jsonl, 공공 통계)
§2  정제·EDA
    §2.1 결측치·이상치 처리 (pandas)
    §2.2 numpy 벡터화 패턴 시연 (가격 정규화, boolean indexing)
    §2.3 기술통계 (describe, value_counts, groupby)
§3  통계 분석 + 시각화 (★ 채점 핵심 ★)
    §3.0 EDA 탐색 — 흥미로운 패턴/가설 발굴 (W1 산출물에서 §3.1·§3.6·§3.7 가설 확정)
    §3.1 t검정 — §3.0 에서 발굴한 흥미로운 가설 (10주차 미러링)
    §3.2 상관분석 — df.corr() + heatmap
    §3.3 matplotlib 시각화 4종 (hist, scatter+polyfit, box, bar) + 해석문
    §3.4 (가산) 시음노트 워드클라우드
    §3.5 (가산) 생산지 지도
    §3.6 sklearn 회귀 (13주차) — §3.0 에서 발굴한 예측 문제 + 계수·잔류 해석
    §3.7 sklearn 분류 (13주차) — 등급/라벨 분류 + feature importance·혼동행렬
§4  응용: MAB 취향 탐색 시뮬레이션
    §4.1 페르소나 로딩 + numpy K-means 클러스터링
    §4.2 reward 함수 + MAB 정책 numpy 직접 구현
    §4.3 시뮬레이션 실행 + cumulative regret + 승률 히트맵
§5  결과 정리 + 정직한 한계 + 활용 계획
```

각 셀은 **주석 풍부**, markdown 셀로 해석/결론 명시. 강의 출처(PDF #) 주석에 표기.

## 6. 코드 구조 `src/`

```
src/
├── scraping/       wine21.py, public_data.py, validate.py, schema.py
├── data/           load_catalog.py, preprocess.py
├── stats/          ttest.py, correlation.py, regression.py, classify.py (sklearn 13주차)
├── mab/            kmeans.py, policies.py (ε-greedy, UCB1, Gaussian TS — numpy 직접)
├── simulation/     run.py (페르소나×정책×T=50)
└── viz/            plots.py (matplotlib 헬퍼)
```

원칙: **모든 로직은 src/, 노트북은 호출+시각화** (CLAUDE.md). 노트북에 numpy/loop 알고리즘
코드를 *발췌해서* 보여주는 건 OK (이해도 증명용) — 단 단일 진실은 src/.

## 7. Acceptance Criteria

**Tier 0 (발표·제출 통과 기준):**

```bash
# CI/CD (이미 구축)
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run pytest -q

# 데이터 수집
uv run python -m src.scraping.wine21 broad 100   # 11개국 × 100 = ~1,100병
uv run python -m src.scraping.validate           # 검증 게이트 통과
uv run python -m src.scraping.public_data        # 공공데이터 API 호출 → CSV

# 노트북 실행 (Tier 0)
uv run jupyter nbconvert --to script notebooks/final_report.ipynb --stdout > /dev/null
# §3 의 t검정 p값, 상관행렬, 4개 figure 출력 확인
```

**Tier 1 (시간 허락 시):**
- §4 의 K-means/MAB 시뮬레이션이 §4.3 의 regret 곡선 + 승률 히트맵을 생성
- `uv run pytest tests/test_mab.py -q` — toy bandit sanity 통과

## 8. 산출물 (Deliverables) — 6/24 마감

| 산출물 | 위치 | 비고 |
|---|---|---|
| 발표 슬라이드 (7분) | `results/presentation/slides.pdf` | 6/9 또는 6/11 발표 |
| 프로그램 (ipynb) | `notebooks/final_report.ipynb` | **주석 풍부**, src/ 호출 |
| 보고서 | `results/report/report.pdf` (word/hwp 변환 가능) | 결과화면 캡처 + 후일담 포함 |
| 소스 코드 | `src/`, `tests/` | git 저장소 (sangho24/wine-mab-project) |
| README | 루트 `README.md` | 재현 방법, 수업 방법 → 셀 매핑 |

## 9. 일정 (현실 — 5/27 기준)

| 주차 | 기간 | Tier 0 목표 | Tier 1 목표 |
|---|---|---|---|
| W1 | 5/27 ~ 6/2 | §1·§2·§3 완성 (수집·정제·통계·시각화 본론) | — |
| W2 | 6/3 ~ 6/8 | §3 보강 (해석문·figure 다듬기) | §4 MAB 시뮬레이션 + figure |
| W3 | 6/9 ~ 6/11 | 발표 슬라이드 + 발표 | — |
| W4 | 6/12 ~ 6/24 | 보고서·코드 정리·최종 제출 | (남은 Tier 2 부분 보고서에 한계로 명시) |

## 10. Risk Register

| Risk | 영향 | 완화 |
|---|---|---|
| 스크래핑 차단 | High | 다른 한국 소스 fallback (와인앤모어/비노봇/와인서처), Kaggle은 *대체 금지* — 속성 보강만 |
| 공공데이터 API 키 발급 지연 | Medium | KOSIS는 키 불필요한 통계표 API 우선 사용. 키 필요 시 5/28 즉시 신청 |
| 시간 부족 → Tier 1 미달성 | Medium | Tier 0 우선. Tier 1 미달성은 발표·보고서에 한계로 명시 (점수 손실 최소화) |
| 보상 모델 자의성 지적 | Medium | 발표/보고서 톤을 "설계 *하에서* 관찰" 로 통제. X-Wines 품종→Body/Acidity 프로파일을 grounding 로 인용 |
| 인프라(uv/CI/pytest)가 수업 범위 밖이라 0점 | Low | 이미 들임. 추가 투자 금지. 보고서에서 1줄만 언급 ("재현성 게이트") |

## 11. 평가 방어 한 문장

> 본 프로젝트의 §1~§3은 강의 10주차의 표준 4단 분석(수집→정제→t검정·상관→시각화) 파이프라인을
> 한국 와인 시장 데이터에 적용한 것이며, §4 응용 레이어는 강의가 강조한 numpy 벡터화·boolean
> indexing·axis 인자를 MAB 알고리즘 직접 구현에 적용한 확장입니다.
