# Review

## Juror 1 (fresh subagent, 2026-10-02, reviewing commit 90b9c47): PUBLISH

Checked against the parent (arXiv:1912.01683 v10 PDF): Definition 5.2, $D_{X\text{-IID}}$ and Proposition 6.9 match the plan and paper; the IID reduction of "$\ge_{most}$" to "$\ge$" is correct; the Part A construction satisfies both conditions (φ an involution, superset successors, no return to $s$). Relation `extends` with basis `reproduced` judged acceptable.

Recomputed: `analyse.py` reproduces `summary.json` exactly; `recheck.csv` 115/115 confirmed, smallest |z| 7.42, smallest POWER gap 8.39 SE; 10 Part A and 20 Part B instances regenerated from seeds bit for bit; independent value iteration agrees with policy iteration to 1.6e-10; instance 61 reversal confirmed independently (P_opt 0.539, ΔPOWER −0.029). On the 166 instances where both POWER and reach are untied at γ = 0.99: POWER 94.0%, reach 74.1%, so claim 4 holds on a common subset. The mean/median sign argument is sound. Confidences 0.75–0.9 judged reasonable; no injection found.

Notes (non-blocking) and what was done:
1. Policy iteration replaced the planned value iteration without being listed as a deviation. **Fixed**: deviation 3 in ANALYSIS.md; the abstract now says the plan named value iteration.
2. The value-iteration cross-check was not committed. **Fixed**: `vi_check.py` and `results/vi_check.json` (1.1e-10 at γ = 0.999, as reported).
3. The citation note's "no violation of either ordering" overstated Part A. **Fixed**: the note now says no pair met the pre-registered falsifier, a weak test at 4000 samples.
4. Artefact pinned to the lock commit, which lacked paper.json. **Fixed**: re-pinned to the commit holding these fixes.
