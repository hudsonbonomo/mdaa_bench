# Dados e operações protegidas

> [PERFIL HUDSON — substitua pelos SEUS recursos preciosos em `06-adaptacao.md`]

## Recursos DIAMANTE (intocáveis sem aprovação explícita)

| Recurso | Proibições absolutas |
|---|---|
| **MySQL (bases DIAMOND)** | Nunca: pull, reset, delete de dados, alteração de `schema.prisma`, migração |
| **LanceDB (PhDNucleus, 257K+ chunks)** | Nunca: drop, reindexação total, escrita em lote |
| **`vault/estado/log-celulas.md`** | Append-only: nunca editar ou apagar entradas passadas |
| **`SKILL-METODO-*.md` (a lei)** | Read-only. Melhoria vai ao ORIGINAL do método (fora deste projeto) e volta por nova cópia — nunca editar a cópia local |

## O protocolo quando uma tarefa TOCA um recurso protegido

1. Declarar em voz alta: "isto toca <recurso protegido>".
2. Preparar o código/comando SEM executar.
3. Provar que compila (quando aplicável) e mostrar exatamente o que será feito.
4. **ESPERAR** a aprovação explícita, por escrito, nesta conversa.
5. Só então executar — e registrar no log da célula que houve aprovação.

## Regra de leitura

Leitura (SELECT, query, busca vetorial) é livre. A fronteira protege
**mutação e destruição**, não consulta.

## Por que isto existe

Anos de dados clínicos, acadêmicos e de pesquisa vivem nesses recursos.
Nenhuma sessão — por mais confiante — tem autoridade para arriscá-los.
A regra não expressa desconfiança do agente: expressa o valor do acervo.
