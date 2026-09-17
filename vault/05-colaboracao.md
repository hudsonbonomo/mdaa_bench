# Colaboração por contratos — entregando células a outras pessoas

O dono deste vault trabalha melhor com colaboração **assíncrona e mediada
por contratos** do que com coordenação contínua. Interface bem definida
substitui reunião (Parnas, 1972). Este arquivo define como empacotar uma
célula para entregar a um colaborador (humano ou agente).

## O pacote de entrega de uma célula

Ao preparar uma célula para outra pessoa, gerar um arquivo
`entregas/<nome-da-celula>.md` com EXATAMENTE estas seções:

```markdown
# Célula: <nome>

## Contrato
- **Provê:** <o que fica pronto e utilizável ao final>
- **Consome:** <o que já existe e pode ser usado (com caminhos exatos)>
- **NÃO toca:** <fronteira negativa — o que é proibido alterar>

## Critério de pronto (binário)
- [ ] build + typecheck verdes
- [ ] <comportamento verificável 1>
- [ ] <comportamento verificável 2>

## Contexto mínimo (≤10 linhas)
<só o que a pessoa precisa para começar; links para docs se necessário>

## Primeiro passo sugerido (<5 min)
<a mesma isca de religação que usamos entre nós>
```

## Regras da colaboração

1. **O contrato é a conversa.** Dúvida sobre o interior da célula → o
   colaborador decide. Dúvida sobre o CONTRATO → pergunta por escrito.
2. **Nunca duas pessoas na mesma célula.** Se precisar, a célula estava
   grande: dividir pelo contrato.
3. **Integração pelo critério de pronto**, não por revisão linha a linha.
   Se os checks passam e o contrato foi respeitado, integra.
4. O agente pode e deve **gerar o pacote de entrega** a partir de uma célula
   do log quando o humano pedir ("empacota a célula X para a/o <nome>").
