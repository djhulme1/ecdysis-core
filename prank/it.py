#!/usr/bin/env python3
"""Ilten & Teitler's product ranks of the 3 x 3 determinant and permanent: pr(Det3) = 5 and pr(Perm3) = 4, and so
tr(Det3) = 5 and tr(Perm3) = 4.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:bd8023834bf6d740) is from Ilten and
Teitler, "Product Ranks of the 3 x 3 Determinant and Permanent" (Canadian Mathematical Bulletin 59(2), 311-319, 2016;
arXiv:1503.00822v2): "We show that the product rank of the 3x3 determinant is 5, and the product rank of the 3x3
permanent is 4. As a corollary, we obtain that the tensor ranks of the 3 x 3 determinant and permanent are 5 and 4,
respectively."

Its test, as registered on 14 October: refuted if the identities the paper's source prints (Glynn's, Perm3 as a sum
of 4 products of linear forms; Derksen's, Det3 as half a sum of 5) do not expand exactly to the 3 x 3 permanent and
determinant, each factor a linear form in one row's variables, so that pr and tr <= 4 and <= 5 fail; or if the Koszul
flattening T_A^1 (A (x) B* -> L2(A) (x) C) of the tensors in C3 (x) C3 (x) C3 they define has rank below 9 for Det3 or
below 7 for Perm3, so that border rank, hence tensor rank, is not certified >= 5 and >= 4.

The correction asked of its person, before any evidence (the archive does not sign a managed agent's claim.amend):
"expand exactly to nonzero rational multiples of the 3 x 3 permanent and determinant ... (a scalar, which a factor
absorbs, is reported)", because the paper prints Glynn's identity without Glynn's factor 1/2^(n-1), and a nonzero
scalar changes neither a product rank nor a tensor rank. SCALAR says which test this file applies: True, the
corrected one; False, the one registered. It is fixed in the commit that runs, before the run.

Standard library only. The input is the claim's data of record, arXiv's source of the paper's v2 (a gzipped tar of
its TeX and bibliography), checked against its SHA-256 and size and opened in memory; its TeX is read as text and
nothing in it is run. Every rule below was fixed before either identity was expanded.

1. Reading. The member pr.tex, as UTF-8. Its split environments (\\begin{split} ... \\end{split}); in each, the
   alignment marks (&), the line breaks (\\\\), the sizing commands \\Big, \\big, \\left and \\right and a final full
   stop are dropped, and the left side of its one "=" names it. Exactly one must name \\Perm_3 and exactly one
   \\Det_3. A right side is a coefficient \\frac{p}{q} before a parenthesised sum, or a sum; a sum is terms joined by +
   and -; a term is an optional integer and one or more factors; a factor is a variable x_{ij} (i, j from 1 to 3) or a
   parenthesised sum of variables, each with a sign and an optional integer. Anything else refuses the run, as a
   reading error.
2. Expansion. Each right side is multiplied out exactly over the rationals and compared, monomial by monomial, with
   Perm3 and Det3 by Leibniz's formula (the sum over the six permutations, with signs for Det3). The multiple c is the
   one rational with expansion = c x target, if there is one.
3. The test's four conditions. Glynn's right side has 4 terms, Derksen's 5, every term three factors, each factor's
   variables in one row and the three factors in the three rows (so each term is a simple tensor, and the identity a
   tensor decomposition); and each expands to c x Perm3 and c x Det3 with c = 1 (SCALAR False) or c != 0 (SCALAR
   True). The tensor of a cubic multihomogeneous in the rows has T[j1][j2][j3] = the coefficient of x_{1 j1} x_{2 j2}
   x_{3 j3}, with A, B and C the variables of rows 1, 2 and 3 (the paper's identification). Its Koszul flattening
   T_A^1 sends a_s (x) b_j* to the sum over i and k of T[i][j][k] (a_s ^ a_i) (x) c_k, a 9 x 9 rational matrix in the
   bases a_s (x) b_j* and (a_p ^ a_q) (x) c_k, p < q; its rank is found by exact elimination over the rationals. Its
   rank must be 9 for Det3 and at least 7 for Perm3, so that border rank is at least ceil(9/2) = 5 and ceil(7/2) = 4
   (Landsberg and Ottaviani: border rank >= rank T_A^p / C(a - 1, p), here a = 3 and p = 1), and tensor rank, which
   is at least border rank, with it. test_passed is 1 if all four hold.
4. Beside the test, none of it counted: the multiples c; the Koszul ranks with B or C distinguished; Strassen's
   commutator for Perm3, at seed-drawn slice combinations T(alpha), T(beta), T(gamma) (alpha, beta, gamma
   independent, T(alpha) invertible), the rank of [T(beta) T(alpha)^-1, T(gamma) T(alpha)^-1] and its bound
   3 + rank/2, and for Det3 how many of 20 seed-drawn combinations are invertible; Glynn's general formula as the
   paper prints it (the sum over epsilon in {+1, -1}^n with epsilon_1 = 1 of the product over i of the sum over j of
   epsilon_i epsilon_j x_ij) and Ryser's (the sum over S of (-1)^(n - |S|) times the product over i of the sum over j
   in S of x_ij), expanded for n = 2 to 5, as multiples of Perm_n, with their numbers of terms; the paper's
   polarization identity, l1...ld = 1/(2^(d-1) d!) times the sum over epsilon with epsilon_1 = 1 of
   (prod epsilon_i)(sum epsilon_i l_i)^d, with the l_i independent variables, for d = 2 to 5; and the paper's
   statements of the four bounds and of the tensor form of Derksen's identity, present in its text.

Controls (controls_passed counts those that behave as stated): on 20 seed-drawn perturbations of the two printed
identities (one variable's sign flipped in one factor, or the variable moved to another column of its row), the
expansion finds no multiple of the target, and an evaluation at six seed-drawn integer matrices agrees, on every one;
at ten seed-drawn integer matrices, each right side evaluated from its factors is c times the target by Leibniz, and
Leibniz agrees with the cofactor expansion (Det3) and Ryser's formula (Perm3); the Koszul flattening of tensors built
from r seed-drawn rank-one terms (r = 1 to 5, two each) has rank at most 2r, of the unit tensor rank 6, and of a
seed-drawn tensor rank 9; on ten seed-drawn tensors with an invertible slice (four of rank at most 3, three of rank at
most 4, three drawn whole), the Koszul rank is 6 plus the rank of Strassen's commutator, two computations of one
invariant; and each identity read as a tensor decomposition, the sum of c u (x) v (x) w over its terms, is the same
multiple of the tensor of Perm3 or Det3.

What it cannot check: the paper's lower bounds on product rank (pr(Perm3) >= 4, pr(Det3) >= 5, and bpr(Perm_n) > n),
proved through Fano schemes of linear spaces in the two hypersurfaces and, for Det3, a computation of minimal primes in
Macaulay2; and the Waring-rank bounds it cites.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 prank/it.py
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

INPUT = ("arXiv-1503.00822v2.tar.gz", "169b1d968f9c5638c7e47e7bdaeeda1f9ff7e75a30007b2d5ceebdd0e5e76a18", 10385)
MEMBER = "pr.tex"
SCALAR = True
TERMS = {"Perm3": 4, "Det3": 5}
NAMES = {"\\Perm_3": "Perm3", "\\Det_3": "Det3"}
KOSZUL_MIN = {"Det3": 9, "Perm3": 7}
STATEMENTS = (
    "Glynn and Derksen identities above show $\\pr(\\Perm_3) \\leq 4$ and $\\pr(\\Det_3) \\leq 5$",
    "So $\\tr(\\Perm_3) \\leq 4$ and $\\tr(\\Det_3) \\leq 5$.",
    "We have $\\tr(\\Det_3) = \\pr(\\Det_3) = 5$.",
    "\\tr(\\Perm_3)=\\pr (\\Perm_3)=\\bpr(\\Perm_3)=4",
    "In fact, Derksen gave his identity originally in tensor form.",
)
PERTURBATIONS = 20
OUTPUTS = ("test_version", "statements", "glynn", "glynn_multiple", "derksen", "derksen_multiple", "koszul_det3",
           "koszul_perm3", "border_rank", "koszul_factors", "strassen", "general_identities", "polarization",
           "conditions_met", "conditions_total", "test_passed", "controls_passed", "controls_total")
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
    return {s: flat.count(s) >= 1 for s in STATEMENTS}


def normalise(block):
    s = block.replace("\\\\", " ")
    for cmd in ("\\Big", "\\big", "\\left", "\\right"):
        s = s.replace(cmd, " ")
    s = s.replace("&", " ").strip()
    if s.endswith("."):
        s = s[:-1].rstrip()
    return s


def blocks(tex):
    """The split environments that name Perm3 and Det3: {name: right side}."""
    found = {}
    for m in re.finditer(r"\\begin\{split\}(.*?)\\end\{split\}", tex, re.S):
        s = normalise(m.group(1))
        parts = s.split("=")
        if len(parts) != 2:
            raise Refused(f"a split environment with {len(parts) - 1} signs '=': {s[:60]!r}")
        left = parts[0].strip()
        if left not in NAMES:
            continue
        name = NAMES[left]
        if name in found:
            raise Refused(f"{left} is named by more than one split environment")
        found[name] = parts[1].strip()
    for left, name in NAMES.items():
        if name not in found:
            raise Refused(f"no split environment names {left}")
    return found


TOKEN = re.compile(r"\s*(?:(x_\{([1-3])([1-3])\})|(\d+)|([()+\-]))")


def tokens(s):
    out, pos = [], 0
    s = s.rstrip()
    while pos < len(s):
        m = TOKEN.match(s, pos)
        if not m or m.end() == pos:
            raise Refused(f"cannot read {s[pos:pos + 30]!r}")
        if m.group(1):
            out.append(("var", (int(m.group(2)) - 1, int(m.group(3)) - 1)))
        elif m.group(4):
            out.append(("int", int(m.group(4))))
        else:
            out.append((m.group(5), None))
        pos = m.end()
    return out


class Parser:
    def __init__(self, toks):
        self.t, self.p = toks, 0

    def peek(self):
        return self.t[self.p][0] if self.p < len(self.t) else "end"

    def take(self, kind):
        if self.peek() != kind:
            raise Refused(f"expected {kind}, found {self.peek()} at token {self.p}")
        tok = self.t[self.p]
        self.p += 1
        return tok[1]

    def linear(self):
        form, sign = {}, 1
        if self.peek() in ("+", "-"):
            sign = -1 if self.peek() == "-" else 1
            self.p += 1
        while True:
            k = self.take("int") if self.peek() == "int" else 1
            v = self.take("var")
            if v in form:
                raise Refused(f"x_{v[0] + 1}{v[1] + 1} twice in one factor")
            form[v] = sign * k
            if self.peek() in ("+", "-"):
                sign = -1 if self.peek() == "-" else 1
                self.p += 1
                continue
            return form

    def factor(self):
        if self.peek() == "var":
            return {self.take("var"): 1}
        self.take("(")
        form = self.linear()
        self.take(")")
        return form

    def term(self, sign):
        k = self.take("int") if self.peek() == "int" else 1
        factors = []
        while self.peek() in ("var", "("):
            factors.append(self.factor())
        if not factors:
            raise Refused(f"a term with no factor at token {self.p}")
        return (Fraction(sign * k), factors)

    def sum(self, stop):
        terms, sign = [], 1
        if self.peek() in ("+", "-"):
            sign = -1 if self.peek() == "-" else 1
            self.p += 1
        while True:
            terms.append(self.term(sign))
            if self.peek() in ("+", "-"):
                sign = -1 if self.peek() == "-" else 1
                self.p += 1
                continue
            if self.peek() == stop:
                return terms
            raise Refused(f"expected + or - or {stop}, found {self.peek()} at token {self.p}")


def parse(right):
    """A right side as [(coefficient, [factor, ...])], each factor {(row, column): integer}."""
    m = re.fullmatch(r"\s*\\frac\{(\d+)\}\{(\d+)\}\s*\((.*)\)\s*", right, re.S)
    if m:
        outer, inner = Fraction(int(m.group(1)), int(m.group(2))), m.group(3)
    else:
        outer, inner = Fraction(1), right
    p = Parser(tokens(inner))
    terms = p.sum("end")
    return [(outer * c, fs) for c, fs in terms]


# ---------------------------------------------------------------- polynomials

def var_index(v, n=3):
    return v[0] * n + v[1]


def mul_linear(poly, form, n=3):
    out = {}
    for mono, c in poly.items():
        for v, a in form.items():
            key = tuple(sorted(mono + (var_index(v, n),)))
            out[key] = out.get(key, 0) + c * a
    return {k: c for k, c in out.items() if c != 0}


def add_into(acc, poly, scale=1):
    for k, c in poly.items():
        acc[k] = acc.get(k, 0) + scale * c
        if acc[k] == 0:
            del acc[k]


def expand(terms, n=3):
    total = {}
    for c, factors in terms:
        p = {(): Fraction(c)}
        for f in factors:
            p = mul_linear(p, f, n)
        add_into(total, p)
    return total


def sign_of(perm):
    s, seen = 1, list(perm)
    for i in range(len(seen)):
        while seen[i] != i:
            j = seen[i]
            seen[i], seen[j] = seen[j], seen[i]
            s = -s
    return s


def leibniz(n, signed):
    poly = {}
    for perm in itertools.permutations(range(n)):
        key = tuple(sorted(i * n + perm[i] for i in range(n)))
        poly[key] = poly.get(key, 0) + (sign_of(perm) if signed else 1)
    return poly


TARGET = {"Perm3": leibniz(3, False), "Det3": leibniz(3, True)}


def multiple(poly, target):
    """The rational c with poly = c x target (c may be 0 only if poly is 0), or None."""
    if any(k not in target for k in poly):
        return None
    ref = next(iter(target))
    c = Fraction(poly.get(ref, 0)) / target[ref]
    if all(Fraction(poly.get(k, 0)) == c * t for k, t in target.items()):
        return c
    return None


def mismatches(poly, target):
    keys = set(poly) | set(target)
    return sum(1 for k in keys if Fraction(poly.get(k, 0)) != target.get(k, 0))


def rows_ok(terms):
    """Every term three factors, each in one row's variables, the three rows covered once."""
    for _, factors in terms:
        if len(factors) != 3:
            return False
        rows = []
        for f in factors:
            rs = {v[0] for v in f}
            if len(rs) != 1:
                return False
            rows.append(rs.pop())
        if sorted(rows) != [0, 1, 2]:
            return False
    return True


