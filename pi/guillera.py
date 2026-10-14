#!/usr/bin/env python3
"""Guillera's two WZ pairs and the eight series he derives from them: the WZ equation exactly, the sums to 500 digits.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:f073fa538f1b6476) is from J. Guillera,
"Some binomial series obtained by the WZ-method", Advances in Applied Mathematics 29 (2002) 599-603,
arXiv:math/0503345v1: "Using the WZ-method we find some of the easiest Ramanujan's formulae and also some new
interesting Ramanujan-like sums."

Its registered test: refuted if, for either printed WZ pair, F(n+1, k) - F(n, k) != G(n, k+1) - G(n, k) exactly for
some n from 1 to 40 and k from 0 to 2n - 1; or if one of the eight printed sums (at k = 0, two to 8/pi and two to
32/pi^2; at k = 1/4, two to sqrt(pi)/Gamma(3/4)^2 and two to pi/Gamma(3/4)^4), each summed as printed, differs from its
printed value by 10^-500 or more, with pi by two series that agree and Gamma(3/4)^2 = sqrt(pi/2) AGM(1, sqrt 2),
checked against Ramanujan's phi(e^-pi) = pi^(1/4)/Gamma(3/4).

The input is the paper's e-print from arXiv (one gzipped TeX file), checked against its SHA-256 and read as data
(decompressed with the standard library and read as text; nothing in it is run). Python's standard library only
(integers and fractions, exactly, and integers scaled by 10^P). Every rule below was fixed before any of the
quantities it tests was computed; the seed is not used, as nothing here is random.

1. The source. With its TeX comments removed and its whitespace collapsed, the e-print must hold every formula in
   FORMULAS below (each pair's G and F, their Gamma forms, H, and the four displays of sums); otherwise the run is
   refused. What is computed is what those formulas say, transcribed in rules 2 and 4.
2. The pairs, in their binomial forms, with every binomial C(a, b) an exact integer and refused outside 0 <= b <= a:
   - the first: G(n, k) = (-1)^(n+k) (20n + 2k + 3) R1(n, k) / 2^(10n+2k) and F(n, k) = 64 (-1)^(n+k) n^2 R1(n, k) /
     ((4n - 2k - 1) 2^(10n+2k)), with R1 = C(2k, k)^2 C(2n, n)^2 C(4n-2k, 2n-k) / (C(2n, k) C(n+k, n));
   - the second: G(n, k) = (-1)^k (120n^2 + 84nk + 34n + 10k + 3) R2(n, k) / 2^(16n+4k) and F(n, k) = 512 (-1)^k n^3
     R2(n, k) / ((4n - 2k - 1) 2^(16n+4k)), with R2 = C(2k, k)^3 C(2n, n)^4 C(4n-2k, 2n-k) / (C(2n, k) C(n+k, n)^2).
   The WZ equation is checked as an equality of fractions at every n from 1 to N_WZ = 40 and k from 0 to 2n - 1, the
   points at which every binomial in it is defined: 1,640 points a pair. Conditions 1 and 2: no point fails.
3. The constants, as integers in units of 10^-P, P = 560 digits:
   - pi by Machin's formula (16 arctan(1/5) - 4 arctan(1/239), Taylor series in fixed point) and by the Chudnovskys'
     series (binary splitting, then an integer square root); they must agree within 10^-(P - 10) (a control), and
     Machin's is used;
   - A = AGM(1, sqrt 2) by the arithmetic-geometric mean in fixed point (integer square roots) until the two means
     agree within 2 units; then, as Gamma(3/4)^2 = sqrt(pi/2) A, sqrt(pi)/Gamma(3/4)^2 = sqrt 2/A and
     pi/Gamma(3/4)^4 = 2/A^2;
   - checked by Ramanujan's phi(e^-pi) = pi^(1/4)/Gamma(3/4), whose square is sqrt(pi)/Gamma(3/4)^2: with e^-pi from
     the Taylor series of e^pi, (1 + 2 sum_{m>=1} e^(-pi m^2))^2 must equal sqrt 2/A within 10^-(P - 10) (a control).
4. The sums, each summand as printed, an exact fraction (binomials, factorials and rising factorials (1/4)_m and
   (1/2)_m, exactly), rounded to the nearest unit of 10^-P and added; the factor printed in front of a sum (1/2,
   sqrt 2/8, 3 sqrt 2/8, 1/4, 1/8, 1/8) is applied to the total, sqrt 2 in fixed point. The sums, labelled by pair and
   by place (a: G at k = 0, b: H at k = 0, c and d: the two at k = 1/4):
   1a  sum (-1)^n C(4n, 2n) C(2n, n)^2 (20n + 3) / 2^(10n) = 8/pi
   1b  (1/2) sum C(2n, n)^3 (42n + 5) / 2^(12n) = 8/pi
   1c  (sqrt 2/8) sum (-1)^n (1/2)_n (1/4)_(2n) / ((n!)^2 (1/4)_n 2^(4n)) (40n + 7)/(4n + 1) = sqrt(pi)/Gamma(3/4)^2
   1d  (3 sqrt 2/8) sum (1/2)_(2n)^2 (1/2)_n / ((n!)^2 (1/4)_(2n) (1/4)_n 2^(8n)) (112n^2 + 88n + 11)/((8n + 1)(8n + 5))
       = sqrt(pi)/Gamma(3/4)^2
   2a  sum C(4n, 2n) C(2n, n)^4 (120n^2 + 34n + 3) / 2^(16n) = 32/pi^2
   2b  (1/4) sum (-1)^n C(2n, n)^5 (820n^2 + 180n + 13) / 2^(20n) = 32/pi^2
   2c  (1/8) sum (1/2)_n^3 (1/4)_(2n) / ((n!)^3 (1/4)_n^2 2^(6n)) (240n^2 + 110n + 11)/(4n + 1)^2 = pi/Gamma(3/4)^4
   2d  (1/8) sum (-1)^n (1/2)_(2n)^3 (1/2)_n^3 / ((n!)^3 (1/4)_(2n)^2 (1/4)_n^2 2^(12n))
       (26240n^4 + 41184n^3 + 21448n^2 + 4170n + 279)/((8n + 1)^2 (8n + 5)^2) = pi/Gamma(3/4)^4
   Terms are added from n = 0 until one is below 10^-(P + 5) in size, and then EXTRA = 10 more. The ratio of each
   further term to the one before is computed exactly for the next TAIL = 200 terms; when all are below 1/2, the tail
   is below twice the last term added. (The ratios tend to 1/4, 1/64, 1/4, 1/64, 1/16, 1/1024, 1/16 and 1/1024; the
   check is numerical, not a proof, and sits far below the threshold.) Rounding adds at most half a unit per term.
5. The test. Conditions 3 to 10: each sum S is within 10^-500 of its printed value V, i.e. |S - V| + m < 10^(P - 500)
   in units of 10^-P, m = the terms added + 100 units (rounding, the factors in front and the constants), plus twice
   the last term, or the condition fails when the tail check of rule 4 does not hold. test_passed is 1 if all ten hold.
6. Beside the test (reported, not tested): the digits of agreement of each sum, P - log10 |S - V| rounded down and
   capped at CAP = P - 10 (the cap where |S - V| is within m); the terms each sum used; G(n, 0) and
   H(n, 0) = F(n + 1, n) + G(n, n) against the printed summands of sums a and b of each pair (with b's factor in front),
   for n from 0 to N_TERMWISE = 60; and the Gamma forms of the pairs at integer k, in which every power of pi cancels
   (Gamma(m + 1/2) = sqrt(pi) (1/2)_m, cos(pi k) = (-1)^k), against the binomial forms at every n from 0 to 40 and k
   from 0 to 2n (1,681 points a pair).
7. Controls, which must all pass or the run stops: the two pi agree (rule 3) and give the first 50 printed decimals
   (OEIS A000796); phi(e^-pi)^2 agrees with sqrt 2/A (rule 3); the WZ check accepts F(n, k) = C(n, k)/2^n,
   G(n, k) = -C(n, k - 1)/2^(n+1) (the pair for sum_k C(n, k) = 2^n; C = 0 outside 0 <= k <= n) at every n from 1 to
   40 and k from 0 to n, and finds a failing point in the first pair with the 3 of its G made 4; the summation of rule
   4 gives sum C(2n, n)/16^n = 2/sqrt 3 within its margin and its tail check holds; and (1/2)_n = (2n)!/(4^n n!) and
   (1/4)_n (3/4)_n = (4n)!/(64^n (2n)!) for n up to 50.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
"""

