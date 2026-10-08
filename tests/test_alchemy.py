"""The AlChemy check without the archive: the input file's rewriting, the population files, the pair mode's reader, the
copying functions, the largest self-maintaining subset, the knitting count, the paper's two laws worked by hand and
the draws. With the archive (ALCHEMY_INPUTS, or inputs/) and gcc, the build and the paper's laws by its own reducer.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("alchemy_check", os.path.join(HERE, "..", "alchemy", "check.py"))
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)

SEED = "0" * 63 + "7"
TEMPLATE = """ *  Every line in which there is an 'equal' sign is an input
		     name of simulation =  0Debug
      maximum overall number of objects =  1000
	number of collisions to perform =  100000
		      snapshot interval =  5000
		            random seed =  714321
	       maximum expression depth =  10
		bind all free variables =  0
	      file with initial objects = 0Debug/Ddata/D20.typ
  acceptance frequency for copy actions = 0.0
"""


def law(i, j, k, l_):
    """The paper's laws: (O(i, j))O(k, l) = O(i - 1, j - 1) when j > 1, and O(k + i - 1, l + i - 1) when j = 1."""
    return A.O(i - 1, j - 1) if j > 1 else A.O(k + i - 1, l_ + i - 1)


class InputFile(unittest.TestCase):
    def test_each_line_set_once(self):
        t = A.input_file(TEMPLATE, name_of_simulation="R", maximum_overall_number_of_objects=3000,
                         number_of_collisions_to_perform=7, snapshot_interval=7, random_seed=99,
                         bind_all_free_variables=1, file_with_initial_objects="start",
                         acceptance_frequency_for_copy_actions="0.0")
        lines = {ln.split("=")[0].strip(): ln.split("=", 1)[1].strip() for ln in t.split("\n") if "=" in ln}
        self.assertEqual(lines["name of simulation"], "R")
        self.assertEqual(lines["maximum overall number of objects"], "3000")
        self.assertEqual(lines["bind all free variables"], "1")
        self.assertEqual(lines["file with initial objects"], "start")
        self.assertEqual(lines["maximum expression depth"], "10")
        self.assertIn("'equal' sign", t)

    def test_a_missing_line_is_refused(self):
        with self.assertRaises(A.Refused):
            A.input_file(TEMPLATE.replace("random seed", "seed"), random_seed=1)
        with self.assertRaises(A.Refused):
            A.input_file(TEMPLATE + "\t\t random seed = 3\n", random_seed=1)


class Objects(unittest.TestCase):
    def test_round_trip(self):
        pop = {b"\\x1.x1": 999, b"\\x1.\\x2.x2": 1}
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "start")
            A.write_objects(p, pop)
            with open(p, "rb") as f:
                self.assertEqual(f.read(), b"\\x1.\\x2.x2 {1 1 0}\n\\x1.x1 {2 999 0}\n")
            self.assertEqual(A.read_objects(p), pop)
            with open(p, "wb") as f:
                f.write(b"(a)b {1 1 0}\n")
            with self.assertRaises(RuntimeError):
                A.read_objects(p)


class Pairs(unittest.TestCase):
    order = [b"\\x1.\\x2.x1", b"\\x1.x1"]

    def test_reader(self):
        data = (b"  1 [0] :   1 [0] =>  *   \\x1.\\x2.\\x3.x2\n"
                b"  1 [0] :   2 [0] =>  *   \\x1.\\x2.\\x3.x3\n"
                b"  2 [0] :   1 [0] =>   1 [0] 1\n"
                b"  2 [0] :   2 [0] =>   2 [0] 1\n")
        p = A.parse_pairs(data, self.order)
        K, I = self.order
        self.assertEqual(p[(K, K)], b"\\x1.\\x2.\\x3.x2")
        self.assertEqual(p[(I, K)], K)
        self.assertEqual(p[(I, I)], I)
        p = A.parse_pairs(data.replace(b"=>   2 [0] 1", b"=>  +"), self.order)
        self.assertIsNone(p[(I, I)])

    def test_refusals(self):
        good = b"  1 [0] :   1 [0] =>  R\n  1 [0] :   2 [0] =>  R\n  2 [0] :   1 [0] =>  R\n"
        with self.assertRaises(RuntimeError):            # a pair missing
            A.parse_pairs(good, self.order)
        with self.assertRaises(RuntimeError):            # a pair twice
            A.parse_pairs(good + b"  2 [0] :   1 [0] =>  R\n", self.order)
        with self.assertRaises(RuntimeError):            # a product out of range
            A.parse_pairs(good + b"  2 [0] :   2 [0] =>   3 [0] 1\n", self.order)
        with self.assertRaises(RuntimeError):            # anything else
            A.parse_pairs(good + b"  2 [0] :   2 [0] => ?\n", self.order)


