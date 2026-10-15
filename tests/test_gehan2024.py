"""Jiang et al. 2024 (itp/gehan2024.py): the weighted log-rank tests on samples whose answers are worked by hand,
against the program's log-rank and statsmodels' survdiff on seed-drawn samples, and the row rules on rows written here.
No workbook is read.

Run with (statsmodels needed, the scipy-notebook image): python3 -m unittest discover -s tests -p test_gehan2024.py
"""

import importlib.util
import math
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_gehan2024", os.path.join(HERE, "..", "itp", "gehan2024.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

A = [(1, True), (2, True)]
B = [(3, True), (4, True)]


def row(**kw):
    base = {"population": "UM-HET3", "cohort": "C2011", "site": "UM", "sex": "m", "id": "x", "group": "Met",
            "dose": "1000", "age_initiation": "9", "status": "dead", "dead": "1", "age": "800"}
    base.update(kw)
    return base


class Tests(unittest.TestCase):
    def test_hand_example(self):
        p, oe = M.weighted_test([(A, B)], "fh1")
        self.assertAlmostEqual(oe, -1.0, places=12)
        self.assertAlmostEqual(p, math.erfc(math.sqrt(1 / 0.375 / 2)), places=12)
        p0, oe0 = M.weighted_test([(A, B)], "logrank")
        self.assertAlmostEqual(oe0, -0.5 - 2 / 3, places=12)
        self.assertAlmostEqual(p0, math.erfc(math.sqrt((7 / 6) ** 2 / (0.25 + 2 / 9) / 2)), places=12)
        self.assertAlmostEqual(p0, M.logrank([(A, B)]), places=12)
        pg, oeg = M.weighted_test([(A, B)], "gb")
        self.assertAlmostEqual(oeg, -4.0, places=12)
        self.assertAlmostEqual(pg, math.erfc(math.sqrt(16 / 6 / 2)), places=12)

    def test_censoring_and_symmetry(self):
        a = [(5, True), (7, False), (9, True), (9, True), (12, False)]
        b = [(6, True), (9, True), (11, True), (13, True), (14, False)]
        for w in ("logrank", "fh1", "gb", "pp"):
            p1, oe1 = M.weighted_test([(a, b)], w)
            p2, oe2 = M.weighted_test([(b, a)], w)
            self.assertAlmostEqual(p1, p2, places=12)
            self.assertAlmostEqual(oe1, -oe2, places=12)
        self.assertEqual(M.weighted_test([(a, a)], "fh1")[0], 1.0)

    def test_against_statsmodels(self):
        for k in range(3):
            strata = M.synthetic("cd" * 32, k)
            self.assertEqual(len(strata), 3)
            self.assertAlmostEqual(M.weighted_test(strata, "logrank")[0], M.logrank(strata), places=12)
            self.assertAlmostEqual(M.weighted_test(strata, "logrank")[0], M.statsmodels_p(strata, None), places=9)
            self.assertAlmostEqual(M.weighted_test(strata, "fh1")[0], M.statsmodels_p(strata, "fh", fh_p=1), places=9)
            self.assertAlmostEqual(M.weighted_test(strata, "gb")[0], M.statsmodels_p(strata, "gb"), places=9)

    def test_rows(self):
        mice = M.mice_from_rows([row(), row(status="removed", dead="0", age="400.0"), row(group="Control", dose="0",
                                                                                        age_initiation=None)], "C2011")
        self.assertEqual(mice[("Met", "UM", "m")], [(800, True), (400, False)])
        self.assertEqual(mice[("Control", "UM", "m")], [(800, True)])
        self.assertEqual(len(M.strata_of(mice, "Met", "m")), 3)
        for bad in (row(cohort="C2012"), row(status="dead", dead="0"), row(group="Nope"), row(dose="100"),
                    row(age="800.5"), row(site="XX"), row(population="B6")):
            with self.assertRaises(M.Refused):
                M.mice_from_rows([bad], "C2011")

    def test_helpers(self):
        self.assertTrue(M.rounds_to(0.034449, 0.0344, 4))
        self.assertFalse(M.rounds_to(0.03455, 0.0344, 4))
        self.assertEqual(M.dead_median([(5, True), (7, False), (9, True)]), 7)
        a, b = M.Stream("ab" * 32, "t"), M.Stream("ab" * 32, "t")
        self.assertEqual(a.ints(9, 0, 4), b.ints(9, 0, 4))

    def test_machinery(self):
        self.assertLessEqual(len(M.TEST), 600)
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 64)
        self.assertEqual(set(M.INPUTS), {"C2005", "C2007", "C2011", "C2015", "C2017"})
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


if __name__ == "__main__":
    unittest.main()
