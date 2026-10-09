"""Population worlds for the collective bench (Paper 8).
Pc (comparable), Pl (location differs), Pw (law differs).
Reuses _sched and _gen_obs from adaptive.worlds by import.
"""
from __future__ import annotations
import numpy as np

from adaptive.worlds import (
    _sched, _gen_obs, AdaptiveWorld, load_policy as load_adaptive_policy,
)
from adaptive.world_utils import c1_blocks
from .worlds import CollectiveWorld, load_policy

__all__ = ["make_Pc", "make_Pl", "make_Pw"]

_CP = load_policy()
_AP = load_adaptive_policy()
_L = int(_AP["stream"]["block_length"])
_KEY = str(_AP["stream"]["key"])
_TARGET = str(_AP["stream"]["target"])
_W0 = int(_AP["declared"]["warrant_window"])


def _make_adaptive_world(T, seed, p_fn) -> AdaptiveWorld:
    """Build an AdaptiveWorld using adaptive's helpers."""
    sc = _sched(T)
    obs, _ = _gen_obs(T, seed, sc, p_fn)
    return AdaptiveWorld(
        obs, [{"seq": 0, "window": _W0, "by": "person"}],
        [], {_KEY: _TARGET},
        {"world": "pop_member"}, {"T": T, "seed": seed})


def _better_rate_per_block(world: AdaptiveWorld) -> list[float]:
    """BETTER rate per c1 block."""
    blocks = c1_blocks(world)
    rates = []
    for start, end in blocks:
        better = total = 0
        for o in world.observations:
            if start <= o["seq"] <= end:
                cond = list(o["conditions"].values())[0]
                if cond == _TARGET:
                    if o["signal"] in ("BETTER", "WORSE"):
                        total += 1
                        if o["signal"] == "BETTER":
                            better += 1
        rates.append(better / total if total > 0 else 0.0)
    return rates


def _location_between_within(person_worlds: list[AdaptiveWorld]):
    """Variance ratio: between-person / within-person on BETTER rate."""
    person_rates = [_better_rate_per_block(pw) for pw in person_worlds]
    person_rates = [r for r in person_rates if len(r) > 1]
    if not person_rates:
        return float("inf")
    person_means = [np.mean(r) for r in person_rates]
    grand_mean = np.mean(person_means)
    between = np.mean([(m - grand_mean) ** 2 for m in person_means])
    within_vars = [np.var(r) for r in person_rates]
    within = np.mean(within_vars)
    if within < 1e-12:
        return float("inf") if between > 1e-12 else 0.0
    return float(between / within)


# ── Pc: comparable ───────────────────────────────────────────
def make_Pc(n: int, T: int, seed: int) -> CollectiveWorld:
    """Pc -- everyone like S world, p = 0.85."""
    p = _CP["Pop"]["Pc"]["p"]
    person_worlds = []
    for i in range(n):
        pw = _make_adaptive_world(T, seed + i * 1000, lambda t: p)
        person_worlds.append(pw)

    w = CollectiveWorld(
        [], [{"seq": 0, "window": _W0, "by": "person"}], [],
        {_KEY: _TARGET}, None, None, person_worlds,
        {"world": "Pc", "planted": "extending_is_correct",
         "all_same_p": True},
        {"world": "Pc", "n": n, "T": T, "seed": seed, "p": p})
    return w


# ── Pl: location differs ────────────────────────────────────
def make_Pl(n: int, T: int, seed: int) -> CollectiveWorld:
    """Pl -- S world with p drawn per person in p_range."""
    rng = np.random.default_rng(seed)
    p_lo, p_hi = _CP["Pop"]["Pl"]["p_range"]
    person_worlds = []
    person_ps = []
    for i in range(n):
        p_i = float(rng.uniform(p_lo, p_hi))
        person_ps.append(p_i)
        pw = _make_adaptive_world(T, seed + i * 1000, lambda t, _p=p_i: _p)
        person_worlds.append(pw)

    ratio = _location_between_within(person_worlds)
    w = CollectiveWorld(
        [], [{"seq": 0, "window": _W0, "by": "person"}], [],
        {_KEY: _TARGET}, None, None, person_worlds,
        {"world": "Pl", "planted": "location_varies",
         "person_ps": person_ps,
         "location_ratio": ratio},
        {"world": "Pl", "n": n, "T": T, "seed": seed})
    return w


# ── Pw: law differs ─────────────────────────────────────────
def make_Pw(n: int, T: int, seed: int) -> CollectiveWorld:
    """Pw -- half S (p0), half decaying linearly from p0 to p1_fast."""
    pw_cfg = _CP["Pop"]["Pw"]
    p0 = pw_cfg["p0"]
    p1_fast = pw_cfg["p1_fast"]
    fast_frac = pw_cfg["fast_fraction"]
    n_fast = max(1, int(n * fast_frac))
    n_stable = n - n_fast

    person_worlds = []
    labels: list[str] = []

    # Stable half
    for i in range(n_stable):
        pw = _make_adaptive_world(T, seed + i * 1000, lambda t: p0)
        person_worlds.append(pw)
        labels.append("stable")

    # Fast-decaying half
    for i in range(n_fast):
        def _p_decay(t, _T=T, _p0=p0, _p1=p1_fast):
            frac = min(t / max(_T - 1, 1), 1.0)
            return _p0 + (_p1 - _p0) * frac
        pw = _make_adaptive_world(
            T, seed + (n_stable + i) * 1000, _p_decay)
        person_worlds.append(pw)
        labels.append("fast_decay")

    ratio = _location_between_within(person_worlds)

    # Planted: extending is correct for stable, WRONG for fast_decay
    extend_correct = {
        "stable": True,
        "fast_decay": False,
    }

    w = CollectiveWorld(
        [], [{"seq": 0, "window": _W0, "by": "person"}], [],
        {_KEY: _TARGET}, None, None, person_worlds,
        {"world": "Pw", "planted": "law_differs",
         "labels": labels,
         "extend_correct": extend_correct,
         "location_ratio": ratio,
         "n_stable": n_stable, "n_fast": n_fast},
        {"world": "Pw", "n": n, "T": T, "seed": seed,
         "p0": p0, "p1_fast": p1_fast})
    return w
