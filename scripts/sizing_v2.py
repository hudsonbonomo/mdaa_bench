"""Sizing v2: Pw, Pc (collective) and R, R+ (value) with corrected
R_pool and R_infer_value from commit 6e69e69.

Usage (chunks of 75 to avoid timeouts):
  python scripts/sizing_v2.py Pw 300001 300075
  python scripts/sizing_v2.py Pw 300076 300150
  python scripts/sizing_v2.py Pc 300001 300075
  python scripts/sizing_v2.py value 200001 200075
  python scripts/sizing_v2.py analyze
"""
from __future__ import annotations
import json, math, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from collective.freeze_check import check_plugin as check_coll
from collective.worlds import make_world as make_coll, load_policy as load_cp
from collective.readers import read_own_folds
from collective.controls import R_pool_pop, R_H1, _collect_returns
from collective.gates import location_between_within
from adaptive.worlds import load_policy as load_ap
from sim.density import H1_BETWEEN_WITHIN

_CP = load_cp()
_AP = load_ap()
_W0 = int(_AP["declared"]["warrant_window"])
_RULE = {"threshold": 3, "step": int(_AP["rule"]["step"]),
         "minWindow": int(_AP["rule"]["min_window"]),
         "maxWindow": int(_AP["rule"]["max_window"])}
_DELTA = _RULE["step"]
OUT_C = ROOT / "collective" / "resultados"
OUT_V = ROOT / "value" / "resultados"


def _run_pw_chunk(seed_lo, seed_hi):
    """Run Pw sizing for seeds [lo, hi], save per-person fold data."""
    check_coll()
    results = []
    folds_dir = OUT_C / "folds_Pw"
    folds_dir.mkdir(parents=True, exist_ok=True)
    for n in _CP["Pop"]["n"]:
        for T in _CP["Pop"]["T"]:
            for seed in range(seed_lo, seed_hi + 1):
                w = make_coll("Pw", seed=seed, n=n, T=T)
                pf = [read_own_folds(pw) for pw in w.person_worlds]
                loc_ratio = location_between_within(w.person_worlds)
                gate = loc_ratio <= H1_BETWEEN_WITHIN
                h1 = R_H1(w.person_worlds, pf, _RULE, loc_ratio,
                           w0=_W0)
                own_ws = [f[-1].get("window") if f else None
                          for f in pf]
                h1_w = h1.get("window") if gate else None
                labs = w.planted.get("labels", [])
                decay_idx = [i for i, l in enumerate(labs)
                             if l == "fast_decay"]
                stable_idx = [i for i, l in enumerate(labs)
                              if l == "stable"]
                n_worse = (sum(1 for i in decay_idx
                               if own_ws[i] and h1_w is not None
                               and h1_w > own_ws[i])
                           if gate else 0)
                borrow_err = (n_worse > len(decay_idx) / 2
                              if gate and decay_idx else False)
                pool_w = h1.get("window") if gate else None
                row = {
                    "seed": seed, "n": n, "T": T,
                    "H1_passed": gate,
                    "location_ratio": loc_ratio,
                    "borrow_error": borrow_err,
                    "R_H1_window": h1_w,
                    "R_pool_window": pool_w,
                    "R_own_windows": own_ws,
                    "R_own_mean_stable": _mean(
                        [own_ws[i] for i in stable_idx
                         if own_ws[i] is not None]),
                    "R_own_mean_decay": _mean(
                        [own_ws[i] for i in decay_idx
                         if own_ws[i] is not None]),
                }
                results.append(row)
                # Save per-person fold data
                fold_file = (folds_dir /
                    f"folds_n{n}_T{T}_s{seed}.json")
                fold_file.write_text(json.dumps(
                    {"seed": seed, "n": n, "T": T,
                     "labels": labs, "folds": pf},
                    default=str) + "\n", encoding="utf-8")
            print(f"Pw n={n} T={T}: seeds {seed_lo}-{seed_hi}",
                  flush=True)
    out = OUT_C / f"sizing_v2_Pw_{seed_lo}_{seed_hi}.json"
    out.write_text(json.dumps(results, default=str) + "\n",
                   encoding="utf-8")
    print(f"Saved {out.name} ({len(results)} rows)")


