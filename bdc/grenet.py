#!/usr/bin/env python3
"""Grenet's upper bound for the permanent versus determinant problem: the (2^n - 1) x (2^n - 1) matrix of variables
and constants whose determinant is the n x n permanent, built as the paper builds it and checked for n from 2 to 10.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:f0290fc22926a2ab) is from B. Grenet, "An
upper bound for the permanent versus determinant problem" (manuscript, 2011; the version of 25 May 2012 on the
author's page, never published with a DOI), its Theorem: "There exists a (2^n − 1) × (2^n − 1) matrix M with entries
in {x_ij : 1 ≤ i, j ≤ n} ∪ {−1, 0, 1} such that det M = per X." The work has no index the archive can read, so it is
registered under a cite: source and its quote is Imago's word, taken from the PDF.

The test, as registered: see TEST below. The construction, in the paper's words. Its Lemma: "The set of vertices of
the ABP is indexed by the subsets of {1, ..., n}. The distinguished vertices are s = ∅ and t = {1, ..., n}. ... There
is an arc from a set S ∈ V_i of weight x_ij to the set S ∪ {j} whenever j ∉ S." Its proof of the Lemma: "an arc
falling in the layer V_i has weight x_ij for some j", so an arc from a set of size i - 1 into the layer of sets of
size i carries x_ij (the construction's "S ∈ V_i" counts layers from V_1 = {s}, as the paper's definition of a
layered program does; the proof's V_0, ..., V_n count from 0, and only the reading i = |S| + 1 gives every arc a
variable). Its Theorem's proof: "We build a new digraph G obtained by merging the two vertices s and t, and by adding
a loop (of weight 1) to all other vertices of the digraph. ... If n is odd, this signature is 1 and per M = det M =
per X and we are done. Otherwise, the signature is −1. If we replace in the first layer (of size n) the weights of
the loops by −1, then the weight of a cycle cover will be multiplied by (−1)^(n−1) = −1."

Every rule below was fixed before this module's construction was evaluated. Known before it: the lab's check of
Alper, Bogart & Velasco (bdc/abv.py) expanded the loops-of-weight-1 version for n = 3 exactly and evaluated it for
n = 2, 4 and 5 at three points each, finding (-1)^(n-1) perm_n, and a research sweep on 10 October evaluated a
version at random points modulo 2^61 - 1 for n = 2 to 10; so the construction's correctness was expected. The
generic expansion's running time was measured beforehand on a perturbed pattern (one extra arc), counting no term of
this matrix.

1. The matrix. Its rows and columns are the subsets of {1, ..., n} other than {1, ..., n}, ordered by size and then
   lexicographically; the empty set stands for the merged vertex s = t. Row S holds, for each j not in S, the
   variable x_ij with i = |S| + 1 in column S ∪ {j}, or in the column of the empty set when S ∪ {j} = {1, ..., n};
   the diagonal holds 1 at every row but the empty set's, and -1 at the n singletons when n is even; every other
   entry is 0. It must have 2^n - 1 rows and columns and every entry a variable or -1, 0 or 1.
2. The determinant, exactly, for n from 2 to 7: every nonzero term of the Leibniz expansion, enumerated as the cycle
   covers of the matrix's digraph (an entry (u, v) is an arc u -> v, a diagonal entry a loop): the smallest uncovered
   vertex is put on its loop, if it has one, or on each simple cycle through it among the uncovered vertices, in
   turn; a cover's term is the product of its entries times (-1) to the number of vertices on cycles of length at
   least 2 less the number of such cycles. The terms are collected as monomials with integer coefficients, and the
   result must equal the permanent, the sum over the n! permutations p of x_1p(1) ... x_np(n), monomial by
   monomial. This enumerates every nonzero term of the expansion without using the paper's argument.
3. The determinant at points, for n from 8 to 10: at four points drawn from the seed (each variable an integer from 0
   to 2^31 - 2, by SHA-256 of the seed, a label and a counter), the determinant modulo the prime 2^31 - 1, by
   Gaussian elimination with numpy's 64-bit integers, against the permanent by Ryser's formula modulo the same prime.
   A nonzero polynomial of degree at most 2^n - 1 vanishes at a random point with probability at most
   (2^n - 1)/(2^31 - 1) (Schwartz and Zippel), so four agreements leave a difference with probability below 6e-26.
4. The test's nine conditions, one for each n from 2 to 10: rule 1's size and entries, and rule 2's identity (n up to
   7) or rule 3's four agreements (n from 8). test_passed is 1 if all nine hold.
5. Beside, none of it counted: the same points of rule 3 for n from 2 to 7 (agreeing with rule 2's expansion); the
   paper's remark that for odd n only 0 and 1 appear as constants; its Corollary, a monotone skew circuit of size
   (n - 1)(2^n - 1) computing the permanent (the product M_1 M_2 ... M_n of the program's layers, each entry of
   layer i's vector a sum of i products, 2i - 1 operations), built and counted for n from 2 to 10, with its value
   at rule 3's points; and its dc_s(2) = 3: no 2 x 2 matrix with entries among the four variables and -1, 0 and 1 has
   determinant per_2 (all 2,401 expanded), while the construction's 3 x 3 does.

Controls (controls_passed counts those that behave as stated; the run stops if any fails): Ryser's permanent against
the sum over permutations at seed-drawn integer points for n from 1 to 6; the modular determinant against an exact
fraction-free one on seed-drawn integer matrices of sizes 1 to 40; the expansion of rule 2 against the Leibniz sum
on seed-drawn 5 x 5 matrices of variables and constants; and three planted faults, each caught: the singletons'
loops left at 1 for n = 2, 4 and 6 (the expansion then gives -per X), one arc's variable changed for n = 3, 4 and 5,
and the singletons' loops left at 1 for n = 8 at rule 3's first point.

What it cannot check: the theorem for n above 10, which rests on the paper's argument (one long cycle through the
merged vertex, every other vertex on its loop).

Writes results/outputs.json and results/detail.json. Run with: python3 bdc/grenet.py
"""

