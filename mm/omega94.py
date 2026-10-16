#!/usr/bin/env python3
"""OpenAI's bound omega <= 9/4: the paper's finite constructions built as printed and checked exactly, and the
hypotheses of its growth lemma solved as a linear programme.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from OpenAI, "An Upper Bound of 9/4 for the
Matrix Multiplication Exponent" (OpenAI Math Release preprint, 2 October 2026; openai/math, family 107, Apache 2.0),
its abstract: "We prove that the exponent of matrix multiplication over the complex numbers is at most 9/4." Its
proof combines three explicit tensor degenerations (Proposition 3.1, Lemmas 4.1 and 4.2) with Strassen's asymptotic
spectrum (Lemma 2.2 and Appendix A) and a discrete growth lemma (Lemma 5.1). No finite computation reaches the
spectral argument or the limits; this module checks every finite construction exactly on small cases, as printed,
and decides whether the hypotheses of Lemma 5.1, as the proof uses them, force its conclusion on a finite grid.

No data of record: the constructions are defined by the paper's formulas, transcribed below, so every run is new.
Standard library, and scipy for the linear programme. Every rule below was fixed before any construction of the paper
was built or any programme solved; the tests exercise the machinery on other inputs.

A degeneration (the paper's Section 2.2): after linear substitutions, each target variable gets an integer weight,
each term the sum of its three variables' weights; it degenerates to the part of weight zero provided no term has
negative weight.

1. Proposition 3.1 (shared-leg separation). For M = 1 to 4, a tensor A = sum_h A_h with a common first leg (basis
   x_a, n_x = 3) and disjoint, matched sectors on the other two (y_(h,b), z_(h,c), each of 1 to 2 coordinates), with
   integer coefficients in [-3, 3] drawn from the seed (each A_h nonzero). L = 5M copies r = 0..L-1, zeta a primitive
   Lth root of unity, and the printed substitutions
       x_a^(r) -> sum_g zeta^(2rg) X_(a,g),   y_(h,b)^(r) -> sum_u zeta^(r(u-h)) Y_(h,b,u),
       z_(h,c)^(r) -> (1/L) sum_v zeta^(r(-v-h)) Z_(h,c,v),   g, u, v in 1..M;
   the copies summed exactly in Z[zeta] (integer vectors modulo the Lth cyclotomic polynomial). Weights as printed:
   w(X_(a,g)) = g^2, w(Y_(h,b,u)) = hu - h^2, w(Z_(h,c,v)) = -hv. It holds for the instance if every surviving term
   satisfies (3.2), u - v + 2(g - h) = 0, has weight (g - h)^2 >= 0, at most (M - 1)^2, and the weight-zero part is
   exactly D = sum c_(h,a,b,c) X_(a,h) Y_(h,b,u) Z_(h,c,u) over u = 1..M: a full direct sum over h (each block's
   variables carry h on all three legs) of A_h tensor B_X(M). Three instances for each M.
2. Lemma 4.1 (determinant filtration), for a = 1 to 5 and b = 2 to 6: C(a,b) tensor B_X(2) as multiplication
   V_(a-1) x (V_(b-1) (x) W_1) -> V_(a+b-2) (x) W_1, W_1 = span(s, w), D = uw - vs; on V_e (x) W_1 the printed basis:
   quotient lifts u^(e-i) v^i s (0 <= i <= e) and v^e w, then the kernel D u^(e-1-j) v^j (0 <= j < e), at e = b - 1
   (second leg) and e = a + b - 2 (third leg, its dual); the first leg the monomials u^(a-1-i) v^i. Weights: 0 on the
   first leg and on quotient coordinates, -1 on second-leg kernel coordinates, +1 on output-dual kernel coordinates.
   It holds if no term has negative weight and the weight-zero part is exactly C(a, b+1) on the quotient coordinates
   (their diagonal images, the standard monomials) and C(a, b-1) on the kernel coordinates (their kernel factors),
   sharing the first leg.
3. Lemma 4.2 (shifted tripling), for a, h = 1 to 6: C(a, B), B = 3h + a - 1, with the printed partition (Y: [0,h-1],
   [h,2h+a-2], [2h+a-1,3h+a-2]; Z: [0,h+a-2], [h+a-1,2h+a-2], [2h+a-1,3h+2a-3]) and weights +1 on middle Y, -1 on
   middle Z. It holds if the parts partition each leg's indices, no term has negative weight, and the weight-zero part
   is the three matched sectors: the outer two C(a,h) by translation, the middle exactly the printed
   sum_(u<a, r<h) x_(a-1-u) y_(h+u+r) z_(h+a-1+r), which is C(a,h) with its second and third legs exchanged and its
   first-leg basis reversed.
4. Lemma 5.1 (diagonal growth). The least P(a,a) the lemma's hypotheses allow on the grid 1 <= a <= 24,
   1 <= b <= 96, found by linear programming (scipy's HiGHS) for each a from 2 to 24: variables P(a,b) >= 0 with
   P(1,b) = b, P(a,b) = P(b,a) where both lie in the grid, concavity 2P(a,b) >= P(a,b+1) + P(a,b-1) along every row,
   and down every column (the paper: "By symmetry, the analogous inequality holds in the first argument"), and the
   tripling P(a, 3h+a-1) >= 3P(a,h) wherever 3h + a - 1 <= 96. The grid holds every inequality the lemma's proof
   uses for a <= 24 (rows to column 4a - 1). It holds if each minimum is at least a^(4/3) - 1e-7.
5. The test (TEST). Refuted if any instance of 1 to 3 fails or any minimum in 4 falls below a^(4/3).

Beside the test, none of it counted: (4.2), the rank of C(a,b) is a + b - 1, by an exact evaluation-interpolation
decomposition and the output flattening's rank, a, b = 1 to 6; the proof's own bound a H_a (H_a = prod_(m<a)
(1 + 1/(3m))) against each linear-programming minimum; the elementary inequality (1 + 1/(3m))^3 >= 1 + 1/m and
H_a^3 >= a for a up to 10^5; the exponent the finite inequality a^(4/3) <= (2a - 1)^(1/t) allows at a = 10^3, 10^6
and 10^9 (it tends to t <= 3/4); and the fewest copies the separation needs, 3M - 2 (any L > 3(M - 1)), against the
printed 5M.

Controls (controls_passed counts those that behave as stated): sum_r zeta^(rk) is L or 0 in Z[zeta] for L = 2 to 20
and |k| <= 3L; the substitution engine with the phase of z planted as zeta^(r(v-h)), with the weight of Z planted as
+hv, and with too few copies (L = 3M - 3 at M = 3) is caught in each case; Lemma 4.1's printed example
u(vw) = v^2 s + vD at a = b = 2 is reproduced, and with the second-leg kernel weight planted as +1 the weight-zero
part is caught; the paper's Figure 1 (C(2,4), a = 2, h = 1: three surviving blocks, two crossed terms) is reproduced;
and with the tripling constraints dropped the programme's minimum falls below a^(4/3) at a = 8 and 16 (the
constraints carry the lemma).

What it cannot check: Lemma 2.2 and Appendix A (the existence of detecting characters), Corollary 3.2's passage from
the finite separation to entropy as N grows, the constructions beyond the sizes tried, and the limits in a. The
paper's Lean formalization (OAI.MatrixMultiplication.complex_omega_le_nine_quarters) needs Lean 4 with Mathlib,
which this container cannot hold.

Changed after a trial: the last control first named a = 4 and 8. The first trial in the reference runner, under a
seed of Imago's own, found every condition of the test met and that control failed: without the tripling the least
P(4,4) is 6.510, above 4^(4/3) = 6.350 (concavity and P(1,b) = b alone force that much at a = 4), while at a = 8 it is
12.331, below 16. The control's two sizes were moved to 8 and 16 at the next commit, after that outcome was seen;
nothing the test computes changed.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 mm/omega94.py
"""

