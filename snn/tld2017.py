#!/usr/bin/env python3
"""Tang, Lin & Davies's spiking LCA: do the network's spike rates approach the solution of the sparse coding problem
it is configured for?

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from Ping Tak Peter Tang, Tsung-Han Lin and
Mike Davies (Intel), "Sparse Coding by Spiking Neural Networks: Convergence Theory and Computational Results",
arXiv:1705.05475v1 (15 May 2017; the arXiv non-exclusive distribution licence), its abstract: "With a moderate but
well-defined assumption, we prove that the SNN indeed solves sparse coding." The paper's Section 3 and Appendices A
to C prove that the spike rates of the spiking LCA (S-LCA, Shapero, Rozell & Hasler's network) configured for a
non-negative LASSO (CLASSO) problem converge to its solution, assuming that a neuron that spikes infinitely often
does so with bounded inter-spike intervals. It is the theory behind Loihi's LASSO results (Davies et al., IEEE Micro
2018, ext:16709f63148f9fdd: "By properly configuring the network, it can be established that as the network dynamics
evolve, the average spike rates of the neurons will converge to a fixed point, and this fixed point is identical to
the solution of the optimization problem.", citing this paper and reusing its Figure 1). No finite computation
reaches a limit; this module simulates the network exactly, event by event, over 10,000 of its time constants and
asks whether its rates approach the CLASSO solution, certified exactly, as the theorem says they must.

The input is the paper's e-print (v1), checked against its size and SHA-256. From its TeX the run reads the strings in
PRINTED (the network, its configuration, the example, its printed solution, the assumption, the 400-neuron setting),
and refuses if one is missing; the 3-neuron example of Section 4.1 (s, Phi and lambda) is parsed from practice.tex as
exact decimals. From its Figure 1 (figures/dynamics-raster.pdf and figures/dynamics-spike-count.pdf, inside the
e-print) the run reads the authors' own simulation: the raster's spike times and the dashed A-LCA curves, from the
figures' vector drawings against their tick marks. Every rule below was fixed before the network was simulated on
the paper's example or on any instance drawn under a registered seed; the tests exercise the machinery on other
inputs, and a timing pilot simulated one instance drawn from a test seed, computing nothing the test compares.

The network (Section 3; Appendix A with tau = 1, as the main text sets alpha(t) = e^(-t)). Neuron i has a soma current
mu_i(t) = b_i - sum_(j != i) w_ij (alpha * sigma_j)(t), alpha(t) = e^(-t) for t >= 0, and a potential that
integrates mu_i - lambda from 0 (v_i(0) = 0, so mu_i(0) = b_i), spikes when it reaches nu_f = 1 and is reset to
nu_r = 0; the configuration is b_i = phi_i^T s, w_ij = phi_i^T phi_j (j != i), the bias lambda the CLASSO lambda
(Section 3, "set nu_f <- 1, nu_r <- 0"). The spike rate is a_i(t) = N_i(t)/t (Eq. 3 with t_0 = 0, the readout the
proof covers). Between events every current and potential has a closed form,
    mu_i(t + x) = b_i + d_i e^(-x),   v_i(t + x) = v_i(t) + (b_i - lambda) x + d_i (1 - e^(-x)),   d_i = mu_i(t) - b_i,
so the next spike time of each neuron is the first root of a convex function (d_i <= 0: inhibition only), found by
Newton's method from the right; the earliest is the next event, at which the spiking neuron's potential is reset and
every other neuron's current drops by its weight. Neurons with b_i <= lambda can never spike (their potentials never
rise) and have a*_i = 0 (a positive coefficient needs b_i = lambda + (G a*)_i > lambda), so only the others are
simulated. Double precision; the root-finding and the closed forms are checked against a 50-digit simulation (mpmath)
and a fine fixed-step one.

The CLASSO solution (Eq. 1: argmin over a >= 0 of 1/2 ||s - Phi a||^2 + lambda ||a||_1) is certified exactly: for a
support S, a_S solves G_SS a_S = b_S - lambda in rationals, every a_S > 0, G_SS is positive definite (positive pivots)
and lambda - (b_j - G_jS a_S) > 0 for every j outside S; these make a* the unique solution (Phi a is unique by strict
convexity of the fit, every solution lives on {j : gradient zero} = S by complementary slackness, and Phi_S has full
column rank). For the example the 8 supports are enumerated, under two readings of its printed atoms, whose norms
are 1 only to four decimals: R1, Phi as printed (G = Phi^T Phi, as a solver such as the paper's LARS takes it); R2,
the problem the configured network solves, whose reset stands for a unit diagonal (G = Phi^T Phi off the diagonal,
1 on it). The test uses R2; R1 is the printed solution's reading. For a drawn instance the support comes from the
homotopy below and the certificate is computed in rationals from the double-precision atoms and signal.

The instances (Section 4.2: "a 400-atom dictionary learned from other image datasets"; "The input has 128 dimensions
by splitting the image into positive and negative channels"; "With the chosen lambda, the optimal solution has 8
non-zeros entries"; the dictionary and the patch are not released): for k = 0..19, drawn from the seed
(numpy's PCG64 from SeedSequence(seed, spawn_key = (1, k, r)), r counting redraws), 400 atoms g ~ N(0, I_64), each
split into channels [max(g, 0); max(-g, 0)] and scaled to unit norm (math.fsum, so the norm is exactly rounded), a
signal x ~ N(0, I_64) split the same way, and lambda the midpoint of the first interval of the CLASSO path (followed
down from lambda_max = max b by the non-negative homotopy: a coefficient leaves when it reaches 0, an atom joins when
its correlation reaches lambda) on which the support has exactly 8 atoms. An instance is redrawn if the path finds no
such interval above lambda_max/100 within 400 events, or the exact certificate fails at the chosen lambda; redraws
are counted. The network's weights and inputs are the exact Gram entries and correlations of the double-precision
atoms, each rounded once.

The test (TEST). E(t1, t2) = max_i max over t in [t1, t2] of |a_i(t) - a*_i|, computed exactly: between a neuron's
own spikes a_i(t) = N_i/t is monotone, so its largest deviation is at the window's ends or at its own spikes, each
taken on both sides. Refuted if, on the example (R2's a*) or on any of the 20 instances,
  1. E(5000, 10000) > 0.01 max_i a*_i  (the rates are not within 1% of the solution's scale late in the run), or
  2. E(5000, 10000) > 0.5 E(500, 1000)  (the deviation does not shrink as the run lengthens).
Conditions: (1) and (2) on the example, (1) on every instance, (2) on every instance.

Beside the test, none of it counted: the example run on to t = 100,000, its rates there against the printed
[0.684, 0, 1.217] (the first and third cut or rounded to three decimals, the second rounding to 0.000), and
E(50000, 100000); neuron 2's spikes ("a weak neuron, such as Neuron 2, is
quickly rendered inactive"); the assumption, as the runs bear it out: whether the neurons spiking in the last window
are exactly the support of a*, the longest inter-spike interval there times a*_i, and the last spike of a neuron
outside the support; Theorem 2's relation, |T_lambda(u_i(t)) - a_i(t)| at t = 10,000 with u_i the average current,
times t; the A-LCA (Theorem 1, the paper's summary of its earlier result) integrated by RK4 (h = 0.01) to t = 50 from
u(0) = 0 on every instance, |T(u(50)) - a*| over max a*; Figure 1(d)'s dashed curves, int_0^t T(u_i) of the A-LCA,
against RK4 (h = 1e-4) from u(0) = 0 and from u(0) = b (the text gives no initial state), at t = 1, 2, 4, ..., 12, and
the S-LCA's counts there (Eq. 7's approximation); and the discrete-time implementation of Section 4 (exact
integration over each step of size h, a spike at the end of the step in which the potential reaches 1, reset to 0,
inhibition at the step's end) for h = 1e-2 and 1e-3 on the example and the first four instances, its readout
(N(1000) - N(500))/500 (a positive t_0, as the section suggests), the relative objective gap (E(a) - E*)/E* and the
digits lost from 1e-3 to 1e-2 (log10 of the ratio of gaps; the paper: "increasing the step size from 10^-3 to 10^-2
sacrifices two digits of accuracy in the computed E*"), with the exact network's gap under the same readout.

Controls (each could fail on the claim's own case or its machinery):
  (a) the printed example: under each reading exactly one support of the 8 passes the certificate, and R3's solution
      (below) is the printed [0.684, 0, 1.217], each decimal cut or rounded (half up) to its printed digits and the 0
      exact, R3's atoms rounding to the printed ones; R1's and R2's comparisons are reported beside;
  (b) Figure 1(c): the exact network's spikes on [0, 12] are as many per neuron as the raster's markers (8, 1, 14 when
      read) and each lies within 0.1 of its marker (the authors' step size is not stated);
  (c) the double-precision simulation of the example on [0, 12] gives the same spike sequence as a 50-digit one
      (mpmath), its times within 1e-9;
  (d) the fixed-step simulation at h = 1e-5 gives the same spike sequence on [0, 12], its times within 2e-3;
  (e) an independent solver (scipy's L-BFGS-B with bounds, on the double-precision problem) agrees with every
      certified solution within 1e-6;
  (f) a planted fault, the example's inhibition halved, fails condition 1, so the test can fail;
  (g) at the end of every run int_0^t (mu_i - lambda) = N_i(t) + v_i(t) within 1e-9 (relative to t);
  (h) every potential is within 1e-12 of 1 at its spike;
  (i) every inter-spike interval is at least 1/(max b - lambda) (Proposition 1's bound with v(0) = 0), within 1e-12;
  (j) instance 0 simulated again gives the same counts and deviations, bit for bit.

Changed after the first trial (under Imago's own seed, which met all four conditions and nine of the ten controls):
control (a) as first committed compared the printed solution with R1's only, and R1's first coefficient is 0.6830
where the paper prints 0.684 (its third, 1.2178, cuts to the printed 1.217). The printed atoms are, to their four
decimals, the unit vectors (3, 8, 3)/sqrt 82, (9, 4, 5)/sqrt 122 and (2, 1, 4)/sqrt 21, identified by hand after that
trial; the control now also solves the example for those atoms (R3: Gram entries n_i.n_j/(|n_i||n_j|), correlations
n_i.s/|n_i|, every support certified in 50-digit arithmetic with margins above 1e-30), checks that each of their
entries rounds (half up) to the printed four decimals, and passes if R3's solution is the printed one. The test, its
conditions, the network's configuration (R2) and the other nine controls are unchanged.

Not tested: the paper's 400-atom dictionary and image patch (not released), its CPU benchmark against FISTA, its
convolutional problems, Theorem 1's own proof (arXiv:1603.01644), and the limit itself, which no finite run reaches.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: OPENBLAS_NUM_THREADS=1 OPENBLAS_CORETYPE=Prescott python3 snn/tld2017.py (the pinned scipy-notebook image).
"""

