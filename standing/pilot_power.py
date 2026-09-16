"""P1 power analysis over the PILOT seeds. PREREGISTRO_v1 §7.

P1 asserts equivalence: B `unlogged` == A for R_declared, on two measures,
cell by cell — (1) total variation distance between the nu distributions and
(2) disagreement rate between pareceres. Equivalence is declared when both fall
below Delta by TOST, alpha = 0.05.

This script runs ONLY seeds 901-905. They are pilot seeds: preregistered as
discarded, they never enter a paper result. Grid seeds 1-20 are not touched.

Factors covered: T in {40, 160} x alpha in {strict, lenient}. The `replicas`
factor of §5 is intra-person and `make_world` takes no such parameter — world
generation does not move with it, so the pilot runs replicas = 1 only.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import os
import time

import numpy as np
from scipy import stats

from .readers import R_declared
from .worlds import make_world

PILOT_SEEDS = (901, 902, 903, 904, 905)
T_LEVELS = (40, 160)
POLICIES = ("strict", "lenient")
STANDING_VALUES = ("APPLICABLE", "OUT_OF_SCOPE", "AGED", "UNEVALUABLE")

DELTA = 0.10
ALPHA = 0.05
N_TARGET = 20
N_BOOTSTRAP = 10_000
BOOTSTRAP_SEED = 20260916          # analysis-side seed; never a world seed
DELTA_SWEEP = np.round(np.arange(0.05, 0.5001, 0.01), 2)

OUT_DIR = Path(__file__).resolve().parent / "resultados"
NOTE = ("Sementes-piloto — descartadas por preregistro (§5). "
        "NAO entram em resultado do paper.")


def cli_sha256() -> str:
    dist = os.environ.get("MDAA_PLUGIN_DIST")
    if not dist:
        raise EnvironmentError("MDAA_PLUGIN_DIST not set")
    return hashlib.sha256((Path(dist) / "standing-cli.js").read_bytes()).hexdigest()


def nu_distribution(verdicts: dict[str, str]) -> np.ndarray:
    """Normalised counts over the four standing values. PREREGISTRO_v1 §6."""
    counts = np.array([sum(1 for v in verdicts.values() if v == s)
                       for s in STANDING_VALUES], dtype=float)
    total = counts.sum()
    return counts / total if total else counts


def total_variation(p: np.ndarray, q: np.ndarray) -> float:
    return float(0.5 * np.abs(p - q).sum())


def parecer(result) -> tuple:
    """The appraisal compared across readings: winning strategy and the summary."""
    return (result.strategy,
            tuple(sorted((k, int(v)) for k, v in result.summary.items())))


def run_cell(T: int, policy: str) -> dict:
    """R_declared over world A and world B `unlogged`, same seed, one cell."""
    tvd, disagreement = [], []
    for seed in PILOT_SEEDS:
        read_a = R_declared(make_world("A", T=T, seed=seed), policy=policy)
        read_b = R_declared(make_world("B", T=T, seed=seed, logged=False),
                            policy=policy)
        tvd.append(total_variation(nu_distribution(read_a.verdicts),
                                   nu_distribution(read_b.verdicts)))
        disagreement.append(0.0 if parecer(read_a) == parecer(read_b) else 1.0)
    return {"tvd_per_seed": tvd,
            "disagreement_per_seed": disagreement,
            "mean_tvd": float(np.mean(tvd)),
            "mean_disagreement": float(np.mean(disagreement))}


def tost_rejects(samples: np.ndarray, delta: float,
                 alpha: float = ALPHA) -> np.ndarray:
    """Two one-sided t-tests of H0: |theta| >= delta, one per row of `samples`.

    Reject (declare equivalence) when both p < alpha/2. A degenerate row (zero
    variance) has no t statistic; the decision is then exact and taken on the
    mean alone, which is the limit of the test as the variance goes to zero.
    """
    x = np.atleast_2d(samples)
    n = x.shape[1]
    mean = x.mean(axis=1)
    se = x.std(axis=1, ddof=1) / np.sqrt(n)
    degenerate = se == 0.0
    safe = np.where(degenerate, 1.0, se)
    df = n - 1
    p_lower = np.where(degenerate, np.where(mean > -delta, 0.0, 1.0),
                       stats.t.sf((mean + delta) / safe, df))
    p_upper = np.where(degenerate, np.where(mean < delta, 0.0, 1.0),
                       stats.t.cdf((mean - delta) / safe, df))
    return (p_lower < alpha / 2) & (p_upper < alpha / 2)


def bootstrap_power(tvd_draws: np.ndarray, dis_draws: np.ndarray,
                    delta: float) -> tuple[float, float, float]:
    """TOST over pre-drawn resamples of n = 20.

    Both measures ride the SAME resample indices, so `power_both` is the joint
    decision of one bench and not the product of two independent ones.
    """
    rej_t = tost_rejects(tvd_draws, delta)
    rej_d = tost_rejects(dis_draws, delta)
    return (float(rej_t.mean()), float(rej_d.mean()),
            float((rej_t & rej_d).mean()))


def wilson_ci(hits: float, n: int, z: float = 1.96) -> list[float]:
    """95% interval on a bootstrap proportion. Monte-Carlo error only."""
    if n == 0:
        return [float("nan"), float("nan")]
    centre = (hits + z * z / (2 * n)) / (1 + z * z / n)
    half = (z / (1 + z * z / n)) * np.sqrt(hits * (1 - hits) / n + z * z / (4 * n * n))
    return [float(max(0.0, centre - half)), float(min(1.0, centre + half))]


def main() -> dict:
    started = time.time()
    sha = cli_sha256()
    cells = {f"T={T},alpha={pol}": run_cell(T, pol)
             for T in T_LEVELS for pol in POLICIES}

    tvd = np.array([v for c in cells.values() for v in c["tvd_per_seed"]])
    dis = np.array([v for c in cells.values() for v in c["disagreement_per_seed"]])
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    idx = rng.integers(0, tvd.size, size=(N_BOOTSTRAP, N_TARGET))
    tvd_draws, dis_draws = tvd[idx], dis[idx]
    p_tvd, p_dis, p_both = bootstrap_power(tvd_draws, dis_draws, DELTA)

    sweep = {}
    min_delta = None
    for d in DELTA_SWEEP:
        _, _, both = bootstrap_power(tvd_draws, dis_draws, float(d))
        sweep[f"{d:.2f}"] = both
        if min_delta is None and both >= 0.80:
            min_delta = float(d)

    payload = {
        "pilot_seeds": list(PILOT_SEEDS),
        "note": NOTE,
        "cli_sha256": sha,
        "cli_commit": "f25caa0",
        "factors": {"T": list(T_LEVELS), "alpha": list(POLICIES), "replicas": 1,
                    "replicas_note": "make_world takes no replicas parameter; "
                                     "world generation does not move with it"},
        "measures_by_cell": cells,
        "pooled": {"n_observations": int(tvd.size),
                   "mean_tvd": float(tvd.mean()),
                   "mean_disagreement": float(dis.mean()),
                   "sd_tvd": float(tvd.std(ddof=1)),
                   "sd_disagreement": float(dis.std(ddof=1))},
        "power_analysis": {
            "delta": DELTA, "alpha": ALPHA, "n_target": N_TARGET,
            "n_bootstrap": N_BOOTSTRAP, "bootstrap_seed": BOOTSTRAP_SEED,
            "power_tvd": p_tvd, "power_disagreement": p_dis, "power_both": p_both,
            "power_both_ci95_montecarlo": wilson_ci(p_both, N_BOOTSTRAP),
            "min_delta_for_080": min_delta,
            "delta_sweep_power_both": sweep,
            "caveat": "5 sementes-piloto: o bootstrap reamostra 5 valores "
                      "observados, entao o intervalo e erro de Monte Carlo do "
                      "reamostrador, nao incerteza amostral do piloto.",
        },
        "elapsed_seconds": round(time.time() - started, 2),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "pilot_power.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(main()["power_analysis"], indent=2, ensure_ascii=False))
