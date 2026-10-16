#!/usr/bin/env python3
"""Krishna and Makam (2018): the tensor rank of the 3 x 3 determinant tensor is 5 over every field, characteristic two
included; their decomposition, the matrices of their proof, and an exhaustive search over six small fields.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from S. Krishna and V. Makam, "On the tensor
rank of 3 x 3 permanent and determinant" (arXiv:1801.00496v1, January 2018), its abstract: "The tensor rank and border
rank of the $3 \\times 3$ determinant tensor is known to be $5$ if characteristic is not two. In this paper, we show
that the tensor rank remains $5$ for fields of characteristic two as well." The determinant tensor is det_3 = sum over
sigma in S_3 of sgn(sigma) e_sigma(1) (x) e_sigma(2) (x) e_sigma(3) in K^3 (x) K^3 (x) K^3; its Theorem 1.3: for any
field K, trk(det_3) = 5. The upper bound is an expression of det_3 as five simple tensors with coefficients +-1 (its
Section 3.1), found over F_2 by computer and signed to hold over every field. The lower bound is a lemma (trk(T) >= r + 1
when trk(T - S) >= r for every simple S) and, for the three kinds of simple S that the action of SL_3 x S_3 leaves
(S = lambda e1 (x) e2 (x) e3; e1 (x) e2 (x) (a e1 + b e2); lambda e1 (x) e1 (x) e1), the rank of a 9 x 9 matrix: the
flattening of its Proposition 2.2, phi(e1 (x) A + e2 (x) B + e3 (x) C) = [[0, A, B], [-A, 0, C], [-B, -C, 0]], whose rank
r gives brk(T) >= r/2, so that a rank of at least 7 gives trk(det_3 - S) >= brk(det_3 - S) >= 4. The paper prints the
four matrices (Proposition 3.3's for det_3 itself, then one for each case) and reduces cases 2 and 3 to the first by
printed row and column operations.

The data of record is the paper's e-print as arXiv serves it (one gzipped TeX file, small-rank.tex), read by hash and
opened in memory; its TeX is read as text and nothing in it is run. Standard library only, and prank/it.py's exact
Koszul flattening for one control. Every rule below was fixed before anything was computed from the expressions or
matrices the TeX prints. Reading it, one slip was seen by hand and the rules name both readings: the operation printed
for case 3, R_1 -> R_1 - lambda R_8, leaves 2 lambda where the reduction needs 0 (R_1 -> R_1 + lambda R_8 clears it), so
it reduces the matrix as printed only in characteristic two.
(The paper numbers its results within sections, Theorem 1.3 and Propositions 2.2 and 3.3; the numbers above were
corrected after the receipt, in this docstring only.)

The rules:
1. Reading. The align* environments whose left side is \\det_3 or \\per_3: the alignment marks, line breaks, \\quad, {}
   and \\Big are dropped and a final full stop or comma; a right side is an optional \\frac{p}{q} before a parenthesised
   sum, or a sum of terms joined by + and -, a term three factors joined by \\otimes, a factor e_i or a parenthesised
   sum of +-[integer] e_i, an integer before a factor multiplying it. Three must be found: Derksen's det_3 (with 1/2),
   the paper's det_3 and its per_3. The arrays {ccc|ccc|ccc}: \\hline dropped, rows split at \\\\, entries at &, a
   {\\color{red} x} read as x (and marked), an entry an integer combination of 1, \\lambda, a and b. There must be four,
   9 x 9, the first before "Case 1" and one after each case's heading. Anything else refuses the run.
2. The test (TEST), all needed: (i) the paper's det_3 expression has five terms and expands, over the integers, to
   det_3 (so in every field); (ii) for each case, the printed matrix is phi(det_3 - S) entry by entry, as polynomials in
   lambda, a and b; (iii) for each case, phi(det_3 - S) has rank at least 7 for every value of its parameters in every
   field: decided by elimination on unit pivots, an entry that is the constant 1 or -1 used to clear its row and column
   by operations with polynomial multipliers over Z, which keep the rank under every specialisation; the number of such
   pivots is a lower bound for the rank everywhere, and it must reach 7; (iv) over the fields with 2, 3, 4, 5, 7 and 8
   elements, det_3 is not a sum of four simple tensors, by exhaustive search: trk(T) <= r exactly when the span S of
   T's slices lies in the span of r rank-one matrices; here dim S = 3, so trk <= 4 exactly when S itself, or S + <R> for
   some rank-one R outside S, is spanned by the rank-one matrices it contains; every R is tried, and every element of
   each S + <R> is examined.

Beside the test, none of it counted: the paper's per_3 expression against per_3 over Z; Derksen's printed expression
(with its 1/2) against det_3 over Q; Glynn's formula as the paper prints it, (1/2^(n-1)) times the sum over v in
{+1, -1}^(n-1) of (e_1 + v_1 e_2 + ... + v_(n-1) e_n)^(x)n, against per_n for n = 2 to 5, and with the sign
v_1 ... v_(n-1) on each term as Glynn's formula has it; the printed reductions (case 2's operations and case 3's, as
printed and with the sign of lambda R_8 reversed) against the first matrix; the first matrix as phi(det_3), with its
unit pivots, and its rank over Q and over F_2; the unit pivots of each case and the residual left; the least rank of each
case's matrix over every parameter value in each of the six fields; per_3 over the fields of odd order: whether it is a
sum of three simple tensors, and of four; and whether per_3 = det_3 over F_2.

Controls (controls_passed counts those that behave as stated): the search finds four simple tensors where Glynn's
formula provides them (per_3 over the fields with 3, 5 and 7 elements); it finds three for the unit tensor and a
decomposition of four for a tensor built from four fixed simple tensors over each of the six fields; phi of each of
those simple tensors, and of every simple tensor over F_2 and F_3, has rank at most 2 (Proposition 2.2's premise);
over Q, phi(det_3 - S) at parameters 0 to 4 has the rank prank/it.py's Koszul flattening gives the same tensor; the
unit-pivot bound never exceeds the rank found directly over each field at each parameter value; and the paper's det_3
expression with one sign changed does not expand to det_3.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 prank/km2018.py
"""

