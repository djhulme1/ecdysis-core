"""Grochow & Moore's lattice decomposition (mm/gm.py): the e-print reader on an archive written here; the factors'
coordinates in the basis f_a against a direct computation with exact fractions; the tensor sums against a direct sum
on terms drawn here; the target tensor; and the checker on decompositions whose answer is known (Strassen's, the
standard one, and broken ones). The lattice decomposition itself is not summed here.

Run with: python3 -m unittest discover -s tests -p test_gm.py
"""

import importlib.util
import io
import os
import random
import tarfile
import tempfile
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("mm_gm", os.path.join(HERE, "..", "mm", "gm.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


def make_tar(files):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, text in files.items():
            data = text.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


class Reading(unittest.TestCase):
    def test_equation_and_statements(self):
        tex = ("intro\n\\begin{equation}\n\\label{eq:lattice}\n\\T_n =   x\n+ y \\, .\n\\end{equation}\n"
               "and \\sum_i \\ket{w_i}   = 0 here")
        data = make_tar({M.TEX: tex})
        got = M.tex_of(data)
        self.assertEqual(M.read_equation(got), "\\T_n = x + y \\, .")
        self.assertEqual(M.statements_found(got, ("\\sum_i \\ket{w_i} = 0", "absent")),
                         {"\\sum_i \\ket{w_i} = 0": True, "absent": False})
        with self.assertRaises(M.Refused):
            M.read_equation("\\begin{equation}\\label{eq:other} x \\end{equation}")
        with self.assertRaises(M.Refused):
            M.tex_of(make_tar({"other.tex": "x"}))

    def test_hash_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, M.EPRINT[0]), "wb") as fh:
                fh.write(make_tar({M.TEX: "x"}))
            with self.assertRaises(M.Refused):
                M.load(d)


class Coordinates(unittest.TestCase):
    def test_small_values(self):
        self.assertEqual(M.corner(2, 0), [2, -1])
        self.assertEqual(M.corner(2, 2), [-1, -1])
        self.assertEqual(M.covector(2, 1, 0), [-1, 1])
        self.assertEqual(M.covector(2, 2, 0), [-2, -1])
        self.assertEqual(M.identity_factor(2), [3, 0, 0, 3])

    def test_factor_against_definition(self):
        # |u_i><u_j - u_i| applied to f_b, read in the basis f (first n coordinates), with exact fractions
        for n in (2, 3, 4):
            def u(i):
                return [Fraction(1 if a == i else 0) - Fraction(1, n + 1) for a in range(n + 1)]

            def f(b):
                return [Fraction(1 if a == b else 0) - Fraction(1 if a == n else 0) for a in range(n + 1)]
            for i in range(n + 1):
                for j in range(n + 1):
                    if i == j:
                        continue
                    ui, d = u(i), [x - y for x, y in zip(u(j), u(i))]
                    want = []
                    for a in range(n):
                        for b in range(n):
                            image = [ui[c] * sum(dc * fc for dc, fc in zip(d, f(b))) for c in range(n + 1)]
                            self.assertEqual(sum(image), 0)            # the image lies in V
                            want.append(image[a] * (n + 1))
                    self.assertEqual(M.factor(n, i, j), [int(w) for w in want])
                    self.assertTrue(all(w.denominator == 1 for w in want))


class Sums(unittest.TestCase):
    def test_target(self):
        t = M.target(3, 5)
        self.assertEqual(int((t != 0).sum()), 27)
        self.assertEqual(int(t[0 * 3 + 1, 1 * 3 + 2, 2 * 3 + 0]), 5)
        self.assertEqual(int(t[0, 0, 1]), 0)

    def test_matrix_products_against_direct(self):
        rng = random.Random(1612)
        for n in (2, 3):
            terms = [tuple([rng.randrange(-4, 5) for _ in range(n * n)] for _ in range(3)) for _ in range(9)]
            self.assertTrue((M.tensor_sum(terms, n) == M.direct_sum(terms, n)).all())

    def test_checker_on_known_decompositions(self):
        self.assertTrue(M.holds(M.strassen_terms(True), 2, 1))
        self.assertFalse(M.holds(M.strassen_terms(False), 2, 1))
        for n in (2, 3, 4):
            std = M.standard_terms(n)
            self.assertEqual(len(std), n ** 3)
            self.assertTrue(M.holds(std, n, 1))
            self.assertFalse(M.holds(std[1:], n, 1))
            self.assertFalse(M.holds(std, n, 2))


class Machinery(unittest.TestCase):
    def test_outputs(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")

    def test_stream(self):
        a, b = M.Stream("cd" * 32, "x"), M.Stream("cd" * 32, "x")
        self.assertEqual([a.below(100) for _ in range(5)], [b.below(100) for _ in range(5)])


if __name__ == "__main__":
    unittest.main()
