#!/usr/bin/env python3
"""Rosowski's commutative matrix algorithms: the n x 3 by 3 x 3 product in 6n + 3 multiplications, the 3 x 3 product
in 21, and the l x n by n x m product for odd n, built as the paper prints them, expanded exactly and counted.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:8f7177fa0b6d99da) is from A. Rosowski,
"Fast Commutative Matrix Algorithm" (arXiv:1904.07683, v2 of 27 July 2020; later in the Journal of Symbolic
Computation), its abstract: "We show that the product of an nx3 matrix and a 3x3 matrix over a commutative ring can
be computed using 6n+3 multiplications. For two 3x3 matrices this gives us an algorithm using 21 multiplications.
This is an improvement with respect to Makarov's algorithm using 22 multiplications[13]. We generalize our result for
nx3 and 3x3 matrices and present an algorithm for computing the product of an lxn matrix and an nxm matrix over a
commutative ring for odd n using n(lm+l+m-1)/2 multiplications if m is odd and using (n(lm+l+m-1)+l-1)/2
multiplications if m is even." The test, as registered: see TEST below. No data of record: the claim is a
construction, so the receipt is a reproduction. Makarov's 22 is not checked (his paper is not read here).

The paper's constructions, read from its TeX (publication.tex in arXiv's source of v2), numbered as its LaTeX numbers
them (one counter each for theorems, corollaries and algorithms):
- Algorithm 1: for a row a = (a1, a2, a3) and a 3 x 3 matrix B, the nine products p1 = (a2 + b12)(a1 + b21),
  p2 = (a3 + b13)(a1 + b31), p3 = (a3 + b23)(a2 + b32), p4 = a1(b11 - b12 - b13 - a2 - a3),
  p5 = a2(b22 - b21 - b23 - a1 - a3), p6 = a3(b33 - b31 - b32 - a1 - a2), p7 = b12 b21, p8 = b13 b31,
  p9 = b23 b32, and aB = (p4 + p1 + p2 - p7 - p8, p5 + p1 + p3 - p7 - p9, p6 + p2 + p3 - p8 - p9).
- Theorem 1: an n x 3 by 3 x 3 product in 6n + 3, Algorithm 1 for each row with p7, p8 and p9 computed once.
- Corollary 1: the 3 x 3 case written out, p1 to p18 for the three rows and p19 to p21 for B's three products.
- Theorem 2 (n even, l, m >= 1): c_i1 = sum_k a_i(2k-1)(b_(2k-1)1 + a_i(2k)) + sum_k a_i(2k)(b_(2k)1 - a_i(2k-1)),
  and for j >= 2, c_ij = sum_k (a_i(2k-1) + b_(2k)j)(a_i(2k) + b_(2k-1)1 + b_(2k-1)j) -
  sum_k a_i(2k-1)(b_(2k-1)1 + a_i(2k)) - sum_k b_(2k)j(b_(2k-1)1 + b_(2k-1)j), k from 1 to n/2: n(lm + l + m - 1)/2.
- Theorem 3 (n >= 3 odd, l >= 1, m >= 3): A = [A1 A2] and B = [B1; B2] with A1 the first three columns and B1 the
  first three rows; A2 B2 by Theorem 2 (nothing when n = 3), A1 B1 by its Case 1 (m odd: c_i1, c_i2, c_i3, then
  c_ij and c_i(j+1) for j = 4, 6, ..., m - 1) or Case 2 (m even: c_i1 to c_i4, then the same pairs for
  j = 5, 7, ..., m - 1), each formula exactly as printed.
While reading, Case 2's c_i4 was expanded by hand (it gives a_i1 b14 + a_i2 b24 + a_i3 b34); nothing else was
computed before this module's rules were committed.

1. Polynomials. Every entry of A and B is a variable; a factor is a linear form in them with integer coefficients;
   an algorithm is, for each entry c_ij, a list of (integer, factor, factor). Its expansion is computed exactly as a
   polynomial over the integers in commuting variables (a product x y kept once as the unordered pair); an algorithm
   holds when every entry's expansion is sum_k a_ik b_kj exactly, every coefficient an integer (no division).
2. Multiplications: the distinct products of two non-constant factors the algorithm uses, a product counted once
   however often its entries use it. Two products are the same when their factors are, up to order and to the sign
   of each factor (each factor is normalised to a leading positive coefficient, the sign moved to the integer).
3. The test's four conditions: (1) Theorem 1, for every n from 1 to 10, holds with at most 6n + 3 multiplications;
   (2) Corollary 1's printed scheme holds with at most 21; (3) Theorem 3 holds for every odd n from 3 to 9, l from 1
   to 5 and odd m from 3 to 9 with at most n(lm + l + m - 1)/2; (4) the same for even m from 4 to 8 with at most
   (n(lm + l + m - 1) + l - 1)/2. test_passed is 1 if all four hold.
4. Beside, none of it counted: Theorem 2 alone for even n from 2 to 10, l from 1 to 5, m from 1 to 7 (no division
   used, n(lm + l + m - 1)/2); the counts against the classical lmn and against Waksman's and Islam's
   (n - 1)(lm + l + m - 1)/2 + lm, which the paper says its odd-n algorithm beats; and the paper's non-bilinear
   Theorems 4 and 5 (n even and odd, over a ring with an involution, the paper's (AB)^T = B^T A^T): their formulas
   evaluated with seed-drawn 3 x 3 integer matrices as entries and transposition as the involution, against the
   block product, for n from 2 to 7, and their products counted up to transposition (X Y and Y^T X^T counted once,
   as the paper's proof reuses them) against n(n^2 + 3n + 1)/2 and n(n^2 + 3n + 2)/2.

Controls (controls_passed counts those that behave as stated; the run stops if any fails): every algorithm of the
test also evaluated numerically at three seed-drawn integer points (entries from -10^6 to 10^6) and compared with
the matrix product, independently of the expansion; Strassen's 2 x 2 algorithm holds under rule 1 with 7
multiplications; the classical product holds with lmn; three planted faults are caught (Corollary 1's p4 with
+ a12 for - a12; Theorem 3's c_ij with b_1j for b_1(j+1) in one factor; the count with sharing switched off, which
must exceed 21 for Corollary 1); and Corollary 1's formulas fail when the entries are seed-drawn 3 x 3 integer
matrices, which do not commute (the algorithm is commutative, not bilinear).

What it cannot check: the theorems for sizes beyond these ranges, which rest on the paper's index patterns (the
check expands every formula at every size it runs, so a pattern that broke at a larger size would not be seen);
Makarov's 22 or any claim that 21 is the least; the approximate non-bilinear 5 x 5 algorithm in 89, not run.

Writes results/outputs.json and results/detail.json. Run with: python3 mm/rosowski.py
"""

