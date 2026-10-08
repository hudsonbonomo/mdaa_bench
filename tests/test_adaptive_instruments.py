"""Instruments verified on deterministic flow (no randomness). Ordem §7b.
World S seed 7001, T=640, all c1 signals replaced with BETTER. k=3.
World V seed 7001, T=320, all c1 signals replaced with BETTER. k=3.
Seeds 7001-7005 ONLY. Numbers hand-verified against the plugin.
CRITICAL: if any number doesn't match, DO NOT adjust -- STOP and report.
"""
import dataclasses
import pytest

from adaptive.worlds import make_world, c1_blocks, condition_at, load_policy
from adaptive.readers import read, read_returns, make_rule
from adaptive.reader_mix import R_mix
from adaptive.replay_check import (reproduces, without_one_return,
                                    _named_observations, _call_replay)

_P = load_policy()
_W0 = int(_P["declared"]["warrant_window"])
_TARGET = str(_P["stream"]["target"])


def _all_better(w):
    """Replace all c1 signals with BETTER."""
    new_obs = []
    for o in w.observations:
        key = list(o["conditions"].keys())[0]
        if o["conditions"][key] == _TARGET:
            o2 = dict(o)
            o2["signal"] = "BETTER"
            new_obs.append(o2)
        else:
            new_obs.append(o)
    return dataclasses.replace(w, observations=new_obs)


# ---- World S, seed 7001, T=640, all c1 -> BETTER, k=3 ----

class TestWorldS:
    @pytest.fixture(scope="class")
    def world(self):
        w = make_world("S", T=640, seed=7001)
        return _all_better(w)

    def test_r_declared_12_adjustments(self, world):
        result = read("R_declared", world, k=3)
        adjs = result.get("adjustments", [])
        assert len(adjs) == 12

    def test_r_declared_final_window_160(self, world):
        result = read("R_declared", world, k=3)
        assert result["window"] == 160

    def test_r_declared_reason_matches(self, world):
        result = read("R_declared", world, k=3)
        assert "declared maximum 160" in result["reason"]

    def test_r_declared_verifier_reproduces_all(self, world):
        result = read("R_declared", world, k=3)
        adjs = result.get("adjustments", [])
        for i, a in enumerate(adjs):
            assert reproduces("R_declared", world, a, k=3), \
                f"adj {i} does not reproduce"

    def test_r_declared_tampered_fails_all(self, world):
        result = read("R_declared", world, k=3)
        adjs = result.get("adjustments", [])
        for i, a in enumerate(adjs):
            tampered = without_one_return(a)
            assert not reproduces("R_declared", world, tampered, k=3), \
                f"adj {i} reproduces even without one return"

    def test_r_fixed_window_always_40(self, world):
        readings = read_returns("R_fixed", world, k=3)
        for i, r in enumerate(readings):
            assert r["window"] == 40, \
                f"block {i}: window={r['window']}"

    def test_r_fixed_no_adjustments(self, world):
        readings = read_returns("R_fixed", world, k=3)
        last = readings[-1]
        assert len(last.get("adjustments", [])) == 0

    def test_r_fixed_lastreturn_not_null(self, world):
        readings = read_returns("R_fixed", world, k=3)
        has_lr = any(r.get("lastReturn") is not None for r in readings)
        assert has_lr, "R_fixed lastReturn never non-null"

    def test_r_mix_4_triggers(self, world):
        result = R_mix(world, k=3)
        triggers = result.get("triggers", [])
        assert len(triggers) == 4

    def test_r_mix_sequence(self, world):
        result = R_mix(world, k=3)
        triggers = result.get("triggers", [])
        seq = [triggers[0]["from"]] + [t["to"] for t in triggers]
        assert seq == [40, 70, 110, 150, 160]

    def test_r_mix_only_last_truncated(self, world):
        result = R_mix(world, k=3)
        triggers = result.get("triggers", [])
        trunc = [t["truncated"] for t in triggers]
        assert trunc == [False, False, False, True]

    def test_r_mix_verifier(self, world):
        result = R_mix(world, k=3)
        triggers = result.get("triggers", [])
        repro = [reproduces("R_mix", world, t, k=3) for t in triggers]
        assert repro == [True, False, False, True]

    def test_r_simple_12_adjustments_reproduced(self, world):
        """Step 1: R_simple makes 12 adj, verifier reproduces 12/12."""
        result = read("R_simple", world, k=3)
        adjs = result.get("adjustments", [])
        assert len(adjs) == 12
        for i, a in enumerate(adjs):
            assert reproduces("R_simple", world, a, k=3), \
                f"adj {i} does not reproduce with own rule"

    def test_r_simple_wrong_threshold_zero(self, world):
        """Step 1: threshold=3 reproduces 0/12 (the defect this fixes)."""
        result = read("R_simple", world, k=3)
        adjs = result.get("adjustments", [])
        assert len(adjs) == 12
        wrong_rule = make_rule(k=3)
        for a in adjs:
            named = _named_observations(world, a)
            r = _call_replay(a, named, wrong_rule)
            assert r.get("window") != a.get("to"), \
                "should NOT reproduce with threshold=3"

    def test_read_returns_one_per_block(self, world):
        readings = read_returns("R_declared", world, k=3)
        blocks = c1_blocks(world)
        assert len(readings) == len(blocks)


# ---- World V, seed 7001, T=320, all c1 -> BETTER, k=3 ----

class TestWorldV:
    @pytest.fixture(scope="class")
    def world(self):
        w = make_world("V", T=320, seed=7001)
        return _all_better(w)

    @pytest.fixture(scope="class")
    def planted(self, world):
        return world.planted

    def test_r_declared_no_adj_after_rename(self, world, planted):
        fr = planted["first_rename"]
        readings = read_returns("R_declared", world, k=3)
        last = readings[-1]
        after = [a for a in last.get("adjustments", [])
                 if a.get("seq", 0) > fr]
        assert len(after) == 0

    def test_r_cross_adjusts_after_rename(self, world, planted):
        fr = planted["first_rename"]
        readings = read_returns("R_cross", world, k=3)
        last = readings[-1]
        after = [a for a in last.get("adjustments", [])
                 if a.get("seq", 0) > fr]
        assert len(after) >= 1

    def test_r_cross_exactly_2_adj_after_rename(self, world, planted):
        """Step 2: R_cross has exactly 2 adj after first rename (not 12)."""
        fr = planted["first_rename"]
        readings = read_returns("R_cross", world, k=3)
        last = readings[-1]
        after = [a for a in last.get("adjustments", [])
                 if a.get("seq", 0) > fr]
        assert len(after) == 2

    def test_suspended_between_rename_recon(self, world, planted):
        pairs = planted.get("rename_recon_pairs", [])
        blocks = c1_blocks(world)
        readings = read_returns("R_declared", world, k=3)
        for i, rdg in enumerate(readings):
            if i < len(blocks):
                ns = blocks[i][1] + 1
                for ren, rec in pairs:
                    if ren < ns <= rec:
                        assert rdg["state"] == "SUSPENDED", \
                            f"block {i} (nowSeq={ns}): not SUSPENDED"
                        assert rdg["window"] == _W0, \
                            f"block {i}: window={rdg['window']}"
