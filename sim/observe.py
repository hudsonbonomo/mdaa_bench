"""Observation layer — y(t) = h(x(t)) + eps, sampled on a schedule.

Everything the identification pipeline receives comes from `observe()`.
This is also the seam where SIM-6 (LLM agents as observation surface) would
plug in: an agent renders y from the hidden x; it never produces dynamics.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .generators import Trajectory


@dataclass
class Observed:
    t: np.ndarray        # (n,) integer time indices actually observed
    y: np.ndarray        # (n, m) observations
    u: np.ndarray        # (n, 1) logged intervention at observed times
    pause: np.ndarray    # (n,) bool


def observe(traj: Trajectory, meas_noise: float = 0.2, keep_frac: float = 1.0,
            nonlinear_h: bool = False, seed: int = 0) -> Observed:
    """Apply the observation map and the sampling schedule.

    keep_frac < 1 drops observations at random (irregular sampling).
    nonlinear_h applies a monotone saturating map (tanh) before noise, the
    simplest way to break linear observability without destroying it.
    """
    rng = np.random.default_rng(seed + 10_000)
    T, d = traj.x.shape
    y = np.tanh(traj.x) if nonlinear_h else traj.x.copy()
    y = y + rng.normal(scale=meas_noise, size=y.shape)
    if keep_frac < 1.0:
        keep = rng.random(T) < keep_frac
        keep[0] = True
    else:
        keep = np.ones(T, dtype=bool)
    idx = np.flatnonzero(keep)
    return Observed(t=idx, y=y[idx], u=traj.u[idx], pause=traj.pause[idx])


def regular_pairs(obs: Observed):
    """Consecutive observation pairs (t, t+1) only — the one-step design
    matrix a Markov model is entitled to use. Irregular gaps are dropped, not
    interpolated: interpolation would invent dynamics."""
    dt = np.diff(obs.t)
    ok = np.flatnonzero(dt == 1)
    return obs.y[ok], obs.y[ok + 1], obs.u[ok]


def pair_times(obs: Observed):
    """Source time of each pair returned by `regular_pairs` — lets a gate put
    its train/test boundary on the original clock rather than on a row count."""
    return obs.t[np.flatnonzero(np.diff(obs.t) == 1)]
