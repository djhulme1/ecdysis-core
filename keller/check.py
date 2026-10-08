#!/usr/bin/env python3
"""Keller's conjecture in dimension 7: the authors' s = 6 formula checked against the paper's encoding, a seeded
sample of its 38,616 cubes re-solved with proofs a verified checker accepts, the cubes' cover checked whole, and the
paper's 256-clique in dimension 8 checked, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:3836ad928c0989ce) is from Brakensiek,
Heule, Mackey and Narvaez, "The Resolution of Keller's Conjecture" (IJCAR 2020; arXiv:1910.03740v5): "We consider
three graphs, G_{7,3}, G_{7,4}, and G_{7,6}, related to Keller's conjecture in dimension 7. The conjecture is false
for this dimension if and only if at least one of the graphs contains a clique of size 2^7 = 128. [...] We apply
satisfiability solving combined with symmetry-breaking techniques to determine that no such clique exists." Its
registered test: no clique of size 128 in G_{7,3}, G_{7,4} or G_{7,6} (vertices {0, ..., 2s-1}^7, adjacent when they
differ by exactly s in one coordinate and differ in another). Refuted by such a clique; by a flaw in the symmetry
breaking (the lemmas, or the clauses added to the s = 6 formula with clausal proofs); or by the s = 6 proof failing:
one of its 38,616 cubes satisfiable with that formula, its proof rejected by a verified checker, or the cubes not
covering the search space.

The inputs, each checked against its SHA-256 and size before anything else runs (see INPUTS): the claim's data of
record, s6.cnf (the formula for G_{7,6} with every symmetry-breaking clause) and s6.dnf (its 38,616 cubes), from the
authors' Zenodo record 3755117 (CC BY 4.0); the paper's e-print, arXiv:1910.03740v5, read as data for its figure of a
256-clique in G_{8,2}; and the solver and the checker of hexagon/check.py, whose code this module imports: CaDiCaL
2.1.3's source as Debian archived it and the two files of the CakeML-verified LRAT checker cake_lpr, compiled from
source by the run, in the pinned image, with no network. Every rule below was fixed before any seed existed.

1. The encoding, written here from the paper's section 3, its equations (1) to (7). For n and s, the clique's
   vertices are c_i for i in 0 .. 2^n - 1, where bit j of i, w(i)_j, says which half of {0, ..., 2s-1} coordinate j
   of c_i lies in; x(i, j, k) is true when c_{i,j} = s w(i)_j + k. Exactly one k for each (i, j) (1); for i < i'
   whose bits differ in one place j, some other coordinate j' and some k with x(i, j', k) != x(i', j', k), through
   variables y(i, i', j', k) (3, 4); for every i < i', some j where their bits differ with x(i, j, k) = x(i', j, k)
   for every k, through variables z(i, i', j) (6, 7). Variables are numbered as the authors' program numbers them:
   x(i, j, k) = s n i + s j + k + 1, then for each pair i < i' in turn, its z for the differing bits j in increasing
   order, then (when they differ in one bit) its y for each other coordinate j' and each k. Its sizes for n = 7 must
   be the paper's Table 2: 39,424 variables and 200,320 clauses for s = 3, 43,008 and 265,728 for s = 4, and 50,176
   and 399,232 for s = 6.
2. The formula of record. s6.cnf is read (one header, every literal within it, the header's clause count) and
   compared, as a multiset of clauses (each a set of literals), with rule 1's formula for n = 7, s = 6: base_found
   counts the encoding's clauses found in it, base_missing those that are not. Of its clauses beyond the encoding, the
   unit clauses are read back as coordinates and must state exactly the canonical form of the paper's section 4 (its
   lemmas after Perron), as the authors' program fixes it: c_0 = (0, 0, 0, 0, 0, 0, 0), c_1 = (6, 1, 0, 0, 0, 0, 0)
   and c_3 = (6, 7, *, *, 1, 1, 1), nineteen positive literals and nothing else (units_ok). The rest, the symmetry
   breaking the authors added with clausal proofs, are counted (extra_clauses) and not checked.
3. The proof, sampled. The cubes must be 38,616 lines "a <literals> 0", each a set of literals on the formula's
   variables with no variable twice. CUBES cubes are drawn without replacement, uniformly, by the seed (numbered by
   their line in the cube file, from 1). For each, s6.cnf with the cube's literals added as unit clauses is solved by
   CaDiCaL with its LRAT proof streamed through a pipe into cake_lpr as it is written (hexagon/check.py's solve), two
   at a time; a check that runs out of cake_lpr's heap or stack is repeated alone with a larger one. A cube counts as
   UNSAT when CaDiCaL reports UNSATISFIABLE and as verified when cake_lpr then reports "s VERIFIED UNSAT" on that
   formula. A cube found satisfiable has its model checked against every clause of s6.cnf and the cube: a model that
   passed would be a clique of 128 in G_{7,6}, refuting the claim. cubes_conflicts adds up CaDiCaL's conflicts.
4. The cover. The negations of all 38,616 cubes, one clause each (over the formula's variables), must be refuted with
   a proof verified as in rule 3: then every assignment satisfies some cube, and the formula is unsatisfiable when
   every cube is.
5. The three graphs. In each coordinate, the map f(a) = a for a < s and f(a) = a - s + 6 for a >= s takes
   {0, ..., 2s-1} into {0, ..., 11}. For s = 3 and s = 4, over every pair of values a, b: |a - b| = s exactly when
   |f(a) - f(b)| = 6, and a = b exactly when f(a) = f(b). Adjacency in G_{n,s} is decided coordinate by coordinate,
   so f makes G_{7,3} and G_{7,4} induced subgraphs of G_{7,6}: a clique of 128 in either would be one in G_{7,6}, and
   the s = 6 formula decides all three graphs. embeds is 1 when both checks hold.
6. The witness in dimension 8, and so the other direction of the encoding. The figure labelled fig:clique256 in the
   e-print's main-clean.tex draws 256 vertices of G_{8,2}, each as \\dicea{x}{y} and \\diceb{x}{y} with four dots each
   at one of the 16 x 16 grid cells; the eight dots in that order are the coordinates (\\ca, \\cb, \\cc, \\cd for 0, 1,
   2, 3, as the caption says), and any other text inside the picture, after its frame, refuses the run.
   witness_clique is 1 when the 256 vertices are distinct and every pair (32,640) is adjacent in G_{8,2}. The clique,
   and its image in G_{8,6} under rule 5's map, are then put into rule 1's formulas for (8, 2) and (8, 6) as unit
   clauses on every x variable (each vertex as c_i for the i its halves name, which must take every i once); each
   formula must be satisfiable, with a model checked against every clause. witness_encodings_sat counts those that
   are, of 2. The paper ran this check on the authors' formulas; here it runs on rule 1's.
7. Controls, each of which must behave as stated (controls_passed counts those that do): rule 1's sizes equal Table
   2's; rule 1's formulas for (3, 2), (4, 2), (3, 3) and (4, 3) refuted with verified proofs (Keller's conjecture holds
   in dimensions up to 6, Perron 1940, so there is no clique of 2^n there); the comparison of rule 2 finds one clause
   missing when one clause of the encoding is taken out of the formula; the cover without one cube (drawn by the seed)
   satisfiable, with a model satisfying none of the other cubes, so a missing cube is caught; the witness with the
   first coordinate of its first vertex raised by one (mod 4) no longer a clique; and hexagon's three pigeonhole proof
   controls (accepted as written, rejected without its last step, rejected without a lemma that step cites).
8. Randomness, only from ECDYSIS_SEED, as in hexagon/check.py: the cubes from the label "keller/cubes", the cube left
   out of control 7's cover from "keller/drop". cubes_ids_sha256 is the SHA-256 of the drawn cube numbers in the order
   drawn, comma-separated; the numbers themselves, timings and each cube's conflicts go to results/detail.json.

test_passed is 1 if s6.cnf has the header's 50,176 variables, base_missing is 0, units_ok holds, every sampled cube is
UNSAT with a verified proof, the cover is verified and embeds is 1; else 0. The witness and the controls are reported
beside it.

What it cannot check:
- the symmetry breaking: the canonical form of c_0, c_1 and c_3 rests on hand proofs (one of them uses Keller's
  conjecture in dimension 6), and the other added clauses on the authors' clausal proofs (their logs are on Zenodo),
  which this run does not re-check;
- the whole proof: only CUBES of the 38,616 cubes are re-solved (about 0.4 s each at the median in the authors' runs,
  with a heavy tail to 75 minutes). A sample this size would catch a defect shared by many cubes, not one bad cube;
- the reduction from cube tilings to these graphs, which is prior work (and the conceptual claim ext:9cc144e889acdc4f);
- the authors' own runs: their proofs (224 GB of DRAT for s = 6) were checked with DRAT-trim and ACL2 and not kept;
  this re-solves with a later CaDiCaL and checks with cake_lpr;
- the tools beyond themselves: cake_lpr is verified in CakeML down to its assembly, but its C wrapper, the compiler,
  the kernel and this script are trusted.

Writes results/outputs.json (the 20 values a receipt carries) and results/detail.json. Run with: python3 keller/check.py
"""

