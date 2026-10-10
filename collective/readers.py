"""Plugin readers for the collective bench (Paper 8).
R_own: collective-cli.js episodes / adjustment-cli.js folds per person.
R_group: collective-cli.js group mode.
Bridge pattern from adaptive/readers.py.
"""
from __future__ import annotations
from pathlib import Path
import json
import os
import subprocess

from adaptive.worlds import load_policy as load_adaptive_policy

__all__ = ["read_own_episodes", "read_own_folds", "read_group",
           "READERS_PLUGIN"]

READERS_PLUGIN = ("R_own", "R_group")
_CLI_COLLECTIVE = "collective-cli.js"
_CLI_ADJUSTMENT = "adjustment-cli.js"
_AP = load_adaptive_policy()


def _dist_path(cli_name: str) -> Path:
    dist = os.environ.get("MDAA_PLUGIN_DIST")
    if not dist:
        raise EnvironmentError(
            "MDAA_PLUGIN_DIST not set: path to tmulab-mdaa/dist required")
    cli = Path(dist) / cli_name
    if not cli.exists():
        raise EnvironmentError(f"{cli} not found: build the plugin first")
    return cli


def _call_bridge(cli_name: str, payload: dict,
                 timeout: float = 120.0) -> dict | list:
    cli = _dist_path(cli_name)
    proc = subprocess.run(
        ["node", str(cli)], input=json.dumps(payload),
        capture_output=True, text=True, encoding="utf-8",
        timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(
            f"{cli_name} exited {proc.returncode}: "
            f"{proc.stderr.strip()[:400]}")
    return json.loads(proc.stdout)


def read_own_episodes(world, offered_strategies=None) -> dict:
    """R_own for O and Pn: collective-cli.js mode episodes.
    EpisodesRequest extends StandingRequest; we send the standing
    fields so the plugin can compute status and election."""
    nowSeq = len(world.observations)
    payload: dict = {
        "mode": "episodes",
        "observations": world.observations,
        "nowSeq": nowSeq,
        "currentConditions": world.condition,
        "vocabularyEvents": world.vocabulary_events,
        "policy": {"appearWindow": 1e9, "warrantWindow": 1e9,
                   "appearanceFloor": 1},
    }
    if offered_strategies is not None:
        payload["offeredStrategies"] = offered_strategies
    return _call_bridge(_CLI_COLLECTIVE, payload)


def read_own_folds(person_world, rule=None) -> list:
    """R_own for Pop worlds: adjustment-cli.js folds per person."""
    from adaptive.readers import reader_rule, _fold_payload
    from adaptive.world_utils import c1_blocks, condition_at
    blocks = c1_blocks(person_world)
    if not blocks:
        return []
    at = []
    for _, last in blocks:
        ns = last + 1
        at.append({"nowSeq": ns,
                   "condition": condition_at(person_world, ns)})
    r = rule or {"threshold": 3,
                 "step": int(_AP["rule"]["step"]),
                 "minWindow": int(_AP["rule"]["min_window"]),
                 "maxWindow": int(_AP["rule"]["max_window"])}
    payload: dict = {
        "mode": "folds",
        "observations": person_world.observations,
        "declarations": person_world.declarations,
        "vocabularyEvents": person_world.vocabulary_events,
        "rule": r,
        "at": at,
    }
    return _call_bridge(_CLI_ADJUSTMENT, payload)


def read_group(group_input: dict) -> dict:
    """R_group: collective-cli.js mode group."""
    payload = {"mode": "group", **group_input}
    return _call_bridge(_CLI_COLLECTIVE, payload)
