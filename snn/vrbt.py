#!/usr/bin/env python3
"""van Rossum, Bi & Turrigiano (2000): under the paper's STDP rule, random stimulation drives a neuron's synaptic
weights to an equilibrium distribution that is stable, unimodal and positively skewed.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from M. C. W. van Rossum, G. Q. Bi and
G. G. Turrigiano, "Stable Hebbian learning from spike timing-dependent plasticity" (J Neurosci 20(23), 8812-8821,
2000; pmid:11102489, open in PMC as PMC6773092): "After random stimulation, the synaptic weights reach an equilibrium
distribution which is stable, unimodal, and has positive skew."

The test, as registered: see TEST below. Standard library and the image's gcc: the neuron is simulated in C
(snn/vrbt.c, compiled here). No data are read: the inputs are generated under the seed. Every rule below was fixed
before any run of the model.

1. The model, as the paper's Methods give it (read on PMC's page; the publisher allows no download of the text): one
   leaky integrate-and-fire neuron, input resistance 100 MOhm (a leak of 10 nS), membrane time constant 20 ms, rest
   -60 mV, threshold -50 mV, reset to rest after a spike; 100 excitatory synapses (reversal 0 mV, 5 ms) whose weights
   are conductances in pS, and 25 inhibitory ones (reversal -70 mV, 5 ms) "fixed at a conductance of 2000 pS" and not
   plastic; every input an independent Poisson train at 20 Hz (the inhibitory trains' rate is the Methods', the
   excitatory one Figure 3's "20 Hz input rate"). The membrane: tau_m dV/dt = (V_rest - V) + g_ex (E_ex - V) +
   g_in (E_in - V), conductances in units of the leak, each arrival adding its synapse's conductance and both decaying
   with 5 ms.
2. The rule (Eqs. 1 and 2): an arrival dt before a postsynaptic spike potentiates its synapse by (c_p + nu w)
   exp(-dt/tau); a postsynaptic spike dt before an arrival depresses it by (-c_d w + nu w) exp(-dt/tau); tau = 20 ms
   for both ("the same time constant for depression and potentiation"); c_p = 1 pS ("In the simulations we use
   cp = 1 pS"), c_d = 0.003, nu Gaussian with mean 0 and standard deviation 0.015, a fresh draw for every change
   ("all plasticity events are independent"). Pairing, as the Methods state it: "only the first postsynaptic spike
   after the synaptic event leads to potentiation" and "only the first synaptic event after a given spike depresses
   the synapse": so at a postsynaptic spike every arrival since the previous one potentiates once, and at an arrival
   every postsynaptic spike since the synapse's previous arrival depresses once, oldest first. No bounds: the paper
   imposes none on this rule.
3. What the paper leaves unstated, fixed here: steps of 0.1 ms; in each, the inhibitory and the excitatory arrivals (a
   Poisson count for each population, each excitatory one given to a synapse drawn uniformly, which is the
   superposition of independent Poisson trains), then the membrane by exponential Euler with the step's conductances,
   then the spike if V >= -50 mV, then one step of decay; an arrival in the step of a postsynaptic spike came before
   it; no refractory period (none is given); the generator xoshiro256**, seeded from SHA-256 of the seed and the
   run's label, and nu by Box-Muller. Initial weights: each drawn uniformly from [0, 2 c_p/c_d) = [0, 666.7) pS (mean
   c_p/c_d, where the rule's mean drift vanishes without a synapse's own share in firing).
4. The reading of "2000 pS": each inhibitory synapse's conductance, or the 25 together (80 pS each). Both readings are
   run, 10 runs each from the uniform start; the test then uses the one whose mean output rate over the window is
   nearer the "postsynaptic firing rate ~25 Hz" of Figure 3's legend (the rate is not one of the tested properties).
5. Runs: 10 runs (Figure 3's weights "were averaged over 10 runs") of 4,000 s each; snapshots of all 100 weights at
   the end of every second from 2,000 s on, the window's halves being 2,001-3,000 s and 3,001-4,000 s; the pooled
   distribution is all 10 runs' snapshots over the whole window (2,000,000 weights). For the chosen reading, 10 more
   runs from each of two other starts: every weight at 2 c_p/c_d = 666.7 pS, and weights drawn from an exponential
   distribution of mean c_p/c_d. (A start whose weights are too weak to make the neuron fire never moves, since every
   change needs a postsynaptic spike, so neither other start is below the uniform one's mean.)
6. The statistics: weights are binned at 0.5 pS from 0 to 5,000 pS (one bin above); moments are exact sums. Skewness is
   the sample skewness m3 / m2^(3/2). Unimodal: a Gaussian kernel density of the pooled bins, bandwidth Silverman's
   0.9 min(sd, IQR/1.34) n^(-1/5) with n = 1,000 (the 10 runs' 100 synapses, the independent weights at any one time),
   evaluated at every bin centre from max(0, min - 3h) to max + 3h, has exactly one local maximum (a point above its
   left neighbour and not below its right one, the grid's ends counting as lower) of height at least 1% of the
   highest. The Kolmogorov-Smirnov distance between two binned distributions is the largest difference of their
   cumulative shares at a bin edge.
7. The test's five conditions: one mode; skewness above 0; the halves less than 0.05 apart; and the pooled
   distributions of each other start less than 0.05 from the uniform start's. test_passed is 1 if all five hold.
8. Beside the test, none of it counted: both readings' output rates (Figure 3: about 25 Hz) and the other reading's
   mode count, skewness and halves' distance; the weights' mean, standard deviation, median, IQR and mode; the
   peak the paper derives for large noise, w = c_p / (c_d - c_p/W_tot + 2 sigma^2), with W_tot = t_w rho N <w>
   (t_w = 20 ms, rho = 20 Hz, N = 100, <w> the pooled mean), beside the density's mode; the bandwidth; and the range.

Controls (controls_passed counts those that behave as stated; the run stops if any fails): the C program matches a
plain implementation written here over 0.5 s with STDP and noise on (under the weaker inhibition, so that the neuron
fires and every rule is exercised), bit for bit in spikes, arrivals, conductances,
histograms, extremes and every final weight (moments, summed in long double in C, within 1e-9); with the noise off, one
arrival 10 ms before a postsynaptic spike raises a synapse by c_p e^(-1/2), and one 10 ms after lowers it by c_d w
e^(-1/2); two arrivals before a postsynaptic spike are both potentiated, and a second spike potentiates nothing; two
postsynaptic spikes before an arrival both depress it, and a second arrival is not depressed; in 20 s with the weights
held at 300 pS, the arrivals are within four standard errors of 40,000 and 10,000 and the mean conductances within 2% of
100 x 20 Hz x 5 ms x 0.03 = 0.3 and 25 x 20 Hz x 5 ms x 0.2 = 0.5; the statistics find one mode and positive skewness in
a gamma sample (shape 4), two modes in a mixture of two normals six standard deviations apart, and negative skewness
in a mirrored gamma sample; and with potentiation alone (c_d = 0) the halves of 50-100 s are 0.05 or more apart.

What it cannot check: the paper's own simulations, which were not released; the analytic solution's exact form
(Eq. 14), which the check does not need; its Figure 3B comparison with measured quantal amplitudes.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 snn/vrbt.py
"""

