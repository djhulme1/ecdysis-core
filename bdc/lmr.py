"""Landsberg, Manivel & Ressayre's quadratic bound on the border determinantal complexity of the permanent: the two
dual-variety dimensions it rests on, read from Hessian ranks.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:5dc9ad960e92ffab) is from Landsberg,
Manivel and Ressayre, "Hypersurfaces with degenerate duals and the Geometric Complexity Theory Program", Commentarii
Mathematici Helvetici 88(2), 469-484, 2013 (arXiv:1004.4802): "We establish additional geometric properties of the
Mulmuley-Sohoni variety and prove a quadratic lower bound for the determinental border-complexity of the permanent."

Its registered test: refuted if, for some m from 2 to 10, the Hessian of perm_m has rank below m^2 at Mignon and
Ressayre's point (all entries 1 but the (1,1) entry, 1 - m, where perm_m = 0) and at each of 20 seed-drawn rational
points of perm_m = 0; or if, for some n from 2 to 10, the Hessian of det_n has rank other than 2n at
diag(1, ..., 1, 0) or at one of 20 seed-drawn integer matrices of rank n - 1. By Katz's formula these give the
dimensions, m^2 - 2 and 2n - 2, of the two dual varieties from which the paper's theorem gives n >= m^2/2.

The input is the paper's arXiv e-print (version 1, the only one, a gzipped tar), checked against its SHA-256 and size
and read in memory as data: its LMRdet260410.tex, in which the statements below are looked for. Nothing in it is run.
Every rule was fixed before any rank was computed; the seed draws the points.

1. The source. The tar must hold LMRdet260410.tex once, as UTF-8. With its whitespace collapsed, it must state the
   theorem, $\\ol{dc}(\\tperm_m)\\geq \\frac{m^2}2$, and Lemma 3.3's form of the determinant's Hessian at a matrix of
   rank n - 1, H_{\\det_n,w}(X)=...=\\sum_{i=1}^{n-1}(x_{nn}x_{ii}-x_{ni}x_{in}), or the run is refused. Four further
   statements are reported beside the test: Katz's formula as the paper writes it, dim Z(P)* = rank(H_{P,w}) - 2;
   Mignon and Ressayre's bound for dc, which it cites; its Theorem 1.3, dc-bar(P) >= (dim Z(P)* + 1)/2; and the
   opening of Lemma 3.3, a matrix of rank exactly n - 1.
2. The Hessians. perm_m and det_n are multilinear in the rows of the matrix, so the second derivative with respect to
   x_ij and x_kl is 0 when i = k or j = l. Otherwise, for the permanent it is the permanent of the matrix with rows
   i, k and columns j, l deleted, computed all at once from Ryser's formula differentiated twice: the sum, over the
   sets S of columns holding j and l, of (-1)^(m - |S|) times the product over the other rows of their sums over S
   (exact integers). For the determinant it is the determinant of the matrix with row i replaced by the unit vector
   e_j and row k by e_l (exact fraction-free elimination). Variables are ordered x_11, x_12, ..., x_mm, and the
   Hessian is the m^2 x m^2 matrix of these.
3. Ranks. A Hessian's rank over Q is at least its rank modulo a prime. The permanent's Hessians are certified of full
   rank m^2 when their rank modulo 2^61 - 1 or modulo 998244353 is m^2; otherwise their exact rank is found by
   fraction-free elimination over the integers. The determinant's Hessians' ranks are found exactly, by the same
   elimination.
4. The points. Mignon and Ressayre's point for m: every entry 1, the (1,1) entry 1 - m (its permanent is checked to be
   0). The seed's points for the permanent: rows 2 to m and the entries (1,2) to (1,m) drawn from -9 to 9, then the
   first row replaced by (-sum_j a_1j c_j, c a_12, ..., c a_1m), c the permanent of the minor of (1,1) and c_j that of
   (1,j), an integer point of perm_m = 0 (redrawn while c = 0). The determinant's points: diag(1, ..., 1, 0), and the
   seed's products U V of an n x (n - 1) and an (n - 1) x n matrix with entries from -3 to 3, kept when their exact
   rank is n - 1. Twenty seed points of each kind for each m and n from 2 to 10, drawn by SHA-256 of the seed, a label
   and a counter.
5. The conditions. For the permanent: for every m from 2 to 10, the Hessian has full rank m^2 at Mignon and
   Ressayre's point or at one of the seed's points (all twenty are computed and reported). For the determinant: for
   every n from 2 to 10, the Hessian has rank exactly 2n at diag(1, ..., 1, 0) and at each of the twenty. test_passed
   is 1 if both hold.
6. Beside the test: the closed form of Mignon and Ressayre's Hessian entries, (m - 2)! where the first row or the
   first column is among those deleted (the rest is all ones), and -2 (m - 3)! where the (1,1) entry survives the
   deletion, compared with the computed matrix; the bound the two
   dimensions give, n >= (m^2 - 2 + 2)/2, for m from 2 to 10, and what Theorem 1.3's (dim + 1)/2 gives with Katz's
   dimension, (m^2 - 1)/2.
7. Controls, known answers: the Hessians from rule 2 agree with second derivatives taken term by term from the
   Leibniz and permanent expansions for m = n = 3, and the permanent's with the permanents of the deleted
   submatrices for m = 4 and 5, at seed-drawn integer points; the modular and exact ranks agree on
   seed-drawn products of known inner dimension; and the determinant's Hessian at diag(1, ..., 1, 0) is twice the
   matrix of Lemma 3.3's printed form for n = 2 to 6.

What it cannot check: the paper's algebraic geometry, that the variety of hypersurfaces with degenerate duals is
closed and contains the orbit closure of the determinant, and Lemma 2.4 on padding by a linear form; the ranks prove
the two dimensions for m and n up to 10, and the bound for all m rests on those arguments.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 bdc/lmr.py
"""

