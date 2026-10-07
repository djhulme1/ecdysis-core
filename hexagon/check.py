#!/usr/bin/env python3
"""The empty hexagon number h(6) = 30: Overmars's 29 points checked exactly, and Heule and Scheucher's proof sampled
and re-checked, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:4c4750ac793ed187) is from Heule and
Scheucher, "Happy Ending: An Empty Hexagon in Every Set of 30 Points" (TACAS 2024, arXiv:2403.00737): "We establish
the exact bound: Every 30-point set in the plane in general position contains an empty hexagon." Its registered test:
every set of 30 points in general position contains an empty hexagon (six points in convex position with no other
point of the set in their convex hull), and 30 is least. Refuted by a 30-point set in general position with no empty
hexagon; by the authors' proof failing to verify (one of its 312,418 cubes satisfiable, its proof rejected, or the
cubes not covering the search space); or by every 29-point set having one, so that 30 is not least (Overmars's 29
points are the witness).

The inputs, each checked against its SHA-256 and size before anything else runs (see INPUTS): from the Lean
formalisation of Subercaseaux, Nawrocki, Gallicchio, Codel, Carneiro and Heule (bsubercaseaux/EmptyHexagonLean at
commit 3073981), Lean/Geo.lean (the 29 points, read as data), final_experiment/final-30-ours-flat.cnf (the formula F
their Lean proof reduces the theorem to), final_experiment/marijn-cubes.icnf (the 312,418 cubes) and
final_experiment/cube_tautology.cnf (the coverage formula); CaDiCaL 2.1.3's source, as Debian archived it; and the
two files from which the CakeML-verified LRAT checker cake_lpr is assembled (tanyongkiam/cake_lpr at a36874a). No
input is executed as given: the solver and the checker are compiled from source into results/build by this run, in
the pinned image, with no network. Every rule below was fixed before any seed existed.

1. The witness. The points are the list after "hole_lower_bound [" in "theorem holeNumber_6" of Geo.lean, which must
   be 29 integer pairs and nothing else. In exact integer arithmetic (orient(a, b, c) = (b - a) x (c - a)): the 29
   are distinct; no three are collinear (all 3,654 triples); every 6-subset is tested, its convex hull taken by
   Andrew's monotone chain, and a convex hexagon (hull of six vertices) is empty when no other point lies strictly
   inside it (on its boundary is impossible in general position). witness_ok needs 29 distinct points, no collinear
   triple and no empty hexagon. Beside it: the convex hexagons counted and the sizes of the convex layers.
2. The proof, sampled. F is read and checked (its header, every literal within it). The cubes must be 312,418 lines
   "a <literals> 0", each a set of literals on F's variables with no variable twice. CUBES cubes are drawn without
   replacement, uniformly, by the seed (numbered by their line in the cube file, from 1). For each, F with the
   cube's literals added as unit clauses is solved by CaDiCaL with an LRAT proof, which is streamed through a pipe
   into cake_lpr as it is written (the authors' own setup; the proofs average hundreds of megabytes and are never
   stored). A cube counts as UNSAT when CaDiCaL reports UNSATISFIABLE (exit 20) and as verified when cake_lpr then
   reports "s VERIFIED UNSAT" on F with that cube. A cube CaDiCaL finds satisfiable has its model checked against
   every clause; a checked model would refute the claim. A check that runs out of cake_lpr's heap or stack is
   repeated alone with a larger one.
3. The coverage. Every clause of cube_tautology.cnf must be a clause of F, the negation of a cube, or a clause with
   a literal whose variable occurs in no other clause (such a clause can always be satisfied by that literal, so it
   cannot change satisfiability; the one such clause, "75109 452000 0", is F's DIMACS header read as a clause by
   the authors' final_experiment/cubing_taut.py). Then cube_tautology.cnf must be UNSAT with its proof verified, as
   in rule 2. Together: F and the negations of all the cubes are unsatisfiable, so every model of F satisfies some
   cube, and F is unsatisfiable if every cube is.
4. Controls, each of which must behave as stated (controls_passed counts those that do): F cut to its opening block
   (its first 237,510 clauses, all of three literals) must be satisfiable, with a model that satisfies every kept
   clause and violates at least one removed one (it must, unless F itself is satisfiable); an LRAT proof CaDiCaL
   writes for the pigeonhole formula (6 pigeons, 5 holes) must be accepted by cake_lpr, and rejected with its last
   step removed and with the lemma its last step first cites removed; the witness with its first point moved onto
   the line through its second and third must fail for collinearity; and the witness with the point (600, 600)
   added (in general position with the 29, checked) must contain an empty hexagon.
5. Seeded extra points (reported only; weak evidence for the bound): EXTRA points are drawn uniformly from the
   witness's bounding box by the seed; a draw that repeats a point or is collinear with two of the 29 is rejected
   and counted. For each 30-point set, every 6-subset containing the new point is tested: there must be an empty
   hexagon, and every empty hexagon in the set contains the new point (the 29 have none).
6. Randomness, only from ECDYSIS_SEED, as in mm/check.py: the 32-byte blocks SHA-256(seed || "|" || label || "|" ||
   counter) read 8 bytes at a time, big-endian; an integer below n by rejection. The labels are "hexagon/cubes" and
   "hexagon/points". The solver's search is deterministic and the work is gathered in a fixed order; timings and
   conflict counts go to results/detail.json only.

test_passed is 1 if witness_ok is 1, every sampled cube is UNSAT with a verified proof, and the coverage check
passes (rule 3, structure, UNSAT and verified); else 0. The controls and the extra points are reported beside it.

What it cannot check:
- the link from F to the theorem: the Lean proof that F's unsatisfiability implies h(6) <= 30 is trusted, not
  re-run (Lean and mathlib cannot be provisioned in the sandbox), and so is the identity of final-30-ours-flat.cnf
  with what the Lean encoder emits;
- the whole proof: only CUBES of the 312,418 cubes are re-solved (167 to 1,215 seconds each in two trials here,
  about 450 on average, with a heavy tail). A sample this size would catch a defect shared by many cubes, not a
  single bad cube;
- the authors' own runs: no proofs were stored, so this re-solves rather than re-checks them, with a later CaDiCaL
  (2.1.3; they used 1.9.3 and 1.9.5);
- the tools beyond themselves: cake_lpr is verified in CakeML down to its assembly, but the C wrapper, the compiler,
  the kernel and this script are trusted;
- every 30-point set: the extra points are a handful of random instances, not the bound.

Writes results/outputs.json (the 20 values a receipt carries, numbers and strings of at most 200 characters) and
results/detail.json (every value computed, uncut). hexagon/README.md gives the inputs, outputs and runtime.
"""

