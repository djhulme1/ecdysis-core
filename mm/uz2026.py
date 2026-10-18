#!/usr/bin/env python3
"""Uznanski's rectangular bounds: the paper's finite constructions built as printed and checked exactly, and its
passage from the angular constraint to the exponent bounds checked on a grid.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from Przemyslaw Uznanski, "Rectangular matrix
multiplication from polynomial products", arXiv:2610.10494v2 (11 October 2026; CC BY 4.0; the note says its proofs
and writeup were obtained through OpenAI Codex), its abstract: "In this note, we extend the matrix-multiplication
analysis by OpenAI to rectangular products and prove omega(1,k,1) <= 2 for 0 <= k <= 1/2, and
omega(1,k,1) <= 1 + k + 1/(4k) for k >= 1/2." It extends OpenAI's omega <= 9/4 (the lab's mm/omega94.py,
ext:3202cd30bbb8b971). The proof joins four explicit degenerations (its Lemma 2.1 (1)-(3) and Lemma 2.2, proved in
its Appendices C, A, B and E), multinomial counting and rescaling (Sections 3 and 4), an angular constraint on a
tensor character's three dot-product parameters (Proposition 4.2), Strassen's spectral theorem, and a final
optimisation (Section 5): with p_i = cos^2(theta_i), sum theta_i >= pi/2, Wolstenholme's inequality bounds
a p_1 + b p_2 + c p_3 by Theorem 1.1's formula. No finite computation reaches the spectral theorem or the limits of
Sections 3 and 4; this module builds every finite construction exactly on small cases, as printed, and checks the
final optimisation numerically on a grid of shapes.

The input is the paper's e-print (v2), checked against its size and SHA-256; its TeX is read only for the strings in
PRINTED_TEX (the constructions, the theorem and corollary, the table and the applications' numbers), and the run is
refused if one is missing. The constructions themselves are transcribed below from the TeX. Every rule below was
fixed before any construction of the paper was built or any optimisation solved; the tests exercise the machinery
on other inputs (other phases, other coordinate changes, other objectives).

A degeneration (the paper's Section 2): after linear substitutions on the three legs, every coefficient is a
polynomial in epsilon and its value at epsilon = 0 is the target. Here each construction is built as a trilinear form
whose coefficients are tracked as exact Laurent polynomials in epsilon (or, where the paper's scalings are monomial
weights, as integer weights per variable), and it holds for an instance if no coefficient has a negative power of
epsilon, the degree is at most the paper's bound where it states one, and the epsilon^0 part is exactly the target.

1. Finite separation (Lemma 2.1 (1), Appendix C), for M = 1 to 4: a tensor T = sum_h T_h with a common first leg
   (x_a, n_x = 3) and disjoint, matched sectors on the other two (y_(h,b), z_(h,c), each of 1 or 2 coordinates), with
   integer coefficients in [-3, 3] drawn from the seed (each T_h nonzero); L = 2M copies l = 0..L-1, zeta a
   primitive Lth root of unity (exactly: Z[zeta] as integer vectors modulo the Lth cyclotomic polynomial; every
   primitive root is a Galois conjugate of this one), and the printed substitutions
       x_a^(l) -> sum_g zeta^(l g) X_(a,g),   y_(h,b)^(l) -> sum_u zeta^(l(u-h)) Y_(h,b,u),
       z_(h,c)^(l) -> (1/L) sum_v zeta^(-l v) Z_(h,c,v),   g, u, v in 1..M;
   weights as printed: g^2 on X_(a,g), 2hu - h^2 on Y_(h,b,u), -2hv on Z_(h,c,v). It holds for the instance if every
   surviving term has g + u = h + v, weight (g - h)^2 >= 0, at most (M - 1)^2, and the weight-zero part is exactly
   sum mu_(h,a,b,c) X_(a,h) Y_(h,b,u) Z_(h,c,u) over u = 1..M, the direct sum over h of T_h tensor B_X(M) (each
   block's variables carry h on all three legs). Three instances for each M.
2. The two-sector splitting (Lemma 2.1 (2), Appendix A), for r = 1 to 5 and s = 2 to 6: C_XY(r,s) tensor B_X(2) as
   (f, (a, b)) -> (fa, fb), deg f < r, deg a, deg b < s; the printed coordinates p = a + tb, h = b - p_(e+1) t^e on
   the input pair (e = s - 1) and on the output pair (e = r + s - 2); the input h scaled by epsilon^-1 and the output
   h coordinate by epsilon. It holds if the coordinates are invertible as printed (b = h + p_(e+1) t^e, a = p - tb),
   the map in them is the printed (p, h) -> (fp, fh + p_s t^(s-1)(f - f_(r-1) t^(r-1))) term for term, no coefficient
   has a negative power of epsilon, and the epsilon^0 part is exactly C_XY(r,s+1) on (f, p, P) and C_XY(r,s-1) on
   (f, h, H), sharing the first leg.
3. The three-sector splitting (Lemma 2.1 (3), Appendix B), for r, s = 1 to 6: C_XY(r, 3s+r-1) with the printed
   intervals (Y: [0,s-1], [s,2s+r-2], [2s+r-1,3s+r-2]; Z: [0,s+r-2], [s+r-1,2s+r-2], [2s+r-1,3s+2r-3]), middle Y
   scaled by epsilon and middle Z by epsilon^-1. It holds if the intervals partition each leg's indices, no term has a
   negative power, and the epsilon^0 part is three matched sectors sharing X: the outer two C_XY(r,s) by translation,
   the middle exactly the printed sum_(u<r, v<s) x_(r-1-u) y_(s+u+v) z_(s+r-1+v), which is C_XZ(r,s) after reversing
   its first-leg basis.
4. Replication (Lemma 2.2, Appendix E), for m = 1 to 5 and r, s = 1 to 3: C_XY(mr, ms) with P(t) = t^m - 1, the inputs
   in the printed coordinates F = sum_a F_a P^a and G = sum_b G_b P^b (deg F_a, G_b < m), each block in its values at
   the m roots of P (exactly in Q(zeta_m), the roots zeta^h, h = 0..m-1); the output's blocks H_c, 0 <= c < r+s-1,
   in their values at the roots, the top block dropped; input blocks scaled by epsilon^-a, epsilon^-b and output block
   c by epsilon^c. It holds if the block coordinates are invertible (the basis t^d P^a has distinct leading degrees
   ma + d), the retained output coordinates number m(r+s-1) <= m(r+s) - 1, no coefficient has a negative power of
   epsilon, the degree is at most one, and the epsilon^0 part is exactly m independent copies of C_XY(r,s), one at each
   root.
5. The exponent bound (Theorem 1.1 from Proposition 4.2): for every shape a >= b >= c >= 0 on the grid a = 1,
   b = 0, 0.02, ..., 1, c = 0, 0.02, ..., b (the bound and the objective are homogeneous of degree one), the largest
   a p_1 + b p_2 + c p_3 over p_i = cos^2(theta_i), theta_i in [0, pi/2], theta_1 + theta_2 + theta_3 = pi/2 (larger
   sums only lower the objective, as the proof says), found on a 401-point grid of theta_1 and theta_2 and refined by
   SLSQP from the best grid point, is at most the theorem's bound plus 1e-9: a + b if c <= ab/(a+b), else
   (a+b+c)/2 + (ab/c + ac/b + bc/a)/4.
6. The curve (Corollary 1.2): Theorem 1.1 applied to the sorted dimensions of (1, k, 1) gives 2 for k <= 1/2 and
   1 + k + 1/(4k) above, in exact fractions at k = 0, 1/100, ..., 4; and the printed table (2, 2.0166..., 2.1125, 2.25,
   2.6666..., 3.125 at k = 0.5, 0.6, 0.8, 1, 1.5, 2) is the curve's values, each cut or rounded to its printed digits.
7. The test (TEST): refuted if any instance of 1 to 4 fails, or 5 or 6 fails.

Beside the test, none of it counted: the gap between the theorem's bound and the largest objective found, counted
where it is below 1e-6 (the bound is attained where the weights sqrt(bc/a), sqrt(ac/b), sqrt(ab/c) satisfy the
triangle inequality, which is exactly c >= ab/(a+b), and on the first branch at theta_3 = pi/2); the six applications' numbers from the curve and the
balances the paper states (lowest common ancestors, omega(x) = 3x, x = (1 + sqrt 3)/4 and exponent (3 + sqrt 3)/2;
Hamming distance, rho = omega(4 - rho) = (13 - sqrt 7)/4; Zwick's 2 + mu with omega(mu) <= 1 + 2 mu at mu = 1/2;
witnesses n^(1 - r + omega(r)) + n^(2 + r) at r = 1/2; sparse products m^2/n^r + n^omega(r) at m = n^1.25, r = 1/2;
and the dynamic inverse, max{u + v, omega(1,u,v) - u, omega(v) - v} at the printed u and v, against the printed
1.30992); the known points of the asymptotic spectrum, the quantum functionals, whose dot-product parameters on
B_i(q) are p_i = 1 - th_i for th on the probability simplex, against the angular constraint on a 201-point grid of
the simplex (the least slack at least -1e-12, and within 1e-12 of zero on its edges); and the fewest copies the separation's filter needs, 2M - 1 (any
L > 2(M - 1)), against the printed 2M.

Controls (controls_passed counts those that behave as stated): sum_l zeta^(lk) is L or 0 in Z[zeta] for L = 2 to 16
and |k| <= 3L; the separation engine with the phase of z planted as zeta^(l v), with the weight of Z planted as +2hv,
and with too few copies (L = 2M - 2 at M = 3) is caught in each case; the two-sector splitting with its output
scaling planted as epsilon^-1, and with the correction p_(e+1) t^e left out of h, is caught; the three-sector splitting
with its middle Z weight planted as +1 is caught; the replication with its output block scaling planted as
epsilon^-c, and with its input scaling left out, is caught; Q(zeta_m) is a field for these m (zeta^m = 1, and the
Lagrange basis at the roots is the identity on them); the optimiser finds 9/4 at a = b = c = 1 within 1e-9; and with
the constraint weakened to sum theta_i = pi/3 the largest objective exceeds the theorem's bound at a = b = c = 1 (the
constraint carries the bound).

What it cannot check: Proposition 4.2 itself (its proof passes through limits of the character's convolution
profiles), Strassen's spectral theorem, the counting and rescaling of Sections 3 and 4, Lemma 5.1's passage from
character bounds to algorithms, the constructions beyond the sizes tried, and the Alman and Vassilevska Williams
combination behind the O(n^2.4999).

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 mm/uz2026.py (the pinned scipy-notebook image, for numpy and scipy).
"""

