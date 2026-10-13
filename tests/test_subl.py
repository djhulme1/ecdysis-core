"""Subliminal learning of an MNIST MLP classifier (subl/mnist.py): the seeded streams; reading idx files and each
refusal; the scaling; the network's initialisation; each loss against the script's batched loss; the batched
formulation against these training steps; a student of its own untrained reference; the script's settings; the verdict
at and beside each threshold; and, with the claim's five inputs at inputs/ (or SUBL_INPUTS), a short run.

Needs PyTorch (the pytorch image). Run with: python3 -m unittest discover -s tests
"""

import gzip
import importlib.util
import os
import tempfile
import unittest

HAVE_TORCH = importlib.util.find_spec("torch") is not None
HERE = os.path.dirname(os.path.abspath(__file__))
INPUTS = os.environ.get("SUBL_INPUTS") or os.path.join(HERE, "..", "inputs")
SEED = "0" * 64

if HAVE_TORCH:
    import numpy as np
    import torch as t
    from torch import nn

    _spec = importlib.util.spec_from_file_location("subl_mnist", os.path.join(HERE, "..", "subl", "mnist.py"))
    M = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(M)
    HAVE = all(os.path.isfile(os.path.join(INPUTS, name)) for name, _ in M.INPUTS.values())
else:
    HAVE = False


def idx_images(n, rows=2, cols=2, magic=2051, extra=b""):
    body = bytes(range(n * rows * cols))
    head = b"".join(v.to_bytes(4, "big") for v in (magic, n, rows, cols))
    return gzip.compress(head + body + extra)


def idx_labels(labels, magic=2049):
    return gzip.compress(magic.to_bytes(4, "big") + len(labels).to_bytes(4, "big") + bytes(labels))


@unittest.skipUnless(HAVE_TORCH, "needs PyTorch")
class Streams(unittest.TestCase):
    def test_labels_and_seeds_give_different_streams(self):
        a = t.rand(4, generator=M.stream(SEED, "init/0"))
        self.assertTrue(t.equal(a, t.rand(4, generator=M.stream(SEED, "init/0"))))
        self.assertFalse(t.equal(a, t.rand(4, generator=M.stream(SEED, "init/1"))))
        self.assertFalse(t.equal(a, t.rand(4, generator=M.stream("1" * 64, "init/0"))))


@unittest.skipUnless(HAVE_TORCH, "needs PyTorch")
class Digits(unittest.TestCase):
    def test_idx_files(self):
        self.assertEqual(M.read_idx(idx_images(3)).shape, (3, 4))
        self.assertEqual(M.read_idx(idx_labels([1, 2, 9])).tolist(), [1, 2, 9])
        for bad in (idx_images(3, magic=2050), idx_images(3, extra=b"x"), idx_labels([1, 2])[:-3] + b"",
                    gzip.compress((2049).to_bytes(4, "big") + (5).to_bytes(4, "big") + bytes([1, 2]))):
            with self.subTest(bad=bad[:8]):
                with self.assertRaises(Exception):
                    M.read_idx(bad)

    def test_scale_is_the_scripts_transform(self):
        x = M.scale(np.array([[0, 255, 51]], dtype=np.uint8))
        self.assertEqual(x.dtype, t.float32)
        self.assertEqual(x.tolist()[0][:2], [-1.0, 1.0])
        self.assertAlmostEqual(x.tolist()[0][2], (51 / 255 - 0.5) / 0.5, places=6)

    def test_counts(self):
        self.assertEqual(sum(M.TRAIN_COUNTS), 60_000)
        self.assertEqual(sum(M.TEST_COUNTS), 10_000)
        self.assertEqual(M.counts(np.array([0, 0, 9], dtype=np.uint8)), (2, 0, 0, 0, 0, 0, 0, 0, 0, 1))


