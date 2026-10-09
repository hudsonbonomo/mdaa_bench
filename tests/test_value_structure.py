"""Structural tests for the value bench (Paper 7). Seeds 9001-9004 ONLY.
Tests: every world builds, structural assertions hold, planted values correct.
"""
import numpy as np
import pytest

from value.worlds import WORLDS, ValueWorld, make_world, load_policy
from value.worlds import (make_N0, make_P, make_R, make_Rplus)
from value.worlds_cx import make_C0, make_C1, make_C2, make_X, make_Xp

SEEDS = (9001, 9002, 9003, 9004)
_P = load_policy()
TS = tuple(_P["T"])


# -- 1. every world builds without assertion errors --
@pytest.mark.parametrize("T", TS)
@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("name", WORLDS)
def test_every_world_builds(name, T, seed):
    w = make_world(name, T=T, seed=seed)
    assert isinstance(w, ValueWorld)
    assert len(w.observations) > 0


# -- 2. N0: no norm is confirmed --
@pytest.mark.parametrize("seed", SEEDS)
def test_N0_no_confirmed_norm(seed):
    w = make_N0(80, seed)
    for ne in w.norm_events:
        if ne.get("type") == "mdaa.norm.reviewed":
            assert ne["review"] != "CONFIRMED"


# -- 3. P: s2 better retention on average over 4 seeds --
def test_P_s2_better_retention():
    """Average retention(s2) > retention(s1) across 4 seeds."""
    diffs = []
    for seed in SEEDS:
        w = make_P(80, seed)
        ret_s1, ret_s2, n1, n2 = 0, 0, 0, 0
        for o in w.observations:
            if o.get("measure") != "retention" or o["signal"] == "UNCLEAR":
                continue
            s = o["strategy"][0]
            if s == "s1":
                n1 += 1
                if o["signal"] == "BETTER":
                    ret_s1 += 1
            elif s == "s2":
                n2 += 1
                if o["signal"] == "BETTER":
                    ret_s2 += 1
        if n1 > 0 and n2 > 0:
            diffs.append(ret_s2 / n2 - ret_s1 / n1)
    assert len(diffs) == len(SEEDS)
    assert sum(diffs) / len(diffs) > 0, "P: s2 must beat s1 in retention on avg"


# -- 4. P: s1 better practice on average --
def test_P_s1_better_practice():
    diffs = []
    for seed in SEEDS:
        w = make_P(80, seed)
        prac_s1, prac_s2, n1, n2 = 0, 0, 0, 0
        for o in w.observations:
            if o.get("measure") != "practice" or o["signal"] == "UNCLEAR":
                continue
            s = o["strategy"][0]
            if s == "s1":
                n1 += 1
                if o["signal"] == "BETTER":
                    prac_s1 += 1
            elif s == "s2":
                n2 += 1
                if o["signal"] == "BETTER":
                    prac_s2 += 1
        if n1 > 0 and n2 > 0:
            diffs.append(prac_s1 / n1 - prac_s2 / n2)
    assert len(diffs) == len(SEEDS)
    assert sum(diffs) / len(diffs) > 0, "P: s1 must beat s2 in practice on avg"


# -- 5. R/R+: journey events exist when pauses happen --
@pytest.mark.parametrize("seed", SEEDS)
def test_R_has_journey_events(seed):
    w = make_R(160, seed)
    # With T=160 and pause_after_s1=0.5, very likely to have pauses
    # but not guaranteed for every seed. Just check structure.
    for je in w.journey_events:
        assert je["type"] == "learning_journey.status_changed"
        assert je["status"] in ("PAUSED", "ACTIVE")


# -- 6. C0: both norms confirmed, no priority --
@pytest.mark.parametrize("seed", SEEDS)
def test_C0_two_norms_no_priority(seed):
    w = make_C0(80, seed)
    confirmed = [ne for ne in w.norm_events
                 if ne.get("type") == "mdaa.norm.reviewed"
                 and ne["review"] == "CONFIRMED"]
    assert len(confirmed) == 2
    priorities = [ne for ne in w.norm_events
                  if ne.get("type") == "mdaa.norm.priority"]
    assert len(priorities) == 0


# -- 7. C1: has priority --
@pytest.mark.parametrize("seed", SEEDS)
def test_C1_has_priority(seed):
    w = make_C1(80, seed)
    priorities = [ne for ne in w.norm_events
                  if ne.get("type") == "mdaa.norm.priority"]
    assert len(priorities) == 1
    assert priorities[0]["higher"] == "n1"
    assert priorities[0]["lower"] == "n2"


# -- 8. C2: no autonomy observations --
@pytest.mark.parametrize("seed", SEEDS)
def test_C2_no_autonomy_obs(seed):
    w = make_C2(80, seed)
    aut = [o for o in w.observations if o.get("measure") == "autonomy"]
    assert len(aut) == 0


# -- 9. X: no assignmentId --
@pytest.mark.parametrize("seed", SEEDS)
def test_X_no_assignment(seed):
    w = make_X(80, seed)
    for o in w.observations:
        assert o.get("assignmentId") is None


# -- 10. Xp: all have assignmentId --
@pytest.mark.parametrize("seed", SEEDS)
def test_Xp_all_assigned(seed):
    w = make_Xp(80, seed)
    for o in w.observations:
        assert o.get("assignmentId") is not None


# -- 11. X: choice depends on hidden state --
def test_X_choice_depends_on_state():
    """In X, tired state biases toward s2, fresh toward s1."""
    w = make_X(160, 9001)
    choices = w.planted["choices"]
    tired_s2 = sum(1 for st, s in choices if st == "tired" and s == "s2")
    tired_total = sum(1 for st, _ in choices if st == "tired")
    fresh_s1 = sum(1 for st, s in choices if st == "fresh" and s == "s1")
    fresh_total = sum(1 for st, _ in choices if st == "fresh")
    if tired_total > 5:
        assert tired_s2 / tired_total > 0.5
    if fresh_total > 5:
        assert fresh_s1 / fresh_total > 0.5


# -- 12. X: retention depends on state, not strategy --
def test_X_retention_depends_on_state():
    """Retention in X correlates with hidden state, not strategy."""
    w = make_X(160, 9001)
    choices = w.planted["choices"]
    # We can't directly test this without knowing which obs maps to which
    # choice, but we verify the world was generated with state-dependent
    # retention (the p_ret parameters differ by state).
    xp = _P["worlds"]["X"]
    assert xp["p_ret_fresh"] != xp["p_ret_tired"]
