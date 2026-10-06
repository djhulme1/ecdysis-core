"""Unit tests for snn_surrogate.py.

Run inside the image:  python -m unittest -v test_snn_surrogate
They use fixed test seeds, not ECDYSIS_SEED.
"""
import hashlib
import math
import unittest

import torch

import snn_surrogate as m

torch.set_num_threads(1)
F64 = torch.float64
MASTER_A = bytes(range(32))
MASTER_B = bytes(range(1, 33))


def small_spec(**kw):
    spec = dict(m.SPEC)
    spec.update(kw)
    return spec


class SurrogateShapes(unittest.TestCase):
    xs = torch.linspace(-3.0, 3.0, 601, dtype=F64)

    def test_peak_values(self):
        for beta in (0.5, 1.0, 10.0, 100.0):
            zero = torch.zeros(1, dtype=F64)
            self.assertAlmostEqual(float(m.surrogate(zero, "superspike", beta)), 1.0, places=12)
            self.assertAlmostEqual(float(m.surrogate(zero, "esser", beta)), 1.0, places=12)
            self.assertAlmostEqual(float(m.surrogate(zero, "sigmoid", beta)), 0.25, places=12)
            self.assertAlmostEqual(float(m.surrogate(zero, "asymptotic", beta)), beta, places=9)
            for shape in ("superspike", "sigmoid", "esser"):
                h = m.surrogate(self.xs, shape, beta)
                self.assertLessEqual(float(h.max()), float(m.surrogate(zero, shape, beta)) + 1e-15)
                # s(1 - s) is computed as written in the paper (and as stork's
                # sig * (1 - sig)), so for large positive beta*x it rounds to 0 where
                # the mirror value is a tiny positive number: symmetric up to 1e-15.
                self.assertTrue(torch.allclose(h, h.flip(0), atol=1e-15, rtol=1e-12), shape)
                self.assertGreaterEqual(float(h.min()), 0.0)

    def test_beta_is_a_pure_steepness_parameter(self):
        # h_beta(x) = h_1(beta x): beta rescales the width, never the peak.
        for shape in ("superspike", "sigmoid", "esser"):
            for beta in (0.1, 2.0, 37.0, 1000.0):
                a = m.surrogate(self.xs, shape, beta)
                b = m.surrogate(self.xs * beta, shape, 1.0)
                self.assertTrue(torch.allclose(a, b, rtol=1e-12, atol=1e-300), (shape, beta))

    def test_steeper_with_larger_beta(self):
        x = torch.tensor([-0.9, -0.3, 0.05, 0.4], dtype=F64)
        for shape in ("superspike", "sigmoid"):
            lo = m.surrogate(x, shape, 2.0)
            hi = m.surrogate(x, shape, 20.0)
            self.assertTrue(bool((hi < lo).all()), shape)
        lo = m.surrogate(x, "esser", 1.0)
        hi = m.surrogate(x, "esser", 2.0)
        self.assertTrue(bool((hi <= lo).all()))

    def test_half_widths(self):
        for beta in (0.5, 10.0, 300.0):
            x = torch.tensor([1.0 / beta], dtype=F64)
            self.assertAlmostEqual(float(m.surrogate(x, "superspike", beta)), 0.25, places=12)
            self.assertAlmostEqual(float(m.surrogate(x / 2, "esser", beta)), 0.5, places=12)
            self.assertAlmostEqual(float(m.surrogate(x, "esser", beta)), 0.0, places=12)
            xs = torch.tensor([math.log(3 + 2 * math.sqrt(2)) / beta], dtype=F64)
            self.assertAlmostEqual(float(m.surrogate(xs, "sigmoid", beta)), 0.125, places=12)

    def test_esser_support(self):
        beta = 4.0
        h = m.surrogate(self.xs, "esser", beta)
        inside = self.xs.abs() < 1.0 / beta
        self.assertTrue(bool((h[inside] > 0).all()))
        self.assertTrue(bool((h[~inside] == 0).all()))

    def test_beta_zero_and_zero_shape(self):
        self.assertTrue(bool((m.surrogate(self.xs, "superspike", 0.0) == 1.0).all()))
        self.assertTrue(bool((m.surrogate(self.xs, "esser", 0.0) == 1.0).all()))
        self.assertTrue(bool((m.surrogate(self.xs, "sigmoid", 0.0) == 0.25).all()))
        self.assertTrue(bool((m.surrogate(self.xs, "zero", 3.0) == 0.0).all()))

    def test_in_place_version_agrees(self):
        u = torch.linspace(-2.0, 4.0, 1001, dtype=torch.float32).reshape(7, 143)
        out = torch.empty_like(u)
        for shape in m.SHAPES_ALL:
            for beta in (0.0, 0.3, 10.0, 100.0, 1000.0):
                ref = m.surrogate(u - 1.0, shape, beta)
                got = m.surrogate_of_u(u, shape, beta, out=out)
                self.assertTrue(torch.allclose(got, ref, rtol=1e-6, atol=0), (shape, beta))

    def test_primitive_derivative_is_the_surrogate(self):
        x = torch.linspace(-2.0, 2.0, 81, dtype=F64) + 0.0123
        eps = 1e-6
        for shape in ("superspike", "sigmoid", "esser", "asymptotic"):
            for beta in (0.7, 5.0):
                fd = (m.surrogate_primitive(x + eps, shape, beta)
                      - m.surrogate_primitive(x - eps, shape, beta)) / (2 * eps)
                self.assertTrue(torch.allclose(fd, m.surrogate(x, shape, beta), atol=1e-6),
                                (shape, beta))

    def test_heaviside_convention(self):
        x = torch.tensor([-1.0, -0.0, 0.0, 1e-7, 2.0])
        self.assertEqual(m.heaviside_(x.clone()).tolist(), [0.0, 0.0, 0.0, 1.0, 1.0])