import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_CORETYPE", "Prescott")

import gzip  # noqa: E402
import hashlib  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
import tarfile  # noqa: E402
import time  # noqa: E402
import zlib  # noqa: E402
from fractions import Fraction  # noqa: E402

import mpmath  # noqa: E402
import numpy as np  # noqa: E402
from scipy.optimize import minimize  # noqa: E402

EPRINT = ("arXiv-1705.05475v1.tar.gz", "282275024e4035aaccf5c2f49e920e7c2744eb67fcaac08625a7670f05dff2ef", 470802)
FILES = {"abstract": "abstract.tex", "snn": "snn.tex", "practice": "practice.tex", "fig3": "fig-3neuron.tex",
         "rates": "SupportDoc2/spike-rates.tex", "raster": "figures/dynamics-raster.pdf",
         "counts": "figures/dynamics-spike-count.pdf"}

N_INSTANCES = 20
PIXELS = 64
ATOMS = 400
SUPPORT = 8
PATH_FLOOR = 0.01
PATH_EVENTS = 400
MAX_REDRAWS = 50
T_END = 10000.0
T_LONG = 100000.0
EARLY = (500.0, 1000.0)
LATE = (5000.0, 10000.0)
LONGEST = (50000.0, 100000.0)
TOL_LATE = 0.01
TOL_SHRINK = 0.5
RASTER_T = 12.0
RASTER_TOL = 0.1
MP_DIGITS = 50
MP_TOL = 1e-9
FINE_H = 1e-5
FINE_TOL = 2e-3
SOLVER_TOL = 1e-6
IDENTITY_TOL = 1e-9
ROOT_TOL = 1e-12
FIG_TIMES = (1, 2, 4, 6, 8, 10, 12)
ALCA_H = 0.01
ALCA_T = 50.0
ALCA_FIG_H = 1e-4
DT_STEPS = (1e-2, 1e-3)
DT_T = 1000.0
DT_T0 = 500.0
DT_INSTANCES = 4
PRINTED_SOLUTION = ("0.684", "0", "1.217")
INTEGER_ATOMS = ((3, 8, 3), (9, 4, 5), (2, 1, 4))     # R3: identified after the first trial (see the docstring)
MP_MARGIN = 1e-30

TEST = ("Refuted if the S-LCA as the paper defines it (Section 3, Appendix A: μ_i = b_i − Σ_{j≠i} w_ij(α∗σ_j), "
        "α(t) = e^−t; potentials integrate μ_i − λ from 0, spike at 1, reset to 0; b_i = φ_iᵀs, w_ij = φ_iᵀφ_j), "
        "simulated event by event, has rates a_i(t) = N_i(t)/t not approaching the CLASSO solution a*: on Section "
        "4.1's 3-neuron example or any of 20 seeded instances like Section 4.2's (400 Gaussian 8 × 8 atoms split "
        "into 128 non-negative channels, λ giving 8 non-zeros), max_i |a_i(t) − a*_i| over t in [5000, 10000] "
        "exceeds 1% of max a*, or half its value over [500, 1000].")

# strings the e-print must print (whitespace removed before comparing), by file
PRINTED = {
    "abstract": ["With a moderate but well-defined assumption, we prove that the SNN indeed solves sparse coding."],
    "snn": [r"where $\decay(t) = e^{-t}$ for $t \ge 0$ and zero otherwise.",
            r"The potential is ``charged'' up according to $\poten_i(t)=\int_0^t(\curr_i-\currbias)$",
            r"Consider now a CLASSO problem where the dictionary atoms are non-negative and normalized to unit Euclidean norm.",
            r"Configure S-LCA with $\currbias$ and $w_{ij} = \transpose{\vvphi}_i\vvphi_j$ from Equation~\ref{eqn:CLASSO},",
            r"and set $\potenfire \gets 1$, $\potenreset \gets 0$.",
            r"\spikerate_i(t) \bydef \frac{1}{t-\starttime}\int_{\starttime}^t \spiketrain_i(s)\,ds"],
    "practice": [r"0.3313 & 0.8148 & 0.4364 \\ 0.8835 & 0.3621 & 0.2182 \\ 0.3313 & 0.4527 & 0.8729",
                 r"\lambda = 0.1.",
                 r"We use a 3-neuron network configured with $b_i = \transpose{\vvphi}_i\vvs$,",
                 r"the bias current as $\lambda=0.1$ and firing threshold set to 1.",
                 r"a weak neuron, such as Neuron 2, is quickly rendered inactive",
                 r"400-atom dictionary learned from other image datasets.",
                 r"The input has 128 dimensions by splitting the image into positive and negative channels.",
                 r"With the chosen $\lambda$, the optimal solution has 8 non-zeros entries.",
                 r"increasing the step size from $10^{-3}$ to $10^{-2}$ sacrifices two digits of accuracy in the computed $E^*$.",
                 r"In practice, picking some $\starttime > 0$ is better when we expect a sparse solution"],
    "fig3": [r"The convergent firing rates yield the CLASSO optimal solution of $[0.684, 0, 1.217]$"],
    "rates": [r"Assume that there is a positive number $r > 0$ such that whenever the numbers"],
}


