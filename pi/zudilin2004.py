#!/usr/bin/env python3
"""Zudilin 2004: one hypergeometric construction recovers Rhin & Viola's irrationality measures of zeta(2) and zeta(3)
and proves that at least one of zeta(5), zeta(7), zeta(9) and zeta(11) is irrational.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from Wadim Zudilin, "Arithmetic of linear forms
involving odd zeta values", J. Theorie des Nombres de Bordeaux 16 (2004) 251-291, arXiv:math/0206176 (v2, 30 November
2009, "slight modification of the abstract"), its abstract: "The construction allows to recover the records of Rhin and
Viola for the irrationality measures of $zeta(2)$ and $zeta(3)$, as well as to explain Rivoal's "infinitely-many" result
(math.NT/0008051) and to prove that at least one of the four numbers $zeta(5)$, $zeta(7)$, $zeta(9)$, and $zeta(11)$ is
irrational."

Its registered test is TEST below. The input is the v2 e-print from arXiv (one gzipped TeX file, rvbr.tex), checked
against its SHA-256 and read as data (decompressed with the standard library and read as text; nothing in it is run).
Every rule below was fixed before any quantity was computed for the paper's parameters; the TeX was read in full before
the rules, and nothing of the paper's cases was computed before the commit. One reading, of (8.7), was settled on the
tests' small case before the commit (item 3). After the first trial, under a seed of Imago's own and with nothing
sealed, one fault was mended: control (8) had computed the form's value from its coefficients at too few digits (their
rounding noise near 1e-80 against a form near 1e-108 at n = 1), and the value is now computed at rising precision until
two agree; nothing in conditions (i) to (iv) changed. The same trial found Proposition 4 giving 5.96760227530 at Theorem
2's directions (6.8) and 5.44124250745, the printed bound, at the Observation's directions, which the paper calls
G-equivalent to (6.8); so the test as registered would fail a claim the run bears out, and the check is held for the
owner (ZETA2_TEST, item 5). Nothing here is random but the points of control (3), drawn from the seed.

1. The source. With its comments removed and its whitespace collapsed, rvbr.tex must hold every formula and printed
   value in PRINTED_TEX (the parameters of Theorems 1 to 3, Hata's (5.14), the Observation's directions, the remark's
   q = 21 directions, and the printed constants); otherwise the run is refused. Theorem 3's sets Omega_1 to Omega_9 and
   Section 5's 20-element set M_0 are parsed from the TeX; a parse that does not give 9 sets and 20 collections refuses
   the run.
2. Theorem 3 (Section 8, r = 3, q = 13, eta = (91; 27, 27, 27, 29, 30, ..., 38)), from the paper's definitions, in
   mpmath at PRECISION digits and in exact rationals: tau_0 is the zero, with positive imaginary part and the largest
   real part, of the integer polynomial (tau - eta_0)^r prod_j (tau - eta_j) - tau^r prod_j (tau - eta_0 + eta_j)
   (mpmath's polyroots, every zero refined by Newton's method); f_0 as printed before Lemma 20 with principal
   logarithms (each argument then avoids its cut, since eta_j <= eta_0 - eta_1 and Re tau_0 lies between eta_0 - eta_1
   and eta_0); Lemma 20's hypotheses are Re tau_0 < eta_0 and Im f_0(tau_0) at least 1e-20 from every multiple of pi;
   C_0 = -Re f_0(tau_0). phi(x) = min over 0 <= y < 1 of phi_0(x, y) as printed, computed exactly at the midpoint of
   every interval between consecutive fractions of denominator at most 91 (every x where a floor of phi_0 jumps, or two
   of its lines in (x, y) cross, has such a denominator, so phi is constant on those intervals), the minimum over y
   read at every y where a floor changes and at the midpoint of every gap between such y. m_j = max(eta_r, eta_0 -
   2 eta_(r+1), eta_0 - eta_1 - eta_(r+j)); the integral of phi against dpsi is sum phi (psi(b) - psi(a)) over the
   intervals (psi the digamma function, mpmath's), and the integral over [0, 1/m_(q-r)) of phi dx/x^2 is exact;
   C_2 = r m_1 + m_2 + ... + m_(q-r) - (the first - the second), Proposition 5's. Condition (i): Lemma 20's
   hypotheses hold and C_0 > C_2.
3. Lemma 19 for n = 1, 2, 3 (h_0 = eta_0 n + 2, h_j = eta_j n + 1), exactly: R(t) the rational function of (8.6), the
   normalisation times R~(t) of (8.2), as a constant times h_0 + 2t times products of linear factors. (8.7) as printed
   omits (8.2)'s factor h_0 + 2t, and without it the symmetry (8.5) changes sign: on the tests' small case (r = 3, q =
   7, eta = (24; 5, 5, 5, 6, 6, 7, 7)), before any of the paper's cases was computed, (8.7) as printed gave nonzero
   zeta(4) and zeta(6) coefficients and a zero zeta(5) coefficient, and with the factor a form in 1 and zeta(5) alone,
   integral as Lemma 19 says and equal to its series. So the rules read (8.6) through (8.2), as the proof's symmetry
   argument does, and (8.7) as printed is reported beside the test (item 6). For every pole t = -k the Laurent
   coefficients B_jk as the Taylor coefficients of R(t)(t + k)^(q-r) at t = -k (truncated products of the linear factors
   in integers, the denominator inverted as a power series in rationals); A_(j-1) = C(j-2, r-1) sum_k B_jk, A_0 = sum_j
   C(j-2, r-1) sum_k B_jk H(k - h_1, j - 1), H(m, s) = sum_(l<=m) 1/l^s. Condition (ii): for each n, A_3 and the
   even-index A_4, ..., A_12 are 0, and D_(m_1)^r D_(m_2) ... D_(m_(q-r)) Phi^-1 A_i is an integer for i = 0, 5, 7, 9,
   11, with the unscaled m_j of (8.8), D_m = lcm(1, ..., m), and Phi = prod over primes sqrt(h_0) < p <= m_(q-r) of
   p^nu_p, nu_p the minimum over k of nu_(k,p) as printed (the brackets the integral part, Python's floor for negative
   arguments too).
4. Theorem 1 (Section 5, Proposition 3) at (alpha; beta) = (18, 17, 16, 19; 0, 7, 31, 32): tau_0 < tau_1 the zeros
   of prod (tau - alpha_j) - prod (tau - beta_k) (a quadratic, the alphas and betas having one sum); f_0 of Lemma 12;
   C_0 = -f_0(tau_0), C_1 = Re f_0(tau_1) (Re log the log of the modulus); M the 480 collections (sigma alpha', beta')
   for the printed M_0 and every permutation sigma of the alphas, c'_jk = |alpha'_j - beta'_k|; phi(x) = max over M of
   the printed floor sum of c minus that of c', exactly at the midpoint of every interval between fractions of
   denominator at most 32 (the largest entry); m_1, m_2, m_3 as defined before Lemma 10 (asterisks the ordering (2.9));
   C_2 = 2 m_1 + m_2 - (the integral of phi dpsi - the integral over [0, 1/m_3) of phi dx/x^2); the bound
   (C_0 + C_1)/(C_0 - C_2). Condition (iii): the bound lies in [5.51389062, 5.51389063), the printed digits followed by
   dots.
5. Theorem 2 (Section 6, Proposition 4) at (alpha; beta) = (13, 12, 14; 0, 24, 28), (6.8): c_00 = sum beta - sum alpha,
   c_jk = |alpha_j - beta_k|; the group generated by a_1 = a_13, a_2 = a_23 (rows), b = b_23 (columns) and h = (c_00
   c_22)(c_11 c_33)(c_13 c_31) on the ten entries, its orbit M of c (the maximum below over the whole orbit is the
   paper's over the 60 representatives of G/G_0, since G_0's a_23 b_23 permutes the five floors among themselves);
   phi(x) the maximum over M of the printed five-floor sum of c minus that of c', on fractions of denominator at most
   28; m_1, m_2, m_3 as printed; tau_0 < tau_1 the zeros of the quadratic; f_0 of Section 6; C_0 = -Re f_0(tau_0), C_1 =
   Re f_0(tau_1); C_2 = m_1 + m_2 - (the two integrals, the second over [0, 1/m_3)); the bound. Condition (iv): it lies
   in [5.44124250, 5.44124251). ZETA2_TEST names the directions condition (iv) reads: (6.8), as registered, or, under
   the owner's correction of the test, the Observation's (10, 11, 12; 0, 24, 25), the other set then beside. test_passed
   is 1 if all four conditions hold.
6. Beside the test, none of it counted: every printed constant of the three proofs (Theorem 3's tau_0, C_0 and C_2;
   Theorem 1's tau_0, tau_1, C_0, C_1, the integral 24.18768530, the 4, C_2, m_1 = m_3 = 16 and m_2 = 18, and phi's
   range {0, 1, 2}), each compared at its printed digits, cut or rounded; Theorem 3's sets Omega_nu = {x: phi(x) >= nu}
   against the printed ones; the group's order (120) and the number of Section 5's collections (480); Theorem 1's proof
   prints C_1 = Re f_0(tau_0) where Proposition 3 defines Re f_0(tau_1) (the value is set against both); Hata's
   7.37795637 at (8, 7, 8, 9; 0, 1, 15, 16) with M the 24 permutations of the alphas alone; the Observation's (10, 11,
   12; 0, 24, 25) for zeta(2); the remark's q = 21, eta_0 = 20, eta_j = 7 (zeta(5), ..., zeta(19)); the first eleven of
   Theorem 3's directions as a q = 11 case (zeta(5), zeta(7), zeta(9)), which the paper says no direction with eta_0 <=
   120 settles; Theorem 3 with phi taken as 0 (no arithmetic saving); Lemma 19 at n = 1 with (8.7) as printed (no factor
   h_0 + 2t), which coefficients are then nonzero; Lemma 19's tighter "fairly rough" inclusions D_(m_0)^(q-j-1) A_j; how
   many primes in Phi's range are tight (Phi p no longer divides); and log|F|/n for the forms of item 3 with F = sum A_i
   zeta(i) - A_0 (every nonzero A_i) in mpmath at rising precision until two values agree, against -C_0.
7. Controls (controls_passed counts those that behave as stated): (1) tau_0 at PRECISION and at 2 PRECISION agree to
   PRECISION - 10 digits, the polynomial vanishes there to the precision, and polyroots returns as many zeros as the
   degree; (2) psi(b) - psi(a) equals mpmath's quadrature of psi' on three intervals of Theorem 3's partition (1e-30);
   (3) the interval method's phi equals an independent evaluation in Fractions (every candidate y) at 300 points drawn
   from the seed, for Theorems 1 to 3; (4) for n = 1 the partial fractions sum back to R(t) exactly at five rational t;
   (5) a planted fault, A_0 + 1/P with P the least prime above h_0 (P divides neither the D product, nor Phi, nor any
   denominator of the form), is reported non-integral at n = 1; (6) the zeta(2) group has order 120 and Section 5's M
   has 480 distinct collections; (7) the quadratics' zeros lie where the paper says (beta_2* < tau_0 < alpha_1* and
   tau_1 > alpha_4* for zeta(3); tau_0 < beta_1 and tau_1 > alpha_3* for zeta(2)) and each quadratic vanishes at them;
   (8) for n = 1 the form's value from its coefficients, sum A_i zeta(i) - A_0, at rising precision until two values
   agree to 1e-30 relative, equals the series at that precision, (1/2) sum over t >= 0 of R''(t) (R'' = R (L'^2 + L''),
   L = log R, by mpmath's nsum; the terms from 1 - h_1 to -1 vanish, R having a zero of order r there) to 1e-20
   relative.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 pi/zudilin2004.py (the pinned scipy-notebook image, for mpmath).
"""

