"""SIM-7 decision worlds — synthetic worlds in which the CORRECT ACTION is known.

The first bench (`sim/`) plants DYNAMICS and asks whether the pipeline recovers
it. This one plants POLICY: at every eligible step there is an action that is
correct by construction, recorded in `truth` and never handed to a decision
module. Paper 4 declares three adversarial models with an explicit failure
condition; these worlds are what can falsify them.

Four families, one distinction each:

  W-absence   no admissible evidence about p              -> OBSERVE
  W-conflict  two items, SAME scope, opposite values      -> PROBE (discriminate)
  W-scope     two items, DIFFERENT conditions, opposite,  -> COMPARE the conditions,
              each one true in its own condition             never infer a deficit
  W-pause     the evidence decides and an authorized      -> WAIT
              pause is in force: lambda(P_next) = T is
              not sufficient

Every family also carries BASELINE steps where the evidence is sufficient,
concordant and collected after a support was given: there the correct action is
ACT. Without them a constant policy would score a family perfectly and the
family would measure nothing. SIGNATURE_FRAC of the steps are signature steps,
which is also the non-vacuity floor: a policy that collapses the distinction a
family turns on is wrong on exactly those steps (tests/test_decision_worlds.py,
`epistemic.blind_action`).

The vocabulary of the record — scope, evidence, authorization, and what a model
is allowed to see — is in `decision/record.py` and re-exported below.

The latent substrate is the M1 node of `sim/generators.py` and the observation
channel is `sim/observe.py`. The decision bench inherits the dynamics, the
measurement noise and the sampling schedule instead of inventing a second set.
"""
from __future__ import annotations
import numpy as np

from sim.generators import generate
from sim.observe import observe
from .record import (ACTION_CLASS, ACTIONS, CONDITIONS, OTHER_PROP, PROP, SUBJECT,
                     DecisionInput, Evidence, PauseRecord, Scope, World)

# Re-exported: a reader of a family should not have to know which file holds the
# vocabulary it emits. `record.py` defines them, this module is where they are used.
__all__ = ["FAMILIES", "ACTIONS", "CONDITIONS", "PROP", "OTHER_PROP", "SUBJECT",
           "ACTION_CLASS", "WINDOW", "GAP", "SIGNATURE_FRAC", "SPONT_FRAC", "FLIP_P",
           "NON_VACUITY_FLOOR", "Scope", "Evidence", "PauseRecord", "DecisionInput",
           "World", "make_world", "reference_action"]

FAMILIES = ("W-absence", "W-conflict", "W-scope", "W-pause")
WINDOW = 1                  # admissible age of evidence, in steps
GAP = 1.3                   # condition offset in state sd; sets the scope-disagreement rate
SIGNATURE_FRAC = 0.70       # target share of signature steps
SPONT_FRAC = 0.25           # share of steps whose support was spontaneous
FLIP_P = 0.05               # evidence noise: an item reports the wrong side of criterion
NON_VACUITY_FLOOR = 0.60    # item 1: a distinction-blind policy must fail at least this often


def reference_action(items, crit_differs: bool, pause_active: bool, prop: str = PROP) -> str:
    """The ground truth of the world: the correct action at one step.

    PRECEDENCE, declared: absence; then a conflict inside one scope; then a REAL
    condition difference; then the provenance of the support; then act. An
    authorized pause is applied LAST and only to ACT, because a pause suspends
    intervening, not looking — suspending the whole repertoire would make WAIT
    the answer to questions the pause says nothing about, and chi would then
    describe a rule the world does not have.

    Only the COMPARE branch reads the latent (`crit_differs`). That is what
    keeps M2 from being this function: a cross-condition disagreement in the
    RECORD may be evidence noise rather than a real condition difference, and a
    model that sees only the record cannot tell. Everything else is a property
    of the record, so the ceiling is reachable in principle — which is the point,
    because a ceiling nobody can reach measures the noise, not the layers.
    """
    about = [e for e in items if e.scope.O == prop]
    if not about:
        return "OBSERVE"
    by_cond: dict = {}
    for e in about:
        by_cond.setdefault(e.scope.C, set()).add(e.value)
    if any(len(v) > 1 for v in by_cond.values()):
        return "PROBE"
    if crit_differs and len(by_cond) > 1:
        return "COMPARE"
    if not any(e.provenance == "post" for e in about):
        return "PROBE"
    return "WAIT" if pause_active else "ACT"


def _readings(x: np.ndarray, gap: float) -> dict:
    """Condition-relative readings of the same latent capacity. With support the
    subject sits `gap` sds above where the unsupported reading puts them, so a
    truthful observation in each condition disagrees whenever |x0| < gap*sd —
    the scope structure W-scope plants is earned from the latent, not stamped."""
    s = float(np.std(x[:, 0])) + 1e-12
    return {"apoiada": x[:, 0] + gap * s, "nao_apoiada": x[:, 0] - gap * s}


def _zero_runs(u: np.ndarray):
    """Maximal spans with no logged forcing, as (start, end_exclusive) pairs."""
    z = np.abs(u[:, 0]) < 1e-12
    edges = np.flatnonzero(np.diff(np.r_[False, z, False].astype(int)))
    return list(zip(edges[::2], edges[1::2]))


