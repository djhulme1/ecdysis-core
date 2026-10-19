#!/usr/bin/env python3
r"""Cohen & Zudilin's continued fractions for Chowla-Selberg gamma quotients: the 39 continued fractions of their
Table 2 against the limits it prints, the denominator bound of their Theorem 7.3 behind the 20 irrationality
measures, and the measures themselves, recomputed.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:23fe41c84d13e2fa) is from H. Cohen and
W. Zudilin, "Continued Fractions and Irrationality Measures for Chowla--Selberg Gamma Quotients", arXiv:2510.00215v5
(26 September 2026; v1 30 September 2025; arXiv's non-exclusive licence), its abstract: "We give 39 rapidly convergent
continued fractions for Chowla--Selberg gamma quotients, and deduce good irrationality measures for 20 of them,
including for CS(-3) = (G(1/3)/G(2/3))^3, for a^(1/4) CS(-4) = a^(1/4) (G(1/4)/G(3/4))^2 with a = 12 and a = 1/5,
and for CS(-7) = G(1/7)G(2/7)G(4/7)/(G(3/7)G(5/7)G(6/7))."

The paper, as its TeX (fastnew4c.tex, the e-print's one source) states it, in its own numbering. Definition 1.1:
CS(D) = (prod_{j=1}^{|D|} Gamma(j/|D|)^(D/j))^(w(D)/(2h(D))), (D/j) the Kronecker symbol, w(D) the number of roots of
unity and h(D) the class number of Q(sqrt D). Cohen's notation [[a_0, a_1, a(n)], [b_0, b(n)]] is the continued
fraction a_0 + b_0/(a_1 + b(1)/(a(2) + b(2)/(a(3) + ...))), and [[a_0, a(n)], [b_0, b(n)]] the same with a_1 = a(1).
Table 2 prints, for each of 39 fractions [[0, a_1, A(n-1)], [b_0, -K(Dn-1)(D(n-1)+1)]] of the family of Section 3,
its tag, its limit L (CS(D) times an algebraic number), a_1, A, b_0, K, D and a bound on mu(L) or "-". Proposition
3.1: with R = (A + sqrt(A^2 - 4KD^2))/2 and E = R^2/(KD^2), L - p(n)/q(n) ~ C_1/E^n and, with
(p', q') = (p, q)/(|K|^floor(n/2) prod_{j<=n}(D(j-1)+1)), log|q'(n)L - p'(n)| ~ -n log|E|/2. Theorem 7.3: with
d_D(n) = lcm(Dj+1)_{1<=j<=n} and d*_D(n) = d_D(n)/prod_{p in P_n} p (P_n the primes p with max(sqrt(2Dn), D) < p <= n,
p = -1 mod D, {(n+1-1/D)/p} >= 1/D and {(n+1/D)/p} < 1-1/D; empty for D = 2), and v_n either p(n) or q(n) divided by
prod_{j<=n}(D(j-1)+1): (i) if A/K is an integer, d*_D(n) K^-floor((n+1)/2) v_{n+1} is an integer; (ii) otherwise, under
its conditions, it is so up to powers p^(e_p(n)), e_p(n) = O(log n), of the primes p dividing the denominator g of
A/K. Proposition 7.7: log d*_D(n) ~ m*_D n, m*_D = D - (pi/2)cot(pi/D). Lemma 1.2: then mu(L) <= 1 + (F + M)/(F - M)
with F = log|E|/2 and M = m*_D, when F > M. Theorem 6.2 lists the 20 bounds.

The test, as registered: see TEST below. Every rule was fixed before this module evaluated any of the paper's
fractions, limits, denominators or bounds; its tests run the machinery on other fractions and on tables written in the
tests. A syntax-only pass of the readers over the e-print (row counts, columns, parsed expressions; nothing evaluated)
came before the first trial. The abstract and the TeX were read whole first, and while reading, to follow Lemma 1.2's
use, three bounds were worked roughly by hand from Table 1's printed log|E|/2 ((1.4) about 5.548, (1.5) about 5.28,
(2.2) about 25.7), and (1.5)'s A/K = -513/4 was seen to make it the one fraction with a bound under Theorem 7.3(ii);
nothing else of the test was computed before the rules. The syntax pass found Table 2 printing 21 bounds, not 20:
(4.5)'s 7.204 for CS(-7) beside (1.5)'s 5.282, of which Theorem 6.2 keeps the better, so its 20 bounds are one for
each constant; the rules below were then written for all 21 fractions with a printed bound.

1. The e-print is read in memory from the bundle's one input, by hash: a gzipped tar holding 00README.json and one
   TeX file. Table 2 (label tableall) must have 39 rows of eight cells: a tag (k.l), L as $c\CS(-d)$ with c a product of
   b^{e} (integer b, rational e), a_1 (an integer or p/q), A, b_0, K and D (integers) and mu ("-" or a decimal). Table 1
   (label tablerat) must have 44 rows of ten cells. Theorem 6.2's alignat* must give 20 pairs mu(L) < value. The
   appendices' Tables 3 and 4 and the three fractions for higher powers, and the fractions printed in the text (the
   motivating 2^(1/3), Theorem 6.1's CS(-3), Section 6.3's 5^(1/4) and pi/sqrt 3, Section 8's 3^(1/3)), are read for
   the checks beside the test. A reader refuses anything else.
2. The limits. CS(D) by Definition 1.1, w(D) = 6, 4 or 2 for D = -3, -4 and others, h(D) by counting reduced binary
   quadratic forms of discriminant D, the Kronecker symbol computed directly, the product taken as a sum of
   log-Gamma values in mpmath at 280 digits and multiplied by the printed algebraic factor. The convergents p(n), q(n)
   exactly in integers (p(0) = 0, q(0) = 1, p(1) = b_0, q(1) = a_1, p(n+1) = A n p(n) - K(Dn-1)(D(n-1)+1) p(n-1), the
   start scaled by a_1's denominator when it is not an integer), at the first N >= 5 with |E|^N >= 10^230 (E exact
   from A, K and D at 280 digits, and A^2 - 4KD^2 > 0 required). Condition: |p(N)/q(N) - L| < 10^-200 max(1, |L|).
3. The denominators, for each of the 21 fractions with a printed bound and every n from 1 to 300: the rational number
   d*_D(n) K^-floor((n+1)/2) p(n+1) / prod_{j<=n+1}(D(j-1)+1), and the same for q, in exact fractions, must have a
   denominator whose prime factors all divide g, the denominator of A/K in lowest terms (so 1 when A/K is an integer,
   Theorem 7.3(i)). P_n is computed as printed, its fractional parts in exact fractions.
4. The bounds, for each of the 21: F = log|E|/2 and m*_D = D - (pi/2)cot(pi/D) at 60 digits; F > m*_D is required, and
   mu = 1 + (F + m*_D)/(F - m*_D) must not exceed the printed bound by half a unit of its last printed digit (a bound
   printed rounded to nearest is accepted; how each printed bound relates to the value, cut, rounded or rounded up,
   is reported beside).
5. The test's 81 conditions: 39 limits (rule 2), 21 denominator checks (rule 3) and 21 bounds (rule 4). test_passed
   is 1 if all 81 hold.
6. Beside, none of it counted: (a) Table 1 against Table 2: A^2/(4KD^2) = (2R_N(tau) - 1)^2 as printed for each of its
   44 rows (exact), its log|E|/2 and m*_D against the computed values (cut or rounded), its "Y" against F > m*_D, its
   five "-" rows against A^2 - 4KD^2 < 0, and each Table 2 row against its Table 1 row as (A, K) -> (mA, m^2 K);
   (b) Theorem 6.2's 20 bounds against Table 2's column (for CS(-7), the better of its two), and Remark 6.3(2)'s
   16.644 = 3 x 5.548; (c) the 18 fractions without a bound: F <= m*_D for each; (d) Theorem 6.1's (1.4): E = (16 + 5 sqrt 10)^4/36, the error times E^n against
   the printed 3^(3/2) CS(-3), and log|q'(n) CS(-3) - p'(n)| + n log((253 + 80 sqrt 10)/3) at n = 100 and 200;
   (e) Lemma 1.2's hypotheses at n = 300 for the 21: log|q'(n)|/(nF) and -log|q'(n)L - p'(n)|/(nF); (f) case (ii)'s
   extra powers (the largest e_p(n) for n <= 300 against log_p n); (g) the denominator bound's sharpness: the actual
   least common denominator of p'(n+1), q'(n+1) against d*_D(n) at n = 300, and the check of rule 3 repeated with
   P_n's conditions p > sqrt(2Dn) and p > D dropped, which Remark 7.5(1) says numerics suggest are unnecessary;
   (h) Theorem 7.1's explicit P_n, Q_n against the recursion, exactly, for every fraction of Table 2 and n <= 30;
   (i) Proposition 7.7: m_D = (D/phi(D)) sum_{gcd(j,D)=1} 1/j against 2, 9/4, 8/3, 18/5, its two forms of m*_D, and
   log d_D(n)/n and log d*_D(n)/n at n = 100,000; (j) the fractions in the text and the appendices: their limits to
   100 digits where their printed rates allow, the observed rate against the printed E, and for CS(-3)^3's slow
   fraction the constant 9 2^(-1/3) CS(-3)^(5/3) against the error times n^(1/3); (k) the Chowla-Selberg relation of
   the introduction, |eta((-delta + sqrt D)/2)|^4 = CS(D)/(2 pi |D|), for each class-number-one D of the tables.
7. Controls (controls_passed counts those that behave as stated; the run stops if any fails): the fraction evaluator
   against classical fractions (Lambert's tanh 1 and Euler's e - 2) to 150 digits; CS(-3) and CS(-4) against the
   reflection formula's Gamma(1/3)^6 (sqrt 3/(2 pi))^3 and Gamma(1/4)^4/(2 pi^2); the class numbers of -23, -47, -71,
   -84, -15 and -163 against 3, 5, 7, 4, 2 and 1; the Kronecker symbol against Euler's criterion for every odd prime
   below 200 and every discriminant of the tables; exact rationals against mpmath on a seed-drawn convergent; and
   three planted faults, each caught: (1.4) with b_0 = 241, its limit missed; (1.4) with K = -1, its limit missed;
   and rule 3 without d*_D(n), an integer missed.

Changed after the first trial, whose outcome had been seen (all 81 conditions and all 8 controls held): beside items
(d) and (e) took |q'(n)L - p'(n)| at the working 280 digits, where its cancellation needs thousands (for (1.11) at
n = 300 about 4,400), and printed nonsense; they now take L - p(n)/q(n) as the exact difference from the convergent
60 steps on (a tail below E^-60 relative), with logarithms of the integers. No condition, control or input changed.

What it cannot check: the limits as identities (the paper proves them through CM values of hypergeometric functions;
here they hold to 200 digits); Theorem 7.3 beyond n = 300; and Proposition 7.7's asymptotics, which rest on the prime
number theorem.

Writes results/outputs.json and results/detail.json. Run with: python3 pi/cz2025.py
"""

