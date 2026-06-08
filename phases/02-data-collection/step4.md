# Step 4 — 통합 EDA

## Read first
- `data/processed/wine_catalog.jsonl`, `data/processed/arms.json`
- `data/processed/personas.jsonl`, `data/processed/xwines_ratings.parquet`
- `docs/ADR.md` ADR-005 (matplotlib only)

## Goal
세 데이터 출처가 합쳐진 결과를 시각화해 — arm 이 잘 채워졌는지, body/acidity 조인이
타당한지, 페르소나 분포가 다양한지 — 검증하고 보고서 도입부 figure 후보를 만든다.

## Tasks
1. `notebooks/02_eda.ipynb` 생성. 다음 plot (전부 matplotlib):
   - arm별 와인 개수 막대그래프 (빈 arm 없는지)
   - arm별 가격(price_krw) 박스플롯
   - body vs acidity 산점도 (점 색 = country_group) — X-Wines 조인 결과 sanity check
   - 페르소나 연령 분포 히스토그램
   - 페르소나 직업·교육 수준 분포 막대그래프
   - X-Wines 평점 분포 히스토그램 (1~5, 분산이 있는지)
2. 모든 figure 는 `results/figures/eda/` 에 저장.
3. notebook 마지막 셀에 한 줄 인사이트 (예: "arm별 와인 30+ 확보, body는 country_group 별로
   분리됨 → 보상함수 설계에 쓸 만함").

## Don't
- seaborn 사용 금지. **이유**: ADR-005 — matplotlib only.
- 시뮬레이션 로직을 notebook 에 작성하지 말 것. **이유**: CLAUDE.md — notebook 은 호출·시각화 전용.

## Acceptance Criteria
```bash
ls results/figures/eda/*.png | wc -l   # >= 6
uv run jupyter nbconvert --to script notebooks/02_eda.ipynb --stdout > /dev/null   # 실행 가능성
```

## Phase exit
이 step 완료 시 `phases/index.json` 의 `02-data-collection.status` 를 `"completed"` 로,
`phases/02-data-collection/index.json` 의 각 step status 도 갱신.
CI 게이트(L1~L5) 통과 확인 후 phase 03 으로.
