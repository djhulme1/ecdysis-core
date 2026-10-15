#!/usr/bin/env python3
"""Guo & Zudilin's q-microscope: Ramanujan's formula for 2√3/π, the q-analogue it is derived from, and the two
supercongruences for its truncations at p - 1 and (p - 1)/2, checked for every prime from 5 to 10,000.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:4b9c849a7af6b605) is from V. J. W. Guo and
W. Zudilin, "A q-microscope for supercongruences", Advances in Mathematics 346 (2019) 329-358 (arXiv:1803.01830), its
abstract: "A typical example includes derivation, from a $q$-analogue of Ramanujan's formula $$ \\sum_{n=0}^\\infty
\\frac{\\binom{4n}{2n}{\\binom{2n}{n}}^2}{2^{8n}3^{2n}}\\,(8n+1) =\\frac{2\\sqrt{3}}π, $$ of the two supercongruences
$$ S(p-1)\\equiv p\\biggl(\\frac{-3}p\\biggr)\\pmod{p^3} \\quad\\text{and}\\quad S\\Bigl(\\frac{p-1}2\\Bigr) \\equiv
p\\biggl(\\frac{-3}p\\biggr)\\pmod{p^3}, $$ valid for all primes $p>3$" (the abstract's sentence goes on: "where $S(N)$
denotes the truncation of the infinite sum at the $N$-th place and $(\\frac{-3}{\\cdot})$ stands for the quadratic
character modulo $3$"; the quote stops before it, to fit the archive's 600 characters).

The test, as registered: see TEST below. Nothing is read from the paper at run time: its statements are the
definitions here. Every rule was fixed before anything below was computed; the paper's TeX (the e-print of 13
February 2019) was read for the formulas, the q-analogue and Theorems 1.1 to 1.3.

1. Ramanujan's formula: the partial sum of a_n (8n + 1) for n from 0 to 1,100, where a_n = C(4n,2n) C(2n,n)^2 /
   (2^(8n) 3^(2n)), each term floored at 1,030 decimal places, against 2√3/π at the same scale (√3 by the integer square
   root, π by Machin's formula, 16 arctan(1/5) - 4 arctan(1/239)); the terms after n = 1,100 total less than
   10^-1040. Condition: they differ by less than 10^-1000.
2. The q-analogue the paper displays (from Guo & Liu 2018 and Guo & Zudilin 2018): the sum over n >= 0 of
   q^(2n^2) (q;q^2)_n^2 (q;q^2)_2n [8n+1] / ((q^2;q^2)_2n (q^6;q^6)_n^2), with [m] = (1 - q^m)/(1 - q), equals
   (q^3;q^2)_inf (q^3;q^6)_inf / ((q^2;q^2)_inf (q^6;q^6)_inf). Both sides are expanded as power series with integer
   coefficients up to q^1000 (multiplying by 1 - q^m and dividing by it, term by term). Condition: all 1,001
   coefficients agree.
3. The supercongruences, for every prime p from 5 to 10,000: S(N) is the sum of a_n (8n + 1) for n from 0 to N,
   computed modulo p^3 (a_n = a_(n-1) (4n)(4n-1)(4n-2)(4n-3) / (2304 n^4), its denominators prime to p for n < p), and
   (-3/p) is 1 when p = 1 (mod 3) and -1 when p = 2 (mod 3). Two conditions: S(p - 1) = p (-3/p) and S((p - 1)/2) =
   p (-3/p) modulo p^3, for every such p.
4. The test's four conditions are rules 1 and 2 and the two of rule 3. test_passed is 1 if all four hold.
5. Beside, none of it counted: the paper's remark that the terms with (p - 1)/2 < n <= p - 1 are not all 0 modulo
   p^3 (the primes where one is not, and where their sum is 0, as the two congruences together require); and its
   q-supercongruences, at roots of unity, in the finite fields of three primes l = 1 (mod n) above 2^61 (each the
   smallest such prime after the one before; l-adic images of the complex roots): Theorem 1.1's two truncations,
   for n coprime to 6 from 5 to 37, are q^(-(n-1)/2) [n] (-3/n) to order 3 at every primitive n-th root and to order 1
   at every root of order d, 1 < d < n, d dividing n (that is, modulo [n] Phi_n(q)^2); and Theorems 1.2 and 1.3's
   four sums, for odd n from 3 to 37, vanish at every root of order d > 1 dividing n (modulo [n]). The expansions are
   power series in e at q = z + e, each factor 1 +- q^m expanded to its sixth term, its simple zero at z (when z^m =
   +-1) taken out as a power of e.

Controls (controls_passed counts those that behave as stated; the run stops if any fails): Machin's π against the
Gauss-Legendre iteration at 1,030 places; the power-series routines on Euler's pentagonal number theorem and Gauss's
triangular-number identity up to q^1000; the recurrence for a_n against the binomials for n up to 60; the modular
S(N) against exact rational sums reduced modulo p^3 for every prime from 5 to 300, both truncations; a planted fault
caught (8n + 3 for 8n + 1 breaks some congruence below 100); and the root-of-unity machinery's valuations on known
cases (order 3 for (1 - q^n)^3/(1 - q), 2 for [n]^2, 0 for 1 - q^(n+1)), with Theorem 1.1's right-hand side negated
caught at order 1.

What it cannot check: the theorems beyond the primes and the n tried, and the paper's proofs.

Writes results/outputs.json and results/detail.json. Run with: python3 pi/gz2019.py
"""

