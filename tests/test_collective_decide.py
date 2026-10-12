"""Decision function tests for collective bench (Paper 8). Seeds 9001-9004.
Tests: refusal with None thresholds, failure classes, not-applicable.
"""
import pytest
import collective.decide as D


def _row(**kw):
    base = {
        "Q1_statute_dup": "T", "Q1_statute_dedup": "T",
        "Q1_total_obs_dup": 80, "Q1_total_obs_dedup": 40,
        "Q1_n_episodes_dup": 40, "Q1_n_episodes_dedup": 40,
        "Q1_inv_s1_obs": 8, "Q1_inv_s2_obs": 12,
        "Q1_inv_s1_episodes": 8, "Q1_inv_s2_episodes": 3,
        "Q1_inv_obs_winner": "s2", "Q1_inv_episode_winner": "s1",
        "Q2_R_own_elected": None, "Q2_suggestion_origin": None,
        "Q2_R_pool_elected": "s2",
        "Q3_location_ratio": 0.5, "Q3_transfer_ratio": None,
        "Q3_H1_passed": None,
        "Q4_R_mean_chosen": "a0", "Q4_R_leastmisery_chosen": "a0",
        "Q4_planted_admissible": ["a0"],
        "Q4_R_mean_in_all_gamma": True,
        "Q4_R_leastmisery_in_all_gamma": True,
        "Q4_admissible_empty": False,
        "Q4_R_group_admissible": None,
        "Q4_R_group_indeterminate": None,
        "Q4_R_group_status_quo_ok": None,
        "world": "O", "seed": 9001,
    }
    base.update(kw)
    return base


def _rows(n=20, **kw):
    return [_row(**kw) for _ in range(n)]


# -- 1. Refuse with None thresholds --
def test_refuse_with_none_thresholds():
    saved = {k: getattr(D, k) for k in dir(D) if k.startswith("TH_")}
    try:
        for k in saved:
            setattr(D, k, None)
        with pytest.raises(RuntimeError, match="thresholds not set"):
            D.decide(_rows(), "O")
    finally:
        for k, v in saved.items():
            setattr(D, k, v)


def test_q1_refuses_none():
    saved = {k: getattr(D, k) for k in dir(D) if k.startswith("TH_")}
    try:
        for k in saved:
            setattr(D, k, None)
        with pytest.raises(RuntimeError, match="thresholds not set"):
            D.q1(_rows(), "O")
    finally:
        for k, v in saved.items():
            setattr(D, k, v)


# -- 2. Not applicable returns None --
def test_q1_not_applicable():
    assert D.q1(_rows(), "Pn") is None

def test_q2_not_applicable():
    assert D.q2(_rows(), "O") is None

def test_q3_not_applicable():
    assert D.q3(_rows(), "O", n=5, T=320) is None

def test_q4_not_applicable():
    assert D.q4(_rows(), "O", n=10, p=0.8, rho=0.0) is None


# -- 3. With thresholds set (monkeypatch per-cell dicts) --
_PW_TH = {(5, 320): 0.80, (5, 640): 0.80,
           (20, 320): 0.80, (20, 640): 0.80}
_PL_TH = {(5, 320): 0.80, (5, 640): 0.80,
           (20, 320): 0.80, (20, 640): 0.80}
_G_TH = {(10, 0.8, 0.0): 0.80, (10, 0.8, 0.5): 0.80,
          (10, 0.9, 0.0): 0.80, (10, 0.9, 0.5): 0.80,
          (30, 0.8, 0.0): 0.80, (30, 0.8, 0.5): 0.80,
          (30, 0.9, 0.0): 0.80, (30, 0.9, 0.5): 0.80}


