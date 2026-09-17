# grade-v1

**Status:** ✔ concluída
**Aberta:** 2026-09-17 · **Fechada:** 2026-09-17
**Commit:** b085568 — 400 execuções, 7 previsões PASS
**CLI:** SHA 8c3cf889...26302543 (tmulab-mdaa 4503cc1)

## O que a próxima sessão precisa saber

1. **Todas as 7 previsões passam.** P1 TOST equivalente (média 0.033–0.040);
   P1b TVD 0.500/0.000; P2 1.00; P3 B 100% + decay 95%; P4 P=R=1.00;
   P4b 1.00; P5 divergência 100% por B_blocking.
2. **20 células × 20 sementes = 400 runs em 26.87s.** Réplicas=1 (make_world
   não tem o parâmetro). D usa RNG do gerador (não force_reconciliation).
3. **Diagnóstico:** D T=160 total → 20% dos pré-τ1 voltam AGED (α funciona
   sobre vocabulário reconciliado). Informativo, não limiar.
4. **Resultados em** standing/resultados/grid_v1_{rows.csv, summary.json,
   predictions.md}.
