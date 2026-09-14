"""The three adversarial models of Paper 4, plus one ablation.

  M0   policy over b(t) and the observed context. The evidence reaches it as a
       SCALAR AGGREGATE over the same admissible items Lambda labels: how many,
       and which way on average. Nothing is withheld from M0 except structure.
  M1   M0 + Lambda(t) explicit: T/F/B/N per proposition, per scope, with
       provenance attached.
  M2   M1 + Omega(t): warrant per action under the frozen chi.

  M1+pausa   THE ABLATION, and the reason this file is not a demonstration.
       M1 with one line added — never ACT while an authorization is in force —
       and nothing else of Omega. If it matches M2, then omega is a flag check
       and the architecture does not need a warrant layer to do it. Reported
       next to the three, never instead of them.

THE ESTIMATOR IS THE SAME OBJECT IN ALL OF THEM. `fit_estimator` is the single
entry point and every model consumes its output; `tests/test_decision_models.py`
compares the FITTED PARAMETERS across the models, not their types, because a
better Kalman filter must never be creditable to the epistemic layer.

The pause flag is in every model's input (`inp.pause`) and M0 and M1 do not
consult it. That is a claim about POLICY, not about information, and the
ablation is what keeps it honest: the bench measures what the flag alone buys.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np

from sim.statespace import SSM, em_fit, kalman, to_grid
from .eligible import eligible_steps
from .epistemic import lambda_of, lambda_policy
from .warrant import Chi, load_chi, remedy, warranted

MODELS = ("M0", "M1", "M2")
ABLATION = "M1+pausa"
ALL_MODELS = MODELS + (ABLATION,)

M0_DECIDED = 0.5      # |mean| below this reads as contested. Exploratory, uncalibrated.
M0_BELIEF_Z = 2.0     # state sds at which M0 calls its own belief confident. Exploratory.
CONF_DECIDED = 0.9    # Lambda has no probabilities; these are the declared stand-ins,
CONF_UNDECIDED = 0.1  # fixed before the pilot and not tuned afterwards.
CONF_DENIED = 0.02


@dataclass
class Run:
    name: str
    idx: np.ndarray
    action: dict = field(default_factory=dict)     # t -> action
    conf: dict = field(default_factory=dict)       # t -> P(acting now is correct)
    reason: dict = field(default_factory=dict)     # t -> warrant reason, "" when none
    ssm: SSM | None = None


def fit_estimator(inp) -> SSM:
    """THE estimator. One linear-Gaussian state space, fitted by EM on the
    observation channel, shared by every model in the contest."""
    y, u, mask = to_grid(inp.obs, t_max=inp.T)
    return em_fit(y, u, mask)


def beliefs(ssm: SSM, inp):
    """b(t): the one-step-ahead predictive mean and covariance. Uses y_{<t} only,
    so a belief at t is never a view of the answer at t."""
    y, u, mask = to_grid(inp.obs, t_max=inp.T)
    xp, Pp, _, _, _ = kalman(ssm, y, u, mask)
    return xp, Pp


def ssm_params(ssm: SSM) -> dict:
    return dict(A=np.asarray(ssm.A), B=np.asarray(ssm.B), Q=np.asarray(ssm.Q),
                R=np.asarray(ssm.R), loglik=float(ssm.loglik))


def evidence_aggregate(items, prop: str, t: int, window: int):
    """What M0 gets: count and mean over exactly the items Lambda would admit.
    The admissibility window is shared, so the only difference between M0's view
    and M1's is the summary, not the data."""
    vals = [e.value for e in items if e.scope.O == prop and t - window < e.scope.t <= t]
    return len(vals), (float(np.mean(vals)) if vals else 0.0)


def m0_action(n: int, e: float) -> str:
    """A scalar reader's best policy. It separates 'nothing on record' from
    'balanced' by the COUNT — it is not handicapped there — and it cannot
    separate a balanced scope from two conditions that disagree, because the
    mean of +1 and -1 is 0 either way."""
    if n == 0:
        return "OBSERVE"
    if abs(e) < M0_DECIDED:
        return "PROBE"
    return "ACT"


def m0_confidence(n: int, e: float, xhat: np.ndarray, P: np.ndarray) -> float:
    """Where b(t) enters M0. The action is decided by the evidence aggregate,
    which is the only thing in M0's input that speaks about the proposition; the
    belief supplies how sure the system is that intervening is right."""
    if n == 0:
        return 0.0
    sd = float(np.sqrt(max(P[0, 0], 1e-12)))
    return float(abs(e) * np.clip(abs(xhat[0]) / (M0_BELIEF_Z * sd), 0.0, 1.0))


def _lambda_confidence(lam) -> float:
    return CONF_DECIDED if lam.decided() else CONF_UNDECIDED


def m2_decide(chi: Chi, lam, pauses, subject: str, t: int):
    """M1's proposal, then Omega. A denial is redirected to the remedy chi
    prescribes for that reason, never left as a refusal."""
    proposed = lambda_policy(lam)
    v = warranted(chi, proposed, lam, pauses, subject, t)
    if v.ok:
        return proposed, ""
    return remedy(chi, proposed, v.reason), v.reason


def run_models(inp, chi: Chi | None = None) -> dict:
    """Run every model on THE SAME eligible steps, with THE SAME estimator."""
    chi = load_chi() if chi is None else chi
    assert chi.window == inp.window, (chi.window, inp.window)   # chi governs admissibility
    idx = eligible_steps(inp)
    ssm = fit_estimator(inp)
    xp, Pp = beliefs(ssm, inp)
    runs = {name: Run(name=name, idx=idx, ssm=ssm) for name in ALL_MODELS}

    for t in idx:
        t = int(t)
        items = inp.evidence.get(t, ())
        lam = lambda_of(items, inp.prop, t, inp.window)
        n, e = evidence_aggregate(items, inp.prop, t, inp.window)
        paused = any(p.covers(inp.subject, "ACT", t) for p in inp.pauses)

        runs["M0"].action[t] = m0_action(n, e)
        runs["M0"].conf[t] = m0_confidence(n, e, xp[t], Pp[t])
        runs["M0"].reason[t] = ""

        a1 = lambda_policy(lam)
        runs["M1"].action[t] = a1
        runs["M1"].conf[t] = _lambda_confidence(lam)
        runs["M1"].reason[t] = ""

        a2, why = m2_decide(chi, lam, inp.pauses, inp.subject, t)
        runs["M2"].action[t] = a2
        runs["M2"].conf[t] = CONF_DENIED if why else _lambda_confidence(lam)
        runs["M2"].reason[t] = why

        blocked = paused and a1 == "ACT"
        runs[ABLATION].action[t] = "WAIT" if blocked else a1
        runs[ABLATION].conf[t] = CONF_DENIED if blocked else _lambda_confidence(lam)
        runs[ABLATION].reason[t] = "pause" if blocked else ""
    return runs