class ForwardPass(unittest.TestCase):
    def reference_trace(self, net, t_in, w1, w2):
        """Eq. 4.1 and Sec. 4.2.2 written out with Python floats (float64)."""
        T = net.T
        nin, H = len(w1), len(w1[0])
        K = len(w2[0])
        U = [0.0] * H
        I = [0.0] * H
        Uo = [0.0] * K
        Io = [0.0] * K
        spikes, us, uouts = [], [], []
        for n in range(T):
            S = [1.0 if U[i] - 1.0 > 0 else 0.0 for i in range(H)]
            spikes.append(S)
            us.append(list(U))
            inp = [sum(w1[u][i] for u in range(nin) if t_in[u] == n) for i in range(H)]
            U = [(net.b_mem * U[i] + (1 - net.b_mem) * I[i]) * (1 - S[i]) for i in range(H)]
            I = [net.b_syn * I[i] + inp[i] for i in range(H)]
            Uo_new = [net.b_out * Uo[k] + (1 - net.b_out) * Io[k] for k in range(K)]
            Io = [net.b_syn * Io[k] + sum(w2[i][k] * S[i] for i in range(H)) for k in range(K)]
            Uo = Uo_new
            uouts.append(list(Uo))
        return spikes, us, uouts

    def test_hand_made_input(self):
        net = m.Network(small_spec(nb_steps=30), dtype=F64)
        t_in = torch.tensor([[0, 3]])
        w1 = torch.tensor([[10.0, 0.5], [0.0, 0.5]], dtype=F64)
        w2 = torch.tensor([[1.0, -1.0], [0.5, 2.0]], dtype=F64)
        S, U_v, _, _, U_out = net.forward(t_in, w1, w2)
        # Worked by hand from eq. 4.1 with b_mem = e^-0.1, b_syn = e^-0.2:
        # U[2] = 0.9516 (no spike), U[3] = 1.640 -> spike, U[4] = 0, U[5] = 0.522,
        # U[6] = 0.900, U[7] = 1.165 -> spike; afterwards it stays below threshold.
        steps0 = [n for n in range(net.T) if S[n, 0, 0] == 1.0]
        self.assertEqual(steps0, [3, 7])
        self.assertEqual(float(S[:, 0, 1].sum()), 0.0)
        self.assertAlmostEqual(float(U_v[2][0, 0]), (1 - math.exp(-0.1)) * 10.0, places=12)
        self.assertEqual(float(U_v[4][0, 0]), 0.0)   # multiplicative reset
        self.assertEqual(float(U_v[8][0, 0]), 0.0)
        ref_s, ref_u, ref_uo = self.reference_trace(net, [0, 3], w1.tolist(), w2.tolist())
        self.assertEqual(S[:, 0, :].tolist(), ref_s)
        got_u = torch.stack([U_v[n][0] for n in range(net.T)])
        self.assertTrue(torch.allclose(got_u, torch.tensor(ref_u, dtype=F64), atol=1e-12))
        self.assertTrue(torch.allclose(U_out[:, 0, :], torch.tensor(ref_uo, dtype=F64), atol=1e-12))
        # The 1-step synaptic delay: the input at n=0 first moves U at n=2.
        self.assertEqual(float(U_v[1][0, 0]), 0.0)

    def test_random_input_matches_reference(self):
        net = m.Network(small_spec(nb_steps=40), dtype=F64)
        gen = torch.Generator().manual_seed(5)
        t_in = torch.randint(0, 25, (1, 6), generator=gen)
        w1 = torch.rand(6, 5, generator=gen, dtype=F64) * 6 - 1
        w2 = torch.rand(5, 3, generator=gen, dtype=F64) * 2 - 1
        S, U_v, _, _, U_out = net.forward(t_in, w1, w2)
        self.assertGreater(float(S.sum()), 0.0)
        ref_s, ref_u, ref_uo = self.reference_trace(net, t_in[0].tolist(), w1.tolist(), w2.tolist())
        self.assertEqual(S[:, 0, :].tolist(), ref_s)
        self.assertTrue(torch.allclose(U_out[:, 0, :], torch.tensor(ref_uo, dtype=F64), atol=1e-12))

    def test_readout_kernel_is_the_recursion(self):
        T = 50
        K = m.readout_kernel(T, math.exp(-0.2), math.exp(-0.05))
        h = torch.randn(T, 3, dtype=F64, generator=torch.Generator().manual_seed(1))
        Uo = torch.zeros(3, dtype=F64)
        Io = torch.zeros(3, dtype=F64)
        rec = []
        for n in range(T):
            Uo, Io = math.exp(-0.05) * Uo + (1 - math.exp(-0.05)) * Io, math.exp(-0.2) * Io + h[n]
            rec.append(Uo)
        self.assertTrue(torch.allclose(K @ h, torch.stack(rec), atol=1e-12))

    def test_hidden_layer_silent_at_paper_initialisation(self):
        spec = dict(m.SPEC)
        data = m.make_dataset(MASTER_A, 0, spec)
        w1, w2 = m.init_weights(MASTER_A, 0, 20, 100, 10)
        net = m.Network(spec)
        S, U_v, _, _, _ = net.forward(data["train"][0][:500], w1, w2)
        self.assertEqual(float(S.sum()), 0.0)
        self.assertLess(float(torch.stack(U_v).max()), 1.0)