import hashlib
import itertools
import json
import math
import os
import re
import sys

import numpy as np

P = 2 ** 31 - 1
EXACT_N = tuple(range(2, 8))
MODULAR_N = tuple(range(8, 11))
POINTS = 4
LIMIT = 200
TEST = ("Refuted if, for some n from 2 to 10, the paper's matrix (its branching program on the subsets of {1, …, n}, "
        "an arc from S to S ∪ {j}, j ∉ S, weighted x_ij with i = |S| + 1, the source ∅ and sink {1, …, n} merged, a "
        "loop of weight 1 at every other vertex, and for even n the singletons' loops −1) is not of size 2^n − 1 with "
        "entries among the variables and −1, 0, 1, or its determinant is not the n × n permanent: identically, every "
        "nonzero term expanded, for n up to 7, and at four seed-drawn points modulo 2^31 − 1 for n from 8 to 10.")
OUTPUTS = ("sizes", "exact", "exact_terms", "modular", "error_bound", "points_small", "constants_odd", "corollary",
           "dcs2", "conditions_met", "conditions_total", "test_passed", "controls_passed", "controls_total")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- the matrix (rule 1)

def vertices(n):
    """The subsets of {0, ..., n-1} other than the whole set, by size and then lexicographically."""
    return [frozenset(c) for r in range(n) for c in itertools.combinations(range(n), r)]


def grenet(n, even_fix=True, fault=None):
    """The paper's matrix as rows of {column: entry}; an entry is an int (a constant) or a pair (i, j), the variable
    x_ij with 1-based indices. fault: None, or ("arc", S, j, j2) to give the arc S -> S + {j} the variable x_i,j2."""
    vs = vertices(n)
    index = {s: k for k, s in enumerate(vs)}
    whole = frozenset(range(n))
    rows = [dict() for _ in vs]
    for s in vs:
        u = index[s]
        if s:
            rows[u][u] = -1 if (even_fix and n % 2 == 0 and len(s) == 1) else 1
        for j in range(n):
            if j in s:
                continue
            t = s | {j}
            v = index[frozenset()] if t == whole else index[t]
            jj = j
            if fault and fault[0] == "arc" and fault[1] == s and fault[2] == j:
                jj = fault[3]
            rows[u][v] = (len(s) + 1, jj + 1)
    return rows


def entries_ok(rows, n):
    ok = len(rows) == 2 ** n - 1
    for r in rows:
        for c, e in r.items():
            if not (0 <= c < len(rows)):
                ok = False
            if isinstance(e, tuple):
                ok = ok and len(e) == 2 and all(1 <= x <= n for x in e)
            else:
                ok = ok and e in (-1, 0, 1)
    return ok


