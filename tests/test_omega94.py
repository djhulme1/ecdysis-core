"""OpenAI's 9/4 (mm/omega94.py): cyclotomic arithmetic, the substitution engine under phases other than the paper's,
C(a,b), the polynomial bases and the exact solver, a partition helper, the linear programme on a small grid without
the tripling, and the rank helpers, on inputs other than the claim's own case: none of the paper's constructions is
checked here and the registered grid is never solved.

Run with: python3 -m unittest tests.test_omega94 (in the pinned scipy-notebook image)
"""

import importlib.util
import math
import os
import random
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("mm_omega94", os.path.join(HERE, "..", "mm", "omega94.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


def pmul(p, q):
    out = [0] * (len(p) + len(q) - 1)
    for i, x in enumerate(p):
        for j, y in enumerate(q):
            out[i + j] += x * y
    return out


class Cyclotomic(unittest.TestCase):
    def test_small(self):
        self.assertEqual(M.cyclotomic(1), [-1, 1])
        self.assertEqual(M.cyclotomic(2), [1, 1])
        self.assertEqual(M.cyclotomic(4), [1, 0, 1])
        self.assertEqual(M.cyclotomic(6), [1, -1, 1])
        self.assertEqual(M.cyclotomic(12), [1, 0, -1, 0, 1])

    def test_product_over_divisors(self):
        for n in range(1, 31):
            p = [1]
            for d in range(1, n + 1):
                if n % d == 0:
                    p = pmul(p, M.cyclotomic(d))
            self.assertEqual(p, [-1] + [0] * (n - 1) + [1], n)

    def test_char_sums(self):
        for L in (3, 7, 8):
            for k in range(-2 * L, 2 * L + 1):
                s = M.char_sum(k, L)
                if k % L == 0:
                    self.assertEqual(s[0], L)
                    self.assertFalse(any(s[1:]))
                else:
                    self.assertFalse(any(s))


class Engine(unittest.TestCase):
    def test_trivial_phases_keep_every_term(self):
        rng = random.Random(5)
        A = M.random_block_tensor(2, rng)
        zero = {"x": lambda r, g: 0, "y": lambda r, h, u: 0, "z": lambda r, h, v: 0}
        T = M.separate(A, 2, 4, phases=zero)
        self.assertEqual(len(T), len(A) * 8)            # every (g, u, v) survives with sum L
        self.assertTrue(all(vec[0] == 4 * A[(h, a, b, c)] for (a, g, h, b, u, c, v), (vec, w) in T.items()))

    def test_blocks(self):
        rng = random.Random(9)
        A = M.random_block_tensor(3, rng)
        self.assertEqual({k[0] for k in A}, {1, 2, 3})
        self.assertTrue(all(abs(v) <= M.COEFF and v for v in A.values()))


class Polynomials(unittest.TestCase):
    def test_C(self):
        self.assertEqual(len(M.C(2, 3)), 6)
        self.assertEqual(set(M.C(1, 2)), {(0, 0, 0), (0, 1, 1)})

    def test_kernel_vectors_vanish_on_the_diagonal(self):
        for e in range(1, 6):
            quot, kern = M.basis_VeW(e)
            self.assertEqual(len(quot) + len(kern), 2 * (e + 1))
            for vec in kern:                            # (i, s) -> u^(e-i+1) v^i, (i, w) -> u^(e-i) v^(i+1)
                image = {}
                for (i, t), x in vec.items():
                    m = i if t == "s" else i + 1
                    image[m] = image.get(m, 0) + x
                self.assertTrue(all(x == 0 for x in image.values()))

    def test_solve(self):
        coords = [0, 1, 2]
        basis = [{0: Fraction(1), 1: Fraction(1)}, {1: Fraction(1)}, {1: Fraction(2), 2: Fraction(3)}]
        xs = M.solve(basis, {0: Fraction(2), 1: Fraction(5), 2: Fraction(3)}, coords)
        self.assertEqual(xs, [2, 1, 1])
        with self.assertRaises(AssertionError):
            M.solve([{0: Fraction(1)}, {0: Fraction(2)}], {0: Fraction(1)}, [0, 1])

    def test_part_of(self):
        parts = [(0, 2), (3, 3), (4, 9)]
        self.assertEqual([M.part_of(x, parts) for x in (0, 2, 3, 4, 9, 10)], [0, 0, 1, 2, 2, None])


class Programme(unittest.TestCase):
    def test_small_grid_without_tripling(self):
        v, viol = M.growth_lp(2, n_a=3, n_b=6, tripling_on=False)
        self.assertGreaterEqual(v, -1e-9)
        self.assertLess(viol, 1e-7)

    def test_bounds(self):
        self.assertAlmostEqual(M.h_proof(1), 1.0)
        self.assertAlmostEqual(M.h_proof(2), 4 / 3)
        self.assertGreater(M.t_bound(10 ** 3), M.t_bound(10 ** 9))
        self.assertGreater(M.t_bound(10 ** 9), 0.75)


class Ranks(unittest.TestCase):
    def test_trivial_sizes(self):
        self.assertTrue(M.rank_decomposition(1, 1))
        self.assertTrue(M.rank_decomposition(1, 2))
        self.assertEqual(M.flattening_rank(1, 1), 1)


class Source(unittest.TestCase):
    def test_refusal(self):
        with self.assertRaises(M.Refused):
            M.run("xyz")

    def test_constants(self):
        self.assertLessEqual(len(M.TEST), 600)
        self.assertEqual(len(set(M.OUTPUTS)), len(M.OUTPUTS))
        self.assertLessEqual(len(M.OUTPUTS), 64)


if __name__ == "__main__":
    unittest.main()
