"""Alper, Bogart & Velasco (bdc/abv.py): the TeX reader on a source written here, the dimension routes on ideals whose
dimensions are known, the polynomial determinant, Grenet's construction for n = 2 and the sizes for n = 4, and the
integer helpers. Nothing here computes the permanent's singular locus or Grenet's 7 x 7 determinant.

Run with (sympy needed, the scipy-notebook image): python3 -m unittest discover -s tests -p test_abv.py
"""

import gzip
import importlib.util
import io
import os
import tarfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("bdc_abv", os.path.join(HERE, "..", "bdc", "abv.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

MATRIX = (r"one can check that $$f = \det \left(\begin{array}{rrrrr}" "\n- y & z & 0 & 0 & 0 \\\\\n"
          r"0 & 0 & z & t & x \\ z & 0 & 1 & 0 & 0 \\ 0 & t & 0 & 1 & 0 \\ 0 & y & 0 & 0 & 1"
          "\n" r"\end{array}\right)$$ which implies")


def source(text, member=M.MEMBER):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        data = text.encode("utf-8")
        info = tarfile.TarInfo(member)
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    return gzip.compress(buf.getvalue())


def tex_with(statements):
    return "Some text.\n" + "\n\n".join(s.replace(" ", "  ") for s in statements) + "\n" + MATRIX + "\nMore."


class Reading(unittest.TestCase):
    def test_statements(self):
        tex = M.tex_of(source(tex_with(M.REQUIRED)))
        self.assertEqual(M.statements_found(tex), len(M.REQUIRED))
        with self.assertRaises(M.Refused):
            M.statements_found(tex_with(M.REQUIRED[1:]))
        with self.assertRaises(M.Refused):
            M.statements_found(tex_with(M.REQUIRED + M.REQUIRED[:1]))
        with self.assertRaises(M.Refused):
            M.tex_of(source("x", member="other.tex"))
        with self.assertRaises(M.Refused):
            M.tex_of(b"not gzip")

    def test_cubic_matrix(self):
        cells = M.cubic_matrix(tex_with(M.REQUIRED))
        self.assertEqual(cells[0][0], (True, "y"))
        self.assertEqual(cells[1][4], (False, "x"))
        self.assertTrue(M.cubic_check([[(False, "x"), (False, "0"), (False, "0"), (False, "0"), (False, "0")],
                                       [(False, "0"), (False, "1"), (False, "0"), (False, "0"), (False, "0")],
                                       [(False, "0"), (False, "0"), (False, "1"), (False, "0"), (False, "0")],
                                       [(False, "0"), (False, "0"), (False, "0"), (False, "1"), (False, "0")],
                                       [(False, "0"), (False, "0"), (False, "0"), (False, "0"), (False, "1")]])
                         is False)
        with self.assertRaises(M.Refused):
            M.cubic_matrix(tex_with(M.REQUIRED).replace("- y &", "2y &"))
        with self.assertRaises(M.Refused):
            M.cubic_matrix(tex_with(M.REQUIRED).replace(r"\begin{array}{rrrrr}", r"\begin{array}{rrrr}"))


class Polynomials(unittest.TestCase):
    def test_poly_det_small(self):
        x, y = M.var(0, 2), M.var(1, 2)
        one = M.const(1, 2)
        d = M.poly_det([[x, one], [one, y]], 2)
        self.assertEqual(d, {(1, 1): 1, (0, 0): -1})
        self.assertEqual(M.poly_det([[x, y], [x, y]], 2), {})

    def test_permanent_poly(self):
        p2 = M.permanent_poly(2)
        self.assertEqual(p2, {(1, 0, 0, 1): 1, (0, 1, 1, 0): 1})
        self.assertEqual(len(M.permanent_poly(4)), 24)

    def test_grenet_small(self):
        A, subsets = M.grenet(2)
        self.assertEqual(len(A), 3)
        self.assertEqual(subsets[0], frozenset())
        d = M.poly_det(A, 4)
        self.assertEqual(d, {k: -v for k, v in M.permanent_poly(2).items()})
        B, _ = M.grenet(4)
        self.assertEqual(len(B), 15)
        self.assertEqual(sum(1 for i in range(15) if B[i][i] == M.const(1, 16)), 14)

    def test_integers(self):
        X = [[2, -1, 0], [1, 3, 4], [0, 5, -2]]
        self.assertEqual(M.bareiss_det(X), M.det_by_permutations(X))
        self.assertEqual(M.perm_int([[1, 2], [3, 4]]), 10)
        self.assertEqual(M.rank_exact([[1, 2, 3], [2, 4, 6], [0, 1, 1]]), 2)
        self.assertEqual(M.evaluate({(2, 0): 3, (0, 1): -1}, (2, 5)), 7)
        a, b = M.Stream("ab" * 32, "t"), M.Stream("ab" * 32, "t")
        self.assertEqual(a.ints(10, -3, 3), b.ints(10, -3, 3))


class Dimensions(unittest.TestCase):
    def test_monomial_dim(self):
        self.assertEqual(M.monomial_dim([(1, 1, 0, 0), (0, 0, 1, 0)], 4), 2)
        self.assertEqual(M.monomial_dim([(1, 0, 0), (0, 1, 0), (0, 0, 1)], 3), 0)
        self.assertEqual(M.monomial_dim([], 3), 3)

    def test_left_kernel(self):
        kernel, rank = M.left_kernel([[1, -1], [2, -2], [0, 3]])
        self.assertEqual(rank, 2)
        self.assertEqual(len(kernel), 1)
        k = kernel[0]
        self.assertEqual([sum(k[i] * w[j] for i, w in enumerate([[1, -1], [2, -2], [0, 3]])) for j in range(2)],
                         [0, 0])

    def test_torus(self):
        self.assertEqual(M.torus_dim([((1, 1, 0), (0, 0, 2), 1)], 3)[0], 2)
        self.assertEqual(M.torus_dim([((1, 0), (0, 1), 1), ((2, 0), (0, 2), 1)], 2)[0], 0)
        self.assertEqual(M.torus_dim([((1, 0), (0, 1), 1), ((2, 0), (0, 2), -1)], 2)[0], 1)

    def test_groebner(self):
        import sympy
        x, y, z = sympy.symbols("x y z")
        self.assertEqual(M.groebner_codim([x * y, z], [x, y, z])[0], 2)
        self.assertEqual(M.groebner_codim([x * y, z], [x, y, z], 3)[0], 2)
        self.assertEqual(M.groebner_codim([x ** 2 + y ** 2, z], [x, y, z])[0], 2)
        polys, gens = M.sympy_jacobian(2, "det")
        self.assertEqual(M.groebner_codim(polys, gens)[0], 4)


class Machinery(unittest.TestCase):
    def test_test_and_outputs(self):
        self.assertLessEqual(len(M.TEST), 600)
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 64)

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


if __name__ == "__main__":
    unittest.main()
