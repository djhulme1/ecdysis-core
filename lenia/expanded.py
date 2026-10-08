#!/usr/bin/env python3
"""Lenia and Expanded Universe: do the patterns the author filed as replicators self-replicate? For an Ecdysis
receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:3b2e2dc1d3f95cae) is from Chan, "Lenia
and Expanded Universe" (ALIFE 2020, arXiv:2005.03742): "Using semi-automatic search e.g. genetic algorithm, we
discovered new phenomena like polyhedral symmetries, individuality, self-replication, emission, growth by ingestion,
and saw the emergence of "virtual eukaryotes" that possess internal division of labor and type differentiation." Its
registered test: refuted if none of the patterns the author's released catalogue files as replicators (Chakazul/Lenia
at adfc542: found/212.json's two named "replicator", one channel and two kernels; found/233s.json's patterns under
"reproduce" and "reproduce + emission", three channels) self-replicates: placed alone in a 256 x 256 periodic world
and run under its stored rule, as LeniaNDKC.py computes it, to t = 500, it never shows two separate parts (8-connected
sites whose channels sum above 0.1) each holding at least half its starting mass.

The test as registered counts 15 patterns, "13" in found/233s.json. The file holds 16 under those headings: 7 under
"reproduce", 6 under "reproduce + emission" and 3 more under a second "reproduce" heading further down, which the
count missed. All 18 are run; replicated counts the 18 and replicated_listed15 the 15 the count meant (212.json's
two and 233s.json's first 13), and test_passed and test_passed_listed15 give the verdict under each reading.

The inputs are the two pattern files and LeniaNDKC.py (v3.5, the author's simulator for many kernels and channels),
all at the same commit, MIT licence (Bert Chan), each checked against its SHA-256. LeniaNDKC.py is the
specification, and "LeniaNDKC.py:n" cites its lines; the simulation below is this module's own. Control a runs the
author's own Board and Automaton classes, taken from LeniaNDKC.py by their syntax tree and run without a display or a
GPU (as LeniaNDKC runs where reikna finds none: numpy in double precision), to show that the port computes what it
computes. Every rule was fixed before any seed existed; the seed is not used, as nothing here is random.

1. Reading a pattern file as LeniaNDKC reads it (read_found_animals, LeniaNDKC.py:1215-1222): the text with trailing
   commas and white space stripped, wrapped in [ ] and parsed as JSON. Its strings are headings and its objects
   patterns; a pattern belongs to the latest heading above it. The replicators are 212.json's patterns named
   "replicator" and 233s.json's patterns under a heading "reproduce" or "reproduce + emission", in file order.
   The negative controls are 212.json's first pattern (code OG2g, "Gyrorbium gyrans") and 233s.json's first under
   "stable".
2. A pattern's rule, as Board.from_data, data2params and set_channels make it (LeniaNDKC.py:109-125, 248-253, 91-107):
   one kernel per entry of params, in order, each with b (fractions), m, s, kn, h (default 1), r (default 1) and c
   [source, destination] (defaults: a channel's own kernels, then the cross kernels, in LeniaNDKC's order). 212.json
   is one channel with two kernels; 233s.json three channels, three own kernels each and one cross kernel per
   ordered pair (15). As load_found_animal_id loads it (LeniaNDKC.py:1253-1260, 1319-1356), every kernel takes the
   first kernel's R; the first kernel's T and gn hold for all (calc_once, LeniaNDKC.py:431-434).
3. Its cells, decoded as rle2cells and ch2val decode them in two dimensions (LeniaNDKC.py:146-151, 207-230): digits
   count, "p" to "y" prefix a two-letter value, "." and "b" are 0, "o" 255, "A" to "X" 1 to 24, a two-letter value
   (p - "p") 24 + (letter - "A" + 25), values / 255; "$" ends a row (a count before it adds empty rows); rows are
   padded with zeros to the longest. Each channel is placed alone in a periodic 256 x 256 world, centred as
   Board.add centres it (LeniaNDKC.py:259-279): row x of a channel of height h at world row (256 - h) // 2 + x,
   likewise for columns, values above 1e-10 copied.
4. The kernels, as calc_kernel and kernel_shell build them (LeniaNDKC.py:474-500, 377-385): with MID = 128 and the
   index arrays of np.mgrid reversed, X = (i - MID) / R, D = sqrt(sum of X^2); for a kernel with B = len(b) peaks,
   Br = B D / r, shell = (D < r) core(min(Br mod 1, 1)) b[min(floor(Br), B - 1)], normalised to sum 1 and transformed
   by np.fft.fftn. Cores (kernel_core[kn - 1], LeniaNDKC.py:339-344): polynomial (4q(1 - q))^4, exponential
   exp(4 - 1/(q(1 - q))), step and staircase; growths (growth_func[gn - 1], LeniaNDKC.py:345-349): polynomial
   2 max(0, 1 - (u - m)^2 / (9 s^2))^4 - 1, exponential and step. Every pattern here has kn = gn = 1, the
   polynomial pair.
5. One step, as calc_once takes it (LeniaNDKC.py:431-469, with its defaults: no soft clip, no Arita mode, no noise, no
   mask, no quantisation): every channel transformed by np.fft.fftn; for each kernel k in order, the potential
   np.fft.fftshift(real(np.fft.ifftn(K^_k F_source))), with the product in that order, the field G(potential, m_k,
   s_k), and D_destination += (dt h_k) field, n_destination += h_k; then each channel A + D / n (A itself where
   n = 0), clipped to [0, 1]. dt = 1 / T. Double precision throughout.
6. The measure, at the start and after every step: S, the channels summed in order; the parts are the components of
   the sites with S > 0.1, 8-connected, joined across the periodic edges (union of labels that touch across an edge
   or a corner); a part's mass is S summed over its sites; m0 is S summed over the whole world at the start. A
   pattern self-replicates at the first step at which two or more parts each hold at least m0 / 2; its time is
   step / T. A run stops there, at t = 500 (500 T steps), or when S sums to 0 (it died). The negative controls run
   to t = 500 and record the most such parts at once.
7. Controls, each of which must behave as stated (controls_passed counts those that do):
   a. the port and the author's own Board and Automaton (rules 2 to 5 as LeniaNDKC.py itself computes them) give
      the same world, bit for bit, after each of 20 steps, for each of the 18 replicators and both negative
      controls;
   b. the torus labelling on made-up worlds: a part across the left and right edges, one across the top and bottom,
      one across a corner, and one joined only diagonally are each one part; two blocks a column apart are two; a
      site exactly at 0.1 is not counted;
   c. the measure on two copies of each negative control placed half the world apart finds two parts of at least
      half one copy's mass, and on one copy it finds one;
   d. neither negative control self-replicates by the measure to t = 500.
   Two worker processes run the simulations; each depends on its pattern alone, and the results are gathered in a
   fixed order.

test_passed is 1 if at least one of the 18 self-replicates, else 0; test_passed_listed15 the same for the 15.

What it cannot check: the paper's own runs (its patterns are not identified, and these files came out five months
later); the author's GPU arithmetic (single precision, by reikna), which this module does not use, as LeniaNDKC does
not where no GPU is found; the other phenomena the sentence lists.

Writes results/outputs.json and results/detail.json.
"""

