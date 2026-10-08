"""Provenance verifier for adjustment derivations. PREREGISTRO rascunho v0.3 §6.

For plugin readers: mount named observations from the seq ranges in the
adjustment's returns, confirmed, inForce fields, call bridge in replay mode.
Reproduces if replay returns `to`. For R_mix: new instance, initial weights,
calculated step, checked against `to`. No result is fixed in code.
"""
from __future__ import annotations
import json
import math
import os
import subprocess
from copy import deepcopy
from pathlib import Path

import numpy as np

from .worlds import AdaptiveWorld, load_policy
from .readers import make_rule, reader_rule

__all__ = ["reproduces", "truncated", "without_one_return"]

_CLI = "adjustment-cli.js"
_P = load_policy()
_CANDIDATES = list(_P["mix"]["candidate_steps"])
_ETA = float(_P["mix"]["eta"])
_W_MAX = int(_P["rule"]["max_window"])
_STEP = int(_P["rule"]["step"])


def _dist_path() -> Path:
    dist = os.environ.get("MDAA_PLUGIN_DIST")
    if not dist:
        raise EnvironmentError("MDAA_PLUGIN_DIST not set")
    return Path(dist) / _CLI


def _call_replay(adjustment: dict, named: list[dict], rule: dict) -> dict:
    cli = _dist_path()
    payload = {"mode": "replay", "adjustment": adjustment,
               "named": named, "rule": rule}
    proc = subprocess.run(
        ["node", str(cli)], input=json.dumps(payload),
        capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(
            f"{_CLI} exited {proc.returncode}: {proc.stderr.strip()[:400]}")
    return json.loads(proc.stdout)


def _named_observations(world: AdaptiveWorld, adjustment: dict) -> list[dict]:
    """Collect c1 observations from the seq ranges the adjustment names."""
    _target = str(_P["stream"]["target"])
    ranges = []
    for span in adjustment.get("returns", []):
        ranges.append((span["fromSeq"], span["toSeq"]))
    conf = adjustment.get("confirmed")
    if conf:
        ranges.append((conf["fromSeq"], conf["toSeq"]))
    inf = adjustment.get("inForce")
    if inf:
        ranges.append((inf["fromSeq"], inf["toSeq"]))
    named, seen = [], set()
    for o in world.observations:
        seq = o["seq"]
        key = list(o["conditions"].keys())[0]
        if o["conditions"][key] != _target:
            continue
        for lo, hi in ranges:
            if lo <= seq <= hi and seq not in seen:
                named.append(o)
                seen.add(seq)
                break
    return named


def _round_half_up_10(x: float) -> int:
    return int(math.floor(x / 10 + 0.5)) * 10


def _reproduces_mix(world: AdaptiveWorld, adjustment: dict, k: int) -> bool:
    """For R_mix: new instance, initial weights, replay logic."""
    n = len(_CANDIDATES)
    weights = np.ones(n, dtype=float)
    named = _named_observations(world, adjustment)
    from_val = adjustment["from"]
    # 1. replay with step 10: if it returns `from`, doesn't reproduce
    rule10 = make_rule(k, step=int(_P["rule"]["step"]))
    r10 = _call_replay(adjustment, named, rule10)
    if r10.get("window") == from_val:
        return False
    # 2. for each candidate s, replay with step=s
    for ci, s in enumerate(_CANDIDATES):
        rule_s = make_rule(k, step=s)
        rs = _call_replay(adjustment, named, rule_s)
        if rs.get("window") != from_val:
            weights[ci] *= math.exp(_ETA * s / 10)
    total = weights.sum()
    if total > 0:
        weights /= total
    weighted_step = float(np.dot(weights, _CANDIDATES))
    effective_step = _round_half_up_10(weighted_step)
    effective_step = max(effective_step, 10)
    computed = min(from_val + effective_step, _W_MAX)
    return computed == adjustment["to"]


def reproduces(reader: str, world: AdaptiveWorld,
               adjustment: dict, k: int) -> bool:
    """Does replaying the derivation from only the named observations
    reproduce the adjustment's `to` value?"""
    if reader == "R_mix":
        return _reproduces_mix(world, adjustment, k)
    named = _named_observations(world, adjustment)
    rule = reader_rule(reader, k)
    result = _call_replay(adjustment, named, rule)
    return result.get("window") == adjustment.get("to")


def truncated(record: dict, rule: dict | None = None) -> bool:
    """Is this adjustment truncated by the ceiling?
    For R_mix: the record itself carries the truncated flag.
    For plugin readers: from + step > maxWindow."""
    if "truncated" in record:
        return bool(record["truncated"])
    step = rule["step"] if rule else _STEP
    w_max = rule["maxWindow"] if rule else _W_MAX
    return record["from"] + step > w_max


def without_one_return(adjustment: dict) -> dict:
    """Copy of the adjustment with the first return removed.
    Positive control for P3b: the verifier must fail."""
    adj = deepcopy(adjustment)
    returns = list(adj.get("returns", []))
    if len(returns) > 0:
        returns.pop(0)
    adj["returns"] = returns
    return adj