import concurrent.futures
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

TEST = ("Refuted if, in the paper's model (a leaky integrate-and-fire neuron; 100 plastic excitatory and 25 fixed "
        "inhibitory conductance synapses on independent 20 Hz Poisson inputs; potentiation (c_p + νw)e^(−Δt/τ), "
        "depression (νw − c_d·w)e^(−Δt/τ), c_p = 1 pS, c_d = 0.003, ς = 0.015, τ = 20 ms; 2,000 pS per inhibitory "
        "synapse or in all, whichever fires nearer its 25 Hz), the weights of 10 runs over 2,000–4,000 s are not "
        "unimodal (one kernel-density mode) with positive skewness, or not stable: the window's halves, or runs from "
        "two other starts, lie 0.05 or more apart in Kolmogorov–Smirnov distance.")

NE, NI = 100, 25
DT = 0.1
TAU_M, V_REST, V_TH, E_EX, E_IN = 20.0, -60.0, -50.0, 0.0, -70.0
TAU_S = 5.0
G_LEAK = 10000.0
RATE = 20.0
TAU_STDP = 20.0
CP, CD, SIGMA = 1.0, 0.003, 0.015
GINH_EACH, GINH_ALL = 2000.0, 2000.0 / NI
PEND, RING = 64, 4096
NBINS, BIN = 10000, 0.5
SHIFT = 333.33333333333331

