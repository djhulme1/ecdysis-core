#!/usr/bin/env python3
"""Potjans & Diesmann (2014): the full-scale cortical microcircuit's spontaneous activity is asynchronous and
irregular, with cell-type specific firing rates that agree with in vivo recordings, L2/3e's low rate included.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from T. C. Potjans and M. Diesmann, "The
cell-type specific cortical microcircuit: relating structure and activity in a full-scale spiking network model"
(Cerebral Cortex 24(3), 785-806, 2014; doi:10.1093/cercor/bhs358; open in PMC as PMC3920768, CC BY-NC, read here in
Europe PMC's full text): "The simulated spontaneous activity is asynchronous irregular and cell-type specific firing
rates are in agreement with in vivo recordings in awake animals, including the low rate of layer 2/3 excitatory
cells."

The test, as registered: see TEST below. Standard library and the image's gcc: the network is simulated in C
(snn/pd2014.c, compiled here). No data are read: the network and its inputs are generated under the seed. Every rule
below was fixed before any run of the model.

1. The model, as Tables 4 and 5 and the Methods give it. Eight populations (L2/3e, L2/3i, L4e, L4i, L5e, L5i, L6e,
   L6i) of 20683, 5834, 21915, 5479, 4850, 1065, 14395 and 2948 current-based leaky integrate-and-fire neurons
   (77,169): tau_m 10 ms, C_m 250 pF, threshold -50 mV, reset -65 mV, 2 ms absolute refractory period with the
   voltage clamped, exponential synaptic currents of 0.5 ms. Connection probabilities from Table 5 (the probability
   of at least one synapse between a pair); each projection's synapse count K inverts Eq. (1),
   C = 1 - (1 - 1/(N_pre N_post))^K, so K = log(1 - C) / log(1 - 1/(N_pre N_post)), truncated as the authors' code
   truncates it; every synapse's presynaptic and postsynaptic neuron drawn independently and uniformly from its two
   populations ("we randomly draw for every synapse the pre- and the postsynaptic neuron"), multapses and autapses
   allowed. Weights Gaussian (87.8 +- 8.8 pA, the 0.15 mV PSP; inhibitory ones g = -4 times as strong; the L4e to
   L2/3e strengths doubled), redrawn until they keep their sign; delays Gaussian (excitatory 1.5 +- 0.75 ms), redrawn
   below 0.1 ms and rounded to the 0.1 ms grid ("positive and multiples of the computation step size"). Every neuron
   receives an independent Poisson train of k_ext x 8 Hz (Table 5's reference k_ext: 1600, 1500, 2100, 1900, 2000,
   1900, 2900, 2100), each arrival of the 0.15 mV PSP's current. No thalamic input (spontaneous activity).
2. Two readings, each run in full: the paper's text, and the authors' implementation released with NEST 2.4.0
   (examples/nest/Potjans_2014: network_params.sli and microcircuit.sli, "adapted by Tom Tetzlaff, David Dahmen,
   Sacha van Albada 2013; Hannah Bos 2014"), the one the paper said "will be made available with the next release
   of the NEST simulation tool". Where they differ:
   - text: Table 5's probabilities to three places (0.0003 as printed); w 87.8 +- 8.8 pA, inhibitory -351.2 +- 35.2,
     L4e to L2/3e 175.6 +- 17.6 (strength and spread doubled); inhibitory delays 0.8 +- 0.4 ms; background 87.8 pA.
   - code: its probabilities to four places; w from PSP_e = 0.15 mV by its formula (87.81 pA) with a spread of 10%,
     inhibitory g times that with 10% of its size, L4e to L2/3e twice the mean with the undoubled spread (its sigma
     is PSC_sd of the source population); inhibitory delays 0.75 +- 0.375 ms; background weight from PSP_ext = 0.15.
   Where the text is silent, both follow the code: E_L = -65 mV (Table 4's membrane equation is an image this check
   could not read; the code's E_L equals the reset), initial potentials Gaussian with mean -58 mV and standard
   deviation 10 mV, background arrivals with a fixed weight, and the truncation of K.
3. Integration as NEST 2.4's iaf_psc_exp does it, on a grid of h = 0.1 ms: in each step the membrane advances by the
   exact propagators from the current of the step before (unless refractory, when the counter counts down), the
   current decays by exp(-h/tau_syn), the step's arrivals are added (spikes sent d steps before with delay d, and
   the step's background count times its weight), and a membrane at or above threshold spikes, resets to -65 mV and
   is refractory for 20 steps. Excitatory and inhibitory currents share one 0.5 ms time constant, so their sum is
   kept. The membrane propagator to the current is NEST's: -tau_m/(C_m (1 - tau_m/tau_syn)) exp(-h/tau_syn)
   expm1(h (1/tau_syn - 1/tau_m)). Background counts are Poisson draws by inversion of the CDF (a guide table speeds
   the C program; the draws are the same). The generator is xoshiro256**, seeded from SHA-256 of the seed and a label
   for each stream (each projection's pairs, each projection's delays, the weights, the initial potentials, and the
   background of each half of the network); Gaussians by Box-Muller.
4. Measurement, as Figure 6 and the authors' analysis script do it: the first 0.2 s are discarded (the script's
   T_start = 200 ms); spikes of the first 1000 neurons of each population ("1000 spike trains") are recorded for the
   next 60 s. A population's rate is the mean over its 1000 neurons of their spike counts divided by 60 s (Table 6's
   "Model, Reference" row is this mean for Figure 6B); irregularity is the mean, over its recorded neurons with at
   least three spikes, of the interspike intervals' coefficient of variation (standard deviation over mean, the
   divisor n); synchrony is the variance divided by the mean (divisor n) of the spike counts of its 1000 neurons
   together in 3 ms bins over the window's first 5 s (1666 whole bins; Figure 6D's 5 s).
5. The test's seven conditions, for each reading (fourteen in all; test_passed is 1 if all hold): (1) every
   population's rate below 30 Hz, (2) every irregularity from 0.7 to 1.2, (3) every synchrony below 8 (the three are
   Figure 8B's criteria for "asynchronously and irregularly at low rate"); (4) L2/3e's rate below 1 Hz ("Consistent
   over species, areas, and behavioral states, the firing rate is <1 Hz"); (5) L5e's rate above each other
   excitatory population's ("L5e consistently shows the highest spontaneous activity"); (6) in every layer the
   inhibitory rate above the excitatory ("In all layers, inhibitory firing exceeds excitatory rates", and in vivo
   "inhibitory activity is typically higher"); (7) each excitatory rate less than 20% from Table 6's model values,
   0.86, 4.45, 7.59 and 1.09 Hz.
6. Beside the test, none of it counted: every population's mean rate over all its neurons; the number of synapses,
   excitatory and inhibitory, against the paper's "about 217 million excitatory and 82 million inhibitory synapses";
   the counts of neurons each irregularity averages; the build's and the simulation's durations (detail only).

Controls (controls_passed counts those that behave as stated; the run stops if any fails): the C program matches a
plain implementation written here, bit for bit (spikes, counts, final potentials, currents and refractory
counters), on a network of the same populations at a hundredth of their sizes over 0.3 s under each reading; one
arrival of the code's 87.81 pA, alone at rest, peaks within 0.5% of 0.15 mV at 1.5 to 1.7 ms ("an average excitatory
postsynaptic potential has an amplitude of 0.15 mV with a rise time of 1.6 ms"); each reading's synapse totals lie
within 1% of the paper's 217 and 82 million; and, from each full run, the in-degrees of every projection with at
least a million synapses have the mean K/N_post exactly and a variance within 3% of the binomial K/N_post (1 -
1/N_post), the delays' mean and standard deviation by type within 0.5% of those of the clipped and rounded Gaussian,
the weights' within 0.5% of the stated ones, and every population's background arrivals within four standard errors
of their Poisson expectation.

What it cannot check: the paper's own simulations and NEST itself (not run here); the comparison with in vivo data,
which is the paper's reading of Table 6 and is taken as it states it; the thalamic stimulation (Figure 10) and the
robustness studies (Figures 7 to 9).

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 snn/pd2014.py
"""

