# PREREGISTRO — Bancada de ajuste da política (`adaptive/`) — v1

**Programa:** MDAA — Paper 6, Adaptive Policy Learning. **Repositório:**
`github.com/hudsonbonomo/mdaa_bench`, concept DOI 10.5281/zenodo.22728835.
**Estado:** v1, congelado em 8 out 2026 com a aprovação de Hudson A. R. Bonomo. O
commit de congelamento é o que introduz este arquivo junto com `adaptive/policy_frozen.json`,
`adaptive/plugin.sha256`, `adaptive/freeze.sha256` (arquivo separado: o hash não mora no
arquivo que protege) e o teste guardião. Nenhuma execução — nem as sementes-piloto — antes
desse commit. Os hashes são calculados com as quebras de linha normalizadas para LF, para
que o guardião dê o mesmo resultado em qualquer sistema.

## 1. Pergunta

Se as quatro regras que o Paper 6 enuncia mudam alguma coisa fora da representação:
(i) só se ajusta com réplicas; (ii) o valor em vigor tem de ser reproduzível a partir da
frase que o explica; (iii) só o desacordo do tipo 2 move a régua; (iv) réplicas só somam
dentro do mesmo regime de vocabulário. A bancada não testa se ajustar melhora pareceres.
Testa se cada regra separa o leitor que a cumpre de um leitor que a abandona, em mundo
onde a diferença foi plantada — e se as duas primeiras são mesmo duas.

## 2. Herança declarada (não reaberta)

Do Paper 2: o eixo M não se decide em trajetória única. Do Paper 4: especificação
definida depois dos resultados é vulnerabilidade. Do Paper 5 e da grade `standing/` v1:
α é declarado e congelado; o estatuto B preserva ordem e não elege; reconciliação é ato
da pessoa. Das decisões de 7 out 2026 (`PAPER_6_DECISOES.md`, D1–D11): dois portões;
réplica é a reentrada na condição; registro reconciliado volta à leitura e não à
contagem; em Suspenso vigora o último valor declarado; redeclaração zera a contagem;
só o tipo 2 move a régua.

## 3. A regra sob teste

O artigo enuncia condições, não uma regra. A bancada testa a regra mais simples que as
cumpre. A janela W é declarada por condição. A unidade é o **bloco**: uma permanência
contínua na condição. Um **retorno** é um bloco precedido de saída da condição.

Em cada retorno j, com sinal majoritário m_j:
- **casca** = os blocos da mesma condição com idade em (W, W + δ] — os que o próximo
  passo devolveria à leitura;
- **tipo 1** = a maioria dos registros em vigor (idade ≤ W), tomados em conjunto,
  contradiz m_j. É estatuto B: informa, não conta, e **encerra a sequência**;
- **retorno contado** = não há tipo 1, a casca existe, está no regime de vocabulário
  corrente, e sua maioria coincide com m_j.

Com **k retornos contados consecutivos**, W ← min(W + δ, W_max), o estado passa a
Ajustado e a contagem zera. Retorno que contradiz a casca encerra a sequência.
Renomeação de chave → Suspenso, e vigora o último valor declarado. Reconciliação →
Declarado, contagem zero, regime novo. Redeclaração → Declarado, contagem zero.

Cada ajuste emite uma **derivação de forma fixa**: valor anterior, os k retornos
contados, a faixa de registros da casca. É a frase do §4 do artigo.

**O momento da leitura.** O leitor só lê um retorno quando o bloco fecha, e o bloco fecha
na primeira rodada fora da condição. Por isso todo leitor é dobrado, para cada bloco de
c₁, em `nowSeq` = última rodada do bloco + 1, com a condição escrita no vocabulário em
vigor nesse `nowSeq`. Cada leitura traz `lastReturn`: a rodada final do último retorno
lido e o que ele foi (`COUNTED`, `CONFLICT`, `CONTRADICTED`, `NEUTRAL`). É por esse campo,
e não pelo texto da razão, que a bancada sabe o que um retorno foi: a razão explica o
estado e não muda num retorno neutro.

## 4. Geradores (condições estruturais assertadas em código)

Objeto comum: uma pessoa, estratégia-alvo s*, duas condições c₁ e c₂ alternando em
blocos de L = 5 rodadas; observações no tipo `ConditionObservation` do plugin, que é o
que a ponte recebe. Só c₁ é medida; c₂ existe para haver saída e retorno. Um bloco de c₁
a cada 10 rodadas. Todo `assert` de gerador é sobre o que foi **plantado** (a agenda de
p, os atos, os eventos), nunca sobre os sinais sorteados. *Assert comum:* nenhum evento
de vocabulário e nenhuma declaração cai dentro de um bloco de c₁; o fluxo começa por c₁
e termina por c₂, para que todo retorno feche e seja lido.

