#!/usr/bin/env python3
"""Sedoglavic & Smirnov's 3 x 5 by 5 x 5 product in 58 multiplications, read from the trilinear form their e-print
prints and checked exactly; beside it, their partial approximate tensor for the border rank 89 of 5 x 5.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:2123dbcba4145ebe) is from Sedoglavic and
Smirnov, "The tensor rank of 5x5 matrices multiplication is bounded by 98 and its border rank by 89" (ISSAC 2021,
345-351; arXiv:2101.12568v2): "We present a non-commutative algorithm for the product of 3x5 by 5x5 matrices using 58
multiplications."

Its registered test: refuted if the trilinear form the paper's e-print prints for <3x5x5:58> (its thirteen expressions
tau_222 ... tau_111, read from the TeX as printed) is not a sum of exactly 58 products, each of a linear form in A's
entries, one in B's and one in C's, or if that sum differs from sum a_ij b_jk c_ki (i <= 3; j, k <= 5), the trace form
the paper uses, in any of the 15 x 25 x 15 = 5,625 coefficients over the integers.

The input is the paper's e-print from arXiv (a gzipped tar), checked against its SHA-256 and read as data (unpacked in
memory with the standard library; nothing in it is run). Python's standard library only, exact integers and fractions.
Every rule below was fixed before the printed scheme was parsed or checked; the seed is not used, as nothing here is
random.

1. The source: the member 3x5x5_58.tex must hold the paragraph "Trilinear form of <3x5x5:58>" up to "Induced
   geometry", whose equation blocks that begin "tau_{xyz}=" are the scheme, and the section on the partial approximate
   tensor T_epsilon from the paragraph on its type up to its remark on serendipitous equalities, whose blocks that
   begin "rho_{xyz}=" are that tensor; otherwise the run is refused.
2. Reading the TeX: comments, labels, alignment marks, line breaks, \\left, \\right and spacing commands removed;
   a_{ij}, b_{ij}, c_{ij} read as the variables a_ij, b_ij, c_ij, \\epsilon as e. What is left is parsed as an
   algebraic expression: sums and differences of products of factors written side by side, a factor being a variable,
   e, a number, a parenthesised or braced expression, or \\frac{numerator}{denominator}, each with an optional power;
   a denominator must be a power of e times a number. Each block's right-hand side is a sum of terms; each term is a
   product whose factors free of variables (signs, powers of e) are its scalar, and whose other factors must be
   exactly one linear form in a's, one in b's and one in c's (a product that is not is counted against condition 2).
3. The scheme (the test): conditions (1) exactly 58 products over the thirteen blocks; (2) every one of them a product
   of one linear form in A's entries (a_ij, i <= 3, j <= 5), one in B's (b_jk, j, k <= 5) and one in C's (c_ki,
   k <= 5, i <= 3), with integer coefficients; (3) their sum, expanded exactly, equal to sum a_ij b_jk c_ki in each of
   the 5,625 coefficients of a_ij b_jk c_ki-space (15 x 25 x 15). test_passed is 1 if all three hold.
4. Beside the test (reported, not tested): the products in each block; each product's type, the ranks of its three
   coefficient matrices (3 x 5, 5 x 5 and 5 x 3, exact ranks over the rationals), against the block's name and the
   printed type polynomial (17 X^2Y^2Z^2 + 2 XY^4Z + ... + 7 XYZ); the pairs of products sharing a factor up to sign
   (the paper's 8 "serendipitous equalities"); and the partial approximate tensor: its products (the printed type
   counts 55), and whether, expanded in e, it has no negative power of e and its e^0 part is exactly
   sum a_ij b_jk c_ki over all i, j, k <= 5 except the nine (i <= 3, 3 <= j <= 5) where a_ij = 0, as the paper says;
   with the counts that build the paper's other bounds: 40 + 58 = 98, 7 x 98 = 686, 58 x 36 = 2088 and
   55 + 20 + 14 = 89 (the 40, 36, 20 and 14 are schemes from elsewhere, not checked here).
5. Controls, which must all pass or the run stops: the reader and the check accept Strassen's algorithm as the paper's
   convention writes it (written out below, not read from the e-print) in 7 products and find two wrong coefficients
   when one of its signs is flipped; the naive 3 x 5 by 5 x 5 algorithm, 75 products, is exact and with one product
   left out has one wrong coefficient; and the approximate reading accepts the border rank 2 expression of
   a11 b11 c12 + a11 b12 c11 + a12 b11 c11 (e^-1 (a11 + e a12)(b11 + e b12)(c11 + e c12) - e^-1 a11 b11 c11, written in
   the paper's style) and finds a negative power of e when its last term is left out.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 mm/ss.py
"""