import gzip
import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
from fractions import Fraction

import mpmath

TEST = ("Refuted if, from the paper's definitions: for q = 13, r = 3, eta = (91; 27, 27, 27, 29, ..., 38) Lemma 20's "
        "tau0 fails its hypotheses or C0 = -Re f0(tau0) is not above C2 = 403 - (int phi dpsi - int_0^(1/33) phi "
        "dx/x^2), phi = min_y phi0; or for some n <= 3 Lemma 19 fails (a nonzero zeta(3) or even-zeta coefficient, "
        "or a coefficient times D_m1^3 D_m2...D_m10 / Phi not an integer); or Propositions 3 and 4 with its "
        "directions and orbits (its printed M0, the 120-element group for zeta(2)) put mu(zeta(3)) outside "
        "[5.51389062, 5.51389063) or mu(zeta(2)) outside [5.44124250, 5.44124251).")

EPRINT = ("arXiv-math-0206176v2.gz", "edea79549afee63c8f8ef901eb9339826013a9fece9be216c35801eca2a6b35f", 30761)
PRECISION = 60
N_MAX = 3
CONTROL_POINTS = 300

# Theorem 3 and the cases beside it: (r, eta_0, (eta_1, ..., eta_q))
T3 = (3, 91, (27, 27, 27) + tuple(25 + j for j in range(4, 14)))
Q21 = (3, 20, (7,) * 21)
Q11 = (3, 91, (27, 27, 27) + tuple(25 + j for j in range(4, 12)))
# Theorem 1, Hata, Theorem 2 and the Observation: (alpha, beta)
T1 = ((18, 17, 16, 19), (0, 7, 31, 32))
HATA = ((8, 7, 8, 9), (0, 1, 15, 16))
T2 = ((13, 12, 14), (0, 24, 28))
OBS = ((10, 11, 12), (0, 24, 25))
# Condition (iv)'s directions: (6.8), as registered. The first trial found Proposition 4 giving 5.96760227530 at (6.8)
# and 5.44124250745 at the Observation's (10, 11, 12; 0, 24, 25), which the paper calls G-equivalent to (6.8), so the
# check is held for the owner: under his correction of the test, ZETA2_TEST becomes OBS and TEST the corrected text.
ZETA2_TEST = T2
BOUNDS = {"t1": (Fraction(551389062, 10 ** 8), Fraction(551389063, 10 ** 8)),
          "t2": (Fraction(544124250, 10 ** 8), Fraction(544124251, 10 ** 8))}

PRINTED_TEX = (
    r"\eta_0=91, \qquad \eta_1=\eta_2=\eta_3=27, \qquad \eta_j=25+j \quad\mbox{for}\; j=4,5,\dots,13,",
    r"we obtain $\tau_0=87.47900541\hdots+i\,3.32820690\dots$,",
    r"C_0&=-\Re f_0(\tau_0)=227.58019641\dots,",
    r"C_2&=3\cdot35+34+8\cdot33",
    r"&=226.24944266\dots",
    r"and $\Omega_{10}=\emptyset$.",
    r"C_2=rm_1+m_2+\dots+m_{q-r} -\biggl(\int_0^1\phi(x)\,\d\psi(x) "
    r"-\int_0^{1/m_{q-r}}\phi(x)\,\frac{\d x}{x^2}\biggr).",
    r"\mu(\zeta(3))\le5.51389062\dots\,.",
    r"\alpha_1&=18, \quad& \alpha_2&=17, \quad& \alpha_3&=16, \quad& \alpha_4&=19, \\ \beta_1&=0, \quad& "
    r"\beta_2&=7, \quad& \beta_3&=31, \quad& \beta_4&=32.",
    r"\tau_0&=8.44961969\dots, \qquad& C_0&=-f_0(\tau_0)=47.15472079\dots,",
    r"\tau_1&=27.38620119\dots, \qquad& C_1&=\Re f_0(\tau_0)=48.46940964\dots\,.",
    r"an easy verification shows that $m_1=m_3=16$ and $m_2=18$.",
    r"&=2\cdot16+18-(24.18768530\hdots-4) =29.81231469\dots,",
    r"\mu(\zeta(3))\le7.37795637\dots",
    r"\alpha_1&=8, \quad& \alpha_2&=7, \quad& \alpha_3&=8, \quad& \alpha_4&=9, \\ \beta_1&=0, \quad& "
    r"\beta_2&=1, \quad& \beta_3&=15, \quad& \beta_4&=16,",
    r"\mu(\zeta(2))\le5.44124250\dots\,.",
    r"\alpha_1&=13, \quad& \alpha_2&=12, \quad& \alpha_3&=14, \\ \beta_1&=0, \quad& \beta_2&=24, \quad& "
    r"\beta_3&=28",
    r"\alpha_1&=10, \quad& \alpha_2&=11, \quad& \alpha_3&=12, \\ \beta_1&=0, \quad& \beta_2&=24, \quad& "
    r"\beta_3&=25",
    r"namely, we take $r=3$, $q=21$, $\eta_0=20$, and $\eta_1=\dots=\eta_{21}=7$ to achieve this result.",
    r"\fh=(c_{00} \; c_{22})(c_{11} \; c_{33})(c_{13} \; c_{31});",
    r"has order~$120$;",
    r"of $480$~such collections",
)

