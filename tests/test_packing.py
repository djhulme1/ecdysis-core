"""The packing-chromatic check on made-up cases: the table read from its figure and anything else refused; violations
counted against a brute-force reference on small tori; the formula's regions read and a placement that differs
refused; each kind of unjustified clause caught; the split's count, order (against a transcription of the authors'
cubes()), unranking and choice of regions; the exact cover check against brute force, failing when any one cube is
removed or a cube is malformed; the cover's parts numbered as written and their proofs checked by a small RUP checker
written here (rejected when a cube is missing); and a cube's outcome read from the solver (a stand-in that stops at
its conflict limit is a timeout, not a failure).

With the real tools (PACKING_TOOLS, a directory holding the cadical and cake_lpr a run built in results/build), also
the small split's controls and a capped solve. With the real inputs (at inputs/ or in PACKING_INPUTS), also the
witness, the reduction, the split's regions and its full order. The stand-in solver is a script, so the temporary
directory must allow execution (in the sandbox, set TMPDIR to a directory under results/).

Run with: python3 -m unittest discover -s tests
"""

import contextlib
import hashlib
import importlib.util
import io
import itertools
import json
import math
import os
import random
import stat
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("packing_check", os.path.join(HERE, "..", "packing", "check.py"))
P = importlib.util.module_from_spec(_spec)
sys.modules["packing_check"] = P
_spec.loader.exec_module(P)

SEED = "a" * 64


def write(path, data):
    with open(path, "wb") as f:
        f.write(data)


def inputs_dir():
    d = os.environ.get("PACKING_INPUTS") or os.path.join(HERE, "..", "inputs")
    return d if all(os.path.isfile(os.path.join(d, name)) and os.path.getsize(os.path.join(d, name)) > 0
                    for name, *_ in P.INPUTS[:3]) else None


def tex(rows, spec=None, label="fig:15", extra=""):
    spec = spec or "c" * len(rows[0])
    body = "\n".join("&".join(map(str, r)) + "\\\\" for r in rows)
    return ("\\begin{figure}\\begin{center}\\resizebox{!}{8cm}{\\tiny\n\\begin{tabular}{%s}\n%s\n\\end{tabular}}\n%s"
            "\\end{center}\\caption{x}\n\\label{%s}\n\\end{figure}\n" % (spec, body, extra, label))


@contextlib.contextmanager
def patched(**values):
    saved = {k: getattr(P, k) for k in values}
    try:
        for k, v in values.items():
            setattr(P, k, v)
        yield
    finally:
        for k, v in saved.items():
            setattr(P, k, v)


# ---------------------------------------------------------------- references, from the definitions

def torus_violations(grid):
    """Unordered pairs of distinct cells of one colour c within toroidal l1 distance c, by every pair."""
    n = len(grid)
    cells = [(i, j) for i in range(n) for j in range(n)]
    out = 0
    for a, b in itertools.combinations(cells, 2):
        c = grid[a[0]][a[1]]
        if c == grid[b[0]][b[1]]:
            di, dj = abs(a[0] - b[0]), abs(a[1] - b[1])
            if min(di, n - di) + min(dj, n - dj) <= c:
                out += 1
    return out


def authors_cubes(var, P_, colours, T, centre=None):
    """A transcription of structured_api.py's cubes() (PackingChromaticTacas@305d6aa) on var[colour index]."""
    rel = list(range(colours, colours - T, -1))
    if centre in rel:
        rel.append(min(rel) - 1)
        rel.remove(centre)
    vpc = {c: var[k] for k, c in enumerate(rel)}
    cbs = []
    for size in range(P_, -1, -1):
        for cmb in itertools.combinations(list(range(T)), size):
            products = itertools.product(*([vpc[rel[i]] for i in cmb]))
            negations = []
            if size != P_:
                for cid, c in enumerate(rel):
                    if cid not in cmb:
                        negations.extend([-1 * v for v in vpc[c]])
            for product in products:
                cbs.append(list(product) + negations)
    return cbs