import gzip
import hashlib
import io
import json
import math
import os
import random
import re
import sys
import tarfile
import time
from fractions import Fraction

import numpy as np
from scipy.optimize import minimize

EPRINT = ("arXiv-2610.10494v2.tar.gz", "3ba6f6bb4860c7f1eda3fdfc7b5cec5e9c2b7d87bea2e4d646e2faedf2d58f8a", 39550)
TEX_NAME = "main.tex"
M_RANGE = (1, 2, 3, 4)
INSTANCES = 3
NX = 3
SECTOR_DIMS = (1, 2)
COEFF = 3
TWO_R = range(1, 6)
TWO_S = range(2, 7)
THREE_RS = range(1, 7)
REP_M = range(1, 6)
REP_RS = range(1, 4)
GRID_STEP = Fraction(1, 50)
THETA_GRID = 401
TOL = 1e-9
K_STEP = Fraction(1, 100)
K_MAX = 4
TABLE = (("0.5", "2"), ("0.6", "2.0166"), ("0.8", "2.1125"), ("1", "2.25"), ("1.5", "2.6666"), ("2", "3.125"))
SIMPLEX_GRID = 201
LIMIT = 200

TEST = ("Refuted if one of the paper's finite constructions, built as printed, fails on small cases: the finite "
        "separation of its Appendix C (2M copies, M = 1 to 4, seed-drawn integer blocks, exactly in Z[ζ]), the "
        "two-sector splitting of Appendix A (r = 1 to 5, s = 2 to 6), the three-sector splitting of Appendix B "
        "(r, s = 1 to 6) or the replication of Appendix E (m = 1 to 5, r, s = 1 to 3, exactly in Q(ζ_m)); or if, on a "
        "grid of shapes, the largest ap₁ + bp₂ + cp₃ the angular constraint allows exceeds Theorem 1.1's bound, or "
        "Corollary 1.2's curve or table departs from it.")

