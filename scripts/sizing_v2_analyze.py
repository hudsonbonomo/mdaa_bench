"""Sizing v2 analysis: merge chunks, compute rates, conjunction thetas."""
from __future__ import annotations
import json, math, glob
from pathlib import Path
from scipy.stats import binom

ROOT = Path(__file__).resolve().parent.parent
OUT_C = ROOT / "collective" / "resultados"
OUT_V = ROOT / "value" / "resultados"


def suggest_theta_conjunction(rate, n_grid=20, k=4):
    """Largest theta s.t. P(Binom(n_grid, rate) >= ceil(n_grid*theta))
    >= 0.80^(1/k)."""
    target = 0.80 ** (1 / k)
    best = 0.0
    for num in range(0, n_grid + 1):
        theta = num / n_grid
        ceil_k = math.ceil(n_grid * theta)
        if binom.sf(ceil_k - 1, n_grid, rate) >= target:
            best = theta
    return best


def _power_single(rate, theta, n_grid=20):
    """P(Binom(n_grid, rate) >= ceil(n_grid * theta))."""
    ceil_k = math.ceil(n_grid * theta)
    return float(binom.sf(ceil_k - 1, n_grid, rate))


def _load_chunks(pattern):
    rows = []
    for p in sorted(glob.glob(str(pattern))):
        rows.extend(json.loads(Path(p).read_text(encoding="utf-8")))
    return rows


def _rate(rows, fn):
    ok = sum(1 for r in rows if fn(r))
    return ok / len(rows) if rows else 0.0


def _cell(rows, **match):
    return [r for r in rows
            if all(r.get(k) == v for k, v in match.items())]


def _mean(lst):
    return sum(lst) / len(lst) if lst else None


def analyze():
    # --- Pw ---
    pw_rows = _load_chunks(OUT_C / "sizing_v2_Pw_*.json")
    pw_out = {"cells": {}, "n_total": len(pw_rows)}
    ns = [5, 20]
    Ts = [320, 640]
    for n in ns:
        for T in Ts:
            cell = _cell(pw_rows, n=n, T=T)
            if not cell:
                continue
            h1_rate = _rate(cell, lambda r: r["H1_passed"])
            borrow_rate = _rate(cell, lambda r: r["borrow_error"])
            own_stable = _mean([r["R_own_mean_stable"]
                                for r in cell
                                if r["R_own_mean_stable"] is not None])
            own_decay = _mean([r["R_own_mean_decay"]
                               for r in cell
                               if r["R_own_mean_decay"] is not None])
            pool_ws = [r["R_pool_window"] for r in cell
                       if r["R_pool_window"] is not None]
            h1_ws = [r["R_H1_window"] for r in cell
                     if r["R_H1_window"] is not None]
            key = f"n{n}_T{T}"
            pw_out["cells"][key] = {
                "n_seeds": len(cell),
                "H1_pass_rate": round(h1_rate, 4),
                "borrow_error_rate": round(borrow_rate, 4),
                "R_own_mean_stable": (round(own_stable, 2)
                                      if own_stable else None),
                "R_own_mean_decay": (round(own_decay, 2)
                                     if own_decay else None),
                "R_pool_mean_window": (round(_mean(pool_ws), 2)
                                       if pool_ws else None),
                "R_H1_mean_window": (round(_mean(h1_ws), 2)
                                     if h1_ws else None),
            }
    OUT_C.mkdir(parents=True, exist_ok=True)
    (OUT_C / "sizing_v2_Pw.json").write_text(
        json.dumps(pw_out, indent=2) + "\n", encoding="utf-8")
    print("=== Pw ===")
    print(json.dumps(pw_out, indent=2))

    # --- Pc ---
    pc_rows = _load_chunks(OUT_C / "sizing_v2_Pc_*.json")
    pc_out = {"cells": {}, "n_total": len(pc_rows)}
    for n in ns:
        for T in Ts:
            cell = _cell(pc_rows, n=n, T=T)
            if not cell:
                continue
            # R_own: mean of first_blocks per person
            own_firsts = []
            for r in cell:
                fb = r.get("R_own_first_blocks", [])
                own_firsts.extend([b for b in fb if b is not None])
            pool_firsts = [r["R_pool_first_return"]
                           for r in cell
                           if r["R_pool_first_return"] is not None]
            h1_firsts = [r["R_H1_first_return"]
                         for r in cell
                         if r["R_H1_first_return"] is not None]
            key = f"n{n}_T{T}"
            pc_out["cells"][key] = {
                "n_seeds": len(cell),
                "R_own_mean_first_block": (round(_mean(own_firsts), 2)
                                           if own_firsts else None),
                "R_own_n_found": len(own_firsts),
                "R_pool_mean_first_return": (
                    round(_mean(pool_firsts), 2)
                    if pool_firsts else None),
                "R_pool_n_found": len(pool_firsts),
                "R_H1_mean_first_return": (
                    round(_mean(h1_firsts), 2)
                    if h1_firsts else None),
                "R_H1_n_found": len(h1_firsts),
            }
    (OUT_C / "sizing_v2_Pc.json").write_text(
        json.dumps(pc_out, indent=2) + "\n", encoding="utf-8")
    print("\n=== Pc ===")
    print(json.dumps(pc_out, indent=2))

    # --- Value R/R+ ---
    v_rows = _load_chunks(OUT_V / "sizing_v2_R_*.json")
    v_out = {"cells": {}, "n_total": len(v_rows)}
    for T in (80, 160):
        for wn in ("R", "R+"):
            cell = _cell(v_rows, T=T, world=wn)
            if not cell:
                continue
            iv_rate = _rate(cell, lambda r: r["R_infer_value_changes"])
            iv_np_rate = _rate(cell,
                lambda r: r["R_infer_value_no_pause_changes"])
            p3_rate = _rate(cell,
                lambda r: r.get("P3_invariant") is True)
            key = f"{wn}_T{T}"
            v_out["cells"][key] = {
                "n_seeds": len(cell),
                "R_infer_value_changes_rate": round(iv_rate, 4),
                "R_infer_value_no_pause_changes_rate": round(
                    iv_np_rate, 4),
                "R_norm_invariance_rate": round(p3_rate, 4),
            }
    (OUT_V / "sizing_v2_R.json").write_text(
        json.dumps(v_out, indent=2) + "\n", encoding="utf-8")
    print("\n=== Value R/R+ ===")
    print(json.dumps(v_out, indent=2))

    # --- Conjunction thetas ---
    conj = _conjunction_thetas(pw_out, v_out)
    print("\n=== Conjunction Thetas ===")
    print(json.dumps(conj, indent=2))
    return pw_out, pc_out, v_out, conj


