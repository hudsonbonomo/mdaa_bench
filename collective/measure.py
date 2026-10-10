"""Measurement function for the collective grid (Paper 8).
measure_run(world_name, seed, **kw) -> flat dict of raw numbers.
Per-reader measurements for Q1-Q4 with optional plugin integration.
"""
from __future__ import annotations

from .worlds import make_world, CollectiveWorld, load_policy
from .controls import (R_count, R_pool, R_H1, R_mean, R_leastmisery)
from .gates import location_between_within, transfer_between_within

__all__ = ["measure_run"]
_P = load_policy()


def _dedup_obs(obs):
    seen, out = set(), []
    for o in obs:
        eid = o.get("episodeId", o["id"])
        if eid not in seen:
            seen.add(eid)
            out.append(o)
    return out


def _status_kind(result: dict) -> str | None:
    """Extract status kind (B/T/...) from episodes result."""
    st = result.get("status", {})
    bp = st.get("byProposition", [])
    if bp and isinstance(bp[0], dict):
        return bp[0].get("status", {}).get("kind")
    return None


def _measure_Q1(world: CollectiveWorld, use_plugin=False) -> dict:
    d: dict = {}
    obs = world.observations
    rc_dup = R_count(obs)
    d["Q1_statute_dup"] = rc_dup["statute"]
    d["Q1_total_obs_dup"] = rc_dup["total_obs"]
    d["Q1_n_episodes_dup"] = rc_dup["n_episodes"]
    dedup = _dedup_obs(obs)
    rc_dd = R_count(dedup)
    d["Q1_statute_dedup"] = rc_dd["statute"]
    d["Q1_total_obs_dedup"] = rc_dd["total_obs"]
    d["Q1_n_episodes_dedup"] = rc_dd["n_episodes"]
    inv = world.planted.get("inversion", {})
    if inv:
        inv_obs = [o for o in obs if "inv-" in o.get("episodeId", "")]
        s1o = [o for o in inv_obs if "inv-s1" in o["episodeId"]]
        s2o = [o for o in inv_obs if "inv-s2" in o["episodeId"]]
        d["Q1_inv_s1_obs"] = len(s1o)
        d["Q1_inv_s2_obs"] = len(s2o)
        s1e = len({o["episodeId"] for o in s1o})
        s2e = len({o["episodeId"] for o in s2o})
        d["Q1_inv_s1_episodes"] = s1e
        d["Q1_inv_s2_episodes"] = s2e
        d["Q1_inv_obs_winner"] = "s2" if len(s2o) > len(s1o) else "s1"
        d["Q1_inv_episode_winner"] = "s1" if s1e > s2e else "s2"
    if use_plugin:
        from .readers import read_own_episodes
        rf = read_own_episodes(world)
        rd_full = _status_kind(rf)
        d["Q1_R_own_full_kind"] = rd_full
        dw = CollectiveWorld(_dedup_obs(obs), world.declarations,
                             world.vocabulary_events, world.condition,
                             None, None, None, world.planted, world.params)
        rd = read_own_episodes(dw)
        rd_dedup = _status_kind(rd)
        d["Q1_R_own_dedup_kind"] = rd_dedup
        d["Q1_R_own_invariant"] = rd_full == rd_dedup
    return d


def _measure_Q2(world: CollectiveWorld, use_plugin=False) -> dict:
    d: dict = {}
    if use_plugin:
        from .readers import read_own_episodes
        result = read_own_episodes(world)
        d["Q2_R_own_elected"] = result.get("elected")
        d["Q2_suggestion_origin"] = result.get("suggestionOrigin")
    else:
        d["Q2_R_own_elected"] = None
        d["Q2_suggestion_origin"] = None
    return d


def _no_cross_adjust(folds):
    for f in folds:
        if isinstance(f, dict):
            if any(a.get("source") == "other"
                   for a in f.get("adjustments", [])):
                return False
    return True