- **S — régua curta demais, mundo parado.** p(BETTER | c₁) = 0,80 constante.
  *Assert:* p invariante. Plantado: alongar é o certo.
- **N — régua certa, desacordo isolado.** p(BETTER | c₁) alterna entre 0,80 e 0,20 a
  cada 40 rodadas, que é W₀. *Assert:* o p plantado do j-ésimo bloco de c₁ (j de zero) é
  0,80 se ⌊j/4⌋ é par e 0,20 se é ímpar, para todo j. Plantado:
  a casca é sempre do regime anterior; retorno contado só ocorre por acaso.
- **K — a pessoa muda uma vez.** p = 0,80 até τ = T/2, depois 0,20. *Assert:* degrau
  único em τ. Plantado: depois de τ há contradição (tipo 1) e nenhuma razão para
  encurtar; a leitura certa é B com ordem.
- **V — renomeação e reconciliação periódicas.** p = 0,80 constante. Primeira
  renomeação em t = 200; depois a cada 60 rodadas; reconciliação total pela pessoa 10
  rodadas depois de cada renomeação. *Assert:* agenda exata. Plantado: Suspenso entre
  renomeação e reconciliação; regimes curtos demais para somar k.
- **R — redeclaração.** Como S; em t = T/2 a pessoa redeclara W = W₀. *Assert:* um
  único ato, com proveniência da pessoa.

## 5. Leitores

- **R_declared** — o plugin `@tmulab/mdaa` com a camada 6, chamado por subprocess, sob a
  regra do §3. Nenhum mock de política.
- **R_fixed** — o mesmo plugin sob a mesma regra com faixa de largura zero
  (W_min = W_max = W₀): lê os retornos e nunca move a janela. É a janela do Paper 5.
  Linha de base. (Com `rule: null` o plugin não lê retorno algum, e o custo em K não
  teria com que comparar.)
- **R_simple** — regra do §3 com k = 1. Abandona o portão da réplica.
- **R_mix** — conta como R_declared: o gatilho é o mesmo, k retornos contados
  consecutivos, lidos pelo plugin. O que muda é o passo. Estado: valor V (começa em W₀),
  pesos sobre os candidatos 10, 20 e 40 (começam iguais) e a rodada do último gatilho.
  A leitura é a do plugin com uma única declaração, de janela V, posta na rodada seguinte
  à do último gatilho (no início, a declaração do mundo), sob a regra de limiar k e
  passo 10. **Há gatilho quando essa leitura traz um ajuste**; a rodada dele é o novo
  último gatilho. No gatilho, repete-se a leitura com passo s para cada candidato; o
  candidato cuja leitura também traz ajuste ganha fator exp(η · s/10). Passo = média dos
  candidatos ponderada pelos pesos, arredondada à dezena com meio para cima.
  V ← min(V + passo, W_max). O valor em vigor passa a depender de toda a história de
  gatilhos. Abandona o portão da proveniência; mantém réplica e tipo 2. R_mix roda só em
  S e N, os mundos das previsões que o envolvem (P3, P4): em R ele ignoraria a
  redeclaração, porque sua leitura tem uma declaração só.
- **R_sym** — regra do §3 mais o simétrico: k retornos de tipo 1 consecutivos encurtam
  W em δ. É a leitura que a D11 recusa.
- **R_cross** — regra do §3 sem a exigência de regime corrente. É a leitura que a D5
  recusa.

## 6. O verificador de proveniência

`replay_check`: para cada ajuste, instancia um leitor **novo** do mesmo tipo no valor
anterior, entrega **só** o que a derivação nomeia — os retornos contados, a faixa
confirmada e a faixa em vigor — e compara o valor obtido com o valor em vigor. Para os
leitores do plugin é a função `replayDerivation`. Para R_mix é uma instância nova, de
pesos iniciais, que faz sobre os registros nomeados o que R_mix faz num gatilho: confere
o gatilho (`replayDerivation` com passo 10 tem de sair de `from`), confere cada candidato
(`replayDerivation` com passo s), atualiza os pesos iniciais, tira o passo e devolve
min(`from` + passo, W_max). **Nenhum resultado do verificador é fixado em código**: o
de R_mix é calculado como o de qualquer outro leitor. Reproduz ou não reproduz.

