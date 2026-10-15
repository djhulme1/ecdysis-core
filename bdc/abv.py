#!/usr/bin/env python3
"""Alper, Bogart & Velasco: the determinantal complexity of the 3 x 3 permanent is 7, checked in the two computed facts
it rests on, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from J. Alper, T. Bogart and M. Velasco, "A
lower bound for the determinantal complexity of a hypersurface" (arXiv:1505.02205v1, May 2015; Found. Comput. Math. 17
(2017), 829-836): "As a result, we obtain that the determinantal complexity of the $3 \\times 3$ permanent is $7$."

The test, as registered: see TEST below. The input is the claim's data of record, the e-print's source
(arXiv-1505.02205v1.tar.gz), checked against its SHA-256 and read as TeX (PermVsDetarxiv.tex). sympy (1.12) in the
pinned scipy-notebook image, no network. Every rule below was fixed before any Groebner basis of the permanent's ideal
was computed and before Grenet's matrix for n = 3 was expanded.

The paper (its TeX numbers definitions, theorems, corollaries and remarks on one counter): Theorem 1.2, dc(f) >=
codim(Sing(f)) + 1 for a form f of degree d > 2 whose singular locus has codimension above 4; the bounds n^2/2 <=
dc(perm_n) <= 2^n - 1, the upper one Grenet's; "it can be readily computed that codim(Sing(perm_3)) = 6"; hence
Corollary 1.4, dc(perm_3) = 7 over any field of characteristic other than 2. Sing(f) is the singular locus of the
hypersurface V(f) in k^n, where f and its partial derivatives vanish.

1. The statements. Each of REQUIRED is found in the TeX with its whitespace collapsed, or the run refuses: Theorem
   1.2's inequality and hypothesis, the bounds with Grenet's name, the sentence giving codim 6 (and 8 for perm_4) and
   Corollary 1.4. Theorem 1.8's printed 5 x 5 matrix is read for a check beside the test.
2. The singular locus. In k[x11, ..., x33], k = Q or F_p (p = 3, 5, 7), J is the ideal of perm_3 = sum over the
   permutations s of x_1s(1) x_2s(2) x_3s(3) and its nine partial derivatives (each a 2 x 2 subpermanent). sympy's
   groebner gives J's reduced Groebner basis in grevlex order with x11 > x12 > ... > x33 (with modulus=p over F_p);
   the dimension of V(J) over the algebraic closure is that of the initial ideal, the largest set S of variables such
   that every leading monomial involves a variable outside S; codim = 9 - dim.
3. Grenet's construction, for n = 3: the rows and columns are the subsets of {1, 2, 3} other than {1, 2, 3}, in the
   order {}, {1}, {2}, {3}, {1,2}, {1,3}, {2,3}; row S holds x_(|S|+1)j in column S + {j} for each j not in S when
   |S| < 2, and, when |S| = 2, x_3j in column {} (the empty set closing the cycle) for the j not in S; 1 on the
   diagonal but at {}; 0 elsewhere. Its determinant is expanded exactly, as a polynomial with integer coefficients
   (rows in order, memoised on the set of columns used, each step's sign the number of used columns above the new
   one), and compared with perm_3 term by term. A cycle cover of its graph is one cycle {} -> {j1} -> {j1,j2} -> {}
   with the remaining four vertices on their loops, so the determinant is (-1)^(n-1) perm_n, perm_3 for n = 3.
4. The test's five conditions: codim 6 over Q, F_3, F_5 and F_7 (four), and Grenet's matrix is 7 x 7 with entries 0, 1
   or a variable and determinant perm_3 identically (one). test_passed is 1 if all five hold.
5. Beside, none of it counted: (a) the dimension over C by an independent method, the torus decomposition of V of
   the nine partials (for each support S of nonzero coordinates, a partial x^u + x^v with exactly one term on S rules
   S out; those with both terms on S give x^(u-v) = -1, solvable on the torus iff every integer relation among the
   exponent differences has an even sum, the solutions then of dimension |S| minus their rank); by Euler's identity
   perm_3 lies in the ideal of its partials in characteristic 0, so this is V(J); (b) over F_2, where perm_3 = det_3,
   the codimension by the same Groebner route; (c) the families the singular locus visibly holds (one nonzero row, one
   nonzero column, two zero columns: the paper's Remark 1.5), each an identity of the partials; (d) Proposition 2.1 on
   Grenet's matrix: the rank of its constant part, which must be m - 1 = 6; (e) Grenet's construction for n = 2, 4
   and 5 (sizes 3, 15 and 31) against (-1)^(n-1) perm_n at three seed-drawn integer points each, in exact integer
   determinants (Bareiss); (f) Theorem 1.8's printed 5 x 5 matrix, its determinant against xy^2 + yt^2 + z^3.

Controls (controls_passed counts those that behave as stated; the run stops if any fails): the dimension routes on
det_3's singular locus, the rank <= 1 matrices (codim 4 over Q and F_3 by Groebner bases, and by the torus method);
the dimension of a monomial ideal with a known answer, and the torus method's parity rule on two binomial systems
whose solvability is known; the polynomial determinant against the sum over permutations on seed-drawn integer
matrices; and a planted fault in Grenet's matrix (x11 written x12) making the determinant differ from perm_3.

What it cannot check: Theorem 1.2's proof; codim Sing(perm_4) = 8, whose Groebner basis this check does not attempt;
the characteristics other than 0, 3, 5 and 7.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 bdc/abv.py
"""

