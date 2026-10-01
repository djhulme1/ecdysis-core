# Analysis (A1–A5 as pre-registered)

Data: results/counts.csv (82,800 instances, MiniSat 2.2, all decided; 254 s of solver wall time on 2 cores). Code: analyse.py -> results/analysis.json. 95% intervals: parametric bootstrap (1000 resamples for A1/A4, 200 for the collapse fits A2/A3).

## A1: per-N 50% point and 10–90% width
| N | $\alpha_{50}$ [95% CI] | width [95% CI] | KS $4.17+3.1N^{-2/3}$ | C&A $4.24+6/N$ |
|---|---|---|---|---|
| 12 | 4.935 [4.912, 4.961] | 2.26 [2.19, 2.34] | 4.761 | 4.740 |
| 20 | 4.670 [4.650, 4.690] | 1.67 [1.62, 1.72] | 4.591 | 4.540 |
| 24 | 4.595 [4.576, 4.613] | 1.51 [1.46, 1.55] | 4.543 | 4.490 |
| 40 | 4.432 [4.417, 4.447] | 1.08 [1.05, 1.12] | 4.435 | 4.390 |
| 50 | 4.392 [4.378, 4.405] | 0.89 [0.85, 0.92] | 4.398 | 4.360 |
| 100 | 4.298 [4.287, 4.309] | 0.58 [0.55, 0.60] | 4.314 | 4.300 |
| 150 | 4.292 [4.283, 4.302] | 0.43 [0.41, 0.46] | 4.280 | 4.280 |
| 200 | 4.271 [4.263, 4.280] | 0.33 [0.31, 0.35] | 4.261 | 4.270 |

## A2: collapse on N ≤ 100 (KS's own range)
$\alpha_c$ = 4.076 [4.056, 4.095]; $\nu$ = 1.519 [1.458, 1.567]; $y_{50}$ = 1.05, s = 0.67.

## A3: collapse on N ∈ {50, 100, 150, 200}
$\alpha_c$ = 4.198 [4.186, 4.214]; $\nu$ = 1.449 [1.361, 1.545]; $y_{50}$ = 0.66.

## A4: effective exponent from width scaling, N = 50–200
slope of log w on log N = −0.702; $\nu_{eff}$ = 1.42 [1.34, 1.51].

## A5: out-of-sample 50% points
N = 150: observed − KS = +0.013, observed − C&A = +0.012. N = 200: observed − KS = +0.010, observed − C&A = +0.001.

