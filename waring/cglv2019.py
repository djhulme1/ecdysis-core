#!/usr/bin/env python3
"""Conner, Gesmundo, Landsberg & Ventura's upper bounds for the Waring rank (18) and the border Waring rank (17) of
the 3 x 3 determinant, and the strict submultiplicativity they show for T_skewcw,2, whose Kronecker square is det_3.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from A. Conner, F. Gesmundo, J. M. Landsberg
and E. Ventura, "Rank and border rank of Kronecker powers of tensors and Strassen's laser method", arXiv:1909.04785v2
(27 December 2021; first version 10 September 2019; computational complexity 31, 2022), its abstract: "We determine
new upper bounds for the (Waring) rank and the (Waring) border rank of $\\det_3$, exhibiting a strict
submultiplicative behaviour for $T_{skewcw,2}$ which is promising for the laser method." Its Theorem (stated in the
introduction and proved in Section 4): R_S(det_3) <= 18 and its border analogue <= 17; with its Lemma (T_skewcw,2's
Kronecker square is det_3 as a tensor) and its Proposition that the border rank of T_skewcw,q is at least q + 3 for
even q, this gives border rank(T_skewcw,2 Kronecker squared) <= 17 < 25 <= border rank(T_skewcw,2)^2.

Its registered test is TEST below. Every rule was fixed before any of the paper's identities, its equations or its
certificate was evaluated. Known before the rules, from reading: the TeX's Sections 1 to 4 (the abstract, the
definitions, the Lemma's proof by stabilisers, the Proposition's flattening, the 18 forms with theta = exp(2 pi i/6)
and the 17 forms L_i(t) with their unknowns z_1..z_44, the degree-27 polynomial, the description of the certificate
and of the numerics that found it); the supplementary page (people.tamu.edu/~jml/CGLVkronsupp.html) and, as text,
Appendix B's Macaulay2 file, whose last line checks "sum(1..18,j-> L_j^3) - 6*det(X)" and whose comment says the
answer is 0 (so the paper's det_3 is read as the cubic form 6 det(X), the cubic form of the tensor eps (x) eps; rule
2 asks only for a nonzero multiple and reports it), and Appendix C's seven files as text (their layout: the field F,
yy_1..yy_44 as polynomials of degree 26 in y with rational coefficients, 14 equations of type 1 and 40 of type 2 in
z_1..z_44, and for each equation a list of triples {monomial, expression, coefficient}, the first monomial of a type
2 equation being its chosen u). A reading-only pass of the readers over every input counted what they read and
computed nothing the test compares.

1. Inputs, each checked against its SHA-256 and size and read in memory, never unpacked to disk: the paper's e-print
   (EPRINT, a gzipped tar holding CGLVkron-Final.tex and its .bbl), the data of record with Appendix B (APPB,
   Det3_Rank18.m2) and Appendix C (APPC, Det3_borderRank17.tar.gz, seven Macaulay2 files), downloaded from the
   authors' supplementary page. The Macaulay2 files are parsed as data by this module's own reader (integers,
   rationals, +, -, *, /, ^, parentheses, the names y, u, a, b, t, z_k and x_(i,j)); nothing in them is executed.
2. C1, the Waring decomposition. The 18 matrices L_1..L_18 of the TeX's proof that R_S(det_3) <= 18 are read entry by
   entry (0, +-1, +-1/3, theta, its inverse theta-bar, and their products); L = (zeta_ij) is the linear form
   sum zeta_ij x_ij. Arithmetic is exact in Q(theta), theta^2 = theta - 1, theta-bar = 1 - theta. C1 holds when
   sum_i L_i^3, expanded, equals c det(X) for a nonzero c in Q(theta), X = (x_ij) generic; c is reported.
3. C2, the border Waring decomposition. The 17 matrices L_i(t) of the TeX's proof that the border rank is <= 17 are
   read entry by entry (0, +-1, +-t, +-z_k, +-z_k t). The system: the coefficients of t^0, t^1 and t^2 of every cubic
   monomial x^alpha in sum_i L_i(t)^3 - t^2 c det(X), c from C1 when rational (else 6), each divided by alpha's
   multinomial coefficient (6, 3 or 1), as polynomials in z_1..z_44; those not identically zero are the system.
   C2 holds when (a) every equation of the system is a nonzero rational multiple of exactly one of Appendix C's 54
   equations and each of those is matched, and (b) Appendix C's certificate holds, every identity exactly:
   F = Q[y]/(f) with f the degree-27 polynomial of the files (rule 6 compares it with the TeX's); for an equation
   of type 1, for each of its triples (m, e, k) the cube of e equals in F the monomial m with each z_j replaced by
   yy_j, sum k m equals the equation as a polynomial in the z's, and sum k e = 0 in F; for one of type 2, the same
   in K = F[u]/(u^3 - p), p the first triple's monomial with each z_j replaced by yy_j, whose expression must be u.
   Why that suffices: at any real root y* of f, evaluation y -> y*, u -> the real cube root of p(y*) is a ring
   homomorphism from F and K to the reals; the real number e(y*, u) has the cube of m(z) at z_j = the real cube
   root of yy_j(y*), so it is m(z), real cube roots being unique; so every equation holds at those z's, and
   sum_i L_i(t)^3 = t^2 c det(X) + O(t^3). (Neither F nor K need be a field for this.)
4. C3, the border rank of T_skewcw,2. T_skewcw,q = sum_j a_0 b_j c_j + a_j b_0 c_j + sum_xi (a_xi b_(xi+u)
   - a_(xi+u) b_xi) c_0, q = 2u, as the TeX defines it; the Proposition's map phi: a_0 -> e_0, a_1..a_u -> e_1,
   a_(u+1)..a_q -> e_2; the p = 1 Koszul flattening of phi(T), A' (x) B* -> Lambda^2 A' (x) C,
   e_m (x) beta_j -> sum T'_ijk (e_i ^ e_m) (x) c_k, its rank computed exactly over Q (Gaussian elimination in
   fractions). Its border rank is at least ceil(rank / 2) (the TeX's inequality with dim A' = 3). C3 holds when at
   q = 2 the rank is 9, so the border rank is at least 5 and 17 < 25.
5. C4, the Kronecker square. The TeX's identification (a_0 <-> -b_0 <-> c_0, a_j <-> b_j <-> -c_(u+j),
   a_(u+j) <-> b_(u+j) <-> c_j) sends T_skewcw,2 to a tensor T' in A (x) A (x) A; C4 holds when T' is a nonzero
   multiple of eps (eps_ijk the sign of the permutation (i, j, k) of (0, 1, 2), 0 otherwise), and T' (x) T', its
   indices paired ((i, i'), (j, j'), (k, k')) as a tensor in (C^9)^(x)3, is symmetric with cubic form
   sum T'_ijk T'_i'j'k' x_ii' x_jj' x_kk' equal to the C1 multiple c times det(X) (both reported).
   test_passed is 1 when C1 to C4 all hold.
6. Beside the test, none of it counted: Appendix B's 18 forms against the TeX's and the multiple its last line
   names; the TeX's degree-27 polynomial against Appendix C's modulus; the number of real roots of f (exactly, by
   sympy's count_roots, and by numpy.roots) and, at each real root found and refined to 120 digits by mpmath, the
   largest residual of the system of rule 3 at z_j = the real cube root of yy_j(y*); the printed counts (54
   equations, 44 unknowns, 14 of type 1, 40 of type 2) against the files and the system; for each type 2 equation,
   whether Q[p] = Q[y*], the 27 x 27 matrix of the powers p^0..p^26 in the basis y^0..y^26 having full rank modulo
   each of two primes (the paper's own claim, not needed by rule 3); the Proposition's rank 2q + 5 for every even q
   from 2 to 20; and Johns & Teitler's remark that their expression is exactly the case d = 3 of theirs: their
   terms (-1)^sigma (sum_i omega^(ij) x_(i,sigma(i)))^3, column 2 divided by 3 (6 det(X) = 18 det(X) / 3), matched
   one to one with the 18 forms up to sixth roots of unity zeta with zeta^3 equal to the term's sign, for omega a
   primitive cube root of unity, either one, and X or its transpose.
7. Controls (controls_passed counts those that behave as stated): (1) with L_1's entry -1/3 replaced by -1/2 the sum
   of cubes is no longer a multiple of det(X); (2) with yy_1 replaced by 2 yy_1 at least one identity of the
   certificate fails; (3) numerically, at a point drawn from the seed (entries a + b i, a and b integers from -9 to 9,
   SHA-256 of the seed, a label and a counter), the 18 cubes sum to c det within 1e-40 at 60 digits exactly when C1
   holds, and the system of rule 3 vanishes within 1e-80 at 120 digits at every real root of f found exactly when the
   certificate holds; (4) the Koszul machinery on unit tensors: sum_(i<=r) a_i b_i c_i in C^r (x) C^r (x) C^r gives
   rank 2r with A' = A (r = 3), and 10 with a seed-drawn integer restriction to C^3 (r = 5; its columns drawn from
   -9..9 and drawn again when zero).

What it cannot check: that 17 and 18 are optimal (Conner, Harper & Landsberg's border apolarity, cited for the lower
bound 17, is not run here), or the numerical search that found the decomposition.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 waring/cglv2019.py
"""

