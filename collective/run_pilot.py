"""Pilot run for the collective bench (Paper 8).

Seeds 901-905 ONLY: preregistered as discarded, never enter a paper result.
Verifies that each control reproves where it should.

WRITTEN, NOT EXECUTED. Do not run before the freeze commit.
"""
from __future__ import annotations
from pathlib import Path
import json
import os
import subprocess
import time

from .worlds import WORLDS, load_policy
from .measure import measure_run
from .freeze_check import check_freeze, check_plugin
from adaptive.freeze_check import sha256_lf

PILOT_SEEDS = (901, 902, 903, 904, 905)
OUT_DIR = Path(__file__).resolve().parent / "resultados"
NOTE = ("Sementes-piloto -- descartadas por preregistro. "
        "NAO entram em resultado do paper.")

_P = load_policy()


def _plugin_commit() -> str:
    dist = os.environ.get("MDAA_PLUGIN_DIST")
    if not dist:
        raise EnvironmentError("MDAA_PLUGIN_DIST not set")
    repo = Path(dist).parent
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10)
        return proc.stdout.strip() if proc.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _dist_sha256() -> dict[str, str]:
    dist = os.environ.get("MDAA_PLUGIN_DIST")
    if not dist:
        raise EnvironmentError("MDAA_PLUGIN_DIST not set")
    result = {}
    for name in ("collective-cli.js", "collective.js", "episode-key.js",
                 "episode-signal.js", "status.js",
                 "adjustment-cli.js", "adjustment.js"):
        p = Path(dist) / name
        if p.exists():
            result[name] = sha256_lf(p)
    return result


def run_pilot() -> dict:
    check_freeze()
    check_plugin()
    started = time.time()
    rows: list[dict] = []

    for k in _P["O"]["k"]:
        for seed in PILOT_SEEDS:
            rows.append(measure_run("O", seed, use_plugin=True, k=k))

    for n in _P["Pn"]["n"]:
        for seed in PILOT_SEEDS:
            rows.append(measure_run("Pn", seed, use_plugin=True, n=n))

    for wn in _P["Pop"]["worlds"]:
        for n in _P["Pop"]["n"]:
            for T in _P["Pop"]["T"]:
                for seed in PILOT_SEEDS:
                    rows.append(measure_run(
                        wn, seed, use_plugin=True, n=n, T=T))

    for n in _P["G"]["n"]:
        for p in _P["G"]["p"]:
            for rho in _P["G"]["rho"]:
                for seed in PILOT_SEEDS:
                    rows.append(measure_run(
                        "G", seed, use_plugin=True,
                        n=n, m=_P["G"]["m"], p=p, rho=rho))

    controls: dict = {}
    o_rows = [r for r in rows if r["world"] == "O"]
    if o_rows:
        ct = sum(1 for r in o_rows if r.get("Q1_statute_dup") == "T")
        controls["O"] = {"R_count_T_rate": ct / len(o_rows)}

    pn_rows = [r for r in rows if r["world"] == "Pn"]
    if pn_rows:
        pe = sum(1 for r in pn_rows
                 if r.get("Q2_R_pool_elected") is not None)
        controls["Pn"] = {"R_pool_elects_rate": pe / len(pn_rows)}

    result = {"seeds": list(PILOT_SEEDS), "note": NOTE,
              "plugin_commit": _plugin_commit(),
              "dist_sha256": _dist_sha256(),
              "controls": controls,
              "elapsed_seconds": round(time.time() - started, 2)}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "pilot_collective.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run_pilot(), indent=2, ensure_ascii=False, default=str))
