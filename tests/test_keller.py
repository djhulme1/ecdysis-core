"""The Keller check without the inputs: the encoding against adjacency, pair by pair, for small n and s; its sizes
against the paper's Table 2; the multiset comparison and the reading of the lemma units; the map that puts G_{7,3}
and G_{7,4} inside G_{7,6}; the reading of the dimension-8 figure from a made-up e-print; the draws. With the built
tools (KELLER_TOOLS) and the inputs (KELLER_INPUTS), the small refutations, the formula of record and the paper's
own figure as well.

Run with: python3 -m unittest discover -s tests
"""

import collections
import importlib.util
import io
import itertools
import os
import tarfile
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("keller_check", os.path.join(HERE, "..", "keller", "check.py"))
K = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(K)

SEED = "0" * 63 + "7"


def blocks(n, s):
    """(variables, the exactly-one clauses, for each pair i < i' the clauses that mention its auxiliary variables),
    with the auxiliary variables numbered pair by pair as rule 1 says."""
    nv, clauses = K.encode(n, s)
    x_max = (1 << n) * n * s
    owner, v = {}, x_max
    for i in range(1 << n):
        for ii in range(i + 1, 1 << n):
            d = bin(i ^ ii).count("1")
            count = d + ((n - 1) * s if d == 1 else 0)
            for a in range(v + 1, v + count + 1):
                owner[a] = (i, ii)
            v += count
    assert v == nv, (v, nv)
    one, out = [], collections.defaultdict(list)
    for c in clauses:
        pairs = {owner[abs(lit)] for lit in c if abs(lit) > x_max}
        assert len(pairs) <= 1, c
        if pairs:
            out[pairs.pop()].append(c)
        else:
            one.append(c)
    return nv, one, out


def decided(clauses, fixed):
    """Whether the clauses can be satisfied with the variables in fixed held to their values: unit propagation to a
    fixpoint, then every free variable set true and the clauses checked (enough for rule 1's shape, where auxiliary
    variables are only ever forced false; None if that completion fails, which would mean another shape)."""
    val = dict(fixed)
    changed = True
    while changed:
        changed = False
        for c in clauses:
            if any(val.get(abs(lit)) == (lit > 0) for lit in c):
                continue
            free = [lit for lit in c if abs(lit) not in val]
            if not free:
                return False
            if len(free) == 1:
                val[abs(free[0])] = free[0] > 0
                changed = True
    ok = all(any(val.get(abs(lit), True) == (lit > 0) for lit in c) for c in clauses)
    return True if ok else None


def class_values(n, s, i):
    """Every vertex c_i can be: coordinate j in s w(i)_j + {0, ..., s-1}."""
    return itertools.product(*[range(s * ((i >> j) & 1), s * ((i >> j) & 1) + s) for j in range(n)])


def one_hot(n, s, i, c):
    return {K.x_var(n, s, i, j, k): c[j] - s * ((i >> j) & 1) == k for j in range(n) for k in range(s)}