import json
import math
import os
import re
import sys
from fractions import Fraction

PRIMES_TO = 10000
DIGITS = 1000
GUARD = 30
TERMS = 1100
QDEG = 1000
THEOREM_N = tuple(n for n in range(5, 38) if math.gcd(n, 6) == 1)
BABY_N = tuple(range(3, 38, 2))
PREC = 6
LIMIT = 200
TEST = ("Refuted if Ramanujan's formula, the sum over n ≥ 0 of C(4n,2n)C(2n,n)²(8n+1)/(2^(8n)3^(2n)) = 2√3/π, fails "
        "within 10^−1000; or the q-analogue the paper displays, Σ q^(2n²)(q;q²)_n²(q;q²)_2n[8n+1]/((q²;q²)_2n"
        "(q⁶;q⁶)_n²) = (q³;q²)_∞(q³;q⁶)_∞/((q²;q²)_∞(q⁶;q⁶)_∞), fails as power series up to q^1000; or for some prime p "
        "from 5 to 10,000, S(p − 1) or S((p − 1)/2), the sum truncated at that n and computed exactly modulo p³, is not "
        "p(−3/p): p if p ≡ 1 (mod 3), −p if p ≡ 2.")
OUTPUTS = ("ramanujan", "q_series", "primes", "full_fail", "half_fail", "first_fail", "middle", "theorem11", "baby",
           "conditions_met", "conditions_total", "test_passed", "controls_passed", "controls_total")


class Refused(Exception):
    pass


def primes_upto(n):
    sieve = bytearray([1]) * (n + 1)
    sieve[0:2] = b"\x00\x00"
    for i in range(2, math.isqrt(n) + 1):
        if sieve[i]:
            sieve[i * i::i] = bytearray(len(sieve[i * i::i]))
    return [i for i in range(n + 1) if sieve[i]]


def chi3(p):
    """(-3/p) for a prime p > 3."""
    return 1 if p % 3 == 1 else -1


# ---------------------------------------------------------------- rule 1: Ramanujan's formula

