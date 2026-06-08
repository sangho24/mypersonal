"""Gaussian HMM (numpy-only) on multi-stream daily behavioral features.

Pipeline:
  1) Load /tmp/personal_daily.parquet
  2) Restrict to days with walking-metric coverage (>=2020) and impute remaining
     gaps with feature-wise medians.
  3) Z-score 7 features.
  4) Fit GHMM (Baum-Welch, log-space) for K in {3,4,5}; pick by BIC.
  5) Viterbi decode the best K.
  6) Compute state means, transition matrix, expected dwell, state timeline.
  7) Overlay known chapters (military 2020-09 to 2022-09, recovery 2022-09 to
     2024-12, France 2024-12 onward) and compute per-chapter state distribution
     plus normalized mutual information between Viterbi states and chapter
     labels (zero would mean HMM found NOTHING aligned with chapters).
  8) Save figure to /tmp/personal_fig_hmm.png and JSON results to
     /tmp/personal_hmm_results.json.
"""
from __future__ import annotations

import json
import sys
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)

DAILY = "/tmp/personal_daily_hmm.parquet"
FIG = "/tmp/personal_fig_hmm.png"
OUT_JSON = "/tmp/personal_hmm_results.json"

FEATURES = [
    "steps",
    "walking_speed",
    "step_length",
    "asymmetry",
    "double_support",
    "audio_max_dB",
    "audio_listen_min",
]

# Known life chapters (approximate, from project context)
CHAPTERS = [
    ("pre_military",   date(2019, 11, 1), date(2020, 9, 14)),
    ("military",       date(2020, 9, 15), date(2022, 9, 14)),
    ("recovery_seoul", date(2022, 9, 15), date(2024, 12, 31)),
    ("france_paris",   date(2025, 1, 1),  date(2026, 6, 5)),
]


# ----------------------------- HMM (numpy) ---------------------------------


def _logsumexp(a: np.ndarray, axis: int) -> np.ndarray:
    m = np.max(a, axis=axis, keepdims=True)
    return (m + np.log(np.sum(np.exp(a - m), axis=axis, keepdims=True))).squeeze(axis)


def _log_gauss_diag(X: np.ndarray, mu: np.ndarray, var: np.ndarray) -> np.ndarray:
    """Log-density of K diagonal Gaussians on T samples.

    X: (T, D), mu: (K, D), var: (K, D) → returns (T, K).
    """
    D = X.shape[1]
    # (T,1,D) - (1,K,D) → (T,K,D)
    diff = X[:, None, :] - mu[None, :, :]
    log_det = np.sum(np.log(var), axis=1)            # (K,)
    quad = np.sum((diff ** 2) / var[None, :, :], axis=2)  # (T,K)
    return -0.5 * (D * np.log(2 * np.pi) + log_det[None, :] + quad)


def kmeans_pp_init(X: np.ndarray, K: int, rng: np.random.Generator) -> np.ndarray:
    """k-means++ seeding for HMM means (numpy)."""
    T = X.shape[0]
    idx0 = rng.integers(T)
    centers = [X[idx0]]
    for _ in range(K - 1):
        d2 = np.min(
            np.sum((X[:, None, :] - np.array(centers)[None, :, :]) ** 2, axis=2),
            axis=1,
        )
        probs = d2 / d2.sum()
        nxt = rng.choice(T, p=probs)
        centers.append(X[nxt])
    return np.array(centers)


