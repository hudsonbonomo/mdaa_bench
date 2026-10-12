# PREREGISTRO — Bancada do coletivo (`collective/`) — v1

**Programa:** MDAA — Paper 8, Collective and Multi-Agent Settings. **Repositório:**
`github.com/hudsonbonomo/mdaa_bench`, concept DOI 10.5281/zenodo.22728835.
**Estado:** v1, congelado em 11 out 2026 com a aprovação de Hudson A. R. Bonomo. Vira v1 no commit de congelamento, que introduz este
arquivo junto com `collective/policy_frozen.json`, `collective/plugin.sha256`,
`collective/freeze.sha256` (arquivo separado) e o teste guardião. Hashes com quebras de
linha normalizadas para LF. Nenhuma execução do piloto nem da grade antes desse commit.
O dimensionamento (sementes 300001–300300) já rodou, com autorização, e é a origem de todos
os limiares (§8). A tabela 8.1 (θ₄ por célula de G) é preenchida no commit de congelamento, a partir de `collective/resultados/sizing_collective_final.json` (`7fcb46e`), entradas 19 a 26.

## 1. Pergunta

Se as regras do Paper 8 mudam alguma coisa fora da representação: (i) o mesmo episódio é
uma fonte só, em toda contagem do plugin; (ii) os registros de outras pessoas entram como
repertório, nunca como evidência; (iii) o portão do Paper 3 não basta para licenciar o
empréstimo, porque testa onde as pessoas estão e não como se movem; (iv) a decisão para mais
de uma pessoa é a interseção dos conjuntos admissíveis, o silêncio não autoriza, o vazio é
declarado com o status quo testado, e a razão de um bloqueio só aparece com autorização. A
bancada não testa aprendizagem colaborativa nem qual regra de grupo é mais justa.

## 2. Herança declarada (não reaberta)

Do Paper 1: o estatuto é o par de indicadores de suporte e não conta. Do Paper 3: o portão
H1 recusa o pooling quando a razão entre a variância de localização entre pessoas e a
variância dentro delas passa de 1 (`H1_BETWEEN_WITHIN` e estimador de `sim/density.py`).
Do Paper 6: a regra da camada 6 (k retornos COUNTED consecutivos → W ← min(W + δ, W_max),
contagem zera; CONFLICT e CONTRADICTED encerram a sequência), que devolve peso e nunca o
retira. Do Paper 7: os braços do juízo contam episódios. Das decisões de Hudson de 8 e 9 out
2026: D1–D3, B1–B4, o sinal do episódio como conjunto dos relatos, `majority()` por episódio
e o marcador OTHERS só quando a estratégia vem apenas da oferta de outros.

## 3. Os leitores sob teste

O plugin `tmulab-mdaa` no commit `32e0105`, sob a célula `CONTRATO-COLETIVO` v0.4.
**R_own:** `collective-cli.js` modo `episodes` em O e Pn (Pn com `offeredStrategies` de
origem OTHERS); `adjustment-cli.js` modo `folds`, **pessoa por pessoa**, nas populações.
**R_group:** `collective-cli.js` modo `group` em G.

## 4. Geradores (condições estruturais assertadas em código)

- **O.** k ∈ {2, 5} observadores relatam BETTER sobre cada episódio de s₁, com o mesmo
  `episodeId`; um observador relata WORSE sobre outro episódio; 30 episódios. Caso de
  inversão: 8 episódios de s₁ com um relato cada e 3 de s₂ com 4 relatos cada; por episódio
  vence s₁, por relato venceria s₂. Plantado: estatuto B.
- **Pn.** A pessoa não tem registros; a população (n ∈ {5, 20}, 40 registros por pessoa)
  tem s₁ com p = 0,5 e s₂ com p = 0,75. Plantado: o parecer não tem evidência.