import hashlib
import io
import itertools
import json
import os
import re
import sys
import tarfile

INPUT = ("arXiv-1505.02205v1.tar.gz", "f3e318ba4cbeac3c5888eca99bd52460da5ab7752ee08992569dcab3977beeb5", 9348)
MEMBER = "PermVsDetarxiv.tex"
REQUIRED = (r"If $\codim(\Sing(f)) > 4$, then $$\dc(f) \ge \codim(\Sing(f)) + 1.$$",
            r"n^2/2 \le \dc(\perm_n) \le 2^n - 1",
            r"the upper bound was established by Grenet \cite{grenet}",
            r"Since it can be readily computed that $\codim(\Sing(\perm_3)) = 6$ and $\codim(\Sing(\perm_4)) = 8$",
            r"Then $\dc(\perm_3) = 7$ and $\dc(\perm_4) \ge 9$.",
            r"Then $\dc(xy^2+yt^2+z^3) = 5$.")
CUBIC_START = r"f = \det \left(\begin{array}{rrrrr}"
CUBIC_END = r"\end{array}\right)$$"
PRIMES = (3, 5, 7)
OTHER_N = (2, 4, 5)
POINTS = 3
OUTPUTS = ("statements", "codim_q", "codim_f3", "codim_f5", "codim_f7", "bases", "grenet", "torus", "char2",
           "families", "prop21", "grenet_other", "cubic", "conditions_met", "conditions_total", "test_passed",
           "controls_passed", "controls_total")
LIMIT = 200
TEST = ("Refuted if the singular locus of the 3 × 3 permanent's hypersurface (the points of 9-dimensional space where "
        "perm_3 and its nine partial derivatives vanish) does not have codimension 6 over Q, F_3, F_5 or F_7, computed "
        "exactly from a Gröbner basis, so that the paper's Theorem 1.2 would not give dc(perm_3) ≥ 7; or if Grenet's "
        "construction, the upper bound 2^n − 1 the paper cites, does not write perm_3 as the determinant of a 7 × 7 "
        "matrix whose entries are 0, 1 or a variable, identically over the integers.")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- reading the source (rule 1)

def read_input(inputs):
    name, sha, size = INPUT
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha or len(data) != size:
        raise Refused(f"{name}: sha256 {got} ({len(data)} bytes), not the registered {sha} ({size})")
    return data


def tex_of(data, member=MEMBER):
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            members = [m for m in tar.getmembers() if m.name == member]
            if len(members) != 1 or not members[0].isfile():
                raise Refused(f"the source holds {len(members)} regular members named {member}")
            raw = tar.extractfile(members[0]).read()
    except (tarfile.TarError, OSError, EOFError) as e:
        raise Refused(f"the source is not a gzipped tar: {e}")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise Refused(f"{member} is not UTF-8: {e}")


def flat(tex):
    return " ".join(tex.split())


def statements_found(tex, required=REQUIRED):
    f = flat(tex)
    missing = [s for s in required if f.count(s) != 1]
    if missing:
        raise Refused(f"the TeX does not state, exactly once, {missing[0]!r}")
    return len(required)


