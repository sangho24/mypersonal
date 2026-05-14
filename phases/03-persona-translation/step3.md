# Step 3 — 방법 B — LLM 기반 개별 매핑 (선택)

## Read first
- `data/personas/sample.parquet` (narrative 컬럼)
- `data/processed/category_final.json` (region/varietal 어휘)
- `docs/ADR.md` ADR-002
- `docs/PRD.md` 4.2절 방법 B

## Goal
페르소나별 narrative + demographic을 Anthropic API에 보내 선호 벡터를 개별 생성. 방법 A 결과와 비교 가능한 동일 스키마.

## Tasks
1. `.env`에 `ANTHROPIC_API_KEY` 저장 (git 제외).
2. `src/personas/translate_llm.py` 생성:
   ```python
   def build_prompt(persona: dict, region_lex: list[str], varietal_lex: list[str]) -> str: ...
   def translate_one(persona: dict, ...) -> dict: ...   # 반환: {region_weights, varietal_weights, price_sensitivity, alpha}
   def translate_batch(df: pandas.DataFrame, out_path: str, *, model: str = "claude-sonnet-4-6", limit: int | None = None) -> pandas.DataFrame: ...
   ```
3. Prompt에 출력 스키마 JSON을 명시하고, 모든 region/varietal 라벨이 어휘 리스트에서 나와야 한다고 강제. JSON 파싱 실패 시 1회 재시도.
4. 결과는 `data/personas/preferences_llm.parquet`로 저장.

## Don't
- 300 페르소나를 동기 루프로 호출하지 말 것. **이유**: 시간 비용. 배치 처리 또는 async 사용 고려. 또는 limit=30으로 일관성 검증부터.
- 출력의 region/varietal 라벨을 검증 없이 그대로 쓰지 말 것. **이유**: LLM이 사전에 없는 라벨을 만들면 후속 매칭 실패. 어휘 리스트에 없으면 reject 후 1회 재시도.
- API 키를 코드에 하드코딩 하지 말 것. **이유**: 보안. `.env` + `python-dotenv` 사용.

## Acceptance Criteria
```bash
# limit=30으로 작게 검증
python -c "
from src.personas.translate_llm import translate_batch
import pandas as pd
df = pd.read_parquet('data/personas/sample.parquet').head(30)
out = translate_batch(df, 'data/personas/_preferences_llm_test.parquet', limit=30)
assert len(out) == 30
print(out.iloc[0])
"
```
스키마 일관성 통과 후 전체 N에 대해 재실행.

## Skip조건
방법 A 결과가 클러스터 해석 가능성·시뮬레이션 안정성 모두 좋으면 이 step은 skip. `phases/index.json`에서 status를 `"skipped"`로 갱신하고 ADR-002에 사유 추가.
