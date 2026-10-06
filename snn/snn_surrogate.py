#!/usr/bin/env python3
"""snn_surrogate.py -- independent reproduction of the surrogate-derivative
shape x steepness comparison in

    F. Zenke and T. P. Vogels (2021). The remarkable robustness of surrogate
    gradient learning for instilling complex function in spiking neural
    networks. Neural Computation 33(4):899-925. doi:10.1162/neco_a_01367
    (bioRxiv doi:10.1101/2020.06.29.176925).

What is reproduced, on the 10-class Randman spike-timing task:
  * Section 2.2 / Figure 3b-c (shape): a feedforward network with one hidden
    layer of current-based LIF neurons, detached reset, trained with each of
    three normalised surrogate derivatives (SuperSpike, Sigmoid', Esser et al.)
    over the grid of slope parameters beta read from Figure 3b;
  * Section 2.3 / Figure 5 (scale = magnitude): the asymptotic SuperSpike
    beta/(beta|x|+1)^2, whose peak grows with beta, over the same beta grid, in
    the two settings where the paper shows the scale mattering: a differentiable
    reset ("aDR", Fig. 5b-c) and recurrent connections that pass gradients
    ("aProp", Fig. 5e); plus the normalised-scale controls sDR and sProp.

This is our own code.  Its semantics follow the paper's Methods (Section 4,
Table 1) and, where the paper is silent, the authors' released code, read as
data: fzenke/randman (MIT licence; the data generator is re-implemented here,
not copied), fmi-basel/stork and fzenke/spytorch.  Sources are cited inline as
"paper Sec. x" or "file:line".  Where paper and code disagree we follow the
paper: the Randman power spectrum is the one printed in Sec. 4.1.1, not the one
in randman's default TorchRandman backend (--randman-spectrum code selects it).

Randomness: every random number comes from the 64-hex-digit seed in the
environment variable ECDYSIS_SEED, through SHA-256(seed || "|" || label) for a
fixed label per stream (data set, weights, minibatch order).  Nothing else is
used: no clock, no /dev/urandom, no global RNG.  Each process runs
single-threaded; runs are pure functions of (seed, configuration), so results
do not depend on how the two worker processes are scheduled.

Outputs: results/outputs.json (flat, at most 20 entries), results/runs.json
(every run; deterministic) and results/timing.json (wall-clock times; not
deterministic).  Progress goes to stderr only; nothing is printed to stdout.
"""

import os

for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import multiprocessing  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

import torch  # noqa: E402

DTYPE = torch.float32

# ---------------------------------------------------------------------------
# Specification.  Every value carries its source.
# ---------------------------------------------------------------------------
SPEC = {
    # Randman data set (paper Sec. 4.1.1 and Table 1, Randman column).
    "nb_classes": 10,            # Sec. 4.1.1 "a 10-way problem"; Table 1: 10 readout units
    "nb_inputs": 20,             # Sec. 4.1.1 "M = 20"; Table 1: 20 input units
    "dim_manifold": 1,           # Sec. 4.1.1 "D = alpha = 1"
    "alpha": 1.0,                # Sec. 4.1.1 "D = alpha = 1"
    "tau_randman": 50e-3,        # Sec. 4.1.1 "tau_randman = 50 ms"
    "samples_per_class": 1000,   # Sec. 4.1.1 "we generated 1000 data points for each class"
    "split_per_class": (800, 100, 100),  # Sec. 4.1.1 "800 for training and two sets of 100 each"
    "randman_prec": 1e-3,        # randman/torch_randman.py:17 (prec=1e-3)
    "randman_max_f_cutoff": 1000,  # Sec. 4.1.1 "n_cutoff = 1000"; torch_randman.py:17,34
    "randman_spectrum": "paper",   # Sec. 4.1.1 formula (k^-alpha at frequency k); "code" =
                                   # released TorchRandman spectrum (see randman_frequencies)
    # Network (paper Sec. 4.2 and Table 1).
    "dt": 1e-3,                  # Table 1 "1ms / 100"
    "nb_steps": 100,             # Table 1 "1ms / 100"
    "nb_hidden": 100,            # Table 1 "Number of hidden units 100"
    "tau_mem": 10e-3,            # Sec. 4.2.1 "tau_mem = 10 ms"
    "tau_syn": 5e-3,             # Sec. 4.2.1 "tau_syn = 5 ms"
    "tau_readout": 20e-3,        # Sec. 4.2.2 "tau_readout = 20 ms"
    # Training (paper Sec. 4.2.5-4.2.6 and Table 1).
    "batch_size": 250,           # Table 1 "Minibatch size 128, 250"
    "epochs": 50,                # Table 1 "Number of epochs 50-100" (lower end)
    "lower_l2_strength": 100.0,  # Table 1 "Lower L2: lambda_lower / nu_lower 100.0/10^-3"
    "lower_l2_threshold": 1e-3,  # Table 1, idem; Sec. 4.2.5 g_lower
    # Sweep, read from the grid points plotted in Fig. 3b (log-axes 1e-1..1e3
    # for beta, 1e-3..1e-1 for eta), consistent with Table 1 "Learning rate
    # sweep 10^-3 <= eta <= 0.1" and "Best eta 0.05".
    "betas": (0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 500.0, 1000.0),
    "etas_fig3b": (1e-3, 5e-3, 1e-2, 2e-2, 5e-2, 1e-1),   # all eta grid points of Fig. 3b
    # Used (cut to fit 2 h on 2 CPUs): the eta values that are best somewhere in
    # Fig. 3b (darkest regions at eta ~0.02-0.1; Table 1 "Best eta 0.05").  In our
    # full 6-eta run (seed 112e9b41...) 1e-3, 5e-3 and 1e-2 were never selected.
    "etas": (2e-2, 5e-2, 1e-1),
    "shapes": ("superspike", "sigmoid", "esser"),  # Sec. 4.2.6; Fig. 3a
    "default_shape": "superspike",  # Sec. 4.2.6 "Unless mentioned otherwise, we set beta = 10" (SuperSpike)
    # Fig. 5: the scale (magnitude) of the surrogate derivative, Sec. 2.3.
    "fig5_shape": "asymptotic",     # Sec. 4.2.6 h(x) = beta/(beta|x| + 1)^2; Fig. 5a (peak = beta)
    "fig5_betas": (0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 500.0, 1000.0),
                                    # Fig. 5 caption (b): "grid search over beta and the
                                    # learning rate eta (cf. Figure 3)": the Fig. 3b grid
    "fig5_etas": (2e-2, 5e-2, 1e-1),  # as Fig. 3 (cut as above); aDR, sDR
    "fig5_rec_etas": (2e-2,),       # recurrent runs: one eta (cut, cost)
    "fig5_epochs": 100,             # Table 1 maximum for Randman; Fig. 5b plots 200 (cut)
    "fig5_control_beta": 10.0,      # normalised-scale controls sDR, sProp at the default beta
    "true_gradient_eta": 5e-2,      # Table 1 "Best eta 0.05"
}

