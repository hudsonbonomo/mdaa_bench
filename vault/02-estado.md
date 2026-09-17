# Formato dos registros de estado

Cinco peças vivem em `vault/estado/`:

## 1. INDICE.md — a lista de células (e de plugins)

Uma linha por célula, sempre atualizada pela skill `pausar`:

```markdown
| Célula | Plugin/área | Status | Última visita | Próximo passo (1 linha) |
|---|---|---|---|---|
| Fetcher OpenAlex | nll-vigilia | ⏸ | 2026-08-24 | rodar `pnpm test` e ler 1º erro |
```

Status: 📋 planejada · 🔵 ativa (máx. UMA) · ⏸ pausada · ✔ concluída.
📋 = célula futura: nunca rodou, logo sem entrada no log (inventar entrada
seria ficção no append-only). Arquivo em `celulas/` é OPCIONAL na 📋 — pode
existir para guardar a fronteira já rascunhada. Abrir promove 📋 → 🔵
(criando ou completando o arquivo); o guard exige log apenas de ⏸ e ✔.
No edtech-nll, célula ↔ plugin: **este índice É a lista de plugins
trabalhados** e de onde cada um parou.

## 2. celulas/<slug>.md — o estado completo de CADA célula

```markdown
# Célula: <nome>
**Plugin/área:** <pacote ou tema>
**Aberta em:** <data> · **Status:** 🔵 | ⏸ | ✔
**Fronteira:** entra: <...> | NÃO entra: <...>
**Último fato:** <o que foi concluído por último, com caminho de arquivo>
**Build/typecheck:** verde | vermelho (<erro em 1 linha>)
**Decisões desta célula:** <lista curta — nunca rediscutir sem fato novo>
**Contexto mínimo (≤5 linhas):** <só o indispensável para religar>

## ➜ PRÓXIMO PASSO (executável em <5 min, sem pensar)
<UMA ação concreta>
```

## 3. CELULA-ATUAL.md — o ponteiro da ativa

Com célula ativa: cópia da projeção dela (formato acima).
Sem célula ativa: "nenhuma célula ativa · N pausadas — ver INDICE.md",
com as 3 pausadas mais recentes e seus próximos passos (1 linha cada).

## 4. log-celulas.md — o registro (append-only, NUNCA editar o passado)

Uma entrada por fechamento, mais recente por último:

```markdown
---
## <AAAA-MM-DD HH:MM> · Célula: <nome>
**Fatos:** <o que foi feito; arquivos com caminho exato>
**Decisões:** <para nunca rediscutir sem fato novo>
**Build:** verde | vermelho
**Próximo passo definido:** <o mesmo do celulas/<slug>.md>
**Nota pessoal (opcional):** <1 linha>
```

## 5. estacionamento.md — ideias capturadas (1 linha cada)

```markdown
- [<data>] <ideia em uma linha> (contexto: célula <nome>)
```

Promovida a célula → marcar ✔ e o nome da célula criada. Nada é apagado.

## Princípio de projeção

O log é a fonte de verdade. INDICE.md, CELULA-ATUAL.md e celulas/*.md são
**projeções** dele: se qualquer projeção divergir do log, o log manda e a
projeção se corrige. (Retomável ⟺ anotado.)
