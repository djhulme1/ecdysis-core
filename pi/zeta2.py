#!/usr/bin/env python3
"""Zudilin's irrationality measure of zeta(2): the printed constants recomputed, the arithmetic functions read from
their definitions, and the linear forms of both hypergeometric constructions computed exactly to n = 100.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:15bdbae7a8cf3533) is from Zudilin, "Two
hypergeometric tales and a new irrationality measure of zeta(2)", Annales mathematiques du Quebec 38 (2014) 101-117,
arXiv:1310.1526v3: "We prove the new upper bound $5.095412$ for the irrationality exponent of $zeta(2)=pi^2/6$; the
earlier record bound $5.441243$ was established in 1996 by G. Rhin and C. Viola."

The proof (its Sections 3 to 7): linear forms r_n = q_n zeta(2) - p_n, the Barnes integral of (pi/sin pi t)^2 R(t) for
the rational function R(a, b; t) of Section 3 with a = (7n+1, 6n+1, 5n+1, 8n+1), b = (1, n+1, 2n+1, 14n+2) (Section 4);
the same forms from a second construction (Section 6: R^ with a^ = (11n+2; 3n+1, 4n+1, 5n+1), b^ = (2n+2; 1, 10n+2,
11n+2), which Proposition 2 ties to the first); q_n and D_9n D_8n p_n integers (Proposition 1, D_m the lcm of 1..m),
sharpened at the end of Section 6 to Phi~_n^-1 q_n and Phi~_n^-1 D_9n D_8n p_n integers, Phi~_n = prod_{p <= 8n}
p^phi~(n/p); the growth of q_n and r_n (Lemma 6: e^(C1 n) and e^(-C0 n), from the zeros of a cubic); the limit of
log(Phi~_n)/n (Lemma 7's formula, with the digamma function); and Hata's lemma: mu(zeta(2)) <= (C0 + C1)/(C0 - C2~),
C2~ = 9 + 8 - lim log(Phi~_n)/n.

Its registered test is TEST below. The input is the paper's v3 e-print from arXiv (one gzipped TeX file), checked
against its SHA-256 and read as data (decompressed with the standard library and read as text; nothing in it is run).
Every rule below was fixed before any quantity was computed for the paper's parameters, with one exception: a dry run of
the whole program on substitute parameters and functions (to exercise every path), made before the rules were
committed, computed Remark 4's polynomial unsubstituted, through a default argument, and printed the logarithms of its
zeros' moduli, 23.229060716453 and -15.885189980743 (they agree with the printed C1 and -C0 to their printed digits);
nothing else of the paper's case was computed, and no rule was changed after it but that default. The seed is not used,
as nothing here is random.

1. The source. With its TeX comments removed and its whitespace collapsed, z2_2014-05-02.tex must hold every formula and
   printed constant in PRINTED_TEX below (the parameters, Lemma 6's f0, Lemma 7's phi, the printed phi, phi^ and phi~,
   the representations in the proofs of Propositions 1 and 3, C_k and A_k, the inclusions, Remark 4's polynomial and
   the printed constants); otherwise the run is refused. What is computed is what those formulas say.
2. The constants, in decimal arithmetic to PRECISION digits. Lemma 6: with alpha = (7, 6, 5, 8) and beta = (0, 1, 2, 14)
   (a_j = alpha_j n + 1, b_j = beta_j n + 1, b_4 = beta_4 n + 2), the cubic prod (tau - alpha_j) - prod (tau - beta_j)
   in integers; its one real zero tau_1 by bisection (above 14, where the cubic changes sign) and its complex pair tau_0
   from the quadratic left (the discriminant must be negative); C1 = f0(tau_1) and C0 = -Re f0(tau_0), Re log taken as
   the log of the modulus. Lemma 7's limit for a step function with value c on [u, v): sum c (psi(v) - psi(u)) minus
   sum c (the integral of dx/x^2 over [u, v) cut to [0, 1/gamma_2)), gamma_2 = 8, psi the digamma function from its
   asymptotic series at x + 80 and the recurrence down. C2 = 17 - lim(phi) and C2~ = 17 - lim(phi~), each the limit of
   the printed step function; the bound (C0 + C1)/(C0 - C2~). Condition 1: the bound's expansion begins 5.09541178
   (the theorem's digits; the abstract's 5.095412 is their rounding), and C0, C1 and C2~ are 15.88518998, 23.22906071
   and 8.20882301 cut or rounded. Beside: the paper's other printed constants (lim(phi) 8.12793878, C2 8.87206121, the
   first bound 5.57728968, lim(phi^) 7.03418177, lim(phi~) 8.79117698, twice the bound as the corollary's 10.19082357
   for mu(pi sqrt d), the satellite's 16.20882301, and Remark 3's 5.20514736 for its parameters, its phi from Lemma 7's
   definition with gamma_1 = gamma_2 = 7).
3. The arithmetic functions, exactly in rationals. phi(x) as Lemma 7 defines it (the maximum over the 24 permutations
   alpha' of alpha), phi^(x) as Lemma 8 defines it at alpha^ = (11, 3, 4, 5), beta^ = (2, 0, 10, 11) (the minimum over
   0 <= y < 1, read at every y where one of its floors changes and at the midpoint of every gap between such y), and
   phi~ = max(phi, phi^). Each is evaluated at every x = j/m in [0, 1) with m <= M_DEN = 60 (every x where a floor of
   either definition jumps, or two of their lines in (x, y) cross, lies among them: the crossings' denominators are at
   most 44) and at three interior points of every interval between consecutive such x. Condition 2: phi, phi^ and phi~
   equal the paper's printed step functions at all those points. Beside: Remark 2's other formula for phi, and the
   paper's list of where phi < phi^.
4. The linear forms, exactly, for n = 1 to N_MAX = 100. Proposition 1: C_k as printed, for k = a_4 .. b_4 - 1;
   q_n = (-1)^d sum C_k (d = sum a - sum b = 9n - 1); P = R - sum C_k/(t + k) evaluated at t = j + 1 - a_2* for
   j = 0 .. d (R in rationals, the sum over a common denominator); the A_l of P = sum A_l P_l(t + a_2*) are its forward
   differences there (P_l(t + a_2*) is the binomial C(t + a_2* - 1, l)), taken in integers over a common denominator;
   p_n = (-1)^d sum C_k H2(k - a_2*) - sum_l (-1)^(d+l) A_l/(l+1), H2(m) = sum_{l<=m} 1/l^2. Proposition 3: A_k and B_k as the value and the derivative at t = -k of
   R^(t) (t + k)^2, by exact first-order (dual-number) arithmetic, at every pole k; q^_n = (-1)^d^ sum A_k and
   p^_n = (-1)^d^ (sum 2 A_k eta2(2k - a0^*) + sum B_k eta1(2k - a0^*)), d^ = b2^ + b3^, eta_s(m) = sum_{l<=m}
   (-1)^(l-1)/l^s, a0^* = min(a0^, 2 a2^*). Condition 3: for every n, D_9n D_8n p_n is an integer; (q_n, p_n) is
   e (q^_n, p^_n) with e = +1 or -1, the same e for every n; and at every prime p with 9n < p^2 and p <= 8n,
   ord_p q_n >= phi~(n/p) and ord_p(D_9n D_8n p_n) >= phi~(n/p), phi~ the printed one (1-periodic). (The bound needs
   only those primes: Lemma 7's inclusion is stated for p > sqrt(gamma_0 n), gamma_0 = 9, and the primes below do not
   change the limit; the paper's inclusions print every p <= 8n, which is reported beside.)
5. Growth (Lemma 6). The ratios |q_(n+1)/q_n|, exactly; their order-4 Richardson extrapolation at n = 95,
   sum_{i=0}^{4} (-1)^(4-i) (95+i)^4 r_(95+i) / (i! (4-i)!). Condition 4: within 1e-5 of e^C1 in ratio; and
   |r_n| = |q_n zeta(2) - p_n| (zeta(2) = pi^2/6, pi by Machin's formula in integers, to R_DIGITS digits, with at least
   40 significant digits surviving the cancellation) below e^(-(C0 - 1/2) n) for every n from 30 to 100; and Remark 4's
   cubic in lambda has one real zero of modulus e^C1 and a complex pair of modulus e^(-C0), each to 1e-20 in the
   logarithm. test_passed is 1 if all four conditions hold.
6. Beside the test: the sign e (the paper writes q_n = q^_n); the paper's inclusions as printed, at every prime
   p <= 8n; Lemma 8's inclusions for q^_n and p^_n at every prime (ord_p q^ >= phi^(n/p), ord_p p^ >= -2 + phi^(n/p));
   the printed closed form of A_k against the dual-number values; sum B_k = 0; the n from which |r_n| < 1 holds on; and
   log|q_n|/n at n = 100.
7. Controls: Machin's pi against its first 50 printed decimals; the digamma function against Gauss's values
   psi(1) - psi(1/2) = 2 log 2 and psi(2/3) - psi(1/2) = pi/(2 sqrt 3) - log(3 sqrt 3/4); Richardson's formula on a
   sequence with a known limit; both partial-fraction decompositions reproducing R and R^ exactly at t = 1/3 for
   n = 1 to 3; q_1 zeta(2) - p_1 against the Barnes integral of Section 3 by composite Gauss-Legendre quadrature in
   complex double precision, and r^_1 against its own integral (Section 6), each to a relative QUAD_TOL = 1e-7 (for
   n = 2 the forms are near 1e-15, below what double precision can resolve against the integrands); Whipple's transformation (Remark 5: q of (a; 1, a4-a1+1, a4-a2+1, b4) and q^ of (b4-a3+a4; a2, a1, a4 /
   a4+1; a4-a3+1, a1+a2, b4)) for a = (4n+1, 3n+1, 3n+1, 5n+1), b4 = 9n+2, n = 1 to 6, as a test of both q formulas,
   equal up to one sign (the tests found q = -q^ on four other such families, under the signs (-1)^d and (-1)^d^ the
   remark gives them, where the remark prints q = q^);
   and, as a negative control, phi~ raised to 3 on [1/6, 2/9) found too strong for the inclusion at some n <= 100.

What it cannot check: the propositions for every n (only n <= 100), Lemma 6's asymptotics (only their agreement with
the forms up to n = 100 and with Remark 4's polynomial), the prime number theorem behind Lemma 7's limit, and Hata's
lemma; only what is printed and what the forms are up to n = 100.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 pi/zeta2.py
"""

