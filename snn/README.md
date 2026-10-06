# snn: surrogate-gradient shape and scale, after Zenke & Vogels (2021)

`snn_surrogate.py` is our own reproduction of the comparison behind Zenke &
Vogels, "The remarkable robustness of surrogate gradient learning for
instilling complex function in spiking neural networks" (Neural Computation
33(4), 2021). The claim under test: surrogate gradient learning "is robust
to different shapes of underlying surrogate derivatives, but the choice of
the derivative's scale can substantially affect learning performance".

What runs, on the paper's 10-class Randman spike-timing task (one hidden
layer of 100 current-based LIF neurons, 100 steps of 1 ms, max-over-time
readout, Adam), with every parameter cited to the paper or to the authors'
released code (read as data; randman is re-implemented, not copied):

- **Shape (Fig. 3b-c):** SuperSpike, Sigmoid' and Esser surrogates, each
  over the paper's grid of slopes β, with the reset detached.
  `shape_spread` is the spread of the shapes' best test accuracies.
- **Scale (Fig. 5):** the asymptotic SuperSpike β/(β|x|+1)², whose magnitude
  grows with β, where the paper shows scale mattering: a differentiable reset
  (aDR) and recurrent connections that pass gradients (aProp), with the
  normalised controls sDR and sProp. `magnitude_scale_spread` is the spread
  of aDR's test accuracy over β.
- `test_passed` is 1 when `shape_spread` < `magnitude_scale_spread`, the
  registered test's condition.
- Controls: no learning, the true (zero) gradient, and a constant surrogate.

Randomness comes only from `ECDYSIS_SEED` (SHA-256 per stream); every run is
single-threaded, and two invocations under one seed give identical outputs on
one machine. Floating-point results can differ across CPU types, so the
receipt declares tolerances on the accuracies.

Known differences from the paper:

- one replicate (the paper's Fig. 3b protocol fixes data and initialisation);
- fewer learning rates: 0.02, 0.05 and 0.1 (the others were never best);
- Fig. 5 at 100 epochs rather than 200;
- no deeper networks (Fig. 5d, 5f);
- per-β accuracy rather than the paper's mean of the ten best grid cells;
- Randman's spectrum follows the paper's printed formula, which differs
  from the released generator's default (`--randman-spectrum code` selects
  that one).

Our aDR reaches 0.95-0.99 at β = 1-5, where the paper's ten best aDR cells
average about 0.78; restricted to β ≥ 10 it ranges 0.53-0.87.

Run (the job takes about 80 minutes on 2 CPUs; `--trial` about a minute):

    env -i ECDYSIS_SEED=<64 hex> HOME=/tmp /usr/bin/python3 snn/snn_surrogate.py

in `pytorch/pytorch@sha256:c4ab67f95221a342dff0e8ca4543a7b8885f79f7a0029c0e2e39685d5eaf1722`
(torch 2.14.1, CPU). Tests: `cd snn && python3 -m unittest -v test_snn_surrogate`.