import ast
import copy
import hashlib
import itertools
import json
import os
import re
import sys
import time
import types
from fractions import Fraction
from multiprocessing import Pool

import numpy as np
import scipy.ndimage

INPUTS = (
    ("lenia_found_212.json", "b60231ebb26e7869abda17fe0a860cd07f8e6b9cf9299e8b16b2014b417088cc", 74933,
     "https://raw.githubusercontent.com/Chakazul/Lenia/adfc542939266de7f4bb7ebb552e8499701ee107/Python/found/212.json"),
    ("lenia_found_233s.json", "d8631e9cd68067566eed018052d10fd07e9a4c5284dd270705f8dc639589476b", 969848,
     "https://raw.githubusercontent.com/Chakazul/Lenia/adfc542939266de7f4bb7ebb552e8499701ee107/Python/found/233s.json"),
    ("LeniaNDKC.py", "ffd8e4cc83156f44fb8f3ceae64c79517636713ce9414d2b9a49c397a9c61e99", 164855,
     "https://raw.githubusercontent.com/Chakazul/Lenia/adfc542939266de7f4bb7ebb552e8499701ee107/Python/LeniaNDKC.py"),
)
RULES = {"lenia_found_212.json": (1, 2, 1), "lenia_found_233s.json": (3, 3, 1)}    # channels, own kernels, cross
REPLICATOR_HEADINGS = ("reproduce", "reproduce + emission")
N = 256
T_END = 500
THRESHOLD = 0.1
SHARE = 0.5
CONTROL_STEPS = 20
EPSILON = 1e-10
LISTED = 15
LIMIT = 200