import cmath
import decimal
import gzip
import hashlib
import json
import math
import os
import re
import sys
from decimal import Decimal
from fractions import Fraction
from itertools import permutations

TEST = ("Refuted if, from the paper's (7n+1, 6n+1, 5n+1, 8n+1; 1, n+1, 2n+1, 14n+2), Lemma 6 and printed phi~, "
        "(C0+C1)/(C0-C2~) differs from 5.09541178 in a digit, or C0, C1, C2~ from 15.88518998, 23.22906071, "
        "8.20882301; or phi, phi^ differ from their printed forms; or for some n <= 100 D_9n D_8n p_n is not an "
        "integer, (q_n, p_n) is not +-(q^_n, p^_n), or ord_p(q_n) or ord_p(D_9n D_8n p_n) < phi~(n/p) at a prime "
        "sqrt(9n) < p <= 8n; or |q_(n+1)/q_n|, Richardson order 4 at n = 95, is 1e-5 from e^C1 in ratio, "
        "|r_n| > e^(-(C0-1/2)n) at a 30 <= n <= 100, or Remark 4's zeros' moduli are not e^C1, e^-C0.")

INPUTS = {"eprint": ("arXiv-1310.1526v3.gz", "6b2981bbb6235a567563089c9be0d4ecbc57e3e63ec0a161213a4641aad39cce")}
PRINTED_TEX = (
    r"bounded from above by $5.09541178\dots$",
    r"a_1&=7n+1, &\quad a_2&=6n+1, &\quad a_3&=5n+1, &\quad a_4&=\phantom08n+1, \\ b_1&=1, &\quad b_2&=\phantom1n+1, "
    r"&\quad b_3&=2n+1, &\quad b_4&=14n+2,",
    r"a_1&=\alpha_1n+1, &\quad a_2&=\alpha_2n+1, &\quad a_3&=\alpha_3n+1, &\quad a_4&=\alpha_4n+1, \\ "
    r"b_1&=\beta_1n+1, &\quad b_2&=\beta_2n+1, &\quad b_3&=\beta_3n+1, &\quad b_4&=\beta_4n+2,",
    r"\prod_{j=1}^4(\tau-\alpha_j)-\prod_{j=1}^4(\tau-\beta_j)",
    r"f_0(\tau) &=\sum_{j=1}^4\bigl(\alpha_j\log(\tau-\alpha_j)-\beta_j\log(\tau-\beta_j)\bigr) \\[-4.5pt] &\qquad "
    r"-\sum_{j=1}^3(\alpha_j-\beta_j)\log(\alpha_j-\beta_j)+(\beta_4-\alpha_4)\log(\beta_4-\alpha_4).",
    r"C_0&=15.88518998\dots, \\ \lim_{n\to\infty}\frac{\log|q_n|}n=C_1&=23.22906071\dotsc.",
    r"\varphi(x)=\max_{\boldsymbol\alpha'=\sigma\boldsymbol\alpha:\sigma\in\mathfrak S_4} &\biggl(\lf(\beta_4-\alpha_4)x"
    r"\rf-\lf(\beta_4-\alpha_4')x\rf \\[-2pt] &\qquad -\sum_{j=1}^3\bigl(\lf(\alpha_j-\beta_j)x\rf-\lf(\alpha_j'-\beta_j)x"
    r"\rf\bigr)\biggr),",
    r"=\int_0^1\varphi(x)\,\d\psi(x)-\int_0^{1/\gamma_2}\varphi(x)\,\frac{\d x}{x^2},",
    r"\varphi(x)=\begin{cases} 2 &\text{if $x\in\bigl[\frac16,\frac15\bigr)\cup\bigl[\frac14,\frac27\bigr)\cup\bigl["
    r"\frac12,\frac47\bigr)\cup\bigl[\frac56,\frac67\bigr)$}, \\ 1 &\text{if $x\in\bigl[\frac18,\frac17\bigr)\cup\bigl["
    r"\frac15,\frac14\bigr)\cup\bigl[\frac27,\frac37\bigr)\cup\bigl[\frac47,\frac56\bigr)\cup\bigl[\frac67,\frac89"
    r"\bigr)$}, \\ 0 &\text{otherwise}, \end{cases}",
    r"\lim_{n\to\infty}\frac{\log\Phi_n}n=8.12793878\dotsc.",
    r"=9+8-8.12793878\hdots=8.87206121\dots",
    r"\mu(\zeta(2))\le\frac{C_0+C_1}{C_0-C_2}=5.57728968\dotsc.",
    r"a_1&=4n+1, &\quad a_2&=5n+1, &\quad a_3&=6n+1, &\quad a_4&=\phantom07n+1, \\ b_1&=1, &\quad b_2&=\phantom1n+1, "
    r"&\quad b_3&=2n+1, &\quad b_4&=12n+2,",
    r"$\mu(\zeta(2))\le5.20514736\dots$",
    r"&=(-1)^{d+b_4+k}\binom{k-b_1}{k-a_1}\binom{k-b_2}{k-a_2}\binom{k-b_3}{k-a_3}\binom{b_4-a_4-1}{k-a_4}\in\mathbb Z",
    r"&=\zeta(2)\cdot(-1)^d\sum_{k=a_4^*}^{b_4-1}C_k -(-1)^d\sum_{k=a_4^*}^{b_4-1}C_k\sum_{\ell=1}^{k-a_2^*}"
    r"\frac1{\ell^2} +\sum_{\ell=0}^d\frac{(-1)^{d+\ell}A_\ell}{\ell+1}.",
    r"R(t)=\sum_{k=a_4^*}^{b_4-1}\frac{C_k}{t+k}+\sum_{\ell=0}^dA_\ell P_\ell(t+a_2^*),",
    r"P_\ell(t)=\frac{(t-1)(t-2)\dotsb(t-\ell)}{\ell!}",
    r"2^2\,3^{12}\,7^{14}\,\lambda^3+3^3\,7^7\,794493690983053821271\,\lambda^2 -2^{20}\,3^4\,7^5\,2687491277\,\lambda"
    r"+2^{48},",
    r"&=(-1)^{\hat d}\binom{2k-\hat b_0}{2k-\hat a_0}\binom{k-\hat b_1}{k-\hat a_1} \binom{\hat b_2-\hat a_2-1}"
    r"{k-\hat a_2}\binom{\hat b_3-\hat a_3-1}{k-\hat a_3}\in\mathbb Z",
    r"B_k =\frac{\d}{\d t}\bigl(\hat R(t)(t+k)^2\bigr)|_{t=-k}",
    r"&=\zeta(2)\cdot(-1)^{\hat d}\sum_{k=\hat a_3^*}^{\hat b_2^*-1}A_k -(-1)^{\hat d}\sum_{k=\hat a_3^*}^{\hat b_2^*-1}"
    r"2A_k\sum_{\ell=1}^{2k-\hat a_0^*}\frac{(-1)^{\ell-1}}{\ell^2} \\ &\qquad -(-1)^{\hat d}\sum_{k=\hat a_2^*}"
    r"^{\hat b_3^*-1}B_k\sum_{\ell=1}^{2k-\hat a_0^*}\frac{(-1)^{\ell-1}}{\ell},",
    r"\hat a_0&=11n+2, &\quad \hat a_1&=3n+1, &\quad \hat a_2&=\phantom04n+1, &\quad \hat a_3&=\phantom05n+1, \\ "
    r"\hat b_0&=\phantom02n+2, &\quad \hat b_1&=1, &\quad \hat b_2&=10n+2, &\quad \hat b_3&=11n+2,",
    r"\hat\varphi(x)=\min_{0\le y<1}\biggl( & \lf 2y-\hat\beta_0x\rf-\lf 2y-\hat\alpha_0x\rf-\lf(\hat\alpha_0-\hat\beta_0)x"
    r"\rf \\[-4.5pt] &\; +\lf y-\hat\beta_1x\rf-\lf y-\hat\alpha_1x\rf-\lf(\hat\alpha_1-\hat\beta_1)x\rf \\[-3pt] &\; "
    r"+\sum_{j=2}^3\bigl(\lf(\hat\beta_j-\hat\alpha_j)x\rf-\lf\hat\beta_jx-y\rf-\lf y-\hat\alpha_jx\rf\bigr)\biggr).",
    r"&=\begin{cases} 2 &\text{if $x\in\bigl[\frac16,\frac29\bigr)\cup\bigl[\frac12,\frac59\bigr)\cup\bigl[\frac56,"
    r"\frac78\bigr)$}, \\ 1 &\text{if $x\in\bigl[\frac29,\frac49\bigr)\cup\bigl[\frac59,\frac79\bigr)\cup\bigl[\frac78,"
    r"\frac89\bigr)$}, \\ 0 &\text{otherwise}, \end{cases}",
    r"\lim_{n\to\infty}\frac{\log\hat\Phi_n}n=7.03418177\dotsc.",
    r"\tilde\varphi(x) =\max\{\varphi(x),\hat\varphi(x)\} =\begin{cases} 2 &\text{if $x\in\bigl[\frac16,\frac29\bigr)"
    r"\cup\bigl[\frac14,\frac27\bigr)\cup\bigl[\frac12,\frac47\bigr)\cup\bigl[\frac56,\frac78\bigr)$}, \\ 1 &\text{if "
    r"$x\in\bigl[\frac18,\frac17\bigr)\cup\bigl[\frac29,\frac14\bigr)\cup\bigl[\frac27,\frac49\bigr)\cup\bigl[\frac47,"
    r"\frac56\bigr)\cup\bigl[\frac78,\frac89\bigr)$}, \\ 0 &\text{otherwise}, \end{cases}",
    r"\tilde\Phi_n^{-1}q_n,\,\tilde\Phi_n^{-1}D_{9n}D_{8n}p_n\in\mathbb Z \quad\text{for}\; n=0,1,2,\dots,",
    r"=8.79117698\dotsc.",
    r"\tilde C_2=\lim_{n\to\infty}\frac{\log(\tilde\Phi_n^{-1}D_{9n}D_{8n})}n=8.20882301\dots",
    r"\mu(\zeta(2))\le\frac{C_0+C_1}{C_0-\tilde C_2}=5.09541178\dots",
    r"\mu(\pi\sqrt{d})\le10.19082357\dots$",
    r"=16.20882301\hdots>C_0,",
    r"\varphi(x)\ge\hat\varphi(x)$ for all $x\in[0,1)$ except for $x\in\bigl[\frac15,\frac29\bigr)\cup\bigl[\frac37,"
    r"\frac49\bigr)\cup\bigl[\frac67,\frac78\bigr)$.",
)