import gzip
import hashlib
import importlib.util
import itertools
import json
import os
import re
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT = ("arXiv-1801.00496v1.gz", "d036de99f99662c05f43dc816bfae25fc1bd8af552764c8307c27f9c4ecb79f7", 13917)
FIELDS = (2, 3, 4, 5, 7, 8)
NEED = 7
PARAMS = ("lam", "a", "b")
FIXED = (((1, 0, 0), (1, 0, 0), (0, 1, 0)), ((0, 1, 0), (0, 1, 0), (0, 0, 1)), ((0, 0, 1), (0, 0, 1), (1, 0, 0)),
         ((1, 1, 1), (1, 1, 0), (0, 1, 1)))   # four simple tensors whose sum has independent slices over every field
CASES = {1: "lambda e1 (x) e2 (x) e3", 2: "e1 (x) e2 (x) (a e1 + b e2)", 3: "lambda e1 (x) e1 (x) e1"}
TEST = ("Refuted if the paper's five-term expression for det_3 (Section 3.1) is not det_3 over the integers; or if, for "
        "any of its three cases of a simple tensor S (lambda e1(x)e2(x)e3, e1(x)e2(x)(a e1 + b e2), lambda e1(x)e1(x)e1),"
        " the matrix its proof prints is not the flattening [[0,A,B],[-A,0,C],[-B,-C,0]] of det_3 - S, or has rank "
        "below 7 for some value of a, b or lambda in some characteristic; or if, over the field with q elements for q = "
        "2, 3, 4, 5, 7 or 8, det_3 is a sum of four simple tensors (an exhaustive search).")
OUTPUTS = ("identity", "case1", "case2", "case3", "fields", "per3_identity", "derksen", "glynn", "reductions", "prop32",
           "least_ranks", "per3_fields", "conditions_met", "conditions_total", "test_passed", "controls_passed",
           "controls_total")


class Refused(Exception):
    pass


# ----------------------------------------------------------------------------------------------- polynomials over Z

def P(c=0, **powers):
    """A polynomial in lam, a, b over Z as {exponents: coefficient}; P(3) is 3, P(1, lam=1) is lambda."""
    if c == 0:
        return {}
    return {tuple(powers.get(n, 0) for n in PARAMS): c}


def padd(p, q, s=1):
    out = dict(p)
    for k, v in q.items():
        out[k] = out.get(k, 0) + s * v
        if out[k] == 0:
            del out[k]
    return out


def pmul(p, q):
    out = {}
    for k1, v1 in p.items():
        for k2, v2 in q.items():
            k = tuple(x + y for x, y in zip(k1, k2))
            out[k] = out.get(k, 0) + v1 * v2
            if out[k] == 0:
                del out[k]
    return out


def pneg(p):
    return {k: -v for k, v in p.items()}


def const(p):
    """The constant a polynomial is, or None."""
    if not p:
        return 0
    if len(p) == 1 and (0, 0, 0) in p:
        return p[(0, 0, 0)]
    return None


def pstr(p):
    if not p:
        return "0"
    parts = []
    for k in sorted(p):
        mono = "*".join(f"{n}^{e}" if e > 1 else n for n, e in zip(PARAMS, k) if e)
        parts.append(f"{p[k]}" + (f"*{mono}" if mono else ""))
    return " + ".join(parts)


def peval(p, values, F):
    """p at values (a dict of field elements) in the field F."""
    acc = 0
    for k, c in p.items():
        term = F.of_int(c)
        for n, e in zip(PARAMS, k):
            for _ in range(e):
                term = F.mul(term, values[n])
        acc = F.add(acc, term)
    return acc


# ----------------------------------------------------------------------------------------------- reading the e-print

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
        tex = gzip.decompress(data).decode("utf-8")
    except Exception as e:      # noqa: BLE001 - any failure to open is a refusal
        raise Refused(f"the e-print is not one gzipped UTF-8 file: {e}")
    if "\\begin{document}" not in tex:
        raise Refused("no \\begin{document} in the e-print")
    return tex


ID_TOKEN = re.compile(r"\s*(\\frac\{(\d+)\}\{(\d+)\}|\\otimes|e_(\d)|\d+|[()+\-=]|\\det_3|\\per_3)")


