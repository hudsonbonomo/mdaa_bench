"""Switching surrogate — piecewise-linear dynamics as a null for N and for M.

The dominant finding of grid v3: a two-regime world fires the N axis on ~25% of
runs and, over ten replicates, the M axis on 28% — more often than the world that
actually has memory (18%). Both are the same mistake seen twice. Piecewise-linear
dynamics are locally nonlinear (each regime has its own slope, so a single linear
map underfits and a polynomial recovers some of it), and pooled across regimes they
look history-dependent (yesterday's regime predicts today's, which reads as memory).

So the null both gates were missing is: could a LINEAR SWITCHING process have
produced this? Fit the two-regime model already in `switching.py`, simulate from
the fit, and recompute whichever statistic the gate uses.

    y_t = [y_{t-1}, u_{t-1}, 1] W_{z(t)} + e_{z(t)},   z a Markov chain

Regimes are drawn from the fitted transition matrix and the noise is resampled
from the fit's own residuals, per regime, rather than assumed Gaussian.

Stability: a surrogate must be a stable switching process, or it is not a null of
anything. The pair (A_1, A_2) read off the fit must admit a common quadratic
Lyapunov function (`stability.py`); when it does not, both matrices are scaled
down by the largest gamma that makes one exist, and the projection is reported.

Nothing here sees `truth`.
"""
from __future__ import annotations
import numpy as np
from .switching import fit_switching, _phi
from .stability import common_lyapunov

PROJECT_STEPS = 24          # bisection depth for the stability projection
GAMMA_FLOOR = 0.05          # below this the fit is degenerate, not merely unstable


def _A_of(W, d):
    """Autoregressive block of each regime: Phi = [y, u, 1], so rows 0..d-1 of W."""
    return [W[k][:d].T.copy() for k in range(len(W))]


def project_to_stable(W, d, target=0.97):
    """Scale every regime's A block by a common gamma until the pair admits a
    common quadratic Lyapunov function. Returns (W, gamma, ok).

    Scaling all regimes by the same gamma keeps their relative geometry, which is
    what makes the surrogate still a surrogate OF THIS FIT rather than of some
    other switching process.
    """
    W = W.copy()
    if common_lyapunov(_A_of(W, d))[0] is not None:
        return W, 1.0, True
    lo, hi = GAMMA_FLOOR, 1.0
    best = None
    for _ in range(PROJECT_STEPS):
        mid = 0.5 * (lo + hi)
        trial = W.copy()
        for k in range(len(trial)):
            trial[k][:d] *= mid
        if common_lyapunov(_A_of(trial, d))[0] is not None:
            best, lo = mid, mid
        else:
            hi = mid
    if best is None:
        return W, 1.0, False
    for k in range(len(W)):
        W[k][:d] *= best
    return W, float(best), True


def _residuals_by_regime(Phi, Y, W, z, K):
    """Per-regime residuals of the fit, for resampling."""
    out = []
    for k in range(K):
        sel = z == k
        out.append(Y[sel] - Phi[sel] @ W[k] if sel.any() else np.zeros((0, Y.shape[1])))
    return out


def _simulate(W, P, res, y0, u, rng, K):
    """One surrogate on the full grid: a regime path from the fitted chain, one
    step of the matching regime's map, and a residual resampled from that regime."""
    T, d = len(u), y0.shape[0]
    ys = np.zeros((T, d)); ys[0] = y0
    z = int(rng.integers(K))
    for t in range(1, T):
        z = int(rng.choice(K, p=P[z]))
        phi = np.concatenate([ys[t - 1], u[t - 1], [1.0]])
        e = res[z][rng.integers(len(res[z]))] if len(res[z]) else np.zeros(d)
        ys[t] = phi @ W[z] + e
    return ys


def switching_null(y, u, mask, kt, gain_fn, rng, n_surr: int = 49, min_dur: int = 25,
                   K: int = 2):
    """Null gains under "the world is a stable linear switching process".

    `gain_fn(y_grid) -> float` recomputes whatever statistic the calling gate uses,
    so the same null serves the N axis (nonlinear-vs-linear gain) and the M axis
    (memory-kernel gain). Returns (gains, info).
    """
    d = y.shape[1]
    obs = np.flatnonzero(mask)
    seen = set(obs.tolist())
    pairs = np.array([t for t in obs if t < kt and (t + 1) in seen], dtype=int)
    if len(pairs) < 4 * (d + u.shape[1] + 2):
        return np.array([0.0]), dict(note="train block too thin for a switching fit",
                                     projected=False, gamma=1.0, n_used=0)

    y0, y1, uu = y[pairs], y[pairs + 1], u[pairs]
    k = max(int(len(y0) * 0.7), 3)
    tr = (y0[:k], y1[:k], uu[:k])
    te = (y0[k:], y1[k:], uu[k:]) if len(y0) - k >= 2 else tr
    fit = fit_switching(tr, te, K=K, min_dur=min_dur)

    W, gamma, ok = project_to_stable(fit.W, d)
    Phi, Y = _phi(tr[0], tr[2]), tr[1]
    res = _residuals_by_regime(Phi, Y, W, fit.z[:len(Y)], K)

    gains = []
    for _ in range(n_surr):
        ys = _simulate(W, fit.P, res, y[obs[0]], u, rng, K)
        if not np.all(np.isfinite(ys)):
            continue
        g = gain_fn(ys)
        if np.isfinite(g):
            gains.append(float(g))
    info = dict(projected=gamma < 1.0, gamma=round(gamma, 4), lyapunov_ok=ok,
                n_used=len(gains),
                occupancy=round(float(np.mean(fit.z)), 3))
    return (np.array(gains) if gains else np.array([0.0])), info
