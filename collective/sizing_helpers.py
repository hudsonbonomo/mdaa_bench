"""Analysis helpers for collective/ sizing (step C, plugin readers).
Computes rates, suggested theta, structurals, costs, and empty-rate
comparison from the raw measurement rows.
"""
from __future__ import annotations
import math
from scipy.stats import binom


def suggest_theta(rate: float, n_seeds: int = 20) -> float:
    best = 0.0
    for th_100 in range(0, 101, 5):
        th = th_100 / 100.0
        k = math.ceil(n_seeds * th)
        if binom.sf(k - 1, n_seeds, rate) >= 0.80:
            best = th
    return best


def _rate(rows, check_fn) -> float:
    ok = sum(1 for r in rows if check_fn(r))
    return ok / len(rows) if rows else 0.0


def _cell(rows, world, **match):
    return [r for r in rows if r["world"] == world
            and all(r.get(k) == v for k, v in match.items())]


# ---- theta quantities -----------------------------------------------

def theta_rates(rows: list[dict], policy: dict) -> dict:
    sg: dict = {}
    # theta_3: R_H1 passes gate in Pw
    for n in policy["Pop"]["n"]:
        for T in policy["Pop"]["T"]:
            pw = _cell(rows, "Pw", n=n, T=T)
            if not pw:
                continue
            r = _rate(pw, lambda r: r.get("Q3_H1_passed") is True)
            sg[f"Pw_n{n}_T{T}_theta3_H1_passes"] = {
                "rate": r, "theta": suggest_theta(r)}
            # theta_3': extends window of fast_decay
            r2 = _rate(pw, lambda r: _extends_fast_decay(r))
            sg[f"Pw_n{n}_T{T}_theta3p_extends_fast"] = {
                "rate": r2, "theta": suggest_theta(r2)}

    # theta_3'': R_H1 refuses in Pl
    for n in policy["Pop"]["n"]:
        for T in policy["Pop"]["T"]:
            pl = _cell(rows, "Pl", n=n, T=T)
            if not pl:
                continue
            r = _rate(pl, lambda r: r.get("Q3_H1_passed") is False)
            sg[f"Pl_n{n}_T{T}_theta3pp_H1_refuses"] = {
                "rate": r, "theta": suggest_theta(r)}

    # theta_4: R_mean outside Gamma_i where expected_empty < 0.5
    g_rows = [r for r in rows if r["world"] == "G"]
    low_empty = [r for r in g_rows
                 if r.get("Q4_expected_empty_rate", 1) < 0.5]
    if low_empty:
        r = _rate(low_empty,
                  lambda r: not r.get("Q4_R_mean_in_all_gamma", True))
        sg["G_low_empty_theta4_R_mean_outside"] = {
            "rate": r, "theta": suggest_theta(r),
            "n_cells": len(low_empty)}

    # theta_1 (Q1 control): R_count transforms B into T
    o_rows = [r for r in rows if r["world"] == "O"]
    if o_rows:
        r = _rate(o_rows, lambda r: r.get("Q1_statute_dup") == "T")
        sg["Q1_count_T"] = {"rate": r, "theta": suggest_theta(r)}

    # theta_2 (Q2 control): R_pool elects
    pn_rows = [r for r in rows if r["world"] == "Pn"]
    if pn_rows:
        r = _rate(pn_rows, lambda r: r.get("Q2_R_pool_elected") is not None)
        sg["Q2_pool_elects"] = {"rate": r, "theta": suggest_theta(r)}

    return sg


def _extends_fast_decay(row: dict) -> bool:
    """Check if H1 gate passed AND pooled window > fast_decay windows."""
    if not row.get("Q3_H1_passed"):
        return False
    labels = row.get("Q3_labels", [])
    windows = row.get("Q3_per_person_windows", [])
    h1r = row.get("Q3_H1_result", {})
    pooled_w = h1r.get("window") if isinstance(h1r, dict) else None
    if pooled_w is None or not windows:
        return False
    fast_ws = [w for w, lb in zip(windows, labels)
               if lb == "fast_decay" and w is not None]
    if not fast_ws:
        return False
    return pooled_w > min(fast_ws)


# ---- structurals (expected 1.00) ------------------------------------