import hashlib
import io
import json
import os
import re
import sys
import tarfile
from collections import defaultdict
from fractions import Fraction

INPUT = ("arXiv-2101.12568v2.tar.gz", "bab114ec8ae73ed65118ad1423caaf6d53c54ebaf2dcffcf8c79a3900c2b8e78")
TEX = "3x5x5_58.tex"
SCHEME = (r"\paragraph{Trilinear form of~$\FMMA{3}{5}{5}{58}$.}", r"\paragraph{Induced geometry}")
APPROX = (r"\paragraph{The type of~$\tensor{T}_{\epsilon}$}",
          r"Remark that there is~$4$ serendipitous equalities in this tensor.")
BLOCKS = ("222", "141", "321", "123", "311", "113", "221", "122", "131", "211", "112", "121", "111")
APPROX_BLOCKS = ("222", "221", "212", "122", "211", "121", "112", "111")
PRINTED_TYPE = {(2, 2, 2): 17, (1, 4, 1): 2, (3, 2, 1): 1, (1, 2, 3): 1, (3, 1, 1): 5, (1, 1, 3): 5, (2, 2, 1): 2,
                (1, 2, 2): 2, (1, 3, 1): 1, (2, 1, 1): 1, (1, 1, 2): 1, (1, 2, 1): 13, (1, 1, 1): 7}
PRODUCTS, APPROX_PRINTED = 58, 55
SHAPE = (3, 5, 5)                          # A is 3 x 5, B 5 x 5, C 5 x 3
ZERO_BLOCK = {(i, j) for i in range(1, 4) for j in range(3, 6)}
LIMIT = 200
OUTPUTS = ("source", "products", "block_counts", "trilinear", "wrong_coefficients", "types", "type_polynomial",
           "serendipitous", "approx_products", "approx_negative", "approx_wrong", "approx_exact", "composites",
           "conditions_met", "conditions_total", "test_passed", "controls_passed", "controls_total")

STRASSEN = r"""
{a_{11}}\left({b_{12}}-{b_{22}}\right)\left({c_{21}}+{c_{22}}\right)\\
+\left({a_{11}}+{a_{12}}\right){b_{22}}\left(-{c_{11}}+{c_{21}}\right)\\
+\left({a_{21}}+{a_{22}}\right){b_{11}}\left({c_{12}}-{c_{22}}\right)\\
+\left({a_{12}}-{a_{22}}\right)\left({b_{21}}+{b_{22}}\right){c_{11}}\\
+\left({a_{11}}+{a_{22}}\right)\left({b_{11}}+{b_{22}}\right)\left({c_{11}}+{c_{22}}\right)\\
+{a_{22}}\left({b_{21}}-{b_{11}}\right)\left({c_{11}}+{c_{12}}\right)\\
+\left({a_{21}}-{a_{11}}\right)\left({b_{11}}+{b_{12}}\right){c_{22}}.
"""
W_STATE = (r"\frac{a_{11}}{\epsilon}\left(b_{11}+b_{12}\epsilon\right)\left(c_{11}+c_{12}{\epsilon}\right)"
           r"+&a_{12}\left(b_{11}+b_{12}\epsilon\right)\left(c_{11}+c_{12}\epsilon\right)"
           r"-&\frac{a_{11}}{\epsilon}b_{11}c_{11}")


class Refused(Exception):
    pass


# --- reading (rules 1 and 2) -----------------------------------------------------------------------------------------