import hashlib
import io
import json
import math
import os
import re
import sys
import tarfile
from fractions import Fraction
from itertools import permutations

TEST = ("Refuted if the cubes of the paper's 18 printed linear forms (theta = e^(2 pi i/6)) do not sum to a nonzero "
        "multiple c of det(X), X a generic 3 x 3 matrix, or its 17 printed forms L_i(t), z_j the real cube root of "
        "the y_j its Appendix C gives in Q[y*] (y* a real root of its degree-27 polynomial), do not give "
        "sum L_i(t)^3 = t^2 c det(X) + O(t^3) exactly, or its Koszul flattening gives T_skewcw,2 border rank below "
        "5, or the Kronecker square of T_skewcw,2 is not det_3 as a tensor.")

EPRINT = ("arXiv-1909.04785v2.tar.gz", "aae0871979872f179c0d57bd0f2c1223a6ae9dc78983f8f41734c6060a3ff9e7", 36958)
APPB = ("Det3_Rank18.m2", "f9dd85a30ba563fd267f1e3ed62a7d885f75764762136a5e5ef50532cba9bf95", 1330)
APPC = ("Det3_borderRank17.tar.gz", "17fef30c5ed673a272efbc44c10cce28fba8adee4d36aa0a2857fc7a50059165", 127194)
TEXNAME = "CGLVkron-Final.tex"
PRINTED = {"equations": 54, "unknowns": 44, "type1": 14, "type2": 40}
PRIMES = (2147483629, 2147483587)


class Refused(Exception):
    pass


# ---------------------------------------------------------------- inputs

def read_input(inputs, spec):
    name, sha, size = spec
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha or len(data) != size:
        raise Refused(f"{name}: sha256 {got} ({len(data)} bytes), not the registered {sha} ({size})")
    return data


def tar_texts(blob):
    """The files of a gzipped tar, read in memory, as text."""
    out = {}
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
        for m in tf.getmembers():
            if m.isfile():
                out[m.name] = tf.extractfile(m).read().decode("utf-8")
    return out


class Stream:
    """Integers from the seed: SHA-256 of seed, label and a counter."""

    def __init__(self, seed, label):
        self.seed, self.label, self.n = seed, label, 0

    def below(self, k):
        self.n += 1
        h = hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
        return int.from_bytes(h[:8], "big") % k


# ---------------------------------------------------------------- Q(theta), theta^2 = theta - 1

class QT:
    __slots__ = ("a", "b")

    def __init__(self, a=0, b=0):
        self.a, self.b = Fraction(a), Fraction(b)

    def __add__(self, o):
        return QT(self.a + o.a, self.b + o.b)

    def __sub__(self, o):
        return QT(self.a - o.a, self.b - o.b)

    def __neg__(self):
        return QT(-self.a, -self.b)

    def __mul__(self, o):
        return QT(self.a * o.a - self.b * o.b, self.a * o.b + o.a * self.b + self.b * o.b)

    def __eq__(self, o):
        return self.a == o.a and self.b == o.b

    def __hash__(self):
        return hash((self.a, self.b))

    def iszero(self):
        return self.a == 0 and self.b == 0

    def __repr__(self):
        return f"{self.a}+{self.b}th"


THETA = QT(0, 1)
THETABAR = QT(1, -1)
ONE = QT(1)
ZERO = QT(0)


def qt_complex(v, mp):
    th = mp.exp(1j * mp.pi / 3)
    return mp.mpf(v.a.numerator) / v.a.denominator + mp.mpf(v.b.numerator) / v.b.denominator * th


def parse_qt_entry(s):
    """A TeX matrix entry of the 18 forms: sign, \\frac{p}{q}, \\theta or \\bar{\\theta}, integers."""
    s = s.replace(" ", "").replace("\n", "")
    if not s:
        raise Refused("empty matrix entry")
    val = ONE
    sign = 1
    while s and s[0] in "+-":
        if s[0] == "-":
            sign = -sign
        s = s[1:]
    pos = 0
    seen = False
    while pos < len(s):
        m = re.match(r"\\frac\{(\d+)\}\{(\d+)\}", s[pos:])
        if m:
            val = val * QT(Fraction(int(m.group(1)), int(m.group(2))))
            pos += m.end()
            seen = True
            continue
        if s.startswith(r"\bar{\theta}", pos):
            val = val * THETABAR
            pos += len(r"\bar{\theta}")
            seen = True
            continue
        if s.startswith(r"\theta", pos):
            val = val * THETA
            pos += len(r"\theta")
            seen = True
            continue
        m = re.match(r"\d+", s[pos:])
        if m:
            val = val * QT(int(m.group(0)))
            pos += m.end()
            seen = True
            continue
        raise Refused(f"matrix entry {s!r}: cannot read at {s[pos:]!r}")
    if not seen:
        raise Refused(f"matrix entry {s!r}")
    return val if sign == 1 else -val


