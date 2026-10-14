"""Zeilberger and Zudilin's bound on the irrationality measure of pi (pi/zz.py): the reading of the e-print (its hash,
its gzip, comments and whitespace, each printed formula refused when altered or commented out); the exact polynomial
helpers, Miller's recurrence, the Taylor shift and Gaussian powers on hand values; primes, P_n and lcm; the forms at
n = 0 by hand and the partial fractions at n = 1; the exact and modular Taylor coefficients agreeing; the algebra's
characteristic polynomial, Richardson's formula, Gauss-Legendre, Bernoulli and digamma on known answers; the verdict
at and beside each condition; the seed refused; and, with the e-print at inputs/ (or ZZ_INPUTS), that its source holds
every printed formula as read, which computes none of the quantities the test is about.

Run with: python3 -m unittest discover -s tests -p test_zz.py
"""

import decimal
import gzip
import hashlib
import importlib.util
import math
import os
import tempfile
import unittest
from decimal import Decimal
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pi_zz", os.path.join(HERE, "..", "pi", "zz.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

INPUTS = os.environ.get("ZZ_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = all(os.path.isfile(os.path.join(INPUTS, name)) for name, _ in M.INPUTS.values())


def setUpModule():
    decimal.getcontext().prec = M.PRECISION


def fake_tex():
    return "\n".join(M.PRINTED_TEX) + "\n"


class Reading(unittest.TestCase):
    def test_hash_refused(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.gz")
            with open(path, "wb") as fh:
                fh.write(b"not the e-print")
            with self.assertRaises(M.Refused):
                M.read_bytes(path, M.INPUTS["eprint"][1])
            self.assertEqual(M.read_bytes(path, hashlib.sha256(b"not the e-print").hexdigest()), b"not the e-print")

    def test_not_gzip_refused(self):
        with self.assertRaises(M.Refused):
            M.tex_of(b"plain bytes")
        self.assertEqual(M.tex_of(gzip.compress("abé".encode("utf-8"))), "abé")

    def test_flatten(self):
        self.assertEqual(M.flatten("a  b % gone\n c\\% kept"), "a b c\\% kept")

    def test_source_held_and_refused(self):
        M.check_source(fake_tex())
        for k in (0, 5, len(M.PRINTED_TEX) - 1):
            s = M.PRINTED_TEX[k]
            with self.assertRaises(M.Refused):
                M.check_source(fake_tex().replace(s, s.replace("2", "3", 1) if "2" in s else s + "x"))
            with self.assertRaises(M.Refused):
                M.check_source(fake_tex().replace(s, "%" + s))

    @unittest.skipUnless(HAVE, "the e-print is not at inputs/")
    def test_real_eprint_as_read(self):
        name, sha = M.INPUTS["eprint"]
        raw = M.read_bytes(os.path.join(INPUTS, name), sha)
        M.check_source(M.tex_of(raw))


class Polynomials(unittest.TestCase):
    def test_h_and_w(self):
        # x^5 + 6x^3 + 25x at x = t - 5, by hand
        self.assertEqual(M.H, [-4000, 3600, -1340, 256, -25, 1])
        # y (y^2+6y+25)^2 at y = 25 + u is (25 + u)(u^2 + 56u + 800)^2
        self.assertEqual(M.W_U, M.pmul([25, 1], M.ppow([800, 56, 1], 2)))
        self.assertEqual(M.W_U[0], 25 * 800 ** 2)

    def test_miller_matches_multiplication(self):
        for h in (M.H, M.W_U, [3, -1, 2]):
            for m in (0, 1, 2, 5):
                direct = M.ppow(h, m)
                self.assertEqual(M.miller_power(h, m, len(direct) + 3), direct + [0, 0, 0])
        with self.assertRaises(ValueError):
            M.miller_power([0, 1], 3, 4)

    def test_compose_and_expand(self):
        self.assertEqual(M.trim(M.compose_shift([0, 0, 1], 2)), [4, 4, 1])  # (t + 2)^2
        # 3 + 2 (y - 1) + (y - 1)^2 = y^2 + 2
        self.assertEqual(M.expand_shifted([3, 2, 1], 1), [2, 0, 1])
        self.assertEqual(M.expand_shifted([], 5), [])

    def test_gaussian_powers(self):
        self.assertEqual(M.gpow_imag((4, 2), 3), [2, 16, 88])               # 4+2i, 12+16i, 16+88i
        self.assertEqual(M.gpow_imag((-1, 2), 2), [2, -4])                  # -1+2i, -3-4i


class Primes(unittest.TestCase):
    def test_sieve_lcm_valuation(self):
        self.assertEqual(M.primes_upto(30), [2, 3, 5, 7, 11, 13, 17, 19, 23, 29])
        self.assertEqual(M.lcm_upto(10, M.primes_upto(10)), 2520)
        self.assertEqual(M.lcm_upto(0, M.primes_upto(10)), 1)
        self.assertEqual(M.v_p(-48, 2), 4)
        self.assertEqual(M.v_p(7, 5), 0)

    def test_P_n(self):
        ps = M.primes_upto(400)
        for n in (0, 1, 2, 3):
            self.assertEqual(M.P_set(n, ps), [])
        self.assertEqual(M.P_set(4, ps), [7])
        self.assertEqual(M.P_set(10, ps), [17, 19])                          # 10/17 = 0.588, 10/19 = 0.526
        self.assertFalse(M.in_P(10, 7))                                      # {10/7} = 3/7 < 1/2
        self.assertTrue(M.in_P(4, 7))
        self.assertFalse(M.in_P(25, 7))                                      # {25/7} = 4/7, but 7^2 < 75


class Forms(unittest.TestCase):
    def test_n0_by_hand(self):
        ps = M.primes_upto(20)
        f = M.forms(0, ps)
        self.assertEqual(f["a"], 0)
        self.assertEqual(f["b"], Fraction(1, 4))                             # I_0 = pi/4
        ap, bp, L, e = M.scaled_forms(0, f["a"], f["b"], ps)
        self.assertEqual((ap, bp, L, e), (0, 1, 1, 2))

    def test_partial_fractions_n1(self):
        ps = M.primes_upto(20)
        n = 1
        f = M.forms(n, ps)
        for x in (Fraction(1, 3), Fraction(-7, 2), Fraction(2)):
            R = 5 * x ** 2 * (x ** 4 + 6 * x ** 2 + 25) ** 2 / ((5 + x) ** 4 * (5 - x) ** 4)
            P = sum(pk * x ** (2 * k) for k, pk in enumerate(f["p"]))
            parts = sum(M.A_of(f["Y"], n, j) * (1 / (5 + x) ** (j + 1) + 1 / (5 - x) ** (j + 1)) for j in range(4))
            self.assertEqual(R, P + parts)
        self.assertEqual(len(f["p"]), 2)                                     # P of degree 4n - 2 = 2 in x

    def test_n1_against_quadrature(self):
        f = M.forms(1, M.primes_upto(20))
        with decimal.localcontext() as ctx:
            ctx.prec = 60
            exact = float(M.to_dec(f["a"], 60) + M.to_dec(f["b"], 60) * M.machin_pi(60))
        q1, q2, im1, im2 = M.quad_forms(1, 64)
        self.assertAlmostEqual(q1 / exact, 1, places=10)
        self.assertAlmostEqual(q2 / exact, 1, places=10)
        self.assertLess(max(im1, im2), 1e-12)

    def test_exact_and_modular_agree(self):
        ps = M.primes_upto(50)
        n = 2
        f = M.forms(n, ps)
        _, _, _, residues = M.lemma_2(n, [7, 11])                           # primes outside P_2: only the agreement
        self.assertTrue(residues)
        for (p, j), x in residues.items():
            self.assertEqual(x, f["Y"][3 * n - j] * pow(10, 4 * n - 1, p) % p)


class Algebra(unittest.TestCase):
    def test_mult_matrix_charpoly(self):
        mod = [-2, 0, 0, 1]                                                  # y^3 - 2
        self.assertEqual(M.charpoly3(M.mult_matrix([0, 1], mod)), [-2, 0, 0, 1])
        self.assertEqual(M.charpoly3(M.mult_matrix([0, 0, 1], mod)), [-4, 0, 0, 1])
        m = [[Fraction(2), 1, 0], [0, 1, 0], [1, 0, 3]]
        inv = M.mat_inv(m)
        self.assertEqual(M.mat_mul(m, inv), [[1, 0, 0], [0, 1, 0], [0, 0, 1]])

    def test_discriminant_and_bisection(self):
        self.assertEqual(M.discriminant(0, -1, 0, 1), 4)                    # x^3 - x: three real zeros
        self.assertEqual(M.discriminant(0, 1, 0, 1), -4)                    # x^3 + x: one real zero
        r = M.real_root_bisect([Decimal(-2), Decimal(0), Decimal(1)], Decimal(1), Decimal(2), 300)
        self.assertLess(abs(r - Decimal(2).sqrt()), Decimal(10) ** -70)


class Numerics(unittest.TestCase):
    def test_richardson_exact(self):
        seq = {k: 4 - Fraction(2, k + 1) for k in range(1, 200)}
        for order in (1, 2, 4):
            want = 4 - Fraction(2, math.prod(range(146, 146 + order + 1)))
            self.assertEqual(M.richardson(seq, 145, order), want)

    def test_gauss_legendre(self):
        xs, ws = M.gauss_legendre(20)
        self.assertAlmostEqual(sum(w * x ** 10 for x, w in zip(xs, ws)), 2 / 11, places=14)
        self.assertAlmostEqual(sum(ws), 2, places=14)

    def test_bernoulli_digamma(self):
        B = M.bernoulli(6)
        self.assertEqual(B[:5], [1, Fraction(-1, 2), Fraction(1, 6), 0, Fraction(-1, 30)])
        gamma = Decimal("0.57721566490153286060651209008240243104215933593992")
        self.assertLess(abs(M.digamma(Decimal(1)) + gamma), Decimal(10) ** -40)
        half = M.digamma(Decimal(1) / 2)
        self.assertLess(abs(half + gamma + 2 * Decimal(2).ln()), Decimal(10) ** -40)

    def test_integral_value_and_digits(self):
        with decimal.localcontext() as ctx:
            ctx.prec = 50
            pi = M.machin_pi(50)
            val, sig = M.integral_value(Fraction(-314159, 100000), Fraction(1), pi, 50)
            self.assertLess(abs(val - (pi - Decimal("3.14159"))), Decimal(10) ** -45)
            self.assertGreater(sig, 40)
        self.assertEqual(M.digits_of(Decimal("1.23456"), 3), "1.234")
        self.assertTrue(M.as_printed(Decimal("1.23456"), "1.234"))
        self.assertTrue(M.as_printed(Decimal("1.23456"), "1.235"))
        self.assertFalse(M.as_printed(Decimal("1.23456"), "1.233"))
        self.assertTrue(M.as_printed(Decimal("-1.90291648559998123"), "-1.90291648559998"))
        self.assertEqual(M.common_digits(Decimal("7.1032053341370017"), "7.1032053341370018"), 15)
        self.assertEqual(str(M.machin_pi(50))[:52], M.PI50)

    def test_v1_search_needs_primes(self):
        self.assertIsNone(M.v1_counterexample(M.primes_upto(50), max_n=3))  # P_1, P_2, P_3 are empty


class Verdict(unittest.TestCase):
    def test_conditions(self):
        good = M.conditions(Decimal("7.10320533413700172"), True, True, True, Fraction(1, 10 ** 7), Fraction(98, 100))
        self.assertTrue(all(good.values()))
        self.assertEqual(len(good), 6)
        self.assertFalse(M.conditions(Decimal("7.103205334136999"), True, True, True, Fraction(0), Fraction(1))
                         ["the bound's expansion begins 7.103205334137"])
        self.assertFalse(M.conditions(Decimal("7.1032053341371"), True, True, True, Fraction(1, 10 ** 5), Fraction(1))
                         ["order-4 Richardson of |b_(n+1)/b_n| at 145 within 1e-5 of N3"])
        self.assertTrue(M.conditions(Decimal("7.1032053341371"), True, True, True, Fraction(0), Fraction(105, 100))
                        ["|I_n|^(1/n) <= 1.05 |N1| for n from 90 to 150"])
        self.assertFalse(M.conditions(Decimal("7.1032053341371"), True, True, True, Fraction(0), Fraction(106, 100))
                         ["|I_n|^(1/n) <= 1.05 |N1| for n from 90 to 150"])
        for k in (1, 2, 3):
            args = [Decimal("7.1032053341371"), True, True, True, Fraction(0), Fraction(1)]
            args[k] = False
            self.assertEqual(sum(M.conditions(*args).values()), 5)

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")

    def test_outputs_named(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)


if __name__ == "__main__":
    unittest.main()