class Refused(Exception):
    pass


# ----------------------------------------------------------------------------------------------- the e-print

def flatten_tex(tex):
    lines = [re.sub(r"(?<!\\)%.*$", "", line) for line in tex.split("\n")]
    return re.sub(r"\s+", "", "\n".join(lines))


def open_eprint(path):
    with open(path, "rb") as fh:
        blob = fh.read()
    name, sha, size = EPRINT
    if len(blob) != size or hashlib.sha256(blob).hexdigest() != sha:
        raise Refused("the e-print does not match its pinned size and SHA-256")
    tf = tarfile.open(fileobj=io.BytesIO(gzip.decompress(blob)))
    members = {m.name: m for m in tf.getmembers() if m.isfile()}
    out = {}
    for key, fname in FILES.items():
        if fname not in members:
            raise Refused(f"the e-print lacks {fname}")
        out[key] = tf.extractfile(members[fname]).read()
    return out


def check_printed(files):
    count = 0
    for key, strings in PRINTED.items():
        flat = flatten_tex(files[key].decode("utf-8"))
        for s in strings:
            if re.sub(r"\s+", "", s) not in flat:
                raise Refused(f"{FILES[key]} does not print: {s[:60]}")
            count += 1
    return count


def parse_example(practice_tex):
    """Section 4.1's s, Phi (columns are the atoms, Phi = [phi_1 phi_2 phi_3]) and lambda, as exact decimals."""
    flat = flatten_tex(practice_tex)
    i = flat.find(r"\subsection{IllustrationofSNNdynamics}")
    if i < 0:
        raise Refused("practice.tex has no Illustration subsection")
    m = re.search(r"\\vvs=\\begin\{bmatrix\}(.*?)\\end\{bmatrix\}.*?\\Phi=\[\\vvphi_1\\,\\vvphi_2\\,\\vvphi_3\]="
                  r"\\begin\{bmatrix\}(.*?)\\end\{bmatrix\},\\quad\\lambda=([0-9.]+)\.\\end\{equation\*\}", flat[i:])
    if not m:
        raise Refused("practice.tex: the example's s, Phi and lambda were not found")
    s = [Fraction(x) for x in m.group(1).split(r"\\")]
    rows = [[Fraction(x) for x in row.split("&")] for row in m.group(2).split(r"\\")]
    lam = Fraction(m.group(3))
    if len(s) != 3 or len(rows) != 3 or any(len(r) != 3 for r in rows):
        raise Refused("practice.tex: the example is not 3 x 3")
    atoms = [[rows[mm][j] for mm in range(3)] for j in range(3)]
    return s, atoms, lam


def parse_printed_solution(fig3_tex):
    flat = flatten_tex(fig3_tex)
    m = re.search(r"CLASSOoptimalsolutionof\$\[([0-9.,]+)\]\$", flat)
    if not m:
        raise Refused("fig-3neuron.tex: the printed solution was not found")
    vals = tuple(m.group(1).split(","))
    if vals != PRINTED_SOLUTION:
        raise Refused(f"fig-3neuron.tex prints {vals}, not {PRINTED_SOLUTION}")
    return vals


# ----------------------------------------------------------------------------------------------- the figures

def pdf_drawing_streams(pdf):
    """Decompressed content streams that draw lines (FlateDecode or raw), in file order."""
    out = []
    for m in re.finditer(rb"<<(.*?)>>\s*stream\r?\n", pdf, re.S):
        d = m.group(1)
        L = re.search(rb"/Length (\d+)\b(?!\s+\d+\s+R)", d)
        if not L:
            continue
        raw = pdf[m.end():m.end() + int(L.group(1))]
        if b"FlateDecode" in d:
            try:
                s = zlib.decompress(raw)
            except zlib.error:
                continue
        else:
            s = raw
        s = re.sub(r"\s+", " ", s.decode("latin-1"))
        if " l S" in s:
            out.append(s)
    return out


SEG = re.compile(r"(-?[\d.]+) (-?[\d.]+) m (-?[\d.]+) (-?[\d.]+) l S")


def axis_ticks(stream, fixed, along, length, labels):
    """Tick strokes perpendicular to an axis: for an x axis (along = 'x'), strokes x y0 m x y1 l with y0 = fixed and
    |y0 - y1| = length; returns their positions in order with the labels that follow them as Tj strings."""
    pos = []
    for m in SEG.finditer(stream):
        a, b, c, d = map(float, m.groups())
        if along == "x" and a == c and abs(b - fixed) < 1e-6 and abs(abs(b - d) - length) < 0.01:
            pos.append(a)
        if along == "y" and b == d and abs(a - fixed) < 1e-6 and abs(abs(a - c) - length) < 0.01:
            pos.append(b)
    if len(pos) != len(labels):
        raise Refused(f"figure: {len(pos)} ticks where {len(labels)} were expected")
    return pos


def read_raster(pdf):
    """Figure 1(c): the spike times of neurons 1-3, from the '+' markers' vertical strokes (6 pt long, centred on a
    neuron's row), mapped by the x ticks at 0 and 12; rows from the y ticks labelled 01, 02, 03 in order."""
    streams = pdf_drawing_streams(pdf)
    if len(streams) != 1:
        raise Refused("raster: expected one drawing stream")
    st = streams[0]
    if [x.strip() for x in re.findall(r"\(([ 0-9]+)\)Tj", st)][:3] != ["01", "02", "03"]:
        raise Refused("raster: the row labels are not 01, 02, 03")
    xt = axis_ticks(st, 180.449, "x", 4.301, ["0", "2", "4", "6", "8", "10", "12"])
    rows = axis_ticks(st, 38.102, "y", 4.296, ["01", "02", "03"])
    x0, x12 = xt[0], xt[-1]
    spikes = {1: [], 2: [], 3: []}
    for m in SEG.finditer(st):
        a, b, c, d = map(float, m.groups())
        if a == c and abs(abs(d - b) - 6.0) < 1e-6:
            y = (b + d) / 2
            for n, r in enumerate(rows, start=1):
                if abs(y - r) < 0.01:
                    spikes[n].append((a - x0) / (x12 - x0) * 12.0)
    return {n: sorted(v) for n, v in spikes.items()}


def read_count_curves(pdf):
    """Figure 1(d): the dashed curves (int_0^t T(u_i) of the A-LCA), one per neuron in the raster's colours, as
    polylines in (t, count) mapped by the x ticks at 0 and 12 and the y ticks at 0 and 15."""
    streams = pdf_drawing_streams(pdf)
    if len(streams) != 1:
        raise Refused("counts: expected one drawing stream")
    st = streams[0]
    xt = axis_ticks(st, 195.898, "x", 4.296, ["0", "2", "4", "6", "8", "10", "12"])
    yt = axis_ticks(st, 44.051, "y", 4.301, ["0", "3", "6", "9", "12", "15"])
    x0, x12, y0, y15 = xt[0], xt[-1], yt[0], yt[-1]
    colours = {"0.117647 0.564706 1": 1, "0.235294 0.701961 0.443137": 2, "0.862745 0.0784314 0.235294": 3}
    tokens = re.finditer(r"(?P<rg>[\d.]+ [\d.]+ [\d.]+) RG|(?P<dash>\[[^\]]*\]) [\d.]+ d|"
                         r"(?P<x>-?[\d.]+) (?P<y>-?[\d.]+) (?P<op>[ml])\b", st)
    colour, dashed, curves = None, False, {1: [], 2: [], 3: []}
    for t in tokens:
        if t.group("rg"):
            colour = colours.get(t.group("rg"))
        elif t.group("dash"):
            dashed = t.group("dash").strip("[] ") != ""
        elif dashed and colour:
            x, y = float(t.group("x")), float(t.group("y"))
            curves[colour].append(((x - x0) / (x12 - x0) * 12.0, (y0 - y) / (y0 - y15) * 15.0))
    for n in curves:
        if len(curves[n]) < 10:
            raise Refused(f"counts: no dashed curve for neuron {n}")
    return curves