def id_tokens(s):
    out, i = [], 0
    s = s.strip()
    while i < len(s):
        m = ID_TOKEN.match(s, i)
        if not m:
            raise Refused(f"an expression holds what the reader does not know: {s[i:i + 30]!r}")
        out.append(m.group(1))
        i = m.end()
        while i < len(s) and s[i].isspace():
            i += 1
    return out


def identity_blocks(tex):
    """The align* environments whose left side is \\det_3 or \\per_3, cleaned: [(name, coefficient, terms)]."""
    found = []
    for m in re.finditer(r"\\begin\{align\*\}(.*?)\\end\{align\*\}", tex, re.S):
        body = m.group(1)
        if "\\det_3" not in body and "\\per_3" not in body:
            continue
        for junk in ("&", "\\\\", "\\quad", "{}", "\\Big"):
            body = body.replace(junk, " ")
        body = body.strip().rstrip(".,").strip()
        found.append(parse_identity(body))
    return found


def parse_identity(body):
    toks = id_tokens(body)
    if len(toks) < 3 or toks[0] not in ("\\det_3", "\\per_3") or toks[1] != "=":
        raise Refused(f"an identity does not begin with det_3 = or per_3 =: {body[:40]!r}")
    name = "det" if toks[0] == "\\det_3" else "per"
    rest = toks[2:]
    coeff = Fraction(1)
    if rest and rest[0].startswith("\\frac"):
        num, den = re.match(r"\\frac\{(\d+)\}\{(\d+)\}", rest[0]).groups()
        coeff = Fraction(int(num), int(den))
        if len(rest) < 3 or rest[1] != "(" or rest[-1] != ")":
            raise Refused("a coefficient not followed by a parenthesised sum")
        rest = rest[2:-1]
    terms = parse_terms(rest)
    return name, coeff, terms


def parse_terms(toks):
    terms, i, n = [], 0, len(toks)
    while i < n:
        sign = 1
        while i < n and toks[i] in "+-":
            sign = -sign if toks[i] == "-" else sign
            i += 1
        factors = []
        while True:
            vec, i = parse_factor(toks, i)
            factors.append(vec)
            if i < n and toks[i] == "\\otimes":
                i += 1
                continue
            break
        if len(factors) != 3:
            raise Refused(f"a term with {len(factors)} factors, not 3")
        terms.append((sign, tuple(factors)))
        if i < n and toks[i] not in "+-":
            raise Refused(f"unexpected {toks[i]!r} after a term")
    if not terms:
        raise Refused("an identity with no terms")
    return terms


def parse_factor(toks, i):
    n = len(toks)
    scale = 1
    if i < n and toks[i].isdigit():
        scale = int(toks[i])
        i += 1
    if i < n and toks[i].startswith("e_"):
        k = int(toks[i][2:])
        if not 1 <= k <= 3:
            raise Refused(f"a basis vector e_{k}")
        v = [0, 0, 0]
        v[k - 1] = scale
        return tuple(v), i + 1
    if i < n and toks[i] == "(":
        i += 1
        v = [0, 0, 0]
        first = True
        while i < n and toks[i] != ")":
            sign = 1
            if toks[i] in "+-":
                sign = -1 if toks[i] == "-" else 1
                i += 1
            elif not first:
                raise Refused("a sum inside a factor without + or -")
            c = 1
            if i < n and toks[i].isdigit():
                c = int(toks[i])
                i += 1
            if i >= n or not toks[i].startswith("e_"):
                raise Refused("a factor's sum holds something other than e_i")
            k = int(toks[i][2:])
            if not 1 <= k <= 3:
                raise Refused(f"a basis vector e_{k}")
            v[k - 1] += sign * c
            i += 1
            first = False
        if i >= n:
            raise Refused("an unclosed parenthesis")
        return tuple(scale * x for x in v), i + 1
    raise Refused(f"a factor that is neither e_i nor a parenthesised sum at {toks[i:i + 3]}")


ENTRY_TOKEN = re.compile(r"\s*(\\lambda|[ab]|\d+|[+\-])")


def parse_entry(s):
    """An integer combination of 1, lambda, a and b, as a polynomial."""
    s = s.strip()
    if not s:
        raise Refused("an empty matrix entry")
    toks, i = [], 0
    while i < len(s):
        m = ENTRY_TOKEN.match(s, i)
        if not m:
            raise Refused(f"a matrix entry the reader does not know: {s!r}")
        toks.append(m.group(1))
        i = m.end()
        while i < len(s) and s[i].isspace():
            i += 1
    p, i, first = {}, 0, True
    while i < len(toks):
        sign = 1
        if toks[i] in "+-":
            sign = -1 if toks[i] == "-" else 1
            i += 1
        elif not first:
            raise Refused(f"a matrix entry without an operator: {s!r}")
        c = 1
        if i < len(toks) and toks[i].isdigit():
            c = int(toks[i])
            i += 1
            if i < len(toks) and toks[i] in ("\\lambda", "a", "b"):
                pass
            else:
                p = padd(p, P(sign * c))
                first = False
                continue
        if i >= len(toks) or toks[i] not in ("\\lambda", "a", "b"):
            raise Refused(f"a matrix entry with a dangling sign: {s!r}")
        name = {"\\lambda": "lam", "a": "a", "b": "b"}[toks[i]]
        p = padd(p, P(sign * c, **{name: 1}))
        i += 1
        first = False
    return p


