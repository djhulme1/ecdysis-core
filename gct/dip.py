"""Multiplicity obstructions where occurrence obstructions cannot separate (Dörfler, Ikenmeyer & Panova 2019).

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:0aa372d02c7fd9e0) is from Dörfler,
Ikenmeyer and Panova, "On geometric complexity theory: Multiplicity obstructions are stronger than occurrence
obstructions" (arXiv:1901.04576, v1, January 2019, the only version), its abstract: "This paper provides for the
first time a setting where separating with multiplicities can be achieved, while the separation with occurrences is
provably impossible."

The setting, as the paper's Section 2 defines it. A^n_m is the space of forms of degree n in m variables, Ch^n_m the
products of n linear forms (the Chow variety) and Pow^n_{m,k} the closure of the sums of k n-th powers of linear
forms (the forms of border Waring rank at most k). If Pow^n_{m,k} lay inside Ch^n_m, restricting functions would give
mult_λ(C[Ch^n_m]_d) ≥ mult_λ(C[Pow^n_{m,k}]_d) for every partition λ; a λ with the reverse strict inequality is a
multiplicity obstruction, and an occurrence obstruction if moreover mult_λ(C[Ch^n_m]_d) = 0. The paper's Theorem 2.3:
(1) for m ≥ 3, n ≥ 2, k = d = n + 1, λ = (n² − 2, n, 2) is a multiplicity obstruction; (2a) for k = 4, n = 6, m = 3,
d = 7, λ = (34, 6, 2), mult_λ(C[Ch]_7) = 7 < 8 = mult_λ(C[Pow]_7); (2b) for k = 4, n = 7, m = 4, d = 8,
λ = (47, 7, 2), mult_λ(C[Ch]_8) < 11 = mult_λ(C[Pow]_8); and neither separation can be achieved with occurrence
obstructions, which the paper shows by a large computation over the generators of the semigroup of partitions with a
positive plethysm coefficient (88 for n = 6, 948 for n = 7). Its Proposition 3.2 gets the two Pow multiplicities by a
computer calculation (8 and 11 tableaux, evaluated at random points of Pow^6_{3,4} and Pow^7_{3,4}), its plethysm
coefficients from the LiE software, and the Chow side from its Lemma 3.4, mult_λ(C[Ch^n_m]_d) ≤ a_λ(n[d]), with
Theorem 3.5, a_λ((n + 1)[n]) = 1 + a_λ(n[n + 1]) for λ = (n² − 2, n, 2).

The test (TEST below) recomputes the multiplicity obstructions: the two finite settings, the family for n up to 8, and
that λ itself occurs in the Chow variety's coordinate ring in the finite settings (else it would be an occurrence
obstruction). It does not check the paper's semigroup computation, the rest of the second half of the quote.

The input is the paper's e-print (arXiv's non-exclusive licence), read for its tableaux only: the 8 of
calculations_brill.tex and the 11 of multobs.tex's section on Proposition 3.2, used by control (f).

Rules, committed before any multiplicity, plethysm coefficient or weight multiplicity of the test's cases was
computed (the module was timed beforehand on other weights only):

1. Coordinates. Forms in A^n_3 are h = sum_a h_a x^a over exponent vectors a = (a1, a2, a3), |a| = n (VECTORS gives
   their order). Functions on A^n_3 of degree d are polynomials in the coordinates c_a (c_a(h) = h_a); a monomial is a
   multiset of d exponent vectors, its weight their sum. GL_3 acts on functions by (g.f)(h) = f(g^T h), which is the
   action (g.f)(h) = f(g^(-1) h) of the paper composed with the automorphism g -> (g^T)^(-1) of GL_3, so the two have
   the same multiplicities; under it c_a has weight a, the degree-d functions are Sym^d(Sym^n C^3), and
   mult_λ(C[A^n_3]_d) is the plethysm coefficient a_λ(d[n]) as in the paper. Its raising operators act as the
   derivations E12 = sum_b (b1 + 1) c_(b + e1 - e2) d/dc_b (over b with b2 ≥ 1) and E23 = sum_b (b2 + 1)
   c_(b + e2 - e3) d/dc_b (over b with b3 ≥ 1), from E21 and E32 acting on Sym^n C^3 as derivations.
2. Highest weight vectors. HWV_λ(C[A^n_3]_d) is the subspace of the weight-λ functions killed by E12 and E23, computed
   as the kernel of the integer matrix of E12 and E23 from the weight-λ monomials to those of weights λ + e1 - e2 and
   λ + e2 - e3, by Gaussian elimination modulo each prime of PRIMES.
3. Multiplicities in coordinate rings. For a variety Z, mult_λ(C[Z]_d) is the dimension of the restriction of
   HWV_λ(C[A]_d) to Z (taking highest weight vectors is exact for GL_3), computed as the rank modulo the prime of the
   matrix of the kernel basis evaluated at seed-drawn points of Z: a_λ(d[n]) + 6 points, each linear form's three
   coefficients drawn uniformly from 1 to p - 1. A point of Pow^n_{3,k} is sum_{i=1..k} (u_i . x)^n, a point of Ch^n_3
   is prod_{j=1..n} (u_j . x), and a generic point has its coefficients drawn directly. A rank is the multiplicity when
   both primes give it; when they differ, the case is reported and its condition does not hold. For a λ of 3 rows the
   multiplicities do not depend on m ≥ 3: a weight-λ function involves only the c_a with a4 = ... = 0, so on Pow^n_{m,k}
   and Ch^n_m it only sees their images in A^n_3, which are Pow^n_{3,k} and Ch^n_3. So (2b) is computed with m = 3, as
   the paper's Proposition 3.2 computes it.
4. Plethysm coefficients, exactly: a_λ(d[n]) = sum over σ in S_3 of sgn(σ) K(λ + δ - σ(δ)), δ = (2, 1, 0), K(μ) the
   number of multisets of d exponent vectors of degree n summing to μ (0 if μ has a negative part), counted by dynamic
   programming over the vectors. This is the alternating sum that recovers the multiplicity of each highest weight from
   the weight multiplicities of a polynomial GL_3-representation.
5. The test's conditions:
   C1: a_(34,6,2)(7[6]) = 8, mult_(34,6,2)(C[Pow^6_{3,4}]_7) = 8 and 0 < mult_(34,6,2)(C[Ch^6_3]_7) < 8.
   C2: a_(47,7,2)(8[7]) = 11, mult_(47,7,2)(C[Pow^7_{3,4}]_8) = 11 and 0 < mult_(47,7,2)(C[Ch^7_3]_8) < 11.
   C3: for every n from 2 to 8, with k = d = n + 1 and λ = (n² - 2, n, 2), mult_λ(C[Ch^n_3]_d) < mult_λ(C[Pow^n_{3,k}]_d).
   The test passes when all three hold.

Beside the test, not counted: the Chow multiplicities themselves (the paper gives 7 for (2a)), a_λ(n[d]) for each case
(the paper's Lemma 3.4 bound), and Theorem 3.5's difference a_λ((n + 1)[n]) - a_λ(n[n + 1]) for n from 2 to 10.

Controls (controls_passed of controls_total):
 (a) Plethysm coefficients against the dimension identity sum_λ a_λ(d[n]) dim S_λ(C^3) = dim Sym^d(Sym^n C^3) for
     every (d, n) with 2 ≤ d, n and d n ≤ 15, and against the classical decompositions Sym^2(Sym^2 C^3) = (4) + (2,2) and
     Sym^3(Sym^2 C^3) = (6) + (4,2) + (2,2,2).
 (b) Hermite reciprocity, a_λ(d[n]) = a_λ(n[d]) for every 2-row λ, d and n from 1 to 6.
 (c) In every case computed: the kernel's dimension at each prime equals a_λ(d[n]) of rule 4, and the rank at generic
     points equals it too (the basis is independent as functions).
 (d) Lemma 3.4: every Chow multiplicity computed is at most a_λ(n[d]).
 (e) The paper's occurrence obstructions for m = 3 (its Proposition 3.16): (2,2,2) for n = 2, d = 3; (7,3,2) for n = 3,
     d = 4; (11,9,8) for n = 4, d = 7; (12,9,9) for n = 5, d = 6: a_λ(d[n]) = 1, a_λ(n[d]) = 0, Chow multiplicity 0 and
     Pow^n_{3,d} multiplicity 1.
 (f) The paper's own certificates: its 8 tableaux of shape (34,6,2) and 11 of shape (47,7,2), each label 1 to d
     appearing n times and each column strictly increasing, give functions whose values at the test's Pow points have
     rank 8 and 11 at both primes. A tableau T gives f_T(sum_i l_i^n) = sum over (i_1, ..., i_d) in [k]^d of the
     product over the columns of det[l_(i_T(r,c))(e_s)]_(r,s ≤ height), the contraction of the paper's Section 6.
"""