# ---------------------------------------------------------------- tensors and flattenings

def tensor_of(poly):
    """T[j1][j2][j3]: the coefficient of x_{1 j1} x_{2 j2} x_{3 j3} (indices 0..8 as 3 i + j)."""
    T = [[[Fraction(0)] * 3 for _ in range(3)] for _ in range(3)]
    for key, c in poly.items():
        rows = sorted(key)
        if [k // 3 for k in rows] != [0, 1, 2]:
            raise ValueError("not multihomogeneous in the rows")
        T[rows[0] % 3][rows[1] % 3][rows[2] % 3] += c
    return T


def tensor_of_terms(terms):
    T = [[[Fraction(0)] * 3 for _ in range(3)] for _ in range(3)]
    for c, factors in terms:
        by_row = {next(iter(f))[0]: f for f in factors}
        u, v, w = ([Fraction(by_row[r].get((r, j), 0)) for j in range(3)] for r in range(3))
        for a, b, d in itertools.product(range(3), repeat=3):
            T[a][b][d] += c * u[a] * v[b] * w[d]
    return T


def permute(T, axis):
    """The tensor with factor `axis` first and the other two in order."""
    if axis == 0:
        return T
    out = [[[Fraction(0)] * 3 for _ in range(3)] for _ in range(3)]
    for i, j, k in itertools.product(range(3), repeat=3):
        idx = (i, j, k)
        rest = [idx[t] for t in range(3) if t != axis]
        out[idx[axis]][rest[0]][rest[1]] = T[i][j][k]
    return out


PAIRS = ((0, 1), (0, 2), (1, 2))


def koszul(T):
    """T_A^1: A (x) B* -> L2(A) (x) C as a 9 x 9 matrix (rows (pq, k), columns (s, j))."""
    M = [[Fraction(0)] * 9 for _ in range(9)]
    for s, j in itertools.product(range(3), repeat=2):
        col = 3 * s + j
        for i in range(3):
            if i == s:
                continue
            pq = PAIRS.index((min(s, i), max(s, i)))
            sgn = 1 if s < i else -1
            for k in range(3):
                if T[i][j][k]:
                    M[3 * pq + k][col] += sgn * T[i][j][k]
    return M


def rank(M):
    A = [[Fraction(x) for x in row] for row in M]
    r, cols = 0, len(A[0]) if A else 0
    for c in range(cols):
        piv = next((i for i in range(r, len(A)) if A[i][c] != 0), None)
        if piv is None:
            continue
        A[r], A[piv] = A[piv], A[r]
        for i in range(len(A)):
            if i != r and A[i][c] != 0:
                f = A[i][c] / A[r][c]
                A[i] = [x - f * y for x, y in zip(A[i], A[r])]
        r += 1
    return r


def det(M):
    A = [[Fraction(x) for x in row] for row in M]
    n, d = len(A), Fraction(1)
    for c in range(n):
        piv = next((i for i in range(c, n) if A[i][c] != 0), None)
        if piv is None:
            return Fraction(0)
        if piv != c:
            A[c], A[piv] = A[piv], A[c]
            d = -d
        d *= A[c][c]
        for i in range(c + 1, n):
            f = A[i][c] / A[c][c]
            A[i] = [x - f * y for x, y in zip(A[i], A[c])]
    return d


def inverse(M):
    n = len(M)
    A = [[Fraction(x) for x in row] + [Fraction(int(i == j)) for j in range(n)] for i, row in enumerate(M)]
    for c in range(n):
        piv = next((i for i in range(c, n) if A[i][c] != 0), None)
        if piv is None:
            raise ZeroDivisionError("singular")
        A[c], A[piv] = A[piv], A[c]
        p = A[c][c]
        A[c] = [x / p for x in A[c]]
        for i in range(n):
            if i != c and A[i][c] != 0:
                f = A[i][c]
                A[i] = [x - f * y for x, y in zip(A[i], A[c])]
    return [row[n:] for row in A]


def matmul(X, Y):
    return [[sum(X[i][t] * Y[t][j] for t in range(len(Y))) for j in range(len(Y[0]))] for i in range(len(X))]


def slice_at(T, alpha):
    return [[sum(alpha[i] * T[i][j][k] for i in range(3)) for k in range(3)] for j in range(3)]


def commutator_rank(T, alpha, beta, gamma):
    inv = inverse(slice_at(T, alpha))
    X, Y = matmul(slice_at(T, beta), inv), matmul(slice_at(T, gamma), inv)
    XY, YX = matmul(X, Y), matmul(Y, X)
    return rank([[a - b for a, b in zip(r1, r2)] for r1, r2 in zip(XY, YX)])


# ---------------------------------------------------------------- the paper's general identities

def glynn_printed(n):
    terms = []
    for rest in itertools.product((1, -1), repeat=n - 1):
        eps = (1,) + rest
        factors = [{(i, j): eps[i] * eps[j] for j in range(n)} for i in range(n)]
        terms.append((Fraction(1), factors))
    return terms


def ryser(n):
    terms = []
    for size in range(1, n + 1):
        for S in itertools.combinations(range(n), size):
            factors = [{(i, j): 1 for j in S} for i in range(n)]
            terms.append((Fraction((-1) ** (n - size)), factors))
    return terms


def polarization(d):
    """1/(2^(d-1) d!) sum over epsilon (epsilon_1 = 1) of (prod epsilon)(sum epsilon_i y_i)^d, y_i as x_{0 i}."""
    scale = Fraction(1, 2 ** (d - 1) * math.factorial(d))
    terms = []
    for rest in itertools.product((1, -1), repeat=d - 1):
        eps = (1,) + rest
        form = {(0, i): eps[i] for i in range(d)}
        terms.append((scale * math.prod(eps), [form] * d))
    return terms


# ---------------------------------------------------------------- seeded draws

class Stream:
    def __init__(self, seed, label):
        self.seed, self.label, self.n = seed, label, 0

    def below(self, m):
        self.n += 1
        h = hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
        return int.from_bytes(h[:8], "big") % m

    def between(self, lo, hi):
        return lo + self.below(hi - lo + 1)


def evaluate(terms, X):
    total = Fraction(0)
    for c, factors in terms:
        v = Fraction(c)
        for f in factors:
            v *= sum(a * X[r][j] for (r, j), a in f.items())
        total += v
    return total


def eval_poly(poly, X, n=3):
    total = Fraction(0)
    for key, c in poly.items():
        v = Fraction(c)
        for k in key:
            v *= X[k // n][k % n]
        total += v
    return total


def cofactor_det(X):
    a, b, c = X[0]
    d, e, f = X[1]
    g, h, i = X[2]
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def ryser_value(X):
    n, total = len(X), 0
    for size in range(1, n + 1):
        for S in itertools.combinations(range(n), size):
            total += (-1) ** (n - size) * math.prod(sum(X[i][j] for j in S) for i in range(n))
    return total


def matrix(st, lo=-9, hi=9):
    return [[st.between(lo, hi) for _ in range(3)] for _ in range(3)]


def eval_multiple(terms, target, points):
    """By evaluation: the consistent nonzero ratio of the right side to the target at the points, or None."""
    ratio = None
    for X in points:
        lhs, rhs = evaluate(terms, X), eval_poly(target, X)
        if rhs == 0:
            if lhs != 0:
                return None
            continue
        r = lhs / rhs
        if ratio is None:
            ratio = r
        elif r != ratio:
            return None
    return ratio if ratio else None


def perturb(terms, st):
    """One variable's sign flipped in one factor, or the variable moved to another column of its row."""
    out = [(c, [dict(f) for f in fs]) for c, fs in terms]
    t = st.below(len(out))
    f = st.below(len(out[t][1]))
    form = out[t][1][f]
    v = sorted(form)[st.below(len(form))]
    if st.below(2) == 0:
        form[v] = -form[v]
        what = f"term {t + 1}, factor {f + 1}: the sign of x_{v[0] + 1}{v[1] + 1} flipped"
    else:
        cols = [j for j in range(3) if j != v[1]]
        w = (v[0], cols[st.below(2)])
        a = form.pop(v)
        form[w] = form.get(w, 0) + a
        if form[w] == 0:
            del form[w]
        if not form:
            form[v] = a
        what = f"term {t + 1}, factor {f + 1}: x_{v[0] + 1}{v[1] + 1} moved to x_{w[0] + 1}{w[1] + 1}"
    return out, what


def rank_one_sum(st, r):
    T = [[[Fraction(0)] * 3 for _ in range(3)] for _ in range(3)]
    for _ in range(r):
        u, v, w = ([st.between(-3, 3) for _ in range(3)] for _ in range(3))
        for i, j, k in itertools.product(range(3), repeat=3):
            T[i][j][k] += u[i] * v[j] * w[k]
    return T


def drawn_tensor(st, lo=-9, hi=9):
    return [[[Fraction(st.between(lo, hi)) for _ in range(3)] for _ in range(3)] for _ in range(3)]


def invertible_frame(T, st, tries=200):
    """Seed-drawn alpha, beta, gamma, independent, with T(alpha) invertible; None if none is found."""
    for _ in range(tries):
        a, b, g = ([st.between(-5, 5) for _ in range(3)] for _ in range(3))
        if det([a, b, g]) != 0 and det(slice_at(T, a)) != 0:
            return a, b, g
    return None


# ---------------------------------------------------------------- the run

def accepted(c):
    return c is not None and (c != 0 if SCALAR else c == 1)


def conditions(found):
    g, d = found["Perm3"], found["Det3"]
    return {
        "Glynn's identity as printed: 4 simple tensors expanding to Perm3" + (" times c != 0" if SCALAR else ""):
            g["terms"] == TERMS["Perm3"] and g["rows_ok"] and accepted(g["multiple"]),
        "Derksen's identity as printed: 5 simple tensors expanding to Det3" + (" times c != 0" if SCALAR else ""):
            d["terms"] == TERMS["Det3"] and d["rows_ok"] and accepted(d["multiple"]),
        "the Koszul flattening of Det3's tensor has rank 9": found["koszul"]["Det3"][0] >= KOSZUL_MIN["Det3"],
        "the Koszul flattening of Perm3's tensor has rank at least 7":
            found["koszul"]["Perm3"][0] >= KOSZUL_MIN["Perm3"],
    }


def frac(c):
    if c is None:
        return "none"
    return str(c.numerator) if c.denominator == 1 else f"{c.numerator}/{c.denominator}"


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    data = read_input(inputs)
    tex = tex_of(data)
    stmts = statements_found(tex)
    rights = blocks(tex)
    parsed = {name: parse(rights[name]) for name in ("Perm3", "Det3")}

    found = {}
    for name, terms in parsed.items():
        poly = expand(terms)
        c = multiple(poly, TARGET[name])
        found[name] = {"terms": len(terms), "factors": [len(fs) for _, fs in terms], "rows_ok": rows_ok(terms),
                       "multiple": c, "monomials": len(poly), "mismatches_exact": mismatches(poly, TARGET[name]),
                       "coefficients": [frac(c_) for c_, _ in terms]}
    tensors = {name: tensor_of(TARGET[name]) for name in ("Perm3", "Det3")}
    found["koszul"] = {name: [rank(koszul(permute(T, ax))) for ax in range(3)] for name, T in tensors.items()}
    cond = conditions(found)

    # beside: Strassen's commutator
    st = Stream(seed, "it/strassen")
    frame = invertible_frame(tensors["Perm3"], st)
    perm_comm = commutator_rank(tensors["Perm3"], *frame) if frame else None
    det_invertible = sum(1 for _ in range(20)
                         if det(slice_at(tensors["Det3"], [st.between(-5, 5) for _ in range(3)])) != 0)
    # beside: the general identities and polarization
    general = {}
    for n in range(2, 6):
        target = leibniz(n, False)
        g = multiple(expand(glynn_printed(n), n), target)
        r = multiple(expand(ryser(n), n), target)
        general[n] = {"glynn_printed": frac(g), "glynn_terms": len(glynn_printed(n)), "ryser": frac(r),
                      "ryser_terms": len(ryser(n))}
    polar = {}
    for d in range(2, 6):
        poly = expand(polarization(d), d)
        mono = {tuple(range(d)): 1}
        polar[d] = {"multiple": frac(multiple(poly, mono)), "terms": len(polarization(d))}

    # controls
    ctl, ctl_detail = {}, {}
    st = Stream(seed, "it/perturb")
    points = [matrix(st) for _ in range(6)]
    rows, ok = [], 0
    for j in range(PERTURBATIONS):
        name = ("Perm3", "Det3")[j % 2]
        terms, what = perturb(parsed[name], st)
        by_expansion = multiple(expand(terms), TARGET[name])
        by_eval = eval_multiple(terms, TARGET[name], points)
        caught = by_expansion is None or by_expansion == 0
        agree = (by_expansion is None or by_expansion == 0) == (by_eval is None)
        ok += int(caught and agree)
        rows.append({"identity": name, "change": what, "expansion": frac(by_expansion), "evaluation": frac(by_eval)})
    ctl["20 seed-drawn perturbations of the identities: each caught, expansion and evaluation agreeing"] = (
        ok == PERTURBATIONS)
    ctl_detail["perturbations"] = rows
    st = Stream(seed, "it/evaluate")
    good = True
    for _ in range(10):
        X = matrix(st)
        p_val, d_val = eval_poly(TARGET["Perm3"], X), eval_poly(TARGET["Det3"], X)
        for name, val in (("Perm3", p_val), ("Det3", d_val)):
            c = found[name]["multiple"]
            if c is not None and evaluate(parsed[name], X) != c * val:
                good = False
        if d_val != cofactor_det(X) or p_val != ryser_value(X):
            good = False
    ctl["at 10 seed-drawn matrices: the right sides are c times Leibniz's values, Leibniz = cofactors and Ryser"] = good
    st = Stream(seed, "it/koszul")
    sound = []
    for r in range(1, 6):
        for _ in range(2):
            sound.append((r, rank(koszul(rank_one_sum(st, r)))))
    unit = [[[Fraction(int(i == j == k)) for k in range(3)] for j in range(3)] for i in range(3)]
    unit_rank = rank(koszul(unit))
    generic_rank = rank(koszul(drawn_tensor(st)))
    ctl["Koszul ranks: at most 2r for r rank-one terms, 6 for the unit tensor, 9 for a drawn tensor"] = (
        all(kr <= 2 * r for r, kr in sound) and unit_rank == 6 and generic_rank == 9)
    ctl_detail["koszul_soundness"] = {"rank_one_sums": sound, "unit": unit_rank, "drawn": generic_rank}
    st = Stream(seed, "it/consistency")
    pairs, consistent = [], True
    for kind in [3] * 4 + [4] * 3 + [None] * 3:
        for _ in range(50):
            T = rank_one_sum(st, kind) if kind else drawn_tensor(st, -3, 3)
            fr = invertible_frame(T, st, tries=50)
            if fr:
                break
        if not fr:
            consistent = False
            pairs.append({"kind": kind, "frame": None})
            continue
        kr, cr = rank(koszul(T)), commutator_rank(T, *fr)
        consistent = consistent and kr == 6 + cr
        pairs.append({"kind": kind, "koszul": kr, "commutator": cr})
    ctl["on 10 seed-drawn tensors with an invertible slice: Koszul rank = 6 + Strassen's commutator rank"] = consistent
    ctl_detail["consistency"] = pairs
    tensor_ok = True
    for name in ("Perm3", "Det3"):
        c = found[name]["multiple"]
        if c is None or not found[name]["rows_ok"]:
            tensor_ok = False
            continue
        TT, T0 = tensor_of_terms(parsed[name]), tensors[name]
        if any(TT[i][j][k] != c * T0[i][j][k] for i, j, k in itertools.product(range(3), repeat=3)):
            tensor_ok = False
    ctl["each identity as a tensor decomposition is the same multiple of the tensor of Perm3 or Det3"] = tensor_ok

    g, d, kz = found["Perm3"], found["Det3"], found["koszul"]
    bd, bp = math.ceil(kz["Det3"][0] / 2), math.ceil(kz["Perm3"][0] / 2)
    strassen_bound = math.ceil(Fraction(6 + perm_comm, 2)) if perm_comm is not None else "none"

    def described(f, name):
        c = f["multiple"]
        shape = (f"{f['terms']} terms of {'/'.join(str(x) for x in sorted(set(f['factors'])))} factors, "
                 f"{'each in one row' if f['rows_ok'] else 'not one per row'}")
        if c is None:
            return f"{shape}; not a multiple of {name}: {f['mismatches_exact']} of its monomials differ"
        exact = "" if c == 1 else f" (against {name} itself, {f['mismatches_exact']} monomials differ)"
        return f"{shape}; expands to {frac(c)} x {name}{exact}"

    values = {
        "test_version": "as corrected: a nonzero scalar allowed and reported" if SCALAR else "as registered: exact",
        "statements": (f"the bounds and Derksen's tensor form, stated in the paper: {sum(stmts.values())} of "
                       f"{len(stmts)}"),
        "glynn": described(g, "Perm3"),
        "glynn_multiple": float(g["multiple"]) if g["multiple"] is not None else 0,
        "derksen": described(d, "Det3"),
        "derksen_multiple": float(d["multiple"]) if d["multiple"] is not None else 0,
        "koszul_det3": kz["Det3"][0],
        "koszul_perm3": kz["Perm3"][0],
        "border_rank": (f"border rank >= {bd} (Det3) and >= {bp} (Perm3) by T_A^1; tensor rank and product rank are at "
                        f"most {d['terms']} and {g['terms']} by the identities"),
        "koszul_factors": (f"T^1 with A, B, C distinguished: Det3 {'/'.join(map(str, kz['Det3']))}, Perm3 "
                           f"{'/'.join(map(str, kz['Perm3']))}"),
        "strassen": (f"Perm3: commutator rank {perm_comm} at seed-drawn slices, bound {strassen_bound}; "
                     f"Det3: {det_invertible} of 20 drawn slice combinations invertible"),
        "general_identities": ("as printed for n = 2..5, Glynn's gives " + ", ".join(general[n]["glynn_printed"]
                               for n in range(2, 6)) + " x Perm_n, Ryser's " + ", ".join(general[n]["ryser"]
                               for n in range(2, 6)) + "; terms " + ", ".join(str(general[n]["glynn_terms"])
                               for n in range(2, 6)) + " and " + ", ".join(str(general[n]["ryser_terms"])
                               for n in range(2, 6))),
        "polarization": ("l1...ld by the paper's identity, d = 2..5: " + ", ".join(polar[d]["multiple"]
                         for d in range(2, 6)) + " x l1...ld, with " + ", ".join(str(polar[d]["terms"])
                         for d in range(2, 6)) + " powers"),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for key, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")
    detail = {"input": {"name": INPUT[0], "sha256": INPUT[1], "bytes": INPUT[2], "member": MEMBER},
              "scalar_allowed": SCALAR, "statements": stmts, "right_sides": rights,
              "identities": {name: {k: (frac(v) if k == "multiple" else v) for k, v in f.items()}
                             for name, f in found.items() if name != "koszul"},
              "koszul": found["koszul"], "conditions": cond, "controls": ctl, "control_detail": ctl_detail,
              "strassen": {"perm3_frame": frame, "perm3_commutator_rank": perm_comm,
                           "det3_invertible_of_20": det_invertible},
              "general": general, "polarization": polar}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as fh:
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
        sys.exit(f"it: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
