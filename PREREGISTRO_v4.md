# Pré-registro v4 — bancada de DECISÃO (`decision/`)

Gerado por `make_prereg_decision.py`, que lê as constantes dos módulos. Nenhuma linha deste documento é digitada duas vezes: se uma tolerância mudar no código, ela muda aqui na próxima execução. O que o código não implementa, não aparece.

Os pré-registros v1–v3 cobrem a bancada de DINÂMICA (`sim/`), que planta uma lei e mede se o pipeline a recupera. Este cobre a segunda bancada, que planta POLÍTICA: mundos em que a AÇÃO CORRETA é conhecida por construção, para testar os três modelos adversariais do Paper 4. As duas bancadas compartilham gerador, camada de observação e estimador; nada em `sim/` foi alterado por esta célula.

**Proveniência:** git commit `33c6133725668bdce2ae91c5028c6ea8abacb1e4` **with uncommitted changes**

**χ congelado:** `decision/warrants.yaml`, versão 1, declarado em 2026-09-14, sha256 `689752ec2d696995e40e3f6b3871a111d65e022dc90494d128e5ed03fcb783c6`.

**Sementes:** CRC32 da tupla da célula (`zlib.crc32(repr(('family', 'T', 'noise', 'keep', 'flip_p', 'rep'))`), de modo que o resultado independe do número de processos. Os sorteios de acompanhamento de `metrics` são semeados por `(semente do mundo, t)`, e não por modelo, para que os três vejam a MESMA evidência devolvida no mesmo passo.

## As quatro famílias de mundo

| família | o que está no registro | ação correta |
|---|---|---|
| `W-absence` | nenhuma evidência admissível sobre `p` (mas o registro não está vazio: há item sobre `q`) | `OBSERVE` |
| `W-conflict` | dois itens, MESMO escopo, valores opostos | `PROBE` |
| `W-scope` | dois itens, condições DIFERENTES, opostos, cada um verdadeiro na sua | `COMPARE` |
| `W-pause` | evidência concordante e suficiente, e uma pausa autorizada em vigor | `WAIT` |

Ações: `ACT`, `OBSERVE`, `PROBE`, `COMPARE`, `WAIT`. Condições: `apoiada`, `nao_apoiada`. Escopo: (S, O, C, t). Proveniência: `post` / `spont` — se a observação veio depois de um apoio dado ou não. A proveniência é atributo do ITEM e não tem contrapartida em `u`: o apoio é dado por uma pessoa, não pelo canal pedagógico que a bancada de dinâmica aciona. Nenhum modelo pode recuperá-la de `u`.

Toda família também tem passos de LINHA DE BASE — evidência suficiente, concordante, com apoio dado — onde a ação correta é `ACT`. Sem eles uma política constante acertaria a família inteira e a família não mediria nada.

| parâmetro | valor |
|---|---|
| `WINDOW` | `1` |
| `GAP` | `1.3` |
| `SIGNATURE_FRAC` | `0.7` |
| `SPONT_FRAC` | `0.25` |
| `FLIP_P` | `0.05` |
| `NON_VACUITY_FLOOR` | `0.6` |

### Teste de não-vacuidade (item 1), MEDIDO

Para cada família, a política que COLAPSA exatamente a distinção que aquela família planta (`epistemic.blind_action`: N→B, B→N, descartar C, descartar Ω). Se ela não erra na maior parte dos passos, a família não testa o que diz testar.

| família | passos de assinatura | erro da política cega | faixa em 20 sementes |
|---|---|---|---|
| `W-absence` | 0.699 | **0.765** | 0.747 – 0.784 |
| `W-conflict` | 0.699 | **0.790** | 0.764 – 0.812 |
| `W-scope` | 0.843 | **0.892** | 0.832 – 0.947 |
| `W-pause` | 0.774 | **0.828** | 0.764 – 0.887 |

Piso declarado: `NON_VACUITY_FLOOR` = 0.6. As quatro passam. `tests/test_decision_worlds.py` asserta o piso em código; o número acima é a medição sobre 20 sementes, T=400.

## Os três modelos, com estimador congelado