PRINTED_TEX = [
    r"a+b,&c\le\dfrac{ab}{a+b},\\[4pt]",
    r"\dfrac{a+b+c}{2} +\dfrac{1}{4}\left(\dfrac{ab}{c}+\dfrac{ac}{b}+\dfrac{bc}{a}\right), &c>\dfrac{ab}{a+b}.",
    r"1+k+\dfrac1{4k},&k\ge\frac{1}{2}.",
    r"$\omega(k)\le$ & $2$ & $2.0166\ldots$ & $2.1125$ & $2.25$ & $2.6666\ldots$ & $3.125$\\",
    r"\sum_{i=1}^3\arccos\sqrt{p_i}\ge\frac{\pi}{2}.",
    r"p=a+tb,\qquad h=b-p_{e+1}t^e,\qquad p_d=[t^d]p.",
    r"Use them on the input pair with $e=s-1$ and on the output pair with $e=r+s-2$.",
    r"\bigl(fp,\,fh+p_s t^{s-1}(f-f_{r-1}t^{r-1})\bigr).",
    r"Scale input $h$ by $\varepsilon^{-1}$ and its output coordinate by $\varepsilon$.",
    r"Y &[0,s-1]&[s,2s+r-2]&[2s+r-1,3s+r-2]\\",
    r"Z &[0,s+r-2]&[s+r-1,2s+r-2]&[2s+r-1,3s+2r-3].",
    r"Scale middle $Y$ variables by $\varepsilon$ and middle $Z$ variables by $\varepsilon^{-1}$",
    r"x_{r-1-u}y_{s+u+v}z_{s+r-1+v},",
    r"Take $L=2M$ copies and a primitive $L$-th root of unity $\zeta$.",
    r"x_a^{(\ell)}&\longmapsto\sum_{g=1}^M\zeta^{\ell g}X_{ag},\\",
    r"y_{hb}^{(\ell)}&\longmapsto\sum_{u=1}^M\zeta^{\ell(u-h)}Y_{hbu},\\",
    r"z_{hc}^{(\ell)}&\longmapsto\frac1L\sum_{v=1}^M \zeta^{-\ell v}Z_{hcv}.",
    r"$g^2$, $2hu-h^2$, and $-2hv$",
    r"most $(M-1)^2$",
    r"Put $P(t)=t^m-1$.",
    r"On the output retain the analogous blocks $H_c$ for $0\le c<r+s-1$.",
    r"Scale input blocks $a,b$ by $\varepsilon^{-a},\varepsilon^{-b}$ and output block $c$ by $\varepsilon^c$.",
    r"$x=(1+\sqrt3)/4$",
    r"$(3+\sqrt3)/2\approx2.36603$",
    r"$\rho=(13-\sqrt7)/4\approx2.58856$",
    r"$u=0.50323551$ and $v=0.80667763$",
    r"$O(n^{1.30992})$",
    r"Thus $m\le n^{1.25}$ permits $O(n^2)$ time.",
    r"Taking $r=\frac{1}{2}$ gives $O(n^{2.5})$ time for all witnesses.",
]


class Refused(Exception):
    pass


def seeded(seed, label):
    return random.Random(int.from_bytes(hashlib.sha256(f"{seed}/{label}".encode()).digest(), "big"))


# ----------------------------------------------------------------------------------------------- the e-print

def flatten_tex(tex):
    lines = [re.sub(r"(?<!\\)%.*$", "", line) for line in tex.split("\n")]
    return re.sub(r"\s+", "", "\n".join(lines))


def read_source(path):
    with open(path, "rb") as fh:
        blob = fh.read()
    name, sha, size = EPRINT
    if len(blob) != size or hashlib.sha256(blob).hexdigest() != sha:
        raise Refused("the e-print does not match its pinned size and SHA-256")
    tf = tarfile.open(fileobj=io.BytesIO(gzip.decompress(blob)))
    members = {m.name: m for m in tf.getmembers() if m.isfile()}
    if TEX_NAME not in members:
        raise Refused("the e-print lacks main.tex")
    flat = flatten_tex(tf.extractfile(members[TEX_NAME]).read().decode("utf-8"))
    missing = [s for s in PRINTED_TEX if re.sub(r"\s+", "", s) not in flat]
    if missing:
        raise Refused(f"the TeX does not print: {missing[:2]}")
    return len(PRINTED_TEX)


# ----------------------------------------------------------------------------------------------- integer polynomials

def poly_divmod(num, den):
    """Integer (or rational) polynomials, lowest degree first; den monic."""
    num = list(num)
    if len(num) < len(den):
        return [0], [x for x in num]
    q = [0] * (len(num) - len(den) + 1)
    for i in range(len(num) - len(den), -1, -1):
        c = num[i + len(den) - 1]
        q[i] = c
        if c:
            for j, d in enumerate(den):
                num[i + j] -= c * d
    r = num[:len(den) - 1]
    return q, r


def cyclotomic(n, memo={}):
    """Phi_n by x^n - 1 = prod over d | n of Phi_d."""
    if n in memo:
        return memo[n]
    p = [-1] + [0] * (n - 1) + [1]
    for d in range(1, n):
        if n % d == 0:
            p, r = poly_divmod(p, cyclotomic(d))
            assert not any(r)
    while p and p[-1] == 0:
        p.pop()
    memo[n] = p
    return p


def reduce_mod(vec, L):
    """A combination of zeta^0 .. zeta^(k) reduced modulo Phi_L: a tuple of phi(L) coefficients."""
    phi = cyclotomic(L)
    n = len(phi) - 1
    vec = list(vec)
    if len(vec) > n:
        _, r = poly_divmod(vec, phi)
    else:
        r = vec
    out = list(r) + [0] * (n - len(r))
    return tuple(out[:n])


def char_sum(k, L):
    """sum over l = 0..L-1 of zeta^(lk), exactly, as a reduced vector."""
    vec = [0] * L
    for l in range(L):
        vec[(l * k) % L] += 1
    return reduce_mod(vec, L)