SHAPES_ALL = ("superspike", "sigmoid", "esser", "zero", "asymptotic")


# ---------------------------------------------------------------------------
# Seeds.
# ---------------------------------------------------------------------------
def read_master_seed():
    """The 32 bytes of ECDYSIS_SEED (64 hexadecimal characters)."""
    text = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", text):
        raise SystemExit("ECDYSIS_SEED must be set to 64 hexadecimal characters")
    return bytes.fromhex(text)


def derived_seed(master, label):
    """64-bit seed: the first 8 bytes of SHA-256(master || '|' || label)."""
    digest = hashlib.sha256(master + b"|" + label.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "little")


def make_generator(master, label):
    gen = torch.Generator(device="cpu")
    gen.manual_seed(derived_seed(master, label))
    return gen


# ---------------------------------------------------------------------------
# Surrogate derivatives h(x), x = U - 1 (paper Sec. 4.2.6).
# ---------------------------------------------------------------------------
def surrogate(x, shape, beta):
    """h(x) for a tensor x (not modified)."""
    if shape == "superspike":      # h(x) = 1/(beta|x| + 1)^2
        return (x.abs() * beta + 1.0).reciprocal_().square_()
    if shape == "sigmoid":         # h(x) = s(x)(1 - s(x)), s(x) = 1/(1 + exp(-beta x))
        s = torch.sigmoid(x * beta)
        return s.addcmul_(s, s, value=-1.0)
    if shape == "esser":           # h(x) = max(0, 1 - beta|x|)
        return (x.abs() * (-beta)).add_(1.0).clamp_(min=0.0)
    if shape == "zero":            # derivative of the Heaviside step (a.e.): no surrogate
        return torch.zeros_like(x)
    if shape == "asymptotic":      # Sec. 4.2.6, used in Fig. 5 only: beta/(beta|x|+1)^2
        return (x.abs() * beta + 1.0).reciprocal_().square_().mul_(beta)
    raise ValueError("unknown surrogate shape %r" % (shape,))


def surrogate_primitive(x, shape, beta):
    """A smooth H with H' = h.  Used only to test gradients by finite differences."""
    if shape == "superspike":
        return x / (x.abs() * beta + 1.0)
    if shape == "sigmoid":
        if beta == 0:
            return 0.25 * x
        return torch.sigmoid(x * beta) / beta
    if shape == "esser":
        if beta == 0:
            return x.clone()
        c = x.clamp(-1.0 / beta, 1.0 / beta)
        return c - 0.5 * beta * c * c.abs()
    if shape == "zero":
        return torch.zeros_like(x)
    if shape == "asymptotic":
        return beta * x / (x.abs() * beta + 1.0)
    raise ValueError("unknown surrogate shape %r" % (shape,))


def heaviside_(x):
    """In place: 1 where x > 0, else 0 (Theta(0) = 0 as in stork activations.py:24)."""
    return x.sign_().clamp_(min=0.0)


def surrogate_of_u(u, shape, beta, out):
    """h(u - 1) written into `out` (same values as surrogate(u - 1, ...))."""
    if shape == "superspike":
        return torch.sub(u, 1.0, out=out).abs_().mul_(beta).add_(1.0).reciprocal_().square_()
    if shape == "sigmoid":
        torch.sub(u, 1.0, out=out).mul_(beta).sigmoid_()
        return out.addcmul_(out, out, value=-1.0)
    if shape == "esser":
        return torch.sub(u, 1.0, out=out).abs_().mul_(-beta).add_(1.0).clamp_(min=0.0)
    if shape == "zero":
        return out.zero_()
    if shape == "asymptotic":
        return torch.sub(u, 1.0, out=out).abs_().mul_(beta).add_(1.0).reciprocal_().square_().mul_(beta)
    raise ValueError("unknown surrogate shape %r" % (shape,))


# ---------------------------------------------------------------------------
# Randman.  Smooth random manifolds (paper Sec. 4.1.1) and the spike-latency
# data set built from them as in stork/datasets.py:171-281 (make_tempo_randman,
# nb_spikes=1).  Two power spectra are available:
#   "paper" (default): the formula printed in the paper, Sec. 4.1.1,
#       f_i(x) = prod_j sum_{k=1}^{n_cutoff} k^-alpha A_ijk sin(2 pi (k x_j B_ijk + C_ijk)),
#       n_cutoff = 1000;
#   "code": the released fzenke/randman default backend (Randman = TorchRandman,
#       randman/__init__.py:15; torch_randman.py:34-71, unchanged since April
#       2019): frequency i = 0..F-1 with weight 1/((i+1)^alpha + 1) and A_0 = 0,
#       F = min(ceil(prec^(-1/alpha)), 1000).
# Both are re-implemented here (randman is MIT-licensed; no code is copied).
# ---------------------------------------------------------------------------
def randman_frequencies(f_cutoff, alpha, spectrum):
    """(frequency multipliers k, amplitude weights s_k) for one Fourier series."""
    if spectrum == "paper":
        k = torch.arange(1, f_cutoff + 1, dtype=torch.float64)
        return k, k ** (-alpha)
    if spectrum == "code":
        i = torch.arange(f_cutoff, dtype=torch.float64)
        return i, 1.0 / ((i + 1.0) ** alpha + 1.0)
    raise ValueError("unknown randman spectrum %r" % (spectrum,))


def randman_embedding(theta, x, alpha, spectrum):
    """f(x) for parameters theta (M, D, 3, F) and points x (N, D) -> (N, M)."""
    M, D, _, F = theta.shape
    freq, spect = randman_frequencies(F, alpha, spectrum)
    y = torch.ones(x.shape[0], M, dtype=torch.float64)
    two_pi = 2.0 * math.pi
    for d in range(D):
        xd = x[:, d:d + 1]
        for m in range(M):
            phase = (xd * (freq * theta[m, d, 1]) + theta[m, d, 2]) * two_pi
            y[:, m] *= torch.sin(phase) @ (theta[m, d, 0] * spect)
    return y


