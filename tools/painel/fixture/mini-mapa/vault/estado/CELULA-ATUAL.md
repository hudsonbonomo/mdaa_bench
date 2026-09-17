# Célula atual

**Célula:** Índice invertido — [projeção completa](celulas/indice-invertido.md)
**Aberta em:** 2026-08-22
**Último fato:** tokenizador escrito; falta o merge dos postings
**Build/typecheck:** VERMELHO — 3 testes falhando em `indice.test.mjs`

**Contexto mínimo (≤5 linhas):**
O índice invertido é o que faz a busca sair de O(n) para O(1) por termo.
O merge dos postings é a parte chata: ordenar por docId e deduplicar.

## ➜ PRÓXIMO PASSO (executável em <5 min, sem pensar)
Rodar `node --test src/indice/` e ler o PRIMEIRO erro — sem consertar nada ainda.