@pytest.fixture(autouse=True)
def _set_thresholds(monkeypatch):
    monkeypatch.setattr(D, "TH_Q1_COUNT", 0.80)
    monkeypatch.setattr(D, "TH_Q2_POOL", 0.80)
    monkeypatch.setattr(D, "TH_Q3_H1_PASS", _PW_TH)
    monkeypatch.setattr(D, "TH_Q3_H1_WRONG", _PW_TH)
    monkeypatch.setattr(D, "TH_Q3_H1_REFUSE", _PL_TH)
    monkeypatch.setattr(D, "TH_Q4_MEAN_OUTSIDE", _G_TH)


# Q1
def test_q1_passes():
    r = D.q1(_rows(Q1_statute_dup="T"), "O")
    assert r["passed"] is True

def test_q1_instrument_defect():
    r = D.q1(_rows(Q1_statute_dup="B"), "O")
    assert not r["passed"]
    assert r["failure_class"] == "instrument_defect"


# Q2
def test_q2_passes():
    r = D.q2(_rows(Q2_R_own_elected=None, Q2_R_pool_elected="s2"), "Pn")
    assert r["passed"] is True

def test_q2_plugin_defect():
    r = D.q2(_rows(Q2_R_own_elected="s1", Q2_R_pool_elected="s2"), "Pn")
    assert not r["passed"]
    assert r["failure_class"] == "plugin_defect"


# Q3
def test_q3_pw_passes():
    r = D.q3(_rows(Q3_location_ratio=0.5, Q3_borrow_error=True),
             "Pw", n=5, T=320)
    assert r["passed"] is True

def test_q3_pw_instrument_defect_gate():
    """Gate fails (ratio > 1): instrument_defect per SS9."""
    r = D.q3(_rows(Q3_location_ratio=1.5), "Pw", n=5, T=320)
    assert not r["passed"]
    assert r["failure_class"] == "instrument_defect"

def test_q3_pw_against_thesis_borrow():
    """Borrowing error below threshold: against_thesis per SS9."""
    r = D.q3(_rows(Q3_location_ratio=0.5, Q3_borrow_error=False),
             "Pw", n=5, T=320)
    assert not r["passed"]
    assert r["failure_class"] == "against_thesis"

def test_q3_pl_passes():
    r = D.q3(_rows(Q3_location_ratio=1.5), "Pl", n=5, T=320)
    assert r["passed"] is True

def test_q3_pl_instrument_defect_gate():
    """Gate fails to refuse (ratio <= 1 in Pl): instrument_defect per SS9."""
    r = D.q3(_rows(Q3_location_ratio=0.5), "Pl", n=5, T=320)
    assert not r["passed"]
    assert r["failure_class"] == "instrument_defect"


# Q4
def test_q4_passes():
    r = D.q4(_rows(Q4_R_mean_in_all_gamma=False,
                   Q4_R_group_admissible=["a0"],
                   Q4_planted_admissible=["a0"],
                   Q4_R_group_indeterminate=False,
                   Q4_admissible_empty=False,
                   Q4_R_group_hidden_ok=True), "G",
             n=10, p=0.8, rho=0.0)
    assert r["passed"] is True

def test_q4_instrument_defect():
    r = D.q4(_rows(Q4_R_mean_in_all_gamma=True,
                   Q4_R_group_admissible=["a0"],
                   Q4_planted_admissible=["a0"],
                   Q4_R_group_indeterminate=False,
                   Q4_admissible_empty=False,
                   Q4_R_group_hidden_ok=True), "G",
             n=10, p=0.8, rho=0.0)
    assert not r["passed"]
    assert r["failure_class"] == "instrument_defect"

def test_q4_plugin_defect_admissible_mismatch():
    r = D.q4(_rows(Q4_R_mean_in_all_gamma=False,
                   Q4_R_group_admissible=["a1"],
                   Q4_planted_admissible=["a0"],
                   Q4_R_group_indeterminate=False,
                   Q4_admissible_empty=False,
                   Q4_R_group_hidden_ok=True), "G",
             n=10, p=0.8, rho=0.0)
    assert not r["passed"]
    assert r["failure_class"] == "plugin_defect"
