"""Multiplicity obstructions (gct/dip.py): weight multiplicities against brute force, plethysm coefficients against
classical decompositions, the raising operators, the kernels and ranks modulo p, the points, and the tableau functions,
all on small cases chosen here. None of the test's cases ((34,6,2), (47,7,2) or (n²-2, n, 2) in degree n + 1) and none
of the paper's occurrence obstructions is computed.

Run with: python3 -m unittest tests.test_dip
"""

import importlib.util
import io
import math
import os
import random
import shutil
import tarfile
import tempfile
import unittest
from itertools import combinations_with_replacement

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("gct_dip", os.path.join(HERE, "..", "gct", "dip.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "7a" * 32
P = M.PRIMES[0]


def brute_count(mu, d, n):
    vs = M.vectors(n)
    return sum(1 for c in combinations_with_replacement(range(len(vs)), d)
               if tuple(sum(vs[i][j] for i in c) for j in range(3)) == tuple(mu))


class Weights(unittest.TestCase):
    def test_vectors(self):
        for n in range(0, 7):
            vs = M.vectors(n)
            self.assertEqual(len(vs), math.comb(n + 2, 2))
            self.assertEqual(len(set(vs)), len(vs))
            self.assertTrue(all(sum(v) == n and min(v) >= 0 for v in vs))
        self.assertEqual(M.vectors(1), [(1, 0, 0), (0, 1, 0), (0, 0, 1)])

    def test_weight_count_brute(self):
        rng = random.Random(5)
        for _ in range(40):
            d, n = rng.randint(1, 4), rng.randint(1, 4)
            a = rng.randint(0, d * n)
            b = rng.randint(0, d * n - a)
            mu = (a, b, d * n - a - b)
            self.assertEqual(M.weight_count(mu, d, n), brute_count(mu, d, n), (mu, d, n))
            self.assertEqual(len(M.monomials(mu, d, n)), brute_count(mu, d, n), (mu, d, n))
        self.assertEqual(M.weight_count((5, -1, 2), 2, 3), 0)
        self.assertEqual(M.weight_count((3, 3, 1), 2, 3), 0)

    def test_dim_schur(self):
        self.assertEqual(M.dim_schur((1, 0, 0)), 3)
        self.assertEqual(M.dim_schur((1, 1, 0)), 3)
        self.assertEqual(M.dim_schur((2, 1, 0)), 8)
        self.assertEqual(M.dim_schur((4, 0, 0)), 15)
        self.assertEqual(len(M.partitions3(4)), 4)  # (4), (3,1), (2,2), (2,1,1)


class Plethysm(unittest.TestCase):
    def test_sym2_sym3(self):
        # Sym^2(Sym^3 C^3) = S_(6) + S_(4,2)
        got = {lam: M.plethysm(lam, 2, 3) for lam in M.partitions3(6)}
        self.assertEqual({k: v for k, v in got.items() if v}, {(6, 0, 0): 1, (4, 2, 0): 1})

    def test_sym4_sym2(self):
        # Sym^4(Sym^2 C^3): the even partitions of 8 with at most 3 rows, each once
        got = {lam: M.plethysm(lam, 4, 2) for lam in M.partitions3(8)}
        want = {lam: 1 for lam in M.partitions3(8) if all(x % 2 == 0 for x in lam)}
        self.assertEqual({k: v for k, v in got.items() if v}, want)

    def test_dimension_identity(self):
        for d, n in ((2, 4), (4, 2), (3, 3)):
            total = sum(M.plethysm(lam, d, n) * M.dim_schur(lam) for lam in M.partitions3(d * n))
            self.assertEqual(total, math.comb(math.comb(n + 2, 2) + d - 1, d))


class LinearAlgebra(unittest.TestCase):
    def test_rank_and_kernel(self):
        self.assertEqual(M.rank_mod([[1, 2, 3], [2, 4, 6], [1, 0, 1]], P), 2)
        self.assertEqual(M.rank_mod([], P), 0)
        # kernel of [[1, 1, 0], [0, 1, 1]] is spanned by (1, -1, 1)
        basis = M.kernel_mod(2, 3, {(0, 0): 1, (0, 1): 1, (1, 1): 1, (1, 2): 1}, P)
        self.assertEqual(len(basis), 1)
        v = basis[0]
        self.assertEqual((v[0] + v[1]) % P, 0)
        self.assertEqual((v[1] + v[2]) % P, 0)
        self.assertEqual(len(M.kernel_mod(0, 3, {}, P)), 3)

    def test_hwv_dimensions(self):
        # weight (2,2,0) of Sym^2(Sym^2 C^3): one highest weight vector; (3,1,0): none; (4,0,0): one (c_200^2)
        for lam, want in (((2, 2, 0), 1), ((3, 1, 0), 0), ((4, 0, 0), 1), ((2, 1, 1), 0)):
            cols, nrows, entries = M.raising_matrix(lam, 2, 2)
            self.assertEqual(len(M.kernel_mod(nrows, len(cols), entries, P)), want, lam)

    def test_raising_kills_the_discriminant(self):
        # 4 c_200 c_020 - c_110^2 is a highest weight vector of weight (2,2,0): E12 and E23 kill it
        vs = M.vectors(2)
        idx = {a: i for i, a in enumerate(vs)}
        cols, nrows, entries = M.raising_matrix((2, 2, 0), 2, 2)
        f = {tuple(sorted((idx[(2, 0, 0)], idx[(0, 2, 0)]))): 4, (idx[(1, 1, 0)],) * 2: -1}
        vec = [f.get(c, 0) for c in cols]
        image = {}
        for (r, j), v in entries.items():
            image[r] = image.get(r, 0) + v * vec[j]
        self.assertTrue(all(v == 0 for v in image.values()))
        # and a wrong combination is not killed
        vec[0] += 1
        image = {}
        for (r, j), v in entries.items():
            image[r] = image.get(r, 0) + v * vec[j]
        self.assertTrue(any(v != 0 for v in image.values()))


class Points(unittest.TestCase):
    def test_pow_and_ch_points(self):
        # n = 2: (x + 2y)^2 = x^2 + 4xy + 4y^2; (x + 2y)(3x + z) = 3x^2 + 6xy + xz + 2yz
        vs = M.vectors(2)
        pw = dict(zip(vs, M.pow_point(2, [(1, 2, 0)], P)))
        self.assertEqual((pw[(2, 0, 0)], pw[(1, 1, 0)], pw[(0, 2, 0)], pw[(0, 0, 2)]), (1, 4, 4, 0))
        ch = dict(zip(vs, M.ch_point(2, [(1, 2, 0), (3, 0, 1)], P)))
        self.assertEqual((ch[(2, 0, 0)], ch[(1, 1, 0)], ch[(1, 0, 1)], ch[(0, 1, 1)], ch[(0, 2, 0)]), (3, 6, 1, 2, 0))

    def test_case_on_quadrics(self):
        # the 2x2 minor of a ternary quadric's matrix (weight (2,2,0), d = n = 2): zero on squares, nonzero on sums of
        # two squares and on products of two linear forms
        c = M.case((2, 2, 0), 2, 2, SEED, "test", {"pow1": ("pow", 1), "pow2": ("pow", 2), "ch": ("ch", None)})
        self.assertEqual(c["a"], 1)
        self.assertEqual(c["kernel"], [1, 1])
        self.assertEqual(c["generic"], [1, 1])
        self.assertEqual(c["ranks"], {"pow1": [0, 0], "pow2": [1, 1], "ch": [1, 1]})
        self.assertEqual(M.mult(c, "ch"), 1)
        self.assertIsNone(M.mult({"ranks": {"x": [1, 0]}}, "x"))


class Tableaux(unittest.TestCase):
    def test_check(self):
        self.assertTrue(M.check_tableau([[1, 1], [2, 2]], (2, 2), 2, 2))
        self.assertFalse(M.check_tableau([[1, 2], [1, 2]], (2, 2), 2, 2))   # a column not increasing
        self.assertFalse(M.check_tableau([[1, 1, 1], [2]], (2, 2), 2, 2))   # wrong shape
        self.assertFalse(M.check_tableau([[1, 1], [2, 3]], (2, 2), 2, 2))   # a label out of range

    def test_value(self):
        # T = [[1,1],[2,2]]: f_T(sum_i l_i^2) = sum over (i, j) of det(l_i, l_j)^2 (first two coordinates)
        t = [[1, 1], [2, 2]]
        forms = [(3, 5, 7), (2, 9, 4), (8, 1, 6)]
        want = sum((a[0] * b[1] - a[1] * b[0]) ** 2 for a in forms for b in forms) % P
        self.assertEqual(M.tableau_value(t, 2, forms, P), want)
        self.assertEqual(M.tableau_value(t, 2, forms[:1], P), 0)
        # three rows: T = [[1,1],[2,2],[3,3]] (d = 3, n = 2): f = sum over (i, j, k) of det(l_i, l_j, l_k)^2
        t3 = [[1, 1], [2, 2], [3, 3]]
        want3 = 0
        for a in forms:
            for b in forms:
                for c in forms:
                    want3 += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
                              + a[2] * (b[0] * c[1] - b[1] * c[0])) ** 2
        self.assertNotEqual(want3 % P, 0)
        self.assertEqual(M.tableau_value(t3, 3, forms, P), want3 % P)

    def test_read_tableaux(self):
        brill = ("\\begin{longtable}{cc}\n{\\def\\lr#1{x}\n\\raisebox{-.6ex}{\\tiny$\\begin{array}[b]{*{2}c}\\cline{1-2}\n"
                 "\\lr{1}&\\lr{1}\\\\\\cline{1-2}\n\\lr{2}&\\lr{2}\\\\\\cline{1-2}\n\\end{array}$}\n} \\\\\n")
        main = ("text \\young(11,22) more. using the following 11 tableaux.\n\\begin{longtable}{c}\n"
                "\\raisebox{-.6ex}{\\tiny\\young(112,23,3)}\\\\\n{\\tiny\\young(111,22,3)}\n\\end{longtable}\n")
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tf:
            for name, text in (("calculations_brill.tex", brill), ("multobs.tex", main)):
                data = text.encode()
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
        t34, t47 = M.read_tableaux(buf.getvalue())
        self.assertEqual(t34, [[[1, 1], [2, 2]]])
        self.assertEqual(t47, [[[1, 1, 2], [2, 3], [3]], [[1, 1, 1], [2, 2], [3]]])


class Run(unittest.TestCase):
    def test_refused_seed(self):
        with self.assertRaises(M.Refused):
            M.run("nothex", inputs=os.path.join(HERE, "nonexistent"), results=os.path.join(HERE, "nonexistent"))

    def test_refused_hash(self):
        work = tempfile.mkdtemp()
        try:
            with open(os.path.join(work, M.EPRINT), "wb") as fh:
                fh.write(b"not the e-print")
            with self.assertRaises(M.Refused):
                M.run(SEED, inputs=work, results=os.path.join(work, "results"))
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def test_test_length(self):
        self.assertLessEqual(len(M.TEST), 600)

    def test_stream(self):
        a, b = M.Stream(SEED, "x"), M.Stream(SEED, "x")
        self.assertEqual([a.below(100) for _ in range(5)], [b.below(100) for _ in range(5)])

    def test_primes(self):
        for p in M.PRIMES:
            self.assertTrue(all(pow(a, p - 1, p) == 1 for a in (2, 3, 5, 7, 11, 13)))


if __name__ == "__main__":
    unittest.main()
