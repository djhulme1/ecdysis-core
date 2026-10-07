"""The empty-hexagon check on made-up cases: orientation, hulls and hexagon counts against a reference written from
the definitions, collinear and doubled points caught, the list in Geo.lean read and anything else in it refused, the
CNF and cube readers and their refusals, other bytes refused, the seeded draws, the coverage formula's clauses
classified (a foreign clause caught), and a whole run with made-up inputs and stand-in tools: a satisfiable cube
caught with its model checked, a proof that does not verify caught, a checker that runs out of heap tried again.

With the real tools (HEXAGON_TOOLS, a directory holding the cadical and cake_lpr a run built in results/build), also
the proof controls and the pipe that carries a proof from the solver to the checker. With the real inputs (at inputs/
or in HEXAGON_INPUTS), also the witness's counts and the inputs' shapes. The stand-in tools are scripts, so the
temporary directory must allow execution (in the sandbox, set TMPDIR to a directory under results/).

Run with: python3 -m unittest discover -s tests
"""

import contextlib
import hashlib
import importlib.util
import itertools
import json
import os
import random
import stat
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("hexagon_check", os.path.join(HERE, "..", "hexagon", "check.py"))
H = importlib.util.module_from_spec(_spec)
sys.modules["hexagon_check"] = H
_spec.loader.exec_module(H)

SEED = "a" * 64
OTHER = "f" * 64


def write(path, data):
    with open(path, "wb") as f:
        f.write(data)


def read(path):
    with open(path, "rb") as f:
        return f.read()


def inputs_dir():
    d = os.environ.get("HEXAGON_INPUTS") or os.path.join(HERE, "..", "inputs")
    return d if all(os.path.isfile(os.path.join(d, name)) and os.path.getsize(os.path.join(d, name)) > 0
                    for name, *_ in H.INPUTS[:4]) else None


# ---------------------------------------------------------------- references, from the definitions

def in_triangle(q, a, b, c):
    """q strictly inside triangle abc, by the signs of three orientations."""
    s = [H.orient(a, b, q), H.orient(b, c, q), H.orient(c, a, q)]
    return all(x > 0 for x in s) or all(x < 0 for x in s)


def reference(points):
    """(convex hexagons, empty hexagons) by the definitions: six points are in convex position when none lies inside
    a triangle of three others (Caratheodory, in the plane); a convex hexagon is empty when no other point lies
    inside a triangle of three of its vertices."""
    convex = empty = 0
    for six in itertools.combinations(points, 6):
        if any(in_triangle(q, *t) for q in six for t in itertools.combinations([p for p in six if p != q], 3)):
            continue
        convex += 1
        if not any(in_triangle(q, *t) for q in points if q not in six for t in itertools.combinations(six, 3)):
            empty += 1
    return convex, empty


def general_points(n, rng, box=60):
    pts = []
    while len(pts) < n:
        q = (rng.randrange(box), rng.randrange(box))
        if H.general_with(pts, q):
            pts.append(q)
    return pts


PARABOLA5 = [(0, 960), (200, 760), (400, 640), (800, 640), (1000, 760)]   # with (600, 600), six on a parabola


def geo_text(points):
    pairs = ", ".join(f"({x}, {y})" for x, y in points)
    return ("theorem holeNumber_5 : holeNumber 5 = 10 :=\n  le_antisymm (x) (hole_lower_bound [(1, 0), (6, 4)])\n\n"
            "theorem holeNumber_6 : holeNumber 6 = 30 :=\n  le_antisymm (hole_6_theorem' unsat_6hole_cnf) "
            f"(hole_lower_bound [\n    {pairs}\n  ])\n")