def figure1(n):
    objs = [A.O(i, j) for i in range(1, n + 1) for j in range(1, i + 1)]
    table = {}
    for i in range(1, n + 1):
        for j in range(1, i + 1):
            for k in range(1, n + 1):
                for l_ in range(1, k + 1):
                    table[(A.O(i, j), A.O(k, l_))] = law(i, j, k, l_)
    return objs, table


class Analysis(unittest.TestCase):
    def test_standard_forms(self):
        self.assertEqual(A.O(1, 1), b"\\x1.x1")
        self.assertEqual(A.O(3, 2), b"\\x1.\\x2.\\x3.x2")

    def test_copying(self):
        objs, table = figure1(3)
        self.assertEqual(A.copying(objs, table), {A.O(1, 1)})
        self.assertEqual(A.copying([A.O(1, 1)], table), {A.O(1, 1)})
        two = {(a, b): a for a in (b"f", b"g") for b in (b"f", b"g")}
        self.assertEqual(A.copying([b"f", b"g"], two), {b"f", b"g"})
        two[(b"f", b"g")] = None                         # an elastic collision is not a copy
        self.assertEqual(A.copying([b"f", b"g"], two), {b"g"})

    def test_self_maintaining_by_hand(self):
        objs, table = figure1(4)
        self.assertEqual(A.self_maintaining(objs, table), set(objs) - {A.O(4, 1)})
        objs, table = figure1(2)                     # I, K, O(2, 2): K is made by nothing but a copy
        self.assertEqual(A.self_maintaining(objs, table), set())

    def test_self_maintaining_is_the_largest(self):
        # a cycle a -> b -> c -> a kept; d made only by itself (a copy) and e made only by d: both dropped
        t = {(x, y): None for x in b"abcde" for y in b"abcde"}
        t = {(bytes([x]), bytes([y])): None for x in b"abcde" for y in b"abcde"}
        t[(b"a", b"b")] = b"c"
        t[(b"b", b"c")] = b"a"
        t[(b"c", b"a")] = b"b"
        t[(b"d", b"a")] = b"d"
        t[(b"d", b"b")] = b"e"
        self.assertEqual(A.self_maintaining([b"a", b"b", b"c", b"d", b"e"], t), {b"a", b"b", b"c"})

    def test_organisation_drops_copying_functions(self):
        objs, table = figure1(4)                     # the identity is made by O(2, 2), but it copies everything
        self.assertEqual(A.organisation(objs, table), set(objs) - {A.O(1, 1), A.O(4, 1)})
        # a set that needs its copying function i: i is made by (a)b, and a and b by acting on i
        t = {(bytes([x]), bytes([y])): None for x in b"iab" for y in b"iab"}
        for y in b"iab":
            t[(b"i", bytes([y]))] = bytes([y])
        t[(b"a", b"i")], t[(b"b", b"i")], t[(b"a", b"b")] = b"b", b"a", b"i"
        self.assertEqual(A.self_maintaining([b"i", b"a", b"b"], t), {b"i", b"a", b"b"})
        self.assertEqual(A.organisation([b"i", b"a", b"b"], t), set())
        # a hypercycle of two copiers (each copies itself and the other) is copying, and no organisation
        h = {(b"a", b"a"): b"a", (b"a", b"b"): b"b", (b"b", b"a"): b"a", (b"b", b"b"): b"b"}
        self.assertEqual(A.copying([b"a", b"b"], h), {b"a", b"b"})
        self.assertEqual(A.organisation([b"a", b"b"], h), set())

    def test_persists(self):
        s0 = {b"a", b"b", b"c", b"d"}
        pop = {b"a": 300, b"b": 100, b"c": 60, b"x": 400, b"y": 140}
        self.assertTrue(A.persists(s0, {b"a", b"b", b"c", b"x"}, pop))         # 460 of 860 objects from before
        self.assertFalse(A.persists(s0, {b"a", b"b", b"c", b"x", b"y"}, pop))  # 460 of 1,000
        self.assertFalse(A.persists(s0, {b"a", b"b", b"x"}, pop))              # two species from before
        self.assertTrue(A.persists(s0, {b"a", b"b", b"c"}, pop))               # shrunk, all from before
        self.assertFalse(A.persists({b"a", b"b"}, {b"a", b"b", b"c"}, pop))    # S0 too small

    def test_keeps(self):
        whole = {b"a", b"b", b"c", b"x", b"y"}
        pop = {b"a": 100, b"b": 100, b"c": 100, b"x": 2000, b"y": 700}
        self.assertTrue(A.keeps(whole, {b"a", b"b", b"c", b"q"}, pop))         # 300 of 3,000: a tenth
        pop[b"x"] += 1
        self.assertFalse(A.keeps(whole, {b"a", b"b", b"c"}, pop))              # 300 of 3,001
        self.assertFalse(A.keeps(whole, {b"x", b"y"}, pop))                    # two species
        self.assertTrue(A.keeps(whole, {b"x", b"y", b"a"}, pop))

    def test_knit(self):
        t = {(bytes([x]), bytes([y])): None for x in b"abcxyg" for y in b"abcxyg"}
        whole = {b"a", b"b", b"x", b"y", b"g"}
        a, b = {b"a", b"b"}, {b"x", b"y"}
        self.assertEqual(A.knit(whole, a, b, t), 0)
        t[(b"y", b"a")] = b"g"                          # a cross product in the whole: glue
        t[(b"a", b"x")] = b"x"                          # a copy does not knit
        t[(b"b", b"x")] = b"c"                          # nor a product outside the whole
        self.assertEqual(A.knit(whole, a, b, t), 1)


