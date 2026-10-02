# v1-era files (kept unchanged, superseded)

The first pass of this project, done on 1 October 2026 under Ecdysis v1: fixed instance seeds
(`ks94|N|alpha_index|sample`), separate analysis scripts, a `paper.json` in protocol 0.1 and two juror reviews.
It was never submitted. Paths inside these scripts are relative to this folder, so they still run here.

The v2 receipt bundle in the parent folder (`run.py`, `bundle.json`) repeats the same pre-registered grid, instance
models, solver and analyses, but draws every formula and every bootstrap resample from one seed (`ECDYSIS_SEED`).
Fed these v1 counts, the v2 analysis code returns the v1 numbers exactly (collapse on N = 12 to 100: alpha_c 4.0762,
nu 1.5194 with duplicates allowed; 4.1154, 1.5168 without), so the v1 data stand as one further independent sample.
