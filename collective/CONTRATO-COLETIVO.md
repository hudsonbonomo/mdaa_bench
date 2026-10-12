# `mdaa.collective`: episódios, repertório de outros e decisão de grupo (célula do contrato, camada 8)

> Plugin `@tmulab/mdaa` · v0.4 · 9 out 2026 (com a implementação, commits 51c627a–62b5917) · escrita a partir das decisões de Hudson:
> D1–D3 de 8 out e B1–B4 de 9 out.
> Origem: Paper 8 (Collective / Multi-Agent), esqueleto v0.2 e desenho da bancada v0.1.

## O que se achou antes de decidir

O estatuto por proposição já é imune à maioria. λ = (τ, φ) só registra se existe suporte de
cada lado; não conta quanto.

Mas quatro lugares do plugin **contam**:

- a eleição por estatuto: entre as proposições que não estão em B, vence a de maior número
  de observações a favor (`status.ts:173`, achado da inspeção de 9 out);
- a réplica da camada 6, que é a reentrada na condição;
- a sugestão exploratória, que escolhe a estratégia menos observada
  (`candidate.count += 1`);
- os braços do juízo da camada 7.

Nesses quatro lugares, cinco observadores relatando o mesmo episódio valem por cinco. A porta
da dupla contagem está aberta onde se conta, não onde se rotula. O primeiro lugar corrige o
esqueleto do Paper 8. A contagem não resolve B, mas escolhe entre proposições que não estão
em conflito. Ali, a maioria entra.

## A decisão

**1. O mesmo episódio é uma fonte só (B4).** Toda contagem do plugin conta episódios
distintos, nunca observações. A dependência é decidida pela origem registrada; o plugin
não a infere. Uma observação sem `episodeId` é o seu próprio episódio. Assim, o
comportamento de hoje não muda.

**2. Os outros dão repertório, nunca evidência (B1).** O hospedeiro pode oferecer
estratégias com `origin: 'OTHERS'` (o que outras pessoas tentaram). Elas só servem à
sugestão exploratória e aparecem marcadas "de outros". Nunca entram em:
- estatuto;
- juízo;
- réplica;
- α.

O parecer de uma pessoa nunca lê o stream de outra. O plugin não tem portão de empréstimo,
porque não empresta (B2).

**3. O grupo é interseção (D2, B3).** `groupAppraisal` é uma função pura. Ela recebe o Γ
de cada membro, já liberado por ele, e devolve:
- o **conjunto** das ações admissíveis para todos, sem ordem e sem eleita;
- se esse conjunto é vazio. Nesse caso o parecer diz `INDETERMINADO` e informa se o status
  quo passa no mesmo teste;
- os bloqueios.

Regras da função:
- Silêncio é não-autorização. Um membro que não liberou o seu Γ bloqueia tudo.
- A razão de um bloqueio só aparece com a autorização de quem bloqueou. Sem ela, aparece
  só "bloqueado por um membro".
- A escolha dentro do conjunto é ato do grupo, não do plugin.

## Os objetos

```
ObservationRecordedPayload.episodeId?: string        ← mesmo episódio = mesma fonte
OfferedStrategy { strategy: string[], origin: 'HOST' | 'OTHERS' }

GroupInput  { actions: string[], statusQuo: string,
              members: [{ memberRef, released: boolean, showReasons: boolean,
                          gamma?: { [action]: { feas, auth, safe, epi } } }] }
GroupReading { admissible: string[] (ordem lexicográfica, sem ranking),
               indeterminate: boolean,
               statusQuo: { action, admissible: boolean },
               blocks: [{ action, memberRef: string | null,
                          component: 'feas'|'auth'|'safe'|'epi'|null }] }
```

## O que os tipos impedem

- `GroupReading` não tem campo `chosen` nem `best`. Um hospedeiro que queira uma ação única
  tem de escolhê-la, e isso fica com ele, à vista.
- `GroupInput` não aceita pesos, utilidades ou notas. Não há o que somar.
- `memberRef` e `component` vêm `null` quando `showReasons` é falso.
- A sugestão exploratória marca `origin: 'OTHERS'` no próprio parecer. O tipo não deixa
  esse marcador sumir.

## O que o hospedeiro tem de observar

- Gravar `episodeId` sempre que mais de um observador relatar o mesmo acontecimento.
- Obter de cada membro a liberação do Γ dele antes de chamar `groupAppraisal`, e nunca
  montar esse Γ a partir do stream do membro sem a liberação.
- Declarar o status quo, a ação "segue o plano vigente", como uma das ações. O grupo vê se
  nem ele passa.

## Pergunta de Verificação: *como verificamos que isto funciona DE VERDADE?*