RUNS = 10
DUR, FROM, SAMPLE = 4000.0, 2000.0, 1.0
PAPER_RATE = 25.0
N_EFF = 1000
MODE_FLOOR = 0.01
KS_MAX = 0.05
LIMIT = 200
WORKERS = 4

OUTPUTS = ("modes", "skewness", "ks_halves", "ks_start_high", "ks_start_exponential", "reading", "rates", "weights",
           "density_mode", "peak_formula", "bandwidth", "other_reading", "range", "conditions_met", "conditions_total",
           "test_passed", "controls_passed", "controls_total")


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

    def gauss(self):
        u1, u2 = 1.0 - self.unif(), self.unif()
        return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


# ---------------------------------------------------------------- the plain implementation (control)

def start_weights(rng, start):
    if start == "uniform":
        return [rng.unif() * (2.0 * CP / CD) for _ in range(NE)]
    return [float(start)] * NE


def plain_run(w4, start, dur, frm, sample, ginh, cd, sigma, plastic):
    """The C program's "run", step for step in Python's floats (the same operations in the same order)."""
    rng = Xoshiro(w4)
    w = start_weights(rng, start)
    pend = [[0] * PEND for _ in range(NE)]
    pend_n, pend_head, dep_from = [0] * NE, [0] * NE, [0] * NE
    post_step = [0] * RING
    hist = [{}, {}]
    mom = [[0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]]
    wmin, wmax, underflow, pend_over = 1e300, -1e300, 0, 0
    total, from_steps = round(dur / (DT * 1e-3)), round(frm / (DT * 1e-3))
    sample_steps = round(sample / (DT * 1e-3))
    mid_steps = from_steps + (total - from_steps) // 2
    lam_in = NI * RATE * DT * 1e-3
    em_in = math.exp(-lam_in)
    lam_ex = NE * RATE * DT * 1e-3
    em_ex = math.exp(-lam_ex)
    dec, gin_unit = math.exp(-DT / TAU_S), ginh / G_LEAK
    v, gex, gin = V_REST, 0.0, 0.0
    post_count = post_meas = pre_meas = inh_meas = steps_meas = 0
    gex_sum = gin_sum = 0.0
    for n in range(total):
        measuring = n >= from_steps
        ki = rng.poisson(lam_in, em_in)
        gin += ki * gin_unit
        ke = rng.poisson(lam_ex, em_ex)
        for _ in range(ke):
            a = rng.below(NE)
            gex += w[a] / G_LEAK
            if plastic:
                for q in range(dep_from[a], post_count):
                    f = math.exp(-(n - post_step[q % RING]) * DT / TAU_STDP)
                    nu = sigma * rng.gauss()
                    w[a] += (-cd * w[a] + nu * w[a]) * f
                dep_from[a] = post_count
                if pend_n[a] == PEND:
                    pend_over += 1
                pend[a][pend_head[a]] = n
                pend_head[a] = (pend_head[a] + 1) % PEND
                if pend_n[a] < PEND:
                    pend_n[a] += 1
            if measuring:
                pre_meas += 1
        if measuring:
            inh_meas += ki
        G = 1.0 + gex + gin
        vinf = (V_REST + gex * E_EX + gin * E_IN) / G
        v = vinf + (v - vinf) * math.exp(-DT * G / TAU_M)
        if measuring:
            gex_sum += gex
            gin_sum += gin
            steps_meas += 1
        if v >= V_TH:
            v = V_REST
            post_step[post_count % RING] = n
            post_count += 1
            if measuring:
                post_meas += 1
            if plastic:
                for a in range(NE):
                    k0 = (pend_head[a] - pend_n[a] + PEND) % PEND
                    for k in range(pend_n[a]):
                        m = pend[a][(k0 + k) % PEND]
                        f = math.exp(-(n - m) * DT / TAU_STDP)
                        nu = sigma * rng.gauss()
                        w[a] += (CP + nu * w[a]) * f
                    pend_n[a] = 0
        gex *= dec
        gin *= dec
        if n + 1 > from_steps and (n + 1 - from_steps) % sample_steps == 0:
            half = 0 if n + 1 <= mid_steps else 1
            for x in w:
                if x < 0.0:
                    underflow += 1
                    continue
                b = min(int(x / BIN), NBINS)
                hist[half][b] = hist[half].get(b, 0) + 1
                d = x - SHIFT
                m4 = mom[half]
                m4[0] += 1.0
                m4[1] += d
                m4[2] += d * d
                m4[3] += d * d * d
                wmin, wmax = min(wmin, x), max(wmax, x)
    T = (total - from_steps) * DT * 1e-3
    return {"rate": post_meas / T if T > 0 else 0.0, "post_spikes": post_meas, "pre_arrivals": pre_meas,
            "inh_arrivals": inh_meas, "gex_mean": gex_sum / steps_meas if steps_meas else 0.0,
            "gin_mean": gin_sum / steps_meas if steps_meas else 0.0, "wmin": wmin, "wmax": wmax,
            "underflow": underflow, "pend_over": pend_over, "mom": mom, "hist": hist, "weights": w}


