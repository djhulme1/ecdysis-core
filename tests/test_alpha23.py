"""The googol-th digit of alpha_{2,3}: the head's terms; the extraction against direct summation at every position up
to 400 and at the edges where terms enter the head; the value against its first terms in floating point; a carry
that cannot be ruled out stops the run; the seed's positions; the googol's digits as section 4 prints them; and the
whole run, its controls included.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import os
import tempfile
import unittest
from fractions import Fraction
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pi_alpha23", os.path.join(HERE, "..", "pi", "alpha23.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "0" * 63 + "7"


class Extraction(unittest.TestCase):
    def test_head_terms(self):
        self.assertEqual(M.head_terms(26), [(1, 3), (2, 9)])
        self.assertEqual(M.head_terms(27), [(1, 3), (2, 9), (3, 27)])
        self.assertEqual(M.head_terms(2), [])

    def test_against_direct_summation(self):
        N = 5000
        pre = M.prefix(N)
        for n in list(range(1, 401)) + [726, 727, 728, 729, 730, 2186, 2187, 2188, 4000]:
            with self.subTest(n=n):
                self.assertEqual(M.digits_from(n), M.window_of(pre, N, n))

    def test_the_value(self):
        approx = 1 / 24 + 1 / (9 * 2 ** 9) + 1 / (27 * 2 ** 27)
        self.assertAlmostEqual(M.digits_from(1) / 2 ** 40, approx, places=11)
        self.assertEqual(M.digits_from(1, width=8), 0b00001010)                 # 1/24 = 0.000010101...

    def test_a_possible_carry_stops_the_run(self):
        all_ones = Fraction(2 ** 128 - 1, 2 ** 128)
        with mock.patch.object(M, "frac_head", lambda d, **kw: (all_ones, 500, 1)):
            with self.assertRaises(M.Uncertain):
                M.digits_from(5)

    def test_positions_are_the_seeds(self):
        p = M.positions(SEED)
        self.assertEqual((len(p), len(set(p))), (16, 16))
        self.assertTrue(all(1 <= x <= 2 ** 20 for x in p))
        self.assertEqual(p, M.positions(SEED))
        self.assertNotEqual(p, M.positions("f" * 64))


class Googol(unittest.TestCase):
    def test_the_printed_digits(self):
        g = M.digits_from(M.GOOGOL)
        self.assertEqual(M.hexd(g), "2205896E7B")                               # Bailey and Crandall, section 4
        self.assertEqual(g >> 39, 0)
        _, tail, terms = M.frac_head(M.GOOGOL - 1)
        self.assertEqual(terms, 209)
        self.assertGreater(tail, 5 * 10 ** 99)

    def test_the_run(self):
        with tempfile.TemporaryDirectory() as d:
            out, detail = M.run(SEED, results=d)
        self.assertEqual(len(out), 10)
        self.assertEqual((out["googol_bit"], out["printed_match"], out["test_passed"]), (0, 1, 1))
        self.assertEqual((out["low_agree"], out["controls"]), ("28/28", "3/3"))
        self.assertEqual(out["next_hex10"], "440B12DCF7")


if __name__ == "__main__":
    unittest.main()
