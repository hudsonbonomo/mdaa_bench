"""The decision worlds: the correct action is PLANTED, and each family's
distinction is not vacuous.

The non-vacuity test is the one that matters. A family only tests a layer if a
policy that COLLAPSES the distinction that family turns on is wrong on most of
its steps. The floor is `worlds.NON_VACUITY_FLOOR`; the realised numbers are
printed by `scripts/decision_nonvacuity.py` and written into the pre-registration.
"""
import numpy as np

from decision.worlds import (ACTIONS, CONDITIONS, FAMILIES, NON_VACUITY_FLOOR,
                             PROP, SUBJECT, make_world)
from decision.epistemic import blind_action, lambda_of
from decision.eligible import eligible_steps

WANTED = {"W-absence": "OBSERVE", "W-conflict": "PROBE",
          "W-scope": "COMPARE", "W-pause": "WAIT"}


def _lam(w, t):
    return lambda_of(w.inp.evidence.get(t, ()), PROP, t, w.inp.window)


def test_every_eligible_step_carries_a_planted_action():
    for fam in FAMILIES:
        w = make_world(fam, T=300, seed=1)
        idx = eligible_steps(w.inp)
        assert len(idx) > 200, fam
        assert all(w.truth["optimal"][t] in ACTIONS for t in idx), fam


def test_each_family_asks_for_its_own_action_on_its_signature_steps():
    for fam, want in WANTED.items():
        w = make_world(fam, T=300, seed=2)
        sig = [t for t in eligible_steps(w.inp) if w.truth["kind"][t] == "sig"]
        share = float(np.mean([w.truth["optimal"][t] == want for t in sig]))
        assert share > 0.95, (fam, want, share)


def test_signature_steps_are_the_majority_by_construction():
    for fam in FAMILIES:
        w = make_world(fam, T=400, seed=3)
        idx = eligible_steps(w.inp)
        share = float(np.mean([w.truth["kind"][t] == "sig" for t in idx]))
        assert share >= NON_VACUITY_FLOOR, (fam, share)


def test_a_policy_that_collapses_the_distinction_is_wrong_on_most_steps():
    """Item 1's non-vacuity requirement, asserted in code rather than inferred
    from the absence of a divergence."""
    for fam in FAMILIES:
        w = make_world(fam, T=400, seed=4)
        idx = eligible_steps(w.inp)
        wrong = [blind_action(fam, _lam(w, t), bool(w.inp.pause[t])) != w.truth["optimal"][t]
                 for t in idx]
        assert float(np.mean(wrong)) >= NON_VACUITY_FLOOR, (fam, float(np.mean(wrong)))


def test_baseline_steps_ask_to_act_unless_the_support_was_spontaneous():
    for fam in FAMILIES:
        w = make_world(fam, T=400, seed=5)
        base = [t for t in eligible_steps(w.inp) if w.truth["kind"][t] == "base"]
        assert len(base) > 20, fam
        acts = [w.truth["optimal"][t] for t in base]
        assert set(acts) <= {"ACT", "PROBE"}, (fam, set(acts))
        share = float(np.mean([a == "ACT" for a in acts]))
        assert 0.5 < share < 1.0, (fam, share)


def test_the_scope_family_plants_a_real_condition_difference():
    w = make_world("W-scope", T=400, seed=6)
    crit = w.truth["crit"]
    for t in eligible_steps(w.inp):
        differ = bool(crit["apoiada"][t] != crit["nao_apoiada"][t])
        assert differ == (w.truth["kind"][t] == "sig"), t
        conds = {e.scope.C for e in w.inp.evidence[t] if e.scope.O == PROP}
        assert conds == set(CONDITIONS), t          # both kinds show both conditions


def test_the_conflict_family_conflicts_inside_one_scope():
    w = make_world("W-conflict", T=400, seed=7)
    for t in eligible_steps(w.inp):
        if w.truth["kind"][t] != "sig":
            continue
        items = [e for e in w.inp.evidence[t] if e.scope.O == PROP]
        assert len({e.scope.C for e in items}) == 1, t
        assert {e.value for e in items} == {1, -1}, t
        assert _lam(w, t).conflict() and not _lam(w, t).cross_scope()


def test_the_absence_family_leaves_a_record_that_is_not_empty():
    w = make_world("W-absence", T=400, seed=8)
    for t in eligible_steps(w.inp):
        if w.truth["kind"][t] != "sig":
            continue
        assert w.inp.evidence[t], t                              # something was recorded
        assert not [e for e in w.inp.evidence[t] if e.scope.O == PROP], t
        assert _lam(w, t).empty()


def test_the_pause_is_authorized_where_no_forcing_was_logged():
    w = make_world("W-pause", T=400, seed=9)
    u = w.truth["u"]
    assert w.inp.pauses, "W-pause must carry pause records"
    for p in w.inp.pauses:
        assert not np.abs(u[p.t0:p.t1]).any()                    # u_ped = 0 inside the pause
        assert p.subject == SUBJECT and p.action_class == "ACT"
    other = make_world("W-scope", T=400, seed=9)
    assert not other.inp.pauses and not other.inp.pause.any()


def test_truth_never_reaches_the_decision_input():
    w = make_world("W-scope", T=200, seed=10)
    assert not hasattr(w.inp, "truth")
    blob = repr(w.inp)
    assert "optimal" not in blob and "crit" not in blob
    assert repr(make_world("W-scope", T=200, seed=10).inp) == blob   # the seed reproduces it


def test_evidence_noise_is_the_only_thing_that_can_fool_a_perfect_reader():
    clean = make_world("W-scope", T=400, seed=11, flip_p=0.0)
    for t in eligible_steps(clean.inp):
        lam = _lam(clean, t)
        got = "COMPARE" if lam.cross_scope() else ("ACT" if lam.has_post() else "PROBE")
        assert got == clean.truth["optimal"][t], (t, got, clean.truth["optimal"][t])
