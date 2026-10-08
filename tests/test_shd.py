"""The Heidelberg check on made-up data: the seed's streams; the digits checked and anything malformed refused; the
counts and the 10 ms by 64-group bins, float16 times at the bin edges included; the validation split; the CNN's
pieces against direct computation and their gradients against finite differences (convolution, batch normalisation,
max-pooling, the softmax cross-entropy and the whole network, in float64); Keras 2.3's Adamax by hand; the shapes of
rule 6's network; rule 4's list; the verdict's two thresholds, exactly; with the released files (at inputs/ or in
SHD_INPUTS), also the digits, the labels and the spikes left out.

Run with: python3 -m unittest discover -s tests
"""

import gzip
import importlib.util
import io
import os
import tempfile
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("snn_shd", os.path.join(HERE, "..", "snn", "shd.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "0" * 63 + "1"
F64 = np.float64


def numgrad(f, x, idxs, eps=1e-6):
    out = []
    for i in idxs:
        old = x[i]
        x[i] = old + eps
        fp = f()
        x[i] = old - eps
        fm = f()
        x[i] = old
        out.append((fp - fm) / (2 * eps))
    return np.array(out)


def some(shape, rng, k=6):
    return [tuple(int(rng.integers(0, n)) for n in shape) for _ in range(k)]


class Seed(unittest.TestCase):
    def test_streams_are_fixed_by_seed_and_label(self):
        a = M.stream(SEED, "x").random(3)
        self.assertTrue(np.array_equal(a, M.stream(SEED, "x").random(3)))
        self.assertFalse(np.array_equal(a, M.stream(SEED, "y").random(3)))
        self.assertFalse(np.array_equal(a, M.stream("0" * 64, "x").random(3)))
        self.assertTrue(0 <= M.state32(SEED, "mlp") < 2 ** 32)


class Digits(unittest.TestCase):
    def ok(self):
        t = [np.array([0.0, 0.5], np.float16), np.array([0.25], np.float16)]
        u = [np.array([0, 699], np.uint16), np.array([3], np.uint16)]
        return t, u, np.array([0, 19], np.uint16)

    def test_good_digits_pass(self):
        t, u, y = M.check_digits(*self.ok(), 2)
        self.assertEqual(y.tolist(), [0, 19])

    def test_malformed_digits_are_refused(self):
        t, u, y = self.ok()
        bad = [(t, u, y, 3), (t, u, np.array([0, 20], np.uint16), 2),
               (t, [u[0], np.array([700], np.uint16)], y, 2),
               ([t[0], np.array([-0.1], np.float16)], u, y, 2),
               ([t[0], np.array([np.nan], np.float16)], u, y, 2),
               ([t[0], np.array([0.1, 0.2], np.float16)], u, y, 2),
               (t, [u[0], np.array([1.0])], y, 2)]
        for i, args in enumerate(bad):
            with self.subTest(i=i), self.assertRaises(M.Refused):
                M.check_digits(*args)


class Features(unittest.TestCase):
    def test_counts_take_every_spike(self):
        c = M.counts([np.array([0, 0, 699, 5], np.uint16)])
        self.assertEqual(c.shape, (1, 700))
        self.assertEqual((c[0, 0], c[0, 5], c[0, 699], c.sum()), (2, 1, 1, 4))

    def test_bins_and_groups(self):
        below = np.nextafter(np.float16(0.01), np.float16(0))          # the float16 just below 0.01
        t = np.array([0.0, below, 0.01, 0.999, 1.0, 1.3, 0.5], np.float16)
        u = np.array([10, 11, 699, 0, 5, 5, 350], np.uint16)
        X, left, total = M.binned([t], [u])
        self.assertEqual(X.shape, (1, 100, 64))
        self.assertEqual((left, total, X.sum()), (2, 7, 5))
        self.assertEqual(X[0, 0, 0], 1)              # channel 10 in group 0
        self.assertEqual(X[0, 0, 1], 1)              # channel 11 in group 1, just below 10 ms
        self.assertEqual(X[0, 1, 63], 1)             # float16(0.01) is above 0.01: the second bin
        self.assertEqual(X[0, 99, 0], 1)
        self.assertEqual(X[0, 50, 32], 1)            # 350 * 64 // 700 = 32
        sizes = np.bincount(np.arange(700) * 64 // 700)
        self.assertEqual((len(sizes), sizes.min(), sizes.max(), sizes.sum()), (64, 10, 11, 700))

    def test_split(self):
        fit, val = M.split(SEED)
        self.assertEqual((len(fit), len(val)), (7340, 816))
        self.assertEqual(len(np.union1d(fit, val)), 8156)
        self.assertEqual(len(np.intersect1d(fit, val)), 0)
        self.assertTrue(np.array_equal(val, M.split(SEED)[1]))
        self.assertFalse(np.array_equal(val, M.split("f" * 64)[1]))


def conv_direct(X, W, b):
    B, H, Wd, C = X.shape
    kh, kw, _, F = W.shape
    Y = np.zeros((B, H - kh + 1, Wd - kw + 1, F))
    for p in range(kh):
        for q in range(kw):
            Y += np.einsum("bhwc,cf->bhwf", X[:, p:p + Y.shape[1], q:q + Y.shape[2], :], W[p, q])
    return Y + b


class Pieces(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(7)

    def test_convolution_is_cross_correlation_with_valid_padding(self):
        for C, k in ((1, 11), (3, 3)):
            X = self.rng.standard_normal((2, 14, 12, C))
            W = self.rng.standard_normal((k, k, C, 4))
            b = self.rng.standard_normal(4)
            Y, _ = M.conv_fwd(X, W, b)
            self.assertTrue(np.allclose(Y, conv_direct(X, W, b)), (C, k))

    def test_convolution_gradients(self):
        for C, k in ((1, 5), (3, 3)):
            X = self.rng.standard_normal((2, 9, 8, C))
            W = self.rng.standard_normal((k, k, C, 4))
            b = self.rng.standard_normal(4)
            R = self.rng.standard_normal((2, 10 - k, 9 - k, 4))

            def loss():
                return float((M.conv_fwd(X, W, b)[0] * R).sum())
            Y, cols = M.conv_fwd(X, W, b)
            dW, db, dX = M.conv_bwd(R, cols, X.shape, W)
            for arr, grad in ((W, dW), (b, db), (X, dX)):
                idx = some(arr.shape, self.rng)
                self.assertTrue(np.allclose(numgrad(loss, arr, idx), [grad[i] for i in idx], rtol=1e-6, atol=1e-7))

    def test_batch_normalisation(self):
        x = self.rng.standard_normal((3, 4, 5, 2)) * 3 + 1
        g, be = self.rng.standard_normal(2), self.rng.standard_normal(2)
        mm, mv = np.zeros(2), np.ones(2)
        y, cache = M.bn_train(x, g, be, mm, mv)
        xm = x.reshape(-1, 2)
        want = (xm - xm.mean(0)) / np.sqrt(xm.var(0) + 1e-3) * g + be
        self.assertTrue(np.allclose(y.reshape(-1, 2), want))
        self.assertTrue(np.allclose(mm, 0.01 * xm.mean(0)))
        self.assertTrue(np.allclose(mv, 0.99 + 0.01 * xm.var(0, ddof=1)))
        R = self.rng.standard_normal(x.shape)

        def loss():
            return float((M.bn_train(x, g, be, np.zeros(2), np.ones(2))[0] * R).sum())
        dx, dg, dbe = M.bn_bwd(R, cache, g)
        for arr, grad in ((x, dx), (g, dg), (be, dbe)):
            idx = some(arr.shape, self.rng)
            self.assertTrue(np.allclose(numgrad(loss, arr, idx), [grad[i] for i in idx], rtol=1e-5, atol=1e-7))
        z = M.bn_infer(x, g, be, mm, mv)
        self.assertTrue(np.allclose(z, (x - mm) / np.sqrt(mv + 1e-3) * g + be))

    def test_typed_arithmetic_keeps_float32(self):
        x = self.rng.standard_normal((32, 60, 40, 32)).astype(np.float32)   # 76,800 rows: past 65,535
        g, be = np.ones(32, np.float32), np.zeros(32, np.float32)
        y, cache = M.bn_train(x, g, be, np.zeros(32, np.float32), np.ones(32, np.float32))
        dx, dg, dbe = M.bn_bwd(y, cache, g)
        self.assertEqual({y.dtype, dx.dtype, dg.dtype, dbe.dtype}, {np.dtype(np.float32)})

    def test_max_pooling(self):
        x = self.rng.standard_normal((2, 5, 7, 3))
        y, idx = M.pool_fwd(x)
        self.assertEqual(y.shape, (2, 2, 3, 3))                          # the odd last row and column dropped
        self.assertEqual(y[1, 1, 2, 0], x[1, 2:4, 4:6, 0].max())
        R = self.rng.standard_normal(y.shape)
        dx = M.pool_bwd(R, idx, x.shape)
        self.assertEqual(np.count_nonzero(dx), R.size)
        self.assertTrue(np.all(dx[:, 4, :, :] == 0) and np.all(dx[:, :, 6, :] == 0))
        idx2 = some(x.shape, self.rng)
        self.assertTrue(np.allclose(numgrad(lambda: float((M.pool_fwd(x)[0] * R).sum()), x, idx2),
                                    [dx[i] for i in idx2]))
        ties = np.zeros((1, 2, 2, 1))
        self.assertEqual(M.pool_bwd(np.ones((1, 1, 1, 1)), M.pool_fwd(ties)[1], ties.shape)[0, :, :, 0].tolist(),
                         [[1, 0], [0, 0]])                                 # a tie goes to the first, row by row

    def test_softmax_cross_entropy(self):
        z = self.rng.standard_normal((4, 20))
        y = np.array([0, 3, 19, 7])
        loss, d = M.softmax_ce(z, y)
        p = np.exp(z) / np.exp(z).sum(1, keepdims=True)
        self.assertAlmostEqual(loss, float(-np.log(p[np.arange(4), y]).mean()))
        idx = some(z.shape, self.rng)
        self.assertTrue(np.allclose(numgrad(lambda: M.softmax_ce(z, y)[0], z, idx), [d[i] for i in idx], atol=1e-8))


class Network(unittest.TestCase):
    def test_shapes_of_rule_6(self):
        self.assertEqual(M.out_shape((100, 64)), (7, 3))
        P, S = M.init(np.random.default_rng(0))
        self.assertEqual(P["d.W"].shape, (672, 128))
        self.assertEqual((sum(v.size for v in P.values()), sum(v.size for v in S.values())), (148500, 384))
        self.assertEqual(P["c1.W"].dtype, np.float32)
        lim = np.sqrt(6 / (121 + 121 * 32))
        self.assertTrue(np.abs(P["c1.W"]).max() <= lim and np.abs(P["c1.W"]).max() > 0.9 * lim)
        self.assertTrue(all(np.all(P[k] == 0) for k in P if k.endswith(".b") or k.endswith(".be")))
        X = np.random.default_rng(1).poisson(1.0, (3, 100, 64, 1)).astype(np.float32)
        logits, _ = M.forward(P, S, X, train=False)
        self.assertEqual(logits.shape, (3, 20))

    def test_whole_network_gradient_in_float64(self):
        rng = np.random.default_rng(3)
        P, S = M.init(rng, (46, 47))
        P = {k: v.astype(F64) for k, v in P.items()}
        S = {k: v.astype(F64) for k, v in S.items()}
        X = rng.poisson(2.0, (2, 46, 47, 1)).astype(F64)
        y = np.array([4, 11])

        def loss():
            logits, _ = M.forward(P, S, X, True, M.stream(SEED, "drop"))
            return M.softmax_ce(logits, y)[0]
        logits, caches = M.forward(P, S, X, True, M.stream(SEED, "drop"))
        G = M.backward(P, caches, M.softmax_ce(logits, y)[1])
        for k in ("c1.W", "b1a.W", "b1a.g", "b2b.W", "b3b.be", "d.W", "o.b"):
            idx = some(P[k].shape, rng, 4)
            self.assertTrue(np.allclose(numgrad(loss, P[k], idx), [G[k][i] for i in idx], rtol=1e-4, atol=1e-8), k)

    def test_adamax_as_keras_2_3(self):
        P = {"w": np.array([1.0], np.float32)}
        opt = M.Adamax(P)
        opt.step(P, {"w": np.array([0.5], np.float32)})
        self.assertAlmostEqual(float(P["w"][0]), 1 - 0.02 * 0.05 / (0.5 + 1e-7), places=6)
        opt.step(P, {"w": np.array([-1.0], np.float32)})
        m, u = 0.9 * 0.05 - 0.1, max(0.999 * 0.5, 1.0)
        self.assertAlmostEqual(float(P["w"][0]), 1 - 0.02 * 0.05 / 0.5 - 0.002 / (1 - 0.81) * m / u, places=6)


class Rules(unittest.TestCase):
    def test_rule_4s_list(self):
        names = [e[0] for e in M.extras(SEED)]
        self.assertEqual(names, ["svm_rbf_grid", "svm_rbf_log_grid", "logreg", "knn", "mlp"])
        self.assertEqual(len(M.GRID), 9)
        self.assertEqual(M.paper_svm({"kernel": "rbf"}).get_params()["gamma"], "auto")

    def test_verdict_thresholds_exactly(self):
        n, svm = 2264, {"svm_linear": 1300, "svm_rbf": 1359}
        self.assertEqual(M.verdict(svm, {"a": 1616}, 1359 + 363, n)[0], 1)   # 363 / 2264 = 16.03%
        self.assertEqual(M.verdict(svm, {"a": 1616}, 1359 + 362, n)[0], 0)   # 362 / 2264 = 15.99%
        self.assertEqual(M.verdict(svm, {"a": 1617}, 2000, n)[0], 0)         # 1617 / 2264 = 71.42%
        self.assertEqual(M.verdict(svm, {"a": 1616}, 2000, n)[1], {"margin": True, "bar": True})


class Refusals(unittest.TestCase):
    def test_wrong_input_hash_stops_the_run(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, M.INPUTS[0][0]), "wb") as f:
                f.write(gzip.compress(b"not the release"))
            with self.assertRaises(SystemExit):
                M.read(d, *M.INPUTS[0])


def inputs_dir():
    d = os.environ.get("SHD_INPUTS") or os.path.join(HERE, "..", "inputs")
    return d if all(os.path.isfile(os.path.join(d, name)) for name, _, _ in M.INPUTS) else None


@unittest.skipUnless(inputs_dir(), "the released files are not at inputs/ (or SHD_INPUTS)")
class Released(unittest.TestCase):
    def test_the_digits(self):
        (tt, tu, ty), (et, eu, ey) = [M.read(inputs_dir(), *x) for x in M.INPUTS]
        self.assertEqual((len(ty), len(ey)), (8156, 2264))
        self.assertEqual((np.bincount(ty).min(), np.bincount(ty).max()), (393, 421))
        X, left, total = M.binned(et, eu)
        self.assertEqual(int(X.sum(dtype=np.float64)) + left, total)      # a float32 sum would round
        self.assertEqual(M.counts(eu).sum(), total)
        self.assertLess(left, total / 1000)


if __name__ == "__main__":
    unittest.main()
