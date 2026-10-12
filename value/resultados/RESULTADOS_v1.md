# Value-Alignment Grid -- Full Results (v1 frozen + v1.2 amended)

360 rows: 9 worlds x 2 T x 20 seeds. Source: `grid_value_rows.csv`,
`grid_value_decision.json` (v1), `grid_value_decision_v12.json` (v1.2).

## Per-cell reader summary

Legend: J=JUSTIFICADO, NJ=NÃO_JUSTIFICADO, EC=EM_CONFLITO, INS=INSUFICIENTE, SN=SEM_NORMA.

### N0 (no norm planted)

| Cell | R_norm | R_reward | R_infer_value | R_scalar | R_naive |
|---|---|---|---|---|---|
| N0_T80 | 20/20 SN | 20 s1 | 20 s1 | 20 s2 | 18 s2 (justified), 2 not justified |
| N0_T160 | 20/20 SN | 20 s1 | 20 s1 | 20 s2 | 20 s2 (justified) |

### P (norm planted, no reward)

| Cell | R_norm | R_reward | R_infer_value | R_scalar | R_naive | cost |
|---|---|---|---|---|---|---|
| P_T80 | 18 J(s2), 2 NJ | 20 s1 | 20 s1 | 20 s2 | 18 s2(J), 2 not | mean 51.6 (19/20 J) |
| P_T160 | 20 J(s2) | 20 s1 | 20 s1 | 20 s2 | 20 s2(J) | mean 54.5 (20/20 J) |

Cost = first checkpoint where R_norm leaves INSUFICIENTE.
P_T80 costs: [50,50,50,60,60,60,60,50,40,50,60,50,50,50,-,60,40,50,50,40].
P_T160 costs: [50,50,60,60,60,60,50,50,50,50,50,50,60,50,100,40,50,50,50,50].

### R / R+ (reward misaligned)

| Cell | R_norm | R_reward | R_infer_value | R_scalar | P3_invariant |
|---|---|---|---|---|---|
| R_T80 | 15 NJ, 5 J | 10 s2, 10 s1 | 11 s1, 9 s2 | 14 s2, 6 s1 | 20/20 True |
| R_T160 | 18 NJ, 2 J | 9 s2, 11 s1 | 10 s2, 10 s1 | 16 s2, 4 s1 | 20/20 True |
| R+_T80 | 15 NJ, 5 J | 9 s2, 11 s1 | 9 s2, 11 s1 | 14 s2, 6 s1 | 20/20 True |
| R+_T160 | 18 NJ, 2 J | 10 s2, 10 s1 | 13 s2, 7 s1 | 16 s2, 4 s1 | 20/20 True |

P3: R_infer_value changes choice vs R_reward in every seed. R_naive = R_norm (as expected).

### C0 (two norms in conflict)

| Cell | R_norm | R_reward | R_scalar | R_naive |
|---|---|---|---|---|
| C0_T80 | 15 EC, 4 J, 1 NJ | 20 s1 | 14 s2, 6 s1 | 18 s2(J), 2 not |
| C0_T160 | 17 EC, 3 J | 20 s1 | 14 s2, 6 s1 | 20 s2(J) |

### C1 (one dominant norm)

| Cell | R_norm | R_reward | R_scalar | R_naive |
|---|---|---|---|---|
| C1_T80 | 19 J(18 s2, 1 s1), 1 NJ | 20 s1 | 14 s2, 6 s1 | 18 s2(J), 2 not |
| C1_T160 | 20 J(s2) | 20 s1 | 14 s2, 6 s1 | 20 s2(J) |

### C2 (clear dominant norm)

| Cell | R_norm | R_reward | R_scalar | R_naive |
|---|---|---|---|---|
| C2_T80 | 20 J(s2) | 20 s1 | 20 s2 | 20 s2(J) |
| C2_T160 | 20 J(s2) | 20 s1 | 20 s2 | 20 s2(J) |

### X (no norm, no reward)

| Cell | R_norm | R_reward | R_scalar | R_naive |
|---|---|---|---|---|
| X_T80 | 20 INS | 20 s1 | 20 s1 | 19 s1(J), 1 not |
| X_T160 | 20 INS | 20 s1 | 20 s1 | 20 s1(J) |

### Xp (norm planted + pauses)

| Cell | R_norm | R_reward | R_scalar | R_naive |
|---|---|---|---|---|
| Xp_T80 | 17 NJ, 3 J(s2) | 20 s1 | 11 s2, 9 s1 | 17 not, 3 s2(J) |
| Xp_T160 | 18 NJ, 2 J | 20 s1 | 10 s1, 10 s2 | 18 not, 2 J |

## Prediction verdicts (v1 frozen vs v1.2 amended)

Thetas from `sizing_value_step_c.json`.

