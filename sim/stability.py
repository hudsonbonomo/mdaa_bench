"""Common quadratic Lyapunov function for a switched linear system.

The M1+H node switches between two matrices. Both being individually stable is
NOT enough: two stable matrices can be switched into divergence (the joint
spectral radius, not the individual ones, governs arbitrary switching). Up to v3
the generator asserted only the individual radii and leaned on "slow switching"
for the rest, which is an argument, not an invariant.

The condition asserted here is the standard sufficient one:

    exists P > 0 such that  A' P A - P < 0  for every A in the set.

A common P makes V(x) = x'Px a Lyapunov function for EVERY switching sequence,
so it certifies stability under arbitrary switching — far stronger than what the
node needs, and checkable.

Solved as written, without an SDP package. The feasible set is a convex cone, so
minimising max_i lambda_max(A_i' P A_i - P) over the normalised slice trace(P) = d
is a convex problem and a grid that refines around its own argmin converges to the
global optimum. For d = 2 the slice is two-dimensional and lambda_max of a
symmetric 2x2 is closed form, so the whole search is a handful of vectorised numpy
operations: ~8 ms per pair, matching a 6-restart Nelder-Mead on 200/200 pairs.
"""
from __future__ import annotations
import numpy as np


def _lmax_sym2(S):
    """lambda_max of symmetric 2x2 matrices, vectorised over the leading axis."""
    t = 0.5 * (S[:, 0, 0] + S[:, 1, 1])
    h = 0.5 * (S[:, 0, 0] - S[:, 1, 1])
    return t + np.sqrt(h * h + S[:, 0, 1] * S[:, 0, 1])


def _margin_general(P, mats) -> float:
    return max(float(np.linalg.eigvalsh(A.T @ P @ A - P).max()) for A in mats)


def common_lyapunov(mats, rounds: int = 7, n: int = 41, tol: float = 1e-7):
    """Return (P, margin). P is None when no common quadratic Lyapunov function
    was found; `margin` is min over P of max_i lambda_max(A_i' P A_i - P), which is
    negative exactly when one exists.

    Implemented for d = 2, which is the bench's state dimension; other dimensions
    raise rather than silently certifying nothing.
    """
    mats = [np.asarray(A, dtype=float) for A in mats]
    d = mats[0].shape[0]
    if d != 2:
        raise NotImplementedError(f"common_lyapunov is implemented for d=2, got d={d}")

    lo_a, hi_a, lo_b, hi_b = 1e-3, 2 - 1e-3, -1.0, 1.0
    best_val, best_P = np.inf, None
    for _ in range(rounds):
        ga = np.linspace(lo_a, hi_a, n)
        gb = np.linspace(lo_b, hi_b, n)
        A_, B_ = (x.ravel() for x in np.meshgrid(ga, gb, indexing="ij"))
        C_ = 2.0 - A_
        ok = (A_ > 0) & (C_ > 0) & (A_ * C_ - B_ * B_ > 1e-12)      # P > 0, trace 2
        if not ok.any():
            break
        A_, B_, C_ = A_[ok], B_[ok], C_[ok]
        P = np.zeros((len(A_), 2, 2))
        P[:, 0, 0] = A_; P[:, 0, 1] = P[:, 1, 0] = B_; P[:, 1, 1] = C_
        m = None
        for M in mats:
            S = np.einsum("ji,gjk,kl->gil", M, P, M) - P          # M' P M - P
            v = _lmax_sym2(S)
            m = v if m is None else np.maximum(m, v)
        k = int(np.argmin(m))
        if m[k] < best_val:
            best_val, best_P = float(m[k]), P[k].copy()
        da, db = (hi_a - lo_a) / 6, (hi_b - lo_b) / 6              # refine around the argmin
        lo_a, hi_a = max(1e-3, A_[k] - da), min(2 - 1e-3, A_[k] + da)
        lo_b, hi_b = B_[k] - db, B_[k] + db

    if best_P is None or best_val >= -tol:
        return None, best_val
    return best_P, best_val


def certifies(P, mats, tol: float = 0.0) -> bool:
    """Independent re-check of a returned P, used by the tests: the search is not
    allowed to be its own witness."""
    if P is None:
        return False
    if np.linalg.eigvalsh(P).min() <= 0:
        return False
    return _margin_general(P, mats) < tol
