#!/usr/bin/env python3
"""Johns & Teitler's power sum decomposition of the determinant: d·d! det_d as d·d! signed dth powers of linear
forms, so the Waring rank of the generic d × d determinant is at most d·d!. Checked identically over the cyclotomic
integers for d from 2 to 7, and at seed-drawn points modulo two primes for d = 8 and 9.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:709084182973f677) is from G. Johns and
Z. Teitler, "An improved upper bound for the Waring rank of the determinant", arXiv:2004.06158v1 (13 April 2020;
Journal of Commutative Algebra 14(3), 2022), its abstract: "The Waring rank of the generic $d \\times d$ determinant
is bounded above by $d \\cdot d!$." The abstract goes on: "Our upper bound comes from an explicit power sum
decomposition." The paper's Theorem 1, its eq. (2), read in its TeX (e-print sha256 49361b49..., 13,264 bytes):

    d \\cdot d! \\det_d = \\sum_{\\sigma \\in S_d} (-1)^{\\sigma} \\sum_{j=1}^d (-1)^{(d+1)j}
                        \\left( \\sum_{i=1}^d \\omega^{ij} x_{i,\\sigma i} \\right)^d,

"where \\omega is a primitive dth root of unity", "a linear combination of d \\cdot d! terms which are dth powers of
linear forms, with coefficients \\pm 1"; dividing by d·d! gives the bound wherever d! is invertible.

Every rule below was fixed before this module's machinery was run on the paper's decomposition. Known before it,
from reading the TeX: Table 2's entries for d = 5 and 6 (37,500 and 15,552) differ from the formula printed above
them, d^3 φ(d) d!/2, which gives 30,000 and 155,520 by hand; the TeX keeps a commented-out version of the table (16,
324, 3,072, 75,000, 311,040), d^3 φ(d) d! for d = 2, 3, 4 and 6 and 75,000 for d = 5. Nothing of the decomposition,
its terms, its symmetries or its equations was computed before the commit; the expansion's running time was measured
beforehand on a perturbed sign pattern ((-1)^(dj) in place of (-1)^((d+1)j)), comparing nothing with the determinant.

1. The terms. For σ in S_d and j = 1, ..., d, the linear form l_(σ,j) = Σ_(i=1..d) ω^(ij) x_(i,σ(i)) with the
   coefficient c_(σ,j) = (-1)^σ (-1)^((d+1)j). The decomposition's sum is R_d = Σ c_(σ,j) l_(σ,j)^d, d·d! terms.
2. Identically, for d from 2 to 7. Arithmetic is in Z[t]/(t^d - 1), ω the class of t, and every coefficient is
   reduced modulo the dth cyclotomic polynomial Φ_d (from t^d - 1 divided by Φ_k for the proper divisors k of d), so
   the identity is decided in Z[ω] for the generic primitive root, and so for every primitive dth root of unity (its
   Galois conjugates). The block polynomial P_d(y_1, ..., y_d) = Σ_j (-1)^((d+1)j) (Σ_i t^(ij) y_i)^d is expanded by
   repeated multiplication of sparse polynomials, not by the multinomial theorem; R_d = Σ_σ (-1)^σ
   P_d(x_(1,σ(1)), ..., x_(d,σ(d))) is formed by substituting each monomial of P_d for every σ and collecting the
   monomials in the d^2 variables. The identity holds for d when every collected coefficient, reduced, is
   d·d!·(-1)^σ on x_(1,σ(1)) ... x_(d,σ(d)) and 0 on every other monomial.
3. At points, for d from 2 to 9 (counted for d = 8 and 9). The two largest primes p below 2^31 with p ≡ 1 (mod
   2520), so that F_p holds a primitive dth root of unity for every d up to 9; ω_p is the first h^((p-1)/d), h = 2,
   3, ..., of order exactly d. At two points per prime drawn from the seed (each entry an integer from 0 to p - 1, by
   SHA-256 of the seed, a label and a counter), R_d is evaluated from rule 1's definition, term by term, modulo p,
   against d·d! times the determinant modulo p (Gaussian elimination). A nonzero difference of degree d vanishes at a
   random point with probability at most d/p (Schwartz and Zippel), so four agreements at d = 9 leave a wrong
   identity whose reductions modulo both primes are nonzero with probability below 4e-34.
4. The test's eight conditions, one for each d from 2 to 9: rule 1's d·d! terms with coefficients ±1, and rule 2's
   identity (d up to 7) or rule 3's four agreements (d = 8 and 9). test_passed is 1 if all eight hold.
5. Beside, none of it counted: rule 3's points for d = 2 to 7; the paper's Lemma (the coefficient of a monomial
   x_(i_1) ... x_(i_d) in P_d is d times the multinomial coefficient when Σ i_k ≡ C(d+1, 2) (mod d), else 0)
   against P_d's expansion for d = 2 to 7; its Section 3 theorem, the terms' linear independence, as the rank modulo
   the first prime of the d·d! powers' values at d·d! seed-drawn points, for d = 2 to 5 (full rank proves
   independence over Q(ω)); its Section 4: every map X -> ω^m D^n P_π X P_σ of the subgroup H it names, for d = 2
   to 5 (m, n in [d], π affine on Z/d, det(D)^n (-1)^π (-1)^σ = 1; D = diag(ω, ..., ω^d), P_σ the permutation
   matrix with ones at (i, σ(i))), each checked to fix the determinant (det A det B = 1, computed from the matrices)
   and to send every term's coefficient matrix D^j P_σ' to one of ω^k D^j'' P_τ with the same coefficient, counted
   as distinct pairs (A, B) against d^3 φ(d) d!/2 and Table 2's printed 8, 162, 1536, 37500 and 15552; its Lemma
   (P_π D is in M = {ω^k D^j P_σ} if and only if π is affine) for every π, d = 2 to 7, with |Aff_d| = d φ(d); and
   transposition as a symmetry for d = 2 to 5 (the paper: yes for d = 2 and 3, not for d > 3); its Section 5
   theorem, the defining equations, over F_p for d = 2, 3 and 4 (p = 3, 7 and 5): the common zeros in projective
   space of the monomial quadrics (two distinct entries of a row or of a column) and of ρ_i^2 - ρ_(i-1) ρ_(i+1), ρ_i
   the ith row sum, indices mod d, found among the matrices with at most one nonzero entry in each row and column
   (exactly the monomial quadrics' zeros), against the d·d! points [D^j P_σ]; Table 1's 41 printed entries against
   their formulas (2^(d-1) d!; (5/6)^floor(d/3) 2^(d-1) d!; (d+1) d!; CGLV's 18; d·d!; C(2d, d) - C(2d-2, d-1),
   with 17 for d = 3 as the text says); the improvement, d·d! below the classical, Derksen and Gurvits bounds for
   d = 3 to 9; and the printed identities, expanded exactly: eq. (1)'s xy and xyz, the classical decomposition (its
   eq. 4, 2^(d-1) d! terms) and Gurvits's (eq. 7, (d+1) d! terms) for d = 2 to 7, and Krishna & Makam's five
   products for det_3.

Controls (controls_passed counts those that behave as stated; the run stops if any fails): (a) Φ_n from the divisor
recursion for n = 1 to 9 against the known polynomials, and t^n ≡ 1 modulo Φ_n; (b) the sparse product against the
multinomial theorem, (Σ a_i y_i)^d with integers a_i drawn from the seed, d = 2 to 7; (c) the determinant modulo p
against the Leibniz sum on seed-drawn matrices, d = 1 to 7; (d) the identity in floating point, an arithmetic path
independent of rules 2 and 3: R_d at a seed-drawn real point with ω = exp(2πi/d) against d·d! det, within 1e-9 of
the sum of the terms' magnitudes, d = 2 to 7; (e) the direct expansion: for d = 2 to 5 each of the d·d! powers
expanded in the d^2 variables by itself and summed, against rule 2's R_d coefficient by coefficient; (f) planted
faults, each caught: one term's sign reversed (σ the identity, j = 1) for d = 2 to 5 by rule 2 and for d = 8 at rule
3's first point, and a root of unity of order d/2 (t^2) in place of ω for d = 4 and 6 by rule 2.

What it cannot check: the theorem for d above 9, which rests on the paper's proof; Conner, Gesmundo, Landsberg &
Ventura's 18-term expression, which the paper says is its d = 3 case; the whole symmetry group G; and the theorem
over commutative rings other than fields.

Writes results/outputs.json and results/detail.json. Run with: python3 waring/jt.py (standard library only).
"""

