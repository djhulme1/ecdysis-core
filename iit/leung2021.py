#!/usr/bin/env python3
"""Leung, Cohen, van Swinderen and Tsuchiya (2021): the integrated information structure of fly local field
potentials, awake and under isoflurane, built as the paper's Methods build it, with IIT 3.0's phi as PyPhi 0.8.1
computes it.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from Leung, Cohen, van Swinderen and
Tsuchiya, "Integrated information structure collapses with anesthetic loss of conscious arousal in Drosophila
melanogaster", PLoS Computational Biology 17(2), e1008722 (2021; CC BY 4.0), its abstract: "Consistent with this
conjecture, we found that integrated interactions among populations of neurons during wakefulness collapsed to
isolated clusters of interactions during anesthesia." The Results make the collapse measurable: the integrated
information structure (IIS) of a set of four channels is the phi of each of its 15 mechanisms, and "we found
integrated information to reduce significantly across all mechanisms with loss of arousal" (Fig 4C, for each
mechanism size).

Data of record: the authors' preprocessed LFPs (Monash Bridges, doi:10.26180/5ebe420ae8d89,
split2250_bipolarRerefType1_lineNoiseRemoved_postPuffpreStim.mat, read here as INPUT names it, by hash; CC BY 4.0):
one MATLAB 5.0 variable, fly_data, 2,250 samples x 15 channels x 8 epochs x 13 flies x 2 conditions, downsampled to
1000 Hz, bipolar re-referenced, line noise removed. The deposit's description orders the conditions "wake/anest"
(index 0 awake at 0% isoflurane, index 1 at 0.6%) and calls channel 1 the most central.

Every rule below was fixed before any phi of the data was computed; the tests exercise the machinery on other
inputs (random and constructed TPMs, synthetic channels), never on the data.

1. Binarisation (Methods, "Local field potential preprocessing"): in each epoch of each fly and condition, a channel
   is on at a sample if its voltage is greater than the median of its 2,250 samples in that epoch, off otherwise.
2. Channel sets: SETS of the 1,365 four-channel sets, drawn by the seed without replacement, the same sets for every
   fly (the paper ran all 1,365; this check samples them, as PyPhi's cost requires). Within a set the channels, in
   ascending order, are nodes 0 to 3.
3. The TPM (Methods, "IIS computation"): for a set, fly, condition and epoch, the state at sample t is its four
   channels' values, node i as bit i (PyPhi's LOLI order for a state-by-node TPM); for each of the 16 states, the
   fraction of samples t (0 <= t < 2250 - TAU) in that state at which each channel is on at t + TAU, TAU = 4 samples
   (4 ms at 1000 Hz). A state never seen at such a t has no estimate; its row is 1/2 for every channel (the maximum
   entropy PyPhi assumes elsewhere), and the number of such rows is reported.
4. Phi (iit/iis.c, built here with flow.c): every mechanism's phi at every state, as PyPhi 0.8.1 defines it (the
   file's header lists the conventions: repertoires, mip_bipartitions, distances rounded to 6 decimals, a MIP of 0
   as soon as one partition gives 0, the core cause and effect the greatest over purviews, the concept the lesser
   of the two). The earth mover's distances are exact (PyPhi called pyemd, which scales masses and costs to parts
   per million first); PyPhi's check that a state is reachable is not applied, and the observed states it would
   refuse are counted.
5. Averages (the Methods' order): within an epoch, each state's phi weighted by the number of samples t
   (0 <= t < 2250 - TAU) at which the set is in that state (the transitions the TPM counts; the variant counting all
   2,250 samples is reported); then the mean over the 8 epochs; then, per mechanism size (4, 6, 4 and 1 mechanisms
   of sizes 1 to 4), the mean over its mechanisms; then, per fly and condition, the mean over the sets.
6. The test (TEST): for each mechanism size, a one-tailed paired t-test over the 13 flies, awake against
   isoflurane, at p < 0.05 (12 degrees of freedom: the paper's "classical" group-level test, run after averaging
   across channel sets to obtain a single value per fly). Refuted if, for any size, the awake mean is not greater
   at that level.

Beside the test, none of it counted: each size's means, its wake/isoflurane ratio (Fig 4D: the paper found larger
mechanisms reduced relatively less) and the order of the sizes' phi (the paper: 1-channel mechanisms greatest, then
2 < 3 < 4); the flies in which each size falls; the variant weighting; the state-weighted number of mechanisms with
phi > 0 (the "isolated clusters"); the rows estimated from no sample and the observed states PyPhi would refuse; and
a null that keeps each channel's own dynamics and breaks the interactions between channels: on NULL_SETS of the
drawn sets (drawn again by the seed), node i's samples taken from epoch (e + 2i) mod 8 of the same fly and
condition, so that the four nodes of a set come from four different 2.25 s windows, the same averages and t-tests
by size.

Controls (controls_passed counts those that behave as stated): the file holds fly_data, 2250 x 15 x 8 x 13 x 2, all
finite; every channel-epoch whose two middle values differ has exactly 1,125 samples on; the state counts of every
epoch sum to 2,246 (and 2,250 in the variant); iis.c agrees with iit/engine.py (written from PyPhi 1.2, held by its
tests to PyPhi's own results; these definitions are unchanged from 0.8.1) on every value of three seed-drawn TPMs of
the data; the effect distance iis.c uses (the sum of the differences of P(on)) equals the exact earth mover's
distance on 200 seed-drawn pairs of product distributions; a TPM of the data rebuilt so that each channel depends
only on itself gives phi 0 for every mechanism of two or more channels at every state; and the hand-written paired
t-test agrees with scipy's for the four sizes.

What it does not check: system-level Phi (the cuts of the whole set), the classification analysis, the linear mixed
models, the spatial maps and the other tau values; the 1,365 - SETS sets not drawn.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 iit/leung2021.py
"""

