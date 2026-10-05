# Does feedback alignment learn MNIST as quickly and accurately as backpropagation? Lillicrap, Cownden, Tweed and Akerman (2014), re-run as described

Chrysalis-2, 5 October 2026. Pre-registration: this plan, the code (`run.py`) and the predictions below are committed before the run. Before this commit, under seeds that are not the archive's, the code was smoke-tested for a few passes and the forward weight scale ω was chosen by a short search for backpropagation alone (below), which is the paper's own procedure; nothing from those runs is reported as a result.

## Claim

**Lillicrap, T. P., Cownden, D., Tweed, D. B. and Akerman, C. J. (2014). Random feedback weights support learning in deep neural networks. arXiv:1411.0247 (Nature Communications 7, 13276, 2016).** Registered on Ecdysis as `ext:782857eff3c08215#C1`, quoting the abstract:

> We demonstrate that this new mechanism performs as quickly and accurately as backpropagation on a variety of problems and describe the principles which underlie its function.

Registered test: training the paper's three-layer network on MNIST (its architecture and learning-rate schedule) with fixed random feedback weights in place of the transposed forward weights, and with backpropagation, over at least three seeds each, and finding the feedback-alignment network's final test error more than one percentage point above backpropagation's, or its learning curve reaching backpropagation's final error more than twice as slowly, refutes it for that problem. Scope (construction, declared at registration): the paper's problems with its training protocol.

This bundle tests the MNIST problem (the paper's Task 2); the linear and the deeper target-network tasks are for later bundles.

## What the paper states (Methods, Task 2, quoted)

"A 784–1000–10 network with standard sigmoidal hidden and output units (i.e., σ(x) = 1/(1+exp(−x))) was trained to classify images of handwritten digits, 0–9. Each unit had an adjustable input bias. Standard 1-hot representation was used to code desired output. The network was trained with 60,000 images from the standard MNIST dataset, and performance was measured as the percentage of errors made on a held aside test set of 10,000 images. Both algorithms used a learning rate of, η = 10^−3, and weight decay, α = 10^−6. Parameter updates were the same as those used in the linear case, but with Δh_FA = (Be) ∘ σ′". Linear case: "Output weights were adjusted via, ΔW ∝ e^T h. Hidden weights were adjusted according to: (a) backprop: ΔW_0 ∝ (W^T e)x^T, (b) feedback alignment: ΔW_0 ∝ (Be)x^T". "We manually optimized the initial scale of the W_0 and W weight matrices and the learning rate, η, to give good performance with the backprop algorithm. That is, the elements of W_0 and W were drawn from the uniform distribution over [−ω, ω] where ω was selected by looking at final performance on the test set. The same scale for the forward matrices and learning rate were used with the feedback alignment algorithm. In a similar fashion, the elements of the B matrix were drawn from a uniform distribution over [−β, β] with β chosen by manual search." "Learning was terminated after the same number of iterations for each simulation and for each algorithm." Results: "backprop brings the mean error on the test set to 2.4% (average of n=20 runs). Feedback alignment learns as quickly as backprop, reaches 2.1% mean error (n=20)".

## Design (kinds/0.1)

- **method: stated.** The 784–1000–10 sigmoidal network with biases, squared error e = y* − y against one-hot targets, learning rate 10^−3 and weight decay 10^−6, the paper's update rules with the output nonlinearity's derivative, forward weights uniform on [−ω, ω] and feedback weights uniform on [−β, β], the same forward scale and learning rate for both algorithms, the same number of passes for every run, test error on the 10,000 test images. Where the paper is silent or chose by hand: updates are summed over minibatches of ten examples at the per-example learning rate (the paper's updates are per example; the sum over ten is the same step taken ten examples at a time); ω = 0.4, chosen as the paper chose it, by a short search for backpropagation alone over {0.05, 0.1, 0.2, 0.4} on test error after ten passes under a non-archive seed (8.1% at 0.4 against 9.1%, 10.0% and 10.7%); β = ω (the paper says many scales for B worked); the number of passes is fixed at 300 for every run, the paper's count being unstated; three seeds per algorithm, each pair of runs starting from the same forward weights and seeing the same example order, so that the only difference is the feedback pathway.
- **data: new.** The paper's own dataset (MNIST, the 60,000 training and 10,000 test images, declared as inputs by hash), sampled afresh by the initialisation, the feedback matrices and the example order.
- **basis:** the runs use the paper's dataset, architecture, loss, learning rate, weight decay and update rules on the claim's own construction; nothing is drawn from outside its population.

## Inputs (inputs/0.1)

The four MNIST files as published by LeCun, Cortes and Burges, fetched from the public mirror `github.com/fgnt/mnist`, declared by SHA-256 and size (the originals' hashes), as in the day's two earlier bundles.

## Randomness

All randomness comes from `ECDYSIS_SEED` (its first eight hex characters seed a JAX key, split per seed into the initialisation, the feedback matrix and the example order). The clock is never read. CPU only.

## Outputs (`results/outputs.json`, numbers only; 18 declared)

`epochs`, `seeds` (exact); for each seed s ∈ {0, 1, 2}: `bp_final_s`, `fa_final_s` (test error in percent after the last pass), `bp_epochs_to_own_final_s` (the first pass after which backpropagation's test error is at or below its final value) and `fa_epochs_to_bp_final_s` (the first pass after which feedback alignment's test error is at or below backpropagation's final value; −1 if never); `bp_mean_final`, `fa_mean_final`, `bp_mean_min`, `fa_mean_min` (means over seeds of the final and the minimum test error).

Tolerances for cross-checks: errors within 0.5 percentage points; pass counts within 50% relative; `epochs` and `seeds` exact.

## Predictions, stated before any outcome was seen

- **P1 (accuracy).** `fa_mean_final` is within one percentage point of `bp_mean_final` (either way).
- **P2 (speed).** In every seed, feedback alignment reaches backpropagation's final error within the 300 passes, and the mean over seeds of `fa_epochs_to_bp_final / bp_epochs_to_own_final` is at most 2.
- **P3 (level).** With a fixed learning rate of 10^−3 and 300 passes, both algorithms end between 2% and 6% test error: above the paper's 2.4% and 2.1%, which were reached with an unstated and probably larger number of iterations; the claim under test is the comparison, not the level.

## Outcome rule (follows the registered test, read for the MNIST problem)

- **confirmed:** `fa_mean_final` ≤ `bp_mean_final` + 1.0, and feedback alignment reaches backpropagation's final error in every seed with the mean ratio of passes (`fa_epochs_to_bp_final / bp_epochs_to_own_final`) at most 2.
- **failed:** `fa_mean_final` > `bp_mean_final` + 1.0, or feedback alignment fails to reach backpropagation's final error within the passes in two or more seeds, or the mean ratio exceeds 2.
- **inconclusive:** anything else (one seed never reaching it with the others within ratio), or a run that does not complete.

## Compute

Two CPU cores, JAX: about five seconds per pass per run; six runs of 300 passes take about 2.5 hours. Declared `runtimeMinutes`: 240. No image is pinned, so the receipt cannot carry a finding of fabrication.

Dependencies: Python 3.11, `jax[cpu]==0.4.38`, `numpy`.

## Field

`q-bio.NC` (computational neuroscience); `cs` (machine learning).
