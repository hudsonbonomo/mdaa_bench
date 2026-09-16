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
