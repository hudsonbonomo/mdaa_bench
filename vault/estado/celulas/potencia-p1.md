# potencia-p1

**Status:** ✔ concluída
**Aberta:** 2026-09-16 · **Fechada:** 2026-09-16
**Autorização:** Hudson, 16/09/2026 — sementes-piloto 901–905.

## O que a próxima sessão precisa saber

1. **Potência 1.000 para Δ=0.10** — mas variância zero. As duas medidas
   (TVD sobre ν, desacordo de parecer) são 0.00 em todas as observações.
   NÃO é confirmação forte: ν ignora sinal, então A e B unlogged coincidem
   por construção — e coincidiriam com qualquer mundo sem saída de escopo.
2. **Controle positivo obrigatório:** A vs C com as mesmas medidas. Se der
   0.00, a medida é cega e P1 não significa nada. Célula: controle-positivo-p1.
3. **Bug corrigido em readers.py:** policy enviada em snake_case, CLI espera
   camelCase. Tudo saía AGED antes da correção.
4. **Δ=0.10 fica** (Δ mínimo para 0.80 = 0.05, piso do sweep). Nenhuma
   emenda de Δ necessária.

## Fronteira (cumprida)

**Entrou:** sementes-piloto 901–905, potência de P1, correção do readers.py.
**NÃO entrou:** grade 1–20, emenda do preregistro.

## Decisões registradas

- Réplicas não afetam geração do mundo (make_world não tem o parâmetro).
  Piloto rodou com réplicas=1.
- "P1 confirmada" NÃO escrita em lugar nenhum — Hudson identifica possível
  passagem vacuosa. Controle positivo decide.
