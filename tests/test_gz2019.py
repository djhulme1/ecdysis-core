"""Guo & Zudilin's q-microscope (pi/gz2019.py): primes and the character; Machin's and Gauss-Legendre's π against known
digits; the power-series routines on identities other than the paper's; the binomial recurrence; the exact modular
reduction; the planted variant's machinery; and the root-of-unity series over F_l (valuations, inverses, negative
powers, the roots' orders). Neither of the paper's congruences nor its q-analogue is evaluated here.

Run with: python3 -m unittest tests.test_gz2019
"""

import importlib.util
import math
import os
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pi_gz2019", os.path.join(HERE, "..", "pi", "gz2019.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

PI50 = 314159265358979323846264338327950288419716939937510


class Basics(unittest.TestCase):
    def test_primes_and_chi(self):
        self.assertEqual(M.primes_upto(30), [2, 3, 5, 7, 11, 13, 17, 19, 23, 29])
        self.assertEqual(len(M.primes_upto(10000)), 1229)
        self.assertEqual([M.chi3(p) for p in (5, 7, 11, 13)], [-1, 1, -1, 1])

    def test_pi(self):
        self.assertEqual(M.machin_pi(50), PI50)
        self.assertLessEqual(abs(M.gauss_legendre_pi(50) - PI50), 1)

    def test_series_routines(self):
        c = [1] + [0] * 20
        M.mul1m(c, 3)
        M.div1m(c, 3)
        self.assertEqual(c, [1] + [0] * 20)
        # 1/(1 - q) is all ones; (1 - q)^2 is 1 - 2q + q^2
        c = [1] + [0] * 10
        M.div1m(c, 1)
        self.assertEqual(c, [1] * 11)
        c = [1] + [0] * 5
        M.mul1m(c, 1)
        M.mul1m(c, 1)
        self.assertEqual(c, [1, -2, 1, 0, 0, 0])
        # partitions into odd parts equal partitions into distinct parts (Euler), to q^60
        odd = [1] + [0] * 60
        for m in range(1, 61, 2):
            M.div1m(odd, m)
        distinct = [1] + [0] * 60
        for m in range(1, 61):
            for i in range(60, m - 1, -1):
                distinct[i] += distinct[i - m]
        self.assertEqual(odd, distinct)

    def test_recurrence_and_exact(self):
        t = Fraction(1)
        for n in range(1, 12):
            t = t * (4 * n) * (4 * n - 1) * (4 * n - 2) * (4 * n - 3) / (2304 * n ** 4)
            self.assertEqual(t, M.a_exact(n))
        self.assertEqual(M.a_exact(1), Fraction(6 * 4, 2304))

    def test_variant_machinery(self):
        # the planted variant against a direct exact sum, for p = 7
        p = 7
        P3 = p ** 3
        s = sum(M.a_exact(n) * (8 * n + 3) for n in range(p))
        h = sum(M.a_exact(n) * (8 * n + 3) for n in range((p - 1) // 2 + 1))
        full, half = M.s_mod_variant(p)
        self.assertEqual(full, s.numerator * pow(s.denominator, -1, P3) % P3)
        self.assertEqual(half, h.numerator * pow(h.denominator, -1, P3) % P3)


class Roots(unittest.TestCase):
    def setUp(self):
        self.ell = M.primes_1_mod(5, 1)[0]
        self.z = M.primitive_root_of_order(5, self.ell)

    def test_primes_one_mod(self):
        ls = M.primes_1_mod(11, 3)
        self.assertEqual(len(ls), 3)
        self.assertTrue(all(l % 11 == 1 and l > 2 ** 61 and M.is_prime(l) for l in ls))
        self.assertEqual(ls, sorted(ls))

    def test_root_order(self):
        self.assertEqual(pow(self.z, 5, self.ell), 1)
        self.assertNotEqual(self.z, 1)
        z35 = M.primitive_root_of_order(35, M.primes_1_mod(35, 1)[0])
        ell = M.primes_1_mod(35, 1)[0]
        self.assertTrue(all(pow(z35, k, ell) != 1 for k in (5, 7)))

    def test_valuations(self):
        one = lambda m: M.factor_ser(self.z, m, -1, self.ell)
        self.assertEqual(one(5).v, 1)
        self.assertEqual(one(10).v, 1)
        self.assertEqual(one(6).v, 0)
        self.assertEqual((one(5) / one(10)).v, 0)
        plus = M.factor_ser(self.z, 5, +1, self.ell)
        self.assertEqual(plus.v, 0)   # 1 + z^5 = 2

    def test_inverse_and_powers(self):
        ell = self.ell
        a = M.factor_ser(self.z, 3, -1, ell)
        prod = a * a.inv()
        self.assertEqual((prod.v, prod.u), (0, [1] + [0] * (M.PREC - 1)))
        p = M.power_ser(self.z, -3, ell) * M.power_ser(self.z, 3, ell)
        self.assertEqual((p.v, p.u), (0, [1] + [0] * (M.PREC - 1)))
        self.assertEqual(M.binom_mod(-1, 3, ell), (-1) % ell)
        self.assertEqual(M.binom_mod(5, 2, ell), 10)

    def test_expansion_matches_direct_values(self):
        # (z + e)^m at e = 0 is z^m; the first-order coefficient is m z^(m-1)
        ell, z = self.ell, self.z
        s = M.power_ser(z, 7, ell)
        self.assertEqual(s.u[0], pow(z, 7, ell))
        self.assertEqual(s.u[1], 7 * pow(z, 6, ell) % ell)

    def test_collect(self):
        ell = self.ell
        a = M.Ser(0, [1, 2, 3, 0, 0, 0], ell)
        b = M.Ser(0, [ell - 1, ell - 2, 0, 0, 0, 0], ell)
        coeffs, known = M.collect([a, b], ell)
        self.assertEqual(coeffs, {2: 3})
        self.assertEqual(M.order_of_vanishing(coeffs, known), 2)


class Run(unittest.TestCase):
    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("nothex", results=os.path.join(HERE, "nonexistent-results"))

    def test_test_length(self):
        self.assertLessEqual(len(M.TEST), 600)


if __name__ == "__main__":
    unittest.main()
