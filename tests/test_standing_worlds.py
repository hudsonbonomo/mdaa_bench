"""The standing worlds: each world is the world it claims to be, and it says so at
construction. PREREGISTRO_v1 §3 and §10 — the structural condition is ASSERTED in the
generator, never inferred from the absence of divergence downstream.

Test seeds only: 9001 (A), 9002 (B), 9003 (C), 9004 (D). Seeds 1-20 are the grid and
901-905 the pilot; neither is touched here. Replicas are not a factor of generation.
"""
import inspect
import os

import pytest

from standing import worlds as W
from standing.worlds import (MAPPED_VALUES, NOISE_UNCLEAR, SIGNALS, STRATEGY,
                             load_alpha, make_world)
from standing.readers import R_current, R_decay, R_declared, ReadingResult

SEED = {"A": 9001, "B": 9002, "C": 9003, "D": 9004}
TS = (40, 160)


def _w(world, T, **kw):
    return make_world(world, T=T, seed=SEED[world], **kw)


# --------------------------------------------------------------------------- #
# 1. the structural assertions exist, in code, and the worlds satisfy them      #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("fn,needle", [
    (W.make_world_a, "monotonicity"),
    (W.make_world_b, "block alternation"),
    (W.make_world_c, "ramp detected"),
    (W.make_world_d, "exactly one rename"),
    (W.make_world_d, "at most one reconciliation"),
])
def test_structural_condition_is_asserted_in_the_generator(fn, needle):
    src = inspect.getsource(fn)
    lines = [ln.strip() for ln in src.splitlines() if "assert" in ln or needle in ln]
    assert any(needle in ln for ln in lines), f"{fn.__name__}: no assert mentioning {needle!r}"
    assert "assert" in src


@pytest.mark.parametrize("T", TS)
def test_every_world_builds_without_firing_its_assertions(T):
    for world, kw in [("A", {}), ("B", {"logged": True}), ("B", {"logged": False}),
                      ("C", {}), ("D", {})]:
        w = _w(world, T, **kw)
        assert len(w.observations) == T, (world, T, len(w.observations))


def test_a_schedule_is_non_increasing_from_080_to_035():
    for T in TS:
        p = _w("A", T).params["p_schedule"]
        assert p[0] == 0.80 and p[-1] == 0.35
        assert all(p[t] >= p[t + 1] for t in range(T - 1))


def test_b_alternates_in_exact_blocks_of_T_over_4():
    for T in TS:
        w = _w("B", T, logged=True)
        block = w.params["block"]
        assert block == T // 4
        true_cond = [w.planted[t]["true_condition"] for t in range(T)]
        blocks = [true_cond[i * block:(i + 1) * block] for i in range(4)]
        assert [set(b).pop() for b in blocks] == ["c1", "c2", "c1", "c2"]
        assert all(len(set(b)) == 1 and len(b) == block for b in blocks)


def test_c_is_a_single_step_at_tau_with_no_ramp():
    for T in TS:
        w = _w("C", T)
        tau, p = w.params["tau"], w.params["p_schedule"]
        assert tau == T // 2
        assert set(p[:tau]) == {0.80} and set(p[tau:]) == {0.25}


