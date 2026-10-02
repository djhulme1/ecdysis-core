# Re-run

Outcome: **matched**.

- Commit: e4411674081e3d468ab7c0a6db9f1599b39bc660 (the commit in paper.json's artefacts), fresh clone, numpy 2.5.3, scipy 1.18.1 from requirements.txt.
- Commands: `python3 analyse.py && python3 vi_check.py` in `projects/2026-10-02-power-seeking-random-mdps`.
- `results/summary.json` and `results/vi_check.json` byte-identical to the committed files.
- Every number in paper.json checked programmatically against the fresh outputs (`summary.json`, `recheck.csv`, `vi_check.json`): no Part A falsifier hits over 1000 pairs; minimum 0.478 at $\gamma$ = 0.1; 836/877 = 95.3% [93.7, 96.5] at 0.99; 96.4% [94.9, 97.4] at 0.9; 41 reversals, 4.7% [3.5, 6.3]; 115/115 confirmed, smallest |z| 7.4, smallest POWER gap 8.4 SE; reach 73.8% [66.7, 79.9] on 168, 733 of 901 equal; decided share 14.6% to 90.1%; value-iteration difference 1.1e-10. All matched.
- Not re-run here: `run.py` and `recheck.py` (the raw CSVs); juror 1 regenerated 30 instances from seeds bit for bit.
