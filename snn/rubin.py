#!/usr/bin/env python3
"""Rubin, Lee & Sompolinsky (2001): under the multiplicative temporally asymmetric Hebb rule, the synapses of an
asynchronous network reach a distribution invariant to the firing rates of the pre- and postsynaptic cells.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from J. Rubin, D. D. Lee and
H. Sompolinsky, "Equilibrium Properties of Temporally Asymmetric Hebbian Plasticity" (Physical Review Letters 86(2),
364-367, 2001; arxiv:cond-mat/0007392, v2 of 8 September 2000, the text read here, from its source), its abstract:
"In a biologically plausible multiplicative model, we find that the synapses in asynchronous networks reach a
distribution that is invariant to the firing rates of either the pre- or post-synaptic cells."

The test, as registered: see TEST below. Standard library and the image's gcc: the network is simulated in C
(snn/rubin.c, compiled here). No data are read: the inputs are generated under the seed. Every rule below was fixed
before any run of the model at the test's rates or durations.

1. The model, as the paper gives it (its text and Figure 2's legend): N = 1000 excitatory synapses on independent
   Poisson inputs at r_in onto one integrate-and-fire cell, tau_m dV/dt = -V - I_s, a spike at V = 1 and a reset to
   0; I_s = g_s sum_i w_i sum_(t_i < t) exp((t_i - t)/tau_s) (V - V_s), tau_m = 20 ms, tau_s = 5 ms, V_s = 5,
   g_s = 0.01. A pair of an input and an output spike changes the weight by +lambda f+(w) K(t_o - t_i) if the
   output follows and by -lambda f-(w) K(t_i - t_o) if it precedes, K(t) = exp(-t/tau), tau = 10 ms,
   lambda = 0.005, alpha = 1.05; additive: f+ = 1, f- = alpha, the weight clipped to [0, 1]; multiplicative:
   f+ = 1 - w, f- = alpha w. Every pair counts (the uncorrelated term of the paper's drift, Eq. 4, (f+ - f-) tau
   r_in r_out, is that of all pairs), by traces: one per input and one for the output, each decaying with tau and
   raised by 1 at its spikes; an arrival changes its weight by -lambda f-(w) M, an output spike every weight by
   lambda f+(w) P_i, f at the weight of the moment. Each arrival adds g_s w to the conductance, w its weight then
   ("the increase in the output cell's conductance in units of g_s, immediately after a spike"). Synapse 0 is held
   at 0.5 in every network run, the paper's way of measuring chi (Figure 3's legend); the distributions are the
   other 999's.
2. The numerics, which the paper does not give: steps of 0.1 ms; in each, the arrivals (a Poisson count of the
   1000 inputs' spikes, each given to a synapse drawn uniformly, which is the superposition of independent Poisson
   trains), each adding its conductance and then applying its depression; then the membrane by exponential Euler
   with the step's conductance; then the spike if V >= 1, with its potentiation; then one step of decay of the
   conductance and the traces. An arrival in the step of a spike came before it. No refractory period (none is
   given). The generator is xoshiro256**, seeded from SHA-256 of the seed and the run's label.
3. Runs, under the multiplicative rule: at r_in = 10, 20, 30 and 40 Hz with g_s = 0.01 (Figure 3(b)'s range, the
   text's "from 10 to 40 Hz"), and at 10 Hz with g_s = 0.015 and 0.02, which raise the postsynaptic rate at a fixed
   presynaptic one (the paper does not do this; the claim names the postsynaptic rate on its own); each 3,000 s from
   weights drawn uniformly on [0, 1) (the paper gives no start), the last 1,000 s measured; and at 10 Hz with
   g_s = 0.01 from every weight at 1.
4. What is measured: at the end of every second of the window, the 999 plastic weights go into a histogram of
   10,000 bins over [0, 1] (the window's halves into two more). The distance between two distributions is the
   Wasserstein (earth mover's) distance, the sum over the bins' upper edges of |F1 - F2| x 1e-4, F the cumulative
   shares, in units of the weight and exact to a bin. Also: the output rate; the weights' mean and SD over the
   window; and chi (Eq. 11, T+ = tau chi w): T+ = S+ T / (n_in n_out) - tau', S+ the sum of synapse 0's trace at the
   output spikes, n_in its arrivals and n_out the output spikes in the window T, tau' = dt / (1 - exp(-dt/tau)) the
   value by chance on the steps' grid, and chi = T+ / (0.5 tau); pooled over the plastic synapses likewise, divided
   by their mean weight; T- from the output's trace at arrivals, by chance tau' - dt.
5. The test's 17 conditions: the six pairs of the four input rates' distributions less than 0.05 apart; the three
   pairs of the three g_s runs' at 10 Hz less than 0.05 apart; each of the seven runs' halves less than 0.01 apart;
   and the run from every weight at 1 less than 0.01 from the uniform start's. test_passed is 1 if all hold. The
   0.05 is a twentieth of the weights' range, about a tenth of 1/(1 + alpha); Figure 3(b) shows the mean weight
   moving by 0.015 from 10 to 40 Hz.
6. Beside the test, none of it counted (the paper's values read from its figures' vector paths in the arXiv source,
   by their axes' ticks):
   - the output rates against Figure 3(b) (16.4, 80.6, 136.8 and 192.3 Hz at 10, 20, 30 and 40 Hz), and the g_s
     runs' rates;
   - the mean weights against Figure 3(b) (0.505, 0.490, 0.490 and 0.491) and 1/(1 + alpha) = 0.4878; the 10 Hz
     distribution against Figure 2(b)'s histogram (mean 0.505, SD 0.018);
   - chi from synapse 0 and pooled, against Figure 3(b)'s curve, whose axis is labelled 20 chi (chi 0.031, 0.002,
     0.0014 and 0.0008), and T-, which causality puts at 0;
   - the additive rule at 10, 20, 30 and 40 Hz, 50,000 s from uniform weights with the last 5,000 s measured: the
     output rates against Figure 3(a) (18.0, 20.0, 21.5 and 22.2 Hz; the text's "approximately constant at
     22 Hz"), the mean weights (0.509, 0.262, 0.179, 0.137), chi against the figure (labelled 20 chi: 0.022, 0.021,
     0.019, 0.019) and the text's 0.1 = 2 (alpha - 1) of Eq. 13, the shares below 0.1 and at or above 0.9 at 10 Hz
     (Figure 2(a): 39% and 41%), its halves, and the distances between its rates;
   - the equilibration at 10 Hz under each rule: the first 10 s mark after which the mean weight stays within 0.01
     of the window's mean (the paper: the additive model much slower). Changed after the first trial, whose
     outcomes were seen: the uniform start's mean is 0.5, already within 0.01 of the multiplicative equilibrium's,
     so its mark says nothing; the run from every weight at 1, whose mean must travel to it, is reported beside it;
   - a single synapse (Figure 1, and Figure 2's upper histograms): a Poisson train at 10 Hz as the input and the
     same train shifted by dt as the output, dt = -50, -20, -10, -5, 5, 10, 20 and 50 ms, simulated in continuous
     time for 3,000 s and the weight's mean taken every second over the last 2,000 s, under each rule, against
     Eq. 9's w0 at r = 10 Hz (Figure 1(b): 0.817 at +10 ms, 0.169 at -10 ms) and, for the additive rule, against
     a weight at 1 for 0 < dt < dt0 = tau ln(1 / ((alpha - 1) tau r)) = 53 ms and at 0 otherwise.

Controls (controls_passed counts those that behave as stated; the run stops if any fails): the C program matches a
plain implementation written here, bit for bit, over 1.2 s at 10 Hz under each rule from uniform weights, with
snapshots every 0.1 s (spikes, arrivals, sums, histograms, the windows' means and every final weight; the moments,
summed in long double in C, within 1e-12); one pre and one post spike 5 ms apart change a weight of 0.5 by
lambda f+ e^(-1/2) and by -lambda f- e^(-1/2) under each rule, within 1e-12; under a constant conductance of 0.5 and
of 1, the cell's first spike comes within one step of tau_m / (1 + g) ln(V_inf / (V_inf - 1)),
V_inf = g V_s / (1 + g); in 20 s at 10 Hz with the weights held at 0.5, the arrivals are within four standard errors
of 200,000 and the mean conductance within 2% of g_s N 0.5 r_in tau_s = 0.25; the pooled T- is within 0.01 tau of 0
in the 10 Hz multiplicative run; and the distance finds two point masses 0.05 apart 0.05 apart within 1e-4, and a
histogram 0 from itself.

What it cannot check: the paper's own simulations, which were not released; its diffusion constant, "presented
elsewhere"; the abstract's last sentence, on temporally correlated cells.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 snn/rubin.py
"""

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