# the paper's parameters: a_j = ALPHA_j n + 1, b_j = BETA_j n + 1, b_4 = BETA_4 n + 2
ALPHA, BETA = (7, 6, 5, 8), (0, 1, 2, 14)
ALPHA_R3, BETA_R3 = (4, 5, 6, 7), (0, 1, 2, 12)                # Remark 3's other choice
ALPHA_HAT, BETA_HAT = (11, 3, 4, 5), (2, 0, 10, 11)            # a0^ = 11n+2, a1^..a3^ = 3n+1, 4n+1, 5n+1; b0^ = 2n+2, ...
GAMMA_0, GAMMA_1, GAMMA_2 = 9, 9, 8
F = Fraction
PHI_PRINTED = {2: [(F(1, 6), F(1, 5)), (F(1, 4), F(2, 7)), (F(1, 2), F(4, 7)), (F(5, 6), F(6, 7))],
               1: [(F(1, 8), F(1, 7)), (F(1, 5), F(1, 4)), (F(2, 7), F(3, 7)), (F(4, 7), F(5, 6)), (F(6, 7), F(8, 9))]}
PHIHAT_PRINTED = {2: [(F(1, 6), F(2, 9)), (F(1, 2), F(5, 9)), (F(5, 6), F(7, 8))],
                  1: [(F(2, 9), F(4, 9)), (F(5, 9), F(7, 9)), (F(7, 8), F(8, 9))]}
PHITILDE_PRINTED = {2: [(F(1, 6), F(2, 9)), (F(1, 4), F(2, 7)), (F(1, 2), F(4, 7)), (F(5, 6), F(7, 8))],
                    1: [(F(1, 8), F(1, 7)), (F(2, 9), F(1, 4)), (F(2, 7), F(4, 9)), (F(4, 7), F(5, 6)),
                        (F(7, 8), F(8, 9))]}
PHI_LESS_PRINTED = [(F(1, 5), F(2, 9)), (F(3, 7), F(4, 9)), (F(6, 7), F(7, 8))]   # where phi < phi^, as printed
REMARK4 = (2 ** 48, -(2 ** 20) * 3 ** 4 * 7 ** 5 * 2687491277, 3 ** 3 * 7 ** 7 * 794493690983053821271,
           2 ** 2 * 3 ** 12 * 7 ** 14)                          # lowest power of lambda first
PRINTED = {"C0": "15.88518998", "C1": "23.22906071", "lim_phi": "8.12793878", "C2": "8.87206121",
           "bound_first": "5.57728968", "lim_phihat": "7.03418177", "lim_phitilde": "8.79117698",
           "C2tilde": "8.20882301", "bound": "5.09541178", "abstract": "5.095412", "corollary": "10.19082357",
           "satellite": "16.20882301", "remark3": "5.20514736"}