def covered_by_brute_force(split, cubes):
    """Whether every assignment of the split's variables satisfies one of the cubes."""
    variables = [v for vs in split.var for v in vs]
    for bits in itertools.product((False, True), repeat=len(variables)):
        a = dict(zip(variables, bits))
        if not any(all(a[abs(lit)] == (lit > 0) for lit in c) for c in cubes):
            return False
    return True


def rup_check(clauses, proof):
    """A plain LRAT (RUP hints only) checker, independent of cake_lpr: whether proof derives the empty clause from
    clauses (numbered from 1)."""
    db = {i + 1: tuple(c) for i, c in enumerate(clauses)}
    last = None
    for line in proof.splitlines():
        toks = line.split()
        if not toks:
            continue
        if toks[1] == "d":
            for t in toks[2:-1]:
                db.pop(int(t))
            continue
        nums = [int(t) for t in toks]
        z = nums.index(0, 1)
        lits, hints = nums[1:z], nums[z + 1:-1]
        true = {-lit for lit in lits}
        for h in hints:
            c = db.get(h)
            if c is None or any(lit in true for lit in c):
                return False
            open_ = [lit for lit in c if -lit not in true]
            if not open_:
                break
            if len(open_) > 1:
                return False
            true.add(open_[0])
        else:
            return False
        db[nums[0]] = tuple(lits)
        last = lits
    return last == []


def small(T=4, R=3, P_=3):
    return P.Split([[k * R + t + 1 for t in range(R)] for k in range(T)], P_)


# ---------------------------------------------------------------- the witness

class Witness(unittest.TestCase):
    def test_the_table_is_read_from_its_figure(self):
        rows = [[1, 2, 1], [3, 1, 2]]
        with patched(WIDTH=3):
            self.assertEqual(P.parse_table("text\n" + tex(rows)), rows)
            self.assertEqual(P.parse_table(tex([[9, 9, 9]], label="fig:14") + tex(rows)), rows)

    def test_anything_else_in_the_table_is_refused(self):
        rows = [[1, 2, 1], [3, 1, 2]]
        with patched(WIDTH=3):
            self.assertEqual(P.parse_table(tex(rows)), rows)
        for bad in (tex(rows, label="fig:14"), tex(rows, spec="ccl"), tex(rows).replace("3&1&2", "3&x&2"),
                    tex(rows).replace("3&1&2", "3&1.5&2"), tex(rows, extra="\\begin{tabular}{c}1\\\\\\end{tabular}"),
                    tex(rows).replace("\\begin{figure}", "")):
            with patched(WIDTH=3), self.assertRaises(P.Refused):
                P.parse_table(bad)

    def test_violations_agree_with_every_pair_on_small_tori(self):
        rng = random.Random(5)
        with patched(WIDTH=12, MAX_COLOUR=3):
            for _ in range(20):
                grid = [[rng.choice((1, 1, 1, 2, 3)) for _ in range(12)] for _ in range(12)]
                w = P.witness(grid)
                self.assertEqual(w["violations"], torus_violations(grid))
                self.assertEqual(w["witness_ok"], 1 if w["violations"] == 0 else 0)

    def test_breakages_are_caught(self):
        # 1 on a chessboard as in the real table, 2 elsewhere, one 3 in the last rows (so its copy wraps)
        grid = [[1 if (i + j) % 2 == 0 else 2 for j in range(12)] for i in range(12)]
        grid[10][1] = 3
        with patched(WIDTH=12, MAX_COLOUR=3):
            base = P.witness(grid)["violations"]
            for i, j, c in ((0, 0, 4), (7, 7, 0)):
                g = [r[:] for r in grid]
                g[i][j] = c
                self.assertEqual(P.witness(g)["witness_ok"], 0, (i, j, c))
            self.assertEqual(P.witness(grid[:-1])["witness_ok"], 0)                 # not square
            rows = P.witness_controls(grid)       # the 3 copied 3 rows on, across the edge; a 1 copied right
            self.assertEqual([(r["passed"], r["cell"], r["wraps"]) for r in rows],
                             [(True, [1, 1], True), (True, [0, 1], False)])
            self.assertGreater(base, 0)               # (2s 2 apart: the real table's zero is in RealInputs)

    def test_the_offsets_count_each_pair_once(self):
        for c in range(1, 8):
            offs = P.offsets(c)
            self.assertEqual(len(offs), c * (c + 1))                 # half of the 2c(c + 1) cells within c
            ring = set(offs) | {(-a, -b) for a, b in offs}
            self.assertEqual(ring, {(a, b) for a in range(-c, c + 1) for b in range(-c, c + 1)
                                    if 0 < abs(a) + abs(b) <= c})


