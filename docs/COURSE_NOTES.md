# 빅데이터컴퓨팅(2026-1학기, 서경희 교수) 강의 정리

기말 프로젝트 채점 방어를 위해 9개 강의자료(PDF 2~10) + 실라버스 + 학생 실습 노트북에서
실제로 다룬 기법/라이브러리/예제만 추출. 추측·일반론 없음. 출처 파일: `/Users/sangho/Desktop/빅데이터컴퓨팅/`.

## 평가 비중
중간 35 / 기말 35 / **프로젝트 10** / 과제 15 / 참여 5. 프로젝트는 "본인 관심 분야 빅데이터를
분석하는 빅데이터 컴퓨팅 산출물(프로그램) 발표". 보고서는 word/hwp + 소스 + 결과화면 캡처
+ 후일담.

## 주차별 진행 (실라버스 + 실제 PDF 매칭)

| 주차 | 주제 | PDF |
|---|---|---|
| 1~2 | 빅데이터 개요·파이썬 기초 | 2 |
| 3 | 기온 공공데이터 (csv + matplotlib) | 3 |
| 4 | 인구 공공데이터 (csv + matplotlib + polyfit) | 4 |
| 5 | NumPy + 인구데이터 응용 | 5 |
| 6 | pandas | 6 |
| 7 | 크롤링 1 — 네이버 API + 공공데이터 API | 7, 8 |
| 8 | 중간고사 | — |
| 9 | 크롤링 2 — BeautifulSoup + Selenium | 9 |
| 10 | 기술통계 + 상관 (와인·타이타닉) | 10 |
| 11 | 텍스트 단어빈도, 워드클라우드 | (예정) |
| 12 | GeoPandas / Folium 지리시각화 | (예정) |
| 13 | 회귀·분류 (sklearn — auto-mpg / 유방암 / 붓꽃) | (예정) |
| 14~15 | 프로젝트 발표 | — |

## 라이브러리 — 강의가 *실제로 가르친* 것

- **기본**: `csv`, `open`, `json`, `random`, `math`, `time`, `urllib.request`/`urllib.parse`
- **수치/표**: `numpy`, `pandas`
- **시각화**: `matplotlib.pyplot` (단일·고정), 한글 폰트는 `plt.rc('font', family='Malgun Gothic')`
- **수집**: `requests`, `bs4.BeautifulSoup('html.parser')`, `selenium.webdriver.Chrome`
- **통계**: `scipy.stats.ttest_ind`
- **EDA 보강(주차10)**: `seaborn` (`heatmap`, `pairplot`, `countplot`, `histplot`, `violinplot`)
- **예정(주차13)**: `sklearn` — 회귀/분류

❌ 등장하지 않음: `sklearn.cluster`, `sklearn.metrics`, RL/MAB, `playwright`, `datasets`(HF),
`huggingface_hub`, `pytest`/`pyright`(테스팅), MLflow, LangChain.

## 강의 스타일의 핵심 패턴

1. **csv.reader → 리스트/dict → for 루프 직접 집계 → matplotlib**가 1~4주차 표준. pandas 없이
   순수 파이썬으로 집계하는 패턴을 *명시적으로* 가르침.
2. pandas는 5주차부터. `read_csv` → `loc`/`iloc` → `describe`/`value_counts`/`corr` 수준.
   `groupby`는 10주차에 본격 등장. **`merge`/`pivot_table`/`melt`는 강의에 안 나옴.**
3. numpy는 "벡터화·브로드캐스팅·boolean indexing·axis 인자"가 강조점. 알고리즘 직접 구현은
   `np.polyfit`(1·2·3차 회귀선)과 유클리드 거리(`np.sum((a-b)**2)`)가 한계.
4. 크롤링 권장 위계 — **공공데이터 API > 민간 API > BS4 정적 > Selenium 동적**. PDF 7·8이
   API+pandas+matplotlib end-to-end 파이프라인을 가장 정성껏 시연. **공공데이터 API는 분명한
   채점 포인트.**
5. 통계분석(10주차)의 표준 결과물 = **"groupby 두 집단 → describe 비교 → `ttest_ind(equal_var=False)`
   → `df.corr()` → `heatmap(annot=True, cmap=RdBu)`"** 4단 + 각 그래프 뒤 해석 1문장
   ("p<0.05이므로 유의미한 차이", "alcohol↔quality는 0.44 양의 상관").
