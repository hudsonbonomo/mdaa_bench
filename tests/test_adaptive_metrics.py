"""Each function in metrics.py verified on FABRICATED readings. Ordem §7c.
Small hand-crafted dicts, no world, no seed. No metric on a generated world.
"""
from adaptive.metrics import (p1_final_window, p2_n_adjustments,
                               p5_monotone_conflict_sym, p6_after_rename,
                               p7_redeclaration, cost_k, cost_v)

def _reading(window=40, state="DECLARED", adjustments=None, run=0,
             reason="test", lastReturn=None, declaredWindow=40):
    return {"window": window, "state": state, "run": run, "reason": reason,
            "declaredWindow": declaredWindow,
            "adjustments": adjustments or [], "lastReturn": lastReturn}

def _adj(seq, frm, to):
    return {"seq": seq, "from": frm, "to": to,
            "returns": [{"fromSeq": seq - 14, "toSeq": seq - 10}],
            "confirmed": {"fromSeq": seq - 30, "toSeq": seq - 20},
            "inForce": {"fromSeq": seq - 20, "toSeq": seq - 10}}


# ---- P1 ----

def test_p1_final_window_basic():
    readings = [_reading(window=40), _reading(window=80)]
    assert p1_final_window(readings) == 80

def test_p1_empty():
    assert p1_final_window([]) == 40


# ---- P2 ----

def test_p2_count_adjustments():
    adjs = [_adj(100, 40, 50), _adj(200, 50, 60)]
    readings = [_reading(adjustments=adjs)]
    assert p2_n_adjustments(readings) == 2

def test_p2_no_adjustments():
    assert p2_n_adjustments([_reading()]) == 0

def test_p2_empty():
    assert p2_n_adjustments([]) == 0


# ---- P5 ----

def test_p5_monotone_true():
    readings = [_reading(window=40), _reading(window=50), _reading(window=60)]
    blocks = [(0, 4), (10, 14), (20, 24)]
    planted = {"tau": 100}
    r = p5_monotone_conflict_sym(readings, blocks, planted, "R_declared")
    assert r["monotone"] is True

def test_p5_monotone_false():
    readings = [_reading(window=60), _reading(window=50)]
    blocks = [(0, 4), (10, 14)]
    planted = {"tau": 100}
    r = p5_monotone_conflict_sym(readings, blocks, planted, "R_declared")
    assert r["monotone"] is False

def test_p5_conflict_in_first_two():
    lr_conflict = {"seq": 14, "kind": "CONFLICT"}
    readings = [_reading(lastReturn=lr_conflict),
                _reading(lastReturn={"seq": 24, "kind": "COUNTED"})]
    blocks = [(10, 14), (20, 24)]
    planted = {"tau": 5}
    r = p5_monotone_conflict_sym(readings, blocks, planted, "R_declared")
    assert r["conflict_in_first_two_after_tau"] is True

def test_p5_no_conflict():
    lr = {"seq": 14, "kind": "COUNTED"}
    readings = [_reading(lastReturn=lr), _reading(lastReturn=lr)]
    blocks = [(10, 14), (20, 24)]
    planted = {"tau": 5}
    r = p5_monotone_conflict_sym(readings, blocks, planted, "R_declared")
    assert r["conflict_in_first_two_after_tau"] is False

def test_p5_sym_shortened():
    readings = [_reading(window=60), _reading(window=50)]
    blocks = [(100, 104), (110, 114)]
    planted = {"tau": 90}
    r = p5_monotone_conflict_sym(readings, blocks, planted, "R_sym")
    assert r["sym_shortened"] is True

def test_p5_sym_not_shortened():
    readings = [_reading(window=40), _reading(window=50)]
    blocks = [(100, 104), (110, 114)]
    planted = {"tau": 90}
    r = p5_monotone_conflict_sym(readings, blocks, planted, "R_sym")
    assert r["sym_shortened"] is False


# ---- P6 ----

