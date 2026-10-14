#!/usr/bin/env python3
"""Zeilberger and Zudilin's bound on the irrationality measure of pi: the printed constants recomputed, the saddle points,
and Propositions 1 and 2 sampled, exactly.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:80b8e1febcd7cc56) is from Zeilberger and
Zudilin, "The Irrationality Measure of Pi is at most 7.103205334137...", Moscow J. Comb. Number Th. 9 (2020) 407-419,
arXiv:1912.06345v2: "We use a variant of Salikhov's ingenious proof that the irrationality measure of $pi$ is at most
$7.606308\\dots$ to prove that, in fact, it is at most $7.103205334137\\dots$."

Its registered test: refuted if, computed exactly: 1 + (log N3 + c)/(-log|N1| - c), c = 4 - (5/2) log 2 - pi/(2 sqrt 3)
+ log(3 sqrt 3/4), with N3 the real and N1 a complex zero of 108N^3 - 2359989N^2 + 138304N - 2048, differs from
7.103205334137 in a printed digit; or those zeros are not g(y) = y(y^2+6y+25)^2/(y-25)^3 at the zeros of g'; or, for
some n <= 150, Lemma 2 fails or 2^(2-floor(5n/2)) L_n I_n is not in Z + Z pi (Proposition 1); or |b_(n+1)/b_n|,
Richardson-extrapolated (order 4) at n = 145, is 1e-5 or more from N3 in ratio; or |I_n|^(1/n) > 1.05 |N1| for some n
from 90 to 150.

The input is the paper's v2 e-print from arXiv (one gzipped TeX file), checked against its SHA-256 and read as data
(decompressed with the standard library and read as text; nothing in it is run). Every rule below was fixed before any
of the quantities it tests was computed; the seed is not used, as nothing here is random.

1. The source. With its TeX comments removed and its whitespace collapsed, pimeas.tex must hold every formula and
   printed constant in PRINTED_TEX below (the integrals of equation (1), the set P_n, L_n, Lemma 2, Propositions 1
   and 2, g and g'/g, the forms I'_n and the closing bound); otherwise the run is refused. What is computed is what
   those formulas say: I_n = i(-1)^(n+1) times the integral from -1-2i to -1+2i of
   R(x) = 5 x^(2n) (x^4 + 6x^2 + 25)^(2n) / ((5+x)^(3n+1) (5-x)^(3n+1)).
2. The constants, in decimal arithmetic to PRECISION digits, pi by Machin's formula in integers: N3, the one real zero of
   the printed cubic (by bisection; the cubic's discriminant must be negative, so its other zeros are a complex pair
   N1, N2 = conj(N1)); |N1|^2 = (2048/108)/N3, the product of the zeros over N3; Re N1 = (2359989/108 - N3)/2;
   c = 4 - (5/2) ln 2 - pi/(2 sqrt 3) + ln(3 sqrt 3/4); E1 = ln|N1| + c and E3 = ln N3 + c; and mu = 1 + E3/(-E1).
   Condition 1: the decimal expansion of mu begins 7.103205334137 (the abstract's digits). Beside it, each of the
   paper's other printed constants (its 30-digit bound, E1, E3, |N1|, N3, N1, the limit of log(Phi_n)/n, the zeros y of
   g') is compared with the computed value, as printed if the printed digits are its digits cut or rounded.
3. The saddle points, exactly in rationals: the numerator of g'/g is derived from g by polynomial arithmetic (and
   compared with the printed 2y^3 - 125y^2 - 500y - 625); in the algebra Q[y]/(that numerator) the matrix of
   multiplication by g = y (y^2+6y+25)^2 (y-25)^(-3) is formed, and its characteristic polynomial, which is the product
   of N - g(y_j) over the three zeros y_j, is compared with the printed cubic divided by 108. Condition 2: equal.
4. The integrals, exactly, for n = 0 to N_MAX = 150. With t = x + 5, (x+5)^(3n+1) R(x) = 5 h(t)^(2n) / (10 - t)^(3n+1),
   h(t) = x^5 + 6x^3 + 25x at x = t - 5; its Taylor coefficients give the A_j of the paper's (3), A_j being the
   coefficient of t^(3n-j) (j from 3n down to -(4n-1)). The polynomial part P(x) of (3) is P~(x^2), P~ the quotient of
   5 y^n (y^2+6y+25)^(2n) by (25-y)^(3n+1), read off the expansion in u = y - 25 (y (y^2+6y+25)^2 = w(u) at y = 25+u).
   Powers of h and w are taken by J. C. P. Miller's recurrence in exact integers. Integrating term by term along the
   segment (the logarithms of the j = 0 term give pi i/2, as the paper computes), I_n = a_n + b_n pi with
   a_n = 2 (-1)^n (S_P + S_A), S_P = sum_k p_k Im((-1+2i)^(2k+1))/(2k+1) over P~'s coefficients p_k,
   S_A = sum_{j=1}^{3n} (A_j/j)(Im((4+2i)^j)/20^j + Im((6+2i)^j)/40^j), and b_n = (-1)^n A_0/2, all exact rationals.
   P_n is the set of primes p > max(5, sqrt(3n)) with 1/2 <= {n/p} < 2/3, Phi_n their product, and
   L_n = lcm(1, ..., 4n)/Phi_n. Condition 3 (Lemma 2): for every n from 1 to 150, every p in P_n and every j from
   -4n+1 to 3n divisible by p, p divides 10^(-j) A_j (computed modulo p from the exact Taylor coefficients).
   Condition 4 (Proposition 1): for every n from 0 to 150, 2^(2-floor(5n/2)) L_n a_n and 2^(2-floor(5n/2)) L_n b_n
   are integers.
5. Growth. r_n = |b_(n+1)/b_n| exactly; its order-4 Richardson extrapolation at n = 145,
   sum_{i=0}^{4} (-1)^(4-i) (145+i)^4 r_(145+i) / (i! (4-i)!), which removes the terms in 1/n to 1/n^4 of its
   expansion. Condition 5: within 1e-5 of N3 in ratio. Decay: |I_n| = |a_n + b_n pi| in decimal arithmetic carried far
   enough that at least 40 significant digits survive the cancellation (checked), for n = 90 to 150 (a full turn of
   N1's argument, about 61 steps). Condition 6: |I_n|^(1/n) <= 1.05 |N1| for every such n.
   test_passed is 1 if all six hold.
6. Beside the test: Lemma 1's powers of 2 and 5 in A_j (j = 0 to 3n, n <= 150); how much room Proposition 1's power of
   2 leaves; the signs of b_n; the forms I'_n and b'_n at n = 150 with the actual L_n, their growth rates and the bound
   they would give; and the limit of log(Phi_n)/n (Hata's Lemma 2.2), with Phi_n computed at n = 10^6.
7. Controls: Machin's pi against its first 50 printed decimals; the printed cubic has one real zero and a complex pair;
   Miller's recurrence against repeated multiplication; I_0 = pi/4 (a_0 = 0, b_0 = 1/4); the partial fractions (3)
   reproducing R exactly at x = 1/3 and x = 7/2 for n = 1 to 3; a_n + b_n pi against Gauss-Legendre quadrature of both
   forms of (1) for n = 1 to 6 (relative 1e-9); Richardson's formula on a sequence with a known limit; the digamma
   values psi(2/3) - psi(1/2), summed from their asymptotic series, against pi/(2 sqrt 3) - ln(3 sqrt 3/4), the paper's
   (Phi) to 40 digits; and, as a negative control, the earlier version of Lemma 2 that the paper's remark withdraws
   (every p in P_n with p | j, j from -4n to 3n, dividing T(m) for every m in M_j) found false at some n <= 10.

What it cannot check: the propositions for every n (only n <= 150), the Poincare lemma and the contour deformation
behind Proposition 2, and Salikhov's Lemma 1 that turns such forms into a bound; only what is printed and what the
integrals are for n up to 150.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 pi/zz.py
"""

