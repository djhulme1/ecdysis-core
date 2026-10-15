"""EventProp's check (snn/eventprop.py): the exact dynamics, the crossing, the local maxima and margins, the losses,
the closed adjoint, and EventProp against derivatives worked out here by other means (the implicit function theorem
and the chain rule on closed-form trajectories) for single neurons, a chain of two and a readout. Every network
simulated here is made by hand; the scenarios' draws are built from a test seed only to check their shapes and
streams, never simulated, and EventProp is never compared with central differences on one.

Run with: python3 -m unittest tests.test_eventprop
"""

import importlib.util
import json
import math
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("snn_eventprop", os.path.join(HERE, "..", "snn", "eventprop.py"))
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)

SEED = "5a" * 32
K, AL, BE, TH = E.KAPPA, E.ALPHA, E.BETA, E.THETA


def g(u):
    return math.exp(-AL * u) - math.exp(-BE * u)


def gp(u):
    return -AL * math.exp(-AL * u) + BE * math.exp(-BE * u)


def G2(x):
    """The integral of g^2 over [0, x], written out term by term."""
    return ((1 - math.exp(-2 * AL * x)) / (2 * AL) - 2 * (1 - math.exp(-(AL + BE) * x)) / (AL + BE)
            + (1 - math.exp(-2 * BE * x)) / (2 * BE))


def root(f, lo, hi):
    """Bisection for f(lo) < 0 <= f(hi)."""
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if mid in (lo, hi):
            break
        if f(mid) < 0:
            lo = mid
        else:
            hi = mid
    return hi


def crossing_after_kick(w):
    """The u where kappa w g(u) = theta first, from rest."""
    return root(lambda u: K * w * g(u) - TH, 0.0, math.log(BE / AL) / (BE - AL))


def simpson(f, a, b, n=20000):
    h = (b - a) / n
    s = f(a) + f(b) + sum((4 if i % 2 else 2) * f(a + i * h) for i in range(1, n))
    return s * h / 3


class Dynamics(unittest.TestCase):
    def test_closed_form_against_rk4(self):
        for V0, I0 in ((0.3, 1.7), (-0.2, -0.6), (0.9, 0.0)):
            A, B = E.coeffs(V0, I0)
            V, I = [V0], [I0]
            for _ in range(2000):
                V, I = E._rk4_step(V, I, 0.005)
            self.assertAlmostEqual(E.v_at(A, B, 10.0), V[0], places=11)
            self.assertAlmostEqual(I0 * math.exp(-BE * 10.0), I[0], places=11)

    def test_critical_point(self):
        A, B = E.coeffs(0.0, 2.0)
        us = E.critical(A, B)
        self.assertAlmostEqual(us, math.log(BE / AL) / (BE - AL), places=12)
        self.assertLess(abs(E.dv_at(A, B, us)), 1e-15)
        self.assertIsNone(E.critical(*E.coeffs(0.5, 0.0)))
        self.assertLess(E.critical(*E.coeffs(0.5, 0.2)), 0.0)  # falls from the start: its turn is before it

    def test_first_crossing(self):
        A, B = E.coeffs(0.0, 9.0)
        u = E.first_crossing(A, B, 30.0)
        self.assertLess(abs(E.v_at(A, B, u) - TH), 1e-14)
        self.assertAlmostEqual(u, crossing_after_kick(9.0), places=12)
        self.assertIsNone(E.first_crossing(*E.coeffs(0.0, 5.0), 30.0))  # its maximum is 0.79
        self.assertIsNone(E.first_crossing(A, B, 0.5 * u))  # not yet within the interval
        self.assertIsNone(E.first_crossing(*E.coeffs(0.7, -0.5), 200.0))  # falls from 0.7
        A, B = E.coeffs(0.6, 5.0)  # rises from 0.6 at once
        u = E.first_crossing(A, B, 50.0)
        self.assertLess(abs(E.v_at(A, B, u) - TH), 1e-14)
        self.assertGreater(E.dv_at(A, B, u), 0.0)
        self.assertTrue(all(E.v_at(A, B, x * u / 100) < TH for x in range(100)))

    def test_simulation_against_rk4(self):
        W = [[0.0, -0.4], [0.8, 0.0]]
        W_in = [[3.0, 2.5], [1.0, 0.0]]
        inputs = [(1.0, 0), (1.6, 0), (3.0, 1), (7.5, 0), (8.0, 0), (12.0, 0), (20.0, 1), (22.0, 0), (22.5, 0),
                  (35.0, 0), (36.0, 0), (36.4, 0)]
        net = E.Net(W, W_in, inputs)
        ev = [(t, m) for t, m, _ in E.simulate(net, T=60.0)["spikes"]]
        fine = E.rk4_network(net, 60.0, 0.002)
        self.assertGreater(len(ev), 2)
        self.assertEqual([m for _, m in ev], [m for _, m in fine])
        for (t1, _), (t2, _) in zip(ev, fine):
            self.assertLess(abs(t1 - t2), 1e-7)

    def test_events_begin_their_segments(self):
        net = E.Net([[0.0, 0.5], [0.9, 0.0]], [[9.0], [2.0]], [(2.0, 0), (2.0, 0), (30.0, 0)])
        rec = E.simulate(net, observe=((15.0, 1, 1.0),))
        for e in rec["events"]:
            self.assertEqual(rec["segments"][e[4]][0], e[0])
        self.assertEqual([e[4] for e in rec["events"]], sorted(set(e[4] for e in rec["events"])))
        for k in range(1, len(rec["segments"])):
            self.assertEqual(rec["segments"][k][0], rec["segments"][k - 1][1])
        self.assertEqual(rec["segments"][-1][1], E.T_END)

    def test_shapes_refused(self):
        with self.assertRaises(E.Refused):
            E.Net([[0.5]], [[1.0]], [])
        with self.assertRaises(E.Refused):
            E.Net([[0.0, 0.1], [0.1, 0.0]], [[1.0]], [])
        with self.assertRaises(E.Refused):
            E.Net([[0.0]], [[1.0]], [(1.0, 1)])


