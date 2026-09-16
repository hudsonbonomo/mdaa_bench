"""Positive control for the P1 measures. PILOT ONLY — discardable.

The pilot (pilot_power.py) found TVD = 0.00 and disagreement = 0.00 for A vs
B `unlogged` in every cell. Equivalence is only informative if the SAME two
measures can separate worlds that must separate. This script runs them on:

  A vs C           positive control, main      — must differ (aging vs step drop)
  A vs B logged    positive control, secondary — must differ (scope comes apart)
  A vs A, seed+1   negative control            — small but nonzero (noise only)

Same cells as the pilot: seeds 901-905, T in {40, 160}, alpha in {strict,
lenient}. Nothing here touches grid seeds 1-20. Measures are imported from
pilot_power, not reimplemented: a control that redefines the measure controls
nothing.
"""
from __future__ import annotations
from pathlib import Path
import json
import time

import numpy as np

from .pilot_power import (PILOT_SEEDS, POLICIES, STANDING_VALUES, T_LEVELS,
                          cli_sha256, nu_distribution, parecer, total_variation)
from .readers import R_declared
from .worlds import make_world

OUT_DIR = Path(__file__).resolve().parent / "resultados"
NOTE = ("Controle positivo — piloto, descartavel. Testa se as medidas de P1 "
        "distinguem mundos que devem diferir.")
PAIRED_SEEDS = tuple(zip(PILOT_SEEDS, PILOT_SEEDS[1:]))     # 901-902 ... 904-905


def counts(verdicts: dict[str, str]) -> dict[str, int]:
    """Raw nu counts over the four standing values — the evidence, not the ratio."""
    return {s: sum(1 for v in verdicts.values() if v == s) for s in STANDING_VALUES}


def measure(read_1, read_2) -> tuple[float, float]:
    """The two P1 measures, exactly as the pilot computes them."""
    tvd = total_variation(nu_distribution(read_1.verdicts),
                          nu_distribution(read_2.verdicts))
    return tvd, (0.0 if parecer(read_1) == parecer(read_2) else 1.0)


def _read(world: str, T: int, seed: int, policy: str, **kw):
    return R_declared(make_world(world, T=T, seed=seed, **kw), policy=policy)


def run_cell(pair: str, T: int, policy: str) -> dict:
    """One cell of one pair, over the five pilot seeds."""
    tvd, dis, raw, strategies = [], [], {}, {}
    for seed in PILOT_SEEDS:
        if pair == "A_vs_C":
            key, r1, r2 = str(seed), _read("A", T, seed, policy), _read("C", T, seed, policy)
            left, right = "A", "C"
        elif pair == "A_vs_B_logged":
            key, r1 = str(seed), _read("A", T, seed, policy)
            r2 = _read("B", T, seed, policy, logged=True)
            left, right = "A", "B_logged"
        else:                                   # A_vs_A_diff_seed — paired seeds
            match = [p for p in PAIRED_SEEDS if p[0] == seed]
            if not match:
                continue                        # 905 has no successor in the pilot
            s1, s2 = match[0]
            key = f"{s1}_vs_{s2}"
            r1, r2 = _read("A", T, s1, policy), _read("A", T, s2, policy)
            left, right = f"A_seed{s1}", f"A_seed{s2}"
        t, d = measure(r1, r2)
        tvd.append(t)
        dis.append(d)
        raw[key] = {left: counts(r1.verdicts), right: counts(r2.verdicts)}
        strategies[key] = {left: r1.strategy, right: r2.strategy}
    return {"tvd_per_seed": tvd, "disagreement_per_seed": dis,
            "mean_tvd": float(np.mean(tvd)), "mean_disagreement": float(np.mean(dis)),
            "raw_distributions": raw, "strategies": strategies}


def run_pair(pair: str) -> dict:
    return {"cells": {f"T={T},alpha={pol}": run_cell(pair, T, pol)
                      for T in T_LEVELS for pol in POLICIES}}


def _all_tvd(pair: dict) -> list[float]:
    return [v for c in pair["cells"].values() for v in c["tvd_per_seed"]]


def _all_dis(pair: dict) -> list[float]:
    return [v for c in pair["cells"].values() for v in c["disagreement_per_seed"]]