6. 시각화 결과물은 그래프 뒤에 **수치 요약 print + 한국어 해석문 1줄**이 짝이 됨 (실습과제 17 패턴).
7. 인코딩은 `cp949` 표준 (csv 저장 시).

## 강의가 *기대하는 학생 수준*

- numpy/pandas는 **벡터화된 표준 메서드 조합** 수준. 강의 자체에서 직접 알고리즘 구현은
  거의 없음 — 가장 알고리즘다운 게 유클리드 거리 한 줄.
- 통계 결과물은 **모델링·예측이 아니라 요약·해석·시각화**. p값, 상관계수, 박스플롯, 히트맵.
- 회귀·분류는 13주차 sklearn으로 한 번 등장 — 직접 구현 X, `sklearn` 호출 수준.

## 와인-MAB 프로젝트와의 정합/불일치

**정합:**
- `requests` + `BeautifulSoup` 기반 wine21 스크래핑은 강의 스타일과 1:1.
- matplotlib only는 강의와 정확히 일치.
- pandas로 정제 → 시각화는 강의 4단 파이프라인 그대로.

**불일치 (=감점 리스크):**
- **공공데이터 API**: 강의가 가장 깊게 시연한 사례인데 프로젝트에 한 건도 없음.
- **`scipy.stats.ttest_ind` + `df.corr()` + `heatmap`**: 10주차의 그 4단 파이프라인이 프로젝트
  본론에 없음. 현재 계획서엔 "기초 EDA" 한 줄로만 뭉뚱그려져 있음.
- **Selenium**: 강의는 Selenium을 동적 페이지 표준으로 가르쳤는데 프로젝트는 Playwright. ADR에
  정당화 필요 (또는 Selenium으로 전환).
- **MAB·K-means 직접 구현**: 강의 평균 수준을 *상회*. 보고서에서 강의가 강조한 벡터화·
  boolean indexing·axis 인자가 알고리즘 코드에 사용된 지점을 *명시*하지 않으면
  "수업 도구와 무관한 것"으로 읽힐 위험.
- **HuggingFace `datasets`, X-Wines, vivino**: 강의 어디에도 안 나옴. 채점 0점 + 시간 소모.
- **`pytest`/`pyright`/CI/uv**: 인프라는 채점 0점 — 이미 들인 비용은 두되 더 들이지 말 것.
- **`seaborn`**: 10주차 통계분석에 등장. 보고서에 1~2번 쓰면 강의 정렬 신호로 가산.

## 기말 프로젝트에 *반드시* 들어가야 할 메서드 체크리스트

채점이 메서드 단위라면 이 리스트가 채점표:

- [ ] **공공데이터 API** 호출 (`requests.get` + `params=` + 인증키) — PDF 7·8
- [ ] `csv` 모듈 또는 `pd.read_csv` 적재
- [ ] `requests` + `BeautifulSoup('html.parser')` + `find_all`/`select` — PDF 9
- [ ] (선택) Selenium 동적 페이지 — PDF 9
- [ ] pandas: `loc`/`iloc`, `describe`, `value_counts`, `groupby('x')['y'].agg([...])`, `corr`
- [ ] numpy: 벡터화·boolean indexing·axis= 인자 — PDF 5
- [ ] **`scipy.stats.ttest_ind(a, b, equal_var=False)`** + p-value 해석 — PDF 10
- [ ] **`df.corr()` + `sns.heatmap(annot=True, cmap='RdBu')`** — PDF 10
- [ ] matplotlib: 히스토그램·산점도·박스플롯·막대 + `title/xlabel/ylabel/legend`
- [ ] `plt.rc('font', family='Malgun Gothic')` 한글 폰트
- [ ] 각 시각화 뒤 **수치 print + 한국어 해석 1문장**
- [ ] (가산) `np.polyfit` 추세선 — PDF 4
- [ ] (가산) 워드클라우드/단어 빈도 (11주차) — 와인 시음노트에 적용 가능
- [ ] (가산) GeoPandas/Folium 지도 (12주차) — 와인 생산지 매핑 가능
- [ ] (가산) `sklearn` 회귀/분류 (13주차) — 가격 회귀나 등급 분류
