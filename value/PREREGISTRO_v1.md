# PREREGISTRO — Bancada do juízo de valor (`value/`) — v1

**Programa:** MDAA — Paper 7, Evaluation and Value. **Repositório:**
`github.com/hudsonbonomo/mdaa_bench`, concept DOI 10.5281/zenodo.22728835.
**Estado:** v1, congelado em 11 out 2026 com a aprovação de Hudson A. R. Bonomo. Vira v1 no commit de congelamento, que introduz este
arquivo junto com `value/policy_frozen.json`, `value/plugin.sha256`, `value/freeze.sha256`
(arquivo separado: o hash não mora no arquivo que protege) e o teste guardião. Os hashes
são calculados com quebras de linha normalizadas para LF. Nenhuma execução do piloto nem
da grade antes desse commit. O dimensionamento (sementes 200001–200300) já rodou, com
autorização, e é a origem de todos os limiares (§8).

## 1. Pergunta

Se as regras do Paper 7 mudam alguma coisa fora da representação: (i) sem norma
confirmada, não há juízo; (ii) a norma nomeia a medida que lê, e a prática não é retenção;
(iii) a pausa autorizada não é perda nem ganho; (iv) conflito entre normas informa, e só a
prioridade declarada pela pessoa elege; (v) sem sorteio registrado, não há justificação;
(vi) o juízo elege só dentro de Γ, nunca move α, nunca toca a sugestão exploratória e
nunca altera o estatuto λ de uma proposição. A bancada não testa se alguma norma é boa,
nem qual estratégia ensina melhor. Testa se o leitor que cumpre cada regra se separa de um
leitor do regime em vigor que a abandona, em mundo onde a diferença foi plantada.

## 2. Herança declarada (não reaberta)

Do Paper 1: o estatuto é o par de indicadores de suporte, e B informa e não elege. Do
Paper 2: a pausa autorizada é u_ped = 0. Do Paper 4: Γ antes de J, e λ = T ⇏ ω = T. Do
Paper 5: a vigência decide que registro vale aqui e agora. Do Paper 6: limiares
dimensionados no próprio gerador antes de congelar; piloto não certifica potência. Das
decisões de Hudson de 8 e 9 out 2026: D1–D3, B1–B4, pontos A e B da célula NORMA, E1
(a medida é parte da identidade da proposição), E2 (duas inclusões de escopo) e E3 (o
componente epistêmico da eleição é ω).

## 3. O leitor sob teste e a regra

R_norm é o plugin `tmulab-mdaa` no commit `32e0105`, chamado pela ponte `value-cli.js`,
modo `judge` para o par (s₁, s₂) — e (s₂, s₃) no mundo P — e modo `parecer` com `layer7`
igual a `true` e a `false`. A regra é a da célula `CONTRATO-NORMA` v0.6: cinco estados
(SEM_NORMA, INSUFICIENTE, JUSTIFICADO, NÃO_JUSTIFICADO, EM_CONFLITO); mínimo por braço e
margem vêm com a norma; só contam episódios com sorteio registrado (`assignmentId`); UNCLEAR
não conta para lado nenhum nem para o mínimo; norma calada não forma estado; prioridade
lexicográfica; eleição só de JUSTIFICADO, dentro de Γ, com ω no lugar de λ. Cada execução
grava três colunas separadas: `R_norm_state`, `R_norm_judged_strategy`, `R_norm_elected`.

## 4. Geradores (condições estruturais assertadas em código)

Uma execução é uma jornada, condição fixa `{modo: c1}`, vigência identidade, T episódios.
Cada episódio tem estratégia (sorteada pelo protocolo, com `mdaa.protocol.assigned`
gravado antes, ou escolhida pela pessoa no mundo X) e duas observações do mesmo episódio:
`practice` ~ Bern(p_prac[s]) e `retention` ~ Bern(p_ret[s]); em C há ainda `autonomy`.
Uma fração u = 0,10 de cada sinal vira UNCLEAR. Protocolo: s₁, s₂, s₃ com probabilidades
0,4, 0,4 e 0,2; s₃ é infactível (fora de Γ) e tem o melhor resultado plantado. Norma:
mínimo 15 por braço, margem 0,15. Parâmetros em `value/policy_frozen.json`.

| Mundo | Norma | O que mais tem | Plantado |
| --- | --- | --- | --- |
| N0 | `retention`, só **proposta** (origem HOST) | sinais de P | nada pode ser julgado |
| P | `retention` confirmada | s₁ melhor na prática, s₂ na retenção | s₂ pela norma |
| R | `retention` confirmada | pausas autorizadas mais frequentes depois de s₁ | nenhuma diferença |
| R+ | idem | R + salto na prática depois de cada pausa | nenhuma diferença |
| C0 | `retention` e `autonomy` confirmadas | sem prioridade | conflito |
| C1 | idem | prioridade `retention ≻ autonomy` | s₂ |
| C2 | idem | nenhuma observação `autonomy` do par | s₂; `autonomy` se cala |
| X | `retention` confirmada | **sem** protocolo; estado oculto escolhe e decide | não justificável |
| Xp | idem | mesma estrutura oculta, com sorteio registrado | nenhuma diferença |

