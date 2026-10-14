#!/usr/bin/env python3
"""Jain & Krishna (2001): a small autocatalytic set appears by chance and spreads across the graph on the timescale
2/p.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:d7d1f3a2067c2293) is from Jain and Krishna,
"A model for the emergence of cooperation, interdependence, and structure in evolving networks" (PNAS 98, 543-547,
2001; arXiv:nlin/0005039): "A small autocatalytic set, appearing by chance, provides the seed for the spontaneous
growth of connectivity and cooperation in the graph. A highly structured chemical organization arises inevitably as the
autocatalytic set enlarges and percolates through the network in a short analytically determined timescale."

Its registered test: refuted if, in 50 seeded runs of the model at s = 100 and x0 = 1e-4 for each of p = 0.0012,
0.0025 and 0.005 (Figure 2's three largest p), a run's graph is not entirely an ACS within 40/(p^2 s) + 40/p graph
updates; or, at some p, the mean update n1 at which an ACS first appears is not within a factor of two of
tau_a = 4/(p^2 s), or the mean (n2 - n1)/ln(s/s1(n1)) is more than 25% from tau_g = 2/p, n2 being the first update at
which the whole graph is an ACS and n1, s1(n1) the update and ACS size at its last appearance before n2; or the slope
of ln of that mean on ln p is outside -1 +/- 0.2.

Standard library and the image's gcc: the model is simulated in C (alife/jk.c, compiled here). No data are read: the
runs are generated under the seed. Every rule below was fixed before any run of the model.

1. The model (the paper's Model section, read from the arXiv e-print nlin/0005039v1): s = 100 species; c_ij, the link
   from j to i, nonzero with probability p, then uniform in [-1, 1] for i != j and in [-1, 0] for i = j; the
   populations x uniform in [0, 1], rescaled to sum 1. Each graph update: (1) the populations follow equation (1) for a
   time T, X = x(T); (2) one of the least fit nodes, chosen at random, is removed with its links; (3) a new species
   takes its place, its links drawn by the same rule, its population x0 = 1e-4 (Figure 1), the others rescaled to sum
   1 - x0. The populations carry over from one update to the next.
2. The numerics, which the paper does not give: equation (1) is the linear system ydot = C y with x = y / sum y and the
   same rule holding x_i at 0 while f_i < 0 (its normalising term rescales every x_i alike, so it never changes their
   ratios or which are zero); integrated for T = 100 by the classical fourth-order Runge-Kutta method with step 0.2, a
   component that would go below 0 set to 0, rescaled to sum 1 every 100 steps. X_i <= 1e-10 counts as 0: the least fit
   are all such nodes, tied, if there are any, and otherwise those with the least X_i. s1 is the number with X_i > 1e-10.
3. Autocatalytic sets (the paper's definition: every member has an incoming positive link from a member). The maximal
   ACS, the union of all of them, by pruning: strike off every node with no positive link from a node not struck off,
   until none is left to strike. A graph contains an ACS if any node is left (it then holds a cycle of positive links),
   and is entirely an ACS if every node is. Its size is the ACS's size, s1(n1) in the test.
4. A run starts from a random graph (update 0) and stops at n2, the first update at which the whole graph is an ACS, or
   at the cap 40/(p^2 s) + 40/p. n1 is the first update at which the graph contains an ACS (0 if the initial graph
   does); if the ACS is ever lost entirely, its last appearance before n2 starts the growth: the run's growth time is
   (n2 - m1)/ln(s/a(m1)), m1 that update and a(m1) the ACS's size then (m1 = n1 when it is never lost).
5. The test's ten conditions: at each p, every run entirely an ACS within the cap; the mean n1 between tau_a/2 and
   2 tau_a, tau_a = 4/(p^2 s); the mean growth time between 0.75 and 1.25 times tau_g = 2/p; and the least-squares slope
   of ln(mean growth time) on ln p over the three p within -1 +/- 0.2. test_passed is 1 if all ten hold.
6. Beside the test, none of it counted: the spread of n1 (a geometric arrival has SD about its mean) and how many
   initial graphs already hold an ACS; the least-squares e-folding time of the ACS's size from m1 to n2; the ACS's size
   and populated nodes when it appears; the runs whose ACS was lost entirely before n2; the positive and negative links
   and populated nodes at n2 (the paper's run: 117 positive links) and the chance, by the paper's equation (prob), that
   a random graph with that many positive links is entirely an ACS (about 1e-16 for 117); and the mean populated nodes
   before the first ACS.

Controls (controls_passed counts those that behave as stated): the C program matches a plain implementation written
here bit for bit over 30 updates of a small model, its pruning matching the plain maximal ACS (nodes on or downstream of
a cycle of positive links) at every update; on a positive 2-cycle with a tail, the populations after T = 300 are its
Perron-Frobenius eigenvector within 1e-9, an isolated and a self-inhibited node at 0; a node whose only link is a
negative one from a populated node is held at exactly 0; pruning and the cycle method agree on 300 seed-drawn random
graphs and four made by hand; and the initial graphs' mean numbers of positive and negative links are within four
standard errors of p s(s - 1)/2 and p s(s - 1)/2 + p s at every p.

What it cannot check: the paper's own runs, which are not published; its PNAS text, which could not be read here (the
model is the e-print's); its Figure 2 below p = 0.0012, where an ACS takes 10^5 to 10^8 updates to appear; and the
catastrophes after n2.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 alife/jk.py
"""