import argparse
import hashlib
import itertools
import json
import multiprocessing
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

# The inputs, at inputs/<name>: (name, SHA-256, bytes, where it comes from). hexagon/README.md gives the URLs.
INPUTS = (
    ("Geo.lean", "3b64f0139928046c812ff336c0d894a3899d0b31710b79714bc5bb07d4c99643", 6376,
     "EmptyHexagonLean@3073981 Lean/Geo.lean"),
    ("final-30-ours-flat.cnf", "95f2789a770999b76129f048ae5ec59c06dfc42c1f8f5f3a134b54e242dd95e3", 9704854,
     "EmptyHexagonLean@3073981 final_experiment/final-30-ours-flat.cnf"),
    ("marijn-cubes.icnf", "7d227e0f7ce9f55c42f70420de5f987518a8372d2f3f4e680c3420a4ea4e0171", 37366908,
     "EmptyHexagonLean@3073981 final_experiment/marijn-cubes.icnf"),
    ("cube_tautology.cnf", "ed1c0cdad2b99d5d9e9a28dd8499243157e4f9b226ebca4a4c39bdd6df992323", 45786575,
     "EmptyHexagonLean@3073981 final_experiment/cube_tautology.cnf"),
    ("cadical_2.1.3.orig.tar.gz", "abfe890aa4ccda7b8449c7ad41acb113cfb8e7e8fbf5e49369075f9b00d70465", 731545,
     "Debian's cadical_2.1.3.orig.tar.gz (snapshot.debian.org)"),
    ("cake_lpr.S", "2f3af32d55083839b3fa0e693afd817679c0b8944bef41def05a8b0ec72b7d4a", 2473208,
     "cake_lpr@a36874a cake_lpr.S"),
    ("basis_ffi.c", "8e30d84fdcb2177aa5571d7fa6661a2fae5ecfd56baa0ce49c65f9233a9f87cb", 12736,
     "cake_lpr@a36874a basis_ffi.c"),
)
POINTS = 29
CUBES_TOTAL = 312418     # the cubes the authors' partition has (marijn-cubes.icnf)
CUBES = 8                # cubes re-solved and re-checked, drawn by the seed
EXTRA = 8                # seeded 30th points (rule 5)
WEAK_KEEP = 237510       # the weakened formula: F's first clauses, its opening block of 3-literal clauses
ADDED = (600, 600)       # the fixed 30th point of the control in rule 4
PIGEONS = 6              # the pigeonhole formula of the proof controls: 6 pigeons, 5 holes
WORKERS = 2
HEAP_MB, STACK_MB = 1024, 512            # cake_lpr's heap and stack (its defaults, 4096 each, exceed 4 GB)
RETRY_HEAP_MB, RETRY_STACK_MB = 2560, 768      # alone: 2.5 GB + 0.75 GB beside one solver, under 4 GB
CADICAL_DIR = "cadical-rel-2.1.3"
CADICAL_FLAGS = ("-O3", "-DNDEBUG", "-DNBUILD")
CAKE_FLAGS = ("-O2", "-std=c99")
CHECKER = "cake_lpr a36874a (CakeML-verified LRAT checker)"
LIMIT = 200              # the archive's longest string output

OUTPUTS = (
    "witness_ok", "witness_collinear_triples", "witness_convex_hexagons", "witness_empty_hexagons", "witness_layers",
    "cubes_sampled", "cubes_ids", "cubes_unsat", "cubes_verified",
    "coverage_clauses", "coverage_unsat", "coverage_verified",
    "controls_passed", "controls_total",
    "extra_sets_checked", "extra_sets_with_hole", "extra_rejected",
    "solver", "checker", "test_passed",
)


class Refused(Exception):
    """An input that is not what the rules say it must be."""


# ---------------------------------------------------------------- the draws