import array
import hashlib
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))

TEST = ("Refuted if, in the paper's full-scale model (77,169 LIF neurons in 8 populations; Table 5's "
        "probabilities, synapse counts by Eq. 1, Gaussian weights and delays, reference Poisson background; 0.1 ms "
        "steps), read by its text or by the authors' NEST 2.4.0 code, 60 s of spontaneous activity after 0.2 s is not "
        "asynchronous irregular in every population (rate below 30 Hz, mean ISI CV 0.7 to 1.2, synchrony below 8), "
        "L2/3e's mean rate is not below 1 Hz, L5e's is not the highest excitatory, a layer's inhibitory rate is not "
        "above its excitatory, or an excitatory mean is 20% or more from Table 6's.")

POPS = ("L2/3e", "L2/3i", "L4e", "L4i", "L5e", "L5i", "L6e", "L6i")
N = (20683, 5834, 21915, 5479, 4850, 1065, 14395, 2948)
K_EXT = (1600, 1500, 2100, 1900, 2000, 1900, 2900, 2100)
BG_RATE = 8.0                                   # Hz per external synapse

# Table 5's connection probabilities, rows the target, columns the source, as printed
C_TEXT = ((0.101, 0.169, 0.044, 0.082, 0.032, 0.0, 0.008, 0.0),
          (0.135, 0.137, 0.032, 0.052, 0.075, 0.0, 0.004, 0.0),
          (0.008, 0.006, 0.050, 0.135, 0.007, 0.0003, 0.045, 0.0),
          (0.069, 0.003, 0.079, 0.160, 0.003, 0.0, 0.106, 0.0),
          (0.100, 0.062, 0.051, 0.006, 0.083, 0.373, 0.020, 0.0),
          (0.055, 0.027, 0.026, 0.002, 0.060, 0.316, 0.009, 0.0),
          (0.016, 0.007, 0.021, 0.017, 0.057, 0.020, 0.040, 0.225),
          (0.036, 0.001, 0.003, 0.001, 0.028, 0.008, 0.066, 0.144))
