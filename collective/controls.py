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


def _collect_returns(person_folds: list[list[dict]]) -> list[dict]:
    """Collect all lastReturn entries from all persons' folds.
    Returns a list of {seq, kind} dicts, sorted by seq.
    Deduplicates by seq (same return seen in overlapping folds).
    """
    seen: set[int] = set()
    returns: list[dict] = []
    for folds in person_folds:
        if not folds:
            continue
        for f in folds:
            if not isinstance(f, dict):
                continue
            lr = f.get("lastReturn")
            if not isinstance(lr, dict) or lr.get("seq") is None:
                continue
            if lr["seq"] not in seen:
                seen.add(lr["seq"])
                returns.append({"seq": lr["seq"], "kind": lr["kind"]})
    returns.sort(key=lambda r: r["seq"])
    return returns


def apply_adjustment_rule(
        returns: list[dict], rule: dict, w0: int | None = None
) -> dict:
    """Apply the plugin's adjustment rule to a return stream.
    Reimplements adjustment.ts foldPolicy L132-145. See E1 spec."""
    k = rule.get("threshold", 3)
    step = rule.get("step", 10)
    min_w = rule.get("minWindow", 20)
    max_w = rule.get("maxWindow", 160)
    w = w0 if w0 is not None else min_w
    run = 0
    adj_count = 0
    for r in returns:
        kind = r["kind"]
        if kind == "COUNTED":
            # adjustment.ts L133: run += 1
            run += 1
        elif kind in ("CONFLICT", "CONTRADICTED"):
            # adjustment.ts L134-135: run = 0, counted = []
            run = 0
        # NEUTRAL: adjustment.ts does nothing (no branch)
        # adjustment.ts L138-143: threshold check
        if run >= k and w < max_w:
            w = min(w + step, max_w)
            run = 0
            adj_count += 1
    return {"window": w, "run": run, "adjustments": adj_count,
            "returns_stream": returns}


def R_pool_pop(person_folds: list[list[dict]], rule: dict,
               w0: int | None = None) -> dict:
    """Pop worlds: merge all persons' returns by seq, apply rule
    as if the population were one person. E1 spec."""
    if not person_folds or not any(person_folds):
        return {"window": None, "counted_returns": 0}
    returns = _collect_returns(person_folds)
    result = apply_adjustment_rule(returns, rule, w0)
    counted = sum(1 for r in returns if r["kind"] == "COUNTED")
    return {"window": result["window"],
            "counted_returns": counted,
            "run": result["run"],
            "adjustments": result["adjustments"],
            "rule_applied": rule}


def R_H1(person_worlds, person_folds, rule, location_ratio,
         w0: int | None = None):
    """R_pool only when location ratio <= H1_BETWEEN_WITHIN.
    Otherwise falls back to R_own (per-person folds, no pooling).
    """
    gate_passed = location_ratio <= H1_BETWEEN_WITHIN
    if gate_passed:
        result = R_pool_pop(person_folds, rule, w0)
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