def randman_spike_times(gen_params, gen_coords, nb_units, dim_manifold, alpha,
                        nb_samples, nb_steps, step_frac, prec=1e-3, max_f_cutoff=1000,
                        spectrum="paper"):
    """Spike-time bins (nb_samples x nb_units, int64) for one class.

    A, B, C ~ U(0,1) i.i.d. (Sec. 4.1.1; torch_randman.py:50); points x ~ U(0,1)^D;
    each embedding coordinate is min-max standardised over the class's samples to
    [0,1) (stork/datasets.py:29-32; Sec. 4.1.1 "standardized ... to lie between 0
    and tau_randman") and becomes the single spike time of one input neuron, in
    bins of nb_steps*step_frac (stork/datasets.py:267-271; integer truncation).
    """
    f_cutoff = int(min(math.ceil(prec ** (-1.0 / alpha)), max_f_cutoff))
    theta = torch.rand(nb_units, dim_manifold, 3, f_cutoff, generator=gen_params,
                       dtype=torch.float64)
    if spectrum == "code":
        theta[:, :, 0, 0] = 0.0       # use_bias=False, torch_randman.py:51-52
    x = torch.rand(nb_samples, dim_manifold, generator=gen_coords, dtype=torch.float64)
    y = randman_embedding(theta, x, alpha, spectrum)
    lo = y.min(0).values
    hi = y.max(0).values
    y = (y - lo) / (hi - lo + 1e-7)
    return (nb_steps * step_frac * y).to(torch.int64)


def make_dataset(master, rep, spec):
    """Train/validation/test spike-time arrays for replicate `rep`."""
    nb_steps = spec["nb_steps"]
    step_frac = spec["tau_randman"] / (spec["dt"] * nb_steps)
    n_tr, n_va, n_te = spec["split_per_class"]
    parts = {"train": ([], []), "valid": ([], []), "test": ([], [])}
    for c in range(spec["nb_classes"]):
        times = randman_spike_times(
            make_generator(master, "rep%d/randman/class%d/params" % (rep, c)),
            make_generator(master, "rep%d/randman/class%d/coords" % (rep, c)),
            spec["nb_inputs"], spec["dim_manifold"], spec["alpha"],
            spec["samples_per_class"], nb_steps, step_frac,
            spec["randman_prec"], spec["randman_max_f_cutoff"], spec["randman_spectrum"])
        bounds = {"train": (0, n_tr), "valid": (n_tr, n_tr + n_va),
                  "test": (n_tr + n_va, n_tr + n_va + n_te)}
        for name, (a, b) in bounds.items():
            parts[name][0].append(times[a:b])
            parts[name][1].append(torch.full((b - a,), c, dtype=torch.int64))
    return {name: (torch.cat(xs), torch.cat(ys)) for name, (xs, ys) in parts.items()}


def init_weights(master, rep, nb_inputs, nb_hidden, nb_out):
    """U(-sqrt(k), sqrt(k)), k = 1/n_inputs, no biases (paper Sec. 4.2.3)."""
    gen = make_generator(master, "rep%d/init" % rep)
    w1 = (torch.rand(nb_inputs, nb_hidden, generator=gen, dtype=torch.float64) * 2 - 1)
    w1 /= math.sqrt(nb_inputs)
    w2 = (torch.rand(nb_hidden, nb_out, generator=gen, dtype=torch.float64) * 2 - 1)
    w2 /= math.sqrt(nb_hidden)
    return w1.to(DTYPE), w2.to(DTYPE)


def init_recurrent(master, rep, nb_hidden):
    """Recurrent weights V, the same rule with n_inputs = nb_hidden (Sec. 4.2.3), from
    their own stream so that W1 and W2 equal those of the feedforward runs."""
    gen = make_generator(master, "rep%d/init_rec" % rep)
    v = (torch.rand(nb_hidden, nb_hidden, generator=gen, dtype=torch.float64) * 2 - 1)
    v /= math.sqrt(nb_hidden)
    return v.to(DTYPE)