import cmath
import decimal
import gzip
import hashlib
import itertools
import json
import math
import os
import re
import sys
from decimal import Decimal
from fractions import Fraction

INPUTS = {"eprint": ("arXiv-1912.06345v2.gz", "f663c4070f3cb10fcce374225fff6fcbb6f22fb0b4c986606cf3a357ac2e6836")}
PRINTED_TEX = (
    r"to prove that, in fact, it is at most $7.103205334137\dots$",
    r"I_n &=5i\int_{4-2i}^{4+2i}\frac{(x-5)^{2n}(x-4+2i)^{2n}(x-4-2i)^{2n}(x-6+2i)^{2n}(x-6-2i)^{2n}} "
    r"{x^{3n+1}(x-10)^{3n+1}}\,\d x",
    r"&=i(-1)^{n+1}\int_{-1-2i}^{-1+2i}\frac{5x^{2n}(x+1+2i)^{2n}(x+1-2i)^{2n}(x-1+2i)^{2n}(x-1-2i)^{2n}} "
    r"{(5+x)^{3n+1}(5-x)^{3n+1}}\,\d x.",
    r"&=\frac{5x^{2n}(x^4+6x^2+25)^{2n}}{(5+x)^{3n+1}(5-x)^{3n+1}}",
    r"R(x)=P(x)+\sum_{j=0}^{3n}\biggl(\frac{A_j}{(5+x)^{j+1}}+\frac{A_j}{(5-x)^{j+1}}\biggr)",
    r"\cP_n=\biggl\{p>\max\{5,\sqrt{3n}\}:\frac12\le\Bigl\{\frac np\Bigr\}<\frac23\biggr\}",
    r"if $p\mid j$ for $j\in\{-4n+1,-4n+2,\dots,3n\}$, then $A_j\equiv0\pmod p$",
    r"An earlier version of the lemma claimed that any prime $p\in\cP_n$, $p\mid j$ for $j\in\{-4n,-4n+1,\dots,3n\}$, "
    r"divides $T(\bm)$ for all $\bm\in\cM_j$",
    r"T(\bm)=T(m_0,m_1,\dots,m_5) =\binom{3n+m_0}{m_0}\prod_{\ell=1}^5\binom{2n}{m_\ell}\in\mathbb Z.",
    r"\Phi=\Phi_n=\prod_{p\in\cP_n}p",
    r"L_n=\frac{\lcm(1,2,\dots,4n)}{\Phi_n}\in\mathbb Z.",
    r"=\frac{\Gamma'(2/3)}{\Gamma(2/3)}-\frac{\Gamma'(1/2)}{\Gamma(1/2)} =\frac\pi{2\sqrt3}-\log\frac{3\sqrt3}4 "
    r"=0.64527561\dotsc",
    r"2^{-\lfloor5n/2\rfloor+2}L_n\times I_n\in\mathbb Z+\mathbb Z\pi.",
    r"\limsup_{n\to\infty}|I_n|^{1/n}=|N_1|=0.029458495928\dots",
    r"\lim_{n\to\infty}b_n^{1/n}=N_3=21851.691396\dots",
    r"N_{1,2}=0.02930189\hdots \pm i\,0.00303351\dots",
    r"108N^3-2359989N^2+138304N-2048.",
    r"g(y)=\frac{y(y^2+6y+25)^2}{(y-25)^3}",
    r"y_{1,2}=-1.91975076\hdots \mp i\,1.01250889\dots",
    r"y_3=66.33950152\dots",
    r"\frac{g'(y)}{g(y)}=\frac{2y^3-125y^2-500y-625}{y(y^2+6y+25)(y-25)}.",
    r"Then $N_j=g(y_j)$ for $j=1,2,3$.",
    r"I_n'=2^{-\lfloor5n/2\rfloor+2}L_nI_n=a_n'+b_n'\pi,",
    r"&=\log|N_1|-\frac52\,\log2+4-\frac\pi{2\sqrt3}+\log\frac{3\sqrt3}4 =-1.90291648559998\dots",
    r"&=\log N_3-\frac52\,\log2+4-\frac\pi{2\sqrt3}+\log\frac{3\sqrt3}4 =11.613890045331\dots",
    r"1+\frac{11.613890045331\dots}{1.90291648559998\dots} =7.10320533413700172750577342281\dotsc.",
)
CUBIC = (-2048, 138304, -2359989, 108)          # the printed 108N^3 - 2359989N^2 + 138304N - 2048, lowest power first
GPRIME_NUM = (-625, -500, -125, 2)              # the printed numerator of g'/g
ABSTRACT_DIGITS = "7.103205334137"
PRINTED = {                                      # the paper's other printed constants, as decimal strings
    "bound_30": "7.10320533413700172750577342281",
    "E1": "-1.90291648559998", "E3": "11.613890045331",
    "absN1": "0.029458495928", "N3": "21851.691396",
    "reN1": "0.02930189", "imN1": "0.00303351",
    "phi_limit": "0.64527561",
    "rey1": "-1.91975076", "imy1": "1.01250889", "y3": "66.33950152",
}
N_MAX = 150
RICHARDSON_N, RICHARDSON_ORDER, RATIO_TOL = 145, 4, Fraction(1, 10 ** 5)
DECAY_FROM, DECAY_TO, DECAY_MARGIN = 90, 150, Fraction(105, 100)
PRECISION = 80
HATA_N = 10 ** 6
QUAD_N, QUAD_NODES, QUAD_TOL = 6, 96, 1e-9
PI50 = "3.14159265358979323846264338327950288419716939937510"
OUTPUTS = ("source", "bound", "bound_printed", "constants", "saddle_points", "lemma_2", "proposition_1", "lemma_1",
           "ratio", "ratio_relative", "decay", "decay_max_ratio", "forms_150", "hata", "conditions_met",
           "conditions_total", "test_passed", "controls_passed", "controls_total")
