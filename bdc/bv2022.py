#!/usr/bin/env python3
"""Bogart & Valero's two generalised permanents: the determinantal representations of sizes 3^n and
prod(m_i + 1) - 1 that Grenet's method builds on the n-cube's face lattice and on a lattice of multisets, and the
Hessian lower bounds at the paper's explicit zeros, decided exactly in finite ranges.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:5583d957847c7474) is from T. Bogart and
J. A. Valero, "Bounds on Determinantal Complexity of Two Types of Generalized Permanents", arXiv:2202.13016v1
(25 February 2022, the only version, CC BY 4.0; Theoretical Computer Science 1071, 115862, May 2026), its abstract:
"We define two new families of polynomials that generalize permanents and prove upper and lower bounds on their
determinantal complexities comparable to the known bounds for permanents."

The paper, as the e-print's TeX states it (its numbering). Definition 1.1: hoperm_n is the sum over sigma in S_n and
eps in {1, -1}^n of prod_i x_{i, eps_i sigma(i)}, in the 2n^2 variables x_{i,j}, 1 <= i <= n, 1 <= |j| <= n.
Definition 1.2: for a composition m = (m_1, ..., m_n) of gamma, mperm_m is the sum over the maps sigma: [gamma] -> [n]
with |sigma^-1(j)| = m_j of the product of x_{i, sigma(i)} over the rows i = 1, ..., gamma (the TeX's product runs to
n, a slip: the polynomial lives on the gamma x n matrix of its Section 3, and Lemma 3.10 counts its terms as the
words of length gamma). Theorem 1.3: dc(hoperm_n) <= 3^n and dc(mperm_m) <= prod(m_i + 1) - 1, by Proposition 2.1
(Grenet's cycle covers on a graded poset with one minimum and one maximum and p elements give size p - 1). Theorem
1.4, for n >= 3 in characteristic zero: dc(hoperm_n) >= n^2/2 and dc(mperm_m) >= (m_1 + ... + m_n)^2/2, by Corollary
3.3 (dc(f) is at least half the rank of f's Hessian at any zero of f, after Mignon and Ressayre) at the zeros of
Propositions 3.7 and 3.11, whose Hessians Propositions 3.8 and 3.13 print.

The test, as registered: see TEST below. Every rule was fixed before this module evaluated any of the paper's
matrices, zeros or Hessians: its tests run the machinery on other posets, on compositions and partitions of 9 and on
other polynomials. Read by hand before the rules, and reported beside (rule 6), not tested:
- Theorem 1.4(2) cannot hold as printed. Its proof shows the gamma n x gamma n Hessian at B^(l) nonsingular, which
  gives dc(mperm_m) >= gamma n/2; and (m_1 + ... + m_n)^2/2 exceeds Theorem 1.3(2)'s own size prod(m_i + 1) - 1 at
  m = (5, 1, 1): 24.5 against 23.
- hoperm_n(X) is per_n(X+ + X-), X+ and X- the n x n matrices of the variables with positive and with negative column
  indices: the sum over eps factorises row by row. So dc(hoperm_n) = dc(per_n): Grenet's 2^n - 1 matrix, each x_ij
  replaced by the linear form x_{i,j} + x_{i,-j}, represents hoperm_n, smaller than 3^n for every n; and setting X- = 0
  gives per_n, so Theorem 1.4(1) is Mignon and Ressayre's bound for the permanent.
- Working Proposition 3.13's sums by hand, R^(1)'s factor comes out (gamma - 3)!/prod m_j!, not the printed
  k_1 = (gamma - 2)!/prod m_j! (Q^(1)'s, R^(2)'s and Q^(2)'s agree with the printed ones); a nonzero factor does not
  change the rank, and the comparison reports a scalar mismatch as such.
- The face lattice as the proof describes it has the cube's 2^n vertices as maxima, while Proposition 2.1 needs one:
  a top is added above them (rule 2), which is the reading that gives 3^n + 1 elements and so the size 3^n.

1. Proposition 2.1's matrix, for a graded poset of rank d with one minimum and one maximum and its cover relations
   labelled: its rows and columns are the elements but the maximum, which is merged with the minimum into vertex 0
   (elements ordered by rank, then lexicographically); each cover x < y puts its label in row x, column y (column 0
   when y is the maximum); the diagonal holds 1 at every vertex but vertex 0; and when d is even the row of vertex 0
   is negated, the proof's "multiplying any single row of A by -1". An entry is an integer or c times a variable,
   c = 1 or -1.
2. The two lattices. (a) Theorem 1.3(1): the faces of the n-cube are the vectors u in {-1, 0, 1}^n, u covered by v
   when v sets one zero coordinate j of u to 1 or -1, the arc labelled x_{i, j} or x_{i, -j} with the sign of v_j and
   i = rank(u) + 1 (the proof's "i is the rank (= number of nonzero coordinates) of u" counts the first layer from 0,
   which no row of the matrix carries; the lab's Grenet check read "S in V_i" the same way). A top is added above the
   2^n vertices, each covered by it with label 1: rank n + 1, 3^n + 1 elements, a 3^n-square matrix. (b) Theorem
   1.3(2): the multisets inside {1^m_1, ..., n^m_n} are the vectors a with 0 <= a_j <= m_j, a covered by a + e_j with
   label x_{|a| + 1, j} (the proof's "if T is a multiset of size i ... label this edge by x_ij", read the same way):
   rank gamma, prod(m_i + 1) elements, a (prod(m_i + 1) - 1)-square matrix.
3. The determinants. When a matrix has at most 81 rows (the cube for n <= 4; the compositions whose lattices have at
   most 82 elements), every nonzero term of its Leibniz expansion is enumerated as a cycle cover of its digraph (the
   enumeration of bdc/grenet.py, extended to entries -x: the smallest uncovered vertex is put on its loop, if it has
   one, or on each simple cycle through it among the uncovered vertices, in turn; with one pruning that cannot lose a
   cover, since vertex 0 is the first covered: a walk from any other vertex steps only to vertices from which its
   start can be reached without passing through vertex 0), the terms are collected as
   monomials with integer coefficients, and the result must equal the polynomial by its definition, monomial by
   monomial: one monomial of coefficient 1 for each signed permutation, or for each word with m_j letters j. This
   uses nothing of the paper's argument. Otherwise, at four points drawn from the seed (each variable an integer from
   0 to 2^31 - 2, by SHA-256 of the seed, a label and a counter, as bdc/grenet.py draws them), the determinant modulo
   2^31 - 1 (bdc/grenet.py's elimination) must equal the polynomial's value by its definition modulo the same prime.
   A nonzero polynomial of degree at most 729 vanishes at a random point with probability at most 729/(2^31 - 1), so
   four agreements leave a wrong matrix a chance below 1.4e-26.
4. The zeros and Hessians. hoperm_n, for n = 3 to 6: B is the n x 2n matrix with b_{n,n} = 1 - 2n (column +n) and
   every other entry 1 (Proposition 3.7). hoperm_n(B) is computed by Definition 1.1 in integers; the Hessian at B is
   taken over the 2n^2 variables in Proposition 3.8's order (x_{1,1}, ..., x_{1,n}, ..., x_{n,n}, then x_{1,-1}, ...,
   x_{n,-n}), each entry the sum, over the monomials containing both variables, of the product of the other
   variables' values (the second derivative of a polynomial of degree at most one in each variable; 0 on the
   diagonal), and its rank over the rationals by exact elimination in fractions. mperm_m, for every partition of
   gamma = 3 to 8 into n >= 3 parts, at B^(l) of Proposition 3.11: l = 2 when all parts are equal, b_{1,1} = 1 - n
   and every other entry 1; otherwise l = 1, b_{gamma,j} = 1 - gamma/(c m_1) for the c parts j equal to the largest,
   m_1, and every other entry 1. The point is multiplied by D = c m_1 (D = 1 for l = 2) to make it integral: mperm_m
   is homogeneous of degree gamma, so its value scales by D^gamma and its Hessian by D^(gamma - 2), and neither the
   zero nor the rank changes. mperm_m there and the gamma n x gamma n Hessian over x_{1,1}, ..., x_{1,n}, ...,
   x_{gamma,n} are computed as for hoperm_n.
5. The test's 24 conditions: (i) for n = 1 to 6, the cube's matrix is 3^n-square and its determinant is hoperm_n
   (rule 3); (ii) for gamma = 1 to 8, every composition of gamma has a (prod(m_i + 1) - 1)-square matrix whose
   determinant is mperm_m; (iii) for n = 3 to 6, hoperm_n(B) = 0 and the Hessian there has rank at least n^2, which
   with Corollary 3.3 gives dc(hoperm_n) >= n^2/2; (iv) for gamma = 3 to 8, every partition of gamma into at least 3
   parts has mperm_m(B^(l)) = 0 and a Hessian of rank gamma n there, which gives dc(mperm_m) >= gamma n/2, the bound
   the proof of Theorem 1.4(2) reaches. test_passed is 1 if all 24 hold.
6. Beside, none of it counted: (a) Proposition 3.8's printed matrix [[C, C], [C, C]] (C = 2^(n-2) (n-3)! times the
   blocks 0, A and (n-2)W, W = U - I) and Proposition 3.13's printed Q^(l) and R^(l) (with k_1 and k_2; 0 on the
   diagonal blocks, Q in the block row and column of the row in which B^(l) differs from 1, R elsewhere), each
   compared exactly with the Hessian of rule 4, a mismatch that is a scalar multiple reported with its factor;
   (b) Theorem 1.4(2) as printed: the compositions of gamma <= 8 into n >= 3 parts whose (m_1 + ... + m_n)^2/2 exceeds
   prod(m_i + 1) - 1, the size of a matrix rule 3 verifies, each with gamma n/2; and how many of rule 4's partitions
   have (m_1 + ... + m_n)^2/2 above gamma n/2; (c) hoperm_n(X) = per_n(X+ + X-) identically for n = 1 to 6, the
   product of the n binomials x_{i,sigma(i)} + x_{i,-sigma(i)} expanded for each sigma and summed, against
   Definition 1.1; and bdc/grenet.py's matrix with each x_ij replaced by x_{i,j} + x_{i,-j}, its determinant against
   hoperm_n at four seed-drawn points modulo 2^31 - 1 for n = 2 to 6 (sizes 3 to 63); (d) Lemma 3.1 (Mignon and
   Ressayre's Proposition 3.8): the Hessian of det_n at seed-drawn integer matrices of rank n - 1 and n - 2 has rank
   at most 2n, n = 2 to 6.
7. Controls (controls_passed counts those that behave as stated; the run stops if any fails): the expansion against
   the Leibniz sum on seed-drawn 5 x 5 matrices of constants and of variables with sign 1 or -1, and against
   bdc/grenet.py's expansion on its matrices for n = 2 to 5; the modular determinant against an exact fraction-free one
   (bdc/grenet.py's) on seed-drawn integer matrices of sizes 1 to 40; hoperm_n and mperm_m by definition against brute
   force over every map [n] -> {+-1, ..., +-n} and [gamma] -> [n] at seed-drawn integer points (n = 1 to 4; every
   composition of gamma <= 6 into at most 3 parts); the Hessian against second differences of the polynomial's
   values, f(y + e_p + e_q) - f(y + e_p) - f(y + e_q) + f(y), at every pair, for hoperm_3 and mperm_(2,1,1) at
   seed-drawn integer points; the exact rank against ranks modulo two primes and numpy's floating-point rank on
   seed-drawn integer matrices of planted ranks; and four planted faults, each caught: an arc's sign flipped in the
   cube's matrix for n = 3; the row negation omitted where the rank is even (the cube for n = 1 and 3; mperm_(1,1)
   and mperm_(2,1,1)), which gives -f; B's corner 1 - 2n replaced by 2 - 2n for n = 3 to 6, no longer a zero; and
   B^(1)'s changed entries raised by 1/(c m_1) for (2,1,1) and (3,2,1), no longer a zero.

What it cannot check: the theorems for n > 6 and gamma > 8, which rest on the paper's arguments; Lemma 3.1 and
Corollary 3.3 in general, on which the lower bounds rest; and whether the journal version corrects Theorem 1.4(2), its
formulas not having been read here.

Writes results/outputs.json and results/detail.json. Run with: python3 bdc/bv2022.py
"""

