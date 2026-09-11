"""Identification pipeline v1 — blind to the generator.

Paper 2 §9: descriptive baseline M0, linear Markov M1, and the reversible axes
N (nonlinear), H (hybrid), M (memory), S (stochastic), each earned only by
held-out gain on a FUTURE temporal block. No fit ever sees `truth`, and every
fit is ridge least squares or EM in closed form — no ML dependency.

Changed from v0 (roadmap cells 1-3):
  M  the reference is no longer AR(1) on y. A noisy view of a Markov state is
     non-Markov in y, so that baseline was a straw man the v0 M axis kept
     beating. Now: the best of AR(1) and the state space (statespace.py).
  H  alternating assignment -> sticky EM with a minimum-duration prior, scored
     one step ahead on the future block, reporting switch times (switching.py).
  S  new: free-Q state space vs the same model with Q pinned to ~0, calibrated
     against a deterministic-world null. Reported as an axis but kept OUT of the
     node string, so the recovery map stays comparable with v0.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from .observe import Observed, regular_pairs, pair_times
from .statespace import to_grid, em_fit, predict_mse, stochastic_null
from .switching import fit_switching, switch_times
from .wiener import wiener_null
from .switching_null import switching_null
from .memory import memory_contest, markov_null
from .density import h3_memory, PASS, FAIL, UNIDENTIFIABLE

TOL = 0.03          # minimum relative held-out gain to activate an axis
NULL_Q = 0.95       # surrogate quantile the N statistic must exceed
N_SURR = 49         # surrogates per test (cheap; raise on the server)
MIN_SEG = 25        # minimum regime segment length for H stability
MEM_P = 6           # AR order for the M axis
M_SURR = 9          # surrogates for the M null (each one refits both competitors)
M_ITERS = 25        # EM iterations for BOTH M competitors — matched on purpose
MIN_REPLICATES = 10 # fewer replicates than this and H3's mean is noise, so the
                    # M verdict stays 'nao identificavel' rather than guessing
S_SURR = 15         # surrogates for the S null (each one costs two EM fits)
S_QFRAC = 0.5       # Q/(Q+R) floor for S. A DECLARED PRIOR, not a tuned cutoff:
                    # "at least half the one-step variance" is the plain reading of
                    # "the dynamics are stochastic". The held-out contest alone is
                    # not enough — see the deterministic control in the README.


def _ridge(X, Y, lam=1e-3):
    X1 = np.hstack([X, np.ones((len(X), 1))])
    return np.linalg.solve(X1.T @ X1 + lam * np.eye(X1.shape[1]), X1.T @ Y)


def _pred(W, X):
    return np.hstack([X, np.ones((len(X), 1))]) @ W


def _mse(a, b):
    return float(np.mean((a - b) ** 2))


def _poly(X):
    """Degree-2 cross terms plus per-coordinate cubics (double-well needs x^3)."""
    cols = [X]; d = X.shape[1]
    for i in range(d):
        for j in range(i, d):
            cols.append((X[:, i] * X[:, j])[:, None])
        cols.append((X[:, i] ** 3)[:, None])
    return np.hstack(cols)


@dataclass
class Fit:
    node: str
    mse_test: dict = field(default_factory=dict)
    gains: dict = field(default_factory=dict)
    axes: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)
    switches: np.ndarray = field(default_factory=lambda: np.empty(0, int))
    kernel_profile: list = field(default_factory=list)
    hardest: dict = field(default_factory=dict)   # axis -> which null bound the gate
    verdicts: dict = field(default_factory=dict)  # axis -> passa / falha / nao identificavel


def _split(y0, y1, u, frac=0.7):
    n = len(y0); k = int(n * frac)
    return (y0[:k], y1[:k], u[:k]), (y0[k:], y1[k:], u[k:])


def _lin_feats(y, u):
    return np.hstack([y, u])


def fit_linear(tr, te):
    W = _ridge(_lin_feats(tr[0], tr[2]), tr[1])
    return W, _mse(_pred(W, _lin_feats(te[0], te[2])), te[1])


def fit_nonlinear(tr, te):
    W = _ridge(np.hstack([_poly(tr[0]), tr[2]]), tr[1], lam=1e-2)
    return W, _mse(_pred(W, np.hstack([_poly(te[0]), te[2]])), te[1])


def nonlinear_null(tr, te, W_lin, rng):
    """Parametric bootstrap: simulate the FITTED linear model with resampled
    residuals, recompute the nonlinear-vs-linear gain. Returns null gains."""
    y0, y1, u = tr
    resid = y1 - _pred(W_lin, _lin_feats(y0, u))
    d = y0.shape[1]; W_lin = W_lin.copy()
    rad = max(abs(np.linalg.eigvals(W_lin[:d].T)))
    if rad >= 0.98:                       # a linear fit to nonlinear data can be unstable;
        W_lin[:d] *= 0.97 / rad           # the null must be a STABLE linear stochastic process
    n_tr, n_te = len(y0), len(te[0]); gains = []
    for _ in range(N_SURR):
        n = n_tr + n_te + 1
        ys = np.zeros((n, d)); ys[0] = y0[0]
        uu = np.vstack([u, te[2], te[2][:1]])
        for t in range(1, n):
            e = resid[rng.integers(len(resid))]
            ys[t] = _pred(W_lin, _lin_feats(ys[t - 1:t], uu[t - 1:t]))[0] + e
        s_tr = (ys[:n_tr], ys[1:n_tr + 1], uu[:n_tr])
        s_te = (ys[n_tr:n - 1], ys[n_tr + 1:], uu[n_tr:n - 1])
        _, m_l = fit_linear(s_tr, s_te); _, m_n = fit_nonlinear(s_tr, s_te)
        gains.append((m_l - m_n) / m_l)
    return np.array(gains)


def _gain_fn(obs: Observed, ug, mg):
    """Recompute the N statistic on a surrogate grid, through exactly the design
    the gate itself uses: consecutive observed pairs, same 70/30 temporal split."""
    ok = np.flatnonzero(np.diff(obs.t) == 1)
    src, dst = obs.t[ok], obs.t[ok] + 1

    def gain(ys):
        y0, y1, uu = ys[src], ys[dst], ug[src]
        s_tr, s_te = _split(y0, y1, uu)
        if len(s_te[0]) < 10:
            return float("nan")
        if not np.all(np.isfinite(ys)):
            return float("nan")
        _, m_l = fit_linear(s_tr, s_te)
        _, m_nl = fit_nonlinear(s_tr, s_te)
        g = (m_l - m_nl) / m_l if m_l > 0 else float("nan")
        return g if np.isfinite(g) else float("nan")
    return gain


def memory_design(obs: Observed, p=MEM_P):
    """AR(p) design on consecutive runs of length >= p+1. Irregular gaps are
    dropped, never interpolated: interpolation would invent dynamics."""
    t, y, u = obs.t, obs.y, obs.u
    rows = np.array([i for i in range(p, len(t)) if t[i] - t[i - p] == p], dtype=int)
    if len(rows) == 0:
        return rows, np.empty((0, p * y.shape[1] + u.shape[1])), np.empty((0, y.shape[1]))
    X = np.array([np.hstack([y[j - p:j].ravel(), u[j - 1]]) for j in rows])
    return rows, X, y[rows]


def fit_memory(obs: Observed, t_split: int, p=MEM_P):
    """AR(p) and AR(1) on the same rows, split on the original clock. Returns
    (mse_arp, mse_ar1, eval_times), or None if the design is too thin."""
    rows, X, Y = memory_design(obs, p)
    if len(rows) == 0:
        return None
    d, m = obs.y.shape[1], obs.u.shape[1]
    is_tr = obs.t[rows] < t_split
    if is_tr.sum() < 4 * (p * d + m) or (~is_tr).sum() < 5:
        return None
    X1 = np.hstack([X[:, (p - 1) * d:p * d], X[:, -m:]])          # last lag + u = AR(1)
    m_p = _mse(_pred(_ridge(X[is_tr], Y[is_tr], lam=1e-2), X[~is_tr]), Y[~is_tr])
    m_1 = _mse(_pred(_ridge(X1[is_tr], Y[is_tr]), X1[~is_tr]), Y[~is_tr])
    return m_p, m_1, obs.t[rows[~is_tr]]


def identify(obs, seed=0, s_null: bool = True, m_null: bool = True) -> Fit:
    """`obs` is an Observed, or a list of Observed that are REPLICATES OF THE SAME
    person. Everything except the M axis is fitted on the first trajectory; the M
    axis needs the replicates and says so when it does not have them."""
    ens_list = list(obs) if isinstance(obs, (list, tuple)) else None
    if ens_list is not None:
        assert len(ens_list) >= 1, "empty ensemble"
        obs = ens_list[0]
    rng = np.random.default_rng(seed + 20_000)
    y0, y1, u = regular_pairs(obs)
    ts = pair_times(obs)
    tr, te = _split(y0, y1, u)
    t_split = int(ts[len(tr[0])]) if len(tr[0]) < len(ts) else int(ts[-1])
    fit = Fit(node="M1")
    fit.mse_test["M0"] = _mse(te[0], te[1])                      # persistence baseline
    W_lin, fit.mse_test["M1"] = fit_linear(tr, te)
    fit.gains["M1_vs_M0"] = (fit.mse_test["M0"] - fit.mse_test["M1"]) / fit.mse_test["M0"]
    if fit.gains["M1_vs_M0"] < TOL:
        fit.node = "M0"; fit.verdicts["M"] = UNIDENTIFIABLE
        fit.notes.append("linear state model adds no held-out value"); return fit
    base = fit.mse_test["M1"]

    # grid form of the same data; the state space and the Wiener null both need it
    yg, ug, mg = to_grid(obs)
    kt = max(min(t_split, len(yg)), 20)

    # N axis: held-out gain against TWO nulls.
    #   linear  — could a linear process in y have done this?
    #   Wiener  — could a linear LATENT process seen through a static h have
    #             done this? (finding 5: a tanh observation map fabricates N)
    # The axis is earned only against the harder of the two.
    gain_fn = _gain_fn(obs, ug, mg)
    _, m_n = fit_nonlinear(tr, te); g_n = (base - m_n) / base
    q_lin = float(np.quantile(nonlinear_null(tr, te, W_lin, rng), NULL_Q))
    w_null, w_info = wiener_null(yg, ug, mg, kt, gain_fn, rng, N_SURR)
    q_wie = float(np.quantile(w_null, NULL_Q))
    sw_null, sw_info = switching_null(yg, ug, mg, kt, gain_fn, rng, N_SURR, min_dur=MIN_SEG)
    q_swi = float(np.quantile(sw_null, NULL_Q))
    fit.gains["N"] = g_n
    fit.gains["N_null_linear_q95"] = q_lin
    fit.gains["N_null_wiener_q95"] = q_wie
    fit.gains["N_null_switching_q95"] = q_swi
    qs = {"linear": q_lin, "wiener": q_wie, "switching": q_swi}
    fit.hardest["N"] = max(qs, key=qs.get)                       # the binding one
    fit.gains["N_null_q95"] = qs[fit.hardest["N"]]
    fit.notes.append(f"N wiener null: h={w_info['h_family']} r2={w_info['h_r2']}")
    fit.notes.append(f"N switching null: gamma={sw_info['gamma']} "
                     f"projected={sw_info['projected']} n={sw_info['n_used']}")
    fit.axes["N"] = bool(g_n > TOL and g_n > fit.gains["N_null_q95"])
    fit.verdicts["N"] = PASS if fit.axes["N"] else FAIL

    # H axis: sticky EM, one-step-ahead on the future block, + stability + not u
    sw = fit_switching(tr, te, min_dur=MIN_SEG)
    ref = min(base, m_n); g_h = (ref - sw.mse_test) / ref
    fit.mse_test["H"] = sw.mse_test; fit.gains["H"] = g_h
    segs = np.diff(np.flatnonzero(np.r_[1, np.diff(sw.z) != 0, 1]))
    occ = float(sw.z.mean())
    # interior runs are >= MIN_SEG by construction of the decoder; the trailing
    # run is cut by the end of the block, so the check is on the median, not min
    stable = bool(len(segs) >= 2 and np.median(segs) >= MIN_SEG and 0.05 < occ < 0.95)
    pulse = (tr[2][:, 0] != 0).astype(float)
    aligned = abs(np.corrcoef(sw.z, pulse)[0, 1]) if (sw.z.std() > 0 and pulse.std() > 0) else 0.0
    fit.axes["H"] = bool(g_h > TOL and stable and aligned < 0.5)
    fit.verdicts["H"] = PASS if fit.axes["H"] else FAIL
    fit.gains["H_u_alignment"] = float(aligned)
    fit.switches = switch_times(sw.z_all, ts)

    # state space fitted on the TRAIN span only; feeds the M and S gates
    ssm = em_fit(yg[:kt], ug[:kt], mg[:kt], q_free=True)
    ssm0 = em_fit(yg[:kt], ug[:kt], mg[:kt], q_free=False)

    # M axis. On ONE trajectory this is not a gate, it is a diagnostic, and the
    # verdict is the third value. Finding 8 of v2 fixed the ceiling: the memory
    # kernel beats the best free d+k state space by 0-11% even when handed the
    # TRUE kernel, against an estimation-noise floor of +-0.14 measured on a world
    # with no memory at all. An axis whose effect is an order of magnitude below
    # the noise of its own instrument is not absent — it is undecidable, and
    # collapsing that into False would let the recovery map count it as a correct
    # rejection. Over REPLICATES the same contest separates cleanly, so that is
    # where the verdict comes from (H3, density.py).
    ev_m = obs.t[obs.t >= t_split]
    con = memory_contest(yg, ug, mg, kt, ev_m, p=MEM_P, n_iter=M_ITERS)
    fit.gains["M"] = con["gain"]
    fit.notes.append(con["note"])
    if np.isfinite(con["gain"]):
        fit.gains["M_k_best"] = float(con["k_best"])
        fit.kernel_profile = con["profile"]

    if ens_list is not None and len(ens_list) >= MIN_REPLICATES:
        h3 = h3_memory(ens_list, p=MEM_P, n_iter=M_ITERS)
        # H3 PASSES when the ensemble is effectively Markov, so the M axis is
        # earned exactly when H3 fails. Polarity stated here once.
        fit.verdicts["M"] = (UNIDENTIFIABLE if h3.verdict == UNIDENTIFIABLE
                             else (FAIL if h3.passed else PASS))
        fit.gains["M_h3"] = h3.stat
        fit.notes.append("M decided over replicates: " + h3.note)
        fit.hardest["M"] = "h3_over_replicates"
    else:
        fit.verdicts["M"] = UNIDENTIFIABLE
        why = ("single trajectory" if ens_list is None
               else f"only {len(ens_list)} replicates, {MIN_REPLICATES} needed")
        fit.notes.append(f"M not identifiable in this design ({why}); the latent contest "
                         f"is reported as a diagnostic only — see README finding 8")
        if m_null and np.isfinite(con["gain"]):
            # the null cannot change a verdict that is already undecidable, so it
            # only runs when someone explicitly asks for the calibrated diagnostic
            nl_m = markov_null(yg, ug, mg, kt, ev_m, rng, p=MEM_P,
                               n_surr=M_SURR, n_iter=M_ITERS)
            fit.gains["M_null_q95"] = float(np.quantile(nl_m, NULL_Q))
    fit.axes["M"] = fit.verdicts["M"] == PASS

    # AR(6) on consecutive rows: REPORTED, no longer deciding. It is the statistic
    # v0 used and v1 corrected, kept so the three versions stay comparable.
    mem = fit_memory(obs, t_split)
    if mem is None:
        fit.notes.append("AR diagnostic unavailable: design too thin")
    else:
        m_p, m_1, ev = mem
        m_ss = predict_mse(ssm, yg, ug, mg, ev)
        fit.gains["M_diag_vs_AR1"] = (m_1 - m_p) / m_1
        fit.gains["M_diag_vs_SS"] = (m_ss - m_p) / m_ss

    # S axis: does the world need process noise, or is it deterministic + sensor noise?
    ev_s = obs.t[obs.t >= t_split]
    if len(ev_s) >= 5:
        m_free = predict_mse(ssm, yg, ug, mg, ev_s)
        m_det = predict_mse(ssm0, yg, ug, mg, ev_s)
        g_s = (m_det - m_free) / m_det
        fit.gains["S"] = g_s
        fit.gains["S_q_frac"] = ssm.q_frac                 # the Q/(Q+R) decomposition
        enough_q = ssm.q_frac > S_QFRAC
        if s_null:
            nl = stochastic_null(ssm0, yg, ug, mg, kt, ev_s, rng, S_SURR)
            fit.gains["S_null_q95"] = float(np.quantile(nl, NULL_Q))
            fit.axes["S"] = bool(g_s > TOL and g_s > fit.gains["S_null_q95"] and enough_q)
        else:
            fit.axes["S"] = bool(g_s > TOL and enough_q)
            fit.notes.append("S gate uncalibrated (s_null=False)")
    else:
        fit.axes["S"] = False; fit.notes.append("S gate skipped: future block too short")

    on = [k for k in ("N", "H", "M") if fit.axes[k]]
    fit.node = "M1" + "".join("+" + k for k in on)
    fit.notes.append("S axis reported separately, not part of the node string")
    return fit
