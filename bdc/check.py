#!/usr/bin/env python3
"""The binary determinantal complexity of the 3 x 3 permanent is 7: an independent, exact search, for an Ecdysis
receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:61d74f4cd1c035ae) is from Hüttenhain and
Ikenmeyer, "Binary determinantal complexity" (Linear Algebra Appl. 504, 2016; arXiv:1410.8202): "We prove that for
writing the 3 by 3 permanent polynomial as a determinant of a matrix consisting only of zeros, ones, and variables as
entries, a 7 by 7 matrix is required." Its registered test: refuted if a square matrix of size at most 6, each of whose
entries is 0, 1 or one of the nine variables x11, ..., x33, has determinant equal to per3 as a polynomial.

The only input is the paper's own output, output-ptest-on-7x7.txt (its 463 matrices of size 7 with determinant per3),
an ancillary file on arXiv, checked against its SHA-256 and read as data for the controls. Nothing of the authors'
code is used: the enumeration and the search below are this module's own, in exact integer arithmetic throughout (no
floating point and no random evaluation), and nauty is not used. Every rule was fixed before any seed existed; the
seed is not used, as nothing here is random.

1. Small sizes. A binary variable matrix A with det A = per_m gives, with every variable set to 1, a 0/1 matrix B (its
   support) with det B = per_m(1, ..., 1) = m!. The largest determinant of an n x n 0/1 matrix is computed for every
   n up to 6 by the exact enumeration of rule 2 (without its condition on ones); for n <= 5 it must be below 6, so
   per3 needs n >= 6.
2. The supports of size 6. B must have det B = 6, and every row and column of B at least two ones: a row (or column)
   of A with one nonzero entry would make det A plus or minus a 5 x 5 binary variable determinant (impossible by
   rule 1) or a multiple of a single variable (per3 is not one). All sets of six distinct rows with at least two
   ones each are enumerated with every k x k minor of the first k rows carried exactly to the next row (Laplace
   expansion along the newest row; a set whose minors are all zero is dropped, as it cannot grow into a nonzero
   determinant); those with determinant +-6 and at least two ones in every column are kept, and grouped into classes
   under row and column permutations (the canonical form is the least code of the sorted rows over all 720 column
   permutations, itself a member of the class). The paper's nauty enumeration found 263 classes; supports_classes is
   this module's count, and supports_classes_transpose the count when transposition is also allowed. If det A = per3
   for some A, then some A' on each class's canonical representative B (made det B = +6 by swapping its first two
   rows if needed) has det A' = per3 too: B = P B(A) Q for permutation matrices P, Q, and det P det Q = 1 because
   both supports have determinant 6, so A' = P A Q. Every representative is therefore searched.
3. The search on a support B with det B = m!. Let P(B) be the permutations pi with B[i, pi(i)] = 1, each with its
   sign. If the variable y occupies the set I of positions (ones of B) and every other variable is 1, the determinant
   is f_I(y) = sum over pi in P(B) of sign(pi) y^|pi meet I|; it must equal per_m with every other variable 1, which
   for per3 is 2y + 4. The sets I with f_I = 2y + 4 (the paper's set S) are found exactly: their derivative at 1,
   the sum of B's cofactors over I, must be 2 (all subsets with that sum are listed by meeting two halves of the
   positions), and then every coefficient of f_I is computed from P(B). For two variables on disjoint sets I, J, the
   determinant with everything else 1 must equal per3 restricted to them (2y + 2z + 2 when the two share a row or a
   column of the 3 x 3 variable matrix, yz + y + z + 3 when not); this is computed, exactly, for every pair of sets.
   The nine variables are then placed by backtracking over these sets, pairwise compatible and disjoint, the
   variable with the fewest remaining sets first, and at every depth the whole determinant with the unplaced
   variables at 1 must equal per3 with them at 1, as polynomials (computed from P(B), exactly). A full placement that
   passes is a matrix with det A = per3 (checked again by its own Leibniz expansion): it would refute the claim.
   search_nodes counts the placements tried and solutions the full ones found (0 if the claim holds). Nothing is
   pruned by the symmetries of per3, so every placement is reached.
4. Controls, each of which must behave as stated (controls_passed counts those that do):
   a. Grenet's 7 x 7 matrix (the paper's equation for the Grenet construction) has determinant per3, exactly;
   b. every one of the paper's listed 7 x 7 matrices (463) has determinant per3, exactly; listed_sparse counts those
      with at most three nonzero entries in every row and column (the paper: Grenet's alone), grenet_listed those
      equal to Grenet's matrix up to row and column permutations, transposition and the symmetries of per3 (the 72
      maps x_ij -> x_a(i)b(j) and x_ij -> x_a(j)b(i)); passed if all are per3, at least one is Grenet's, and every
      sparse one is Grenet's;
   c. the same search on the support of Grenet's matrix (size 7) finds full placements, each with determinant per3
      by its own expansion, Grenet's own among them;
   d. the same enumeration and search for the 2 x 2 permanent: no 0/1 matrix of size 2 has determinant 2, the search
      on the size-3 classes finds placements, each with determinant per2 by its own expansion, and the search on the
      support of the paper's 3 x 3 matrix for per2 finds that matrix (bdc(per2) = 3, as the paper says is easy to
      see);
   e. the largest determinants of 0/1 matrices of sizes 1 to 6 are 1, 1, 2, 3, 5 and 9 (the known values).

test_passed is 1 if the largest determinant for every size up to 5 is below 6, every class was searched to the end,
and no full placement was found; else 0.

What it cannot check: nothing here re-runs the authors' program; the arguments that a support needs two ones in each
row and column, and that one representative per class suffices, are the paper's and are restated above (both are
elementary); the arithmetic is Python's exact integers and numpy's int16, int32 and int64 (whose values here stay far
below overflow: minors of 0/1 matrices of size 6 are at most 9, polynomial coefficients at most 5040).

Writes results/outputs.json and results/detail.json.
"""

