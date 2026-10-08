"""Verdicts per prediction, costs, and control_view. PREREGISTRO v0.5 SS8-9.

verdicts(): aggregates cell-level decisions into per-prediction verdicts.
costs(): per-cell cost numbers, no thresholds.
control_view(): pilot-only view with control-side rates and thresholds.
rate_excluding_empty(): shared helper for excluded-seed handling.
"""
from __future__ import annotations

from .decide import (
    TH_P2_SIMPLE_T320, TH_P2_SIMPLE_T640,
    TH_P3_MIX, TH_P3B, TH_P4_SIMPLE, TH_P4_MIX,
    TH_P5_CONFLICT, TH_P5_SYM, TH_P6_CROSS)

__all__ = ["rate_excluding_empty", "verdicts", "costs", "control_view"]


def rate_excluding_empty(rows: list[dict], total_key: str, check_fn) -> dict:
    """Rate excluding seeds with total==0. Shared by decide.py."""
    excluded = ok = counted = 0
    for r in rows:
        if r[total_key] == 0:
            excluded += 1
        else:
            counted += 1
            if check_fn(r):
                ok += 1
    if counted == 0:
        return {"rate": 0.0, "excluded": excluded,
                "n_counted": 0, "all_empty": True}
    return {"rate": ok / counted, "excluded": excluded,
            "n_counted": counted, "all_empty": False}


def _mean_excluding_empty(rows: list[dict], total_key: str, val_fn) -> dict:
    """Mean over seeds with total > 0."""
    excluded = 0
    vals: list[float] = []
    for r in rows:
        if r[total_key] == 0:
            excluded += 1
        else:
            vals.append(val_fn(r))
    if not vals:
        return {"mean": 0.0, "excluded": excluded,
                "n_counted": 0, "all_empty": True}
    return {"mean": sum(vals) / len(vals), "excluded": excluded,
            "n_counted": len(vals), "all_empty": False}


# --- verdicts ---

_PRED_CELLS = {
    "p1": lambda w, T, k: w == "S",
    "p2": lambda w, T, k: w == "N",
    "p3": lambda w, T, k: w == "S" and T == 640,
    "p3b": lambda w, T, k: w == "S" and T == 640,
    "p4": lambda w, T, k: (w == "S" and T == 640) or w == "N",
    "p5": lambda w, T, k: w == "K",
    "p6": lambda w, T, k: w == "V",
    "p7": lambda w, T, k: w == "R",
}


def _parse_cell_key(key: str):
    parts = key.split("_")
    return parts[0], int(parts[1][1:]), int(parts[2][1:])


def verdicts(decision_by_cell: dict) -> dict:
    """Per-prediction verdict. SS9 of PREREGISTRO v0.5."""
    result: dict = {}
    for pred, filt in _PRED_CELLS.items():
        if pred == "p4":
            continue
        failed: list[dict] = []
        n_app = 0
        for ck, cd in decision_by_cell.items():
            w, T, k = _parse_cell_key(ck)
            if not filt(w, T, k) or pred not in cd:
                continue
            n_app += 1
            r = cd[pred]
            if not r.get("passed", True):
                failed.append({"cell": ck,
                               "failure_class": r.get("failure_class")})
        result[pred] = {"passed": n_app > 0 and not failed,
                        "failed_cells": failed}
    result["p4"] = _verdict_p4(decision_by_cell)
    return result


def _verdict_p4(dbc: dict) -> dict:
    """P4: own sides + borrowed from P2 (R_simple in N) and P3 (R_mix)."""
    failed: list[dict] = []
    for ck, cd in dbc.items():
        w, T, k = _parse_cell_key(ck)
        # Own sides
        if ((w == "S" and T == 640) or w == "N") and "p4" in cd:
            if not cd["p4"].get("passed", True):
                failed.append({
                    "cell": ck,
                    "failure_class": cd["p4"].get("failure_class") or "against_thesis",
                    "source": "own"})
        # Borrowed P2: R_simple side in N cells
        if w == "N" and "p2" in cd:
            th = TH_P2_SIMPLE_T640 if T == 640 else TH_P2_SIMPLE_T320
            if cd["p2"].get("rate_simple", 0) < th:
                failed.append({"cell": ck,
                               "failure_class": "instrument_defect",
                               "source": "borrowed_p2"})
        # Borrowed P3: R_mix side in S T=640
        if w == "S" and T == 640 and "p3" in cd:
            n_mix = cd["p3"].get("n_counted_mix", 0)
            if n_mix == 0 or cd["p3"].get("mean_mix", 0.0) > TH_P3_MIX:
                failed.append({"cell": ck,
                               "failure_class": "instrument_defect",
                               "source": "borrowed_p3"})
    return {"passed": not failed, "failed_cells": failed}


# --- costs ---

def costs(rows: list[dict]) -> dict:
    """Per-cell cost numbers. SS8 of PREREGISTRO v0.5."""
    from collections import defaultdict
    cells: dict[str, list] = defaultdict(list)
    for r in rows:
        cells[f"{r['world']}_T{r['T']}_k{r['k']}"].append(r)
    result: dict = {}
    for key, cr in cells.items():
        w = cr[0]["world"]
        n = len(cr)
        if w == "K":
            bd = sum(r.get("cost_B_R_declared", 0) for r in cr) / n
            bf = sum(r.get("cost_B_R_fixed", 0) for r in cr) / n
            result[key] = {"mean_B_R_declared": bd, "mean_B_R_fixed": bf,
                           "mean_B_diff": bd - bf}
        elif w == "V":
            ac = sum(r.get("cost_A_R_cross", 0) for r in cr) / n
            ad = sum(r.get("cost_A_R_declared", 0) for r in cr) / n
            result[key] = {"mean_A_R_cross": ac, "mean_A_R_declared": ad}
    return result


# --- control_view (pilot) ---

def control_view(cell_results: dict) -> dict:
    """Pilot-only view: control-side rates + thresholds. No passed/fc."""
    view: dict = {}
    for ck, preds in cell_results.items():
        _, T, _ = _parse_cell_key(ck)
        cv: dict = {}
        if "p2" in preds:
            th = TH_P2_SIMPLE_T640 if T == 640 else TH_P2_SIMPLE_T320
            cv["p2"] = {"rate_simple": preds["p2"].get("rate_simple"),
                        "threshold": th}
        if "p3" in preds:
            r = preds["p3"]
            cv["p3"] = {"mean_mix": r.get("mean_mix"),
                        "excluded_mix": r.get("excluded_mix"),
                        "threshold": TH_P3_MIX}
        if "p3b" in preds:
            cv["p3b"] = {"rate": preds["p3b"].get("rate"),
                         "threshold": TH_P3B}
        if "p4" in preds:
            r = preds["p4"]
            s = r.get("side")
            th = TH_P4_SIMPLE if s == "R_simple" else TH_P4_MIX
            cv["p4"] = {"side": s, "rate": r.get("rate"), "threshold": th}
        if "p5" in preds:
            r = preds["p5"]
            d: dict = {}
            if "rate_sym" in r:
                d["rate_sym"] = r["rate_sym"]
                d["threshold_sym"] = TH_P5_SYM
            if d:
                cv["p5"] = d
        if "p6" in preds:
            r = preds["p6"]
            if "rate_cross" in r:
                cv["p6"] = {"rate_cross": r["rate_cross"],
                            "threshold_cross": TH_P6_CROSS}
        if cv:
            view[ck] = cv
    return view
