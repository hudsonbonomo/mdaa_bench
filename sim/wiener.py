"""Wiener surrogate for the N gate — linear dynamics seen through a static
output nonlinearity.

Finding 5 of the v1 bench: a tanh observation map roughly triples the N axis'
false-alarm rate. The linear surrogate null cannot see this, because the
surrogate it builds IS linear in y — it asks "could a linear process in y have
produced this?", and the answer is honestly no. The question that matters is
different: could a LINEAR LATENT process, seen through a static distortion,
have produced this? That is a Wiener system, and it is the null built here.

    z_t = A z_{t-1} + B u_{t-1} + w_t,  z observed with noise   (linear core)
    y_t = h(z_t),  h static, monotone, fitted                   (output map)

The latent z is constructed by rank-Gaussianising y (the amplitude adjustment
of AAFT, but with a state space instead of an FFT, so that gaps and inputs are
handled without interpolating anything). h is then fitted PARAMETRICALLY on the
(z, y) pairs — scaled tanh or cubic, whichever fits better — so the surrogate
generator is an explicit Wiener model that can be read off and audited.

Nothing here sees `truth`.
"""
from __future__ import annotations
import numpy as np
from .statespace import em_fit

TANH_SCALES = (0.25, 0.5, 1.0, 2.0, 4.0)


def rank_gaussianize(y, mask, rng):
    """Observed values -> normal scores, per coordinate, by rank. Monotone by
    construction, so it is a valid candidate for h^{-1}. Unobserved entries are
    left at zero; they are masked everywhere downstream and never interpolated."""
    z = np.zeros_like(y)
    idx = np.flatnonzero(mask)
    n = len(idx)
    scores = np.sort(rng.standard_normal(n))
    for c in range(y.shape[1]):
        order = np.argsort(y[idx, c], kind="stable")
        z[idx[order], c] = scores
    return z


def fit_static_h(z, y, mask):
    """Fit the static output map y = h(z) per coordinate. Returns (h, r2, family).

    Two declared families, no search beyond them: a scaled tanh with a linear
    term (saturation, the shape `observe()` actually applies) and a cubic
    (the shape the N gate's own feature map can express).
    """
    idx = np.flatnonzero(mask)
    d = y.shape[1]
    best = []
    for c in range(d):
        zc, yc = z[idx, c], y[idx, c]
        cands = []
        for b in TANH_SCALES:
            X = np.column_stack([np.tanh(b * zc), zc, np.ones_like(zc)])
            w, *_ = np.linalg.lstsq(X, yc, rcond=None)
            cands.append((float(np.mean((X @ w - yc) ** 2)), "tanh", b, w))
        X = np.column_stack([zc, zc ** 2, zc ** 3, np.ones_like(zc)])
        w, *_ = np.linalg.lstsq(X, yc, rcond=None)
        cands.append((float(np.mean((X @ w - yc) ** 2)), "cubic", 0.0, w))
        cands.sort(key=lambda t: t[0])
        var = float(np.var(yc)) + 1e-12
        best.append((cands[0], 1.0 - cands[0][0] / var))

    def h(zz):
        out = np.empty_like(zz)
        for c in range(d):
            (_, fam, b, w), _ = best[c]
            v = zz[:, c]
            if fam == "tanh":
                out[:, c] = w[0] * np.tanh(b * v) + w[1] * v + w[2]
            else:
                out[:, c] = w[0] * v + w[1] * v ** 2 + w[2] * v ** 3 + w[3]
        return out

    r2 = float(np.mean([r for _, r in best]))
    family = "+".join(sorted({cand[1] for cand, _ in best}))
    return h, r2, family


def _simulate(s, u, mask, rng):
    """One realisation of the fitted linear core, on the full grid."""
    T = len(u)
    d = s.A.shape[0]
    x = np.zeros((T, d))
    qs, rs = np.sqrt(np.diag(s.Q)), np.sqrt(np.diag(s.R))
    x[0] = s.mu0 + rng.normal(scale=np.sqrt(np.maximum(np.diag(s.P0), 0.0)))
    for t in range(1, T):
        x[t] = s.A @ x[t - 1] + s.B @ u[t - 1] + rng.normal(scale=qs)
    return x + rng.normal(scale=rs, size=x.shape)


def wiener_null(y, u, mask, kt, gain_fn, rng, n_surr: int = 49, n_iter: int = 10):
    """Null gains for the N statistic under "linear latent dynamics + static h".

    `gain_fn(y_grid) -> float` recomputes the pipeline's own nonlinear-vs-linear
    gain on a surrogate grid, so the surrogate is scored by exactly the statistic
    the gate uses. Returns (gains, info).
    """
    z = rank_gaussianize(y, mask, rng)
    h, r2, family = fit_static_h(z, y, mask)
    core = em_fit(z[:kt], u[:kt], mask[:kt], n_iter=n_iter)
    lo, hi = z[mask].min(0), z[mask].max(0)          # h is identified HERE and nowhere else;
    gains = []                                       # outside this range a cubic explodes and
    for _ in range(n_surr):                          # the surrogate stops being a surrogate
        ys = h(np.clip(_simulate(core, u, mask, rng), lo, hi))
        g = gain_fn(ys)
        if np.isfinite(g):                           # skip degenerate surrogates
            gains.append(float(g))
    info = dict(h_family=family, h_r2=round(r2, 4), n_used=len(gains))
    return np.array(gains) if gains else np.array([0.0]), info
