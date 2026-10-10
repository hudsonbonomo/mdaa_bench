"""Measurement function for the value grid (Paper 7).
measure_run(world_name, T, seed) -> flat dict of raw numbers, no thresholds.

Per-reader: R_norm state/elected, controls' choices,
P3 invariance (pause removal), P6 invariance (layer7), cost.
"""
from __future__ import annotations
import copy

from .worlds import make_world, ValueWorld, load_policy
from .controls import R_reward, R_infer_value, R_scalar, R_naive

__all__ = ["measure_run"]

_P = load_policy()
_CHK = int(_P["checkpoint_every"])


def _strip_pauses(world: ValueWorld) -> ValueWorld:
    """Remove journey status_changed events and renumber seq contiguously."""
    new_obs = []
    for i, o in enumerate(world.observations):
        o2 = dict(o)
        o2["seq"] = i
        o2["id"] = f"obs-{i}"
        new_obs.append(o2)
    new_proto = []
    for i, pe in enumerate(world.protocol_events):
        pe2 = dict(pe)
        if pe2.get("type") == "mdaa.protocol.assigned":
            pe2["seq"] = i
        new_proto.append(pe2)
    return ValueWorld(new_obs, world.norm_events, new_proto, [],
                      world.planted, world.params)


def _measure_gap_shift(world: ValueWorld) -> dict:
    """R_infer_value gap with vs without pauses. For R/R+ only."""
    iv_with = R_infer_value(world)
    gap_with = iv_with["values"].get("s2", 0) - iv_with["values"].get("s1", 0)
    stripped = _strip_pauses(world)
    iv_without = R_infer_value(stripped)
    gap_wo = iv_without["values"].get("s2", 0) - iv_without["values"].get("s1", 0)
    return {"gap_with_pauses": gap_with, "gap_without_pauses": gap_wo,
            "gap_shift": abs(gap_with - gap_wo)}


def _measure_controls(world: ValueWorld) -> dict:
    """Run all four Python controls on the world."""
    d: dict = {}
    rw = R_reward(world)
    d["R_reward_elected"] = rw["elected"]
    iv = R_infer_value(world)
    d["R_infer_value_elected"] = iv["elected"]
    sc = R_scalar(world)
    d["R_scalar_elected"] = sc["elected"]
    nv = R_naive(world)
    d["R_naive_elected"] = nv["elected"]
    d["R_naive_justified"] = nv["justified"]
    d["R_naive_diff"] = nv["diff"]
    return d


def _measure_norm_stub(world: ValueWorld, world_name: str) -> dict:
    """Stub for R_norm measurements. Filled by integration when plugin is
    available. Returns empty-state markers so decide.py can detect absence."""
    d: dict = {}
    d["R_norm_state"] = None
    d["R_norm_judged_strategy"] = None
    d["R_norm_elected"] = None
    d["R_norm_s2s3_state"] = None
    d["R_norm_s2s3_elected"] = None
    d["P3_invariant"] = None
    d["P6_layer7_true"] = None
    d["P6_layer7_false"] = None
    d["P6_s3_never_elected"] = None
    d["cost_checkpoint"] = None
    return d


def _judged_from_perNorm(jdg: dict) -> str | None:
    """Derive the best strategy from perNorm when elected is absent.
    Returns the strategy with the higher BETTER rate among JUSTIFICADO
    norms, or None if the judgment is not JUSTIFICADO."""
    if jdg.get("state") != "JUSTIFICADO":
        return None
    for nr in jdg.get("perNorm", []):
        if nr.get("verdict") != "JUSTIFICADO":
            continue
        arms = nr.get("arms", {})
        best_s, best_rate = None, -1.0
        for s, arm in arms.items():
            eps = arm.get("episodes", 0)
            rate = arm["better"] / eps if eps > 0 else 0.0
            if rate > best_rate:
                best_rate = rate
                best_s = s
        if best_s is not None:
            return best_s
    return None


def _measure_norm_integration(world: ValueWorld,
                              world_name: str) -> dict:
    """Full R_norm measurements via plugin bridge."""
    from .readers import read_judge, read_parecer
    d: dict = {}
    jdg = read_judge(world, ("s1", "s2"))
    d["R_norm_state"] = jdg.get("state")
    d["R_norm_judged_strategy"] = _judged_from_perNorm(jdg)
    el = jdg.get("elected")
    d["R_norm_elected"] = el[0] if isinstance(el, list) and el else el
    if world_name == "P":
        jdg23 = read_judge(world, ("s2", "s3"))
        d["R_norm_s2s3_state"] = jdg23.get("state")
        el23 = jdg23.get("elected")
        d["R_norm_s2s3_elected"] = (el23[0] if isinstance(el23, list)
                                    and el23 else el23)
    else:
        d["R_norm_s2s3_state"] = None
        d["R_norm_s2s3_elected"] = None
    if world_name in ("R", "R+"):
        stripped = _strip_pauses(world)
        jdg_stripped = read_judge(stripped, ("s1", "s2"))
        d["P3_invariant"] = (jdg["state"] == jdg_stripped["state"]
                             and jdg.get("elected") == jdg_stripped.get("elected"))
    else:
        d["P3_invariant"] = None
    par_on = read_parecer(world, layer7=True)
    par_off = read_parecer(world, layer7=False)
    d["P6_layer7_true"] = par_on
    d["P6_layer7_false"] = par_off
    jdg_s3 = read_judge(world, ("s1", "s3"))
    d["P6_s3_never_elected"] = jdg_s3.get("elected") != "s3"
    # Cost only for P (reaches JUSTIFICADO); Xp gets None by design
    if world_name == "P":
        d["cost_checkpoint"] = _cost_checkpoint(world, world_name)
    else:
        d["cost_checkpoint"] = None
    return d


def _cost_checkpoint(world: ValueWorld, world_name: str) -> int | None:
    """First checkpoint (every checkpoint_every episodes) at which
    R_norm returns JUSTIFICADO. None if never."""
    from .readers import read_judge
    obs = world.observations
    n_obs = len(obs)
    for cp in range(_CHK, n_obs + 1, _CHK):
        sub_obs = obs[:cp]
        sub_world = ValueWorld(
            sub_obs, world.norm_events, world.protocol_events,
            world.journey_events, world.planted, world.params)
        jdg = read_judge(sub_world, ("s1", "s2"))
        if jdg.get("state") == "JUSTIFICADO":
            return cp
    return None


def measure_run(world_name: str, T: int, seed: int,
                use_plugin: bool = False,
                world_override: 'ValueWorld | None' = None) -> dict:
    """Run all readers and measurements for one (world, T, seed) cell.
    Pass world_override to use a pre-built world (e.g. alternative params).
    """
    w = world_override or make_world(world_name, T=T, seed=seed)
    d: dict = {}
    d.update(_measure_controls(w))
    if world_name in ("R", "R+"):
        d.update(_measure_gap_shift(w))
    if use_plugin:
        d.update(_measure_norm_integration(w, world_name))
    else:
        d.update(_measure_norm_stub(w, world_name))
    d["world"] = world_name
    d["T"] = T
    d["seed"] = seed
    return d
