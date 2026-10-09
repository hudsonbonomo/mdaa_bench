"""Verdicts per prediction, costs. Paper 7.
Aggregates cell-level decisions into per-prediction verdicts.
Reuses rate_excluding_empty from adaptive.verdicts by import.
"""
from __future__ import annotations

from adaptive.verdicts import rate_excluding_empty
from .worlds import WORLDS

__all__ = ["verdicts", "costs"]


_PRED_CELLS = {
    "p1": lambda w, T: w == "N0",
    "p2": lambda w, T: w == "P",
    "p3": lambda w, T: w in ("R", "R+"),
    "p4": lambda w, T: w in ("C0", "C1", "C2"),
    "p5": lambda w, T: w in ("X", "Xp"),
    "p6": lambda w, T: True,
}


def _parse_cell_key(key: str):
    """Parse 'P_T80' -> ('P', 80)."""
    parts = key.rsplit("_T", 1)
    return parts[0], int(parts[1])


def verdicts(decision_by_cell: dict) -> dict:
    """Per-prediction verdict."""
    result: dict = {}
    for pred, filt in _PRED_CELLS.items():
        failed: list[dict] = []
        n_app = 0
        for ck, cd in decision_by_cell.items():
            w, T = _parse_cell_key(ck)
            if not filt(w, T) or pred not in cd:
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
    """Per-cell cost: mean checkpoint to JUSTIFICADO."""
    from collections import defaultdict
    cells: dict[str, list] = defaultdict(list)
    for r in rows:
        cells[f"{r['world']}_T{r['T']}"].append(r)
    result: dict = {}
    for key, cr in cells.items():
        costs_list = [r["cost_checkpoint"] for r in cr
                      if r.get("cost_checkpoint") is not None]
        if costs_list:
            result[key] = {
                "mean_cost": sum(costs_list) / len(costs_list),
                "n_justified": len(costs_list),
                "n_total": len(cr),
            }
    return result
