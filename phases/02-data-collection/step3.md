# Step 3 — Nemotron 페르소나 로딩 + X-Wines 평점 매트릭스 준비

## Read first
- HuggingFace 데이터셋 카드: `nvidia/Nemotron-Personas-Korea`
- `data/raw/xwines/drive/last/XWines_Full_21M_ratings.csv` (또는 Slim 150K — 개발용)
- `docs/ADR.md` ADR-006 (취향 아키타입은 X-Wines 평점 클러스터링 — 클러스터링 자체는 phase 03)

## Goal
두 가지 raw material 을 준비한다 — (1) Nemotron 한국인 페르소나 200~500명 샘플,
(2) X-Wines user×wine 평점 매트릭스. **클러스터링·매핑은 phase 03 의 일** — 여기서는
로딩·샘플링·정제까지만.

## Tasks
1. `src/personas/loader.py` 생성:
   ```python
   def load_personas(streaming: bool = True) -> "datasets.Dataset": ...
   def sample_personas(ds, n: int = 300, seed: int = 42) -> list[dict]: ...
   ```
   - 와인 취향과 연결될 컬럼을 보존: `uuid, age, sex, occupation, education_level,
     bachelors_field, marital_status, province, persona, culinary_persona`.
   - 미성년 등 와인 무관 페르소나 필터 (필터 규칙은 loader.py 안에 명시).
   - 결과를 `data/processed/personas.jsonl` 로 저장 (시드 고정).
2. `src/personas/xwines_ratings.py` 생성:
   ```python
   def load_ratings(slim: bool = True) -> "numpy.ndarray | pandas.DataFrame": ...
   ```
   - X-Wines 평점 CSV(`UserID, WineID, Rating`) 로딩. 개발은 Slim(150K), 본 클러스터링은 Full.
   - user×wine 희소행렬 형태로 `data/processed/xwines_ratings.parquet` 저장.
3. `src/personas/load_smoke.py` 생성 — 페르소나 샘플 개수·컬럼·평점 매트릭스 shape 출력.

## Don't
- Nemotron 전체(수백만)를 메모리에 올리지 말 것. **이유**: `datasets` streaming 또는 `select`.
- X-Wines Full(21M, 1.1GB)을 개발 단계에서 매번 로딩하지 말 것. **이유**: 느림. 개발은
  Slim(150K)으로, 최종 클러스터링만 Full.
- 시드 없이 샘플링 금지. **이유**: Reproducibility — 모든 시뮬레이션 seed 고정 (ADR 철학).

## Acceptance Criteria
```bash
uv run python -m src.personas.load_smoke
uv run python -c "
import json
ps = [json.loads(l) for l in open('data/processed/personas.jsonl')]
assert 200 <= len(ps) <= 500, len(ps)
assert len({p['uuid'] for p in ps}) == len(ps), 'uuid 중복'
need = {'age','occupation','education_level','culinary_persona'}
assert need <= set(ps[0]), '필수 컬럼 누락'
print(len(ps), 'personas OK')
"
uv run python -c "
import pandas as pd
r = pd.read_parquet('data/processed/xwines_ratings.parquet')
print('ratings shape:', r.shape)
assert len(r) >= 100000
"
```
페르소나 200~500명(uuid 유니크, 필수 컬럼 보유), 평점 매트릭스 10만 행 이상.