- **Populações**, a partir dos blocos c₁ e c₂ do mundo S de `adaptive/`, n ∈ {5, 20},
  T ∈ {320, 640}, com W₀ = 40, δ = 10, W_min = 20, W_max = 160 e k = 3.
  **Pc:** todos com p = 0,85. **Pl:** p por pessoa, uniforme numa faixa, em cinco faixas:
  [0,6; 0,9], [0,5; 0,95], [0,4; 0,95], [0,3; 0,95] e [0,05; 0,95]. **Pw:** metade com
  p = 0,85; metade com p decaindo linearmente de 0,85 a 0,35 ao longo de T. Plantado em Pw:
  alongar é correto para os estáveis e errado para os que decaem, e a razão de localização
  fica ≤ 1 em média.
- **G.** n ∈ {5, 10, 30}, m = 5 ações, a₀ é o status quo. Para cada membro e ação, `auth`
  ~ Bern(p), p ∈ {0,8; 0,9}; `feas`, `safe` e `epi` ~ Bern(0,95). Com probabilidade
  ρ ∈ {0; 0,5}, a decisão de uma ação é comum a todos. `showReasons` ~ Bern(0,7).

## 5. Leitores de controle (Python)

- **R_count:** conta relatos e decide por maioria; transforma B em T.
- **R_pool:** em Pn, elege pela razão BETTER da população. Nas populações, lê a população
  como uma pessoa só: junta os retornos de todos (o `lastReturn` de cada fold de fim de
  bloco) num fluxo ordenado por `seq` e aplica a esse fluxo a regra da camada 6, como em
  `adjustment.ts` (`foldPolicy`, L132–145). Todas as pessoas recebem essa janela. Um teste
  confere que a regra em Python, aplicada ao fluxo de uma pessoa, dá a janela do plugin.
- **R_H1:** R_pool quando a razão entre/dentro da localização (taxa BETTER por bloco c₁;
  centro = mediana por pessoa, como em `sim/density.py`) é ≤ 1,0; R_own quando não é. Só
  esse componente do H1 é usado: a instabilidade por bootstrap e a bimodalidade não entram.
- **R_mean:** escolhe a ação com a maior fração de membros que a autorizam.
- **R_leastmisery:** escolhe a ação de maior mínimo; no empate, a primeira em ordem
  lexicográfica.

## 6. Medidas

**Q1:** estatuto, eleição por estatuto, contagem de réplicas da camada 6, sugestão
exploratória e braços da camada 7 no fluxo com relatos duplicados e no deduplicado.
**Q2:** se R_own elege; a origem da sugestão. **Q3:** janela final por pessoa e por
subgrupo para R_own, R_pool e R_H1; se o portão passa; a mesma razão sobre a quantidade
transferida (só relatada); o **erro do empréstimo** em Pw: verdadeiro na semente se, para a
maioria das pessoas que decaem, a janela final de R_H1 é maior que a janela final de R_own
da própria pessoa; o **preço da recusa** em Pc: o primeiro bloco em que a janela chega a
W₀ + δ, por leitor. **Q4:** conjunto admissível, `indeterminate`, status quo, campos de
razão nulos quando `showReasons` é falso, escolha de R_mean e R_leastmisery e se ela está
dentro de todos os Γᵢ; taxa observada de vazio ao lado de (1 − p_efⁿ)ᵐ, p_ef = p × 0,95³,
só com ρ = 0.

## 7. Fatores e tamanho

O: 2 células; Pn: 2; Pc e Pw: 4 cada (n × T); Pl: 5 faixas × 4 = 20; G: 12. Total de
44 células × 20 sementes = **880 execuções**. Sementes: grade 1–20; piloto 901–905, só do
lado dos controles, gravado e descartado; dimensionamento 300001–300300, já rodado; testes
9001–9004.

## 8. Previsões comprometidas

Cada previsão vale célula a célula, sobre as 20 sementes, e se cumpre quando se cumpre em
todas as células a que se aplica. Os limiares estão em `collective/decide.py`, e um teste
confere que cada um aparece no parágrafo da sua previsão.

- **Q1 (contagem não vota).** O: duplicar relatos do mesmo episódio deixa idênticos, em
  R_own, o estatuto, a eleição, a contagem de réplicas, a sugestão e os braços do juízo, em
  1,00, incluindo o caso de inversão. R_count transforma B em T em ≥ θ₁ = 1,00.