# ----------------------------------------------------------------------------------------------- 1. the separation

PHASES = {"x": lambda l, g: l * g, "y": lambda l, h, u: l * (u - h), "z": lambda l, h, v: -l * v}
WEIGHTS = {"x": lambda g: g * g, "y": lambda h, u: 2 * h * u - h * h, "z": lambda h, v: -2 * h * v}


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


def separate(T, M, L, phases=PHASES, weights=WEIGHTS):
    """The L copies of T under the substitutions, summed: {(a, g, h, b, u, c, v): (vector, weight)}, the vector the
    exact multiple of 1/L in Z[zeta_L] (the 1/L of the z substitution kept aside)."""
    out, cache = {}, {}
    for (h, a, b, c), coeff in T.items():
        for g in range(1, M + 1):
            for u in range(1, M + 1):
                for v in range(1, M + 1):
                    key = (g, h, u, v)
                    if key not in cache:
                        vec = [0] * L
                        for l in range(L):
                            vec[(phases["x"](l, g) + phases["y"](l, h, u) + phases["z"](l, h, v)) % L] += 1
                        cache[key] = reduce_mod(vec, L)
                    s = cache[key]
                    if any(s):
                        w = weights["x"](g) + weights["y"](h, u) + weights["z"](h, v)
                        out[(a, g, h, b, u, c, v)] = (tuple(coeff * x for x in s), w)
    return out


def check_separation(T, M, L, phases=PHASES, weights=WEIGHTS):
    S = separate(T, M, L, phases, weights)
    n = len(cyclotomic(L)) - 1
    unit = tuple([L] + [0] * (n - 1))                       # L as a vector: the 1/L then gives 1
    filtered = [k for k in S if k[1] + k[4] != k[2] + k[6]]
    negative = [k for k, (vec, w) in S.items() if w < 0]
    wrong = [k for k, (vec, w) in S.items() if w != (k[1] - k[2]) ** 2]
    high = [k for k, (vec, w) in S.items() if w > (M - 1) ** 2]
    zero = {k: vec for k, (vec, w) in S.items() if w == 0}
    expected = {}
    for (h, a, b, c), coeff in T.items():
        for u in range(1, M + 1):
            expected[(a, h, h, b, u, c, u)] = tuple(coeff * x for x in unit)
    zero_ok = zero == expected
    ok = not filtered and not negative and not wrong and not high and zero_ok
    return {"ok": ok, "terms": len(S), "weight_zero_terms": len(zero), "expected_terms": len(expected),
            "outside_filter": len(filtered), "negative": len(negative), "wrong_weight": len(wrong),
            "above_degree": len(high), "weight_zero_ok": zero_ok,
            "max_weight": max((w for _, w in S.values()), default=0)}


# ----------------------------------------------------------------------------------------------- convolutions

def C(r, s):
    """{(i, j, k): 1}: sum over i < r, j < s of x_i y_j z_(i+j) (C_XY(r, s))."""
    return {(i, j, i + j): 1 for i in range(r) for j in range(s)}


def pmul(p, q):
    if not p or not q:
        return []
    out = [0] * (len(p) + len(q) - 1)
    for i, x in enumerate(p):
        if x:
            for j, y in enumerate(q):
                if y:
                    out[i + j] += x * y
    return out


def padd(p, q):
    n = max(len(p), len(q))
    return [(p[i] if i < len(p) else 0) + (q[i] if i < len(q) else 0) for i in range(n)]


def pscale(p, c):
    return [c * x for x in p]


def coeff(p, d):
    return p[d] if 0 <= d < len(p) else 0


def mono(d):
    return [0] * d + [1]


# ----------------------------------------------------------------------------------------------- 2. two sectors

def to_ph(a, b, e):
    """The printed coordinates: p = a + t b, h = b - p_(e+1) t^e (deg a, b <= e)."""
    p = padd(a, [0] + list(b))
    h = padd(b, pscale(mono(e), -coeff(p, e + 1)))
    return p, h


def from_ph(p, h, e, correction=True):
    """The printed inverse: b = h + p_(e+1) t^e, a = p - t b."""
    b = padd(h, pscale(mono(e), coeff(p, e + 1))) if correction else list(h)
    a = padd(p, pscale([0] + list(b), -1))
    return a, b


def trim(p):
    p = list(p)
    while p and p[-1] == 0:
        p.pop()
    return p


def two_sector(r, s, in_scale=-1, out_scale=1, correction=True):
    """C_XY(r,s) tensor B_X(2) in the printed coordinates: {(i, kind_in, k, kind_out, d): (coefficient, epsilon power)}
    over the first-leg monomials f = t^i, input basis vectors (p = t^k or h = t^k) and output coordinates (P_d, H_d)."""
    e_in, e_out = s - 1, r + s - 2
    terms = {}
    inputs = [("p", k) for k in range(s + 1)] + [("h", k) for k in range(s - 1)]
    for i in range(r):
        f = mono(i)
        for kind, k in inputs:
            p, h = (mono(k), []) if kind == "p" else ([], mono(k))
            a, b = from_ph(p, h, e_in, correction)
            fa, fb = pmul(f, a), pmul(f, b)
            P, H = to_ph(fa, fb, e_out)
            for kind_out, poly, w_out in (("P", P, 0), ("H", H, out_scale)):
                for d, x in enumerate(poly):
                    if x:
                        terms[(i, kind, k, kind_out, d)] = (x, (in_scale if kind == "h" else 0) + w_out)
    return terms


