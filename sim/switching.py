"""Switching linear dynamics by sticky EM — the H gate, cell 2 of the roadmap.

v0 recovered 0/8 planted regime structures with alternating assignment plus a
7-step box smoother. That detector had no model of *duration*: it could hand
back one-step regimes, and nothing tied its segments to a dwell time.

Here: K-regime linear-Gaussian switching regression,
    y_t = W_z(t) [y_{t-1}, u_{t-1}, 1] + e,   e ~ N(0, sig_z(t) I),  z a Markov chain.
EM with forward-backward (E step) and weighted ridge (M step). The
minimum-duration prior is a floor on the self-transition probability,
P_kk >= 1 - 1/min_dur — exactly "expected dwell time >= min_dur steps".

Scoring is one-step-ahead on the FUTURE block: the regime belief is propagated
by the filter (alpha @ P) and the prediction is the mixture over regimes.
y_t never enters the belief used to predict y_t.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np

LOG2PI = float(np.log(2 * np.pi))


@dataclass
class Switching:
    W: np.ndarray                # (K, f, d) regime regressions
    sig: np.ndarray              # (K,) isotropic noise per regime
    P: np.ndarray                # (K, K) transition matrix
    loglik: float
    z: np.ndarray                # MAP path over the train block
    mse_test: float              # one-step-ahead predictive MSE, future block
    z_all: np.ndarray = field(default_factory=lambda: np.empty(0, int))


def _phi(y0, u):
    return np.hstack([y0, u, np.ones((len(y0), 1))])


def _emission_ll(Phi, Y, W, sig):
    """(n, K) log N(Y ; Phi W_k, sig_k I)."""
    d = Y.shape[1]
    out = np.empty((len(Y), len(W)))
    for k in range(len(W)):
        r2 = np.sum((Y - Phi @ W[k]) ** 2, axis=1)
        out[:, k] = -0.5 * (r2 / sig[k] + d * (LOG2PI + np.log(sig[k])))
    return out


def _forward_backward(logB, P, pi):
    n, K = logB.shape
    logP = np.log(P + 1e-300)
    a = np.empty((n, K)); a[0] = np.log(pi + 1e-300) + logB[0]
    for t in range(1, n):
        m = a[t - 1].max()
        a[t] = logB[t] + m + np.log(np.exp(a[t - 1] - m) @ P + 1e-300)
    b = np.zeros((n, K))
    for t in range(n - 2, -1, -1):
        v = logB[t + 1] + b[t + 1]; m = v.max()
        b[t] = m + np.log(P @ np.exp(v - m) + 1e-300)
    mx = a[-1].max(); ll = float(mx + np.log(np.exp(a[-1] - mx).sum()))
    g = a + b; g -= g.max(1, keepdims=True); g = np.exp(g); g /= g.sum(1, keepdims=True)
    xi = np.zeros((K, K))
    for t in range(n - 1):
        e = a[t][:, None] + logP + (logB[t + 1] + b[t + 1])[None, :]
        e = np.exp(e - e.max()); xi += e / e.sum()
    return g, xi, ll


def _viterbi(logB, P, pi):
    n, K = logB.shape; logP = np.log(P + 1e-300)
    delta = np.log(pi + 1e-300) + logB[0]; psi = np.zeros((n, K), int)
    for t in range(1, n):
        e = delta[:, None] + logP
        psi[t] = e.argmax(0); delta = e.max(0) + logB[t]
    z = np.zeros(n, int); z[-1] = int(delta.argmax())
    for t in range(n - 2, -1, -1):
        z[t] = psi[t + 1, z[t + 1]]
    return z


def _viterbi_mindur(logB, P, pi, D):
    """Viterbi under a HARD minimum-duration constraint: no run shorter than D
    (the trailing run may be cut by the end of the block).

    The sticky prior alone is a floor on P_kk, which a confident likelihood can
    still overrule — v1 saw 2- and 3-step regimes survive the decode and veto
    the H gate's stability check. Here the constraint is in the state space:
    the state is (regime, steps-in-regime capped at D) and a switch is only
    reachable from a saturated counter.
    """
    n, K = logB.shape
    if D <= 1:
        return _viterbi(logB, P, pi)
    logP = np.log(P + 1e-300); NEG = -1e18
    delta = np.full((K, D), NEG); delta[:, 0] = np.log(pi + 1e-300) + logB[0]
    sat = np.zeros((n, K), bool)        # at (t, k, D-1): predecessor was already saturated
    frm = np.zeros((n, K), np.int16)    # at (t, k, 0): regime we switched away from
    for t in range(1, n):
        new = np.full((K, D), NEG)
        stay = delta + np.diag(logP)[:, None]
        new[:, 1:] = stay[:, :D - 1]
        hold = stay[:, D - 1] > new[:, D - 1]
        new[hold, D - 1] = stay[hold, D - 1]; sat[t] = hold
        sw = delta[:, D - 1][:, None] + logP          # (from, to); switching needs c = D-1
        np.fill_diagonal(sw, NEG)
        frm[t] = sw.argmax(0); new[:, 0] = sw.max(0)
        delta = new + logB[t][:, None]
    k, c = np.unravel_index(int(delta.argmax()), delta.shape)
    z = np.zeros(n, int); z[-1] = k
    for t in range(n - 1, 0, -1):
        if c == 0:
            k = int(frm[t, k]); c = D - 1
        elif not (c == D - 1 and sat[t, k]):
            c -= 1
        z[t - 1] = k
    return z


def _m_step(Phi, Y, g, lam):
    K = g.shape[1]; f = Phi.shape[1]; d = Y.shape[1]
    W = np.zeros((K, f, d)); sig = np.zeros(K)
    for k in range(K):
        w = g[:, k]; G = Phi.T * w
        W[k] = np.linalg.solve(G @ Phi + lam * np.eye(f), G @ Y)
        r2 = np.sum((Y - Phi @ W[k]) ** 2, axis=1)
        sig[k] = max(float(w @ r2 / (d * max(w.sum(), 1e-6))), 1e-8)
    return W, sig


def fit_switching(tr, te, K: int = 2, n_iter: int = 30, min_dur: int = 25,
                  lam: float = 1e-3) -> Switching:
    """tr/te are (y0, y1, u) blocks already split in time."""
    Phi, Y = _phi(tr[0], tr[2]), tr[1]
    n = len(Y); p_floor = 1.0 - 1.0 / max(min_dur, 2)
    best = None
    for init in range(2):                      # temporal halves, then a block clock
        z0 = (np.arange(n) >= n // 2) if init == 0 else (np.arange(n) % (2 * min_dur) >= min_dur)
        g = np.full((n, K), 1e-3); g[np.arange(n), z0.astype(int) % K] = 1.0
        g /= g.sum(1, keepdims=True)
        P = np.full((K, K), (1 - p_floor) / (K - 1)); np.fill_diagonal(P, p_floor)
        pi = np.full(K, 1.0 / K); ll = -np.inf; logB = None
        for _ in range(n_iter):
            W, sig = _m_step(Phi, Y, g, lam)
            logB = _emission_ll(Phi, Y, W, sig)
            g, xi, ll_new = _forward_backward(logB, P, pi)
            P = xi / xi.sum(1, keepdims=True)
            np.fill_diagonal(P, np.maximum(np.diag(P), p_floor))     # duration prior
            P /= P.sum(1, keepdims=True)
            pi = g[0] / g[0].sum()
            done = ll_new - ll < 1e-5 * abs(ll); ll = ll_new
            if done:
                break
        if best is None or ll > best[0]:
            best = (ll, W, sig, P, pi, _viterbi_mindur(logB, P, pi, min_dur))
    ll, W, sig, P, pi, z = best

    # future block, one step ahead: propagate the belief, predict the mixture
    Phi_te, Y_te = _phi(te[0], te[2]), te[1]
    logB_te = _emission_ll(Phi_te, Y_te, W, sig)
    alpha = np.zeros(K); alpha[z[-1]] = 1.0; se = 0.0
    for t in range(len(Y_te)):
        pw = alpha @ P
        yhat = sum(pw[k] * (Phi_te[t] @ W[k]) for k in range(K))
        se += float(np.sum((Y_te[t] - yhat) ** 2))
        lk = np.exp(logB_te[t] - logB_te[t].max()) * pw
        alpha = lk / max(lk.sum(), 1e-300)
    mse = se / (len(Y_te) * Y_te.shape[1])

    z_all = _viterbi_mindur(_emission_ll(np.vstack([Phi, Phi_te]), np.vstack([Y, Y_te]), W, sig),
                            P, pi, min_dur)
    return Switching(W=W, sig=sig, P=P, loglik=float(ll), z=z, mse_test=mse, z_all=z_all)


def switch_times(z, t_src):
    """Regime changes as times on the original clock. Pair j predicts the state
    at t_src[j] + 1, so a label change between j-1 and j is a switch there."""
    return t_src[np.flatnonzero(np.diff(z)) + 1] + 1


def match_switches(planted, recovered, tol: int = 10):
    """Greedy nearest-neighbour matching within +/- tol steps."""
    planted = np.asarray(planted, float).ravel(); recovered = np.asarray(recovered, float).ravel()
    if len(planted) == 0 and len(recovered) == 0:
        return dict(n_planted=0, n_recovered=0, matched=0, precision=1.0, recall=1.0, mae=float("nan"))
    free = list(range(len(recovered))); errs = []
    for p in planted:
        if not free:
            break
        k = min(free, key=lambda i: abs(recovered[i] - p))
        if abs(recovered[k] - p) <= tol:
            free.remove(k); errs.append(abs(recovered[k] - p))
    return dict(n_planted=len(planted), n_recovered=len(recovered), matched=len(errs),
                precision=round(len(errs) / max(len(recovered), 1), 3),
                recall=round(len(errs) / max(len(planted), 1), 3),
                mae=round(float(np.mean(errs)), 2) if errs else float("nan"))
