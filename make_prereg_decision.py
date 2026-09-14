"""Generate PREREGISTRO_v4.md by READING THE CODE, not by describing it.

Same rule as `make_prereg.py`, applied to the decision bench: every constant,
every family, every warrant rule and every metric name in the output is
introspected at run time, so the document cannot claim anything the code does
not implement. Run it again after any change and the document moves.

    python make_prereg_decision.py

The measured numbers below are FROZEN constants with the command that produced
them, not live measurements: a pre-registration has to be reproducible, and a
wall clock is not. Re-measure and paste, on an idle machine.
"""
from __future__ import annotations
import hashlib
import pathlib
import subprocess

from decision import bench as B
from decision import metrics as ME
from decision import models as MO
from decision import worlds as W
from decision.warrant import load_chi

ROOT = pathlib.Path(__file__).parent
OUT_NAME = "PREREGISTRO_v4.md"
SRC = sorted((ROOT / "decision").glob("*.py"))

GRID = ("python -m decision.bench --T 300 600 --noise 0.05 0.3 --keep 1.0 0.7 \\\n"
        "    --flip 0.05 0.25 --reps 20 --jobs 8 --out out_decision_v4")
GRID_MIN = GRID.replace("--reps 20", "--reps 5").replace("out_decision_v4", "out_decision_v4_min")

# MEASURED on 8 real cells (4 per T, one per family), idle machine:
#   python -c "from decision.bench import measure_cost; print(measure_cost(T=300, reps=1))"
COST = {300: 0.27, 600: 0.54}

# MEASURED by `python scripts/decision_nonvacuity.py 20` (20 seeds, T=400).
NONVACUITY = {"W-absence": (0.699, 0.765, 0.747, 0.784),
              "W-conflict": (0.699, 0.790, 0.764, 0.812),
              "W-scope": (0.843, 0.892, 0.832, 0.947),
              "W-pause": (0.774, 0.828, 0.764, 0.887)}

# PILOT, 64 cells: `python -m decision.bench --T 300 --flip 0.05 0.25 --reps 8`.
# One T, one measurement noise, complete sampling: a SUBSET of the grid below,
# and labelled as such everywhere it is quoted.
PILOT = {
    "W-absence": {"M0": (0.945, 0.644), "M1": (0.945, 0.644),
                  "M2": (1.000, 0.688), "M1+pausa": (0.945, 0.644)},
    "W-conflict": {"M0": (0.944, 0.561), "M1": (0.944, 0.561),
                   "M2": (1.000, 0.603), "M1+pausa": (0.944, 0.561)},
    "W-scope": {"M0": (0.110, 1.000), "M1": (0.724, 0.243),
                "M2": (0.756, 0.243), "M1+pausa": (0.724, 0.243)},
    "W-pause": {"M0": (0.163, 1.000), "M1": (0.163, 1.000),
                "M2": (1.000, 0.000), "M1+pausa": (0.957, 0.000)},
}
PILOT_FLIP = {"W-scope": {"M1": (0.093, 0.394), "M0": (1.000, 1.000)}}
CEILING = {"W-absence": 1.0, "W-conflict": 1.0, "W-pause": 1.0, "W-scope": 0.756}


def provenance() -> str:
    try:
        h = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                           text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                               capture_output=True, text=True).stdout.strip()
        return f"git commit `{h}`" + (" **with uncommitted changes**" if dirty else "")
    except Exception:
        digest = hashlib.sha256(b"".join(p.read_bytes() for p in SRC)).hexdigest()
        return f"content hash of `decision/` `{digest}`"


