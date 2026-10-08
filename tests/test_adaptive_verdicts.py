"""Tests for verdicts, costs, and control_view. Emendas-3 SS5."""
import pytest
from adaptive.verdicts import verdicts, costs, control_view
from adaptive import decide as D

def _row(**kw):
    base = {"R_declared_window": 40, "R_declared_n_adj": 0,
            "R_fixed_window": 40, "R_fixed_n_adj": 0,
            "R_simple_window": 40, "R_simple_n_adj": 0,
            "R_sym_window": 40, "R_sym_n_adj": 0,
            "R_cross_window": 40, "R_cross_n_adj": 0}
    base.update(kw)
    return base
def _rows(n=20, **kw):
    return [_row(**kw) for _ in range(n)]

def test_all_empty_does_not_pass():
    r = D.p3b(_rows(P3b_total=0, P3b_failed=0), "S", 640, 3)
    assert not r["passed"] and r["failure_class"] == "instrument_defect"

def test_one_empty_rest_pass():
    rows = [_row(P3b_total=5, P3b_failed=5)] * 19
    rows.append(_row(P3b_total=0, P3b_failed=0))
    r = D.p3b(rows, "S", 640, 3)
    assert r["passed"] and r["excluded"] == 1

def _cd(pred, passed, failure_class=None, **kw):
    d = {"passed": passed, "failure_class": failure_class}
    d.update(kw)
    return {pred: d}

def test_prediction_passes_all_cells():
    dbc = {"S_T320_k3": _cd("p1", True), "S_T320_k5": _cd("p1", True),
           "S_T640_k3": _cd("p1", True)}
    v = verdicts(dbc)
    assert v["p1"]["passed"] is True and v["p1"]["failed_cells"] == []

def test_prediction_fails_one_cell():
    dbc = {"S_T320_k3": _cd("p1", True), "S_T320_k5": _cd("p1", True),
           "S_T640_k3": _cd("p1", False, "against_thesis"),
           "S_T640_k5": _cd("p1", True)}
    v = verdicts(dbc)
    assert not v["p1"]["passed"]
    assert "S_T640_k3" in [f["cell"] for f in v["p1"]["failed_cells"]]

def test_three_pass_one_fail():
    dbc = {"K_T320_k3": _cd("p5", True), "K_T320_k5": _cd("p5", True),
           "K_T640_k3": _cd("p5", True),
           "K_T640_k5": _cd("p5", False, "against_thesis")}
    v = verdicts(dbc)
    assert not v["p5"]["passed"]
    assert len(v["p5"]["failed_cells"]) == 1
    assert v["p5"]["failed_cells"][0]["cell"] == "K_T640_k5"

def test_p4_own_ok_borrowed_p2_fails():
    dbc = {
        "S_T640_k3": {"p4": {"side": "R_simple", "rate": 1.0,
                      "passed": True, "failure_class": None},
                      "p3": {"mean_mix": 0.3, "passed": True,
                      "failure_class": None}},
        "N_T320_k3": {"p4": {"side": "R_mix", "rate": 1.0,
                      "passed": True, "failure_class": None},
                      "p2": {"rate_declared": 0.95, "rate_simple": 0.3,
                      "passed": False, "failure_class": "instrument_defect"}},
        "N_T640_k3": {"p4": {"side": "R_mix", "rate": 1.0,
                      "passed": True, "failure_class": None},
                      "p2": {"rate_declared": 0.95, "rate_simple": 0.9,
                      "passed": True, "failure_class": None}},
    }
    v = verdicts(dbc)
    assert not v["p4"]["passed"]
    classes = {f["failure_class"] for f in v["p4"]["failed_cells"]}
    assert "instrument_defect" in classes

def test_p4_own_side_fails_against_thesis():
    dbc = {
        "S_T640_k3": {"p4": {"side": "R_simple", "rate": 0.5,
                      "passed": False, "failure_class": "against_thesis"},
                      "p3": {"mean_mix": 0.3, "passed": True,
                      "failure_class": None}},
        "N_T320_k3": {"p4": {"side": "R_mix", "rate": 1.0,
                      "passed": True, "failure_class": None},
                      "p2": {"rate_declared": 0.95, "rate_simple": 0.9,
                      "passed": True, "failure_class": None}},
    }
    v = verdicts(dbc)
    assert not v["p4"]["passed"]
    sources = {f["source"] for f in v["p4"]["failed_cells"]}
    assert "own" in sources
    classes = {f["failure_class"] for f in v["p4"]["failed_cells"]}
    assert "against_thesis" in classes

