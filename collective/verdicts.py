"""Verdicts per prediction, costs. Paper 8.
Aggregates cell-level decisions into per-prediction verdicts.
Reuses rate_excluding_empty from adaptive.verdicts by import.
"""
from __future__ import annotations

from adaptive.verdicts import rate_excluding_empty
from .worlds import WORLDS

__all__ = ["verdicts", "costs"]

_PRED_CELLS = {
    "q1": lambda w: w == "O",
    "q2": lambda w: w == "Pn",
    "q3": lambda w: w in ("Pw", "Pl"),
    "q4": lambda w: w == "G",
}


def _parse_cell_key(key: str) -> str:
    """Parse cell key to extract world name.
    Keys are like 'O_k2', 'Pn_n5', 'Pc_n5_T320', 'G_n5_m5_p0.8_rho0.0'.
    """
    return key.split("_")[0]


def verdicts(decision_by_cell: dict) -> dict:
    """Per-prediction verdict."""
    result: dict = {}
    for pred, filt in _PRED_CELLS.items():
        failed: list[dict] = []
        n_app = 0
        for ck, cd in decision_by_cell.items():
            w = _parse_cell_key(ck)
            if not filt(w) or pred not in cd:
                continue
            n_app += 1
            r = cd[pred]
            if not r.get("passed", True):
                failed.append({"cell": ck,
                               "failure_class": r.get("failure_class")})
        result[pred] = {"passed": n_app > 0 and not failed,
                        "failed_cells": failed}
    return result


def costs(rows: list[dict]) -> dict:
    """Per-cell cost: in Pc, first block where window reaches W0+delta."""
    from collections import defaultdict
    cells: dict[str, list] = defaultdict(list)
    for r in rows:
        w = r["world"]
        if w == "Pc":
            cells[f"Pc_n{r.get('n', '?')}_T{r.get('T', '?')}"].append(r)
    result: dict = {}
    for key, cr in cells.items():
        cost_vals = [r.get("Q3_cost_first_extend")
                     for r in cr
                     if r.get("Q3_cost_first_extend") is not None]
        if cost_vals:
            result[key] = {
                "mean_cost": sum(cost_vals) / len(cost_vals),
                "n_with_cost": len(cost_vals),
                "n_total": len(cr),
            }
    return result