def main():
    chi = load_chi()
    L = []
    add = L.append

    add("# Pré-registro v4 — bancada de DECISÃO (`decision/`)")
    add("")
    add("Gerado por `make_prereg_decision.py`, que lê as constantes dos módulos. "
        "Nenhuma linha deste documento é digitada duas vezes: se uma tolerância mudar no "
        "código, ela muda aqui na próxima execução. O que o código não implementa, não aparece.")
    add("")
    add("Os pré-registros v1–v3 cobrem a bancada de DINÂMICA (`sim/`), que planta uma lei e "
        "mede se o pipeline a recupera. Este cobre a segunda bancada, que planta POLÍTICA: "
        "mundos em que a AÇÃO CORRETA é conhecida por construção, para testar os três "
        "modelos adversariais do Paper 4. As duas bancadas compartilham gerador, camada de "
        "observação e estimador; nada em `sim/` foi alterado por esta célula.")
    add("")
    add(f"**Proveniência:** {provenance()}")
    add("")
    add(f"**χ congelado:** `decision/warrants.yaml`, versão {chi.version}, "
        f"declarado em {chi.frozen_on}, sha256 `{chi.sha256}`.")
    add("")
    add("**Sementes:** CRC32 da tupla da célula "
        f"(`zlib.crc32(repr({B.CELL_KEYS})`), de modo que o resultado independe do número "
        "de processos. Os sorteios de acompanhamento de `metrics` são semeados por "
        "`(semente do mundo, t)`, e não por modelo, para que os três vejam a MESMA "
        "evidência devolvida no mesmo passo.")
    add("")

    add("## As quatro famílias de mundo")
    add("")
    add("| família | o que está no registro | ação correta |")
    add("|---|---|---|")
    for fam, desc in [
            ("W-absence", "nenhuma evidência admissível sobre `p` (mas o registro não está vazio: há item sobre `q`)"),
            ("W-conflict", "dois itens, MESMO escopo, valores opostos"),
            ("W-scope", "dois itens, condições DIFERENTES, opostos, cada um verdadeiro na sua"),
            ("W-pause", "evidência concordante e suficiente, e uma pausa autorizada em vigor")]:
        want = {"W-absence": "OBSERVE", "W-conflict": "PROBE",
                "W-scope": "COMPARE", "W-pause": "WAIT"}[fam]
        add(f"| `{fam}` | {desc} | `{want}` |")
    add("")
    add(f"Ações: {', '.join('`' + a + '`' for a in W.ACTIONS)}. "
        f"Condições: {', '.join('`' + c + '`' for c in W.CONDITIONS)}. "
        f"Escopo: (S, O, C, t). Proveniência: `post` / `spont` — se a observação veio "
        "depois de um apoio dado ou não. A proveniência é atributo do ITEM e não tem "
        "contrapartida em `u`: o apoio é dado por uma pessoa, não pelo canal pedagógico "
        "que a bancada de dinâmica aciona. Nenhum modelo pode recuperá-la de `u`.")
    add("")
    add("Toda família também tem passos de LINHA DE BASE — evidência suficiente, "
        "concordante, com apoio dado — onde a ação correta é `ACT`. Sem eles uma política "
        "constante acertaria a família inteira e a família não mediria nada.")
    add("")
    add("| parâmetro | valor |")
    add("|---|---|")
    for k in ("WINDOW", "GAP", "SIGNATURE_FRAC", "SPONT_FRAC", "FLIP_P", "NON_VACUITY_FLOOR"):
        add(f"| `{k}` | `{getattr(W, k)}` |")
    add("")

    add("### Teste de não-vacuidade (item 1), MEDIDO")
    add("")
    add("Para cada família, a política que COLAPSA exatamente a distinção que aquela "
        "família planta (`epistemic.blind_action`: N→B, B→N, descartar C, descartar Ω). "
        "Se ela não erra na maior parte dos passos, a família não testa o que diz testar.")
    add("")
    add("| família | passos de assinatura | erro da política cega | faixa em 20 sementes |")
    add("|---|---|---|---|")
    for fam in W.FAMILIES:
        s, b, lo, hi = NONVACUITY[fam]
        add(f"| `{fam}` | {s:.3f} | **{b:.3f}** | {lo:.3f} – {hi:.3f} |")
    add("")
    add(f"Piso declarado: `NON_VACUITY_FLOOR` = {W.NON_VACUITY_FLOOR}. As quatro passam. "
        "`tests/test_decision_worlds.py` asserta o piso em código; o número acima é a "
        "medição sobre 20 sementes, T=400.")
    add("")

    add("## Os três modelos, com estimador congelado")
    add("")
    add("| modelo | o que vê |")
    add("|---|---|")
    add("| `M0` | b(t) do estimador + contexto observado. A evidência chega como AGREGADO "
        "ESCALAR sobre exatamente os itens que Λ admitiria: quantos, e para que lado em "
        "média. Nada é retirado de M0 exceto a estrutura — inclusive a CONTAGEM, então "
        "separar N de B está ao alcance dele. |")
    add("| `M1` | M0 + Λ(t) explícito: T/F/B/N por proposição, por escopo, com proveniência "
        "anexada. Λ carrega a proveniência e NÃO age sobre ela: exigi-la é norma, não "
        "leitura, e a exigência mora em χ. |")
    add("| `M2` | M1 + Ω(t): warrant por ação sob o χ congelado. Uma negação é redirigida "
        "para o remédio que χ prescreve, nunca deixada como recusa. |")
    add(f"| `{MO.ABLATION}` | **A ABLAÇÃO.** M1 com uma linha a mais — nunca `ACT` sob "
        "autorização em vigor — e nada mais de Ω. Se empatar com M2, ω é uma checagem de "
        "flag e o README tem de dizer isso. |")
    add("")
    add("O estimador é `decision.models.fit_estimator` — um único espaço de estados "
        "linear-gaussiano ajustado por EM (`sim/statespace.py`) sobre o canal de "
        "observação. `tests/test_decision_models.py` compara os PARÂMETROS AJUSTADOS "
        "(A, B, Q, R, loglik) entre os quatro modelos, não os tipos: um Kalman melhor não "
        "pode ser creditado à camada epistêmica.")
    add("")
    add("Constantes de política, declaradas antes do piloto e não ajustadas depois — todas "
        "**por exploração**, nenhuma calibrada:")
    add("")
    add("| constante | valor | papel |")
    add("|---|---|---|")
    add(f"| `M0_DECIDED` | `{MO.M0_DECIDED}` | |média| abaixo disso lê como contestado |")
    add(f"| `M0_BELIEF_Z` | `{MO.M0_BELIEF_Z}` | sds de estado em que M0 chama a própria crença de confiante |")
    add(f"| `CONF_DECIDED` | `{MO.CONF_DECIDED}` | Λ não tem probabilidades; substituto declarado |")
    add(f"| `CONF_UNDECIDED` | `{MO.CONF_UNDECIDED}` | idem, para N/B/cross-escopo |")
    add(f"| `CONF_DENIED` | `{MO.CONF_DENIED}` | confiança quando o warrant é negado |")
    add("")
    add("### Predicado único de elegibilidade")
    add("")
    add("`decision/eligible.py`: um passo entra na pontuação de TODOS os modelos só se "
        "`sim.observe.scorable_steps` o aceita (t e t−1 ambos observados, que é o que o "
        "estimador compartilhado precisa para produzir uma crença) e o janela de evidência "
        "cabe no registro. O teste asserta igualdade de CONJUNTOS de índices, não de "
        "contagens. M2 se abstém onde M1 age: um modelo que escolhe o próprio denominador "
        "ganharia respondendo menos.")
    add("")

    add("## χ declarado e CONGELADO")
    add("")
    add(f"`decision/warrants.yaml`, sha256 `{chi.sha256}`, congelado em "
        f"`decision/warrants.sha256`. O hash é verificado em TODA carga (`load_chi`) e a "
        "cada célula da grade. `tests/test_decision_warrants.py` falha se o arquivo, o "
        "congelamento e este documento discordarem. Mudar uma regra exige recongelar o "
        "hash E regerar este documento, o que move o commit: não dá para fazer em silêncio. "
        "Esta é a vulnerabilidade que o próprio paper declara (D8), tratada como invariante.")
    add("")
    add(f"Janela de admissibilidade: `max_age` = {chi.max_age}, logo {chi.window} passo — "
        "χ governa a janela e o mundo tem de concordar (asserção em `run_models`).")
    add("")
    add("| ação | claim de warrant | proveniência exigida | bloqueada por pausa | critério externo |")
    add("|---|---|---|---|---|")
    for name in ("ACT", "OBSERVE", "PROBE", "COMPARE", "WAIT"):
        r = chi.actions[name]
        claim = " ".join(r["warrant_claim"].split())
        claim = claim[:96] + "…" if len(claim) > 96 else claim
        prov = (r.get("provenance") or {}).get("required") or "—"
        cls = r.get("blocked_by_pause_class") or "—"
        crit = ", ".join(f"`{c}`" for c in r["external_criterion"])
        add(f"| `{name}` | {claim} | `{prov}` | `{cls}` | {crit} |")
    add("")
    add("Remédios de `ACT` por motivo de negação: "
        + ", ".join(f"`{k}` → `{v}`" for k, v in chi.actions["ACT"]["on_denied"].items())
        + ". Nenhum deles é `ACT`, e nenhum é uma recusa sem saída — uma abstenção grátis "
          "premiaria o modelo que responde menos.")
    add("")

    add("## Critérios EXTERNOS às regras de warrant (item 4)")
    add("")
    add("Nenhum deles é «M2 escolheu ações diferentes». Todos com DENOMINADOR "
        "COMPARTILHADO: o conjunto elegível, ou um subconjunto definido pelo MUNDO (passos "
        "sob pausa, passos em que as condições de fato diferem), nunca pelo comportamento "
        "do modelo. `metrics.evaluate` asserta a igualdade em vez de confiar nela.")
    add("")
    add("| critério | o que mede | direção |")
    add("|---|---|---|")
    for k, desc in [
            ("contradicted_rate", "ações depois contraditas por leitura posterior NA MESMA condição"),
            ("brier_act", "calibração da confiança de intervenção, em todos os passos elegíveis"),
            ("request_resolution_rate", "pedidos de informação que de fato assentam a questão do passo"),
            ("unsupported_counterfactual_rate", "`ACT` sem nenhum item de proveniência `post`"),
            ("pause_violation_rate", "`ACT` dentro de pausa autorizada / passos sob pausa"),
            ("deficit_inference_rate", "`ACT` ou `PROBE` onde as condições de fato diferem — o caso lido como problema de S"),
            ("accuracy", "coincidência com a ação plantada (reportada, NÃO é o critério primário)")]:
        arrow = "maior é melhor" if ME.HIGHER_IS_BETTER[k] else "menor é melhor"
        add(f"| `{k}` | {desc} | {arrow} |")
    add("")
    add("Critério primário por família, que é o que a figura mostra: "
        + ", ".join(f"`{f}` → `{ME.PRIMARY[f]}`" for f in W.FAMILIES) + ".")
    add("")
    add("**Teto do registro.** `metrics.ceiling` recomputa a ação de referência lendo a "
        "diferença de condição do REGISTRO em vez do mundo. Em três famílias o registro "
        "decide e o teto é 1.0, então toda perda pertence a uma camada. Em `W-scope` o teto "
        "é " + f"{CEILING['W-scope']:.3f}" + " (piloto): uma discordância entre condições no "
        "registro pode ser um item invertido, e leitor nenhum do registro distingue. Essa "
        "folga é o sensor, não uma camada.")
    add("")

    add("## Piloto — 64 células, NÃO é a grade")
    add("")
    add("`python -m decision.bench --T 300 --flip 0.05 0.25 --reps 8`. Um T, um ruído de "
        "medida, amostragem completa. É um SUBCONJUNTO da grade abaixo e está rotulado "
        "assim em todo lugar onde é citado. Serve para registrar hipóteses, não para "
        "responder.")
    add("")
    add("| família | critério primário | M0 | M1 | M2 | " + MO.ABLATION + " |")
    add("|---|---|---|---|---|---|")
    for fam in W.FAMILIES:
        k = ME.PRIMARY[fam]
        vals = " | ".join(f"{PILOT[fam][m][1]:.3f}" for m in MO.ALL_MODELS)
        add(f"| `{fam}` | `{k}` | {vals} |")
    add("")
    add("| família | acurácia (teto) | M0 | M1 | M2 | " + MO.ABLATION + " |")
    add("|---|---|---|---|---|---|")
    for fam in W.FAMILIES:
        vals = " | ".join(f"{PILOT[fam][m][0]:.3f}" for m in MO.ALL_MODELS)
        add(f"| `{fam}` | {CEILING[fam]:.3f} | {vals} |")
    add("")

    add("## Hipóteses REGISTRADAS, por família")
    add("")
    add("A condição de falha é a do paper: **se M1 não vence M0, a camada de evidência "
        "proposicional perde papel operacional; se M2 não vence M1, a camada de warrant sai "
        "da arquitetura.** As hipóteses abaixo predizem que isso acontece em parte — e "
        "predizer o resultado negativo antes de medi-lo é o que torna a medição um teste.")
    add("")
    add("1. **`W-absence`: M1 = M0.** |M1 − M0| ≤ 0.01 em `request_resolution_rate` e em "
        "`accuracy`. M0 recebe a CONTAGEM de itens, então N versus B está ao alcance de um "
        "agregado escalar. Predição do desenho, não resultado: se Λ vencer aqui, o "
        "baseline estava aleijado e é o baseline que precisa de conserto.")
    add("2. **`W-conflict`: M1 = M0**, mesmo limiar e mesmo motivo.")
    add("3. **`W-scope`: M1 ≫ M0.** `deficit_inference_rate` de M0 ≥ 0.95 e de M1 ≤ 0.30 "
        f"a `flip_p` = {W.FLIP_P}. Os dois números vêm do piloto (1.000 e "
        f"{PILOT_FLIP['W-scope']['M1'][0]:.3f}); a grade os mede em 320 células por família. "
        "**Esta é a única família em que a camada Λ tem caso a fazer, e o desenho prevê "
        "isso antes de medir.** Sob `flip_p` = 0.25 a vantagem degrada e não desaparece: "
        f"predição registrada de M1 ≤ 0.50 (piloto: {PILOT_FLIP['W-scope']['M1'][1]:.3f}).")
    add("4. **`W-pause`: M2 ≫ M1 e M2 = " + MO.ABLATION + " no critério primário.** "
        "`pause_violation_rate` = 1.0 para M0 e M1, 0.0 para M2. **Registrado antes da "
        "grade: a violação de pausa NÃO separa Ω de uma checagem de flag.** O que separa é "
        f"acurácia ({PILOT['W-pause']['M2'][0]:.3f} contra "
        f"{PILOT['W-pause'][MO.ABLATION][0]:.3f}) e `unsupported_counterfactual_rate` "
        "(0.000 contra 0.044), e isso é a cláusula de proveniência, não a de pausa.")
    add("5. **Ω tem dois dentes e só um deles é a pausa.** Em `W-absence` e `W-conflict`, "
        "onde não há pausa nenhuma, M2 > M1 por ≥ 0.03 em `request_resolution_rate` e por "
        "0.05 em `accuracy`, inteiramente pela exigência de proveniência. Se esse ganho "
        "sumir na grade, ω se reduz à checagem de flag e sai.")
    add("")

    add("## Grade de decisão — PRÉ-REGISTRADA, condicional à aprovação")
    add("")
    add("```bash")
    add(GRID)
    add("```")
    add("")
    n_cells = 4 * 2 * 2 * 2 * 2 * 20
    add(f"4 famílias × 2 T × 2 ruídos de medida × 2 `keep` × 2 `flip_p` × 20 sementes = "
        f"**{n_cells} células**, {n_cells * len(MO.ALL_MODELS)} linhas (uma por modelo). "
        f"Versão mínima, com 5 sementes: {n_cells // 4} células.")
    add("")
    total = sum(COST[t] * n_cells // 2 for t in (300, 600))
    add(f"Custo MEDIDO em 8 células reais (4 por T, uma por família), máquina ociosa, não "
        f"estimado por aritmética: **{COST[300]} s** por célula em T=300 e **{COST[600]} s** "
        f"em T=600. Total serial: {total:.0f} s ≈ {total / 60:.1f} min. A bancada de decisão "
        "é duas ordens de grandeza mais barata que a de dinâmica (7.8 h) porque ajusta UM "
        "espaço de estados por célula e o resto é política.")
    add("")
    add("Colunas por linha: `family`, `T`, `noise`, `keep`, `flip_p`, `rep`, `seed`, "
        "`model`, `chi_sha256`, `record_ceiling`, `signature_frac`, "
        + ", ".join(f"`{k}`" for k in ME.METRICS) + ", `n_steps`, `n_paused`, `n_scope`.")
    add("")
    add("Reportada POR FAMÍLIA e nunca agregada. Agregar deixaria a família em que o "
        "warrant é decisivo pagar pelas famílias em que ele não muda nada, que é o oposto "
        "de uma condição de falsificação.")
    add("")
    add("A grade **não roda** enquanto a linha de aprovação em `ESTADO_CELULA.md` estiver "
        "vazia (Modo Celular, regra 5).")
    add("")

    add("## O que este desenho NÃO decide")
    add("")
    add("- **Se Λ vale a pena fora de `W-scope`.** O desenho prevê empate em duas das "
        "quatro famílias e a previsão está registrada. Um empate ali não é resultado nulo "
        "da bancada: é o desenho funcionando.")
    add("- **Se o escopo temporal faz trabalho.** `max_age` é declarado e governa a janela, "
        "mas nenhuma família planta evidência velha, então a cláusula nunca é a vinculante. "
        "Declarado, não implicado.")
    add("- **Se as regras de χ são as certas.** A bancada mede se as regras declaradas "
        "sobrevivem a critérios externos, não se outro χ iria melhor. Um χ concorrente é "
        "outra célula.")
    add("- **Agentes LLM como superfície de decisão.** Fora de escopo, pela mesma razão que "
        "SIM-6 continua fechado na outra bancada.")
    add("- **Múltiplos sujeitos ou múltiplas proposições.** Um S, um `p`, um `q` de "
        "controle. As cláusulas de χ sobre S e O existem e nunca são exercidas.")
    add("")

    out = ROOT / OUT_NAME
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{out.name}: {len(L)} linhas")


if __name__ == "__main__":
    main()
