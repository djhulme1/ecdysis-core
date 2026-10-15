"""Grenet's matrix (bdc/grenet.py): the matrix's shape (sizes, arcs, loops, the planted fault), the entries' check,
the cycle-cover expansion against the Leibniz sum, the modular determinant against an exact one, Ryser's formula,
the corollary's count, and the seed's points. No determinant of the paper's matrix is computed here.

Run with: python3 -m unittest tests.test_grenet
"""

import importlib.util
import itertools
import math
import os
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("bdc_grenet", os.path.join(HERE, "..", "bdc", "grenet.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "ab" * 32


def leibniz_terms(rows, n):
    want = {}
    for q in itertools.permutations(range(n)):
        coef, mono = 1, []
        for u in range(n):
            e = rows[u].get(q[u], 0)
            if isinstance(e, tuple):
                mono.append(e)
            else:
                coef *= e
        if coef:
            inv = sum(1 for a in range(n) for b in range(a + 1, n) if q[a] > q[b])
            key = tuple(sorted(mono))
            want[key] = want.get(key, 0) + (-1) ** inv * coef
    return {k: c for k, c in want.items() if c}


class Shape(unittest.TestCase):
    def test_vertices(self):
        for n in range(2, 7):
            vs = M.vertices(n)
            self.assertEqual(len(vs), 2 ** n - 1)
            self.assertEqual(vs[0], frozenset())
            self.assertNotIn(frozenset(range(n)), vs)
            self.assertEqual([len(v) for v in vs], sorted(len(v) for v in vs))

    def test_arcs_and_loops(self):
        for n in range(2, 8):
            rows = M.grenet(n)
            arcs = sum(1 for r in rows for c, e in r.items() if isinstance(e, tuple))
            loops = [rows[u][u] for u in range(len(rows)) if u in rows[u]]
            self.assertEqual(arcs, n * 2 ** (n - 1))
            self.assertEqual(len(loops), 2 ** n - 2)
            self.assertNotIn(0, rows[0])
            self.assertEqual(loops.count(-1), n if n % 2 == 0 else 0)
            # every arc into the merged vertex comes from a set of size n - 1 and carries x_n,j
            into = [(u, e) for u, r in enumerate(rows) for c, e in r.items() if c == 0]
            self.assertEqual(len(into), n)
            self.assertTrue(all(e[0] == n for _, e in into))
            # the arcs out of the merged vertex carry x_1j
            self.assertEqual(sorted(e for c, e in rows[0].items()), [(1, j) for j in range(1, n + 1)])

    def test_even_fix_off(self):
        rows = M.grenet(4, even_fix=False)
        self.assertEqual({rows[u][u] for u in range(1, len(rows))}, {1})

    def test_fault(self):
        good = M.grenet(4)
        bad = M.grenet(4, fault=("arc", frozenset([0]), 1, 2))
        diff = [(u, c) for u in range(len(good)) for c in good[u] if good[u][c] != bad[u].get(c)]
        self.assertEqual(len(diff), 1)
        u, c = diff[0]
        self.assertEqual(good[u][c], (2, 2))
        self.assertEqual(bad[u][c], (2, 3))

    def test_entries_ok(self):
        rows = M.grenet(3)
        self.assertTrue(M.entries_ok(rows, 3))
        self.assertFalse(M.entries_ok(rows[:-1], 3))
        bad = [dict(r) for r in rows]
        bad[1][1] = 2
        self.assertFalse(M.entries_ok(bad, 3))
        bad = [dict(r) for r in rows]
        bad[0][1] = (4, 1)
        self.assertFalse(M.entries_ok(bad, 3))
        self.assertEqual(M.constants_of(M.grenet(3)), [1])
        self.assertEqual(M.constants_of(M.grenet(4)), [-1, 1])


class Expansion(unittest.TestCase):
    def test_against_leibniz(self):
        st = M.Stream(SEED, "test/expand")
        for n in (1, 2, 3, 4, 5, 6):
            for _ in range(4):
                cells = st.ints(n * n, 0, 9)
                rows = [dict() for _ in range(n)]
                for k, c in enumerate(cells):
                    u, v = divmod(k, n)
                    if c < 4:
                        rows[u][v] = (1 + c % 2, 1 + v % 3)
                    elif c < 7:
                        rows[u][v] = (-1, 1, 2)[c - 4]
                self.assertEqual(M.expand(rows), leibniz_terms(rows, n))

    def test_cycle_signs(self):
        # a 2-cycle and a 3-cycle of variables: signs -1 and +1
        two = [{1: (1, 2)}, {0: (2, 1)}]
        self.assertEqual(M.expand(two), {((1, 2), (2, 1)): -1})
        three = [{1: (1, 2)}, {2: (2, 3)}, {0: (3, 1)}]
        self.assertEqual(M.expand(three), {((1, 2), (2, 3), (3, 1)): 1})

    def test_permanent_terms(self):
        t = M.permanent_terms(3)
        self.assertEqual(len(t), 6)
        self.assertIn(((1, 1), (2, 2), (3, 3)), t)
        self.assertTrue(all(c == 1 for c in t.values()))


class Numbers(unittest.TestCase):
    def test_det_mod(self):
        st = M.Stream(SEED, "test/det")
        for size in (1, 2, 3, 7, 15):
            A = [[v - 100 for v in st.ints(size, 0, 200)] for _ in range(size)]
            self.assertEqual(M.det_mod(np.array(A, dtype=np.int64) % M.P), M.bareiss(A) % M.P)
        self.assertEqual(M.det_mod(np.zeros((3, 3), dtype=np.int64)), 0)
        self.assertEqual(M.bareiss([[0, 1], [1, 0]]), -1)

    def test_ryser(self):
        st = M.Stream(SEED, "test/ryser")
        for n in range(1, 6):
            X = [[v - 5 for v in st.ints(n, 0, 10)] for _ in range(n)]
            self.assertEqual(M.ryser(X), M.leibniz_per(X))
            self.assertEqual(M.ryser(X, M.P), M.leibniz_per(X) % M.P)

    def test_numeric(self):
        rows = [{0: (1, 2), 1: -1}, {1: 1}]
        A = M.numeric(rows, [[5, 7], [11, 13]])
        self.assertEqual(A.tolist(), [[7, M.P - 1], [0, 1]])

    def test_points(self):
        a = M.point(M.Stream(SEED, "x"), 3)
        b = M.point(M.Stream(SEED, "x"), 3)
        c = M.point(M.Stream(SEED, "y"), 3)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertTrue(all(0 <= v < M.P for r in a for v in r))

    def test_corollary_count(self):
        for n in range(2, 9):
            ops, _ = M.corollary(n)
            self.assertEqual(ops, sum((2 * i - 1) * math.comb(n, i) for i in range(2, n + 1)))

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not hex", results=os.path.join(HERE, "nonexistent-results"))

    def test_test_length(self):
        self.assertLessEqual(len(M.TEST), 600)


if __name__ == "__main__":
    unittest.main()
