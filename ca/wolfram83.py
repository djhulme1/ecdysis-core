#!/usr/bin/env python3
"""Wolfram's legal elementary cellular automata from a single site: homogeneous, or self-similar with fractal
dimension log2 3 or log2(1 + sqrt 5).

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from Wolfram, "Statistical mechanics of
cellular automata" (Reviews of Modern Physics 55, 601-644, 1983; doi:10.1103/RevModPhys.55.601), its abstract as the
index prints it: "With simple initial configurations, the cellular automata either tend to homogeneous states, or
generate self-similar patterns with fractal dimensions ~1.59 or ~1.69." The cellular automata are the paper's 32
legal elementary rules (its Sec. II, Fig. 3, and Sec. VI: "The 32 possible (legal) elementary cellular automata were
found to fall into two broad classes"), and the simplest initial configuration is a single site with value 1, the one
its Fig. 3 evolves and its Sec. VI names ("the very simplest initial state in which only one site had a nonzero
value").

No data of record: the rules are defined by construction, by the paper's Fig. 1 numbering (the new value of a site is
bit 4l + 2c + r of the rule number, l, c and r being the old values of its left neighbour, itself and its right
neighbour), so every run is new. Standard library, and numpy for box counting beside the test. Every rule below was
fixed before any pattern of a legal rule was computed; before the commit the machinery ran only on the tests' inputs
(other rules, Pascal's triangle built by Lucas's theorem, constructed cones and random cones).

1. Rules. The legal rules are those with a(000) = 0, a(100) = a(001) and a(110) = a(011) (the paper's quiescence and
   reflection conditions). There must be 32 and they must be the 32 of the paper's Fig. 3 (LEGAL_PRINTED, read from
   its panels), or the run is refused.
2. Evolution. From a single site with value 1 on an infinite line of 0s, T = 4,096 rows (t = 0 to 4,095), each row
   held exactly as an integer, one bit a site; a quiescent rule cannot reach beyond |x| <= t, which the run asserts.
3. Homogeneous. A rule tends to a homogeneous state if (a) some row t >= 1 is all 0 (it dies; the paper's rules 0 and
   160), (b) every row equals row 0 (it stays unchanged; rules 4 and 36), or (c) from row 2,048 on, the interior of each
   row (the sites more than 8 sites inside its outermost 1s, at least 16 of them) is periodic in space with one period
   p <= 4 and in time with one period q <= 2, the same p and q for all those rows (a uniform structure, which the
   paper's rules 50 and 122 make).
4. Self-similar. Otherwise, with S_v(k) the number of sites with value v between the outermost 1s of rows 0 to
   2^k - 1, and v the value with the smaller S_v(12) (the rarer value, the sites that carry the pattern's structure:
   the 1s of rule 90's Sierpinski pattern, the 0s of a pattern whose large triangles are filled with 1s), D(k) =
   log2(S_v(k) / S_v(k-1)). The pattern is self-similar with dimension d if |D(12) - d| <= 0.02 and |D(11) - d| <= 0.02,
   for d = log2 3 or d = log2(1 + sqrt 5) = log2(2 phi), the paper's 1.59 and 1.69 (its eqs. 3.5 and 3.6).
5. The test (TEST). Refuted if some legal rule is neither homogeneous nor self-similar with one of the two dimensions,
   or if one of the two dimensions occurs for no rule. test_passed is 1 if neither happens.

Beside the test, none of it counted:
 - the dimension of the nonzero sites, D(12) and D(11) with v = 1 whatever is rarer: the paper defines a pattern's
   dimension by covering "all sites with nonzero values" (its p. 616), which for a pattern whose large triangles are
   filled with 1s is not the dimension of its structure;
 - box-counting dimensions (square boxes of 8 to 256 sites a side, least squares) of the rarer value's sites and of
   the nonzero sites, for the rules found self-similar; boxes of 2 and 4 are left out because there the lattice bends
   the counts (on Pascal's triangle built by Lucas's theorem, before the commit, the local slopes from boxes of 1 to 4
   were 0.585 and 1.263, and from 8 on 1.585);
 - eq. 3.2: rule 90 has 2^#1(t) sites with value 1 at step t (#1(t) the number of 1s in t's binary digits), t < 4,096;
 - rule 150's number of sites with value 1 at step t against the product of chi(j) over the runs of j 1s in t's binary
   digits, chi(1) = 3, under the printed recurrence chi(j) = (2j + 1) chi(j - 1) for odd j and (2j - 1) chi(j - 1) for
   even j, and under chi(j) = 2 chi(j - 1) + 1 for odd j and 2 chi(j - 1) - 1 for even j, which gives the printed
   examples chi(2) = 5 and chi(3) = 11;
 - the paper's p. 604 classes: the rules with 100 -> 0 and 001 -> 0 are those whose initial 1 is erased or stays, and
   its named examples (erased 0 and 160, unchanged 4 and 36, uniform 50 and 122, complex 18, 22 and 90); and which of
   Fig. 16's complex rules (18, 22, 90, 122, 126, 146, 150, 182) are self-similar from a single site, against Sec. VI
   ("The complex rules were found to yield self-similar fractal patterns. For all but one of the rules ... log2 3");
 - seeds of width 1 to 4 (1, 11, 101, 111, 1001, 1011, 1101, 1111) under the complex rules, classified as in 3 and 4
   (Sec. III: patterns grown from any simple initial state by the complex rules but 150 have dimension log2 3);
 - the 128 quiescent elementary rules (a(000) = 0), legal or not, from a single site, classified as in 3 and 4 except
   that a pattern no wider than 8 sites from row 2,048 is "bounded" (a still or moving remnant) and only periodicity in
   space is asked of a uniform interior (a shifting rule's interior repeats in time only up to a shift); the paper's
   p. 607: "consideration of illegal as well as "legal" cellular automaton rules introduces no qualitatively new
   features";
 - Sec. IV: the cycle length Pi_N and transient Upsilon_N of rules 90 and 150 on rings of N = 3 to 30 sites from one
   nonzero site, against the printed list (the same for both rules, it says) and the printed Upsilon_N (rule 90: 1 for
   odd N, D_2(N)/2 otherwise; rule 150: 0 if 3 does not divide N, 1 if N is odd, D_2(N) otherwise; D_2(n) the largest
   power of 2 dividing n); for rule 90 and odd N from 3 to 41, Pi_N against Pi*_N = 2^sord_N(2) - 1 (equal "for most
   N; the first exception occurs for N = 37, in which case Pi_37 = Pi*_37/3"); and for even N from 4 to 30, Pi_N
   against 2 Pi_(N/2) ("When N is even, Pi_N = 2 Pi_(N/2)").

Controls (controls_passed counts those that behave as stated): Fig. 2's worked example (one step of rule 90 on its
printed 21 sites gives its printed 19); the integer step against a cell-by-cell step for all 256 rules on seed-drawn
rows; the numbering against the printed Boolean forms of rules 90, 54 and 150, and a reversed bit order (a planted
fault) giving a legal set other than Fig. 3's; rule 90's rows against Pascal's triangle mod 2 by Lucas's theorem and
rule 150's rows against (1 + x + x^2)^t mod 2 by the Frobenius product, t < 1,024; the dimension estimator on Pascal's
triangle built by Lucas's theorem (log2 3) and on a seed-drawn random cone (about 2, not self-similar); the homogeneity
detector on constructed cones (a checkerboard and all 1s are uniform, Pascal's triangle is not); and rule 30 put among
the rules under test (a planted fault) makes the test fail.

What it cannot check: the infinite-time limit and the exact self-similarity the paper derives; a finite run measures
the growth of counts over 4,096 steps, which the tolerance and the two doublings bound.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 ca/wolfram83.py
"""

