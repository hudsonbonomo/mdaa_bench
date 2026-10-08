"""Structural tests for the adaptive bench. Seeds 7001-7005 ONLY.
Tests structural assertions, block alternation, V schedule, R single act,
reader shapes, replay_check basics. No prediction metrics. Ordem §7a.
"""
import math
import os
import pytest

from adaptive.worlds import (WORLDS, AdaptiveWorld, load_policy,
                              make_world, make_world_s, make_world_n,
                              make_world_k, make_world_v, make_world_r,
                              c1_blocks, condition_at)
from adaptive.readers import read, read_returns, READERS
from adaptive.replay_check import reproduces, without_one_return

SEEDS = (7001, 7002, 7003, 7004, 7005)
_P = load_policy()
_L = int(_P["stream"]["block_length"])
_W0 = int(_P["declared"]["warrant_window"])
_TARGET = str(_P["stream"]["target"])
_KEY = str(_P["stream"]["key"])
TS = tuple(_P["T"])

# -- 1. structural assertions exist in the generators --
@pytest.mark.parametrize("fn,needle", [
    (make_world_s, "extending_is_correct"),
    (make_world_n, "planted p="),
    (make_world_k, "tau must be T/2"),
    (make_world_v, "rename schedule"),
    (make_world_v, "reconciliation"),
    (make_world_r, "redeclaration act"),
])
def test_structural_condition_is_asserted(fn, needle):
    import inspect
    src = inspect.getsource(fn)
    assert "assert" in src, f"{fn.__name__}: no assert found"
    assert any(needle in ln for ln in src.splitlines()), \
        f"{fn.__name__}: no assert mentioning {needle!r}"

# -- 2. every world builds without firing its assertions --
@pytest.mark.parametrize("T", TS)
@pytest.mark.parametrize("seed", SEEDS)
def test_every_world_builds(T, seed):
    for name in WORLDS:
        w = make_world(name, T=T, seed=seed)
        assert isinstance(w, AdaptiveWorld)
        assert len(w.observations) == T