import gzip
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

import mpmath

INPUT = ("cz-2510.00215v5.tar.gz", "d387361875bb6f302f99d045e6a4f518061458b38ec8503caf70335051a0ed29", 29117)
TEX_NAME = "fastnew4c.tex"
DPS = 280
DIGITS_RATE = 230
DIGITS_NEED = 200
N_DEN = 300
LIMIT = 200
TEST = ("Refuted if, for one of Table 2's 39 continued fractions [[0,a_1,A(n−1)],[b_0,−K(Dn−1)(D(n−1)+1)]] as the "
        "e-print prints them, the exact convergent at the first depth N with |E|^N ≥ 10^230, E = R²/(KD²), misses its "
        "printed limit L (computed from Γ to 260 digits) by 10^−200·max(1,|L|) or more; or, for one of the 21 with a "
        "bound, d*_D(n)K^−⌊(n+1)/2⌋ times p(n+1) or q(n+1) over Π_{j≤n+1}(D(j−1)+1) is not an integer for some n ≤ "
        "300 (primes of A/K's denominator aside), or 1 + (F + m*_D)/(F − m*_D), F = log|E|/2, exceeds its printed μ "
        "by half a unit of its last digit.")
OUTPUTS = ("fractions", "limits", "limit_digits", "slowest", "bounds_count", "denominators", "case_ii", "bounds",
           "bound_print", "table1_rows", "table1_values", "table1_pairs", "theorem62", "no_bound", "thm61",
           "lemma12", "sharpness", "pn_conditions", "explicit", "prop77", "text_fractions", "appendix",
           "chowla_selberg", "conditions_met", "conditions_total", "test_passed", "controls_passed", "controls_total")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- reading (rule 1)

def read_input(directory="inputs"):
    path = os.path.join(directory, INPUT[0])
    data = open(path, "rb").read()
    if len(data) != INPUT[2] or hashlib.sha256(data).hexdigest() != INPUT[1]:
        raise Refused(f"{INPUT[0]} is not the e-print of record")
    return read_tex(data)


def read_tex(data):
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
            members = [m for m in tf.getmembers() if m.isfile()]
            names = sorted(m.name for m in members)
            if names != ["00README.json", TEX_NAME]:
                raise Refused(f"unexpected members: {names}")
            raw = tf.extractfile(next(m for m in members if m.name == TEX_NAME)).read()
    except (tarfile.TarError, gzip.BadGzipFile, OSError) as e:
        raise Refused(f"not a gzipped tar: {e}")
    return raw.decode("utf-8")


def table_rows(tex, label):
    i = tex.find("\\label{" + label + "}")
    if i < 0 or tex.count("\\label{" + label + "}") != 1:
        raise Refused(f"no single table {label}")
    a = tex.index("\\hline\\hline", i) + len("\\hline\\hline")
    b = tex.index("\\end{tabular}", a)
    rows = []
    for line in tex[a:b].split("\n"):
        line = line.strip()
        if not line or line == "\\hline":
            continue
        if not line.endswith("\\\\"):
            raise Refused(f"row without its end: {line!r}")
        rows.append([c.strip() for c in line[:-2].split("&")])
    return rows


def unmath(cell):
    c = cell.strip()
    if c.startswith("$") and c.endswith("$") and len(c) >= 2:
        c = c[1:-1]
    return c


def rat(s):
    s = unmath(s).replace(" ", "")
    if not re.fullmatch(r"-?\d+(/\d+)?", s):
        raise Refused(f"not a rational: {s!r}")
    return Fraction(s)


def integer(s):
    v = rat(s)
    if v.denominator != 1:
        raise Refused(f"not an integer: {s!r}")
    return int(v)


def decimal_or_dash(s):
    s = unmath(s)
    if s in ("-", ""):
        return None
    if not re.fullmatch(r"\d+(\.\d+)?", s):
        raise Refused(f"not a decimal: {s!r}")
    return s


LIMIT_RE = re.compile(r"((?:\d+\^\{-?\d+/\d+\})*)\\CS\((-\d+)\)")


def parse_limit(s):
    """'2^{1/3}3^{1/2}\\CS(-3)' -> ([(2, 1/3), (3, 1/2)], -3)."""
    s = unmath(s).replace(" ", "")
    m = LIMIT_RE.fullmatch(s)
    if not m:
        raise Refused(f"not a limit of Table 2's form: {s!r}")
    factors = [(int(b), Fraction(int(p), int(q))) for b, p, q in re.findall(r"(\d+)\^\{(-?\d+)/(\d+)\}", m.group(1))]
    return factors, int(m.group(2))


