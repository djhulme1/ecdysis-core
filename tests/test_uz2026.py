"""Uznanski's rectangular bounds (mm/uz2026.py): cyclotomic and Q(zeta_m) arithmetic, the substitution engine under
phases other than the paper's, polynomial and P-adic helpers, the coordinate maps at sizes the run does not use, the
optimiser on a constraint other than the paper's, and the readers and comparisons, on inputs other than the claim's
own case: none of the paper's constructions is checked here and the registered grid is never solved.

Run with: python3 -m unittest tests.test_uz2026 (in the pinned scipy-notebook image)
"""

import gzip
import hashlib
import importlib.util
import io
import math
import os
import random
import sys
import tarfile
import tempfile
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("mm_uz2026", os.path.join(HERE, "..", "mm", "uz2026.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)


class Cyclotomic(unittest.TestCase):
    def test_small(self):
        self.assertEqual(M.cyclotomic(1), [-1, 1])
        self.assertEqual(M.cyclotomic(2), [1, 1])
        self.assertEqual(M.cyclotomic(4), [1, 0, 1])
        self.assertEqual(M.cyclotomic(6), [1, -1, 1])
        self.assertEqual(M.cyclotomic(12), [1, 0, -1, 0, 1])

    def test_char_sums_beyond_the_run(self):
        for L in (18, 20, 24):
            n = len(M.cyclotomic(L)) - 1
            for k in range(-2 * L, 2 * L + 1):
                want = tuple([L] + [0] * (n - 1)) if k % L == 0 else tuple([0] * n)
                self.assertEqual(M.char_sum(k, L), want, (k, L))


class Field(unittest.TestCase):
    def test_fields_the_run_does_not_use(self):
        for m in (6, 7, 9):
            K = M.Cyc(m)
            z = K.zeta_pow(1)
            self.assertEqual(K.zeta_pow(m), K.one())
            self.assertEqual(M.cpoly_eval(K, [K.reduce([x]) for x in M.cyclotomic(m)], z), K.zero())
            rng = random.Random(m)
            for _ in range(5):
                x = K.reduce([Fraction(rng.randint(-5, 5), rng.randint(1, 4)) for _ in range(K.n)])
                y = K.reduce([Fraction(rng.randint(-5, 5), rng.randint(1, 4)) for _ in range(K.n)])
                self.assertEqual(K.mul(x, y), K.mul(y, x))
                self.assertEqual(K.add(x, K.neg(x)), K.zero())
            for h in range(m):
                Lh = M.lagrange_at_roots(K, m, h)
                for j in range(m):
                    self.assertEqual(M.cpoly_eval(K, Lh, K.zeta_pow(j)), K.one() if j == h else K.zero())

    def test_p_adic_digits_rebuild(self):
        K = M.Cyc(6)
        rng = random.Random(3)
        p = [K.reduce([rng.randint(-3, 3) for _ in range(K.n)]) for _ in range(23)]
        digits, rest = M.p_adic_digits(K, p, 6, 5)
        rebuilt = [K.zero()]
        for c, d in enumerate(digits):
            term = M.cpoly_mul(K, d, M.P_power(K, 6, c))
            n = max(len(rebuilt), len(term))
            rebuilt = [K.add(rebuilt[i] if i < len(rebuilt) else K.zero(), term[i] if i < len(term) else K.zero())
                       for i in range(n)]
        while rebuilt and K.is_zero(rebuilt[-1]):
            rebuilt.pop()
        self.assertTrue(all(K.is_zero(x) for x in rest))
        self.assertEqual(rebuilt, p)
        self.assertTrue(all(len(d) == 6 for d in digits))


class Engine(unittest.TestCase):
    def test_trivial_phases_keep_every_term(self):
        rng = random.Random(5)
        T = M.random_block_tensor(2, rng)
        zero_phases = {"x": lambda l, g: 0, "y": lambda l, h, u: 0, "z": lambda l, h, v: 0}
        S = M.separate(T, 2, 5, phases=zero_phases)
        self.assertEqual(len(S), len(T) * 8)
        n = len(M.cyclotomic(5)) - 1
        self.assertTrue(all(vec == tuple(c * x for x in (5,) + (0,) * (n - 1))
                            for (a, g, h, b, u, c_, v), (vec, w) in S.items()
                            for c in [T[(h, a, b, c_)]]))

    def test_blocks(self):
        rng = random.Random(7)
        for Mn in (1, 5):
            T = M.random_block_tensor(Mn, rng)
            self.assertEqual({k[0] for k in T}, set(range(1, Mn + 1)))
            self.assertTrue(all(1 <= abs(v) <= M.COEFF for v in T.values()))


class Polynomials(unittest.TestCase):
    def test_helpers(self):
        self.assertEqual(M.pmul([1, 1], [1, -1]), [1, 0, -1])
        self.assertEqual(M.padd([1], [0, 2]), [1, 2])
        self.assertEqual(M.trim([1, 0, 0]), [1])
        self.assertEqual(M.coeff([1, 2], 5), 0)
        self.assertEqual(M.C(2, 2), {(0, 0, 0): 1, (0, 1, 1): 1, (1, 0, 1): 1, (1, 1, 2): 1})

    def test_coordinates_invert_at_other_sizes(self):
        rng = random.Random(11)
        for e in (12, 15):
            for _ in range(5):
                a = [rng.randint(-5, 5) for _ in range(e + 1)]
                b = [rng.randint(-5, 5) for _ in range(e + 1)]
                p, h = M.to_ph(a, b, e)
                a2, b2 = M.from_ph(p, h, e)
                self.assertEqual(M.trim(a2), M.trim(a))
                self.assertEqual(M.trim(b2), M.trim(b))

    def test_part_of(self):
        self.assertEqual(M.part_of(3, [(0, 2), (3, 5)]), 1)
        self.assertIsNone(M.part_of(9, [(0, 2), (3, 5)]))


class Optimiser(unittest.TestCase):
    def test_other_constraint(self):
        # sum theta = pi/4, a = b = c = 1: cos^2 is concave there, so the best is the equal split
        want = 3 * (1 + math.cos(math.pi / 6)) / 2
        self.assertAlmostEqual(M.best_objective(1.0, 1.0, 1.0, total=math.pi / 4), want, places=9)

    def test_corner(self):
        # a single weight: the best puts its angle at zero
        self.assertAlmostEqual(M.best_objective(3.0, 0.0, 0.0, total=1.0), 3.0, places=12)


class Comparisons(unittest.TestCase):
    def test_cut_or_round(self):
        self.assertTrue(M.cut_or_round(Fraction(1, 3), "0.333"))
        self.assertFalse(M.cut_or_round(Fraction(1, 3), "0.334"))
        self.assertTrue(M.cut_or_round(Fraction(2, 3), "0.667"))
        self.assertTrue(M.cut_or_round(Fraction(2, 3), "0.666"))
        self.assertTrue(M.cut_or_round(Fraction(7), "7"))

    def test_bisect(self):
        self.assertAlmostEqual(M.bisect(lambda x: x * x - 2, 0.0, 2.0), math.sqrt(2), places=12)

    def test_quantum_functionals_small_grid(self):
        worst, edge = M.quantum_functionals(n=5)
        self.assertTrue(math.isfinite(worst) and math.isfinite(edge))


class Source(unittest.TestCase):
    def tarball(self, text):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tf:
            data = text.encode()
            ti = tarfile.TarInfo(M.TEX_NAME)
            ti.size = len(data)
            tf.addfile(ti, io.BytesIO(data))
        return gzip.compress(buf.getvalue())

    def test_refusals(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.tar.gz")
            blob = self.tarball("\\documentclass{article}")
            with open(p, "wb") as fh:
                fh.write(blob)
            with self.assertRaises(M.Refused):
                M.read_source(p)                                    # wrong hash
            saved = M.EPRINT
            try:
                M.EPRINT = ("x.tar.gz", hashlib.sha256(blob).hexdigest(), len(blob))
                with self.assertRaises(M.Refused):
                    M.read_source(p)                                # the strings are missing
                whole = "\n".join(M.PRINTED_TEX)
                blob2 = self.tarball(whole)
                with open(p, "wb") as fh:
                    fh.write(blob2)
                M.EPRINT = ("x.tar.gz", hashlib.sha256(blob2).hexdigest(), len(blob2))
                self.assertEqual(M.read_source(p), len(M.PRINTED_TEX))
            finally:
                M.EPRINT = saved


if __name__ == "__main__":
    unittest.main()