# ---------------------------------------------------------------- the C program

def build(work):
    exe = os.path.join(work, "vrbt")
    subprocess.run(["gcc", "-O2", "-ffp-contract=off", "-std=gnu11", "-o", exe, os.path.join(HERE, "vrbt.c"), "-lm"],
                   check=True)
    return exe


def parse_hist(text):
    out = {}
    if text:
        for part in text.split(","):
            b, _, c = part.partition(":")
            out[int(b)] = int(c)
    return out


def c_run(exe, w4, start, dur, frm, sample, ginh, cd, sigma, plastic, wout="-"):
    out = subprocess.run([exe, "run", *w4, str(start), repr(float(dur)), repr(float(frm)), repr(float(sample)),
                          repr(float(ginh)), repr(float(cd)), repr(float(sigma)), str(int(plastic)), wout],
                         check=True, capture_output=True, text=True).stdout
    got = {}
    for line in out.splitlines():
        k, _, v = line.partition("=")
        got[k] = v
    res = {"rate": float(got["rate"]), "post_spikes": int(got["post_spikes"]),
           "pre_arrivals": int(got["pre_arrivals"]), "inh_arrivals": int(got["inh_arrivals"]),
           "gex_mean": float(got["gex_mean"]), "gin_mean": float(got["gin_mean"]),
           "wmin": float(got["wmin"]), "wmax": float(got["wmax"]), "underflow": int(got["underflow"]),
           "pend_over": int(got["pend_over"]),
           "mom": [[float(x) for x in got[f"mom{h}"].split(",")] for h in (0, 1)],
           "hist": [parse_hist(got.get(f"hist{h}", "")) for h in (0, 1)]}
    if wout != "-":
        with open(wout) as fh:
            res["weights"] = [float(x) for x in fh.read().split()]
    return res