def _measure_Q3(world: CollectiveWorld, use_plugin=False) -> dict:
    d: dict = {}
    if world.person_worlds is None:
        d["Q3_location_ratio"] = None
        d["Q3_transfer_ratio"] = None
        d["Q3_H1_passed"] = None
        return d
    loc_ratio = location_between_within(world.person_worlds)
    d["Q3_location_ratio"] = loc_ratio
    if use_plugin:
        from .readers import read_own_folds
        from adaptive.worlds import load_policy as load_ap
        from sim.density import H1_BETWEEN_WITHIN
        ap = load_ap()
        rule = {"threshold": 3, "step": int(ap["rule"]["step"]),
                "minWindow": int(ap["rule"]["min_window"]),
                "maxWindow": int(ap["rule"]["max_window"])}
        pf = [read_own_folds(pw) for pw in world.person_worlds]
        d["Q3_transfer_ratio"] = transfer_between_within(pf)
        gate = loc_ratio <= H1_BETWEEN_WITHIN
        d["Q3_H1_passed"] = gate
        d["Q3_H1_result"] = R_H1(world.person_worlds, pf, rule, loc_ratio)
        d["Q3_per_person_windows"] = [
            f[-1].get("window") if f else None for f in pf]
        d["Q3_R_own_no_cross_adjust"] = all(_no_cross_adjust(f) for f in pf)
    else:
        d["Q3_transfer_ratio"] = None
        d["Q3_H1_passed"] = None
    labels = world.planted.get("labels")
    if labels:
        d["Q3_labels"] = labels
        d["Q3_extend_correct"] = world.planted.get("extend_correct")
    return d


def _measure_Q4(world: CollectiveWorld, use_plugin=False) -> dict:
    d: dict = {}
    if world.group_input is None:
        return d
    gi = world.group_input
    planted_adm = world.planted.get("admissible", [])
    rm, rl = R_mean(gi), R_leastmisery(gi)
    d["Q4_R_mean_chosen"] = rm["chosen"]
    d["Q4_R_leastmisery_chosen"] = rl["chosen"]
    d["Q4_planted_admissible"] = planted_adm
    d["Q4_R_mean_in_all_gamma"] = rm["chosen"] in planted_adm
    d["Q4_R_leastmisery_in_all_gamma"] = rl["chosen"] in planted_adm
    d["Q4_n_hidden_reasons"] = sum(
        1 for m in gi["members"] if not m["showReasons"])
    d["Q4_admissible_empty"] = len(planted_adm) == 0
    d["Q4_status_quo"] = gi["statusQuo"]
    n, m = len(gi["members"]), len(gi["actions"])
    d["Q4_n_members"] = n
    d["Q4_m_actions"] = m
    p = world.params.get("p", 0.8)
    d["Q4_expected_empty_rate"] = 1.0 - (1.0 - p ** n) ** m
    if use_plugin:
        from .readers import read_group
        gr = read_group(gi)
        adm = gr.get("admissible", [])
        d["Q4_R_group_admissible"] = adm
        d["Q4_R_group_indeterminate"] = gr.get("indeterminate", False)
        d["Q4_R_group_status_quo_ok"] = gr.get(
            "statusQuo", {}).get("passes")
        blocks = gr.get("blocks", [])
        d["Q4_R_group_hidden_ok"] = all(
            b.get("reason") is None for b in blocks
            if not b.get("showReasons", True))
    else:
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
        d.update(_measure_Q1(w, use_plugin=use_plugin))
    elif world_name == "Pn":
        d.update(_measure_Q2(w, use_plugin=use_plugin))
        rp = R_pool(w.planted["population_obs"], w.planted["repertoire"])
        d["Q2_R_pool_elected"] = rp["elected"]
    elif world_name in ("Pc", "Pl", "Pw"):
        d.update(_measure_Q3(w, use_plugin=use_plugin))
    elif world_name == "G":
        d.update(_measure_Q4(w, use_plugin=use_plugin))
    d["world"] = world_name
    d["seed"] = seed
    d.update(kw)
    return d