import hashlib
import json
import os
import re
import sys

THEOREM1_N = tuple(range(1, 11))
THEOREM3_N = (3, 5, 7, 9)
THEOREM3_L = tuple(range(1, 6))
THEOREM3_M_ODD = (3, 5, 7, 9)
THEOREM3_M_EVEN = (4, 6, 8)
THEOREM2_N = (2, 4, 6, 8, 10)
THEOREM2_L = tuple(range(1, 6))
THEOREM2_M = tuple(range(1, 8))
NONBILINEAR_N = tuple(range(2, 8))
BLOCK = 3
POINTS = 3
LIMIT = 200
TEST = ("Refuted if, expanded exactly as polynomials over the integers, the paper's algorithms do not give AB or use "
        "more distinct products of two non-constant factors than it states: Algorithm 1 row by row, B's three "
        "products shared (Theorem 1), for n × 3 by 3 × 3 with n from 1 to 10, at most 6n + 3; Corollary 1's printed "
        "3 × 3 scheme, 21; and Theorem 3 (A1B1 by its Case 1 or 2, A2B2 by Theorem 2) for odd n from 3 to 9, l from "
        "1 to 5 and m from 3 to 9, at most n(lm + l + m − 1)/2 for odd m, (n(lm + l + m − 1) + l − 1)/2 for even "
        "m.")
OUTPUTS = ("theorem1", "corollary1", "theorem3_odd_m", "theorem3_even_m", "theorem3_counts", "theorem2",
           "against_waksman", "nonbilinear", "nonbilinear_counts", "conditions_met", "conditions_total",
           "test_passed", "controls_passed", "controls_total")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- randomness

class Stream:
    def __init__(self, seed, label):
        self.seed, self.label, self.n, self.buf = seed, label, 0, []

    def u(self):
        if not self.buf:
            h = hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
            self.n += 1
            self.buf = [int.from_bytes(h[i:i + 8], "big") for i in range(24, -1, -8)]
        return self.buf.pop()

    def int_in(self, lo, hi):
        return lo + self.u() % (hi - lo + 1)