def curve_at(points, t):
    xs = [p[0] for p in points]
    k = max(1, min(len(points) - 1, int(np.searchsorted(xs, t, side="right"))))
    (xa, ya), (xb, yb) = points[k - 1], points[k]
    return ya if xb == xa else ya + (yb - ya) * (t - xa) / (xb - xa)


# ----------------------------------------------------------------------------------------------- exact arithmetic

def frac_of(x):
    return Fraction(x) if not isinstance(x, Fraction) else x


def scaled_ints(vec):
    """Exact integers X and a power K with vec = X / 2^K (vec of doubles)."""
    ratios = [float(x).as_integer_ratio() for x in vec]
    K = max(den.bit_length() - 1 for _, den in ratios)
    return [num << (K - (den.bit_length() - 1)) for num, den in ratios], K


def exact_dot(xi, Kx, yi, Ky):
    return Fraction(sum(a * b for a, b in zip(xi, yi)), 1 << (Kx + Ky))


def solve_exact(A, rhs):
    n = len(A)
    M = [list(map(frac_of, A[i])) + [frac_of(rhs[i])] for i in range(n)]
    for col in range(n):
        piv = next((r for r in range(col, n) if M[r][col] != 0), None)
        if piv is None:
            raise ZeroDivisionError("singular")
        M[col], M[piv] = M[piv], M[col]
        p = M[col][col]
        for r in range(n):
            if r != col and M[r][col] != 0:
                f = M[r][col] / p
                M[r] = [x - f * y for x, y in zip(M[r], M[col])]
    return [M[i][n] / M[i][i] for i in range(n)]


def positive_definite(A):
    n = len(A)
    M = [list(map(frac_of, row)) for row in A]
    for k in range(n):
        if M[k][k] <= 0:
            return False
        for r in range(k + 1, n):
            f = M[r][k] / M[k][k]
            if f:
                for c in range(k, n):
                    M[r][c] -= f * M[k][c]
    return True


def certify(G, b, lam, S):
    """G(j, i) exact Gram entry, b exact correlations (list), lam exact; S the candidate support. Returns the
    certificate: a dict with ok, the exact solution (dict i -> Fraction) and the smallest slack off the support."""
    S = sorted(S)
    n = len(b)
    lam = frac_of(lam)
    if not S:
        slack = min((lam - b[j] for j in range(n)), default=Fraction(1))
        return {"ok": slack > 0, "a": {}, "slack": slack, "pd": True, "positive": True}
    GSS = [[G(i, j) for j in S] for i in S]
    pd = positive_definite(GSS)
    if not pd:
        return {"ok": False, "a": {}, "slack": None, "pd": False, "positive": False}
    aS = solve_exact(GSS, [b[i] - lam for i in S])
    positive = all(x > 0 for x in aS)
    a = dict(zip(S, aS))
    inS = set(S)
    slack = None
    for j in range(n):
        if j in inS:
            continue
        r = b[j] - sum(G(j, i) * a[i] for i in S)
        sl = lam - r
        slack = sl if slack is None or sl < slack else slack
    ok = pd and positive and (slack is None or slack > 0)
    return {"ok": ok, "a": a, "slack": slack, "pd": pd, "positive": positive}


def enumerate_supports(G, b, lam):
    n = len(b)
    passing = []
    for mask in range(1 << n):
        S = [i for i in range(n) if mask >> i & 1]
        c = certify(G, b, lam, S)
        if c["ok"]:
            passing.append((S, c))
    return passing


def cut_or_round(x, printed):
    """x against a printed decimal, cut or rounded (half up) to its digits; a printed integer is exact."""
    x = frac_of(x)
    if "." not in printed:
        return x == Fraction(printed)
    d = len(printed.split(".")[1])
    p = Fraction(printed)
    q = Fraction(1, 10 ** d)
    cut = Fraction(math.floor(x / q)) * q if x >= 0 else -Fraction(math.floor(-x / q)) * q
    rnd = Fraction(math.floor(x / q + Fraction(1, 2))) * q
    return cut == p or rnd == p


# ----------------------------------------------------------------------------------------------- the network

def first_passage(v, c, d, thr=1.0, x=None):
    """The first x >= 0 with v + c x + d (1 - e^-x) = thr, for c > 0 and d <= 0 (convex, increasing at its root);
    Newton's method from the upper bound (thr - v - d)/c, which converges monotonically from the right."""
    if v >= thr:
        return 0.0
    if d >= 0.0:
        return (thr - v) / c
    if x is None:
        x = (thr - v - d) / c
    for _ in range(200):
        g = v + c * x - d * math.expm1(-x) - thr
        gp = c + d * math.exp(-x)
        step = g / gp
        if not step > 1e-16 * max(1.0, x):
            break
        x -= step
    return x


def slca_exact(b, W, lam, t_end, windows=(), astar=None, record_until=0.0, thr=1.0, isi_window=None, snapshot=None):
    """The S-LCA simulated event by event (every neuron given must have b_i > lam). Returns counts, the deviation
    maxima per window, the state at t_end and the run's checks."""
    b = np.ascontiguousarray(b, dtype=float)
    K = b.size
    c = b - lam
    if np.any(c <= 0):
        raise ValueError("every neuron simulated must have b > lambda")
    WT = np.ascontiguousarray(np.asarray(W, dtype=float).T)
    if np.any(np.diag(WT) != 0) or np.any(WT < 0):
        raise ValueError("weights must be non-negative with a zero diagonal")
    astar = np.zeros(K) if astar is None else np.asarray(astar, dtype=float)
    v = np.zeros(K)
    mu = b.copy()
    integ = np.zeros(K)
    count = np.zeros(K, dtype=np.int64)
    last = np.full(K, -1.0)
    first = np.full(K, -1.0)
    max_isi_win = np.zeros(K)
    win = [(float(t1), float(t2)) for t1, t2 in windows]
    wE = [np.zeros(K) for _ in win]
    bounds = sorted({x for w in win for x in w if x <= t_end} | ({float(snapshot)} if snapshot is not None else set()))
    count_snap = None
    bi = 0
    t = 0.0
    min_isi = math.inf
    root_res = 0.0
    events = 0
    spikes = []
    while True:
        d = mu - b
        U = (thr - v - d) / c
        m = float(U.min())
        L = (thr - v) / c
        best, k = math.inf, -1
        for i in np.flatnonzero(L <= m):
            x = first_passage(float(v[i]), float(c[i]), float(d[i]), thr, float(U[i]))
            if x < best:
                best, k = x, int(i)
        tn = t + best
        while bi < len(bounds) and bounds[bi] <= min(tn, t_end):
            tau = bounds[bi]
            if snapshot is not None and tau == float(snapshot):
                count_snap = count.copy()
            dev = np.abs(count / tau - astar)
            for wi, (t1, t2) in enumerate(win):
                if tau == t1 or tau == t2:
                    np.maximum(wE[wi], dev, out=wE[wi])
            bi += 1
        dt = (t_end - t) if tn > t_end else best
        e = math.exp(-dt)
        oe = -math.expm1(-dt)
        v += c * dt + d * oe
        integ += b * dt + d * oe
        mu = b + d * e
        if tn > t_end:
            t = t_end
            break
        t = tn
        res = abs(float(v[k]) - thr)
        if res > root_res:
            root_res = res
        v[k] = 0.0
        count[k] += 1
        n = int(count[k])
        for wi, (t1, t2) in enumerate(win):
            if t1 <= t <= t2:
                dev = max(abs((n - 1) / t - astar[k]), abs(n / t - astar[k]))
                if dev > wE[wi][k]:
                    wE[wi][k] = dev
        if last[k] >= 0:
            isi = t - last[k]
            if isi < min_isi:
                min_isi = isi
            if isi_window and isi_window[0] <= last[k] and t <= isi_window[1] and isi > max_isi_win[k]:
                max_isi_win[k] = isi
        else:
            first[k] = t
        last[k] = t
        if t <= record_until:
            spikes.append((k, t))
        mu -= WT[k]
        events += 1
    identity = float(np.max(np.abs((integ - lam * t) - (count + v)))) / t
    return {"count": count, "E": [float(x.max()) for x in wE], "E_each": wE, "rates": count / t, "u_avg": integ / t,
            "v": v, "mu": mu, "t": t, "events": events, "spikes": spikes, "root_res": root_res, "min_isi": min_isi,
            "identity": identity, "last": last, "first": first, "max_isi_win": max_isi_win, "count_snap": count_snap}


