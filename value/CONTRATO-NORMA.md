# `mdaa.norm`: a norma como registro e o juízo relativo a ela (célula do contrato, camada 7)

> Plugin `@tmulab/mdaa` · v0.6 · 9 out 2026 (com a emenda E3, decidida por Hudson) · escrita a partir das decisões de Hudson:
> D1–D3 de 8 out e B1–B4 de 9 out.
> Origem: Paper 7 (Evaluation / Value), esqueleto v0.2 e desenho da bancada v0.1.

## O que se achou antes de decidir

Hoje o plugin elege uma estratégia por estatuto: a proposição de maior sustentação, desde
que não esteja em B. Quando nada é eleito, ele sugere a estratégia menos observada. Em
nenhum desses dois caminhos entra um critério de "melhor". Isso vem do Paper 4, que deixou
J em aberto, e do Paper 6, que recusou ajustar a política por desempenho.

A camada 7 é o lugar desse critério. Mas a série já fechou de onde ele não pode vir: do
desenho do sistema, do comportamento da pessoa e de uma soma que transforma conflito em
média.

## A decisão

**Um juízo de "melhor" só existe relativo a uma norma que é um registro, e só elege dentro
de Γ.**

A norma pode chegar de dois modos:

- **O hospedeiro propõe.** A norma entra como `PENDING` e só passa a valer quando a pessoa
  confirma. O silêncio da pessoa não confirma.
- **A própria pessoa declara.** A norma entra já confirmada.

Toda norma diz:
- a medida que lê;
- o escopo de condições em que vale;
- a regra declarada de decisão: o mínimo de episódios por braço e a margem.

O juízo assume um destes cinco estados (B1):

| Estado | Quando ocorre | Como se sai dele |
|---|---|---|
| `SEM_NORMA` | Não há norma confirmada no escopo | A pessoa declara ou confirma uma norma (ato sobre o conteúdo) |
| `INSUFICIENTE` | Há norma, mas a evidência sob protocolo não alcança o mínimo; ou só existe registro observacional (B3) | Mais episódios sob protocolo |
| `JUSTIFICADO` | A diferença entre os braços é maior ou igual à margem | — (elege a estratégia de melhor resultado) |
| `NÃO_JUSTIFICADO` | Os braços estão completos e a diferença fica abaixo da margem: "nenhuma diferença" | — |
| `EM_CONFLITO` | Duas normas confirmadas elegem estratégias opostas e não há prioridade confirmada | A pessoa declara uma prioridade entre normas (ato sobre a ordem) |

Quando há duas normas e uma delas **se cala** (zero episódios da sua medida para o par),
isso não é estado: decide a outra norma. Já uma norma com dados insuficientes não se cala.
Ela torna o juízo inteiro `INSUFICIENTE`, porque não se pode afastar a oposição dela.

Quando o juízo é `JUSTIFICADO`, a estratégia eleita entra no parecer como estratégia, com
proveniência `INFERRED`. Isso só acontece se ela estiver em Γ e se o estatuto dela não
estiver em B (D3).

Sempre que a camada 7 está ativa, o parecer ganha um campo **aditivo**, `judgment`, com o
estado, as normas e as versões, e a frase. A frase diz o porquê, inclusive em `INSUFICIENTE`,
e aí nomeia as saídas e o custo de cada uma. Nos demais campos, fora de `JUSTIFICADO`, o
parecer é exatamente o de antes da camada 7.

O que fica fora do juízo:
- A pausa autorizada nunca é lida: nem como perda, nem como ganho (B2). No plugin de hoje,
  a pausa autorizada é o estado de jornada `PAUSED`. Ele é registrado pelo evento
  `learning_journey.status_changed`, que só a pessoa emite. Durante a pausa, nenhuma
  observação entra. O juízo não lê esse evento nem os saltos de `seq` que a pausa deixa.
- Os intervalos entre observações também não são lidos. A inatividade não declarada não
  existe para o juízo.
