# PREREGISTRO — `value/` — adendo v2 (segunda rodada, só a P3)

**Estado:** v2, congelado em 12 out 2026 com a aprovação de Hudson A. R. Bonomo

## 1. Por que há uma segunda rodada

A auditoria da grade v1 (emenda v1.3, §14 do preregistro v1) mostrou que o controle da P3,
R_infer_value, não cobrava a pausa de nenhuma estratégia, e que o limiar θ₃ tinha sido
dimensionado sobre outra quantidade. O lado do plugin da P3 foi testado na v1 e se cumpriu
(80/80). O contraste com um leitor que conta a pausa não foi testado. Esta rodada testa só
esse contraste, com o controle corrigido (`6e69e69`). Tudo o mais do preregistro v1 continua
valendo como está, inclusive os vereditos da v1.

## 2. O que não muda

Mundos R e R+, T ∈ {80, 160}, política de `value/policy_frozen.json`, plugin em `32e0105`,
regra da norma, definições do §6 do v1. A P3 continua com dois lados: (i) o juízo de R_norm é
idêntico com e sem as pausas, em 1,00; (ii) R_infer_value muda de escolha entre o fluxo com
pausas e o fluxo sem pausas (eventos `status_changed` apagados e `seq` renumerado).

## 3. O que muda

- **Controle.** R_infer_value cobra cada pausa da estratégia do episódio que a precede, como o
  mundo R planta (`value/controls.py`, `_seq_consumed`, em `6e69e69`).
- **Medida.** A mudança de escolha é `R_infer_value_elected ≠ R_infer_value_no_pause_elected`,
  na mesma execução. Não é a comparação com R_reward.
- **Regra dos limiares, para a conjunção.** Para uma previsão que cobre k células, o θ de cada
  célula é o maior valor tal que P(Binom(20, taxa) ≥ ⌈20θ⌉) ≥ 0,80^(1/k). Assim a previsão
  inteira, e não cada célula, tem potência de pelo menos 0,80.
- **Sementes.** Grade nas sementes 21–40, que nenhuma rodada usou. Não há piloto: o
  dimensionamento em 300 sementes, com o mesmo código, já caracteriza o controle.

## 4. Dimensionamento

Sementes 200001–200300, commit `b2362a4`. As taxas abaixo foram recalculadas a partir das
linhas gravadas, com a definição do §3. O relatório automático daquele commit mediu a mudança
contra R_reward; os números quase coincidem, mas a fonte deste adendo é o recálculo.

| Célula | Mudança com e sem pausas | θ (k = 4) | Potência na célula |
| --- | --- | --- | --- |
| R, T = 80 | 0,527 | 0,35 | 0,965 |
| R+, T = 80 | 0,537 | 0,35 | 0,972 |
| R, T = 160 | 0,540 | 0,35 | 0,973 |
| R+, T = 160 | 0,527 | 0,35 | 0,965 |

Potência da conjunção: 0,88. A invariância de R_norm deu 1,00 nas quatro células.

O θ abaixo de 0,50 é esperado, e não é falta de potência. Em R as duas estratégias são iguais
pela norma; sem as pausas, a escolha do controle é quase um sorteio, e em cerca de metade das
execuções ela já estava onde a pausa a empurra.

## 5. Previsão v2

**P3-v2.** Em R e R+, com T = 80 e T = 160, sementes 21–40: (i) o juízo de R_norm é idêntico
com e sem as pausas em 1,00 das execuções, em cada célula; (ii) R_infer_value muda de escolha
em ≥ 0,35 das execuções, em cada célula.

**Classes**, como no §9 do v1: (i) abaixo de 1,00 é contra a tese; (ii) abaixo de 0,35 em
alguma célula é defeito de instrumento.

## 6. Conferências antes do congelamento

1. Um teste aplica a medida e o `decide.py` v2 às linhas do dimensionamento (`b2362a4`) e
   reproduz as quatro taxas da tabela do §4, com tolerância de 0,001. Vermelho se não
   reproduzir.
2. Um teste confere que cada θ v2 do `decide.py` é igual ao da tabela do §4.
