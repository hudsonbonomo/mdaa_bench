# PREREGISTRO v1 — Bancada de vigência do registro (`standing/`)

**Programa:** MDAA — Paper 5, Memory. **Repositório:** `github.com/hudsonbonomo/mdaa_bench`,
concept DOI 10.5281/zenodo.22728835. **Data de congelamento:** 2026-09-15.
**Hashes SHA-256 deste arquivo e de `alpha_frozen.json`:** em `standing/freeze.sha256`,
arquivo separado (o hash não mora no arquivo que protege), preenchido no commit de
congelamento e verificado por `tests/test_freeze_guardian.py` antes de qualquer
execução. **`.gitattributes` (`* text eol=lf`) no mesmo commit ou antes.** Nenhuma execução — nem as
sementes-piloto — antes do commit de congelamento.

## 1. Pergunta

Se um leitor de registros situados consegue distinguir os quatro estados de vigência
(applicable, out of scope, aged, unevaluable) quando quatro mecanismos distintos
produzem a mesma trajetória observável de sinais. A bancada não testa se o
envelhecimento existe nem se a vigência melhora pareceres; testa distinguibilidade sob
condições declaradas, que é precondição da afirmação empírica e não a afirmação.

## 2. Herança declarada (não reaberta)

Do Paper 2 e das grades v3/v4: o eixo M não é identificável em trajetória única;
decide-se sobre réplicas intra-pessoa; o comparador inclui modelo de chaveamento. Do
Paper 4 e da grade de decisão: pausa autorizada bloqueia ω independentemente da
evidência; aqui é bloqueio independente e não interage por construção. Do Paper 5
(rascunho v0.1, 2026-09-15): o leitor do MDAA **não infere** envelhecimento — aplica
α declarado. Logo a bancada mede (i) se R_declared atribui corretamente os estados
que não dependem de α e reporta contrário em vez de idade, e (ii) se os comparadores
leem escopo, esquecimento e vocabulário como idade.

## 3. Geradores (condições estruturais assertadas em código)

Objeto comum: fluxo de observações `(strategy, conditions, signal ∈ {BETTER, WORSE,
UNCLEAR}, t)` sob vocabulário de condições, estratégia-alvo s*, ruído UNCLEAR = 0,15.

- **A — envelhecimento verdadeiro.** Condição fixa e registrada; p(BETTER | s*) decai
  monotonicamente de p₀ = 0,80 a p₁ = 0,35 em T. *Assert:* monotonia não crescente de p.
  Plantado: `aged` além da janela de α; `applicable` dentro.
- **B — troca de condição.** c₁ (p = 0,80) e c₂ (p = 0,35) alternam em blocos de
  T/4. Fator `logged`: condição real no registro. Fator `unlogged`: tudo gravado como c₁.
  *Assert:* alternância em blocos exatos. Plantado (`logged`): `out of scope` para a
  condição não vigente. Plantado (`unlogged`): **indeterminado por construção**.
- **C — a pessoa perdeu o que sabia.** Condição fixa e registrada; em τ = T/2,
  p(BETTER | s*) cai em degrau de 0,80 para 0,25 e permanece. *Assert:* degrau único em
  τ, sem rampa. Plantado: `applicable`; leitura correta é estatuto **B com ordem**
  (BETTER antes de τ, WORSE depois). Nenhum registro é `aged` por mérito do mundo.
- **D — mudança de vocabulário.** Condição fixa; em τ₁ = T/3 a chave c₁ é renomeada
  c₁′ (mesmos valores); em τ₂ = 2T/3, com probabilidade ½, evento de reconciliação,
  total ou parcial (½ cada). *Assert:* rename único em τ₁; no máximo um evento em τ₂.
  Plantado: pré-τ₁ `unevaluable` entre τ₁ e τ₂; após total, `applicable`; após
  parcial, `out of scope` para valores sem correspondente; sem evento, `unevaluable`.

## 4. Leitores

- **R_declared** — o fold real do plugin MDAA com a camada de vigência: lê condições
  como escopo, lê eventos de vocabulário, aplica α de `alpha_frozen.json` (duas
  janelas, autoriza ⊂ aparece; piso de aparecer 0,30), compõe parecer com estatuto
  por proposição (T·F·B·N) e ordem preservada. Nenhum mock de política.
