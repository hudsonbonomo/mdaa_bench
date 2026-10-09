"""Python control readers for the collective bench (Paper 8).
These do NOT call the plugin. Each abandons one rule.

R_count:       counts reports by signal, majority wins, elects by obs count.
R_pool:        borrows evidence from population.
R_H1:          R_pool only when between/within location ratio <= H1.
R_mean:        chooses action with highest fraction of authorizing members.
R_leastmisery: chooses action with highest minimum across members.
"""
from __future__ import annotations
import numpy as np

from sim.density import H1_BETWEEN_WITHIN

__all__ = ["R_count", "R_pool", "R_pool_pop", "R_H1",
           "R_mean", "R_leastmisery"]


def R_count(observations: list[dict]) -> dict:
    """Count reports by signal. Majority signal wins. Elect by obs count."""
    by_episode: dict[str, dict] = {}
    for o in observations:
        sig = o["signal"]
        if sig not in ("BETTER", "WORSE"):
            continue
        # Count every observation, NOT deduplicated
        eid = o.get("episodeId", o["id"])
        if eid not in by_episode:
            by_episode[eid] = {"BETTER": 0, "WORSE": 0}
        by_episode[eid][sig] += 1

    better_count = sum(1 for e in by_episode.values()
                       if e["BETTER"] > e["WORSE"])
    worse_count = sum(1 for e in by_episode.values()
                      if e["WORSE"] > e["BETTER"])
    total_obs = sum(e["BETTER"] + e["WORSE"] for e in by_episode.values())

    if better_count > worse_count:
        statute = "T"
    elif worse_count > better_count:
        statute = "T_worse"
    else:
        statute = "B"

    return {"statute": statute,
            "better_count": better_count,
            "worse_count": worse_count,
            "total_obs": total_obs,
            "n_episodes": len(by_episode)}


def R_pool(population_obs: list[dict], strategies: list[str]) -> dict:
    """In Pn: elect by BETTER rate of population."""
    rates: dict[str, float] = {}
    for s in strategies:
        better = total = 0
        for o in population_obs:
            if o["strategy"][0] != s:
                continue
            if o["signal"] in ("BETTER", "WORSE"):
                total += 1
                if o["signal"] == "BETTER":
                    better += 1
        rates[s] = better / total if total > 0 else 0.0
    elected = max(rates, key=lambda s: rates[s]) if rates else None
    return {"elected": elected, "rates": rates,
            "source": "population"}


def R_pool_pop(person_folds: list[list[dict]], rule: dict) -> dict:
    """In Pop worlds: sum COUNTED returns across persons, apply rule.
    Each person_folds[i] is the folds result for person i.
    Returns a single window for the whole population.
    """
    if not person_folds or not any(person_folds):
        return {"window": None, "counted_returns": 0}

    total_counted = 0
    for folds in person_folds:
        if not folds:
            continue
        last = folds[-1] if isinstance(folds, list) else folds
        if isinstance(last, dict):
            total_counted += last.get("countedReturns", 0)

    k = rule.get("threshold", 3)
    step = rule.get("step", 10)
    min_w = rule.get("minWindow", 20)
    max_w = rule.get("maxWindow", 160)

    # Apply rule to aggregate count
    w = min_w
    if total_counted >= k:
        w = min(w + step, max_w)

    return {"window": w, "counted_returns": total_counted,
            "rule_applied": rule}


def R_H1(person_worlds, person_folds, rule, location_ratio):
    """R_pool only when location ratio <= H1_BETWEEN_WITHIN.
    Otherwise falls back to R_own (per-person folds, no pooling).
    """
    gate_passed = location_ratio <= H1_BETWEEN_WITHIN
    if gate_passed:
        result = R_pool_pop(person_folds, rule)
        result["gate_passed"] = True
        result["location_ratio"] = location_ratio
        return result
    else:
        return {"gate_passed": False,
                "location_ratio": location_ratio,
                "fallback": "R_own"}


def R_mean(group_input: dict) -> dict:
    """Choose action with highest fraction of authorizing members."""
    members = group_input["members"]
    actions = group_input["actions"]
    n = len(members)
    fracs: dict[str, float] = {}
    for a in actions:
        auth_count = 0
        for m in members:
            if not m.get("released"):
                continue
            g = m.get("gamma", {}).get(a, {})
            if (g.get("auth", False) and g.get("feas", True)
                    and g.get("safe", True) and g.get("epi", True)):
                auth_count += 1
        fracs[a] = auth_count / n if n > 0 else 0.0
    best = max(actions, key=lambda a: (fracs[a], a))
    return {"chosen": best, "fractions": fracs}


def R_leastmisery(group_input: dict) -> dict:
    """Choose action with highest minimum across members.
    Ties broken lexicographically.
    """
    members = group_input["members"]
    actions = group_input["actions"]
    mins: dict[str, float] = {}
    for a in actions:
        scores = []
        for m in members:
            if not m.get("released"):
                scores.append(0.0)
                continue
            g = m.get("gamma", {}).get(a, {})
            s = 1.0 if (g.get("auth", False) and g.get("feas", True)
                        and g.get("safe", True)
                        and g.get("epi", True)) else 0.0
            scores.append(s)
        mins[a] = min(scores) if scores else 0.0
    # Ties broken lexicographically
    best = max(actions, key=lambda a: (mins[a], a))
    return {"chosen": best, "minimums": mins}