OUTPUTS = (
    "patterns", "replicated", "replicated_listed15", "replicated_multi_kernel", "replicated_multi_channel",
    "replication_times", "died", "steps_run", "port_bit_identical", "port_max_abs_diff", "labelling_cases_ok",
    "two_copies_ok", "negative_max_parts", "controls_passed", "controls_total", "test_passed",
    "test_passed_listed15",
)


class Refused(Exception):
    """An input that is not what the rules say it must be."""


# ---------------------------------------------------------------- reading the catalogue

def read_found(text):
    """Rule 1: the file as LeniaNDKC reads it, as a list of (heading or None, pattern) in order."""
    data = json.loads("[" + text.rstrip(", \n\r\t") + "]")
    out, heading = [], None
    for x in data:
        if isinstance(x, str):
            heading = x
        elif isinstance(x, dict):
            out.append((heading, x))
        else:
            raise Refused(f"an entry that is neither a heading nor a pattern: {x!r}"[:200])
    return out


def ch2val(c):
    if c in ".b":
        return 0
    if c == "o":
        return 255
    if len(c) == 1:
        return ord(c) - ord("A") + 1
    return (ord(c[0]) - ord("p")) * 24 + (ord(c[1]) - ord("A") + 25)


def rle2cells(st):
    """Rule 3: one channel's cells, as LeniaNDKC's rle2cells decodes them in two dimensions."""
    rows, row = [], []
    last, count = "", ""
    for ch in st.rstrip("!") + "$":
        if ch.isdigit():
            count += ch
        elif ch in "pqrstuvwxy@":
            last = ch
        else:
            if last + ch == "$":
                rows.append(row)
                if count != "":
                    rows.extend([[]] * (int(count) - 1))
                row = []
            elif last + ch in ("%", "#") or last == "@":
                raise Refused(f"a delimiter of more than two dimensions: {last + ch!r}")
            else:
                if last == "" and not ("A" <= ch <= "X" or ch in ".bo"):
                    raise Refused(f"an unexpected character in cells: {ch!r}")
                if last != "" and not ("A" <= ch <= "X"):
                    raise Refused(f"an unexpected two-letter value: {last + ch!r}")
                v = ch2val(last + ch) / 255
                row.extend([v] * (int(count) if count != "" else 1))
            last, count = "", ""
    width = max((len(r) for r in rows), default=0)
    return np.asarray([r + [0] * (width - len(r)) for r in rows], dtype=float).reshape(len(rows), width)


class Kernel:
    """One kernel of a rule: b, m, s, kn, gn, h, r, c [source, destination], T and R."""


def rule_of(pattern, channels, own, cross):
    """Rule 2: the kernels in order, each with its source and destination channel."""
    params = pattern["params"]
    if not isinstance(params, list):
        params = [params] * (own * channels + cross * channels * (channels - 1))
    if len(params) != own * channels + cross * channels * (channels - 1):
        raise Refused(f"{len(params)} kernels where the rule has {own * channels + cross * channels * (channels - 1)}")
    defaults = [[c0, c0] for c0 in range(channels) for _ in range(own)]
    defaults += [[c0, c1] for c0 in range(channels) for c1 in range(channels) if c0 != c1 for _ in range(cross)]
    kernels = []
    for p, d in zip(params, defaults):
        k = Kernel()
        k.b = [float(Fraction(x)) for x in p["b"].split(",")]
        k.m, k.s, k.kn, k.gn, k.T, k.R = p["m"], p["s"], p["kn"], p["gn"], p["T"], p["R"]
        k.h = p.get("h", 1)
        k.r = p.get("r", 1)
        k.c = list(p.get("c", d))
        if not (0 <= k.c[0] < channels and 0 <= k.c[1] < channels):
            raise Refused(f"a kernel's channels {k.c} outside 0..{channels - 1}")
        kernels.append(k)
    cells = pattern["cells"]
    if not isinstance(cells, list):
        cells = [cells] * channels
    if len(cells) != channels:
        raise Refused(f"{len(cells)} channels of cells where the rule has {channels}")
    return kernels, [rle2cells(c) for c in cells]


