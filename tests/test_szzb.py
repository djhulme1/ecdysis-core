"""Niedbala Giraudin's law check (pi/szzb.py): the window exactly and in floating point against a direct test of
its criterion, its psi-measure against closed forms, the stationary cubic against the derivative it clears, the
min-max search, the triples' sets and the comparisons, on triples and a configuration ((13, 7 + 4i)) chosen for the
tests. Nothing here computes the law at Salikhov's configuration.

Run with: python3 -m unittest tests.test_szzb (in the pinned scipy-notebook image)
"""

import gzip
import importlib.util
import io
import math
import os
import sys
import tarfile
import tempfile
import unittest
from fractions import Fraction

import mpmath

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pi_szzb", os.path.join(HERE, "..", "pi", "szzb.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)

TRIPLES = [(2, 3, 4), (3, 5, 7), (1, 1, 1), (2, 1, 5), (1, 2, 5), (4, 4, 9), (5, 3, 8), (3, 7, 11), (6, 5, 13)]
CFG13 = (49 - 16, 49 + 16, 169)                 # (13, 7 + 4i): D = 33, N = 65, M = 169


def frac(x):
    return x - math.floor(x)


def in_E(A, B, C, u):
    return frac(A * u + Fraction(1, 2)) + 2 * frac(B * u) < frac(C * u)


def arc_inside(rho, alpha, beta):
    """The note's criterion as stated: every point of the arc [rho, rho + 2 alpha] lies in [1/2, 1/2 + beta] mod 1
    (sampled at 513 points of the arc, in floating point)."""
    if 2 * alpha >= 1:
        return False
    r, a2, b = float(rho), float(2 * alpha), float(beta)
    return all(((r + a2 * k / 512 - 0.5) % 1.0) <= b + 1e-12 for k in range(513))


class Window(unittest.TestCase):
    def test_against_the_criterion(self):
        for A, B, C in TRIPLES:
            comps = M.window_exact(A, B, C)
            fine = 6 * A * B * C * 7
            for k in range(fine):
                u = Fraction(2 * k + 1, 2 * fine)
                inside = any(l_ <= u < r_ for l_, r_ in comps)
                self.assertEqual(inside, in_E(A, B, C, u), (A, B, C, u))

    def test_arc_reading(self):
        # {A u + 1/2} + 2{B u} < {C u} is the arc criterion with rho = {A u}, alpha = {B u}, beta = {C u}
        for A, B, C in TRIPLES:
            for k in range(1, 400):
                u = Fraction(k, 401)
                rho, alpha, beta = frac(A * u), frac(B * u), frac(C * u)
                if frac(rho - Fraction(1, 2)) + 2 * alpha == beta:
                    continue
                self.assertEqual(in_E(A, B, C, u), arc_inside(rho, alpha, beta), (A, B, C, u))

    def test_fast_matches_exact(self):
        for A, B, C in TRIPLES + [(37, 74, 111), (101, 150, 263)]:
            comps = M.window_exact(A, B, C)
            l_, r_, wid, nc = M.window_fast(A, B, C)
            self.assertEqual(nc, len(comps), (A, B, C))
            self.assertAlmostEqual(float(sum(wid)), float(sum(r - l for l, r in comps)), places=13)
            R = max(C, 2 * A + 4 * B - 2 * C)
            self.assertAlmostEqual(M.W_fast((l_, r_, wid, nc), R), float(M.W_exact(comps, R)), places=12)

    def test_merging(self):
        comps = M.window_exact(5, 3, 8)
        for (a, b), (c, d) in zip(comps, comps[1:]):
            self.assertLess(b, c)


class Measure(unittest.TestCase):
    def test_closed_forms(self):
        with mpmath.workdps(40):
            w = M.W_exact([(Fraction(1, 3), Fraction(1, 2))], 10)
            self.assertLess(abs(w - (mpmath.psi(0, mpmath.mpf(1) / 2) - mpmath.psi(0, mpmath.mpf(1) / 3))), 1e-35)
            # with the cut at 1/R = 1/2 the first copy drops out
            w2 = M.W_exact([(Fraction(1, 3), Fraction(1, 2))], 2)
            self.assertLess(abs(w2 - (mpmath.psi(0, mpmath.mpf(3) / 2) - mpmath.psi(0, mpmath.mpf(4) / 3))), 1e-35)
            # a cut inside the first copy
            w3 = M.W_exact([(Fraction(1, 5), Fraction(1, 2))], 3)
            want = (mpmath.psi(0, mpmath.mpf(3) / 2) - mpmath.psi(0, mpmath.mpf(6) / 5)) + 3 - 2
            self.assertLess(abs(w3 - want), 1e-35)

    def test_digamma_points(self):
        self.assertLess(abs(float(mpmath.psi(0, 0.5)) - (-0.5772156649015329 - 2 * math.log(2))), 1e-15)