class Maxima(unittest.TestCase):
    def test_interior_corner_and_end(self):
        net = E.Net([[0.0]], [[0.5, -2.0]], [(5.0, 0), (8.0, 1)])
        loc = E.local_maxima(E.simulate(net), 0)
        self.assertEqual([x[2] for x in loc], ["corner", "end"])  # pushed below 0, it climbs back until T
        self.assertEqual(loc[0][1], 8.0)
        self.assertLess(loc[1][0], 0.0)
        self.assertAlmostEqual(loc[0][0], 0.5 * K * g(3.0), places=14)
        net = E.Net([[0.0]], [[0.5]], [(5.0, 0)])
        loc = E.local_maxima(E.simulate(net), 0)
        us = math.log(BE / AL) / (BE - AL)
        self.assertEqual([x[2] for x in loc], ["interior"])
        self.assertAlmostEqual(loc[0][1], 5.0 + us, places=10)
        net = E.Net([[0.0]], [[0.5]], [(98.0, 0)])
        loc = E.local_maxima(E.simulate(net), 0)
        self.assertEqual([x[2] for x in loc], ["end"])

    def test_margins(self):
        us = math.log(BE / AL) / (BE - AL)
        near = (TH - 0.005) / (K * g(us))
        rec = E.simulate(E.Net([[0.0]], [[near]], [(5.0, 0)]))
        self.assertAlmostEqual(rec["margins"]["v"], 0.005, places=10)
        self.assertFalse(E.non_critical(rec))
        rec = E.simulate(E.Net([[0.0]], [[(TH - 0.05) / (K * g(us))]], [(5.0, 0)]))
        self.assertTrue(E.non_critical(rec))
        self.assertFalse(E.non_critical(rec, need={0}))
        ts = 2.0 + crossing_after_kick(9.0)
        rec = E.simulate(E.Net([[0.0]], [[9.0, 0.01]], [(2.0, 0), (ts + 5e-5, 1)]))
        self.assertLess(rec["margins"]["event"], 1e-4)
        self.assertFalse(E.non_critical(rec, need={0}))
        rec = E.simulate(E.Net([[0.0]], [[9.0, 0.01]], [(2.0, 0), (ts + 0.5, 1)]))
        self.assertTrue(E.non_critical(rec, need={0}))
        self.assertAlmostEqual(rec["margins"]["dv"], 9.0 * math.exp(-BE * (ts - 2.0)) - TH, places=12)
        rec = E.simulate(E.Net([[0.0]], [[9.0]], [(E.T_END - (ts - 2.0) - 0.005, 0)]))
        self.assertEqual(len(rec["spikes"]), 1)
        self.assertFalse(E.non_critical(rec))

    def test_readout_margins(self):
        us = math.log(BE / AL) / (BE - AL)
        first = K * 0.7 * g(us)
        for w2, close in ((0.66, True), (0.5, False)):
            net = E.Net([[0.0]], [[0.7, w2]], [(10.0, 0), (60.0, 1)], firing=[False])
            rec = E.simulate(net, track_readout=0)
            tm = root(lambda t: -(0.7 * gp(t - 10.0) + w2 * gp(t - 60.0)), 60.0, 90.0)
            second = K * (0.7 * g(tm - 10.0) + w2 * g(tm - 60.0))
            self.assertAlmostEqual(rec["margins"]["readout"], abs(first - second), places=10)
            self.assertEqual(abs(first - second) < E.MARGIN_V, close)
            self.assertEqual(E.non_critical(rec, readout=True), not close)
            self.assertEqual(rec["rmax"][2], "interior")

    def test_structure_sees_a_spike_pass_an_input(self):
        ts = 2.0 + crossing_after_kick(9.0)
        net = E.Net([[0.0]], [[9.0, 0.01]], [(2.0, 0), (ts + 1e-6, 1)])
        base = E.structure(E.simulate(net))
        net.W_in[0][0] = 9.0 - 1e-3
        self.assertNotEqual(E.structure(E.simulate(net)), base)
        net.W_in[0][0] = 9.0 + 1e-3
        self.assertEqual(E.structure(E.simulate(net)), base)