# ---------------------------------------------------------------------------
# Network: one hidden layer of current-based LIF neurons, feedforward, and a
# leaky-integrator readout (paper Sec. 4.2.1-4.2.4):
#   S[n]   = Theta(U[n] - 1)
#   U[n+1] = (b_mem U[n] + (1 - b_mem) I[n]) (1 - S[n])          (eq. 4.1)
#   I[n+1] = b_syn I[n] + sum_j W_ij S_j^in[n]
#   U_out[n+1] = b_out U_out[n] + (1 - b_out) I_out[n],  I_out[n+1] = b_syn I_out[n] + W2 S[n]
#   a_k = max_n U_out_k[n]  ->  softmax  ->  cross-entropy           (Sec. 4.2.4, "Max")
#   + lambda_lower * mean_{mu,i} [nu_lower - zeta_i^mu]_+^2           (Sec. 4.2.5, g_lower)
# The reset is detached from the graph unless diff_reset (Sec. 2.3, 4.2.1).
# Gradients: backpropagation through time with the spike derivative replaced
# by h(U - 1).  `Network.loss_and_grad` does this by hand (fast); the
# autograd version `loss_autograd` is the reference used in the tests.
# ---------------------------------------------------------------------------
class Network:
    def __init__(self, spec, dtype=DTYPE):
        self.T = spec["nb_steps"]
        dt = spec["dt"]
        self.b_mem = math.exp(-dt / spec["tau_mem"])
        self.c_mem = 1.0 - self.b_mem
        self.b_syn = math.exp(-dt / spec["tau_syn"])
        self.b_out = math.exp(-dt / spec["tau_readout"])
        self.dtype = dtype
        self.kernel = readout_kernel(self.T, self.b_syn, self.b_out).to(dtype)
        self._buffers = {}

    def _buf(self, name, shape):
        """A persistent buffer and the list of its views along dim 0."""
        key = (name, shape)
        if key not in self._buffers:
            buf = torch.empty(shape, dtype=self.dtype)
            self._buffers[key] = (buf, list(buf.unbind(0)))
        return self._buffers[key]

    def _spike_index(self, t_in):
        """Row t*B + b of a time-major (T*B, .) array for every input spike (b, u)."""
        B = t_in.shape[0]
        key = ("arange", B)
        if key not in self._buffers:
            self._buffers[key] = torch.arange(B).unsqueeze(1)
        return (t_in * B + self._buffers[key]).reshape(-1)

    def forward(self, t_in, w1, w2, shape=None, beta=None, smooth=False,
                record_pre=False, frozen_reset=None, w_rec=None):
        """Simulate hidden layer and readout for a batch of spike-time inputs.

        Returns (S, U, P, R, U_out): spikes S (T,B,H); membrane potentials U
        (T+1,B,H) with U[0] = 0; P[n] = b_mem U[n] + c_mem I[n] (only if
        record_pre); R, the list of tensors used for the reset (S, or
        frozen_reset in tests); U_out (T,B,K) with U_out[n] the readout
        potential after step n.  smooth=True replaces Theta by the primitive of
        the surrogate (tests only).  w_rec (H,H), if given, adds the recurrent
        current sum_j V_ji S_j[n] to I[n+1] (paper Sec. 4.2.1, the V term).
        """
        T = self.T
        B, nin = t_in.shape
        H = w1.shape[1]
        K = w2.shape[1]
        t_last = min(int(t_in.max()), T - 1)    # no input current after this step
        h_in, h_in_v = self._buf("hin", (T, B, H))
        h_in[:t_last + 1].zero_()
        h_in.view(T * B, H).index_add_(
            0, self._spike_index(t_in), w1.unsqueeze(0).expand(B, nin, H).reshape(B * nin, H))
        U, U_v = self._buf("U", (T + 1, B, H))
        S, S_v = self._buf("S", (T, B, H))
        P, P_v = self._buf("P", (T, B, H)) if record_pre else (None, None)
        R_v = S_v if frozen_reset is None else list(frozen_reset.unbind(0))
        b_mem, b_syn, b_out = self.b_mem, self.b_syn, self.b_out
        U_v[0].zero_()
        I = torch.zeros(B, H, dtype=self.dtype)
        for n in range(T):
            Un = U_v[n]
            Sn = S_v[n]
            if smooth:
                Sn.copy_(surrogate_primitive(Un - 1.0, shape, beta))
            else:
                heaviside_(torch.sub(Un, 1.0, out=Sn))               # S[n] = Theta(U[n] - 1)
            Un1 = torch.lerp(I, Un, b_mem, out=U_v[n + 1])           # b_mem U[n] + (1-b_mem) I[n]
            if record_pre:
                P_v[n].copy_(Un1)
            Un1.addcmul_(Un1, R_v[n], value=-1.0)                    # (1 - S[n]) reset, eq. 4.1
            if n <= t_last:
                I = h_in_v[n].add_(I, alpha=b_syn)                   # I[n+1] = b_syn I[n] + W S_in[n]
            else:
                I = torch.mul(I, b_syn, out=h_in_v[n])               # no input spikes at step n
            if w_rec is not None:
                I.addmm_(Sn, w_rec)                                  # + V S[n] (recurrent)
        # Readout: I_out[n+1] = b_syn I_out[n] + W2 S[n]; U_out[n+1] = b_out U_out[n] + (1-b_out) I_out[n]
        h_out, h_out_v = self._buf("hout", (T, B, K))
        torch.mm(S.view(T * B, H), w2, out=h_out.view(T * B, K))
        U_out, U_out_v = self._buf("Uout", (T, B, K))
        I_out = torch.zeros(B, K, dtype=self.dtype)
        Uo = torch.zeros(B, K, dtype=self.dtype)
        for n in range(T):
            Uo = torch.lerp(I_out, Uo, b_out, out=U_out_v[n])        # U_out[n+1]
            I_out = h_out_v[n].add_(I_out, alpha=b_syn)              # I_out[n+1]
        return S, U_v, P_v, R_v, U_out

    def logits(self, t_in, w1, w2, w_rec=None):
        S, _, _, _, U_out = self.forward(t_in, w1, w2, w_rec=w_rec)
        return U_out.max(dim=0).values, S

    def loss_and_grad(self, t_in, y, w1, w2, shape, beta, lam_low, nu_low,
                      smooth=False, diff_reset=False, frozen_reset=None, w_rec=None,
                      rec_grad=True):
        """Loss, cross-entropy part, regulariser part, dL/dW1, dL/dW2, dL/dV (by hand).

        diff_reset: let gradients flow through the reset term (paper "DR", Fig. 5b-d).
        w_rec: recurrent weights V; rec_grad: let gradients flow through the
        recurrent connections ("Prop", Fig. 5e-f) or not ("Det"/"Ctl"; V still
        learns from its local term).  dL/dV is None without w_rec.
        """
        T = self.T
        B, nin = t_in.shape
        H = w1.shape[1]
        K = w2.shape[1]
        S, U_v, P_v, R_v, U_out = self.forward(t_in, w1, w2, shape, beta, smooth=smooth,
                                               record_pre=diff_reset,
                                               frozen_reset=frozen_reset, w_rec=w_rec)
        # a = max over time; torch.max picks the first index on ties, as
        # torch.max(output, 1) in spytorch Tutorial 2 and stork loss_stacks.py:54.
        logits, nstar = U_out.max(dim=0)
        logp = torch.log_softmax(logits, dim=1)
        ce = -logp.gather(1, y.unsqueeze(1)).mean()
        zeta = S.sum(0)
        short = (nu_low - zeta).clamp_(min=0.0)
        reg = lam_low * short.square().mean()
        loss = ce + reg
        # --- backward: loss and readout ---
        g_logits = logp.exp()
        g_logits[torch.arange(B), y] -= 1.0
        g_logits /= B
        # dL/dh_out[m, b, k] = kernel[nstar_bk, m] * g_logits[b, k], h_out[m] = W2^T S[m]
        g_hout = (self.kernel.index_select(0, nstar.reshape(-1))
                  * g_logits.reshape(-1, 1)).t().contiguous().view(T, B, K)
        g_w2 = torch.mm(S.view(T * B, H).t(), g_hout.view(T * B, K))
        g_hout_v = g_hout.unbind(0)
        w2t = w2.t().contiguous()
        g_zeta = short.mul_(-2.0 * lam_low / (B * H))                  # dL_reg/dzeta
        # --- backward: hidden layer, by hand (BPTT) ---
        b_mem, c_mem, b_syn = self.b_mem, self.c_mem, self.b_syn
        G, G_v = self._buf("G", (T + 1, B, H))      # G[n] = dL/dI[n] / c_mem
        G_v[T].zero_()
        gU = torch.zeros(B, H, dtype=self.dtype)    # dL/dU[n+1]
        _, (gpre, h, gS) = self._buf("work", (3, B, H))
        rec_path = w_rec is not None and rec_grad
        if rec_path:
            w_rec_t = w_rec.t().contiguous()
        for n in range(T - 1, -1, -1):
            torch.addcmul(gU, gU, R_v[n], value=-1.0, out=gpre)    # dL/d(b_mem U[n] + c_mem I[n])
            torch.add(gpre, G_v[n + 1], alpha=b_syn, out=G_v[n])   # dL/dI[n] / c_mem
            surrogate_of_u(U_v[n], shape, beta, out=h)             # sigma'(U[n]) = h(U[n] - 1)
            torch.addmm(g_zeta, g_hout_v[n], w2t, out=gS)          # dL/dS[n], readout + regulariser
            if rec_path:
                gS.addmm_(G_v[n + 1], w_rec_t, alpha=c_mem)        # recurrent path: I[n+1] += V S[n]
            if diff_reset:
                gS.addcmul_(gU, P_v[n], value=-1.0)                # reset path: dU[n+1]/dS[n] = -P[n]
            torch.addcmul(gpre.mul_(b_mem), gS, h, out=gU)         # dL/dU[n]
        # I[n+1] = b_syn I[n] + h_in[n]  =>  dL/dh_in[n] = dL/dI[n+1] = c_mem G[n+1]
        g_hin = G[1:].view(T * B, H)
        g_w1 = g_hin.index_select(0, self._spike_index(t_in)).view(B, nin, H).sum(0)
        g_w1.mul_(c_mem)
        g_wrec = None
        if w_rec is not None:                                      # dL/dV = sum_n S[n]^T dL/dI[n+1]
            g_wrec = torch.mm(S.view(T * B, H).t(), g_hin).mul_(c_mem)
        return loss, ce, reg, g_w1, g_w2, g_wrec

    def accuracy(self, t_in, y, w1, w2, batch=1000, w_rec=None):
        correct = 0
        spikes = 0.0
        for a in range(0, len(y), batch):
            logits, S = self.logits(t_in[a:a + batch], w1, w2, w_rec=w_rec)
            correct += int((logits.argmax(dim=1) == y[a:a + batch]).sum())
            spikes += float(S.sum(dtype=torch.float64))
        return correct / len(y), spikes / len(y)


