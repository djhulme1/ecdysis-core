#!/usr/bin/env python3
"""Bai's bound mu(pi) < 7.101862832357: the three rates recomputed from their definitions, and the integer linear
forms in 1 and pi built exactly for n = 1 to 6.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from Yufei Bai, "The irrationality measure of
pi is at most 7.101862832357", arXiv:2609.11276v2 (10 September 2026; the TeX dated 5 September 2026), its abstract:
"The resulting integer linear forms in $1$ and $pi$ prove [ mu(pi)<7.101862832357. ]" The paper discloses that two AI
systems assisted throughout its research and writing. It inserts two numerator exponents into Zeilberger and
Zudilin's integral (the lab's pi/zz.py, ext:80b8e1febcd7cc56) and fixes the triple (a, b, c) = (1857, 3714, 5570):
R_n(t) = 5 t^(2an) (t^4 + 6t^2 + 25)^(bn) / (25 - t^2)^(cn+1), J_n = i * integral from -1-2i to -1+2i of R_n(t) dt =
u_n + v_n pi, v_n = -c_(0,n)/2 with c_(0,n) the residue of R_n at t = -5; M_n = 2^(4-hn) L_n^(0)/Phi_n (h = 4645,
L_n^(0) = lcm(1, ..., 7430n), Phi_n the product of the primes p in (max(5, sqrt(7430n)), 7430n] with
{an/p + 1/2} + 2{bn/p} < {cn/p}) makes M_n J_n = U_n + V_n pi with U_n, V_n integers (its Proposition 2.7), and
mu(pi) <= 1 + (r + C)/(-s - C) with r the coefficients' growth, s the integral's decay and C the denominators' cost,
each per cn (its (5.17)); the paper prints 1 + sigma/tau = 7.1018628323563507957... .

The input is the paper's v2 e-print from arXiv (a gzipped tar of TeX files), checked against its SHA-256 and read as
data: its members are read from the archive in memory as text and nothing in it is run. Every rule below was fixed
before any of the quantities it tests was computed; the seed is not used, as nothing here is random. Before the rules,
the paper was read and nothing was computed from it.

1. The source. With TeX comments removed and all whitespace deleted, the e-print's TeX (main.tex, sections/*.tex and
   the appendix) must contain every string in PRINTED_TEX (the integral, R_n, P_n, M_n, V_n, S(z), P(z), F(y), the
   formulas for r, C and the bound, the printed cubic and its discriminant, |E|, and every printed constant this
   module compares with); otherwise the run is refused.
2. The rates, in mpmath at DPS digits, from their definitions, for a triple (a, b, c) with d0 = 2a + 4b - 2c,
   h = 5b - 5c/2, alpha = a/c, beta = b/c:
   r: S(z) = (1+z)^(2a) P(z)^b / (1-z)^d0, P(z) = (z^2+2z+2)(2z^2+2z+1); zeta in (0, 1) the root of
   m(x) = 2a x/(1+x) + b x P'(x)/P(x) + d0 x/(1-x) = c (bisection; m increases); r = (2(a+b-c) log 5 + (4b-2c) log 2 +
   log S(zeta) - c log zeta)/c.
   s: the numerator of F'(y), F(y) = alpha log|y| + beta log|y^2+6y+25| - log|25-y|, cleared as -c y (y^2+6y+25)(25-y)
   F'(y), is a cubic with integer coefficients (exact arithmetic); its roots by mpmath.polyroots; y_c the root with
   positive imaginary part (the cubic must have one real root and a complex pair); s = F(y_c).
   C: E = {u in [0,1): {a u + 1/2} + 2{b u} < {c u}}, found exactly: on each cell between consecutive breakpoints
   (u with a u + 1/2, b u or c u an integer) the floors are constant, so E is an initial segment of the cell ending
   where (a + 2b - c) u + 1/2 meets the cell's integer K; touching pieces are merged. omega = sum over E's components
   [l, r) of psi(r) - psi(l) (mpmath's digamma), and C = (d0 - h log 2 - omega)/c.
   sigma = r + C, tau = -s - C, B = 1 + sigma/tau.
   Condition 1: at (1857, 3714, 5570), B's decimal expansion begins 7.1018628323563507957 (the paper's printed digits)
   and B < 7.101862832357 (the abstract's bound).
3. The forms, exactly, for n = 1 to N_FORMS = 6. Since b = 2a, the numerator is h(t)^(bn), h(t) = t^5 + 6t^3 + 25t,
   and (t+5)^(cn+1) R_n(t) = G(z) = 5 H(z)^(bn) (10 - z)^(-(cn+1)) with z = t + 5 and H(z) = h(z - 5); its Taylor
   coefficients g_m are computed from the first-order equation H (10 - z) G' = (bn H' (10 - z) + (cn+1) H) G as the
   integers G~_m = g_m 10^(cn+1+m)/5 (every division asserted exact), and c_(0,n) = g_(cn). Phi_n from the primes by
   the paper's condition (in integers: ((2an + p) mod 2p) + 4 (bn mod p) < 2 (cn mod p)); L_n^(0) from the primes;
   V_n = M_n v_n = -2^(3-hn) (L_n^(0)/Phi_n) c_(0,n), as an exact fraction. pi to 11500n + 600 digits by the
   Chudnovsky series in integers (binary splitting), floor(10^D pi) with error below 1. Conditions 2 to 7, one for each
   n: V_n is a nonzero integer, the distance from V_n pi to the nearest integer is below exp(-0.8 cn tau) (bounded
   rigorously: the truncation of pi adds at most |V_n| units of 10^-D), and log|V_n| lies within 2% of cn sigma.
   (The paper's analysis predicts a distance near exp(-cn tau), about 10^(-1535n); an integer U_n with U_n + V_n pi
   that small is what its Hata lemma uses.)
   test_passed is 1 if all seven conditions hold.
4. Beside the test, none of it counted: the printed enclosures of r, s, C, omega, sigma, tau and the final bound, each
   against the computed value; the printed cubic p(y) = 3715y^3 - 232119y^2 - 928475y - 1160625 against the derived
   one, its printed discriminant, the printed N(z) of (A.1) against (1 - z^2) P(z)(m(z) - 5570), and the printed
   identity (w+1)^6 N((w-1)/(w+1)) = (4/625) p(25w^2); the printed rho, y_c, eta_* and lambda_* digits (eta_*, lambda_*
   from the paper's (4.13)); E's 2,784 components, |E| = 1724689/13797510 and its first left endpoint 1/3714, and E
   against the union of the five printed interval families; the phase F along the paper's arc gamma_eta*(lambda) =
   q lambda/(1 - i eta*(1 - lambda)), q = -3 + 4i, sampled at 20,001 points (its maximum at lambda_* equal to s, the
   arc in the upper half plane within |gamma| <= 5); |v_n| by the paper's (4.6), (25 * 2^3716)^n/4 [z^(5570n)] S(z)^n,
   computed from ((1+z)P(z))^(3714n) and (1-z)^(-7430n) for n = 1 and 2, against the residue route; Lemma 2.1's
   valuations of c_(j,1) for every j from -7429 to 5570 and Lemma 2.2's deletion (p | j, p in P_1, implies p | 10^-j
   c_(j,1); Phi_1 | c_(0,1)); the empirical rates log|V_n|/(cn) and -log dist/(cn) for n = 1 to 6; log(Phi_n)/n at
   n = 2000 by direct count of primes against omega; the auxiliary bound at Zeilberger and Zudilin's triple (1, 2, 3)
   and the improvement against the printed 0.001342501780650931772.

Controls (controls_passed of controls_total; the run stops if any fails):
 (a) pi by the Chudnovsky series against Machin's formula to 3,000 digits;
 (b) the G~ recurrence against direct series multiplication (H^k by repeated products, times the binomial series of
     (10 - z)^-(l)) for k = 3, l = 7 and k = 4, l = 9, to degree 40;
 (c) the rates' code at Zeilberger and Zudilin's triple (1, 2, 3) gives 7.103205334137001727505773..., the bound the
     lab's receipt on their paper computed (850a63a2...), to 20 digits; and its E there is exactly [1/2, 2/3);
 (d) the forms' code at that triple, for n = 40, 60, 80 and 100 (cn even, hn integral): V_n a nonzero integer
     and V_n pi within exp(-0.8 cn tau_ZZ) of an integer;
 (e) the digamma function at 1/2 and 1/3 against its closed forms;
 (f) negative controls, each caught: V_1 e (Euler's number) is not within exp(-0.8 cn tau) of an integer; and with
     the pole order raised by one (cn + 2 for cn + 1), the V_1 so built is not a good form (not an integer, or V_1 pi
     not that near an integer).

Changed after the first trial, before any output: that trial stopped at the conversion of V_1, a 9,400-digit integer,
to a decimal string (Python's 4,300-digit limit), inside the logarithm used for the growth and distance figures; the
logarithm is now math.log10 of the integer itself. No output had been written and nothing the test compares had been
seen. Changed after the second trial, whose outputs had been seen: the label of control (d) in detail.json named
n = 2, 4, 6 and 8, the values it ran before ZZ_FORMS was set to 40, 60, 80 and 100 in the rules; only the label
changed.

What it cannot check: the limits themselves (the forms only for n <= 6), the paper's contour deformation and its
Hata lemma beyond what the forms show, and its local optimality theorem (Section 6), which is not tested.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 pi/bai.py (the pinned scipy-notebook image, for mpmath).
"""

