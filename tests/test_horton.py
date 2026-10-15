"""Horton's sets (holes/horton.py and holes/horton.c): the construction on the hand-worked S_2, the observations'
machinery, the hull and brute force on hand-made sets, and the counting (Python and C) on a convex heptagon, a square
with a point inside and seed-drawn sets. No S_k with k > 2 is built and no S_k is searched for empty polygons here.

Run with: python3 -m unittest tests.test_horton
"""

import importlib.util
import os
import shutil
import tempfile
import unittest
from math import comb

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("holes_horton", os.path.join(HERE, "..", "holes", "horton.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "5c" * 32
HEPTAGON = [(0, 0), (4, -1), (7, 1), (8, 5), (5, 8), (1, 7), (-2, 3)]     # convex, no three collinear


class Construction(unittest.TestCase):
    def test_digits(self):
        self.assertEqual(M.digits(1, 2), [0, 1])
        self.assertEqual(M.digits(2, 2), [1, 0])
        self.assertEqual(M.digits(6, 3), [1, 1, 0])

    def test_s2_by_hand(self):
        # c = 5: d(0) = 0, d(1) = a_2 c = 5, d(2) = a_1 = 1, d(3) = 1 + 5 = 6
        self.assertEqual(M.horton(2), [(0, 0), (1, 5), (2, 1), (3, 6)])
        self.assertEqual(M.horton(1), [(0, 0), (1, 1)])

    def test_other_readings(self):
        self.assertEqual(M.horton(2, heavy_first=True), [(0, 0), (1, 1), (2, 5), (3, 6)])
        self.assertEqual(M.horton(2, c=2), [(0, 0), (1, 2), (2, 1), (3, 3)])

    def test_observations_s2(self):
        self.assertTrue(all(M.observations(2, M.horton(2)).values()))
        obs = M.observations(2, M.horton(2, heavy_first=True))
        self.assertFalse(obs["(e) halving x and multiplying y by c takes B onto L"])
        # a moved point breaks (b)
        bad = M.horton(2)
        bad[3] = (3, 7)
        self.assertFalse(M.observations(2, bad)["(b) R is L moved by (2^(k-1), 1)"])


class Geometry(unittest.TestCase):
    def test_orient_and_hull(self):
        self.assertGreater(M.orient((0, 0), (1, 0), (0, 1)), 0)
        self.assertEqual(M.orient((0, 0), (1, 1), (2, 2)), 0)
        self.assertEqual(len(M.hull(HEPTAGON)), 7)
        self.assertEqual(sorted(M.hull([(0, 0), (4, 0), (4, 4), (0, 4), (1, 2)])), [(0, 0), (0, 4), (4, 0), (4, 4)])

    def test_brute_heptagon(self):
        self.assertEqual(M.brute(HEPTAGON), [comb(7, 3), comb(7, 4), comb(7, 5), comb(7, 6), 1])

    def test_brute_square_with_point(self):
        pts = [(0, 0), (4, 0), (4, 4), (0, 4), (1, 2)]
        # 10 triangles, of which the corner triangles (0,0),(4,0),(0,4) and (0,0),(4,4),(0,4) hold (1, 2)
        b = M.brute(pts)
        self.assertEqual(b[0], 8)
        self.assertEqual(b[4], 0)

    def test_general(self):
        self.assertTrue(M.general(HEPTAGON))
        self.assertFalse(M.general([(0, 0), (1, 1), (3, 3), (0, 5)]))


class Counting(unittest.TestCase):
    def test_python_counting(self):
        self.assertEqual(M.count_py(HEPTAGON), (0, [comb(7, 3), comb(7, 4), comb(7, 5), comb(7, 6), 1]))
        pts = [(0, 0), (4, 0), (4, 4), (0, 4), (1, 2)]
        self.assertEqual(M.count_py(pts)[1], M.brute(pts))
        self.assertGreater(M.count_py([(0, 0), (1, 1), (2, 2), (5, 0)])[0], 0)

    def test_python_against_brute(self):
        st = M.Stream(SEED, "t")
        for t in range(12):
            pts = M.random_set(st, 8 + t % 4, convex7=(t % 2 == 0))
            self.assertEqual(M.count_py(pts), (0, M.brute(pts)))
            if t % 2 == 0:
                self.assertGreaterEqual(M.brute(pts)[4], 1)

    @unittest.skipIf(shutil.which("gcc") is None, "no gcc")
    def test_c_program(self):
        work = tempfile.mkdtemp()
        try:
            exe = M.build(work)
            self.assertEqual(M.count_c(exe, work, HEPTAGON)[:2], (0, [35, 35, 21, 7, 1]))
            st = M.Stream(SEED, "c")
            for t in range(10):
                pts = M.random_set(st, 30)
                self.assertEqual(M.count_c(exe, work, pts)[:2], M.count_py(pts))
            self.assertGreater(M.count_c(exe, work, [(0, 0), (1, 1), (2, 2), (5, 0)])[0], 0)
            # observation (g)'s mode on a hand-made set: B = (0,0), (2,0); T = (1, 5), (3, 5)
            self.assertEqual(M.c_run(exe, work, "above", [(0, 0), (1, 5), (2, 0), (3, 5)])["above"], [0, 0])
            # (1, -5) is below B's line; (0, 0) is above T's line and (2, 0) on it
            self.assertEqual(M.c_run(exe, work, "above", [(0, 0), (1, -5), (2, 0), (3, 5)])["above"], [1, 2])
            # too large for 128-bit orientations
            with self.assertRaises(Exception):
                M.c_run(exe, work, "count", [(0, 0), (1 << 62, 1 << 62), (2, 5)])
        finally:
            shutil.rmtree(work, ignore_errors=True)


class Run(unittest.TestCase):
    def test_refused(self):
        with self.assertRaises(M.Refused):
            M.run("nothex", results=os.path.join(HERE, "nonexistent-results"))

    def test_test_length(self):
        self.assertLessEqual(len(M.TEST), 600)

    def test_stream(self):
        a, b = M.Stream(SEED, "x"), M.Stream(SEED, "x")
        self.assertEqual([a.below(100) for _ in range(5)], [b.below(100) for _ in range(5)])


if __name__ == "__main__":
    unittest.main()