def constants_of(rows):
    return sorted({e for r in rows for e in r.values() if not isinstance(e, tuple)})


# ---------------------------------------------------------------- the exact expansion (rule 2)

def expand(rows):
    """Every nonzero term of det(rows), as {monomial: coefficient}, a monomial a sorted tuple of variables."""
    sys.setrecursionlimit(max(10000, 20 * len(rows)))
    N = len(rows)
    covered = [False] * N
    terms = {}
    mono = []
    state = {"coef": 1, "sign": 1}

    def take(e):
        if isinstance(e, tuple):
            mono.append(e)
            return 1
        return e

    def leave(e):
        if isinstance(e, tuple):
            mono.pop()

    def rec():
        v = next((u for u in range(N) if not covered[u]), None)
        if v is None:
            if state["coef"]:
                key = tuple(sorted(mono))
                terms[key] = terms.get(key, 0) + state["sign"] * state["coef"]
            return
        covered[v] = True
        if v in rows[v]:
            e = rows[v][v]
            c = take(e)
            old = state["coef"]
            state["coef"] = old * c
            if state["coef"]:
                rec()
            state["coef"] = old
            leave(e)

        def walk(u, length):
            for w, e in rows[u].items():
                if w == v and u != v:
                    c = take(e)
                    old, olds = state["coef"], state["sign"]
                    state["coef"], state["sign"] = old * c, olds * (-1) ** (length - 1)
                    if state["coef"]:
                        rec()
                    state["coef"], state["sign"] = old, olds
                    leave(e)
                elif w != v and not covered[w]:
                    c = take(e)
                    old = state["coef"]
                    state["coef"] = old * c
                    if state["coef"]:
                        covered[w] = True
                        walk(w, length + 1)
                        covered[w] = False
                    state["coef"] = old
                    leave(e)

        walk(v, 1)
        covered[v] = False

    rec()
    return {k: c for k, c in terms.items() if c}


def permanent_terms(n):
    return {tuple(sorted((i + 1, p[i] + 1) for i in range(n))): 1 for p in itertools.permutations(range(n))}


# ---------------------------------------------------------------- points (rule 3)

class Stream:
    def __init__(self, seed, label):
        self.seed, self.label, self.n = seed, label, 0

    def ints(self, k, lo, hi):
        out = []
        while len(out) < k:
            h = hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
            self.n += 1
            for i in range(0, 32, 8):
                out.append(lo + int.from_bytes(h[i:i + 8], "big") % (hi - lo + 1))
        return out[:k]


def point(stream, n):
    vals = stream.ints(n * n, 0, P - 1)
    return [vals[i * n:(i + 1) * n] for i in range(n)]


def numeric(rows, X, p=P):
    N = len(rows)
    A = np.zeros((N, N), dtype=np.int64)
    for u, r in enumerate(rows):
        for v, e in r.items():
            A[u, v] = (X[e[0] - 1][e[1] - 1] if isinstance(e, tuple) else e) % p
    return A


def det_mod(A, p=P):
    A = A.copy() % p
    n = A.shape[0]
    det = 1
    for c in range(n):
        nz = np.nonzero(A[c:, c])[0]
        if nz.size == 0:
            return 0
        r = c + int(nz[0])
        if r != c:
            A[[c, r]] = A[[r, c]]
            det = -det
        piv = int(A[c, c])
        det = det * piv % p
        if c + 1 < n:
            inv = pow(piv, p - 2, p)
            f = (A[c + 1:, c] * inv) % p
            A[c + 1:, c:] = (A[c + 1:, c:] - (f[:, None] * A[c, c:][None, :]) % p) % p
    return det % p


def ryser(X, p=None):
    """per X = (-1)^n sum over nonempty column sets S of (-1)^|S| prod_i sum_{j in S} x_ij (exact, or modulo p)."""
    n = len(X)
    total = 0
    for mask in range(1, 1 << n):
        prod = 1
        for i in range(n):
            s = 0
            for j in range(n):
                if mask >> j & 1:
                    s += X[i][j]
            prod *= s
            if p:
                prod %= p
        total += -prod if bin(mask).count("1") % 2 else prod
        if p:
            total %= p
    total *= (-1) ** n
    return total % p if p else total


def leibniz_per(X):
    n = len(X)
    return sum(math.prod(X[i][q[i]] for i in range(n)) for q in itertools.permutations(range(n)))