import importlib.util
import itertools
import json
import math
import os
import re
import sys
from fractions import Fraction

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("bdc_grenet_for_bv", os.path.join(HERE, "grenet.py"))
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)

P = G.P                      # 2^31 - 1
POINTS = 4
EXACT_ROWS = 81
CUBE_N = tuple(range(1, 7))
GAMMAS = tuple(range(1, 9))
HOPERM_LOWER = tuple(range(3, 7))
MPERM_LOWER = tuple(range(3, 9))
GRENET_SUM_N = tuple(range(2, 7))
MR_N = tuple(range(2, 7))
LIMIT = 200
TEST = ("Refuted if a bound the paper's proofs give fails where its construction or Hessian decides it: for n = 1 to "
        "6, the n-cube's face lattice labelled as Theorem 1.3's proof says, a top added, gives by Proposition 2.1 a "
        "3^n-square matrix whose determinant is not hoperm_n; for a composition m of γ ≤ 8, the multiset lattice "
        "gives a (Π(m_i + 1) − 1)-square one whose determinant is not mperm_m (identically up to 81 rows, else at "
        "four seed-drawn points mod 2^31 − 1); or, for n = 3 to 6 and each partition of γ ≤ 8 into n ≥ 3 parts, B or "
        "B^(ℓ) is not a zero or its Hessian has rank below n² or γn.")