import hashlib
import itertools
import json
import math
import os
import random
import re
import sys

T_LOG = 12
MARGIN = 8
MIN_INTERIOR = 16
P_MAX, Q_MAX = 4, 2
TOL = 0.02
BOUNDED_WIDTH = 8
TARGETS = (("log2 3", math.log2(3)), ("log2(1+sqrt 5)", math.log2(1 + math.sqrt(5))))
LEGAL_PRINTED = (0, 4, 18, 22, 32, 36, 50, 54, 72, 76, 90, 94, 104, 108, 122, 126, 128, 132, 146, 150, 160, 164, 178,
                 182, 200, 204, 218, 222, 232, 236, 250, 254)
COMPLEX_PRINTED = (18, 22, 90, 122, 126, 146, 150, 182)
NAMED_P604 = {"dies": (0, 160), "unchanged": (4, 36), "uniform": (50, 122), "complex": (18, 22, 90)}
FIG2 = ("010110110101011100010", "0011011000001011010")
PI_PRINTED = (1, 1, 3, 2, 7, 1, 7, 6, 31, 4, 63, 14, 15, 1, 15, 14, 511, 12, 63, 62, 2047, 8, 1023, 126, 511, 28, 16383,
              30)                                             # N = 3 to 30, as printed on p. 627