def bareiss(M):
    A = [list(r) for r in M]
    n = len(A)
    sign, prev = 1, 1
    for k in range(n - 1):
        if A[k][k] == 0:
            sw = next((r for r in range(k + 1, n) if A[r][k] != 0), None)
            if sw is None:
                return 0
            A[k], A[sw] = A[sw], A[k]
            sign = -sign
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                A[i][j] = (A[i][j] * A[k][k] - A[i][k] * A[k][j]) // prev
        prev = A[k][k]
    return sign * A[n - 1][n - 1]


# ---------------------------------------------------------------- beside

def corollary(n, X=None, p=P):
    """The skew circuit M_1 ... M_n: its operation count, and its value at X modulo p (or None)."""
    ops = 0
    prev = {frozenset([j]): (X[0][j] % p if X else None) for j in range(n)}
    for i in range(2, n + 1):
        cur = {}
        for c in itertools.combinations(range(n), i):
            t = frozenset(c)
            ops += 2 * i - 1
            if X:
                cur[t] = sum(prev[t - {j}] * X[i - 1][j] for j in c) % p
            else:
                cur[t] = None
        prev = cur
    value = prev[frozenset(range(n))] if X else None
    return ops, value


def dcs2():
    """Every 2 x 2 matrix with entries among x11, x12, x21, x22, -1, 0, 1: how many have determinant per_2."""
    choices = [(1, 1), (1, 2), (2, 1), (2, 2), -1, 0, 1]
    target = {((1, 1), (2, 2)): 1, ((1, 2), (2, 1)): 1}
    hits = 0
    total = 0
    for a, b, c, d in itertools.product(choices, repeat=4):
        total += 1
        rows = [{0: a, 1: b}, {0: c, 1: d}]
        rows = [{k: v for k, v in r.items() if v != 0} for r in rows]
        hits += expand(rows) == target
    return hits, total


# ---------------------------------------------------------------- controls

def controls_run(seed):
    ctl = {}
    st = Stream(seed, "grenet/controls")
    ok = True
    for n in range(1, 7):
        for _ in range(3):
            X = [[v - 50 for v in st.ints(n, 0, 100)] for _ in range(n)]
            ok &= ryser(X) == leibniz_per(X)
    ctl["Ryser's permanent equals the sum over permutations, n from 1 to 6"] = ok
    ok = True
    for size in list(range(1, 11)) + [20, 30, 40]:
        M = [[v - 1000 for v in st.ints(size, 0, 2000)] for _ in range(size)]
        ok &= det_mod(np.array(M, dtype=np.int64) % P) == bareiss(M) % P
    ctl["the modular determinant equals an exact one modulo 2^31 - 1, sizes 1 to 40"] = ok
    ok = True
    for _ in range(3):
        cells = st.ints(25, 0, 9)
        rows = [dict() for _ in range(5)]
        for k, c in enumerate(cells):
            u, v = divmod(k, 5)
            if c < 4:
                rows[u][v] = (u + 1, v + 1)
            elif c < 6:
                rows[u][v] = (-1, 1)[c - 4]
        got = expand(rows)
        want = {}
        for q in itertools.permutations(range(5)):
            coef, mono = 1, []
            for u in range(5):
                e = rows[u].get(q[u], 0)
                if isinstance(e, tuple):
                    mono.append(e)
                else:
                    coef *= e
            if coef:
                inv = sum(1 for a in range(5) for b in range(a + 1, 5) if q[a] > q[b])
                key = tuple(sorted(mono))
                want[key] = want.get(key, 0) + (-1) ** inv * coef
        ok &= got == {k: c for k, c in want.items() if c}
    ctl["the cycle-cover expansion equals the Leibniz sum on 5 x 5 matrices"] = ok
    ok = True
    for n in (2, 4, 6):
        neg = {k: -c for k, c in permanent_terms(n).items()}
        ok &= expand(grenet(n, even_fix=False)) == neg
    ctl["a planted fault caught: the singletons' loops left at 1 (n = 2, 4, 6) give -per"] = ok
    ok = True
    for n in (3, 4, 5):
        fault = ("arc", frozenset([0]), 1, 2)
        ok &= expand(grenet(n, fault=fault)) != permanent_terms(n)
    ctl["a planted fault caught: one arc's variable changed (n = 3, 4, 5)"] = ok
    X = point(Stream(seed, "grenet/points/8"), 8)
    ctl["a planted fault caught at n = 8: the singletons' loops left at 1"] = (
        det_mod(numeric(grenet(8, even_fix=False), X)) != ryser(X, P))
    return ctl