# the authors' code (NEST 2.4.0, examples/nest/Potjans_2014/network_params.sli, conn_probs)
C_CODE = ((0.1009, 0.1689, 0.0437, 0.0818, 0.0323, 0.0, 0.0076, 0.0),
          (0.1346, 0.1371, 0.0316, 0.0515, 0.0755, 0.0, 0.0042, 0.0),
          (0.0077, 0.0059, 0.0497, 0.135, 0.0067, 0.0003, 0.0453, 0.0),
          (0.0691, 0.0029, 0.0794, 0.1597, 0.0033, 0.0, 0.1057, 0.0),
          (0.1004, 0.0622, 0.0505, 0.0057, 0.0831, 0.3726, 0.0204, 0.0),
          (0.0548, 0.0269, 0.0257, 0.0022, 0.06, 0.3158, 0.0086, 0.0),
          (0.0156, 0.0066, 0.0211, 0.0166, 0.0572, 0.0197, 0.0396, 0.2252),
          (0.0364, 0.001, 0.0034, 0.0005, 0.0277, 0.008, 0.0658, 0.1443))

TAU_M, TAU_SYN, C_M, T_REF = 10.0, 0.5, 250.0, 2.0
E_L, V_TH, V_RESET = -65.0, -50.0, -65.0
H = 0.1                                         # ms
STEPS_PER_MS = 10.0
V0_MEAN, V0_SD = -58.0, 10.0
G = -4.0
PSP = 0.15                                      # mV
D_LOW = 0.1                                     # ms
WARM_MS, REC_MS, SYNC_MS, BIN_MS = 200.0, 60000.0, 5000.0, 3.0
N_REC = 1000
TABLE6 = {"L2/3e": 0.86, "L4e": 4.45, "L5e": 7.59, "L6e": 1.09}
TOL = 0.2
RATE_MAX, CV_LO, CV_HI, SYNC_MAX = 30.0, 0.7, 1.2, 8.0
L23_MAX = 1.0
PAPER_SYNAPSES = (217e6, 82e6)
PTAB = 64
SMALL = 0.01                                    # the plain implementation's network: a hundredth of the sizes
SMALL_MS, SMALL_WARM_MS = 300.0, 50.0
LIMIT = 200

OUTPUTS = ("rates_text", "rates_code", "irregularity_text", "irregularity_code", "synchrony_text",
           "synchrony_code", "table6", "l23e_text", "l23e_code", "rates_all_neurons", "synapses",
           "conditions_met", "conditions_total", "test_passed", "controls_passed", "controls_total")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- seeds and the generator

MASK = (1 << 64) - 1


def words(seed, label):
    """Four 64-bit words for xoshiro256**, from SHA-256 of seed and label (never all zero)."""
    h = hashlib.sha256(f"{seed}/{label}".encode()).digest()
    w = [int.from_bytes(h[8 * i:8 * i + 8], "big") for i in range(4)]
    if not any(w):
        w[0] = 1
    return [f"{x:016x}" for x in w]


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

    def gauss(self):
        u1, u2 = 1.0 - self.unif(), self.unif()
        return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


# ---------------------------------------------------------------- the model's numbers

def psc_per_psp(tau_m=TAU_M, tau_syn=TAU_SYN, c_m=C_M):
    """The authors' code's factor from PSP amplitude (mV) to PSC amplitude (pA)."""
    re_, de = tau_m / tau_syn, tau_syn - tau_m
    return ((1.0 / c_m) * tau_m * tau_syn / de * (re_ ** (tau_m / de) - re_ ** (tau_syn / de))) ** -1


def synapse_count(c, n_pre, n_post):
    """K by inverting Eq. (1), truncated as the authors' code (cvi) truncates it."""
    if c <= 0.0:
        return 0
    prod = float(n_pre) * float(n_post)
    return int(math.log(1.0 - c) / math.log((prod - 1.0) / prod))


def reading(name):
    """Weights (pA), spreads, delays (ms) and probabilities of one reading."""
    if name == "text":
        we, wsd_e = 87.8, 8.8
        wi, wsd_i = G * 87.8, abs(G) * 8.8
        w234, wsd_234 = 2 * 87.8, 2 * 8.8
        d = {"e": (1.5, 0.75), "i": (0.8, 0.4)}
        wext, probs = 87.8, C_TEXT
    elif name == "code":
        f = psc_per_psp()
        we = f * PSP
        wi = f * (PSP * G)
        wsd_e, wsd_i = 0.1 * abs(we), 0.1 * abs(wi)
        w234, wsd_234 = f * (2 * PSP), 0.1 * abs(we)
        d = {"e": (1.5, 0.75), "i": (0.75, 0.375)}
        wext, probs = f * PSP, C_CODE
    else:
        raise ValueError(name)
    wmean = [[(we if s % 2 == 0 else wi) for s in range(8)] for t in range(8)]
    wsd = [[(wsd_e if s % 2 == 0 else wsd_i) for s in range(8)] for t in range(8)]
    wmean[0][2], wsd[0][2] = w234, wsd_234
    return {"name": name, "wmean": wmean, "wsd": wsd, "delays": d, "wext": wext, "probs": probs}


