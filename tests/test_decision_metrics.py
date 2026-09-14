"""The external criteria: shared denominators, and none of them is 'M2 differed'."""
import numpy as np
import pytest

from decision.eligible import eligible_steps
from decision.metrics import METRICS, PRIMARY, ceiling, evaluate
from decision.models import ABLATION, ALL_MODELS, Run, run_models
from decision.worlds import FAMILIES, make_world


def _runs(fam, **kw):
    w = make_world(fam, T=300, seed=1, **kw)
    return w, run_models(w.inp)


def test_every_metric_is_reported_for_every_model():
    for fam in FAMILIES:
        w, runs = _runs(fam)
        res = evaluate(w, runs)
        assert set(res) == set(ALL_MODELS), fam
        for name, m in res.items():
            for k in METRICS:
                assert k in m, (fam, name, k)


def test_the_denominators_are_the_same_for_every_model():
    for fam in FAMILIES:
        w, runs = _runs(fam)
        res = evaluate(w, runs)
        for k in ("n_steps", "n_paused", "n_scope"):
            assert len({res[n][k] for n in res}) == 1, (fam, k)
        assert res["M0"]["n_steps"] == len(eligible_steps(w.inp))


def test_a_model_scored_on_a_different_set_of_steps_is_refused():
    w, runs = _runs("W-scope")
    cut = Run(name="M0", idx=runs["M0"].idx[:-5], action=runs["M0"].action,
              conf=runs["M0"].conf, reason=runs["M0"].reason)
    with pytest.raises(AssertionError):
        evaluate(w, {"M0": cut, "M1": runs["M1"]})


def test_only_models_that_can_wait_avoid_violating_the_pause():
    w, runs = _runs("W-pause")
    res = evaluate(w, runs)
    assert res["M0"]["pause_violation_rate"] > 0.5
    assert res["M1"]["pause_violation_rate"] > 0.5
    assert res["M2"]["pause_violation_rate"] == 0.0
    assert res[ABLATION]["pause_violation_rate"] == 0.0


def test_the_pause_rate_is_nan_where_no_pause_was_authorized():
    for fam in ("W-absence", "W-conflict", "W-scope"):
        w, runs = _runs(fam)
        assert np.isnan(evaluate(w, runs)["M0"]["pause_violation_rate"]), fam


def test_only_the_warrant_layer_refuses_an_unsupported_counterfactual():
    w, runs = _runs("W-absence")
    res = evaluate(w, runs)
    assert res["M2"]["unsupported_counterfactual_rate"] == 0.0
    assert res["M1"]["unsupported_counterfactual_rate"] > 0.0
    assert res[ABLATION]["unsupported_counterfactual_rate"] > 0.0   # the pause flag is not it


def test_a_probe_cannot_settle_a_condition_difference():
    """The instrument that separates M0 from M1 on W-scope: both ask, one asks a
    question whose answer cannot resolve the case."""
    w, runs = _runs("W-scope")
    res = evaluate(w, runs)
    assert res["M0"]["deficit_inference_rate"] > 0.9      # every scope step read as S's problem
    assert res["M1"]["deficit_inference_rate"] < 0.1
    assert res["M1"]["request_resolution_rate"] > res["M0"]["request_resolution_rate"]


def test_evidence_noise_is_what_keeps_resolution_below_one():
    clean, runs_c = make_world("W-scope", T=300, seed=2, flip_p=0.0), None
    runs_c = run_models(clean.inp)
    noisy = make_world("W-scope", T=300, seed=2, flip_p=0.25)
    res_c = evaluate(clean, runs_c)
    res_n = evaluate(noisy, run_models(noisy.inp))
    assert res_c["M2"]["request_resolution_rate"] > res_n["M2"]["request_resolution_rate"]


def test_the_ceiling_is_one_where_the_record_decides_and_below_one_where_it_cannot():
    """Three families are fully determined by the record, so a perfect reader
    reaches 1.0 and every shortfall belongs to a layer. W-scope is the exception
    by construction: a cross-condition disagreement on the record may be a
    flipped item, and no reader of the record can tell. That gap is the sensor,
    not a layer, and it is why the figure carries the ceiling."""
    for fam in FAMILIES:
        w, runs = _runs(fam)
        c = ceiling(w)["record_ceiling"]
        res = evaluate(w, runs)
        if fam == "W-scope":
            assert 0.85 <= c < 1.0, (fam, c)
        else:
            assert c == 1.0, (fam, c)
        assert all(res[n]["accuracy"] <= c + 1e-9 for n in res), (fam, c, res)


def test_every_family_names_a_primary_criterion_that_exists():
    assert set(PRIMARY) == set(FAMILIES)
    assert all(v in METRICS for v in PRIMARY.values())


def test_a_disagreement_across_conditions_is_not_counted_as_a_contradiction():
    w, runs = _runs("W-scope")
    res = evaluate(w, runs)
    assert res["M1"]["contradicted_rate"] < 0.35
