#!/usr/bin/env python3
"""Engelken et al.'s reanalysis of Ostojic's network: the autocorrelation's timescale across couplings and the decay
of small perturbations, simulated afresh from the seed, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:2de4f36e0bd30dff) is from Engelken,
Farkhooi, Hansel, van Vreeswijk & Wolf, "A reanalysis of 'Two types of asynchronous activity in networks of excitatory
and inhibitory spiking neurons'" (F1000Research 5:2043, 2016): "In the spiking network, we found in contrast that the
timescale of the autocorrelations is insensitive to the coupling strength and that rate deviations resulting from
small input perturbations rapidly decay."

Its registered test: refuted if, in Ostojic's network (8,000 E and 2,000 I LIF neurons, in-degrees 800/200, J and -5J
mV after 0.55 ms, mu_0 24 mV, theta 20, reset 10, tau 20 ms, 0.5 ms refractory), the e-folding time of the
population-averaged spike autocorrelation (3,000 neurons, 1 ms bins), fitted on lags of 10-40 ms, leaves 10-40 ms at
any of J = 0.5, 0.6, 0.7, 0.8 mV or varies over twofold across them; or if, at J = 0.3 or 0.45 mV, the mean rate
deviation after 2 ms perturbations of mu_0 (SD 1 mV) along the least stable direction of the matched rate network,
projected on it, takes over 80 ms to fall by e.

The one input is the claim's data of record, the authors' code (reanalysis-v1.0.zip, Zenodo 59624, GPL-2.0 by the
record), read as data and never run. numpy only, with snn/ostojic.py's network and simulator. Every rule below was
fixed before any seed existed; the seed draws the network, the starting potentials, the neurons sampled, the
perturbations' signs and the synthetic data of the controls.

0. The data of record. reanalysis-v1.0.zip must have its committed sha256, and its code must state, verbatim, the
   parameters this check uses (REQUIRED below: the network's sizes, in-degrees, g, potentials, time constants, delay
   and refractory period; the perturbation's 2 ms and pertsize 100 on the normalised least stable eigenvector of the
   stability matrix of Ostojic's equation 12; the projection of the spikes on it). Otherwise the run is refused.
1. The model: Ostojic's network exactly as snn/ostojic.py's rule 1 and code. One network serves every run, drawn from
   numpy's PCG64 seeded by SHA-256(seed || "|engelken/network").
2. The autocorrelation, at J = 0.5, 0.6, 0.7 and 0.8 mV: each run 1 s and then 10 s of analysis, from potentials
   uniform in [V_r, theta) ("engelken/v0/J<J>"). 3,000 neurons drawn without replacement ("engelken/sample"); each
   one's spikes counted in 1 ms bins, x(t) for t = 0 .. T - 1; its autocovariance at lag k, the sum over t < T - k of
   (x(t) - m)(x(t + k) - m) over T - k, with m its mean count (from exact integer sums); C(k) their mean over the
   3,000. The e-folding time is -1/slope of the least-squares line through ln C(k) for k = 10 .. 40 ms. A C(k) <= 0 in
   that window, or a slope >= 0, leaves no e-folding time, and its condition fails.
3. The least stable direction, at J = 0.3 and 0.45 mV. The matched rate network linearised (Ostojic's equations 5, 6
   and 12, as the authors' getMaxRealEigenvector.jl writes them): at the white-noise mean-field rate nu_0
   (snn/ostojic.py's mean_field_rate), mu = mu_0 + tau nu_0 J (C_E - g C_I) and sigma^2 = tau nu_0 J^2 (C_E + g^2 C_I);
   the slopes d phi/d mu and d phi/d sigma^2 of Ricciardi's transfer function (evaluated as mean_field_rate does) by
   central differences of 1e-3 mV and 1e-3 sigma^2; the stability matrix M = tau (d phi/d mu W + d phi/d sigma^2 W o W),
   W the network's weights, row i holding neuron i's inputs. Its eigenvalues by LAPACK (numpy's eigvals); lambda is the
   one of largest real part (of a complex pair, the one with positive imaginary part). Its eigenvector by inverse
   iteration in real arithmetic: three steps on two vectors drawn from "engelken/start/<J>", solving with
   (M - lambda)(M - conj lambda) for a complex pair or M - lambda for a real one, orthonormalised after each; then the
   eigenvector y of the 2 x 2 matrix H = Q^T M Q for its eigenvalue nearest lambda, u = Q y. The direction v: the real
   part of u turned by the phase theta = atan2(2 Re u . Im u, |Re u|^2 - |Im u|^2) / 2, which makes Re u orthogonal
   to Im u with Re u the longer (the phase ARPACK returns, whose real part the authors take, is arbitrary),
   normalised, signed so that its largest component is positive, rounded to 1e-6 (so that last-bit differences
   between machines' LAPACK leave it as it is) and normalised again.
4. The perturbations, at J = 0.3 and 0.45 mV. From potentials uniform in [V_r, theta) ("engelken/v0/pert<J>"), 1 s
   unperturbed and then 60 s in which, for each 2 ms, neuron i's constant input is mu_0 + s_k 100 v_i mV (an SD across
   neurons of 1 mV, as the authors' pertsize 100 on a unit vector), s_k = +1 or -1 drawn from "engelken/signs/<J>":
   perturbations back to back, of random sign, whose mean response is that to one perturbation as long as the
   response is linear (the authors found 0.1 mV gave "very similar results" to 1 mV), at 2 ms apart rather than their
   161.8 ms. snn/ostojic.py's update with the input per neuron. The rate deviation projected on v: y(t), the sum over
   neurons of v_i times their spikes in the t-th 1 ms bin. The mean response at lag L ms, h(L), is the mean over
   perturbations k of s_k y(2k + L), for L = 0 .. 159. Its e-folding time is the tau of the least-squares fit of
   A exp(-(L - 2)/tau) to h(L) for L = 2 .. 100 (from the end of the perturbation): tau on a grid of 0.05 ms from 1 to
   1,000 ms, A in closed form. If A <= 0 its condition fails.
5. The test's seven conditions: rule 2's four e-folding times within [10, 40] ms; their largest at most twice their
   smallest; rule 4's two at most 80 ms. test_passed is 1 if all seven hold and every control does.
6. Beside the test: each run's rate; lambda at both couplings; the matched rate network's own linearised response to
   the same perturbation, projected on v (exactly, in the plane Q spans: tau dx/dt = (H - 1) x + d phi/d mu 100 c for
   2 ms, c = Q^T v, y = c.x / 1000 at the middle of each 1 ms bin), fitted as rule 4 fits h; and h's fall by e without
   a fit: the first lag after 4 ms at which h's 5 ms running mean is at most its value at 4 ms over e, less 4 ms.
7. Controls (controls_passed counts those that behave as stated), on synthetic data drawn from "engelken/controls" and
   on the code itself:
   - 3,000 Poisson neurons, each switching between 0 and 80 Hz as its own symmetric two-state Markov chain in 1 ms
     steps whose state's autocorrelation is exp(-k/25 ms), for 10 s: rule 2 gives 25 ms within 15%;
   - 3,000 independent Poisson neurons at 20 Hz for 10 s: rule 2 gives no e-folding time within [10, 40] ms;
   - rule 4's estimator on synthetic responses: 30,000 perturbations of random sign, each adding 0.02 and 0.04 during
     its 2 ms and 0.03 exp(-(L - 2)/30) from L = 2 to 159, plus Gaussian noise of SD 0.27 per bin: it gives 30 ms within
     10%; and with 150 ms for 30 ms, more than 80 ms;
   - rule 3 on a network of 400 and 100 neurons (in-degrees 40 and 10; J = 0.45 mV's slopes) against numpy's full eig:
     lambda within 1e-9 and v within 1e-5;
   - rule 4's simulator with every perturbation zero gives exactly snn/ostojic.py's spikes (the network of rule 1 at
     J = 0.45 mV, 300 ms);
   - the simulator at J = 0 (500 neurons, 1 s): every interval exactly 2,556 steps, as snn/ostojic.py's control.

What it cannot check: the authors' own figures' values (the data of record holds code, not results; the
autocorrelation analysis is not in it); their 1.42 million isolated perturbations, which this replaces by their linear
response; the abstract's next sentence (that the decay accelerates as the coupling grows), which the test does not ask.

Writes results/outputs.json and results/detail.json. Run with: python3 snn/engelken.py
"""