Ajuste **truncado pelo teto** (`from` + passo > W_max) fica fora da taxa de reprodução,
para todos os leitores: qualquer passo que chegue ao teto devolve o mesmo valor, e quem
responde ali é a faixa, não a derivação. Legibilidade entra por substituto declarado: a
derivação tem forma fixa, que não cresce com o número de ajustes.

## 7. Fatores e tamanho

| Fator | Níveis |
| --- | --- |
| Mundo | S, N, K, V, R |
| T (rodadas) | 320, 640 |
| k (retornos consecutivos) | 3, 5 |

20 células × 20 sementes = **400 execuções**, os cinco leitores do plugin em cada uma e
R_mix nas de S e N. Parâmetros
fixos em `policy_frozen.json`: W₀ = 40, δ = 10, W_min = 20, W_max = 160, janela de
aparecer 160, L = 5; R_mix com passos candidatos 10, 20 e 40 e η = 0,5. Sementes 1–20 na grade; sementes 901–905
são **piloto**, usadas só para conferir que cada controle falha onde deve, e descartadas.

## 8. Previsões comprometidas

Cada previsão vale célula a célula: a taxa é calculada sobre as 20 sementes de cada
célula (mundo, T, k) a que a previsão se aplica, e a previsão se cumpre quando se cumpre
em todas essas células. Os limiares desta seção estão em `adaptive/decide.py`, e um teste
confere que cada um aparece no parágrafo da sua previsão. Onde a taxa é sobre ajustes
(P3, P3b, P4 do lado de R_simple), semente sem ajuste fica fora da taxa e é reportada; a
célula em que nenhuma semente tem ajuste não cumpre a previsão, e a falha é de
instrumento: o controle não teve com que falhar.

- **P1 (o que a camada acrescenta).** S: R_declared termina com W ≥ W₀ + 2δ em ≥ 0,90
  das sementes, em todas as células; R_fixed termina em W₀ em 1,00 das sementes.
- **P2 (portão da réplica).** N: R_declared faz zero ajustes em ≥ 0,95 das sementes;
  R_simple faz ao menos um em ≥ 0,60 com T = 320 e em ≥ 0,85 com T = 640.
- **P3 (portão da proveniência).** S com T = 640: `replay_check` reproduz 1,00 dos
  ajustes de R_declared e, em média sobre as sementes, ≤ 0,50 dos de R_mix, contados só
  os ajustes não truncados pelo teto (§6). Semente sem ajuste não truncado fica fora da
  média e é reportada.
- **P3b (controle positivo do verificador).** Retirar um retorno da derivação de
  R_declared faz o `replay_check` falhar em 1,00. Se não falhar, o verificador não lê o
  que diz ler, e nada do P3 vale.
- **P4 (os dois portões são dois).** R_simple reproduz 1,00 no `replay_check` em S com
  T = 640, verificado sob a sua própria regra (limiar 1), e reprova em N. R_mix faz zero ajustes em ≥ 0,95 das sementes de N e reprova no P3. Cada um
  falha um portão e passa no outro.
- **P5 (só o tipo 2).** K: em nenhuma leitura de R_declared a janela é menor que na
  leitura anterior (taxa 1,00), e em ≥ 0,95 das sementes ao menos um dos dois primeiros retornos
  depois de τ é lido como `CONFLICT` (o desacordo do tipo 1, estatuto B). R_sym tem ao
  menos uma leitura depois de τ com janela menor que a anterior em ≥ 0,80 das sementes
  com k = 3. A ordem que o estatuto B preserva é da camada 5 e não é medida aqui.
- **P6 (regime de vocabulário).** V: depois da primeira renomeação R_declared faz zero
  ajustes; entre renomeação e reconciliação o valor em vigor é W₀; todo parecer traz a
  razão nomeada (em Suspenso, a razão nomeia a renomeação). Taxas de 1,00. R_cross faz
  ao menos um ajuste depois da primeira renomeação em ≥ 0,90 das sementes com k = 3; com
  k = 5 o número é reportado sem limiar.
- **P7 (redeclaração, espelho-controle).** R: depois do ato, estado Declarado, valor
  W₀, contagem zero, e todos os retornos que o ajuste seguinte nomeia começam depois do
  ato. Taxa 1,00 por construção.