class Losses(unittest.TestCase):
    def test_v2_integral(self):
        for A, B, D in ((0.8, -0.5, 7.0), (-1.2, 2.0, 40.0), (0.0, 1.0, 3.0)):
            want = simpson(lambda u: E.v_at(A, B, u) ** 2, 0.0, D)
            self.assertAlmostEqual(E.seg_v2_integral(A, B, D), want, places=10)

    def test_values(self):
        net = E.Net([[0.0, 0.0], [7.5, 0.0]], [[9.0], [0.0]], [(2.0, 0)])
        rec = E.simulate(net)
        t0 = 2.0 + crossing_after_kick(9.0)
        t1 = t0 + crossing_after_kick(7.5)
        self.assertEqual([n for _, n, _ in rec["spikes"]], [0, 1])
        self.assertAlmostEqual(E.Loss("sum_t", neurons=(0, 1)).value(rec), t0 + t1, places=11)
        self.assertAlmostEqual(E.Loss("sum_t2", neurons=(1,)).value(rec), t1 * t1 / E.T_END, places=11)
        net = E.Net([[0.0]], [[0.7, 0.5]], [(10.0, 0), (14.0, 1)], firing=[False])
        rec = E.simulate(net, observe=((30.0, 0, 2.0),), track_readout=0)
        self.assertAlmostEqual(E.Loss("observe").value(rec), 2.0 * K * (0.7 * g(20.0) + 0.5 * g(16.0)), places=13)
        Vf = lambda t: K * (0.7 * g(t - 10.0) * (t > 10.0) + 0.5 * g(t - 14.0) * (t > 14.0))
        tm = root(lambda t: -(0.7 * gp(t - 10.0) + 0.5 * gp(t - 14.0)), 14.0, 40.0)
        self.assertAlmostEqual(E.Loss("max", readout=0).value(rec), Vf(tm), places=13)
        v2 = E.Loss("v2", c=[0.3]).value(rec)
        want = 0.15 * (simpson(lambda t: Vf(t) ** 2, 10.0, 14.0, 4000) + simpson(lambda t: Vf(t) ** 2, 14.0, 100.0))
        self.assertAlmostEqual(v2, want, places=9)


class Adjoint(unittest.TestCase):
    def test_closed_segment_against_rk4(self):
        for lv, li, A, B, D, c in ((1.5, 0.7, -0.4, 1.1, 12.0, 0.2), (0.0, -0.3, 0.0, 0.0, 5.0, 0.0),
                                   (-0.2, 0.0, 2.0, -2.0, 60.0, 0.01)):
            x = E.back_segment(lv, li, A, B, D, c)
            y = E.rk4_adjoint(lv, li, A, B, D, c, 6000)
            self.assertAlmostEqual(x[0], y[0], places=11)
            self.assertAlmostEqual(x[1], y[1], places=11)

    def test_zero_length_segment(self):
        x = E.back_segment(0.4, -0.1, 1.0, -1.0, 0.0, 0.3)
        self.assertAlmostEqual(x[0], 0.4, places=15)
        self.assertAlmostEqual(x[1], -0.1, places=15)