def test_p6_adj_after_rename():
    a1 = _adj(180, 40, 50)
    a2 = _adj(250, 50, 60)
    readings = [_reading(adjustments=[a1, a2])]
    blocks = [(0, 4)]
    planted = {"first_rename": 200, "rename_recon_pairs": []}
    r = p6_after_rename(readings, blocks, planted)
    assert r["adjustments_after_rename"] == 1

def test_p6_suspended_correct():
    rdg = _reading(state="SUSPENDED", window=40,
                   reason="a condition key was renamed: evidence cannot be asked")
    readings = [rdg]
    blocks = [(200, 204)]  # nowSeq = 205
    planted = {"first_rename": 200,
               "rename_recon_pairs": [(200, 210)]}
    r = p6_after_rename(readings, blocks, planted)
    assert r["suspended_correct"] is True

def test_p6_suspended_wrong_state():
    rdg = _reading(state="DECLARED", window=40, reason="test")
    readings = [rdg]
    blocks = [(200, 204)]
    planted = {"first_rename": 200,
               "rename_recon_pairs": [(200, 210)]}
    r = p6_after_rename(readings, blocks, planted)
    assert r["suspended_correct"] is False

def test_p6_all_have_reason():
    readings = [_reading(reason="x"), _reading(reason="y")]
    blocks = [(0, 4), (10, 14)]
    planted = {"first_rename": 500, "rename_recon_pairs": []}
    r = p6_after_rename(readings, blocks, planted)
    assert r["all_have_reason"] is True

def test_p6_missing_reason():
    readings = [_reading(reason="x"), _reading(reason="")]
    blocks = [(0, 4), (10, 14)]
    planted = {"first_rename": 500, "rename_recon_pairs": []}
    r = p6_after_rename(readings, blocks, planted)
    assert r["all_have_reason"] is False


# ---- P7 ----

def test_p7_redeclaration_ok():
    extra = _reading(state="DECLARED", window=40, run=0)
    readings = [_reading(adjustments=[_adj(200, 40, 50)])]
    planted = {"redeclare_seq": 160}
    r = p7_redeclaration(extra, readings, planted)
    assert r["declared_state_ok"] is True
    assert r["returns_after_redecl"] is True

def test_p7_wrong_state():
    extra = _reading(state="ADJUSTED", window=50, run=2)
    planted = {"redeclare_seq": 160}
    r = p7_redeclaration(extra, [], planted)
    assert r["declared_state_ok"] is False

def test_p7_returns_before_redecl():
    adj_bad = {"seq": 200, "from": 40, "to": 50,
               "returns": [{"fromSeq": 100, "toSeq": 110}],
               "confirmed": {"fromSeq": 80, "toSeq": 90},
               "inForce": None}
    readings = [_reading(adjustments=[adj_bad])]
    planted = {"redeclare_seq": 160}
    extra = _reading(state="DECLARED", window=40, run=0)
    r = p7_redeclaration(extra, readings, planted)
    assert r["returns_after_redecl"] is False


# ---- Cost K ----

def test_cost_k_counts_conflicts():
    lr_c = {"seq": 164, "kind": "CONFLICT"}
    lr_n = {"seq": 174, "kind": "COUNTED"}
    readings = [_reading(lastReturn=lr_c), _reading(lastReturn=lr_n)]
    blocks = [(160, 164), (170, 174)]
    planted = {"tau": 150}
    assert cost_k(readings, blocks, planted) == 1

def test_cost_k_before_tau():
    lr_c = {"seq": 14, "kind": "CONFLICT"}
    readings = [_reading(lastReturn=lr_c)]
    blocks = [(10, 14)]
    planted = {"tau": 100}
    assert cost_k(readings, blocks, planted) == 0


# ---- Cost V ----

def test_cost_v_counts_after_rename():
    a1 = _adj(180, 40, 50)
    a2 = _adj(250, 50, 60)
    a3 = _adj(300, 60, 70)
    readings = [_reading(adjustments=[a1, a2, a3])]
    planted = {"first_rename": 200}
    assert cost_v(readings, planted) == 2

def test_cost_v_none_after_rename():
    a1 = _adj(100, 40, 50)
    readings = [_reading(adjustments=[a1])]
    planted = {"first_rename": 200}
    assert cost_v(readings, planted) == 0
