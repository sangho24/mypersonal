# 발표 스피커 노트 — 개인 데이터 디지털 트윈 (5분 + Q&A 1분, rev5)

> 1인칭 한국어 발화 대본. 슬라이드의 figure 가 *보여주는* 수치를 *재인용*하는 방식.
> 총 목표 300초 × 320자/분 × 0.95 buffer ≈ 1,500자.
> rev5 변경: 양/질 narrative 폐기 (데이터 재계산 결과 24m/8m 분리는 코드 하드코딩 산물), 새 발견 = (1) 라벨이 데이터를 자르지 않는다 + 도시 효과의 day-type 의존, (2) Paris 사건의 다채널 시간 위상, Hero = Paris orchestration 시연.

---

## Slide 1: Hook — 6년치 나, 디지털 트윈으로 부팅 (15s)

여러분, 교수님. 오늘 제가 가져온 건 와인 데이터가 아니라 *제 6년치 행동 데이터*입니다. AI 시대가 본격적으로 열리고 취업을 앞두면서, 저는 *나만의 특수성과 능력*을 함께 고민해 줄 디지털 트윈이 필요했습니다. 그 첫 부팅을 5 소스, 7 도구, 1 LLM으로 보여드립니다.

## Slide 2: 배경 — 데이터 과학자 = 세상 보는 안경, 그래서 나부터 (25s)

데이터 과학을 공부한다는 건 *세상을 보는 새로운 안경*을 하나 더 쓰는 일이라고 저는 생각합니다. 그중에서도 *모델링* — 현실을 수식과 알고리즘으로 다시 쓰는 일에 관심이 있었습니다. 그러면 그 안경을 어디에 가장 먼저 들이대고 싶었느냐. 답은 *나 자신*이었습니다. 남의 데이터로 모델을 돌리기 전에 *나부터 분석하고 싶었습니다*. 그러자 자연스럽게 다음 질문이 따라왔습니다 — "나를 설명하는 데이터는 도대체 어디에 있을까?" 검색해 보니, 6년 가까이 들고 다닌 아이폰 안에 Apple Health export 216 MB와 Google Timeline JSON이 잠들어 있더군요. *재료는 이미 6년치가 쌓여 있었고*, 안경을 들이댈 준비가 끝나 있었습니다.

## Slide 3: 차용 vs 신규 + 와인 1줄 회고 (25s)

먼저 솔직하게 보고드리겠습니다. 학기 초 wine-mab 트랙으로 시작했지만 *나부터 분석하고 싶다*는 동기와 정합이 더 강한 personal-data 트랙으로 pivot했고, *와인은 이 슬라이드에서 마지막으로 등장합니다*. *차용*은 (1) wine-mab의 numpy UCB1 한 모듈을 T7으로 그대로 포팅, (2) 강의 표준 라이브러리 scipy.stats, numpy, matplotlib, (3) Apple과 Google 공식 export 포맷 스키마, (4) Anthropic SDK 네 가지입니다. *이번 기말에 새로 한 것*은 src/personal 패키지 전체 — anchors.py (단일 진실 출처) 와 data.py (loader) 부터 7개 도구의 LLM 호출 가능 wrap, tool_use 오케스트레이터, 3개 finding 모듈, 그리고 4항목 rubric 평가 기준과 figure 5종 및 발표 산출물입니다. 한 줄로 — *알고리즘 한 줄은 빌렸지만 도구화와 LLM 결합은 모두 새로 짰습니다*.

## Slide 4: 데이터 수집 + raw 정제 (35s)

실제 분석에 들어간 데이터는 두 source 입니다. Apple Health 건강앱에서 export.xml 216 MB 한 파일에 walking 4 metric, 일별 활동량 4 metric, Workout 60건, Headphone audio 60K건이 모두 통합되어 있어 별도 추출이 필요 없었고, Google Maps Timeline은 Takeout으로 JSON 한 파일입니다. GPX workout-routes 10건도 같이 받았지만 모두 2022년 군 복무 시기 1-2km 짧은 세션이라 본 분석 범위 밖이고, 한계 슬라이드에 정직하게 인정합니다. 정제 결정은 다섯입니다. 첫째, 216 MB XML을 한 번에 메모리에 올리면 터지므로 iterparse 로 record 단위 스트리밍 파싱하고 elem.clear()로 즉시 비워서 *50 MB 이내*로 처리. 둘째, 일별 9 metric — steps, distance_km, active_energy_kcal, flights, walking_speed, step_length, asymmetry, double_support, audio_max_dB — 를 groupby 압축. 셋째, UTC를 Asia/Seoul로 일괄 변환하고 좌표는 *저장하지 않으며* 도시 bounding box로만 분류. 넷째, sourceName 필터로 iPhone과 Nike Run Club stepCount 더블 카운트 차단, iOS 14 이전 gait 결측은 NaN 그대로 보존. 다섯째, baseline window 는 pre-MIL 2020년 9월부터 2021년 10월까지로 src/personal/anchors.py 한 곳에서 정의하고 모든 모듈이 import 합니다 — 하드코딩 충돌 방지.

