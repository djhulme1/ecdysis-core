# v1-era files (kept unchanged, superseded)

The first pass of this project, done on 2 October 2026 under Ecdysis v1: a fixed master seed (20261002),
separate scripts (`run.py`, `analyse.py`, `recheck.py`, `vi_check.py`), a `paper.json` in protocol 0.1 and one
juror review. It was never submitted. `mdp.py` is copied here so that the scripts still run from this folder.

The v2 receipt bundle in the parent folder (`run.py`, `bundle.json`) repeats the same pre-registered
constructions, estimators, thresholds and re-checks in one entry point, and draws every instance and every
reward sample from one seed (`ECDYSIS_SEED`). With no seed set, its default seed derives the v1 master seed
(20261002), so the default run regenerates the v1 instances and reward samples.
