"""The Pythagorean triples check without the inputs: the triples against a direct search, the encoding's sizes against
the paper's, the tree merge of the cover on small trees, the colouring check, the cube reader and the draws. With the
inputs (PTN_INPUTS, or inputs/), the formulas of record as well.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import itertools
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("ptn_check", os.path.join(HERE, "..", "ptn", "check.py"))
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)

SEED = "0" * 63 + "5"


class Encoding(unittest.TestCase):
    def test_triples_against_a_direct_search(self):
        for n in (5, 13, 30, 100):
            direct = [(a, b, c) for a in range(1, n + 1) for b in range(a, n + 1) for c in range(b, n + 1)
                      if a * a + b * b == c * c]
            self.assertEqual(P.triples(n), direct)

    def test_sizes_are_the_papers(self):
        for n, (variables, clauses) in P.PRINTED.items():
            ts, cl = P.encode(n)
            self.assertEqual((P.occurring(cl), len(cl)), (variables, clauses))
            self.assertEqual(len(cl), 2 * len(ts))
        self.assertEqual(len(P.triples(7825)), 9472)
        self.assertEqual(len(P.triples(7824)), 9465)

    def test_the_clauses(self):
        _, cl = P.encode(13)
        self.assertEqual(cl, [(3, 4, 5), (-3, -4, -5), (5, 12, 13), (-5, -12, -13), (6, 8, 10), (-6, -8, -10)])


class Cover(unittest.TestCase):
    def tree(self, depth):
        """The leaves of a full decision tree on the variables 1 .. depth, each path in order."""
        return [tuple(v if bit else -v for v, bit in zip(range(1, depth + 1), bits))
                for bits in itertools.product((1, 0), repeat=depth)]

    def test_a_full_tree_ends_in_the_empty_cube(self):
        for depth in (1, 3, 6):
            leaves = self.tree(depth)
            merges, rounds, left = P.tree_cover(leaves)
            self.assertEqual(left, {()})
            self.assertEqual(merges, len(leaves) - 1)

    def test_an_uneven_tree(self):
        leaves = [(1, 2), (1, -2, 5), (1, -2, -5), (-1,)]
        merges, _, left = P.tree_cover(leaves)
        self.assertEqual((merges, left), (3, {()}))

    def test_a_missing_leaf_is_not_a_cover(self):
        leaves = self.tree(4)
        for k in range(len(leaves)):
            _, _, left = P.tree_cover(leaves[:k] + leaves[k + 1:])
            self.assertNotEqual(left, {()})
            self.assertGreater(len(left), 0)

    def test_the_reader(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "c.cubes")
            with open(path, "wb") as f:
                f.write(b"a 1 -2 3 0\na -1 0\n")
            self.assertEqual(P.parse_cubes(path, 5), [(1, -2, 3), (-1,)])
            for bad in (b"a 1 -1 0\n", b"a 6 0\n", b"b 1 0\n", b"a 1 x 0\n", b"a 0\n"):
                with open(path, "wb") as f:
                    f.write(bad)
                with self.assertRaises(P.Refused):
                    P.parse_cubes(path, 5)


class Witness(unittest.TestCase):
    def test_monochromatic(self):
        ts = P.triples(13)
        colour = P.colouring({3, 4, 5, 6, 8, 10, 12, 13}, 13)
        self.assertEqual(P.monochromatic(colour, ts), 3)
        colour = P.colouring({3, 4, 6, 12}, 13)
        self.assertEqual(P.monochromatic(colour, ts), 0)
        self.assertFalse(colour[7])


class Draws(unittest.TestCase):
    def test_the_seed_alone_decides(self):
        a = P.H.sample(SEED, "ptn/cubes", P.CUBES_TOTAL, P.CUBES)
        self.assertEqual(a, P.H.sample(SEED, "ptn/cubes", P.CUBES_TOTAL, P.CUBES))
        self.assertEqual(len(set(a)), P.CUBES)
        self.assertNotEqual(a, P.H.sample("e" * 64, "ptn/cubes", P.CUBES_TOTAL, P.CUBES))
        self.assertLessEqual(len(",".join(str(i + 1) for i in a)), P.LIMIT)


def inputs_dir():
    d = os.environ.get("PTN_INPUTS") or os.path.join(HERE, "..", "inputs")
    return d if all(os.path.isfile(os.path.join(d, i[0])) for i in P.INPUTS[:5]) else None


@unittest.skipUnless(inputs_dir(), "the inputs are not at inputs/ (or PTN_INPUTS)")
class TheInputs(unittest.TestCase):
    def test_the_formulas_of_record(self):
        f = P.check_formulas(inputs_dir())
        self.assertTrue(f["encoding_equal"])
        self.assertEqual(f["encoding_clauses"], 18944)
        self.assertEqual(f["transformed_units"], [2520])
        self.assertEqual((f["transformed_kept_variables"], f["transformed_kept"]), P.PRINTED_BCE)
        self.assertTrue(f["kept_in_plain"] and f["negation_closed"] and f["transformed_sound"])
        self.assertTrue(f["sizes_ok"] and f["transformed_sizes_ok"])
        self.assertEqual(f["missing_when_cut"], 1)
        self.assertTrue(f["backbone_has_encoding"] and f["backbone_extra_units_only"])
        self.assertEqual(len(f["backbone_units"]), 2304)

    def test_a_changed_input_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "transformed.cnf"), "wb") as f:
                f.write(b"p cnf 1 1\n1 0\n")
            with self.assertRaises(P.Refused):
                P.load(d, "transformed.cnf")


if __name__ == "__main__":
    unittest.main()