# ---------------------------------------------------------------- the port

CORES = (lambda q: (4 * q * (1 - q)) ** 4,
         lambda q: np.exp(4 - 1 / (q * (1 - q))),
         lambda q, a=1 / 4: (q >= a) * (q <= 1 - a),
         lambda q, a=1 / 4: (q >= a) * (q <= 1 - a) + (q < a) * 0.5)
GROWTHS = (lambda u, m, s: np.maximum(0, 1 - (u - m) ** 2 / (9 * s ** 2)) ** 4 * 2 - 1,
           lambda u, m, s: np.exp(- (u - m) ** 2 / (2 * s ** 2)) * 2 - 1,
           lambda u, m, s: (np.abs(u - m) <= s) * 2 - 1)


def placed(cells_list, n=N):
    """Rule 3: each channel centred alone in an empty n x n world."""
    world = []
    for cells in cells_list:
        A = np.zeros((n, n))
        h, w = cells.shape
        if h > n or w > n:
            raise Refused("a pattern larger than the world")
        r0, c0 = (n - h) // 2, (n - w) // 2
        for i in range(h):
            for j in range(w):
                if cells[i, j] > EPSILON:
                    A[(r0 + i) % n, (c0 + j) % n] = cells[i, j]
        world.append(A)
    return world


def kernel_ffts(kernels, n=N):
    """Rule 4."""
    R = kernels[0].R
    mid = int(n / 2)
    I = list(reversed(np.mgrid[(slice(0, n), slice(0, n))]))
    X = [(i - mid) / R for i in I]
    D = np.sqrt(sum([x ** 2 for x in X]))
    out = []
    for k in kernels:
        B = len(k.b)
        Br = B * D / k.r
        bs = np.asarray(k.b)
        bv = bs[np.minimum(np.floor(Br).astype(int), B - 1)]
        with np.errstate(divide="ignore", invalid="ignore"):
            shell = (D < k.r) * CORES[k.kn - 1](np.minimum(Br % 1, 1)) * bv
        out.append(np.fft.fftn(shell / shell.sum()))
    return out


class Port:
    """Rules 2 to 5 for one pattern."""

    def __init__(self, kernels, cells_list, n=N):
        self.kernels = kernels
        self.C = len(cells_list)
        self.A = placed(cells_list, n)
        self.K = kernel_ffts(kernels, n)
        self.dt = 1 / kernels[0].T
        self.G = GROWTHS[kernels[0].gn - 1]

    def step(self):
        A = self.A
        F = [np.fft.fftn(A[c]) for c in range(self.C)]
        D = [np.zeros(A[c].shape) for c in range(self.C)]
        Dn = [0] * self.C
        for k, kp in enumerate(self.kernels):
            c0, c1 = kp.c
            potential = np.fft.fftshift(np.real(np.fft.ifftn(np.multiply(self.K[k], F[c0]))))
            field = self.G(potential, kp.m, kp.s)
            D[c1] += self.dt * kp.h * field
            Dn[c1] += kp.h
        new = [A[c] + D[c] / Dn[c] if Dn[c] > 0 else A[c] for c in range(self.C)]
        self.A = [np.clip(a, 0, 1) for a in new]

    def total(self):
        S = self.A[0].copy()
        for c in range(1, self.C):
            S = S + self.A[c]
        return S


# ---------------------------------------------------------------- the measure

STRUCTURE = np.ones((3, 3), dtype=int)


def part_masses(S, threshold=THRESHOLD):
    """Rule 6: the masses of the parts of S above the threshold, 8-connected on the torus."""
    lab, n = scipy.ndimage.label(S > threshold, structure=STRUCTURE)
    if n == 0:
        return np.zeros(0)
    parent = np.arange(n + 1)

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    rows, cols = lab.shape
    pairs = []
    for d in (-1, 0, 1):
        pairs.append(np.stack([lab[0, :], np.roll(lab[rows - 1, :], -d)], axis=1))
        pairs.append(np.stack([lab[:, 0], np.roll(lab[:, cols - 1], -d)], axis=1))
    pairs = np.concatenate(pairs)
    pairs = pairs[(pairs[:, 0] > 0) & (pairs[:, 1] > 0)]
    for a, b in np.unique(pairs, axis=0).tolist():
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    roots = np.array([find(a) for a in range(n + 1)])
    masses = np.bincount(roots[lab].ravel(), weights=S.ravel(), minlength=n + 1)
    return masses[np.unique(roots[1:])]