class Encoding(unittest.TestCase):
    def test_table_2(self):
        sizes, ok = K.table_sizes()
        self.assertTrue(ok)
        self.assertEqual(sizes, {3: (39424, 200320), 4: (43008, 265728), 6: (50176, 399232)})

    def test_each_pair_says_exactly_adjacent(self):
        for n, s in ((2, 2), (2, 3), (3, 2), (3, 3)):
            _, _, by_pair = blocks(n, s)
            self.assertEqual(len(by_pair), (1 << n) * ((1 << n) - 1) // 2)
            checked = 0
            for (i, ii), clauses in by_pair.items():
                for u in class_values(n, s, i):
                    for v in class_values(n, s, ii):
                        fixed = {**one_hot(n, s, i, u), **one_hot(n, s, ii, v)}
                        got = decided(clauses, fixed)
                        self.assertIsNotNone(got)
                        self.assertEqual(got, K.adjacent(u, v, s), (n, s, i, ii, u, v))
                        checked += 1
            self.assertGreater(checked, 0)

    def test_exactly_one_value_per_coordinate(self):
        n, s = 2, 3
        _, one, _ = blocks(n, s)
        for i in range(1 << n):
            for j in range(n):
                xs = [K.x_var(n, s, i, j, k) for k in range(s)]
                mine = [c for c in one if all(abs(lit) in xs for lit in c)]
                for bits in itertools.product((False, True), repeat=s):
                    fixed = dict(zip(xs, bits))
                    sat = all(any(fixed[abs(lit)] == (lit > 0) for lit in c) for c in mine)
                    self.assertEqual(sat, sum(bits) == 1)

    def test_no_clique_of_four_in_dimension_2(self):
        n, s = 2, 2
        nv, clauses = K.encode(n, s)
        for vertices in itertools.product(*[list(class_values(n, s, i)) for i in range(1 << n)]):
            fixed = {}
            for i, c in enumerate(vertices):
                fixed.update(one_hot(n, s, i, c))
            clique = all(K.adjacent(u, v, s) for u, v in itertools.combinations(vertices, 2))
            self.assertFalse(clique)
            self.assertFalse(decided(clauses, fixed))

    def test_decode(self):
        self.assertEqual(K.decode(7, 6, 1), (0, 0, 0))
        self.assertEqual(K.decode(7, 6, 43), (1, 0, 6))
        self.assertEqual(K.decode(7, 6, 134), (3, 1, 7))
        self.assertIsNone(K.decode(7, 6, -1))
        self.assertIsNone(K.decode(7, 6, 128 * 7 * 6 + 1))


class FormulaOfRecord(unittest.TestCase):
    def test_compare_as_multisets(self):
        base = [(1, 2), (-1, 3), (2, 3)]
        found, missing, extra = K.compare([(3, -1), (2, 1), (4,), (2, 1)], base)
        self.assertEqual((found, missing), (2, 1))
        self.assertEqual(sorted(extra), [(1, 2), (4,)])

    def canonical(self):
        units = []
        for i, vec in K.CANONICAL.items():
            for j, value in enumerate(vec):
                if value is not None:
                    w = (i >> j) & 1
                    units.append((K.x_var(7, 6, i, j, value - 6 * w),))
        return units

    def test_lemma_units(self):
        units = self.canonical()
        self.assertEqual([u[0] for u in units], [1, 7, 13, 19, 25, 31, 37, 43, 50, 55, 61, 67, 73, 79, 127, 134, 152,
                                                 158, 164])
        text, ok = K.lemma_units(units)
        self.assertTrue(ok)
        self.assertEqual(text, "c0=(0,0,0,0,0,0,0); c1=(6,1,0,0,0,0,0); c3=(6,7,*,*,1,1,1)")
        changed = [(50 + 1,) if u == (50,) else u for u in units]
        self.assertFalse(K.lemma_units(changed)[1])
        self.assertFalse(K.lemma_units(units[:-1])[1])
        self.assertFalse(K.lemma_units(units + [(-200,)])[1])


class ThreeGraphs(unittest.TestCase):
    def test_the_map(self):
        self.assertTrue(K.embeds(3))
        self.assertTrue(K.embeds(4))
        self.assertEqual([K.embedding(3)(a) for a in range(6)], [0, 1, 2, 6, 7, 8])
        self.assertFalse(K.embeds(7))

    def test_adjacency_survives_whole_vertices(self):
        for s in (3, 4):
            f = K.embedding(s)
            vs = list(itertools.product(range(2 * s), repeat=2))
            for u, v in itertools.product(vs, repeat=2):
                self.assertEqual(K.adjacent(u, v, s), K.adjacent(tuple(map(f, u)), tuple(map(f, v)), 6))


def eprint(vertices, between="", after=""):
    """A made-up e-print holding main-clean.tex with the figure drawn as the paper draws it."""
    name = "abcd"
    dice = []
    for k, v in enumerate(vertices):
        x, y = k % 16, k // 16
        a = "".join("{\\c%s}" % name[d] for d in v[:4])
        b = "".join("{\\c%s}" % name[d] for d in v[4:])
        dice.append(f"\\dicea{{{x}}}{{{y}}}{a}\\diceb{{{x}}}{{{y}}}{b}")
    tex = ("\\begin{figure}[t]\n\\centering\n\\begin{tikzpicture}[scale=0.70]\n\n" + K.FRAME + "\n\n"
           + ("\n" + between).join(dice) + after + "\n\n\\end{tikzpicture}\n\\caption{A clique.}\n"
           "\\label{fig:clique256}\n\\end{figure}\n")
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:gz") as tar:
        data = tex.encode("utf-8")
        info = tarfile.TarInfo("main-clean.tex")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    return out.getvalue()


class Witness(unittest.TestCase):
    def vertices(self):
        return [tuple((k >> (2 * j)) & 3 if j < 4 else (k * 7 >> j) & 3 for j in range(8)) for k in range(256)]

    def test_the_figure_is_read_in_order(self):
        vs = self.vertices()
        self.assertEqual(K.parse_witness(eprint(vs)), vs)

    def test_anything_else_is_refused(self):
        vs = self.vertices()
        with self.assertRaises(K.Refused):
            K.parse_witness(eprint(vs, between="\\node at (0,0) {x};\n"))
        with self.assertRaises(K.Refused):
            K.parse_witness(eprint(vs, after="\n\\draw (0,0) -- (1,1);"))
        with self.assertRaises(K.Refused):
            K.parse_witness(eprint(vs[:255]))

    def test_adjacency(self):
        self.assertTrue(K.adjacent((0, 0), (2, 1), 2))
        self.assertFalse(K.adjacent((0, 0), (2, 0), 2))
        self.assertFalse(K.adjacent((0, 0), (1, 1), 2))
        self.assertTrue(K.adjacent((0, 3, 1), (2, 3, 0), 2))

    def test_units_need_every_slot_once(self):
        n, s = 2, 2
        vs = [next(iter(class_values(n, s, i))) for i in range(1 << n)]
        units = K.witness_units(vs, n, s)
        self.assertEqual(len(units), n * (1 << n))
        self.assertIsNone(K.witness_units(vs[:-1] + [vs[0]], n, s))


class Draws(unittest.TestCase):
    def test_the_seed_alone_decides(self):
        a = K.H.sample(SEED, "keller/cubes", K.CUBES_TOTAL, K.CUBES)
        self.assertEqual(a, K.H.sample(SEED, "keller/cubes", K.CUBES_TOTAL, K.CUBES))
        self.assertEqual(len(set(a)), K.CUBES)
        self.assertTrue(all(0 <= i < K.CUBES_TOTAL for i in a))
        self.assertNotEqual(a, K.H.sample("f" * 64, "keller/cubes", K.CUBES_TOTAL, K.CUBES))
        self.assertNotEqual(K.H.sample(SEED, "keller/drop", K.CUBES_TOTAL, 1)[0], a[0])


def tools_dir():
    d = os.environ.get("KELLER_TOOLS")
    return d if d and all(os.path.isfile(os.path.join(d, t)) for t in ("cadical", "cake_lpr")) else None


def inputs_dir():
    d = os.environ.get("KELLER_INPUTS") or os.path.join(HERE, "..", "inputs")
    return d if all(os.path.isfile(os.path.join(d, i[0])) for i in K.INPUTS[:3]) else None


@unittest.skipUnless(tools_dir(), "the built tools are not in KELLER_TOOLS")
class Tools(unittest.TestCase):
    def test_small_dimensions_are_refuted(self):
        tools = {"cadical": os.path.join(tools_dir(), "cadical"), "cake_lpr": os.path.join(tools_dir(), "cake_lpr")}
        with tempfile.TemporaryDirectory() as work:
            for n, s in K.SMALL:
                nv, clauses = K.encode(n, s)
                r = K.solve_cnf(tools, work, f"t-{n}-{s}", nv, clauses)
                self.assertEqual((r["answer"], r["verified"]), ("unsat", True), (n, s))


@unittest.skipUnless(inputs_dir(), "the inputs are not at inputs/ (or KELLER_INPUTS)")
class TheInputs(unittest.TestCase):
    def test_the_formula_of_record(self):
        f = K.check_formula(inputs_dir())
        self.assertEqual((f["variables"], f["clauses"]), (K.VARIABLES, K.CLAUSES))
        self.assertEqual((f["found"], f["missing"], f["units"], f["others"]), (399232, 0, 19, 4224))
        self.assertTrue(f["units_ok"])
        self.assertEqual(f["units_text"], "c0=(0,0,0,0,0,0,0); c1=(6,1,0,0,0,0,0); c3=(6,7,*,*,1,1,1)")
        self.assertEqual(f["missing_when_cut"], 1)
        self.assertTrue(f["others_on_x_only"])
        self.assertTrue(f["table_ok"])

    def test_the_papers_figure(self):
        vs = K.parse_witness(K.load(inputs_dir(), "arXiv-1910.03740v5.tar.gz"))
        self.assertEqual(len(set(vs)), 256)
        self.assertEqual(vs[:2], [(0,) * 8, (2, 1, 0, 0, 0, 0, 0, 0)])
        self.assertEqual(K.non_adjacent(vs, 2), 0)
        self.assertEqual(K.non_adjacent([tuple(map(K.embedding(2), v)) for v in vs], 6), 0)
        self.assertIsNotNone(K.witness_units(vs, 8, 2))

    def test_the_cubes(self):
        cubes = K.H.parse_cubes(K.load(inputs_dir(), "s6.dnf"), K.VARIABLES)
        self.assertEqual(len(cubes), K.CUBES_TOTAL)
        self.assertEqual(len({abs(lit) for c in cubes for lit in c}), 39)

    def test_a_changed_input_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "s6.dnf"), "wb") as f:
                f.write(b"a 1 0\n" * (K.INPUTS[1][2] // 6))
            with self.assertRaises(K.Refused):
                K.load(d, "s6.dnf")


if __name__ == "__main__":
    unittest.main()