class Cubic(unittest.TestCase):
    def test_roots_are_stationary(self):
        D, N, Mm = CFG13
        for t in [(2, 2, 3), (3, 4, 7), (6, 4, 9), (5, 5, 8)]:
            a0, a1, b = t
            c = M.cubic_coeffs(t, CFG13)
            with mpmath.workdps(30):
                for z in mpmath.polyroots([mpmath.mpf(x) for x in c], maxsteps=200, extraprec=60):
                    dlog = (mpmath.mpf(a0) / (2 * z) + a1 * (2 * z - 2 * D) / (z * z - 2 * D * z + N * N)
                            - b / (z - Mm))
                    self.assertLess(abs(dlog), 1e-20, t)

    def test_fast_roots_and_levels(self):
        for t in [(3, 4, 7), (6, 4, 9)]:
            rts, x, y = M.roots_fast(t, CFG13)
            c = M.cubic_coeffs(t, CFG13)
            with mpmath.workdps(30):
                ex = sorted(mpmath.polyroots([mpmath.mpf(v) for v in c], maxsteps=200, extraprec=60),
                            key=lambda z: (float(mpmath.re(z)), float(mpmath.im(z))))
            fr = sorted(rts, key=lambda z: (z.real, z.imag))
            for a, b in zip(fr, ex):
                self.assertLess(abs(a - complex(b)), 1e-9 * max(1, abs(a)))

    def test_degenerate(self):
        self.assertTrue(M.degenerate((2, 1, 3)))
        self.assertEqual(M.law_fast((2, 1, 3))[0], "degenerate")


class MinMax(unittest.TestCase):
    def test_substitute_configuration(self):
        for t in [(2, 2, 3), (4, 3, 5)]:
            a = M.minmax(t, grid=(401, 201), conf=(13, 7, 4))
            b = M.minmax(t, grid=(601, 301), conf=(13, 7, 4))
            self.assertIsNotNone(a["level"])
            self.assertEqual(a["index"], b["index"], t)
            self.assertIn(a["level"], a["crit"])
            self.assertGreaterEqual(a["level"], min(a["crit"]))
            self.assertLess(b["gap"], 0.05 * (max(b["crit"]) - min(b["crit"])) + 0.05)


class Sets(unittest.TestCase):
    def test_b_range(self):
        lo, hi = Fraction(14995, 10000), Fraction(15003, 10000)
        self.assertEqual(list(M.b_range(2000, lo, hi)), [2999, 3000])
        self.assertEqual(list(M.b_range(10000, lo, hi)), list(range(14995, 15004)))
        self.assertEqual(list(M.b_range(7, lo, hi)), [])

    def test_triples_from_decimals(self):
        self.assertEqual(M.q_triple("3700"), (3700, 3700, 5549))
        self.assertEqual(M.q_triple("3713.5"), (14854, 14854, 22277))
        self.assertEqual(M.above_triple(50), (25, 25, 38))
        self.assertEqual(M.xy_triple(Fraction(999, 1000), Fraction(14997, 10000)), (9990, 10000, 14997))
        self.assertEqual(M.norm((3, 3, 5)), (6, 6, 10))
        self.assertTrue(M.primitive((4, 6, 9)))
        self.assertFalse(M.primitive((4, 6, 8)))

    def test_savings(self):
        self.assertEqual(M.c2_of((2, 4, 6)), Fraction(5))
        self.assertEqual(M.c2_of((2, 2, 6)), Fraction(-4))
        self.assertEqual(M.cP_of((2, 2, 6)), 6)
        self.assertEqual(M.R_of((2, 2, 6)), 6)


class Comparisons(unittest.TestCase):
    def test_cut_or_round(self):
        self.assertTrue(M.cut_or_round(mpmath.mpf("7.10186283235635"), "7.101862832356"))
        self.assertTrue(M.cut_or_round(mpmath.mpf("7.10186283235671"), "7.101862832357"))
        self.assertTrue(M.cut_or_round(mpmath.mpf("7.10186283235671"), "7.101862832356"))
        self.assertFalse(M.cut_or_round(mpmath.mpf("7.10186283235671"), "7.101862832355"))
        self.assertTrue(M.cut_or_round(mpmath.mpf("-3.5247729241"), "-3.524772924"))
        self.assertFalse(M.cut_or_round(mpmath.mpf("3.5247729241"), "-3.524772924"))
        self.assertTrue(M.cut_or_round(mpmath.mpf("0.000000001"), "0"))

    def test_planted(self):
        res = [((1, 1, 1), "bound", 7.2), ((1, 1, 2), "nobound", None), ((1, 2, 3), "bound", 7.0)]
        self.assertEqual(M.compare_planted(res, 7.1), [2])


class Source(unittest.TestCase):
    def test_refusals(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.tar.gz")
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w") as tf:
                data = b"\\documentclass{article}"
                ti = tarfile.TarInfo(M.TEX_NAME)
                ti.size = len(data)
                tf.addfile(ti, io.BytesIO(data))
            with open(p, "wb") as fh:
                fh.write(gzip.compress(buf.getvalue()))
            with self.assertRaises(M.Refused):
                M.read_source(p)


if __name__ == "__main__":
    unittest.main()
