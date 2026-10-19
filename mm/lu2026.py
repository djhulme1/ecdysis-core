#!/usr/bin/env python3
r"""Lü's polynomial separation of a shared tensor leg (2026), built exactly over fields of every small characteristic.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from Houxi Lü, "Polynomial Separation of a
Shared Tensor Leg and Matrix Multiplication in Arbitrary Characteristic" (arXiv:2610.18914v1, 12 October 2026, CC BY
4.0), its abstract: "If $M$ tensor blocks have a common first space and independent matched sectors on their other
two spaces, then $M+n-1$ copies of their matched sum degenerate to the full direct sum of the blocks, each tensored
with an $n$-dimensional dot product." It is the paper's Proposition 2.1, which replaces Proposition 3.1 of OpenAI's
omega <= 9/4 (checked as mm/omega94.py) and needs only that F contain M + n - 1 distinct elements.

Data of record: the e-print (the bundle's one input, by hash). The module reads its TeX from the archive in memory
and confirms that it prints each formula transcribed below; the construction is then built from those formulas.

The construction, as the proof gives it. Distinct a_1..a_M in F; P = F[t]_<M, J = F[u]/(u^n), Q = F[t]_<n,
W = F[t]_<l with l = M + n - 1. sigma_h(p, j) = p(a_h + eps u) j in J[eps]; Phi(eps)(x(x)p, y_h(x)j, z_h(x)phi) =
A_h(x, y_h, z_h) phi(sigma_h(p, j)), zero on components with different Y- and Z-labels (its eq. 2.3). g_h: Q -> J[eps],
q -> q(a_h + eps u), and iota_h: W -> J[eps], f -> f(a_h + eps u). The pullback of A (x) C_mu, C_mu(p, q, psi) =
psi(pq), along alpha = id, beta = (+)_h (id (x) g_h^-1), gamma = (+)_h (id (x) iota_h^dual) is Phi(eps); and A (x) C_mu
is a restriction of A^(+l) by evaluation at distinct b_1..b_l and interpolation. At eps = 0, under id_X (x) e,
e(p) = (p(a_1), .., p(a_M)), Phi(0) is the direct sum of the A_h (x) B_X(n), B_X(n)(c, j, phi) = c phi(j). The paper's
remarks: g_h^-1 is j(u) -> j((t - a_h)/eps); Phi has degree at most min(M - 1, n - 1) in eps.

Rules, fixed before any instance was built (the tests exercise the machinery on other fields and blocks):

1. Fields: Q; F_2, F_3, F_5, F_7; F_4 = F_2[x]/(x^2 + x + 1), F_8 = F_2[x]/(x^3 + x + 1), F_16 = F_2[x]/(x^4 + x + 1),
   F_9 = F_3[x]/(x^2 + 1), F_27 = F_3[x]/(x^3 + 2x + 1). Every pair 1 <= M, n <= 5 with M + n - 1 <= |F|, so that the
   smallest fields the proposition admits are used whole (F_2 at M + n = 3, F_3 at 4, F_4 at 5, F_5 at 6, F_7 at 8,
   F_8 at 9). Two instances for each field and pair.
2. An instance: a common X of dimension 2; for each h, Y_h and Z_h of dimension 1 or 2; A_h with entries drawn from
   the seed (integers in [-3, 3] over Q, uniform elements of F otherwise; each A_h drawn again until nonzero); the
   points a_1..a_M and b_1..b_l distinct, drawn from the seed (distinct integers in [-6, 6] over Q).
3. The pullback, computed as the composition of linear maps it is: the first leg x_a (x) t^m -> sum_k b_k^m x_a^(k);
   the second y_(h,b) (x) u^s -> y_(h,b) (x) g_h^-1(u^s), with g_h^-1 the inverse of g_h's matrix over F[eps, eps^-1]
   (back substitution; its diagonal is eps^r), then y (x) t^i -> sum_k b_k^i y^(k); the third z_(h,c) (x) u^r* ->
   z_(h,c) (x) iota_h^dual(u^r*), then z (x) (t^w)* -> sum_k L_k[w] z^(k), L_k the Lagrange polynomials at the b's;
   and the form of A^(+l) (copy k of A on copy k of each leg) pulled back along them, as Laurent polynomials in eps.
   Phi(eps) separately, from eq. 2.3 with sigma_h expanded in F[eps][u]/(u^n).
4. The test's conditions for an instance: (i) the pullback is polynomial in eps; (ii) it equals Phi(eps), every
   coefficient; (iii) Phi(0), with the first leg in the basis x_a (x) La_h (La the Lagrange polynomials at the a's,
   so that e(La_h) is the h-th unit vector), is exactly the direct sum of the A_h (x) B_X(n): A_h(a, b, c) on
   (x_a (x) La_h, y_(h,b) (x) u^s, z_(h,c) (x) u^s*) and zero elsewhere; (iv) the degree in eps is at most
   min(M - 1, n - 1); (v) the evaluation-interpolation restriction reproduces C_mu exactly: sum_k b_k^(m+s) L_k[w] is
   1 when w = m + s and 0 otherwise. The test passes when every condition holds in every instance.

Beside the test, not counted: whether g_h^-1 is the printed j(u) -> j((t - a_h)/eps); whether the degree bound is
attained; the instances on the smallest admitted fields; the flattening rank of C_mu (l, so that fewer than l copies
of A cannot restrict to A (x) C_mu); the copies the separation needs for n = M, 2M - 1, against OpenAI's printed 5M
and the 3M - 2 its own construction needs (mm/omega94.py's beside item); and, for Section 4's claims of
characteristic independence, Lemma 4.1's determinant filtration over F_2, F_3 and F_5: the sequence
0 -> (uw - vs)V_(e-1) -> V_e (x) span(s, w) -> V_(e+1) -> 0 exact for e = 1 to 12, and mm/omega94.py's degeneration of
C(a,b) (x) B_X(2) rebuilt over F_p for a = 1 to 5, b = 2 to 6 (Lemma 4.2's tripling has no field arithmetic at all).

Controls (controls_passed counts those that behave as stated):
 (a) Each finite field's tables: associativity and distributivity on all triples (q <= 9) or 2,000 drawn ones,
     inverses, and an element of order q - 1 (so the modulus is irreducible).
 (b) Interpolation: sum_k f(b_k) L_k = f for drawn f of degree < l in every field.
 (c) Planted: one point too few (l - 1 evaluation points) breaks the restriction, caught in every instance with l >= 2.
 (d) Planted: g_h^-1 replaced by u^s -> t^s (no substitution) breaks the pullback, caught where n >= 2.
 (e) Planted: a crossed term A(x, y_1, z_2) != 0 is caught by (ii) and (iii), where M >= 2.
 (f) Planted: a_1 = a_2 leaves no Lagrange basis at the a's (e is singular), caught where M >= 2.
 (g) By hand: M = 2, n = 1 over Q with a = (0, 1), b = (0, 1): Phi(0) on x (x) t is A_2's block only.
 (h) The e-print prints the 14 formulas the rules transcribe.

Writes results/outputs.json and results/detail.json. Run with: python3 mm/lu2026.py
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
from fractions import Fraction

INPUT = ("lu-2610.18914v1.tar.gz", "b1dbe22d8f007f5c2623dd82306b59e848280d3be8a2788457d16a849befb838", 6377)
TEX_MEMBER = "paaaaaaper.tex"
FIELDS = [("Q", 0, 1, None), ("F2", 2, 1, None), ("F3", 3, 1, None), ("F4", 2, 2, (1, 1, 1)), ("F5", 5, 1, None),
          ("F7", 7, 1, None), ("F8", 2, 3, (1, 1, 0, 1)), ("F9", 3, 2, (1, 0, 1)), ("F16", 2, 4, (1, 1, 0, 0, 1)),
          ("F27", 3, 3, (1, 2, 0, 1))]          # modulus coefficients, constant term first (monic)
MN_MAX, INSTANCES, NX, COEFF, QPOINTS = 5, 2, 2, 3, 6
LEMMA41_P, LEMMA41_E, LEMMA41_A, LEMMA41_B = (2, 3, 5), 12, range(1, 6), range(2, 7)
PRINTED = [
    r"A^{\oplus(M+n-1)}\degen \bigoplus_{h=1}^M\bigl(A_h\otimes B_X(n)\bigr).",
    r"suppose that $F$ contains at least $M+n-1$ distinct elements.",
    r"A(x,y,z)=\sum_{h=1}^M A_h(x,y_h,z_h),",
    r"(c,j,\varphi)\longmapsto c\varphi(j),",
    r"P=F[t]_{<M},\qquad J=F[u]/(u^n),",
    r"\sigma_h(p,j)=p(a_h+\eps u)j\quad\text{in }J[\eps].",
    r"=A_h(x,y_h,z_h)\varphi\bigl(\sigma_h(p,j)\bigr),",
    r"Put $\ell=M+n-1$, $Q=F[t]_{<n}$ and $W=F[t]_{<\ell}$.",
    r"g_h:Q\longrightarrow J[\eps],\quad q\longmapsto q(a_h+\eps u),",
    r"\iota_h:W\longrightarrow J[\eps],\quad f\longmapsto f(a_h+\eps u).",
    r"\beta&=\bigoplus_h(\operatorname{id}_{Y_h}\otimes g_h^{-1}),",
    r"\gamma&=\bigoplus_h(\operatorname{id}_{Z_h}\otimes\iota_h^\vee).",
    r"=p(a_h)A_h(x,y_h,z_h)\varphi(j).",
    r"at most $\min(M-1,n-1)$ in $\eps$, since powers $u^n$ and higher vanish in $J$.",
]
TEST = ("Refuted if, over Q, F_2, F_3, F_4, F_5, F_7, F_8, F_9, F_16 or F_27, for M, n <= 5 with M + n - 1 <= |F| and "
        "seed-drawn blocks and distinct points (two instances each), the pullback of M + n - 1 copies of the matched "
        "sum along the paper's maps (evaluation at the b's and interpolation, then id, (+)(id (x) g_h^-1), (+)(id (x) "
        "iota_h^dual)) is not polynomial in eps, differs from eq. 2.3's Phi(eps), has eps-degree above min(M - 1, "
        "n - 1), or at eps = 0 is not, under id_X (x) e, the direct sum of the A_h (x) B_X(n); or the evaluation "
        "restriction does not reproduce C_mu.")
LIMIT = 200


class Refused(Exception):
    pass


def seeded(seed, label):
    return random.Random(int.from_bytes(hashlib.sha256(f"{seed}/{label}".encode()).digest(), "big"))


# ----------------------------------------------------------------------------------------------- fields
class Field:
    """Q (p = 0, elements Fractions) or GF(p^k) (elements 0..q-1, base-p digits the coefficients of x^0, x^1, ..)."""

    def __init__(self, name, p, k=1, modulus=None):
        self.name, self.p, self.k = name, p, k
        if p == 0:
            self.q, self.zero, self.one = None, Fraction(0), Fraction(1)
            return
        self.q = p ** k
        self.zero, self.one = 0, 1
        q = self.q

        def digits(a):
            return [(a // p ** i) % p for i in range(k)]

        def number(ds):
            return sum(d * p ** i for i, d in enumerate(ds))

        def polymul(a, b):
            da, db = digits(a), digits(b)
            prod = [0] * (2 * k - 1)
            for i, x in enumerate(da):
                for j, y in enumerate(db):
                    prod[i + j] = (prod[i + j] + x * y) % p
            if k > 1:
                mod = list(modulus)                                  # monic, degree k
                for d in range(2 * k - 2, k - 1, -1):
                    c = prod[d]
                    if c:
                        for i in range(k + 1):
                            prod[d - k + i] = (prod[d - k + i] - c * mod[i]) % p
            return number(prod[:k])

        self.add_t = [[number([(x + y) % p for x, y in zip(digits(a), digits(b))]) for b in range(q)] for a in range(q)]
        self.mul_t = [[polymul(a, b) for b in range(q)] for a in range(q)]
        self.neg_t = [number([(-x) % p for x in digits(a)]) for a in range(q)]
        self.inv_t = [None] * q
        for a in range(1, q):
            for b in range(1, q):
                if self.mul_t[a][b] == 1:
                    self.inv_t[a] = b
                    break

    def elements(self):
        return list(range(self.q))

    def add(self, a, b):
        return a + b if self.p == 0 else self.add_t[a][b]

    def sub(self, a, b):
        return a - b if self.p == 0 else self.add_t[a][self.neg_t[b]]

    def mul(self, a, b):
        return a * b if self.p == 0 else self.mul_t[a][b]

    def neg(self, a):
        return -a if self.p == 0 else self.neg_t[a]

    def inv(self, a):
        if self.p == 0:
            if a == 0:
                raise ZeroDivisionError
            return 1 / a
        if a == 0 or self.inv_t[a] is None:
            raise ZeroDivisionError
        return self.inv_t[a]

    def from_int(self, n):
        if self.p == 0:
            return Fraction(n)
        return n % self.p                      # the prime field inside, as constant polynomials

    def power(self, a, e):
        r = self.one
        for _ in range(e):
            r = self.mul(r, a)
        return r

    def is_zero(self, a):
        return a == 0


# ----------------------------------------------------------------------------------------------- polynomials
def padd(F, a, b):
    n = max(len(a), len(b))
    return [F.add(a[i] if i < len(a) else F.zero, b[i] if i < len(b) else F.zero) for i in range(n)]


def pmul(F, a, b):
    if not a or not b:
        return []
    out = [F.zero] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        if F.is_zero(x):
            continue
        for j, y in enumerate(b):
            out[i + j] = F.add(out[i + j], F.mul(x, y))
    return out


def pscale(F, a, c):
    return [F.mul(x, c) for x in a]


def peval(F, a, x):
    r = F.zero
    for c in reversed(a):
        r = F.add(F.mul(r, x), c)
    return r


def lagrange(F, pts):
    """The Lagrange polynomials at pts, coefficient lists of length len(pts) (constant term first)."""
    out = []
    for k, bk in enumerate(pts):
        num, den = [F.one], F.one
        for j, bj in enumerate(pts):
            if j != k:
                num = pmul(F, num, [F.neg(bj), F.one])
                den = F.mul(den, F.sub(bk, bj))
        poly = pscale(F, num, F.inv(den))
        out.append(poly + [F.zero] * (len(pts) - len(poly)))
    return out


def binom_poly(F, a, w, n):
    """(a + eps u)^w modulo u^n, as {(power of eps, power of u): coefficient}, expanded by repeated multiplication."""
    cur = {(0, 0): F.one}
    for _ in range(w):
        nxt = {}
        for (e, d), c in cur.items():
            for (e2, d2, c2) in ((0, 0, a), (1, 1, F.one)):
                if d + d2 < n:
                    key = (e + e2, d + d2)
                    nxt[key] = F.add(nxt.get(key, F.zero), F.mul(c, c2))
        cur = {key: c for key, c in nxt.items() if not F.is_zero(c)}
    return cur


# ----------------------------------------------------------------------------------------------- Laurent polynomials
def ladd(F, a, b):
    out = dict(a)
    for e, c in b.items():
        out[e] = F.add(out.get(e, F.zero), c)
    return {e: c for e, c in out.items() if not F.is_zero(c)}


def lmul(F, a, b):
    out = {}
    for e1, c1 in a.items():
        for e2, c2 in b.items():
            out[e1 + e2] = F.add(out.get(e1 + e2, F.zero), F.mul(c1, c2))
    return {e: c for e, c in out.items() if not F.is_zero(c)}


def g_matrix(F, a, n):
    """g_h: Q -> J[eps], t^s -> (a + eps u)^s mod u^n; G[r][s] = coefficient of u^r, a Laurent polynomial."""
    G = [[{} for _ in range(n)] for _ in range(n)]
    for s in range(n):
        for (e, d), c in binom_poly(F, a, s, n).items():
            G[d][s] = ladd(F, G[d][s], {e: c})
    return G


def g_inverse(F, G, n):
    """The inverse of the upper-triangular G over F[eps, eps^-1] by back substitution (diagonal entries monomials)."""
    inv = [[{} for _ in range(n)] for _ in range(n)]
    for col in range(n):                       # solve G x = e_col
        x = [{} for _ in range(n)]
        for r in range(n - 1, -1, -1):
            rhs = {0: F.one} if r == col else {}
            for c in range(r + 1, n):
                if x[c] and G[r][c]:
                    rhs = ladd(F, rhs, {e: F.neg(v) for e, v in lmul(F, G[r][c], x[c]).items()})
            d = G[r][r]
            if len(d) != 1:
                raise AssertionError("the diagonal of g_h is not a monomial")
            (de, dc), = d.items()
            x[r] = {e - de: F.mul(v, F.inv(dc)) for e, v in rhs.items()}
        for r in range(n):
            inv[r][col] = x[r]
    return inv                                  # inv[i][s]: coefficient of t^i in g^-1(u^s)


# ----------------------------------------------------------------------------------------------- one instance
def draw_instance(F, M, n, rng):
    dims_y = [rng.choice((1, 2)) for _ in range(M)]
    dims_z = [rng.choice((1, 2)) for _ in range(M)]
    blocks = []
    for h in range(M):
        while True:
            if F.p == 0:
                A = {(a, b, c): Fraction(rng.randint(-COEFF, COEFF)) for a in range(NX) for b in range(dims_y[h])
                     for c in range(dims_z[h])}
            else:
                A = {(a, b, c): rng.randrange(F.q) for a in range(NX) for b in range(dims_y[h]) for c in range(dims_z[h])}
            A = {key: v for key, v in A.items() if not F.is_zero(v)}
            if A:
                break
        blocks.append(A)
    l = M + n - 1
    if F.p == 0:
        pool = [Fraction(v) for v in range(-QPOINTS, QPOINTS + 1)]
    else:
        pool = F.elements()
    a_pts = rng.sample(pool, M)
    b_pts = rng.sample(pool, l)
    return {"M": M, "n": n, "dims_y": dims_y, "dims_z": dims_z, "blocks": blocks, "a": a_pts, "b": b_pts}


def matched_form(inst, cross=None):
    """A = sum_h A_h(x, y_h, z_h): {(a, (h, b), (h', c)): coefficient}; cross plants one crossed term."""
    A = {}
    for h, blk in enumerate(inst["blocks"]):
        for (a, b, c), v in blk.items():
            A[(a, (h, b), (h, c))] = v
    if cross is not None:
        A[(0, (0, 0), (1, 0))] = cross
    return A


def pullback(F, inst, A, b_pts=None, beta_plain=False):
    """The form of A^(+l) pulled back along the restriction (evaluation at the b's, interpolation) and alpha, beta,
    gamma: {((a, m), (h, b, s), (h', c, r)): Laurent polynomial}. Also returns the restriction check (v).

    Each leg's map sends a basis vector to multiples of one coordinate of A in every copy k (x_a (x) t^m to
    b_k^m x_a^(k); y_(h,b) (x) u^s to Y1[h, s, k] y_(h,b)^(k); z_(h,c) (x) u^r* to Z1[h, r, k] z_(h,c)^(k)), so the
    pulled-back coefficient is A(x_a, y_(h,b), z_(h',c)) times sum_k of the three multipliers."""
    M, n = inst["M"], inst["n"]
    a_pts = inst["a"]
    b_pts = inst["b"] if b_pts is None else b_pts
    l = M + n - 1
    L = lagrange(F, b_pts)                      # degree < len(b_pts)
    width = max(l, len(b_pts))
    L = [row + [F.zero] * (width - len(row)) for row in L]
    # (v): sum_k b_k^(m+s) L_k[w] == [w == m + s]
    restr_ok = True
    for m in range(M):
        for s in range(n):
            for w in range(l):
                v = F.zero
                for k, bk in enumerate(b_pts):
                    v = F.add(v, F.mul(F.power(bk, m + s), L[k][w]))
                if v != (F.one if w == m + s else F.zero):
                    restr_ok = False
    K = range(len(b_pts))
    X1 = {(m, k): {0: F.power(b_pts[k], m)} for m in range(M) for k in K}
    Y1, Z1 = {}, {}
    for h in range(M):
        Ginv = g_inverse(F, g_matrix(F, a_pts[h], n), n)
        for s in range(n):
            col = ({i: ({0: F.one} if i == s else {}) for i in range(n)} if beta_plain
                   else {i: Ginv[i][s] for i in range(n)})
            for k in K:
                v = {}
                for i, lp in col.items():
                    if lp:
                        v = ladd(F, v, {e: F.mul(c, F.power(b_pts[k], i)) for e, c in lp.items()})
                Y1[(h, s, k)] = v
        I = [[{} for _ in range(l)] for _ in range(n)]          # I[r][w]: coefficient of u^r in (a_h + eps u)^w
        for w in range(l):
            for (e, d), c in binom_poly(F, a_pts[h], w, n).items():
                I[d][w] = ladd(F, I[d][w], {e: c})
        for r in range(n):
            for k in K:
                v = {}
                for w in range(l):
                    if I[r][w] and not F.is_zero(L[k][w]):
                        v = ladd(F, v, {e: F.mul(x, L[k][w]) for e, x in I[r][w].items()})
                Z1[(h, r, k)] = v
    cache = {}

    def multiplier(m, h, s, h2, r):
        key = (m, h, s, h2, r)
        if key not in cache:
            tot = {}
            for k in K:
                if X1[(m, k)] and Y1[(h, s, k)] and Z1[(h2, r, k)]:
                    tot = ladd(F, tot, lmul(F, lmul(F, X1[(m, k)], Y1[(h, s, k)]), Z1[(h2, r, k)]))
            cache[key] = tot
        return cache[key]

    T = {}
    for (a, (h, b), (h2, c)), coef in A.items():
        for m in range(M):
            for s in range(n):
                for r in range(n):
                    mult = multiplier(m, h, s, h2, r)
                    if mult:
                        v = {e: F.mul(x, coef) for e, x in mult.items()}
                        v = {e: x for e, x in v.items() if not F.is_zero(x)}
                        if v:
                            key = ((a, m), (h, b, s), (h2, c, r))
                            T[key] = ladd(F, T.get(key, {}), v)
    return {k: v for k, v in T.items() if v}, restr_ok


def phi(F, inst):
    """Eq. 2.3: Phi((a, m), (h, b, s), (h, c, r)) = A_h(a, b, c) * coefficient of u^r in (a_h + eps u)^m u^s."""
    M, n = inst["M"], inst["n"]
    out = {}
    for h, blk in enumerate(inst["blocks"]):
        for m in range(M):
            sig = binom_poly(F, inst["a"][h], m, n)
            for s in range(n):
                for (e, d), c in sig.items():
                    r = d + s
                    if r >= n:
                        continue
                    for (a, b, cc), v in blk.items():
                        key = ((a, m), (h, b, s), (h, cc, r))
                        out[key] = ladd(F, out.get(key, {}), {e: F.mul(c, v)})
    return {k: v for k, v in out.items() if v}


def direct_sum_at_zero(F, inst, form):
    """Phi(0) with the first leg in the basis x_a (x) La_h': equal to the direct sum of the A_h (x) B_X(n)?"""
    M, n = inst["M"], inst["n"]
    La = lagrange(F, inst["a"])                 # raises ZeroDivisionError when two a's coincide
    got = {}
    for ((a, m), yi, zi), lp in form.items():
        v0 = lp.get(0)
        if v0 is None or F.is_zero(v0):
            continue
        for hp in range(M):
            c = La[hp][m] if m < len(La[hp]) else F.zero
            if F.is_zero(c):
                continue
            key = ((a, hp), yi, zi)
            got[key] = F.add(got.get(key, F.zero), F.mul(c, v0))
    got = {k: v for k, v in got.items() if not F.is_zero(v)}
    want = {}
    for h, blk in enumerate(inst["blocks"]):
        for (a, b, c), v in blk.items():
            for s in range(n):
                want[((a, h), (h, b, s), (h, c, s))] = v
    return got == want


def check_instance(F, inst):
    A = matched_form(inst)
    T, restr_ok = pullback(F, inst, A)
    P = phi(F, inst)
    polynomial = all(e >= 0 for lp in T.values() for e in lp)
    equal = T == P
    try:
        dsum = direct_sum_at_zero(F, inst, T)
    except ZeroDivisionError:
        dsum = False
    deg = max((e for lp in T.values() for e in lp), default=0)
    bound = min(inst["M"] - 1, inst["n"] - 1)
    # beside: g_h^-1 as printed, u^s -> eps^-s (t - a_h)^s
    printed_inv = True
    for h in range(inst["M"]):
        Ginv = g_inverse(F, g_matrix(F, inst["a"][h], inst["n"]), inst["n"])
        for s in range(inst["n"]):
            poly = [F.one]
            for _ in range(s):
                poly = pmul(F, poly, [F.neg(inst["a"][h]), F.one])
            want = {i: ({-s: poly[i]} if i < len(poly) and not F.is_zero(poly[i]) else {}) for i in range(inst["n"])}
            got = {i: Ginv[i][s] for i in range(inst["n"])}
            printed_inv &= got == want
    return {"polynomial": polynomial, "equal": equal, "direct_sum": dsum, "degree_ok": deg <= bound,
            "restriction": restr_ok, "degree": deg, "bound": bound, "attained": deg == bound,
            "printed_inverse": printed_inv, "terms": len(T)}


# ----------------------------------------------------------------------------------------------- beside: Lemma 4.1 mod p
def rank_mod(rows, p):
    rows = [[x % p for x in r] for r in rows]
    rank, col, ncols = 0, 0, len(rows[0]) if rows else 0
    for col in range(ncols):
        piv = next((i for i in range(rank, len(rows)) if rows[i][col]), None)
        if piv is None:
            continue
        rows[rank], rows[piv] = rows[piv], rows[rank]
        inv = pow(rows[rank][col], p - 2, p)
        rows[rank] = [(x * inv) % p for x in rows[rank]]
        for i in range(len(rows)):
            if i != rank and rows[i][col]:
                f = rows[i][col]
                rows[i] = [(x - f * y) % p for x, y in zip(rows[i], rows[rank])]
        rank += 1
    return rank


def rank_q(rows):
    rows = [[Fraction(x) for x in r] for r in rows]
    rank = 0
    for col in range(len(rows[0]) if rows else 0):
        piv = next((i for i in range(rank, len(rows)) if rows[i][col] != 0), None)
        if piv is None:
            continue
        rows[rank], rows[piv] = rows[piv], rows[rank]
        rows[rank] = [x / rows[rank][col] for x in rows[rank]]
        for i in range(len(rows)):
            if i != rank and rows[i][col] != 0:
                f = rows[i][col]
                rows[i] = [x - f * y for x, y in zip(rows[i], rows[rank])]
        rank += 1
    return rank


def exact_sequence(e, p):
    """0 -> D V_(e-1) -> V_e (x) span(s, w) -> V_(e+1) -> 0, D = uw - vs: injective, surjective, composition zero."""
    coords = [(i, t) for i in range(e + 1) for t in "sw"]          # u^(e-i) v^i (x) t
    # surjection: f (x) s + g (x) w -> f u + g v ; u^(e-i) v^i (x) s -> u^(e+1-i) v^i, (x) w -> u^(e-i) v^(i+1)
    surj = [[0] * len(coords) for _ in range(e + 2)]
    for col, (i, t) in enumerate(coords):
        surj[i if t == "s" else i + 1][col] = 1
    # injection: h = u^(e-1-j) v^j -> (u h) (x) w - (v h) (x) s
    inj = [[0] * e for _ in coords]
    for j in range(e):
        inj[coords.index((j, "w"))][j] += 1
        inj[coords.index((j + 1, "s"))][j] -= 1
    comp = [[sum(surj[r][c] * inj[c][j] for c in range(len(coords))) % p for j in range(e)] for r in range(e + 2)]
    return (rank_mod(surj, p) == e + 2 and (e == 0 or rank_mod(inj, p) == e)
            and all(x == 0 for row in comp for x in row) and len(coords) == (e + 2) + e)


def solve_mod(basis, target, coords, p):
    n = len(basis)
    idx = {c: i for i, c in enumerate(coords)}
    rows = [[0] * (n + 1) for _ in coords]
    for col, vec in enumerate(basis):
        for c, x in vec.items():
            rows[idx[c]][col] = x % p
    for c, x in target.items():
        rows[idx[c]][n] = x % p
    r = 0
    for col in range(n):
        piv = next((i for i in range(r, len(rows)) if rows[i][col]), None)
        if piv is None:
            raise AssertionError("singular")
        rows[r], rows[piv] = rows[piv], rows[r]
        inv = pow(rows[r][col], p - 2, p)
        rows[r] = [(x * inv) % p for x in rows[r]]
        for i in range(len(rows)):
            if i != r and rows[i][col]:
                f = rows[i][col]
                rows[i] = [(x - f * y) % p for x, y in zip(rows[i], rows[r])]
        r += 1
    if any(rows[i][n] for i in range(r, len(rows))):
        raise AssertionError("outside the span")
    return [rows[i][n] for i in range(n)]


def filtration_mod(a, b, p):
    """mm/omega94.py's Lemma 4.1 degeneration (its printed bases and weights) rebuilt over F_p."""
    def basis_VeW(e):
        quot = [{(i, "s"): 1} for i in range(e + 1)] + [{(e, "w"): 1}]
        kern = [{(j, "w"): 1, (j + 1, "s"): -1} for j in range(e)]
        return quot, kern

    e_in, e_out = b - 1, a + b - 2
    q_in, k_in = basis_VeW(e_in)
    q_out, k_out = basis_VeW(e_out)
    out_basis = q_out + k_out
    coords = [(i, t) for i in range(e_out + 1) for t in ("s", "w")]
    terms = {}
    for i in range(a):
        for kind, family in (("q", q_in), ("k", k_in)):
            for j, g in enumerate(family):
                prod = {}
                for (m, t), x in g.items():
                    prod[(m + i, t)] = prod.get((m + i, t), 0) + x
                xs = solve_mod(out_basis, prod, coords, p)
                for o, x in enumerate(xs):
                    if x:
                        okind, oj = ("q", o) if o < len(q_out) else ("k", o - len(q_out))
                        w = (-1 if kind == "k" else 0) + (1 if okind == "k" else 0)
                        terms[(i, kind, j, okind, oj)] = (x, w)
    negative = [k for k, (x, w) in terms.items() if w < 0]
    zero = {k: x for k, (x, w) in terms.items() if w == 0}
    plus = {(i, j, oj): x for (i, kind, j, okind, oj), x in zero.items() if kind == "q" and okind == "q"}
    minus = {(i, j, oj): x for (i, kind, j, okind, oj), x in zero.items() if kind == "k" and okind == "k"}
    cross = [k for k in zero if k[1] != k[3]]
    C = lambda aa, bb: {(i, j, i + j): 1 for i in range(aa) for j in range(bb)}
    return not negative and not cross and plus == C(a, b + 1) and minus == C(a, b - 1)


# ----------------------------------------------------------------------------------------------- reading the e-print
def read_input(path=None):
    name, sha, size = INPUT
    path = path or os.path.join("inputs", name)
    if not os.path.exists(path):
        raise Refused(f"input {name} is missing")
    with open(path, "rb") as fh:
        data = fh.read()
    if hashlib.sha256(data).hexdigest() != sha or len(data) != size:
        raise Refused(f"input {name} does not match its hash")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        member = tar.getmember(TEX_MEMBER)
        tex = tar.extractfile(member).read().decode("utf-8")
    return tex


def printed_found(tex):
    flat = " ".join(tex.split())
    return [" ".join(s.split()) in flat for s in PRINTED]


# ----------------------------------------------------------------------------------------------- controls
def controls(seed, fields):
    ctl, info = {}, {}
    rng = seeded(seed, "controls")
    ok = True
    for F in fields:
        if F.p == 0:
            continue
        el = F.elements()
        triples = ([(a, b, c) for a in el for b in el for c in el] if F.q <= 9
                   else [(rng.randrange(F.q), rng.randrange(F.q), rng.randrange(F.q)) for _ in range(2000)])
        for a, b, c in triples:
            ok &= F.mul(F.mul(a, b), c) == F.mul(a, F.mul(b, c))
            ok &= F.add(F.add(a, b), c) == F.add(a, F.add(b, c))
            ok &= F.mul(a, F.add(b, c)) == F.add(F.mul(a, b), F.mul(a, c))
        ok &= all(F.mul(a, F.inv(a)) == 1 for a in el if a)
        orders = []
        for g in el[1:]:
            x, o = g, 1
            while x != 1:
                x, o = F.mul(x, g), o + 1
            orders.append(o)
        ok &= max(orders) == F.q - 1
    ctl["(a) field tables"] = ok
    ok = True
    for F in fields:
        for l in range(1, 10):
            if F.q is not None and l > F.q:
                continue
            pool = [Fraction(v) for v in range(-QPOINTS, QPOINTS + 1)] if F.p == 0 else F.elements()
            pts = rng.sample(pool, l)
            f = [Fraction(rng.randint(-5, 5)) for _ in range(l)] if F.p == 0 else [rng.randrange(F.q) for _ in range(l)]
            L = lagrange(F, pts)
            rec = [F.zero] * l
            for k, bk in enumerate(pts):
                rec = padd(F, rec, pscale(F, L[k], peval(F, f, bk)))
            rec = rec + [F.zero] * (l - len(rec))
            ok &= rec[:l] == f
    ctl["(b) interpolation"] = ok
    caught_c = caught_d = caught_e = caught_f = True
    counts = {"c": 0, "d": 0, "e": 0, "f": 0}
    for F in fields:
        for M in range(1, 4):
            for n in range(1, 4):
                l = M + n - 1
                if F.q is not None and l > F.q:
                    continue
                inst = draw_instance(F, M, n, seeded(seed, f"control/{F.name}/{M}/{n}"))
                A = matched_form(inst)
                good = phi(F, inst)
                if l >= 2:
                    T, r_ok = pullback(F, inst, A, b_pts=inst["b"][:-1])
                    caught_c &= (not r_ok) and T != good
                    counts["c"] += 1
                if n >= 2:
                    T, _ = pullback(F, inst, A, beta_plain=True)
                    caught_d &= T != good
                    counts["d"] += 1
                if M >= 2:
                    T, _ = pullback(F, inst, matched_form(inst, cross=F.one))
                    try:
                        ds = direct_sum_at_zero(F, inst, T)
                    except ZeroDivisionError:
                        ds = False
                    caught_e &= T != good and not ds
                    counts["e"] += 1
                    bad = dict(inst, a=[inst["a"][0], inst["a"][0]] + inst["a"][2:])
                    try:
                        direct_sum_at_zero(F, bad, phi(F, bad))
                        caught_f = False
                    except ZeroDivisionError:
                        pass
                    counts["f"] += 1
    ctl["(c) planted: one point too few"] = caught_c and counts["c"] > 0
    ctl["(d) planted: no substitution in beta"] = caught_d and counts["d"] > 0
    ctl["(e) planted: a crossed term"] = caught_e and counts["e"] > 0
    ctl["(f) planted: a_1 = a_2"] = caught_f and counts["f"] > 0
    info["planted_counts"] = counts
    Qf = fields[0]
    inst = {"M": 2, "n": 1, "dims_y": [1, 1], "dims_z": [1, 1], "a": [Fraction(0), Fraction(1)],
            "b": [Fraction(0), Fraction(1)],
            "blocks": [{(0, 0, 0): Fraction(2)}, {(0, 0, 0): Fraction(3), (1, 0, 0): Fraction(5)}]}
    T, r_ok = pullback(Qf, inst, matched_form(inst))
    at_t = {k: v[0] for k, v in T.items() if k[0][1] == 1 and 0 in v}      # x (x) t: p = t, p(a_1) = 0, p(a_2) = 1
    ctl["(g) by hand: M = 2, n = 1"] = (r_ok and T == phi(Qf, inst)
                                        and at_t == {((0, 1), (1, 0, 0), (1, 0, 0)): Fraction(3),
                                                     ((1, 1), (1, 0, 0), (1, 0, 0)): Fraction(5)})
    return ctl, info


# ----------------------------------------------------------------------------------------------- the run
def run(seed, results="results", input_path=None):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    tex = read_input(input_path)
    found = printed_found(tex)
    fields = [Field(*f) for f in FIELDS]
    per, counts = [], {"polynomial": 0, "equal": 0, "direct_sum": 0, "degree_ok": 0, "restriction": 0}
    attained = printed_inv = minimal = minimal_ok = 0
    by_field = {}
    for F in fields:
        size = F.q if F.q is not None else 10 ** 9
        for M in range(1, MN_MAX + 1):
            for n in range(1, MN_MAX + 1):
                if M + n - 1 > size:
                    continue
                for k in range(INSTANCES):
                    inst = draw_instance(F, M, n, seeded(seed, f"instance/{F.name}/{M}/{n}/{k}"))
                    r = check_instance(F, inst)
                    ok = all(r[c] for c in counts)
                    for c in counts:
                        counts[c] += int(r[c])
                    attained += int(r["attained"])
                    printed_inv += int(r["printed_inverse"])
                    if F.q is not None and M + n - 1 == F.q:
                        minimal += 1
                        minimal_ok += int(ok)
                    by_field.setdefault(F.name, [0, 0])
                    by_field[F.name][0] += 1
                    by_field[F.name][1] += int(ok)
                    per.append({"field": F.name, "M": M, "n": n, "k": k, "ok": ok, **{c: r[c] for c in counts},
                                "degree": r["degree"], "bound": r["bound"], "terms": r["terms"]})
    n_inst = len(per)
    met = sum(counts.values())
    total = 5 * n_inst
    # beside: C_mu's flattening rank (its third flattening, W* -> P (x) Q), l for every field and pair
    flat_ok, flat_n = True, 0
    for p_ in (0, 2, 3, 5, 7):
        for M in range(1, MN_MAX + 1):
            for n in range(1, MN_MAX + 1):
                l = M + n - 1
                rows = [[1 if m + s == w else 0 for m in range(M) for s in range(n)] for w in range(l)]
                rank = rank_q(rows) if p_ == 0 else rank_mod(rows, p_)
                flat_ok &= rank == l
                flat_n += 1
    copies = "; ".join(f"M={M}: {2 * M - 1}/{3 * M - 2}/{5 * M}" for M in (1, 2, 3, 4, 5, 10))
    seq_ok = all(exact_sequence(e, p_) for p_ in LEMMA41_P for e in range(1, LEMMA41_E + 1))
    filt = {p_: sum(int(filtration_mod(a, b, p_)) for a in LEMMA41_A for b in LEMMA41_B) for p_ in LEMMA41_P}
    filt_total = len(LEMMA41_A) * len(LEMMA41_B)
    ctl, cinfo = controls(seed, fields)
    ctl["(h) the e-print prints the transcribed formulas"] = all(found)
    out = {
        "instances": f"{n_inst} instances: " + ", ".join(f"{k} {v[1]}/{v[0]}" for k, v in by_field.items()),
        "polynomial": counts["polynomial"], "equal_phi": counts["equal"], "direct_sum": counts["direct_sum"],
        "degree_bound": counts["degree_ok"], "restriction": counts["restriction"],
        "instances_total": n_inst,
        "minimal_fields": f"instances on the smallest admitted fields (|F| = M + n - 1): {minimal_ok} of {minimal}",
        "degree_attained": f"eps-degree equals min(M - 1, n - 1) in {attained} of {n_inst}",
        "printed_inverse": f"g_h^-1 is j(u) -> j((t - a_h)/eps), as printed, in {printed_inv} of {n_inst}",
        "flattening": (f"C_mu's flattening rank is M + n - 1 in {flat_n} of {flat_n} cases (char 0, 2, 3, 5, 7)"
                       if flat_ok else "C_mu's flattening rank differs from M + n - 1"),
        "copies": "copies for n = M, Lü/OpenAI's fewest/OpenAI printed: " + copies,
        "lemma41_sequence": f"Lemma 4.1's sequence exact for e = 1..{LEMMA41_E} over F2, F3, F5: {int(seq_ok)}",
        "lemma41_degeneration": "Lemma 4.1's degeneration over F_p (a <= 5, b = 2..6): " + ", ".join(
            f"F{p_} {filt[p_]}/{filt_total}" for p_ in LEMMA41_P),
        "printed_formulas": f"{sum(found)} of {len(found)}",
        "conditions_met": met, "conditions_total": total, "test_passed": int(met == total),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k} is longer than {LIMIT} characters: {v}")
    detail = {"test": TEST, "instances": per, "controls": ctl, "control_info": cinfo, "printed": dict(zip(PRINTED, found)),
              "lemma41": {"sequence": seq_ok, "degeneration": filt}}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, sort_keys=True, ensure_ascii=False)
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
        sys.exit(f"lu2026: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