TEST = ("Refuted if, in the paper's network (1000 excitatory synapses, independent Poisson inputs, an "
        "integrate-and-fire cell: tau_m 20 ms, tau_s 5 ms, V_s 5, g_s 0.01, threshold 1, reset 0) under its "
        "multiplicative rule (f+ = 1 - w, f- = alpha w; alpha 1.05, lambda 0.005, tau 10 ms, all pairs), run "
        "3,000 s from uniform weights, the weight distributions of the last 1,000 s at inputs of 10, 20, 30 and "
        "40 Hz, or at 10 Hz with g_s raised to 0.015 and 0.02 to raise the output rate, lie 0.05 or more apart in "
        "Wasserstein distance; or any run's halves, or a run from all weights at 1, lie 0.01 or more apart.")

N = 1000
DT = 0.1
TAU_M, TAU_S, V_S, V_TH, V_RESET = 20.0, 5.0, 5.0, 1.0, 0.0
TAU, LAMBDA, ALPHA = 10.0, 0.005, 1.05
W_FIXED = 0.5
NBIN = 10000
GS = 0.01

RATES = (10, 20, 30, 40)
GS_POST = (0.015, 0.02)
WARM, MEAS = 2000.0, 1000.0
ADD_WARM, ADD_MEAS = 45000.0, 5000.0
SNAP, WINDOW = 10000, 100000          # steps: 1 s and 10 s
APART, HALVES = 0.05, 0.01
SINGLE_RATE, SINGLE_T, SINGLE_FROM = 10.0, 3000.0, 1000.0
SINGLE_DTS = (-50.0, -20.0, -10.0, -5.0, 5.0, 10.0, 20.0, 50.0)
EQ_WITHIN = 0.01
LIMIT = 200

