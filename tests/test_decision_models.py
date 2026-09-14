"""M0 / M1 / M2: one estimator, one set of steps, and layers that actually differ."""
import numpy as np
import pytest

from decision.eligible import eligible_steps
from decision.models import (ABLATION, ALL_MODELS, MODELS, fit_estimator, m0_action,
                             run_models, ssm_params)
from decision.warrant import load_chi
from decision.worlds import FAMILIES, make_world


def test_the_estimator_is_the_same_object_with_the_same_fitted_parameters():
    """Item 2. A better Kalman filter must not be creditable to the epistemic
    layer, so the comparison is of FITTED PARAMETERS, not of types."""
    w = make_world("W-scope", T=300, seed=1, keep_frac=0.8)
    runs = run_models(w.inp)
    ref = ssm_params(runs["M0"].ssm)
    for name in ALL_MODELS:
        assert runs[name].ssm is runs["M0"].ssm, name
        got = ssm_params(runs[name].ssm)
        for k in ("A", "B", "Q", "R"):
            assert np.array_equal(got[k], ref[k]), (name, k)
        assert got["loglik"] == ref["loglik"], name
    again = ssm_params(fit_estimator(w.inp))                 # and the fit is deterministic
    for k in ("A", "B", "Q", "R"):
        assert np.allclose(again[k], ref[k]), k


def test_every_model_is_scored_on_the_same_index_set():
    """Not the same COUNT — the same SET. M2 abstains where M1 acts, so a model
    allowed to pick its own denominator could look good by answering less."""
    for keep in (1.0, 0.7):
        w = make_world("W-pause", T=300, seed=2, keep_frac=keep)
        runs = run_models(w.inp)
        want = set(int(t) for t in eligible_steps(w.inp))
        for name in ALL_MODELS:
            assert set(runs[name].action) == want, (name, keep)
            assert set(runs[name].conf) == want, (name, keep)


def test_the_eligibility_predicate_bites_under_missing_data_and_is_identity_without():
    full = make_world("W-scope", T=300, seed=3, keep_frac=1.0)
    holes = make_world("W-scope", T=300, seed=3, keep_frac=0.7)
    assert len(eligible_steps(full.inp)) == full.inp.T - full.inp.window
    assert len(eligible_steps(holes.inp)) < 0.85 * len(eligible_steps(full.inp))
    idx = eligible_steps(holes.inp)
    obs_t = set(int(t) for t in holes.inp.obs.t)
    assert all(t in obs_t and (t - 1) in obs_t for t in idx)


def test_m0_cannot_separate_a_conflict_from_a_condition_difference():
    """The whole of M1's case against M0, isolated: the aggregate is the same."""
    from decision.epistemic import lambda_of, lambda_policy
    from decision.models import evidence_aggregate
    from decision.worlds import CONDITIONS, PROP, SUBJECT, Evidence, Scope
    ap, nao = CONDITIONS
    same = (Evidence(Scope(SUBJECT, PROP, nao, 5), 1, "post"),
            Evidence(Scope(SUBJECT, PROP, nao, 5), -1, "post"))
    across = (Evidence(Scope(SUBJECT, PROP, ap, 5), 1, "post"),
              Evidence(Scope(SUBJECT, PROP, nao, 5), -1, "post"))
    assert evidence_aggregate(same, PROP, 5, 1) == evidence_aggregate(across, PROP, 5, 1)
    assert m0_action(*evidence_aggregate(same, PROP, 5, 1)) == "PROBE"
    assert m0_action(*evidence_aggregate(across, PROP, 5, 1)) == "PROBE"
    assert lambda_policy(lambda_of(same, PROP, 5, 1)) == "PROBE"
    assert lambda_policy(lambda_of(across, PROP, 5, 1)) == "COMPARE"


def test_m0_is_not_handicapped_on_absence():
    """M0 sees the item COUNT, so N versus B is inside its reach. If M1 beats it
    on W-absence the reason has to be something other than a crippled baseline."""
    assert m0_action(0, 0.0) == "OBSERVE"
    assert m0_action(2, 0.0) == "PROBE"


def test_only_m2_and_the_ablation_ever_wait():
    w = make_world("W-pause", T=300, seed=4)
    runs = run_models(w.inp)
    assert "WAIT" not in set(runs["M0"].action.values())
    assert "WAIT" not in set(runs["M1"].action.values())
    assert "WAIT" in set(runs["M2"].action.values())
    assert "WAIT" in set(runs[ABLATION].action.values())


def test_m2_differs_from_m1_only_where_a_warrant_is_denied():
    for fam in FAMILIES:
        w = make_world(fam, T=300, seed=5)
        runs = run_models(w.inp)
        for t in runs["M1"].action:
            same = runs["M2"].action[t] == runs["M1"].action[t]
            assert same == (runs["M2"].reason[t] == ""), (fam, t)


def test_the_ablation_is_m2_minus_everything_except_the_pause():
    """If these two never diverge, omega is a flag check and the README has to
    say so. They must at least be able to diverge: provenance is the difference."""
    w = make_world("W-absence", T=400, seed=6)
    runs = run_models(w.inp)
    diff = [t for t in runs["M2"].action if runs["M2"].action[t] != runs[ABLATION].action[t]]
    assert diff, "the provenance clause never bound: chi would be scenery"
    assert all(runs["M2"].reason[t] == "provenance" for t in diff)


def test_chi_governs_the_admissibility_window():
    w = make_world("W-scope", T=200, seed=7, window=2)
    with pytest.raises(AssertionError):
        run_models(w.inp, load_chi())


def test_truth_cannot_change_what_any_model_does():
    w = make_world("W-scope", T=300, seed=8)
    before = {k: dict(v.action) for k, v in run_models(w.inp).items()}
    w.truth["optimal"][:] = "ACT"
    w.truth["crit"] = None
    after = {k: dict(v.action) for k, v in run_models(w.inp).items()}
    assert before == after