def cubic_matrix(tex):
    """Theorem 1.8's printed matrix: entries 0, 1, or a signed variable among x, y, z, t."""
    f = flat(tex)
    if f.count(CUBIC_START) != 1:
        raise Refused("the TeX does not print Theorem 1.8's matrix exactly once")
    body = f.split(CUBIC_START, 1)[1].split(CUBIC_END, 1)[0]
    rows = [r.strip() for r in body.split(r"\\") if r.strip()]
    out = []
    for r in rows:
        cells = []
        for c in r.split("&"):
            c = c.replace(" ", "")
            m = re.fullmatch(r"(-?)([xyzt]|[01])", c)
            if not m:
                raise Refused(f"cannot read the entry {c!r} of Theorem 1.8's matrix")
            cells.append((m.group(1) == "-", m.group(2)))
        out.append(cells)
    if len(out) != 5 or any(len(r) != 5 for r in out):
        raise Refused("Theorem 1.8's matrix is not 5 x 5")
    return out


# ---------------------------------------------------------------- polynomials as {exponents: coefficient}

def padd(p, q, s=1):
    r = dict(p)
    for k, v in q.items():
        r[k] = r.get(k, 0) + s * v
        if r[k] == 0:
            del r[k]
    return r


def pmul(p, q):
    r = {}
    for a, x in p.items():
        for b, y in q.items():
            k = tuple(i + j for i, j in zip(a, b))
            r[k] = r.get(k, 0) + x * y
    return {k: v for k, v in r.items() if v}


def var(i, nv):
    return {tuple(1 if t == i else 0 for t in range(nv)): 1}


def const(c, nv):
    return {(0,) * nv: c} if c else {}


def poly_det(A, nv):
    """The determinant of a square matrix of polynomials, rows in order, memoised on the set of columns used."""
    m = len(A)
    D = {0: const(1, nv)}
    for k in range(m):
        E = {}
        for mask, val in D.items():
            for c in range(m):
                if mask >> c & 1 or not A[k][c]:
                    continue
                above = bin(mask >> (c + 1)).count("1")
                term = pmul(val, A[k][c])
                nm = mask | (1 << c)
                E[nm] = padd(E.get(nm, {}), term, -1 if above % 2 else 1)
        D = {k2: v for k2, v in E.items() if v}
    return D.get((1 << m) - 1, {})


def permanent_poly(n):
    nv = n * n
    out = {}
    for s in itertools.permutations(range(n)):
        e = [0] * nv
        for i in range(n):
            e[i * n + s[i]] = 1
        out[tuple(e)] = out.get(tuple(e), 0) + 1
    return out


def grenet(n):
    """Grenet's matrix for perm_n (rule 3): (2^n - 1) square, rows and columns the subsets other than {1..n}."""
    nv = n * n
    subsets = [frozenset(c) for r in range(n) for c in itertools.combinations(range(n), r)]
    index = {s: i for i, s in enumerate(subsets)}
    m = len(subsets)
    A = [[{} for _ in range(m)] for _ in range(m)]
    for s in subsets:
        i = index[s]
        if s:
            A[i][i] = const(1, nv)
        for j in range(n):
            if j in s:
                continue
            t = s | {j}
            col = index[frozenset()] if len(t) == n else index[t]
            A[i][col] = padd(A[i][col], var(len(s) * n + j, nv))
    return A, subsets


# ---------------------------------------------------------------- dimensions (rule 2 and beside a)

def monomial_dim(leading, nv):
    """The dimension of V of a monomial ideal: the largest set S of variables such that every generator involves a
    variable outside S."""
    for r in range(nv, -1, -1):
        for S in itertools.combinations(range(nv), r):
            Ss = set(S)
            if all(any(e and i not in Ss for i, e in enumerate(m)) for m in leading):
                return r
    return 0


def groebner_codim(polys, gens, modulus=None):
    import sympy
    kw = {"modulus": modulus} if modulus else {"domain": "QQ"}
    G = sympy.groebner(polys, *gens, order="grevlex", **kw)
    exprs = list(G.exprs)
    leading = [sympy.Poly(g, *gens).monoms(order="grevlex")[0] for g in exprs]
    dim = monomial_dim(leading, len(gens))
    digest = hashlib.sha256("\n".join(sorted(str(e) for e in exprs)).encode()).hexdigest()[:16]
    return len(gens) - dim, len(exprs), digest