def slca_mp(b, W, lam, t_end, digits=MP_DIGITS, thr=1):
    """The same network in mpmath at the given digits, for short runs: returns the spike sequence."""
    with mpmath.workdps(digits):
        K = len(b)
        b = [mpmath.mpf(x) for x in b]
        W = [[mpmath.mpf(x) for x in row] for row in W]
        lam = mpmath.mpf(lam)
        thr = mpmath.mpf(thr)
        v = [mpmath.mpf(0)] * K
        mu = list(b)
        t = mpmath.mpf(0)
        out = []
        tol = mpmath.mpf(10) ** (-(digits - 5))
        while True:
            best, k = None, -1
            for i in range(K):
                c, d = b[i] - lam, mu[i] - b[i]
                if c <= 0:
                    continue
                if d == 0:
                    x = (thr - v[i]) / c
                else:
                    x = (thr - v[i] - d) / c
                    for _ in range(400):
                        g = v[i] + c * x + d * (1 - mpmath.exp(-x)) - thr
                        step = g / (c + d * mpmath.exp(-x))
                        x -= step
                        if abs(step) < tol:
                            break
                if best is None or x < best:
                    best, k = x, i
            if best is None or t + best > t_end:
                break
            dt = best
            for i in range(K):
                d = mu[i] - b[i]
                v[i] = v[i] + (b[i] - lam) * dt + d * (1 - mpmath.exp(-dt))
                mu[i] = b[i] + d * mpmath.exp(-dt)
            t += dt
            v[k] = mpmath.mpf(0)
            for j in range(K):
                if j != k:
                    mu[j] -= W[j][k]
            out.append((k, float(t)))
        return out


def slca_discrete(b, W, lam, h, t_end, t0=None, record_until=0.0, thr=1.0):
    """Section 4's approximation: steps of size h (whole steps counted as integers), each integrated exactly with no
    spike inside it; a neuron whose potential has reached thr at the step's end spikes, is reset to 0, and inhibits
    the others from then on."""
    b = np.ascontiguousarray(b, dtype=float)
    c = b - lam
    W = np.asarray(W, dtype=float)
    steps = int(round(t_end / h))
    s0 = int(round(t0 / h)) if t0 is not None else None
    e = math.exp(-h)
    oe = -math.expm1(-h)
    v = np.zeros(b.size)
    mu = b.copy()
    count = np.zeros(b.size, dtype=np.int64)
    count0 = None
    spikes = []
    for n in range(1, steps + 1):
        d = mu - b
        v += c * h + d * oe
        mu = b + d * e
        fired = np.flatnonzero(v >= thr)
        if fired.size:
            v[fired] = 0.0
            count[fired] += 1
            mu -= W[:, fired].sum(axis=1)
            if n * h <= record_until:
                spikes.extend((int(k), n * h) for k in fired)
        if s0 is not None and n == s0:
            count0 = count.copy()
    return {"count": count, "count0": count0, "spikes": spikes}


def alca_rk4(b, W, lam, u0, t_end, h, sample_times=()):
    """The A-LCA, u' = b - u - W T(u), T(u) = max(u - lam, 0), with z' = T(u) carried along (RK4, whole steps)."""
    b = np.asarray(b, dtype=float)
    W = np.asarray(W, dtype=float)

    def f(u):
        T = np.maximum(u - lam, 0.0)
        return b - u - W @ T, T

    u = np.asarray(u0, dtype=float).copy()
    z = np.zeros_like(u)
    steps = int(round(t_end / h))
    marks = {int(round(ts / h)): ts for ts in sample_times}
    samples = {}
    for n in range(1, steps + 1):
        k1, T1 = f(u)
        k2, T2 = f(u + 0.5 * h * k1)
        k3, T3 = f(u + 0.5 * h * k2)
        k4, T4 = f(u + h * k3)
        z += h / 6.0 * (T1 + 2 * T2 + 2 * T3 + T4)
        u += h / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)
        if n in marks:
            samples[marks[n]] = z.copy()
    return u, z, samples


# ----------------------------------------------------------------------------------------------- instances

def split_unit(g):
    norm = math.sqrt(math.fsum(float(x) * float(x) for x in g))
    return np.concatenate([np.maximum(g, 0.0), np.maximum(-g, 0.0)]) / norm


def signal(x):
    return np.concatenate([np.maximum(x, 0.0), np.maximum(-x, 0.0)])


def homotopy_lambda(G, b, target=SUPPORT, floor=PATH_FLOOR, max_events=PATH_EVENTS):
    """The non-negative LASSO path from lambda_max = max b downwards; the midpoint of the first interval on which the
    support has `target` atoms, with that support, or None."""
    lam0 = float(b.max())
    lam = lam0
    S = [int(np.argmax(b))]
    just = S[0]
    for _ in range(max_events):
        GSS = G[np.ix_(S, S)]
        p = np.linalg.solve(GSS, b[S])
        q = np.linalg.solve(GSS, np.ones(len(S)))
        best, ev = 0.0, None
        for idx, i in enumerate(S):
            if q[idx] < 0 and i != just:
                lj = p[idx] / q[idx]
                if 0 < lj < lam * (1 - 1e-12) and lj > best:
                    best, ev = lj, ("drop", i)
        out = np.setdiff1d(np.arange(b.size), S)
        if out.size:
            GjS = G[np.ix_(out, S)]
            num = b[out] - GjS @ p
            den = 1.0 - GjS @ q
            ok = den > 0
            lj = np.where(ok, num / np.where(ok, den, 1.0), -np.inf)
            lj = np.where(lj < lam * (1 - 1e-12), lj, -np.inf)
            j = int(np.argmax(lj))
            if lj[j] > best:
                best, ev = float(lj[j]), ("add", int(out[j]))
        if len(S) == target:
            if best <= 0:
                return None
            return (best + lam) / 2.0, sorted(S)
        if ev is None or best < floor * lam0:
            return None
        if ev[0] == "drop":
            S.remove(ev[1])
            just = -1
        else:
            S.append(ev[1])
            just = ev[1]
        lam = best
    return None