def test_d_has_one_rename_at_tau1_and_at_most_one_reconciliation_at_tau2():
    for T in TS:
        for forced in (None, "none", "total", "partial"):
            w = _w("D", T, force_reconciliation=forced)
            ren = [e for e in w.vocabulary_events if e["type"] == "rename"]
            rec = [e for e in w.vocabulary_events if e["type"] == "reconciliation"]
            assert len(ren) == 1 and ren[0]["t"] == T // 3 == w.params["tau1"]
            assert len(rec) <= 1 and all(e["t"] == 2 * T // 3 for e in rec)


# --------------------------------------------------------------------------- #
# 2. the planted state, per record                                             #
# --------------------------------------------------------------------------- #

def test_a_plants_aged_or_applicable_on_every_record():
    w = _w("A", 40)
    assert all(w.planted[t]["planted_state"] == "aged_or_applicable" for t in range(40))
    assert all("p_better" in w.planted[t] for t in range(40))


def test_b_logged_plants_applicable_or_out_of_scope_by_condition():
    w = _w("B", 40, logged=True)
    cur = w.params["current_condition"]
    for t in range(40):
        want = "applicable" if w.planted[t]["true_condition"] == cur else "out_of_scope"
        assert w.planted[t]["planted_state"] == want, t
    assert {w.planted[t]["planted_state"] for t in range(40)} == {"applicable", "out_of_scope"}


def test_b_unlogged_is_indeterminate_by_construction():
    w = _w("B", 40, logged=False)
    assert all(w.planted[t]["planted_state"] is None for t in range(40))
    assert w.params["indeterminate_by_construction"] is True
    assert {o.conditions["env"] for o in w.observations} == {"c1"}


def test_c_plants_applicable_everywhere_read_as_B_with_order():
    for T in TS:
        w = _w("C", T)
        assert all(w.planted[t]["planted_state"] == "applicable" for t in range(T))
        assert all(w.planted[t]["correct_reading"] == "B_with_order" for t in range(T))
        assert not any(w.planted[t]["planted_state"] == "aged" for t in range(T))


@pytest.mark.parametrize("forced,pre_states", [
    ("none", {"unevaluable"}),
    ("total", {"applicable"}),
    ("partial", {"applicable", "out_of_scope"}),
])
def test_d_covers_all_three_branches_by_parameter(forced, pre_states):
    T = 40
    w = _w("D", T, force_reconciliation=forced)
    tau1 = w.params["tau1"]
    assert w.params["reconciliation"] == (None if forced == "none" else forced)
    pre = {w.planted[t]["planted_state"] for t in range(tau1)}
    assert pre <= pre_states and pre, (forced, pre)
    assert all(w.planted[t]["state_between_tau1_tau2"] == "unevaluable" for t in range(tau1))
    assert all(w.planted[t]["planted_state"] == "applicable" for t in range(tau1, T))
    if forced == "partial":
        for t in range(tau1):
            want = "applicable" if w.planted[t]["regime"] in MAPPED_VALUES else "out_of_scope"
            assert w.planted[t]["planted_state"] == want, t


# --------------------------------------------------------------------------- #
# 3. noise comes from the frozen file, and shows up in the flow                 #
# --------------------------------------------------------------------------- #

def test_noise_is_read_from_alpha_frozen_not_hardcoded():
    assert NOISE_UNCLEAR == float(load_alpha()["signal_noise_unclear"]) == 0.15
    for fn in (W.make_world_a, W.make_world_b, W.make_world_c, W.make_world_d):
        default = inspect.signature(fn).parameters["noise_unclear"].default
        assert default == NOISE_UNCLEAR, fn.__name__


@pytest.mark.parametrize("world,kw", [("A", {}), ("B", {"logged": True}),
                                      ("C", {}), ("D", {})])
def test_unclear_fraction_is_near_the_frozen_noise(world, kw):
    w = _w(world, 160, **kw)
    frac = sum(o.signal == "UNCLEAR" for o in w.observations) / 160
    assert abs(frac - NOISE_UNCLEAR) < 0.10, (world, frac)
    assert all(o.signal in SIGNALS and o.strategy == STRATEGY for o in w.observations)


# --------------------------------------------------------------------------- #
# 4. the three readers take the same flow and give back the same shape          #
# --------------------------------------------------------------------------- #

def _check_shape(r, T):
    assert isinstance(r, ReadingResult)
    assert len(r.verdicts) == T and all(isinstance(v, str) for v in r.verdicts.values())
    assert r.strategy is None or r.strategy == STRATEGY
    assert sum(r.summary.values()) == T


@pytest.mark.parametrize("reader", [R_decay, R_current])
def test_pure_python_readers_share_the_reading_result_form(reader):
    w = _w("A", 40)
    _check_shape(reader(w), 40)


def test_r_declared_needs_the_plugin_dist():
    if not os.environ.get("MDAA_PLUGIN_DIST"):
        with pytest.raises(EnvironmentError):
            R_declared(_w("A", 40))
        pytest.skip("MDAA_PLUGIN_DIST not set")
    _check_shape(R_declared(_w("A", 40)), 40)
