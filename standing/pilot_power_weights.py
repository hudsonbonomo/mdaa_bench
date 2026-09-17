"""P1 power on the WEIGHT measure. Emenda v1.2, over the PILOT seeds only.

Emenda v1.2 moved P1 off R_declared and onto R_decay, and off the parecer and
onto the WEIGHTS: the measure is the distance between the vectors of WEIGHTED
SHARE PER STRATEGY at the end of the R_decay tally, world A vs world B
`unlogged`, same seed, cell by cell.

    d(A, B) = max_s | w_A[s] - w_B[s] |,  w[s] = weighted BETTER share of s

With a single strategy in the repertoire the vector has one coordinate and the
distance collapses to |share_A - share_B|, which is what runs here.

Seeds 901-905 ONLY: pilot, preregistered as discarded, never a paper result.
Grid seeds 1-20 are not touched. Nothing here reads `planted`.
"""
from __future__ import annotations
from pathlib import Path
import json
import time

import numpy as np

from .pilot_power import (ALPHA, DELTA, DELTA_SWEEP, BOOTSTRAP_SEED, N_BOOTSTRAP,
                          N_TARGET, PILOT_SEEDS, POLICIES, T_LEVELS, NOTE,
                          cli_sha256, tost_rejects, wilson_ci)
from .readers import R_decay
from .worlds import make_world

OUT_DIR = Path(__file__).resolve().parent / "resultados"


def weight_distance(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """Distance between two weight vectors: the largest per-strategy gap.

    Strategies absent from one side count as share 0 there — a strategy the
    other world never carried is a difference, not a missing value.
    """
    keys = set(vec_a) | set(vec_b)
    if not keys:
        return 0.0
    return float(max(abs(vec_a.get(k, 0.0) - vec_b.get(k, 0.0)) for k in keys))


def run_cell(T: int, policy: str) -> dict:
    """R_decay over world A and world B `unlogged`, same seed, one cell."""
    distances, pairs = [], []
    for seed in PILOT_SEEDS:
        read_a = R_decay(make_world("A", T=T, seed=seed), policy=policy)
        read_b = R_decay(make_world("B", T=T, seed=seed, logged=False), policy=policy)
        vec_a = read_a.raw["weight_vector"]
        vec_b = read_b.raw["weight_vector"]
        distances.append(weight_distance(vec_a, vec_b))
        pairs.append({"seed": seed, "weight_a": vec_a, "weight_b_unlogged": vec_b})
    return {"distance_per_seed": distances,
            "mean_distance": float(np.mean(distances)),
            "max_distance": float(np.max(distances)),
            "weights_per_seed": pairs}


def bootstrap_power(draws: np.ndarray, delta: float) -> float:
    return float(tost_rejects(draws, delta).mean())


def main() -> dict:
    started = time.time()
    cells = {f"T={T},alpha={pol}": run_cell(T, pol)
             for T in T_LEVELS for pol in POLICIES}

    pooled = np.array([v for c in cells.values() for v in c["distance_per_seed"]])
    # R_decay does not read the policy: the alpha factor is inert for this
    # measure and each value appears twice in the pool. Reported both ways so
    # the duplication cannot be mistaken for evidence.
    distinct = np.array([v for k, c in cells.items() if "alpha=strict" in k
                         for v in c["distance_per_seed"]])
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    idx = rng.integers(0, pooled.size, size=(N_BOOTSTRAP, N_TARGET))
    draws = pooled[idx]
    power = bootstrap_power(draws, DELTA)

    rng_d = np.random.default_rng(BOOTSTRAP_SEED)
    idx_d = rng_d.integers(0, distinct.size, size=(N_BOOTSTRAP, N_TARGET))
    power_distinct = bootstrap_power(distinct[idx_d], DELTA)

    sweep, min_delta = {}, None
    for d in DELTA_SWEEP:
        p = bootstrap_power(draws, float(d))
        sweep[f"{d:.2f}"] = p
        if min_delta is None and p >= 0.80:
            min_delta = float(d)

    payload = {
        "measure": "P1 emenda v1.2 — max_s |w_A[s] - w_B_unlogged[s]| over the "
                   "R_decay weighted-BETTER-share vector at end of tally",
        "reader": "R_decay",
        "pilot_seeds": list(PILOT_SEEDS),
        "note": NOTE,
        "cli_sha256": cli_sha256(),
        "factors": {"T": list(T_LEVELS), "alpha": list(POLICIES), "replicas": 1,
                    "alpha_is_inert": "R_decay does not read the standing policy; "
                                      "the two alpha levels give identical values"},
        "measures_by_cell": cells,
        "pooled": {"n_observations": int(pooled.size),
                   "n_distinct": int(distinct.size),
                   "mean_distance": float(pooled.mean()),
                   "sd_distance": float(pooled.std(ddof=1)),
                   "max_distance": float(pooled.max())},
        "power_analysis": {
            "delta": DELTA, "alpha": ALPHA, "n_target": N_TARGET,
            "n_bootstrap": N_BOOTSTRAP, "bootstrap_seed": BOOTSTRAP_SEED,
            "power_weight_distance": power,
            "power_weight_distance_distinct_only": power_distinct,
            "power_ci95_montecarlo": wilson_ci(power, N_BOOTSTRAP),
            "min_delta_for_080": min_delta,
            "delta_sweep_power": sweep,
            "caveat": "5 sementes-piloto: o bootstrap reamostra 5 valores observados "
                      "por celula, entao o intervalo e erro de Monte Carlo do "
                      "reamostrador, nao incerteza amostral do piloto.",
        },
        "elapsed_seconds": round(time.time() - started, 2),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "pilot_power_weights.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    out = main()
    print(json.dumps({"pooled": out["pooled"],
                      "power_analysis": {k: v for k, v in out["power_analysis"].items()
                                         if k != "delta_sweep_power"}},
                     indent=2, ensure_ascii=False))
