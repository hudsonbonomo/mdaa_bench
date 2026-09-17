# Índice de células

> Projeção do log — se divergir, `log-celulas.md` manda.
> Status: 🔵 ativa (máx. uma) · ⏸ pausada · ✔ concluída · 📋 planejada

| Célula | Plugin/área | Status | Última visita | Próximo passo (1 linha) |
|---|---|---|---|---|
| [Fetcher OpenAlex](celulas/fetcher-openalex.md) | `src/fetcher/` | ✔ | 2026-08-20 | — |
| [Normalizador de autores](celulas/normalizador-autores.md) | `src/normalizar/` | ✔ | 2026-08-21 | — |
| [Índice invertido](celulas/indice-invertido.md) | `src/indice/` | 🔵 | 2026-08-22 | rodar `node --test` e ler o primeiro erro |

### Segunda onda — sem link, como no índice real

| Célula | Plugin/área | Status | Última visita | Próximo passo (1 linha) |
|---|---|---|---|---|
| Deduplicação por DOI | `src/dedupe/` | ⏸ | 2026-08-19 | decidir se DOI ausente vira chave composta (`titulo` \| `ano`) |
| Exportador CSV | `src/export/` | 📋 | — | depois do índice invertido |
| Cache de requisições | `src/cache/` | 📋 | — | só quando o fetcher doer |