OUTPUTS = ("cube_sizes", "cube_exact", "cube_terms", "cube_modular", "mperm_compositions", "mperm_exact",
           "mperm_modular", "error_bound", "hoperm_zero", "hoperm_rank", "hoperm_bound", "mperm_zero", "mperm_rank",
           "mperm_bound", "printed_hoperm", "printed_mperm", "theorem_14_2", "hoperm_is_per", "grenet_sum",
           "mr_lemma", "conditions_met", "conditions_total", "test_passed", "controls_passed", "controls_total")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- polynomials by definition

def signed_perms(n):
    """Every signed permutation of [n] as the tuple (tau(1), ..., tau(n)), tau(i) = eps_i sigma(i)."""
    for sigma in itertools.permutations(range(1, n + 1)):
        for eps in itertools.product((1, -1), repeat=n):
            yield tuple(e * s for e, s in zip(eps, sigma))


def hoperm_terms(n):
    """Definition 1.1 as {monomial: coefficient}, a monomial the sorted tuple of its variables (i, j), j = +-1..+-n."""
    terms = {}
    for t in signed_perms(n):
        key = tuple(sorted((i + 1, t[i]) for i in range(n)))
        terms[key] = terms.get(key, 0) + 1
    return terms


def words(m):
    """Every word of length sum(m) with m_j letters j (1-based), in lexicographic order."""
    n, gamma = len(m), sum(m)
    counts, w = list(m), []

    def rec():
        if len(w) == gamma:
            yield tuple(w)
            return
        for j in range(n):
            if counts[j]:
                counts[j] -= 1
                w.append(j + 1)
                yield from rec()
                w.pop()
                counts[j] += 1

    yield from rec()


def mperm_terms(m):
    """Definition 1.2 as {monomial: coefficient}: x_{1,w_1} ... x_{gamma,w_gamma} for each word w."""
    terms = {}
    for w in words(m):
        key = tuple((i + 1, w[i]) for i in range(len(w)))
        terms[key] = terms.get(key, 0) + 1
    return terms


def det_terms(n):
    """The Leibniz expansion of det_n: {monomial: sign}."""
    terms = {}
    for q in itertools.permutations(range(n)):
        inv = sum(1 for a in range(n) for b in range(a + 1, n) if q[a] > q[b])
        terms[tuple((i + 1, q[i] + 1) for i in range(n))] = (-1) ** inv
    return terms


def value(terms, X, p=None):
    """A polynomial given by its terms at the point X (a dict variable -> integer or Fraction), exactly or mod p."""
    total = 0
    for mono, c in terms.items():
        prod = c
        for v in mono:
            prod *= X[v]
            if p:
                prod %= p
        total += prod
        if p:
            total %= p
    return total


def hoperm_vars(n):
    """Proposition 3.8's order: x_{1,1}, ..., x_{n,n}, then x_{1,-1}, ..., x_{n,-n}."""
    return [(i, j) for i in range(1, n + 1) for j in range(1, n + 1)] + \
           [(i, -j) for i in range(1, n + 1) for j in range(1, n + 1)]


def mperm_vars(m):
    return [(i, j) for i in range(1, sum(m) + 1) for j in range(1, len(m) + 1)]


# ---------------------------------------------------------------- Proposition 2.1's matrices (rules 1 and 2)

def neg(e):
    return -e if isinstance(e, int) else (-e[0], e[1])


def finish(rows, d, fix):
    if fix and d % 2 == 0:
        rows[0] = {c: neg(e) for c, e in rows[0].items()}
    return rows


def poset_rows(elements, covers, top, fix=True):
    """Proposition 2.1 for any graded poset: elements ordered by rank then as given, the minimum first; covers a list of
    (x, y, label), label an int or a variable; top the maximum. Returns (rows, d), rows a list of {column: entry}."""
    verts = [x for x in elements if x != top]
    index = {x: k for k, x in enumerate(verts)}
    index[top] = 0
    rows = [dict() for _ in verts]
    for k in range(1, len(verts)):
        rows[k][k] = 1
    for x, y, label in covers:
        if index[y] in rows[index[x]]:
            raise Refused("two covers in one entry")
        rows[index[x]][index[y]] = label if isinstance(label, int) else (1, label)
    rank = {elements[0]: 0}
    for x, y, _ in covers:                      # covers are listed in rank order of x
        if rank.get(y, rank[x] + 1) != rank[x] + 1:
            raise Refused("the poset is not graded")
        rank[y] = rank[x] + 1
    return finish(rows, rank[top], fix), rank[top]


def cube_poset(n, fault=None):
    """Rule 2(a): the cube's faces as vectors in {-1, 0, 1}^n, by rank then lexicographically, and an added top."""
    vecs = sorted(itertools.product((-1, 0, 1), repeat=n), key=lambda u: (sum(map(abs, u)), u))
    top = "top"
    covers = []
    for u in vecs:
        r = sum(map(abs, u))
        if r == n:
            covers.append((u, top, 1))
            continue
        for j in range(n):
            if u[j] == 0:
                for s in (1, -1):
                    v = u[:j] + (s,) + u[j + 1:]
                    lab = (r + 1, s * (j + 1))
                    if fault == (u, j, s):
                        lab = (r + 1, -s * (j + 1))
                    covers.append((u, v, lab))
    return vecs + [top], covers, top


def cube_rows(n, fix=True, fault=None):
    return poset_rows(*cube_poset(n, fault), fix=fix)