import argparse
import collections
import hashlib
import importlib.util
import io
import itertools
import json
import os
import platform
import re
import shutil
import sys
import tarfile
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("keller_hexagon", os.path.join(HERE, "..", "hexagon", "check.py"))
H = importlib.util.module_from_spec(_spec)
sys.modules["keller_hexagon"] = H
_spec.loader.exec_module(H)

ZENODO = "Zenodo record 3755117 (doi:10.5281/zenodo.3755117, CC BY 4.0)"
INPUTS = (
    ("s6.cnf", "ca2f188eb41efb696a8be6ca00afa34dca22131515db09547c171e753d1301cb", 8726612, f"{ZENODO}, s6.cnf"),
    ("s6.dnf", "1beaa793e4561892539e4b8fa00ca26dce9669b930739c0d9fd109f79924cf16", 3629397, f"{ZENODO}, s6.dnf"),
    ("arXiv-1910.03740v5.tar.gz", "0c58ed0bf1964dec60ee0c44150b277878aec0e70378c5996ff253f6b088a62a", 580648,
     "the e-print of arXiv:1910.03740v5 (https://arxiv.org/src/1910.03740v5)"),
) + tuple(i for i in H.INPUTS if i[0] in ("cadical_2.1.3.orig.tar.gz", "cake_lpr.S", "basis_ffi.c"))

