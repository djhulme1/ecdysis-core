"""Exoo and Ismailescu's {1,2}-graph (udg/two_distance.py): the coordinates' exact distances; the reflections and the
paper's rotation by pi/3; the rotation by arccos(49/50) about a point, an isometry fixing its centre; the edge rule at
and beside 1 and 2; the reading of the TeX and its refusals; the colouring formula and the triangle; and, with the
e-print at inputs/ (or TWO_DISTANCE_INPUTS), the construction's counts against the paper's (no solver is run here).

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import io
import os
import tarfile
import unittest
from fractions import Fraction as F

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("udg_two_distance", os.path.join(HERE, "..", "udg", "two_distance.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

INPUTS = os.environ.get("TWO_DISTANCE_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = os.path.isfile(os.path.join(INPUTS, M.EPRINT[0]))


def P(*xs):
    return tuple(F(x) for x in xs)


class Distances(unittest.TestCase):
    def test_coordinates(self):
        self.assertEqual(M.sq144(P(0, 0, 12, 0), P(0, 0, 0, 0)), (144, 0))     # (0, 1): one apart
        self.assertEqual(M.sq144(P(12, 0, 0, 0), P(0, 0, 0, 0)), (432, 0))     # (sqrt3, 0): |p|^2 = 3
        self.assertEqual(M.sq144(P(1, 1, 0, 0), P(0, 0, 0, 0)), (14, 1))       # a sqrt33 part

    def test_edges_at_and_beside_one_and_two(self):
        pts = [P(0, 0, 0, 0), P(0, 0, 12, 0), P(0, 0, 24, 0), P(0, 0, 13, 0)]
        P_, one, two = M.edges(pts)
        self.assertEqual(len(one), 1 + 1)          # (0,0)-(0,1) and (0,1)-(0,2); (0,13/12) is 1/12 from (0,1)
        self.assertEqual(len(two), 1)              # (0,0)-(0,2)


class Maps(unittest.TestCase):
    def test_reflections_and_the_printed_rotation(self):
        p = P(2, -6, 0, 4)
        self.assertEqual(M.reflect_x(p), P(2, -6, 0, -4))
        self.assertEqual(M.reflect_y(p), P(-2, 6, 0, 4))
        q = p
        for _ in range(6):
            self.assertEqual(M.sq144(q, P(0, 0, 0, 0)), M.sq144(p, P(0, 0, 0, 0)))
            q = M.rotate60(q)
        self.assertEqual(q, p)                       # six turns of pi/3 come back
        unit = P(0, 0, 12, 0)                        # (0, 1) turned by pi/3 is (-sqrt3/2, 1/2)
        self.assertEqual(M.rotate60(unit), P(-6, 0, 6, 0))

    def test_the_turn_about_a_point(self):
        A = P(-2, 0, 0, -6)
        R = M.rotation_about(A, *M.THETA)
        self.assertEqual(R(A), A)
        pts = [P(8, 0, 0, 4), P(0, 0, 0, 0), P(-5, 3, -3, 3), P(3, 1, 2, -7)]
        for p in pts:
            for q in pts:
                self.assertEqual(M.sq144(R(p), R(q)), M.sq144(p, q))
        B = P(8, 0, 0, 4)
        self.assertEqual(M.sq144(A, B), (3600, 0))   # |AB| = 5
        self.assertEqual(M.sq144(B, R(B)), (144, 0))  # |BB'| = 1
        Rc = M.rotation_about(A, *M.CONTROL_ANGLE)
        self.assertEqual(M.sq144(Rc(A), Rc(B)), (3600, 0))
        self.assertNotEqual(M.sq144(B, Rc(B)), (144, 0))
        back = M.rotation_about(A, *M.MINUS_THETA)
        self.assertEqual(back(R(B)), B)


def fake_tex(drop=None, s_points=23):
    S = " ".join(f"[{i}, 0, 0, {2 * i}]," for i in range(s_points))
    extra = " ".join(f"[{i}, 1, 1, {i}]," for i in range(9))
    printed = [s for k, s in enumerate(M.PRINTED) if k != drop]
    return ("\\begin{align*}\nS:=\\{&" + S + "\\}.\n\\end{align*}\n\\begin{align*}\nA:=&" + extra + "\n\\end{align*}\n"
            + "\n".join(printed))


class Paper(unittest.TestCase):
    def test_reading_and_refusals(self):
        S, extra, missing = M.read_paper(fake_tex())
        self.assertEqual((len(S), len(extra), missing), (23, 9, []))
        self.assertEqual(extra[0], P(0, 1, 1, 0))
        self.assertEqual(M.read_paper(fake_tex(drop=5))[2], [5])
        with self.assertRaises(M.Refused):
            M.read_paper(fake_tex(s_points=22))

    def test_the_tex_from_the_tarball(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            data = fake_tex().encode("utf-8")
            info = tarfile.TarInfo(M.TEX)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        self.assertEqual(M.tex_of(buf.getvalue()), fake_tex())


class Formula(unittest.TestCase):
    def test_colouring_clauses_and_triangle(self):
        es = [(0, 1), (1, 2), (0, 2), (2, 3)]
        clauses = M.colouring_clauses(4, es)
        self.assertEqual(len(clauses), 4 + 5 * len(es))
        self.assertEqual(M.first_triangle(4, es), (0, 1, 2))
        with self.assertRaises(M.Refused):
            M.first_triangle(3, [(0, 1), (1, 2)])
        self.assertEqual(M.colours_from_model({1, 7, 13, 19}, 4), [0, 1, 2, 3])


@unittest.skipUnless(HAVE, "the e-print is not at inputs/ (or TWO_DISTANCE_INPUTS)")
class Construction(unittest.TestCase):
    def test_the_counts_the_paper_prints(self):
        S, extra, missing = M.read_paper(M.tex_of(M.load(INPUTS, M.EPRINT[0])))
        self.assertEqual(missing, [])
        T, V, Hs, R, Hp, K = M.construct(S, extra)
        self.assertEqual(len(T), 57)
        for points, want in ((V, M.COUNTS["G"]), (Hs, M.COUNTS["H"]), (K, M.COUNTS["K"])):
            pts, one, two = M.edges(points)
            self.assertEqual((len(pts), len(one), len(two)), want)
        B = extra[1]
        self.assertEqual(M.sq144(B, R(B)), (144, 0))


if __name__ == "__main__":
    unittest.main()