def read_bytes(path, sha256):
    with open(path, "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha256:
        raise Refused(f"{path}: sha256 {got}, not the registered {sha256}")
    return data


def tex_of(eprint):
    try:
        with tarfile.open(fileobj=io.BytesIO(eprint), mode="r:gz") as t:
            member = t.getmember(TEX)
            return t.extractfile(member).read().decode("utf-8")
    except KeyError:
        raise Refused(f"the e-print holds no {TEX}") from None
    except (tarfile.TarError, OSError, EOFError, UnicodeDecodeError) as e:
        raise Refused(f"the e-print is not a readable gzipped tar: {e}") from None


def region(tex, marks):
    start = tex.find(marks[0])
    end = tex.find(marks[1], start + 1)
    if start < 0 or end < 0:
        raise Refused(f"the TeX does not hold {marks[0]!r} ... {marks[1]!r}")
    return tex[start:end]


def blocks(text, name):
    """The equation blocks of a region that begin '<name>_{xyz}=', as {xyz: right-hand side}, in order."""
    out = {}
    for body in re.findall(r"\\begin\{equation\}(.*?)\\end\{equation\}", text, re.S):
        flat = normalise(body)
        m = re.match(r"\\" + name + r"_\{(\d{3})\}=(.*)$", flat)
        if m:
            if m.group(1) in out:
                raise Refused(f"{name}_{m.group(1)} printed twice")
            out[m.group(1)] = m.group(2)
    return out


def normalise(tex):
    lines = [re.sub(r"(?<!\\)%.*$", "", line) for line in tex.split("\n")]
    s = " ".join(lines)
    s = re.sub(r"\\label\{[^}]*\}", "", s)
    for w in (r"\begin{split}", r"\end{split}", r"\begin{aligned}", r"\end{aligned}"):
        s = s.replace(w, "")
    s = s.replace("\\\\", " ").replace("&", "").replace(r"\!", "").replace(r"\,", "")
    s = s.replace(r"\left", "").replace(r"\right", "")
    s = re.sub(r"([abc])_\{(\d)(\d)\}", r"\1\2\3", s)
    s = s.replace(r"\epsilon", "e")
    s = re.sub(r"\s+", "", s)
    return s.replace(".", "").replace(",", "")


TOKEN = re.compile(r"\\frac|[abc]\d\d|e|\d+|[-+(){}^]")


def tokens(s):
    out, pos = [], 0
    while pos < len(s):
        m = TOKEN.match(s, pos)
        if not m:
            raise Refused(f"cannot read the TeX at {s[pos:pos + 40]!r}")
        out.append(m.group(0))
        pos = m.end()
    return out


# Polynomials: {(variables, power of e): coefficient}, variables a sorted tuple.

def pmul(p, q):
    out = defaultdict(Fraction)
    for (v1, e1), c1 in p.items():
        for (v2, e2), c2 in q.items():
            out[(tuple(sorted(v1 + v2)), e1 + e2)] += c1 * c2
    return {k: c for k, c in out.items() if c}


def padd(p, q, sign=1):
    out = defaultdict(Fraction, p)
    for k, c in q.items():
        out[k] += sign * c
    return {k: c for k, c in out.items() if c}


ONE = {((), 0): Fraction(1)}


class Parser:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self, want=None):
        tok = self.peek()
        if tok is None or (want is not None and tok != want):
            raise Refused(f"expected {want!r} at token {self.i}, found {tok!r}")
        self.i += 1
        return tok

    def terms(self, stop=(None, ")", "}")):
        """A sum: [(sign, [factor polynomials])]."""
        out, sign = [], 1
        if self.peek() in ("+", "-"):
            sign = -1 if self.take() == "-" else 1
        while True:
            factors = []
            while self.peek() not in ("+", "-") + stop:
                factors.append(self.factor())
            if not factors:
                raise Refused(f"an empty term at token {self.i}")
            out.append((sign, factors))
            if self.peek() in ("+", "-"):
                sign = -1 if self.take() == "-" else 1
                continue
            return out

    def poly(self, stop):
        total = {}
        for sign, factors in self.terms(stop):
            prod = ONE
            for f in factors:
                prod = pmul(prod, f)
            total = padd(total, prod, sign)
        return total

    def factor(self):
        tok = self.take()
        if tok == "(":
            p = self.poly((")",))
            self.take(")")
        elif tok == "{":
            p = self.poly(("}",))
            self.take("}")
        elif tok == r"\frac":
            self.take("{")
            num = self.poly(("}",))
            self.take("}")
            self.take("{")
            den = self.poly(("}",))
            self.take("}")
            if len(den) != 1 or next(iter(den))[0] != ():
                raise Refused("a denominator that is not a power of e")
            (_, k), c = next(iter(den.items()))
            p = {(v, e - k): x / c for (v, e), x in num.items()}
        elif tok == "e":
            p = {((), 1): Fraction(1)}
        elif tok.isdigit():
            p = {((), 0): Fraction(int(tok))}
        elif re.fullmatch(r"[abc]\d\d", tok):
            p = {((tok,), 0): Fraction(1)}
        else:
            raise Refused(f"unexpected {tok!r} at token {self.i - 1}")
        if self.peek() == "^":
            self.take("^")
            if self.peek() == "{":
                self.take("{")
                n = int(self.take())
                self.take("}")
            else:
                n = int(self.take())
            q = ONE
            for _ in range(n):
                q = pmul(q, p)
            p = q
        return p