## Verdicts on the predictions
- **P1 (replication): partly falsified.** $\nu$ replicates (1.52, inside 1.5 ± 0.1). $\alpha_c$ does not: under the pre-registered collapse model on KS's own N range, the interval [4.056, 4.095] lies wholly below 4.17 ± 0.05.
- **P2 (drift above 4.22): falsified.** The fitted $\alpha_c$ does drift upwards when larger N are used (4.08 → 4.20), but A3's interval [4.186, 4.214] stays below 4.22.
- **P3 (KS's $\alpha_{50}$ law predicts N = 150, 200 within 0.03): holds** (+0.013, +0.010). Note KS's law misses badly at the smallest N (N = 12: +0.17), where it was presumably not fitted to $\alpha_{50}$ directly.
- **P4 ($\nu_{eff}$ in [1.3, 1.9]): holds** (1.42 [1.34, 1.51]); at N ≤ 200 the window narrows faster than the asymptotic bound $\nu \ge 2$ (Wilson) allows, so 1.5 is an effective, pre-asymptotic exponent.

## Interpretation and caveats (to carry into the draft)
- The collapse parameters are model-dependent: $\alpha_c$, $\nu$ and $y_{50}$ trade off (a lower $\alpha_c$ is compensated by a larger $y_{50}$: 1.05 against KS's 0.74). KS fitted by eye ("the range of each parameter over which the best fits were obtained"); we fit by maximum likelihood with a logistic scaling function. So the refutation of $\alpha_c$ = 4.17 is a refutation within this fitting procedure, and the honest statement is that the data do not single out 4.17: the fitted $\alpha_c$ moves with the N range (4.08 on 12–100, 4.20 on 50–200), consistent with a pre-asymptotic drift towards the cavity value ≈ 4.267.
- The observable, procedure-free quantities ($\alpha_{50}(N)$, widths) are consistent with KS's 50% law at N ≥ 40 within about 0.015.
- Clauses were drawn independently (duplicates allowed); KS do not say whether they excluded duplicate clauses. At N ≥ 50 duplicates are rare (expected number of duplicate pairs ≈ $M^2/(2\cdot 8\binom{N}{3})$ ≈ 0.15 at N = 50, α = 4.4; corrected at review, the earlier figure 0.6 was an arithmetic error). Not rare at N = 12–24, which drive A2: see the post-review duplicate-free arm (run_nodup.py, counts_nodup.csv) and sensitivity.py.

## Deviations from the plan
1. Arithmetic slip in PLAN.md: it listed KS's formula as 4.229 at N = 150; the correct value is 4.280 (and CA's 4.280). The test uses the formula itself, as stated, so the verdicts are unaffected. N = 200 values (4.261, 4.270) were correct.
2. Collapse bootstraps used 200 resamples (not 1000) for time, each started from the point estimate; A1/A4 used 1000 as planned.
3. A2/A3 point estimates take the best of three Nelder–Mead starts (convergence of the other starts not checked; to verify at drafting).

## Drafting-stage checks (exploratory, not pre-registered): check_fit.py -> results/check_fit.json, results/check_fit.log
Added 2026-10-01 at drafting, to close deviation 3 and to test how much the $\alpha_c$ verdict depends on the fit.
- **Convergence.** A2 and A3 refitted from 72 starts each ($\alpha_c$ ∈ {4.0, 4.17, 4.27} × $\nu$ ∈ {1.2, 1.5, 2.0, 2.6} × $y_{50}$ ∈ {0.3, 0.7, 1.2} × s ∈ {0.3, 0.7}). All 72 reach the same optimum (to within 1e-3 in log-likelihood; $\alpha_c$ spread < 1e-7). Deviation 3 is closed.
- **Goodness of fit.** The single-logistic collapse is misspecified: residual deviance 621.0 on 182 df for N ≤ 100 (dispersion φ = 3.41) and 212.8 on 100 df for N = 50–200 (φ = 2.13). So the parametric-bootstrap intervals in A2/A3 are too narrow.
- **Overdispersion-corrected profile intervals for $\alpha_c$** (profile deviance / φ ≤ 3.84, grid step 0.005): N ≤ 100: [4.04, 4.11]; N = 50–200: [4.175, 4.22]. At $\alpha_c$ = 4.17 the corrected deviance is 29.6 (N ≤ 100) and 4.5 (N = 50–200).
- **KS's published triple** ($\alpha_c$ 4.17, $\nu$ 1.5, $y_{50}$ 0.74, only the scale fitted): deviance 301.8 worse than the best fit on N ≤ 100; 10.4 worse on N = 50–200.
- Consequence for the verdicts: the P1 verdict on $\alpha_c$ survives the overdispersion correction on KS's own N range. On N = 50–200, KS's value lies at the edge of the corrected interval. The model misfit is itself a finding: one logistic scaling function with one $\alpha_c$ does not describe N = 12–100, so "$\alpha_c$" from such a collapse is an effective, range-dependent parameter.

## Post-review sensitivity analysis (exploratory, not pre-registered): instance model
Added 2026-10-01 after juror 1. run_nodup.py -> results/counts_nodup.csv (same grid, same solver, new seeds, no duplicate clauses within a formula); sensitivity.py -> results/sensitivity_with_duplicates.json and results/sensitivity_no_duplicates.json (+ .log). Profile intervals are quasi-likelihood (profile deviance / φ ≤ 3.84) on a grid of step 0.01 for $\alpha_c$ and 0.02 for $\nu$, so endpoints are resolved to the grid step; A1 intervals here use 300 bootstrap resamples. The with-duplicates rows reproduce the earlier A2/A3 and check_fit numbers (4.0762, 1.5194, deviance 621.0, φ 3.41, deviance at 4.17 = 101.0, KS triple 301.8).

| | with duplicates | no duplicates |
|---|---|---|
| A2 (N 12–100) $\alpha_c$ [corrected 95%] | 4.076 [4.04, 4.11] | 4.115 [4.08, 4.14] |
| A2 $\nu$ [corrected 95%] | 1.519 [1.44, 1.62] | 1.517 [1.44, 1.62] |
| A2 $y_{50}$; φ | 1.05; 3.41 | 0.91; 3.30 |
| A2 deviance at $\alpha_c$ = 4.17, raw (÷φ) | 101.0 (29.6) | 35.4 (10.7) |
| A2 KS triple 4.17/1.5/0.74, raw (÷φ) | 301.8 (88.4) | 97.8 (29.7) |
| A3 (N 50–200) $\alpha_c$ [corrected 95%] | 4.198 [4.18, 4.22] | 4.190 [4.17, 4.21] |
| A3 $\nu$ [corrected 95%] | 1.449 [1.34, 1.60] | 1.451 [1.34, 1.58] |
| A3 deviance ÷φ at 4.17 | 4.5 | 2.7 |
| A4 $\nu_{eff}$ (N 50–200) | 1.42 | 1.46 |
| A5 obs − KS law, N = 150 / 200 | +0.013 / +0.010 | +0.002 / +0.009 |
| $\alpha_{50}$ at N = 12 / 150 / 200 | 4.935 / 4.292 / 4.271 | 4.859 / 4.282 / 4.269 |

Consequences for the draft:
- The P1 verdict on $\alpha_c$ ("wholly below 4.17 ± 0.05") holds with duplicates allowed but NOT without them: the duplicate-free corrected interval [4.08, 4.14] overlaps KS's range [4.12, 4.22]. KS do not state their instance model, so the "refutes" relation is withdrawn. What survives under both models: the point value 4.17 itself lies outside the corrected 95% interval on KS's N range (deviance ÷ φ 29.6 and 10.7, both > 3.84), and KS's published triple fits far worse than the best collapse.
- $\nu$, the drift of the fitted $\alpha_c$ with N range, the 50% law at N = 150, 200 and $\nu_{eff}$ are robust to the instance model.
- Duplicate clauses mainly move the smallest sizes ($\alpha_{50}$ at N = 12 falls by 0.08 without them), which is where the A2 collapse gets its leverage.