CHI_PRINTED = (3, 5, 11)                                      # chi(1), chi(2), chi(3), as printed on p. 614
SEEDS = ("1", "11", "101", "111", "1001", "1011", "1101", "1111")
RING_N = range(3, 31)
ODD_N_STAR = range(3, 42, 2)
TEST = ("Refuted if, run 4,096 steps from a single site with value 1, one of the 32 legal elementary rules (the "
        "paper's Fig. 3) neither tends to a homogeneous state (dies, stays unchanged, or from step 2,048 its interior, "
        "8 sites in from its outermost 1s, is periodic in space with period ≤ 4 and in time with period ≤ 2) nor is "
        "self-similar with dimension within 0.02 of log2 3 or log2(1+√5) at both of the last two doublings (log2 of the "
        "growth over the first 2^k steps of the count of the rarer value's sites between the outermost 1s); or one "
        "dimension never occurs.")
OUTPUTS = ("legal", "dies_unchanged", "uniform", "selfsimilar", "neither", "dims_found", "d_150", "d_max_dev",
           "literal", "box", "eq32", "chi", "classes_p604", "complex_single", "seeds", "quiescent", "quiescent_other",
           "pi_list", "pi_90_150", "upsilon", "pi_star", "pi_even", "conditions_met", "conditions_total", "test_passed",
           "controls_passed", "controls_total")
LIMIT = 200


class Refused(Exception):
    pass


# ----------------------------------------------------------------------------------------------- rules and steps
def rule_bit(rule, l, c, r):
    """The paper's Fig. 1 numbering: the new value is bit 4l + 2c + r of the rule number."""
    return (rule >> (4 * l + 2 * c + r)) & 1


def is_legal(rule, bit=rule_bit):
    return (bit(rule, 0, 0, 0) == 0 and bit(rule, 1, 0, 0) == bit(rule, 0, 0, 1)
            and bit(rule, 1, 1, 0) == bit(rule, 0, 1, 1))


def legal_rules(bit=rule_bit):
    return tuple(r for r in range(256) if is_legal(r, bit))


def step(row, rule, mask):
    """One step on a line held as an integer, bit i for site i; sites beyond the mask are 0."""
    left = (row << 1) & mask           # bit i holds the old value of site i - 1
    right = row >> 1                   # bit i holds the old value of site i + 1
    nl, nc, nr = ~left & mask, ~row & mask, ~right & mask
    out = 0
    for k in range(8):
        if rule >> k & 1:
            out |= (left if k & 4 else nl) & (row if k & 2 else nc) & (right if k & 1 else nr)
    return out


def step_cells(cells, rule):
    """The same step, site by site, on a list of 0s and 1s with 0s beyond its ends."""
    n = len(cells)
    get = lambda i: cells[i] if 0 <= i < n else 0
    return [rule_bit(rule, get(i - 1), get(i), get(i + 1)) for i in range(n)]


def evolve(rule, seed="1", steps=1 << T_LOG):
    """Rows 0 to steps - 1 from the seed (its first site at x = 0) on a line of 0s. Bit offset + x is site x."""
    offset = steps + 2
    width = 2 * offset + len(seed) + 2
    mask = (1 << width) - 1
    row = 0
    for i, ch in enumerate(seed):
        if ch == "1":
            row |= 1 << (offset + i)
    rows = [row]
    for _ in range(steps - 1):
        row = step(row, rule, mask)
        rows.append(row)
    return rows, offset


def edges(row):
    return (row & -row).bit_length() - 1, row.bit_length() - 1


# ----------------------------------------------------------------------------------------------- classification
def interior(row):
    lo, hi = edges(row)
    lo, hi = lo + MARGIN, hi - MARGIN
    if hi - lo + 1 < MIN_INTERIOR:
        return None
    return lo, hi


def span_mask(lo, hi):
    return ((1 << (hi - lo + 1)) - 1) << lo if hi >= lo else 0


def uniform(rows, temporal=True):
    """(p, q) if from row len/2 on every row's interior has one spatial period p <= P_MAX (and, if temporal, one
    temporal period q <= Q_MAX); None otherwise."""
    start = len(rows) // 2
    ints = []
    for t in range(start, len(rows)):
        if rows[t] == 0:
            return None
        iv = interior(rows[t])
        if iv is None:
            return None
        ints.append(iv)
    p_found = None
    for p in range(1, P_MAX + 1):
        if all(((rows[t] >> p) ^ rows[t]) & span_mask(lo, hi - p) == 0
               for t, (lo, hi) in zip(range(start, len(rows)), ints)):
            p_found = p
            break
    if p_found is None:
        return None
    if not temporal:
        return p_found, None
    for q in range(1, Q_MAX + 1):
        ok = True
        for i in range(q, len(ints)):
            lo = max(ints[i][0], ints[i - q][0])
            hi = min(ints[i][1], ints[i - q][1])
            t = start + i
            if (rows[t] ^ rows[t - q]) & span_mask(lo, hi):
                ok = False
                break
        if ok:
            return p_found, q
    return None