def readout_kernel(T, b_syn, b_out):
    """K[n, m] = response of U_out[n+1] to a unit input h_out[m] (float64).

    Built by running the readout recursion of paper Sec. 4.2.2 for every
    impulse position m at once.
    """
    K = torch.zeros(T, T, dtype=torch.float64)
    U = torch.zeros(T, dtype=torch.float64)
    I = torch.zeros(T, dtype=torch.float64)
    eye = torch.eye(T, dtype=torch.float64)
    for n in range(T):
        U_next = b_out * U + (1.0 - b_out) * I
        I = b_syn * I + eye[n]
        U = U_next
        K[n] = U
    return K


class _SpikeFn(torch.autograd.Function):
    """Heaviside (or its smooth stand-in) forward, surrogate h backward."""

    @staticmethod
    def forward(ctx, x, shape, beta, smooth):
        ctx.save_for_backward(x)
        ctx.shape, ctx.beta = shape, beta
        if smooth:
            return surrogate_primitive(x, shape, beta)
        return (x > 0).to(x.dtype)

    @staticmethod
    def backward(ctx, grad):
        (x,) = ctx.saved_tensors
        return grad * surrogate(x, ctx.shape, ctx.beta), None, None, None


def loss_autograd(net, t_in, y, w1, w2, shape, beta, lam_low, nu_low,
                  smooth=False, diff_reset=False, frozen_reset=None, w_rec=None,
                  rec_grad=True):
    """Reference implementation with PyTorch autograd (used by the tests).

    Written independently of Network.loss_and_grad: dense input raster, an
    explicit readout recursion, autograd for every gradient.
    """
    T = net.T
    B, nin = t_in.shape
    dense = torch.zeros(B, T, nin, dtype=w1.dtype)
    dense.scatter_(1, t_in.unsqueeze(1), 1.0)
    h_in = dense @ w1
    U = torch.zeros(B, w1.shape[1], dtype=w1.dtype)
    I = torch.zeros_like(U)
    spikes = []
    for n in range(T):
        Sn = _SpikeFn.apply(U - 1.0, shape, beta, smooth)
        if frozen_reset is not None:
            Rn = frozen_reset[n]
        else:
            Rn = Sn if diff_reset else Sn.detach()
        U_next = (net.b_mem * U + (1.0 - net.b_mem) * I) * (1.0 - Rn)
        I = net.b_syn * I + h_in[:, n]
        if w_rec is not None:
            I = I + (Sn if rec_grad else Sn.detach()) @ w_rec
        U = U_next
        spikes.append(Sn)
    S = torch.stack(spikes)
    I_out = torch.zeros(B, w2.shape[1], dtype=w1.dtype)
    U_out = torch.zeros_like(I_out)
    rec = []
    for n in range(T):
        U_next = net.b_out * U_out + (1.0 - net.b_out) * I_out
        I_out = net.b_syn * I_out + S[n] @ w2
        U_out = U_next
        rec.append(U_out)
    logits = torch.stack(rec).max(dim=0).values
    ce = torch.nn.functional.cross_entropy(logits, y)
    reg = lam_low * torch.clamp(nu_low - S.sum(0), min=0.0).square().mean()
    return ce + reg, S