def check_two_sector(r, s, **kw):
    terms = two_sector(r, s, **kw)
    e_in, e_out = s - 1, r + s - 2
    # the coordinates as printed: invertible, the round trip the identity on random pairs
    rng = random.Random(1000 * r + s)
    inverse_ok, printed_ok = True, True
    for _ in range(5):
        a = [rng.randint(-4, 4) for _ in range(s)]
        b = [rng.randint(-4, 4) for _ in range(s)]
        p, h = to_ph(a, b, e_in)
        a2, b2 = from_ph(p, h, e_in)
        inverse_ok &= trim(a2) == trim(a) and trim(b2) == trim(b) and len(trim(p)) <= s + 1 and len(trim(h)) <= s - 1
        f = [rng.randint(-4, 4) for _ in range(r)]
        P, H = to_ph(pmul(f, a), pmul(f, b), e_out)
        want_P = pmul(f, p)
        cross = pscale(pmul(mono(s - 1), padd(f, pscale(mono(r - 1), -coeff(f, r - 1)))), coeff(p, s))
        want_H = padd(pmul(f, h), cross)
        printed_ok &= trim(P) == trim(want_P) and trim(H) == trim(want_H)
    negative = [k for k, (x, w) in terms.items() if w < 0]
    zero = {k: x for k, (x, w) in terms.items() if w == 0}
    plus = {(i, k, d): x for (i, kind, k, ko, d), x in zero.items() if kind == "p" and ko == "P"}
    minus = {(i, k, d): x for (i, kind, k, ko, d), x in zero.items() if kind == "h" and ko == "H"}
    crossed_zero = [k for k in zero if (k[1] == "p") != (k[3] == "P")]
    cross_terms = {(i, k, d): x for (i, kind, k, ko, d), (x, w) in terms.items() if kind == "p" and ko == "H"}
    want_cross = {(i, s, s - 1 + i): 1 for i in range(r - 1)}
    ok = (inverse_ok and printed_ok and not negative and not crossed_zero and plus == C(r, s + 1)
          and minus == C(r, s - 1) and cross_terms == want_cross)
    return {"ok": ok, "terms": len(terms), "inverse_ok": inverse_ok, "printed_ok": printed_ok,
            "negative": len(negative), "plus_ok": plus == C(r, s + 1), "minus_ok": minus == C(r, s - 1),
            "cross_terms": len(cross_terms), "cross_ok": cross_terms == want_cross}


# ----------------------------------------------------------------------------------------------- 3. three sectors

def tripling_parts(r, s):
    Y = [(0, s - 1), (s, 2 * s + r - 2), (2 * s + r - 1, 3 * s + r - 2)]
    Z = [(0, s + r - 2), (s + r - 1, 2 * s + r - 2), (2 * s + r - 1, 3 * s + 2 * r - 3)]
    return Y, Z


def part_of(x, parts):
    return next((n for n, (lo, hi) in enumerate(parts) if lo <= x <= hi), None)


def three_sector(r, s, ymid=1, zmid=-1):
    B = 3 * s + r - 1
    Y, Z = tripling_parts(r, s)
    partitions = (all(sum(1 for lo, hi in Y if lo <= y <= hi) == 1 for y in range(B))
                  and all(sum(1 for lo, hi in Z if lo <= z <= hi) == 1 for z in range(r + B - 1))
                  and all(lo <= hi for lo, hi in Y + Z))
    terms = C(r, B)
    weight = lambda y, z: (ymid if part_of(y, Y) == 1 else 0) + (zmid if part_of(z, Z) == 1 else 0)
    negative = [t for t in terms if weight(t[1], t[2]) < 0]
    crossed = [t for t in terms if weight(t[1], t[2]) > 0]
    zero = {t for t in terms if weight(t[1], t[2]) == 0}
    sectors = {n: {t for t in zero if part_of(t[1], Y) == n} for n in range(3)}
    matched = all(part_of(t[2], Z) == part_of(t[1], Y) for t in zero)
    base = set(C(r, s))
    left_ok = sectors[0] == base
    off = 2 * s + r - 1
    right_ok = {(i, y - off, z - off) for i, y, z in sectors[2]} == base
    printed_middle = {(r - 1 - u, s + u + v, s + r - 1 + v) for u in range(r) for v in range(s)}
    middle_printed = sectors[1] == printed_middle
    # C_XZ(r,s) = sum x_u z_v y_(u+v): reverse the first leg (x_(r-1-u) -> x'_u), z_(s+r-1+v) -> z'_v, y_(s+u+v) -> y'_(u+v)
    c_xz = {(u, u + v, v) for u in range(r) for v in range(s)}         # (x index, y index, z index)
    mapped = {(r - 1 - i, y - s, z - (s + r - 1)) for i, y, z in sectors[1]}
    middle_iso = mapped == c_xz
    ok = partitions and not negative and matched and left_ok and right_ok and middle_printed and middle_iso
    return {"ok": ok, "partitions": partitions, "negative": len(negative), "crossed": len(crossed),
            "matched": matched, "left": left_ok, "right": right_ok, "middle_printed": middle_printed,
            "middle_iso": middle_iso, "sizes": [len(sectors[n]) for n in range(3)]}


# ----------------------------------------------------------------------------------------------- Q(zeta_m)

class Cyc:
    """Exact arithmetic in Q(zeta_m): coefficient tuples of Fractions over 1, zeta, ..., zeta^(phi(m)-1)."""

    def __init__(self, m):
        self.m = m
        self.phi = cyclotomic(m)
        self.n = len(self.phi) - 1

    def reduce(self, vec):
        vec = [Fraction(x) for x in vec]
        phi = self.phi
        for i in range(len(vec) - 1, self.n - 1, -1):
            c = vec[i]
            if c:
                for j, d in enumerate(phi):
                    vec[i - self.n + j] -= c * d
        out = vec[:self.n] + [Fraction(0)] * (self.n - len(vec[:self.n]))
        return tuple(out)

    def zero(self):
        return tuple([Fraction(0)] * self.n)

    def one(self):
        return self.reduce([1])

    def zeta_pow(self, k):
        return self.reduce(mono(k % self.m))

    def add(self, x, y):
        return tuple(a + b for a, b in zip(x, y))

    def neg(self, x):
        return tuple(-a for a in x)

    def mul(self, x, y):
        out = [Fraction(0)] * (2 * self.n - 1)
        for i, a in enumerate(x):
            if a:
                for j, b in enumerate(y):
                    if b:
                        out[i + j] += a * b
        return self.reduce(out)

    def scale(self, x, c):
        return tuple(a * c for a in x)

    def is_zero(self, x):
        return not any(x)


def cpoly_mul(K, p, q):
    if not p or not q:
        return []
    out = [K.zero() for _ in range(len(p) + len(q) - 1)]
    for i, x in enumerate(p):
        if not K.is_zero(x):
            for j, y in enumerate(q):
                if not K.is_zero(y):
                    out[i + j] = K.add(out[i + j], K.mul(x, y))
    return out