def pmatrix_cells(body):
    rows = [r for r in re.split(r"\\\\", body) if r.strip()]
    cells = [[c.strip() for c in r.split("&")] for r in rows]
    if len(cells) != 3 or any(len(r) != 3 for r in cells):
        raise Refused(f"a matrix that is not 3 x 3: {body[:80]!r}")
    return cells


def tex_section(tex, start, end):
    i = tex.find(start)
    if i < 0:
        raise Refused(f"the TeX lacks {start!r}")
    j = tex.find(end, i)
    if j < 0:
        raise Refused(f"the TeX lacks {end!r} after {start!r}")
    return tex[i:j]


def read_forms18(tex):
    block = tex_section(tex, r"\begin{theorem}\label{det18thm}", r"\end{proof}")
    found = re.findall(r"L_\{?(\d+)\}?\s*=\s*\\begin\{pmatrix\}(.*?)\\end\{pmatrix\}", block, re.S)
    if [int(k) for k, _ in found] != list(range(1, 19)):
        raise Refused(f"the 18 forms: read {[k for k, _ in found]}")
    return [[[parse_qt_entry(c) for c in row] for row in pmatrix_cells(body)] for _, body in found]


def parse_t_entry(s):
    """A TeX matrix entry of the 17 forms: (coefficient, z index or None, power of t)."""
    s = s.replace(" ", "").replace("\n", "")
    sign = 1
    while s and s[0] in "+-":
        if s[0] == "-":
            sign = -sign
        s = s[1:]
    if s == "0":
        return (0, None, 0)
    m = re.fullmatch(r"(\d*)(?:z_\{(\d+)\})?(t?)", s)
    if not m or s == "":
        raise Refused(f"matrix entry {s!r}")
    num, z, t = m.groups()
    if num == "" and z is None and t == "":
        raise Refused(f"matrix entry {s!r}")
    coef = sign * (int(num) if num else 1)
    return (coef, int(z) if z else None, 1 if t else 0)


def read_forms17(tex):
    block = tex_section(tex, r"\begin{theorem}\label{det17thm}", r"The coefficients $z_1")
    found = re.findall(r"L_\{?(\d+)\}?\(t\)\s*=\s*\\begin\{pmatrix\}(.*?)\\end\{pmatrix\}", block, re.S)
    if [int(k) for k, _ in found] != list(range(1, 18)):
        raise Refused(f"the 17 forms: read {[k for k, _ in found]}")
    return [[[parse_t_entry(c) for c in row] for row in pmatrix_cells(body)] for _, body in found]


def read_tex_polynomial(tex):
    block = tex_section(tex, r"Let $y_*$ be a real root of the polynomial", r"For $i = 1")
    m = re.search(r"\\begin\{align\*\}(.*?)\\end\{align\*\}", block, re.S)
    if not m:
        raise Refused("the degree-27 polynomial's display")
    s = m.group(1).replace("&", "").replace("\\\\", "").replace("\n", "").replace(" ", "").rstrip(".")
    coeffs = {}
    for sign, num, var, exp in re.findall(r"([+-]?)(\d*)(x?)(?:\^\{?(\d+)\}?)?", s):
        if num == "" and var == "":
            continue
        c = int(num) if num else 1
        c = -c if sign == "-" else c
        e = (int(exp) if exp else 1) if var else 0
        if e in coeffs:
            raise Refused(f"the polynomial repeats x^{e}")
        coeffs[e] = c
    if max(coeffs) != 27 or coeffs[27] != 1:
        raise Refused("the TeX's polynomial is not monic of degree 27")
    return [coeffs.get(i, 0) for i in range(28)]


# ---------------------------------------------------------------- Macaulay2 expressions, read as data

def m2_tokens(s):
    toks = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch.isspace():
            i += 1
            continue
        m = re.match(r"x_\((\d+),(\d+)\)", s[i:])
        if m:
            toks.append(("var", f"x{m.group(1)}{m.group(2)}"))
            i += m.end()
            continue
        m = re.match(r"z_(\d+)", s[i:])
        if m:
            toks.append(("var", f"z{int(m.group(1))}"))
            i += m.end()
            continue
        m = re.match(r"\d+", s[i:])
        if m:
            toks.append(("num", int(m.group(0))))
            i += m.end()
            continue
        if ch in "yuabt" and not (i + 1 < len(s) and (s[i + 1].isalnum() or s[i + 1] == "_")):
            toks.append(("var", ch))
            i += 1
            continue
        if ch in "+-*/^()":
            toks.append(("op", ch))
            i += 1
            continue
        raise Refused(f"Macaulay2 text: cannot read {s[i:i + 30]!r}")
    return toks


class Poly:
    """Sparse polynomial over Q: {tuple(sorted((name, exponent))): Fraction}."""

    __slots__ = ("t",)

    def __init__(self, terms=None):
        self.t = {k: v for k, v in (terms or {}).items() if v != 0}

    @staticmethod
    def const(c):
        return Poly({(): Fraction(c)})

    @staticmethod
    def var(name):
        return Poly({((name, 1),): Fraction(1)})

    def __add__(self, o):
        r = dict(self.t)
        for k, v in o.t.items():
            r[k] = r.get(k, 0) + v
        return Poly(r)

    def __neg__(self):
        return Poly({k: -v for k, v in self.t.items()})

    def __sub__(self, o):
        return self + (-o)

    def __mul__(self, o):
        r = {}
        for k1, v1 in self.t.items():
            for k2, v2 in o.t.items():
                d = dict(k1)
                for n, e in k2:
                    d[n] = d.get(n, 0) + e
                k = tuple(sorted(d.items()))
                r[k] = r.get(k, 0) + v1 * v2
        return Poly(r)

    def scale(self, c):
        return Poly({k: v * c for k, v in self.t.items()})

    def __pow__(self, n):
        r = Poly.const(1)
        for _ in range(n):
            r = r * self
        return r

    def __eq__(self, o):
        return self.t == o.t

    def iszero(self):
        return not self.t

    def isconst(self):
        return all(k == () for k in self.t)

    def constval(self):
        return self.t.get((), Fraction(0))

    def names(self):
        return {n for k in self.t for n, _ in k}

    def canonical(self):
        """Divided by the coefficient of its first term in sorted order: equal for rational multiples."""
        if not self.t:
            return ()
        k0 = min(self.t)
        c = self.t[k0]
        return tuple(sorted((k, v / c) for k, v in self.t.items()))


class M2Parser:
    def __init__(self, text):
        self.toks = m2_tokens(text)
        self.i = 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else (None, None)

    def take(self):
        t = self.peek()
        self.i += 1
        return t

    def parse(self):
        p = self.expr()
        if self.i != len(self.toks):
            raise Refused(f"Macaulay2 text: trailing {self.toks[self.i:self.i + 4]}")
        return p

    def expr(self):
        p = self.term()
        while self.peek() in (("op", "+"), ("op", "-")):
            op = self.take()[1]
            q = self.term()
            p = p + q if op == "+" else p - q
        return p

    def term(self):
        p = self.unary()
        while self.peek() in (("op", "*"), ("op", "/")):
            op = self.take()[1]
            q = self.unary()
            if op == "*":
                p = p * q
            else:
                if not q.isconst() or q.constval() == 0:
                    raise Refused("Macaulay2 text: division by a non-constant")
                p = p.scale(1 / q.constval())
        return p

    def unary(self):
        if self.peek() == ("op", "-"):
            self.take()
            return -self.unary()
        if self.peek() == ("op", "+"):
            self.take()
            return self.unary()
        return self.power()

    def power(self):
        p = self.atom()
        if self.peek() == ("op", "^"):
            self.take()
            kind, n = self.take()
            if kind != "num":
                raise Refused("Macaulay2 text: a non-integer exponent")
            p = p ** n
        return p

    def atom(self):
        kind, v = self.take()
        if kind == "num":
            return Poly.const(v)
        if kind == "var":
            return Poly.var(v)
        if (kind, v) == ("op", "("):
            p = self.expr()
            if self.take() != ("op", ")"):
                raise Refused("Macaulay2 text: unbalanced parentheses")
            return p
        raise Refused(f"Macaulay2 text: unexpected {kind} {v!r}")