import gzip
import hashlib
import io
import json
import math
import os
import re
import sys
import tarfile
from fractions import Fraction

import mpmath

INPUT = ("arXiv-2609.11276v2.tar.gz", "82839b5cecfe72a6551b5a4bbeedda48401fc8811676cb54500af67954ba5e04", 41155)
TRIPLE = (1857, 3714, 5570)
ZZ_TRIPLE = (1, 2, 3)
N_FORMS = 6
ZZ_FORMS = (40, 60, 80, 100)
DPS = 60
DECAY_FRACTION = Fraction(8, 10)
GROWTH_BAND = 0.02
PRIME_N = 2000
ARC_POINTS = 20001
LIMIT = 200
ZZ_RECEIPT_BOUND = "7.10320533413700172750577"

TEST = ("Refuted if, at the paper's triple (a,b,c) = (1857,3714,5570), 1 + (r+C)/(−s−C), recomputed from its "
        "definitions (the real saddle of S(z) for r, the stationary cubic's upper root for s, the deleted primes' "
        "density over E by the digamma function for C), does not begin 7.1018628323563507957 or is not below "
        "7.101862832357; or, for some n from 1 to 6, V_n = M_n v_n (v_n = −c_(0,n)/2, computed exactly) is not a "
        "nonzero integer, or V_n π is not within exp(−0.8·5570nτ) of an integer, or log|V_n| is not within 2% of "
        "5570nσ.")

OUTPUTS = ("bound", "bound_vs_abstract", "rates", "omega", "forms_integer", "forms_distance", "forms_growth",
           "printed_enclosures", "cubic", "N_identity", "roots", "arc", "E_set", "E_families", "v_by_S",
           "laurent_lemma", "deletion_lemma", "omega_by_primes", "zz_bound", "improvement",
           "conditions_met", "conditions_total", "test_passed", "controls_passed", "controls_total")

PRINTED = {
    "bound_digits": "7.1018628323563507957",
    "abstract": "7.101862832357",
    "r": ("3.33194398617829933828283250382326", "3.33194398617829933828283250382327"),
    "s": ("-1.174543941310025108442583231", "-1.174543941310025108442583192"),
    "C": ("0.539993819198880114452898006", "0.539993819198880114452898061"),
    "omega": ("1202.5657733612918002543146", "1202.5657733612918002543149"),
    "sigma": ("3.87193780537717945273573050982326", "3.87193780537717945273573056482327"),
    "tau": ("0.634550122111144993989685131", "0.634550122111144993989685225"),
    "final": ("7.101862832356350795733674505", "7.101862832356350795733675497"),
    "B_ZZ": "7.1032053341370017275057734",
    "improvement": "0.001342501780650931772",
    "rho": "66.321017380598567",
    "yc": ("-1.919728071187574", "1.012573903136436"),
    "eta": ("0.9102483223156522812", "0.9102483223156522813"),
    "lambda": ("0.48021524689625610102", "0.48021524689625610103"),
    "cubic": (3715, -232119, -928475, -1160625),
    "disc": -16947864892329506560000,
    "N": (-11140, 11152, 102158, 167160, 102158, 11152, -11140),
    "w_identity": (-7428, 0, -148556, 0, -928476, 0, 371500),
    "E_measure": Fraction(1724689, 13797510),
    "E_components": 2784,
    "E_first": Fraction(1, 3714),
    "families": (186, 557, 742, 371, 928),
}

