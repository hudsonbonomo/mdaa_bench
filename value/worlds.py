"""Value worlds -- nine generators for the value/norm bench (Paper 7).
Each returns a ValueWorld with structural asserts on what was planted.
Parameters from policy_frozen.json. Generators for C and X families
live in worlds_cx.py to respect the 200-line limit.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

from .world_utils import (
    load_policy, draw_signal, corrupt_unclear, make_obs,
    make_norm_proposed, make_norm_reviewed,
    make_protocol_consented, make_protocol_assigned,
    make_status_changed,
)

__all__ = [
    "WORLDS", "ValueWorld", "load_policy", "make_world",
    "make_N0", "make_P", "make_R", "make_Rplus",
]
WORLDS = ("N0", "P", "R", "R+", "C0", "C1", "C2", "X", "Xp")

_P = load_policy()
_U = float(_P["u_unclear"])
_STRATS = _P["protocol"]["strategies"]
_PROBS = [float(x) for x in _P["protocol"]["p"]]
_NORM = _P["norm"]


@dataclass(frozen=True)
class ValueWorld:
    observations: list[dict]
    norm_events: list[dict]
    protocol_events: list[dict]
    journey_events: list[dict]
    planted: dict
    params: dict


def _protocol_and_obs(T, seed, p_map, measure, strats, probs):
    """Protocol-assigned episodes with Bernoulli signals."""
    rng = np.random.default_rng(seed)
    proto_evts, obs = [], []
    for t in range(T):
        s = str(rng.choice(strats, p=probs))
        aid = f"a-{t}"
        proto_evts.append(make_protocol_assigned(
            "proto1", aid, s, probs[strats.index(s)], seq=t))
        obs.append(make_obs(t, draw_signal(rng, p_map[s]),
                            s, measure, assignment_id=aid))
    obs = corrupt_unclear(rng, obs, _U)
    return proto_evts, obs, rng


def _base_norm_events(reads, review="CONFIRMED"):
    evts = [make_norm_proposed("n1", reads,
            _NORM["minPerArm"], _NORM["margin"], seq=0)]
    if review:
        evts.append(make_norm_reviewed("n1", review, seq=0))
    return evts


def make_N0(T: int, seed: int) -> ValueWorld:
    """N0: norm only PROPOSED, never confirmed."""
    pp = _P["worlds"]["P"]
    p_ret = {s: pp["p_ret"][s] for s in _STRATS}
    proto_evts, obs, _ = _protocol_and_obs(
        T, seed, p_ret, "retention", _STRATS, _PROBS)
    norms = [make_norm_proposed("n1", "retention",
             _NORM["minPerArm"], _NORM["margin"], origin="HOST")]
    pc = [make_protocol_consented("proto1", _STRATS, _PROBS)]
    w = ValueWorld(obs, norms, pc + proto_evts, [],
                   {"world": "N0", "planted": "no_norm_confirmed"},
                   {"world": "N0", "T": T, "seed": seed})
    assert all(ne.get("review") != "CONFIRMED" for ne in w.norm_events
               if ne.get("type") == "mdaa.norm.reviewed"), \
        "N0: no norm may be confirmed"
    return w


def make_P(T: int, seed: int) -> ValueWorld:
    """P: practice != retention. s2 best by retention norm."""
    pp = _P["worlds"]["P"]
    p_ret = {s: pp["p_ret"][s] for s in _STRATS}
    p_prac = {s: pp["p_prac"][s] for s in _STRATS}
    proto_evts, obs_ret, rng = _protocol_and_obs(
        T, seed, p_ret, "retention", _STRATS, _PROBS)
    _, obs_prac, _ = _protocol_and_obs(
        T, seed + 1_000_000, p_prac, "practice", _STRATS, _PROBS)
    for i, o in enumerate(obs_prac):
        o["seq"] = T + i
        o["id"] = f"obs-{T + i}"
        o["assignmentId"] = proto_evts[i]["assignmentId"]
    norms = _base_norm_events("retention")
    pc = [make_protocol_consented("proto1", _STRATS, _PROBS)]
    w = ValueWorld(obs_ret + obs_prac, norms, pc + proto_evts, [],
                   {"world": "P", "planted": "s2_best_by_norm",
                    "p_ret": p_ret, "p_prac": p_prac},
                   {"world": "P", "T": T, "seed": seed})
    assert p_ret["s2"] > p_ret["s1"], "P: s2 must beat s1 in retention"
    assert p_prac["s1"] > p_prac["s2"], "P: s1 must beat s2 in practice"
    return w


def _R_core(T, seed, with_boost):
    """Shared for R and R+."""
    rp = _P["worlds"]["R"]
    p_ret, p_prac = float(rp["p_ret"]), float(rp["p_prac"])
    pa_s1, pa_s2 = float(rp["pause_after_s1"]), float(rp["pause_after_s2"])
    plen = int(rp["pause_len"])
    boost = float(rp["boost_after_pause"]) if with_boost else 0.0
    rng = np.random.default_rng(seed)
    proto_evts, obs, j_evts = [], [], []
    seq, last_paused = 0, False
    for t in range(T):
        s = str(rng.choice(_STRATS[:2], p=[0.5, 0.5]))
        aid = f"a-{t}"
        proto_evts.append(make_protocol_assigned(
            "proto1", aid, s, 0.5, seq=seq))
        obs.append(make_obs(seq, draw_signal(rng, p_ret), s, "retention", aid))
        p_p = min(1.0, p_prac + boost) if last_paused and with_boost else p_prac
        obs.append(make_obs(seq+1, draw_signal(rng, p_p), s, "practice", aid))
        seq += 2
        pa = pa_s1 if s == "s1" else pa_s2
        if rng.random() < pa:
            j_evts.append(make_status_changed(seq, "PAUSED"))
            seq += plen
            j_evts.append(make_status_changed(seq, "ACTIVE"))
            last_paused = True
        else:
            last_paused = False
    obs = corrupt_unclear(rng, obs, _U)
    return proto_evts, obs, j_evts, rng


def make_R(T: int, seed: int) -> ValueWorld:
    """R: pause, no boost. No difference by norm."""
    proto_evts, obs, j_evts, _ = _R_core(T, seed, False)
    norms = _base_norm_events("retention")
    pc = [make_protocol_consented("proto1", _STRATS[:2], [0.5, 0.5])]
    return ValueWorld(obs, norms, pc + proto_evts, j_evts,
                      {"world": "R", "planted": "no_diff_by_norm"},
                      {"world": "R", "T": T, "seed": seed})


def make_Rplus(T: int, seed: int) -> ValueWorld:
    """R+: pause with practice boost. No difference by norm."""
    proto_evts, obs, j_evts, _ = _R_core(T, seed, True)
    norms = _base_norm_events("retention")
    pc = [make_protocol_consented("proto1", _STRATS[:2], [0.5, 0.5])]
    return ValueWorld(obs, norms, pc + proto_evts, j_evts,
                      {"world": "R+", "planted": "no_diff_by_norm"},
                      {"world": "R+", "T": T, "seed": seed})


# --- Dispatch includes C/X from worlds_cx ---
from .worlds_cx import make_C0, make_C1, make_C2, make_X, make_Xp  # noqa: E402

_DISPATCH = {
    "N0": make_N0, "P": make_P, "R": make_R, "R+": make_Rplus,
    "C0": make_C0, "C1": make_C1, "C2": make_C2,
    "X": make_X, "Xp": make_Xp,
}


def make_world(name: str, T: int, seed: int) -> ValueWorld:
    assert name in WORLDS, f"unknown world {name!r}"
    return _DISPATCH[name](T=T, seed=seed)