def arrays(tex):
    """The arrays {ccc|ccc|ccc}: [(position, matrix of polynomials, red marks)]."""
    out = []
    for m in re.finditer(r"\\begin\{array\}\{ccc\|ccc\|ccc\}(.*?)\\end\{array\}", tex, re.S):
        body = m.group(1).replace("\\hline", " ")
        rows = [r for r in body.split("\\\\") if r.strip()]
        if len(rows) != 9:
            raise Refused(f"an array with {len(rows)} rows, not 9")
        mat, red = [], []
        for r in rows:
            cells = r.split("&")
            if len(cells) != 9:
                raise Refused(f"an array row with {len(cells)} entries, not 9")
            row, reds = [], []
            for c in cells:
                rm = re.fullmatch(r"\s*\{\\color\{red\}\s*(.*?)\}\s*", c, re.S)
                reds.append(rm is not None)
                row.append(parse_entry(rm.group(1) if rm else c))
            mat.append(row)
            red.append(reds)
        out.append((m.start(), mat, red))
    return out


def label_arrays(tex, found):
    """Which array is which: the first before Case 1's heading, then one after each case's heading."""
    heads = {int(m.group(1)): m.start() for m in re.finditer(r"\\textbf\{Case (\d)\}", tex)}
    if sorted(heads) != [1, 2, 3]:
        raise Refused(f"case headings {sorted(heads)}, not 1, 2, 3")
    if len(found) != 4:
        raise Refused(f"{len(found)} arrays, not 4")
    labelled = {}
    for pos, mat, red in found:
        before = [k for k, h in heads.items() if h < pos]
        key = max(before) if before else 0
        if key in labelled:
            raise Refused(f"two arrays after the heading of case {key}")
        labelled[key] = (mat, red)
    if sorted(labelled) != [0, 1, 2, 3]:
        raise Refused("the arrays do not fall one before the cases and one in each")
    return labelled


# ----------------------------------------------------------------------------------------------- tensors

def sign(perm):
    s, p = 1, list(perm)
    for i in range(len(p)):
        for j in range(i + 1, len(p)):
            if p[i] > p[j]:
                s = -s
    return s


def det_tensor(n=3):
    return {perm: sign(perm) for perm in itertools.permutations(range(n))}


def per_tensor(n=3):
    return {perm: 1 for perm in itertools.permutations(range(n))}


def tensor_of_terms(terms, coeff=Fraction(1)):
    """sum of coeff * sign * u (x) v (x) w over the terms, as {index: Fraction}, zeros dropped."""
    T = {}
    for s, (u, v, w) in terms:
        for i, j, k in itertools.product(range(3), repeat=3):
            x = u[i] * v[j] * w[k]
            if x:
                T[(i, j, k)] = T.get((i, j, k), 0) + coeff * s * x
    return {key: val for key, val in T.items() if val != 0}


def same(T, U):
    keys = set(T) | set(U)
    return all(T.get(k, 0) == U.get(k, 0) for k in keys)


def glynn(n, signed):
    """Glynn's formula for per_n as the paper prints it (signed False) or with the sign v_1...v_(n-1) (signed True)."""
    T = {}
    for v in itertools.product((1, -1), repeat=n - 1):
        vec = (1,) + v
        s = 1
        if signed:
            for x in v:
                s *= x
        for idx in itertools.product(range(n), repeat=n):
            x = s
            for t in idx:
                x *= vec[t]
            T[idx] = T.get(idx, 0) + Fraction(x, 2 ** (n - 1))
    return {k: v for k, v in T.items() if v != 0}


def case_tensor(case):
    """det_3 - S as {index: polynomial}."""
    T = {k: P(v) for k, v in det_tensor().items()}
    if case == 1:
        S = {(0, 1, 2): P(1, lam=1)}
    elif case == 2:
        S = {(0, 1, 0): P(1, a=1), (0, 1, 1): P(1, b=1)}
    elif case == 3:
        S = {(0, 0, 0): P(1, lam=1)}
    else:
        S = {}
    for k, p in S.items():
        T[k] = padd(T.get(k, {}), p, -1)
    return T


def flatten(T):
    """phi(e1 (x) A + e2 (x) B + e3 (x) C) = [[0, A, B], [-A, 0, C], [-B, -C, 0]], entries polynomials."""
    sl = [[[T.get((s, j, k), {}) for k in range(3)] for j in range(3)] for s in range(3)]
    A, B, C = sl
    Z = [[{} for _ in range(3)] for _ in range(3)]

    def neg(X):
        return [[pneg(x) for x in row] for row in X]
    blocks = [[Z, A, B], [neg(A), Z, C], [neg(B), neg(C), Z]]
    M = []
    for br in range(3):
        for r in range(3):
            M.append([blocks[br][bc][r][c] for bc in range(3) for c in range(3)])
    return M


def matrices_equal(M, N):
    return all(not padd(M[i][j], N[i][j], -1) for i in range(len(M)) for j in range(len(M[0])))


# ----------------------------------------------------------------------------------------------- unit pivots