@unittest.skipUnless(HAVE_TORCH, "needs PyTorch")
class Network(unittest.TestCase):
    def test_initialisation(self):
        net = M.init(M.stream(SEED, "t"))
        self.assertEqual([tuple(w.shape) for w, _ in net], [(256, 784), (256, 256), (13, 256)])
        self.assertTrue(all(float(b.abs().max()) == 0.0 for _, b in net))
        self.assertAlmostEqual(float(net[0][0].std()), 1 / 28, delta=0.001)
        self.assertAlmostEqual(float(net[1][0].std()), 1 / 16, delta=0.002)

    def test_losses_are_the_scripts_share(self):
        g = M.stream(SEED, "loss")
        out, tgt = t.randn(2, 5, 3, generator=g), t.randn(2, 5, 3, generator=g)
        batched = nn.functional.kl_div(nn.functional.log_softmax(out, -1), nn.functional.softmax(tgt, -1),
                                       reduction="batchmean")
        mine = sum(M.distill_loss(out[m], tgt[m], models=2) for m in range(2))
        self.assertAlmostEqual(float(batched), float(mine), places=6)
        logits, labels = t.randn(2, 5, 13, generator=g), t.randint(0, 10, (2, 5), generator=g)
        batched = nn.functional.cross_entropy(logits[..., :10].flatten(0, 1), labels.flatten())
        mine = sum(M.teacher_loss(logits[m], labels[m], models=2) for m in range(2))
        self.assertAlmostEqual(float(batched), float(mine), places=6)

    def test_batched_formulation_agrees(self):
        g = M.stream(SEED, "b")
        x = t.rand(3000, 784, generator=g) * 2 - 1
        y = t.randint(0, 10, (3000,), generator=g)
        self.assertLess(M.batched_agrees(x, y, M.noise_of(g, 3000), g), 1e-9)

    def test_batched_formulation_agrees_under_many_seeds(self):
        # the sealed seed of 13 October found a float32 difference of 1.3e-4; in float64 every seed must agree
        for k in range(12):
            g = M.stream("%064x" % k, "batched")
            x = t.rand(2048, 784, generator=g) * 2 - 1
            y = t.randint(0, 10, (2048,), generator=g)
            with self.subTest(k=k):
                self.assertLess(M.batched_agrees(x, y, M.noise_of(g, 2048), g), 1e-9)

    def test_the_sealed_seed_of_13_october(self):
        seed = "6cad426c9705797320a0ad454c5e675d552e1c4bc02dfc81113d49f54159f164"
        if not HAVE:
            self.skipTest("needs the inputs")
        x = M.scale(M.read_idx(M.input_bytes(INPUTS, "train_x")))
        y = t.from_numpy(M.read_idx(M.input_bytes(INPUTS, "train_y")).astype(np.int64))
        worst = M.batched_agrees(x[:8192], y[:8192], M.noise_of(M.stream(seed, "batched-noise"), 8192),
                                 M.stream(seed, "batched"))
        self.assertLess(worst, 1e-9)

    def test_a_student_of_its_own_reference_stays(self):
        g = M.stream(SEED, "self")
        ref = M.init(g)
        x = t.rand(500, 784, generator=g) * 2 - 1
        y = t.randint(0, 10, (500,), generator=g)
        student = M.distill(M.clone(ref), ref, M.AUX, M.noise_of(g, 2048), g, epochs=1)
        self.assertLess(abs(M.accuracy(student, x, y) - M.accuracy(ref, x, y)), 2.0)

    def test_distillation_moves_the_student_towards_its_teacher(self):
        g = M.stream(SEED, "move")
        ref, other = M.init(g), M.init(g)
        noise = M.noise_of(g, 2048)
        with t.no_grad():
            before = float(M.distill_loss(M.forward(ref, noise)[:, list(M.AUX)], M.forward(other, noise)[:, list(M.AUX)]))
        student = M.distill(M.clone(ref), other, M.AUX, noise, g, epochs=3)
        with t.no_grad():
            after = float(M.distill_loss(M.forward(student, noise)[:, list(M.AUX)], M.forward(other, noise)[:, list(M.AUX)]))
        self.assertLess(after, before)


@unittest.skipUnless(HAVE_TORCH, "needs PyTorch")
class Script(unittest.TestCase):
    def test_facts(self):
        text = "\n".join(M.SCRIPT_FACTS)
        self.assertEqual(M.read_script(text), f"{len(M.SCRIPT_FACTS)} of {len(M.SCRIPT_FACTS)}")
        with self.assertRaises(M.Refused):
            M.read_script(text.replace("LR = 3e-4", "LR = 1e-3"))


@unittest.skipUnless(HAVE_TORCH, "needs PyTorch")
class Verdict(unittest.TestCase):
    def test_at_and_beside_each_threshold(self):
        self.assertEqual(sum(M.conditions(50.01, 15.0, 10.0).values()), 2)
        self.assertEqual(sum(M.conditions(50.0, 15.0, 10.0).values()), 1)
        self.assertEqual(sum(M.conditions(50.01, 15.01, 10.0).values()), 1)
        self.assertEqual(sum(M.conditions(49.0, 16.0, 10.0).values()), 0)


@unittest.skipUnless(HAVE, "needs PyTorch and the claim's five inputs at inputs/ or SUBL_INPUTS")
class Run(unittest.TestCase):
    def test_a_short_run(self):
        with tempfile.TemporaryDirectory() as d:
            out, detail = M.run(SEED, inputs=INPUTS, results=d, runs=2, shift_runs=1, log=None)
        self.assertEqual((out["runs"], out["controls"], out["script_facts"]), (2, "3 of 3", "30 of 30"))
        self.assertGreater(out["teacher_mean"], 90.0)
        self.assertLess(out["reference_mean"], 20.0)
        self.assertEqual(len(detail["runs"]), 2)


if __name__ == "__main__":
    unittest.main()
