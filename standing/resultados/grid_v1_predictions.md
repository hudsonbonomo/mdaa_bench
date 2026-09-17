# Grade v1 — previsoes comprometidas × observado

Preregistro: `standing/PREREGISTRO_v1.md (v1 + emendas v1.1, v1.2, v1.3)`. CLI SHA-256 `8c3cf88999013bca8c55ae0905055f27327a931301e70d4ddd29388f26302543`.
Sementes 1–20 (20). 20 celulas × 20 sementes = 400 execucoes em 26.87 s.

Bracos: A-logged, B-logged, B-unlogged, C-logged, D-logged. T [40, 160], α ['strict', 'lenient'], replicas 1.

> `logged`/`unlogged` e fator do mundo B (§3); A, C e D registram a condicao
> por construcao. `replicas` nao e parametro de `make_world`: a grade roda 1,
> como o piloto. Em D a reconciliacao vem do RNG do gerador (p = ½), nao de
> `force_reconciliation`.

| previsao | celula | limiar (preregistro) | observado | veredito |
|---|---|---|---|---|
| P1 (equivalencia, R_decay) | T=40,alpha=strict | TOST Δ=0,10, α=0,05: equivalente | media 0.0325, max 0.0750, p_lo=1.25e-15, p_hi=1.95e-10 | PASS |
| P1 (equivalencia, R_decay) | T=40,alpha=lenient | TOST Δ=0,10, α=0,05: equivalente | media 0.0325, max 0.0750, p_lo=1.25e-15, p_hi=1.95e-10 | PASS |
| P1 (equivalencia, R_decay) | T=160,alpha=strict | TOST Δ=0,10, α=0,05: equivalente | media 0.0398, max 0.0875, p_lo=1.42e-16, p_hi=4.60e-10 | PASS |
| P1 (equivalencia, R_decay) | T=160,alpha=lenient | TOST Δ=0,10, α=0,05: equivalente | media 0.0398, max 0.0875, p_lo=1.42e-16, p_hi=4.60e-10 | PASS |
| P1b (instrumento, R_declared) | T=40,alpha=strict | TVD(A, B logged) ≥ 0,40 e TVD(A, B unlogged) ≤ 0,05 | logged min 0.500 (media 0.500); unlogged max 0.000 | PASS |
| P1b (instrumento, R_declared) | T=40,alpha=lenient | TVD(A, B logged) ≥ 0,40 e TVD(A, B unlogged) ≤ 0,05 | logged min 0.500 (media 0.500); unlogged max 0.000 | PASS |
| P1b (instrumento, R_declared) | T=160,alpha=strict | TVD(A, B logged) ≥ 0,40 e TVD(A, B unlogged) ≤ 0,05 | logged min 0.500 (media 0.500); unlogged max 0.000 | PASS |
| P1b (instrumento, R_declared) | T=160,alpha=lenient | TVD(A, B logged) ≥ 0,40 e TVD(A, B unlogged) ≤ 0,05 | logged min 0.500 (media 0.500); unlogged max 0.000 | PASS |
| P2 (B logged, out of scope) | T=40,alpha=strict | ≥ 0,95 | 1.0000 (400/400) | PASS |
| P2 (B logged, out of scope) | T=40,alpha=lenient | ≥ 0,95 | 1.0000 (400/400) | PASS |
| P2 (B logged, out of scope) | T=160,alpha=strict | ≥ 0,95 | 1.0000 (1600/1600) | PASS |
| P2 (B logged, out of scope) | T=160,alpha=lenient | ≥ 0,95 | 1.0000 (1600/1600) | PASS |
| P3 (C, estatuto B com ordem) | T=40,alpha=strict | B ≥ 0,95 e nenhum AGED na janela | B 1.00 (20/20), AGED-na-janela 0, ordem legivel 1.00 | PASS |
| P3 (C, estatuto B com ordem) | T=40,alpha=lenient | B ≥ 0,95 e nenhum AGED na janela | B 1.00 (20/20), AGED-na-janela 0, ordem legivel 1.00 | PASS |
| P3 (C, estatuto B com ordem) | T=160,alpha=strict | B ≥ 0,95 e nenhum AGED na janela | B 1.00 (20/20), AGED-na-janela 0, ordem legivel 1.00 | PASS |
| P3 (C, estatuto B com ordem) | T=160,alpha=lenient | B ≥ 0,95 e nenhum AGED na janela | B 1.00 (20/20), AGED-na-janela 0, ordem legivel 1.00 | PASS |
| P3 (C, R_decay reporta decaimento) | T=160,alpha=strict | ≥ 0,80 com T=160 | share<0,5 em 0.95 (media do share 0.440) | PASS |
| P3 (C, R_decay reporta decaimento) | T=160,alpha=lenient | ≥ 0,80 com T=160 | share<0,5 em 0.95 (media do share 0.440) | PASS |
| P4 (D, unevaluable) | T=40,alpha=strict | precisao e revocacao ≥ 0,99, todos voltam apos total, out of scope apos parcial | P=1.0000, R=1.0000, voltam 1.00 (tp=156, fp=0, fn=0) | PASS |
| P4 (D, unevaluable) | T=40,alpha=lenient | precisao e revocacao ≥ 0,99, todos voltam apos total, out of scope apos parcial | P=1.0000, R=1.0000, voltam 1.00 (tp=156, fp=0, fn=0) | PASS |
| P4 (D, unevaluable) | T=160,alpha=strict | precisao e revocacao ≥ 0,99, todos voltam apos total, out of scope apos parcial | P=1.0000, R=1.0000, voltam 1.00 (tp=636, fp=0, fn=0) | PASS |
| P4 (D, unevaluable) | T=160,alpha=lenient | precisao e revocacao ≥ 0,99, todos voltam apos total, out of scope apos parcial | P=1.0000, R=1.0000, voltam 1.00 (tp=636, fp=0, fn=0) | PASS |
| P4 — leitura estrita (diagnostico, sem limiar) | T=40,alpha=strict | APPLICABLE apos total | 1.00; 0 registros pre-τ₁ voltaram AGED (fora da janela de α) | — |
| P4 — leitura estrita (diagnostico, sem limiar) | T=40,alpha=lenient | APPLICABLE apos total | 1.00; 0 registros pre-τ₁ voltaram AGED (fora da janela de α) | — |
| P4 — leitura estrita (diagnostico, sem limiar) | T=160,alpha=strict | APPLICABLE apos total | 0.80; 212 registros pre-τ₁ voltaram AGED (fora da janela de α) | — |
| P4 — leitura estrita (diagnostico, sem limiar) | T=160,alpha=lenient | APPLICABLE apos total | 0.80; 160 registros pre-τ₁ voltaram AGED (fora da janela de α) | — |
| P4b (espelho-controle, R_current) | T=40,alpha=strict | 1,00 | 1.00 (20 sementes) | PASS |
| P4b (espelho-controle, R_current) | T=40,alpha=lenient | 1,00 | 1.00 (20 sementes) | PASS |
| P4b (espelho-controle, R_current) | T=160,alpha=strict | 1,00 | 1.00 (20 sementes) | PASS |
| P4b (espelho-controle, R_current) | T=160,alpha=lenient | 1,00 | 1.00 (20 sementes) | PASS |
| P5 (A, divergencia com causa) | A, T=160, alpha=lenient | divergencia ≥ 0,90 e razao = bloqueio por B em 1,00 | divergencia 1.00 (20/20), B_blocking 1.00 | PASS |

## Veredito por previsao

| previsao | celulas | PASS |
|---|---|---|
| P1 | 4 | 4/4 — PASS |
| P1b | 4 | 4/4 — PASS |
| P2 | 4 | 4/4 — PASS |
| P3 | 4 | 4/4 — PASS |
| P4 | 4 | 4/4 — PASS |
| P4b | 4 | 4/4 — PASS |
| P5 | 1 | 1/1 — PASS |