class Stream:
    """As in mm/check.py: SHA-256(seed || "|" || label || "|" || counter), 8 bytes at a time, big-endian; an
    integer below n by rejection."""

    def __init__(self, seed_hex, label):
        self.seed, self.label, self.counter, self.buf = bytes.fromhex(seed_hex), label.encode("ascii"), 0, b""

    def u64(self):
        if len(self.buf) < 8:
            self.buf += hashlib.sha256(self.seed + b"|" + self.label + b"|" + str(self.counter).encode("ascii")).digest()
            self.counter += 1
        x, self.buf = int.from_bytes(self.buf[:8], "big"), self.buf[8:]
        return x

    def below(self, n):
        limit = (1 << 64) - ((1 << 64) % n)
        while True:
            x = self.u64()
            if x < limit:
                return x % n


def sample(seed, label, n, k):
    """k distinct integers below n, in the order drawn."""
    if not 0 <= k <= n:
        raise ValueError("cannot draw that many")
    s, out, seen = Stream(seed, label), [], set()
    while len(out) < k:
        x = s.below(n)
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


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


PAIR = r"\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)"


def parse_points(text):
    """The integer pairs after "hole_lower_bound [" in theorem holeNumber_6, refusing anything else in the list."""
    at = text.find("theorem holeNumber_6")
    if at < 0:
        raise Refused("Geo.lean: no theorem holeNumber_6")
    start = text.find("hole_lower_bound [", at)
    if start < 0:
        raise Refused("Geo.lean: no hole_lower_bound [ in holeNumber_6")
    start += len("hole_lower_bound [")
    end = text.find("]", start)
    body = text[start:end]
    if end < 0 or not re.fullmatch(rf"\s*{PAIR}(\s*,\s*{PAIR})*\s*", body):
        raise Refused("Geo.lean: the list in holeNumber_6 is not integer pairs alone")
    return [(int(a), int(b)) for a, b in re.findall(PAIR, body)]


def parse_cnf(data, what):
    """(variables, clauses as tuples, the header line, the body bytes) of a DIMACS CNF: one header "p cnf V C", no
    comments, every clause ending in 0 on its own line, every literal within V, exactly C clauses."""
    first, _, body = data.partition(b"\n")
    m = re.fullmatch(rb"p cnf (\d+) (\d+)", first.strip())
    if m is None:
        raise Refused(f"{what}: the first line is not a DIMACS header")
    variables, count = int(m.group(1)), int(m.group(2))
    clauses = []
    for line in body.split(b"\n"):
        toks = line.split()
        if not toks:
            continue
        if toks[-1] != b"0" or toks[0][:1] in (b"c", b"p"):
            raise Refused(f"{what}: a line that is not a clause ending in 0")
        try:
            clause = tuple(int(t) for t in toks[:-1])
        except ValueError:
            raise Refused(f"{what}: a literal that is not an integer") from None
        if any(lit == 0 or abs(lit) > variables for lit in clause):
            raise Refused(f"{what}: a literal outside 1..{variables}")
        clauses.append(clause)
    if len(clauses) != count:
        raise Refused(f"{what}: {len(clauses)} clauses, not the header's {count}")
    if not body.endswith(b"\n"):
        body += b"\n"
    return variables, clauses, first, body


def parse_cubes(data, variables):
    """The cubes of an iCNF cube file: lines "a <literals> 0", each literal within 1..variables, no variable twice."""
    cubes = []
    for line in data.split(b"\n"):
        toks = line.split()
        if not toks:
            continue
        if toks[0] != b"a" or toks[-1] != b"0" or len(toks) < 3:
            raise Refused("cubes: a line that is not \"a <literals> 0\"")
        try:
            cube = tuple(int(t) for t in toks[1:-1])
        except ValueError:
            raise Refused("cubes: a literal that is not an integer") from None
        if any(lit == 0 or abs(lit) > variables for lit in cube) or len({abs(lit) for lit in cube}) != len(cube):
            raise Refused("cubes: a literal out of range or a variable twice")
        cubes.append(cube)
    return cubes


# ---------------------------------------------------------------- geometry, exactly

def orient(a, b, c):
    """Twice the signed area of abc: positive when abc turn anticlockwise, 0 when collinear."""
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def collinear_triples(points):
    return sum(1 for a, b, c in itertools.combinations(points, 3) if orient(a, b, c) == 0)


def signs(points):
    """table[a][b][c] = the sign of orient(points[a], points[b], points[c])."""
    n = len(points)
    table = [[[0] * n for _ in range(n)] for _ in range(n)]
    for a, b, c in itertools.permutations(range(n), 3):
        v = orient(points[a], points[b], points[c])
        table[a][b][c] = (v > 0) - (v < 0)
    return table


def hull(ids, table):
    """Andrew's monotone chain on point numbers sorted by (x, y): the hull's vertices, anticlockwise, collinear
    points dropped."""
    lower, upper = [], []
    for p in ids:
        while len(lower) >= 2 and table[lower[-2]][lower[-1]][p] <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(ids):
        while len(upper) >= 2 and table[upper[-2]][upper[-1]][p] <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1] if len(ids) > 2 else list(ids)


