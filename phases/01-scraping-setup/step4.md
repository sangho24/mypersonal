# Step 4 — 카테고리 후보 도출 및 ADR-001 검증

## Read first
- 직전 step의 결과 `data/raw/wineandmore/{YYYYMMDD}/records.jsonl`
- `docs/PRD.md` (8 ~ 15 카테고리 = MAB arms)
- `docs/ADR.md` ADR-001

## Goal
샘플 50병의 분포를 보고 (지역 × 품종) 또는 (지역 × 가격대) 어느 축이 더 균형 있게 8~15 카테고리로 나뉘는지 결정. ADR-001을 갱신하거나 확정.

## Tasks
1. `notebooks/01_categorize_eda.ipynb` 생성. records.jsonl을 읽어:
   - 지역별 빈도 막대그래프 (matplotlib)
   - 품종별 빈도 막대그래프
   - 가격 분포 히스토그램 (3 ~ 5 구간)
   - (지역 × 품종) 교차표 히트맵
   - (지역 × 가격대) 교차표 히트맵
2. 카테고리 8~15개 후보를 정해 `data/processed/category_candidates.json`에 저장. 형식: `[{"id": 0, "name": "보르도-레드", "rule": {"region": "Bordeaux", "varietal_group": "red"}}, ...]`
3. `docs/ADR.md`에 결정을 `ADR-001 — 결정` 아래 한 줄 추가: "카테고리 축은 {지역×품종 / 지역×가격대}로 확정. 사유: ..."

## Don't
- 50병만 보고 카테고리를 너무 잘게 쪼개지 말 것. **이유**: 본 수집(1,500병) 시 빈 arm 발생 위험. 50병에서 최소 2 ~ 3건이 들어가는 축을 골라야 본 수집에서 안정.

## Acceptance Criteria
```bash
test -f data/processed/category_candidates.json
python -c "import json; cs = json.load(open('data/processed/category_candidates.json')); assert 8 <= len(cs) <= 15, len(cs); print(len(cs), 'categories')"
```
ADR.md의 ADR-001에 카테고리 축 결정 한 줄이 추가되어 있어야 한다.

## Phase exit
이 step 완료 시 `phases/index.json`에서 `01-scraping-setup.status`를 `"completed"`로 업데이트한다.
