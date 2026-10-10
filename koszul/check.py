#!/usr/bin/env python3
"""Landsberg & Ottaviani's lower bound for the border rank of matrix multiplication, by its own Koszul flattening, for an
Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:72c84a0906e77f5f) is from Landsberg &
Ottaviani, "New lower bounds for the border rank of matrix multiplication" (Theory of Computing 11 (2015);
arXiv:1112.6007): "The border rank of the matrix multiplication operator for n by n matrices is a standard measure of its
complexity. Using techniques from algebraic geometry and representation theory, we show the border rank is at least
2n^2-n." Its registered test: refuted if, for some n from 2 to 5, the Koszul flattening of the paper's section 3 proof
(M_<n> with its A factor projected onto A' = S^{2n-2}W* by e_i (x) f_j -> a_{i+j}, p = n-1: Lambda^{n-1}A' (x) B* ->
Lambda^n A' (x) C, an integer matrix of order 12, 90, 560 and 3,150) is not injective over Q, so that its rank divided by
C(2n-2, n-1) falls below 2n^2-n (6, 15, 28, 45); or if an explicit border rank decomposition of M_<n> with fewer than
2n^2-n terms is shown for any n.

Standard library only; nothing is read in. The rules were fixed before any seed existed; the seed draws only the
controls' random tensors, so the test itself does not depend on it.

1. The tensor (the paper's section 3). For <m, n, l>: A = M (x) N*, B = N (x) L*, C = L (x) M*, and the matrix
   multiplication tensor is sum over i < m, j < n, k < l of a_ij (x) b_jk (x) c_ki. Its A factor is projected onto
   A' = S^{m+n-2}W*, of dimension m + n - 1, by polynomial multiplication (Remark 3.2): a_ij -> x_{i+j}.
2. The Koszul flattening (Theorem 2.1). For T = sum of coefficients t(s, beta, gamma) x_s (x) b_beta (x) c_gamma in
   A' (x) B (x) C, T_A'^{wedge p}: Lambda^p A' (x) B* -> Lambda^{p+1} A' (x) C sends x_S (x) b*_beta to the sum over s
   and gamma of t(s, beta, gamma) (x_s wedge x_S) (x) c_gamma, with x_s wedge x_S = (-1)^{#{t in S : t < s}} x_{S + s}
   for s not in S. Rows and columns are ordered by the subsets S in lexicographic order and then the basis of C or B*.
3. The rank. Each flattening is reduced modulo three primes, 2^31 - 1, 2^61 - 1 and 998244353, by Gaussian elimination
   over the field; full rank modulo any prime means a nonzero determinant over Z, so the map is injective over Q. The
   rank over Q is at least the largest of the three; they must agree.
4. The bound. ur(T) >= rank / C(a - 1, p) (Theorem 2.1), with a = 2n - 1 and p = n - 1 for <n, n, n> (Corollary 1.2),
   as an exact fraction; Lemma 3.1 carries it from the projected tensor back to M_<n>.

test_passed is 1 if, for every n from 2 to 5, the flattening of order n^2 C(2n - 1, n - 1) has full rank modulo all three
primes, so that rank / C(2n - 2, n - 1) = 2n^2 - n; else 0. The test's last clause (an explicit decomposition with fewer
terms) is a matter of the literature, where none is known, and no run can show its absence.

Controls (controls_passed counts those that behave as stated):
(a) rank one: for x, y, z drawn from the seed with no zero coordinate, the flattening of x (x) y (x) z has rank exactly
    C(a - 1, p) (the computation in the paper's section 2), for (a, p, dim B, dim C) = (3, 1, 4, 4), (5, 2, 9, 9),
    (7, 3, 16, 16);
(b) the bound cannot exceed a known rank: for <3, 3, 3>'s shapes, sums of r = 14 rank-one tensors drawn from the seed
    (three of them) give rank at most 14 C(4, 2) = 84 < 90, so their bound stays at most 14, below 15;
(c) the rectangular cases of Theorem 1.1, (m, n, l) = (3, 2, 2), (4, 2, 3) and (4, 3, 2), each with n <= m and
    p = n - 1: full rank, so the bound is n l (n + m - 1)/m = 16/3, 15/2 and 9;
(d) the paper's projection matters: projecting M_<3>'s A factor by a_ij -> x_i instead (forgetting j) leaves a tensor
    of rank at most 9 (the sum over i and k of x_i (x) (sum_j b_jk) (x) c_ki), so its flattening's bound must be at most 9,
    not 15. (A first draft's control, M_<3> with every sign taken as +1, was dropped before any seed: that matrix is of
    full rank too, so it showed nothing.)
(e) the bound is not had for free: the same flattening of M_<2> with p = 0 (a mere slice) gives at most C(a - 1, 0)
    times the bound's numerator, a bound of 4, not 6.

What it cannot check: the paper's proof for general n (the test samples n from 2 to 5), the representation theory of its
section 4, and whether a smaller decomposition exists.

Writes results/outputs.json and results/detail.json. Run with: python3 koszul/check.py
"""