def big_parts(S, m0):
    return int(np.sum(part_masses(S) >= SHARE * m0))


def simulate(task):
    """Rules 5 and 6 for one pattern: (outcome, step, t, most parts, m0)."""
    kernels, cells_list, full = task
    port = Port(kernels, cells_list)
    S = port.total()
    m0 = float(S.sum())
    if m0 <= 0:
        raise Refused("a pattern with no mass")
    T = kernels[0].T
    most = big_parts(S, m0)
    if most >= 2 and not full:
        return ("replicated", 0, 0.0, most, m0)
    for step in range(1, T_END * T + 1):
        port.step()
        S = port.total()
        if S.sum() == 0:
            return ("died", step, step / T, most, m0)
        k = big_parts(S, m0)
        most = max(most, k)
        if k >= 2 and not full:
            return ("replicated", step, step / T, most, m0)
    return ("persisted", T_END * T, float(T_END), most, m0)


# ---------------------------------------------------------------- the author's own classes (control a)

def author_classes(source, channels, own, cross, n=N):
    """Board and Automaton, taken from LeniaNDKC.py by its syntax tree and run in a namespace holding the globals
    they read, for two dimensions, an n x n world and this rule; no display, no GPU, nothing printed."""
    tree = ast.parse(source)
    wanted = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name in ("Board", "Automaton")]
    if [node.name for node in wanted] != ["Board", "Automaton"]:
        raise Refused("LeniaNDKC.py does not define Board and Automaton as expected")
    mid = int(n / 2)
    size_2 = int(np.log2(n))
    ns = {
        "np": np, "scipy": scipy, "copy": copy, "itertools": itertools, "Fraction": Fraction,
        "DIM": 2, "DIM_DELIM": {0: "", 1: "$", 2: "%", 3: "#", 4: "@A", 5: "@B", 6: "@C", 7: "@D", 8: "@E", 9: "@F"},
        "X_AXIS": -1, "Y_AXIS": -2, "Z_AXIS": -3, "SIZE": [n, n], "MID": [mid, mid], "SIZEX": n, "SIZEY": n,
        "MIDX": mid, "MIDY": mid, "SIZER": mid, "SIZETH": n, "SIZEF": mid,
        "DEF_R": int(np.power(2.0, size_2 - 6) * 2 * 5), "CN": channels, "KN": own, "XN": cross,
        "CHANNEL": range(channels), "KERNEL": range(own * channels + cross * channels * (channels - 1)),
        "EPSILON": EPSILON, "ROUND": 10, "STATUS": [], "args": types.SimpleNamespace(G=False), "reikna": None,
        "print": lambda *a, **k: None, "__name__": "lenia_ndkc_classes",
    }
    exec(compile(ast.Module(body=wanted, type_ignores=[]), "LeniaNDKC.py", "exec"), ns)
    return ns["Board"], ns["Automaton"]


def author_world(classes, pattern, n=N):
    """The world and automaton as load_found_animal_id leaves them (LeniaNDKC.py:1253-1260, 1319-1371)."""
    Board, Automaton = classes
    world = Board([n, n])
    part = Board.from_data(pattern)
    R = part.params[0]["R"]
    world.params = [{**part.params[k], "R": R} for k in range(len(part.params))]
    world.names = part.names.copy()
    automaton = Automaton(world)
    world.clear()
    automaton.reset()
    tx = {"shift": [0, 0], "rotate": [0] * 3, "R": world.params[0]["R"], "flip": -1}
    world.add_transformed(part, tx)
    return world, automaton


