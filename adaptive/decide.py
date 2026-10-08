"""Decision functions for adaptive grid. PREREGISTRO v0.5 SS8-9.
Seeds with total==0 excluded from rates over adjustments (P3, P3b, P4).
"""
from __future__ import annotations
from .worlds import load_policy

__all__ = [
    "TH_P1_DECLARED", "TH_P1_FIXED", "TH_P2_DECLARED",
    "TH_P2_SIMPLE_T320", "TH_P2_SIMPLE_T640", "TH_P3_DECLARED",
    "TH_P3_MIX", "TH_P3B", "TH_P4_SIMPLE", "TH_P4_MIX",
    "TH_P5_MONOTONE", "TH_P5_CONFLICT", "TH_P5_SYM",
    "TH_P6_DECLARED", "TH_P6_CROSS", "TH_P7",
    "p1", "p2", "p3", "p3b", "p4", "p5", "p6", "p7"]

_P = load_policy()
_W0 = int(_P["declared"]["warrant_window"])
_STEP = int(_P["rule"]["step"])
TH_P1_DECLARED = 0.90
TH_P1_FIXED = 1.00
TH_P2_DECLARED = 0.95
TH_P2_SIMPLE_T320 = 0.60
TH_P2_SIMPLE_T640 = 0.85
TH_P3_DECLARED = 1.00
TH_P3_MIX = 0.50
TH_P3B = 1.00
TH_P4_SIMPLE = 1.00
TH_P4_MIX = 0.95
TH_P5_MONOTONE = 1.00
TH_P5_CONFLICT = 0.95
TH_P5_SYM = 0.80
TH_P6_DECLARED = 1.00
TH_P6_CROSS = 0.90
TH_P7 = 1.00

def _rate(ok: int, n: int) -> float:
    return ok / n if n else 0.0

def p1(rows: list[dict], world: str, T: int, k: int):
    """P1 (S): R_declared >= W0+2delta >= 0.90; R_fixed == W0."""
    if world != "S":
        return None
    n = len(rows)
    ok_d = sum(1 for r in rows if r["R_declared_window"] >= _W0 + 2 * _STEP)
    ok_f = sum(1 for r in rows if r["R_fixed_window"] == _W0)
    rd, rf = _rate(ok_d, n), _rate(ok_f, n)
    passed = rd >= TH_P1_DECLARED and rf >= TH_P1_FIXED
    fc = None
    if not passed:
        fc = "against_thesis" if rd < TH_P1_DECLARED else "instrument_defect"
    return {"rate_declared": rd, "rate_fixed": rf,
            "passed": passed, "failure_class": fc}

def p2(rows: list[dict], world: str, T: int, k: int):
    """P2 (N): R_declared zero adj >= 0.95; R_simple >=1 adj."""
    if world != "N":
        return None
    n = len(rows)
    ok_d = sum(1 for r in rows if r["R_declared_n_adj"] == 0)
    ok_s = sum(1 for r in rows if r["R_simple_n_adj"] >= 1)
    rd, rs = _rate(ok_d, n), _rate(ok_s, n)
    th_s = TH_P2_SIMPLE_T640 if T == 640 else TH_P2_SIMPLE_T320
    passed = rd >= TH_P2_DECLARED and rs >= th_s
    fc = None
    if not passed:
        fc = "against_thesis" if rd < TH_P2_DECLARED else "instrument_defect"
    return {"rate_declared": rd, "rate_simple": rs,
            "passed": passed, "failure_class": fc}

def p3(rows: list[dict], world: str, T: int, k: int):
    """P3 (S T=640): R_declared 1.00; R_mix mean <= 0.50."""
    if world != "S" or T != 640:
        return None
    from .verdicts import rate_excluding_empty
    dr = rate_excluding_empty(
        rows, "P3_R_declared_total",
        lambda r: r["P3_R_declared_reproduced"] == r["P3_R_declared_total"])
    mix_rates: list[float] = []
    ex_mix = 0
    for r in rows:
        if r["P3_R_mix_total"] == 0:
            ex_mix += 1
        else:
            mix_rates.append(r["P3_R_mix_reproduced"] / r["P3_R_mix_total"])
    rm = sum(mix_rates) / len(mix_rates) if mix_rates else 0.0
    base = {"rate_declared": dr["rate"], "mean_mix": rm,
            "excluded_declared": dr["excluded"], "excluded_mix": ex_mix,
            "n_counted_mix": len(mix_rates)}
    if dr["all_empty"] or not mix_rates:
        return {**base, "passed": False, "failure_class": "instrument_defect"}
    passed = dr["rate"] >= TH_P3_DECLARED and rm <= TH_P3_MIX
    fc = None
    if not passed:
        fc = "plugin_defect" if dr["rate"] < TH_P3_DECLARED else "instrument_defect"
    return {**base, "passed": passed, "failure_class": fc}