def _run_pc_chunk(seed_lo, seed_hi):
    """Run Pc sizing for seeds [lo, hi], save per-person fold data."""
    check_coll()
    results = []
    folds_dir = OUT_C / "folds_Pc"
    folds_dir.mkdir(parents=True, exist_ok=True)
    for n in _CP["Pop"]["n"]:
        for T in _CP["Pop"]["T"]:
            for seed in range(seed_lo, seed_hi + 1):
                w = make_coll("Pc", seed=seed, n=n, T=T)
                pf = [read_own_folds(pw) for pw in w.person_worlds]
                # Pc: find first block where window >= W0 + delta
                target_w = _W0 + _DELTA
                first_blocks = []
                for pi, folds in enumerate(pf):
                    found = None
                    for bi, f in enumerate(folds):
                        if isinstance(f, dict):
                            fw = f.get("window")
                            if fw is not None and fw >= target_w:
                                found = bi
                                break
                    first_blocks.append(found)
                # Also compute R_pool and R_H1 first blocks
                returns = _collect_returns(pf)
                pool_first = None
                run, pw = 0, _W0
                for ri, r in enumerate(returns):
                    kind = r["kind"]
                    if kind == "COUNTED":
                        run += 1
                    elif kind in ("CONFLICT", "CONTRADICTED"):
                        run = 0
                    if run >= _RULE["threshold"] and pw < _RULE["maxWindow"]:
                        pw = min(pw + _RULE["step"], _RULE["maxWindow"])
                        run = 0
                        if pw >= target_w:
                            pool_first = ri
                            break
                loc_ratio = location_between_within(w.person_worlds)
                gate = loc_ratio <= H1_BETWEEN_WITHIN
                h1_first = pool_first if gate else None
                row = {
                    "seed": seed, "n": n, "T": T,
                    "R_own_first_blocks": first_blocks,
                    "R_pool_first_return": pool_first,
                    "R_H1_first_return": h1_first,
                    "H1_passed": gate,
                    "location_ratio": loc_ratio,
                }
                results.append(row)
                fold_file = (folds_dir /
                    f"folds_n{n}_T{T}_s{seed}.json")
                fold_file.write_text(json.dumps(
                    {"seed": seed, "n": n, "T": T,
                     "folds": pf}, default=str) + "\n",
                    encoding="utf-8")
            print(f"Pc n={n} T={T}: seeds {seed_lo}-{seed_hi}",
                  flush=True)
    out = OUT_C / f"sizing_v2_Pc_{seed_lo}_{seed_hi}.json"
    out.write_text(json.dumps(results, default=str) + "\n",
                   encoding="utf-8")
    print(f"Saved {out.name} ({len(results)} rows)")


def _run_value_chunk(seed_lo, seed_hi):
    """Run value R/R+ sizing for seeds [lo, hi]."""
    from value.freeze_check import check_plugin as check_val
    from value.worlds import make_world as make_val
    from value.controls import R_reward, R_infer_value
    from value.measure import _strip_pauses
    check_val()
    results = []
    for T in (80, 160):
        for wn in ("R", "R+"):
            for seed in range(seed_lo, seed_hi + 1):
                w = make_val(wn, T=T, seed=seed)
                rw = R_reward(w)
                iv = R_infer_value(w)
                stripped = _strip_pauses(w)
                iv_np = R_infer_value(stripped)
                # R_norm invariance
                from value.readers import read_judge
                jdg = read_judge(w, ("s1", "s2"))
                jdg_s = read_judge(stripped, ("s1", "s2"))
                p3_inv = (jdg["state"] == jdg_s["state"]
                          and jdg.get("elected") == jdg_s.get("elected"))
                row = {
                    "seed": seed, "T": T, "world": wn,
                    "R_reward_elected": rw["elected"],
                    "R_infer_value_elected": iv["elected"],
                    "R_infer_value_no_pause_elected": iv_np["elected"],
                    "R_infer_value_changes": (
                        iv["elected"] != rw["elected"]),
                    "R_infer_value_no_pause_changes": (
                        iv_np["elected"] != rw["elected"]),
                    "R_norm_state": jdg.get("state"),
                    "R_norm_elected": jdg.get("elected"),
                    "P3_invariant": p3_inv,
                }
                results.append(row)
            print(f"{wn} T={T}: seeds {seed_lo}-{seed_hi}",
                  flush=True)
    out = OUT_V / f"sizing_v2_R_{seed_lo}_{seed_hi}.json"
    out.write_text(json.dumps(results, default=str) + "\n",
                   encoding="utf-8")
    print(f"Saved {out.name} ({len(results)} rows)")


def _mean(lst):
    return sum(lst) / len(lst) if lst else None


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("Usage: python scripts/sizing_v2.py "
              "<Pw|Pc|value|analyze> <seed_lo> <seed_hi>")
        sys.exit(1)
    t0 = time.time()
    cmd = args[0]
    if cmd == "analyze":
        from scripts.sizing_v2_analyze import analyze
        analyze()
    elif cmd in ("Pw", "Pc", "value"):
        lo = int(args[1])
        hi = int(args[2])
        if cmd == "Pw":
            _run_pw_chunk(lo, hi)
        elif cmd == "Pc":
            _run_pc_chunk(lo, hi)
        else:
            _run_value_chunk(lo, hi)
    else:
        print(f"Unknown: {cmd}")
        sys.exit(1)
    print(f"Elapsed: {time.time() - t0:.1f}s")