import ctypes
import hashlib
import itertools
import json
import math
import multiprocessing
import os
import random
import re
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT = ("leung2021_lfps.mat", "c1d90525273f45a779719dab879ea4baed620242ec86e062061f8a32d99ba187", 53509449)
SHAPE = (2250, 15, 8, 13, 2)
TAU = 4
SETS = 60
NULL_SETS = 10
N = 4
SIZES = (1, 2, 3, 4)
ALPHA = 0.05
WAKE, ANEST = 0, 1
TEST = ("Refuted if, in the authors' released LFPs (13 flies, 15 channels, 8 epochs of 2,250 samples awake and under "
        "isoflurane), each channel binarised at its epoch median, each 4-channel set's state-by-channel TPM taken at "
        "tau = 4 ms and IIT 3.0's phi of each mechanism (PyPhi 0.8.1's definitions) averaged over states by "
        "occurrence, over epochs and over 60 seed-drawn channel sets, for any mechanism size (1 to 4 channels) the "
        "awake phi is not greater than under isoflurane by a one-tailed paired t-test over the 13 flies at p < 0.05.")
OUTPUTS = ("sets", "phi_wake_1", "phi_wake_2", "phi_wake_3", "phi_wake_4", "phi_anest_1", "phi_anest_2",
           "phi_anest_3", "phi_anest_4", "t_1", "t_2", "t_3", "t_4", "p_1", "p_2", "p_3", "p_4", "flies_1",
           "flies_2", "flies_3", "flies_4", "ratio", "order", "variant", "concepts", "null", "unseen_rows", "unreachable",
           "conditions_met", "conditions_total", "test_passed", "controls_passed", "controls_total")


class Refused(Exception):
    pass


def seeded(seed, label):
    return random.Random(int.from_bytes(hashlib.sha256(f"{seed}/{label}".encode()).digest(), "big"))


# ----------------------------------------------------------------------------------------------- the engine

def build(results):
    lib = os.path.join(os.path.abspath(results), "libiis.so")
    subprocess.run(["gcc", "-O2", "-shared", "-fPIC", "-o", lib, os.path.join(HERE, "iis.c"),
                    os.path.join(HERE, "flow.c"), "-lm"], check=True)
    return lib


