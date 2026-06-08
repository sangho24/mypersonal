"""Single source of truth for personal-data track timeline anchors.

모든 figure/분석 모듈은 여기서 import 해서 사용. 하드코딩 금지.
사용자(20200572 엄상호) 가 확정한 사실만 담는다 — 위반 시 sanity_anchors.py 가 fail.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Window:
    start: date
    end: date
    label: str

    def contains(self, d: date) -> bool:
        return self.start <= d <= self.end


# ─── Life event anchors (사용자 확정) ───
ENROLLMENT = date(2019, 3, 1)            # 학부 입학
MIL_START = date(2021, 11, 15)           # 군 입대 (정확)
MIL_END = date(2023, 5, 14)              # 전역 (정확)
ACL_INJURY = date(2023, 10, 15)          # 무릎(전방십자인대) 부상, ±2주 불확실
ACL_SURGERY = date(2024, 1, 5)           # ACL 수술 (월 단위 확정, 일자 ±1주)
PARIS_START = date(2024, 12, 1)          # 교환학생 출국 (추정)
PARIS_END = date(2025, 6, 15)            # 귀국 (추정)
SEOUL_REC_START = date(2025, 7, 1)       # 귀국 후 Seoul 재정착

# ─── 분석용 window ───
# baseline = pre-MIL (사용자 확정). quality 채널은 iOS 14 gait sensor 도입 (2020-09) 이후만 존재
PRE_MIL_BASELINE = Window(
    start=date(2020, 9, 1),
    end=date(2021, 10, 31),
    label="pre-MIL baseline",
)
MIL_WINDOW = Window(
    start=MIL_START,
    end=MIL_END,
    label="군 복무",
)
ACL_RECOVERY = Window(
    start=ACL_SURGERY,
    end=date(2025, 6, 30),
    label="ACL 수술 후 회복기",
)
PARIS_WINDOW = Window(
    start=PARIS_START,
    end=PARIS_END,
    label="Paris 교환학생",
)
SEOUL_REC_WINDOW = Window(
    start=SEOUL_REC_START,
    end=date(2026, 4, 30),
    label="Seoul (귀국 후)",
)

# ─── 폐기된 anchor (절대 사용 금지 — sanity_anchors.py 가 grep 으로 검출) ───
# build_fig_06_v_curve*.py 에 있던 잘못된 값 — 참조 금지
_DEPRECATED_DO_NOT_USE = {
    "OLD_BASELINE_END": "date(2021, 12, 1)",   # 군 복무 중간 기간 포함 → baseline 부적격
    "OLD_MIL_START": "date(2020, 7, 1)",        # 실제는 2021-11-15
    "OLD_MIL_END": "date(2022, 4, 1)",          # 실제는 2023-05-14
    "OLD_QUALITY_CROSS": "date(2022, 12, 1)",   # MIL_END + 8m 하드코딩 — 데이터 산출 아님
    "OLD_QUANTITY_CROSS": "date(2024, 4, 1)",   # MIL_END + 24m 하드코딩 — 데이터 산출 아님
}
