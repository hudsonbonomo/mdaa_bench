"""Omega(t) — warrant per action, under a chi that is declared and FROZEN.

Paper 4's own declared vulnerability (D8) is that the warrant rules are written
by the hand that runs the evaluation. The answer here is mechanical rather than
rhetorical: `warrants.yaml` is hashed into `warrants.sha256`, the hash is
verified on EVERY load, the same hash goes into the pre-registration, and a test
fails if any of the three disagree. A rule cannot be adjusted after seeing a
result without leaving a commit that says so.

The evaluator is deliberately small. It answers one question — is action `a`
warranted for subject S at t, given Lambda and the standing authorizations —
and, when it is not, returns the reason, because the reason is what chi maps to
a remedy. It reads chi generically: nothing in this module knows what "pause"
or "provenance" mean beyond looking them up.

Check order matches the world's declared precedence (`worlds.reference_action`):
support, then contra, then provenance, then the pause. The pause is last and
applies only to the action class it names, because an authorization suspends
intervening, not looking.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import pathlib

import yaml

ROOT = pathlib.Path(__file__).parent
CHI_PATH = ROOT / "warrants.yaml"
FREEZE_PATH = ROOT / "warrants.sha256"

REASONS = ("no_support", "conflict", "cross_scope", "provenance", "pause")


class FrozenChiViolation(RuntimeError):
    """chi changed between being declared and being used. This is the whole
    point of the file: the exception is the measurement."""


@dataclass(frozen=True)
class Verdict:
    ok: bool
    reason: str = ""


@dataclass(frozen=True)
class Chi:
    version: int
    frozen_on: str
    max_age: int
    actions: dict
    sha256: str
    path: str

    @property
    def window(self) -> int:
        """The admissibility window Lambda must use, in steps. chi sets it; the
        world has to agree, and a test says so."""
        return self.max_age + 1


def chi_hash(path=CHI_PATH) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def frozen_hash(path=FREEZE_PATH) -> str:
    return pathlib.Path(path).read_text(encoding="utf-8").split()[0].strip()


def freeze(chi_path=CHI_PATH, freeze_path=FREEZE_PATH) -> str:
    """Record the current hash. Run by hand, once, when chi is declared — never
    from the bench, so that a run can never re-freeze what it is about to use."""
    h = chi_hash(chi_path)
    pathlib.Path(freeze_path).write_text(h + "\n", encoding="utf-8")
    return h


def load_chi(path=CHI_PATH, verify: bool = True) -> Chi:
    path = pathlib.Path(path)
    h = chi_hash(path)
    if verify:
        want = frozen_hash()
        if h != want:
            raise FrozenChiViolation(
                f"chi at {path} hashes to {h[:12]}..., frozen as {want[:12]}...")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Chi(version=int(raw["version"]), frozen_on=str(raw["frozen_on"]),
               max_age=int(raw["max_age"]), actions=raw["actions"], sha256=h, path=str(path))


def warranted(chi: Chi, action: str, lam, pauses, subject: str, t: int) -> Verdict:
    """Is `action` warranted? The reason, when it is not, is what chi maps to a
    remedy — so a denial is never a dead end, it is a redirection."""
    rule = chi.actions[action]
    sup = rule.get("admissible_support") or {}
    contra = rule.get("inadmissible_contra") or {}
    if sup.get("requires_decided") and lam.empty():
        return Verdict(False, "no_support")
    if sup.get("requires_cross_scope") and not lam.cross_scope():
        return Verdict(False, "no_support")
    if contra.get("conflict") and lam.conflict():
        return Verdict(False, "conflict")
    if contra.get("cross_scope") and lam.cross_scope():
        return Verdict(False, "cross_scope")
    if (rule.get("provenance") or {}).get("required") == "post" and not lam.has_post():
        return Verdict(False, "provenance")
    cls = rule.get("blocked_by_pause_class")
    if cls and any(p.covers(subject, cls, t) for p in pauses):
        return Verdict(False, "pause")
    return Verdict(True)


def remedy(chi: Chi, action: str, reason: str) -> str:
    """What chi prescribes instead. A rule that denies without prescribing would
    make abstention free, and an abstainer that answers nothing scores well on
    every criterion that counts errors."""
    return (chi.actions[action].get("on_denied") or {}).get(reason, "WAIT")
