"""Decision function tests for value bench (Paper 7). Seeds 9001-9004.
Tests: refusal with None thresholds, failure classes, empty cell handling.
"""
import pytest
import value.decide as D


def _row(**kw):
    base = {
        "R_norm_state": None, "R_norm_elected": None,
        "R_norm_s2s3_state": None, "R_norm_s2s3_elected": None,
        "R_reward_elected": "s1", "R_infer_value_elected": "s1",
        "R_scalar_elected": "s1", "R_naive_elected": None,
        "R_naive_justified": False, "R_naive_diff": 0.0,
        "P3_invariant": None, "P6_s3_never_elected": True,
        "P6_layer7_true": {}, "P6_layer7_false": {},
        "cost_checkpoint": None,
        "world": "P", "T": 80, "seed": 9001,
    }
    base.update(kw)
    return base


def _rows(n=20, **kw):
    return [_row(**kw) for _ in range(n)]


# -- 1. Refuse with None thresholds (no fixture, real None) --
def test_refuse_with_none_thresholds():
    """decide() must refuse when any TH_ is still None."""
    saved = {k: getattr(D, k) for k in dir(D) if k.startswith("TH_")}
    try:
        for k in saved:
            setattr(D, k, None)
        with pytest.raises(RuntimeError, match="thresholds not set"):
            D.decide(_rows(), "P", 80)
    finally:
        for k, v in saved.items():
            setattr(D, k, v)


def test_p1_refuses_none():
    saved = {k: getattr(D, k) for k in dir(D) if k.startswith("TH_")}
    try:
        for k in saved:
            setattr(D, k, None)
        with pytest.raises(RuntimeError, match="thresholds not set"):
            D.p1(_rows(R_norm_state="SEM_NORMA"), "N0", 80)
    finally:
        for k, v in saved.items():
            setattr(D, k, v)


# -- 2. Not applicable returns None (skips _check_thresholds) --
def test_p1_not_applicable():
    assert D.p1(_rows(), "P", 80) is None


def test_p2_not_applicable():
    assert D.p2(_rows(), "N0", 80) is None


def test_p3_not_applicable():
    assert D.p3(_rows(), "P", 80) is None


def test_p4_not_applicable():
    assert D.p4(_rows(), "P", 80) is None


def test_p5_not_applicable():
    assert D.p5(_rows(), "P", 80) is None


# -- 3. With thresholds set, test each prediction --
@pytest.fixture(autouse=True)
def _set_thresholds(monkeypatch):
    """Set all thresholds to known values for testing."""
    monkeypatch.setattr(D, "TH_P1_NORM", 1.0)
    monkeypatch.setattr(D, "TH_P1_REWARD", 1.0)
    monkeypatch.setattr(D, "TH_P2", 0.80)
    monkeypatch.setattr(D, "TH_P2_REWARD", 0.80)
    monkeypatch.setattr(D, "TH_P3", 0.80)
    monkeypatch.setattr(D, "TH_P4_CONFLICT", 0.80)
    monkeypatch.setattr(D, "TH_P4_ELECT", 0.80)
    monkeypatch.setattr(D, "TH_P5_X_NAIVE", 0.80)
    monkeypatch.setattr(D, "TH_P5_XP", 0.80)


# P1
def test_p1_passes():
    r = D.p1(_rows(R_norm_state="SEM_NORMA", R_reward_elected="s1"), "N0", 80)
    assert r["passed"] is True


def test_p1_plugin_defect():
    r = D.p1(_rows(R_norm_state="JUSTIFICADO", R_reward_elected="s1"), "N0", 80)
    assert not r["passed"] and r["failure_class"] == "plugin_defect"


# P2
def test_p2_passes():
    r = D.p2(_rows(R_norm_state="JUSTIFICADO", R_norm_elected="s2",
                   R_reward_elected="s1"), "P", 80)
    assert r["passed"] is True


def test_p2_against_thesis():
    r = D.p2(_rows(R_norm_state="JUSTIFICADO", R_norm_elected="s1",
                   R_reward_elected="s1"), "P", 80)
    assert not r["passed"] and r["failure_class"] == "against_thesis"


# P3
def test_p3_passes():
    r = D.p3(_rows(P3_invariant=True, R_infer_value_elected="s1",
                   R_infer_value_no_pause="s2"), "R", 80)
    assert r["passed"] is True


def test_p3_plugin_defect():
    r = D.p3(_rows(P3_invariant=False, R_infer_value_elected="s1",
                   R_infer_value_no_pause="s2"), "R", 80)
    assert not r["passed"] and r["failure_class"] == "plugin_defect"


# P4
def test_p4_conflict_passes():
    r = D.p4(_rows(R_norm_state="EM_CONFLITO", R_scalar_elected="s1"), "C0", 80)
    assert r["passed"] is True


def test_p4_c1_passes():
    r = D.p4(_rows(R_norm_state="JUSTIFICADO", R_norm_elected="s2"), "C1", 80)
    assert r["passed"] is True


def test_p4_c1_against_thesis():
    r = D.p4(_rows(R_norm_state="INSUFICIENTE", R_norm_elected=None), "C1", 80)
    assert not r["passed"] and r["failure_class"] == "against_thesis"


# P5
def test_p5_x_passes():
    r = D.p5(_rows(R_norm_state="INSUFICIENTE",
                   R_naive_justified=True, R_naive_elected="s1"), "X", 80)
    assert r["passed"] is True


def test_p5_x_plugin_defect():
    r = D.p5(_rows(R_norm_state="JUSTIFICADO",
                   R_naive_justified=True, R_naive_elected="s1"), "X", 80)
    assert not r["passed"] and r["failure_class"] == "plugin_defect"


def test_p5_xp_passes():
    r = D.p5(_rows(R_norm_state="NAO_JUSTIFICADO"), "Xp", 80)
    assert r["passed"] is True


# P6
def test_p6_passes():
    r = D.p6(_rows(P6_s3_never_elected=True), "P", 80)
    assert r["passed"] is True


def test_p6_plugin_defect():
    r = D.p6(_rows(P6_s3_never_elected=False), "P", 80)
    assert not r["passed"] and r["failure_class"] == "plugin_defect"


# -- 4. Failure class: instrument_defect for all-empty cell --
def test_p1_instrument_defect_when_reward_fails():
    r = D.p1(_rows(R_norm_state="SEM_NORMA", R_reward_elected=None), "N0", 80)
    assert not r["passed"] and r["failure_class"] == "instrument_defect"
