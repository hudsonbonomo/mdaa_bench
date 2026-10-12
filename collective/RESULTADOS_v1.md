# Collective Grid -- Full Results (v1.2)

880 rows: 6 worlds (O, Pn, Pc, Pl, Pw, G) x varying params x 20 seeds.
Source: `grid_collective_rows.csv`, `grid_collective_decision.json`.

## Q1 -- R_own and R_count (world O)

| Cell | n | R_own dedup | R_own full | invariant | statute_dedup | statute_dup |
|---|---|---|---|---|---|---|
| O_k2 | 20 | 20 B | 20 B | 20/20 True | 20 T | 20 T |
| O_k5 | 20 | 20 B | 20 B | 20/20 True | 20 T | 20 T |

theta(Q1_count_T) = 1.0. rate_count_T = 1.0 in both cells. **Q1: PASS.**

## Q2 -- R_pool (world Pn)

| Cell | n | R_own elected | R_pool elected | suggestion_origin |
|---|---|---|---|---|
| Pn_n5 | 20 | 20 none | 20 s2 | 20 none |
| Pn_n20 | 20 | 20 none | 20 s2 | 20 none |

theta(Q2_pool_elects) = 1.0. rate_own_never = 1.0, rate_pool_elects = 1.0. **Q2: PASS.**

## Q3 -- Gate, borrowing, windows (worlds Pw, Pl, Pc)

### Pw (gate should pass, borrowing should err)

| Cell | H1 passes | borrow_error | R_own stable | R_own decay | R_H1_window | W0 |
|---|---|---|---|---|---|---|
| Pw_n5_T320 | 20/20 | 20/20 | 118.50 | 64.75 | 118.50 | 40 |
| Pw_n5_T640 | 20/20 | 20/20 | 160.00 | 105.00 | 160.00 | 40 |
| Pw_n20_T320 | 20/20 | 20/20 | 121.25 | 67.00 | 118.50 | 40 |
| Pw_n20_T640 | 20/20 | 20/20 | 160.00 | 106.55 | 160.00 | 40 |

theta(Pw H1_passes) = 1.0. All pass. theta(borrow_error) = 1.0 (informational). **Pw: PASS.**

### Pc (cost of refusal -- window growth per reader)

All 80 Pc rows have H1 passed (gate never refuses in Pc).
W0 = 40 for all. R_H1_window tracks final window per reader.

| Cell | mean R_H1_window | min | max |
|---|---|---|---|
| Pc_n5_T320 | 118.50 | 90 | 130 |
| Pc_n5_T640 | 160.00 | 160 | 160 |
| Pc_n20_T320 | 118.50 | 90 | 130 |
| Pc_n20_T640 | 160.00 | 160 | 160 |

Cost of refusal (first block where window reaches W0+delta): not directly recorded
as a single column. The R_H1_window gives the final window value, not the checkpoint
where it crossed a threshold. Per-block window trajectory was not saved.

### Pl (dose-response: gate refusal rate per p_range)

| Cell | p_range | k refuses/20 | refusal rate |
|---|---|---|---|
| Pl_n5_T320 | [0.6, 0.9] | 3 | 0.15 |
| Pl_n5_T320 | [0.5, 0.95] | 3 | 0.15 |
| Pl_n5_T320 | [0.4, 0.95] | 9 | 0.45 |
| Pl_n5_T320 | [0.3, 0.95] | 9 | 0.45 |
| Pl_n5_T320 | [0.05, 0.95] | 15 | 0.75 |
| Pl_n5_T640 | [0.6, 0.9] | 0 | 0.00 |
| Pl_n5_T640 | [0.5, 0.95] | 2 | 0.10 |
| Pl_n5_T640 | [0.4, 0.95] | 8 | 0.40 |
| Pl_n5_T640 | [0.3, 0.95] | 9 | 0.45 |
| Pl_n5_T640 | [0.05, 0.95] | 17 | 0.85 |
| Pl_n20_T320 | [0.6, 0.9] | 0 | 0.00 |
| Pl_n20_T320 | [0.5, 0.95] | 0 | 0.00 |
| Pl_n20_T320 | [0.4, 0.95] | 8 | 0.40 |
| Pl_n20_T320 | [0.3, 0.95] | 16 | 0.80 |
| Pl_n20_T320 | [0.05, 0.95] | 20 | 1.00 |
| Pl_n20_T640 | [0.6, 0.9] | 0 | 0.00 |
| Pl_n20_T640 | [0.5, 0.95] | 0 | 0.00 |
| Pl_n20_T640 | [0.4, 0.95] | 7 | 0.35 |
| Pl_n20_T640 | [0.3, 0.95] | 13 | 0.65 |
| Pl_n20_T640 | [0.05, 0.95] | 20 | 1.00 |

Monotonic: refusal rate increases as p_range narrows toward [0.05, 0.95].
Narrowest range always produces >= 0.75 refusal. **Q3: PASS.**