## Slide 5: 내 인생 굵직한 타임라인 (25s)

발견을 발화하기 전에, 그래프에 마커가 찍혀 있습니다 — 제 6년치 인생 chapter 입니다. 2019년 3월 학부 입학, 2020년 9월 iOS 14 gait sensor 도입, 2021년 10월 baseline window 종료, 2021년 11월 15일 군 입대, 2023년 5월 14일 전역, 2023년 10월 무릎 부상, 2024년 1월 ACL 수술, 2024년 12월부터 2025년 6월까지 프랑스 Sorbonne 교환학생, 2025년 7월부터 한국 재정착. 핵심은 — 제 데이터는 *그냥 시계열*이 아니라 *인생 chapter가 박힌 시계열*이고, 다음 슬라이드 발견 1에서 *이 chapter들이 진짜 데이터 분기점인지 데이터가 직접 검증* 합니다.

## Slide 6: Research Question + "유의미함" 의 정의 (정직한 한정) (30s)

그래서 제가 던지는 질문은 — *내 6년치 개인 행동 로그에서, 단일 지표 직관만으로는 보이지 않는 유의미한 패턴을 발견할 수 있는가?* 입니다. 방법은 분리해 두었습니다 — 7개 통계 도구를 LLM이 상황 따라 조합 호출하는 오케스트레이터 구조. *유의미함*은 4항목 rubric 으로 명문화 — ① 통계 분리도 (p, effect size, n 셋 다 보고), ② 단일지표 모순성 (합계 단독으로는 안 보이거나 반대 결론), ③ 채널 교차 일관성 (최소 2 채널 재현), ④ 행동 가능성 (개입 권유 한 줄). false positive 감소는 별도 기준이 아니라 ②의 한 측정 방법입니다. 한계는 정직하게 — N=1, ground truth 라벨 없음, 시나리오 1개, F1 미산출, *qualitative defense* 만 청구합니다.

## Slide 7: 발견 1 — 자전적 라벨이 데이터를 자르지 않는다 / 도시 효과는 단순하지 않다 (45s)

발견 1은 두 가지가 한 메시지로 묶입니다. 첫째 — 9채널 일별 K-means 가 학부 baseline (n=343일) 과 군복무 (n=435일) 를 *같은 cluster c0* 에 묶었습니다. c0 비중이 학부 61.2 퍼센트, 군복무 60.0 퍼센트, 차이 1.2 퍼센트 포인트로 사실상 동일 분포입니다. *군복무가 인생 분기점*이라는 자전적 라벨이 데이터 차원에서는 분기되지 않습니다. 둘째 — Paris와 Seoul_rec 일일 걸음 차이가 전체로는 d=0.50 으로 유의하지만, Maps day-category 로 stratify 하면 home_only 와 outing 에서는 d 가 1.04 와 1.36 으로 Paris 가 훨씬 강하고, routine 에서는 차이 없음 (p=0.08) 이고, 놀랍게도 *explore-day 에서는 Seoul 이 Paris 보다 더 걷습니다* — d=-0.80 입니다. 도시 효과가 한 방향이 아니라 day-type 별로 방향과 강도가 다 다릅니다. 단일 지표 평균이 이 풍부한 패턴을 다 가리는 거고, rubric ②(모순성) 와 ③(교차) 를 한 번에 통과합니다.

## Slide 8: 발견 2 — 'Paris' 라는 한 사건이 세 채널에 다른 위상으로 (45s)