def c_pair(exe, w, sigma, events):
    out = subprocess.run([exe, "pair", repr(float(w)), repr(float(sigma)), events], check=True, capture_output=True,
                         text=True).stdout
    return float(out.strip().split("=")[1])


def exponential_start(seed, label):
    """One run's start: weights drawn from an exponential distribution of mean c_p/c_d."""
    rng = Xoshiro(words(seed, label + "/start"))
    return [-(CP / CD) * math.log(1.0 - rng.unif()) for _ in range(NE)]


# ---------------------------------------------------------------- statistics (rule 6)

def merge(hists):
    out = {}
    for h in hists:
        for b, c in h.items():
            out[b] = out.get(b, 0) + c
    return out


def merge_moments(moms):
    return [sum(m[i] for m in moms) for i in range(4)]


def summary(mom):
    """Mean, standard deviation and sample skewness from the sums about SHIFT."""
    n, s1, s2, s3 = mom
    if n <= 0:
        return float("nan"), float("nan"), float("nan")
    d = s1 / n
    m2 = s2 / n - d * d
    m3 = s3 / n - 3.0 * d * (s2 / n) + 2.0 * d ** 3
    sd = math.sqrt(m2) if m2 > 0 else 0.0
    return SHIFT + d, sd, (m3 / m2 ** 1.5 if m2 > 0 else float("nan"))


def quantile(hist, q):
    """The q-quantile of a binned distribution, at the centre of the bin where the cumulative share reaches q."""
    total = sum(hist.values())
    acc = 0
    for b in sorted(hist):
        acc += hist[b]
        if acc >= q * total:
            return (b + 0.5) * BIN
    return float("nan")


def bandwidth(hist, sd, n_eff=N_EFF):
    iqr = quantile(hist, 0.75) - quantile(hist, 0.25)
    spread = min(sd, iqr / 1.34) if iqr > 0 else sd
    return 0.9 * spread * n_eff ** (-0.2)


def density(hist, h):
    """The Gaussian kernel density of the bins at every bin centre from max(0, min - 3h) to max + 3h."""
    if not hist or h <= 0:
        return 0, []
    lo_b, hi_b = min(hist), max(hist)
    lo = max(0, int(math.floor(((lo_b + 0.5) * BIN - 3 * h) / BIN)))
    hi = int(math.ceil(((hi_b + 0.5) * BIN + 3 * h) / BIN))
    K = int(math.ceil(4 * h / BIN))
    kern = [math.exp(-0.5 * ((k * BIN) / h) ** 2) for k in range(-K, K + 1)]
    d = [0.0] * (hi - lo + 1)
    for b, c in hist.items():
        for k in range(-K, K + 1):
            j = b + k - lo
            if 0 <= j < len(d):
                d[j] += c * kern[k + K]
    return lo, d


def modes(hist, h, floor=MODE_FLOOR):
    """The density's local maxima (above the left neighbour, not below the right one; the ends count as lower) of
    height at least floor times the highest, as (centre, height)."""
    lo, d = density(hist, h)
    if not d:
        return []
    top = max(d)
    out = []
    for i, x in enumerate(d):
        left = d[i - 1] if i > 0 else -1.0
        right = d[i + 1] if i + 1 < len(d) else -1.0
        if x > left and x >= right and x >= floor * top:
            out.append(((lo + i + 0.5) * BIN, x))
    return out


def ks(h1, h2):
    n1, n2 = sum(h1.values()), sum(h2.values())
    if n1 == 0 or n2 == 0:
        return float("nan")
    a1 = a2 = 0
    best = 0.0
    for b in sorted(set(h1) | set(h2)):
        a1 += h1.get(b, 0)
        a2 += h2.get(b, 0)
        best = max(best, abs(a1 / n1 - a2 / n2))
    return best


def bin_values(values):
    hist = {}
    for x in values:
        if x < 0:
            continue
        b = min(int(x / BIN), NBINS)
        hist[b] = hist.get(b, 0) + 1
    return hist


