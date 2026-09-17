# Contrato do Painel v1 (sem grafo)

> Escrito ANTES de qualquer código (princípio 1). Célula "Painel v1", 25/08/2026.
> Mesmo formato da C2 (A1–A4) e da C4 (B1–B4): critérios mecânicos primeiro,
> veredito com evidência depois. Série **V** (de Verificação) porque A, B, D, E e P
> já estão usados neste projeto e C colide com os nomes das células.

## A pergunta

**Eu, cansado, olho a página e sei onde estou em 10 segundos?**

Essa é a pergunta humana e ela não é testável por máquina. O que É testável — e o que
este contrato cobre — é a condição necessária: **a página diz a verdade sobre o vault,
e continua dizendo enquanto um agente trabalha, sem F5.** Página que mente, ou que
congela, falha antes de chegar ao critério humano.

## Decisões pré-comprometidas (não reabrir durante a célula)

1. **Zero dependências de produção.** Só `node:*`. Padrão `sdd-para-vault`.
2. **Read-only absoluto** sobre o projeto-alvo. O painel nunca escreve lá — V6 prova.
3. **Watch no DIRETÓRIO** `vault/estado/`, filtrado por nome, **debounce 80ms**
   (o `fs.watch` do Windows duplica evento e perde watch em rename).
4. **Porta ocupada falha ALTO**, nomeando a porta. Não tenta a próxima: porta diferente
   da pedida é o tipo de silêncio que faz olhar a aba errada. Default `3007`.
5. **Anúncio antes de esperar**, e honesto sobre o mecanismo:
   `servindo <projeto> na porta N — observando vault/estado/ (M arquivos)`.
   (A fronteira dizia "observando M arquivos"; o watch é de diretório, então o anúncio
   declara os dois — senão o anúncio mente na segunda escrita.)
6. **Sem `contratos/mapa-de-chaves.md` o painel roda.** Degradação declarada, não erro.

## A fixture (dado simulado porém COERENTE — Regra 1.1, passo 1)

`tools/painel/fixture/mini-projeto/` com a cara do vault real, nunca `foo`/`bar`:

- `vault/estado/INDICE.md` — **duas tabelas** (a armadilha real: o índice do edtech-nll
  tem quatro, e um parser que lê só a primeira perde metade das células), **6 células**:
  2 ✔ · 1 🔵 · 1 ⏸ · 2 📋. Metade com link `[nome](celulas/slug.md)`, metade sem —
  as duas formas existem no índice real.
- `vault/estado/CELULA-ATUAL.md` — com a seção `## ➜ PRÓXIMO PASSO` e uma frase exata.
- `contratos/mapa-de-chaves.md` — presente aqui; **ausente** na variante `mini-sem-mapa/`.

## Escopo de resposta declarado ANTES de rodar (Regra 1.1, passo 2)

| | Valor exato esperado |
|---|---|
| células parseadas | **6** |
| contagens | **2 ✔ · 1 🔵 · 1 ⏸ · 2 📋** |
| próximo passo | a string exata da `CELULA-ATUAL.md` da fixture, sem o `## ➜` |
| HTTP da página | **200**, `content-type: text/html` |
| eventos SSE por escrita | **exatamente 1** |
| escritas no projeto-alvo | **0 bytes, 0 arquivos** |

## Os 6 critérios de aceite (mecânicos)

### V1 · Parse fiel — varre TODAS as tabelas
```
parse(fixture) → 6 células
contagens === { '✔': 2, '🔵': 1, '⏸': 1, '📋': 2 }
célula com link e célula sem link chegam iguais no resultado
```
**Vermelho sem o conserto:** parser que para na primeira tabela devolve 3, não 6.

### V2 · A alma está no topo
A página contém a **frase exata** do PRÓXIMO PASSO e as 4 contagens.
```
GET / → 200
corpo.includes(<frase exata do próximo passo>)
corpo tem as 6 células, cada uma sob seu status
```
**Vermelho sem o conserto:** sem a seção do próximo passo, a asserção da frase cai.
**Nota de fronteira:** quando não há célula 🔵, `CELULA-ATUAL.md` continua tendo um
`## ➜ PRÓXIMO PASSO` (hoje: "Dizer `/celula` para abrir a C5"). O painel lê a seção,
não a célula ativa — senão a alma some justo no momento de escolher o que fazer.