def products_of(rhs):
    """The products of one block: [(scalar, {letter: {variable: {power: coefficient}}})] or a reason it is not one."""
    parser = Parser(tokens(rhs))
    terms = parser.terms()
    if parser.peek() is not None:
        raise Refused(f"unread tokens from {parser.i}")
    out = []
    for sign, factors in terms:
        scalar, forms, bad = {((), 0): Fraction(sign)}, {}, None
        for f in factors:
            if all(not v for (v, _) in f):
                scalar = pmul(scalar, f)
                continue
            if any(len(v) != 1 for (v, _) in f) or len({v[0][0] for (v, _) in f}) != 1:
                bad = "a factor that is not a linear form in one matrix's entries"
                continue
            letter = next(iter(f))[0][0][0]
            if letter in forms:
                bad = f"two factors in {letter}"
                continue
            form = defaultdict(dict)
            for (v, e), c in f.items():
                form[v[0]][e] = c
            forms[letter] = dict(form)
        if bad is None and set(forms) != {"a", "b", "c"}:
            bad = "not one form in each of A, B and C"
        out.append({"scalar": {e: c for (_, e), c in scalar.items()}, "forms": forms, "bad": bad})
    return out


# --- the exact check (rule 3) ----------------------------------------------------------------------------------------

def target(m, n, p, zero=frozenset()):
    return {(f"a{i}{j}", f"b{j}{k}", f"c{k}{i}"): 1
            for i in range(1, m + 1) for j in range(1, n + 1) for k in range(1, p + 1) if (i, j) not in zero}


def in_range(var, m, n, p):
    i, j = int(var[1]), int(var[2])
    rows, cols = {"a": (m, n), "b": (n, p), "c": (p, m)}[var[0]]
    return 1 <= i <= rows and 1 <= j <= cols


def integer_form(prod):
    """Exact products only: {letter: {variable: integer}} with the scalar folded into a; None if not integral."""
    if prod["bad"] or set(prod["scalar"]) != {0}:
        return None
    s = prod["scalar"][0]
    out = {}
    for letter in "abc":
        form = {}
        for v, powers in prod["forms"][letter].items():
            if set(powers) != {0}:
                return None
            c = powers[0] * (s if letter == "a" else 1)
            if c.denominator != 1:
                return None
            form[v] = int(c)
        out[letter] = form
    return out


def wrong_count(forms, m, n, p):
    """The coefficients of the expanded sum that differ from the m x n by n x p product's tensor."""
    total = defaultdict(int)
    for f in forms:
        for x, ca in f["a"].items():
            for y, cb in f["b"].items():
                for z, cc in f["c"].items():
                    total[(x, y, z)] += ca * cb * cc
    want = target(m, n, p)
    keys = set(total) | set(want)
    return sum(1 for k in keys if total.get(k, 0) != want.get(k, 0))


def expand_approx(prods):
    """sum of the products as {(x, y, z): {power of e: coefficient}}."""
    total = defaultdict(lambda: defaultdict(Fraction))
    for prod in prods:
        if prod["bad"]:
            continue
        sa, fa, fb, fc = prod["scalar"], prod["forms"]["a"], prod["forms"]["b"], prod["forms"]["c"]
        for x, px in fa.items():
            for y, py in fb.items():
                for z, pz in fc.items():
                    for e0, c0 in sa.items():
                        for e1, c1 in px.items():
                            for e2, c2 in py.items():
                                for e3, c3 in pz.items():
                                    total[(x, y, z)][e0 + e1 + e2 + e3] += c0 * c1 * c2 * c3
    return total


