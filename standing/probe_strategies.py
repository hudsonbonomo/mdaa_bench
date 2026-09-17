"""SONDA DESCARTAVEL — nao entra em resultado do paper.

Question: do the worlds need TWO strategies for P3/P5 to be testable?

Builds a two-strategy variant of A/B/C/D by pairing every s_star observation with
an s_alt observation that carries THE SAME conditions and a signal drawn from a
DIFFERENT p(BETTER). Interleaved seqs (s_star even, s_alt odd) so both strategies
live in one flow. Nothing here edits worlds.py or readers.py.

Seeds 901-905 (pilot). Grid seeds 1-20 are NOT touched.
"""
from __future__ import annotations
from pathlib import Path
import json
import os
import subprocess
import numpy as np

from .worlds import Observation, StandingWorld, make_world, _draw, NOISE_UNCLEAR
from .readers import R_declared, R_decay, to_payload

SEEDS = (901, 902, 903, 904, 905)
T_VALUES = (40, 160)
POLICIES = ("strict", "lenient")
ALT = "s_alt"
P_ALT = 0.50                       # flat: s_star's schedule is what must differ
HERE = Path(__file__).resolve().parent
DRIVER = HERE / "probe_status_driver.mjs"
OUT = HERE / "resultados"
WORLD_KW = {"A": {}, "B": {"logged": True}, "C": {}, "D": {"force_reconciliation": "total"}}


def two_strategy(world: StandingWorld, seed: int) -> StandingWorld:
    """Same record, twice: s_star as generated, s_alt flat at P_ALT, same conditions."""
    rng = np.random.default_rng(seed + 100_000)
    obs: list[Observation] = []
    for i, o in enumerate(world.observations):
        obs.append(Observation(o.strategy, o.conditions, o.signal, 2 * i))
        obs.append(Observation(ALT, o.conditions, _draw(rng, P_ALT, NOISE_UNCLEAR), 2 * i + 1))
    assert len({o.t for o in obs}) == len(obs), "interleaved seqs must stay unique"
    return StandingWorld(obs, world.vocabulary_events, world.planted,
                         {**world.params, "variant": "two_strategy", "p_alt": P_ALT})


def run_status(payload: dict) -> dict:
    proc = subprocess.run(["node", str(DRIVER)], input=json.dumps(payload),
                          capture_output=True, text=True, timeout=180)
    if proc.returncode != 0:
        raise RuntimeError(f"driver exited {proc.returncode}: {proc.stderr.strip()[:400]}")
    return json.loads(proc.stdout)


def kind_counts(props: list[dict]) -> dict[str, int]:
    out = {"T": 0, "F": 0, "B": 0, "N": 0}
    for p in props:
        out[p["kind"]] += 1
    return out