LIMIT = 200


class Refused(Exception):
    pass


# --- reading -----------------------------------------------------------------------------------------------------

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
    for s in PRINTED_TEX:
        if s not in flat:
            raise Refused(f"the e-print does not hold, as read: {s[:80]!r}")


# --- exact polynomials (lists of coefficients, lowest power first) ---------------------------------------------------

def pmul(a, b):
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b):
                out[i + j] += x * y
    return out


def padd(a, b):
    out = [0] * max(len(a), len(b))
    for i, x in enumerate(a):
        out[i] += x
    for i, x in enumerate(b):
        out[i] += x
    return out


def pscale(a, s):
    return [s * x for x in a]


def ppow(a, m):
    out = [1]
    for _ in range(m):
        out = pmul(out, a)
    return out


def compose_shift(a, s):
    """a(t + s) as coefficients in t."""
    out = [0]
    for c in reversed(a):
        out = padd(pmul(out, [s, 1]), [c])
    return out


def trim(a):
    a = list(a)
    while len(a) > 1 and a[-1] == 0:
        a.pop()
    return a


def miller_power(h, m, terms):
    """The first `terms` Taylor coefficients of h(t)^m, exactly, by J. C. P. Miller's recurrence
    h0 k f_k = sum_{i>=1} (m i - k + i) h_i f_(k-i), which needs h(0) != 0; every division is exact."""
    h0 = h[0]
    if h0 == 0:
        raise ValueError("Miller's recurrence needs h(0) != 0")
    d = len(h) - 1
    f = [h0 ** m] + [0] * (terms - 1)
    for k in range(1, terms):
        acc = 0
        for i in range(1, min(k, d) + 1):
            if h[i]:
                acc += (m * i - k + i) * h[i] * f[k - i]
        q, r = divmod(acc, k * h0)
        if r:
            raise AssertionError(f"Miller's recurrence left a remainder at k = {k}")
        f[k] = q
    return f


X5 = [0, 25, 0, 6, 0, 1]                          # x^5 + 6x^3 + 25x = x (x^4 + 6x^2 + 25)
H = trim(compose_shift(X5, -5))                   # h(t) = that polynomial at x = t - 5
W = trim(pmul([0, 1], ppow([25, 6, 1], 2)))        # y (y^2 + 6y + 25)^2
W_U = trim(compose_shift(W, 25))                  # w(u) = the same at y = 25 + u


def expand_shifted(coeffs, s):
    """sum_m coeffs[m] (y - s)^m as coefficients of y^0, y^1, ... (Horner, exactly)."""
    out = []
    for cm in reversed(coeffs):
        new = [0] * (len(out) + 1)
        for i, v in enumerate(out):
            new[i + 1] += v
            new[i] -= s * v
        new[0] += cm
        out = new
    return out


def gpow_imag(z, count):
    """Im(z^1), ..., Im(z^count) for a Gaussian integer z = (re, im)."""
    re_, im_ = z
    a, b = 1, 0
    out = []
    for _ in range(count):
        a, b = a * re_ - b * im_, a * im_ + b * re_
        out.append(b)
    return out


# --- primes, P_n, L_n -----------------------------------------------------------------------------------------------

def primes_upto(m):
    if m < 2:
        return []
    sieve = bytearray([1]) * (m + 1)
    sieve[0] = sieve[1] = 0
    for p in range(2, int(m ** 0.5) + 1):
        if sieve[p]:
            sieve[p * p::p] = bytearray(len(range(p * p, m + 1, p)))
    return [i for i in range(m + 1) if sieve[i]]


def in_P(n, p):
    """p in P_n: p > max(5, sqrt(3n)) and 1/2 <= {n/p} < 2/3 (p prime, checked by the caller)."""
    r = n % p
    return p > 5 and p * p > 3 * n and 2 * r >= p and 3 * r < 2 * p


def P_set(n, primes):
    return [p for p in primes if p <= 2 * n and in_P(n, p)]


def lcm_upto(m, primes):
    out = 1
    for p in primes:
        if p > m:
            break
        q = p
        while q * p <= m:
            q *= p
        out *= q
    return out


def v_p(x, p):
    """The p-adic valuation of a nonzero integer."""
    x = abs(x)
    if p == 2:
        return (x & -x).bit_length() - 1
    k = 0
    while x % p == 0:
        x //= p
        k += 1
    return k


# --- the integrals, exactly -----------------------------------------------------------------------------------------