# ---------------------------------------------------------------- linear forms and programs (rule 1)

def a(i, j):
    return ("a", i, j)


def b(i, j):
    return ("b", i, j)


def L(*terms):
    """A linear form from (coefficient, variable) pairs or bare variables (coefficient 1)."""
    out = {}
    for t in terms:
        c, v = (1, t) if isinstance(t[0], str) else t
        out[v] = out.get(v, 0) + c
    return {v: c for v, c in out.items() if c}


def neg(v):
    return (-1, v)


def expand(program):
    """{entry: {sorted pair of variables: integer}}."""
    out = {}
    for entry, terms in program.items():
        poly = {}
        for c, f, g in terms:
            for u, cu in f.items():
                for v, cv in g.items():
                    key = (u, v) if u <= v else (v, u)
                    poly[key] = poly.get(key, 0) + c * cu * cv
        out[entry] = {k: x for k, x in poly.items() if x}
    return out


def target(l, n, m):
    return {(i, j): {(a(i, k), b(k, j)): 1 for k in range(1, n + 1)} for i in range(1, l + 1) for j in range(1, m + 1)}


def holds(program, l, n, m):
    if set(program) != {(i, j) for i in range(1, l + 1) for j in range(1, m + 1)}:
        return False
    if not all(isinstance(c, int) and all(isinstance(x, int) for x in f.values()) and all(
            isinstance(x, int) for x in g.values()) for terms in program.values() for c, f, g in terms):
        return False
    return expand(program) == target(l, n, m)


def norm_factor(f):
    items = tuple(sorted(f.items()))
    if not items:
        return items, 0
    if items[0][1] < 0:
        return tuple((v, -c) for v, c in items), -1
    return items, 1


def products(program):
    """Rule 2: the distinct products of two non-constant factors."""
    keys = set()
    for terms in program.values():
        for c, f, g in terms:
            nf, _ = norm_factor(f)
            ng, _ = norm_factor(g)
            if nf and ng:
                keys.add(tuple(sorted((nf, ng))))
    return keys


def occurrences(program):
    """The count with sharing switched off (a planted fault)."""
    return sum(len(terms) for terms in program.values())


# ---------------------------------------------------------------- the paper's algorithms

def algorithm1_row(i, shared):
    """Algorithm 1 for row i of A; shared holds p7, p8, p9 (B's products)."""
    a1, a2, a3 = a(i, 1), a(i, 2), a(i, 3)
    p1 = (L(a2, b(1, 2)), L(a1, b(2, 1)))
    p2 = (L(a3, b(1, 3)), L(a1, b(3, 1)))
    p3 = (L(a3, b(2, 3)), L(a2, b(3, 2)))
    p4 = (L(a1), L(b(1, 1), neg(b(1, 2)), neg(b(1, 3)), neg(a2), neg(a3)))
    p5 = (L(a2), L(b(2, 2), neg(b(2, 1)), neg(b(2, 3)), neg(a1), neg(a3)))
    p6 = (L(a3), L(b(3, 3), neg(b(3, 1)), neg(b(3, 2)), neg(a1), neg(a2)))
    p7, p8, p9 = shared
    plus = lambda p: (1, p[0], p[1])
    minus = lambda p: (-1, p[0], p[1])
    return {(i, 1): [plus(p4), plus(p1), plus(p2), minus(p7), minus(p8)],
            (i, 2): [plus(p5), plus(p1), plus(p3), minus(p7), minus(p9)],
            (i, 3): [plus(p6), plus(p2), plus(p3), minus(p8), minus(p9)]}


def theorem1(n):
    shared = ((L(b(1, 2)), L(b(2, 1))), (L(b(1, 3)), L(b(3, 1))), (L(b(2, 3)), L(b(3, 2))))
    prog = {}
    for i in range(1, n + 1):
        prog.update(algorithm1_row(i, shared))
    return prog


