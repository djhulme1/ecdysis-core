"""Conner, Gesmundo, Landsberg & Ventura's det_3 decompositions (waring/cglv2019.py) on inputs written here, never
the paper's: Q(theta) arithmetic, the TeX and Macaulay2 readers, the field F = Q[y]/(f) and its cubic extensions on
a small certificate of the same shape, the system builder's normalisation, the Koszul flattening on unit tensors and
the tensor helpers.

Run with: python3 -m unittest discover -s tests -p test_cglv2019.py (in the pinned scipy-notebook image)
"""

import importlib.util
import os
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("waring_cglv2019", os.path.join(HERE, "..", "waring", "cglv2019.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


class QTheta(unittest.TestCase):
    def test_relations(self):
        th = M.THETA
        self.assertEqual(th * th, th - M.ONE)
        self.assertEqual(th * M.THETABAR, M.ONE)
        p = M.ONE
        for _ in range(6):
            p = p * th
        self.assertEqual(p, M.ONE)
        self.assertEqual(th * th * th, -M.ONE)

    def test_entries(self):
        e = M.parse_qt_entry(r"-\frac{1}{3} \bar{\theta}")
        self.assertEqual(e, -(M.QT(Fraction(1, 3)) * M.THETABAR))
        self.assertEqual(M.parse_qt_entry("0"), M.ZERO)
        self.assertEqual(M.parse_qt_entry(r"\theta"), M.THETA)
        with self.assertRaises(M.Refused):
            M.parse_qt_entry(r"\pi")
        self.assertEqual(M.parse_t_entry("-z_{36} t"), (-1, 36, 1))
        self.assertEqual(M.parse_t_entry("t"), (1, None, 1))
        self.assertEqual(M.parse_t_entry("-1"), (-1, None, 0))
        with self.assertRaises(M.Refused):
            M.parse_t_entry("w")


def synthetic_tex():
    mats18 = "\n".join(
        f"L_{{{k}}} = \\begin{{pmatrix}} {k} & 0 & 0 \\\\ 0 & -\\frac{{1}}{{3}}\\theta & 0 \\\\ 0 & 0 & \\bar{{\\theta}} "
        "\\end{pmatrix}" for k in range(1, 19))
    mats17 = "\n".join(
        f"L_{{{k}}}(t)= \\begin{{pmatrix}} z_{{{k}}} & 0 & 0 \\\\ 0 & z_{{{k + 1}}} t & 0 \\\\ -1 & 0 & t "
        "\\end{pmatrix}" for k in range(1, 18))
    return ("\\begin{theorem}\\label{det18thm} x \\end{theorem}\\begin{proof}" + mats18 + "\\end{proof}"
            "\\begin{theorem}\\label{det17thm} y \\end{theorem}\\begin{proof}" + mats17 +
            " The coefficients $z_1 ... Let $y_*$ be a real root of the polynomial \n\\begin{align*}\n"
            "& x^{27} - 2x^{26} + 17 x^{25}  \\\\\n & - 5 x^9 + x - 7.\\\\\n\\end{align*}\nFor $i = 1")


class Readers(unittest.TestCase):
    def test_tex(self):
        tex = synthetic_tex()
        f18 = M.read_forms18(tex)
        self.assertEqual(len(f18), 18)
        self.assertEqual(f18[4][0][0], M.QT(5))
        self.assertEqual(f18[0][1][1], -(M.QT(Fraction(1, 3)) * M.THETA))
        f17 = M.read_forms17(tex)
        self.assertEqual(len(f17), 17)
        self.assertEqual(f17[2][1][1], (1, 4, 1))
        poly = M.read_tex_polynomial(tex)
        self.assertEqual(poly[27], 1)
        self.assertEqual(poly[26], -2)
        self.assertEqual(poly[25], 17)
        self.assertEqual(poly[9], -5)
        self.assertEqual(poly[1], 1)
        self.assertEqual(poly[0], -7)
        with self.assertRaises(M.Refused):
            M.read_forms18(tex.replace("L_{7} =", "L_{77} ="))

    def test_m2(self):
        p = M.m2("-(3/7)*y^2+(1/2)*y-5")
        self.assertEqual(p.t[(("y", 2),)], Fraction(-3, 7))
        self.assertEqual(p.t[()], -5)
        q = M.m2("z_10^2*z_11 - z_15 + 1")
        self.assertEqual(q.t[(("z10", 2), ("z11", 1))], 1)
        r = M.m2("-1/3 *x_(1,1) + b*x_(2,2)")
        self.assertEqual(r.t[(("x11", 1),)], Fraction(-1, 3))
        self.assertEqual(r.t[(("b", 1), ("x22", 1))], 1)
        with self.assertRaises(M.Refused):
            M.m2("y^z_1")
        with self.assertRaises(M.Refused):
            M.m2("import os")
        mon = M.read_mon("Mon = { \n{{z_1^2, y^2, 1}, {z_2, (y^2), -1}},\n{{1, 1, 1}}   };")
        self.assertEqual(len(mon), 2)
        self.assertEqual(len(mon[0]), 2)
        self.assertEqual(mon[0][1][2].constval(), -1)
        a = M.m2_assignments("e_1\t=z_1 + z_2; \ne_2 = 3;", "e")
        self.assertEqual(sorted(a), [1, 2])

    def test_canonical(self):
        p = M.m2("2*z_1*z_2 - 4")
        q = M.m2("-z_1*z_2 + 2")
        self.assertEqual(p.canonical(), q.canonical())
        self.assertNotEqual(p.canonical(), M.m2("z_1*z_2 - 4").canonical())


def small_certificate():
    """f = y^27 - 2: z_1 = y, z_2 = y^2, and a type 2 equation with u = z_3 z_1, z_3^3 = y, z_6^3 = y^4."""
    M.FE.MOD = [-2] + [0] * 26
    yy = {1: M.m2("y^3"), 2: M.m2("y^6"), 3: M.m2("y"), 6: M.m2("y^4")}
    cert = {
        "e1": {1: M.m2("z_1^2 - z_2")},
        "e2": {1: M.m2("z_3*z_1 - z_6")},
        "mon1": [[(M.m2("z_1^2"), M.m2("y^2"), M.m2("1")), (M.m2("z_2"), M.m2("y^2"), M.m2("-1"))]],
        "mon2": [[(M.m2("z_3*z_1"), M.m2("u"), M.m2("1")), (M.m2("z_6"), M.m2("u"), M.m2("-1"))]],
    }
    return cert, {j: M.FE.from_poly(p) for j, p in yy.items()}


class Field(unittest.TestCase):
    def test_reduction(self):
        M.FE.MOD = [-2] + [0] * 26
        y = M.FE.from_poly(M.m2("y"))
        p = M.fe_one()
        for _ in range(27):
            p = p * y
        self.assertEqual(p, M.FE.from_poly(M.m2("2")))
        self.assertEqual(M.FE.from_poly(M.m2("y^28")), M.FE.from_poly(M.m2("2*y")))
        half = M.FE.from_poly(M.m2("(1/2)*y^26"))
        self.assertEqual(half * y, M.fe_one())

    def test_certificate(self):
        cert, yy = small_certificate()
        out = M.check_certificate(cert, yy)
        self.assertEqual((out["type1"], out["type2"]), (1, 1))
        self.assertEqual(out["cube_identities"], 4)
        bad = dict(yy)
        bad[2] = yy[2].scale(2)
        out = M.check_certificate(cert, bad)
        self.assertEqual(out["type1"], 0)
        bad = dict(yy)
        bad[6] = yy[6].scale(3)
        self.assertEqual(M.check_certificate(cert, bad)["type2"], 0)

    def test_extension(self):
        M.FE.MOD = [-2] + [0] * 26
        p = M.FE.from_poly(M.m2("y"))
        u = M.ke_from_poly(M.m2("u"), p)
        cube = u * u * u
        self.assertEqual(cube, M.KE([p, M.fe_zero(), M.fe_zero()], p))
        self.assertEqual(M.ke_from_poly(M.m2("u^4"), p), M.KE([M.fe_zero(), p, M.fe_zero()], p))

    def test_field_generated(self):
        M.FE.MOD = [-2] + [0] * 26
        self.assertEqual(M.field_generated(M.FE.from_poly(M.m2("y")), M.PRIMES), [27, 27])
        self.assertLess(max(M.field_generated(M.FE.from_poly(M.m2("y^3")), M.PRIMES)), 27)


class System(unittest.TestCase):
    def test_normalisation(self):
        mat = [[(1, None, 0), (0, None, 0), (0, None, 0)], [(0, None, 0), (1, 1, 1), (0, None, 0)],
               [(0, None, 0)] * 3]
        eqs = M.system17([mat], M.QT(6))
        x00_3 = ((3,) + (0,) * 8, 0)
        self.assertEqual(eqs[x00_3], M.Poly.const(1))
        x00_2_x11 = ((2, 0, 0, 0, 1, 0, 0, 0, 0), 1)
        self.assertEqual(eqs[x00_2_x11], M.m2("z_1"))
        x00_x11_2 = ((1, 0, 0, 0, 2, 0, 0, 0, 0), 2)
        self.assertEqual(eqs[x00_x11_2], M.m2("z_1^2"))
        diag = ((1, 0, 0, 0, 1, 0, 0, 0, 1), 2)
        self.assertEqual(eqs[diag], M.Poly.const(-1))
        anti = ((0, 0, 1, 0, 1, 0, 1, 0, 0), 2)
        self.assertEqual(eqs[anti], M.Poly.const(1))
        self.assertNotIn(((3,) + (0,) * 8, 3), eqs)

    def test_match(self):
        derived = {("a", 0): M.m2("2*z_1 - 2"), ("b", 0): M.m2("z_2")}
        cert = {"e1": {1: M.m2("z_1 - 1")}, "e2": {1: M.m2("-z_2")}}
        r = M.match_systems(derived, cert)
        self.assertEqual((r["matched"], r["files_used"], r["files_total"]), (2, 2, 2))
        cert["e2"][2] = M.m2("z_3")
        self.assertEqual(M.match_systems(derived, cert)["files_used"], 2)
        self.assertEqual(M.match_systems(derived, cert)["files_total"], 3)


class Tensors(unittest.TestCase):
    def test_cubes_and_det(self):
        dt = M.det_terms()
        self.assertEqual(len(dt), 6)
        poly = {k: M.QT(2 * s) for k, s in dt.items()}
        self.assertEqual(M.multiple_of_det(poly), M.QT(2))
        poly[(3,) + (0,) * 8] = M.ONE
        self.assertIsNone(M.multiple_of_det(poly))
        x = [[M.ONE, M.ZERO, M.ZERO], [M.ZERO] * 3, [M.ZERO] * 3]
        self.assertEqual(M.cube_sum([x]), {(3,) + (0,) * 8: M.ONE})

    def test_koszul_unit(self):
        unit3 = {(i, i, i): Fraction(1) for i in range(3)}
        self.assertEqual(M.koszul_rank(unit3, (3, 3, 3), [[1, 0, 0], [0, 1, 0], [0, 0, 1]], 1), 6)
        unit = {(i, i, i): Fraction(1) for i in range(4)}
        phi = [[1, 0, 0, 1], [0, 1, 0, 1], [0, 0, 1, 1]]
        self.assertEqual(M.koszul_rank(unit, (4, 4, 4), phi, 1), 8)
        unit5 = {(i, i, i): Fraction(1) for i in range(5)}
        phi5 = [[1, 0, 0, 1, 2], [0, 1, 0, 1, 3], [0, 0, 1, 1, 5]]
        self.assertEqual(M.koszul_rank(unit5, (5, 5, 5), phi5, 2), 5)
        ident5 = [[int(i == j) for j in range(5)] for i in range(5)]
        self.assertEqual(M.koszul_rank(unit5, (5, 5, 5), ident5, 2), 30)

    def test_skew_family_shape(self):
        for q in (4, 6):
            t = M.skewcw(q)
            self.assertEqual(len(t), 2 * q + q)
            tp = M.identify(t, q)
            for (i, j, k), v in tp.items():
                self.assertEqual(tp.get((j, i, k)), -v)
                self.assertEqual(tp.get((i, k, j)), -v)
        with self.assertRaises(M.Refused):
            M.skewcw(3)

    def test_kron_square(self):
        sym, form = M.kron_square_form({(0, 0, 0): Fraction(1)})
        self.assertTrue(sym)
        self.assertEqual(form, {(3,) + (0,) * 8: 1})
        sym, _ = M.kron_square_form({(0, 1, 2): Fraction(1)})
        self.assertFalse(sym)

    def test_jt_terms(self):
        terms = M.jt_terms(M.THETA * M.THETA)
        self.assertEqual(len(terms), 18)
        self.assertTrue(all(sum(1 for r in m for c in r if not c.iszero()) == 3 for _, m in terms))


class Draws(unittest.TestCase):
    def test_stream(self):
        a = [M.Stream("0" * 64, "x").below(19) for _ in range(1)]
        s1, s2 = M.Stream("0" * 64, "x"), M.Stream("0" * 64, "x")
        self.assertEqual([s1.below(1000) for _ in range(5)], [s2.below(1000) for _ in range(5)])
        self.assertTrue(0 <= a[0] < 19)

    def test_bad_seed(self):
        with self.assertRaises(M.Refused):
            M.run("nope")


if __name__ == "__main__":
    unittest.main()