class Draws(unittest.TestCase):
    def test_seeds(self):
        s = A.H.Stream(SEED, "alchemy/l1")
        got = [A.seed_for(s) for _ in range(50)]
        self.assertTrue(all(1 <= x < (1 << 31) - 1 for x in got))
        again = A.H.Stream(SEED, "alchemy/l1")
        self.assertEqual(got, [A.seed_for(again) for _ in range(50)])
        self.assertNotEqual(got[0], A.seed_for(A.H.Stream(SEED, "alchemy/l0")))


def inputs_dir():
    d = os.environ.get("ALCHEMY_INPUTS") or os.path.join(HERE, "..", "inputs")
    return d if os.path.isfile(os.path.join(d, A.ARCHIVE)) and shutil.which("gcc") else None


@unittest.skipUnless(inputs_dir(), "the archive is not at inputs/ (or ALCHEMY_INPUTS), or there is no gcc")
class TheArchive(unittest.TestCase):
    def test_the_paper_laws_by_its_own_reducer(self):
        with tempfile.TemporaryDirectory() as d:
            binary, template, _ = A.build(inputs_dir(), os.path.join(d, "bin"), os.path.join(d, "src"))
            reactor = A.Reactor(binary, template, os.path.join(d, "runs"))
            objs, want = figure1(3)
            order, products = reactor.table("t", objs)
            self.assertEqual({k: products[k] for k in want}, want)

    def test_a_changed_archive_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, A.ARCHIVE), "wb") as f:
                f.write(b"not the archive")
            with self.assertRaises(A.Refused):
                A.load(d, A.ARCHIVE)


if __name__ == "__main__":
    unittest.main()