def corollary1(fault=None):
    """Corollary 1 as printed: p1-p18 for the rows, p19-p21 for B."""
    P = {}
    for r, base in ((1, 0), (2, 6), (3, 12)):
        x1, x2, x3 = a(r, 1), a(r, 2), a(r, 3)
        P[base + 1] = (L(x2, b(1, 2)), L(x1, b(2, 1)))
        P[base + 2] = (L(x3, b(1, 3)), L(x1, b(3, 1)))
        P[base + 3] = (L(x3, b(2, 3)), L(x2, b(3, 2)))
        if fault == "p4" and r == 1:
            P[base + 4] = (L(x1), L(b(1, 1), neg(b(1, 2)), neg(b(1, 3)), x2, neg(x3)))
        else:
            P[base + 4] = (L(x1), L(b(1, 1), neg(b(1, 2)), neg(b(1, 3)), neg(x2), neg(x3)))
        P[base + 5] = (L(x2), L(b(2, 2), neg(b(2, 1)), neg(b(2, 3)), neg(x1), neg(x3)))
        P[base + 6] = (L(x3), L(b(3, 3), neg(b(3, 1)), neg(b(3, 2)), neg(x1), neg(x2)))
    P[19] = (L(b(1, 2)), L(b(2, 1)))
    P[20] = (L(b(1, 3)), L(b(3, 1)))
    P[21] = (L(b(2, 3)), L(b(3, 2)))

    def row(*spec):
        return [(s, P[k][0], P[k][1]) for s, k in spec]
    prog = {}
    for r, base in ((1, 0), (2, 6), (3, 12)):
        prog[(r, 1)] = row((1, base + 4), (1, base + 1), (1, base + 2), (-1, 19), (-1, 20))
        prog[(r, 2)] = row((1, base + 5), (1, base + 1), (1, base + 3), (-1, 19), (-1, 21))
        prog[(r, 3)] = row((1, base + 6), (1, base + 2), (1, base + 3), (-1, 20), (-1, 21))
    return prog