import cmath
import hashlib
import itertools
import json
import math
import os
import re
import sys
from fractions import Fraction

EXACT_D = (2, 3, 4, 5, 6, 7)
MODULAR_D = (8, 9)
ALL_D = EXACT_D + MODULAR_D
MODULUS_LCM = 2520
POINTS_PER_PRIME = 2
LIMIT = 200
FLOAT_TOL = 1e-9
SYM_D = (2, 3, 4, 5)
INDEP_D = (2, 3, 4, 5)
EQ_PRIMES = {2: 3, 3: 7, 4: 5}

TEST = ("Refuted if, for some d from 2 to 9, the paper's sum over σ in S_d and j = 1, …, d of (−1)^σ (−1)^((d+1)j) "
        "(Σ_i ω^(ij) x_(i,σ(i)))^d, ω a primitive dth root of unity (its eq. 2, Theorem 1; d·d! terms of "
        "coefficient ±1), is not d·d! times the generic d × d determinant: identically over Z[ω], every coefficient "
        "expanded and reduced, for d up to 7, and at two seed-drawn points modulo each of two primes p ≡ 1 "
        "(mod 2520) below 2^31 for d = 8 and 9.")

OUTPUTS = ("exact", "exact_monomials", "modular", "modular_small", "primes", "error_bound", "lemma", "independence",
           "symmetries", "table2", "affine_lemma", "transpose", "equations", "table1", "improvement", "eq1_km",
           "classical", "gurvits", "conditions_met", "conditions_total", "test_passed", "controls_passed",
           "controls_total")

# Table 1 as printed (d = 2, ..., 9), and Table 2 (d = 2, ..., 6)
TABLE1 = {
    "classical": (4, 24, 192, 1920, 23040, 322560, 5160960, 92897280),
    "derksen": (4, 20, 160, 1600, 16000, 224000, 3584000, 53760000),
    "gurvits": (6, 24, 120, 720, 5040, 40320, 362880, 3628800),
    "cglv": {3: 18},
    "new": (4, 18, 96, 600, 4320, 35280, 322560, 3265920),
    "lower": (4, 17, 50, 182, 672, 2508, 9438, 35750),
}
TABLE2 = {2: 8, 3: 162, 4: 1536, 5: 37500, 6: 15552}


class Refused(Exception):
    pass


# ---------------------------------------------------------------- the cyclotomic integers

def poly_divmod(num, den):
    """Integer polynomials, lowest degree first; den monic. Returns (quotient, remainder)."""
    num = list(num)
    q = [0] * max(1, len(num) - len(den) + 1)
    for k in range(len(num) - len(den), -1, -1):
        c = num[k + len(den) - 1]
        q[k] = c
        if c:
            for i, b in enumerate(den):
                num[k + i] -= c * b
    rem = num[:len(den) - 1]
    return q, rem


_PHI = {}