def counts(rows):
    """Per row: the number of 1s and the number of 0s between its outermost 1s."""
    ones, zeros = [], []
    for r in rows:
        if r == 0:
            ones.append(0)
            zeros.append(0)
            continue
        lo, hi = edges(r)
        c = r.bit_count()
        ones.append(c)
        zeros.append(hi - lo + 1 - c)
    return ones, zeros


def growth(series, k_max):
    """S(k) = sum of the series over rows 0 to 2^k - 1, k = 0 .. k_max."""
    acc = list(itertools.accumulate(series))
    return [acc[(1 << k) - 1] for k in range(k_max + 1)]


def dims(rows, k_max):
    """D(k_max), D(k_max - 1) for the rarer value and for the nonzero sites; the rarer value."""
    ones, zeros = counts(rows)
    s1, s0 = growth(ones, k_max), growth(zeros, k_max)
    v, s = (1, s1) if s1[k_max] <= s0[k_max] else (0, s0)
    d = lambda S, k: math.log2(S[k] / S[k - 1]) if S[k - 1] > 0 and S[k] > 0 else float("nan")
    return {"rarer": v, "d_last": d(s, k_max), "d_prev": d(s, k_max - 1), "nonzero_last": d(s1, k_max),
            "nonzero_prev": d(s1, k_max - 1), "s_rarer": s[k_max], "s_ones": s1[k_max], "s_zeros": s0[k_max]}


def target_of(dm):
    for name, d in TARGETS:
        if abs(dm["d_last"] - d) <= TOL and abs(dm["d_prev"] - d) <= TOL:
            return name
    return None


def classify(rows, k_max, legal=True):
    """The classes of rules 3 and 4 (legal = True) or the beside classes for any quiescent rule (legal = False)."""
    if any(r == 0 for r in rows[1:]):
        return {"class": "dies"}
    if legal and all(r == rows[0] for r in rows):
        return {"class": "unchanged"}
    if not legal:
        start = len(rows) // 2
        if all(edges(r)[1] - edges(r)[0] + 1 <= BOUNDED_WIDTH for r in rows[start:]):
            return {"class": "bounded"}
    u = uniform(rows, temporal=legal)
    dm = dims(rows, k_max)
    if u is not None:
        return {"class": "uniform", "p": u[0], "q": u[1], **dm}
    name = target_of(dm)
    if name is not None:
        return {"class": "self-similar", "target": name, **dm}
    return {"class": "neither", **dm}


def decide(classes):
    """The test on a {rule: classification} map: (conditions, the rules that are neither)."""
    neither = sorted(r for r, c in classes.items() if c["class"] == "neither")
    found = {name: sorted(r for r, c in classes.items() if c.get("target") == name) for name, _ in TARGETS}
    cond = {"every legal rule tends to a homogeneous state or is self-similar with dimension log2 3 or "
            "log2(1+sqrt 5)": not neither}
    for name, _ in TARGETS:
        cond[f"dimension {name} occurs"] = bool(found[name])
    return cond, neither, found


