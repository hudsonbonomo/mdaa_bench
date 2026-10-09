"""The collective grid (Paper 8).

Seeds 1-20. 28 cells x 20 seeds = 560 executions.
Each calls measure_run; writes grid_collective_rows.csv and
grid_collective_decision.json (per-cell, verdicts, costs), plus plugin info.

WRITTEN, NOT EXECUTED. Do not run before the freeze commit AND explicit
authorisation from Hudson A. R. Bonomo.
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
OUT_DIR = Path(__file__).resolve().parent / "resultados"
_PREDS = [D.q1, D.q2, D.q3, D.q4]


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


def run_grid() -> list[dict]:
    rows: list[dict] = []
    for k in _P["O"]["k"]:
        for seed in SEEDS:
            rows.append(measure_run("O", seed, use_plugin=True, k=k))
        print(f"O k={k}: done", flush=True)

    for n in _P["Pn"]["n"]:
        for seed in SEEDS:
            rows.append(measure_run("Pn", seed, use_plugin=True, n=n))
        print(f"Pn n={n}: done", flush=True)

    for wn in _P["Pop"]["worlds"]:
        for n in _P["Pop"]["n"]:
            for T in _P["Pop"]["T"]:
                for seed in SEEDS:
                    rows.append(measure_run(
                        wn, seed, use_plugin=True, n=n, T=T))
                print(f"{wn} n={n} T={T}: done", flush=True)

    for n in _P["G"]["n"]:
        for p in _P["G"]["p"]:
            for rho in _P["G"]["rho"]:
                for seed in SEEDS:
                    rows.append(measure_run(
                        "G", seed, use_plugin=True,
                        n=n, m=_P["G"]["m"], p=p, rho=rho))
                print(f"G n={n} p={p} rho={rho}: done", flush=True)
    return rows


def _decide(rows: list[dict]) -> dict:
    decision: dict = {}
    # Group by cell key
    cells: dict[str, list] = {}
    for r in rows:
        w = r["world"]
        if w == "O":
            key = f"O_k{r.get('k', '?')}"
        elif w == "Pn":
            key = f"Pn_n{r.get('n', '?')}"
        elif w in ("Pc", "Pl", "Pw"):
            key = f"{w}_n{r.get('n', '?')}_T{r.get('T', '?')}"
        elif w == "G":
            key = (f"G_n{r.get('n', '?')}_m{r.get('m', '?')}"
                   f"_p{r.get('p', '?')}_rho{r.get('rho', '?')}")
        else:
            continue
        cells.setdefault(key, []).append(r)

    for key, cell_rows in cells.items():
        w = key.split("_")[0]
        d = {}
        for fn in _PREDS:
            result = fn(cell_rows, w)
            if result is not None:
                d[fn.__name__] = result
        if d:
            decision[key] = d
    return decision


def main() -> dict:
    check_freeze()
    check_plugin()
    started = time.time()
    rows = run_grid()
    decision = _decide(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fields = sorted({k for r in rows for k in r})
    with (OUT_DIR / "grid_collective_rows.csv").open(
            "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    v = _verdicts(decision)
    c = _costs(rows)
    summary = {"decision": decision, "verdicts": v, "costs": c,
               "n_rows": len(rows),
               "worlds": list(WORLDS), "seeds": list(SEEDS),
               "plugin_commit": _plugin_commit(),
               "dist_sha256": _dist_sha256(),
               "elapsed_seconds": round(time.time() - started, 2)}
    (OUT_DIR / "grid_collective_decision.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8")
    return summary


if __name__ == "__main__":
    main()
