#!/usr/bin/env python3
"""Two disjoint 5-holes in every set of 17 points: Scheucher's SAT instance written again, refuted again, and the
refutation checked by a verified checker, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:3f9aeb39e61fa85d) is from Scheucher, "Two disjoint
5-holes in point sets", Computational Geometry 91, 101670 (2020), arXiv:1807.10848v4: "We use computer assistance to
show that every set of 17 points in general position admits two disjoint 5-holes, that is, holes with disjoint
respective convex hulls." Its registered test: refuted if 17 points in general position can be placed with no two
disjoint 5-holes; checked as the paper checks it, by the SAT instance its program writes for 17 points (h55.py in the
e-print's ancillary files; 23,392 variables and 825,689 clauses, as the paper prints), which must be unsatisfiable.

The inputs, each checked against its SHA-256 and size before anything else runs: the e-print (the claim's data of
record), and the solver and checker of hexagon/check.py, compiled from source into results/build in the pinned image
with no network (CaDiCaL 2.1.3 as Debian archived it; the CakeML-verified LRAT checker cake_lpr). The e-print is read
as data: its program is never run here. Every rule below was fixed before any seed existed.

1. The e-print. Its anc/h55.py must have the committed SHA-256; its draft.tex must print the instance's size ("825\\,689
   constraints in 23\\,392 variables"); its figs/n16.psz must hold 16 points with integer coordinates (the paper's set
   of 16 points without two disjoint 5-holes). Otherwise the run is refused.
2. The formula. encode(n) is h55.py transcribed into Python 3, clause for clause and in the same order, with the
   same numbering of its variables: (1) the alternating axioms of the triple orientations, (2) the signotope axioms,
   (3) every point sorted around point 0, (4) to (6) the extremal segments, convex position, inner points and empty
   triangles of every four and three points, (7) the 5-holes, (8) for every ordered pair a, b, no 5-hole through a
   wholly left of the line ab together with one through b wholly right of it (two disjoint convex polygons are
   separated by a line through a vertex of each), and (9) the windows Harborth's theorem gives (every ten points hold
   a 5-hole). Its DIMACS text, written as the program writes it, must have the SHA-256 of the file the author's program
   writes for that n (FORMULA_SHA256: computed for 16 and 17 by running the e-print's h55.py under Python 2.7, in a
   container without network, on 12 October 2026). So the formula refuted below is the paper's own, byte for byte.
3. The proof. The 17-point formula is renamed and shuffled by the seed (es/check.py's rule 6: the variables by a
   permutation, then the clauses' order, then each clause's literals), and CaDiCaL solves it with its LRAT proof
   streamed down a pipe into cake_lpr; a check that runs out of cake_lpr's heap or stack is repeated with a larger
   one. unsat_verified is 1 when CaDiCaL reports UNSATISFIABLE and cake_lpr "s VERIFIED UNSAT" on that formula.
4. Controls, each of which must behave as stated (controls_passed counts those that do):
   a. the witness: the 16 points of figs/n16.psz are in general position, and of their 5-holes (exact integer
      geometry: convex position and no other point inside) no two have disjoint convex hulls (decided by an edge of
      one of them with the other strictly on its far side, the separating axis test);
   b. the witness admitted: its points, the lowest first and the rest counterclockwise around it (so point 0 is a
      vertex of the hull and every o(0, b, c) is positive), with every variable of
      the 16-point formula given its geometric meaning (the orientations; for every four and three points the extremal
      segments, convex position, inner point and emptiness; the 5-holes; hole_left(a, b) and hole_right(a, b) exactly
      when a 5-hole as clause (8) describes exists), satisfy every clause of that formula;
   c. the definitions: for GEO_SETS sets of GEO_POINTS points drawn by the seed, the geometric assignment satisfies
      every clause of groups (1) to (7), and changing any one variable of groups (4) to (6), or a true 5-hole variable,
      breaks one: so those clauses define the geometry, not just admit it;
   d. the theorem's direction: RANDOM17 sets of 17 points drawn by the seed each have two disjoint 5-holes (exact
      geometry), and each one's geometric assignment breaks a clause of group (8) or (9) of the 17-point formula;
   e. hexagon's three pigeonhole proof controls: an LRAT proof accepted, and rejected without its last step or
      without a lemma that step cites.
5. test_passed is 1 if the formula is the author's (rule 2), the e-print prints its size (rule 1) and unsat_verified
   is 1; else 0. The controls are reported beside it.
6. Randomness, only from ECDYSIS_SEED: the shuffle as es/check.py's (label "es/shuffle"), the point sets from the
   labels "holes/points" and "holes/random17", through hexagon's Stream (SHA-256 in counter mode).

What it cannot check: the paper's lemmas that make the formula a model of the theorem (sorting around a point of the
hull, the separation by a line through two vertices, and Harborth's theorem in clause group 9), which are argued in
the paper rather than computed, though controls b to d test the encoding against real point sets; and the tools
beyond themselves: cake_lpr is verified in CakeML down to its assembly, but its C wrapper, the compiler, the kernel and
this script (the transcription and the shuffle) are trusted.

Writes results/outputs.json (20 values) and results/detail.json. Run with: python3 holes/h55.py
"""

