"""Gates for the collective bench (Paper 8).
Two variance ratios:
  1. Location between/within on BETTER rate per c1 block per person.
  2. Same ratio on transferred quantity (COUNTED return rate per person).
The second is measured only; no reader uses it.
"""
from __future__ import annotations
import numpy as np

from adaptive.worlds import AdaptiveWorld
from adaptive.world_utils import c1_blocks

__all__ = ["location_between_within", "transfer_between_within"]

_TARGET = "c1"


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


def _variance_ratio(per_person_series: list[list[float]]) -> float:
    """Between-person / within-person variance ratio."""
    valid = [s for s in per_person_series if len(s) > 1]
    if not valid:
        return float("inf")
    person_means = [np.mean(s) for s in valid]
    grand_mean = np.mean(person_means)
    between = float(np.mean([(m - grand_mean) ** 2 for m in person_means]))
    within = float(np.mean([np.var(s) for s in valid]))
    if within < 1e-12:
        return float("inf") if between > 1e-12 else 0.0
    return between / within


def location_between_within(
        person_worlds: list[AdaptiveWorld]) -> float:
    """Variance ratio on BETTER rate per c1 block, between persons."""
    series = [_better_rate_per_block(pw) for pw in person_worlds]
    return _variance_ratio(series)


def transfer_between_within(
        person_folds: list[list[dict]]) -> float:
    """Variance ratio on COUNTED return rate per person.
    Each person_folds[i] is a list of fold dicts with countedReturns.
    Measured only -- no reader uses this gate.
    """
    series = []
    for folds in person_folds:
        if not folds:
            continue
        rates = []
        for f in folds:
            if isinstance(f, dict):
                cr = f.get("countedReturns", 0)
                total = f.get("totalReturns", 1)
                rates.append(cr / total if total > 0 else 0.0)
        if rates:
            series.append(rates)
    return _variance_ratio(series)
