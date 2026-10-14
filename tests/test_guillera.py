"""Guillera's WZ pairs and series (pi/guillera.py): the reader on e-prints built here and its refusals; binomials,
rising factorials and rounding; pi by both series, the AGM, e^x and phi(e^-pi)^2 at 60 digits; the summation and its
tail check on series whose sums are known; the WZ check on a pair known to satisfy the equation and on one known not
to; the pairs and the eight summands at points worked by hand from the printed formulas; the evaluation of rule 5 on a
known series; the outputs and the seed refused. No WZ equation of the paper's pairs, none of its sums, no H(n, 0) and
no Gamma form against a binomial one is computed here, and the paper's source is not read.

Run with: python3 -m unittest discover -s tests -p test_guillera.py
"""

import gzip
import importlib.util
import math
import os
import tempfile
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pi_guillera", os.path.join(HERE, "..", "pi", "guillera.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

D = 60


def eprint(formulas):
    """A gzipped TeX file holding the given formulas, broken over lines, with extra spaces and a comment."""
    body = "\n% a comment that is not read\n".join(f.replace(" ", "\n   ", 3) for f in formulas)
    return gzip.compress(("\\documentclass{amsart}\n" + body + "\n\\enddocument\n").encode("utf-8"))


def float_agm(a, b):
    for _ in range(60):
        a, b = (a + b) / 2, math.sqrt(a * b)
    return a


class Reading(unittest.TestCase):
    def test_source(self):
        M.check_source(M.tex_of(eprint(M.FORMULAS)))
        with self.assertRaises(M.Refused):
            M.check_source(M.tex_of(eprint(M.FORMULAS[1:])))
        with self.assertRaises(M.Refused):
            M.check_source(M.tex_of(eprint([f.replace("20n+2k+3", "20n+2k+4") for f in M.FORMULAS])))

    def test_not_gzip(self):
        with self.assertRaises(M.Refused):
            M.tex_of(b"\\documentclass{amsart}")
        with self.assertRaises(M.Refused):
            M.tex_of(gzip.compress(b"caf\xe9"))

    def test_hash_refused(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, M.INPUT[0])
            with open(path, "wb") as fh:
                fh.write(eprint(M.FORMULAS))
            with self.assertRaises(M.Refused):
                M.read_bytes(path, M.INPUT[1])


class Arithmetic(unittest.TestCase):
    def test_binomials(self):
        self.assertEqual(M.C(6, 3), 20)
        for a, b in ((3, 4), (3, -1), (-2, 0)):
            with self.assertRaises(ValueError):
                M.C(a, b)
        self.assertEqual((M.C0(3, 4), M.C0(3, -1), M.C0(4, 2)), (0, 0, 6))

    def test_rising_factorial(self):
        self.assertEqual(M.HALF(3), Fraction(15, 8))
        self.assertEqual(M.QUARTER(2), Fraction(5, 16))
        self.assertEqual(M.Poch(Fraction(3, 4))(0), 1)
        self.assertEqual(M.Poch(2)(4), 2 * 3 * 4 * 5)

    def test_rounding(self):
        self.assertEqual(M.fixed(Fraction(1, 3), 10 ** 4), 3333)
        self.assertEqual(M.fixed(Fraction(2, 3), 10 ** 4), 6667)
        self.assertEqual(M.fixed(Fraction(-1, 3), 10 ** 4), -3333)
        self.assertEqual(M.fixed(Fraction(-2, 3), 10 ** 4), -6667)
        self.assertEqual(M.nearest(7, 2), 4)
        self.assertEqual(M.as_decimal(31415, 4, 3), "3.141")
        self.assertEqual(M.as_decimal(5, 3), "0.005")

    def test_constants(self):
        a, b = M.pi_machin(D), M.pi_chudnovsky(D)
        self.assertLess(abs(a - b), 10 ** 3)
        self.assertEqual(M.as_decimal(a, D, 50), M.PI50)
        scale = 10 ** 15
        g = M.agm(scale, math.isqrt(2 * scale * scale)) / scale
        self.assertAlmostEqual(g, float_agm(1.0, math.sqrt(2.0)), places=13)
        self.assertAlmostEqual(M.exp_fixed(scale, scale) / scale, math.e, places=13)
        self.assertAlmostEqual(M.exp_fixed(3 * scale, scale) / scale, math.exp(3), places=12)
        k = M.constants(D)
        self.assertLess(abs(k["theta_squared"] - k["values"]["sqrt(pi)/Gamma(3/4)^2"]), 10 ** 3)
        self.assertAlmostEqual(k["values"]["8/pi"] / 10 ** D, 8 / math.pi, places=14)
        self.assertAlmostEqual(k["values"]["32/pi^2"] / 10 ** D, 32 / math.pi ** 2, places=14)
        gamma34 = math.gamma(0.75)
        self.assertAlmostEqual(k["values"]["sqrt(pi)/Gamma(3/4)^2"] / 10 ** D, math.sqrt(math.pi) / gamma34 ** 2,
                               places=13)
        self.assertAlmostEqual(k["values"]["pi/Gamma(3/4)^4"] / 10 ** D, math.pi / gamma34 ** 4, places=13)
        self.assertTrue(all(SUM[3] in k["values"] for SUM in M.SUMS.values()))


