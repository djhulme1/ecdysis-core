# Yin-Yang benchmark: do its ANN baselines replicate, and is surrogate-gradient SNN training on it robust to the surrogate's shape?

Area: snn (spiking neural networks). Kind: assessment. Field label: **neuro**.
Pre-registered: this file's commit time on chrysalis-lab is the pre-registration. No results have been looked at.

## Question

The Yin-Yang dataset is a small, procedurally generated benchmark built for spiking networks and neuromorphic hardware. Its value as a benchmark rests on its published baselines: that it is learnable by a small deep network but not by a linear (shallow) classifier, with a gap of more than 30 percentage points. (1) Do those baselines replicate from the published data and hyperparameters? (2) A widely cited review claims surrogate-gradient learning does not depend crucially on the surrogate's shape. On this benchmark, with a fixed small LIF network, does test accuracy stay within a few points across surrogate shapes?

## Parents (each opened on 2026-10-02 with the web fetch tool)

1. **arxiv:2102.08211**, L. Kriener, J. Göltz, M. A. Petrovici, "The Yin-Yang dataset". Claims tested (quoted verbatim from the PDF):
   - Table 1 (caption: "Mean and standard deviation of the test accuracy for 20 training runs with different random initializations for different network configurations"): "deep network | $(97.0 \pm 1.6) \%$" (20 hidden), "deep network | $(97.6 \pm 1.5)\%$" (30 hidden), "deep network (frozen lower weights) | $(78.3 \pm 7.8) \%$" (20), "deep network (frozen lower weights) | $(85.5 \pm 5.8) \%$" (30), "shallow network | $(63.8 \pm 1.0) \%$".
   - "both the shallow network and the one with the frozen lower weights are clearly unable to learn the required features to successfully classify the dataset. This leads to a gap of more than $30\,\%$"
   - "even 10 hidden units are enough to achieve results (around 88% accuracy)"
   - Table 2 hyperparameters: "activation function: ReLU, size input: 4, size hidden layer (for deep net): 30, size output layer: 3, training epochs: 300, batch size: 20, optimizer: Adam, learning rate: 0.01".
   - Dataset: "In the default configuration the training set has 5000 samples while the validation and test sets have 1000 samples respectively".
2. **arxiv:1901.09948**, E. O. Neftci, H. Mostafa, F. Zenke, "Surrogate Gradient Learning in Spiking Neural Networks". Claim tested (verbatim): "While a more systematic comparison of different surrogate nonlinearities is still pending, overall the diversity found in the present literature suggests that the success of the method is not crucially dependent on the details of the surrogate used to approximate the derivative."
3. Background: **arxiv:2009.08378**, Wunderlich & Pehle, EventProp: reports "$(98.1 \pm 0.2)$ %" on Yin-Yang with a spiking network over 10 seeds; used only as a reference point for what a spiking network can reach, not tested.

Data: the authors' published split, https://github.com/lkriener/yin_yang_data_set at commit e6eef9617b1dbd30d1f01508d462275747ae45b1, `publication_data/` (train 5000, validation 1000, test 1000; inputs $(x, y, 1-x, 1-y)$, 3 classes).

## Method

### Arm A: ANN baselines (replication of parent 1)
- PyTorch, CPU. Adam, lr 0.01, batch 20, 300 epochs, ReLU hidden layer, softmax cross-entropy loss (the loss is not stated in the parent: an assumption, recorded as such). PyTorch default initialisation.
- Configurations: shallow (4→3, no hidden layer); deep with 10, 20, 30 hidden; frozen lower weights with 20 and 30 hidden (input→hidden weights and biases left at their random initialisation, only hidden→output trained).
- 20 seeds (0–19) per configuration, as in the parent. Primary metric: test accuracy after the final epoch. Secondary: test accuracy at the epoch with best validation accuracy (the parent does not say which it used).

### Arm B: surrogate shapes (test of parent 2)
- Network: 4 inputs → 120 current-based LIF hidden neurons → 3 non-spiking leaky readout neurons; class = argmax over time of readout membrane potential; cross-entropy on those maxima. Inputs encoded as constant currents scaled by the input value plus a bias input, over T = 40 time steps (dt = 1 ms, membrane time constant 10 ms, synaptic 5 ms, threshold 1, reset by subtraction). Backpropagation through time, spikes detached in the reset path.
- Surrogate derivatives of the Heaviside spike function at $u = v - 1$, with steepness $\beta$:
  - fast sigmoid (SuperSpike): $1/(\beta|u|+1)^2$
  - sigmoid derivative: $4\sigma(\beta u)(1-\sigma(\beta u))$ (scaled to peak 1)
  - triangle (piecewise linear): $\max(0, 1-\beta|u|)$
  - exponential: $\exp(-\beta|u|)$
  Each normalised to peak height 1, so shapes differ but peak gain does not.
- $\beta \in \{2, 5, 10, 25\}$ (four steepnesses), 5 seeds each: 4 × 4 × 5 = 80 runs. Adam, lr 2e-3, batch 100, 60 epochs. Test accuracy at the final epoch.
- Hyperparameters (lr, epochs, time constants) are fixed here before any run and not tuned per shape.

## Predictions and falsification

Arm A (parent 1), each configuration separately:
- P1. Replicates if our 20-seed mean lies within the parent's mean ± 1 parent SD. Also reported: Welch t-test of our mean against the parent's mean and SD (n = 20 each), $\alpha$ = 0.05, as a stricter check.
- P2. The deep(30) − shallow gap exceeds 30 pp (95% CI lower bound above 30). Falsified if the CI lower bound is ≤ 30.
- P3. Deep(10) mean in [85, 91] % ("around 88%"). Falsified outside that band.
- Expectation before running: P1 holds for shallow and deep; frozen-weight rows have large variance and depend on initialisation scale, so they may not.

Arm B (parent 2):
- P4. At each $\beta$, the spread of mean test accuracy across the four shapes (max minus min of 5-seed means) is ≤ 3 pp, for every $\beta$ at which the best shape reaches ≥ 90%. Falsified if at any such $\beta$ the spread exceeds 3 pp and the worst and best shapes' 95% bootstrap CIs (over seeds) do not overlap.
- P5 (exploratory, no direction asserted): how accuracy varies with $\beta$ within each shape. Reported, not used to judge parent 2, which makes no claim about scale.

## Compute plan
One CPU core. Arm A: 6 configurations × 20 seeds × 75,000 steps, expected ≤ 25 min. Arm B: 80 runs, expected 15–25 min. Run 1: Arm A. Run 2: Arm B. Then analysis, draft, review, re-run. Outputs to results/ as CSV; no large files.

## Limitations stated in advance
The parent's loss, initialisation and epoch-selection rule are not stated; a mismatch could be ours. Arm B tests one architecture on one small dataset: it can falsify "not crucially dependent" for this setting, and cannot establish it in general.
