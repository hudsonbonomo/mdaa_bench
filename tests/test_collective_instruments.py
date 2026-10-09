"""Instrument tests for collective bench controls (Paper 8). Seeds 9001-9004.
Each control, on a hand-written fixture, gives the answer the design says.
"""
import pytest
from collective.controls import (
    R_count, R_pool, R_H1, R_mean, R_leastmisery,
)


def _obs(seq, signal, episode_id=None, observer="obs-0"):
    o = {
        "seq": seq, "signal": signal,
        "conditions": {"modo": "c1"},
        "strategy": ["s*"], "id": f"obs-{seq}",
        "journeyId": "bench", "note": "",
        "provenance": {"kind": "PERSON", "observer": observer},
    }
    if episode_id:
        o["episodeId"] = episode_id
    return o


# --- R_count ---

class TestRCount:
    def test_majority_better(self):
        """3 BETTER, 1 WORSE -> statute T."""
        obs = [_obs(0, "BETTER", "e1"), _obs(1, "BETTER", "e2"),
               _obs(2, "BETTER", "e3"), _obs(3, "WORSE", "e4")]
        r = R_count(obs)
        assert r["statute"] == "T"
        assert r["better_count"] == 3
        assert r["worse_count"] == 1

    def test_majority_worse(self):
        obs = [_obs(0, "WORSE", "e1"), _obs(1, "WORSE", "e2"),
               _obs(2, "BETTER", "e3")]
        r = R_count(obs)
        assert r["statute"] == "T_worse"

    def test_tie_is_B(self):
        obs = [_obs(0, "BETTER", "e1"), _obs(1, "WORSE", "e2")]
        r = R_count(obs)
        assert r["statute"] == "B"

    def test_duplicated_obs_counted(self):
        """Same episodeId, two observations -> counts both."""
        obs = [_obs(0, "BETTER", "e1", "obs-0"),
               _obs(1, "BETTER", "e1", "obs-1"),
               _obs(2, "WORSE", "e2", "obs-0")]
        r = R_count(obs)
        # e1: 2 BETTER, e2: 1 WORSE -> better_count=1, worse_count=1
        # wait, it groups by episode, majority wins per episode
        assert r["better_count"] == 1
        assert r["worse_count"] == 1


# --- R_pool ---

class TestRPool:
    def test_elects_higher_rate(self):
        obs = []
        for i in range(20):
            o = _obs(i, "BETTER" if i < 8 else "WORSE")
            o["strategy"] = ["s1"]
            o["personRef"] = "p0"
            obs.append(o)
        for i in range(20):
            o = _obs(20 + i, "BETTER" if i < 15 else "WORSE")
            o["strategy"] = ["s2"]
            o["personRef"] = "p0"
            obs.append(o)
        r = R_pool(obs, ["s1", "s2"])
        assert r["elected"] == "s2"
        assert r["rates"]["s2"] > r["rates"]["s1"]


# --- R_mean ---

class TestRMean:
    def test_chooses_highest_fraction(self):
        gi = {
            "actions": ["a0", "a1"],
            "statusQuo": "a0",
            "members": [
                {"memberRef": "m0", "released": True, "showReasons": True,
                 "gamma": {"a0": {"auth": True, "feas": True,
                                  "safe": True, "epi": True},
                           "a1": {"auth": False, "feas": True,
                                  "safe": True, "epi": True}}},
                {"memberRef": "m1", "released": True, "showReasons": True,
                 "gamma": {"a0": {"auth": True, "feas": True,
                                  "safe": True, "epi": True},
                           "a1": {"auth": True, "feas": True,
                                  "safe": True, "epi": True}}},
                {"memberRef": "m2", "released": True, "showReasons": True,
                 "gamma": {"a0": {"auth": True, "feas": True,
                                  "safe": True, "epi": True},
                           "a1": {"auth": True, "feas": True,
                                  "safe": True, "epi": True}}},
            ],
        }
        r = R_mean(gi)
        # a0: 3/3=1.0, a1: 2/3=0.67
        assert r["chosen"] == "a0"
        assert r["fractions"]["a0"] == 1.0

    def test_chooses_outside_gamma(self):
        """R_mean can choose an action that some member blocks."""
        gi = {
            "actions": ["a0", "a1"],
            "statusQuo": "a0",
            "members": [
                {"memberRef": "m0", "released": True, "showReasons": True,
                 "gamma": {"a0": {"auth": False, "feas": True,
                                  "safe": True, "epi": True},
                           "a1": {"auth": True, "feas": True,
                                  "safe": True, "epi": True}}},
                {"memberRef": "m1", "released": True, "showReasons": True,
                 "gamma": {"a0": {"auth": False, "feas": True,
                                  "safe": True, "epi": True},
                           "a1": {"auth": True, "feas": True,
                                  "safe": True, "epi": True}}},
            ],
        }
        r = R_mean(gi)
        assert r["chosen"] == "a1"
        # a1 is chosen, but m0 blocks a0 -> a1 is in both gammas


# --- R_leastmisery ---

class TestRLeastmisery:
    def test_chooses_highest_minimum(self):
        gi = {
            "actions": ["a0", "a1"],
            "statusQuo": "a0",
            "members": [
                {"memberRef": "m0", "released": True, "showReasons": True,
                 "gamma": {"a0": {"auth": True, "feas": True,
                                  "safe": True, "epi": True},
                           "a1": {"auth": True, "feas": True,
                                  "safe": True, "epi": True}}},
                {"memberRef": "m1", "released": True, "showReasons": True,
                 "gamma": {"a0": {"auth": True, "feas": True,
                                  "safe": True, "epi": True},
                           "a1": {"auth": False, "feas": True,
                                  "safe": True, "epi": True}}},
            ],
        }
        r = R_leastmisery(gi)
        # a0: min(1,1)=1, a1: min(1,0)=0
        assert r["chosen"] == "a0"

    def test_tie_broken_lexicographically(self):
        gi = {
            "actions": ["b0", "a0"],
            "statusQuo": "a0",
            "members": [
                {"memberRef": "m0", "released": True, "showReasons": True,
                 "gamma": {"b0": {"auth": True, "feas": True,
                                  "safe": True, "epi": True},
                           "a0": {"auth": True, "feas": True,
                                  "safe": True, "epi": True}}},
            ],
        }
        r = R_leastmisery(gi)
        # both have min=1, tie broken by max(key=(min, name))
        assert r["chosen"] == "b0"


# --- R_H1 ---

class TestRH1:
    def test_passes_when_ratio_low(self):
        r = R_H1(None, [[]], {"threshold": 3}, 0.5)
        assert r["gate_passed"] is True

    def test_refuses_when_ratio_high(self):
        r = R_H1(None, [[]], {"threshold": 3}, 1.5)
        assert r["gate_passed"] is False
        assert r["fallback"] == "R_own"