def read_table2(tex):
    rows = table_rows(tex, "tableall")
    out = []
    for r in rows:
        if len(r) != 8:
            raise Refused(f"Table 2 row of {len(r)} cells: {r}")
        tag = r[0]
        if not re.fullmatch(r"\(\d\.\d+\)", tag):
            raise Refused(f"tag {tag!r}")
        factors, D_disc = parse_limit(r[1])
        out.append({"tag": tag, "L": unmath(r[1]), "factors": factors, "disc": D_disc, "a1": rat(r[2]),
                    "A": integer(r[3]), "b0": integer(r[4]), "K": integer(r[5]), "D": integer(r[6]),
                    "mu": decimal_or_dash(r[7])})
    if len(out) != 39 or len({x["tag"] for x in out}) != 39:
        raise Refused(f"Table 2 has {len(out)} rows")
    return out


def read_table1(tex):
    rows = table_rows(tex, "tablerat")
    out = []
    for r in rows:
        if len(r) != 10:
            raise Refused(f"Table 1 row of {len(r)} cells: {r}")
        out.append({"tag": r[0], "N": integer(r[1]), "D": integer(r[2]), "tau": unmath(r[3]),
                    "z2": rat(r[4]), "A": rat(r[5]), "K": integer(r[6]), "logE2": decimal_or_dash(r[7]),
                    "mstar": decimal_or_dash(r[8]), "irr": unmath(r[9])})
    if len(out) != 44:
        raise Refused(f"Table 1 has {len(out)} rows")
    return out


def read_theorem62(tex):
    i = tex.index("\\label{thm:irrall}")
    a = tex.index("\\begin{alignat*}{3}", i)
    b = tex.index("\\end{alignat*}", a)
    body = tex[a:b]
    pairs = re.findall(r"\\mu\(([^&]*?)\)&<\s*([\d.]+)", body)
    if len(pairs) != 20:
        raise Refused(f"Theorem 6.2 lists {len(pairs)} bounds")
    return [(p.replace(" ", ""), v) for p, v in pairs]


# ---------------------------------------------------------------- polynomials and printed fractions

def poly_parse(s):
    """A polynomial in n with rational coefficients, as {degree: Fraction}; the grammar of the TeX's fractions:
    sums of products of integers, n^k and parenthesised sums, each optionally raised to an integer power."""
    s = s.replace(" ", "")
    pos = [0]

    def peek():
        return s[pos[0]] if pos[0] < len(s) else ""

    def add(a, b, sign=1):
        out = dict(a)
        for k, v in b.items():
            out[k] = out.get(k, 0) + sign * v
        return {k: v for k, v in out.items() if v}

    def mul(a, b):
        out = {}
        for i, x in a.items():
            for j, y in b.items():
                out[i + j] = out.get(i + j, 0) + x * y
        return {k: v for k, v in out.items() if v}

    def power(a, k):
        out = {0: Fraction(1)}
        for _ in range(k):
            out = mul(out, a)
        return out

    def expr():
        sign = 1
        if peek() in "+-":
            sign = -1 if peek() == "-" else 1
            pos[0] += 1
        acc = {k: sign * v for k, v in term().items()}
        while peek() in ("+", "-") and peek():
            sign = -1 if peek() == "-" else 1
            pos[0] += 1
            acc = add(acc, term(), sign)
        return acc

    def term():
        acc = factor()
        while peek() and (peek().isdigit() or peek() in "n("):
            acc = mul(acc, factor())
        return acc

    def factor():
        c = peek()
        if c.isdigit():
            j = pos[0]
            while peek().isdigit():
                pos[0] += 1
            val = {0: Fraction(int(s[j:pos[0]]))}
        elif c == "n":
            pos[0] += 1
            val = {1: Fraction(1)}
        elif c == "(":
            pos[0] += 1
            val = expr()
            if peek() != ")":
                raise Refused(f"unbalanced polynomial {s!r}")
            pos[0] += 1
        else:
            raise Refused(f"unexpected {c!r} in polynomial {s!r}")
        if peek() == "^":
            pos[0] += 1
            if peek() == "{":
                pos[0] += 1
                j = pos[0]
                while peek().isdigit():
                    pos[0] += 1
                k = int(s[j:pos[0]])
                if peek() != "}":
                    raise Refused(f"bad exponent in {s!r}")
                pos[0] += 1
            else:
                k = int(peek())
                pos[0] += 1
            val = power(val, k)
        return val

    out = expr()
    if pos[0] != len(s):
        raise Refused(f"trailing text in polynomial {s!r}")
    return out


def poly_eval(p, n):
    return sum(c * n ** k for k, c in p.items())


def split_top(s):
    parts, depth, cur = [], 0, ""
    for ch in s:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return parts


def parse_cf(s):
    """'[[a_0,a_1,a(n)],[b_0,b(n)]]' or '[[a_0,a(n)],[b_0,b(n)]]' -> (a0, initial a list, a poly, b0, b poly)."""
    s = s.replace(" ", "")
    m = re.fullmatch(r"\[\[(.*)\],\[(.*)\]\]", s)
    if not m:
        raise Refused(f"not a fraction in Cohen's notation: {s!r}")
    a = split_top(m.group(1))
    b = split_top(m.group(2))
    if len(b) != 2 or len(a) not in (2, 3):
        raise Refused(f"unexpected fraction shape: {s!r}")
    a0 = rat(a[0])
    init = [rat(x) for x in a[1:-1]]
    return a0, init, poly_parse(a[-1]), rat(b[0]), poly_parse(b[1])


# ---------------------------------------------------------------- continued fractions

def convergents(a0, init, apoly, b0, bpoly, N):
    """p(n), q(n) for n = 0..N: p(0) = a_0, q(0) = 1, p(1) = a_1 a_0 + b_0, q(1) = a_1, then p(n) = a_n p(n-1) +
    b(n-1) p(n-2). Integers when the polynomials are integral (the start then scaled by its common denominator, which
    leaves every ratio p(n)/q(n) as it is), exact fractions otherwise."""
    def a(k):
        return init[k - 1] if k <= len(init) else poly_eval(apoly, k)
    a1 = Fraction(a(1))
    start = [Fraction(a0), Fraction(1), a1 * a0 + b0, a1]
    integral = all(Fraction(c).denominator == 1 for c in list(apoly.values()) + list(bpoly.values())) and all(
        Fraction(c).denominator == 1 for c in init[1:])
    if integral:
        s = 1
        for x in start:
            s = math.lcm(s, x.denominator)
        p0, q0, p1, q1 = (int(x * s) for x in start)
        conv = int
    else:
        p0, q0, p1, q1 = start
        conv = Fraction
    ps, qs = [p0, p1], [q0, q1]
    for k in range(2, N + 1):
        ak, bk = conv(a(k)), conv(poly_eval(bpoly, k - 1))
        ps.append(ak * ps[-1] + bk * ps[-2])
        qs.append(ak * qs[-1] + bk * qs[-2])
    return ps, qs


def ratio(p, q):
    """p/q at the working precision, for integers or fractions."""
    p, q = Fraction(p), Fraction(q)
    return (mpmath.mpf(p.numerator) * q.denominator) / (mpmath.mpf(q.numerator) * p.denominator)


def backward(a0, init, apoly, b0, bpoly, N):
    """The same fraction truncated at a_N, evaluated from the bottom up in mpmath."""
    def a(k):
        return init[k - 1] if k <= len(init) else poly_eval(apoly, k)
    t = mpmath.mpf(0)
    for k in range(N, 1, -1):
        b = poly_eval(bpoly, k - 1)
        t = mpmath.mpf(b.numerator) / b.denominator / (mpmath.mpf(Fraction(a(k)).numerator) / Fraction(a(k)).denominator + t)
    a1 = Fraction(a(1))
    return mpmath.mpf(a0.numerator) / a0.denominator + (mpmath.mpf(b0.numerator) / b0.denominator) / (
        mpmath.mpf(a1.numerator) / a1.denominator + t)


