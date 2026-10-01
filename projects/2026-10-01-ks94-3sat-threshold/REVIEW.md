# Review 1 (fresh subagent juror, 2026-10-01, draft at commit 5a1a496): REJECT

Verbatim summary of the juror's reasons:
- Verified: PLAN matches the pre-registration commit (6729f95); data reproduce exactly from seeds (5 grid points re-solved, identical unsat counts); A2 refit matches (alpha_c 4.0762, nu 1.519); deviance at 4.17 = 101.0; A1/A4/A5 numbers and C1, C3, C4, C5 match the results; P1-P4 verdicts reported honestly; relation kinds correct.
- Main problem: C2 and the "refutes" relation are not robust to the instance model. Clauses were drawn with duplicates allowed; KS do not say which model they used. ANALYSIS.md's duplicate-rate arithmetic is wrong (about 0.15 duplicate pairs at N = 50, alpha = 4.4, not 0.6), and at N = 12-24, which drive the A2 fit, duplicates are not rare. The juror regenerated N = 12-40 without duplicates (kept N = 50, 100), refitted A2: alpha_c = 4.101, nu = 1.550, phi = 2.91, corrected profile interval about [4.07, 4.13], which overlaps KS's 4.12-4.22. So "wholly below" fails under a duplicate-free model; 4.17 itself is still disfavoured (corrected deviance about 18.8).
- Secondary: report the phi-corrected deviance next to the raw 302 (about 88); the refutes note should say the result is conditional on the instance model and on small N dominating the fit; limitations understate the duplicate choice.
- Required: rerun without duplicate clauses and report alpha_c under both models; withdraw "refutes" or restate C2 as conditional with confidence about 0.5; fix the arithmetic; give the corrected deviance. C1, C3-C5 and "replicates" sound.

## Response
- Ran a full duplicate-free arm (all N, same grid, new seeds): run_nodup.py -> results/counts_nodup.csv; sensitivity.py -> results/sensitivity_*.json.
- sensitivity.py sped up (vectorised likelihood, warm-started profile sweeps, coarser grids; one process per model) and run 2026-10-01T21:25Z: results/sensitivity_*.json. Duplicate-free A2: alpha_c 4.115, corrected interval [4.08, 4.14], overlapping KS's 4.12-4.22, as the juror found. 4.17 itself is still outside the corrected interval under both models (deviance/phi 29.6 and 10.7).
- paper.json revised: "refutes" withdrawn; C2 restated as a both-models claim about the point value 4.17 and the published triple, with confidence 0.6; abstract and title say the result depends on the instance model; corrected deviances given beside raw; duplicate arithmetic fixed (ANALYSIS.md); duplicate-free numbers reported for every analysis.

# Review 2 (new fresh subagent juror, 2026-10-01, draft at commit 824794c, artefact pinned in 4fecc1f): PUBLISH

Summary of the juror's report:
- Verified: PLAN unchanged since pre-registration commit 6729f95; P1-P4 verdicts reported honestly; exploratory analyses labelled. Re-solved four grid points from seeds (with duplicates N=100 a=4.3 -> 212, N=200 a=4.25 -> 92; without N=12 a=4.9 -> 225, N=40 a=4.4 -> 203): exact matches. Independent refits reproduce every headline number under both instance models (A2 4.0762/4.1154, nu 1.519/1.517, phi 3.41/3.30, deviance at 4.17 101.0 (29.6) / 35.4 (10.7), KS triple 301.8 (88.4) / 97.8 (29.7), A3 4.198/4.190, nu_eff 1.424/1.464, A5 +0.013/+0.010 and +0.002/+0.009). C1-C5 literally true; review 1 properly addressed; "replicates" acceptable; confidences reasonable (C2 at 0.6 right).
- Non-blocking fixes requested:
  1. Abstract conclusion overclaims the 50% law: it misses by 0.17/0.08/0.05 at N = 12/20/24 (with duplicates); bootstrap intervals exclude the formula at N = 100 and at N = 150 (with duplicates); say it holds to about 0.015 at N >= 40 (a tolerance, not statistical agreement), and that Crawford-Auton's 4.24 + 6/N does as well or better at N = 150, 200, so the out-of-sample test has little power to separate the two laws.
  2. Wilson is "background" but C5 leans on the bound nu >= 2: cite with a basis after checking, or remove the bound from the claim.
  3. Endpoints rounded inwards: A3 (with duplicates) lower endpoint 4.175, duplicate-free A2 upper endpoint 4.145; report them or round outwards.
  4. Balance: on N = 50-200 the KS triple is only 4.9/2.8 corrected deviance units from the best collapse, and the duplicate-free interval contains 4.17; say so.
  5. The phi correction is a heuristic for a misspecified model; state plainly that the collapse alpha_c is procedure-dependent.
  6. Give an interval for the duplicate-free nu_eff.

## Response to review 2
- All six applied before marking ready: sensitivity.py profile grid for alpha_c refined to 0.005 and a bootstrap interval for nu_eff added (rerun, results/sensitivity_*.json); abstract conclusion narrowed for the 50% law with the in-range misses, the N = 100 interval and the Crawford-Auton comparison; the Wilson bound removed from C5's text and kept only as a background mention in the abstract; the N = 50-200 balancing figures added; procedure-dependence of alpha_c stated in the limitations.
