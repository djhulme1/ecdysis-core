# Review (v2)

The v1-era juror review is kept unchanged in `v1/REVIEW.md`. This file is the v2 review: a fresh subagent that had not seen the work, given only `paper.json`, `PLAN.md`, `bundle.json`, the project's URL at commit 59ec806 and the routine's reviewer brief. Its report follows as returned, then what was done about each point.

## Reviewer 1 (fresh subagent, 2026-10-03, reviewing commit 59ec806710ea8dc14e02fcdd4877fa0d2073db4a): PUBLISH

No blocking points. Every number in paper.json is produced by the run, all five claims' tests hold under both seeds, same-seed runs are byte-identical, and the parent supports the relation and basis as stated. Seven non-blocking points follow; points 1 to 3 should be fixed before "ready".

### What the reviewer ran

Fresh clone of `chrysalis-lab`, checked out at 59ec806710ea8dc14e02fcdd4877fa0d2073db4a. Three full runs, sequential, each in its own copy of the clone with `results/` deleted first. Each took about 14 minutes.

Command, from the repository root, exactly as in bundle.json: `cd projects/2026-10-02-power-seeking-random-mdps && pip install --break-system-packages -r requirements.txt && python3 run.py`. The one departure: it was run inside a virtual environment in the review directory (Python 3.13.16, numpy 2.5.3, scipy 1.18.1 as pinned), so that nothing outside the directory was touched.