# ---------------------------------------------------------------- the reduction

class Reduction(unittest.TestCase):
    def setUp(self):
        self.r = P.CELL_VARS + 1                     # a plus of colour 14 around (0, 0)
        self.plus = [(0, 0), (0, -1), (-1, 0), (1, 0), (0, 1)]
        self.s = P.CELL_VARS + 2                     # a plus of colour 14 around (3, 0), disjoint from it
        self.plus2 = [(3, 0), (3, -1), (2, 0), (4, 0), (3, 1)]
        self.formula = [(self.r, -P.x(p, 14)) for p in self.plus] + [(self.s, -P.x(p, 14)) for p in self.plus2]
        self.found = P.regions(self.formula)

    def test_regions_are_read_from_the_membership_clauses(self):
        self.assertEqual(self.found, {self.r: (14, frozenset(self.plus)), self.s: (14, frozenset(self.plus2))})
        with self.assertRaises(P.Refused):
            P.regions(self.formula + [(self.r, -P.x((5, 5), 13))])

    def test_justified_clauses(self):
        ok = [tuple(P.x((2, 2), c) for c in range(1, 15)), (P.x((0, 0), 6),),
              (-P.x((0, 0), 5), -P.x((2, 3), 5)), (-self.r, -P.x((6, 0), 14)), (-self.r, -self.s)]
        ok.append(tuple(sorted(next(iter(P.symmetry_clauses())))))
        kinds, bad = P.classify(self.formula + ok, self.found)
        self.assertEqual(bad, [])
        self.assertEqual(kinds, {"at_least_one_colour": 1, "distance": 1, "centre": 1, "membership": 10,
                                 "region_cell": 1, "region_region": 1, "symmetry": 1})

    def test_each_kind_of_unjustified_clause_is_caught(self):
        sym = sorted(next(iter(P.symmetry_clauses())))
        bad = [(-P.x((0, 0), 5), -P.x((3, 3), 5)),              # distance 6 > 5
               (-P.x((0, 0), 5), -P.x((1, 0), 4)),              # two colours
               (P.x((0, 0), 5),),                               # the wrong centre colour
               (-self.r, -P.x((0, 0), 14)),                     # a cell of the region itself
               (-self.r, -P.x((14, 0), 14)),                    # too far from some of the region
               (-self.r, -P.x((6, 0), 13)),                     # another colour
               (-self.r, -(P.CELL_VARS + 3)),                   # an unknown region
               tuple(sym[:-1]),                                 # a symmetry clause cut short
               (-P.x((0, 0), 5), P.x((1, 0), 5)),               # anything else
               tuple(P.x((2, 2), c) for c in range(1, 14))]     # a colour missing
        far = P.CELL_VARS + 4                                   # two regions not all within 14 of each other
        formula = self.formula + [(far, -P.x(p, 14)) for p in [(13, 0), (12, 0), (14, 0), (13, 1), (13, -1)]]
        found = P.regions(formula)
        bad.append((-self.r, -far))
        _, caught = P.classify(formula + bad, found)
        self.assertEqual(sorted(caught), sorted(bad))

    def test_a_placement_that_differs_is_refused(self):
        found = {P.CELL_VARS + 1: (4, frozenset(self.plus))}
        good = json.dumps({"1": [], "4": [[list(p) for p in self.plus]]})
        self.assertEqual(P.check_placement(found, good), {1: [], 4: [P.CELL_VARS + 1]})
        for bad in (json.dumps({"4": [[list(p) for p in self.plus2]]}),
                    json.dumps({"5": [[list(p) for p in self.plus]]}),
                    json.dumps({"4": [[list(p) for p in self.plus], [[9, 9]]]}), "not json", json.dumps({"4": [[1]]})):
            with self.assertRaises(P.Refused):
                P.check_placement(found, bad)

    def test_the_symmetry_clauses_are_the_papers(self):
        sym = P.symmetry_clauses()
        self.assertEqual(len(sym), 93 + 69 + 69 + 49 + 49)
        self.assertEqual(sorted({len(c) for c in sym}), [1, 21, 37, 53, 65])