import hashlib
import itertools
import json
import math
import os
import re
import sys
import time
from collections import defaultdict

import numpy as np

INPUT = ("output-ptest-on-7x7.txt", "d465797b5d75d45ca71a8372a3d6cf05944edb83d227eacab398a13b53a51708", 132881,
         "https://arxiv.org/src/1410.8202v2/anc/output-ptest-on-7x7.txt")
PRINTED_CLASSES = 263
PRINTED_LISTED = 463
KNOWN_MAX_DET = (1, 1, 2, 3, 5, 9)          # largest determinant of an n x n 0/1 matrix, n = 1..6
VARS3 = ("x11", "x12", "x13", "x21", "x22", "x23", "x31", "x32", "x33")
VARS2 = ("x11", "x12", "x21", "x22")
# Grenet's construction, the paper's matrix for it (Section "Uniqueness of the Grenet construction").
GRENET = (("x11", "x12", "x13", 0, 0, 0, 0),
          (1, 0, 0, "x32", "x33", 0, 0),
          (0, 1, 0, "x31", 0, "x33", 0),
          (0, 0, 1, 0, "x31", "x32", 0),
          (0, 0, 0, 1, 0, 0, "x23"),
          (0, 0, 0, 0, 1, 0, "x22"),
          (0, 0, 0, 0, 0, 1, "x21"))
# The paper's 3 x 3 matrix with determinant per2 (its first example).
PER2_EXAMPLE = ((0, "x11", "x21"),
                ("x12", 0, 1),
                ("x22", 1, 0))
LIMIT = 200
CHUNK = 16384

OUTPUTS = (
    "max_det_by_size", "supports_size6", "supports_classes", "supports_classes_transpose", "classes_searched",
    "variable_sets_total", "variable_sets_max", "search_nodes", "solutions", "grenet_ok", "listed_7x7",
    "listed_7x7_ok", "listed_sparse", "grenet_listed", "grenet_support_solutions", "per2_size2_supports",
    "per2_size3_solutions", "controls_passed", "controls_total", "test_passed",
)


class Refused(Exception):
    """An input that is not what the rules say it must be."""


# ---------------------------------------------------------------- the permanent

def per_monomials(m):
    """per_m as a list of monomials, each the frozenset of its variable indices (row-major, 0-based)."""
    return [frozenset(i * m + s[i] for i in range(m)) for s in itertools.permutations(range(m))]


def restriction(monomials, placed):
    """per_m with every variable not in `placed` at 1: {exponent tuple over `placed`: coefficient}."""
    out = defaultdict(int)
    for mono in monomials:
        out[tuple(1 if v in mono else 0 for v in placed)] += 1
    return dict(out)


def single_target(m):
    """per_m with one variable y and the rest 1: (m-1)! y + m! - (m-1)!."""
    f = math.factorial
    return {(1,): f(m - 1), (0,): f(m) - f(m - 1)}


