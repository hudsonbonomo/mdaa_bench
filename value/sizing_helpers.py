"""Analysis helpers for value/ sizing (step C, plugin readers).
Rates, suggested theta, structurals, costs, X/Xp alternative comparison.
"""
from __future__ import annotations
import math
from scipy.stats import binom


def suggest_theta(rate: float, n_seeds: int = 20) -> float:
    """Largest theta in [0,1] (step 0.05) such that
    P(Binom(n_seeds, rate) >= ceil(n_seeds*theta)) >= 0.80."""
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


def _cell(rows, world, T):
    return [r for r in rows if r["world"] == world and r["T"] == T]


# ---- theta quantities ------------------------------------------------

def theta_rates(rows: list[dict], T_levels) -> dict:
    """Compute theta_2, theta_4p, theta_5p and control thetas."""
    sg: dict = {}
    for T in T_levels:
        # theta_2: JUSTIFICADO with s2 in P
        pc = _cell(rows, "P", T)
        if pc:
            r = _rate(pc, lambda r: (r.get("R_norm_state") == "JUSTIFICADO"
                      and r.get("R_norm_elected") == "s2"))
            sg[f"P_T{T}_theta2_s2_justified"] = {
                "rate": r, "theta": suggest_theta(r)}
        # theta_2' (control): R_reward elects s1
        if pc:
            r = _rate(pc, lambda r: r.get("R_reward_elected") == "s1")
            sg[f"P_T{T}_R_reward_s1"] = {"rate": r, "theta": suggest_theta(r)}
        # theta_4': s2 elected in C1 and C2
        for w in ("C1", "C2"):
            cc = _cell(rows, w, T)
            if cc:
                r = _rate(cc, lambda r: r.get("R_norm_elected") == "s2")
                sg[f"{w}_T{T}_theta4p_s2_elected"] = {
                    "rate": r, "theta": suggest_theta(r)}
        # theta_5': NAO_JUSTIFICADO in Xp
        xp = _cell(rows, "Xp", T)
        if xp:
            r = _rate(xp, lambda r:
                      r.get("R_norm_state") == "NAO_JUSTIFICADO"
                      or r.get("R_norm_state") == "NÃO_JUSTIFICADO")
            sg[f"Xp_T{T}_theta5p_nao_justificado"] = {
                "rate": r, "theta": suggest_theta(r)}
        # theta_4 (C0 control): R_scalar judges
        c0 = _cell(rows, "C0", T)
        if c0:
            r = _rate(c0, lambda r: r.get("R_scalar_elected") is not None)
            sg[f"C0_T{T}_R_scalar_judges"] = {
                "rate": r, "theta": suggest_theta(r)}
        # R_infer_value_changes (R/R+)
        for w in ("R", "R+"):
            rc = _cell(rows, w, T)
            if rc:
                r = _rate(rc, lambda r: r.get("R_infer_value_elected")
                          != r.get("R_reward_elected"))
                sg[f"{w}_T{T}_R_infer_value_changes"] = {
                    "rate": r, "theta": suggest_theta(r)}
        # R_naive_s1 in X (theta_5 control)
        xc = _cell(rows, "X", T)
        if xc:
            r = _rate(xc, lambda r: (r.get("R_naive_justified")
                      and r.get("R_naive_elected") == "s1"))
            sg[f"X_T{T}_R_naive_s1"] = {"rate": r, "theta": suggest_theta(r)}
    return sg


# ---- structurals (expected 1.00) -------------------------------------

