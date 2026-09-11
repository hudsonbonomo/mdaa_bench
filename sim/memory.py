"""The M axis, decided in latent space instead of on AR(p) rows.

Two findings forced this. Finding 2: a 2-dimensional latent Markov state seen
through noise already mimics a decaying memory kernel, so AR(p) beating AR(1)
proves nothing. Finding 6: AR(p) needs p CONSECUTIVE observations, and the bench
refuses to interpolate, so at keep_frac 0.5 the design had zero usable rows and
the axis could not be tested at all.

Both competitors here are missing-aware state spaces scored one step ahead on
the same future observations:

  Markov baseline   free linear-Gaussian SSM, latent dim d+k for k in {1,2}.
                    "Give the Markov story a bigger state and see if that is
                    enough." The baseline takes the BEST k, which makes the M
                    axis harder to earn — the direction a sceptical gate wants.
  Memory model      AR(p) with measurement noise, written in companion form:
                    latent [z_t, z_{t-1}, ..., z_{t-p+1}], only the top block
                    row and the top noise block are free. A genuine decaying
                    kernel, of latent dim p*d, far more constrained than a free
                    SSM of the same size.

M is earned only when the kernel beats the best augmented Markov story. AR(6) on
consecutive rows survives as a reported diagnostic; it no longer decides.

Nothing here sees `truth`.
"""
from __future__ import annotations
import numpy as np
from .statespace import SSM, kalman, rts, predict_mse

Q_FLOOR = 1e-9          # keeps the companion shift blocks invertible for the smoother
LAG_PENALTY = 0.05      # declared decay prior on the kernel; see em_aug


def _lag_warm_start(y, u, mask, d, p):
    """Ridge AR(p) on whatever fully-observed runs of length p+1 exist. Starting
    the companion EM from zeroed lag blocks leaves it at AR(1) for many
    iterations; at latent dim p*d that is the difference between fitting the
    kernel and reporting noise. Returns (A_top, B_top) or None if no run exists."""
    T = len(y)
    ok = np.array([t for t in range(p, T) if mask[t - p:t + 1].all()], dtype=int)
    if len(ok) < 3 * (p * d + u.shape[1] + 1):
        return None
    X = np.array([np.concatenate([y[t - p:t][::-1].ravel(), u[t - 1]]) for t in ok])
    Y = y[ok]
    W = np.linalg.solve(X.T @ X + 1e-2 * np.eye(X.shape[1]), X.T @ Y)
    return W[:p * d].T, W[p * d:].T