def binomials_row(n, terms):
    """C(3n + k, k) for k = 0 .. terms - 1."""
    out = [1]
    for k in range(1, terms):
        out.append(out[-1] * (3 * n + k) // k)
    return out


def forms(n, primes):
    """For one n: the scaled partial-fraction coefficients Y_i = 10^(6n+1) A_(3n-i) (i = 0..3n), the polynomial part's
    coefficients p_k (P(x) = sum p_k x^(2k)), and a_n, b_n (exact Fractions) with I_n = a_n + b_n pi."""
    nu = [5 * c for c in miller_power(H, 2 * n, 3 * n + 1)]
    B = binomials_row(n, 3 * n + 1)
    Wk = [B[k] * 10 ** (3 * n - k) for k in range(3 * n + 1)]
    Y = [sum(nu[i - k] * Wk[k] for k in range(i + 1)) for i in range(3 * n + 1)]

    c = [5 * v for v in miller_power(W_U, n, 5 * n + 1)]
    sign = -1 if (3 * n + 1) % 2 else 1
    phat = [sign * c[m + 3 * n + 1] for m in range(2 * n)]
    p = expand_shifted(phat, 25) if phat else []

    L4 = lcm_upto(4 * n, primes)
    ims_b = gpow_imag((-1, 2), 4 * n)                       # Im((-1+2i)^m), m = 1 .. 4n
    num_p = sum(pk * ims_b[2 * k] * (L4 // (2 * k + 1)) for k, pk in enumerate(p))
    S_P = Fraction(num_p, L4)

    if n:
        L3 = lcm_upto(3 * n, primes)
        im4 = gpow_imag((4, 2), 3 * n)
        im6 = gpow_imag((6, 2), 3 * n)
        num_a = sum(Y[3 * n - j] * (im4[j - 1] * 2 ** j + im6[j - 1]) * (L3 // j) * 40 ** (3 * n - j)
                    for j in range(1, 3 * n + 1))
        S_A = Fraction(num_a, L3 * 40 ** (3 * n) * 10 ** (6 * n + 1))
    else:
        S_A = Fraction(0)
    s = -1 if n % 2 else 1
    a = 2 * s * (S_P + S_A)
    b = s * Fraction(Y[3 * n], 2 * 10 ** (6 * n + 1))
    return {"Y": Y, "p": p, "a": a, "b": b}


def A_of(Y, n, j):
    """A_j as a Fraction, j = 0 .. 3n."""
    return Fraction(Y[3 * n - j], 10 ** (6 * n + 1))


def lemma_2(n, P):
    """Lemma 2 for one n: for p in P and j in [-4n+1, 3n] with p | j, whether p | 10^(-j) A_j. The Taylor coefficients
    X_i = 10^(10n) A_(3n-i) (i = 0 .. 7n-1) are integers, 10^(-j) A_j = X_i / 10^(10n+j), and p does not divide 10, so
    the test is X_i = 0 mod p. Returns (cases, holding, failures, residues), residues[(p, j)] = X_(3n-j) mod p for
    j >= 0, which the run compares with the exact route (X_i = 10^(4n-1) Y_i for i <= 3n)."""
    terms = 7 * n
    nu = [5 * c for c in miller_power(H, 2 * n, terms)]
    B = binomials_row(n, terms)
    cases = held = 0
    failures = []
    residues = {}
    for p in P:
        nu_p = [v % p for v in nu]
        W_p = [(B[k] % p) * pow(10, 7 * n - 1 - k, p) % p for k in range(terms)]
        for j in range(-4 * n + 1, 3 * n + 1):
            if j % p:
                continue
            i = 3 * n - j
            x = sum(nu_p[i - k] * W_p[k] for k in range(i + 1)) % p
            cases += 1
            if x == 0:
                held += 1
            else:
                failures.append({"n": n, "p": p, "j": j})
            if j >= 0:
                residues[(p, j)] = x
    return cases, held, failures, residues


def scaled_forms(n, a, b, primes):
    """(a'_n, b'_n) = 2^(2 - floor(5n/2)) L_n (a_n, b_n), exact Fractions."""
    P = P_set(n, primes)
    phi = math.prod(P)
    L = Fraction(lcm_upto(4 * n, primes), phi)
    e = 2 - (5 * n) // 2
    f = L * (Fraction(2) ** e)
    return f * a, f * b, L, e


# --- decimal constants ------------------------------------------------------------------------------------------------

def machin_pi(digits):
    """pi as a Decimal to the given digits (and five more): 16 arctan(1/5) - 4 arctan(1/239) in integers."""
    scale = 10 ** (digits + 10)

    def arctan_inv(x):
        total, term, k, sign, x2 = 0, scale // x, 1, 1, x * x
        while term:
            total += sign * (term // k)
            term //= x2
            k += 2
            sign = -sign
        return total
    v = 16 * arctan_inv(5) - 4 * arctan_inv(239)
    with decimal.localcontext() as ctx:
        ctx.prec = digits + 5
        return Decimal(v) / Decimal(scale)


def peval(coeffs, x):
    out = 0
    for c in reversed(coeffs):
        out = out * x + c
    return out


def real_root_bisect(coeffs, lo, hi, iterations):
    flo = peval(coeffs, lo)
    for _ in range(iterations):
        mid = (lo + hi) / 2
        fm = peval(coeffs, mid)
        if (fm < 0) == (flo < 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return (lo + hi) / 2


def discriminant(d0, c1, b2, a3):
    """The discriminant of a3 x^3 + b2 x^2 + c1 x + d0."""
    a, b, c, d = a3, b2, c1, d0
    return 18 * a * b * c * d - 4 * b ** 3 * d + b * b * c * c - 4 * a * c ** 3 - 27 * a * a * d * d


def constants(pi):
    """N3, N1 and the bound, from the printed cubic and the printed formula."""
    D = Decimal
    cub = [D(x) for x in CUBIC]
    lo, hi = D(1), D(10 ** 6)
    if not (peval(cub, lo) < 0 < peval(cub, hi)):
        raise AssertionError("the cubic does not change sign on [1, 1e6]")
    N3 = real_root_bisect(cub, lo, hi, 4 * PRECISION)
    absN1_sq = D(2048) / D(108) / N3
    absN1 = absN1_sq.sqrt()
    reN1 = (D(2359989) / D(108) - N3) / 2
    imN1 = (absN1_sq - reN1 * reN1).sqrt()
    sqrt3 = D(3).sqrt()
    phi_limit = pi / (2 * sqrt3) - (3 * sqrt3 / 4).ln()
    c = 4 - D(5) / 2 * D(2).ln() - phi_limit
    E1 = absN1.ln() + c
    E3 = N3.ln() + c
    mu = 1 + E3 / (-E1)
    return {"N3": N3, "absN1": absN1, "reN1": reN1, "imN1": imN1, "phi_limit": phi_limit, "c": c, "E1": E1, "E3": E3,
            "mu": mu}


def digits_of(x, places):
    """x written with `places` decimals, cut (not rounded), as a string."""
    q = Decimal(1).scaleb(-places)
    return str(x.quantize(q, rounding=decimal.ROUND_DOWN))


def as_printed(x, printed):
    """Whether the printed decimal string is x cut or rounded to its number of decimals."""
    places = len(printed.split(".")[1])
    q = Decimal(1).scaleb(-places)
    return printed in (str(x.quantize(q, rounding=decimal.ROUND_DOWN)), str(x.quantize(q, rounding=decimal.ROUND_HALF_EVEN)))


def common_digits(x, printed):
    """How many leading digits (after the point) of the printed string are x's digits, cut."""
    places = len(printed.split(".")[1])
    cut = digits_of(x, places)
    k = 0
    for u, v in zip(cut.split(".")[1], printed.split(".")[1]):
        if u != v:
            break
        k += 1
    return k


def y_zeros():
    """The zeros of the printed numerator of g'/g: the real one by bisection, the complex pair by deflation."""
    D = Decimal
    q = [D(x) for x in GPRIME_NUM]
    y3 = real_root_bisect(q, D(30), D(100), 4 * PRECISION)
    # 2y^3 - 125y^2 - 500y - 625 = (y - y3)(2y^2 + s y + t)
    s = D(-125) + 2 * y3
    t = D(-500) + s * y3
    re_ = -s / 4
    disc = s * s - 8 * t
    im_ = (-disc).sqrt() / 4
    return {"y3": y3, "rey1": re_, "imy1": im_}


# --- the saddle points, exactly --------------------------------------------------------------------------------------

def gprime_numerator():
    """The numerator of g'/g over y (y^2+6y+25)(y-25), from g = y (y^2+6y+25)^2 (y-25)^(-3) by logarithmic
    differentiation: (y^2+6y+25)(y-25) + 2(2y+6) y (y-25) - 3 y (y^2+6y+25)."""
    q = [25, 6, 1]
    t1 = pmul(q, [-25, 1])
    t2 = pmul(pscale([6, 2], 2), pmul([0, 1], [-25, 1]))
    t3 = pscale(pmul([0, 1], q), -3)
    return trim(padd(padd(t1, t2), t3))


def mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def mat_inv(m):
    a = [[Fraction(x) for x in row] + [Fraction(int(i == j)) for j in range(3)] for i, row in enumerate(m)]
    for col in range(3):
        piv = next(r for r in range(col, 3) if a[r][col] != 0)
        a[col], a[piv] = a[piv], a[col]
        pv = a[col][col]
        a[col] = [x / pv for x in a[col]]
        for r in range(3):
            if r != col and a[r][col] != 0:
                f = a[r][col]
                a[r] = [x - f * y for x, y in zip(a[r], a[col])]
    return [row[3:] for row in a]


def mult_matrix(poly, modulus):
    """The matrix of multiplication by poly in Q[y]/(modulus), modulus of degree 3, in the basis 1, y, y^2."""
    monic = [Fraction(x, modulus[3]) for x in modulus]

    def reduce(p):
        p = [Fraction(x) for x in p]
        while len(p) > 3:
            top = p.pop()
            for i in range(3):
                p[len(p) - 3 + i] -= top * monic[i]
        return p + [Fraction(0)] * (3 - len(p))
    cols = [reduce(pmul(poly, [0] * k + [1])) for k in range(3)]
    return [[cols[j][i] for j in range(3)] for i in range(3)]


def charpoly3(m):
    """N^3 - tr N^2 + (sum of principal 2x2 minors) N - det, lowest power first."""
    tr = m[0][0] + m[1][1] + m[2][2]
    minors = (m[0][0] * m[1][1] - m[0][1] * m[1][0] + m[0][0] * m[2][2] - m[0][2] * m[2][0]
              + m[1][1] * m[2][2] - m[1][2] * m[2][1])
    det = (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
           + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
    return [-det, minors, -tr, Fraction(1)]


def saddle_charpoly():
    num = gprime_numerator()
    top = trim(pmul([0, 1], ppow([25, 6, 1], 2)))           # y (y^2 + 6y + 25)^2
    m_top = mult_matrix(top, num)
    m_den = mult_matrix([-25, 1], num)
    inv = mat_inv(m_den)
    m_g = mat_mul(m_top, mat_mul(inv, mat_mul(inv, inv)))
    return num, charpoly3(m_g)


# --- growth and decay -----------------------------------------------------------------------------------------------

def richardson(seq, n, order):
    """sum_{i=0}^{order} (-1)^(order-i) (n+i)^order s_(n+i) / (i! (order-i)!), seq a dict n -> Fraction."""
    total = Fraction(0)
    for i in range(order + 1):
        total += Fraction((-1) ** (order - i) * (n + i) ** order, math.factorial(i) * math.factorial(order - i)) * seq[n + i]
    return total


def to_dec(fr, prec):
    with decimal.localcontext() as ctx:
        ctx.prec = prec
        return Decimal(fr.numerator) / Decimal(fr.denominator)


def magnitude(fr):
    """A rough base-10 order of a nonzero Fraction (from bit lengths: no decimal conversion of huge integers)."""
    return int((abs(fr.numerator).bit_length() - fr.denominator.bit_length()) * 0.30103) + 1


def integral_value(a, b, pi_big, prec):
    """|a + b pi| as a Decimal, with the number of significant digits that survive the cancellation."""
    with decimal.localcontext() as ctx:
        ctx.prec = prec
        big = to_dec(b, prec) * pi_big
        val = to_dec(a, prec) + big
        lost = (abs(big).adjusted() - abs(val).adjusted()) if val != 0 else prec
        return abs(val), prec - lost - 2


# --- quadrature control ---------------------------------------------------------------------------------------------

def gauss_legendre(nodes):
    xs, ws = [], []
    for i in range(1, nodes + 1):
        x = math.cos(math.pi * (i - 0.25) / (nodes + 0.5))
        for _ in range(100):
            p0, p1 = 1.0, x
            for k in range(2, nodes + 1):
                p0, p1 = p1, ((2 * k - 1) * x * p1 - (k - 1) * p0) / k
            dp = nodes * (x * p1 - p0) / (x * x - 1)
            dx = p1 / dp
            x -= dx
            if abs(dx) < 1e-16:
                break
        xs.append(x)
        ws.append(2 / ((1 - x * x) * dp * dp))
    return xs, ws


def quad_forms(n, nodes):
    """I_n by Gauss-Legendre quadrature of both forms of equation (1), in complex double precision: the first along
    x = 4 + it (I_n = -5 times the integral over t of its integrand), the second along x = -1 + it
    (I_n = (-1)^n times the integral of R)."""
    xs, ws = gauss_legendre(nodes)

    def first(x):
        num = ((x - 5) * (x - 4 + 2j) * (x - 4 - 2j) * (x - 6 + 2j) * (x - 6 - 2j)) ** (2 * n)
        return num / (x ** (3 * n + 1) * (x - 10) ** (3 * n + 1))

    def second(x):
        return 5 * x ** (2 * n) * (x ** 4 + 6 * x * x + 25) ** (2 * n) / ((5 + x) ** (3 * n + 1) * (5 - x) ** (3 * n + 1))
    s1 = sum(w * first(4 + 2j * t) for t, w in zip(xs, ws)) * 2       # t in [-2, 2]: x = 4 + i (2 s)
    s2 = sum(w * second(-1 + 2j * t) for t, w in zip(xs, ws)) * 2
    return (-5 * s1).real, ((-1) ** n * s2).real, abs((-5 * s1).imag), abs(((-1) ** n * s2).imag)


# --- controls -------------------------------------------------------------------------------------------------------

def bernoulli(m):
    """B_0 .. B_m (B_1 = -1/2), exactly."""
    B = [Fraction(0)] * (m + 1)
    for k in range(m + 1):
        B[k] = Fraction(1) if k == 0 else -sum(math.comb(k + 1, i) * B[i] for i in range(k)) / (k + 1)
    return B


def digamma(x, shift=80, terms=30):
    """psi(x) for a Decimal x > 0: psi(x + shift) from its asymptotic series, then the recurrence downwards."""
    B = bernoulli(2 * terms)
    z = x + shift
    s = z.ln() - 1 / (2 * z)
    for k in range(1, terms + 1):
        s -= to_dec(B[2 * k], PRECISION + 20) / (2 * k * z ** (2 * k))
    for k in range(shift):
        s -= 1 / (x + k)
    return s


def v1_counterexample(primes, max_n=10):
    """The earlier Lemma 2: every p in P_n with p | j (j from -4n to 3n) divides T(m) for every m in M_j. The first
    (n, p, j, m) against it, searching n upwards, p and j ascending and m in lexicographic order."""
    for n in range(1, max_n + 1):
        for p in P_set(n, primes):
            for j in range(-4 * n, 3 * n + 1):
                if j % p:
                    continue
                s = 3 * n - j
                for rest in itertools.product(range(min(2 * n, s) + 1), repeat=5):
                    m0 = s - sum(rest)
                    if m0 < 0:
                        continue
                    T = math.comb(3 * n + m0, m0)
                    for r in rest:
                        T *= math.comb(2 * n, r)
                    if T % p:
                        return {"n": n, "p": p, "j": j, "m": [m0] + list(rest), "T": T}
    return None


def controls_known(pi, primes, quad):
    pi_ok = str(pi)[:52] == PI50
    disc_ok = discriminant(*CUBIC) < 0
    h4 = miller_power(H, 4, 21) == ppow(H, 4) + [0] * (21 - len(ppow(H, 4)))
    f0 = forms(0, primes)
    zero_ok = f0["a"] == 0 and f0["b"] == Fraction(1, 4)
    pf_ok = True
    for n in (1, 2, 3):
        f = forms(n, primes)
        for x in (Fraction(1, 3), Fraction(7, 2)):
            R = 5 * x ** (2 * n) * (x ** 4 + 6 * x ** 2 + 25) ** (2 * n) / ((5 + x) ** (3 * n + 1) * (5 - x) ** (3 * n + 1))
            P = sum(pk * x ** (2 * k) for k, pk in enumerate(f["p"]))
            parts = sum(A_of(f["Y"], n, j) * (1 / (5 + x) ** (j + 1) + 1 / (5 - x) ** (j + 1)) for j in range(3 * n + 1))
            pf_ok = pf_ok and (R == P + parts)
    quad_ok = all(q["agree"] for q in quad)
    seq = {k: Fraction(4 * (2 * k + 1), 2 * k + 2) for k in range(140, 160)}       # C(2k+2,k+1)/C(2k,k) -> 4
    rich_ok = abs(richardson(seq, RICHARDSON_N, RICHARDSON_ORDER) - 4) < Fraction(1, 10 ** 9)
    psi_diff = digamma(Decimal(2) / 3) - digamma(Decimal(1) / 2)
    sqrt3 = Decimal(3).sqrt()
    closed = pi / (2 * sqrt3) - (3 * sqrt3 / 4).ln()
    psi_ok = abs(psi_diff - closed) < Decimal(10) ** -40
    v1 = v1_counterexample(primes)
    return ({"Machin's pi gives its first 50 printed decimals": pi_ok,
             "the printed cubic has one real zero and a complex pair (discriminant < 0)": disc_ok,
             "Miller's recurrence gives h^4 as repeated multiplication does": h4,
             "I_0 = pi/4: a_0 = 0 and b_0 = 1/4": zero_ok,
             "the partial fractions reproduce R exactly at x = 1/3 and 7/2 for n = 1 to 3": pf_ok,
             "a_n + b_n pi matches quadrature of both forms of (1) for n = 1 to 6": quad_ok,
             "Richardson's formula gives the limit 4 of C(2k+2,k+1)/C(2k,k) to 1e-9": rich_ok,
             "psi(2/3) - psi(1/2) from its series is pi/(2 sqrt 3) - ln(3 sqrt 3/4) to 1e-40": psi_ok,
             "the withdrawn first version of Lemma 2 is found false": v1 is not None},
            {"psi_difference": str(psi_diff), "v1_counterexample": v1})


# --- the run --------------------------------------------------------------------------------------------------------

def conditions(mu, charpoly_ok, lemma2_ok, prop1_ok, ratio_rel, decay_max):
    return {"the bound's expansion begins 7.103205334137": str(mu).startswith(ABSTRACT_DIGITS),
            "the cubic's zeros are g at the zeros of g' (characteristic polynomial)": charpoly_ok,
            "Lemma 2 holds for every n from 1 to 150": lemma2_ok,
            "Proposition 1 holds for every n from 0 to 150": prop1_ok,
            "order-4 Richardson of |b_(n+1)/b_n| at 145 within 1e-5 of N3": ratio_rel < RATIO_TOL,
            "|I_n|^(1/n) <= 1.05 |N1| for n from 90 to 150": decay_max <= DECAY_MARGIN}


def hata(primes_big, n):
    P = [p for p in primes_big if p <= 2 * n and in_P(n, p)]
    return sum(math.log(p) for p in P) / n, len(P)


def short(x, k=12):
    return f"{x:.{k}g}" if isinstance(x, float) else str(x)


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    decimal.getcontext().prec = PRECISION
    raw = read_bytes(os.path.join(inputs, INPUTS["eprint"][0]), INPUTS["eprint"][1])
    check_source(tex_of(raw))
    pi = machin_pi(PRECISION)
    primes = primes_upto(4 * N_MAX + 10)

    # 2. constants
    k = constants(pi)
    ys = y_zeros()
    computed = dict(k)
    computed.update(ys)
    computed["bound_30"] = k["mu"]
    printed_ok = {}
    for name, s in PRINTED.items():
        x = computed[name]
        printed_ok[name] = as_printed(x, s)
    bound30_digits = common_digits(k["mu"], PRINTED["bound_30"])

    # 3. saddle points
    num, cp = saddle_charpoly()
    num_ok = num == list(GPRIME_NUM)
    charpoly_ok = num_ok and cp == [Fraction(x, CUBIC[3]) for x in CUBIC]

    # 4. the integrals
    lemma2_cases = lemma2_held = 0
    lemma2_fail = []
    prop1 = {}
    lemma1_cases = lemma1_held = 0
    slack2 = {}
    a_of, b_of = {}, {}
    for n in range(0, N_MAX + 1):
        f = forms(n, primes)
        a_of[n], b_of[n] = f["a"], f["b"]
        ap, bp, L, e = scaled_forms(n, f["a"], f["b"], primes)
        prop1[n] = ap.denominator == 1 and bp.denominator == 1
        vals = [x for x in (ap, bp) if x != 0]
        slack2[n] = min((v_p(x.numerator, 2) - v_p(x.denominator, 2) for x in vals), default=None)
        for j in range(0, 3 * n + 1):
            Yv = f["Y"][3 * n - j]
            lemma1_cases += 1
            if Yv == 0:
                lemma1_held += 1
                continue
            ok2 = Yv % (1 << (6 * n + (5 * n + 3 * j) // 2)) == 0      # v_2(A_j) >= floor((5n+3j)/2) - 1
            ok5 = Yv % (5 ** (6 * n + 1 + j)) == 0                       # v_5(A_j) >= j
            lemma1_held += int(ok2 and ok5)
        if n >= 1:
            P = P_set(n, primes)
            c_, h_, fl, residues = lemma_2(n, P)
            for (p, j), x in residues.items():          # the modular route against the exact one, for j >= 0
                if x != f["Y"][3 * n - j] * pow(10, 4 * n - 1, p) % p:
                    raise AssertionError(f"n = {n}, p = {p}, j = {j}: the exact and modular coefficients disagree")
            lemma2_cases += c_
            lemma2_held += h_
            lemma2_fail += fl
    lemma2_ok = lemma2_cases > 0 and lemma2_held == lemma2_cases
    prop1_ok = all(prop1.values())

    # 5. growth and decay
    r = {n: abs(b_of[n + 1] / b_of[n]) for n in range(1, N_MAX)}
    rich = richardson(r, RICHARDSON_N, RICHARDSON_ORDER)
    N3f = Fraction(k["N3"])
    ratio_rel = abs(rich / N3f - 1)
    rich_orders = {f"order {o} at {N_MAX - 1 - o}": str(to_dec(abs(richardson(r, N_MAX - 1 - o, o) / N3f - 1), 6))
                   for o in range(0, 7)}

    top_prec = magnitude(b_of[N_MAX]) + 2 * N_MAX + 120
    pi_big = machin_pi(top_prec + 20)
    decay = {}
    with decimal.localcontext() as ctx:
        ctx.prec = top_prec
        absN1 = k["absN1"]
        for n in range(DECAY_FROM, DECAY_TO + 1):
            val, sig = integral_value(a_of[n], b_of[n], pi_big, top_prec)
            if sig < 40:
                raise AssertionError(f"n = {n}: only {sig} significant digits survive")
            root = (val.ln() / n).exp()
            decay[n] = {"root_over_absN1": root / absN1, "sig": sig, "log10": float(val.log10())}
    ratios = {n: Fraction(d["root_over_absN1"]) for n, d in decay.items()}
    decay_max_n = max(ratios, key=lambda n: ratios[n])
    decay_min_n = min(ratios, key=lambda n: ratios[n])
    decay_max = ratios[decay_max_n]

    # 6. beside: the forms at n = 150 and Hata's limit
    with decimal.localcontext() as ctx:
        ctx.prec = top_prec
        n = N_MAX
        ap, bp, L, e = scaled_forms(n, a_of[n], b_of[n], primes)
        I_val, _ = integral_value(a_of[n], b_of[n], pi_big, top_prec)
        Ip = I_val * to_dec(abs(L * Fraction(2) ** e), top_prec)
        logIp = float(Ip.ln()) / n
        logbp = float(to_dec(abs(bp), top_prec).ln()) / n
        both_int = ap.denominator == 1 and bp.denominator == 1
    bound_150 = 1 + logbp / (-logIp)
    primes_big = primes_upto(2 * HATA_N)
    hata_val, hata_count = hata(primes_big, HATA_N)
    b_signs = sorted({1 if b_of[n] > 0 else -1 for n in range(1, N_MAX + 1)})

    # 7. controls
    quad = []
    with decimal.localcontext() as ctx:
        ctx.prec = 120
        pi120 = machin_pi(120)
        for n in range(1, QUAD_N + 1):
            exact = float(to_dec(a_of[n], 120) + to_dec(b_of[n], 120) * pi120)
            q1, q2, im1, im2 = quad_forms(n, QUAD_NODES)
            agree = (abs(q1 - exact) <= QUAD_TOL * abs(exact) and abs(q2 - exact) <= QUAD_TOL * abs(exact))
            quad.append({"n": n, "exact": exact, "first_form": q1, "second_form": q2, "agree": agree})
    controls, control_detail = controls_known(pi, primes, quad)

    mu = k["mu"]
    cond = conditions(mu, charpoly_ok, lemma2_ok, prop1_ok, ratio_rel, decay_max)
    abstract_ok = str(mu).startswith(ABSTRACT_DIGITS)
    n_printed = sum(printed_ok.values())
    tight = sum(1 for n in range(2, N_MAX + 1) if slack2[n] == 0)
    values = {
        "source": "the e-print holds the integrals, P_n, L_n, Lemma 2, Propositions 1 and 2 and every constant as read",
        "bound": f"mu <= 1 + E3/(-E1) = {str(mu)[:34]}; E3 = {str(k['E3'])[:18]}, E1 = {str(k['E1'])[:19]}",
        "bound_printed": (f"the abstract's 7.103205334137: {'as printed' if abstract_ok else 'differs'}; "
                          f"the closing 30-digit value: {bound30_digits} of its 29 decimals as printed"),
        "constants": f"printed constants as printed: {n_printed} of {len(printed_ok)}"
                     + ("" if n_printed == len(printed_ok) else
                        " (not: " + ", ".join(nm for nm, ok in printed_ok.items() if not ok) + ")"),
        "saddle_points": ("g'/g's numerator derived as printed, and the characteristic polynomial of g on Q[y]/(it) "
                          f"is the printed cubic over 108: {'exactly' if charpoly_ok else 'no'}"),
        "lemma_2": f"p | 10^-j A_j in {lemma2_held} of {lemma2_cases} cases (n 1 to 150, p in P_n, p | j)",
        "proposition_1": (f"2^(2-floor(5n/2)) L_n a_n and b_n integers for {sum(prop1.values())} of {len(prop1)} n "
                          "(0 to 150)"),
        "lemma_1": f"2^(1-floor((5n+3j)/2)) 5^-j A_j integral in {lemma1_held} of {lemma1_cases} cases (n <= 150)",
        "ratio": (f"order-4 Richardson of |b_(n+1)/b_n| at 145: {str(to_dec(rich, 20))}; "
                  f"N3 {str(k['N3'])[:20]}"),
        "ratio_relative": float(f"{float(ratio_rel):.3e}"),
        "decay": (f"|I_n|^(1/n)/|N1|, n 90 to 150: max {float(decay_max):.6f} (n = {decay_max_n}), "
                  f"min {float(ratios[decay_min_n]):.6f} (n = {decay_min_n})"),
        "decay_max_ratio": float(f"{float(decay_max):.6f}"),
        "forms_150": (f"n = 150: log|I'_n|/n {logIp:.6f}, log|b'_n|/n {logbp:.6f} (limits -1.902916, 11.613890); "
                      f"their bound {bound_150:.4f}; a', b' integers: {both_int}"),
        "hata": f"log Phi_n/n at n = 1e6: {hata_val:.6f} ({hata_count} primes); the limit {str(k['phi_limit'])[:12]}",
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(controls.values()), "controls_total": len(controls),
    }
    out = {kk: values[kk] for kk in OUTPUTS}
    for kk, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{kk}: longer than {LIMIT} characters: {v}")
    detail = {"inputs": {kk: {"name": nm, "sha256": s} for kk, (nm, s) in INPUTS.items()},
              "conditions": cond, "controls": controls, "control_detail": control_detail,
              "constants": {kk: str(v) for kk, v in computed.items()},
              "printed": PRINTED, "printed_as_printed": printed_ok, "bound_30_common_decimals": bound30_digits,
              "gprime_numerator": num, "charpoly": [str(x) for x in cp],
              "lemma_2": {"cases": lemma2_cases, "held": lemma2_held, "failures": lemma2_fail[:50]},
              "proposition_1_failures": [n for n, ok in prop1.items() if not ok],
              "lemma_1": {"cases": lemma1_cases, "held": lemma1_held},
              "two_adic_room": {str(n): slack2[n] for n in range(N_MAX + 1)},
              "two_adic_tight_n": tight,
              "b_signs": b_signs,
              "richardson_relative_by_order": rich_orders,
              "ratio_raw_149_relative": str(to_dec(abs(r[149] / N3f - 1), 8)),
              "decay": {str(n): {"root_over_absN1": str(d["root_over_absN1"])[:14], "log10_abs_I": d["log10"],
                                 "significant_digits": d["sig"]} for n, d in decay.items()},
              "forms_150": {"log_abs_Iprime_over_n": logIp, "log_abs_bprime_over_n": logbp, "bound": bound_150,
                            "integers": both_int},
              "hata": {"n": HATA_N, "value": hata_val, "primes": hata_count},
              "quadrature": quad,
              "P_150": P_set(150, primes)}
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
        sys.exit(f"zz: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
