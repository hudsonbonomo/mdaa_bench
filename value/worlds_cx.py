"""C and X world families for the value bench. Split from worlds.py
for the 200-line limit.
"""
from __future__ import annotations
import numpy as np

from .world_utils import (
    load_policy, draw_signal, corrupt_unclear, make_obs,
    make_norm_proposed, make_norm_reviewed, make_norm_priority,
    make_protocol_consented, make_protocol_assigned,
)

_P = load_policy()
_U = float(_P["u_unclear"])
_STRATS = _P["protocol"]["strategies"]
_NORM = _P["norm"]


def _base_norm_events(reads, review="CONFIRMED"):
    evts = [make_norm_proposed("n1", reads,
            _NORM["minPerArm"], _NORM["margin"], seq=0)]
    if review:
        evts.append(make_norm_reviewed("n1", review, seq=0))
    return evts


def _C_core(T, seed, priority, include_autonomy_obs):
    from .worlds import ValueWorld
    cp = _P["worlds"]["C"]
    p_ret = {s: cp["p_ret"][s] for s in _STRATS[:2]}
    p_aut = {s: cp["p_aut"][s] for s in _STRATS[:2]}
    rng = np.random.default_rng(seed)
    strats_2, probs_2 = _STRATS[:2], [0.5, 0.5]
    proto_evts, obs, seq = [], [], 0
    for t in range(T):
        s = str(rng.choice(strats_2, p=probs_2))
        aid = f"a-{t}"
        proto_evts.append(make_protocol_assigned(
            "proto1", aid, s, 0.5, seq=seq))
        obs.append(make_obs(seq, draw_signal(rng, p_ret[s]),
                            s, "retention", aid))
        seq += 1
        if include_autonomy_obs:
            obs.append(make_obs(seq, draw_signal(rng, p_aut[s]),
                                s, "autonomy", aid))
            seq += 1
    obs = corrupt_unclear(rng, obs, _U)
    norms = _base_norm_events("retention")
    norms.append(make_norm_proposed("n2", "autonomy",
                 _NORM["minPerArm"], _NORM["margin"], seq=0))
    norms.append(make_norm_reviewed("n2", "CONFIRMED", seq=0))
    if priority:
        norms.append(make_norm_priority("n1", "n2", seq=0))
    pc = [make_protocol_consented("proto1", strats_2, probs_2)]
    return proto_evts, obs, norms, pc, rng


def make_C0(T: int, seed: int):
    """C0: two norms, no priority. Planted: conflict."""
    from .worlds import ValueWorld
    proto_evts, obs, norms, pc, _ = _C_core(T, seed, False, True)
    w = ValueWorld(obs, norms, pc + proto_evts, [],
                   {"world": "C0", "planted": "conflict"},
                   {"world": "C0", "T": T, "seed": seed})
    cp = _P["worlds"]["C"]
    assert cp["p_ret"]["s2"] > cp["p_ret"]["s1"], "C: s2 better retention"
    assert cp["p_aut"]["s1"] > cp["p_aut"]["s2"], "C: s1 better autonomy"
    return w


def make_C1(T: int, seed: int):
    """C1: two norms, priority retention > autonomy. Planted: s2."""
    from .worlds import ValueWorld
    proto_evts, obs, norms, pc, _ = _C_core(T, seed, True, True)
    return ValueWorld(obs, norms, pc + proto_evts, [],
                      {"world": "C1", "planted": "s2_by_priority"},
                      {"world": "C1", "T": T, "seed": seed})


def make_C2(T: int, seed: int):
    """C2: two norms, no autonomy observations. Planted: s2, autonomy silent."""
    from .worlds import ValueWorld
    proto_evts, obs, norms, pc, _ = _C_core(T, seed, False, False)
    w = ValueWorld(obs, norms, pc + proto_evts, [],
                   {"world": "C2", "planted": "s2_autonomy_silent"},
                   {"world": "C2", "T": T, "seed": seed})
    assert not any(o.get("measure") == "autonomy" for o in w.observations), \
        "C2: no autonomy observations"
    return w


def _X_core(T, seed, with_protocol):
    xp = _P["worlds"]["X"]
    p_stay = float(xp["p_stay"])
    p_s2_tired = float(xp["p_choose_s2_if_tired"])
    p_s1_fresh = float(xp["p_choose_s1_if_fresh"])
    p_ret_fresh = float(xp["p_ret_fresh"])
    p_ret_tired = float(xp["p_ret_tired"])
    rng = np.random.default_rng(seed)
    strats_2, probs_2 = _STRATS[:2], [0.5, 0.5]
    proto_evts, obs, choices = [], [], []
    state = "fresh"
    for t in range(T):
        if with_protocol:
            s = str(rng.choice(strats_2, p=probs_2))
            aid = f"a-{t}"
            proto_evts.append(make_protocol_assigned(
                "proto1", aid, s, 0.5, seq=t))
        else:
            if state == "tired":
                s = "s2" if rng.random() < p_s2_tired else "s1"
            else:
                s = "s1" if rng.random() < p_s1_fresh else "s2"
            aid = None
        choices.append((state, s))
        p_r = p_ret_fresh if state == "fresh" else p_ret_tired
        obs.append(make_obs(t, draw_signal(rng, p_r), s, "retention", aid))
        if state == "fresh":
            state = "tired" if rng.random() > p_stay else "fresh"
        else:
            state = "fresh" if rng.random() > p_stay else "tired"
    obs = corrupt_unclear(rng, obs, _U)
    norms = _base_norm_events("retention")
    pc = [make_protocol_consented("proto1", strats_2, probs_2)] \
        if with_protocol else []
    return proto_evts, obs, norms, pc, choices, rng


def make_X(T: int, seed: int):
    """X: confounded, no protocol. Planted: not justifiable."""
    from .worlds import ValueWorld
    proto_evts, obs, norms, pc, choices, _ = _X_core(T, seed, False)
    w = ValueWorld(obs, norms, pc + proto_evts, [],
                   {"world": "X", "planted": "not_justifiable",
                    "choices": choices},
                   {"world": "X", "T": T, "seed": seed})
    assert all(o.get("assignmentId") is None for o in w.observations), \
        "X: no assignmentId allowed"
    return w


def make_Xp(T: int, seed: int):
    """Xp: same hidden structure as X, with protocol. No difference."""
    from .worlds import ValueWorld
    proto_evts, obs, norms, pc, choices, _ = _X_core(T, seed, True)
    w = ValueWorld(obs, norms, pc + proto_evts, [],
                   {"world": "Xp", "planted": "no_difference",
                    "choices": choices},
                   {"world": "Xp", "T": T, "seed": seed})
    assert all(o.get("assignmentId") is not None for o in w.observations), \
        "Xp: all observations must have assignmentId"
    return w