def cpoly_eval(K, p, z):
    acc = K.zero()
    for c in reversed(p):
        acc = K.add(K.mul(acc, z), c)
    return acc


def cpoly_divmod_P(K, p, m):
    """Divide by P = t^m - 1: (quotient, remainder of degree < m)."""
    p = list(p)
    q = [K.zero() for _ in range(max(len(p) - m, 0))]
    for i in range(len(p) - 1, m - 1, -1):
        c = p[i]
        if not K.is_zero(c):
            q[i - m] = K.add(q[i - m], c)
            p[i - m] = K.add(p[i - m], c)            # t^i = t^(i-m) (t^m - 1) + t^(i-m)
            p[i] = K.zero()
    return q, p[:m] + [K.zero() for _ in range(m - len(p[:m]))]


def p_adic_digits(K, p, m, count):
    """The digits H_0 .. H_(count-1) of p in base P = t^m - 1, each of degree < m."""
    digits = []
    cur = list(p)
    for _ in range(count):
        q, rem = cpoly_divmod_P(K, cur, m)
        digits.append(rem)
        cur = q
    return digits, cur


def lagrange_at_roots(K, m, h):
    """L_h(t) = (1/m) sum_k zeta^(-hk) t^k: 1 at zeta^h and 0 at the other roots of t^m - 1."""
    return [K.scale(K.zeta_pow(-h * k), Fraction(1, m)) for k in range(m)]


def P_power(K, m, a):
    P = [K.neg(K.one())] + [K.zero()] * (m - 1) + [K.one()]
    out = [K.one()]
    for _ in range(a):
        out = cpoly_mul(K, out, P)
    return out


def replication(m, r, s, in_scale=True, out_sign=1):
    """C_XY(mr, ms) pulled back to the printed coordinates: {(h, a), (h', b), (h'', c): {epsilon power: value}}."""
    K = Cyc(m)
    roots = [K.zeta_pow(h) for h in range(m)]
    X = {}
    for h in range(m):
        Lh = lagrange_at_roots(K, m, h)
        for a in range(r):
            X[(h, a)] = (cpoly_mul(K, Lh, P_power(K, m, a)), -a if in_scale else 0)
    Y = {}
    for h in range(m):
        Lh = lagrange_at_roots(K, m, h)
        for b in range(s):
            Y[(h, b)] = (cpoly_mul(K, Lh, P_power(K, m, b)), -b if in_scale else 0)
    n_out = r + s - 1
    form = {}
    for xk, (F, ea) in X.items():
        for yk, (G, eb) in Y.items():
            FG = cpoly_mul(K, F, G)
            if len(FG) > m * r + m * s - 1:
                raise AssertionError("the product exceeds the output length")
            digits, rest = p_adic_digits(K, FG, m, n_out + 1)
            for c in range(n_out):
                for h2 in range(m):
                    val = cpoly_eval(K, digits[c], roots[h2])
                    if not K.is_zero(val):
                        e = ea + eb + out_sign * c
                        form.setdefault((xk, yk, (h2, c)), {})
                        form[(xk, yk, (h2, c))][e] = K.add(form[(xk, yk, (h2, c))].get(e, K.zero()), val)
    return form, K


def leading_degrees_distinct(m, r):
    """The basis t^d P^a (d < m, a < r) has distinct leading degrees ma + d covering 0 .. mr - 1."""
    degs = sorted(m * a + d for a in range(r) for d in range(m))
    return degs == list(range(m * r))


def check_replication(m, r, s, **kw):
    form, K = replication(m, r, s, **kw)
    negative = [k for k, terms in form.items() for e, v in terms.items() if e < 0 and not K.is_zero(v)]
    degree = max((e for terms in form.values() for e, v in terms.items() if not K.is_zero(v)), default=0)
    zero = {k: terms.get(0) for k, terms in form.items() if 0 in terms and not K.is_zero(terms[0])}
    want = {((h, a), (h, b), (h, a + b)): K.one() for h in range(m) for a in range(r) for b in range(s)}
    zero_ok = zero == want
    coords_ok = leading_degrees_distinct(m, r) and leading_degrees_distinct(m, s) and m * (r + s - 1) <= m * (r + s) - 1
    ok = coords_ok and not negative and degree <= 1 and zero_ok
    return {"ok": ok, "terms": len(form), "negative": len(negative), "degree": degree, "zero_ok": zero_ok,
            "coords_ok": coords_ok}


# ----------------------------------------------------------------------------------------------- 5. the bound

def theorem_bound(a, b, c):
    """Theorem 1.1 for sorted a >= b >= c >= 0 (exact if given Fractions)."""
    if a == 0 and b == 0:
        return a + b
    c0 = (a * b) / (a + b) if (a + b) else 0
    if c <= c0:
        return a + b
    return (a + b + c) / 2 + (a * b / c + a * c / b + b * c / a) / 4


def objective(th1, th2, a, b, c, total=math.pi / 2):
    th3 = total - th1 - th2
    return a * np.cos(th1) ** 2 + b * np.cos(th2) ** 2 + c * np.cos(th3) ** 2


def best_objective(a, b, c, total=math.pi / 2, n=THETA_GRID):
    """The largest a cos^2 th1 + b cos^2 th2 + c cos^2 th3 with th_i >= 0, sum = total (th_i <= pi/2 holds then)."""
    g = np.linspace(0.0, total, n)
    T1, T2 = np.meshgrid(g, g, indexing="ij")
    mask = T1 + T2 <= total + 1e-15
    vals = np.where(mask, objective(T1, T2, a, b, c, total), -np.inf)
    idx = np.unravel_index(np.argmax(vals), vals.shape)
    x0 = np.array([T1[idx], T2[idx]])
    best = float(vals[idx])
    cons = [{"type": "ineq", "fun": lambda x: total - x[0] - x[1]}]
    res = minimize(lambda x: -objective(x[0], x[1], a, b, c, total), x0, method="SLSQP",
                   bounds=[(0.0, total), (0.0, total)], constraints=cons, options={"ftol": 1e-15, "maxiter": 500})
    if res.success or res.status in (0, 8, 9):
        x = np.clip(res.x, 0.0, total)
        if x[0] + x[1] > total:
            x = x * (total / (x[0] + x[1]))
        best = max(best, float(objective(x[0], x[1], a, b, c, total)))
    return best