def target_keys(monomials, placed, base):
    """restriction(monomials, placed) in the encoding of Support.poly."""
    out = defaultdict(int)
    for mono in monomials:
        key, mult = 0, 1
        for v in placed:
            if v in mono:
                key += mult
            mult *= base
        out[key] += 1
    return tuple(sorted((k, c) for k, c in out.items() if c))


# ---------------------------------------------------------------- exact enumeration of 0/1 supports

def bit(r, n, j):
    return (r >> (n - 1 - j)) & 1


def row_bits(rows, n):
    return np.array([[bit(r, n, j) for j in range(n)] for r in rows], dtype=np.int32).reshape(len(rows), n)


def enumerate_supports(n, target, min_ones):
    """Every set of n distinct rows of length n, each with at least min_ones ones (and at least one), whose
    determinant is +-target, with at least min_ones ones in every column too: a list of (tuple of row masks in
    increasing order, determinant with the rows in that order). Also the largest |det| over all such row sets,
    columns unrestricted (target None: only that). The k x k minors of the first k rows are carried exactly from
    one level to the next by Laplace expansion along the new row; a set whose minors are all zero is dropped."""
    rows = [r for r in range(1, 1 << n) if bin(r).count("1") >= max(min_ones, 1)]
    R = len(rows)
    bits = row_bits(rows, n)
    keep, maxdet = [], 0

    def final(cmb, dets):
        nonlocal maxdet
        if len(dets):
            maxdet = max(maxdet, int(np.abs(dets).max()))
        if target is None:
            return
        sel = np.flatnonzero(np.abs(dets) == target)
        if not len(sel):
            return
        c = cmb[sel].astype(np.int64)
        colmin = bits[c].sum(axis=1).min(axis=1)
        for ci, d in zip(c[colmin >= min_ones], dets[sel][colmin >= min_ones]):
            keep.append((tuple(rows[int(i)] for i in ci), int(d)))

    combo = np.arange(R, dtype=np.int16)[:, None]
    minors = bits.copy()                                       # level 1: the 1 x 1 minors are the entries
    if n == 1:
        final(combo, minors[:, 0])
        return keep, maxdet
    subsets = [list(itertools.combinations(range(n), k)) for k in range(n + 1)]
    index = [{t: i for i, t in enumerate(subsets[k])} for k in range(n + 1)]
    ar = np.arange(R, dtype=np.int64)
    for k in range(1, n):
        nk, nk1 = len(subsets[k]), len(subsets[k + 1])
        # L[S, r, T]: the coefficient of the level-k minor on S in the level-(k+1) minor on T when row r comes last
        L = np.zeros((nk, R, nk1), dtype=np.int32)
        for ti, T in enumerate(subsets[k + 1]):
            for pos, t in enumerate(T):
                sign = 1 if (k + 1 + pos + 1) % 2 == 0 else -1     # (-1)^(row k+1 + column pos+1), 1-based
                L[index[k][T[:pos] + T[pos + 1:]], :, ti] += sign * bits[:, t]
        Lf = L.reshape(nk, R * nk1)
        last = k + 1 == n
        new_combo, new_minors = [], []
        for s in range(0, len(combo), CHUNK):
            mk = minors[s:s + CHUNK]
            ext = (mk @ Lf).reshape(len(mk), R, nk1)
            later = ar[None, :] > combo[s:s + CHUNK, -1].astype(np.int64)[:, None]
            if last:
                d = ext[:, :, 0]
                if target is None:
                    md = np.abs(np.where(later, d, 0)).max() if d.size else 0
                    maxdet = max(maxdet, int(md))
                    continue
                p, r = np.nonzero(later)
                cmb = np.concatenate([combo[s + p], r[:, None].astype(np.int16)], axis=1)
                final(cmb, d[p, r])
            else:
                p, r = np.nonzero(later & np.any(ext != 0, axis=2))
                new_combo.append(np.concatenate([combo[s + p], r[:, None].astype(np.int16)], axis=1))
                new_minors.append(ext[p, r])
        if last:
            break
        combo = np.concatenate(new_combo) if new_combo else np.zeros((0, k + 1), dtype=np.int16)
        minors = np.concatenate(new_minors) if new_minors else np.zeros((0, nk1), dtype=np.int32)
    return keep, maxdet


