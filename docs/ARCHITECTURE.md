# ARCHITECTURE — wine-mab-project

## 디렉토리 구조
- `src/scraping/` — 와인 리테일 사이트 스크래퍼 (`wineandmore.py`, `winesearcher.py` 등). 사이트별 모듈은 동일한 `fetch_catalog() -> list[WineRecord]` 시그니처 준수.
- `src/personas/` — Nemotron 로딩 (`loader.py`), 클러스터링 (`cluster.py`), Persona Translation Layer (`translate_cluster.py`, `translate_llm.py`).
- `src/mab/` — MAB 정책 (`policies.py`: EpsilonGreedy, UCB1, ThompsonSampling). 모든 정책은 동일한 `select_arm(t) -> int`, `update(arm, reward)` 인터페이스.
- `src/simulation/` — Reward function (`reward.py`), 시뮬레이션 러너 (`runner.py`).
- `src/viz/` — matplotlib 시각화 (`regret_curve.py`, `winrate_heatmap.py`, `arm_pulls.py`, `persona_scatter.py`).
- `data/` — git 제외. `raw/` (스크래핑 원본), `processed/` (정제), `personas/` (샘플링된 페르소나).
- `notebooks/` — EDA 및 결과 시각화 호출 전용. 비즈니스 로직 금지.
- `results/figures/` — 발표/보고서용 산출물.
- `phases/` — Harness 프레임워크 step 지시서.

## 데이터 흐름
```
1) Scraping
   웹 사이트 → src/scraping/{site}.py → data/raw/{site}/{YYYYMMDD}/*.jsonl
2) 정제 & 카테고리화
   data/raw/ → src/scraping/normalize.py → data/processed/wines.parquet
   (지역 × 품종 또는 지역 × 가격대 기준 8 ~ 15 카테고리 = MAB arms)
3) Persona Loading
   HuggingFace → src/personas/loader.py → data/personas/sample.parquet
4) Persona Translation
   sample.parquet → src/personas/translate_*.py → data/personas/preferences.parquet
   (지역 가중치, 품종 가중치, 가격 민감도, α)
5) Simulation
   processed/wines + personas/preferences + src/mab/policies
   → src/simulation/runner.py → results/logs/{run_id}.jsonl
6) Analysis & Viz
   results/logs/ → src/viz/*.py → results/figures/*.png
```

## 설계 원칙
- **Reproducibility**: 모든 실행은 seed 고정. CLI 진입점은 `--seed` 받음.
- **No frameworks for the core**: MAB 정책과 K-means는 numpy로 직접 구현 (수업 평가 기준).
- **Module 시그니처는 step 지시서에 명시**된 형태를 유지 — agent가 임의로 바꾸지 않는다.
- **Notebook은 호출만**: 로직은 `src/`. notebook은 import해서 plot 호출.

## 상태 관리
- 시뮬레이션 결과는 `results/logs/{run_id}.jsonl`에 한 줄당 한 step씩 append (run_id, persona_cluster, policy, t, arm_pulled, reward, cumulative_regret).
- 시각화는 logs를 다시 읽어 그린다 — 시뮬레이션과 시각화 분리.

## 외부 의존성
- HuggingFace `datasets` (Nemotron-Personas-Korea, 한 번만 다운로드)
- (선택) Anthropic API — Persona Translation 방법 B 사용 시. `.env`에 키 저장, git에 커밋 금지.

## 패턴
- 사이트별 스크래퍼는 동일 인터페이스 (Strategy 패턴)
- MAB 정책은 동일 인터페이스 (Strategy 패턴)
- Persona Translation 방법 A/B는 동일 출력 스키마