OUTPUTS = ("t3_tau0_re", "t3_tau0_im", "t3_c0", "t3_c2", "t3_margin", "t3_hypotheses", "t3_ipsi", "t3_i2",
           "t3_omega", "l19", "l19_passed", "l19_tight", "l19_forms", "l19_printed", "t1_mu", "t1_c0", "t1_c1",
           "t1_c2", "t1_ipsi", "t1_i2", "t1_tau", "t1_m", "t1_phi_range", "t2_mu", "t2_c0", "t2_c1", "t2_c2",
           "t2_ipsi", "t2_i2", "t2_m", "t2_group", "t2_obs_mu", "hata_mu", "q21", "q11", "t3_no_phi", "printed",
           "printed_matched", "printed_total", "conditions_met", "conditions_total", "test_passed", "controls_passed",
           "controls_total")
LIMIT = 200


class Refused(Exception):
    pass


# ---------------------------------------------------------------- the source

def read_input(inputs, spec):
    name, sha, size = spec
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha or len(data) != size:
        raise Refused(f"{name}: sha256 {got} ({len(data)} bytes), not the registered {sha} ({size})")
    return data


def flatten(tex):
    """Comments removed (an unescaped % to the end of its line) and whitespace collapsed to single spaces."""
    lines = [re.sub(r"(?<!\\)%.*$", "", ln) for ln in tex.split("\n")]
    return re.sub(r"\s+", " ", " ".join(lines))


FRAC = r"(?:\\tfrac(\{\d+\}|\d)(\{\d+\}|\d)|(0|1))"


def _num(tok):
    return int(tok.strip("{}"))


def _endpoint(groups):
    num, den, plain = groups
    if plain is not None:
        return Fraction(int(plain))
    return Fraction(_num(num), _num(den))


def parse_omegas(flat):
    """Theorem 3's printed sets: {nu: [(a, b), ...]} for nu = 1..9, each a union of intervals [a, b)."""
    i = flat.index(r"where $\Omega_0=[0,1)$,")
    j = flat.index(r"and $\Omega_{10}=\emptyset$.", i)
    block = flat[i:j]
    starts = list(re.finditer(r"\\Omega_(\d+) &=", block))
    out = {}
    for s, nxt in zip(starts, starts[1:] + [None]):
        nu = int(s.group(1))
        body = block[s.end(): nxt.start() if nxt else len(block)]
        also = re.match(r"\s*\\Omega_(\d+) =", body)
        ivals = []
        for m in re.finditer(r"\\bigl\[" + FRAC + r"," + FRAC + r"\\bigr\)", body):
            g = m.groups()
            ivals.append((_endpoint(g[0:3]), _endpoint(g[3:6])))
        out[nu] = ivals
        if also:
            out[int(also.group(1))] = list(ivals)
    if sorted(out) != list(range(1, 10)) or any(not v for v in out.values()):
        raise Refused(f"Theorem 3's sets parsed as {sorted(out)}")
    return out


def parse_m0(flat):
    """Section 5's 20 collections (alpha'; beta') of M_0, as printed."""
    i = flat.index(r"The set $\sM_0$ in this case consists of the following elements:")
    j = flat.index("an easy verification shows", i)
    out = []
    for body in re.findall(r"\\begin\{array\}\{rrrr\}(.*?)\\end\{array\}", flat[i:j]):
        rows = body.split(r"\\")
        if len(rows) != 2:
            raise Refused(f"M_0 entry {body!r}")
        a, b = (tuple(int(v) for v in re.findall(r"\d+", row)) for row in rows)
        if len(a) != 4 or len(b) != 4:
            raise Refused(f"M_0 entry {body!r}")
        out.append((a, b))
    if len(out) != 20:
        raise Refused(f"M_0 parsed with {len(out)} collections")
    return out


def read_source(inputs):
    data = read_input(inputs, EPRINT)
    tex = gzip.decompress(data).decode("latin-1")
    flat = flatten(tex)
    missing = [s for s in PRINTED_TEX if flatten(s) not in flat]
    if missing:
        raise Refused(f"the e-print does not hold {len(missing)} of the formulas the check uses, the first "
                      f"{missing[0]!r}")
    return flat, parse_omegas(flat), parse_m0(flat)


# ---------------------------------------------------------------- exact helpers

def farey(nmax):
    """Every fraction in [0, 1] with denominator at most nmax, sorted."""
    pts = {Fraction(k, d) for d in range(1, nmax + 1) for k in range(0, d + 1)}
    return sorted(pts)


def primes_upto(m):
    sieve = bytearray([1]) * (m + 1)
    sieve[0:2] = b"\x00\x00"
    for i in range(2, int(m ** 0.5) + 1):
        if sieve[i]:
            sieve[i * i::i] = bytearray(len(sieve[i * i::i]))
    return [i for i in range(m + 1) if sieve[i]]


def lcm_upto(m):
    out = 1
    for p in primes_upto(m):
        q = p
        while q * p <= m:
            q *= p
        out *= q
    return out


def poly_mul(a, b):
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b):
                out[i + j] += x * y
    return out


def poly_of_roots(roots):
    """prod (t - r), coefficients lowest degree first."""
    out = [1]
    for r in roots:
        out = poly_mul(out, [-r, 1])
    return out


def poly_sub(a, b):
    n = max(len(a), len(b))
    a = a + [0] * (n - len(a))
    b = b + [0] * (n - len(b))
    out = [x - y for x, y in zip(a, b)]
    while out and out[-1] == 0:
        out.pop()
    return out


# ---------------------------------------------------------------- Theorem 3's analytic constant

def t3_polynomial(r, eta0, eta):
    first = poly_mul(poly_of_roots([eta0] * r), poly_of_roots(list(eta)))
    second = poly_mul(poly_of_roots([0] * r), poly_of_roots([eta0 - e for e in eta]))
    return poly_sub(first, second)


def poly_eval(coeffs, x):
    acc = mpmath.mpf(0) if not isinstance(x, mpmath.mpc) else mpmath.mpc(0)
    for c in reversed(coeffs):
        acc = acc * x + c
    return acc


def poly_deriv(coeffs):
    return [i * c for i, c in enumerate(coeffs)][1:]


def refine(coeffs, z, steps=80):
    d = poly_deriv(coeffs)
    for _ in range(steps):
        fz = poly_eval(coeffs, z)
        dz = poly_eval(d, z)
        if dz == 0:
            break
        step = fz / dz
        z = z - step
        if abs(step) < mpmath.mpf(10) ** (-mpmath.mp.dps + 5) * max(1, abs(z)):
            break
    return z


def roots_of(coeffs, dps):
    with mpmath.workdps(dps):
        rs = mpmath.polyroots(list(reversed(coeffs)), maxsteps=400, extraprec=4 * dps)
        rs = [refine(coeffs, mpmath.mpc(z)) for z in rs]
        return rs


def f0_t3(r, eta0, eta, tau):
    q = len(eta)
    s = r * eta0 * mpmath.log(eta0 - tau)
    for e in eta:
        s += e * mpmath.log(tau - e) - (eta0 - e) * mpmath.log(tau - eta0 + e)
    s -= 2 * sum(e * mpmath.log(e) for e in eta[:r])
    s += sum((eta0 - 2 * e) * mpmath.log(eta0 - 2 * e) for e in eta[r:q])
    return s


