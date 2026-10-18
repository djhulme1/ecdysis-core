#!/usr/bin/env python3
"""Niedbala Giraudin's law for the Salikhov-Zeilberger-Zudilin-Bai family: within Salikhov's configuration, is
Bai's point (1857, 1857, 2785) the minimum, mu = 7.101862832356...?

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from David Niedbala Giraudin, "A closed-form
law for the Salikhov-Zeilberger-Zudilin-Bai family, and computational evidence that Bai's point is optimal",
arXiv:2609.37459v2 (5 October 2026; v1 28 September; CC BY 4.0), its abstract: "Within that configuration the minimum
is 7.101862832356 at (1857,1857,2785), which is Bai's point, the vertex sitting exactly at Q = 2a/(3a-2b) = 3714."
The configuration is Salikhov's, (P, w) = (5, 1+2i), which the sentence before names. The note labels the statement
VERIFIED (its Sections 8 and 9: finite computations), credits Claude (Anthropic) with technical assistance, and rests
on Bai's bound (arXiv:2609.11276, the lab's pi/bai.py, ext:12d112870a970612) and on Zeilberger and Zudilin's
(arXiv:1912.06345, pi/zz.py, ext:80b8e1febcd7cc56).

The family and its law, as the note defines them (Sections 2 to 5 and 7). R(x) = x^E0 (x^4 - 2Dx^2 + N^2)^E1 /
(P^2 - x^2)^F with E0 = a0 n, E1 = a1 n, F = bn + 1, D = u^2 - v^2 and N = u^2 + v^2 for w = u + vi; at (5, 1+2i),
D = -3, N = 5 and M = P^2 = 25. With g(y) = y^(a0/2) (y^2 - 2Dy + N^2)^a1 / (y - M)^b:
  the stationary cubic (a0+4a1-2b) y^3 - [a0(2D+M) + 4a1(D+M) - 4bD] y^2 + [a0(N^2+2DM) + 4a1 DM - 2bN^2] y
  - a0 M N^2 = 0, its roots' levels E_i = log|g(zeta_i)|, S = max_i E_i, and s the min-max value (Theorem 2), with
  s <= s_min = -min_i E_i, so that mu computed from s_min is a lower bound for mu;
  R = max(b, a0 + 4a1 - 2b); the window: the primes p <= Rn with t = n/p such that the arc [rho, rho + 2 alpha]
  lies inside the arc [1/2, 1/2 + beta] mod 1 (rho = {(a0/2) t}, alpha = {a1 t}, beta = {b t}); W its psi-measure,
  the limit of (1/n) times the sum of log p over it;
  at (5, 1+2i): c2 = 2.5 (2a1 - b) if b <= 2a1 and 4a1 - 2b otherwise; cP = max(0, 2b - a0 - 2a1); no odd content;
  Lambda = R - W - c2 log 2 + cP log 5, and mu = 1 + (S + Lambda)/(s - Lambda), a bound only where S > 0, s > 0 and
  s > Lambda.

The input is the note's v2 e-print from arXiv (a gzipped tar holding the TeX and the ancillary verifier
anc/verify_szzb.py), checked against its SHA-256 and read as data from memory. Every rule below was fixed before any
of the quantities it tests was computed; the seed is not used, as nothing here is random. Before the rules, the whole
TeX and the verifier's source were read, and this code was timed only on substitute exponents (ratios near the
note's other base (3/2, 7/4), none in the test's sets) and the cubic at another configuration (P = 13, w = 7 + 4i);
nothing at Salikhov's configuration was computed.

1. The source. With TeX comments removed and all whitespace deleted, the TeX must contain every string in
   PRINTED_TEX (the integrand, the cubic, S and s_min, R, the window, the savings, Lambda and mu, the calibration
   rows, the sentence under test in the summary table, and every printed value compared beside the test), and the
   tar must hold the verifier; otherwise the run is refused.
2. The law at a triple, exactly (mpmath at DPS = 40 digits). If a0 is odd the triple is doubled (mu depends only
   on the ratios, the note's Theorem 7; the window's period in t is then 1). With A = a0/2, B = a1 and C = b the
   window is E = {u in [0, 1): {A u + 1/2} + 2{B u} < {C u}} (the arc criterion written out: the arc from rho of
   length 2 alpha lies in the arc from 1/2 of length beta iff {rho - 1/2} + 2 alpha <= beta, and
   {rho - 1/2} = {A u + 1/2}; this is the set E of Bai's paper at her triple), found exactly: on each cell between
   consecutive breakpoints (u with A u + 1/2, B u or C u an integer) the floors are constant, so E meets the cell in
   an initial segment, a final segment, or all or none of it, as d = A + 2B - C is positive, negative or zero, cut
   where d u + 1/2 meets the cell's K = floor(A u + 1/2) + 2 floor(B u) - floor(C u); touching pieces are merged.
   W = sum over E's components [l, r) of psi(r + 1) - psi(l + 1) + (1/max(l, 1/R) - 1/r if r > 1/R, else 0): the
   measure dt/t^2 of E's periodic extension over t >= 1/R (primes up to Rn). The cubic's roots by mpmath.polyroots
   (a root is real when its imaginary part is below 10^-20); S, s_min and Lambda as above; mu_low = 1 + (S + Lambda)/
   (s_min - Lambda). A triple with a0 + 4a1 - 2b = 0 is degenerate (the cubic drops a degree; the note sets these
   apart) and is counted apart; one with S <= 0, s_min <= 0 or s_min <= Lambda yields no bound.
3. The same in floating point for the scans (numpy and scipy's digamma; the cubic and the levels with every exponent
   divided by a1; roots by numpy.roots polished by two Newton steps). Its values only choose which triples are
   recomputed by rule 2: every triple whose floating mu_low is below Bai's floating mu plus TIE = 5e-9, and every
   triple a later rule or the comparisons beside the test name, is recomputed exactly, and every comparison in the
   test uses the exact values.
4. The min-max value, where the test needs it (a triple whose exact mu_low is at or below Bai's) and at Bai's and
   Zeilberger and Zudilin's points: on a GRID of 601 by 301 points over the upper half x-plane (Re x within
   +-(1.3 max(P, |Re sqrt(zeta)|) + 1), Im x from 0 to 1.3 max(v, |Im sqrt(zeta)|) + 1), the least level M at which
   the point nearest -wbar = -1 + 2i is joined to the real axis through points with log|g(x^2)| <= M (the points
   taken in order of their level and joined to their neighbours by union-find); s = -E_i for the critical level E_i
   nearest the grid's M (the note reads the level off the exact critical value in the same way).
5. The test, two conditions.
   Condition 1: at (1857, 1857, 2785) the cubic has one real root and a conjugate pair, the pair's level is the least
   of the three and is the min-max value of rule 4, and mu (= mu_low there) begins 7.101862832356 (the quote's digits).
   Condition 2: no primitive triple (gcd 1) other than Bai's, in the three sets below, yields a bound at or below
   Bai's mu: one whose exact mu_low is at or below it and whose mu with s the min-max value (rule 4) is too.
     set 1: 1 <= a0, a1 <= 40 and 1 <= b <= 100;
     set 2: a0 = a1 = a with 2 <= a <= 8000 and 1.4995 <= b/a <= 1.5003;
     set 3: 2 <= a1 <= 3000, a0 != a1 with |a0 - a1| <= 0.002 a1, and 1.4995 <= b/a1 <= 1.5003.
   test_passed is 1 if both hold.
6. Beside the test, none of it counted, each against the note's printed values (decimals compared both cut and
   rounded): the three calibrations of its Section 5 (Lambda and mu at (2,2,3) and at Bai's point; at (3,3,5) mu with
   the window's first two components, the note's "his own two-branch window", W = 0.57064923 and 7.6063085207111912,
   and with all of them, W = 0.63855046 and 7.4147395226; at Bai's point the window's 2784 components and
   W = 601.2828866806, and 599.138404 for the ray (2,2,3) at that scale); the calibration cubic 2y^3 - 125y^2 - 500y
   - 625 with y3, N3, |N1| and l = -3.524772924; Section 8's Q table (mu minus Bai's, in 1e-9, at Q = 3694 ... 3716 on
   the slice x = 1, y = 3/2 - 1/Q, each at its primitive triple), its scan (i) (odd a from 1841 to 1881 with
   b = (3a - 1)/2: a = 1857 the strict minimum, the neighbours 1855 and 1859 at +2.6e-9 and +8.2e-9) and scan (ii)
   (the 162 primitive (q, q, p) with 1500 <= q <= 3748 and 1.499715 <= p/q <= 1.499745, Bai's the least, the next
   (3712, 3712, 5567) at +1.51e-9); its table of dips (the bases (6,4,7), (4,3,5), (10,7,12) and the printed best
   points (15000,10000,17499) and (4952,3714,6189), nine decimals); Section 9's tables at rational points (the 5 by 7
   table, four decimals; the slice at Q = 50 ... 60000 and above the ray at Q = 50 ... 10^5, the points at 10^6 and
   3.10^6 left out for size); Section 7's row for (5, 1+2i) over its range (primitive a0, a1 <= 10, b <= 22: 1848
   triples, 33 degenerate; 665 with S, s_min > 0, 291 with s_min > Lambda, the least 7.103205334 at (2,2,3)); and the
   note's own verifier, run once in this sandbox as published (its source piped from memory to python3 -I -), its
   printed mu at the three calibrations and at Bai's neighbours.

Controls (controls_passed of controls_total):
 (a) the window at (2,2,3), (A, B, C) = (1, 2, 3), is exactly [1/2, 2/3) and its W is psi(2/3) - psi(1/2) =
     pi/(2 sqrt 3) - (3/2) log 3 + 2 log 2 to 35 digits;
 (b) floating point against exact: at 40 triples drawn evenly from the three sets (those yielding a bound), the
     same number of window components and mu_low within 1e-11;
 (c) the window at Bai's (doubled) point against the lab's pi/bai.py (the receipt f22c6ac8... on her bound): its
     E_set(1857, 3714, 5570) is the same list of components, and its rates() bound 1 + sigma/tau, whose growth rate
     comes from the positive-coefficient saddle of her S(z), not from the cubic's levels, equals mu within 1e-30;
 (d) the same two routes at three more triples where Bai's formula applies (R = a0 + 4a1 - 2b, b <= 2a1, cP = 0):
     (2,2,3), (3712,3712,5567) and (1855,1855,2782), mu against her B within 1e-25;
 (e) the cubic at (2,2,3) is twice 2y^3 - 125y^2 - 500y - 625, and at Bai's doubled point twice Bai's printed
     3715y^3 - 232119y^2 - 928475y - 1160625;
 (f) the min-max value at (2,2,3) (rule 4) is the conjugate pair's level, -3.524772924 to nine decimals;
 (g) negative controls, each caught: with the window replaced by the ray's at Bai's scale, mu at Bai's point does
     not begin 7.101862832356; and a triple planted below Bai's value in a copy of set 2's results is flagged by the
     comparison;
 (h) scipy's digamma against mpmath's at 25 points in (1, 2] within 2e-15.

What it cannot check: the law's derivation (the window's sufficiency, the savings, Theorem 2's min-max argument),
which is the note's; directions other than the three sets' lattice points; and the other fifteen configurations of
the note's Section 7, which are not tested.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 pi/szzb.py (the pinned scipy-notebook image, for numpy, scipy and mpmath).
"""