def structurals(rows: list[dict], policy: dict) -> tuple[dict, list]:
    rates: dict = {}
    fails: list = []

    # Q1: R_own invariant (dup vs dedup) in O
    o_rows = [r for r in rows if r["world"] == "O"]
    if o_rows:
        r = _rate(o_rows, lambda r: r.get("Q1_R_own_invariant") is True)
        rates["Q1_R_own_invariant"] = r
        for row in o_rows:
            if row.get("Q1_R_own_invariant") is not True:
                fails.append({"cell": f"O_k{row.get('k')}",
                              "seed": row["seed"], "field": "Q1"})

    # Q2: R_own never elected in Pn
    pn_rows = [r for r in rows if r["world"] == "Pn"]
    if pn_rows:
        r = _rate(pn_rows, lambda r: r.get("Q2_R_own_elected") is None)
        rates["Q2_R_own_never_elected"] = r
        for row in pn_rows:
            if row.get("Q2_R_own_elected") is not None:
                fails.append({"cell": f"Pn_n{row.get('n')}",
                              "seed": row["seed"], "field": "Q2"})

    # Q3: R_own no cross adjust in Pop worlds
    for wn in ("Pc", "Pl", "Pw"):
        wc = [r for r in rows if r["world"] == wn]
        if wc:
            r = _rate(wc, lambda r: r.get("Q3_R_own_no_cross_adjust", True))
            rates[f"{wn}_Q3_R_own_no_cross"] = r
            for row in wc:
                if not row.get("Q3_R_own_no_cross_adjust", True):
                    fails.append({"cell": f"{wn}_n{row.get('n')}_T{row.get('T')}",
                                  "seed": row["seed"], "field": "Q3"})

    # Q4: R_group never outside Gamma_i
    g_rows = [r for r in rows if r["world"] == "G"]
    if g_rows:
        plugged = [r for r in g_rows if r.get("Q4_R_group_admissible") is not None]
        if plugged:
            r = _rate(plugged, lambda r: _group_in_gamma(r))
            rates["Q4_R_group_in_gamma"] = r
            for row in plugged:
                if not _group_in_gamma(row):
                    fails.append({"cell": f"G_n{row.get('n')}_p{row.get('p')}_rho{row.get('rho')}",
                                  "seed": row["seed"], "field": "Q4"})
    return rates, fails


def _group_in_gamma(row):
    adm = row.get("Q4_R_group_admissible", [])
    planted = row.get("Q4_planted_admissible", [])
    if not adm:
        return True  # empty admissible = indeterminate, not violation
    return all(a in planted for a in adm)


# ---- empty intersection observed vs expected -------------------------

def empty_intersection(rows: list[dict], policy: dict) -> dict:
    g_rows = [r for r in rows if r["world"] == "G"]
    result: dict = {}
    for n in policy["G"]["n"]:
        for p in policy["G"]["p"]:
            for rho in policy["G"]["rho"]:
                cell = _cell(g_rows, "G", n=n, p=p, rho=rho)
                if not cell:
                    continue
                obs_empty = _rate(cell, lambda r: r.get("Q4_admissible_empty"))
                exp = cell[0].get("Q4_expected_empty_rate", 0)
                key = f"G_n{n}_p{p}_rho{rho}"
                result[key] = {"observed": obs_empty, "expected": exp,
                               "n_seeds": len(cell)}
    return result


# ---- cost of refusal in Pc -------------------------------------------

def cost_refusal(rows: list[dict], policy: dict) -> dict:
    """In Pc, how many more blocks R_own takes vs R_pool."""
    result: dict = {}
    for n in policy["Pop"]["n"]:
        for T in policy["Pop"]["T"]:
            pc = _cell(rows, "Pc", n=n, T=T)
            if not pc:
                continue
            # per-person windows from R_own vs pooled from R_pool
            own_ws = [w for r in pc for w in (r.get("Q3_per_person_windows") or [])
                      if w is not None]
            result[f"Pc_n{n}_T{T}"] = {
                "mean_window": sum(own_ws) / len(own_ws) if own_ws else None,
                "n_persons": len(own_ws), "n_seeds": len(pc)}
    return result