def m2(text):
    return M2Parser(text).parse()


def m2_assignments(text, prefix):
    """name_k = expression; statements, as {k: Poly}."""
    out = {}
    for k, body in re.findall(prefix + r"_(\d+)\s*=\s*([^;]*);", text):
        k = int(k)
        if k in out:
            raise Refused(f"{prefix}_{k} assigned twice")
        out[k] = m2(body)
    return out


def split_top(s, sep=","):
    """Split at separators outside braces and parentheses."""
    parts, depth, cur = [], 0, []
    for ch in s:
        if ch in "{(":
            depth += 1
        elif ch in "})":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if depth != 0:
        raise Refused("unbalanced braces")
    parts.append("".join(cur))
    return [p.strip() for p in parts]


def strip_braces(s):
    s = s.strip()
    if not (s.startswith("{") and s.endswith("}")):
        raise Refused(f"expected a braced list: {s[:40]!r}")
    return s[1:-1]


def read_mon(text):
    m = re.search(r"Mon\s*=\s*(\{.*\})\s*;", text, re.S)
    if not m:
        raise Refused("a monomials file without Mon = {...};")
    eqs = []
    for eq in split_top(strip_braces(m.group(1))):
        triples = []
        for tr in split_top(strip_braces(eq)):
            parts = split_top(strip_braces(tr))
            if len(parts) != 3:
                raise Refused(f"a triple of {len(parts)} parts")
            triples.append((m2(parts[0]), m2(parts[1]), m2(parts[2])))
        eqs.append(triples)
    return eqs


def read_modulus(text):
    m = re.search(r"F\s*=\s*QQ\[y\]/\((.*?)\)\s*\n", text, re.S)
    if not m:
        raise Refused("no F = QQ[y]/(...)")
    p = m2(m.group(1))
    coeffs = [Fraction(0)] * 28
    for k, v in p.t.items():
        if len(k) > 1 or (k and k[0][0] != "y"):
            raise Refused("the modulus is not a polynomial in y")
        e = k[0][1] if k else 0
        if e > 27:
            raise Refused("the modulus has degree above 27")
        coeffs[e] = v
    if coeffs[27] != 1 or any(c.denominator != 1 for c in coeffs):
        raise Refused("the modulus is not monic with integer coefficients")
    return [int(c) for c in coeffs]


def read_appendix_c(blob):
    files = tar_texts(blob)
    base = "Det3_borderRank17/"
    need = ["checkingType1eqns.m2", "checkingType2eqns.m2", "eqnsType1.m2", "eqnsType2.m2", "yy_exps.m2",
            "monomialsType1.m2", "monomialsType2.m2"]
    for n in need:
        if base + n not in files:
            raise Refused(f"Appendix C lacks {n}")
    mod1 = read_modulus(files[base + "checkingType1eqns.m2"])
    mod2 = read_modulus(files[base + "checkingType2eqns.m2"])
    if mod1 != mod2:
        raise Refused("Appendix C's two checking files define different fields")
    yy = m2_assignments(files[base + "yy_exps.m2"], "yy")
    if sorted(yy) != list(range(1, 45)):
        raise Refused(f"yy_exps defines {sorted(yy)[:5]}..., not yy_1..yy_44")
    e1 = m2_assignments(files[base + "eqnsType1.m2"], "e")
    e2 = m2_assignments(files[base + "eqnsType2.m2"], "e")
    mon1 = read_mon(files[base + "monomialsType1.m2"])
    mon2 = read_mon(files[base + "monomialsType2.m2"])
    if sorted(e1) != list(range(1, len(e1) + 1)) or sorted(e2) != list(range(1, len(e2) + 1)):
        raise Refused("equations not numbered 1..n")
    if len(mon1) != len(e1) or len(mon2) != len(e2):
        raise Refused("monomial lists and equations differ in number")
    return {"modulus": mod1, "yy": yy, "e1": e1, "e2": e2, "mon1": mon1, "mon2": mon2}


def read_appendix_b(blob):
    text = blob.decode("utf-8")
    forms = {}
    for k, body in re.findall(r"\nL_(\d+)\s*=\s*([^\n]*)", text):
        k = int(k)
        if k in forms:
            raise Refused(f"Appendix B defines L_{k} twice")
        p = m2(body)
        lin = [[ZERO] * 3 for _ in range(3)]
        for key, v in p.t.items():
            xs = [(n, e) for n, e in key if n.startswith("x")]
            rest = [(n, e) for n, e in key if not n.startswith("x")]
            if len(xs) != 1 or xs[0][1] != 1:
                raise Refused(f"Appendix B's L_{k} is not linear in x")
            c = QT(v)
            for n, e in rest:
                for _ in range(e):
                    c = c * (THETA if n == "a" else THETABAR if n == "b" else None)
            r, col = int(xs[0][0][1]), int(xs[0][0][2])
            lin[r][col] = lin[r][col] + c
        forms[k] = lin
    m = re.search(r"sum\(1\.\.18,\s*j->\s*L_j\^3\)\s*-\s*(\d+)\*det\(X\)", text)
    return [forms[k] for k in sorted(forms)], (int(m.group(1)) if m else None)


# ---------------------------------------------------------------- C1: cubic forms over Q(theta)

def lin_terms(mat):
    return [(3 * r + c, mat[r][c]) for r in range(3) for c in range(3) if not mat[r][c].iszero()]


def qt_poly_mul(p, q):
    r = {}
    for k1, v1 in p.items():
        for k2, v2 in q.items():
            k = tuple(a + b for a, b in zip(k1, k2))
            r[k] = r.get(k, ZERO) + v1 * v2
    return {k: v for k, v in r.items() if not v.iszero()}


def lin_poly(mat):
    p = {}
    for idx, c in lin_terms(mat):
        e = [0] * 9
        e[idx] = 1
        p[tuple(e)] = c
    return p


def cube_sum(mats):
    total = {}
    for m in mats:
        lp = lin_poly(m)
        cube = qt_poly_mul(qt_poly_mul(lp, lp), lp)
        for k, v in cube.items():
            total[k] = total.get(k, ZERO) + v
    return {k: v for k, v in total.items() if not v.iszero()}