import gzip
import hashlib
import importlib.util
import io
import json
import math
import multiprocessing
import os
import re
import subprocess
import sys
import tarfile
import time
from fractions import Fraction

import mpmath
import numpy as np
import scipy.special

INPUT = ("arXiv-2609.37459v2.tar.gz", "327e18fad5302b7574310c0744233d3b93500c3da2fdefa2c7079ffa3b960bed", 32145)
TEX_NAME = "szzb_family.tex"
VERIFIER_NAME = "anc/verify_szzb.py"
P, U, V = 5, 1, 2
D, N, M = U * U - V * V, U * U + V * V, P * P            # -3, 5, 25
BAI = (1857, 1857, 2785)
ZZ = (2, 2, 3)
DPS = 40
TIE = 5e-9
GRID = (601, 301)
QUOTE_DIGITS = "7.101862832356"
SET1 = (40, 40, 100)
SET2 = (8000, Fraction(14995, 10000), Fraction(15003, 10000))
SET3 = (3000, Fraction(2, 1000))
WORKERS = 2
VERIFIER_TIMEOUT = 1200
LIMIT = 200

TEST = ("Refuted if, with the note's law recomputed at Salikhov's (P,w) = (5,1+2i) (Λ = R − W − c₂ log 2 + c_P log 5, "
        "W the ψ-measure of its window, μ = 1 + (S+Λ)/(s−Λ), S the largest level of its stationary cubic, s the "
        "min-max level), μ(1857,1857,2785) does not begin 7.101862832356, or some other primitive (a0,a1,b) yielding "
        "a bound has μ at or below it: with a0, a1 ≤ 40 and b ≤ 100; or a0 = a1 ≤ 8000 and 1.4995 ≤ b/a1 ≤ 1.5003; "
        "or a1 ≤ 3000, 0 < |a0/a1 − 1| ≤ 0.002 and b/a1 in that range.")

OUTPUTS = ("mu_bai", "condition_1", "mu_zz", "set1", "set2", "set3", "at_or_below", "runner_up", "pair_least",
           "calibrations", "q_table", "section8_scans", "dips", "section9_tables", "section7_row", "verifier",
           "conditions_met", "conditions_total", "test_passed", "controls_passed", "controls_total")