def left_kernel(W):
    """A Z-basis of {c : c W = 0} and the rank of W, by unimodular row operations on [W | I]."""
    r = len(W)
    if r == 0:
        return [], 0
    s = len(W[0])
    M = [list(W[i]) + [1 if j == i else 0 for j in range(r)] for i in range(r)]
    row = 0
    for col in range(s):
        while True:
            nz = [i for i in range(row, r) if M[i][col]]
            if not nz:
                break
            p = min(nz, key=lambda i: abs(M[i][col]))
            M[row], M[p] = M[p], M[row]
            done = True
            for i in range(row + 1, r):
                if M[i][col]:
                    q = M[i][col] // M[row][col]
                    M[i] = [a - q * b for a, b in zip(M[i], M[row])]
                    if M[i][col]:
                        done = False
            if done:
                row += 1
                break
        if row == r:
            break
    return [M[i][s:] for i in range(row, r)], row


def torus_dim(binomials, nv):
    """dim over C of V of binomials x^u + c x^v (c = +1 or -1), by the torus decomposition (beside a)."""
    best, feasible = -1, 0
    for mask in range(1 << nv):
        S = [i for i in range(nv) if mask >> i & 1]
        rows, parity, ok = [], [], True
        for u, v, c in binomials:
            iu = all(mask >> i & 1 for i, e in enumerate(u) if e)
            iv = all(mask >> i & 1 for i, e in enumerate(v) if e)
            if iu != iv:
                ok = False
                break
            if iu:
                rows.append([u[i] - v[i] for i in S])
                parity.append(1 if c == 1 else 0)
        if not ok:
            continue
        kernel, rank = left_kernel(rows) if rows else ([], 0)
        if any(sum(k * e for k, e in zip(vec, parity)) % 2 for vec in kernel):
            continue
        feasible += 1
        best = max(best, len(S) - rank)
    return best, feasible


def partial_binomials(n, sign):
    """The partials of perm_n (sign +1) or det_n (sign -1, up to an overall sign) for n = 3, as binomials."""
    assert n == 3
    out = []
    for i in range(3):
        for j in range(3):
            r = [a for a in range(3) if a != i]
            c = [b for b in range(3) if b != j]
            u = [0] * 9
            v = [0] * 9
            u[r[0] * 3 + c[0]] += 1
            u[r[1] * 3 + c[1]] += 1
            v[r[0] * 3 + c[1]] += 1
            v[r[1] * 3 + c[0]] += 1
            out.append((tuple(u), tuple(v), sign))
    return out


# ---------------------------------------------------------------- exact integer determinants and permanents

def bareiss_det(A):
    M = [list(r) for r in A]
    n, sign, prev = len(M), 1, 1
    for k in range(n - 1):
        if M[k][k] == 0:
            sw = next((i for i in range(k + 1, n) if M[i][k]), None)
            if sw is None:
                return 0
            M[k], M[sw] = M[sw], M[k]
            sign = -sign
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                M[i][j] = (M[i][j] * M[k][k] - M[i][k] * M[k][j]) // prev
        prev = M[k][k]
    return sign * M[n - 1][n - 1]


def rank_exact(M):
    from fractions import Fraction
    A = [[Fraction(x) for x in row] for row in M]
    rank, cols = 0, len(A[0]) if A else 0
    for c in range(cols):
        piv = next((i for i in range(rank, len(A)) if A[i][c] != 0), None)
        if piv is None:
            continue
        A[rank], A[piv] = A[piv], A[rank]
        for i in range(len(A)):
            if i != rank and A[i][c] != 0:
                f = A[i][c] / A[rank][c]
                A[i] = [a - f * b for a, b in zip(A[i], A[rank])]
        rank += 1
    return rank


def perm_int(X):
    n = len(X)
    total = 0
    for s in itertools.permutations(range(n)):
        p = 1
        for i in range(n):
            p *= X[i][s[i]]
        total += p
    return total


def det_by_permutations(X):
    n = len(X)
    total = 0
    for s in itertools.permutations(range(n)):
        inv = sum(1 for a in range(n) for b in range(a + 1, n) if s[a] > s[b])
        p = 1
        for i in range(n):
            p *= X[i][s[i]]
        total += -p if inv % 2 else p
    return total