def multiset_poset(m):
    """Rule 2(b): the vectors a with 0 <= a_j <= m_j, by rank then lexicographically."""
    elems = sorted(itertools.product(*[range(mj + 1) for mj in m]), key=lambda a: (sum(a), a))
    covers = []
    for a in elems:
        for j in range(len(m)):
            if a[j] < m[j]:
                covers.append((a, a[:j] + (a[j] + 1,) + a[j + 1:], (sum(a) + 1, j + 1)))
    return elems, covers, tuple(m)


def multiset_rows(m, fix=True):
    return poset_rows(*multiset_poset(m), fix=fix)


# ---------------------------------------------------------------- determinants (rule 3)

def expand(rows):
    """Every nonzero term of det(rows) as {monomial: coefficient}; an entry is a nonzero int or (c, v), c times the
    variable v. bdc/grenet.py's cycle-cover enumeration: the smallest uncovered vertex on its loop, if it has one, or
    on each simple cycle through it among the uncovered vertices; a cycle of L vertices contributes (-1)^(L - 1).
    Vertex 0 is covered first, so a walk from any other vertex v steps only to vertices w from which v can be reached
    without passing through vertex 0 (reach0), which loses no cycle."""
    N = len(rows)
    sys.setrecursionlimit(max(10000, 20 * N))
    succ = [[w for w in rows[u] if w != u] for u in range(N)]
    reach0 = []
    for w in range(N):
        seen = {w}
        stack = [w] if w != 0 else []
        while stack:
            u = stack.pop()
            for x in succ[u]:
                if x != 0 and x not in seen:
                    seen.add(x)
                    stack.append(x)
        reach0.append(seen)
    covered = [False] * N
    terms = {}
    mono = []

    def split(e):
        return (e[0], e[1]) if isinstance(e, tuple) else (e, None)

    def rec(coef, start):
        v = start
        while v < N and covered[v]:
            v += 1
        if v == N:
            key = tuple(sorted(mono))
            terms[key] = terms.get(key, 0) + coef
            return
        covered[v] = True
        if v in rows[v]:
            c, x = split(rows[v][v])
            if x is not None:
                mono.append(x)
            rec(coef * c, v + 1)
            if x is not None:
                mono.pop()
        walk(v, v, 1, coef)
        covered[v] = False

    def walk(v, u, length, coef):
        for w, e in rows[u].items():
            if w == v and u != v:
                c, x = split(e)
                if x is not None:
                    mono.append(x)
                rec(coef * c * (-1) ** (length - 1), v + 1)
                if x is not None:
                    mono.pop()
            elif w != v and not covered[w] and (v == 0 or v in reach0[w]):
                c, x = split(e)
                if x is not None:
                    mono.append(x)
                covered[w] = True
                walk(v, w, length + 1, coef * c)
                covered[w] = False
                if x is not None:
                    mono.pop()

    rec(1, 0)
    return {k: c for k, c in terms.items() if c}


def numeric(rows, X, p=P):
    N = len(rows)
    A = np.zeros((N, N), dtype=np.int64)
    for u, r in enumerate(rows):
        for v, e in r.items():
            A[u, v] = (e if isinstance(e, int) else e[0] * X[e[1]]) % p
    return A


def draw_point(seed, label, variables):
    st = G.Stream(seed, label)
    vals = st.ints(len(variables), 0, P - 1)
    return dict(zip(variables, vals))


def check_det(rows, terms, variables, seed, label):
    """Rule 3: ('exact', identical, number of terms) or ('modular', agreements)."""
    if len(rows) <= EXACT_ROWS:
        got = expand(rows)
        return "exact", got == terms, len(got)
    agree = 0
    for k in range(POINTS):
        X = draw_point(seed, f"{label}/{k}", variables)
        agree += G.det_mod(numeric(rows, X)) == value(terms, X, P)
    return "modular", agree == POINTS, agree


# ---------------------------------------------------------------- Hessians and ranks (rule 4)

def hessian(terms, variables, X):
    """H[p][q] = sum over monomials containing p and q of coefficient times the product of the others' values."""
    pos = {v: k for k, v in enumerate(variables)}
    N = len(variables)
    H = [[0] * N for _ in range(N)]
    for mono, coef in terms.items():
        if len(set(mono)) != len(mono):
            raise Refused("a monomial with a repeated variable")
        vals = [X[v] for v in mono]
        idx = [pos[v] for v in mono]
        L = len(mono)
        for s in range(L):
            for t in range(s + 1, L):
                prod = coef
                for r in range(L):
                    if r != s and r != t:
                        prod *= vals[r]
                H[idx[s]][idx[t]] += prod
                H[idx[t]][idx[s]] += prod
    return H


def rank_exact(M):
    """The rank over the rationals, by Gaussian elimination in fractions."""
    A = [[Fraction(x) for x in row] for row in M]
    rows = len(A)
    cols = len(A[0]) if rows else 0
    r = 0
    for c in range(cols):
        piv = next((i for i in range(r, rows) if A[i][c] != 0), None)
        if piv is None:
            continue
        A[r], A[piv] = A[piv], A[r]
        inv = 1 / A[r][c]
        for i in range(r + 1, rows):
            if A[i][c] != 0:
                f = A[i][c] * inv
                Ai, Ar = A[i], A[r]
                for j in range(c, cols):
                    if Ar[j] != 0:
                        Ai[j] -= f * Ar[j]
        r += 1
        if r == rows:
            break
    return r


def rank_mod(M, p):
    A = [[int(x) % p for x in row] for row in M]
    rows = len(A)
    cols = len(A[0]) if rows else 0
    r = 0
    for c in range(cols):
        piv = next((i for i in range(r, rows) if A[i][c]), None)
        if piv is None:
            continue
        A[r], A[piv] = A[piv], A[r]
        inv = pow(A[r][c], p - 2, p)
        for i in range(r + 1, rows):
            if A[i][c]:
                f = A[i][c] * inv % p
                A[i] = [(a - f * b) % p for a, b in zip(A[i], A[r])]
        r += 1
        if r == rows:
            break
    return r


def hoperm_B(n, corner=None):
    """Proposition 3.7's zero: every entry 1 but b_{n,n} = 1 - 2n (in column +n)."""
    X = {v: 1 for v in hoperm_vars(n)}
    X[(n, n)] = 1 - 2 * n if corner is None else corner
    return X