import hashlib
import io
import itertools
import json
import math
import os
import re
import sys
import tarfile
from fractions import Fraction

INPUT = ("arXiv-1004.4802v1.tar.gz", "536d98ca346ade9335c451fc7f13f4a307d8972e16f304017f0ba1fa31e1253a", 20080)
MEMBER = "LMRdet260410.tex"
REQUIRED = (r"$\ol{dc}(\tperm_m)\geq \frac{m^2}2$",
            r"H_{\det_n,w}(X)=\det(w,\ldots ,w,X,X)=\sum_{i=1}^{n-1}(x_{nn}x_{ii}-x_{ni}x_{in})")
REPORTED = (r"$$\dim Z(P)^* = \trank (H_{P,w})-2,$$",
            r"$dc(\tperm_m)\geq \frac {m^2}2$, which was proved in \cite{MR2126826}",
            r"$$\ol{dc}(P)\geq \frac{\dim Z(P)^*+1}2.$$",
            r"Let $w$ be a matrix of rank exactly $n-1$.")
SIZES = range(2, 11)
POINTS = 20
PRIMES = (2 ** 61 - 1, 998244353)
OUTPUTS = ("statements", "perm_mr_ranks", "perm_mr_full", "perm_seed_full", "perm_full_all", "det_ranks",
           "det_points_ok", "det_points_total", "mr_closed_form", "bound", "conditions_met", "conditions_total",
           "test_passed", "controls_passed", "controls_total")
LIMIT = 200


class Refused(Exception):
    pass


# ---------------------------------------------------------------- reading the source

def read_input(inputs):
    name, sha, size = INPUT
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha or len(data) != size:
        raise Refused(f"{name}: sha256 {got} ({len(data)} bytes), not the registered {sha} ({size})")
    return data


def tex_of(data):
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            members = [m for m in tar.getmembers() if m.name == MEMBER]
            if len(members) != 1 or not members[0].isfile():
                raise Refused(f"the source holds {len(members)} regular members named {MEMBER}")
            raw = tar.extractfile(members[0]).read()
    except (tarfile.TarError, OSError, EOFError) as e:
        raise Refused(f"the source is not a gzipped tar: {e}")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise Refused(f"{MEMBER} is not UTF-8: {e}")


def statements_found(tex):
    flat = " ".join(tex.split())
    found = {s: flat.count(s) >= 1 for s in REQUIRED + REPORTED}
    missing = [s for s in REQUIRED if not found[s]]
    if missing:
        raise Refused(f"the TeX does not state {missing[0]!r}")
    return found


# ---------------------------------------------------------------- permanents, determinants, ranks

def permanent(A):
    """Ryser's formula, exact; the permanent of the empty matrix is 1."""
    k = len(A)
    if k == 0:
        return 1
    total = 0
    for size in range(1, k + 1):
        sign = (-1) ** (k - size)
        for S in itertools.combinations(range(k), size):
            p = 1
            for row in A:
                s = 0
                for j in S:
                    s += row[j]
                p *= s
                if p == 0:
                    break
            total += sign * p
    return total


