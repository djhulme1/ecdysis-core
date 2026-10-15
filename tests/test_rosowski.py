"""Rosowski's commutative algorithms (mm/rosowski.py): the linear forms, the exact expansion and its check against
the matrix product, the product count with factors normalised by sign and order, the numeric evaluation, the matrix
helpers and the transposition-aware count, all on programs of the tests' own (the classical product, Strassen's,
hand-made ones). None of the paper's algorithms is expanded or counted here.

Run with: python3 -m unittest tests.test_rosowski
"""

import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("mm_rosowski", os.path.join(HERE, "..", "mm", "rosowski.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "ef" * 32
a, b, L, neg = M.a, M.b, M.L, M.neg


class Forms(unittest.TestCase):
    def test_linear_forms(self):
        self.assertEqual(L(a(1, 1), neg(b(2, 1)), a(1, 1)), {a(1, 1): 2, b(2, 1): -1})
        self.assertEqual(L(a(1, 1), neg(a(1, 1))), {})

    def test_expand(self):
        # (a11 + b11)(a11 - b11) = a11^2 - b11^2
        prog = {(1, 1): [(1, L(a(1, 1), b(1, 1)), L(a(1, 1), neg(b(1, 1))))]}
        self.assertEqual(M.expand(prog), {(1, 1): {(a(1, 1), a(1, 1)): 1, (b(1, 1), b(1, 1)): -1}})

    def test_holds_classical_and_strassen(self):
        self.assertTrue(M.holds(M.classical(2, 3, 4), 2, 3, 4))
        self.assertTrue(M.holds(M.strassen(), 2, 2, 2))
        bad = M.strassen()
        bad[(1, 2)] = bad[(1, 2)][:1]
        self.assertFalse(M.holds(bad, 2, 2, 2))
        self.assertFalse(M.holds(M.classical(2, 3, 3), 2, 3, 4))      # a missing column

    def test_target(self):
        t = M.target(1, 2, 1)
        self.assertEqual(t, {(1, 1): {(a(1, 1), b(1, 1)): 1, (a(1, 2), b(2, 1)): 1}})


class Counting(unittest.TestCase):
    def test_sign_and_order(self):
        f, g = L(a(1, 1), b(2, 1)), L(neg(a(1, 2)), neg(b(1, 2)))
        prog = {(1, 1): [(1, f, g)], (1, 2): [(-1, L(neg(a(1, 2)), neg(b(1, 2))), L(a(1, 1), b(2, 1)))],
                (1, 3): [(1, L(a(1, 2), b(1, 2)), L(a(1, 1), b(2, 1)))]}
        self.assertEqual(len(M.products(prog)), 1)
        self.assertEqual(M.occurrences(prog), 3)
        self.assertEqual(M.norm_factor(L(neg(a(1, 1)), b(1, 1))), (((("a", 1, 1), 1), (("b", 1, 1), -1)), -1))

    def test_strassen_count(self):
        self.assertEqual(len(M.products(M.strassen())), 7)
        self.assertEqual(len(M.products(M.classical(3, 3, 3))), 27)

    def test_formulas(self):
        self.assertEqual(M.theorem3_bound(3, 3, 3), 21)
        self.assertEqual(M.theorem3_bound(3, 3, 4), 28)
        self.assertEqual(M.waksman(3, 3, 3), 23)     # (n - 1)(lm + l + m - 1)/2 + lm = 14 + 9
        with self.assertRaises(ValueError):
            M.theorem3(2, 4, 5)
        with self.assertRaises(ValueError):
            M.theorem3(2, 5, 2)


class Numeric(unittest.TestCase):
    def test_numeric(self):
        self.assertTrue(M.numeric_ok(M.classical(2, 3, 2), 2, 3, 2, M.Stream(SEED, "n")))
        self.assertTrue(M.numeric_ok(M.strassen(), 2, 2, 2, M.Stream(SEED, "s")))
        bad = M.strassen()
        bad[(2, 2)] = bad[(2, 2)][1:]
        self.assertFalse(M.numeric_ok(bad, 2, 2, 2, M.Stream(SEED, "s")))
        vals = {a(1, 1): 3, b(1, 1): 5}
        self.assertEqual(M.evaluate({(1, 1): [(2, L(a(1, 1)), L(b(1, 1), a(1, 1)))]}, vals), {(1, 1): 48})

    def test_stream(self):
        x, y = M.Stream(SEED, "q"), M.Stream(SEED, "q")
        self.assertEqual([x.int_in(-5, 5) for _ in range(10)], [y.int_in(-5, 5) for _ in range(10)])
        self.assertTrue(all(-5 <= M.Stream(SEED, "r").int_in(-5, 5) <= 5 for _ in range(10)))


class Matrices(unittest.TestCase):
    def test_helpers(self):
        X = ((1, 2), (3, 4))
        Y = ((0, 1), (1, 0))
        self.assertEqual(M.mmul(X, Y), ((2, 1), (4, 3)))
        self.assertEqual(M.mT(X), ((1, 3), (2, 4)))
        self.assertEqual(M.madd(X, Y, -1), ((1, 1), (2, 4)))
        self.assertNotEqual(M.mmul(X, Y), M.mmul(Y, X))
        R = M.mat_rand(M.Stream(SEED, "m"))
        self.assertEqual((len(R), len(R[0])), (M.BLOCK, M.BLOCK))

    def test_noncommutative_eval(self):
        # Strassen's algorithm is bilinear, so it holds with matrix entries in its own factor order
        st = M.Stream(SEED, "nc")
        vals = {v: M.mat_rand(st) for v in [a(i, j) for i in (1, 2) for j in (1, 2)] + [b(i, j) for i in (1, 2)
                                                                                         for j in (1, 2)]}
        got = M.eval_noncommutative(M.strassen(), vals)
        for i in (1, 2):
            for j in (1, 2):
                want = M.madd(M.mmul(vals[a(i, 1)], vals[b(1, j)]), M.mmul(vals[a(i, 2)], vals[b(2, j)]))
                self.assertEqual(got[(i, j)], want)

    def test_transposition_count(self):
        X = {("A", 1, 1, False): 1}
        Y = {("B", 1, 1, False): 1}
        XT = {("A", 1, 1, True): 1}
        YT = {("B", 1, 1, True): 1}
        prog = {(1, 1): [(1, X, Y), (1, YT, XT)], (1, 2): [(1, Y, X)]}
        self.assertEqual(M.nonbilinear_count(prog), 2)
        vals = {("A", 1, 1): ((1, 2, 0), (0, 1, 0), (0, 0, 1)), ("B", 1, 1): ((1, 0, 0), (3, 1, 0), (0, 0, 1))}
        got = M.nonbilinear_eval({(1, 1): [(1, X, YT)]}, vals)
        self.assertEqual(got[(1, 1)], M.mmul(vals[("A", 1, 1)], M.mT(vals[("B", 1, 1)])))


class Run(unittest.TestCase):
    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("nothex", results=os.path.join(HERE, "nonexistent-results"))

    def test_test_length(self):
        self.assertLessEqual(len(M.TEST), 600)


if __name__ == "__main__":
    unittest.main()
