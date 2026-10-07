#!/usr/bin/env python3
"""The packing chromatic number of the infinite square grid is 15: Martin et al.'s 15-colouring checked exactly, the
reduction to the formula checked clause by clause, the split's cover checked twice, and Subercaseaux and Heule's
proof sampled and re-checked, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:18c6f5de78f846d3) is from Subercaseaux and
Heule, "The Packing Chromatic Number of the Infinite Square Grid is 15" (TACAS 2023, arXiv:2301.09757). Its registered
test: the packing chromatic number of the infinite square grid is 15. Refuted by any of: a packing colouring of Z^2
with 14 colours; the 72x72 periodic 15-colouring of Martin et al. (arXiv:1510.02374v3) having two cells of colour c
within l1 distance c; or, for the paper's radius-15, 14-colour instance with colour 6 at the centre, a cube of its
split (5,217,031 cubes) whose formula is satisfiable or whose proof fails a verified checker, or the cubes failing to
cover the search space.

The inputs, each checked against its SHA-256 and size before anything else runs (see INPUTS): Martin, Raimondi, Chen
and Martin's LaTeX source as arXiv serves it (1510.02374v3, a gzipped tar, read as data; nothing in it is run); from
the authors' repository bsubercaseaux/PackingChromaticTacas at commit 305d6aa, formulas/P15_14_6_S5.cnf (the formula
F: the plus encoding of the radius-15 diamond with 14 colours, colour 6 at the centre and five layers of symmetry
breaking) and placements/placement-15-14-plus (its regions); and, as in hexagon/check.py, whose code this module
imports, CaDiCaL 2.1.3's source as Debian archived it and the two files of the CakeML-verified LRAT checker cake_lpr.
No input is executed as given: the solver and the checker are compiled from source into results/build by the run, in
the pinned image, with no network. Every rule below was fixed before any seed existed.

1. The witness. In PackingCromaticNumberDAM.tex, the figure labelled fig:15 must hold exactly one tabular, with 72
   columns "c", whose rows are 72 integers joined by "&" and ended by "\\", and nothing else. The table must be 72 x
   72 with every entry in 1..15. Read as the colouring (x, y) -> T[x mod 72][y mod 72] of Z^2, it is a packing
   colouring when no two cells of a colour c are within l1 distance c: for every cell and every offset d with
   1 <= |d|_1 <= c (its colour), the cell at d (mod 72 both ways) must not have colour c. As |d|_1 <= 15 < 72, no
   offset wraps onto its own cell, so this is exactly the condition on the plane. witness_ok needs a 72 x 72 table,
   colours in 1..15 and no violation; beside it, how many colours are used, their counts, and each colour's closest
   pair (at least c + 1 when it holds).
2. The reduction, reported beside the test. Every clause of F must be justified by the direct encoding D(15,14,6) of
   the definition (cells of the l1 ball of radius 15; cell number n in the authors' order, i from -15 to 15 then j,
   colour c the variable 14n + c; a region variable r stands for "some cell of its region has its colour"): an
   at-least-one-colour clause of a cell; two cells u != v of colour c with d(u, v) <= c; the centre unit (colour 6 at
   (0, 0)); a membership clause r v -x(v, c) (these clauses define the regions: each region variable's cells and
   colour come from them, and must equal the placement's, in its order); -r v -x(u, c) for a cell u outside r's
   region and within c of all of it; -r v -s for two disjoint regions of colour c all within c of each other; or one
   of the 329 symmetry-breaking clauses of the paper's five layers, exactly. Then a packing colouring of the diamond
   turns into a model of F: map it by the square's symmetry that puts the highest layer colour t (14 down to 10)
   found in the ball of radius t // 2 into the octant 0 <= i <= j (it is there at most once), and set every r to the
   "or" of its region. formula_unjustified counts the clauses that are none of these (0 when it holds). It replaces
   the authors' symmetry and re-encoding proofs (their Lemma 3; Lemma 8 of arXiv v2) by this argument.
3. The cubes. The split is the paper's Algorithm 1 (the authors' structured_api.py, cubes()) with P = 6, T = 7,
   R = 9: the colours 14 down to 8 (6, at the centre, is not among them); for each, its R regions with the least sum
   of distances of their cells to the centre, ties kept in placement order (the same nine as the paper's least
   distance: for every colour the regions with centres (0,0), (-1,2), (2,1), (1,-2), (-2,-1), (1,3), (3,-1),
   (-1,-3), (-3,1)); then for p = 6 down to 0, for each set of p colours (itertools.combinations order), for each
   choice of one of its R regions per colour (itertools.product order), a cube of those p region variables, with the
   negations of all R regions of every other split colour when p < 6. They are regenerated in that order and
   numbered from 1: there must be 5,217,031, with 59,038,434 literals; cubes_sha256 is the SHA-256 of their text as
   iCNF lines "a <literals> 0".
4. The proof, sampled. CUBES cubes are drawn without replacement, uniformly, by the seed. For each, F with the cube's
   literals added as unit clauses is solved by CaDiCaL with its LRAT proof streamed down a pipe into cake_lpr, as in
   hexagon/check.py. A cube counts as UNSAT when CaDiCaL reports UNSATISFIABLE and as verified when cake_lpr then
   reports "s VERIFIED UNSAT" on F with that cube. A cube that reaches CAP_CONFLICTS conflicts, or CAP_SECONDS of
   wall-clock time, is stopped and counted as timed out: a timeout is not a refutation, and it is not a failure, but
   the test needs none. A satisfiable cube has its model checked against F and the cube's units; a checked model
   would refute the claim. A check that runs out of cake_lpr's heap or stack is repeated alone with a larger one.
5. The cover (Lemma 1 of the TACAS paper, Lemma 6 of arXiv v2), completely, twice. (a) Exactly: every cube must have,
   for each split colour, one positive literal, the negations of all R of its regions, or none of its literals. Then
   a cube is satisfied by every assignment that satisfies it on the minimal assignment with, for each colour, no
   region true or only its least true region; so the cubes cover every assignment of the 63 split variables if they
   cover the 10^7 minimal ones, and those are all marked, cube by cube. (b) By the verified checker, in ten parts:
   the negations of the cubes in which region t of colour 14 is positive, with the unit r(t, 14), for t = 1..9; and
   the negations of the cubes without colour 14, with the nine units -r(t, 14). The ten unit sets cover every
   assignment, and each part's clauses are negated cubes, so if each part is unsatisfiable, so are the negated cubes,
   and the cubes form a tautology. Each part is refuted by the resolution proof the paper's tautology part describes
   (the tree argument; written by this script, untrusted) and checked by cake_lpr. The cover needs no clause of F.
   One verified call on all 5,217,031 negated cubes does not fit in the sandbox: cake_lpr ran out of a 2,560 MB heap
   still reading them, and CaDiCaL had not refuted them after ten minutes. cover_ok needs (a), and (b) verified for
   all ten parts.
6. Controls, each of which must behave as stated (controls_passed counts those that do): the witness with a cell of
   colour 15 copied to l1 distance 15 across the torus's edge, and with a colour-1 cell copied next to a 1, must each
   fail; F with an added clause forbidding colour 6 at two cells at distance 7 must have it found unjustified; F
   without the at-least-one-colour clauses of the cells farther than WEAK_RADIUS from the centre must be satisfiable,
   with a model that satisfies every kept clause and violates at least one removed one (it must, unless F is
   satisfiable); hexagon's three pigeonhole proof controls (an LRAT proof accepted, and rejected without its last
   step or without a lemma that step cites); and the same split built small (SMALL: colours, regions, P) on fresh
   variables, whose negated cubes CaDiCaL refutes with a proof cake_lpr verifies (the paper's SAT call, at a size
   that fits), whose parts (split by its first colour, as in 5b) cake_lpr verifies, and which with one cube removed
   fails the exact check and has a part's proof rejected.
7. Randomness, only from ECDYSIS_SEED, as in hexagon/check.py: SHA-256(seed || "|" || "packing/cubes" || "|" ||
   counter) read 8 bytes at a time, big-endian; an integer below n by rejection. The solver's search is
   deterministic and the work is gathered in a fixed order; timings and conflict counts go to results/detail.json.

test_passed is 1 if witness_ok is 1 with all 15 colours used (a valid table with fewer would itself refute the lower
bound), every sampled cube that finished is UNSAT with a verified proof, none timed out, and cover_ok is 1; else 0.
The reduction (rule 2) and the controls are reported beside it.

What it cannot check:
- the lower bound's last step: Lemma 2 of the TACAS paper (Lemma 7 of arXiv v2: D(15,14,6) unsatisfiable implies
  chi >= 15) is a hand proof, trusted; it uses chi >= 14 from the authors' 2022 paper, not re-checked here;
- the whole proof: only CUBES of the 5,217,031 cubes are re-solved (seconds each, with a heavy tail); a sample this
  size would catch a defect shared by many cubes, not a single bad cube;
- the paper's formula exactly: the released P15_14_6_S5.cnf has no ALOD clauses, which the paper's P* includes. They
  only add constraints, so a cube unsatisfiable here is unsatisfiable there; the authors' timings were with them;
- the authors' runs: their proofs were not kept, so this re-solves with a later CaDiCaL rather than re-checks;
- the tools beyond themselves: cake_lpr is verified in CakeML down to its assembly, but its C wrapper, the compiler,
  the kernel and this script (the witness, the reduction and the exact cover check are plain Python) are trusted;
- the upper bound beyond the table: the colouring is checked as printed in the e-print, which is what the paper cites.

Writes results/outputs.json (the 20 values a receipt carries, numbers and strings of at most 200 characters) and
results/detail.json (every value computed). packing/README.md gives the inputs, outputs and runtime.
"""

