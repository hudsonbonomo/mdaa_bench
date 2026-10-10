"""Utility helpers for value worlds. Split for the 200-line limit.
Provides observation builders, signal drawing, protocol/norm event
factories, and the UNCLEAR corruption function.
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np

__all__ = [
    "load_policy", "draw_signal", "make_obs", "make_norm_proposed",
    "make_norm_reviewed", "make_norm_priority", "make_protocol_consented",
    "make_protocol_assigned", "make_status_changed", "corrupt_unclear",
    "POLICY_PATH",
]

POLICY_PATH = Path(__file__).resolve().parent / "policy_frozen.json"


def load_policy(path: Path | str = POLICY_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def draw_signal(rng: np.random.Generator, p_better: float) -> str:
    """Draw BETTER with probability p_better, else WORSE."""
    return str(rng.choice(["BETTER", "WORSE"],
               p=[p_better, max(1.0 - p_better, 0.0)]))


def corrupt_unclear(rng: np.random.Generator,
                    observations: list[dict],
                    u: float) -> list[dict]:
    """Replace a fraction u of signals with UNCLEAR."""
    out = []
    for o in observations:
        if rng.random() < u:
            o2 = dict(o)
            o2["signal"] = "UNCLEAR"
            out.append(o2)
        else:
            out.append(o)
    return out


def make_obs(seq: int, signal: str, strategy: str,
             measure: str, assignment_id: str | None = None,
             conditions: dict | None = None) -> dict:
    """Build one observation record matching the plugin schema."""
    o: dict = {
        "id": f"obs-{seq}", "seq": seq, "journeyId": "bench",
        "conditions": conditions or {"modo": "c1"},
        "strategy": [strategy], "signal": signal,
        "note": "", "measure": measure,
    }
    if assignment_id is not None:
        o["assignmentId"] = assignment_id
    return o


def make_norm_proposed(norm_id: str, reads: str,
                       min_per_arm: int, margin: float,
                       seq: int = 0,
                       origin: str = "DECLARED") -> dict:
    return {
        "type": "mdaa.norm.proposed", "seq": seq,
        "normId": norm_id, "version": 1,
        "reads": reads,
        "scope": {"modo": "c1"},
        "rule": {"minPerArm": min_per_arm, "margin": margin},
        "provenance": {"origin": origin, "recordedBy": "host"},
    }


def make_norm_reviewed(norm_id: str, review: str, seq: int = 1) -> dict:
    return {
        "type": "mdaa.norm.reviewed", "seq": seq,
        "normId": norm_id, "version": 1,
        "review": review,
    }


def make_norm_priority(higher: str, lower: str, seq: int) -> dict:
    return {
        "type": "mdaa.norm.priority", "seq": seq,
        "higher": higher, "lower": lower,
    }


def make_protocol_consented(protocol_id: str, strategies: list[str],
                            probabilities: list[float],
                            seq: int = 0) -> dict:
    return {
        "type": "mdaa.protocol.consented", "seq": seq,
        "protocolId": protocol_id,
        "strategies": strategies,
        "probabilities": probabilities,
    }


def make_protocol_assigned(protocol_id: str, assignment_id: str,
                           strategy: str, p: float,
                           seq: int = 0) -> dict:
    return {
        "type": "mdaa.protocol.assigned", "seq": seq,
        "protocolId": protocol_id,
        "assignmentId": assignment_id,
        "strategy": strategy, "p": p,
    }


def make_status_changed(seq: int, status: str) -> dict:
    """Journey status change event (PAUSED/ACTIVE)."""
    return {
        "type": "learning_journey.status_changed", "seq": seq,
        "status": status,
        "journeyId": "bench",
    }