def evaluate(P, point):
    total = 0
    for e, c in P.items():
        t = c
        for x, k in zip(point, e):
            t *= x ** k
        total += t
    return total


class Stream:
    def __init__(self, seed, label):
        self.seed, self.label, self.n = seed, label, 0

    def ints(self, k, lo, hi):
        out = []
        while len(out) < k:
            h = hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
            self.n += 1
            for i in range(0, 32, 4):
                out.append(lo + int.from_bytes(h[i:i + 4], "big") % (hi - lo + 1))
        return out[:k]


# ---------------------------------------------------------------- run

def sympy_jacobian(n, kind):
    import sympy
    X = [[sympy.Symbol(f"x{i}{j}") for j in range(1, n + 1)] for i in range(1, n + 1)]
    gens = [v for row in X for v in row]
    if kind == "perm":
        f = sympy.Add(*[sympy.Mul(*[X[i][s[i]] for i in range(n)]) for s in itertools.permutations(range(n))])
    else:
        f = sympy.Matrix(X).det(method="berkowitz").expand()
    return [f] + [sympy.diff(f, v) for v in gens], gens


def families_hold(polys, gens):
    """Remark 1.5 and two more visible families of singular points, as identities of the partials."""
    import sympy
    X = [gens[0:3], gens[3:6], gens[6:9]]
    checks = {}
    for name, zero in (("one nonzero row", [X[1][j] for j in range(3)] + [X[2][j] for j in range(3)]),
                       ("one nonzero column", [X[i][1] for i in range(3)] + [X[i][2] for i in range(3)]),
                       ("two zero columns", [X[i][0] for i in range(3)] + [X[i][1] for i in range(3)])):
        sub = {v: 0 for v in zero}
        checks[name] = all(sympy.expand(p.subs(sub)) == 0 for p in polys)
    return checks


def cubic_check(cells):
    import sympy
    x, y, z, t = sympy.symbols("x y z t")
    names = {"x": x, "y": y, "z": z, "t": t, "0": 0, "1": 1}
    M = sympy.Matrix([[(-1 if neg else 1) * names[s] for neg, s in row] for row in cells])
    return sympy.expand(M.det(method="berkowitz") - (x * y ** 2 + y * t ** 2 + z ** 3)) == 0


def controls_run(seed):
    import sympy
    ctl = {}
    polys, gens = sympy_jacobian(3, "det")
    cq = groebner_codim(polys, gens)[0]
    c3 = groebner_codim(polys, gens, 3)[0]
    tdim, _ = torus_dim(partial_binomials(3, -1), 9)
    ctl["det_3's singular locus: codim 4 over Q and F_3 and by the torus method"] = (cq, c3, 9 - tdim) == (4, 4, 4)
    ok_mono = monomial_dim([(1, 1, 0, 0), (0, 0, 1, 0)], 4) == 2 and monomial_dim([(1, 0), (0, 1)], 2) == 0
    a_plus_b = ((1, 0), (0, 1), 1)
    ok_parity = (torus_dim([a_plus_b, ((2, 0), (0, 2), -1)], 2)[0] == 1 and
                 torus_dim([a_plus_b, ((2, 0), (0, 2), 1)], 2)[0] == 0)
    ctl["a monomial ideal's dimension and the torus parity rule"] = ok_mono and ok_parity
    st = Stream(seed, "abv/controls")
    good = True
    for n in (2, 3, 4, 5):
        for _ in range(3):
            vals = st.ints(n * n, -5, 5)
            X = [vals[i * n:(i + 1) * n] for i in range(n)]
            P = poly_det([[const(X[i][j], 1) for j in range(n)] for i in range(n)], 1)
            good &= evaluate(P, (0,)) == det_by_permutations(X) == bareiss_det(X)
    ctl["the polynomial determinant against the sum over permutations"] = good
    A, subsets = grenet(3)
    i = subsets.index(frozenset())
    j = subsets.index(frozenset({0}))
    A[i][j] = var(1, 9)
    ctl["a planted fault in Grenet's matrix changes its determinant"] = poly_det(A, 9) != permanent_poly(3)
    return ctl