| modelo | o que vê |
|---|---|
| `M0` | b(t) do estimador + contexto observado. A evidência chega como AGREGADO ESCALAR sobre exatamente os itens que Λ admitiria: quantos, e para que lado em média. Nada é retirado de M0 exceto a estrutura — inclusive a CONTAGEM, então separar N de B está ao alcance dele. |
| `M1` | M0 + Λ(t) explícito: T/F/B/N por proposição, por escopo, com proveniência anexada. Λ carrega a proveniência e NÃO age sobre ela: exigi-la é norma, não leitura, e a exigência mora em χ. |
| `M2` | M1 + Ω(t): warrant por ação sob o χ congelado. Uma negação é redirigida para o remédio que χ prescreve, nunca deixada como recusa. |
| `M1+pausa` | **A ABLAÇÃO.** M1 com uma linha a mais — nunca `ACT` sob autorização em vigor — e nada mais de Ω. Se empatar com M2, ω é uma checagem de flag e o README tem de dizer isso. |

O estimador é `decision.models.fit_estimator` — um único espaço de estados linear-gaussiano ajustado por EM (`sim/statespace.py`) sobre o canal de observação. `tests/test_decision_models.py` compara os PARÂMETROS AJUSTADOS (A, B, Q, R, loglik) entre os quatro modelos, não os tipos: um Kalman melhor não pode ser creditado à camada epistêmica.

Constantes de política, declaradas antes do piloto e não ajustadas depois — todas **por exploração**, nenhuma calibrada:

| constante | valor | papel |
|---|---|---|
| `M0_DECIDED` | `0.5` | |média| abaixo disso lê como contestado |
| `M0_BELIEF_Z` | `2.0` | sds de estado em que M0 chama a própria crença de confiante |
| `CONF_DECIDED` | `0.9` | Λ não tem probabilidades; substituto declarado |
| `CONF_UNDECIDED` | `0.1` | idem, para N/B/cross-escopo |
| `CONF_DENIED` | `0.02` | confiança quando o warrant é negado |

### Predicado único de elegibilidade

`decision/eligible.py`: um passo entra na pontuação de TODOS os modelos só se `sim.observe.scorable_steps` o aceita (t e t−1 ambos observados, que é o que o estimador compartilhado precisa para produzir uma crença) e o janela de evidência cabe no registro. O teste asserta igualdade de CONJUNTOS de índices, não de contagens. M2 se abstém onde M1 age: um modelo que escolhe o próprio denominador ganharia respondendo menos.

## χ declarado e CONGELADO

`decision/warrants.yaml`, sha256 `689752ec2d696995e40e3f6b3871a111d65e022dc90494d128e5ed03fcb783c6`, congelado em `decision/warrants.sha256`. O hash é verificado em TODA carga (`load_chi`) e a cada célula da grade. `tests/test_decision_warrants.py` falha se o arquivo, o congelamento e este documento discordarem. Mudar uma regra exige recongelar o hash E regerar este documento, o que move o commit: não dá para fazer em silêncio. Esta é a vulnerabilidade que o próprio paper declara (D8), tratada como invariante.

Janela de admissibilidade: `max_age` = 0, logo 1 passo — χ governa a janela e o mundo tem de concordar (asserção em `run_models`).

| ação | claim de warrant | proveniência exigida | bloqueada por pausa | critério externo |
|---|---|---|---|---|
| `ACT` | Intervening on S is licensed: the record decides the proposition in a single reading, nothing on… | `post` | `ACT` | `pause_violation_rate`, `unsupported_counterfactual_rate`, `contradicted_rate`, `brier_act` |
| `OBSERVE` | Asking for a first observation is licensed whenever the record holds nothing admissible about th… | `—` | `—` | `request_resolution_rate` |
| `PROBE` | Asking for a discriminating observation is licensed when the record holds a conflict inside one … | `—` | `—` | `request_resolution_rate` |
| `COMPARE` | Comparing conditions is licensed when two readings in DIFFERENT conditions are each decided and … | `—` | `—` | `request_resolution_rate`, `unsupported_counterfactual_rate` |
| `WAIT` | Not acting is always licensed. It is the remedy an authorization leaves open, and it is the only… | `—` | `—` | `pause_violation_rate` |

