# estatuto-por-proposicao

**Status:** ✔ concluída
**Aberta:** 2026-09-16 · **Fechada:** 2026-09-16
**Repo:** C:\Users\hudso\Documents\GitHub\tmulab-mdaa
**Commit:** b926d81 — 68 verdes, 0 vermelhos

## O que a próxima sessão precisa saber

1. **B não elege.** Nenhuma proposição elege enquanto a de maior sustentação
   estiver em B — regra no CONTRATO-ESTATUTO.md:37.
2. **tallyWinner mantido** como instrumento do controle negativo — exportado
   de policy.ts, não chamado por recommend.ts.
3. **Identidade de proposição** por conjunto exato de estratégia × condições
   (não label-level includes). Desempate por seq mais antigo.
4. **Dois testes existentes editados** (recommendation.test.mjs,
   sovereignty.test.mjs) — codificavam a eleição que o contrato abole.
5. **Estratégia excluída** (REFUSED + excludedStrategies) é ignorada antes
   de poder vencer ou bloquear.

## Fronteira (cumprida)

**Entrou:** estatuto T·F·B·N por proposição; B não elege; substituir
tallyWinner; contrato copiado; testes com PVs literais.
**NÃO entrou:** declaredStrategy, standing, decisão, mdaa_bench, schiusa.
