"""Figure 10 — Arm pull heatmap (policy × country).

Reads results/logs/run_baseline.jsonl (250 runs = 5 policies × 50 seeds, T=200).
Builds a 4×11 heatmap of normalized pull frequency:
  Rows: EpsilonGreedy, ThompsonGauss, UCB1 (c=c*), RandomPolicy
  Cols: 11 countries sorted by markup ASC (= highest reward first), i.e. the
        country with the lowest markup is the best arm.
Cells: mean pull count over 50 seeds, normalized so each row sums to 1.
Cells are annotated to 2 decimals; viridis colormap; colorbar attached.

Output: results/figures/mab/10_pull_heatmap.png (9×4 in, 300 dpi).

Run:
    uv run python scripts/build_fig_10_pulls.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "results" / "logs" / "run_baseline.jsonl"
OUT_PATH = ROOT / "results" / "figures" / "mab" / "10_pull_heatmap.png"

# src 패키지 import 가능하게 ROOT 를 sys.path 에 추가
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# arm 인덱스 순서 — src.mab.reward.TARGET_COUNTRIES 와 1:1 대응
# (한국어 + 영어 라벨 + markup 정렬 키)
ARM_KR_ORDER: list[str] = [
    "프랑스",
    "포르투갈",
    "이탈리아",
    "스페인",
    "칠레",
    "미국",
    "호주",
    "뉴질랜드",
    "독일",
    "아르헨티나",
    "남아프리카",
]
KR_TO_EN: dict[str, str] = {
    "프랑스": "France",
    "포르투갈": "Portugal",
    "이탈리아": "Italy",
    "스페인": "Spain",
    "칠레": "Chile",
    "미국": "USA",
    "호주": "Australia",
    "뉴질랜드": "NZ",
    "독일": "Germany",
    "아르헨티나": "Argentina",
    "남아프리카": "South Africa",
}

# 표시할 정책 순서 (4행). 키 = jsonl 의 policy_name.
POLICY_ROW_ORDER: list[tuple[str, str]] = [
    ("EpsilonGreedy", "ε-greedy"),
    ("ThompsonGauss", "Thompson"),
    ("UCB1", "UCB1 (c=c*)"),
    ("RandomPolicy", "Random"),
]


def _setup_korean_font() -> None:
    """플랫폼별 한국어 폰트 설정."""
    candidates = ["AppleGothic", "NanumGothic", "Malgun Gothic", "Noto Sans CJK KR"]
    available = {f.name for f in mpl.font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            mpl.rc("font", family=name)
            break
    mpl.rcParams["axes.unicode_minus"] = False


def _load_runs() -> list[dict]:
    if not LOG_PATH.exists():
        raise FileNotFoundError(
            f"baseline log not found at {LOG_PATH}. "
            "Run `uv run python -m src.mab.simulate` first."
        )
    with LOG_PATH.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _markup_order_indices() -> list[int]:
    """markup ASC (= 보상 DESC) 기준으로 arm index 를 재정렬해서 반환.

    src.mab.reward.load_markup_table 의 결과를 사용해서 결정한다.
    """
    from src.mab.reward import load_markup_table

    table = load_markup_table()
    # table.country 는 TARGET_COUNTRIES 순서로 정렬되어 있고 길이가 11.
    country_to_arm: dict[str, int] = {c: i for i, c in enumerate(ARM_KR_ORDER)}
    # markup ASC 정렬
    sorted_rows = sorted(
        table.to_dict("records"), key=lambda r: float(r["markup"])
    )
    return [country_to_arm[r["country"]] for r in sorted_rows]


def _build_matrix(runs: list[dict], col_arm_idx: list[int]) -> np.ndarray:
    """4×11 행렬: 각 정책별 평균 pull 비율 (행 합 = 1)."""
    n_rows = len(POLICY_ROW_ORDER)
    n_cols = len(col_arm_idx)
    mat = np.zeros((n_rows, n_cols), dtype=np.float64)

    for row_idx, (policy_key, _label) in enumerate(POLICY_ROW_ORDER):
        seed_pulls = [r["arm_pulls"] for r in runs if r["policy_name"] == policy_key]
        if not seed_pulls:
            raise RuntimeError(f"no runs found for policy {policy_key}")
        arr = np.asarray(seed_pulls, dtype=np.float64)  # (n_seeds, 11)
        # seed별 비율로 정규화 한 뒤 평균 — seed 마다 T가 같다는 가정과 무관하게 안전.
        seed_totals = arr.sum(axis=1, keepdims=True)
        seed_props = arr / np.where(seed_totals == 0, 1.0, seed_totals)
        mean_props = seed_props.mean(axis=0)  # shape (11,)
        # markup 정렬 순서대로 reindex
        mat[row_idx, :] = mean_props[col_arm_idx]

    # 행 합이 1 이 되도록 한번 더 정규화 (부동소수 오차 보정)
    row_sums = mat.sum(axis=1, keepdims=True)
    mat = mat / np.where(row_sums == 0, 1.0, row_sums)
    return mat


def _draw(mat: np.ndarray, col_arm_idx: list[int]) -> None:
    row_labels = [label for _, label in POLICY_ROW_ORDER]
    col_labels = [KR_TO_EN[ARM_KR_ORDER[i]] for i in col_arm_idx]

    fig, ax = plt.subplots(figsize=(9, 4), dpi=300)
    im = ax.imshow(mat, aspect="auto", cmap="viridis", vmin=0.0, vmax=float(mat.max()))

    # 축 라벨
    ax.set_xticks(np.arange(len(col_labels)))
    ax.set_xticklabels(col_labels, rotation=30, ha="right", fontsize=10)
    ax.set_yticks(np.arange(len(row_labels)))
    ax.set_yticklabels(row_labels, fontsize=10)

    # 셀 주석 — 색이 밝은 쪽에선 검정, 어두운 쪽에선 흰색
    vmax = float(mat.max()) if mat.max() > 0 else 1.0
    for r in range(mat.shape[0]):
        for c in range(mat.shape[1]):
            v = mat[r, c]
            color = "white" if v < 0.55 * vmax else "black"
            ax.text(c, r, f"{v:.2f}", ha="center", va="center", fontsize=8, color=color)

    ax.set_title(
        "정책별 arm 선택 분포 — Thompson은 FR/PT에 집중, UCB1은 균등 탐색",
        fontsize=11,
        pad=10,
    )

    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("mean pull share (row-normalized)", fontsize=9)
    cbar.ax.tick_params(labelsize=8)

    fig.tight_layout()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    _setup_korean_font()
    runs = _load_runs()
    col_arm_idx = _markup_order_indices()
    mat = _build_matrix(runs, col_arm_idx)
    _draw(mat, col_arm_idx)

    print(f"[fig10] wrote {OUT_PATH}")
    print(f"  policies: {[k for k, _ in POLICY_ROW_ORDER]}")
    print(f"  columns (arm idx, markup-ASC): {col_arm_idx}")
    print(f"  columns (labels): {[KR_TO_EN[ARM_KR_ORDER[i]] for i in col_arm_idx]}")
    print("  matrix (row-normalized pull share):")
    for (key, label), row in zip(POLICY_ROW_ORDER, mat, strict=True):
        cells = "  ".join(f"{v:.3f}" for v in row)
        print(f"    {label:>13s} | {cells}  sum={row.sum():.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