1. **Dado coerente:** um grupo de 3 membros com 4 ações. A interseção tem uma ação. Um
   membro bloqueia uma ação por segurança e não autoriza mostrar a razão.
2. **Escopo declarado ANTES:**
   - (a) Duplicar k observações com o mesmo `episodeId` deixa idênticos o estatuto, a
     eleição por estatuto, a contagem de réplicas da camada 6, a sugestão exploratória e os
     braços da camada 7. Isso inclui o caso em que a duplicação inverteria a eleita.
   - (b) Um membro com `released: false` faz o conjunto ficar vazio.
   - (c) Com a interseção vazia, o resultado é `indeterminate: true` e o status quo é
     avaliado.
   - (d) Com `showReasons: false`, `memberRef` e `component` vêm nulos.
   - (e) Estratégias `OTHERS` não alteram o estatuto, o juízo nem α. Removê-las só muda a
     sugestão exploratória.
3. **Função real:** fold e função reais, sem mock.
4. **Falha sem o conserto:** contar observações em vez de episódios, na eleição por estatuto
   ou na réplica da camada 6, tem de deixar o item (a) vermelho.
5. **Reporte na entrega.**

## Fronteira

**Entra:** o `episodeId` e a contagem por episódio, a origem do repertório,
`groupAppraisal`, o modo de CLI e os testes acima.

**Não entra:**
- a moldura de limites vinda da população;
- a forma de obter a liberação do Γ (é do hospedeiro);
- a interpretação de terceiro (célula própria, ponto ainda pendente).

## Ponto aberto: para Hudson

**A.** A regressão zero proposta é esta: sem `episodeId`, nada muda. Ela muda o hash do
`dist/adjustment.js`. A bancada do Paper 6 está fixada no commit `04e71bb` e continua
íntegra, porque o guardião dela recusaria o dist novo. O suplemento do Paper 6 também não
muda. Recomendo seguir assim e registrar, no README do `tmulab-mdaa`, que o Paper 6 cita
`04e71bb`.

## Episódio com vários relatos (v0.3, 9 out) [precisa do ok de Hudson]

Na camada 7, o código fez "o primeiro registro fala pelo episódio". Isso depende da ordem de
chegada, e é a mesma coisa que "a mais recente vence" com o sinal trocado. A série já recusou
esse tipo de regra.

Proposta: o sinal de um episódio é o **conjunto** dos sinais relatados, deixando UNCLEAR de
fora.
- **No estatuto:** um episódio com BETTER e WORSE dá suporte aos dois lados. O conflito entre
  observadores do mesmo episódio é B, e B informa.
- **Nas contagens** (eleição, réplica, sugestão, braços): o episódio conta **uma vez**. Conta
  como BETTER só se todos os relatos forem BETTER, e como WORSE só se todos forem WORSE.
  Episódio misto fica fora da razão, como UNCLEAR. Na sugestão exploratória, que mede
  ignorância e não sinal, ele conta como episódio observado.
- Nenhuma regra depende da ordem dos relatos.

## Depois da implementação (v0.4, 9 out): registrado como ficou

- **Réplica da camada 6.** A sequência de retornos não muda. O veredito de cada retorno
  (`majority()`) passa a contar episódios, e o episódio misto fica de fora, como UNCLEAR.
  Por isso o hash de `dist/adjustment.js` mudou para `a701183d…`, enquanto o Paper 6 continua
  fixado em `04e71bb`.
- **Marcador `OTHERS`.** Aparece só quando a estratégia entra no repertório apenas pela
  oferta de outros. Se ela já está no registro da pessoa, ou se o hospedeiro também a
  ofereceu, o marcador não aparece.
- **"Estatuto idêntico" sob duplicação.** Quer dizer o mesmo estado de cada proposição, a
  mesma eleita e as mesmas contagens. O retrato continua listando cada relato, com a ordem
  da evidência, porque é proveniência e não peso.
- **Bloqueios.** Há um bloqueio por par (ação, membro), com o primeiro componente que falha,
  na ordem feas, auth, safe, epi. O silêncio conta como `auth`.
- **Recusas de `groupAppraisal`.** A função recusa ações repetidas e um status quo que não
  esteja entre as ações.
- **Membro sem autorização.** Cada membro que bloqueia sem autorizar a exibição vira uma
  entrada nula. O **número** de bloqueadores fica visível; quem são e por quê, não. É o
  conflito preservado sem expor ninguém.
- **Modo `episodes` da CLI.** A réplica e o juízo só são calculados quando vêm os blocos
  `adjustment` e `norms`. O juízo lê a fatia `warranting` (E2).
