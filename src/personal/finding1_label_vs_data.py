"""발견 1 — "자전적 라벨이 데이터를 자르지 않는다" 산출 모듈.

(A) 9채널 일별 K-means (numpy 직구현, K=4) → cluster c0 비중 pre-MIL vs MIL Δ 산출
(B) Paris vs Seoul-rec daily_steps 가 Maps day-category 로 stratify 됐을 때 Simpson 효과

결과 JSON 위치: results/personal/finding1.json
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from src.personal.anchors import (
    MIL_END,
    MIL_START,
    PARIS_END,
    PARIS_START,
    PRE_MIL_BASELINE,
    SEOUL_REC_START,
)
from src.personal.data import load_daily_9ch

MAPS_JSON = Path("/Users/sangho/Downloads/location-history.json")
OUT_JSON = Path(__file__).parents[2] / "results" / "personal" / "finding1.json"


# ─── K-means (numpy 직구현, sklearn 금지) ───
def kmeans_lloyd(X: np.ndarray, K: int, seed: int = 42, max_iter: int = 100) -> tuple[np.ndarray, np.ndarray, float]:
    """k-means++ init + Lloyd. 반환: (labels, centroids, inertia)."""
    rng = np.random.default_rng(seed)
    n, d = X.shape
    centroids = np.empty((K, d))
    centroids[0] = X[rng.integers(n)]
    for k in range(1, K):
        diff = X[:, None, :] - centroids[None, :k, :]
        dist2 = (diff * diff).sum(-1).min(1)
        s = dist2.sum()
        if s == 0:
            centroids[k] = X[rng.integers(n)]
        else:
            centroids[k] = X[rng.choice(n, p=dist2 / s)]
    for _ in range(max_iter):
        diff = X[:, None, :] - centroids[None, :, :]
        labels = (diff * diff).sum(-1).argmin(1)
        new_c = np.zeros_like(centroids)
        for k in range(K):
            mask = labels == k
            new_c[k] = X[mask].mean(0) if mask.any() else centroids[k]
        if np.allclose(new_c, centroids):
            break
        centroids = new_c
    diff = X[:, None, :] - centroids[None, :, :]
    sq = (diff * diff).sum(-1)
    inertia = float(sq.min(1).sum())
    return labels, centroids, inertia


def kmeans_best_of(X: np.ndarray, K: int, n_init: int = 15, max_iter: int = 100) -> tuple[np.ndarray, np.ndarray]:
    best = None
    for seed in range(n_init):
        labels, centroids, inertia = kmeans_lloyd(X, K, seed=seed, max_iter=max_iter)
        if best is None or inertia < best[2]:
            best = (labels, centroids, inertia)
    assert best is not None
    return best[0], best[1]


# ─── (A) 9채널 K-means → cluster c0 비중 pre-MIL vs MIL ───
def run_kmeans_chapter() -> dict:
    df = load_daily_9ch()
    df = df.dropna(subset=["walking_speed"]).copy()  # iOS 14+ gait 데이터 있는 날만
    feature_cols = [
        "steps", "distance_km", "active_energy_kcal", "flights",
        "walking_speed", "step_length", "asymmetry", "double_support", "audio_max_dB",
    ]
    # 같은 달 mean imputation (NaN 채우기) — 같은 월 평균이 또 NaN 이면 0
    df["ym"] = df["date"].dt.to_period("M")
    for c in feature_cols:
        df[c] = df.groupby("ym")[c].transform(lambda s: s.fillna(s.mean()))
    df[feature_cols] = df[feature_cols].fillna(0.0)
    # z-score 전체 시리즈 기준
    X = df[feature_cols].to_numpy(dtype=np.float64)
    X = (X - X.mean(0)) / (X.std(0, ddof=1) + 1e-9)

    labels, centroids = kmeans_best_of(X, K=4, n_init=15, max_iter=100)
    df["cluster"] = labels

    # cluster index 정렬: 첫 c0 = pre-MIL 에서 가장 큰 비중 cluster
    pre_mask = (df["date"] >= pd.Timestamp(PRE_MIL_BASELINE.start)) & (
        df["date"] <= pd.Timestamp(PRE_MIL_BASELINE.end)
    )
    pre_counts = df.loc[pre_mask, "cluster"].value_counts()
    c0 = int(pre_counts.idxmax()) if len(pre_counts) else 0

    pre_n = int(pre_mask.sum())
    pre_c0 = int((df.loc[pre_mask, "cluster"] == c0).sum())

    mil_mask = (df["date"] >= pd.Timestamp(MIL_START)) & (df["date"] <= pd.Timestamp(MIL_END))
    mil_n = int(mil_mask.sum())
    mil_c0 = int((df.loc[mil_mask, "cluster"] == c0).sum())

    pre_pct = pre_c0 / pre_n * 100 if pre_n else float("nan")
    mil_pct = mil_c0 / mil_n * 100 if mil_n else float("nan")

    return {
        "K": 4,
        "n_features": len(feature_cols),
        "feature_cols": feature_cols,
        "n_days_used": int(len(df)),
        "c0_index": c0,
        "pre_MIL_window": {"start": str(PRE_MIL_BASELINE.start), "end": str(PRE_MIL_BASELINE.end), "n_days": pre_n, "c0_days": pre_c0, "c0_pct": round(pre_pct, 2)},
        "MIL_window": {"start": str(MIL_START), "end": str(MIL_END), "n_days": mil_n, "c0_days": mil_c0, "c0_pct": round(mil_pct, 2)},
        "delta_pp": round(mil_pct - pre_pct, 2),
        "interpretation": "pre-MIL 과 MIL 의 c0 비중 차이가 작을수록 (|Δ| < 5pp) '두 chapter 가 데이터상 같은 cluster' 라는 결론이 강해짐.",
    }


# ─── (B) Maps day-category × city Simpson ───
def categorize_days_from_maps() -> pd.DataFrame:
    if not MAPS_JSON.exists():
        return pd.DataFrame(columns=["date", "category", "n_visits", "n_searched"])
    with open(MAPS_JSON) as f:
        data = json.load(f)
    segments = data.get("semanticSegments", data) if isinstance(data, dict) else data
    by_date: dict[str, dict] = defaultdict(lambda: {"visits": 0, "searched": 0})
    for seg in segments:
        ts = (seg.get("startTime") or "")[:10]
        if not ts:
            continue
        visit = seg.get("visit") or {}
        if not visit:
            continue
        topc = visit.get("topCandidate") or {}
        sem = topc.get("semanticType", "")
        by_date[ts]["visits"] += 1
        if "SEARCHED" in sem.upper():
            by_date[ts]["searched"] += 1
    rows = []
    for d, info in by_date.items():
        n_v = info["visits"]
        n_s = info["searched"]
        if n_v == 0:
            cat = "home_only"
        elif n_s >= 2:
            cat = "explore"
        elif n_v >= 5:
            cat = "outing"
        else:
            cat = "routine"
        rows.append({"date": d, "category": cat, "n_visits": n_v, "n_searched": n_s})
    return pd.DataFrame(rows)


def welch_t_and_d(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """Welch t, df-Welch p-value(two-sided), Cohen's d (pooled std). scipy 없이 numpy 만."""
    x = np.asarray(x, dtype=np.float64); y = np.asarray(y, dtype=np.float64)
    nx, ny = len(x), len(y)
    if nx < 2 or ny < 2:
        return float("nan"), float("nan"), float("nan")
    mx, my = x.mean(), y.mean()
    vx, vy = x.var(ddof=1), y.var(ddof=1)
    se = np.sqrt(vx / nx + vy / ny)
    if se == 0:
        return float("nan"), float("nan"), float("nan")
    t = (mx - my) / se
    df_num = (vx / nx + vy / ny) ** 2
    df_den = (vx / nx) ** 2 / max(nx - 1, 1) + (vy / ny) ** 2 / max(ny - 1, 1)
    df = df_num / df_den if df_den > 0 else (nx + ny - 2)
    # two-sided p via numerical CDF (Student t survival) — Welch-Satterthwaite
    # Stirling-grade approx via incomplete beta unavailable without scipy; use normal approx for |t| (df>20 안전)
    from math import erf, sqrt
    p_normal = 2 * (1 - 0.5 * (1 + erf(abs(t) / sqrt(2))))
    pooled = np.sqrt(((nx - 1) * vx + (ny - 1) * vy) / max(nx + ny - 2, 1))
    d = (mx - my) / pooled if pooled > 0 else float("nan")
    return float(t), float(p_normal), float(d)