N, S = 7, 6
VARIABLES, CLAUSES = 50176, 403475          # s6.cnf's header
CUBES_TOTAL = 38616
CUBES = 100                                 # cubes re-solved and re-checked, drawn by the seed
TABLE2 = {3: (39424, 200320), 4: (43008, 265728), 6: (50176, 399232)}
SMALL = ((3, 2), (4, 2), (3, 3), (4, 3))
CANONICAL = {0: (0, 0, 0, 0, 0, 0, 0), 1: (6, 1, 0, 0, 0, 0, 0), 3: (6, 7, None, None, 1, 1, 1)}
WITNESS_N, WITNESS_S, WITNESS_SIZE = 8, 2, 256
DOTS = {"a": 0, "b": 1, "c": 2, "d": 3}
WORKERS = 2
HEAP_MB, STACK_MB = 1024, 512
RETRY_HEAP_MB, RETRY_STACK_MB = 2560, 768
LIMIT = 200

OUTPUTS = (
    "formula_vars", "formula_clauses", "base_found", "base_missing", "lemma_units", "extra_clauses",
    "cubes_total", "cubes_sampled", "cubes_ids_sha256", "cubes_unsat", "cubes_verified", "cubes_conflicts",
    "coverage_verified", "witness_clique", "witness_encodings_sat", "embeds",
    "controls_passed", "controls_total", "tools", "test_passed",
)


class Refused(Exception):
    """An input that is not what the rules say it must be."""


def load(directory, name):
    spec = next(i for i in INPUTS if i[0] == name)
    with open(os.path.join(directory, name), "rb") as f:
        data = f.read()
    got = hashlib.sha256(data).hexdigest()
    if got != spec[1] or len(data) != spec[2]:
        raise Refused(f"{name}: sha256 {got} and {len(data)} bytes, not the committed {spec[1]} and {spec[2]}")
    return data


# ---------------------------------------------------------------- rule 1: the encoding

def x_var(n, s, i, j, k):
    return s * n * i + s * j + k + 1


