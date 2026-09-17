"""Cell-level aggregation of the standing grid: the seven committed predictions.

`metrics.py` measures one run; this measures one CELL (a T x alpha slice over the
20 seeds) and applies the thresholds PREREGISTRO_v1 §7 and emendas v1.2/v1.3
committed to. Thresholds are literals here so that reading them against the
pre-registration is a one-line diff. No I/O, no execution.
"""
from __future__ import annotations

import json

from . import metrics as M
from .pilot_power import cli_sha256, total_variation

__all__ = ["summarise", "confusion_by_arm"]

PREREG = "standing/PREREGISTRO_v1.md (v1 + emendas v1.1, v1.2, v1.3)"


def _by(rows, **sel):
    return [r for r in rows if all(r[k] == v for k, v in sel.items())]


def confusion_by_arm(rows) -> dict:
    out: dict[str, dict[str, int]] = {}
    for r in rows:
        cell = out.setdefault(f"{r['arm']}|T={r['T']}|alpha={r['alpha']}", {})
        for k, v in json.loads(r["confusion_json"]).items():
            cell[k] = cell.get(k, 0) + v
    return {k: v for k, v in out.items() if v}


def _p1(rows, seeds, T, pol) -> tuple[dict, dict]:
    a = {r["seed"]: r for r in _by(rows, arm="A-logged", T=T, alpha=pol)}
    bu = {r["seed"]: r for r in _by(rows, arm="B-unlogged", T=T, alpha=pol)}
    bl = {r["seed"]: r for r in _by(rows, arm="B-logged", T=T, alpha=pol)}
    dist = [M.weight_distance(a[s]["_weight_vector"], bu[s]["_weight_vector"]) for s in seeds]
    tvd_l = [total_variation(a[s]["_nu"], bl[s]["_nu"]) for s in seeds]
    tvd_u = [total_variation(a[s]["_nu"], bu[s]["_nu"]) for s in seeds]
    p1 = {**M.tost(dist), "distance_per_seed": dist}
    p1b = {"mean_tvd_B_logged": float(sum(tvd_l) / len(tvd_l)), "min_tvd_B_logged": min(tvd_l),
           "mean_tvd_B_unlogged": float(sum(tvd_u) / len(tvd_u)),
           "max_tvd_B_unlogged": max(tvd_u),
           "pass": min(tvd_l) >= 0.40 and max(tvd_u) <= 0.05}
    return p1, p1b


def _p2(rows, T, pol) -> dict:
    bl = _by(rows, arm="B-logged", T=T, alpha=pol)
    hits, tot = sum(r["p2_hits"] for r in bl), sum(r["p2_total"] for r in bl)
    return {"hits": hits, "total": tot, "rate": hits / tot if tot else float("nan"),
            "pass": tot > 0 and hits / tot >= 0.95}


def _p3(rows, T, pol) -> dict:
    c = _by(rows, world="C", T=T, alpha=pol)
    nb = sum(1 for r in c if r["sstar_kind"] == "B")
    aged = sum(r["aged_inside_window"] for r in c)
    return {"n": len(c), "n_statute_B": nb, "rate_B": nb / len(c),
            "n_aged_inside_window": aged,
            "order_legible_rate": sum(r["order_legible"] for r in c) / len(c),
            "decay_share_mean": sum(r["decay_better_share"] for r in c) / len(c),
            "decay_decline_rate": sum(1 for r in c if r["decay_better_share"] < 0.5) / len(c),
            "pass": nb / len(c) >= 0.95 and aged == 0}


def _p4(rows, T, pol) -> tuple[dict, dict]:
    d = _by(rows, world="D", T=T, alpha=pol)
    agg = M.prf(sum(r["p4_tp"] for r in d), sum(r["p4_fp"] for r in d),
                sum(r["p4_fn"] for r in d))
    # `pass` follows P4's own wording: unevaluable at >= 0.99 precision and recall
    # AND every branch returning ("todos voltam"). `branch_ok_strict_rate`
    # additionally demands APPLICABLE after a total reconciliation; it is reported,
    # not decided on, because it fails only where the returned block is older than
    # the alpha window — the standing layer working, not the reconciliation failing.
    p4 = {**agg,
          "branches": {b: sum(1 for r in d if r["reconciliation"] == b)
                       for b in ("none", "total", "partial")},
          "returned_ok_rate": sum(1 for r in d if r["p4_returned_ok"]) / len(d),
          "branch_ok_strict_rate": sum(1 for r in d if r["p4_branch_ok"]) / len(d),
          "n_aged_pre_tau1": sum(r["p4_n_aged_pre_tau1"] for r in d),
          "pass": agg["precision"] >= 0.99 and agg["recall"] >= 0.99
          and all(r["p4_returned_ok"] for r in d)}
    p4b = {"n": len(d), "rate": sum(1 for r in d if r["p4b_all_excluded"]) / len(d),
           "pass": all(r["p4b_all_excluded"] for r in d)}
    return p4, p4b


def _p5(rows, seeds, cells) -> dict:
    a_cell = _by(rows, world="A", T=160, alpha="lenient")
    div = [r for r in a_cell if r["p5_divergent"]]
    out = {"cell": "A, T=160, alpha=lenient", "n": len(a_cell), "n_divergent": len(div),
           "divergence_rate": len(div) / len(a_cell),
           "reasons": {x: sum(1 for r in div if r["decl_reason"] == x)
                       for x in sorted({r["decl_reason"] for r in div})},
           "b_blocking_rate": (sum(1 for r in div if r["decl_reason"] == "B_blocking")
                               / len(div)) if div else float("nan"),
           "all_cells_divergence": {
               f"T={T},alpha={p}": sum(1 for r in _by(rows, world="A", T=T, alpha=p)
                                       if r["p5_divergent"]) / len(seeds)
               for T, p in cells}}
    out["pass"] = out["divergence_rate"] >= 0.90 and out["b_blocking_rate"] == 1.0
    return out


def summarise(rows: list[dict], elapsed: float, *, seeds, t_levels, policies,
              arms, replicas) -> dict:
    cells = [(T, pol) for T in t_levels for pol in policies]
    P = {k: {} for k in ("P1", "P1b", "P2", "P3", "P4", "P4b")}
    for T, pol in cells:
        key = f"T={T},alpha={pol}"
        P["P1"][key], P["P1b"][key] = _p1(rows, seeds, T, pol)
        P["P2"][key] = _p2(rows, T, pol)
        P["P3"][key] = _p3(rows, T, pol)
        P["P4"][key], P["P4b"][key] = _p4(rows, T, pol)
    return {"preregistro": PREREG, "cli_sha256": cli_sha256(), "seeds": list(seeds),
            "factors": {"world_arms": arms, "T": list(t_levels),
                        "alpha": list(policies), "replicas": replicas},
            "n_cells": len(arms) * len(cells), "n_rows": len(rows),
            "elapsed_seconds": round(elapsed, 2),
            "confusion_by_arm": confusion_by_arm(rows),
            **P, "P5": _p5(rows, seeds, cells)}