# ---------------------------------------------------------------- run

def run(seed, results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    ctl = controls_run(seed)
    if not all(ctl.values()):
        raise AssertionError(f"a control failed: {[k for k, v in ctl.items() if not v]}")

    cond, detail_n = {}, {}
    sizes, terms_count, small_points, consts_odd, cor = [], [], [], [], []
    for n in EXACT_N + MODULAR_N:
        rows = grenet(n)
        ok_entries = entries_ok(rows, n)
        sizes.append(len(rows))
        st = Stream(seed, f"grenet/points/{n}")
        agree = 0
        cor_ok = 0
        for _ in range(POINTS):
            X = point(st, n)
            per = ryser(X, P)
            agree += det_mod(numeric(rows, X)) == per
            cor_ok += corollary(n, X)[1] == per
        ops, _ = corollary(n)
        cor.append((n, ops, ops == (n - 1) * (2 ** n - 1) == sum((2 * i - 1) * math.comb(n, i) for i in range(2, n + 1)),
                    cor_ok))
        if n % 2:
            consts_odd.append((n, constants_of(rows)))
        info = {"size": len(rows), "entries_ok": ok_entries, "constants": constants_of(rows), "points_agree": agree}
        if n in EXACT_N:
            got = expand(rows)
            same = got == permanent_terms(n)
            info.update({"terms": len(got), "identical": same,
                         "coefficients": sorted(set(got.values()))})
            terms_count.append(len(got))
            small_points.append(agree)
            cond[f"n = {n}: {2 ** n - 1} square, entries ok, determinant identical to per_{n}"] = ok_entries and same
        else:
            cond[f"n = {n}: {2 ** n - 1} square, entries ok, determinant = per_{n} at {POINTS} of {POINTS} points"] = (
                ok_entries and agree == POINTS)
        detail_n[n] = info
    hits2, total2 = dcs2()
    three = expand(grenet(2)) == permanent_terms(2)
    bound = ((2 ** max(MODULAR_N) - 1) / P) ** POINTS

    values = {
        "sizes": ("sizes for n = 2..10: " + ", ".join(str(s) for s in sizes)
                  + ("; every entry a variable or -1, 0, 1" if all(detail_n[n]["entries_ok"] for n in detail_n)
                     else "; NOT every entry a variable or -1, 0, 1")),
        "exact": ("n = 2..7, every nonzero term: " + ", ".join(
            f"{n} {'identical' if detail_n[n]['identical'] else 'DIFFERS'}" for n in EXACT_N)),
        "exact_terms": "terms: " + ", ".join(str(t) for t in terms_count) + " (n! is "
                       + ", ".join(str(math.factorial(n)) for n in EXACT_N) + ")",
        "modular": ("modulo 2^31 - 1: " + ", ".join(f"n = {n} at {detail_n[n]['points_agree']} of {POINTS}"
                                                     for n in MODULAR_N)),
        "error_bound": f"a wrong n = 10 matrix passes four points with probability at most {bound:.1e}",
        "points_small": "n = 2..7 at the same points: " + ", ".join(f"{a} of {POINTS}" for a in small_points),
        "constants_odd": "constants for odd n: " + "; ".join(f"{n}: {c}" for n, c in consts_odd),
        "corollary": ("skew circuit ops (n-1)(2^n-1): " + ", ".join(f"{o}{'' if good else '!'}" for _, o, good, _ in cor)
                      + f"; its value per_n at {sum(c for *_, c in cor)} of {POINTS * len(cor)} points"),
        "dcs2": (f"2 x 2 of variables and -1, 0, 1 with determinant per_2: {hits2} of {total2}; the 3 x 3: "
                 + ("per_2" if three else "not per_2")),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"test": TEST, "conditions": cond, "controls": ctl, "n": {str(n): v for n, v in detail_n.items()},
              "corollary": [{"n": n, "ops": o, "formula_ok": g, "value_ok": c} for n, o, g, c in cor],
              "dcs2": {"hits": hits2, "total": total2, "three_by_three": three}, "error_bound": bound}
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
        sys.exit(f"grenet: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