def mperm_B(m, raise_by=0):
    """Proposition 3.11's zero for a partition m, scaled to integers: (X, D, l, c). raise_by adds raise_by/(c m_1) to
    B^(1)'s changed entries (a planted fault)."""
    if list(m) != sorted(m, reverse=True) or min(m) < 1:
        raise Refused("not a partition")
    n, gamma = len(m), sum(m)
    X = {v: 1 for v in mperm_vars(m)}
    if len(set(m)) == 1:
        X[(1, 1)] = 1 - n
        return X, 1, 2, n
    c = sum(1 for mj in m if mj == m[0])
    D = c * m[0]
    X = {v: D for v in X}
    for j in range(1, c + 1):
        X[(gamma, j)] = D - gamma + raise_by          # D (1 - gamma/(c m_1)) + raise_by
    return X, D, 1, c


def partitions(gamma, min_parts=3):
    out = []

    def rec(rest, largest, acc):
        if rest == 0:
            if len(acc) >= min_parts:
                out.append(tuple(acc))
            return
        for k in range(min(rest, largest), 0, -1):
            rec(rest - k, k, acc + [k])

    rec(gamma, gamma, [])
    return out


def compositions(gamma):
    out = []
    for cuts in itertools.product((0, 1), repeat=gamma - 1):
        parts, run = [], 1
        for c in cuts:
            if c:
                parts.append(run)
                run = 1
            else:
                run += 1
        parts.append(run)
        out.append(tuple(parts))
    return sorted(out)


# ---------------------------------------------------------------- the printed Hessians (rule 6a)

def printed_hoperm(n):
    """Proposition 3.8: [[C, C], [C, C]], C = 2^(n-2)(n-3)! times blocks 0 (i = k), (n-2)W (i or k = n), A."""
    scale = 2 ** (n - 2) * math.factorial(n - 3)

    def a_entry(j, l):
        if j == l:
            return 0
        return n - 2 if (j == n or l == n) else -2

    N = n * n
    C = [[0] * N for _ in range(N)]
    for i in range(1, n + 1):
        for k in range(1, n + 1):
            if i == k:
                continue
            for j in range(1, n + 1):
                for l in range(1, n + 1):
                    if i == n or k == n:
                        e = (n - 2) * (0 if j == l else 1)
                    else:
                        e = a_entry(j, l)
                    C[(i - 1) * n + j - 1][(k - 1) * n + l - 1] = scale * e
    return [C[r] + C[r] for r in range(N)] + [C[r] + C[r] for r in range(N)]


def printed_mperm(m):
    """Proposition 3.13's matrix with Q^(l) and R^(l) as printed, Q in the block row and column of the changed row."""
    n, gamma = len(m), sum(m)
    prodfact = math.prod(math.factorial(x) for x in m)
    if len(set(m)) == 1:
        mm = m[0]
        k2 = Fraction(math.factorial(mm * n - 3), prodfact)
        Q = [[k2 * (mm * n - 2) * (mm * (mm - 1) if j == jj else mm * mm) for jj in range(n)] for j in range(n)]

        def r2(j, jj):
            if j == 0 and jj == 0:
                return 2 * (mm - 1) * (n - 1)
            if j == 0 or jj == 0:
                return mm * (n - 2)
            return -2 * (mm - 1) if j == jj else -2 * mm

        R = [[k2 * mm * r2(j, jj) for jj in range(n)] for j in range(n)]
        special = 1
    else:
        c = sum(1 for x in m if x == m[0])
        d = Fraction(gamma, c * m[0])
        k1 = Fraction(math.factorial(gamma - 2), prodfact)

        def base(j, jj):
            return m[j] * (m[j] - 1) if j == jj else m[j] * m[jj]

        Q = [[k1 * base(j, jj) for jj in range(n)] for j in range(n)]

        def r1(j, jj):
            if j < c and jj < c:
                return 2 * (d - 1) * base(j, jj)
            if (j < c) != (jj < c):
                return (d - 2) * m[j] * m[jj]
            return -2 * base(j, jj)

        R = [[k1 * r1(j, jj) for jj in range(n)] for j in range(n)]
        special = gamma
    N = gamma * n
    H = [[Fraction(0)] * N for _ in range(N)]
    for i in range(1, gamma + 1):
        for ii in range(1, gamma + 1):
            if i == ii:
                continue
            block = Q if (i == special or ii == special) else R
            for j in range(n):
                for jj in range(n):
                    H[(i - 1) * n + j][(ii - 1) * n + jj] = block[j][jj]
    return H, Q, R, special


def compare_printed_mperm(m, Hc):
    """Hc: the Hessian at B^(l) itself (Fractions). Returns ('match', []) or ('differs', [(block, factor)]), block 'Q',
    'R' or 'diagonal', factor the one scalar by which every such block differs from the printed one, or None."""
    n, gamma = len(m), sum(m)
    Hp, Q, R, special = printed_mperm(m)
    if Hp == Hc:
        return "match", []
    seen = {"Q": set(), "R": set()}
    diagonal_zero = True
    for i in range(1, gamma + 1):
        for ii in range(1, gamma + 1):
            blk = tuple(tuple(Hc[(i - 1) * n + j][(ii - 1) * n + jj] for jj in range(n)) for j in range(n))
            if i == ii:
                diagonal_zero &= all(x == 0 for row in blk for x in row)
            else:
                seen["Q" if (i == special or ii == special) else "R"].add(blk)
    verdicts = [] if diagonal_zero else [("diagonal", None)]
    for name, want in (("Q", Q), ("R", R)):
        want_t = tuple(tuple(row) for row in want)
        if seen[name] == {want_t} or not seen[name]:
            continue
        if len(seen[name]) != 1:
            verdicts.append((name, None))
            continue
        got = next(iter(seen[name]))
        zeros_ok = all((g == 0) == (w == 0) for gr, wr in zip(got, want_t) for g, w in zip(gr, wr))
        ratios = {g / w for gr, wr in zip(got, want_t) for g, w in zip(gr, wr) if w != 0}
        verdicts.append((name, ratios.pop() if zeros_ok and len(ratios) == 1 else None))
    return "differs", verdicts


# ---------------------------------------------------------------- beside (rule 6c, 6d)

def poly_mul(a, b):
    out = {}
    for ka, ca in a.items():
        for kb, cb in b.items():
            key = tuple(sorted(ka + kb))
            out[key] = out.get(key, 0) + ca * cb
    return {k: c for k, c in out.items() if c}