def encode(n, s):
    """Rule 1: (variables, clauses as tuples) of the paper's equations (1) to (7), numbered as the authors' program."""
    x = lambda i, j, k: x_var(n, s, i, j, k)  # noqa: E731
    clauses = []
    for i in range(1 << n):                                                     # (1)
        for j in range(n):
            clauses.append(tuple(x(i, j, k) for k in range(s)))
            clauses.extend((-x(i, j, k), -x(i, j, kk)) for k, kk in itertools.combinations(range(s), 2))
    v = (1 << n) * n * s
    for i in range(1 << n):
        for ii in range(i + 1, 1 << n):
            differ = [j for j in range(n) if (i ^ ii) >> j & 1]
            z = {j: v + t + 1 for t, j in enumerate(differ)}
            v += len(differ)
            clauses.append(tuple(z[j] for j in differ))                         # (7)
            for j in differ:                                                    # (6)
                for k in range(s):
                    clauses.append((-z[j], x(i, j, k), -x(ii, j, k)))
                    clauses.append((-z[j], -x(i, j, k), x(ii, j, k)))
            if len(differ) == 1:
                others = [(jj, k) for jj in range(n) if jj != differ[0] for k in range(s)]
                y = {jk: v + t + 1 for t, jk in enumerate(others)}
                v += len(others)
                clauses.append(tuple(y[jk] for jk in others))                   # (4)
                for (jj, k), yv in y.items():                                   # (3)
                    clauses.append((-yv, x(i, jj, k), x(ii, jj, k)))
                    clauses.append((-yv, -x(i, jj, k), -x(ii, jj, k)))
    return v, clauses


def table_sizes():
    """Rule 1's sizes for n = 7 and s = 3, 4, 6, and whether they are Table 2's."""
    sizes = {s: (lambda e: (e[0], len(e[1])))(encode(N, s)) for s in TABLE2}
    return sizes, all(sizes[s] == TABLE2[s] for s in TABLE2)


def decode(n, s, lit):
    """A positive literal on an x variable as (i, j, value of c_{i,j}); None for anything else."""
    if lit <= 0 or lit > (1 << n) * n * s:
        return None
    i, r = divmod(lit - 1, s * n)
    j, k = divmod(r, s)
    return i, j, s * ((i >> j) & 1) + k


# ---------------------------------------------------------------- rule 2: the formula of record

def compare(formula, base):
    """Rule 2 on clause lists: (found, missing, the clauses beyond the encoding as a list)."""
    have = collections.Counter(frozenset(c) for c in formula)
    want = collections.Counter(frozenset(c) for c in base)
    found = sum(min(k, have[c]) for c, k in want.items())
    extra = have - want
    return found, sum(want.values()) - found, [tuple(sorted(c, key=abs)) for c, k in extra.items() for _ in range(k)]


def lemma_units(units, n=N, s=S):
    """Rule 2: the unit clauses read back as coordinates; (as text, whether they are exactly the canonical form)."""
    fixed, ok = {}, True
    for (lit,) in units:
        d = decode(n, s, lit)
        if d is None or (d[0], d[1]) in fixed:
            ok = False
            continue
        fixed[(d[0], d[1])] = d[2]
    want = {(i, j): v for i, vec in CANONICAL.items() for j, v in enumerate(vec) if v is not None}
    ok = ok and fixed == want and len(units) == len(want)
    vertices = sorted({i for i, _ in fixed})
    text = "; ".join(f"c{i}=(" + ",".join(str(fixed.get((i, j), "*")) for j in range(n)) + ")" for i in vertices)
    return text, ok


def check_formula(inputs):
    """Rules 1 and 2 and control 7's removed clause, in a child process: a summary, nothing big."""
    variables, formula, header, _ = H.parse_cnf(load(inputs, "s6.cnf"), "s6.cnf")
    nv, base = encode(N, S)
    found, missing, extra = compare(formula, base)
    units = [c for c in extra if len(c) == 1]
    others = [c for c in extra if len(c) > 1]
    text, units_ok = lemma_units(units)
    last = frozenset(base[-1])              # control: the encoding's last clause taken out of the formula
    at = next((k for k, c in enumerate(formula) if frozenset(c) == last), None)
    _, missing_cut, _ = compare(formula[:at] + formula[at + 1:], base) if at is not None else (None, None, None)
    on_x = all(abs(lit) <= (1 << N) * N * S for c in others for lit in c)
    slots = sorted({decode(N, S, abs(lit))[0] for c in others for lit in c}) if on_x else None
    sizes, table_ok = table_sizes()
    return {"variables": variables, "clauses": len(formula), "header": header.decode(), "encoding_variables": nv,
            "encoding_clauses": len(base), "found": found, "missing": missing, "extra": len(extra),
            "units": len(units), "units_text": text, "units_ok": units_ok, "others": len(others),
            "others_lengths": dict(sorted(collections.Counter(len(c) for c in others).items())),
            "others_on_x_only": on_x, "others_vertices": slots, "missing_when_cut": missing_cut,
            "table_sizes": {str(s): list(v) for s, v in sizes.items()}, "table_ok": table_ok}