import concurrent.futures as cf
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
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
SPECIES = 100
X0 = "1e-4"
PS = ("0.0012", "0.0025", "0.005")
RUNS = 50
T = "100"
DT = "0.2"
EPS = "1e-10"
RENORM = 100
FLUSH = 1e-250
FACTOR = 2                                     # the band for the mean n1: tau_a / 2 to 2 tau_a
BAND = 0.25                                    # the band for the mean growth time: 0.75 to 1.25 tau_g
SLOPE_BAND = 0.2
LIMIT = 200
OUTPUTS = ("runs", "spanned", "first_acs", "first_acs_spread", "growth", "growth_slope", "growth_fit", "acs_at_birth",
           "losses", "structure_n2", "chance", "before_acs", "initial_links", "conditions_met", "conditions_total",
           "test_passed", "controls_passed", "controls_total")
MASK = (1 << 64) - 1


class Refused(Exception):
    pass


# ---------------------------------------------------------------- the paper's numbers

def tau_a(p, s=SPECIES):
    return Fraction(4) / (Fraction(p) ** 2 * s)


def tau_g(p):
    return Fraction(2) / Fraction(p)


def cap(p, s=SPECIES):
    return math.ceil(Fraction(40) / (Fraction(p) ** 2 * s) + Fraction(40) / Fraction(p))


def growth_time(run, s=SPECIES):
    """(n2 - m1)/ln(s/a(m1)), or None for a run that never spanned the graph (or spanned it at once)."""
    if run["n2"] < 0 or run["a_m1"] >= s or run["a_m1"] <= 0:
        return None
    return (run["n2"] - run["m1"]) / math.log(s / run["a_m1"])


def chance_log10(lp, s=SPECIES):
    """log10 of the paper's equation (prob): [1 - (1 - m*/(s-1))^(s-1)]^s, m* = lp/s."""
    m = lp / s
    return s * math.log10(1.0 - (1.0 - m / (s - 1)) ** (s - 1))


def slope(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)


def mean(v):
    return sum(v) / len(v)


def sd(v):
    m = mean(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))


def median(v):
    w = sorted(v)
    k = len(w) // 2
    return w[k] if len(w) % 2 else (w[k - 1] + w[k]) / 2


# ---------------------------------------------------------------- seeds and the generator

class Stream:
    """Integers from the seed: SHA-256 of seed, label and a counter."""

    def __init__(self, seed, label):
        self.seed, self.label, self.n = seed, label, 0

    def below(self, m):
        self.n += 1
        h = hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
        return int.from_bytes(h[:8], "big") % m


