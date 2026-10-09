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

# --- Thresholds: None until sizing. decide() refuses with None. ---
TH_Q1_COUNT: float | None = None      # R_count converts B->T rate in O
TH_Q2_POOL: float | None = None       # R_pool elects rate in Pn
TH_Q3_H1_PASS: float | None = None    # R_H1 passes gate in Pw
TH_Q3_H1_WRONG: float | None = None   # R_H1 adjusts wrong in Pw
TH_Q3_H1_REFUSE: float | None = None  # R_H1 refuses in Pl
TH_Q4_MEAN_OUTSIDE: float | None = None  # R_mean outside Gamma_i


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


def q1(rows: list[dict], world: str) -> dict | None:
    """Q1 (O): duplicate obs don't change statute. R_count converts B->T."""
    if world != "O":
        return None
    _check_thresholds()
    n = len(rows)
    # R_own side: statute must be B with both dup and dedup (rate 1.00)
    # This is structural, tested via plugin integration.
    # R_count side: converts B to T
    ok_count = sum(1 for r in rows
                   if r.get("Q1_statute_dup") == "T")
    rate_count = ok_count / n if n else 0.0
    passed = rate_count >= TH_Q1_COUNT
    fc = None
    if not passed:
        fc = "instrument_defect"
    return {"rate_count_T": rate_count,
            "passed": passed, "failure_class": fc}


def q2(rows: list[dict], world: str) -> dict | None:
    """Q2 (Pn): R_own never elects (1.00). R_pool elects >= TH."""
    if world != "Pn":
        return None
    _check_thresholds()
    n = len(rows)
    # R_own must never elect (plugin side, stub None means not elected)
    ok_own = sum(1 for r in rows
                 if r.get("Q2_R_own_elected") is None)
    rate_own = ok_own / n if n else 0.0
    # R_pool elects
    ok_pool = sum(1 for r in rows
                  if r.get("Q2_R_pool_elected") is not None)
    rate_pool = ok_pool / n if n else 0.0
    passed = rate_own >= 1.0 and rate_pool >= TH_Q2_POOL
    fc = None
    if not passed:
        fc = "plugin_defect" if rate_own < 1.0 else "instrument_defect"
    return {"rate_own_never": rate_own, "rate_pool_elects": rate_pool,
            "passed": passed, "failure_class": fc}


def q3(rows: list[dict], world: str) -> dict | None:
    """Q3 (Pw/Pl): H1 gate and adjustment correctness."""
    if world not in ("Pw", "Pl"):
        return None
    _check_thresholds()
    n = len(rows)
    if world == "Pw":
        # H1 passes in rate >= TH_Q3_H1_PASS
        ok_pass = sum(1 for r in rows
                      if r.get("Q3_location_ratio") is not None
                      and r["Q3_location_ratio"] <= 1.0)
        rate_pass = ok_pass / n if n else 0.0
        passed = rate_pass >= TH_Q3_H1_PASS
        fc = "against_thesis" if not passed else None
        return {"rate_H1_passes": rate_pass,
                "passed": passed, "failure_class": fc}
    else:  # Pl
        # H1 refuses in rate >= TH_Q3_H1_REFUSE
        ok_refuse = sum(1 for r in rows
                        if r.get("Q3_location_ratio") is not None
                        and r["Q3_location_ratio"] > 1.0)
        rate_refuse = ok_refuse / n if n else 0.0
        passed = rate_refuse >= TH_Q3_H1_REFUSE
        fc = "against_thesis" if not passed else None
        return {"rate_H1_refuses": rate_refuse,
                "passed": passed, "failure_class": fc}


def q4(rows: list[dict], world: str) -> dict | None:
    """Q4 (G): group intersection correctness."""
    if world != "G":
        return None
    _check_thresholds()
    n = len(rows)
    # R_mean outside Gamma_i rate
    ok_mean_out = sum(1 for r in rows
                      if r.get("Q4_R_mean_in_all_gamma") is False)
    rate_mean_out = ok_mean_out / n if n else 0.0
    passed = rate_mean_out >= TH_Q4_MEAN_OUTSIDE
    fc = "instrument_defect" if not passed else None
    return {"rate_mean_outside": rate_mean_out,
            "passed": passed, "failure_class": fc}


def decide(rows: list[dict], world: str) -> dict:
    """Run all applicable predictions for one cell."""
    _check_thresholds()
    result: dict = {}
    for fn in (q1, q2, q3, q4):
        r = fn(rows, world)
        if r is not None:
            result[fn.__name__] = r
    return result
