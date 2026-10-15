"""mm/mfg_reduce.py: the denominators a term really needs, and the rescaling to integers, on schemes written here.

Run with: python3 -m unittest discover -s tests -p test_mfg_reduce.py
"""

import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("mm_mfg_reduce", os.path.join(HERE, "..", "mm", "mfg_reduce.py"))
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)

STRASSEN = """(a11 + a22)*(b11 + b22)*(c11 + c22)
(a21 + a22)*(b11)*(c12 - c22)
(a11)*(b12 - b22)*(c21 + c22)
(a22)*(b21 - b11)*(c11 + c12)
(a11 + a12)*(b22)*(-c11 + c21)
(a21 - a11)*(b11 + b12)*(c22)
(a12 - a22)*(b21 + b22)*(c11)
"""


class Reduce(unittest.TestCase):
    def test_needed_primes(self):
        self.assertEqual(R.needed_primes({0: 3, 1: 6}, {0: 5}, {0: 1}, 15), (set(), {3, 5}))
        self.assertEqual(R.needed_primes({0: 3, 1: 6}, {0: 1}, {0: 1}, 15), ({5}, {3, 5}))
        self.assertEqual(R.needed_primes({0: 3}, {0: 3}, {0: 1}, 27), ({3}, {3}))
        self.assertEqual(R.needed_primes({0: 3}, {0: 3}, {0: 3}, 27), (set(), {3}))

    def test_integral_strassen(self):
        text = STRASSEN.replace("(a11 + a22)*(b11 + b22)*(c11 + c22)", "(3*a11 + 3*a22)*(b11 + b22)*(c11 + c22)/3")
        text = text.replace("(a11 + a12)*(b22)*(-c11 + c21)", "-((5*a11 + 5*a12)*(b22)*(c11 - c21))/5")
        row = R.examine(text, (2, 2, 2))
        self.assertEqual((row["products"], row["written"], row["needed"]), (7, [3, 5], []))
        self.assertEqual((row["wrong_over_Q_as_written"], row["wrong_over_Z_rescaled"], row["largest_integer"]),
                         (0, 0, 1))

    def test_kept_denominator(self):
        text = STRASSEN.replace("(a11 + a22)*(b11 + b22)*(c11 + c22)", "(a11 + a22)*(b11 + b22)*(c11 + c22)/3")
        row = R.examine(text, (2, 2, 2))
        self.assertEqual(row["needed"], [3])
        self.assertNotIn("wrong_over_Z_rescaled", row)
        self.assertIsNone(R.integral(list(R.terms(text, (2, 2, 2)))))


if __name__ == "__main__":
    unittest.main()