def _pause_windows(u, steps, target):
    """Authorized pauses placed on spans where no forcing was logged, so the
    generator's invariant (u_ped = 0 inside an authorized pause) holds without
    touching the trajectory. Largest spans first, until the pause covers
    `target` of the steps: W-pause needs the pause to be the majority case, not
    a 10% corner, or the family cannot clear the non-vacuity floor."""
    covered = np.zeros(len(u), bool)
    out = []
    for s0, s1 in sorted(_zero_runs(u), key=lambda r: r[1] - r[0], reverse=True):
        out.append(PauseRecord(SUBJECT, ACTION_CLASS, int(s0), int(s1)))
        covered[s0:s1] = True
        if covered[steps].mean() >= target:
            break
    return tuple(out), covered


def _signature_steps(family, steps, z, crit, u, rng, frac):
    if family == "W-scope":                      # the latent decides; measured, not set
        return steps[crit["apoiada"][steps] != crit["nao_apoiada"][steps]], ()
    if family == "W-pause":
        pauses, covered = _pause_windows(u, steps, frac)
        return steps[covered[steps]], pauses
    k = int(round(frac * len(steps)))
    if family == "W-conflict":                   # contest the least separated readings
        order = np.argsort(np.abs(z["nao_apoiada"][steps]))
        return np.sort(steps[order[:k]]), ()
    return np.sort(rng.permutation(steps)[:k]), ()   # W-absence: no latent to rank by


def _emit(family, kind, t, crit, rng, flip_p, pv):
    def val(c):
        v = 1 if crit[c][t] else -1
        return -v if rng.random() < flip_p else v

    if family == "W-scope":                      # both kinds show both conditions, so the
        return tuple(Evidence(Scope(SUBJECT, PROP, c, t), val(c), pv)  # SHAPE of the record
                     for c in CONDITIONS)                              # cannot give it away
    if kind == "sig" and family == "W-absence":
        c = CONDITIONS[1]
        return (Evidence(Scope(SUBJECT, OTHER_PROP, c, t), val(c), pv),)
    if kind == "sig" and family == "W-conflict":
        c = CONDITIONS[1]
        v = val(c)
        return (Evidence(Scope(SUBJECT, PROP, c, t), v, pv),
                Evidence(Scope(SUBJECT, PROP, c, t), -v, pv))
    c = CONDITIONS[1]
    if kind == "sig" and family == "W-pause":
        v = val(c)                               # the two observations AGREE and the support
        return (Evidence(Scope(SUBJECT, PROP, c, t), v, "post"),   # was given: lambda(P_next)
                Evidence(Scope(SUBJECT, PROP, c, t), v, "post"))   # = T, and only omega stops
    return (Evidence(Scope(SUBJECT, PROP, c, t), val(c), pv),   # baseline: two independent
            Evidence(Scope(SUBJECT, PROP, c, t), val(c), pv))   # readings, so noise can split


def make_world(family: str, T: int = 400, seed: int = 0, meas_noise: float = 0.1,
               keep_frac: float = 1.0, flip_p: float = FLIP_P,
               signature_frac: float = SIGNATURE_FRAC, spont_frac: float = SPONT_FRAC,
               window: int = WINDOW, gap: float = GAP) -> World:
    """One decision world. `truth` records the planted action at every step and
    is not reachable from `World.inp`."""
    assert family in FAMILIES, family
    rng = np.random.default_rng(seed)
    traj = generate("M1", T=T, seed=seed, pause_frac=0.0)
    obs = observe(traj, meas_noise=meas_noise, keep_frac=keep_frac, seed=seed)
    z = _readings(traj.x, gap)
    crit = {c: z[c] > 0 for c in CONDITIONS}
    steps = np.arange(window, T)
    sig, pauses = _signature_steps(family, steps, z, crit, traj.u, rng, signature_frac)
    sig_set = {int(t) for t in sig}

    evidence, optimal, kind = {}, np.full(T, "", dtype=object), np.full(T, "", dtype=object)
    for t in steps:
        t = int(t)
        kind[t] = "sig" if t in sig_set else "base"
        pv = "spont" if rng.random() < spont_frac else "post"
        items = _emit(family, kind[t], t, crit, rng, flip_p, pv)
        evidence[t] = items
        active = any(p.covers(SUBJECT, ACTION_CLASS, t) for p in pauses)
        optimal[t] = reference_action(
            items, bool(crit["apoiada"][t] != crit["nao_apoiada"][t]), active)
    pause = np.zeros(T, bool)
    for p in pauses:
        pause[p.t0:p.t1] = True

    inp = DecisionInput(obs=obs, evidence=evidence, pauses=tuple(pauses), pause=pause,
                        window=window, subject=SUBJECT, prop=PROP, T=T)
    truth = dict(family=family, optimal=optimal, kind=kind, crit=crit, z=z, u=traj.u,
                 x=traj.x, flip_p=flip_p, seed=seed, gap=gap,
                 signature_frac_realised=float(len(sig) / len(steps)))
    return World(inp=inp, truth=truth)