- **R_decay** — comparador por recência: kernel exponencial após 72 rodadas, piso
  0,30, sem leitura de condições como escopo; tally ponderado.
- **R_current** — o plugin como está em 2026-09-15: casamento exato de string de
  condições, sem vigência, sem eventos de vocabulário.
- **R_infer** (célula opcional, não conta para as previsões): fator de esquecimento
  ajustado ao erro de predição. É a camada 6; mede o custo da recusa.

## 5. Fatores e tamanho

| Fator | Níveis |
| --- | --- |
| Mundo | A, B, C, D |
| Registro de condições | logged, unlogged |
| T (rodadas) | 40, 160 |
| Réplicas intra-pessoa | 1, 10 |
| α | strict (80/40), lenient (160/120) |

64 células × 20 sementes = **1.280 execuções**. Sementes 1–20 na grade; sementes
901–905 são **piloto**, usadas só para a potência de P1 (§7) e descartadas.

## 6. Métricas

Por registro: matriz de confusão ν_atribuído × ν_plantado para R_declared, por célula
— **exceto B `unlogged`**, sem ν_plantado, fora da matriz por construção.
Por parecer: em C, se R_declared reporta B com ordem, e se R_decay reporta decaimento
(peso ponderado de BETTER < 0,5 ao final); em D, precisão/revocação de `unevaluable`
sobre pré-τ₁ e retorno correto após cada tipo de reconciliação; em B, distância de
variação total entre pareceres `unlogged` × `logged` na mesma semente (custo do não
registro); em B `unlogged` × A, as duas medidas de P1.

## 7. Previsões comprometidas

- **P1 (equivalência).** B `unlogged` ≡ A para R_declared: distância de variação
  total entre distribuições de ν **e** taxa de desacordo entre pareceres ambas < Δ =
  0,10, por TOST com α = 0,05, célula a célula. Potência para Δ = 0,10 com 20
  sementes calculada por simulação sobre as sementes-piloto antes da grade; se
  < 0,80, Δ sobe e o valor entra aqui **antes** do congelamento (v1.1). Previsto:
  equivalência — falha em distinguir, por construção.
- **P2.** B `logged`: R_declared atribui `out of scope` à condição não vigente em
  ≥ 0,95, todas as células.
- **P3.** C: R_declared reporta B com ordem em ≥ 0,95 e nunca atribui `aged` dentro
  da janela de α; R_decay reporta decaimento em ≥ 0,80 com T = 160.
- **P4.** D: `unevaluable` sobre pré-τ₁ com precisão e revocação ≥ 0,99; após
  reconciliação total todos voltam; após parcial, sem correspondente → `out of
  scope`, nenhum `unevaluable`.
- **P4b (espelho-controle).** D: R_current deixa todos os pré-τ₁ fora do tally e nunca
  os devolve, taxa 1,00 por construção.
- **P5.** A: R_decay e R_declared concordam no parecer em ≥ 0,90 com α lenient e
  T = 160 — o comparador acerta onde idade é idade.

## 8. Regras de decisão

Falha da tese do Paper 5: P3 ou P4 abaixo do limiar. P1 é previsto e não corrigível.
P2 ou P5 abaixo do limiar: defeito de instrumento — diagnóstico, correção declarada,
segunda grade (v2), como a grade v3 → v4 do Paper 2. P4b abaixo de 1,00: o caso de
colisão III está mal descrito, não a bancada.

## 9. Fora desta grade

Ruído variável; múltiplos observadores (camada 8); α aprendido (camada 6, R_infer
opcional); pausa autorizada (medida na bancada de decisão).

## 10. Congelamento e execução

Este arquivo, `alpha_frozen.json`, `freeze.sha256` e `.gitattributes` no mesmo
commit. O teste guardião recomputa os dois hashes e compara com `freeze.sha256`;
falha se qualquer um divergir. Nenhuma execução
antes do commit de congelamento; nenhuma execução da grade sem autorização explícita
de Hudson A. R. Bonomo, registrada no commit de execução.

## Emenda v1.1 (16 set 2026)

Acrescentados `decay_constant_rounds` e `full_weight_until_rounds` ao bloco
`comparators.R_decay` de `alpha_frozen.json`, explicitando a constante de tempo
do kernel exponencial e o limiar de peso unitário. Os dois valores são 72,
compatíveis com o `decay_after_rounds` original; a semântica do comparador não
muda. `freeze.sha256` recomputado neste commit.