# ---------------------------------------------------------------------------
# One training run.
# ---------------------------------------------------------------------------
def train_run(net, data, w1_init, w2_init, master, rep, shape, beta, eta, epochs,
              batch_size, lam_low, nu_low, diff_reset=False, w_rec_init=None, rec_grad=True):
    """Adam with default parameters (paper Sec. 4.2.6); returns a result dict.

    diff_reset: gradients through the reset (Fig. 5 "DR"); w_rec_init: recurrent
    weights V for a recurrent hidden layer (Fig. 5e-f), trained with W (Sec. 4.2.6);
    rec_grad: gradients through the recurrent connections ("Prop") or not.
    """
    w1 = w1_init.clone().requires_grad_(True)
    w2 = w2_init.clone().requires_grad_(True)
    params = [w1, w2]
    w_rec = None
    if w_rec_init is not None:
        w_rec = w_rec_init.clone().requires_grad_(True)
        params.append(w_rec)
    opt = torch.optim.Adam(params, lr=eta)
    x_tr, y_tr = data["train"]
    n = len(y_tr)
    nb = n // batch_size
    order = make_generator(master, "rep%d/order" % rep)
    last_ce = float("nan")
    for _ in range(epochs):
        perm = torch.randperm(n, generator=order)
        ce_sum = 0.0
        for i in range(nb):
            idx = perm[i * batch_size:(i + 1) * batch_size]
            _, ce, _, g1, g2, gr = net.loss_and_grad(
                x_tr[idx], y_tr[idx], w1.detach(), w2.detach(), shape, beta, lam_low, nu_low,
                diff_reset=diff_reset, w_rec=None if w_rec is None else w_rec.detach(),
                rec_grad=rec_grad)
            w1.grad = g1
            w2.grad = g2
            if w_rec is not None:
                w_rec.grad = gr
            opt.step()
            ce_sum += float(ce)
        last_ce = ce_sum / nb
    wr = None if w_rec is None else w_rec.detach()
    with torch.no_grad():
        val_acc, _ = net.accuracy(*data["valid"], w1.detach(), w2.detach(), w_rec=wr)
        test_acc, spikes = net.accuracy(*data["test"], w1.detach(), w2.detach(), w_rec=wr)
    finite = all(bool(torch.isfinite(p).all()) for p in params)
    return {"val_acc": val_acc, "test_acc": test_acc, "train_ce_last_epoch": last_ce,
            "hidden_spikes_per_test_input": spikes, "finite": finite}


# ---------------------------------------------------------------------------
# Job: grid of runs, two worker processes.
# ---------------------------------------------------------------------------
_WORKER = {}


def _worker_init(cfg):
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    _WORKER.clear()
    _WORKER["cfg"] = cfg
    _WORKER["master"] = read_master_seed()
    _WORKER["net"] = Network(cfg["spec"])
    _WORKER["reps"] = {}


def _replicate(rep):
    reps = _WORKER["reps"]
    if rep not in reps:
        spec = _WORKER["cfg"]["spec"]
        master = _WORKER["master"]
        data = make_dataset(master, rep, spec)
        w1, w2 = init_weights(master, rep, spec["nb_inputs"], spec["nb_hidden"],
                              spec["nb_classes"])
        w_rec = init_recurrent(master, rep, spec["nb_hidden"])
        reps[rep] = (data, w1, w2, w_rec)
    return reps[rep]


def _worker_run(task):
    cfg = _WORKER["cfg"]
    spec = cfg["spec"]
    data, w1, w2, w_rec = _replicate(task["rep"])
    t0 = time.perf_counter()
    res = train_run(_WORKER["net"], data, w1, w2, _WORKER["master"], task["rep"],
                    task["shape"], task["beta"], task["eta"], task["epochs"],
                    spec["batch_size"], spec["lower_l2_strength"],
                    spec["lower_l2_threshold"], diff_reset=task["diff_reset"],
                    w_rec_init=w_rec if task["recurrent"] else None,
                    rec_grad=task["rec_grad"])
    res["seconds"] = time.perf_counter() - t0
    out = dict(task)
    out.update(res)
    return out


def build_tasks(cfg):
    """All runs.  Fig. 3: shapes x slope beta x eta, feedforward, detached reset.
    Fig. 5: asymptotic SuperSpike over the same beta grid, (i) feedforward with
    differentiable reset ("aDR", Fig. 5b-c) and (ii) recurrent with gradients
    through the recurrent connections and detached reset ("aProp", Fig. 5e)."""
    def task(kind, rep, shape, beta, eta, epochs, diff_reset=False, recurrent=False,
             rec_grad=False):
        return {"kind": kind, "rep": rep, "shape": shape, "beta": beta, "eta": eta,
                "epochs": epochs, "diff_reset": diff_reset, "recurrent": recurrent,
                "rec_grad": rec_grad}

    tasks = []
    for rep in range(cfg["seeds"]):
        for shape in cfg["shapes"]:
            for beta in cfg["betas"]:
                for eta in cfg["etas"]:
                    tasks.append(task("grid", rep, shape, beta, eta, cfg["epochs"]))
        if cfg["fig5"]:
            for beta in cfg["fig5_betas"]:
                for eta in cfg["fig5_etas"]:
                    tasks.append(task("fig5_dr", rep, "asymptotic", beta, eta,
                                      cfg["fig5_epochs"], diff_reset=True))
            for beta in cfg["fig5_rec_betas"]:
                for eta in cfg["fig5_rec_etas"]:
                    tasks.append(task("fig5_rec", rep, "asymptotic", beta, eta,
                                      cfg["fig5_epochs"], recurrent=True, rec_grad=True))
            # The same two settings with the normalised SuperSpike (peak 1): the
            # paper's sDR (Fig. 5c) and sProp (Fig. 5e) controls, at the default beta.
            b0 = cfg["fig5_control_beta"]
            for eta in cfg["fig5_etas"]:
                tasks.append(task("fig5_sdr", rep, "superspike", b0, eta, cfg["fig5_epochs"],
                                  diff_reset=True))
            for eta in cfg["fig5_rec_etas"]:
                tasks.append(task("fig5_sprop", rep, "superspike", b0, eta, cfg["fig5_epochs"],
                                  recurrent=True, rec_grad=True))
        if cfg["controls"]:
            # Learning disabled (eta = 0): must stay at chance.
            tasks.append(task("no_learning", rep, "superspike", 10.0, 0.0, cfg["epochs"]))
            # The actual derivative of the step (zero a.e.), paper Fig. 2b "True".  From
            # the silent start nothing receives a gradient, so one eta suffices.
            tasks.append(task("true_gradient", rep, "zero", 0.0, cfg["true_gradient_eta"],
                              cfg["epochs"]))
            for eta in cfg["etas"]:
                # Constant surrogate (beta = 0 -> h = 1), paper Fig. 3c grey bars.
                tasks.append(task("constant", rep, "superspike", 0.0, eta, cfg["epochs"]))
    # Longest runs first, so that the two workers finish together.
    cost = {"fig5_rec": 2.3, "fig5_sprop": 2.3, "fig5_dr": 1.15, "fig5_sdr": 1.15}
    tasks.sort(key=lambda t: -cost.get(t["kind"], 1.0) * t["epochs"])
    return tasks


def task_key(t):
    return (t["kind"], t["rep"], t["shape"], t["beta"], t["eta"])