Mundo X/Xp: p_stay = 0,8; a pessoa escolhe s₁ descansada e s₂ cansada com probabilidade
0,8; p_ret = 0,8 descansada e 0,3 cansada (emenda §12, item 3). Cada gerador assere o que
planta nas sementes 9001–9004 (`tests/test_value_*.py`).

## 5. Leitores de controle (Python, sem chamar o plugin)

- **R_reward:** elege pelo maior BETTER na prática. Julga sempre. É o regime em vigor.
- **R_infer_value:** valor = BETTER na prática ÷ `seq` consumido pelos episódios da
  estratégia, contando o salto da pausa. Lê a pausa como custo.
- **R_scalar:** soma, com peso igual, as razões BETTER de retenção e de autonomia.
- **R_naive:** compara as razões de retenção sem olhar o `assignmentId`; "justifica" se a
  diferença for ≥ margem.

## 6. Medidas

Por execução e leitor: estado, estratégia julgada e eleita de R_norm; escolha de cada
controle. **Invariância da pausa:** o `judge` de R_norm e a escolha de R_infer_value no
fluxo com pausas e no fluxo em que se apagam os eventos `status_changed` e se renumera o
`seq`. **Invariâncias da D3:** leitura da camada 6 e sugestão exploratória com `layer7`
igual a `true` e a `false`; estatuto λ de cada proposição nas duas leituras. **Custo:** o
primeiro checkpoint (a cada 10 episódios) em que R_norm sai de INSUFICIENTE.

## 7. Fatores e tamanho

9 mundos × T ∈ {80, 160} episódios × 20 sementes = **360 execuções**. Sementes: grade
1–20; piloto 901–905, só do lado dos controles, gravado e descartado; dimensionamento
200001–200300, já rodado; testes 9001–9004.

## 8. Previsões comprometidas

Cada previsão vale célula a célula (mundo, T), sobre as 20 sementes, e se cumpre quando se
cumpre em todas as células a que se aplica. Os limiares estão em `value/decide.py`, e um
teste confere que cada um aparece no parágrafo da sua previsão.

- **P1 (sem norma, não há juízo).** N0: R_norm devolve SEM_NORMA em 1,00. R_reward julga
  em 1,00.
- **P2 (prática não é retenção).** P: R_norm devolve JUSTIFICADO com s₂ em ≥ θ₂ = 0,80
  (T = 80) e 0,95 (T = 160), e nunca elege s₁. R_reward elege s₁ em ≥ θ₂′ = 1,00.
- **P3 (a pausa não é perda nem ganho).** R e R+: o estado, a estratégia julgada e a
  eleita de R_norm são idênticos com e sem as pausas em 1,00. R_infer_value muda de escolha
  em ≥ θ₃ = 0,20 (R) e 0,25 (R+), nos dois T.
- **P4 (conflito informa, prioridade elege).** C0: R_norm devolve EM_CONFLITO e não elege
  em 1,00; R_scalar elege em ≥ θ₄ = 1,00. C1 e C2: R_norm elege s₂ em ≥ θ₄′ = 0,85
  (T = 80) e 0,95 (T = 160).
- **P5 (sem contrafactual, não justifica).** X: R_norm devolve INSUFICIENTE em 1,00;
  R_naive "justifica" s₁ em ≥ θ₅ = 0,85 (T = 80) e 0,95 (T = 160). Xp: R_norm devolve
  NÃO_JUSTIFICADO em ≥ θ₅′ = 0,70 (T = 80) e 0,90 (T = 160).
- **P6 (as fronteiras da D3, em todos os mundos, 1,00).** R_norm nunca elege s₃; a leitura
  da camada 6 é idêntica com e sem a camada 7; quando a camada 7 não elege, a sugestão
  exploratória é idêntica com e sem ela, e quando elege a sugestão não aparece; o estatuto
  λ de toda proposição é idêntico com e sem a camada 7; nada é eleito de EM_CONFLITO.

**De onde vêm os limiares.** Do dimensionamento nas sementes 200001–200300 (commits
`3d10ce4` e `66dfbe0`; X/Xp com os parâmetros da emenda em `66dfbe0`). Para cada célula e
quantidade, θ é o maior valor tal que P(Binom(20, taxa) ≥ ⌈20θ⌉) ≥ 0,80.

| Quantidade | T = 80 | T = 160 |
| --- | --- | --- |
| P: R_norm JUSTIFICADO s₂ | 0,87 → 0,80 | 0,96 → 0,95 |
| P: R_reward elege s₁ | 1,00 → 1,00 | 1,00 → 1,00 |
| R: R_infer_value muda | 0,263 → 0,20 | 0,267 → 0,20 |
| R+: R_infer_value muda | 0,330 → 0,25 | 0,313 → 0,25 |
| C0: R_scalar elege | 1,00 → 1,00 | 1,00 → 1,00 |
| C1: R_norm elege s₂ | 0,90 → 0,85 | 0,98 → 0,95 |
| C2: R_norm elege s₂ | 0,91 → 0,85 | 0,98 → 0,95 |
| X: R_naive justifica s₁ | 0,89 → 0,85 | 0,96 → 0,95 |
| Xp: R_norm NÃO_JUSTIFICADO | 0,79 → 0,70 | 0,95 → 0,90 |

