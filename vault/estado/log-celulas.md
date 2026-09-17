# Log de células — append-only

> Uma entrada por fechamento de célula, mais recente por ÚLTIMO.
> NUNCA editar ou apagar entradas passadas. Formato em `../02-estado.md`.
> Se este log e o CELULA-ATUAL.md divergirem, ESTE arquivo manda.

## mdaa-autonomo — ✔ concluída (2026-09-16)

**Objetivo:** @tmulab/mdaa compila e testa com zero dependências @schiusa/*.
**Commit:** f25caa0 — 58 verdes, build limpo, deps runtime vazio.
**Decisões:** host-types.ts 194L (espelho do hospedeiro, não editado);
chaves de capability com prefixo schiusa.* (decisão quando houver 2º host).
**Estacionamento:** encolher PersonScope; anotar chaves no CONTRATO-HOSPEDAGEM.

## schiusa-consome-mdaa — ✔ concluída (2026-09-16)

**Objetivo:** schiusa consome @tmulab/mdaa como file:, plugins/mdaa/ removido.
**Commit:** b6d3996 — 264 verdes, +62/-4803 linhas.
**Decisões:** brand por cast na fronteira (2 arquivos); .npmrc install-links=true;
plugins/query era segundo consumidor não previsto.
**Estacionamento:** brand por string; install-links=true.

## bancada-aponta-mdaa — ✔ concluída (2026-09-16)

**Objetivo:** religar MDAA_PLUGIN_DIST para tmulab-mdaa/dist, provar R_declared.
**standing-cli.js SHA-256:** `07b2464d…9229db7a` (tmulab-mdaa f25caa0).
**Testes:** 27 verdes, 0 skipped, R_declared contra CLI real.
**Estacionamento:** appearingIds é partição, não duplicação.

## potencia-p1 — ✔ concluída (2026-09-16)

**Objetivo:** primeira execução real — potência de P1 com sementes-piloto 901–905.
**Resultado:** potência 1.000 para Δ=0.10 (TVD e desacordo exatamente 0.00,
variância zero). Hudson identifica passagem vacuosa: ν ignora sinal, medida
pode ser cega. Controle positivo A vs C obrigatório antes da grade.
**Bug corrigido:** readers.py snake_case → camelCase na policy.
**Estacionamento:** controle-positivo-p1; vocabulario-worlds.

## controle-positivo-p1 — ✔ concluída (2026-09-16)

**Objetivo:** testar se as medidas de P1 distinguem mundos que devem diferir.
**Resultado:** A vs C dá 0.00 — régua cega. ν é determinística de (escopo, idade),
ignora sinal. A vs B logged separa (0.50). Emenda de P1 necessária.
**Estacionamento:** emenda-p1 (célula própria).

## emenda-p1 — ✔ concluída (2026-09-16)

**Objetivo:** emendar P1 no preregistro — régua cega motivou mudança de leitor e medida.
**Commits:** 5d583f5 (emenda v1.2, freeze) + 56d8e2f (controle positivo, estado).
**Pendência declarada:** estratégia-alvo única pode afetar P3/P5 — célula estrategia-unica.
**Ponto de partida da próxima:** a pergunta não é "quantas estratégias", é se os mundos
precisam produzir divergência de escolha para que previsões sobre parecer signifiquem algo.

## estatuto-por-proposicao — ✔ concluída (2026-09-16)

**Objetivo:** estatuto T·F·B·N por proposição; B não elege, informa.
**Commit:** b926d81 — 68 verdes. tallyWinner mantido como controle negativo.
**Decisões:** identidade por conjunto exato; desempate por seq mais antigo;
B com mais suporte bloqueia eleição (leitura literal do contrato);
estratégia excluída ignorada antes de vencer ou bloquear.

## estrategia-unica — ✔ concluída (2026-09-16)

**Objetivo:** investigar se mundos precisam de divergência de escolha para P3/P5.
**Resultado:** duas estratégias necessárias mas não suficientes. B aparece em quase
todo lugar (ruído 0.15); B-blocking nunca disparou (0/160). P3 e P5 intestáveis
como escritas. Resolvido pelo CONTRATO-SUGESTAO-EXPLORATORIA.
**Pendências:** readers.py hardcoda s_star; warrant_window/τ; emenda de P3/P5.

## sugestao-exploratoria — ✔ concluída (2026-09-16)

**Objetivo:** sugestão exploratória por ignorância quando nada elege.
**Commit:** 2dcfaae — 74 verdes. Critério nunca lê sinal; PV6 controle negativo.
**Decisões:** offeredStrategies=[] (fallback); ACCEPTED sobre sugestão com marca;
nota no contrato sobre repertório limitado ao registro.
**Célula seguinte:** offeredStrategies na entrada de generateRecommendation.

## vocabulario-worlds — ✔ concluída (2026-09-17)

**Objetivo:** mundo D renomeia chave (não valor); eventos no formato CLI.
**Commit:** 7be78ee — 28 verdes. Ponta a ponta nos 3 ramos bate com §3.
**Decisão:** ramo parcial = "nenhum valor tem correspondente" (caso extremo);
valueMap com valor que registros não carregam, contido por assert.

## leitores-completos — ✔ concluída (2026-09-17)

**Objetivo:** CLI expõe estatuto; readers.py reporta eleição; P1 por pesos.
**CLI:** SHA 8c3cf889 (uncommitted tmulab-mdaa). 81 verdes.
**P1:** potência 1.000 Δ=0.10 (pesos). α inerte para R_decay.
**P3:** B confirmado, ordem parcial (ruído sobrepõe faixas).
**P5:** falsificada — R_declared nunca elege, divergência 76/80. Emenda v1.3.

## emenda-p3-p5 — ✔ concluída (2026-09-17)

**Objetivo:** emenda v1.3 — P3 esclarecida, P5 passa a prever divergência.
**Commits:** cb17ad6 (prereg + freeze) + fd9d675 (código + sondas + estado).
**Resultado:** todas as previsões agora testáveis. Grade pode rodar.

## grade-v1 — ✔ concluída (2026-09-17)

**Objetivo:** primeira execução da grade — sementes 1–20, 20 células, 3 leitores.
**Commit:** b085568 — 400 runs, 26.87s. CLI 8c3cf889 (tmulab-mdaa 4503cc1).
**Resultado:** 7/7 previsões PASS. Nenhum FAIL.
**Diagnóstico:** D T=160 total → 20% pré-τ1 voltam AGED (α sobre vocabulário).
