# Results: grokking on modular addition, seed e061c39c…

Receipt `163a94c2…` on `ext:c3a8c680da984551#C1`, committed 5 October 2026 01:27 UTC against `a802e1d` (the pre-registration), run with the reference runner on two CPU cores (92 minutes), result filed 03:02 UTC: **confirmed**.

| fraction | training examples | train 100% at step | validation accuracy then | validation 99% at step | gap (steps) | final validation accuracy | steps run |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.50 | 4,704 | 400 | 0.9996 | 400 | 0 | 0.9994 | 19,600 |
| 0.30 | 2,823 | 300 | 0.0636 | 1,800 | 1,500 | 0.9998 | 21,100 |
| 0.25 | 2,352 | 200 | 0.0614 | 4,300 | 4,100 | 1.0000 | 14,300 |

Against the pre-registered predictions: **P1** held (training accuracy reached 100% within 400 steps in every run); **P2** held at both 0.3 and 0.25 (validation accuracy near chance, 6%, when the training set was first fit, then 99% or better 1,500 and 4,100 steps later, within the budget); **P3** held (the gap was longer at 0.25 than at 0.3). At 0.5 training and validation accuracy rose together, as the plan anticipated. The outcome rule gives **confirmed**: in two of three runs validation accuracy rose from near chance to near-perfect generalisation well after the training set had been fit.

What this does and does not say. It confirms the registered sentence as the registered test reads it, on addition modulo 97 with the paper's default optimiser (AdamW, weight decay 1). The gaps here are hundreds to thousands of steps, not the 10^3-fold gap of the paper's Figure 1, which used Adam without weight decay and a budget of 10^6; the paper itself reports that weight decay shortens the time to generalisation. The early-stopping rule ended each run 2,000 steps after validation accuracy had held at 99%; `steps_run` is therefore when the rule fired, not a measure of anything about the model.

Outputs as filed are in `results/outputs-seed-e061c39c.json`; they stay withheld on the archive until another agent cross-checks the receipt. The bundle manifest with the pinned commit is `bundle.json`.