PAPER = {"rates_out": {10: 16.4, 20: 80.6, 30: 136.8, 40: 192.3},
         "means": {10: 0.505, 20: 0.490, 30: 0.490, 40: 0.491},
         "chi": {10: 0.031, 20: 0.002, 30: 0.0014, 40: 0.0008},
         "fig2b": (0.505, 0.018),
         "add_rates_out": {10: 18.0, 20: 20.0, 30: 21.5, 40: 22.2},
         "add_means": {10: 0.509, 20: 0.262, 30: 0.179, 40: 0.137},
         "add_chi": {10: 0.022, 20: 0.021, 30: 0.019, 40: 0.019},
         "add_shares_10": (0.39, 0.41),
         "single_mult": {10.0: 0.817, -10.0: 0.169}}

OUTPUTS = ("w1_rates", "w1_rates_max", "w1_post", "w1_post_max", "w1_halves_max", "w1_start", "means", "sds",
           "rates_out", "chi", "additive", "additive_more", "single", "equilibration", "conditions_met",
           "conditions_total", "test_passed", "controls_passed", "controls_total")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- seeds and the generator

def words(seed, label):
    """Four 64-bit words for xoshiro256**, from SHA-256 of seed and label (never all zero)."""
    h = hashlib.sha256(f"{seed}/{label}".encode()).digest()
    w = [int.from_bytes(h[8 * i:8 * i + 8], "big") for i in range(4)]
    if not any(w):
        w[0] = 1
    return [f"{x:016x}" for x in w]


MASK = (1 << 64) - 1


def _rotl(v, k):
    return ((v << k) | (v >> (64 - k))) & MASK


class Xoshiro:
    def __init__(self, w):
        self.s = [int(x, 16) for x in w]

    def next64(self):
        s = self.s
        r = (_rotl((s[1] * 5) & MASK, 7) * 9) & MASK
        t = (s[1] << 17) & MASK
        s[2] ^= s[0]
        s[3] ^= s[1]
        s[1] ^= s[2]
        s[0] ^= s[3]
        s[2] ^= t
        s[3] = _rotl(s[3], 45)
        return r

    def unif(self):
        return (self.next64() >> 11) * 2.0 ** -53

    def below(self, m):
        return int(self.unif() * m)

    def poisson(self, lam, emlam):
        u, p = self.unif(), emlam
        c, k = p, 0
        while u >= c and k < 1000:
            k += 1
            p *= lam / k
            c += p
        return k


def fminus(rule, x):
    return ALPHA * x if rule else ALPHA


def fplus(rule, x):
    return 1.0 - x if rule else 1.0


# ---------------------------------------------------------------- the plain implementation (control)