def column_tables(n):
    """For each column permutation p, the row mask each row mask becomes: t[p, r]."""
    perms = list(itertools.permutations(range(n)))
    t = np.zeros((len(perms), 1 << n), dtype=np.int16)
    for pi, p in enumerate(perms):
        for r in range(1 << n):
            t[pi, r] = sum(bit(r, n, p[j]) << (n - 1 - j) for j in range(n))
    return t


def canonical_codes(row_sets, n, tables):
    """For each set of n row masks, the least code of its sorted rows over all column permutations."""
    out = []
    K = np.array(row_sets, dtype=np.int64).reshape(len(row_sets), n)
    for s in range(0, len(K), 2048):
        blk = np.sort(tables[:, K[s:s + 2048]], axis=2).astype(np.int64)      # (n!, b, n)
        code = np.zeros(blk.shape[:2], dtype=np.int64)
        for j in range(n):
            code = code * (1 << n) + blk[:, :, j]
        out.extend(code.min(axis=0).tolist())
    return out


def decode(code, n):
    rs = []
    for _ in range(n):
        rs.append(code % (1 << n))
        code //= 1 << n
    return tuple(rs[::-1])


def transpose_rows(rows, n):
    return tuple(sum(bit(rows[i], n, j) << (n - 1 - i) for i in range(n)) for j in range(n))


def classes_of(supports, n):
    """The classes of the supports under row and column permutations, each as its canonical representative (rows),
    in increasing order of code; and the number of classes when transposition is also allowed."""
    tables = column_tables(n)
    codes = sorted(set(canonical_codes([rows for rows, _ in supports], n, tables)))
    reps = [decode(c, n) for c in codes]
    trans = canonical_codes([transpose_rows(r, n) for r in reps], n, tables) if reps else []
    return reps, len({min(c, t) for c, t in zip(codes, trans)})


# ---------------------------------------------------------------- the search on one support

POP8 = np.array([bin(i).count("1") for i in range(256)], dtype=np.int64)


def popcount(x):
    x = np.asarray(x, dtype=np.int64)
    out = np.zeros(x.shape, dtype=np.int64)
    for s in range(0, 64, 8):
        out += POP8[(x >> s) & 0xFF]
    return out


def perm_sign(p):
    s, seen = 1, [False] * len(p)
    for i in range(len(p)):
        if not seen[i]:
            j, length = i, 0
            while not seen[j]:
                seen[j] = True
                j = p[j]
                length += 1
            if length % 2 == 0:
                s = -s
    return s


def supported_perms(B):
    """The permutations pi with B[i][pi(i)] nonzero for every i, each with its sign."""
    n = len(B)
    out = []

    def go(i, used, p):
        if i == n:
            out.append(tuple(p))
            return
        for j in range(n):
            if B[i][j] and not used & (1 << j):
                p.append(j)
                go(i + 1, used | (1 << j), p)
                p.pop()
    go(0, 0, [])
    return [(p, perm_sign(p)) for p in out]


def support_of(A):
    return [[0 if a == 0 else 1 for a in r] for r in A]


class Support:
    """A 0/1 support B: its positions (its ones), its supported permutations as bitmasks over the positions, with
    their signs, its determinant and its cofactors at the positions."""

    def __init__(self, B):
        self.B = [list(r) for r in B]
        self.n = len(B)
        self.pos = [(i, j) for i in range(self.n) for j in range(self.n) if B[i][j]]
        self.bit_of = {p: k for k, p in enumerate(self.pos)}
        self.perms = supported_perms(self.B)
        self.masks = np.array([sum(1 << self.bit_of[(i, p[i])] for i in range(self.n)) for p, _ in self.perms],
                              dtype=np.int64)
        self.signs = np.array([s for _, s in self.perms], dtype=np.int64)
        self.det = int(self.signs.sum()) if len(self.perms) else 0
        self.cof = [int(sum(s for (p, s) in self.perms if p[i] == j)) for (i, j) in self.pos]
        self.base = self.n + 1

    def poly(self, sets):
        """det with variable v on the positions sets[v] (bitmasks) and 1 elsewhere, as a sorted tuple of
        (key, coefficient), key = sum over v of e_v (n + 1)^v: injective, as no exponent exceeds n."""
        key = np.zeros(len(self.masks), dtype=np.int64)
        mult = 1
        for s in sets:
            key += popcount(self.masks & s) * mult
            mult *= self.base
        u, inv = np.unique(key, return_inverse=True)
        coef = np.zeros(len(u), dtype=np.int64)
        np.add.at(coef, inv.ravel(), self.signs)
        nz = coef != 0
        return tuple(zip(u[nz].tolist(), coef[nz].tolist()))


