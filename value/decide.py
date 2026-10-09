"""Decision functions for the value grid (Paper 7).
Predictions P1-P6 per cell. Thresholds are None until sizing sets them.
The decide() dispatcher REFUSES to run with any threshold still None.
Failure classes: against_thesis, instrument_defect, plugin_defect.
"""
from __future__ import annotations

from adaptive.verdicts import rate_excluding_empty

__all__ = [
    "TH_P1_NORM", "TH_P1_REWARD",
    "TH_P2", "TH_P2_REWARD",
    "TH_P3",
    "TH_P4_CONFLICT", "TH_P4_ELECT",
    "TH_P5_X_NAIVE", "TH_P5_XP",
    "p1", "p2", "p3", "p4", "p5", "p6", "decide",
]

# --- Thresholds: None until sizing. decide() refuses to run with None. ---
TH_P1_NORM: float | None = None      # R_norm SEM_NORMA rate in N0
TH_P1_REWARD: float | None = None    # R_reward judges rate in N0
TH_P2: float | None = None           # R_norm JUSTIFICADO s2 rate in P
TH_P2_REWARD: float | None = None    # R_reward elects s1 rate in P
TH_P3: float | None = None           # R_infer_value changes juizo in R/R+
TH_P4_CONFLICT: float | None = None  # R_norm EM_CONFLITO rate in C0
TH_P4_ELECT: float | None = None     # R_norm elects s2 rate in C1/C2
TH_P5_X_NAIVE: float | None = None   # R_naive justifies s1 in X
TH_P5_XP: float | None = None        # R_norm NAO_JUSTIFICADO rate in Xp

FAILURE_CLASSES = ("against_thesis", "instrument_defect", "plugin_defect")


def _check_thresholds():
    """Refuse to run if any threshold is still None."""
    nones = []
    for name in __all__:
        if name.startswith("TH_") and globals()[name] is None:
            nones.append(name)
    if nones:
        raise RuntimeError(
            f"Cannot decide: thresholds not set: {', '.join(nones)}. "
            "Run sizing first.")


def p1(rows: list[dict], world: str, T: int) -> dict | None:
    """P1 (N0): R_norm SEM_NORMA in 1.00; R_reward judges in 1.00."""
    if world != "N0":
        return None
    _check_thresholds()
    n = len(rows)
    ok_norm = sum(1 for r in rows if r["R_norm_state"] == "SEM_NORMA")
    ok_rw = sum(1 for r in rows if r["R_reward_elected"] is not None)
    rn = ok_norm / n if n else 0.0
    rr = ok_rw / n if n else 0.0
    passed = rn >= 1.0 and rr >= 1.0
    fc = None
    if not passed:
        fc = "plugin_defect" if rn < 1.0 else "instrument_defect"
    return {"rate_norm": rn, "rate_reward": rr,
            "passed": passed, "failure_class": fc}


def p2(rows: list[dict], world: str, T: int) -> dict | None:
    """P2 (P): R_norm JUSTIFICADO s2 >= TH_P2; R_reward elects s1 >= TH_P2'."""
    if world != "P":
        return None
    _check_thresholds()
    n = len(rows)
    ok_norm = sum(1 for r in rows
                  if r["R_norm_state"] == "JUSTIFICADO"
                  and r["R_norm_elected"] == "s2")
    ok_rw = sum(1 for r in rows if r["R_reward_elected"] == "s1")
    rn = ok_norm / n if n else 0.0
    rr = ok_rw / n if n else 0.0
    passed = rn >= TH_P2 and rr >= TH_P2_REWARD
    fc = None
    if not passed:
        fc = "against_thesis" if rn < TH_P2 else "instrument_defect"
    return {"rate_norm": rn, "rate_reward": rr,
            "passed": passed, "failure_class": fc}


