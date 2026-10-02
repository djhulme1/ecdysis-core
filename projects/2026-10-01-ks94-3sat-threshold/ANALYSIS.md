# Analysis (v2 bundle): A1–A5 as pre-registered, on freshly seeded data

Run: `ECDYSIS_SEED=2df72687f12ef8d7afd74dbec44cfbb27e6a4aaa72f0f0aa7f630999ec67df87 python3 run.py` at commit efb557c (about 16 minutes on one CPU). 82,800 random 3-CNF formulas per instance model, every one decided by MiniSat 2.2. Everything below is in `results/analysis.json`; the 20 headline outputs are in `results/outputs.json`.

Two instance models: **dup** (clauses drawn independently, duplicates possible: the pre-registered model) and **nodup** (no clause repeated within a formula: added at the v1 review, not pre-registered, because the parent does not say which it used).

Uncertainty: bootstrap by binomial resampling of each grid point at its observed fraction (300 resamples for A1/A4, 100 for each collapse), reported as standard errors (SE) and 95% percentile intervals. This measures what a new seed would change. It does not measure model error: see "Goodness of fit".

## A1: per-N 50% point and 10–90% width
| N | $\alpha_{50}$ dup [95%] | width dup | $\alpha_{50}$ nodup [95%] | width nodup | KS law $4.17+3.1N^{-2/3}$ | obs − KS (dup / nodup) |
|---|---|---|---|---|---|---|
| 12 | 4.935 [4.908, 4.958] | 2.31 | 4.862 [4.840, 4.884] | 2.25 | 4.761 | +0.173 / +0.101 |
| 20 | 4.663 [4.644, 4.682] | 1.68 | 4.647 [4.627, 4.666] | 1.64 | 4.591 | +0.072 / +0.056 |
| 24 | 4.578 [4.559, 4.596] | 1.47 | 4.561 [4.541, 4.579] | 1.43 | 4.543 | +0.035 / +0.018 |
| 40 | 4.436 [4.417, 4.450] | 1.06 | 4.440 [4.423, 4.454] | 1.04 | 4.435 | +0.000 / +0.005 |
| 50 | 4.396 [4.383, 4.410] | 0.90 | 4.380 [4.365, 4.394] | 0.87 | 4.398 | −0.003 / −0.019 |
| 100 | 4.301 [4.291, 4.312] | 0.56 | 4.314 [4.303, 4.325] | 0.55 | 4.314 | −0.012 / +0.000 |
| 150 | 4.287 [4.277, 4.296] | 0.44 | 4.280 [4.271, 4.290] | 0.43 | 4.280 | +0.007 / +0.001 |
| 200 | 4.278 [4.269, 4.285] | 0.33 | 4.277 [4.269, 4.286] | 0.34 | 4.261 | +0.017 / +0.017 |

## A2: collapse on N = 12–100 (the parent's own range)
| | dup | nodup |
|---|---|---|
| $\alpha_c$ (SE) [95%] | 4.098 (0.009) [4.080, 4.112] | 4.126 (0.009) [4.109, 4.146] |
| $\nu$ (SE) [95%] | 1.471 (0.023) [1.429, 1.515] | 1.489 (0.028) [1.441, 1.543] |
| $y_{50}$ | 1.06 | 0.92 |
| dispersion φ (residual deviance / 182 df) | 3.53 | 3.13 |
| deviance with $\alpha_c$ fixed at 4.17, raw (÷φ) | 64.7 (18.3) | 23.4 (7.5) |
| deviance of the parent's triple (4.17, 1.5, 0.74), raw (÷φ) | 258.7 (73.4) | 98.1 (31.3) |

## A3: collapse on N ∈ {50, 100, 150, 200}
| | dup | nodup |
|---|---|---|
| $\alpha_c$ (SE) [95%] | 4.201 (0.008) [4.188, 4.216] | 4.203 (0.009) [4.185, 4.216] |
| $\nu$ (SE) [95%] | 1.440 (0.049) [1.369, 1.544] | 1.508 (0.051) [1.414, 1.612] |
| φ | 1.98 | 1.84 |
| deviance at $\alpha_c$ = 4.17 ÷ φ | 5.8 | 6.4 |

## A4: effective exponent from the width, N = 50–200
$\nu_{eff}$ = 1.44 (SE 0.05) [1.34, 1.54] dup; 1.50 (SE 0.05) [1.41, 1.61] nodup.

## A5: the parent's 50% law out of sample
N = 150: +0.007 (dup), +0.001 (nodup). N = 200: +0.017, +0.017. SE of each $\alpha_{50}$: 0.005. Crawford–Auton's $4.24 + 6/N$ misses by +0.007 / +0.000 at N = 150 and +0.008 / +0.007 at N = 200: as close or closer, so this check cannot separate the two laws.

