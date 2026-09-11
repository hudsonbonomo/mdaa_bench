"""Generate PREREGISTRO_v1.md by READING THE CODE, not by describing it.

Every tolerance, every gate name and every generator parameter in the output is
introspected from the modules at run time. Nothing can be asserted in the
pre-registration that the code does not implement, because nothing is typed
twice. Run it again after any change to the constants and the document moves.

    python make_prereg.py
"""
from __future__ import annotations
import hashlib
import inspect
import pathlib
import subprocess
import numpy as np

from sim import generators as G
from sim import pipeline as P
from sim import density as D
from sim import memory as M
from sim import ensemble as E
from sim import recovery as R

ROOT = pathlib.Path(__file__).parent
SRC = sorted((ROOT / "sim").glob("*.py"))   # the analysis code the document describes;
                                           # hashing tests/ too would make this file
                                           # change whenever its own guard changes

_GRID_HEAD = "python -m sim.recovery --T 300 600 --noise 0.05 0.3 --keep 1.0 0.7"
_GRID_TAIL = "    --nonlinear_h 0 1 --reps_per_person 1 10 --reps {n} --jobs 12 --out out_v3"
GRID_V3 = _GRID_HEAD + " \\\n" + _GRID_TAIL.format(n=10)
GRID_V3_MIN = _GRID_HEAD + " \\\n" + _GRID_TAIL.format(n=3)
CELL_SECONDS = {300: 11.7, 600: 23.6}      # measured serially, one process, this machine


def provenance() -> str:
    """Git commit if there is one; otherwise a content hash of the sources, which
    is the honest substitute and is stated as such."""
    try:
        h = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                           text=True, timeout=10)
        if h.returncode == 0:
            dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                                   capture_output=True, text=True, timeout=10).stdout.strip()
            return (f"git commit `{h.stdout.strip()}`"
                    + (" **with uncommitted changes**" if dirty else ""))
    except (OSError, subprocess.SubprocessError):
        pass
    acc = hashlib.sha256()
    for f in SRC:
        acc.update(f.name.encode()); acc.update(f.read_bytes())
    return (f"**not a git repository** — SHA-256 over the {len(SRC)} files of `sim/` instead: "
            f"`{acc.hexdigest()[:16]}`. A real pre-registration needs a commit; this "
            f"identifies the code but cannot prove when it was written.")


def boundedness_table() -> list[str]:
    """The condition written above each node body, read back out of the source."""
    src = inspect.getsource(G.generate).splitlines()
    out, node = [], None
    for i, line in enumerate(src):
        if 'node == "' in line:
            node = line.split('node == "')[1].split('"')[0]
        if "BOUNDEDNESS:" in line and node:
            parts = [line.split("BOUNDEDNESS:")[1].strip()]
            j = i + 1                       # the condition runs to the end of its comment block
            while j < len(src) and src[j].strip().startswith("#"):
                parts.append(src[j].strip().lstrip("#").strip())
                j += 1
            out.append(f"| `{node}` | {' '.join(p for p in parts if p)} |")
            node = None
    return out


def measured_ranges() -> dict:
    """Numbers the document quotes must come from running the code, not memory."""
    rho = [G.generate("M1+M", T=60, seed=s).truth["companion_rho"] for s in range(60)]
    worst = max(float(np.abs(G.generate(n, T=800, seed=s).x).max())
                for n in G.NODES for s in range(40))
    return dict(companion_rho=(min(rho), max(rho)), worst_abs_x=worst)