class AgainstOtherDerivatives(unittest.TestCase):
    """EventProp on hand-made networks, against derivatives from the implicit function theorem and the chain rule."""

    def test_one_neuron_one_spike(self):
        w = 9.0
        net = E.Net([[0.0]], [[w]], [(5.0, 0)])
        rec = E.simulate(net)
        u = crossing_after_kick(w)
        want = -g(u) / (w * gp(u))
        _, gin = E.eventprop(net, rec, E.Loss("sum_t", neurons=(0,)))
        self.assertAlmostEqual(gin[0][0] / want, 1.0, places=11)
        _, gin = E.eventprop(net, rec, E.Loss("sum_t2", neurons=(0,)))
        self.assertAlmostEqual(gin[0][0] / (2 * (5.0 + u) / E.T_END * want), 1.0, places=11)

    def test_coincident_inputs(self):
        net = E.Net([[0.0]], [[5.0, 4.0]], [(2.0, 0), (2.0, 1)])
        rec = E.simulate(net)
        u = crossing_after_kick(9.0)
        want = -g(u) / (9.0 * gp(u))
        _, gin = E.eventprop(net, rec, E.Loss("sum_t", neurons=(0,)))
        self.assertAlmostEqual(gin[0][0] / want, 1.0, places=11)
        self.assertAlmostEqual(gin[0][1] / want, 1.0, places=11)

    def test_two_spikes_of_one_neuron(self):
        """L = t2, the second spike: an input w at 2 ms fires the neuron; after the reset a second input w_b at
        20 ms fires it again. t2 depends on w through the state at 20 ms, which the reset shapes."""
        w, wb, ta, tb = 9.0, 6.0, 2.0, 20.0
        net = E.Net([[0.0]], [[w, wb]], [(ta, 0), (tb, 1)])
        rec = E.simulate(net)
        self.assertEqual(len(rec["spikes"]), 2)

        def t2_parts(w):
            u1 = crossing_after_kick(w)
            t1 = ta + u1
            Ir = w * math.exp(-BE * u1)
            Vb = K * Ir * g(tb - t1)
            Ip = w * math.exp(-BE * (tb - ta)) + wb
            A, B = Vb + K * Ip, -K * Ip
            s_peak = math.log(-BE * B / (AL * A)) / (BE - AL)
            s2 = root(lambda s: A * math.exp(-AL * s) + B * math.exp(-BE * s) - TH, 0.0, s_peak)
            return u1, t1, A, B, s2
        u1, t1, A, B, s2 = t2_parts(w)
        self.assertAlmostEqual(rec["spikes"][1][0], tb + s2, places=11)
        du1 = -g(u1) / (w * gp(u1))
        dVb = K * (math.exp(-BE * u1) * g(tb - t1) - w * BE * math.exp(-BE * u1) * du1 * g(tb - t1)
                   - w * math.exp(-BE * u1) * gp(tb - t1) * du1)
        dIp = math.exp(-BE * (tb - ta))
        dA, dB = dVb + K * dIp, -K * dIp
        Fw = dA * math.exp(-AL * s2) + dB * math.exp(-BE * s2)
        Fs = -AL * A * math.exp(-AL * s2) - BE * B * math.exp(-BE * s2)
        want_w = -Fw / Fs
        want_wb = -(K * math.exp(-AL * s2) - K * math.exp(-BE * s2)) / Fs
        loss = E.Loss("sum_t", neurons=(0,))  # L = t1 + t2; t1 depends on w alone
        _, gin = E.eventprop(net, rec, E.Loss("sum_t", neurons=()))
        self.assertEqual(gin, [[0.0, 0.0]])
        _, gin = E.eventprop(net, rec, loss)
        self.assertAlmostEqual(gin[0][0] / (du1 + want_w), 1.0, places=9)
        self.assertAlmostEqual(gin[0][1] / want_wb, 1.0, places=9)
        _, bad = E.eventprop(net, rec, loss, variant="no_theta")
        self.assertGreater(abs(bad[0][0] / (du1 + want_w) - 1.0), 1e-3)

    def test_chain_of_two(self):
        wa, w = 9.0, 7.5
        net = E.Net([[0.0, 0.0], [w, 0.0]], [[wa], [0.0]], [(2.0, 0)])
        rec = E.simulate(net)
        self.assertEqual([n for _, n, _ in rec["spikes"]], [0, 1])
        u0, u1 = crossing_after_kick(wa), crossing_after_kick(w)
        dt0_dwa = -g(u0) / (wa * gp(u0))
        dt1_dw = -g(u1) / (w * gp(u1))
        gW, gin = E.eventprop(net, rec, E.Loss("sum_t", neurons=(1,)))
        self.assertAlmostEqual(gW[1][0] / dt1_dw, 1.0, places=11)
        self.assertAlmostEqual(gin[0][0] / dt0_dwa, 1.0, places=11)
        gW, gin = E.eventprop(net, rec, E.Loss("sum_t", neurons=(0, 1)))
        self.assertAlmostEqual(gin[0][0] / (2 * dt0_dwa), 1.0, places=11)
        gW, gin = E.eventprop(net, rec, E.Loss("sum_t", neurons=(1,)), variant="transposed")
        self.assertEqual(gin[0][0], 0.0)

    def test_voltage_loss_one_neuron(self):
        """L = (c/2) integral of V^2 with one spike: the spike time moves the reset, so l_V^- - l_V^+ enters."""
        w, ta, c = 9.0, 5.0, 0.3
        net = E.Net([[0.0]], [[w]], [(ta, 0)])
        rec = E.simulate(net)
        self.assertEqual(len(rec["spikes"]), 1)
        T = E.T_END
        us = crossing_after_kick(w)
        ts = ta + us
        Is = w * math.exp(-BE * us)
        L = 0.5 * c * (K * K * w * w * G2(us) + K * K * Is * Is * G2(T - ts))
        loss = E.Loss("v2", c=[c])
        self.assertAlmostEqual(loss.value(rec) / L, 1.0, places=12)
        dus = -g(us) / (w * gp(us))
        dIs = math.exp(-BE * us) - w * BE * math.exp(-BE * us) * dus
        want = 0.5 * c * (2 * K * K * w * G2(us) + TH * TH * dus + 2 * K * K * Is * dIs * G2(T - ts)
                          - K * K * Is * Is * g(T - ts) ** 2 * dus)
        _, gin = E.eventprop(net, rec, loss)
        self.assertAlmostEqual(gin[0][0] / want, 1.0, places=10)
        for variant in ("no_lv_jump", "no_theta"):
            _, bad = E.eventprop(net, rec, loss, variant=variant)
            self.assertGreater(abs(bad[0][0] / want - 1.0), 1e-3, variant)

    def test_readout_fixed_time_and_maximum(self):
        net = E.Net([[0.0]], [[0.7, 0.5]], [(10.0, 0), (14.0, 1)], firing=[False])
        obs = ((30.0, 0, 2.0), (45.0, 0, -1.0))
        rec = E.simulate(net, observe=obs)
        _, gin = E.eventprop(net, rec, E.Loss("observe", observe=obs))
        self.assertAlmostEqual(gin[0][0], K * (2 * g(20.0) - g(35.0)), places=13)
        self.assertAlmostEqual(gin[0][1], K * (2 * g(16.0) - g(31.0)), places=13)
        rec = E.simulate(net, track_readout=0)
        tm = root(lambda t: -(0.7 * gp(t - 10.0) + 0.5 * gp(t - 14.0)), 14.0, 40.0)
        self.assertAlmostEqual(rec["rmax"][1], tm, places=9)
        _, gin = E.eventprop(net, rec, E.Loss("max", readout=0))
        self.assertAlmostEqual(gin[0][0], K * g(tm - 10.0), places=12)
        self.assertAlmostEqual(gin[0][1], K * g(tm - 14.0), places=12)

    def test_unknown_variant_refused(self):
        net = E.Net([[0.0]], [[9.0]], [(5.0, 0)])
        with self.assertRaises(E.Refused):
            E.eventprop(net, E.simulate(net), E.Loss("sum_t", neurons=(0,)), variant="other")


