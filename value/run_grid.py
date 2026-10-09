"""The value grid (Paper 7).

Seeds 1-20. Readers over 9 worlds x two T = 360 executions (including
X/Xp as pair). Each calls measure_run; writes grid_value_rows.csv and
grid_value_decision.json (per-cell, verdicts, costs), plus plugin info.

WRITTEN, NOT EXECUTED. Do not run before the freeze commit AND explicit
authorisation from Hudson A. R. Bonomo, registered in the execution commit.
"""
from __future__ import annotations
from pathlib import Path
import csv
import json
import os
import subprocess
import time

from .worlds import WORLDS, load_policy
from .measure import measure_run
from . import decide as D
from .verdicts import verdicts as _verdicts, costs as _costs
from .freeze_check import check_freeze, check_plugin
from adaptive.freeze_check import sha256_lf

_P = load_policy()
SEEDS = tuple(range(_P["seeds"]["grid"][0], _P["seeds"]["grid"][1] + 1))
T_LEVELS = tuple(_P["T"])
OUT_DIR = Path(__file__).resolve().parent / "resultados"
_PREDS = [D.p1, D.p2, D.p3, D.p4, D.p5, D.p6]


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


def _check_authorisation() -> None:
    auth = OUT_DIR / "AUTHORISED"
    if not auth.exists():
        raise RuntimeError(
            "Explicit authorisation file not found. Create "
            "value/resultados/AUTHORISED with the commit hash.")


def _decide(rows: list[dict]) -> dict:
    decision: dict = {}
    for wn in WORLDS:
        for T in T_LEVELS:
            key = f"{wn}_T{T}"
            cell = [r for r in rows
                    if r["world"] == wn and r["T"] == T]
            if not cell:
                continue
            d = {}
            for fn in _PREDS:
                r = fn(cell, wn, T)
                if r is not None:
                    d[fn.__name__] = r
            if d:
                decision[key] = d
    return decision


def run_grid() -> list[dict]:
    rows: list[dict] = []
    for wn in WORLDS:
        for T in T_LEVELS:
            for seed in SEEDS:
                d = measure_run(wn, T, seed, use_plugin=True)
                rows.append(d)
            print(f"{wn} T={T}: {len(SEEDS)} seeds", flush=True)
    return rows


def main() -> dict:
    check_freeze()
    check_plugin()
    _check_authorisation()
    started = time.time()
    rows = run_grid()
    decision = _decide(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fields = sorted({k for r in rows for k in r})
    with (OUT_DIR / "grid_value_rows.csv").open(
            "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    v = _verdicts(decision)
    c = _costs(rows)
    summary = {"decision": decision, "verdicts": v, "costs": c,
               "n_rows": len(rows),
               "worlds": list(WORLDS), "T_levels": list(T_LEVELS),
               "seeds": list(SEEDS),
               "plugin_commit": _plugin_commit(),
               "dist_sha256": _dist_sha256(),
               "elapsed_seconds": round(time.time() - started, 2)}
    (OUT_DIR / "grid_value_decision.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8")
    return summary


if __name__ == "__main__":
    main()