def det_terms():
    """{exponent tuple: sign} of det(X), X = (x_rc), variable 3r + c."""
    out = {}
    for perm in permutations(range(3)):
        e = [0] * 9
        for r in range(3):
            e[3 * r + perm[r]] += 1
        out[tuple(e)] = perm_sign(perm)
    return out


def perm_sign(perm):
    s, p = 1, list(perm)
    for i in range(len(p)):
        while p[i] != i:
            j = p[i]
            p[i], p[j] = p[j], p[i]
            s = -s
    return s


def multiple_of_det(poly):
    """c if poly == c det(X) with c != 0, else None."""
    dt = det_terms()
    lead = tuple(1 if i in (0, 4, 8) else 0 for i in range(9))
    c = poly.get(lead, ZERO)
    if c.iszero():
        return None
    if set(poly) != set(dt):
        return None
    for k, s in dt.items():
        if not poly[k] == (c if s == 1 else -c):
            return None
    return c


# ---------------------------------------------------------------- C2: the system from the 17 forms

XN = [f"x{r}{c}" for r in range(3) for c in range(3)]


def form17_poly(mat):
    p = Poly()
    for r in range(3):
        for c in range(3):
            coef, z, tp = mat[r][c]
            if coef == 0:
                continue
            key = [(XN[3 * r + c], 1)]
            if z is not None:
                key.append((f"z{z}", 1))
            if tp:
                key.append(("t", tp))
            p = p + Poly({tuple(sorted(key)): Fraction(coef)})
    return p


def multinomial(xexp):
    m = 6
    for e in xexp:
        m //= math.factorial(e)
    return m


def system17(mats, c):
    total = Poly()
    for m in mats:
        lp = form17_poly(m)
        total = total + lp * lp * lp
    groups = {}
    for key, v in total.t.items():
        d = dict(key)
        tp = d.pop("t", 0)
        if tp > 2:
            continue
        xexp = tuple(d.pop(n, 0) for n in XN)
        zkey = tuple(sorted(d.items()))
        g = groups.setdefault((xexp, tp), {})
        g[zkey] = g.get(zkey, 0) + v
    dt = det_terms()
    eqs = {}
    for (xexp, tp), g in groups.items():
        p = Poly(g).scale(Fraction(1, multinomial(xexp)))
        eqs[(xexp, tp)] = p
    for xexp, s in dt.items():
        key = (xexp, 2)
        p = eqs.get(key, Poly())
        target = QT(c.a, c.b) if isinstance(c, QT) else QT(c)
        if target.b != 0:
            raise Refused("a multiple of det(X) outside Q cannot enter the system of rational equations")
        eqs[key] = p - Poly.const(target.a * s / multinomial(xexp))
    return {k: v for k, v in eqs.items() if not v.iszero()}


# ---------------------------------------------------------------- C2: the certificate, in F = Q[y]/(f) and K = F[u]/(u^3 - p)