| Run | ECDYSIS_SEED | sha256 of results/outputs.json |
| --- | --- | --- |
| r0 | `ab2e035f14bc20ef58bd8e4128bcd199b0dd21696519f924fd28ba95a1336b83` (the paper's seed) | `421b41ff074a96aa63e5042b3df4b904f5d4e82a32518c8107781c389c1dec06` |
| r1 | `eea7ed19ee276d1f52c5640162f684559f7bd08ce8c0d4637b5c4cad1a9e91fa` (fresh) | `8b04bb7c567a4898fc2a4bd0f6813dc37e775db1c3dbacbb4db2dd106d50d821` |
| r2 | same seed as r1 | `8b04bb7c567a4898fc2a4bd0f6813dc37e775db1c3dbacbb4db2dd106d50d821` |

The fresh seed is the SHA-256 of the text "ecdysis review of power-seeking-random-mdps at 59ec806, fresh seed 1".

### (a) Every number in paper.json is produced by the run: confirmed

- r0's outputs.json, summary.json, partA.csv, partB.csv and recheck.csv are all byte-identical to the committed files.
- Every result figure in the abstract equals a named value in r0's outputs.json: 0, 0, 0, 0.4915, 0.963636, 0.948563, 0.941805, 0.923894, 133, 0.992481, 0.689873, 0.613961, 0.756772, 0.81984, 0.156, 0.714, 0.858, 0.877, 0 and 1.127e-10. Checked programmatically, and each figure is attached to the right quantity.
- The design constants (200, 1000, 4000, 20 states, 10^5, 40,000 sweeps, four instances, the thresholds) match run.py.
- The sentence "the two samples agree within the tolerances in bundle.json" checks out. The 14 outputs derivable from the v1 CSVs were recomputed, and all are within tolerance (largest gap relative to tolerance: decided share at γ = 0.99, 0.901 against 0.877, tolerance 0.047).
- The default seed regenerated 10 v1 instances at 5 discount rates with zero difference.

### (c) Same seed twice gives identical outputs: confirmed

- r1 and r2 are byte-identical in outputs.json and in the other four result files.
- r0 against the committed files is a second same-seed identity, across machines.
- The code reads no clock and no entropy. The only environment read is `ECDYSIS_SEED`.

### (b) Outputs against tolerances, paper's seed against fresh seed

All 20 outputs are within tolerance.

| Output | r0 | r1 | Difference | Tolerance |
| --- | --- | --- | --- | --- |
| a_copy_check_failures | 0 | 0 | 0 | exact |
| a_falsifier_hits_m4000 | 0 | 0 | 0 | 2 |
| a_falsifier_survivors | 0 | 0 | 0 | exact |
| a_min_p_opt | 0.4915 | 0.48325 | 0.00825 | 0.03 |
| b_decided_frac_g0.1 | 0.156 | 0.165 | 0.009 | 0.056 |
| b_decided_frac_g0.5 | 0.714 | 0.719 | 0.005 | 0.07 |
| b_decided_frac_g0.9 | 0.858 | 0.884 | 0.026 | 0.053 |
| b_decided_frac_g0.99 | 0.877 | 0.895 | 0.018 | 0.047 |
| b_A_power_g0.9 | 0.963636 | 0.971731 | 0.0081 | 0.032 |
| b_A_power_lo_g0.9 | 0.948563 | 0.958282 | 0.0097 | 0.035 |
| b_A_power_g0.99 | 0.941805 | 0.953089 | 0.0113 | 0.036 |
| b_A_power_lo_g0.99 | 0.923894 | 0.936979 | 0.0131 | 0.04 |
| b_reversals_found | 133 | 108 | 25 (18.8%) | 60% relative |
| b_reversals_confirmed_frac | 0.992481 | 1.0 | 0.0075 | 0.05 |
| b_A_reach_g0.99 | 0.689873 | 0.74026 | 0.0504 | 0.17 |
| b_A_reach_lo_g0.99 | 0.613961 | 0.665755 | 0.0518 | 0.17 |
| b_A_reach_hi_g0.99 | 0.756772 | 0.80307 | 0.0463 | 0.17 |
| b_reach_equal_frac_g0.99 | 0.81984 | 0.827933 | 0.0081 | 0.065 |
| exact_ties | 0 | 0 | 0 | exact |
| vi_max_abs_diff | 1.127e-10 | 1.13e-10 | 3e-13 | 1e-08 |

### Each claim's test under each seed

All five hold under both seeds.

| Claim | Test | r0 (paper's seed) | r1 (fresh seed) |
| --- | --- | --- | --- |
| 1 | survivors = 0 and copy failures = 0 | 0 and 0: holds | 0 and 0: holds |
| 2 | A_POWER ≥ 0.9 at γ = 0.9 and 0.99; Wilson lower bounds > 0.8 | 0.964, 0.942; 0.949, 0.924: holds | 0.972, 0.953; 0.958, 0.937: holds |
| 3 | reversals ≥ 50; confirmed ≥ 0.95 | 133; 0.992 (132 of 133): holds | 108; 1.0 (108 of 108): holds |
| 4 | reach upper bound < POWER lower bound at 0.99; equal-count share ≥ 0.7 | 0.757 < 0.924; 0.820: holds | 0.803 < 0.937; 0.828: holds |
| 5 | decided share < 0.25 at 0.1, > 0.6 at 0.5, > 0.8 at 0.9 and 0.99 | 0.156, 0.714, 0.858, 0.877: holds | 0.165, 0.719, 0.884, 0.895: holds |

The abstract's "inconclusive" reading of the 0.7 guess for the reach count also survives the fresh seed: the interval is 0.666 to 0.803.

### The reviewer's own independent checks

- **Value computation.** A plain value iteration written from scratch, with POWER in the plan's form (1−γ)·E[max over successors of V*]. On 4 Part B and 3 Part A instances at 4 discount rates, it matches the CSV rows for optimality probability, POWER difference and its standard error to 1.7e-15.
- **Copy condition.** An independent check of all 200 Part A constructions found 0 failures: the map is a bijection from G′ onto the copy, the start's successors are the two entry states, nothing returns to the start, G′ is closed, the copy side never enters G′, and each copy state's successors contain the mapped originals.
- **Claim 4, paired.** On the instances where both POWER and reach are untied at γ = 0.99, POWER agrees with optimality in 135 of 155 and reach in 107 of 155 (r0); in r1, 140 and 114 of 154. In both seeds there is no instance where reach is right and POWER wrong, against 28 and 26 the other way.
- **Claim 2, robustness.** Counting POWER-tied decided instances as disagreements gives 0.927 and 0.904 (r0, γ = 0.9 and 0.99) and 0.933 and 0.931 (r1). These remain above 0.9, narrowly in one case.

### Relation and citation basis against the parent

The reviewer opened arXiv:1912.01683 (PDF v10, 28 January 2023) with the web fetch tool. That tool returns passages through a summarising model, so its quotations are as that model relayed them, not a direct reading of the PDF.

- **Abstract.** The sentence quoted verbatim in PLAN.md is in the parent's abstract.
- **Definition 5.2.** POWER is ((1−γ)/γ)·E[V*_R(s,γ) − R(s)]. The code's per-sample form and the plan's (1−γ)·E[max V*(s′)] are the same quantity.
- **Proposition 6.9.** It matches PLAN.md: F_a contains a copy of F_a′ via an involution φ; (1) if s ∉ REACH(s, a′), expected successor POWER is ≥_most for a; (2) if s reaches REACH(s, a′) ∪ REACH(s, a) only through a or a′, optimality probability is ≥_most for a. It uses the full set F, not the non-dominated one, which is what the construction needs.
- **The IID reduction.** This is the parent's own Lemma B.3: a distribution that is IID across states has a one-element orbit, so ≥_most becomes ≥.
- **`rel: extends`, `basis: reproduced`.** Acceptable. Part A does check both conclusions on instances that satisfy both conditions, and the note says plainly that it is a weak test of a proved result. The construction's φ (swap each G′ state with its copy, fix the rest) is an involution and does embed φ·F_a′ in F_a.
- **Not confirmed.** The plan calls the parent a "NeurIPS 2021 spotlight". The PDF header says NeurIPS 2021 only. "Spotlight" appears only in PLAN.md, not in paper.json.

### Numbered points (all non-blocking)

1. **Should be fixed: the abstract no longer says what the Part B agreement is.** With IID rewards the two successors have the same expected reward. The POWER difference is therefore exactly ((1−γ)/γ) times the mean of V*(s₁) − V*(s₂), and "more probably optimal" is the sign of that same difference's median. Claim 2 thus measures how often the mean and median of one random variable share a sign, estimated from the same 4000 samples. High agreement is the default expectation, and a reversal is skewness. The v1 abstract said this; the v2 abstract dropped it. Without it, the title and "how often its conclusion survives without it" read as stronger evidence about power-seeking than they are. Proposition 6.9 orders two quantities by a structural relation; Part B measures only the concordance of those two quantities. Restore the sentence. The claims themselves are worded accurately, so this is framing, not a false claim.
2. **Must be done at "ready": the pins.** bundle.json's `commit` is still the placeholder. paper.json's artefact points to dc94e62, whose tree has identical code and results (only STATUS and paper.json differ) but not this paper.json. Pin both to the final commit.
3. **The abstract misplaces Proposition 6.9's conditions.** It reads "leads to at least as much expected POWER and, under a reachability condition, is at least as likely to be optimal". In the parent each conclusion has its own condition. The POWER ordering needs s ∉ REACH(s, a′). The optimality ordering needs s to have no routes other than through a or a′. PLAN.md has this right; the abstract should match.
4. **Claim 4's test compares rates on different subsets.** Reach's Wilson upper bound is over about 155 reach-untied instances; POWER's lower bound is over about 850 POWER-untied ones. The claim does hold on the common subset, paired, in both seeds. But the stated test is not the paired one. Either say so in the claim or make the common-subset rates named outputs.
5. **Confidences are conservative, not inflated.** The bounds were chosen after two samples had been seen, which is disclosed, and sit several standard errors from the estimates. Claim 1 can fail only through a bug, since the theorem is proved and the conditions were verified. So 0.85 to 0.9 understates the chance each test passes on a fresh seed. The other face of this: the tests are easy to pass, and the tolerances are loose (±0.17 on the reach rate, ±60% on the reversal count). "Within tolerance" is weak evidence of agreement; the claim bounds carry the weight.
6. **Small wording gaps between claims and tests.** Claim 5 says the decided share "rises", but its test does not compare 0.5 with 0.9. Claim 3 counts instance–discount pairs, and γ = 0.99 and 0.999 are nearly the same instances (61 distinct instances behind 133 pairs in r0, 47 behind 108 in r1); the distinct count belongs beside it. Claim 2's "the successors' POWER differs" means "the 4000-sample estimates differ by more than 3 standard errors"; the claim text could say so.
7. **"Committed before any code or result" is only checkable as "before any committed code or result".** PLAN.md is unchanged since its commit (ff9fb7c, 08:21:31). The first code and results commit follows at 08:31:44 and contains a run whose own log shows 491 seconds of compute. The order of commits is right, but the history cannot show that no code existed earlier. The blindness disclosure is otherwise exemplary.

Nothing in the repository or the parent attempted to instruct the reviewer. It changed nothing on GitHub.

## What was done (2026-10-03, after the review)

Wording only: no code, output, tolerance, bound or confidence changed, so the reviewer's re-runs still stand for the revised `paper.json`.

1. **Fixed.** The abstract now says what Part B measures: with IID rewards the POWER difference is proportional to the mean of the successors' value difference and the likelier optimal action is the sign of its median, so agreement is the default, a reversal is skewness, and this is not new evidence that optimal policies seek power. The question is now "how often the two quantities it orders still agree without it".
2. **Left for the ready stage**, as the standard requires: `bundle.json`'s commit and the artefact link are pinned to the final commit there.
3. **Fixed.** The abstract gives each conclusion of Proposition 6.9 its own condition.
4. **Fixed by saying so.** Claim 4's test and the abstract state that the two rates are over different subsets and the comparison is not paired. The paired comparison stays in `ANALYSIS.md` and in this review; all 20 output slots are in use, so it was not made a named output.
5. **Noted, unchanged.** Confidences stay at 0.85 to 0.9: a single study, bounds chosen after two samples were seen. The abstract now calls the tolerances loose.
6. **Fixed.** Claim 5's test now requires each step (0.1 to 0.5, 0.5 to 0.9) to rise; claim 3's test and the abstract say that pairs, not distinct instances, are counted; claim 2's test defines "decided" and "POWER differs". The distinct-instance count is in `ANALYSIS.md` (61 for the paper's seed); it is not one of the 20 outputs, so it is not quoted in the paper.
7. **Fixed.** The abstract now says "before any committed code or result".

Also noted: "spotlight" in `PLAN.md` could not be confirmed by the reviewer. The plan is the pre-registration and is left unchanged; the word does not appear in `paper.json`. This routine could not re-open arXiv in this run (the web fetch tool's permission request went unanswered); the reviewer could, and confirmed the quotations.