import hashlib
import json
import math
import os
import random
import re
import sys
from fractions import Fraction

M_RANGE = (1, 2, 3, 4)
INSTANCES = 3
NX = 3
SECTOR_DIMS = (1, 2)
COEFF = 3
LEMMA41_A = range(1, 6)
LEMMA41_B = range(2, 7)
LEMMA42_A = range(1, 7)
LEMMA42_H = range(1, 7)
GRID_A, GRID_B = 24, 96
LP_TOL = 1e-7
NO_TRIPLING_A = (8, 16)
TEST = ("Refuted if one of the paper's finite constructions, built as printed, fails on small cases: Proposition 3.1's "
        "substitutions and weights (L = 5M copies, M = 1 to 4, seed-drawn integer blocks) leave a negative weight, a "
        "survivor outside (3.2) or a weight-zero part other than the direct sum of the A_h ⊗ B_X(M); Lemma 4.1's bases and "
        "weights (a = 1 to 5, b = 2 to 6) leave a negative weight or a weight-zero part other than C(a,b+1) ⊕ "
        "C(a,b−1); Lemma 4.2's (a, h = 1 to 6) other than its three sectors; or the least P(a,a) Lemma 5.1's "
        "hypotheses allow on a 24 × 96 grid falls below a^(4/3).")