import hashlib
import json
import math
import os
import re
import sys
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from snn import ostojic as O  # noqa: E402

ZIP = "reanalysis-v1.0.zip"
ZIP_SHA256 = "dd27bf7395bffd0e63edaba187e86b1ef45e85a9c5e995c7a95c651ecceb9ed1"
REQUIRED = {
    "spikingNetworkPerturbation.jl": (
        "f = 0.8 # fraction of excitatory cells", "g = 5.0 # relative strength of inhibition", "Vre = 10 ", "Vth = 20 ",
        "\u03c4_m = 20/1000", "\u03bc0 = 24 ", "PerturbationTime  = 0.002 # in s",
        "IextP = Iext + pertsize*vReal/norm(vReal)", "w = vReal[trainNeuron2];",
        "tBins1ms = 0:0.001:PerturbationPeriod"),
    "example_script_spikingPerturbation.jl": (
        "N = 10000", "C = 1000", "tauRef = 0.5/1000", "tauDelay = 0.55/1000", "pertsize = 100"),
    "getMaxRealEigenvector.jl": (
        "Stabilitymatrix = \u03c4_m / 1000 * (JMatrix * \u03b3_\u03bc + JMatrix2 * \u03b3_\u03c32)", "which=:LR",
        "vReal = real(v)"),
    "makeConnectivity.jl": (
        "sample([1:min(n-1,Ne);(n+1):Ne],Ce,replace = false)", "sample([Ne+1:n-1;max(n+1,Ne+1):N],Ci,replace = false)",
        "JMatrix[n,m] = -g*J"),
    "Ostojic_SpikingNetwork_simulation_NEST.py": (
        "CE    = 800*factor", "CI    = 200*factor", "delay   = 0.55", '"t_ref"     : 0.5', "mu_0 = 24.0",
        "tauMem = 20.0", "theta  = 20.0", "V_reset = 10.0"),
}