def per_of_sum_terms(n):
    """per_n(X+ + X-): for each sigma the product of the binomials x_{i,sigma(i)} + x_{i,-sigma(i)}, expanded."""
    total = {}
    for sigma in itertools.permutations(range(1, n + 1)):
        poly = {(): 1}
        for i in range(1, n + 1):
            poly = poly_mul(poly, {((i, sigma[i - 1]),): 1, ((i, -sigma[i - 1]),): 1})
        for k, c in poly.items():
            total[k] = total.get(k, 0) + c
    return {k: c for k, c in total.items() if c}


def grenet_sum_numeric(n, X, p=P):
    rows = G.grenet(n)
    N = len(rows)
    A = np.zeros((N, N), dtype=np.int64)
    for u, r in enumerate(rows):
        for v, e in r.items():
            A[u, v] = ((X[(e[0], e[1])] + X[(e[0], -e[1])]) if isinstance(e, tuple) else e) % p
    return A


def planted_rank_matrix(st, N, r, lo=-9, hi=9):
    U = [[x + lo for x in st.ints(r, 0, hi - lo)] for _ in range(N)]
    V = [[x + lo for x in st.ints(N, 0, hi - lo)] for _ in range(r)]
    return [[sum(U[i][k] * V[k][j] for k in range(r)) for j in range(N)] for i in range(N)]


def mr_lemma(seed):
    out = []
    for n in MR_N:
        st = G.Stream(seed, f"bv/mr/{n}")
        for r in (n - 1, n - 2):
            if r > 0:
                M = planted_rank_matrix(st, n, r)
            else:
                M = [[0] * n for _ in range(n)]
            X = {(i + 1, j + 1): M[i][j] for i in range(n) for j in range(n)}
            H = hessian(det_terms(n), [(i, j) for i in range(1, n + 1) for j in range(1, n + 1)], X)
            out.append((n, rank_exact(M), rank_exact(H), 2 * n))
    return out


# ---------------------------------------------------------------- controls (rule 7)

def leibniz_terms(rows):
    N = len(rows)
    want = {}
    for q in itertools.permutations(range(N)):
        coef, mono = 1, []
        for u in range(N):
            e = rows[u].get(q[u], 0)
            if isinstance(e, tuple):
                coef *= e[0]
                mono.append(e[1])
            else:
                coef *= e
            if not coef:
                break
        if coef:
            inv = sum(1 for a in range(N) for b in range(a + 1, N) if q[a] > q[b])
            key = tuple(sorted(mono))
            want[key] = want.get(key, 0) + (-1) ** inv * coef
    return {k: c for k, c in want.items() if c}


def brute_hoperm(n, X):
    total = 0
    labels = [s * j for j in range(1, n + 1) for s in (1, -1)]
    for tau in itertools.product(labels, repeat=n):
        if sorted(abs(t) for t in tau) == list(range(1, n + 1)):
            total += math.prod(X[(i + 1, tau[i])] for i in range(n))
    return total


def brute_mperm(m, X):
    n, gamma = len(m), sum(m)
    total = 0
    for f in itertools.product(range(1, n + 1), repeat=gamma):
        if all(f.count(j + 1) == m[j] for j in range(n)):
            total += math.prod(X[(i + 1, f[i])] for i in range(gamma))
    return total


def second_differences(terms, variables, X):
    N = len(variables)
    H = [[0] * N for _ in range(N)]
    f0 = value(terms, X)
    single = []
    for a in variables:
        Y = dict(X)
        Y[a] += 1
        single.append(value(terms, Y))
    for s in range(N):
        for t in range(N):
            Y = dict(X)
            Y[variables[s]] += 1
            Y[variables[t]] += 1
            H[s][t] = value(terms, Y) - single[s] - single[t] + f0
    return H


def controls_run(seed):
    ctl = {}
    st = G.Stream(seed, "bv/controls")
    ok = True
    for _ in range(4):
        cells = st.ints(25, 0, 9)
        rows = [dict() for _ in range(5)]
        for k, c in enumerate(cells):
            u, v = divmod(k, 5)
            if c < 3:
                rows[u][v] = (1, (u + 1, v + 1))
            elif c < 5:
                rows[u][v] = (-1, (u + 1, v + 1))
            elif c < 7:
                rows[u][v] = (-1, 1, 2)[c - 5]
        ok &= expand(rows) == leibniz_terms(rows)
    for n in range(2, 6):
        g = G.grenet(n)
        mine = [{c: (e if isinstance(e, int) else (1, e)) for c, e in r.items()} for r in g]
        ok &= expand(mine) == G.expand(g)
    ctl["the expansion equals the Leibniz sum on 5 x 5 matrices and bdc/grenet.py's on its matrices, n = 2 to 5"] = ok
    ok = True
    for size in list(range(1, 11)) + [20, 30, 40]:
        M = [[v - 1000 for v in st.ints(size, 0, 2000)] for _ in range(size)]
        ok &= G.det_mod(np.array(M, dtype=np.int64) % P) == G.bareiss(M) % P
    ctl["the modular determinant equals an exact one modulo 2^31 - 1, sizes 1 to 40"] = ok
    ok = True
    for n in range(1, 5):
        X = dict(zip(hoperm_vars(n), [v - 50 for v in st.ints(2 * n * n, 0, 100)]))
        ok &= value(hoperm_terms(n), X) == brute_hoperm(n, X)
    for gamma in range(1, 7):
        for m in compositions(gamma):
            if len(m) <= 3:
                X = dict(zip(mperm_vars(m), [v - 50 for v in st.ints(gamma * len(m), 0, 100)]))
                ok &= value(mperm_terms(m), X) == brute_mperm(m, X)
    ctl["hoperm_n and mperm_m by definition equal brute force over all maps"] = ok
    ok = True
    for terms, variables in ((hoperm_terms(3), hoperm_vars(3)), (mperm_terms((2, 1, 1)), mperm_vars((2, 1, 1)))):
        X = dict(zip(variables, [v - 20 for v in st.ints(len(variables), 0, 40)]))
        ok &= hessian(terms, variables, X) == second_differences(terms, variables, X)
    ctl["the Hessian equals second differences at every pair, hoperm_3 and mperm_(2,1,1)"] = ok
    ok = True
    for N, ranks in ((5, (0, 1, 3, 5)), (20, (1, 10, 19, 20)), (40, (7, 39, 40))):
        for r in ranks:
            M = planted_rank_matrix(st, N, r) if r else [[0] * N for _ in range(N)]
            e = rank_exact(M)
            ok &= e == rank_mod(M, P) == rank_mod(M, 2 ** 61 - 1) == int(np.linalg.matrix_rank(np.array(M, float)))
    ctl["the exact rank equals two modular ranks and numpy's on planted-rank matrices"] = ok
    ok = expand(cube_rows(3, fault=((0, 0, 0), 1, -1))[0]) != hoperm_terms(3)
    ctl["a planted fault caught: an arc's sign flipped in the cube's matrix, n = 3"] = ok
    ok = True
    for rows_d, terms in ((cube_rows(1, fix=False), hoperm_terms(1)), (cube_rows(3, fix=False), hoperm_terms(3)),
                          (multiset_rows((1, 1), fix=False), mperm_terms((1, 1))),
                          (multiset_rows((2, 1, 1), fix=False), mperm_terms((2, 1, 1)))):
        rows, d = rows_d
        ok &= d % 2 == 0 and expand(rows) == {k: -c for k, c in terms.items()}
    ctl["a planted fault caught: the row negation omitted at even rank gives -f"] = ok
    ok = all(value(hoperm_terms(n), hoperm_B(n, corner=2 - 2 * n)) != 0 for n in HOPERM_LOWER)
    ctl["a planted fault caught: B's corner 2 - 2n is not a zero, n = 3 to 6"] = ok
    ok = all(value(mperm_terms(m), mperm_B(m, raise_by=1)[0]) != 0 for m in ((2, 1, 1), (3, 2, 1)))
    ctl["a planted fault caught: B^(1)'s changed entries raised by 1/(c m_1) are not a zero"] = ok
    return ctl