PRINTED_TEX = [
    r"R(x)=\frac{x^{E_0}\,(x^4-2Dx^2+N^2)^{E_1}}{(P^2-x^2)^{F}}",
    r"E_0=a_0n,\quad E_1=a_1n,\quad F=bn+1",
    r"(a_0+4a_1-2b)\,y^3-\big[a_0(2D+M)+4a_1(D+M)-4bD\big]y^2",
    r"{}+\big[a_0(N^2+2DM)+4a_1DM-2bN^2\big]y-a_0MN^2=0",
    r"$E_i=\log|g(\zeta_i)|$ for their levels, and put $S=\max_i E_i$",
    r"s\ \le\ s_{\min}:=-\min_i E_i",
    r"R=\max(b,\,a_0+4a_1-2b)",
    r"Every window prime must therefore satisfy $p\le Rn$",
    r"$\rho=\{(a_0n/2)/p\}$, $\alpha=\{a_1n/p\}$, $\beta=\{bn/p\}$",
    r"\text{the arc } [\rho,\ \rho+2\alpha] \text{ must lie inside the arc } [1/2,\ 1/2+\beta] \pmod 1",
    r"For $(2,2,3)$ the window is exactly $[1/2,2/3)$, $W=0.64527561$",
    r"c_2 &= 2(\lambda_++\lambda_-)a_1-\big(1+\max(\lambda_+,\lambda_-,1)\big)b &&\text{if } b\le 2a_1",
    r"c_2 &= 4\lambda_- a_1-(1+\lambda_-)b &&\text{if } b>2a_1",
    r"c_P &= \max(0,\ 2b-a_0-2a_1) &&\text{(a cost)}",
    r"For $(5,1+2i)$: $\lambda_-=1$, $\lambda_+=3/2$, so $c_2=2.5(2a_1-b)$ resp. $4a_1-2b$; no odd $q$.",
    r"\Lambda \;=\; R-W-c_2\log 2+c_P\log P-\sum_q c_q\log q",
    r"\mu \;=\; 1+\frac{S+\Lambda}{s-\Lambda}",
    r"$(2,2,3)$ & 1.621856438365 & 7.1032053341370017 & 7.10320533413700172750 (Zeilberger--Zudilin)",
    r"$(3,3,5)$ & 4.305920726 & 7.6063085207111912 & 7.606308 (Salikhov)",
    r"$(1857,1857,2785)$ & 1503.882786468 & 7.1018628323563507 & 7.101862832357 (Bai)",
    r"The Salikhov line uses his own two-branch window, $W=0.57064923$; with the full three-branch window derived "
    r"here the same integral gives $7.4147395226$",
    r"At Bai's point the window has 2784 branches and $W=601.2828866806$, against $599.138404$ for the exact ray "
    r"$(2,2,3)$ at the same scale",
    r"yields $\mu(\pi)\le 7.4147395226$ ($W=0.63855046$)",
    r"$2y^3-125y^2-500y-625=0$",
    r"$y_3=66.3395015246$, $N_3=21851.6913962$, $|N_1|=0.0294584959281$",
    r"$\ell=-3.524772924$, so $s=3.524772924$",
    r"Within that configuration the minimum is $\mu=7.101862832356$ at $(1857,1857,2785)$, which is Bai's point; the "
    r"vertex sits exactly at $Q=2a/(3a-2b)=3714$.",
    r"$Q$ & 3694 & 3700 & 3704 & 3708 & 3710 & 3712 & 3713 & 3713.5 & 3714 & 3714.5 & 3715 & 3716 \\",
    r"$\mu-$Bai, in $10^{-9}$ & 5.39 & 5.02 & 4.63 & 2.86 & 2.63 & 1.51 & 0.76 & 0.41 & 0 & 1.11 & 2.16 & 4.32 \\",
    r"(i) All odd $a$ from 1841 to 1881, both residues mod~4: $a=1857$ is a strict minimum, neighbours at "
    r"$+2.6\cdot 10^{-9}$ and $+8.2\cdot 10^{-9}$.",
    r"(ii) An exhaustive scan of the 162 primitive rationals $p/q$ with $q\in[1500,3748]$ and "
    r"$y\in[1.499715,1.499745]$: Bai's is the unique minimum, the next being $(3712,3712,5567)$ at "
    r"$+1.51\cdot 10^{-9}$.",
    r"$(3/2,7/4)$ & 7.250861742 & 7.250539184 at $(15000,10000,17499)$",
    r"$(4/3,5/3)$ & 7.387260401 & 7.387036254 at $(4952,3714,6189)$",
    r"$(10/7,12/7)$ & 7.330100902 & none found",
    r"$Q$ & 50 & 200 & 800 & 1800 & 3000 & 3714 & 5000 & 12000 & 60000 & $10^6$ \\",
    r"$\mu$ & 7.4485 & 7.1513 & 7.1065 & 7.1024 & 7.10190 & 7.1018628 & 7.10191 & 7.10230 & 7.10289 & 7.10317 \\",
    r"$Q$ & 50 & 400 & 2500 & 3714 & 15000 & $10^5$ & $10^6$ & $3\cdot 10^6$ \\",
    r"$\mu$ at $y=3/2+1/Q$ & 7.2487 & 7.1341 & 7.1100 & 7.1080 & 7.1046 & 7.1035 & 7.10324 & 7.10322 \\",
    r"$y$ & $x=0.98$ & $x=0.995$ & $x=0.999$ & $x=1$ & $x=1.001$ & $x=1.005$ & $x=1.02$ \\",
    r"1.4950 & 7.4094 & 7.1833 & 7.1611 & 7.1513 & 7.1694 & 7.2339 & 7.4677 \\",
    r"1.4997 & 7.4836 & 7.2154 & 7.1239 & 7.1019 & 7.1170 & 7.1742 & 7.3925 \\",
    r"1.5000 & 7.4900 & 7.2225 & 7.1328 & 7.1032 & 7.1171 & 7.1730 & 7.3900 \\",
    r"1.5050 & 7.5080 & 7.2587 & 7.1811 & 7.1565 & 7.1597 & 7.1634 & 7.2780 \\",
    r"$(5,1+2i)$ & 0.4472 & $1+$pair & 665 & 291 $\to$ least 7.103205334 at $(2,2,3)$",
    r"First, $33$ of the $1848$ primitive triples of the range have $a_0+4a_1-2b=0$.",
]

PRINTED = {
    "cal": {"L223": "1.621856438365", "mu223": "7.1032053341370017", "zz": "7.10320533413700172750",
            "L335": "4.305920726", "mu335": "7.6063085207111912", "W335two": "0.57064923", "W335full": "0.63855046",
            "mu335full": "7.4147395226", "Lbai": "1503.882786468", "mubai": "7.1018628323563507",
            "branches": 2784, "Wbai": "601.2828866806", "Wray": "599.138404", "W223": "0.64527561"},
    "cubic": {"y3": "66.3395015246", "N3": "21851.6913962", "N1": "0.0294584959281", "ell": "-3.524772924"},
    "qtable": [("3694", "5.39"), ("3700", "5.02"), ("3704", "4.63"), ("3708", "2.86"), ("3710", "2.63"),
               ("3712", "1.51"), ("3713", "0.76"), ("3713.5", "0.41"), ("3714", "0"), ("3714.5", "1.11"),
               ("3715", "2.16"), ("3716", "4.32")],
    "scan_i": ((1841, 1881), ("2.6", "8.2")),
    "scan_ii": (162, (3712, 3712, 5567), "1.51"),
    "dips": [((6, 4, 7), "7.250861742"), ((15000, 10000, 17499), "7.250539184"), ((4, 3, 5), "7.387260401"),
             ((4952, 3714, 6189), "7.387036254"), ((10, 7, 12), "7.330100902")],
    "slice": [(50, "7.4485"), (200, "7.1513"), (800, "7.1065"), (1800, "7.1024"), (3000, "7.10190"),
              (3714, "7.1018628"), (5000, "7.10191"), (12000, "7.10230"), (60000, "7.10289")],
    "above": [(50, "7.2487"), (400, "7.1341"), (2500, "7.1100"), (3714, "7.1080"), (15000, "7.1046"),
              (100000, "7.1035")],
    "xs": [Fraction(49, 50), Fraction(199, 200), Fraction(999, 1000), Fraction(1), Fraction(1001, 1000),
           Fraction(201, 200), Fraction(51, 50)],
    "ys": [Fraction(299, 200), Fraction(14997, 10000), Fraction(3, 2), Fraction(301, 200)],
    "xtable": [["7.4094", "7.1833", "7.1611", "7.1513", "7.1694", "7.2339", "7.4677"],
               ["7.4836", "7.2154", "7.1239", "7.1019", "7.1170", "7.1742", "7.3925"],
               ["7.4900", "7.2225", "7.1328", "7.1032", "7.1171", "7.1730", "7.3900"],
               ["7.5080", "7.2587", "7.1811", "7.1565", "7.1597", "7.1634", "7.2780"]],
    "sec7": (1848, 33, 665, 291, "7.103205334", (2, 2, 3)),
}
BAI_CUBIC = (3715, -232119, -928475, -1160625)
ZZ_CUBIC = (2, -125, -500, -625)


class Refused(Exception):
    pass


# ---------------------------------------------------------------- the source (rule 1)

def read_source(path):
    with open(path, "rb") as fh:
        blob = fh.read()
    if len(blob) != INPUT[2] or hashlib.sha256(blob).hexdigest() != INPUT[1]:
        raise Refused("the e-print does not match its pinned size and SHA-256")
    tf = tarfile.open(fileobj=io.BytesIO(gzip.decompress(blob)))
    names = {m.name: m for m in tf.getmembers() if m.isfile()}
    if TEX_NAME not in names or VERIFIER_NAME not in names:
        raise Refused("the e-print lacks the TeX or the verifier")
    tex = tf.extractfile(names[TEX_NAME]).read().decode("utf-8")
    verifier = tf.extractfile(names[VERIFIER_NAME]).read()
    lines = [re.sub(r"(?<!\\)%.*$", "", line) for line in tex.split("\n")]
    flat = re.sub(r"\s+", "", "\n".join(lines))
    missing = [s for s in PRINTED_TEX if re.sub(r"\s+", "", s) not in flat]
    if missing:
        raise Refused(f"the TeX does not print: {missing[:3]}")
    return flat, verifier


# ---------------------------------------------------------------- triples

def norm(t):
    """The triple doubled if a0 is odd, so that A = a0/2 is an integer (mu depends only on the ratios)."""
    a0, a1, b = t
    return (2 * a0, 2 * a1, 2 * b) if a0 % 2 else (a0, a1, b)


