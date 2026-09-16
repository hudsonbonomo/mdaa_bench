# Piloto P1 — potência (sementes 901–905)

**Data:** 2026-09-16. **Escopo:** PREREGISTRO_v1 §7, previsão P1.
**Sementes:** 901, 902, 903, 904, 905 — **piloto, descartadas por preregistro (§5).
Não entram em resultado do paper.** Nenhuma semente da grade (1–20) foi usada.

**CLI:** `standing-cli.js`, commit `f25caa0`,
SHA-256 `07b2464d2be93e3ad68f65d61bd841e4465fed34fc142b101b3e8b7d9229db7a` (conferido
antes da execução). Guardião de congelamento (`tests/test_freeze_guardian.py`) verde.

## Grade do piloto

T ∈ {40, 160} × α ∈ {strict, lenient} = 4 células × 5 sementes = 20 observações.
O fator **réplicas** de §5 é intra-pessoa e `make_world` não recebe tal parâmetro:
a geração de mundo não se move com ele, então o piloto roda réplicas = 1.

## Medidas

| Célula | média DVT | média desacordo |
| --- | --- | --- |
| T=40, α=strict | 0,00 | 0,00 |
| T=40, α=lenient | 0,00 | 0,00 |
| T=160, α=strict | 0,00 | 0,00 |
| T=160, α=lenient | 0,00 | 0,00 |

Agregado: n = 20, média DVT = 0,00 (dp 0,00), média desacordo = 0,00 (dp 0,00).
**As duas medidas são exatamente zero em todas as sementes e todas as células.**

## Potência

| Quantidade | Valor |
| --- | --- |
| Potência DVT, Δ = 0,10 | 1,000 |
| Potência desacordo, Δ = 0,10 | 1,000 |
| Potência conjunta, Δ = 0,10 | 1,000 |
| IC 95% (erro de Monte Carlo) | [0,9996; 1,000] |
| Δ mínimo com potência ≥ 0,80 | 0,05 (piso da varredura) |

Bootstrap: 10 000 reamostras com reposição para n = 20, mesmos índices para as duas
medidas; TOST bilateral (dois testes t unilaterais), rejeita com ambos p < α/2 = 0,025.
Varredura de Δ de 0,05 a 0,50 em passos de 0,01: potência 1,000 em todo o intervalo.

**Δ = 0,10 fica como está. Não há emenda v1.1 de Δ a fazer.**

## Leitura honesta do resultado

A potência é 1,000 porque as medidas têm **variância zero por construção**, não porque
o piloto seja grande. Em B `unlogged` todas as observações são gravadas como `c1` e a
condição vigente é `c1`; em A todas são `stable` e a vigente é `stable`. Nos dois
mundos, portanto, **todo registro está em escopo**, e o estatuto que R_declared atribui
passa a depender só da idade — que é a mesma trajetória de `seq` nos dois. As
distribuições de ν coincidem registro a registro, não em média. Isso é exatamente o
"indeterminado por construção" de §3, e é a previsão de P1: falha em distinguir.

Consequência metodológica: o TOST aqui decide no limite de variância nula (a decisão
recai sobre a média), e o intervalo relatado é erro de Monte Carlo do reamostrador, não
incerteza amostral do piloto. Um piloto de 5 sementes não sustenta uma afirmação de
potência quando há variância; sustenta esta porque não há.

## Defeito de instrumento corrigido antes da execução

`standing/readers.py`, `to_payload`: a política era enviada ao CLI em *snake_case*
(`appear_window`, `warrant_window`), enquanto `dist/standing.js` lê *camelCase*
(`appearWindow`, `warrantWindow`). As janelas chegavam como `undefined`, toda
comparação de idade falhava e **todo registro saía `AGED`** em todas as células. Com a
tradução corrigida, T=160/strict dá 40 `APPLICABLE` + 120 `AGED` e T=160/lenient dá
120 + 40, como α manda. `alpha_frozen.json` não foi tocado — a tradução mora no leitor.

## Pendência conhecida, fora do piloto

`vocabulary_events` de `worlds.py` usa `{"type", "t", "from"/"to", "kind"}`; o CLI lê
`{"kind": "KEY_RENAMED"|"RECONCILED", "seq", "from"/"to", "oldKey"/"newKey",
"valueMap"}`. Além disso o CLI renomeia **chaves** de condição, enquanto o mundo D
renomeia o **valor** `c1 → c1_prime` sob a chave `env`. Nada disso afeta P1 (A e B não
têm eventos de vocabulário), mas **P4 e P4b não rodam corretamente sem reconciliar esse
contrato**. Não foi alterado aqui.

## Arquivos

- `standing/pilot_power.py` — o script (185 linhas)
- `standing/resultados/pilot_power.json` — números completos, varredura de Δ inclusa

Tempo de execução: 3,08 s (20 chamadas ao CLI + 10 000 × 47 TOSTs vetorizados).