def run(seed, inputs="inputs", results="results"):
    import sympy
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    tex = tex_of(read_input(inputs))
    statements = statements_found(tex)
    cells = cubic_matrix(tex)

    ctl = controls_run(seed)
    if not all(ctl.values()):
        raise AssertionError(f"a control failed: {[c for c, ok in ctl.items() if not ok]}")

    polys, gens = sympy_jacobian(3, "perm")
    codim, sizes, digests = {}, {}, {}
    for p in (None,) + PRIMES:
        key = "Q" if p is None else f"F_{p}"
        codim[key], sizes[key], digests[key] = groebner_codim(polys, gens, p)
    c2, n2, d2 = groebner_codim(polys, gens, 2)

    A, subsets = grenet(3)
    entries_ok = len(A) == 7 and all(
        not e or e == const(1, 9) or (len(e) == 1 and list(e.values())[0] == 1 and sum(list(e.keys())[0]) == 1)
        for row in A for e in row)
    det3 = poly_det(A, 9)
    perm3 = permanent_poly(3)
    grenet_ok = entries_ok and det3 == perm3

    cond = {f"codim Sing(perm_3) = 6 over {k}": codim[k] == 6 for k in ("Q", "F_3", "F_5", "F_7")}
    cond["Grenet's 7 x 7 matrix: entries 0, 1 or a variable, determinant perm_3"] = grenet_ok

    tdim, feasible = torus_dim(partial_binomials(3, 1), 9)
    fam = families_hold(polys[1:], gens)
    L0 = [[evaluate(e, (0,) * 9) if e else 0 for e in row] for row in A]
    rank0 = rank_exact(L0)
    st = Stream(seed, "abv/grenet")
    others = {}
    for n in OTHER_N:
        B, _ = grenet(n)
        hits = 0
        for _ in range(POINTS):
            vals = st.ints(n * n, -4, 4)
            X = [vals[i * n:(i + 1) * n] for i in range(n)]
            num = [[evaluate(e, vals) if e else 0 for e in row] for row in B]
            hits += bareiss_det(num) == (-1) ** (n - 1) * perm_int(X)
        others[n] = {"size": len(B), "points": POINTS, "agree": hits}
    cubic_ok = cubic_check(cells)

    values = {
        "statements": f"{statements} of {len(REQUIRED)} statements found once each, and Theorem 1.8's 5 x 5 matrix",
        "codim_q": codim["Q"], "codim_f3": codim["F_3"], "codim_f5": codim["F_5"], "codim_f7": codim["F_7"],
        "bases": ("reduced Groebner bases: " + ", ".join(f"{k} {sizes[k]} ({digests[k]})" for k in sizes)
                  + f"; F_2 {n2} ({d2})"),
        "grenet": (f"{len(A)} x {len(A)}, {sum(1 for row in A for e in row if e)} nonzero entries, "
                   f"{'all 0, 1 or a variable' if entries_ok else 'not all 0, 1 or a variable'}; determinant "
                   f"{len(det3)} terms, {'identical to' if det3 == perm3 else 'not'} perm_3"),
        "torus": f"over C by the torus decomposition: codim {9 - tdim}, {feasible} feasible supports of 512",
        "char2": f"over F_2, where perm_3 = det_3: codim {c2}",
        "families": "; ".join(f"{k}: {'singular' if v else 'not all singular'}" for k, v in fam.items()),
        "prop21": f"rank of Grenet's constant part {rank0} (m - 1 = {len(A) - 1})",
        "grenet_other": "; ".join(f"n = {n}: size {o['size']}, (-1)^(n-1) perm_n at {o['agree']} of {o['points']} "
                                  f"points" for n, o in others.items()),
        "cubic": f"Theorem 1.8's 5 x 5 determinant {'equals' if cubic_ok else 'differs from'} xy^2 + yt^2 + z^3",
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"input": {"name": INPUT[0], "sha256": INPUT[1]}, "conditions": cond, "controls": ctl,
              "codim": codim, "basis_sizes": sizes, "basis_digests": digests, "char2": [c2, n2, d2],
              "torus": [tdim, feasible], "families": fam, "constant_part_rank": rank0, "others": others,
              "cubic": cubic_ok, "det3_terms": len(det3), "test": TEST, "sympy": sympy.__version__}
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
        sys.exit(f"abv: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