def cyclotomic(n):
    """Φ_n, lowest degree first, from t^n - 1 = Π_(k | n) Φ_k."""
    if n not in _PHI:
        num = [-1] + [0] * (n - 1) + [1]
        for k in range(1, n):
            if n % k == 0:
                num, rem = poly_divmod(num, cyclotomic(k))
                assert not any(rem), (n, k)
        while len(num) > 1 and num[-1] == 0:
            num.pop()
        _PHI[n] = num
    return _PHI[n]


def reduce_cyc(c, n):
    """c: coefficients of t^0..t^(n-1) (an element of Z[t]/(t^n - 1)); its image in Z[t]/Φ_n, a tuple of length φ(n)."""
    phi = cyclotomic(n)
    deg = len(phi) - 1
    c = list(c)
    for k in range(len(c) - 1, deg - 1, -1):
        a = c[k]
        if a:
            for i, b in enumerate(phi):
                c[k - deg + i] -= a * b
    return tuple(c[:deg])


def rotate(c, k):
    """Multiply an element of Z[t]/(t^n - 1) by t^k."""
    n = len(c)
    k %= n
    return c[-k:] + c[:-k] if k else c


# ---------------------------------------------------------------- sparse polynomials over Z[t]/(t^n - 1)

def mul_linear(F, lin, nring):
    """F: {exponent tuple: list of nring ints}; lin: [(variable, power of t, integer scalar)]. Returns F * lin."""
    out = {}
    for mono, c in F.items():
        for v, k, s in lin:
            m = list(mono)
            m[v] += 1
            m = tuple(m)
            rc = rotate(c, k)
            acc = out.get(m)
            if acc is None:
                out[m] = [s * x for x in rc]
            else:
                for idx in range(nring):
                    acc[idx] += s * rc[idx]
    return out


def power_linear(lin, d, nvars, nring):
    F = {tuple([0] * nvars): [1] + [0] * (nring - 1)}
    for _ in range(d):
        F = mul_linear(F, lin, nring)
    return F


def add_into(acc, F, scale):
    for mono, c in F.items():
        a = acc.get(mono)
        if a is None:
            acc[mono] = [scale * x for x in c]
        else:
            for idx in range(len(c)):
                a[idx] += scale * c[idx]


def perms_with_signs(d):
    out = []
    for p in itertools.permutations(range(d)):
        seen, sign = [False] * d, 1
        for i in range(d):
            if not seen[i]:
                j, length = i, 0
                while not seen[j]:
                    seen[j] = True
                    j = p[j]
                    length += 1
                if length % 2 == 0:
                    sign = -sign
        out.append((p, sign))
    return out


def jt_sign(d, j, pattern="paper"):
    e = (d + 1) * j if pattern == "paper" else d * j
    return -1 if e % 2 else 1


def block_jt(d, pattern="paper", omega_power=1):
    """P_d(y) = Σ_j (-1)^((d+1)j) (Σ_i t^(ij) y_i)^d in Z[t]/(t^d - 1), expanded by repeated multiplication."""
    acc = {}
    for j in range(1, d + 1):
        lin = [(i - 1, (omega_power * i * j) % d, 1) for i in range(1, d + 1)]
        add_into(acc, power_linear(lin, d, d, d), jt_sign(d, j, pattern))
    return acc


def reduce_poly(F, n):
    out = {}
    for mono, c in F.items():
        r = reduce_cyc(c, n)
        if any(r):
            out[mono] = r
    return out


def substitute(block, d, perms, width):
    """Σ_σ sign(σ) block(x_(1,σ(1)), ..., x_(d,σ(d))); monomials as sorted tuples of variable indices i*d + σ(i)."""
    items = []
    for lam, c in block.items():
        rows = [i for i in range(d) for _ in range(lam[i])]
        nz = [(idx, v) for idx, v in enumerate(c) if v]
        items.append((rows, nz))
    R = {}
    for p, sign in perms:
        for rows, nz in items:
            key = tuple(i * d + p[i] for i in rows)
            acc = R.get(key)
            if acc is None:
                acc = [0] * width
                R[key] = acc
            for idx, v in nz:
                acc[idx] += sign * v
    return R


def det_target(d, perms, scale):
    return {tuple(i * d + p[i] for i in range(d)): scale * s for p, s in perms}


def compare(R, target, width):
    """Identical when every coefficient equals the target integer (in the first slot) and every other slot is 0."""
    zero = [0] * width
    keys = set(R) | set(target)
    bad = 0
    for k in keys:
        want = [target.get(k, 0)] + [0] * (width - 1)
        if list(R.get(k, zero)) != want:
            bad += 1
    nonzero = sum(1 for v in R.values() if any(v))
    return bad == 0, bad, nonzero


def exact_identity(d, perms, pattern="paper", omega_power=1, flip=False):
    block = reduce_poly(block_jt(d, pattern, omega_power), d)
    width = len(cyclotomic(d)) - 1
    R = substitute(block, d, perms, width)
    if flip:  # planted fault: the term (σ = identity, j = 1) with its sign reversed: subtract it twice
        lin = [(i * d + i, (omega_power * (i + 1)) % d, 1) for i in range(d)]
        T = reduce_poly(power_linear(lin, d, d * d, d), d)
        c = jt_sign(d, 1, pattern)
        for mono, v in T.items():
            key = tuple(x for x in range(d * d) for _ in range(mono[x]))
            acc = R.setdefault(key, [0] * width)
            for idx in range(width):
                acc[idx] -= 2 * c * v[idx]
    same, bad, nonzero = compare(R, det_target(d, perms, d * math.factorial(d)), width)
    return same, bad, nonzero, block


def direct_identity(d, perms):
    """Control (e): every power expanded in the d^2 variables by itself, summed, reduced."""
    acc = {}
    for p, s in perms:
        for j in range(1, d + 1):
            lin = [(i * d + p[i], ((i + 1) * j) % d, 1) for i in range(d)]
            add_into(acc, power_linear(lin, d, d * d, d), s * jt_sign(d, j))
    width = len(cyclotomic(d)) - 1
    R = {}
    for mono, c in acc.items():
        r = reduce_cyc(c, d)
        R[tuple(x for x in range(d * d) for _ in range(mono[x]))] = list(r)
    return R