# ---------------------------------------------------------------- the split

class Splitting(unittest.TestCase):
    def test_counts(self):
        for T, R, P_ in ((4, 3, 3), (3, 2, 3), (5, 2, 2), (7, 9, 6)):
            sp = P.Split([[k * R + t + 1 for t in range(R)] for k in range(T)], P_)
            self.assertEqual(sp.total, sum(math.comb(T, p) * R ** p for p in range(min(P_, T) + 1)))
        self.assertEqual(P.Split([[1] * 9] * 7, 6).total, P.CUBES_TOTAL)

    def test_the_order_is_the_authors(self):
        for T, R, P_ in ((4, 3, 3), (3, 2, 1), (5, 2, 4)):
            var = [[100 + k * R + t for t in range(R)] for k in range(T)]
            sp = P.Split(var, P_)
            self.assertEqual([lits for _, _, lits in sp.stream()], authors_cubes(var, P_, 14, T))

    def test_unrank_and_rank(self):
        sp = small()
        for i, (Q, S, lits) in enumerate(sp.stream()):
            self.assertEqual(sp.unrank(i), (Q, S))
            self.assertEqual(sp.rank(Q, S), i)
            self.assertEqual(sp.literals(Q, S), lits)
        with self.assertRaises(IndexError):
            sp.unrank(sp.total)

    def test_regions_by_sum_of_distances_ties_in_placement_order(self):
        found = {1: (14, frozenset([(0, 3)])), 2: (14, frozenset([(2, 1)])), 3: (14, frozenset([(0, 1)])),
                 4: (14, frozenset([(5, 5)]))}
        top, var, same = P.split_variables({14: [1, 2, 3, 4]}, found, colours=14, centre=6, T=1, R=2)
        self.assertEqual((top, var), ([14], [[3, 1]]))
        self.assertFalse(same)                       # a tie at the cut (1 and 2 are both 3 away)
        top, var, same = P.split_variables({14: [1, 2, 3, 4]}, found, colours=14, centre=6, T=1, R=3)
        self.assertEqual((var, same), ([[3, 1, 2]], True))
        top, _, _ = P.split_variables({c: [1, 2, 3, 4] for c in (14, 13, 12)}, found, colours=14, centre=13, T=2,
                                      R=1)
        self.assertEqual(top, [14, 12])              # the centre's colour is replaced by the next below


# ---------------------------------------------------------------- the cover