def bareiss_det(A):
    """Exact determinant of an integer matrix by fraction-free elimination."""
    M = [list(r) for r in A]
    n = len(M)
    if n == 0:
        return 1
    sign, prev = 1, 1
    for c in range(n - 1):
        piv = next((i for i in range(c, n) if M[i][c] != 0), None)
        if piv is None:
            return 0
        if piv != c:
            M[c], M[piv] = M[piv], M[c]
            sign = -sign
        for i in range(c + 1, n):
            for j in range(c + 1, n):
                M[i][j] = (M[i][j] * M[c][c] - M[i][c] * M[c][j]) // prev
        prev = M[c][c]
    return sign * M[n - 1][n - 1]


def rank_mod(M, p):
    A = [[x % p for x in row] for row in M]
    rows, cols = len(A), len(A[0]) if A else 0
    r = 0
    for c in range(cols):
        piv = next((i for i in range(r, rows) if A[i][c]), None)
        if piv is None:
            continue
        A[r], A[piv] = A[piv], A[r]
        inv = pow(A[r][c], p - 2, p)
        A[r] = [(x * inv) % p for x in A[r]]
        for i in range(rows):
            if i != r and A[i][c]:
                f = A[i][c]
                A[i] = [(x - f * y) % p for x, y in zip(A[i], A[r])]
        r += 1
        if r == rows:
            break
    return r


def rank_exact(M):
    """Rank over Q of an integer matrix, by fraction-free elimination."""
    A = [list(r) for r in M]
    rows, cols = len(A), len(A[0]) if A else 0
    r, prev = 0, 1
    for c in range(cols):
        piv = next((i for i in range(r, rows) if A[i][c] != 0), None)
        if piv is None:
            continue
        A[r], A[piv] = A[piv], A[r]
        for i in range(r + 1, rows):
            for j in range(c + 1, cols):
                A[i][j] = (A[i][j] * A[r][c] - A[i][c] * A[r][j]) // prev
            A[i][c] = 0
        prev = A[r][c]
        r += 1
        if r == rows:
            break
    return r


def full_rank(M, size):
    """Rule 3: (rank, how) for a square integer matrix of the given size."""
    best = 0
    for p in PRIMES:
        rp = rank_mod(M, p)
        best = max(best, rp)
        if rp == size:
            return rp, f"mod {p}"
    return rank_exact(M), "exact"


def drop(A, rows, cols):
    return [[A[i][j] for j in range(len(A[i])) if j not in cols] for i in range(len(A)) if i not in rows]


def perm_hessian(A):
    """Rule 2 for the permanent: Ryser's formula differentiated with respect to x_ij and x_kl."""
    m = len(A)
    H = [[0] * (m * m) for _ in range(m * m)]
    for mask in range(1, 1 << m):
        cols = [c for c in range(m) if mask >> c & 1]
        if len(cols) < 2:
            continue
        sign = 1 if (m - len(cols)) % 2 == 0 else -1
        rs = [sum(A[r][c] for c in cols) for r in range(m)]
        for i in range(m):
            for k in range(i + 1, m):
                q = sign
                for r in range(m):
                    if r != i and r != k:
                        q *= rs[r]
                        if q == 0:
                            break
                if q == 0:
                    continue
                for j in cols:
                    row = H[i * m + j]
                    for l in cols:
                        if l != j:
                            row[k * m + l] += q
    for a in range(m * m):              # filled for i < k, so above the diagonal; mirror it
        for b in range(a + 1, m * m):
            H[b][a] = H[a][b]
    return H


def perm_hessian_minors(A):
    """The same entries as permanents of the deleted submatrices (a control)."""
    m = len(A)
    idx = [(i, j) for i in range(m) for j in range(m)]
    H = [[0] * (m * m) for _ in range(m * m)]
    for a, (i, j) in enumerate(idx):
        for b, (k, l) in enumerate(idx):
            if i != k and j != l:
                H[a][b] = permanent(drop(A, {i, k}, {j, l}))
    return H


def det_hessian(w):
    """Rule 2 for the determinant: rows i and k replaced by e_j and e_l."""
    n = len(w)
    idx = [(i, j) for i in range(n) for j in range(n)]
    H = [[0] * (n * n) for _ in range(n * n)]
    for a, (i, j) in enumerate(idx):
        for b, (k, l) in enumerate(idx):
            if b < a or i == k or j == l:
                continue
            M = [list(r) for r in w]
            M[i] = [1 if c == j else 0 for c in range(n)]
            M[k] = [1 if c == l else 0 for c in range(n)]
            H[a][b] = H[b][a] = bareiss_det(M)
    return H