import hashlib
import json
import math
import os
import re
import sys
import tarfile
import io
from itertools import permutations

import numpy as np

PRIMES = (2147483647, 2147483629)
EPRINT = "dip-1901.04576v1.tar.gz"
EPRINT_SHA256 = "f7b2cdd4f632500efa34722256103b2642d122425bdeef010368e624a4ecb527"
INPUTS = {EPRINT: EPRINT_SHA256}
EXTRA_POINTS = 6
FAMILY = range(2, 9)
THEOREM_35 = range(2, 11)
OCCURRENCE = (((2, 2, 2), 2, 3), ((7, 3, 2), 3, 4), ((11, 9, 8), 4, 7), ((12, 9, 9), 5, 6))
TEST = ("Refuted if, computed exactly (plethysm coefficients from weight multiplicities; a multiplicity in a "
        "coordinate ring as the rank, modulo two primes near 2^31, of the type-λ highest weight vectors evaluated at "
        "seed-drawn points of the variety), λ = (34,6,2) is not a multiplicity obstruction with 0 < mult in "
        "C[Ch^6_3]_7 < mult in C[Pow^6_{3,4}]_7 = 8 = a_λ(7[6]), or λ = (47,7,2) not one with 0 < mult in C[Ch^7_3]_8 "
        "< 11 = mult in C[Pow^7_{3,4}]_8 = a_λ(8[7]); or, for some n from 2 to 8, (n²-2,n,2) is not one for "
        "Pow^n_{3,n+1} against Ch^n_3 in degree n+1.")