def run_simpson_stratification() -> dict:
    df = load_daily_9ch()[["date", "steps"]].copy()
    cats = categorize_days_from_maps()
    cats["date"] = pd.to_datetime(cats["date"])
    df = df.merge(cats, on="date", how="left")
    df["category"] = df["category"].fillna("home_only")
    df["city"] = "other"
    df.loc[(df["date"] >= pd.Timestamp(PARIS_START)) & (df["date"] <= pd.Timestamp(PARIS_END)), "city"] = "Paris"
    df.loc[df["date"] >= pd.Timestamp(SEOUL_REC_START), "city"] = "Seoul_rec"

    paris = df[df["city"] == "Paris"]["steps"].dropna().to_numpy()
    seoul = df[df["city"] == "Seoul_rec"]["steps"].dropna().to_numpy()
    overall_t, overall_p, overall_d = welch_t_and_d(paris, seoul)

    strat = {}
    for cat in ["home_only", "routine", "outing", "explore"]:
        p = df[(df["city"] == "Paris") & (df["category"] == cat)]["steps"].dropna().to_numpy()
        s = df[(df["city"] == "Seoul_rec") & (df["category"] == cat)]["steps"].dropna().to_numpy()
        t, p_val, d = welch_t_and_d(p, s)
        strat[cat] = {
            "n_Paris": int(len(p)), "n_Seoul_rec": int(len(s)),
            "mean_Paris": round(float(p.mean()) if len(p) else float("nan"), 1),
            "mean_Seoul_rec": round(float(s.mean()) if len(s) else float("nan"), 1),
            "welch_t": round(t, 3), "p_value": round(p_val, 4), "cohens_d": round(d, 3),
        }
    return {
        "overall": {
            "n_Paris": int(len(paris)), "n_Seoul_rec": int(len(seoul)),
            "mean_Paris": round(float(paris.mean()) if len(paris) else float("nan"), 1),
            "mean_Seoul_rec": round(float(seoul.mean()) if len(seoul) else float("nan"), 1),
            "welch_t": round(overall_t, 3), "p_value": round(overall_p, 4), "cohens_d": round(overall_d, 3),
        },
        "stratified_by_day_category": strat,
        "interpretation": "overall p<0.05 인데 모든 stratified cell 의 p>0.05 라면 Simpson 효과 — 도시차가 day-type 구성비 차이로 환원됨.",
    }


def run() -> dict:
    out = {
        "kmeans_chapter": run_kmeans_chapter(),
        "simpson_stratification": run_simpson_stratification(),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    return out


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
