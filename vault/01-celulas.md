# O protocolo de células

## O que é uma célula

Uma **célula** é a unidade de trabalho do modo: um objetivo pequeno, com
fronteira explícita, dimensionado para caber em UMA sessão de foco
(tipicamente 30–120 min). Exemplos: "fetcher OpenAlex retorna JSON
normalizado", "corrigir o bug do token no login", "esqueleto do plugin
vigília com contrato inject/provide".

Uma célula tem: **nome**, **fronteira** (entra / NÃO entra), **critério de
pronto** verificável, e **estado anotado** ao fechar.

## Várias células em paralelo

Células **pausadas coexistem** — é o estado normal do método, especialmente
num projeto all-plugins onde célula ↔ plugin. As regras:

- No máximo **UMA célula 🔵 ativa** por vez.
- `vault/estado/INDICE.md` é o mapa: toda célula tem linha lá, com status
  (🔵 ⏸ ✔) e o próximo passo em 1 linha. No edtech-nll, o índice É a lista
  de plugins trabalhados.
- Cada célula tem seu arquivo em `vault/estado/celulas/<slug>.md` com o
  estado completo — é ele que torna "voltar àquela célula" um gesto direto:
  `/celula <nome>` religa em 5 linhas, de onde parou.
- Célula futura entra como **📋 planejada**: linha no índice, sem log (nunca
  rodou; registrar seria ficção); arquivo em `celulas/` opcional, para a
  fronteira já rascunhada. Abrir promove 📋 → 🔵.
- Trocar de célula = fechar a ativa pelo ritual (`pausar`) + abrir a outra.
  Nunca trocar "por cima" sem anotar.

## O ciclo

### 1. ABRIR (ou retomar) — skill `celula`
- `/celula <nome>`: retomada direcionada — carrega `celulas/<slug>.md`,
  religação em ≤5 linhas, executa o próximo passo IMEDIATAMENTE.
- `/celula` com ativa: retoma a ativa direto.
- `/celula` sem ativa: índice resumido (só pausadas + "nova") e escolha.
- Abertura nova: propor nome + fronteira em uma frase + primeiro passo.
  Confirmar. Criar o arquivo da célula e a linha 🔵 no índice.

### 2. TRABALHAR
- Só o que está dentro da fronteira. Ideias de fora →
  `estado/estacionamento.md` (capturar em 1 linha e voltar; trocar de
  célula é direito do humano — sempre pelo ritual).
- Passos pequenos e verificáveis. Build/typecheck como pulso (regra 4).
- Decisões tomadas → anotar na hora no arquivo da célula (senão serão
  rediscutidas).

### 3. FECHAR — skill `pausar`
- Fatos no log (append-only) → projeção em `celulas/<slug>.md` → linha do
  índice atualizada (⏸ ou ✔) → CELULA-ATUAL vira ponteiro "nenhuma ativa"
  → próximo passo único e <5 min → ideias no estacionamento → despedida leve.

## A regra bicondicional

**Retomável ⟺ anotado.** Tudo que a próxima sessão precisa saber tem que
estar no estado; nada vive só na memória (humana ou do agente). O log é a
fonte de verdade; índice e arquivos de célula são projeções dele.

## Dimensionamento

- Célula boa: cabe numa sessão, tem UM entregável, critério de pronto
  binário (build verde + comportamento X).
- Grande demais: dividir ANTES de começar, nunca no meio do cansaço.
- Pequena demais: se o fechamento custa mais que o trabalho, fundir com a
  vizinha.

## Células inacabadas

São o estado normal do método, não dívida. Uma célula pausada não quebra
nada (fronteiras!). Ela espera no índice, com a isca do próximo passo pronta.
