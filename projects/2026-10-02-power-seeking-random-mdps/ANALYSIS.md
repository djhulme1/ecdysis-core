# Analysis

Commands: `python3 run.py` (Part A, Part B at M = 4000), `python3 analyse.py` (writes `results/summary.json`), `python3 recheck.py` (re-checks every Part B reversal with $10^5$ fresh reward samples, writes `results/recheck.csv`). All seeds derive from 20261002. Exact optimal values come from batched policy iteration (exact linear solves); against 40,000 sweeps of value iteration the maximum absolute difference was $4\times10^{-16}$ ($\gamma=0.5$), $1.4\times10^{-12}$ (0.99) and $1.1\times10^{-10}$ (0.999). No exact ties occurred anywhere.

## Part A: reproduction of Proposition 6.9's IID consequence (200 constructed instances × 5 discount rates)

All 200 instances passed the programmatic copy check (no return to the start; each copied state's successors contain the image of the original's).

| $\gamma$ | mean $P_{opt}(a)$ | min $P_{opt}(a)$ | instances below 0.5 | min z of POWER difference |
| --- | --- | --- | --- | --- |
| 0.1 | 0.510 | 0.478 | 33 | 9.97 |
| 0.5 | 0.555 | 0.503 | 0 | 4.49 |
| 0.9 | 0.612 | 0.496 | 1 | 0.79 |
| 0.99 | 0.624 | 0.501 | 0 | −0.16 |
| 0.999 | 0.625 | 0.500 | 0 | −0.26 |

No instance–$\gamma$ pair met the pre-registered falsifier (one-sided binomial $p<10^{-4}$ for $P_{opt}(a)<0.5$, or a POWER deficit beyond 4 SE), so no $10^5$-sample re-check was triggered. The smallest value, 0.478 at $\gamma = 0.1$, is $z = -2.8$ (one-sided $p\approx 0.003$, one of 1000 pairs): consistent with Monte Carlo noise around a true value at or just above 0.5. **Prediction A holds.** At $\gamma\to1$ the two successors' POWER can coincide (the small negative z values), as expected when the extra states add no better long-run cycle.

## Part B: random deterministic MDPs (1000 instances, n = 20)

"Decided": $|P_{opt}-0.5|$ with $z>3$ at M = 4000. "POWER-untied": $|\Delta\mathrm{POWER}| > 3$ SE. Wilson 95% intervals.

| $\gamma$ | decided (of 1000) | $A_{POWER}$ | 95% CI | reach-untied | $A_{reach}$ | 95% CI |
| --- | --- | --- | --- | --- | --- | --- |
| 0.1 | 146 | 1.000 (145/145) | [0.974, 1.000] | 34 | 0.765 | [0.600, 0.876] |
| 0.5 | 727 | 0.997 (722/724) | [0.990, 0.999] | 142 | 0.768 | [0.692, 0.830] |
| 0.9 | 874 | 0.964 (820/851) | [0.949, 0.974] | 164 | 0.750 | [0.679, 0.810] |
| 0.99 | 901 | 0.953 (836/877) | [0.937, 0.965] | 168 | 0.738 | [0.667, 0.799] |
| 0.999 | 903 | 0.953 (836/877) | [0.937, 0.965] | 168 | 0.738 | [0.667, 0.799] |

- **B1 (confirmed)**: $A_{POWER} > 0.8$ at $\gamma = 0.9$ and 0.99; both Wilson lower bounds (0.949, 0.937) exceed 0.8.
- **B2 (confirmed)**: all 115 reversal pairs found at M = 4000 (48 distinct instances: 2 at $\gamma=0.5$, 31 at 0.9, 41 at 0.99, 41 at 0.999) were confirmed on $10^5$ fresh samples; every one kept $|z|>3$ (smallest $|z| = 7.4$; all rows in `results/recheck.csv`) and a POWER difference beyond 3 SE (smallest 8.4 SE) with the opposite sign. Reversal rate among decided, POWER-untied instances: 4.7% [3.5%, 6.3%] at $\gamma = 0.99$.
- **B3 (split)**: $A_{reach}(0.99) = 0.738$ [0.667, 0.799]. The pre-registered confirmation needed the lower bound above 0.7 and the falsification needed the upper bound below 0.7: neither, so the "> 0.7" part is **inconclusive**. The comparison part is **confirmed**: $A_{reach}$ < $A_{POWER}$ with non-overlapping intervals at every $\gamma$. Reach counts were equal for 733 of 901 decided instances at 0.99 (most states reach the same large component), so the option count is uninformative for most instances.
- **B4 (confirmed)**: the decided fraction rises monotonically: 0.146 [0.126, 0.169], 0.727, 0.874, 0.901, 0.903.

$\gamma = 0.99$ and 0.999 give identical agreement tables. This is expected: for small deterministic MDPs the optimal policy is constant for $\gamma$ near 1 (Blackwell optimality), so most per-instance orderings do not change between them.

## Reading of the reversals (descriptive, not pre-registered)

A reversal means the expected (net) optimal value of one successor is higher (higher POWER) while the other successor is more often the better one: the mean and the median of the value difference have opposite signs, i.e. the difference is skewed. Example, instance 61 ($\gamma=0.9$): successor 13 offers an immediate choice between a self-loop state and another branch and reaches 6 states; successor 8 is forced into state 5 and then a larger region of 11 states. Action → 13 is optimal with probability 0.537 ($10^5$ samples), yet successor 8 has higher POWER (difference −0.0306, SE 0.00045, sign reversed). POWER-seeking and optimality probability are distinct quantities; Turner et al.'s theorems order both under their symmetry condition, and here they come apart only when it fails.

## Deviations from the plan

1. The plan text contains an in-line "Wait:" note written while pre-registering, clarifying that $a$'s successor is the copy's entry state and that extra options are added as extra edges. The code implements that clarified construction; nothing else in Part A changed.
2. Agreement rates are computed only over decided and POWER-untied (or reach-untied) instances, as planned; this conditioning is a selection, and the undecided share is reported alongside (e.g. 85.4% undecided at $\gamma = 0.1$).
3. None other. Re-checks ran with fresh reward samples (seed salt 1–5), as planned.

## Limits

One graph model (out-degree U{1,2,3}, n = 20), IID U[0,1] state rewards, deterministic transitions, exact optimal (not learned) policies. "Decided" depends on M; the B1–B4 numbers are conditional on that threshold. Part A's 200 constructions sample a narrow family satisfying the condition; it is a numerical consistency check of a proved result, not a test that could add evidence to the theorem beyond detecting a gap.