- O comportamento é evidência de cumprimento, na medida que a norma lê. Nunca é fonte de
  norma (B4).

## Os objetos

Todos os eventos novos vão no stream `mdaa-<personId>`.

```
mdaa.norm.proposed   { normId, version, reads: measureKey, scope: Record<string,string>,
                       rule: { minPerArm, margin },
                       provenance: { origin: 'INFERRED' | 'DECLARED', recordedBy } }
mdaa.norm.reviewed   { normId, version, review: 'CONFIRMED' | 'REJECTED' }   ← só a pessoa
mdaa.norm.retired    { normId }                                              ← só a pessoa
mdaa.norm.priority   { higher: normId, lower: normId }                       ← só a pessoa
mdaa.protocol.consented { protocolId, strategies: string[][], probabilities: number[] }  ← só a pessoa
mdaa.protocol.assigned  { protocolId, assignmentId, strategy, p }    ← gravado ANTES da observação
mdaa.protocol.withdrawn { protocolId }                               ← só a pessoa; retira o consentimento
```

`ObservationRecordedPayload` ganha dois campos opcionais: `measure?: string` e
`assignmentId?: string`. Uma observação sem `measure` não é lida por nenhuma norma. Uma
observação sem `assignmentId` é observacional e nunca justifica.

Dentro do braço, o mínimo conta **episódios distintos**, como define a célula
CONTRATO-COLETIVO.

O juízo é uma função pura, `judge(...)`, que devolve:

```
JudgmentReading { state, elected?, perNorm: [{ normId, version, verdict,
                  arms: { [strategy]: { episodes, better } }, diff }], sentence }
```

**Γ no plugin de hoje (inspeção de 9 out).** O plugin não tem factível, seguro nem garantido.
A autorização existe só como `excludedStrategies` nas decisões da pessoa. Por isso o Γ da
camada 7 se monta em três partes:

| Componente | De onde vem |
|---|---|
| `feasible` e `safe` | do hospedeiro, a cada chamada |
| `auth` | da união dos `excludedStrategies` das decisões da pessoa na jornada (na CLI pura, entra como `excludedStrategies`, como na `standing-cli`) |
| `epi` | do estatuto: a estratégia tem de ser T |

O escopo da norma usa o predicado `inScope` que já existe em `status.ts`. Não se cria outro.

## O que os tipos impedem

- `review`, `priority` e `protocol.consented` exigem `requirePersonAuthority`. Um
  hospedeiro não confirma norma em nome da pessoa.
- `NormProposedInput` não tem campo de peso. Duas normas nunca se somam, e o tipo não
  deixa.
- A assinatura de `judge` não recebe nem eventos de pausa nem tempo de relógio, só `seq` e
  episódios. Com isso, a invariância da pausa vale por construção, e o teste a confirma.
- `JudgmentReading` não tem campo de nota nem de escore da pessoa (D2): o que se julga são
  estratégias.

## O que o hospedeiro tem de observar

Para usar a camada 7, o hospedeiro precisa fazer três coisas:
- propor a norma com a medida e a regra;
- apresentá-la à pessoa e registrar a revisão dela;
- se quiser justificativas, pedir à pessoa o consentimento para um protocolo de alternância
  e gravar cada sorteio **antes** de entregar a estratégia.

Sem protocolo, o juízo fica `INSUFICIENTE` para sempre, e o parecer diz por quê, com as
saídas e o custo de cada uma. O Γ de cada estratégia, isto é, se ela é factível e segura,
vem do hospedeiro a cada chamada. A autorização vem das exclusões da pessoa, e a garantia
vem do estatuto.

## Pergunta de Verificação: *como verificamos que isto funciona DE VERDADE?*

1. **Dado coerente.** Uma jornada com protocolo consentido entre s1 e s2. A norma
   "retenção" é confirmada. Há 12 episódios por braço e s2 é melhor pela retenção. O juízo
   sai `JUSTIFICADO` com s2, e o parecer traz s2 com proveniência da norma.
