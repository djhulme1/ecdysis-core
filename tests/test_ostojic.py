"""Ostojic's network check: the connections, the refractory period losing its input, the delay, the J = 0 period, the
Fano factor and the spread on spikes of known shape, the mean-field rate against an independent implementation, and the
test's three conditions, each shown failing where it should.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import math
import os
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("snn_ostojic", os.path.join(HERE, "..", "snn", "ostojic.py"))
O = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(O)

SEED = "0" * 63 + "7"


def one_link(pre, post, n):
    """A network of n neurons whose only connection is pre -> post, excitatory."""
    targets = np.array([post], dtype=np.int32)
    excit = np.array([True])
    starts = np.zeros(n + 1, dtype=np.int64)
    starts[pre + 1:] = 1
    return targets, excit, starts


class Connections(unittest.TestCase):
    def test_exact_in_degrees_no_autapses(self):
        targets, excit, starts = O.network(np.random.default_rng(3), ne=40, ni=10, ce=8, ci=2)
        incoming = {i: [] for i in range(50)}
        for j in range(50):
            for t, e in zip(targets[starts[j]:starts[j + 1]], excit[starts[j]:starts[j + 1]]):
                incoming[int(t)].append((j, bool(e)))
        for i, pre in incoming.items():
            self.assertEqual(sum(1 for _, e in pre if e), 8)
            self.assertEqual(sum(1 for _, e in pre if not e), 2)
            self.assertNotIn(i, [j for j, _ in pre])
            self.assertEqual(len(set(j for j, _ in pre)), 10)

    def test_the_same_seed_draws_the_same_network(self):
        a = O.network(O.rng_for(SEED, "network"), ne=40, ni=10, ce=8, ci=2)
        b = O.network(O.rng_for(SEED, "network"), ne=40, ni=10, ce=8, ci=2)
        c = O.network(O.rng_for(SEED[:-1] + "8", "network"), ne=40, ni=10, ce=8, ci=2)
        self.assertTrue(all(np.array_equal(x, y) for x, y in zip(a, b)))
        self.assertFalse(np.array_equal(a[0], c[0]))


class Dynamics(unittest.TestCase):
    def test_at_j_zero_every_interval_is_2556_steps(self):
        n = 20
        net = (np.zeros(0, np.int32), np.zeros(0, bool), np.zeros(n + 1, np.int64))
        st, si = O.simulate(net, 0.0, np.linspace(O.VR, O.THETA - 0.01, n), 20_000, 0)
        for i in range(n):
            t = np.sort(st[si == i])
            self.assertTrue((np.diff(t) == 2556).all(), np.diff(t)[:5])
        expected = O.REF_MS + O.TAU_MS * math.log((O.MU0 - O.VR) / (O.MU0 - O.THETA))
        self.assertAlmostEqual(2556 * O.DT_MS, expected, delta=O.DT_MS)

    def first_crossing(self, v0):
        """The step at which a neuron starting at v0, with no input, first reaches threshold."""
        decay = math.exp(-O.DT_MS / O.TAU_MS)
        v, k = v0, 0
        while True:
            v = O.MU0 + (v - O.MU0) * decay
            if v >= O.THETA:
                return k
            k += 1

    def test_an_input_arrives_exactly_after_the_delay(self):
        # Neuron 0 starts at threshold and fires at step 0; neuron 1, at 15 mV, would need over 1,600 steps on its own,
        # but the 30 mV input reaches it 55 steps (0.55 ms) later and fires it then.
        self.assertEqual(O.steps_of(O.DELAY_MS), 55)
        self.assertGreater(self.first_crossing(15.0), 1600)
        st, si = O.simulate(one_link(0, 1, 2), 30.0, np.array([O.THETA, 15.0]), 200, 0)
        self.assertEqual(list(zip(st.tolist(), si.tolist())), [(0, 0), (55, 1)])

    def test_an_input_that_arrives_while_refractory_is_lost(self):
        # Neuron 1 starts just under threshold and fires on its own at step 29; it is refractory for steps 30 to 79, so
        # the 30 mV input of step 55 is lost and it does not fire again within 200 steps.
        k = self.first_crossing(19.94)
        self.assertEqual(k, 29)
        st, si = O.simulate(one_link(0, 1, 2), 30.0, np.array([O.THETA, 19.94]), 200, 0)
        self.assertEqual(list(zip(st.tolist(), si.tolist())), [(0, 0), (29, 1)])
        # The same input after the refractory period counts: neuron 1 fires at step 0 with neuron 0, is refractory for
        # steps 1 to 50, and the input of step 55 fires it again.
        st, si = O.simulate(one_link(0, 1, 2), 30.0, np.array([O.THETA, O.THETA]), 200, 0)
        self.assertEqual(list(zip(st.tolist(), si.tolist())), [(0, 0), (0, 1), (55, 1)])

    def test_spikes_before_the_window_are_not_reported(self):
        st, si = O.simulate(one_link(0, 1, 2), 30.0, np.array([O.THETA, 15.0]), 200, 10)
        self.assertEqual(list(zip(st.tolist(), si.tolist())), [(45, 1)])


class Measures(unittest.TestCase):
    def test_controls_pass(self):
        rows = O.controls(SEED)
        self.assertEqual([r["passed"] for r in rows], [True, True, True, True], rows)

    def test_fano_of_a_burst_train_is_large_and_of_a_regular_one_zero(self):
        n, steps = 10, O.steps_of(10_000.0)
        per = O.steps_of(100.0)
        # Each neuron fires 20 spikes in every fifth 100 ms window and none otherwise: counts 20, 0, 0, 0, 0, ...
        t = np.concatenate([np.arange(w * per, w * per + 20) for w in range(0, 100, 5)])
        st = np.tile(t, n)
        si = np.repeat(np.arange(n), t.size)
        f, fired = O.fano(st, si, n, steps)
        self.assertEqual(fired, n)
        self.assertAlmostEqual(f, (np.var([20, 0, 0, 0, 0]) / 4.0), places=9)
        reg = np.arange(0, steps, O.steps_of(50.0))
        f2, _ = O.fano(np.tile(reg, n), np.repeat(np.arange(n), reg.size), n, steps)
        self.assertEqual(f2, 0.0)

    def test_the_spread_is_zero_for_identical_neurons_and_grows_with_their_differences(self):
        n, steps = 50, O.steps_of(10_000.0)
        t = np.arange(0, steps, O.steps_of(25.0))
        same = O.spread(np.tile(t, n), np.repeat(np.arange(n), t.size), n, steps, chunk=20)
        self.assertLess(same, 1e-5)
        # Half the neurons fire twice as often: rates 40 and 80 Hz, so the spread is 20 Hz once the ripple is filtered.
        t2 = np.arange(0, steps, O.steps_of(12.5))
        st = np.concatenate([np.tile(t, 25), np.tile(t2, 25)])
        si = np.concatenate([np.repeat(np.arange(25), t.size), np.repeat(np.arange(25, 50), t2.size)])
        self.assertAlmostEqual(O.spread(st, si, n, steps, chunk=20), 20.0, delta=0.05)

    def test_the_mean_field_rate_agrees_with_an_independent_implementation(self):
        # scipy's quad and brentq (the sweep's pilot, outside the image) gave 13.73 and 13.82 Hz.
        self.assertAlmostEqual(O.mean_field_rate(0.2), 13.73, delta=0.01)
        self.assertAlmostEqual(O.mean_field_rate(0.8), 13.82, delta=0.01)


class Conditions(unittest.TestCase):
    def m(self, f02, f08, s02, s08):
        return {"J0.2": {"fano": f02, "spread": s02}, "J0.8": {"fano": f08, "spread": s08}}

    def test_all_three_hold(self):
        self.assertTrue(all(O.conditions(self.m(0.7, 8.0, 7.0, 35.0)).values()))

    def test_each_fails_alone(self):
        self.assertEqual(list(O.conditions(self.m(0.7, 2.0, 7.0, 35.0)).values()), [False, True, True])
        self.assertEqual(list(O.conditions(self.m(0.7, 8.0, 7.0, 13.9)).values()), [True, False, True])
        self.assertEqual(list(O.conditions(self.m(1.2, 8.0, 7.0, 35.0)).values()), [True, True, False])
        self.assertTrue(O.conditions(self.m(0.7, 8.0, 7.0, 14.0))["spread at 0.8 mV at least twice that at 0.2 mV"])


if __name__ == "__main__":
    unittest.main()