def arctan_inv(x, scale):
    """arctan(1/x) * scale, floored term by term."""
    total, power, n, sign = 0, scale // x, 1, 1
    x2 = x * x
    while power:
        total += sign * (power // n)
        power //= x2
        n += 2
        sign = -sign
    return total


def machin_pi(places):
    scale = 10 ** (places + 10)
    return (16 * arctan_inv(5, scale) - 4 * arctan_inv(239, scale)) // 10 ** 10


def gauss_legendre_pi(places):
    scale = 10 ** (places + 10)
    a, b, t, p = scale, math.isqrt(scale * scale // 2), scale // 4, 1
    for _ in range(40):
        an = (a + b) // 2
        b = math.isqrt(a * b)
        t -= p * (a - an) * (a - an) // scale
        a, p = an, 2 * p
        if abs(a - b) <= 1:
            break
    return ((a + b) * (a + b) // (4 * t)) // 10 ** 10


def ramanujan_check(places=DIGITS + GUARD, terms=TERMS):
    scale = 10 ** places
    total, c4, c2, den = 0, 1, 1, 1
    for n in range(terms + 1):
        if n:
            c4 = c4 * (4 * n) * (4 * n - 1) * (4 * n - 2) * (4 * n - 3) // ((2 * n) * (2 * n - 1)) ** 2
            c2 = c2 * (2 * n) * (2 * n - 1) // (n * n)
            den *= 2304
        total += c4 * c2 * c2 * (8 * n + 1) * scale // den
    pi = machin_pi(places)
    value = 2 * math.isqrt(3 * scale * scale) * scale // pi
    diff = abs(total - value)
    agree = places - len(str(diff)) if diff else places
    return {"difference_units": diff, "places": places, "agree_digits": agree, "ok": diff < 10 ** (places - DIGITS)}


# ---------------------------------------------------------------- rule 2: power series

def mul1m(c, m):
    """c times (1 - q^m), truncated at len(c)."""
    for i in range(len(c) - 1, m - 1, -1):
        c[i] -= c[i - m]


def div1m(c, m):
    """c divided by (1 - q^m), truncated at len(c)."""
    for i in range(m, len(c)):
        c[i] += c[i - m]


def q_lhs(N, eight=8):
    total = [0] * (N + 1)
    n = 0
    while 2 * n * n <= N:
        top = N - 2 * n * n
        c = [0] * (top + 1)
        c[0] = 1
        for j in range(n):
            if 2 * j + 1 <= top:
                mul1m(c, 2 * j + 1)
                mul1m(c, 2 * j + 1)
        for j in range(2 * n):
            if 2 * j + 1 <= top:
                mul1m(c, 2 * j + 1)
        if eight * n + 1 <= top:
            mul1m(c, eight * n + 1)
        div1m(c, 1)
        for j in range(1, 2 * n + 1):
            if 2 * j <= top:
                div1m(c, 2 * j)
        for j in range(1, n + 1):
            if 6 * j <= top:
                div1m(c, 6 * j)
                div1m(c, 6 * j)
        for i in range(top + 1):
            total[2 * n * n + i] += c[i]
        n += 1
    return total


def q_rhs(N):
    c = [0] * (N + 1)
    c[0] = 1
    for m in range(3, N + 1, 2):
        mul1m(c, m)
    for m in range(3, N + 1, 6):
        mul1m(c, m)
    for m in range(2, N + 1, 2):
        div1m(c, m)
    for m in range(6, N + 1, 6):
        div1m(c, m)
    return c


# ---------------------------------------------------------------- rule 3: the supercongruences

def s_mod(p):
    """S(p - 1) and S((p - 1)/2) modulo p^3, and the middle terms: whether one is nonzero, and their sum."""
    P3 = p ** 3
    num = [1] * p
    for n in range(1, p):
        num[n] = num[n - 1] * (4 * n) * (4 * n - 1) * (4 * n - 2) * (4 * n - 3) % P3
    den = 1
    for n in range(1, p):
        den = den * 2304 * pow(n, 4, P3) % P3
    inv = pow(den, -1, P3)
    invden = [0] * p
    invden[p - 1] = inv
    for n in range(p - 1, 0, -1):
        invden[n - 1] = invden[n] * 2304 * pow(n, 4, P3) % P3
    half = (p - 1) // 2
    full = halfsum = middle_sum = 0
    middle_nonzero = False
    for n in range(p):
        t = num[n] * invden[n] % P3 * (8 * n + 1) % P3
        full = (full + t) % P3
        if n <= half:
            halfsum = (halfsum + t) % P3
        else:
            middle_sum = (middle_sum + t) % P3
            middle_nonzero |= t != 0
    return full, halfsum, middle_nonzero, middle_sum


def a_exact(n):
    return Fraction(math.comb(4 * n, 2 * n) * math.comb(2 * n, n) ** 2, 2 ** (8 * n) * 3 ** (2 * n))


def s_exact_mod(p, N):
    s = sum(a_exact(n) * (8 * n + 1) for n in range(N + 1))
    P3 = p ** 3
    return s.numerator * pow(s.denominator, -1, P3) % P3


def supercongruences(primes):
    full_fail, half_fail, middle_nz, middle_zero = [], [], 0, 0
    for p in primes:
        full, half, nz, msum = s_mod(p)
        target = p * chi3(p) % p ** 3
        if full != target:
            full_fail.append(p)
        if half != target:
            half_fail.append(p)
        middle_nz += nz
        middle_zero += msum == 0
    return full_fail, half_fail, middle_nz, middle_zero


# ---------------------------------------------------------------- beside: roots of unity in F_l

def is_prime(n):
    if n < 2:
        return False
    for q in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % q == 0:
            return n == q
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def primes_1_mod(n, count, start=2 ** 61):
    out, k = [], start // n + 1
    while len(out) < count:
        ell = k * n + 1
        if is_prime(ell):
            out.append(ell)
        k += 1
    return out


def prime_factors(n):
    out, d = [], 2
    while d * d <= n:
        if n % d == 0:
            out.append(d)
            while n % d == 0:
                n //= d
        d += 1
    if n > 1:
        out.append(n)
    return out


def primitive_root_of_order(n, ell):
    for g in range(2, 10 ** 6):
        z = pow(g, (ell - 1) // n, ell)
        if all(pow(z, n // r, ell) != 1 for r in prime_factors(n)):
            return z
    raise Refused("no root of the order found")


class Ser:
    """e^v times a unit u(e) = u0 + u1 e + ..., known to PREC terms, over F_l."""
    __slots__ = ("v", "u", "ell")

    def __init__(self, v, u, ell):
        self.v, self.u, self.ell = v, u, ell

    def __mul__(self, other):
        ell, P = self.ell, PREC
        a, b = self.u, other.u
        c = [0] * P
        for i in range(P):
            ai = a[i]
            if ai:
                for j in range(P - i):
                    c[i + j] = (c[i + j] + ai * b[j]) % ell
        return Ser(self.v + other.v, c, ell)

    def inv(self):
        ell, P, a = self.ell, PREC, self.u
        b = [0] * P
        b[0] = pow(a[0], -1, ell)
        for i in range(1, P):
            s = 0
            for j in range(1, i + 1):
                s += a[j] * b[i - j]
            b[i] = -s * b[0] % ell
        return Ser(-self.v, b, ell)

    def __truediv__(self, other):
        return self * other.inv()


def binom_mod(m, i, ell):
    """C(m, i) modulo ell for any integer m (negative too) and 0 <= i < PREC."""
    num = 1
    for k in range(i):
        num = num * (m - k) % ell
    return num * pow(math.factorial(i), -1, ell) % ell


def power_ser(z, s, ell):
    """(z + e)^s for an integer s."""
    zs = pow(z, s % (ell - 1), ell)
    zinv = pow(z, -1, ell)
    return Ser(0, [binom_mod(s, i, ell) * zs * pow(zinv, i, ell) % ell for i in range(PREC)], ell)


def factor_ser(z, m, sign, ell):
    """1 + sign q^m at q = z + e (sign is -1 or +1), its simple zero, if any, taken out."""
    zm = pow(z, m, ell)
    zinv = pow(z, -1, ell)
    coeff = [sign * binom_mod(m, i, ell) * zm * pow(zinv, i, ell) % ell for i in range(PREC + 1)]
    coeff[0] = (1 + coeff[0]) % ell
    if coeff[0] == 0:
        return Ser(1, coeff[1:PREC + 1], ell)
    return Ser(0, coeff[:PREC], ell)


def const_ser(c, ell):
    return Ser(0, [c % ell] + [0] * (PREC - 1), ell)


def collect(terms, ell):
    """The sum of the Ser terms as {exponent: coefficient}, with the exponent below which every coefficient is known."""
    known = min(t.v + PREC for t in terms)
    out = {}
    for t in terms:
        for i, c in enumerate(t.u):
            e = t.v + i
            if e < known:
                out[e] = (out.get(e, 0) + c) % ell
    return {e: c for e, c in out.items() if c}, known


def order_of_vanishing(coeffs, known):
    return min(coeffs) if coeffs else known


def thm11_terms(z, n, ell, upto):
    """The terms of Theorem 1.1's sum at q = z + e for k from 0 to upto, built term by term."""
    one = lambda m: factor_ser(z, m, -1, ell)
    t = const_ser(1, ell)
    out = [t]
    for k in range(1, upto + 1):
        r = one(2 * k - 1) * one(2 * k - 1) * one(4 * k - 3) * one(4 * k - 1) * one(8 * k + 1) * power_ser(z, 4 * k - 2, ell)
        r = r / (one(4 * k - 2) * one(4 * k) * one(6 * k) * one(6 * k) * one(8 * k - 7))
        t = t * r
        out.append(t)
    return out


def thm11_rhs(z, n, ell, sign=1):
    bracket = factor_ser(z, n, -1, ell) / factor_ser(z, 1, -1, ell)
    return power_ser(z, -(n - 1) // 2, ell) * bracket * const_ser(sign * (1 if n % 3 == 1 else -1), ell)


def check_thm11(n, ell, sign=1):
    """Theorem 1.1's two congruences at every root of order d > 1 dividing n: the orders of vanishing found, the
    smallest term valuation, and whether both reach the orders the theorem asks (3 at order n, 1 below)."""
    z0 = primitive_root_of_order(n, ell)
    ok, vmin, worst = True, 0, {}
    for d in [d for d in range(2, n + 1) if n % d == 0]:
        need = 3 if d == n else 1
        base = pow(z0, n // d, ell)
        for j in range(1, d):
            if math.gcd(j, d) != 1:
                continue
            z = pow(base, j, ell)
            terms = thm11_terms(z, n, ell, n - 1)
            vmin = min(vmin, min(t.v for t in terms))
            rhs = thm11_rhs(z, n, ell, sign)
            neg = Ser(rhs.v, [(-c) % ell for c in rhs.u], ell)
            for upto in (n - 1, (n - 1) // 2):
                coeffs, known = collect(terms[:upto + 1] + [neg], ell)
                order = order_of_vanishing(coeffs, known)
                key = (d, "full" if upto == n - 1 else "half")
                worst[key] = min(worst.get(key, order), order)
                if order < need:
                    ok = False
    return ok, vmin, worst


def baby_terms(z, ell, upto, which):
    one = lambda m: factor_ser(z, m, -1, ell)
    plus = lambda m: factor_ser(z, m, +1, ell)
    t = const_ser(1, ell)
    out = [t]
    for k in range(1, upto + 1):
        if which == 2:   # Theorem 1.2: (-1)^k (q;q^2)_k (-q;q^2)_k^2 / ((q^4;q^4)_k (-q^4;q^4)_k^2) [6k+1] q^(3k^2)
            r = const_ser(-1, ell) * one(2 * k - 1) * plus(2 * k - 1) * plus(2 * k - 1) * power_ser(z, 6 * k - 3, ell)
        else:            # Theorem 1.3: (q^2;q^4)_k (-q;q^2)_k^2 / ((q^4;q^4)_k (-q^4;q^4)_k^2) [6k+1] q^(k^2)
            r = one(4 * k - 2) * plus(2 * k - 1) * plus(2 * k - 1) * power_ser(z, 2 * k - 1, ell)
        r = r * one(6 * k + 1) / (one(4 * k) * plus(4 * k) * plus(4 * k) * one(6 * k - 5))
        t = t * r
        out.append(t)
    return out


def check_baby(n, ell):
    z0 = primitive_root_of_order(n, ell)
    ok = True
    for d in [d for d in range(2, n + 1) if n % d == 0]:
        base = pow(z0, n // d, ell)
        for j in range(1, d):
            if math.gcd(j, d) != 1:
                continue
            z = pow(base, j, ell)
            for which in (2, 3):
                terms = baby_terms(z, ell, n - 1, which)
                for upto in (n - 1, (n - 1) // 2):
                    coeffs, known = collect(terms[:upto + 1], ell)
                    if order_of_vanishing(coeffs, known) < 1:
                        ok = False
    return ok


# ---------------------------------------------------------------- controls

def controls_run():
    ctl = {}
    a, b = machin_pi(DIGITS + GUARD), gauss_legendre_pi(DIGITS + GUARD)
    ctl["Machin's pi equals the Gauss-Legendre iteration's at 1,030 places"] = abs(a - b) < 10 ** 5
    N = QDEG
    euler = [0] * (N + 1)
    euler[0] = 1
    for m in range(1, N + 1):
        mul1m(euler, m)
    pent = [0] * (N + 1)
    k = 0
    while True:
        done = True
        for kk in ((k,) if k == 0 else (k, -k)):
            e = kk * (3 * kk - 1) // 2
            if e <= N:
                pent[e] += (-1) ** kk
                done = False
        if done and k > 0:
            break
        k += 1
    gauss = [0] * (N + 1)
    n = 0
    while n * (n + 1) // 2 <= N:
        gauss[n * (n + 1) // 2] += 1
        n += 1
    prod = [0] * (N + 1)
    prod[0] = 1
    for m in range(2, N + 1, 2):
        mul1m(prod, m)
    for m in range(1, N + 1, 2):
        div1m(prod, m)
    ctl["the series routines give Euler's pentagonal and Gauss's triangular identities to q^1000"] = (
        euler == pent and prod == gauss)
    ok = True
    t = Fraction(1)
    for n in range(1, 61):
        t = t * (4 * n) * (4 * n - 1) * (4 * n - 2) * (4 * n - 3) / (2304 * n ** 4)
        ok &= t == a_exact(n)
    ctl["the recurrence for a_n equals the binomials for n up to 60"] = ok
    ok = True
    for p in primes_upto(300)[2:]:
        full, half, _, _ = s_mod(p)
        ok &= full == s_exact_mod(p, p - 1) and half == s_exact_mod(p, (p - 1) // 2)
    ctl["the modular S(N) equals exact sums reduced modulo p^3 for primes 5 to 300"] = ok
    caught = False
    for p in primes_upto(100)[2:]:
        full3, half3 = s_mod_variant(p)
        target = p * chi3(p) % p ** 3
        caught |= full3 != target or half3 != target
    ctl["a planted fault caught: 8n + 3 for 8n + 1 breaks a congruence below 100"] = caught
    ell = primes_1_mod(7, 1)[0]
    z = primitive_root_of_order(7, ell)
    one = lambda m: factor_ser(z, m, -1, ell)
    cube = one(7) * one(7) * one(7) / one(1)
    sq = (one(7) / one(1)) * (one(7) / one(1))
    ctl["the root-of-unity valuations: 3, 2 and 0 on known cases at n = 7"] = (
        (cube.v, sq.v, one(8).v) == (3, 2, 0))
    ok11, _, _ = check_thm11(7, ell, sign=-1)
    ctl["Theorem 1.1 with its right-hand side negated is caught at n = 7"] = not ok11
    return ctl


def s_mod_variant(p):
    """S with 8n + 3 in place of 8n + 1: the planted fault."""
    P3 = p ** 3
    full = half = 0
    a = Fraction(1)
    for n in range(p):
        if n:
            a = a * (4 * n) * (4 * n - 1) * (4 * n - 2) * (4 * n - 3) / (2304 * n ** 4)
        t = a.numerator * pow(a.denominator, -1, P3) * (8 * n + 3) % P3
        full = (full + t) % P3
        if n <= (p - 1) // 2:
            half = (half + t) % P3
    return full, half


# ---------------------------------------------------------------- run

def run(seed, results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    ctl = controls_run()
    if not all(ctl.values()):
        raise AssertionError(f"a control failed: {[k for k, v in ctl.items() if not v]}")

    ram = ramanujan_check()
    lhs, rhs = q_lhs(QDEG), q_rhs(QDEG)
    q_equal = sum(1 for x, y in zip(lhs, rhs) if x == y)
    q_first = next((i for i, (x, y) in enumerate(zip(lhs, rhs)) if x != y), None)
    primes = [p for p in primes_upto(PRIMES_TO) if p >= 5]
    full_fail, half_fail, middle_nz, middle_zero = supercongruences(primes)

    t11, vmins, worst_all = {}, {}, {}
    for n in THEOREM_N:
        res = []
        for ell in primes_1_mod(n, 3):
            ok, vmin, worst = check_thm11(n, ell)
            res.append(ok)
            vmins[n] = min(vmins.get(n, 0), vmin)
            worst_all[n] = {f"{d}/{h}": o for (d, h), o in worst.items()}
        t11[n] = all(res)
    baby = {n: all(check_baby(n, ell) for ell in primes_1_mod(n, 3)) for n in BABY_N}

    cond = {
        "Ramanujan's formula within 10^-1000": ram["ok"],
        "the q-analogue as power series up to q^1000": q_first is None,
        "S(p - 1) = p(-3/p) modulo p^3 for every prime from 5 to 10,000": not full_fail,
        "S((p - 1)/2) = p(-3/p) modulo p^3 for every prime from 5 to 10,000": not half_fail,
    }
    firsts = []
    if full_fail:
        firsts.append(f"S(p-1) first fails at p = {full_fail[0]}")
    if half_fail:
        firsts.append(f"S((p-1)/2) first fails at p = {half_fail[0]}")
    values = {
        "ramanujan": (f"sum to n = {TERMS} against 2 sqrt(3)/pi: agree to {ram['agree_digits']} places "
                      f"({'within' if ram['ok'] else 'NOT within'} 10^-{DIGITS})"),
        "q_series": (f"q-analogue to q^{QDEG}: {q_equal} of {QDEG + 1} coefficients equal"
                     + ("" if q_first is None else f", first difference at q^{q_first}")),
        "primes": len(primes),
        "full_fail": len(full_fail),
        "half_fail": len(half_fail),
        "first_fail": "; ".join(firsts) if firsts else "none",
        "middle": (f"a middle term (p-1)/2 < n <= p-1 nonzero mod p^3 for {middle_nz} of {len(primes)} primes; "
                   f"middle sum 0 mod p^3 for {middle_zero}"),
        "theorem11": (f"Theorem 1.1 mod [n]Phi_n^2, n coprime to 6 from 5 to 37, three primes l each: "
                      f"{sum(t11.values())} of {len(t11)} hold"),
        "baby": (f"Theorems 1.2 and 1.3 mod [n], odd n from 3 to 37, three primes l each: "
                 f"{sum(baby.values())} of {len(baby)} hold"),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"test": TEST, "conditions": cond, "controls": ctl,
              "ramanujan": {k: (str(v) if k == "difference_units" else v) for k, v in ram.items()},
              "q_series": {"equal": q_equal, "first_difference": q_first, "lhs_head": lhs[:30], "rhs_head": rhs[:30]},
              "supercongruences": {"primes": len(primes), "full_fail": full_fail[:50], "half_fail": half_fail[:50],
                                   "middle_nonzero": middle_nz, "middle_zero": middle_zero},
              "theorem11": {str(n): {"holds": t11[n], "min_term_valuation": vmins[n], "orders": worst_all[n]}
                            for n in THEOREM_N},
              "baby": {str(n): baby[n] for n in BABY_N}}
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
        sys.exit(f"gz2019: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
