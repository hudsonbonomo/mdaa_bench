"""Measurement function for the collective grid (Paper 8).
measure_run(world_name, seed, **kw) -> flat dict of raw numbers.

Per-reader measurements for Q1-Q4:
Q1: statute, elected, suggestion, replica count (dup vs dedup), inversion.
Q2: whether R_own elected and suggestion origin.
Q3: window per person/subgroup, H1 gate, both ratios from gates.py.
Q4: admissibles, indeterminate, status quo, null reasons, R_mean/R_leastmisery.
"""
from __future__ import annotations

from .worlds import make_world, CollectiveWorld, load_policy
from .controls import (R_count, R_pool, R_H1, R_mean, R_leastmisery)
from .gates import location_between_within, transfer_between_within

__all__ = ["measure_run"]

_P = load_policy()


def _measure_Q1(world: CollectiveWorld) -> dict:
    """Q1: statute from duplicated vs deduplicated stream. Inversion."""
    d: dict = {}
    obs = world.observations
    # R_count on full (duplicated) stream
    rc_dup = R_count(obs)
    d["Q1_statute_dup"] = rc_dup["statute"]
    d["Q1_total_obs_dup"] = rc_dup["total_obs"]
    d["Q1_n_episodes_dup"] = rc_dup["n_episodes"]

    # Deduplicated: one obs per episodeId
    seen: set = set()
    dedup_obs = []
    for o in obs:
        eid = o.get("episodeId", o["id"])
        if eid not in seen:
            seen.add(eid)
            dedup_obs.append(o)
    rc_dedup = R_count(dedup_obs)
    d["Q1_statute_dedup"] = rc_dedup["statute"]
    d["Q1_total_obs_dedup"] = rc_dedup["total_obs"]
    d["Q1_n_episodes_dedup"] = rc_dedup["n_episodes"]

    # Inversion case: check if per-obs s2 would win but per-episode s1 wins
    inv = world.planted.get("inversion", {})
    if inv:
        inv_obs = [o for o in obs if "inv-" in o.get("episodeId", "")]
        inv_s1_obs = [o for o in inv_obs if "inv-s1" in o["episodeId"]]
        inv_s2_obs = [o for o in inv_obs if "inv-s2" in o["episodeId"]]
        d["Q1_inv_s1_obs"] = len(inv_s1_obs)
        d["Q1_inv_s2_obs"] = len(inv_s2_obs)
        inv_s1_eps = len({o["episodeId"] for o in inv_s1_obs})
        inv_s2_eps = len({o["episodeId"] for o in inv_s2_obs})
        d["Q1_inv_s1_episodes"] = inv_s1_eps
        d["Q1_inv_s2_episodes"] = inv_s2_eps
        d["Q1_inv_obs_winner"] = ("s2" if len(inv_s2_obs) > len(inv_s1_obs)
                                  else "s1")
        d["Q1_inv_episode_winner"] = ("s1" if inv_s1_eps > inv_s2_eps
                                      else "s2")
    return d


def _measure_Q2(world: CollectiveWorld) -> dict:
    """Q2: R_own elected (must be never) and suggestion origin."""
    d: dict = {}
    # Stub: plugin integration fills this
    d["Q2_R_own_elected"] = None
    d["Q2_suggestion_origin"] = None
    return d


def _measure_Q3(world: CollectiveWorld) -> dict:
    """Q3: windows per person/subgroup, H1 gate, both ratios."""
    d: dict = {}
    if world.person_worlds is None:
        d["Q3_location_ratio"] = None
        d["Q3_transfer_ratio"] = None
        d["Q3_H1_passed"] = None
        return d

    loc_ratio = location_between_within(world.person_worlds)
    d["Q3_location_ratio"] = loc_ratio
    # Transfer ratio: stub (needs plugin folds)
    d["Q3_transfer_ratio"] = None
    d["Q3_H1_passed"] = None

    labels = world.planted.get("labels")
    if labels:
        d["Q3_labels"] = labels
        d["Q3_extend_correct"] = world.planted.get("extend_correct")
    return d


def _measure_Q4(world: CollectiveWorld) -> dict:
    """Q4: group decision measurements."""
    d: dict = {}
    if world.group_input is None:
        return d

    gi = world.group_input
    planted_adm = world.planted.get("admissible", [])

    # R_mean and R_leastmisery
    rm = R_mean(gi)
    rl = R_leastmisery(gi)
    d["Q4_R_mean_chosen"] = rm["chosen"]
    d["Q4_R_leastmisery_chosen"] = rl["chosen"]
    d["Q4_planted_admissible"] = planted_adm

    # Check if R_mean/R_leastmisery choices are in all Gamma_i
    d["Q4_R_mean_in_all_gamma"] = rm["chosen"] in planted_adm
    d["Q4_R_leastmisery_in_all_gamma"] = rl["chosen"] in planted_adm

    # Null reason fields when showReasons is false
    n_hidden = sum(1 for m in gi["members"] if not m["showReasons"])
    d["Q4_n_hidden_reasons"] = n_hidden

    # Observed empty rate
    d["Q4_admissible_empty"] = len(planted_adm) == 0
    d["Q4_status_quo"] = gi["statusQuo"]
    d["Q4_n_members"] = len(gi["members"])
    d["Q4_m_actions"] = len(gi["actions"])

    # Expected empty rate: 1 - (1 - p^n)^m
    n = len(gi["members"])
    m = len(gi["actions"])
    p = world.params.get("p", 0.8)
    expected_empty = 1.0 - (1.0 - p ** n) ** m
    d["Q4_expected_empty_rate"] = expected_empty

    # Plugin stub fields
    d["Q4_R_group_admissible"] = None
    d["Q4_R_group_indeterminate"] = None
    d["Q4_R_group_status_quo_ok"] = None
    return d


def measure_run(world_name: str, seed: int,
                use_plugin: bool = False, **kw) -> dict:
    """Run all readers and measurements for one cell."""
    w = make_world(world_name, seed=seed, **kw)
    d: dict = {}

    if world_name == "O":
        d.update(_measure_Q1(w))
    elif world_name == "Pn":
        d.update(_measure_Q2(w))
        rp = R_pool(w.planted["population_obs"],
                     w.planted["repertoire"])
        d["Q2_R_pool_elected"] = rp["elected"]
    elif world_name in ("Pc", "Pl", "Pw"):
        d.update(_measure_Q3(w))
    elif world_name == "G":
        d.update(_measure_Q4(w))

    d["world"] = world_name
    d["seed"] = seed
    d.update(kw)
    return d