def shape_grid():
    out = []
    n = int(1 / GRID_STEP)
    for i in range(n + 1):
        b = i * GRID_STEP
        for j in range(i + 1):
            c = j * GRID_STEP
            out.append((Fraction(1), b, c))
    return out


# ----------------------------------------------------------------------------------------------- 6. the curve

def curve(k):
    """Corollary 1.2, exactly."""
    k = Fraction(k)
    if k <= Fraction(1, 2):
        return Fraction(2)
    return 1 + k + 1 / (4 * k)


def theorem_at_1k1(k):
    a, b, c = sorted((Fraction(1), Fraction(k), Fraction(1)), reverse=True)
    return theorem_bound(a, b, c)


def cut_or_round(x, printed):
    """True if the exact value x, cut or rounded to the printed digits, reads as printed."""
    digits = len(printed.split(".")[1]) if "." in printed else 0
    q = Fraction(10) ** digits
    cut = Fraction(math.floor(x * q), q)
    rounded = Fraction(math.floor(x * q + Fraction(1, 2)), q)
    target = Fraction(printed)
    return cut == target or rounded == target


# ----------------------------------------------------------------------------------------------- beside: applications

def bisect(fn, lo, hi, steps=200):
    flo = fn(lo)
    for _ in range(steps):
        mid = (lo + hi) / 2
        fm = fn(mid)
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return (lo + hi) / 2


def applications():
    w = lambda k: 2.0 if k <= 0.5 else 1 + k + 1 / (4 * k)
    out = {}
    x = bisect(lambda x: w(x) - 3 * x, 0.5, 1.0)
    out["lca_x"] = (x, (1 + math.sqrt(3)) / 4)
    out["lca_exponent"] = (1 + 2 * x, (3 + math.sqrt(3)) / 2, 2.36603)
    rho = bisect(lambda r: r - w(4 - r), 2.0, 3.5)
    out["hamming_rho"] = (rho, (13 - math.sqrt(7)) / 4, 2.58856)
    out["zwick"] = (w(0.5), 1 + 2 * 0.5, 2 + 0.5)
    out["witnesses"] = (max(1 - 0.5 + w(0.5), 2 + 0.5), 2.5)
    out["sparse"] = (max(2 * 1.25 - 0.5, w(0.5)), 2.0)
    u, v = 0.50323551, 0.80667763
    a, b, c = sorted((1.0, u, v), reverse=True)
    dyn = max(u + v, theorem_bound(a, b, c) - u, w(v) - v)
    out["dynamic_inverse"] = (dyn, 1.30992)
    ok = {
        "lca": abs(x - (1 + math.sqrt(3)) / 4) < 1e-12 and abs(1 + 2 * x - 2.36603) < 5e-6,
        "hamming": abs(rho - (13 - math.sqrt(7)) / 4) < 1e-12 and abs(rho - 2.58856) < 5e-6,
        "zwick": w(0.5) <= 1 + 2 * 0.5 + 1e-15,
        "witnesses": abs(max(1 - 0.5 + w(0.5), 2 + 0.5) - 2.5) < 1e-15,
        "sparse": max(2 * 1.25 - 0.5, w(0.5)) <= 2.0 + 1e-15,
        "dynamic_inverse": dyn <= 1.30992 and 1.30992 - dyn < 1e-5,
    }
    return out, ok


def quantum_functionals(n=SIMPLEX_GRID):
    """The least slack of sum arccos sqrt(1 - th_i) - pi/2 over a grid of the probability simplex, and on its edges."""
    worst, edge_worst = math.inf, 0.0
    for i in range(n):
        for j in range(n - i):
            th = (i / (n - 1), j / (n - 1), (n - 1 - i - j) / (n - 1))
            slack = sum(math.acos(math.sqrt(max(0.0, 1 - t))) for t in th) - math.pi / 2
            worst = min(worst, slack)
            if 0 in (i, j, n - 1 - i - j):
                edge_worst = max(edge_worst, abs(slack))
    return worst, edge_worst


# ----------------------------------------------------------------------------------------------- the run