import functools
import hashlib
import importlib.util
import io
import itertools
import json
import os
import re
import sys
import tarfile
import tempfile
import time
from itertools import combinations, permutations

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("holes_es", os.path.join(HERE, "..", "es", "check.py"))
E = importlib.util.module_from_spec(_spec)
sys.modules["holes_es"] = E
_spec.loader.exec_module(E)
H = E.H

EPRINT = ("arXiv-1807.10848v4.tar.gz", "60405c83d86bb99a498ccbc44f143453e7a5beec1696542ac92a21d5b288ddde", 1242929)
INPUTS = (EPRINT,) + tuple(i[:3] for i in E.INPUTS)
PROGRAM = ("anc/h55.py", "febc39843fb81ee95b8e56b7214effae9373b80b04c4f41d31e9602f8eda3047")
TEX, WITNESS = "draft.tex", "figs/n16.psz"
PRINTED_SIZE = r"825\,689 constraints in 23\,392 variables"
FORMULA_SHA256 = {16: "7ff824f95b05851898d4a5cf18f7c17ba5d8885d511127283fd25e13ea3388ad",
                  17: "fa0e57ea5361fb320394d84e4a5cdc4244890c68b979bb3d41e87025cc70ae04"}
N_PROOF = 17
GEO_SETS, GEO_POINTS, RANDOM17, RANGE = 12, 11, 4, 10 ** 6
HEAP_MB, STACK_MB = 2560, 768
RETRY_HEAP_MB, RETRY_STACK_MB = 3200, 768
GROUPS = ("(1) alternating", "(2) signotope", "(3) sorted", "(4) segments", "(5) 4-gons", "(6) 3-holes", "(7) 5-holes",
          "(8) disjoint", "(9) Harborth")
OUTPUTS = ("formula_is_authors", "printed_size", "cnf_vars", "cnf_clauses", "cnf_sha256", "unsat_answer",
           "unsat_verified", "proof_conflicts", "witness_points", "witness_holes", "witness_disjoint_pairs",
           "witness_admitted", "geo_violations", "geo_unforced", "random17_caught", "controls_passed", "controls_total",
           "solver", "checker", "test_passed")


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


# ---------------------------------------------------------------- rule 1: the e-print

