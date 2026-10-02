# Review (v2 standard)

The v1 jury reviews are in `v1/REVIEW.md`. This file is the v2 review of the seeded bundle.

## Review 1: publish (2026-10-02, fresh subagent, model claude-fable-5-1)

The reviewer was given only `paper.json`, `PLAN.md`, `bundle.json` and the project URL at commit b1475c3, with the standing reviewer instructions. It made its own fresh clone and ran the bundle four times on one CPU (about 16.5 minutes each).

**Verdict: publish**, with non-blocking fixes.

### Reasons given

1. The bundle reproduces exactly: a re-run with the paper's seed (2df726…df87) gave `outputs.json`, `analysis.json` and both counts files byte-identical to the committed ones.
2. It is deterministic: seed A run twice from empty results directories gave identical files.
3. All five claims survive two fresh seeds. No output came within one bootstrap SE of a refutation bound, and all 20 outputs are within the `bundle.json` tolerances pairwise across the paper seed, A and B.
4. Each claim's test tests the claim: each is a bound on named outputs. Confidences of 0.85 to 0.9 are reasonable; the tightest margin seen is about 1.2 SE (nu_small_nodup = 1.5649 under seed B against the bound 1.6).
5. The parent quotations are accurate (see below).
6. Honesty is good: the non-blind second sample, the unregistered no-duplicates arm, the smaller bootstrap, the poor collapse fit and the failed predictions are all disclosed. `PLAN.md` has a single commit (6729f95), five minutes before the first data commit (e823c59).

### Outputs under each seed

Seed A = ebaf5d6d23a02f91f5671a2b3699d67e913031ddc0a2e9ee76ceec6a56b8aa08; seed B = 28632c78ecb6747f99f0c7106bf93893c78a58616f2d4e65cdaef48e0842e81b.

| output | paper seed | seed A | seed B | tolerance | largest pairwise difference | refutation bound | holds |
|---|---|---|---|---|---|---|---|
| instances_per_arm | 82800 | 82800 | 82800 | exact | 0 | – | yes |
| alpha_c_small_dup | 4.0975 | 4.0915 | 4.1095 | 0.05 | 0.018 | claim 2: < 4.17 | yes |
| alpha_c_small_nodup | 4.1264 | 4.1152 | 4.1172 | 0.05 | 0.011 | claim 2: < 4.17 | yes |
| nu_small_dup | 1.4713 | 1.4747 | 1.4451 | 0.14 | 0.030 | claim 1: [1.4, 1.6] | yes |
| nu_small_nodup | 1.4888 | 1.5338 | 1.5649 | 0.14 | 0.076 | claim 1: [1.4, 1.6] | yes |
| phi_small_dup | 3.5252 | 3.1238 | 3.5506 | 1.3 | 0.43 | – | – |
| phi_small_nodup | 3.132 | 3.5061 | 3.4024 | 1.3 | 0.37 | – | – |
| alpha_c_large_dup | 4.201 | 4.2047 | 4.2051 | 0.045 | 0.004 | – | – |
| alpha_c_large_nodup | 4.2025 | 4.2047 | 4.2048 | 0.045 | 0.002 | – | – |
| large − small, dup | 0.1035 | 0.1132 | 0.0956 | – | – | claim 3: ≥ 0.04 | yes |
| large − small, nodup | 0.0761 | 0.0895 | 0.0876 | – | – | claim 3: ≥ 0.04 | yes |
| nu_eff_dup | 1.4378 | 1.4196 | 1.4649 | 0.25 | 0.045 | claim 5: [1.3, 1.9] | yes |
| nu_eff_nodup | 1.5027 | 1.413 | 1.4391 | 0.25 | 0.090 | claim 5: [1.3, 1.9] | yes |
| ks_law_miss_150_dup | 0.0068 | −0.0017 | 0.0048 | 0.025 | 0.0085 | claim 4: abs ≤ 0.03 | yes |
| ks_law_miss_200_dup | 0.0173 | 0.0173 | 0.0153 | 0.025 | 0.002 | claim 4: abs ≤ 0.03 | yes |
| ks_law_miss_150_nodup | 0.0005 | 0.0007 | 0.0063 | 0.025 | 0.006 | claim 4: abs ≤ 0.03 | yes |
| ks_law_miss_200_nodup | 0.0166 | 0.0198 | 0.0145 | 0.025 | 0.005 | claim 4: abs ≤ 0.03 | yes |
| se_alpha_c_small | 0.0089 | 0.0104 | 0.0095 | 50% relative | 17% | – | – |
| se_nu_small | 0.0284 | 0.0282 | 0.0302 | 50% relative | 7% | – | – |
| se_alpha_c_large | 0.0092 | 0.008 | 0.0077 | 50% relative | 16% | – | – |
| se_nu_eff | 0.0538 | 0.0471 | 0.0499 | 50% relative | 12% | – | – |
| se_alpha50_large | 0.0051 | 0.005 | 0.0055 | 50% relative | 9% | – | – |

### Same-seed identity (sha256 of results/outputs.json)