- **Q2 (repertório não é evidência).** Pn: R_own nunca elege (1,00), e a sugestão traz o
  marcador OTHERS quando a estratégia vem só dos outros (1,00). R_pool elege em
  ≥ θ₂ = 1,00.
- **Q3 (o portão não basta).** Pw: R_H1 passa no portão em ≥ θ₃ = 0,95 (n = 5, T = 320) e
  1,00 nas outras células; o erro do empréstimo ocorre em ≥ θ₃′ = 0,95 (n = 5, T = 320)
  e 1,00 nas outras células. Pl, só na faixa [0,05; 0,95]: o portão recusa em ≥ θ₃″ = 0,70
  (n = 5) e 1,00 (n = 20). R_own nunca ajusta a partir de outros (1,00).
- **Q4 (o grupo é interseção).** G: R_group nunca devolve ação fora de algum Γᵢ (1,00);
  com interseção vazia, devolve `indeterminate` e avalia o status quo (1,00); nunca mostra
  razão de bloqueio sem autorização (1,00). R_mean escolhe fora de algum Γᵢ em ≥ θ₄, por célula (tabela 8.1),
  nas células em que a taxa de vazio do dimensionamento é ≥ 0,5 (n = 10 e n = 30).

**De onde vêm os limiares.** Do dimensionamento nas sementes 300001–300300: O, Pn e G no
passo C (`66dfbe0`); Pw e Pc no passo E (`5f710b8`), com o R_pool corrigido; Pl e o portão
em Pw no passo F (`18c88f0`, `dd4d773`), com o estimador da mediana; tabela consolidada no
passo H (`7fcb46e`). θ é o maior valor tal
que P(Binom(20, taxa) ≥ ⌈20θ⌉) ≥ 0,80.

| Quantidade | Célula | Taxa | θ |
| --- | --- | --- | --- |
| R_count B → T | O, k = 2 e 5 | 1,00 | 1,00 |
| R_pool elege | Pn, n = 5 e 20 | 1,00 | 1,00 |
| Portão passa | Pw, n = 5, T = 320 | 0,987 | 0,95 |
| Portão passa | Pw, demais | 1,00 | 1,00 |
| Erro do empréstimo | Pw, n = 5, T = 320 | 0,977 | 0,95 |
| Erro do empréstimo | Pw, n = 5, T = 640 | 0,993 | 1,00 |
| Erro do empréstimo | Pw, n = 20 | 1,00 | 1,00 |
| Portão recusa | Pl [0,05; 0,95], n = 5, T = 320 e 640 | 0,773 e 0,783 | 0,70 |
| Portão recusa | Pl [0,05; 0,95], n = 20 | 1,00 | 1,00 |
| R_mean fora de algum Γᵢ | G, n = 10 e 30 | tabela 8.1 | tabela 8.1 |

**Tabela 8.1.** θ₄ por célula de G (n, p, ρ), com a taxa de vazio observada no
dimensionamento. Preenchida no congelamento, a partir das entradas 19 a 26 do
`sizing_collective_final.json`; o valor agregado (entrada 27) não é usado.

| n | p | ρ | Taxa de vazio | Taxa de R_mean fora de algum Γᵢ | θ₄ |
| --- | --- | --- | --- | --- | --- |
| 10 | 0,8 | 0 | 0,887 | 0,887 | 0,85 |
| 10 | 0,8 | 0,5 | 0,850 | 0,850 | 0,80 |
| 10 | 0,9 | 0 | 0,650 | 0,650 | 0,55 |
| 10 | 0,9 | 0,5 | 0,663 | 0,663 | 0,60 |
| 30 | 0,8 | 0 | 1,000 | 1,000 | 1,00 |
| 30 | 0,8 | 0,5 | 1,000 | 1,000 | 1,00 |
| 30 | 0,9 | 0 | 0,997 | 0,997 | 1,00 |
| 30 | 0,9 | 0,5 | 1,000 | 1,000 | 1,00 |

**Relatado sem limiar.** O preço da recusa em Pc; a curva de recusa do portão nas cinco
faixas de Pl; a janela de R_own das pessoas que decaem e das estáveis, contra W₀; a razão
sobre a quantidade transferida; a taxa observada de vazio em G ao lado da fórmula.