def fit_ghmm(
    X: np.ndarray, K: int, n_iter: int = 100, tol: float = 1e-4, seed: int = 0
) -> dict:
    """Fit a Gaussian HMM with diagonal covariance via Baum-Welch (log-space)."""
    T, D = X.shape
    rng = np.random.default_rng(seed)

    # init
    mu = kmeans_pp_init(X, K, rng)                            # (K, D)
    var = np.tile(np.var(X, axis=0, keepdims=True) + 1e-3, (K, 1))   # (K, D)
    log_pi = np.log(np.full(K, 1.0 / K))
    log_A = np.log(np.full((K, K), 1.0 / K))

    prev_ll = -np.inf
    history = []
    for it in range(n_iter):
        log_B = _log_gauss_diag(X, mu, var)                  # (T, K)

        # forward
        log_alpha = np.full((T, K), -np.inf)
        log_alpha[0] = log_pi + log_B[0]
        for t in range(1, T):
            # log_alpha[t,k] = logsumexp_j(log_alpha[t-1,j] + log_A[j,k]) + log_B[t,k]
            log_alpha[t] = _logsumexp(log_alpha[t - 1][:, None] + log_A, axis=0) + log_B[t]
        ll = _logsumexp(log_alpha[-1], axis=0)
        history.append(float(ll))

        # backward
        log_beta = np.full((T, K), -np.inf)
        log_beta[-1] = 0.0
        for t in range(T - 2, -1, -1):
            log_beta[t] = _logsumexp(log_A + log_B[t + 1][None, :] + log_beta[t + 1][None, :], axis=1)

        # posteriors
        log_gamma = log_alpha + log_beta
        log_gamma -= _logsumexp(log_gamma, axis=1)[:, None]
        gamma = np.exp(log_gamma)                            # (T, K)

        # xi
        log_xi = (
            log_alpha[:-1, :, None]
            + log_A[None, :, :]
            + log_B[1:, None, :]
            + log_beta[1:, None, :]
        )
        log_xi -= _logsumexp(log_xi.reshape(T - 1, -1), axis=1)[:, None, None]
        xi_sum = np.exp(_logsumexp(log_xi, axis=0))          # (K, K)

        # M-step
        log_pi = np.log(gamma[0] + 1e-12)
        A_new = xi_sum / xi_sum.sum(axis=1, keepdims=True)
        log_A = np.log(A_new + 1e-12)

        Nk = gamma.sum(axis=0) + 1e-12                       # (K,)
        mu = (gamma.T @ X) / Nk[:, None]
        var = (gamma.T @ (X ** 2)) / Nk[:, None] - mu ** 2
        var = np.clip(var, 1e-3, None)

        if it > 4 and abs(ll - prev_ll) < tol * max(1.0, abs(prev_ll)):
            break
        prev_ll = ll

    # BIC: params = K-1 (init) + K*(K-1) (trans) + 2*K*D (mu+var)
    n_params = (K - 1) + K * (K - 1) + 2 * K * D
    bic = float(n_params * np.log(T) - 2.0 * history[-1])

    return {
        "K": K,
        "log_pi": log_pi,
        "log_A": log_A,
        "mu": mu,
        "var": var,
        "gamma": gamma,
        "loglik": history[-1],
        "bic": bic,
        "history": history,
        "n_params": n_params,
    }


def viterbi(X: np.ndarray, log_pi: np.ndarray, log_A: np.ndarray, mu: np.ndarray, var: np.ndarray) -> np.ndarray:
    T, _ = X.shape
    K = mu.shape[0]
    log_B = _log_gauss_diag(X, mu, var)
    delta = np.full((T, K), -np.inf)
    psi = np.zeros((T, K), dtype=np.int64)
    delta[0] = log_pi + log_B[0]
    for t in range(1, T):
        prev = delta[t - 1][:, None] + log_A          # (K,K)
        psi[t] = np.argmax(prev, axis=0)
        delta[t] = np.max(prev, axis=0) + log_B[t]
    states = np.zeros(T, dtype=np.int64)
    states[-1] = int(np.argmax(delta[-1]))
    for t in range(T - 2, -1, -1):
        states[t] = int(psi[t + 1, states[t + 1]])
    return states


# ----------------------------- main pipeline -------------------------------


def chapter_for(d: pd.Timestamp) -> str:
    dt = d.date()
    for name, s, e in CHAPTERS:
        if s <= dt <= e:
            return name
    return "unknown"


