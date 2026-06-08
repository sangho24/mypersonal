"""T6 — Cluster today's feature vector to nearest archetype (numpy K-means stub).

K-means 전 과정을 본 모듈에서 새로 학습하지는 않는다 (전제: 호출자가
src/personal/cluster_fit.py 등에서 사전 fit 한 centroid 행렬과 라벨을 전달).
본 함수는 numpy 유클리드 거리만으로 가장 가까운 centroid 와 가장 가까운 과거 3일을 반환.

CLAUDE.md 룰 준수: sklearn 금지, numpy 직접 구현. K-means 자체는 src/mab 가
재사용하는 numpy 구현을 가져다 쓰는 것이 원칙이며, 본 모듈에서는 assignment 만 한다.
"""

from __future__ import annotations

import numpy as np


def _euclid(x: np.ndarray, Y: np.ndarray) -> np.ndarray:
    """x: (d,) , Y: (N, d) → (N,) 유클리드 거리."""
    diff = Y - x[None, :]
    return np.sqrt((diff * diff).sum(axis=1))


def cluster_today_archetype(
    today_vector: np.ndarray,
    fitted_centroids: np.ndarray,
    cluster_labels: list[str],
    past_vectors: np.ndarray | None = None,
    past_dates: list[str] | None = None,
    top_k_similar: int = 3,
) -> dict:
    """오늘 벡터를 사전 학습된 centroid 에 할당 + 유사 과거일 top-k.

    Parameters
    ----------
    today_vector : np.ndarray (d,)
        오늘의 feature vector (예: [mean_step, mean_HR, audio_exposure, ...]).
    fitted_centroids : np.ndarray (K, d)
        사전 학습된 K-means 중심.
    cluster_labels : list[str]
        길이 K 의 사람이 읽기 좋은 라벨 (예: ["휴식", "유산소", "근력", ...]).
    past_vectors : np.ndarray (M, d) | None
        과거 일별 벡터. 주어지면 유사 과거일을 찾음.
    past_dates : list[str] | None
        길이 M, past_vectors 행에 대응.

    Returns
    -------
    dict
        {cluster_id, cluster_label, distance, similar_past_days}
    """
    x = np.asarray(today_vector, dtype=np.float64).reshape(-1)
    C = np.asarray(fitted_centroids, dtype=np.float64)
    if C.ndim != 2 or C.shape[1] != x.shape[0]:
        raise ValueError(f"centroid shape {C.shape} vs vector shape {x.shape}")
    if len(cluster_labels) != C.shape[0]:
        raise ValueError("cluster_labels 길이가 centroid 수와 다름")

    d_to_centroids = _euclid(x, C)
    cid = int(np.argmin(d_to_centroids))
    label = str(cluster_labels[cid])
    dist = float(d_to_centroids[cid])

    similar: list[dict] = []
    if past_vectors is not None and past_dates is not None and len(past_dates) > 0:
        P = np.asarray(past_vectors, dtype=np.float64)
        d_past = _euclid(x, P)
        order = np.argsort(d_past)[:top_k_similar]
        similar = [
            {"date": str(past_dates[i]), "distance": float(d_past[i])}
            for i in order
        ]

    return {
        "cluster_id": cid,
        "cluster_label": label,
        "distance": dist,
        "similar_past_days": similar,
    }


def _smoke() -> int:
    rng = np.random.default_rng(4)
    # 3 archetype centroids (d=3): rest, cardio, strength
    C = np.array([[2000, 60, 50], [8000, 130, 65], [4500, 110, 75]], dtype=np.float64)
    labels = ["휴식", "유산소", "근력"]
    # 오늘은 cardio 비슷
    today = np.array([7800.0, 128.0, 64.0])
    past = rng.normal(0, 1, (20, 3)) * np.array([1500, 30, 10]) + np.array([6000, 100, 60])
    dates = [f"2026-05-{i + 1:02d}" for i in range(20)]
    out = cluster_today_archetype(today, C, labels, past, dates)
    print("[T6 smoke]", out)
    assert out["cluster_label"] == "유산소"
    assert len(out["similar_past_days"]) == 3
    return 0


if __name__ == "__main__":
    raise SystemExit(_smoke())
