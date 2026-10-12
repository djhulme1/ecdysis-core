"""Scheucher's two disjoint 5-holes (holes/h55.py): the formula's size against the paper's, its groups and its DIMACS
form; the exact geometry (holes, separation, the angular order) on hand examples; the geometric assignment against the
definitional clauses on drawn sets; and, with the e-print at inputs/ (or H55_INPUTS), the formulas for 16 and 17 points
byte for byte the author's program's, and the witness admitted.

Run with: python3 -m unittest discover -s tests
"""

import hashlib
import importlib.util
import os
import unittest
from math import comb

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("holes_h55", os.path.join(HERE, "..", "holes", "h55.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

INPUTS = os.environ.get("H55_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = os.path.isfile(os.path.join(INPUTS, M.EPRINT[0]))


def variables(n):
    return n * (n - 1) * (n - 2) + 5 * comb(n, 4) + comb(n, 3) + comb(n, 5) + 2 * n * (n - 1)


class Formula(unittest.TestCase):
    def test_sizes(self):
        F = M.Formula(17)
        self.assertEqual((len(F.names), len(F.clauses)), (23392, 825689))      # the paper's 23 392 and 825 689
        self.assertEqual(len(F.names), variables(17))
        for n in (6, 11):
            with self.subTest(n=n):
                self.assertEqual(len(M.Formula(n).names), variables(n))

    def test_dimacs_form(self):
        F = M.Formula(6)
        lines = F.dimacs().decode("ascii").splitlines()
        self.assertEqual(lines[0], f"p cnf {len(F.names)} {len(F.clauses)}")
        self.assertEqual(lines[1], " ".join(str(x) for x in F.clauses[0]) + " 0")
        self.assertEqual(len(lines), len(F.clauses) + 1)

    def test_groups_appear_in_order(self):
        F = M.Formula(12)
        self.assertEqual(F.groups, sorted(F.groups))
        self.assertEqual(set(F.groups), set(range(9)))


class Geometry(unittest.TestCase):
    PENTAGON = [(0, 0), (10, 0), (13, 9), (5, 15), (-3, 9)]

    def test_holes(self):
        self.assertEqual(M.holes(self.PENTAGON), [(0, 1, 2, 3, 4)])
        self.assertEqual(M.holes(self.PENTAGON + [(5, 6)]), [])                 # a point inside: no 5-hole
        self.assertEqual(len(M.holes(self.PENTAGON + [(50, 50)])), 1)            # a point outside: still one

    def test_separation(self):
        far = [(x + 100, y) for x, y in self.PENTAGON]
        near = [(x + 8, y + 3) for x, y in self.PENTAGON]
        self.assertTrue(M.disjoint(self.PENTAGON, far))
        self.assertFalse(M.disjoint(self.PENTAGON, near))

    def test_sorted_around_starts_at_the_lowest_and_turns_left(self):
        pts = [(0, 270), (140, 0), (0, 0), (9, 127), (59, 85)]
        P = M.sorted_around(pts)
        self.assertEqual(P[0], (0, 0))
        self.assertTrue(all(M.orient(P[0], P[b], P[c]) > 0 for b in range(1, 5) for c in range(b + 1, 5)))

    def test_definitions_on_drawn_sets(self):
        self.assertEqual(M.definitions_control("0" * 64), (0, 0))


@unittest.skipUnless(HAVE, "needs the e-print at inputs/ or H55_INPUTS")
class EPrint(unittest.TestCase):
    def test_the_authors_formulas_and_witness(self):
        printed, witness = M.read_eprint(M.load(INPUTS, M.EPRINT[0]))
        self.assertTrue(printed)
        for n in (16, 17):
            with self.subTest(n=n):
                self.assertEqual(hashlib.sha256(M.Formula(n).dimacs()).hexdigest(), M.FORMULA_SHA256[n])
        W = M.sorted_around(witness)
        hs = M.holes(W)
        self.assertEqual((len(W), M.disjoint_pairs(W, hs)), (16, 0))
        F = M.Formula(16)
        self.assertEqual(M.broken(F, M.geometric_assignment(F, W), range(9)), [])


if __name__ == "__main__":
    unittest.main()
