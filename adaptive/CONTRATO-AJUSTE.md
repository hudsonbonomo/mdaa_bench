# `mdaa.adjustment` — o ajuste da política (célula do contrato, v0.2, 7 out 2026)

> Nasce onde o código para: a bancada do Paper 6 precisa de um leitor com camada 6, e o
> plugin não tem. Esta célula diz o que qualquer implementação tem de fazer para que um
> valor ajustado continue podendo ser chamado de declarado.

## A decisão

A janela de autorizar de **uma condição** é ela mesma um registro, com três estados de
leitura: **Declarado**, **Ajustado**, **Suspenso**. O plugin pode alongá-la; nunca a
encurta. Encurtar é redeclarar, e redeclarar é ato de quem declarou.

O plugin só ajusta sob uma **regra declarada** — passo, faixa e limiar — posta pelo
hospedeiro ou pela pessoa antes de valer. Sem regra declarada a camada é inerte, e a
jornada se comporta exatamente como antes.

A unidade é o **retorno**: a reentrada na condição. Um retorno conta quando confirma
registros que a janela tinha envelhecido **e** nenhum registro em vigor é contradito
naquele retorno. Registro em vigor contradito é estatuto B: informa, não elege — nem
estratégia, nem régua. Com o limiar de retornos contados **consecutivos**, a janela
alonga um passo. Retorno que contradiz encerra a sequência.

Renomeação de chave suspende: vigora o **último valor declarado**, porque a derivação do
valor ajustado nomeia evidência que não pode mais ser perguntada. Reconciliação, que é
só da pessoa, abre regime novo com contagem zero: o registro reconciliado volta à
leitura, não à contagem. Redeclaração zera a contagem.

## Os objetos

Nenhum evento novo nesta célula. O ajuste **não é gravado**: é derivado no fold, por
regra fixa, a partir do que já está no diário. O que o fold devolve:

```
PolicyReading { state, window, declaredWindow, run, reason, lastReturn, adjustments[] }
Adjustment    { seq, from, to, returns[], confirmed, inForce }   ← a frase, em forma fixa
```

`reason` é obrigatória em todo estado. Declarado abaixo do limiar não é silêncio: diz
que viu, quanto viu e por que ainda não pode agir. No teto da faixa a razão nomeia o
teto, e não o limiar: quem impede o alongamento ali é a faixa.

`lastReturn { seq, kind }` diz o que o último retorno lido **foi** — contado, conflito,
contradito ou neutro. A razão explica o estado e não muda num retorno neutro; sem este
campo, quem lê não distingue "o último retorno foi um conflito" de "houve um conflito
e depois nada". É `null` enquanto nenhum retorno foi lido.

A ponte de linha de comando tem três modos: `fold` (uma leitura), `folds` (o mesmo
diário dobrado em vários momentos, cada um com a condição como escrita então) e `replay`.

## O que os tipos impedem

`assertRule` rejeita faixa acima da janela de aparecer (o invariante autoriza ⊂ aparece
do Paper 5 não se quebra por ajuste). Não existe função que encurte a janela fora da
variante `SYMMETRIC`, que é exportada só para a bancada e que nenhum comando alcança —
como o `tallyWinner` na camada de estatuto. O `Adjustment` não tem campo livre: a frase
é o que os campos dizem.

## Pergunta de Verificação — *como verificamos que isto funciona DE VERDADE?*

1. **Dado coerente:** fluxo real de uma estratégia sob duas condições alternadas; janela
   declarada 40, passo 10, limiar 3. Com sinal estável, a janela alonga depois de três
   retornos contados, e o `Adjustment` nomeia os três.
2. **O que não pode acontecer:** nenhuma sequência de contradições encurta a janela;
   retorno com registros em vigor contraditos nunca conta; abaixo do limiar o valor não
   se move, e a razão vem nomeada.
3. **A frase basta:** `replayDerivation`, alimentado **só** com o que o `Adjustment`
   nomeia, devolve `to`. Com um retorno retirado, devolve `from`.
4. **Regressão:** jornada sem regra declarada produz a mesma recomendação de antes desta
   célula, byte a byte.
4b. **O retorno é dito:** depois de um conflito seguido de um retorno neutro, a razão
   ainda nomeia o conflito e `lastReturn.kind` é `NEUTRAL`. No teto, a razão nomeia o teto.
5. **A história não é relida:** ajustes anteriores a uma renomeação saem idênticos, seja
   qual for o `nowSeq` posterior de onde se dobra.
6. **Falha sem o conserto:** permitir o encurtamento por contradição e o teste 2 fica
   vermelho.

## Fronteira

Entra: as funções puras (`foldPolicy`, `readReturn`, `replayDerivation`, `assertRule`) e
a ponte de linha de comando para a bancada. NÃO entra: eventos de declaração da regra e
da janela por condição, projeção, e a ligação a `recommend.ts` — célula seguinte, depois
da grade; reconciliação parcial; o que o hospedeiro exibe.

## Pontos abertos — para Hudson

**A.** Com mais de uma estratégia sob a mesma condição, o que é "confirmar"? A bancada
tem estratégia-alvo única. O artigo diz que a janela é por condição; se a contagem for
por estratégia, uma estratégia pode alongar a janela das outras. É a razão de a ligação
a `recommend.ts` ficar fora desta célula.

**B.** Sinal `UNCLEAR` não conta para nenhum lado, e um retorno sem maioria é neutro: não
conta e não encerra. Segue a célula de estatuto, e fica provisório pelo mesmo motivo.

**C.** Se o hospedeiro pode redeclarar sem a pessoa — herdado em aberto da célula de
hospedagem.
