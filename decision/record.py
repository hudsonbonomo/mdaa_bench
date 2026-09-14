"""The vocabulary of the record: scope, evidence, authorization, and what a
decision model is allowed to see.

Split out of `worlds.py` for the house limit, but the seam is a real one: this
file says what a piece of evidence IS, and `worlds.py` says which ones a family
produces. Nothing here knows about families, and nothing here reads a latent.

SCOPE is (S, O, C, t): subject, object (the proposition), condition, time. The
condition is what carries the weight in this bench — apoiada / nao_apoiada,
performance with and without support — and the time component is carried and
checked by chi, but no family plants stale evidence, so it is never the binding
clause. Stated rather than implied.

PROVENANCE is whether the observation was made after a support was given
("post") or without one ("spont"). It is an attribute of the ITEM and has no
counterpart in the logged forcing u: the support is given by a person, not
through the pedagogical channel the dynamics bench drives, so no model can
recover it from u.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

from sim.observe import Observed

ACTIONS = ("ACT", "OBSERVE", "PROBE", "COMPARE", "WAIT")
CONDITIONS = ("apoiada", "nao_apoiada")
PROP = "p"                  # "S reaches the criterion on O"
OTHER_PROP = "q"            # a second proposition: an absent record is not an empty one
SUBJECT = "S1"
ACTION_CLASS = "ACT"        # the action class an authorized pause suspends


@dataclass(frozen=True)
class Scope:
    S: str
    O: str
    C: str
    t: int


@dataclass(frozen=True)
class Evidence:
    scope: Scope
    value: int          # +1 supports the proposition, -1 opposes it
    provenance: str     # "post" or "spont"


@dataclass(frozen=True)
class PauseRecord:
    """An authorization, not a sensor reading: it suspends an action CLASS for a
    subject over a span. It is handed to every model (see DecisionInput.pause);
    what separates the models is whether their policy has anywhere to put it."""
    subject: str
    action_class: str
    t0: int
    t1: int

    def covers(self, subject: str, action_class: str, t: int) -> bool:
        return (self.subject == subject and self.action_class == action_class
                and self.t0 <= t < self.t1)


@dataclass
class DecisionInput:
    """Everything a decision model may see. No field of this object is derived
    from World.truth; tests/test_decision_worlds.py asserts it."""
    obs: Observed
    evidence: dict          # t -> tuple[Evidence, ...]
    pauses: tuple           # tuple[PauseRecord, ...]
    pause: np.ndarray       # (T,) bool — the flag form of the records above
    window: int
    subject: str
    prop: str
    T: int


@dataclass
class World:
    inp: DecisionInput
    truth: dict