def _conjunction_thetas(pw_out, v_out):
    result = {}
    # theta_3: H1 gate passes in Pw (k=4 cells)
    h1_rates = []
    for key, cell in pw_out.get("cells", {}).items():
        h1_rates.append({"cell": key,
                         "rate": cell["H1_pass_rate"]})
    k = len(h1_rates)
    for r in h1_rates:
        r["theta"] = suggest_theta_conjunction(r["rate"], k=k)
        r["power"] = _power_single(r["rate"], r["theta"])
    conj_power_h1 = math.prod(r["power"] for r in h1_rates) if h1_rates else 0
    result["theta3_H1_passes"] = {
        "k": k, "cells": h1_rates,
        "conjunction_power": round(conj_power_h1, 4)}

    # theta_3': borrowing error in Pw (k=4 cells)
    be_rates = []
    for key, cell in pw_out.get("cells", {}).items():
        be_rates.append({"cell": key,
                         "rate": cell["borrow_error_rate"]})
    k = len(be_rates)
    for r in be_rates:
        r["theta"] = suggest_theta_conjunction(r["rate"], k=k)
        r["power"] = _power_single(r["rate"], r["theta"])
    conj_power_be = math.prod(r["power"] for r in be_rates) if be_rates else 0
    result["theta3p_borrow_error"] = {
        "k": k, "cells": be_rates,
        "conjunction_power": round(conj_power_be, 4)}

    # P3: R_infer_value changes in R/R+ (k=4 cells)
    iv_rates = []
    for key, cell in v_out.get("cells", {}).items():
        iv_rates.append({"cell": key,
                         "rate": cell["R_infer_value_changes_rate"]})
    k = len(iv_rates)
    for r in iv_rates:
        r["theta"] = suggest_theta_conjunction(r["rate"], k=k)
        r["power"] = _power_single(r["rate"], r["theta"])
    conj_power_iv = math.prod(r["power"] for r in iv_rates) if iv_rates else 0
    result["P3_R_infer_value_changes"] = {
        "k": k, "cells": iv_rates,
        "conjunction_power": round(conj_power_iv, 4)}
    return result


if __name__ == "__main__":
    analyze()
