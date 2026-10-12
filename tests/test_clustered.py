"""The clustered balanced network (snn/clustered.py): the clustering rule against the paper's 38 of 800 in-cluster
inputs; the drawn connections, weights and biases; the integrator on a neuron with no inputs (its interspike interval in
closed form); the counts, the Fano factor (zero means skipped, both denominators) and the in-cluster correlation on hand
examples; the controls; and the verdict at and beside each condition.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import math
import os
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("snn_clustered", os.path.join(HERE, "..", "snn", "clustered.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "0" * 64


class Clustering(unittest.TestCase):
    def test_the_rule_gives_the_papers_38_of_800(self):
        p_out, p_in = M.p_out_in()
        self.assertAlmostEqual(p_in / p_out, 2.5)
        within, total = (M.C - 1) * p_in, (M.C - 1) * p_in + (M.NE - M.C) * p_out
        self.assertEqual(round(within), 38)
        self.assertAlmostEqual(total, 800, delta=1.0)

    def test_drawn_networks(self):
        for clustered in (False, True):
            with self.subTest(clustered=clustered):
                WT, mu = M.network(np.random.default_rng(1), clustered)
                W = WT.T
                self.assertTrue(set(np.unique(W)) <= {0, 240, 456, -450, 140, -570})
                self.assertEqual(int(np.count_nonzero(np.diag(W))), 0)
                ee = W[:M.NE, :M.NE] != 0
                self.assertAlmostEqual(ee.mean(), 0.2, delta=0.002)
                block = ee[:M.C, :M.C]
                if clustered:
                    p_out, p_in = M.p_out_in()
                    self.assertTrue(set(np.unique(W[:M.C, :M.C])) <= {0, 456})
                    self.assertAlmostEqual(block.sum() / (M.C * (M.C - 1)), p_in, delta=0.03)
                    self.assertTrue(set(np.unique(W[:M.C, M.C:M.NE])) <= {0, 240})
                else:
                    self.assertTrue(set(np.unique(W[:M.NE, :M.NE])) <= {0, 240})
                for rows, cols, p in ((slice(0, M.NE), slice(M.NE, M.N), 0.5), (slice(M.NE, M.N), slice(0, M.NE), 0.5),
                                      (slice(M.NE, M.N), slice(M.NE, M.N), 0.5)):
                    self.assertAlmostEqual((W[rows, cols] != 0).mean(), p, delta=0.01)
                self.assertTrue(np.all((mu[:M.NE] >= 1.1) & (mu[:M.NE] <= 1.2)))
                self.assertTrue(np.all((mu[M.NE:] >= 1.0) & (mu[M.NE:] <= 1.05)))


class Integrator(unittest.TestCase):
    def test_a_neuron_without_inputs_fires_at_the_closed_form_interval(self):
        WT = np.zeros((M.N, M.N), dtype=np.int16)
        mu = np.full(M.N, 0.5)
        mu[0], mu[M.NE] = 1.2, 1.05                              # one excitatory and one inhibitory neuron above threshold
        times, cells = M.simulate(WT, mu, np.zeros(M.N), t_end=300.0)
        for cell, tau in ((0, M.TAU_E), (M.NE, M.TAU_I)):
            t = times[cells == cell]
            isi = np.diff(t)
            want = tau * math.log(mu[cell] / (mu[cell] - 1.0)) + M.REF
            self.assertGreater(len(t), 3)
            self.assertTrue(np.all(np.abs(isi - want) < 0.3), (cell, isi, want))
        self.assertEqual(set(cells.tolist()), {0, M.NE})          # the others stay below threshold

    def test_an_excitatory_spike_raises_its_target(self):
        WT = np.zeros((M.N, M.N), dtype=np.int16)
        WT[1, 0] = 456                                           # neuron 1 onto neuron 0
        mu = np.zeros(M.N)
        mu[0], mu[1] = 0.99, 1.2                                 # neuron 0 rests just below threshold on its own
        v0 = np.zeros(M.N)
        v0[0] = 0.99
        times, cells = M.simulate(WT, mu, v0, t_end=60.0)
        self.assertIn(1, cells.tolist())
        self.assertIn(0, cells.tolist())                         # one input of 0.0456 tips it over
        self.assertGreater(times[cells == 0][0], times[cells == 1][0])
        alone, _ = M.simulate(np.zeros((M.N, M.N), dtype=np.int16), mu, v0, t_end=60.0)
        self.assertEqual(int(np.sum(_ == 0)), 0)                  # without the input it never fires


class Statistics(unittest.TestCase):
    def test_counts_in_windows(self):
        times = np.array([1499.9, 1500.0, 1599.9, 1600.0, 2999.9, 3000.0, 1550.0])
        cells = np.array([0, 0, 0, 0, 0, 0, M.NE])                # the last is inhibitory: not counted
        c = M.counts(times, cells, 100.0)
        self.assertEqual(c.shape, (M.NE, 15))
        self.assertEqual((c[0, 0], c[0, 1], c[0, 14], int(c.sum())), (2, 1, 1, 4))

    def test_fano_factor(self):
        stack = np.zeros((3, 3, 2), dtype=np.int64)              # trials x neurons x windows
        stack[:, 0, 0] = [1, 2, 3]                                 # mean 2, sample var 1: 0.5
        stack[:, 0, 1] = [0, 0, 6]                                 # mean 2, sample var 12: 6
        stack[:, 1, 0] = [2, 2, 2]                                 # var 0: 0; window 1 all zero: skipped
        ff = M.fano_per_neuron(stack)
        self.assertAlmostEqual(ff[0], (0.5 + 6.0) / 2)
        self.assertAlmostEqual(ff[1], 0.0)
        self.assertTrue(math.isnan(ff[2]))
        ff9 = M.fano_per_neuron(stack, ddof=0)
        self.assertAlmostEqual(ff9[0], ((2 / 3) / 2 + 8.0 / 2) / 2)

    def test_correlation_in_blocks(self):
        rng = np.random.default_rng(3)
        stack = np.zeros((2, M.NE, 30), dtype=np.int64)
        base = rng.poisson(2.0, size=30)
        stack[:, :M.C, :] = base                                 # the first block moves together
        stack[:, M.C:2 * M.C, :] = rng.poisson(2.0, size=(2, M.C, 30))
        r = M.corr_in_blocks(stack)
        n_pairs = M.C * (M.C - 1) // 2
        self.assertGreater(r, 0.9 * n_pairs / (2 * n_pairs))      # block 1 contributes 1 per pair, block 2 about 0

    def test_controls_pass(self):
        ctl = M.controls(SEED)
        self.assertTrue(all(v[1] for v in ctl.values()), ctl)


class Verdict(unittest.TestCase):
    def test_at_and_beside_each_condition(self):
        self.assertTrue(all(M.conditions({"clustered": 1.1, "uniform": 0.79}).values()))
        for ff in ({"clustered": 1.0, "uniform": 0.5}, {"clustered": 1.2, "uniform": 0.9}):
            with self.subTest(ff=ff):
                self.assertEqual(sum(M.conditions(ff).values()), 1)


if __name__ == "__main__":
    unittest.main()