def primitive(t):
    return math.gcd(math.gcd(t[0], t[1]), t[2]) == 1


def degenerate(t):
    return t[0] + 4 * t[1] - 2 * t[2] == 0


def R_of(t):
    a0, a1, b = t
    return max(b, a0 + 4 * a1 - 2 * b)


def c2_of(t):
    a0, a1, b = t
    return Fraction(5, 2) * (2 * a1 - b) if b <= 2 * a1 else Fraction(4 * a1 - 2 * b)


def cP_of(t):
    a0, a1, b = t
    return max(0, 2 * b - a0 - 2 * a1)


def cubic_coeffs(t, cfg=None):
    a0, a1, b = t
    D, N, M = cfg if cfg is not None else (globals()["D"], globals()["N"], globals()["M"])
    return (a0 + 4 * a1 - 2 * b,
            -(a0 * (2 * D + M) + 4 * a1 * (D + M) - 4 * b * D),
            a0 * (N * N + 2 * D * M) + 4 * a1 * D * M - 2 * b * N * N,
            -a0 * M * N * N)


# ---------------------------------------------------------------- the window, exactly (rule 2)

def window_exact(A, B, C):
    """E = {u in [0,1): {A u + 1/2} + 2{B u} < {C u}} as merged half-open intervals of Fractions."""
    L = math.lcm(2 * A, B, C)
    h = L // (2 * A)
    pts = set(range(0, L, L // B)) | set(range(0, L, L // C)) | set(range(h, L, 2 * h))
    pts.add(L)
    mm = sorted(pts)
    d = A + 2 * B - C
    pieces = []
    for lo, hi in zip(mm, mm[1:]):
        K = (2 * A * lo + L) // (2 * L) + 2 * ((B * lo) // L) - (C * lo) // L
        if d > 0:                                   # d m + L/2 < K L  iff  m < (2K - 1) L / (2d)
            num, den = (2 * K - 1) * L, 2 * d
            if num > den * lo:
                r = Fraction(hi, L) if num >= den * hi else Fraction(num, den * L)
                pieces.append((Fraction(lo, L), r))
        elif d < 0:                                 # m > (1 - 2K) L / (2|d|)
            num, den = (1 - 2 * K) * L, -2 * d
            if num < den * hi:
                l_ = Fraction(lo, L) if num <= den * lo else Fraction(num, den * L)
                pieces.append((l_, Fraction(hi, L)))
        elif 2 * K > 1:
            pieces.append((Fraction(lo, L), Fraction(hi, L)))
    merged = []
    for lo, hi in pieces:
        if merged and merged[-1][1] == lo:
            merged[-1] = (merged[-1][0], hi)
        else:
            merged.append((lo, hi))
    return merged


def W_exact(comps, R):
    mp = mpmath.mpf
    cut = Fraction(1, R)
    tot = mp(0)
    for l_, r_ in comps:
        lm, rm = mp(l_.numerator) / l_.denominator, mp(r_.numerator) / r_.denominator
        tot += mpmath.psi(0, rm + 1) - mpmath.psi(0, lm + 1)
        if r_ > cut:
            lo = max(l_, cut)
            tot += mp(lo.denominator) / lo.numerator - mp(r_.denominator) / r_.numerator
    return tot


def law_exact(t, comps_override=None, W_override=None):
    """The note's law at a triple, in mpmath; mu_low uses s_min (a lower bound; the value where the least level is the
    min-max value)."""
    tn = norm(t)
    a0, a1, b = tn
    out = {"triple": t, "norm": tn}
    with mpmath.workdps(DPS):
        mp = mpmath.mpf
        cub = cubic_coeffs(tn)
        out["cubic"] = cub
        if cub[0] == 0:
            out["status"] = "degenerate"
            return out
        roots = mpmath.polyroots([mp(c) for c in cub], maxsteps=400, extraprec=3 * DPS)
        tiny = mp(10) ** -20

        def lev(z):
            return (mp(a0) / 2 * mpmath.log(abs(z)) + a1 * mpmath.log(abs(z * z - 2 * D * z + N * N))
                    - b * mpmath.log(abs(z - M)))
        info = []
        for z in roots:
            real = abs(mpmath.im(z)) < tiny
            info.append((lev(z), real, z))
        levels = [x[0] for x in info]
        S, smin = max(levels), -min(levels)
        nreal = sum(1 for x in info if x[1])
        least = min(info, key=lambda x: x[0])
        out.update({"S": S, "s_min": smin, "n_real": nreal, "least_is_pair": (nreal == 1 and not least[1]),
                    "levels": levels, "roots": [z for _, _, z in info]})
        A, B, C = a0 // 2, a1, b
        R = R_of(tn)
        comps = comps_override if comps_override is not None else window_exact(A, B, C)
        W = W_override if W_override is not None else W_exact(comps, R)
        c2, cP = c2_of(tn), cP_of(tn)
        Lam = R - W - mp(c2.numerator) / c2.denominator * mpmath.log(2) + cP * mpmath.log(5)
        out.update({"R": R, "W": W, "c2": c2, "cP": cP, "Lambda": Lam, "components": len(comps), "comps": comps})
        if S <= 0 or smin <= 0 or smin <= Lam:
            out["status"] = "nobound"
            return out
        out["status"] = "bound"
        out["mu_low"] = 1 + (S + Lam) / (smin - Lam)
        scale = 2 if tn != tuple(t) else 1                      # W and Lambda of the triple as given
        out["W_given"], out["Lambda_given"] = W / scale, Lam / scale
    return out


# ---------------------------------------------------------------- the same in floating point (rule 3)

def window_fast(A, B, C):
    """E's pieces as float arrays (l, r), their exact widths and the number of merged components, in numpy int64
    (None if it could overflow)."""
    L = math.lcm(2 * A, B, C)
    if L * (2 * (A + 2 * B + C) + 4) >= 2 ** 62:
        return None
    h = L // (2 * A)
    s1 = np.arange(0, L, L // B, dtype=np.int64)
    s2 = np.arange(0, L, L // C, dtype=np.int64)
    s3 = np.arange(h, L, 2 * h, dtype=np.int64)
    mm = np.unique(np.concatenate([s1, s2, s3, np.array([L], dtype=np.int64)]))
    lo, hi = mm[:-1], mm[1:]
    K = (2 * A * lo + L) // (2 * L) + 2 * ((B * lo) // L) - (C * lo) // L
    d = A + 2 * B - C
    if d > 0:
        num, den = (2 * K - 1) * L, 2 * d
        keep = num > den * lo
        full = num >= den * hi
        l_ = lo / L
        r_ = np.where(full, hi / L, num / (den * L))
        wid = np.where(full, (hi - lo) / L, (num - den * lo) / (den * L))
        touch = keep[:-1] & full[:-1] & keep[1:]
    elif d < 0:
        num, den = (1 - 2 * K) * L, -2 * d
        keep = num < den * hi
        part = num > den * lo
        l_ = np.where(part, num / (den * L), lo / L)
        r_ = hi / L
        wid = np.where(part, (den * hi - num) / (den * L), (hi - lo) / L)
        touch = keep[:-1] & keep[1:] & ~part[1:]
    else:
        keep = 2 * K > 1
        l_, r_, wid = lo / L, hi / L, (hi - lo) / L
        touch = keep[:-1] & keep[1:]
    ncomp = int(np.sum(keep)) - int(np.sum(touch))
    l_, r_, wid = l_[keep], r_[keep], wid[keep]
    return l_, r_, wid, ncomp


def W_fast(pieces, R):
    l_, r_, wid, _ = pieces
    psi = scipy.special.digamma
    tot = float(np.sum(psi(r_ + 1.0) - psi(l_ + 1.0)))
    cut = 1.0 / R
    above = l_ >= cut
    k0 = np.where(above, wid / np.maximum(l_ * r_, 1e-300), np.where(r_ > cut, R - 1.0 / r_, 0.0))
    return tot + float(np.sum(k0))


def n_components_fast(pieces):
    return pieces[3]


def roots_fast(t, cfg=None):
    a0, a1, b = t
    D, N, M = cfg if cfg is not None else (globals()["D"], globals()["N"], globals()["M"])
    x, y = a0 / a1, b / a1
    c = [x + 4 - 2 * y, -(x * (2 * D + M) + 4 * (D + M) - 4 * y * D), x * (N * N + 2 * D * M) + 4 * D * M
         - 2 * y * N * N, -x * M * N * N]
    rts = np.roots(c).astype(complex)
    for _ in range(2):
        f = ((c[0] * rts + c[1]) * rts + c[2]) * rts + c[3]
        fp = (3 * c[0] * rts + 2 * c[1]) * rts + c[2]
        ok = fp != 0
        rts = np.where(ok, rts - np.where(ok, f / np.where(ok, fp, 1), 0), rts)
    return rts, x, y


def lev_fast(z, x, y, cfg=None):
    D, N, M = cfg if cfg is not None else (globals()["D"], globals()["N"], globals()["M"])
    return (x / 2) * np.log(np.abs(z)) + np.log(np.abs(z * z - 2 * D * z + N * N)) - y * np.log(np.abs(z - M))


def law_fast(t):
    """(status, mu_low, n_real, least_is_pair) in floating point, every quantity divided by a1."""
    if degenerate(t):
        return ("degenerate", None, None, None)
    tn = norm(t)
    a0, a1, b = tn
    rts, x, y = roots_fast(tn)
    lv = lev_fast(rts, x, y)
    real = np.abs(rts.imag) < 1e-9 * np.maximum(1.0, np.abs(rts.real))
    S, smin = float(np.max(lv)), -float(np.min(lv))
    nreal = int(np.sum(real))
    least_pair = bool(nreal == 1 and not real[int(np.argmin(lv))])
    if S <= 0 or smin <= 0:
        return ("nobound", None, nreal, least_pair)
    R = R_of(tn)
    pieces = window_fast(a0 // 2, a1, b)
    if pieces is None:
        return ("exact", None, nreal, least_pair)
    W = W_fast(pieces, R)
    c2, cP = c2_of(tn), cP_of(tn)
    Lam = (R - W - float(c2) * math.log(2) + cP * math.log(5)) / a1
    if smin <= Lam:
        return ("nobound", None, nreal, least_pair)
    return ("bound", 1.0 + (S + Lam) / (smin - Lam), nreal, least_pair)


def _scan(chunk):
    return [(t,) + law_fast(t) for t in chunk]


def scan(triples, workers=WORKERS):
    if not triples:
        return []
    size = max(1, len(triples) // (8 * workers) + 1)
    chunks = [triples[i:i + size] for i in range(0, len(triples), size)]
    if workers <= 1:
        res = [_scan(c) for c in chunks]
    else:
        with multiprocessing.get_context("fork").Pool(workers) as pool:
            res = pool.map(_scan, chunks)
    return [r for part in res for r in part]


# ---------------------------------------------------------------- the sets (rule 5)

def set1():
    a0m, a1m, bm = SET1
    return [(a0, a1, b) for a0 in range(1, a0m + 1) for a1 in range(1, a1m + 1) for b in range(1, bm + 1)
            if primitive((a0, a1, b))]


def b_range(a1, lo, hi):
    b0 = -((-lo.numerator * a1) // lo.denominator)            # ceil
    b1 = (hi.numerator * a1) // hi.denominator                # floor
    return range(b0, b1 + 1)


def set2():
    amax, lo, hi = SET2
    return [(a, a, b) for a in range(2, amax + 1) for b in b_range(a, lo, hi) if math.gcd(a, b) == 1]


def set3():
    a1max, dev = SET3
    lo, hi = SET2[1], SET2[2]
    out = []
    for a1 in range(2, a1max + 1):
        k = (dev.numerator * a1) // dev.denominator
        for a0 in range(a1 - k, a1 + k + 1):
            if a0 == a1 or a0 < 1:
                continue
            for b in b_range(a1, lo, hi):
                if primitive((a0, a1, b)):
                    out.append((a0, a1, b))
    return out


# ---------------------------------------------------------------- the min-max value (rule 4)

def minmax(t, grid=GRID, conf=None):
    """The grid's min-max level from -wbar to the real axis (per a1) and the critical level nearest it; conf is
    (P, u, v), Salikhov's by default."""
    P, U, V = conf if conf is not None else (globals()["P"], globals()["U"], globals()["V"])
    cfg = (U * U - V * V, U * U + V * V, P * P)
    tn = norm(t)
    rts, x, y = roots_fast(tn, cfg)
    crit = [float(v) for v in lev_fast(rts, x, y, cfg)]
    sq = np.sqrt(rts.astype(complex))
    X = 1.3 * max(P, U, float(np.max(np.abs(sq.real)))) + 1.0
    Y = 1.3 * max(V, float(np.max(np.abs(sq.imag)))) + 1.0
    nx, ny = grid
    re_ = np.linspace(-X, X, nx)
    im_ = np.linspace(0.0, Y, ny)
    Z = re_[None, :] + 1j * im_[:, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        val = lev_fast(Z * Z, x, y, cfg)
    val = np.where(np.isnan(val), np.inf, val)
    flat = val.ravel()
    start = int(np.argmin(np.abs(im_ - V))) * nx + int(np.argmin(np.abs(re_ + U)))
    parent = list(range(nx * ny))
    axis = [False] * (nx * ny)
    for i in range(nx):
        axis[i] = True                                      # row 0 is the real axis
    active = [False] * (nx * ny)

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    level = None
    for idx in np.argsort(flat, kind="stable"):
        idx = int(idx)
        if not math.isfinite(flat[idx]) and flat[idx] > 0:
            break
        active[idx] = True
        j, i = divmod(idx, nx)
        for jj, ii in ((j - 1, i), (j + 1, i), (j, i - 1), (j, i + 1)):
            if 0 <= jj < ny and 0 <= ii < nx and active[jj * nx + ii]:
                ra, rb = find(idx), find(jj * nx + ii)
                if ra != rb:
                    parent[ra] = rb
                    axis[rb] = axis[rb] or axis[ra]
        if active[start] and axis[find(start)]:
            level = float(flat[idx])
            break
    if level is None:
        return {"grid_level": None, "level": None, "crit": crit}
    near = min(range(3), key=lambda k: abs(crit[k] - level))
    real = abs(rts[near].imag) < 1e-9 * max(1.0, abs(rts[near].real))
    return {"grid_level": level, "level": crit[near], "gap": abs(crit[near] - level), "index": near,
            "at_pair": not real, "crit": crit, "box": (X, Y)}


def mu_with_minmax(ex, mm):
    """mu with s = -(the min-max level), from an exact law record and a minmax record (levels per a1)."""
    a1 = ex["norm"][1]
    k = mm["index"]
    lv = [mpmath.mpf(v) for v in ex["levels"]]
    # match the floating critical level to the exact one by value
    exact = min(lv, key=lambda v: abs(float(v) / a1 - mm["level"]))
    s = -exact
    if s <= ex["Lambda"] or s <= 0:
        return None
    return 1 + (ex["S"] + ex["Lambda"]) / (s - ex["Lambda"])


# ---------------------------------------------------------------- comparisons

def cut_or_round(x, printed):
    """True if the printed decimal is x cut or rounded to its number of decimals."""
    s = printed.strip()
    neg = s.startswith("-")
    places = len(s.split(".")[1]) if "." in s else 0
    with mpmath.workdps(DPS):
        v = mpmath.mpf(x)
        q = mpmath.mpf(10) ** places
        cut = mpmath.floor(abs(v) * q) / q
        rnd = mpmath.floor(abs(v) * q + mpmath.mpf(1) / 2) / q
        want = abs(mpmath.mpf(s))
        tol = mpmath.mpf(10) ** -(places + 6)
        ok_sign = (v < 0) == neg or want == 0
        return bool(ok_sign and (abs(cut - want) < tol or abs(rnd - want) < tol))


def s_(x, n=25):
    return mpmath.nstr(x, n, strip_zeros=False)


def q_triple(Q):
    """The primitive triple on the slice x = 1 at y = 3/2 - 1/Q (Q a decimal string)."""
    q = Fraction(Q)
    y = Fraction(3, 2) - 1 / q
    return (y.denominator, y.denominator, y.numerator)


def above_triple(Q):
    y = Fraction(3, 2) + Fraction(1, Q)
    return (y.denominator, y.denominator, y.numerator)


def xy_triple(x, y):
    a1 = math.lcm(x.denominator, y.denominator)
    t = (int(x * a1), a1, int(y * a1))
    g = math.gcd(math.gcd(t[0], t[1]), t[2])
    return tuple(v // g for v in t)


def compare_planted(results, mu_ref):
    """Indices of results (triple, status, mu) at or below mu_ref (used by the negative control)."""
    return [k for k, r in enumerate(results) if r[1] == "bound" and r[2] is not None and r[2] <= mu_ref]


# ---------------------------------------------------------------- the verifier, beside the test

def run_verifier(source):
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, "-I", "-"], input=source, capture_output=True, timeout=VERIFIER_TIMEOUT)
        text = p.stdout.decode("utf-8", "replace")
        rc = p.returncode
    except subprocess.TimeoutExpired as e:
        text = (e.stdout or b"").decode("utf-8", "replace")
        rc = "timeout"
    dt = time.time() - t0
    got = {"returncode": rc, "seconds": round(dt, 1)}
    m = re.search(r"\(a0,a1,b\) = \(2,2,3\)\s+Zeilberger-Zudilin.*?mu\s+=\s+(\S+)", text, re.S)
    got["mu223"] = m.group(1) if m else None
    m = re.search(r"two-branch window : W = (\S+) , Lambda = (\S+) , mu = (\S+)", text)
    got["mu335two"] = m.group(3) if m else None
    m = re.search(r"three-branch window : W = (\S+) , mu = (\S+)", text)
    got["mu335full"] = m.group(2) if m else None
    m = re.search(r"window : (\d+) branches", text)
    got["branches"] = int(m.group(1)) if m else None
    m = re.search(r"Bai's point \(1857,1857,2785\).*?Lambda = (\S+)\s+mu = (\S+)", text, re.S)
    got["mubai"] = m.group(2) if m else None
    got["neighbours"] = {f"({a},{b},{c})": mu for a, b, c, q, mu in
                         re.findall(r"\((\d+),(\d+),(\d+)\)\s+Q = (\d+)\s+mu = (\S+)", text)}
    m = re.search(r"least SCREENED mu over all sixteen configurations and the whole range :\s+(\S+) at", text)
    got["least_screened"] = m.group(1) if m else None
    m = re.search(r"total elapsed (\S+) s", text)
    got["finished"] = bool(m)
    got["tail"] = text[-1500:]
    return got


# ---------------------------------------------------------------- the lab's pi/bai.py, for controls (c), (d)

def load_bai():
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("pi_bai", os.path.join(here, "bai.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- the run

def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    path = os.path.join(inputs, INPUT[0])
    if not os.path.exists(path):
        raise Refused(f"missing input {INPUT[0]}")
    _, verifier_src = read_source(path)
    timing = {}
    t0 = time.time()
    mpmath.mp.dps = DPS
    mp = mpmath.mpf
    ctl = {}

    # ---- Bai's point and the calibrations, exactly
    bai = law_exact(BAI)
    zz = law_exact(ZZ)
    mu_bai = bai["mu_low"]
    mm_bai = minmax(BAI)
    mm_zz = minmax(ZZ)
    cond = {}
    c1_parts = {"one real root and a pair": bai["n_real"] == 1, "the pair's level the least": bai["least_is_pair"],
                "the grid's min-max at the pair": bool(mm_bai.get("at_pair")) and
                abs(mm_bai["level"] - float(min(bai["levels"])) / bai["norm"][1]) < 1e-12,
                "mu begins " + QUOTE_DIGITS: s_(mu_bai, 30).startswith(QUOTE_DIGITS)}
    cond["condition 1: mu at (1857,1857,2785) begins 7.101862832356, s the pair's (least, min-max) level"] = \
        all(c1_parts.values())
    timing["exact calibrations"] = round(time.time() - t0, 1)

    # ---- the scans (floating point), then exact recomputation of every near tie
    t1 = time.time()
    sets = {"set 1": set1(), "set 2": set2(), "set 3": set3()}
    scans = {k: scan(v) for k, v in sets.items()}
    timing["scans"] = round(time.time() - t1, 1)
    mu_bai_f = float(mu_bai)
    t2 = time.time()
    exact_cache = {BAI: bai, ZZ: zz}

    def ex(t):
        if t not in exact_cache:
            exact_cache[t] = law_exact(t)
        return exact_cache[t]
    summary, refuting, near = {}, [], {}
    for name, res in scans.items():
        counts = {"primitive": len(res), "degenerate": 0, "nobound": 0, "bound": 0, "exact_only": 0}
        bound = []
        pair_least = [0, 0]
        for t, status, mu, nreal, lp in res:
            if status == "exact":
                counts["exact_only"] += 1
                e = ex(t)
                status, mu = e["status"], (float(e["mu_low"]) if e["status"] == "bound" else None)
            counts[status] += 1
            if status == "bound":
                bound.append((mu, t))
                if name != "set 1":
                    pair_least[0] += 1
                    pair_least[1] += int(bool(lp))
        bound.sort()
        cand = [t for mu, t in bound if t != BAI and mu <= mu_bai_f + TIE]
        recs = []
        for t in cand:
            e = ex(t)
            recs.append(e)
            if e["status"] == "bound" and e["mu_low"] <= mu_bai:
                mm = minmax(t)
                mu_t = mu_with_minmax(e, mm) if mm.get("level") is not None else None
                refuting.append({"set": name, "triple": t, "mu_low": s_(e["mu_low"]),
                                 "mu_minmax": (s_(mu_t) if mu_t is not None else "no bound"),
                                 "refutes": bool(mu_t is not None and mu_t <= mu_bai)})
        least = [(mu, t) for mu, t in bound if t != BAI][:3]
        least_exact = [(ex(t)["mu_low"], t) for _, t in least if ex(t)["status"] == "bound"]
        least_exact.sort()
        summary[name] = {"counts": counts, "least": [(s_(m, 20), t) for m, t in least_exact],
                         "recomputed": len(cand), "pair_least": pair_least}
        near[name] = least_exact
    n_ref = sum(1 for r in refuting if r["refutes"])
    cond["condition 2: no other primitive triple in the three sets yields a bound at or below Bai's mu"] = n_ref == 0
    timing["exact near ties"] = round(time.time() - t2, 1)

    # ---- controls
    t3 = time.time()
    comps223 = window_exact(1, 2, 3)
    W223 = W_exact(comps223, R_of(ZZ))
    closed = mpmath.pi / (2 * mpmath.sqrt(3)) - mp(3) / 2 * mpmath.log(3) + 2 * mpmath.log(2)
    ctl["(a) the window at (2,2,3) is [1/2, 2/3) and W = psi(2/3) - psi(1/2) to 35 digits"] = bool(
        comps223 == [(Fraction(1, 2), Fraction(2, 3))] and abs(W223 - closed) < mp(10) ** -35)
    pool = []
    for name, k_ in (("set 1", 14), ("set 2", 13), ("set 3", 13)):
        b_ = [(mu, t) for t, st, mu, nr, lp in scans[name] if st == "bound"]
        step = max(1, len(b_) // k_)
        pool += [b_[k] for k in range(0, len(b_), step)][:k_]
    worst, comp_ok = 0.0, True
    for mu_f, t in pool:
        e = ex(t)
        tn = norm(t)
        pieces = window_fast(tn[0] // 2, tn[1], tn[2])
        if pieces is None or n_components_fast(pieces) != e["components"]:
            comp_ok = False
        if e["status"] == "bound":
            worst = max(worst, abs(float(e["mu_low"]) - mu_f))
    ctl["(b) floating point against exact at 40 triples of the sets: components alike, mu_low within 1e-11"] = bool(
        comp_ok and worst < 1e-11 and len(pool) == 40)
    baimod = load_bai()
    E_bai = baimod.E_set(1857, 3714, 5570)
    Rb = baimod.rates(1857, 3714, 5570)
    ctl["(c) Bai's window and bound by the lab's pi/bai.py: the same components, 1 + sigma/tau = mu within 1e-30"] = \
        bool(E_bai == bai["comps"] and abs(Rb["B"] - mu_bai) < mp(10) ** -30)
    routes = {}
    for t, bt in ((ZZ, (1, 2, 3)), ((3712, 3712, 5567), (1856, 3712, 5567)), ((1855, 1855, 2782), (1855, 3710, 5564))):
        e = ex(t)
        Rx = baimod.rates(*bt)
        routes[str(t)] = (s_(e["mu_low"], 30), mpmath.nstr(Rx["B"], 30), float(abs(Rx["B"] - e["mu_low"])))
    ctl["(d) the law's mu against Bai's B (her saddle route) at (2,2,3), (3712,3712,5567), (1855,1855,2782)"] = all(
        v[2] < 1e-25 for v in routes.values())
    cz = cubic_coeffs(ZZ)
    cb = cubic_coeffs(norm(BAI))
    ctl["(e) the cubic: twice ZZ's 2y^3 - 125y^2 - 500y - 625 and twice Bai's printed cubic"] = bool(
        tuple(cz) == tuple(2 * v for v in ZZ_CUBIC) and tuple(cb) == tuple(2 * v for v in BAI_CUBIC))
    ell = mm_zz["level"] * 2 if mm_zz.get("level") is not None else None
    ctl["(f) the min-max value at (2,2,3) is the pair's level, -3.524772924"] = bool(
        mm_zz.get("at_pair") and ell is not None and cut_or_round(ell, PRINTED["cubic"]["ell"]))
    with mpmath.workdps(DPS):                     # the ray's measure at the doubled triple's scale, 1857 W(2,2,3)
        W_ray_doubled = mp(1857) * (mpmath.psi(0, mp(2) / 3) - mpmath.psi(0, mp(1) / 2))
    ray = law_exact(BAI, comps_override=bai["comps"], W_override=W_ray_doubled)
    planted = list(scans["set 2"]) + [((1, 1, 1), "bound", mu_bai_f - 1e-9, 1, True)]
    flagged = compare_planted([(r[0], r[1], r[2]) for r in planted], mu_bai_f)
    ctl["(g) negatives: the ray's window at Bai's point fails condition 1; a planted triple is flagged"] = bool(
        ray["status"] == "bound" and not s_(ray["mu_low"], 30).startswith(QUOTE_DIGITS)
        and (len(planted) - 1) in flagged)
    xs = [1 + k / 25 for k in range(1, 26)]
    dev = max(abs(float(scipy.special.digamma(v)) - float(mpmath.psi(0, mp(v)))) for v in xs)
    ctl["(h) scipy's digamma against mpmath's at 25 points in (1, 2] within 2e-15"] = dev < 2e-15
    timing["controls"] = round(time.time() - t3, 1)

    # ---- beside the test
    t4 = time.time()
    pr = PRINTED["cal"]
    t335 = law_exact((3, 3, 5))
    two = t335["comps"][:2]
    t335two = law_exact((3, 3, 5), comps_override=two)
    W_ray_bai = mp(1857) / 2 * (mpmath.psi(0, mp(2) / 3) - mpmath.psi(0, mp(1) / 2))
    cal = {
        "Lambda(2,2,3)": cut_or_round(zz["Lambda_given"], pr["L223"]),
        "mu(2,2,3) law": cut_or_round(zz["mu_low"], pr["mu223"]),
        "mu(2,2,3) ZZ": cut_or_round(zz["mu_low"], pr["zz"]),
        "W(2,2,3)": cut_or_round(zz["W_given"], pr["W223"]),
        "Lambda(3,3,5) two-branch": cut_or_round(t335two["Lambda_given"], pr["L335"]),
        "W(3,3,5) two-branch": cut_or_round(t335two["W_given"], pr["W335two"]),
        "mu(3,3,5) two-branch": cut_or_round(t335two["mu_low"], pr["mu335"]),
        "W(3,3,5) full": cut_or_round(t335["W_given"], pr["W335full"]),
        "mu(3,3,5) full": cut_or_round(t335["mu_low"], pr["mu335full"]),
        "Lambda(Bai)": cut_or_round(bai["Lambda_given"], pr["Lbai"]),
        "mu(Bai)": cut_or_round(mu_bai, pr["mubai"]),
        "components(Bai)": bai["components"] == pr["branches"],
        "W(Bai)": cut_or_round(bai["W_given"], pr["Wbai"]),
        "W(ray at Bai's scale)": cut_or_round(W_ray_bai, pr["Wray"]),
    }
    cub = PRINTED["cubic"]
    zr = [z for z in zz["roots"] if abs(mpmath.im(z)) < mp(10) ** -20]
    zp = [z for z in zz["roots"] if abs(mpmath.im(z)) >= mp(10) ** -20]
    y3 = mpmath.re(zr[0]) if zr else mp(0)
    lev_pair = min(zz["levels"])
    cal["cubic y3"] = cut_or_round(y3, cub["y3"])
    cal["cubic N3"] = cut_or_round(mpmath.exp(max(zz["levels"])), cub["N3"])
    cal["cubic |N1|"] = cut_or_round(mpmath.exp(lev_pair), cub["N1"])
    cal["l"] = cut_or_round(lev_pair, cub["ell"])
    qrows = []
    for Q, val in PRINTED["qtable"]:
        t = q_triple(Q)
        e = ex(t) if t != BAI else bai
        diff = (e["mu_low"] - mu_bai) * mp(10) ** 9 if e["status"] == "bound" else None
        qrows.append((Q, t, (mpmath.nstr(diff, 6) if diff is not None else None),
                      bool(diff is not None and cut_or_round(diff, val))))
    scan_i = []
    for a in range(PRINTED["scan_i"][0][0], PRINTED["scan_i"][0][1] + 1, 2):
        t = (a, a, (3 * a - 1) // 2)
        e = ex(t) if t != BAI else bai
        scan_i.append((a, s_((e["mu_low"] - mu_bai) * mp(10) ** 9, 6) if e["status"] == "bound" else None))
    diffs_i = {a: d for a, d in scan_i}
    strict = all(d is not None and (a == 1857 or mpmath.mpf(d) > 0) for a, d in scan_i)
    nb = [diffs_i.get(1855), diffs_i.get(1859)]
    i_ok = bool(strict and nb[0] is not None and nb[1] is not None and
                sorted([cut_or_round(mpmath.mpf(nb[0]), PRINTED["scan_i"][1][0]) or
                        cut_or_round(mpmath.mpf(nb[0]), PRINTED["scan_i"][1][1]),
                        cut_or_round(mpmath.mpf(nb[1]), PRINTED["scan_i"][1][0]) or
                        cut_or_round(mpmath.mpf(nb[1]), PRINTED["scan_i"][1][1])]) == [True, True])
    ii = [r for r in scans["set 2"] if 1500 <= r[0][0] <= 3748 and
          Fraction(1499715, 1000000) <= Fraction(r[0][2], r[0][0]) <= Fraction(1499745, 1000000)]
    ii_b = sorted((r[2], r[0]) for r in ii if r[1] == "bound")
    ii_exact = sorted((ex(t)["mu_low"] if t != BAI else mu_bai, t) for _, t in ii_b[:3])
    ii_least = ii_exact[0][1] if ii_exact else None
    ii_next = ii_exact[1] if len(ii_exact) > 1 else None
    ii_ok = bool(len(ii) == PRINTED["scan_ii"][0] and ii_least == BAI and ii_next is not None and
                 ii_next[1] == PRINTED["scan_ii"][1] and cut_or_round((ii_next[0] - mu_bai) * mp(10) ** 9,
                                                                       PRINTED["scan_ii"][2]))
    dips = []
    for t, val in PRINTED["dips"]:
        e = ex(t)
        dips.append((t, s_(e["mu_low"], 12) if e["status"] == "bound" else None,
                     bool(e["status"] == "bound" and cut_or_round(e["mu_low"], val))))
    xt = []
    for j, yv in enumerate(PRINTED["ys"]):
        for i, xv in enumerate(PRINTED["xs"]):
            t = xy_triple(xv, yv)
            st, mu_f, _, _ = law_fast(t)
            if st == "exact":
                e = ex(t)
                st, mu_f = e["status"], (float(e["mu_low"]) if e["status"] == "bound" else None)
            want = float(PRINTED["xtable"][j][i])
            xt.append((str(xv), str(yv), t, mu_f, bool(mu_f is not None and abs(mu_f - want) <= 1e-4 + 5e-5)))
    sl = []
    for Q, val in PRINTED["slice"]:
        t = q_triple(str(Q))
        st, mu_f, _, _ = law_fast(t)
        sl.append(("below", Q, t, mu_f, bool(mu_f is not None and cut_or_round(mu_f, val))))
    for Q, val in PRINTED["above"]:
        t = above_triple(Q)
        st, mu_f, _, _ = law_fast(t)
        sl.append(("above", Q, t, mu_f, bool(mu_f is not None and cut_or_round(mu_f, val))))
    r7 = [r for r in scans["set 1"] if r[0][0] <= 10 and r[0][1] <= 10 and r[0][2] <= 22]
    n7 = len(r7)
    deg7 = sum(1 for r in r7 if r[1] == "degenerate")
    pos7 = 0
    for t, st, mu_f, nr, lp in r7:
        if st == "degenerate":
            continue
        rts, x_, y_ = roots_fast(norm(t))
        lv = lev_fast(rts, x_, y_)
        if float(np.max(lv)) > 0 and -float(np.min(lv)) > 0:
            pos7 += 1
    b7 = sorted((r[2], r[0]) for r in r7 if r[1] == "bound")
    sec7 = {"primitive": n7, "degenerate": deg7, "S,s>0": pos7, "s>Lambda": len(b7),
            "least": (s_(ex(b7[0][1])["mu_low"], 12), b7[0][1]) if b7 else None}
    sec7_ok = bool(n7 == PRINTED["sec7"][0] and deg7 == PRINTED["sec7"][1] and pos7 == PRINTED["sec7"][2] and
                   len(b7) == PRINTED["sec7"][3] and b7 and b7[0][1] == PRINTED["sec7"][5] and
                   cut_or_round(ex(b7[0][1])["mu_low"], PRINTED["sec7"][4]))
    timing["beside"] = round(time.time() - t4, 1)
    t5 = time.time()
    ver = run_verifier(verifier_src)
    timing["verifier"] = round(time.time() - t5, 1)

    def vmatch(got, mine, digits):
        return bool(got is not None and s_(mine, digits + 4).startswith(got[:digits]))
    ver_ok = {"(2,2,3)": vmatch(ver["mu223"], zz["mu_low"], 17),
              "(3,3,5) two-branch": vmatch(ver["mu335two"], t335two["mu_low"], 17),
              "(3,3,5) full": vmatch(ver["mu335full"], t335["mu_low"], 17),
              "Bai": vmatch(ver["mubai"], mu_bai, 17)}
    timing["total"] = round(time.time() - t0, 1)

    def least_line(name):
        sm = summary[name]
        c = sm["counts"]
        lst = sm["least"]
        head = f"{c['bound']} of {c['primitive']} primitive yield a bound ({c['degenerate']} degenerate)"
        if not lst:
            return head + "; none below"
        first = lst[0]
        return head + f"; least {first[0]} at {first[1]}"[:LIMIT - len(head)]
    all_near = sorted((m, t) for nm in near.values() for m, t in nm)
    ru = all_near[0] if all_near else None
    pl = [summary[n]["pair_least"] for n in ("set 2", "set 3")]
    yn = lambda v: "yes" if v else "no"
    values = {
        "mu_bai": s_(mu_bai, 25),
        "condition_1": "; ".join(f"{k}: {yn(v)}" for k, v in c1_parts.items())[:LIMIT],
        "mu_zz": s_(zz["mu_low"], 25),
        "set1": least_line("set 1"), "set2": least_line("set 2"), "set3": least_line("set 3"),
        "at_or_below": n_ref,
        "runner_up": (f"least mu other than Bai's: {s_(ru[0], 20)} at {ru[1]}, "
                      f"{mpmath.nstr((ru[0] - mu_bai) * mp(10) ** 9, 4)}e-9 above" if ru else "none"),
        "pair_least": (f"least level the pair's in {pl[0][1]} of {pl[0][0]} (set 2) and {pl[1][1]} of {pl[1][0]} "
                       f"(set 3) triples yielding a bound"),
        "calibrations": f"{sum(cal.values())} of {len(cal)} printed calibration values reproduced",
        "q_table": f"{sum(1 for r in qrows if r[3])} of {len(qrows)} as printed (mu minus Bai's, 1e-9)",
        "section8_scans": f"(i) 1857 strict minimum, neighbours as printed: {yn(i_ok)}; (ii) {len(ii)} triples "
                          f"(printed 162), least Bai's, next as printed: {yn(ii_ok)}",
        "dips": f"{sum(1 for d in dips if d[2])} of {len(dips)} as printed (nine decimals)",
        "section9_tables": (f"5x7 table {sum(1 for r in xt if r[4])} of {len(xt)} within 1.5e-4; slices "
                            f"{sum(1 for r in sl if r[4])} of {len(sl)} as printed"),
        "section7_row": (f"{n7} primitive, {deg7} degenerate, {pos7} with S, s > 0, {len(b7)} with s > Lambda, "
                         f"least {sec7['least'][0] if sec7['least'] else None} at "
                         f"{sec7['least'][1] if sec7['least'] else None}: as printed {yn(sec7_ok)}")[:LIMIT],
        "verifier": (f"the note's verifier finished: {yn(ver['finished'])}; its mu at (2,2,3), (3,3,5) two and full, "
                     f"Bai's match: {sum(ver_ok.values())} of 4; branches {ver['branches']}")[:LIMIT],
        "conditions_met": sum(cond.values()), "conditions_total": len(cond),
        "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
        if isinstance(v, float) and not math.isfinite(v):
            raise AssertionError(f"{k}: not finite")
    detail = {
        "test": TEST, "conditions": cond, "condition_1_parts": c1_parts, "controls": ctl, "timing": timing,
        "bai": {"mu": s_(mu_bai, 40), "S": s_(bai["S"], 40), "s_min": s_(bai["s_min"], 40),
                "Lambda": s_(bai["Lambda_given"], 40), "W": s_(bai["W_given"], 40), "R": bai["R"],
                "components": bai["components"], "levels": [s_(v, 30) for v in bai["levels"]],
                "minmax": {k: v for k, v in mm_bai.items() if k != "crit"}},
        "zz": {"mu": s_(zz["mu_low"], 40), "Lambda": s_(zz["Lambda_given"], 40), "W": s_(zz["W_given"], 40),
               "levels": [s_(v, 30) for v in zz["levels"]], "minmax": {k: v for k, v in mm_zz.items() if k != "crit"}},
        "sets": summary, "refuting_candidates": refuting,
        "near": {k: [(s_(m, 25), t, mpmath.nstr((m - mu_bai) * mp(10) ** 9, 6)) for m, t in v] for k, v in near.items()},
        "routes": routes, "floating_vs_exact_worst": worst,
        "calibrations": cal, "salikhov": {"two": [str(c) for c in two], "W_two": s_(t335two["W_given"], 20),
                                         "mu_two": s_(t335two["mu_low"], 20), "W_full": s_(t335["W_given"], 20),
                                         "mu_full": s_(t335["mu_low"], 20), "components": t335["components"]},
        "q_table": qrows, "scan_i": scan_i, "scan_ii": {"count": len(ii), "least": [(s_(m, 20), t) for m, t in
                                                                                    ii_exact]},
        "dips": dips, "xtable": xt, "slices": sl, "section7": sec7, "verifier": ver, "verifier_match": ver_ok,
    }
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True, ensure_ascii=True)
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
        sys.exit(f"szzb: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