class Summation(unittest.TestCase):
    def test_known_sums(self):
        scale = 10 ** D
        total, used, last, worst = M.sum_series(lambda n: Fraction(M.C(2 * n, n), 16 ** n), scale)
        want = M.nearest(2 * scale * scale, math.isqrt(3 * scale * scale))
        self.assertLessEqual(abs(total - want), used + 10)
        self.assertLess(worst, Fraction(1, 2))
        self.assertLess(abs(last), Fraction(1, scale * 10 ** 5))
        total, used, last, worst = M.sum_series(lambda n: Fraction(1, 3 ** n), scale, tail=20)
        self.assertLessEqual(abs(total - 3 * scale // 2), used)
        self.assertEqual(worst, Fraction(1, 3))
        self.assertEqual(Fraction(1, 3 ** (used - 1)), last)

    def test_evaluate(self):
        saved = M.SUMS
        k = M.constants(D)
        scale = k["scale"]
        k["values"]["2/sqrt 3"] = M.nearest(2 * scale * scale, math.isqrt(3 * scale * scale))
        k["values"]["wrong"] = k["values"]["2/sqrt 3"] + 5 * 10 ** 14
        M.SUMS = {"x": (lambda n: Fraction(M.C(2 * n, n), 16 ** n), Fraction(1), False, "2/sqrt 3"),
                  "y": (lambda n: Fraction(M.C(2 * n, n), 16 ** n), Fraction(1), False, "wrong"),
                  "z": (lambda n: Fraction(M.C(2 * n, n), 16 ** n), Fraction(1, 2), True, "2/sqrt 3")}
        try:
            x = M.evaluate("x", k, digits=D, threshold=50)
            y = M.evaluate("y", k, digits=D, threshold=50)
            z = M.evaluate("z", k, digits=D, threshold=50)
            loose = M.evaluate("y", k, digits=D, threshold=40)
        finally:
            M.SUMS = saved
        self.assertTrue(x["within"] and x["tail_ok"])
        self.assertEqual(x["digits"], D - 10)
        self.assertFalse(y["within"])
        self.assertEqual(y["digits"], D - 15)
        self.assertTrue(loose["within"])
        self.assertFalse(z["within"])                       # (sqrt 2/2)(2/sqrt 3) is not 2/sqrt 3
        self.assertTrue(z["sum"].startswith("0.8164965809"))  # sqrt(2/3)


class Pairs(unittest.TestCase):
    def test_hand_values(self):
        self.assertEqual(M.g1(0, 0), 3)
        self.assertEqual(M.f1(1, 0), Fraction(-1, 2))       # 64 (-1) / (3 2^10) * C(2,1)^2 C(4,2) = -1/2
        self.assertEqual(M.g2(0, 0), 3)
        self.assertEqual(M.f2(1, 0), Fraction(1, 4))        # 512 / (3 2^16) * C(2,1)^4 C(4,2) = 1/4
        self.assertEqual(M.f1(0, 0), 0)
        self.assertEqual(M.gamma_g1(0, 0), 3)
        self.assertEqual(M.gamma_f2(0, 0), 0)
        with self.assertRaises(ValueError):
            M.g1(1, 3)                                       # k > 2n: outside the binomial forms

    def test_wz_check(self):
        bad, checked = M.wz_failures(M.control_f, M.control_g, 10, lambda n: range(0, n + 1))
        self.assertEqual((bad, checked), ([], sum(n + 1 for n in range(1, 11))))
        bad, _ = M.wz_failures(M.control_f, lambda n, k: 2 * M.control_g(n, k), 10, lambda n: range(0, n + 1))
        self.assertTrue(bad)
        self.assertEqual(sum(len(M.paper_ks(n)) for n in range(1, M.N_WZ + 1)), 1640)

    def test_summands_by_hand(self):
        firsts = [M.s1a(0), M.s1b(0), M.s1c(0), M.s1d(0), M.s2a(0), M.s2b(0), M.s2c(0), M.s2d(0)]
        self.assertEqual(firsts, [3, 5, 7, Fraction(11, 5), 3, 13, 11, Fraction(279, 25)])
        self.assertEqual(M.s1a(1), Fraction(-69, 128))       # -C(4,2) C(2,1)^2 23 / 2^10
        self.assertEqual(M.s1b(1), Fraction(47, 512))        # C(2,1)^3 47 / 2^12
        self.assertEqual(M.s1c(1), Fraction(-47, 128))       # -(1/2)(5/16) / ((1/4) 16) * 47/5
        self.assertEqual(M.s2a(1), Fraction(471, 2048))      # C(4,2) C(2,1)^4 157 / 2^16
        self.assertEqual(M.s2b(1), Fraction(-1013, 32768))   # -C(2,1)^5 1013 / 2^20
        self.assertEqual(list(M.SUMS), list(M.LABELS))


class Verdict(unittest.TestCase):
    def test_conditions(self):
        sums = [{"label": lab, "printed": "v", "within": lab != "2c"} for lab in M.LABELS]
        cond = M.conditions(([], 1640), ([(3, 1)], 1640), sums)
        self.assertEqual((len(cond), sum(cond.values())), (10, 8))

    def test_listing(self):
        self.assertEqual(M.listing([]), "none")
        self.assertEqual(M.listing([(1, 0), (2, 3)]), "(1, 0), (2, 3)")
        self.assertEqual(M.listing(list(range(9)), 3), "0, 1, 2 and 6 more")

    def test_outputs_named(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


if __name__ == "__main__":
    unittest.main()
