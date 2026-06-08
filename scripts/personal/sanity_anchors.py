"""CI sanity gate — anchors.py SoT 가 사용자 확정 사실과 일치하고,
폐기된 narrative/anchor 문자열이 어디에도 남아있지 않은지 확인.

실패 시 exit 1. CI 파이프라인 (.github/workflows/ci.yml) 에서 호출.

Usage:
    uv run python scripts/personal/sanity_anchors.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from src.personal.anchors import (
    ACL_INJURY,
    ACL_SURGERY,
    MIL_END,
    MIL_START,
    PARIS_END,
    PARIS_START,
)

ROOT = Path(__file__).resolve().parents[2]

# Tier-A: 코드/식별자 수준 — 어떤 파일에서도 발견되면 실패 (메타 문서도 예외 없음)
FORBIDDEN_CODE_PATTERNS = [
    r"\bMIL_END\s*=\s*date\(\s*2022\s*,\s*4",
    r"\bMIL_START\s*=\s*date\(\s*2020\s*,\s*7",
    r"quality_cross_dt\s*=\s*datetime\(\s*2022\s*,\s*12",
    r"quantity_cross_dt\s*=\s*datetime\(\s*2024\s*,\s*4",
]

# Tier-B: narrative 패턴 — 폐기된 메시지가 *현재 결론으로* 인용되는 경우만 검출.
# 메타 문서 (changelog / Q&A "왜 제거했나" 설명) 는 면제.
FORBIDDEN_NARRATIVE_PATTERNS = [
    r"양은 늦게",
    r"질은 먼저",
    r"24개월에 baseline 회복",
    r"8개월에 baseline 회복",
    r"양 24개월 / 질 8개월",
]
NARRATIVE_EXEMPT_FILES = {
    "docs/personal/DECK_PLAN.md",   # §7 rev5 changelog
    "docs/personal/QA_CARDS.md",    # Card 11 "왜 폐기?" 답변
}

# 폐기된 스크립트 — 존재하면 실패
FORBIDDEN_FILES = [
    "scripts/personal/build_fig_06_v_curve.py",
    "scripts/personal/build_fig_06_v_curve_v2.py",
    "scripts/personal/build_fig_07_paris_seoul.py",
    "scripts/personal/build_fig_07_paris_seoul_v2.py",
    "scripts/personal/build_fig_08_hero_demo.py",
    "docs/personal/DECK_PLAN_v1.md",
]

# 사용자 확정 사실 (anchors.py 가 이 값들과 일치해야 함)
EXPECTED = {
    "MIL_START": date(2021, 11, 15),
    "MIL_END": date(2023, 5, 14),
    "ACL_INJURY": date(2023, 10, 15),
    "ACL_SURGERY": date(2024, 1, 5),
    "PARIS_START": date(2024, 12, 1),
    "PARIS_END": date(2025, 6, 15),
}


def check_anchors() -> list[str]:
    errors = []
    actual = {
        "MIL_START": MIL_START,
        "MIL_END": MIL_END,
        "ACL_INJURY": ACL_INJURY,
        "ACL_SURGERY": ACL_SURGERY,
        "PARIS_START": PARIS_START,
        "PARIS_END": PARIS_END,
    }
    for name, expected in EXPECTED.items():
        got = actual[name]
        if got != expected:
            errors.append(f"anchor mismatch: {name} = {got}, expected {expected}")
    return errors


def check_forbidden_patterns() -> list[str]:
    """Tier-A 코드 식별자 + Tier-B narrative 패턴 (메타 문서 면제) grep."""
    errors = []
    search_dirs = [
        ROOT / "docs" / "personal",
        ROOT / "scripts" / "personal",
        ROOT / "src" / "personal",
    ]
    files: list[Path] = []
    for d in search_dirs:
        if not d.exists():
            continue
        files.extend(d.rglob("*.py"))
        files.extend(d.rglob("*.md"))
    # anchors.py 의 _DEPRECATED_DO_NOT_USE 와 sanity_anchors.py 자체는 제외
    files = [f for f in files if f.name not in {"anchors.py", "sanity_anchors.py"}]
    for f in files:
        try:
            text = f.read_text(errors="ignore")
        except Exception:
            continue
        rel_str = str(f.relative_to(ROOT))
        # Tier-A: 모든 파일에서 검사
        for pat in FORBIDDEN_CODE_PATTERNS:
            for m in re.finditer(pat, text):
                line_no = text[: m.start()].count("\n") + 1
                errors.append(f"[CODE] forbidden '{pat}' at {rel_str}:{line_no}")
        # Tier-B: 메타 문서는 면제
        if rel_str in NARRATIVE_EXEMPT_FILES:
            continue
        for pat in FORBIDDEN_NARRATIVE_PATTERNS:
            for m in re.finditer(pat, text):
                line_no = text[: m.start()].count("\n") + 1
                errors.append(f"[NARRATIVE] forbidden '{pat}' at {rel_str}:{line_no}")
    return errors


def check_forbidden_files() -> list[str]:
    errors = []
    for rel in FORBIDDEN_FILES:
        p = ROOT / rel
        if p.exists():
            errors.append(f"deprecated file still exists: {rel}")
    return errors


def main() -> int:
    all_errors: list[str] = []
    all_errors.extend(check_anchors())
    all_errors.extend(check_forbidden_patterns())
    all_errors.extend(check_forbidden_files())

    if all_errors:
        print("FAIL — sanity_anchors detected issues:", file=sys.stderr)
        for e in all_errors:
            print(f"  • {e}", file=sys.stderr)
        return 1
    print("OK — anchors.py SoT 일치, 폐기 narrative/file 0건.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