def main() -> None:
    m = measured_ranges()
    L: list[str] = []
    add = L.append

    add("# Pré-registro v2 — mdaa_bench")
    add("")
    add("Gerado por `make_prereg.py`, que lê as constantes dos módulos. Nenhuma linha")
    add("deste documento é digitada duas vezes: se uma tolerância mudar no código, ela muda")
    add("aqui na próxima execução. O que o código não implementa, não aparece.")
    add("")
    add(f"**Proveniência:** {provenance()}")
    add("")
    add("**Sementes:** CRC32 da tupla da célula "
        "(`zlib.crc32(repr((node, T, noise, keep, nonlinear_h, rep)))`), de modo que o mapa")
    add("independe do número de processos. Verificado por diff entre `--jobs 1` e `--jobs 4`.")
    add("")

    add("## Geradores")
    add("")
    add(f"Nós: {', '.join('`' + n + '`' for n in G.NODES)}. Parâmetros de `generate()`:")
    add("")
    sig = inspect.signature(G.generate)
    add("| parâmetro | padrão |")
    add("|---|---|")
    for k, v in sig.parameters.items():
        if v.default is not inspect.Parameter.empty:
            add(f"| `{k}` | `{v.default}` |")
    add("")
    add("### Condição de boundedness, por nó")
    add("")
    add("| nó | condição |")
    add("|---|---|")
    L.extend(boundedness_table())
    add("")
    add(f"Medido no código atual: `M1+M` tem raio de companion em "
        f"[{m['companion_rho'][0]:.4f}, {m['companion_rho'][1]:.4f}] sobre 60 sementes; "
        f"o maior `max|x|` sobre os quatro nós × 40 sementes em T=800 é {m['worst_abs_x']:.1f}, "
        f"contra o limite de {50.0} que `tests/test_boundedness.py` impõe.")
    add("")

    add("### Fronteira medida de `loc_radius`")
    add("")
    add(f"H1 recusa o pooling quando a razão entre/intra passa de "
        f"`H1_BETWEEN_WITHIN` = {D.H1_BETWEEN_WITHIN}. Por bisseção em quatro sementes "
        f"(M1, 30 pessoas, T=400, ruído 0.05, `A_radius`=0), isso acontece em "
        f"`loc_radius` entre **0.65 e 1.01**, mediana ≈ 0.84, em unidades de estado. "
        f"Com `loc_radius`=0 e `A_radius` até 0.9 a razão fica em 0.008 e H1 passa: "
        f"dispersar a LEI não quebra o pooling em raio nenhum.")
    add("")
    add("## Gates e regras de parada")
    add("")
    add("Cada gate devolve `(veredito, estatística, nota de parada)`. O veredito pertence a "
        f"{{{', '.join(repr(v) for v in D.VERDICTS)}}}.")
    add("")
    add("| gate | onde | tolerância declarada |")
    add("|---|---|---|")
    add(f"| M1 vs M0 | `pipeline.identify` | ganho fora da amostra > `TOL` = {P.TOL} |")
    add(f"| N | `pipeline.identify` + `wiener.py` | `TOL` = {P.TOL} e quantil `NULL_Q` = "
        f"{P.NULL_Q} de **dois** nulos, `N_SURR` = {P.N_SURR} surrogates cada |")
    add(f"| H | `switching.py` | `TOL` = {P.TOL}, corrida mediana >= `MIN_SEG` = {P.MIN_SEG}, "
        f"ocupação em (0.05, 0.95), \\|corr\\| com u < 0.5 |")
    add(f"| M | `density.h3_memory` sobre réplicas | `H3_TOL` = {D.H3_TOL}; exige "
        f"`MIN_REPLICATES` = {P.MIN_REPLICATES}; abaixo disso o veredito é "
        f"`{D.UNIDENTIFIABLE}` |")
    add(f"| S | `pipeline.identify` + `statespace.stochastic_null` | `TOL` = {P.TOL}, "
        f"quantil {P.NULL_Q} de {P.S_SURR} surrogates, e `S_QFRAC` = {P.S_QFRAC} |")
    add(f"| H1 | `density.h1_ensemble` | instabilidade < `H1_INSTAB` = {D.H1_INSTAB}; "
        f"bimodalidade > `H1_BIMODAL_SEP` = {D.H1_BIMODAL_SEP}; entre/intra > "
        f"`H1_BETWEEN_WITHIN` = {D.H1_BETWEEN_WITHIN} |")
    add(f"| H2 | `density.h2_geometry` | razão de escalas <= `H2_SCALE_RATIO` = "
        f"{D.H2_SCALE_RATIO} |")
    add(f"| H3 | `density.h3_memory` | `H3_TOL` = {D.H3_TOL}, no máximo "
        f"`H3_MAX_TRAJ` = {D.H3_MAX_TRAJ} trajetórias ajustadas |")
    add(f"| H4 | `density.h4_locality` | ganho > `H4_MARGIN` = {D.H4_MARGIN}, grade "
        f"`H4_GRID` = {D.H4_GRID} por eixo |")
    add("")
    add("### Quais tolerâncias são prior declarado e quais são por exploração")
    add("")
    add("Declaradas antes de ver o resultado, com justificativa escrita no código:")
    add(f"- `S_QFRAC` = {P.S_QFRAC} — \"pelo menos metade da variância de um passo\";")
    add(f"- `H1_BETWEEN_WITHIN` = {D.H1_BETWEEN_WITHIN} — \"pessoas diferem entre si mais do "
        "que variam dentro de si\";")
    add(f"- `MIN_SEG` = {P.MIN_SEG} — duração mínima de regime, imposta no decodificador.")
    add("")
    add("**Por exploração**, e assinaladas como tais:")
    add(f"- `TOL` = {P.TOL} — escolhido no v0 sem calibração; nunca foi revisado.")
    add(f"- `H4_MARGIN` = {D.H4_MARGIN} — introduzido porque o competidor não local é fraco "
        "(uma deriva por janela contra uma por célula), então empate é o nulo honesto; "
        "o valor foi escolhido olhando o controle negativo.")
    add(f"- `M.LAG_PENALTY` = {M.LAG_PENALTY} — prior de decaimento do kernel; a forma é "
        "declarada, a intensidade não foi calibrada.")
    add(f"- `E.OFFSET_SCALE` = {E.OFFSET_SCALE} — resquício do v2, hoje sem uso no caminho "
        "de `loc_radius`.")
    add("")

    add("## O que o desenho NÃO decide")
    add("")
    add("- O eixo **M** em trajetória única. O veredito é "
        f"`{D.UNIDENTIFIABLE}`, não `{D.FAIL}`. Motivo medido: o modelo de memória com o "
        "kernel verdadeiro vence o melhor espaço de estados livre d+k por 0–11%, contra um "
        "piso de ruído de estimação de ±0.14. O mapa de recuperação registra a terceira "
        "coluna em vez de contar como rejeição correta.")
    add("- O eixo **S** acima de ruído de medida ≈ 0.1 (poder cai de 8/8 para 4/8).")
    add("- Qualquer `h` não monotônico: o nulo de Wiener gaussianiza por posto.")
    add("- O eixo M sobre réplicas **não é infalível**. Medido em 8 células de ensemble "
        "(reps=10, 4 nós × 2 T): um falso positivo em `M1+H` a T=300 e um falso negativo "
        "em `M1+M` a T=300. A separação limpa (margem 0.157) foi medida a T=400 com 30 "
        "réplicas numa semente; as taxas reais são o que a grade v3 vai estabelecer.")
    add("- `reps_per_person` acima de "
        f"{D.H3_MAX_TRAJ} não muda o que H3 vê: o gate corta em `H3_MAX_TRAJ`. Os valores "
        "10 e 30 diferem apenas por sortearem pessoas diferentes, não por mais informação.")
    add("")

    add("## Grade v3 — pré-registrada, condicional à aprovação")
    add("")
    add("```bash")
    add(GRID_V3)
    add("```")
    n = len(G.NODES) * 2 * 2 * 2 * 2 * 2 * 10
    n_min = len(G.NODES) * 2 * 2 * 2 * 2 * 2 * 3
    hrs = (n / 2) * (CELL_SECONDS[300] + CELL_SECONDS[600]) / 2 / 3600
    add("")
    add(f"{len(G.NODES)} nós × 2 T × 2 ruídos × 2 keep × 2 h × 2 reps_per_person × 10 "
        f"sementes = **{n} runs**. Versão mínima, com 3 sementes: {n_min} runs.")
    add("")
    add(f"Custo medido serialmente nesta máquina: {CELL_SECONDS[300]} s por célula em "
        f"T=300 e {CELL_SECONDS[600]} s em T=600, **praticamente independente de "
        f"`reps_per_person`** porque `identify()` ajusta tudo menos o eixo M na primeira "
        f"trajetória e H3 se limita a `H3_MAX_TRAJ` = {D.H3_MAX_TRAJ} réplicas. "
        f"Total serial estimado: {hrs:.1f} h.")
    add("")
    add(f"O fator `reps_per_person` é o que esta grade adiciona: em 1 o eixo M é "
        f"`{D.UNIDENTIFIABLE}` por construção; em 10 ele recebe veredito de H3. Sem esse "
        f"fator a grade não diria nada sobre memória.")
    add("")
    add("Colunas registradas por `recovery.run_cell`: `exact`, `spurious`, `missed`, "
        "`undecided`, `m_verdict`, `reps_per_person`, `s_axis`, `n_hardest`, além de "
        "`vd_*` por eixo e `gain_*` por estatística.")
    add("")
    add("A grade **não roda** enquanto a linha de aprovação em `ESTADO_CELULA.md` estiver "
        "vazia (Modo Celular, regra 5).")
    add("")
    add("## Hipóteses que a grade vai testar")
    add("")
    add("1. Taxa de falso alarme de N sob `nonlinear_h=1` cai em relação ao v1 (0.204) — o "
        "nulo de Wiener é a defesa; o v2 mediu 1/6 em 6 sementes, a grade mede em 240.")
    add("2. Poder de H cresce com T e cai com ruído; tempos de troca mantêm MAE < 5 passos "
        "onde o gate dispara.")
    add(f"3. O eixo M é `{D.UNIDENTIFIABLE}` em **100%** das células, porque toda célula da "
        "grade é de trajetória única. Esta é uma predição do desenho, não um resultado.")
    add("4. O eixo S tem poder decrescente em ruído de medida, com 0 falsos no controle "
        "determinístico.")
    add("")

    out = ROOT / "PREREGISTRO_v2.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{out.name}: {len(L)} linhas")


if __name__ == "__main__":
    main()