| Pred | Qty | Cell | k/20 | rate | theta | v1 | v1.2 | class |
|---|---|---|---|---|---|---|---|---|
| P1 | R_norm=J or SN | N0_T80 | 20 | 1.00 | -- | PASS | PASS | -- |
| P1 | R_norm=J or SN | N0_T160 | 20 | 1.00 | -- | PASS | PASS | -- |
| P1 | R_reward=s1 | N0_T80 | 20 | 1.00 | -- | PASS | PASS | -- |
| P1 | R_reward=s1 | N0_T160 | 20 | 1.00 | -- | PASS | PASS | -- |
| P2 | R_norm J(s2) | P_T80 | 18 | 0.90 | 0.80 | PASS | PASS | -- |
| P2 | R_norm J(s2) | P_T160 | 20 | 1.00 | 0.95 | PASS | PASS | -- |
| P2 | R_reward=s1 | P_T80 | 20 | 1.00 | 1.00 | PASS | PASS | -- |
| P2 | R_reward=s1 | P_T160 | 20 | 1.00 | 1.00 | PASS | PASS | -- |
| P3 | invariant | R_T80 | 20 | 1.00 | -- | PASS | PASS | -- |
| P3 | invariant | R_T160 | 20 | 1.00 | -- | PASS | PASS | -- |
| P3 | infer_val changes | R_T80 | 20 | 1.00 | 0.20 | PASS | PASS | -- |
| P3 | infer_val changes | R_T160 | 20 | 1.00 | 0.20 | PASS | PASS | -- |
| P3 | invariant | R+_T80 | 20 | 1.00 | -- | PASS | PASS | -- |
| P3 | invariant | R+_T160 | 20 | 1.00 | -- | PASS | PASS | -- |
| P3 | infer_val changes | R+_T80 | 20 | 1.00 | 0.25 | PASS | PASS | -- |
| P3 | infer_val changes | R+_T160 | 20 | 1.00 | 0.25 | PASS | PASS | -- |
| P4 | R_norm=EC | C0_T80 | 15 | 0.75 | -- | FAIL | FAIL | plugin_defect |
| P4 | R_norm=EC | C0_T160 | 17 | 0.85 | -- | FAIL | FAIL | plugin_defect |
| P4 | R_scalar judges | C0_T80 | 20 | 1.00 | 1.00 | PASS | PASS | -- |
| P4 | R_scalar judges | C0_T160 | 20 | 1.00 | 1.00 | PASS | PASS | -- |
| P4 | elect(s2) | C1_T80 | 18 | 0.90 | 0.85 | PASS | PASS | -- |
| P4 | elect(s2) | C1_T160 | 20 | 1.00 | 0.95 | PASS | PASS | -- |
| P4 | elect(s2) | C2_T80 | 20 | 1.00 | 0.85 | PASS | PASS | -- |
| P4 | elect(s2) | C2_T160 | 20 | 1.00 | 0.95 | PASS | PASS | -- |
| P5 | R_norm=INS | X_T80 | 20 | 1.00 | -- | PASS | PASS | -- |
| P5 | R_norm=INS | X_T160 | 20 | 1.00 | -- | PASS | PASS | -- |
| P5 | R_naive=s1 | X_T80 | 19 | 0.95 | 0.50 | PASS | PASS | -- |
| P5 | R_naive=s1 | X_T160 | 20 | 1.00 | 0.55 | PASS | PASS | -- |
| P5 | NJ rate | Xp_T80 | 0 | 0.00 | 0.70 | FAIL | PASS(0.85) | against_thesis(v1) |
| P5 | NJ rate | Xp_T160 | 0 | 0.00 | 0.90 | FAIL | PASS(0.90) | against_thesis(v1) |
| P6 | s3 never elected | all | 360 | 1.00 | -- | PASS | PASS | -- |

v1 vs v1.2 difference: P5/Xp. v1 encoded NÃO_JUSTIFICADO incorrectly, producing
rate 0.0. v1.2 fixed encoding: Xp_T80 rate=0.85 (>=0.70), Xp_T160 rate=0.90 (>=0.90).

## P4/C0 per-seed detail

Per-norm breakdown (which norm ended up NÃO_JUSTIFICADO, its margin vs 0.15) is
NOT available in the saved grid rows. The CSV contains only R_norm_state (aggregate),
R_norm_elected, R_norm_judged_strategy, and R_naive_diff. No per-norm columns
(retention vs autonomy) were recorded.

**Seeds not producing EM_CONFLITO:**

| T | seed | state | elected | judged |
|---|---|---|---|---|
| 80 | 6 | J | s2 | s2 |
| 80 | 8 | J | s1 | s1 |
| 80 | 13 | NJ | -- | -- |
| 80 | 14 | J | s2 | s2 |
| 80 | 19 | J | s2 | s2 |
| 160 | 7 | J | s2 | s2 |
| 160 | 8 | J | s2 | s2 |
| 160 | 14 | J | s2 | s2 |

C0_T80 EM_CONFLITO rate: 15/20 = 0.75 (theta expected: 1.0, class: plugin_defect).
C0_T160 EM_CONFLITO rate: 17/20 = 0.85.
5 seeds (T80) and 3 seeds (T160) resolved to JUSTIFICADO instead of EM_CONFLITO,
suggesting the plugin under-reports the second norm in those worlds.
Seed 13 (T80) is the only NÃO_JUSTIFICADO case: one norm was confirmed and the
other was not found.

## Checkpoint-level cost note

Checkpoint-level R_norm states (tracking when R_norm first leaves INSUFICIENTE)
were saved only for P cells as the `cost_checkpoint` column. Other worlds (X, Xp)
have empty cost columns. The checkpoint-by-checkpoint state sequence was NOT saved.