발견 2는 Paris 라는 한 사건의 *다채널 해부* 입니다. 채널 1 — Paris 체류 중 활동량 3채널이 일제 상승합니다. 직전 Seoul 6개월 대비 steps +28 퍼센트 (d=0.38), distance +35 퍼센트 (d=0.44), flights +26 퍼센트 (d=0.25). 채널 2 — 청취량이 Paris 6개월 동안 단조 증가합니다. 12월 71분 일에서 6월 251분 일로 *3.5배*, Spearman ρ=0.86 으로 매우 강한 단조성. *적응할수록 음악 의존이 줄어든다*는 가설의 정확히 반대 방향입니다. 채널 3 — gait remodel 과 능동 탐색은 *Paris 자체가 아니라 귀국 후에 더 강하게 출현* 합니다. Seoul_rec 의 walking_speed 와 step_length 가 baseline 대비 d=0.85 와 1.15, double_support 는 d=-1.30 으로 모두 p<0.001 입니다. Maps 의 Searched Address 능동 탐색은 Paris 후반 1/3 에 11건 폭발했습니다 — early 0, mid 5, late 11. 세 채널이 같은 사건의 다른 위상이라는 게 핵심이고, 이게 다음 슬라이드 Hero 시연으로 바로 이어집니다.

## Slide 9: Vision — 디지털 트윈 + 함께 만들 분 (30s)

AI 시대가 본격적으로 열리고 취업을 앞두면서 나만의 특수성과 능력이 무엇인지 진지하게 고민하게 됐습니다. 오늘 보여드린 *7개 도구와 LLM 오케스트레이터*는 그 고민을 함께 해 줄 디지털 트윈의 첫 부팅 단계입니다. 학교 프로젝트로 끝내지 않고, 6년치 행동 데이터 위에서 천천히 자라나서 *내가 모르는 내 패턴을 먼저 짚어 주는 비서*로 키우는 게 다음 단계입니다. Apple Health export 한 파일과 7 tool, 1 LLM 이면 충분히 시작됩니다. 이 취지에 공감하신다면 학교를 넘어 함께 만들어 갑시다.

## Slide 10: Hero S1 — 동일 trigger 에 도구 단독 답 vs 조합 답 (50s)

이 슬라이드가 클라이맥스입니다 — 평가 기준의 실증. 동일한 trigger 인 *"2025-06 Paris 효과 어땠어"* 에 두 run 을 나란히 보겠습니다. *baseline run* — T1 만 단독 호출하면 Paris 평균 9196 vs pre-Paris Seoul 평균 7161, Welch t=3.71 p=0.0002 d=+0.38 한 숫자를 보고 LLM 이 *"Paris 에서 일일 걸음수가 +28% 증가, 더 활동적이었음"* 한 줄로 끝납니다. *단일 채널 false positive* — 활동량 한 축만 보니 Paris=긍정적 사건이라는 결론. *full run* — T1 결과를 본 LLM 이 plan 단계에서 T4 audio 와 T2 city compare 와 T3 baseline z-score 를 *추가로* 호출합니다. T1 으로 활동량 3채널 상승, T4 로 청취량 3.5배 단조 증가, T2 와 T3 로 귀국 후 gait remodel d=0.85에서 1.30 까지, Maps explore-day 폭발을 모두 잡고, 합성 답은 *"Paris=원료 투입 trigger, 귀국 후=가공 완료의 2단계 구조"* 가 됩니다. *도구 조합이 도구 합집합이 아니라 출력을 잇는 것*이 본질입니다. rubric 4항목 모두 통과합니다.

## Slide 11: 한계 + 닫는 말 (Q&A 진입) (30s)

마지막 정직한 한정 — N=1, sensor 결손, city-level only, LLM hallucination 정규식 가드. 결정적으로 Apple Watch 가 없어 HeartRate 와 HRV 와 VO2Max 와 SleepAnalysis 채널이 전부 0건이라 *도시 스트레스 회복*같은 자율신경 가설은 본 데이터로 답할 수 없습니다. Google Timeline 은 2025년 2월 이후 15개월치만 커버해서 semantic 정보는 Paris 와 Seoul_rec window 에만 한정 적용됩니다. ACL 부상일 ±2주 와 Paris 일자 ±1주 추정 가능하고, day-type 자체가 도시에 의해 부분 결정되는 동어반복 가능성도 인정합니다. precision/recall/F1 은 산출하지 않은 qualitative defense 입니다. 그래도 *오케스트레이션이라는 방향*은 확실합니다. 감사합니다 — 질문 받겠습니다.