def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    path = os.path.join(inputs, EPRINT[0])
    if not os.path.exists(path):
        raise Refused(f"missing input {EPRINT[0]}")
    printed = read_source(path)
    timing, detail = {}, {}

    t0 = time.time()
    sep = {}
    for M in M_RANGE:
        for n in range(INSTANCES):
            T = random_block_tensor(M, seeded(seed, f"separation/{M}/{n}"))
            sep[f"M{M}/{n}"] = check_separation(T, M, 2 * M)
    sep_ok = all(v["ok"] for v in sep.values())
    timing["separation"] = round(time.time() - t0, 2)

    t0 = time.time()
    two = {f"r{r}/s{s}": check_two_sector(r, s) for r in TWO_R for s in TWO_S}
    two_ok = all(v["ok"] for v in two.values())
    three = {f"r{r}/s{s}": three_sector(r, s) for r in THREE_RS for s in THREE_RS}
    three_ok = all(v["ok"] for v in three.values())
    timing["splittings"] = round(time.time() - t0, 2)

    t0 = time.time()
    rep = {f"m{m}/r{r}/s{s}": check_replication(m, r, s) for m in REP_M for r in REP_RS for s in REP_RS}
    rep_ok = all(v["ok"] for v in rep.values())
    timing["replication"] = round(time.time() - t0, 2)

    t0 = time.time()
    shapes = shape_grid()
    excess, gaps, worst_shape, within, tight = -math.inf, [], None, 0, 0
    for a, b, c in shapes:
        bound = float(theorem_bound(a, b, c))
        best = best_objective(float(a), float(b), float(c))
        if best - bound > excess:
            excess, worst_shape = best - bound, (float(a), float(b), float(c))
        gaps.append(bound - best)
        within += best <= bound + TOL
        tight += bound - best < 1e-6
    theorem_ok = within == len(shapes)
    timing["theorem"] = round(time.time() - t0, 2)

    ks = [K_STEP * i for i in range(int(K_MAX / K_STEP) + 1)]
    curve_ok = all(curve(k) == theorem_at_1k1(k) for k in ks)
    table = {k: (str(curve(Fraction(k))), cut_or_round(curve(Fraction(k)), v)) for k, v in TABLE}
    table_ok = all(ok for _, ok in table.values())
    lower_ok = all(curve(k) >= max(2, 1 + k) for k in ks)

    cond = {
        "1. Appendix C's finite separation holds on every instance (2M copies, M = 1 to 4)": sep_ok,
        "2. Appendix A's two-sector splitting holds (r = 1 to 5, s = 2 to 6)": two_ok,
        "3. Appendix B's three-sector splitting holds (r, s = 1 to 6)": three_ok,
        "4. Appendix E's replication holds (m = 1 to 5, r, s = 1 to 3)": rep_ok,
        "5. the angular constraint allows no objective above Theorem 1.1's bound on the grid": theorem_ok,
        "6. Corollary 1.2's curve is the theorem at (1, k, 1), and its table reads as printed": curve_ok and table_ok,
    }

    # beside
    app_values, app_ok = applications()
    qf_worst, qf_edge = quantum_functionals()
    fewest = {}
    for M in (2, 3, 4):
        T = random_block_tensor(M, seeded(seed, f"fewest/{M}"))
        fewest[M] = {L: check_separation(T, M, L)["ok"] for L in (2 * M - 2, 2 * M - 1, 2 * M)}
    fewest_ok = all(v[2 * M - 1] and not v[2 * M - 2] for M, v in fewest.items())

    # controls
    t0 = time.time()
    ctl = {}
    ctl["(a) sum_l zeta^(lk) is L or 0 in Z[zeta], L = 2 to 16, |k| <= 3L"] = all(
        char_sum(k, L) == (tuple([L] + [0] * (len(cyclotomic(L)) - 2)) if k % L == 0 else
                           tuple([0] * (len(cyclotomic(L)) - 1)))
        for L in range(2, 17) for k in range(-3 * L, 3 * L + 1))
    T3 = random_block_tensor(3, seeded(seed, "control/separation"))
    bad_phase = dict(PHASES, z=lambda l, h, v: l * v)
    bad_weight = dict(WEIGHTS, z=lambda h, v: 2 * h * v)
    ctl["(b) the separation with a planted phase, a planted weight or too few copies is caught"] = (
        not check_separation(T3, 3, 6, phases=bad_phase)["ok"]
        and not check_separation(T3, 3, 6, weights=bad_weight)["ok"]
        and not check_separation(T3, 3, 4)["ok"])
    ctl["(c) the two-sector splitting with its output scaling or its correction planted is caught"] = (
        not check_two_sector(3, 4, out_scale=-1)["ok"] and not check_two_sector(3, 4, correction=False)["ok"])
    ctl["(d) the three-sector splitting with its middle Z weight planted as +1 is caught"] = \
        not three_sector(3, 2, zmid=1)["ok"]
    ctl["(e) the replication with its output scaling or its input scaling planted is caught"] = (
        not check_replication(3, 2, 2, out_sign=-1)["ok"] and not check_replication(3, 2, 2, in_scale=False)["ok"])
    field_ok = True
    for m in REP_M:
        K = Cyc(m)
        field_ok &= K.zeta_pow(m) == K.one() and cpoly_eval(K, [K.reduce([x]) for x in cyclotomic(m)],
                                                            K.zeta_pow(1)) == K.zero()
        for h in range(m):
            Lh = lagrange_at_roots(K, m, h)
            field_ok &= all(cpoly_eval(K, Lh, K.zeta_pow(j)) == (K.one() if j == h else K.zero()) for j in range(m))
    ctl["(f) Q(zeta_m): zeta^m = 1, Phi_m(zeta) = 0, and the Lagrange basis at the roots is the identity"] = field_ok
    ctl["(g) the optimiser finds 9/4 at a = b = c = 1 within 1e-9"] = abs(best_objective(1.0, 1.0, 1.0) - 2.25) < 1e-9
    ctl["(h) with sum theta = pi/3 the objective exceeds the bound at a = b = c = 1 (the constraint carries it)"] = \
        best_objective(1.0, 1.0, 1.0, total=math.pi / 3) > 2.25 + 1e-3
    timing["controls"] = round(time.time() - t0, 2)

    out = {
        "printed_strings": printed,
        "separation_instances": len(sep), "separation_ok": sum(v["ok"] for v in sep.values()),
        "separation_max_weight": max(v["max_weight"] for v in sep.values()),
        "two_sector_cases": len(two), "two_sector_ok": sum(v["ok"] for v in two.values()),
        "three_sector_cases": len(three), "three_sector_ok": sum(v["ok"] for v in three.values()),
        "replication_cases": len(rep), "replication_ok": sum(v["ok"] for v in rep.values()),
        "theorem_shapes": len(shapes), "theorem_within_bound": within, "theorem_tight": tight,
        "curve_points": len(ks), "curve_ok": int(curve_ok), "table_ok": int(table_ok), "lower_bound_ok": int(lower_ok),
        "applications_ok": sum(app_ok.values()), "applications_total": len(app_ok),
        "quantum_functionals_ok": int(qf_worst >= -1e-12 and qf_edge <= 1e-12),
        "fewest_copies_2M_minus_1": int(fewest_ok),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond),
        "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    for k, v in out.items():
        if isinstance(v, float) and not math.isfinite(v):
            raise AssertionError(f"{k}: not finite")
    detail = {"test": TEST, "conditions": cond, "controls": ctl, "timing": timing, "separation": sep,
              "two_sector": two, "three_sector": three, "replication": rep,
              "theorem": {"worst_shape": worst_shape, "excess": excess, "max_gap": max(gaps), "min_gap": min(gaps)},
              "table": table, "applications": {"values": app_values, "ok": app_ok},
              "quantum_functionals": {"min_slack": qf_worst, "edge_slack": qf_edge},
              "fewest_copies": {str(M): {str(L): ok for L, ok in v.items()} for M, v in fewest.items()}}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="utf-8") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, ensure_ascii=False, default=str)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"uz2026: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
