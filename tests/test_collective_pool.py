"""Unit + integration tests for R_pool_pop and apply_adjustment_rule.
E1 verification: Python reimplementation must match plugin exactly.

Unit tests use hand-crafted fold data (no plugin needed).
Integration tests require MDAA_PLUGIN_DIST (skipped without it).
"""
import os
import pytest
from collective.controls import (
    R_pool_pop, apply_adjustment_rule, _collect_returns,
)

_RULE = {"threshold": 3, "step": 10, "minWindow": 20, "maxWindow": 160}


def _fold(seq, kind):
    return {"window": 40, "lastReturn": {"seq": seq, "kind": kind},
            "adjustments": []}


# -- Unit: _collect_returns --

class TestCollectReturns:
    def test_merges_and_sorts_by_seq(self):
        pf = [[_fold(30, "COUNTED")], [_fold(10, "COUNTED")],
              [_fold(20, "NEUTRAL")]]
        ret = _collect_returns(pf)
        assert [r["seq"] for r in ret] == [10, 20, 30]

    def test_dedup_same_seq(self):
        pf = [[_fold(10, "COUNTED"), _fold(10, "COUNTED")]]
        assert len(_collect_returns(pf)) == 1

    def test_skips_none_lastReturn(self):
        pf = [[{"window": 40, "lastReturn": None, "adjustments": []}]]
        assert _collect_returns(pf) == []


# -- Unit: apply_adjustment_rule --

class TestApplyAdjustmentRule:
    def test_three_counted_fires(self):
        """3 COUNTED -> window grows once."""
        rets = [{"seq": i, "kind": "COUNTED"} for i in range(3)]
        r = apply_adjustment_rule(rets, _RULE, w0=20)
        assert r["window"] == 30
        assert r["adjustments"] == 1

    def test_six_counted_fires_twice(self):
        """6 COUNTED -> window grows twice."""
        rets = [{"seq": i, "kind": "COUNTED"} for i in range(6)]
        r = apply_adjustment_rule(rets, _RULE, w0=20)
        assert r["window"] == 40
        assert r["adjustments"] == 2

    def test_conflict_resets(self):
        """COUNTED x2, CONFLICT, COUNTED x2 -> no fire (run never hits 3)."""
        kinds = ["COUNTED", "COUNTED", "CONFLICT", "COUNTED", "COUNTED"]
        rets = [{"seq": i, "kind": k} for i, k in enumerate(kinds)]
        r = apply_adjustment_rule(rets, _RULE, w0=20)
        assert r["window"] == 20

    def test_contradicted_resets(self):
        kinds = ["COUNTED", "COUNTED", "CONTRADICTED", "COUNTED", "COUNTED"]
        rets = [{"seq": i, "kind": k} for i, k in enumerate(kinds)]
        r = apply_adjustment_rule(rets, _RULE, w0=20)
        assert r["window"] == 20

    def test_neutral_preserves_run(self):
        """COUNTED, NEUTRAL, COUNTED, COUNTED -> fires."""
        kinds = ["COUNTED", "NEUTRAL", "COUNTED", "COUNTED"]
        rets = [{"seq": i, "kind": k} for i, k in enumerate(kinds)]
        r = apply_adjustment_rule(rets, _RULE, w0=20)
        assert r["window"] == 30

    def test_max_window_cap(self):
        """Many COUNTED should not exceed maxWindow."""
        rets = [{"seq": i, "kind": "COUNTED"} for i in range(100)]
        r = apply_adjustment_rule(rets, _RULE, w0=20)
        assert r["window"] == 160

    def test_empty_returns(self):
        r = apply_adjustment_rule([], _RULE, w0=20)
        assert r["window"] == 20
        assert r["adjustments"] == 0


# -- Unit: R_pool_pop --

class TestRPoolPop:
    def test_counts_from_lastReturn_kind(self):
        pf = [[_fold(10, "COUNTED"), _fold(20, "COUNTED")],
              [_fold(30, "NEUTRAL"), _fold(40, "COUNTED")],
              [{"window": 40, "lastReturn": None, "adjustments": []}]]
        assert R_pool_pop(pf, _RULE)["counted_returns"] == 3

    def test_window_grows_after_threshold(self):
        pf = [[_fold(10, "COUNTED")],
              [_fold(20, "COUNTED")],
              [_fold(30, "COUNTED")]]
        r = R_pool_pop(pf, _RULE, w0=20)
        assert r["window"] == 30
        assert r["adjustments"] == 1

    def test_multi_person_merge_by_seq(self):
        pf = [[_fold(10, "COUNTED"), _fold(30, "COUNTED")],
              [_fold(20, "COUNTED")]]
        r = R_pool_pop(pf, _RULE, w0=20)
        assert r["window"] == 30

    def test_empty_folds(self):
        r = R_pool_pop([], _RULE)
        assert r["window"] is None


# -- Integration: Python rule matches plugin for one person --

_need_plugin = pytest.mark.skipif(
    not os.environ.get("MDAA_PLUGIN_DIST"),
    reason="MDAA_PLUGIN_DIST not set")

SEEDS = (9001, 9002, 9003, 9004)


@_need_plugin
@pytest.mark.parametrize("seed", SEEDS)
def test_python_rule_matches_plugin_per_person(seed):
    """For each person in Pc n=5 T=320, apply_adjustment_rule on
    that person's returns must give the same final window as the
    plugin fold. This validates E1."""
    from collective.worlds_pop import make_Pc
    from collective.readers import read_own_folds
    from adaptive.worlds import load_policy as load_ap
    ap = load_ap()
    rule = {"threshold": 3, "step": int(ap["rule"]["step"]),
            "minWindow": int(ap["rule"]["min_window"]),
            "maxWindow": int(ap["rule"]["max_window"])}
    w0 = int(ap["declared"]["warrant_window"])
    world = make_Pc(5, 320, seed)
    for i, pw in enumerate(world.person_worlds):
        folds = read_own_folds(pw, rule)
        if not folds:
            continue
        plugin_window = folds[-1].get("window")
        rets = _collect_returns([folds])
        py_result = apply_adjustment_rule(rets, rule, w0=w0)
        assert py_result["window"] == plugin_window, (
            f"seed={seed} person={i}: Python {py_result['window']} "
            f"!= plugin {plugin_window}")
