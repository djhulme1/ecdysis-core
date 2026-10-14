"""Landsberg, Manivel & Ressayre's bound (bdc/lmr.py): the reader on archives built here and its refusals; Ryser's
permanent and the fraction-free determinant against the definitions; the modular and exact ranks on matrices of known
rank; the two Hessians against term-by-term derivatives and deleted-submatrix permanents at points that are not zeros;
the seeded zeros and rank-deficient points; the outputs and the seed refused. No Hessian rank at a zero of the
permanent or at a singular matrix is computed here, and the paper's source is not read.

Run with: python3 -m unittest discover -s tests -p test_lmr.py
"""

import importlib.util
import io
import itertools
import math
import os
import random
import tarfile
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("bdc_lmr", os.path.join(HERE, "..", "bdc", "lmr.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


def source(tex, name=M.MEMBER):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        raw = tex.encode("utf-8")
        info = tarfile.TarInfo(name)
        info.size = len(raw)
        tar.addfile(info, io.BytesIO(raw))
    return buf.getvalue()


def leibniz(A, signed):
    n, total = len(A), 0
    for sigma in itertools.permutations(range(n)):
        inv = sum(1 for x in range(n) for y in range(x + 1, n) if sigma[x] > sigma[y])
        sgn = -1 if (signed and inv % 2) else 1
        total += sgn * math.prod(A[i][sigma[i]] for i in range(n))
    return total


class Reading(unittest.TestCase):
    def test_statements(self):
        tex = "\n".join(M.REQUIRED + M.REPORTED).replace(" ", "\n   ")
        found = M.statements_found(M.tex_of(source(tex)))
        self.assertTrue(all(found.values()))
        with self.assertRaises(M.Refused):
            M.statements_found(M.tex_of(source(M.REQUIRED[1])))
        partial = M.statements_found("\n".join(M.REQUIRED))
        self.assertEqual(sum(partial.values()), len(M.REQUIRED))

    def test_archive(self):
        with self.assertRaises(M.Refused):
            M.tex_of(source("x", name="other.tex"))
        with self.assertRaises(M.Refused):
            M.tex_of(b"not a tar")

    def test_hash_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, M.INPUT[0]), "wb") as fh:
                fh.write(source("x"))
            with self.assertRaises(M.Refused):
                M.read_input(d)


class Arithmetic(unittest.TestCase):
    def test_permanent(self):
        self.assertEqual(M.permanent([]), 1)
        for k in range(1, 7):
            self.assertEqual(M.permanent([[1] * k for _ in range(k)]), math.factorial(k))
        rnd = random.Random(1)
        for k in range(1, 6):
            A = [[rnd.randint(-5, 5) for _ in range(k)] for _ in range(k)]
            self.assertEqual(M.permanent(A), leibniz(A, False))

    def test_determinant(self):
        rnd = random.Random(2)
        for k in range(1, 7):
            A = [[rnd.randint(-5, 5) for _ in range(k)] for _ in range(k)]
            self.assertEqual(M.bareiss_det(A), leibniz(A, True))
        self.assertEqual(M.bareiss_det([[0, 1], [1, 0]]), -1)

    def test_ranks(self):
        rnd = random.Random(3)
        for inner in (1, 2, 4):
            U = [[rnd.randint(-4, 4) for _ in range(inner)] for _ in range(6)]
            V = [[rnd.randint(-4, 4) for _ in range(6)] for _ in range(inner)]
            P = M.matmul(U, V)
            r = M.rank_exact(P)
            self.assertLessEqual(r, inner)
            self.assertEqual(M.rank_mod(P, M.PRIMES[0]), r)
        eye = [[int(i == j) for j in range(5)] for i in range(5)]
        self.assertEqual(M.rank_exact(eye), 5)
        self.assertEqual(M.full_rank(eye, 5), (5, f"mod {M.PRIMES[0]}"))
        self.assertEqual(M.rank_exact([[0] * 4 for _ in range(4)]), 0)
        self.assertEqual(M.full_rank([[2, 4], [1, 2]], 2), (1, "exact"))


class Hessians(unittest.TestCase):
    def test_against_derivatives(self):
        rnd = random.Random(4)
        A = [[rnd.randint(-6, 6) for _ in range(3)] for _ in range(3)]
        self.assertEqual(M.perm_hessian(A), M.term_by_term(A, False))
        self.assertEqual(M.det_hessian(A), M.term_by_term(A, True))
        for m in (4, 5):
            B = [[rnd.randint(-6, 6) for _ in range(m)] for _ in range(m)]
            H = M.perm_hessian(B)
            self.assertEqual(H, M.perm_hessian_minors(B))
            self.assertTrue(all(H[a][b] == H[b][a] for a in range(m * m) for b in range(m * m)))

    def test_points(self):
        st = M.Stream("ab" * 32, "t")
        for m in (3, 4):
            self.assertEqual(M.permanent(M.perm_point(st, m)), 0)
            self.assertEqual(M.permanent(M.mr_point(m)), 0)
        for n in (3, 4):
            self.assertEqual(M.rank_exact(M.det_point(st, n)), n - 1)
        self.assertEqual(M.rank_exact(M.diag_point(5)), 4)

    def test_stream(self):
        a, b = M.Stream("ab" * 32, "x"), M.Stream("ab" * 32, "x")
        self.assertEqual([a.between(-9, 9) for _ in range(5)], [b.between(-9, 9) for _ in range(5)])
        c, d = M.Stream("cd" * 32, "x"), M.Stream("ab" * 32, "x")
        self.assertNotEqual([c.below(10 ** 9) for _ in range(3)], [d.below(10 ** 9) for _ in range(3)])


class Verdict(unittest.TestCase):
    def test_outputs_named(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


if __name__ == "__main__":
    unittest.main()
