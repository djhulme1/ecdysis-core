"""The 42-term border rank expression check: the skew cousin tensor as the paper defines it, the twelfth roots of
unity, the reader of the printed entries and its refusals, the expansion on a wrong or empty expression, and, with the
e-print at inputs/ (or LASER_INPUTS), the whole run.

Run with: python3 -m unittest discover -s tests
"""

import cmath
import importlib.util
import itertools
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("laser_check", os.path.join(HERE, "..", "laser", "check.py"))
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)


def sign(perm):
    s = 1
    for i, j in itertools.combinations(range(3), 2):
        if perm[i] > perm[j]:
            s = -s
    return s


class Tensor(unittest.TestCase):
    def test_skew_cousin(self):
        T = L.skewcw(2)
        cells = [(a, b, c) for a in range(5) for b in range(5) for c in range(5)]
        self.assertEqual(sum(1 for a, b, c in cells if T[a][b][c]), 12)
        for a, b, c in cells:
            for perm in itertools.permutations(range(3)):
                idx = [(a, b, c)[k] for k in perm]
                self.assertEqual(T[idx[0]][idx[1]][idx[2]], sign(perm) * T[a][b][c])
        self.assertEqual((T[0][1][3], T[0][3][1], T[1][3][0]), (1, -1, 1))

    def test_kronecker_square_is_symmetric(self):
        T = L.skewcw(2)
        cells = [(r, c) for r in range(5) for c in range(5)]
        nonzero = 0
        for p in itertools.product(cells, repeat=3):
            v = L.kron_square_entry(T, *p)
            nonzero += v != 0
            for perm in itertools.permutations(p):
                self.assertEqual(L.kron_square_entry(T, *perm), v)
        self.assertEqual(nonzero, 144)

    def test_the_definition_in_the_tex(self):
        tex = "x\n$$\n" + L.TEX_T.replace(" - ", "\n - ").replace("\\ot ", "\\ot  ") + "\n$$\n"
        self.assertIn(L.squash(L.TEX_T), L.squash(tex))


class Reader(unittest.TestCase):
    def test_roots_of_unity(self):
        z = L.zeta_powers(12)
        for k in range(12):
            self.assertLess(abs(z[k] - cmath.exp(2j * cmath.pi * k / 12)), 1e-15)
        self.assertEqual(z[3], 1j)

    def test_entries(self):
        self.assertIsNone(L.entry(" 0 "))
        self.assertEqual(L.entry("\\frac{\\zeta^{3} z_{25} z_{26}}{t^{269}}"),
                         ([("zeta", 0, 3), ("z", 25, 1), ("z", 26, 1)], [("t", 0, 269)]))
        self.assertEqual(L.entry("\\zeta^{10} z_{33} t^{100}"), ([("zeta", 0, 10), ("z", 33, 1), ("t", 0, 100)], []))
        self.assertEqual(L.entry("\\frac{1}{t}"), ([], [("t", 0, 1)]))
        self.assertEqual(L.entry("\\frac{\\zeta t^{184}}{z_{27} z_{30}^{2}}"),
                         ([("zeta", 0, 1), ("t", 0, 184)], [("z", 27, 1), ("z", 30, 2)]))
        for bad in ("\\zeta^3", "z_{3}z_{4}", "2 z_{3}", "-\\zeta", "\\frac{z_{1}}", "x", "z_{1}^2"):
            with self.subTest(text=bad), self.assertRaises(L.Refused):
                L.entry(bad)

    def test_values_and_shapes(self):
        z = [complex(2, 0)] * 36
        mats = [[[None] * 5 for _ in range(5)] for _ in range(2)]
        mats[0][1][2] = ([("zeta", 0, 3), ("z", 4, 2)], [("t", 0, 5)])
        vals = L.evaluate(mats, z, L.zeta_powers(12))
        self.assertEqual(vals[1], {})
        coef, power = vals[0][(1, 2)]
        self.assertEqual((coef, power), (4j, -5))
        with self.assertRaises(L.Refused):
            L.matrices("\\begin{pmatrix} 0 & 0 \\\\ 0 & 0 \\end{pmatrix}")
        with self.assertRaises(L.Refused):
            L.z_values("z_{0} &= 1.0 + 2.0i & z_{0} &= 1.0 + 2.0i")


class Expansion(unittest.TestCase):
    def test_nothing_gives_nothing(self):
        r = L.expand([], L.skewcw(2))
        self.assertEqual((r["max_negative"], r["max_zero"]), (0.0, 1))
        self.assertFalse(L.passes(r))

    def test_a_single_wrong_cube_fails(self):
        v = {(r, c): (complex(1, 0), -1 if (r, c) == (0, 0) else 0) for r in range(5) for c in range(5)}
        r = L.expand([v], L.skewcw(2))
        self.assertTrue(r["tight"])
        self.assertFalse(L.passes(r))
        self.assertEqual(r["unordered_triples"], 2925)


def inputs_dir():
    d = os.environ.get("LASER_INPUTS") or os.path.join(HERE, "..", "inputs")
    return d if os.path.isfile(os.path.join(d, L.INPUT[0])) else None


@unittest.skipUnless(inputs_dir(), "the e-print is not at inputs/ (or LASER_INPUTS)")
class TheEprint(unittest.TestCase):
    def test_the_printed_expression(self):
        with tempfile.TemporaryDirectory() as d:
            out, detail = L.run(inputs=inputs_dir(), results=d)
        self.assertEqual(out["test_passed"], 1)
        self.assertEqual((out["z_values"], out["matrices"], out["entries_nonzero"]), (36, 42, 226))
        self.assertEqual((out["equations"], out["unordered_triples"], out["zero_triples"]), (692, 2925, 144))
        self.assertEqual((out["controls_passed"], out["controls_total"]), (3, 3))
        self.assertLess(max(out["max_negative"], out["max_zero"]), 1e-14)


if __name__ == "__main__":
    unittest.main()
