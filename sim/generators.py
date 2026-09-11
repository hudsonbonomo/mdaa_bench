"""SIM-1 generators — known-world trajectories for the MDAA recovery study.

Each generator returns a Trajectory whose `truth` field records exactly what was
planted (node, regimes, switch times, memory order, intervention effects).
The pipeline never sees `truth`; only `recovery.py` compares against it.

Lattice nodes (Paper 2 §9):
  M1        linear Markov, process noise (baseline)
  M1+N      nonlinear drift (double-well / soft saturation)
  M1+H      hybrid: two linear regimes, Markov switching
  M1+M      memory: AR(p) with slowly decaying kernel (non-Markov in x)
All nodes share: hidden state x in R^d, logged intervention u(t) with a
known additive effect, optional authorized pause where u_ped = 0.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from .stability import common_lyapunov

NODES = ("M1", "M1+N", "M1+H", "M1+M")
H_MAX_REDRAWS = 50   # 24.8% of A2 draws lack a common P; 50 makes exhaustion impossible


@dataclass
class Trajectory:
    x: np.ndarray            # (T, d) hidden state
    u: np.ndarray            # (T, 1) logged intervention (pedagogical forcing)
    pause: np.ndarray        # (T,) bool, authorized pause (u_ped = 0 inside)
    truth: dict = field(default_factory=dict)


def _stable_matrix(rng: np.random.Generator, d: int, rho: float) -> np.ndarray:
    a = rng.normal(size=(d, d))
    a = a / max(abs(np.linalg.eigvals(a))) * rho
    return a


def _companion_rho(A_half, kernel, d: int) -> float:
    """Spectral radius of the AR(p) companion matrix — the boundedness condition
    of the M1+M node, and the only one of the four that is not readable off A."""
    p = len(kernel); n = p * d
    C = np.zeros((n, n)); C[d:, :-d] = np.eye(n - d)
    C[:d, :d] = A_half + kernel[0] * np.eye(d)
    for j in range(1, p):
        C[:d, j * d:(j + 1) * d] = kernel[j] * np.eye(d)
    return float(max(abs(np.linalg.eigvals(C))))


def _memory_mass(A_half, shape, d: int, target: float, hi: float = 0.95) -> float:
    """Total kernel mass whose companion radius equals `target`. Bisection: the
    radius is monotone in the mass, and a closed form would need the roots of the
    characteristic polynomial for every eigenvalue of A_half."""
    lo = 0.0
    if _companion_rho(A_half, shape * hi, d) <= target:
        return hi
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if _companion_rho(A_half, shape * mid, d) > target:
            hi = mid
        else:
            lo = mid
    return lo


def _intervention_schedule(rng, T: int, n_pulses: int, pause_frac: float):
    u = np.zeros((T, 1)); pause = np.zeros(T, dtype=bool)
    starts = rng.choice(np.arange(10, T - 10), size=n_pulses, replace=False)
    for s in starts:
        u[s:s + 5, 0] = rng.choice([-1.0, 1.0])
    if pause_frac > 0:
        p0 = int(T * 0.55); p1 = p0 + int(T * pause_frac)
        pause[p0:p1] = True; u[p0:p1] = 0.0
    return u, pause


def generate(node: str, T: int = 400, d: int = 2, seed: int = 0,
             process_noise: float = 0.15, rho: float = 0.9,
             n_pulses: int = 4, pause_frac: float = 0.1,
             noise_seed: int | None = None, A_override=None,
             offset=None) -> Trajectory:
    """Simulate one trajectory at the given lattice node.

    `noise_seed` splits the two random streams that `seed` otherwise shares:
    the STRUCTURE (A, B, the intervention schedule) keeps using `seed`, while
    the REALISATION (initial condition, process noise, regime chain) uses
    `noise_seed`. That is what makes within-person replicates possible — same
    person, same protocol, different day (ensemble.py). Left at None the single
    stream is used exactly as before, so every v0/v1 number is reproducible.

    `A_override` replaces the drawn A, for between-person ensembles where each
    trajectory gets its own A around a common mean. `offset` adds a constant to
    the drift, moving the fixed point to (I - A)^-1 offset: that is how people
    differ in WHERE they sit, not only in how they move. Both default to the
    original behaviour.
    """
    assert node in NODES, node
    assert T >= 20 + n_pulses, f"T={T} too short for {n_pulses} pulses in [10, T-10)"
    rng = np.random.default_rng(seed)
    A = _stable_matrix(rng, d, rho)
    B = rng.normal(scale=0.6, size=(d, 1))          # known intervention effect
    u, pause = _intervention_schedule(rng, T, n_pulses, pause_frac)
    if A_override is not None:
        A = np.asarray(A_override, dtype=float)
    if noise_seed is not None:
        rng = np.random.default_rng(noise_seed)     # realisation stream splits off here
    off = np.zeros(d) if offset is None else np.asarray(offset, dtype=float)
    x = np.zeros((T, d)); x[0] = rng.normal(size=d) + off
    truth = dict(node=node, A=A, B=B, rho=rho, process_noise=process_noise, offset=off)

    if node == "M1":
        # BOUNDEDNESS: rho(A) < 1. Guaranteed by _stable_matrix, which normalises to rho.
        for t in range(1, T):
            x[t] = A @ x[t - 1] + (B @ u[t - 1]) + off + rng.normal(scale=process_noise, size=d)

    elif node == "M1+N":
        alpha = 0.45
        # The drift is A x + alpha*(tanh(3 x0) - x0) on coordinate 0. Far from the
        # origin tanh saturates, so the map linearises to (A - alpha e0 e0') — NOT
        # to A. Drawing A stable therefore did NOT make the node stable: for ~18% of
        # seeds rho(A - alpha e0 e0') > 1 and the trajectory ran away to 1e78. The
        # bug was silent from v0 to v1. Fix: shift A so the FAR-FIELD matrix is the
        # stable draw; near the origin tanh still contributes +2*alpha*x0, which is
        # what opens the well. See ESTADO_CELULA.md.
        # BOUNDEDNESS: rho(A - alpha e0 e0') < 1, i.e. the FAR-FIELD matrix, not A.
        e0 = np.zeros((d, d)); e0[0, 0] = 1.0
        A = A + alpha * e0
        truth.update(A=A, A_far=A - alpha * e0,
                     nonlinearity=f"bounded double-well: +{alpha}*(tanh(3x)-x) on coordinate 0")
        for t in range(1, T):
            drift = A @ x[t - 1]
            drift[0] += alpha * (np.tanh(3.0 * x[t - 1, 0]) - x[t - 1, 0])   # bistable, bounded
            x[t] = drift + (B @ u[t - 1]) + off + rng.normal(scale=process_noise, size=d)

    elif node == "M1+H":
        # BOUNDEDNESS: exists P > 0 with A'PA - P < 0 and A2'PA2 - P < 0 (a COMMON
        # quadratic Lyapunov function), which certifies stability under arbitrary
        # switching. rho(A) < 1 and rho(A2) < 1 separately do NOT: two stable
        # matrices can be switched into divergence. A2 is redrawn until a common P
        # exists; 24.8% of draws are rejected (measured, 200 nodes) — see the README.
        for _n_redraw in range(H_MAX_REDRAWS):
            A2 = _stable_matrix(rng, d, rho * 0.6)
            A2 = -A2 if rng.random() < 0.5 else A2            # qualitatively different law
            P_common, lyap_margin = common_lyapunov((A, A2))  # sign-invariant: (-A2)'P(-A2) = A2'PA2
            if P_common is not None:
                break
        else:
            raise RuntimeError(f"no common Lyapunov P after {H_MAX_REDRAWS} redraws "
                               f"(seed={seed}, rho={rho})")
        truth.update(lyapunov_P=P_common, lyapunov_margin=lyap_margin, n_redraws=_n_redraw)
        p_stay = 0.985
        q = np.zeros(T, dtype=int)
        for t in range(1, T):
            q[t] = q[t - 1] if rng.random() < p_stay else 1 - q[t - 1]
            Aq = A if q[t] == 0 else A2
            x[t] = Aq @ x[t - 1] + (B @ u[t - 1]) + off + rng.normal(scale=process_noise, size=d)
        truth.update(A2=A2, regime=q, switches=np.flatnonzero(np.diff(q)) + 1, p_stay=p_stay)

    elif node == "M1+M":
        # BOUNDEDNESS: rho(companion of [0.5A + k1 I, k2 I, ..., kp I]) < 1.
        # The old fixed mass of 0.55 put z = 1 on the characteristic polynomial
        # exactly: at z = 1 it reads 1 = lambda + sum(kernel) = 0.45 + 0.55, so a
        # UNIT ROOT appeared whenever 0.5A had a real dominant eigenvalue 0.45 —
        # 60 of 200 seeds. Those trajectories were integrated random walks, not
        # the stationary decaying-kernel memory the node claims to be. The kernel
        # SHAPE (0.5^k) is kept and its MASS is solved for so the companion radius
        # lands on rho, the same target every other node is normalised to.
        p = 8
        shape = 0.5 ** np.arange(1, p + 1); shape = shape / shape.sum()
        kernel = shape * _memory_mass(A * 0.5, shape, d, rho)
        truth.update(memory_order=p, kernel=kernel,
                     companion_rho=_companion_rho(A * 0.5, kernel, d))
        for t in range(1, T):
            lag = sum(kernel[k - 1] * x[t - k] for k in range(1, min(p, t) + 1))
            x[t] = (A * 0.5) @ x[t - 1] + lag + (B @ u[t - 1]) + off + rng.normal(scale=process_noise, size=d)

    return Trajectory(x=x, u=u, pause=pause, truth=truth)
