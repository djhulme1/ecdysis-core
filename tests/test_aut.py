"""Burichenko's automorphism groups (mm/aut.py): the reading of printed definitions and its refusals; <m,n,p> and the
standard algorithms; the normal form of a term; inverses over the rationals and over GF(q); the isomorphism types on
groups whose type is known; the search on Strassen's algorithm (S3 x S3, of order 36) and its refusal of the standard
algorithm, whose torus of symmetries no rank-one terms can fix; and, with the e-print at inputs/ (or AUT_INPUTS), the
three printed algorithms, each in both forms.

Run with: python3 -m unittest tests.test_aut
"""

import importlib.util
import itertools
import os
import sys
import unittest
from fractions import Fraction as F

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("mm_aut", os.path.join(HERE, "..", "mm", "aut.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)

INPUTS = os.environ.get("AUT_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = os.path.isfile(os.path.join(INPUTS, M.EPRINT[0]))

STRASSEN_COMP = r"""Consider the following products:
$$ p_1=x_{11}(y_{12}+y_{22}),\quad p_2=(x_{11}-x_{12})
y_{22},\quad  p_3=(-x_{21}+x_{22})y_{11}, $$
$$p_4=x_{22}(y_{11}+y_{21}),\quad p_5=(x_{11}+x_{22})
(y_{11}+y_{22}),$$
$$ p_6=(x_{11}+x_{21})(y_{11}-y_{12}),\quad p_7=(x_{12}
+x_{22})(y_{21}-y_{22}).$$
Next, take linear combinations
$$ z_{11}=-p_2-p_4+p_5+p_7,\quad z_{12}=p_1-p_2,$$
$$ z_{21}=-p_3+p_4,\quad z_{22}=-p_1-p_3+p_5-p_6.$$
"""

STRASSEN_TENS = r""" && e_{11}\ot(e_{12}+e_{22})\ot(e_{21}-e_{22}),\
(e_{11}-e_{12})\ot e_{22}\ot(-e_{11}-e_{21}),\\
&&  (-e_{21}+e_{22})\ot e_{11}\ot(-e_{12}-e_{22}),\
e_{22}\ot(e_{11}+e_{21})\ot(-e_{11}+e_{12}),\\
&& (e_{11}+e_{22})\ot(e_{11}+e_{22})\ot(e_{11}+e_{22}),\
(e_{11}+e_{21})\ot(e_{11}-e_{12})\ot(-e_{22}),\\
&&  (e_{12}+e_{22})\ot(e_{21}-e_{22})\ot e_{11}\ """


def unit(r, c, i, j):
    return tuple(tuple(int((u, v) == (i, j)) for v in range(c)) for u in range(r))


def standard(fmt):
    m, n, p = fmt
    return [(unit(m, n, i, j), unit(n, p, j, k), unit(p, m, k, i))
            for i in range(m) for j in range(n) for k in range(p)]


def perm_group(gens):
    return M.closure([tuple(g) for g in gens])


class Reading(unittest.TestCase):
    def test_strassen_both_forms(self):
        comp = M.computational_terms(STRASSEN_COMP, (2, 2, 2), "strassen")
        tens = M.tensor_terms(STRASSEN_TENS, (2, 2, 2), "strassen")
        self.assertEqual(len(comp), 7)
        self.assertEqual(len(tens), 7)
        self.assertEqual(tens[0], (((1, 0), (0, 0)), ((0, 1), (0, 1)), ((0, 0), (1, -1))))
        for a, b in zip(comp, tens):
            self.assertEqual(M.normal(M.term_to_field(a, 0), 0), M.normal(M.term_to_field(b, 0), 0))
        self.assertEqual(M.tensor([M.term_to_field(t, 0) for t in tens]), M.mnp_tensor((2, 2, 2)))

    def test_refusals(self):
        with self.assertRaises(M.Refused):                      # a coefficient other than a sign
            M.computational_terms(STRASSEN_COMP.replace("p_1=x_{11}", "p_1=2x_{11}"), (2, 2, 2), "strassen")
        with self.assertRaises(M.Refused):                      # a formula missing
            M.computational_terms(STRASSEN_COMP.replace("z_{21}=-p_3+p_4,\\quad ", ""), (2, 2, 2), "strassen")
        with self.assertRaises(M.Refused):                      # an index outside the matrix
            M.tensor_terms(STRASSEN_TENS.replace("e_{11}\\ot(e_{12}", "e_{13}\\ot(e_{12}", 1), (2, 2, 2),
                           "strassen")
        with self.assertRaises(M.Refused):                      # two factors only
            M.tensor_terms(STRASSEN_TENS.replace("\\ot e_{11}\\ ", " e_{11}\\ "), (2, 2, 2), "strassen")
        with self.assertRaises(M.Refused):
            M.block("abc abc", "abc", "c")

    def test_definitions_split_displays(self):
        d = M.definitions(r"$$t_{19}=e_{12}\ot e_{21}\ot e_{11}\,,\quad t_{20}=e_{23}" "\n" r"\ot e_{32}\ot e_{22}\,,$$")
        self.assertEqual([x[:2] for x in d], [("t", "19"), ("t", "20")])
        self.assertEqual(d[1][2], "e_{23}\\ote_{32}\\ote_{22}")
        with self.assertRaises(M.Refused):
            M.definitions(r"$$ X=1, p_1=x_{11}y_{11} $$")


class Tensors(unittest.TestCase):
    def test_standard_algorithms_and_permutations_of_factors(self):
        for fmt in ((2, 2, 2), (3, 2, 3), (3, 3, 3), (2, 3, 4)):
            with self.subTest(fmt=fmt):
                std = standard(fmt)
                self.assertEqual(M.tensor(std), M.mnp_tensor(fmt))
                self.assertNotEqual(M.tensor(std[1:]), M.mnp_tensor(fmt))
                for name, rho in M.outer_parts(fmt).items():
                    self.assertEqual(M.tensor([rho(t) for t in std]), M.mnp_tensor(fmt), name)
        self.assertEqual(sorted(M.outer_parts((3, 2, 3))), ["(12)", "e"])
        self.assertEqual(len(M.outer_parts((3, 3, 3))), 6)
        self.assertEqual(sorted(M.outer_parts((2, 3, 4))), ["e"])

    def test_normal_form(self):
        a = ((F(2), F(0)), (F(0), F(4)))
        t = (a, a, a)
        u = (M.scale(a, F(3), 0), M.scale(a, F(1, 6), 0), M.scale(a, F(2), 0))
        self.assertEqual(M.normal(t, 0), M.normal(u, 0))
        self.assertNotEqual(M.normal(t, 0), M.normal((M.scale(a, F(2), 0), a, a), 0))
        b = ((1, 0), (0, 2))
        self.assertEqual(M.normal((b, b, b), 5), M.normal((M.scale(b, 3, 5), M.scale(b, 2, 5), b), 5))  # 3 * 2 = 1

    def test_inverse(self):
        a = ((F(0), F(-1)), (F(1), F(-1)))
        ai = M.inverse(a, 0)
        self.assertEqual(M.mul(a, ai, 0), M.eye(2, 0))
        self.assertEqual(ai, ((F(-1), F(1)), (F(-1), F(0))))           # the paper's d^-1
        b = ((1, 2, 0), (0, 1, 3), (4, 0, 2))                           # determinant 26, a unit mod 5
        self.assertEqual(M.mul(b, M.inverse(b, 5), 5), M.eye(3, 5))
        self.assertIsNone(M.inverse(((1, 2, 0), (0, 1, 3), (4, 0, 1)), 5))     # determinant 25
        self.assertIsNone(M.inverse(((F(1), F(2)), (F(2), F(4))), 0))
        self.assertIsNone(M.inverse(((1, 1), (1, 1)), 2))


class Types(unittest.TestCase):
    S4 = perm_group([(1, 2, 3, 0), (1, 0, 2, 3)])
    A4 = perm_group([(1, 2, 0, 3), (1, 0, 3, 2)])
    S3Z2 = perm_group([(1, 2, 0, 3, 4), (1, 0, 2, 3, 4), (0, 1, 2, 4, 3)])
    Z12 = perm_group([(1, 2, 3, 0, 5, 6, 4)])
    Z2A4 = perm_group([(1, 2, 0, 3, 4, 5), (1, 0, 3, 2, 4, 5), (0, 1, 2, 3, 5, 4)])
    S3S3 = perm_group([(1, 2, 0, 3, 4, 5), (1, 0, 2, 3, 4, 5), (0, 1, 2, 4, 5, 3), (0, 1, 2, 4, 3, 5)])
    S3Z6 = perm_group([(1, 2, 0, 3, 4, 5, 6, 7), (1, 0, 2, 3, 4, 5, 6, 7), (0, 1, 2, 4, 3, 5, 6, 7),
                       (0, 1, 2, 3, 4, 6, 7, 5)])

    def test_orders(self):
        self.assertEqual([len(g) for g in (self.S4, self.A4, self.S3Z2, self.Z12, self.Z2A4, self.S3S3, self.S3Z6)],
                         [24, 12, 12, 12, 24, 36, 36])
        self.assertTrue(all(M.is_group(g) for g in (self.S4, self.S3Z2, self.S3S3)))

    def test_s4(self):
        self.assertTrue(M.is_s4(self.S4))
        self.assertFalse(M.is_s4(self.Z2A4))
        self.assertFalse(M.is_s4(self.A4))

    def test_s3z2(self):
        self.assertTrue(M.is_s3z2(self.S3Z2))
        self.assertFalse(M.is_s3z2(self.A4))
        self.assertFalse(M.is_s3z2(self.Z12))

    def test_s3s3(self):
        self.assertTrue(M.is_s3s3(self.S3S3))
        self.assertFalse(M.is_s3s3(self.S3Z6))

    def test_order_of_a_permutation(self):
        self.assertEqual(M.order((1, 2, 0, 4, 3)), 6)
        self.assertEqual(M.order((0, 1, 2)), 1)


class Search(unittest.TestCase):
    def test_strassen_s3_by_s3(self):
        terms = [M.term_to_field(t, 0) for t in M.tensor_terms(STRASSEN_TENS, (2, 2, 2), "strassen")]
        g = M.group_report(terms, (2, 2, 2), 0)
        self.assertEqual(g["order"], 36)
        self.assertTrue(g["faithful"] and g["closed"])
        self.assertEqual(set(g["parts"].values()), {6})
        self.assertTrue(M.is_s3s3(g["perms"]))

    def test_the_standard_algorithm_is_refused(self):
        std = [M.term_to_field(t, 0) for t in standard((2, 2, 2))]
        self.assertIsNone(M.automorphisms(std, (2, 2, 2), 0))

    def test_a_moved_algorithm_keeps_its_group(self):
        terms = [M.term_to_field(t, 0) for t in M.tensor_terms(STRASSEN_TENS, (2, 2, 2), "strassen")]
        a = ((F(1), F(1)), (F(0), F(1)))
        b = ((F(2), F(0)), (F(1), F(1)))
        c = ((F(0), F(1)), (F(1), F(3)))
        invs = tuple(M.inverse(x, 0) for x in (a, b, c))
        moved = [M.act((a, b, c), invs, t, 0) for t in terms]
        self.assertEqual(M.tensor(moved), M.mnp_tensor((2, 2, 2)))
        self.assertEqual(M.group_report(moved, (2, 2, 2), 0)["order"], 36)

    def test_over_gf3(self):
        terms = [M.term_to_field(t, 3) for t in M.tensor_terms(STRASSEN_TENS, (2, 2, 2), "strassen")]
        self.assertEqual(M.tensor(terms, 3), M.target_tensor((2, 2, 2), 3))
        g = M.group_report(terms, (2, 2, 2), 3)
        self.assertIsNotNone(g)
        self.assertTrue(g["faithful"] and g["closed"])


@unittest.skipUnless(HAVE, "the e-print is not at inputs/")
class EPrint(unittest.TestCase):
    def test_three_algorithms_in_both_forms(self):
        algs = M.read_all(M.load(INPUTS))
        for name, fmt in M.FORMATS.items():
            with self.subTest(name=name):
                tens, comp = algs[name]["tens"], algs[name]["comp"]
                self.assertEqual(len(tens), M.SIZES[name])
                self.assertEqual(len(comp), M.SIZES[name])
                q0 = [M.term_to_field(t, 0) for t in tens]
                self.assertEqual(M.tensor(q0), M.mnp_tensor(fmt))
                for a, b in zip(tens, comp):
                    self.assertEqual(M.normal(M.term_to_field(a, 0), 0), M.normal(M.term_to_field(b, 0), 0))

    def test_the_paper_generators_preserve_hopcroft(self):
        algs = M.read_all(M.load(INPUTS))
        terms = [M.term_to_field(t, 0) for t in algs["hopcroft"]["tens"]]
        g, rels = M.hopcroft_generators()
        r = M.generators_report(terms, M.FORMATS["hopcroft"], g, rels, [], M.HOP_ACTIONS)
        self.assertEqual((r["preserve"], r["relations"], r["actions"]), (3, 6, 16))


if __name__ == "__main__":
    unittest.main()