Remédios de `ACT` por motivo de negação: `no_support` → `OBSERVE`, `conflict` → `PROBE`, `cross_scope` → `COMPARE`, `provenance` → `PROBE`, `pause` → `WAIT`. Nenhum deles é `ACT`, e nenhum é uma recusa sem saída — uma abstenção grátis premiaria o modelo que responde menos.

## Critérios EXTERNOS às regras de warrant (item 4)

Nenhum deles é «M2 escolheu ações diferentes». Todos com DENOMINADOR COMPARTILHADO: o conjunto elegível, ou um subconjunto definido pelo MUNDO (passos sob pausa, passos em que as condições de fato diferem), nunca pelo comportamento do modelo. `metrics.evaluate` asserta a igualdade em vez de confiar nela.

| critério | o que mede | direção |
|---|---|---|
| `contradicted_rate` | ações depois contraditas por leitura posterior NA MESMA condição | menor é melhor |
| `brier_act` | calibração da confiança de intervenção, em todos os passos elegíveis | menor é melhor |
| `request_resolution_rate` | pedidos de informação que de fato assentam a questão do passo | maior é melhor |
| `unsupported_counterfactual_rate` | `ACT` sem nenhum item de proveniência `post` | menor é melhor |
| `pause_violation_rate` | `ACT` dentro de pausa autorizada / passos sob pausa | menor é melhor |
| `deficit_inference_rate` | `ACT` ou `PROBE` onde as condições de fato diferem — o caso lido como problema de S | menor é melhor |
| `accuracy` | coincidência com a ação plantada (reportada, NÃO é o critério primário) | maior é melhor |

Critério primário por família, que é o que a figura mostra: `W-absence` → `request_resolution_rate`, `W-conflict` → `request_resolution_rate`, `W-scope` → `deficit_inference_rate`, `W-pause` → `pause_violation_rate`.

**Teto do registro.** `metrics.ceiling` recomputa a ação de referência lendo a diferença de condição do REGISTRO em vez do mundo. Em três famílias o registro decide e o teto é 1.0, então toda perda pertence a uma camada. Em `W-scope` o teto é 0.756 (piloto): uma discordância entre condições no registro pode ser um item invertido, e leitor nenhum do registro distingue. Essa folga é o sensor, não uma camada.

## Piloto — 64 células, NÃO é a grade

`python -m decision.bench --T 300 --flip 0.05 0.25 --reps 8`. Um T, um ruído de medida, amostragem completa. É um SUBCONJUNTO da grade abaixo e está rotulado assim em todo lugar onde é citado. Serve para registrar hipóteses, não para responder.

| família | critério primário | M0 | M1 | M2 | M1+pausa |
|---|---|---|---|---|---|
| `W-absence` | `request_resolution_rate` | 0.644 | 0.644 | 0.688 | 0.644 |
| `W-conflict` | `request_resolution_rate` | 0.561 | 0.561 | 0.603 | 0.561 |
| `W-scope` | `deficit_inference_rate` | 1.000 | 0.243 | 0.243 | 0.243 |
| `W-pause` | `pause_violation_rate` | 1.000 | 1.000 | 0.000 | 0.000 |

| família | acurácia (teto) | M0 | M1 | M2 | M1+pausa |
|---|---|---|---|---|---|
| `W-absence` | 1.000 | 0.945 | 0.945 | 1.000 | 0.945 |
| `W-conflict` | 1.000 | 0.944 | 0.944 | 1.000 | 0.944 |
| `W-scope` | 0.756 | 0.110 | 0.724 | 0.756 | 0.724 |
| `W-pause` | 1.000 | 0.163 | 0.163 | 1.000 | 0.957 |

## Hipóteses REGISTRADAS, por família

A condição de falha é a do paper: **se M1 não vence M0, a camada de evidência proposicional perde papel operacional; se M2 não vence M1, a camada de warrant sai da arquitetura.** As hipóteses abaixo predizem que isso acontece em parte — e predizer o resultado negativo antes de medi-lo é o que torna a medição um teste.