class IIS:
    def __init__(self, lib):
        self.lib = ctypes.CDLL(lib)
        d = ctypes.POINTER(ctypes.c_double)
        self.lib.phis.argtypes = [ctypes.c_int, d, d, d, d]
        self.lib.phis.restype = ctypes.c_int
        self.lib.emd_hamming.argtypes = [ctypes.c_int, d, d]
        self.lib.emd_hamming.restype = ctypes.c_double

    def phis(self, tpm):
        """tpm: 2^n x n (P(node j on | state s), LOLI). Returns (phi, cause, effect), each [mechanism - 1][state]."""
        n = len(tpm[0])
        ns = 2 ** n
        flat = (ctypes.c_double * (ns * n))(*[float(tpm[s][j]) for s in range(ns) for j in range(n)])
        bufs = [(ctypes.c_double * ((ns - 1) * ns))() for _ in range(3)]
        if self.lib.phis(n, flat, *bufs) != 0:
            raise Refused("iis.c refused the TPM")
        return [[[b[(m - 1) * ns + s] for s in range(ns)] for m in range(1, ns)] for b in bufs]

    def emd(self, m, p, q):
        k = 2 ** m
        return self.lib.emd_hamming(m, (ctypes.c_double * k)(*p), (ctypes.c_double * k)(*q))


def mechanisms(n=N):
    """Mechanism bitmasks 1 .. 2^n - 1 and their sizes."""
    return [(m, bin(m).count("1")) for m in range(1, 2 ** n)]


# ----------------------------------------------------------------------------------------------- the data

def read(inputs):
    path = os.path.join(inputs, INPUT[0])
    if not os.path.exists(path):
        raise Refused(f"{INPUT[0]} is missing")
    with open(path, "rb") as fh:
        blob = fh.read()
    if len(blob) != INPUT[2] or hashlib.sha256(blob).hexdigest() != INPUT[1]:
        raise Refused(f"{INPUT[0]} is not the file of record")
    import scipy.io
    mat = scipy.io.loadmat(path)
    if "fly_data" not in mat:
        raise Refused("fly_data is missing")
    data = np.asarray(mat["fly_data"], dtype=float)
    if data.shape != SHAPE:
        raise Refused(f"fly_data has shape {data.shape}, not {SHAPE}")
    return data


def binarise(x):
    """x: samples x channels (one epoch). On where greater than the channel's median over the epoch."""
    med = np.median(x, axis=0)
    return (x > med[None, :]).astype(np.int64), med


def states_of(b, chans):
    """The state index (node i = bit i) at every sample, for channels chans (ascending)."""
    out = np.zeros(b.shape[0], dtype=np.int64)
    for i, c in enumerate(chans):
        out |= b[:, c] << i
    return out


def tpm_of(b, chans, tau=TAU):
    """(tpm, counts over t < T - tau, counts over every t, unseen rows) for one epoch and set."""
    st = states_of(b, chans)
    ns = 2 ** len(chans)
    T = b.shape[0]
    cur = st[:T - tau]
    nxt = b[tau:, list(chans)]
    counts = np.bincount(cur, minlength=ns)
    on = np.zeros((ns, len(chans)))
    for j in range(len(chans)):
        on[:, j] = np.bincount(cur, weights=nxt[:, j], minlength=ns)
    tpm = np.full((ns, len(chans)), 0.5)
    seen = counts > 0
    tpm[seen] = on[seen] / counts[seen][:, None]
    return tpm, counts, np.bincount(st, minlength=ns), int((~seen).sum())


def null_epoch(epochs, e, chans):
    """The null's samples for epoch e: node i (channel chans[i]) from epoch (e + 2i) mod 8, as columns 0..3."""
    return np.stack([epochs[(e + 2 * i) % len(epochs)][:, c] for i, c in enumerate(chans)], axis=1)


def reachable(tpm, s):
    """PyPhi 0.8.1's validate.state_reachable for the whole system."""
    n = tpm.shape[1]
    state = np.array([(s >> i) & 1 for i in range(n)])
    test = tpm - state[None, :]
    return bool(np.any(np.all((test > -1) & (test < 1), axis=1)))


