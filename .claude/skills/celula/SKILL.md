---
name: celula
description: Abrir, retomar ou escolher uma célula de trabalho no Modo Celular. Use SEMPRE que o usuário disser /celula (com ou sem nome de célula), "vamos retomar", "onde paramos", "volta para a célula X", "abrir célula", "continuar o plugin Y", "quais células tenho", "lista as células", ou ao início de qualquer sessão num projeto que contenha vault/estado/. Use também quando o usuário pedir tarefa nova sem célula aberta.
---

# Abrir, retomar ou escolher célula

## Fontes de estado
- `vault/estado/INDICE.md` — a lista de todas as células (status, próximo passo)
- `vault/estado/CELULA-ATUAL.md` — projeção da célula ATIVA (no máximo uma)
- `vault/estado/celulas/<slug>.md` — estado completo de cada célula

## Guard de integridade (ANTES de qualquer roteamento)

Toda célula ⏸ ou ✔ do `INDICE.md` deve ter ≥1 entrada em `log-celulas.md`
(📋 planejadas estão isentas — nunca rodaram). Se o log tiver menos do que o
índice implica: PARE, acuse "log encolhido" listando as células sem entrada,
reconstrua as ausentes a partir de `INDICE.md` + `celulas/*.md` (marcadas
`[reconstruída]`) e só então prossiga.

## Roteamento (decida primeiro qual caso é)

**A. O usuário nomeou uma célula** ("/celula vigilia", "volta pra célula do
fetcher", "continuar o plugin X"):
1. Localize no `INDICE.md` por correspondência aproximada de nome/plugin.
   Ambíguo → mostre só as 2-3 candidatas e pergunte qual.
2. Se OUTRA célula estiver 🔵 ativa: diga "a célula <Y> está ativa — fecho
   ela primeiro" e execute o ritual completo da skill `pausar` para ela.
3. Carregue `celulas/<slug>.md` → religação em ≤5 linhas (célula, último
   fato, build, PRÓXIMO PASSO) → copie a projeção para `CELULA-ATUAL.md`,
   marque 🔵 no índice → pergunte "Seguimos?" → execute o próximo passo
   pequeno IMEDIATAMENTE.
4. Célula pedida está 📋 (planejada): é ABERTURA, não retomada — crie ou
   complete `celulas/<slug>.md` (a 📋 pode já ter o arquivo, com a fronteira
   rascunhada), promova 📋 → 🔵 e siga o fluxo de abertura.

**B. Sem nome, e existe célula 🔵 ativa:** retome-a direto (religação ≤5
linhas + executar o próximo passo). Não mostre o índice.

**C. Sem nome, nenhuma ativa, mas há ⏸ pausadas:** mostre o índice resumido
— as ⏸ pausadas e 📋 planejadas, uma linha cada: `nome · próximo passo` — mais a opção
"célula nova". Pergunte qual abrir. Máximo ~8 linhas; se houver mais
células, mostre as 6 mais recentes e diga quantas outras existem.

**D. Nenhuma célula existe (ou o usuário pediu célula nova):** proponha
nome + fronteira em uma frase ("Célula: X — entra: A, B; NÃO entra: C") +
primeiro passo. Confirme. Crie `celulas/<slug>.md`, linha 🔵 no índice,
e a projeção em `CELULA-ATUAL.md`.

Slug: nome em kebab-case sem acentos (ex.: "Fetcher OpenAlex" → `fetcher-openalex`).

## Durante o trabalho
Respeite as sete regras do `CLAUDE.md`. Ideias fora do escopo →
`vault/estado/estacionamento.md`, sem bloquear nem seguir sozinho: o humano
decide se troca de célula (e trocar = pausar a atual + abrir a outra, sempre
pelo ritual).

## Nunca
- Nunca abra listando tudo que falta no projeto (paralisa). O índice
  resumido do caso C é o máximo de panorama permitido.
- Nunca reabra decisões registradas como decididas sem fato novo.
- Nunca trate células pausadas como pendência culposa — coexistir pausadas
  é o estado normal do método.
- Nunca tenha duas células 🔵 ativas ao mesmo tempo.
