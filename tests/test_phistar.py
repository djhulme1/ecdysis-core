"""Phi* from the decoding perspective (iit/phistar.py): the linear algebra, the steady state, the Gaussian quantities
against closed forms, the search, and the drawn systems, all on inputs chosen here. None of the test's systems (the
paper's model at a = 0 or a = 0.4, or systems drawn from an archive seed) is computed, and no test asks whether Phi*
lies between 0 and I on a system with interacting parts.

Run with: python3 -m unittest tests.test_phistar
"""

import importlib.util
import math
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("iit_phistar", os.path.join(HERE, "..", "iit", "phistar.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "5c" * 32


def close(a, b, tol=1e-12):
    return all(abs(x - y) <= tol for ra, rb in zip(a, b) for x, y in zip(ra, rb))


class LinearAlgebra(unittest.TestCase):
    def test_products_and_inverse(self):
        a = [[2.0, 1.0, 0.5], [1.0, 3.0, 0.2], [0.5, 0.2, 1.5]]
        self.assertEqual(M.mul([[1, 2], [3, 4]], [[5, 6], [7, 8]]), [[19, 22], [43, 50]])
        self.assertEqual(M.tr([[1, 2, 3], [4, 5, 6]]), [[1, 4], [2, 5], [3, 6]])
        self.assertTrue(close(M.mul(a, M.inv(a)), M.eye(3)))
        x = M.solve(a, [[1.0], [2.0], [3.0]])
        self.assertTrue(close(M.mul(a, x), [[1.0], [2.0], [3.0]]))
        with self.assertRaises(ZeroDivisionError):
            M.inv([[1.0, 2.0], [2.0, 4.0]])

    def test_logdet(self):
        self.assertAlmostEqual(M.logdet([[4.0, 1.0], [1.0, 3.0]]), math.log(11.0), places=14)
        a = [[2.0, 1.0, 0.5], [1.0, 3.0, 0.2], [0.5, 0.2, 1.5]]
        det = (2 * (3 * 1.5 - 0.2 * 0.2) - 1 * (1 * 1.5 - 0.2 * 0.5) + 0.5 * (1 * 0.2 - 3 * 0.5))
        self.assertAlmostEqual(M.logdet(a), math.log(det), places=13)
        # a row swap is needed here, and the determinant is still positive
        self.assertAlmostEqual(M.logdet([[0.0, 1.0], [-1.0, 0.0]]), 0.0, places=15)
        with self.assertRaises(ValueError):
            M.logdet([[0.0, 1.0], [1.0, 0.0]])
        with self.assertRaises(ValueError):
            M.logdet([[-1.0, 0.0], [0.0, 2.0]])

    def test_blocks(self):
        z = M.blockdiag([[[1.0, 2.0], [3.0, 4.0]], [[5.0]]], [[0, 2], [1]], 3)
        self.assertEqual(z, [[1.0, 0.0, 2.0], [0.0, 5.0, 0.0], [3.0, 0.0, 4.0]])
        self.assertEqual(M.sub(z, [0, 2]), [[1.0, 2.0], [3.0, 4.0]])


class SteadyState(unittest.TestCase):
    def test_scalar(self):
        for a in (0.2, -0.6, 0.9):
            self.assertAlmostEqual(M.steady([[a]], [[2.0]])[0][0], 2.0 / (1 - a * a), places=12)

    def test_residual_and_symmetry(self):
        A = [[0.3, -0.2, 0.1], [0.25, 0.1, -0.3], [0.0, 0.2, 0.4]]
        SE = [[1.0, 0.3, -0.2], [0.3, 2.0, 0.1], [-0.2, 0.1, 0.7]]
        S = M.steady(A, SE)
        res = M.add(M.add(S, M.mul(M.mul(A, S), M.tr(A)), -1.0), SE, -1.0)
        self.assertLess(max(abs(x) for r in res for x in r), 1e-13)
        self.assertEqual(S, M.tr(S))

    def test_paper_structure_other_a(self):
        # A = a J with J the all-ones 2x2: along (1,1) the variance is (1+c)/(1-4a^2), along (1,-1) it is 1-c
        for a, c in ((0.3, 0.5), (0.1, 0.8), (0.45, 0.2)):
            S = M.steady([[a, a], [a, a]], [[1.0, c], [c, 1.0]])
            su, sv = (1 + c) / (1 - 4 * a * a), 1 - c
            self.assertTrue(close(S, [[(su + sv) / 2, (su - sv) / 2], [(su - sv) / 2, (su + sv) / 2]], 1e-12))


class Quantities(unittest.TestCase):
    def test_scalar_closed_form(self):
        for a in (0.2, 0.55, -0.8):
            S, C, Sp = M.system([[a]], [[1.0]])
            f = M.istar_fn(S, C, [[0]])
            s = 1 / (1 - a * a)
            self.assertAlmostEqual(M.mutual_info(S, Sp), -0.5 * math.log(1 - a * a), places=12)
            for beta in (0.0, 0.3, 1.0, 1.7, 3.0):
                Q = 1 / s + beta * a * a
                want = 0.5 * s * (beta - beta * beta * a * a / Q) + 0.5 * math.log(Q * s) - beta / 2
                self.assertAlmostEqual(f(beta), want, places=12)
            beta, best = M.maximise(f)
            self.assertAlmostEqual(beta, 1.0, places=6)
            self.assertAlmostEqual(best, -0.5 * math.log(1 - a * a), places=12)

    def test_istar_at_zero(self):
        A = [[0.2, 0.3, 0.0], [-0.1, 0.25, 0.2], [0.3, 0.0, 0.1]]
        SE = [[1.0, 0.4, 0.1], [0.4, 1.0, 0.2], [0.1, 0.2, 1.0]]
        S, C, _ = M.system(A, SE)
        self.assertAlmostEqual(M.istar_fn(S, C, [[0], [1, 2]])(0.0), 0.0, places=13)

    def test_mutual_info_other_a(self):
        # the paper's structure at a = 0.3: I = -(1/2) log(1 - 4a^2) whatever c is
        for c in (0.0, 0.5, 0.9):
            m = M.measures(*M.paper_model(0.3, c))
            self.assertAlmostEqual(m["I"], -0.5 * math.log(1 - 4 * 0.09), places=11)

    def test_phi_I_closed_form_other_a(self):
        # each unit alone: I(M) = -(1/2) log(1 - (a s_u / s_11)^2), s_11 = (s_u + s_v)/2
        for a, c in ((0.3, 0.97), (0.2, 0.6)):
            su, sv = (1 + c) / (1 - 4 * a * a), 1 - c
            r = a * su / ((su + sv) / 2)
            want = -0.5 * math.log(1 - 4 * a * a) - 2 * (-0.5 * math.log(1 - r * r))
            self.assertAlmostEqual(M.measures(*M.paper_model(a, c))["phi_I"], want, places=10)
        self.assertLess(M.measures(*M.paper_model(0.3, 0.97))["phi_I"], 0)

    def test_no_information_three_units(self):
        # A = 0: nothing passes from past to present, so I = 0, I*(beta) = 0 for every beta, Phi_I = 0 and
        # Phi_H = sum (1/2) log SE_ii - (1/2) log |SE|
        SE = [[1.0, 0.5, 0.2], [0.5, 2.0, -0.3], [0.2, -0.3, 1.5]]
        A = M.zeros(3)
        S, C, _ = M.system(A, SE)
        f = M.istar_fn(S, C, [[0, 2], [1]])
        for beta in (0.0, 0.5, 1.0, 4.0):
            self.assertAlmostEqual(f(beta), 0.0, places=12)
        m = M.measures(A, SE, [[0], [1], [2]])
        self.assertAlmostEqual(m["I"], 0.0, places=13)
        self.assertAlmostEqual(m["phistar"], 0.0, places=12)
        self.assertAlmostEqual(m["phi_I"], 0.0, places=13)
        want = 0.5 * (math.log(1.0) + math.log(2.0) + math.log(1.5)) - 0.5 * M.logdet(SE)
        self.assertAlmostEqual(m["phi_H"], want, places=12)
        self.assertGreater(m["phi_H"], 0)

    def test_matched_decoding(self):
        st = M.Stream(SEED, "tests/matched")
        for _ in range(25):
            A, SE, _ = M.draw_system(st)
            n = len(A)
            m = M.measures(A, SE, [list(range(n))])
            self.assertLess(abs(m["phistar"]), 1e-9)
            self.assertAlmostEqual(m["beta"], 1.0, places=5)
            self.assertAlmostEqual(m["phi_I"], 0.0, places=12)
            self.assertAlmostEqual(m["phi_H"], 0.0, places=12)

    def test_independent_parts(self):
        st = M.Stream(SEED, "tests/independent")
        for _ in range(25):
            A, SE, parts = M.draw_system(st, independent=True)
            m = M.measures(A, SE, parts)
            self.assertLess(abs(m["phistar"]), 1e-9)
            self.assertLess(abs(m["phi_I"]), 1e-9)
            self.assertLess(abs(m["phi_H"]), 1e-9)

    def test_partition_order_irrelevant(self):
        A = [[0.2, 0.3, 0.0, 0.1], [-0.1, 0.25, 0.2, 0.0], [0.3, 0.0, 0.1, -0.2], [0.0, 0.1, 0.2, 0.3]]
        SE = M.add(M.eye(4), [[0.0, 0.3, 0.1, 0.0], [0.3, 0.0, 0.2, 0.1], [0.1, 0.2, 0.0, 0.0], [0.0, 0.1, 0.0, 0.0]])
        a = M.measures(A, SE, [[0, 3], [1, 2]])
        b = M.measures(A, SE, [[2, 1], [3, 0]])
        for k in ("I", "phistar", "phi_I", "phi_H"):
            self.assertAlmostEqual(a[k], b[k], places=11)


class Search(unittest.TestCase):
    def test_known_maxima(self):
        beta, best = M.maximise(lambda b: -(b - 2.5) ** 2 + 1.0)
        self.assertAlmostEqual(beta, 2.5, places=6)
        self.assertAlmostEqual(best, 1.0, places=12)
        beta, best = M.maximise(lambda b: 3.0 - 0.001 * (b - 700.0) ** 2)
        self.assertAlmostEqual(beta, 700.0, places=3)
        self.assertEqual(M.maximise(lambda b: -b), (0.0, 0.0))

    def test_against_grid_and_concavity(self):
        st = M.Stream(SEED, "tests/search")
        for _ in range(10):
            A, SE, parts = M.draw_system(st)
            S, C, _ = M.system(A, SE)
            f = M.istar_fn(S, C, parts)
            beta, best = M.maximise(f)
            top = 4 * max(beta, 1e-3)
            vals = [f(top * j / 200) for j in range(201)]
            self.assertLessEqual(max(vals), best + 1e-12)
            self.assertTrue(all(vals[j - 1] - 2 * vals[j] + vals[j + 1] <= 1e-11 for j in range(1, 200)))


class Drawn(unittest.TestCase):
    def test_partitions_uniform(self):
        st = M.Stream(SEED, "tests/partitions")
        counts = {}
        for _ in range(7000):
            parts = M.draw_partition(st, 4, 2)
            self.assertEqual(sorted(i for p in parts for i in p), [0, 1, 2, 3])
            self.assertTrue(all(parts))
            key = frozenset(frozenset(p) for p in parts)
            counts[key] = counts.get(key, 0) + 1
        self.assertEqual(len(counts), 7)   # S(4, 2) = 7
        self.assertTrue(all(abs(v - 1000) < 150 for v in counts.values()), counts)

    def test_systems(self):
        st = M.Stream(SEED, "tests/systems")
        sizes = set()
        for _ in range(60):
            A, SE, parts = M.draw_system(st)
            n = len(A)
            sizes.add(n)
            self.assertTrue(2 <= n <= 6 and 2 <= len(parts) <= n)
            fro = math.sqrt(sum(x * x for r in A for x in r))
            self.assertTrue(0.1 - 1e-12 <= fro <= 0.95 + 1e-12)
            self.assertTrue(math.isfinite(M.logdet(SE)))
            self.assertTrue(all(SE[i][j] == SE[j][i] for i in range(n) for j in range(n)))
        self.assertEqual(sizes, {2, 3, 4, 5, 6})

    def test_independent_systems_block_diagonal(self):
        st = M.Stream(SEED, "tests/blocks")
        for _ in range(20):
            A, SE, parts = M.draw_system(st, independent=True)
            where = {i: p for p, idx in enumerate(parts) for i in idx}
            n = len(A)
            for i in range(n):
                for j in range(n):
                    if where[i] != where[j]:
                        self.assertEqual(A[i][j], 0.0)
                        self.assertEqual(SE[i][j], 0.0)


class Run(unittest.TestCase):
    def test_refused_seed(self):
        work = tempfile.mkdtemp()
        try:
            with self.assertRaises(M.Refused):
                M.run("nothex", results=os.path.join(work, "results"))
            self.assertFalse(os.path.exists(os.path.join(work, "results")))
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def test_test_length(self):
        self.assertLessEqual(len(M.TEST), 600)

    def test_stream(self):
        a, b = M.Stream(SEED, "x"), M.Stream(SEED, "x")
        self.assertEqual([a.below(100) for _ in range(5)], [b.below(100) for _ in range(5)])
        u = [M.Stream(SEED, "y").uniform(-1, 1) for _ in range(3)]
        self.assertTrue(all(-1 <= x < 1 for x in u))


if __name__ == "__main__":
    unittest.main()