# ---------------------------------------------------------------- run

def fmt(x):
    if isinstance(x, Fraction):
        return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"
    return str(x)


def half(k):
    return str(k // 2) if k % 2 == 0 else f"{k / 2:.1f}"


def run(seed, results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    ctl = controls_run(seed)
    if not all(ctl.values()):
        raise AssertionError(f"a control failed: {[k for k, v in ctl.items() if not v]}")
    cond, detail = {}, {"cube": {}, "compositions": {}, "hoperm_lower": {}, "mperm_lower": {}}

    # (i) the cube's matrices
    cube_info = []
    for n in CUBE_N:
        rows, d = cube_rows(n)
        mode, same, extra = check_det(rows, hoperm_terms(n), hoperm_vars(n), seed, f"bv/cube/{n}")
        ok = len(rows) == 3 ** n and same
        cond[f"cube n = {n}: {3 ** n} square, determinant hoperm_{n} ({mode})"] = ok
        cube_info.append((n, len(rows), mode, same, extra))
        detail["cube"][str(n)] = {"size": len(rows), "rank_d": d, "mode": mode, "identical_or_agrees": same,
                                  "terms_or_points": extra}

    # (ii) the multiset lattices
    comp_stats = {"exact": [0, 0], "modular": [0, 0]}
    sizes = {}
    for gamma in GAMMAS:
        ok_all = True
        for m in compositions(gamma):
            rows, d = multiset_rows(m)
            size_ok = len(rows) == math.prod(x + 1 for x in m) - 1
            mode, same, extra = check_det(rows, mperm_terms(m), mperm_vars(m), seed, f"bv/mperm/{m}")
            comp_stats[mode][0] += same and size_ok
            comp_stats[mode][1] += 1
            sizes[m] = (len(rows), size_ok and same)
            ok_all &= size_ok and same
            detail["compositions"][",".join(map(str, m))] = {"size": len(rows), "mode": mode, "ok": size_ok and same,
                                                            "terms_or_points": extra}
        cond[f"gamma = {gamma}: every composition's matrix of size prod(m_i + 1) - 1 has determinant mperm_m"] = ok_all

    # (iii) hoperm's zero and Hessian
    h_zero, h_rank, h_printed = [], [], []
    for n in HOPERM_LOWER:
        terms = hoperm_terms(n)
        X = hoperm_B(n)
        z = value(terms, X)
        H = hessian(terms, hoperm_vars(n), X)
        rk = rank_exact(H)
        h_zero.append(z)
        h_rank.append((n, rk, len(H)))
        h_printed.append(H == printed_hoperm(n))
        cond[f"hoperm_{n}: B is a zero and the Hessian there has rank at least {n * n}"] = z == 0 and rk >= n * n
        detail["hoperm_lower"][str(n)] = {"value": z, "rank": rk, "rows": len(H), "printed_match": H == printed_hoperm(n)}

    # (iv) mperm's zeros and Hessians
    m_info = []
    for gamma in MPERM_LOWER:
        ok_all = True
        for m in partitions(gamma):
            n = len(m)
            terms = mperm_terms(m)
            X, D, ell, c = mperm_B(m)
            z = value(terms, X)
            H = hessian(terms, mperm_vars(m), X)
            rk = rank_exact(H)
            Hc = [[Fraction(x, D ** (gamma - 2)) for x in row] for row in H]
            verdict = compare_printed_mperm(m, Hc)
            ok = z == 0 and rk == gamma * n
            ok_all &= ok
            m_info.append((m, ell, z, rk, gamma * n, verdict))
            detail["mperm_lower"][",".join(map(str, m))] = {
                "l": ell, "scale": D, "value_scaled": z, "rank": rk, "rows": gamma * n,
                "printed": verdict[0], "printed_blocks": [(b, fmt(f) if f is not None else None)
                                                          for b, f in verdict[1]]}
        cond[f"gamma = {gamma}: every partition into at least 3 parts has B^(l) a zero and a Hessian of rank gamma n"] = (
            ok_all)

    # beside (b): Theorem 1.4(2) as printed
    contra = []
    for gamma in GAMMAS:
        for m in compositions(gamma):
            if len(m) >= 3 and sizes[m][1] and Fraction(gamma * gamma, 2) > sizes[m][0]:
                contra.append((m, Fraction(gamma * gamma, 2), sizes[m][0], Fraction(gamma * len(m), 2)))
    above = sum(1 for m, *_ in m_info if sum(m) ** 2 > sum(m) * len(m))

    # beside (c): hoperm as a permanent of a sum
    is_per = [(n, per_of_sum_terms(n) == hoperm_terms(n), len(hoperm_terms(n))) for n in CUBE_N]
    gsum = []
    for n in GRENET_SUM_N:
        agree = 0
        for k in range(POINTS):
            X = draw_point(seed, f"bv/grenet-sum/{n}/{k}", hoperm_vars(n))
            agree += G.det_mod(grenet_sum_numeric(n, X)) == value(hoperm_terms(n), X, P)
        gsum.append((n, 2 ** n - 1, agree))

    # beside (d): Mignon and Ressayre's lemma
    mr = mr_lemma(seed)

    # outputs
    bound = (max(r[1] for r in cube_info) / P) ** POINTS

    def mstr(m):
        return "(" + ",".join(map(str, m)) + ")"

    def dec(x):
        x = Fraction(x)
        return str(x.numerator) if x.denominator == 1 else f"{float(x):g}"

    pr_ok = sum(1 for t in m_info if t[5][0] == "match")
    kinds = {}
    for m, ell, z, rk, full, verdict in m_info:
        for blk, f in verdict[1]:
            if blk == "R" and ell == 1 and f == Fraction(1, sum(m) - 2):
                key = "R^(1) is the printed one divided by gamma - 2"
            elif f is not None:
                key = f"{blk}^({ell}) differs by a factor"
            else:
                key = f"{blk}^({ell}) differs, not by a factor" if blk != "diagonal" else "a diagonal block not 0"
            kinds.setdefault(key, []).append(m)
    printed_m = (f"Q and R as printed give the Hessian for {pr_ok} of {len(m_info)} partitions"
                 + "".join(f"; {k} in {len(v)}" for k, v in kinds.items()))
    min_m = min(m_info, key=lambda t: t[4])
    max_m = max(m_info, key=lambda t: t[4])
    groups = []
    for m, g2, size, gn in contra:
        key = tuple(sorted(m, reverse=True))
        if key not in [g[0] for g in groups]:
            groups.append((key, g2, size, gn, sum(1 for mm, *_ in contra if tuple(sorted(mm, reverse=True)) == key)))
    contra_text = "; ".join(f"{mstr(k)} {dec(g2)} > {size} ({cnt} orders; gamma n/2 = {dec(gn)})"
                            for k, g2, size, gn, cnt in groups[:3])
    if len(groups) > 3:
        contra_text += f"; {len(groups) - 3} more"
    ranks = sorted({t[3] for t in m_info})
    values = {
        "cube_sizes": "sizes for n = 1..6: " + ", ".join(str(s) for _, s, *_ in cube_info) + " (3^n)",
        "cube_exact": "n = 1..4, every nonzero term: " + ", ".join(
            f"{n} {'identical' if same else 'DIFFERS'}" for n, s, mode, same, _ in cube_info if mode == "exact"),
        "cube_terms": "terms: " + ", ".join(str(x) for n, s, mode, same, x in cube_info if mode == "exact")
                      + " (2^n n!: " + ", ".join(str(2 ** n * math.factorial(n))
                                                for n, s, mode, *_ in cube_info if mode == "exact") + ")",
        "cube_modular": "modulo 2^31 - 1: " + ", ".join(f"n = {n} at {x} of {POINTS}" for n, s, mode, same, x in cube_info
                                                       if mode == "modular"),
        "mperm_compositions": (f"{sum(v[1] for v in comp_stats.values())} compositions of gamma = 1..8, sizes "
                               f"{min(s for s, _ in sizes.values())} to {max(s for s, _ in sizes.values())}"),
        "mperm_exact": f"up to 81 rows, every nonzero term: {comp_stats['exact'][0]} of {comp_stats['exact'][1]} identical",
        "mperm_modular": (f"above 81 rows, at {POINTS} of {POINTS} points modulo 2^31 - 1: {comp_stats['modular'][0]} of "
                          f"{comp_stats['modular'][1]}"),
        "error_bound": f"a wrong matrix of at most 729 rows passes four points with probability at most {bound:.1e}",
        "hoperm_zero": "hoperm_n(B), n = 3..6: " + ", ".join(str(z) for z in h_zero),
        "hoperm_rank": "Hessian ranks at B, n = 3..6: " + ", ".join(f"{rk} of {N}" for _, rk, N in h_rank)
                       + " (n^2: " + ", ".join(str(n * n) for n in HOPERM_LOWER) + ")",
        "hoperm_bound": "dc(hoperm_n) >= rank/2: " + ", ".join(half(rk) for _, rk, _ in h_rank),
        "mperm_zero": (f"B^(l) a zero for {sum(1 for t in m_info if t[2] == 0)} of {len(m_info)} partitions "
                       f"(l = 2 for {sum(1 for t in m_info if t[1] == 2)})"),
        "mperm_rank": (f"Hessian of rank gamma n at B^(l): {sum(1 for t in m_info if t[3] == t[4])} of {len(m_info)} "
                       f"partitions; ranks {ranks[0]} to {ranks[-1]}"),
        "mperm_bound": (f"dc(mperm_m) >= gamma n/2: from {half(min_m[4])} at {mstr(min_m[0])} to {half(max_m[4])} at "
                        f"{mstr(max_m[0])}"),
        "printed_hoperm": (f"Proposition 3.8's [[C, C], [C, C]] is the Hessian at B for {sum(h_printed)} of "
                           f"{len(h_printed)} n (3..6)"),
        "printed_mperm": printed_m,
        "theorem_14_2": ("gamma^2/2 above the verified size prod(m_i + 1) - 1: " + (contra_text or "none")
                         + f"; above gamma n/2 for {above} of {len(m_info)}"),
        "hoperm_is_per": ("hoperm_n = per_n(X+ + X-) identically, n = 1..6: "
                          + ", ".join(f"{n} {'yes' if same else 'NO'}" for n, same, _ in is_per)),
        "grenet_sum": ("Grenet's matrix with x_ij -> x_i,j + x_i,-j: det = hoperm_n at "
                       + ", ".join(f"{a}" for _, _, a in gsum) + f" of {POINTS} points, sizes "
                       + ", ".join(str(s) for _, s, _ in gsum)),
        "mr_lemma": (f"Hessian of det_n at rank n-1 and n-2, n = 2..6: rank at most 2n in "
                     f"{sum(1 for _, _, rk, b in mr if rk <= b)} of {len(mr)} ("
                     + ", ".join(f"{rk}" for _, _, rk, _ in mr) + ")"),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail.update({"test": TEST, "conditions": cond, "controls": ctl,
                   "theorem_14_2": [(mstr(m), fmt(g2), size, fmt(gn)) for m, g2, size, gn in contra],
                   "hoperm_is_per": is_per, "grenet_sum": gsum, "mr_lemma": mr, "error_bound": bound})
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
        sys.exit(f"bv2022: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