class Refused(Exception):
    pass


class Stream:
    def __init__(self, seed, label):
        self.seed, self.label, self.n = seed, label, 0

    def below(self, m):
        self.n += 1
        h = hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
        return int.from_bytes(h[:8], "big") % m


# ---------------------------------------------------------------- exponent vectors and weights

def vectors(n):
    """The exponent vectors of degree n in 3 variables, a1 descending, then a2 descending."""
    return [(a1, a2, n - a1 - a2) for a1 in range(n, -1, -1) for a2 in range(n - a1, -1, -1)]


def weight_count(mu, d, n):
    """K(μ): multisets of d exponent vectors of degree n summing to μ (rule 4), by dynamic programming."""
    if any(x < 0 for x in mu) or sum(mu) != d * n:
        return 0
    states = {(0, 0, 0): 1}  # (count, s1, s2) -> number of ways; s3 = count n - s1 - s2
    for a in vectors(n):
        new = {}
        for (c, s1, s2), w in states.items():
            t = 0
            while c + t <= d:
                t1, t2 = s1 + t * a[0], s2 + t * a[1]
                t3 = (c + t) * n - t1 - t2
                if t1 > mu[0] or t2 > mu[1] or t3 > mu[2]:
                    break
                key = (c + t, t1, t2)
                new[key] = new.get(key, 0) + w
                t += 1
        states = new
    return states.get((d, mu[0], mu[1]), 0)


SHIFTS = (((0, 0, 0), 1), ((1, -1, 0), -1), ((2, 0, -2), -1), ((0, 1, -1), -1), ((1, 1, -2), 1), ((2, -1, -1), 1))


def plethysm(lam, d, n):
    """a_λ(d[n]) by rule 4: sum over σ of sgn(σ) K(λ + δ - σ(δ)); SHIFTS lists δ - σ(δ) with sgn(σ)."""
    lam = tuple(lam) + (0,) * (3 - len(lam))
    return sum(s * weight_count(tuple(l + x for l, x in zip(lam, sh)), d, n) for sh, s in SHIFTS)


def dim_schur(lam):
    l1, l2, l3 = tuple(lam) + (0,) * (3 - len(lam))
    return (l1 - l2 + 1) * (l2 - l3 + 1) * (l1 - l3 + 2) // 2