# -- 3. block alternation c1/c2 --
@pytest.mark.parametrize("T", TS)
def test_block_alternation(T):
    w = make_world("S", T=T, seed=SEEDS[0])
    for t in range(T):
        o = w.observations[t]
        expected = _TARGET if (t // _L) % 2 == 0 else "c2"
        key = list(o["conditions"].keys())[0]
        assert o["conditions"][key] == expected, f"t={t}"

# -- 4. world-specific structural properties --
def test_s_p_invariant():
    for T in TS:
        w = make_world("S", T=T, seed=SEEDS[0])
        assert w.planted["planted"] == "extending_is_correct"

def test_n_planted_schedule():
    """N: p of j-th c1 block is p_hi if floor(j/4)%2==0 else p_lo."""
    for T in TS:
        w = make_world("N", T=T, seed=SEEDS[1])
        p_hi = float(_P["worlds"]["N"]["p_hi"])
        p_lo = float(_P["worlds"]["N"]["p_lo"])
        ps = w.planted["p_schedule"]
        for j in range(len(ps)):
            expected = p_hi if math.floor(j / 4) % 2 == 0 else p_lo
            assert ps[j] == expected, f"block {j}: {ps[j]} != {expected}"

def test_n_regime_switch():
    w = make_world("N", T=640, seed=SEEDS[1])
    assert "p_schedule" in w.planted

def test_k_single_step():
    for T in TS:
        w = make_world("K", T=T, seed=SEEDS[2])
        assert w.planted["tau"] == T // 2

def test_v_schedule():
    w = make_world("V", T=640, seed=SEEDS[3])
    fr = int(_P["worlds"]["V"]["first_rename"])
    re = int(_P["worlds"]["V"]["rename_every"])
    ra = int(_P["worlds"]["V"]["reconcile_after"])
    renames = [e for e in w.vocabulary_events if e["kind"] == "KEY_RENAMED"]
    expected = list(range(fr, 640, re))
    assert [e["seq"] for e in renames] == expected
    recons = [e for e in w.vocabulary_events if e["kind"] == "RECONCILED"]
    for i, r in enumerate(recons):
        assert r["seq"] == expected[i] + ra

def test_v_key_names_increment():
    w = make_world("V", T=640, seed=SEEDS[3])
    renames = [e for e in w.vocabulary_events if e["kind"] == "KEY_RENAMED"]
    assert renames[0]["from"] == _KEY and renames[0]["to"] == f"{_KEY}_2"

def test_r_single_redeclaration():
    for T in TS:
        w = make_world("R", T=T, seed=SEEDS[4])
        assert len(w.declarations) == 2
        assert w.declarations[0] == {"seq": 0, "window": _W0, "by": "person"}
        d1 = w.declarations[1]
        assert d1["seq"] == T // 2 and d1["by"] == "person"

# -- 5. declarations and condition shape --
@pytest.mark.parametrize("name", WORLDS)
def test_initial_declaration(name):
    w = make_world(name, T=TS[0], seed=SEEDS[0])
    assert w.declarations[0] == {"seq": 0, "window": _W0, "by": "person"}

@pytest.mark.parametrize("name", ["S", "N", "K", "R"])
def test_condition_is_target(name):
    w = make_world(name, T=TS[0], seed=SEEDS[0])
    assert _TARGET in w.condition.values()

# -- 6. c1_blocks and condition_at --
def test_c1_blocks_count():
    w = make_world("S", T=320, seed=SEEDS[0])
    blocks = c1_blocks(w)
    expected = 320 // (2 * _L)  # half the blocks are c1
    assert len(blocks) == expected
    for a, b in blocks:
        assert b - a == _L - 1

def test_block_integrity_common():
    """Common assert: no event/declaration inside a c1 block;
    starts c1, ends c2."""
    for name in WORLDS:
        w = make_world(name, T=320, seed=SEEDS[0])
        blocks = c1_blocks(w)
        assert blocks[0][0] == 0  # starts with c1
        last = w.observations[-1]
        lk = list(last["conditions"].keys())[0]
        assert last["conditions"][lk] != _TARGET  # ends with c2
        for a, b in blocks:
            for d in w.declarations:
                assert not (a < d["seq"] <= b)
            for e in w.vocabulary_events:
                assert not (a < e["seq"] <= b)

def test_condition_at_v():
    """condition_at in V changes at each rename."""
    w = make_world("V", T=640, seed=SEEDS[3])
    kn = w.planted["key_names"]
    renames = w.planted["renames"]
    c0 = condition_at(w, 0)
    assert c0 == {kn[0]: _TARGET}
    if renames:
        c_after = condition_at(w, renames[0] + 1)
        assert c_after == {kn[1]: _TARGET}

# -- 7. readers return well-formed readings (requires plugin) --
@pytest.mark.parametrize("reader", READERS)
def test_reader_returns_valid_dict(reader):
    w = make_world("S", T=TS[0], seed=SEEDS[0])
    result = read(reader, w, k=3)
    assert isinstance(result, dict)
    assert result["state"] in ("DECLARED", "ADJUSTED", "SUSPENDED")
    assert isinstance(result["window"], (int, float))
    assert isinstance(result["adjustments"], list)

# -- 8. read_returns returns one reading per block --
def test_read_returns_one_per_block():
    w = make_world("S", T=320, seed=SEEDS[0])
    readings = read_returns("R_declared", w, k=3)
    blocks = c1_blocks(w)
    assert len(readings) == len(blocks)

# -- 9. replay_check reproduces R_declared, fails without a return --
def test_replay_reproduces_declared():
    w = make_world("S", T=640, seed=SEEDS[0])
    result = read("R_declared", w, k=3)
    adjs = result.get("adjustments", [])
    if not adjs:
        pytest.skip("No adjustments found with this seed")
    assert reproduces("R_declared", w, adjs[0], k=3)

def test_replay_fails_without_one_return():
    w = make_world("S", T=640, seed=SEEDS[0])
    result = read("R_declared", w, k=3)
    adjs = result.get("adjustments", [])
    if not adjs:
        pytest.skip("No adjustments found with this seed")
    assert not reproduces("R_declared", w, without_one_return(adjs[0]), k=3)