def approx_check(prods, m, n, p, zero):
    """(monomials with a nonzero negative power of e, monomials whose e^0 coefficient is wrong), a_ij in the zero
    block left out, as the paper sets those entries to 0."""
    total = expand_approx(prods)
    want = target(m, n, p, zero)
    negative = wrong = 0
    for key in set(total) | set(want):
        a = key[0]
        if (int(a[1]), int(a[2])) in zero:
            continue
        powers = total.get(key, {})
        if any(c and e < 0 for e, c in powers.items()):
            negative += 1
        if powers.get(0, 0) != want.get(key, 0):
            wrong += 1
    return negative, wrong


# --- beside: types and shared factors (rule 4) ------------------------------------------------------------------------

def rank(rows):
    """Exact rank over the rationals."""
    m = [[Fraction(x) for x in r] for r in rows]
    r = 0
    cols = len(m[0]) if m else 0
    for c in range(cols):
        piv = next((i for i in range(r, len(m)) if m[i][c] != 0), None)
        if piv is None:
            continue
        m[r], m[piv] = m[piv], m[r]
        for i in range(len(m)):
            if i != r and m[i][c] != 0:
                f = m[i][c] / m[r][c]
                m[i] = [a - f * b for a, b in zip(m[i], m[r])]
        r += 1
    return r


def matrix(form, rows, cols):
    out = [[0] * cols for _ in range(rows)]
    for v, c in form.items():
        out[int(v[1]) - 1][int(v[2]) - 1] = c
    return out


def type_of(f, m=3, n=5, p=5):
    return (rank(matrix(f["a"], m, n)), rank(matrix(f["b"], n, p)), rank(matrix(f["c"], p, m)))


def shared_pairs(forms):
    def key(form):
        items = sorted(form.items())
        if not items:
            return ()
        s = 1 if items[0][1] > 0 else -1
        return tuple((v, s * c) for v, c in items)
    count = 0
    for r in range(len(forms)):
        for s in range(r + 1, len(forms)):
            if any(key(forms[r][x]) == key(forms[s][x]) for x in "abc"):
                count += 1
    return count


