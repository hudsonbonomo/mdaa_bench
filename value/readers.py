"""Plugin reader R_norm for the value bench (Paper 7).
Calls value-cli.js via subprocess, same bridge pattern as adaptive/readers.py.
Modes: judge (pair comparison) and parecer (with/without layer7).
"""
from __future__ import annotations
from pathlib import Path
import json
import os
import subprocess

from .worlds import ValueWorld, load_policy

__all__ = ["read_judge", "read_parecer", "JUDGE_STATES"]


def _labels(s):
    """Normalise strategy to list of labels (plugin convention)."""
    return [s] if isinstance(s, str) else s


def _wrap_events(events: list[dict]) -> list[dict]:
    """Wrap flat bench events into {type, seq, payload} envelope
    expected by the plugin's readLedger.  Also normalises strategy
    fields to arrays (plugin calls strategyIdentity which needs
    .join)."""
    wrapped = []
    for e in events:
        env: dict = {"type": e["type"], "seq": e["seq"]}
        payload = {k: v for k, v in e.items()
                   if k not in ("type", "seq")}
        if "strategy" in payload:
            payload["strategy"] = _labels(payload["strategy"])
        if "strategies" in payload:
            payload["strategies"] = [_labels(s) for s in
                                     payload["strategies"]]
        env["payload"] = payload
        wrapped.append(env)
    return wrapped

JUDGE_STATES = (
    "SEM_NORMA", "INSUFICIENTE", "JUSTIFICADO",
    "NAO_JUSTIFICADO", "EM_CONFLITO",
)
_CLI = "value-cli.js"
_P = load_policy()
_GAMMA = _P["gamma"]


def _dist_path() -> Path:
    dist = os.environ.get("MDAA_PLUGIN_DIST")
    if not dist:
        raise EnvironmentError(
            "MDAA_PLUGIN_DIST not set: path to tmulab-mdaa/dist required")
    cli = Path(dist) / _CLI
    if not cli.exists():
        raise EnvironmentError(f"{cli} not found: build the plugin first")
    return cli


def _call_bridge(payload: dict, timeout: float = 120.0) -> dict:
    cli = _dist_path()
    proc = subprocess.run(
        ["node", str(cli)], input=json.dumps(payload),
        capture_output=True, text=True, encoding="utf-8",
        timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(
            f"{_CLI} exited {proc.returncode}: {proc.stderr.strip()[:400]}")
    return json.loads(proc.stdout)


def _gamma_input(pair: tuple[str, str]) -> dict:
    """Build gammaInput for a pair of strategies."""
    return {
        "pair": list(pair),
        "feasible": {s: _GAMMA[s]["feasible"] for s in pair},
        "safe": {s: _GAMMA[s]["safe"] for s in pair},
    }


def _judge_payload(world: ValueWorld,
                   pair: tuple[str, str]) -> dict:
    return {
        "mode": "judge",
        "observations": world.observations,
        "normEvents": _wrap_events(world.norm_events),
        "protocolEvents": _wrap_events(world.protocol_events),
        "gamma": _gamma_input(pair),
        "currentConditions": {"modo": "c1"},
    }


def read_judge(world: ValueWorld,
               pair: tuple[str, str] = ("s1", "s2")) -> dict:
    """Call R_norm in judge mode for the given pair."""
    return _call_bridge(_judge_payload(world, pair))


def _parecer_payload(world: ValueWorld, layer7: bool) -> dict:
    return {
        "mode": "parecer",
        "observations": world.observations,
        "normEvents": _wrap_events(world.norm_events),
        "protocolEvents": _wrap_events(world.protocol_events),
        "layer7": layer7,
        "currentConditions": {"modo": "c1"},
        "gamma": _gamma_input(("s1", "s2")),
        "nowSeq": len(world.observations),
        "vocabularyEvents": [],
        "policy": {"appearWindow": 1e9, "warrantWindow": 1e9,
                   "appearanceFloor": 1},
    }


def read_parecer(world: ValueWorld, layer7: bool = True) -> dict:
    """Call value-cli in parecer mode."""
    return _call_bridge(_parecer_payload(world, layer7))