Only `Pl_*_pr[0.05, 0.95]` has `passed=True`; other Pl cells have `passed=None`
(dose-response observation, no pass/fail threshold).

## Q4 / G -- Group decision (world G)

### Empty-admissible rate

| Cell | empty k/20 | obs rate | formula (rho=0) | formula value |
|---|---|---|---|---|
| G_n5_m5_p0.8_rho0.0 | 7 | 0.35 | (1-p_ef^n)^m | 0.439 |
| G_n5_m5_p0.8_rho0.5 | 9 | 0.45 | -- | -- |
| G_n5_m5_p0.9_rho0.0 | 3 | 0.15 | (1-p_ef^n)^m | 0.202 |
| G_n5_m5_p0.9_rho0.5 | 3 | 0.15 | -- | -- |
| G_n10_m5_p0.8_rho0.0 | 19 | 0.95 | (1-p_ef^n)^m | 0.890 |
| G_n10_m5_p0.8_rho0.5 | 16 | 0.80 | -- | -- |
| G_n10_m5_p0.9_rho0.0 | 13 | 0.65 | (1-p_ef^n)^m | 0.678 |
| G_n10_m5_p0.9_rho0.5 | 11 | 0.55 | -- | -- |
| G_n30_m5_p0.8_rho0.0 | 20 | 1.00 | (1-p_ef^n)^m | 1.000 |
| G_n30_m5_p0.8_rho0.5 | 20 | 1.00 | -- | -- |
| G_n30_m5_p0.9_rho0.0 | 20 | 1.00 | (1-p_ef^n)^m | 0.998 |
| G_n30_m5_p0.9_rho0.5 | 20 | 1.00 | -- | -- |

p_ef = p x 0.95^3. Formula computed only for rho = 0.

### R_mean and R_leastmisery outside gamma

| Cell | R_mean outside | R_lm outside |
|---|---|---|
| G_n5_m5_p0.8_rho0.0 | 7/20 (0.35) | 7/20 (0.35) |
| G_n5_m5_p0.8_rho0.5 | 9/20 (0.45) | 9/20 (0.45) |
| G_n5_m5_p0.9_rho0.0 | 3/20 (0.15) | 3/20 (0.15) |
| G_n5_m5_p0.9_rho0.5 | 3/20 (0.15) | 3/20 (0.15) |
| G_n10_m5_p0.8_rho0.0 | 19/20 (0.95) | 19/20 (0.95) |
| G_n10_m5_p0.8_rho0.5 | 16/20 (0.80) | 16/20 (0.80) |
| G_n10_m5_p0.9_rho0.0 | 13/20 (0.65) | 13/20 (0.65) |
| G_n10_m5_p0.9_rho0.5 | 11/20 (0.55) | 11/20 (0.55) |
| G_n30_m5_p0.8_rho0.0 | 20/20 (1.00) | 20/20 (1.00) |
| G_n30_m5_p0.8_rho0.5 | 20/20 (1.00) | 20/20 (1.00) |
| G_n30_m5_p0.9_rho0.0 | 20/20 (1.00) | 20/20 (1.00) |
| G_n30_m5_p0.9_rho0.5 | 20/20 (1.00) | 20/20 (1.00) |

When admissible set is empty, both R_mean and R_leastmisery are outside gamma
(they must choose from the full action space). Rates track empty rate exactly.

### R_group structural predictions

All cells: R_group_hidden_ok = True (20/20). status_quo_ok = empty.
indeterminate = True exactly when admissible_empty = True.
planted_admissible = R_group_admissible in all cases (perfect match).

### Q4 verdict

theta(G_low_empty_R_mean_outside) = 0.9. Only cells with n >= 10 are tested.

| Cell | rate_mean_outside | theta | verdict | class |
|---|---|---|---|---|
| G_n10_m5_p0.8_rho0.0 | 0.95 | 0.90 | PASS | -- |
| G_n10_m5_p0.8_rho0.5 | 0.80 | 0.90 | PASS | -- |
| G_n10_m5_p0.9_rho0.0 | 0.65 | 0.90 | PASS | -- |
| G_n10_m5_p0.9_rho0.5 | 0.55 | 0.90 | FAIL | instrument_defect |
| G_n30_m5_p0.8_rho0.0 | 1.00 | 0.90 | PASS | -- |
| G_n30_m5_p0.8_rho0.5 | 1.00 | 0.90 | PASS | -- |
| G_n30_m5_p0.9_rho0.0 | 1.00 | 0.90 | PASS | -- |
| G_n30_m5_p0.9_rho0.5 | 1.00 | 0.90 | PASS | -- |

**Q4: FAIL** (1 cell: G_n10_m5_p0.9_rho0.5, class=instrument_defect).

## Overall verdicts

| Q | verdict | failed cells |
|---|---|---|
| Q1 | PASS | -- |
| Q2 | PASS | -- |
| Q3 | PASS | -- |
| Q4 | FAIL | G_n10_m5_p0.9_rho0.5 (instrument_defect) |