def run_tasks(cfg, tasks, workers, log):
    results = {}
    t_start = time.perf_counter()
    done = 0

    def note(res):
        nonlocal done
        done += 1
        results[task_key(res)] = res
        elapsed = time.perf_counter() - t_start
        eta_s = elapsed / done * (len(tasks) - done)
        log("[%d/%d] %s rep=%d %s beta=%g eta=%g -> val=%.3f test=%.3f (%.1fs; "
            "elapsed %.0fs, remaining ~%.0fs)" % (
                done, len(tasks), res["kind"], res["rep"], res["shape"], res["beta"],
                res["eta"], res["val_acc"], res["test_acc"], res["seconds"], elapsed, eta_s))

    if workers <= 1:
        _worker_init(cfg)
        for t in tasks:
            note(_worker_run(t))
    else:
        ctx = multiprocessing.get_context("spawn")
        with ctx.Pool(processes=workers, initializer=_worker_init, initargs=(cfg,)) as pool:
            for res in pool.imap_unordered(_worker_run, tasks, chunksize=1):
                note(res)
    return results, time.perf_counter() - t_start


def select_by_validation(results, kind, rep, shape, beta, etas):
    """Test accuracy at the learning rate with the best validation accuracy
    (ties: the smaller eta)."""
    best = None
    for eta in etas:
        r = results[(kind, rep, shape, beta, eta)]
        if best is None or r["val_acc"] > best["val_acc"]:
            best = r
    return best


def selected_curve(results, kind, reps, shape, betas, etas):
    """Per beta: test accuracy at the validation-selected eta; mean over seeds.
    Returns (selected runs, curve over betas, best over betas averaged over seeds)."""
    sel = {(r, b): select_by_validation(results, kind, r, shape, b, etas)
           for r in reps for b in betas}
    n = float(len(reps))
    curve = [sum(sel[(r, b)]["test_acc"] for r in reps) / n for b in betas]
    best = sum(max(sel[(r, b)]["test_acc"] for b in betas) for r in reps) / n
    return sel, curve, best


def summarise(cfg, results):
    """Outputs (at most 20 entries) and a detailed summary for runs.json.

    shape_spread: Fig. 3, spread over shapes of each shape's best test accuracy
    (best over the slope beta, mean over seeds).  slope_spread_default: Fig. 3,
    max - min over beta of SuperSpike's test accuracy.  magnitude_scale_spread:
    Fig. 5, max - min over beta of the asymptotic SuperSpike's test accuracy with a
    differentiable reset (aDR, Fig. 5b-c, the setting Sec. 2.3 introduces first and
    concludes on: "the scale of the surrogate derivative plays an important role ...
    if implicit recurrence, as contributed by the spike reset, is present");
    magnitude_scale_spread_recurrent: the same for the recurrent network with
    gradients through the recurrent connections (aProp, Fig. 5e).
    test_passed = 1 if shape_spread < magnitude_scale_spread.
    """
    reps = range(cfg["seeds"])
    nrep = float(len(reps))
    shapes, betas, etas = cfg["shapes"], cfg["betas"], cfg["etas"]
    sel, curve, best = {}, {}, {}
    for s in shapes:
        sel_s, curve[s], best[s] = selected_curve(results, "grid", reps, s, betas, etas)
        sel.update({("grid", r, s, b): v for (r, b), v in sel_s.items()})
    slope_spread = {s: max(curve[s]) - min(curve[s]) for s in shapes}
    shape_spread = max(best.values()) - min(best.values())
    default = cfg["default_shape"] if cfg["default_shape"] in shapes else shapes[0]

    def r4(v):
        return round(float(v), 4)

    def curve_text(bs, accs):
        return ",".join("%g:%.3f" % (b, a) for b, a in zip(bs, accs))[:200]

    out = {"shape_spread": r4(shape_spread),
           "slope_spread_default": r4(slope_spread[default])}
    detail = {"curve_mean_test_acc_by_beta": {}, "best_test_acc_mean_over_seeds": best,
              "slope_spread": slope_spread}
    if cfg["fig5"]:
        sel_dr, curve_dr, _ = selected_curve(results, "fig5_dr", reps, "asymptotic",
                                             cfg["fig5_betas"], cfg["fig5_etas"])
        sel_rec, curve_rec, _ = selected_curve(results, "fig5_rec", reps, "asymptotic",
                                               cfg["fig5_rec_betas"], cfg["fig5_rec_etas"])
        b0 = cfg["fig5_control_beta"]
        _, sdr, _ = selected_curve(results, "fig5_sdr", reps, "superspike", (b0,),
                                   cfg["fig5_etas"])
        _, sprop, _ = selected_curve(results, "fig5_sprop", reps, "superspike", (b0,),
                                     cfg["fig5_rec_etas"])
        sel.update({("fig5_dr", r, "asymptotic", b): v for (r, b), v in sel_dr.items()})
        sel.update({("fig5_rec", r, "asymptotic", b): v for (r, b), v in sel_rec.items()})
        magnitude = max(curve_dr) - min(curve_dr)
        out["magnitude_scale_spread"] = r4(magnitude)
        out["magnitude_scale_spread_recurrent"] = r4(max(curve_rec) - min(curve_rec))
        out["test_passed"] = int(shape_spread < magnitude)
        detail["curve_mean_test_acc_by_beta"]["fig5_aDR"] = dict(
            zip([str(b) for b in cfg["fig5_betas"]], curve_dr))
        detail["curve_mean_test_acc_by_beta"]["fig5_aProp"] = dict(
            zip([str(b) for b in cfg["fig5_rec_betas"]], curve_rec))
        detail["normalised_controls"] = {"sDR": sdr[0], "sProp": sprop[0], "beta": b0}
    else:
        out["test_passed"] = int(shape_spread < slope_spread[default])
    for s in shapes[:3]:
        out["best_acc_" + s] = r4(best[s])
    out["acc_by_beta_" + default] = curve_text(betas, curve[default])
    if cfg["fig5"]:
        out["acc_by_beta_adr"] = curve_text(cfg["fig5_betas"], curve_dr)
        out["acc_by_beta_aprop"] = curve_text(cfg["fig5_rec_betas"], curve_rec)
        out["normalised_scale_controls"] = "sDR=%.3f,sProp=%.3f (beta=%g)" % (
            sdr[0], sprop[0], b0)
    out["chance_accuracy"] = r4(1.0 / cfg["spec"]["nb_classes"])
    if cfg["controls"]:
        out["control_accuracy"] = r4(sum(results[("no_learning", r, "superspike", 10.0, 0.0)]
                                         ["test_acc"] for r in reps) / nrep)
        out["true_gradient_accuracy"] = r4(sum(
            results[("true_gradient", r, "zero", 0.0, cfg["true_gradient_eta"])]["test_acc"]
            for r in reps) / nrep)
        out["constant_surrogate_accuracy"] = r4(sum(select_by_validation(
            results, "constant", r, "superspike", 0.0, etas)["test_acc"] for r in reps) / nrep)
    out["n_seeds"] = len(reps)
    out["n_shapes"] = len(shapes)
    out["n_scales"] = len(betas)
    if cfg["fig5"]:
        out["magnitude_setting"] = (
            "magnitude_scale_spread = aDR (Fig. 5b-c: asymptotic SuperSpike, feedforward "
            "nh=1, differentiable reset); _recurrent = aProp (Fig. 5e)")
    assert len(out) <= 20, len(out)
    for s in shapes:
        detail["curve_mean_test_acc_by_beta"][s] = dict(zip([str(b) for b in betas], curve[s]))
    detail["selected"] = [dict({a: v for a, v in sel[k].items() if a != "seconds"},
                               selected_for=list(k)) for k in sorted(sel)]
    return out, detail