No dimensionamento, todas as quantidades estruturais (P1, P3 e P5 do lado de R_norm em X,
e P6) deram 1,00. O θ₃ é baixo por construção, não por falta de potência: em R as
estratégias são iguais, e sem pausas a escolha de R_infer_value já é um sorteio.

**Custo, sem limiar.** Em P e Xp, por T: o primeiro checkpoint em que R_norm sai de
INSUFICIENTE. É o juízo pago em tempo.

## 9. Regras de decisão

**Contra a tese do Paper 7:** P2 do lado de R_norm (elege s₁ ou não alcança θ₂); P3 do
lado de R_norm (o juízo muda quando se apagam as pausas); P4 em C1 ou C2 (o conflito vira
paralisia); P5 do lado de Xp (a recusa em X seria cega, e o artigo diz isso).

**Defeito de instrumento** (diagnóstico e emenda declarada antes da grade): um controle
que não falha onde deve — P1 e P2 do lado de R_reward, P3 do lado de R_infer_value, P4 do
lado de R_scalar, P5 do lado de R_naive —, ou célula sem nenhuma semente válida.

**Defeito do plugin**, não da bancada: P1, P4 em C0, P5 em X, ou P6 abaixo de 1,00 do
lado de R_norm.

## 10. Fora desta grade

As duas inclusões de escopo da E2 (cobertas pelos testes do plugin, não plantadas aqui);
redeclaração de norma e retirada do protocolo; ciclo de prioridades; mais de duas normas;
norma proposta e recusada; várias pessoas (camada 8); leitura da frase por pessoas reais.

## 11. O que o congelamento fixa

1. A célula `CONTRATO-NORMA` v0.6, copiada em `value/CONTRATO-NORMA.md`.
2. O plugin no commit `32e0105`, com o SHA-256 de `dist/value-cli.js`, `dist/judgment.js`,
   `dist/norm.js`, `dist/standing-cli.js` e `dist/status.js` em `value/plugin.sha256`. O
   piloto e a grade recusam rodar contra outro `dist/`.
3. O diretório `value/` e os testes `tests/test_value_*.py`.

Ordem daqui em diante: congelamento (com aprovação) → piloto, só controles (com
autorização) → grade (com autorização explícita de Hudson A. R. Bonomo, registrada no
commit de execução).

## 12. Emendas do desenho v0.2 para este preregistro (antes de qualquer execução da grade)

1. O horizonte é T ∈ {80, 160} episódios, como na política e no dimensionamento. O texto
   do desenho, que falava em 320 e 640, herdara a escala do Paper 6.
2. P3, lado do controle: "muda de escolha". A quantidade `gap_shift` foi descartada antes
   de decidir qualquer coisa: o valor de R_infer_value é BETTER por unidade de `seq`, e a
   margem de 0,15 não se aplica a essa escala.
3. Mundo X/Xp: p_ret 0,8 descansada e 0,3 cansada (era 0,7 e 0,4). Com os parâmetros
   antigos, o confundimento plantado dava diferença de cerca de 0,18, quase igual à margem.
4. P6, quarta fronteira: depois da E3, "estratégia em B não elege" passou a ser "o juízo
   nunca altera λ e nada é eleito de EM_CONFLITO".
5. Interface: eventos no envelope `{type, seq, payload}`; estratégia como lista; N0 com
   norma de origem HOST (uma norma de origem DECLARED é a declaração da própria pessoa e
   entra confirmada); leitura da saída do plugin em UTF-8.

## §13 — Emenda v1.2 (12 out 2026, DEPOIS da grade)

Ao ler a grade, encontrou-se que value/decide.py comparava o estado NÃO_JUSTIFICADO com a grafia sem til e por isso não contou nenhuma leitura de Xp nesse estado. A comparação foi corrigida para a grafia que o plugin devolve. Os dados não mudam: o decide.py emendado é reaplicado às linhas da grade gravadas antes da emenda, sem nova execução. Os dois vereditos são relatados, o do código congelado e o do código emendado. A previsão P4 não é emendada: o seu veredito fica como saiu.

## §14 — Emenda v1.3 (12 out 2026, depois da grade)

Uma auditoria por recomputação das linhas gravadas encontrou dois problemas. (a) O controle R_infer_value media o vão entre o primeiro e o último episódio de cada estratégia, e não o seq consumido por ela; a pausa alongava as duas por igual, e o controle não mudou de escolha em nenhuma das 80 execuções de R e R+. O decide.py lia uma coluna que não foi gravada e devolvia 1,00, e o dimensionamento do θ₃ mediu outra quantidade (R_infer_value contra R_reward). O lado do controle da P3 não foi testado. O controle foi corrigido para cobrar a pausa da estratégia do episódio que a precede. (b) O decide.py conferia uma só das cinco fronteiras da P6; passou a conferir as cinco, reaplicado às linhas gravadas. Nenhum limiar muda.
