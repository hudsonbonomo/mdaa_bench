# mdaa-autonomo

**Status:** ✔ concluída
**Aberta:** 2026-09-16 · **Fechada:** 2026-09-16
**Repo:** C:\Users\hudso\Documents\GitHub\tmulab-mdaa
**Commit final:** f25caa0 — 58 testes verdes, zero dependências @schiusa/*

## O que a próxima sessão precisa saber

1. **f25caa0** é o commit autônomo: 58 verdes, build e typecheck limpos,
   dependencies runtime vazio.
2. **host-types.ts tem 194 linhas por decisão** — é espelho fiel do
   hospedeiro (PersonScope arrastou 15 tipos transitivos), não versão
   editada. Encolher PersonScope é célula própria (ver estacionamento).
3. **As chaves de capability carregam o prefixo `schiusa.`**
   (`schiusa.event-journal`, `schiusa.person-substrate`). Funciona porque
   hoje o único hospedeiro é o schiusa; vira decisão quando existir um
   segundo hospedeiro.

## Fronteira (cumprida)

**Entrou:** resolver os 21 imports externos de @schiusa/* para que
@tmulab/mdaa compile e teste com ZERO dependências do schiusa.

**NÃO entrou:** mudança de comportamento, recurso novo, tocar no schiusa ou
mdaa_bench.

## Decisões registradas

- sdk.ts (124 linhas): copiado de packages/plugin-sdk, branding de
  CapabilityKey preservado.
- host-types.ts (194 linhas): tipos do hospedeiro copiados; PersonScope
  arrastou 15 tipos transitivos (aceito, não editado).
- Chaves de capability: { id: "schiusa.event-journal", version: "1.0.0" }
  e { id: "schiusa.person-substrate", version: "1.0.0" }.
- Host de teste: host.mjs (144 linhas) + journal.mjs (179 linhas).
  openScope throws — nenhum teste usa.