# ---------------------------------------------------------------- the integer decompositions beside it

def block_classical(d):
    acc = {}
    for eps in itertools.product((1, -1), repeat=d - 1):
        e = (1,) + eps
        lin = [(i, 0, e[i]) for i in range(d)]
        add_into(acc, power_linear(lin, d, d, 1), math.prod(e))
    return acc


def block_gurvits(d):
    acc = {}
    add_into(acc, power_linear([(i, 0, 1) for i in range(d)], d, d, 1), 1)
    for j in range(d):
        add_into(acc, power_linear([(i, 0, 1) for i in range(d) if i != j], d, d, 1), -1)
    return acc


def integer_identity(block, d, perms, scale):
    block = {m: c for m, c in block.items() if c[0]}
    R = substitute(block, d, perms, 1)
    return compare(R, det_target(d, perms, scale), 1)


def poly_from_products(factors_list, nvars):
    """Σ_k coef_k Π_f (linear form f); a linear form is {variable: integer}. Integer polynomial {exponents: int}."""
    total = {}
    for coef, factors in factors_list:
        F = {tuple([0] * nvars): [coef]}
        for f in factors:
            F = mul_linear(F, [(v, 0, a) for v, a in f.items()], 1)
        add_into(total, F, 1)
    return {m: c[0] for m, c in total.items() if c[0]}


def km_identity():
    """Krishna & Makam's det_3 as five products of linear forms, as the paper prints it; variable x_ij is 3(i-1)+(j-1)."""
    x = lambda i, j: 3 * (i - 1) + (j - 1)
    lf = lambda *pairs: {x(i, j): 1 for i, j in pairs}
    terms = [
        (1, [lf((1, 1)), lf((2, 2), (2, 3)), lf((3, 1), (3, 3))]),
        (1, [lf((1, 2), (1, 3)), lf((2, 1)), lf((3, 2))]),
        (-1, [lf((1, 1), (1, 3)), lf((2, 2)), lf((3, 1))]),
        (-1, [lf((1, 2)), lf((2, 1), (2, 3)), lf((3, 2), (3, 3))]),
        (1, [{x(1, 2): 1, x(1, 1): -1}, lf((2, 3)), lf((3, 1), (3, 2), (3, 3))]),
    ]
    got = poly_from_products(terms, 9)
    want = {}
    for p, s in perms_with_signs(3):
        m = [0] * 9
        for i in range(3):
            m[3 * i + p[i]] += 1
        want[tuple(m)] = s
    return got == want


def eq1_identities():
    # 4xy = (x+y)^2 - (x-y)^2; 24xyz = (x+y+z)^3 - (x+y-z)^3 - (x-y+z)^3 + (x-y-z)^3
    two = poly_from_products([(1, [{0: 1, 1: 1}] * 2), (-1, [{0: 1, 1: -1}] * 2)], 2)
    three = poly_from_products([(1, [{0: 1, 1: 1, 2: 1}] * 3), (-1, [{0: 1, 1: 1, 2: -1}] * 3),
                                (-1, [{0: 1, 1: -1, 2: 1}] * 3), (1, [{0: 1, 1: -1, 2: -1}] * 3)], 3)
    return two == {(1, 1): 4}, three == {(1, 1, 1): 24}


# ---------------------------------------------------------------- the paper's Lemma

def lemma_check(d, block_reduced):
    """Lemma: [x_I] P_d = d * multinomial(d; λ) if Σ i_k ≡ C(d+1, 2) (mod d), else 0 (indices 1..d)."""
    ok = True
    for lam in compositions(d, d):
        s = sum((i + 1) * lam[i] for i in range(d))
        want = d * math.factorial(d) // math.prod(math.factorial(a) for a in lam) if (s - math.comb(d + 1, 2)) % d == 0 \
            else 0
        got = block_reduced.get(lam)
        got = tuple(got) if got is not None else tuple([0] * (len(cyclotomic(d)) - 1))
        ok = ok and got == (want,) + (0,) * (len(got) - 1)
    return ok


def compositions(total, parts):
    if parts == 1:
        yield (total,)
        return
    for a in range(total + 1):
        for rest in compositions(total - a, parts - 1):
            yield (a,) + rest


# ---------------------------------------------------------------- modular arithmetic