class Gradients(unittest.TestCase):
    def setUp(self):
        self.spec = small_spec(nb_steps=24)
        self.net = m.Network(self.spec, dtype=F64)
        gen = torch.Generator().manual_seed(11)
        self.t_in = torch.randint(0, 12, (3, 4), generator=gen)
        self.y = torch.tensor([0, 2, 1])
        self.w1 = torch.rand(4, 5, generator=gen, dtype=F64) * 9.0 - 2.0
        # mostly positive, so that every readout rises above its initial 0 and the
        # max over time does not sit on the constant first step (zero gradient)
        self.w2 = torch.rand(5, 3, generator=gen, dtype=F64) * 2.0 - 0.5
        self.v = torch.rand(5, 5, generator=gen, dtype=F64) * 1.2 - 0.6

    def loss_only(self, params, shape, beta, **kw):
        w1, w2, v = params
        out = self.net.loss_and_grad(self.t_in, self.y, w1, w2, shape, beta, 100.0, 1e-3,
                                     w_rec=v, **kw)
        return float(out[0])

    def finite_differences(self, shape, beta, recurrent=False, eps=1e-6, **kw):
        """Central differences of the loss for W1, W2 (and V if recurrent)."""
        params = [self.w1, self.w2, self.v if recurrent else None]
        grads = []
        for k in range(3 if recurrent else 2):
            w = params[k]
            gw = torch.zeros_like(w)
            for idx in range(w.numel()):
                plus, minus = list(params), list(params)
                wp = w.clone().view(-1)
                wm = w.clone().view(-1)
                wp[idx] += eps
                wm[idx] -= eps
                plus[k], minus[k] = wp.view_as(w), wm.view_as(w)
                gw.view(-1)[idx] = (self.loss_only(plus, shape, beta, **kw)
                                    - self.loss_only(minus, shape, beta, **kw)) / (2 * eps)
            grads.append(gw)
        return grads

    def assert_close(self, a, b, tol, msg):
        scale = max(float(b.abs().max()), 1e-12)
        self.assertLess(float((a - b).abs().max()) / scale, tol, msg)

    def test_surrogate_gradient_matches_finite_differences(self):
        """Spikes replaced by the smooth primitive H of h (H' = h), differentiable
        reset: then the surrogate-gradient code computes an exact gradient, which
        must equal central finite differences.  The asymptotic case is the Fig. 5
        "aDR" setting."""
        for shape, beta in (("superspike", 5.0), ("sigmoid", 4.0), ("esser", 0.8),
                            ("asymptotic", 3.0), ("asymptotic", 12.0)):
            _, ce, _, g1, g2, _ = self.net.loss_and_grad(self.t_in, self.y, self.w1, self.w2,
                                                         shape, beta, 100.0, 1e-3, smooth=True,
                                                         diff_reset=True)
            f1, f2 = self.finite_differences(shape, beta, smooth=True, diff_reset=True)
            if shape != "asymptotic":   # its readouts stay below 0: regulariser path only
                self.assertNotAlmostEqual(float(ce), math.log(3), places=6)  # readout path live
            self.assertGreater(float(g1.abs().max()), 0.0)
            self.assert_close(g1, f1, 1e-5, "W1 %s %g" % (shape, beta))
            self.assert_close(g2, f2, 1e-5, "W2 %s %g" % (shape, beta))

    def test_recurrent_gradient_matches_finite_differences(self):
        """Recurrent hidden layer with gradients through V (Fig. 5e "Prop"), with
        and without a differentiable reset, smooth stand-in for the spike: the
        hand-written BPTT for W1, W2 and V equals central finite differences."""
        for shape, beta, dr in (("superspike", 5.0, False), ("asymptotic", 3.0, False),
                                ("asymptotic", 3.0, True), ("sigmoid", 4.0, True)):
            out = self.net.loss_and_grad(self.t_in, self.y, self.w1, self.w2, shape, beta,
                                         100.0, 1e-3, smooth=True, diff_reset=dr,
                                         w_rec=self.v, rec_grad=True)
            kw = {"diff_reset": True}
            if not dr:   # a detached reset is a reset signal held fixed (see the test below)
                S = self.net.forward(self.t_in, self.w1, self.w2, shape, beta, smooth=True,
                                     w_rec=self.v)[0]
                kw = {"frozen_reset": S.clone()}
            f1, f2, fv = self.finite_differences(shape, beta, recurrent=True, smooth=True,
                                                 rec_grad=True, **kw)
            self.assertGreater(float(out[5].abs().max()), 0.0)
            for got, ref, name in ((out[3], f1, "W1"), (out[4], f2, "W2"), (out[5], fv, "V")):
                self.assert_close(got, ref, 1e-5, "%s %s %g dr=%s" % (name, shape, beta, dr))

    def test_detached_reset_matches_finite_differences_with_frozen_reset(self):
        """Detaching the reset = treating the reset signal as a constant input."""
        for shape, beta in (("superspike", 5.0), ("sigmoid", 4.0)):
            S, _, _, _, _ = self.net.forward(self.t_in, self.w1, self.w2, shape, beta, smooth=True)
            frozen = S.clone()
            _, _, _, g1, g2, _ = self.net.loss_and_grad(self.t_in, self.y, self.w1, self.w2,
                                                        shape, beta, 100.0, 1e-3, smooth=True)
            f1, f2 = self.finite_differences(shape, beta, smooth=True, frozen_reset=frozen)
            self.assert_close(g1, f1, 1e-5, "W1 " + shape)
            self.assert_close(g2, f2, 1e-5, "W2 " + shape)

    def test_manual_backward_equals_autograd_with_real_spikes(self):
        """Heaviside forward, surrogate backward: the hand-written BPTT equals
        PyTorch autograd on an independent implementation, for the Fig. 3 setting
        (detached reset), the Fig. 5 settings (differentiable reset; recurrent
        with and without gradients through V) and the controls."""
        spec = dict(m.SPEC)
        net = m.Network(spec, dtype=F64)
        data = m.make_dataset(MASTER_A, 0, spec)
        w1, w2 = m.init_weights(MASTER_A, 0, 20, 100, 10)
        v = m.init_recurrent(MASTER_A, 0, 100).double()
        w1 = w1.double() * 8.0
        w2 = w2.double()
        x, y = data["train"][0][:40], data["train"][1][:40]
        cases = [(s, b, {}) for s, b in (("superspike", 10.0), ("sigmoid", 5.0), ("esser", 1.0),
                                         ("zero", 0.0), ("superspike", 0.0))]
        cases += [("asymptotic", 10.0, {"diff_reset": True}),
                  ("superspike", 10.0, {"diff_reset": True}),
                  ("asymptotic", 10.0, {"w_rec": v, "rec_grad": True}),
                  ("asymptotic", 10.0, {"w_rec": v, "rec_grad": False}),
                  ("superspike", 10.0, {"w_rec": v, "rec_grad": True, "diff_reset": True})]
        for shape, beta, kw in cases:
            loss, _, _, g1, g2, gv = net.loss_and_grad(x, y, w1, w2, shape, beta, 100.0, 1e-3, **kw)
            a1 = w1.clone().requires_grad_(True)
            a2 = w2.clone().requires_grad_(True)
            akw = dict(kw)
            if "w_rec" in kw:
                akw["w_rec"] = av = kw["w_rec"].clone().requires_grad_(True)
            la, S = m.loss_autograd(net, x, y, a1, a2, shape, beta, 100.0, 1e-3, **akw)
            la.backward()
            msg = "%s %g %s" % (shape, beta, sorted(k for k in kw))
            self.assertGreater(float(S.detach().sum()), 0.0)
            self.assertAlmostEqual(float(loss), float(la.detach()), places=12, msg=msg)
            pairs = [(g1, a1.grad), (g2, a2.grad)] + ([(gv, av.grad)] if "w_rec" in kw else [])
            for got, ref in pairs:
                self.assertLess(float((got - ref).abs().max()),
                                1e-12 + 1e-9 * float(ref.abs().max()), msg)
            if shape == "zero":
                self.assertEqual(float(g1.abs().max()), 0.0)

    def test_magnitude_scales_gradients_only_through_recurrence(self):
        """Asymptotic = beta x normalised SuperSpike.  With the reset detached and no
        recurrence each gradient path to W1 holds one surrogate factor, so the W1
        gradient scales exactly by beta (which Adam's normalisation absorbs); with a
        differentiable reset the paths hold several factors and the ratio departs from
        beta.  This is the mechanism behind Fig. 5."""
        spec = dict(m.SPEC)
        net = m.Network(spec, dtype=F64)
        data = m.make_dataset(MASTER_A, 0, spec)
        w1, w2 = m.init_weights(MASTER_A, 0, 20, 100, 10)
        w1, w2 = w1.double() * 8.0, w2.double()
        x, y = data["train"][0][:40], data["train"][1][:40]
        beta = 10.0
        g_s = net.loss_and_grad(x, y, w1, w2, "superspike", beta, 100.0, 1e-3)[3]
        g_a = net.loss_and_grad(x, y, w1, w2, "asymptotic", beta, 100.0, 1e-3)[3]
        self.assertTrue(torch.allclose(g_a, beta * g_s, rtol=1e-10, atol=0))
        g_s = net.loss_and_grad(x, y, w1, w2, "superspike", beta, 100.0, 1e-3, diff_reset=True)[3]
        g_a = net.loss_and_grad(x, y, w1, w2, "asymptotic", beta, 100.0, 1e-3, diff_reset=True)[3]
        self.assertFalse(torch.allclose(g_a, beta * g_s, rtol=1e-3, atol=0))


