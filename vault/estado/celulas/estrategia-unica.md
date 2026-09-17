# estrategia-unica

**Status:** ✔ concluída
**Aberta:** 2026-09-16 · **Fechada:** 2026-09-16
**Autorização:** sementes-piloto 901–905.

## O que a próxima sessão precisa saber

1. **Duas estratégias necessárias mas não suficientes.** Desbloqueiam R_decay
   e criam coexistência T/B, mas não desbloqueiam P3 (warrant_window corta τ)
   nem P5 (readers.py hardcoda s_star).
2. **B aparece em quase todo lugar** com ruído 0.15 — um WORSE basta. A regra
   "B não elege" produz "nada nunca elege" na prática. Resolvido pelo
   CONTRATO-SUGESTAO-EXPLORATORIA (sugestão por ignorância, não desempenho).
3. **B-blocking nunca disparou** (0/160 runs). T sempre tem mais suporte que B
   quando coexistem.
4. **CLI não mudou** (07b2464d) — status.ts não está no grafo de imports do
   standing-cli.js.

## Três pendências para a bancada

- readers.py hardcoda s_star → R_declared precisa reportar a estratégia eleita
- warrant_window/τ: janela corta o bloco que deveria mostrar a ordem em P3
- P3 e P5 intestáveis como escritas — emenda necessária após vocabulário de sinal