PI50 = "3.14159265358979323846264338327950288419716939937510"
N_MAX = 100
RICH_N, RICH_ORDER, RICH_TOL = 95, 4, Fraction(1, 10 ** 5)
DECAY_FROM, DECAY_SLACK = 30, Fraction(1, 2)
DECAY_SHOW = (30, 60, 100)
M_DEN = 60
PRECISION = 60
R_DIGITS = 2100
QUAD_TOL = 1e-7
OUTPUTS = ("source", "bound", "constants", "functions", "forms", "sign", "inclusion", "growth", "decay", "remark4",
           "eq67_all_primes", "lemma5", "remark3", "conditions_met", "conditions_total", "test_passed",
           "controls_passed", "controls_total")


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


# --- integers and primes ------------------------------------------------------------------------------------------

def primes_upto(m):
    if m < 2:
        return []
    sieve = bytearray([1]) * (m + 1)
    sieve[0] = sieve[1] = 0
    for p in range(2, int(m ** 0.5) + 1):
        if sieve[p]:
            sieve[p * p::p] = bytearray(len(range(p * p, m + 1, p)))
    return [i for i in range(m + 1) if sieve[i]]


def lcm_upto(m, primes):
    """D_m = lcm(1, ..., m)."""
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
    """The p-adic valuation of a nonzero integer (None for 0)."""
    if x == 0:
        return None
    x = abs(x)
    k = 0
    while x % p == 0:
        x //= p
        k += 1
    return k


# --- the first construction (Proposition 1) ------------------------------------------------------------------------