N = O.NE + O.NI
AC_COUPLINGS = (0.5, 0.6, 0.7, 0.8)
PERT_COUPLINGS = (0.3, 0.45)
TRANSIENT_S, AC_S, PERT_S = 1.0, 10.0, 60.0
SAMPLE, FIT_LAGS = 3000, (10, 40)
AC_LOW, AC_HIGH, AC_RATIO = 10.0, 40.0, 2.0
PULSE_MS, PERT_SIZE, LAGS = 2, 100.0, 160
PERT_FIT = (2, 100)
PERT_LIMIT = 80.0
TAU_GRID = np.round(np.arange(1.0, 1000.0 + 1e-9, 0.05), 2)
ROUND_V = 6
WORKERS = 2
LIMIT = 200
OUTPUTS = ("tau_ac_05", "tau_ac_06", "tau_ac_07", "tau_ac_08", "ac_ratio", "tau_pert_03", "tau_pert_045",
           "rate_tau_03", "rate_tau_045", "fall_03", "fall_045", "lambda_03", "lambda_045", "rates",
           "conditions_met", "conditions_total", "controls_passed", "controls_total", "test_passed")


class Refused(Exception):
    pass


def rng_for(seed_hex, label):
    digest = hashlib.sha256(bytes.fromhex(seed_hex) + b"|" + b"engelken/" + label.encode("ascii")).digest()
    return np.random.default_rng(int.from_bytes(digest, "big"))


def key(j):
    return f"{j:g}"


# ---------------------------------------------------------------- rule 0: the data of record

def read_zip(directory):
    path = os.path.join(directory, ZIP)
    with open(path, "rb") as f:
        data = f.read()
    got = hashlib.sha256(data).hexdigest()
    if got != ZIP_SHA256:
        raise Refused(f"{ZIP}: sha256 {got}, not the committed {ZIP_SHA256}")
    texts = {}
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            base = name.rsplit("/", 1)[-1]
            if base in REQUIRED:
                texts[base] = z.read(name).decode("utf-8").replace("\r\n", "\n")
    check_texts(texts)
    return texts


def check_texts(texts):
    for base, needles in REQUIRED.items():
        if base not in texts:
            raise Refused(f"{ZIP} has no {base}")
        for needle in needles:
            if needle not in texts[base]:
                raise Refused(f"{base} does not state {needle!r}")


# ---------------------------------------------------------------- rule 2: the autocorrelation

def counts_per_ms(st, si, neurons, bins):
    """Spikes of the given neurons (in that order) in 1 ms bins, as int64 rows."""
    rank = np.full(N, -1, dtype=np.int64)
    rank[neurons] = np.arange(neurons.size)
    keep = rank[si] >= 0
    b = st[keep] // O.steps_of(1.0)
    x = np.zeros((neurons.size, bins), dtype=np.int64)
    np.add.at(x, (rank[si[keep]], np.minimum(b, bins - 1)), 1)
    return x


def autocovariance(x, max_lag):
    """C(k) for k = 0 .. max_lag: each row's autocovariance from exact integer sums, then their mean."""
    t = x.shape[1]
    total = x.sum(axis=1)
    m = total / t
    out = np.zeros(max_lag + 1)
    for k in range(max_lag + 1):
        s = (x[:, : t - k] * x[:, k:]).sum(axis=1)
        a = x[:, : t - k].sum(axis=1)
        b = x[:, k:].sum(axis=1)
        cov = (s - m * (a + b) + (t - k) * m * m) / (t - k)
        out[k] = cov.mean()
    return out