## Verdicts on the pre-registered predictions (this seed)
- **P1 (replication): $\nu$ holds, $\alpha_c$ depends on the instance model.** $\nu$'s interval overlaps 1.5 ± 0.1 in both arms. $\alpha_c$'s interval lies wholly below 4.17 ± 0.05 = [4.12, 4.22] in the pre-registered dup model ([4.080, 4.112]), and overlaps it without duplicates ([4.109, 4.146]). So the pre-registered test falsifies the $\alpha_c$ half of P1, but that verdict does not survive the change of instance model, and the parent does not state its model. No "refutes".
- **P2 (drift above 4.22): falsified.** The fitted $\alpha_c$ rises with the N range (4.10 → 4.20 dup, 4.13 → 4.20 nodup), but both A3 intervals stay below 4.22.
- **P3 (the 50% law predicts N = 150, 200 within 0.03): holds** in both arms (largest miss +0.017).
- **P4 ($\nu_{eff}$ in [1.3, 1.9]): holds** in both arms.

## Seed-to-seed check: two independent samples so far
The v1 data (fixed seeds, in `v1/results/`) are an independent sample of the same grid. The v2 analysis code, fed those counts, returns the v1 numbers exactly. Side by side:

| output | v1 sample dup / nodup | this seed dup / nodup | largest difference | tolerance in bundle.json |
|---|---|---|---|---|
| $\alpha_c$, N 12–100 | 4.076 / 4.115 | 4.098 / 4.126 | 0.021 | 0.05 |
| $\nu$, N 12–100 | 1.519 / 1.517 | 1.471 / 1.489 | 0.048 | 0.14 |
| φ, N 12–100 | 3.41 / 3.30 | 3.53 / 3.13 | 0.16 | 1.3 |
| $\alpha_c$, N 50–200 | 4.198 / 4.190 | 4.201 / 4.203 | 0.012 | 0.045 |
| $\nu_{eff}$ | 1.424 / 1.464 | 1.438 / 1.503 | 0.038 | 0.25 |
| 50% law miss, N = 150 | +0.013 / +0.002 | +0.007 / +0.001 | 0.006 | 0.025 |
| 50% law miss, N = 200 | +0.010 / +0.009 | +0.017 / +0.017 | 0.008 | 0.025 |

Tolerances are about five bootstrap SEs (two independent runs differ by $\sqrt 2$ SE, so this is about 3.5 standard deviations of the difference). Every difference observed is well inside. A third seed is run at the ready stage.

What is stable across samples and so fit to be claimed: $\nu$ on N = 12–100 inside 1.5 ± 0.1 under both models; the fitted $\alpha_c$ on N = 12–100 below the parent's point value 4.17 under both models (4.08 to 4.13 in four fits, SE 0.009) and about 0.03 to 0.04 lower with duplicates than without; $\alpha_c$ on N = 50–200 near 4.20 under both; the 50% law within 0.03 at N = 150, 200; $\nu_{eff}$ about 1.4 to 1.5, below 2.

What is not stable and must not be claimed:
- **"The 50% law holds to 0.015"** (the v1 draft's wording). Under this seed the miss at N = 200 is 0.017 in both arms. The pre-registered 0.03 stands; 0.015 was fitted to one sample.
- **"4.17 lies outside the overdispersion-corrected interval under both models."** Without duplicates the corrected deviance at 4.17 was 10.7 in the v1 sample and is 7.5 here, against a threshold of 3.84. It cleared both times, but a statistic that moves by 3 between seeds with a margin of 4 to 7 will fail under some seeds. The v2 draft should claim the point estimates, with their SE, and not this test.

## Goodness of fit
One logistic scaling function with one $\alpha_c$ does not fit N = 12–100: φ is 3.5 (dup) and 3.1 (nodup) where a correct model gives about 1. So the collapse parameters are effective, range-dependent summaries, not estimates of an asymptotic threshold: $\alpha_c$ moves from about 4.1 to 4.2 when the N range moves from 12–100 to 50–200, still below the cavity value near 4.267 (mentioned as background; not tested here). The bootstrap SEs describe seed-to-seed variation of this fitting procedure, and say nothing about how far another reasonable procedure (the parent fitted by eye) would land.

## Deviations from the plan
1. **Seeded re-run for v2.** The plan derived instance seeds from (N, α index, sample). The bundle derives them from `ECDYSIS_SEED` as well, so the data here are new, and were generated after the v1 results had been seen. Grid, instance model, solver and analyses are unchanged; the verdicts above are therefore a second, non-blind sample of the same pre-registered tests, and they agree with the first.
2. **Duplicate-free arm**: not pre-registered; added after the first v1 review. Reported beside the pre-registered arm throughout.
3. **Bootstrap sizes**: 300 resamples for A1/A4 and 100 per collapse, where the plan said 1000, to keep the bundle near 16 minutes. Each SE therefore carries a Monte Carlo error of its own of about 4% (A1/A4) and 7% (collapses).
4. **Arithmetic slip in PLAN.md**: it gives the parent's law as 4.229 at N = 150; the formula gives 4.280. Tests use the formula.
5. **Clock**: the v1 run recorded solver wall time; the bundle never reads the clock, so timing is no longer an output.
6. **Crawford–Auton's law** is quoted from the parent and was not opened separately; it is a reference curve only.
