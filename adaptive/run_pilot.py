"""Pilot run for the adaptive bench. PREREGISTRO rascunho v0.5 SS7-8.

Seeds 901-905 ONLY: preregistered as discarded, they never enter a paper result.
Uses control_view: records ONLY control-side rates + thresholds.
No passed, no failure_class, no R_declared rates (except P3b).

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
from . import decide as D
from .verdicts import control_view
from .freeze_check import check_freeze, check_plugin, sha256_lf

PILOT_SEEDS = (901, 902, 903, 904, 905)
OUT_DIR = Path(__file__).resolve().parent / "resultados"
NOTE = ("Sementes-piloto -- descartadas por preregistro. "
        "NAO entram em resultado do paper.")

_P = load_policy()
T_LEVELS = tuple(_P["T"])
K_LEVELS = tuple(_P["rule"]["thresholds"])
_CONTROL_PREDS = [D.p2, D.p3, D.p3b, D.p4, D.p5, D.p6]


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
    for name in ("adjustment-cli.js", "adjustment.js", "standing.js"):
        p = Path(dist) / name
        if p.exists():
            result[name] = sha256_lf(p)
    return result


def run_pilot() -> dict:
    check_freeze()
    check_plugin()
    started = time.time()
    rows: list[dict] = []
    for wn in WORLDS:
        for T in T_LEVELS:
            for k in K_LEVELS:
                for seed in PILOT_SEEDS:
                    d = measure_run(wn, T, k, seed)
                    d.update(world=wn, T=T, k=k, seed=seed)
                    rows.append(d)
    full_decision: dict = {}
    for wn in WORLDS:
        for T in T_LEVELS:
            for k in K_LEVELS:
                key = f"{wn}_T{T}_k{k}"
                cell = [r for r in rows
                        if r["world"] == wn and r["T"] == T and r["k"] == k]
                d = {}
                for fn in _CONTROL_PREDS:
                    r = fn(cell, wn, T, k)
                    if r is not None:
                        d[fn.__name__] = r
                if d:
                    full_decision[key] = d
    controls = control_view(full_decision)
    result = {"seeds": list(PILOT_SEEDS), "note": NOTE,
              "plugin_commit": _plugin_commit(),
              "dist_sha256": _dist_sha256(),
              "controls": controls,
              "elapsed_seconds": round(time.time() - started, 2)}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "pilot_adaptive.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run_pilot(), indent=2, ensure_ascii=False, default=str))