def compare(task):
    """Control a for one pattern: (bit-identical after every step, largest absolute difference)."""
    source, rule, pattern = task
    kernels, cells = rule_of(pattern, *rule)
    port = Port(kernels, cells)
    world, automaton = author_world(author_classes(source, *rule), pattern)
    same, worst = True, 0.0
    for c in range(port.C):
        same &= np.array_equal(world.cells[c], port.A[c])
        worst = max(worst, float(np.max(np.abs(world.cells[c] - port.A[c]))))
    for _ in range(CONTROL_STEPS):
        port.step()
        automaton.calc_once()
        for c in range(port.C):
            same &= np.array_equal(world.cells[c], port.A[c])
            worst = max(worst, float(np.max(np.abs(world.cells[c] - port.A[c]))))
    return bool(same), worst


# ---------------------------------------------------------------- control b: labelling on made-up worlds

def labelling_cases():
    n = 16
    cases = []
    S = np.zeros((n, n)); S[5:8, 0:2] = 1; S[5:8, n - 2:] = 1
    cases.append(("across the left and right edges", S, 1))
    S = np.zeros((n, n)); S[0:2, 4:7] = 1; S[n - 1, 4:7] = 1
    cases.append(("across the top and bottom", S, 1))
    S = np.zeros((n, n)); S[0, 0] = 1; S[n - 1, n - 1] = 1
    cases.append(("across a corner", S, 1))
    S = np.zeros((n, n)); S[3, 3] = 1; S[4, 4] = 1; S[5, 5] = 1
    cases.append(("joined only diagonally", S, 1))
    S = np.zeros((n, n)); S[4:9, 2:5] = 1; S[4:9, 6:9] = 1
    cases.append(("two blocks a column apart", S, 2))
    S = np.zeros((n, n)); S[4:9, 2:5] = 1; S[4:9, 5] = THRESHOLD; S[4:9, 6:9] = 1
    cases.append(("a column exactly at the threshold between them", S, 2))
    return [(name, len(part_masses(S)), want) for name, S, want in cases]