# ---------------------------------------------------------------- seeded draws and points

class Stream:
    def __init__(self, seed, label):
        self.seed, self.label, self.n = seed, label, 0

    def below(self, k):
        self.n += 1
        h = hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
        return int.from_bytes(h[:8], "big") % k

    def between(self, lo, hi):
        return lo + self.below(hi - lo + 1)


def mr_point(m):
    A = [[1] * m for _ in range(m)]
    A[0][0] = 1 - m
    return A


def perm_point(st, m, lo=-9, hi=9):
    """Rule 4: an integer point of perm_m = 0."""
    while True:
        A = [[st.between(lo, hi) for _ in range(m)] for _ in range(m)]
        c = [permanent(drop(A, {0}, {j})) for j in range(m)]
        if c[0] == 0:
            continue
        rest = sum(A[0][j] * c[j] for j in range(1, m))
        A[0] = [-rest] + [c[0] * A[0][j] for j in range(1, m)]
        return A


def matmul(X, Y):
    return [[sum(X[i][t] * Y[t][j] for t in range(len(Y))) for j in range(len(Y[0]))] for i in range(len(X))]


def det_point(st, n, lo=-3, hi=3):
    """Rule 4: an integer matrix of rank exactly n - 1."""
    while True:
        U = [[st.between(lo, hi) for _ in range(n - 1)] for _ in range(n)]
        V = [[st.between(lo, hi) for _ in range(n)] for _ in range(n - 1)]
        w = matmul(U, V)
        if rank_exact(w) == n - 1:
            return w


def diag_point(n):
    return [[1 if (i == j and i < n - 1) else 0 for j in range(n)] for i in range(n)]


# ---------------------------------------------------------------- beside the test and controls

def mr_closed_form(m):
    """Rule 6: Mignon and Ressayre's Hessian entries in closed form."""
    idx = [(i, j) for i in range(m) for j in range(m)]
    H = [[0] * (m * m) for _ in range(m * m)]
    for a, (i, j) in enumerate(idx):
        for b, (k, l) in enumerate(idx):
            if i == k or j == l:
                continue
            if 0 in (i, k) or 0 in (j, l):
                H[a][b] = math.factorial(m - 2)
            else:
                H[a][b] = -2 * math.factorial(m - 3)
    return H


def printed_form(n):
    """Lemma 3.3's form at diag(1, ..., 1, 0): sum over i < n of x_nn x_ii - x_ni x_in, as a symmetric matrix times 2."""
    def v(i, j):
        return i * n + j
    Q = [[0] * (n * n) for _ in range(n * n)]
    last = n - 1
    for i in range(n - 1):
        for a, b, s in ((v(last, last), v(i, i), 1), (v(last, i), v(i, last), -1)):
            Q[a][b] += s
            Q[b][a] += s
    return Q


def term_by_term(A, signed):
    """Second derivatives of the Leibniz (signed) or permanent expansion, term by term."""
    n = len(A)
    idx = [(i, j) for i in range(n) for j in range(n)]
    H = [[0] * (n * n) for _ in range(n * n)]
    for sigma in itertools.permutations(range(n)):
        sgn = 1
        if signed:
            inv = sum(1 for x in range(n) for y in range(x + 1, n) if sigma[x] > sigma[y])
            sgn = -1 if inv % 2 else 1
        for a, (i, j) in enumerate(idx):
            if sigma[i] != j:
                continue
            for b, (k, l) in enumerate(idx):
                if k == i or sigma[k] != l:
                    continue
                prod = sgn
                for r in range(n):
                    if r not in (i, k):
                        prod *= A[r][sigma[r]]
                H[a][b] += prod
    return H


