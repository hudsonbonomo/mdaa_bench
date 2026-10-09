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
        capture_output=True, text=True, timeout=timeout)
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
        "normEvents": world.norm_events,
        "protocolEvents": world.protocol_events,
        "journeyEvents": world.journey_events,
        "gammaInput": _gamma_input(pair),
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
        "normEvents": world.norm_events,
        "protocolEvents": world.protocol_events,
        "journeyEvents": world.journey_events,
        "layer7": layer7,
        "currentConditions": {"modo": "c1"},
        "gammaInput": _gamma_input(("s1", "s2")),
    }


def read_parecer(world: ValueWorld, layer7: bool = True) -> dict:
    """Call value-cli in parecer mode."""
    return _call_bridge(_parecer_payload(world, layer7))