def weighted(phi, w):
    """phi: [mechanism][state]; w: counts per state. The weighted mean over states, per mechanism."""
    tot = float(w.sum())
    return [sum(phi[m][s] * w[s] for s in range(len(w))) / tot for m in range(len(phi))]


# ----------------------------------------------------------------------------------------------- one fly

_ENGINE = None


def _init(lib):
    global _ENGINE
    _ENGINE = IIS(lib)


def fly_job(args):
    """Every set, condition and epoch of one fly: per set and condition, the epoch means of the IIS."""
    f, bins, sets, null_sets = args
    mech = mechanisms()
    out = {"fly": f, "iis": {}, "iis_all": {}, "concepts": {}, "null": {}, "unseen": 0, "unreachable": 0,
           "sums": []}
    for c in (WAKE, ANEST):
        for si, chans in enumerate(null_sets):
            acc = [0.0] * len(mech)
            for e in range(SHAPE[2]):
                b = null_epoch(bins[c], e, chans)
                tpm, w, _, _ = tpm_of(b, tuple(range(len(chans))))
                phi, _, _ = _ENGINE.phis(tpm.tolist())
                iis = weighted(phi, w)
                for m in range(len(mech)):
                    acc[m] += iis[m] / SHAPE[2]
            out["null"][(c, si)] = acc
        for si, chans in enumerate(sets):
            acc = [0.0] * len(mech)
            acc_all = [0.0] * len(mech)
            conc = 0.0
            for e in range(SHAPE[2]):
                b = bins[c][e]
                tpm, w, w_all, unseen = tpm_of(b, chans)
                out["unseen"] += unseen
                out["sums"].append((int(w.sum()), int(w_all.sum())))
                phi, _, _ = _ENGINE.phis(tpm.tolist())
                for s in range(2 ** N):
                    if w[s] > 0 and not reachable(tpm, s):
                        out["unreachable"] += 1
                iis = weighted(phi, w)
                iis_all = weighted(phi, w_all)
                for m in range(len(mech)):
                    acc[m] += iis[m] / SHAPE[2]
                    acc_all[m] += iis_all[m] / SHAPE[2]
                conc += sum(w[s] * sum(1 for m in range(len(mech)) if phi[m][s] > 0)
                            for s in range(2 ** N)) / float(w.sum()) / SHAPE[2]
            out["iis"][(c, si)] = acc
            out["iis_all"][(c, si)] = acc_all
            out["concepts"][(c, si)] = conc
    return out


# ----------------------------------------------------------------------------------------------- statistics

def betacf(a, b, x):
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1.0 + aa / c if abs(1.0 + aa / c) > 1e-300 else 1e-300
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1.0 + aa / c if abs(1.0 + aa / c) > 1e-300 else 1e-300
        de = d * c
        h *= de
        if abs(de - 1.0) < 1e-15:
            break
    return h