def propagators(h=H, tau_m=TAU_M, tau_syn=TAU_SYN, c_m=C_M):
    p11 = math.exp(-h / tau_syn)
    p22 = math.exp(-h / tau_m)
    p21 = -tau_m / (c_m * (1.0 - tau_m / tau_syn)) * p11 * math.expm1(h * (1.0 / tau_syn - 1.0 / tau_m))
    return p11, p21, p22


def poisson_table(lam):
    p = math.exp(-lam)
    c = p
    tab = [c]
    for k in range(1, PTAB):
        p *= lam / k
        c += p
        tab.append(c)
    return tab


def sizes_of(scale):
    return tuple(N) if scale == 1 else tuple(max(1, int(round(n * scale))) for n in N)


def counts_matrix(rd, sizes):
    return [[synapse_count(rd["probs"][t][s], sizes[s], sizes[t]) for s in range(8)] for t in range(8)]


def config(rd, seed, sizes, warm_steps, rec_steps, nrec, prefix):
    """The C program's configuration (and the plain implementation's), as a dict and as text."""
    lab = f"pd2014/{rd['name']}/{'full' if tuple(sizes) == tuple(N) else 'small'}"
    K = counts_matrix(rd, sizes)
    p11, p21, p22 = propagators()
    tabs = [poisson_table(K_EXT[p] * BG_RATE * H * 1e-3) for p in range(8)]
    cfg = {"N": list(sizes), "K": K, "wmean": rd["wmean"], "wsd": rd["wsd"],
           "dmean": [rd["delays"]["e" if s % 2 == 0 else "i"][0] for s in range(8)],
           "dsd": [rd["delays"]["e" if s % 2 == 0 else "i"][1] for s in range(8)],
           "dlow": D_LOW, "steps_per_ms": STEPS_PER_MS, "wext": rd["wext"], "ptab": tabs,
           "prop": (p11, p21, p22), "theta": V_TH - E_L, "vreset": V_RESET - E_L, "refc": int(round(T_REF / H)),
           "v0": (V0_MEAN - E_L, V0_SD), "steps": (warm_steps, rec_steps), "nrec": nrec,
           "conn": {(t, s): words(seed, f"{lab}/conn/{t}/{s}") for t in range(8) for s in range(8)},
           "delay": {(t, s): words(seed, f"{lab}/delay/{t}/{s}") for t in range(8) for s in range(8)},
           "weight": words(seed, f"{lab}/weight"), "vinit": words(seed, f"{lab}/vinit"),
           "bg": [words(seed, f"{lab}/bg/0"), words(seed, f"{lab}/bg/1")],
           "spikes": prefix + "-spikes", "counts": prefix + "-counts.bin", "state": prefix + "-state.bin"}
    hx = float.hex
    lines = ["N " + " ".join(str(x) for x in cfg["N"])]
    for t in range(8):
        lines.append(f"K {t} " + " ".join(str(x) for x in K[t]))
        lines.append(f"wmean {t} " + " ".join(hx(float(x)) for x in cfg["wmean"][t]))
        lines.append(f"wsd {t} " + " ".join(hx(float(x)) for x in cfg["wsd"][t]))
    lines.append("dmean " + " ".join(hx(float(x)) for x in cfg["dmean"]))
    lines.append("dsd " + " ".join(hx(float(x)) for x in cfg["dsd"]))
    lines.append(f"dlow {hx(D_LOW)}")
    lines.append(f"steps_per_ms {hx(STEPS_PER_MS)}")
    lines.append(f"wext {hx(float(rd['wext']))}")
    for p in range(8):
        lines.append(f"ptab {p} " + " ".join(hx(x) for x in tabs[p]))
    lines.append(f"prop {hx(p11)} {hx(p21)} {hx(p22)}")
    lines.append(f"theta {hx(cfg['theta'])}")
    lines.append(f"vreset {hx(cfg['vreset'])}")
    lines.append(f"refc {cfg['refc']}")
    lines.append(f"v0 {hx(cfg['v0'][0])} {hx(cfg['v0'][1])}")
    lines.append(f"steps {warm_steps} {rec_steps}")
    lines.append(f"nrec {nrec}")
    for (t, s), w in cfg["conn"].items():
        lines.append(f"conn {t} {s} " + " ".join(w))
    for (t, s), w in cfg["delay"].items():
        lines.append(f"delay {t} {s} " + " ".join(w))
    lines.append("weight " + " ".join(cfg["weight"]))
    lines.append("vinit " + " ".join(cfg["vinit"]))
    lines.append("bg 0 " + " ".join(cfg["bg"][0]))
    lines.append("bg 1 " + " ".join(cfg["bg"][1]))
    lines.append(f"spikes {cfg['spikes']}")
    lines.append(f"counts {cfg['counts']}")
    lines.append(f"state {cfg['state']}")
    return cfg, "\n".join(lines) + "\n"