def partitions3(total):
    out = []
    for l1 in range(total, -1, -1):
        for l2 in range(min(l1, total - l1), -1, -1):
            l3 = total - l1 - l2
            if 0 <= l3 <= l2:
                out.append((l1, l2, l3))
    return out


# ---------------------------------------------------------------- highest weight vectors (rules 1 and 2)

def monomials(mu, d, n):
    """Every multiset of d exponent vectors of degree n summing to μ, as a sorted tuple of vector indices."""
    vs = vectors(n)
    out = []

    def rec(start, left, rem, acc):
        if left == 0:
            if rem == (0, 0, 0):
                out.append(tuple(acc))
            return
        for i in range(start, len(vs)):
            a = vs[i]
            if a[0] > rem[0] or a[1] > rem[1] or a[2] > rem[2]:
                continue
            nxt = (rem[0] - a[0], rem[1] - a[1], rem[2] - a[2])
            # every later vector has a1 ≤ a[0]: the rest must still fit
            if nxt[0] > (left - 1) * a[0]:
                continue
            acc.append(i)
            rec(i, left - 1, nxt, acc)
            acc.pop()

    if all(x >= 0 for x in mu) and sum(mu) == d * n:
        rec(0, d, tuple(mu), [])
    return out


def raising_matrix(lam, d, n):
    """The integer matrix of E12 and E23 on the weight-λ monomials (columns) into weights λ+e1-e2 and λ+e2-e3 (rows)."""
    vs = vectors(n)
    index = {a: i for i, a in enumerate(vs)}
    cols = monomials(lam, d, n)
    rows = {}
    entries = {}
    for j, mono in enumerate(cols):
        counts = {}
        for i in mono:
            counts[i] = counts.get(i, 0) + 1
        for i, mult in counts.items():
            b = vs[i]
            for (src, dst, coef_axis) in ((1, 0, 0), (2, 1, 1)):  # E12: b2 >= 1, b -> b + e1 - e2; E23 likewise
                if b[src] < 1:
                    continue
                nb = list(b)
                nb[src] -= 1
                nb[dst] += 1
                coef = mult * (b[coef_axis] + 1)
                new = list(mono)
                new.remove(i)
                new.append(index[tuple(nb)])
                key = (src, tuple(sorted(new)))
                r = rows.setdefault(key, len(rows))
                entries[(r, j)] = entries.get((r, j), 0) + coef
    return cols, len(rows), entries


def rref_mod(m, p):
    """Row reduce an int64 array modulo p in place; return the pivot columns."""
    m %= p
    pivots = []
    r = 0
    rows, cols = m.shape
    for c in range(cols):
        if r >= rows:
            break
        nz = np.nonzero(m[r:, c])[0]
        if nz.size == 0:
            continue
        k = r + int(nz[0])
        if k != r:
            m[[r, k]] = m[[k, r]]
        inv = pow(int(m[r, c]), p - 2, p)
        m[r] = (m[r] * inv) % p
        col = m[:, c].copy()
        col[r] = 0
        nzr = np.nonzero(col)[0]
        if nzr.size:
            m[nzr] = (m[nzr] - (col[nzr, None] * m[r][None, :]) % p) % p
        pivots.append(c)
        r += 1
    return pivots


def rank_mod(rows, p):
    if not rows or not rows[0]:
        return 0
    m = np.array(rows, dtype=np.int64)
    return len(rref_mod(m, p))


def kernel_mod(nrows, ncols, entries, p):
    """A basis of the kernel modulo p of the sparse integer matrix, as rows of length ncols."""
    if ncols == 0:
        return []
    if nrows == 0:
        return [[1 if j == i else 0 for j in range(ncols)] for i in range(ncols)]
    m = np.zeros((nrows, ncols), dtype=np.int64)
    for (r, c), v in entries.items():
        m[r, c] = v % p
    pivots = rref_mod(m, p)
    free = [c for c in range(ncols) if c not in set(pivots)]
    basis = []
    for f in free:
        v = [0] * ncols
        v[f] = 1
        for i, pc in enumerate(pivots):
            v[pc] = int((-m[i, f]) % p)
        basis.append(v)
    return basis


# ---------------------------------------------------------------- points (rule 3)

def multinomial(n, a):
    return math.factorial(n) // (math.factorial(a[0]) * math.factorial(a[1]) * math.factorial(a[2]))