def betainc(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lb = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(lb) * betacf(a, b, x) / a
    return 1.0 - math.exp(lb) * betacf(b, a, 1 - x) / b


def paired_t(x, y):
    """One-tailed paired t-test that x > y: (t, p, df), by hand."""
    d = [a - b for a, b in zip(x, y)]
    n = len(d)
    m = sum(d) / n
    v = sum((u - m) ** 2 for u in d) / (n - 1)
    t = m / math.sqrt(v / n) if v > 0 else (math.inf if m > 0 else -math.inf)
    df = n - 1
    if math.isinf(t):
        return t, (0.0 if t > 0 else 1.0), df
    tail = 0.5 * betainc(df / 2, 0.5, df / (df + t * t))
    return t, (tail if t > 0 else 1.0 - tail), df


def scipy_paired(x, y):
    from scipy import stats
    r = stats.ttest_rel(x, y, alternative="greater")
    return float(r.statistic), float(r.pvalue)


# ----------------------------------------------------------------------------------------------- controls

def control_engine(engine, lib_flow, tpms):
    """iis.c against iit/engine.py on every value of the given TPMs."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("iit_engine", os.path.join(HERE, "engine.py"))
    E = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(E)
    flow = E.Flow(lib_flow, 0)
    worst, values = 0.0, 0
    for tpm in tpms:
        phi, pc, pe = engine.phis(tpm)
        net = E.Network(tpm)
        n = len(tpm[0])
        for s in range(2 ** n):
            state = tuple((s >> i) & 1 for i in range(n))
            sub = E.Subsystem(net, state, tuple(range(n)), cache={})
            for m in range(1, 2 ** n):
                mech = tuple(i for i in range(n) if (m >> i) & 1)
                c, _ = sub.mice(flow, E.CAUSE, mech)
                e, _ = sub.mice(flow, E.EFFECT, mech)
                worst = max(worst, abs(c[0] - pc[m - 1][s]), abs(e[0] - pe[m - 1][s]),
                            abs(min(c[0], e[0]) - phi[m - 1][s]))
                values += 3
    return worst == 0.0, {"values": values, "worst": worst}


def control_effect(engine, rng):
    worst = 0.0
    for _ in range(200):
        m = rng.randint(1, 4)
        g = [rng.random() for _ in range(m)]
        h = [rng.random() for _ in range(m)]

        def prod(v):
            return [math.prod(v[t] if (s >> t) & 1 else 1 - v[t] for t in range(m)) for s in range(2 ** m)]
        worst = max(worst, abs(engine.emd(m, prod(g), prod(h)) - sum(abs(a - b) for a, b in zip(g, h))))
    return worst < 1e-12, worst


def control_independent(engine, b, chans):
    """Each channel's next state from its own current state only: no mechanism of 2+ channels may have phi."""
    st = states_of(b, chans)
    T = b.shape[0]
    own = []
    for j, c in enumerate(chans):
        cur = b[:T - TAU, c]
        nxt = b[TAU:, c]
        p1 = float(nxt[cur == 1].mean()) if (cur == 1).any() else 0.5
        p0 = float(nxt[cur == 0].mean()) if (cur == 0).any() else 0.5
        own.append((p0, p1))
    tpm = [[own[j][(s >> j) & 1] for j in range(len(chans))] for s in range(2 ** len(chans))]
    phi, _, _ = engine.phis(tpm)
    multi = max(phi[m - 1][s] for m, k in mechanisms(len(chans)) if k > 1 for s in range(2 ** len(chans)))
    single = max(phi[m - 1][s] for m, k in mechanisms(len(chans)) if k == 1 for s in range(2 ** len(chans)))
    return multi == 0.0 and single > 0.0, {"multi_max": multi, "single_max": single}


# ----------------------------------------------------------------------------------------------- the run

def run(seed, inputs="inputs", results="results", workers=2):
    data = read(inputs)
    os.makedirs(results, exist_ok=True)
    lib = build(results)
    lib_flow = os.path.join(os.path.abspath(results), "libflow.so")
    subprocess.run(["gcc", "-O2", "-shared", "-fPIC", "-o", lib_flow, os.path.join(HERE, "flow.c"), "-lm"],
                   check=True)
    engine = IIS(lib)
    nf = SHAPE[3]
    # 1. binarise
    bins = {}
    halves, ties = 0, 0
    for f in range(nf):
        for c in (WAKE, ANEST):
            for e in range(SHAPE[2]):
                x = data[:, :, e, f, c]
                b, med = binarise(x)
                bins[(f, c, e)] = b
                srt = np.sort(x, axis=0)
                for ch in range(SHAPE[1]):
                    if srt[1124, ch] != srt[1125, ch]:
                        halves += int(b[:, ch].sum() == 1125)
                    else:
                        ties += 1
    # 2. sets
    allsets = list(itertools.combinations(range(SHAPE[1]), N))
    rng = seeded(seed, "sets")
    sets = [allsets[i] for i in sorted(rng.sample(range(len(allsets)), SETS))]
    # 3-5. every fly
    null_sets = [sets[i] for i in sorted(seeded(seed, "null").sample(range(SETS), NULL_SETS))]
    jobs = [(f, {c: [bins[(f, c, e)] for e in range(SHAPE[2])] for c in (WAKE, ANEST)}, sets, null_sets)
            for f in range(nf)]
    if workers > 1:
        with multiprocessing.get_context("fork").Pool(workers, initializer=_init, initargs=(lib,)) as pool:
            done = pool.map(fly_job, jobs)
    else:
        _init(lib)
        done = [fly_job(j) for j in jobs]
    done.sort(key=lambda r: r["fly"])
    mech = mechanisms()

    def size_means(iis):
        return {k: sum(iis[i] for i, (_, kk) in enumerate(mech) if kk == k) / sum(1 for _, kk in mech if kk == k)
                for k in SIZES}

    per = {}      # (fly, condition) -> size -> mean over sets
    per_all = {}
    ratios = {k: [] for k in SIZES}
    conc = {WAKE: [], ANEST: []}
    for r in done:
        f = r["fly"]
        for c in (WAKE, ANEST):
            sm = [size_means(r["iis"][(c, si)]) for si in range(SETS)]
            sa = [size_means(r["iis_all"][(c, si)]) for si in range(SETS)]
            per[(f, c)] = {k: sum(x[k] for x in sm) / SETS for k in SIZES}
            per_all[(f, c)] = {k: sum(x[k] for x in sa) / SETS for k in SIZES}
            conc[c].append(sum(r["concepts"][(c, si)] for si in range(SETS)) / SETS)
        for si in range(SETS):
            w = size_means(r["iis"][(WAKE, si)])
            a = size_means(r["iis"][(ANEST, si)])
            for k in SIZES:
                if a[k] > 0:
                    ratios[k].append(w[k] / a[k])
    out = {"sets": f"{SETS} of {len(allsets)} four-channel sets, drawn by the seed (the same for every fly)"}
    cond = {}
    tests = {}
    for k in SIZES:
        wake = [per[(f, WAKE)][k] for f in range(nf)]
        anest = [per[(f, ANEST)][k] for f in range(nf)]
        t, p, df = paired_t(wake, anest)
        tests[k] = (t, p, df, wake, anest)
        out[f"phi_wake_{k}"] = round(sum(wake) / nf, 9)
        out[f"phi_anest_{k}"] = round(sum(anest) / nf, 9)
        out[f"t_{k}"] = round(t, 6)
        out[f"p_{k}"] = float(f"{p:.6g}")
        out[f"flies_{k}"] = sum(1 for a, b in zip(wake, anest) if a > b)
        cond[f"size {k}: awake phi greater than under isoflurane, one-tailed paired t-test over 13 flies, p < 0.05"] = (
            p < ALPHA and t > 0)
    out["ratio"] = ("mean wake/isoflurane ratio per set and fly, sizes 1 to 4: " + ", ".join(
        f"{sum(ratios[k]) / len(ratios[k]):.3f}" if ratios[k] else "none" for k in SIZES))
    wake_means = {k: out[f"phi_wake_{k}"] for k in SIZES}
    out["order"] = "awake phi by size, greatest first: " + " > ".join(
        str(k) for k in sorted(SIZES, key=lambda k: -wake_means[k]))
    alt = []
    for k in SIZES:
        t2, p2, _ = paired_t([per_all[(f, WAKE)][k] for f in range(nf)], [per_all[(f, ANEST)][k] for f in range(nf)])
        alt.append(f"{k}: p {p2:.3g}")
    out["variant"] = "weights over all 2,250 samples, one-tailed p by size: " + "; ".join(alt)
    out["concepts"] = (f"mechanisms with phi > 0, state-weighted, mean over flies: awake {sum(conc[WAKE]) / nf:.3f}, "
                       f"isoflurane {sum(conc[ANEST]) / nf:.3f} (of 15)")
    nul = []
    null_per = {}
    for r in done:
        for c in (WAKE, ANEST):
            sm = [size_means(r["null"][(c, si)]) for si in range(NULL_SETS)]
            null_per[(r["fly"], c)] = {k: sum(x[k] for x in sm) / NULL_SETS for k in SIZES}
    for k in SIZES:
        wk = [null_per[(f, WAKE)][k] for f in range(nf)]
        an = [null_per[(f, ANEST)][k] for f in range(nf)]
        t3, p3, _ = paired_t(wk, an)
        nul.append(f"{k}: {sum(wk) / nf:.4f}/{sum(an) / nf:.4f} p {p3:.2g}")
    out["null"] = f"channels from 4 epochs, {NULL_SETS} sets; awake/isoflurane by size: " + "; ".join(nul)
    out["unseen_rows"] = sum(r["unseen"] for r in done)
    out["unreachable"] = sum(r["unreachable"] for r in done)
    out["conditions_met"] = sum(1 for v in cond.values() if v)
    out["conditions_total"] = len(cond)
    out["test_passed"] = int(all(cond.values()))
    # controls
    controls, cdetail = {}, {}
    controls["the file holds fly_data, 2250 x 15 x 8 x 13 x 2, all finite"] = bool(np.isfinite(data).all())
    total = nf * 2 * SHAPE[2] * SHAPE[1]
    controls["every channel-epoch with distinct middle values has 1,125 samples on"] = (halves == total - ties)
    cdetail["ties_at_median"] = ties
    sums = [s for r in done for s in r["sums"]]
    controls["every epoch's state counts sum to 2,246 (2,250 in the variant)"] = all(
        a == SHAPE[0] - TAU and b == SHAPE[0] for a, b in sums)
    crng = seeded(seed, "controls")
    picks = [(crng.randrange(nf), crng.choice((WAKE, ANEST)), crng.randrange(SHAPE[2]), crng.choice(sets))
             for _ in range(3)]
    tpms = [tpm_of(bins[(f, c, e)], s)[0].tolist() for f, c, e, s in picks]
    ok, det = control_engine(engine, lib_flow, tpms)
    controls["iis.c equals iit/engine.py on every value of three seed-drawn TPMs of the data"] = ok
    cdetail["engine"] = dict(det, picks=[list(p[:3]) + [list(p[3])] for p in picks])
    ok, worst = control_effect(engine, crng)
    controls["the effect distance equals the exact earth mover's distance on 200 pairs of product distributions"] = ok
    cdetail["effect_worst"] = worst
    f, c, e, s = picks[0]
    ok, det = control_independent(engine, bins[(f, c, e)], s)
    controls["a TPM with each channel depending only on itself gives phi 0 to every mechanism of 2+ channels"] = ok
    cdetail["independent"] = det
    agree = True
    for k in SIZES:
        t, p, df, wake, anest = tests[k]
        st, sp = scipy_paired(wake, anest)
        agree &= abs(st - t) < 1e-9 * max(1, abs(t)) and abs(sp - p) < 1e-9
    controls["the hand-written paired t-test equals scipy's for the four sizes"] = bool(agree)
    out["controls_passed"] = sum(1 for v in controls.values() if v)
    out["controls_total"] = len(controls)
    assert set(out) == set(OUTPUTS), sorted(set(out) ^ set(OUTPUTS))
    detail = {"test": TEST, "conditions": cond, "controls": controls, "control_detail": cdetail,
              "sets": [list(s) for s in sets], "null_sets": [list(s) for s in null_sets],
              "per_fly": {f"{f}": {"wake": per[(f, WAKE)], "anest": per[(f, ANEST)]} for f in range(nf)},
              "per_fly_all_samples": {f"{f}": {"wake": per_all[(f, WAKE)], "anest": per_all[(f, ANEST)]}
                                      for f in range(nf)},
              "tests": {f"{k}": {"t": tests[k][0], "p": tests[k][1], "df": tests[k][2]} for k in SIZES},
              "concepts": {"wake": conc[WAKE], "anest": conc[ANEST]},
              "null_per_fly": {f"{f}": {"wake": null_per[(f, WAKE)], "anest": null_per[(f, ANEST)]}
                               for f in range(nf)},
              "per_set": {f"{r['fly']}": {f"{c}/{si}": r["iis"][(c, si)] for c in (WAKE, ANEST)
                                          for si in range(SETS)} for r in done}}
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
    with open(os.path.join(results, "detail.json"), "w", encoding="utf-8") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, default=float)
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"leung2021: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