def hexagons(points, containing=None):
    """(convex hexagons, empty hexagons as tuples of points) among the 6-subsets of points, or only those containing
    the point numbered containing. Assumes no three collinear (checked separately)."""
    order = sorted(range(len(points)), key=lambda i: points[i])
    pts = [points[i] for i in order]
    table = signs(pts)
    n = len(pts)
    if containing is None:
        subsets = itertools.combinations(range(n), 6)
    else:
        m = order.index(containing)
        rest = [i for i in range(n) if i != m]
        subsets = (tuple(sorted(c + (m,))) for c in itertools.combinations(rest, 5))
    convex, empty = 0, []
    for ids in subsets:
        h = hull(ids, table)
        if len(h) != 6:
            continue
        convex += 1
        inside = set(ids)
        cycle = list(zip(h, h[1:] + h[:1]))
        if not any(q not in inside and all(table[a][b][q] > 0 for a, b in cycle) for q in range(n)):
            empty.append(tuple(pts[i] for i in h))
    return convex, empty


def layers(points):
    """The sizes of the convex layers: the hull, then the hull of what is left, and so on."""
    rest, out = sorted(points), []
    while rest:
        table = signs(rest)
        h = set(hull(list(range(len(rest))), table))
        out.append(len(h))
        rest = [p for i, p in enumerate(rest) if i not in h]
    return out


def witness(points):
    """Rule 1 on a list of points: a dict of the counts and witness_ok."""
    distinct = len(set(points)) == len(points)
    col = collinear_triples(points)
    convex, empty = hexagons(points) if distinct and col == 0 else (None, None)
    ok = len(points) == POINTS and distinct and col == 0 and empty == []
    return {"points": len(points), "distinct": distinct, "collinear_triples": col, "convex_hexagons": convex,
            "empty_hexagons": None if empty is None else len(empty), "empty_examples": (empty or [])[:3],
            "layers": layers(points) if distinct else None, "witness_ok": 1 if ok else 0}


def general_with(points, q):
    """Whether q is a new point collinear with no two of points."""
    return q not in points and all(orient(a, b, q) != 0 for a, b in itertools.combinations(points, 2))


def extra_points(points, seed, k):
    """Rule 5: (rows, rejected draws). Each row: the new point, the empty hexagons containing it, and whether every
    empty hexagon of the 30 contains it (true by construction when the 29 have none)."""
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    s = Stream(seed, "hexagon/points")
    rows, rejected = [], 0
    while len(rows) < k:
        q = (min(xs) + s.below(max(xs) - min(xs) + 1), min(ys) + s.below(max(ys) - min(ys) + 1))
        if not general_with(points, q):
            rejected += 1
            if rejected > 1000 * (k + 1):
                raise RuntimeError("the box has almost no point in general position with the witness")
            continue
        _, empty = hexagons(points + [q], containing=len(points))
        rows.append({"point": list(q), "empty_hexagons": len(empty),
                     "example": [list(p) for p in empty[0]] if empty else None})
    return rows, rejected


# ---------------------------------------------------------------- the tools, built here

def safe_extract(archive, top, dest):
    """The regular files of a .tar.gz under top/, written to dest. A path outside top/ is refused; links are skipped
    (CaDiCaL's tarball has one, src/configure -> ../configure, which this build does not use); anything else that is
    not a file or a directory is refused."""
    with tarfile.open(archive, "r:gz") as tar:
        for m in tar.getmembers():
            name = m.name
            if name.startswith("/") or ".." in name.split("/") or not (name == top or name.startswith(top + "/")):
                raise Refused(f"{archive}: {name!r} is outside {top}/")
            if m.isdir() or m.issym() or m.islnk():
                continue
            if not m.isfile():
                raise Refused(f"{archive}: {name!r} is not a regular file")
            target = os.path.join(dest, name)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with tar.extractfile(m) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
    return os.path.join(dest, top)