class RandmanData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = dict(m.SPEC)
        cls.a1 = m.make_dataset(MASTER_A, 0, cls.spec)
        cls.a2 = m.make_dataset(MASTER_A, 0, cls.spec)

    def test_same_seed_identical(self):
        for name in ("train", "valid", "test"):
            self.assertTrue(torch.equal(self.a1[name][0], self.a2[name][0]))
            self.assertTrue(torch.equal(self.a1[name][1], self.a2[name][1]))

    def test_other_seed_or_replicate_differs(self):
        b = m.make_dataset(MASTER_B, 0, self.spec)
        c = m.make_dataset(MASTER_A, 1, self.spec)
        self.assertFalse(torch.equal(self.a1["train"][0], b["train"][0]))
        self.assertFalse(torch.equal(self.a1["train"][0], c["train"][0]))

    def test_one_spike_per_input_in_first_50_ms(self):
        x, y = self.a1["train"]
        self.assertEqual(tuple(x.shape), (8000, 20))
        self.assertEqual(int(x.min()), 0)
        self.assertEqual(int(x.max()), 49)
        self.assertEqual(self.a1["valid"][0].shape[0], 1000)
        self.assertEqual(self.a1["test"][0].shape[0], 1000)
        for split, n in (("train", 800), ("valid", 100), ("test", 100)):
            counts = torch.bincount(self.a1[split][1], minlength=10)
            self.assertEqual(counts.tolist(), [n] * 10)

    def test_per_class_standardisation(self):
        for spectrum in ("paper", "code"):
            gp = m.make_generator(MASTER_A, "p")
            gc = m.make_generator(MASTER_A, "c")
            t = m.randman_spike_times(gp, gc, 20, 1, 1.0, 1000, 100, 0.5, spectrum=spectrum)
            self.assertEqual(t.min(0).values.tolist(), [0] * 20)
            self.assertEqual(t.max(0).values.tolist(), [49] * 20)

    def test_embedding_matches_the_formulas(self):
        gen = torch.Generator().manual_seed(3)
        theta = torch.rand(2, 2, 3, 7, generator=gen, dtype=F64)
        x = torch.rand(4, 2, generator=gen, dtype=F64)
        alpha = 1.5
        paper = m.randman_embedding(theta, x, alpha, "paper")
        code = m.randman_embedding(theta, x, alpha, "code")
        for n in range(4):
            for i in range(2):
                # paper Sec. 4.1.1: prod_j sum_{k=1}^{7} k^-alpha A sin(2 pi (k x_j B + C))
                p = 1.0
                c = 1.0
                for j in range(2):
                    A, B, C = theta[i, j].tolist()
                    p *= sum(k ** -alpha * A[k - 1] * math.sin(2 * math.pi * (k * x[n, j].item() * B[k - 1] + C[k - 1]))
                             for k in range(1, 8))
                    # torch_randman.py: sum_{i=0}^{6} A_i s_i sin(2 pi (i x B_i + C_i)), s_i = 1/((i+1)^a + 1)
                    c *= sum(A[q] / ((q + 1) ** alpha + 1) * math.sin(2 * math.pi * (q * x[n, j].item() * B[q] + C[q]))
                             for q in range(7))
                self.assertAlmostEqual(float(paper[n, i]), p, places=12)
                self.assertAlmostEqual(float(code[n, i]), c, places=12)

    def test_manifold_is_smooth_in_its_coordinate(self):
        # Two samples at nearby intrinsic coordinates fire at nearby times.
        gp = m.make_generator(MASTER_A, "p")
        t = m.randman_spike_times(gp, m.make_generator(MASTER_A, "c"), 20, 1, 1.0, 1000, 100, 0.5)
        # the same intrinsic coordinates as drawn inside randman_spike_times
        x = torch.rand(1000, 1, generator=m.make_generator(MASTER_A, "c"), dtype=F64)
        order = torch.argsort(x[:, 0])
        jumps = (t[order][1:] - t[order][:-1]).abs().float().mean()
        shuffled = (t[1:] - t[:-1]).abs().float().mean()
        self.assertLess(float(jumps), 0.25 * float(shuffled))


