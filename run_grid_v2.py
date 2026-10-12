"""Grid v2 — second round (value P3-v2 + collective Q3-v2).

Only v2 cells: R, R+ for value; Pw, Pc for collective.
Seeds 21-40. Saves per-person folds to disk.

WRITTEN, NOT EXECUTED. Do not run before freeze v2 commit AND
explicit authorisation from Hudson A. R. Bonomo.
"""
from __future__ import annotations
from pathlib import Path
import json
import os
import subprocess
import time

from value.worlds import load_policy as load_vp
from value.measure import measure_run as value_measure
from value import decide as VD
from value.freeze_check import check_freeze as vcheck_freeze
from value.freeze_check import check_plugin as vcheck_plugin
from collective.worlds import load_policy as load_cp, make_world
from collective.measure import measure_run as coll_measure
from collective import decide as CD
from collective.readers import read_own_folds
from collective.controls import (
    _collect_returns, apply_adjustment_rule, R_pool_pop,
)
from collective.freeze_check import check_freeze as ccheck_freeze
from collective.freeze_check import check_plugin as ccheck_plugin
from adaptive.worlds import load_policy as load_ap
from adaptive.world_utils import c1_blocks

_VP = load_vp()
_CP = load_cp()
_AP = load_ap()
_BL = int(_AP["stream"]["block_length"])
SEEDS_V2 = tuple(range(21, 41))
V_OUT = Path("value/resultados")
C_OUT = Path("collective/resultados")


def _plugin_commit() -> str:
    dist = os.environ.get("MDAA_PLUGIN_DIST")
    if not dist:
        return "unknown"
    repo = Path(dist).parent
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10)
        return proc.stdout.strip() if proc.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def seq_to_block(s: int) -> int:
    """Map observation seq to c1 block index (0-indexed fold)."""
    if s < _BL:
        return 0
    return (s - _BL) // (2 * _BL) + 1


# ── value v2 ────────────────────────────────────────────────
def _run_value_v2() -> dict:
    rows: list[dict] = []
    for wn in ("R", "R+"):
        for T in _VP["T"]:
            for seed in SEEDS_V2:
                d = value_measure(wn, T, seed, use_plugin=True)
                rows.append(d)
            print(f"value {wn} T={T}: done", flush=True)
    decision: dict = {}
    for wn in ("R", "R+"):
        for T in _VP["T"]:
            key = f"{wn}_T{T}"
            cell = [r for r in rows if r["world"] == wn and r["T"] == T]
            r = VD.p3_v2(cell, wn, T)
            if r is not None:
                decision[key] = {"p3_v2": r}
    return {"rows": rows, "decision": decision}


# ── collective v2 ───────────────────────────────────────────
def _run_collective_v2() -> dict:
    rule = {"threshold": 3, "step": int(_AP["rule"]["step"]),
            "minWindow": int(_AP["rule"]["min_window"]),
            "maxWindow": int(_AP["rule"]["max_window"])}
    w0 = int(_AP["declared"]["warrant_window"])
    pw_rows: list[dict] = []
    pc_rows: list[dict] = []
    for n in _CP["Pop"]["n"]:
        for T in _CP["Pop"]["T"]:
            # Pw
            for seed in SEEDS_V2:
                d = coll_measure("Pw", seed, use_plugin=True, n=n, T=T)
                pw_rows.append(d)
            print(f"coll Pw n={n} T={T}: done", flush=True)
            # Pc — also save folds
            folds_dir = C_OUT / "folds_v2_Pc"
            folds_dir.mkdir(parents=True, exist_ok=True)
            for seed in SEEDS_V2:
                w = make_world("Pc", seed=seed, n=n, T=T)
                d = coll_measure("Pc", seed, use_plugin=True, n=n, T=T)
                # Read folds per person
                pf = [read_own_folds(pw) for pw in w.person_worlds]
                fpath = folds_dir / f"folds_n{n}_T{T}_s{seed}.json"
                fpath.write_text(json.dumps(
                    {"seed": seed, "n": n, "T": T, "folds": pf},
                    default=str, ensure_ascii=False) + "\n",
                    encoding="utf-8")
                # Compute R_pool cost in blocks
                returns = _collect_returns(pf)
                pool_block = _first_extend_block(returns)
                own_blocks = _own_first_blocks(pf)
                d["R_pool_first_block"] = pool_block
                d["R_own_first_blocks"] = own_blocks
                pc_rows.append(d)
            print(f"coll Pc n={n} T={T}: done", flush=True)
    # Pw decision
    decision: dict = {}
    for n in _CP["Pop"]["n"]:
        for T in _CP["Pop"]["T"]:
            key = f"Pw_n{n}_T{T}"
            cell = [r for r in pw_rows
                    if r.get("n") == n and r.get("T") == T]
            r = CD.q3_v2(cell, "Pw", n=n, T=T)
            if r is not None:
                decision[key] = {"q3_v2": r}
    # Pc cost summary
    pc_cost: dict = {}
    for n in _CP["Pop"]["n"]:
        for T in _CP["Pop"]["T"]:
            key = f"Pc_n{n}_T{T}"
            cell = [r for r in pc_rows
                    if r.get("n") == n and r.get("T") == T]
            own = [b for r in cell for b in (r.get("R_own_first_blocks") or [])]
            pool = [r["R_pool_first_block"] for r in cell
                    if r.get("R_pool_first_block") is not None]
            pc_cost[key] = {
                "R_own_mean_block": sum(own) / len(own) if own else None,
                "R_pool_mean_block": sum(pool) / len(pool) if pool else None,
            }
    return {"pw_rows": pw_rows, "pc_rows": pc_rows,
            "decision": decision, "pc_cost": pc_cost}


def _first_extend_block(returns: list[dict]) -> int | None:
    """Block of the return that first pushed window to 50."""
    run, threshold = 0, 3
    for r in returns:
        kind = r["kind"]
        if kind == "COUNTED":
            run += 1
        elif kind in ("CONFLICT", "CONTRADICTED"):
            run = 0
        if run >= threshold:
            return seq_to_block(r["seq"])
    return None


def _own_first_blocks(person_folds: list[list[dict]]) -> list[int | None]:
    """Per person: fold index where window first reaches 50."""
    result: list[int | None] = []
    for pf in person_folds:
        found = None
        for fi, f in enumerate(pf):
            if isinstance(f, dict) and f.get("window", 0) >= 50:
                found = fi
                break
        result.append(found)
    return result


# ── main ────────────────────────────────────────────────────
def main() -> dict:
    vcheck_freeze()
    vcheck_plugin()
    ccheck_freeze()
    ccheck_plugin()
    started = time.time()
    val = _run_value_v2()
    coll = _run_collective_v2()
    V_OUT.mkdir(parents=True, exist_ok=True)
    C_OUT.mkdir(parents=True, exist_ok=True)
    summary = {
        "value_decision": val["decision"],
        "collective_decision": coll["decision"],
        "collective_pc_cost": coll["pc_cost"],
        "seeds": list(SEEDS_V2),
        "plugin_commit": _plugin_commit(),
        "elapsed_seconds": round(time.time() - started, 2),
    }
    (V_OUT / "grid_v2_value.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8")
    (C_OUT / "grid_v2_collective.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8")
    return summary


if __name__ == "__main__":
    main()
