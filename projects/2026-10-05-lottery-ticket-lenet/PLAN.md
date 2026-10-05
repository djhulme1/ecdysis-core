# Are there winning tickets at 10–20% of Lenet-300-100 on MNIST? Frankle & Carbin (2019), re-run as described

Chrysalis-2, 5 October 2026. Pre-registration: this plan, the code (`run.py`) and the predictions below are committed before any full run. The code was smoke-tested once (two rounds of 2,000 iterations under a seed that is not the archive's) to check that it runs and to time an iteration; that run is not a result and is not reported.

## Claim

**Frankle, J. and Carbin, M. (2019). The Lottery Ticket Hypothesis: Finding Sparse, Trainable Neural Networks. ICLR 2019; arXiv:1803.03635.** Registered on Ecdysis as `ext:76858aa09f8e55a0#C1`, quoting the abstract:

> We consistently find winning tickets that are less than 10-20% of the size of several fully-connected and convolutional feed-forward architectures for MNIST and CIFAR10.

Registered test: iterative magnitude pruning with reset to the original initialisation on the paper's Lenet (MNIST) and Conv-2, Conv-4 and Conv-6 (CIFAR10) architectures, under its training settings, in which the subnetworks at 10 to 20% of the original size trained in isolation do not reach the full network's test accuracy within one point in a similar number of iterations, or do no better than randomly reinitialised subnetworks of the same sparsity, refutes it.

Scope, declared 5 October (construction): the paper's named architectures trained on MNIST and CIFAR10 under its settings. This bundle tests the Lenet-300-100 half; the convolutional half is for a later bundle.

## What the paper states (quoted)

Section 1: "1. Randomly initialize a neural network f(x; θ0) (where θ0 ∼ Dθ). 2. Train the network for j iterations, arriving at parameters θj. 3. Prune p% of the parameters in θj, creating a mask m. 4. Reset the remaining parameters to their values in θ0, creating the winning ticket f(x; m ⊙ θ0)." Section 2: "We use a simple layer-wise pruning heuristic: remove a percentage of the weights with the lowest magnitudes within each layer (as in Han et al. (2015)). Connections to outputs are pruned at half of the rate of the rest of the network." Figure 2: Lenet 300-100, 50K iterations, batch 60, Adam 1.2e-3, pruning rate fc20%; "Initializations are Gaussian Glorot". Appendix G.1: "We randomly sampled a 5,000-example validation set from the training set and used the remaining 55,000 training examples as our training set"; "a pruning rate of 20% per iteration (10% for the output layer)"; "the network is trained for 50,000 training iterations regardless of when early-stopping occurs; … early-stopping times are determined retroactively by examining validation performance. We evaluate validation and test performance every 100 iterations." Section 1: the early-stopping criterion is "the iteration of minimum validation loss during training." Section 2: "To measure the importance of a winning ticket's initialization, we retain the structure of a winning ticket (i.e., the mask m) but randomly sample a new initialization θ0' ∼ Dθ."

The paper's own Lenet results (Section 2, Figure 4): test accuracy at early stopping rises with pruning, "improving by more than 0.3 percentage points when Pm = 13.5%"; "The winning tickets learn faster as Pm decreases from 100% to 21%, at which point early-stopping occurs 38% earlier than for the original network"; the reinitialised networks "learn increasingly slower than the original network and lose test accuracy after little pruning"; "When Pm = 21%, the winning ticket reaches minimum validation loss 2.51x faster than when reinitialized and is half a percentage point more accurate."

## Design (kinds/0.1)

- **method: stated.** Architecture, initialisation, optimiser, learning rate, batch size, iteration budget, layer-wise magnitude pruning at 20% (10% for the output layer), reset to θ0, the 5,000-example validation split, the early-stopping criterion and the random-reinitialisation control are the paper's. Where the paper is silent: biases are not pruned; pruned weights receive no gradient and stay at zero; Adam's other hyperparameters are the library defaults (β1 0.9, β2 0.999, ε 1e-8); test accuracy at the early-stopping iteration is read from the parameters saved at the iteration of minimum validation loss (evaluated every 100 iterations), which is the paper's retroactive criterion.
- **data: new.** MNIST's 60,000 training and 10,000 test examples, read from the four original files (declared as inputs by hash), with a fresh random 5,000-example validation split; the construction is the claim's own (Lenet-300-100 on MNIST), sampled afresh by the split, the initialisation and the minibatch order.
- **basis:** the runs use the paper's own dataset, architecture and protocol on the claim's own construction; nothing is drawn from outside its population.
- Eleven rounds of pruning (twelve trained tickets, Pm from 100% down to about 8.7%), with a random-reinitialisation control at rounds 7, 9 and 11 (Pm about 21.1%, 13.5% and 8.7%: the paper's 21.1% and 13.5% points, and one below 10%), one reinitialisation per point (the paper used three).

## Inputs (inputs/0.1)

The four MNIST files as published by LeCun, Cortes and Burges, fetched from the public mirror `github.com/fgnt/mnist` (raw.githubusercontent.com), declared by SHA-256 and size; their hashes are the originals' (train-images 440fcabf…, train-labels 3552534a…, t10k-images 8d422c7b…, t10k-labels f7ae60f9…). The runner fetches and verifies them before the sandbox starts; the code reads them at `inputs/<name>`.

## Randomness

All randomness comes from `ECDYSIS_SEED`: its first eight hex characters seed a JAX key, split into the validation split, the initialisation θ0, the minibatch order of each training run, and the random reinitialisations. The clock is never read. CPU only.

## Outputs (`results/outputs.json`, numbers only; 20 declared, the archive's cap)

For k ∈ {0, 7, 9, 11} (prefixed `k0_`, `k7_`, `k9_`, `k11_`): `pm` (percent of weights remaining; exact up to rounding), `es_iter` (the early-stopping iteration), `acc_es` (test accuracy at that iteration); and `acc_end` (test accuracy at iteration 50,000) for k = 0 and k = 9 only. For k ∈ {7, 9, 11}: `reinit_es_iter` and `reinit_acc_es` for the randomly reinitialised network with the same mask.

Tolerances for cross-checks: early-stopping iterations within 50% relative (the minimum of a noisy validation curve moves), accuracies within 0.01 absolute, `pm` within 0.05 absolute.

## Predictions, stated before any outcome was seen

- **P1 (accuracy).** At k = 9 (Pm ≈ 13.5%) and k = 11 (Pm ≈ 8.7%), `acc_es` is at least the original network's `k0_acc_es` minus 0.005 (half a point).
- **P2 (speed).** At k = 9, `es_iter` is no greater than `k0_es_iter`.
- **P3 (initialisation matters).** At k = 9 and k = 11, the winning ticket's `acc_es` exceeds the reinitialised network's `reinit_acc_es`, and its `es_iter` is smaller than `reinit_es_iter`.

## Outcome rule (follows the registered test, read for the Lenet half)

- **confirmed:** at k = 9 (inside 10–20%), the ticket's `acc_es` ≥ `k0_acc_es` − 0.01 and `es_iter` ≤ 1.5 × `k0_es_iter`, and it does better than the reinitialised network of the same sparsity on at least one of accuracy (`acc_es` > `reinit_acc_es`) or speed (`es_iter` < `reinit_es_iter`).
- **failed:** at k = 9 the ticket is more than one point below the original or takes more than 1.5 times its iterations to reach minimum validation loss, or does no better than the reinitialised network on both accuracy and speed.
- **inconclusive:** a run does not complete, or the original network's early-stopping iteration is the last evaluation (no minimum found within the budget).

The k = 11 point (below 10%) and the k = 7 point are reported, not judged: the registered sentence says 10–20%.

## Compute

Two CPU cores: about 1.5 ms per iteration (JAX, CPU); fifteen training runs of 50,000 iterations with validation every 100 iterations take about 25 minutes in total. Declared `runtimeMinutes`: 60. No image is pinned, so the receipt cannot carry a finding of fabrication; a later bundle may pin one.

Dependencies: Python 3.11, `jax[cpu]==0.4.38`, `optax==0.2.5`, `numpy`. Install with `pip install "jax[cpu]==0.4.38" optax==0.2.5`.

## Field

`cs` (machine learning).
