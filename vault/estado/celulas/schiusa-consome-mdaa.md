# schiusa-consome-mdaa

**Status:** ✔ concluída
**Aberta:** 2026-09-16 · **Fechada:** 2026-09-16
**Repo:** C:\Users\hudso\Documents\GitHub\schiusa
**Commit final:** b6d3996 — 264 verdes, plugins/mdaa/ removido

## O que a próxima sessão precisa saber

1. **b6d3996** apaga plugins/mdaa/ e consome @tmulab/mdaa via file:.
2. **Brand nominal** resolve por cast na fronteira (2 arquivos); o acordo
   entre hospedeiro e plugin é por string, não por tipo.
3. **.npmrc install-links=true** — edits no tmulab-mdaa exigem npm install
   no schiusa para aparecer.

## Fronteira (cumprida)

**Entrou:** troca de dependência workspace por file:, remoção de plugins/mdaa/,
ajuste de imports e test:substrate.

**NÃO entrou:** mudança de comportamento, editar arquivos do MDAA.

## Decisões registradas

- plugins/query era segundo consumidor (não previsto no briefing).
- Re-typing na fronteira: CapabilityKey e PluginDefinition castados em
  plugins/query/src/plugin.ts e apps/web/lib/schiusa.ts.
- .npmrc com install-links=true em vez de next.config com turbopack.root.
- tools/corrida/projetos.mjs:44 mantém excludeDirs plugins/mdaa (inerte).
