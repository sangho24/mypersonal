# Step 3 — Nemotron-Personas-Korea 로딩 및 샘플링

## Read first
- `docs/PRD.md` 3.2절 (200 ~ 500 페르소나)
- `docs/ARCHITECTURE.md` 데이터 흐름 3번
- HuggingFace 데이터셋 카드: `nvidia/Nemotron-Personas-Korea`

## Goal
HuggingFace에서 데이터셋을 받아 200 ~ 500개 페르소나를 샘플링하고 표준 스키마로 저장.

## Tasks
1. `src/personas/loader.py` 생성:
   ```python
   def load_dataset(cache_dir: str = "data/personas/_hf_cache") -> "datasets.Dataset": ...
   def sample_personas(ds, n: int = 300, seed: int = 42) -> pandas.DataFrame: ...
   ```
2. 샘플 결과를 `data/personas/sample.parquet`로 저장. 컬럼: `persona_id`, `age`, `region`, `occupation`, `income_level`, `narrative`, `raw_attrs` (json 문자열).
3. 와인과 관련성 낮은 페르소나(예: 미성년)를 필터링한 뒤 샘플링한다. 필터 규칙은 `src/personas/loader.py` 안에 명시.

## Don't
- 700만 개를 전부 다운로드해서 메모리에 올리지 말 것. **이유**: 디스크/메모리 폭발. `datasets`의 streaming 또는 `select` 사용.
- 시드 없이 샘플링하지 말 것. **이유**: Reproducibility — 모든 시뮬레이션은 seed 고정.

## Acceptance Criteria
```bash
python -m src.personas.load_smoke
python -c "
import pandas as pd
df = pd.read_parquet('data/personas/sample.parquet')
assert 200 <= len(df) <= 500, len(df)
assert df['persona_id'].is_unique
print(df[['age','region','occupation','income_level']].describe(include='all'))
"
```
