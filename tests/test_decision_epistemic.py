"""Lambda: four values, scope separation, provenance carried but not acted on."""
import pytest

from decision.epistemic import MERGED, Lambda, blind_action, collapse, lambda_of, lambda_policy
from decision.worlds import CONDITIONS, PROP, Evidence, Scope

AP, NAO = CONDITIONS


def ev(c, v, t=5, prov="post", O=PROP):
    return Evidence(Scope("S1", O, c, t), v, prov)


def test_the_four_values_are_the_four_cases():
    assert lambda_of((), PROP, 5, 1).collapsed() == "N"
    assert lambda_of((ev(NAO, 1),), PROP, 5, 1).collapsed() == "T"
    assert lambda_of((ev(NAO, -1),), PROP, 5, 1).collapsed() == "F"
    assert lambda_of((ev(NAO, 1), ev(NAO, -1)), PROP, 5, 1).collapsed() == "B"


def test_n_and_b_are_the_pair_a_scalar_summary_cannot_separate():
    """Both have mean 0 and both read as an uninformative middle; only the
    labels differ, and they ask for different actions."""
    absent = lambda_of((), PROP, 5, 1)
    both = lambda_of((ev(NAO, 1), ev(NAO, -1)), PROP, 5, 1)
    assert absent.empty() and not both.empty()
    assert lambda_policy(absent) == "OBSERVE"
    assert lambda_policy(both) == "PROBE"


def test_scope_separates_a_conflict_from_a_condition_difference():
    same = lambda_of((ev(NAO, 1), ev(NAO, -1)), PROP, 5, 1)
    across = lambda_of((ev(AP, 1), ev(NAO, -1)), PROP, 5, 1)
    assert same.conflict() and not same.cross_scope()
    assert across.cross_scope() and not across.conflict()
    assert across.collapsed() == same.collapsed() == "B"      # identical without C
    assert lambda_policy(across) == "COMPARE" and lambda_policy(same) == "PROBE"


def test_agreement_across_conditions_is_not_a_comparison():
    lam = lambda_of((ev(AP, 1), ev(NAO, 1)), PROP, 5, 1)
    assert lam.decided() and not lam.cross_scope()
    assert lambda_policy(lam) == "ACT"


def test_evidence_outside_the_window_is_not_admissible():
    stale = lambda_of((ev(NAO, 1, t=2),), PROP, 5, window=1)
    fresh = lambda_of((ev(NAO, 1, t=5),), PROP, 5, window=1)
    assert stale.empty() and not fresh.empty()
    assert lambda_of((ev(NAO, 1, t=2),), PROP, 5, window=4).collapsed() == "T"


def test_evidence_about_another_proposition_is_not_admissible():
    lam = lambda_of((ev(NAO, 1, O="q"),), PROP, 5, 1)
    assert lam.empty() and lambda_policy(lam) == "OBSERVE"


def test_provenance_is_carried_and_not_acted_on():
    spont = lambda_of((ev(NAO, 1, prov="spont"), ev(NAO, 1, prov="spont")), PROP, 5, 1)
    post = lambda_of((ev(NAO, 1), ev(NAO, 1)), PROP, 5, 1)
    assert not spont.has_post() and post.has_post()
    assert lambda_policy(spont) == lambda_policy(post) == "ACT"   # the rule lives in chi


def test_each_collapse_drops_exactly_one_distinction():
    absent = lambda_of((), PROP, 5, 1)
    both = lambda_of((ev(NAO, 1), ev(NAO, -1)), PROP, 5, 1)
    across = lambda_of((ev(AP, 1), ev(NAO, -1)), PROP, 5, 1)
    assert collapse(absent, "N->B").by_cond == {MERGED: "B"}
    assert collapse(both, "N->B") is both                        # only absence is touched
    assert collapse(both, "B->N").empty()
    assert collapse(across, "drop-scope").by_cond == {MERGED: "B"}
    assert collapse(across, "B->N") is not None and across.cross_scope()
    with pytest.raises(ValueError):
        collapse(both, "no-such-mode")


def test_the_blind_policy_of_each_family_answers_something_else():
    absent = lambda_of((), PROP, 5, 1)
    both = lambda_of((ev(NAO, 1), ev(NAO, -1)), PROP, 5, 1)
    across = lambda_of((ev(AP, 1), ev(NAO, -1)), PROP, 5, 1)
    decided = lambda_of((ev(NAO, 1), ev(NAO, 1)), PROP, 5, 1)
    assert blind_action("W-absence", absent, False) == "PROBE"      # want OBSERVE
    assert blind_action("W-conflict", both, False) == "OBSERVE"     # want PROBE
    assert blind_action("W-scope", across, False) == "PROBE"        # want COMPARE
    assert blind_action("W-pause", decided, True) == "ACT"          # want WAIT
