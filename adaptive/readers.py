"""Five plugin readers for the adaptive bench. PREREGISTRO rascunho v0.3 §5.

Every reader shells out to the adjustment-cli.js bridge.
No policy mock: the plugin does all counting. Parameters from policy_frozen.json.

R_declared  -- rule with threshold k, step, minWindow, maxWindow
R_fixed     -- rule with zero-width range (minWindow=maxWindow=W0), reads returns
R_simple    -- rule with threshold 1 (abandons the replication gate)
R_sym       -- variant SYMMETRIC (also shortens on type-1 contradictions)
R_cross     -- variant CROSS_REGIME (ignores vocabulary regime requirement)
"""
from __future__ import annotations
from pathlib import Path
import json
import os
import subprocess

from .worlds import AdaptiveWorld, load_policy
from .world_utils import c1_blocks, condition_at

__all__ = ["read", "read_returns", "READERS", "make_rule", "reader_rule"]

READERS = ("R_declared", "R_fixed", "R_simple", "R_sym", "R_cross")
_CLI = "adjustment-cli.js"
_P = load_policy()
_W0 = int(_P["declared"]["warrant_window"])


def _dist_path() -> Path:
    dist = os.environ.get("MDAA_PLUGIN_DIST")
    if not dist:
        raise EnvironmentError(
            "MDAA_PLUGIN_DIST not set: path to tmulab-mdaa/dist required")
    cli = Path(dist) / _CLI
    if not cli.exists():
        raise EnvironmentError(f"{cli} not found: build the plugin first")
    return cli


def make_rule(k: int, step: int | None = None) -> dict:
    """Build an AdjustmentRule from policy_frozen.json and the given k."""
    return {"threshold": k,
            "step": step if step is not None else int(_P["rule"]["step"]),
            "minWindow": int(_P["rule"]["min_window"]),
            "maxWindow": int(_P["rule"]["max_window"])}


def make_rule_fixed(k: int, step: int | None = None) -> dict:
    """Rule with zero-width range: reads returns but never moves."""
    return {"threshold": k,
            "step": step if step is not None else int(_P["rule"]["step"]),
            "minWindow": _W0, "maxWindow": _W0}


def _call_bridge(payload: dict, timeout: float = 120.0):
    cli = _dist_path()
    proc = subprocess.run(
        ["node", str(cli)], input=json.dumps(payload),
        capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(
            f"{_CLI} exited {proc.returncode}: {proc.stderr.strip()[:400]}")
    return json.loads(proc.stdout)


def _fold_payload(world: AdaptiveWorld, rule: dict | None,
                  variant: str | None = None,
                  now_seq: int | None = None) -> dict:
    payload: dict = {
        "mode": "fold",
        "observations": world.observations,
        "declarations": world.declarations,
        "vocabularyEvents": world.vocabulary_events,
        "condition": world.condition,
        "rule": rule,
        "nowSeq": now_seq if now_seq is not None else len(world.observations),
    }
    if variant is not None:
        payload["variant"] = variant
    return payload


def reader_rule(reader: str, k: int) -> dict | None:
    if reader == "R_fixed":
        return make_rule_fixed(k)
    if reader == "R_simple":
        return make_rule(k=1)
    return make_rule(k)


def _reader_variant(reader: str) -> str | None:
    if reader == "R_sym":
        return "SYMMETRIC"
    if reader == "R_cross":
        return "CROSS_REGIME"
    return None


def read(reader: str, world: AdaptiveWorld, k: int,
         now_seq: int | None = None) -> dict:
    """Call the plugin bridge in fold mode for the named reader."""
    assert reader in READERS, f"unknown reader {reader!r}"
    rule = reader_rule(reader, k)
    variant = _reader_variant(reader)
    return _call_bridge(_fold_payload(world, rule, variant, now_seq))


def read_returns(reader: str, world: AdaptiveWorld, k: int) -> list[dict]:
    """ONE call in folds mode, one point per c1 block. Returns readings
    in block order. The plugin reads a return when the block closes:
    nowSeq = last_round + 1."""
    assert reader in READERS, f"unknown reader {reader!r}"
    blocks = c1_blocks(world)
    if not blocks:
        return []
    at = []
    for _, last in blocks:
        ns = last + 1
        at.append({"nowSeq": ns, "condition": condition_at(world, ns)})
    rule = reader_rule(reader, k)
    variant = _reader_variant(reader)
    payload: dict = {
        "mode": "folds",
        "observations": world.observations,
        "declarations": world.declarations,
        "vocabularyEvents": world.vocabulary_events,
        "rule": rule,
        "at": at,
    }
    if variant is not None:
        payload["variant"] = variant
    return _call_bridge(payload)