def moments_of(values):
    m = [0.0, 0.0, 0.0, 0.0]
    for x in values:
        d = x - SHIFT
        m[0] += 1.0
        m[1] += d
        m[2] += d * d
        m[3] += d * d * d
    return m


# ---------------------------------------------------------------- runs

def run_set(exe, seed, label, start, ginh, runs=RUNS):
    """`runs` runs of DUR seconds in parallel (results do not depend on the order), each under its own label."""
    def one(r):
        return c_run(exe, words(seed, f"{label}/{r}"), start, DUR, FROM, SAMPLE, ginh, CD, SIGMA, 1)
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        return list(pool.map(one, range(runs)))


def pooled(res):
    h0, h1 = merge(r["hist"][0] for r in res), merge(r["hist"][1] for r in res)
    return {"halves": (h0, h1), "all": merge([h0, h1]),
            "mom": merge_moments([r["mom"][0] for r in res] + [r["mom"][1] for r in res]),
            "rate": sum(r["rate"] for r in res) / len(res),
            "wmin": min(r["wmin"] for r in res), "wmax": max(r["wmax"] for r in res),
            "underflow": sum(r["underflow"] for r in res), "pend_over": sum(r["pend_over"] for r in res),
            "overflow": sum(r["hist"][h].get(NBINS, 0) for r in res for h in (0, 1))}


def describe(p):
    mean, sd, skew = summary(p["mom"])
    h = bandwidth(p["all"], sd)
    found = modes(p["all"], h)
    return {"mean": mean, "sd": sd, "skewness": skew, "median": quantile(p["all"], 0.5),
            "iqr": quantile(p["all"], 0.75) - quantile(p["all"], 0.25), "bandwidth": h, "modes": found,
            "ks_halves": ks(*p["halves"])}