def variable_sets(sup, target):
    """Every set I of positions with det(B with y on I, 1 elsewhere) = target(y), exactly, as sorted bitmasks: first
    the cofactor sum over I (the derivative at y = 1) must equal the linear coefficient, then every coefficient."""
    want = target.get((1,), 0)
    m = len(sup.pos)
    cof = np.array(sup.cof, dtype=np.int64)
    h = m // 2

    def half(lo, k):
        idx = np.arange(1 << k, dtype=np.int64)
        bits = (idx[:, None] >> np.arange(k)[None, :]) & 1
        return idx, bits @ cof[lo:lo + k]
    ilo, slo = half(0, h)
    ihi, shi = half(h, m - h)
    order = np.argsort(shi, kind="stable")
    shs = shi[order]
    left = np.searchsorted(shs, want - slo, "left")
    right = np.searchsorted(shs, want - slo, "right")
    counts = right - left
    total = int(counts.sum())
    if total == 0:
        return []
    a = np.repeat(np.arange(len(slo)), counts)
    offset = np.arange(total) - np.repeat(np.cumsum(counts) - counts, counts)
    masks = ilo[a] | (ihi[order[np.repeat(left, counts) + offset]] << h)
    masks = np.unique(masks[masks != 0])
    D = sup.n + 1
    tvec = np.zeros(D, dtype=np.int64)
    for (e,), v in target.items():
        tvec[e] = v
    good = []
    for s in range(0, len(masks), 1 << 16):
        mk = masks[s:s + (1 << 16)]
        coef = np.zeros((len(mk), D), dtype=np.int64)
        rows = np.arange(len(mk))
        for p in range(len(sup.masks)):
            coef[rows, popcount(mk & sup.masks[p])] += sup.signs[p]       # one entry per row for each p
        good.append(mk[np.all(coef == tvec[None, :], axis=1)])
    return [int(x) for x in np.concatenate(good)]


def pair_tables(sup, sets, targets):
    """For each target t ({(a, b): coefficient}, a polynomial in y, z), a boolean |S| x |S| table: disjoint sets
    I, J with det(B with y on I, z on J, 1 elsewhere) = t, exactly."""
    S = np.array(sets, dtype=np.int64)
    k = len(S)
    D = sup.n + 1
    pc = np.stack([popcount(S & mk) for mk in sup.masks])               # (|P|, k): |pi meet I|
    plus = sup.signs > 0
    tv = []
    for t in targets:
        a = np.zeros((D, D), dtype=np.int64)
        for (x, y), v in t.items():
            a[x, y] = v
        tv.append(a.ravel())
    tables = [np.zeros((k, k), dtype=bool) for _ in targets]
    base = (np.arange(k, dtype=np.int64) * D * D)[None, :]
    for i in range(k):
        key = base + pc[:, i:i + 1] * D + pc                           # (|P|, k): set b, exponent of y, of z
        coef = (np.bincount(key[plus].ravel(), minlength=k * D * D)
                - np.bincount(key[~plus].ravel(), minlength=k * D * D)).reshape(k, D * D)
        disjoint = (S & S[i]) == 0
        for ti, a in enumerate(tv):
            tables[ti][i] = disjoint & np.all(coef == a[None, :], axis=1)
    return tables


def search(sup, m, monomials):
    """Rule 3 on one support for per_m: (variable sets, placements tried, full placements found as {variable: set
    index})."""
    nv = m * m
    sets = variable_sets(sup, single_target(m))
    if not sets:
        return sets, 0, []
    same, other = pair_tables(sup, sets, [restriction(monomials, (0, 1)), restriction(monomials, (0, m + 1))])
    k = len(sets)
    nodes, found, cache = 0, [], {}

    def want(order):
        if order not in cache:
            cache[order] = target_keys(monomials, order, sup.base)
        return cache[order]

    def line(u, v):
        return u // m == v // m or u % m == v % m

    def rec(placed, allowed):
        nonlocal nodes
        if len(placed) == nv:
            found.append(dict(placed))
            return
        free = [v for v in range(nv) if v not in placed]
        v = min(free, key=lambda u: int(allowed[u].sum()))
        for a in np.flatnonzero(allowed[v]).tolist():
            nodes += 1
            trial = dict(placed)
            trial[v] = a
            order = tuple(sorted(trial))
            if sup.poly([sets[trial[u]] for u in order]) != want(order):
                continue
            nxt, ok = {}, True
            for u in free:
                if u == v:
                    continue
                nxt[u] = allowed[u] & (same[a] if line(u, v) else other[a])
                if not nxt[u].any():
                    ok = False
                    break
            if ok:
                rec(trial, nxt)
    rec({}, {v: np.ones(k, dtype=bool) for v in range(nv)})
    return sets, nodes, found


