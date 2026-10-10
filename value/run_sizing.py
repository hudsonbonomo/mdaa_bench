"""Sizing run for the value bench (Paper 7), step C: plugin readers.

Seeds 200001-200300, T in {80, 160}. Runs ALL readers including R_norm
(plugin bridge). For each cell and quantity: rate and suggested theta.
Also: structurals, gap shift (P3), X/Xp alternative params, costs.

Run per-world to stay within timeout:
  python -m value.run_sizing N0 P R R+ C0 C1 C2 X Xp alt
  python -m value.run_sizing P          # single world
  python -m value.run_sizing analyze    # merge partials -> final report

WRITTEN, NOT EXECUTED. Do not run before check_plugin() passes AND
explicit authorisation from Hudson A. R. Bonomo.
"""
from __future__ import annotations
from pathlib import Path
import json
import sys
import time

from .worlds import WORLDS, load_policy
from .worlds_cx import make_X, make_Xp
from .measure import measure_run
from .controls import R_naive
from .freeze_check import check_plugin
from .sizing_helpers import (
    suggest_theta, theta_rates, structurals,
    gap_shift_rates, cost_summary, alt_comparison,
)

_P = load_policy()
SEEDS = tuple(range(_P["seeds"]["sizing"][0], _P["seeds"]["sizing"][1] + 1))
T_LEVELS = tuple(_P["T"])
_MARGIN = float(_P["norm"]["margin"])
OUT_DIR = Path(__file__).resolve().parent / "resultados"


def run_world(world_name: str) -> list[dict]:
    """Run sizing for one world, all T and seeds. Save partial."""
    check_plugin()
    rows: list[dict] = []
    for T in T_LEVELS:
        for seed in SEEDS:
            d = measure_run(world_name, T, seed, use_plugin=True)
            rows.append(d)
        print(f"{world_name} T={T}: {len(SEEDS)} seeds done", flush=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"sizing_plugin_{world_name}.json"
    path.write_text(json.dumps(rows, default=str, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"Saved {path.name} ({len(rows)} rows)")
    return rows


def run_alternative() -> list[dict]:
    """Run X and Xp with alternative retention parameters."""
    check_plugin()
    alt_rows: list[dict] = []
    for T in T_LEVELS:
        for seed in SEEDS:
            # X alternative: only controls (R_naive), no plugin needed
            w_x = make_X(T=T, seed=seed,
                         p_ret_fresh=0.8, p_ret_tired=0.3)
            nv = R_naive(w_x)
            alt_rows.append({
                "world": "X", "T": T, "seed": seed,
                "R_naive_elected": nv["elected"],
                "R_naive_justified": nv["justified"],
                "R_naive_diff": nv["diff"],
            })
            # Xp alternative: plugin judge
            w_xp = make_Xp(T=T, seed=seed,
                           p_ret_fresh=0.8, p_ret_tired=0.3)
            d = measure_run("Xp", T, seed, use_plugin=True,
                            world_override=w_xp)
            alt_rows.append(d)
        print(f"alt X/Xp T={T}: done", flush=True)
    path = OUT_DIR / "sizing_plugin_alt.json"
    path.write_text(
        json.dumps(alt_rows, default=str, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"Saved alt ({len(alt_rows)} rows)")
    return alt_rows


def analyze() -> dict:
    """Merge all partials and produce final analysis."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for wn in WORLDS:
        path = OUT_DIR / f"sizing_plugin_{wn}.json"
        if path.exists():
            rows.extend(json.loads(path.read_text(encoding="utf-8")))
    alt_path = OUT_DIR / "sizing_plugin_alt.json"
    alt_rows = (json.loads(alt_path.read_text(encoding="utf-8"))
                if alt_path.exists() else [])

    result: dict = {
        "seeds": list(SEEDS),
        "n_rows": len(rows),
        "thetas": theta_rates(rows, T_LEVELS),
        "gap_shift": gap_shift_rates(rows, T_LEVELS, _MARGIN),
    }
    struct_rates, struct_fails = structurals(rows, T_LEVELS)
    result["structurals"] = struct_rates
    result["structural_failures"] = struct_fails
    result["costs"] = cost_summary(rows, T_LEVELS)
    if alt_rows:
        result["alt_comparison"] = alt_comparison(rows, alt_rows, T_LEVELS)
    (OUT_DIR / "sizing_value_step_c.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return result


if __name__ == "__main__":
    args = sys.argv[1:] if len(sys.argv) > 1 else list(WORLDS) + ["alt"]
    started = time.time()
    for arg in args:
        if arg == "alt":
            run_alternative()
        elif arg == "analyze":
            analyze()
        elif arg in WORLDS:
            run_world(arg)
        else:
            print(f"Unknown argument: {arg}", file=sys.stderr)
            sys.exit(1)
    if "analyze" not in args:
        print(f"Elapsed: {time.time() - started:.1f}s")