2. **Escopo declarado ANTES.**
   - (a) Com a norma só proposta, o juízo é `SEM_NORMA`. Todos os campos do parecer que já
     existiam saem **byte a byte idênticos** aos de um stream sem nenhum evento da camada 7.
     Só o campo aditivo `judgment` difere.
   - (b) Apagar todos os eventos de pausa autorizada não muda o `JudgmentReading`.
   - (c) As mesmas observações sem `assignmentId` dão `INSUFICIENTE`.
   - (d) Duas normas opostas sem prioridade dão `EM_CONFLITO`, com os campos que já
     existiam idênticos aos de sem camada 7. Declarar a prioridade faz eleger.
   - (e) Uma estratégia fora de Γ nunca é eleita, mesmo com o melhor resultado.
   - (f) A leitura da camada 6 e a sugestão exploratória, quando nada é eleito, são idênticas
     com e sem os eventos da camada 7.
   - (g) Ator máquina em `review`, `priority` ou `consented` falha antes do append.
3. **Função real.** O fold real roda sobre o journal real, sem mock.
4. **Falha sem o conserto.** Fazer `judge` contar a pausa como episódio de WORSE tem de
   deixar (b) vermelho.
5. **Reporte na entrega.**

## Fronteira

**Entra:** os eventos acima, os campos `measure` e `assignmentId`, `judge`, a integração com
o parecer, o modo de CLI e os testes acima.

**Não entra:**
- o conteúdo de qualquer norma;
- as suposições declaradas à moda de Daza, que ficam só no texto;
- a moldura vinda de outras pessoas (camada 8);
- o modo como o hospedeiro mostra a frase.

## Pontos abertos: para Hudson, não para eu decidir

**A.** De onde vêm `minPerArm` e `margin`? Recomendo que venham com a norma, propostos pelo
hospedeiro e confirmados pela pessoa junto com ela. A alternativa é fixá-los por versão do
plugin.

**B.** Quando a pessoa redeclara uma norma (versão nova), os episódios já colhidos
continuam valendo? Recomendo que sim: episódios são fatos, e o que muda é a regra. O juízo
é recalculado sob a versão nova, e a frase cita a versão.

## Respostas às portas da implementação (v0.3, 9 out)

Estas respostas saem das decisões já tomadas: B1, D3, a regra de `UNCLEAR` da
CONTRATO-ESTATUTO e "a pessoa decide". As que são novas estão marcadas **[novo]** e
dependem do ok de Hudson.

**1. Resultado e diferença.** `UNCLEAR` não conta para nenhum lado, como no estatuto: não
entra no braço e não conta para o mínimo. O braço guarda `{ episodes, better }`, contando
só episódios com BETTER ou WORSE. A diferença é `diff = better_A/episodes_A −
better_B/episodes_B`, com `margin ∈ [0, 1]`. A `measure` só rotula qual sinal a norma lê.

**2. Escopo.** O escopo da norma é `Record<string,string>`. A norma só vale se o escopo
estiver contido nas `currentConditions`, verificado com `inScope`. Uma observação entra no
braço se o escopo da norma também estiver contido nas `conditions` dela, de novo com
`inScope`. `judge` e a CLI passam a receber `currentConditions`.

**3. Γ_epi.** É o estatuto T da estratégia sob as `currentConditions`, calculado pelo
`statusesFor` real.

**4. O par.** Vai dentro do `gammaInput` opcional: `{ pair: [sA, sB], feasible, safe }`. Sem
`gammaInput`, a camada 7 fica inativa.

**5. Combinação de normas.** Entram só as normas confirmadas, em escopo e não retiradas.
- As que se calam ficam fora.
- Se qualquer norma restante dá `INSUFICIENTE`, o juízo é `INSUFICIENTE`.
- Entre as que restam, `NÃO_JUSTIFICADO` não se opõe a `JUSTIFICADO`. Isso é dominância
  fraca: ganha a que justifica.