PRINTED_TEX = [
    r"\mu(\pi)<7.101862832357.",
    r"(a,b,c)=(1857,3714,5570)",
    r"R_n(t)=\frac{5t^{2an}(t^4+6t^2+25)^{bn}}{(25-t^2)^{cn+1}},",
    r"J_n=i\int_{-1-2i}^{-1+2i}R_n(t)\,dt",
    r"\left\{\frac{an}{p}+\frac12\right\}+2\left\{\frac{bn}{p}\right\}<\left\{\frac{cn}{p}\right\}",
    r"M_n=2^{4-4645n}\frac{L_n^{(0)}}{\Phi_n}=2^{4-hn}L_n.",
    r"V_n=-2^{3-hn}L_nc_{0,n}\in\mathbbZ.",
    r"S(z)=\frac{(1+z)^{3714}P(z)^{3714}}{(1-z)^{7430}}.",
    r"P(z)=(z^2+2z+2)(2z^2+2z+1)",
    r"F(y)=\alpha\log|y|+\beta\log|y^2+6y+25|-\log|25-y|.",
    r"r=\frac{\log25+3716\log2+\logS(\zeta)-5570\log\zeta}{5570}.",
    r"=\frac{7430-4645\log2-\omega}{5570}.",
    r"=1+\frac{r+\mathcalC}{-s-\mathcalC}.",
    r"p(y)=3715y^3-232119y^2-928475y-1160625.",
    r"\(-16947864892329506560000<0\)",
    r"|E|=\frac{1724689}{13797510}.",
    r"-11140+11152z+102158z^2+167160z^3",
    r"+102158z^4+11152z^5-11140z^6.",
    r"-7428-148556w^2-928476w^4+371500w^6.",
    r"1+\frac{\sigma}{\tau}=7.1018628323563507957\ldots.",
    r"B_{\rmZZ}=7.1032053341370017275057734\ldots.",
    r"=0.001342501780650931772\ldots,",
    r"\rho&=66.321017380598567\ldots,",
    r"y_c&=-1.919728071187574\ldots+1.012573903136436\ldotsi.",
] + [v for k in ("r", "s", "C", "omega", "sigma", "tau", "final") for v in PRINTED[k]]


class Refused(Exception):
    pass


# ---------------------------------------------------------------- the source (rule 1)

def read_source(path):
    blob = open(path, "rb").read()
    if len(blob) != INPUT[2] or hashlib.sha256(blob).hexdigest() != INPUT[1]:
        raise Refused("the e-print does not match its pinned size and SHA-256")
    tf = tarfile.open(fileobj=io.BytesIO(gzip.decompress(blob)))
    texts = {}
    for m in tf.getmembers():
        if m.isfile() and m.name.endswith(".tex"):
            texts[m.name] = tf.extractfile(m).read().decode("utf-8")
    order = ["main.tex"] + sorted(k for k in texts if k.startswith("sections/")) + ["appendix_exact_calculations.tex"]
    if any(k not in texts for k in order):
        raise Refused("the e-print lacks a TeX file the module reads")
    body = []
    for k in order:
        for line in texts[k].split("\n"):
            body.append(re.sub(r"(?<!\\)%.*$", "", line))
    flat = re.sub(r"\s+", "", "\n".join(body))
    missing = [s for s in PRINTED_TEX if re.sub(r"\s+", "", s) not in flat]
    if missing:
        raise Refused(f"the TeX does not print: {missing[:3]}")
    return flat


# ---------------------------------------------------------------- integer polynomials (lowest degree first)

def padd(p, q):
    n = max(len(p), len(q))
    return [(p[i] if i < len(p) else 0) + (q[i] if i < len(q) else 0) for i in range(n)]


def pmul(p, q):
    out = [0] * (len(p) + len(q) - 1)
    for i, a in enumerate(p):
        if a:
            for j, b in enumerate(q):
                out[i + j] += a * b
    return out


def pscale(p, k):
    return [k * a for a in p]


def pderiv(p):
    return [i * p[i] for i in range(1, len(p))]


def ptrim(p):
    p = list(p)
    while len(p) > 1 and p[-1] == 0:
        p.pop()
    return p


def ppow(p, k):
    out = [1]
    for _ in range(k):
        out = pmul(out, p)
    return out


def pcompose_shift(p, s):
    """p(x + s) for an integer polynomial p."""
    out = [0]
    for a in reversed(p):
        out = padd(pmul(out, [s, 1]), [a])
    return ptrim(out)


P_POLY = [2, 6, 9, 6, 2]                                    # (z^2+2z+2)(2z^2+2z+1)
H_POLY = [0, 25, 0, 6, 0, 1]                                # h(t) = t^5 + 6t^3 + 25t


def stationary_cubic(a, b, c):
    """-c * y (y^2+6y+25)(25-y) * F'(y), with F'(y) = alpha/y + beta(2y+6)/(y^2+6y+25) + 1/(25-y)."""
    f = [25, 6, 1]
    t1 = pscale(pmul(f, [25, -1]), Fraction(a, c))
    t2 = pscale(pmul(pmul([6, 2], [0, 1]), [25, -1]), Fraction(b, c))
    t3 = pmul([0, 1], f)
    total = padd(padd(t1, t2), t3)
    return ptrim([-c * x for x in total])


def cubic_discriminant(p):
    d, cc, bb, aa = p   # p = d + cc y + bb y^2 + aa y^3
    return 18 * aa * bb * cc * d - 4 * bb ** 3 * d + bb ** 2 * cc ** 2 - 4 * aa * cc ** 3 - 27 * aa ** 2 * d ** 2


