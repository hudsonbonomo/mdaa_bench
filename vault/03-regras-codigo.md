# Regras de código — perfil local (a lei mora na SKILL)

> **A lei é `SKILL-METODO-TMULAB.md`, na raiz.** Leia-a na íntegra antes de
> qualquer tarefa de código — TDD (R1), Pergunta de Verificação (R1.1),
> Verificação Trilateral + strict total (R2), escala de sessão (R3), erros
> epistêmicos do agente (R4.1), DIAMOND (R13), design literal (R14),
> comunicação (R15). Este arquivo NÃO a repete: guarda só os valores locais
> e o estilo da casa. **Em conflito, a SKILL vence.**
> [PERFIL HUDSON — adapte os valores em `06-adaptacao.md`]

## Valores locais (parametrizam a lei)

1. **Máximo ~200 linhas** por arquivo e por tarefa (R3 local). Passou,
   a célula estava grande: dividir.
2. **Operações em lote** (scan, ingest, migração, seed): preparar → provar
   que compila → mostrar o plano → **ESPERAR aprovação explícita**. Sempre.
3. **Um commit por célula fechada**, mensagem citando a célula. Flexão
   legítima: quando duas células tocam os mesmos arquivos por razão real,
   commit único nomeando ambas — o registro manda na regra, nunca o inverso.

## Estilo da casa (preferências, não lei)

- Caminhos EXATOS sempre — nada de "no arquivo de config".
- Diffs pequenos e completos, não trechos soltos.
- Erros reportados com a mensagem REAL, literal — nunca paráfrase otimista.
- Arquivo novo justifica em 1 linha por que não coube num existente.

## Relação com as células

A lei dá o rigor (testes, gates, DIAMOND); as células dão o tamanho e o
ritmo. Juntas: nenhuma sessão cansada dispara nada irreversível, e nenhum
"funciona?" é respondido com "os testes passam".