def default_config(trial=False):
    """The job the runner executes (trial=False), or the few-minute --trial."""
    spec = dict(SPEC)
    cfg = {"spec": spec, "seeds": 1, "epochs": spec["epochs"], "betas": spec["betas"],
           "etas": spec["etas"], "shapes": spec["shapes"],
           "default_shape": spec["default_shape"], "controls": True,
           "fig5": True, "fig5_betas": spec["fig5_betas"], "fig5_etas": spec["fig5_etas"],
           "fig5_rec_betas": spec["fig5_betas"], "fig5_rec_etas": spec["fig5_rec_etas"],
           "fig5_epochs": spec["fig5_epochs"], "fig5_control_beta": spec["fig5_control_beta"],
           "true_gradient_eta": spec["true_gradient_eta"]}
    if trial:
        cfg.update(seeds=1, epochs=3, betas=(0.5, 10.0, 100.0), etas=(2e-2, 5e-2),
                   fig5_betas=(1.0, 10.0, 100.0), fig5_etas=(5e-2,),
                   fig5_rec_betas=(1.0, 100.0), fig5_rec_etas=(2e-2,), fig5_epochs=3)
    return cfg


def parse_floats(text):
    return tuple(float(v) for v in text.split(",") if v.strip())


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out-dir", default="results")
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--seeds", type=int, default=None, help="replicates (data set + init)")
    p.add_argument("--epochs", type=int, default=None)
    p.add_argument("--betas", type=parse_floats, default=None)
    p.add_argument("--etas", type=parse_floats, default=None)
    p.add_argument("--shapes", default=None, help="comma-separated")
    p.add_argument("--no-controls", action="store_true")
    p.add_argument("--no-fig5", action="store_true", help="skip the Fig. 5 (magnitude) runs")
    p.add_argument("--fig5-epochs", type=int, default=None)
    p.add_argument("--randman-spectrum", choices=("paper", "code"), default=None,
                   help="data generator power spectrum (default: paper, Sec. 4.1.1)")
    p.add_argument("--trial", action="store_true",
                   help="a few-minute check: 1 seed, few betas and etas, 3 epochs")
    args = p.parse_args(argv)

    master = read_master_seed()
    del master  # read here only to fail early; workers derive their own streams
    cfg = default_config(trial=args.trial)
    spec = cfg["spec"]
    if args.seeds is not None:
        cfg["seeds"] = args.seeds
    if args.epochs is not None:
        cfg["epochs"] = args.epochs
    if args.betas is not None:
        cfg["betas"] = args.betas
    if args.etas is not None:
        cfg["etas"] = args.etas
    if args.shapes is not None:
        cfg["shapes"] = tuple(s for s in args.shapes.split(",") if s)
    if args.no_controls:
        cfg["controls"] = False
    if args.no_fig5:
        cfg["fig5"] = False
    if args.fig5_epochs is not None:
        cfg["fig5_epochs"] = args.fig5_epochs
    if args.randman_spectrum is not None:
        spec["randman_spectrum"] = args.randman_spectrum
    for s in cfg["shapes"]:
        if s not in SHAPES_ALL:
            raise SystemExit("unknown shape %r" % (s,))

    def log(msg):
        print(msg, file=sys.stderr, flush=True)

    torch.set_num_threads(1)
    tasks = build_tasks(cfg)
    log("snn_surrogate: %d runs; Fig. 3: %d seeds x %d shapes x %d betas x %d etas, %d epochs; "
        "Fig. 5: %s; %d workers" % (
            len(tasks), cfg["seeds"], len(cfg["shapes"]), len(cfg["betas"]), len(cfg["etas"]),
            cfg["epochs"], ("aDR %dx%d, aProp %dx%d, %d epochs" % (
                len(cfg["fig5_betas"]), len(cfg["fig5_etas"]), len(cfg["fig5_rec_betas"]),
                len(cfg["fig5_rec_etas"]), cfg["fig5_epochs"])) if cfg["fig5"] else "off",
            args.workers))
    results, wall = run_tasks(cfg, tasks, args.workers, log)
    out, detail = summarise(cfg, results)

    os.makedirs(args.out_dir, exist_ok=True)
    runs = [{k: v for k, v in results[key].items() if k != "seconds"}
            for key in sorted(results)]
    cfg_public = dict(cfg)
    cfg_public["spec"] = {k: (list(v) if isinstance(v, tuple) else v) for k, v in spec.items()}
    with open(os.path.join(args.out_dir, "runs.json"), "w") as f:
        json.dump({"config": cfg_public, "runs": runs, "summary": detail}, f, indent=1,
                  sort_keys=True)
    secs = [results[k]["seconds"] for k in sorted(results)]
    with open(os.path.join(args.out_dir, "timing.json"), "w") as f:
        json.dump({"job_wall_seconds": wall, "runs": len(secs),
                   "mean_seconds_per_run": sum(secs) / len(secs),
                   "max_seconds_per_run": max(secs), "workers": args.workers}, f, indent=1)
    with open(os.path.join(args.out_dir, "outputs.json"), "w") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    log("done in %.0fs: %s" % (wall, json.dumps(out)))


if __name__ == "__main__":
    main()
