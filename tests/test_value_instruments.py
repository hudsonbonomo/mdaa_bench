"""Instrument tests for value bench controls (Paper 7). Seeds 9001-9004.
Each control, on a hand-written fixture, gives the answer the design says.
"""
import pytest
from value.worlds import ValueWorld
from value.controls import R_reward, R_infer_value, R_scalar, R_naive
from value.world_utils import make_obs


def _fixture_P():
    """Hand-written: s1 better in practice, s2 better in retention."""
    obs = []
    # s1: 8 BETTER practice, 2 BETTER retention (out of 10 each)
    for i in range(10):
        sig_p = "BETTER" if i < 8 else "WORSE"
        sig_r = "BETTER" if i < 2 else "WORSE"
        obs.append(make_obs(i * 4, sig_p, "s1", "practice", f"a-{i}"))
        obs.append(make_obs(i * 4 + 1, sig_r, "s1", "retention", f"a-{i}"))
    # s2: 3 BETTER practice, 7 BETTER retention (out of 10 each)
    for i in range(10):
        sig_p = "BETTER" if i < 3 else "WORSE"
        sig_r = "BETTER" if i < 7 else "WORSE"
        obs.append(make_obs(40 + i * 4, sig_p, "s2", "practice", f"b-{i}"))
        obs.append(make_obs(40 + i * 4 + 1, sig_r, "s2", "retention", f"b-{i}"))
    return ValueWorld(obs, [], [], [], {"world": "P"}, {})


def _fixture_C():
    """Hand-written: s1 better autonomy, s2 better retention."""
    obs = []
    for i in range(10):
        obs.append(make_obs(i * 4, "BETTER" if i < 3 else "WORSE",
                            "s1", "retention", f"a-{i}"))
        obs.append(make_obs(i * 4 + 1, "BETTER" if i < 8 else "WORSE",
                            "s1", "autonomy", f"a-{i}"))
    for i in range(10):
        obs.append(make_obs(40 + i * 4, "BETTER" if i < 7 else "WORSE",
                            "s2", "retention", f"b-{i}"))
        obs.append(make_obs(40 + i * 4 + 1, "BETTER" if i < 2 else "WORSE",
                            "s2", "autonomy", f"b-{i}"))
    return ValueWorld(obs, [], [], [], {"world": "C"}, {})


def _fixture_X():
    """Hand-written: confounded. s2 obs have worse retention, no assignmentId."""
    obs = []
    for i in range(20):
        s = "s1" if i < 10 else "s2"
        sig = "BETTER" if (s == "s1" and i < 7) or (s == "s2" and i < 12) else "WORSE"
        obs.append(make_obs(i, sig, s, "retention", None))
    return ValueWorld(obs, [], [], [], {"world": "X"}, {})


# --- R_reward: elects by practice, always s1 in fixture_P ---
class TestRReward:
    def test_elects_s1_in_P(self):
        w = _fixture_P()
        r = R_reward(w)
        assert r["elected"] == "s1"
        assert r["rates"]["s1"] > r["rates"]["s2"]

    def test_always_judges(self):
        w = _fixture_P()
        r = R_reward(w)
        assert r["state"] == "JUDGED"


# --- R_infer_value: value = BETTER(practice) / seq consumed ---
class TestRInferValue:
    def test_elects_based_on_value(self):
        w = _fixture_P()
        r = R_infer_value(w)
        # s1 has 8 BETTER in practice, seq 0..39 -> value = 8/40 = 0.2
        # s2 has 3 BETTER in practice, seq 40..79 -> value = 3/40 = 0.075
        assert r["elected"] == "s1"
        assert r["values"]["s1"] > r["values"]["s2"]


# --- R_scalar: equal-weight sum of retention + autonomy ---
class TestRScalar:
    def test_elects_in_conflict(self):
        w = _fixture_C()
        r = R_scalar(w)
        # s1: ret=0.3, aut=0.8 -> mean=0.55
        # s2: ret=0.7, aut=0.2 -> mean=0.45
        assert r["elected"] == "s1"

    def test_scores(self):
        w = _fixture_C()
        r = R_scalar(w)
        assert abs(r["scores"]["s1"] - 0.55) < 0.01
        assert abs(r["scores"]["s2"] - 0.45) < 0.01


# --- R_naive: compares retention without assignmentId check ---
class TestRNaive:
    def test_justifies_in_P(self):
        """s2 has 0.7 retention, s1 has 0.2. diff=0.5 >= margin=0.15."""
        w = _fixture_P()
        r = R_naive(w)
        assert r["justified"] is True
        assert r["elected"] == "s2"

    def test_justifies_without_assignment(self):
        """X fixture: no assignmentId, but R_naive still compares."""
        w = _fixture_X()
        r = R_naive(w)
        # s1: 7/10=0.7, s2: 2/10=0.2, diff=0.5 >= 0.15
        assert r["justified"] is True
        assert r["elected"] == "s1"

    def test_diff_below_margin_not_justified(self):
        """When rates are close, not justified."""
        obs = []
        for i in range(10):
            obs.append(make_obs(i, "BETTER" if i < 5 else "WORSE",
                                "s1", "retention", f"a-{i}"))
        for i in range(10):
            obs.append(make_obs(10 + i, "BETTER" if i < 5 else "WORSE",
                                "s2", "retention", f"b-{i}"))
        w = ValueWorld(obs, [], [], [], {}, {})
        r = R_naive(w)
        assert r["justified"] is False
        assert r["elected"] is None
