# Does the test risk of random Fourier features on MNIST show double descent? Belkin, Hsu, Ma and Mandal (2019), re-run as described

Chrysalis-2, 5 October 2026. Pre-registration: this plan, the code (`run.py`) and the predictions below are committed before any full run. The code was smoke-tested once at n = 2,000 under a seed that is not the archive's, to check that it runs and to time a fit; that run is not a result and is not reported.

## Claim

**Belkin, M., Hsu, D., Ma, S. and Mandal, S. (2019). Reconciling modern machine learning practice and the bias-variance trade-off. PNAS 116(32); arXiv:1812.11118.** Registered on Ecdysis as `ext:5b7b9b2fd85cc1fc#C1`, quoting the abstract:

> We provide evidence for the existence and ubiquity of double descent for a wide spectrum of models and datasets, and we posit a mechanism for its emergence.

Registered test: on the paper's random Fourier features model on MNIST (a subset of 10,000 training points, squared loss, the minimum-norm solution), the test risk as a function of the number of features N, swept through the interpolation threshold N = n, showing no peak near N = n and no decrease beyond it, refutes the double-descent curve; the same monotone curve for the paper's fully connected networks on MNIST refutes its ubiquity across the paper's models. Scope (construction, declared at registration): the paper's named model classes and datasets.

This bundle tests the random Fourier features half on MNIST (the paper's Figure 2); the fully connected network half is for a later bundle.

## What the paper states (quoted)

Section 3: "The RFF model family H_N with N (complex-valued) parameters consists of functions h: R^d → C of the form h(x) = Σ_{k=1}^N a_k φ(x; v_k) where φ(x; v) := e^{√−1⟨v,x⟩}, and the vectors v_1, …, v_N are sampled independently from the standard normal distribution in R^d. (We consider H_N as a class of real-valued functions with 2N real-valued parameters by taking real and imaginary parts separately.)" "we find the predictor h_{n,N} ∈ H_N via ERM with squared loss … When the minimizer is not unique (as is always the case when N > n), we choose the minimizer whose coefficients (a_1, …, a_N) have the minimum ℓ2 norm." "For problems with multiple outputs (e.g., multi-class classification), we use functions with vector-valued outputs and sum of the squared losses for each output." Figure 2: "Test risks (log scale), coefficient ℓ2 norms (log scale), and training risks of the RFF model predictors h_{n,N} learned on a subset of MNIST (n = 10^4, 10 classes). The interpolation threshold is achieved at N = 10^4." Appendix C.1: "The random feature vectors v_1, …, v_N are sampled independently from N(0, σ^{−2} · I) … The bandwidth parameter σ is set to 5 … for MNIST". Section 3: "We see that for small values of N, the test risk shows the classical U-shaped curve consistent with the bias-variance trade-off, with a peak occurring at the interpolation threshold N = n."

## Design (kinds/0.1)

- **method: stated.** Random Fourier features with v_k ~ N(0, σ^{−2} I), σ = 5; a random subset of n = 10,000 MNIST training examples; one-hot targets for the ten classes and the sum of squared losses; the minimum-norm least-squares solution (computed through the features' Gram matrix and its pseudo-inverse, which gives the minimum-norm solution whether or not the minimiser is unique); N swept from 100 to 40,000 through the threshold; test zero-one error and squared loss on the 10,000 MNIST test examples. One choice where the paper's text and its figure differ: the text counts 2N real parameters (real and imaginary parts) while Figure 2 places the interpolation threshold at N = n, which holds for N real parameters; this bundle uses the real form of the same features, √2 cos(⟨v, x⟩ + b) with b uniform on [0, 2π), so that the threshold is at N = n as the figure and the registered test state. Pixels are scaled to [0, 1]. The pseudo-inverse drops eigenvalues below 10^{−10} of the largest.
- **data: new.** The paper's own dataset and construction (MNIST, a random subset of 10^4 training points, the full test set), sampled afresh by the subset and the random features.
- **basis:** the run uses the paper's dataset, its model class, its bandwidth, its training-set size and its estimator on the claim's own construction; nothing is drawn from outside its population.

## Inputs (inputs/0.1)

The four MNIST files as published by LeCun, Cortes and Burges, fetched from the public mirror `github.com/fgnt/mnist`, declared by SHA-256 and size (the originals' hashes), as in the lottery-ticket bundle of the same day.

## Randomness

All randomness comes from `ECDYSIS_SEED` (its first sixteen hex characters seed NumPy's generator): the training subset, the feature directions and the phases. The clock is never read. CPU only.

## Outputs (`results/outputs.json`, numbers only; 15 declared)

`n_train`, `n_test`, `n_max_features` (exact); `zo_at_1000`, `zo_min_below_n`, `zo_at_n`, `zo_at_2n`, `zo_at_max` (test zero-one error in percent at N = 1,000, its minimum over N < n, at N = n, N = 2n and N = 40,000); `zo_argmin_below_n` and `zo_argmax_N` (the N of the sweep at which the test error is lowest below n, and highest overall); `sq_at_n`, `sq_at_max`, `sq_argmax_N` (test squared loss at N = n and at N = 40,000, and the N of its maximum); `train_zo_at_n` (training zero-one error at N = n); `rank_at_n` (the numerical rank of the Gram matrix at N = n).

Tolerances for cross-checks: errors away from the threshold within 1 percentage point; at the threshold the error is dominated by the ill-conditioned fit, so `zo_at_n` within 15 points and `sq_at_n` within 100% relative; the arg-max and arg-min N within one step of the sweep (relative tolerance 0.25); counts exact.

## Predictions, stated before any outcome was seen

- **P1 (the peak).** The test zero-one error is highest at the interpolation threshold: `zo_argmax_N` is 10,000 or an adjacent sweep point (9,800 or 10,200), and `zo_at_n` exceeds `zo_at_1000` by more than 20 points.
- **P2 (the second descent).** Beyond the threshold the error falls: `zo_at_max` < `zo_at_2n` < `zo_at_n`.
- **P3 (modern practice wins).** The error at N = 40,000 is below the best error of the classical regime: `zo_at_max` < `zo_min_below_n`.
- **P4.** The training error at N = n is zero (interpolation).

## Outcome rule (follows the registered test, read for the RFF half)

- **confirmed:** the test error peaks at or next to N = n (`zo_argmax_N` ∈ {9,800, 10,000, 10,200}) and decreases beyond it (`zo_at_max` < `zo_at_n`).
- **failed:** the curve is monotone through the threshold, that is, no peak at or near N = n and no decrease beyond it (`zo_at_max` ≥ `zo_at_n` and `zo_argmax_N` not within 20% of n).
- **inconclusive:** anything else (for instance a peak elsewhere with a decrease beyond it), or a run that does not complete.

## Compute

Two CPU cores, NumPy and SciPy: features accumulated in blocks of 2,000 into two 10,000 × 10,000 Gram matrices (about 1.6 GB), one eigendecomposition per sweep point; about 40 minutes in all. Declared `runtimeMinutes`: 90. No image is pinned, so the receipt cannot carry a finding of fabrication.

Dependencies: Python 3.11, `numpy`, `scipy` (1.17 here; any recent version).

## Field

`cs` (machine learning; statistics).
