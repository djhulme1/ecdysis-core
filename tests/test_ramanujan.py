"""The Ramanujan Machine's two continued fractions (pi/ramanujan.py): the convergents against the nested fractions; each
constant by its two series and against its published digits; the agreement measure and the exact threshold, at and
beside it; the verdict; and a short run end to end.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import math
import os
import tempfile
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pi_ramanujan", os.path.join(HERE, "..", "pi", "ramanujan.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


class Fractions(unittest.TestCase):
    def test_terms_as_the_quote_prints_them(self):
        self.assertEqual([M.b_pi(n) for n in range(4)], [2, 16, 44, 86])                # 2 + 7 n (n + 1)
        self.assertEqual([M.a_pi(n) for n in range(1, 4)], [8, 128, 648])               # 8 n^4
        self.assertEqual([M.b_zeta(n) for n in range(4)], [1, 21, 95, 259])             # 1.1, 3.7, 5.19, 7.37
        self.assertEqual([M.a_zeta(n) for n in range(1, 4)], [-1, -64, -729])           # -n^6

    def test_convergents_equal_the_nested_fractions(self):
        for b, a in ((M.b_pi, M.a_pi), (M.b_zeta, M.a_zeta)):
            kept, prev, last = M.convergents(b, a, 12, keep=range(13))
            for n in range(13):
                with self.subTest(b=b.__name__, n=n):
                    self.assertEqual(Fraction(*kept[n]), M.nested(b, a, n))
            self.assertEqual((prev, last), (kept[11], kept[12]))


class Constants(unittest.TestCase):
    def test_pi_two_ways(self):
        a, b = M.pi_machin(600), M.pi_chudnovsky(600)
        self.assertLess(abs(a - b), 10 ** 20)
        self.assertEqual(M.as_digits(a, 600, 50), M.PI50)

    def test_zeta3_two_ways(self):
        a, b = M.zeta3_apery(400), M.zeta3_az(400)
        self.assertLess(abs(a - b), 10 ** 20)
        self.assertEqual(M.as_digits(a, 400, 50), M.ZETA50)


class Agreement(unittest.TestCase):
    def test_measure(self):
        self.assertAlmostEqual(M.agreement(1, 3, 3333, 4), -math.log10(abs(1 / 3 - 0.3333)), places=9)
        self.assertEqual(M.agreement(1, 4, 2500, 4), math.inf)

    def test_threshold_exactly(self):
        # c = 0.5 to 6 digits; p/q = 0.5 + 10^-4 exactly misses 10^-4 and passes 10^-3
        self.assertFalse(M.within(5001, 10000, 500000, 6, 4))
        self.assertTrue(M.within(5001, 10000, 500000, 6, 3))
        self.assertTrue(M.within(50009, 100000, 500000, 6, 4))

    def test_verdict(self):
        self.assertEqual(sum(M.conditions(True, True).values()), 2)
        self.assertEqual(sum(M.conditions(True, False).values()), 1)


class Run(unittest.TestCase):
    def test_a_short_run(self):
        with tempfile.TemporaryDirectory() as d:
            out, detail = M.run("0" * 64, results=d, digits=700, n_pi=700, n_zeta=420, threshold=600, log=None)
            self.assertEqual(sorted(os.listdir(d)), ["detail.json", "outputs.json"])
        self.assertEqual(tuple(out), M.OUTPUTS)
        self.assertEqual((out["controls"], out["test_passed"]), ("4 of 4", 1))
        self.assertGreater(out["digits_pi_cf"], 620)                 # about 0.903 digits a term
        self.assertGreater(out["digits_zeta_cf"], 640)               # about 1.531


if __name__ == "__main__":
    unittest.main()