def placed_matrix(sup, sets, placement):
    """The binary variable matrix of a placement: ('v', variable) on its set's positions, 1 on the other ones."""
    A = [[1 if b else 0 for b in r] for r in sup.B]
    for v, s in placement.items():
        for k, (i, j) in enumerate(sup.pos):
            if sets[s] >> k & 1:
                A[i][j] = ("v", v)
    return A


# ---------------------------------------------------------------- binary variable matrices, exactly

def det_poly(A, nvars):
    """det A, exactly, over its supported permutations, for a matrix of 0, 1 and ('v', k):
    {exponent tuple over 0..nvars-1: coefficient}."""
    out = defaultdict(int)
    for p, s in supported_perms(support_of(A)):
        e = [0] * nvars
        for i, j in enumerate(p):
            if A[i][j] != 1:
                e[A[i][j][1]] += 1
        out[tuple(e)] += s
    return {e: c for e, c in out.items() if c}


def per_poly(m):
    return {tuple(1 if v in mono else 0 for v in range(m * m)): 1 for mono in per_monomials(m)}


def as_matrix(rows, names=VARS3):
    return [[a if a in (0, 1) else ("v", names.index(a)) for a in r] for r in rows]


def as_names(A, names=VARS3):
    return [[a if a in (0, 1) else names[a[1]] for a in r] for r in A]


def parse_listing(text):
    """The paper's output: blocks '{{ ... }}' of 7 rows of 7 entries, each 0, 1 or x11, ..., x33 (its lines end in
    CR LF)."""
    out = []
    for b in re.findall(r"\{\{(.*?)\}\}", text, re.S):
        mat = []
        for r in b.split("}"):
            r = r.strip("{}, \t\r\n")
            if not r:
                continue
            row = []
            for x in (e.strip() for e in r.split(",")):
                if x in ("0", "1"):
                    row.append(int(x))
                elif x in VARS3:
                    row.append(x)
                else:
                    raise Refused(f"unexpected entry {x!r} in the paper's output")
            mat.append(tuple(row))
        if len(mat) != 7 or any(len(r) != 7 for r in mat):
            raise Refused("a listed matrix is not 7 x 7")
        out.append(tuple(mat))
    rest = re.sub(r"\{\{.*?\}\}", "", text, flags=re.S)
    if rest.strip():
        raise Refused("the paper's output has text outside its matrices")
    return out


def sparse(A):
    return max(max(sum(1 for a in r if a != 0) for r in A), max(sum(1 for a in c if a != 0) for c in zip(*A))) <= 3


def per3_maps():
    """The 72 maps of the variables that leave per3 unchanged: x_ij -> x_a(i)b(j) and x_ij -> x_a(j)b(i)."""
    out, seen = [], set()
    for a in itertools.permutations(range(3)):
        for b in itertools.permutations(range(3)):
            for t in (False, True):
                mp = {}
                for i in range(3):
                    for j in range(3):
                        ii, jj = (a[j], b[i]) if t else (a[i], b[j])
                        mp[VARS3[3 * i + j]] = VARS3[3 * ii + jj]
                key = tuple(mp[v] for v in VARS3)
                if key not in seen:
                    seen.add(key)
                    out.append(mp)
    return out


def coded(A, mp=None):
    return [[a if a in (0, 1) else 2 + VARS3.index(a if mp is None else mp[a]) for a in r] for r in A]


def profile(C):
    """Invariant under row and column permutations: the sorted multisets of sorted rows and of sorted columns."""
    return (sorted(tuple(sorted(r)) for r in C), sorted(tuple(sorted(c)) for c in zip(*C)))