import importlib.util
import json
import os
import re
import sys
import time
from fractions import Fraction
from itertools import combinations
from math import comb

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("koszul_mm", os.path.join(HERE, "..", "mm", "check.py"))
MM = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(MM)
Stream = MM.Stream

PRIMES = (2 ** 31 - 1, 2 ** 61 - 1, 998244353)
SIZES = (2, 3, 4, 5)
ORDERS = {2: 12, 3: 90, 4: 560, 5: 3150}
RECTANGULAR = ((3, 2, 2), (4, 2, 3), (4, 3, 2))
RANK_ONE = ((3, 1, 4, 4), (5, 2, 9, 9), (7, 3, 16, 16))
LOW_RANK, LOW_RANK_TRIALS = 14, 3
ENTRY = 1000                 # the controls' coefficients: integers from -ENTRY to ENTRY, never 0 for rank one


def mm_projected(m, n, l):
    """Rule 1: <m, n, l> with A projected onto S^{m+n-2}W*: {(s, beta, gamma): 1}, beta = (j, k) in B* and
    gamma = (k, i) in C, each as an index j*l + k and k*m + i."""
    t = {}
    for i in range(m):
        for j in range(n):
            for k in range(l):
                key = (i + j, j * l + k, k * m + i)
                t[key] = t.get(key, 0) + 1
    return t, m + n - 1, n * l, l * m


def mm_forgetful(n):
    """Control (d): <n, n, n> with a_ij -> x_i, in the same shapes as rule 1's projection (A' of dimension 2n - 1)."""
    t = {}
    for i in range(n):
        for j in range(n):
            for k in range(n):
                key = (i, j * n + k, k * n + i)
                t[key] = t.get(key, 0) + 1
    return t, 2 * n - 1, n * n, n * n


def flattening(t, a, b, c, p, signed=True):
    """Rule 2: the matrix of T_A^{wedge p}, as rows of {column: integer}; columns (S, beta), rows (S', gamma)."""
    by_beta = {}
    for (s, beta, gamma), v in t.items():
        if v:
            by_beta.setdefault(beta, []).append((s, gamma, v))
    cols = [(S, beta) for S in combinations(range(a), p) for beta in range(b)]
    row_index = {}
    for S in combinations(range(a), p + 1):
        for gamma in range(c):
            row_index[(S, gamma)] = len(row_index)
    rows = [dict() for _ in range(len(row_index))]
    for ci, (S, beta) in enumerate(cols):
        members = set(S)
        for s, gamma, v in by_beta.get(beta, ()):
            if s in members:
                continue
            sign = -1 if signed and sum(1 for x in S if x < s) % 2 else 1
            r = row_index[(tuple(sorted(S + (s,))), gamma)]
            rows[r][ci] = rows[r].get(ci, 0) + sign * v
    return rows, len(cols)


def rank_mod(rows, prime):
    """Rule 3: the rank of the matrix modulo prime, by elimination on sparse rows (pivot on each row's least column)."""
    pivots, rank = {}, 0
    for row in rows:
        r = {c: v % prime for c, v in row.items() if v % prime}
        while r:
            c = min(r)
            if c not in pivots:
                inv = pow(r[c], prime - 2, prime)
                pivots[c] = {k: v * inv % prime for k, v in r.items()}
                rank += 1
                break
            f, pr = r[c], pivots[c]
            for k, v in pr.items():
                x = (r.get(k, 0) - f * v) % prime
                if x:
                    r[k] = x
                else:
                    r.pop(k, None)
    return rank


def ranks(rows):
    return [rank_mod(rows, q) for q in PRIMES]


def random_tensor(stream, a, b, c, terms, nonzero=False):
    """A sum of rank-one tensors x (x) y (x) z with integer coordinates drawn from the stream (x, then y, then z, for each
    term in turn), as {(s, beta, gamma): coefficient}."""
    def draw():
        while True:
            v = stream.below(2 * ENTRY + 1) - ENTRY
            if v or not nonzero:
                return v
    t = {}
    for _ in range(terms):
        x = [draw() for _ in range(a)]
        y = [draw() for _ in range(b)]
        z = [draw() for _ in range(c)]
        for s in range(a):
            for beta in range(b):
                for gamma in range(c):
                    v = x[s] * y[beta] * z[gamma]
                    if v:
                        t[(s, beta, gamma)] = t.get((s, beta, gamma), 0) + v
    return t


