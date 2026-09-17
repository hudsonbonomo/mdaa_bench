---
name: pausar
description: Fechar ou concluir a célula atual do Modo Celular anotando o estado para retomada. Use SEMPRE que o usuário disser /pausar, "cansei", "vou parar", "chega por hoje", "anota aí", "continuo depois", "preciso sair", "fecha essa célula", "conclui a célula", ou demonstrar cansaço. Também use ANTES de trocar para outra célula ou assunto grande.
---

# Fechar célula (pausar ou concluir)

O fechamento é o ato mais importante do Modo Celular: é ele que torna o
retorno barato. Execute com cuidado, em poucas trocas.

## Passos

0. GUARD DE INTEGRIDADE: leia `INDICE.md` — toda célula ⏸ ou ✔ deve ter ≥1
   entrada em `log-celulas.md` (📋 planejadas isentas). Log menor do que o
   índice implica → PARE, acuse "log encolhido" com a diferença, reconstrua
   as ausentes de `INDICE.md` + `celulas/*.md` (marcadas `[reconstruída]`)
   e só então appende.
1. Colete os FATOS da sessão (o que foi feito de verdade, não intenções):
   arquivos tocados com caminho exato, decisões tomadas, status de
   build/typecheck.
2. **Append** no `vault/estado/log-celulas.md` (formato em
   `vault/02-estado.md`). Append-only: NUNCA editar entradas passadas.
3. Escreva a projeção completa em `vault/estado/celulas/<slug>.md`
   (mesmo formato do CELULA-ATUAL.md, campo Plugin/área incluído).
4. Atualize a linha da célula no `vault/estado/INDICE.md`:
   - Pausa normal → status ⏸, data de hoje, próximo passo em 1 linha.
   - Critério de pronto atingido → pergunte "concluímos esta célula?";
     se sim → status ✔, e o próximo passo vira "—".
5. Reescreva `vault/estado/CELULA-ATUAL.md` como:
   "nenhuma célula ativa · N pausadas — ver INDICE.md", listando as 3
   pausadas mais recentes com seus próximos passos (1 linha cada).
6. O PRÓXIMO PASSO registrado é a peça-chave: **UMA ação concreta,
   executável em <5 minutos, sem precisar pensar**. Proponha e confirme.
   Bom: "rodar `pnpm test vigilia` e ler o primeiro erro".
   Ruim: "continuar a refatoração".
7. Ideias soltas da sessão → `vault/estado/estacionamento.md`.
8. Despedida em uma linha, leve, sem culpa e sem listar pendências.
   As células sabem esperar.

## Nunca
- Nunca minimize o cansaço nem sugira "só mais uma coisinha".
- Nunca feche sem próximo passo registrado (retomável ⟺ anotado) —
  exceto célula ✔ concluída.
- Nunca transforme o fechamento em retrospectiva longa.
- Nunca apague o arquivo de uma célula concluída: ele é histórico.
