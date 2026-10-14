#!/usr/bin/env python3
"""Zudilin's Ramanujan-type supercongruences: every congruence the e-print prints, for every prime up to 1,000.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:da5cfd4c4951c6e2) is from W. Zudilin,
"Ramanujan-type supercongruences", Journal of Number Theory 129(8) (2009) 1848-1857, arXiv:0805.2788v3: "We present
several supercongruences that may be viewed as p-adic analogues of Ramanujan-type series for 1/pi and 1/pi^2, and
prove three of these examples."

Its registered test: refuted if, for some prime p up to 1,000 above the bound the paper states for it, one of the 23
supercongruences it presents fails as printed, each sum over n from 0 to p - 1 (to (p - 1)/2 in (6)) computed
exactly modulo the printed power of p: (2)-(6), (9), (11) and (12) of its introduction and theorems, and (21)-(35) of
Section 3. Theorem 3 is tested in the form (9) it is stated to be equivalent to, its printed form (13) reported
beside. The congruences are read from the e-print's TeX (v3).

The input is the claim's data of record, arXiv's source of the paper (one gzipped TeX file), checked against its
SHA-256 and size and read as text; nothing in it is run. Python's standard library only: integers, exactly, and
fractions. Every rule below was fixed before any of the sums was computed; the seed is not used, as nothing here is
random. The equation numbers are the e-print's as amsart numbers them (its labels in CONGRUENCES).

1. The source. With its TeX comments removed and its white space collapsed, the e-print must hold each congruence's
   display line as transcribed in CONGRUENCES (its summand, right-hand side and modulus, followed by its label), its
   bound "for $p>b$" within the 200 characters after the label (or inside the line), the three WZ pairs of Section 2
   (PAIRS), the WZ equation (14), and the congruences of Wolstenholme, Morley (18), (19) and the Lemma (LEMMAS);
   otherwise the run is refused. What is computed is what CONGRUENCES transcribes.
2. A congruence's sum. A summand of the hypergeometric kind is prod (a)_(m n) / (n!)^d times z^n times a polynomial in
   n, the Pochhammer symbols (a)_j = a (a + 1) ... (a + j - 1) with a = 1/2, 1/3, ... as printed, and m = 2 for
   (1/2)_(2n). For a prime p above the congruence's bound, the summands for n from 0 to p - 1 (to (p - 1)/2 for (6))
   are computed modulo p^(r + EXTRA), r the printed power, each as p^v times a unit: going from n to n + 1, every
   integer factor a_den (a + j) is divided by p as often as p divides it (v counts it), and every denominator (the
   a_den, (n + 1)^d and z's denominator, all prime to p for p above the bound; otherwise the run is refused) is
   inverted modulo p^(r + EXTRA). The four sums of Section 3 with an inner sum over k ((32)-(35)) take the inner sum
   exactly, as an integer, from math.comb, and reduce it.
3. The right-hand side: c (D/p) p^e as printed, (D/p) the Legendre symbol by Euler's criterion (0 when p divides D),
   (-1)^((p-1)/2) being (-1/p).
4. The test. For each of the 23 congruences TESTED and each prime p with bound < p <= P_MAX = 1,000: the sum less the
   right-hand side must be divisible by p^r. Condition i holds if it is for every such prime; test_passed is 1 if all
   23 hold.
5. Beside the test, none of it counted.
   - Each congruence's strength: the least, over its primes, of the power of p dividing the difference, up to r + EXTRA
     (EXTRA = 2).
   - Theorem 3 as printed, (13): its sum has no (-1)^n, where (9), which the paper calls equivalent, and the proof's
     F(n, 0) have one; its count of primes for which it holds.
   - The proofs: each of the three WZ pairs of Section 2 against (14), F(n, k - 1) - F(n, k) = G(n + 1, k) - G(n, k),
     exactly, at every 1 <= k <= n <= N_WZ = 30; F(n, 0) against the summand of the congruence each proof proves, (6),
     (12) and (9), for n from 0 to N_WZ; and Theorem 1's two printed forms of G against each other.
   - The congruences the proofs use, for primes 5 to 997: Wolstenholme's binom(2p-1, p-1) == 1 (mod p^3), Morley's
     (18), (19) and the Lemma.
   - The series the congruences are analogues of, where the paper prints them and they converge geometrically: the
     three unnumbered after (1) (to 4/pi, 2 sqrt 2/pi and 16/pi), (8) (8/pi) and (10) (32/pi^2), each summed exactly
     (fractions) until a term is below 10^-70 and compared with its value at 60 digits (pi by Machin's formula, sqrt 2
     by the integer square root); (1) converges too slowly (|z| = 1) and is not summed.

Controls (controls_passed counts those that behave as stated): rule 2's modular sums equal the exact sums (fractions,
reduced modulo p^(r + EXTRA)) for p = 5, 7, 11 and 13 wherever the bound allows; (2) with its right-hand side made p,
without the Legendre symbol, fails for some prime p = 3 (mod 4) below 50; Euler's criterion equals a count of
quadratic residues for every D used and every odd prime below 100; (1/2)_n = (2n)!/(4^n n!) and (1/2)_(2n) =
4^n (1/4)_n (3/4)_n for n up to 50; the inner sums for small n equal values worked out by hand (1, 2, 18, 164, 1810,
21252 for (32); 1, -3, 9, -3 for (33); 1, 4, 28, 256 for (34); 1, 32, 3168 for (35)); and the WZ check finds a failing
point in Theorem 1's pair with the 2 of its G made 3.

What it cannot check: the congruences for primes above 1,000 (three are proved for all), and the claim's framing,
that these are p-adic analogues of Ramanujan's series.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 pi/zudilin.py
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

INPUT = ("arXiv-0805.2788v3.gz", "4341ce378ec955596799b4fc9ee8490499dd325593de5ef8468ee1176ae601c8", 8589)
P_MAX = 1000
EXTRA = 2
N_WZ = 30
DIGITS = 60
LIMIT = 200

H = (1, 2)      # 1/2

# label -> number, kind, Pochhammer parameters (num, den, m), d, polynomial (c0, c1, ...), z (num, den), upper,
# right-hand side (c, D or None, e), r, bound, the display line as the TeX flattens it.
CONGRUENCES = {
    "A01b": dict(no=2, kind="hyper", poch=[H, H, H], d=3, poly=(1, 4), z=(-1, 1), upper="p-1", rhs=(1, -1, 1), r=3,
                 bound=2, tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n^3}{n!^3}(4n+1)(-1)^n &\overset?\equiv\biggl(\frac{-1}p\biggr)p\pmod{p^3} \quad\text{for $p>2$},"),
    "A02b": dict(no=3, kind="hyper", poch=[H, H, H], d=3, poly=(1, 6), z=(1, 4), upper="p-1", rhs=(1, -1, 1), r=3,
                 bound=2, tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n^3}{n!^3}(6n+1)\frac1{4^n} &\overset?\equiv\biggl(\frac{-1}p\biggr)p\pmod{p^3} \quad\text{for $p>2$},"),
    "A03b": dict(no=4, kind="hyper", poch=[H, H, H], d=3, poly=(1, 6), z=(-1, 8), upper="p-1", rhs=(1, -2, 1), r=3,
                 bound=2, tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n^3}{n!^3}(6n+1)\frac{(-1)^n}{8^n} &\overset?\equiv\biggl(\frac{-2}p\biggr)p\pmod{p^3} \quad\text{for $p>2$},"),
    "A04b": dict(no=5, kind="hyper", poch=[H, H, H], d=3, poly=(5, 42), z=(1, 64), upper="p-1", rhs=(5, -1, 1), r=3,
                 bound=2, tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n^3}{n!^3}(42n+5)\frac1{64^n} &\overset?\equiv5\biggl(\frac{-1}p\biggr)p\pmod{p^3} \quad\text{for $p>2$},"),
    "A01": dict(no=6, kind="hyper", poch=[H, H, H], d=3, poly=(1, 4), z=(-1, 1), upper="(p-1)/2", rhs=(1, -1, 1), r=3,
                bound=2, tex=r"\sum_{n=0}^{(p-1)/2}\frac{(\frac12)_n^3}{n!^3}(4n+1)(-1)^n \overset?\equiv(-1)^{(p-1)/2}p\pmod{p^3} \quad\text{for $p>2$}."),
    "x01b": dict(no=9, kind="hyper", poch=[H, (1, 4), (3, 4)], d=3, poly=(3, 20), z=(-1, 4), upper="p-1",
                 rhs=(3, -1, 1), r=3, bound=2,
                 tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n(\frac14)_n(\frac34)_n}{n!^3}(20n+3)\frac{(-1)^n}{2^{2n}} \overset?\equiv3\biggl(\frac{-1}p\biggr)p\pmod{p^3} \quad\text{for $p>2$}."),
    "B03b": dict(no=11, kind="hyper", poch=[H, H, H, (1, 4), (3, 4)], d=5, poly=(3, 34, 120), z=(1, 16), upper="p-1",
                 rhs=(3, None, 2), r=5, bound=2,
                 tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n^3(\frac14)_n(\frac34)_n}{n!^5}(120n^2+34n+3)\frac1{2^{4n}} \overset?\equiv 3p^2\pmod{p^5} \quad\text{for $p>2$}."),
    "B03": dict(no=12, kind="hyper", poch=[H, H, H, (1, 2, 2)], d=5, poly=(3, 34, 120), z=(1, 64), upper="p-1",
                rhs=(3, None, 2), r=5, bound=2,
                tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n^3(\frac12)_{2n}}{n!^5}(120n^2+34n+3)\frac1{2^{6n}} \equiv3p^2\pmod{p^5} \quad\text{for $p>2$};"),
    "A05b": dict(no=21, kind="hyper", poch=[H, (1, 6), (5, 6)], d=3, poly=(263, 5418), z=(-1, 80 ** 3), upper="p-1",
                 rhs=(263, -15, 1), r=3, bound=5,
                 tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n(\frac16)_n(\frac56)_n}{n!^3}(5418n+263)\frac{(-1)^n}{80^{3n}} &\overset?\equiv263\biggl(\frac{-15}p\biggr)p\pmod{p^3} \quad\text{for $p>5$},"),
    "A06b": dict(no=22, kind="hyper", poch=[H, (1, 4), (3, 4)], d=3, poly=(1123, 21460), z=(-1, 882 ** 2),
                 upper="p-1", rhs=(1123, -1, 1), r=3, bound=7,
                 tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n(\frac14)_n(\frac34)_n}{n!^3}(21460n+1123)\frac{(-1)^n}{882^{2n}} &\overset?\equiv1123\biggl(\frac{-1}p\biggr)p\pmod{p^3} \quad\text{for $p>7$},"),
    "A07b": dict(no=23, kind="hyper", poch=[H, (1, 4), (3, 4)], d=3, poly=(1103, 26390), z=(1, 99 ** 4),
                 upper="p-1", rhs=(1103, -2, 1), r=3, bound=11,
                 tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n(\frac14)_n(\frac34)_n}{n!^3}(26390n+1103)\frac1{99^{4n}} &\overset?\equiv1103\biggl(\frac{-2}p\biggr)p\pmod{p^3} \quad\text{for $p>11$},"),
    "A08b": dict(no=24, kind="hyper", poch=[H, (1, 3), (2, 3)], d=3, poly=(827, 14151), z=(-1, 500 ** 2),
                 upper="p-1", rhs=(827, -3, 1), r=3, bound=5,
                 tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n(\frac13)_n(\frac23)_n}{n!^3}(14151n+827)\frac{(-1)^n}{500^{2n}} &\overset?\equiv827\biggl(\frac{-3}p\biggr)p\pmod{p^3} \quad\text{for $p>5$},"),
    "B01b": dict(no=25, kind="hyper", poch=[H] * 5, d=5, poly=(1, 8, 20), z=(-1, 4), upper="p-1", rhs=(1, None, 2),
                 r=5, bound=3,
                 tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n^5}{n!^5}(20n^2+8n+1)\frac{(-1)^n}{2^{2n}} &\overset?\equiv p^2\pmod{p^5} \quad\text{for $p>3$},"),
    "B02b": dict(no=26, kind="hyper", poch=[H] * 5, d=5, poly=(13, 180, 820), z=(-1, 1024), upper="p-1",
                 rhs=(13, None, 2), r=5, bound=3,
                 tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n^5}{n!^5}(820n^2+180n+13)\frac{(-1)^n}{2^{10n}} &\overset?\equiv13p^2\pmod{p^5} \quad\text{for $p>3$},"),
    "B04b": dict(no=27, kind="hyper", poch=[H, (1, 4), (3, 4), (1, 6), (5, 6)], d=5, poly=(15, 278, 1640),
                 z=(-1, 1024), upper="p-1", rhs=(15, 3, 2), r=5, bound=3,
                 tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n(\frac14)_n(\frac34)_n(\frac16)_n(\frac56)_n}{n!^5} (1640n^2+278n+15)\frac{(-1)^n}{2^{10n}} &\overset?\equiv15\biggl(\frac3p\biggr)p^2\pmod{p^5}"),
    "B05b": dict(no=28, kind="hyper", poch=[H, (1, 4), (3, 4), (1, 3), (2, 3)], d=5, poly=(5, 63, 252), z=(-1, 48),
                 upper="p-1", rhs=(5, None, 2), r=5, bound=3,
                 tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n(\frac14)_n(\frac34)_n(\frac13)_n(\frac23)_n}{n!^5} (252n^2+63n+5)\frac{(-1)^n}{48^n} &\overset?\equiv 5p^2\pmod{p^5}"),
    "B06b": dict(no=29, kind="hyper", poch=[H, (1, 3), (2, 3), (1, 6), (5, 6)], d=5, poly=(29, 693, 5418),
                 z=(-1, 80 ** 3), upper="p-1", rhs=(29, 5, 2), r=5, bound=5,
                 tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n(\frac13)_n(\frac23)_n(\frac16)_n(\frac56)_n}{n!^5} (5418n^2+693n+29)\frac{(-1)^n}{80^{3n}} &\overset?\equiv29\biggl(\frac5p\biggr)p^2\pmod{p^5}"),
    "B07b": dict(no=30, kind="hyper", poch=[H, (1, 8), (3, 8), (5, 8), (7, 8)], d=5, poly=(15, 304, 1920),
                 z=(1, 7 ** 4), upper="p-1", rhs=(15, 7, 2), r=5, bound=7,
                 tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n(\frac18)_n(\frac38)_n(\frac58)_n(\frac78)_n}{n!^5} (1920n^2+304n+15)\frac1{7^{4n}} &\overset?\equiv15\biggl(\frac7p\biggr)p^2\pmod{p^5}"),
    "B08b": dict(no=31, kind="hyper", poch=[H] * 7, d=7, poly=(1, 14, 76, 168), z=(1, 64), upper="p-1",
                 rhs=(1, -1, 3), r=7, bound=2,
                 tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n^7}{n!^7} (168n^3+76n^2+14n+1)\frac1{2^{6n}} &\overset?\equiv\biggl(\frac{-1}p\biggr)p^3\pmod{p^7}"),
    "C01b": dict(no=32, kind="double", inner="c01", poly=(1, 4), z=(1, 36), upper="p-1", rhs=(1, -15, 1), r=2, bound=3,
                 tex=r"\sum_{n=0}^{p-1}\sum_{k=0}^n{\binom nk}^4\cdot(4n+1)\frac1{6^{2n}} &\overset?\equiv\biggl(\frac{-15}p\biggr)p\pmod{p^2}"),
    "C02b": dict(no=33, kind="double", inner="c02", poly=(1, 4), z=(1, 81), upper="p-1", rhs=(1, -3, 1), r=3, bound=3,
                 tex=r"\sum_{n=0}^{p-1}\sum_{k=0}^{[n/3]}(-1)^{n-k}3^{n-3k} \frac{(3k)!}{k!^3}\binom n{3k}\binom{n+k}k \cdot(4n+1)\frac1{81^n} &\overset?\equiv\biggl(\frac{-3}p\biggr)p\pmod{p^3}"),
    "C03b": dict(no=34, kind="double", inner="c03", poly=(1, 5), z=(1, 64), upper="p-1", rhs=(1, -3, 1), r=3, bound=2,
                 tex=r"\sum_{n=0}^{p-1}\sum_{k=0}^n\binom nk^2\binom{2k}k\binom{2n-2k}{n-k} \cdot(5n+1)\frac1{64^n} &\overset?\equiv\biggl(\frac{-3}p\biggr)p\pmod{p^3}"),
    "C04b": dict(no=35, kind="double", inner="c04", poly=(1, 12, 36), z=(1, 1024), upper="p-1", rhs=(1, None, 2), r=3,
                 bound=2,
                 tex=r"\sum_{n=0}^{p-1}\binom{2n}n^2\sum_{k=0}^n\binom{2k}k^2\binom{2n-2k}{n-k}^2 \cdot(36n^2+12n+1)\frac1{2^{10n}} &\overset?\equiv p^2\pmod{p^3}"),
}
TESTED = tuple(CONGRUENCES)
# Theorem 3 as printed (13), beside the test.
PRINTED_X01 = dict(no=13, kind="hyper", poch=[H, (1, 2, 2)], d=3, poly=(3, 20), z=(1, 16), upper="p-1",
                   rhs=(3, -1, 1), r=3, bound=2,
                   tex=r"\sum_{n=0}^{p-1}\frac{(\frac12)_n(\frac12)_{2n}}{n!^3}(20n+3)\frac1{2^{4n}} \equiv3(-1)^{(p-1)/2}p\pmod{p^3} \quad\text{for $p>2$},")
# The three WZ pairs of Section 2, and the equation they satisfy.
PAIRS = (
    r"F(n,k) =(-1)^{n+k}(4n+1)\frac{(\frac12)_n^2(\frac12)_{n+k}}{(1)_n^2(1)_{n-k}(\frac12)_k^2}, \\ G(n,k) =-\frac{(2n-1)^2}{2(n-k)(4n-3)}F(n-1,k) =(-1)^{n+k}\cdot2\cdot\frac{(\frac12)_n^2(\frac12)_{n+k-1}}{(1)_{n-1}^2(1)_{n-k}(\frac12)_k^2}",
    r"F(n,k) =(120n^2-84nk+34n-10k+3)\frac{(\frac12)_n^3(\frac12)_{2n+k}}{2^{6n}(1)_n^3(1)_{n-k}^2(\frac12)_k^3}, \\ G(n,k) =\frac{(\frac12)_n^3(\frac12)_{2n+k-1}}{2^{6n-8}(1)_{n-1}^3(1)_{n-k}^2(\frac12)_k^3}",
    r"F(n,k) =(20n-2k+3)\frac{(-1)^{n+k}(\frac12)_n(\frac12)_{2n+k}}{2^{4n}(1)_n^2(1)_{n-k}(\frac12)_k^2}, \\ G(n,k) =\frac{(-1)^{n+k}(\frac12)_n(\frac12)_{2n+k-1}}{2^{4n-6}(1)_{n-1}^2(1)_{n-k}(\frac12)_k^2}.",
    r"F(n,k-1)-F(n,k)=G(n+1,k)-G(n,k).",
)
LEMMAS = (
    r"\binom{2p-1}{p-1} \equiv1\pmod{p^3}",
    r"\binom{p-1}{\frac{p-1}2} \equiv(-1)^{(p-1)/2}2^{2(p-1)}\pmod{p^3}",
    r"2^{-6(p-1)}\frac{(3p-2)!}{(\frac{3(p-1)}2)!\,(\frac{p-1}2)!^3} \equiv p\pmod{p^4},",
    r"For a prime $p\ge5$ take $n=(p-1)/2$. Then \begin{equation*} \frac{(6n+1)!}{(3n)!\,n!^3} \equiv p\cdot2^{12n}\pmod{p^4}.",
)
# The series printed in the introduction that converge geometrically: summand as in rule 2, and the value.
SERIES = {
    "4/pi": dict(poch=[H, H, H], d=3, poly=(1, 6), z=(1, 4), value="4/pi",
                               tex=r"\sum_{n=0}^\infty\frac{(\frac12)_n^3}{n!^3}(6n+1)\frac1{4^n} &=\frac4\pi,"),
    "2sqrt2/pi": dict(poch=[H, H, H], d=3, poly=(1, 6), z=(-1, 8), value="2sqrt2/pi",
                                      tex=r"\sum_{n=0}^\infty\frac{(\frac12)_n^3}{n!^3}(6n+1)\frac{(-1)^n}{8^n} &=\frac{2\sqrt2}\pi,"),
    "16/pi": dict(poch=[H, H, H], d=3, poly=(5, 42), z=(1, 64), value="16/pi",
                                tex=r"\sum_{n=0}^\infty\frac{(\frac12)_n^3}{n!^3}(42n+5)\frac1{64^n} &=\frac{16}\pi,"),
    "8/pi (8)": dict(poch=[H, (1, 4), (3, 4)], d=3, poly=(3, 20), z=(-1, 4), value="8/pi",
                         tex=r"\sum_{n=0}^\infty\frac{(\frac12)_n(\frac14)_n(\frac34)_n}{n!^3}(20n+3)\frac{(-1)^n}{2^{2n}} =\frac8\pi;"),
    "32/pi^2 (10)": dict(poch=[H, H, H, (1, 4), (3, 4)], d=5, poly=(3, 34, 120), z=(1, 16), value="32/pi^2",
                             tex=r"\sum_{n=0}^\infty\frac{(\frac12)_n^3(\frac14)_n(\frac34)_n}{n!^5}(120n^2+34n+3)\frac1{2^{4n}} =\frac{32}{\pi^2},"),
}
INNER_KNOWN = {"c01": (1, 2, 18, 164, 1810, 21252), "c02": (1, -3, 9, -3), "c03": (1, 4, 28, 256), "c04": (1, 32, 3168)}
LEGENDRE_D = (-1, -2, -3, 3, 5, 7, -15)
OUTPUTS = ("congruences", "checks", "failures", "first_failure", "proved", "strength", "theorem3_printed", "wz",
           "lemmas", "series", "conditions_met", "conditions_total", "test_passed", "controls_passed",
           "controls_total")


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
    for lab, c in list(CONGRUENCES.items()) + [("x01", PRINTED_X01)]:
        i = flat.find(c["tex"])
        lab_at = flat.find("\\label{" + lab + "}", i) if i >= 0 else -1
        ok = i >= 0 and lab_at >= 0 and not flat[i + len(c["tex"]):lab_at].strip()
        bound = f"\\text{{for $p>{c['bound']}$}}"
        ok = ok and (bound in c["tex"] or bound in flat[lab_at:lab_at + 200])
        found[f"({c['no']}) {lab}"] = ok
    for k, s in enumerate(PAIRS):
        found[f"pair or equation {k + 1}"] = s in flat
    for k, s in enumerate(LEMMAS):
        found[f"lemma {k + 1}"] = s in flat
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


# ---------------------------------------------------------------- rule 2: sums modulo p^R

def upper_of(c, p):
    return p - 1 if c["upper"] == "p-1" else (p - 1) // 2


def hyper_sum(c, p, R):
    mod = p ** R
    zn, zd = c["z"]
    if zd % p == 0 or any(den % p == 0 for _, den, *_ in c["poch"]):
        raise Refused(f"a denominator of ({c['no']}) is divisible by {p}")
    v, u, total = 0, 1, 0
    top = upper_of(c, p)
    for n in range(top + 1):
        if v < R:
            total = (total + p ** v * u * poly_at(c["poly"], n)) % mod
        if n == top:
            break
        num, den = zn, zd * pow(n + 1, c["d"], mod)
        for entry in c["poch"]:
            a, b = entry[0], entry[1]
            m = entry[2] if len(entry) > 2 else 1
            for j in range(m):
                w = a + (m * n + j) * b
                while w % p == 0:
                    w //= p
                    v += 1
                num = num * w % mod
                den = den * b % mod
        u = u * num * pow(den, -1, mod) % mod
    return total


def poch(a, j):
    out = Fraction(1)
    for i in range(j):
        out *= a + i
    return out


def hyper_term_exact(c, n):
    t = Fraction(c["z"][0], c["z"][1]) ** n * poly_at(c["poly"], n) / Fraction(math.factorial(n)) ** c["d"]
    for entry in c["poch"]:
        m = entry[2] if len(entry) > 2 else 1
        t *= poch(Fraction(entry[0], entry[1]), m * n)
    return t


def exact_mod(x, p, R):
    """A fraction with denominator prime to p, modulo p^R."""
    mod = p ** R
    if x.denominator % p == 0:
        raise Refused(f"a denominator divisible by {p}")
    return x.numerator * pow(x.denominator, -1, mod) % mod


def inner_values(name, n_max):
    out = []
    comb = math.comb
    for n in range(n_max):
        if name == "c01":
            s = sum(comb(n, k) ** 4 for k in range(n + 1))
        elif name == "c02":
            s = sum((-1) ** (n - k) * 3 ** (n - 3 * k) * comb(3 * k, k) * comb(2 * k, k) * comb(n, 3 * k)
                    * comb(n + k, k) for k in range(n // 3 + 1))
        elif name == "c03":
            s = sum(comb(n, k) ** 2 * comb(2 * k, k) * comb(2 * n - 2 * k, n - k) for k in range(n + 1))
        elif name == "c04":
            s = comb(2 * n, n) ** 2 * sum(comb(2 * k, k) ** 2 * comb(2 * n - 2 * k, n - k) ** 2 for k in range(n + 1))
        else:
            raise ValueError(name)
        out.append(s)
    return out


def double_sum(c, inner, p, R):
    mod = p ** R
    zn, zd = c["z"]
    if zd % p == 0:
        raise Refused(f"a denominator of ({c['no']}) is divisible by {p}")
    zinv = zn * pow(zd, -1, mod) % mod
    total, zpow = 0, 1
    for n in range(upper_of(c, p) + 1):
        total = (total + inner[n] % mod * poly_at(c["poly"], n) * zpow) % mod
        zpow = zpow * zinv % mod
    return total


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


def check(c, p, inner=None):
    """(holds to the printed power, the power of p dividing the difference up to r + EXTRA)."""
    R = c["r"] + EXTRA
    s = hyper_sum(c, p, R) if c["kind"] == "hyper" else double_sum(c, inner, p, R)
    diff = (s - rhs(c, p, R)) % p ** R
    v = valuation(diff, p, R) if diff else R
    return v >= c["r"], v


# ---------------------------------------------------------------- the proofs

def half_poch(j):
    return poch(Fraction(1, 2), j)


def fact(j):
    if j < 0:
        raise ValueError("negative factorial")
    return Fraction(math.factorial(j))


def f1(n, k):
    return (-1) ** (n + k) * (4 * n + 1) * half_poch(n) ** 2 * half_poch(n + k) / (
        fact(n) ** 2 * fact(n - k) * half_poch(k) ** 2)


def g1(n, k, two=2):
    return (-1) ** (n + k) * two * half_poch(n) ** 2 * half_poch(n + k - 1) / (
        fact(n - 1) ** 2 * fact(n - k) * half_poch(k) ** 2)


def g1_first_form(n, k):
    return -Fraction((2 * n - 1) ** 2, 2 * (n - k) * (4 * n - 3)) * f1(n - 1, k)


def f2(n, k):
    return ((120 * n * n - 84 * n * k + 34 * n - 10 * k + 3) * half_poch(n) ** 3 * half_poch(2 * n + k)
            / (Fraction(2) ** (6 * n) * fact(n) ** 3 * fact(n - k) ** 2 * half_poch(k) ** 3))


def g2(n, k):
    return half_poch(n) ** 3 * half_poch(2 * n + k - 1) / (
        Fraction(2) ** (6 * n - 8) * fact(n - 1) ** 3 * fact(n - k) ** 2 * half_poch(k) ** 3)


def f3(n, k):
    return ((20 * n - 2 * k + 3) * (-1) ** (n + k) * half_poch(n) * half_poch(2 * n + k)
            / (Fraction(2) ** (4 * n) * fact(n) ** 2 * fact(n - k) * half_poch(k) ** 2))


def g3(n, k):
    return (-1) ** (n + k) * half_poch(n) * half_poch(2 * n + k - 1) / (
        Fraction(2) ** (4 * n - 6) * fact(n - 1) ** 2 * fact(n - k) * half_poch(k) ** 2)


def wz_failures(F, G, n_max=N_WZ):
    """Points 1 <= k <= n <= n_max at which F(n, k-1) - F(n, k) != G(n+1, k) - G(n, k)."""
    bad, points = [], 0
    for n in range(1, n_max + 1):
        for k in range(1, n + 1):
            points += 1
            if F(n, k - 1) - F(n, k) != G(n + 1, k) - G(n, k):
                bad.append((n, k))
    return bad, points


# ---------------------------------------------------------------- the series

def arctan_inv(x, scale):
    total = term = scale // x
    x2, k, s = x * x, 1, -1
    while term:
        term //= x2
        total += s * (term // (2 * k + 1))
        s, k = -s, k + 1
    return total


def series_value(name, scale):
    """The value in units of 1/scale (scale = 10^(DIGITS + 10)); pi by Machin's formula."""
    pi = 16 * arctan_inv(5, scale) - 4 * arctan_inv(239, scale)
    sqrt2 = math.isqrt(2 * scale * scale)
    return {"4/pi": 4 * scale * scale // pi, "2sqrt2/pi": 2 * sqrt2 * scale // pi, "16/pi": 16 * scale * scale // pi,
            "8/pi": 8 * scale * scale // pi, "32/pi^2": 32 * scale ** 3 // (pi * pi)}[name]


def series_agree(s):
    scale = 10 ** (DIGITS + 10)
    total, n = Fraction(0), 0
    while True:
        t = hyper_term_exact(s, n)
        total += t
        n += 1
        if abs(t) < Fraction(1, 10 ** 70):
            break
    got = total.numerator * scale // total.denominator
    return abs(got - series_value(s["value"], scale)) < 10 ** 10, n


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
    inner = {name: inner_values(name, P_MAX) for name in ("c01", "c02", "c03", "c04")}

    results_by = {}
    for lab, c in CONGRUENCES.items():
        rows = []
        for p in primes:
            if p <= c["bound"]:
                continue
            ok, v = check(c, p, inner.get(c.get("inner")))
            rows.append((p, ok, v))
        results_by[lab] = rows
    x01_rows = [(p,) + check(PRINTED_X01, p) for p in primes if p > 2]

    cond = {f"({CONGRUENCES[lab]['no']}) holds for every prime above {CONGRUENCES[lab]['bound']} up to {P_MAX}":
            all(ok for _, ok, _ in rows) for lab, rows in results_by.items()}
    checks = sum(len(rows) for rows in results_by.values())
    fails = [(CONGRUENCES[lab]["no"], p) for lab, rows in results_by.items() for p, ok, _ in rows if not ok]
    strength = {CONGRUENCES[lab]["no"]: min(v for _, _, v in rows) for lab, rows in results_by.items()}

    # the proofs
    wz = {}
    for name, F, G in (("Theorem 1", f1, g1), ("Theorem 2", f2, g2), ("Theorem 3", f3, g3)):
        bad, points = wz_failures(F, G)
        wz[name] = {"points": points, "failing": bad[:5], "failures": len(bad)}
    g1_forms = all(g1(n, k) == g1_first_form(n, k) for n in range(1, N_WZ + 1) for k in range(0, n))
    f0 = {"Theorem 1 and (6)": all(f1(n, 0) == hyper_term_exact(CONGRUENCES["A01"], n) for n in range(N_WZ + 1)),
          "Theorem 2 and (12)": all(f2(n, 0) == hyper_term_exact(CONGRUENCES["B03"], n) for n in range(N_WZ + 1)),
          "Theorem 3 and (9)": all(f3(n, 0) == hyper_term_exact(CONGRUENCES["x01b"], n) for n in range(N_WZ + 1)),
          "Theorem 3 and (13)": all(f3(n, 0) == hyper_term_exact(PRINTED_X01, n) for n in range(N_WZ + 1))}

    lemma_fail = {"Wolstenholme": 0, "Morley (18)": 0, "(19)": 0, "Lemma": 0}
    for p in primes:
        if p < 5:
            continue
        n = (p - 1) // 2
        if (math.comb(2 * p - 1, p - 1) - 1) % p ** 3:
            lemma_fail["Wolstenholme"] += 1
        if (math.comb(p - 1, n) - (-1) ** n * 2 ** (2 * (p - 1))) % p ** 3:
            lemma_fail["Morley (18)"] += 1
        ratio = Fraction(math.factorial(6 * n + 1), math.factorial(3 * n) * math.factorial(n) ** 3)
        if exact_mod(ratio / Fraction(2) ** (12 * n) - p, p, 4):
            lemma_fail["(19)"] += 1
        if exact_mod(ratio - p * Fraction(2) ** (12 * n), p, 4):
            lemma_fail["Lemma"] += 1

    series = {name: series_agree(s) for name, s in SERIES.items()}

    # controls
    ctl = {}
    same = True
    for lab, c in CONGRUENCES.items():
        for p in (5, 7, 11, 13):
            if p <= c["bound"]:
                continue
            R = c["r"] + EXTRA
            if c["kind"] == "hyper":
                exact = sum(hyper_term_exact(c, n) for n in range(upper_of(c, p) + 1))
                if hyper_sum(c, p, R) != exact_mod(exact, p, R):
                    same = False
            else:
                vals = inner_values(c["inner"], p)
                exact = sum(Fraction(vals[n] * poly_at(c["poly"], n) * c["z"][0] ** n, c["z"][1] ** n)
                            for n in range(p))
                if double_sum(c, inner[c["inner"]], p, R) != exact_mod(exact, p, R):
                    same = False
    ctl["the modular sums equal exact sums of fractions for p = 5, 7, 11 and 13"] = same
    wrong = dict(CONGRUENCES["A01b"], rhs=(1, None, 1))
    ctl["(2) with its right-hand side made p fails for some prime p = 3 (mod 4) below 50"] = any(
        not check(wrong, p)[0] for p in primes if 2 < p < 50 and p % 4 == 3)
    ctl["Euler's criterion equals a count of quadratic residues"] = all(
        legendre(D, p) == legendre_count(D, p) for D in LEGENDRE_D for p in primes if 2 < p < 100)
    ctl["(1/2)_n = (2n)!/(4^n n!) and (1/2)_(2n) = 4^n (1/4)_n (3/4)_n for n up to 50"] = all(
        half_poch(n) == Fraction(math.factorial(2 * n), 4 ** n * math.factorial(n))
        and half_poch(2 * n) == 4 ** n * poch(Fraction(1, 4), n) * poch(Fraction(3, 4), n) for n in range(51))
    ctl["the inner sums for small n equal values worked out by hand"] = all(
        tuple(inner[name][:len(known)]) == known for name, known in INNER_KNOWN.items())
    bad, _ = wz_failures(f1, lambda n, k: g1(n, k, two=3), 6)
    ctl["the WZ check finds a failing point in Theorem 1's pair with the 2 of its G made 3"] = bool(bad)

    proved = {lab: all(ok for _, ok, _ in results_by[lab]) for lab in ("A01", "B03", "x01b")}
    x01_holds = sum(1 for _, ok, _ in x01_rows if ok)
    values = {
        "congruences": (f"{len(TESTED)} congruences, every prime above its bound up to {P_MAX} ({checks:,} checks): "
                        f"{len(fails)} fail"),
        "checks": checks,
        "failures": len(fails),
        "first_failure": (f"({fails[0][0]}) at p = {fails[0][1]}" if fails else "none"),
        "proved": ("Theorems 1 to 3, as (6), (12) and (9): " + ", ".join(
            f"({CONGRUENCES[lab]['no']}) {'holds' if ok else 'fails'}" for lab, ok in proved.items())),
        "strength": "least power of p dividing the difference, by number: " + " ".join(
            f"{no}:{v}" for no, v in strength.items()),
        "theorem3_printed": (f"(13) as printed, without (-1)^n: holds for {x01_holds} of {len(x01_rows)} primes; "
                             f"the proof's F(n, 0) is (9)'s summand: {f0['Theorem 3 and (9)']}, (13)'s: "
                             f"{f0['Theorem 3 and (13)']}"),
        "wz": ("the three pairs against (14) at 1 <= k <= n <= 30: " + ", ".join(
            f"{name} {w['failures']} of {w['points']} fail" for name, w in wz.items())
            + f"; F(n, 0) as (6) and (12): {f0['Theorem 1 and (6)'] and f0['Theorem 2 and (12)']}"),
        "lemmas": "primes 5 to 997, failures: " + ", ".join(f"{k} {v}" for k, v in lemma_fail.items()),
        "series": "summed to 60 digits: " + "; ".join(f"{name} {'agrees' if ok else 'differs'} ({n} terms)"
                                                    for name, (ok, n) in series.items()),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(bool(v) for v in ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for key, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")
    detail = {"input": {"name": INPUT[0], "sha256": INPUT[1], "bytes": INPUT[2]}, "source": found,
              "results": {f"({CONGRUENCES[lab]['no']}) {lab}": rows for lab, rows in results_by.items()},
              "x01_printed": x01_rows, "strength": strength, "conditions": cond, "wz": wz,
              "g1_two_forms_agree": g1_forms, "f_n0": f0, "lemmas": lemma_fail,
              "series": {k: {"agrees": v[0], "terms": v[1]} for k, v in series.items()}, "controls": ctl}
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
        sys.exit(f"zudilin: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
