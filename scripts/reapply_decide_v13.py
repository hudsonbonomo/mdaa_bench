"""P4: Re-apply corrected decide to saved grid rows (v1.3).
No grid re-runs.  Loads CSV rows, applies decide(), compares v1.2 vs v1.3.
Outputs: grid_value_decision_v13.json, grid_collective_decision_v13.json.
"""
from __future__ import annotations
import ast
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V_ROWS = ROOT / "value" / "resultados" / "grid_value_rows.csv"
C_ROWS = ROOT / "collective" / "resultados" / "grid_collective_rows.csv"
V_OLD = ROOT / "value" / "resultados" / "grid_value_decision_v12.json"
C_OLD = ROOT / "collective" / "resultados" / "grid_collective_decision.json"
V_OUT = ROOT / "value" / "resultados" / "grid_value_decision_v13.json"
C_OUT = ROOT / "collective" / "resultados" / "grid_collective_decision_v13.json"


def _conv(v, typ):
    """Convert CSV string to typed value."""
    if v == "" or v is None:
        return None
    if typ == bool:
        return v == "True"
    if typ == int:
        return int(v)
    if typ == float:
        return float(v)
    if typ == "list":
        return ast.literal_eval(v)
    return v


_V_TYPES = {
    "T": int, "seed": int, "cost_checkpoint": int,
    "P3_invariant": bool, "P6_s3_never_elected": bool,
    "R_naive_justified": bool, "R_naive_diff": float,
}

_C_TYPES = {
    "T": int, "seed": int, "n": int, "k": int, "m": int,
    "p": float, "rho": float,
    "Q3_location_ratio": float, "Q3_transfer_ratio": float,
    "Q3_H1_passed": bool, "Q3_borrow_error": bool,
    "Q4_R_mean_in_all_gamma": bool,
    "Q4_R_leastmisery_in_all_gamma": bool,
    "Q4_admissible_empty": bool,
    "Q4_R_group_indeterminate": bool,
    "Q4_R_group_hidden_ok": bool,
    "Q4_R_group_status_quo_ok": bool,
    "Q1_R_own_invariant": bool,
    "Q4_R_group_admissible": "list",
    "Q4_planted_admissible": "list",
    "p_range": "list",
}


def _load_csv(path, types):
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            for k, t in types.items():
                if k in r:
                    r[k] = _conv(r[k], t)
            # Convert empty strings to None for remaining fields
            for k, v in r.items():
                if v == "":
                    r[k] = None
            rows.append(r)
    return rows


def _value_decide(rows):
    import value.decide as D
    from value.worlds import WORLDS
    decision = {}
    T_LEVELS = (80, 160)
    for wn in WORLDS:
        for T in T_LEVELS:
            key = f"{wn}_T{T}"
            cell = [r for r in rows if r["world"] == wn and r["T"] == T]
            if not cell:
                continue
            d = D.decide(cell, wn, T)
            if d:
                decision[key] = d
    return decision


def _coll_decide(rows):
    import collective.decide as D

    def _cell_key(r):
        w = r["world"]
        if w == "O":
            return f"O_k{r.get('k', '?')}"
        if w == "Pn":
            return f"Pn_n{r.get('n', '?')}"
        if w == "Pl":
            return f"Pl_n{r.get('n','?')}_T{r.get('T','?')}_pr{r.get('p_range','?')}"
        if w in ("Pc", "Pw"):
            return f"{w}_n{r.get('n','?')}_T{r.get('T','?')}"
        if w == "G":
            return (f"G_n{r.get('n','?')}_m{r.get('m','?')}"
                    f"_p{r.get('p','?')}_rho{r.get('rho','?')}")
        return None

    def _cell_params(r):
        return {k: r[k] for k in ("n", "T", "k", "m", "p", "rho", "p_range")
                if k in r and r[k] is not None}

    cells: dict[str, list] = {}
    for r in rows:
        ck = _cell_key(r)
        if ck:
            cells.setdefault(ck, []).append(r)
    decision = {}
    for key, cr in cells.items():
        w = key.split("_")[0]
        cp = _cell_params(cr[0])
        d = D.decide(cr, w, **cp)
        if d:
            decision[key] = d
    return decision


def _compare(old_dec, new_dec, broken_sides):
    """Compare v1.2 vs v1.3 verdicts per prediction per cell."""
    all_keys = sorted(set(list(old_dec.keys()) + list(new_dec.keys())))
    result = {}
    for ck in all_keys:
        od = old_dec.get(ck, {})
        nd = new_dec.get(ck, {})
        preds = sorted(set(list(od.keys()) + list(nd.keys())))
        cell_cmp = {}
        for p in preds:
            o = od.get(p, {})
            n = nd.get(p, {})
            entry = {
                "v12_passed": o.get("passed"),
                "v13_passed": n.get("passed"),
                "changed": o.get("passed") != n.get("passed"),
            }
            if p in broken_sides:
                entry["note"] = broken_sides[p]
            cell_cmp[p] = entry
        result[ck] = cell_cmp
    return result


def main():
    # Value
    vrows = _load_csv(V_ROWS, _V_TYPES)
    v_new = _value_decide(vrows)
    v_old_data = json.loads(V_OLD.read_text(encoding="utf-8"))
    v_old = v_old_data.get("decision", v_old_data)
    v_broken = {"p3": "não testado (defeito de instrumento: R_infer_value)"}
    v_cmp = _compare(v_old, v_new, v_broken)
    V_OUT.write_text(
        json.dumps({"comparison_v12_v13": v_cmp,
                     "decision_v13": v_new},
                    indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8")
    print(f"Value: {V_OUT}")

    # Collective
    crows = _load_csv(C_ROWS, _C_TYPES)
    c_new = _coll_decide(crows)
    c_old_data = json.loads(C_OLD.read_text(encoding="utf-8"))
    c_old = c_old_data.get("decision", c_old_data)
    c_broken = {"q3": "não testado (defeito de instrumento: R_pool)"}
    c_cmp = _compare(c_old, c_new, c_broken)
    C_OUT.write_text(
        json.dumps({"comparison_v12_v13": c_cmp,
                     "decision_v13": c_new},
                    indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8")
    print(f"Collective: {C_OUT}")


if __name__ == "__main__":
    main()