def unit_pivots(M):
    """Elimination on entries that are the constants 1 or -1, clearing each pivot's column and row by operations with
    polynomial multipliers. Returns (pivots, the residual matrix of the rows and columns left)."""
    A = [[dict(x) for x in row] for row in M]
    rows, cols = list(range(len(A))), list(range(len(A[0])))
    pivots = []
    while True:
        piv = None
        for i in rows:
            for j in cols:
                c = const(A[i][j])
                if c in (1, -1):
                    piv = (i, j, c)
                    break
            if piv:
                break
        if not piv:
            break
        i, j, c = piv
        for r in rows:
            if r != i and A[r][j]:
                f = pmul(A[r][j], P(c))          # c = 1/c for c = +-1
                A[r] = [padd(A[r][t], pmul(f, A[i][t]), -1) for t in range(len(A[0]))]
        for t in cols:
            if t != j and A[i][t]:
                A[i][t] = {}                      # column operations clear the pivot's row; other rows already 0 at j
        pivots.append((i, j))
        rows.remove(i)
        cols.remove(j)
    return pivots, [[A[r][t] for t in cols] for r in rows]


def apply_ops(M, ops):
    """Row and column operations ('R', target, [(coefficient polynomial, source)]) or ('C', ...), in order."""
    A = [[dict(x) for x in row] for row in M]
    for kind, tgt, terms in ops:
        if kind == "R":
            new = list(A[tgt])
            for coef, src in terms:
                new = [padd(new[t], pmul(coef, A[src][t])) for t in range(len(A[0]))]
            A[tgt] = new
        else:
            col = [A[r][tgt] for r in range(len(A))]
            for coef, src in terms:
                col = [padd(col[r], pmul(coef, A[r][src])) for r in range(len(A))]
            for r in range(len(A)):
                A[r][tgt] = col[r]
    return A


# ----------------------------------------------------------------------------------------------- finite fields

class GF:
    """The field with q elements, q in 2, 3, 4, 5, 7, 8; elements 0 .. q-1 (for 4 and 8, bit vectors of a polynomial
    basis modulo x^2 + x + 1 and x^3 + x + 1)."""

    def __init__(self, q):
        self.q = q
        if q in (2, 3, 5, 7):
            self.p, self.k, mod = q, 1, None
        elif q == 4:
            self.p, self.k, mod = 2, 2, 0b111
        elif q == 8:
            self.p, self.k, mod = 2, 3, 0b1011
        else:
            raise ValueError(q)
        r = range(q)
        if self.k == 1:
            self._add = [[(a + b) % q for b in r] for a in r]
            self._mul = [[(a * b) % q for b in r] for a in r]
        else:
            self._add = [[a ^ b for b in r] for a in r]
            self._mul = [[self._clmul(a, b, mod) for b in r] for a in r]
        self._neg = [next(b for b in r if self._add[a][b] == 0) for a in r]
        self._inv = [None] + [next(b for b in r if self._mul[a][b] == 1) for a in range(1, q)]

    def _clmul(self, a, b, mod):
        out = 0
        while b:
            if b & 1:
                out ^= a
            b >>= 1
            a <<= 1
            if a >> self.k:
                a ^= mod
        return out

    def of_int(self, n):
        return n % self.p        # the prime field's image of an integer

    def add(self, a, b):
        return self._add[a][b]

    def mul(self, a, b):
        return self._mul[a][b]

    def neg(self, a):
        return self._neg[a]

    def inv(self, a):
        return self._inv[a]


def rank_gf(rows, F):
    """The rank of a list of vectors over F."""
    A = [list(r) for r in rows]
    rk, ncol = 0, len(A[0]) if A else 0
    for c in range(ncol):
        piv = next((i for i in range(rk, len(A)) if A[i][c]), None)
        if piv is None:
            continue
        A[rk], A[piv] = A[piv], A[rk]
        iv = F.inv(A[rk][c])
        A[rk] = [F.mul(iv, x) for x in A[rk]]
        for i in range(len(A)):
            if i != rk and A[i][c]:
                f = A[i][c]
                A[i] = [F.add(x, F.neg(F.mul(f, y))) for x, y in zip(A[i], A[rk])]
        rk += 1
    return rk


def slices_gf(T, F):
    """The three slices of an integer (or rational with odd denominators) tensor, as 9-tuples over F."""
    out = []
    for s in range(3):
        m = []
        for j in range(3):
            for k in range(3):
                x = T.get((s, j, k), 0)
                if isinstance(x, Fraction):
                    m.append(F.mul(F.of_int(x.numerator), F.inv(F.of_int(x.denominator))))
                else:
                    m.append(F.of_int(x))
        out.append(tuple(m))
    return out


def rank_one_matrices(F):
    """Every rank-one 3 x 3 matrix over F, and one representative of each line."""
    q = F.q
    vecs = [v for v in itertools.product(range(q), repeat=3) if any(v)]
    reps = [v for v in vecs if v[next(i for i in range(3) if v[i])] == 1]
    every = set()
    for u in vecs:
        for v in vecs:
            every.add(tuple(F.mul(x, y) for x in u for y in v))
    lines = [tuple(F.mul(x, y) for x in u for y in v) for u in reps for v in vecs if v[next(i for i in range(3) if v[i])] == 1]
    return every, lines