import argparse
import hashlib
import importlib.util
import io
import itertools
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("packing_hexagon", os.path.join(HERE, "..", "hexagon", "check.py"))
H = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(H)
Refused = H.Refused

# The inputs, at inputs/<name>: (name, SHA-256, bytes, where it comes from). packing/README.md gives the URLs.
INPUTS = (
    ("arXiv-1510.02374v3.tar.gz", "a8539f6859d8a9c85a2611b832f654d8ef7fbc4932d7a17c93fe5fa120b9b1c2", 20068,
     "arXiv e-print 1510.02374v3 (Martin, Raimondi, Chen and Martin), LaTeX source"),
    ("P15_14_6_S5.cnf", "36deda618e7d17d3af2d7352de5ebf010ae76ba8ef7b08cf1c8a3c92d1149084", 1329373,
     "PackingChromaticTacas@305d6aa formulas/P15_14_6_S5.cnf"),
    ("placement-15-14-plus", "dcbfcecf8149303c71de4bab675df2e3c8fc29eb44d0e0db034ad5f8a267ea0d", 44901,
     "PackingChromaticTacas@305d6aa placements/placement-15-14-plus"),
) + tuple(i for i in H.INPUTS if i[0] in ("cadical_2.1.3.orig.tar.gz", "cake_lpr.S", "basis_ffi.c"))

TEX = "PackingCromaticNumberDAM.tex"     # the e-print's file with the table
LABEL = "fig:15"
WIDTH, MAX_COLOUR = 72, 15
RADIUS, COLOURS, CENTRE, LAYERS = 15, 14, 6, 5   # D(15, 14, 6), five symmetry-breaking layers
SPLIT_P, SPLIT_T, SPLIT_R = 6, 7, 9
CUBES_TOTAL, CUBE_LITERALS = 5217031, 59038434
CUBES = 1000                             # cubes re-solved and re-checked, drawn by the seed
CAP_CONFLICTS, CAP_SECONDS = 10_000_000, 1800    # a cube's limits; reaching either is a timeout
WEAK_RADIUS = 8                          # the weakened formula keeps at-least-one-colour clauses within this radius
SMALL = (4, 3, 3)                        # the small split of the controls: colours, regions per colour, P
WORKERS = 2
HEAP_MB, STACK_MB = 512, 256             # cake_lpr per cube (the cubes' proofs are small)
RETRY_HEAP_MB, RETRY_STACK_MB = 2560, 768
COVER_HEAP_MB, COVER_STACK_MB = 1536, 256    # cake_lpr per part of the cover, two at a time
CHECKER = "cake_lpr a36874a (CakeML-verified LRAT checker)"
LIMIT = 200

OUTPUTS = (
    "witness_ok", "witness_colours", "witness_counts", "witness_violations",
    "formula_unjustified",
    "cubes_total", "cubes_sha256", "cubes_sampled", "cubes_ids_head", "cubes_unsat", "cubes_verified",
    "cubes_timed_out", "cubes_sat",
    "cover_exact", "cover_parts_verified", "cover_ok",
    "controls_passed", "controls_total",
    "solver", "test_passed",
)