**De onde vêm os limiares.** P1 e P2 foram dimensionados por aritmética binomial exata
sobre os parâmetros do §4, sem sorteio e sem rodar gerador:

| Quantidade | T = 320 | T = 640 |
| --- | --- | --- |
| S: P(W ≥ W₀ + 2δ), k = 3 | 1,000 | 1,000 |
| S: P(W ≥ W₀ + 2δ), k = 5 | 0,974 | 1,000 |
| N: P(R_simple ajusta ao menos uma vez) | 0,808 | 0,973 |
| N: P(R_declared ajusta), k = 3 | 0,005 | 0,011 |
| N: P(R_declared ajusta), k = 5 | < 0,001 | < 0,001 |

A conta também mostrou o que não usar: com ruído maior (0,70/0,30), k = 3 deixa passar
ajuste falso em 7% a 16% das sementes. O limiar é declarável, mas é declarado contra
uma suposição de ruído — e isso entra no artigo.

Os limiares do lado dos controles em P3 (R_mix), P5 (R_sym) e P6 (R_cross) dependem de
dinâmica que não fecha em conta de papel. São conferidos nas sementes-piloto; se a
potência for < 0,80, o limiar é emendado **antes** da grade (v1.1), como no Paper 5.
O piloto grava e exibe só o lado dos controles e o P3b; o lado de R_declared não é
gravado nem exibido nas sementes-piloto.

**Conferência estrutural sem sorteio (7 out, antes do congelamento).** Com um fluxo
determinístico — todo bloco de c₁ igual a BETTER, sem gerador, sem semente — a regra do
§3 foi dobrada à mão para ver se cada instrumento mede o que diz. Dois achados entraram
nesta versão. (i) Em S, R_mix faz quatro ajustes (40 → 70 → 110 → 150 → 160) e o
verificador reproduz o primeiro e o último: 2 de 4, exatamente o limiar de 0,50. O
último só reproduz porque o teto o trunca. Sem os truncados, 1 de 3 — daí a regra do §6.
(ii) Em V, com k = 5, R_cross só ajusta se os cinco retornos de um regime contarem todos:
sem ruído ajusta no quinto, com ruído a conta de papel dá perto de 0,55 por regime. Daí
o limiar de P6 valer só para k = 3. A mesma conferência mostrou que R_declared soma no
máximo um retorno contado por regime em V, e que a leitura no meio do fluxo exige a
condição no vocabulário daquele momento.

**Custos, medidos sem limiar e definidos aqui, antes de qualquer execução.**
Em K: B(X) = número de retornos de c₁ iniciados em τ ou depois cuja leitura traz
`lastReturn.kind = CONFLICT`. Reportam-se B(R_declared), B(R_fixed) e a diferença: é o
preço de ter alongado e não poder encurtar. Em V: A(X) = número de ajustes de X com
rodada posterior à primeira renomeação. Reportam-se A(R_cross) e A(R_declared), que P6
prevê zero: a diferença são os alongamentos de que a regra de regime abre mão. Entram no
artigo como números, não como vereditos.

## 9. Regras de decisão

**Agregação.** Uma previsão se cumpre quando se cumpre em todas as células a que se
aplica. A P4 se cumpre quando se cumprem os seus dois lados próprios (R_simple reproduz;
R_mix não ajusta em N) e os dois lados dos controles que ela toma emprestados (R_simple
ajusta em N, na P2; R_mix não reproduz, na P3).

**Contra a tese do Paper 6:** P4 falha num dos seus lados próprios — os dois controles
reprovam pelo mesmo motivo, os portões são um, e o §4 do artigo é redundante; ou P5
falha do lado de R_declared; ou P2 falha do lado de R_declared, e o portão da réplica não
segura o desacordo isolado sob o ruído declarado; ou P1 falha, e a camada não acrescenta
nada.

**Defeito de instrumento** (diagnóstico, emenda declarada antes da grade, como v1.1–v1.3
do Paper 5): um controle que não falha onde deve — P2 do lado de R_simple, P3 do lado de
R_mix, P5 do lado de R_sym, P6 do lado de R_cross —, P3b abaixo de 1,00, ou célula sem
nenhuma semente com ajuste numa taxa sobre ajustes.

**Defeito do plugin**, não da bancada: P3, P6 ou P7 abaixo de 1,00 do lado de
R_declared (a derivação de R_declared reproduz por construção).

## 10. Fora desta grade