def words(seed, label):
    """Four 64-bit words for the C generator (xoshiro256**), from SHA-256 of seed and label."""
    h = hashlib.sha256(f"{seed}/{label}".encode()).digest()
    w = [h[i:i + 8].hex() for i in range(0, 32, 8)]
    if all(int(x, 16) == 0 for x in w):
        raise Refused("an all-zero generator state")
    return w


def _rotl(v, k):
    return ((v << k) | (v >> (64 - k))) & MASK


class Xoshiro:
    """xoshiro256**, as alife/jk.c has it."""

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
        k = int(self.unif() * float(m))
        return k if k < m else m - 1


# ---------------------------------------------------------------- maximal ACS, two ways

def acs_pruning(c):
    """Strike off nodes with no positive link from a node not struck off; the rest is the maximal ACS."""
    s = len(c)
    left = set(range(s))
    changed = True
    while changed:
        changed = False
        for i in sorted(left):
            if not any(j != i and j in left and c[i][j] > 0.0 for j in range(s)):
                left.discard(i)
                changed = True
    return left


def acs_cycles(c):
    """The nodes on a cycle of positive links and every node a positive path leads to from one."""
    s = len(c)
    out = [[i for i in range(s) if i != j and c[i][j] > 0.0] for j in range(s)]      # j -> i

    def reach(j):
        seen, todo = set(), list(out[j])
        while todo:
            v = todo.pop()
            if v not in seen:
                seen.add(v)
                todo.extend(out[v])
        return seen

    reaches = [reach(j) for j in range(s)]
    on_cycle = {j for j in range(s) if j in reaches[j]}
    members = set(on_cycle)
    for j in on_cycle:
        members |= reaches[j]
    return members


# ---------------------------------------------------------------- a plain implementation, for the bit-for-bit control

class Plain:
    def __init__(self, w, s, p, x0, t, dt, eps):
        self.g = Xoshiro(w)
        self.s, self.p, self.x0, self.t, self.dt, self.eps = s, float(p), float(x0), float(t), float(dt), float(eps)
        self.c = [[self.draw(i == j) for j in range(s)] for i in range(s)]
        x = [self.g.unif() for _ in range(s)]
        tot = 0.0
        for v in x:
            tot += v
        self.x = [v / tot for v in x]

    def draw(self, diag):
        u = self.g.unif()
        if not u < self.p:
            return 0.0
        v = self.g.unif()
        return -v if diag else 2.0 * v - 1.0

    def renorm(self, y):
        tot = 0.0
        for v in y:
            tot += v
        out = []
        for v in y:
            q = v / tot
            out.append(0.0 if q < FLUSH else q)
        return out

    def evolve(self):
        s, c = self.s, self.c
        rows = [(i, [(j, c[i][j]) for j in range(s) if c[i][j] != 0.0]) for i in range(s)]
        rows = [(i, r) for i, r in rows if r]
        y = list(self.x)
        steps = round(self.t / self.dt)
        h2, h6, dt = 0.5 * self.dt, self.dt / 6.0, self.dt

        def deriv(z):
            k = {}
            for i, r in rows:
                f = 0.0
                for j, v in r:
                    f += v * z[j]
                if not z[i] > 0.0 and f < 0.0:
                    f = 0.0
                k[i] = f
            return k

        for n in range(1, steps + 1):
            k1 = deriv(y)
            yt = list(y)
            for i, _ in rows:
                yt[i] = y[i] + h2 * k1[i]
            k2 = deriv(yt)
            for i, _ in rows:
                yt[i] = y[i] + h2 * k2[i]
            k3 = deriv(yt)
            for i, _ in rows:
                yt[i] = y[i] + dt * k3[i]
            k4 = deriv(yt)
            for i, _ in rows:
                inc = k1[i] + 2.0 * k2[i]
                inc = inc + 2.0 * k3[i]
                inc = inc + k4[i]
                v = y[i] + h6 * inc
                y[i] = v if v > 0.0 else 0.0
            if n % RENORM == 0:
                y = self.renorm(y)
        self.x = self.renorm(y)

    def least_fit(self):
        z = [i for i, v in enumerate(self.x) if v <= self.eps]
        if not z:
            m = min(self.x)
            z = [i for i, v in enumerate(self.x) if v == m]
        return z[self.g.below(len(z))]

    def replace(self, i0):
        rest = 0.0
        for i, v in enumerate(self.x):
            if i != i0:
                rest += v
        f = (1.0 - self.x0) / rest
        self.x = [self.x0 if i == i0 else v * f for i, v in enumerate(self.x)]
        for j in range(self.s):
            self.c[i0][j] = self.draw(j == i0)
        for j in range(self.s):
            if j != i0:
                self.c[j][i0] = self.draw(False)


