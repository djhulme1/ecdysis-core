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
- Clauses were drawn independently (duplicates allowed); KS do not say whether they excluded duplicate clauses. At N ≥ 50 duplicates are rare (expected number of duplicate pairs ≈ $M^2/(2\cdot 8\binom{N}{3})$ ≈ 0.6 at N = 50, α = 4.4) and should not move $\alpha_{50}$ appreciably; not tested.

## Deviations from the plan
1. Arithmetic slip in PLAN.md: it listed KS's formula as 4.229 at N = 150; the correct value is 4.280 (and CA's 4.280). The test uses the formula itself, as stated, so the verdicts are unaffected. N = 200 values (4.261, 4.270) were correct.
2. Collapse bootstraps used 200 resamples (not 1000) for time, each started from the point estimate; A1/A4 used 1000 as planned.
3. A2/A3 point estimates used three Nelder–Mead starts; all converged to the reported optimum.
