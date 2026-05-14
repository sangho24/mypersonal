# Step 4 — 방법 선택 또는 비교, ADR-002 갱신

## Read first
- `data/personas/preferences.parquet` (방법 A)
- `data/personas/preferences_llm.parquet` (방법 B, 있을 경우)
- `docs/ADR.md` ADR-002

## Goal
시뮬레이션에 어느 preference set을 쓸지 결정. 두 방법을 비교한다면 비교 기준을 문서화.

## Tasks
1. 다음 비교 분석을 `notebooks/04_method_compare.ipynb`에 작성:
   - 두 방법의 region_weights, varietal_weights 분포 차이 (KL divergence 또는 코사인 유사도)
   - 두 방법의 alpha 분포 비교 (히스토그램)
   - 동일 클러스터 안에서 LLM 매핑의 분산 — 클러스터 가정의 타당성 검증
2. 결정 한 줄을 ADR-002에 추가 — "시뮬레이션은 방법 X를 메인 사용. 비교 실험은 phase 05에서 별도 run으로 진행" 형태.
3. 시뮬레이션 진입점이 읽을 canonical 경로를 `data/personas/preferences.parquet`로 고정 (방법 B를 쓰기로 했다면 `preferences_llm.parquet`를 이 이름으로 복사).

## Don't
- 데이터를 보지도 않고 방법 B가 "더 좋을 거"라고 가정하지 말 것. **이유**: 분산이 크거나 어휘 일관성이 떨어지면 시뮬레이션 노이즈만 키움.

## Acceptance Criteria
```bash
test -f data/personas/preferences.parquet
# ADR.md에 "ADR-002 결정 갱신" 또는 "결정 확정" 한 줄이 추가되어 있어야 함
grep -q "ADR-002" docs/ADR.md
```

## Phase exit
`phases/index.json`의 `03-persona-translation.status`를 `"completed"`로.
