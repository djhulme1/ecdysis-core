# Analysis (v2, seeded run)

Command: `python3 run.py` with `ECDYSIS_SEED=ab2e035f14bc20ef58bd8e4128bcd199b0dd21696519f924fd28ba95a1336b83` (the SHA-256 of "chrysalis-1 power-seeking v2 first seeded run"). One run writes everything: `results/partA.csv`, `partB.csv`, `recheck.csv`, `summary.json` and the 20 named outputs in `results/outputs.json`. Optimal values come from batched policy iteration (exact linear solves). No exact tie occurred anywhere (`exact_ties` = 0).

The v1-era run (master seed 20261002, `v1/ANALYSIS.md`) used the same constructions and estimators, so it serves below as a second, independent seed. Where the two disagree, that is said.

## Part A: Proposition 6.9's IID consequence (200 constructed instances × 5 discount rates)

All 200 instances passed the programmatic copy check (`a_copy_check_failures` = 0).

| $\gamma$ | mean $P_{opt}(a)$ | min $P_{opt}(a)$ | instances below 0.5 | min z of POWER difference |
| --- | --- | --- | --- | --- |
| 0.1 | 0.510 | 0.4915 | 32 | 8.86 |
| 0.5 | 0.559 | 0.511 | 0 | 4.35 |
| 0.9 | 0.619 | 0.510 | 0 | 1.49 |
| 0.99 | 0.628 | 0.498 | 1 | 0.13 |
| 0.999 | 0.629 | 0.496 | 1 | −0.34 |

No instance–$\gamma$ pair met the pre-registered falsifier (one-sided binomial $p<10^{-4}$ for $P_{opt}(a)<0.5$, or a POWER deficit beyond 4 SE): `a_falsifier_hits_m4000` = 0, so nothing went to the $10^5$-sample re-check and `a_falsifier_survivors` = 0. The smallest $P_{opt}(a)$ over all 1000 pairs is 0.4915 (instance 54, $\gamma = 0.1$; each estimate has standard error 0.0079, so $z = -1.1$). **Prediction A holds** on this seed, as it did on the v1 seed (minimum 0.478, $z=-2.8$, no hit). The mean rises with $\gamma$ in both; at $\gamma = 0.1$ the true values sit so close to 1/2 that about a sixth of the instances fall below it by noise (32 here, 33 in v1).

## Part B: random deterministic MDPs (1000 instances, n = 20)

"Decided": $|P_{opt}-0.5|$ with $|z|>3$ at M = 4000. "POWER-untied": $|\Delta\mathrm{POWER}| > 3$ SE. Wilson 95% intervals over instances.

| $\gamma$ | decided (of 1000) | 95% CI | $A_{POWER}$ | 95% CI | reach-untied | $A_{reach}$ | 95% CI |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.1 | 156 | [0.135, 0.180] | 0.994 (154/155) | [0.964, 0.999] | 35 | 0.771 | [0.610, 0.879] |
| 0.5 | 714 | [0.685, 0.741] | 0.993 (702/707) | [0.984, 0.997] | 138 | 0.688 | [0.607, 0.760] |
| 0.9 | 858 | [0.835, 0.878] | 0.964 (795/825) | [0.949, 0.974] | 154 | 0.701 | [0.625, 0.768] |
| 0.99 | 877 | [0.855, 0.896] | 0.942 (793/842) | [0.924, 0.956] | 158 | 0.690 | [0.614, 0.757] |
| 0.999 | 877 | [0.855, 0.896] | 0.943 (790/838) | [0.925, 0.957] | 158 | 0.690 | [0.614, 0.757] |

- **B1 (confirmed)**: $A_{POWER} > 0.8$ at $\gamma = 0.9$ and 0.99; both Wilson lower bounds (0.949 and 0.924) exceed 0.8. The v1 seed gave 0.964 [0.949, 0.974] and 0.953 [0.937, 0.965].
- **B2 (confirmed)**: 133 reversal pairs at M = 4000 (61 distinct instances: 1 at $\gamma = 0.1$, 5 at 0.5, 30 at 0.9, 49 at 0.99, 48 at 0.999). On $10^5$ fresh samples 132 were confirmed (`b_reversals_confirmed_frac` = 0.992, Wilson [0.959, 0.999]); among the confirmed the smallest $|z|$ is 4.6 and the smallest POWER gap 9.6 SE. The one that was not (instance 988, $\gamma = 0.5$): $P_{opt}$ 0.474 at M = 4000 ($z=-3.3$) but 0.4976 at $10^5$ ($z=-1.5$), i.e. a false "decided" call, which is expected now and then among several thousand calls at $|z|>3$. Reversal rate among decided, POWER-untied instances at $\gamma = 0.99$: 5.8% [4.4%, 7.6%] (v1 seed: 4.7% [3.5%, 6.3%]).
- **B3 (split, as in v1)**: $A_{reach}(0.99) = 0.690$ [0.614, 0.757]. The interval contains 0.7, so the "> 0.7" part is **inconclusive** on this seed too (v1: 0.738 [0.667, 0.799]); the point estimate has moved to the other side of 0.7, so nothing should be claimed about that threshold. The comparison part is **confirmed**: $A_{reach}$'s upper bound (0.757) is far below $A_{POWER}$'s lower bound (0.924) at $\gamma = 0.99$, and the intervals do not overlap at $\gamma$ = 0.5, 0.9 or 0.999 either (at 0.1 they do not overlap but only 35 instances are reach-untied). Reach counts were equal for 719 of 877 decided instances at 0.99 (82.0%; v1: 81.4%), so the option count says nothing for most instances.
- **B4 (confirmed)**: the decided share rises with $\gamma$: 0.156, 0.714, 0.858, 0.877 (and 0.877 at 0.999), with non-overlapping intervals for the first two steps (0.1 to 0.5 to 0.9); 0.9 to 0.99 is a small rise (0.858 to 0.877, overlapping intervals; v1: 0.874 to 0.901).

