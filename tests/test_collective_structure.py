"""Structural tests for the collective bench (Paper 8). Seeds 9001-9004.
Tests: every world builds, structural assertions hold, planted values correct.
"""
import numpy as np
import pytest

from collective.worlds import (
    WORLDS, CollectiveWorld, make_world, load_policy,
    make_O, make_Pn, make_G,
)
from collective.worlds_pop import make_Pc, make_Pl, make_Pw
from collective.gates import location_between_within

SEEDS = (9001, 9002, 9003, 9004)
_P = load_policy()


# -- 1. O world builds and has statute B planted --
@pytest.mark.parametrize("k", _P["O"]["k"])
@pytest.mark.parametrize("seed", SEEDS)
def test_O_builds(k, seed):
    w = make_O(k, seed)
    assert isinstance(w, CollectiveWorld)
    assert w.planted["planted"] == "statute_B"
    assert len(w.observations) > 0


# -- 2. O: inversion -- per obs s2 wins, per episode s1 wins --
@pytest.mark.parametrize("seed", SEEDS)
def test_O_inversion(seed):
    w = make_O(2, seed)
    inv = w.planted["inversion"]
    inv_obs = [o for o in w.observations if "inv-" in o.get("episodeId", "")]
    inv_s1 = [o for o in inv_obs if "inv-s1" in o["episodeId"]]
    inv_s2 = [o for o in inv_obs if "inv-s2" in o["episodeId"]]
    assert len(inv_s2) > len(inv_s1), "per obs s2 must have more"
    eps_s1 = {o["episodeId"] for o in inv_s1}
    eps_s2 = {o["episodeId"] for o in inv_s2}
    assert len(eps_s1) > len(eps_s2), "per episode s1 must have more"


# -- 3. Pn: person has no records, population exists --
@pytest.mark.parametrize("n", _P["Pn"]["n"])
@pytest.mark.parametrize("seed", SEEDS)
def test_Pn_no_records(n, seed):
    w = make_Pn(n, seed)
    assert len(w.observations) == 0, "Pn: person must have no records"
    assert w.planted["planted"] == "no_evidence"
    assert len(w.planted["population_obs"]) == n * _P["Pn"]["records_per_person"]
    assert set(w.planted["repertoire"]) == {"s1", "s2"}


# -- 4. Pop worlds build --
@pytest.mark.parametrize("seed", SEEDS)
def test_Pc_builds(seed):
    w = make_Pc(5, 320, seed)
    assert w.planted["planted"] == "extending_is_correct"
    assert len(w.person_worlds) == 5


@pytest.mark.parametrize("seed", SEEDS)
def test_Pl_builds(seed):
    w = make_Pl(5, 320, seed)
    assert w.planted["planted"] == "location_varies"
    assert len(w.planted["person_ps"]) == 5


@pytest.mark.parametrize("seed", SEEDS)
def test_Pw_builds(seed):
    w = make_Pw(5, 320, seed)
    assert w.planted["planted"] == "law_differs"
    assert w.planted["n_stable"] + w.planted["n_fast"] == 5


# -- 5. Pw: location ratio <= 1 on average (H1 passes) --
def test_Pw_H1_passes_on_average():
    """The location between/within ratio must be <= 1 on average of 4 seeds."""
    ratios = []
    for seed in SEEDS:
        w = make_Pw(5, 320, seed)
        ratios.append(w.planted["location_ratio"])
    mean_ratio = np.mean(ratios)
    assert mean_ratio <= 1.0, (
        f"Pw: mean location ratio {mean_ratio:.4f} > 1.0, H1 should pass")


# -- 6. Pw: extend_correct differs between subgroups --
@pytest.mark.parametrize("seed", SEEDS)
def test_Pw_extend_correct_differs(seed):
    w = make_Pw(5, 320, seed)
    ec = w.planted["extend_correct"]
    assert ec["stable"] is True
    assert ec["fast_decay"] is False


# -- 7. G world builds --
@pytest.mark.parametrize("n", [5, 10])
@pytest.mark.parametrize("seed", SEEDS)
def test_G_builds(n, seed):
    w = make_G(n, 5, 0.8, 0.0, seed)
    assert isinstance(w, CollectiveWorld)
    assert w.planted["planted"] == "intersection"
    assert w.planted["n_members"] == n
    assert w.planted["m_actions"] == 5


# -- 8. G: admissible set is valid intersection --
@pytest.mark.parametrize("seed", SEEDS)
def test_G_admissible_is_intersection(seed):
    w = make_G(5, 5, 0.9, 0.0, seed)
    gi = w.group_input
    adm = w.planted["admissible"]
    for a in adm:
        for m in gi["members"]:
            g = m["gamma"][a]
            assert g["auth"] and g["feas"] and g["safe"] and g["epi"], \
                f"action {a} in admissible but member {m['memberRef']} blocks"
    # Actions NOT in admissible should have at least one blocker
    for a in gi["actions"]:
        if a not in adm:
            blocked = False
            for m in gi["members"]:
                g = m["gamma"][a]
                if not (g["auth"] and g["feas"] and g["safe"] and g["epi"]):
                    blocked = True
                    break
            assert blocked, f"action {a} not admissible but no blocker"


# -- 9. make_world dispatch works --
@pytest.mark.parametrize("seed", SEEDS[:1])
def test_dispatch(seed):
    for name in WORLDS:
        kw = {}
        if name == "O":
            kw = {"k": 2}
        elif name == "Pn":
            kw = {"n": 5}
        elif name in ("Pc", "Pl", "Pw"):
            kw = {"n": 5, "T": 320}
        elif name == "G":
            kw = {"n": 5, "m": 5, "p": 0.8, "rho": 0.0}
        w = make_world(name, seed=seed, **kw)
        assert isinstance(w, CollectiveWorld)