def efold_from_log(c, lags=FIT_LAGS):
    """Rule 2: -1/slope of the least-squares line through ln C(k), k in the window; None if undefined."""
    k = np.arange(lags[0], lags[1] + 1, dtype=float)
    y = c[lags[0]: lags[1] + 1]
    if (y <= 0).any():
        return None
    y = np.log(y)
    kc = k - k.mean()
    slope = float((kc * (y - y.mean())).sum() / (kc * kc).sum())
    if slope >= 0:
        return None
    return -1.0 / slope


# ---------------------------------------------------------------- rule 3: the least stable direction

def transfer(mu, s2):
    """Ricciardi's rate (Hz) for mean mu and variance s2 (mV, mV^2), evaluated as snn/ostojic.py's mean_field_rate."""
    tau, tref = O.TAU_MS * 1e-3, O.REF_MS * 1e-3
    s = math.sqrt(s2)
    a, b = (O.VR - mu) / s, (O.THETA - mu) / s
    n = 4000
    h = (b - a) / n

    def f(u):
        if u < -25.0:
            return (1.0 - 1.0 / (2 * u * u)) / (-u * math.sqrt(math.pi))
        return math.exp(u * u) * math.erfc(-u)

    total = f(a) + f(b) + sum((4 if i % 2 else 2) * f(a + i * h) for i in range(1, n))
    return 1.0 / (tref + tau * math.sqrt(math.pi) * total * h / 3)


def slopes(j):
    """Rule 3's mean field at coupling j: nu_0, mu, sigma^2, the two slopes and M's entries for an excitatory and an
    inhibitory input."""
    tau = O.TAU_MS * 1e-3
    nu = O.mean_field_rate(j)
    mu = O.MU0 + tau * nu * j * (O.CE - O.G * O.CI)
    s2 = tau * nu * j * j * (O.CE + O.G * O.G * O.CI)
    hm, hs = 1e-3, 1e-3 * s2
    d_mu = (transfer(mu + hm, s2) - transfer(mu - hm, s2)) / (2 * hm)
    d_s2 = (transfer(mu, s2 + hs) - transfer(mu, s2 - hs)) / (2 * hs)
    return {"nu": nu, "mu": mu, "s2": s2, "d_mu": d_mu, "d_s2": d_s2,
            "a": tau * (d_mu * j + d_s2 * j * j), "b": tau * (-d_mu * O.G * j + d_s2 * O.G * O.G * j * j),
            "lambda_eq16": math.sqrt(O.CE * (tau * (d_mu * j + d_s2 * j * j)) ** 2
                                     + O.CI * (tau * (-d_mu * O.G * j + d_s2 * O.G * O.G * j * j)) ** 2)}


def stability_matrix(net, a, b, ne=O.NE):
    targets, _excit, starts = net
    n = starts.size - 1
    cols = np.repeat(np.arange(n), np.diff(starts))
    m = np.zeros((n, n))
    m[targets, cols] = np.where(cols < ne, a, b)
    return m


def rightmost(w):
    """The eigenvalue of largest real part; of a complex pair, the one with positive imaginary part."""
    best = max(range(w.size), key=lambda i: (w[i].real, w[i].imag))
    return complex(w[best])


def phased_real(u):
    """The real part of u at the phase that makes Re u orthogonal to Im u with Re u the longer, normalised and signed so
    that its largest component is positive."""
    a2, b2, ab = float(u.real @ u.real), float(u.imag @ u.imag), float(u.real @ u.imag)
    theta = 0.5 * math.atan2(2 * ab, a2 - b2)
    r = (u * np.exp(-1j * theta)).real
    r = r / np.linalg.norm(r)
    if r[int(np.argmax(np.abs(r)))] < 0:
        r = -r
    return r


def rounded_direction(r):
    v = np.round(r, ROUND_V)
    return v / np.linalg.norm(v)


def least_stable(m, rng, lam=None):
    """Rule 3 on the stability matrix m: (lambda, v, Q, H, residual)."""
    n = m.shape[0]
    if lam is None:
        lam = rightmost(np.linalg.eigvals(m))
    if lam.imag != 0.0:
        b = m @ m
        for i in range(0, n, 1000):  # in blocks, so that no third n x n array is made
            b[i: i + 1000] -= (2.0 * lam.real) * m[i: i + 1000]
        b[np.diag_indices(n)] += abs(lam) ** 2
    else:
        b = m.copy()
        b[np.diag_indices(n)] -= lam.real
    q = rng.standard_normal((n, 2))
    for _ in range(3):
        q = np.linalg.solve(b, q)
        q, _r = np.linalg.qr(q)
    del b
    h = q.T @ (m @ q)
    w, vecs = np.linalg.eig(h)
    k = int(np.argmin(np.abs(w - lam)))
    u = q @ vecs[:, k]
    u = u / np.linalg.norm(u)
    residual = float(np.linalg.norm(m @ u - lam * u))
    return lam, rounded_direction(phased_real(u)), q, h, residual


