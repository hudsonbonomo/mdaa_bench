# Guia de adaptação — tornando este vault SEU

> Escrito pensando em você, Aline. Mas serve para qualquer pessoa. 💜

Este vault tem duas camadas. A **camada de protocolo** é genérica e
provavelmente serve para você como está. A **camada de perfil** é do Hudson
e é exatamente o que você vai substituir.

## O que FICA (protocolo genérico)

- `CLAUDE.md` — ajuste apenas a lista de regras se necessário
- `01-celulas.md` — o ciclo abrir/trabalhar/fechar
- `02-estado.md` — os formatos de registro
- `05-colaboracao.md` — contratos de entrega
- `.claude/skills/` — os comandos `/celula` e `/pausar`
- `vault/estado/` — zere os arquivos (apague as entradas, mantenha os cabeçalhos)

## O que você SUBSTITUI (perfil pessoal)

### 1. `00-perfil.md` — reescreva por inteiro
Perguntas-guia para escrever o seu:
- Como sua energia funciona? O que renova, o que drena?
- Qual o SEU ciclo natural de trabalho? (o do Hudson é paper→foco→código→
  cansaço→anotação; o seu pode ser outro — desenhe o real, não o ideal)
- O que um assistente faz que te AJUDA de verdade? (seja concreta)
- O que te atrapalha, trava ou irrita? (seja mais concreta ainda)
- Que tamanho de célula funciona para você? (30 min? 2 horas?)

### 2. `03-regras-codigo.md` — troque os valores
As regras do Hudson (200 linhas, build-gate, proibição de lote) vêm do
método dele. Mantenha a ESTRUTURA (limites claros + gate de verificação +
protocolo para operações perigosas) e ponha os SEUS números e ferramentas.

### 3. `04-protecoes.md` — liste os SEUS recursos preciosos
Bancos, pastas, APIs, dados de terceiros — o que nenhuma sessão pode tocar
sem sua aprovação explícita. Se não souber ainda, deixe a tabela vazia e
preencha na primeira semana de uso: você vai descobrir rápido.

### 4. `SKILL-METODO-TMULAB.md` (a lei, na raiz)

É o método de engenharia (MIT, base de Fábio Akita + extensões do Hudson).
Três opções, todas válidas: manter como está (serve a qualquer projeto com
código), trocar pela SUA lei mantendo a estrutura em camadas (lei → vault →
projeto), ou remover a referência no CLAUDE.md se seu projeto não tem código.
O que não muda: a cópia local é read-only — método evolui no original.

## Teste de adaptação bem-feita

Abra o projeto no seu agente, digite `/celula` e trabalhe uma sessão real.
Depois digite "cansei". Se a religação da sessão seguinte custar menos de
5 minutos e você não tiver precisado explicar seu jeito nenhuma vez — o
vault é seu.

## Uma nota do Hudson (via Claude)

Este modo não corrige ninguém. Ele parte do princípio de que o seu jeito de
funcionar é o motor, não o problema — e constrói a engenharia em volta dele.
Adapte sem cerimônia: o vault certo é o que descreve você.