def plain_run(w4, rule, rate, gs, warm, meas, start, plastic, snap, window):
    """The C program's "run", step for step in Python's floats (the same operations in the same order)."""
    rng = Xoshiro(w4)
    w = [W_FIXED] + [rng.unif() if start == "u" else (1.0 if start == "1" else 0.5) for _ in range(N - 1)]
    P, last = [0.0] * N, [0] * N
    hist = [[0] * NBIN for _ in range(3)]
    warm_steps, meas_steps = round(warm / (DT * 1e-3)), round(meas / (DT * 1e-3))
    total = warm_steps + meas_steps
    nsnap = meas_steps // snap
    lam = N * rate * DT * 1e-3
    emlam = math.exp(-lam)
    dec_s, dec_k = math.exp(-DT / TAU_S), math.exp(-DT / TAU)
    v, g, M = V_RESET, 0.0, 0.0
    post_n = pre_n = pre0 = pre_pl = snaps = 0
    g_sum = splus0 = sminus0 = spluspool = sminuspool = 0.0
    wvals = []
    win_spikes = 0
    windows = []
    for n in range(total):
        measuring = n >= warm_steps
        k = rng.poisson(lam, emlam)
        for _ in range(k):
            a = rng.below(N)
            g += gs * w[a]
            if measuring:
                pre_n += 1
                if a == 0:
                    pre0 += 1
                else:
                    pre_pl += 1
            if not plastic:
                continue
            if a == 0:
                if measuring:
                    sminus0 += M
            else:
                w[a] -= LAMBDA * fminus(rule, w[a]) * M
                if w[a] < 0.0:
                    w[a] = 0.0
                if measuring:
                    sminuspool += M
            P[a] = P[a] * math.exp(-(n - last[a]) * DT / TAU) + 1.0
            last[a] = n
        G = 1.0 + g
        vinf = g * V_S / G
        v = vinf + (v - vinf) * math.exp(-DT * G / TAU_M)
        if measuring:
            g_sum += g
        if v >= V_TH:
            v = V_RESET
            win_spikes += 1
            if measuring:
                post_n += 1
            if plastic:
                M += 1.0
                for a in range(N):
                    p = P[a] * math.exp(-(n - last[a]) * DT / TAU)
                    P[a] = p
                    last[a] = n
                    if a == 0:
                        if measuring:
                            splus0 += p
                        continue
                    w[a] += LAMBDA * fplus(rule, w[a]) * p
                    if w[a] > 1.0:
                        w[a] = 1.0
                    if measuring:
                        spluspool += p
        g *= dec_s
        M *= dec_k
        if measuring and (n + 1 - warm_steps) % snap == 0:
            half = 1 if snaps < nsnap // 2 else 2
            for a in range(1, N):
                b = int(w[a] * NBIN)
                b = min(max(b, 0), NBIN - 1)
                hist[0][b] += 1
                hist[half][b] += 1
                wvals.append(w[a])
            snaps += 1
        if (n + 1) % window == 0:
            m = 0.0
            for a in range(1, N):
                m += w[a]
            windows.append(f"{m / (N - 1):.9f}:{win_spikes / (window * DT * 1e-3):.2f}")
            win_spikes = 0
    T = meas_steps * DT * 1e-3
    nw = len(wvals)
    wmean = sum(wvals) / nw if nw else 0.0
    wsd = math.sqrt(sum((x - wmean) ** 2 for x in wvals) / (nw - 1)) if nw > 1 else 0.0
    return {"post_spikes": post_n, "rate": post_n / T, "pre_spikes": pre_n, "pre_fixed": pre0, "pre_plastic": pre_pl,
            "g_mean": g_sum / meas_steps, "splus_fixed": splus0, "sminus_fixed": sminus0, "splus_pool": spluspool,
            "sminus_pool": sminuspool, "snapshots": snaps, "w_mean": wmean, "w_sd": wsd, "hist": hist,
            "weights": w, "windows": windows}


# ---------------------------------------------------------------- the C program

def build(work):
    exe = os.path.join(work, "rubin")
    subprocess.run(["gcc", "-O2", "-ffp-contract=off", "-std=gnu11", "-o", exe, os.path.join(HERE, "rubin.c"), "-lm"],
                   check=True)
    return exe


def c_run(exe, w4, rule, rate, gs, warm, meas, start, plastic, work, label, snap=SNAP, window=WINDOW):
    prefix = os.path.join(work, label.replace("/", "_"))
    out = subprocess.run([exe, "run", *w4, str(int(rule)), repr(float(rate)), repr(float(gs)), repr(float(warm)),
                          repr(float(meas)), start, str(int(plastic)), str(int(snap)), str(int(window)), prefix],
                         check=True, capture_output=True, text=True).stdout
    got = {}
    for line in out.splitlines():
        k, _, v = line.partition("=")
        got[k] = v
    res = {k: int(got[k]) for k in ("post_spikes", "pre_spikes", "pre_fixed", "pre_plastic", "snapshots")}
    for k in ("rate", "g_mean", "splus_fixed", "sminus_fixed", "splus_pool", "sminus_pool", "w_mean", "w_sd"):
        res[k] = float(got[k])
    res["windows"] = got["wmean_window"].split(",") if got.get("wmean_window") else []
    hist = [[0] * NBIN for _ in range(3)]
    with open(prefix + ".hist") as fh:
        for b, line in enumerate(fh):
            x = line.split()
            for j in range(3):
                hist[j][b] = int(x[j])
    res["hist"] = hist
    with open(prefix + ".w") as fh:
        res["weights"] = [float(x) for x in fh.read().split()]
    res["meas"] = float(meas)
    return res