| run | sha256 |
|---|---|
| seed A, run 1 | b1665e53cc4d301693a65c3d1a53382636efbffa55395a81c6e585d705c3154e |
| seed A, run 2 | b1665e53cc4d301693a65c3d1a53382636efbffa55395a81c6e585d705c3154e |
| seed B | 1a59b9463bda9390f71bca914a9dc743b8a43d2e28d0285e8ca07c47555e3679 |
| paper seed, reviewer's re-run | 0b0ca765f16e6399b408339eac2a11730c91e29db87bb149f8db3f8f22873285 |
| paper seed, committed | 0b0ca765f16e6399b408339eac2a11730c91e29db87bb149f8db3f8f22873285 |

### Numbers in paper.json

- Matched to `outputs.json`: every figure in the abstract's results (1) to (5) and in the five claims, the five standard errors and the instance count.
- Supported by `analysis.json` only (same run, byte-identical, no figure quoted in the paper): the duplicates-allowed interval for alpha_c below 4.12 ([4.080, 4.112]); prediction 2 failing under both models ([4.188, 4.216] and [4.185, 4.216], both below 4.22); Crawford–Auton being as close or closer (misses 0.0066 / 0.0003 at N = 150 and 0.0080 / 0.0072 at N = 200).
- Not checkable: phi_small's tolerance of 1.3 has no SE among the outputs, so "about five SE" cannot be checked for it.

### Parents

- **Kirkpatrick & Selman (doi:10.1126/science.264.5163.1297).** The DOI page returned 403; the reviewer read the scanned PDF from the second author's Cornell page, all five pages. Confirmed verbatim: Table 1 for k = 3, the sentence on the errors, the scaling variable, the rescaling sentence, the 50% law, the sizes in Fig. 3A and the Crawford–Auton law. Two inaccuracies in our reading: "typically averaged over 10,000 samples" is from the Fig. 2 caption (N = 12 to 50), not stated for Fig. 3A; and KS did not simply fit by eye: the Fig. 3 caption takes alpha_c as "the crossing point of the curves at large N", and nu is then chosen to match slopes. The "replicates" relation is acceptable.
- **Wilson (arXiv:math/0005136).** Read through the fetch tool's summariser (HTML v2 and PDF v1), not by eye; both return the quoted sentences. "background" is correct.
- Crawford & Auton was not opened by anyone; it is used only as quoted in KS, as the paper says.

### Non-blocking points, and what was done

1. "Inside KS's stated range without duplicates" holds only for the paper seed (4.1264; seeds A and B and the v1 sample give 4.115 to 4.117, below 4.12); the interval straddles 4.12 in every sample. **Fixed**: abstract and builds_on note now say the estimate sits at the lower edge of the range with an interval that overlaps it.
2. "Prediction 1's alpha_c half failed with duplicates allowed" is seed-dependent (under seed B the interval reaches 4.12). **Fixed**: the abstract says it is a verdict on this sample.
3. The title's "depends on … the instance model" is not backed by a tested claim (the gap between the arms is 0.008 to 0.039 across four samples against an SE of the difference near 0.013). **Fixed**: removed from the title.
4. The title's "the 50% law holds" is stronger than claim 4; the N = 200 miss is positive in all eight arm-samples. **Fixed**: the title says "within 0.03 at N = 150, 200".
5. Claim 5 said "below the asymptotic lower bound of 2" while Wilson is cited only as background. **Fixed**: phrase removed from the claim (the abstract still mentions Wilson's result as context).
6. `bundle.json`'s commit is a placeholder and the artefact URL pins 7b56ac9 (code and results identical to b1475c3). **Left for the ready stage**, which pins both.
7. KS's procedure was misdescribed as "by eye". **Fixed** in the abstract's limitations. The reviewer's supplementary check (not part of the bundle, not in the paper): the crossing of the per-N logistic fits for N = 50 and 100 gives 4.12 to 4.21 across eight arm-samples, consistent with KS's 4.17 ± 0.05; "below 4.17" is a property of the four-parameter collapse, which the small sizes dominate. `PLAN.md` (the pre-registration) and `ANALYSIS.md` keep their original wording; this entry is the correction.
8. Claim 3 confounds sizes with the alpha grid. The reviewer's refit on a common grid (alpha 3.8 to 4.8) kept the gap at 0.095 to 0.128 (duplicates) and 0.059 to 0.091 (none). **Noted** as a limitation in the abstract; the refit is not an output of the bundle and is not claimed.
9. A run can be inside tolerance and still refute a claim. **Fixed**: one line in the methods.
10. Minor, recorded only: the deviance per degree of freedom counts saturated grid points (misfit understated if anything); "each negated with probability 1/2" is the standard reading rather than KS's words; the seed-to-seed SD of alpha_c_small_dup over four samples is 0.014 against a bootstrap SE near 0.009 to 0.010 (not significant with four samples).

Only wording in `paper.json` changed after the review (title, abstract, methods, claim 5's text, one builds_on note); no code, result, output, tolerance, confidence or refutation bound changed.

## After the review (ready stage, 2026-10-02)

The receipt-ready re-run (`RERUN.md`) put nu_small_nodup at 1.5939 under a new seed, close to claim 1's upper bound. Claim 1's confidence was lowered from 0.85 to 0.8; nothing else in the claims changed. The artefact link and `bundle.json`'s commit were pinned to 0c7376e (point 6 above).
