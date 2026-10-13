"""Ballard, Ikenmeyer, Landsberg & Ryder's rank-23 decompositions (mm/bilr.py): the reading of a data file and its
refusals; M<3> and the standard decomposition; the normal form of a rank-one term and cubes; the outer symmetries;
the conditions that carry a term onto itself, and the search refusing a decomposition whose rank-one terms cannot fix
g, h and k (the standard one, with its torus of symmetries); the verdict at and beside each condition; and, with the
e-print at inputs/ (or BILR_INPUTS), the six decompositions and the order 12.

Run with: python3 -m unittest tests.test_bilr
"""

import importlib.util
import os
import sys
import unittest
from fractions import Fraction as F

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("mm_bilr", os.path.join(HERE, "..", "mm", "bilr.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)

INPUTS = os.environ.get("BILR_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = os.path.isfile(os.path.join(INPUTS, M.EPRINT[0]))


def E(i, j):
    return tuple(tuple(F(1) if (r, c) == (i, j) else F(0) for c in range(3)) for r in range(3))


STD = [(E(i, j), E(j, k), E(k, i)) for i in range(3) for j in range(3) for k in range(3)]

PIECE = r"""\begin{align}
\Mthree
&= \label{x_c1} \begin{pmatrix} 1 & 0 & 0 \\ 0 & 0 & 0 \\ 0 & 0 & 0 \end{pmatrix}^{\ot 3}
	+ \begin{pmatrix} 0 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & 0 \end{pmatrix}^{\ot 3} \\
&+ \label{x_c2} \BZ_3^{std} \cdot
	\begin{pmatrix} 0 & 0 & 0 \\ 1 & 0 & 0 \\ 0 & 0 & 0 \end{pmatrix} \ot
	\begin{pmatrix} 1 & 0 & 0 \\ 0 & 0 & 0 \\ 0 & 0 & 0 \end{pmatrix} \ot
	\begin{pmatrix} 0 & 1 & 0 \\ 0 & 0 & 0 \\ 0 & 0 & 0 \end{pmatrix} \\
\end{align}"""


class Reading(unittest.TestCase):
    def test_cubes_and_orbits(self):
        terms = M.parse(PIECE)
        self.assertEqual(len(terms), 2 + 3)
        self.assertEqual(terms[0], (E(0, 0),) * 3)
        self.assertEqual(terms[2], (E(1, 0), E(0, 0), E(0, 1)))
        self.assertEqual(terms[3], (E(0, 0), E(0, 1), E(1, 0)))
        self.assertEqual(terms[4], (E(0, 1), E(1, 0), E(0, 0)))

    def test_refusals(self):
        with self.assertRaises(M.Refused):
            M.parse(PIECE.replace("^{\\ot 3}\n\t+", "^{\\ot 2}\n\t+", 1))
        with self.assertRaises(M.Refused):
            M.parse(PIECE.replace("1 & 0 & 0 \\\\ 0 & 0 & 0 \\\\ 0 & 0 & 0 \\end{pmatrix}^{\\ot 3}",
                                  "1/2 & 0 & 0 \\\\ 0 & 0 & 0 \\\\ 0 & 0 & 0 \\end{pmatrix}^{\\ot 3}", 1))
        with self.assertRaises(M.Refused):
            M.parse(PIECE.replace("\\Mthree", "\\Mtwo"))


class Tensors(unittest.TestCase):
    def test_standard_decomposition_and_outer_symmetries(self):
        self.assertEqual(M.tensor(STD), M.M3)
        for name, f in M.OUTER.items():
            with self.subTest(outer=name):
                self.assertEqual(M.tensor([f(t) for t in STD]), M.M3)
        self.assertNotEqual(M.tensor(STD[:-1]), M.M3)

    def test_normal_form_and_cubes(self):
        a = ((F(2), F(0), F(0)), (F(0), F(0), F(0)), (F(0), F(0), F(4)))
        t = (a, a, a)
        u = (M.scale(a, F(3)), M.scale(a, F(1, 6)), M.scale(a, F(2)))     # 3 * 1/6 * 2 = 1: the same tensor
        self.assertEqual(M.normal(t), M.normal(u))
        self.assertNotEqual(M.normal(t), M.normal((M.scale(a, F(2)), a, a)))
        self.assertTrue(M.is_cube(u))
        self.assertFalse(M.is_cube((a, E(0, 0), a)))
        self.assertEqual(M.tensor([t]), M.tensor([u]))


class Group(unittest.TestCase):
    def test_a_torus_of_symmetries_is_refused(self):
        # The standard decomposition's rank-one factors span only the coordinate points, which cannot fix g, h and k
        # (its symmetries include a torus), so the search must refuse it rather than report a finite group.
        with self.assertRaises(M.Refused):
            M.symmetry_group(STD)

    def test_conditions_carry_a_term(self):
        s = (E(0, 1), E(1, 2), E(2, 0))
        eqs = M.conditions_for(s, s)
        ident = [F(1), F(0), F(0), F(0), F(1), F(0), F(0), F(0), F(1)]
        for x in "ghk":
            for row in eqs[x]:
                self.assertEqual(sum(a * b for a, b in zip(row, ident)), 0)


class Verdict(unittest.TestCase):
    def results(self, **kw):
        r = {n: {"exact": True, "distinct": 23, "printed": 23, "cyclic": True} for n in M.NAMES}
        for name, change in kw.items():
            r[name].update(change)
        return r

    def test_at_and_beside_each_condition(self):
        self.assertEqual(sum(M.conditions(self.results(), 11, 12).values()), 5)
        for bad in ((self.results(lad={"exact": False}), 11, 12), (self.results(twofix={"distinct": 22}), 11, 12),
                    (self.results(addtlone={"printed": 24}), 11, 12), (self.results(zfzt={"cyclic": False}), 11, 12),
                    (self.results(), 10, 12), (self.results(), 11, 24)):
            with self.subTest(bad=bad[1:]):
                self.assertEqual(sum(M.conditions(*bad).values()), 4)


@unittest.skipUnless(HAVE, "the e-print is not at inputs/ (or BILR_INPUTS)")
class EPrint(unittest.TestCase):
    def test_the_six_and_the_order_twelve(self):
        tx = M.texts(M.load(INPUTS))
        for name in M.NAMES:
            terms = M.parse(tx[name])
            exact, distinct, cyclic = M.checks(terms)
            with self.subTest(name=name):
                self.assertEqual((len(terms), exact, distinct, cyclic), (23, True, 23, True))
        zfzt = M.parse(tx["zfzt"])
        self.assertEqual(sum(1 for t in zfzt if M.is_cube(t)), 11)
        self.assertEqual(len(M.symmetry_group(zfzt)), 12)


if __name__ == "__main__":
    unittest.main()
