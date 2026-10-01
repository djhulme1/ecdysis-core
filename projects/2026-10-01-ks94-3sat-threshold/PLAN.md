# Does Kirkpatrick & Selman's finite-size scaling of the random 3-SAT threshold hold up with a modern solver and larger N?

Area: sat · Kind: assessment (replication / check of a published claim) · Field label: **math**
Pre-registered: the commit that adds this file. Written 2026-10-01 before any satisfiability outcome was seen.

## Question
Kirkpatrick & Selman (1994) fitted the random 3-SAT satisfiability transition, for N = 12 to 100 variables, with finite-size scaling and reported $\alpha_c = 4.17 \pm 0.05$ and $\nu = 1.5 \pm 0.1$. Do these parameters reproduce on fresh data in their own N range, and does their implied 50% point $\alpha_{50}(N)$ predict the transition at larger N (150, 200)?

## Parents (opened and checked)
1. **Kirkpatrick, S. & Selman, B. (1994) "Critical Behavior in the Satisfiability of Random Boolean Expressions", Science 264, 1297–1301, doi:10.1126/science.264.5163.1297.** Read in full (scanned PDF from the second author's Cornell page). Exact claims tested:
   - Table 1 (k = 3): "$\alpha_c$ 4.17 ± 0.05, $y_{50}$ 0.74, $\nu$ 1.5 ± 0.1", where "The errors show the range of each parameter over which the best fits were obtained."
   - Scaling variable: "$y = N^{1/\nu}(\alpha - \alpha_c)/\alpha_c$".
   - "Rescaling with $\alpha_c$ = 4.17 and $\nu$ = 1.5 (Fig. 3B), we find that these two parameters capture both the threshold shift and the steepening of the curves."
   - "For k = 3, $\alpha_{50} \approx 4.17 + 3.1N^{-2/3}$".
   - Their 3-SAT data: N = 12, 20, 24, 40, 50, 100 (Fig. 3A), "typically averaged over 10,000 samples", Davis–Putnam backtracking.
   - They also quote Crawford & Auton's fit "$\alpha_{50}$ = 4.24 + 6/N" (not opened separately; used only as a second reference curve, never as a parent).
2. **Wilson, D. B. "On the critical exponents of random k-SAT", arXiv:math/0005136** (background). Abstract quoted: "Experiments have suggested that ν₃ = 1.5 ± 0.1 ... We give here a simple proof that each of these exponents is at least 2 (provided the exponent is well-defined)." Context only: the asymptotic exponent cannot be 1.5, so any agreement with 1.5 at small N must be an effective, finite-size exponent.

## Method
- Instances: random 3-CNF, N variables, M = round($\alpha$N) clauses, each clause 3 distinct variables chosen uniformly, each negated with probability 1/2 (KS's model). Clauses drawn independently (duplicates allowed).
- Solver: MiniSat 2.2 through python-sat (complete; each instance decided exactly, no time limit). Choice made from a timing-only pilot (wall time at N = 200, 250, α = 4.26; outcomes not recorded or looked at): CaDiCaL and MiniSat both take seconds per unsatisfiable instance at N = 250, so N is capped at 200.
- Grid: N ∈ {12, 20, 24, 40, 50, 100}: α from 3.0 to 6.0 step 0.1, 400 instances per point. N ∈ {150, 200}: α from 3.8 to 4.8 step 0.05, 200 instances per point. Seeds: instance seed derived deterministically from (N, α index, sample index) via SHA-256.
- Analyses (all pre-specified):
  - **A1 per-N 50% point and width.** Fit a two-parameter logistic in α to the binomial counts at each N (maximum likelihood). $\alpha_{50}(N)$ = midpoint; width $w(N)$ = distance between the 10% and 90% points. Intervals by parametric bootstrap over instances (1000 resamples).
  - **A2 collapse in KS's range.** On N ≤ 100 only, fit $P_{unsat} = F(y)$, $y = N^{1/\nu}(\alpha-\alpha_c)/\alpha_c$, with F a logistic in y (location $y_{50}$, scale s), parameters ($\alpha_c$, $\nu$, $y_{50}$, s) by maximum likelihood; 95% intervals by bootstrap.
  - **A3 collapse over the larger range.** The same fit on N ∈ {50, 100, 150, 200}.
  - **A4 effective exponent.** $1/\nu_{eff}$ = slope of $\log w(N)$ against $\log N$ for N ∈ {50, 100, 150, 200}, with bootstrap interval.
  - **A5 out-of-sample prediction.** Compare $\alpha_{50}(150)$ and $\alpha_{50}(200)$ with KS's $4.17 + 3.1N^{-2/3}$ (4.229 and 4.261) and with Crawford–Auton's 4.24 + 6/N (4.280, 4.270).

## Predictions and what would falsify them
- **P1 (replication).** A2's 95% intervals overlap $\alpha_c$ = 4.17 ± 0.05 and $\nu$ = 1.5 ± 0.1. Falsified if either interval lies wholly outside KS's range.
- **P2 (drift).** A3 gives $\alpha_c$ above 4.22 (above KS's range), i.e. the fitted critical point drifts up as larger N is included. Falsified if A3's 95% interval for $\alpha_c$ includes 4.22 or lies below it.
- **P3 (out-of-sample).** KS's formula predicts $\alpha_{50}$ at N = 150 and 200 to within 0.03. Falsified if either bootstrap 95% interval for $\alpha_{50}$ lies wholly more than 0.03 from the formula.
- **P4 (effective exponent).** A4 gives $\nu_{eff}$ in [1.3, 1.9]: the transition still sharpens faster than the asymptotic bound $\nu \ge 2$ allows at these sizes. Falsified if the 95% interval lies wholly outside [1.3, 1.9].
I hold P1 and P4 with moderate confidence (~0.6), P2 and P3 with low confidence (~0.5): I do not know the answer.

## Compute plan
Two cores. Estimated ≤ 25 minutes in total (N ≤ 100: about 74,000 small instances; N = 150, 200: 8,400 instances at roughly 0.1–0.5 s each). One run for data, one for analysis. If N = 200 exceeds 30 minutes, it is finished in a second run with the same seeds; nothing is changed after seeing outcomes.

## Deviations
Any deviation from this plan will be recorded in ANALYSIS.md.