def linear_forms(stream, count, p):
    return [tuple(1 + stream.below(p - 1) for _ in range(3)) for _ in range(count)]


def pow_point(n, forms, p):
    vs = vectors(n)
    return [sum(multinomial(n, a) * pow(u[0], a[0], p) * pow(u[1], a[1], p) * pow(u[2], a[2], p)
                for u in forms) % p for a in vs]


def ch_point(n, forms, p):
    poly = {(0, 0, 0): 1}
    for u in forms:
        new = {}
        for e, c in poly.items():
            for axis in range(3):
                ne = list(e)
                ne[axis] += 1
                ne = tuple(ne)
                new[ne] = (new.get(ne, 0) + c * u[axis]) % p
        poly = new
    return [poly.get(a, 0) for a in vectors(n)]


def evaluate(basis, cols, point, p):
    """The values of the basis functions (rows of coefficients on the monomials cols) at one point."""
    vals = []
    for mono in cols:
        v = 1
        for i in mono:
            v = v * point[i] % p
        vals.append(v)
    return [sum(b * v for b, v in zip(vec, vals)) % p for vec in basis]


def case(lam, d, n, seed, label, varieties):
    """Rules 1 to 3 for one (λ, d, n): kernel dimensions, generic ranks and the ranks on each variety, at each prime.
    varieties: {name: ('pow', k) or ('ch', None)}."""
    cols, nrows, entries = raising_matrix(lam, d, n)
    a = plethysm(lam, d, n)
    out = {"lambda": list(lam), "d": d, "n": n, "a": a, "a_swap": plethysm(lam, n, d), "monomials": len(cols),
           "kernel": [], "generic": [], "ranks": {name: [] for name in varieties}, "points": a + EXTRA_POINTS}
    for p in PRIMES:
        basis = kernel_mod(nrows, len(cols), entries, p)
        out["kernel"].append(len(basis))
        npts = a + EXTRA_POINTS
        st = Stream(seed, f"{label}/generic/{p}")
        gen = [evaluate(basis, cols, [1 + st.below(p - 1) for _ in vectors(n)], p) for _ in range(npts)]
        out["generic"].append(rank_mod([list(r) for r in zip(*gen)] if basis else [], p))
        for name, (kind, k) in varieties.items():
            st = Stream(seed, f"{label}/{name}/{p}")
            vals = []
            for _ in range(npts):
                if kind == "pow":
                    pt = pow_point(n, linear_forms(st, k, p), p)
                else:
                    pt = ch_point(n, linear_forms(st, n, p), p)
                vals.append(evaluate(basis, cols, pt, p))
            out["ranks"][name].append(rank_mod([list(r) for r in zip(*vals)] if basis else [], p))
    return out


def mult(c, name):
    r = c["ranks"][name]
    return r[0] if len(set(r)) == 1 else None


# ---------------------------------------------------------------- the paper's tableaux (control f)

def read_tableaux(tar_bytes):
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tf:
        files = {os.path.basename(m.name): tf.extractfile(m).read().decode("utf-8") for m in tf.getmembers()
                 if m.isfile()}
    brill = files.get("calculations_brill.tex")
    main = files.get("multobs.tex")
    if brill is None or main is None:
        raise Refused("the e-print lacks calculations_brill.tex or multobs.tex")
    t34 = []
    for block in brill.split("\\begin{array}")[1:]:
        block = block.split("\\end{array}")[0]
        rows = [[int(x) for x in re.findall(r"\\lr\{(\d+)\}", line)] for line in block.split("\\\\")]
        rows = [r for r in rows if r]
        t34.append(rows)
    start = main.find("using the following 11 tableaux")
    end = main.find("\\end{longtable}", start)
    if start < 0 or end < 0:
        raise Refused("multobs.tex: the 11 tableaux were not found")
    t47 = [[[int(ch) for ch in row] for row in m.split(",")]
           for m in re.findall(r"\\young\(([0-9,]+)\)", main[start:end])]
    return t34, t47


def check_tableau(t, lam, d, n):
    if [len(r) for r in t] != list(lam):
        return False
    labels = [x for r in t for x in r]
    if sorted(labels) != sorted(list(range(1, d + 1)) * n):
        return False
    for c in range(len(t[0])):
        col = [t[r][c] for r in range(len(t)) if c < len(t[r])]
        if any(col[i] >= col[i + 1] for i in range(len(col) - 1)):
            return False
    return True