- Há `EM_CONFLITO` quando duas normas elegem estratégias opostas e não existe prioridade
  confirmada entre elas, nem direta nem por transitividade. Se todos os pares opostos
  estão ordenados, elege a norma mais alta que elege.
- Com prioridade, a ordem é lexicográfica: se a norma de cima dá `NÃO_JUSTIFICADO`, que é
  empate, a decisão passa para a de baixo.
- Isso vale para três normas ou mais.

**6. Ciclo de vida da norma.**
- Enquanto uma versão nova não é confirmada, a anterior confirmada continua valendo. O
  silêncio não confirma.
- `retired` retira o `normId` inteiro, com todas as versões.
- Uma prioridade nova entre o mesmo par substitui a anterior.
- Um ciclo de prioridades (A>B, B>C, C>A) anula a ordem entre as normas do ciclo. O resultado
  é `EM_CONFLITO`, e a frase nomeia o ciclo.
- Prioridade que cita norma retirada ou não confirmada é ignorada.

**7. Observação e sorteio.**
- `recordObservation` com `assignmentId` recusa antes do append em dois casos:
  - o sorteio não existe no stream (`ASSIGNMENT_NOT_FOUND`);
  - a estratégia observada difere da sorteada (`ASSIGNMENT_STRATEGY_MISMATCH`). Nesse caso a
    observação pode ser gravada sem `assignmentId`, e aí conta como observacional.
- `recordAssignment` recusa em três casos:
  - estratégia fora do protocolo;
  - `p` diferente da probabilidade declarada;
  - protocolo retirado.
- **[novo]** `mdaa.protocol.withdrawn`: só a pessoa emite. A partir dele, novos sorteios
  são recusados, e os episódios anteriores continuam valendo. Consentir inclui poder
  retirar.

**8. Como o parecer mostra a eleição.** Se o juízo justifica s2 e o estatuto tinha eleito
s1, s2 substitui a estratégia. Se nada tinha sido eleito, s2 entra e a sugestão exploratória
sai, porque as duas nunca coexistem. **[novo]** O campo `judgment` traz
`{ state, norms: [{ normId, version }], sentence }` e é aditivo, como descrito acima.

**9. Mecânica.** Ficam autorizados:
- o gancho em `projection.ts` para os eventos novos, com extração pura antes;
- os ganchos de 1 a 2 linhas em `projection.ts` e `observe.ts` para que `measure`,
  `assignmentId` e o `episodeId` futuro cheguem à projeção;
- a normalização do índice para LF no próximo toque.

## Depois da implementação (v0.4, 9 out): o que o código preencheu e duas emendas

**Registrado como está** (commits `c179f0e`–`b9df504`):
- a norma vale por jornada, porque todos os eventos levam `journeyId` e `requireActive`
  exige jornada ativa;
- existe o comando `withdrawProtocol`;
- um juízo `JUSTIFICADO` fora de Γ continua `JUSTIFICADO`, mas sem `elected`, e a frase
  nomeia o componente que falhou (Paper 4: valor não compra garantia);
- uma norma se cala quando não há BETTER nem WORSE da sua medida para o par; se só houver
  registro observacional, o juízo é `INSUFICIENTE`; se todas as normas se calam, também é
  `INSUFICIENTE`;
- diferença zero nunca justifica;
- as recusas de comando acrescentadas são: versão repetida, `normId` retirado, revisão
  repetida, probabilidades que não somam 1 e `assignmentId` repetido.