def run_quiet(cmd, what, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        raise RuntimeError(f"{what} failed ({r.returncode}): {r.stdout.decode(errors='replace')[-2000:]}")
    return r.stdout.decode(errors="replace")


def build_tools(inputs, build):
    """CaDiCaL from Debian's source tarball (g++ CADICAL_FLAGS on every src/*.cpp but mobical.cpp, then linked) and
    cake_lpr from its two files (gcc CAKE_FLAGS, as its Makefile does), in build/: their paths and versions."""
    os.makedirs(build, exist_ok=True)
    src = os.path.join(safe_extract(os.path.join(inputs, "cadical_2.1.3.orig.tar.gz"), CADICAL_DIR, build), "src")
    files = sorted(f for f in os.listdir(src) if f.endswith(".cpp") and f != "mobical.cpp")
    objs = os.path.join(build, "obj")
    os.makedirs(objs, exist_ok=True)
    with ThreadPoolExecutor(WORKERS) as pool:
        list(pool.map(lambda f: run_quiet(["g++", *CADICAL_FLAGS, "-c", os.path.join(src, f), "-o",
                                           os.path.join(objs, f[:-4] + ".o")], f"g++ {f}"), files))
    cadical = os.path.join(build, "cadical")
    run_quiet(["g++", "-O3", "-o", cadical] + [os.path.join(objs, f[:-4] + ".o") for f in files], "linking CaDiCaL")
    cake = os.path.join(build, "cake_lpr")
    run_quiet(["gcc", *CAKE_FLAGS, os.path.join(inputs, "basis_ffi.c"), os.path.join(inputs, "cake_lpr.S"), "-o", cake],
              "assembling cake_lpr")
    version = run_quiet([cadical, "--version"], "cadical --version").strip()
    shutil.rmtree(objs)                       # only the two programs stay in build/
    shutil.rmtree(os.path.dirname(src))
    return {"cadical": cadical, "cake_lpr": cake, "cadical_version": version, "cadical_files": len(files),
            "gcc": run_quiet(["gcc", "-dumpfullversion"], "gcc -dumpfullversion").strip()}


# ---------------------------------------------------------------- solving, with the proof streamed into the checker

def model(text):
    """The literals of CaDiCaL's "v" lines."""
    lits = []
    for line in text.splitlines():
        if line.startswith("v "):
            lits.extend(int(t) for t in line[2:].split())
    if not lits or lits[-1] != 0:
        raise Refused("solver: a model that does not end in 0")
    return set(lits[:-1])


def satisfies(assignment, clauses):
    """How many clauses no literal of the assignment satisfies, after checking it assigns no variable both ways."""
    if any(-lit in assignment for lit in assignment):
        raise Refused("solver: a model with a variable both true and false")
    return sum(1 for c in clauses if not any(lit in assignment for lit in c))


def solve(tools, cnf, work, tag, heap=HEAP_MB, stack=STACK_MB, proof=True):
    """CaDiCaL on cnf; with proof, its LRAT proof goes down a pipe into cake_lpr as it is written. A dict: the
    solver's answer ("unsat", "sat" or "error"), the model's text if satisfiable, whether cake_lpr verified it."""
    paths = {k: os.path.join(work, f"{tag}.{k}") for k in ("so", "se", "co", "ce")}
    files = {k: open(p, "wb") for k, p in paths.items()}
    started = time.monotonic()
    try:
        checker = None
        if proof:
            r, w = os.pipe()
            try:
                checker = subprocess.Popen([tools["cake_lpr"], f"--CML_HEAP_SIZE={heap}", f"--CML_STACK_SIZE={stack}",
                                            cnf, f"/proc/self/fd/{r}"], stdin=subprocess.DEVNULL, stdout=files["co"],
                                           stderr=files["ce"], pass_fds=(r,))
                solver = subprocess.Popen([tools["cadical"], "--lrat", "--binary=true", cnf, f"/proc/self/fd/{w}"],
                                          stdin=subprocess.DEVNULL, stdout=files["so"], stderr=files["se"], pass_fds=(w,))
            finally:
                os.close(r)   # the checker and the solver hold the only ends: when the solver exits, the checker
                os.close(w)   # reads to the end of the proof, whatever happened
        else:
            solver = subprocess.Popen([tools["cadical"], cnf], stdin=subprocess.DEVNULL, stdout=files["so"],
                                      stderr=files["se"])
        solver_rc = solver.wait()
        solved = time.monotonic()
        checker_rc = checker.wait() if checker else None
    finally:
        for f in files.values():
            f.close()
    text = {}
    for k, p in paths.items():
        with open(p, "rb") as f:
            text[k] = f.read().decode(errors="replace")
        os.unlink(p)
    status = [line for line in text["so"].splitlines() if line.startswith("s ")]
    conflicts = re.search(r"^c conflicts:\s+(\d+)", text["so"], re.M)
    answer = ("unsat" if solver_rc == 20 and status == ["s UNSATISFIABLE"] else
              "sat" if solver_rc == 10 and status == ["s SATISFIABLE"] else "error")
    verified = bool(checker and checker_rc == 0 and "s VERIFIED UNSAT" in text["co"].splitlines())
    tail = (text["ce"] + text["co"]).strip().splitlines()[-1:] if checker else []
    return {"answer": answer, "solver_rc": solver_rc, "checker_rc": checker_rc, "verified": verified,
            "conflicts": int(conflicts.group(1)) if conflicts else None, "seconds": round(solved - started, 1),
            "checker_said": tail[0][:200] if tail else "",
            "solver_said": (text["se"].strip().splitlines() or [""])[-1][:200],
            "model": text["so"] if answer == "sat" else None,
            "resources": bool(checker) and not verified and bool(re.search(r"heap|stack|exhausted|alloc", text["ce"]))}


def clause_lines(clauses):
    """Clauses as DIMACS lines."""
    return b"".join(b" ".join(b"%d" % lit for lit in c) + b" 0\n" for c in clauses)


def with_units(header_vars, clause_count, body, units):
    """A DIMACS CNF: the formula's body with each literal of units added as a unit clause."""
    lines = b"".join(b"%d 0\n" % lit for lit in units)
    return b"p cnf %d %d\n" % (header_vars, clause_count + len(units)) + body + lines


# ---------------------------------------------------------------- coverage structure

def coverage_structure(formula, cubes, coverage):
    """Rule 3's classification of the coverage formula's clauses: counts of those in F, negated cubes, and clauses
    with a variable found in no other clause; anything else is refused by the caller (other > 0)."""
    in_f = {frozenset(c) for c in formula}
    negated = {frozenset(-lit for lit in c): i for i, c in enumerate(cubes)}
    occurs = {}
    for c in coverage:
        for lit in c:
            occurs[abs(lit)] = occurs.get(abs(lit), 0) + 1
    counts = {"from_formula": 0, "negated_cubes": 0, "pure": 0, "other": 0}
    covered = set()
    for c in coverage:
        s = frozenset(c)
        if s in negated:
            counts["negated_cubes"] += 1
            covered.add(negated[s])
        elif s in in_f:
            counts["from_formula"] += 1
        elif any(occurs[abs(lit)] == 1 for lit in c):
            counts["pure"] += 1
        else:
            counts["other"] += 1
    counts["cubes_covered"] = len(covered)
    return counts


# ---------------------------------------------------------------- the proof controls

def pigeonhole(pigeons):
    """The pigeonhole formula: pigeons pigeons, pigeons - 1 holes, variable (p - 1)(pigeons - 1) + h for pigeon p in
    hole h (both from 1)."""
    holes = pigeons - 1
    v = lambda p, h: (p - 1) * holes + h  # noqa: E731
    clauses = [tuple(v(p, h) for h in range(1, holes + 1)) for p in range(1, pigeons + 1)]
    clauses += [(-v(p, h), -v(q, h)) for h in range(1, holes + 1)
                for p, q in itertools.combinations(range(1, pigeons + 1), 2)]
    return pigeons * holes, clauses


def lrat_lines(text):
    """An ASCII LRAT proof as (lines, additions): additions maps a clause number to (line index, literals, hints)."""
    lines = [line for line in text.splitlines() if line.strip()]
    additions = {}
    for k, line in enumerate(lines):
        toks = line.split()
        if len(toks) > 1 and toks[1] == "d":
            continue
        nums = [int(t) for t in toks]
        z = nums.index(0, 1)
        additions[nums[0]] = (k, nums[1:z], nums[z + 1:-1])
    return lines, additions


def proof_controls(tools, work):
    """Rule 4's proof controls on the pigeonhole formula: (rows, how many behaved as required)."""
    nv, clauses = pigeonhole(PIGEONS)
    cnf = os.path.join(work, "php.cnf")
    with open(cnf, "wb") as f:
        f.write(b"p cnf %d %d\n" % (nv, len(clauses)) + clause_lines(clauses))
    proof = os.path.join(work, "php.lrat")
    r = subprocess.run([tools["cadical"], "-q", "--lrat", "--binary=false", cnf, proof], stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    with open(proof) as f:
        lines, additions = lrat_lines(f.read())
    last = max(additions)
    if r.returncode != 20 or additions[last][1] != []:
        raise RuntimeError("the pigeonhole formula did not give an LRAT proof ending in the empty clause")
    lemmas = [h for h in additions[last][2] if h > len(clauses)]   # lemmas, not original clauses, the last step cites
    if not lemmas:
        raise RuntimeError("the pigeonhole proof's last step cites no lemma")
    cited = lemmas[0]
    variants = (("accepted as written", lines, True),
                ("rejected without its last step", [x for k, x in enumerate(lines) if k != additions[last][0]], False),
                (f"rejected without lemma {cited}, which the last step cites",
                 [x for k, x in enumerate(lines) if k != additions[cited][0]], False))
    rows, passed = [], 0
    for what, body, accept in variants:
        path = os.path.join(work, "php-variant.lrat")
        with open(path, "w") as f:
            f.write("\n".join(body) + "\n")
        c = subprocess.run([tools["cake_lpr"], f"--CML_HEAP_SIZE={HEAP_MB}", f"--CML_STACK_SIZE={STACK_MB}", cnf, path],
                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ok = (c.returncode == 0 and b"s VERIFIED UNSAT" in c.stdout.splitlines()) == accept
        passed += ok
        rows.append({"control": f"pigeonhole proof {what}", "steps": len(lines), "passed": ok,
                     "checker_said": (c.stdout + c.stderr).decode(errors="replace").strip()[-200:]})
    return rows, passed


# ---------------------------------------------------------------- the run

def summarise(values):
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters")
    return out


def in_child(fn, *args):
    """fn(*args) in a forked child process, so that the memory the big inputs take while they are read is returned
    when it exits (in the sandbox's 4 GB, beside two checkers of 1 GB each); in this process if no child can be made."""
    try:
        context = multiprocessing.get_context("fork")
        pool = ProcessPoolExecutor(1, mp_context=context)
    except (OSError, ValueError, ImportError) as e:   # no fork, or no shared memory for the pool's locks
        print(f"hexagon/check.py: no child process ({e}); reading in this one", file=sys.stderr)
        return fn(*args)
    with pool:
        return pool.submit(fn, *args).result()


def prepare(inputs, work, tools, chosen):
    """The heavy reading, in a child process: F, the cubes and the coverage formula read and checked; rule 3's
    classification; rule 4's weakened formula solved and its model checked; the chosen cubes' literals."""
    variables, formula, header, _ = parse_cnf(load(inputs, "final-30-ours-flat.cnf"), "formula")
    cubes = parse_cubes(load(inputs, "marijn-cubes.icnf"), variables)
    if len(cubes) != CUBES_TOTAL:
        raise Refused(f"cubes: {len(cubes)}, not {CUBES_TOTAL}")
    _, coverage, _, _ = parse_cnf(load(inputs, "cube_tautology.cnf"), "coverage formula")
    structure = coverage_structure(formula, cubes, coverage)
    del coverage
    if not all(len(c) == 3 for c in formula[:WEAK_KEEP]) or len(formula[WEAK_KEEP]) == 3:
        raise Refused(f"formula: its first {WEAK_KEEP} clauses are not its opening block of 3-literal clauses")
    weak = os.path.join(work, "weak.cnf")
    with open(weak, "wb") as f:
        f.write(b"p cnf %d %d\n" % (variables, WEAK_KEEP) + clause_lines(formula[:WEAK_KEEP]))
    r = solve(tools, weak, work, "weak", proof=False)
    os.unlink(weak)
    kept = removed = None
    if r["answer"] == "sat":
        m = model(r["model"])
        kept, removed = satisfies(m, formula[:WEAK_KEEP]), satisfies(m, formula[WEAK_KEEP:])
    return {"variables": variables, "clauses": len(formula), "header": header.decode(),
            "distinct_clauses": len({frozenset(c) for c in formula}), "structure": structure,
            "chosen": [cubes[i] for i in chosen],
            "weak": {"control": f"formula cut to its first {WEAK_KEEP} clauses: satisfiable, model checked",
                     "passed": r["answer"] == "sat" and kept == 0 and removed > 0, "answer": r["answer"],
                     "kept_clauses_violated": kept, "removed_clauses_violated": removed, "seconds": r["seconds"]}}


def check_models(inputs, found):
    """For each (cube, model text) a solver called satisfiable: the clauses of F and the cube's units it violates."""
    _, formula, _, _ = parse_cnf(load(inputs, "final-30-ours-flat.cnf"), "formula")
    out = []
    for cube, text in found:
        m = model(text)
        out.append(satisfies(m, formula) + satisfies(m, [(lit,) for lit in cube]))
    return out


def run(seed, inputs="inputs", results="results", cubes_wanted=CUBES, extra=EXTRA, tools=None, log=print):
    """Every rule, in order; returns (outputs, detail). tools, if given, replaces the build (tests only)."""
    started = time.monotonic()
    data = {name: load(inputs, name) for name, *_ in INPUTS}   # every input checked before anything runs
    geo, flat = data["Geo.lean"].decode("utf-8"), data["final-30-ours-flat.cnf"]
    del data
    detail = {"inputs": [{"name": n, "sha256": h, "bytes": b, "source": s} for n, h, b, s in INPUTS]}
    values = {}

    # Rule 1: the witness, and its controls.
    points = parse_points(geo)
    w = witness(points)
    log(f"hexagon: witness {w['points']} points, {w['collinear_triples']} collinear triples, "
        f"{w['convex_hexagons']} convex hexagons, {w['empty_hexagons']} empty, layers {w['layers']}")
    values.update({"witness_ok": w["witness_ok"], "witness_collinear_triples": w["collinear_triples"],
                   "witness_convex_hexagons": w["convex_hexagons"], "witness_empty_hexagons": w["empty_hexagons"],
                   "witness_layers": ",".join(map(str, w["layers"] or []))})
    moved = [(2 * points[2][0] - points[1][0], 2 * points[2][1] - points[1][1])] + points[1:]
    broken = witness(moved)
    if not general_with(points, ADDED):
        raise AssertionError(f"{ADDED} is not in general position with the witness")
    added_convex, added_empty = hexagons(points + [ADDED], containing=len(points))
    controls = [
        {"control": "witness with its first point moved onto the line through its second and third: fails",
         "passed": broken["witness_ok"] == 0 and broken["collinear_triples"] > 0,
         "collinear_triples": broken["collinear_triples"]},
        {"control": f"witness with {ADDED} added: an empty hexagon", "passed": len(added_empty) > 0,
         "empty_hexagons": len(added_empty), "example": [list(p) for p in added_empty[0]] if added_empty else None},
    ]

    # Rule 5: seeded extra points.
    rows, rejected = extra_points(points, seed, extra)
    log(f"hexagon: {len(rows)} seeded 30th points, {rejected} draws rejected, "
        f"{sum(1 for r in rows if r['empty_hexagons'] > 0)} with an empty hexagon")
    values.update({"extra_sets_checked": len(rows), "extra_rejected": rejected,
                   "extra_sets_with_hole": sum(1 for r in rows if r["empty_hexagons"] > 0)})
    detail["extra_points"] = rows

    # The tools.
    os.makedirs(results, exist_ok=True)
    if tools is None:
        if platform.machine() not in ("x86_64", "AMD64"):
            raise SystemExit("hexagon/check.py: cake_lpr.S is x86-64 assembly; run this on an x86-64 machine")
        tools = build_tools(os.path.abspath(inputs), os.path.abspath(os.path.join(results, "build")))
        log(f"hexagon: built CaDiCaL {tools['cadical_version']} ({tools['cadical_files']} files) and cake_lpr, "
            f"gcc {tools['gcc']}, at {time.monotonic() - started:.0f} s")
    chosen = sample(seed, "hexagon/cubes", CUBES_TOTAL, cubes_wanted)
    work = tempfile.mkdtemp(prefix="hexagon-")
    try:
        # The formula, the cubes and the coverage formula, read and checked in a child; rule 4's weakened formula.
        prep = in_child(prepare, inputs, work, tools, chosen)
        structure = prep["structure"]
        log(f"hexagon: coverage formula {structure}")
        controls.append(prep["weak"])
        rows_p, _ = proof_controls(tools, work)
        controls.extend(rows_p)
        log(f"hexagon: controls {sum(1 for c in controls if c['passed'])} of {len(controls)} passed")
        _, _, body = flat.partition(b"\n")
        if not body.endswith(b"\n"):
            body += b"\n"
        units = dict(zip(chosen, prep["chosen"]))

        # Rules 2 and 3: the sampled cubes and the coverage formula, two at a time.
        def job(item, heap=HEAP_MB, stack=STACK_MB):
            kind, i = item
            if kind == "coverage":
                return solve(tools, os.path.abspath(os.path.join(inputs, "cube_tautology.cnf")), work, "coverage",
                             heap, stack)
            path = os.path.join(work, f"cube-{i + 1}.cnf")
            with open(path, "wb") as f:
                f.write(with_units(prep["variables"], prep["clauses"], body, units[i]))
            try:
                return solve(tools, path, work, f"cube-{i + 1}", heap, stack)
            finally:
                os.unlink(path)

        items = [("coverage", None)] + [("cube", i) for i in chosen]
        done = []
        with ThreadPoolExecutor(WORKERS) as pool:
            for item, r in zip(items, pool.map(job, items)):
                done.append(r)
                log(f"hexagon: {item[0]} {'' if item[1] is None else item[1] + 1}: {r['answer']}, "
                    f"verified {r['verified']}, {r['conflicts']} conflicts, {r['seconds']} s")
        for k, item in enumerate(items):   # a check that ran out of room, again, alone, with more
            if done[k]["resources"]:
                log(f"hexagon: {item[0]} {'' if item[1] is None else item[1] + 1}: cake_lpr ran out of room; again "
                    f"with {RETRY_HEAP_MB} MB")
                done[k] = dict(job(item, RETRY_HEAP_MB, RETRY_STACK_MB), retried=True)
        cover, per_cube = done[0], done[1:]
        found = [(units[i], r["model"]) for i, r in zip(chosen, per_cube) if r["answer"] == "sat"]
        if found:   # a satisfiable cube: its model checked against F and the cube
            violations = iter(in_child(check_models, inputs, found))
            for r in per_cube:
                if r["answer"] == "sat":
                    r["model_violates"] = next(violations)
        for r in done:
            r["model"] = None
    finally:
        shutil.rmtree(work, ignore_errors=True)

    structure_ok = structure["other"] == 0 and structure["cubes_covered"] == CUBES_TOTAL
    values.update({
        "cubes_sampled": len(chosen), "cubes_ids": ",".join(str(i + 1) for i in chosen),
        "cubes_unsat": sum(1 for r in per_cube if r["answer"] == "unsat"),
        "cubes_verified": sum(1 for r in per_cube if r["answer"] == "unsat" and r["verified"]),
        "coverage_clauses": ",".join(f"{k}={structure[k]}" for k in ("negated_cubes", "cubes_covered", "from_formula",
                                                                     "pure", "other")),
        "coverage_unsat": 1 if cover["answer"] == "unsat" else 0,
        "coverage_verified": 1 if cover["answer"] == "unsat" and cover["verified"] else 0,
        "controls_passed": sum(1 for c in controls if c["passed"]), "controls_total": len(controls),
        "solver": f"CaDiCaL {tools['cadical_version']} (Debian orig tarball; g++ {' '.join(CADICAL_FLAGS)})",
        "checker": CHECKER,
    })
    coverage_ok = structure_ok and values["coverage_verified"] == 1
    values["test_passed"] = 1 if (values["witness_ok"] == 1 and values["cubes_verified"] == len(chosen) == cubes_wanted
                                  and coverage_ok) else 0
    detail.update({"values": values, "witness": w, "witness_moved": broken, "controls": controls,
                   "added_point": {"point": list(ADDED), "convex_hexagons_with_it": added_convex,
                                   "empty_hexagons": len(added_empty)},
                   "formula": {k: prep[k] for k in ("variables", "clauses", "header", "distinct_clauses")},
                   "coverage": {"structure": structure, **cover},
                   "cubes": [{"cube": i + 1, "literals": len(units[i]), **r} for i, r in zip(chosen, per_cube)],
                   "tools": {k: v for k, v in tools.items() if k not in ("cadical", "cake_lpr")},
                   "seconds": round(time.monotonic() - started, 1)})
    return summarise(values), detail


def main():
    parser = argparse.ArgumentParser(description="h(6) = 30: the witness, the proof sampled, the coverage")
    parser.add_argument("--cubes", type=int, default=CUBES, help=f"cubes to re-solve (default {CUBES})")
    parser.add_argument("--extra", type=int, default=EXTRA, help=f"seeded 30th points (default {EXTRA})")
    args = parser.parse_args()
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, detail = run(seed, cubes_wanted=args.cubes, extra=args.extra,
                          log=lambda line: print(line, file=sys.stderr, flush=True))
    except Refused as e:
        sys.exit(f"hexagon/check.py: refused: {e}")
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