def hexbits(v):
    return struct.pack(">d", v).hex()


def plain_trace(w, s, p, x0, t, dt, eps, updates):
    m = Plain(w, s, p, x0, t, dt, eps)
    lines = [" ".join(["start", str(len(acs_cycles(m.c)))] + [hexbits(v) for v in m.x])]
    for n in range(1, updates + 1):
        m.evolve()
        lines.append(" ".join(["X"] + [hexbits(v) for v in m.x]))
        i0 = m.least_fit()
        m.replace(i0)
        members = sorted(acs_cycles(m.c))
        lines.append(" ".join(["update", str(n), "removed", str(i0), "acs", str(len(members)), "members"]
                              + [str(i) for i in members]))
    return lines


# ---------------------------------------------------------------- the C program

def build(work):
    exe = os.path.join(work, "jk")
    subprocess.run(["gcc", "-O2", "-ffp-contract=off", "-std=gnu11", "-o", exe, os.path.join(HERE, "jk.c"), "-lm"],
                   check=True)
    return exe


def c_run(exe, seed, p, r):
    w = words(seed, f"jk/run/{p}/{r}")
    out = subprocess.run([exe, "run", *w, str(SPECIES), p, X0, T, DT, EPS, str(cap(p))], check=True,
                         capture_output=True, text=True).stdout.split()
    if len(out) != 30 or out[0::2] != ["n1", "a_n1", "s1_n1", "m1", "a_m1", "n2", "losses", "s1_n2", "lp", "ln",
                                       "lp0", "ln0", "pre_mean", "slope", "updates"]:
        raise Refused(f"jk/run/{p}/{r}: unreadable output")
    keys, vals = out[0::2], out[1::2]
    res = {k: (float(v) if k in ("pre_mean", "slope") else int(v)) for k, v in zip(keys, vals)}
    res["run"] = r
    return res


def c_trace(exe, w, s, p, x0, t, dt, eps, updates):
    r = subprocess.run([exe, "trace", *w, str(s), p, x0, t, dt, eps, str(updates)], check=True, capture_output=True,
                       text=True)
    return r.stdout.strip().split("\n")


def c_graph(exe, s, t, dt, entries):
    args = [exe, "graph", str(s), t, dt, EPS, str(len(entries))]
    for i, j, c in entries:
        args += [str(i), str(j), c]
    out = subprocess.run(args, check=True, capture_output=True, text=True).stdout.split()
    return int(out[1]), [float(v) for v in out[2:]]


# ---------------------------------------------------------------- controls

def control_trace(exe, seed):
    w = words(seed, "jk/trace")
    args = (12, "0.25", X0, "30", DT, EPS, 30)
    got = c_trace(exe, w, *args)
    want = plain_trace(w, 12, "0.25", X0, "30", DT, EPS, 30)
    removed = sum(1 for line in want if line.startswith("update"))
    return got == want, {"updates": removed, "lines": len(want), "matching_lines": sum(a == b for a, b in zip(got, want)),
                         "final": want[-1][:120]}


def control_perron(exe):
    n, x = c_graph(exe, 5, "300", DT, [(1, 0, "0.5"), (0, 1, "0.8"), (2, 1, "0.3"), (4, 4, "-0.5")])
    lam = math.sqrt(0.5 * 0.8)
    v = [0.8 / lam, 1.0, 0.3 / lam, 0.0, 0.0]
    tot = sum(v)
    v = [a / tot for a in v]
    err = max(abs(a - b) for a, b in zip(x, v))
    ok = n == 3 and err < 1e-9 and x[3] <= float(EPS) and x[4] <= float(EPS)
    return ok, {"populated": n, "max_error": err, "X": x}