class Geometry(unittest.TestCase):
    def test_orientation_and_hull(self):
        self.assertGreater(H.orient((0, 0), (1, 0), (0, 1)), 0)
        self.assertLess(H.orient((0, 0), (0, 1), (1, 0)), 0)
        self.assertEqual(H.orient((0, 0), (1, 1), (3, 3)), 0)
        pts = sorted([(0, 0), (4, 0), (4, 4), (0, 4), (2, 1)])
        self.assertEqual(sorted(pts[i] for i in H.hull(list(range(5)), H.signs(pts))), [(0, 0), (0, 4), (4, 0), (4, 4)])

    def test_hexagon_counts_agree_with_the_definitions(self):
        rng = random.Random(7)
        for n in (6, 7, 9, 11):
            for _ in range(3):
                pts = general_points(n, rng)
                convex, empty = H.hexagons(pts)
                self.assertEqual((convex, len(empty)), reference(pts), pts)

    def test_a_regular_hexagon_is_empty_until_a_point_is_put_inside(self):
        hexagon = [(2, 0), (4, 1), (4, 3), (2, 4), (0, 3), (0, 1)]
        self.assertEqual(H.collinear_triples(hexagon), 0)
        convex, empty = H.hexagons(hexagon)
        self.assertEqual((convex, len(empty)), (1, 1))
        convex, empty = H.hexagons(hexagon + [(2, 2)])
        self.assertEqual((convex, len(empty)), (1, 0))

    def test_only_hexagons_containing_the_new_point_when_asked(self):
        rng = random.Random(11)
        pts = general_points(10, rng)
        _, every = H.hexagons(pts)
        _, some = H.hexagons(pts, containing=4)
        self.assertEqual(sorted(some), sorted(h for h in every if pts[4] in h))

    def test_layers(self):
        self.assertEqual(H.layers([(0, 0), (10, 0), (0, 10), (10, 10), (3, 4), (6, 4), (5, 7), (5, 5)]), [4, 3, 1])

    def test_the_witness_rules(self):
        saved = H.POINTS
        try:
            H.POINTS = 5
            good = H.witness(PARABOLA5)
            self.assertEqual((good["witness_ok"], good["convex_hexagons"], good["empty_hexagons"]), (1, 0, 0))
            collinear = H.witness([(0, 0), (1, 1), (2, 2), (5, 0), (0, 7)])
            self.assertEqual((collinear["witness_ok"], collinear["collinear_triples"]), (0, 1))
            doubled = H.witness([(0, 0), (0, 0), (2, 3), (5, 0), (0, 7)])
            self.assertEqual(doubled["witness_ok"], 0)
            self.assertEqual(H.witness(PARABOLA5[:4])["witness_ok"], 0)        # too few points
            H.POINTS = 6
            hole = H.witness(PARABOLA5 + [(600, 600)])                       # six in convex position: a hole
            self.assertEqual((hole["witness_ok"], hole["empty_hexagons"]), (0, 1))
        finally:
            H.POINTS = saved

    def test_extra_points_are_drawn_from_the_seed_in_general_position(self):
        rows, rejected = H.extra_points(PARABOLA5, SEED, 6)
        again, _ = H.extra_points(PARABOLA5, SEED, 6)
        other, _ = H.extra_points(PARABOLA5, OTHER, 6)
        self.assertEqual(rows, again)
        self.assertNotEqual(rows, other)
        for r in rows:
            q = tuple(r["point"])
            self.assertTrue(0 <= q[0] <= 1000 and 640 <= q[1] <= 960)
            self.assertTrue(H.general_with(PARABOLA5, q))
            convex, empty = H.hexagons(PARABOLA5 + [q])
            self.assertEqual(r["empty_hexagons"], len(empty))

    def test_collinear_draws_are_rejected_and_counted(self):
        pts = [(0, 0), (10, 0), (0, 10), (10, 10), (3, 7)]   # about half its box is on a line through two
        rows, rejected = H.extra_points(pts, SEED, 10)
        self.assertGreater(rejected, 0)
        self.assertTrue(all(H.general_with(pts, tuple(r["point"])) for r in rows))


class Reading(unittest.TestCase):
    def test_the_points_after_hole_lower_bound_in_holenumber_6(self):
        self.assertEqual(H.parse_points(geo_text(PARABOLA5)), PARABOLA5)

    def test_anything_else_in_the_list_is_refused(self):
        for bad in (geo_text(PARABOLA5).replace("(0, 960)", "(0, 960), x"),
                    geo_text(PARABOLA5).replace("(0, 960)", "(0.5, 960)"),
                    geo_text(PARABOLA5).replace("holeNumber_6", "holeNumber_7"),
                    geo_text([])):
            with self.assertRaises(H.Refused):
                H.parse_points(bad)

    def test_a_cnf_is_read_and_its_faults_refused(self):
        v, clauses, header, body = H.parse_cnf(b"p cnf 3 2\n1 -2 0\n3 0\n", "f")
        self.assertEqual((v, clauses, header, body), (3, [(1, -2), (3,)], b"p cnf 3 2", b"1 -2 0\n3 0\n"))
        for bad in (b"p cnf 3 3\n1 -2 0\n3 0\n", b"p cnf 3 2\n1 -4 0\n3 0\n", b"c x\np cnf 3 2\n1 0\n2 0\n",
                    b"p cnf 3 2\n1 -2\n3 0\n", b"p cnf 3 2\nc note\n1 0\n2 0\n", b"p cnf 3 1\n1 x 0\n"):
            with self.assertRaises(H.Refused):
                H.parse_cnf(bad, "f")

    def test_cubes_are_read_and_their_faults_refused(self):
        self.assertEqual(H.parse_cubes(b"a 1 -2 0\na -3 0\n", 3), [(1, -2), (-3,)])
        for bad in (b"a 1 -2 0\n1 0\n", b"a 1 -1 0\n", b"a 4 0\n", b"a 0\n", b"a 1 2\n"):
            with self.assertRaises(H.Refused):
                H.parse_cubes(bad, 3)

    def test_other_bytes_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            write(os.path.join(d, "Geo.lean"), b"not the file")
            with self.assertRaises(H.Refused):
                H.load(d, "Geo.lean")

    def test_with_units_adds_each_literal_as_a_clause(self):
        self.assertEqual(H.with_units(3, 1, b"1 2 0\n", (-1, 3)), b"p cnf 3 3\n1 2 0\n-1 0\n3 0\n")