def theorem2(l, n, m, col0=0, row0=0):
    """Theorem 2 for an l x n by n x m product (n even), its columns of A and rows of B offset by col0 and row0."""
    A = lambda i, k: a(i, col0 + k)
    B = lambda k, j: b(row0 + k, j)
    prog = {}
    for i in range(1, l + 1):
        prog[(i, 1)] = []
        for k in range(1, n // 2 + 1):
            prog[(i, 1)].append((1, L(A(i, 2 * k - 1)), L(B(2 * k - 1, 1), A(i, 2 * k))))
        for k in range(1, n // 2 + 1):
            prog[(i, 1)].append((1, L(A(i, 2 * k)), L(B(2 * k, 1), neg(A(i, 2 * k - 1)))))
        for j in range(2, m + 1):
            terms = []
            for k in range(1, n // 2 + 1):
                terms.append((1, L(A(i, 2 * k - 1), B(2 * k, j)), L(A(i, 2 * k), B(2 * k - 1, 1), B(2 * k - 1, j))))
            for k in range(1, n // 2 + 1):
                terms.append((-1, L(A(i, 2 * k - 1)), L(B(2 * k - 1, 1), A(i, 2 * k))))
            for k in range(1, n // 2 + 1):
                terms.append((-1, L(B(2 * k, j)), L(B(2 * k - 1, 1), B(2 * k - 1, j))))
            prog[(i, j)] = terms
    return prog


def theorem3(l, n, m, fault=None):
    """Theorem 3: A1 B1 by Case 1 (m odd) or Case 2 (m even), A2 B2 by Theorem 2."""
    if n < 3 or n % 2 == 0 or m < 3 or l < 1:
        raise ValueError("Theorem 3 needs odd n >= 3, l >= 1 and m >= 3")
    prog = {}
    for i in range(1, l + 1):
        x1, x2, x3 = a(i, 1), a(i, 2), a(i, 3)
        q12 = (L(x1, b(2, 1)), L(x2, b(1, 2)))
        q13 = (L(x1, b(3, 1)), L(x3, b(1, 3)))
        q23 = (L(x2, b(3, 2)), L(x3, b(2, 3)))
        s12 = (L(b(1, 2)), L(b(2, 1)))
        s13 = (L(b(1, 3)), L(b(3, 1)))
        s23 = (L(b(2, 3)), L(b(3, 2)))
        t = lambda c, p: (c, p[0], p[1])
        prog[(i, 1)] = [t(1, q12), t(1, q13),
                        (1, L(x1), L(b(1, 1), neg(b(1, 2)), neg(b(1, 3)), neg(x2), neg(x3))), t(-1, s12), t(-1, s13)]
        prog[(i, 2)] = [t(1, q12), t(1, q23),
                        (1, L(x2), L(b(2, 2), neg(b(2, 1)), neg(b(2, 3)), neg(x1), neg(x3))), t(-1, s12), t(-1, s23)]
        prog[(i, 3)] = [t(1, q13), t(1, q23),
                        (1, L(x3), L(b(3, 3), neg(b(3, 1)), neg(b(3, 2)), neg(x1), neg(x2))), t(-1, s13), t(-1, s23)]
        if m % 2:
            pairs = range(4, m, 2)
        else:
            prog[(i, 4)] = [t(1, q12),
                            (1, L(x1, b(2, 1), neg(b(2, 4))), L(neg(x2), neg(b(1, 2)), b(1, 4))),
                            (1, L(x3), L(b(3, 4))),
                            t(-1, s12),
                            (-1, L(b(2, 1), neg(b(2, 4))), L(neg(b(1, 2)), b(1, 4)))]
            pairs = range(5, m, 2)
        for j in pairs:
            jj = j + 1
            b1j = b(1, jj) if fault == "b1j" and i == 1 and j == pairs[0] else b(1, j)
            prog[(i, j)] = [t(1, q12), t(1, q13),
                            (1, L(x1, b(2, 1), neg(b(2, j))), L(neg(x2), neg(b(1, 2)), b1j, neg(b(1, jj)))),
                            (1, L(x1, b(3, 1), neg(b(3, j))), L(neg(x3), neg(b(1, 3)), b(1, jj))),
                            t(-1, s12), t(-1, s13),
                            (-1, L(b(2, 1), neg(b(2, j))), L(neg(b(1, 2)), b(1, j), neg(b(1, jj)))),
                            (-1, L(b(3, 1), neg(b(3, j))), L(neg(b(1, 3)), b(1, jj)))]
            prog[(i, jj)] = [t(1, q13), t(1, q23),
                             (1, L(x1, b(3, 1), neg(b(3, j))), L(neg(x3), neg(b(1, 3)), b(1, jj))),
                             (1, L(x2, b(3, 2), b(3, j), neg(b(3, jj))), L(neg(x3), neg(b(2, 3)), b(2, jj))),
                             t(-1, s13), t(-1, s23),
                             (-1, L(b(3, 1), neg(b(3, j))), L(neg(b(1, 3)), b(1, jj))),
                             (-1, L(b(3, 2), b(3, j), neg(b(3, jj))), L(neg(b(2, 3)), b(2, jj)))]
    if n > 3:
        for entry, terms in theorem2(l, n - 3, m, col0=3, row0=3).items():
            prog[entry] = prog[entry] + terms
    return prog


def theorem3_bound(l, n, m):
    if m % 2:
        return n * (l * m + l + m - 1) // 2
    return (n * (l * m + l + m - 1) + l - 1) // 2


def waksman(l, n, m):
    """Waksman's and Islam's count for odd n, as the paper gives it."""
    return (n - 1) * (l * m + l + m - 1) // 2 + l * m


def strassen():
    """Strassen's 2 x 2 algorithm (a control)."""
    a11, a12, a21, a22 = a(1, 1), a(1, 2), a(2, 1), a(2, 2)
    b11, b12, b21, b22 = b(1, 1), b(1, 2), b(2, 1), b(2, 2)
    M1 = (L(a11, a22), L(b11, b22))
    M2 = (L(a21, a22), L(b11))
    M3 = (L(a11), L(b12, neg(b22)))
    M4 = (L(a22), L(b21, neg(b11)))
    M5 = (L(a11, a12), L(b22))
    M6 = (L(a21, neg(a11)), L(b11, b12))
    M7 = (L(a12, neg(a22)), L(b21, b22))
    t = lambda c, p: (c, p[0], p[1])
    return {(1, 1): [t(1, M1), t(1, M4), t(-1, M5), t(1, M7)], (1, 2): [t(1, M3), t(1, M5)],
            (2, 1): [t(1, M2), t(1, M4)], (2, 2): [t(1, M1), t(-1, M2), t(1, M3), t(1, M6)]}


def classical(l, n, m):
    return {(i, j): [(1, L(a(i, k)), L(b(k, j))) for k in range(1, n + 1)]
            for i in range(1, l + 1) for j in range(1, m + 1)}


# ---------------------------------------------------------------- numeric evaluation (controls)

def evaluate(program, values):
    out = {}
    for entry, terms in program.items():
        s = 0
        for c, f, g in terms:
            s += c * sum(x * values[v] for v, x in f.items()) * sum(x * values[v] for v, x in g.items())
        out[entry] = s
    return out


def numeric_ok(program, l, n, m, stream):
    for _ in range(POINTS):
        vals = {}
        for i in range(1, l + 1):
            for k in range(1, n + 1):
                vals[a(i, k)] = stream.int_in(-10 ** 6, 10 ** 6)
        for k in range(1, n + 1):
            for j in range(1, m + 1):
                vals[b(k, j)] = stream.int_in(-10 ** 6, 10 ** 6)
        got = evaluate(program, vals)
        for i in range(1, l + 1):
            for j in range(1, m + 1):
                if got[(i, j)] != sum(vals[a(i, k)] * vals[b(k, j)] for k in range(1, n + 1)):
                    return False
    return True


# ---------------------------------------------------------------- matrices as entries (beside, controls)

def mat_rand(stream, s=BLOCK, lo=-9, hi=9):
    return tuple(tuple(stream.int_in(lo, hi) for _ in range(s)) for _ in range(s))


def madd(X, Y, c=1):
    return tuple(tuple(x + c * y for x, y in zip(r, q)) for r, q in zip(X, Y))


def mmul(X, Y):
    return tuple(tuple(sum(X[i][k] * Y[k][j] for k in range(len(Y))) for j in range(len(Y[0])))
                 for i in range(len(X)))


def mT(X):
    return tuple(zip(*X))


def mzero(s=BLOCK):
    return tuple(tuple(0 for _ in range(s)) for _ in range(s))


def eval_noncommutative(program, values, s=BLOCK):
    """Evaluate a commutative program with matrices as entries, keeping each product's factor order."""
    out = {}
    for entry, terms in program.items():
        acc = mzero(s)
        for c, f, g in terms:
            F, G = mzero(s), mzero(s)
            for v, x in f.items():
                F = madd(F, values[v], x)
            for v, x in g.items():
                G = madd(G, values[v], x)
            acc = madd(acc, mmul(F, G), c)
        out[entry] = acc
    return out


def nonbilinear(n):
    """Theorems 4 (n even) and 5 (n odd): for each C_ij, a list of (coefficient, X, Y), X and Y formal sums of
    (name, i, j, transposed) with integer coefficients."""
    def sym(name, i, j, tr=False):
        return ((name, i, j, tr),)

    def fsum(*parts):
        out = {}
        for part in parts:
            for t in part:
                out[t] = out.get(t, 0) + 1
        return out

    prog = {}
    pairs = list(range(1, n, 2)) if n % 2 == 0 else list(range(1, n - 1, 2))
    for i in pairs:
        for j in range(1, n + 1):
            for row, other in ((i, i + 1), (i + 1, i)):
                terms = []
                for k in range(1, n + 1):
                    terms.append((1, fsum(sym("A", row, k), sym("B", j, k, True)),
                                  fsum(sym("A", other, j, True), sym("B", k, j))))
                terms.append((-1, fsum(*[sym("A", row, k) for k in range(1, n + 1)],
                                        *[sym("B", j, k, True) for k in range(1, n + 1)]),
                              fsum(sym("A", other, j, True))))
                for k in range(1, n + 1):
                    terms.append((-1, fsum(sym("B", j, k, True)), fsum(sym("B", k, j))))
                prog[(row, j)] = terms
    if n % 2:
        for j in range(1, n + 1):
            terms = []
            for k in range(1, n + 1):
                terms.append((1, fsum(sym("A", n, k), sym("B", j, k, True)),
                              fsum(sym("A", n, j, True), sym("B", k, j))))
            terms.append((-1, fsum(*[sym("A", n, k) for k in range(1, n + 1)],
                                    *[sym("B", j, k, True) for k in range(1, n + 1)]), fsum(sym("A", n, j, True))))
            for k in range(1, n + 1):
                terms.append((-1, fsum(sym("B", j, k, True)), fsum(sym("B", k, j))))
            prog[(n, j)] = terms
    return prog


def nonbilinear_eval(prog, values):
    out = {}
    for entry, terms in prog.items():
        acc = mzero()
        for c, X, Y in terms:
            F, G = mzero(), mzero()
            for (name, i, j, tr), x in X.items():
                F = madd(F, mT(values[(name, i, j)]) if tr else values[(name, i, j)], x)
            for (name, i, j, tr), x in Y.items():
                G = madd(G, mT(values[(name, i, j)]) if tr else values[(name, i, j)], x)
            acc = madd(acc, mmul(F, G), c)
        out[entry] = acc
    return out


def nonbilinear_count(prog):
    """Distinct products up to transposition: X Y and Y^T X^T counted once."""
    def key(X):
        return tuple(sorted(X.items()))

    def transpose(X):
        return {(name, i, j, not tr): x for (name, i, j, tr), x in X.items()}
    keys = set()
    for terms in prog.values():
        for c, X, Y in terms:
            k1 = (key(X), key(Y))
            k2 = (key(transpose(Y)), key(transpose(X)))
            keys.add(min(k1, k2))
    return len(keys)


# ---------------------------------------------------------------- the run

def controls_run(seed):
    ctl = {}
    ok = True
    st = Stream(seed, "rosowski/numeric")
    for n in THEOREM1_N:
        ok &= numeric_ok(theorem1(n), n, 3, 3, st)
    ok &= numeric_ok(corollary1(), 3, 3, 3, st)
    for n in THEOREM3_N:
        for l in THEOREM3_L:
            for m in THEOREM3_M_ODD + THEOREM3_M_EVEN:
                ok &= numeric_ok(theorem3(l, n, m), l, n, m, st)
    ctl["every algorithm of the test equals AB numerically at three seed-drawn integer points"] = ok
    ctl["Strassen's 2 x 2 algorithm holds with 7 multiplications"] = (
        holds(strassen(), 2, 2, 2) and len(products(strassen())) == 7)
    ctl["the classical product holds with lmn multiplications (l, n, m = 2, 3, 4)"] = (
        holds(classical(2, 3, 4), 2, 3, 4) and len(products(classical(2, 3, 4))) == 24)
    ctl["planted fault caught: Corollary 1's p4 with + a12"] = not holds(corollary1(fault="p4"), 3, 3, 3)
    ctl["planted fault caught: Theorem 3's c_ij with b_1j for b_1(j+1)"] = not holds(
        theorem3(2, 5, 7, fault="b1j"), 2, 5, 7)
    ctl["planted fault caught: the count without sharing exceeds 21"] = occurrences(corollary1()) > 21
    st = Stream(seed, "rosowski/noncommutative")
    vals = {}
    for i in range(1, 4):
        for j in range(1, 4):
            vals[a(i, j)] = mat_rand(st)
            vals[b(i, j)] = mat_rand(st)
    got = eval_noncommutative(corollary1(), vals)
    block = {(i, j): mzero() for i in range(1, 4) for j in range(1, 4)}
    for i in range(1, 4):
        for j in range(1, 4):
            for k in range(1, 4):
                block[(i, j)] = madd(block[(i, j)], mmul(vals[a(i, k)], vals[b(k, j)]))
    ctl["Corollary 1 fails on noncommuting 3 x 3 integer matrix entries"] = got != block
    return ctl


def run(seed, results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    ctl = controls_run(seed)
    if not all(ctl.values()):
        raise AssertionError(f"a control failed: {[k for k, v in ctl.items() if not v]}")

    t1 = {}
    for n in THEOREM1_N:
        prog = theorem1(n)
        t1[n] = {"holds": holds(prog, n, 3, 3), "products": len(products(prog)), "bound": 6 * n + 3}
    c1 = corollary1()
    c1_info = {"holds": holds(c1, 3, 3, 3), "products": len(products(c1)), "bound": 21,
               "same_as_theorem1": expand(c1) == expand(theorem1(3)) and products(c1) == products(theorem1(3))}
    t3 = {}
    for n in THEOREM3_N:
        for l in THEOREM3_L:
            for m in THEOREM3_M_ODD + THEOREM3_M_EVEN:
                prog = theorem3(l, n, m)
                t3[(l, n, m)] = {"holds": holds(prog, l, n, m), "products": len(products(prog)),
                                 "bound": theorem3_bound(l, n, m), "classical": l * n * m,
                                 "waksman": waksman(l, n, m)}
    cond = {
        "Theorem 1 holds for n = 1..10 with at most 6n + 3": all(v["holds"] and v["products"] <= v["bound"]
                                                                   for v in t1.values()),
        "Corollary 1's printed scheme holds with at most 21": c1_info["holds"] and c1_info["products"] <= 21,
        "Theorem 3 holds for odd m with at most n(lm + l + m - 1)/2": all(
            v["holds"] and v["products"] <= v["bound"] for (l, n, m), v in t3.items() if m % 2),
        "Theorem 3 holds for even m with at most (n(lm + l + m - 1) + l - 1)/2": all(
            v["holds"] and v["products"] <= v["bound"] for (l, n, m), v in t3.items() if m % 2 == 0),
    }

    t2 = {}
    for n in THEOREM2_N:
        for l in THEOREM2_L:
            for m in THEOREM2_M:
                prog = theorem2(l, n, m)
                t2[(l, n, m)] = {"holds": holds(prog, l, n, m), "products": len(products(prog)),
                                 "bound": n * (l * m + l + m - 1) // 2}
    nb = {}
    st = Stream(seed, "rosowski/nonbilinear")
    for n in NONBILINEAR_N:
        prog = nonbilinear(n)
        vals = {(name, i, j): mat_rand(st) for name in ("A", "B") for i in range(1, n + 1) for j in range(1, n + 1)}
        got = nonbilinear_eval(prog, vals)
        ok = True
        for i in range(1, n + 1):
            for j in range(1, n + 1):
                want = mzero()
                for k in range(1, n + 1):
                    want = madd(want, mmul(vals[("A", i, k)], vals[("B", k, j)]))
                ok &= got[(i, j)] == want
        bound = n * (n * n + 3 * n + (1 if n % 2 == 0 else 2)) // 2
        nb[n] = {"holds": ok, "products": nonbilinear_count(prog), "bound": bound}

    exact3 = sum(v["products"] == v["bound"] for v in t3.values())
    saving = [v["waksman"] - v["products"] for v in t3.values()]
    values = {
        "theorem1": ("n x 3 by 3 x 3, n = 1..10: " + ", ".join(
            f"{t1[n]['products']}{'' if t1[n]['holds'] else '!'}" for n in THEOREM1_N)
            + " products (6n + 3: " + ", ".join(str(6 * n + 3) for n in THEOREM1_N) + ")"),
        "corollary1": (f"3 x 3 as printed: {'holds' if c1_info['holds'] else 'FAILS'}, {c1_info['products']} "
                       f"products; {'the same as' if c1_info['same_as_theorem1'] else 'not'} Theorem 1 at n = 3"),
        "theorem3_odd_m": (f"odd n 3..9, l 1..5, m 3,5,7,9: holds in "
                           f"{sum(v['holds'] for (l, n, m), v in t3.items() if m % 2)} of "
                           f"{sum(1 for (l, n, m) in t3 if m % 2)}; within the bound in "
                           f"{sum(v['products'] <= v['bound'] for (l, n, m), v in t3.items() if m % 2)}"),
        "theorem3_even_m": (f"odd n 3..9, l 1..5, m 4,6,8: holds in "
                            f"{sum(v['holds'] for (l, n, m), v in t3.items() if m % 2 == 0)} of "
                            f"{sum(1 for (l, n, m) in t3 if m % 2 == 0)}; within the bound in "
                            f"{sum(v['products'] <= v['bound'] for (l, n, m), v in t3.items() if m % 2 == 0)}"),
        "theorem3_counts": (f"products equal to the stated count in {exact3} of {len(t3)}; n = 9, l = 5, m = 9: "
                            f"{t3[(5, 9, 9)]['products']} (classical {t3[(5, 9, 9)]['classical']})"),
        "theorem2": (f"even n 2..10, l 1..5, m 1..7: holds in {sum(v['holds'] for v in t2.values())} of {len(t2)}, "
                     f"at the stated count in {sum(v['products'] == v['bound'] for v in t2.values())}"),
        "against_waksman": (f"fewer than Waksman and Islam's count in {sum(s > 0 for s in saving)} of {len(saving)} "
                            f"(saving {min(saving)} to {max(saving)})"),
        "nonbilinear": ("Theorems 4 and 5, 3 x 3 integer blocks, n = 2..7: " + ", ".join(
            f"{n} {'holds' if nb[n]['holds'] else 'FAILS'}" for n in NONBILINEAR_N)),
        "nonbilinear_counts": ("products up to transposition: " + ", ".join(
            f"{nb[n]['products']}/{nb[n]['bound']}" for n in NONBILINEAR_N)),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"test": TEST, "conditions": cond, "controls": ctl, "theorem1": {str(k): v for k, v in t1.items()},
              "corollary1": c1_info, "theorem3": {f"{l},{n},{m}": v for (l, n, m), v in t3.items()},
              "theorem2": {f"{l},{n},{m}": v for (l, n, m), v in t2.items()},
              "nonbilinear": {str(k): v for k, v in nb.items()}}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="utf-8") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"rosowski: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
