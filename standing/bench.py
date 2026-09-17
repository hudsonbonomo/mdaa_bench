"""The standing grid. PREREGISTRO_v1 §5, with emendas v1.1-v1.3.

Seeds 1-20, authorised by Hudson A. R. Bonomo. Writes
`resultados/grid_v1_rows.csv`, `grid_v1_summary.json`, `grid_v1_predictions.md`.

Factor notes, declared here because the grid instantiates fewer cells than §5's
nominal 64:
  * `logged`/`unlogged` is a factor OF WORLD B (§3). A, C and D record their
    condition by construction and have no such level; running them twice would
    duplicate rows, not add cells.
  * `replicas` in {1, 10}: `make_world` takes no replicas parameter, so world
    generation does not move with it. Same decision as the pilot (pilot_power.py):
    replicas = 1 only.
  * World D's reconciliation is drawn by the generator's own RNG (p = 1/2, then
    total/partial at 1/2 each). `force_reconciliation` is NOT used in the grid.
"""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path

from . import metrics as M
from .aggregate import summarise
from .pilot_power import STANDING_VALUES, nu_distribution
from .readers import R_current, R_decay, R_declared
from .report import write_predictions
from .worlds import make_world

SEEDS = tuple(range(1, 21))
T_LEVELS = (40, 160)
POLICIES = ("strict", "lenient")
REPLICAS = 1
ARMS = (("A", "logged", {}), ("B", "logged", {"logged": True}),
        ("B", "unlogged", {"logged": False}), ("C", "logged", {}), ("D", "logged", {}))
OUT_DIR = Path(__file__).resolve().parent / "resultados"

FIELDS = ["world", "arm", "logging", "T", "alpha", "replicas", "seed", "reconciliation",
          "n_obs", "decl_elected", "decl_reason", "decl_n_warranting", "decl_n_appearing",
          "decl_n_props", "decl_n_conflicts", "decl_APPLICABLE", "decl_OUT_OF_SCOPE",
          "decl_AGED", "decl_UNEVALUABLE", "aged_inside_window", "sstar_kind",
          "n_supporting", "n_contradicting", "supp_seq_min", "supp_seq_max",
          "contra_seq_min", "contra_seq_max", "order_legible", "decay_strategy",
          "decay_better_share", "decay_weight_sstar", "current_strategy",
          "current_counted", "current_excluded", "p2_hits", "p2_total", "p4_tp",
          "p4_fp", "p4_fn", "p4_branch_ok", "p4_returned_ok", "p4_n_aged_pre_tau1",
          "p4_branch_expected", "p4b_all_excluded", "p5_divergent", "confusion_json"]


def run_one(world_name: str, arm: str, kw: dict, T: int, policy: str, seed: int) -> dict:
    """One cell x one seed: three readers over the same world, measured."""
    w = make_world(world_name, T=T, seed=seed, **kw)
    dec, decay, cur = (R_declared(w, policy), R_decay(w, policy), R_current(w, policy))
    prop = M.sstar_proposition(dec.status)
    order = M.order_report(prop)
    p2h, p2t = M.p2_out_of_scope(w, dec.verdicts) if (world_name, arm) == ("B", "logged") \
        else (0, 0)
    p4 = M.p4_unevaluable(w, dec.verdicts) if world_name == "D" else {}
    branch = M.p4_branch(w, dec.verdicts) if world_name == "D" else {}
    mirror = M.p4b_current(w, cur) if world_name == "D" else {}
    reason = M.blocking_reason(dec)
    row = {
        "world": world_name, "arm": f"{world_name}-{arm}", "logging": arm, "T": T,
        "alpha": policy, "replicas": REPLICAS, "seed": seed,
        "reconciliation": w.params.get("reconciliation") or ("none" if world_name == "D" else ""),
        "n_obs": len(w.observations), "decl_elected": dec.strategy or "", "decl_reason": reason,
        "decl_n_warranting": len(dec.raw.get("warrantingIds", [])),
        "decl_n_appearing": len(dec.raw.get("appearingIds", [])),
        "decl_n_props": len((dec.status or {}).get("byProposition") or []),
        "decl_n_conflicts": len((dec.status or {}).get("conflicts") or []),
        "aged_inside_window": M.aged_inside_window(w, dec.verdicts, policy),
        "sstar_kind": order["kind"] or "", "decay_strategy": decay.strategy or "",
        "decay_better_share": decay.raw["weighted_better_share"],
        "decay_weight_sstar": decay.raw["weight_vector"].get("s_star", 0.0),
        "current_strategy": cur.strategy or "",
        "current_counted": cur.summary.get("counted", 0),
        "current_excluded": cur.summary.get("excluded", 0),
        "p2_hits": p2h, "p2_total": p2t,
        "p4_tp": p4.get("tp", ""), "p4_fp": p4.get("fp", ""), "p4_fn": p4.get("fn", ""),
        "p4_branch_ok": branch.get("branch_ok", ""),
        "p4_returned_ok": branch.get("returned_ok", ""),
        "p4_n_aged_pre_tau1": branch.get("n_aged", ""),
        "p4_branch_expected": branch.get("expected", ""),
        "p4b_all_excluded": mirror.get("all_excluded", ""),
        "p5_divergent": bool(decay.strategy is not None and dec.strategy is None),
        "confusion_json": json.dumps(M.confusion(w, dec.verdicts), sort_keys=True),
    }
    row.update({f"decl_{s}": dec.summary.get(s, 0) for s in STANDING_VALUES})
    row.update({k: order[k] for k in ("n_supporting", "n_contradicting", "supp_seq_min",
                                      "supp_seq_max", "contra_seq_min", "contra_seq_max",
                                      "order_legible")})
    row["_weight_vector"] = decay.raw["weight_vector"]
    row["_nu"] = nu_distribution(dec.verdicts)
    return row


def run_grid() -> list[dict]:
    rows = []
    for world_name, arm, kw in ARMS:
        for T in T_LEVELS:
            for policy in POLICIES:
                for seed in SEEDS:
                    rows.append(run_one(world_name, arm, kw, T, policy, seed))
                print(f"{world_name}-{arm} T={T} alpha={policy}: {len(SEEDS)} seeds",
                      flush=True)
    return rows


def main() -> dict:
    started = time.time()
    rows = run_grid()
    summary = summarise(rows, time.time() - started, seeds=SEEDS, t_levels=T_LEVELS,
                        policies=POLICIES, arms=[f"{w}-{a}" for w, a, _ in ARMS],
                        replicas=REPLICAS)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "grid_v1_rows.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    (OUT_DIR / "grid_v1_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8")
    write_predictions(summary, OUT_DIR / "grid_v1_predictions.md")
    return summary


if __name__ == "__main__":
    main()