class Draws(unittest.TestCase):
    def test_the_stream_is_sha256_of_seed_label_and_counter(self):
        s = H.Stream(SEED, "hexagon/cubes")
        block = hashlib.sha256(bytes.fromhex(SEED) + b"|hexagon/cubes|0").digest()
        self.assertEqual([s.u64() for _ in range(4)], [int.from_bytes(block[k:k + 8], "big") for k in (0, 8, 16, 24)])
        second = hashlib.sha256(bytes.fromhex(SEED) + b"|hexagon/cubes|1").digest()
        self.assertEqual(s.u64(), int.from_bytes(second[:8], "big"))

    def test_the_sample_is_distinct_in_range_and_fixed_by_the_seed(self):
        a = H.sample(SEED, "hexagon/cubes", H.CUBES_TOTAL, 50)
        self.assertEqual(len(set(a)), 50)
        self.assertTrue(all(0 <= x < H.CUBES_TOTAL for x in a))
        self.assertEqual(a, H.sample(SEED, "hexagon/cubes", H.CUBES_TOTAL, 50))
        self.assertEqual(a[:8], H.sample(SEED, "hexagon/cubes", H.CUBES_TOTAL, 8))
        self.assertNotEqual(a, H.sample(OTHER, "hexagon/cubes", H.CUBES_TOTAL, 50))
        self.assertEqual(sorted(H.sample(SEED, "x", 5, 5)), [0, 1, 2, 3, 4])


class Coverage(unittest.TestCase):
    FORMULA = [(1, 2, 3), (-1, 2, 4), (-2,), (-3,), (-4,)]
    CUBES = [(1,), (-1,)]

    def test_the_clauses_are_classified(self):
        coverage = [(-1,), (1,)] + self.FORMULA + [(4, 9)]
        self.assertEqual(H.coverage_structure(self.FORMULA, self.CUBES, coverage),
                         {"from_formula": 5, "negated_cubes": 2, "pure": 1, "other": 0, "cubes_covered": 2})

    def test_a_foreign_clause_is_caught(self):
        coverage = [(-1,), (1,)] + self.FORMULA + [(2, 3)]
        self.assertEqual(H.coverage_structure(self.FORMULA, self.CUBES, coverage)["other"], 1)

    def test_a_clause_whose_variable_occurs_twice_is_not_pure(self):
        coverage = [(-1,)] + self.FORMULA + [(4, 9), (-9, 2)]
        got = H.coverage_structure(self.FORMULA, self.CUBES, coverage)
        self.assertEqual((got["pure"], got["other"], got["cubes_covered"]), (0, 2, 1))


# ---------------------------------------------------------------- stand-in tools for the orchestration

FAKE_SOLVER = r'''
import hashlib, itertools, sys
args = sys.argv[1:]
files = [a for a in args if not a.startswith("-")]
data = open(files[0], "rb").read()
lines = data.split(b"\n")
nv, nc = int(lines[0].split()[2]), int(lines[0].split()[3])
clauses = [tuple(int(t) for t in l.split()[:-1]) for l in lines[1:] if l.strip()]
if len(clauses) != nc:
    print("cadical: error: parse error", file=sys.stderr); sys.exit(1)
for bits in itertools.product((False, True), repeat=nv):
    if all(any((lit > 0) == bits[abs(lit) - 1] for lit in c) for c in clauses):
        print("s SATISFIABLE"); print("v " + " ".join(str(i + 1 if b else -i - 1) for i, b in enumerate(bits)) + " 0")
        sys.exit(10)
if len(files) > 1:
    with open(files[1], "wb") as f:
        f.write(b"PROOF " + hashlib.sha256(data).hexdigest().encode())
print("c conflicts:                     7         1.00    per second"); print("s UNSATISFIABLE"); sys.exit(20)
'''

