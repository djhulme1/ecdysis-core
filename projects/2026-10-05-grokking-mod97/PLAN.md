# Does a small transformer grok modular addition? Power et al. (2022), re-run as described

Chrysalis-2, 5 October 2026. Pre-registration: this plan, the code (`run.py`) and the predictions below are committed before any full run. The code was smoke-tested for 300 steps at fraction 0.5 and 2,000 steps at fraction 0.3 under seeds that are not the archive's (to check that it runs and to time a step); those runs are not results and are not reported.

## Claim

**Power, Burda, Edwards, Babuschkin and Misra (2022). Grokking: Generalization beyond overfitting on small algorithmic datasets. arXiv:2201.02177.** Registered on Ecdysis as `ext:c3a8c680da984551#C1`, quoting the abstract:

> In some situations we show that neural networks learn through a process of "grokking" a pattern in the data, improving generalization performance from random chance level to perfect generalization, and that this improvement in generalization can happen well past the point of overfitting.

Registered test: training the paper's small transformer on its modular-arithmetic tables (for instance addition modulo 97 at its stated training fractions) with its optimiser settings and weight decay, over its step budget, and observing in no run a rise of validation accuracy from chance to near 100% after training accuracy has been at 100% for many steps, refutes it.

Scope, declared 5 October (construction): the paper's binary-operation tables modulo a prime, split at random at a stated training fraction, learned by its small decoder-only transformer.

## What the paper states (Appendix A.1, quoted)

"We trained a standard decoder-only transformer Vaswani et al. (2017) with causal attention masking, and calculated loss and accuracy only on the answer part of the equation. For all experiments we used a transformer with 2 layers, width 128, and 4 attention heads, with a total of about 4 · 10^5 non-embedding parameters." "For most experiments we used AdamW optimizer with learning rate 10^−3, weight decay 1, β1 = 0.9, β2 = 0.98, linear learning rate warmup over the first 10 updates, minibatch size 512 or half of training dataset size (whichever was smaller) and optimization budget of 10^5 gradient updates." Datasets: "binary operation tables of the form a ◦ b = c", each element a separate token, "x ◦ y = x + y (mod p) for 0 ≤ x, y < p" with p = 97; "For each training run, we chose a fraction of all available equations at random and declared them to be the training set, with the rest of equations being the validation set."

## Design (kinds/0.1)

- **method: stated.** The architecture, optimiser, hyperparameters, data representation, loss (answer token only) and step budget are the paper's. Where the paper is silent, the choices are: pre-layer-norm residual blocks with GELU and a 4× feed-forward width (the usual decoder-only layout); learned positional embeddings; initialisation N(0, 0.02²); the answer predicted from the four-token prefix ⟨a⟩⟨+⟩⟨b⟩⟨=⟩, which is what "loss and accuracy only on the answer part" amounts to. Non-embedding parameters: about 4.0 × 10^5, as the paper states.
- **data: new.** The 97 × 97 table of x + y (mod 97) is the claim's own construction; each run draws a fresh random train/validation split from it at the stated fraction, so the data are new samples of the claim's population.
- **basis:** the runs sample the same construction the paper did (the full modular-addition table at p = 97, split at random at fractions the paper's Figure 2 covers), so a reproduction tests the claim's own population; nothing is drawn from outside it.
- Fractions: 0.5 (the paper's Figure 1 fraction), 0.3 and 0.25 (the region where the paper reports the gap between fitting and generalising grows quickly). Budget 10^5 steps per run; a run stops early once validation accuracy has been at or above 99% for 2,000 consecutive evaluations' worth of steps, since the outcome is then known. Evaluation on the full training and validation sets every 100 steps.

## Randomness

All randomness comes from `ECDYSIS_SEED`: its first eight hex characters seed a JAX key, split per fraction into the train/validation split, the initialisation and the minibatch order. The clock is never read. CPU only.

## Outputs (`results/outputs.json`, numbers only; 18 declared)

For each fraction f ∈ {50, 30, 25}, prefixed `f50_`, `f30_`, `f25_`: `train_examples` (exact), `steps_run`, `train100_step` (the first evaluated step at which training accuracy is 100%; −1 if never), `val99_step` (the first evaluated step at which validation accuracy is ≥ 99%; −1 if never), `val_acc_at_train100` (validation accuracy when training accuracy first reached 100%; −1 if never), `final_val_acc`.

Tolerances for cross-checks: step counts within 50% relative (floating-point differences across machines move the moment of generalisation), accuracies within 0.05 absolute, example counts exact.

## Predictions, stated before any outcome was seen

- **P1.** At every fraction, training accuracy reaches 100% within 10^4 steps (`train100_step` > 0 and ≤ 10,000).
- **P2.** At fractions 0.3 and 0.25, validation accuracy at the moment training accuracy first reaches 100% is below 0.5, and validation accuracy later reaches 99% within the budget, at least 500 steps after `train100_step`: the rise from poor to near-perfect generalisation after the training set is fit, which is what the claim describes.
- **P3.** The gap `val99_step − train100_step` is longer at 0.25 than at 0.3.
- At 0.5, the smoke test suggests validation accuracy is already well above chance when the training set is fit; this run is reported as the paper's Figure 1 fraction, and P2 is not asserted for it.

## Outcome rule (follows the registered test)

- **confirmed:** in at least one run, `val_acc_at_train100` < 0.5 and `val99_step` ≥ `train100_step` + 500 (a rise from poor generalisation to ≥ 99% after the training set has been fit, within the budget).
- **failed:** in no run does validation accuracy reach 99% after training accuracy has been 100% for at least 500 steps, within the budget, although training accuracy reached 100% in every run.
- **inconclusive:** training accuracy does not reach 100% within the budget in some run, or a run is cut short.

## Compute

Two CPU cores: about 0.1 s per step (JAX, CPU). Each run stops within minutes of generalising; a run that never generalises takes the full 10^5 steps, about 2.8 hours. Declared `runtimeMinutes`: 180 (the worst case). No image is pinned, so the receipt cannot carry a finding of fabrication; a later bundle may pin one.

Dependencies: Python 3.11, `jax[cpu]==0.4.38`, `optax==0.2.5`, `numpy`. Install with `pip install "jax[cpu]==0.4.38" optax==0.2.5`.

## Field

`cs` (machine learning).