OUTPUTS = ("prop31", "prop31_terms", "lemma41", "lemma41_star", "lemma42", "lemma51", "lemma51_margin",
           "lemma51_proof", "rank42", "h_bound", "t_bound", "copies", "conditions_met", "conditions_total",
           "test_passed", "controls_passed", "controls_total")
LIMIT = 200


class Refused(Exception):
    pass


def seeded(seed, label):
    return random.Random(int.from_bytes(hashlib.sha256(f"{seed}/{label}".encode()).digest(), "big"))


# ----------------------------------------------------------------------------------------------- Z[zeta_L]
def poly_divmod(num, den):
    """Integer polynomials, lowest degree first; den monic."""
    num = list(num)
    q = [0] * max(len(num) - len(den) + 1, 1)
    for i in range(len(num) - len(den), -1, -1):
        c = num[i + len(den) - 1]
        q[i] = c
        if c:
            for j, d in enumerate(den):
                num[i + j] -= c * d
    r = num[:len(den) - 1]
    while r and r[-1] == 0:
        r.pop()
    return q, r


def cyclotomic(n, memo={}):
    """Phi_n by x^n - 1 = prod over d | n of Phi_d."""
    if n in memo:
        return memo[n]
    p = [-1] + [0] * (n - 1) + [1]
    for d in range(1, n):
        if n % d == 0:
            p, r = poly_divmod(p, cyclotomic(d))
            assert not r
    while p and p[-1] == 0:
        p.pop()
    memo[n] = p
    return p


def reduce_mod(vec, L):
    """An integer combination of zeta^0 .. zeta^(L-1) reduced modulo Phi_L: a tuple of phi(L) integers."""
    phi = cyclotomic(L)
    _, r = poly_divmod(list(vec) + [0], phi) if len(vec) >= len(phi) else (None, list(vec))
    out = list(r) + [0] * (len(phi) - 1 - len(r))
    return tuple(out[:len(phi) - 1])


def char_sum(k, L):
    """sum over r = 0..L-1 of zeta^(rk), exactly, as a reduced vector."""
    vec = [0] * L
    for r in range(L):
        vec[(r * k) % L] += 1
    return reduce_mod(vec, L)


# ----------------------------------------------------------------------------------------------- Proposition 3.1
PHASES = {
    "x": lambda r, g: 2 * r * g,
    "y": lambda r, h, u: r * (u - h),
    "z": lambda r, h, v: r * (-v - h),
}
WEIGHTS = {
    "x": lambda g: g * g,
    "y": lambda h, u: h * u - h * h,
    "z": lambda h, v: -h * v,
}


def random_block_tensor(M, rng):
    """{(h, a, b, c): coefficient}: a common first leg of NX coordinates, sector h with its own y and z coordinates."""
    terms = {}
    for h in range(1, M + 1):
        ny, nz = rng.choice(SECTOR_DIMS), rng.choice(SECTOR_DIMS)
        block = {}
        while not block:
            for a in range(NX):
                for b in range(ny):
                    for c in range(nz):
                        v = rng.randint(-COEFF, COEFF)
                        if v and rng.random() < 0.6:
                            block[(h, a, b, c)] = v
        terms.update(block)
    return terms


def separate(A, M, L, phases=PHASES, weights=WEIGHTS):
    """The L copies of A under the substitutions, summed: {(a, g, h, b, u, c, v): (coefficient vector, weight)}.
    The vector is the exact multiple of 1/L in Z[zeta_L] (the 1/L of the z substitution kept aside)."""
    out = {}
    cache = {}
    for (h, a, b, c), coeff in A.items():
        for g in range(1, M + 1):
            for u in range(1, M + 1):
                for v in range(1, M + 1):
                    key = (g, h, u, v)
                    if key not in cache:
                        vec = [0] * L
                        for r in range(L):
                            e = phases["x"](r, g) + phases["y"](r, h, u) + phases["z"](r, h, v)
                            vec[e % L] += 1
                        cache[key] = reduce_mod(vec, L)
                    s = cache[key]
                    if any(s):
                        w = weights["x"](g) + weights["y"](h, u) + weights["z"](h, v)
                        out[(a, g, h, b, u, c, v)] = (tuple(coeff * x for x in s), w)
    return out