# ---------------------------------------------------------------- inputs

def load(directory, name):
    """The bytes of an input, after its SHA-256 and size are checked against INPUTS."""
    spec = next(i for i in INPUTS if i[0] == name)
    path = os.path.join(directory, name)
    with open(path, "rb") as f:
        data = f.read()
    got = hashlib.sha256(data).hexdigest()
    if got != spec[1] or len(data) != spec[2]:
        raise Refused(f"{path}: sha256 {got} and {len(data)} bytes, not the committed {spec[1]} and {spec[2]}")
    return data


def tex_from_eprint(data):
    """The text of TEX from the e-print's gzipped tar, read in memory (nothing is extracted)."""
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            m = tar.getmember(TEX)
            if not m.isfile():
                raise Refused(f"e-print: {TEX} is not a regular file")
            return tar.extractfile(m).read().decode("utf-8")
    except (tarfile.TarError, KeyError) as e:
        raise Refused(f"e-print: no {TEX} in it ({e})") from None


# ---------------------------------------------------------------- rule 1: the witness

def parse_table(tex):
    """The table of the figure labelled LABEL: rows of integers joined by "&" and ended by "\\\\", refusing anything
    else in the figure's one tabular."""
    at = tex.find("\\label{%s}" % LABEL)
    if at < 0:
        raise Refused(f"{TEX}: no \\label{{{LABEL}}}")
    start = tex.rfind("\\begin{figure}", 0, at)
    if start < 0:
        raise Refused(f"{TEX}: \\label{{{LABEL}}} is not in a figure")
    tabs = re.findall(r"\\begin\{tabular\}\{([^}]*)\}(.*?)\\end\{tabular\}", tex[start:at], re.S)
    if len(tabs) != 1:
        raise Refused(f"{TEX}: the figure {LABEL} has {len(tabs)} tabulars, not one")
    spec, body = tabs[0]
    if spec != "c" * WIDTH:
        raise Refused(f"{TEX}: the tabular of {LABEL} is not {WIDTH} columns of c")
    rows = [r.strip() for r in body.split("\\\\")]
    if rows and rows[-1] == "":
        rows.pop()
    if not rows or not all(re.fullmatch(r"\d+(&\d+)*", r) for r in rows):
        raise Refused(f"{TEX}: a row of {LABEL} that is not integers joined by &")
    return [[int(x) for x in r.split("&")] for r in rows]


def offsets(c):
    """The offsets d with 1 <= |d|_1 <= c, each unordered pair once (d > 0 in (i, j) order)."""
    return [(di, dj) for di in range(0, c + 1) for dj in range(-c, c + 1)
            if 0 < abs(di) + abs(dj) <= c and (di > 0 or dj > 0)]


