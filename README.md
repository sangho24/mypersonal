# wine-mab-project

한국 와인 시장에서의 합리적 취향 탐색 전략 시뮬레이션
(빅데이터 컴퓨팅 기말 프로젝트, 20200572 엄상호)

와인 선택을 multi-armed bandit (MAB) 문제로 정식화하고, ε-greedy / UCB1 / Thompson Sampling 등 탐색 정책의 성능을 NVIDIA Nemotron-Personas-Korea 합성 페르소나 위에서 비교합니다.

## 빠른 시작
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 프로젝트 구조
```
wine-mab-project/
├── CLAUDE.md             # Harness 프레임워크 가이드
├── docs/                 # PRD, ARCHITECTURE, ADR
├── phases/               # phase별 step 지시서 (LLM-friendly)
│   ├── index.json        # 전체 phase 현황
│   └── {phase-name}/
│       ├── index.json    # 해당 phase의 step 목록 + status
│       └── step{N}.md    # 단일 모듈 지시서
├── src/                  # 모든 구현 코드
│   ├── scraping/         # 와인 리테일 사이트 스크래퍼
│   ├── personas/         # Nemotron 로딩 + Persona Translation
│   ├── mab/              # MAB 정책 (numpy 직접 구현)
│   ├── simulation/       # 시뮬레이션 러너
│   └── viz/              # matplotlib 시각화
├── data/                 # git에 커밋하지 않음
│   ├── raw/              # 스크래핑 원본
│   ├── processed/        # 정제된 데이터
│   └── personas/         # 샘플링된 페르소나
├── notebooks/            # EDA만 — 로직 금지
└── results/figures/      # 보고서/발표용 그림
```

## 진행 phase
1. `01-scraping-setup` — 스크래퍼 프로토타입
2. `02-data-collection` — 본 수집 + Nemotron 로딩
3. `03-persona-translation` — Persona Translation Layer
4. `04-reward-and-mab` — Reward Function + MAB 정책 구현
5. `05-simulation-analysis` — 메인 시뮬레이션 실행 + 결과 분석
6. `06-visualization-report` — 시각화 + 보고서

자세한 작업 단위는 `phases/{name}/step{N}.md` 참고.
