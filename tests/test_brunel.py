"""Brunel's model A check: the connections (exact in-degrees, no autapses, the presynaptic index), the refractory
period and the window in a small network, the ISI CV and the Welch peak on spikes of known shape, the 25% span, and the
ten conditions.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import os
import unittest
from unittest import mock

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("snn_brunel", os.path.join(HERE, "..", "snn", "brunel.py"))
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)

SEED = "0" * 63 + "9"
SMALL = dict(NE=50, NI=20, CE=10, CI=4)


class Connections(unittest.TestCase):
    def test_no_autapses_and_distinct(self):
        rng = np.random.default_rng(1)
        for post in (0, 7, 49):
            draw = B.presynaptic(rng, 50, 10, post, 0, True)
            self.assertNotIn(post, draw)
            self.assertEqual(len(set(draw.tolist())), 10)
            self.assertTrue(((draw >= 0) & (draw < 50)).all())
        draw = B.presynaptic(rng, 20, 4, 55, 50, True)
        self.assertNotIn(55, draw)
        self.assertTrue(((draw >= 50) & (draw < 70)).all())

    def test_exact_in_degrees(self):
        with mock.patch.multiple(B, **SMALL):
            targets, excit, starts = B.network(np.random.default_rng(2))
        n = 70
        incoming = {i: [] for i in range(n)}
        for j in range(n):
            for t in targets[starts[j]:starts[j + 1]]:
                incoming[int(t)].append(j)
        for i in range(n):
            self.assertEqual(sum(1 for j in incoming[i] if j < 50), 10)
            self.assertEqual(sum(1 for j in incoming[i] if j >= 50), 4)
            self.assertNotIn(i, incoming[i])
        self.assertEqual(int(excit.sum()), 70 * 10)


class Dynamics(unittest.TestCase):
    def test_refractory_and_window(self):
        with mock.patch.multiple(B, TRANSIENT_S=0.01, ANALYSIS_S=0.05, **SMALL):
            with mock.patch.dict(B.POINTS, {"A": (3.0, 8.0)}):
                st, si, pop = B.simulate(SEED, "A")
        self.assertGreater(st.size, 0)
        self.assertEqual(pop.size, 500)
        self.assertEqual(int(pop.sum()), st.size)
        self.assertTrue(((st >= 0) & (st < 500)).all())
        order = np.lexsort((st, si))
        st, si = st[order], si[order]
        same = si[1:] == si[:-1]
        self.assertGreaterEqual(int((st[1:] - st[:-1])[same].min()), B.REF_STEPS + 1)

    def test_the_seed_draws_everything(self):
        with mock.patch.multiple(B, TRANSIENT_S=0.0, ANALYSIS_S=0.02, **SMALL):
            with mock.patch.dict(B.POINTS, {"A": (3.0, 8.0)}):
                a = B.simulate(SEED, "A")
                b = B.simulate(SEED, "A")
                c = B.simulate("1" * 64, "A")
        self.assertTrue(all(np.array_equal(x, y) for x, y in zip(a, b)))
        self.assertFalse(np.array_equal(a[2], c[2]))


class Measures(unittest.TestCase):
    def test_cv(self):
        st = np.array([0, 10, 20, 30, 0, 5, 20, 25, 40, 0, 3, 9])
        si = np.array([0, 0, 0, 0, 1, 1, 1, 1, 1, 2, 2, 2])
        cv, used = B.cv_of(st, si)
        self.assertEqual(used, 2)                  # neuron 2 has two intervals only
        self.assertAlmostEqual(cv, 0.25)            # 0 and 0.5

    def test_welch_peak(self):
        steps, n = int(round(B.ANALYSIS_S * 1e3 / B.DT_MS)), 1000
        t = np.arange(steps) * B.DT_MS * 1e-3
        pop = np.rint(5 * (1 + np.sin(2 * np.pi * 40 * t))).astype(np.int64)
        f, p = B.peak(*B.welch(pop, n))
        self.assertAlmostEqual(f, 40.0)
        self.assertGreater(p, 0)

    def test_span(self):
        span = B.RATE_SPAN["B"]
        self.assertTrue(B.within(41.85, span) and B.within(75.875, span))
        self.assertFalse(B.within(41.8, span) or B.within(75.9, span))

    def test_conditions(self):
        good = {"A": {"cv": 0.01, "rate": 300, "frequency": 330, "peak_power": 9},
                "B": {"cv": 0.8, "rate": 59, "frequency": 184, "peak_power": 100},
                "C": {"cv": 0.4, "rate": 37, "frequency": 140, "peak_power": 5},
                "D": {"cv": 0.5, "rate": 5, "frequency": 24, "peak_power": 3}}
        self.assertTrue(all(B.conditions(good).values()))
        bad = {k: dict(v) for k, v in good.items()}
        bad["C"]["peak_power"] = 11
        c = B.conditions(bad)
        self.assertEqual([k for k, v in c.items() if not v], ["C peak under a tenth of B's"])
        self.assertEqual(len(c), 10)

    def test_controls(self):
        rows = B.controls(SEED)
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r["passed"] for r in rows), rows)


if __name__ == "__main__":
    unittest.main()
