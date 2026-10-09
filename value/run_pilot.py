"""Pilot run for the value bench (Paper 7).

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
T_LEVELS = tuple(_P["T"])


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
    for name in ("value-cli.js", "judgment.js", "norm.js",
                 "standing-cli.js", "status.js"):
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
            for seed in PILOT_SEEDS:
                d = measure_run(wn, T, seed, use_plugin=True)
                rows.append(d)
    controls: dict = {}
    for wn in WORLDS:
        for T in T_LEVELS:
            key = f"{wn}_T{T}"
            cell = [r for r in rows if r["world"] == wn and r["T"] == T]
            c: dict = {}
            if wn == "P":
                s1 = sum(1 for r in cell if r["R_reward_elected"] == "s1")
                c["R_reward_s1_rate"] = s1 / len(cell) if cell else 0
            if wn in ("R", "R+"):
                ch = sum(1 for r in cell
                         if r["R_infer_value_elected"] != r["R_reward_elected"])
                c["R_infer_value_changes_rate"] = ch / len(cell) if cell else 0
            if wn == "C0":
                sc = sum(1 for r in cell if r["R_scalar_elected"] is not None)
                c["R_scalar_judges_rate"] = sc / len(cell) if cell else 0
            if wn == "X":
                nv = sum(1 for r in cell
                         if r["R_naive_justified"] and r["R_naive_elected"] == "s1")
                c["R_naive_s1_rate"] = nv / len(cell) if cell else 0
            if c:
                controls[key] = c
    result = {"seeds": list(PILOT_SEEDS), "note": NOTE,
              "plugin_commit": _plugin_commit(),
              "dist_sha256": _dist_sha256(),
              "controls": controls,
              "elapsed_seconds": round(time.time() - started, 2)}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "pilot_value.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run_pilot(), indent=2, ensure_ascii=False, default=str))