def control_clamp(exe):
    n, x = c_graph(exe, 3, "50", DT, [(1, 0, "0.5"), (0, 1, "0.8"), (2, 0, "-0.4")])
    return n == 2 and x[2] == 0.0, {"populated": n, "X": x}


def hand_graphs():
    def g(s, links):
        c = [[0.0] * s for _ in range(s)]
        for i, j, v in links:
            c[i][j] = v
        return c
    return [
        ("a chain of positive links", g(4, [(1, 0, 0.5), (2, 1, 0.5), (3, 2, 0.5)]), set()),
        ("a positive 2-cycle with a tail", g(4, [(1, 0, 0.5), (0, 1, 0.7), (2, 1, 0.2), (0, 3, -0.9)]), {0, 1, 2}),
        ("a negative 2-cycle", g(3, [(1, 0, -0.5), (0, 1, -0.7), (2, 1, 0.4)]), set()),
        ("a positive ring through every node", g(5, [((i + 1) % 5, i, 0.3) for i in range(5)]), set(range(5))),
    ]


def control_acs(seed):
    st = Stream(seed, "jk/acs")
    agree, bad = 0, []
    for k in range(300):
        s = 30
        q = (2 + st.below(14)) / 100
        c = [[0.0] * s for _ in range(s)]
        for i in range(s):
            for j in range(s):
                if st.below(10 ** 6) < q * 10 ** 6:
                    c[i][j] = (st.below(2001) - 1000) / 1000 if i != j else -st.below(1001) / 1000
        a, b = acs_pruning(c), acs_cycles(c)
        if a == b:
            agree += 1
        else:
            bad.append(k)
    hand = {name: acs_pruning(c) == want == acs_cycles(c) for name, c, want in hand_graphs()}
    return agree == 300 and all(hand.values()), {"random_graphs_agreeing": agree, "disagreeing": bad[:5], "hand": hand}


def control_links(results):
    out, ok = {}, True
    s = SPECIES
    for p in PS:
        q = float(p)
        pairs = s * (s - 1)
        e_pos = pairs * q / 2
        e_neg = pairs * q / 2 + s * q
        v_pos = pairs * (q / 2) * (1 - q / 2)
        v_neg = v_pos + s * q * (1 - q)
        rs = results[p]
        m_pos, m_neg = mean([r["lp0"] for r in rs]), mean([r["ln0"] for r in rs])
        z_pos = (m_pos - e_pos) / math.sqrt(v_pos / len(rs))
        z_neg = (m_neg - e_neg) / math.sqrt(v_neg / len(rs))
        ok = ok and abs(z_pos) <= 4 and abs(z_neg) <= 4
        out[p] = {"positive": m_pos, "expected_positive": e_pos, "z_positive": z_pos, "negative": m_neg,
                  "expected_negative": e_neg, "z_negative": z_neg}
    return ok, out


# ---------------------------------------------------------------- the run

def fmt(v, nd=1):
    return f"{v:.{nd}f}"


def listing(values):
    return ", ".join(values)


def conditions(stats, slope_value):
    cond = {}
    for p in PS:
        st = stats[p]
        cond[f"p = {p}: every run entirely an ACS within {cap(p)} updates"] = st["spanned"] == st["runs"]
        cond[f"p = {p}: the mean n1 within a factor of two of tau_a = {float(tau_a(p)):.0f}"] = (
            st["n1_mean"] is not None and float(tau_a(p)) / FACTOR <= st["n1_mean"] <= FACTOR * float(tau_a(p)))
        cond[f"p = {p}: the mean growth time within 25% of tau_g = {float(tau_g(p)):.0f}"] = (
            st["g_mean"] is not None and abs(st["g_mean"] / float(tau_g(p)) - 1.0) <= BAND)
    cond["the slope of ln(mean growth time) on ln p within -1 +/- 0.2"] = (
        slope_value is not None and abs(slope_value + 1.0) <= SLOPE_BAND)
    return cond