def witness(grid):
    """Rule 1 on a table: a dict of the counts and witness_ok."""
    n = len(grid)
    square = n == WIDTH and all(len(r) == WIDTH for r in grid)
    in_range = all(1 <= v <= MAX_COLOUR for r in grid for v in r)
    counts = {}
    for r in grid:
        for v in r:
            counts[v] = counts.get(v, 0) + 1
    violations, examples, closest = 0, [], {}
    if square and in_range:
        offs = {c: offsets(c) for c in counts}
        for i in range(n):
            for j in range(n):
                c = grid[i][j]
                for di, dj in offs[c]:
                    if grid[(i + di) % n][(j + dj) % n] == c:
                        violations += 1
                        if len(examples) < 3:
                            examples.append([i, j, (i + di) % n, (j + dj) % n, c])
        for c in sorted(counts):          # each colour's closest pair, by offsets of growing norm (< n / 2)
            cells = [(i, j) for i in range(n) for j in range(n) if grid[i][j] == c]
            for dist in range(1, n // 2):
                ring = [(di, dj) for di in range(0, dist + 1) for dj in (dist - di, di - dist)
                        if di > 0 or dj > 0]
                if any(grid[(i + di) % n][(j + dj) % n] == c for i, j in cells for di, dj in ring):
                    closest[c] = dist
                    break
    ok = square and in_range and violations == 0
    return {"rows": n, "square": square, "in_range": in_range, "colours": len(counts),
            "counts": {str(c): counts[c] for c in sorted(counts)}, "violations": violations,
            "examples": examples, "closest": {str(c): d for c, d in sorted(closest.items())},
            "witness_ok": 1 if ok else 0}


# ---------------------------------------------------------------- the diamond, the formula and its regions

def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def diamond(radius=RADIUS):
    """The cells of the l1 ball, in the authors' order (i, then j, from -radius)."""
    return [(i, j) for i in range(-radius, radius + 1) for j in range(-radius, radius + 1) if abs(i) + abs(j) <= radius]


CELLS = diamond()
CELL_VARS = len(CELLS) * COLOURS        # 6,734


def x(cell, c):
    return CELLS.index(cell) * COLOURS + c


def decode(v):
    """(cell, colour) of a cell variable."""
    return CELLS[(v - 1) // COLOURS], (v - 1) % COLOURS + 1


def regions(formula):
    """{region variable: (colour, cells)} from the membership clauses r v -x(v, c) (r above CELL_VARS)."""
    found = {}
    for c in formula:
        if len(c) == 2 and max(c) > CELL_VARS and min(c) < 0 and -min(c) <= CELL_VARS:
            cell, colour = decode(-min(c))
            found.setdefault(max(c), []).append((cell, colour))
    out = {}
    for r, members in found.items():
        colours = {colour for _, colour in members}
        if len(colours) != 1:
            raise Refused(f"formula: region variable {r} has members of colours {sorted(colours)}")
        out[r] = (colours.pop(), frozenset(cell for cell, _ in members))
    return out


def check_placement(found, placement):
    """The regions F defines must be the placement's: colour c's region t is variable CELL_VARS + 1 + (its rank
    among the colours with regions) * count + t, cell for cell. Returns {colour: [variables in placement order]}."""
    try:
        table = {int(k): [frozenset((int(p[0]), int(p[1])) for p in region) for region in v]
                 for k, v in json.loads(placement).items()}
    except (ValueError, TypeError, IndexError, AttributeError) as e:
        raise Refused(f"placement: not the expected JSON ({e})") from None
    by_colour, nxt = {}, CELL_VARS + 1
    for c in sorted(table):
        by_colour[c] = list(range(nxt, nxt + len(table[c])))
        for v, cells in zip(by_colour[c], table[c]):
            if found.get(v) != (c, cells):
                raise Refused(f"formula: region variable {v} is not the placement's region of colour {c}")
        nxt += len(table[c])
    if sorted(found) != list(range(CELL_VARS + 1, nxt)):
        raise Refused("formula: its region variables are not the placement's")
    return by_colour


def symmetry_clauses(colours=COLOURS, layers=LAYERS, cells=None):
    """The paper's symmetry-breaking clauses, as sets: for each layer colour t (colours down), each cell of the ball
    of radius t // 2 outside the octant 0 <= i <= j gets -x(cell, t), or a higher layer colour h in the octant
    within h // 2."""
    cells = CELLS if cells is None else cells
    octant = lambda p: 0 <= p[0] <= p[1]   # noqa: E731
    out = set()
    for t in range(colours, colours - layers, -1):
        broken = [x(p, h) for h in range(t + 1, colours + 1) for p in cells if dist(p, (0, 0)) <= h // 2 and octant(p)]
        for p in cells:
            if dist(p, (0, 0)) <= t // 2 and not octant(p):
                out.add(frozenset(broken + [-x(p, t)]))
    return out


def classify(formula, found):
    """Rule 2: counts of F's clauses by the kind that justifies them, and the unjustified ones."""
    sym = symmetry_clauses()
    centre = (x((0, 0), CENTRE),)
    kinds = {k: 0 for k in ("at_least_one_colour", "distance", "centre", "membership", "region_cell",
                            "region_region", "symmetry")}
    bad = []
    def one_cell_all_colours(c):
        return len(c) == COLOURS and all(0 < lit <= CELL_VARS for lit in c) and \
            len({decode(lit)[0] for lit in c}) == 1 and \
            sorted(decode(lit)[1] for lit in c) == list(range(1, COLOURS + 1))

    def too_close(c):        # -x(u, k) v -x(v, k) with u != v and d(u, v) <= k
        if len(c) != 2 or not all(-CELL_VARS <= lit < 0 for lit in c):
            return False
        (u, a), (v, b) = decode(-c[0]), decode(-c[1])
        return a == b and u != v and dist(u, v) <= a

    for c in formula:
        if one_cell_all_colours(c):
            kinds["at_least_one_colour"] += 1
        elif c == centre:
            kinds["centre"] += 1
        elif too_close(c):
            kinds["distance"] += 1
        elif len(c) == 2 and max(c) > CELL_VARS and min(c) < 0 and -min(c) <= CELL_VARS:
            kinds["membership"] += 1      # defines the region (rule 2)
        elif len(c) == 2 and c[0] < 0 and c[1] < 0 and (-c[0] > CELL_VARS) != (-c[1] > CELL_VARS):
            r, v = max(-c[0], -c[1]), min(-c[0], -c[1])
            (cell, colour), (rc, members) = decode(v), found.get(r, (None, frozenset()))
            if colour == rc and cell not in members and all(dist(cell, m) <= colour for m in members):
                kinds["region_cell"] += 1
            else:
                bad.append(c)
        elif len(c) == 2 and c[0] < -CELL_VARS and c[1] < -CELL_VARS:
            (c1, m1), (c2, m2) = found.get(-c[0], (None, frozenset())), found.get(-c[1], (0, frozenset()))
            if c1 == c2 and not (m1 & m2) and all(dist(a, b) <= c1 for a in m1 for b in m2):
                kinds["region_region"] += 1
            else:
                bad.append(c)
        elif frozenset(c) in sym and len(set(c)) == len(c):
            kinds["symmetry"] += 1
        else:
            bad.append(c)
    return kinds, bad


# ---------------------------------------------------------------- rule 3: the split

class Split:
    """The paper's PTR split over var[k][t] (split colour k, its region t, in the order the cubes use), P at most."""

    def __init__(self, var, P):
        self.var, self.P, self.T, self.R = [list(v) for v in var], P, len(var), len(var[0])
        if any(len(v) != self.R for v in self.var):
            raise ValueError("every split colour needs the same number of regions")
        self.blocks, self.offset, off = [], {}, 0
        for p in range(P, -1, -1):
            for cmb in itertools.combinations(range(self.T), p):
                self.blocks.append((off, p, cmb))
                self.offset[cmb] = off
                off += self.R ** p
        self.total = off

    def literals(self, Q, S):
        """The cube for split colours Q (increasing) with regions S."""
        neg = [] if len(Q) == self.P else [-v for k in range(self.T) if k not in Q for v in self.var[k]]
        return [self.var[k][s] for k, s in zip(Q, S)] + neg

    def stream(self):
        """(Q, S, literals) for every cube, in order."""
        for _, p, cmb in self.blocks:
            neg = [] if p == self.P else [-v for k in range(self.T) if k not in cmb for v in self.var[k]]
            for S in itertools.product(range(self.R), repeat=p):
                yield cmb, S, [self.var[k][s] for k, s in zip(cmb, S)] + neg

    def unrank(self, i):
        """(Q, S) of cube number i (from 0)."""
        if not 0 <= i < self.total:
            raise IndexError(i)
        lo, hi = 0, len(self.blocks) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.blocks[mid][0] <= i:
                lo = mid
            else:
                hi = mid - 1
        off, p, cmb = self.blocks[lo]
        r, S = i - off, []
        for _ in range(p):
            S.append(r % self.R)
            r //= self.R
        return cmb, tuple(reversed(S))

    def rank(self, Q, S):
        v = 0
        for s in S:
            v = v * self.R + s
        return self.offset[tuple(Q)] + v


def split_variables(by_colour, found, colours=COLOURS, centre=CENTRE, T=SPLIT_T, R=SPLIT_R):
    """Algorithm 1's choice: the T colours from the highest (the centre's colour replaced by the next below), each
    with its R regions of least sum of distances to the centre, ties in placement order. Also whether the paper's
    least distance (its appendix) picks the same regions."""
    top = list(range(colours, colours - T, -1))
    if centre in top:
        top.append(min(top) - 1)
        top.remove(centre)
    var, same = [], True
    for c in top:
        vs = by_colour[c]
        by_sum = sorted(vs, key=lambda v: sum(dist(p, (0, 0)) for p in found[v][1]))
        by_min = sorted(vs, key=lambda v: min(dist(p, (0, 0)) for p in found[v][1]))
        var.append(by_sum[:R])
        same = same and set(by_sum[:R]) == set(by_min[:R]) and \
            sum(dist(p, (0, 0)) for p in found[by_sum[R - 1]][1]) < sum(dist(p, (0, 0)) for p in found[by_sum[R]][1])
    return top, var, same


# ---------------------------------------------------------------- rule 5: the cover

class Cover:
    """Rule 5a, fed one cube (a list of literals) at a time. Each colour of each cube must be one positive literal,
    all R negations or nothing; a minimal assignment is numbered by its colours' states (R for "no region")."""

    def __init__(self, split):
        self.owner = {v: (k, t) for k, vs in enumerate(split.var) for t, v in enumerate(vs)}
        self.T, self.R = split.T, split.R
        self.stride = [(self.R + 1) ** (self.T - 1 - k) for k in range(self.T)]
        self.marks = bytearray((self.R + 1) ** self.T)
        self.count = self.bad = 0

    def add(self, lits):
        self.count += 1
        pos, neg = {}, {}
        for lit in lits:
            k, t = self.owner.get(abs(lit), (None, None))
            if k is None:
                self.bad += 1
                return
            (pos if lit > 0 else neg).setdefault(k, set()).add(t)
        base, free, R, stride = 0, [], self.R, self.stride
        for k in range(self.T):
            p, n = pos.get(k, ()), neg.get(k, ())
            if len(p) == 1 and not n:
                base += next(iter(p)) * stride[k]
            elif not p and len(n) == R:
                base += R * stride[k]
            elif not p and not n:
                free.append(k)
            else:
                self.bad += 1
                return
        inner = free.pop() if free else None
        for states in itertools.product(range(R + 1), repeat=len(free)):
            b = base + sum(s * stride[k] for s, k in zip(states, free))
            if inner is None:
                self.marks[b] = 1
            else:
                self.marks[b:b + (R + 1) * stride[inner]:stride[inner]] = b"\x01" * (R + 1)

    def result(self):
        """(covered, details): covered needs every cube well formed and every minimal assignment marked."""
        missing = self.marks.count(0)
        example = None
        if missing:
            i = self.marks.index(0)
            example = [(i // self.stride[k]) % (self.R + 1) for k in range(self.T)]
        return self.bad == 0 and missing == 0, {"cubes": self.count, "malformed": self.bad,
                                                "assignments": len(self.marks), "uncovered": missing,
                                                "uncovered_example": example}


def cover_exact(split, cubes):
    """Rule 5a on an iterable of literal lists: (covered, details)."""
    c = Cover(split)
    for lits in cubes:
        c.add(lits)
    return c.result()


def part_of(Q, S, R):
    """The part of the cover a cube's negation goes to: its region of the first split colour, or R (none)."""
    return S[0] if Q and Q[0] == 0 else R


def part_units(split, part):
    return [(split.var[0][part],)] if part < split.R else [(-v,) for v in split.var[0]]


class Parts:
    """Clause numbers within each part's CNF: its units first, then its negated cubes in cube order."""

    def __init__(self, split):
        self.split, R = split, split.R
        self.offset = [{} for _ in range(R + 1)]
        self.size = [0] * (R + 1)
        for _, p, cmb in split.blocks:
            if cmb and cmb[0] == 0:
                for t in range(R):
                    self.offset[t][cmb] = self.size[t]
                    self.size[t] += R ** (p - 1)
            else:
                self.offset[R][cmb] = self.size[R]
                self.size[R] += R ** p
        self.units = [len(part_units(split, t)) for t in range(R + 1)]

    def id(self, Q, S):
        part = part_of(Q, S, self.split.R)
        v = 0
        for s in (S[1:] if part < self.split.R else S):
            v = v * self.split.R + s
        return self.units[part] + self.offset[part][tuple(Q)] + v + 1


def part_proof(split, parts, part, out):
    """Rule 5b's refutation of one part, as ASCII LRAT lines written to out: the lemma E(Q, S, m) = {-r(S_q, q)} +
    {r(t, k): k < m, k not in Q, any t}, for m = T - 1 down to 1, from E(Q, S, m + 1) and the E(Q + m, S + t, m + 1);
    E(Q, S, T) is the negated cube and a negated cube with P positives subsumes every E(Q, S, m). Then the empty
    clause from the part's units. Returns the number of lemmas."""
    T, R, P, var = split.T, split.R, split.P, split.var
    nid = parts.units[part] + parts.size[part]
    level = {}

    def ref(Q, S, m):
        return parts.id(Q, S) if len(Q) == P or m == T else level[m][(Q, S)]

    lemmas = 0
    for m in range(T - 1, 0, -1):
        level[m] = {}
        lines = []
        for p in range(0, min(m, P - 1) + 1):
            for Q in itertools.combinations(range(m), p):
                if (part < R) != (bool(Q) and Q[0] == 0):
                    continue
                for S in itertools.product(range(R), repeat=p):
                    if part < R and S[0] != part:
                        continue
                    lits = [-var[k][s] for k, s in zip(Q, S)] + [var[k][t] for k in range(m) if k not in Q
                                                                  for t in range(R)]
                    hints = [ref(Q + (m,), S + (t,), m + 1) for t in range(R)] + [ref(Q, S, m + 1)]
                    nid += 1
                    lemmas += 1
                    level[m][(Q, S)] = nid
                    lines.append("%d %s0 %s 0\n" % (nid, "".join("%d " % lit for lit in lits),
                                                     " ".join(map(str, hints))))
                    if len(lines) >= 10000:
                        out.write("".join(lines))
                        lines = []
        out.write("".join(lines))
        if m + 1 in level and level[m + 1]:
            out.write("%d d %s 0\n" % (nid, " ".join(map(str, sorted(level[m + 1].values())))))
            del level[m + 1]
    last = ref((0,), (part,), 1) if part < R else ref((), (), 1)
    out.write("%d 0 %s %d 0\n" % (nid + 1, " ".join(str(u) for u in range(1, parts.units[part] + 1)), last))
    return lemmas + 1


def write_parts(split, cubes, directory, header_vars):
    """Rule 5b's CNFs, one per part, from an iterable of (Q, S, literals); every clause's number is checked
    against Parts. Returns their paths."""
    parts = Parts(split)
    paths = [os.path.join(directory, f"cover-{t}.cnf") for t in range(split.R + 1)]
    files = [open(p, "wb") for p in paths]
    try:
        bufs = [[] for _ in paths]
        seen = [0] * len(paths)
        for t, f in enumerate(files):
            f.write(b"p cnf %d %d\n" % (header_vars, parts.units[t] + parts.size[t]))
            f.write(b"".join(b"%d 0\n" % u for (u,) in part_units(split, t)))
            seen[t] = parts.units[t]
        for Q, S, lits in cubes:
            t = part_of(Q, S, split.R)
            seen[t] += 1
            if parts.id(Q, S) != seen[t]:
                raise AssertionError(f"cover part {t}: clause {seen[t]} is numbered {parts.id(Q, S)}")
            bufs[t].append(b" ".join(b"%d" % -lit for lit in lits) + b" 0\n")
            if len(bufs[t]) >= 20000:
                files[t].write(b"".join(bufs[t]))
                bufs[t] = []
        for t, f in enumerate(files):
            f.write(b"".join(bufs[t]))
        if seen != [parts.units[t] + parts.size[t] for t in range(len(paths))]:
            raise AssertionError("cover parts: not every clause was written")
    finally:
        for f in files:
            f.close()
    return paths, parts


def check_part(tools, cnf, proof, heap=COVER_HEAP_MB, stack=COVER_STACK_MB):
    """cake_lpr on a part and its proof: (verified, its last line)."""
    r = subprocess.run([tools["cake_lpr"], f"--CML_HEAP_SIZE={heap}", f"--CML_STACK_SIZE={stack}", cnf, proof],
                       stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    said = (r.stdout + r.stderr).decode(errors="replace").strip().splitlines()
    return r.returncode == 0 and "s VERIFIED UNSAT" in r.stdout.decode(errors="replace").splitlines(), \
        (said[-1][:200] if said else "")


def verify_parts(tools, split, cubes, directory, header_vars, workers=WORKERS, heap=COVER_HEAP_MB):
    """Rule 5b: write the parts and their proofs to directory, have cake_lpr check each, remove the files."""
    os.makedirs(directory, exist_ok=True)
    paths, parts = write_parts(split, cubes, directory, header_vars)
    proofs, lemmas = [], []
    for t in range(split.R + 1):
        proofs.append(os.path.join(directory, f"cover-{t}.lrat"))
        with open(proofs[-1], "w") as f:
            lemmas.append(part_proof(split, parts, t, f))
    sizes = [(os.path.getsize(c), os.path.getsize(p)) for c, p in zip(paths, proofs)]
    with ThreadPoolExecutor(workers) as pool:
        results = list(pool.map(lambda cp: check_part(tools, cp[0], cp[1], heap), zip(paths, proofs)))
    for p in paths + proofs:
        os.unlink(p)
    return [{"part": f"r({t + 1} of the first colour)" if t < split.R else "none of the first colour",
             "clauses": parts.units[t] + parts.size[t], "lemmas": n, "cnf_bytes": a, "proof_bytes": b,
             "verified": ok, "checker_said": said}
            for t, (n, (a, b), (ok, said)) in enumerate(zip(lemmas, sizes, results))]


# ---------------------------------------------------------------- the solver, capped

def capped(tools, directory):
    """A copy of tools whose cadical stops at CAP_CONFLICTS conflicts or CAP_SECONDS (a shell script in
    directory, which must allow execution: results/build in the sandbox)."""
    path = os.path.join(directory, "cadical-capped")
    with open(path, "w") as f:
        f.write('#!/bin/sh\nexec "%s" -c %d -t %d "$@"\n' % (tools["cadical"], CAP_CONFLICTS, CAP_SECONDS))
    os.chmod(path, 0o755)
    return dict(tools, cadical=path)


def verdict(r):
    """A cube's outcome from hexagon's solve(): unsat (verified or not), sat, timeout (the solver stopped at its
    limits: exit 0, no answer) or error."""
    if r["answer"] in ("unsat", "sat"):
        return r["answer"]
    return "timeout" if r["solver_rc"] == 0 else "error"


# ---------------------------------------------------------------- controls

def witness_controls(grid):
    """Rule 6's two broken witnesses: (rows of the controls)."""
    n = len(grid)
    i, j = next((i, j) for i in range(n - 1, -1, -1) for j in range(n) if grid[i][j] == MAX_COLOUR)
    far = [r[:] for r in grid]
    far[(i + MAX_COLOUR) % n][j] = MAX_COLOUR          # i + 15 >= 72 for a 15 in the last rows: across the edge
    a, b = next((a, b) for a in range(n) for b in range(n) if grid[a][b] == 1)
    near = [r[:] for r in grid]
    near[a][(b + 1) % n] = 1
    rows = []
    for what, g, cell in (("a 15 copied to distance 15 across the torus's edge", far, [(i + MAX_COLOUR) % n, j]),
                          ("a 1 copied next to a 1", near, [a, (b + 1) % n])):
        w = witness(g)
        rows.append({"control": f"witness with {what}: fails", "cell": cell, "wraps": what.endswith("edge") and
                     i + MAX_COLOUR >= n, "passed": w["witness_ok"] == 0 and w["violations"] > 0,
                     "violations": w["violations"]})
    return rows


def small_split():
    """The small split of the controls, on variables 1..colours * regions."""
    T, R, P = SMALL
    return Split([[k * R + t + 1 for t in range(R)] for k in range(T)], P)


def small_controls(tools, work):
    """Rule 6's controls on the small split: the paper's SAT call verified; its parts' proofs verified; one cube
    removed caught by the exact check and by a part's proof."""
    sp = small_split()
    nv = sp.T * sp.R
    rows = []
    cnf = os.path.join(work, "small-negated.cnf")
    cubes = list(sp.stream())
    with open(cnf, "wb") as f:
        f.write(b"p cnf %d %d\n" % (nv, len(cubes)) + b"".join(b" ".join(b"%d" % -lit for lit in lits) + b" 0\n"
                                                              for _, _, lits in cubes))
    r = H.solve(tools, cnf, work, "small")
    rows.append({"control": f"small split {SMALL}: its {len(cubes)} negated cubes refuted by CaDiCaL, proof verified",
                 "passed": r["answer"] == "unsat" and r["verified"], "answer": r["answer"],
                 "checker_said": r["checker_said"]})
    parts = verify_parts(tools, sp, cubes, os.path.join(work, "small-parts"), nv, workers=1, heap=256)
    rows.append({"control": f"small split {SMALL}: its {sp.R + 1} parts' proofs verified",
                 "passed": all(p["verified"] for p in parts), "parts": len(parts)})
    gone = sp.total // 3                                  # a cube with P positives
    ok, info = cover_exact(sp, (lits for k, (_, _, lits) in enumerate(cubes) if k != gone))
    rows.append({"control": f"small split with cube {gone + 1} removed: the exact check finds it uncovered",
                 "passed": not ok and info["uncovered"] > 0, **info})
    keep = [c for k, c in enumerate(cubes) if k != gone]
    Q, S, _ = cubes[gone]
    t = part_of(Q, S, sp.R)
    d = os.path.join(work, "small-gone")
    os.makedirs(d, exist_ok=True)
    pc = os.path.join(d, "part.cnf")
    units = part_units(sp, t)
    with open(pc, "wb") as f:      # the part without the cube, with the proof written for the whole part
        mine = [lits for q, s, lits in keep if part_of(q, s, sp.R) == t]
        f.write(b"p cnf %d %d\n" % (nv, len(units) + len(mine)) + b"".join(b"%d 0\n" % u for (u,) in units) +
                b"".join(b" ".join(b"%d" % -lit for lit in lits) + b" 0\n" for lits in mine))
    pp = os.path.join(d, "part.lrat")
    with open(pp, "w") as f:
        part_proof(sp, Parts(sp), t, f)
    verified, said = check_part(tools, pc, pp, heap=256)
    rows.append({"control": f"small split with cube {gone + 1} removed: its part's proof rejected",
                 "passed": not verified, "checker_said": said})
    shutil.rmtree(d, ignore_errors=True)
    return rows


def weak_control(tools, formula, variables, work):
    """Rule 6: F without the at-least-one-colour clauses of the cells beyond WEAK_RADIUS, solved, its model
    checked."""
    far = {tuple(x(p, c) for c in range(1, COLOURS + 1)) for p in CELLS if dist(p, (0, 0)) > WEAK_RADIUS}
    keep = [c for c in formula if c not in far]
    gone = [c for c in formula if c in far]
    path = os.path.join(work, "weak.cnf")
    with open(path, "wb") as f:
        f.write(b"p cnf %d %d\n" % (variables, len(keep)) + H.clause_lines(keep))
    r = H.solve(tools, path, work, "weak", proof=False)
    os.unlink(path)
    kept = removed = None
    if r["answer"] == "sat":
        m = H.model(r["model"])
        kept, removed = H.satisfies(m, keep), H.satisfies(m, gone)
    return {"control": f"F without the {len(gone)} at-least-one-colour clauses beyond radius {WEAK_RADIUS}: "
                       "satisfiable, model checked",
            "passed": r["answer"] == "sat" and kept == 0 and removed > 0, "answer": r["answer"],
            "kept_clauses_violated": kept, "removed_clauses_violated": removed, "seconds": r["seconds"]}


# ---------------------------------------------------------------- the run

def summarise(values):
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters")
    return out


def run(seed, inputs="inputs", results="results", cubes_wanted=CUBES, tools=None, log=print):
    """Every rule, in order; returns (outputs, detail). tools, if given, replaces the build (tests only)."""
    started = time.monotonic()
    data = {name: load(inputs, name) for name, *_ in INPUTS}     # every input checked before anything runs
    detail = {"inputs": [{"name": n, "sha256": h, "bytes": b, "source": s} for n, h, b, s in INPUTS]}
    values = {}

    # Rule 1: the witness, and its controls.
    tex = tex_from_eprint(data["arXiv-1510.02374v3.tar.gz"])
    grid = parse_table(tex)
    w = witness(grid)
    log(f"packing: witness {w['rows']} rows, {w['colours']} colours, {w['violations']} violations, "
        f"closest pairs {w['closest']}")
    values.update({"witness_ok": w["witness_ok"], "witness_colours": w["colours"],
                   "witness_counts": ",".join(str(v) for v in w["counts"].values()),
                   "witness_violations": w["violations"]})
    controls = witness_controls(grid) if w["square"] and w["in_range"] else []
    detail["witness"] = dict(w, tex_sha256=hashlib.sha256(tex.encode("utf-8")).hexdigest())

    # Rule 2: the reduction.
    variables, formula, header, body = H.parse_cnf(data["P15_14_6_S5.cnf"], "formula")
    found = regions(formula)
    by_colour = check_placement(found, data["placement-15-14-plus"].decode("utf-8"))
    kinds, bad = classify(formula, found)
    values["formula_unjustified"] = len(bad)
    extra = formula + [(-x((0, 1), CENTRE), -x((0, 1 + CENTRE + 1), CENTRE))]       # colour 6, distance 7
    _, extra_bad = classify(extra, found)
    controls.append({"control": "F with a clause forbidding colour 6 at two cells 7 apart: found unjustified",
                     "passed": len(extra_bad) == 1, "unjustified": len(extra_bad)})
    log(f"packing: formula {header.decode()}, {len(found)} regions, clauses {kinds}, unjustified {len(bad)}")
    detail["formula"] = {"header": header.decode(), "regions": len(found), "kinds": kinds,
                         "unjustified": [list(c) for c in bad[:20]]}

    # Rule 3: the split.
    top, var, same = split_variables(by_colour, found)
    split = Split(var, SPLIT_P)
    if split.total != CUBES_TOTAL:
        raise Refused(f"split: {split.total} cubes, not {CUBES_TOTAL}")
    detail["split"] = {"colours": top, "regions": [[v - by_colour[c][0] + 1 for v in vs] for c, vs in zip(top, var)],
                       "region_centres": [[list(sorted(found[v][1])[2]) for v in vs] for vs in var[:1]],
                       "least_distance_same_regions": same}
    chosen = H.sample(seed, "packing/cubes", CUBES_TOTAL, cubes_wanted)
    units = {i: split.literals(*split.unrank(i)) for i in chosen}

    # The tools.
    os.makedirs(results, exist_ok=True)
    if tools is None:
        if platform.machine() not in ("x86_64", "AMD64"):
            raise SystemExit("packing/check.py: cake_lpr.S is x86-64 assembly; run this on an x86-64 machine")
        tools = H.build_tools(os.path.abspath(inputs), os.path.abspath(os.path.join(results, "build")))
        log(f"packing: built CaDiCaL {tools['cadical_version']} ({tools['cadical_files']} files) and cake_lpr, "
            f"gcc {tools['gcc']}, at {time.monotonic() - started:.0f} s")
    work = tempfile.mkdtemp(prefix="packing-")
    build = os.path.join(os.path.abspath(results), "build")
    os.makedirs(build, exist_ok=True)
    try:
        # Rules 3 and 5: one pass over the cubes, in order: counted, digested, checked for cover exactly and written
        # into the ten parts; the sampled cubes' literals compared with their unranked ones.
        digest, literals, sampled, exact = hashlib.sha256(), [0], {}, Cover(split)
        want = set(chosen)

        def every():
            for k, (Q, S, lits) in enumerate(split.stream()):
                digest.update(b"a " + b" ".join(b"%d" % lit for lit in lits) + b" 0\n")
                literals[0] += len(lits)
                exact.add(lits)
                if k in want:
                    sampled[k] = lits
                yield Q, S, lits

        parts_rows = verify_parts(tools, split, every(), os.path.join(os.path.abspath(results), "cover"), variables)
        ok_exact, info = exact.result()
        log(f"packing: cubes regenerated: {info['cubes']} ({literals[0]} literals), sha256 {digest.hexdigest()}")
        if literals[0] != CUBE_LITERALS or info["cubes"] != CUBES_TOTAL:
            raise Refused(f"split: {info['cubes']} cubes and {literals[0]} literals, not {CUBES_TOTAL} and "
                          f"{CUBE_LITERALS}")
        if any(sampled[i] != units[i] for i in chosen):
            raise AssertionError("a sampled cube's unranked literals differ from the stream's")
        log(f"packing: cover exact {ok_exact} {info}; parts verified "
            f"{sum(1 for p in parts_rows if p['verified'])} of {len(parts_rows)}")

        # Rule 6: the controls.
        controls.append(weak_control(tools, formula, variables, work))
        rows_p, _ = H.proof_controls(tools, work)
        controls.extend(rows_p)
        controls.extend(small_controls(tools, work))
        log(f"packing: controls {sum(1 for c in controls if c['passed'])} of {len(controls)} passed")

        # Rule 4: the sampled cubes, two at a time.
        body = body if body.endswith(b"\n") else body + b"\n"
        solver = capped(tools, build)

        def job(i, heap=HEAP_MB, stack=STACK_MB):
            path = os.path.join(work, f"cube-{i + 1}.cnf")
            with open(path, "wb") as f:
                f.write(H.with_units(variables, len(formula), body, units[i]))
            try:
                return H.solve(solver, path, work, f"cube-{i + 1}", heap, stack)
            finally:
                os.unlink(path)

        done = []
        with ThreadPoolExecutor(WORKERS) as pool:
            for k, (i, r) in enumerate(zip(chosen, pool.map(job, chosen))):
                done.append(r)
                v = verdict(r)
                if v != "unsat" or not r["verified"] or (k + 1) % 50 == 0 or r["seconds"] > 60:
                    log(f"packing: cube {i + 1} ({k + 1} of {len(chosen)}): {v}, verified {r['verified']}, "
                        f"{r['conflicts']} conflicts, {r['seconds']} s")
        for k, i in enumerate(chosen):        # a check that ran out of room, again, alone, with more
            if done[k]["resources"] and verdict(done[k]) == "unsat":
                log(f"packing: cube {i + 1}: cake_lpr ran out of room; again with {RETRY_HEAP_MB} MB")
                done[k] = dict(job(i, RETRY_HEAP_MB, RETRY_STACK_MB), retried=True)
        for i, r in zip(chosen, done):
            r["verdict"] = verdict(r)
            if r["verdict"] == "sat":     # a satisfiable cube: its model checked against F and the cube
                m = H.model(r["model"])
                r["model_violates"] = H.satisfies(m, formula) + H.satisfies(m, [(lit,) for lit in units[i]])
            r["model"] = None
    finally:
        shutil.rmtree(work, ignore_errors=True)
        shutil.rmtree(os.path.join(results, "cover"), ignore_errors=True)

    finished = [r for r in done if r["verdict"] != "timeout"]
    values.update({
        "cubes_total": split.total, "cubes_sha256": digest.hexdigest(), "cubes_sampled": len(chosen),
        "cubes_ids_head": ",".join(str(i + 1) for i in chosen[:12]),
        "cubes_unsat": sum(1 for r in done if r["verdict"] == "unsat"),
        "cubes_verified": sum(1 for r in done if r["verdict"] == "unsat" and r["verified"]),
        "cubes_timed_out": sum(1 for r in done if r["verdict"] == "timeout"),
        "cubes_sat": sum(1 for r in done if r["verdict"] == "sat"),
        "cover_exact": 1 if ok_exact else 0,
        "cover_parts_verified": sum(1 for p in parts_rows if p["verified"]),
        "controls_passed": sum(1 for c in controls if c["passed"]), "controls_total": len(controls),
        "solver": f"CaDiCaL {tools['cadical_version']} (Debian orig tarball; g++ {' '.join(H.CADICAL_FLAGS)}); "
                  f"checker {CHECKER}",
    })
    values["cover_ok"] = 1 if values["cover_exact"] == 1 and values["cover_parts_verified"] == len(parts_rows) \
        == split.R + 1 else 0
    values["test_passed"] = 1 if (values["witness_ok"] == 1 and values["witness_colours"] == MAX_COLOUR
                                  and len(chosen) == cubes_wanted
                                  and all(r["verdict"] == "unsat" and r["verified"] for r in finished)
                                  and values["cubes_timed_out"] == 0 and values["cover_ok"] == 1) else 0
    detail.update({"values": values, "controls": controls,
                   "cover": {"exact": info, "parts": parts_rows},
                   "cubes": [{"cube": i + 1, "literals": len(units[i]), **r} for i, r in zip(chosen, done)],
                   "caps": {"conflicts": CAP_CONFLICTS, "seconds": CAP_SECONDS},
                   "tools": {k: v for k, v in tools.items() if k not in ("cadical", "cake_lpr")},
                   "seconds": round(time.monotonic() - started, 1)})
    return summarise(values), detail


def main():
    parser = argparse.ArgumentParser(description="chi_rho(Z^2) = 15: the witness, the reduction, the cover, the "
                                                 "proof sampled")
    parser.add_argument("--cubes", type=int, default=CUBES, help=f"cubes to re-solve (default {CUBES})")
    args = parser.parse_args()
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, detail = run(seed, cubes_wanted=args.cubes, log=lambda line: print(line, file=sys.stderr, flush=True))
    except Refused as e:
        sys.exit(f"packing/check.py: refused: {e}")
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