def eprint_files(data):
    """{name: bytes} for the three files rule 1 reads, from the e-print read in memory (nothing written to disk)."""
    want, out = (PROGRAM[0], TEX, WITNESS), {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for m in tar.getmembers():
            if m.name in want and m.isfile():
                out[m.name] = tar.extractfile(m).read()
    missing = [w for w in want if w not in out]
    if missing:
        raise Refused(f"the e-print lacks {missing}")
    return out


def parse_psz(text):
    """A .psz file: the number of points, then one "x y" pair of integers a line."""
    lines = [ln.split() for ln in text.strip().splitlines() if ln.strip()]
    n = int(lines[0][0])
    pts = [(int(x), int(y)) for x, y in lines[1:]]
    if len(pts) != n or len(set(pts)) != n:
        raise Refused(f"the witness holds {len(pts)} points ({len(set(pts))} distinct), not {n}")
    return pts


def read_eprint(data):
    files = eprint_files(data)
    got = hashlib.sha256(files[PROGRAM[0]]).hexdigest()
    if got != PROGRAM[1]:
        raise Refused(f"{PROGRAM[0]}: sha256 {got}, not the committed {PROGRAM[1]}")
    printed = PRINTED_SIZE in files[TEX].decode("utf-8", errors="replace")
    return printed, parse_psz(files[WITNESS].decode("ascii"))


# ---------------------------------------------------------------- rule 2: h55.py, transcribed

class Formula:
    """h55.py's variables (numbered in its order) and clauses (in its order), with each clause's group."""

    def __init__(self, n):
        N = range(n)
        names = []
        names += [("trip", I) for I in permutations(N, 3)]
        for kind in ("extr_ab", "extr_cd", "convpos", "b_inner", "c_inner"):
            names += [(kind, I) for I in combinations(N, 4)]
        names += [("emptytr", I) for I in combinations(N, 3)]
        names += [("is5hole", I) for I in combinations(N, 5)]
        names += [("hole_left", I) for I in permutations(N, 2)]
        names += [("hole_right", I) for I in permutations(N, 2)]
        self.n, self.names = n, names
        self.index = {v: i + 1 for i, v in enumerate(names)}
        self.clauses, self.groups = [], []
        self._build(n, N)

    def v(self, kind, *I):
        return self.index[(kind, I)]

    def add(self, group, clause):
        self.clauses.append(clause)
        self.groups.append(group)

    def _build(self, n, N):
        v = self.v
        for a, b, c in combinations(N, 3):                                    # (1)
            for s in (+1, -1):
                t = v("trip", a, b, c)
                self.add(0, [s * t, -s * v("trip", b, c, a)])
                self.add(0, [s * t, -s * v("trip", c, a, b)])
                self.add(0, [s * t, s * v("trip", c, b, a)])
                self.add(0, [s * t, s * v("trip", b, a, c)])
                self.add(0, [s * t, s * v("trip", a, c, b)])
        for I4 in combinations(N, 4):                                         # (2)
            for t1, t2, t3 in combinations(list(combinations(I4, 3)), 3):
                for s in (+1, -1):
                    self.add(1, [s * v("trip", *t1), -s * v("trip", *t2), s * v("trip", *t3)])
        for b, c in combinations(range(1, n), 2):                             # (3)
            self.add(2, [v("trip", 0, b, c)])
        for I in combinations(N, 4):                                          # (4)
            a, b, c, d = I
            ab, cd = v("extr_ab", *I), v("extr_cd", *I)
            self.add(3, [-ab, v("trip", a, b, c), -v("trip", a, b, d)])
            self.add(3, [-ab, -v("trip", a, b, c), v("trip", a, b, d)])
            self.add(3, [ab, v("trip", a, b, c), v("trip", a, b, d)])
            self.add(3, [ab, -v("trip", a, b, c), -v("trip", a, b, d)])
            self.add(3, [-cd, v("trip", a, c, d), -v("trip", b, c, d)])
            self.add(3, [-cd, -v("trip", a, c, d), v("trip", b, c, d)])
            self.add(3, [cd, v("trip", a, c, d), v("trip", b, c, d)])
            self.add(3, [cd, -v("trip", a, c, d), -v("trip", b, c, d)])
        for I in combinations(N, 4):                                          # (5)
            ab, cd, cp = v("extr_ab", *I), v("extr_cd", *I), v("convpos", *I)
            bi, ci = v("b_inner", *I), v("c_inner", *I)
            self.add(4, [-cp, ab])
            self.add(4, [-cp, cd])
            self.add(4, [cp, -ab, -cd])
            self.add(4, [bi, ci, cp])
            self.add(4, [-bi, -ci])
            self.add(4, [-bi, -cp])
            self.add(4, [-ci, -cp])
            self.add(4, [bi, ab])
            self.add(4, [-bi, -ab])
            self.add(4, [ci, cd])
            self.add(4, [-ci, -cd])
        for a, b, c in combinations(N, 3):                                    # (6)
            e = v("emptytr", a, b, c)
            self.add(5, [e] + [v("b_inner", a, i, b, c) for i in range(a + 1, b)]
                     + [v("c_inner", a, b, i, c) for i in range(b + 1, c)])
            for i in range(a + 1, b):
                self.add(5, [-e, -v("b_inner", a, i, b, c)])
            for i in range(b + 1, c):
                self.add(5, [-e, -v("c_inner", a, b, i, c)])
        for I in combinations(N, 5):                                          # (7)
            self.add(6, [-v("convpos", *J) for J in combinations(I, 4)]
                     + [-v("emptytr", *J) for J in combinations(I, 3)] + [v("is5hole", *I)])
        for a, b in permutations(N, 2):                                       # (8)
            for I in combinations(N, 5):
                if a in I and b not in I:
                    self.add(7, [-v("is5hole", *I)] + [-v("trip", a, b, c) for c in I if c != a]
                             + [v("hole_left", a, b)])
                if a not in I and b in I:
                    self.add(7, [-v("is5hole", *I)] + [v("trip", a, b, c) for c in I if c != b]
                             + [v("hole_right", a, b)])
            self.add(7, [-v("hole_left", a, b), -v("hole_right", a, b)])
        for k in range(10, n):                                                # (9)
            self.add(8, [v("is5hole", *I) for I in combinations(range(k - 10, k), 5)])
        for I in combinations(range(0, n - 10), 5):
            self.add(8, [-v("is5hole", *I)])
        for I in combinations(range(10, n), 5):
            self.add(8, [-v("is5hole", *I)])

    def dimacs(self):
        """The text h55.py writes: its header line, then each clause's literals joined by spaces and " 0"."""
        out = [f"p cnf {len(self.names)} {len(self.clauses)}\n"]
        out += [" ".join(str(x) for x in c) + " 0\n" for c in self.clauses]
        return "".join(out).encode("ascii")


# ---------------------------------------------------------------- rule 4: geometry

orient = E.orient


def general_position(pts):
    return all(orient(*t) != 0 for t in combinations(pts, 3))


def convex_position(pts):
    return E.hull_size(list(pts)) == len(pts)


def inside_triangle(p, a, b, c):
    s = [orient(a, b, p) > 0, orient(b, c, p) > 0, orient(c, a, p) > 0]
    return all(s) or not any(s)


def hull_ccw(pts):
    """The vertices of a set in convex position, counterclockwise from the lowest-then-leftmost one."""
    return sorted_around(pts)


def sorted_around(pts):
    """The lowest point (the leftmost of the lowest) first, then the others counterclockwise around it: a vertex of the
    hull first and every other point at an angle in [0, pi) from it, compared by orientation alone (exact)."""
    p0 = min(pts, key=lambda p: (p[1], p[0]))
    rest = [p for p in pts if p != p0]
    return [p0] + sorted(rest, key=functools.cmp_to_key(lambda p, q: -1 if orient(p0, p, q) > 0 else 1))


def holes(pts, k=5):
    """The k-subsets (as index tuples) in convex position with no other point of the set inside."""
    out = []
    for I in combinations(range(len(pts)), k):
        P = [pts[i] for i in I]
        if not convex_position(P):
            continue
        hull = hull_ccw(P)
        empty = True
        for j in range(len(pts)):
            if j in I:
                continue
            q = pts[j]
            if all(orient(hull[i], hull[(i + 1) % k], q) > 0 for i in range(k)):
                empty = False
                break
        if empty:
            out.append(I)
    return out


def disjoint(P, Q):
    """Whether two convex polygons (vertex lists) have disjoint convex hulls: an edge of one with every vertex of the
    other strictly on its far side (the separating axis test, exact in integers)."""
    for A, B in ((P, Q), (Q, P)):
        h = hull_ccw(A)
        for i in range(len(h)):
            u, w = h[i], h[(i + 1) % len(h)]
            if all(orient(u, w, q) < 0 for q in B):
                return True
    return False


def disjoint_pairs(pts, hs):
    return sum(1 for I, J in combinations(hs, 2)
               if not set(I) & set(J) and disjoint([pts[i] for i in I], [pts[j] for j in J]))


def geometric_assignment(F, P):
    """Every variable of F given its geometric meaning for the point list P (in F's order): a set of true literals."""
    n = F.n
    sig = {t: orient(*(P[i] for i in t)) > 0 for t in permutations(range(n), 3)}
    val = {}
    for t, s in sig.items():
        val[("trip", t)] = s
    for I in combinations(range(n), 4):
        a, b, c, d = I
        val[("extr_ab", I)] = sig[(a, b, c)] == sig[(a, b, d)]
        val[("extr_cd", I)] = sig[(a, c, d)] == sig[(b, c, d)]
        val[("convpos", I)] = convex_position([P[i] for i in I])
        val[("b_inner", I)] = inside_triangle(P[b], P[a], P[c], P[d])
        val[("c_inner", I)] = inside_triangle(P[c], P[a], P[b], P[d])
    for I in combinations(range(n), 3):
        val[("emptytr", I)] = not any(inside_triangle(P[j], *(P[i] for i in I)) for j in range(n) if j not in I)
    hs = set(holes(P))
    for I in combinations(range(n), 5):
        val[("is5hole", I)] = I in hs
    for a, b in permutations(range(n), 2):
        val[("hole_left", (a, b))] = any(a in I and b not in I and all(sig[(a, b, c)] for c in I if c != a) for I in hs)
        val[("hole_right", (a, b))] = any(b in I and a not in I and not any(sig[(a, b, c)] for c in I if c != b)
                                          for I in hs)
    return {(F.index[k] if v else -F.index[k]) for k, v in val.items()}


def broken(F, lits, groups):
    return [k for k, c in enumerate(F.clauses) if F.groups[k] in groups and not any(x in lits for x in c)]


def point_sets(seed, label, sets, n):
    stream, out = H.Stream(seed, label), []
    while len(out) < sets:
        pts = [(stream.below(2 * RANGE + 1) - RANGE, stream.below(2 * RANGE + 1) - RANGE) for _ in range(n)]
        if len(set(pts)) < n or not general_position(pts):
            continue
        out.append(sorted_around(pts))
    return out


def definitions_control(seed):
    """Rule 4c: (violations, unforced changes) over the drawn sets."""
    F = None
    violations = unforced = 0
    for P in point_sets(seed, "holes/points", GEO_SETS, GEO_POINTS):
        if F is None:
            F = Formula(GEO_POINTS)
            occurs = {}
            for k, c in enumerate(F.clauses):
                if F.groups[k] <= 6:
                    for x in c:
                        occurs.setdefault(abs(x), []).append(k)
        lits = geometric_assignment(F, P)
        violations += len(broken(F, lits, range(7)))
        for kind in ("extr_ab", "extr_cd", "convpos", "b_inner", "c_inner", "emptytr", "is5hole"):
            for (k2, I), idx in ((key, i) for key, i in F.index.items() if key[0] == kind):
                lit = idx if idx in lits else -idx
                if kind == "is5hole" and lit < 0:
                    continue                                   # only a true 5-hole variable is forced
                flipped = (lits - {lit}) | {-lit}
                if not any(not any(x in flipped for x in F.clauses[k]) for k in occurs.get(idx, [])):
                    unforced += 1
    return violations, unforced


def random17_control(seed, F):
    """Rule 4d: (sets with two disjoint 5-holes, sets whose assignment breaks group 8 or 9)."""
    with_pairs = caught = 0
    for P in point_sets(seed, "holes/random17", RANDOM17, N_PROOF):
        hs = holes(P)
        with_pairs += disjoint_pairs(P, hs) > 0
        caught += bool(broken(F, geometric_assignment(F, P), (7, 8)))
    return with_pairs, caught


# ---------------------------------------------------------------- the run

def prepare(seed, inputs, cnf):
    """Rules 1, 2 and 4a-4d, and the shuffled 17-point formula written to cnf: run in a child process, so that the memory
    the formulas take is returned before the solver and the checker start (in the sandbox's 4 GB)."""
    started = time.monotonic()
    data = load(inputs, EPRINT[0])
    printed, witness = read_eprint(data)
    formulas = {n: Formula(n) for n in (16, N_PROOF)}
    sha = {n: hashlib.sha256(F.dimacs()).hexdigest() for n, F in formulas.items()}
    authors = all(sha[n] == FORMULA_SHA256[n] for n in sha)
    controls = []
    W = sorted_around(witness)                                                      # 4a, 4b
    w_general = general_position(W)
    w_holes = holes(W)
    w_pairs = disjoint_pairs(W, w_holes)
    controls.append({"control": "the witness: general position, no two disjoint 5-holes",
                     "passed": w_general and w_pairs == 0, "holes": len(w_holes), "disjoint_pairs": w_pairs})
    w_broken = broken(formulas[16], geometric_assignment(formulas[16], W), range(9))
    controls.append({"control": "the witness admitted by the 16-point formula", "passed": not w_broken,
                     "broken": len(w_broken), "first": [GROUPS[formulas[16].groups[k]] for k in w_broken[:3]]})
    geo_v, geo_u = definitions_control(seed)                                         # 4c
    controls.append({"control": "the definitions", "passed": geo_v == 0 and geo_u == 0, "violations": geo_v,
                     "unforced": geo_u})
    F = formulas[N_PROOF]
    with_pairs, caught = random17_control(seed, F)                                   # 4d
    controls.append({"control": "random 17-point sets", "passed": with_pairs == RANDOM17 and caught == RANDOM17,
                     "with_disjoint_pairs": with_pairs, "caught": caught})
    nv = len(F.names)                                                                # 3
    clauses, _ = E.renamed(nv, F.clauses, seed)
    text = E.dimacs(nv, clauses)
    with open(cnf, "wb") as f:
        f.write(text)
    return {"printed": printed, "authors": authors, "sha": sha, "controls": controls, "nv": nv,
            "clauses": len(F.clauses), "cnf_sha256": hashlib.sha256(text).hexdigest(), "witness_points": len(W),
            "witness_holes": len(w_holes), "witness_pairs": w_pairs, "witness_admitted": not w_broken,
            "geo_v": geo_v, "geo_u": geo_u, "caught": caught, "seconds": round(time.monotonic() - started, 1)}


def run(seed, inputs="inputs", results="results", tools=None, log=print):
    started = time.monotonic()
    for name, *_ in INPUTS:
        load(inputs, name)
    os.makedirs(results, exist_ok=True)
    work = tempfile.mkdtemp(prefix="h55-", dir=results)
    cnf = os.path.join(work, "h55.cnf")
    pre = H.in_child(prepare, seed, inputs, cnf)
    log(f"h55: formulas and controls in {pre['seconds']} s; the author's formula: {pre['authors']}; "
        f"controls {[c['passed'] for c in pre['controls']]}")
    controls = list(pre["controls"])
    if tools is None:
        tools = H.build_tools(os.path.abspath(inputs), os.path.abspath(os.path.join(results, "build")))
        log(f"h55: built CaDiCaL {tools['cadical_version']} and cake_lpr")
    rows, _ = H.proof_controls(tools, work)                                          # 4e
    controls += rows
    r = H.solve(tools, cnf, work, "h55", heap=HEAP_MB, stack=STACK_MB, proof=True)
    if r["answer"] == "unsat" and not r["verified"] and r["resources"]:
        r = H.solve(tools, cnf, work, "h55", heap=RETRY_HEAP_MB, stack=RETRY_STACK_MB, proof=True)
    os.unlink(cnf)
    log(f"h55: 17 points: {r['answer']}{' (verified)' if r['verified'] else ''}, {r['seconds']} s, "
        f"{r['conflicts']} conflicts")
    unsat_verified = int(r["answer"] == "unsat" and r["verified"])
    passed = sum(1 for c in controls if c["passed"])
    values = {
        "formula_is_authors": int(pre["authors"]), "printed_size": int(pre["printed"]), "cnf_vars": pre["nv"],
        "cnf_clauses": pre["clauses"], "cnf_sha256": pre["cnf_sha256"], "unsat_answer": r["answer"],
        "unsat_verified": unsat_verified, "proof_conflicts": r["conflicts"], "witness_points": pre["witness_points"],
        "witness_holes": pre["witness_holes"], "witness_disjoint_pairs": pre["witness_pairs"],
        "witness_admitted": int(pre["witness_admitted"]), "geo_violations": pre["geo_v"], "geo_unforced": pre["geo_u"],
        "random17_caught": f"{pre['caught']} of {RANDOM17}",
        "controls_passed": passed, "controls_total": len(controls),
        "solver": f"CaDiCaL {tools.get('cadical_version', '2.1.3')}", "checker": H.CHECKER,
        "test_passed": int(pre["authors"] and pre["printed"] and unsat_verified == 1),
    }
    out = {k: values[k] for k in OUTPUTS}
    detail = {"values": values, "controls": controls, "proof": {k: v for k, v in r.items() if k != "model"},
              "formula_sha256": pre["sha"], "seconds": round(time.monotonic() - started, 1)}
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
        out, _ = run(seed, log=lambda s: print(s, file=sys.stderr, flush=True))
    except Refused as e:
        sys.exit(f"holes/h55.py: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