def _project_stable(A, d, companion, cap=0.98, target=0.97):
    """Keep both competitors inside the unit circle.

    A companion fit sits close to the edge often (seed 3 of M1+M: radius 0.9912),
    and `predict_mse` filters the whole grid with train-block parameters, so an
    almost-unstable fit degrades across the test block and loses a contest it
    should win. Scaling lag block j by gamma^j maps every eigenvalue to gamma*lambda,
    which is the companion-form version of what `nonlinear_null` already does to
    keep its surrogate a stable linear process.
    """
    rad = float(max(abs(np.linalg.eigvals(A))))
    if rad < cap or rad == 0.0:
        return A
    g = target / rad
    A = A.copy()
    if companion:
        for j in range(A.shape[0] // d):
            A[:d, j * d:(j + 1) * d] *= g ** (j + 1)
    else:
        A *= g
    return A


def _init(y, u, mask, n, d, companion, p=None):
    m = u.shape[1]
    v = float(np.var(y[mask])) + 1e-8
    A = np.zeros((n, n))
    A[:d, :d] = 0.5 * np.eye(d)
    B = np.zeros((n, m))
    if companion:
        A[d:, :-d] = np.eye(n - d)                      # the shift, fixed forever
        warm = _lag_warm_start(y, u, mask, d, p)
        if warm is not None:
            A[:d, :], B[:d, :] = warm
    else:
        A[d:, d:] = 0.5 * np.eye(n - d)
        # The competitors must be matched in ESTIMATION effort, not just given the
        # same iteration count. Warm-starting only the companion made it win by
        # 0.14 on a world with no memory at all — an initialisation artefact that
        # reads exactly like the axis it is supposed to test. Same one-step ridge
        # start for the observed block here.
        warm = _lag_warm_start(y, u, mask, d, 1)
        if warm is not None:
            A[:d, :d], B[:d, :] = warm[0][:, :d], warm[1]
    q = np.full(n, Q_FLOOR); q[:d] = 0.6 * v
    if not companion:
        q[:] = 0.6 * v
    mu0 = np.zeros(n); mu0[:d] = y[mask][0]
    return SSM(A, B, np.diag(q), (0.4 * v) * np.eye(d), mu0, v * np.eye(n))


def em_aug(y, u, mask, n_latent, n_iter=12, companion=False, tol=1e-4) -> SSM:
    """EM for a latent of dimension n_latent >= d, observed as C = [I_d | 0].

    companion=True pins everything except the top block row of A, the top block
    of B and the top block of Q: that is exactly an AR(p) kernel with measurement
    noise, and it is the memory model. companion=False leaves A free: that is the
    augmented Markov baseline.
    """
    T, d = y.shape
    n, m = n_latent, u.shape[1]
    s = _init(y, u, mask, n, d, companion, p=n // d if companion else None)
    shift = s.A[d:, :].copy()                           # preserved across M-steps
    prev = -np.inf
    for _ in range(n_iter):
        xp, Pp, xf, Pf, ll = kalman(s, y, u, mask)
        xs, Ps, Pc = rts(s, xp, Pp, xf, Pf)
        Szz = np.zeros((n + m, n + m)); Sxz = np.zeros((n, n + m)); Sxx = np.zeros((n, n))
        for t in range(1, T):
            z = np.concatenate([xs[t - 1], u[t - 1]])
            Ezz = np.outer(z, z); Ezz[:n, :n] += Ps[t - 1]
            Exz = np.outer(xs[t], z); Exz[:, :n] += Pc[t]
            Szz += Ezz; Sxz += Exz; Sxx += np.outer(xs[t], xs[t]) + Ps[t]
        rows = d if companion else n                    # companion: only the top row is free
        pen = np.full(n + m, 1e-6)
        if companion:
            # The declared model class is a DECAYING kernel, so the prior charges
            # lag j at rate (j+1)^2: a far lag has to earn its place. Without it
            # the latent-(p*d) M-step overfits lags 3-6 into noise and the memory
            # model loses out of sample to a free SSM half its size.
            pen[:n] = LAG_PENALTY * (np.arange(n) // d + 1.0) ** 2 * np.trace(Szz[:n, :n]) / n
        AB = np.linalg.solve(Szz + np.diag(pen), Sxz[:rows].T).T
        A = s.A.copy(); B = np.zeros((n, m))
        A[:rows] = AB[:, :n]; B[:rows] = AB[:, n:]
        if companion:
            A[d:] = shift
        A = _project_stable(A, d, companion)
        Qn = Sxx - np.hstack([A, B]) @ Sxz.T           # full transition, not just the free rows
        qd = np.maximum(np.diag((Qn + Qn.T) / 2) / (T - 1), Q_FLOOR)
        if companion:
            qd[d:] = Q_FLOOR                            # the shift is deterministic
        obs_t = np.flatnonzero(mask)
        res = y[obs_t] - xs[obs_t][:, :d]
        Rd = (np.einsum("ti,ti->i", res, res) + np.einsum("tii->i", Ps[obs_t][:, :d, :d])) / len(obs_t)
        s = SSM(A, B, np.diag(qd), np.diag(np.maximum(Rd, 1e-8)), xs[0].copy(), Ps[0], ll)
        if ll - prev < tol * abs(prev):
            break
        prev = ll
    return s


def markov_baseline(y, u, mask, kt, idx, ks=(1, 2), n_iter=12):
    """Best augmented Markov story. Returns (mse, k, per_k)."""
    d = y.shape[1]
    out = {}
    for k in ks:
        s = em_aug(y[:kt], u[:kt], mask[:kt], d + k, n_iter=n_iter)
        out[k] = predict_mse(s, y, u, mask, idx)
    k_best = min(out, key=out.get)
    return out[k_best], k_best, out


def memory_model(y, u, mask, kt, idx, p, n_iter=12):
    """AR(p)-with-measurement-noise in companion form. Returns (mse, ssm)."""
    d = y.shape[1]
    s = em_aug(y[:kt], u[:kt], mask[:kt], p * d, n_iter=n_iter, companion=True)
    return predict_mse(s, y, u, mask, idx), s


def kernel_profile(s: SSM, d: int, p: int):
    """The fitted decay profile: ||A_j|| per lag j. Reported, not gated — it is
    what makes an M activation readable as 'memory' rather than 'more state'."""
    return [float(np.linalg.norm(s.A[:d, j * d:(j + 1) * d])) for j in range(p)]


def memory_contest(y, u, mask, kt, idx, p=6, ks=(1, 2), n_iter=12):
    """The M gate. Returns a dict; the caller applies TOL to `gain`."""
    if len(idx) < 5 or kt < 20:
        return dict(gain=float("nan"), note="future block or train span too short")
    m_mk, k_best, per_k = markov_baseline(y, u, mask, kt, idx, ks, n_iter)
    m_mem, s_mem = memory_model(y, u, mask, kt, idx, p, n_iter)
    d = y.shape[1]
    gain = (m_mk - m_mem) / m_mk if m_mk > 0 else float("nan")
    return dict(gain=float(gain), mse_markov=float(m_mk), mse_memory=float(m_mem),
                k_best=int(k_best), per_k={int(k): float(v) for k, v in per_k.items()},
                profile=kernel_profile(s_mem, d, p),
                note=f"AR({p}) kernel vs best free SSM of latent dim d+{k_best}")


def _simulate(s, u, mask, rng, d):
    """One realisation of a fitted SSM on the full grid, observed through C."""
    T, n = len(u), s.A.shape[0]
    x = np.zeros((T, n))
    qs = np.sqrt(np.diag(s.Q)); rs = np.sqrt(np.diag(s.R))
    x[0] = s.mu0
    for t in range(1, T):
        x[t] = s.A @ x[t - 1] + s.B @ u[t - 1] + rng.normal(scale=qs)
    return x[:, :d] + rng.normal(scale=rs, size=(T, d))


def markov_null(y, u, mask, kt, idx, rng, p=6, ks=(1, 2), n_surr=9, n_iter=12):
    """Gains produced by a world that is genuinely Markov.

    The two competitors are not matched in estimation quality: the memory model
    is latent p*d with a decay prior, the baseline is latent d+k and free. On a
    LINEAR world at keep 0.5 / noise 0.3 the memory model won by up to 0.14 —
    on regularisation, not on memory. That confound is what this null prices.
    Simulate from the fitted Markov baseline, refit both, recompute the gain.
    """
    d = y.shape[1]
    s_mk = em_aug(y[:kt], u[:kt], mask[:kt], d + ks[-1], n_iter=n_iter)
    out = []
    for _ in range(n_surr):
        ys = _simulate(s_mk, u, mask, rng, d)
        if not np.all(np.isfinite(ys)):
            continue
        m_mk, _, _ = markov_baseline(ys, u, mask, kt, idx, ks, n_iter)
        m_mem, _ = memory_model(ys, u, mask, kt, idx, p, n_iter)
        if m_mk > 0:
            out.append((m_mk - m_mem) / m_mk)
    return np.array(out) if out else np.array([0.0])