# ---------------------------------------------------------------- rule 4: the perturbations

def pulsed(net, j_mv, v0, warm_steps, signs, p, record=False):
    """snn/ostojic.py's update, with neuron i's constant input mu_0 + s_k p_i in the k-th 2 ms after warm_steps.
    Returns y (after warm_steps, per 1 ms bin, the spikes weighted by p / |p|: rule 4's projection on v when p = 100 v),
    the number of spikes after warm_steps and, if record, every spike's (step, neuron), for the control."""
    targets, excit, starts = net
    n = v0.size
    weights = np.where(excit, j_mv, -O.G * j_mv)
    delay, refractory = O.steps_of(O.DELAY_MS), O.steps_of(O.REF_MS)
    ring = np.zeros((delay + 1, n))
    v = v0.astype(float).copy()
    ref = np.zeros(n, dtype=np.int32)
    decay = math.exp(-O.DT_MS / O.TAU_MS)
    slot_steps, per_ms = O.steps_of(PULSE_MS), O.steps_of(1.0)
    total = warm_steps + signs.size * slot_steps
    norm = np.linalg.norm(p)
    w = p / norm if norm > 0 else np.zeros(n)
    y = np.zeros(signs.size * slot_steps // per_ms)
    spikes = 0
    sp_t, sp_i = [], []
    mu = np.full(n, O.MU0)
    for k in range(total):
        if k >= warm_steps and (k - warm_steps) % slot_steps == 0:
            mu = O.MU0 + signs[(k - warm_steps) // slot_steps] * p
        slot = k % (delay + 1)
        active = ref == 0
        v = np.where(active, mu + (v - mu) * decay + ring[slot], v)
        np.maximum(ref - 1, 0, out=ref)
        ring[slot] = 0.0
        fired = np.flatnonzero(v >= O.THETA)
        if fired.size:
            v[fired] = O.VR
            ref[fired] = refractory
            if j_mv != 0.0:
                idx = np.concatenate([np.arange(starts[f], starts[f + 1]) for f in fired])
                ring[(k + delay) % (delay + 1)] += np.bincount(targets[idx], weights=weights[idx], minlength=n)
            if record:
                sp_t.append(np.full(fired.size, k, dtype=np.int64))
                sp_i.append(fired.astype(np.int64))
            if k >= warm_steps:
                y[(k - warm_steps) // per_ms] += w[fired].sum()
                spikes += fired.size
    if record:
        st = np.concatenate(sp_t) if sp_t else np.zeros(0, np.int64)
        si = np.concatenate(sp_i) if sp_i else np.zeros(0, np.int64)
        return y, spikes, (st, si)
    return y, spikes, None


def kernel(y, signs, lags=LAGS):
    """h(L) = the mean over perturbations k of s_k y(2k + L), for L = 0 .. lags - 1."""
    h = np.zeros(lags)
    onsets = PULSE_MS * np.arange(signs.size)
    for lag in range(lags):
        idx = onsets + lag
        ok = idx < y.size
        h[lag] = float((signs[ok] * y[idx[ok]]).mean())
    return h


def efold_fit(h, window=PERT_FIT):
    """Rule 4: (tau, A) of the least-squares fit of A exp(-(L - window[0])/tau) to h over the window."""
    lags = np.arange(window[0], window[1] + 1, dtype=float)
    target = h[window[0]: window[1] + 1]
    x = np.exp(-(lags[None, :] - window[0]) / TAU_GRID[:, None])
    xx = (x * x).sum(axis=1)
    xh = (x * target[None, :]).sum(axis=1)
    sse = (target * target).sum() - xh * xh / xx
    best = int(np.argmin(sse))
    return float(TAU_GRID[best]), float(xh[best] / xx[best])


def fall_by_e(h):
    """Rule 6: the first lag after 4 ms at which h's 5 ms running mean is at most its value at 4 ms over e, less 4."""
    run = np.array([h[i - 2: i + 3].mean() for i in range(2, h.size - 2)])  # run[i - 2] centres on lag i
    ref = run[4 - 2]
    for lag in range(5, h.size - 2):
        if run[lag - 2] <= ref / math.e:
            return lag - 4
    return None


def rate_response(h2, c, d_mu, lags=LAGS):
    """Rule 6: the matched rate network's linearised response to one perturbation, projected on v, per 1 ms bin."""
    a = (h2 - np.eye(2)) / O.TAU_MS
    drive = d_mu * PERT_SIZE * np.asarray(c, dtype=float) / O.TAU_MS
    mu_, vecs = np.linalg.eig(a)
    inv = np.linalg.inv(vecs)

    def expm(t):
        return (vecs @ np.diag(np.exp(mu_ * t)) @ inv).real

    ainv = np.linalg.inv(a)
    x2 = ainv @ (expm(PULSE_MS) - np.eye(2)) @ drive
    out = np.zeros(lags)
    for lag in range(lags):
        t = lag + 0.5
        x = ainv @ (expm(t) - np.eye(2)) @ drive if t < PULSE_MS else expm(t - PULSE_MS) @ x2
        out[lag] = float(np.asarray(c) @ x) / 1000.0
    return out


# ---------------------------------------------------------------- the runs

def ac_run(args):
    seed_hex, j = args
    t0 = time.monotonic()
    net = O.network(rng_for(seed_hex, "network"))
    v0 = rng_for(seed_hex, f"v0/J{key(j)}").uniform(O.VR, O.THETA, N)
    first = O.steps_of(TRANSIENT_S * 1e3)
    total = first + O.steps_of(AC_S * 1e3)
    st, si = O.simulate(net, j, v0, total, first)
    neurons = rng_for(seed_hex, "sample").choice(N, SAMPLE, replace=False)
    bins = int(round(AC_S * 1e3))
    c = autocovariance(counts_per_ms(st, si, neurons, bins), 60)
    tau = efold_from_log(c)
    return ("ac", key(j)), {"j": j, "rate": st.size / (N * AC_S), "c": c.tolist(), "tau": tau,
                            "seconds": round(time.monotonic() - t0, 1)}


def pert_run(args):
    seed_hex, j, v = args
    t0 = time.monotonic()
    net = O.network(rng_for(seed_hex, "network"))
    v0 = rng_for(seed_hex, f"v0/pert{key(j)}").uniform(O.VR, O.THETA, N)
    slots = int(round(PERT_S * 1e3 / PULSE_MS))
    signs = rng_for(seed_hex, f"signs/{key(j)}").choice(np.array([-1.0, 1.0]), slots)
    y, spikes, _ = pulsed(net, j, v0, O.steps_of(TRANSIENT_S * 1e3), signs, PERT_SIZE * v)
    h = kernel(y, signs)
    tau, amp = efold_fit(h)
    return ("pert", key(j)), {"j": j, "rate": spikes / (N * PERT_S), "h": h.tolist(), "tau": tau, "amplitude": amp,
                              "fall": fall_by_e(h), "y_sd": float(y.std()),
                              "noise": float(y.std() / math.sqrt(slots)), "seconds": round(time.monotonic() - t0, 1)}


def directions(seed_hex, log):
    """Rule 3 at both couplings, one after the other (each needs about 2.4 GB)."""
    net = O.network(rng_for(seed_hex, "network"))
    found = {}
    for j in PERT_COUPLINGS:
        t0 = time.monotonic()
        s = slopes(j)
        m = stability_matrix(net, s["a"], s["b"])
        lam, v, q, h2, residual = least_stable(m, rng_for(seed_hex, f"start/{key(j)}"))
        del m
        c = q.T @ v
        rr = rate_response(h2, c, s["d_mu"])
        tau_r, amp_r = efold_fit(rr)
        found[key(j)] = {"j": j, "slopes": s, "lambda": [lam.real, lam.imag], "v": v, "residual": residual,
                         "H": h2.tolist(), "c": c.tolist(), "rate_response": rr.tolist(), "rate_tau": tau_r,
                         "rate_amplitude": amp_r, "seconds": round(time.monotonic() - t0, 1)}
        log(f"engelken: J = {j}: lambda {lam.real:.5f}{lam.imag:+.5f}i (eq. 16: {s['lambda_eq16']:.4f}), residual "
            f"{residual:.1e}; rate network's response falls by e in {tau_r:.1f} ms; {found[key(j)]['seconds']} s")
    return found


# ---------------------------------------------------------------- rule 7: the controls

def telegraph(rng, n, t, tc):
    """n symmetric two-state Markov chains (0 or 1) of t steps from their stationary law, each step flipping with
    probability (1 - exp(-1/tc)) / 2, so that the state's autocorrelation is exp(-k/tc)."""
    flip = rng.random((n, t)) < (1.0 - math.exp(-1.0 / tc)) / 2.0
    flip[:, 0] = rng.random(n) < 0.5
    return (np.cumsum(flip, axis=1) % 2).astype(float)

def controls(seed_hex, net, d045):
    rng = rng_for(seed_hex, "controls")
    rows = []
    # Poisson neurons whose rate switches between 0 and 80 Hz, correlated as exp(-k/25 ms).
    n, t, tc = SAMPLE, 10_000, 25.0
    x = rng.poisson(0.080 * telegraph(rng, n, t, tc))
    tau = efold_from_log(autocovariance(x, 40))
    rows.append({"control": "Poisson neurons switching between 0 and 80 Hz over 25 ms: rule 2 gives 25 ms within 15%",
                 "passed": tau is not None and abs(tau / tc - 1) <= 0.15, "value": tau})
    x = rng.poisson(0.020, (n, t))
    tau = efold_from_log(autocovariance(x, 40))
    rows.append({"control": "independent Poisson neurons: rule 2 gives no e-folding time within [10, 40] ms",
                 "passed": tau is None or not (AC_LOW <= tau <= AC_HIGH), "value": tau})
    # Rule 4's estimator on synthetic responses.
    k = 30_000
    found = []
    for tau_true in (30.0, 150.0):
        g = np.zeros(LAGS)
        g[0], g[1] = 0.02, 0.04
        g[2:] = 0.03 * np.exp(-(np.arange(2, LAGS) - 2) / tau_true)
        s = rng.choice(np.array([-1.0, 1.0]), k)
        up = np.zeros(PULSE_MS * k)
        up[::PULSE_MS] = s
        y = np.convolve(up, g)[: up.size] + rng.normal(0.0, 0.27, up.size)
        found.append(efold_fit(kernel(y, s))[0])
    rows.append({"control": "rule 4's estimator on synthetic responses of 30 ms: 30 ms within 10%",
                 "passed": abs(found[0] / 30.0 - 1) <= 0.10, "value": found[0]})
    rows.append({"control": "rule 4's estimator on synthetic responses of 150 ms: more than 80 ms",
                 "passed": found[1] > PERT_LIMIT, "value": found[1]})
    # Rule 3 against numpy's full eig on a small network.
    small = O.network(rng, ne=400, ni=100, ce=40, ci=10)
    m = stability_matrix(small, d045["a"], d045["b"], ne=400)
    lam, v, _q, _h, _res = least_stable(m, rng)
    w, vecs = np.linalg.eig(m)
    ref_lam = rightmost(w)
    ref_v = rounded_direction(phased_real(vecs[:, int(np.argmin(np.abs(w - ref_lam)))]))
    gap = float(np.abs(v - ref_v).max())
    rows.append({"control": "rule 3 against numpy's full eig (500 neurons): lambda within 1e-9, v within 1e-5",
                 "passed": abs(lam - ref_lam) <= 1e-9 and gap <= 1e-5, "value": [abs(lam - ref_lam), gap]})
    # Rule 4's simulator with zero perturbations against snn/ostojic.py's.
    v0 = rng.uniform(O.VR, O.THETA, N)
    steps = O.steps_of(300.0)
    st, si = O.simulate(net, 0.45, v0, steps, 0)
    warm = O.steps_of(100.0)
    signs = rng.choice(np.array([-1.0, 1.0]), (steps - warm) // O.steps_of(PULSE_MS))
    _y, _n, (pt, pi) = pulsed(net, 0.45, v0, warm, signs, np.zeros(N), record=True)
    same = st.size == pt.size and bool((st == pt).all() and (si == pi).all())
    rows.append({"control": "rule 4's simulator with zero perturbations gives snn/ostojic.py's spikes exactly",
                 "passed": same, "value": [int(st.size), int(pt.size)]})
    # The simulator at J = 0.
    few = 500
    empty = (np.zeros(0, np.int32), np.zeros(0, bool), np.zeros(few + 1, np.int64))
    zt, zi = O.simulate(empty, 0.0, rng.uniform(O.VR, O.THETA, few), O.steps_of(1000.0), 0)
    order = np.lexsort((zt, zi))
    zt, zi = zt[order], zi[order]
    intervals = np.unique((zt[1:] - zt[:-1])[zi[1:] == zi[:-1]])
    rows.append({"control": "the simulator at J = 0: every interval exactly 2,556 steps",
                 "passed": intervals.tolist() == [2556], "value": intervals.tolist()})
    return rows


# ---------------------------------------------------------------- the verdict

def conditions(ac, pert):
    taus = [ac[key(j)]["tau"] for j in AC_COUPLINGS]
    cond = {}
    for j, tau in zip(AC_COUPLINGS, taus):
        cond[f"J = {j} mV: autocorrelation e-folding time within [10, 40] ms"] = (
            tau is not None and AC_LOW <= tau <= AC_HIGH)
    ok = all(tau is not None for tau in taus)
    cond["autocorrelation e-folding times within a factor of two"] = ok and max(taus) <= AC_RATIO * min(taus)
    for j in PERT_COUPLINGS:
        p = pert[key(j)]
        cond[f"J = {j} mV: perturbation falls by e within 80 ms"] = p["amplitude"] > 0 and p["tau"] <= PERT_LIMIT
    return cond


def none_or(x):
    return "none" if x is None else x


def run(seed_hex, results="results", inputs="inputs", log=print):
    started = time.monotonic()
    read_zip(inputs)
    dirs = directions(seed_hex, log)
    jobs = [(pert_run, (seed_hex, j, dirs[key(j)]["v"])) for j in PERT_COUPLINGS]
    jobs += [(ac_run, (seed_hex, j)) for j in AC_COUPLINGS]
    found = {}
    with ProcessPoolExecutor(WORKERS) as pool:
        futures = [pool.submit(fn, a) for fn, a in jobs]
        for fut in futures:
            (kind, k), r = fut.result()
            found.setdefault(kind, {})[k] = r
            if kind == "ac":
                log(f"engelken: J = {r['j']}: rate {r['rate']:.2f} Hz, autocorrelation e-folding {r['tau']} ms, "
                    f"{r['seconds']} s")
            else:
                log(f"engelken: J = {r['j']}: rate {r['rate']:.2f} Hz, perturbation e-folding {r['tau']} ms (A "
                    f"{r['amplitude']:.4f}), fall {r['fall']} ms, {r['seconds']} s")
    ac, pert = found["ac"], found["pert"]
    net = O.network(rng_for(seed_hex, "network"))
    rows = controls(seed_hex, net, dirs[key(0.45)]["slopes"])
    cond = conditions(ac, pert)
    ok_controls = sum(1 for r in rows if r["passed"])
    taus = [ac[key(j)]["tau"] for j in AC_COUPLINGS]
    r4 = lambda x: "none" if x is None else float(round(x, 4))  # noqa: E731

    def lam(j):
        re_, im_ = dirs[key(j)]["lambda"]
        return f"{re_:.5f}{im_:+.5f}i"

    values = {
        "tau_ac_05": r4(taus[0]), "tau_ac_06": r4(taus[1]), "tau_ac_07": r4(taus[2]), "tau_ac_08": r4(taus[3]),
        "ac_ratio": r4(max(taus) / min(taus)) if all(t is not None for t in taus) else "none",
        "tau_pert_03": r4(pert[key(0.3)]["tau"]), "tau_pert_045": r4(pert[key(0.45)]["tau"]),
        "rate_tau_03": r4(dirs[key(0.3)]["rate_tau"]), "rate_tau_045": r4(dirs[key(0.45)]["rate_tau"]),
        "fall_03": none_or(pert[key(0.3)]["fall"]), "fall_045": none_or(pert[key(0.45)]["fall"]),
        "lambda_03": lam(0.3), "lambda_045": lam(0.45),
        "rates": "; ".join([f"J {j}: {ac[key(j)]['rate']:.3f}" for j in AC_COUPLINGS]
                           + [f"J {j} pulsed: {pert[key(j)]['rate']:.3f}" for j in PERT_COUPLINGS]) + " Hz",
        "conditions_met": sum(cond.values()), "conditions_total": len(cond),
        "controls_passed": ok_controls, "controls_total": len(rows),
        "test_passed": int(all(cond.values()) and ok_controls == len(rows)),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters")
    detail = {"values": values, "conditions": cond, "controls": rows,
              "autocorrelation": ac, "perturbation": pert,
              "directions": {k: {kk: vv for kk, vv in d.items() if kk != "v"} | {"v_head": d["v"][:8].tolist()}
                             for k, d in dirs.items()},
              "rules": {"transient_s": TRANSIENT_S, "ac_s": AC_S, "pert_s": PERT_S, "sample": SAMPLE,
                        "fit_lags": FIT_LAGS, "pert_fit": PERT_FIT, "pert_size": PERT_SIZE, "round_v": ROUND_V},
              "seconds": round(time.monotonic() - started, 1)}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as f:
        json.dump(detail, f, indent=1, sort_keys=True, default=float)
        f.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed, log=lambda s: print(s, file=sys.stderr, flush=True))
    except Refused as e:
        sys.exit(f"snn/engelken.py: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
