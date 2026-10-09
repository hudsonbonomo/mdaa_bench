"""Sizing run for the value bench (Paper 7).

Seeds 200001-200300. Runs all generators and ALL readers (controls only,
since plugin thresholds come from the plugin run). For each cell and each
quantity that carries a threshold, records the estimated rate and the
suggested theta: the largest theta such that P(Binom(20, rate) >= ceil(20*theta)) >= 0.80.

Does NOT decide predictions.

WRITTEN, NOT EXECUTED. Do not run before check_plugin() passes AND explicit
authorisation from Hudson A. R. Bonomo, registered in the execution commit.
"""
from __future__ import annotations
from pathlib import Path
import json
import math
import time
from scipy.stats import binom

from .worlds import WORLDS, load_policy
from .measure import measure_run
from .freeze_check import check_plugin

_P = load_policy()
SEEDS = tuple(range(_P["seeds"]["sizing"][0], _P["seeds"]["sizing"][1] + 1))
T_LEVELS = tuple(_P["T"])
OUT_DIR = Path(__file__).resolve().parent / "resultados"


def _suggest_theta(rate: float, n_seeds: int = 20) -> float:
    """Largest theta in [0,1] (step 0.05) such that
    P(Binom(n_seeds, rate) >= ceil(n_seeds*theta)) >= 0.80."""
    best = 0.0
    for th_100 in range(0, 101, 5):
        th = th_100 / 100.0
        k = math.ceil(n_seeds * th)
        if binom.sf(k - 1, n_seeds, rate) >= 0.80:
            best = th
    return best


def _rate_for(rows, key, check_fn) -> float:
    ok = sum(1 for r in rows if check_fn(r))
    return ok / len(rows) if rows else 0.0


def run_sizing() -> dict:
    check_plugin()
    started = time.time()
    rows: list[dict] = []
    for wn in WORLDS:
        for T in T_LEVELS:
            for seed in SEEDS:
                d = measure_run(wn, T, seed, use_plugin=False)
                rows.append(d)
            print(f"{wn} T={T}: {len(SEEDS)} seeds done", flush=True)
    suggestions: dict = {}
    for wn in WORLDS:
        for T in T_LEVELS:
            cell = [r for r in rows if r["world"] == wn and r["T"] == T]
            key = f"{wn}_T{T}"
            s: dict = {}
            if wn == "P":
                rate = _rate_for(cell, "R_reward_elected",
                                 lambda r: r["R_reward_elected"] == "s1")
                s["R_reward_s1"] = {"rate": rate,
                                    "theta": _suggest_theta(rate)}
            if wn in ("R", "R+"):
                rate = _rate_for(cell, "R_infer_value_elected",
                                 lambda r: r["R_infer_value_elected"]
                                 != r["R_reward_elected"])
                s["R_infer_value_changes"] = {"rate": rate,
                                              "theta": _suggest_theta(rate)}
            if wn == "C0":
                rate = _rate_for(cell, "R_scalar_elected",
                                 lambda r: r["R_scalar_elected"] is not None)
                s["R_scalar_judges"] = {"rate": rate,
                                        "theta": _suggest_theta(rate)}
            if wn == "X":
                rate = _rate_for(cell, "R_naive_justified",
                                 lambda r: (r["R_naive_justified"]
                                            and r["R_naive_elected"] == "s1"))
                s["R_naive_s1"] = {"rate": rate,
                                   "theta": _suggest_theta(rate)}
            if s:
                suggestions[key] = s
    result = {"seeds": list(SEEDS), "suggestions": suggestions,
              "n_rows": len(rows),
              "elapsed_seconds": round(time.time() - started, 2)}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "sizing_value.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run_sizing(), indent=2, ensure_ascii=False, default=str))