def check_separation(A, M, L, phases=PHASES, weights=WEIGHTS):
    T = separate(A, M, L, phases, weights)
    phi_len = len(cyclotomic(L)) - 1
    unit = tuple([L] + [0] * (phi_len - 1))            # L, as a reduced vector: the 1/L then gives 1
    bad_32 = [k for k in T if k[4] - k[6] + 2 * (k[1] - k[2]) != 0]
    negative = [k for k, (vec, w) in T.items() if w < 0]
    wrong_weight = [k for k, (vec, w) in T.items() if w != (k[1] - k[2]) ** 2]
    too_high = [k for k, (vec, w) in T.items() if w > (M - 1) ** 2]
    zero = {k: vec for k, (vec, w) in T.items() if w == 0}
    expected = {}
    for (h, a, b, c), coeff in A.items():
        for u in range(1, M + 1):
            expected[(a, h, h, b, u, c, u)] = tuple(coeff * x for x in unit)
    weight_zero_ok = zero == expected
    blocks_disjoint = all(k[1] == k[2] for k in zero)   # X carries h through g = h; Y and Z carry h
    ok = not bad_32 and not negative and not wrong_weight and not too_high and weight_zero_ok and blocks_disjoint
    return {"ok": ok, "terms": len(T), "weight_zero_terms": len(zero), "expected_terms": len(expected),
            "outside_32": len(bad_32), "negative": len(negative), "wrong_weight": len(wrong_weight),
            "above_degree": len(too_high), "weight_zero_ok": weight_zero_ok, "max_weight": max(
                (w for _, w in T.values()), default=0)}


# ----------------------------------------------------------------------------------------------- C(a, b)
def C(a, b):
    """{(i, j, k): 1}: sum over i < a, j < b of x_i y_j z_(i+j)."""
    return {(i, j, i + j): 1 for i in range(a) for j in range(b)}


# ----------------------------------------------------------------------------------------------- Lemma 4.1
def basis_VeW(e):
    """The printed basis of V_e (x) W_1: quotient lifts u^(e-i) v^i s, then v^e w, then the kernel D u^(e-1-j) v^j;
    vectors over the standard monomials (i, t) = u^(e-i) v^i (x) t, t in 's', 'w'."""
    quot = [{(i, "s"): Fraction(1)} for i in range(e + 1)] + [{(e, "w"): Fraction(1)}]
    kern = [{(j, "w"): Fraction(1), (j + 1, "s"): Fraction(-1)} for j in range(e)]   # D = uw - vs
    return quot, kern


def solve(basis, target, coords):
    """Coordinates of target in the given basis (exact; the basis spans the space of coords)."""
    n = len(basis)
    idx = {c: i for i, c in enumerate(coords)}
    rows = [[Fraction(0)] * (n + 1) for _ in coords]
    for col, vec in enumerate(basis):
        for c, x in vec.items():
            rows[idx[c]][col] = x
    for c, x in target.items():
        rows[idx[c]][n] = x
    r = 0
    piv = []
    for col in range(n):
        p = next((i for i in range(r, len(rows)) if rows[i][col] != 0), None)
        if p is None:
            raise AssertionError("the basis is singular")
        rows[r], rows[p] = rows[p], rows[r]
        inv = 1 / rows[r][col]
        rows[r] = [x * inv for x in rows[r]]
        for i in range(len(rows)):
            if i != r and rows[i][col] != 0:
                f = rows[i][col]
                rows[i] = [x - f * y for x, y in zip(rows[i], rows[r])]
        piv.append(col)
        r += 1
    for i in range(r, len(rows)):
        if rows[i][n] != 0:
            raise AssertionError("the target is outside the span")
    return [rows[i][n] for i in range(n)]


def filtration(a, b, kernel_weight=-1, dual_kernel_weight=1):
    """Lemma 4.1's tensor in the printed bases with its weights: the block structure and the weight-zero part."""
    e_in, e_out = b - 1, a + b - 2
    q_in, k_in = basis_VeW(e_in)
    q_out, k_out = basis_VeW(e_out)
    out_basis = q_out + k_out
    coords = [(i, t) for i in range(e_out + 1) for t in ("s", "w")]
    terms = {}
    for i in range(a):                                  # f_i = u^(a-1-i) v^i: shifts the v-exponent by i
        for kind, family in (("q", q_in), ("k", k_in)):
            for j, g in enumerate(family):
                prod = {}
                for (m, t), x in g.items():
                    prod[(m + i, t)] = prod.get((m + i, t), 0) + x
                xs = solve(out_basis, prod, coords)
                for o, x in enumerate(xs):
                    if x != 0:
                        okind, oj = ("q", o) if o < len(q_out) else ("k", o - len(q_out))
                        w = (kernel_weight if kind == "k" else 0) + (dual_kernel_weight if okind == "k" else 0)
                        terms[(i, kind, j, okind, oj)] = (x, w)
    negative = [k for k, (x, w) in terms.items() if w < 0]
    star = [k for k, (x, w) in terms.items() if k[1] == "q" and k[3] == "k"]
    zero = {k: x for k, (x, w) in terms.items() if w == 0}
    plus = {(i, j, oj): x for (i, kind, j, okind, oj), x in zero.items() if kind == "q" and okind == "q"}
    minus = {(i, j, oj): x for (i, kind, j, okind, oj), x in zero.items() if kind == "k" and okind == "k"}
    cross = [k for k in zero if k[1] != k[3]]
    ok = (not negative and not cross and plus == {k: Fraction(1) for k in C(a, b + 1)}
          and minus == {k: Fraction(1) for k in C(a, b - 1)})
    return {"ok": ok, "terms": len(terms), "negative": len(negative), "star": len(star), "cross_zero": len(cross),
            "plus_ok": plus == {k: Fraction(1) for k in C(a, b + 1)},
            "minus_ok": minus == {k: Fraction(1) for k in C(a, b - 1)}}