def span_elements(gens, F):
    """Every element of the span of gens (9-tuples) over F."""
    elems = {tuple([0] * 9)}
    for g in gens:
        new = set()
        for e in elems:
            for t in range(F.q):
                tg = [F.mul(t, x) for x in g]
                new.add(tuple(F.add(x, y) for x, y in zip(e, tg)))
        elems = new
    return elems


def rank_at_most(T, r, F, R1=None):
    """Whether the 3 x 3 x 3 tensor T (integer entries) is a sum of at most r simple tensors over F, for r <= dim S + 1,
    S the span of its slices: exhaustively, as the rules state."""
    if R1 is None:
        R1 = rank_one_matrices(F)
    every, lines = R1
    sl = slices_gf(T, F)
    d = rank_gf(sl, F)
    if r < d:
        return False, {"dim_S": d}
    S = span_elements(sl, F)
    in_S = [m for m in S if m in every]
    if rank_gf(in_S, F) == d if in_S else d == 0:
        return True, {"dim_S": d, "witness": "S"}
    if r == d:
        return False, {"dim_S": d}
    if r > d + 1:
        raise ValueError("the search handles r <= dim S + 1")
    S_list = list(S)
    tried = 0
    if F.p == 2:                 # in characteristic two, a matrix packed into an integer adds by exclusive or
        def pack(m):
            return sum(x << (F.k * i) for i, x in enumerate(m))

        def unpack(c):
            return tuple((c >> (F.k * i)) & (F.q - 1) for i in range(9))
        every_c = {pack(m) for m in every}
        S_c = [pack(s) for s in S_list]
    for R in lines:
        if R in S:
            continue
        tried += 1
        found = []
        for t in range(F.q):
            tR = [F.mul(t, x) for x in R]
            if F.p == 2:
                tc = pack(tR)
                found.extend(unpack(s ^ tc) for s in S_c if (s ^ tc) in every_c)
            else:
                for s in S_list:
                    m = tuple(F.add(x, y) for x, y in zip(s, tR))
                    if m in every:
                        found.append(m)
        if found and rank_gf(found, F) == d + 1:
            return True, {"dim_S": d, "witness": "S + <R>", "tried": tried}
    return False, {"dim_S": d, "tried": tried}


def flat_rank_gf(M, values, F):
    return rank_gf([[peval(x, values, F) for x in row] for row in M], F)


def least_rank(M, case, F):
    names = {1: ("lam",), 2: ("a", "b"), 3: ("lam",)}[case]
    best = None
    for vals in itertools.product(range(F.q), repeat=len(names)):
        values = {"lam": 0, "a": 0, "b": 0}
        values.update(dict(zip(names, vals)))
        rk = flat_rank_gf(M, values, F)
        best = rk if best is None else min(best, rk)
    return best


def rank_q(M):
    A = [[Fraction(x) for x in row] for row in M]
    r = 0
    for c in range(len(A[0])):
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


def at_int(M, values):
    return [[sum(c * values["lam"] ** k[0] * values["a"] ** k[1] * values["b"] ** k[2] for k, c in x.items())
             for x in row] for row in M]