def rowcol_canonical(C):
    """The least tuple of sorted rows over all column permutations: a complete invariant under row and column
    permutations."""
    n = len(C)
    return min(tuple(sorted(tuple(r[j] for j in p) for r in C)) for p in itertools.permutations(range(n)))


def grenet_forms():
    G = coded(GRENET)
    GT = [list(c) for c in zip(*G)]
    return [(profile(G), rowcol_canonical(G)), (profile(GT), rowcol_canonical(GT))]


def is_grenet(A, forms, maps):
    """Whether A is Grenet's matrix up to row and column permutations, transposition and the symmetries of per3."""
    for mp in maps:
        C = coded(A, mp)
        pr = profile(C)
        for gp, gc in forms:
            if pr == gp and rowcol_canonical(C) == gc:
                return True
    return False


# ---------------------------------------------------------------- the run

def summarise(values):
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters")
    return out


def load(directory):
    path = os.path.join(directory, INPUT[0])
    with open(path, "rb") as f:
        data = f.read()
    got = hashlib.sha256(data).hexdigest()
    if got != INPUT[1] or len(data) != INPUT[2]:
        raise Refused(f"{path}: sha256 {got} and {len(data)} bytes, not the committed {INPUT[1]} and {INPUT[2]}")
    return data.decode("ascii")


def representative(rows, n):
    B = [[bit(r, n, j) for j in range(n)] for r in rows]
    if Support(B).det < 0:
        B[0], B[1] = B[1], B[0]
    return B


def search_classes(reps, n, m, names):
    """Rule 3 on every class representative: (classes searched, variable sets in all, the most on one, placements
    tried, verified solutions as named matrices, per-class detail)."""
    mono = per_monomials(m)
    target = per_poly(m)
    searched, total, most, nodes, solutions, detail = 0, 0, 0, 0, [], []
    for rows in reps:
        sup = Support(representative(rows, n))
        if sup.det != math.factorial(m):
            raise AssertionError("a representative's determinant is not m!")
        sets, nd, found = search(sup, m, mono)
        searched += 1
        total += len(sets)
        most = max(most, len(sets))
        nodes += nd
        for f in found:
            A = placed_matrix(sup, sets, f)
            if det_poly(A, m * m) == target:
                solutions.append(as_names(A, names))
        detail.append({"rows": list(rows), "ones": len(sup.pos), "perms": len(sup.perms), "sets": len(sets),
                       "nodes": nd, "found": len(found)})
    return searched, total, most, nodes, solutions, detail


