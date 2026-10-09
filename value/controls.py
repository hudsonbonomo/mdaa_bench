"""Python control readers for the value bench (Paper 7).
These do NOT call the plugin. Each abandons one rule from R_norm.

R_reward:      elects by highest BETTER rate in practice. Always judges.
R_infer_value: value = BETTER(practice) / seq consumed, pauses count.
R_scalar:      equal-weight sum of BETTER rates for retention + autonomy.
R_naive:       compares retention rates without checking assignmentId.
"""
from __future__ import annotations

from .worlds import ValueWorld, load_policy

__all__ = ["R_reward", "R_infer_value", "R_scalar", "R_naive"]

_P = load_policy()
_MARGIN = float(_P["norm"]["margin"])


def _count_signals(observations: list[dict], measure: str,
                   strategy: str, require_assignment: bool = False):
    """Count BETTER and total (BETTER+WORSE) for a strategy and measure."""
    better = total = 0
    for o in observations:
        if o.get("measure") != measure:
            continue
        if o["strategy"][0] != strategy:
            continue
        if require_assignment and o.get("assignmentId") is None:
            continue
        if o["signal"] in ("BETTER", "WORSE"):
            total += 1
            if o["signal"] == "BETTER":
                better += 1
    return better, total


def R_reward(world: ValueWorld,
             strategies: tuple[str, ...] = ("s1", "s2")) -> dict:
    """Elect by highest BETTER rate in practice. Always judges."""
    rates = {}
    for s in strategies:
        b, t = _count_signals(world.observations, "practice", s)
        rates[s] = b / t if t > 0 else 0.0
    best = max(rates, key=lambda s: rates[s])
    return {"elected": best, "rates": rates, "state": "JUDGED"}


def _seq_consumed(world: ValueWorld, strategy: str) -> int:
    """Total seq span consumed by episodes of this strategy,
    including pause gaps in the seq numbering."""
    seqs = [o["seq"] for o in world.observations
            if o["strategy"][0] == strategy]
    if not seqs:
        return 0
    return max(seqs) - min(seqs) + 1


def R_infer_value(world: ValueWorld,
                  strategies: tuple[str, ...] = ("s1", "s2")) -> dict:
    """Value = BETTER(practice) / seq consumed. Pauses inflate denominator."""
    values = {}
    for s in strategies:
        b, _ = _count_signals(world.observations, "practice", s)
        consumed = _seq_consumed(world, s)
        values[s] = b / consumed if consumed > 0 else 0.0
    best = max(values, key=lambda s: values[s])
    return {"elected": best, "values": values, "state": "JUDGED"}


def R_scalar(world: ValueWorld,
             strategies: tuple[str, ...] = ("s1", "s2")) -> dict:
    """Equal-weight sum of BETTER rates for retention + autonomy."""
    scores = {}
    for s in strategies:
        total_score = 0.0
        n_measures = 0
        for m in ("retention", "autonomy"):
            b, t = _count_signals(world.observations, m, s)
            if t > 0:
                total_score += b / t
                n_measures += 1
        scores[s] = total_score / n_measures if n_measures > 0 else 0.0
    best = max(scores, key=lambda s: scores[s])
    return {"elected": best, "scores": scores, "state": "JUDGED"}


def R_naive(world: ValueWorld,
            strategies: tuple[str, ...] = ("s1", "s2")) -> dict:
    """Compare retention rates without checking assignmentId.
    'Justifies' if difference >= margin."""
    rates = {}
    for s in strategies:
        b, t = _count_signals(world.observations, "retention", s,
                              require_assignment=False)
        rates[s] = b / t if t > 0 else 0.0
    sorted_s = sorted(rates, key=lambda s: rates[s], reverse=True)
    diff = rates[sorted_s[0]] - rates[sorted_s[1]] if len(sorted_s) > 1 else 0
    justified = diff >= _MARGIN
    return {
        "elected": sorted_s[0] if justified else None,
        "rates": rates,
        "diff": diff,
        "justified": justified,
        "state": "JUSTIFIED" if justified else "NOT_JUSTIFIED",
    }