def diagnose(pairs: dict) -> tuple[str, str]:
    """Blind when the positive controls do not move. Diagnosis reads the raw counts."""
    ac, ab = pairs["A_vs_C"], pairs["A_vs_B_logged"]
    ac_flat, ab_flat = _all_tvd(ac) + _all_dis(ac), _all_tvd(ab) + _all_dis(ab)
    ac_dead, ab_dead = max(ac_flat) == 0.0, max(ab_flat) == 0.0
    aa = _all_tvd(pairs["A_vs_A_diff_seed"]) + _all_dis(pairs["A_vs_A_diff_seed"])

    # Evidence 1: are the nu counts literally identical where TVD is zero?
    identical = []
    for name, pair in (("A_vs_C", ac), ("A_vs_B_logged", ab)):
        for cell, data in pair["cells"].items():
            for key, dist in data["raw_distributions"].items():
                a, b = list(dist.values())
                identical.append((name, cell, key, a == b))
    ident_ac = all(ok for n, _, _, ok in identical if n == "A_vs_C")
    # Evidence 2: does the winning strategy ever vary?
    strats = {s for pair in pairs.values() for c in pair["cells"].values()
              for row in c["strategies"].values() for s in row.values()}

    if not ac_dead:
        return "not_blind", (
            f"A vs C separa: TVD max = {max(_all_tvd(ac)):.4f}, desacordo medio = "
            f"{float(np.mean(_all_dis(ac))):.4f}. As medidas de P1 movem quando os "
            f"mundos diferem, entao o zero do piloto (A vs B unlogged) e resultado, "
            f"nao cegueira. Controle negativo A vs A (semente vizinha): TVD max = "
            f"{max(_all_tvd(pairs['A_vs_A_diff_seed'])):.4f}.")

    parts = [f"A vs C da 0.00 nas duas medidas em todas as {len(ac_flat)//2} "
             f"observacoes: o controle positivo principal nao separa."]
    if ident_ac:
        parts.append("As contagens brutas de nu sao IDENTICAS entre A e C em toda "
                     "celula e semente — nu nao le o sinal (BETTER/WORSE/UNCLEAR). "
                     "A e C so diferem no sinal: mesma condicao {'env':'stable'}, "
                     "mesma estrategia s_star, nenhum evento de vocabulario. "
                     "Logo nu depende so de escopo e idade, e as duas medidas sao "
                     "cegas a qualquer mundo que mova apenas a trajetoria.")
    if len(strats) <= 1:
        parts.append(f"A estrategia vencedora e sempre {strats or {None}} — ha um "
                     "unico alvo s_star, entao o primeiro componente do parecer nao "
                     "pode discordar; o desacordo herda so o resumo de nu.")
    parts.append("A vs B logged " + ("TAMBEM da 0.00" if ab_dead else
                 f"separa (TVD max = {max(_all_tvd(ab)):.4f})") +
                 ", e o controle negativo A vs A (semente vizinha) da TVD max = "
                 f"{max(aa[:len(aa)//2]) if aa else float('nan'):.4f}.")
    return "blind", " ".join(parts)


def main() -> dict:
    started = time.time()
    pairs = {name: run_pair(name)
             for name in ("A_vs_C", "A_vs_B_logged", "A_vs_A_diff_seed")}
    verdict, diagnosis = diagnose(pairs)
    payload = {
        "pilot_seeds": list(PILOT_SEEDS),
        "note": NOTE,
        "cli_sha256": cli_sha256(),
        "factors": {"T": list(T_LEVELS), "alpha": list(POLICIES)},
        "paired_seeds_negative_control": [list(p) for p in PAIRED_SEEDS],
        "pairs": pairs,
        "verdict": verdict,
        "diagnosis": diagnosis,
        "elapsed_seconds": round(time.time() - started, 2),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "positive_control.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_summary(payload)
    return payload


def write_summary(payload: dict) -> None:
    lines = ["# Controle positivo das medidas de P1", "",
             f"- Sementes-piloto: {list(PILOT_SEEDS)} (descartaveis; grade 1-20 intocada)",
             f"- CLI sha256: `{payload['cli_sha256']}`",
             f"- Veredito: **{payload['verdict']}**", "",
             "| Par | Celula | TVD medio | TVD max | Desacordo medio |",
             "|---|---|---|---|---|"]
    for name, pair in payload["pairs"].items():
        for cell, d in pair["cells"].items():
            lines.append(f"| {name} | {cell} | {d['mean_tvd']:.4f} | "
                         f"{max(d['tvd_per_seed']):.4f} | {d['mean_disagreement']:.4f} |")
    lines += ["", "## Diagnostico", "", payload["diagnosis"], "",
              "## Contagens brutas de nu — A vs C, T=40, alpha=strict", "",
              "| Semente | Mundo | " + " | ".join(STANDING_VALUES) + " |",
              "|---|---|" + "---|" * len(STANDING_VALUES)]
    sample = payload["pairs"]["A_vs_C"]["cells"]["T=40,alpha=strict"]["raw_distributions"]
    for seed, dist in sample.items():
        for world, c in dist.items():
            lines.append(f"| {seed} | {world} | " +
                         " | ".join(str(c[s]) for s in STANDING_VALUES) + " |")
    (OUT_DIR / "positive_control_summary.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    out = main()
    print(json.dumps({"verdict": out["verdict"], "diagnosis": out["diagnosis"]},
                     indent=2, ensure_ascii=False))