def draw_instance(seed, k):
    """Instance k under the seed: atoms, signal, lambda (support 8), the exact certificate, the network's inputs and
    weights (each exact value rounded once), redraws counted."""
    for r in range(MAX_REDRAWS):
        rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(int(seed, 16), spawn_key=(1, k, r))))
        g = rng.standard_normal((PIXELS, ATOMS))
        x = rng.standard_normal(PIXELS)
        Phi = np.stack([split_unit(g[:, j]) for j in range(ATOMS)], axis=1)
        s = signal(x)
        cols = [scaled_ints(Phi[:, j]) for j in range(ATOMS)]
        si, Ks = scaled_ints(s)
        bex = [exact_dot(ci, Kc, si, Ks) for ci, Kc in cols]
        bfl = np.array([float(q) for q in bex])
        G = Phi.T @ Phi
        found = homotopy_lambda(G, bfl, target=SUPPORT, floor=PATH_FLOOR, max_events=PATH_EVENTS)
        if found is None:
            continue
        lam, S = found
        memo = {}

        def Gx(j, i):
            key = (j, i) if j <= i else (i, j)
            if key not in memo:
                memo[key] = exact_dot(cols[key[0]][0], cols[key[0]][1], cols[key[1]][0], cols[key[1]][1])
            return memo[key]

        cert = certify(Gx, bex, Fraction(lam), S)
        if not cert["ok"]:
            continue
        lamx = Fraction(lam)
        cand = [i for i in range(ATOMS) if bex[i] > lamx]
        W = np.zeros((len(cand), len(cand)))
        for p_, i in enumerate(cand):
            for q_, j in enumerate(cand):
                if q_ > p_:
                    W[p_, q_] = W[q_, p_] = float(Gx(i, j))
        astar = np.zeros(ATOMS)
        for i, val in cert["a"].items():
            astar[i] = float(val)
        return {"k": k, "redraws": r, "Phi": Phi, "s": s, "lam": lam, "S": S, "b": bfl, "G": G, "cand": cand,
                "W": W, "astar": astar, "astar_exact": cert["a"], "slack": float(cert["slack"]),
                "a_max": float(astar.max())}
    raise Refused(f"instance {k}: no draw met the conditions in {MAX_REDRAWS}")


def lbfgs_solution(G, b, lam):
    f = lambda a: (0.5 * a @ G @ a - b @ a + lam * a.sum(), G @ a - b + lam)  # noqa: E731
    r = minimize(f, np.zeros(b.size), jac=True, method="L-BFGS-B", bounds=[(0.0, None)] * b.size,
                 options={"maxiter": 100000, "maxfun": 200000, "ftol": 1e-16, "gtol": 1e-13})
    return r.x


def objective(G, b, ss, lam, a):
    """1/2 ||s - Phi a||^2 + lam sum(a), written with the Gram matrix G, b = Phi^T s and ss = s^T s."""
    return 0.5 * ss - float(b @ a) + 0.5 * float(a @ G @ a) + lam * float(np.sum(a))


def fin(x, default=-1.0):
    return float(x) if isinstance(x, (int, float, np.floating)) and math.isfinite(float(x)) else default


# ----------------------------------------------------------------------------------------------- the run

def r3_problem(s, lam, digits=MP_DIGITS):
    """R3: the unit vectors n_j/|n_j| that the printed atoms round; every support certified in mpmath."""
    with mpmath.workdps(digits):
        n = INTEGER_ATOMS
        norms = [mpmath.sqrt(sum(x * x for x in v)) for v in n]
        atoms = [[mpmath.mpf(x) / nm for x in v] for v, nm in zip(n, norms)]
        G = [[sum(mpmath.mpf(a) * c for a, c in zip(n[i], n[j])) / (norms[i] * norms[j]) for j in range(3)]
             for i in range(3)]
        def mpq(q):
            q = Fraction(q)
            return mpmath.mpf(q.numerator) / q.denominator

        b = [sum(mpmath.mpf(a) * mpq(c) for a, c in zip(n[i], s)) / norms[i] for i in range(3)]
        lm = mpq(lam)
        passing = []
        for mask in range(8):
            S = [i for i in range(3) if mask >> i & 1]
            if not S:
                slack = min(lm - b[j] for j in range(3))
                if slack > MP_MARGIN:
                    passing.append((S, [mpmath.mpf(0)] * 3, slack))
                continue
            A = mpmath.matrix([[G[i][j] for j in S] for i in S])
            piv_ok = all(x > MP_MARGIN for x in [mpmath.det(mpmath.matrix([[G[i][j] for j in S[:k]] for i in S[:k]]))
                                                 for k in range(1, len(S) + 1)])
            if not piv_ok:
                continue
            aS = mpmath.lu_solve(A, mpmath.matrix([b[i] - lm for i in S]))
            a = {i: aS[k] for k, i in enumerate(S)}
            if not all(a[i] > MP_MARGIN for i in S):
                continue
            slack = min((lm - (b[j] - sum(G[j][i] * a[i] for i in S)) for j in range(3) if j not in S), default=1)
            if slack > MP_MARGIN:
                passing.append((S, [a.get(i, mpmath.mpf(0)) for i in range(3)], slack))
        rounds = []
        for j in range(3):
            for m in range(3):
                rounds.append(Fraction(mpmath.nstr(atoms[j][m], 40)))
        return passing, rounds