def check_models(inputs, found):
    """For each (cube, model text) the solver called satisfiable: the clauses of s6.cnf and of the cube it violates."""
    _, formula, _, _ = H.parse_cnf(load(inputs, "s6.cnf"), "s6.cnf")
    out = []
    for cube, text in found:
        m = H.model(text)
        out.append(H.satisfies(m, formula) + H.satisfies(m, [(lit,) for lit in cube]))
    return out


# ---------------------------------------------------------------- rule 5: the three graphs

def embedding(s, into=S):
    return lambda a: a if a < s else a - s + into


def embeds(s, into=S):
    f = embedding(s, into)
    return all((abs(a - b) == s) == (abs(f(a) - f(b)) == into) and (a == b) == (f(a) == f(b))
               for a in range(2 * s) for b in range(2 * s))


# ---------------------------------------------------------------- rule 6: the witness

PAIR = re.compile(r"\\dicea\{(\d+)\}\{(\d+)\}((?:\{\\c[abcd]\}){4})\s*\\diceb\{(\d+)\}\{(\d+)\}((?:\{\\c[abcd]\}){4})")
FRAME = r"\draw[fill=white,white] (-0.1,-0.1) rectangle (16.1,16.1);"


def parse_witness(eprint):
    """The 256 vertices of the figure labelled fig:clique256, in the order drawn."""
    with tarfile.open(fileobj=io.BytesIO(eprint), mode="r:gz") as tar:
        try:
            member = tar.getmember("main-clean.tex")
        except KeyError:
            raise Refused("e-print: no main-clean.tex") from None
        if not member.isfile():
            raise Refused("e-print: main-clean.tex is not a file")
        tex = tar.extractfile(member).read().decode("utf-8")
    at = tex.find(r"\label{fig:clique256}")
    start = tex.rfind(r"\begin{tikzpicture}", 0, at)
    end = tex.find(r"\end{tikzpicture}", start)
    if at < 0 or start < 0 or end < 0 or end > at:
        raise Refused("e-print: no tikzpicture before \\label{fig:clique256}")
    body = tex[start + len(r"\begin{tikzpicture}"):end].strip()
    if not body.startswith("[scale=0.70]"):
        raise Refused("e-print: the picture does not open with [scale=0.70]")
    body = body[len("[scale=0.70]"):].strip()
    if not body.startswith(FRAME):
        raise Refused("e-print: the picture does not open with its white frame")
    body = body[len(FRAME):]
    vertices, cells, pos = [], set(), 0
    for m in PAIR.finditer(body):
        if body[pos:m.start()].strip():
            raise Refused("e-print: text between the dice that is not a vertex")
        pos = m.end()
        xa, ya, a, xb, yb, b = m.groups()
        if (xa, ya) != (xb, yb) or not (0 <= int(xa) < 16 and 0 <= int(ya) < 16):
            raise Refused("e-print: a vertex whose two halves are drawn at different cells, or off the grid")
        cells.add((int(xa), int(ya)))
        vertices.append(tuple(DOTS[d] for d in re.findall(r"\\c([abcd])", a + b)))
    if body[pos:].strip():
        raise Refused("e-print: text after the dice that is not a vertex")
    if len(vertices) != WITNESS_SIZE or len(cells) != WITNESS_SIZE:
        raise Refused(f"e-print: {len(vertices)} vertices in {len(cells)} cells, not {WITNESS_SIZE}")
    return vertices


def adjacent(u, v, s):
    """Adjacency in G_{n,s}: some coordinate differs by exactly s and some other coordinate differs."""
    return any(abs(u[i] - v[i]) == s and any(u[j] != v[j] for j in range(len(u)) if j != i) for i in range(len(u)))