def p3b(rows: list[dict], world: str, T: int, k: int):
    """P3b (S T=640): tampered R_declared fails = 1.00."""
    if world != "S" or T != 640:
        return None
    from .verdicts import rate_excluding_empty
    er = rate_excluding_empty(
        rows, "P3b_total",
        lambda r: r["P3b_failed"] == r["P3b_total"])
    if er["all_empty"]:
        return {"rate": 0.0, "excluded": er["excluded"],
                "passed": False, "failure_class": "instrument_defect"}
    passed = er["rate"] >= TH_P3B
    fc = "instrument_defect" if not passed else None
    return {"rate": er["rate"], "excluded": er["excluded"],
            "passed": passed, "failure_class": fc}

def p4(rows: list[dict], world: str, T: int, k: int):
    """P4: R_simple reproduces (S T=640); R_mix zero triggers (N)."""
    if world == "S" and T == 640:
        from .verdicts import rate_excluding_empty
        er = rate_excluding_empty(
            rows, "P3_R_simple_total",
            lambda r: r["P3_R_simple_reproduced"] == r["P3_R_simple_total"])
        if er["all_empty"]:
            return {"side": "R_simple", "rate": 0.0,
                    "excluded": er["excluded"],
                    "passed": False, "failure_class": "instrument_defect"}
        passed = er["rate"] >= TH_P4_SIMPLE
        fc = "against_thesis" if not passed else None
        return {"side": "R_simple", "rate": er["rate"],
                "excluded": er["excluded"],
                "passed": passed, "failure_class": fc}
    if world == "N":
        n = len(rows)
        ok = sum(1 for r in rows if r["R_mix_n_triggers"] == 0)
        rate = _rate(ok, n)
        passed = rate >= TH_P4_MIX
        fc = "against_thesis" if not passed else None
        return {"side": "R_mix", "rate": rate,
                "passed": passed, "failure_class": fc}
    return None

def p5(rows: list[dict], world: str, T: int, k: int):
    """P5 (K): R_declared monotone+conflict; R_sym shortened (k=3)."""
    if world != "K":
        return None
    n = len(rows)
    ok_m = sum(1 for r in rows if r["P5_R_declared_monotone"])
    ok_c = sum(1 for r in rows if r["P5_R_declared_conflict_first_two"])
    rm, rc = _rate(ok_m, n), _rate(ok_c, n)
    passed = rm >= TH_P5_MONOTONE and rc >= TH_P5_CONFLICT
    result: dict = {"rate_monotone": rm, "rate_conflict": rc}
    if k == 3:
        ok_s = sum(1 for r in rows if r["P5_R_sym_shortened"])
        rs = _rate(ok_s, n)
        result["rate_sym"] = rs
        passed = passed and rs >= TH_P5_SYM
    fc = None
    if not passed:
        if rm < TH_P5_MONOTONE or rc < TH_P5_CONFLICT:
            fc = "against_thesis"
        else:
            fc = "instrument_defect"
    result.update(passed=passed, failure_class=fc)
    return result

def p6(rows: list[dict], world: str, T: int, k: int):
    """P6 (V): R_declared zero adj/suspended/reason; R_cross (k=3)."""
    if world != "V":
        return None
    n = len(rows)
    ok_d = sum(1 for r in rows
               if r["P6_R_declared_adj_after_rename"] == 0 and
               r["P6_R_declared_suspended_ok"] and
               r["P6_R_declared_all_reason"])
    rd = _rate(ok_d, n)
    passed = rd >= TH_P6_DECLARED
    result: dict = {"rate_declared": rd}
    if k == 3:
        ok_c = sum(1 for r in rows if r["P6_R_cross_adj_after_rename"] >= 1)
        rc = _rate(ok_c, n)
        result["rate_cross"] = rc
        passed = passed and rc >= TH_P6_CROSS
    fc = None
    if not passed:
        fc = "plugin_defect" if rd < TH_P6_DECLARED else "instrument_defect"
    result.update(passed=passed, failure_class=fc)
    return result

def p7(rows: list[dict], world: str, T: int, k: int):
    """P7 (R): state/returns after redeclaration = 1.00."""
    if world != "R":
        return None
    n = len(rows)
    ok = sum(1 for r in rows
             if r["P7_declared_state_ok"] and r["P7_returns_after_redecl"])
    rate = _rate(ok, n)
    passed = rate >= TH_P7
    fc = "plugin_defect" if not passed else None
    return {"rate": rate, "passed": passed, "failure_class": fc}