def printed_example():
    """u (v w) = v^2 s + v D at a = b = 2: the product of f = u with the lift v^1 w, in the output basis (e = 2)."""
    q_out, k_out = basis_VeW(2)
    coords = [(i, t) for i in range(3) for t in ("s", "w")]
    prod = {(1, "w"): Fraction(1)}                      # u * (v w) = u v w: the monomial u^(2-1) v^1 (x) w
    xs = solve(q_out + k_out, prod, coords)
    quot = {i: x for i, x in enumerate(xs[:len(q_out)]) if x}
    kern = {j: x for j, x in enumerate(xs[len(q_out):]) if x}
    return quot == {2: 1} and kern == {1: 1}            # v^2 s (the lift u^0 v^2 s) and v D (D u^0 v^1)


# ----------------------------------------------------------------------------------------------- Lemma 4.2
def tripling_parts(a, h):
    Y = [(0, h - 1), (h, 2 * h + a - 2), (2 * h + a - 1, 3 * h + a - 2)]
    Z = [(0, h + a - 2), (h + a - 1, 2 * h + a - 2), (2 * h + a - 1, 3 * h + 2 * a - 3)]
    return Y, Z


def part_of(x, parts):
    return next((n for n, (lo, hi) in enumerate(parts) if lo <= x <= hi), None)


def tripling(a, h, ymid=1, zmid=-1):
    B = 3 * h + a - 1
    Y, Z = tripling_parts(a, h)
    partitions = (all(sum(1 for lo, hi in Y if lo <= y <= hi) == 1 for y in range(B))
                  and all(sum(1 for lo, hi in Z if lo <= z <= hi) == 1 for z in range(a + B - 1))
                  and all(lo <= hi for lo, hi in Y + Z))
    terms = C(a, B)
    weight = lambda y, z: (ymid if part_of(y, Y) == 1 else 0) + (zmid if part_of(z, Z) == 1 else 0)
    negative = [t for t in terms if weight(t[1], t[2]) < 0]
    crossed = [t for t in terms if weight(t[1], t[2]) > 0]
    zero = {t for t in terms if weight(t[1], t[2]) == 0}
    sectors = {n: {t for t in zero if part_of(t[1], Y) == n} for n in range(3)}
    matched = all(part_of(t[2], Z) == part_of(t[1], Y) for t in zero)
    base = set(C(a, h))
    left_ok = sectors[0] == base
    off = 2 * h + a - 1
    right_ok = {(i, y - off, z - off) for i, y, z in sectors[2]} == base
    printed_middle = {(a - 1 - u, h + u + r, h + a - 1 + r) for u in range(a) for r in range(h)}
    middle_printed = sectors[1] == printed_middle
    # as C(a,h) with legs 2 and 3 exchanged and the first leg reversed: x_(a-1-u) -> x_u, y_(h+u+r) -> z_(u+r),
    # z_(h+a-1+r) -> y_r gives x_u y_r z_(u+r)
    mapped = {(a - 1 - i, z - (h + a - 1), y - h) for i, y, z in sectors[1]}
    middle_iso = mapped == base
    ok = partitions and not negative and matched and left_ok and right_ok and middle_printed and middle_iso
    return {"ok": ok, "partitions": partitions, "negative": len(negative), "crossed": len(crossed),
            "matched": matched, "left": left_ok, "right": right_ok, "middle_printed": middle_printed,
            "middle_iso": middle_iso, "sizes": [len(sectors[n]) for n in range(3)]}


