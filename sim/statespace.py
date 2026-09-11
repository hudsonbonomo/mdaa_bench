"""Linear-Gaussian state space, fitted by EM (Kalman filter + RTS smoother).

This is the measurement-noise-aware layer the v0 gates lacked. Model:

    x_t = A x_{t-1} + B u_{t-1} + w_t,   w ~ N(0, Q)     (latent dynamics)
    y_t =     x_t              + v_t,    v ~ N(0, R)     (what we observe)

Two cells of the roadmap rest on it:
  cell 1 (M gate)  a noisy observation of a Markov state is non-Markov in y;
                   the honest Markov baseline is this model's one-step-ahead
                   prediction, not an AR(1) fitted to y.
  cell 3 (S gate)  Q vs R is the process-noise / measurement-noise split. A
                   world with Q = 0 is deterministic dynamics seen through
                   noise; a world with Q > 0 is genuinely stochastic.

Gaps (keep_frac < 1) are handled as missing data: the filter simply skips the
update step. Nothing is interpolated. u is zero-filled where unobserved —
conservative: assume no logged intervention where nothing was logged.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass
class SSM:
    A: np.ndarray
    B: np.ndarray
    Q: np.ndarray            # process noise (diagonal)
    R: np.ndarray            # measurement noise (diagonal)
    mu0: np.ndarray
    P0: np.ndarray
    loglik: float = -np.inf

    @property
    def q_frac(self) -> float:
        """Share of one-step variance that is process noise. 0 = deterministic
        dynamics seen through noise; 1 = no measurement noise."""
        q, r = float(np.mean(np.diag(self.Q))), float(np.mean(np.diag(self.R)))
        return q / (q + r + 1e-12)


def to_grid(obs, t_max: int | None = None):
    """Observed -> (y, u, mask) on the regular integer time grid."""
    T = int(obs.t[-1]) + 1 if t_max is None else t_max
    d, m = obs.y.shape[1], obs.u.shape[1]
    y, u, mask = np.zeros((T, d)), np.zeros((T, m)), np.zeros(T, bool)
    sel = obs.t < T
    y[obs.t[sel]] = obs.y[sel]; u[obs.t[sel]] = obs.u[sel]; mask[obs.t[sel]] = True
    return y, u, mask


def kalman(s: SSM, y, u, mask):
    """Forward pass. Returns one-step-ahead means/covs (prediction, uses only
    y_{<t}), filtered means/covs, and the log-likelihood.

    The latent may be larger than the observation: the observation matrix is
    fixed to C = [I_d | 0], so an augmented state (memory.py) filters through
    the same code. With n = d every line below reduces to the plain C = I case."""
    T, d = y.shape
    n = s.A.shape[0]                       # latent dim; C = [I_d | 0], so n >= d
    xp, Pp = np.zeros((T, n)), np.zeros((T, n, n))
    xf, Pf = np.zeros((T, n)), np.zeros((T, n, n))
    ll = 0.0
    for t in range(T):
        if t == 0:
            xp[0], Pp[0] = s.mu0, s.P0
        else:
            xp[t] = s.A @ xf[t - 1] + s.B @ u[t - 1]
            Pp[t] = s.A @ Pf[t - 1] @ s.A.T + s.Q
        if mask[t]:
            S = Pp[t][:d, :d] + s.R
            Si = np.linalg.inv(S)
            K = Pp[t][:, :d] @ Si
            r = y[t] - xp[t][:d]
            xf[t] = xp[t] + K @ r
            Pf[t] = Pp[t] - K @ Pp[t][:d, :]
            ll += -0.5 * (np.linalg.slogdet(S)[1] + r @ Si @ r + d * np.log(2 * np.pi))
        else:
            xf[t], Pf[t] = xp[t], Pp[t]
    return xp, Pp, xf, Pf, float(ll)


def rts(s: SSM, xp, Pp, xf, Pf):
    """Backward pass. Returns smoothed means/covs and lag-one cross-covariance."""
    T, d = xf.shape
    xs, Ps, Pc = xf.copy(), Pf.copy(), np.zeros((T, d, d))
    J = np.zeros((T, d, d))
    for t in range(T - 2, -1, -1):
        J[t] = Pf[t] @ s.A.T @ np.linalg.inv(Pp[t + 1] + 1e-10 * np.eye(d))
        xs[t] = xf[t] + J[t] @ (xs[t + 1] - xp[t + 1])
        Ps[t] = Pf[t] + J[t] @ (Ps[t + 1] - Pp[t + 1]) @ J[t].T
    for t in range(1, T):
        Pc[t] = Ps[t] @ J[t - 1].T
    return xs, Ps, Pc


def _warm_start(y, u, mask, d, m):
    """Ridge one-step fit on consecutive observed pairs. Attenuated by
    measurement noise (errors in variables), but a much better EM start than
    A = I/2; the residual variance seeds Q + R."""
    ok = np.flatnonzero(mask[:-1] & mask[1:])
    if len(ok) < d + m + 2:
        return 0.5 * np.eye(d), np.zeros((d, m)), 1.0
    X = np.hstack([y[ok], u[ok], np.ones((len(ok), 1))])
    W = np.linalg.solve(X.T @ X + 1e-3 * np.eye(d + m + 1), X.T @ y[ok + 1])
    r = float(np.mean((y[ok + 1] - X @ W) ** 2)) + 1e-8
    return W[:d].T, W[d:d + m].T, r


def em_fit(y, u, mask, n_iter: int = 15, q_free: bool = True, tol: float = 1e-4) -> SSM:
    """EM for (A, B, Q, R, mu0, P0). q_free=False pins Q ~ 0: the restricted
    'deterministic dynamics + measurement noise' model used by the S gate.

    15 iterations is not convergence of the likelihood (EM still creeps), but
    the one-step predictive MSE the gates consume is flat to 4 decimals from
    ~10 iterations on, and the gates are its only consumer."""
    T, d = y.shape; m = u.shape[1]
    v = float(np.var(y[mask])) + 1e-8
    A0, B0, r0 = _warm_start(y, u, mask, d, m)          # moment-based init: EM
    Q0 = (0.6 * r0) * np.eye(d) if q_free else 1e-8 * np.eye(d)   # from a cold
    s = SSM(A0, B0, Q0, (0.4 * r0) * np.eye(d),                   # start needs
            y[mask][0].copy(), v * np.eye(d))                     # ~3x the iters
    prev = -np.inf
    for _ in range(n_iter):
        xp, Pp, xf, Pf, ll = kalman(s, y, u, mask)
        xs, Ps, Pc = rts(s, xp, Pp, xf, Pf)
        Szz = np.zeros((d + m, d + m)); Sxz = np.zeros((d, d + m)); Sxx = np.zeros((d, d))
        for t in range(1, T):
            z = np.concatenate([xs[t - 1], u[t - 1]])
            Ezz = np.outer(z, z); Ezz[:d, :d] += Ps[t - 1]
            Exz = np.outer(xs[t], z); Exz[:, :d] += Pc[t]
            Szz += Ezz; Sxz += Exz; Sxx += np.outer(xs[t], xs[t]) + Ps[t]
        AB = np.linalg.solve(Szz + 1e-6 * np.eye(d + m), Sxz.T).T
        A, B = AB[:, :d], AB[:, d:]
        Q = s.Q
        if q_free:
            Qn = Sxx - AB @ Sxz.T
            Q = np.diag(np.maximum(np.diag((Qn + Qn.T) / 2) / (T - 1), 1e-8))
        obs_t = np.flatnonzero(mask)
        res = y[obs_t] - xs[obs_t]
        Rd = (np.einsum("ti,ti->i", res, res) + np.einsum("tii->i", Ps[obs_t])) / len(obs_t)
        R = np.diag(np.maximum(Rd, 1e-8))
        s = SSM(A, B, Q, R, xs[0].copy(), Ps[0], ll)
        if ll - prev < tol * abs(prev):
            break
        prev = ll
    return s


def predict_mse(s: SSM, y, u, mask, idx) -> float:
    """One-step-ahead predictive MSE at times `idx`: E[y_t | y_{<t}] vs y_t.
    The filter runs over the whole grid but never uses y_t to predict y_t."""
    xp = kalman(s, y, u, mask)[0]
    return float(np.mean((y[idx] - xp[idx][:, :y.shape[1]]) ** 2))


def stochastic_null(s0: SSM, y, u, mask, kt, idx, rng, n_surr: int = 15, n_iter: int = 8):
    """Parametric bootstrap for the S gate: gains produced by a world that is
    genuinely deterministic.

    Simulate the FITTED Q ~ 0 model (A, B, mu0, measurement noise R, no process
    noise), refit both models on the train span, recompute the free-Q gain.
    This is needed because a Q ~ 0 filter has a vanishing Kalman gain: it
    predicts open-loop, so any error in A compounds across the test block and
    the free-Q model wins *even on deterministic data*. The null measures
    exactly that penalty, so the gate can charge for it.
    """
    T, d = y.shape
    sd = np.sqrt(np.diag(s0.R))
    xs = np.zeros((T, d))
    xs[0] = s0.mu0
    for t in range(1, T):
        xs[t] = s0.A @ xs[t - 1] + s0.B @ u[t - 1]
    out = []
    for _ in range(n_surr):
        ys = xs + rng.normal(scale=sd, size=xs.shape)
        a = em_fit(ys[:kt], u[:kt], mask[:kt], q_free=True, n_iter=n_iter)
        b = em_fit(ys[:kt], u[:kt], mask[:kt], q_free=False, n_iter=n_iter)
        m_free = predict_mse(a, ys, u, mask, idx)
        m_det = predict_mse(b, ys, u, mask, idx)
        out.append((m_det - m_free) / m_det)
    return np.array(out)