# ----------------------------------------------------------------------------------------------- beside the test
def box_dims(rows, value, j_lo=3, j_hi=8):
    """Least-squares box-counting dimension of the sites with the given value between the outermost 1s, square boxes
    of 2^j_lo to 2^j_hi sites a side (numpy)."""
    import numpy as np
    unit = 1 << j_hi
    width = max(r.bit_length() for r in rows) + 2
    width = (width + unit - 1) // unit * unit
    height = len(rows)
    if height % unit:
        raise AssertionError("the rows must be a multiple of the largest box")
    grid = np.zeros((height, width), dtype=bool)
    for t, r in enumerate(rows):
        if r == 0:
            continue
        lo, hi = edges(r)
        bits = r if value == 1 else (~r) & span_mask(lo, hi)
        grid[t] = np.unpackbits(np.frombuffer(bits.to_bytes(width // 8, "little"), dtype=np.uint8),
                                bitorder="little").astype(bool)
    js, ns = [], []
    for j in range(j_lo, j_hi + 1):
        a = 1 << j
        n = int(grid.reshape(height // a, a, width // a, a).any(axis=(1, 3)).sum())
        js.append(j)
        ns.append(math.log2(n))
    mj, mn = sum(js) / len(js), sum(ns) / len(ns)
    slope = sum((x - mj) * (y - mn) for x, y in zip(js, ns)) / sum((x - mj) ** 2 for x in js)
    return -slope


def runs_of_ones(t):
    return [len(s) for s in bin(t)[2:].split("0") if s]


def chi_printed(j):
    c = 3
    for i in range(2, j + 1):
        c = (2 * i + 1) * c if i % 2 else (2 * i - 1) * c
    return c


def chi_examples(j):
    c = 3
    for i in range(2, j + 1):
        c = 2 * c + 1 if i % 2 else 2 * c - 1
    return c


def ring_step(x, rule, n):
    full = (1 << n) - 1
    left = ((x << 1) | (x >> (n - 1))) & full
    right = (x >> 1) | ((x & 1) << (n - 1))
    nl, nc, nr = ~left & full, ~x & full, ~right & full
    out = 0
    for k in range(8):
        if rule >> k & 1:
            out |= (left if k & 4 else nl) & (x if k & 2 else nc) & (right if k & 1 else nr)
    return out


def orbit(rule, n, start=1, limit=1 << 22):
    """(period, transient) of the ring of n sites from the given state."""
    seen = {start: 0}
    x, t = start, 0
    while t < limit:
        x = ring_step(x, rule, n)
        t += 1
        if x in seen:
            return t - seen[x], seen[x]
        seen[x] = t
    raise AssertionError(f"rule {rule}, N = {n}: no cycle within {limit} steps")


def d2(n):
    return n & -n


def sord(n):
    j, v = 1, 2 % n
    while v not in (1, n - 1):
        j, v = j + 1, v * 2 % n
    return j


def upsilon_printed(rule, n):
    if rule == 90:
        return 1 if n % 2 else d2(n) // 2
    if n % 3:
        return 0
    return 1 if n % 2 else d2(n)


def pascal_rows(steps, offset):
    """Pascal's triangle mod 2 by Lucas's theorem, as rule 90's rows from one site: C(t, k) odd at x = 2k - t."""
    rows = []
    for t in range(steps):
        row, k = 0, t
        while True:                                   # every k whose binary digits lie inside t's
            row |= 1 << (offset + 2 * k - t)
            if k == 0:
                break
            k = (k - 1) & t
        rows.append(row)
    return rows


def frobenius_rows(steps, offset):
    """(1 + x + x^2)^t mod 2 as the product over t's binary digits of 1 + x^(2^j) + x^(2^(j+1)), placed as rule 150's
    rows from one site (coefficient i at site i - t)."""
    rows = []
    for t in range(steps):
        p, j = 1, 0
        while t >> j:
            if t >> j & 1:
                m = 1 << j
                p = p ^ (p << m) ^ (p << (2 * m))
            j += 1
        rows.append(p << (offset - t))
    return rows


def cone_rows(steps, offset, fill):
    rows = []
    for t in range(steps):
        row = 0
        for x in range(-t, t + 1):
            if fill(t, x):
                row |= 1 << (offset + x)
        rows.append(row)
    return rows


def random_cone(steps, offset, rng):
    rows = []
    for t in range(steps):
        bits = rng.getrandbits(2 * t + 1) | 1 | (1 << (2 * t))     # the edges kept 1, as a growing rule's are
        rows.append(bits << (offset - t))
    return rows


# ----------------------------------------------------------------------------------------------- controls
def seeded(seed, label):
    return random.Random(int.from_bytes(hashlib.sha256(f"{seed}/{label}".encode()).digest(), "big"))


def controls_run(seed, classes):
    ctl, info = {}, {}
    top, bottom = FIG2
    cells = [int(c) for c in top]
    stepped = step_cells(cells, 90)[1:-1]
    ctl["Fig. 2: one step of rule 90 on the printed 21 sites gives the printed 19"] = (
        "".join(map(str, stepped)) == bottom)

    rng = seeded(seed, "wolfram83/step")
    width = 200
    mask = (1 << width) - 1
    same = True
    for rule in range(256):
        for _ in range(4):
            cells = [0] * 70 + [rng.getrandbits(1) for _ in range(60)] + [0] * 70
            row = sum(b << i for i, b in enumerate(cells))
            for _ in range(5):
                cells = step_cells(cells, rule)
                row = step(row, rule, mask)
                if row != sum(b << i for i, b in enumerate(cells)):
                    same = False
    ctl["the integer step equals a cell-by-cell step for all 256 rules on 1,024 seed-drawn rows"] = same

    forms = {90: lambda l, c, r: l ^ r, 54: lambda l, c, r: c ^ (l | r), 150: lambda l, c, r: l ^ c ^ r}
    ok = all(rule_bit(rule, l, c, r) == f(l, c, r) for rule, f in forms.items()
             for l, c, r in itertools.product((0, 1), repeat=3))
    reversed_bit = lambda rule, l, c, r: (rule >> (7 - (4 * l + 2 * c + r))) & 1
    ctl["numbering: rules 90, 54 and 150 as their printed Boolean forms; the legal set is Fig. 3's, and a reversed "
        "bit order (planted) is not"] = (ok and legal_rules() == LEGAL_PRINTED
                                          and legal_rules(reversed_bit) != LEGAL_PRINTED)

    off = 1024 + 2
    r90, _ = evolve(90, "1", 1024)
    r150, _ = evolve(150, "1", 1024)
    ctl["rule 90's rows are Pascal's triangle mod 2 (Lucas) and rule 150's are (1+x+x^2)^t mod 2 (Frobenius), "
        "t < 1,024"] = r90 == pascal_rows(1024, off) and r150 == frobenius_rows(1024, off)

    steps = 1 << T_LOG
    off = steps + 2
    dp = dims(pascal_rows(steps, off), T_LOG)
    dr = dims(random_cone(steps, off, seeded(seed, "wolfram83/random-cone")), T_LOG)
    info["pascal"] = dp
    info["random_cone"] = dr
    ctl["the estimator gives log2 3 on Pascal's triangle (Lucas) and about 2, not self-similar, on a random cone"] = (
        abs(dp["d_last"] - math.log2(3)) < 1e-9 and abs(dp["d_prev"] - math.log2(3)) < 1e-9
        and abs(dr["d_last"] - 2) < 0.05 and target_of(dr) is None)

    small = 512
    o = small + 2
    checker = cone_rows(small, o, lambda t, x: (x + t) % 2 == 0)
    ones = cone_rows(small, o, lambda t, x: True)
    ctl["the homogeneity detector: a checkerboard cone and a cone of 1s are uniform, Pascal's triangle is not"] = (
        uniform(checker) == (2, 2) and uniform(ones) == (1, 1) and uniform(pascal_rows(small, o)) is None)

    with_30 = dict(classes)
    rows30, _ = evolve(30, "1", steps)
    with_30[30] = classify(rows30, T_LOG)
    cond30, _, _ = decide(with_30)
    info["rule_30_planted"] = {k: v for k, v in with_30[30].items()}
    ctl["rule 30 put among the rules under test (planted) makes the test fail"] = not all(cond30.values())
    return ctl, info


# ----------------------------------------------------------------------------------------------- the run
def fmt(x, n=3):
    return f"{x:.{n}f}"


def joined(xs, limit=None):
    xs = list(xs)
    if limit is not None and len(xs) > limit:
        return ", ".join(map(str, xs[:limit])) + f" and {len(xs) - limit} more"
    return ", ".join(map(str, xs)) if xs else "none"


def run(seed, results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    legal = legal_rules()
    if len(legal) != 32 or legal != LEGAL_PRINTED:
        raise Refused("the legal rules by the paper's conditions are not the 32 of its Fig. 3")
    steps = 1 << T_LOG

    classes, rows_kept = {}, {}
    for rule in legal:
        rows, off = evolve(rule, "1", steps)
        for t, r in enumerate(rows):
            if r and (edges(r)[0] < off - t or edges(r)[1] > off + t):
                raise AssertionError(f"rule {rule} left its light cone at step {t}")
        classes[rule] = classify(rows, T_LOG)
        if classes[rule]["class"] == "self-similar" or rule in COMPLEX_PRINTED or rule in (90, 150):
            rows_kept[rule] = rows
    ctl, ctl_info = controls_run(seed, classes)
    cond, neither, found = decide(classes)

    by = lambda name: [r for r in legal if classes[r]["class"] == name]
    selfsim = by("self-similar")
    devs = []
    for r in selfsim:
        d = dict(TARGETS)[classes[r]["target"]]
        devs += [abs(classes[r]["d_last"] - d), abs(classes[r]["d_prev"] - d)]
    growing = [r for r in legal if classes[r]["class"] in ("uniform", "self-similar", "neither")]
    literal_diff = [r for r in growing if classes[r]["class"] != "uniform"
                    and abs(classes[r]["nonzero_last"] - classes[r]["d_last"]) > TOL]

    box = {}
    for r in selfsim:
        box[r] = {"rarer": box_dims(rows_kept[r], classes[r]["rarer"]), "nonzero": box_dims(rows_kept[r], 1)}
    box_rarer = [box[r]["rarer"] for r in selfsim]
    box_dev = max((abs(box[r]["rarer"] - dict(TARGETS)[classes[r]["target"]]) for r in selfsim), default=float("nan"))
    box_literal = [r for r in selfsim if abs(box[r]["nonzero"] - box[r]["rarer"]) > 0.1]

    n90 = [r.bit_count() for r in rows_kept[90]]
    eq32_bad = [t for t in range(steps) if n90[t] != 1 << bin(t).count("1")]
    n150 = [r.bit_count() for r in rows_kept[150]]
    prod = lambda f, t: math.prod(f(j) for j in runs_of_ones(t))
    chi_a = sum(n150[t] == prod(chi_printed, t) for t in range(steps))
    chi_b = sum(n150[t] == prod(chi_examples, t) for t in range(steps))

    no_spread = [r for r in legal if rule_bit(r, 1, 0, 0) == 0 and rule_bit(r, 0, 0, 1) == 0]
    erased_or_kept = [r for r in legal if classes[r]["class"] in ("dies", "unchanged")]
    named_ok = {k: all(classes[r]["class"] == (k if k != "complex" else "self-similar") for r in v)
                for k, v in NAMED_P604.items()}
    complex_cls = {r: classes[r]["class"] for r in COMPLEX_PRINTED}

    seeds = {}
    for r in COMPLEX_PRINTED:
        for s in SEEDS:
            rows, _ = evolve(r, s, steps)
            c = classify(rows, T_LOG)
            seeds[f"{r}/{s}"] = c
    others = {k: c for k, c in seeds.items() if not k.startswith("150/")}
    seed_dims = [c["d_last"] for c in others.values() if c["class"] == "self-similar"]
    seed_targets = sorted({c["target"] for c in others.values() if c["class"] == "self-similar"})
    seed_neither = sorted(k for k, c in others.items() if c["class"] == "neither")
    seed_uniform = sorted(k for k, c in others.items() if c["class"] == "uniform")
    seed_150 = sum(c.get("target") == TARGETS[1][0] for k, c in seeds.items() if k.startswith("150/"))

    quiescent = {}
    for r in range(0, 256, 2):
        rows, _ = evolve(r, "1", steps)
        quiescent[r] = classify(rows, T_LOG, legal=False)
    qcount = {}
    for c in quiescent.values():
        key = c["class"] if c["class"] != "self-similar" else f"self-similar {c['target']}"
        qcount[key] = qcount.get(key, 0) + 1
    q_other = sorted(r for r, c in quiescent.items() if c["class"] == "neither")
    q_other_illegal = [r for r in q_other if r not in legal]

    rings = {}
    for rule in (90, 150):
        for n in RING_N:
            rings[(rule, n)] = orbit(rule, n)
    pi90 = [rings[(90, n)][0] for n in RING_N]
    pi150 = [rings[(150, n)][0] for n in RING_N]
    pi90_ok = sum(a == b for a, b in zip(pi90, PI_PRINTED))
    pi150_ok = sum(a == b for a, b in zip(pi150, PI_PRINTED))
    differ = [n for n, a, b in zip(RING_N, pi90, pi150) if a != b]
    ups_ok = {rule: [n for n in RING_N if rings[(rule, n)][1] == upsilon_printed(rule, n)] for rule in (90, 150)}
    ups_bad = {rule: [n for n in RING_N if rings[(rule, n)][1] != upsilon_printed(rule, n)] for rule in (90, 150)}
    star = {}
    for n in ODD_N_STAR:
        pi_n = orbit(90, n)[0]
        ps = (1 << sord(n)) - 1
        star[n] = {"pi": pi_n, "pi_star": ps, "divides": ps % pi_n == 0}
    star_exceptions = [n for n, v in star.items() if v["pi"] != v["pi_star"]]
    star_37 = star[37]["pi"] * 3 == star[37]["pi_star"]
    even_bad = [n for n in range(4, 31, 2) if orbit(90, n)[0] != 2 * orbit(90, n // 2)[0]]

    yn = lambda b: "yes" if b else "NO"
    t1, t2 = TARGETS[0][0], TARGETS[1][0]

    values = {
        "legal": f"{len(legal)} legal rules by the paper's conditions, the 32 of its Fig. 3: {yn(legal == LEGAL_PRINTED)}",
        "dies_unchanged": f"dies: {joined(by('dies'))}; unchanged: {joined(by('unchanged'))}",
        "uniform": "uniform (p, q): " + joined(f"{r} ({classes[r]['p']},{classes[r]['q']})" for r in by("uniform")),
        "selfsimilar": "self-similar, D(12): " + joined(f"{r} {fmt(classes[r]['d_last'])}" for r in selfsim),
        "neither": "neither homogeneous nor self-similar: " + joined(neither),
        "dims_found": f"{t1}: {joined(found[t1])}; {t2}: {joined(found[t2])}",
        "d_150": round(classes[150]["d_last"], 9) if "d_last" in classes[150] else -1,
        "d_max_dev": round(max(devs), 9) if devs else -1,
        "literal": ("D of the nonzero sites (the paper's covering of all nonzero sites) differs from the rarer value's at "
                    + (joined(f"{r} ({fmt(classes[r]['nonzero_last'])})" for r in literal_diff) if literal_diff
                       else "no rule")),
        "box": (f"box-count D, boxes 8-256, rarer value: {fmt(min(box_rarer))} to {fmt(max(box_rarer))} "
                f"(largest gap to the target {fmt(box_dev)}); nonzero sites differ at " + joined(
                    f"{r} ({fmt(box[r]['nonzero'])})" for r in box_literal)) if box else "none self-similar",
        "eq32": ("rule 90 has 2^#1(t) sites with value 1 at every step t < 4,096 (eq. 3.2): "
                 + ("yes" if not eq32_bad else f"NO, first at t = {eq32_bad[0]}")),
        "chi": (f"rule 150's count as the product of chi: printed recurrence (chi(2) = {chi_printed(2)}) at {chi_a} of "
                f"{steps} steps; 2chi(j-1)+-1 (chi(2) = {chi_examples(2)}, chi(3) = {chi_examples(3)}) at {chi_b}"),
        "classes_p604": (f"100->0 and 001->0 exactly the rules that die or stay: {yn(no_spread == erased_or_kept)}; "
                         "named examples as printed: " + ", ".join(f"{k} {yn(v)}" for k, v in named_ok.items())),
        "complex_single": "Fig. 16's complex rules from one site: " + "; ".join(
            f"{c} {joined(r for r in COMPLEX_PRINTED if complex_cls[r] == c)}" for c in sorted(set(complex_cls.values()))),
        "seeds": (f"seeds of width 1-4, complex rules but 150: self-similar D(12) {fmt(min(seed_dims))} to "
                  f"{fmt(max(seed_dims))} ({joined(seed_targets)}), uniform {len(seed_uniform)}, neither "
                  f"{len(seed_neither)} of {len(others)}; rule 150: {seed_150} of {len(SEEDS)} at {TARGETS[1][0]}"
                  ) if seed_dims else "no self-similar seed",
        "quiescent": "128 quiescent rules from one site: " + ", ".join(f"{k} {v}" for k, v in sorted(qcount.items())),
        "quiescent_other": f"neither, {len(q_other_illegal)} illegal: " + joined(q_other_illegal, 24),
        "pi_list": f"Pi_N for N = 3-30 as printed: rule 90 {pi90_ok} of 28, rule 150 {pi150_ok} of 28",
        "pi_90_150": "Pi_N of rules 90 and 150 differ at N = " + joined(differ),
        "upsilon": (f"Upsilon_N as printed: rule 90 {len(ups_ok[90])} of 28 (not at {joined(ups_bad[90], 8)}), "
                    f"rule 150 {len(ups_ok[150])} of 28 (not at {joined(ups_bad[150], 8)})"),
        "pi_star": (f"rule 90, odd N 3-41: Pi_N divides Pi*_N: {yn(all(v['divides'] for v in star.values()))}; "
                    f"differs at N = {joined(star_exceptions)}; Pi_37 = Pi*_37/3: {yn(star_37)}"),
        "pi_even": "rule 90, even N 4-30: Pi_N = 2 Pi_(N/2) except at N = " + joined(even_bad),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for key, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")
        if isinstance(v, float) and not math.isfinite(v):
            raise AssertionError(f"{key}: not finite")
    detail = {"classes": {str(r): c for r, c in classes.items()}, "conditions": cond, "controls": ctl,
              "control_detail": ctl_info, "box": {str(r): v for r, v in box.items()}, "eq32_bad": eq32_bad[:50],
              "chi": {"printed_matches": chi_a, "examples_matches": chi_b,
                      "printed": [chi_printed(j) for j in range(1, 8)], "examples": [chi_examples(j) for j in range(1, 8)]},
              "seeds": seeds, "quiescent": {str(r): c for r, c in quiescent.items()}, "quiescent_neither": q_other,
              "rings": {f"{rule}/{n}": {"period": p, "transient": u, "upsilon_printed": upsilon_printed(rule, n)}
                        for (rule, n), (p, u) in rings.items()},
              "pi_printed": dict(zip(RING_N, PI_PRINTED)), "pi_star": {str(n): v for n, v in star.items()},
              "pi_even_exceptions": even_bad, "seed_neither": seed_neither, "seed_uniform": seed_uniform,
              "test": TEST}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"wolfram83: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
