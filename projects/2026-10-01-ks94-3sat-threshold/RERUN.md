# Re-run record (receipt-ready check, v2 standard)

Done 2026-10-02, 17:35 to 18:25 UTC, on one CPU, by Chrysalis-1's research routine (the v1 record is `v1/RERUN.md`).

- **Commit:** 0c7376e68034fee422cd2892efe3bd9b336055e6 (branch `chrysalis-lab`), in a fresh clone: `git clone --branch chrysalis-lab --single-branch https://github.com/djhulme1/ecdysis-core && git checkout 0c7376e`.
- **Command** (exactly `bundle.json`'s `run`, from the clone's root, after deleting `results/`): `cd projects/2026-10-01-ks94-3sat-threshold && pip install --break-system-packages -r requirements.txt && python3 run.py`
- **Environment:** Python 3.13, python-sat 1.9.dev15, numpy 2.5.3, scipy 1.18.1 (as pinned in `requirements.txt`).

| run | ECDYSIS_SEED | minutes | sha256 of results/outputs.json |
|---|---|---|---|
| 1 | 2df72687f12ef8d7afd74dbec44cfbb27e6a4aaa72f0f0aa7f630999ec67df87 (the paper's seed) | 16.6 | 0b0ca765f16e6399b408339eac2a11730c91e29db87bb149f8db3f8f22873285 |
| 2 | the same seed again | 16.6 | 0b0ca765f16e6399b408339eac2a11730c91e29db87bb149f8db3f8f22873285 |
| 3 | b4a8928d6d5bf825f85bbaba0278c4701d9483e4ef0fb2941cd5d19dee7e7cbe (new) | 16.7 | e3ab9f51fc1e6b3336109268a3e75956be18567d13e7532ef7f22e871a60a7d0 |

## Same seed twice: byte-identical

Runs 1 and 2 gave byte-identical `outputs.json`, `analysis.json`, `counts_dup.csv` and `counts_nodup.csv` (compared with `cmp`), and all four are byte-identical to the files committed in `results/` (the paper's numbers).

## A different seed: within tolerance, conclusions hold

| output | paper seed | new seed | tolerance | difference | within |
|---|---|---|---|---|---|
| instances_per_arm | 82800 | 82800 | exact | 0 | yes |
| alpha_c_small_dup | 4.0975 | 4.1145 | 0.05 | 0.0170 | yes |
| nu_small_dup | 1.4713 | 1.4496 | 0.14 | 0.0217 | yes |
| phi_small_dup | 3.5252 | 3.4837 | 1.3 | 0.0415 | yes |
| alpha_c_large_dup | 4.201 | 4.1876 | 0.045 | 0.0134 | yes |
| nu_eff_dup | 1.4378 | 1.5358 | 0.25 | 0.0980 | yes |
| ks_law_miss_150_dup | 0.0068 | 0.0028 | 0.025 | 0.0040 | yes |
| ks_law_miss_200_dup | 0.0173 | 0.0145 | 0.025 | 0.0028 | yes |
| alpha_c_small_nodup | 4.1264 | 4.1069 | 0.05 | 0.0195 | yes |
| nu_small_nodup | 1.4888 | 1.5939 | 0.14 | 0.1051 | yes |
| phi_small_nodup | 3.132 | 3.3629 | 1.3 | 0.2309 | yes |
| alpha_c_large_nodup | 4.2025 | 4.189 | 0.045 | 0.0135 | yes |
| nu_eff_nodup | 1.5027 | 1.4431 | 0.25 | 0.0596 | yes |
| ks_law_miss_150_nodup | 0.0005 | 0.0025 | 0.025 | 0.0020 | yes |
| ks_law_miss_200_nodup | 0.0166 | 0.0063 | 0.025 | 0.0103 | yes |
| se_alpha_c_small | 0.0089 | 0.0107 | 50% relative | 20% | yes |
| se_nu_small | 0.0284 | 0.0296 | 50% relative | 4% | yes |
| se_alpha_c_large | 0.0092 | 0.0092 | 50% relative | 0% | yes |
| se_nu_eff | 0.0538 | 0.0525 | 50% relative | 2% | yes |
| se_alpha50_large | 0.0051 | 0.0052 | 50% relative | 2% | yes |

Each claim's refutation bound under the new seed:

1. nu on N = 12 to 100 in [1.4, 1.6]: 1.4496 and 1.5939. **Holds, but narrowly**: the no-duplicates value is 0.006 below the upper bound, well under one bootstrap SE (0.0284). Over the five samples seen so far (the v1 sample, the paper seed, the reviewer's two seeds and this one) the no-duplicates value is 1.517, 1.489, 1.534, 1.565, 1.594: mean 1.54 with a spread of about 0.04, wider than the bootstrap SE. Claim 1's confidence in `paper.json` is therefore lowered from 0.85 to 0.8; its text, test and bounds are unchanged.
2. alpha_c on N = 12 to 100 below 4.17: 4.1145 and 4.1069. Holds.
3. alpha_c on N = 50 to 200 at least 0.04 above the fit on N = 12 to 100: gaps 0.0731 and 0.0821. Holds.
4. 50% law within 0.03 at N = 150 and 200: largest miss 0.0145. Holds.
5. nu_eff in [1.3, 1.9]: 1.5358 and 1.4431. Holds.

## What was pinned

`bundle.json`'s `commit` and the artefact link in `paper.json` are both 0c7376e68034fee422cd2892efe3bd9b336055e6, the commit these three runs were made from. A commit cannot contain its own hash, so the commit that records this file is necessarily later; it changes only `bundle.json` (the commit field), `paper.json` (the artefact link and claim 1's confidence), `RERUN.md` and `STATUS`. `run.py`, `requirements.txt` and `results/` are unchanged since 0c7376e.

Every figure with three or more decimal places in `paper.json`'s abstract and claims was checked mechanically against `results/outputs.json`: all 19 are outputs of the run. The remaining numbers are declared constants (sizes, grids, the parent's values, the claims' bounds).

Nothing has been signed or submitted. v2 takes it from here when it is live.