def summarise(results):
    stats = {}
    for p in PS:
        rs = results[p]
        spanned = [r for r in rs if r["n2"] >= 0]
        n1s = [r["n1"] for r in rs if r["n1"] >= 0]
        gs = [g for g in (growth_time(r) for r in rs) if g is not None]
        fits = [1.0 / r["slope"] for r in spanned if r["slope"] > 0]
        stats[p] = {
            "runs": len(rs), "spanned": len(spanned), "latest_n2": max((r["n2"] for r in spanned), default=-1),
            "n1_mean": mean(n1s) if n1s else None, "n1_sd": sd(n1s) if len(n1s) > 1 else None,
            "n1_median": median(n1s) if n1s else None, "acs_at_start": sum(1 for r in rs if r["n1"] == 0),
            "g_mean": mean(gs) if gs else None, "g_sd": sd(gs) if len(gs) > 1 else None, "g_runs": len(gs),
            "fit_mean": mean(fits) if fits else None,
            "a_n1_mean": mean([r["a_n1"] for r in rs if r["n1"] >= 0]) if n1s else None,
            "s1_n1_mean": mean([r["s1_n1"] for r in rs if r["s1_n1"] >= 0]) if n1s else None,
            "loss_runs": sum(1 for r in rs if r["losses"] > 0), "losses": sum(r["losses"] for r in rs),
            "lp_n2": mean([r["lp"] for r in spanned]) if spanned else None,
            "ln_n2": mean([r["ln"] for r in spanned]) if spanned else None,
            "s1_n2": mean([r["s1_n2"] for r in spanned]) if spanned else None,
            "pre_mean": mean([r["pre_mean"] for r in rs if r["pre_mean"] >= 0]) if any(
                r["pre_mean"] >= 0 for r in rs) else None,
            "tau_a": float(tau_a(p)), "tau_g": float(tau_g(p)), "cap": cap(p),
        }
    gm = [stats[p]["g_mean"] for p in PS]
    slope_value = slope([math.log(float(p)) for p in PS], [math.log(g) for g in gm]) if all(gm) else None
    return stats, slope_value


def values_from(stats, slope_value, cond, controls):
    def each(key, nd=1, scale=1.0):
        return listing("-" if stats[p][key] is None else fmt(stats[p][key] * scale, nd) for p in PS)

    def ratio(key, ref):
        return listing("-" if stats[p][key] is None else fmt(stats[p][key] / stats[p][ref], 3) for p in PS)

    chance = listing("-" if stats[p]["lp_n2"] is None else fmt(chance_log10(stats[p]["lp_n2"]), 1) for p in PS)
    return {
        "runs": (f"{RUNS} runs at each p = {', '.join(PS)}; s = {SPECIES}, x0 = {X0}; T = {T} between updates "
                 f"(RK4, step {DT}); X <= {EPS} counts as 0"),
        "spanned": (f"runs entirely an ACS within the cap: {listing(str(stats[p]['spanned']) + '/' + str(RUNS) for p in PS)}"
                    f"; latest n2 {listing(str(stats[p]['latest_n2']) for p in PS)} (caps "
                    f"{listing(str(cap(p)) for p in PS)})"),
        "first_acs": (f"mean n1 {each('n1_mean')}; tau_a = 4/(p^2 s) {listing(fmt(float(tau_a(p)), 0) for p in PS)}; "
                      f"ratio {ratio('n1_mean', 'tau_a')}"),
        "first_acs_spread": (f"n1: SD/mean {listing('-' if stats[p]['n1_sd'] is None else fmt(stats[p]['n1_sd'] / stats[p]['n1_mean'], 2) for p in PS)}; "
                             f"median {each('n1_median', 0)}; an ACS at n = 0 in {listing(str(stats[p]['acs_at_start']) for p in PS)} runs"),
        "growth": (f"mean (n2 - n1)/ln(s/s1(n1)) {each('g_mean')}; tau_g = 2/p "
                   f"{listing(fmt(float(tau_g(p)), 0) for p in PS)}; ratio {ratio('g_mean', 'tau_g')}"),
        "growth_slope": None if slope_value is None else round(slope_value, 4),
        "growth_fit": (f"least-squares e-folding time of the ACS's size, n1 to n2: {each('fit_mean')}; ratio to 2/p "
                       f"{ratio('fit_mean', 'tau_g')}"),
        "acs_at_birth": (f"mean size of the ACS when it appears {each('a_n1_mean', 2)}; its populated nodes "
                         f"{each('s1_n1_mean', 2)}"),
        "losses": (f"runs whose ACS was lost entirely before n2: {listing(str(stats[p]['loss_runs']) for p in PS)} "
                   f"({listing(str(stats[p]['losses']) for p in PS)} losses)"),
        "structure_n2": (f"at n2, mean positive links {each('lp_n2')}, negative {each('ln_n2')}, populated nodes "
                         f"{each('s1_n2')}"),
        "chance": f"log10 chance that a random graph with that many positive links is entirely an ACS: {chance}",
        "before_acs": f"mean populated nodes before the first ACS: {each('pre_mean')}",
        "initial_links": "; ".join(f"{p}: +{controls['links'][p]['positive']:.1f} -{controls['links'][p]['negative']:.1f}"
                                   for p in PS) + " (mean links at n = 0)",
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
    }


