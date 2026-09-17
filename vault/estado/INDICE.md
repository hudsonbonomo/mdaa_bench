# Índice de células

> Projeção do log — se divergir, `log-celulas.md` manda.
> Status: 📋 planejada (nunca rodou; sem log) · 🔵 ativa (máx. uma)
> · ⏸ pausada · ✔ concluída. O guard de integridade cobra log só de ⏸ e ✔.
> No edtech-nll: célula ↔ plugin. Esta tabela é a lista de plugins
> trabalhados e o mapa de onde cada um parou.

| Célula | Plugin/área | Status | Última visita | Próximo passo (1 linha) |
|---|---|---|---|---|
| mdaa-autonomo | @tmulab/mdaa | ✔ | 2026-09-16 | f25caa0, 58 verdes; host-types 194L por decisão; chaves schiusa.* |
| schiusa-consome-mdaa | schiusa → @tmulab/mdaa | ✔ | 2026-09-16 | b6d3996, 264 verdes; brand por cast; install-links=true |
| bancada-aponta-mdaa | mdaa_bench → tmulab-mdaa/dist | ✔ | 2026-09-16 | CLI 07b2464d (f25caa0); env.example; R_declared real, 27 verdes, 0 skip |
| potencia-p1 | standing/pilot | ✔ | 2026-09-16 | Potência 1.000 mas variância zero — controle positivo obrigatório |
| controle-positivo-p1 | standing/pilot | ✔ | 2026-09-16 | Régua cega: TVD(ν)=0.00 em A vs C; ν ignora sinal; P1 intestável como estava |
| emenda-p1 | standing/prereg | ✔ | 2026-09-16 | 5d583f5: P1 → R_decay pesos; P1b instrumento; pendência s* declarada |
| estatuto-por-proposicao | @tmulab/mdaa status | ✔ | 2026-09-16 | b926d81, 68 verdes; B não elege; tallyWinner mantido como controle |
| estrategia-unica | standing/§3 | ✔ | 2026-09-16 | 2 estratégias: B em toda parte, P3/P5 intestáveis, sugestão exploratória resolve |
| sugestao-exploratoria | @tmulab/mdaa exploratory | ✔ | 2026-09-16 | 2dcfaae, 74 verdes; critério de ignorância; offeredStrategies é célula seguinte |
| vocabulario-worlds | standing/worlds.py | ✔ | 2026-09-17 | 7be78ee; D renomeia chave; ponta a ponta nos 3 ramos; P4/P4b desbloqueados |
| leitores-completos | CLI + readers + P1 | ✔ | 2026-09-17 | CLI 8c3cf889; readers sem hardcode; P1 pesos 1.000; P5 falsificada |
| emenda-p3-p5 | standing/prereg | 🔵 | 2026-09-17 | P3 esclarecida (ordem registrada); P5 → divergência com causa nomeada |