def family_convergents(row, N):
    """Integers p(0..N), q(0..N) of [[0,a_1,A(n-1)],[b_0,-K(Dn-1)(D(n-1)+1)]], the start scaled by a_1's denominator."""
    s = row["a1"].denominator
    A, K, D = row["A"], row["K"], row["D"]
    p = [0, int(row["b0"] * s)]
    q = [s, int(row["a1"] * s)]
    for n in range(1, N):
        c = -K * (D * n - 1) * (D * (n - 1) + 1)
        p.append(A * n * p[n] + c * p[n - 1])
        q.append(A * n * q[n] + c * q[n - 1])
    return p, q


def rate(A, K, D):
    disc = mpmath.mpf(A) ** 2 - 4 * K * D * D
    if disc <= 0:
        return None
    R = (A + mpmath.sqrt(disc)) / 2
    return R * R / (K * D * D)


def log_gap(p, q, n, m):
    """log|p(m)/q(m) - p(n)/q(n)|, exactly from the integers: the error of the nth convergent when m is far enough on."""
    d = Fraction(p[m], q[m]) - Fraction(p[n], q[n])
    return math.log(abs(d.numerator)) - math.log(d.denominator)


def depth_for(E, digits):
    N = int(mpmath.ceil(digits / mpmath.log10(abs(E))))
    return max(5, N)


# ---------------------------------------------------------------- Chowla-Selberg quotients (rule 2)

def kronecker(D, n):
    """The Kronecker symbol (D/n) for n >= 1."""
    if n == 1:
        return 1
    result = 1
    while n % 2 == 0:
        n //= 2
        if D % 2 == 0:
            return 0
        if D % 8 in (3, 5):
            result = -result
    if n == 1:
        return result
    a, m = D % n, n
    while a:
        while a % 2 == 0:
            a //= 2
            if m % 8 in (3, 5):
                result = -result
        a, m = m, a
        if a % 4 == 3 and m % 4 == 3:
            result = -result
        a %= m
    return result if m == 1 else 0


def class_number(D):
    """Reduced forms (a, b, c), b^2 - 4ac = D, |b| <= a <= c, b >= 0 when |b| = a or a = c."""
    if D >= 0 or D % 4 not in (0, 1):
        raise Refused(f"not a negative discriminant: {D}")
    h, a = 0, 1
    while 3 * a * a <= -D:
        for b in range(-a + 1, a + 1):
            num = b * b - D
            if num % (4 * a) == 0:
                c = num // (4 * a)
                if c >= a and not (a == c and b < 0):
                    h += 1
        a += 1
    return h


def roots_of_unity(D):
    return {-3: 6, -4: 4}.get(D, 2)


def cs(D):
    """CS(D) at the working precision."""
    m = -D
    s = mpmath.mpf(0)
    for j in range(1, m + 1):
        k = kronecker(D, j)
        if k:
            s += k * mpmath.loggamma(mpmath.mpf(j) / m)
    return mpmath.exp(s * mpmath.mpf(roots_of_unity(D)) / (2 * class_number(D)))


def limit_value(row, cache):
    D = row["disc"]
    if D not in cache:
        cache[D] = cs(D)
    v = cache[D]
    for b, e in row["factors"]:
        v *= mpmath.power(b, mpmath.mpf(e.numerator) / e.denominator)
    return v


# ---------------------------------------------------------------- denominators (rule 3)

def primes_upto(n):
    if n < 2:
        return []
    sieve = bytearray([1]) * (n + 1)
    sieve[0] = sieve[1] = 0
    for i in range(2, int(n ** 0.5) + 1):
        if sieve[i]:
            sieve[i * i::i] = bytearray(len(sieve[i * i::i]))
    return [i for i in range(n + 1) if sieve[i]]