def non_adjacent(vertices, s):
    return sum(1 for u, v in itertools.combinations(vertices, 2) if not adjacent(u, v, s))


def witness_units(vertices, n, s):
    """Rule 6: unit clauses putting each vertex at the c_i its halves name; None if they do not name every i once."""
    slots, units = set(), []
    for v in vertices:
        i = sum((v[j] >= s) << j for j in range(n))
        slots.add(i)
        units.extend((x_var(n, s, i, j, v[j] - s * ((i >> j) & 1)),) for j in range(n))
    return units if slots == set(range(1 << n)) else None


def witness_sat(tools, work, vertices, n, s):
    """Rule 6 for one (n, s), in a child process: the encoding with the clique's units, solved, its model checked."""
    nv, clauses = encode(n, s)
    units = witness_units(vertices, n, s)
    if units is None:
        return {"n": n, "s": s, "passed": False, "answer": None, "why": "the vertices do not take every c_i once"}
    clauses += units
    cnf = os.path.join(work, f"witness-{n}-{s}.cnf")
    with open(cnf, "wb") as f:
        f.write(b"p cnf %d %d\n" % (nv, len(clauses)) + H.clause_lines(clauses))
    r = H.solve(tools, cnf, work, f"witness-{n}-{s}", proof=False)
    os.unlink(cnf)
    violated = H.satisfies(H.model(r["model"]), clauses) if r["answer"] == "sat" else None
    return {"n": n, "s": s, "variables": nv, "clauses": len(clauses), "answer": r["answer"], "violated": violated,
            "seconds": r["seconds"], "passed": r["answer"] == "sat" and violated == 0}


# ---------------------------------------------------------------- solving

def solve_cnf(tools, work, tag, nv, clauses, proof=True):
    cnf = os.path.join(work, f"{tag}.cnf")
    with open(cnf, "wb") as f:
        f.write(b"p cnf %d %d\n" % (nv, len(clauses)) + H.clause_lines(clauses))
    r = H.solve(tools, cnf, work, tag, heap=HEAP_MB, stack=STACK_MB, proof=proof)
    if r["answer"] == "unsat" and not r["verified"] and r["resources"]:
        r = dict(H.solve(tools, cnf, work, tag, heap=RETRY_HEAP_MB, stack=RETRY_STACK_MB, proof=proof), retried=True)
    os.unlink(cnf)
    return r


def summarise(values):
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters")
    return out


# ---------------------------------------------------------------- the run