def run(seed, results="results", workers=None):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    if shutil.which("gcc") is None:
        raise Refused("no gcc in this image")
    os.makedirs(results, exist_ok=True)
    work = tempfile.mkdtemp(prefix="work-", dir=results)   # the sandbox's /tmp cannot run what is built in it
    try:
        exe = build(work)
        ctl, ctl_detail = {}, {}
        ok, ctl_detail["trace"] = control_trace(exe, seed)
        ctl["the C program matches the plain implementation bit for bit over 30 updates, its ACS at each included"] = ok
        ok, ctl_detail["perron"] = control_perron(exe)
        ctl["a positive 2-cycle with a tail settles on its Perron-Frobenius eigenvector"] = ok
        ok, ctl_detail["clamp"] = control_clamp(exe)
        ctl["a node with only a negative link from a populated node is held at exactly 0"] = ok
        ok, ctl_detail["acs"] = control_acs(seed)
        ctl["pruning and the cycle method agree on 300 random graphs and four by hand"] = ok
        if not all(ctl.values()):
            raise Refused("a control failed before the runs: " + json.dumps(ctl_detail, default=str)[:400])

        workers = workers or max(1, os.cpu_count() or 1)
        jobs = [(p, r) for p in PS for r in range(1, RUNS + 1)]
        with cf.ThreadPoolExecutor(workers) as pool:
            futs = {job: pool.submit(c_run, exe, seed, *job) for job in jobs}
            done = {job: f.result() for job, f in futs.items()}
        res = {p: [done[(p, r)] for r in range(1, RUNS + 1)] for p in PS}

        ok, ctl_detail["links"] = control_links(res)
        ctl["the initial graphs' mean link counts within four standard errors of p s(s-1)/2 (+ p s)"] = ok
        stats, slope_value = summarise(res)
        cond = conditions(stats, slope_value)
        values = values_from(stats, slope_value, cond, ctl_detail)
        values["controls_passed"] = sum(ctl.values())
        values["controls_total"] = len(ctl)
        out = {k: values[k] for k in OUTPUTS}
        for key, v in out.items():
            if isinstance(v, str) and len(v) > LIMIT:
                raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")
        detail = {"conditions": cond, "controls": ctl, "control_detail": ctl_detail, "stats": stats,
                  "slope": slope_value, "runs": res,
                  "parameters": {"s": SPECIES, "x0": X0, "p": PS, "runs": RUNS, "T": T, "dt": DT, "eps": EPS,
                                 "renorm_every": RENORM, "flush": FLUSH}}
        with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
            json.dump(out, fh, indent=2, sort_keys=True)
            fh.write("\n")
        with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as fh:
            json.dump(detail, fh, indent=1, sort_keys=True)
            fh.write("\n")
        return out, detail
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"jk: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
