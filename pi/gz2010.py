#!/usr/bin/env python3
"""Guillera and Zudilin's "divergent" Ramanujan-type supercongruences: every congruence the e-print presents, for every
prime up to 1,000.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:628411bbc71bd189) is from J. Guillera and
W. Zudilin, '"Divergent" Ramanujan-type supercongruences', Proceedings of the AMS 140 (2012) 765-777, arXiv:1004.4337v4:
'"Divergent" Ramanujan-type series for 1/pi and 1/pi^2 provide us with new nice examples of supercongruences of the
same kind as those related to the convergent cases.'

Its registered test: refuted if, for some prime p up to 1,000 above the bound the paper states for it, one of the 12
supercongruences it presents fails as printed, each sum over n from 0 to p - 1 (to (p - 1)/2 in (10) and (11))
computed exactly modulo the printed power of p: (1)-(9) of its introduction, the conjectural (5)-(9) among them, and
(10)-(12) of its main theorem. The congruences are read from the e-print's TeX (v4).

The input is the claim's data of record, arXiv's source of the paper (one gzipped TeX file), checked against its
SHA-256 and size and read as text; nothing in it is run. Python's standard library only: integers, exactly, and
fractions. Every rule below was fixed before any of the sums was computed; the seed is not used, as nothing here is
random. The equation numbers are the e-print's as amsart numbers them (its labels in CONGRUENCES).

1. The source. With its TeX comments removed and its white space collapsed, the e-print must hold each congruence's
   display line as transcribed in CONGRUENCES (its summand, right-hand side, modulus and bound, followed by its label),
   the four WZ pairs and the WZ equation (23) (PAIRS), the lemmas and identities checked beside (LEMMAS) and the series
   summed beside (SERIES); otherwise the run is refused. What is computed is what CONGRUENCES transcribes.
2. A congruence's sum: prod (a)_n / (1)_n^d times z^n times a polynomial in n, the Pochhammer symbols (a)_n =
   a (a + 1) ... (a + n - 1), with a = 1/2, 1/3, 2/3, 1/4 and 3/4 as printed. For a prime p above the congruence's
   bound, the summands for n from 0 to p - 1 (to (p - 1)/2 for (10) and (11)) are computed modulo p^(r + EXTRA), r the
   printed power, each as p^v times a unit: going from n to n + 1, every factor of the ratio of consecutive terms
   (z's numerator and denominator, each a_num + n a_den and a_den, and n + 1, d times) is divided by p as often as p
   divides it, v counting the powers in the numerator less those in the denominator, and the units of the denominator
   are inverted modulo p^(r + EXTRA). So p may divide a Pochhammer denominator, as 3 does in (7) and (9). A term with
   v < 0 would not be p-integral; none is expected, and one refuses the run.
3. The right-hand side: c (D/p) p^e as printed, (D/p) the Legendre symbol by Euler's criterion (0 when p divides D),
   (-1)^((p-1)/2) being (-1/p).
4. The test. For each of the 12 congruences and each prime p with bound < p <= P_MAX = 1,000: the sum less the
   right-hand side must be divisible by p^r. Condition i holds if it is for every such prime; test_passed is 1 if all
   12 hold.
5. Beside the test, none of it counted.
   - Each congruence's strength: the least, over its primes, of the power of p dividing the difference, up to
     r + EXTRA (EXTRA = 2).
   - The half sums: the paper notes that (1), (2), (3), (4) and (8) may be summed to (p - 1)/2; for every prime above
     each one's bound, the sum to (p - 1)/2 against the sum to p - 1, modulo the printed power.
   - The proofs: each of the four WZ pairs (Lemma 3's at x = -8, 1/3 and 5, and those of the proofs of (10), (11) and
     (12)) against (23), F(n, k - 1) - F(n, k) = G(n + 1, k) - G(n, k), exactly, at every 0 <= n <= N_WZ and
     1 <= k <= N_WZ (N_WZ = 30), with G(0, k) = 0 as the paper takes it; and F(n, 0) against the summand of (10), (11)
     and (12), and Lemma 3's against binom(2n, n) (x/4)^n, for n from 0 to N_WZ.
   - The congruences the proofs use, for every prime up to 1,000 above their bounds: (13), (14), (15), Morley's (18),
     (19) (at x = -8, -3, -1, 1/2, 2, 3/4, -5/4 and 5, wherever x and 1 - x are prime to p and 1 - x is a square
     modulo p, with y the least square root of 1 - x modulo p and again with y + p), (30) and (31), and (31) with
     -4p q_p(2) for its right-hand side (see below); and the identities of Staver (for N up to 40) and of Borwein and
     Bradley (for N up to 20), exactly.
   - The series of Section 4, to 50 digits: Guillera's 8/pi^2, which converges geometrically and is summed exactly
     until a term is below 10^-70; and three that do not converge, or converge too slowly to sum, by Euler's
     transformation, sum c_n z^n = (1/(1 - z)) sum_k (Delta^k c)(0) (z/(1 - z))^k, which converges for them
     (|z/(1 - z)| = 8/9, 4/5 and 8/9) and gives the analytic continuation off the cut [1, infinity) that the paper
     means: the second of (43), "=" 1/pi at z = -8; the divergent companion of the 8/pi^2 series, "=" 4/pi^2 at
     z = -4; and the complex series (44), = sqrt 7/pi at z = (47 + 45 sqrt(-7))/128, whose |z| = 1. Each is summed
     exactly, in Q(sqrt(-7)), to K_EULER = 1,600 terms, and its real part compared with the printed value and its
     sqrt(-7) part with 0, each to 50 of 60 digits (pi by Machin's formula, sqrt 7 by the integer square root). The
     first of (43) and (45) have z = 4 and 256/81, on the cut, and are not summed.
   - The divergent companion's parameters: (46) and (47) with tau_1 = sqrt 5, k_1 = 1, z(tau_1) = 1/4 and (a, b, c) =
     (1/8, 1, 5/2) (the 8/pi^2 series over 8), solved exactly, against the values the paper gives: k_2 = 0,
     tau_2 = sqrt 5/2 and (a, b, c) = (1/4, 3/2, 5/2), four times which is (2)'s polynomial.

Controls (controls_passed counts those that behave as stated): rule 2's modular sums equal the exact sums (fractions,
reduced modulo p^(r + EXTRA)) for p = 3, 5, 7, 11 and 13 wherever the bound allows, p = 3 dividing the Pochhammer
denominators of (7) and (9); (3) with its right-hand side made p, without the Legendre symbol, fails for some prime
p = 3 (mod 4) below 50; Euler's criterion equals a count of quadratic residues for every D used and every odd prime
below 100; (1/2)_n = (2n)!/(4^n n!), (1/3)_n (2/3)_n = (3n)!/(27^n n!) and (1/4)_n (3/4)_n = (4n)!/(64^n (2n)!) for
n up to 50; the WZ check finds a failing point in (10)'s pair with its G's 2^(2n) made 2^(2n+1); and Euler's
transformation sums the divergent binomial series sum (1/2)_n/n! (-8)^n to (1 + 8)^(-1/2) = 1/3, to 50 digits.

After the trial (under a seed of Imago's own, before any seed was issued), one addition beside the test: (31) as
printed, 3 sum_{n=1}^{p-1} (-1)^n 2^n binom(2n, n) == -4 q_p(2) (mod p^2), held for none of the 167 primes, its left
side being divisible by p and its right side not; the form the proof of (12) uses to reach (25) has -4p q_p(2) on the
right, which is now checked beside it. The test's conditions, its data and its rules did not change.

What it cannot check: the congruences for primes above 1,000 (three are proved for all, one more by Sun), and the
claim's framing, that these come from "divergent" Ramanujan-type series.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 pi/gz2010.py
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
    sys.set_int_max_str_digits(0)

INPUT = ("arXiv-1004.4337v4.gz", "b5be9238a9e12c0ba4da4d75d9b59d4e7b036beeb71b55f963a65465197e56e2", 10598)
P_MAX = 1000
EXTRA = 2
N_WZ = 30
DIGITS = 60
AGREE = 10 ** 10          # 50 of DIGITS digits
K_EULER = 1600
LIMIT = 200

H = (1, 2)      # 1/2

# label -> number, Pochhammer parameters (num, den), d, polynomial (c0, c1, ...), z (num, den), upper, right-hand side
# (c, D or None, e), r, bound, the display line as the TeX flattens it.
CONGRUENCES = {
    "J1a": dict(no=1, poch=[H] * 3, d=3, poly=(1, 3), z=(4, 1), upper="p-1", rhs=(1, None, 1), r=3, bound=2,
                tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n^3}{n!^3}(3n+1)2^{2n} &\equiv p\pmod{p^3} \quad\text{for $p>2$},"),
    "J2a": dict(no=2, poch=[H] * 5, d=5, poly=(1, 6, 10), z=(-4, 1), upper="p-1", rhs=(1, None, 2), r=5, bound=3,
                tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n^5}{n!^5}(10n^2+6n+1)(-1)^n2^{2n} &\equiv p^2\pmod{p^5} \quad\text{for $p>3$},"),
    "3F2-zu3": dict(no=3, poch=[H] * 3, d=3, poly=(1, 3), z=(-8, 1), upper="p-1", rhs=(1, -1, 1), r=3, bound=2,
                    tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n^3}{(1)_n^3}(3n+1)(-1)^n2^{3n} &\equiv \biggl(\frac{-1}{p}\biggr)p\pmod{p^3} \quad\text{for $p>2$},"),
    "3F2-zu2": dict(no=4, poch=[H] * 3, d=3, poly=(8, 21), z=(64, 1), upper="p-1", rhs=(8, None, 1), r=3, bound=2,
                    tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n^3}{(1)_n^3}(21n+8)2^{6n} &\equiv 8p\pmod{p^3} \quad\text{for $p>2$},"),
    "3F2-zu4": dict(no=5, poch=[H, (1, 4), (3, 4)], d=3, poly=(1, 5), z=(-16, 9), upper="p-1", rhs=(1, -3, 1), r=3,
                    bound=3,
                    tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n(\frac14)_n(\frac34)_n}{(1)_n^3}(5n+1)(-1)^n\biggl(\frac43\biggr)^{2n} &\overset?\equiv \biggl(\frac{-3}{p}\biggr)p\pmod{p^3} \quad\text{for $p>3$},"),
    "3F2-zun": dict(no=6, poch=[H, (1, 4), (3, 4)], d=3, poly=(8, 35), z=(256, 81), upper="p-1", rhs=(8, None, 1), r=3,
                    bound=3,
                    tex=r"\sum_{n=0}^{p-1} \frac{(\frac12)_n(\frac14)_n(\frac34)_n}{(1)_n^3} (35n+8)\biggl(\frac43\biggr)^{4n} &\overset?\equiv 8p \pmod{p^3} \quad\text{for $p>3$},"),
    "3F2-zu5": dict(no=7, poch=[H, (1, 3), (2, 3)], d=3, poly=(3, 11), z=(27, 16), upper="p-1", rhs=(3, None, 1), r=3,
                    bound=2,
                    tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n(\frac13)_n(\frac23)_n}{(1)_n^3}(11n+3)\biggl(\frac{27}{16}\biggr)^n &\overset?\equiv 3p\pmod{p^3} \quad\text{for $p>2$},"),
    "5F4-zu2": dict(no=8, poch=[H] * 5, d=5, poly=(32, 160, 205), z=(-1024, 1), upper="p-1", rhs=(32, None, 2), r=5,
                    bound=3,
                    tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n^5}{(1)_n^5}(205n^2+160n+32)(-1)^n2^{10n} &\overset?\equiv 32p^2\pmod{p^5} \quad\text{for $p>3$},"),
    "5F4-zu4": dict(no=9, poch=[H, (1, 3), (2, 3), (1, 4), (3, 4)], d=5, poly=(9, 75, 172), z=(-27, 16), upper="p-1",
                    rhs=(9, None, 2), r=5, bound=2,
                    tex=r"\nonumber \sum_{n=0}^{p-1}\frac{(\frac12)_n(\frac13)_n(\frac23)_n(\frac14)_n(\frac34)_n}{(1)_n^5} \qquad\qquad\qquad \\[-7.5pt] \times (172n^2+75n+9)(-1)^n\biggl(\frac{27}{16}\biggr)^n &\overset?\equiv 9p^2\pmod{p^5} \quad\text{for $p>2$}."),
    "J1": dict(no=10, poch=[H] * 3, d=3, poly=(1, 3), z=(4, 1), upper="(p-1)/2", rhs=(1, None, 1), r=3, bound=2,
               tex=r"\sum_{n=0}^{(p-1)/2}\frac{(\frac12)_n^3}{n!^3}(3n+1)2^{2n} &\equiv p\pmod{p^3} \quad\text{for $p>2$},"),
    "J2": dict(no=11, poch=[H] * 5, d=5, poly=(1, 6, 10), z=(-4, 1), upper="(p-1)/2", rhs=(1, None, 2), r=5, bound=3,
               tex=r"\sum_{n=0}^{(p-1)/2}\frac{(\frac12)_n^5}{n!^5}(10n^2+6n+1)(-1)^n2^{2n} &\equiv p^2\pmod{p^5} \quad\text{for $p>3$},"),
    "J4": dict(no=12, poch=[H] * 3, d=3, poly=(1, 3), z=(-8, 1), upper="p-1", rhs=(1, -1, 1), r=3, bound=2,
               tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n^3}{(1)_n^3}(3n+1)(-1)^n2^{3n} &\equiv(-1)^{(p-1)/2}p\pmod{p^3} \quad\text{for $p>2$}."),
}
TESTED = tuple(CONGRUENCES)
PROVED = ("J1", "J2", "J4")
CONJECTURAL = ("3F2-zu4", "3F2-zun", "3F2-zu5", "5F4-zu2", "5F4-zu4")
HALF = ("J1a", "J2a", "3F2-zu3", "3F2-zu2", "5F4-zu2")
# The WZ pairs (Lemma 3's, then those of the proofs of (10), (11) and (12)) and the equation they satisfy.
PAIRS = (
    r"F(n,k)=\frac{(\frac12-k)_n}{(1)_n}\,\frac{x^n}{(1-x)^k} \quad\text{and}\quad G(n,k)=-\frac{(\frac32-k)_{n-1}}{(1)_{n-1}}\,\frac{x^n}{(1-x)^k}.",
    r"F(n,k)=(3n+2k+1)\frac{(\frac12)_n(\frac12+k)_n^2}{(1)_n^3}2^{2n} \quad\text{and}\quad G(n,k)=-\frac{(\frac12)_n(\frac12+k)_{n-1}^2}{(1)_{n-1}^3}2^{2n}.",
    r"F(n,k)=(10n^2+12nk+4k^2+6n+4k+1)\frac{(\frac12)_n(\frac12+k)_n^4}{(1)_n^5}(-1)^n2^{2n} \quad\text{and}\\ G(n,k)=(n+2k-1)\frac{(\frac12)_n(\frac12+k)_{n-1}^4}{(1)_{n-1}^5}(-1)^n2^{2n+1}",
    r"F(n,k)=(3n+2k+1)\frac{(\frac12)_n(\frac12+k)_n^2(\frac12)_k}{(1)_n^2(1+2k)_n(1)_k}(-1)^n2^{3n} \quad\text{and}\\ G(n,k)=\frac{(\frac12)_n(\frac12+k)_{n-1}^2(\frac12)_k}{(1)_{n-1}^2(1+2k)_{n-1}(1)_k}(-1)^n2^{3n-2}.",
    r"F(n,k-1)-F(n,k)=G(n+1,k)-G(n,k). \label{00}",
)
LEMMAS = (
    r"\sum_{n=1}^{(p-1)/2}\frac{\binom{2n}n}n &\equiv0\pmod p \quad\text{for $p>3$}, \label{st1}",
    r"\sum_{n=1}^{(p-1)/2}\frac{(-1)^n\binom{2n}n}{n^2} &\equiv0\pmod p \quad\text{for $p>5$}. \label{st2}",
    r"\sum_{n=0}^{(p-3)/2}\frac{2^{-2n}\binom{2n}n}{2n+1} \equiv-(-1)^{(p-1)/2}q_p(2)\pmod p \quad\text{for $p>2$}. \label{st3}",
    r"\frac{(\frac12)_{(p-1)/2}}{(1)_{(p-1)/2}} =\binom{p-1}{\frac{p-1}2}2^{-(p-1)} \equiv(-1)^{(p-1)/2}2^{p-1}\pmod{p^2}. \label{st3-3}",
    r"\sum_{n=1}^{p-1}\binom{2n}n\biggl(\frac x4\biggr)^n &\equiv\frac{px}{2(1-x)}\bigl(-q(x)+q(y+1)(y+1)-q(y-1)(y-1)\bigr)\pmod{p^2}. \label{M0}",
    r"\sum_{n=1}^{p-1}\frac{(-1)^n2^n\binom{2n}n}n &\equiv-4q_p(2)\pmod p \quad\text{for $p>2$}, \label{st4}",
    r"3\sum_{n=1}^{p-1}(-1)^n2^n\binom{2n}n &\equiv-4q_p(2)\pmod{p^2} \quad\text{for $p>2$}. \label{st5}",
    r"\sum_{n=1}^N \binom{2n}{n} \frac{1}{n} = \frac{N+1}3 \binom{2N+1}{N} \sum_{n=1}^N \frac{1}{n^2 {\binom{N}{n}}^2}.",
    r"\sum_{n=1}^N\binom{2n}n\frac{n^2}{4N^4+n^4}\prod_{k=1}^{n-1}\frac{N^4-k^4}{4N^4+k^4} =\frac2{5N^2},",
    r"(k_1+1)\tau_2=(k_2+1)\tau_1, \quad (k_1+1)(k_2+1)+8=4 \tau_1 \tau_2, \label{ktau}",
    r"c(\tau_2)=\frac{\tau_2}{\tau_1} \cdot \frac{c}{\sqrt{z}}(\tau_1), \quad b(\tau_2)=\frac{\tau_2}{\tau_1} \cdot \frac{c-b}{\sqrt{z}}(\tau_1), \quad a(\tau_2)=\frac{\tau_2}{\tau_1} \cdot \frac{c-2b+4a}{4 \sqrt{z}}(\tau_1). \label{par-abc}",
    r"with $z(\tau_2)=4$, $\tau_2=\sqrt{5}/2$, $k=0$, $c=5/2$, $b=3/2$ and $a=1/4$;",
    r"in which case $k=1$ and $z(\tau_1)=1/4$.",
)
X_LEMMA = (Fraction(-8), Fraction(-3), Fraction(-1), Fraction(1, 2), Fraction(2), Fraction(3, 4), Fraction(-5, 4),
           Fraction(5))
X_WZ = (Fraction(-8), Fraction(1, 3), Fraction(5))
# The series of Section 4: m, the power of (1/2)_n/n! in the summand; the polynomial's coefficients, each u + v sqrt(-7)
# as (u, v); z as (u, v, denominator); the value; the TeX line.
SERIES = {
    "8/pi^2": dict(m=5, poly=((1, 0), (8, 0), (20, 0)), z=(-1, 0, 4), value="8/pi^2", euler=False,
                   tex=r"\sum_{n=0}^{\infty}\frac{(\frac12)_n^5}{(1)_n^5}(20n^2+8n+1)\frac{(-1)^n}{2^{2n}}=\frac{8}{\pi^2}"),
    "(43), second": dict(m=3, poly=((1, 0), (3, 0)), z=(-8, 0, 1), value="1/pi", euler=True,
                         tex=r"\sum_{n=0}^{\infty}\frac{(\frac12)_n^3}{(1)_n^3}(3n+1)(-1)^n2^{3n}\,\text{``$=$''}\,\frac1\pi. \label{3F2-div3}"),
    "companion": dict(m=5, poly=((1, 0), (6, 0), (10, 0)), z=(-4, 0, 1), value="4/pi^2", euler=True,
                      tex=r"\sum_{n=0}^{\infty} \frac{(\frac12)_n^5}{(1)_n^5}(10n^2+6n+1)(-1)^n2^{2n}\,\text{``$=$''}\,\frac{4}{\pi^2}"),
    "(44)": dict(m=3, poly=((Fraction(49, 64), Fraction(-13, 64)), (Fraction(105, 32), Fraction(-21, 32))),
                 z=(47, 45, 128), value="sqrt7/pi", euler=True,
                 tex=r"\sum_{n=0}^{\infty}\frac{(\frac12)_n^3}{(1)_n^3} \biggl(\frac{105-21\sqrt{-7}}{32}n+\frac{49-13\sqrt{-7}}{64}\biggr) \cdot\biggl(\frac{47+45\sqrt{-7}}{128}\biggr)^n =\frac{\sqrt{7}}{\pi}. \label{3F2-divm}"),
}
LEGENDRE_D = (-1, -3)
OUTPUTS = ("congruences", "checks", "failures", "first_failure", "proved", "conjectural", "strength", "half_sums", "wz",
           "lemmas", "identities", "series", "companion", "conditions_met", "conditions_total", "test_passed",
           "controls_passed", "controls_total")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- the source

def read_bytes(path, sha256, size):
    with open(path, "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha256 or len(data) != size:
        raise Refused(f"{path}: sha256 {got} ({len(data)} bytes), not the registered {sha256} ({size})")
    return data


def flat_tex(data):
    try:
        tex = gzip.decompress(data).decode("utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise Refused(f"the e-print is not gzipped UTF-8 TeX: {e}")
    tex = re.sub(r"(?<!\\)%.*", "", tex)
    return " ".join(tex.split())


def source_checks(flat):
    """Rule 1: what the e-print must hold, by name; False where it does not."""
    found = {}
    for lab, c in CONGRUENCES.items():
        i = flat.find(c["tex"])
        lab_at = flat.find("\\label{" + lab + "}", i) if i >= 0 else -1
        found[f"({c['no']}) {lab}"] = i >= 0 and lab_at >= 0 and not flat[i + len(c["tex"]):lab_at].strip()
    for k, s in enumerate(PAIRS):
        found[f"pair or equation {k + 1}"] = s in flat
    for k, s in enumerate(LEMMAS):
        found[f"lemma or identity {k + 1}"] = s in flat
    for name, s in SERIES.items():
        found[f"series {name}"] = s["tex"] in flat
    return found


# ---------------------------------------------------------------- primes and symbols

def primes_upto(n):
    sieve = bytearray([1]) * (n + 1)
    sieve[0:2] = b"\x00\x00"
    for i in range(2, math.isqrt(n) + 1):
        if sieve[i]:
            sieve[i * i::i] = bytearray(len(sieve[i * i::i]))
    return [i for i in range(n + 1) if sieve[i]]


def legendre(D, p):
    a = D % p
    if a == 0:
        return 0
    return 1 if pow(a, (p - 1) // 2, p) == 1 else -1


def legendre_count(D, p):
    a = D % p
    if a == 0:
        return 0
    return 1 if a in {(x * x) % p for x in range(1, p)} else -1


def poly_at(coeffs, n):
    return sum(c * n ** i for i, c in enumerate(coeffs))


def split(x, p):
    """A nonzero integer x as (v, u): x = p^v u, u prime to p."""
    if x == 0:
        raise Refused("a factor of a summand is zero")
    v = 0
    while x % p == 0:
        x //= p
        v += 1
    return v, x


# ---------------------------------------------------------------- rule 2: sums modulo p^R

def upper_of(c, p):
    return p - 1 if c["upper"] == "p-1" else (p - 1) // 2


def hyper_sum(c, p, R):
    mod = p ** R
    zn, zd = c["z"]
    vzn, uzn = split(zn, p)
    vzd, uzd = split(zd, p)
    v, u, total = 0, 1, 0
    top = upper_of(c, p)
    for n in range(top + 1):
        if v < 0:
            raise Refused(f"a term of ({c['no']}) is not {p}-integral at n = {n}")
        if v < R:
            total = (total + p ** v * u * poly_at(c["poly"], n)) % mod
        if n == top:
            break
        vn, un = split(n + 1, p)
        v += vzn - vzd - c["d"] * vn
        num, den = uzn, uzd * pow(un, c["d"], mod)
        for a, b in c["poch"]:
            va, ua = split(a + n * b, p)
            vb, ub = split(b, p)
            v += va - vb
            num = num * ua % mod
            den = den * ub % mod
        u = u * num * pow(den, -1, mod) % mod
    return total


def poch(a, j):
    out = Fraction(1)
    for i in range(j):
        out *= a + i
    return out


def hyper_term_exact(c, n):
    t = Fraction(c["z"][0], c["z"][1]) ** n * poly_at(c["poly"], n) / Fraction(math.factorial(n)) ** c["d"]
    for a, b in c["poch"]:
        t *= poch(Fraction(a, b), n)
    return t


def exact_mod(x, p, R):
    """A fraction with denominator prime to p, modulo p^R."""
    mod = p ** R
    if x.denominator % p == 0:
        raise Refused(f"a denominator divisible by {p}")
    return x.numerator * pow(x.denominator, -1, mod) % mod


def rhs(c, p, R):
    coef, D, e = c["rhs"]
    sym = 1 if D is None else legendre(D, p)
    return coef * sym * p ** e % p ** R


def valuation(x, p, cap):
    v = 0
    while v < cap and x % p == 0:
        x //= p
        v += 1
    return v


def check(c, p):
    """(holds to the printed power, the power of p dividing the difference up to r + EXTRA)."""
    R = c["r"] + EXTRA
    diff = (hyper_sum(c, p, R) - rhs(c, p, R)) % p ** R
    v = valuation(diff, p, R) if diff else R
    return v >= c["r"], v


# ---------------------------------------------------------------- the proofs

def half_poch(j):
    return poch(Fraction(1, 2), j)


def fact(j):
    if j < 0:
        raise ValueError("negative factorial")
    return Fraction(math.factorial(j))


def lemma_pair(x):
    def F(n, k):
        return poch(Fraction(1, 2) - k, n) / fact(n) * x ** n / (1 - x) ** k

    def G(n, k):
        if n == 0:
            return Fraction(0)
        return -poch(Fraction(3, 2) - k, n - 1) / fact(n - 1) * x ** n / (1 - x) ** k
    return F, G


def f10(n, k):
    return (3 * n + 2 * k + 1) * half_poch(n) * poch(Fraction(1, 2) + k, n) ** 2 / fact(n) ** 3 * Fraction(4) ** n


def g10(n, k, base=4):
    if n == 0:
        return Fraction(0)
    return -half_poch(n) * poch(Fraction(1, 2) + k, n - 1) ** 2 / fact(n - 1) ** 3 * Fraction(base) ** n


def f11(n, k):
    return ((10 * n * n + 12 * n * k + 4 * k * k + 6 * n + 4 * k + 1) * half_poch(n) * poch(Fraction(1, 2) + k, n) ** 4
            / fact(n) ** 5 * Fraction(-4) ** n)


def g11(n, k):
    if n == 0:
        return Fraction(0)
    return ((n + 2 * k - 1) * half_poch(n) * poch(Fraction(1, 2) + k, n - 1) ** 4 / fact(n - 1) ** 5 * (-1) ** n
            * Fraction(2) ** (2 * n + 1))


def f12(n, k):
    return ((3 * n + 2 * k + 1) * half_poch(n) * poch(Fraction(1, 2) + k, n) ** 2 * half_poch(k)
            / (fact(n) ** 2 * poch(Fraction(1 + 2 * k), n) * fact(k)) * Fraction(-8) ** n)


def g12(n, k):
    if n == 0:
        return Fraction(0)
    return (half_poch(n) * poch(Fraction(1, 2) + k, n - 1) ** 2 * half_poch(k)
            / (fact(n - 1) ** 2 * poch(Fraction(1 + 2 * k), n - 1) * fact(k)) * (-1) ** n * Fraction(2) ** (3 * n - 2))


def wz_failures(F, G, n_max=N_WZ):
    """Points 0 <= n <= n_max, 1 <= k <= n_max at which F(n, k-1) - F(n, k) != G(n+1, k) - G(n, k)."""
    bad, points = [], 0
    for n in range(0, n_max + 1):
        for k in range(1, n_max + 1):
            points += 1
            if F(n, k - 1) - F(n, k) != G(n + 1, k) - G(n, k):
                bad.append((n, k))
    return bad, points


# ---------------------------------------------------------------- the lemmas

def inv(x, mod):
    return pow(x, -1, mod)


def frac_mod(x, p, R):
    return exact_mod(Fraction(x), p, R)


def fermat_q(x, p):
    """q_p(x) = (x^(p-1) - 1)/p modulo p, x a rational prime to p."""
    x = Fraction(x)
    m = p * p
    t = pow(x.numerator % m, p - 1, m) * pow(inv(x.denominator % m, m), p - 1, m) % m
    return (t - 1) // p % p


def sqrt_mod(a, p):
    a %= p
    for y in range(1, p):
        if y * y % p == a:
            return y
    return None


def lemma_checks(primes):
    """Rule 5: the congruences the proofs use; for each, the number of primes it fails for and the number tried."""
    fail = {k: [0, 0] for k in ("(13)", "(14)", "(15)", "(18)", "(19)", "(19) with y + p", "(30)", "(31)",
                                "(31) with p q")}

    def tally(key, holds):
        fail[key][1] += 1
        fail[key][0] += not holds
    for p in primes:
        if p == 2:
            continue
        m, p2 = (p - 1) // 2, p * p
        c2 = [math.comb(2 * n, n) for n in range(p)]
        if p > 3:
            tally("(13)", sum(c2[n] * inv(n, p) for n in range(1, m + 1)) % p == 0)
        if p > 5:
            tally("(14)", sum((-1) ** n * c2[n] * inv(n * n, p) for n in range(1, m + 1)) % p == 0)
        left = sum(c2[n] * inv(4 ** n * (2 * n + 1), p) for n in range(0, (p - 3) // 2 + 1))
        tally("(15)", (left + (-1) ** m * fermat_q(2, p)) % p == 0)
        lhs18 = half_poch(m) / fact(m)
        tally("(18)", lhs18 == Fraction(math.comb(p - 1, m), 2 ** (p - 1))
              and (frac_mod(lhs18, p, 2) - (-1) ** m * 2 ** (p - 1)) % p2 == 0)
        tally("(30)", (sum((-1) ** n * 2 ** n * c2[n] * inv(n, p) for n in range(1, p)) + 4 * fermat_q(2, p)) % p == 0)
        s31 = 3 * sum((-1) ** n * 2 ** n * c2[n] for n in range(1, p))
        tally("(31)", (s31 + 4 * fermat_q(2, p)) % p2 == 0)
        tally("(31) with p q", (s31 + 4 * p * fermat_q(2, p)) % p2 == 0)
        if p > 3:
            for x in X_LEMMA:
                if x.numerator % p == 0 or x.denominator % p == 0 or (1 - x).numerator % p == 0:
                    continue
                y = sqrt_mod(frac_mod(1 - x, p, 1), p)
                if y is None:
                    continue
                xm = frac_mod(x / 4, p, 2)
                left = sum(c2[n] * pow(xm, n, p2) for n in range(1, p)) % p2
                for key, yy in (("(19)", y), ("(19) with y + p", y + p)):
                    inner = (-fermat_q(x, p) + fermat_q(yy + 1, p) * (yy + 1) - fermat_q(yy - 1, p) * (yy - 1)) % p
                    tally(key, (left - p * frac_mod(x / (2 * (1 - x)), p, 2) * inner) % p2 == 0)
    return fail


def identity_checks():
    staver = all(
        sum(Fraction(math.comb(2 * n, n), n) for n in range(1, N + 1))
        == Fraction(N + 1, 3) * math.comb(2 * N + 1, N) * sum(Fraction(1, n * n * math.comb(N, n) ** 2)
                                                              for n in range(1, N + 1))
        for N in range(1, 41))

    def bb(N):
        total, prod = Fraction(0), Fraction(1)
        for n in range(1, N + 1):
            total += math.comb(2 * n, n) * Fraction(n * n, 4 * N ** 4 + n ** 4) * prod
            prod *= Fraction(N ** 4 - n ** 4, 4 * N ** 4 + n ** 4)
        return total
    borwein_bradley = all(bb(N) == Fraction(2, 5 * N * N) for N in range(1, 21))
    return {"Staver, N up to 40": staver, "Borwein and Bradley, N up to 20": borwein_bradley}


# ---------------------------------------------------------------- the series

def arctan_inv(x, scale):
    total = term = scale // x
    x2, k, s = x * x, 1, -1
    while term:
        term //= x2
        total += s * (term // (2 * k + 1))
        s, k = -s, k + 1
    return total


def constants(scale):
    pi = 16 * arctan_inv(5, scale) - 4 * arctan_inv(239, scale)
    sqrt7 = math.isqrt(7 * scale * scale)
    return {"1/pi": scale * scale // pi, "4/pi^2": 4 * scale ** 3 // (pi * pi), "8/pi^2": 8 * scale ** 3 // (pi * pi),
            "sqrt7/pi": sqrt7 * scale // pi, "1/3": scale // 3, "pi": pi}


class Q7:
    """u + v sqrt(-7), u and v fractions."""

    def __init__(self, u, v=0):
        self.u, self.v = Fraction(u), Fraction(v)

    def __add__(self, o):
        return Q7(self.u + o.u, self.v + o.v)

    def __mul__(self, o):
        return Q7(self.u * o.u - 7 * self.v * o.v, self.u * o.v + self.v * o.u)

    def inverse(self):
        n = self.u * self.u + 7 * self.v * self.v
        return Q7(self.u / n, -self.v / n)


def difference_heads(seq):
    """(Delta^k seq)(0) for k = 0 .. len(seq) - 1, exactly."""
    heads, row = [], list(seq)
    while row:
        heads.append(row[0])
        row = [b - a for a, b in zip(row, row[1:])]
    return heads


def euler_sum(m, poly, z, K=K_EULER, heads_cache=None):
    """sum_n ((1/2)_n/n!)^m poly(n) z^n by Euler's transformation, the first K terms of the transformed series, exactly:
    (1/(1 - z)) sum_k (Delta^k c)(0) w^k, w = z/(1 - z). Returns (real part, sqrt(-7) part) as fractions."""
    zq = Q7(Fraction(z[0], z[2]), Fraction(z[1], z[2]))
    one_minus = Q7(1) + Q7(-zq.u, -zq.v)
    w = zq * one_minus.inverse()
    scale = 4 ** (m * K)
    base = [math.comb(2 * n, n) ** m * 4 ** (m * (K - n)) for n in range(K)]     # ((1/2)_n/n!)^m 4^(mK), integers
    total = Q7(0)
    for j, (cu, cv) in enumerate(poly):
        key = (m, j, K)
        if heads_cache is not None and key in heads_cache:
            heads = heads_cache[key]
        else:
            heads = difference_heads([n ** j * b for n, b in enumerate(base)])
            if heads_cache is not None:
                heads_cache[key] = heads
        # sum_k heads[k] w^k, with w = (wu + wv sqrt(-7)) over a common denominator, in integers
        den = math.lcm(w.u.denominator, w.v.denominator)
        a, b = int(w.u * den), int(w.v * den)
        x, y, sx, sy, dp = 1, 0, 0, 0, den ** (K - 1)
        for k in range(K):
            sx += heads[k] * x * dp
            sy += heads[k] * y * dp
            x, y, dp = a * x - 7 * b * y, a * y + b * x, dp // den
        part = Q7(Fraction(sx, den ** (K - 1) * scale), Fraction(sy, den ** (K - 1) * scale))
        total = total + Q7(cu, cv) * part
    total = total * one_minus.inverse()
    return total.u, total.v


def direct_sum(m, poly, z):
    """A series that converges geometrically, summed exactly until a term is below 10^-70."""
    zz = Fraction(z[0], z[2])
    total, n, a = Fraction(0), 0, Fraction(1)
    while True:
        t = a * poly_at([Fraction(cu) for cu, _ in poly], n) * zz ** n
        total += t
        if n > 5 and abs(t) < Fraction(1, 10 ** 70):
            return total, n + 1
        n += 1
        a *= Fraction(2 * n - 1, 2 * n) ** m


def series_check(name, s, consts, scale, cache):
    if s["euler"]:
        u, v = euler_sum(s["m"], s["poly"], s["z"], heads_cache=cache)
        terms = K_EULER
    else:
        u, terms = direct_sum(s["m"], s["poly"], s["z"])
        v = Fraction(0)
    got_u = u.numerator * scale // u.denominator
    got_v = abs(v.numerator) * scale // v.denominator * math.isqrt(7 * scale * scale) // scale if v else 0
    return {"agrees": abs(got_u - consts[s["value"]]) < AGREE and got_v < AGREE, "terms": terms,
            "real_minus_value": str(Fraction(got_u - consts[s["value"]], scale)),
            "imaginary": str(Fraction(got_v, scale))}


def companion():
    """(46) and (47), solved exactly with tau_2 = t tau_1, tau_1 = sqrt 5, k_1 = 1, sqrt z(tau_1) = 1/2."""
    tau1_sq, k1, sqrt_z = Fraction(5), Fraction(1), Fraction(1, 2)
    a1, b1, c1 = Fraction(1, 8), Fraction(1), Fraction(5, 2)
    # (k1 + 1) t = k2 + 1 and (k1 + 1)(k2 + 1) + 8 = 4 t tau1^2: substitute k2 + 1 = (k1 + 1) t.
    t = Fraction(8) / (4 * tau1_sq - (k1 + 1) ** 2)
    k2 = (k1 + 1) * t - 1
    c2 = t * c1 / sqrt_z
    b2 = t * (c1 - b1) / sqrt_z
    a2 = t * (c1 - 2 * b1 + 4 * a1) / (4 * sqrt_z)
    z2 = 1 / (sqrt_z * sqrt_z)
    return {"k2": k2, "tau2_over_tau1": t, "a": a2, "b": b2, "c": c2, "z": z2,
            "as_printed": (k2, t, a2, b2, c2, z2) == (0, Fraction(1, 2), Fraction(1, 4), Fraction(3, 2),
                                                      Fraction(5, 2), 4),
            "four_times_is_(2)": (4 * a2, 4 * b2, 4 * c2) == (1, 6, 10)}


# ---------------------------------------------------------------- the run

def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    data = read_bytes(os.path.join(inputs, INPUT[0]), INPUT[1], INPUT[2])
    flat = flat_tex(data)
    found = source_checks(flat)
    if not all(found.values()):
        raise Refused("the e-print does not hold " + ", ".join(k for k, v in found.items() if not v))
    primes = primes_upto(P_MAX)

    results_by = {}
    for lab, c in CONGRUENCES.items():
        results_by[lab] = [(p,) + check(c, p) for p in primes if p > c["bound"]]
    cond = {f"({CONGRUENCES[lab]['no']}) holds for every prime above {CONGRUENCES[lab]['bound']} up to {P_MAX}":
            all(ok for _, ok, _ in rows) for lab, rows in results_by.items()}
    checks = sum(len(rows) for rows in results_by.values())
    fails = [(CONGRUENCES[lab]["no"], p) for lab, rows in results_by.items() for p, ok, _ in rows if not ok]
    strength = {CONGRUENCES[lab]["no"]: min(v for _, _, v in rows) for lab, rows in results_by.items()}

    # beside: the half sums
    half = {}
    for lab in HALF:
        c = CONGRUENCES[lab]
        hc = dict(c, upper="(p-1)/2")
        R = c["r"]
        rows = [p for p in primes if p > c["bound"]]
        half[c["no"]] = sum(1 for p in rows if hyper_sum(c, p, R) == hyper_sum(hc, p, R)), len(rows)

    # beside: the proofs
    wz = {}
    for x in X_WZ:
        bad, points = wz_failures(*lemma_pair(x))
        wz[f"Lemma 3, x = {x}"] = {"points": points, "failures": len(bad), "failing": bad[:5]}
    for name, F, G in (("(10)", f10, g10), ("(11)", f11, g11), ("(12)", f12, g12)):
        bad, points = wz_failures(F, G)
        wz[name] = {"points": points, "failures": len(bad), "failing": bad[:5]}
    f0 = {"(10)": all(f10(n, 0) == hyper_term_exact(CONGRUENCES["J1"], n) for n in range(N_WZ + 1)),
          "(11)": all(f11(n, 0) == hyper_term_exact(CONGRUENCES["J2"], n) for n in range(N_WZ + 1)),
          "(12)": all(f12(n, 0) == hyper_term_exact(CONGRUENCES["J4"], n) for n in range(N_WZ + 1)),
          "Lemma 3": all(lemma_pair(x)[0](n, 0) == math.comb(2 * n, n) * (x / 4) ** n
                         for x in X_WZ for n in range(N_WZ + 1))}

    lemmas = lemma_checks(primes)
    identities = identity_checks()

    scale = 10 ** DIGITS
    consts = constants(scale)
    cache = {}
    series = {name: series_check(name, s, consts, scale, cache) for name, s in SERIES.items()}
    comp = companion()

    # controls
    ctl = {}
    same = True
    for lab, c in CONGRUENCES.items():
        for p in (3, 5, 7, 11, 13):
            if p <= c["bound"]:
                continue
            R = c["r"] + EXTRA
            exact = sum(hyper_term_exact(c, n) for n in range(upper_of(c, p) + 1))
            if hyper_sum(c, p, R) != exact_mod(exact, p, R):
                same = False
    ctl["the modular sums equal exact sums of fractions for p = 3, 5, 7, 11 and 13"] = same
    wrong = dict(CONGRUENCES["3F2-zu3"], rhs=(1, None, 1))
    ctl["(3) with its right-hand side made p fails for some prime p = 3 (mod 4) below 50"] = any(
        not check(wrong, p)[0] for p in primes if 2 < p < 50 and p % 4 == 3)
    ctl["Euler's criterion equals a count of quadratic residues"] = all(
        legendre(D, p) == legendre_count(D, p) for D in LEGENDRE_D for p in primes if 2 < p < 100)
    ctl["(1/2)_n, (1/3)_n (2/3)_n and (1/4)_n (3/4)_n as factorials for n up to 50"] = all(
        half_poch(n) == Fraction(math.factorial(2 * n), 4 ** n * math.factorial(n))
        and poch(Fraction(1, 3), n) * poch(Fraction(2, 3), n) == Fraction(math.factorial(3 * n),
                                                                          27 ** n * math.factorial(n))
        and poch(Fraction(1, 4), n) * poch(Fraction(3, 4), n) == Fraction(math.factorial(4 * n),
                                                                          64 ** n * math.factorial(2 * n))
        for n in range(51))
    bad, _ = wz_failures(f10, lambda n, k: g10(n, k, base=8), 6)
    ctl["the WZ check finds a failing point in (10)'s pair with its G's 2^(2n) made 2^(2n+1)"] = bool(bad)
    u, v = euler_sum(1, ((1, 0),), (-8, 0, 1))
    ctl["Euler's transformation sums sum (1/2)_n/n! (-8)^n to 1/3"] = (
        abs(u.numerator * scale // u.denominator - consts["1/3"]) < AGREE and v == 0)

    proved = {CONGRUENCES[lab]["no"]: all(ok for _, ok, _ in results_by[lab]) for lab in PROVED}
    conj = {CONGRUENCES[lab]["no"]: all(ok for _, ok, _ in results_by[lab]) for lab in CONJECTURAL}
    lemma_failures = sum(f for f, _ in lemmas.values())
    values = {
        "congruences": (f"{len(TESTED)} congruences, every prime above its bound up to {P_MAX} ({checks:,} checks): "
                        f"{len(fails)} fail"),
        "checks": checks,
        "failures": len(fails),
        "first_failure": (f"({fails[0][0]}) at p = {fails[0][1]}" if fails else "none"),
        "proved": "the main theorem: " + ", ".join(f"({no}) {'holds' if ok else 'fails'}" for no, ok in proved.items()),
        "conjectural": "the conjectures: " + ", ".join(f"({no}) {'holds' if ok else 'fails'}"
                                                       for no, ok in conj.items()),
        "strength": "least power of p dividing the difference, by number: " + " ".join(
            f"{no}:{v}" for no, v in strength.items()),
        "half_sums": "summed to (p - 1)/2, as the sum to p - 1 modulo the printed power: " + ", ".join(
            f"({no}) {a} of {b}" for no, (a, b) in half.items()),
        "wz": ("the pairs against (23) at 0 <= n <= 30, 1 <= k <= 30, failing points: Lemma 3 at x = -8, 1/3, 5: "
               + ", ".join(str(wz[f"Lemma 3, x = {x}"]["failures"]) for x in X_WZ) + "; "
               + ", ".join(f"{name} {wz[name]['failures']}" for name in ("(10)", "(11)", "(12)"))
               + f"; F(n, 0) as printed: {all(f0.values())}"),
        "lemmas": "failures (primes tried): " + ", ".join(f"{k} {f} ({t})" for k, (f, t) in lemmas.items()),
        "identities": "exactly: " + ", ".join(f"{k} {'holds' if ok else 'fails'}" for k, ok in identities.items()),
        "series": "to 50 digits: " + "; ".join(f"{name} {'agrees' if s['agrees'] else 'differs'}"
                                               for name, s in series.items()),
        "companion": (f"from (46) and (47): k = {comp['k2']}, tau_2/tau_1 = {comp['tau2_over_tau1']}, (a, b, c) = "
                      f"({comp['a']}, {comp['b']}, {comp['c']}), z = {comp['z']}; as printed: {comp['as_printed']}; "
                      f"four times is (2)'s: {comp['four_times_is_(2)']}"),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(bool(v) for v in ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for key, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")
    detail = {"input": {"name": INPUT[0], "sha256": INPUT[1], "bytes": INPUT[2]}, "source": found,
              "results": {f"({CONGRUENCES[lab]['no']}) {lab}": rows for lab, rows in results_by.items()},
              "strength": strength, "conditions": cond, "half_sums": {str(k): v for k, v in half.items()},
              "wz": wz, "f_n0": f0, "lemmas": lemmas, "lemma_failures": lemma_failures, "identities": identities,
              "series": series, "companion": {k: str(v) for k, v in comp.items()}, "controls": ctl}
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
        sys.exit(f"gz2010: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
