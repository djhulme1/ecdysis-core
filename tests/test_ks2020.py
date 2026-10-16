"""Kauffman & Steel's expected numbers of RAFs (raf/ks2020.py): the definitions, the brute force and Theorem 1(i)'s
formula on systems of one and two reactions whose expectations are derived by hand, the planted faults, the models,
the sampler and the beside computations. None of the archive's drawn systems, nor the paper's Fig. 1, is computed.

Run with: python3 -m unittest tests.test_ks2020
"""

import importlib.util
import math
import os
import random
import sys
import unittest
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("raf_ks2020", os.path.join(HERE, "..", "raf", "ks2020.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)


def one_reaction(cminus=(), bminus=()):
    """Food f (0) reacts to x (1)."""
    return M.System(2, [0], [((0,), (1,))], cminus, bminus)


def hs_example(cminus=()):
    """Hordijk & Steel's 2004 example: a..g are 0..6; F = {a, b}; r1: a + b -> c, by d; r2: b + c -> d, by a; r3: c + d
    -> e + f; r4: a + e -> g, by f."""
    a, b, c, d, e, f, g = range(7)
    s = M.System(7, (a, b), [((a, b), (c,)), ((b, c), (d,)), ((c, d), (e, f)), ((a, e), (g,))], cminus)
    return s, {0: {d}, 1: {a}, 2: set(), 3: {f}}


def all_three(s, cd, bd=None):
    cg = M.enumerate_groups(s, s.cat_types, "cat")
    bg = M.enumerate_groups(s, s.blk_types, "blk")
    mu, p, mu_u = M.brute(s, cg, bg, cd, bd)
    return mu, p, mu_u, cg, bg


class Definitions(unittest.TestCase):
    def test_hs_example(self):
        s, cat = hs_example()
        A = M.raf_mask(s, M.cols_of(s, cat))
        rafs = {frozenset(r for r in range(s.k) if S >> r & 1) for S in range(1, 1 << s.k) if A >> S & 1}
        self.assertEqual(rafs, {frozenset({0, 1})})              # r3 is uncatalysed, so r4's f never appears
        ref, _ = M.raf_sets_reference(s, cat)
        self.assertEqual(set(ref), rafs)
        s2, cat2 = hs_example(cminus=(0,))                        # a may no longer catalyse r2
        self.assertEqual(M.raf_mask(s2, M.cols_of(s2, cat2)), 0)

    def test_f_generated_two_ways(self):
        s, _ = hs_example()
        for S in range(1, 1 << s.k):
            self.assertEqual(s.fg[S], M.f_generated_by_orderings(s, S))
        self.assertTrue(s.fg[0b0011] and not s.fg[0b0010] and s.fg[0b1111] and not s.fg[0b1000])

    def test_food_products_and_inhibition(self):
        # f -> x + f: the product f is food and may catalyse; x inhibits.
        s = M.System(2, [0], [((0,), (1, 0))])
        self.assertEqual(s.s[1], 1)
        cat, inh = {0: {0}}, {0: {1}}
        A = M.raf_mask(s, M.cols_of(s, cat))
        U = M.unblocked_mask(s, M.cols_of(s, inh))
        self.assertEqual((A, A & U), (0b10, 0))
        _, u = M.raf_sets_reference(s, cat, inh)
        self.assertEqual(u, [])

    def test_validation(self):
        with self.assertRaises(ValueError):
            M.System(2, [0], [((0,), (1,))], cminus=[1])
        with self.assertRaises(ValueError):
            M.System(2, [0], [((), (1,))])


class HandExpectations(unittest.TestCase):
    def test_one_reaction(self):
        p, q = Fr(1, 5), Fr(1, 7)
        for cminus, n in (((), 2), ((0,), 1)):
            s = one_reaction(cminus)
            mu, P, mu_u, *_ = all_three(s, M.model("uniform", p), M.model("uniform", q))
            self.assertEqual(mu, 1 - (1 - p) ** n)
            self.assertEqual(P, mu)
            self.assertEqual(mu_u, (1 - (1 - p) ** n) * (1 - q) ** 2)
            self.assertEqual(M.formula(s, M.model("uniform", p)), mu)
            self.assertEqual(M.formula(s, M.model("uniform", p), M.model("uniform", q)), mu_u)

    def test_two_elementary_reactions(self):
        s = M.elementary_system(2)
        for p in (Fr(1, 4), Fr(1, 3)):
            mu, P, *_ = all_three(s, M.model("uniform", p))
            self.assertEqual(mu, 2 * p + (2 * p - p * p) ** 2)
            self.assertEqual(M.formula(s, M.model("uniform", p)), mu)
            mu_a, P_a, *_ = all_three(s, M.model("aon", p))
            self.assertEqual(mu_a, 4 - (2 - p) ** 2)
            self.assertEqual(P_a, 1 - (1 - p) ** 2)
            self.assertEqual(M.formula(s, M.model("aon", p)), mu_a)
            # sparse: each x is a catalyst (C = 2p) with chance 1/2
            mu_s, *_ = all_three(s, M.model("sparse", p))
            single = Fr(1, 2) * 2 * p                              # E[C]: x_j catalyses its own reaction
            lam1, lam2 = 1 - p, Fr(1, 2) + Fr(1, 2) * (1 - 2 * p) ** 2
            pair = 1 - 2 * lam1 ** 2 + lam2 ** 2
            self.assertEqual(mu_s, 2 * single + pair)
            self.assertEqual(M.formula(s, M.model("sparse", p)), mu_s)
            self.assertLessEqual(mu, mu_s)                        # Theorem 1(ii) in this case

    def test_double_sum_matches(self):
        s = M.System(3, [0], [((0,), (1,)), ((1,), (2,))])
        cg = M.enumerate_groups(s, s.cat_types, "cat")
        bg = M.enumerate_groups(s, s.blk_types, "blk")
        cd, bd = M.model("two-point", Fr(1, 3)), M.model("sparse", Fr(1, 5))
        self.assertEqual(M.brute(s, cg, bg, cd, bd)[2], M.brute(s, cg, bg, cd, bd, double=True)[2])

    def test_faults_are_caught(self):
        s = one_reaction()
        cd = M.model("uniform", Fr(1, 5))
        mu = all_three(s, cd)[0]
        self.assertNotEqual(M.formula(s, cd, fault="no-food"), mu)
        s2 = M.System(3, [0], [((0,), (1, 2))])                   # two products from one reaction: s = 2, k = 1
        self.assertNotEqual(M.formula(s2, cd, fault="k-for-s"), all_three(s2, cd)[0])


class Models(unittest.TestCase):
    def test_means_and_sums(self):
        for kind in ("uniform", "sparse", "aon", "two-point"):
            for mu in (Fr(1, 5), Fr(1, 3)):
                d = M.model(kind, mu)
                self.assertEqual(sum(w for w, _ in d), 1)
                self.assertEqual(sum(w * v for w, v in d), mu)
                for k in (1, 2, 4):
                    self.assertEqual(sum(math.comb(k, a) * x for a, x in enumerate(M.row_probs(d, k))), 1)
        self.assertEqual(M.lam(M.model("aon", Fr(1, 4)), 3), Fr(3, 4))
        self.assertEqual(M.lam(M.model("uniform", Fr(1, 4)), 3), Fr(27, 64))
        with self.assertRaises(ValueError):
            M.model("sparse", Fr(2, 3))

    def test_sampler(self):
        s = M.System(3, [0], [((0,), (1,)), ((1,), (2,))])
        cd, bd = M.model("sparse", Fr(1, 5)), M.model("uniform", Fr(1, 6))
        exact = M.brute(s, M.enumerate_groups(s, s.cat_types, "cat"), M.enumerate_groups(s, s.blk_types, "blk"),
                        cd, bd)[2]
        mean, se = M.monte_carlo(s, "ab" * 32, "test", cd, bd, n=4000)
        self.assertLess(abs(mean - float(exact)), 4 * se)

    def test_draws(self):
        for i in range(6):
            s = M.draw_system("cd" * 32, i)
            self.assertLessEqual((1 << s.k) ** len(s.cat_types), M.BUDGET)
            self.assertLessEqual((1 << s.k) ** len(s.blk_types), M.BUDGET)
            self.assertTrue(any(s.fg[1 << r] for r in range(s.k)))
            self.assertEqual(M.draw_system("cd" * 32, i).reactions, s.reactions)


class Beside(unittest.TestCase):
    def test_ab0_and_series(self):
        g = 0.05
        self.assertAlmostEqual(M.series(g), g + 2 * g ** 2 + 4.5 * g ** 3 + (256 / 24) * g ** 4, delta=1e-5)
        self.assertLess(abs(M.ab0(10 ** 5, g) - M.series(g)) / M.series(g), 1e-3)

    def test_generable_and_corollary(self):
        s = M.System(3, [0], [((0,), (1,)), ((1,), (2,))])
        self.assertEqual(M.generable(s), 3)
        self.assertIn(M.corollary2(s, 0.5), (True, False))


if __name__ == "__main__":
    unittest.main()
