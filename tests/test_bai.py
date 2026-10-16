"""Bai's bound (pi/bai.py): the polynomial helpers, the stationary cubic, the set E, the Laurent recurrence, the deleted
primes, pi and e in integers and the distance to the nearest integer, on inputs other than the paper's triple (the
Zeilberger-Zudilin triple (1, 2, 3), small triples and made-up numbers). The paper's triple is never evaluated here.

Run with: python3 -m unittest tests.test_bai (in the pinned scipy-notebook image)
"""

import importlib.util
import math
import os
import random
import tempfile
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pi_bai", os.path.join(HERE, "..", "pi", "bai.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


class Polynomials(unittest.TestCase):
    def test_helpers(self):
        self.assertEqual(M.pmul([1, 1], [1, -1]), [1, 0, -1])
        self.assertEqual(M.ppow([1, 1], 3), [1, 3, 3, 1])
        self.assertEqual(M.pderiv([5, 0, 3]), [0, 6])
        self.assertEqual(M.pcompose_shift([0, 0, 1], 2), [4, 4, 1])            # (x+2)^2
        self.assertEqual(M.ptrim([1, 2, 0, 0]), [1, 2])

    def test_shifted_h(self):
        H = M.H_shifted()                      # h(z - 5), h(t) = t^5 + 6t^3 + 25t
        for z in (-2, 0, 3, 7):
            t = z - 5
            self.assertEqual(sum(c * z ** i for i, c in enumerate(H)), t ** 5 + 6 * t ** 3 + 25 * t)

    def test_cubic_at_zeilberger_zudilin(self):
        cub = M.stationary_cubic(1, 2, 3)
        self.assertEqual([int(x) for x in reversed(cub)], [2, -125, -500, -625])   # their printed g'/g numerator

    def test_discriminant(self):
        # (y-1)(y-2)(y-3) has discriminant 4
        self.assertEqual(M.cubic_discriminant([-6, 11, -6, 1]), 4)


class TheSetE(unittest.TestCase):
    def test_zeilberger_zudilin(self):
        self.assertEqual(M.E_set(1, 2, 3), [(Fraction(1, 2), Fraction(2, 3))])

    def test_against_a_grid(self):
        for a, b, c in ((3, 4, 6), (4, 5, 8), (2, 4, 5)):
            E = M.E_set(a, b, c)
            for k in range(1, 4000):
                u = Fraction(k, 4000) + Fraction(1, 10 ** 7)
                inside = any(lo <= u < hi for lo, hi in E)
                frac = lambda x: x - math.floor(x)
                want = frac(a * u + Fraction(1, 2)) + 2 * frac(b * u) < frac(c * u)
                self.assertEqual(inside, want, (a, b, c, u))

    def test_deleted_against_fractions(self):
        rng = random.Random(4)
        frac = lambda x: x - math.floor(x)
        for _ in range(300):
            a, b, c = rng.randint(1, 50), rng.randint(1, 50), rng.randint(1, 50)
            p, n = rng.choice([7, 11, 13, 101, 997]), rng.randint(1, 200)
            want = frac(Fraction(a * n, p) + Fraction(1, 2)) + 2 * frac(Fraction(b * n, p)) < frac(Fraction(c * n, p))
            self.assertEqual(M.deleted(p, n, a, b, c), want)


class Recurrence(unittest.TestCase):
    def test_against_direct(self):
        for k, l in ((2, 5), (3, 7), (5, 4)):
            G = M.g_tilde(k, l, 30)
            D = M.g_direct(k, l, 30)
            self.assertEqual([Fraction(x) for x in G], D)
            self.assertEqual(M.g_tilde(k, l, 30, keep_all=False), G[30])

    def test_S_route_at_zeilberger_zudilin(self):
        primes = M.primes_upto(1000)
        for n in (2, 4):
            f = M.form(n, 1, 2, 3, primes)
            self.assertEqual(M.S_route_v(n, 1, 2, 3), abs(f["c0"]) / 2)


class Arithmetic(unittest.TestCase):
    def test_primes_and_lcm(self):
        self.assertEqual(M.primes_upto(30), [2, 3, 5, 7, 11, 13, 17, 19, 23, 29])
        self.assertEqual(M.lcm_upto(10, M.primes_upto(10)), 2520)

    def test_nu(self):
        self.assertEqual(M.nu(Fraction(48, 5), 2), 4)
        self.assertEqual(M.nu(Fraction(3, 250), 5), -3)
        self.assertEqual(M.nu(Fraction(5 ** 37 * 7), 5), 37)

    def test_pi_e(self):
        self.assertEqual(M.pi_digits(1000), M.pi_machin(1000))
        self.assertEqual(str(M.pi_digits(30)), "3141592653589793238462643383279")
        self.assertEqual(str(M.e_digits(30)), "2718281828459045235360287471352")

    def test_distance(self):
        D = 60
        third = 10 ** D // 3
        d_int, err = M.distance(3, third, D)          # 3 * (1/3) is an integer
        self.assertLessEqual(d_int, err)
        d_int, err = M.distance(2, third, D)          # 2/3 is 1/3 from an integer
        self.assertAlmostEqual(d_int / 10 ** D, 1 / 3, places=12)

    def test_forms_machinery_at_zeilberger_zudilin(self):
        primes = M.primes_upto(1000)
        f = M.form(20, 1, 2, 3, primes)
        self.assertEqual(f["V"].denominator, 1)
        self.assertNotEqual(f["V"], 0)
        bad = M.form(20, 1, 2, 3, primes, pole_extra=1)["V"]
        if bad.denominator == 1:
            D = 400
            d_int, err = M.distance(bad.numerator, M.pi_digits(D), D)
            self.assertGreater(d_int, 10 ** (D - 20))        # not a good form: V pi far from an integer


class Source(unittest.TestCase):
    def test_refusals(self):
        with self.assertRaises(M.Refused):
            M.run("xyz")
        with tempfile.TemporaryDirectory() as tmp:
            open(os.path.join(tmp, M.INPUT[0]), "wb").write(b"not the e-print")
            with self.assertRaises(M.Refused):
                M.read_source(os.path.join(tmp, M.INPUT[0]))

    def test_families_as_printed(self):
        fam, counts = M.families()
        self.assertEqual(counts, (186, 557, 742, 371, 928))
        self.assertEqual(len(fam), 2784)

    def test_constants(self):
        self.assertLessEqual(len(M.TEST), 600)
        self.assertEqual(len(set(M.OUTPUTS)), len(M.OUTPUTS))
        self.assertLessEqual(len(M.OUTPUTS), 64)
        self.assertEqual(M.TRIPLE, (1857, 3714, 5570))
        self.assertEqual(M.INPUT[2], 41155)


if __name__ == "__main__":
    unittest.main()