class Differences(unittest.TestCase):
    def test_stencil_exact_on_quartics(self):
        f = lambda x: 3 * x ** 4 - 2 * x ** 3 + x - 7
        self.assertAlmostEqual(E.stencil(f, 0.6, 0.1), 12 * 0.6 ** 3 - 6 * 0.6 ** 2 + 1, places=12)

    def test_fd_on_one_neuron(self):
        w = 9.0
        net = E.Net([[0.0]], [[w]], [(5.0, 0)])
        rec = E.simulate(net)
        fd, changed = E.fd_all(net, E.Loss("sum_t", neurons=(0,)), [("in", 0, 0)], rec)
        u = crossing_after_kick(w)
        self.assertEqual(changed, 0)
        self.assertAlmostEqual(fd[0] / (-g(u) / (w * gp(u))), 1.0, places=7)
        self.assertEqual(net.W_in[0][0], w)

    def test_deviations_floor(self):
        devs, G = E.deviations([1.0, 0.0, 2e-9], [1.0 + 1e-6, 0.0, 0.0])
        self.assertEqual(G, 1.0 + 1e-6)
        self.assertAlmostEqual(devs[0], 1e-6 / (1.0 + 1e-6), places=15)
        self.assertEqual(devs[1], 0.0)
        self.assertAlmostEqual(devs[2], 2e-9 / (E.FLOOR * G), places=15)