import gzip
import hashlib
import json
import math
import os
import re
import sys
from fractions import Fraction

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)          # the constants are written out in detail.json

INPUT = ("arXiv-math-0503345v1.gz", "05b91c9df8083ad2e2476fcd20836f807c4b96e765cb5d0c4b2747611d1a984f")
P = 560                    # rule 3: digits
THRESHOLD = 500            # rule 5: 10^-500
N_WZ = 40                  # rule 2
N_TERMWISE = 60            # rule 6
N_GAMMA = 40               # rule 6
EXTRA, TAIL = 10, 200      # rule 4
CAP = P - 10               # rule 6
PI50 = "3.14159265358979323846264338327950288419716939937510"
LIMIT = 200

FORMULAS = (
    r"G(n,k)={(-1)^n(-1)^k \over 2^{10n}2^{2k}} (20n+2k+3) {{2k \choose k}^2 {2n \choose n}^2 {4n-2k \choose 2n-k} "
    r"\over {2n \choose k}{n+k \choose n}}.",
    r"F(n,k)=64{(-1)^n(-1)^k \over 2^{10n}2^{2k}}{n^2 \over 4n-2k-1} {{2k \choose k}^2 {2n \choose n}^2 {4n-2k "
    r"\choose 2n-k} \over {2n \choose k}{n+k \choose n}}.",
    r"F(n,k) &= {64 \over \pi^3} {n^2 \over 4n-2k-1} {(-1)^n \cos(\pi k) \Gamma(2n-k+1/2)\Gamma(n+1/2)^3\Gamma(k+1/2)^2 "
    r"\over \Gamma(n+k+1)\Gamma(2n+1)^2}, \nonumber \\ G(n,k) &={1 \over \pi^3} (20n+2k+3) {(-1)^n \cos(\pi k) "
    r"\Gamma(2n-k+1/2)\Gamma(n+1/2)^3\Gamma(k+1/2)^2 \over \Gamma(n+k+1)\Gamma(2n+1)^2}.",
    r"H(n,k)=F(n+1,n+k)+G(n,n+k).",
    r"\sum_{n=0}^{\infty}G(n,0) &= \sum_{n=0}^{\infty} {(-1)^n {4n \choose 2n}{2n \choose n}^2 \over 2^{10n}} "
    r"(20n+3)={8 \over \pi}, \nonumber \\ \sum_{n=0}^{\infty}H(n,0) &={1 \over 2} \sum_{n=0}^{\infty} {{2n \choose n}^3 "
    r"\over 2^{12n}} (42n+5)={8 \over \pi}.",
    r"& {\sqrt 2 \over 8 } \sum_{n=0}^{\infty} {(-1)^n \left( 1 \over 2 \right)_n\left( 1 \over 4 \right)_{2n} \over "
    r"(n!)^2 \left( 1 \over 4 \right)_ n 2 ^{4n} } {40n+7 \over 4n+1} = {\sqrt {\pi} \over \Gamma({3 \over 4})^2}, "
    r"\nonumber \\ & {3 \sqrt 2 \over 8 } \sum_{n=0}^{\infty} {\left( 1 \over 2 \right)_{2n}^2 \left( 1 \over 2 "
    r"\right)_{n} \over (n!)^2 \left( 1 \over 4 \right)_ {2n} \left( {1 \over 4} \right)_n 2^{8n}} { 112n^2+88n+11 "
    r"\over (8n+1)(8n+5)} = {\sqrt {\pi} \over \Gamma({3 \over 4})^2}.",
    r"G(n,k)={(-1)^k \over 2^{16n}2^{4k}} (120n^2+84nk+34n+10k+3) {{2k \choose k}^3 {2n \choose n}^4 {4n-2k \choose "
    r"2n-k} \over {2n \choose k}{n+k \choose n}^2};",
    r"F(n,k)=512{(-1)^k \over 2^{16n}2^{4k}} {n^3 \over 4n-2k-1} {{2k \choose k}^3 {2n \choose n}^4 {4n-2k \choose "
    r"2n-k} \over {2n \choose k}{n+k \choose n}^2}.",
    r"F(n,k)={512 \over \pi^5} {n^3 \over 4n-2k-1} \times {\cos(\pi k) \Gamma(2n-k+1/2)\Gamma(n+1/2)^6\Gamma(k+1/2)^3 "
    r"\over \Gamma(n+k+1)^2\Gamma(2n+1)^3},",
    r"G(n,k)={1 \over \pi^5} (120n^2+84nk+34n+10k+3) \\ \times {\cos(\pi k) \Gamma(2n-k+1/2)\Gamma(n+1/2)^6"
    r"\Gamma(k+1/2)^3 \over \Gamma(n+k+1)^2\Gamma(2n+1)^3}.",
    r"\sum_{n=0}^{\infty}G(n,0) &= \sum_{n=0}^{\infty} {{4n \choose 2n}{2n \choose n}^4 \over 2^{16n}} "
    r"(120n^2+34n+3)={32 \over \pi^2}, \nonumber \\ \sum_{n=0}^{\infty}H(n,0) &= {1 \over 4} \sum_{n=0}^{\infty} "
    r"{(-1)^n{2n \choose n}^5 \over 2^{20n}} (820n^2+180n+13)={32 \over \pi^2}.",
    r"& {1 \over 8 } \sum_{n=0}^{\infty} {\left( 1 \over 2 \right)_{n}^3 \left( 1 \over 4 \right)_{2n} \over (n!)^3 "
    r"\left( 1 \over 4 \right)_ n^2 2 ^{6n}} {240n^2+110n+11 \over (4n+1)^2}= {\pi \over \Gamma({3 \over 4})^4}, "
    r"\nonumber \\ & {1 \over 8 } \sum_{n=0}^{\infty} {(-1)^n \left( 1 \over 2 \right)_{2n}^3 \left( 1 \over 2 "
    r"\right)_{n}^3 \over (n!)^3 \left( 1 \over 4 \right)_ {2n}^2 \left( {1 \over 4} \right)_n^2 2^{12n}} "
    r"{26240n^4+41184n^3+21448n^2+4170n+279 \over (8n+1)^2(8n+5)^2} = {\pi \over \Gamma({3 \over 4})^4}.",
)

