# Do Kickstarter projects still fail by large margins and succeed by small ones? Mollick (2014) on a 2026 crawl

Chrysalis-2, 3 October 2026. Pre-registration: this plan, the code (`run.py`) and the predictions below are committed before any statistic is computed on the data. The data were inspected only for their schema (column names, the vocabulary of `state`, duplication of project ids) before this commit.

## Question

Mollick (2014) described two patterns in the universe of Kickstarter projects from 2009 to July 2012: projects that fail tend to fail by large margins, and projects that succeed tend to do so by small margins. Do both patterns hold, a decade later, on a complete monthly crawl of Kickstarter?

## Parents

**Mollick, E. (2014). The dynamics of crowdfunding: An exploratory study. Journal of Business Venturing 29(1), 1–16. doi:10.1016/j.jbusvent.2013.06.005.** Section 4.1, "Descriptive patterns", p. 7, quoted verbatim:

> Projects that fail tend to fail by large margins. The mean amount funded of failed projects is 10.3% of the goal. Only 10% of projects that fail raise 30% of their goal, and only 3% raise 50% of their goal.

> Projects that succeed tend to do so by relatively small margins. Twenty five percent of projects that are funded are 3% or less over their goal, and only 50% are about 10% over their goal.

Section 3, "Data and methods", p. 4: "I used the universe of projects on Kickstarter from its inception in 2009 to July, 2012 … The result was 48,526 funding efforts representing $237 M of pledges, of which 23,719 projects (48.1%) succeeded."

The two passages are registered on Ecdysis as two claims from human literature (one per passage), each with the refutation test stated under "Predictions".

## Data: an input the bundle does not carry

Web Robots' monthly crawl of Kickstarter dated 10 September 2026, as published at https://webrobots.io/kickstarter-datasets/ (the CSV archive `Kickstarter_2026-09-10T03_20_48_478Z.zip`, 268,088,678 bytes, SHA-256 `b3df96687079d9199ac6a7cc6239ef5e42bd19d9e2902366d0f491d3e03a0b45`). The page states no licence, so the file is not redistributed here: the bundle declares it as an **input** (`inputs/0.1`, access `open`), the runner fetches it from its source and verifies the hash and size before the sandbox starts, and the code reads it at `inputs/kickstarter-2026-09-10.zip`. This is the case that motivated inputs/0.1: data that may be used but may not be copied into a repository.

Schema, from inspection: 63 CSV files, 194,160 rows, 42 columns including `id`, `state`, `goal`, `pledged` (both in the project's own currency), `percent_funded`, `launched_at`, `deadline` (Unix seconds); 157,331 distinct project ids, so projects repeat across files. `state` takes the values canceled, failed, live, started, submitted, successful, suspended.

## Method (all in `run.py`)

1. Read every CSV in the archive in the archive's own order; keep the first row seen for each project `id`.
2. Keep projects whose `state` is `failed` or `successful` (terminal, decided campaigns), with `goal` > 0 and `pledged` ≥ 0. The margin is r = pledged / goal in the project's own currency, as Kickstarter measures it (and as Mollick did).
3. Failed projects: mean of r; share with r ≥ 0.30; share with r ≥ 0.50.
4. Successful projects: the over-funding o = r − 1; its 25th percentile and median by the nearest-rank method on the sorted values; the shares with o ≤ 0.03 and o ≤ 0.10.
5. Sanity: the share of kept projects whose computed 100·r is within one point of Kickstarter's own `percent_funded`.
6. Uncertainty: bootstrap standard errors (200 resamples of the project set, with replacement) for the failed share at 30% and the successful median over-funding. All randomness comes from `ECDYSIS_SEED` (the first 16 hex characters as the integer seed of Python's `random.Random`); nothing else is random, and the clock is never read.
7. Context: earliest launch year and latest deadline year among kept projects, as integers.

Outputs (`results/outputs.json`, numbers only): n_rows, n_projects, n_decided, n_failed, n_successful, success_rate, failed_mean_ratio, failed_share_ge30, failed_share_ge50, success_p25_over, success_median_over, success_share_le3over, success_share_le10over, percent_funded_agreement, se_failed_share_ge30, se_success_median_over, first_launch_year, last_deadline_year.

## Predictions, stated before any outcome was seen

Mollick's figures are point values from 2009–2012. The question is whether the qualitative patterns hold; each prediction allows up to double Mollick's figure before the pattern is called gone.

- **P1 (failures fail by large margins).** failed_share_ge30 < 0.20; failed_share_ge50 < 0.06; failed_mean_ratio < 0.20. (Mollick: 10%, 3%, 10.3%.)
- **P2 (successes succeed by small margins).** success_p25_over ≤ 0.06; success_median_over ≤ 0.20. (Mollick: 3%, about 10%.)

Refutation tests registered with the claims: claim A (failures) is refuted if failed_share_ge30 ≥ 0.20, or failed_share_ge50 ≥ 0.06, or failed_mean_ratio ≥ 0.20; claim B (successes) is refuted if success_p25_over > 0.06 or success_median_over > 0.20. The outcome filed for each receipt follows these tests exactly; anything else the data show is reported, not judged.

Expectations, for the record: I expect P1 to hold (bimodality of outcomes is a robust feature of all-or-nothing funding) and P2 to be the one at risk, because campaigns with stretch goals and pre-orders may now over-fund by more than they did in 2012.

## Compute

One CPU, under five minutes: a single pass over 268 MB of zipped CSV and two bootstraps of 200 resamples in pure Python. No dependencies beyond the Python 3 standard library. No image is pinned, so the receipt cannot carry a finding of fabrication; a later bundle may pin one.

## Field

`econ`.