class Draws(unittest.TestCase):
    def test_reproducible_and_shared(self):
        a = E.build(SEED, "B1", 0, 0)[0]
        b = E.build(SEED, "B2", 0, 0)[0]
        self.assertEqual((a.W, a.W_in, a.inputs), (b.W, b.W_in, b.inputs))
        c = E.build(SEED, "B1", 0, 1)[0]
        self.assertNotEqual(a.W, c.W)
        d = E.build("5b" * 32, "B1", 0, 0)[0]
        self.assertNotEqual(a.W, d.W)
        x, y = E.build(SEED, "C1", 2, 3)[0], E.build(SEED, "C2", 2, 3)[0]
        self.assertEqual((x.W, x.W_in, x.inputs), (y.W, y.W_in, y.inputs))

    def test_shapes(self):
        net, loss, weights, observe, track, need, readout = E.build(SEED, "A", 0, 0)
        self.assertEqual((net.n, len(weights), loss.kind, need), (2, 101, "sum_t", {1}))
        self.assertTrue(all(0 <= x <= 0.04 for x in net.W_in[0]) and 3.0 <= net.W[1][0] <= 6.0)
        net, loss, weights, observe, track, need, readout = E.build(SEED, "B2", 1, 0)
        self.assertEqual((net.n, len(weights), loss.kind), (6, 210, "v2"))
        net, loss, weights, observe, track, need, readout = E.build(SEED, "C2", 1, 0)
        self.assertEqual((net.n, len(weights), loss.kind, track, readout, net.firing[5]), (6, 105, "max", 5, True, False))

    def test_poisson_rate(self):
        rng = E.rng_for(SEED, "|test/poisson")
        x = E.poisson(rng, 200, 100.0, 100.0)
        self.assertLess(abs(len(x) - 2000) / 2000, 0.1)
        self.assertEqual(x, sorted(x))
        self.assertTrue(all(0 < t < 100.0 for t, _ in x))


class WholeRun(unittest.TestCase):
    def test_plumbing_without_scenarios(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, detail = E.run(SEED, results=tmp, draws=E.DRAWS, scenarios=())
            on_disk = json.load(open(os.path.join(tmp, "outputs.json")))
        self.assertEqual(sorted(out), sorted(E.OUTPUTS))
        self.assertEqual(on_disk, out)
        self.assertEqual((out["test_passed"], out["conditions_total"], out["faults_total"]), (0, 0, 0))
        self.assertEqual(out["controls_passed"], out["controls_total"])
        self.assertTrue(all(out[f"{s}_summary"] == "not run" for s in E.SCENARIOS))

    def test_refusals(self):
        with self.assertRaises(E.Refused):
            E.run("xyz", scenarios=())
        with self.assertRaises(E.Refused):
            E.run(SEED, scenarios=("D",))
        with self.assertRaises(E.Refused):
            E.run(SEED, draws=0, scenarios=("A",))


class Registered(unittest.TestCase):
    def test_constants(self):
        self.assertLessEqual(len(E.TEST), 600)
        self.assertEqual((E.TAU_M, E.TAU_S, E.THETA, E.T_END), (20.0, 5.0, 1.0, 100.0))
        self.assertEqual((E.H_FD, E.TOL, E.FLOOR, E.DRAWS, E.MAX_ATTEMPTS), (1e-5, 1e-5, 1e-3, 3, 50))
        self.assertEqual(E.SCENARIOS, ("A", "B1", "B2", "C1", "C2"))
        self.assertEqual(set(E.FAULTS), {"no_theta", "transposed", "no_lv_jump"})
        self.assertEqual(len(set(E.OUTPUTS)), len(E.OUTPUTS))
        self.assertLessEqual(len(E.OUTPUTS), 64)

    def test_controls(self):
        c = E.controls_known(SEED)
        self.assertEqual(len(c), 6)
        self.assertTrue(all(c.values()), c)


if __name__ == "__main__":
    unittest.main()