1. **`W-absence`: M1 = M0.** |M1 − M0| ≤ 0.01 em `request_resolution_rate` e em `accuracy`. M0 recebe a CONTAGEM de itens, então N versus B está ao alcance de um agregado escalar. Predição do desenho, não resultado: se Λ vencer aqui, o baseline estava aleijado e é o baseline que precisa de conserto.
2. **`W-conflict`: M1 = M0**, mesmo limiar e mesmo motivo.
3. **`W-scope`: M1 ≫ M0.** `deficit_inference_rate` de M0 ≥ 0.95 e de M1 ≤ 0.30 a `flip_p` = 0.05. Os dois números vêm do piloto (1.000 e 0.093); a grade os mede em 320 células por família. **Esta é a única família em que a camada Λ tem caso a fazer, e o desenho prevê isso antes de medir.** Sob `flip_p` = 0.25 a vantagem degrada e não desaparece: predição registrada de M1 ≤ 0.50 (piloto: 0.394).
4. **`W-pause`: M2 ≫ M1 e M2 = M1+pausa no critério primário.** `pause_violation_rate` = 1.0 para M0 e M1, 0.0 para M2. **Registrado antes da grade: a violação de pausa NÃO separa Ω de uma checagem de flag.** O que separa é acurácia (1.000 contra 0.957) e `unsupported_counterfactual_rate` (0.000 contra 0.044), e isso é a cláusula de proveniência, não a de pausa.
5. **Ω tem dois dentes e só um deles é a pausa.** Em `W-absence` e `W-conflict`, onde não há pausa nenhuma, M2 > M1 por ≥ 0.03 em `request_resolution_rate` e por 0.05 em `accuracy`, inteiramente pela exigência de proveniência. Se esse ganho sumir na grade, ω se reduz à checagem de flag e sai.

## Grade de decisão — PRÉ-REGISTRADA, condicional à aprovação

```bash
python -m decision.bench --T 300 600 --noise 0.05 0.3 --keep 1.0 0.7 \
    --flip 0.05 0.25 --reps 20 --jobs 8 --out out_decision_v4
```

4 famílias × 2 T × 2 ruídos de medida × 2 `keep` × 2 `flip_p` × 20 sementes = **1280 células**, 5120 linhas (uma por modelo). Versão mínima, com 5 sementes: 320 células.

Custo MEDIDO em 8 células reais (4 por T, uma por família), máquina ociosa, não estimado por aritmética: **0.27 s** por célula em T=300 e **0.54 s** em T=600. Total serial: 517 s ≈ 8.6 min. A bancada de decisão é duas ordens de grandeza mais barata que a de dinâmica (7.8 h) porque ajusta UM espaço de estados por célula e o resto é política.

Colunas por linha: `family`, `T`, `noise`, `keep`, `flip_p`, `rep`, `seed`, `model`, `chi_sha256`, `record_ceiling`, `signature_frac`, `accuracy`, `request_resolution_rate`, `unsupported_counterfactual_rate`, `contradicted_rate`, `brier_act`, `pause_violation_rate`, `deficit_inference_rate`, `n_steps`, `n_paused`, `n_scope`.

Reportada POR FAMÍLIA e nunca agregada. Agregar deixaria a família em que o warrant é decisivo pagar pelas famílias em que ele não muda nada, que é o oposto de uma condição de falsificação.

A grade **não roda** enquanto a linha de aprovação em `ESTADO_CELULA.md` estiver vazia (Modo Celular, regra 5).

## O que este desenho NÃO decide

- **Se Λ vale a pena fora de `W-scope`.** O desenho prevê empate em duas das quatro famílias e a previsão está registrada. Um empate ali não é resultado nulo da bancada: é o desenho funcionando.
- **Se o escopo temporal faz trabalho.** `max_age` é declarado e governa a janela, mas nenhuma família planta evidência velha, então a cláusula nunca é a vinculante. Declarado, não implicado.
- **Se as regras de χ são as certas.** A bancada mede se as regras declaradas sobrevivem a critérios externos, não se outro χ iria melhor. Um χ concorrente é outra célula.
- **Agentes LLM como superfície de decisão.** Fora de escopo, pela mesma razão que SIM-6 continua fechado na outra bancada.
- **Múltiplos sujeitos ou múltiplas proposições.** Um S, um `p`, um `q` de controle. As cláusulas de χ sobre S e O existem e nunca são exercidas.