### V3 · AO VIVO — exatamente 1 evento por escrita
```
cliente SSE conectado → escrever UMA vez no INDICE.md da fixture
→ em ≤500ms chega EXATAMENTE 1 evento (não 2, não 0)
```
**Vermelho sem o conserto:** sem o debounce de 80ms, o `fs.watch` do Windows entrega
2+ eventos para a mesma escrita e a asserção `=== 1` fica vermelha. É o teste que
prova o debounce em vez de afirmá-lo.

### V4 · Degradação declarada, não erro
```
painel(mini-sem-mapa) → sobe, GET / → 200
corpo.includes('sem grafo: mapa ausente')
```
**Vermelho sem o conserto:** um `readFileSync` sem guarda lança ENOENT e o GET nunca
chega a 200.

### V5 · Fail-fast alto, ANTES de abrir a porta
```
painel(<pasta sem vault/estado>) → exit code ≠ 0
stderr cita o caminho procurado
nada escutando na porta
```
Rodado como **processo-filho com timeout** (padrão `sdd-para-vault`: `execFileSync`
com `timeout`), para que travar fique vermelho em vez de passar batido.
**Vermelho sem o conserto:** sem a checagem, o processo sobe e o teste morre no timeout.

### V6 · Read-only provado
Fotografar a fixture inteira (caminho → conteúdo) antes e depois de subir, servir e
disparar o watch. **Idêntica.** Painel que edita o vault que ele observa é um laço.
**Vermelho sem o conserto:** qualquer escrita acidental muda a foto.

## Split das 200 linhas

| Arquivo | Responsabilidade |
|---|---|
| `parse.mjs` | ler `INDICE.md` + `CELULA-ATUAL.md` → estrutura (V1) |
| `painel.mjs` | HTML autocontido, server, SSE, watch, CLI, fail-fast (V2–V5) |
| `painel.test.mjs` | V1–V6, com fixture e vermelho-provado |

Parsing **linear** (varredura de linhas, split por `|`), sem regex sobre entrada
livre — a lição do backlog: dois regex perderam 4 chaves ⚠ em silêncio.

## Veredito — 25/08/2026, célula fechada ✔

**Funciona:** rodei o painel REAL (servidor, `fs.watch`, SSE de verdade — mock em nada)
sobre a fixture coerente e sobre o próprio edtech-nll; a saída caiu no escopo declarado
acima; e provei que cada critério fica vermelho sem o seu conserto.

**Gates:** painel **11/11** (`node --test`) · repo intacto: `tsc --noEmit` limpo + **17/17**
no vitest (o `include` explícito da C3 mantém as duas suítes separadas).

**As 6 provas de vermelho** (uma mutação por critério, restaurada em seguida):

| | Mutação | Vermelho observado |
|---|---|---|
| V1 | parser para na 1ª tabela | 3 células em vez de 6 |
| V2 | não lê a seção `## ➜` | a frase exata some da página |
| V3 | **remove o debounce** | `expected: 1, actual: 2` |
| V4 | `temMapa: true` sempre | some "sem grafo: mapa ausente" |
| V5 | erro sem citar o caminho | stderr não basta para consertar |
| V6 | painel escreve 1 arquivo | a foto do alvo muda |

**Achado da célula — a primeira mutação de V3 não valia.** `DEBOUNCE = 0` ficou VERDE: o
`setTimeout(…, 0)` ainda coalesce no mesmo tick, então o teste teria passado sem provar
nada. A mutação certa é remover o debounce inteiro — aí saem **2 eventos** para uma
escrita. A duplicação do `fs.watch` no Windows não é folclore: foi medida nesta máquina.
**Lição: mutação fraca dá falso verde na prova de vermelho — a mutação tem de apagar o
mecanismo, não afrouxá-lo.**

**Defeito que só a página real mostrou:** o nome da célula no topo vinha com markdown cru
(`Painel v1 — [projeção completa](...)`). Teste escrito, vermelho visto, conserto feito —
`nomeDaCelula` entende as duas formas que convivem no vault.

**Rodado contra o edtech-nll:** `✔ 7 · 🔵 1 · ⏸ 0 · 📋 17`, com uma escrita real no
`CELULA-ATUAL.md` reescrevendo a página sozinha, sem F5.

**Escolhas declaradas (não são dívida escondida):** a v1 **não transforma markdown** —
renderizar `código` quebraria a asserção da frase exata do PRÓXIMO PASSO; e porta ocupada
falha alto citando a porta, comportamento implementado mas **não coberto** por V1–V6.