def controls(exe, seed, work):
    ctl = {}
    w4 = words(seed, "vrbt/control/plain")
    wout = os.path.join(work, "plain.txt")
    c = c_run(exe, w4, "uniform", 0.5, 0.0, 0.1, GINH_ALL, CD, SIGMA, 1, wout)
    p = plain_run(w4, "uniform", 0.5, 0.0, 0.1, GINH_ALL, CD, SIGMA, 1)
    same = all(c[k] == p[k] for k in ("rate", "post_spikes", "pre_arrivals", "inh_arrivals", "gex_mean", "gin_mean",
                                       "wmin", "wmax", "underflow", "pend_over", "hist", "weights"))
    close = all(abs(a - b) <= 1e-9 * max(1.0, abs(b)) for h in (0, 1) for a, b in zip(c["mom"][h], p["mom"][h]))
    ctl["the C program matches the plain implementation over 0.5 s (moments within 1e-9)"] = bool(same and close
                                                                                                   and p["post_spikes"] > 0)
    e5, e25 = math.exp(-0.5), math.exp(-0.25)
    up, down = c_pair(exe, 300.0, 0.0, "pre:0,post:100"), c_pair(exe, 300.0, 0.0, "post:0,pre:100")
    ctl["an arrival 10 ms before a spike adds c_p e^(-1/2); 10 ms after, takes c_d w e^(-1/2)"] = (
        abs(up - (300.0 + CP * e5)) < 1e-12 and abs(down - (300.0 - CD * 300.0 * e5)) < 1e-12)
    two_pre = c_pair(exe, 300.0, 0.0, "pre:0,pre:50,post:100,post:150")
    want = 300.0 + CP * e5
    want = want + CP * e25
    ctl["two arrivals before a spike are both potentiated, and a second spike potentiates nothing"] = (
        abs(two_pre - want) < 1e-12)
    two_post = c_pair(exe, 300.0, 0.0, "post:0,post:50,pre:100,pre:150")
    want = 300.0 + (-CD * 300.0) * e5
    want = want + (-CD * want) * e25
    ctl["two spikes before an arrival both depress it, and a second arrival is not depressed"] = (
        abs(two_post - want) < 1e-12)
    held = c_run(exe, words(seed, "vrbt/control/held"), "300", 20.0, 0.0, 20.0, GINH_EACH, CD, SIGMA, 0)
    ne, ni = NE * RATE * 20.0, NI * RATE * 20.0
    gex0 = NE * RATE * TAU_S * 1e-3 * (300.0 / G_LEAK)
    gin0 = NI * RATE * TAU_S * 1e-3 * (GINH_EACH / G_LEAK)
    ctl["20 s held at 300 pS: arrivals within four standard errors, conductances within 2% of 0.3 and 0.5"] = (
        abs(held["pre_arrivals"] - ne) < 4 * math.sqrt(ne) and abs(held["inh_arrivals"] - ni) < 4 * math.sqrt(ni)
        and abs(held["gex_mean"] / gex0 - 1) < 0.02 and abs(held["gin_mean"] / gin0 - 1) < 0.02)
    rng = Xoshiro(words(seed, "vrbt/control/statistics"))

    def gamma4():
        return -75.0 * sum(math.log(1.0 - rng.unif()) for _ in range(4))
    g = [gamma4() for _ in range(100000)]
    mix = [(250.0 if rng.unif() < 0.5 else 650.0) + 50.0 * rng.gauss() for _ in range(100000)]
    mirror = [1500.0 - x for x in g]
    found = {}
    for name, vals in (("gamma", g), ("mixture", mix), ("mirror", mirror)):
        hist = bin_values(vals)
        mean, sd, skew = summary(moments_of(vals))
        found[name] = (len(modes(hist, bandwidth(hist, sd))), skew)
    ctl["the statistics: gamma one mode and skew > 0; mixture two modes; mirrored gamma skew < 0"] = (
        found["gamma"][0] == 1 and found["gamma"][1] > 0 and found["mixture"][0] == 2 and found["mirror"][1] < 0)
    grow = c_run(exe, words(seed, "vrbt/control/potentiation-only"), "uniform", 100.0, 50.0, 1.0, GINH_EACH, 0.0,
                 SIGMA, 1)
    ctl["potentiation alone (c_d = 0): the halves of 50-100 s are 0.05 or more apart"] = ks(*grow["hist"]) >= KS_MAX
    return ctl, found


def fmt(x, nd=1):
    return f"{x:.{nd}f}"


