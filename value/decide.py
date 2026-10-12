"""Decision functions for the value grid (Paper 7).
Predictions P1-P6 per cell.  Thresholds from sizing (PREREGISTRO v1 SS8).
Failure classes: against_thesis, instrument_defect, plugin_defect.
"""
from __future__ import annotations
import ast
from adaptive.verdicts import rate_excluding_empty

__all__ = [
    "TH_P1_NORM", "TH_P1_REWARD", "TH_P2_T80", "TH_P2_T160",
    "TH_P2_REWARD", "TH_P3_R", "TH_P3_RPLUS", "TH_P4_CONFLICT",
    "TH_P4_ELECT_T80", "TH_P4_ELECT_T160", "TH_P5_X_NAIVE_T80",
    "TH_P5_X_NAIVE_T160", "TH_P5_XP_T80", "TH_P5_XP_T160",
    "p1", "p2", "p3", "p4", "p5", "p6", "decide",
]

# --- Thresholds from sizing (PREREGISTRO v1 SS8). ---
TH_P1_NORM: float | None = 1.00
TH_P1_REWARD: float | None = 1.00
TH_P2_T80: float | None = 0.80
TH_P2_T160: float | None = 0.95
TH_P2_REWARD: float | None = 1.00
TH_P3_R: float | None = 0.20
TH_P3_RPLUS: float | None = 0.25
TH_P4_CONFLICT: float | None = 1.00
TH_P4_ELECT_T80: float | None = 0.85
TH_P4_ELECT_T160: float | None = 0.95
TH_P5_X_NAIVE_T80: float | None = 0.85
TH_P5_X_NAIVE_T160: float | None = 0.95
TH_P5_XP_T80: float | None = 0.70
TH_P5_XP_T160: float | None = 0.90

FAILURE_CLASSES = ("against_thesis", "instrument_defect", "plugin_defect")


def _check_thresholds():
    nones = [n for n in __all__
             if n.startswith("TH_") and globals()[n] is None]
    if nones:
        raise RuntimeError(
            f"Cannot decide: thresholds not set: {', '.join(nones)}. "
            "Run sizing first.")


def _rate(rows, pred):
    n = len(rows)
    return sum(1 for r in rows if pred(r)) / n if n else 0.0


def p1(rows: list[dict], world: str, T: int) -> dict | None:
    """P1 (N0): R_norm SEM_NORMA 1.00; R_reward judges 1.00."""
    if world != "N0":
        return None
    _check_thresholds()
    rn = _rate(rows, lambda r: r["R_norm_state"] == "SEM_NORMA")
    rr = _rate(rows, lambda r: r["R_reward_elected"] is not None)
    passed = rn >= 1.0 and rr >= 1.0
    fc = ("plugin_defect" if rn < 1.0
          else "instrument_defect" if not passed else None)
    return {"rate_norm": rn, "rate_reward": rr,
            "passed": passed, "failure_class": fc}


def p2(rows: list[dict], world: str, T: int) -> dict | None:
    """P2 (P): R_norm JUSTIFICADO s2 >= TH; R_reward elects s1."""
    if world != "P":
        return None
    _check_thresholds()
    th = TH_P2_T160 if T == 160 else TH_P2_T80
    rn = _rate(rows, lambda r: (r["R_norm_state"] == "JUSTIFICADO"
                                and r["R_norm_elected"] == "s2"))
    rr = _rate(rows, lambda r: r["R_reward_elected"] == "s1")
    passed = rn >= th and rr >= TH_P2_REWARD
    fc = ("against_thesis" if rn < th
          else "instrument_defect" if not passed else None)
    return {"rate_norm": rn, "rate_reward": rr,
            "passed": passed, "failure_class": fc}


def p3(rows: list[dict], world: str, T: int) -> dict | None:
    """P3 (R, R+): pause invariance 1.00; R_infer_value changes >= TH."""
    if world not in ("R", "R+"):
        return None
    _check_thresholds()
    th = TH_P3_RPLUS if world == "R+" else TH_P3_R
    rinv = _rate(rows, lambda r: r["P3_invariant"] is True)
    riv = _rate(rows, lambda r: (
        r["R_infer_value_elected"] != r.get("R_infer_value_no_pause")))
    passed = rinv >= 1.0 and riv >= th
    fc = ("plugin_defect" if rinv < 1.0
          else "instrument_defect" if not passed else None)
    return {"rate_invariant": rinv, "rate_infer_value_changes": riv,
            "passed": passed, "failure_class": fc}