class Covering(unittest.TestCase):
    def test_the_exact_check_agrees_with_brute_force(self):
        for T, R, P_ in ((3, 2, 2), (3, 2, 1), (4, 2, 3), (3, 3, 2)):
            sp = P.Split([[k * R + t + 1 for t in range(R)] for k in range(T)], P_)
            cubes = [lits for _, _, lits in sp.stream()]
            ok, info = P.cover_exact(sp, cubes)
            self.assertTrue(ok and covered_by_brute_force(sp, cubes), (T, R, P_, info))
            for k in range(len(cubes)):              # every cube is needed
                rest = cubes[:k] + cubes[k + 1:]
                ok, info = P.cover_exact(sp, rest)
                self.assertFalse(ok)
                self.assertFalse(covered_by_brute_force(sp, rest))
                self.assertEqual(info["uncovered"], 1)

    def test_a_malformed_cube_is_refused_by_the_exact_check(self):
        sp = small()
        cubes = [lits for _, _, lits in sp.stream()]
        for bad in ([1, 2], [1, -2], [-1, -2], [99], [1, -4, -5]):
            ok, info = P.cover_exact(sp, cubes + [bad])
            self.assertEqual((ok, info["malformed"]), (False, 1), bad)

    def test_the_parts_are_numbered_as_written_and_their_proofs_check(self):
        for T, R, P_ in ((4, 3, 3), (3, 2, 2), (3, 2, 1), (5, 2, 4)):
            sp = P.Split([[k * R + t + 1 for t in range(R)] for k in range(T)], P_)
            with tempfile.TemporaryDirectory() as d:
                paths, parts = P.write_parts(sp, sp.stream(), d, T * R)
                for t, path in enumerate(paths):
                    with open(path, "rb") as f:
                        _, clauses, _, _ = P.H.parse_cnf(f.read(), "part")
                    buf = io.StringIO()
                    P.part_proof(sp, parts, t, buf)
                    self.assertTrue(rup_check(clauses, buf.getvalue()), (T, R, P_, t))
                    self.assertFalse(rup_check(clauses[:-1], buf.getvalue()))

    def test_every_cube_lands_in_one_part_and_the_units_cover(self):
        sp = small()
        sizes = [0] * (sp.R + 1)
        for Q, S, lits in sp.stream():
            t = P.part_of(Q, S, sp.R)
            sizes[t] += 1
            if t < sp.R:
                self.assertIn(sp.var[0][t], lits)
            else:
                self.assertFalse(any(abs(lit) in sp.var[0] and lit > 0 for lit in lits))
        self.assertEqual(sizes, P.Parts(sp).size)
        for bits in itertools.product((False, True), repeat=sp.R):   # every assignment of the first colour
            self.assertTrue(any(all(bits[sp.var[0].index(abs(u))] == (u > 0) for (u,) in P.part_units(sp, t))
                                for t in range(sp.R + 1)))

    def test_a_proof_without_one_of_its_clauses_fails_the_reference_checker(self):
        sp = small()
        parts = P.Parts(sp)
        with tempfile.TemporaryDirectory() as d:
            paths, _ = P.write_parts(sp, sp.stream(), d, 12)
            with open(paths[0], "rb") as f:
                _, clauses, _, _ = P.H.parse_cnf(f.read(), "part")
        buf = io.StringIO()
        P.part_proof(sp, parts, 0, buf)
        for k in range(1, len(clauses)):
            broken = clauses[:k] + [(1, -1)] + clauses[k + 1:]      # a clause replaced by a tautology
            self.assertFalse(rup_check(broken, buf.getvalue()), k)


# ---------------------------------------------------------------- the solver's outcomes

FAKE_SOLVER = r'''
import sys
args = sys.argv[1:]
limit = None
files = []
k = 0
while k < len(args):
    if args[k] in ("-c", "-t"):
        if args[k] == "-c":
            limit = int(args[k + 1])
        k += 2
        continue
    if not args[k].startswith("-"):
        files.append(args[k])
    k += 1
text = open(files[0]).read()
if "STOP" in text and limit is not None:
    print("c conflicts: %d" % limit); sys.exit(0)
if "SAT" in text:
    print("s SATISFIABLE"); print("v 1 -2 0"); sys.exit(10)
if "BROKEN" in text:
    sys.exit(1)
if len(files) > 1:
    open(files[1], "w").write("PROOF")
print("c conflicts: 3"); print("s UNSATISFIABLE"); sys.exit(20)
'''