def det_mod(rows, p):
    h = len(rows)
    if h == 1:
        return rows[0][0] % p
    if h == 2:
        return (rows[0][0] * rows[1][1] - rows[0][1] * rows[1][0]) % p
    if h == 3:
        a, b, c = rows
        return (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
                + a[2] * (b[0] * c[1] - b[1] * c[0])) % p
    raise ValueError("height above 3")


def tableau_value(t, d, forms, p):
    """f_T(sum_i l_i^n): the sum over (i_1, ..., i_d) in [k]^d of the product of the columns' determinants."""
    k = len(forms)
    width = len(t[0])
    types = {}
    for c in range(width):
        labels = tuple(t[r][c] for r in range(len(t)) if c < len(t[r]))
        types[labels] = types.get(labels, 0) + 1
    total = np.ones((k,) * d, dtype=np.int64)
    for labels, count in types.items():
        h = len(labels)
        table = np.zeros((k,) * h, dtype=np.int64)
        for idx in np.ndindex(*((k,) * h)):
            rows = [forms[i][:h] for i in idx]
            table[idx] = pow(det_mod(rows, p), count, p)
        # broadcast the table along the labels' axes (labels 1..d are axes 0..d-1, distinct within a column)
        shape = [1] * d
        order = sorted(range(h), key=lambda i: labels[i])
        tt = np.transpose(table, order)
        for i in range(h):
            shape[labels[order[i]] - 1] = k
        total = (total * tt.reshape(shape)) % p
    return int(total.sum() % p)


def tableau_rank(ts, d, k, seed, label, p, npts):
    st = Stream(seed, f"{label}/pow/{p}")
    vals = []
    for _ in range(npts):
        forms = linear_forms(st, k, p)
        vals.append([tableau_value(t, d, forms, p) for t in ts])
    return rank_mod([list(r) for r in zip(*vals)], p)


# ---------------------------------------------------------------- the run