def run(seed, inputs="inputs", results="results", cubes_wanted=CUBES, tools=None, log=print):
    """Every rule, in order; returns (outputs, detail). tools, if given, replaces the build (tests only)."""
    started = time.monotonic()
    for name, *_ in INPUTS:                    # every input checked before anything runs
        load(inputs, name)
    detail = {"inputs": [{"name": n, "sha256": h, "bytes": b, "source": s} for n, h, b, s in INPUTS]}
    values, controls = {}, []

    # Rule 5: the three graphs.
    values["embeds"] = 1 if embeds(3) and embeds(4) else 0

    # Rule 6, first half: the witness read and checked as a clique.
    vertices = parse_witness(load(inputs, "arXiv-1910.03740v5.tar.gz"))
    gaps = non_adjacent(vertices, WITNESS_S)
    image = [tuple(map(embedding(WITNESS_S), v)) for v in vertices]
    gaps_image = non_adjacent(image, S)
    values["witness_clique"] = 1 if len(set(vertices)) == WITNESS_SIZE and gaps == 0 else 0
    log(f"keller: witness {len(set(vertices))} distinct vertices, {gaps} non-adjacent pairs in G_(8,2), "
        f"{gaps_image} in G_(8,6) after the map")
    broken = [((vertices[0][0] + 1) % 4,) + vertices[0][1:]] + vertices[1:]
    controls.append({"control": "the witness with its first vertex's first coordinate raised by one: not a clique",
                     "passed": non_adjacent(broken, WITNESS_S) > 0, "non_adjacent": non_adjacent(broken, WITNESS_S)})

    # The tools.
    os.makedirs(results, exist_ok=True)
    if tools is None:
        if platform.machine() not in ("x86_64", "AMD64"):
            raise SystemExit("keller/check.py: cake_lpr.S is x86-64 assembly; run this on an x86-64 machine")
        tools = H.build_tools(os.path.abspath(inputs), os.path.abspath(os.path.join(results, "build")))
        log(f"keller: built CaDiCaL {tools['cadical_version']} and cake_lpr, gcc {tools['gcc']}, "
            f"at {time.monotonic() - started:.0f} s")
    work = tempfile.mkdtemp(prefix="keller-")
    try:
        # Rules 1 and 2, in a child.
        formula = H.in_child(check_formula, inputs)
        log(f"keller: s6.cnf {formula['variables']} variables, {formula['clauses']} clauses; encoding "
            f"{formula['found']} found, {formula['missing']} missing; units {formula['units_text']} "
            f"({'as stated' if formula['units_ok'] else 'NOT as stated'}); {formula['others']} other added clauses")
        controls.append({"control": "rule 1's sizes for n = 7 are Table 2's", "passed": formula["table_ok"],
                         "sizes": formula["table_sizes"]})
        controls.append({"control": "one clause of the encoding taken out of s6.cnf: found missing",
                         "passed": formula["missing_when_cut"] == formula["missing"] + 1,
                         "missing": formula["missing_when_cut"]})

        # Rule 6, second half: the witness in the encodings, each in a child.
        rows = [H.in_child(witness_sat, tools, work, vertices, WITNESS_N, WITNESS_S),
                H.in_child(witness_sat, tools, work, image, WITNESS_N, S)]
        values["witness_encodings_sat"] = sum(1 for r in rows if r["passed"])
        log("keller: witness in the encodings: " + "; ".join(f"({r['n']}, {r['s']}) {r['answer']}" for r in rows))

        # Control: small dimensions, refuted.
        for n, s in SMALL:
            nv, clauses = encode(n, s)
            r = solve_cnf(tools, work, f"small-{n}-{s}", nv, clauses)
            controls.append({"control": f"rule 1's formula for ({n}, {s}): refuted, proof verified",
                             "passed": r["answer"] == "unsat" and r["verified"], "answer": r["answer"],
                             "verified": r["verified"], "conflicts": r["conflicts"], "seconds": r["seconds"]})

        # The cubes.
        data = load(inputs, "s6.dnf")
        cubes = H.parse_cubes(data, VARIABLES)
        del data
        if len(cubes) != CUBES_TOTAL:
            raise Refused(f"s6.dnf: {len(cubes)} cubes, not {CUBES_TOTAL}")
        chosen = H.sample(seed, "keller/cubes", CUBES_TOTAL, cubes_wanted)
        drop = H.sample(seed, "keller/drop", CUBES_TOTAL, 1)[0]

        # Rule 4 and its control: the cover, and the cover without one cube.
        negated = [tuple(-lit for lit in c) for c in cubes]
        cover = solve_cnf(tools, work, "cover", VARIABLES, negated)
        without = [c for k, c in enumerate(negated) if k != drop]
        r = solve_cnf(tools, work, "cover-drop", VARIABLES, without, proof=False)
        if r["answer"] == "sat":
            m = H.model(r["model"])
            others = H.satisfies(m, without)
            hits_dropped = all(lit in m for lit in cubes[drop])
        else:
            others, hits_dropped = None, None
        controls.append({"control": f"the cover without cube {drop + 1}: satisfiable, its model in none of the others",
                         "passed": r["answer"] == "sat" and others == 0, "answer": r["answer"],
                         "violated": others, "model_in_dropped_cube": hits_dropped})
        del negated, without
        log(f"keller: cover {cover['answer']}, verified {cover['verified']}; without cube {drop + 1}: {r['answer']}")

        controls_p, _ = H.proof_controls(tools, work)
        controls += controls_p

        # Rule 3: the sampled cubes, two at a time.
        with open(os.path.join(inputs, "s6.cnf"), "rb") as f:
            _, _, body = f.read().partition(b"\n")
        if not body.endswith(b"\n"):
            body += b"\n"

        def job(i, heap=HEAP_MB, stack=STACK_MB):
            path = os.path.join(work, f"cube-{i + 1}.cnf")
            with open(path, "wb") as f:
                f.write(H.with_units(VARIABLES, CLAUSES, body, cubes[i]))
            try:
                return H.solve(tools, path, work, f"cube-{i + 1}", heap, stack)
            finally:
                os.unlink(path)

        per_cube = []
        with ThreadPoolExecutor(WORKERS) as pool:
            for i, r in zip(chosen, pool.map(job, chosen)):
                per_cube.append(r)
                log(f"keller: cube {i + 1}: {r['answer']}, verified {r['verified']}, {r['conflicts']} conflicts, "
                    f"{r['seconds']} s")
        for k, i in enumerate(chosen):          # a check that ran out of room, again, alone, with more
            if per_cube[k]["resources"]:
                log(f"keller: cube {i + 1}: cake_lpr ran out of room; again with {RETRY_HEAP_MB} MB")
                per_cube[k] = dict(job(i, RETRY_HEAP_MB, RETRY_STACK_MB), retried=True)
        found = [(cubes[i], r["model"]) for i, r in zip(chosen, per_cube) if r["answer"] == "sat"]
        if found:                               # a satisfiable cube: its model checked against s6.cnf and the cube
            violations = iter(H.in_child(check_models, inputs, found))
            for r in per_cube:
                if r["answer"] == "sat":
                    r["model_violates"] = next(violations)
                    log(f"keller: a satisfiable cube; its model violates {r['model_violates']} clauses")
        for r in per_cube + [cover]:
            r["model"] = None
    finally:
        shutil.rmtree(work, ignore_errors=True)

    ids = ",".join(str(i + 1) for i in chosen)
    conflicts = [r["conflicts"] for r in per_cube]
    values.update({
        "formula_vars": formula["variables"], "formula_clauses": formula["clauses"],
        "base_found": formula["found"], "base_missing": formula["missing"],
        "lemma_units": formula["units_text"], "extra_clauses": formula["others"],
        "cubes_total": len(cubes), "cubes_sampled": len(chosen),
        "cubes_ids_sha256": hashlib.sha256(ids.encode("ascii")).hexdigest(),
        "cubes_unsat": sum(1 for r in per_cube if r["answer"] == "unsat"),
        "cubes_verified": sum(1 for r in per_cube if r["answer"] == "unsat" and r["verified"]),
        "cubes_conflicts": sum(conflicts) if all(c is not None for c in conflicts) else -1,
        "coverage_verified": 1 if cover["answer"] == "unsat" and cover["verified"] else 0,
        "controls_passed": sum(1 for c in controls if c["passed"]), "controls_total": len(controls),
        "tools": f"CaDiCaL {tools['cadical_version']} (Debian orig tarball); {H.CHECKER}",
    })
    formula_ok = (formula["variables"] == VARIABLES and formula["clauses"] == CLAUSES and formula["missing"] == 0
                  and formula["found"] == TABLE2[S][1] and formula["units_ok"])
    values["test_passed"] = 1 if (formula_ok and values["cubes_verified"] == len(chosen) == cubes_wanted
                                  and values["coverage_verified"] == 1 and values["embeds"] == 1) else 0
    detail.update({
        "values": values, "formula": formula, "controls": controls, "witness": {
            "vertices": len(vertices), "distinct": len(set(vertices)), "non_adjacent_g82": gaps,
            "non_adjacent_g86_image": gaps_image, "encodings": rows, "first": [list(v) for v in vertices[:3]]},
        "cover": {k: v for k, v in cover.items() if k != "model"}, "dropped_cube": drop + 1,
        "cubes": [{"cube": i + 1, "literals": len(cubes[i]), **{k: v for k, v in r.items() if k != "model"}}
                  for i, r in zip(chosen, per_cube)],
        "cubes_ids": ids,
        "tools": {k: v for k, v in tools.items() if k not in ("cadical", "cake_lpr")},
        "seconds": round(time.monotonic() - started, 1)})
    return summarise(values), detail


def main():
    parser = argparse.ArgumentParser(description="Keller's conjecture in dimension 7: the s = 6 proof, sampled")
    parser.add_argument("--cubes", type=int, default=CUBES, help=f"cubes to re-solve (default {CUBES})")
    args = parser.parse_args()
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, detail = run(seed, cubes_wanted=args.cubes, log=lambda line: print(line, file=sys.stderr, flush=True))
    except Refused as e:
        sys.exit(f"keller/check.py: refused: {e}")
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