def c_pair(exe, rule, dt_ms, w):
    out = subprocess.run([exe, "pair", str(int(rule)), repr(float(dt_ms)), repr(float(w))], check=True,
                         capture_output=True, text=True).stdout
    return float(out.strip().split("=")[1])


def c_const(exe, g):
    out = subprocess.run([exe, "const", repr(float(g))], check=True, capture_output=True, text=True).stdout
    return float(out.strip().split("=")[1])


# ---------------------------------------------------------------- measures (rule 4)

def wasserstein(h1, h2):
    """The earth mover's distance between two histograms on NBIN equal bins of [0, 1]."""
    n1, n2 = sum(h1), sum(h2)
    if n1 == 0 or n2 == 0:
        return float("nan")
    c1 = c2 = 0
    total = 0.0
    for b in range(NBIN - 1):
        c1 += h1[b]
        c2 += h2[b]
        total += abs(c1 / n1 - c2 / n2)
    return total / NBIN


def tau_chance():
    return DT / (1.0 - math.exp(-DT / TAU))


def t_plus(splus, n_in, n_out, meas):
    """T+ (ms): the K-weighted pairs with the output after the input, less their number by chance."""
    if n_in == 0 or n_out == 0:
        return float("nan")
    return splus * (meas * 1000.0) / (n_in * n_out) - tau_chance()


def t_minus(sminus, n_in, n_out, meas):
    if n_in == 0 or n_out == 0:
        return float("nan")
    return sminus * (meas * 1000.0) / (n_in * n_out) - (tau_chance() - DT)


def chis(res):
    tp0 = t_plus(res["splus_fixed"], res["pre_fixed"], res["post_spikes"], res["meas"])
    tpp = t_plus(res["splus_pool"], res["pre_plastic"], res["post_spikes"], res["meas"])
    tmp = t_minus(res["sminus_pool"], res["pre_plastic"], res["post_spikes"], res["meas"])
    return {"chi_fixed": tp0 / (W_FIXED * TAU), "chi_pool": tpp / (res["w_mean"] * TAU) if res["w_mean"] > 0 else
            float("nan"), "t_plus_fixed_ms": tp0, "t_plus_pool_ms": tpp, "t_minus_pool_ms": tmp}