FAKE_CHECKER = r'''
import sys
cnf, proof = [a for a in sys.argv[1:] if not a.startswith("--CML_")]
print("s VERIFIED UNSAT" if open(proof).read() == "PROOF" else "c empty clause not derived at end of proof")
'''


class Outcomes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        tools = {}
        for name, text in (("cadical", FAKE_SOLVER), ("cake_lpr", FAKE_CHECKER)):
            path = os.path.join(self.tmp.name, name)
            write(path, f"#!{sys.executable}\n{text}".encode())
            os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
            tools[name] = path
        try:
            subprocess.run([tools["cadical"], "-h"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (PermissionError, OSError):
            self.skipTest("the temporary directory cannot run the stand-in tools (noexec); set TMPDIR")
        self.tools = P.capped(tools, self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def outcome(self, text):
        path = os.path.join(self.tmp.name, "f.cnf")
        write(path, text.encode())
        r = P.H.solve(self.tools, path, self.tmp.name, "f")
        return P.verdict(r), r

    def test_the_cap_is_passed_and_reaching_it_is_a_timeout(self):
        with open(self.tools["cadical"]) as f:
            self.assertIn(f"-c {P.CAP_CONFLICTS} -t {P.CAP_SECONDS}", f.read())
        v, r = self.outcome("p cnf 2 1\n1 2 0\nc STOP\n")
        self.assertEqual((v, r["verified"], r["conflicts"]), ("timeout", False, P.CAP_CONFLICTS))

    def test_unsat_sat_and_errors(self):
        v, r = self.outcome("p cnf 2 1\n1 2 0\n")
        self.assertEqual((v, r["verified"]), ("unsat", True))
        v, r = self.outcome("p cnf 2 1\n1 2 0\nc SAT\n")
        self.assertEqual((v, r["verified"]), ("sat", False))
        self.assertEqual(P.H.satisfies(P.H.model(r["model"]), [(1, 2), (-2,)]), 0)
        v, r = self.outcome("p cnf 2 1\n1 2 0\nc BROKEN\n")
        self.assertEqual((v, r["verified"]), ("error", False))


# ---------------------------------------------------------------- the draws

class Draws(unittest.TestCase):
    def test_the_sample_is_hexagons_stream_under_the_packing_label(self):
        a = P.H.sample(SEED, "packing/cubes", P.CUBES_TOTAL, 20)
        block = hashlib.sha256(bytes.fromhex(SEED) + b"|packing/cubes|0").digest()
        first = int.from_bytes(block[:8], "big")
        self.assertEqual(a[0], first % P.CUBES_TOTAL)        # the first draw is below the rejection limit
        self.assertEqual(len(set(a)), 20)
        self.assertEqual(a, P.H.sample(SEED, "packing/cubes", P.CUBES_TOTAL, 20))


class Inputs(unittest.TestCase):
    def test_other_bytes_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            write(os.path.join(d, "P15_14_6_S5.cnf"), b"p cnf 1 1\n1 0\n")
            with self.assertRaises(P.Refused):
                P.load(d, "P15_14_6_S5.cnf")

    def test_an_eprint_without_the_file_is_refused(self):
        with self.assertRaises(P.Refused):
            P.tex_from_eprint(b"not a tar")


# ---------------------------------------------------------------- with the real tools or the real inputs

@unittest.skipUnless(os.environ.get("PACKING_TOOLS"), "set PACKING_TOOLS to a directory with the built cadical and "
                                                       "cake_lpr")
class RealTools(unittest.TestCase):
    def setUp(self):
        d = os.environ["PACKING_TOOLS"]
        self.tools = {"cadical": os.path.join(d, "cadical"), "cake_lpr": os.path.join(d, "cake_lpr")}
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_small_split_controls(self):
        rows = P.small_controls(self.tools, self.tmp.name)
        self.assertEqual([r["passed"] for r in rows], [True] * 4, rows)

    def test_a_capped_solve_stops_at_its_limit(self):
        nv, clauses = P.H.pigeonhole(9)
        path = os.path.join(self.tmp.name, "php.cnf")
        write(path, b"p cnf %d %d\n" % (nv, len(clauses)) + P.H.clause_lines(clauses))
        with patched(CAP_CONFLICTS=100):
            tools = P.capped(self.tools, self.tmp.name)
        r = P.H.solve(tools, path, self.tmp.name, "php", 256, 128)
        self.assertEqual((P.verdict(r), r["verified"], r["conflicts"]), ("timeout", False, 100))


@unittest.skipUnless(inputs_dir(), "put the inputs at inputs/ or name their directory in PACKING_INPUTS")
class RealInputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        d = inputs_dir()
        cls.data = {n: P.load(d, n) for n, *_ in P.INPUTS[:3]}
        _, cls.formula, cls.header, _ = P.H.parse_cnf(cls.data["P15_14_6_S5.cnf"], "formula")
        cls.found = P.regions(cls.formula)
        cls.by_colour = P.check_placement(cls.found, cls.data["placement-15-14-plus"].decode("utf-8"))

    def test_the_witness(self):
        grid = P.parse_table(P.tex_from_eprint(self.data["arXiv-1510.02374v3.tar.gz"]))
        w = P.witness(grid)
        self.assertEqual((w["rows"], w["colours"], w["violations"], w["witness_ok"]), (72, 15, 0, 1))
        self.assertEqual(list(w["counts"].values()), [2592, 648, 648, 288, 288, 144, 144] + [72] * 4 + [36] * 4)
        self.assertEqual(w["closest"]["15"], 16)
        self.assertTrue(all(r["passed"] for r in P.witness_controls(grid)))

    def test_the_reduction(self):
        kinds, bad = P.classify(self.formula, self.found)
        self.assertEqual(bad, [])
        self.assertEqual(kinds, {"at_least_one_colour": 481, "distance": 52320, "centre": 1, "membership": 4675,
                                 "region_cell": 25612, "region_region": 8112, "symmetry": 329})
        self.assertEqual(sum(kinds.values()), len(self.formula))

    def test_the_split_and_its_full_order(self):
        top, var, same = P.split_variables(self.by_colour, self.found)
        self.assertEqual((top, same), ([14, 13, 12, 11, 10, 9, 8], True))
        for c, vs in zip(top, var):
            self.assertEqual([v - self.by_colour[c][0] for v in vs], [0, 1, 3, 5, 7, 2, 4, 6, 8])
            self.assertEqual([sorted(self.found[v][1])[2] for v in vs],
                             [(0, 0), (-1, 2), (2, 1), (1, -2), (-2, -1), (1, 3), (3, -1), (-1, -3), (-3, 1)])
        sp = P.Split(var, P.SPLIT_P)
        digest, total, lits = hashlib.sha256(), 0, 0
        for mine, theirs in zip(sp.stream(), authors_cubes(var, 6, 14, 7, centre=6)):
            self.assertEqual(mine[2], theirs)
            digest.update(b"a " + b" ".join(b"%d" % lit for lit in theirs) + b" 0\n")
            total += 1
            lits += len(theirs)
        self.assertEqual((total, lits), (P.CUBES_TOTAL, P.CUBE_LITERALS))
        self.assertEqual(digest.hexdigest(), "49e5536d43708044e86c6b426dda1e650acb4128b1e096d5ffe303e12b4245ed")


if __name__ == "__main__":
    with contextlib.suppress(SystemExit):
        unittest.main()