def run(seed, results="results", sizes=SIZES, log=print):
    started = time.monotonic()
    out, detail = {}, {"primes": list(PRIMES), "sizes": list(sizes), "square": [], "controls": []}

    # The test: <n, n, n> for each n.
    square_ok, bounds, rank_list, order_list = True, [], [], []
    for n in sizes:
        t0 = time.monotonic()
        t, a, b, c = mm_projected(n, n, n)
        p = n - 1
        rows, ncols = flattening(t, a, b, c, p)
        rk = ranks(rows)
        order = len(rows)
        bound = Fraction(max(rk), comb(a - 1, p))
        full = len(rows) == ncols and all(x == order for x in rk)
        square_ok = square_ok and full and bound == 2 * n * n - n and (n not in ORDERS or ORDERS[n] == order)
        bounds.append(bound)
        rank_list.append(max(rk))
        order_list.append(order)
        detail["square"].append({"n": n, "order": order, "columns": ncols, "ranks_mod_primes": rk, "full": full,
                                 "bound": str(bound), "target": 2 * n * n - n,
                                 "seconds": round(time.monotonic() - t0, 2)})
        log(f"koszul: n = {n}: order {order}, ranks {rk}, bound {bound} (target {2 * n * n - n}), "
            f"{time.monotonic() - t0:.1f} s")
    primes_agree = all(len(set(row["ranks_mod_primes"])) == 1 for row in detail["square"])

    # Controls.
    controls = []
    stream = Stream(seed, "koszul/rank-one")
    ok = True
    for a, p, b, c in RANK_ONE:
        rows, _ = flattening(random_tensor(stream, a, b, c, 1, nonzero=True), a, b, c, p)
        rk = ranks(rows)
        ok = ok and all(x == comb(a - 1, p) for x in rk)
        detail["controls"].append({"control": f"rank one, a = {a}, p = {p}", "ranks": rk, "expected": comb(a - 1, p)})
    controls.append({"control": "rank one gives C(a - 1, p)", "passed": ok})

    stream = Stream(seed, "koszul/low-rank")
    worst = []
    for trial in range(LOW_RANK_TRIALS):
        rows, _ = flattening(random_tensor(stream, 5, 9, 9, LOW_RANK), 5, 9, 9, 2)
        rk = max(ranks(rows))
        worst.append(rk)
    low_ok = all(r <= LOW_RANK * comb(4, 2) for r in worst)
    detail["controls"].append({"control": f"sums of {LOW_RANK} rank-one tensors in <3,3,3>'s shapes", "ranks": worst,
                               "at_most": LOW_RANK * comb(4, 2)})
    controls.append({"control": f"rank-{LOW_RANK} tensors bound at most {LOW_RANK}", "passed": low_ok})

    rect = []
    for m, n, l in RECTANGULAR:
        t, a, b, c = mm_projected(m, n, l)
        rows, ncols = flattening(t, a, b, c, n - 1)
        rk = ranks(rows)
        bound = Fraction(max(rk), comb(a - 1, n - 1))
        rect.append(bound)
        detail["controls"].append({"control": f"<{m},{n},{l}>", "ranks": rk, "columns": ncols, "bound": str(bound),
                                   "formula": str(Fraction(n * l * (n + m - 1), m))})
    rect_ok = all(b == Fraction(n * l * (n + m - 1), m) for b, (m, n, l) in zip(rect, RECTANGULAR))
    controls.append({"control": "Theorem 1.1's rectangular cases", "passed": rect_ok})

    t, a, b, c = mm_forgetful(3)
    rows, ncols = flattening(t, a, b, c, 2)
    forgetful = Fraction(max(ranks(rows)), comb(a - 1, 2))
    detail["controls"].append({"control": "M_<3> projected by a_ij -> x_i", "bound": str(forgetful), "at_most": 9})
    controls.append({"control": "the paper's projection matters", "passed": forgetful <= 9})

    t, a, b, c = mm_projected(2, 2, 2)
    rows, ncols = flattening(t, a, b, c, 0)
    slice_bound = Fraction(max(ranks(rows)), comb(a - 1, 0))
    detail["controls"].append({"control": "M_<2> with p = 0", "bound": str(slice_bound)})
    controls.append({"control": "p = 0 gives no more than 4", "passed": slice_bound <= 4})

    out.update({
        "sizes": ",".join(map(str, sizes)),
        "orders": ",".join(map(str, order_list)),
        "ranks": ",".join(map(str, rank_list)),
        "bounds": ",".join(str(b) for b in bounds),
        "targets": ",".join(str(2 * n * n - n) for n in sizes),
        "primes_agree": int(primes_agree),
        "rank_one_ok": int(controls[0]["passed"]),
        "low_rank_max": max(worst),
        "rect_bounds": ",".join(str(b) for b in rect),
        "forgetful_bound_3": str(forgetful),
        "slice_bound_2": str(slice_bound),
        "controls_passed": sum(1 for c_ in controls if c_["passed"]),
        "controls_total": len(controls),
        "test_passed": int(square_ok and primes_agree),
    })
    detail["control_results"] = controls
    detail["seconds"] = round(time.monotonic() - started, 1)
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as f:
        json.dump(detail, f, indent=1, sort_keys=True)
        f.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    out, _ = run(seed, log=lambda s: print(s, file=sys.stderr, flush=True))
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
