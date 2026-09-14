"""Criteria EXTERNAL to the warrant rules.

"M2 chooses different actions, therefore M2 is useful" is not a finding, it is a
restatement of chi. Everything here is scored against what happens in the world:
evidence that arrives later, the latent condition structure, the authorization
on the record, and the calibration of the confidence attached to intervening.

DENOMINATORS ARE SHARED. Every rate is computed over an index set that is the
same for every model — the eligible steps, or a subset of them defined by the
WORLD (steps inside a pause, steps where the conditions really differ) and never
by the model's own behaviour. A model that abstains answers fewer questions; it
must not thereby be asked fewer questions.

Follow-up draws are seeded from (world seed, t), so all models see the SAME
returned evidence at the same step. Seeding per model would let the comparison
turn on which one got the luckier probe.
"""
from __future__ import annotations
import zlib

import numpy as np

from .epistemic import lambda_of
from .worlds import CONDITIONS, reference_action

REQUESTS = ("OBSERVE", "PROBE", "COMPARE")
CONTRADICT_K = 5          # steps ahead in which a later reading may contradict an action
DEFAULT_C = CONDITIONS[1]

#: Higher is better for these; lower is better for the rest.
HIGHER_IS_BETTER = {"accuracy": True, "request_resolution_rate": True,
                    "unsupported_counterfactual_rate": False, "contradicted_rate": False,
                    "brier_act": False, "pause_violation_rate": False,
                    "deficit_inference_rate": False}

#: The criterion each family is built to expose. Reported per family, never pooled.
PRIMARY = {"W-absence": "request_resolution_rate", "W-conflict": "request_resolution_rate",
           "W-scope": "deficit_inference_rate", "W-pause": "pause_violation_rate"}

METRICS = tuple(HIGHER_IS_BETTER)


def _true_value(crit, c, t) -> int:
    return 1 if crit[c][t] else -1


def _rng(seed: int, t: int):
    return np.random.default_rng(zlib.crc32(repr(("followup", seed, t)).encode()) % (2 ** 31))


def _settles(world, t: int, action: str) -> bool:
    """Does the evidence this request returns settle the question the step poses?

    The STRUCTURAL half is a statement about what each request does, written into
    the world and not measured: an OBSERVE visits one condition once, so it can
    end an absence but cannot supersede a contested reading nor reach a second
    condition; a PROBE replaces the contested reading with two fresh ones, so it
    ends a conflict and establishes whether a support was given, but still visits
    one condition; a COMPARE visits both. The NOISE half is measured: a correctly
    aimed request still fails when the evidence it returns is flipped, and that
    is why a probe costs less than a comparison but buys less.
    """
    if action not in REQUESTS:
        return False
    if world.truth["optimal"][t] != action:
        return False
    crit, f = world.truth["crit"], world.truth["flip_p"]
    rng = _rng(int(world.truth["seed"]), int(t))

    def draw(c):
        v = _true_value(crit, c, t)
        return -v if rng.random() < f else v

    if action == "OBSERVE":
        return draw(DEFAULT_C) == _true_value(crit, DEFAULT_C, t)
    if action == "PROBE":
        a, b = draw(DEFAULT_C), draw(DEFAULT_C)
        return a == b == _true_value(crit, DEFAULT_C, t)
    return all(draw(c) == _true_value(crit, c, t) for c in CONDITIONS)


def _future_contradicts(world, t: int, conds, v: int) -> bool:
    """Did a later reading IN THE SAME CONDITION come back the other way? A
    disagreement across conditions is not a contradiction, it is the thing
    W-scope plants, and counting it here would charge the models twice."""
    T = world.inp.T
    for s in range(t + 1, min(t + 1 + CONTRADICT_K, T)):
        for e in world.inp.evidence.get(s, ()):
            if e.scope.O == world.inp.prop and e.scope.C in conds and e.value == -v:
                return True
    return False


def evaluate(world, runs: dict) -> dict:
    """Every metric, for every model, on shared denominators."""
    inp, truth = world.inp, world.truth
    idx = [int(t) for t in next(iter(runs.values())).idx]
    crit = truth["crit"]
    paused = [t for t in idx if inp.pause[t]]
    scope_steps = [t for t in idx if crit["apoiada"][t] != crit["nao_apoiada"][t]]

    lam = {t: lambda_of(inp.evidence.get(t, ()), inp.prop, t, inp.window) for t in idx}
    settles = {t: {a: _settles(world, t, a) for a in REQUESTS} for t in idx}
    out = {}
    for name, run in runs.items():
        assert [int(t) for t in run.idx] == idx, name          # one denominator, asserted
        acts = {t: run.action[t] for t in idx}
        n = len(idx)
        hit = [acts[t] == truth["optimal"][t] for t in idx]
        res = [settles[t].get(acts[t], False) for t in idx]
        unsupported = [acts[t] == "ACT" and not lam[t].has_post() for t in idx]
        brier = [(run.conf[t] - float(truth["optimal"][t] == "ACT")) ** 2 for t in idx]
        contra = []
        for t in idx:
            if acts[t] != "ACT" or lam[t].empty():
                contra.append(False)
                continue
            conds = set(lam[t].by_cond)
            v = 1 if lam[t].collapsed() == "T" else -1
            contra.append(_future_contradicts(world, t, conds, v))
        out[name] = {
            "accuracy": float(np.mean(hit)),
            "request_resolution_rate": float(np.mean(res)),
            "unsupported_counterfactual_rate": float(np.mean(unsupported)),
            "contradicted_rate": float(np.mean(contra)),
            "brier_act": float(np.mean(brier)),
            "pause_violation_rate": (float(np.mean([acts[t] == "ACT" for t in paused]))
                                     if paused else float("nan")),
            "deficit_inference_rate": (float(np.mean([acts[t] in ("ACT", "PROBE")
                                                      for t in scope_steps]))
                                       if scope_steps else float("nan")),
            "n_steps": n, "n_paused": len(paused), "n_scope": len(scope_steps),
        }
    return out


def ceiling(world) -> dict:
    """What a reader of the RECORD can reach at best: the reference action
    recomputed from the record alone, with the latent condition difference read
    off the record instead of off the world. The gap to 1.0 is evidence noise,
    not a layer. A bench whose ceiling is unknown cannot say whether a model
    fell short of the world or of the sensor."""
    inp, truth = world.inp, world.truth
    idx = [int(t) for t in _all_steps(world)]
    hit = []
    for t in idx:
        items = inp.evidence.get(t, ())
        lam = lambda_of(items, inp.prop, t, inp.window)
        best = reference_action(items, lam.cross_scope(), bool(inp.pause[t]))
        hit.append(best == truth["optimal"][t])
    return {"record_ceiling": float(np.mean(hit)), "n_steps": len(idx)}


def _all_steps(world):
    from .eligible import eligible_steps
    return eligible_steps(world.inp)