# ----------------------------------------------------------------------------------------------- Lemma 5.1
def growth_lp(target_a, n_a=GRID_A, n_b=GRID_B, tripling_on=True):
    """The least P(target_a, target_a) the hypotheses allow on the grid (scipy HiGHS)."""
    import numpy as np
    from scipy.optimize import linprog
    from scipy.sparse import lil_matrix
    idx = {}
    for a in range(1, n_a + 1):
        for b in range(1, n_b + 1):
            idx[(a, b)] = len(idx)
    n = len(idx)
    ub_rows, eq_rows = [], []                          # each row: (dict var -> coeff, rhs); A_ub x <= b_ub
    for b in range(1, n_b + 1):
        eq_rows.append(({idx[(1, b)]: 1.0}, float(b)))
    for a in range(1, n_a + 1):
        for b in range(a + 1, n_a + 1):
            eq_rows.append(({idx[(a, b)]: 1.0, idx[(b, a)]: -1.0}, 0.0))
    for a in range(1, n_a + 1):
        for b in range(2, n_b):                         # -2P(a,b) + P(a,b+1) + P(a,b-1) <= 0
            ub_rows.append(({idx[(a, b)]: -2.0, idx[(a, b + 1)]: 1.0, idx[(a, b - 1)]: 1.0}, 0.0))
    for b in range(1, n_b + 1):
        for a in range(2, n_a):
            ub_rows.append(({idx[(a, b)]: -2.0, idx[(a + 1, b)]: 1.0, idx[(a - 1, b)]: 1.0}, 0.0))
    if tripling_on:
        for a in range(1, n_a + 1):
            h = 1
            while 3 * h + a - 1 <= n_b:                 # 3P(a,h) - P(a,3h+a-1) <= 0
                row = {idx[(a, 3 * h + a - 1)]: -1.0}
                row[idx[(a, h)]] = row.get(idx[(a, h)], 0.0) + 3.0
                ub_rows.append((row, 0.0))
                h += 1

    def matrix(rows):
        A = lil_matrix((len(rows), n))
        rhs = np.zeros(len(rows))
        for r, (row, v) in enumerate(rows):
            for j, x in row.items():
                A[r, j] = x
            rhs[r] = v
        return A.tocsr(), rhs
    A_ub, b_ub = matrix(ub_rows)
    A_eq, b_eq = matrix(eq_rows)
    c = np.zeros(n)
    c[idx[(target_a, target_a)]] = 1.0
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=[(0, None)] * n, method="highs")
    if res.status != 0:
        raise AssertionError(f"the programme for a = {target_a} did not solve: {res.message}")
    x = res.x
    viol = max(float(np.max(A_ub @ x - b_ub, initial=0.0)), float(np.max(np.abs(A_eq @ x - b_eq), initial=0.0)))
    return float(res.fun), viol


def h_proof(a):
    v = 1.0
    for m in range(1, a):
        v *= 1 + 1 / (3 * m)
    return v


# ----------------------------------------------------------------------------------------------- beside
def rank_decomposition(a, b):
    """Evaluation at t = 0..a+b-2 and interpolation: a + b - 1 rank-one terms whose sum must be C(a,b)."""
    n = a + b - 1
    pts = list(range(n))
    V = [[Fraction(t) ** k for k in range(n)] for t in pts]   # V[t][k] = t^k, the evaluation matrix
    aug = [row[:] + [Fraction(int(i == j)) for j in range(n)] for i, row in enumerate(V)]
    for col in range(n):                                 # Gauss-Jordan: [V | I] -> [I | V^-1]
        p = next(i for i in range(col, n) if aug[i][col] != 0)
        aug[col], aug[p] = aug[p], aug[col]
        f = 1 / aug[col][col]
        aug[col] = [x * f for x in aug[col]]
        for i in range(n):
            if i != col and aug[i][col] != 0:
                g = aug[i][col]
                aug[i] = [x - g * y for x, y in zip(aug[i], aug[col])]
    Vinv = [row[n:] for row in aug]                      # Vinv[k][t]: interpolation
    total = {}
    for t in pts:
        for i in range(a):
            for j in range(b):
                for k in range(n):
                    x = Fraction(t) ** i * Fraction(t) ** j * Vinv[k][t]
                    if x:
                        total[(i, j, k)] = total.get((i, j, k), 0) + x
    total = {k: x for k, x in total.items() if x != 0}
    return total == {k: Fraction(1) for k in C(a, b)}


def flattening_rank(a, b):
    """Rank of the output flattening (z against the pairs (x, y)) of C(a,b), exactly."""
    rows = [[Fraction(int(i + j == k)) for i in range(a) for j in range(b)] for k in range(a + b - 1)]
    r = 0
    cols = len(rows[0])
    for col in range(cols):
        p = next((i for i in range(r, len(rows)) if rows[i][col] != 0), None)
        if p is None:
            continue
        rows[r], rows[p] = rows[p], rows[r]
        for i in range(len(rows)):
            if i != r and rows[i][col] != 0:
                f = rows[i][col] / rows[r][col]
                rows[i] = [x - f * y for x, y in zip(rows[i], rows[r])]
        r += 1
    return r


