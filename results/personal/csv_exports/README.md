# Designer CSV pack — Slide 8 & Slide 12

> 빅데이터컴퓨팅 기말 발표 deck rev5.1. PowerPoint 네이티브 차트로 옮길 때 그대로 import.
> 출처: `src/personal/finding{2,3}.py` 산출 + Apple Health XML 재처리.
> 작성: 20200572 엄상호 (2026-06-08)

---

## Slide 8 — 'Paris' 라는 한 사건이 세 채널에 다른 위상으로

핵심 메시지: **"Paris=원료 투입 / 귀국 후=가공 완료 의 2단계 구조"**

### Panel 1 (활동량, Paris 중) — `slide8_panel1_monthly_activity.csv`
- 컬럼: `month, steps_per_day, distance_km_per_day, flights_per_day, phase`
- 79 행 (2019-12 ~ 2026-06 monthly)
- phase: `MIL` / `Paris` / `Seoul_rec` / `other` — 색상 구분 또는 음영 영역 표시용
- **차트 추천**: 3-line chart (steps 좌축, distance/flights 우축). Paris window (2024-12~2025-06) 음영 + 귀국 (2025-07) vertical line.

### Panel 2 (청취량, Paris 중 monotonic) — `slide8_panel2_paris_audio_monthly.csv`
- 컬럼: `month, audio_listen_min_per_day`
- 7 행 (Paris 7 개월)
- **차트 추천**: bar 또는 line. 첫(71분)/마지막(251분) 마커. **Spearman ρ=0.86** annotation.

### Panel 3 (gait remodel, 귀국 후 강화) — `slide8_panel3_walking_speed_monthly.csv`
- 컬럼: `month, walking_speed_kmh, baseline_pre_MIL_mean, baseline_pre_MIL_low_1sd, baseline_pre_MIL_high_1sd, Seoul_rec_mean, Seoul_rec_low_1sd, Seoul_rec_high_1sd`
- 69 행 (2020-09 ~ 2026-06, gait sensor 데이터 있는 월)
- **차트 추천**: line + 2 horizontal band (baseline 파랑, Seoul_rec 녹색) 영역.

### Panel 3 보조 — `slide8_panel3_explore_timing.csv`
- 컬럼: `paris_third, explore_day_count`
- 3 행 (early/mid/late)
- **차트 추천**: 3-bar chart, late 가 11 로 강조.

### Callout — `slide8_key_numbers.csv`
8 행. 채널·metric·value·p_value 의 텍스트 박스/표 용. (R2 검증 통과한 정확한 수치)

---

## Slide 12 — Appendix 부상 시리즈 (질문 시 활용)

핵심 메시지: **"Walking Steadiness 가 부상 4개월 선행 / asymmetry z=+5.58σ 시계열 최강 / Running 91일 만에 폭주"**

### Panel 1 (Walking Steadiness 단조 하락) — `slide12_panel1_steadiness.csv`
- 컬럼: `month, walking_steadiness_pct, event`
- 13 행 (2023-08 ~ 2024-08)
- event 컬럼: ACL 부상/수술 시점 marker
- **차트 추천**: line + 2 vertical marker (2023-10 부상 / 2024-01 수술). y축 90~100%.

### Panel 2 (수술월 채널별 z-score) — `slide12_panel2_surgery_zscores.csv`
- 컬럼: `channel, surgery_month_z, is_timeseries_extreme, extreme_month, extreme_z`
- 6 행 (steps/distance_km/walking_speed/step_length/asymmetry/double_support)
- **차트 추천**: horizontal bar chart, asymmetry (z=+5.58, "Yes" extreme) 강조 (다른 색).

### Panel 3 (Running 47건 timeline) — `slide12_panel3_running_timeline.csv`
- 컬럼: `date, duration_min, source, days_from_surgery, phase`
- 47 행 (전체 Running workout)
- phase: `before_surgery` / `after_surgery`
- **차트 추천**: scatter (x=date, y=duration_min), 색상 = phase, 수술일 (2024-01-05) vertical line. 공백 296일 + 91일 후 폭주 시각화.

### Panel 4 (2024 월별 Running 빈도) — `slide12_panel4_2024_monthly_running.csv`
- 컬럼: `month, running_session_count`
- 12 행 (모든 2024 월, 0건 포함)
- **차트 추천**: bar chart. 2024-04 의 8건 만 빨강 강조 (나머지 0).

### Callout — `slide12_key_numbers.csv`
6 행. finding·metric·value 의 텍스트 박스/표 용.

---

## 재산출 명령
```bash
PYTHONPATH=. uv run python scripts/personal/export_designer_csvs.py
```

데이터 / 코드가 갱신되면 다시 돌리면 됩니다.
