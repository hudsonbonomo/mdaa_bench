# vocabulario-worlds

**Status:** ✔ concluída
**Aberta:** 2026-09-17 · **Fechada:** 2026-09-17
**Commit:** 7be78ee — 28 verdes

## O que a próxima sessão precisa saber

1. **Mundo D renomeia CHAVE** (c1→c1_prime), não valor. Eventos no formato
   do CLI (KEY_RENAMED, RECONCILED). Verificação ponta a ponta nos três ramos.
2. **Ramo parcial** é, por construção, "nenhum valor tem correspondente" —
   caso extremo. valueMap contém "legacy", que os registros não carregam
   (assert COND_VALUE not in MAPPED_VALUES). Ramo intermediário é melhoria
   futura, não bloqueante.
3. **P4/P4b desbloqueados** — o mundo D agora testa o quarto estado
   (unevaluable), não escopo de novo.
