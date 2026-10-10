"""Landsberg & Ottaviani's Koszul flattening check: the rank modulo a prime on matrices of known rank, the flattening on
rank-one and low-rank tensors (Theorem 2.1's inequality), one column of M_<2>'s matrix worked by hand, the bounds for
n = 2 and 3, and broken constructions that must fall short of 2n^2 - n.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import os
import tempfile
import unittest
from fractions import Fraction
from itertools import combinations
from math import comb

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("koszul_check", os.path.join(HERE, "..", "koszul", "check.py"))
K = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(K)

SEED = "0" * 63 + "9"
P = K.PRIMES[0]


def collapsed(n):
    """M_<n> with the top degree folded into the one below it, a_ij -> x_min(i + j, 2n - 3): not the paper's projection."""
    t = {}
    for i in range(n):
        for j in range(n):
            for k in range(n):
                key = (min(i + j, 2 * n - 3), j * n + k, k * n + i)
                t[key] = t.get(key, 0) + 1
    return t, 2 * n - 1, n * n, n * n


def bound(t, a, b, c, p):
    rows, _ = K.flattening(t, a, b, c, p)
    return Fraction(max(K.ranks(rows)), comb(a - 1, p))


class Rank(unittest.TestCase):
    def test_known_ranks(self):
        identity = [{i: 1} for i in range(6)]
        self.assertEqual(K.rank_mod(identity, P), 6)
        repeated = [{0: 1, 1: 2}, {0: 2, 1: 4}, {2: 5}]
        self.assertEqual(K.rank_mod(repeated, P), 2)
        self.assertEqual(K.rank_mod([{}, {}], P), 0)
        self.assertEqual(K.rank_mod([{0: P}, {1: 1}], P), 1)          # P is 0 modulo P
        self.assertEqual(K.rank_mod([{0: 1, 1: 1}, {0: 1, 1: -1}], 2), 1)  # dependent modulo 2 only

    def test_three_primes(self):
        self.assertEqual(K.ranks([{0: 3}, {1: 7}]), [2, 2, 2])


class Flattening(unittest.TestCase):
    def test_rank_one_gives_the_binomial(self):
        stream = K.Stream(SEED, "test/rank-one")
        for a, p, b, c in ((3, 1, 2, 2), (4, 1, 3, 2), (5, 2, 4, 4), (6, 2, 3, 3)):
            with self.subTest(a=a, p=p):
                rows, _ = K.flattening(K.random_tensor(stream, a, b, c, 1, nonzero=True), a, b, c, p)
                self.assertEqual(K.ranks(rows), [comb(a - 1, p)] * 3)

    def test_r_terms_give_at_most_r_times_the_binomial(self):
        stream = K.Stream(SEED, "test/low-rank")
        for r in (1, 2, 5, 9):
            with self.subTest(r=r):
                rows, _ = K.flattening(K.random_tensor(stream, 5, 6, 6, r), 5, 6, 6, 2)
                self.assertLessEqual(max(K.ranks(rows)), r * comb(4, 2))

    def test_one_column_of_m2_by_hand(self):
        # x_0 (x) b*_00 goes to sum over i of (x_i wedge x_0) (x) c_0i; only i = 1 survives, x_1 wedge x_0 = -x_01.
        t, a, b, c = K.mm_projected(2, 2, 2)
        rows, ncols = K.flattening(t, a, b, c, 1)
        cols = [(S, beta) for S in combinations(range(a), 1) for beta in range(b)]
        index = [(S, g) for S in combinations(range(a), 2) for g in range(c)]
        col = cols.index(((0,), 0))
        self.assertEqual([(index[r], row[col]) for r, row in enumerate(rows) if col in row], [(((0, 1), 1), -1)])
        self.assertEqual((len(rows), ncols), (12, 12))

    def test_the_matrix_multiplication_tensor(self):
        t, a, b, c = K.mm_projected(2, 3, 2)
        self.assertEqual((a, b, c), (4, 6, 4))
        self.assertEqual(sum(t.values()), 2 * 3 * 2)


class Bounds(unittest.TestCase):
    def test_the_paper_s_bound_for_n_2_and_3(self):
        for n in (2, 3):
            with self.subTest(n=n):
                t, a, b, c = K.mm_projected(n, n, n)
                self.assertEqual(bound(t, a, b, c, n - 1), 2 * n * n - n)

    def test_a_broken_projection_falls_short(self):
        for n in (2, 3, 4):
            with self.subTest(n=n):
                self.assertLess(bound(*collapsed(n), n - 1), 2 * n * n - n)

    def test_the_forgetful_projection_stays_within_its_rank(self):
        self.assertLessEqual(bound(*K.mm_forgetful(3), 2), 9)

    def test_rectangular_formula(self):
        for m, n, l in K.RECTANGULAR:
            with self.subTest(shape=(m, n, l)):
                t, a, b, c = K.mm_projected(m, n, l)
                self.assertEqual(bound(t, a, b, c, n - 1), Fraction(n * l * (n + m - 1), m))


class Run(unittest.TestCase):
    def test_a_small_run(self):
        with tempfile.TemporaryDirectory() as d:
            out, detail = K.run(SEED, d, sizes=(2, 3), log=lambda *_: None)
        self.assertEqual((out["bounds"], out["targets"], out["test_passed"]), ("6,15", "6,15", 1))
        self.assertEqual(out["controls_passed"], out["controls_total"], detail["control_results"])

    def test_the_seed_draws_the_controls_and_nothing_else(self):
        with tempfile.TemporaryDirectory() as d:
            a, _ = K.run(SEED, d, sizes=(2,), log=lambda *_: None)
            b, _ = K.run("f" * 64, d, sizes=(2,), log=lambda *_: None)
        self.assertEqual({k: v for k, v in a.items() if k != "low_rank_max"},
                         {k: v for k, v in b.items() if k != "low_rank_max"})


if __name__ == "__main__":
    unittest.main()