class Seeds(unittest.TestCase):
    def test_derivation(self):
        expect = int.from_bytes(hashlib.sha256(MASTER_A + b"|rep0/init").digest()[:8], "little")
        self.assertEqual(m.derived_seed(MASTER_A, "rep0/init"), expect)
        self.assertNotEqual(m.derived_seed(MASTER_A, "rep0/init"),
                            m.derived_seed(MASTER_A, "rep1/init"))
        g1 = m.make_generator(MASTER_A, "x")
        g2 = m.make_generator(MASTER_A, "x")
        self.assertTrue(torch.equal(torch.rand(5, generator=g1), torch.rand(5, generator=g2)))

    def test_init_is_paper_uniform(self):
        w1, w2 = m.init_weights(MASTER_A, 0, 20, 100, 10)
        self.assertLessEqual(float(w1.abs().max()), 1 / math.sqrt(20))
        self.assertLessEqual(float(w2.abs().max()), 1 / math.sqrt(100))
        self.assertGreater(float(w1.abs().max()), 0.95 / math.sqrt(20))


class Training(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = dict(m.SPEC)
        cls.full = m.make_dataset(MASTER_A, 0, cls.spec)
        cls.data = {"train": (cls.full["train"][0][::8], cls.full["train"][1][::8]),
                    "valid": cls.full["valid"], "test": cls.full["test"]}
        cls.w1, cls.w2 = m.init_weights(MASTER_A, 0, 20, 100, 10)
        cls.net = m.Network(cls.spec)

    def run_once(self, shape, beta, eta, epochs):
        return m.train_run(self.net, self.data, self.w1, self.w2, MASTER_A, 0, shape, beta, eta,
                           epochs, 250, 100.0, 1e-3)

    def test_two_runs_are_identical(self):
        a = self.run_once("superspike", 10.0, 0.05, 2)
        b = m.train_run(m.Network(self.spec), self.data, self.w1, self.w2, MASTER_A, 0,
                        "superspike", 10.0, 0.05, 2, 250, 100.0, 1e-3)
        self.assertEqual(a, b)

    def test_no_learning_stays_at_chance(self):
        r = self.run_once("superspike", 10.0, 0.0, 1)
        self.assertEqual(r["test_acc"], 0.1)
        self.assertEqual(r["hidden_spikes_per_test_input"], 0.0)

    def test_zero_surrogate_cannot_leave_the_silent_start(self):
        r = self.run_once("zero", 0.0, 0.05, 2)
        self.assertEqual(r["test_acc"], 0.1)

    def test_fig5_settings_run_and_are_deterministic(self):
        v = m.init_recurrent(MASTER_A, 0, 100)
        args = (self.data, self.w1, self.w2, MASTER_A, 0, "asymptotic", 10.0, 0.02, 1, 250,
                100.0, 1e-3)
        a = m.train_run(self.net, *args, w_rec_init=v, rec_grad=True)
        b = m.train_run(m.Network(self.spec), *args, w_rec_init=v, rec_grad=True)
        self.assertEqual(a, b)
        c = m.train_run(self.net, *args, diff_reset=True)
        self.assertTrue(c["finite"])
        w1, _ = m.init_weights(MASTER_A, 0, 20, 100, 10)
        self.assertTrue(torch.equal(w1, self.w1))       # V has its own stream

    def test_surrogate_learning_beats_chance(self):
        r = m.train_run(self.net, self.full, self.w1, self.w2, MASTER_A, 0, "superspike", 10.0,
                        0.05, 3, 250, 100.0, 1e-3)
        self.assertGreater(r["val_acc"], 0.15)
        self.assertGreater(r["hidden_spikes_per_test_input"], 0.0)


class Job(unittest.TestCase):
    def test_default_job(self):
        cfg = m.default_config()
        tasks = m.build_tasks(cfg)
        kinds = {}
        for t in tasks:
            kinds[t["kind"]] = kinds.get(t["kind"], 0) + 1
        self.assertEqual(kinds, {"grid": 3 * 12 * 3, "fig5_dr": 12 * 3, "fig5_rec": 12,
                                 "fig5_sdr": 3, "fig5_sprop": 1, "no_learning": 1,
                                 "true_gradient": 1, "constant": 3})
        self.assertEqual(len({m.task_key(t) for t in tasks}), len(tasks))
        self.assertEqual(cfg["fig5_betas"], cfg["betas"])          # cf. Figure 3
        for t in tasks:
            self.assertEqual(t["diff_reset"], t["kind"] in ("fig5_dr", "fig5_sdr"))
            self.assertEqual(t["recurrent"], t["kind"] in ("fig5_rec", "fig5_sprop"))
            self.assertEqual(t["epochs"], 100 if t["kind"].startswith("fig5") else 50)
            if t["kind"] == "fig5_dr" or t["kind"] == "fig5_rec":
                self.assertEqual(t["shape"], "asymptotic")
        self.assertEqual(m.build_tasks(cfg), tasks)                 # deterministic order

    def test_trial_job_is_small(self):
        self.assertLess(len(m.build_tasks(m.default_config(trial=True))), 40)


class Summary(unittest.TestCase):
    @staticmethod
    def record(results, kind, rep, shape, beta, eta, val, test):
        results[(kind, rep, shape, beta, eta)] = {
            "kind": kind, "rep": rep, "shape": shape, "beta": beta, "eta": eta,
            "val_acc": val, "test_acc": test}

    def test_fig3_definitions(self):
        cfg = {"spec": dict(m.SPEC), "seeds": 2, "betas": (1.0, 10.0), "etas": (0.01, 0.1),
               "shapes": ("superspike", "esser"), "default_shape": "superspike",
               "controls": False, "fig5": False}
        # (val, test) per (rep, shape, beta, eta)
        table = {
            (0, "superspike", 1.0): [(0.5, 0.52), (0.7, 0.68)],
            (0, "superspike", 10.0): [(0.9, 0.91), (0.8, 0.99)],
            (0, "esser", 1.0): [(0.95, 0.94), (0.95, 0.10)],
            (0, "esser", 10.0): [(0.1, 0.1), (0.1, 0.1)],
            (1, "superspike", 1.0): [(0.6, 0.62), (0.6, 0.60)],
            (1, "superspike", 10.0): [(0.9, 0.93), (0.95, 0.95)],
            (1, "esser", 1.0): [(0.9, 0.92), (0.8, 0.85)],
            (1, "esser", 10.0): [(0.1, 0.1), (0.1, 0.1)],
        }
        results = {}
        for (rep, shape, beta), pairs in table.items():
            for eta, (v, t) in zip(cfg["etas"], pairs):
                self.record(results, "grid", rep, shape, beta, eta, v, t)
        out, detail = m.summarise(cfg, results)
        # Selected by validation (ties -> smaller eta):
        # rep0: ss b1 -> .68, ss b10 -> .91, es b1 -> .94 (tie), es b10 -> .1
        # rep1: ss b1 -> .62 (tie), ss b10 -> .95, es b1 -> .92, es b10 -> .1
        # best: ss (.91 + .95)/2 = .93, es (.94 + .92)/2 = .93 -> shape spread 0
        # curves: ss [(.68+.62)/2, (.91+.95)/2] = [.65, .93] -> .28; es [.93, .1] -> .83
        self.assertAlmostEqual(out["shape_spread"], 0.0, places=4)
        self.assertAlmostEqual(out["slope_spread_default"], 0.28, places=4)
        self.assertAlmostEqual(detail["slope_spread"]["esser"], 0.83, places=4)
        self.assertEqual(out["test_passed"], 1)       # without Fig. 5: against the slope spread
        self.assertAlmostEqual(out["best_acc_superspike"], 0.93, places=4)
        self.assertEqual(out["acc_by_beta_superspike"], "1:0.650,10:0.930")
        self.assertNotIn("magnitude_scale_spread", out)
        self.assertLessEqual(len(out), 20)

    def test_fig5_definitions(self):
        cfg = {"spec": dict(m.SPEC), "seeds": 1, "betas": (1.0, 10.0), "etas": (0.02, 0.05),
               "shapes": ("superspike", "sigmoid", "esser"), "default_shape": "superspike",
               "controls": True, "fig5": True, "fig5_betas": (1.0, 10.0, 100.0),
               "fig5_etas": (0.02, 0.05), "fig5_rec_betas": (1.0, 100.0),
               "fig5_rec_etas": (0.02,), "fig5_control_beta": 10.0, "true_gradient_eta": 0.05}
        R = {}
        for shape, accs in (("superspike", (0.97, 0.99)), ("sigmoid", (0.96, 0.98)),
                            ("esser", (0.95, 0.10))):
            for beta, acc in zip(cfg["betas"], accs):
                self.record(R, "grid", 0, shape, beta, 0.02, acc - 0.01, acc - 0.02)
                self.record(R, "grid", 0, shape, beta, 0.05, acc, acc)
        # aDR: beta 1 -> .80 (eta .05 by validation), 10 -> .55, 100 -> .30: spread .50
        for beta, (a, b) in zip(cfg["fig5_betas"], ((0.70, 0.80), (0.55, 0.40), (0.20, 0.30))):
            self.record(R, "fig5_dr", 0, "asymptotic", beta, 0.02, a, a)
            self.record(R, "fig5_dr", 0, "asymptotic", beta, 0.05, b, b)
        self.record(R, "fig5_rec", 0, "asymptotic", 1.0, 0.02, 0.3, 0.35)
        self.record(R, "fig5_rec", 0, "asymptotic", 100.0, 0.02, 0.2, 0.15)
        self.record(R, "fig5_sdr", 0, "superspike", 10.0, 0.02, 0.97, 0.975)
        self.record(R, "fig5_sdr", 0, "superspike", 10.0, 0.05, 0.98, 0.985)
        self.record(R, "fig5_sprop", 0, "superspike", 10.0, 0.02, 0.95, 0.955)
        self.record(R, "no_learning", 0, "superspike", 10.0, 0.0, 0.1, 0.1)
        self.record(R, "true_gradient", 0, "zero", 0.0, 0.05, 0.1, 0.1)
        for eta in cfg["etas"]:
            self.record(R, "constant", 0, "superspike", 0.0, eta, 0.5, 0.55)
        out, _ = m.summarise(cfg, R)
        self.assertAlmostEqual(out["shape_spread"], 0.04, places=4)       # .99 - .95
        self.assertAlmostEqual(out["slope_spread_default"], 0.02, places=4)
        self.assertAlmostEqual(out["magnitude_scale_spread"], 0.5, places=4)
        self.assertAlmostEqual(out["magnitude_scale_spread_recurrent"], 0.2, places=4)
        self.assertEqual(out["test_passed"], 1)
        self.assertEqual(out["acc_by_beta_adr"], "1:0.800,10:0.550,100:0.300")
        self.assertEqual(out["acc_by_beta_aprop"], "1:0.350,100:0.150")
        self.assertEqual(out["normalised_scale_controls"], "sDR=0.985,sProp=0.955 (beta=10)")
        self.assertEqual(out["true_gradient_accuracy"], 0.1)
        self.assertEqual(out["constant_surrogate_accuracy"], 0.55)
        self.assertIn("aDR", out["magnitude_setting"])
        self.assertLessEqual(len(out), 20)
        self.assertTrue(all(isinstance(v, (int, float, str)) for v in out.values()))
        self.assertTrue(all(len(v) <= 200 for v in out.values() if isinstance(v, str)))


if __name__ == "__main__":
    unittest.main()