def p4(rows: list[dict], world: str, T: int) -> dict | None:
    """P4 (C0/C1/C2): conflict or elect rates."""
    if world == "C0":
        _check_thresholds()
        rn = _rate(rows, lambda r: r["R_norm_state"] == "EM_CONFLITO")
        rsc = _rate(rows, lambda r: r["R_scalar_elected"] is not None)
        passed = rn >= 1.0 and rsc >= TH_P4_CONFLICT
        fc = ("plugin_defect" if rn < 1.0
              else "instrument_defect" if not passed else None)
        return {"rate_conflict": rn, "rate_scalar": rsc,
                "passed": passed, "failure_class": fc}
    if world in ("C1", "C2"):
        _check_thresholds()
        th = TH_P4_ELECT_T160 if T == 160 else TH_P4_ELECT_T80
        rn = _rate(rows, lambda r: (r["R_norm_state"] == "JUSTIFICADO"
                                    and r["R_norm_elected"] == "s2"))
        passed = rn >= th
        fc = "against_thesis" if not passed else None
        return {"rate_elect": rn, "passed": passed, "failure_class": fc}
    return None


def p5(rows: list[dict], world: str, T: int) -> dict | None:
    """P5 (X, Xp): confounded / protocol."""
    if world == "X":
        _check_thresholds()
        th = TH_P5_X_NAIVE_T160 if T == 160 else TH_P5_X_NAIVE_T80
        ri = _rate(rows, lambda r: r["R_norm_state"] == "INSUFICIENTE")
        rn = _rate(rows, lambda r: (
            r["R_naive_justified"] and r["R_naive_elected"] == "s1"))
        passed = ri >= 1.0 and rn >= th
        fc = ("plugin_defect" if ri < 1.0
              else "instrument_defect" if not passed else None)
        return {"rate_insuf": ri, "rate_naive_s1": rn,
                "passed": passed, "failure_class": fc}
    if world == "Xp":
        _check_thresholds()
        th = TH_P5_XP_T160 if T == 160 else TH_P5_XP_T80
        rn = _rate(rows, lambda r: r["R_norm_state"] == "NÃO_JUSTIFICADO")
        passed = rn >= th
        fc = "against_thesis" if not passed else None
        return {"rate_no_justificado": rn,
                "passed": passed, "failure_class": fc}
    return None


def _parse_par(v):
    if isinstance(v, str) and v:
        return ast.literal_eval(v)
    return v if isinstance(v, dict) else None


def p6(rows: list[dict], world: str, T: int) -> dict | None:
    """P6 (all worlds): five D3 boundaries, each 1.00."""
    _check_thresholds()
    n = len(rows)
    ok = [0, 0, 0, 0, 0]
    for r in rows:
        if r.get("P6_s3_never_elected") is True:
            ok[0] += 1
        on = _parse_par(r.get("P6_layer7_true"))
        off = _parse_par(r.get("P6_layer7_false"))
        if not isinstance(on, dict) or not isinstance(off, dict):
            continue
        if on.get("verdicts") == off.get("verdicts"):
            ok[1] += 1
        el = on.get("electedStrategy")
        s_on, s_off = on.get("exploratory"), off.get("exploratory")
        if (el is not None and s_on is None) or (
                el is None and s_on == s_off):
            ok[2] += 1
        po = on.get("status", {}).get("byProposition", [])
        pf = off.get("status", {}).get("byProposition", [])
        if len(po) == len(pf) and all(
                a.get("status", {}).get("kind")
                == b.get("status", {}).get("kind")
                for a, b in zip(po, pf)):
            ok[3] += 1
        jdg = on.get("judgment", {})
        if not (jdg.get("state") == "EM_CONFLITO" and el is not None):
            ok[4] += 1
    names = ["s3_never", "verdicts_eq", "suggestion_ok",
             "lambda_eq", "no_conflict_elect"]
    rates = {names[i]: ok[i] / n if n else 0.0 for i in range(5)}
    passed = all(v >= 1.0 for v in rates.values())
    fc = "plugin_defect" if not passed else None
    return {"rates": rates, "passed": passed, "failure_class": fc}


def decide(rows: list[dict], world: str, T: int) -> dict:
    """Run all applicable predictions for one cell."""
    _check_thresholds()
    result: dict = {}
    for fn in (p1, p2, p3, p4, p5, p6):
        r = fn(rows, world, T)
        if r is not None:
            result[fn.__name__] = r
    return result