def p3(rows: list[dict], world: str, T: int) -> dict | None:
    """P3 (R, R+): pause invariance 1.00; R_infer_value changes >= TH_P3."""
    if world not in ("R", "R+"):
        return None
    _check_thresholds()
    n = len(rows)
    ok_inv = sum(1 for r in rows if r["P3_invariant"] is True)
    rinv = ok_inv / n if n else 0.0
    ok_iv = sum(1 for r in rows
                if r["R_infer_value_elected"] != r.get("R_infer_value_no_pause"))
    riv = ok_iv / n if n else 0.0
    passed = rinv >= 1.0 and riv >= TH_P3
    fc = None
    if not passed:
        fc = "plugin_defect" if rinv < 1.0 else "instrument_defect"
    return {"rate_invariant": rinv, "rate_infer_value_changes": riv,
            "passed": passed, "failure_class": fc}


def p4(rows: list[dict], world: str, T: int) -> dict | None:
    """P4 (C0/C1/C2): conflict/elect rates."""
    if world == "C0":
        _check_thresholds()
        n = len(rows)
        ok = sum(1 for r in rows if r["R_norm_state"] == "EM_CONFLITO")
        rn = ok / n if n else 0.0
        ok_sc = sum(1 for r in rows if r["R_scalar_elected"] is not None)
        rsc = ok_sc / n if n else 0.0
        passed = rn >= 1.0 and rsc >= TH_P4_CONFLICT
        fc = None
        if not passed:
            fc = "plugin_defect" if rn < 1.0 else "instrument_defect"
        return {"rate_conflict": rn, "rate_scalar": rsc,
                "passed": passed, "failure_class": fc}
    if world in ("C1", "C2"):
        _check_thresholds()
        n = len(rows)
        ok = sum(1 for r in rows
                 if r["R_norm_state"] == "JUSTIFICADO"
                 and r["R_norm_elected"] == "s2")
        rn = ok / n if n else 0.0
        passed = rn >= TH_P4_ELECT
        fc = "against_thesis" if not passed else None
        return {"rate_elect": rn,
                "passed": passed, "failure_class": fc}
    return None


def p5(rows: list[dict], world: str, T: int) -> dict | None:
    """P5 (X, Xp): confounded / protocol."""
    if world == "X":
        _check_thresholds()
        n = len(rows)
        ok_insuf = sum(1 for r in rows if r["R_norm_state"] == "INSUFICIENTE")
        ri = ok_insuf / n if n else 0.0
        ok_naive = sum(1 for r in rows
                       if r["R_naive_justified"] and r["R_naive_elected"] == "s1")
        rn = ok_naive / n if n else 0.0
        passed = ri >= 1.0 and rn >= TH_P5_X_NAIVE
        fc = None
        if not passed:
            fc = "plugin_defect" if ri < 1.0 else "instrument_defect"
        return {"rate_insuf": ri, "rate_naive_s1": rn,
                "passed": passed, "failure_class": fc}
    if world == "Xp":
        _check_thresholds()
        n = len(rows)
        ok = sum(1 for r in rows if r["R_norm_state"] == "NAO_JUSTIFICADO")
        rn = ok / n if n else 0.0
        passed = rn >= TH_P5_XP
        fc = "against_thesis" if not passed else None
        return {"rate_no_justificado": rn,
                "passed": passed, "failure_class": fc}
    return None


def p6(rows: list[dict], world: str, T: int) -> dict | None:
    """P6 (all worlds): D3 boundaries, always 1.00."""
    _check_thresholds()
    n = len(rows)
    ok_s3 = sum(1 for r in rows if r.get("P6_s3_never_elected") is True)
    rs3 = ok_s3 / n if n else 0.0
    passed = rs3 >= 1.0
    fc = "plugin_defect" if not passed else None
    return {"rate_s3_never": rs3,
            "passed": passed, "failure_class": fc}


def decide(rows: list[dict], world: str, T: int) -> dict:
    """Run all applicable predictions for one cell."""
    _check_thresholds()
    result: dict = {}
    for fn in (p1, p2, p3, p4, p5, p6):
        r = fn(rows, world, T)
        if r is not None:
            result[fn.__name__] = r
    return result