def assess(seed, tar_bytes):
    cases = {}
    cases["34"] = case((34, 6, 2), 7, 6, seed, "34", {"pow": ("pow", 4), "ch": ("ch", None)})
    cases["47"] = case((47, 7, 2), 8, 7, seed, "47", {"pow": ("pow", 4), "ch": ("ch", None)})
    family = {}
    for n in FAMILY:
        family[n] = case((n * n - 2, n, 2), n + 1, n, seed, f"family/{n}",
                         {"pow": ("pow", n + 1), "ch": ("ch", None)})
    occ = {}
    for lam, n, d in OCCURRENCE:
        occ[lam] = case(lam, d, n, seed, f"occurrence/{lam}", {"pow": ("pow", d), "ch": ("ch", None)})

    def obstruction(c, a_expected, pow_expected):
        ch, pw = mult(c, "ch"), mult(c, "pow")
        return (c["a"] == a_expected and pw == pow_expected and ch is not None and 0 < ch < pw)

    c1 = obstruction(cases["34"], 8, 8)
    c2 = obstruction(cases["47"], 11, 11)
    c3 = all(mult(c, "ch") is not None and mult(c, "pow") is not None and mult(c, "ch") < mult(c, "pow")
             for c in family.values())
    cond = {"C1 (34,6,2)": c1, "C2 (47,7,2)": c2, "C3 family n = 2 to 8": c3}

    # controls
    ctl = {}
    ok_a = True
    dims = []
    for d in range(2, 8):
        for n in range(2, 8):
            if d * n > 15:
                continue
            total = sum(plethysm(lam, d, n) * dim_schur(lam) for lam in partitions3(d * n))
            want = math.comb(math.comb(n + 2, 2) + d - 1, d)
            dims.append([d, n, total, want])
            ok_a &= total == want
    known = {(2, 2): {(4, 0, 0): 1, (2, 2, 0): 1}, (3, 2): {(6, 0, 0): 1, (4, 2, 0): 1, (2, 2, 2): 1}}
    for (d, n), dec in known.items():
        for lam in partitions3(d * n):
            ok_a &= plethysm(lam, d, n) == dec.get(lam, 0)
    ctl["(a) plethysm dimension identity and classical decompositions"] = ok_a
    ok_b = True
    for d in range(1, 7):
        for n in range(1, 7):
            for lam in partitions3(d * n):
                if lam[2] == 0:
                    ok_b &= plethysm(lam, d, n) == plethysm(lam, n, d)
    ctl["(b) Hermite reciprocity for 2-row partitions, d, n ≤ 6"] = ok_b
    every = list(cases.values()) + list(family.values()) + list(occ.values())
    ctl["(c) kernel and generic rank equal the plethysm coefficient"] = all(
        all(k == c["a"] for k in c["kernel"]) and all(g == c["a"] for g in c["generic"]) for c in every)
    ctl["(d) Lemma 3.4: Chow multiplicity at most a_λ(n[d])"] = all(
        mult(c, "ch") is not None and mult(c, "ch") <= c["a_swap"] for c in every)
    ctl["(e) the paper's occurrence obstructions for m = 3"] = all(
        c["a"] == 1 and c["a_swap"] == 0 and mult(c, "ch") == 0 and mult(c, "pow") == 1 for c in occ.values())
    t34, t47 = read_tableaux(tar_bytes)
    shapes_ok = (len(t34) == 8 and len(t47) == 11 and all(check_tableau(t, (34, 6, 2), 7, 6) for t in t34)
                 and all(check_tableau(t, (47, 7, 2), 8, 7) for t in t47))
    tab = {"34": [], "47": []}
    if shapes_ok:
        for p in PRIMES:
            tab["34"].append(tableau_rank(t34, 7, 4, seed, "34", p, 8 + EXTRA_POINTS))
            tab["47"].append(tableau_rank(t47, 8, 4, seed, "47", p, 11 + EXTRA_POINTS))
    ctl["(f) the paper's tableaux give ranks 8 and 11 on Pow"] = shapes_ok and tab["34"] == [8, 8] and tab["47"] == [
        11, 11]

    th35 = {n: plethysm((n * n - 2, n, 2), n + 1, n) - plethysm((n * n - 2, n, 2), n, n + 1) for n in THEOREM_35}

    def show(x):
        return "disagree" if x is None else str(x)

    met = sum(cond.values())
    out = {
        "a_34": cases["34"]["a"], "a_34_swap": cases["34"]["a_swap"],
        "pow_34": show(mult(cases["34"], "pow")), "ch_34": show(mult(cases["34"], "ch")),
        "a_47": cases["47"]["a"], "a_47_swap": cases["47"]["a_swap"],
        "pow_47": show(mult(cases["47"], "pow")), "ch_47": show(mult(cases["47"], "ch")),
        "tableaux": f"paper's tableaux on Pow: (34,6,2) rank {tab['34']}, (47,7,2) rank {tab['47']} (two primes)",
        "family": "n: Ch < Pow (k = d = n+1): " + "; ".join(
            f"{n}: {show(mult(c, 'ch'))} < {show(mult(c, 'pow'))}" for n, c in family.items()),
        "family_a": "n: a(d[n]) / a(n[d]): " + "; ".join(f"{n}: {c['a']}/{c['a_swap']}" for n, c in family.items()),
        "theorem_3_5": "a((n+1)[n]) - a(n[n+1]) for n = 2 to 10: " + ", ".join(str(v) for v in th35.values()),
        "conditions_met": met, "conditions_total": len(cond), "test_passed": int(met == len(cond)),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    for k, v in out.items():
        if isinstance(v, str) and len(v) > 200:
            raise AssertionError(f"{k}: longer than 200 characters: {v}")
    detail = {"test": TEST, "conditions": cond, "controls": ctl, "dimension_identity": dims,
              "cases": cases, "family": {str(n): c for n, c in family.items()},
              "occurrence": {str(k): c for k, c in occ.items()}, "tableau_ranks": tab, "theorem_3_5": th35}
    return out, detail


def read_bytes(path, sha256):
    with open(path, "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha256:
        raise Refused(f"{path}: sha256 {got}, not the registered {sha256}")
    return data


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    tar_bytes = read_bytes(os.path.join(inputs, EPRINT), EPRINT_SHA256)
    out, detail = assess(seed, tar_bytes)
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="utf-8") as fh:
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
        sys.exit(f"dip: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
