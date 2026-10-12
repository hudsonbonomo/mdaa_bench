# PREREGISTRO — `collective/` — adendo v2 (segunda rodada, só o empréstimo do Q3)

**Estado:** v2, congelado em 12 out 2026 com a aprovação de Hudson A. R. Bonomo

## 1. Por que há uma segunda rodada

A auditoria da grade v1 (emenda v1.3, §15 do preregistro v1) mostrou que o R_pool deduplicava
os retornos por `seq` e, como as pessoas compartilham o calendário, guardava só os retornos da
primeira pessoa. O lado do empréstimo do Q3 não foi testado, e o θ₃′ tinha sido dimensionado
com o mesmo defeito. O lado do portão (passa em Pw; curva de recusa em Pl) não dependia do
R_pool e vale como está. Esta rodada testa só o lado do empréstimo e mede o preço da recusa,
com o R_pool corrigido (`6e69e69`). Tudo o mais do preregistro v1 continua valendo, inclusive
os vereditos da v1.

## 2. O que não muda

Mundos Pw e Pc, n ∈ {5, 20}, T ∈ {320, 640}, regra da camada 6 (k = 3, δ = 10, W₀ = 40,
W_max = 160), estimador do portão (mediana, como `sim/density.py`), plugin em `32e0105`, e a
definição do erro do empréstimo no §6 do v1. Na semente, o erro ocorre se, para a maioria das
pessoas que decaem, a janela final de R_H1 for maior que a janela final de R_own da própria
pessoa.

## 3. O que muda

- **R_pool.** A população é lida como uma pessoa só: os retornos de todas as pessoas entram num
  fluxo único, deduplicado por (pessoa, `seq`) e ordenado por (`seq`, pessoa), e a regra da
  camada 6 se aplica a esse fluxo.
- **Preço da recusa, em blocos.** Em Pc, para R_own (cada pessoa) e para R_pool, é o índice do
  primeiro bloco em que a janela chega a W₀ + δ = 50. Para R_pool, o bloco é aquele em que foi
  lido o retorno que fez a janela chegar a 50. A mesma unidade para os dois leitores.
- **Regra dos limiares, para a conjunção:** como no adendo v2 de `value/`. O θ de cada célula
  é o maior valor tal que P(Binom(20, taxa) ≥ ⌈20θ⌉) ≥ 0,80^(1/k).
- **Sementes.** Grade nas sementes 21–40. Não há piloto.

## 4. Dimensionamento

Sementes 300001–300300, commit `b2362a4`. As taxas e os blocos abaixo foram recalculados a
partir dos folds gravados por pessoa. O relatório automático daquele commit dava o preço da
recusa de R_pool em retornos, e não em blocos.

| Célula de Pw | Portão passa | θ₃ (k = 4) | Erro do empréstimo | θ₃′ (k = 4) |
| --- | --- | --- | --- | --- |
| n = 5, T = 320 | 0,987 | 0,95 | 0,987 | 0,95 |
| n = 5, T = 640 | 1,00 | 1,00 | 0,993 | 0,95 |
| n = 20, T = 320 | 1,00 | 1,00 | 1,00 | 1,00 |
| n = 20, T = 640 | 1,00 | 1,00 | 1,00 | 1,00 |

Potência da conjunção: 0,97 para θ₃ e 0,96 para θ₃′. Com o R_pool corrigido, a janela
emprestada chegou ao teto (160) em todas as 2.400 execuções, 1.200 de Pw e 1.200 de Pc. A janela de R_own
ficou em cerca de 121 (T = 320) e 160 (T = 640) para quem não decai, e entre 67 e 106 para
quem decai.

Preço da recusa em Pc, em blocos até a janela chegar a 50: R_own, 6,46 (n = 5) e 6,42
(n = 20); R_pool, 4,09 e 4,00. Cerca de 2,4 blocos.

## 5. Previsão v2

**Q3-v2.** Em Pw, sementes 21–40, em cada célula: (i) o portão passa em ≥ θ₃; (ii) o erro do
empréstimo ocorre em ≥ θ₃′; (iii) R_own nunca ajusta a partir de outros (1,00).

**Classes**, como no §9 do v1: (ii) abaixo de θ₃′ é contra a tese; (i) abaixo de θ₃ é defeito
de instrumento (o mundo não plantou o que diz); (iii) abaixo de 1,00 é defeito do plugin.

**Relatado sem limiar:** o preço da recusa em Pc, por leitor e por célula, em blocos; as
janelas finais médias por subgrupo em Pw para R_own, R_pool e R_H1.

## 6. Conferências antes do congelamento

1. Um teste aplica a medida e o `decide.py` v2 aos folds gravados do dimensionamento
   (`b2362a4`) e reproduz as taxas e os blocos da tabela do §4, com tolerância de 0,01. Vermelho
   se não reproduzir.
2. Um teste confere que cada θ v2 do `decide.py` é igual ao da tabela do §4.