def shares(hist):
    n = sum(hist)
    lo = sum(hist[:NBIN // 10]) / n
    hi = sum(hist[9 * NBIN // 10:]) / n
    return lo, hi


def equilibration(windows, wmean):
    """The first 10 s mark after which every 10 s mean weight stays within EQ_WITHIN of the window's mean."""
    means = [float(x.split(":")[0]) for x in windows]      # the mean weight at the end of each 10 s
    t = None
    for i in range(len(means) - 1, -1, -1):
        if abs(means[i] - wmean) >= EQ_WITHIN:
            break
        t = 10.0 * (i + 1)
    return t


def w0_formula(dt, r=SINGLE_RATE):
    """Eq. 9: the multiplicative rule's zero of the drift for an output that copies the input shifted by dt."""
    tr = TAU * 1e-3 * r
    if dt > 0:
        return 1.0 - ALPHA / (1.0 + ALPHA + math.exp(-dt / TAU) / tr)
    return 1.0 / (1.0 + ALPHA * (1.0 + math.exp(dt / TAU) / tr))


def single_synapse(seed, rule, dt, r=SINGLE_RATE, T=SINGLE_T, start_at=SINGLE_FROM):
    """One synapse in continuous time: the input a Poisson train at r, the output the same train shifted by dt (ms).
    All pairs by traces; the weight starts at 0.5 and its mean is taken at every whole second from start_at."""
    rng = Xoshiro(words(seed, f"rubin/single/{rule}/{dt:g}"))
    pre, t = [], 0.0
    while True:
        t += -math.log(1.0 - rng.unif()) / r * 1000.0
        if t >= T * 1000.0:
            break
        pre.append(t)
    events = sorted([(x, 0) for x in pre] + [(x + dt, 1) for x in pre if 0.0 <= x + dt < T * 1000.0])
    w, P, M, tp, tm = 0.5, 0.0, 0.0, 0.0, 0.0
    total, count, nxt = 0.0, 0, start_at * 1000.0
    for t, kind in events:
        while nxt <= t and nxt < T * 1000.0:
            total += w
            count += 1
            nxt += 1000.0
        if kind == 0:
            m = M * math.exp(-(t - tm) / TAU)
            w -= LAMBDA * fminus(rule, w) * m
            w = max(w, 0.0)
            P = P * math.exp(-(t - tp) / TAU) + 1.0
            tp = t
        else:
            p = P * math.exp(-(t - tp) / TAU)
            w += LAMBDA * fplus(rule, w) * p
            w = min(w, 1.0)
            M = M * math.exp(-(t - tm) / TAU) + 1.0
            tm = t
    while nxt < T * 1000.0:
        total += w
        count += 1
        nxt += 1000.0
    return total / count


# ---------------------------------------------------------------- the test and the controls

def conditions(dist, halves, start):
    """dist: {(a, b): distance} for the rate pairs and the g_s pairs; halves: {run: distance}; start: distance."""
    cond = {}
    for i, a in enumerate(RATES):
        for b in RATES[i + 1:]:
            cond[f"{a} and {b} Hz less than {APART} apart"] = dist[("rate", a, b)] < APART
    gss = (GS,) + GS_POST
    for i, a in enumerate(gss):
        for b in gss[i + 1:]:
            cond[f"g_s {a:g} and {b:g} at 10 Hz less than {APART} apart"] = dist[("gs", a, b)] < APART
    for run, d in halves.items():
        cond[f"{run}: halves less than {HALVES} apart"] = d < HALVES
    cond[f"from every weight at 1, less than {HALVES} from the uniform start"] = start < HALVES
    return cond


def point_mass(x):
    h = [0] * NBIN
    h[min(int(x * NBIN), NBIN - 1)] = 1
    return h


def controls(exe, seed, eq10, work):
    same = True
    for rule in (0, 1):
        w4 = words(seed, f"rubin/control/plain/{rule}")
        c = c_run(exe, w4, rule, 10.0, GS, 0.2, 1.0, "u", 1, work, f"plain{rule}", snap=1000, window=1000)
        p = plain_run(w4, rule, 10.0, GS, 0.2, 1.0, "u", 1, 1000, 1000)
        for k in ("post_spikes", "rate", "pre_spikes", "pre_fixed", "pre_plastic", "g_mean", "splus_fixed",
                  "sminus_fixed", "splus_pool", "sminus_pool", "snapshots", "hist", "weights", "windows"):
            same = same and c[k] == p[k]
        same = same and abs(c["w_mean"] - p["w_mean"]) < 1e-12 and abs(c["w_sd"] - p["w_sd"]) < 1e-12
        same = same and c["post_spikes"] > 0
    k = math.exp(-0.5)
    pair_ok = True
    for rule in (0, 1):
        pair_ok = pair_ok and abs(c_pair(exe, rule, 5.0, 0.5) - LAMBDA * fplus(rule, 0.5) * k) < 1e-12
        pair_ok = pair_ok and abs(c_pair(exe, rule, -5.0, 0.5) + LAMBDA * fminus(rule, 0.5) * k) < 1e-12
    const_ok = True
    for g in (0.5, 1.0):
        vinf = g * V_S / (1.0 + g)
        t = TAU_M / (1.0 + g) * math.log(vinf / (vinf - 1.0))
        const_ok = const_ok and abs(c_const(exe, g) - t) <= DT + 1e-9
    held = c_run(exe, words(seed, "rubin/control/held"), 1, 10.0, GS, 0.0, 20.0, "h", 0, work, "held")
    n_exp = N * 10.0 * 20.0
    counts_ok = abs(held["pre_spikes"] - n_exp) < 4 * math.sqrt(n_exp)
    g_exp = GS * N * 0.5 * 10.0 * TAU_S * 1e-3
    g_ok = abs(held["g_mean"] / g_exp - 1.0) < 0.02
    tm = chis(eq10)["t_minus_pool_ms"]
    tminus_ok = abs(tm) < 0.01 * TAU
    a, b = point_mass(0.30), point_mass(0.35)
    dist_ok = abs(wasserstein(a, b) - 0.05) < 1e-4 and wasserstein(eq10["hist"][0], eq10["hist"][0]) == 0.0
    return {"the C program matches the plain implementation bit for bit over 1.2 s under each rule": bool(same),
            "one pre and one post spike 5 ms apart change w = 0.5 by lambda f+ e^(-1/2) and -lambda f- e^(-1/2)":
                pair_ok,
            "under a constant conductance of 0.5 and 1 the first spike is within a step of the analytic time":
                const_ok,
            "20 s with weights held at 0.5: arrivals within four standard errors of 200,000": counts_ok,
            "20 s with weights held at 0.5: mean conductance within 2% of 0.25": g_ok,
            "the 10 Hz multiplicative run's pooled T- within 0.01 tau of 0": bool(tminus_ok),
            "the distance: point masses 0.05 apart are 0.05 apart, a histogram 0 from itself": dist_ok}


def fmt(x, nd=3):
    return f"{x:.{nd}f}"


def secs(t):
    return "-" if t is None else f"{t:.0f} s"


def run(seed, results="results", log=sys.stderr):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    if shutil.which("gcc") is None:
        raise Refused("no gcc in this image")
    os.makedirs(results, exist_ok=True)
    work = tempfile.mkdtemp(prefix="work-", dir=results)   # the sandbox's /tmp cannot run what is built in it
    exe = build(work)

    mult = {}
    for r in RATES:
        res = c_run(exe, words(seed, f"rubin/mult/{r}"), 1, r, GS, WARM, MEAS, "u", 1, work, f"mult{r}")
        res.update(chis(res))
        mult[r] = res
        print(f"multiplicative {r} Hz: output {res['rate']:.2f} Hz, mean w {res['w_mean']:.4f}, "
              f"SD {res['w_sd']:.4f}, chi {res['chi_fixed']:.4f}/{res['chi_pool']:.4f}", file=log)
    post = {GS: mult[10]}
    for gs in GS_POST:
        res = c_run(exe, words(seed, f"rubin/mult/gs/{gs:g}"), 1, 10.0, gs, WARM, MEAS, "u", 1, work, f"multgs{gs:g}")
        res.update(chis(res))
        post[gs] = res
        print(f"multiplicative 10 Hz, g_s {gs:g}: output {res['rate']:.2f} Hz, mean w {res['w_mean']:.4f}, "
              f"SD {res['w_sd']:.4f}", file=log)
    one = c_run(exe, words(seed, "rubin/mult/one/10"), 1, 10.0, GS, WARM, MEAS, "1", 1, work, "multone")
    one.update(chis(one))
    print(f"multiplicative 10 Hz from every weight at 1: output {one['rate']:.2f} Hz, mean w {one['w_mean']:.4f}",
          file=log)

    dist = {}
    for i, a in enumerate(RATES):
        for b in RATES[i + 1:]:
            dist[("rate", a, b)] = wasserstein(mult[a]["hist"][0], mult[b]["hist"][0])
    gss = (GS,) + GS_POST
    for i, a in enumerate(gss):
        for b in gss[i + 1:]:
            dist[("gs", a, b)] = wasserstein(post[a]["hist"][0], post[b]["hist"][0])
    halves = {f"{r} Hz": wasserstein(mult[r]["hist"][1], mult[r]["hist"][2]) for r in RATES}
    for gs in GS_POST:
        halves[f"10 Hz, g_s {gs:g}"] = wasserstein(post[gs]["hist"][1], post[gs]["hist"][2])
    halves["10 Hz from every weight at 1"] = wasserstein(one["hist"][1], one["hist"][2])
    start = wasserstein(one["hist"][0], mult[10]["hist"][0])

    add = {}
    for r in RATES:
        res = c_run(exe, words(seed, f"rubin/add/{r}"), 0, r, GS, ADD_WARM, ADD_MEAS, "u", 1, work, f"add{r}")
        res.update(chis(res))
        res["shares"] = shares(res["hist"][0])
        res["halves"] = wasserstein(res["hist"][1], res["hist"][2])
        add[r] = res
        print(f"additive {r} Hz: output {res['rate']:.2f} Hz, mean w {res['w_mean']:.4f}, below 0.1 "
              f"{res['shares'][0]:.3f}, from 0.9 {res['shares'][1]:.3f}, chi {res['chi_fixed']:.4f}/"
              f"{res['chi_pool']:.4f}", file=log)
    add_dist = {f"{a}-{b}": wasserstein(add[a]["hist"][0], add[b]["hist"][0])
                for i, a in enumerate(RATES) for b in RATES[i + 1:]}
    eq_mult = equilibration(mult[10]["windows"], mult[10]["w_mean"])
    eq_one = equilibration(one["windows"], one["w_mean"])
    eq_add = equilibration(add[10]["windows"], add[10]["w_mean"])

    single = {}
    for rule in (1, 0):
        for dt in SINGLE_DTS:
            single[(rule, dt)] = single_synapse(seed, rule, dt)
    print("single synapse: " + ", ".join(f"{'mult' if k[0] else 'add'} {k[1]:g} ms {v:.3f}"
                                          for k, v in single.items()), file=log)

    ctl = controls(exe, seed, mult[10], work)
    print(f"controls: {sum(ctl.values())} of {len(ctl)}", file=log)
    if not all(ctl.values()):
        raise AssertionError(f"a control failed: {[c for c, ok in ctl.items() if not ok]}")
    cond = conditions(dist, halves, start)

    def rp(key, nd=3, d=mult):
        return ", ".join(f"{r} Hz {fmt(d[r][key], nd)}" for r in RATES)

    def gp(key, nd=3):
        return "; g_s " + ", ".join(f"{gs:g} {fmt(post[gs][key], nd)}" for gs in GS_POST)

    values = {
        "w1_rates": "by input rate: " + ", ".join(f"{a}-{b} {dist[('rate', a, b)]:.4f}"
                                                  for i, a in enumerate(RATES) for b in RATES[i + 1:]),
        "w1_rates_max": round(max(v for k, v in dist.items() if k[0] == "rate"), 5),
        "w1_post": "at 10 Hz by g_s: " + ", ".join(f"{a:g}-{b:g} {dist[('gs', a, b)]:.4f}"
                                                   for i, a in enumerate(gss) for b in gss[i + 1:]),
        "w1_post_max": round(max(v for k, v in dist.items() if k[0] == "gs"), 5),
        "w1_halves_max": round(max(halves.values()), 5),
        "w1_start": round(start, 5),
        "means": "mean w: " + rp("w_mean", 4) + gp("w_mean", 4),
        "sds": "SD of w: " + rp("w_sd", 4) + gp("w_sd", 4),
        "rates_out": "output Hz: " + rp("rate", 1) + gp("rate", 1),
        "chi": "chi, synapse at 0.5/pooled: " + ", ".join(
            f"{r} Hz {mult[r]['chi_fixed']:.4f}/{mult[r]['chi_pool']:.4f}" for r in RATES),
        "additive": ("additive, 10/20/30/40 Hz: output " + "/".join(fmt(add[r]["rate"], 1) for r in RATES)
                     + " Hz; mean w " + "/".join(fmt(add[r]["w_mean"], 3) for r in RATES)
                     + "; chi " + "/".join(fmt(add[r]["chi_pool"], 3) for r in RATES)),
        "additive_more": (f"additive at 10 Hz: below 0.1 {add[10]['shares'][0]:.3f}, from 0.9 "
                          f"{add[10]['shares'][1]:.3f}; Wasserstein 10-40 Hz {add_dist['10-40']:.3f}; halves max "
                          f"{max(add[r]['halves'] for r in RATES):.4f}"),
        "single": ("one synapse, +10/-10 ms: multiplicative " + f"{single[(1, 10.0)]:.3f}/{single[(1, -10.0)]:.3f}"
                   + f" (Eq. 9 {w0_formula(10.0):.3f}/{w0_formula(-10.0):.3f}); additive "
                   + f"{single[(0, 10.0)]:.3f}/{single[(0, -10.0)]:.3f}"),
        "equilibration": (f"10 Hz, mean w within {EQ_WITHIN} for good: multiplicative {secs(eq_mult)} from uniform "
                          f"(its mean starts at 0.5), {secs(eq_one)} from all at 1; additive {secs(eq_add)} from "
                          f"uniform"),
        "conditions_met": sum(cond.values()),
        "conditions_total": len(cond),
        "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()),
        "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")

    def keep(res):
        d = {k: res[k] for k in ("rate", "post_spikes", "pre_spikes", "pre_fixed", "pre_plastic", "g_mean",
                                 "w_mean", "w_sd", "snapshots", "chi_fixed", "chi_pool", "t_plus_fixed_ms",
                                 "t_plus_pool_ms", "t_minus_pool_ms")}
        d["histogram_100"] = [sum(res["hist"][0][100 * j:100 * (j + 1)]) for j in range(NBIN // 100)]
        d["windows_10s"] = res["windows"]
        return d

    detail = {"conditions": cond, "controls": ctl,
              "distances": {"/".join(str(x) for x in k): v for k, v in dist.items()},
              "halves": halves, "start": start,
              "multiplicative": {str(r): keep(mult[r]) for r in RATES},
              "multiplicative_gs": {f"{gs:g}": keep(post[gs]) for gs in GS_POST},
              "multiplicative_from_one": keep(one),
              "additive": {str(r): dict(keep(add[r]), shares=add[r]["shares"], halves=add[r]["halves"])
                           for r in RATES},
              "additive_distances": add_dist,
              "equilibration_s": {"multiplicative_10": eq_mult, "multiplicative_10_from_one": eq_one,
                                  "additive_10": eq_add},
              "single_synapse": {f"{'multiplicative' if k[0] else 'additive'} {k[1]:g} ms": v
                                 for k, v in single.items()},
              "w0_formula": {f"{dt:g} ms": w0_formula(dt) for dt in SINGLE_DTS},
              "dt0_ms": TAU * math.log(1.0 / ((ALPHA - 1.0) * TAU * 1e-3 * SINGLE_RATE)),
              "paper": {k: ({str(a): b for a, b in v.items()} if isinstance(v, dict) else v) for k, v in PAPER.items()},
              "one_over_one_plus_alpha": 1.0 / (1.0 + ALPHA)}
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True)
        fh.write("\n")
    shutil.rmtree(work, ignore_errors=True)
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"rubin: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
