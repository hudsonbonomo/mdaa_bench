"""Three readers of the same flow. PREREGISTRO_v1 §4.

R_declared  the real MDAA fold with the standing layer — conditions as scope,
            vocabulary events read, alpha from alpha_frozen.json. No policy mock:
            it shells out to the plugin's CLI and fails loudly if it is absent.
R_decay     recency comparator — exponential kernel, floor 0.30, NO scope reading.
R_current   the plugin as of 2026-09-15 — exact string match on conditions,
            vocabulary events ignored.

Readers only: nothing here executes the grid, and nothing here sees `planted`.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import json
import math
import os
import subprocess

from .worlds import StandingWorld, load_alpha

__all__ = ["ReadingResult", "R_declared", "R_decay", "R_current",
           "DEFAULT_POLICY", "obs_id", "to_payload", "weight_vector"]

DEFAULT_POLICY = "lenient"
_CLI = "standing-cli.js"


@dataclass
class ReadingResult:
    verdicts: dict[str, str]            # observation_id -> standing/status
    strategy: str | None                # elected/winning strategy, or None
    summary: dict[str, int]             # counts by standing
    reader: str = ""
    status: dict | None = None          # byProposition + conflicts (R_declared only)
    raw: dict = field(default_factory=dict, repr=False)


def obs_id(t: int) -> str:
    """Stable record identity across the three readers."""
    return f"obs-{t}"


def _summarise(verdicts: dict[str, str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for v in verdicts.values():
        out[v] = out.get(v, 0) + 1
    return out


def _current_conditions(world: StandingWorld) -> dict[str, str]:
    """What is in force when the record is read: the last observation's conditions."""
    return dict(world.observations[-1].conditions) if world.observations else {}


def to_payload(world: StandingWorld, policy: str = DEFAULT_POLICY,
               current_conditions: dict[str, str] | None = None) -> dict:
    """The JSON the plugin CLI eats. Alpha comes from the frozen file, never inline."""
    alpha = load_alpha()
    assert policy in alpha["policies"], f"unknown policy {policy!r}"
    window = alpha["policies"][policy]
    return {
        "observations": [{"id": obs_id(o.t), "strategy": o.strategy,
                          "conditions": dict(o.conditions), "signal": o.signal,
                          "seq": o.t} for o in world.observations],
        "nowSeq": len(world.observations),
        "currentConditions": current_conditions if current_conditions is not None
        else _current_conditions(world),
        "vocabularyEvents": [dict(e) for e in world.vocabulary_events],
        # The CLI's policy contract is camelCase (dist/standing.js: standingOf).
        # alpha_frozen.json is snake_case and frozen; the translation lives here.
        "policy": {"name": policy,
                   "appearWindow": window["appear_window"],
                   "warrantWindow": window["warrant_window"],
                   "appearanceFloor": alpha["appearance_floor"]},
    }


# --------------------------------------------------------------------------- #
# R_declared — the real fold, over subprocess. No mock of policy, no fallback.  #
# --------------------------------------------------------------------------- #

def R_declared(world: StandingWorld, policy: str = DEFAULT_POLICY,
               current_conditions: dict[str, str] | None = None,
               timeout: float = 120.0) -> ReadingResult:
    dist = os.environ.get("MDAA_PLUGIN_DIST")
    if not dist:
        raise EnvironmentError(
            "MDAA_PLUGIN_DIST not set: path to schiusa/plugins/mdaa/dist required")
    cli = Path(dist) / _CLI
    if not cli.exists():
        raise EnvironmentError(f"{cli} not found: build the plugin before reading")
    payload = to_payload(world, policy, current_conditions)
    proc = subprocess.run(["node", str(cli)], input=json.dumps(payload),
                          capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"{_CLI} exited {proc.returncode}: {proc.stderr.strip()[:400]}")
    out = json.loads(proc.stdout)
    # The parecer is READ, never assumed: the elected strategy comes from the
    # plugin's own status cell. A dist that does not expose it is a stale build,
    # and saying so is better than resurrecting the hardcoded s_star.
    if "electedStrategy" not in out or "status" not in out:
        raise RuntimeError(
            f"{_CLI} answers without 'electedStrategy'/'status': stale dist, rebuild the plugin")
    verdicts = {v["id"]: v["standing"] for v in out.get("verdicts", [])}
    elected = out.get("electedStrategy") or None
    return ReadingResult(verdicts=verdicts,
                         strategy=">".join(elected) if elected else None,
                         summary=_summarise(verdicts) or dict(out.get("summary", {})),
                         reader="R_declared", status=out.get("status"), raw=out)


