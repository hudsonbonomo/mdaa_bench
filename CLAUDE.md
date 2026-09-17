# Modo Celular — como este humano trabalha

Este projeto segue o **Modo Celular**: trabalho em células pequenas de foco,
com estado sempre anotado para retomada. O dono deste projeto é neurodivergente
e este modo não é uma preferência estética — é a arquitetura cognitiva dele.
Respeitá-la é condição de qualidade do trabalho.

Leia `vault/00-perfil.md` antes da primeira tarefa de cada sessão.

## As sete regras inegociáveis

1. **Uma célula ATIVA por vez** (pausadas coexistem no índice). Escopo pequeno,
   fronteira clara. Não expandir o
   escopo por iniciativa própria. Protocolo completo: `vault/01-celulas.md`.
2. **Retomável ⟺ anotado.** Todo fim de célula atualiza o estado
   (`vault/estado/`). O que não foi anotado não existe para a próxima sessão.
3. **Máximo ~200 linhas** por arquivo e por tarefa. Detalhes: `vault/03-regras-codigo.md`.
4. **Build + typecheck antes de qualquer teste ou entrega.** Nunca declarar
   algo pronto sem build verde.
5. **NUNCA executar operações em lote ou destrutivas sem aprovação explícita.**
   Preparar o código, mostrar que compila, e ESPERAR. Recursos protegidos:
   `vault/04-protecoes.md`.
6. **Divergência é método, não distração.** Se o humano abrir uma ideia
   paralela: sinalize riscos como parceiro, capture no estacionamento
   (`vault/estado/estacionamento.md`), mas NUNCA bloqueie nem trate como
   desvio. Ele decide o rumo; você segura o fio.
7. **Cansaço é sinal de protocolo, não problema.** "Cansei", "vou parar",
   "anota aí" → executar o fechamento de célula (skill `pausar`) com cuidado
   e sem culpabilizar.

## Método (a lei)

Este pacote inclui `SKILL-METODO-TMULAB.md` na raiz — o Método Akita
Estendido (TMULAB v5.1): TDD, Verificação Trilateral, Pergunta de
Verificação, DIAMOND, erros epistêmicos do agente e mais. **Leia e siga
antes de qualquer tarefa de código.** Em conflito com
`vault/03-regras-codigo.md`, a SKILL vence. A cópia é read-only DIAMOND:
melhoria de método vai ao ORIGINAL (fora deste projeto) e volta por nova
cópia — nunca editar a cópia local.

## Comandos do modo

- `/celula` — abrir/retomar célula; `/celula <nome>` retoma uma célula específica do índice
- `/pausar` — fechar a célula atual anotando estado para retomada

## Mapa do vault

| Arquivo | O que contém |
|---|---|
| `vault/00-perfil.md` | Quem é este humano e como ele funciona |
| `vault/01-celulas.md` | O protocolo de células: abrir, trabalhar, fechar |
| `vault/02-estado.md` | Formato dos registros de estado |
| `vault/03-regras-codigo.md` | Regras de código (Método Akita Estendido) |
| `vault/04-protecoes.md` | Dados e operações protegidas |
| `vault/05-colaboracao.md` | Como entregar células a colaboradores |
| `vault/06-adaptacao.md` | Guia para adaptar este vault a outra pessoa |
| `vault/estado/` | Estado vivo: índice de células, ativa, celulas/, log, estacionamento |
| `SKILL-METODO-TMULAB.md` (raiz) | A LEI de engenharia — Método TMULAB (Akita Estendido) |
