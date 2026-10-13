"""Bäsel & Baillie's tiny numbers (sinc/tiny.py): the closed-form sum against exact sums, the first n beyond small
a_0, the exact t at a_0 = 2 against the paper's printed fraction, the rounding to 41 significant digits, the unit
distance between mantissas, and, with the e-print at inputs/ (or SINC_INPUTS), its Table 1 read whole.

Run with: python3 -m unittest tests.test_tiny
"""

import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("sinc_tiny", os.path.join(HERE, "..", "sinc", "tiny.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)
INPUTS = os.environ.get("SINC_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = os.path.isfile(os.path.join(INPUTS, M.INPUT[0]))


class Numbers(unittest.TestCase):
    def setUp(self):
        M.mpmath.mp.dps = M.DPS

    def test_closed_form_sum(self):
        for n in (1, 2, 7, 50):
            exact = sum(Fraction(1, 2 * k - 1) for k in range(1, n + 1))
            self.assertLess(abs(M.s_closed(n) - M.mpmath.mpf(exact.numerator) / exact.denominator),
                            M.mpmath.mpf(10) ** -100)

    def test_first_n(self):
        self.assertEqual([M.n0_of(a) for a in (1, 2, 3)], [2, 8, 57])

    def test_exact_t(self):
        self.assertEqual(M.exact_t(1), (2, Fraction(1, 12)))
        self.assertEqual(M.exact_t(2), (8, M.A2_FRACTION))

    def test_rounding_and_units(self):
        lnt = M.mpmath.log(M.mpmath.mpf(1) / 12)
        self.assertEqual(M.scientific(lnt), ("8.3333333333333333333333333333333333333333", -2))
        self.assertEqual(M.scientific(M.mpmath.log(M.mpmath.mpf("9.99999999999999999999999999999999999999996e-5"))),
                         ("1.0000000000000000000000000000000000000000", -4))
        self.assertEqual(M.units_apart("1.0001", "1.0003"), 2)

    def test_refuses_another_file(self):
        d = tempfile.mkdtemp()
        try:
            with open(os.path.join(d, M.INPUT[0]), "wb") as fh:
                fh.write(b"not the e-print")
            with self.assertRaises(M.Refused):
                M.read_table(d)
        finally:
            shutil.rmtree(d)


@unittest.skipUnless(HAVE, "the e-print is not at inputs/")
class Table(unittest.TestCase):
    def test_read_whole(self):
        rows = M.read_table(INPUTS)
        self.assertEqual(sorted(rows), list(range(1, 11)))
        self.assertEqual(rows[10], (68100151, M.MANTISSA, M.EXPONENT))


if __name__ == "__main__":
    unittest.main()