def run(seed, results="results", log=sys.stderr):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    if shutil.which("gcc") is None:
        raise Refused("no gcc in this image")
    os.makedirs(results, exist_ok=True)
    work = tempfile.mkdtemp(prefix="work-", dir=results)   # the sandbox's /tmp cannot run what is built in it
    exe = build(work)

    ctl, stats = controls(exe, seed, work)
    print(f"controls: {sum(ctl.values())} of {len(ctl)}", file=log)
    if not all(ctl.values()):
        raise AssertionError(f"a control failed: {[c for c, ok in ctl.items() if not ok]}")

    readings = {}
    for name, ginh in (("each", GINH_EACH), ("all", GINH_ALL)):
        readings[name] = pooled(run_set(exe, seed, f"vrbt/{name}/uniform", "uniform", ginh))
        print(f"2000 pS {name}: rate {readings[name]['rate']:.2f} Hz", file=log)
    chosen = min(readings, key=lambda k: (abs(readings[k]["rate"] - PAPER_RATE), k != "each"))
    other = "all" if chosen == "each" else "each"
    ginh = GINH_EACH if chosen == "each" else GINH_ALL
    main = readings[chosen]
    high = pooled(run_set(exe, seed, f"vrbt/{chosen}/high", repr(2.0 * CP / CD), ginh))
    expo = pooled(run_exponential(exe, seed, f"vrbt/{chosen}/exponential", ginh, work))
    d_main, d_other = describe(main), describe(readings[other])
    ks_high, ks_expo = ks(main["all"], high["all"]), ks(main["all"], expo["all"])
    print(f"chosen: {chosen}; modes {len(d_main['modes'])}, skew {d_main['skewness']:.4f}, halves "
          f"{d_main['ks_halves']:.4f}, high {ks_high:.4f}, exponential {ks_expo:.4f}", file=log)

    cond = {"one mode": len(d_main["modes"]) == 1,
            "skewness above 0": d_main["skewness"] > 0,
            f"the halves less than {KS_MAX} apart": d_main["ks_halves"] < KS_MAX,
            f"the start at 2 c_p/c_d less than {KS_MAX} away": ks_high < KS_MAX,
            f"the exponential start less than {KS_MAX} away": ks_expo < KS_MAX}
    w_tot = 0.020 * RATE * NE * d_main["mean"]
    peak = CP / (CD - CP / w_tot + 2 * SIGMA ** 2)
    top = max(d_main["modes"], key=lambda m: m[1])[0] if d_main["modes"] else float("nan")
    values = {
        "modes": len(d_main["modes"]),
        "skewness": round(d_main["skewness"], 4),
        "ks_halves": round(d_main["ks_halves"], 4),
        "ks_start_high": round(ks_high, 4),
        "ks_start_exponential": round(ks_expo, 4),
        "reading": f"2000 pS {'per inhibitory synapse' if chosen == 'each' else 'for the 25 together'}",
        "rates": (f"output Hz, mean of 10 runs: 2000 pS each {readings['each']['rate']:.2f}, "
                  f"in all {readings['all']['rate']:.2f} (paper: about 25)"),
        "weights": (f"pS: mean {fmt(d_main['mean'])}, sd {fmt(d_main['sd'])}, median {fmt(d_main['median'])}, "
                    f"IQR {fmt(d_main['iqr'])}"),
        "density_mode": round(top, 1),
        "peak_formula": f"c_p/(c_d - c_p/W_tot + 2 sigma^2) = {peak:.1f} pS, W_tot = {w_tot:.0f} pS",
        "bandwidth": round(d_main["bandwidth"], 2),
        "other_reading": (f"{other}: {len(d_other['modes'])} mode(s), skewness {d_other['skewness']:.4f}, halves "
                          f"{d_other['ks_halves']:.4f}"),
        "range": (f"pS {main['wmin']:.1f} to {main['wmax']:.1f}; above 5000: {main['overflow']}, below 0: "
                  f"{main['underflow']}"),
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
    detail = {"conditions": cond, "controls": ctl, "control_statistics": stats, "chosen": chosen,
              "readings": {k: {"rate": readings[k]["rate"], "describe": describe(readings[k]),
                               "pend_over": readings[k]["pend_over"]} for k in readings},
              "starts": {"high": {"rate": high["rate"], "ks": ks_high, "describe": describe(high)},
                         "exponential": {"rate": expo["rate"], "ks": ks_expo, "describe": describe(expo)}},
              "histogram_main_10pS": coarse(main["all"]), "test": TEST}
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="utf-8") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    shutil.rmtree(work, ignore_errors=True)
    return out, detail


def coarse(hist, width=10.0):
    out = {}
    for b, c in hist.items():
        k = int(b * BIN // width)
        out[k] = out.get(k, 0) + c
    return {str(int(k * width)): out[k] for k in sorted(out)}


def run_exponential(exe, seed, label, ginh, work):
    """The exponential start: each run's weights written to a file the C program reads as its start."""
    def one(r):
        weights = exponential_start(seed, f"{label}/{r}")
        path = os.path.join(work, f"{label.replace('/', '_')}_{r}.start")
        with open(path, "w") as fh:
            for x in weights:
                fh.write(f"{x!r}\n")
        return c_run(exe, words(seed, f"{label}/{r}"), "file:" + path, DUR, FROM, SAMPLE, ginh, CD, SIGMA, 1)
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        return list(pool.map(one, range(RUNS)))


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"vrbt: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
