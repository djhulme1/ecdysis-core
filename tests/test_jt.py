"""Johns & Teitler's decomposition (waring/jt.py): the cyclotomic arithmetic, sparse products, substitution over the
symmetric group, the modular and floating-point determinants, the primes and roots of unity, on inputs made here.
The paper's decomposition, its symmetries and its equations are never evaluated.

Run with: python3 -m unittest tests.test_jt
"""

import importlib.util
import math
import os
import random
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("waring_jt", os.path.join(HERE, "..", "waring", "jt.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


class Cyclotomic(unittest.TestCase):
    def test_known_polynomials(self):
        self.assertEqual(M.cyclotomic(10), [1, -1, 1, -1, 1])
        self.assertEqual(M.cyclotomic(12), [1, 0, -1, 0, 1])
        self.assertEqual(M.cyclotomic(15), [1, -1, 0, 1, -1, 1, 0, -1, 1])

    def test_reduction(self):
        self.assertEqual(M.reduce_cyc([0, 0, 1, 0], 4), (-1, 0))          # ω^2 = -1 for ω of order 4
        self.assertEqual(M.reduce_cyc([0, 0, 0, 1, 0, 0], 6), (-1, 0))    # ω^3 = -1 for ω of order 6
        self.assertEqual(M.reduce_cyc([1, 1, 1], 3), (0, 0))
        self.assertEqual(M.reduce_cyc([5, 0, 0, 0, 0], 5), (5, 0, 0, 0))

    def test_rotate(self):
        self.assertEqual(M.rotate([1, 2, 3], 1), [3, 1, 2])
        self.assertEqual(M.rotate([1, 2, 3], 3), [1, 2, 3])
        self.assertEqual(M.rotate([1, 2, 3, 4], -1), [2, 3, 4, 1])


class Polynomials(unittest.TestCase):
    def test_binomial(self):
        F = M.power_linear([(0, 0, 1), (1, 0, 1)], 3, 2, 1)
        self.assertEqual({k: v[0] for k, v in F.items()}, {(3, 0): 1, (2, 1): 3, (1, 2): 3, (0, 3): 1})

    def test_ring_coefficients(self):
        F = M.power_linear([(0, 0, 1), (1, 1, 1)], 2, 2, 3)               # (y1 + t y2)^2 in Z[t]/(t^3 - 1)
        self.assertEqual(F, {(2, 0): [1, 0, 0], (1, 1): [0, 2, 0], (0, 2): [0, 0, 1]})

    def test_roots_of_unity_filter(self):
        # Σ_k (y1 + ω^k y2)^n = n (y1^n + y2^n) for ω of order n: an identity that is not the paper's
        for n in (3, 4, 5, 6):
            acc = {}
            for k in range(n):
                M.add_into(acc, M.power_linear([(0, 0, 1), (1, k, 1)], n, 2, n), 1)
            red = M.reduce_poly(acc, n)
            zero = (0,) * (len(M.cyclotomic(n)) - 2)
            self.assertEqual(red, {(n, 0): (n,) + zero, (0, n): (n,) + zero})

    def test_products(self):
        got = M.poly_from_products([(1, [{0: 1, 1: 1}, {0: 1, 1: -1}])], 2)
        self.assertEqual(got, {(2, 0): 1, (0, 2): -1})

    def test_compositions(self):
        self.assertEqual(sum(1 for _ in M.compositions(4, 3)), 15)
        self.assertEqual(sum(1 for _ in M.compositions(5, 5)), math.comb(9, 5))


class Substitution(unittest.TestCase):
    def test_leibniz_from_the_product_block(self):
        # the block y1 ... yd substituted over S_d is the Leibniz expansion of det_d
        for d in (2, 3, 4):
            perms = M.perms_with_signs(d)
            block = {tuple([1] * d): [1]}
            R = M.substitute(block, d, perms, 1)
            same, bad, nonzero = M.compare(R, M.det_target(d, perms, 1), 1)
            self.assertTrue(same and bad == 0 and nonzero == math.factorial(d))
            R[next(iter(R))][0] += 1
            self.assertFalse(M.compare(R, M.det_target(d, perms, 1), 1)[0])

    def test_signs(self):
        signs = dict(M.perms_with_signs(3))
        self.assertEqual(signs[(0, 1, 2)], 1)
        self.assertEqual(signs[(1, 0, 2)], -1)
        self.assertEqual(signs[(1, 2, 0)], 1)
        self.assertEqual(sum(s for _, s in M.perms_with_signs(5)), 0)


class Modular(unittest.TestCase):
    def test_primes(self):
        p1, p2 = M.primes_1_mod(2520, 2 ** 31, 2)
        self.assertTrue(p2 < p1 < 2 ** 31 and p1 % 2520 == 1 and p2 % 2520 == 1)
        for n in (p1, p2):
            self.assertTrue(all(n % q for q in range(2, 50000)))
        k = (p1 - 1) // 2520 + 1
        while 1 + 2520 * k < 2 ** 31:
            self.assertFalse(M.is_prime(1 + 2520 * k))
            k += 1
        small = [n for n in range(2, 3000) if all(n % q for q in range(2, int(n ** 0.5) + 1))]
        self.assertEqual([n for n in range(2, 3000) if M.is_prime(n)], small)

    def test_roots_of_unity(self):
        p = M.primes_1_mod(2520, 2 ** 31, 1)[0]
        for d in range(2, 11):
            if (p - 1) % d:
                continue
            w = M.root_of_unity(d, p)
            self.assertEqual(pow(w, d, p), 1)
            self.assertTrue(all(pow(w, k, p) != 1 for k in range(1, d)))

    def test_determinants(self):
        p = 2 ** 31 - 1
        rng = random.Random(5)
        for d in range(1, 6):
            X = [[rng.randrange(-9, 10) for _ in range(d)] for _ in range(d)]
            self.assertEqual(M.det_mod(X, p), M.leibniz(X, M.perms_with_signs(d)) % p)
            self.assertAlmostEqual(abs(M.float_det(X) - M.leibniz(X, M.perms_with_signs(d))), 0, places=6)
        self.assertEqual(M.det_mod([[1, 2], [2, 4]], p), 0)

    def test_rank(self):
        p = 101
        self.assertEqual(M.rank_mod([[1, 2], [2, 4]], p), 1)
        self.assertEqual(M.rank_mod([[1, 0, 0], [0, 1, 0], [0, 0, 1]], p), 3)
        self.assertEqual(M.rank_mod([[1, 2, 3], [2, 4, 6], [1, 1, 1]], p), 2)

    def test_stream(self):
        a = M.Stream("ab" * 32, "x")
        b = M.Stream("ab" * 32, "x")
        xs = [a.below(7) for _ in range(200)]
        self.assertEqual(xs, [b.below(7) for _ in range(200)])
        self.assertEqual(set(xs), set(range(7)))
        u = [a.unit() for _ in range(100)]
        self.assertTrue(all(-1 <= v < 1 for v in u))


class Monomial(unittest.TestCase):
    def test_membership(self):
        d = 6
        for j in range(1, d + 1):
            for k in range(d):
                E = [k + j * (r + 1) for r in range(d)]
                self.assertEqual(M.in_M((0, 1, 2, 3, 4, 5), E, d), j)
        self.assertIsNone(M.in_M((0, 1, 2, 3, 4, 5), [0, 1, 3, 3, 4, 5], d))

    def test_affine_counts_beyond_the_range(self):
        for d in (10, 12):
            self.assertEqual(len(M.affine_perms(d)), d * M.euler_phi(d))

    def test_unit_power(self):
        self.assertEqual(M.unit_power(-1, 0, 4), (1, 2))
        self.assertEqual(M.unit_power(-1, 1, 3), (-1, 1))
        self.assertEqual(M.unit_power(1, 7, 3), (1, 1))

    def test_normalise(self):
        self.assertEqual(M.normalise([[0, 2], [4, 0]], 5), (0, 1, 2, 0))


class WholeRun(unittest.TestCase):
    def test_refusal(self):
        with self.assertRaises(M.Refused):
            M.run("xyz")

    def test_constants(self):
        self.assertLessEqual(len(M.TEST), 600)
        self.assertEqual(len(set(M.OUTPUTS)), len(M.OUTPUTS))
        self.assertLessEqual(len(M.OUTPUTS), 64)
        self.assertEqual(sum(len(v) for v in M.TABLE1.values()), 41)
        self.assertEqual(M.EXACT_D + M.MODULAR_D, tuple(range(2, 10)))


if __name__ == "__main__":
    unittest.main()
