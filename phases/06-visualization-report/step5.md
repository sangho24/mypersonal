# Step 5 — 발표 슬라이드 outline + 보고서 초안

## Read first
- 전체 `docs/PRD.md`
- `results/figures/fig{1,2,3,4}.png`
- `notebooks/05_main_analysis.ipynb` 인사이트 노트

## Goal
발표 슬라이드 outline과 보고서 초안을 작성. 발표 핵심 메시지: "와인은 가장 맛있는 예시였을 뿐, 같은 프레임워크가 음악·식당·신약 임상까지 transfer 된다."

## Tasks
1. `docs/REPORT.md` 작성. 구조:
   - 1. 서론 (탐색-활용 trade-off, 와인을 고른 이유)
   - 2. 데이터 (와인 카탈로그, Nemotron-Personas-Korea)
   - 3. 방법 (Persona Translation Layer — 핵심 기여 1)
   - 4. 방법 (Reward Function + MAB — 핵심 기여 2)
   - 5. 결과 (Figure 1~4 해석)
   - 6. 민감도 분석
   - 7. 한계 및 향후 연구
   - 8. 결론 — 일반화 가능성
2. `docs/SLIDES.md` 작성 — 슬라이드별 1줄 메시지 + 어느 figure를 보일지.
3. 보고서 최종은 PDF로 export — 환경에 따라 marp / pandoc / 수동 변환.

## Don't
- "성공" 일색으로 결론짓지 말 것. **이유**: 평가자는 한계를 인지하는 학생을 더 높게 평가. 단일 사이트 출처, 합성 페르소나의 한계, 짧은 T 등을 7장에 명시.

## Acceptance Criteria
```bash
test -f docs/REPORT.md
wc -l docs/REPORT.md   # >= 150
test -f docs/SLIDES.md
```

## Phase exit
`phases/index.json`의 `06-visualization-report.status`를 `"completed"`로. 프로젝트 종료.