def t_bound(a):
    """The largest t with a^(4/3) <= (2a - 1)^(1/t)."""
    return math.log(2 * a - 1) / ((4 / 3) * math.log(a))


# ----------------------------------------------------------------------------------------------- the run
def run(seed, results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    ctl, ctl_info = {}, {}

    # controls first: the character sums, the planted faults
    sums_ok = all(char_sum(k, L) == (tuple([L] + [0] * (len(cyclotomic(L)) - 2)) if k % L == 0
                                     else tuple([0] * (len(cyclotomic(L)) - 1)))
                  for L in range(2, 21) for k in range(-3 * L, 3 * L + 1))
    ctl["sum over r of zeta^(rk) is L or 0 in Z[zeta] for L = 2 to 20 and |k| <= 3L"] = sums_ok
    rng = seeded(seed, "omega94/controls")
    A3 = random_block_tensor(3, rng)
    bad_phase = dict(PHASES, z=lambda r, h, v: r * (v - h))
    bad_weight = dict(WEIGHTS, z=lambda h, v: h * v)
    caught_phase = not check_separation(A3, 3, 15, phases=bad_phase)["ok"]
    caught_weight = not check_separation(A3, 3, 15, weights=bad_weight)["ok"]
    caught_short = not check_separation(A3, 3, 6)["ok"]
    ctl_info["planted"] = {"phase": caught_phase, "weight": caught_weight, "short": caught_short}
    ctl["the separation with z's phase planted as zeta^(r(v-h)), Z's weight as +hv, or 6 copies at M = 3 is caught"] = (
        caught_phase and caught_weight and caught_short)
    ex = printed_example()
    planted41 = not filtration(2, 3, kernel_weight=1)["ok"]
    ctl["Lemma 4.1's example u(vw) = v^2 s + vD is reproduced; a kernel weight planted as +1 is caught"] = (
        ex and planted41)
    fig = tripling(2, 1)
    ctl["Figure 1: C(2,4) at a = 2, h = 1 leaves three blocks of 2 terms and crosses 2 terms"] = (
        fig["ok"] and fig["sizes"] == [2, 2, 2] and fig["crossed"] == 2)
    no_trip = [growth_lp(a, tripling_on=False)[0] for a in NO_TRIPLING_A]
    ctl_info["without_tripling"] = no_trip
    ctl["without the tripling constraints the least P(a,a) falls below a^(4/3) at a = 8 and 16"] = all(
        v < a ** (4 / 3) - 1e-6 for v, a in zip(no_trip, NO_TRIPLING_A))

    # 1. Proposition 3.1
    prop = {}
    for M in M_RANGE:
        for n in range(INSTANCES):
            A = random_block_tensor(M, seeded(seed, f"omega94/prop31/{M}/{n}"))
            prop[(M, n)] = check_separation(A, M, 5 * M)
            prop[(M, n)]["source_terms"] = len(A)
    prop_ok = all(v["ok"] for v in prop.values())
    # 2. Lemma 4.1
    filt = {(a, b): filtration(a, b) for a in LEMMA41_A for b in LEMMA41_B}
    filt_ok = all(v["ok"] for v in filt.values())
    # 3. Lemma 4.2
    trip = {(a, h): tripling(a, h) for a in LEMMA42_A for h in LEMMA42_H}
    trip_ok = all(v["ok"] for v in trip.values())
    # 4. Lemma 5.1
    lp = {}
    for a in range(2, GRID_A + 1):
        lp[a] = growth_lp(a)
    lp_margin = min(v - a ** (4 / 3) for a, (v, _) in lp.items())
    lp_ok = all(v >= a ** (4 / 3) - LP_TOL for a, (v, _) in lp.items())
    worst_viol = max(viol for _, viol in lp.values())
    proof_bound = {a: a * h_proof(a) for a in lp}
    lp_vs_proof = min(lp[a][0] - proof_bound[a] for a in lp)

    cond = {
        "Proposition 3.1: every instance, M = 1 to 4, separates as printed": prop_ok,
        "Lemma 4.1: every (a, b), a = 1 to 5, b = 2 to 6, degenerates to C(a,b+1) and C(a,b-1)": filt_ok,
        "Lemma 4.2: every (a, h), a, h = 1 to 6, degenerates to its three sectors": trip_ok,
        "Lemma 5.1: on the 24 x 96 grid the least P(a,a) is at least a^(4/3), a = 2 to 24": lp_ok,
    }

    # beside
    rank_ok = all(rank_decomposition(a, b) and flattening_rank(a, b) == a + b - 1
                  for a in range(1, 7) for b in range(1, 7))
    elem_ok = all((1 + Fraction(1, 3 * m)) ** 3 >= 1 + Fraction(1, m) for m in range(1, 2001))
    h = 1.0
    h_ok = True
    for a in range(2, 100001):
        h *= 1 + 1 / (3 * (a - 1))
        if h ** 3 < a * (1 - 1e-12):
            h_ok = False
            break
    tb = {a: t_bound(a) for a in (10 ** 3, 10 ** 6, 10 ** 9)}
    fewest = {}
    for M in (2, 3, 4):
        A = random_block_tensor(M, seeded(seed, f"omega94/copies/{M}"))
        ok_L = [L for L in range(1, 5 * M + 1) if check_separation(A, M, L)["ok"]]
        fewest[M] = min(ok_L) if ok_L else None

    def yn(b):
        return "yes" if b else "NO"

    star_total = sum(v["star"] for v in filt.values())
    values = {
        "prop31": (f"{sum(v['ok'] for v in prop.values())} of {len(prop)} instances separate as printed (M = 1 to 4, "
                   f"L = 5M; survivors outside (3.2) {sum(v['outside_32'] for v in prop.values())}, negative weights "
                   f"{sum(v['negative'] for v in prop.values())})"),
        "prop31_terms": (f"terms after summing the copies: {sum(v['terms'] for v in prop.values())}; of weight zero "
                         f"{sum(v['weight_zero_terms'] for v in prop.values())}, the direct sum's "
                         f"{sum(v['expected_terms'] for v in prop.values())}; largest weight "
                         f"{max(v['max_weight'] for v in prop.values())}"),
        "lemma41": (f"{sum(v['ok'] for v in filt.values())} of {len(filt)} (a, b) degenerate to C(a,b+1) and C(a,b-1); "
                    f"negative weights {sum(v['negative'] for v in filt.values())}"),
        "lemma41_star": f"terms in the starred block (weight +1, dropped): {star_total}",
        "lemma42": (f"{sum(v['ok'] for v in trip.values())} of {len(trip)} (a, h) degenerate to the three sectors; "
                    f"negative weights {sum(v['negative'] for v in trip.values())}, crossed terms "
                    f"{sum(v['crossed'] for v in trip.values())}"),
        "lemma51": (f"least P(a,a) on the 24 x 96 grid at least a^(4/3) for a = 2 to 24: {yn(lp_ok)}; at a = 24 "
                    f"{lp[GRID_A][0]:.3f} against {GRID_A ** (4 / 3):.3f}; residuals below 1e-6: "
                    f"{yn(worst_viol < 1e-6)}"),
        "lemma51_margin": round(lp_margin, 4),
        "lemma51_proof": (f"least P(a,a) minus the proof's bound a H_a, a = 2 to 24: smallest {lp_vs_proof:.3f}"),
        "rank42": f"R(C(a,b)) = a + b - 1 by interpolation and the output flattening, a, b = 1 to 6: {yn(rank_ok)}",
        "h_bound": (f"(1 + 1/(3m))^3 >= 1 + 1/m for m to 2,000: {yn(elem_ok)}; H_a^3 >= a for a to 100,000: "
                    f"{yn(h_ok)}"),
        "t_bound": "t allowed by a^(4/3) <= (2a-1)^(1/t): " + ", ".join(f"{v:.5f} at a = 10^{int(round(math.log10(a)))}"
                                                                        for a, v in tb.items()),
        "copies": "fewest copies that separate a seed-drawn A: " + ", ".join(f"M = {M}: {L}" for M, L in fewest.items())
                  + " (the paper uses 5M)",
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for key, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")
        if isinstance(v, float) and not math.isfinite(v):
            raise AssertionError(f"{key}: not finite")
    detail = {"conditions": cond, "controls": ctl, "control_detail": ctl_info,
              "prop31": {f"{M}/{n}": v for (M, n), v in prop.items()},
              "lemma41": {f"{a}/{b}": v for (a, b), v in filt.items()},
              "lemma42": {f"{a}/{h}": v for (a, h), v in trip.items()},
              "lemma51": {str(a): {"min": v, "residual": r, "a43": a ** (4 / 3), "proof": proof_bound[a]}
                          for a, (v, r) in lp.items()},
              "t_bound": {str(a): v for a, v in tb.items()}, "fewest_copies": fewest, "test": TEST}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, default=str)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"omega94: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
