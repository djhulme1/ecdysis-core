"""Gradient alignment in subliminal learning (subl/align.py): the streams; reading idx files and notebooks and each
refusal; the network; the projection, orthogonal when it acts and idle otherwise; the audit stream's passes; the trait
gradient as the mean of batch means; the verdict at and beside each threshold; the released results' reader and its
refusal; and, with the claim's seven inputs at inputs/ (or ALIGN_INPUTS), one short run in this process.

Needs PyTorch (the pytorch image). Run with: python3 -m unittest tests.test_align
"""

import csv
import gzip
import importlib.util
import io
import json
import os
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("subl_align", os.path.join(HERE, "..", "subl", "align.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
t = M.t

INPUTS = os.environ.get("ALIGN_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = all(os.path.isfile(os.path.join(INPUTS, name)) for name, _ in M.INPUTS.values())
SEED = "0" * 64


class Streams(unittest.TestCase):
    def test_labels_and_seeds(self):
        a = t.rand(4, generator=M.stream(SEED, "init/0"))
        self.assertTrue(t.equal(a, t.rand(4, generator=M.stream(SEED, "init/0"))))
        self.assertFalse(t.equal(a, t.rand(4, generator=M.stream(SEED, "init/1"))))
        self.assertFalse(t.equal(a, t.rand(4, generator=M.stream("1" * 64, "init/0"))))


class Files(unittest.TestCase):
    def test_idx(self):
        imgs = gzip.compress((2051).to_bytes(4, "big") + (2).to_bytes(4, "big") + (28).to_bytes(4, "big") +
                             (28).to_bytes(4, "big") + bytes(2 * 784))
        self.assertEqual(M.read_idx(imgs).shape, (2, 784))
        for bad in (gzip.compress((2049).to_bytes(4, "big") + (3).to_bytes(4, "big") + bytes(2)),
                    gzip.compress((7).to_bytes(4, "big"))):
            with self.subTest(bad=bad[:8]), self.assertRaises(M.Refused):
                M.read_idx(bad)

    def test_notebook_code_and_facts(self):
        nb = {"cells": [{"cell_type": "markdown", "source": ["eps=1e-12"]},
                        {"cell_type": "code", "source": ["a = 1\n", "if dot > 0.0:\n"]}]}
        code = M.code_of(json.dumps(nb).encode("utf-8"))
        self.assertIn("if dot > 0.0:", code)
        self.assertNotIn("eps=1e-12", code)                 # markdown is not code
        self.assertEqual(M.read_facts(code, ("a = 1",), "test"), 1)
        with self.assertRaises(M.Refused):
            M.read_facts(code, ("eps=1e-12",), "test")


class Network(unittest.TestCase):
    def test_init_and_forward(self):
        net = M.init(M.stream(SEED, "init/0"))
        self.assertEqual([tuple(w.shape) for w, _ in net], [(256, 784), (256, 256), (13, 256)])
        self.assertAlmostEqual(float(net[0][0].std()), 1 / 28, delta=0.002)
        self.assertTrue(all(float(b.abs().sum()) == 0.0 for _, b in net))
        self.assertEqual(tuple(M.forward(net, t.zeros(5, 784)).shape), (5, 13))


class Projection(unittest.TestCase):
    def test_orthogonal_when_it_acts(self):
        g = t.tensor([1.0, 2.0, 0.0])
        tr = t.tensor([1.0, 0.0, 0.0])
        out, did = M.project(g, tr)
        self.assertTrue(did)
        self.assertAlmostEqual(float(out @ tr), 0.0, places=6)
        self.assertTrue(t.allclose(out, t.tensor([0.0, 2.0, 0.0])))

    def test_idle_when_not_aligned(self):
        g = t.tensor([-1.0, 2.0])
        out, did = M.project(g, t.tensor([1.0, 0.0]))
        self.assertFalse(did)
        self.assertTrue(t.equal(out, g))
        self.assertFalse(M.project(t.tensor([0.0, 1.0]), t.tensor([1.0, 0.0]))[1])       # zero product: no projection


class Audit(unittest.TestCase):
    def test_passes_cover_the_set(self):
        s = M.AuditStream(2500, t.Generator().manual_seed(1))
        first = [s.next() for _ in range(3)]
        self.assertEqual([len(b) for b in first], [1024, 1024, 452])
        self.assertEqual(sorted(int(i) for b in first for i in b), list(range(2500)))
        self.assertEqual(len(s.next()), 1024)                                          # a new pass

    def test_trait_gradient_is_the_mean_of_batch_means(self):
        net = M.init(M.stream(SEED, "init/0"))
        xs, ys = t.rand(6, 784), t.tensor([0, 1, 2, 3, 4, 5])
        groups = [t.tensor([0, 1, 2, 3]), t.tensor([4, 5])]
        got = M.trait_grad(net, xs, ys, groups)
        losses = [t.nn.functional.cross_entropy(M.forward(net, xs[j])[:, :10], ys[j]) for j in groups]
        want = M.flat(t.autograd.grad((losses[0] + losses[1]) / 2, M.params(net)))
        self.assertTrue(t.allclose(got, want))


class Verdict(unittest.TestCase):
    def test_at_and_beside_each_threshold(self):
        ok = (0.64, [0.51] * 5, 0.0038, 22.6)
        self.assertEqual(sum(M.conditions(*ok).values()), 5)
        for bad in ((0.6399, [0.51] * 5, 0.0038, 22.6), (0.64, [0.51] * 4 + [0.5], 0.0038, 22.6),
                    (0.64, [0.51] * 5, 0.00379, 22.6), (0.64, [0.51] * 5, 0.1, 22.6), (0.64, [0.51] * 5, 0.0038, 22.59)):
            with self.subTest(bad=bad):
                self.assertEqual(sum(M.conditions(*bad).values()), 4)


class Released(unittest.TestCase):
    def zipped(self, seeds):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for s in seeds:
                for cond, acc in (("control", 0.5), ("intervention", 0.1)):
                    rows = io.StringIO()
                    w = csv.writer(rows)
                    w.writerow(["seed", "condition", "student_test_acc", "projected_fraction"])
                    w.writerow([s, cond, acc + s / 10000, 0.5])
                    z.writestr(f"runs_mnist_conflicting_grad_revised/seed_{s:02d}/{cond}_metrics.csv", rows.getvalue())
        return buf.getvalue()

    def test_reads_the_hundred_seeds(self):
        summary, acted = M.released_summary(self.zipped(range(1, 101)))
        self.assertAlmostEqual(summary["control"][0], 50.505, places=6)
        self.assertAlmostEqual(summary["intervention"][2], 10.01, places=6)
        self.assertEqual(acted, 0.5)

    def test_refuses_a_missing_seed(self):
        with self.assertRaises(M.Refused):
            M.released_summary(self.zipped(range(1, 100)))


@unittest.skipUnless(HAVE, "the claim's seven inputs are not at inputs/ (or ALIGN_INPUTS)")
class Run(unittest.TestCase):
    def test_one_short_run(self):
        with tempfile.TemporaryDirectory() as d:
            out, detail = M.run(SEED, inputs=INPUTS, results=d, runs=1, placebo_runs=1, workers=1, log=None)
            self.assertEqual(sorted(os.listdir(d)), ["detail.json", "outputs.json"])
        self.assertEqual(tuple(out), M.OUTPUTS)
        self.assertEqual(out["notebook_facts"], f"{len(M.ALIGN_FACTS) + len(M.PROJECT_FACTS)} of "
                                                f"{len(M.ALIGN_FACTS) + len(M.PROJECT_FACTS)}")
        self.assertEqual(out["controls"], "2 of 2")
        self.assertIn("control 55.28 sd 10.48 (26.31-76.04), projected 10.14 sd 1.33", out["released"])
        self.assertEqual(detail["runs"][0]["steps"], 5 * 59)
        self.assertGreater(out["teacher_mean"], 90.0)


if __name__ == "__main__":
    unittest.main()