# ---------------------------------------------------------------- the plain implementation (control)

def plain_run(cfg):
    """The C program's "run", step for step in Python's floats (the same operations in the same order)."""
    sizes = cfg["N"]
    base = [0]
    for n in sizes:
        base.append(base[-1] + n)
    ntot = base[-1]
    hb = (0, ntot // 2, ntot)
    popof = []
    for p in range(8):
        popof += [p] * sizes[p]
    K = cfg["K"]
    segs = [[] for _ in range(2 * ntot)]
    for t in range(8):
        for s in range(8):
            r, rd = Xoshiro(cfg["conn"][(t, s)]), Xoshiro(cfg["delay"][(t, s)])
            for _ in range(K[t][s]):
                pre = base[s] + r.below(sizes[s])
                post = base[t] + r.below(sizes[t])
                x = cfg["dmean"][s] + cfg["dsd"][s] * rd.gauss()
                while x < cfg["dlow"]:
                    x = cfg["dmean"][s] + cfg["dsd"][s] * rd.gauss()
                st = max(1, math.floor(x * cfg["steps_per_ms"] + 0.5))
                h = 1 if post >= hb[1] else 0
                segs[2 * pre + h].append((st << 16) | (post - hb[h]))
    rw = Xoshiro(cfg["weight"])
    syn = []
    for j in range(ntot):
        for h in range(2):
            keys = sorted(segs[2 * j + h])
            lst = []
            for key in keys:
                tl = key & 0xFFFF
                tp, sp = popof[hb[h] + tl], popof[j]
                mu, sd = cfg["wmean"][tp][sp], cfg["wsd"][tp][sp]
                x = mu + sd * rw.gauss()
                while (mu > 0 and x < 0) or (mu < 0 and x > 0):
                    x = mu + sd * rw.gauss()
                lst.append((key >> 16, tl, f32(x)))
            syn.append(lst)
    maxdel = max([d for lst in syn for (d, _, _) in lst] or [1])
    D = 1
    while D <= maxdel:
        D <<= 1
    rv = Xoshiro(cfg["vinit"])
    V = [cfg["v0"][0] + cfg["v0"][1] * rv.gauss() for _ in range(ntot)]
    I = [0.0] * ntot
    ref = [0] * ntot
    ring = [[[0.0] * (hb[h + 1] - hb[h]) for _ in range(D)] for h in range(2)]
    rb = [Xoshiro(cfg["bg"][0]), Xoshiro(cfg["bg"][1])]
    p11, p21, p22 = cfg["prop"]
    theta, vreset, refc, wext = cfg["theta"], cfg["vreset"], cfg["refc"], cfg["wext"]
    tabs = cfg["ptab"]
    warm, recn = cfg["steps"]
    nrec = cfg["nrec"]
    counts = [0] * ntot
    rec = [[], []]
    for n in range(warm + recn):
        slot = n & (D - 1)
        spk = [[], []]
        for th in range(2):
            rr = ring[th][slot]
            for i in range(hb[th], hb[th + 1]):
                li = i - hb[th]
                inn = rr[li]
                rr[li] = 0.0
                if ref[i] == 0:
                    V[i] = V[i] * p22 + I[i] * p21
                else:
                    ref[i] -= 1
                p = popof[i]
                u = (rb[th].next64() >> 11) * 2.0 ** -53
                k = 0
                tab = tabs[p]
                while k < PTAB - 1 and u >= tab[k]:
                    k += 1
                I[i] = I[i] * p11 + inn + k * wext
                if V[i] >= theta:
                    ref[i] = refc
                    V[i] = vreset
                    spk[th].append(i)
                    if n >= warm:
                        counts[i] += 1
                        if i - base[p] < nrec:
                            rec[th].append((i, n - warm))
        for th in range(2):
            for o in range(2):
                for j in spk[o]:
                    for (d, tl, w) in syn[2 * j + th]:
                        ring[th][(n + d) & (D - 1)][tl] += w
    return {"counts": counts, "rec": rec, "V": V, "I": I, "ref": ref}


# ---------------------------------------------------------------- the C program

def build(work):
    exe = os.path.join(work, "pd2014")
    subprocess.run(["gcc", "-O2", "-ffp-contract=off", "-std=gnu11", "-pthread", "-o", exe,
                    os.path.join(HERE, "pd2014.c"), "-lm"], check=True)
    return exe


def c_run(exe, text, cfg, work, name):
    path = os.path.join(work, name + ".cfg")
    with open(path, "w") as fh:
        fh.write(text)
    out = subprocess.run([exe, "run", path], check=True, capture_output=True, text=True).stdout
    got = {}
    for line in out.splitlines():
        k, _, v = line.partition("=")
        got[k] = v
    ntot = sum(cfg["N"])
    with open(cfg["counts"], "rb") as fh:
        counts = array.array("I")
        counts.fromfile(fh, ntot)
    rec = []
    for th in range(2):
        a = array.array("I")
        with open(cfg["spikes"] + f".{th}", "rb") as fh:
            a.frombytes(fh.read())
        rec.append(a)
    with open(cfg["state"], "rb") as fh:
        V = array.array("d")
        V.fromfile(fh, ntot)
        I = array.array("d")
        I.fromfile(fh, ntot)
        ref = array.array("i")
        ref.fromfile(fh, ntot)
    for f in (cfg["counts"], cfg["state"], cfg["spikes"] + ".0", cfg["spikes"] + ".1"):
        os.remove(f)
    stats = {"neurons": int(got["neurons"]), "synapses": int(got["synapses"]),
             "synapses_e": int(got["synapses_e"]), "synapses_i": int(got["synapses_i"]),
             "max_delay_steps": int(got["max_delay_steps"]), "ring": int(got["ring"]),
             "delay_redraws": int(got["delay_redraws"]), "weight_redraws": int(got["weight_redraws"]),
             "delays": {t: [float(x) for x in got[f"delay_{t}"].split(",")] for t in ("e", "i")},
             "weights": [[float(x) for x in got[f"weight_{c}"].split(",")] for c in range(3)],
             "indeg": [[[float(y) for y in x.split(":")] for x in got[f"indeg_{t}"].split(",")] for t in range(8)],
             "bg_arrivals": [int(x) for x in got["bg_arrivals"].split(",")],
             "spikes": int(got["spikes"]), "deliveries": int(got["deliveries"]),
             "build_s": float(got["build_s"]), "sim_s": float(got["sim_s"])}
    return {"counts": counts, "rec": rec, "V": V, "I": I, "ref": ref, "stats": stats}


def c_psp(exe, w):
    p11, p21, p22 = propagators()
    out = subprocess.run([exe, "psp", float.hex(p11), float.hex(p21), float.hex(p22), float.hex(float(w))],
                         check=True, capture_output=True, text=True).stdout
    got = dict(line.split("=", 1) for line in out.splitlines())
    return float(got["peak"]), int(got["step"])


# ---------------------------------------------------------------- statistics

def trains(rec_flat_list, base, sizes, nrec):
    """Per population, a list of each recorded neuron's spike steps (in order)."""
    out = [[[] for _ in range(min(nrec, sizes[p]))] for p in range(8)]
    pop_of = []
    for p in range(8):
        pop_of += [p] * sizes[p]
    for a in rec_flat_list:
        for q in range(0, len(a), 2):
            i, n = a[q], a[q + 1]
            p = pop_of[i]
            out[p][i - base[p]].append(n)
    return out


def cv_of(steps):
    isi = [b - a for a, b in zip(steps, steps[1:])]
    m = sum(isi) / len(isi)
    v = sum((x - m) ** 2 for x in isi) / len(isi)
    return math.sqrt(v) / m


def population_stats(tr, rec_ms=REC_MS, sync_ms=SYNC_MS, bin_ms=BIN_MS, h=H):
    """Rate (Hz), irregularity (mean CV, neurons with at least three spikes) and synchrony of one population."""
    n = len(tr)
    rate = sum(len(s) for s in tr) / n / (rec_ms * 1e-3)
    cvs = [cv_of(s) for s in tr if len(s) >= 3]
    irr = sum(cvs) / len(cvs) if cvs else float("nan")
    bin_steps = int(round(bin_ms / h))
    nbins = int(sync_ms / bin_ms)
    hist = [0] * nbins
    for s in tr:
        for x in s:
            b = x // bin_steps
            if b < nbins:
                hist[b] += 1
    m = sum(hist) / nbins
    var = sum((c - m) ** 2 for c in hist) / nbins
    sync = var / m if m > 0 else float("nan")
    return {"rate": rate, "irregularity": irr, "cv_neurons": len(cvs), "synchrony": sync, "bins": nbins}


def conditions(st):
    """The test's seven conditions on one reading's statistics (keys: population names)."""
    r = {p: st[p]["rate"] for p in POPS}
    cond = {
        "every rate below 30 Hz": all(r[p] < RATE_MAX for p in POPS),
        "every irregularity from 0.7 to 1.2": all(CV_LO <= st[p]["irregularity"] <= CV_HI for p in POPS),
        "every synchrony below 8": all(st[p]["synchrony"] < SYNC_MAX for p in POPS),
        "L2/3e below 1 Hz": r["L2/3e"] < L23_MAX,
        "L5e the highest excitatory": all(r["L5e"] > r[p] for p in ("L2/3e", "L4e", "L6e")),
        "inhibitory above excitatory in every layer": all(r[POPS[2 * k + 1]] > r[POPS[2 * k]] for k in range(4)),
        "excitatory rates within 20% of Table 6": all(abs(r[p] - v) < TOL * v for p, v in TABLE6.items()),
    }
    return cond


def delay_moments(mu, sd, low=D_LOW, spm=STEPS_PER_MS):
    """Mean and standard deviation (ms) of a Gaussian delay redrawn below `low` and rounded to the grid."""
    def phi(x):
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
    z = 1.0 - phi((low - mu) / sd)
    m = q = 0.0
    for s in range(1, 256):
        lo, hi = max(low, (s - 0.5) / spm), (s + 0.5) / spm
        if hi <= low:
            continue
        p = (phi((hi - mu) / sd) - phi((lo - mu) / sd)) / z
        m += p * s / spm
        q += p * (s / spm) ** 2
    return m, math.sqrt(q - m * m)


def fmt_pops(values, nd=2):
    return ", ".join(f"{p} {values[p]:.{nd}f}" for p in POPS)


# ---------------------------------------------------------------- controls

def controls_before(exe, seed, work):
    ctl, stats = {}, {}
    for name in ("text", "code"):
        rd = reading(name)
        sizes = sizes_of(SMALL)
        cfg, text = config(rd, seed, sizes, int(round(SMALL_WARM_MS / H)), int(round((SMALL_MS - SMALL_WARM_MS) / H)),
                           10 ** 9, os.path.join(work, f"small-{name}"))
        c = c_run(exe, text, cfg, work, f"small-{name}")
        p = plain_run(cfg)
        c_rec = [[(a[q], a[q + 1]) for q in range(0, len(a), 2)] for a in c["rec"]]
        same = (list(c["counts"]) == p["counts"] and c_rec == p["rec"] and list(c["V"]) == p["V"]
                and list(c["I"]) == p["I"] and list(c["ref"]) == p["ref"])
        ctl[f"the C program bit for bit against the plain implementation ({name})"] = same
        stats[f"small_{name}"] = {"sizes": sizes, "synapses": c["stats"]["synapses"],
                                  "spikes": c["stats"]["spikes"], "recorded": sum(len(x) for x in p["rec"])}
        K = counts_matrix(rd, N)
        ke = sum(K[t][s] for t in range(8) for s in range(0, 8, 2))
        ki = sum(K[t][s] for t in range(8) for s in range(1, 8, 2))
        ctl[f"synapse totals within 1% of 217 and 82 million ({name})"] = (
            abs(ke - PAPER_SYNAPSES[0]) < 0.01 * PAPER_SYNAPSES[0] and abs(ki - PAPER_SYNAPSES[1]) < 0.01 * PAPER_SYNAPSES[1])
        stats[f"synapses_{name}"] = [ke, ki]
    w = psc_per_psp() * PSP
    peak, step = c_psp(exe, w)
    ctl["one 87.81 pA arrival peaks at 0.15 mV within 0.5%, at 1.5 to 1.7 ms"] = (
        abs(peak - PSP) < 0.005 * PSP and 15 <= step <= 17)
    stats["psp"] = {"weight_pA": w, "peak_mV": peak, "step": step}
    return ctl, stats


def controls_after(name, rd, cfg, st):
    ctl, out = {}, {}
    K = cfg["K"]
    ok, worst = True, 0.0
    for t in range(8):
        for s in range(8):
            if K[t][s] < 10 ** 6:
                continue
            m, v = st["indeg"][t][s]
            n = N[t]
            mean, var = K[t][s] / n, K[t][s] / n * (1.0 - 1.0 / n)
            if abs(m - mean) > 1e-9 * mean or abs(v - var) > 0.03 * var:
                ok = False
            worst = max(worst, abs(v - var) / var)
    ctl[f"in-degrees binomial ({name})"] = ok
    out["indeg_worst_variance_gap"] = worst
    ok = True
    for ty in ("e", "i"):
        em, es = delay_moments(*rd["delays"][ty])
        m, s, _ = st["delays"][ty]
        out[f"delay_{ty}"] = {"measured": [m, s], "expected": [em, es]}
        if abs(m - em) > 0.005 * em or abs(s - es) > 0.005 * es:
            ok = False
    ctl[f"delays as drawn ({name})"] = ok
    ok = True
    for c, (mu, sd) in enumerate(((rd["wmean"][1][0], rd["wsd"][1][0]), (rd["wmean"][0][1], rd["wsd"][0][1]),
                                  (rd["wmean"][0][2], rd["wsd"][0][2]))):
        m, s, _ = st["weights"][c]
        out[f"weight_{c}"] = {"measured": [m, s], "stated": [mu, sd]}
        if abs(m - mu) > 0.005 * abs(mu) or abs(s - sd) > 0.005 * sd:
            ok = False
    ctl[f"weights as drawn ({name})"] = ok
    ok = True
    steps = cfg["steps"][1]
    for p in range(8):
        lam = K_EXT[p] * BG_RATE * H * 1e-3
        e = N[p] * lam * steps
        if abs(st["bg_arrivals"][p] - e) > 4.0 * math.sqrt(e):
            ok = False
        out[f"bg_{POPS[p]}"] = {"arrivals": st["bg_arrivals"][p], "expected": e}
    ctl[f"background arrivals Poisson ({name})"] = ok
    return ctl, out


# ---------------------------------------------------------------- the run

def run_reading(exe, seed, name, work, log):
    rd = reading(name)
    cfg, text = config(rd, seed, N, int(round(WARM_MS / H)), int(round(REC_MS / H)), N_REC,
                       os.path.join(work, f"full-{name}"))
    t0 = time.time()
    c = c_run(exe, text, cfg, work, f"full-{name}")
    base = [0]
    for n in N:
        base.append(base[-1] + n)
    tr = trains(c["rec"], base, N, N_REC)
    st = {POPS[p]: population_stats(tr[p]) for p in range(8)}
    all_rates = {POPS[p]: sum(c["counts"][base[p]:base[p + 1]]) / N[p] / (REC_MS * 1e-3) for p in range(8)}
    print(f"{name}: built in {c['stats']['build_s']:.0f} s, simulated in {c['stats']['sim_s']:.0f} s "
          f"({time.time() - t0:.0f} s in all)", file=log)
    return rd, cfg, c["stats"], st, all_rates


def run(seed, results="results", log=sys.stderr):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    if shutil.which("gcc") is None:
        raise Refused("no gcc in this image")
    os.makedirs(results, exist_ok=True)
    work = tempfile.mkdtemp(prefix="work-", dir=results)   # the sandbox's /tmp cannot run what is built in it
    exe = build(work)

    ctl, cstats = controls_before(exe, seed, work)
    print(f"controls before the runs: {sum(ctl.values())} of {len(ctl)}", file=log)
    if not all(ctl.values()):
        raise AssertionError(f"a control failed: {[c for c, ok in ctl.items() if not ok]}")

    res = {}
    for name in ("text", "code"):
        rd, cfg, stats, st, all_rates = run_reading(exe, seed, name, work, log)
        c2, o2 = controls_after(name, rd, cfg, stats)
        ctl.update(c2)
        cstats[f"after_{name}"] = o2
        if not all(c2.values()):
            raise AssertionError(f"a control failed: {[c for c, ok in c2.items() if not ok]}")
        res[name] = {"stats": stats, "pops": st, "all_rates": all_rates, "conditions": conditions(st)}

    cond = {}
    for name in ("text", "code"):
        for k, v in res[name]["conditions"].items():
            cond[f"{k} ({name})"] = v

    def r(name):
        return {p: res[name]["pops"][p]["rate"] for p in POPS}

    t6 = ("from " + ", ".join(f"{v}" for v in TABLE6.values()) + " Hz (L2/3e, L4e, L5e, L6e): "
          + "; ".join(f"{n} " + ", ".join(f"{100 * (r(n)[p] - v) / v:+.1f}%" for p, v in TABLE6.items())
                      for n in ("text", "code")))
    values = {
        "rates_text": "Hz: " + fmt_pops(r("text")),
        "rates_code": "Hz: " + fmt_pops(r("code")),
        "irregularity_text": "CV: " + fmt_pops({p: res["text"]["pops"][p]["irregularity"] for p in POPS}),
        "irregularity_code": "CV: " + fmt_pops({p: res["code"]["pops"][p]["irregularity"] for p in POPS}),
        "synchrony_text": "var/mean: " + fmt_pops({p: res["text"]["pops"][p]["synchrony"] for p in POPS}),
        "synchrony_code": "var/mean: " + fmt_pops({p: res["code"]["pops"][p]["synchrony"] for p in POPS}),
        "table6": t6,
        "l23e_text": round(r("text")["L2/3e"], 4),
        "l23e_code": round(r("code")["L2/3e"], 4),
        "rates_all_neurons": " | ".join(f"{n}: " + ", ".join(f"{res[n]['all_rates'][p]:.2f}" for p in POPS)
                                        for n in ("text", "code")),
        "synapses": " | ".join(f"{n}: {res[n]['stats']['synapses_e'] / 1e6:.2f}M e, "
                               f"{res[n]['stats']['synapses_i'] / 1e6:.2f}M i" for n in ("text", "code"))
                    + " (paper: about 217M and 82M)",
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
    detail = {"conditions": cond, "controls": ctl, "control_statistics": cstats, "test": TEST,
              "readings": {n: {"populations": res[n]["pops"], "all_neuron_rates": res[n]["all_rates"],
                               "build": res[n]["stats"]} for n in ("text", "code")}}
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="utf-8") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, ensure_ascii=False)
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
        sys.exit(f"pd2014: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
