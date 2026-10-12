"""Decision functions for the collective grid (Paper 8).
Predictions Q1-Q4 per cell. Thresholds are None until sizing.
decide() REFUSES to run with any threshold still None.
Failure classes: against_thesis, instrument_defect, plugin_defect.
"""
from __future__ import annotations

from adaptive.verdicts import rate_excluding_empty

__all__ = [
    "TH_Q1_COUNT", "TH_Q2_POOL", "TH_Q3_H1_PASS",
    "TH_Q3_H1_WRONG", "TH_Q3_H1_REFUSE", "TH_Q4_MEAN_OUTSIDE",
    "q1", "q2", "q3", "q4", "decide",
]

FAILURE_CLASSES = ("against_thesis", "instrument_defect", "plugin_defect")

# --- Thresholds from sizing (PREREGISTRO v1 SS8, per-cell). ---
TH_Q1_COUNT: float | None = 1.00      # R_count converts B->T rate in O
TH_Q2_POOL: float | None = 1.00       # R_pool elects rate in Pn

# Q3: per-cell (n, T) thresholds -- Pw
TH_Q3_H1_PASS: dict[tuple, float] | None = {
    (5, 320): 0.95, (5, 640): 1.00,
    (20, 320): 1.00, (20, 640): 1.00,
}
TH_Q3_H1_WRONG: dict[tuple, float] | None = {
    (5, 320): 0.95, (5, 640): 1.00,
    (20, 320): 1.00, (20, 640): 1.00,
}
# Q3: per-cell (n, T) thresholds -- Pl, only p_range [0.05, 0.95]
TH_Q3_H1_REFUSE: dict[tuple, float] | None = {
    (5, 320): 0.70, (5, 640): 0.70,
    (20, 320): 1.00, (20, 640): 1.00,
}
# Q4: per-cell (n, p, rho) thresholds -- G
TH_Q4_MEAN_OUTSIDE: dict[tuple, float] | None = {
    (10, 0.8, 0.0): 0.85, (10, 0.8, 0.5): 0.80,
    (10, 0.9, 0.0): 0.55, (10, 0.9, 0.5): 0.60,
    (30, 0.8, 0.0): 1.00, (30, 0.8, 0.5): 1.00,
    (30, 0.9, 0.0): 1.00, (30, 0.9, 0.5): 1.00,
}


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


def q1(rows: list[dict], world: str, **cell) -> dict | None:
    """Q1 (O): duplicate obs don't change statute. R_count converts B->T."""
    if world != "O":
        return None
    _check_thresholds()
    n = len(rows)
    ok_count = sum(1 for r in rows
                   if r.get("Q1_statute_dup") == "T")
    rate_count = ok_count / n if n else 0.0
    passed = rate_count >= TH_Q1_COUNT
    fc = None
    if not passed:
        fc = "instrument_defect"
    return {"rate_count_T": rate_count,
            "passed": passed, "failure_class": fc}


def q2(rows: list[dict], world: str, **cell) -> dict | None:
    """Q2 (Pn): R_own never elects (1.00). R_pool elects >= TH."""
    if world != "Pn":
        return None
    _check_thresholds()
    n = len(rows)
    ok_own = sum(1 for r in rows
                 if r.get("Q2_R_own_elected") is None)
    rate_own = ok_own / n if n else 0.0
    ok_pool = sum(1 for r in rows
                  if r.get("Q2_R_pool_elected") is not None)
    rate_pool = ok_pool / n if n else 0.0
    passed = rate_own >= 1.0 and rate_pool >= TH_Q2_POOL
    fc = None
    if not passed:
        fc = "plugin_defect" if rate_own < 1.0 else "instrument_defect"
    return {"rate_own_never": rate_own, "rate_pool_elects": rate_pool,
            "passed": passed, "failure_class": fc}


def q3(rows: list[dict], world: str, **cell) -> dict | None:
    """Q3 (Pw/Pl): H1 gate and adjustment correctness."""
    if world not in ("Pw", "Pl"):
        return None
    _check_thresholds()
    key = (cell["n"], cell["T"])
    n = len(rows)
    if world == "Pw":
        if key not in TH_Q3_H1_PASS:
            raise RuntimeError(f"No theta for Q3 H1 pass, cell {key}")
        th_pass = TH_Q3_H1_PASS[key]
        th_wrong = TH_Q3_H1_WRONG[key]
        ok_pass = sum(1 for r in rows
                      if r.get("Q3_location_ratio") is not None
                      and r["Q3_location_ratio"] <= 1.0)
        rate_pass = ok_pass / n if n else 0.0
        pass_ok = rate_pass >= th_pass
        ok_borrow = sum(1 for r in rows if r.get("Q3_borrow_error"))
        rate_borrow = ok_borrow / n if n else 0.0
        borrow_ok = rate_borrow >= th_wrong
        passed = pass_ok and borrow_ok
        fc = ("against_thesis" if not pass_ok
              else "instrument_defect" if not borrow_ok else None)
        return {"rate_H1_passes": rate_pass,
                "rate_borrow_error": rate_borrow,
                "passed": passed, "failure_class": fc}
    else:  # Pl
        if key not in TH_Q3_H1_REFUSE:
            raise RuntimeError(f"No theta for Q3 H1 refuse, cell {key}")
        th_refuse = TH_Q3_H1_REFUSE[key]
        ok_refuse = sum(1 for r in rows
                        if r.get("Q3_location_ratio") is not None
                        and r["Q3_location_ratio"] > 1.0)
        rate_refuse = ok_refuse / n if n else 0.0
        passed = rate_refuse >= th_refuse
        fc = "against_thesis" if not passed else None
        return {"rate_H1_refuses": rate_refuse,
                "passed": passed, "failure_class": fc}


def q4(rows: list[dict], world: str, **cell) -> dict | None:
    """Q4 (G): group intersection correctness."""
    if world != "G":
        return None
    _check_thresholds()
    key = (cell["n"], cell["p"], cell["rho"])
    if key not in TH_Q4_MEAN_OUTSIDE:
        raise RuntimeError(f"No theta for Q4 mean outside, cell {key}")
    th = TH_Q4_MEAN_OUTSIDE[key]
    n = len(rows)
    ok_mean_out = sum(1 for r in rows
                      if r.get("Q4_R_mean_in_all_gamma") is False)
    rate_mean_out = ok_mean_out / n if n else 0.0
    passed = rate_mean_out >= th
    fc = "instrument_defect" if not passed else None
    return {"rate_mean_outside": rate_mean_out,
            "passed": passed, "failure_class": fc}


def decide(rows: list[dict], world: str, **cell) -> dict:
    """Run all applicable predictions for one cell."""
    _check_thresholds()
    result: dict = {}
    for fn in (q1, q2, q3, q4):
        r = fn(rows, world, **cell)
        if r is not None:
            result[fn.__name__] = r
    return result