def frac_part(x):
    return x - (x.numerator // x.denominator)


def prime_set(D, n, primes, relaxed=False):
    """P_n of Theorem 7.3 as printed (relaxed: without p > sqrt(2Dn) and p > D, as Remark 7.5(1) suggests)."""
    if D == 2:
        return []
    out = []
    for p in primes:
        if p > n:
            break
        if not relaxed and not (p * p > 2 * D * n and p > D):
            continue
        if p % D != D - 1:
            continue
        f1 = frac_part((Fraction(n + 1) - Fraction(1, D)) / p)
        f2 = frac_part((Fraction(n) + Fraction(1, D)) / p)
        if f1 >= Fraction(1, D) and f2 < 1 - Fraction(1, D):
            out.append(p)
    return out


def prime_factors(m):
    out, d = set(), 2
    m = abs(m)
    while d * d <= m:
        while m % d == 0:
            out.add(d)
            m //= d
        d += 1
    if m > 1:
        out.add(m)
    return out


def denominators(row, p, q, n_max=N_DEN, relaxed=False, use_dstar=True):
    """Rule 3 for one fraction: (ok, first failing n or None, largest extra exponents by prime, detail)."""
    D, K, A = row["D"], row["K"], row["A"]
    g = Fraction(A, K).denominator
    allowed = prime_factors(g)
    primes = primes_upto(n_max + 1)
    lcm = 1
    prodf = 1                      # prod_{j=1}^{1} (D(j-1)+1); multiplied by Dn+1 at each n below
    extra = {p_: 0 for p_ in allowed}
    first_bad = None
    for n in range(1, n_max + 1):
        lcm = math.lcm(lcm, D * n + 1)
        prodf *= D * n + 1         # now prod_{j=1}^{n+1} (D(j-1)+1)
        mult = lcm
        if use_dstar:
            for pr in prime_set(D, n, primes, relaxed):
                if mult % pr:
                    raise Refused(f"{pr} in P_{n} does not divide d_D(n)")
                mult //= pr
        else:
            mult = 1
        kpow = abs(K) ** ((n + 1) // 2)
        for v in (p[n + 1], q[n + 1]):
            x = Fraction(mult * v, kpow * prodf)
            den = x.denominator
            for pr in allowed:
                e = 0
                while den % pr == 0:
                    den //= pr
                    e += 1
                extra[pr] = max(extra[pr], e)
            if den != 1 and first_bad is None:
                first_bad = n
    return first_bad is None, first_bad, extra


def dstar(D, n, primes):
    lcm = 1
    for j in range(1, n + 1):
        lcm = math.lcm(lcm, D * j + 1)
    for pr in prime_set(D, n, primes):
        lcm //= pr
    return lcm


# ---------------------------------------------------------------- bounds (rule 4)

def m_star(D):
    return D - mpmath.pi / 2 * mpmath.cot(mpmath.pi / D)


def m_star_general(D):
    phi = sum(1 for j in range(1, D + 1) if math.gcd(j, D) == 1)
    mD = mpmath.mpf(D) / phi * sum(mpmath.mpf(1) / j for j in range(1, D + 1) if math.gcd(j, D) == 1)
    return mD - (mpmath.pi * mpmath.cot(mpmath.pi / D) + mpmath.mpf(D) / (D - 1) - D) / phi


def m_exact(D):
    phi = sum(1 for j in range(1, D + 1) if math.gcd(j, D) == 1)
    return Fraction(D, phi) * sum(Fraction(1, j) for j in range(1, D + 1) if math.gcd(j, D) == 1)


def bound(row):
    with mpmath.workdps(60):
        E = rate(row["A"], row["K"], row["D"])
        if E is None or abs(E) <= 1:
            return None, m_star(row["D"]), None
        F = mpmath.log(abs(E)) / 2
        M = m_star(row["D"])
        mu = 1 + (F + M) / (F - M) if F > M else None
        return F, M, mu


def printed_relation(mu, printed):
    """How a printed decimal relates to the value: 'cut', 'rounded', 'up' (rounded up), or 'off'."""
    d = len(printed.split(".")[1]) if "." in printed else 0
    scale = mpmath.mpf(10) ** d
    v = mu * scale
    cut = mpmath.floor(v)
    up = mpmath.ceil(v)
    near = mpmath.nint(v)
    pv = mpmath.mpf(printed) * scale
    kinds = []
    if abs(pv - near) < 0.5:
        kinds.append("rounded")
    if abs(pv - cut) < 0.5:
        kinds.append("cut")
    if abs(pv - up) < 0.5:
        kinds.append("up")
    return "/".join(kinds) if kinds else "off"


# ---------------------------------------------------------------- Theorem 7.1 (beside h)

def lam(B, i):
    out = Fraction(1)
    for m in range(-i, i):
        out *= B + m
    return out


def explicit_v(n, B, Z, K, v0, v1):
    """Theorem 7.1: v_{n+1} = (P_n v_1 + Q_n v_0)/(B+1)_n."""
    P = Fraction(0)
    for j in range(n // 2 + 1):
        inner = sum(Fraction((-1) ** i * math.factorial(n - i), math.factorial(i) ** 2 * math.factorial(j - i))
                    * lam(B, i) for i in range(j + 1))
        P += (-1) ** j * Fraction(K) ** (n - j) * (Z / K) ** (n - 2 * j) * Fraction(
            math.factorial(n - j), math.factorial(n - 2 * j)) * inner
    Q = Fraction(0)
    for j in range((n - 1) // 2 + 1):
        inner = sum(Fraction((-1) ** i * math.factorial(n - i),
                             math.factorial(i) * math.factorial(i + 1) * math.factorial(j - i)) * lam(B, i)
                    for i in range(j + 1))
        Q += (-1) ** j * Fraction(K) ** (n - j) * (Z / K) ** (n - 2 * j - 1) * Fraction(
            math.factorial(n - j - 1), math.factorial(n - 2 * j - 1)) * inner
    Q *= B - 1
    poch = Fraction(1)
    for k in range(n):
        poch *= B + 1 + k
    return (P * v1 + Q * v0) / poch


def recursion_v(n_max, B, Z, K, v0, v1):
    """(n+B) v_{n+1} = Z n v_n + K(B-n) v_{n-1}."""
    v = [Fraction(v0), Fraction(v1)]
    for n in range(1, n_max + 1):
        v.append((Z * n * v[n] + K * (B - n) * v[n - 1]) / (n + B))
    return v


# ---------------------------------------------------------------- beside (i): log d_D(n) and log d*_D(n)

def log_d(D, n):
    """log d_D(n) and log d*_D(n), d_D(n) = lcm(Dj+1)_{1<=j<=n}, by primes."""
    top = D * n + 1
    primes = primes_upto(top)
    total = mpmath.mpf(0)
    for p in primes:
        if D % p == 0:
            continue
        k, pk = 0, p
        while pk <= top:
            j0 = (-pow(D, -1, pk)) % pk
            if j0 == 0:
                j0 = pk
            if j0 <= n:
                k += 1
                pk *= p
            else:
                break
        if k:
            total += k * mpmath.log(p)
    star = total
    for p in prime_set(D, n, primes):
        star -= mpmath.log(p)
    return total, star


# ---------------------------------------------------------------- beside (j): printed fractions and their limits

ALG_RE = re.compile(r"\((\d+)\+\\sqrt\{(\d+)\}\)")


def parse_general_limit(s):
    """Appendix limits: products of b^{e}, (a+\\sqrt{b}) and \\CS(-d), possibly inside (...)^k or with ^k on CS."""
    s = unmath(s).replace(" ", "")
    power = 1
    m = re.fullmatch(r"\((.*)\)\^(\d+)", s)
    if m and m.group(1).count("(") == m.group(1).count(")"):
        s, power = m.group(1), int(m.group(2))
    m = re.fullmatch(r"(.*\\CS\(-\d+\))\^(\d+)", s)
    if m:
        s, power = m.group(1), power * int(m.group(2))
    factors, algs = [], []
    rest = s
    while rest:
        m1 = re.match(r"(\d+)\^\{(-?\d+)/(\d+)\}", rest)
        m2 = ALG_RE.match(rest)
        m3 = re.match(r"\\CS\((-\d+)\)", rest)
        if m1:
            factors.append((int(m1.group(1)), Fraction(int(m1.group(2)), int(m1.group(3)))))
            rest = rest[m1.end():]
        elif m2:
            algs.append((int(m2.group(1)), int(m2.group(2))))
            rest = rest[m2.end():]
        elif m3:
            disc = int(m3.group(1))
            rest = rest[m3.end():]
        else:
            raise Refused(f"unparsed limit {s!r}")
    return factors, algs, disc, power


def general_value(spec, cache):
    factors, algs, disc, power = spec
    if disc not in cache:
        cache[disc] = cs(disc)
    v = cache[disc]
    for b, e in factors:
        v *= mpmath.power(b, mpmath.mpf(e.numerator) / e.denominator)
    for a, b in algs:
        v *= a + mpmath.sqrt(b)
    return v ** power


def parse_rate(s):
    """Appendix E cells: rationals, -(a+\\sqrt{b})^k, -((a+\\sqrt{b})/c)^{k}."""
    s = unmath(s).replace(" ", "")
    if re.fullmatch(r"-?\d+(/\d+)?", s):
        return mpmath.mpf(Fraction(s).numerator) / Fraction(s).denominator
    m = re.fullmatch(r"(-?)\((\d+)\+\\sqrt\{(\d+)\}\)\^(\d+)", s)
    if m:
        v = (int(m.group(2)) + mpmath.sqrt(int(m.group(3)))) ** int(m.group(4))
        return -v if m.group(1) else v
    m = re.fullmatch(r"(-?)\(\((\d+)\+\\sqrt\{(\d+)\}\)/(\d+)\)\^\{(\d+)\}", s)
    if m:
        v = ((int(m.group(2)) + mpmath.sqrt(int(m.group(3)))) / int(m.group(4))) ** int(m.group(5))
        return -v if m.group(1) else v
    raise Refused(f"unparsed rate {s!r}")


def read_appendix(tex):
    out = []
    for r in table_rows(tex, "tableaux"):
        if len(r) != 10:
            raise Refused(f"Table 3 row {r}")
        lin1 = poly_parse(unmath(r[7]))
        lin2 = poly_parse(unmath(r[8]))
        K = poly_parse(unmath(r[6]))
        kval = K.get(0, 0)
        bpoly = {k: -kval * v for k, v in mul_poly(lin1, lin2).items()}
        apoly = {1: rat(r[3]), 0: rat(r[4])}
        out.append({"where": "Table 3", "L": unmath(r[0]), "spec": parse_general_limit(r[0]),
                    "cf": (rat(r[1]), [rat(r[2])], apoly, rat(r[5]), bpoly), "E": parse_rate(r[9])})
    for r in table_rows(tex, "tableaux2"):
        if len(r) != 10:
            raise Refused(f"Table 4 row {r}")
        D1, D2 = integer(r[7]), integer(r[8])
        f1 = poly_parse(f"({D1}n+1)({D1}n+{D1 - 1})")
        f2 = poly_parse(f"({D2}n+1)({D2}n+{D2 - 1})")
        kval = rat(r[6])
        bpoly = {k: -kval * v for k, v in mul_poly(f1, f2).items()}
        apoly = {2: rat(r[3]), 0: rat(r[4])}
        out.append({"where": "Table 4", "L": unmath(r[0]), "spec": parse_general_limit(r[0]),
                    "cf": (rat(r[1]), [rat(r[2])], apoly, rat(r[5]), bpoly), "E": parse_rate(r[9])})
    i = tex.index("For higher powers we found")
    a = tex.index("\\begin{align*}", i)
    b = tex.index("\\end{align*}", a)
    for line in tex[a + len("\\begin{align*}"):b].split("\\\\"):
        line = line.strip()
        if not line:
            continue
        m = re.fullmatch(r"(\\CS\(-\d+\)\^\d+)&=(\[\[.*\]\])\\quad\s*\((P|E)=(\d+/\d+|\d+)\)", line)
        if not m:
            raise Refused(f"unparsed higher power {line!r}")
        rate_val = None if m.group(3) == "P" else mpmath.mpf(Fraction(m.group(4)).numerator) / Fraction(m.group(4)).denominator
        out.append({"where": "higher powers", "L": m.group(1), "spec": parse_general_limit(m.group(1)),
                    "cf": parse_cf(m.group(2)), "E": rate_val, "P": m.group(4) if m.group(3) == "P" else None})
    if len(out) != 20 + 12 + 3:
        raise Refused(f"appendix fractions: {len(out)}")
    return out


def mul_poly(a, b):
    out = {}
    for i, x in a.items():
        for j, y in b.items():
            out[i + j] = out.get(i + j, 0) + x * y
    return {k: v for k, v in out.items() if v}


def read_text_fractions(tex):
    found = {}
    pats = {
        "2^(1/3), Section 1.2": (r"2\^\{1/3\}=(\[\[5/4,252,253\(2n-1\)\],\[5/2,-\(9n\^2-1\)\]\])", None),
        "5^(1/4), Section 6.3": (r"5\^\{1/4\}=(\[\[3/2,645,644\(2n-1\)\],\[-3,-\(4n-1\)\(4n\+1\)\]\])", None),
        "pi/sqrt 3, Section 6.3": (r"\\pi/\\sqrt\{3\}=(\[\[0,3\(2n-1\)\],\[6,3n\^2\]\])", None),
        "3^(1/3), Section 8": (r"3\^\{1/3\}=(\[\[13/9,6581,6576\(2n-1\)\],\[-130/9,-25\(9n\^2-1\)\]\])", None),
        "CS(-3), Theorem 6.1": (r"\\label\{thm:1\}.*?=(\[\[0,31,1012\(n-1\)\],\[240,-\(6n-1\)\(6n-5\)\]\])", re.S),
    }
    for name, (pat, flags) in pats.items():
        m = re.search(pat, tex, flags or 0)
        if not m:
            raise Refused(f"the text's fraction {name} not found as expected")
        found[name] = parse_cf(m.group(1))
    return found


# ---------------------------------------------------------------- the Dedekind eta (beside k)

def eta_abs4(D):
    delta = 0 if D % 4 == 0 else 1
    tau = (-delta + mpmath.sqrt(mpmath.mpf(D) + 0j)) / 2
    q = mpmath.exp(2j * mpmath.pi * tau)
    prod = mpmath.mpf(1)
    k = 1
    while True:
        t = q ** k
        prod *= 1 - t
        if abs(t) < mpmath.mpf(10) ** (-mpmath.mp.dps - 5):
            break
        k += 1
    eta = mpmath.exp(2j * mpmath.pi * tau / 24) * prod
    return abs(eta) ** 4


# ---------------------------------------------------------------- controls (rule 7)

def controls_run(tex_rows, seed):
    ctl = {}
    with mpmath.workdps(170):
        ps, qs = convergents(Fraction(0), [], {1: Fraction(2), 0: Fraction(-1)}, Fraction(1), {0: Fraction(1)}, 120)
        ok = abs(ratio(ps[-1], qs[-1]) - mpmath.tanh(1)) < mpmath.mpf(10) ** -150
        ps, qs = convergents(Fraction(0), [], {1: Fraction(1)}, Fraction(1), {1: Fraction(1)}, 160)
        ok &= abs(ratio(ps[-1], qs[-1]) - (mpmath.e - 2)) < mpmath.mpf(10) ** -150
    ctl["the evaluator gives Lambert's tanh 1 and Euler's e - 2 to 150 digits"] = bool(ok)
    with mpmath.workdps(120):
        a = cs(-3) - mpmath.gamma(mpmath.mpf(1) / 3) ** 6 * (mpmath.sqrt(3) / (2 * mpmath.pi)) ** 3
        b = cs(-4) - mpmath.gamma(mpmath.mpf(1) / 4) ** 4 / (2 * mpmath.pi ** 2)
        ok = abs(a) < mpmath.mpf(10) ** -100 and abs(b) < mpmath.mpf(10) ** -100
    ctl["CS(-3) and CS(-4) agree with the reflection formula's closed forms"] = bool(ok)
    ctl["class numbers of -23, -47, -71, -84, -15, -163 are 3, 5, 7, 4, 2, 1"] = (
        [class_number(d) for d in (-23, -47, -71, -84, -15, -163)] == [3, 5, 7, 4, 2, 1])
    ok = True
    discs = sorted({r["disc"] for r in tex_rows})
    for p in primes_upto(200)[1:]:
        for d in discs:
            e = pow(d % p, (p - 1) // 2, p)
            want = 0 if d % p == 0 else (1 if e == 1 else -1)
            ok &= kronecker(d, p) == want
    ctl["the Kronecker symbol agrees with Euler's criterion for odd primes below 200"] = ok
    st = hashlib.sha256(f"{seed}/cz/controls".encode()).digest()
    pick = tex_rows[st[0] % len(tex_rows)]
    depth = 20 + st[1] % 40
    p, q = family_convergents(pick, depth)
    cf = (Fraction(0), [pick["a1"]], {1: Fraction(pick["A"]), 0: Fraction(-pick["A"])}, Fraction(pick["b0"]),
          {k: -pick["K"] * v for k, v in poly_parse(f"({pick['D']}n-1)({pick['D']}n-{pick['D'] - 1})").items()})
    with mpmath.workdps(120):
        ok = abs(ratio(p[depth], q[depth]) - backward(*cf, depth)) < mpmath.mpf(10) ** -100 * max(1, abs(ratio(p[depth], q[depth])))
    ctl["the forward recursion agrees with the fraction evaluated from the bottom, on a seed-drawn row and depth"] = bool(ok)
    r14 = next(r for r in tex_rows if r["tag"] == "(1.4)")
    cache = {}
    with mpmath.workdps(DPS):
        L = limit_value(r14, cache)
        for change, label in (({"b0": 241}, "b_0 = 241"), ({"K": -1}, "K = -1")):
            bad = dict(r14, **change)
            E = rate(bad["A"], bad["K"], bad["D"])
            N = depth_for(E, DIGITS_RATE) if E is not None else 50
            pp, qq = family_convergents(bad, N)
            miss = abs(mpmath.mpf(pp[N]) / qq[N] - L) >= mpmath.mpf(10) ** -DIGITS_NEED * max(1, abs(L))
            ctl[f"a planted fault caught: (1.4) with {label} misses CS(-3)"] = bool(miss)
    p, q = family_convergents(r14, 62)
    ok, first_bad, _ = denominators(r14, p, q, n_max=60, use_dstar=False)
    ctl["a planted fault caught: rule 3 without d*_D(n) finds a non-integer"] = (not ok)
    return ctl


# ---------------------------------------------------------------- run

def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    tex = read_input(inputs)
    t2 = read_table2(tex)
    t1 = read_table1(tex)
    th62 = read_theorem62(tex)
    appendix = read_appendix(tex)
    text_cfs = read_text_fractions(tex)
    mpmath.mp.dps = DPS
    ctl = controls_run(t2, seed)
    if not all(ctl.values()):
        raise AssertionError(f"a control failed: {[k for k, v in ctl.items() if not v]}")

    cond, detail = {}, {"limits": {}, "denominators": {}, "bounds": {}}
    cache = {}
    with_bound = [r for r in t2 if r["mu"] is not None]
    if len(with_bound) != 21:
        raise Refused(f"Table 2 prints {len(with_bound)} bounds")

    # rule 2: the limits
    digits, slowest = {}, None
    conv = {}
    for r in t2:
        with mpmath.workdps(DPS):
            E = rate(r["A"], r["K"], r["D"])
            if E is None or abs(E) <= 1:
                cond[f"{r['tag']} {r['L']}: converges to its limit"] = False
                detail["limits"][r["tag"]] = {"E": None}
                continue
            N = depth_for(E, DIGITS_RATE)
            p, q = family_convergents(r, max(N, N_DEN + 62))
            conv[r["tag"]] = (p, q)
            L = limit_value(r, cache)
            err = abs(mpmath.mpf(p[N]) / q[N] - L)
            ok = err < mpmath.mpf(10) ** -DIGITS_NEED * max(1, abs(L))
            d = int(mpmath.floor(-mpmath.log10(err))) if err > 0 else DPS
            digits[r["tag"]] = d
            if slowest is None or abs(E) < abs(slowest[1]):
                slowest = (r["tag"], E, N)
            cond[f"{r['tag']} {r['L']}: convergent {N} within 10^-200 of the printed limit"] = bool(ok)
            detail["limits"][r["tag"]] = {"E": mpmath.nstr(E, 15), "N": N, "digits": d, "L": mpmath.nstr(L, 30)}

    # rule 3: the denominators
    case_ii = {}
    for r in with_bound:
        p, q = conv.get(r["tag"], family_convergents(r, N_DEN + 2))
        ok, first_bad, extra = denominators(r, p, q)
        g = Fraction(r["A"], r["K"]).denominator
        if g != 1:
            case_ii[r["tag"]] = (g, extra)
        cond[f"{r['tag']}: d*_D(n) K^-floor((n+1)/2) v_(n+1) integral for n <= {N_DEN}"
             + (f" up to powers of {sorted(prime_factors(g))}" if g != 1 else "")] = ok
        detail["denominators"][r["tag"]] = {"ok": ok, "first_bad": first_bad, "g": g,
                                            "extra": {str(k): v for k, v in extra.items()}}

    # rule 4: the bounds
    rel = {}
    for r in with_bound:
        F, M, mu = bound(r)
        printed = r["mu"]
        dlast = len(printed.split(".")[1]) if "." in printed else 0
        with mpmath.workdps(60):
            ok = mu is not None and mu <= mpmath.mpf(printed) + mpmath.mpf(5) / mpmath.mpf(10) ** (dlast + 1)
        rel[r["tag"]] = printed_relation(mu, printed) if mu is not None else "none"
        cond[f"{r['tag']}: mu <= {printed}"] = bool(ok)
        detail["bounds"][r["tag"]] = {"F": mpmath.nstr(F, 12), "m_star": mpmath.nstr(M, 12),
                                      "mu": mpmath.nstr(mu, 12) if mu is not None else None, "printed": printed,
                                      "relation": rel[r["tag"]]}

    # beside (a): Table 1
    t2_by_tag = {r["tag"]: r for r in t2}
    z_ok, logE_ok, mstar_ok, y_ok, dash_ok, pair_ok = 0, 0, 0, 0, 0, 0
    logE_kinds = {}
    for r in t1:
        A, K, D = r["A"], r["K"], r["D"]
        z_ok += (A * A) / (4 * K * D * D) == r["z2"]
        disc = A * A - 4 * K * D * D
        if r["logE2"] is None:
            dash_ok += disc < 0
            continue
        with mpmath.workdps(60):
            E = rate(mpmath.mpf(A.numerator) / A.denominator, K, D)
            F = mpmath.log(abs(E)) / 2
            M = m_star(D)
        kind = printed_relation(F, r["logE2"])
        logE_kinds[kind] = logE_kinds.get(kind, 0) + 1
        logE_ok += kind != "off"
        mstar_ok += printed_relation(M, r["mstar"]) != "off"
        y_ok += (r["irr"] == "Y") == (F > M)
        t = t2_by_tag.get(r["tag"])
        if t is not None:
            m = Fraction(t["A"]) / A
            pair_ok += m > 0 and Fraction(t["K"]) == m * m * K and t["D"] == D
    n_vals = sum(1 for r in t1 if r["logE2"] is not None)

    # beside (b): Theorem 6.2
    th_ok = 0
    for L_expr, v in th62:
        printed = [Fraction(r["mu"]) for r in with_bound if r["L"] == L_expr]
        th_ok += bool(printed) and Fraction(v) == min(printed)
    r14 = t2_by_tag["(1.4)"]
    rem63 = Fraction(r14["mu"]) * 3 == Fraction("16.644")

    # beside (c): no bound
    nb = [r for r in t2 if r["mu"] is None]
    nb_ok = sum(1 for r in nb if (lambda b: b[2] is None)(bound(r)))

    # beside (d): Theorem 6.1
    with mpmath.workdps(DPS):
        E14 = rate(1012, 1, 6)
        Ealt = (16 + 5 * mpmath.sqrt(10)) ** 4 / 36
        L14 = limit_value(r14, cache)
        p, q = conv["(1.4)"]
        n0 = 30
        const = (L14 - mpmath.mpf(p[n0]) / q[n0]) * E14 ** n0 / (3 ** mpmath.mpf(1.5) * L14)
        f = lambda n: abs(r14["K"]) ** (n // 2) * math.prod(6 * (j - 1) + 1 for j in range(1, n + 1))
        drift = []
        for n in (100, 200):
            log_qp = math.log(abs(q[n])) - math.log(f(n))
            drift.append(mpmath.mpf(log_qp + log_gap(p, q, n, n + 60))
                         + n * mpmath.log((253 + 80 * mpmath.sqrt(10)) / 3))
        thm61 = (f"E = (16+5 sqrt10)^4/36: {'yes' if abs(E14 - Ealt) < mpmath.mpf(10) ** -250 else 'no'}; "
                 f"error x E^n / (3^(3/2) CS(-3)) at n = 30: {mpmath.nstr(const, 8)}; "
                 f"log|q'L - p'| + n log((253+80 sqrt10)/3) at n = 100, 200: "
                 + ", ".join(mpmath.nstr(x, 5) for x in drift))

    # beside (e): Lemma 1.2's hypotheses at n = 300
    l12 = []
    with mpmath.workdps(DPS):
        for r in with_bound:
            p, q = conv[r["tag"]]
            n = N_DEN
            fn = abs(r["K"]) ** (n // 2) * math.prod(r["D"] * (j - 1) + 1 for j in range(1, n + 1))
            F = float(mpmath.log(abs(rate(r["A"], r["K"], r["D"]))) / 2)
            log_qp = math.log(abs(q[n])) - math.log(fn)
            grow = log_qp / (n * F)
            small = -(log_qp + log_gap(p, q, n, n + 60)) / (n * F)
            l12.append((r["tag"], grow, small))
    lemma12 = (f"at n = 300, log|q'|/(nF) from {min(x[1] for x in l12):.3f} to {max(x[1] for x in l12):.3f}, "
               f"-log|q'L-p'|/(nF) from {min(x[2] for x in l12):.3f} to {max(x[2] for x in l12):.3f}")

    # beside (f): case (ii)
    case_text = "; ".join(f"{t}: g = {g}, largest extra power " + ", ".join(
        f"{pr}^{e} (log_{pr} 300 = {math.log(300, pr):.1f})" for pr, e in sorted(extra.items()))
        for t, (g, extra) in case_ii.items()) or "none"

    # beside (g): sharpness and relaxed conditions
    sharp = []
    relaxed_ok = 0
    primes = primes_upto(N_DEN + 2)
    for r in with_bound:
        p, q = conv[r["tag"]]
        n = N_DEN
        prodf = math.prod(r["D"] * (j - 1) + 1 for j in range(1, n + 2))
        kpow = abs(r["K"]) ** ((n + 1) // 2)
        lcd = math.lcm(Fraction(p[n + 1], kpow * prodf).denominator, Fraction(q[n + 1], kpow * prodf).denominator)
        ds = dstar(r["D"], n, primes)
        sharp.append(math.log(lcd) / math.log(ds) if ds > 1 else float("nan"))
        ok_rel, _, _ = denominators(r, p, q, relaxed=True)
        relaxed_ok += ok_rel
    sharpness = (f"actual denominator against d*_D(300), as logs: {min(sharp):.4f} to {max(sharp):.4f} "
                 f"over the {len(with_bound)}")
    pn_text = f"rule 3 with P_n's p > sqrt(2Dn) and p > D dropped: {relaxed_ok} of {len(with_bound)} still integral"

    # beside (h): Theorem 7.1
    ex_ok = 0
    for r in t2:
        B = Fraction(1, r["D"])
        Z = Fraction(r["A"], r["D"])
        K = Fraction(r["K"])
        s = r["a1"].denominator
        for v0, v1 in ((0, r["b0"] * s), (s, r["a1"] * s)):
            rec = recursion_v(31, B, Z, K, Fraction(v0), Fraction(v1))
            ex_ok += all(explicit_v(n, B, Z, K, Fraction(v0), Fraction(v1)) == rec[n + 1] for n in range(0, 31))
    explicit = f"Theorem 7.1's P_n, Q_n give the recursion's v_(n+1) for n <= 30: {ex_ok} of {2 * len(t2)} sequences"

    # beside (i): Proposition 7.7
    with mpmath.workdps(30):
        mvals = [m_exact(D) for D in (2, 3, 4, 6)]
        forms = max(abs(m_star(D) - m_star_general(D)) for D in (3, 4, 6))
        logs = []
        for D in (2, 3, 4, 6):
            ld, lds = log_d(D, 100000)
            logs.append((D, float(ld / 100000), float(lds / 100000), float(m_star(D))))
    prop77 = ("m_D = " + ", ".join(str(m) for m in mvals) + f"; m*_D forms agree to {mpmath.nstr(forms, 2)}; at n = 1e5 "
              + ", ".join(f"D={D}: {a:.3f}/{b:.3f} (m* {c:.3f})" for D, a, b, c in logs))

    # beside (j): fractions in the text and appendices
    text_res = []
    with mpmath.workdps(150):
        targets = {"2^(1/3), Section 1.2": mpmath.cbrt(2), "5^(1/4), Section 6.3": mpmath.root(5, 4),
                   "pi/sqrt 3, Section 6.3": mpmath.pi / mpmath.sqrt(3), "3^(1/3), Section 8": mpmath.cbrt(3),
                   "CS(-3), Theorem 6.1": cs(-3)}
        for name, cf in text_cfs.items():
            ps, qs = convergents(*cf, 400 if "pi" in name else 60)
            val = ratio(ps[-1], qs[-1])
            err = abs(val - targets[name])
            text_res.append((name, int(mpmath.floor(-mpmath.log10(err))) if err else 150))
        app_ok, app_digits, app_rate = 0, [], []
        for item in appendix:
            L = general_value(item["spec"], cache)
            if item["E"] is None:
                ps, qs = convergents(*item["cf"], 4000)
                val = ratio(ps[-1], qs[-1])
                C = 9 * mpmath.cbrt(mpmath.mpf(1) / 2) * cs(-3) ** (mpmath.mpf(5) / 3)
                slow = (L - val) * mpmath.cbrt(4000) / C
                continue
            N = max(10, int(mpmath.ceil(110 / mpmath.log10(abs(item["E"])))))
            ps, qs = convergents(*item["cf"], N + 2)
            vals = [ratio(ps[k], qs[k]) for k in (N - 2, N - 1, N)]
            err = abs(vals[-1] - L)
            dgt = int(mpmath.floor(-mpmath.log10(err))) if err else 150
            app_digits.append(dgt)
            app_ok += dgt >= 100
            e1, e2 = L - vals[1], L - vals[2]
            obs = e1 / e2 if e2 != 0 else mpmath.inf
            app_rate.append(abs(obs / item["E"] - 1) < mpmath.mpf("0.05"))
    text_fr = "; ".join(f"{n}: {d} digits" for n, d in text_res)
    appendix_text = (f"Tables 3 and 4 and the higher powers: {app_ok} of {len(app_digits)} to 100 digits (least "
                     f"{min(app_digits)}), rate within 5% of the printed E in {sum(app_rate)}; CS(-3)^3's slow "
                     f"fraction: error x n^(1/3) / C at n = 4000 is {mpmath.nstr(slow, 6)}")

    # beside (k): Chowla-Selberg's relation
    with mpmath.workdps(60):
        cs_ok, cs_n = 0, 0
        for D in sorted({r["disc"] for r in t2}):
            if class_number(D) != 1:
                continue
            cs_n += 1
            lhs = eta_abs4(D)
            rhs = cs(D) / (2 * mpmath.pi * abs(D))
            cs_ok += abs(lhs / rhs - 1) < mpmath.mpf(10) ** -50

    values = {
        "fractions": f"Table 2: {len(t2)} fractions (D = 6: {sum(r['D'] == 6 for r in t2)}, 4: {sum(r['D'] == 4 for r in t2)}, 3: {sum(r['D'] == 3 for r in t2)}, 2: {sum(r['D'] == 2 for r in t2)}), {len(with_bound)} with a bound",
        "limits": f"{sum(1 for k, v in cond.items() if 'printed limit' in k and v)} of 39 within 10^-200 of the printed limit at the depth |E|^N >= 10^230",
        "limit_digits": f"digits of agreement from {min(digits.values())} to {max(digits.values())}",
        "slowest": f"slowest: {slowest[0]}, |E| = {mpmath.nstr(abs(slowest[1]), 6)}, N = {slowest[2]}",
        "bounds_count": f"{sum(1 for k, v in cond.items() if ': mu <=' in k and v)} of {len(with_bound)} bounds hold as printed (Theorem 6.2 keeps 20, one per constant)",
        "denominators": f"{sum(1 for k, v in cond.items() if 'integral for n' in k and v)} of {len(with_bound)} integral for every n <= {N_DEN}",
        "case_ii": case_text[:LIMIT],
        "bounds": "; ".join(f"{r['tag']} {mpmath.nstr(bound(r)[2], 7)}" for r in with_bound[:6]) + " ...",
        "bound_print": "printed bounds against the values: " + ", ".join(
            f"{k} {v}" for k, v in sorted({x: sum(1 for y in rel.values() if y == x) for x in set(rel.values())}.items())),
        "table1_rows": f"Table 1: A^2/(4KD^2) = (2R-1)^2 in {z_ok} of 44; the 5 dashes with A^2 - 4KD^2 < 0: {dash_ok}",
        "table1_values": (f"log|E|/2 as printed in {logE_ok} of {n_vals} (" + ", ".join(
            f"{k} {v}" for k, v in sorted(logE_kinds.items())) + f"); m*_D in {mstar_ok}; Y as F > m*_D in {y_ok}"),
        "table1_pairs": f"Table 2 rows as (mA, m^2 K) of Table 1's: {pair_ok} of 39",
        "theorem62": f"Theorem 6.2's bounds are Table 2's (the better for CS(-7)) in {th_ok} of {len(th62)}; 3 x 5.548 = 16.644: {'yes' if rem63 else 'no'}",
        "no_bound": f"the {len(nb)} without a bound have F <= m*_D: {nb_ok} of {len(nb)}",
        "thm61": thm61[:LIMIT],
        "lemma12": lemma12,
        "sharpness": sharpness,
        "pn_conditions": pn_text,
        "explicit": explicit,
        "prop77": prop77[:LIMIT],
        "text_fractions": text_fr[:LIMIT],
        "appendix": appendix_text[:LIMIT],
        "chowla_selberg": f"|eta|^4 = CS(D)/(2 pi |D|) to 50 digits for {cs_ok} of {cs_n} class-number-one D",
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail.update({"test": TEST, "conditions": cond, "controls": ctl, "relations": rel,
                   "lemma12": l12, "text_fractions": text_res, "appendix_digits": app_digits,
                   "theorem62": th62, "table1_logE_kinds": logE_kinds})
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="utf-8") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, ensure_ascii=False, default=str)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"cz2025: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