def tale1(a, b, want_parts=False):
    """q and p with r = q zeta(2) - p for R(a, b; t) of Section 3 (Proposition 1), exactly (q an int, p a Fraction)."""
    a1, a2, a3, a4 = a
    b1, b2, b3, b4 = b
    if not (max(b1, b2, b3) <= min(a) and max(a) < b4 and a4 == max(a)):
        raise ValueError("the parameters break the conditions of Section 3, or a4 is not the largest a")
    d = sum(a) - sum(b)
    if d < 0:
        raise ValueError("d < 0")
    sgn = -1 if d % 2 else 1
    a2s = sorted(a)[1]
    fact = math.factorial
    C = {}
    for k in range(a4, b4):
        c = (math.comb(k - b1, k - a1) * math.comb(k - b2, k - a2) * math.comb(k - b3, k - a3)
             * math.comb(b4 - a4 - 1, k - a4))
        C[k] = -c if (d + b4 + k) % 2 else c
    q = sgn * sum(C.values())
    rden = fact(a1 - b1) * fact(a2 - b2) * fact(a3 - b3)
    rnum_c = fact(b4 - a4 - 1)

    def R_at(t):
        num = rnum_c
        for aj, bj in ((a1, b1), (a2, b2), (a3, b3)):
            for i in range(bj, aj):
                num *= t + i
        den = rden
        for i in range(a4, b4):
            den *= t + i
        return Fraction(num, den)

    def S_at(t):
        """sum_k C_k/(t + k) for an integer t (every t + k >= 1)."""
        M = math.lcm(*range(t + a4, t + b4))
        return Fraction(sum(C[k] * (M // (t + k)) for k in range(a4, b4)), M)

    Qs = [R_at(j + 1 - a2s) - S_at(j + 1 - a2s) for j in range(d + 1)]   # P(t) at t = 1 - a2* .. d + 1 - a2*
    L = 1
    for x in Qs:
        L = math.lcm(L, x.denominator)
    row = [x.numerator * (L // x.denominator) for x in Qs]
    A_scaled = []                                    # L A_l, the forward differences of L P there
    for _ in range(d + 1):
        A_scaled.append(row[0])
        row = [row[i + 1] - row[i] for i in range(len(row) - 1)]
    M2 = math.lcm(*range(1, d + 2))
    total = sum((-x if l % 2 else x) * (M2 // (l + 1)) for l, x in enumerate(A_scaled))
    polypart = sgn * Fraction(total, M2 * L)        # sum_l (-1)^(d+l) A_l/(l+1)
    h2 = [Fraction(0)]
    for l in range(1, b4 - a2s):
        h2.append(h2[-1] + Fraction(1, l * l))
    p = sgn * sum(C[k] * h2[k - a2s] for k in range(a4, b4)) - polypart
    if want_parts:
        return q, p, {"C": C, "d": d, "a2s": a2s, "R_at": R_at, "A": [Fraction(x, L) for x in A_scaled]}
    return q, p


def r1_from_parts(parts, t):
    """R(t) rebuilt from Proposition 1's decomposition, at a rational t: sum C_k/(t+k) + sum A_l P_l(t + a2*)."""
    C, d, a2s, R_at = parts["C"], parts["d"], parts["a2s"], parts["R_at"]
    Q = [R_at(j + 1 - a2s) - sum(Fraction(C[k], j + 1 - a2s + k) for k in C) for j in range(d + 1)]
    A = []
    for l in range(d + 1):
        A.append(sum((-1) ** (l - j) * math.comb(l, j) * Q[j] for j in range(l + 1)))
    s = t + a2s - 1                                   # P_l(t + a2*) = C(s, l), s = t + a2* - 1
    poly = Fraction(0)
    binom = Fraction(1)
    for l in range(d + 1):
        poly += A[l] * binom
        binom = binom * (s - l) / (l + 1)
    return sum(Fraction(C[k]) / (t + k) for k in C) + poly


# --- the second construction (Proposition 3) -----------------------------------------------------------------------

def tale2(ah, bh, want_parts=False):
    """q^ and p^ with r^ = q^ zeta(2) - p^ for R^ of Section 6 (Proposition 3), exactly."""
    A0, A1, A2, A3 = ah
    B0, B1, B2, B3 = bh
    if not (max(Fraction(B0, 2), B1) <= min(Fraction(A0, 2), A1, A2, A3) and max(Fraction(A0, 2), A1, A2, A3) < min(B2, B3)
            and A0 + A1 + A2 + A3 == B0 + B1 + B2 + B3 - 2):
        raise ValueError("the parameters break the conditions of Section 6")
    dh = B2 + B3
    sgn = -1 if dh % 2 else 1
    a1s, a2s, a3s = sorted((A1, A2, A3))
    a0s = min(A0, 2 * a2s)
    fact = math.factorial
    cnum = fact(B2 - A2 - 1) * fact(B3 - A3 - 1)
    cden = fact(A0 - B0) * fact(A1 - B1)
    Ak, Bk = {}, {}
    for k in range(min(A2, A3), max(B2, B3)):
        N0, N1 = cnum, 0
        for i in range(B0, A0):
            v = i - 2 * k
            N0, N1 = N0 * v, N0 * 2 + N1 * v
        for i in range(B1, A1):
            v = i - k
            N0, N1 = N0 * v, N0 + N1 * v
        D0, D1 = cden, 0
        mult = 0
        for lo, hi in ((A2, B2), (A3, B3)):
            for i in range(lo, hi):
                v = i - k
                if v == 0:
                    mult += 1
                    continue
                D0, D1 = D0 * v, D0 + D1 * v
        if mult == 0:
            continue
        F0 = Fraction(N0, D0)
        F1 = Fraction(N1 * D0 - N0 * D1, D0 * D0)
        if mult == 2:
            Ak[k], Bk[k] = F0, F1
        else:
            Ak[k], Bk[k] = Fraction(0), F0
    qh = sgn * sum(Ak.values())
    if qh.denominator == 1:
        qh = qh.numerator
    top = 2 * max(Bk) - a0s if Bk else 0
    eta1, eta2 = [Fraction(0)], [Fraction(0)]
    for l in range(1, top + 1):
        sgl = 1 if l % 2 else -1
        eta1.append(eta1[-1] + Fraction(sgl, l))
        eta2.append(eta2[-1] + Fraction(sgl, l * l))
    for k in Bk:
        if 2 * k - a0s < 0:
            raise ValueError("2k - a0* < 0")
    ph = sgn * (sum(2 * Ak[k] * eta2[2 * k - a0s] for k in Ak) + sum(Bk[k] * eta1[2 * k - a0s] for k in Bk))
    if want_parts:
        return qh, ph, {"A": Ak, "B": Bk, "dh": dh, "a0s": a0s, "a2s": a2s, "a3s": a3s,
                        "b2s": min(B2, B3), "b3s": max(B2, B3)}
    return qh, ph


def ak_closed(ah, bh, k):
    """A_k as Section 6 prints it."""
    A0, A1, A2, A3 = ah
    B0, B1, B2, B3 = bh

    def C(n, m):
        return math.comb(n, m) if 0 <= m <= n else 0
    v = C(2 * k - B0, 2 * k - A0) * C(k - B1, k - A1) * C(B2 - A2 - 1, k - A2) * C(B3 - A3 - 1, k - A3)
    return -v if (B2 + B3) % 2 else v


def r2_at(ah, bh, t):
    """R^(t) directly, at a rational t."""
    A0, A1, A2, A3 = ah
    B0, B1, B2, B3 = bh
    fact = math.factorial
    num = Fraction(fact(B2 - A2 - 1) * fact(B3 - A3 - 1), fact(A0 - B0) * fact(A1 - B1))
    for i in range(B0, A0):
        num *= 2 * t + i
    for i in range(B1, A1):
        num *= t + i
    for lo, hi in ((A2, B2), (A3, B3)):
        for i in range(lo, hi):
            num /= t + i
    return num


def r1_at(a, b, t):
    """R(t) of Section 3 directly, at a rational t."""
    a1, a2, a3, a4 = a
    b1, b2, b3, b4 = b
    fact = math.factorial
    v = Fraction(fact(b4 - a4 - 1), fact(a1 - b1) * fact(a2 - b2) * fact(a3 - b3))
    for aj, bj in ((a1, b1), (a2, b2), (a3, b3)):
        for i in range(bj, aj):
            v *= t + i
    for i in range(a4, b4):
        v /= t + i
    return v


def params(n):
    a = tuple(al * n + 1 for al in ALPHA)
    b = (BETA[0] * n + 1, BETA[1] * n + 1, BETA[2] * n + 1, BETA[3] * n + 2)
    return a, b


def params_hat(n):
    return ((ALPHA_HAT[0] * n + 2, ALPHA_HAT[1] * n + 1, ALPHA_HAT[2] * n + 1, ALPHA_HAT[3] * n + 1),
            (BETA_HAT[0] * n + 2, BETA_HAT[1] * n + 1, BETA_HAT[2] * n + 2, BETA_HAT[3] * n + 2))


# --- the arithmetic functions --------------------------------------------------------------------------------------

def fl(x):
    return math.floor(x)


def phi_lemma4(al, be, x):
    """Lemma 7's phi: the maximum over permutations alpha' of alpha."""
    base = fl((be[3] - al[3]) * x) - sum(fl((al[j] - be[j]) * x) for j in range(3))
    best = None
    for ap in set(permutations(al)):
        v = base - fl((be[3] - ap[3]) * x) + sum(fl((ap[j] - be[j]) * x) for j in range(3))
        best = v if best is None else max(best, v)
    return best


def frac(x):
    return x - fl(x)


def min_over_y(g, cuts):
    """The minimum over 0 <= y < 1 of a 1-periodic step function g whose steps lie at the given y in [0, 1): g is
    read at each cut and at the midpoint of each gap between consecutive cuts (and of the wrap-around gap)."""
    ys = sorted(set(frac(c) for c in cuts) | {Fraction(0)})
    cand = list(ys)
    for i, y in enumerate(ys):
        nxt = ys[i + 1] if i + 1 < len(ys) else ys[0] + 1
        cand.append((y + nxt) / 2)
    return min(g(frac(y)) for y in cand)


def phi_remark2(al, be, x):
    """Remark 2's other formula for phi (a minimum over y)."""
    def g(y):
        return (sum(fl(y - be[j] * x) - fl(y - al[j] * x) - fl((al[j] - be[j]) * x) for j in range(3))
                + fl((be[3] - al[3]) * x) - fl(be[3] * x - y) - fl(y - al[3] * x))
    cuts = [c * x for c in (be[0], be[1], be[2], al[0], al[1], al[2], al[3], be[3])]
    return min_over_y(g, cuts)


def phi_hat(ah, bh, x):
    """Lemma 8's phi^ (a minimum over y)."""
    def g(y):
        return (fl(2 * y - bh[0] * x) - fl(2 * y - ah[0] * x) - fl((ah[0] - bh[0]) * x)
                + fl(y - bh[1] * x) - fl(y - ah[1] * x) - fl((ah[1] - bh[1]) * x)
                + sum(fl((bh[j] - ah[j]) * x) - fl(bh[j] * x - y) - fl(y - ah[j] * x) for j in (2, 3)))
    cuts = []
    for c in (bh[0], ah[0]):
        cuts += [c * x / 2, (c * x + 1) / 2]
    cuts += [c * x for c in (bh[1], ah[1], ah[2], ah[3], bh[2], bh[3])]
    return min_over_y(g, cuts)


def step(printed, x):
    """A printed step function (value c on each listed [u, v), 0 elsewhere) at x, taken modulo 1."""
    x = frac(Fraction(x))
    for c, ivs in printed.items():
        for u, v in ivs:
            if u <= x < v:
                return c
    return 0


def grid_points(mden):
    """Every j/m in [0, 1) with m <= mden, and three interior points of each gap between consecutive ones."""
    pts = sorted({Fraction(j, m) for m in range(1, mden + 1) for j in range(m)})
    out = list(pts)
    for i, x in enumerate(pts):
        nxt = pts[i + 1] if i + 1 < len(pts) else Fraction(1)
        for w in (Fraction(1, 4), Fraction(1, 2), Fraction(3, 4)):
            out.append(x + w * (nxt - x))
    return out


def functions(pts):
    """Condition 2 and its neighbours: the functions as defined against the printed ones at every point."""
    bad = {"phi": [], "phihat": [], "phitilde": [], "remark2": [], "less": []}
    for x in pts:
        f1 = phi_lemma4(ALPHA, BETA, x)
        f2 = phi_hat(ALPHA_HAT, BETA_HAT, x)
        if f1 != step(PHI_PRINTED, x):
            bad["phi"].append(str(x))
        if f2 != step(PHIHAT_PRINTED, x):
            bad["phihat"].append(str(x))
        if max(f1, f2) != step(PHITILDE_PRINTED, x):
            bad["phitilde"].append(str(x))
        if phi_remark2(ALPHA, BETA, x) != f1:
            bad["remark2"].append(str(x))
        printed_less = any(u <= x < v for u, v in PHI_LESS_PRINTED)
        if (f1 < f2) != printed_less:
            bad["less"].append(str(x))
    return bad


# --- decimals ------------------------------------------------------------------------------------------------------

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


def to_dec(fr, prec):
    with decimal.localcontext() as ctx:
        ctx.prec = prec
        return Decimal(fr.numerator) / Decimal(fr.denominator)


def bernoulli(m):
    """B_0 .. B_m (B_1 = -1/2), exactly."""
    B = [Fraction(0)] * (m + 1)
    for k in range(m + 1):
        B[k] = Fraction(1) if k == 0 else -sum(math.comb(k + 1, i) * B[i] for i in range(k)) / (k + 1)
    return B


_BERN = bernoulli(60)


def digamma(x, shift=80, terms=30):
    """psi(x) for a Decimal x > 0: psi(x + shift) from its asymptotic series, then the recurrence downwards."""
    z = x + shift
    s = z.ln() - 1 / (2 * z)
    for k in range(1, terms + 1):
        s -= to_dec(_BERN[2 * k], PRECISION + 20) / (2 * k * z ** (2 * k))
    for k in range(shift):
        s -= 1 / (x + k)
    return s


def dec_of(fr):
    return Decimal(fr.numerator) / Decimal(fr.denominator)


def step_limit(printed, gamma2):
    """Lemma 7's limit for a step function: sum c (psi(v) - psi(u)) - the integral of c dx/x^2 below 1/gamma2."""
    total = Decimal(0)
    cut = Fraction(1, gamma2)
    for c, ivs in printed.items():
        for u, v in ivs:
            total += c * (digamma(dec_of(v)) - digamma(dec_of(u)))
            lo, hi = u, min(v, cut)
            if lo < hi:
                total -= c * (1 / dec_of(lo) - 1 / dec_of(hi))
    return total


def as_steps(fn, mden):
    """A step function as a dict value -> intervals, read from its values at the points j/m (m <= mden), for a
    function constant between consecutive such points (each interval [x_i, x_(i+1)) takes the value at x_i)."""
    pts = sorted({Fraction(j, m) for m in range(1, mden + 1) for j in range(m)}) + [Fraction(1)]
    out = {}
    i = 0
    while i < len(pts) - 1:
        c = fn(pts[i])
        j = i + 1
        while j < len(pts) - 1 and fn(pts[j]) == c:
            j += 1
        if c:
            out.setdefault(c, []).append((pts[i], pts[j]))
        i = j
    return out


def peval(coeffs, x):
    out = 0
    for c in reversed(coeffs):
        out = out * x + c
    return out


def cubic_of(al, be):
    """prod (tau - alpha_j) - prod (tau - beta_j), lowest power first, in integers."""
    def poly(roots):
        p = [1]
        for r in roots:
            p = [(p[i - 1] if i > 0 else 0) - r * (p[i] if i < len(p) else 0) for i in range(len(p) + 1)]
        return p
    pa, pb = poly(al), poly(be)
    diff = [x - y for x, y in zip(pa, pb)]
    if diff[-1] != 0:
        raise ValueError("not a cubic")
    return diff[:-1]


def discriminant(d0, c1, b2, a3):
    a, b, c, d = a3, b2, c1, d0
    return 18 * a * b * c * d - 4 * b ** 3 * d + b * b * c * c - 4 * a * c ** 3 - 27 * a * a * d * d


def bisect(coeffs, lo, hi, iterations):
    flo = peval(coeffs, lo)
    for _ in range(iterations):
        mid = (lo + hi) / 2
        fm = peval(coeffs, mid)
        if (fm < 0) == (flo < 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return (lo + hi) / 2


def lemma3(al, be):
    """C0 and C1 of Lemma 6, and the zeros of its cubic."""
    D = Decimal
    cub = [D(c) for c in cubic_of(al, be)]
    if discriminant(*cubic_of(al, be)) >= 0:
        raise ValueError("the cubic has three real zeros")
    lo = D(max(max(al), max(be)))
    hi = lo
    while (peval(cub, hi) < 0) == (peval(cub, lo) < 0):
        hi = hi * 2 + 1
        if hi > 10 ** 12:
            raise ValueError("no sign change above max(alpha, beta)")
    t1 = bisect(cub, lo, hi, 4 * PRECISION)
    c3, c2, c0 = cub[3], cub[2], cub[0]
    u = c2 / c3 + t1                                 # c3 (t - t1)(t^2 + u t + w)
    w = -c0 / (c3 * t1)
    re0 = -u / 2
    im0 = (w - u * u / 4).sqrt()

    def logabs(c):
        return (((re0 - c) ** 2 + im0 ** 2).ln()) / 2

    const = -sum((al[j] - be[j]) * D(al[j] - be[j]).ln() for j in range(3)) + (be[3] - al[3]) * D(be[3] - al[3]).ln()
    f1 = sum(al[j] * (t1 - al[j]).ln() - (be[j] * (t1 - be[j]).ln() if be[j] else 0) for j in range(4)) + const
    f0re = sum(al[j] * logabs(al[j]) - (be[j] * logabs(be[j]) if be[j] else 0) for j in range(4)) + const
    return {"C0": -f0re, "C1": f1, "tau1": t1, "tau0": (re0, im0)}


def digits_of(x, places):
    q = Decimal(1).scaleb(-places)
    return str(x.quantize(q, rounding=decimal.ROUND_DOWN))


def as_printed(x, printed):
    """Whether the printed decimal string is x cut or rounded to its number of decimals."""
    places = len(printed.split(".")[1])
    q = Decimal(1).scaleb(-places)
    return printed in (str(x.quantize(q, rounding=decimal.ROUND_DOWN)), str(x.quantize(q, rounding=decimal.ROUND_HALF_EVEN)))


def richardson(seq, n, order):
    total = Fraction(0)
    for i in range(order + 1):
        total += Fraction((-1) ** (order - i) * (n + i) ** order, math.factorial(i) * math.factorial(order - i)) * seq[n + i]
    return total


def remark4_zeros(coeffs=None):
    """The real zero of a cubic in lambda (lowest power first; Remark 4's by default) and, when the other two are a
    complex pair, their common modulus (None when the zeros are all real)."""
    D = Decimal
    if coeffs is None:
        coeffs = REMARK4
    cub = [D(c) for c in coeffs]
    if discriminant(*coeffs) >= 0:
        return None
    # the real zero: search outwards on both sides of 0 for a sign change
    found = None
    for sign in (-1, 1):
        x0 = D(0)
        x1 = D(sign)
        for _ in range(200):
            if (peval(cub, x0) < 0) != (peval(cub, x1) < 0):
                found = (x0, x1)
                break
            x0, x1 = x1, x1 * 2
        if found:
            break
    if not found:
        return None
    lo, hi = sorted(found)
    lam1 = bisect(cub, lo, hi, 6 * PRECISION)
    w = -cub[0] / (cub[3] * lam1)
    return {"lambda1": lam1, "abs_pair": w.sqrt()}


# --- the forms ------------------------------------------------------------------------------------------------------

def forms_all(nmax, primes):
    out = {}
    for n in range(1, nmax + 1):
        a, b = params(n)
        q, p = tale1(a, b)
        ah, bh = params_hat(n)
        qh, ph, parts = tale2(ah, bh, want_parts=True)
        out[n] = {"q": q, "p": p, "qh": qh, "ph": ph, "parts": parts}
    return out


def inclusion(forms, primes, phi_printed, small_too=False):
    """The first failures of ord_p q_n >= phi(n/p) and ord_p(D_9n D_8n p_n) >= phi(n/p), at primes p <= 8n with
    9n < p^2 (or every p <= 8n with small_too)."""
    fails = []
    for n, f in forms.items():
        X = f["p"] * lcm_upto(9 * n, primes) * lcm_upto(8 * n, primes)
        if X.denominator != 1:
            fails.append({"n": n, "what": "D9n D8n p_n not an integer"})
            continue
        X = X.numerator
        for p in primes:
            if p > 8 * n:
                break
            if not small_too and p * p <= GAMMA_0 * n:
                continue
            need = step(phi_printed, Fraction(n % p, p))
            if need == 0:
                continue
            for name, val in (("q", f["q"]), ("D9D8p", X)):
                v = v_p(val, p)
                if v is not None and v < need:
                    fails.append({"n": n, "p": p, "form": name, "need": need, "ord": v})
    return fails


def lemma5(forms, primes):
    """Lemma 8 at every prime p up to 11n: ord_p q^_n >= phi^(n/p) and ord_p p^_n >= -2 + phi^(n/p)."""
    fails = []
    for n, f in forms.items():
        for p in primes:
            if p > 11 * n + 2:
                break
            need = step(PHIHAT_PRINTED, Fraction(n % p, p))
            vq = v_p(f["qh"], p)
            if vq is not None and vq < need:
                fails.append({"n": n, "p": p, "form": "q^", "need": need, "ord": vq})
            ph = f["ph"]
            if ph != 0:
                vp = v_p(ph.numerator, p) - v_p(ph.denominator, p)
                if vp < need - 2:
                    fails.append({"n": n, "p": p, "form": "p^", "need": need - 2, "ord": vp})
    return fails


# --- quadrature control -----------------------------------------------------------------------------------------------

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


def panels(half, width, nodes):
    """Composite Gauss-Legendre nodes and weights on [-half, half], panels of the given width."""
    xs, ws = gauss_legendre(nodes)
    out = []
    k = int(round(2 * half / width))
    for j in range(k):
        lo = -half + j * width
        for x, w in zip(xs, ws):
            out.append((lo + (x + 1) * width / 2, w * width / 2))
    return out


def barnes1(a, b, half=24.0, width=0.5, nodes=16):
    """(-1)^d/(2 pi i) times the integral of (pi/sin pi t)^2 R(t) along Re t = 1/2 - a2* (Section 3), by composite
    Gauss-Legendre on Im t in [-half, half] (complex double precision)."""
    a1, a2, a3, a4 = a
    b1, b2, b3, b4 = b
    d = sum(a) - sum(b)
    c0 = 0.5 - sorted(a)[1]
    fact = math.factorial
    pref = fact(b4 - a4 - 1) / (fact(a1 - b1) * fact(a2 - b2) * fact(a3 - b3))
    total = 0j
    for y, w in panels(half, width, nodes):
        t = complex(c0, y)
        v = pref * (cmath.pi / cmath.sin(cmath.pi * t)) ** 2
        for aj, bj in ((a1, b1), (a2, b2), (a3, b3)):
            for i in range(bj, aj):
                v *= t + i
        for i in range(a4, b4):
            v /= t + i
        total += w * v
    total /= 2 * math.pi                              # dt = i dy, and 1/(2 pi i) times i
    return ((-1) ** d) * total


def barnes2(ah, bh, c, half=24.0, width=0.5, nodes=16):
    """(-1)^d^/(2 pi i) times the integral of pi/sin(2 pi t) R^(t) along Re t = c/2."""
    A0, A1, A2, A3 = ah
    B0, B1, B2, B3 = bh
    fact = math.factorial
    pref = fact(B2 - A2 - 1) * fact(B3 - A3 - 1) / (fact(A0 - B0) * fact(A1 - B1))
    total = 0j
    for y, w in panels(half, width, nodes):
        t = complex(c / 2, y)
        v = pref * cmath.pi / cmath.sin(2 * cmath.pi * t)
        for i in range(B0, A0):
            v *= 2 * t + i
        for i in range(B1, A1):
            v *= t + i
        for lo, hi in ((A2, B2), (A3, B3)):
            for i in range(lo, hi):
                v /= t + i
        total += w * v
    total /= 2 * math.pi
    return ((-1) ** (B2 + B3)) * total


# --- the assessment ----------------------------------------------------------------------------------------------------

def assess(inputs_dir):
    decimal.getcontext().prec = PRECISION
    raw = read_bytes(os.path.join(inputs_dir, INPUTS["eprint"][0]), INPUTS["eprint"][1])
    tex = tex_of(raw)
    check_source(tex)
    primes = primes_upto(12 * N_MAX + 10)

    # 2. the constants
    L3 = lemma3(ALPHA, BETA)
    C0, C1 = L3["C0"], L3["C1"]
    lim_phi = step_limit(PHI_PRINTED, GAMMA_2)
    lim_hat = step_limit(PHIHAT_PRINTED, GAMMA_2)
    lim_tilde = step_limit(PHITILDE_PRINTED, GAMMA_2)
    C2 = GAMMA_1 + GAMMA_2 - lim_phi
    C2t = GAMMA_1 + GAMMA_2 - lim_tilde
    bound = (C0 + C1) / (C0 - C2t)
    bound_first = (C0 + C1) / (C0 - C2)
    # Remark 3: its phi from Lemma 7's definition, gamma_1 = gamma_2 = 7
    L3r = lemma3(ALPHA_R3, BETA_R3)
    steps_r3 = as_steps(lambda x: phi_lemma4(ALPHA_R3, BETA_R3, x), M_DEN)
    C2r = 7 + 7 - step_limit(steps_r3, 7)
    bound_r3 = (L3r["C0"] + L3r["C1"]) / (L3r["C0"] - C2r)
    computed = {"C0": C0, "C1": C1, "lim_phi": lim_phi, "C2": C2, "bound_first": bound_first, "lim_phihat": lim_hat,
                "lim_phitilde": lim_tilde, "C2tilde": C2t, "bound": bound, "abstract": bound,
                "corollary": 2 * bound, "satellite": C2t + 8, "remark3": bound_r3}
    agree = {k: as_printed(computed[k], PRINTED[k]) for k in PRINTED}
    c1 = digits_of(bound, 8) == PRINTED["bound"] and agree["C0"] and agree["C1"] and agree["C2tilde"]

    # 3. the functions
    pts = grid_points(M_DEN)
    bad = functions(pts)
    c2 = not bad["phi"] and not bad["phihat"] and not bad["phitilde"]

    # 4. the forms
    forms = forms_all(N_MAX, primes)
    integral = all((f["p"] * lcm_upto(9 * n, primes) * lcm_upto(8 * n, primes)).denominator == 1
                   for n, f in forms.items())
    signs = set()
    sign_ok = True
    for n, f in forms.items():
        if f["q"] == f["qh"] and f["p"] == f["ph"]:
            signs.add(1)
        elif f["q"] == -f["qh"] and f["p"] == -f["ph"]:
            signs.add(-1)
        else:
            sign_ok = False
    sign_ok = sign_ok and len(signs) == 1
    incl = inclusion(forms, primes, PHITILDE_PRINTED)
    c3 = integral and sign_ok and not incl

    # 5. growth
    ratios = {n: abs(Fraction(forms[n + 1]["q"], forms[n]["q"])) for n in range(1, N_MAX)}
    rich = richardson(ratios, RICH_N, RICH_ORDER)
    eC1 = C1.exp()
    rich_dec = to_dec(rich, PRECISION)
    growth_ok = abs(rich_dec / eC1 - 1) < dec_of(RICH_TOL)
    pi_big = machin_pi(R_DIGITS)
    with decimal.localcontext() as ctx:
        ctx.prec = R_DIGITS
        z2 = pi_big * pi_big / 6
        decay, decay_ok, surviving = {}, True, []
        first_small = None
        for n in range(1, N_MAX + 1):
            q, p = forms[n]["q"], forms[n]["p"]
            big = Decimal(q) * z2
            val = big - to_dec(p, R_DIGITS)
            lost = (abs(big).adjusted() - abs(val).adjusted()) if val != 0 else R_DIGITS
            surviving.append(R_DIGITS - lost - 2)
            lr = abs(val).ln() / n if val != 0 else Decimal("-Infinity")
            decay[n] = lr
            if n >= DECAY_FROM and not (lr < -(C0 - dec_of(DECAY_SLACK))):
                decay_ok = False
        for n in range(N_MAX, 0, -1):
            if decay[n] >= 0:
                first_small = n + 1
                break
        else:
            first_small = 1
    digits_ok = min(surviving) >= 40
    rz = remark4_zeros()
    if rz is None:
        rem4_ok = False
        rem4 = {"lambda1": None, "abs_pair": None}
    else:
        dl1 = abs(abs(rz["lambda1"]).ln() - C1)
        dl2 = abs(rz["abs_pair"].ln() + C0)
        rem4_ok = dl1 < Decimal("1e-20") and dl2 < Decimal("1e-20")
        rem4 = {"lambda1": rz["lambda1"], "abs_pair": rz["abs_pair"], "dlog1": dl1, "dlog_pair": dl2}
    c4 = growth_ok and decay_ok and digits_ok and rem4_ok

    cond = {"C1 the bound and its constants": c1, "C2 the arithmetic functions": c2,
            "C3 the forms' arithmetic": c3, "C4 the growth": c4}

    # 6. beside
    incl_all = inclusion(forms, primes, PHITILDE_PRINTED, small_too=True)
    l5 = lemma5(forms, primes)
    ak_ok, bsum_ok = True, True
    for n, f in forms.items():
        ah, bh = params_hat(n)
        for k, v in f["parts"]["A"].items():
            if v != ak_closed(ah, bh, k):
                ak_ok = False
        if sum(f["parts"]["B"].values()) != 0:
            bsum_ok = False

    # 7. controls
    ctl = controls(primes, pi_big, forms)

    met = sum(cond.values())
    small_fail = [x for x in incl_all if "p" in x]
    out = {
        "source": "arXiv:1310.1526v3, sha256 6b2981bb..., all %d printed formulas found" % len(PRINTED_TEX),
        "bound": digits_of(bound, 20),
        "constants": "C0 %s C1 %s C2~ %s (%d of %d printed constants agree)" % (
            digits_of(C0, 10), digits_of(C1, 10), digits_of(C2t, 10), sum(agree.values()), len(agree)),
        "functions": "phi, phi^, phi~ against print: %d, %d, %d points differ of %d" % (
            len(bad["phi"]), len(bad["phihat"]), len(bad["phitilde"]), len(pts)),
        "forms": "n 1 to %d: D9n D8n p_n integral %s; (q, p) = e (q^, p^) %s" % (
            N_MAX, "yes" if integral else "no", "yes" if sign_ok else "no"),
        "sign": (sorted(signs)[0] if len(signs) == 1 else 0),
        "inclusion": "%d failures at primes sqrt(9n) < p <= 8n" % len(incl),
        "growth": "Richardson ratio %s, e^C1 %s" % (digits_of(rich_dec, 4), digits_of(eC1, 4)),
        "decay": "log|r_n|/n at n = %s: %s; -C0 %s" % (
            ", ".join(str(n) for n in DECAY_SHOW), ", ".join(digits_of(decay[n], 4) for n in DECAY_SHOW if n in decay),
            digits_of(-C0, 4)),
        "remark4": ("moduli %s, %s" % (digits_of(abs(rem4["lambda1"]).ln(), 12), digits_of(rem4["abs_pair"].ln(), 12))
                    if rem4["lambda1"] is not None else "no complex pair"),
        "eq67_all_primes": "%d failures at primes p <= 8n (all n <= %d)" % (len(small_fail), N_MAX),
        "lemma5": "%d failures" % len(l5),
        "remark3": digits_of(bound_r3, 10),
        "conditions_met": met, "conditions_total": len(cond), "test_passed": int(met == len(cond)),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    detail = {
        "test": TEST, "conditions": cond, "controls": ctl,
        "computed": {k: str(v) for k, v in computed.items()}, "printed": PRINTED, "agree": agree,
        "lemma3": {"tau1": str(L3["tau1"]), "tau0": [str(x) for x in L3["tau0"]]},
        "functions_bad": bad, "points": len(pts),
        "remark3_phi": {str(c): [[str(u), str(v)] for u, v in ivs] for c, ivs in steps_r3.items()},
        "remark3_C0_C1_C2": [str(L3r["C0"]), str(L3r["C1"]), str(C2r)],
        "signs": sorted(signs), "inclusion_failures": incl, "eq67_failures": small_fail[:200],
        "lemma5_failures": l5[:200], "ak_closed_form_agrees": ak_ok, "sum_B_zero": bsum_ok,
        "prop1_D": "D_{c1} D_{c2} = D_9n D_8n (c1 = 8n, c2 = 9n)",
        "richardson": str(rich_dec), "eC1": str(eC1),
        "ratios_tail": {n: str(to_dec(ratios[n], 30)) for n in range(N_MAX - 10, N_MAX)},
        "decay": {n: str(v)[:30] for n, v in decay.items()}, "surviving_digits_min": min(surviving),
        "first_n_from_which_r_below_1": first_small,
        "remark4": {k: str(v) for k, v in rem4.items()},
        "log_q_over_n_60": str((Decimal(abs(forms[N_MAX]["q"])).ln() / N_MAX)),
    }
    return out, detail


def controls(primes, pi_big, forms):
    ctl = {}
    ctl["(a) Machin's pi"] = str(pi_big)[:52] == PI50
    D = Decimal
    g1 = digamma(D(1)) - digamma(D(1) / 2)
    g2 = digamma(D(2) / 3) - digamma(D(1) / 2)
    sqrt3 = D(3).sqrt()
    pi = machin_pi(PRECISION)
    ctl["(b) digamma at rationals"] = (abs(g1 - 2 * D(2).ln()) < D("1e-40")
                                       and abs(g2 - (pi / (2 * sqrt3) - (3 * sqrt3 / 4).ln())) < D("1e-40"))
    seq = {n: 2 + Fraction(3, n) - Fraction(5, n * n) + Fraction(7, n ** 3) for n in range(10, 20)}
    ctl["(c) Richardson"] = abs(richardson(seq, 12, 4) - 2) < Fraction(1, 10 ** 6)
    pf_ok = True
    for n in (1, 2, 3):
        a, b = params(n)
        _, _, parts = tale1(a, b, want_parts=True)
        if r1_from_parts(parts, Fraction(1, 3)) != r1_at(a, b, Fraction(1, 3)):
            pf_ok = False
        ah, bh = params_hat(n)
        _, _, p2 = tale2(ah, bh, want_parts=True)
        t = Fraction(1, 3)
        rebuilt = sum(v / (t + k) ** 2 for k, v in p2["A"].items()) + sum(v / (t + k) for k, v in p2["B"].items())
        if rebuilt != r2_at(ah, bh, t):
            pf_ok = False
    ctl["(d) partial fractions"] = pf_ok
    qd_ok = True
    for n in (1,):
        a, b = params(n)
        quad = barnes1(a, b)
        rr = rel_r(forms[n]["q"], forms[n]["p"], pi_big)
        qd_ok &= abs(quad.real - rr) <= QUAD_TOL * abs(rr) and abs(quad.imag) <= QUAD_TOL * abs(rr)
    ah, bh = params_hat(1)
    a0s = min(ah[0], 2 * sorted(ah[1:])[1])
    cpos = -a0s + 0.5                                 # inside (-a0^*, 1 - b0^), and no pole on Re t = cpos/2
    quad2 = barnes2(ah, bh, cpos)
    rr2 = rel_r(forms[1]["qh"], forms[1]["ph"], pi_big)
    qd_ok &= abs(quad2.real - rr2) <= QUAD_TOL * abs(rr2) and abs(quad2.imag) <= QUAD_TOL * abs(rr2)
    ctl["(e) Barnes integrals by quadrature"] = qd_ok
    wh_signs = set()
    for n in range(1, 7):
        a = (4 * n + 1, 3 * n + 1, 3 * n + 1, 5 * n + 1)
        b4 = 9 * n + 2
        b = (1, a[3] - a[0] + 1, a[3] - a[1] + 1, b4)
        ah = (b4 - a[2] + a[3], a[1], a[0], a[3])
        bh = (a[3] + 1, a[3] - a[2] + 1, a[0] + a[1], b4)
        q1, _ = tale1(a, b)
        q2, _ = tale2(ah, bh)
        wh_signs.add(1 if q1 == q2 else (-1 if q1 == -q2 else 0))
    ctl["(f) Whipple's transformation, up to one sign"] = len(wh_signs) == 1 and 0 not in wh_signs
    raised = {k: list(v) for k, v in PHITILDE_PRINTED.items()}
    raised[2] = [iv for iv in raised[2] if iv != (F(1, 6), F(2, 9))]
    raised[3] = [(F(1, 6), F(2, 9))]
    ctl["(g) a raised phi~ is caught"] = bool(inclusion(forms, primes, raised))
    return ctl


def rel_r(q, p, pi_big):
    """q zeta(2) - p as a float, from 200-digit decimals."""
    with decimal.localcontext() as ctx:
        ctx.prec = 200
        z2 = pi_big * pi_big / 6
        return float(to_dec(Fraction(q), 200) * z2 - to_dec(Fraction(p), 200))


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    out, detail = assess(inputs)
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="utf-8") as fh:
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
        sys.exit(f"zeta2: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
