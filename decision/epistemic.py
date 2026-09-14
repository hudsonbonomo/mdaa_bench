"""Lambda(t) — the propositional evidence layer: T / F / B / N per proposition,
per SCOPE, with the provenance of the support attached.

The four values are Belnap's, and the reason they are four is the whole claim
M1 makes against M0: a scalar summary of evidence cannot separate "nothing is
known" (N) from "as much evidence each way" (B). Both read as an uninformative
middle. Scope adds the second separation: two truthful observations made in
DIFFERENT conditions can disagree without either being wrong, and a layer that
drops C reads that as B and asks for a probe that cannot possibly resolve it.

Provenance is CARRIED here and not ACTED ON. M1 knows that a support was or was
not given before the observation; it has nowhere to put that fact, because
requiring it is a norm, not a reading. The requirement lives in chi, and chi is
consumed by Omega (`decision/warrant.py`). That is deliberate: it makes M2's
provenance advantage a claim about norms rather than about information, and
keeps M1 the strongest version of an evidence-only decider.
"""
from __future__ import annotations
from dataclasses import dataclass

LABELS = ("T", "F", "B", "N")
MERGED = "*"            # the pseudo-condition a scope-blind reading collapses to


@dataclass(frozen=True)
class Lambda:
    """The labelled evidential state of ONE proposition at ONE step.

    `by_cond` holds only the conditions actually witnessed: a condition with no
    item is not labelled N, it is absent, and the whole proposition is N exactly
    when `by_cond` is empty. Labelling unwitnessed conditions would invent a
    scope the record does not have."""
    prop: str
    t: int
    by_cond: dict       # C -> "T" | "F" | "B"
    prov: dict          # C -> frozenset({"post", "spont"})

    @property
    def conds(self):
        return tuple(sorted(self.by_cond))

    def empty(self) -> bool:
        return not self.by_cond

    def conflict(self) -> bool:
        """A conflict INSIDE one scope — the only kind a probe can settle."""
        return any(v == "B" for v in self.by_cond.values())

    def cross_scope(self) -> bool:
        """Decided and opposite in two different conditions. Not a conflict: a
        comparison of conditions, which is a different request."""
        decided = {v for v in self.by_cond.values() if v in ("T", "F")}
        return len(self.by_cond) > 1 and len(decided) > 1 and not self.conflict()

    def decided(self) -> bool:
        return not self.empty() and not self.conflict() and not self.cross_scope()

    def collapsed(self) -> str:
        """What a reader without C sees: the four-valued label after merging
        every condition into one. This is the information M0 does not have and
        the information a scope-blind M1 would throw away."""
        vals = set()
        for lab in self.by_cond.values():
            vals |= {"T", "F"} if lab == "B" else {lab}
        if not vals:
            return "N"
        return "B" if len(vals) > 1 else vals.pop()

    def has_post(self) -> bool:
        return any("post" in v for v in self.prov.values())


def lambda_of(items, prop: str, t: int, window: int) -> Lambda:
    """Label the admissible items about `prop`. An item is admissible if its
    scope names this proposition and its scope time is inside the window ending
    at t. Nothing else about the item is consulted here."""
    vals: dict = {}
    prov: dict = {}
    for e in items:
        if e.scope.O != prop or not (t - window < e.scope.t <= t):
            continue
        vals.setdefault(e.scope.C, set()).add(e.value)
        prov.setdefault(e.scope.C, set()).add(e.provenance)
    by_cond = {c: ("B" if len(v) > 1 else ("T" if 1 in v else "F")) for c, v in vals.items()}
    return Lambda(prop=prop, t=t, by_cond=by_cond,
                  prov={c: frozenset(v) for c, v in prov.items()})


def lambda_policy(lam: Lambda) -> str:
    """The action Lambda alone licenses — M1's policy, and the inner half of M2's.

    Provenance is visible in `lam` and not consulted: without chi there is no
    rule that makes it matter, and inventing one here would move Omega's work
    into M1 and hide the very comparison the bench exists to make."""
    if lam.empty():
        return "OBSERVE"
    if lam.conflict():
        return "PROBE"
    if lam.cross_scope():
        return "COMPARE"
    return "ACT"


def collapse(lam: Lambda, mode: str) -> Lambda:
    """Degrade Lambda by exactly one distinction. Used only by `blind_action`,
    to give each family a reference policy that is blind to the thing that
    family plants — which is how non-vacuity is asserted instead of hoped for."""
    if mode == "N->B":                  # absence read as balanced evidence
        if not lam.empty():
            return lam
        return Lambda(lam.prop, lam.t, {MERGED: "B"}, {})
    if mode == "B->N":                  # balanced evidence read as absence
        kept = {c: v for c, v in lam.by_cond.items() if v != "B"}
        return Lambda(lam.prop, lam.t, kept,
                      {c: v for c, v in lam.prov.items() if c in kept})
    if mode == "drop-scope":            # the condition dropped from every scope
        lab = lam.collapsed()
        if lab == "N":
            return Lambda(lam.prop, lam.t, {}, {})
        merged = frozenset().union(*lam.prov.values()) if lam.prov else frozenset()
        return Lambda(lam.prop, lam.t, {MERGED: lab}, {MERGED: merged})
    raise ValueError(mode)


#: For each family, the layer a distinction-blind policy drops. Three of the four
#: are operations on Lambda; W-pause drops Omega, which at this level simply means
#: deciding from Lambda alone — that is, being M1.
BLIND_MODE = {"W-absence": "N->B", "W-conflict": "B->N",
              "W-scope": "drop-scope", "W-pause": None}


def blind_action(family: str, lam: Lambda, pause_active: bool) -> str:
    """The reference collapse of a family. NOT a model: a measuring stick for
    the world. If this policy is not wrong on most of a family's steps, that
    family does not test what it claims to test."""
    mode = BLIND_MODE[family]
    return lambda_policy(lam if mode is None else collapse(lam, mode))