def controls_known():
    strassen = [integer_form(x) for x in products_of(normalise(STRASSEN))]
    ok_strassen = len(strassen) == 7 and all(strassen) and wrong_count(strassen, 2, 2, 2) == 0
    flipped = [integer_form(x) for x in products_of(normalise(STRASSEN.replace(r"-{c_{11}}+{c_{21}}",
                                                                                r"+{c_{11}}+{c_{21}}")))]
    ok_flip = all(flipped) and wrong_count(flipped, 2, 2, 2) == 2
    naive = [{"a": {f"a{i}{j}": 1}, "b": {f"b{j}{k}": 1}, "c": {f"c{k}{i}": 1}}
             for i in range(1, 4) for j in range(1, 6) for k in range(1, 6)]
    ok_naive = len(naive) == 75 and wrong_count(naive, 3, 5, 5) == 0 and wrong_count(naive[1:], 3, 5, 5) == 1
    w = products_of(normalise(W_STATE))
    w_target = {"a11b11c12", "a11b12c11", "a12b11c11"}

    def w_errors(prods):
        total = expand_approx(prods)
        neg = sum(1 for powers in total.values() if any(c and e < 0 for e, c in powers.items()))
        zero = {"".join(k): powers.get(0, 0) for k, powers in total.items()}
        wrong = sum(1 for k in set(zero) | w_target if zero.get(k, 0) != (1 if k in w_target else 0))
        return neg, wrong
    ok_w = len(w) == 3 and w_errors(w) == (0, 0) and w_errors(w[:2])[0] > 0
    return {"Strassen's algorithm, as the paper's convention writes it, is read as 7 exact products": ok_strassen,
            "with one of Strassen's signs flipped, two coefficients are wrong": ok_flip,
            "the naive 3x5 by 5x5 algorithm is exact in 75 products, with one left out one coefficient is wrong":
                ok_naive,
            "a border rank 2 expression reads as exact at e^0 with no negative power, and not with its last term "
            "left out": ok_w}


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    ctl = controls_known()
    if not all(ctl.values()):
        raise AssertionError(f"a control failed: {[c for c, ok in ctl.items() if not ok]}")
    tex = tex_of(read_bytes(os.path.join(inputs, INPUT[0]), INPUT[1]))
    scheme = blocks(region(tex, SCHEME), "tau")
    approx = blocks(region(tex, APPROX), "rho")
    if tuple(sorted(scheme)) != tuple(sorted(BLOCKS)) or tuple(sorted(approx)) != tuple(sorted(APPROX_BLOCKS)):
        raise Refused(f"the blocks printed are {sorted(scheme)} and {sorted(approx)}")

    prods, counts = [], {}
    for name in BLOCKS:
        got = products_of(scheme[name])
        counts[name] = len(got)
        prods += [(name, x) for x in got]
    forms = [integer_form(x) for _, x in prods]
    trilinear = all(f is not None for f in forms)
    ranges = all(in_range(v, *SHAPE) for f in forms if f for form in f.values() for v in form)
    wrong = wrong_count([f for f in forms if f], *SHAPE) if trilinear and ranges else None
    cond = {f"exactly {PRODUCTS} products": len(prods) == PRODUCTS,
            "each a linear form in A's entries times one in B's times one in C's, integral": trilinear and ranges,
            "the sum is the 3x5 by 5x5 product's tensor in all 5,625 coefficients": wrong == 0}

    types = [type_of(f) if f else None for f in forms]
    mismatched = [f"{name}#{i}" for i, ((name, _), t) in enumerate(zip(prods, types))
                  if t != tuple(int(ch) for ch in name)]
    poly = defaultdict(int)
    for t in types:
        if t:
            poly[t] += 1
    shared = shared_pairs([f for f in forms if f]) if trilinear else None

    aprods = []
    for name in APPROX_BLOCKS:
        aprods += products_of(approx[name])
    abad = sum(1 for x in aprods if x["bad"])
    neg, awrong = approx_check(aprods, 5, 5, 5, ZERO_BLOCK)

    values = {
        "source": "the e-print prints the 58 in 13 blocks and the partial approximate tensor in 8, as read",
        "products": len(prods),
        "block_counts": ", ".join(f"{k} {counts[k]}" for k in BLOCKS),
        "trilinear": int(trilinear and ranges),
        "wrong_coefficients": -1 if wrong is None else wrong,
        "types": (f"all {len(prods)} as their blocks are named" if not mismatched else
                  f"{len(mismatched)} differ from their block's name: " + ", ".join(mismatched[:8])),
        "type_polynomial": "as printed" if dict(poly) == PRINTED_TYPE else "not as printed: " + ", ".join(
            f"{t} {poly.get(t, 0)}/{PRINTED_TYPE.get(t, 0)}" for t in sorted(set(poly) | set(PRINTED_TYPE))
            if poly.get(t, 0) != PRINTED_TYPE.get(t, 0))[:180],
        "serendipitous": -1 if shared is None else shared,
        "approx_products": len(aprods),
        "approx_negative": neg,
        "approx_wrong": awrong,
        "approx_exact": int(abad == 0 and neg == 0 and awrong == 0),
        "composites": (f"40 + {len(prods)} = {40 + len(prods)}; 7 x {40 + len(prods)} = {7 * (40 + len(prods))}; "
                       f"{len(prods)} x 36 = {len(prods) * 36}; {len(aprods)} + 20 + 14 = {len(aprods) + 34}"),
        "conditions_met": sum(cond.values()),
        "conditions_total": len(cond),
        "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()),
        "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"input": {"name": INPUT[0], "sha256": INPUT[1]}, "conditions": cond, "controls": ctl,
              "block_counts": counts, "types": {f"{name}#{i}": list(t) if t else None
                                                for i, ((name, _), t) in enumerate(zip(prods, types))},
              "type_polynomial": {str(k): v for k, v in sorted(poly.items())},
              "bad_products": [f"{name}#{i}: {x['bad']}" for i, (name, x) in enumerate(prods) if x["bad"]],
              "approx_bad_products": [x["bad"] for x in aprods if x["bad"]],
              "approx_block_counts": {name: len(products_of(approx[name])) for name in APPROX_BLOCKS}}
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
        sys.exit(f"ss: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
