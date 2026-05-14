# CLAUDE.md

이 파일은 Claude Code가 이 저장소에서 작업할 때 참고하는 프로젝트 가이드입니다.
구현은 **Harness 프레임워크** 워크플로우를 따릅니다 (참고: jha0313/harness_framework).

## Project Information
- **Project Name:** wine-mab-project
- **주제:** 한국 와인 시장에서의 합리적 취향 탐색 전략 시뮬레이션
- **저자:** 20200572 엄상호
- **수업:** 빅데이터 컴퓨팅 (기말 프로젝트)

## Technology Stack
- **Language:** Python 3.10+
- **Scraping:** `requests`, `beautifulsoup4`, `playwright` (동적 페이지 fallback)
- **Data:** `numpy`, `pandas`
- **ML:** numpy 기반 직접 구현 (K-means, MAB 정책 — `sklearn` 사용 금지)
- **Visualization:** `matplotlib` only (seaborn, plotly 금지)
- **External Data:** HuggingFace `datasets` (nvidia/Nemotron-Personas-Korea)
- **(선택) LLM 매핑:** `anthropic` SDK — Persona Translation Layer 방법 B 사용 시

## Architecture Rules
- **CRITICAL:** "모든 시뮬레이션 로직은 `src/` 패키지 안에서만 정의한다. notebook은 호출 및 시각화 전용." (Reproducibility 보장)
- **CRITICAL:** "스크래핑 결과는 반드시 `data/raw/{site}/{YYYYMMDD}/` 경로에 원본 그대로 저장한 뒤, 정제는 `data/processed/`로 분리한다." (재정제 가능성 보장)
- **CRITICAL:** "MAB 알고리즘과 K-means는 외부 라이브러리 없이 numpy로 직접 구현한다." (수업 평가 기준 — 직접 구현이 핵심)
- Standard: 모듈은 `scraping/`, `personas/`, `mab/`, `simulation/`, `viz/`로 분리
- Standard: 타입 힌트와 docstring은 public 함수에 한정해서 작성

## Development Process
- **CRITICAL:** "각 phase는 `phases/{phase}/step{N}.md` 지시서에 따라 순서대로 진행한다. step을 건너뛰지 않는다."
- **CRITICAL:** "step 실행 후 AC(acceptance criteria)에 명시된 커맨드가 실패 없이 통과해야 다음 step으로 넘어간다."
- 결정사항은 `docs/ADR.md`에 기록 (특히 방법 A/B 선택 같은 분기 결정)
- 커밋 메시지: conventional commits 형식 (feat:, fix:, docs:, chore:, data:)
- 데이터 수집 결과는 git에 커밋하지 않는다 (`.gitignore`로 제외 — `data/raw/`, `data/processed/`)

## Available Commands
패키지 관리는 **uv** (pyproject.toml + uv.lock). pip / requirements.txt 사용 금지.
```bash
# 환경 세팅 (.venv 자동 생성, python 3.12 고정)
uv sync

# 코드 품질 게이트 (CI 와 동일 — .github/workflows/ci.yml)
uv run ruff check .          # 린트
uv run ruff format --check . # 포맷
uv run pyright               # 타입 검사
uv run pytest -q             # 단위 테스트 + 데이터 검증 로직

# 데이터 검증 게이트 — 크롤링 결과가 WineRecord 테이블대로 뽑혔는지
uv run python -m src.scraping.validate   # 최신 records.jsonl 검증 (통과 0 / 실패 1)

# 단위 검증 (각 phase의 AC가 호출)
uv run python -m src.scraping.smoke_test    # phase 1
uv run python -m src.personas.load_smoke    # phase 2
uv run python -m src.mab.verify             # phase 4 (MAB 알고리즘 sanity check)
uv run python -m src.simulation.run --quick # phase 5 quick run
```

## Subagent 오케스트레이션 룰
병렬화 가능한 작업이 들어오면 **반드시 subagent를 적극 활용**한다. 메인 컨텍스트를 보호하고 처리량을 늘리기 위함.