A pessoa que muda em silêncio sob a mesma condição e depois volta (limite declarado no
§12 do artigo). Reconciliação parcial. Mais de duas condições. Leitura por pessoas: o
substituto do §6 não a mede. Desempenho de qualquer leitor: é camada 7.

## 11. O que o congelamento fixa

O congelamento fixa as três peças de que a bancada depende:
1. a célula do contrato `mdaa.adjustment`, v0.2, copiada em `adaptive/CONTRATO-AJUSTE.md`
   — a regra do §3 como exigência;
2. a camada 6 no plugin `tmulab-mdaa`, no commit `04e71bb` (camada em `4ad4e05`, `17e00bf`,
   `45ea303`; emenda 1 em `a1f2555`, `3af3baa`, `04e71bb`: `lastReturn`, razão no teto, modo
   `folds` da ponte). O commit e o SHA-256 de `dist/adjustment-cli.js`,
   `dist/adjustment.js` e `dist/standing.js` ficam em `adaptive/plugin.sha256`, e o piloto
   e a grade recusam rodar contra outro `dist/`. O hash da ponte sozinho não bastaria: ele
   não mudou quando a regra de escopo mudou, porque a ponte só importa a regra;
3. o diretório `adaptive/` no `mdaa_bench` e os testes `tests/test_adaptive_*.py`:
   geradores, leitores, verificador, medida, decisão, guardião.

Ordem daqui em diante: piloto (com autorização) → emenda v1.1, se a potência de algum
controle ficar abaixo de 0,80 → grade (com autorização). Nenhuma execução da grade sem
autorização explícita de Hudson A. R. Bonomo, registrada no commit de execução.

## 12. Emendas da v0.2 para a v0.3 (7 out, antes de qualquer execução)

Todas nasceram de escrever o código, e nenhuma de olhar resultado.

1. **Leitura por retorno** (§3): `nowSeq` = fim do bloco + 1; `lastReturn` é o
   instrumento. A v0.2 não dizia como a bancada sabe o que um retorno foi.
2. **Formato** (§4): as observações são o `ConditionObservation` do plugin.
3. **Asserts sobre o plantado** (§4): em N, a agenda de p por bloco, exata.
4. **R_fixed** (§5): faixa de largura zero, não `rule: null`.
5. **R_mix** (§5): gatilho, declaração e arredondamento definidos.
6. **Verificador de R_mix** (§6): calculado, nunca fixado; ajustes truncados pelo teto
   ficam fora da taxa.
7. **P5** (§8): medido por `lastReturn`; "com ordem" saiu, porque é da camada 5.
8. **P6** (§8): limiar do controle só para k = 3.
9. **P7** (§8): medido pelos retornos que o ajuste seguinte nomeia.
10. **Custos** (§8): fórmulas escritas antes de executar, não depois do piloto.
11. **Hashes** (§11): commit do plugin e três arquivos do `dist/`.

## 13. Emendas da v0.3 para a v0.4 (8 out, antes de qualquer execução)

Nasceram da leitura do código da bancada, e nenhuma de resultado.

1. **Avaliação por célula** (§8): a regra que P1 já dizia vale para todas.
2. **Limiares em código** (§8): `adaptive/decide.py`, conferido contra este texto.
3. **P3** (§8): semente sem ajuste não truncado fica fora da média de R_mix.
4. **P4** (§8): o verificador de R_simple usa a regra de R_simple. Com o limiar da célula,
   nenhum ajuste de R_simple reproduziria, e a P4 cairia por erro de instrumento,
   apontando contra a tese.
5. **R_mix só em S e N** (§5, §7).
6. **Piloto** (§8): só o lado dos controles.
7. **Regras de decisão** (§9): a v0.3 não classificava a falha de P2 nem de P3 do lado
   de R_declared. P2 conta contra a tese; P3 é defeito do plugin.

## 14. Emendas da v0.4 para a v0.5 (8 out, antes de qualquer execução)

Da segunda leitura do código, e nenhuma de resultado.

1. **Sem aprovação vazia** (§8): semente sem ajuste fica fora das taxas sobre ajustes, e
   célula sem nenhuma semente com ajuste não cumpre a previsão.
2. **Agregação e P4** (§9): como as células se somam numa previsão, e como a P4 junta os
   seus lados aos lados emprestados da P2 e da P3.
3. **Números no texto** (§8): P1 do lado de R_fixed e P5 do lado de R_declared passam a
   dizer a taxa, 1,00, que o código já usava.
4. **Piloto** (§8): o lado de R_declared não é gravado nem exibido.