def run(inputs="inputs", log=print):
    started = time.monotonic()
    listing = parse_listing(load(inputs))
    values, controls, detail = {}, [], {}

    def at():
        return f"at {time.monotonic() - started:.0f} s"

    # Rule 1 and control e: the largest determinants.
    maxdets = [enumerate_supports(n, None, 1)[1] for n in range(1, 7)]
    values["max_det_by_size"] = ",".join(map(str, maxdets))
    controls.append({"control": "e: largest 0/1 determinants for n = 1..6 are 1, 1, 2, 3, 5, 9",
                     "passed": tuple(maxdets) == KNOWN_MAX_DET, "found": maxdets})
    log(f"bdc: largest 0/1 determinants by size: {maxdets}, {at()}")

    # Rule 2: supports of size 6.
    supports, _ = enumerate_supports(6, 6, 2)
    reps, n_t = classes_of(supports, 6)
    values.update({"supports_size6": len(supports), "supports_classes": len(reps), "supports_classes_transpose": n_t})
    log(f"bdc: {len(supports)} row sets of size 6 with |det| 6, {len(reps)} classes ({n_t} with transposition), {at()}")

    # Rule 3: the search on every class.
    searched, total, most, nodes, solutions, cdetail = search_classes(reps, 6, 3, VARS3)
    values.update({"classes_searched": searched, "variable_sets_total": total, "variable_sets_max": most,
                   "search_nodes": nodes, "solutions": len(solutions)})
    detail["classes"] = cdetail
    detail["solutions"] = solutions
    log(f"bdc: searched {searched} classes: {total} variable sets, {nodes} placements tried, "
        f"{len(solutions)} solutions, {at()}")

    # Controls a, b: Grenet's matrix and the paper's listing.
    target = per_poly(3)
    grenet_ok = det_poly(as_matrix(GRENET), 9) == target
    listed_ok = sum(1 for A in listing if det_poly(as_matrix(A), 9) == target)
    forms, maps = grenet_forms(), per3_maps()
    sparse_ones = [A for A in listing if sparse(A)]
    grenet_listed = sum(1 for A in listing if is_grenet(A, forms, maps))
    sparse_grenet = sum(1 for A in sparse_ones if is_grenet(A, forms, maps))
    values.update({"grenet_ok": int(grenet_ok), "listed_7x7": len(listing), "listed_7x7_ok": listed_ok,
                   "listed_sparse": len(sparse_ones), "grenet_listed": grenet_listed})
    controls.append({"control": "a: Grenet's matrix has determinant per3", "passed": grenet_ok})
    controls.append({"control": "b: every listed 7 x 7 matrix has determinant per3; Grenet's is among them and every "
                                "sparse one is Grenet's, up to row and column permutations, transposition and the "
                                "symmetries of per3",
                     "passed": listed_ok == len(listing) and grenet_listed >= 1 and sparse_grenet == len(sparse_ones),
                     "listed": len(listing), "ok": listed_ok, "sparse": len(sparse_ones),
                     "sparse_grenet": sparse_grenet, "grenet": grenet_listed})
    log(f"bdc: Grenet's matrix per3: {grenet_ok}; listed {len(listing)}, per3 {listed_ok}, sparse {len(sparse_ones)}, "
        f"Grenet's {grenet_listed}, {at()}")

    # Control c: the search on Grenet's support.
    mono3 = per_monomials(3)
    gsup = Support(support_of(GRENET))
    gsets, gnodes, gfound = search(gsup, 3, mono3)
    gmats = [placed_matrix(gsup, gsets, f) for f in gfound]
    gverified = sum(1 for A in gmats if det_poly(A, 9) == target)
    own = as_matrix(GRENET)
    has_own = any(A == own for A in gmats)
    values["grenet_support_solutions"] = len(gfound)
    controls.append({"control": "c: the search on Grenet's support finds placements, each per3, Grenet's own among "
                                "them",
                     "passed": len(gfound) > 0 and gverified == len(gfound) and has_own, "found": len(gfound),
                     "verified": gverified, "own": has_own, "nodes": gnodes, "sets": len(gsets)})
    log(f"bdc: Grenet's support: {len(gfound)} placements found, {gverified} verified (Grenet's own: {has_own}), "
        f"{at()}")

    # Control d: the 2 x 2 permanent.
    s2, md2 = enumerate_supports(2, 2, 1)
    s3, _ = enumerate_supports(3, 2, 2)
    reps3, _ = classes_of(s3, 3)
    _, _, _, _, sol3, _ = search_classes(reps3, 3, 2, VARS2)
    esup = Support(support_of(PER2_EXAMPLE))
    esets, _, efound = search(esup, 2, per_monomials(2))
    example = as_matrix(PER2_EXAMPLE, VARS2)
    example_ok = det_poly(example, 4) == per_poly(2)
    example_found = any(placed_matrix(esup, esets, f) == example for f in efound)
    values.update({"per2_size2_supports": len(s2), "per2_size3_solutions": len(sol3)})
    controls.append({"control": "d: per2: no 0/1 matrix of size 2 has determinant 2; placements on the size-3 classes, "
                                "each per2; the paper's per2 matrix found on its support",
                     "passed": len(s2) == 0 and md2 < 2 and len(sol3) > 0 and example_ok and example_found,
                     "size3_classes": len(reps3), "solutions": len(sol3), "example_ok": example_ok,
                     "example_found": example_found})
    controls.sort(key=lambda c: c["control"])

    values.update({"controls_passed": sum(1 for c in controls if c["passed"]), "controls_total": len(controls)})
    values["test_passed"] = int(max(maxdets[:5]) < 6 and searched == len(reps) and len(solutions) == 0)
    detail.update({"controls": controls, "seconds": round(time.monotonic() - started, 1),
                   "printed": {"classes": PRINTED_CLASSES, "listed": PRINTED_LISTED}})
    return summarise(values), detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, detail = run(log=lambda line: print(line, file=sys.stderr, flush=True))
    except Refused as e:
        sys.exit(f"bdc/check.py: refused: {e}")
    os.makedirs("results", exist_ok=True)
    with open(os.path.join("results", "outputs.json"), "w", encoding="ascii") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(os.path.join("results", "detail.json"), "w", encoding="ascii") as f:
        json.dump(detail, f, indent=1, sort_keys=True)
        f.write("\n")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