Not among the 20 outputs (descriptive, computed from `partB.csv`): on the 155 instances at $\gamma = 0.99$ where both POWER and reach are untied, POWER agrees with optimality in 87.1% [80.9, 91.5] and reach in 69.0% [61.4, 75.8] (v1: 94.0% and 74.1% on 166). The ordering holds on the common subset, but POWER's own agreement is lower there than overall: instances where reach counts differ are harder for POWER as well.

## What is stable across the two seeds, and what is not

| Quantity | v2 seeded run | v1 seed 20261002 | Verdict |
| --- | --- | --- | --- |
| Part A falsifier hits / survivors | 0 / 0 | 0 / 0 | stable |
| $A_{POWER}(0.9)$ | 0.964 | 0.964 | stable |
| $A_{POWER}(0.99)$ | 0.942 | 0.953 | stable (lower bounds 0.924, 0.937; both far above 0.8) |
| reversal pairs found | 133 | 115 | same order; varies with seed |
| reversals confirmed | 132 of 133 | 115 of 115 | "every reversal confirmed" is **not** seed-stable; "at least 95%" is |
| $A_{reach}(0.99)$ | 0.690 | 0.738 | point estimate straddles 0.7: not stable; $A_{reach} < A_{POWER}$ is |
| decided share, $\gamma$ 0.1 → 0.99 | 0.156 → 0.877 | 0.146 → 0.901 | stable |
| policy vs value iteration, max difference | $1.13\times10^{-10}$ | $1.1\times10^{-10}$ | stable |

Every difference between the two seeds is inside the tolerance declared for that output in `bundle.json`.

Consequences for the draft: the v1 wording "all reversals were confirmed" must become a bound (for example, at least 95% confirmed); nothing may be claimed about $A_{reach}$ against 0.7; and claims should be bounds that any seed can test from `outputs.json`.

## Deviations from the plan

1. The plan text contains an in-line "Wait:" note written while pre-registering, clarifying that $a$'s successor is the copy's entry state and that extra options are added as extra edges. The code implements that clarified construction.
2. Agreement rates are computed only over decided and POWER-untied (or reach-untied) instances, as planned; this conditioning is a selection, and the undecided share is reported alongside (84.4% undecided at $\gamma = 0.1$).
3. The plan specified value iteration; the code computes optimal values by exact policy iteration (batched linear solves). The cross-check against 40,000 sweeps of plain value iteration is now part of the run (Part B instances 0 to 3, 200 reward samples each): largest absolute difference $2.2\times10^{-16}$, $4.4\times10^{-16}$, $1.6\times10^{-14}$, $1.4\times10^{-12}$ and $1.13\times10^{-10}$ at $\gamma$ = 0.1, 0.5, 0.9, 0.99, 0.999 (`vi_max_abs_diff`).
4. The plan fixed the master seed 20261002. Under the v2 standard the seed comes from `ECDYSIS_SEED`; 20261002 remains the default. The estimators, thresholds and sample sizes are unchanged; the v1 `analyse.py`, fed this run's CSVs, returns the same counts and intervals.
5. The plan's compute split (re-checks in a second run) is now one run of about 16 minutes. The Part A re-check at $10^5$ samples is implemented but was not triggered.
6. The $10^5$-sample re-checks use fresh reward samples (salts 1 to 5), as planned.

## Limits

One graph model (out-degree U{1,2,3}, n = 20), IID U[0,1] state rewards, deterministic transitions, exact optimal (not learned) policies. "Decided" depends on M; the B1–B4 numbers are conditional on that threshold, and a call at $|z|>3$ is occasionally wrong (one seen). Part A's 200 constructions sample a narrow family satisfying the condition; at 4000 samples the falsifier is a weak test, a numerical consistency check of a proved result that could detect only a gross gap. $\gamma = 0.99$ and 0.999 give nearly identical tables, as expected when the optimal policy is constant for $\gamma$ near 1 (Blackwell optimality). The reading of reversals as a skewed value difference (mean and median of opposite sign) in `v1/ANALYSIS.md` is descriptive and was not pre-registered.