def example_problem(s, atoms, lam, reading):
    n = len(atoms)
    G = [[sum(atoms[i][m] * atoms[j][m] for m in range(len(s))) for j in range(n)] for i in range(n)]
    if reading == "R2":
        for i in range(n):
            G[i][i] = Fraction(1)
    b = [sum(atoms[i][m] * s[m] for m in range(len(s))) for i in range(n)]
    return G, b


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    path = os.path.join(inputs, EPRINT[0])
    if not os.path.exists(path):
        raise Refused(f"missing input {EPRINT[0]}")
    files = open_eprint(path)
    printed = check_printed(files)
    s_ex, atoms_ex, lam_ex = parse_example(files["practice"].decode("utf-8"))
    parse_printed_solution(files["fig3"].decode("utf-8"))
    raster = read_raster(files["raster"])
    curves = read_count_curves(files["counts"])
    timing, detail = {}, {"test": TEST}

    # ---- the example: certificates under both readings
    t0 = time.time()
    ex = {}
    for reading in ("R1", "R2"):
        G, b = example_problem(s_ex, atoms_ex, lam_ex, reading)
        passing = enumerate_supports(lambda j, i, G=G: G[j][i], b, lam_ex)
        ex[reading] = {"G": G, "b": b, "passing": passing}
    unique = all(len(ex[r]["passing"]) == 1 for r in ex)
    sol = {r: [ex[r]["passing"][0][1]["a"].get(i, Fraction(0)) for i in range(3)] if ex[r]["passing"] else None
           for r in ex}
    printed_r1 = bool(sol["R1"]) and all(cut_or_round(x, p) for x, p in zip(sol["R1"], PRINTED_SOLUTION))
    printed_r2 = bool(sol["R2"]) and all(cut_or_round(x, p) for x, p in zip(sol["R2"], PRINTED_SOLUTION))
    r3_passing, r3_atoms = r3_problem(s_ex, lam_ex)
    q4 = Fraction(1, 10000)
    r3_round = all(Fraction(math.floor(x / q4 + Fraction(1, 2))) * q4 == atoms_ex[j][m]
                   for (j, m), x in zip(((j, m) for j in range(3) for m in range(3)), r3_atoms))
    r3_sol = ([Fraction(mpmath.nstr(x, 40)) if x != 0 else Fraction(0) for x in r3_passing[0][1]]
              if len(r3_passing) == 1 else None)
    printed_r3 = bool(r3_sol) and all(cut_or_round(x, p) for x, p in zip(r3_sol, PRINTED_SOLUTION))
    if not sol["R2"]:
        raise Refused("the example's R2 problem has no certified solution")
    G1 = ex["R1"]["G"]
    b_ex = np.array([float(x) for x in ex["R2"]["b"]])
    W_ex = np.array([[0.0 if i == j else float(G1[i][j]) for j in range(3)] for i in range(3)])
    lam_f = float(lam_ex)
    a_ex = np.array([float(x) for x in sol["R2"]])
    cand_ex = [i for i in range(3) if ex["R2"]["b"][i] > lam_ex]
    if cand_ex != [0, 1, 2]:
        raise Refused("the example has a neuron that cannot spike")

    # ---- the example: the network
    run_ex = slca_exact(b_ex, W_ex, lam_f, T_LONG, windows=(EARLY, LATE, LONGEST), astar=a_ex,
                        record_until=RASTER_T, isi_window=LATE)
    E_early_ex, E_late_ex, E_longest_ex = run_ex["E"]
    amax_ex = float(a_ex.max())
    c1 = E_late_ex <= TOL_LATE * amax_ex
    c2 = E_late_ex <= TOL_SHRINK * E_early_ex
    timing["example"] = round(time.time() - t0, 2)

    # controls on the example
    t0 = time.time()
    sim_spikes = {n: [t for k, t in run_ex["spikes"] if k == n - 1] for n in (1, 2, 3)}
    raster_counts = {n: len(raster[n]) for n in raster}
    raster_same_counts = all(len(sim_spikes[n]) == raster_counts[n] for n in raster)
    raster_dev = max((abs(a - b) for n in raster for a, b in zip(sim_spikes[n], raster[n])), default=-1.0)
    ctl_raster = raster_same_counts and 0 <= raster_dev <= RASTER_TOL
    mp_spikes = slca_mp(list(b_ex), W_ex.tolist(), lam_f, RASTER_T)
    dbl = [(k, t) for k, t in run_ex["spikes"]]
    mp_same = [k for k, _ in mp_spikes] == [k for k, _ in dbl]
    mp_dev = max((abs(a[1] - b[1]) for a, b in zip(mp_spikes, dbl)), default=-1.0) if mp_same else -1.0
    ctl_mp = mp_same and 0 <= mp_dev <= MP_TOL
    fine = slca_discrete(b_ex, W_ex, lam_f, FINE_H, RASTER_T, record_until=RASTER_T)
    fine_same = [k for k, _ in fine["spikes"]] == [k for k, _ in dbl]
    fine_dev = max((abs(a[1] - b[1]) for a, b in zip(fine["spikes"], dbl)), default=-1.0) if fine_same else -1.0
    ctl_fine = fine_same and 0 <= fine_dev <= FINE_TOL
    fault = slca_exact(b_ex, 0.5 * W_ex, lam_f, T_END, windows=(EARLY, LATE), astar=a_ex)
    ctl_fault = fault["E"][1] > TOL_LATE * amax_ex
    timing["example_controls"] = round(time.time() - t0, 2)

    # beside on the example: Figure 1(d) and the A-LCA, Eq. 7
    t0 = time.time()
    fig = {n: {t: curve_at(curves[n], t) for t in FIG_TIMES} for n in curves}
    alca_fig = {}
    for label, u0 in (("u0_zero", np.zeros(3)), ("u0_b", b_ex.copy())):
        _, _, smp = alca_rk4(b_ex, W_ex, lam_f, u0, RASTER_T, ALCA_FIG_H, sample_times=FIG_TIMES)
        dev = max(abs(float(smp[t][n - 1]) - fig[n][t]) for n in (1, 2, 3) for t in FIG_TIMES)
        alca_fig[label] = {"max_dev": dev, "values": {str(t): [float(x) for x in smp[t]] for t in FIG_TIMES}}
    counts_at = {str(t): [sum(1 for k, tt in run_ex["spikes"] if k == n and tt <= t) for n in range(3)]
                 for t in FIG_TIMES}
    timing["example_beside"] = round(time.time() - t0, 2)

    # ---- the instances
    t0 = time.time()
    inst = []
    redraws = 0
    for k in range(N_INSTANCES):
        I = draw_instance(seed, k)
        redraws += I["redraws"]
        cand = I["cand"]
        a_c = I["astar"][cand]
        r = slca_exact(I["b"][cand], I["W"], I["lam"], T_END, windows=(EARLY, LATE), astar=a_c, isi_window=LATE)
        E1, E2 = r["E"]
        active_end = sorted(int(cand[i]) for i in range(len(cand)) if r["last"][i] >= LATE[0])
        T_u = np.maximum(r["u_avg"] - I["lam"], 0.0)
        thm2 = float(np.max(np.abs(T_u - r["rates"]))) * r["t"]
        isi_ratio = max((float(r["max_isi_win"][i]) * float(a_c[i]) for i in range(len(cand)) if a_c[i] > 0),
                        default=0.0)
        last_off = max((float(r["last"][i]) for i in range(len(cand)) if a_c[i] == 0), default=0.0)
        a_lb = lbfgs_solution(I["G"], I["b"], I["lam"])
        solver_dev = float(np.max(np.abs(a_lb - I["astar"])))
        u_end, _, _ = alca_rk4(I["b"][cand], I["W"], I["lam"], np.zeros(len(cand)), ALCA_T, ALCA_H)
        alca_err = float(np.max(np.abs(np.maximum(u_end - I["lam"], 0.0) - a_c))) / I["a_max"]
        inst.append({"k": k, "redraws": I["redraws"], "lam": I["lam"], "support": I["S"], "candidates": len(cand),
                     "a_max": I["a_max"], "slack": I["slack"], "astar": {str(i): float(I["astar"][i]) for i in I["S"]},
                     "E_early": E1, "E_late": E2, "late_ok": E2 <= TOL_LATE * I["a_max"],
                     "shrink_ok": E2 <= TOL_SHRINK * E1, "events": r["events"], "root_res": r["root_res"],
                     "identity": r["identity"], "min_isi": r["min_isi"],
                     "isi_bound": 1.0 / (float(I["b"].max()) - I["lam"]),
                     "active_end": active_end, "active_is_support": active_end == I["S"], "isi_ratio": isi_ratio,
                     "last_off_support": last_off, "thm2_times_t": thm2, "solver_dev": solver_dev,
                     "alca_err": alca_err, "_I": I, "_r": r})
        timing[f"instance_{k}"] = round(time.time() - t0, 2)
    c3 = all(x["late_ok"] for x in inst)
    c4 = all(x["shrink_ok"] for x in inst)

    # control (j): instance 0 again
    I0 = inst[0]["_I"]
    r0 = slca_exact(I0["b"][I0["cand"]], I0["W"], I0["lam"], T_END, windows=(EARLY, LATE),
                    astar=I0["astar"][I0["cand"]], isi_window=LATE)
    ctl_repeat = bool(np.array_equal(r0["count"], inst[0]["_r"]["count"])) and r0["E"] == inst[0]["_r"]["E"]

    # beside: the discrete-time implementation
    t0 = time.time()
    dt = {}
    G2 = np.array([[float(x) for x in row] for row in ex["R2"]["G"]])
    ss_ex = float(sum(x * x for x in s_ex))
    cases = [("example", G2, b_ex, ss_ex, b_ex, W_ex, lam_f, a_ex, [0, 1, 2])]
    for x in inst[:DT_INSTANCES]:
        I = x["_I"]
        cases.append((f"instance_{x['k']}", I["G"], I["b"], float(I["s"] @ I["s"]), I["b"][I["cand"]], I["W"],
                      I["lam"], I["astar"], I["cand"]))
    for name, G, bb, ss, bc, W, lam, astar, cand in cases:
        Estar = objective(G, bb, ss, lam, astar)
        gaps = {}
        for h in DT_STEPS:
            q = slca_discrete(bc, W, lam, h, DT_T, t0=DT_T0)
            a = np.zeros(bb.size)
            a[cand] = (q["count"] - q["count0"]) / (DT_T - DT_T0)
            gaps[h] = (objective(G, bb, ss, lam, a) - Estar) / Estar
        ex_run = slca_exact(bc, W, lam, DT_T, snapshot=DT_T0)
        a = np.zeros(bb.size)
        a[cand] = (ex_run["count"] - ex_run["count_snap"]) / (DT_T - DT_T0)
        gap_exact = (objective(G, bb, ss, lam, a) - Estar) / Estar
        digits = (math.log10(gaps[1e-2] / gaps[1e-3]) if gaps[1e-2] > 0 and gaps[1e-3] > 0 else float("nan"))
        dt[name] = {"gap_h1e-2": gaps[1e-2], "gap_h1e-3": gaps[1e-3], "gap_exact": gap_exact, "digits": digits}
    timing["discrete"] = round(time.time() - t0, 2)

    # ---- conditions, controls, outputs
    all_runs = [run_ex] + [x["_r"] for x in inst]
    ctl_identity = all(rr["identity"] <= IDENTITY_TOL for rr in all_runs)
    ctl_root = all(rr["root_res"] <= ROOT_TOL for rr in all_runs)
    bound_ex = 1.0 / (float(b_ex.max()) - lam_f)
    ctl_isi = run_ex["min_isi"] >= bound_ex - 1e-12 and all(x["min_isi"] >= x["isi_bound"] - 1e-12 for x in inst)
    ctl_solver_ex = float(np.max(np.abs(lbfgs_solution(G2, b_ex, lam_f) - a_ex)))
    ctl_solver = max([ctl_solver_ex] + [x["solver_dev"] for x in inst])
    controls = {"a_example_printed": bool(unique and len(r3_passing) == 1 and r3_round and printed_r3),
                "b_raster": bool(ctl_raster),
                "c_mpmath": bool(ctl_mp), "d_fine_step": bool(ctl_fine), "e_solver": bool(ctl_solver <= SOLVER_TOL),
                "f_fault": bool(ctl_fault), "g_identity": bool(ctl_identity), "h_root": bool(ctl_root),
                "i_isi_bound": bool(ctl_isi), "j_repeat": bool(ctl_repeat)}
    conditions = {"1_example_late": bool(c1), "2_example_shrinks": bool(c2), "3_instances_late": bool(c3),
                  "4_instances_shrink": bool(c4)}
    test_passed = int(all(conditions.values()))
    rel_late = [x["E_late"] / x["a_max"] for x in inst]
    ratio = [x["E_late"] / x["E_early"] if x["E_early"] > 0 else -1.0 for x in inst]
    digits_inst = [d for d in (dt[f"instance_{x['k']}"]["digits"] for x in inst[:DT_INSTANCES]) if math.isfinite(d)]
    rates_ex_long = run_ex["rates"]
    out = {
        "printed_strings": printed,
        "ex_astar_1": float(a_ex[0]), "ex_astar_2": float(a_ex[1]), "ex_astar_3": float(a_ex[2]),
        "ex_r1_astar_1": float(sol["R1"][0]) if sol["R1"] else -1.0,
        "ex_r1_astar_3": float(sol["R1"][2]) if sol["R1"] else -1.0,
        "ex_printed_r1": int(printed_r1), "ex_printed_r2": int(printed_r2), "ex_printed_r3": int(printed_r3),
        "ex_r3_atoms_round": int(r3_round), "ex_r3_supports": len(r3_passing),
        "ex_r3_astar_1": float(r3_sol[0]) if r3_sol else -1.0, "ex_r3_astar_3": float(r3_sol[2]) if r3_sol else -1.0,
        "ex_E_early": E_early_ex, "ex_E_late": E_late_ex, "ex_E_longest": E_longest_ex,
        "ex_late_rel": E_late_ex / amax_ex, "ex_shrink_ratio": fin(E_late_ex / E_early_ex if E_early_ex > 0 else -1.0),
        "ex_rate_1_at_1e5": float(rates_ex_long[0]), "ex_rate_2_at_1e5": float(rates_ex_long[1]),
        "ex_rate_3_at_1e5": float(rates_ex_long[2]),
        "ex_rates_match_printed": int(cut_or_round(Fraction(float(rates_ex_long[0])), PRINTED_SOLUTION[0])
                                      and cut_or_round(Fraction(float(rates_ex_long[2])), PRINTED_SOLUTION[2])
                                      and round(float(rates_ex_long[1]), 3) == 0),
        "ex_neuron2_spikes": int(run_ex["count"][1]), "ex_neuron2_last_spike": float(run_ex["last"][1]),
        "ex_raster_max_dev": raster_dev, "ex_raster_spikes": int(sum(raster_counts.values())),
        "ex_mp_max_dev": mp_dev, "ex_fine_max_dev": fine_dev, "ex_fault_E_late_rel": fault["E"][1] / amax_ex,
        "fig_alca_dev_u0_zero": alca_fig["u0_zero"]["max_dev"], "fig_alca_dev_u0_b": alca_fig["u0_b"]["max_dev"],
        "inst_n": len(inst), "inst_redraws": redraws,
        "inst_late_ok": sum(x["late_ok"] for x in inst), "inst_shrink_ok": sum(x["shrink_ok"] for x in inst),
        "inst_late_rel_max": max(rel_late), "inst_late_rel_median": float(np.median(rel_late)),
        "inst_shrink_ratio_max": max(ratio),
        "inst_support_8": sum(len(x["support"]) == SUPPORT for x in inst),
        "inst_candidates_median": float(np.median([x["candidates"] for x in inst])),
        "inst_events_median": float(np.median([x["events"] for x in inst])),
        "assume_active_is_support": sum(x["active_is_support"] for x in inst),
        "assume_isi_ratio_max": max(x["isi_ratio"] for x in inst),
        "assume_last_off_support_max": max(x["last_off_support"] for x in inst),
        "thm2_times_t_max": max(x["thm2_times_t"] for x in inst),
        "alca_err_max": max(x["alca_err"] for x in inst),
        "solver_dev_max": ctl_solver,
        "dt_digits_example": fin(dt["example"]["digits"], -99.0),
        "dt_gap_example_h1e2": dt["example"]["gap_h1e-2"], "dt_gap_example_h1e3": dt["example"]["gap_h1e-3"],
        "dt_gap_example_exact": dt["example"]["gap_exact"],
        "dt_digits_instances_median": float(np.median(digits_inst)) if digits_inst else -99.0,
        "dt_digits_instances_min": float(min(digits_inst)) if digits_inst else -99.0,
        "dt_digits_instances_max": float(max(digits_inst)) if digits_inst else -99.0,
        "dt_digits_instances_n": len(digits_inst),
        "conditions_met": sum(conditions.values()), "conditions": len(conditions),
        "controls_passed": sum(controls.values()), "controls": len(controls),
        "test_passed": test_passed,
    }
    for kk, vv in out.items():
        if isinstance(vv, float) and not math.isfinite(vv):
            raise AssertionError(f"{kk}: not finite")
    detail.update({
        "conditions": conditions, "controls": controls, "timing": timing,
        "example": {"s": [str(x) for x in s_ex], "atoms": [[str(x) for x in a] for a in atoms_ex], "lambda": str(lam_ex),
                    "solutions": {r: ([str(x) for x in sol[r]] if sol[r] else None) for r in sol},
                    "solutions_float": {r: ([float(x) for x in sol[r]] if sol[r] else None) for r in sol},
                    "r3": {"supports": [p[0] for p in r3_passing], "atoms_round": r3_round,
                           "solution": [str(x) for x in r3_sol] if r3_sol else None,
                           "slack": [float(p[2]) for p in r3_passing]},
                    "passing_supports": {r: [p[0] for p in ex[r]["passing"]] for r in ex},
                    "slack": {r: (float(ex[r]["passing"][0][1]["slack"]) if ex[r]["passing"] else None) for r in ex},
                    "counts_1e5": [int(x) for x in run_ex["count"]], "events": run_ex["events"],
                    "E": {"early": E_early_ex, "late": E_late_ex, "longest": E_longest_ex},
                    "E_each_late": [float(x) for x in run_ex["E_each"][1]],
                    "spikes_to_12": [(int(k), t) for k, t in run_ex["spikes"]],
                    "raster": {str(n): raster[n] for n in raster}, "raster_dev": raster_dev,
                    "mp_dev": mp_dev, "fine_dev": fine_dev, "fault": {"E": fault["E"], "rates": list(fault["rates"])},
                    "first_spikes": [float(x) for x in run_ex["first"]], "last_spikes": [float(x) for x in run_ex["last"]],
                    "figure_1d": {str(n): {str(t): fig[n][t] for t in FIG_TIMES} for n in fig},
                    "alca_vs_figure": alca_fig, "slca_counts_at": counts_at,
                    "u_avg_1e5": [float(x) for x in run_ex["u_avg"]]},
        "instances": [{kk: vv for kk, vv in x.items() if not kk.startswith("_")} for x in inst],
        "discrete": dt,
    })
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
        sys.exit(f"tld2017: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