class FE:
    """An element of Q[y]/(f): integer numerators of y^0..y^26 over a positive common denominator."""

    __slots__ = ("n", "d")
    MOD = None

    def __init__(self, nums, den=1):
        g = 0
        for x in nums:
            g = math.gcd(g, x)
        g = math.gcd(g, den)
        if g == 0:
            g = 1
        if den < 0:
            g = -g
        self.n = [x // g for x in nums]
        self.d = den // g

    @classmethod
    def from_poly(cls, p, var="y"):
        fr = [Fraction(0)] * 27
        hi = {}
        for key, v in p.t.items():
            d = dict(key)
            e = d.pop(var, 0)
            if d:
                raise Refused(f"an element of F with variables {sorted(d)}")
            if e < 27:
                fr[e] += v
            else:
                hi[e] = hi.get(e, 0) + v
        den = 1
        for x in list(fr) + list(hi.values()):
            den = den * x.denominator // math.gcd(den, x.denominator)
        nums = [int(x * den) for x in fr]
        if hi:
            conv = nums + [0] * (max(hi) - 26)
            for e, v in hi.items():
                conv[e] += int(v * den)
            nums = cls.reduce(conv)
        return cls(nums, den)

    @classmethod
    def reduce(cls, conv):
        f = cls.MOD
        conv = list(conv)
        for k in range(len(conv) - 1, 26, -1):
            c = conv[k]
            if c:
                conv[k] = 0
                for i in range(27):
                    if f[i]:
                        conv[k - 27 + i] -= c * f[i]
        return conv[:27] + [0] * max(0, 27 - len(conv))

    def __mul__(self, o):
        conv = [0] * 53
        for i, a in enumerate(self.n):
            if a:
                for j, b in enumerate(o.n):
                    if b:
                        conv[i + j] += a * b
        return FE(FE.reduce(conv), self.d * o.d)

    def __add__(self, o):
        return FE([a * o.d + b * self.d for a, b in zip(self.n, o.n)], self.d * o.d)

    def __neg__(self):
        return FE([-a for a in self.n], self.d)

    def __sub__(self, o):
        return self + (-o)

    def scale(self, c):
        c = Fraction(c)
        return FE([a * c.numerator for a in self.n], self.d * c.denominator)

    def iszero(self):
        return not any(self.n)

    def __eq__(self, o):
        return (self - o).iszero()

    def modp(self, p):
        inv = pow(self.d % p, -1, p)
        return [a * inv % p for a in self.n]


def fe_one():
    return FE([1] + [0] * 26)


def fe_zero():
    return FE([0] * 27)


class KE:
    """An element of F[u]/(u^3 - p): three coefficients in F."""

    __slots__ = ("c", "p")

    def __init__(self, coeffs, p):
        self.c, self.p = list(coeffs), p

    def __mul__(self, o):
        r = [fe_zero() for _ in range(5)]
        for i in range(3):
            if self.c[i].iszero():
                continue
            for j in range(3):
                if o.c[j].iszero():
                    continue
                r[i + j] = r[i + j] + self.c[i] * o.c[j]
        out = [r[0] + r[3] * self.p, r[1] + r[4] * self.p, r[2]]
        return KE(out, self.p)

    def __add__(self, o):
        return KE([a + b for a, b in zip(self.c, o.c)], self.p)

    def scale(self, k):
        return KE([a.scale(k) for a in self.c], self.p)

    def iszero(self):
        return all(a.iszero() for a in self.c)

    def __eq__(self, o):
        return all((a - b).iszero() for a, b in zip(self.c, o.c))


def ke_from_poly(poly, p):
    parts = {0: {}, 1: {}, 2: {}}
    extra = {}
    for key, v in poly.t.items():
        d = dict(key)
        e = d.pop("u", 0)
        rest = tuple(sorted(d.items()))
        (parts[e] if e < 3 else extra.setdefault(e, {}))[rest] = v
    out = KE([FE.from_poly(Poly(parts[i])) for i in range(3)], p)
    for e, terms in extra.items():
        q, r = divmod(e, 3)
        piece = FE.from_poly(Poly(terms))
        for _ in range(q):
            piece = piece * p
        add = [fe_zero(), fe_zero(), fe_zero()]
        add[r] = piece
        out = out + KE(add, p)
    return out


def monomial_cube(m, yy):
    """m, a monomial in the z's (Poly of one term), with each z_j replaced by yy_j: its cube's value in F."""
    if len(m.t) != 1:
        raise Refused("a triple's monomial is not a single term")
    (key, coef), = m.t.items()
    if coef != 1:
        raise Refused("a triple's monomial has a coefficient")
    val = fe_one()
    for n, e in key:
        if not n.startswith("z"):
            raise Refused(f"a monomial in {n}")
        for _ in range(e):
            val = val * yy[int(n[1:])]
    return val


def check_certificate(cert, yy):
    """Rule 3(b), every identity exactly. Returns counts and the failures."""
    out = {"type1": 0, "type2": 0, "cube_identities": 0, "cube_failures": [], "sum_failures": [],
           "equation_failures": [], "u_failures": []}
    for i, triples in enumerate(cert["mon1"], 1):
        ok = True
        total = fe_zero()
        poly = Poly()
        for m, e, k in triples:
            ev = FE.from_poly(e)
            out["cube_identities"] += 1
            if not (ev * ev * ev) == monomial_cube(m, yy):
                out["cube_failures"].append(f"type 1, e_{i}")
                ok = False
            total = total + ev.scale(k.constval())
            poly = poly + m.scale(k.constval())
        if not poly == cert["e1"][i]:
            out["sum_failures"].append(f"type 1, e_{i}")
            ok = False
        if not total.iszero():
            out["equation_failures"].append(f"type 1, e_{i}")
            ok = False
        out["type1"] += ok
    for i, triples in enumerate(cert["mon2"], 1):
        ok = True
        p = monomial_cube(triples[0][0], yy)
        if not triples[0][1] == Poly.var("u"):
            out["u_failures"].append(f"type 2, e_{i}")
            ok = False
        total = KE([fe_zero()] * 3, p)
        poly = Poly()
        for m, e, k in triples:
            ev = ke_from_poly(e, p)
            out["cube_identities"] += 1
            mc = KE([monomial_cube(m, yy), fe_zero(), fe_zero()], p)
            if not (ev * ev * ev) == mc:
                out["cube_failures"].append(f"type 2, e_{i}")
                ok = False
            total = total + ev.scale(k.constval())
            poly = poly + m.scale(k.constval())
        if not poly == cert["e2"][i]:
            out["sum_failures"].append(f"type 2, e_{i}")
            ok = False
        if not total.iszero():
            out["equation_failures"].append(f"type 2, e_{i}")
            ok = False
        out["type2"] += ok
    return out


def match_systems(derived, cert):
    """Rule 3(a): each derived equation a rational multiple of exactly one of the files' equations."""
    files = {}
    for kind in ("e1", "e2"):
        for i, p in cert[kind].items():
            files.setdefault(p.canonical(), []).append(f"{kind}_{i}")
    used, unmatched, ambiguous = set(), [], []
    for key, p in derived.items():
        hits = files.get(p.canonical(), [])
        if len(hits) == 1:
            used.add(hits[0])
        elif not hits:
            unmatched.append(key)
        else:
            ambiguous.append((key, hits))
    total = sum(len(v) for v in files.values())
    return {"derived": len(derived), "matched": len(derived) - len(unmatched) - len(ambiguous),
            "files_total": total, "files_used": len(used), "unmatched": unmatched, "ambiguous": ambiguous}


def field_generated(p, primes):
    """Q[p] = Q[y]: the matrix of p^0..p^26 in the basis y^0..y^26 has full rank modulo the primes."""
    ranks = []
    for q in primes:
        if p.d % q == 0:
            ranks.append(None)
            continue
        f = [c % q for c in FE.MOD]
        base = p.modp(q)

        def mulp(a, b):
            conv = [0] * 53
            for i, x in enumerate(a):
                if x:
                    for j, y in enumerate(b):
                        conv[i + j] = (conv[i + j] + x * y) % q
            for k in range(52, 26, -1):
                c = conv[k]
                if c:
                    conv[k] = 0
                    for i in range(27):
                        conv[k - 27 + i] = (conv[k - 27 + i] - c * f[i]) % q
            return conv[:27]

        rows, cur = [], [1] + [0] * 26
        for _ in range(27):
            rows.append(cur)
            cur = mulp(cur, base)
        ranks.append(rank_mod(rows, q))
    return ranks


def rank_mod(rows, q):
    m = [list(r) for r in rows]
    rank, ncol = 0, len(m[0]) if m else 0
    for col in range(ncol):
        piv = next((i for i in range(rank, len(m)) if m[i][col] % q), None)
        if piv is None:
            continue
        m[rank], m[piv] = m[piv], m[rank]
        inv = pow(m[rank][col], -1, q)
        m[rank] = [x * inv % q for x in m[rank]]
        for i in range(len(m)):
            if i != rank and m[i][col]:
                c = m[i][col]
                m[i] = [(x - c * y) % q for x, y in zip(m[i], m[rank])]
        rank += 1
    return rank


# ---------------------------------------------------------------- C3, C4: tensors and Koszul flattenings

def skewcw(q):
    if q % 2:
        raise Refused("T_skewcw,q needs even q")
    u = q // 2
    t = {}
    for j in range(1, q + 1):
        t[(0, j, j)] = t.get((0, j, j), 0) + 1
        t[(j, 0, j)] = t.get((j, 0, j), 0) + 1
    for xi in range(1, u + 1):
        t[(xi, xi + u, 0)] = t.get((xi, xi + u, 0), 0) + 1
        t[(xi + u, xi, 0)] = t.get((xi + u, xi, 0), 0) - 1
    return {k: Fraction(v) for k, v in t.items() if v}


def phi_skew(q):
    """The Proposition's map: a_0 -> e_0, a_1..a_u -> e_1, a_(u+1)..a_q -> e_2, q = 2u."""
    u = q // 2
    return [[1] + [0] * q, [0] + [1] * u + [0] * u, [0] + [0] * u + [1] * u]


def rank_q(rows):
    m = [[Fraction(x) for x in r] for r in rows]
    rank, ncol = 0, len(m[0]) if m else 0
    for col in range(ncol):
        piv = next((i for i in range(rank, len(m)) if m[i][col] != 0), None)
        if piv is None:
            continue
        m[rank], m[piv] = m[piv], m[rank]
        pv = m[rank][col]
        m[rank] = [x / pv for x in m[rank]]
        for i in range(len(m)):
            if i != rank and m[i][col] != 0:
                c = m[i][col]
                m[i] = [x - c * y for x, y in zip(m[i], m[rank])]
        rank += 1
    return rank


def koszul_rank(t, dims, phi, p):
    """Rank of the p-th Koszul flattening of phi(T) on A': Lambda^p A' (x) B* -> Lambda^(p+1) A' (x) C."""
    na, nb, nc = dims
    na2 = len(phi)
    tp = {}
    for (i, j, k), v in t.items():
        for i2 in range(na2):
            if phi[i2][i]:
                key = (i2, j, k)
                tp[key] = tp.get(key, 0) + phi[i2][i] * v
    from itertools import combinations
    dom = [(s, j) for s in combinations(range(na2), p) for j in range(nb)]
    cod = {(s, k): n for n, (s, k) in enumerate((s, k) for s in combinations(range(na2), p + 1) for k in range(nc))}
    rows = [[0] * len(dom) for _ in range(len(cod))]
    for col, (s, j) in enumerate(dom):
        for (i2, jj, k), v in tp.items():
            if jj != j or v == 0 or i2 in s:
                continue
            new = (i2,) + s
            order = sorted(new)
            sign = perm_sign([order.index(x) for x in new])
            rows[cod[(tuple(order), k)]][col] += sign * v
    return rank_q(rows)


def identify(t, q):
    """The TeX's identification of B and C with A: b_0 -> -a_0, b_j -> a_j, c_0 -> a_0, c_(u+j) -> -a_j,
    c_j -> a_(u+j)."""
    u = q // 2

    def bmap(j):
        return (0, -1) if j == 0 else (j, 1)

    def cmap(k):
        if k == 0:
            return (0, 1)
        if k > u:
            return (k - u, -1)
        return (k + u, 1)

    out = {}
    for (i, j, k), v in t.items():
        jb, sb = bmap(j)
        kc, sc = cmap(k)
        key = (i, jb, kc)
        out[key] = out.get(key, 0) + v * sb * sc
    return {k: v for k, v in out.items() if v}


def eps_multiple(t):
    eps = {p: perm_sign(p) for p in permutations(range(3))}
    lam = t.get((0, 1, 2), 0)
    if lam == 0 or set(t) != set(eps):
        return None
    return lam if all(t[p] == lam * s for p, s in eps.items()) else None


def kron_square_form(t):
    """T (x) T with paired indices: (symmetric?, its cubic form as {exponent tuple: coefficient})."""
    k2 = {}
    for (i, j, k), v in t.items():
        for (i2, j2, k2_), w in t.items():
            k2[(3 * i + i2, 3 * j + j2, 3 * k + k2_)] = v * w
    symmetric = all(k2.get(tuple(p), 0) == v for key, v in k2.items() for p in permutations(key))
    form = {}
    for (a, b, c), v in k2.items():
        e = [0] * 9
        for x in (a, b, c):
            e[x] += 1
        form[tuple(e)] = form.get(tuple(e), 0) + v
    return symmetric, {k: v for k, v in form.items() if v}


# ---------------------------------------------------------------- beside: Johns & Teitler's case d = 3

def jt_terms(omega, scale_col=1, transpose=False):
    """(-1)^sigma (sum_i omega^(ij) x_(i,sigma(i)))^3, i, j = 1..3, column scale_col divided by 3."""
    out = []
    for perm in permutations(range(3)):
        sgn = perm_sign(perm)
        for j in range(1, 4):
            mat = [[ZERO] * 3 for _ in range(3)]
            for r in range(3):
                c = perm[r]
                w = ONE
                for _ in range((r + 1) * j):
                    w = w * omega
                if c == scale_col:
                    w = w * QT(Fraction(1, 3))
                if transpose:
                    mat[c][r] = w
                else:
                    mat[r][c] = w
            out.append((sgn, mat))
    return out


def jt_match(forms):
    w = THETA * THETA
    roots = [ONE]
    for _ in range(5):
        roots.append(roots[-1] * THETA)
    results = []
    for oname, omega in (("omega", w), ("omega-bar", w * w)):
        for transpose in (False, True):
            terms = jt_terms(omega, 1, transpose)
            used = [False] * len(terms)
            hits = 0
            for f in forms:
                for idx, (sgn, mat) in enumerate(terms):
                    if used[idx]:
                        continue
                    ok = False
                    for z in roots:
                        z3 = z * z * z
                        if not (z3 == QT(sgn)):
                            continue
                        if all(f[r][c] == z * mat[r][c] for r in range(3) for c in range(3)):
                            ok = True
                            break
                    if ok:
                        used[idx] = True
                        hits += 1
                        break
            results.append({"omega": oname, "transpose": transpose, "matched": hits})
    return results


# ---------------------------------------------------------------- numerics (beside and control 3)

def real_roots(modulus, mp):
    import numpy as np
    coeffs = [float(c) for c in reversed(modulus)]
    approx = np.roots(coeffs)
    cands = sorted(r.real for r in approx if abs(r.imag) < 1e-6 * max(1.0, abs(r)))
    f = lambda x: sum(mp.mpf(c) * x ** i for i, c in enumerate(modulus))  # noqa: E731
    roots = []
    for c in cands:
        r = mp.findroot(f, mp.mpf(c))
        if abs(mp.im(r)) == 0 and all(abs(r - s) > mp.mpf(10) ** -50 for s in roots):
            roots.append(mp.re(r))
    return len(cands), roots


def residuals(system, yy_polys, root, mp):
    def ev(poly, vals):
        tot = mp.mpf(0)
        for key, v in poly.t.items():
            term = mp.mpf(v.numerator) / v.denominator
            for n, e in key:
                term *= vals[n] ** e
            tot += term
        return tot

    zs = {}
    for j, p in yy_polys.items():
        y = ev(p, {"y": root})
        zs[f"z{j}"] = mp.sign(y) * abs(y) ** (mp.mpf(1) / 3)
    worst = mp.mpf(0)
    for p in system.values():
        worst = max(worst, abs(ev(p, zs)))
    return worst


# ---------------------------------------------------------------- run

def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    import mpmath
    files = tar_texts(read_input(inputs, EPRINT))
    if TEXNAME not in files:
        raise Refused(f"the e-print lacks {TEXNAME}")
    tex = files[TEXNAME]
    forms18 = read_forms18(tex)
    forms17 = read_forms17(tex)
    tex_poly = read_tex_polynomial(tex)
    appb_forms, appb_multiple = read_appendix_b(read_input(inputs, APPB))
    cert = read_appendix_c(read_input(inputs, APPC))
    FE.MOD = cert["modulus"][:27]
    yy = {j: FE.from_poly(p) for j, p in cert["yy"].items()}

    # C1
    s18 = cube_sum(forms18)
    c1 = multiple_of_det(s18)
    c1_ok = c1 is not None
    c_used = c1 if (c1_ok and c1.b == 0) else QT(6)

    # C2
    system = system17(forms17, c_used)
    match = match_systems(system, cert)
    certificate = check_certificate(cert, yy)
    c2a = (match["matched"] == match["derived"] and match["files_used"] == match["files_total"]
           and not match["ambiguous"])
    c2b = (certificate["type1"] == len(cert["mon1"]) and certificate["type2"] == len(cert["mon2"]))
    c2_ok = c2a and c2b

    # C3
    q = 2
    r3 = koszul_rank(skewcw(q), (q + 1, q + 1, q + 1), phi_skew(q), 1)
    c3_bound = -(-r3 // 2)
    c3_ok = r3 == 9 and c3_bound >= 5 and 17 < c3_bound ** 2

    # C4
    tprime = identify(skewcw(2), 2)
    lam = eps_multiple(tprime)
    sym, form = kron_square_form(tprime)
    c4_mult = None
    if form:
        fpoly = {k: QT(v) for k, v in form.items()}
        c4_mult = multiple_of_det(fpoly)
    c4_ok = lam is not None and sym and c4_mult is not None and c4_mult == c_used

    conds = {"C1": c1_ok, "C2": c2_ok, "C3": c3_ok, "C4": c4_ok}
    met = sum(conds.values())

    # beside
    appb_same = sum(1 for a, b in zip(appb_forms, forms18) if all(a[r][c] == b[r][c] for r in range(3)
                                                                  for c in range(3)))
    poly_same = tex_poly == cert["modulus"]
    unknowns = sorted({n for p in list(cert["e1"].values()) + list(cert["e2"].values()) for n in p.names()})
    skew_ranks = {}
    for qq in range(2, 21, 2):
        skew_ranks[qq] = koszul_rank(skewcw(qq), (qq + 1, qq + 1, qq + 1), phi_skew(qq), 1)
    skew_all = all(v == 2 * k + 5 for k, v in skew_ranks.items())
    gen = [field_generated(monomial_cube(tr[0][0], yy), PRIMES) for tr in cert["mon2"]]
    gen_full = sum(1 for g in gen if 27 in g)
    jt = jt_match(forms18)
    jt_best = max(jt, key=lambda r: r["matched"])
    try:
        import sympy
        ysym = sympy.Symbol("y")
        exact_real = int(sympy.Poly([int(c) for c in reversed(cert["modulus"])], ysym).count_roots())
    except Exception as e:  # noqa: BLE001
        exact_real = f"sympy failed: {e}"
    mpmath.mp.dps = 120
    n_cands, roots = real_roots(cert["modulus"], mpmath.mp)
    res = [residuals(system, cert["yy"], r, mpmath.mp) for r in roots]

    # controls
    controls = {}
    bad = [[[x for x in row] for row in m] for m in forms18]
    bad[0][1][1] = QT(Fraction(-1, 2))
    controls["a changed entry of L_1 breaks the multiple of det(X)"] = multiple_of_det(cube_sum(bad)) is None
    yy_bad = dict(yy)
    yy_bad[1] = yy[1].scale(2)
    cb = check_certificate(cert, yy_bad)
    controls["doubling yy_1 breaks an identity of the certificate"] = bool(cb["cube_failures"] or
                                                                          cb["equation_failures"])
    st = Stream(seed, "point")
    mpmath.mp.dps = 60
    x0 = [[mpmath.mpc(st.below(19) - 9, st.below(19) - 9) for _ in range(3)] for _ in range(3)]
    tot = mpmath.mpc(0)
    for m in forms18:
        lv = sum(qt_complex(m[r][c], mpmath.mp) * x0[r][c] for r in range(3) for c in range(3))
        tot += lv ** 3
    det0 = mpmath.det(mpmath.matrix(x0))
    num_c1 = abs(tot - qt_complex(c_used, mpmath.mp) * det0)
    mpmath.mp.dps = 120
    controls["numerically, the 18 cubes and the system of rule 3 agree with the exact verdicts"] = (
        (num_c1 < mpmath.mpf(10) ** -40) == c1_ok and bool(roots) and
        all(r < mpmath.mpf(10) ** -80 for r in res) == c2b)
    unit3 = {(i, i, i): Fraction(1) for i in range(3)}
    st2 = Stream(seed, "restriction")
    cols = []
    while len(cols) < 5:
        col = [st2.below(19) - 9 for _ in range(3)]
        if any(col):
            cols.append(col)
    phi5 = [[cols[j][i] for j in range(5)] for i in range(3)]
    unit5 = {(i, i, i): Fraction(1) for i in range(5)}
    controls["the Koszul flattening of unit tensors has rank 2r"] = (
        koszul_rank(unit3, (3, 3, 3), [[1, 0, 0], [0, 1, 0], [0, 0, 1]], 1) == 6 and
        koszul_rank(unit5, (5, 5, 5), phi5, 1) == 10)
    cpass = sum(controls.values())

    def short(v):
        return str(v.a) if isinstance(v, QT) and v.b == 0 else (repr(v) if v is not None else "none")

    out = {
        "waring_18": (f"sum of the 18 cubes = {short(c1)} det(X)" if c1_ok else "the 18 cubes do not sum to a "
                      "multiple of det(X)"),
        "waring_18_multiple": short(c1),
        "border_17_system": f"{match['derived']} equations from the 17 forms, {match['matched']} matched to the "
                            f"files' {match['files_total']}",
        "border_17_certificate": f"type 1 {certificate['type1']} of {len(cert['mon1'])}, type 2 "
                                 f"{certificate['type2']} of {len(cert['mon2'])}; {certificate['cube_identities']} "
                                 "cube identities",
        "skew_flattening_rank": r3,
        "skew_border_rank_bound": c3_bound,
        "kron_square": (f"T' = {lam} eps; its Kronecker square symmetric: {sym}; cubic form "
                        f"{short(c4_mult)} det(X)"),
        "appendix_b": f"{appb_same} of 18 forms as in the TeX; its last line names {appb_multiple} det(X)",
        "polynomial": "the TeX's degree-27 polynomial is Appendix C's modulus" if poly_same else
                      "the TeX's degree-27 polynomial differs from Appendix C's",
        "real_roots": f"{exact_real} (sympy, exactly); {n_cands} by numpy.roots, {len(roots)} refined",
        "residual_log10": int(math.floor(mpmath.log10(max(res)))) if res and max(res) > 0 else -999,
        "printed_counts": (f"system {match['derived']} (printed {PRINTED['equations']}), unknowns {len(unknowns)} "
                           f"(printed {PRINTED['unknowns']}), type 1 {len(cert['e1'])} (printed "
                           f"{PRINTED['type1']}), type 2 {len(cert['e2'])} (printed {PRINTED['type2']})"),
        "field_generation": f"Q[p] = Q[y*] for {gen_full} of {len(gen)} type 2 equations",
        "skew_ranks": "rank 2q + 5 for every even q from 2 to 20" if skew_all else
                      "not 2q + 5 at q = " + ", ".join(str(k) for k, v in skew_ranks.items() if v != 2 * k + 5),
        "johns_teitler": (f"{jt_best['matched']} of 18 forms are their d = 3 terms (column 2 over 3, "
                          f"{jt_best['omega']}{', transposed' if jt_best['transpose'] else ''})"),
        "conditions_met": met,
        "conditions_total": 4,
        "test_passed": int(met == 4),
        "controls_passed": cpass,
        "controls_total": len(controls),
    }
    for k, v in out.items():
        if isinstance(v, str) and len(v) > 200:
            raise Refused(f"output {k} is longer than 200 characters")
    detail = {
        "inputs": [list(EPRINT), list(APPB), list(APPC)],
        "conditions": conds, "controls": controls, "c1_multiple": short(c1),
        "system_keys": [[list(k[0]), k[1]] for k in sorted(system)],
        "match": {k: (v if not isinstance(v, list) else [str(x) for x in v]) for k, v in match.items()},
        "certificate": certificate, "skew_ranks": skew_ranks, "field_generation_ranks": gen,
        "johns_teitler": jt, "real_root_values": [mpmath.nstr(r, 30) for r in roots],
        "residuals": [mpmath.nstr(r, 5) for r in res], "numeric_c1": mpmath.nstr(num_c1, 5),
        "unknowns": unknowns, "tex_polynomial": tex_poly, "appendix_b_multiple": appb_multiple,
    }
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
        sys.exit(f"cglv2019: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
