"""Sizing run for the collective bench (Paper 8), step C: plugin readers.

Seeds 300001-300300. Runs all generators AND plugin readers (R_own, R_group).
For each quantity: rate and suggested theta.

Run per-world to stay within timeout:
  python -m collective.run_sizing O Pn Pc Pl Pw G
  python -m collective.run_sizing Pw   # single world (slow for n=20)
  python -m collective.run_sizing analyze

Pop worlds with n=20 may need seed-range splits:
  python -m collective.run_sizing Pw 300001 300100

WRITTEN, NOT EXECUTED. Do not run before check_plugin() passes AND
explicit authorisation from Hudson A. R. Bonomo.
"""
from __future__ import annotations
from pathlib import Path
import json
import sys
import time

from .worlds import WORLDS, load_policy
from .measure import measure_run
from .freeze_check import check_plugin
from .sizing_helpers import (
    suggest_theta, theta_rates, structurals,
    empty_intersection, cost_refusal,
)

_P = load_policy()
SEEDS = tuple(range(
    _P["seeds"]["sizing"][0], _P["seeds"]["sizing"][1] + 1))
OUT_DIR = Path(__file__).resolve().parent / "resultados"


def _world_cells(world_name: str) -> list[dict]:
    """Return list of kw dicts for each cell of a world."""
    if world_name == "O":
        return [{"k": k} for k in _P["O"]["k"]]
    if world_name == "Pn":
        return [{"n": n} for n in _P["Pn"]["n"]]
    if world_name in ("Pc", "Pl", "Pw"):
        return [{"n": n, "T": T}
                for n in _P["Pop"]["n"] for T in _P["Pop"]["T"]]
    if world_name == "G":
        return [{"n": n, "m": _P["G"]["m"], "p": p, "rho": rho}
                for n in _P["G"]["n"]
                for p in _P["G"]["p"]
                for rho in _P["G"]["rho"]]
    return [{}]


def run_world(world_name: str, seed_lo: int | None = None,
              seed_hi: int | None = None) -> list[dict]:
    """Run sizing for one world, all cells and seeds. Save partial."""
    check_plugin()
    seeds = SEEDS
    if seed_lo is not None:
        seeds = tuple(s for s in SEEDS if s >= seed_lo
                      and (seed_hi is None or s <= seed_hi))
    cells = _world_cells(world_name)
    rows: list[dict] = []
    for kw in cells:
        for seed in seeds:
            d = measure_run(world_name, seed, use_plugin=True, **kw)
            rows.append(d)
        desc = " ".join(f"{k}={v}" for k, v in kw.items())
        print(f"{world_name} {desc}: {len(seeds)} seeds done", flush=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = ""
    if seed_lo is not None:
        suffix = f"_{seed_lo}_{seed_hi or 'end'}"
    path = OUT_DIR / f"sizing_plugin_{world_name}{suffix}.json"
    path.write_text(json.dumps(rows, default=str, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"Saved {path.name} ({len(rows)} rows)")
    return rows


def analyze() -> dict:
    """Merge all partials and produce final analysis."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    import glob as gl
    for p in sorted(gl.glob(str(OUT_DIR / "sizing_plugin_*.json"))):
        path = Path(p)
        if path.name == "sizing_collective_step_c.json":
            continue
        rows.extend(json.loads(path.read_text(encoding="utf-8")))
    result: dict = {
        "seeds": list(SEEDS),
        "n_rows": len(rows),
        "thetas": theta_rates(rows, _P),
    }
    sr, sf = structurals(rows, _P)
    result["structurals"] = sr
    result["structural_failures"] = sf
    result["empty_intersection"] = empty_intersection(rows, _P)
    result["cost_refusal"] = cost_refusal(rows, _P)
    (OUT_DIR / "sizing_collective_step_c.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return result


if __name__ == "__main__":
    args = sys.argv[1:] if len(sys.argv) > 1 else list(WORLDS)
    started = time.time()
    for i, arg in enumerate(args):
        if arg == "analyze":
            analyze()
        elif arg in WORLDS:
            lo = int(args[i + 1]) if i + 1 < len(args) and args[i + 1].isdigit() else None
            hi = int(args[i + 2]) if i + 2 < len(args) and args[i + 2].isdigit() else None
            if lo is not None:
                run_world(arg, lo, hi)
                break  # seed range args consumed
            else:
                run_world(arg)
        elif arg.isdigit():
            continue  # consumed by previous world arg
        else:
            print(f"Unknown argument: {arg}", file=sys.stderr)
            sys.exit(1)
    if "analyze" not in args:
        print(f"Elapsed: {time.time() - started:.1f}s")