# ---------------------------------------------------------------- the rates (rule 2)

def E_set(a, b, c):
    """E = {u in [0,1): {a u + 1/2} + 2{b u} < {c u}} as merged half-open intervals of Fractions."""
    pts = {Fraction(0), Fraction(1)}
    pts.update(Fraction(2 * k - 1, 2 * a) for k in range(1, a + 1))
    pts.update(Fraction(k, b) for k in range(b))
    pts.update(Fraction(k, c) for k in range(c))
    pts = sorted(p for p in pts if 0 <= p <= 1)
    d = a + 2 * b - c
    assert d > 0
    pieces = []
    for lo, hi in zip(pts, pts[1:]):
        K = math.floor(a * lo + Fraction(1, 2)) + 2 * math.floor(b * lo) - math.floor(c * lo)
        end = (K - Fraction(1, 2)) / d            # g(u) = d u + 1/2 - K < 0  iff  u < end
        if end > lo:
            pieces.append((lo, min(hi, end)))
    merged = []
    for lo, hi in pieces:
        if merged and merged[-1][1] == lo:
            merged[-1] = (merged[-1][0], hi)
        else:
            merged.append((lo, hi))
    return merged


def rates(a, b, c, dps=DPS):
    mpmath.mp.dps = dps
    mp = mpmath.mpf
    d0 = 2 * a + 4 * b - 2 * c
    h = mp(5 * b) - mp(5 * c) / 2
    P = lambda x: 2 + 6 * x + 9 * x ** 2 + 6 * x ** 3 + 2 * x ** 4
    dP = lambda x: 6 + 18 * x + 18 * x ** 2 + 8 * x ** 3
    m = lambda x: 2 * a * x / (1 + x) + b * x * dP(x) / P(x) + d0 * x / (1 - x)
    lo, hi = mp(0), mp(1)
    for _ in range(4 * dps):
        mid = (lo + hi) / 2
        if m(mid) < c:
            lo = mid
        else:
            hi = mid
    zeta = (lo + hi) / 2
    logS = 2 * a * mpmath.log(1 + zeta) + b * mpmath.log(P(zeta)) - d0 * mpmath.log(1 - zeta)
    r = (2 * (a + b - c) * mpmath.log(5) + (4 * b - 2 * c) * mpmath.log(2) + logS - c * mpmath.log(zeta)) / c
    cub = stationary_cubic(a, b, c)
    assert all(Fraction(x).denominator == 1 for x in cub)
    roots = mpmath.polyroots([mp(int(x)) for x in reversed(cub)], maxsteps=200, extraprec=2 * dps)
    complex_roots = [z for z in roots if abs(mpmath.im(z)) > mp(10) ** (-dps // 2)]
    real_roots = [mpmath.re(z) for z in roots if abs(mpmath.im(z)) <= mp(10) ** (-dps // 2)]
    assert len(complex_roots) == 2 and len(real_roots) == 1
    yc = [z for z in complex_roots if mpmath.im(z) > 0][0]
    alpha, beta = mp(a) / c, mp(b) / c
    F = lambda y: alpha * mpmath.log(abs(y)) + beta * mpmath.log(abs(y ** 2 + 6 * y + 25)) - mpmath.log(abs(25 - y))
    s = F(yc)
    E = E_set(a, b, c)
    omega = mpmath.fsum(mpmath.psi(0, mp(r_.numerator) / r_.denominator) -
                        mpmath.psi(0, mp(l_.numerator) / l_.denominator) for l_, r_ in E)
    C = (d0 - h * mpmath.log(2) - omega) / c
    sigma, tau = r + C, -s - C
    return {"zeta": zeta, "r": r, "s": s, "yc": yc, "rho": real_roots[0], "cubic": cub, "E": E, "omega": omega,
            "C": C, "sigma": sigma, "tau": tau, "B": 1 + sigma / tau, "F": F, "d0": d0, "h": h}


# ---------------------------------------------------------------- primes, lcm, deleted primes

def primes_upto(n):
    sieve = bytearray([1]) * (n + 1)
    sieve[0:2] = b"\x00\x00"
    for i in range(2, int(n ** 0.5) + 1):
        if sieve[i]:
            sieve[i * i::i] = bytearray(len(range(i * i, n + 1, i)))
    return [i for i in range(n + 1) if sieve[i]]


def lcm_upto(n, primes):
    out = 1
    for p in primes:
        if p > n:
            break
        q = p
        while q * p <= n:
            q *= p
        out *= q
    return out


def deleted(p, n, a, b, c):
    """The paper's condition {an/p + 1/2} + 2{bn/p} < {cn/p}, in integers."""
    return ((2 * a * n + p) % (2 * p)) + 4 * ((b * n) % p) < 2 * ((c * n) % p)


def Phi(n, a, b, c, primes, all_deleted=False):
    d0n = (2 * a + 4 * b - 2 * c) * n
    lo = max(5, math.isqrt(d0n))
    out, chosen = 1, []
    for p in primes:
        if p > d0n:
            break
        if p > lo and p * p > d0n and (all_deleted or deleted(p, n, a, b, c)):
            out *= p
            chosen.append(p)
    return out, chosen


# ---------------------------------------------------------------- the Laurent coefficients (rule 3)

def H_shifted():
    return pcompose_shift(H_POLY, -5)                     # H(z) = h(z - 5)


def g_tilde(k, l, mmax, keep_all=True):
    """G~_m = g_m 10^(l+m)/5 for G(z) = 5 H(z)^k (10 - z)^(-l), m = 0..mmax, by the first-order recurrence of
    H (10 - z) G' = (k H' (10 - z) + l H) G. Returns the list, or only G~_mmax (keep_all False)."""
    H = H_shifted()
    A = pmul(H, [10, -1])                                   # degree 6
    B = padd(pscale(pmul(pderiv(H), [10, -1]), k), pscale(H, l))   # degree 5
    Bs = [(i, Bi * 10 ** (i + 1)) for i, Bi in enumerate(B) if Bi]
    As = [(i, A[i] * 10 ** i) for i in range(1, len(A)) if A[i]]
    A0 = A[0]
    G = {0: H[0] ** k}
    out = [G[0]] if keep_all else None
    for m in range(0, mmax):
        acc = 0
        for i, w in Bs:
            if m - i >= 0:
                acc += w * G[m - i]
        for i, w in As:
            if m + 1 - i >= 0:
                acc -= w * (m + 1 - i) * G[m + 1 - i]
        q, rem = divmod(acc, A0 * (m + 1))
        assert rem == 0, "a division in the recurrence was not exact"
        G[m + 1] = q
        G.pop(m - 6, None)
        if keep_all:
            out.append(q)
    return out if keep_all else G[mmax]


def g_direct(k, l, mmax):
    """Control: 5 H^k (10 - z)^(-l) by direct products, scaled as in g_tilde, to degree mmax."""
    Hk = [1]
    H = H_shifted()
    for _ in range(k):
        Hk = pmul(Hk, H)[:mmax + 1]
    out = []
    for m in range(mmax + 1):
        tot = Fraction(0)
        for j in range(m + 1):
            hk = Hk[m - j] if m - j < len(Hk) else 0
            tot += Fraction(hk * math.comb(l - 1 + j, j), 10 ** (l + j))
        out.append(tot * 10 ** (l + m))                     # (5 tot) 10^(l+m)/5
    return out


def form(n, a, b, c, primes, all_deleted=False, pole_extra=0):
    assert b == 2 * a
    d0 = 2 * a + 4 * b - 2 * c
    hn = Fraction(5 * b * n) - Fraction(5 * c * n, 2)
    assert hn.denominator == 1
    hn = int(hn)
    cn = c * n
    l = cn + 1 + pole_extra
    c0 = Fraction(5 * g_tilde(b * n, l, cn, keep_all=False), 10 ** (l + cn))
    L0 = lcm_upto(d0 * n, primes)
    ph, chosen = Phi(n, a, b, c, primes, all_deleted)
    V = -Fraction(2) ** (3 - hn) * Fraction(L0, ph) * c0
    return {"V": V, "c0": c0, "Phi": ph, "deleted": chosen, "L0": L0, "hn": hn, "cn": cn}


# ---------------------------------------------------------------- pi, e and the distances

def pi_digits(D):
    """floor(10^D pi) by the Chudnovsky series with binary splitting (integers only)."""
    C3 = 640320 ** 3 // 24

    def bs(a_, b_):
        if b_ - a_ == 1:
            if a_ == 0:
                Pab = Qab = 1
            else:
                Pab = (6 * a_ - 5) * (2 * a_ - 1) * (6 * a_ - 1)
                Qab = a_ * a_ * a_ * C3
            Tab = Pab * (13591409 + 545140134 * a_)
            if a_ & 1:
                Tab = -Tab
            return Pab, Qab, Tab
        mid = (a_ + b_) // 2
        P1, Q1, T1 = bs(a_, mid)
        P2, Q2, T2 = bs(mid, b_)
        return P1 * P2, Q1 * Q2, Q2 * T1 + P1 * T2

    terms = int(D / 14.18) + 3
    _, Q, T = bs(0, terms)
    G = 10 ** 20
    sq = math.isqrt(10005 * 10 ** (2 * (D + 20)))
    return (Q * 426880 * sq) // T // G


def pi_machin(D):
    G = 10 ** 20

    def arctan_inv(x):
        unity = 10 ** (D + 20)
        total = term = unity // x
        x2, k, sign = x * x, 1, -1
        while term:
            term //= x2
            total += sign * (term // (2 * k + 1))
            sign, k = -sign, k + 1
        return total
    return (4 * (4 * arctan_inv(5) - arctan_inv(239))) // G


def e_digits(D):
    unity = 10 ** (D + 20)
    total = term = unity
    k = 1
    while term:
        term //= k
        total += term
        k += 1
    return total // 10 ** 20


def distance(V, X_D, D):
    """For an integer V and X_D = floor(10^D x): (d_int, err) with |V x - nearest integer| 10^D in
    [d_int - err, d_int + err]."""
    Y = abs(V) * X_D
    rem = Y % 10 ** D
    d_int = min(rem, 10 ** D - rem)
    return d_int, 2 * abs(V) + 2


def log10_int(x):
    """log10 of a positive integer of any size (math.log10 takes Python integers whole, with no string)."""
    if x <= 0:
        return float("-inf")
    return math.log10(x)


# ---------------------------------------------------------------- the beside checks

def S_route_v(n, a, b, c):
    """|v_n| by (4.6): (5^(2(a+b-c)) 2^(4b-2c))^n / 4 [z^(cn)] S(z)^n."""
    d0 = 2 * a + 4 * b - 2 * c
    base = pmul([1, 1], P_POLY)                              # (1+z) P(z), degree 5 (2a = b)
    N = b * n
    K = c * n
    cf = [base[0] ** N]                                      # Miller's recurrence for base^N
    for k in range(1, K + 1):
        acc = 0
        for i in range(1, min(k, 5) + 1):
            acc += ((N + 1) * i - k) * base[i] * cf[k - i]
        q, rem = divmod(acc, k * base[0])
        assert rem == 0
        cf.append(q)
    coeff, binom = 0, 1                                      # binom(d0 n - 1 + j, j)
    binoms = [1]
    for j in range(1, K + 1):
        binom = binom * (d0 * n - 1 + j) // j
        binoms.append(binom)
    for k in range(K + 1):
        coeff += cf[k] * binoms[K - k]
    return Fraction((5 ** (2 * (a + b - c)) * 2 ** (4 * b - 2 * c)) ** n, 4) * coeff


def nu(x, p):
    """p-adic valuation of a nonzero Fraction."""
    def nu_int(v):
        v, k = abs(v), 0
        step = p
        while v % step == 0:
            pw, e = step, 1
            while v % (pw * pw) == 0:
                pw, e = pw * pw, e * 2
            v //= pw
            k += e
        return k
    return nu_int(x.numerator) - nu_int(x.denominator)


def laurent_lemmas(a, b, c, primes):
    """Lemma 2.1 and Lemma 2.2 at n = 1, every j from -d0 + 1 to c."""
    # c_(j,1) = g_(cn-j) = 5 G~_(cn-j) / 10^(2cn+1-j), so 10^-j c_(j,1) = 5 G~_(cn-j) / 10^(2cn+1): every bound of
    # Lemma 2.1 is a bound on nu_2 or nu_5 of the integer G~_(cn-j), and Lemma 2.2's p | 10^-j c_(j,1) is p | G~.
    n, cn = 1, c
    d0 = 2 * a + 4 * b - 2 * c
    hn = 5 * b - 5 * c // 2
    G = g_tilde(b, cn + 1, cn + d0 - 1)
    e5 = 2 * cn + 2 * (a + b - c) * n                       # nu_5(G~) needed by both nu_5 bounds
    five = 5 ** e5
    ok21, nonzero = True, 0
    for j in range(-d0 + 1, cn + 1):
        x = G[cn - j]
        if x == 0:
            continue
        nonzero += 1
        v2 = (x & -x).bit_length() - 1
        if v2 < 2 * cn + (4 * b - 2 * c) * n:              # nu_2(10^-j c_j) >= (4b - 2c)n - 1
            ok21 = False
        if j >= 0 and v2 < 2 * cn + hn + (3 * j) // 2 - j:  # nu_2(c_j) >= hn + floor(3j/2) - 1
            ok21 = False
        if x % five:                                        # nu_5 bounds (both reduce to this)
            ok21 = False
    ph, chosen = Phi(1, a, b, c, primes)
    checks, ok22 = 0, True
    for p in chosen:
        for j in range(-((d0 - 1) // p) * p, cn + 1, p):
            if j != 0:
                checks += 1
                if G[cn - j] % p:
                    ok22 = False
    c0_ok = all(G[cn] % p == 0 for p in chosen)
    return {"lemma21": ok21, "lemma22": ok22, "lemma22_cases": checks, "Phi1_divides_c0": c0_ok,
            "deleted_primes": len(chosen), "nonzero": nonzero, "c0": Fraction(5 * G[cn], 10 ** (2 * cn + 1))}


def arc_check(R):
    U, V = mpmath.re(R["yc"]), mpmath.im(R["yc"])
    lam = (U ** 2 + V ** 2) / (-3 * U + 4 * V)
    eta = (4 * U + 3 * V) / (U ** 2 + V ** 2 + 3 * U - 4 * V)
    q = mpmath.mpc(-3, 4)
    best, best_l, upper, inside = None, None, True, True
    for k in range(1, ARC_POINTS):
        l_ = mpmath.mpf(k) / ARC_POINTS
        g = q * l_ / (1 - 1j * eta * (1 - l_))
        upper = upper and mpmath.im(g) > 0
        inside = inside and abs(g) <= 5
        val = R["F"](g)
        if best is None or val > best:
            best, best_l = val, l_
    g_star = q * lam / (1 - 1j * eta * (1 - lam))
    return {"lambda": lam, "eta": eta, "max": best, "argmax": best_l, "at_star": R["F"](g_star),
            "through_saddle": abs(g_star - R["yc"]) < mpmath.mpf(10) ** (-20), "upper": upper, "inside": inside}


def families():
    """The paper's five printed interval families (Proposition 3.1)."""
    out = []
    out += [(Fraction(j, 3714), Fraction(3 * j + 1, 2 * 5570)) for j in range(1, 372, 2)]
    out += [(Fraction(j, 3714), Fraction(3 * j, 2 * 5570)) for j in range(2, 1115, 2)]
    out += [(Fraction(j, 3714), Fraction(2 * j + 1, 2 * 3715)) for j in range(373, 1856, 2)]
    out += [(Fraction(j, 3714), Fraction(2 * j + 1, 2 * 3715)) for j in range(1116, 1857, 2)]
    out += [(Fraction(j, 3714), Fraction(3 * j - 1, 2 * 5570)) for j in range(1859, 3714, 2)]
    counts = (len(range(1, 372, 2)), len(range(2, 1115, 2)), len(range(373, 1856, 2)), len(range(1116, 1857, 2)),
              len(range(1859, 3714, 2)))
    return sorted(out), counts


def omega_by_primes(n, a, b, c):
    d0n = (2 * a + 4 * b - 2 * c) * n
    primes = primes_upto(d0n)
    lo = max(5, math.isqrt(d0n))
    tot = 0.0
    for p in primes:
        if p > lo and p * p > d0n and deleted(p, n, a, b, c):
            tot += math.log(p)
    return tot / n


def in_interval(x, lo_s, hi_s):
    with mpmath.workdps(DPS):
        return mpmath.mpf(lo_s) < x < mpmath.mpf(hi_s)


def begins(x, digits):
    """True if the decimal expansion of x (positive) begins with the printed digits."""
    s = mpmath.nstr(x, len(digits) + 15, strip_zeros=False)
    return s.startswith(digits)


# ---------------------------------------------------------------- controls

def controls_run(primes):
    ctl = {}
    ctl["pi by Chudnovsky against Machin to 3,000 digits"] = pi_digits(3000) == pi_machin(3000) or \
        abs(pi_digits(3000) - pi_machin(3000)) <= 1
    ok = True
    for k, l in ((3, 7), (4, 9)):
        G = g_tilde(k, l, 40)
        D = g_direct(k, l, 40)
        ok = ok and all(Fraction(G[m]) == D[m] for m in range(41))
    ctl["the G~ recurrence against direct series multiplication (k, l) = (3, 7), (4, 9), degree 40"] = ok
    Z = rates(*ZZ_TRIPLE)
    zz_ok = begins(Z["B"], ZZ_RECEIPT_BOUND) and Z["E"] == [(Fraction(1, 2), Fraction(2, 3))]
    ctl["the rates' code at Zeilberger-Zudilin's (1, 2, 3): their bound to 20 digits, E = [1/2, 2/3)"] = zz_ok
    ok = True
    for n in ZZ_FORMS:
        f = form(n, *ZZ_TRIPLE, primes)
        V = f["V"]
        if V.denominator != 1 or V == 0:
            ok = False
            continue
        Vi = V.numerator
        D = int(log10_int(abs(Vi))) + 3 * f["cn"] + 200
        d_int, err = distance(Vi, pi_digits(D), D)
        thresh_log10 = -float(DECAY_FRACTION) * f["cn"] * float(Z["tau"]) / math.log(10)
        ok = ok and (d_int + err) < 10 ** (D + int(math.floor(thresh_log10)))
    ctl["the forms' code at (1, 2, 3), n = 40, 60, 80, 100: V_n integral, V_n pi within exp(-0.8 cn tau) of an "
        "integer"] = ok
    mpmath.mp.dps = DPS
    g = mpmath.euler
    ok = (abs(mpmath.psi(0, mpmath.mpf(1) / 2) - (-g - 2 * mpmath.log(2))) < mpmath.mpf(10) ** -35 and
          abs(mpmath.psi(0, mpmath.mpf(1) / 3) - (-g - mpmath.pi / (2 * mpmath.sqrt(3)) - 1.5 * mpmath.log(3)))
          < mpmath.mpf(10) ** -35)
    ctl["digamma at 1/2 and 1/3 against their closed forms"] = bool(ok)
    return ctl, Z


# ---------------------------------------------------------------- the run

def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    path = os.path.join(inputs, INPUT[0])
    if not os.path.exists(path):
        raise Refused(f"missing input {INPUT[0]}")
    read_source(path)
    a, b, c = TRIPLE
    d0 = 2 * a + 4 * b - 2 * c
    primes = primes_upto(d0 * N_FORMS + 10)
    ctl, Z = controls_run(primes)
    R = rates(a, b, c)

    cond = {}
    B = R["B"]
    cond["the bound 1 + sigma/tau begins 7.1018628323563507957 and is below 7.101862832357"] = bool(
        begins(B, PRINTED["bound_digits"]) and B < mpmath.mpf(PRINTED["abstract"]))
    forms_info, c0s = [], {}
    for n in range(1, N_FORMS + 1):
        f = form(n, a, b, c, primes)
        c0s[n] = f["c0"]
        V = f["V"]
        integral = V.denominator == 1 and V != 0
        cn = f["cn"]
        info = {"n": n, "integral": integral, "deleted_primes": len(f["deleted"])}
        ok = integral
        if integral:
            Vi = V.numerator
            lv = log10_int(abs(Vi))
            D = 11500 * n + 600
            d_int, err = distance(Vi, pi_digits(D), D)
            thresh_log10 = -float(DECAY_FRACTION) * cn * float(R["tau"]) / math.log(10)
            # rigorous: d_int + err < 10^(D + thresh_log10)
            near = (d_int + err) < 10 ** (D + int(math.floor(thresh_log10)))
            growth = abs(lv * math.log(10) / (cn * float(R["sigma"])) - 1) < GROWTH_BAND
            dist_log10 = log10_int(d_int) - D
            info.update({"log10_V": lv, "log10_dist": dist_log10, "threshold_log10": thresh_log10,
                         "near": near, "growth": growth,
                         "rate_V": lv * math.log(10) / cn, "rate_dist": -dist_log10 * math.log(10) / cn})
            ok = ok and near and growth
        if n == 1:
            V1 = V.numerator if integral else None
        cond[f"n = {n}: V_n a nonzero integer, V_n pi within exp(-0.8 cn tau) of an integer, log|V_n| within 2% of "
             f"cn sigma"] = bool(ok)
        forms_info.append(info)

    # controls (f): negative
    neg_e = False
    if V1 is not None:
        D = 11500 + 600
        d_int, err = distance(V1, e_digits(D), D)
        thresh = -float(DECAY_FRACTION) * c * float(R["tau"]) / math.log(10)
        neg_e = not ((d_int + err) < 10 ** (D + int(math.floor(thresh))))
    fault = form(1, a, b, c, primes, pole_extra=1)["V"]
    neg_pole = True
    if fault.denominator == 1 and fault != 0:
        D = 11500 + 600
        d_int, err = distance(fault.numerator, pi_digits(D), D)
        thresh = -float(DECAY_FRACTION) * c * float(R["tau"]) / math.log(10)
        neg_pole = not ((d_int + err) < 10 ** (D + int(math.floor(thresh))))
    ctl["negative: V_1 e is not near an integer; the pole order raised by one gives no good form"] = bool(
        neg_e and neg_pole)
    if not all(ctl.values()):
        raise AssertionError(f"a control failed: {[k for k, v in ctl.items() if not v]}")

    # beside
    enc = {k: in_interval(R[k], *PRINTED[k]) for k in ("r", "s", "C", "omega", "sigma", "tau")}
    enc["final"] = in_interval(B, *PRINTED["final"])
    cub = R["cubic"]
    cubic_ok = tuple(int(x) for x in reversed(cub)) == PRINTED["cubic"] and all(Fraction(x).denominator == 1 for x in cub)
    disc_ok = cubic_discriminant([Fraction(x) for x in cub]) == PRINTED["disc"]
    # N(z) = (1 - z^2) P(z) (m(z) - c), cleared
    P = P_POLY
    dP = pderiv(P)
    Nz = padd(padd(padd(pscale(pmul(pmul([0, 1], [1, -1]), P), 2 * a),
                        pscale(pmul(pmul([0, 1], [1, 0, -1]), dP), b)),
                   pscale(pmul(pmul([0, 1], [1, 1]), P), d0)),
              pscale(pmul([1, 0, -1], P), -c))
    N_ok = tuple(ptrim(Nz)) == PRINTED["N"]
    # (w+1)^6 N((w-1)/(w+1)) = sum N_k (w-1)^k (w+1)^(6-k)
    lhs = [0]
    for k, Nk in enumerate(PRINTED["N"]):
        lhs = padd(lhs, pscale(pmul(ppow([-1, 1], k), ppow([1, 1], 6 - k)), Nk))
    rhs = [0] * 7
    for k, pk in enumerate(reversed(PRINTED["cubic"])):
        rhs[2 * k] += Fraction(4, 625) * pk * 25 ** k
    w_ok = [Fraction(x) for x in ptrim(lhs)] == [Fraction(x) for x in ptrim(rhs)] and \
        tuple(ptrim(lhs)) == PRINTED["w_identity"]
    mpmath.mp.dps = DPS
    roots_ok = (mpmath.nstr(R["rho"], 25).startswith(PRINTED["rho"]) and
                mpmath.nstr(mpmath.re(R["yc"]), 25).startswith(PRINTED["yc"][0]) and
                mpmath.nstr(mpmath.im(R["yc"]), 25).startswith(PRINTED["yc"][1]))
    arc = arc_check(R)
    arc_ok = (in_interval(arc["eta"], *PRINTED["eta"]) and in_interval(arc["lambda"], *PRINTED["lambda"]) and
              arc["through_saddle"] and arc["upper"] and arc["inside"] and arc["max"] <= R["s"] + mpmath.mpf(10) ** -15
              and abs(arc["argmax"] - arc["lambda"]) < mpmath.mpf(2) / ARC_POINTS)
    E = R["E"]
    E_measure = sum((r_ - l_ for l_, r_ in E), Fraction(0))
    fam, fam_counts = families()
    E_ok = (len(E) == PRINTED["E_components"] and E_measure == PRINTED["E_measure"] and E[0][0] == PRINTED["E_first"])
    fam_ok = fam == E and fam_counts == PRINTED["families"]
    vS = {n: S_route_v(n, a, b, c) == abs(c0s[n]) / 2 for n in (1, 2)}
    lem = laurent_lemmas(a, b, c, primes)
    om_primes = omega_by_primes(PRIME_N, a, b, c)
    zz_B = Z["B"]
    improvement = zz_B - B
    imp_ok = mpmath.nstr(improvement, 30).startswith(PRINTED["improvement"][:20])
    yn = lambda v: "yes" if v else "NO"

    values = {
        "bound": "1 + sigma/tau = " + mpmath.nstr(B, 28),
        "bound_vs_abstract": ("begins 7.1018628323563507957: " + yn(begins(B, PRINTED["bound_digits"])) +
                              "; below 7.101862832357: " + yn(B < mpmath.mpf(PRINTED["abstract"]))),
        "rates": ("r " + mpmath.nstr(R["r"], 22) + ", s " + mpmath.nstr(R["s"], 22) + ", C " +
                  mpmath.nstr(R["C"], 22)),
        "omega": "omega " + mpmath.nstr(R["omega"], 26) + " over " + str(len(E)) + " components of E",
        "forms_integer": "V_n a nonzero integer, n = 1..6: " + ", ".join(yn(x["integral"]) for x in forms_info),
        "forms_distance": "log10 dist(V_n pi, Z): " + ", ".join(
            f"{x.get('log10_dist', float('nan')):.0f}" for x in forms_info) + " (thresholds " + ", ".join(
            f"{x.get('threshold_log10', float('nan')):.0f}" for x in forms_info) + ")",
        "forms_growth": "log|V_n|/(cn sigma): " + ", ".join(
            f"{x.get('log10_V', 0) * math.log(10) / (TRIPLE[2] * x['n'] * float(R['sigma'])):.4f}" for x in forms_info),
        "printed_enclosures": "within the printed enclosures: " + ", ".join(f"{k} {yn(v)}" for k, v in enc.items()),
        "cubic": f"stationary cubic as printed: {yn(cubic_ok)}; discriminant as printed: {yn(disc_ok)}",
        "N_identity": f"N(z) as printed: {yn(N_ok)}; (w+1)^6 N((w-1)/(w+1)) = (4/625) p(25w^2): {yn(w_ok)}",
        "roots": f"rho and y_c digits as printed: {yn(roots_ok)}",
        "arc": (f"eta*, lambda* in the printed enclosures, arc through y_c in the upper half plane, |gamma| <= 5, "
                f"phase maximum s at lambda*: {yn(arc_ok)}"),
        "E_set": (f"E: {len(E)} components, |E| = {E_measure}, first left endpoint {E[0][0]}: {yn(E_ok)}"),
        "E_families": (f"E equals the five printed families ({', '.join(str(x) for x in fam_counts)}): {yn(fam_ok)}"),
        "v_by_S": "|v_n| by (4.6) equal to the residue route: " + ", ".join(f"n={n} {yn(v)}" for n, v in vS.items()),
        "laurent_lemma": (f"Lemma 2.1 at n = 1, j = -7429..5570: {yn(lem['lemma21'])} ({lem['nonzero']} nonzero "
                          f"coefficients)"),
        "deletion_lemma": (f"Lemma 2.2 at n = 1: {yn(lem['lemma22'])} in {lem['lemma22_cases']} cases over "
                           f"{lem['deleted_primes']} deleted primes; Phi_1 | c_(0,1): {yn(lem['Phi1_divides_c0'])}"),
        "omega_by_primes": f"log(Phi_n)/n at n = {PRIME_N}: {om_primes:.3f} (omega {float(R['omega']):.3f})",
        "zz_bound": "the same code at (1, 2, 3): " + mpmath.nstr(zz_B, 26),
        "improvement": "B_ZZ - B = " + mpmath.nstr(improvement, 22) + f" (as printed: {yn(imp_ok)})",
        "conditions_met": sum(cond.values()), "conditions_total": len(cond),
        "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"test": TEST, "conditions": cond, "controls": ctl,
              "rates": {k: mpmath.nstr(R[k], 40) for k in ("zeta", "r", "s", "rho", "omega", "C", "sigma", "tau", "B")},
              "yc": [mpmath.nstr(mpmath.re(R["yc"]), 40), mpmath.nstr(mpmath.im(R["yc"]), 40)],
              "cubic": [str(x) for x in R["cubic"]], "enclosures": enc, "forms": forms_info,
              "arc": {k: (mpmath.nstr(v, 30) if isinstance(v, (mpmath.mpf, mpmath.mpc)) else v) for k, v in arc.items()},
              "E": {"components": len(E), "measure": str(E_measure), "families": fam_counts, "equal": fam_ok},
              "v_by_S": vS, "laurent": {k: (str(v) if isinstance(v, Fraction) else v) for k, v in lem.items()
                                        if k != "c0"},
              "omega_by_primes": om_primes, "zz": {k: mpmath.nstr(Z[k], 30) for k in ("r", "s", "C", "omega", "B")},
              "improvement": mpmath.nstr(improvement, 30)}
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
        sys.exit(f"bai: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