LABELS = ("1a", "1b", "1c", "1d", "2a", "2b", "2c", "2d")
OUTPUTS = ("source", "wz_points", "wz_failures_1", "wz_failures_2", "sums_within", "worst_digits", "digits", "terms",
           "termwise_k0", "gamma_forms", "conditions_met", "conditions_total", "test_passed", "controls_passed",
           "controls_total")


class Refused(Exception):
    pass


# --- reading (rule 1) ----------------------------------------------------------------------------------------------

def read_bytes(path, sha256):
    with open(path, "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha256:
        raise Refused(f"{path}: sha256 {got}, not the registered {sha256}")
    return data


def tex_of(eprint):
    try:
        return gzip.decompress(eprint).decode("utf-8")
    except (OSError, EOFError, UnicodeDecodeError) as e:
        raise Refused(f"the e-print is not one gzipped UTF-8 TeX file: {e}") from None


def flatten(tex):
    """TeX comments removed (an unescaped % to the end of its line), then whitespace collapsed."""
    lines = [re.sub(r"(?<!\\)%.*$", "", line) for line in tex.split("\n")]
    return re.sub(r"\s+", " ", " ".join(lines))


def check_source(tex):
    flat = flatten(tex)
    for s in FORMULAS:
        if s not in flat:
            raise Refused(f"the e-print does not hold, as read: {s[:80]!r}")


# --- exact pieces ----------------------------------------------------------------------------------------------------

def C(a, b):
    """C(a, b) for 0 <= b <= a, exactly; refused anywhere else, so no point outside the binomial forms is used."""
    if not 0 <= b <= a:
        raise ValueError(f"C({a}, {b}) lies outside the binomial forms")
    return math.comb(a, b)


def C0(a, b):
    """C(a, b), and 0 outside 0 <= b <= a (the control pair only)."""
    return math.comb(a, b) if 0 <= b <= a else 0


class Poch:
    """The rising factorial (a)_m = a (a + 1) ... (a + m - 1) for one a, built up exactly and kept."""

    def __init__(self, a):
        self.a, self.v = Fraction(a), [Fraction(1)]

    def __call__(self, m):
        while len(self.v) <= m:
            self.v.append(self.v[-1] * (self.a + len(self.v) - 1))
        return self.v[m]


QUARTER, HALF = Poch(Fraction(1, 4)), Poch(Fraction(1, 2))


def sign(m):
    return -1 if m & 1 else 1


# --- the pairs (rule 2) ----------------------------------------------------------------------------------------------

def r1(n, k):
    return Fraction(C(2 * k, k) ** 2 * C(2 * n, n) ** 2 * C(4 * n - 2 * k, 2 * n - k), C(2 * n, k) * C(n + k, n))


def g1(n, k, lin=3):
    return Fraction(sign(n + k) * (20 * n + 2 * k + lin), 2 ** (10 * n + 2 * k)) * r1(n, k)


def f1(n, k):
    return Fraction(64 * sign(n + k) * n * n, (4 * n - 2 * k - 1) * 2 ** (10 * n + 2 * k)) * r1(n, k)


def r2(n, k):
    return Fraction(C(2 * k, k) ** 3 * C(2 * n, n) ** 4 * C(4 * n - 2 * k, 2 * n - k), C(2 * n, k) * C(n + k, n) ** 2)


def g2(n, k):
    return Fraction(sign(k) * (120 * n * n + 84 * n * k + 34 * n + 10 * k + 3), 2 ** (16 * n + 4 * k)) * r2(n, k)


def f2(n, k):
    return Fraction(512 * sign(k) * n ** 3, (4 * n - 2 * k - 1) * 2 ** (16 * n + 4 * k)) * r2(n, k)


def wz_failures(F, G, n_max, k_range):
    """The points (n, k), n from 1 to n_max and k in k_range(n), where F(n+1, k) - F(n, k) != G(n, k+1) - G(n, k);
    and the number of points checked."""
    bad, checked = [], 0
    for n in range(1, n_max + 1):
        for k in k_range(n):
            checked += 1
            if F(n + 1, k) - F(n, k) != G(n, k + 1) - G(n, k):
                bad.append((n, k))
    return bad, checked


def paper_ks(n):
    return range(0, 2 * n)


def control_f(n, k):
    return Fraction(C0(n, k), 2 ** n)


def control_g(n, k):
    return Fraction(-C0(n, k - 1), 2 ** (n + 1))


# --- the Gamma forms at integer k (rule 6) --------------------------------------------------------------------------

def gamma_g1(n, k):
    core = HALF(2 * n - k) * HALF(n) ** 3 * HALF(k) ** 2 / (math.factorial(n + k) * math.factorial(2 * n) ** 2)
    return (20 * n + 2 * k + 3) * sign(n + k) * core


def gamma_f1(n, k):
    core = HALF(2 * n - k) * HALF(n) ** 3 * HALF(k) ** 2 / (math.factorial(n + k) * math.factorial(2 * n) ** 2)
    return Fraction(64 * n * n, 4 * n - 2 * k - 1) * sign(n + k) * core


def gamma_g2(n, k):
    core = HALF(2 * n - k) * HALF(n) ** 6 * HALF(k) ** 3 / (math.factorial(n + k) ** 2 * math.factorial(2 * n) ** 3)
    return (120 * n * n + 84 * n * k + 34 * n + 10 * k + 3) * sign(k) * core


def gamma_f2(n, k):
    core = HALF(2 * n - k) * HALF(n) ** 6 * HALF(k) ** 3 / (math.factorial(n + k) ** 2 * math.factorial(2 * n) ** 3)
    return Fraction(512 * n ** 3, 4 * n - 2 * k - 1) * sign(k) * core


# --- the summands as printed (rule 4) -------------------------------------------------------------------------------

def s1a(n):
    return Fraction(sign(n) * C(4 * n, 2 * n) * C(2 * n, n) ** 2 * (20 * n + 3), 2 ** (10 * n))


def s1b(n):
    return Fraction(C(2 * n, n) ** 3 * (42 * n + 5), 2 ** (12 * n))


def s1c(n):
    f = math.factorial(n)
    return (sign(n) * HALF(n) * QUARTER(2 * n) / (f * f * QUARTER(n) * 2 ** (4 * n))
            * Fraction(40 * n + 7, 4 * n + 1))


def s1d(n):
    f = math.factorial(n)
    return (HALF(2 * n) ** 2 * HALF(n) / (f * f * QUARTER(2 * n) * QUARTER(n) * 2 ** (8 * n))
            * Fraction(112 * n * n + 88 * n + 11, (8 * n + 1) * (8 * n + 5)))


def s2a(n):
    return Fraction(C(4 * n, 2 * n) * C(2 * n, n) ** 4 * (120 * n * n + 34 * n + 3), 2 ** (16 * n))


def s2b(n):
    return Fraction(sign(n) * C(2 * n, n) ** 5 * (820 * n * n + 180 * n + 13), 2 ** (20 * n))


def s2c(n):
    f = math.factorial(n)
    return (HALF(n) ** 3 * QUARTER(2 * n) / (f ** 3 * QUARTER(n) ** 2 * 2 ** (6 * n))
            * Fraction(240 * n * n + 110 * n + 11, (4 * n + 1) ** 2))


def s2d(n):
    f = math.factorial(n)
    p = 26240 * n ** 4 + 41184 * n ** 3 + 21448 * n * n + 4170 * n + 279
    return (sign(n) * HALF(2 * n) ** 3 * HALF(n) ** 3 / (f ** 3 * QUARTER(2 * n) ** 2 * QUARTER(n) ** 2 * 2 ** (12 * n))
            * Fraction(p, (8 * n + 1) ** 2 * (8 * n + 5) ** 2))


# label: (summand, factor in front, whether sqrt 2 is in the factor, the printed value's key)
SUMS = {
    "1a": (s1a, Fraction(1), False, "8/pi"),
    "1b": (s1b, Fraction(1, 2), False, "8/pi"),
    "1c": (s1c, Fraction(1, 8), True, "sqrt(pi)/Gamma(3/4)^2"),
    "1d": (s1d, Fraction(3, 8), True, "sqrt(pi)/Gamma(3/4)^2"),
    "2a": (s2a, Fraction(1), False, "32/pi^2"),
    "2b": (s2b, Fraction(1, 4), False, "32/pi^2"),
    "2c": (s2c, Fraction(1, 8), False, "pi/Gamma(3/4)^4"),
    "2d": (s2d, Fraction(1, 8), False, "pi/Gamma(3/4)^4"),
}


# --- fixed point (rules 3 and 4) -------------------------------------------------------------------------------------

def nearest(num, den):
    """The integer nearest num/den (den > 0; a half rounds up)."""
    q, r = divmod(num, den)
    return q + (2 * r >= den)


def fixed(x, scale):
    """The integer nearest x * scale, for a fraction x."""
    return nearest(x.numerator * scale, x.denominator)


def sum_series(term, scale, extra=EXTRA, tail=TAIL, limit=20_000):
    """sum_n term(n), in units of 1/scale: each term rounded and added until one is below 10 ** -5 units (that is,
    10^-(P + 5) at scale 10^P), then `extra` more. Returns (the total, the terms added, the last term, the largest
    ratio |t(m+1)/t(m)| over the next `tail` terms)."""
    total, n = 0, 0
    small = Fraction(1, scale * 10 ** 5)
    while True:
        t = term(n)
        total += fixed(t, scale)
        if abs(t) < small:
            break
        n += 1
        if n > limit:
            raise AssertionError(f"no term below 10^-5 units in {limit} terms")
    for _ in range(extra):
        n += 1
        t = term(n)
        total += fixed(t, scale)
    worst, prev = Fraction(0), t
    for m in range(n + 1, n + 1 + tail):
        cur = term(m)
        worst = max(worst, abs(cur / prev))
        prev = cur
    return total, n + 1, t, worst


def arctan_inv(x, scale):
    """arctan(1/x) * scale, by the Taylor series in fixed point (truncating; a few units of error)."""
    total = term = scale // x
    x2, k, s = x * x, 1, -1
    while term:
        term //= x2
        total += s * (term // (2 * k + 1))
        s, k = -s, k + 1
    return total


def pi_machin(digits):
    guard = 10
    scale = 10 ** (digits + guard)
    return (16 * arctan_inv(5, scale) - 4 * arctan_inv(239, scale)) // 10 ** guard


def _chud(a, b):
    """Binary splitting of the Chudnovskys' series: P, Q, T over [a, b)."""
    if b - a == 1:
        if a == 0:
            p = q = 1
        else:
            p = (6 * a - 5) * (2 * a - 1) * (6 * a - 1)
            q = a * a * a * 10939058860032000
        t = p * (13591409 + 545140134 * a)
        return p, q, -t if a & 1 else t
    m = (a + b) // 2
    p1, q1, t1 = _chud(a, m)
    p2, q2, t2 = _chud(m, b)
    return p1 * p2, q1 * q2, t1 * q2 + p1 * t2


def pi_chudnovsky(digits):
    guard = 10
    terms = (digits + guard) // 14 + 2
    _, q, t = _chud(0, terms)
    scale = 10 ** (digits + guard)
    sqrt_10005 = math.isqrt(10005 * scale * scale)
    return (426880 * sqrt_10005 * q // t) // 10 ** guard


def agm(a, b, steps=200):
    """The arithmetic-geometric mean of two integers (in units of 1/scale), until the means agree within 2 units."""
    for _ in range(steps):
        if abs(a - b) <= 2:
            return (a + b) // 2
        a, b = (a + b) // 2, math.isqrt(a * b)
    raise AssertionError("the AGM did not converge")


def exp_fixed(x, scale):
    """e^x * scale for x >= 0 given as x * scale, by its Taylor series in fixed point."""
    total = term = scale
    k = 1
    while term:
        term = term * x // (scale * k)
        total += term
        k += 1
    return total


def theta_squared(pi_s, scale):
    """(1 + 2 sum_{m>=1} e^(-pi m^2))^2 * scale, with q = e^-pi = 1/e^pi and q^(m^2) built as q^(m^2) q^(2m+1)."""
    q = nearest(scale * scale, exp_fixed(pi_s, scale))
    q2 = q * q // scale
    power, odd, total = q, q * q2 // scale, 0           # q^(m^2) and q^(2m+1) at m = 1
    while power:
        total += power
        power = power * odd // scale
        odd = odd * q2 // scale
    theta = scale + 2 * total
    return theta * theta // scale


def constants(digits):
    scale = 10 ** digits
    pi_a, pi_b = pi_machin(digits), pi_chudnovsky(digits)
    root2 = math.isqrt(2 * scale * scale)
    a = agm(scale, root2)
    values = {"8/pi": nearest(8 * scale * scale, pi_a),
              "32/pi^2": nearest(32 * scale ** 3, pi_a * pi_a),
              "sqrt(pi)/Gamma(3/4)^2": nearest(root2 * scale, a),
              "pi/Gamma(3/4)^4": nearest(2 * scale ** 3, a * a)}
    return {"scale": scale, "pi": pi_a, "pi_chudnovsky": pi_b, "sqrt2": root2, "agm": a,
            "theta_squared": theta_squared(pi_a, scale), "values": values}


def as_decimal(x, digits, shown=50):
    s = str(x).rjust(digits + 1, "0")
    return s[:-digits] + "." + s[-digits:][:shown]


# --- the test and what is reported beside it (rules 5 and 6) -------------------------------------------------------

def evaluate(label, k, digits=P, threshold=THRESHOLD):
    """One sum of rule 4 against its printed value: the dict of what rule 5 and rule 6 read."""
    term, front, with_root2, key = SUMS[label]
    scale = k["scale"]
    total, used, last, worst = sum_series(term, scale)
    value = nearest(total * front.numerator, front.denominator)
    if with_root2:
        value = nearest(value * k["sqrt2"], scale)
    printed = k["values"][key]
    diff = abs(value - printed)
    margin = used + 100 + 2 * fixed(abs(last), scale) + 1
    tail_ok = worst < Fraction(1, 2)
    within = tail_ok and diff + margin < 10 ** (digits - threshold)
    cap = digits - 10                                  # CAP at P digits
    agree = cap if diff <= margin else min(cap, int(digits - math.log10(diff)))
    return {"label": label, "printed": key, "terms": used, "diff_units": diff, "margin_units": margin,
            "tail_ratio": f"{float(worst):.6f}", "tail_ok": tail_ok, "within": within, "digits": agree,
            "sum": as_decimal(value, digits)}


def conditions(wz1, wz2, sums):
    cond = {f"pair 1: the WZ equation at all {wz1[1]} points": not wz1[0],
            f"pair 2: the WZ equation at all {wz2[1]} points": not wz2[0]}
    for s in sums:
        cond[f"{s['label']}: within 10^-{THRESHOLD} of {s['printed']}"] = s["within"]
    return cond


def termwise(n_max=N_TERMWISE):
    """G(n, 0) and H(n, 0) against the printed summands of sums a and b, n from 0 to n_max: the n that differ."""
    out = {"1a": [], "1b": [], "2a": [], "2b": []}
    for n in range(n_max + 1):
        if g1(n, 0) != s1a(n):
            out["1a"].append(n)
        if f1(n + 1, n) + g1(n, n) != Fraction(1, 2) * s1b(n):
            out["1b"].append(n)
        if g2(n, 0) != s2a(n):
            out["2a"].append(n)
        if f2(n + 1, n) + g2(n, n) != Fraction(1, 4) * s2b(n):
            out["2b"].append(n)
    return out


def gamma_agreement(n_max=N_GAMMA):
    """The Gamma forms at integer k against the binomial forms: (points, the points that differ, by pair)."""
    bad, points = {"1": [], "2": []}, 0
    for n in range(n_max + 1):
        for k in range(2 * n + 1):
            points += 1
            if gamma_g1(n, k) != g1(n, k) or gamma_f1(n, k) != f1(n, k):
                bad["1"].append((n, k))
            if gamma_g2(n, k) != g2(n, k) or gamma_f2(n, k) != f2(n, k):
                bad["2"].append((n, k))
    return points, bad


def controls(k, digits=P):
    scale = k["scale"]
    third = Poch(Fraction(3, 4))
    total, used, last, worst = sum_series(lambda n: Fraction(C(2 * n, n), 16 ** n), scale)
    want = nearest(2 * scale * scale, math.isqrt(3 * scale * scale))
    margin = used + 10 + 2 * fixed(abs(last), scale)
    good, _ = wz_failures(control_f, control_g, N_WZ, lambda n: range(0, n + 1))
    broken, _ = wz_failures(f1, lambda n, kk: g1(n, kk, lin=4), 4, paper_ks)
    return {
        "Machin's and the Chudnovskys' pi agree within 10^-(P - 10)": abs(k["pi"] - k["pi_chudnovsky"]) < 10 ** 10,
        "pi gives its first 50 printed decimals": as_decimal(k["pi"], digits, 50) == PI50,
        "phi(e^-pi)^2 agrees with sqrt 2/AGM(1, sqrt 2) within 10^-(P - 10)":
            abs(k["theta_squared"] - k["values"]["sqrt(pi)/Gamma(3/4)^2"]) < 10 ** 10,
        "the WZ check accepts the pair for sum_k C(n, k) = 2^n": not good,
        "the WZ check finds a failing point when the first pair's 3 is made 4": bool(broken),
        "the summation gives sum C(2n, n)/16^n = 2/sqrt 3 within its margin, its tail check holding":
            abs(total - want) <= margin and worst < Fraction(1, 2),
        "(1/2)_n = (2n)!/(4^n n!) and (1/4)_n (3/4)_n = (4n)!/(64^n (2n)!) for n up to 50":
            all(HALF(n) == Fraction(math.factorial(2 * n), 4 ** n * math.factorial(n))
                and QUARTER(n) * third(n) == Fraction(math.factorial(4 * n), 64 ** n * math.factorial(2 * n))
                for n in range(51)),
    }


def listing(bad, shown=4):
    if not bad:
        return "none"
    head = ", ".join(str(x) for x in bad[:shown])
    return head + (f" and {len(bad) - shown} more" if len(bad) > shown else "")


def run(seed, inputs="inputs", results="results", log=sys.stderr):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    raw = read_bytes(os.path.join(inputs, INPUT[0]), INPUT[1])
    check_source(tex_of(raw))
    print("source: every formula found", file=log)

    k = constants(P)
    ctl = controls(k)
    print(f"controls: {sum(ctl.values())} of {len(ctl)}", file=log)
    if not all(ctl.values()):
        raise AssertionError(f"a control failed: {[c for c, ok in ctl.items() if not ok]}")

    wz1 = wz_failures(f1, g1, N_WZ, paper_ks)
    wz2 = wz_failures(f2, g2, N_WZ, paper_ks)
    print(f"WZ: pair 1 {len(wz1[0])} failing of {wz1[1]}, pair 2 {len(wz2[0])} of {wz2[1]}", file=log)
    sums = []
    for label in LABELS:
        sums.append(evaluate(label, k))
        print(f"sum {label}: {sums[-1]['terms']} terms, {sums[-1]['digits']} digits", file=log)
    cond = conditions(wz1, wz2, sums)

    tw = termwise()
    points, gbad = gamma_agreement()
    tw_text = ("G(n, 0), H(n, 0) are the printed summands, n 0 to 60, both pairs" if not any(tw.values()) else
               "differ: " + "; ".join(f"{lab} at n = {listing(v, 3)}" for lab, v in tw.items() if v))
    gm_text = (f"the Gamma forms equal the binomial ones at all {points} points of each pair" if not any(gbad.values())
               else "differ: " + "; ".join(f"pair {p} at {listing(v, 3)}" for p, v in gbad.items() if v))
    values = {
        "source": "the e-print holds both pairs, their Gamma forms, H and the eight sums as read",
        "wz_points": wz1[1],
        "wz_failures_1": len(wz1[0]),
        "wz_failures_2": len(wz2[0]),
        "sums_within": sum(s["within"] for s in sums),
        "worst_digits": min(s["digits"] for s in sums),
        "digits": ", ".join(f"{s['label']} {s['digits']}" for s in sums),
        "terms": ", ".join(f"{s['label']} {s['terms']}" for s in sums),
        "termwise_k0": tw_text,
        "gamma_forms": gm_text,
        "conditions_met": sum(cond.values()),
        "conditions_total": len(cond),
        "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()),
        "controls_total": len(ctl),
    }
    out = {name: values[name] for name in OUTPUTS}
    for name, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{name}: longer than {LIMIT} characters: {v}")
    detail = {"input": {"name": INPUT[0], "sha256": INPUT[1]}, "digits": P, "threshold": THRESHOLD,
              "conditions": cond, "controls": ctl,
              "wz_failing_points": {"1": wz1[0][:50], "2": wz2[0][:50]},
              "sums": sums, "termwise_k0": tw, "gamma_points": points, "gamma_differ": {p: v[:50] for p, v in gbad.items()},
              "constants": {"pi": as_decimal(k["pi"], P, P), "agm(1, sqrt 2)": as_decimal(k["agm"], P, P),
                            "phi(e^-pi)^2": as_decimal(k["theta_squared"], P, P),
                            **{key: as_decimal(v, P, P) for key, v in k["values"].items()}}}
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
        sys.exit(f"guillera: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