def normalized_mutual_info(a: np.ndarray, b: np.ndarray) -> float:
    """NMI between two label arrays (numpy)."""
    a = np.asarray(a)
    b = np.asarray(b)
    n = len(a)
    ua, ia = np.unique(a, return_inverse=True)
    ub, ib = np.unique(b, return_inverse=True)
    Ca, Cb = len(ua), len(ub)
    M = np.zeros((Ca, Cb))
    for i, j in zip(ia, ib):
        M[i, j] += 1
    Pxy = M / n
    Px = Pxy.sum(axis=1, keepdims=True)
    Py = Pxy.sum(axis=0, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        mi = np.nansum(np.where(Pxy > 0, Pxy * np.log(Pxy / (Px @ Py)), 0.0))
        hx = -np.nansum(np.where(Px > 0, Px * np.log(Px), 0.0))
        hy = -np.nansum(np.where(Py > 0, Py * np.log(Py), 0.0))
    if hx + hy == 0:
        return 0.0
    return float(2.0 * mi / (hx + hy))


def main() -> int:
    df = pd.read_parquet(DAILY)
    df = df[df["date"] >= pd.Timestamp("2020-01-01")].copy()

    # require steps and at least one walking metric overall
    df = df.dropna(subset=["steps"]).reset_index(drop=True)

    # impute other features with feature-wise median (constant fill — HMM is
    # robust to mild censoring; days with no walking metrics often = sedentary)
    for f in FEATURES:
        if f not in df.columns:
            continue
        med = float(df[f].median())
        df[f] = df[f].fillna(med)

    X_raw = df[FEATURES].to_numpy(dtype=float)
    # z-score
    mu_z = X_raw.mean(axis=0)
    sd_z = X_raw.std(axis=0) + 1e-9
    X = (X_raw - mu_z) / sd_z

    print(f"X shape={X.shape}  features={FEATURES}")

    # Fit K = 3, 4, 5 with multiple random restarts; keep best by training LL
    fits = {}
    for K in (3, 4, 5):
        best = None
        for seed in range(6):
            f = fit_ghmm(X, K, n_iter=120, tol=1e-5, seed=seed)
            if best is None or f["loglik"] > best["loglik"]:
                best = f
        fits[K] = best
        print(f"  K={K}  LL={best['loglik']:.1f}  BIC={best['bic']:.1f}  iters={len(best['history'])}")

    K_star = min(fits.keys(), key=lambda k: fits[k]["bic"])
    print(f"Selected K*={K_star} by BIC")
    fit = fits[K_star]

    states = viterbi(X, fit["log_pi"], fit["log_A"], fit["mu"], fit["var"])
    df["state"] = states

    # state means in ORIGINAL units (un-z-score)
    state_means_raw = {}
    state_counts = {}
    for k in range(K_star):
        mask = states == k
        state_counts[int(k)] = int(mask.sum())
        state_means_raw[int(k)] = {
            f: float(np.mean(X_raw[mask, i])) for i, f in enumerate(FEATURES)
        }

    A = np.exp(fit["log_A"])
    expected_dwell = (1.0 / (1.0 - np.diag(A) + 1e-12)).tolist()

    # chapter overlay
    df["chapter"] = df["date"].apply(chapter_for)
    chap_state = (
        df.groupby(["chapter", "state"]).size().unstack(fill_value=0).astype(float)
    )
    chap_state_norm = chap_state.div(chap_state.sum(axis=1), axis=0)

    nmi = normalized_mutual_info(states, df["chapter"].to_numpy())
    print(f"NMI(state, chapter)={nmi:.4f}")

    # also: dominant-state-per-chapter purity
    dominant = chap_state_norm.idxmax(axis=1).to_dict()
    chap_purity = chap_state_norm.max(axis=1).to_dict()

    # ----------------- figure: 4-panel ----------------------------------
    fig = plt.figure(figsize=(15, 11))
    colors = plt.get_cmap("tab10").colors[:K_star]

    # (a) state probability over time (stacked area of soft posterior gamma_K)
    ax1 = fig.add_subplot(3, 2, (1, 2))
    gamma = fit["gamma"]                        # (T, K)
    dates = df["date"].to_numpy()
    stk = np.cumsum(gamma, axis=1)
    prev = np.zeros(len(dates))
    for k in range(K_star):
        ax1.fill_between(dates, prev, stk[:, k], color=colors[k], alpha=0.85, label=f"S{k}")
        prev = stk[:, k]
    for name, s, e in CHAPTERS:
        ax1.axvline(pd.Timestamp(s), color="black", lw=0.7, ls="--", alpha=0.6)
        ax1.text(pd.Timestamp(s), 1.01, name, fontsize=8, rotation=0, ha="left", va="bottom")
    ax1.set_ylim(0, 1)
    ax1.set_ylabel("P(state | data)")
    ax1.set_title(f"(a) HMM soft state posterior over time  (K*={K_star} by BIC)")
    ax1.legend(loc="lower left", ncol=K_star, fontsize=8)

    # (b) transition matrix heatmap
    ax2 = fig.add_subplot(3, 2, 3)
    im = ax2.imshow(A, cmap="Blues", vmin=0, vmax=1)
    ax2.set_xticks(range(K_star)); ax2.set_yticks(range(K_star))
    ax2.set_xticklabels([f"S{k}" for k in range(K_star)])
    ax2.set_yticklabels([f"S{k}" for k in range(K_star)])
    for i in range(K_star):
        for j in range(K_star):
            ax2.text(j, i, f"{A[i,j]:.2f}", ha="center", va="center",
                     color="white" if A[i, j] > 0.5 else "black", fontsize=9)
    ax2.set_title("(b) Transition matrix A")
    fig.colorbar(im, ax=ax2, fraction=0.04)

    # (c) per-state feature means (z-scored — for cross-state comparison)
    ax3 = fig.add_subplot(3, 2, 4)
    z_means = np.array([fit["mu"][k] for k in range(K_star)])
    im2 = ax3.imshow(z_means, cmap="RdBu_r", vmin=-2, vmax=2, aspect="auto")
    ax3.set_xticks(range(len(FEATURES)))
    ax3.set_xticklabels(FEATURES, rotation=35, ha="right", fontsize=8)
    ax3.set_yticks(range(K_star))
    ax3.set_yticklabels([f"S{k}" for k in range(K_star)])
    for i in range(K_star):
        for j in range(len(FEATURES)):
            ax3.text(j, i, f"{z_means[i,j]:+.1f}", ha="center", va="center", fontsize=7)
    ax3.set_title("(c) Per-state feature means (z-score)")
    fig.colorbar(im2, ax=ax3, fraction=0.04)

    # (d) chapter × state composition
    ax4 = fig.add_subplot(3, 2, 5)
    chap_order = [c[0] for c in CHAPTERS]
    chap_order = [c for c in chap_order if c in chap_state_norm.index]
    bottom = np.zeros(len(chap_order))
    xs = np.arange(len(chap_order))
    for k in range(K_star):
        ys = np.array([chap_state_norm.loc[c, k] if k in chap_state_norm.columns else 0.0
                       for c in chap_order])
        ax4.bar(xs, ys, bottom=bottom, color=colors[k], label=f"S{k}")
        bottom += ys
    ax4.set_xticks(xs); ax4.set_xticklabels(chap_order, rotation=20, ha="right", fontsize=8)
    ax4.set_ylabel("share of days")
    ax4.set_title(f"(d) Chapter composition by state  (NMI={nmi:.3f})")
    ax4.legend(fontsize=8, loc="upper right")

    # (e) viterbi sequence strip + steps overlay
    ax5 = fig.add_subplot(3, 2, 6)
    # state strip
    state_arr = states.reshape(1, -1)
    ax5.imshow(state_arr, aspect="auto", cmap=matplotlib.colors.ListedColormap(colors),
               extent=[dates[0], dates[-1], 0, 1])
    ax5.set_yticks([])
    ax5b = ax5.twinx()
    ax5b.plot(dates, df["steps"].to_numpy(), color="black", lw=0.4, alpha=0.7)
    ax5b.set_ylabel("daily steps", fontsize=8)
    ax5.set_title("(e) Viterbi MAP state sequence + steps overlay")

    fig.suptitle(
        f"Gaussian HMM (numpy, Baum-Welch) on multi-stream daily features  "
        f"— T={len(df)} days, D={len(FEATURES)}, K*={K_star}",
        fontsize=12, y=0.995,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(FIG, dpi=140, bbox_inches="tight")
    print(f"saved figure -> {FIG}")

    # ----------------- JSON results -------------------------------------
    out = {
        "T": int(len(df)),
        "D": len(FEATURES),
        "features": FEATURES,
        "model_selection": {
            str(K): {"loglik": float(fits[K]["loglik"]), "bic": float(fits[K]["bic"]),
                     "n_params": int(fits[K]["n_params"])}
            for K in fits
        },
        "K_star": int(K_star),
        "transition_matrix": A.tolist(),
        "stationary_init": np.exp(fit["log_pi"]).tolist(),
        "expected_dwell_days": expected_dwell,
        "state_counts": state_counts,
        "state_means_z": {str(k): {f: float(fit["mu"][k, i]) for i, f in enumerate(FEATURES)}
                          for k in range(K_star)},
        "state_means_raw": state_means_raw,
        "chapter_state_share": {c: {str(k): float(chap_state_norm.loc[c, k])
                                    for k in chap_state_norm.columns}
                                for c in chap_state_norm.index},
        "chapter_dominant_state": {c: int(dominant[c]) for c in dominant},
        "chapter_dominant_purity": {c: float(chap_purity[c]) for c in chap_purity},
        "nmi_state_chapter": float(nmi),
        "figure_path": FIG,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"saved results -> {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