**Emenda E1 [precisa do ok de Hudson]: a medida entra na identidade da proposição.** Hoje,
`status.ts` agrupa por estratégia e condições, misturando as medidas. Uma estratégia com
WORSE na prática e BETTER na retenção sai em B. Isso é o caso de colisão II do Paper 4: o
escopo colapsado fabrica contradição. A consequência é que o mundo P da bancada não pode
eleger s₂ por construção. Com a emenda, a identidade vira `(estratégia, condições,
medida)` quando a medida existe. Sem medida, nada muda (regressão zero). O `epi` do juízo
passa a ser o estatuto T da proposição da medida que a norma lê.

**Emenda E2: o juízo lê a mesma fatia que o estatuto.** Hoje, em `recommend.ts`, o juízo lê
o registro inteiro, e o estatuto lê só os registros que a vigência deixa autorizar.
Justificar é autorizar a eleição, então o juízo passa a ler exatamente essa partição.
Registro envelhecido aparece, mas não justifica. A regra é a do invariante "escrita e
leitura são o mesmo juiz": dois pontos que leem a mesma coisa usam a mesma função.

**Consequência da E2: dois escopos, duas inclusões (v0.5, 9 out).** O escopo da norma diz
onde o **critério** vale. A vigência diz que **evidência** vale aqui. Por isso, um registro
só entra no braço se as duas inclusões valerem ao mesmo tempo:
1. o escopo da norma está contido nas condições do registro (resposta 2);
2. as condições do registro cabem nas condições correntes, ou seja, o registro está em
   escopo pela vigência (E2).

Uma norma de escopo largo não alarga o escopo da evidência. Registros feitos sob condições
irmãs (por exemplo, `teoria-primeiro` quando a condição corrente é `exemplo-primeiro`) nunca
justificam, por mais que a norma valha para as duas. É o mesmo princípio do Paper 1:
evidência tem escopo, e um critério declarado não o muda.

## Emenda E3: o componente epistêmico da eleição é ω, não λ (v0.6, 9 out, decidida por Hudson)

**O defeito.** O componente epistêmico de Γ exigia λ = T na proposição da medida que a norma
lê. Com sinais ruidosos, essa proposição fica em B quase sempre. No mundo P da bancada, a
chance de s2 não ter nenhum WORSE em cerca de 32 episódios é 0,7³² ≈ 10⁻⁵. Com essa
exigência, a camada 7 justificaria e quase nunca elegeria.

**A leitura decidida.** Segue o Paper 4: λ = T não implica ω = T. O estatuto da proposição
(λ) diz se há evidência a favor e se há evidência contra. A garantia da ação (ω) vem de uma
especificação declarada (χ_u). Na eleição da camada 7, a especificação declarada é o próprio
juízo: norma confirmada, protocolo consentido e regra com mínimo e margem. Portanto, nessa
eleição, o componente epistêmico de Γ passa a ser **ω(eleger s) = T, se e somente se o juízo
é `JUSTIFICADO` com s**. Os outros três componentes (factível, autorizado e seguro) não mudam.

**O que "nunca rompe B" passa a querer dizer (D3).**
- A camada 7 nunca altera λ. A proposição da retenção de s2 continua em B no retrato, e esse B
  informa. Os campos do retrato saem byte a byte idênticos com a camada 7 e sem ela.
- A camada 7 nunca elege quando o próprio juízo está em conflito (`EM_CONFLITO`).
- A eleição por estatuto da camada 5 não muda: B não elege por sustentação.

**O que não muda.** O registro observacional continua dando `INSUFICIENTE` (B3), e a
evidência continua tendo escopo (E2 e os dois escopos). Contar passa a ser admissível só
aqui, sob uma regra declarada, com protocolo consentido e para uma proposição comparativa.
É a primeira vez na série que a contagem entra, e ela entra declarada.

**Pergunta de Verificação, item novo 2(h).** s2 com retenção mista (BETTER e WORSE),
protocolo, 20 episódios por braço e diferença acima da margem. O juízo é `JUSTIFICADO`, a
eleita é s2, e λ(s2, C, retenção) continua B no retrato. **Falha sem o conserto:** com
`epi = λ = T`, injetado pela fixture, o teste fica vermelho.