def structurals(rows: list[dict], T_levels) -> tuple[dict, list]:
    """Returns (rates_dict, failures_list). failures have seed+cell."""
    rates: dict = {}
    fails: list = []

    for T in T_levels:
        # P1: SEM_NORMA in N0
        n0 = _cell(rows, "N0", T)
        r = _rate(n0, lambda r: r.get("R_norm_state") == "SEM_NORMA")
        rates[f"N0_T{T}_P1_sem_norma"] = r
        for row in n0:
            if row.get("R_norm_state") != "SEM_NORMA":
                fails.append({"cell": f"N0_T{T}", "seed": row["seed"],
                              "field": "P1", "got": row.get("R_norm_state")})

        # P3: invariance in R/R+
        for w in ("R", "R+"):
            rc = _cell(rows, w, T)
            r = _rate(rc, lambda r: r.get("P3_invariant") is True)
            rates[f"{w}_T{T}_P3_invariant"] = r
            for row in rc:
                if row.get("P3_invariant") is not True:
                    fails.append({"cell": f"{w}_T{T}", "seed": row["seed"],
                                  "field": "P3", "got": row.get("P3_invariant")})

        # P5: INSUFICIENTE in X
        xc = _cell(rows, "X", T)
        r = _rate(xc, lambda r: r.get("R_norm_state") == "INSUFICIENTE")
        rates[f"X_T{T}_P5_insuficiente"] = r
        for row in xc:
            if row.get("R_norm_state") != "INSUFICIENTE":
                fails.append({"cell": f"X_T{T}", "seed": row["seed"],
                              "field": "P5", "got": row.get("R_norm_state")})

        # P6: s3 never elected (all worlds)
        for w in ("N0", "P", "R", "R+", "C0", "C1", "C2", "X", "Xp"):
            wc = _cell(rows, w, T)
            r = _rate(wc, lambda r: r.get("P6_s3_never_elected") is True)
            rates[f"{w}_T{T}_P6_s3_never"] = r
            for row in wc:
                if row.get("P6_s3_never_elected") is not True:
                    fails.append({"cell": f"{w}_T{T}", "seed": row["seed"],
                                  "field": "P6_s3", "got": row.get("P6_s3_never_elected")})

    return rates, fails


# ---- gap shift for P3 ------------------------------------------------

def gap_shift_rates(rows: list[dict], T_levels, margin: float) -> dict:
    """R_infer_value_gap_shift: |gap with pauses - gap without| >= margin."""
    sg: dict = {}
    for T in T_levels:
        for w in ("R", "R+"):
            rc = _cell(rows, w, T)
            if not rc:
                continue
            r = _rate(rc, lambda r: r.get("gap_shift", 0) >= margin)
            sg[f"{w}_T{T}_gap_shift_ge_margin"] = {
                "rate": r, "theta": suggest_theta(r)}
    return sg


# ---- costs ------------------------------------------------------------

def cost_summary(rows: list[dict], T_levels) -> dict:
    """Cost = blocks until JUSTIFICADO, for P and Xp."""
    cs: dict = {}
    for T in T_levels:
        for w in ("P", "Xp"):
            wc = _cell(rows, w, T)
            costs = [r.get("cost_checkpoint") for r in wc
                     if r.get("cost_checkpoint") is not None]
            cs[f"{w}_T{T}_cost"] = {
                "n_found": len(costs),
                "n_total": len(wc),
                "mean": sum(costs) / len(costs) if costs else None,
                "min": min(costs) if costs else None,
                "max": max(costs) if costs else None,
            }
    return cs


# ---- alternative X/Xp comparison ------------------------------------

def alt_comparison(current_rows, alt_rows, T_levels) -> dict:
    """Compare R_naive_s1 in X and theta_5p in Xp between param sets."""
    cmp: dict = {}
    for T in T_levels:
        # X: R_naive_s1
        xc_cur = _cell(current_rows, "X", T)
        xc_alt = _cell(alt_rows, "X", T)
        r_cur = _rate(xc_cur, lambda r: (r.get("R_naive_justified")
                      and r.get("R_naive_elected") == "s1"))
        r_alt = _rate(xc_alt, lambda r: (r.get("R_naive_justified")
                      and r.get("R_naive_elected") == "s1"))
        cmp[f"X_T{T}_R_naive_s1"] = {
            "current_0.7_0.4": {"rate": r_cur, "theta": suggest_theta(r_cur)},
            "alt_0.8_0.3": {"rate": r_alt, "theta": suggest_theta(r_alt)},
        }
        # Xp: theta_5p (NAO_JUSTIFICADO)
        xp_cur = _cell(current_rows, "Xp", T)
        xp_alt = _cell(alt_rows, "Xp", T)
        r_cur = _rate(xp_cur, lambda r:
                      r.get("R_norm_state") in
                      ("NAO_JUSTIFICADO", "NÃO_JUSTIFICADO"))
        r_alt = _rate(xp_alt, lambda r:
                      r.get("R_norm_state") in
                      ("NAO_JUSTIFICADO", "NÃO_JUSTIFICADO"))
        cmp[f"Xp_T{T}_theta5p"] = {
            "current_0.7_0.4": {"rate": r_cur, "theta": suggest_theta(r_cur)},
            "alt_0.8_0.3": {"rate": r_alt, "theta": suggest_theta(r_alt)},
        }
    return cmp