def is_prime(n):
    if n < 2:
        return False
    for q in (2, 3, 5, 7, 11, 13):
        if n % q == 0:
            return n == q
    dd, s = n - 1, 0
    while dd % 2 == 0:
        dd //= 2
        s += 1
    for a in (2, 3, 5, 7):          # deterministic below 3,215,031,751
        x = pow(a, dd, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def primes_1_mod(m, below, count):
    out, k = [], (below - 2) // m
    while len(out) < count:
        p = 1 + m * k
        if p < below and is_prime(p):
            out.append(p)
        k -= 1
    return out


def prime_factors(n):
    f, q = set(), 2
    while q * q <= n:
        while n % q == 0:
            f.add(q)
            n //= q
        q += 1
    if n > 1:
        f.add(n)
    return f


def root_of_unity(d, p):
    """The first h^((p-1)/d), h = 2, 3, ..., of multiplicative order exactly d modulo p."""
    assert (p - 1) % d == 0
    for h in range(2, p):
        w = pow(h, (p - 1) // d, p)
        if pow(w, d, p) == 1 and all(pow(w, d // q, p) != 1 for q in prime_factors(d)):
            return w
    raise AssertionError("no root of unity")


def det_mod(A, p):
    A = [[x % p for x in row] for row in A]
    n, det = len(A), 1
    for c in range(n):
        piv = next((r for r in range(c, n) if A[r][c]), None)
        if piv is None:
            return 0
        if piv != c:
            A[c], A[piv] = A[piv], A[c]
            det = -det
        det = det * A[c][c] % p
        inv = pow(A[c][c], p - 2, p)
        for r in range(c + 1, n):
            f = A[r][c] * inv % p
            if f:
                A[r] = [(a - f * b) % p for a, b in zip(A[r], A[c])]
    return det % p


def rank_mod(A, p):
    """Rank modulo p by forward elimination."""
    A = [[x % p for x in row] for row in A]
    rows, cols, rank = len(A), len(A[0]) if A else 0, 0
    for c in range(cols):
        piv = next((r for r in range(rank, rows) if A[r][c]), None)
        if piv is None:
            continue
        A[rank], A[piv] = A[piv], A[rank]
        inv = pow(A[rank][c], p - 2, p)
        pr = [a * inv % p for a in A[rank]]
        A[rank] = pr
        for r in range(rank + 1, rows):
            f = A[r][c]
            if f:
                A[r] = [(a - f * b) % p for a, b in zip(A[r], pr)]
        rank += 1
        if rank == rows:
            break
    return rank


def leibniz(X, perms):
    return sum(s * math.prod(X[i][p[i]] for i in range(len(X))) for p, s in perms)


def r_mod(X, d, p, w, perms, flip=False):
    """R_d at the point X, modulo p, from rule 1's definition, term by term."""
    W = [[pow(w, ((i + 1) * j) % d, p) for j in range(1, d + 1)] for i in range(d)]
    signs = [jt_sign(d, j) for j in range(1, d + 1)]
    total = 0
    for p_, s in perms:
        y = [X[i][p_[i]] for i in range(d)]
        for jj in range(d):
            lin = sum(W[i][jj] * y[i] for i in range(d)) % p
            total += s * signs[jj] * pow(lin, d, p)
    if flip:  # the term (σ = identity, j = 1) with its sign reversed
        lin = sum(W[i][0] * X[i][i] for i in range(d)) % p
        total -= 2 * signs[0] * pow(lin, d, p)
    return total % p


class Stream:
    def __init__(self, seed, label):
        self.seed, self.label, self.k, self.buf = seed, label, 0, b""

    def _more(self):
        self.buf += hashlib.sha256(f"{self.seed}/{self.label}/{self.k}".encode()).digest()
        self.k += 1

    def below(self, n):
        """An integer from 0 to n - 1 (rejection sampling on 64-bit words)."""
        lim = (2 ** 64 // n) * n
        while True:
            while len(self.buf) < 8:
                self._more()
            v, self.buf = int.from_bytes(self.buf[:8], "big"), self.buf[8:]
            if v < lim:
                return v % n

    def unit(self):
        return self.below(2 ** 53) / 2 ** 53 * 2 - 1


# ---------------------------------------------------------------- the floating-point control

def float_det(X):
    A = [list(map(complex, row)) for row in X]
    n, det = len(A), complex(1)
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(A[r][c]))
        if abs(A[piv][c]) == 0:
            return 0j
        if piv != c:
            A[c], A[piv] = A[piv], A[c]
            det = -det
        det *= A[c][c]
        for r in range(c + 1, n):
            f = A[r][c] / A[c][c]
            A[r] = [a - f * b for a, b in zip(A[r], A[c])]
    return det


def float_identity(d, X, perms):
    w = cmath.exp(2j * math.pi / d)
    total, mag = 0j, 0.0
    for p, s in perms:
        for j in range(1, d + 1):
            lin = sum(w ** (i * j) * X[i - 1][p[i - 1]] for i in range(1, d + 1))
            term = s * jt_sign(d, j) * lin ** d
            total += term
            mag += abs(term)
    target = d * math.factorial(d) * float_det(X)
    return abs(total - target) <= FLOAT_TOL * max(mag, 1.0)


# ---------------------------------------------------------------- linear independence (Section 3)

def independence_rank(d, p, w, stream, perms):
    terms = [(pp, j) for pp, _ in perms for j in range(1, d + 1)]
    W = [[pow(w, (i * j) % d, p) for j in range(0, d + 1)] for i in range(0, d + 1)]
    pts = [[[stream.below(p) for _ in range(d)] for _ in range(d)] for _ in range(len(terms))]
    E = []
    for pp, j in terms:
        row = []
        for Z in pts:
            lin = sum(W[i + 1][j] * Z[i][pp[i]] for i in range(d)) % p
            row.append(pow(lin, d, p))
        E.append(row)
    return rank_mod(E, p), len(terms)


# ---------------------------------------------------------------- symmetries (Section 4)

def in_M(tau, E, d):
    """A monomial matrix with ones-pattern tau (row r -> column tau[r], 0-based) and entry ω^E[r] in row r: is it
    ω^k D^j P_tau? Returns j mod d (1..d) or None. Rows are 1-based in the paper: E[r] ≡ k + j (r + 1)."""
    j = (E[1] - E[0]) % d if d > 1 else 0
    k = (E[0] - j) % d
    if all((E[r] - k - j * (r + 1)) % d == 0 for r in range(d)):
        return j if j else d
    return None


def affine_perms(d):
    """Aff_d as 0-based tuples: i -> a i + b mod d on 1..d (residue 0 read as d), a a unit mod d."""
    out = set()
    for a in range(1, d + 1):
        if math.gcd(a, d) != 1:
            continue
        for b in range(d):
            img = tuple(((a * i + b - 1) % d) for i in range(1, d + 1))
            out.add(img)
    return out


def _sign_cycles(p):
    seen, sign = [False] * len(p), 1
    for i in range(len(p)):
        if not seen[i]:
            j, length = i, 0
            while not seen[j]:
                seen[j] = True
                j = p[j]
                length += 1
            if length % 2 == 0:
                sign = -sign
    return sign


def unit_power(sign, e, d):
    """±ω^e normalised: (sign, e mod d), with -1 folded into ω^(d/2) when d is even."""
    e %= d
    if sign < 0 and d % 2 == 0:
        sign, e = 1, (e + d // 2) % d
    return sign, e


def symmetries(d, perms):
    terms = {}
    for p, s in perms:
        for j in range(1, d + 1):
            terms[(p, j)] = s * jt_sign(d, j)
    aff = affine_perms(d)
    count, distinct, all_ok, det_agrees = 0, set(), True, True
    for m in range(1, d + 1):
        for n in range(1, d + 1):
            for pi in aff:
                spi = _sign_cycles(pi)
                for sg, ssg in perms:
                    # det A: A = ω^m D^n P_π, row r (1-based) holds ω^(m + n r) at column π(r)
                    detA = unit_power(spi, sum(m + n * r for r in range(1, d + 1)), d)
                    detAB = unit_power(detA[0] * ssg, detA[1], d)
                    preserves = detAB == (1, 0)
                    paper = unit_power(spi * ssg, n * (d * (d + 1) // 2), d) == (1, 0)
                    det_agrees = det_agrees and preserves == paper
                    if not paper:
                        continue
                    count += 1
                    distinct.add((pi, tuple((m + n * r) % d for r in range(1, d + 1)), sg))
                    for (sp, j), c in terms.items():
                        # A C B for C = D^j P_σ': row r has ω^(m + n r + j π(r)) at column σ(σ'(π(r))) (1-based π)
                        tau = tuple(sg[sp[pi[r]]] for r in range(d))
                        E = [m + n * (r + 1) + j * (pi[r] + 1) for r in range(d)]
                        jj = in_M(tau, E, d)
                        if jj is None or terms[(tau, jj)] != c:
                            all_ok = False
                    all_ok = all_ok and preserves
    return {"count": count, "distinct": len(distinct), "all_ok": all_ok, "det_condition_agrees": det_agrees,
            "formula": d ** 3 * euler_phi(d) * math.factorial(d) // 2, "affine": len(aff)}


def euler_phi(n):
    return sum(1 for k in range(1, n + 1) if math.gcd(k, n) == 1)


def transpose_symmetry(d, perms):
    terms = {}
    for p, s in perms:
        for j in range(1, d + 1):
            terms[(p, j)] = s * jt_sign(d, j)
    ok = True
    for (p, j), c in terms.items():
        # C = D^j P_σ: (r, σ(r)) holds ω^(j (r+1)); C^T: row σ(r) holds it at column r
        inv = [0] * d
        for r in range(d):
            inv[p[r]] = r
        tau = tuple(inv)
        E = [j * (inv[s] + 1) for s in range(d)]
        jj = in_M(tau, E, d)
        if jj is None or terms[(tau, jj)] != c:
            ok = False
    return ok


def affine_lemma(d, perms):
    aff = affine_perms(d)
    ok = True
    for p, _ in perms:
        # P_π D: row r holds ω^(π(r)) at column π(r) (1-based)
        E = [p[r] + 1 for r in range(d)]
        ok = ok and ((in_M(p, E, d) is not None) == (p in aff))
    return ok, len(aff) == d * euler_phi(d)


# ---------------------------------------------------------------- defining equations (Section 5)

def equations(d, p):
    w = root_of_unity(d, p)
    expected = set()
    for perm, _ in perms_with_signs(d):
        for j in range(1, d + 1):
            M = [[0] * d for _ in range(d)]
            for r in range(d):
                M[r][perm[r]] = pow(w, (j * (r + 1)) % d, p)
            expected.add(normalise(M, p))
    zeros = set()
    for k in range(1, d + 1):
        for rows in itertools.combinations(range(d), k):
            for cols in itertools.permutations(range(d), k):
                for vals in itertools.product(range(1, p), repeat=k - 1):
                    M = [[0] * d for _ in range(d)]
                    M[rows[0]][cols[0]] = 1
                    for t in range(1, k):
                        M[rows[t]][cols[t]] = vals[t - 1]
                    rho = [sum(M[i]) % p for i in range(d)]
                    if all((rho[i] ** 2 - rho[(i - 1) % d] * rho[(i + 1) % d]) % p == 0 for i in range(d)):
                        zeros.add(normalise(M, p))
    return len(zeros), len(expected), zeros == expected


def normalise(M, p):
    flat = [x % p for row in M for x in row]
    first = next(x for x in flat if x)
    inv = pow(first, p - 2, p)
    return tuple(x * inv % p for x in flat)


# ---------------------------------------------------------------- the tables

def table1_check():
    rows = {"classical": lambda d: 2 ** (d - 1) * math.factorial(d),
            "derksen": lambda d: Fraction(5, 6) ** (d // 3) * 2 ** (d - 1) * math.factorial(d),
            "gurvits": lambda d: (d + 1) * math.factorial(d),
            "new": lambda d: d * math.factorial(d),
            "lower": lambda d: 17 if d == 3 else math.comb(2 * d, d) - math.comb(2 * d - 2, d - 1)}
    entries, matches, bad = 0, 0, []
    for name, f in rows.items():
        for d, v in zip(range(2, 10), TABLE1[name]):
            entries += 1
            if f(d) == v:
                matches += 1
            else:
                bad.append((name, d, v, str(f(d))))
    entries += 1
    if TABLE1["cglv"] == {3: 18}:
        matches += 1
    improve = all(d * math.factorial(d) < min(rows["classical"](d), rows["derksen"](d), rows["gurvits"](d))
                  for d in range(3, 10))
    return entries, matches, bad, improve


# ---------------------------------------------------------------- controls

KNOWN_PHI = {1: [-1, 1], 2: [1, 1], 3: [1, 1, 1], 4: [1, 0, 1], 5: [1, 1, 1, 1, 1], 6: [1, -1, 1],
             7: [1] * 7, 8: [1, 0, 0, 0, 1], 9: [1, 0, 0, 1, 0, 0, 1]}


def controls_run(seed, perms_by_d, primes):
    ctl = {}
    ok = all(cyclotomic(n) == KNOWN_PHI[n] for n in KNOWN_PHI)
    for n in range(2, 10):
        _, rem = poly_divmod([0] * n + [1], cyclotomic(n))           # t^n leaves 1 modulo Φ_n
        ok = ok and rem == [1] + [0] * (len(KNOWN_PHI[n]) - 2)
        ok = ok and reduce_cyc([1] * n, n) == (0,) * (len(KNOWN_PHI[n]) - 1)   # 1 + ω + ... + ω^(n-1) = 0
    ctl["cyclotomic polynomials for n = 1..9 as known, t^n = 1 and 1 + t + ... + t^(n-1) = 0 modulo each"] = ok

    st = Stream(seed, "jt/control/multinomial")
    ok = True
    for d in range(2, 8):
        a = [st.below(11) - 5 for _ in range(d)]
        F = power_linear([(i, 0, a[i]) for i in range(d)], d, d, 1)
        for lam in compositions(d, d):
            want = math.factorial(d) // math.prod(math.factorial(x) for x in lam) * math.prod(
                a[i] ** lam[i] for i in range(d))
            ok = ok and F.get(lam, [0])[0] == want
    ctl["sparse products against the multinomial theorem, d = 2..7"] = ok

    st = Stream(seed, "jt/control/det")
    ok = True
    p = primes[0]
    for d in range(1, 8):
        X = [[st.below(p) for _ in range(d)] for _ in range(d)]
        ok = ok and det_mod(X, p) == leibniz(X, perms_by_d[d]) % p
    ctl["determinant modulo p against the Leibniz sum, d = 1..7"] = ok

    st = Stream(seed, "jt/control/float")
    ok = True
    for d in EXACT_D:
        X = [[st.unit() for _ in range(d)] for _ in range(d)]
        ok = ok and float_identity(d, X, perms_by_d[d])
    ctl["the identity in floating point with omega = exp(2 pi i/d), d = 2..7"] = ok

    ok = True
    for d in (2, 3, 4, 5):
        width = len(cyclotomic(d)) - 1
        direct = direct_identity(d, perms_by_d[d])
        block = reduce_poly(block_jt(d), d)
        via = substitute(block, d, perms_by_d[d], width)
        keys = set(direct) | set(via)
        ok = ok and all(list(direct.get(k, [0] * width)) == list(via.get(k, [0] * width)) for k in keys)
    ctl["each power expanded by itself and summed, against rule 2, d = 2..5"] = ok

    ok = True
    for d in (2, 3, 4, 5):
        same, *_ = exact_identity(d, perms_by_d[d], flip=True)
        ok = ok and not same
    for d in (4, 6):
        same, *_ = exact_identity(d, perms_by_d[d], omega_power=2)
        ok = ok and not same
    st = Stream(seed, f"jt/points/8/{primes[0]}")
    X = [[st.below(primes[0]) for _ in range(8)] for _ in range(8)]
    w = root_of_unity(8, primes[0])
    target = 8 * math.factorial(8) * det_mod(X, primes[0]) % primes[0]
    ok = ok and r_mod(X, 8, primes[0], w, perms_by_d[8], flip=True) != target
    ctl["planted faults caught: a sign reversed (d = 2..5, and d = 8 at a point), omega of order d/2 (d = 4, 6)"] = ok
    return ctl


# ---------------------------------------------------------------- the run

def run(seed, results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    perms_by_d = {d: perms_with_signs(d) for d in range(1, 10)}
    primes = primes_1_mod(MODULUS_LCM, 2 ** 31, 2)
    ctl = controls_run(seed, perms_by_d, primes)
    if not all(ctl.values()):
        raise AssertionError(f"a control failed: {[k for k, v in ctl.items() if not v]}")

    cond, info = {}, {}
    lemma_ok, block_sizes = [], []
    for d in ALL_D:
        perms = perms_by_d[d]
        n_terms = len(perms) * d
        coeffs = {s * jt_sign(d, j) for _, s in perms for j in range(1, d + 1)}
        terms_ok = n_terms == d * math.factorial(d) and coeffs <= {1, -1}
        agree, roots = 0, []
        for p in primes:
            w = root_of_unity(d, p)
            roots.append(w)
            st = Stream(seed, f"jt/points/{d}/{p}")
            for _ in range(POINTS_PER_PRIME):
                X = [[st.below(p) for _ in range(d)] for _ in range(d)]
                target = d * math.factorial(d) * det_mod(X, p) % p
                agree += r_mod(X, d, p, w, perms) == target
        entry = {"terms": n_terms, "coefficients": sorted(coeffs), "terms_ok": terms_ok, "points_agree": agree,
                 "roots": roots}
        if d in EXACT_D:
            same, bad, nonzero, block = exact_identity(d, perms)
            lemma_ok.append(lemma_check(d, block))
            block_sizes.append(len(block))
            entry.update({"identical": same, "differing_monomials": bad, "nonzero_monomials": nonzero,
                          "block_monomials": len(block)})
            cond[f"d = {d}: {n_terms} terms of coefficient +-1, identical to {n_terms} det_{d} over Z[omega]"] = (
                terms_ok and same)
        else:
            cond[f"d = {d}: {n_terms} terms of coefficient +-1, equal to {n_terms} det_{d} at all "
                 f"{POINTS_PER_PRIME * len(primes)} points"] = terms_ok and agree == POINTS_PER_PRIME * len(primes)
        info[d] = entry

    indep = {}
    for d in INDEP_D:
        w = root_of_unity(d, primes[0])
        r, n = independence_rank(d, primes[0], w, Stream(seed, f"jt/independence/{d}"), perms_by_d[d])
        indep[d] = (r, n)
    sym = {d: symmetries(d, perms_by_d[d]) for d in SYM_D}
    trans = {d: transpose_symmetry(d, perms_by_d[d]) for d in SYM_D}
    aff = {d: affine_lemma(d, perms_by_d[d]) for d in range(2, 8)}
    eqs = {d: equations(d, p) for d, p in EQ_PRIMES.items()}
    t1_entries, t1_matches, t1_bad, improve = table1_check()
    eq1 = eq1_identities()
    km = km_identity()
    classical = {d: integer_identity(block_classical(d), d, perms_by_d[d], 2 ** (d - 1) * math.factorial(d))[0]
                 for d in EXACT_D}
    gurvits = {d: integer_identity(block_gurvits(d), d, perms_by_d[d], math.factorial(d))[0] for d in EXACT_D}
    bound = 1.0
    for _ in range(POINTS_PER_PRIME * len(primes)):
        bound *= max(MODULAR_D) / min(primes)
    yn = lambda b: "yes" if b else "NO"
    t2_formula = {d: d ** 3 * euler_phi(d) * math.factorial(d) // 2 for d in TABLE2}

    values = {
        "exact": "identical to d*d! det_d over Z[omega]: " + ", ".join(
            f"d={d} {yn(info[d]['identical'])}" for d in EXACT_D),
        "exact_monomials": ("nonzero monomials of R_d: " + ", ".join(str(info[d]["nonzero_monomials"]) for d in EXACT_D)
                            + "; of P_d: " + ", ".join(str(s) for s in block_sizes)),
        "modular": "; ".join(f"d={d}: {info[d]['points_agree']} of {POINTS_PER_PRIME * len(primes)} points"
                             for d in MODULAR_D) + " (two primes, two points each)",
        "modular_small": "d=2..7 at the same points: " + ", ".join(
            f"{info[d]['points_agree']}/{POINTS_PER_PRIME * len(primes)}" for d in EXACT_D),
        "primes": "p = " + ", ".join(str(p) for p in primes) + " (both 1 mod 2520); omega_p of order d for d = 2..9",
        "error_bound": f"a wrong d = 9 identity passes four points with probability at most {bound:.1e}",
        "lemma": "P_d's coefficients as the Lemma states, d = 2..7: " + ", ".join(yn(x) for x in lemma_ok),
        "independence": "rank of the terms' values mod p: " + ", ".join(
            f"d={d} {r}/{n}" for d, (r, n) in indep.items()),
        "symmetries": ("|H| for d = 2..5: " + ", ".join(f"{sym[d]['distinct']}" for d in SYM_D)
                       + "; each fixes det and permutes the signed terms: "
                       + ", ".join(yn(sym[d]["all_ok"] and sym[d]["det_condition_agrees"]) for d in SYM_D)),
        "table2": ("printed " + ", ".join(str(TABLE2[d]) for d in TABLE2) + "; d^3 phi(d) d!/2: "
                   + ", ".join(str(t2_formula[d]) for d in TABLE2)),
        "affine_lemma": ("P_pi D in M iff pi affine, every pi, d = 2..7: " + ", ".join(yn(a[0]) for a in aff.values())
                         + "; |Aff_d| = d phi(d): " + yn(all(a[1] for a in aff.values()))),
        "transpose": "transposition permutes the signed terms: " + ", ".join(
            f"d={d} {'yes' if trans[d] else 'no'}" for d in SYM_D),
        "equations": "zero locus over F_p: " + ", ".join(
            f"d={d} (p={EQ_PRIMES[d]}) {eqs[d][0]} points, the {eqs[d][1]} [D^j P_s]: {yn(eqs[d][2])}" for d in eqs),
        "table1": f"Table 1: {t1_matches} of {t1_entries} printed entries match their formulas",
        "improvement": "d*d! below the classical, Derksen and Gurvits bounds for d = 3..9: " + yn(improve),
        "eq1_km": f"eq. 1: xy {yn(eq1[0])}, xyz {yn(eq1[1])}; Krishna-Makam det_3 as 5 products: {yn(km)}",
        "classical": "eq. 4, 2^(d-1) d! powers, identical for d = 2..7: " + ", ".join(yn(classical[d]) for d in EXACT_D),
        "gurvits": "eq. 7, (d+1) d! powers, identical for d = 2..7: " + ", ".join(yn(gurvits[d]) for d in EXACT_D),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond),
        "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"test": TEST, "conditions": cond, "controls": ctl, "primes": primes,
              "d": {str(d): v for d, v in info.items()},
              "independence": {str(d): {"rank": r, "terms": n} for d, (r, n) in indep.items()},
              "symmetries": {str(d): v for d, v in sym.items()},
              "transpose": {str(d): v for d, v in trans.items()},
              "affine_lemma": {str(d): {"lemma": a[0], "order": a[1]} for d, a in aff.items()},
              "equations": {str(d): {"p": EQ_PRIMES[d], "zeros": z, "expected": e, "equal": q}
                            for d, (z, e, q) in eqs.items()},
              "table1": {"entries": t1_entries, "matches": t1_matches, "mismatches": t1_bad, "improvement": improve},
              "table2": {"printed": TABLE2, "formula": t2_formula},
              "eq1": eq1, "krishna_makam": km, "classical": classical, "gurvits": gurvits,
              "lemma": dict(zip(EXACT_D, lemma_ok)), "error_bound": bound}
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
        sys.exit(f"jt: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
