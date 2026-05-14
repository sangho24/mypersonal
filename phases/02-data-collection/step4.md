# Step 4 — 기초 EDA

## Read first
- `data/processed/wines_labeled.parquet`
- `data/personas/sample.parquet`

## Goal
와인 카탈로그와 페르소나 양쪽의 기초 분포를 시각화하여 발표/보고서 도입부에 들어갈 figure 후보를 만든다.

## Tasks
1. `notebooks/02_eda.ipynb` 생성. 다음 plot:
   - 카테고리별 와인 개수 막대그래프
   - 카테고리별 평균 가격 박스플롯
   - 가격 vs 평균 평점 산점도 (점 크기 = rating_count)
   - 페르소나 연령 분포
   - 페르소나 지역 분포 (지도 없이 막대로 충분)
2. 모든 plot은 `results/figures/eda/`에 저장.
3. notebook 마지막 셀에 한 줄짜리 인사이트 노트 작성.

## Don't
- seaborn 사용하지 말 것. **이유**: ADR-005 — matplotlib only.

## Acceptance Criteria
```bash
ls results/figures/eda/*.png | wc -l   # >= 5
jupyter nbconvert --to script notebooks/02_eda.ipynb --stdout > /dev/null   # 실행 가능성 확인
```

## Phase exit
이 step 완료 시 `phases/index.json`의 `02-data-collection.status`를 `"completed"`로.
