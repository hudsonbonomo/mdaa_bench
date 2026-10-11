# collective/resultados -- guia de validade

## Arquivos validos para o pre-registro

| arquivo | o que contem | etapa |
|---|---|---|
| `sizing_collective_step_c.json` | O, Pn, G (com correcao G2 da formula de expected_empty) | C + G2 |
| `sizing_e4_Pc.json` | Pc com R_pool corrigido (300 seeds x 4 celulas) | E4 |
| `sizing_e4_Pw.json` | Pw com R_pool corrigido (300 seeds x 4 celulas) | E4 |
| `sizing_collective_final.json` | tabela consolidada de theta (todas as quantidades) | G1 |
| `sizing_plugin_O.json` | dados brutos do plugin O (Q1) | C |
| `sizing_plugin_Pn.json` | dados brutos do plugin Pn (Q2) | C |
| `sizing_plugin_G.json` | dados brutos do plugin G (Q4, empty intersection) | C |

## Arquivos supersedidos (commit 0628a09 e anteriores)

Calculados com o R_pool de passo unico e o estimador de media em gates.py.
Mantidos no repositorio para rastreabilidade, mas NAO devem ser usados.

| arquivo | motivo da invalidacao |
|---|---|
| `sizing_plugin_Pc_300001_300075.json` | R_pool antigo (passo unico) |
| `sizing_plugin_Pc_300076_300150.json` | idem |
| `sizing_plugin_Pc_300151_300225.json` | idem |
| `sizing_plugin_Pc_300226_300300.json` | idem |
| `sizing_plugin_Pl_300001_300075.json` | R_pool antigo + estimador de media |
| `sizing_plugin_Pl_300076_300150.json` | idem |
| `sizing_plugin_Pl_300151_300225.json` | idem |
| `sizing_plugin_Pl_300226_300300.json` | idem |
| `sizing_plugin_Pw_300001_300075.json` | R_pool antigo + estimador de media |
| `sizing_plugin_Pw_300076_300150.json` | idem |
| `sizing_plugin_Pw_300151_300225.json` | idem |
| `sizing_plugin_Pw_300226_300300.json` | idem |
| `sizing_collective.json` | agregado anterior ao step C, supersedido |
