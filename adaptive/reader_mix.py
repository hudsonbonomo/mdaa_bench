"""R_mix -- the learned-step reader. PREREGISTRO rascunho v0.3 §5 + Ordem §3.

State: V (starts at W0), weights on candidates (start equal), last_trigger_seq.
Reading uses the plugin in folds mode. Trigger: block's reading has non-empty
adjustments. On trigger: repeat reading at same nowSeq with step=s for each
candidate; fired candidates get factor exp(eta*s/10). Step = weighted mean of
candidates, rounded to nearest 10 with half UP. V <- min(V + step, W_max).
Parameters from policy_frozen.json.
"""
from __future__ import annotations
import json
import math
import os
import subprocess
from pathlib import Path

import numpy as np

from .worlds import AdaptiveWorld, load_policy
from .world_utils import c1_blocks, condition_at
from .readers import make_rule

__all__ = ["R_mix", "MixState"]

_CLI = "adjustment-cli.js"
_P = load_policy()
_CANDIDATES = list(_P["mix"]["candidate_steps"])
_ETA = float(_P["mix"]["eta"])
_W0 = int(_P["declared"]["warrant_window"])
_W_MAX = int(_P["rule"]["max_window"])


class MixState:
    """Mutable state for R_mix across trigger points."""
    def __init__(self):
        n = len(_CANDIDATES)
        self.weights = np.ones(n, dtype=float)
        self.window = _W0
        self.triggers: list[dict] = []
        self.last_trigger_seq = -1  # so first decl is at seq 0


def _dist_path() -> Path:
    dist = os.environ.get("MDAA_PLUGIN_DIST")
    if not dist:
        raise EnvironmentError("MDAA_PLUGIN_DIST not set")
    return Path(dist) / _CLI


def _call(payload: dict):
    cli = _dist_path()
    proc = subprocess.run(
        ["node", str(cli)], input=json.dumps(payload),
        capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(f"{_CLI} exited {proc.returncode}: "
                           f"{proc.stderr.strip()[:400]}")
    return json.loads(proc.stdout)


def _folds_payload(world: AdaptiveWorld, window: int, decl_seq: int,
                   k: int, step: int, at: list[dict]) -> dict:
    """Build folds request with ONE declaration at decl_seq."""
    rule = make_rule(k, step=step)
    return {
        "mode": "folds",
        "observations": world.observations,
        "declarations": [{"seq": decl_seq, "window": window, "by": "person"}],
        "vocabularyEvents": world.vocabulary_events,
        "rule": rule,
        "at": at,
    }


def _fold_single(world: AdaptiveWorld, window: int, decl_seq: int,
                 k: int, step: int, now_seq: int, cond: dict) -> dict:
    """Single fold for a candidate test at a trigger point."""
    rule = make_rule(k, step=step)
    return _call({
        "mode": "fold",
        "observations": world.observations,
        "declarations": [{"seq": decl_seq, "window": window,
                          "by": "person"}],
        "vocabularyEvents": world.vocabulary_events,
        "condition": cond,
        "rule": rule,
        "nowSeq": now_seq,
    })


def _round_half_up_10(x: float) -> int:
    """Round x to nearest 10 with half UP (not banker's rounding)."""
    return int(math.floor(x / 10 + 0.5)) * 10


def R_mix(world: AdaptiveWorld, k: int) -> dict:
    """Run R_mix over the full world. Returns final reading + state."""
    state = MixState()
    blocks = c1_blocks(world)
    if len(blocks) < 2:
        return {"state": "DECLARED", "window": _W0, "declaredWindow": _W0,
                "adjustments": [], "triggers": [], "reader": "R_mix"}

    remaining = list(range(1, len(blocks)))  # skip first block (not a return)

    while remaining:
        decl_seq = state.last_trigger_seq + 1 if state.last_trigger_seq >= 0 \
            else 0
        at = []
        for bi in remaining:
            _, last = blocks[bi]
            ns = last + 1
            at.append({"nowSeq": ns, "condition": condition_at(world, ns)})
        readings = _call(_folds_payload(world, state.window, decl_seq,
                                        k, int(_P["rule"]["step"]), at))
        trigger_idx = None
        for i, rdg in enumerate(readings):
            if rdg.get("adjustments"):
                trigger_idx = i
                break
        if trigger_idx is None:
            break
        bi = remaining[trigger_idx]
        _, last = blocks[bi]
        now_seq = last + 1
        cond = condition_at(world, now_seq)
        adj0 = readings[trigger_idx]["adjustments"][0]
        trigger_seq = adj0["seq"]
        state.last_trigger_seq = trigger_seq
        # test each candidate at the SAME nowSeq
        fired = {}
        for ci, s in enumerate(_CANDIDATES):
            trial = _fold_single(world, state.window, decl_seq,
                                 k, s, now_seq, cond)
            if trial.get("adjustments"):
                fired[ci] = s
                state.weights[ci] *= math.exp(_ETA * s / 10)
        total = state.weights.sum()
        if total > 0:
            state.weights /= total
        weighted_step = float(np.dot(state.weights, _CANDIDATES))
        effective_step = _round_half_up_10(weighted_step)
        effective_step = max(effective_step, 10)
        v_before = state.window
        new_window = min(v_before + effective_step, _W_MAX)
        truncated = v_before + effective_step > _W_MAX
        trigger_record = {
            "seq": trigger_seq, "from": v_before, "to": new_window,
            "returns": adj0.get("returns"),
            "confirmed": adj0.get("confirmed"),
            "inForce": adj0.get("inForce"),
            "step": effective_step, "truncated": truncated,
        }
        state.triggers.append(trigger_record)
        state.window = new_window
        remaining = [b for b in remaining if b > bi]

    return {"state": "ADJUSTED" if state.triggers else "DECLARED",
            "window": state.window, "declaredWindow": _W0,
            "adjustments": state.triggers, "triggers": state.triggers,
            "weights": state.weights.tolist(), "reader": "R_mix"}
