#!/usr/bin/env python3
"""Bak & Sneppen (1993): a model of coevolving species self-organizes into a critical steady state with avalanches of
all sizes, punctuated equilibrium.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from P. Bak and K. Sneppen, "Punctuated
equilibrium and criticality in a simple model of evolution" (Physical Review Letters 71(24), 4083-4086, 1993;
doi:10.1103/PhysRevLett.71.4083), its abstract as OpenAlex holds it: "The model self-organizes into a critical steady
state with intermittent coevolutionary avalanches of all sizes; i.e., it exhibits ``punctuated equilibrium''
behavior."

The test, as registered: see TEST below. Standard library and the image's gcc: the model is simulated in C
(alife/bs1993.c, compiled here). No data are read: the runs are generated under the seed. Every rule below was fixed
before any run of the model at the test's sizes or lengths.

1. The model, as the paper defines it: "(i) N species are arranged on a one-dimensional line with periodic boundary
   conditions. (ii) A random barrier, B_i, equally distributed between 0 and 1, is assigned to each species. At each
   time step, the ecology is updated by (iii) locating the site with the lowest barrier and mutating it by assigning a
   new random number to that site, and (iv) changing the landscapes of the two neighbors to the right and left,
   respectively, by assigning new random numbers to those sites, too." Time counts mutations (the paper's unit). The
   2D version beside the test: L x L sites on a torus, the lowest barrier and its four nearest neighbours renewed.
2. The numerics: barriers are doubles drawn as 53-bit uniforms from xoshiro256**, seeded from SHA-256 of the seed and
   the run's label; the lowest barrier is found by a tournament tree, a tie going to the lowest site (a plain scan's
   answer); the minimum's own barrier is renewed first, then its left and its right neighbour's (in 2D left, right,
   up, down).
3. Runs, 1D: N = 4096 (Figure 2's size), 3 x 10^8 steps of transient and 10^9 measured; N = 1024 from barriers uniform
   on [0, 1) (the paper's start) and from barriers uniform on [0.9, 1), each 10^8 steps of transient and 5 x 10^8
   measured; N = 256, 2 x 10^7 and 2 x 10^8. Beside the test, 2D at L = 64 (4096 sites), 2 x 10^8 and 5 x 10^8.
4. What is measured over the window: 1,000 snapshots of all barriers at equal intervals into a histogram of 10,000 bins
   on [0, 1) (and the window's halves into two more); every selected minimum (a histogram, and the largest); the ring
   distance x between successive minima, C(x) (Figure 1); the waiting time, in steps, between successive minima inside
   each block of 10 consecutive sites (Figure 4's segment), pooled over the N/10 whole blocks; and for each threshold
   f0 in 0.55, 0.60, 0.63, 0.65 (Figure 5's) and 0.66 (in 2D 0.25, 0.28, 0.30, 0.31 and 0.32), the avalanches as the
   paper defines them, maximal runs of consecutive steps whose minimum is below f0, sized by their number of steps
   (a run that began in the transient and ends in the window counts whole; one still open at the end does not). Sizes
   and waits are binned at 100 bins per decade, bin floor(100 log10 x).
   - The threshold: the edge of the barrier distribution's flat part, B_c = 1 - 1/h, h the density of the snapshot
     barriers over [0.70, 1) (a distribution uniform on [B_c, 1] has h = 1/(1 - B_c)). The step: the share of barriers
     below 0.65, and the six 0.05 bins over [0.70, 1) each within 5% of their mean.
   - Power laws: in each decade window, the maximum-likelihood exponent of a discrete power law p(x) ~ x^(-a) truncated
     to the window, fitted to the binned counts (each bin's probability the sum of x^(-a) over the integers it holds);
     two windows agree when their exponents differ by less than 0.3. C(x): windows [4, 40) and [40, 400); avalanches at
     f0 = 0.65: [10, 100), [100, 1000) and [1000, 10^4); waits: [10^2, 10^3), [10^3, 10^4) and [10^4, 10^5).
   - The hierarchy of avalanches: the 99th percentile of the sizes at each threshold (the lower edge of the bin where
     the cumulative share passes 0.99).
   - Distances between distributions: the Wasserstein distance on the 10,000 bins, as in snn/rubin.py.
5. The test's 15 conditions, at N = 4096 unless named: the barrier distribution flat over [0.70, 1) and under 1% of
   it below 0.65; B_c within 0.67 +/- 0.01, the paper's value; no selected minimum above 0.68 ("All mutations turn out
   to take place through barriers which are less than a self-organized critical value, B_c = 0.67 +/- 0.01"); C(x),
   the avalanche sizes at f0 = 0.65 and the waits each a power law over its windows (consecutive windows agreeing,
   every exponent positive); the 99th-percentile avalanche at least four times larger at each threshold of 0.60, 0.63,
   0.65 and 0.66 than at the one before (three conditions: avalanches of all sizes as f0 nears B_c); the window's halves
   less than 0.002 apart at N = 256, 1024 (both starts) and 4096 (four conditions: a steady state); and the two starts
   at N = 1024 less than 0.002 apart ("This does not depend on the initial conditions, so the critical state is a global
   attractor for the dynamics; hence it is self-organized"). test_passed is 1 if all 15 hold.
6. Beside the test, none of it counted: B_c at N = 256, 1024 and 4096 against the paper's 0.67 +/- 0.01 and the later
   0.66702 (Paczuski, Maslov & Bak 1996); the exponents over the whole windows, C(x)'s over [4, 400) against the
   paper's 3.15 +/- 0.05 (later 3.23) and the avalanches' at f0 = 0.65 over [10, 10^4) against its 0.9 +/- 0.1 (later
   1.07), and the waits' over [10^2, 10^5); the barrier density above B_c against Figure 2's (about 0.03 per 0.01);
   the mode of the minima's distribution (Figure 2's left curve); the 2D model's B_c and its avalanche exponent at
   0.31 over [10, 10^3) against the paper's "in 2D the exponent is about 1.1" (later 0.328 and 1.245); and the planted
   model in which only the lowest barrier is renewed.

Controls (controls_passed counts those that behave as stated; the run stops if any fails): the C program matches a plain
implementation written here bit for bit (every histogram, count, extreme and final barrier; the mean minimum within
1e-12) on 2 x 10^5 steps of N = 64 in 1D and of L = 8 in 2D; the planted model (only the lowest barrier renewed, no
interaction) at N = 256 fails the test's barrier conditions, its barriers not flat over [0.70, 1) and its B_c outside
0.67 +/- 0.01, so the test can fail; the edge
estimator gives 0.600 +/- 0.005 on 10^6 barriers drawn uniform on [0.6, 1); the exponent estimator gives 1.5 +/- 0.05 in
each decade of 2 x 10^5 sizes drawn from a discrete power law with exponent 1.5 on [10, 10^4), and finds the decades of
a geometric distribution (mean 300) 0.3 or more apart; and the distance gives 0.05 for two point masses 0.05 apart.

What it cannot check: the paper's own runs, which were not released; the later exponents' precision; the mean-field
version [13] and the "many different versions" its last paragraphs mention.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 alife/bs1993.py
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

TEST = ("Refuted if, in the paper's model (N species on a ring, barriers uniform on [0, 1); each step the lowest "
        "barrier and its two neighbours' get new ones) at N = 4096 over 10^9 steps after 3 x 10^8: the barriers are "
        "not flat above 0.70 or 1% or more lie below 0.65; the flat part's edge is outside 0.67 +/- 0.01 or a minimum "
        "exceeds 0.68; the distances between successive minima, avalanche sizes at 0.65 or a 10-site block's waits "
        "are not power laws (decade exponents 0.3 or more apart); avalanches at 0.60, 0.63, 0.65, 0.66 do not grow "
        "fourfold; or halves, or starts at N = 1024, lie 0.002 or more apart.")

NBIN = 10000
LBIN = 1300
SNAPS = 1000
SEG = 10
F0 = (0.55, 0.60, 0.63, 0.65, 0.66)
F0_2D = (0.25, 0.28, 0.30, 0.31, 0.32)
RUNS = {"n4096": (1, 4096, "n", "u", 300_000_000, 1_000_000_000),
        "n1024u": (1, 1024, "n", "u", 100_000_000, 500_000_000),
        "n1024h": (1, 1024, "n", "h", 100_000_000, 500_000_000),
        "n256": (1, 256, "n", "u", 20_000_000, 200_000_000),
        "d2l64": (2, 64, "n", "u", 200_000_000, 500_000_000),
        "fault": (1, 256, "s", "u", 100_000, 1_000_000)}
BC = (0.66, 0.68)
MAXMIN = 0.68
BELOW, BELOW_SHARE = 0.65, 0.01
FLAT_TOL = 0.05
AGREE = 0.3
GROWTH = 4.0
APART = 0.002
WIN_CX = ((4, 40), (40, 400))
WIN_AV = ((10, 100), (100, 1000), (1000, 10000))
WIN_WT = ((100, 1000), (1000, 10000), (10000, 100000))
LIMIT = 200

OUTPUTS = ("bc", "bc_sizes", "max_min", "below_065", "flat_dev", "cx_exponents", "aval_exponents", "wait_exponents",
           "p99", "halves_max", "starts", "exponents_whole", "minima_mode", "two_d", "fault", "conditions_met",
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


def lbin(x):
    k = math.floor(100.0 * math.log10(float(x)))
    return min(max(k, 0), LBIN - 1)


# ---------------------------------------------------------------- the plain implementation (control)

def plain_run(w4, dim, L, mode, start, warm, meas, snaps, seg, f0s):
    """The C program's "run", step for step in Python's floats, with a plain scan for the minimum."""
    rng = Xoshiro(w4)
    N = L if dim == 1 else L * L
    b = [rng.unif() if start == "u" else 0.9 + 0.1 * rng.unif() for _ in range(N)]
    bh = [[0] * NBIN for _ in range(3)]
    mh = [0] * NBIN
    cx = [0] * (N // 2 + 1)
    wt = [0] * LBIN
    av = [[0] * LBIN for _ in f0s]
    run, nav = [0] * len(f0s), [0] * len(f0s)
    nseg = N // seg if dim == 1 and seg > 0 else 0
    lastseg = [-1] * nseg
    total, snap_every, nsnap = warm + meas, (meas // snaps if snaps > 0 else 0), 0
    maxmin, prev, wsum, minsum = -1.0, -1, 0, 0.0
    for n in range(total):
        m = min(b)
        i = b.index(m)
        for j, f in enumerate(f0s):
            if m < f:
                run[j] += 1
            elif run[j] > 0:
                if n >= warm:
                    av[j][lbin(run[j])] += 1
                    nav[j] += 1
                run[j] = 0
        if n >= warm:
            mh[min(int(m * NBIN), NBIN - 1)] += 1
            minsum += m
            if m > maxmin:
                maxmin = m
            if dim == 1:
                if prev >= 0:
                    d = abs(i - prev)
                    d = min(d, N - d)
                    cx[d] += 1
                if nseg > 0 and i < nseg * seg:
                    k = i // seg
                    if lastseg[k] >= 0:
                        wt[lbin(n - lastseg[k])] += 1
                        wsum += 1
                    lastseg[k] = n
            prev = i
        b[i] = rng.unif()
        if mode != "s":
            if dim == 1:
                left, right = (N - 1 if i == 0 else i - 1), (0 if i == N - 1 else i + 1)
                b[left] = rng.unif()
                b[right] = rng.unif()
            else:
                x, y = i % L, i // L
                for q in (y * L + (x + L - 1) % L, y * L + (x + 1) % L, ((y + L - 1) % L) * L + x,
                          ((y + 1) % L) * L + x):
                    b[q] = rng.unif()
        if n >= warm and snap_every > 0 and (n + 1 - warm) % snap_every == 0 and nsnap < snaps:
            half = 1 if nsnap < snaps // 2 else 2
            for q in range(N):
                bb = min(int(b[q] * NBIN), NBIN - 1)
                bh[0][bb] += 1
                bh[half][bb] += 1
            nsnap += 1
    return {"N": N, "steps": meas, "snapshots": nsnap, "max_min": maxmin, "mean_min": minsum / meas if meas else 0.0,
            "waits": wsum, "avalanches": nav, "open_runs": run, "bhist": bh, "mhist": mh, "cx": cx, "wait": wt,
            "aval": av, "final": b}


# ---------------------------------------------------------------- the C program

def build(work):
    exe = os.path.join(work, "bs1993")
    subprocess.run(["gcc", "-O2", "-ffp-contract=off", "-std=gnu11", "-o", exe, os.path.join(HERE, "bs1993.c"),
                    "-lm"], check=True)
    return exe


def c_run(exe, w4, dim, L, mode, start, warm, meas, snaps, seg, f0s, work, label):
    prefix = os.path.join(work, label)
    out = subprocess.run([exe, "run", *w4, str(dim), str(L), mode, start, str(warm), str(meas), str(snaps), str(seg),
                          prefix, *[repr(float(f)) for f in f0s]], check=True, capture_output=True, text=True).stdout
    got = dict(line.partition("=")[::2] for line in out.splitlines())
    res = {"N": int(got["N"]), "steps": int(got["steps"]), "snapshots": int(got["snapshots"]),
           "max_min": float(got["max_min"]), "mean_min": float(got["mean_min"]), "waits": int(got["waits"]),
           "avalanches": [int(x) for x in got["avalanches"].split(",")],
           "open_runs": [int(x) for x in got["open_runs"].split(",")]}
    bh = [[0] * NBIN for _ in range(3)]
    with open(prefix + ".bhist") as fh:
        for k, line in enumerate(fh):
            for j, v in enumerate(line.split()):
                bh[j][k] = int(v)
    res["bhist"] = bh

    def ints(ext):
        with open(prefix + "." + ext) as fh:
            return [int(x) for x in fh.read().split()]
    res["mhist"], res["cx"], res["wait"] = ints("mhist"), ints("cx"), ints("wait")
    av = [[0] * LBIN for _ in f0s]
    with open(prefix + ".aval") as fh:
        for k, line in enumerate(fh):
            for j, v in enumerate(line.split()):
                av[j][k] = int(v)
    res["aval"] = av
    with open(prefix + ".final") as fh:
        res["final"] = [float(x) for x in fh.read().split()]
    return res


# ---------------------------------------------------------------- measures (rule 4)

def edge(hist):
    """B_c = 1 - 1/h, h the density over [0.70, 1) of a histogram on NBIN bins of [0, 1)."""
    n = sum(hist)
    lo = int(0.70 * NBIN)
    h = sum(hist[lo:]) / (n * 0.30)
    return 1.0 - 1.0 / h if h > 0 else float("nan")


def share_below(hist, x):
    return sum(hist[:int(round(x * NBIN))]) / sum(hist)


def flat_deviation(hist):
    """The largest relative deviation of the six 0.05 bins over [0.70, 1) from their mean."""
    w = NBIN // 20
    parts = [sum(hist[int(0.70 * NBIN) + j * w:int(0.70 * NBIN) + (j + 1) * w]) for j in range(6)]
    mean = sum(parts) / 6
    return max(abs(p - mean) / mean for p in parts) if mean > 0 else float("inf")


def wasserstein(h1, h2):
    n1, n2 = sum(h1), sum(h2)
    if n1 == 0 or n2 == 0:
        return float("nan")
    c1 = c2 = 0
    total = 0.0
    for k in range(len(h1) - 1):
        c1 += h1[k]
        c2 += h2[k]
        total += abs(c1 / n1 - c2 / n2)
    return total / len(h1)


_EDGES = {}


def bin_range(k):
    """The integers x >= 1 with floor(100 log10 x) = k, as [lo, hi) (bins below 1,000 can be empty)."""
    if k in _EDGES:
        return _EDGES[k]

    def first(kk):   # the least integer x >= 1 with floor(100 log10 x) >= kk
        x = max(1, int(10 ** (kk / 100.0)) - 2)
        while math.floor(100.0 * math.log10(float(x))) < kk:
            x += 1
        return x
    r = (first(k), first(k + 1))
    _EDGES[k] = r
    return r


def power_sum(lo, hi, a):
    """sum of x^(-a) over the integers lo <= x < hi."""
    if hi - lo <= 200 or lo < 100:
        return math.fsum(x ** -a for x in range(lo, hi))
    # Euler-Maclaurin for long ranges: integral plus the endpoint corrections
    f = lambda x: x ** -a
    integral = (hi ** (1 - a) - lo ** (1 - a)) / (1 - a) if abs(a - 1) > 1e-12 else math.log(hi / lo)
    return integral + (f(lo) - f(hi)) / 2 + (-a * lo ** (-a - 1) + a * hi ** (-a - 1)) / -12


def mle_exponent(groups, lo, hi):
    """The exponent a of p(x) ~ x^(-a) on integers [lo, hi), maximum likelihood from grouped counts.
    groups: a list of (count, x_lo, x_hi), each a set of integers [x_lo, x_hi) inside [lo, hi)."""
    groups = [(c, a, b) for c, a, b in groups if c > 0 and b > a]
    n = sum(c for c, _, _ in groups)
    if n == 0:
        return float("nan"), 0

    def loglik(a):
        z = power_sum(lo, hi, a)
        return sum(c * math.log(power_sum(x0, x1, a) / z) for c, x0, x1 in groups)
    a_lo, a_hi = 0.01, 8.0
    g = (math.sqrt(5) - 1) / 2
    x1, x2 = a_hi - g * (a_hi - a_lo), a_lo + g * (a_hi - a_lo)
    f1, f2 = loglik(x1), loglik(x2)
    for _ in range(80):
        if f1 < f2:
            a_lo, x1, f1 = x1, x2, f2
            x2 = a_lo + g * (a_hi - a_lo)
            f2 = loglik(x2)
        else:
            a_hi, x2, f2 = x2, x1, f1
            x1 = a_hi - g * (a_hi - a_lo)
            f1 = loglik(x1)
    return (a_lo + a_hi) / 2, n


def groups_from_exact(counts, lo, hi):
    return [(counts[x], x, x + 1) for x in range(lo, min(hi, len(counts)))]


def groups_from_log(hist, lo, hi):
    """The log bins wholly inside [lo, hi) (lo and hi powers of ten, so the windows hold whole bins)."""
    out = []
    for k in range(LBIN):
        a, b = bin_range(k)
        if a >= lo and b <= hi and b > a:
            out.append((hist[k], a, b))
    return out


def window_exponents(groups_fn, data, windows):
    return [mle_exponent(groups_fn(data, lo, hi), lo, hi)[0] for lo, hi in windows]


def power_law(exps):
    return all(e > 0 for e in exps) and all(abs(exps[i + 1] - exps[i]) < AGREE for i in range(len(exps) - 1))


def percentile(hist, q):
    n = sum(hist)
    if n == 0:
        return float("nan")
    c = 0
    for k, v in enumerate(hist):
        c += v
        if c >= q * n:
            return bin_range(k)[0]
    return float("nan")


def mode_of(hist):
    k = max(range(len(hist)), key=lambda j: hist[j])
    return (k + 0.5) / len(hist)


# ---------------------------------------------------------------- the test and the controls

def conditions(r):
    cond = {}
    big = r["n4096"]
    cond["N = 4096: the barriers flat over [0.70, 1) (six 0.05 bins within 5% of their mean)"] = (
        big["flat_dev"] < FLAT_TOL)
    cond[f"N = 4096: under {BELOW_SHARE:.0%} of the barriers below {BELOW}"] = big["below"] < BELOW_SHARE
    cond[f"N = 4096: the threshold B_c within {BC[0]}-{BC[1]}"] = BC[0] <= big["bc"] <= BC[1]
    cond[f"N = 4096: no selected minimum above {MAXMIN}"] = big["max_min"] <= MAXMIN
    cond["N = 4096: C(x) a power law over [4, 40) and [40, 400)"] = power_law(big["cx_exp"])
    cond["N = 4096: avalanche sizes at 0.65 a power law over [10, 10^4)"] = power_law(big["av_exp"])
    cond["N = 4096: 10-site blocks' waits a power law over [10^2, 10^5)"] = power_law(big["wt_exp"])
    p = big["p99"]
    for a, b in ((0.60, 0.63), (0.63, 0.65), (0.65, 0.66)):
        cond[f"N = 4096: the 99th-percentile avalanche at {b} at least {GROWTH:g} times that at {a}"] = (
            p[b] >= GROWTH * p[a])
    for name in ("n256", "n1024u", "n1024h", "n4096"):
        cond[f"{name}: the window's halves less than {APART} apart"] = r[name]["halves"] < APART
    cond[f"N = 1024: the two starts less than {APART} apart"] = r["starts"] < APART
    return cond


def pareto_sample(rng, a, lo, hi, n):
    """Integers on [lo, hi) with p(x) ~ x^(-a), by inverse transform on the exact cumulative sums."""
    w = [x ** -a for x in range(lo, hi)]
    z = math.fsum(w)
    cum, c = [], 0.0
    for v in w:
        c += v / z
        cum.append(c)
    out = []
    for _ in range(n):
        u = rng.unif()
        k0, k1 = 0, len(cum) - 1
        while k0 < k1:
            mid = (k0 + k1) // 2
            if cum[mid] >= u:
                k1 = mid
            else:
                k0 = mid + 1
        out.append(lo + k0)
    return out


def log_hist(values):
    h = [0] * LBIN
    for v in values:
        h[lbin(v)] += 1
    return h


def controls(exe, seed, fault, work):
    same = True
    for dim, L in ((1, 64), (2, 8)):
        f0s = F0 if dim == 1 else F0_2D
        w4 = words(seed, f"bs1993/control/plain/{dim}")
        c = c_run(exe, w4, dim, L, "n", "u", 50_000, 150_000, 100, SEG, f0s, work, f"plain{dim}")
        p = plain_run(w4, dim, L, "n", "u", 50_000, 150_000, 100, SEG, f0s)
        for k in ("N", "steps", "snapshots", "max_min", "waits", "avalanches", "open_runs", "bhist", "mhist", "cx",
                  "wait", "aval", "final"):
            same = same and c[k] == p[k]
        same = same and abs(c["mean_min"] - p["mean_min"]) < 1e-12 and sum(c["avalanches"]) > 0
    fault_ok = fault["flat_dev"] >= FLAT_TOL and not (BC[0] <= fault["bc"] <= BC[1])
    rng = Xoshiro(words(seed, "bs1993/control/estimators"))
    h = [0] * NBIN
    for _ in range(1_000_000):
        h[min(int((0.6 + 0.4 * rng.unif()) * NBIN), NBIN - 1)] += 1
    edge_ok = abs(edge(h) - 0.6) < 0.005
    sample = log_hist(pareto_sample(rng, 1.5, 10, 10_000, 200_000))
    exps = window_exponents(groups_from_log, sample, WIN_AV)
    pareto_ok = all(abs(e - 1.5) < 0.05 for e in exps)
    geo = []
    q = 1.0 / 300.0
    for _ in range(200_000):
        u = 1.0 - rng.unif()
        geo.append(1 + int(math.log(u) / math.log(1.0 - q)))
    gexps = window_exponents(groups_from_log, log_hist(geo), WIN_AV)
    geo_ok = not power_law(gexps)
    a, b = [0] * NBIN, [0] * NBIN
    a[3000], b[3500] = 1, 1
    dist_ok = abs(wasserstein(a, b) - 0.05) < 1e-9
    return ({"the C program matches the plain implementation bit for bit in 1D (N = 64) and 2D (L = 8)": bool(same),
             "the planted model (the lowest barrier alone renewed) fails the flatness and the threshold": fault_ok,
             "the edge estimator gives 0.600 +/- 0.005 on barriers uniform on [0.6, 1)": edge_ok,
             "the exponent estimator gives 1.5 +/- 0.05 in each decade of a discrete power law": pareto_ok,
             "the exponent estimator finds a geometric distribution's decades 0.3 or more apart": geo_ok,
             "the distance gives 0.05 for two point masses 0.05 apart": dist_ok},
            {"pareto_exponents": exps, "geometric_exponents": gexps, "edge_uniform": edge(h)})


def fmt(x, nd=3):
    return f"{x:.{nd}f}"


def run(seed, results="results", log=sys.stderr):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    if shutil.which("gcc") is None:
        raise Refused("no gcc in this image")
    os.makedirs(results, exist_ok=True)
    work = tempfile.mkdtemp(prefix="work-", dir=results)   # the sandbox's /tmp cannot run what is built in it
    exe = build(work)

    r = {}
    for name, (dim, L, mode, start, warm, meas) in RUNS.items():
        f0s = F0_2D if dim == 2 else F0
        res = c_run(exe, words(seed, f"bs1993/{name}"), dim, L, mode, start, warm, meas, SNAPS, SEG, f0s, work, name)
        bh = res["bhist"]
        res["bc"] = edge(bh[0])
        res["below"] = share_below(bh[0], BELOW)
        res["flat_dev"] = flat_deviation(bh[0])
        res["halves"] = wasserstein(bh[1], bh[2])
        res["p99"] = {f: percentile(res["aval"][j], 0.99) for j, f in enumerate(f0s)}
        res["minima_mode"] = mode_of(res["mhist"])
        if dim == 1 and mode == "n":
            res["cx_exp"] = window_exponents(groups_from_exact, res["cx"], WIN_CX)
            j65 = f0s.index(0.65)
            res["av_exp"] = window_exponents(groups_from_log, res["aval"][j65], WIN_AV)
            res["wt_exp"] = window_exponents(groups_from_log, res["wait"], WIN_WT)
            res["cx_whole"] = mle_exponent(groups_from_exact(res["cx"], 4, 400), 4, 400)[0]
            res["av_whole"] = mle_exponent(groups_from_log(res["aval"][j65], 10, 10_000), 10, 10_000)[0]
            res["wt_whole"] = mle_exponent(groups_from_log(res["wait"], 100, 100_000), 100, 100_000)[0]
        if dim == 2:
            j31 = f0s.index(0.31)
            res["av_whole"] = mle_exponent(groups_from_log(res["aval"][j31], 10, 1000), 10, 1000)[0]
        r[name] = res
        print(f"{name}: B_c {res['bc']:.4f}, max minimum {res['max_min']:.4f}, below 0.65 {res['below']:.4f}, "
              f"halves {res['halves']:.5f}, avalanches {res['avalanches']}", file=log)
    r["starts"] = wasserstein(r["n1024u"]["bhist"][0], r["n1024h"]["bhist"][0])

    ctl, ctl_detail = controls(exe, seed, r["fault"], work)
    print(f"controls: {sum(ctl.values())} of {len(ctl)}", file=log)
    if not all(ctl.values()):
        raise AssertionError(f"a control failed: {[c for c, ok in ctl.items() if not ok]}")
    cond = conditions(r)

    big, two = r["n4096"], r["d2l64"]
    values = {
        "bc": round(big["bc"], 5),
        "bc_sizes": "B_c: " + ", ".join(f"N = {r[n]['N']} {r[n]['bc']:.4f}" for n in ("n256", "n1024u", "n4096")),
        "max_min": round(big["max_min"], 5),
        "below_065": round(big["below"], 5),
        "flat_dev": round(big["flat_dev"], 5),
        "cx_exponents": "C(x) [4,40) " + fmt(big["cx_exp"][0]) + ", [40,400) " + fmt(big["cx_exp"][1]),
        "aval_exponents": "sizes at 0.65: " + ", ".join(f"[10^{i + 1},10^{i + 2}) {e:.3f}"
                                                      for i, e in enumerate(big["av_exp"])),
        "wait_exponents": "waits: " + ", ".join(f"[10^{i + 2},10^{i + 3}) {e:.3f}"
                                                for i, e in enumerate(big["wt_exp"])),
        "p99": "99th-percentile avalanche: " + ", ".join(f"{f:g} {big['p99'][f]}" for f in F0),
        "halves_max": round(max(r[n]["halves"] for n in ("n256", "n1024u", "n1024h", "n4096")), 6),
        "starts": round(r["starts"], 6),
        "exponents_whole": (f"C(x) [4,400) {big['cx_whole']:.3f}; sizes at 0.65 [10,10^4) {big['av_whole']:.3f}; "
                            f"waits [10^2,10^5) {big['wt_whole']:.3f}"),
        "minima_mode": round(big["minima_mode"], 4),
        "two_d": (f"2D L = 64: B_c {two['bc']:.4f}, max minimum {two['max_min']:.4f}, sizes at 0.31 [10,10^3) "
                  f"{two['av_whole']:.3f}"),
        "fault": (f"lowest barrier alone renewed: B_c {r['fault']['bc']:.4f}, flat deviation "
                  f"{r['fault']['flat_dev']:.3f}, below 0.65 {r['fault']['below']:.4f}"),
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
        d = {k: res[k] for k in ("N", "steps", "snapshots", "max_min", "mean_min", "waits", "avalanches", "open_runs",
                                 "bc", "below", "flat_dev", "halves", "minima_mode") if k in res}
        d["p99"] = {f"{f:g}": v for f, v in res["p99"].items()}
        for k in ("cx_exp", "av_exp", "wt_exp", "cx_whole", "av_whole", "wt_whole"):
            if k in res:
                d[k] = res[k]
        d["barrier_hist_100"] = [sum(res["bhist"][0][100 * j:100 * (j + 1)]) for j in range(100)]
        d["minima_hist_100"] = [sum(res["mhist"][100 * j:100 * (j + 1)]) for j in range(100)]
        d["cx_first_400"] = res["cx"][:400]
        d["wait_log10"] = [sum(res["wait"][100 * j:100 * (j + 1)]) for j in range(13)]
        d["aval_log10"] = [[sum(h[100 * j:100 * (j + 1)]) for j in range(13)] for h in res["aval"]]
        return d

    detail = {"conditions": cond, "controls": ctl, "control_detail": ctl_detail,
              "runs": {n: keep(r[n]) for n in RUNS}, "starts": r["starts"],
              "paper": {"B_c": "0.67 +/- 0.01", "C(x) exponent": "3.15 +/- 0.05", "avalanche exponent": "0.9 +/- 0.1",
                        "2D avalanche exponent": "about 1.1", "Figure 2 N": 4096, "Figure 5 threshold": 0.65},
              "later": {"f_c": 0.66702, "pi": 3.23, "tau": 1.07, "f_c_2D": 0.328, "tau_2D": 1.245}}
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
        sys.exit(f"bs1993: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