def t3_analytic(r, eta0, eta, dps=PRECISION):
    coeffs = t3_polynomial(r, eta0, eta)
    with mpmath.workdps(dps):
        rs = roots_of(coeffs, dps)
        upper = [z for z in rs if z.imag > mpmath.mpf(10) ** (-dps // 2)]
        tau0 = max(upper, key=lambda z: z.real)
        f = f0_t3(r, eta0, eta, tau0)
        im = f.imag
        dist = abs(im - mpmath.pi * mpmath.nint(im / mpmath.pi))
        hyp = bool(tau0.real < eta0 and dist > mpmath.mpf("1e-20"))
        scale = sum(abs(c) * abs(tau0) ** i for i, c in enumerate(coeffs))
        resid = abs(poly_eval(coeffs, tau0)) / scale
        return {"coeffs_degree": len(coeffs) - 1, "roots": len(rs), "tau0": tau0, "c0": -f.real, "im_f0": im,
                "pi_distance": dist, "hypotheses": hyp, "residual": resid}


# ---------------------------------------------------------------- Theorem 3's arithmetic constant

def t3_coeffs(r, eta0, eta):
    """The x coefficients of phi_0's floors: for each term (sign, cx, cy) meaning sign * floor(cx x + cy y)."""
    q = len(eta)
    terms = []
    for e in eta[:r]:
        terms += [(1, 0, 1), (1, eta0, -1), (-1, -e, 1), (-1, eta0 - e, -1), (-2, e, 0)]
    for e in eta[r:q]:
        terms += [(1, eta0 - 2 * e, 0), (-1, -e, 1), (-1, eta0 - e, -1)]
    return terms


def phi0_int(terms, P, Q, Y):
    """phi_0 at x = P/Q and y = Y/(2Q), exactly (integers)."""
    s = 0
    for sign, cx, cy in terms:
        s += sign * ((2 * cx * P + cy * Y) // (2 * Q))
    return s


def phi_min_at(terms, P, Q):
    """min over 0 <= y < 1 of phi_0(P/Q, y): at every y where a floor changes and at the midpoints between them."""
    cuts = {0}
    for _, cx, cy in terms:
        if cy:
            cuts.add(2 * ((cx * P * -cy) % Q))  # y with cx x + cy y an integer: y = frac(-cy cx x) for cy = +-1
    ys = sorted(cuts)
    cand = list(ys)
    for a, b in zip(ys, ys[1:] + [2 * Q]):
        cand.append((a + b) // 2)
    return min(phi0_int(terms, P, Q, Y) for Y in cand)


def phi_min_exact(terms, x):
    """The same minimum in Fractions with every candidate y, for control (3)."""
    cuts = {Fraction(0)}
    for _, cx, cy in terms:
        if cy:
            v = -cy * cx * x
            cuts.add(v - math.floor(v))
    ys = sorted(cuts)
    cand = list(ys) + [(a + b) / 2 for a, b in zip(ys, ys[1:] + [Fraction(1)])]

    def val(y):
        return sum(sign * math.floor(cx * x + cy * y) for sign, cx, cy in terms)
    return min(val(y) for y in cand)


def step_function(points, value_at_mid):
    """[(a, b, value)] over consecutive points, the value at each interval's midpoint."""
    out = []
    for a, b in zip(points, points[1:]):
        out.append((a, b, value_at_mid(a, b)))
    return out


def merge_steps(steps):
    out = []
    for a, b, v in steps:
        if out and out[-1][2] == v and out[-1][1] == a:
            out[-1] = (out[-1][0], b, v)
        else:
            out.append((a, b, v))
    return out


def integrals(steps, cut, dps=PRECISION):
    """(int_0^1 phi dpsi, int_0^cut phi dx/x^2): the first in mpmath, the second exact."""
    i2 = Fraction(0)
    with mpmath.workdps(dps + 10):
        ipsi = mpmath.mpf(0)
        cache = {}

        def psi(x):
            if x not in cache:
                cache[x] = mpmath.digamma(mpmath.mpf(x.numerator) / x.denominator)
            return cache[x]
        for a, b, v in steps:
            if v == 0:
                continue
            if a == 0:
                raise Refused("phi is not zero next to 0, so the integral against dpsi diverges")
            ipsi += v * (psi(b) - psi(a))
            lo, hi = a, min(b, cut)
            if lo < hi:
                i2 += v * (1 / lo - 1 / hi)
    return ipsi, i2


def t3_m(r, eta0, eta):
    q = len(eta)
    return [max(eta[r - 1], eta0 - 2 * eta[r], eta0 - eta[0] - eta[r + j - 1]) for j in range(1, q - r + 1)]


def t3_arithmetic(r, eta0, eta):
    terms = t3_coeffs(r, eta0, eta)
    dens = set()
    xs = sorted({abs(cx) for _, cx, _ in terms} | {0})
    for a in xs:
        for b in xs:
            if a != b:
                dens.add(abs(a - b))
    dmax = max(dens)
    pts = farey(dmax)

    def mid(a, b):
        P = a.numerator * b.denominator + b.numerator * a.denominator
        Q = 2 * a.denominator * b.denominator
        return phi_min_at(terms, P, Q)
    steps = merge_steps(step_function(pts, mid))
    m = t3_m(r, eta0, eta)
    ipsi, i2 = integrals(steps, Fraction(1, m[-1]))
    c2 = r * m[0] + sum(m[1:]) - (ipsi - i2)
    return {"terms": terms, "steps": steps, "m": m, "ipsi": ipsi, "i2": i2, "c2": c2, "dmax": dmax,
            "phi_max": max(v for _, _, v in steps), "dsum": r * m[0] + sum(m[1:])}


def omegas_of(steps, top):
    """{nu: merged [(a, b)] where phi >= nu}."""
    out = {}
    for nu in range(1, top + 1):
        iv = []
        for a, b, v in steps:
            if v >= nu:
                if iv and iv[-1][1] == a:
                    iv[-1] = (iv[-1][0], b)
                else:
                    iv.append((a, b))
        out[nu] = iv
    return out


def merged(ivals):
    out = []
    for a, b in sorted(ivals):
        if out and out[-1][1] == a:
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return out


# ---------------------------------------------------------------- Lemma 19's linear forms

def lemma19_parts(r, eta0, eta, n, well_poised=True):
    """h, the constant, the shifts of N(t) and D(t) (R = const (h_0 + 2t) N/D, each factor t + s), and the poles.

    well_poised=False drops the factor h_0 + 2t, which (8.7) as printed does (beside the test only, item 6)."""
    h0 = eta0 * n + 2
    h = [e * n + 1 for e in eta]
    q = len(h)
    const = Fraction(1)
    for hj in h[:r]:
        const /= math.factorial(hj - 1) ** 2
    for hj in h[r:]:
        const *= math.factorial(h0 - 2 * hj)
    num = []
    for hj in h[:r]:
        num += list(range(1, hj))                    # Gamma(h_j + t)/Gamma(1 + t)
        num += list(range(h0 - hj + 1, h0))          # Gamma(h_0 + t)/Gamma(1 + h_0 - h_j + t)
    den = []
    for hj in h[r:]:
        den += list(range(hj, h0 - hj + 1))          # Gamma(h_j + t)/Gamma(1 + h_0 - h_j + t)
    poles = list(range(h[r], h0 - h[r] + 1))
    return {"h0": h0, "h": h, "q": q, "const": const, "num": num, "den": den, "poles": poles, "wp": well_poised}


def series_trunc_product(shifts, k, deg):
    """prod (u + s - k) over the shifts, as integer coefficients up to u^deg."""
    out = [1] + [0] * deg
    for s in shifts:
        c = s - k
        nxt = [0] * (deg + 1)
        for i in range(deg + 1):
            if out[i]:
                nxt[i] += out[i] * c
                if i + 1 <= deg:
                    nxt[i + 1] += out[i]
        out = nxt
    return out


def series_inverse(coeffs, deg):
    inv = [Fraction(0)] * (deg + 1)
    inv[0] = Fraction(1, coeffs[0])
    for m in range(1, deg + 1):
        acc = Fraction(0)
        for i in range(1, m + 1):
            if i < len(coeffs) and coeffs[i]:
                acc += coeffs[i] * inv[m - i]
        inv[m] = -acc / coeffs[0]
    return inv


def laurent_b(parts, r):
    """B[(j, k)] for j = r+1..q and every pole k: the coefficient of 1/(t + k)^(j - r)."""
    q = parts["q"]
    order = q - r
    deg = order - 1
    out = {}
    for k in parts["poles"]:
        o = parts["den"].count(k)
        others = [s for s in parts["den"] if s != k]
        nk = series_trunc_product(parts["num"], k, deg)
        if parts["wp"]:                      # h_0 + 2t = (h_0 - 2k) + 2u at t = u - k
            nk = [(parts["h0"] - 2 * k) * nk[i] + (2 * nk[i - 1] if i else 0) for i in range(deg + 1)]
        dk = series_trunc_product(others, k, deg)
        inv = series_inverse(dk, deg)
        g = [Fraction(0)] * (deg + 1)       # N/D' to degree deg
        for i in range(deg + 1):
            if nk[i]:
                for jj in range(deg + 1 - i):
                    g[i + jj] += nk[i] * inv[jj]
        shift = order - o                    # G_k(u) = const u^(order - o) N/D'
        full = [Fraction(0)] * (deg + 1)
        for i in range(deg + 1):
            if i + shift <= deg:
                full[i + shift] = g[i] * parts["const"]
        for j in range(r + 1, q + 1):
            out[(j, k)] = full[q - j]
    return out


_HARMONIC = {}


def harmonic(m, s):
    """H(m, s) = sum_(l <= m) 1/l^s, from a cumulative table per s."""
    table = _HARMONIC.setdefault(s, [Fraction(0)])
    while len(table) <= m:
        table.append(table[-1] + Fraction(1, len(table) ** s))
    return table[m]


def lemma19_coefficients(parts, r, B):
    q = parts["q"]
    h1 = parts["h"][0]
    A = {}
    for j in range(r + 1, q + 1):
        A[j - 1] = math.comb(j - 2, r - 1) * sum((B[(j, k)] for k in parts["poles"]), Fraction(0))
    a0 = Fraction(0)
    for j in range(r + 1, q + 1):
        cj = math.comb(j - 2, r - 1)
        for k in parts["poles"]:
            if B[(j, k)]:
                a0 += cj * B[(j, k)] * harmonic(k - h1, j - 1)
    A[0] = a0
    return A


def lemma19_arith(parts, r):
    """Lemma 19's denominators: the unscaled m_j, the D product, Phi and its nu_p."""
    h0, h = parts["h0"], parts["h"]
    q = parts["q"]
    m0 = max(h[r - 1] - 1, h0 - 2 * h[r])
    m = [max(m0, h0 - h[0] - h[r + j - 1]) for j in range(1, q - r + 1)]
    dprod = lcm_upto(m[0]) ** r
    for mj in m[1:]:
        dprod *= lcm_upto(mj)
    nus = {}
    phi = 1
    for p in primes_upto(m[-1]):
        if p * p <= h0:
            continue
        best = None
        for k in range(h[r], h0 - h[r] + 1):
            v = 0
            for hj in h[:r]:
                v += ((k - 1) // p + (h0 - k - 1) // p - (k - hj) // p - (h0 - hj - k) // p - 2 * ((hj - 1) // p))
            for hj in h[r:]:
                v += ((h0 - 2 * hj) // p - (k - hj) // p - (h0 - hj - k) // p)
            best = v if best is None else min(best, v)
        nus[p] = best
        phi *= p ** best
    return {"m0": m0, "m": m, "dprod": dprod, "phi": phi, "nu": nus}


def r_at(parts, t):
    """R(t) exactly at a rational t (control (4))."""
    v = parts["const"] * (parts["h0"] + 2 * t if parts["wp"] else 1)
    for s in parts["num"]:
        v *= (t + s)
    for s in parts["den"]:
        v /= (t + s)
    return v


def series_value(parts, r, dps=PRECISION):
    """(1/(r-1)!) sum_(t >= 1-h_1) R^(r-1)(t) for r = 3, from t = 0 (R vanishes to order r at -1, ..., 1 - h_1)."""
    if r != 3:
        raise ValueError("the series is implemented for r = 3")
    if any(parts["num"].count(i) < r for i in range(1, parts["h"][0])):
        raise ValueError("R does not vanish to order r where the sum begins")
    with mpmath.workdps(dps):
        const = mpmath.mpf(parts["const"].numerator) / parts["const"].denominator
        num, den, h0, wp = parts["num"], parts["den"], parts["h0"], parts["wp"]

        def term(t):
            t = mpmath.mpf(t)
            rv = const
            l1 = mpmath.mpf(0)
            l2 = mpmath.mpf(0)
            if wp:
                rv *= h0 + 2 * t
                l1 += 2 / (h0 + 2 * t)
                l2 -= 4 / (h0 + 2 * t) ** 2
            for s in num:
                rv *= t + s
                l1 += 1 / (t + s)
                l2 -= 1 / (t + s) ** 2
            for s in den:
                rv /= t + s
                l1 -= 1 / (t + s)
                l2 += 1 / (t + s) ** 2
            return rv * (l1 * l1 + l2) / 2
        return mpmath.nsum(term, [0, mpmath.inf])


def lemma19(r, eta0, eta, n, want_value=True, well_poised=True):
    parts = lemma19_parts(r, eta0, eta, n, well_poised)
    B = laurent_b(parts, r)
    A = lemma19_coefficients(parts, r, B)
    ar = lemma19_arith(parts, r)
    q = parts["q"]
    zero_needed = [r] + list(range(r + 1, q, 2))
    zeros_ok = all(A[i] == 0 for i in zero_needed)
    sym_ok = all(B[(j, k)] == (-1) ** j * B[(j, parts["h0"] - k)] for (j, k) in B if (j, parts["h0"] - k) in B)
    kept = [0] + list(range(r + 2, q - 1, 2))
    integral = {i: (ar["dprod"] * A[i] / ar["phi"]).denominator == 1 for i in kept}
    rough = {j: (lcm_upto(ar["m0"]) ** (q - j - 1) * A[j]).denominator == 1 for j in range(r + 2, q - 1, 2)}
    tight = []
    for p in ar["nu"]:
        if not all((ar["dprod"] * A[i] / (ar["phi"] * p)).denominator == 1 for i in kept):
            tight.append(p)
    out = {"n": n, "zeros_ok": zeros_ok, "symmetric": sym_ok, "integral": integral, "rough": rough,
           "tight": tight, "m": ar["m"], "nu": ar["nu"], "parts": parts, "B": B, "A": A, "kept": kept,
           "phi": ar["phi"], "dprod": ar["dprod"]}
    out["nonzero"] = sorted(i for i in A if i and A[i] != 0)
    if want_value:
        big = max(abs(A[i]) for i in A if A[i] != 0)
        start = max(int(math.log10(big.numerator + 1) - math.log10(big.denominator)), 0)
        F, digits = form_value(A, start)
        out["digits"] = max(digits, PRECISION)
        out["F"] = F
        with mpmath.workdps(out["digits"]):
            out["log_abs_F_over_n"] = mpmath.log(abs(F)) / n
    return out


def form_value(A, start):
    """sum A_i zeta(i) - A_0 over every nonzero A_i, kept or not, at rising precision (start + 80, + 160, + 320, ...
    digits) until two successive values agree to 1e-30 relative; (the value, the digits it settled at)."""
    prev, margin = None, 80
    while margin <= 40960:
        dps = start + margin
        with mpmath.workdps(dps):
            F = -mpmath.mpf(A[0].numerator) / A[0].denominator
            for i in sorted(A):
                if i and A[i] != 0:
                    F += mpmath.mpf(A[i].numerator) / A[i].denominator * mpmath.zeta(i)
            if prev is not None and F != 0 and abs(F - prev) <= abs(F) * mpmath.mpf(10) ** -30:
                return F, dps
            prev = F
        margin *= 2
    raise Refused("the form's value did not settle")


def least_prime_above(m):
    p = m + 1
    while any(p % d == 0 for d in range(2, math.isqrt(p) + 1)):
        p += 1
    return p


def planted_fault_caught(x):
    """Control (5): A_0 + 1/P, P the least prime above h_0, must fail the integrality check; (caught, P)."""
    p = least_prime_above(x["parts"]["h0"])
    return bool((x["dprod"] * (x["A"][0] + Fraction(1, p)) / x["phi"]).denominator != 1), p


# ---------------------------------------------------------------- Theorems 1 and 2

def cmat(alpha, beta):
    return [[abs(a - b) for b in beta] for a in alpha]


ZETA3_FLOORS = ((2, 1), (3, 1), (4, 1), (1, 2), (3, 2), (4, 2), (3, 3), (4, 4))


def floor_sum3(c, P, Q):
    return sum((c[j - 1][k - 1] * P) // Q for j, k in ZETA3_FLOORS)


def zeta3_orbit(m0):
    coll = set()
    for a, b in m0:
        for perm in itertools.permutations(a):
            coll.add((perm, b))
    return sorted(coll)


def zeta3_m(alpha, beta):
    bs = sorted(beta)
    b1s, b2s, b3s, b4s = bs
    a1s = min(alpha)
    a1, a2, a3, a4 = alpha
    be1, be2, be3, be4 = beta
    m1 = b4s - a1s
    m2 = max(a1 - be1, a2 - be2, b4s - a3, b4s - a4, b3s - a1s)
    return m1, m2, min(m1, m2)


def quadratic_roots(alpha, beta, dps=PRECISION):
    coeffs = poly_sub(poly_of_roots(list(alpha)), poly_of_roots(list(beta)))
    if len(coeffs) != 3:
        raise Refused(f"the polynomial for {alpha}, {beta} has degree {len(coeffs) - 1}, not 2")
    c, b, a = coeffs
    with mpmath.workdps(dps):
        disc = mpmath.mpf(b * b - 4 * a * c)
        if disc <= 0:
            raise Refused("the quadratic has no real zeros")
        s = mpmath.sqrt(disc)
        t0, t1 = sorted([(-b - s) / (2 * a), (-b + s) / (2 * a)])
        resid = max(abs(a * t * t + b * t + c) for t in (t0, t1))
    return t0, t1, coeffs, resid


def relog(x):
    return mpmath.log(abs(x))


def f0_zeta3_re(alpha, beta, tau):
    a1, a2, a3, a4 = alpha
    b1, b2, b3, b4 = beta
    s = sum(a * relog(a - tau) for a in alpha)
    s -= b1 * relog(tau - b1) + b2 * relog(tau - b2) + b3 * relog(b3 - tau) + b4 * relog(b4 - tau)
    s -= (a1 - b1) * relog(a1 - b1) + (a2 - b2) * relog(a2 - b2)
    s += (b3 - a3) * relog(b3 - a3) + (b4 - a4) * relog(b4 - a4)
    return s


def f0_zeta2_re(alpha, beta, tau):
    a1, a2, a3 = alpha
    b1, b2, b3 = beta
    s = a1 * relog(a1 - tau) + a2 * relog(a2 - tau) + a3 * relog(a3 - tau)
    s -= (b1 * relog(tau - b1) if b1 else 0) + b2 * relog(b2 - tau) + b3 * relog(b3 - tau)
    s += -(a1 - b1) * relog(a1 - b1) + (b2 - a2) * relog(b2 - a2) + (b3 - a3) * relog(b3 - a3)
    return s


def zeta3_case(alpha, beta, collections):
    c = cmat(alpha, beta)
    cs = [cmat(a, b) for a, b in collections]
    dmax = max(max(max(row) for row in cc) for cc in cs + [c])
    pts = farey(dmax)

    def mid(a, b):
        P = a.numerator * b.denominator + b.numerator * a.denominator
        Q = 2 * a.denominator * b.denominator
        base = floor_sum3(c, P, Q)
        return max(base - floor_sum3(cc, P, Q) for cc in cs)
    steps = merge_steps(step_function(pts, mid))
    m1, m2, m3 = zeta3_m(alpha, beta)
    ipsi, i2 = integrals(steps, Fraction(1, m3))
    t0, t1, quad, resid = quadratic_roots(alpha, beta)
    with mpmath.workdps(PRECISION):
        c0 = -f0_zeta3_re(alpha, beta, t0)
        c1 = f0_zeta3_re(alpha, beta, t1)
        c1_at_t0 = f0_zeta3_re(alpha, beta, t0)
        c2 = 2 * m1 + m2 - (ipsi - i2)
        mu = (c0 + c1) / (c0 - c2)
    bs, as_ = sorted(beta), sorted(alpha)
    where = bool(bs[1] < t0 < as_[0] and t1 > as_[3])
    return {"steps": steps, "m": (m1, m2, m3), "ipsi": ipsi, "i2": i2, "tau0": t0, "tau1": t1, "c0": c0, "c1": c1,
            "c1_at_tau0": c1_at_t0, "c2": c2, "mu": mu, "range": sorted({v for _, _, v in steps}),
            "where": where, "resid": resid, "orbit": len(collections), "dmax": dmax}


ZETA2_POS = ["c00"] + [f"c{j}{k}" for j in (1, 2, 3) for k in (1, 2, 3)]


def zeta2_generators():
    idx = {name: i for i, name in enumerate(ZETA2_POS)}

    def perm(*cycles):
        p = list(range(10))
        for x, y in cycles:
            p[idx[x]], p[idx[y]] = idx[y], idx[x]
        return tuple(p)
    a1 = perm(("c11", "c31"), ("c12", "c32"), ("c13", "c33"))
    a2 = perm(("c21", "c31"), ("c22", "c32"), ("c23", "c33"))
    b = perm(("c12", "c13"), ("c22", "c23"), ("c32", "c33"))
    h = perm(("c00", "c22"), ("c11", "c33"), ("c13", "c31"))
    return [a1, a2, b, h]


def group_closure(gens):
    ident = tuple(range(len(gens[0])))
    seen = {ident}
    frontier = [ident]
    while frontier:
        nxt = []
        for g in frontier:
            for s in gens:
                comp = tuple(g[s[i]] for i in range(len(s)))
                if comp not in seen:
                    seen.add(comp)
                    nxt.append(comp)
        frontier = nxt
    return seen


ZETA2_FLOORS = ("c00", "c21", "c31", "c22", "c33")


def zeta2_vector(alpha, beta):
    c = [sum(beta) - sum(alpha)]
    for a in alpha:
        for b in beta:
            c.append(abs(a - b))
    return tuple(c)


def zeta2_case(alpha, beta):
    c = zeta2_vector(alpha, beta)
    group = group_closure(zeta2_generators())
    orbit = sorted({tuple(c[g[i]] for i in range(10)) for g in group})
    sel = [ZETA2_POS.index(nm) for nm in ZETA2_FLOORS]
    dmax = max(c)
    pts = farey(dmax)

    def fsum(v, P, Q):
        return sum((v[i] * P) // Q for i in sel)

    def mid(a, b):
        P = a.numerator * b.denominator + b.numerator * a.denominator
        Q = 2 * a.denominator * b.denominator
        base = fsum(c, P, Q)
        return max(base - fsum(v, P, Q) for v in orbit)
    steps = merge_steps(step_function(pts, mid))
    as_ = sorted(alpha)
    bs = sorted(beta[1:])
    m1 = bs[1] - as_[0]
    m2 = max(alpha[0] - beta[0], bs[1] - alpha[1], bs[1] - alpha[2], bs[0] - as_[0])
    m3 = min(m1, m2)
    ipsi, i2 = integrals(steps, Fraction(1, m3))
    t0, t1, quad, resid = quadratic_roots(alpha, beta)
    with mpmath.workdps(PRECISION):
        c0 = -f0_zeta2_re(alpha, beta, t0)
        c1 = f0_zeta2_re(alpha, beta, t1)
        c2 = m1 + m2 - (ipsi - i2)
        mu = (c0 + c1) / (c0 - c2)
    where = bool(t0 < beta[0] and t1 > as_[2])
    return {"steps": steps, "m": (m1, m2, m3), "ipsi": ipsi, "i2": i2, "tau0": t0, "tau1": t1, "c0": c0, "c1": c1,
            "c2": c2, "mu": mu, "range": sorted({v for _, _, v in steps}), "group": len(group), "orbit": len(orbit),
            "where": where, "resid": resid, "vector": c}


# ---------------------------------------------------------------- comparisons and formatting

def digits_as(x, printed):
    """A printed decimal (followed by dots) against a value: 'cut', 'rounded' or None."""
    places = len(printed.split(".")[1])
    with mpmath.workdps(PRECISION):
        v = mpmath.mpf(x) if not isinstance(x, Fraction) else mpmath.mpf(x.numerator) / x.denominator
        scaled = v * mpmath.mpf(10) ** places
        cut = mpmath.floor(scaled) if v >= 0 else mpmath.ceil(scaled)
        rnd = mpmath.nint(scaled)
        p = mpmath.mpf(printed) * mpmath.mpf(10) ** places
        if abs(cut - p) < mpmath.mpf("0.5"):
            return "cut"
        if abs(rnd - p) < mpmath.mpf("0.5"):
            return "rounded"
    return None


def in_bounds(x, lo, hi):
    with mpmath.workdps(PRECISION):
        lo_m = mpmath.mpf(lo.numerator) / lo.denominator
        hi_m = mpmath.mpf(hi.numerator) / hi.denominator
        return bool(lo_m <= x < hi_m)


def num(x, places=12):
    return float(mpmath.nstr(x, places + 6, strip_zeros=False)) if not isinstance(x, (int, Fraction)) else float(x)


def s8(x, places=8):
    return mpmath.nstr(x, places + 4)


def fit_list(head, items, limit=LIMIT):
    s = head
    for k, it in enumerate(items):
        piece = ("" if k == 0 else "; ") + it
        if len(s) + len(piece) > limit - 6:
            return s + "; ..."
        s += piece
    return s


# ---------------------------------------------------------------- the run

def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    mpmath.mp.dps = PRECISION
    flat, omegas_printed, m0 = read_source(inputs)

    # Theorem 3
    r3, e0, eta = T3
    an = t3_analytic(r3, e0, eta)
    an2 = t3_analytic(r3, e0, eta, dps=2 * PRECISION)
    ar = t3_arithmetic(r3, e0, eta)
    margin = an["c0"] - ar["c2"]
    om = omegas_of(ar["steps"], 9)
    om_match = sum(1 for nu in range(1, 10) if om[nu] == merged(omegas_printed[nu]))

    # Lemma 19
    l19 = [lemma19(r3, e0, eta, n) for n in range(1, N_MAX + 1)]
    l19_ok = all(x["zeros_ok"] and all(x["integral"].values()) for x in l19)
    l19_printed = lemma19(r3, e0, eta, 1, want_value=False, well_poised=False)

    # Theorems 1 and 2, and beside
    t1 = zeta3_case(T1[0], T1[1], zeta3_orbit(m0))
    hata = zeta3_case(HATA[0], HATA[1], sorted({(perm, HATA[1]) for perm in itertools.permutations(HATA[0])}))
    t2 = zeta2_case(*T2)
    obs = zeta2_case(*OBS)
    z2 = t2 if ZETA2_TEST == T2 else obs
    q21 = (t3_analytic(*Q21), t3_arithmetic(*Q21))
    q11 = (t3_analytic(*Q11), t3_arithmetic(*Q11))

    cond = {
        "(i) Theorem 3: Lemma 20's hypotheses hold and C0 > C2": bool(an["hypotheses"] and margin > 0),
        "(ii) Lemma 19 for n = 1, 2, 3": bool(l19_ok),
        "(iii) Theorem 1's bound in [5.51389062, 5.51389063)": in_bounds(t1["mu"], *BOUNDS["t1"]),
        ("(iv) Theorem 2's bound in [5.44124250, 5.44124251)" if ZETA2_TEST == T2 else
         "(iv) the Observation's zeta(2) bound in [5.44124250, 5.44124251)"): in_bounds(z2["mu"], *BOUNDS["t2"]),
    }

    # beside: printed values
    printed_rows = [
        ("Theorem 3 Re tau0", an["tau0"].real, "87.47900541"), ("Theorem 3 Im tau0", an["tau0"].imag, "3.32820690"),
        ("Theorem 3 C0", an["c0"], "227.58019641"), ("Theorem 3 C2", ar["c2"], "226.24944266"),
        ("Theorem 1 tau0", t1["tau0"], "8.44961969"), ("Theorem 1 tau1", t1["tau1"], "27.38620119"),
        ("Theorem 1 C0", t1["c0"], "47.15472079"), ("Theorem 1 C1 (= Re f0(tau1))", t1["c1"], "48.46940964"),
        ("Theorem 1 int phi dpsi", t1["ipsi"], "24.18768530"), ("Theorem 1 C2", t1["c2"], "29.81231469"),
        ("Theorem 1 bound", t1["mu"], "5.51389062"), ("Theorem 2 bound", t2["mu"], "5.44124250"),
        ("Hata's bound", hata["mu"], "7.37795637"), ("Observation's zeta(2) bound", obs["mu"], "5.44124250"),
    ]
    rows = []
    for label, val, pr in printed_rows:
        rows.append({"label": label, "printed": pr, "ours": mpmath.nstr(val, 20), "as": digits_as(val, pr)})
    exact_rows = [
        ("Theorem 3 D sum 3*35+34+8*33", ar["dsum"] == 3 * 35 + 34 + 8 * 33),
        ("Theorem 1 int over [0, 1/16) of phi dx/x^2 = 4", t1["i2"] == 4),
        ("Theorem 1 m1 = m3 = 16, m2 = 18", t1["m"] == (16, 18, 16)),
        ("Theorem 1 phi in {0, 1, 2}", set(t1["range"]) <= {0, 1, 2} and 2 in t1["range"]),
        ("Theorem 3 Omega sets", om_match == 9),
        ("zeta(2) group order 120", t2["group"] == 120),
        ("Section 5's M has 480 collections", t1["orbit"] == 480),
    ]
    for label, ok in exact_rows:
        rows.append({"label": label, "printed": "as printed", "ours": str(ok), "as": "exact" if ok else None})
    misses = [r_["label"] for r_ in rows if r_["as"] is None]
    matched = sum(1 for r_ in rows if r_["as"] is not None)

    # controls
    ctl, ctl_detail = {}, {}
    agree = abs(an["tau0"] - an2["tau0"])
    ctl["(1) tau0 at two precisions, the polynomial's zero, as many zeros as the degree"] = bool(
        agree < mpmath.mpf(10) ** (-(PRECISION - 10)) and an["residual"] < mpmath.mpf(10) ** (-(PRECISION - 15))
        and an["roots"] == an["coeffs_degree"])
    ctl_detail["tau0_agreement"] = mpmath.nstr(agree, 5)
    gaps = []
    with mpmath.workdps(PRECISION):
        nonzero = [s_ for s_ in ar["steps"] if s_[2] > 0]
        for a, b, _ in (nonzero[0], nonzero[len(nonzero) // 2], nonzero[-1]):
            qd = mpmath.quad(lambda x: mpmath.psi(1, x), [mpmath.mpf(a.numerator) / a.denominator,
                                                         mpmath.mpf(b.numerator) / b.denominator])
            dd = mpmath.digamma(mpmath.mpf(b.numerator) / b.denominator) - mpmath.digamma(
                mpmath.mpf(a.numerator) / a.denominator)
            gaps.append(abs(qd - dd))
    ctl["(2) psi(b) - psi(a) equals the quadrature of psi'"] = bool(max(gaps) < mpmath.mpf("1e-30"))
    ctl_detail["psi_gaps"] = [mpmath.nstr(g, 5) for g in gaps]
    rng = random.Random(int(seed, 16))
    bad = 0
    terms = ar["terms"]
    c1m = cmat(*T1)
    cs1 = [cmat(a, b) for a, b in zeta3_orbit(m0)]
    v2 = t2["vector"]
    grp = group_closure(zeta2_generators())
    orb2 = sorted({tuple(v2[g[i]] for i in range(10)) for g in grp})
    sel2 = [ZETA2_POS.index(nm) for nm in ZETA2_FLOORS]

    def step_at(steps, x):
        for a, b, v in steps:
            if a < x < b:
                return v
        return None
    for _ in range(CONTROL_POINTS):
        x = Fraction(rng.randrange(1, 10 ** 9), 10 ** 9)
        v = step_at(ar["steps"], x)
        if v is not None and v != phi_min_exact(terms, x):
            bad += 1
        v = step_at(t1["steps"], x)
        if v is not None:
            base = sum(math.floor(c1m[j - 1][k - 1] * x) for j, k in ZETA3_FLOORS)
            w = max(base - sum(math.floor(cc[j - 1][k - 1] * x) for j, k in ZETA3_FLOORS) for cc in cs1)
            bad += v != w
        v = step_at(t2["steps"], x)
        if v is not None:
            base = sum(math.floor(v2[i] * x) for i in sel2)
            w = max(base - sum(math.floor(o[i] * x) for i in sel2) for o in orb2)
            bad += v != w
    ctl["(3) the interval method's phi equals the direct evaluation at points from the seed"] = bad == 0
    ctl_detail["phi_mismatches"] = bad
    p1 = l19[0]["parts"]
    B1 = l19[0]["B"]
    pf_ok = True
    for t in (Fraction(1, 3), Fraction(7, 2), Fraction(-1, 2), Fraction(100, 7), Fraction(-201, 2)):
        tot = sum((B1[(j, k)] / (t + k) ** (j - r3) for (j, k) in B1), Fraction(0))
        pf_ok = pf_ok and tot == r_at(p1, t)
    ctl["(4) the partial fractions sum back to R(t) at five rational t (n = 1)"] = pf_ok
    x1 = l19[0]
    caught, big_p = planted_fault_caught(x1)
    ctl["(5) a planted fault, A_0 + 1/P (P the least prime above h_0), is caught at n = 1"] = caught
    ctl_detail["planted_prime"] = big_p
    ctl["(6) the zeta(2) group has order 120 and Section 5's M 480 collections"] = bool(
        t2["group"] == 120 and t1["orbit"] == 480)
    ctl["(7) the quadratics' zeros lie where the paper says and solve them"] = bool(
        t1["where"] and t2["where"] and t1["resid"] < mpmath.mpf("1e-40") and t2["resid"] < mpmath.mpf("1e-40"))
    with mpmath.workdps(x1["digits"]):
        fs = series_value(p1, r3, dps=x1["digits"])
        rel = abs(fs - x1["F"]) / abs(fs)
    ctl["(8) the form's value from its coefficients equals the series (n = 1)"] = bool(rel < mpmath.mpf("1e-20"))
    ctl_detail["series_vs_coefficients"] = {"series": mpmath.nstr(fs, 30), "coefficients": mpmath.nstr(l19[0]["F"], 30),
                                            "relative_difference": mpmath.nstr(rel, 5)}

    def l19_str():
        parts = []
        for x in l19:
            sym = "ok" if x["symmetric"] else "NO"
            parts.append(f"n {x['n']}: zeros {'ok' if x['zeros_ok'] else 'NO'}, integral "
                         f"{sum(x['integral'].values())}/{len(x['integral'])}, symmetric {sym}")
        return "; ".join(parts)

    values = {
        "t3_tau0_re": num(an["tau0"].real), "t3_tau0_im": num(an["tau0"].imag), "t3_c0": num(an["c0"]),
        "t3_c2": num(ar["c2"]), "t3_margin": num(margin), "t3_hypotheses": int(an["hypotheses"]),
        "t3_ipsi": num(ar["ipsi"]), "t3_i2": num(ar["i2"]),
        "t3_omega": f"{om_match} of 9 sets as printed; phi at most {ar['phi_max']}",
        "l19": l19_str(), "l19_passed": int(l19_ok),
        "l19_tight": fit_list("tight primes: ", [f"n {x['n']}: {','.join(map(str, x['tight'])) or 'none'}"
                                                 for x in l19]),
        "l19_forms": fit_list("log|F|/n: ", [f"n {x['n']} {mpmath.nstr(x['log_abs_F_over_n'], 8)}" for x in l19]),
        "l19_printed": (f"(8.7) as printed, without h0 + 2t, n 1: nonzero zeta(i) coefficients at i = "
                        f"{', '.join(map(str, l19_printed['nonzero'])) or 'none'}; the test's zeros "
                        f"{'hold' if l19_printed['zeros_ok'] else 'fail'}"),
        "t1_mu": num(t1["mu"]), "t1_c0": num(t1["c0"]), "t1_c1": num(t1["c1"]), "t1_c2": num(t1["c2"]),
        "t1_ipsi": num(t1["ipsi"]), "t1_i2": num(t1["i2"]),
        "t1_tau": f"tau0 {s8(t1['tau0'])}, tau1 {s8(t1['tau1'])}; Re f0(tau0) {s8(t1['c1_at_tau0'])}",
        "t1_m": f"m1 {t1['m'][0]}, m2 {t1['m'][1]}, m3 {t1['m'][2]}",
        "t1_phi_range": ",".join(map(str, t1["range"])),
        "t2_mu": num(t2["mu"]), "t2_c0": num(t2["c0"]), "t2_c1": num(t2["c1"]), "t2_c2": num(t2["c2"]),
        "t2_ipsi": num(t2["ipsi"]), "t2_i2": num(t2["i2"]),
        "t2_m": f"m1 {t2['m'][0]}, m2 {t2['m'][1]}, m3 {t2['m'][2]}; phi in {','.join(map(str, t2['range']))}",
        "t2_group": t2["group"], "t2_obs_mu": num(obs["mu"]), "hata_mu": num(hata["mu"]),
        "q21": (f"C0 {s8(q21[0]['c0'])}, C2 {s8(q21[1]['c2'])}, C0 > C2 {bool(q21[0]['c0'] > q21[1]['c2'])}, "
                f"hypotheses {q21[0]['hypotheses']}"),
        "q11": (f"C0 {s8(q11[0]['c0'])}, C2 {s8(q11[1]['c2'])}, C0 > C2 {bool(q11[0]['c0'] > q11[1]['c2'])}, "
                f"hypotheses {q11[0]['hypotheses']}"),
        "t3_no_phi": f"C2 {ar['dsum']} without Phi, C0 > C2 {bool(an['c0'] > ar['dsum'])}",
        "printed": fit_list("unmatched: ", misses) if misses else "all as printed",
        "printed_matched": matched, "printed_total": len(rows),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for key, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")
        if isinstance(v, float) and not math.isfinite(v):
            raise AssertionError(f"{key}: not finite")
    detail = {
        "input": list(EPRINT), "conditions": cond, "controls": ctl, "control_detail": ctl_detail,
        "printed": rows,
        "t3": {"tau0": mpmath.nstr(an["tau0"], 40), "c0": mpmath.nstr(an["c0"], 40), "c2": mpmath.nstr(ar["c2"], 40),
               "ipsi": mpmath.nstr(ar["ipsi"], 40), "i2": str(ar["i2"]), "m": ar["m"],
               "im_f0": mpmath.nstr(an["im_f0"], 30), "pi_distance": mpmath.nstr(an["pi_distance"], 10),
               "degree": an["coeffs_degree"], "steps": [[str(a), str(b), v] for a, b, v in ar["steps"]],
               "omegas_computed": {nu: [[str(a), str(b)] for a, b in iv] for nu, iv in om.items()},
               "omegas_printed": {nu: [[str(a), str(b)] for a, b in merged(iv)] for nu, iv in omegas_printed.items()}},
        "lemma19": [{"n": x["n"], "zeros_ok": x["zeros_ok"], "symmetric": x["symmetric"],
                     "integral": {str(k): v for k, v in x["integral"].items()},
                     "rough": {str(k): v for k, v in x["rough"].items()}, "tight": x["tight"], "m": x["m"],
                     "nu": {str(p): v for p, v in x["nu"].items()},
                     "A_digits": {str(i): (len(str(abs(x["A"][i].numerator))) - len(str(x["A"][i].denominator)))
                                  for i in x["kept"]},
                     "log_abs_F_over_n": mpmath.nstr(x["log_abs_F_over_n"], 15)} for x in l19],
        "lemma19_as_printed": {"n": 1, "nonzero": l19_printed["nonzero"], "zeros_ok": l19_printed["zeros_ok"],
                               "symmetric": l19_printed["symmetric"],
                               "integral": {str(k): v for k, v in l19_printed["integral"].items()}},
        "t1": {k: (mpmath.nstr(v, 30) if isinstance(v, (mpmath.mpf, mpmath.mpc)) else v)
               for k, v in t1.items() if k not in ("steps",)},
        "t2": {k: (mpmath.nstr(v, 30) if isinstance(v, (mpmath.mpf, mpmath.mpc)) else v)
               for k, v in t2.items() if k not in ("steps",)},
        "hata": {"mu": mpmath.nstr(hata["mu"], 30), "m": hata["m"], "range": hata["range"]},
        "obs": {"mu": mpmath.nstr(obs["mu"], 30), "m": obs["m"]},
        "q21": {"c0": mpmath.nstr(q21[0]["c0"], 30), "c2": mpmath.nstr(q21[1]["c2"], 30), "m": q21[1]["m"]},
        "q11": {"c0": mpmath.nstr(q11[0]["c0"], 30), "c2": mpmath.nstr(q11[1]["c2"], 30), "m": q11[1]["m"]},
    }
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
        sys.exit(f"zudilin2004: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