def two_copies(kernels, cells_list):
    """Control c: two copies half the world apart, against one."""
    one = Port(kernels, cells_list)
    S1 = one.total()
    m1 = float(S1.sum())
    S2 = S1 + np.roll(S1, N // 2, axis=1)
    return big_parts(S1, m1), int(np.sum(part_masses(S2) >= SHARE * m1))


# ---------------------------------------------------------------- the run

def summarise(values):
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters")
    return out


def load(directory):
    texts = {}
    for name, sha, size, _ in INPUTS:
        path = os.path.join(directory, name)
        with open(path, "rb") as f:
            data = f.read()
        got = hashlib.sha256(data).hexdigest()
        if got != sha or len(data) != size:
            raise Refused(f"{path}: sha256 {got} and {len(data)} bytes, not the committed {sha} and {size}")
        texts[name] = data.decode("utf-8")
    return texts


def selection(texts):
    """Rule 1: the replicators in order, as (file, pattern, listed among the 15), and the two negative controls."""
    reps, negatives = [], []
    r212 = read_found(texts["lenia_found_212.json"])
    r233 = read_found(texts["lenia_found_233s.json"])
    for _, p in r212:
        if p.get("name") == "replicator":
            reps.append(("lenia_found_212.json", p))
    in233 = [p for heading, p in r233 if heading in REPLICATOR_HEADINGS]
    reps += [("lenia_found_233s.json", p) for p in in233]
    if not r212 or r212[0][1].get("code") != "OG2g":
        raise Refused("212.json's first pattern is not OG2g")
    negatives.append(("lenia_found_212.json", r212[0][1]))
    stable = [p for heading, p in r233 if heading == "stable"]
    if not stable:
        raise Refused("233s.json has no pattern under \"stable\"")
    negatives.append(("lenia_found_233s.json", stable[0]))
    return reps, negatives


def fmt_t(outcome, t):
    return (f"{t:g}" if outcome == "replicated" else "-")


def run(inputs="inputs", log=print, workers=2):
    started = time.monotonic()
    texts = load(inputs)
    reps, negatives = selection(texts)
    values, controls, detail = {}, [], {}

    def at():
        return f"at {time.monotonic() - started:.0f} s"
    log(f"expanded: {len(reps)} replicators ({sum(1 for f, _ in reps if f == 'lenia_found_212.json')} in 212.json), "
        f"{len(negatives)} negative controls")

    rules = [(f, p, rule_of(p, *RULES[f])) for f, p in reps + negatives]
    tasks = [(k, c, False) for _, _, (k, c) in rules[:len(reps)]] + [(k, c, True) for _, _, (k, c) in rules[len(reps):]]
    with Pool(workers) as pool:
        results = pool.map(simulate, tasks, chunksize=1)
        log(f"expanded: simulations done, {at()}")
        compared = pool.map(compare, [(texts["LeniaNDKC.py"], RULES[f], p) for f, p in reps + negatives], chunksize=1)
    log(f"expanded: control a done, {at()}")
    rep_results, neg_results = results[:len(reps)], results[len(reps):]

    replicated = [r[0] == "replicated" for r in rep_results]
    kinds = [f for f, _ in reps]
    values.update({
        "patterns": len(reps),
        "replicated": sum(replicated),
        "replicated_listed15": sum(replicated[:LISTED]),
        "replicated_multi_kernel": sum(r for r, f in zip(replicated, kinds) if f == "lenia_found_212.json"),
        "replicated_multi_channel": sum(r for r, f in zip(replicated, kinds) if f == "lenia_found_233s.json"),
        "replication_times": ",".join(fmt_t(r[0], r[2]) for r in rep_results),
        "died": sum(1 for r in rep_results if r[0] == "died"),
        "steps_run": sum(r[1] for r in results),
    })
    detail["replicators"] = [{"file": f, "code": p.get("code"), "name": p.get("name"), "outcome": r[0], "step": r[1],
                              "t": r[2], "most_parts": r[3], "m0": r[4], "listed": i < LISTED}
                             for i, ((f, p), r) in enumerate(zip(reps, rep_results))]
    detail["negative_controls"] = [{"file": f, "code": p.get("code"), "name": p.get("name"), "outcome": r[0],
                                    "most_parts": r[3], "m0": r[4]} for (f, p), r in zip(negatives, neg_results)]

    identical = sum(1 for s, _ in compared if s)
    worst = max(w for _, w in compared)
    values.update({"port_bit_identical": identical, "port_max_abs_diff": worst})
    controls.append({"control": "a: the port equals the author's Board and Automaton bit for bit for 20 steps",
                     "passed": identical == len(compared), "identical": identical, "of": len(compared),
                     "max_abs_diff": worst})

    cases = labelling_cases()
    ok = sum(1 for _, got, want in cases if got == want)
    values["labelling_cases_ok"] = ok
    controls.append({"control": "b: the torus labelling on made-up worlds", "passed": ok == len(cases),
                     "cases": [{"case": n, "parts": g, "want": w} for n, g, w in cases]})

    copies = [two_copies(*rule) for _, _, rule in rules[len(reps):]]
    copies_ok = all(one == 1 and two == 2 for one, two in copies)
    values["two_copies_ok"] = int(copies_ok)
    controls.append({"control": "c: two copies of each negative control measure as two parts, one copy as one",
                     "passed": copies_ok, "found": [{"one": a, "two": b} for a, b in copies]})

    most = max(r[3] for r in neg_results)
    values["negative_max_parts"] = most
    controls.append({"control": "d: neither negative control self-replicates by the measure to t = 500",
                     "passed": most < 2, "outcomes": [r[0] for r in neg_results]})

    values.update({"controls_passed": sum(1 for c in controls if c["passed"]), "controls_total": len(controls)})
    values["test_passed"] = int(values["replicated"] >= 1)
    values["test_passed_listed15"] = int(values["replicated_listed15"] >= 1)
    detail.update({"controls": controls, "seconds": round(time.monotonic() - started, 1),
                   "world": N, "t_end": T_END, "threshold": THRESHOLD, "share": SHARE})
    log(f"expanded: {values['replicated']} of {len(reps)} replicated ({values['replicated_listed15']} of {LISTED}); "
        f"controls {values['controls_passed']}/{values['controls_total']}, {at()}")
    return summarise(values), detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, detail = run(log=lambda line: print(line, file=sys.stderr, flush=True))
    except Refused as e:
        sys.exit(f"lenia/expanded.py: refused: {e}")
    os.makedirs("results", exist_ok=True)
    with open(os.path.join("results", "outputs.json"), "w", encoding="ascii") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(os.path.join("results", "detail.json"), "w", encoding="ascii") as f:
        json.dump(detail, f, indent=1, sort_keys=True)
        f.write("\n")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