### 언제 subagent를 스폰하는가
- **독립 정찰** — 여러 후보 사이트/소스를 동시에 살펴봐야 할 때 (예: wine21, winenara, vivino 동시 정찰)
- **다중 도구 시도** — 한 사이트를 requests / Playwright / 다른 UA 등 여러 방식으로 동시에 검증할 때
- **광범위 검색** — codebase 또는 데이터에서 3개 이상 위치를 cross-check 할 때 (`Explore` agent)
- **무거운 분석 / 리서치** — 결과 요약만 메인 컨텍스트에 남기고 raw output은 격리

### 어떻게 스폰하는가 (오케스트레이션 룰)
1. **단일 메시지에 N개의 Agent 도구 호출을 묶는다** — 의존성이 없으면 반드시 병렬. 순차 호출 금지.
2. **에이전트 타입을 골라쓴다** — 읽기만 하면 `Explore`, 코드 작성을 시키면 `general-purpose`, 설계는 `Plan`.
3. **자기완결적 프롬프트** — 각 subagent는 이 대화의 컨텍스트를 모름. 목적·읽어야 할 파일·예상 산출물·길이 제한을 프롬프트에 포함.
4. **결과 집계는 메인 에이전트가** — subagent 결과는 메인에서 비교/머지. subagent끼리 통신 금지.
5. **scope 제한** — phase 한 개를 통째로 subagent에 위임하지 않는다. step 단위가 적정 granularity.

### CI 게이트 (phase 전환 조건)
phase의 모든 step `status == "completed"`로 넘기기 전 다음을 통과해야 한다:
- **L1 — 정적 검사**: `python -m py_compile $(git ls-files '*.py')` 모든 .py가 syntax-clean
- **L2 — 모듈 임포트**: `python -c "import src.scraping, src.personas, src.mab, src.simulation, src.viz"` 모든 패키지 임포트 가능
- **L3 — step AC**: 해당 phase의 모든 step.md 안 AC 블록의 커맨드가 종료 코드 0
- **L4 — phase smoke**: 해당 phase에 명시된 smoke entrypoint (`src/{module}/smoke_test.py` 등) 통과
- **L5 — 메타데이터 갱신**: `phases/index.json` + `phases/{phase}/index.json`에 status 반영, ADR이 분기/결정사항 반영

L1~L5 중 하나라도 실패하면 phase는 `"blocked"` 또는 `"error"`로 두고, 메인 에이전트가 root cause를 진단한 뒤 재실행. 실패를 우회(--no-verify 류, AC를 무력화하는 mock) 금지.

### 스폰 예시 (이 프로젝트에서)
- phase 01 step1: `Explore` × 2 (wine21 구조 정찰 / winenara 구조 정찰) — 단일 메시지, 병렬
- phase 02 step1: 한 시점에 두 사이트에서 동시 수집할 일이 생기면 사이트별 subagent 2개 + 메인에서 머지
- phase 03 step3: 방법 B(LLM 매핑)와 방법 A의 검증을 분리할 때 — `general-purpose` × 2
- phase 04 step3: toy bandit sanity와 메인 시뮬레이션 dry-run을 동시에 — `general-purpose` × 2
- phase 06: figure 1~4를 4개 subagent에 분리해서 동시에 그리기 (의존성 없음)

스폰은 *수단*이고 *목적*이 아니다. 단일·짧은 작업은 직접 처리. 3+ step 이상이거나 메인 컨텍스트를 오염시킬 만한 raw output을 동반하는 경우에 사용.

## Phase 진행 순서
1. `phases/01-scraping-setup/` — wine21 (ADR-001 갱신) 스크래퍼 프로토타입
2. `phases/02-data-collection/` — 본 수집 + Nemotron 페르소나 로딩
3. `phases/03-persona-translation/` — Persona Translation Layer (핵심 기여 1)
4. `phases/04-reward-and-mab/` — Reward Function + MAB 정책 (핵심 기여 2)
5. `phases/05-simulation-analysis/` — 메인 시뮬레이션 실행
6. `phases/06-visualization-report/` — 시각화 + 보고서 산출물

각 phase의 `index.json`에 step 목록과 status가 들어있고, `step{N}.md`는 단일 모듈에 대한 자기완결적 지시서입니다.
