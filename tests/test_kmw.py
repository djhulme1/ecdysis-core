"""Kauers, Moosbauer & Wood's structured 6 x 6 decomposition (mm/kmw.py): factors compared up to sign; the graph of
shared factors and every structure of a small table; the exponent formula on known answers (log2 7, and the paper's
printed 2.805065 and 2.80190); the verdict at and beside each of its three conditions; the controls; the hash and the
seed refused; and, with the files at inputs/ (or KMW_INPUTS), that both read as 153 products, which computes neither
their exactness nor their structure.

Run with: python3 -m unittest discover -s tests -p test_kmw.py
"""

import importlib.util
import math
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("mm_kmw", os.path.join(HERE, "..", "mm", "kmw.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

INPUTS = os.environ.get("KMW_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = all(os.path.isfile(os.path.join(INPUTS, name)) for name, _ in M.INPUTS.values())


class Factors(unittest.TestCase):
    def test_up_to_sign(self):
        self.assertEqual(M.normal({3: -1, 5: 2}), M.normal({3: 1, 5: -2}))
        self.assertNotEqual(M.normal({3: 1, 5: 1}), M.normal({3: 1, 5: -1}))

    def test_toy_graph_and_structures(self):
        edges = M.share_graph(M.TOY)
        self.assertEqual(sorted(edges), [(0, 1, "A"), (1, 2, "B"), (2, 3, "C")])
        totals, _ = M.achievable(M.TOY)
        self.assertEqual(totals, {(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1)})

    def test_disjoint_parts_add(self):
        two = M.TOY + [({k + 10: v for k, v in u.items()}, {k + 10: v for k, v in v_.items()},
                        {k + 10: v for k, v in w.items()}) for u, v_, w in M.TOY]
        totals, _ = M.achievable(two)
        self.assertIn((2, 0, 2), totals)
        self.assertEqual(max(sum(t) for t in totals), 4)


class Exponent(unittest.TestCase):
    def test_known_answers(self):
        self.assertAlmostEqual(M.omega_sym(2, 2, 2, [(7, 1, 1, 1)]), math.log2(7), places=10)
        self.assertLess(abs(M.omega_sym(6, 6, 6, [(137, 1, 1, 1), (8, 2, 1, 1)]) - 2.805065), 1e-6)   # printed
        self.assertLess(abs(M.omega_sym(6, 6, 6, M.blocks_of(153, 6, 6, 6)) - 2.80190), 1e-5)

    def test_blocks(self):
        self.assertEqual(M.blocks_of(153, 6, 6, 6), [(117, 1, 1, 1), (6, 1, 1, 2), (6, 2, 1, 1), (6, 1, 2, 1)])
        self.assertEqual(M.blocks_of(153, 0, 8, 0), [(137, 1, 1, 1), (8, 2, 1, 1)])


class Verdict(unittest.TestCase):
    def test_at_and_beside(self):
        good = {(6, 6, 6), (5, 7, 6)}
        self.assertTrue(all(M.conditions(153, 0, good, 2.80194).values()))
        self.assertEqual(sum(M.conditions(152, 0, good, 2.80194).values()), 2)
        self.assertEqual(sum(M.conditions(153, 1, good, 2.80194).values()), 2)
        self.assertEqual(sum(M.conditions(153, 0, {(5, 7, 6), (6, 6, 5)}, 2.80194).values()), 2)
        self.assertEqual(sum(M.conditions(153, 0, good, 2.80195).values()), 2)


class Controls(unittest.TestCase):
    def test_known(self):
        got = M.controls_known()
        self.assertEqual(len(got), 3)
        self.assertTrue(all(got.values()), got)


class Refusals(unittest.TestCase):
    def test_hash(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, M.INPUTS["structured"][0]), "wb") as fh:
                fh.write(b"(a11)*(b11)*(c11)\n")
            with self.assertRaises(M.Refused):
                M.read_input(d, "structured")

    def test_seed(self):
        with self.assertRaises(M.Refused):
            M.run("xyz", inputs=os.path.join(HERE, "_never"), results=os.path.join(HERE, "_never"))


@unittest.skipUnless(HAVE, "the two files are not at inputs/ (or KMW_INPUTS)")
class Pinned(unittest.TestCase):
    def test_both_read_as_153_products(self):
        for key in M.INPUTS:
            with self.subTest(key=key):
                self.assertEqual(len(M.CHECK.read_flips(M.read_input(INPUTS, key), 6, 6, 6)), 153)


if __name__ == "__main__":
    unittest.main()