def controls_known(seed):
    st = Stream(seed, "lmr/controls")
    A = [[st.between(-9, 9) for _ in range(3)] for _ in range(3)]
    hess_ok = perm_hessian(A) == term_by_term(A, False) and det_hessian(A) == term_by_term(A, True)
    for m in (4, 5):
        B = [[st.between(-9, 9) for _ in range(m)] for _ in range(m)]
        hess_ok &= perm_hessian(B) == perm_hessian_minors(B)
    rank_ok = True
    for inner in (1, 2, 3, 5):
        U = [[st.between(-5, 5) for _ in range(inner)] for _ in range(7)]
        V = [[st.between(-5, 5) for _ in range(7)] for _ in range(inner)]
        M = matmul(U, V)
        r = rank_exact(M)
        rank_ok &= r <= inner and all(rank_mod(M, p) <= r for p in PRIMES) and r == rank_mod(M, PRIMES[0])
    form_ok = all(det_hessian(diag_point(n)) == printed_form(n) for n in range(2, 7))
    return {"the Hessians from rule 2 equal term-by-term second derivatives and deleted-submatrix permanents":
            bool(hess_ok),
            "modular and exact ranks agree on products of known inner dimension": bool(rank_ok),
            "the determinant's Hessian at diag(1, ..., 1, 0) is twice Lemma 3.3's printed form": bool(form_ok)}


# ---------------------------------------------------------------- the run

def run(seed, inputs="inputs", results="results", sizes=SIZES, points=POINTS):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    found = statements_found(tex_of(read_input(inputs)))

    perm = {}
    for m in sizes:
        A = mr_point(m)
        if permanent(A) != 0:
            raise AssertionError(f"Mignon and Ressayre's point is not a zero for m = {m}")
        H = perm_hessian(A)
        r, how = full_rank(H, m * m)
        st = Stream(seed, f"lmr/perm/{m}")
        seeded = []
        for _ in range(points):
            P = perm_point(st, m)
            if permanent(P) != 0:
                raise AssertionError("a drawn point is not a zero")
            rs, hs = full_rank(perm_hessian(P), m * m)
            seeded.append(rs)
        perm[m] = {"mr_rank": r, "mr_how": how, "mr_closed_form": H == mr_closed_form(m), "seeded": seeded,
                   "full": r == m * m or any(x == m * m for x in seeded)}

    det = {}
    for n in sizes:
        r0 = rank_exact(det_hessian(diag_point(n)))
        st = Stream(seed, f"lmr/det/{n}")
        seeded = [rank_exact(det_hessian(det_point(st, n))) for _ in range(points)]
        det[n] = {"diag_rank": r0, "seeded": seeded, "ok": r0 == 2 * n and all(x == 2 * n for x in seeded)}

    cond = {
        "for every m from 2 to 10 the permanent's Hessian has full rank m^2 at a zero tried":
            all(perm[m]["full"] for m in sizes),
        "for every n from 2 to 10 the determinant's Hessian has rank 2n at every rank n - 1 point tried":
            all(det[n]["ok"] for n in sizes),
    }
    controls = controls_known(seed)
    ok_points = sum((det[n]["diag_rank"] == 2 * n) + sum(x == 2 * n for x in det[n]["seeded"]) for n in sizes)
    values = {
        "statements": f"{sum(found.values())} of {len(found)} found",
        "perm_mr_ranks": ", ".join(f"{m}: {perm[m]['mr_rank']}/{m * m}" for m in sizes),
        "perm_mr_full": sum(perm[m]["mr_rank"] == m * m for m in sizes),
        "perm_seed_full": sum(sum(x == m * m for x in perm[m]["seeded"]) for m in sizes),
        "perm_full_all": sum(perm[m]["full"] for m in sizes),
        "det_ranks": ", ".join(f"{n}: {det[n]['diag_rank']}"
                               + ("" if all(x == det[n]["diag_rank"] for x in det[n]["seeded"])
                                  else "/" + "/".join(str(x) for x in sorted(set(det[n]["seeded"]))))
                               for n in sizes),
        "det_points_ok": ok_points,
        "det_points_total": len(list(sizes)) * (points + 1),
        "mr_closed_form": f"{sum(perm[m]['mr_closed_form'] for m in sizes)} of {len(list(sizes))} as the closed form",
        "bound": ("n >= m^2/2: " + ", ".join(f"{m}: {math.ceil(m * m / 2)}" for m in sizes)
                  + "; Theorem 1.3's (dim + 1)/2 with Katz's dimension: "
                  + ", ".join(f"{math.ceil((m * m - 1) / 2)}" for m in sizes)),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(controls.values()), "controls_total": len(controls),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"input": {"name": INPUT[0], "sha256": INPUT[1]}, "statements": found, "conditions": cond,
              "controls": controls, "perm": {str(m): perm[m] for m in sizes}, "det": {str(n): det[n] for n in sizes}}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"lmr: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