def by_strategy(props: list[dict]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for p in props:
        d = out.setdefault(p["strategy"], {"T": 0, "F": 0, "B": 0, "N": 0})
        d[p["kind"]] += 1
    return out


def one_run(world: StandingWorld, variant: str, policy: str) -> dict:
    payload = to_payload(world, policy)
    st = run_status(payload)
    dec = R_declared(world, policy)
    decay = R_decay(world, policy)
    props = st["byProposition"]
    return {
        "variant": variant,
        "n_observations": len(world.observations),
        "R_declared": {"strategy": dec.strategy, "summary": dec.summary,
                       "n_warranting": len(dec.raw.get("warrantingIds", [])),
                       "n_appearing": len(dec.raw.get("appearingIds", []))},
        "status": {"elected": st["elected"], "n_warranting": st["nWarranting"],
                   "n_appearing": st["nAppearing"], "n_conflicts": st["nConflicts"],
                   "kind_counts": kind_counts(props), "by_strategy": by_strategy(props),
                   "propositions": props[:12], "n_propositions": len(props)},
        "R_decay": {"strategy": decay.strategy, "tally": decay.raw["tally"],
                    "weighted_better_share": decay.raw["weighted_better_share"]},
    }


def main() -> None:
    if not os.environ.get("MDAA_PLUGIN_DIST"):
        raise EnvironmentError("MDAA_PLUGIN_DIST not set")
    assert set(SEEDS).isdisjoint(range(1, 21)), "grid seeds 1-20 are forbidden here"
    OUT.mkdir(exist_ok=True)
    records = []
    for w in ("A", "B", "C", "D"):
        for T in T_VALUES:
            for seed in SEEDS:
                base = make_world(w, T=T, seed=seed, **WORLD_KW[w])
                two = two_strategy(base, seed)
                for policy in POLICIES:
                    for variant, wo in (("single", base), ("two", two)):
                        rec = {"world": w, "T": T, "policy": policy, "seed": seed}
                        rec.update(one_run(wo, variant, policy))
                        records.append(rec)
                        print(f"{w} T={T} {policy} seed={seed} {variant}: "
                              f"elected={rec['status']['elected']} "
                              f"kinds={rec['status']['kind_counts']} "
                              f"decay={rec['R_decay']['strategy']}", flush=True)
    (OUT / "probe_strategies.json").write_text(json.dumps(
        {"note": "SONDA DESCARTAVEL — nao entra em resultado do paper.",
         "seeds": list(SEEDS), "T_values": list(T_VALUES), "policies": list(POLICIES),
         "p_alt": P_ALT, "world_kwargs": WORLD_KW, "records": records},
        indent=2), encoding="utf-8")
    write_summary(records)


def _row(r: dict) -> str:
    s = r["status"]
    el = s["elected"][0] if s["elected"] else "—"
    bs = "; ".join(f"{k}:{''.join(f'{n}{c}' for c, n in v.items() if n)}"
                   for k, v in s["by_strategy"].items())
    return (f"| {r['world']} | {r['T']} | {r['policy']} | {r['seed']} | {r['variant']} | "
            f"{el} | {r['R_declared']['strategy'] or '—'} | {r['R_decay']['strategy'] or '—'} | "
            f"{s['kind_counts']['T']}/{s['kind_counts']['F']}/{s['kind_counts']['B']}/"
            f"{s['kind_counts']['N']} | {bs} |")


def write_summary(records: list[dict]) -> None:
    lines = ["# probe_strategies — SONDA DESCARTAVEL",
             "",
             "**Nao entra em resultado do paper.** Seeds 901-905 (piloto). "
             "Grid seeds 1-20 nao foram usados.",
             "",
             "`status.elected` vem de `electedStrategy(partition.warranting, ...)` "
             "reproduzindo `recommend.ts` §43-61; `standing-cli.js` NAO expoe a celula "
             "de estatuto, so `partitionByStanding`.",
             "",
             "| world | T | alpha | seed | variant | elected (status) | R_declared.strategy "
             "| R_decay | T/F/B/N | por estrategia |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    lines += [_row(r) for r in records if r["seed"] == SEEDS[0]]
    lines += ["", "## Agregado sobre os 5 seeds", "",
              "| world | T | alpha | variant | elected (contagem) | B por estrategia (media) |",
              "|---|---|---|---|---|---|"]
    keys = sorted({(r["world"], r["T"], r["policy"], r["variant"]) for r in records},
                  key=lambda k: (k[0], k[1], k[2], k[3]))
    for k in keys:
        sub = [r for r in records if (r["world"], r["T"], r["policy"], r["variant"]) == k]
        tally: dict[str, int] = {}
        bmean: dict[str, float] = {}
        for r in sub:
            el = r["status"]["elected"][0] if r["status"]["elected"] else "—"
            tally[el] = tally.get(el, 0) + 1
            for s, d in r["status"]["by_strategy"].items():
                bmean[s] = bmean.get(s, 0.0) + d["B"] / len(sub)
        lines.append(f"| {k[0]} | {k[1]} | {k[2]} | {k[3]} | "
                     + ", ".join(f"{a}×{b}" for a, b in sorted(tally.items())) + " | "
                     + ", ".join(f"{a}:{b:.1f}" for a, b in sorted(bmean.items())) + " |")
    (OUT / "probe_strategies_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
