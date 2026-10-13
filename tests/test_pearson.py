"""Pearson's spots (gs/pearson.py): the stream; the start and its noise; the five-point sum and one step against the
equations written out, and the red state as a fixed point; spots on the torus; the tracker on drawn frames (a
division in two, complete lineages and their growth, a split into three, a merge, a birth, a death, a split whose
daughter has a second parent); the verdict at and beside each threshold; and one short run in this process.

Needs numpy and scipy (the scipy-notebook image). Run with: python3 -m unittest tests.test_pearson
"""

import importlib.util
import os
import sys
import tempfile
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("gs_pearson", os.path.join(HERE, "..", "gs", "pearson.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M          # so that the worker pool can pickle simulate by name
_spec.loader.exec_module(M)

SEED = "0" * 64


def disc(cy, cx, r, n=M.N):
    y, x = np.ogrid[:n, :n]
    dy = np.minimum(np.abs(y - cy), n - np.abs(y - cy))
    dx = np.minimum(np.abs(x - cx), n - np.abs(x - cx))
    return dy * dy + dx * dx <= r * r


class Streams(unittest.TestCase):
    def test_labels_and_seeds(self):
        a = M.Stream(SEED, "gs/x").uniforms(9)
        self.assertTrue(np.array_equal(a, M.Stream(SEED, "gs/x").uniforms(9)))
        self.assertFalse(np.array_equal(a, M.Stream(SEED, "gs/y").uniforms(9)))
        self.assertFalse(np.array_equal(a, M.Stream("1" * 64, "gs/x").uniforms(9)))
        u = M.Stream(SEED, "gs/x").uniforms(100000)
        self.assertTrue(0.0 <= u.min() and u.max() < 1.0)
        self.assertAlmostEqual(float(u.mean()), 0.5, delta=0.005)


class Start(unittest.TestCase):
    def test_square_and_noise(self):
        U, V = M.start(SEED, "epsilon-4")
        a, b = M.SQUARE
        self.assertEqual((a, b), (118, 138))
        inside = np.zeros((M.N, M.N), bool)
        inside[a:b, a:b] = True
        self.assertTrue(np.all(np.abs(U[inside] / 0.5 - 1) <= 0.01))
        self.assertTrue(np.all(np.abs(V[inside] / 0.25 - 1) <= 0.01))
        self.assertTrue(np.all(np.abs(U[~inside] - 1) <= 0.01))
        self.assertEqual(float(np.abs(V[~inside]).max()), 0.0)          # relative noise: V stays 0 outside
        self.assertGreater(float(U[~inside].std()), 0.005)                # and U's is spread over +-1%
        U2, _ = M.start(SEED, "zeta")
        self.assertFalse(np.array_equal(U, U2))


class Model(unittest.TestCase):
    def test_sum_and_step_against_the_equations(self):
        rng = np.random.default_rng(3)
        U, V = rng.random((M.N, M.N)), rng.random((M.N, M.N)) * 0.3
        out = np.empty_like(U)
        M.laplacian_into(U, out)
        roll = np.roll(U, 1, 0) + np.roll(U, -1, 0) + np.roll(U, 1, 1) + np.roll(U, -1, 1) - 4 * U
        self.assertTrue(np.allclose(out, roll, rtol=0, atol=1e-14))
        F, k = 0.02, 0.059
        lap = lambda X: (np.roll(X, 1, 0) + np.roll(X, -1, 0) + np.roll(X, 1, 1) + np.roll(X, -1, 1) - 4 * X) / M.H ** 2
        want_u = U + (M.DU * lap(U) - U * V * V + F * (1 - U))
        want_v = V + (M.DV * lap(V) + U * V * V - (F + k) * V)
        m = M.Model(U.copy(), V.copy(), F, k)
        m.step()
        self.assertTrue(np.allclose(m.U, want_u, rtol=0, atol=1e-12))
        self.assertTrue(np.allclose(m.V, want_v, rtol=0, atol=1e-12))

    def test_red_is_a_fixed_point(self):
        m = M.Model(np.ones((M.N, M.N)), np.zeros((M.N, M.N)), 0.02, 0.059)
        m.step(50)
        self.assertTrue(np.array_equal(m.U, np.ones((M.N, M.N))) and not m.V.any())

    def test_coefficients(self):
        self.assertEqual(M.H, 5 / 512)
        self.assertAlmostEqual(M.CU, 0.2097152, places=12)
        self.assertAlmostEqual(M.CV, 0.1048576, places=12)
        self.assertLess(M.CU, 0.25)                                      # forward Euler's limit in two dimensions


class Spots(unittest.TestCase):
    def test_torus_and_adjacency(self):
        mask = np.zeros((M.N, M.N), bool)
        mask[0:3, 10:13] = True
        mask[-2:, 10:13] = True                                           # the same spot, across the top edge
        mask[50, 0] = mask[50, -1] = True                                 # and across the side edge
        mask[100, 100] = mask[101, 101] = True                            # diagonal: two spots
        lab, n = M.spots(mask)
        self.assertEqual(n, 4)
        self.assertEqual(lab[0, 10], lab[-1, 10])
        self.assertEqual(lab[50, 0], lab[50, -1])
        self.assertNotEqual(lab[100, 100], lab[101, 101])
        self.assertEqual([int(lab[0, 10]), int(lab[50, 0]), int(lab[100, 100])], [1, 2, 3])   # first-point order
        self.assertEqual(int(np.bincount(lab.ravel())[1]), 15)


class Tracking(unittest.TestCase):
    def feed(self, frames):
        tr = M.Tracker()
        for i, mask in enumerate(frames, start=1):
            tr.see(*M.spots(mask), 100 * i)
        return tr.summary()

    def test_division_lineages_and_growth(self):
        f1 = disc(100, 100, 5)
        f2 = disc(100, 100, 7)
        f3 = disc(100, 93, 4) | disc(100, 107, 4)                         # a division in two
        f4 = disc(100, 90, 6) | disc(100, 110, 6)                         # both grow
        f5 = disc(94, 90, 4) | disc(106, 90, 4) | disc(94, 110, 4) | disc(106, 110, 4)   # both divide in two
        s = self.feed([f1, f2, f3, f4, f5])
        self.assertEqual((s["splits"], s["divisions"], s["merges"], s["births"], s["deaths"]), (3, 3, 0, 0, 0))
        self.assertEqual(s["lineages"], 2)
        area4, area6 = int(disc(0, 0, 4).sum()), int(disc(0, 0, 6).sum())
        self.assertAlmostEqual(s["growth_median"], area6 / area4)
        self.assertEqual(s["reproduction_median"], 200.0)                 # first seen at 300, daughters at 500
        self.assertEqual(s["dividing_median"], float(area6))
        self.assertEqual(s["spots_at_end"], 4)

    def test_three_merge_birth_death(self):
        one = disc(50, 50, 8)
        three = disc(44, 50, 3) | disc(56, 44, 3) | disc(56, 56, 3)
        s = self.feed([one, three])
        self.assertEqual((s["splits"], s["divisions"]), (1, 0))
        two = disc(50, 44, 4) | disc(50, 56, 4)
        merged = disc(50, 50, 9)
        s = self.feed([two, merged])
        self.assertEqual((s["merges"], s["splits"]), (1, 0))
        s = self.feed([disc(20, 20, 4), disc(200, 200, 4)])
        self.assertEqual((s["births"], s["deaths"]), (1, 1))

    def test_a_daughter_with_a_second_parent(self):
        before = disc(50, 50, 5) | disc(50, 64, 2)
        after = disc(50, 46, 3) | (disc(50, 56, 3) | disc(50, 62, 3))     # the right daughter also covers the small one
        s = self.feed([before, after])
        self.assertEqual((s["splits"], s["divisions"], s["merges"]), (1, 0, 1))


class Verdict(unittest.TestCase):
    def summary(self, **kw):
        s = {"divisions": 50, "splits": 55, "lineages": 20, "growth_median": 1.5, "dividing_cv": 0.25,
             "sightings": 1000, "oversize": 10, "spots_at_end": 20}
        s.update(kw)
        return s

    def test_at_and_beside_each_threshold(self):
        self.assertEqual(sum(M.conditions(self.summary()).values()), 6)
        for bad in (dict(divisions=49, splits=54), dict(splits=56), dict(lineages=19), dict(growth_median=1.4999),
                    dict(dividing_cv=0.2501), dict(oversize=11), dict(spots_at_end=19)):
            with self.subTest(bad=bad):
                self.assertEqual(sum(M.conditions(self.summary(**bad)).values()), 5)

    def test_line_is_short(self):
        s = {**self.summary(), "dividing_mean": 149.123, "oversize_fraction": 0.01}
        text = M.line({"k": 0.0625, "F": 0.025, "trackers": {"U<0.5": s}})
        self.assertLessEqual(len(text), 200)
        self.assertTrue(text.endswith("6 of 6"))


class Run(unittest.TestCase):
    def test_one_short_run(self):
        with tempfile.TemporaryDirectory() as d:
            out, detail = M.run(SEED, results=d, steps=2000, points=M.POINTS[3:4], log=None)
            self.assertEqual(sorted(os.listdir(d)), ["detail.json", "outputs.json"])
        self.assertEqual(tuple(out), M.OUTPUTS)
        self.assertEqual([k for k in M.OUTPUTS[:9] if out[k] == "not run"],
                         [k for k in M.OUTPUTS[:9] if k != "epsilon_4"])
        first = detail["points"][0]["trackers"]["U<0.5"]["first"]
        self.assertEqual(first[0][0], 600)                                # the first division, at step 600
        self.assertGreater(first[0][1], 1.5 * max(first[0][2]))
        self.assertEqual(out["conditions_total"], 6)


if __name__ == "__main__":
    unittest.main()
