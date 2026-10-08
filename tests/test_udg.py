"""Heule's unit-distance graph check: exact arithmetic in Q(sqrt3, sqrt5, sqrt11), the coordinate parser and its
refusals, the Moser spindle (a 4-chromatic unit-distance graph in the same field) through the geometry and the
colouring formulas, the symmetry-breaking triangle, and the forward RUP checker on small formulas.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import itertools
import os
import unittest
from fractions import Fraction as F

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("udg_check", os.path.join(HERE, "..", "udg", "check.py"))
U = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(U)
Q = U.Q3

# The Moser spindle: two rhombi of unit equilateral triangles at the origin, their far tips one apart.
MOSER = """{0, 0}
{Sqrt[3]/2, 1/2}
{Sqrt[3]/2, -1/2}
{Sqrt[3], 0}
{(5*Sqrt[3] - Sqrt[11])/12, (Sqrt[33] + 5)/12}
{(5*Sqrt[3] + Sqrt[11])/12, (Sqrt[33] - 5)/12}
{5*Sqrt[3]/6, Sqrt[33]/6}
"""
MOSER_EDGES = [(1, 2), (1, 3), (2, 3), (2, 4), (3, 4), (1, 5), (1, 6), (5, 6), (5, 7), (6, 7), (4, 7)]
MOSER_FILE = "p edge 7 11\n" + "".join(f"e {u} {v}\n" for u, v in MOSER_EDGES)


class Field(unittest.TestCase):
    def test_products_and_radicals(self):
        r3, r5, r11 = Q.sqrt(3), Q.sqrt(5), Q.sqrt(11)
        self.assertEqual(r3 * r3, Q.rational(3))
        self.assertEqual(Q.sqrt(15) * Q.sqrt(33), Q({55: 3}))
        self.assertEqual(r3 * r5 * r11, Q.sqrt(165))
        self.assertEqual(Q.sqrt(F(11, 3)), Q({33: F(1, 3)}))
        self.assertEqual(Q.sqrt(12), Q({3: 2}))
        self.assertEqual(Q.sqrt(F(1, 4)), Q.rational(F(1, 2)))

    def test_inverses(self):
        one = Q.rational(1)
        for y in (Q({3: 32}), Q({1: 1, 3: 1, 5: 1, 11: 1}), Q({1: -35, 5: 3, 33: 7, 165: 1}), Q({55: F(2, 7), 15: -1})):
            with self.subTest(y=y.key()):
                self.assertEqual(y * y.inverse(), one)
        with self.assertRaises(U.Refused):
            Q().inverse()

    def test_outside_the_field_is_refused(self):
        for r in (2, 7, F(3, 2), 0, -3):
            with self.subTest(r=r), self.assertRaises(U.Refused):
                Q.sqrt(r)


class Points(unittest.TestCase):
    def test_lines_as_the_file_writes_them(self):
        x, y = U.parse_point("{Sqrt[11/3]/2, -1/(2*Sqrt[3])}")
        self.assertEqual((x, y), (Q({33: F(1, 6)}), Q({3: F(-1, 6)})))
        x, y = U.parse_point("{(-21 - 15*Sqrt[5] - 7*Sqrt[33] + 3*Sqrt[165])/96, "
                             "-(-35 + 3*Sqrt[5] + 7*Sqrt[33] + Sqrt[165])/(32*Sqrt[3])}")
        self.assertAlmostEqual(float(x), (-21 - 15 * 5 ** .5 - 7 * 33 ** .5 + 3 * 165 ** .5) / 96, places=12)
        self.assertAlmostEqual(float(y), -(-35 + 3 * 5 ** .5 + 7 * 33 ** .5 + 165 ** .5) / (32 * 3 ** .5), places=12)

    def test_refusals(self):
        for bad in ("{1.5, 0}", "{x, 0}", "{1, 2, 3}", "{Sqrt[Sqrt[3]], 0}", "{Sqrt[2], 0}", "{1/0, 0}", "{2^2, 0}",
                    "{1, 0} 1", "(1, 0)", "{Sqrt(3), 0}"):
            with self.subTest(line=bad), self.assertRaises(U.Refused):
                U.parse_point(bad)


class Moser(unittest.TestCase):
    def setUp(self):
        self.points = U.parse_points(MOSER)
        self.edges = U.parse_edges(MOSER_FILE, 7)

    def test_unit_edges_exactly(self):
        self.assertEqual(U.unit_edges(self.points, self.edges), 11)
        self.assertEqual(U.unlisted_unit_pairs(self.points, self.edges), [])
        moved = list(self.points)
        moved[1] = (moved[1][0] + Q.rational(F(1, 10 ** 9)), moved[1][1])
        self.assertLess(U.unit_edges(moved, self.edges), 11)
        self.assertEqual(U.unlisted_unit_pairs(self.points, self.edges[:-1]), [(4, 7)])

    def test_colouring_formula_means_proper_colourings(self):
        for k, colourable in ((3, False), (4, True)):
            clauses = U.colouring_clauses(7, self.edges, k)
            found = False
            for colours in itertools.product(range(1, k + 1), repeat=7):
                true = {k * v + c for v, c in enumerate(colours)}
                sat = all(any((lit > 0) == (abs(lit) in true) for lit in c) for c in clauses)
                self.assertEqual(sat, U.proper(list(colours), self.edges))
                found = found or sat
            self.assertEqual(found, colourable, k)

    def test_restricted_formula_and_model_reading(self):
        clauses = U.colouring_clauses(7, self.edges, 3, vertices=[1, 2, 3, 4])
        self.assertEqual(len(clauses), 4 + 3 * 5)
        self.assertEqual(U.colours_from_model({1, 5, 9, 2}, 3, 3), [1, 2, 3])
        self.assertEqual(U.colours_from_model({1}, 2, 3), [1, None])

    def test_symmetry_breaking_triangle(self):
        self.assertTrue(U.triangle_units([1, 6, 11], self.edges, 4))     # vertices 1, 2, 3 in colours 1, 2, 3
        self.assertFalse(U.triangle_units([1, 6, 15], self.edges, 4))    # vertex 4 is not adjacent to vertex 1
        self.assertFalse(U.triangle_units([1, 5, 11], self.edges, 4))    # vertices 1 and 2 both in colour 1
        self.assertFalse(U.triangle_units([1, 6], self.edges, 4))

    def test_edge_file_refusals(self):
        for bad in ("p edge 8 11\n" + MOSER_FILE.split("\n", 1)[1], MOSER_FILE + "e 1 2\n", MOSER_FILE + "e 3 3\n",
                    MOSER_FILE.replace("p edge 7 11", "p edge 7 12"), MOSER_FILE + "x 1 2\n"):
            with self.subTest(text=bad[-20:]), self.assertRaises(U.Refused):
                U.parse_edges(bad, 7)


class Proofs(unittest.TestCase):
    def test_a_refutation(self):
        clauses = [(1, 2), (1, -2), (-1, 2), (-1, -2)]
        self.assertEqual(U.rup_check(2, clauses, [(False, (1,)), (True, (1, 2)), (False, ())]), (2, 1, True))

    def test_a_lemma_not_implied_stops_the_check(self):
        self.assertEqual(U.rup_check(2, [(1, 2)], [(False, (1,))]), (1, 0, False))
        self.assertEqual(U.rup_check(2, [(1, 2), (-1, 2)], [(False, ())]), (1, 0, False))

    def test_long_clauses_through_their_watches(self):
        clauses = [(1, 2, 3), (-1, 4), (-2, 4), (-3, 4)]
        self.assertEqual(U.rup_check(4, clauses, [(False, (4,))]), (1, 1, False))
        self.assertEqual(U.rup_check(4, clauses, [(False, (-4,))]), (1, 0, False))
        self.assertEqual(U.rup_check(7, clauses + [(-4, 5, 6, 7), (-5,), (-6,), (-7,)], [(False, ())]), (1, 0, True))
        self.assertEqual(U.rup_check(3, [(1, 2, 3), (-1,), (-2,), (-3,)], []), (0, 0, True))

    def test_drat_lines(self):
        self.assertEqual(U.parse_drat(b"1 -2 0\nd 1 -2 0\n0\n", 2), [(False, (1, -2)), (True, (1, -2)), (False, ())])
        for bad in (b"1 2\n", b"1 3 0\n", b"1 a 0\n", b"d\n"):
            with self.subTest(text=bad), self.assertRaises(U.Refused):
                U.parse_drat(bad, 2)


if __name__ == "__main__":
    unittest.main()