def it_module():
    spec = importlib.util.spec_from_file_location("prank_it_for_km", os.path.join(HERE, "it.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def yes(b):
    return "yes" if b else "no"


# ----------------------------------------------------------------------------------------------- the run

def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    tex = tex_of(read_input(inputs))
    ids = identity_blocks(tex)
    derksen = [x for x in ids if x[0] == "det" and x[1] != 1]
    km_det = [x for x in ids if x[0] == "det" and x[1] == 1]
    km_per = [x for x in ids if x[0] == "per"]
    if len(derksen) != 1 or len(km_det) != 1 or len(km_per) != 1:
        raise Refused(f"identities found: {[(x[0], str(x[1]), len(x[2])) for x in ids]}")
    mats = label_arrays(tex, arrays(tex))
    cond, controls, detail = {}, {}, {}
    DET, PER = det_tensor(), per_tensor()

    # (i) the decomposition
    _, c_det, t_det = km_det[0]
    ok_i = len(t_det) == 5 and same(tensor_of_terms(t_det), DET)
    cond["(i) the five-term expression is det_3 over Z"] = ok_i
    detail["identity"] = {"terms": len(t_det), "equal": ok_i}

    # (ii), (iii) each case
    case_out = {}
    for k in (1, 2, 3):
        printed, red = mats[k]
        phi = flatten(case_tensor(k))
        eq = matrices_equal(printed, phi)
        piv, resid = unit_pivots(phi)
        residual = [[pstr(x) for x in row] for row in resid]
        cond[f"(ii) case {k}: the printed matrix is phi(det_3 - S)"] = eq
        cond[f"(iii) case {k}: rank >= 7 everywhere by unit pivots"] = len(piv) >= NEED
        lone = sum(1 for i in range(9) for j in range(9) if red[i][j])
        case_out[k] = {"equal_to_flattening": eq, "unit_pivots": len(piv), "residual": residual,
                       "red_entries": lone}
    detail["cases"] = case_out

    # (iv) the exhaustive search
    fields = {}
    R1s = {}
    for q in FIELDS:
        F = GF(q)
        R1s[q] = rank_one_matrices(F)
        le4, info = rank_at_most(DET, 4, F, R1s[q])
        le5_terms = tensor_of_terms(t_det)
        fields[q] = {"rank_at_most_4": le4, "info": info,
                     "five_terms_hold": slices_gf(le5_terms, F) == slices_gf(DET, F)}
        cond[f"(iv) over F_{q}: det_3 is not a sum of four simple tensors"] = not le4
    detail["fields"] = {str(k): v for k, v in fields.items()}

    # beside
    _, c_per, t_per = km_per[0]
    per_ok = len(t_per) == 5 and same(tensor_of_terms(t_per), PER)
    _, c_der, t_der = derksen[0]
    der_ok = same(tensor_of_terms(t_der, c_der), DET)
    glynn_rows = {}
    for n in (2, 3, 4, 5):
        target = {k: Fraction(1) for k in per_tensor(n)}
        glynn_rows[n] = {"printed": same(glynn(n, False), target), "signed": same(glynn(n, True), target)}
    prop = mats[0][0]
    prop_is_phi = matrices_equal(prop, flatten(case_tensor(0)))
    prop_piv, prop_res = unit_pivots(prop)
    prop_rank_q = rank_q(at_int(prop, {"lam": 0, "a": 0, "b": 0}))
    prop_rank_2 = flat_rank_gf(prop, {"lam": 0, "a": 0, "b": 0}, GF(2))
    lam, a, b = P(1, lam=1), P(1, a=1), P(1, b=1)
    ops2 = [("R", 4, [(a, 8), (pneg(b), 5)]), ("C", 4, [(b, 5)]), ("C", 3, [(a, 5)])]
    ops3_printed = [("R", 3, [(lam, 8)]), ("R", 0, [(pneg(lam), 7)])]
    ops3_signed = [("R", 3, [(lam, 8)]), ("R", 0, [(lam, 7)])]
    red2 = matrices_equal(apply_ops(mats[2][0], ops2), prop)
    red3p = apply_ops(mats[3][0], ops3_printed)
    red3p_exact = matrices_equal(red3p, prop)
    diff3 = [(i, j, pstr(padd(red3p[i][j], prop[i][j], -1))) for i in range(9) for j in range(9)
             if padd(red3p[i][j], prop[i][j], -1)]
    red3s = matrices_equal(apply_ops(mats[3][0], ops3_signed), prop)
    least = {}
    for k in (1, 2, 3):
        phi = flatten(case_tensor(k))
        least[k] = {q: least_rank(phi, k, GF(q)) for q in FIELDS}
    per_fields = {}
    for q in (3, 5, 7):
        F = GF(q)
        le3, _ = rank_at_most(PER, 3, F, R1s[q])
        le4, _ = rank_at_most(PER, 4, F, R1s[q])
        per_fields[q] = {"at_most_3": le3, "at_most_4": le4}
    per_eq_det_f2 = slices_gf(PER, GF(2)) == slices_gf(DET, GF(2))
    detail["beside"] = {"per3_identity": per_ok, "derksen": der_ok, "glynn": {str(k): v for k, v in glynn_rows.items()},
                        "prop32_is_phi_det3": prop_is_phi, "prop32_unit_pivots": len(prop_piv),
                        "prop32_residual": [[pstr(x) for x in row] for row in prop_res],
                        "prop32_rank_Q": prop_rank_q, "prop32_rank_F2": prop_rank_2,
                        "case2_printed_reduction": red2, "case3_printed_reduction": red3p_exact,
                        "case3_printed_leaves": diff3, "case3_sign_reversed_reduction": red3s,
                        "least_ranks": {str(k): {str(q): v for q, v in d.items()} for k, d in least.items()},
                        "per3_fields": {str(k): v for k, v in per_fields.items()}, "per3_equals_det3_over_F2": per_eq_det_f2}

    # controls
    ok = True
    for q in (3, 5, 7):
        ok = ok and per_fields[q]["at_most_4"]
    controls["the search finds four simple tensors for per_3 over F_3, F_5 and F_7 (Glynn)"] = ok
    unit = {(i, i, i): 1 for i in range(3)}
    fixed = FIXED
    four = tensor_of_terms([(1, t) for t in fixed])
    ok_unit, ok_four = True, True
    for q in FIELDS:
        F = GF(q)
        ok_unit = ok_unit and rank_at_most(unit, 3, F, R1s[q])[0] and not rank_at_most(unit, 2, F, R1s[q])[0]
        ok_four = ok_four and rank_at_most(four, 4, F, R1s[q])[0]
    controls["the search finds three for the unit tensor (not two) and four for a sum of four fixed simple tensors"] = (
        ok_unit and ok_four)
    prem = True
    for q in (2, 3):
        F = GF(q)
        vecs = [v for v in itertools.product(range(q), repeat=3) if any(v)]
        for u in vecs:
            for v in vecs:
                for w in vecs:
                    T = {(i, j, k): u[i] * v[j] * w[k] for i in range(3) for j in range(3) for k in range(3)}
                    Tp = {kk: P(x) for kk, x in T.items() if x}
                    prem = prem and flat_rank_gf(flatten(Tp), {"lam": 0, "a": 0, "b": 0}, F) <= 2
    for t in fixed:
        T = tensor_of_terms([(1, t)])
        prem = prem and rank_q(at_int(flatten({kk: P(int(x)) for kk, x in T.items()}), {"lam": 0, "a": 0, "b": 0})) <= 2
    controls["phi of every simple tensor over F_2 and F_3 (and of the four fixed ones over Q) has rank at most 2"] = prem
    it = it_module()
    agree = True
    for k in (1, 2, 3):
        for val in range(5):
            values = {"lam": val, "a": val, "b": (val * 3 + 1) % 5}
            phi_rank = rank_q(at_int(flatten(case_tensor(k)), values))
            Tk = case_tensor(k)
            arr = [[[Fraction(sum(c * values["lam"] ** e[0] * values["a"] ** e[1] * values["b"] ** e[2]
                                  for e, c in Tk.get((i, j, kk), {}).items())) for kk in range(3)] for j in range(3)]
                   for i in range(3)]
            agree = agree and it.rank(it.koszul(arr)) == phi_rank
    controls["over Q, phi(det_3 - S) at five parameter values has prank/it.py's Koszul rank"] = agree
    bound_ok = True
    for k in (1, 2, 3):
        piv = case_out[k]["unit_pivots"]
        bound_ok = bound_ok and all(least[k][q] >= piv for q in FIELDS)
    controls["the unit-pivot bound never exceeds the least rank found over each field"] = bound_ok
    s0, (u0, v0, w0) = t_det[0]
    flipped = [(-s0, (u0, v0, w0))] + list(t_det[1:])
    controls["the det_3 expression with its first sign changed is not det_3"] = not same(tensor_of_terms(flipped), DET)

    # outputs
    def case_line(k):
        c = case_out[k]
        return (f"S = {CASES[k]}: printed matrix is phi(det_3 - S): {yes(c['equal_to_flattening'])}; unit pivots "
                f"{c['unit_pivots']} (need 7); least rank over F_2..F_8: "
                + ", ".join(str(least[k][q]) for q in FIELDS))[:200]
    out = {
        "identity": f"the paper's det_3 expression: {len(t_det)} terms, det_3 over Z: {yes(ok_i)}",
        "case1": case_line(1), "case2": case_line(2), "case3": case_line(3),
        "fields": ("a sum of four simple tensors over F_q, q = 2, 3, 4, 5, 7, 8: "
                   + ", ".join(yes(fields[q]["rank_at_most_4"]) for q in FIELDS)
                   + "; the five terms hold in each: " + yes(all(fields[q]["five_terms_hold"] for q in FIELDS))),
        "per3_identity": f"the paper's per_3 expression: {len(t_per)} terms, per_3 over Z: {yes(per_ok)}",
        "derksen": f"Derksen's expression as printed (with 1/2) is det_3 over Q: {yes(der_ok)}",
        "glynn": ("Glynn's formula as printed is per_n, n = 2..5: "
                  + ", ".join(yes(glynn_rows[n]["printed"]) for n in (2, 3, 4, 5))
                  + "; with the sign v_1...v_(n-1): " + ", ".join(yes(glynn_rows[n]["signed"]) for n in (2, 3, 4, 5))),
        "reductions": (f"case 2's printed operations give the first matrix: {yes(red2)}; case 3's as printed: "
                       f"{yes(red3p_exact)} (leaves {', '.join(d[2] for d in diff3) or 'nothing'}); with + lambda R_8: "
                       f"{yes(red3s)}")[:200],
        "prop32": (f"the first matrix is phi(det_3): {yes(prop_is_phi)}; unit pivots {len(prop_piv)}; rank over Q "
                   f"{prop_rank_q}, over F_2 {prop_rank_2}"),
        "least_ranks": "; ".join(f"case {k}: " + "/".join(str(least[k][q]) for q in FIELDS) for k in (1, 2, 3)),
        "per3_fields": ("per_3 over F_3, F_5, F_7: a sum of three simple tensors "
                        + "/".join(yes(per_fields[q]["at_most_3"]) for q in (3, 5, 7)) + ", of four "
                        + "/".join(yes(per_fields[q]["at_most_4"]) for q in (3, 5, 7))
                        + f"; per_3 = det_3 over F_2: {yes(per_eq_det_f2)}"),
    }
    out["conditions_met"] = sum(1 for v in cond.values() if v)
    out["conditions_total"] = len(cond)
    out["test_passed"] = int(all(cond.values()))
    out["controls_passed"] = sum(1 for v in controls.values() if v)
    out["controls_total"] = len(controls)
    assert set(out) == set(OUTPUTS), sorted(set(out) ^ set(OUTPUTS))
    for kk, v in out.items():
        if isinstance(v, str):
            assert len(v) <= 200, (kk, len(v))
    detail.update({"test": TEST, "conditions": cond, "controls": controls,
                   "input": {"name": INPUT[0], "sha256": INPUT[1], "bytes": INPUT[2]}})
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
        out, _ = run(seed)      # nothing here depends on the seed: every check is exhaustive or exact
    except Refused as e:
        sys.exit(f"km2018: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
