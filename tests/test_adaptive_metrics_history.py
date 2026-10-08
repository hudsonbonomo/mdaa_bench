"""Cumulative-history metric tests. Ordem emendas-2 SS2.
Fabricated readings are CUMULATIVE: each reading repeats all prior adjustments,
as the plugin actually does. These tests catch the double-counting bugs.
"""
from adaptive.metrics import (p6_after_rename, p7_redeclaration,
                               p5_monotone_conflict_sym, cost_k, cost_v)


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


# ---- p6 cumulative counting ----

def test_p6_adj_count_no_cumulative():
    """Same adj repeated across readings: count only from last reading."""
    a_before = _adj(180, 40, 50)   # seq < 200 (first_rename)
    a_after = _adj(250, 50, 60)    # seq > 200
    # Cumulative: r1 has [a_before], r2 has [a_before, a_after]
    r1 = _reading(adjustments=[a_before])
    r2 = _reading(adjustments=[a_before, a_after])
    blocks = [(0, 4), (10, 14)]
    planted = {"first_rename": 200, "rename_recon_pairs": []}
    result = p6_after_rename([r1, r2], blocks, planted)
    assert result["adjustments_after_rename"] == 1


def test_p6_at_rename_boundary_checked():
    """Reading at nowSeq == rename should be checked for SUSPENDED."""
    rdg = _reading(state="SUSPENDED", window=40,
                   reason="a condition key was renamed: no evidence")
    blocks = [(196, 199)]  # nowSeq = 200
    planted = {"first_rename": 200, "rename_recon_pairs": [(200, 210)]}
    result = p6_after_rename([rdg], blocks, planted)
    assert result["suspended_correct"] is True


def test_p6_at_rename_not_suspended_fails():
    """Reading at nowSeq == rename that is NOT SUSPENDED must fail."""
    rdg = _reading(state="DECLARED", window=50, reason="normal")
    blocks = [(196, 199)]  # nowSeq = 200
    planted = {"first_rename": 200, "rename_recon_pairs": [(200, 210)]}
    result = p6_after_rename([rdg], blocks, planted)
    assert result["suspended_correct"] is False


def test_p6_at_reconciliation_not_required_suspended():
    """Reading at nowSeq == reconciliation is NOT in the interval."""
    rdg = _reading(state="DECLARED", window=50, reason="normal")
    blocks = [(200, 204)]  # nowSeq = 205
    planted = {"first_rename": 200, "rename_recon_pairs": [(200, 205)]}
    result = p6_after_rename([rdg], blocks, planted)
    assert result["suspended_correct"] is True


# ---- cost_v cumulative ----

def test_cost_v_no_cumulative():
    """Same adj in multiple readings: count only from last."""
    a = _adj(250, 40, 50)  # seq > 200
    r1 = _reading(adjustments=[a])
    r2 = _reading(adjustments=[a])
    planted = {"first_rename": 200}
    assert cost_v([r1, r2], planted) == 1


# ---- p7 cumulative ----

def test_p7_no_cumulative():
    """Only the last reading's adjustments matter for returns check."""
    adj_ok = {"seq": 200, "from": 40, "to": 50,
              "returns": [{"fromSeq": 170, "toSeq": 180}],
              "confirmed": None, "inForce": None}
    r1 = _reading(adjustments=[adj_ok])
    r2 = _reading(adjustments=[adj_ok])
    extra = _reading(state="DECLARED", window=40, run=0)
    planted = {"redeclare_seq": 160}
    result = p7_redeclaration(extra, [r1, r2], planted)
    assert result["returns_after_redecl"] is True


# ---- cost_k and p5: stale lastReturn ----

def test_cost_k_stale_lastreturn_no_count():
    """A lastReturn from a previous block doesn't count."""
    lr_real = {"seq": 104, "kind": "CONFLICT"}
    lr_stale = {"seq": 104, "kind": "CONFLICT"}  # seq != block1 last (114)
    readings = [_reading(lastReturn=lr_real),
                _reading(lastReturn=lr_stale)]
    blocks = [(100, 104), (110, 114)]
    planted = {"tau": 50}
    assert cost_k(readings, blocks, planted) == 1


def test_p5_stale_lastreturn_no_conflict():
    """A stale lastReturn from a previous block doesn't count as CONFLICT."""
    lr_stale = {"seq": 14, "kind": "CONFLICT"}  # block0 last=14, ok
    lr_stale2 = {"seq": 14, "kind": "CONFLICT"}  # block1 last=24, STALE
    readings = [_reading(lastReturn=lr_stale),
                _reading(lastReturn=lr_stale2)]
    blocks = [(10, 14), (20, 24)]
    planted = {"tau": 5}
    r = p5_monotone_conflict_sym(readings, blocks, planted, "R_declared")
    # block0: lr.seq=14 == 14 -> CONFLICT counted
    # block1: lr.seq=14 != 24 -> NOT counted
    assert r["conflict_in_first_two_after_tau"] is True  # block0 has it