FAKE_CHECKER = r'''
import hashlib, os, sys
heap = int(next(a.split("=")[1] for a in sys.argv[1:] if a.startswith("--CML_HEAP_SIZE=")))
cnf, proof = [a for a in sys.argv[1:] if not a.startswith("--CML_")]
data = open(cnf, "rb").read()
p = open(proof, "rb").read()
digest = hashlib.sha256(data).hexdigest()
heavy = os.path.join(os.path.dirname(os.path.abspath(__file__)), "heavy.txt")
# a heavy formula needs more than the first heap (1024 MB) and no more than the retry's (2560 MB)
if os.path.exists(heavy) and digest in open(heavy).read().split() and heap < 2048:
    print("CakeML heap space exhausted.", file=sys.stderr); sys.exit(1)
bad = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reject.txt")
if p == b"PROOF " + digest.encode() and not (os.path.exists(bad) and digest in open(bad).read().split()):
    print("s VERIFIED UNSAT")
else:
    print("c empty clause not derived at end of proof")
'''


def stand_in_tools(d):
    """The stand-in solver and checker as executable scripts in d, or None where d cannot run them."""
    tools = {"cadical_version": "stand-in", "cadical_files": 0, "gcc": "-"}
    for name, text in (("cadical", FAKE_SOLVER), ("cake_lpr", FAKE_CHECKER)):
        path = os.path.join(d, name)
        write(path, f"#!{sys.executable}\n{text}".encode())
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
        tools[name] = path
    try:
        subprocess.run([tools["cadical"], "-h"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except PermissionError:
        return None
    return tools


class Orchestration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tools = stand_in_tools(self.tmp.name)
        if self.tools is None:
            self.skipTest("the temporary directory cannot run the stand-in tools (noexec); set TMPDIR")

    def tearDown(self):
        self.tmp.cleanup()

    def cnf(self, name, nv, clauses):
        path = os.path.join(self.tmp.name, name)
        write(path, b"p cnf %d %d\n" % (nv, len(clauses)) + H.clause_lines(clauses))
        return path

    def test_unsat_with_a_proof_that_verifies(self):
        r = H.solve(self.tools, self.cnf("u.cnf", 1, [(1,), (-1,)]), self.tmp.name, "u")
        self.assertEqual((r["answer"], r["verified"], r["conflicts"]), ("unsat", True, 7))

    def test_a_proof_the_checker_rejects_is_not_verified(self):
        path = self.cnf("u.cnf", 1, [(1,), (-1,)])
        write(os.path.join(self.tmp.name, "reject.txt"), hashlib.sha256(read(path)).hexdigest().encode())
        r = H.solve(self.tools, path, self.tmp.name, "u")
        self.assertEqual((r["answer"], r["verified"], r["resources"]), ("unsat", False, False))

    def test_satisfiable_and_broken_formulas_do_not_hang_or_verify(self):
        r = H.solve(self.tools, self.cnf("s.cnf", 2, [(1, 2)]), self.tmp.name, "s")
        self.assertEqual((r["answer"], r["verified"]), ("sat", False))
        self.assertEqual(H.satisfies(H.model(r["model"]), [(1, 2)]), 0)
        path = os.path.join(self.tmp.name, "b.cnf")
        write(path, b"p cnf 2 5\n1 2 0\n")
        r = H.solve(self.tools, path, self.tmp.name, "b")
        self.assertEqual((r["answer"], r["verified"]), ("error", False))

    def test_a_model_is_checked(self):
        self.assertEqual(H.satisfies({1, -2}, [(1, 2), (2,), (-1, -2)]), 1)
        with self.assertRaises(H.Refused):
            H.satisfies({1, -1}, [(1,)])
        with self.assertRaises(H.Refused):
            H.model("s SATISFIABLE\nv 1 -2\n")

    def made_up_run(self, formula, nv, cubes, coverage, heavy=False, reject_cube=None):
        """A whole run with made-up inputs: the witness PARABOLA5 (five points), formula F, cubes and coverage."""
        d = self.tmp.name
        for marker in ("heavy.txt", "reject.txt"):
            if os.path.exists(os.path.join(d, marker)):
                os.unlink(os.path.join(d, marker))
        inputs = os.path.join(d, "inputs")
        os.makedirs(inputs, exist_ok=True)
        files = {
            "Geo.lean": geo_text(PARABOLA5).encode(),
            "final-30-ours-flat.cnf": b"p cnf %d %d\n" % (nv, len(formula)) + H.clause_lines(formula),
            "marijn-cubes.icnf": b"".join(b"a " + b" ".join(b"%d" % x for x in c) + b" 0\n" for c in cubes),
            "cube_tautology.cnf": b"p cnf 9 %d\n" % len(coverage) + H.clause_lines(coverage),
            "cadical_2.1.3.orig.tar.gz": b"unused", "cake_lpr.S": b"unused", "basis_ffi.c": b"unused"}
        specs = []
        for name, *rest in H.INPUTS:
            write(os.path.join(inputs, name), files[name])
            specs.append((name, hashlib.sha256(files[name]).hexdigest(), len(files[name]), rest[-1]))
        for c in ([cubes[0]] if heavy else []):
            data = H.with_units(nv, len(formula), H.clause_lines(formula), c)
            write(os.path.join(d, "heavy.txt"), hashlib.sha256(data).hexdigest().encode())
        if reject_cube is not None:
            data = H.with_units(nv, len(formula), H.clause_lines(formula), cubes[reject_cube])
            write(os.path.join(d, "reject.txt"), hashlib.sha256(data).hexdigest().encode())
        saved = (H.INPUTS, H.POINTS, H.CUBES_TOTAL, H.WEAK_KEEP, H.proof_controls)
        H.INPUTS, H.POINTS, H.CUBES_TOTAL, H.WEAK_KEEP = tuple(specs), 5, len(cubes), 2
        H.proof_controls = lambda tools, work: ([{"control": "stand-in", "passed": True}], 1)
        try:
            out, detail = H.run(SEED, inputs=inputs, results=os.path.join(d, "results"), cubes_wanted=len(cubes),
                                extra=2, tools=self.tools, log=lambda line: None)
        finally:
            H.INPUTS, H.POINTS, H.CUBES_TOTAL, H.WEAK_KEEP, H.proof_controls = saved
        self.assertEqual(set(out), set(H.OUTPUTS))
        self.assertEqual(len(out), 20)
        self.assertTrue(all(isinstance(v, (int, float)) or (isinstance(v, str) and len(v) <= 200) for v in out.values()))
        json.dumps(detail)
        return out, detail

    # F: its opening block (two 3-literal clauses) is satisfiable; with (-2), (-3), (-4) it is not.
    FORMULA = [(1, 2, 3), (-1, 2, 4), (-2,), (-3,), (-4,)]

    def test_a_whole_run_that_passes(self):
        cubes = [(1,), (-1,)]
        coverage = [(-1,), (1,)] + self.FORMULA + [(4, 9)]
        out, detail = self.made_up_run(self.FORMULA, 4, cubes, coverage)
        self.assertEqual((out["witness_ok"], out["witness_convex_hexagons"], out["witness_empty_hexagons"]), (1, 0, 0))
        self.assertEqual((out["cubes_sampled"], out["cubes_unsat"], out["cubes_verified"]), (2, 2, 2))
        self.assertEqual(sorted(out["cubes_ids"].split(",")), ["1", "2"])
        self.assertEqual(out["coverage_clauses"], "negated_cubes=2,cubes_covered=2,from_formula=5,pure=1,other=0")
        self.assertEqual((out["coverage_unsat"], out["coverage_verified"]), (1, 1))
        self.assertEqual((out["controls_passed"], out["controls_total"]), (4, 4))   # two witness, weak, stand-in
        weak = next(c for c in detail["controls"] if c["control"].startswith("formula cut"))
        self.assertEqual((weak["kept_clauses_violated"], weak["removed_clauses_violated"] > 0), (0, True))
        self.assertEqual((out["extra_sets_checked"], out["test_passed"]), (2, 1))

    def test_a_satisfiable_cube_is_caught_with_its_model_checked(self):
        formula = [(1, 2, 3), (-1, 2, 4), (-2,), (-3,)]          # satisfiable when 1 and 4 are true
        cubes = [(1,), (-1,)]
        coverage = [(-1,), (1,)] + formula
        out, detail = self.made_up_run(formula, 4, cubes, coverage)
        sat = [c for c in detail["cubes"] if c["answer"] == "sat"]
        self.assertEqual([(c["cube"], c["model_violates"]) for c in sat], [(1, 0)])
        self.assertEqual((out["cubes_unsat"], out["cubes_verified"], out["test_passed"]), (1, 1, 0))

    def test_a_rejected_proof_or_a_foreign_coverage_clause_fails_the_test(self):
        cubes = [(1,), (-1,)]
        out, _ = self.made_up_run(self.FORMULA, 4, cubes, [(-1,), (1,)] + self.FORMULA, reject_cube=1)
        self.assertEqual((out["cubes_unsat"], out["cubes_verified"], out["test_passed"]), (2, 1, 0))
        out, _ = self.made_up_run(self.FORMULA, 4, cubes, [(-1,), (1,)] + self.FORMULA + [(2, 3)])
        self.assertEqual((out["coverage_verified"], out["coverage_clauses"][-7:], out["test_passed"]), (1, "other=1", 0))
        out, _ = self.made_up_run(self.FORMULA, 4, cubes, [(-1,)] + self.FORMULA)    # a cube not covered
        self.assertEqual(out["test_passed"], 0)

    def test_a_checker_out_of_heap_is_tried_again_alone(self):
        cubes = [(1,), (-1,)]
        out, detail = self.made_up_run(self.FORMULA, 4, cubes, [(-1,), (1,)] + self.FORMULA, heavy=True)
        self.assertEqual((out["cubes_verified"], out["test_passed"]), (2, 1))
        cubes = sorted(detail["cubes"], key=lambda c: c["cube"])
        self.assertEqual([c.get("retried", False) for c in cubes], [True, False])


# ---------------------------------------------------------------- with the real tools or the real inputs

@unittest.skipUnless(os.environ.get("HEXAGON_TOOLS"),
                     "set HEXAGON_TOOLS to a directory with the built cadical and cake_lpr")
class RealTools(unittest.TestCase):
    def setUp(self):
        d = os.environ["HEXAGON_TOOLS"]
        self.tools = {"cadical": os.path.join(d, "cadical"), "cake_lpr": os.path.join(d, "cake_lpr")}
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_proof_controls(self):
        rows, passed = H.proof_controls(self.tools, self.tmp.name)
        self.assertEqual(passed, 3, rows)
        self.assertIn("clause index unavailable", rows[2]["checker_said"])

    def test_the_pipe_from_solver_to_checker(self):
        nv, clauses = H.pigeonhole(5)
        path = os.path.join(self.tmp.name, "php.cnf")
        write(path, b"p cnf %d %d\n" % (nv, len(clauses)) + H.clause_lines(clauses))
        r = H.solve(self.tools, path, self.tmp.name, "php")
        self.assertEqual((r["answer"], r["verified"]), ("unsat", True), r)
        write(path, b"p cnf 2 1\n1 2 0\n")
        r = H.solve(self.tools, path, self.tmp.name, "sat")
        self.assertEqual((r["answer"], r["verified"]), ("sat", False))
        write(path, b"p cnf 2 5\n1 2 0\n")
        r = H.solve(self.tools, path, self.tmp.name, "broken")
        self.assertEqual((r["answer"], r["verified"]), ("error", False))


@unittest.skipUnless(inputs_dir(), "put the inputs at inputs/ or name their directory in HEXAGON_INPUTS")
class RealInputs(unittest.TestCase):
    def test_the_witness(self):
        points = H.parse_points(H.load(inputs_dir(), "Geo.lean").decode("utf-8"))
        w = H.witness(points)
        self.assertEqual((w["points"], w["collinear_triples"], w["convex_hexagons"], w["empty_hexagons"], w["layers"],
                          w["witness_ok"]), (29, 0, 5335, 0, [3, 4, 7, 7, 7, 1], 1))
        self.assertTrue(H.general_with(points, H.ADDED))

    def test_the_shapes_of_the_formula_and_the_cubes(self):
        d = inputs_dir()
        variables, formula, header, _ = H.parse_cnf(H.load(d, "final-30-ours-flat.cnf"), "formula")
        self.assertEqual((variables, len(formula), header), (75109, 452000, b"p cnf 75109 452000"))
        self.assertTrue(all(len(c) == 3 for c in formula[:H.WEAK_KEEP]) and len(formula[H.WEAK_KEEP]) != 3)
        cubes = H.parse_cubes(H.load(d, "marijn-cubes.icnf"), variables)
        self.assertEqual(len(cubes), H.CUBES_TOTAL)


if __name__ == "__main__":
    with contextlib.suppress(SystemExit):
        unittest.main()
