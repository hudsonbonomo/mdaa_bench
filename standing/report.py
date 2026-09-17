"""The predictions table for the standing grid. Reads `grid_v1_summary.json`'s
payload and writes one Markdown row per prediction x cell, with the threshold the
pre-registration committed to, the observed value and PASS/FAIL.

No measurement happens here — only formatting. Thresholds are quoted from
PREREGISTRO_v1 §7 and emendas v1.2/v1.3 and must not be edited to fit a result.
"""
from __future__ import annotations

from pathlib import Path

__all__ = ["write_predictions"]

HEAD = ("| previsao | celula | limiar (preregistro) | observado | veredito |\n"
        "|---|---|---|---|---|")


def _v(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def _rows(summary: dict) -> list[str]:
    out = []
    for cell, d in summary["P1"].items():
        out.append(f"| P1 (equivalencia, R_decay) | {cell} | TOST Δ=0,10, α=0,05: "
                   f"equivalente | media {d['mean']:.4f}, max {d['max']:.4f}, "
                   f"p_lo={d['p_lower']:.2e}, p_hi={d['p_upper']:.2e} | {_v(d['equivalent'])} |")
    for cell, d in summary["P1b"].items():
        out.append(f"| P1b (instrumento, R_declared) | {cell} | TVD(A, B logged) ≥ 0,40 "
                   f"e TVD(A, B unlogged) ≤ 0,05 | logged min {d['min_tvd_B_logged']:.3f} "
                   f"(media {d['mean_tvd_B_logged']:.3f}); unlogged max "
                   f"{d['max_tvd_B_unlogged']:.3f} | {_v(d['pass'])} |")
    for cell, d in summary["P2"].items():
        out.append(f"| P2 (B logged, out of scope) | {cell} | ≥ 0,95 | "
                   f"{d['rate']:.4f} ({d['hits']}/{d['total']}) | {_v(d['pass'])} |")
    for cell, d in summary["P3"].items():
        out.append(f"| P3 (C, estatuto B com ordem) | {cell} | B ≥ 0,95 e nenhum AGED "
                   f"na janela | B {d['rate_B']:.2f} ({d['n_statute_B']}/{d['n']}), "
                   f"AGED-na-janela {d['n_aged_inside_window']}, ordem legivel "
                   f"{d['order_legible_rate']:.2f} | {_v(d['pass'])} |")
    for cell, d in summary["P3"].items():
        if cell.startswith("T=160"):
            ok = d["decay_decline_rate"] >= 0.80
            out.append(f"| P3 (C, R_decay reporta decaimento) | {cell} | ≥ 0,80 com T=160 "
                       f"| share<0,5 em {d['decay_decline_rate']:.2f} (media do share "
                       f"{d['decay_share_mean']:.3f}) | {_v(ok)} |")
    for cell, d in summary["P4"].items():
        out.append(f"| P4 (D, unevaluable) | {cell} | precisao e revocacao ≥ 0,99, "
                   f"todos voltam apos total, out of scope apos parcial | "
                   f"P={d['precision']:.4f}, R={d['recall']:.4f}, voltam "
                   f"{d['returned_ok_rate']:.2f} (tp={d['tp']}, fp={d['fp']}, "
                   f"fn={d['fn']}) | {_v(d['pass'])} |")
    for cell, d in summary["P4"].items():
        out.append(f"| P4 — leitura estrita (diagnostico, sem limiar) | {cell} | "
                   f"APPLICABLE apos total | {d['branch_ok_strict_rate']:.2f}; "
                   f"{d['n_aged_pre_tau1']} registros pre-τ₁ voltaram AGED "
                   f"(fora da janela de α) | — |")
    for cell, d in summary["P4b"].items():
        out.append(f"| P4b (espelho-controle, R_current) | {cell} | 1,00 | "
                   f"{d['rate']:.2f} ({d['n']} sementes) | {_v(d['pass'])} |")
    p5 = summary["P5"]
    out.append(f"| P5 (A, divergencia com causa) | {p5['cell']} | divergencia ≥ 0,90 e "
               f"razao = bloqueio por B em 1,00 | divergencia {p5['divergence_rate']:.2f} "
               f"({p5['n_divergent']}/{p5['n']}), B_blocking "
               f"{p5['b_blocking_rate']:.2f} | {_v(p5['pass'])} |")
    return out


def _verdict_block(summary: dict) -> list[str]:
    lines = ["", "## Veredito por previsao", "",
             "| previsao | celulas | PASS |", "|---|---|---|"]
    named = {"P1": [d["equivalent"] for d in summary["P1"].values()],
             "P1b": [d["pass"] for d in summary["P1b"].values()],
             "P2": [d["pass"] for d in summary["P2"].values()],
             "P3": [d["pass"] for d in summary["P3"].values()],
             "P4": [d["pass"] for d in summary["P4"].values()],
             "P4b": [d["pass"] for d in summary["P4b"].values()],
             "P5": [summary["P5"]["pass"]]}
    for name, vals in named.items():
        lines.append(f"| {name} | {len(vals)} | {sum(vals)}/{len(vals)} "
                     f"— {_v(all(vals))} |")
    return lines


def write_predictions(summary: dict, path: Path) -> None:
    f = summary["factors"]
    lines = [
        "# Grade v1 — previsoes comprometidas × observado",
        "",
        f"Preregistro: `{summary['preregistro']}`. "
        f"CLI SHA-256 `{summary['cli_sha256']}`.",
        f"Sementes {min(summary['seeds'])}–{max(summary['seeds'])} "
        f"({len(summary['seeds'])}). "
        f"{summary['n_cells']} celulas × {len(summary['seeds'])} sementes = "
        f"{summary['n_rows']} execucoes em {summary['elapsed_seconds']} s.",
        "",
        f"Bracos: {', '.join(f['world_arms'])}. T {f['T']}, α {f['alpha']}, "
        f"replicas {f['replicas']}.",
        "",
        "> `logged`/`unlogged` e fator do mundo B (§3); A, C e D registram a condicao",
        "> por construcao. `replicas` nao e parametro de `make_world`: a grade roda 1,",
        "> como o piloto. Em D a reconciliacao vem do RNG do gerador (p = ½), nao de",
        "> `force_reconciliation`.",
        "",
        HEAD,
    ]
    lines += _rows(summary)
    lines += _verdict_block(summary)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