## 9. Regras de decisão

**Contra a tese do Paper 8:** Q3 do lado do erro do empréstimo abaixo de θ₃′. O portão
passa, o empréstimo não erra, e o H1 bastaria; a recusa total da D1 teria um custo sem
motivo, e o artigo diz isso.

**Defeito de instrumento** (diagnóstico e emenda declarada antes da grade): R_count abaixo de
θ₁; R_pool abaixo de θ₂; o portão abaixo de θ₃ em Pw (o mundo não plantou o que diz); o
portão abaixo de θ₃″ na faixa extrema de Pl (o portão estaria cego); R_mean abaixo de θ₄; ou
célula sem nenhuma semente válida.

**Defeito do plugin**, não da bancada: Q1, Q2, Q4 ou o "R_own nunca ajusta a partir de
outros" abaixo de 1,00.

## 10. Fora desta grade

A interpretação de terceiro (célula própria, pendente); várias instâncias do plugin e a
reconciliação de vocabulário; a moldura de limites vinda da população; a forma de obter a
liberação de cada Γᵢ; os outros componentes do H1; grupos reais e o que as pessoas fazem com
a frase do parecer.

## 11. O que o congelamento fixa

1. A célula `CONTRATO-COLETIVO` v0.4, copiada em `collective/CONTRATO-COLETIVO.md`.
2. O plugin no commit `32e0105`, com o SHA-256 de `dist/collective-cli.js`,
   `dist/collective.js`, `dist/episode-key.js`, `dist/episode-signal.js`, `dist/status.js`,
   `dist/adjustment-cli.js` e `dist/adjustment.js` em `collective/plugin.sha256`. O piloto e
   a grade recusam rodar contra outro `dist/`.
3. O diretório `collective/` e os testes `tests/test_collective_*.py`.

Ordem: congelamento (com aprovação) → piloto, só controles (com autorização) → grade (com
autorização explícita de Hudson A. R. Bonomo, registrada no commit de execução).

## 12. Emendas do desenho v0.2 para este preregistro (antes de qualquer execução da grade)

1. **R_pool.** A primeira versão lia um campo que o plugin não tem (`countedReturns`) e
   contava zero; a segunda aplicava um único passo à contagem agregada. Ficou a população
   lida como uma pessoa só, com a regra do plugin conferida contra o próprio plugin.
2. **θ₃′.** "Alongar a janela de quem decai" passou a ser medido contra a janela que o
   próprio registro da pessoa sustenta. R_own também alonga a janela de quem decai, porque a
   camada 6 devolve peso e nunca o retira; o erro atribuível ao empréstimo é o excesso.
3. **Estimador do portão.** Alinhado a `sim/density.py`: centro = mediana por pessoa. Com
   isso, 4 sementes de Pw (n = 5, T = 320) passaram a recusar o empréstimo e caem em R_own.
4. **Pl.** Com a faixa original, o portão quase nunca recusa: em registros de sinais
   binários, nesse tamanho de bloco, ele mal enxerga diferença de localização. Pl virou uma
   curva com cinco faixas, e o limiar ficou só na faixa extrema, como prova de que o portão
   consegue recusar.
5. **Fórmula de G.** A taxa de vazio é (1 − p_efⁿ)ᵐ, com p_ef = p × 0,95³, e só vale com
   ρ = 0. A versão anterior comparava a taxa de vazio com a probabilidade de não vazio.
6. **Interface:** campos da requisição `episodes` (`nowSeq`, `currentConditions`,
   `policy`); leitura da saída do plugin em UTF-8.
7. **Saídas substituídas.** As do passo D5 (`0628a09`) foram calculadas com o R_pool de
   passo único e o estimador da média; o θ₃′ = 0 e o θ₃″ = 0 que elas trazem não valem. Ficam
   no histórico e não são usadas.
8. **Arquivo reescrito por teste.** `make_prereg.py` (L42), chamado por `tests/test_prereg.py`
   (L21), reescreve o hash de proveniência de `PREREGISTRO_v3.md` a cada execução. Esse arquivo
   não é coberto por nenhum `freeze.sha256` e nunca entra em commit da bancada do Paper 8.