# --------------------------------------------------------------------------- #
# R_decay — recency only. Scope is not read; every record is weighted by age.   #
# --------------------------------------------------------------------------- #

def _decay_params() -> tuple[float, float, float]:
    """Explicit parameterization (alpha_frozen.json, emenda v1.1): weight is 1.0 up to
    `full_weight_until_rounds`, then exp(-(age - that) / `decay_constant_rounds`)."""
    cfg = load_alpha()["comparators"]["R_decay"]
    assert cfg["kernel"] == "exponential", f"unsupported kernel {cfg['kernel']!r}"
    decay_constant = float(cfg["decay_constant_rounds"])
    full_weight_until = float(cfg["full_weight_until_rounds"])
    assert decay_constant > 0, f"decay_constant_rounds must be positive, got {decay_constant}"
    return decay_constant, full_weight_until, float(cfg["floor"])


def weight_vector(tally: dict[str, dict[str, float]]) -> dict[str, float]:
    """WEIGHTED BETTER SHARE per strategy at the end of the R_decay tally — the
    vector emenda v1.2 measures P1 on. Each coordinate is that strategy's weighted
    BETTER over its own weighted mass, a share in [0, 1] that does not move with
    how much the strategy was observed."""
    out: dict[str, float] = {}
    for strategy, counts in tally.items():
        mass = sum(counts.values())
        out[strategy] = (counts["BETTER"] / mass) if mass else 0.0
    return out


def R_decay(world: StandingWorld, policy: str = DEFAULT_POLICY,
            current_conditions: dict[str, str] | None = None) -> ReadingResult:
    decay_constant, full_weight_until, floor = _decay_params()
    now = len(world.observations)
    verdicts, tally = {}, {}
    weighted_better = weighted_total = 0.0
    for o in world.observations:
        age = now - o.t
        if age <= full_weight_until:
            w = 1.0
        else:
            w = max(floor, math.exp(-(age - full_weight_until) / decay_constant))
        s = tally.setdefault(o.strategy, {"BETTER": 0.0, "WORSE": 0.0, "UNCLEAR": 0.0})
        s[o.signal] += w
        weighted_total += w
        if o.signal == "BETTER":
            weighted_better += w
        # recency is the only standing this reader knows: fresh or decayed to floor.
        verdicts[obs_id(o.t)] = "fresh" if w > floor else "decayed"
    best = None
    if tally:
        best = max(tally, key=lambda k: tally[k]["BETTER"] - tally[k]["WORSE"])
        if tally[best]["BETTER"] - tally[best]["WORSE"] <= 0:
            best = None
    summary = _summarise(verdicts)
    share = weighted_better / weighted_total if weighted_total else 0.0
    return ReadingResult(verdicts=verdicts, strategy=best, summary=summary,
                         reader="R_decay",
                         raw={"weighted_better_share": share,
                              "weight_vector": weight_vector(tally),
                              "decay_constant_rounds": decay_constant,
                              "full_weight_until_rounds": full_weight_until,
                              "floor": floor, "tally": tally})


# --------------------------------------------------------------------------- #
# R_current — exact string match on conditions, vocabulary events ignored.      #
# --------------------------------------------------------------------------- #

def R_current(world: StandingWorld, policy: str = DEFAULT_POLICY,
              current_conditions: dict[str, str] | None = None) -> ReadingResult:
    cfg = load_alpha()["comparators"]["R_current"]
    assert cfg["condition_match"] == "exact_string"
    assert cfg["vocabulary_events"] == "ignored"
    cur = current_conditions if current_conditions is not None else _current_conditions(world)
    verdicts, tally = {}, {}
    for o in world.observations:
        match = all(str(o.conditions.get(k)) == str(v) for k, v in cur.items()) \
            and set(o.conditions) == set(cur)
        verdicts[obs_id(o.t)] = "counted" if match else "excluded"
        if match:
            s = tally.setdefault(o.strategy, {"BETTER": 0, "WORSE": 0, "UNCLEAR": 0})
            s[o.signal] += 1
    best = None
    if tally:
        best = max(tally, key=lambda k: tally[k]["BETTER"] - tally[k]["WORSE"])
        if tally[best]["BETTER"] - tally[best]["WORSE"] <= 0:
            best = None
    return ReadingResult(verdicts=verdicts, strategy=best,
                         summary=_summarise(verdicts), reader="R_current",
                         raw={"tally": tally, "currentConditions": cur})