def test_p4_own_side_preserves_instrument_defect():
    """P4 own side with instrument_defect from decide.p4 is preserved."""
    dbc = {
        "S_T640_k3": {"p4": {"side": "R_simple", "rate": 0.0,
                      "passed": False, "failure_class": "instrument_defect"},
                      "p3": {"mean_mix": 0.3, "n_counted_mix": 5,
                      "passed": True, "failure_class": None}},
        "N_T320_k3": {"p4": {"side": "R_mix", "rate": 1.0,
                      "passed": True, "failure_class": None},
                      "p2": {"rate_declared": 0.95, "rate_simple": 0.9,
                      "passed": True, "failure_class": None}},
    }
    v = verdicts(dbc)
    assert not v["p4"]["passed"]
    own_fails = [f for f in v["p4"]["failed_cells"] if f["source"] == "own"]
    assert len(own_fails) == 1
    assert own_fails[0]["failure_class"] == "instrument_defect"


def test_p4_borrowed_p3_fails_when_n_counted_mix_zero():
    """P4 borrowed P3 side fails when no R_mix seed has adjustments."""
    dbc = {
        "S_T640_k3": {"p4": {"side": "R_simple", "rate": 1.0,
                      "passed": True, "failure_class": None},
                      "p3": {"mean_mix": 0.0, "n_counted_mix": 0,
                      "passed": False, "failure_class": "instrument_defect"}},
        "N_T320_k3": {"p4": {"side": "R_mix", "rate": 1.0,
                      "passed": True, "failure_class": None},
                      "p2": {"rate_declared": 0.95, "rate_simple": 0.9,
                      "passed": True, "failure_class": None}},
    }
    v = verdicts(dbc)
    assert not v["p4"]["passed"]
    bp3 = [f for f in v["p4"]["failed_cells"]
           if f["source"] == "borrowed_p3"]
    assert len(bp3) == 1
    assert bp3[0]["failure_class"] == "instrument_defect"


def test_control_view_no_forbidden_keys():
    cell_results = {
        "N_T640_k3": {"p2": {"rate_declared": 0.95, "rate_simple": 0.9,
                      "passed": True, "failure_class": None}},
        "S_T640_k3": {"p3": {"rate_declared": 1.0, "mean_mix": 0.3,
                      "excluded_mix": 0, "passed": True, "failure_class": None},
                      "p3b": {"rate": 1.0, "passed": True,
                      "failure_class": None},
                      "p4": {"side": "R_simple", "rate": 1.0,
                      "passed": True, "failure_class": None}},
        "K_T320_k3": {"p5": {"rate_monotone": 1.0, "rate_conflict": 0.95,
                      "rate_sym": 0.85, "passed": True,
                      "failure_class": None}},
        "V_T320_k3": {"p6": {"rate_declared": 1.0, "rate_cross": 0.95,
                      "passed": True, "failure_class": None}},
    }
    cv = control_view(cell_results)
    forbidden = {"declared", "monotone", "conflict"}
    for ck, cd in cv.items():
        for pn, pd in cd.items():
            if pn == "p3b":
                continue
            for key in pd:
                for bad in forbidden:
                    assert bad not in key, f"{ck}.{pn}.{key} has '{bad}'"
            assert "passed" not in pd
            assert "failure_class" not in pd

def test_control_view_has_thresholds():
    cell_results = {
        "N_T640_k3": {"p2": {"rate_simple": 0.9, "passed": True}},
        "S_T640_k3": {"p3": {"mean_mix": 0.3, "excluded_mix": 0,
                      "passed": True},
                      "p3b": {"rate": 1.0, "passed": True}},
    }
    cv = control_view(cell_results)
    assert cv["N_T640_k3"]["p2"]["threshold"] == 0.85
    assert cv["S_T640_k3"]["p3"]["threshold"] == 0.50
    assert cv["S_T640_k3"]["p3b"]["threshold"] == 1.00

def test_costs_k_cell():
    rows = [{"world": "K", "T": 320, "k": 3,
             "cost_B_R_declared": 4, "cost_B_R_fixed": 2},
            {"world": "K", "T": 320, "k": 3,
             "cost_B_R_declared": 6, "cost_B_R_fixed": 4}]
    c = costs(rows)
    assert c["K_T320_k3"]["mean_B_R_declared"] == 5.0
    assert c["K_T320_k3"]["mean_B_R_fixed"] == 3.0
    assert c["K_T320_k3"]["mean_B_diff"] == 2.0

def test_costs_v_cell():
    rows = [{"world": "V", "T": 320, "k": 3,
             "cost_A_R_cross": 3, "cost_A_R_declared": 0},
            {"world": "V", "T": 320, "k": 3,
             "cost_A_R_cross": 5, "cost_A_R_declared": 0}]
    c = costs(rows)
    assert c["V_T320_k3"]["mean_A_R_cross"] == 4.0
    assert c["V_T320_k3"]["mean_A_R_declared"] == 0.0
