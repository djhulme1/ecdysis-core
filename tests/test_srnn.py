"""The released SHD network of Yin, Corradi & Bohte (snn/srnn.py): the restricted unpickler; the bins against the
generator's rule spike by spike, at the edges; the vectorised network against the step-by-step one on a random small
network; the readout's start; the script's facts and its log; the verdict at and beside each threshold; and, with the
claim's three inputs at inputs/ (or SRNN_INPUTS), a short run.

Run with: python3 -m unittest discover -s tests
"""

import collections
import importlib.util
import io
import os
import pickle
import tempfile
import unittest
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("snn_srnn", os.path.join(HERE, "..", "snn", "srnn.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

INPUTS = os.environ.get("SRNN_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = all(os.path.isfile(os.path.join(INPUTS, name)) for name, _ in M.INPUTS.values())
SEED = "0" * 64


def random_params(rng):
    p = {k: rng.normal(0, 0.3, size=s) for k, s in M.SHAPES.items()}
    for k in ("tau_adp_h1", "tau_adp_h2", "tau_adp_o"):
        p[k] = rng.uniform(100, 200, size=M.SHAPES[k])
    for k in ("tau_m_h1", "tau_m_h2", "tau_m_o"):
        p[k] = rng.uniform(5, 30, size=M.SHAPES[k])
    p["i_2_h1.weight"] = rng.normal(0.2, 0.5, size=M.SHAPES["i_2_h1.weight"])
    return p


class Archive(unittest.TestCase):
    def test_a_foreign_name_is_refused(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("archive/data.pkl", pickle.dumps(collections.Counter(), protocol=2))
        with self.assertRaises(M.Refused):
            M.read_archive(buf.getvalue())

    def test_a_plain_dict_is_not_a_module(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("archive/data.pkl", pickle.dumps(collections.OrderedDict(a=1), protocol=2))
        with self.assertRaises(M.Refused):
            M.read_archive(buf.getvalue())


class Bins(unittest.TestCase):
    def test_edges(self):
        e = M.edges()
        self.assertEqual((len(e), float(e[0]), float(e[-1])), (250, 0.0, float(np.float16(0.996))))
        self.assertTrue(np.all(np.diff(e.astype(np.float64)) > 0))

    def test_against_the_rule_spike_by_spike(self):
        rng = np.random.default_rng(4)
        e = M.edges()
        for k in range(3):
            t = np.concatenate([rng.uniform(0, 1.2, 300), e[[0, 1, 37, 249]].astype(np.float64), [0.99609375, 1.0]])
            u = np.concatenate([rng.integers(0, 700, 300), [0, 5, 699, 1], [3, 4]])
            t16 = t.astype(np.float16)
            X, kept, total = M.binarise([t16], [u.astype(np.uint16)])
            with self.subTest(k=k):
                self.assertTrue(np.array_equal(X[0], M.binarise_slow(t16, u)))
                self.assertEqual(total, len(t))

    def test_unit_zero_and_late_spikes_are_left_out(self):
        t = np.array([0.0, 0.5, 0.999], dtype=np.float16)
        u = np.array([0, 10, 10], dtype=np.uint16)
        X, kept, total = M.binarise([t], [u])
        self.assertEqual((kept, total, int(X.sum())), (1, 3, 1))
        self.assertEqual(int(X[0, 125, 690]), 1)              # 0.5 is edge 125; unit 10 lights channel 690


class Network(unittest.TestCase):
    def test_vectorised_against_step_by_step(self):
        rng = np.random.default_rng(5)
        p = random_params(rng)
        X = (rng.random((3, 40, M.CHANNELS)) < 0.05).astype(np.uint8)
        m1, m2, mo = M.starts(rng, 3)
        fast = M.forward(p, X, m1, m2, mo)
        for k in range(3):
            self.assertLess(float(np.max(np.abs(M.forward_one(p, X[k], m1[k], m2[k], mo[k]) - fast[k]))), 1e-9)
        self.assertGreater(float(fast.sum()), 0)

    def test_the_readout_starts_after_step_ten(self):
        rng = np.random.default_rng(6)
        p = random_params(rng)
        X = (rng.random((2, 12, M.CHANNELS)) < 0.05).astype(np.uint8)
        m = M.starts(rng, 2)
        self.assertEqual(float(M.forward(p, X[:, :11], *m).sum()), 0.0)
        self.assertAlmostEqual(float(M.forward(p, X, *m).sum()), 2.0)   # one softmax per digit at step 11

    def test_accuracy(self):
        out = np.array([[0.1, 0.9], [0.8, 0.2], [0.3, 0.7]])
        self.assertAlmostEqual(M.accuracy(out, np.array([1, 0, 0])), 200 / 3)
        self.assertAlmostEqual(M.accuracy(out, np.array([1, 0, 0]), np.array([True, False, True])), 50.0)


class Script(unittest.TestCase):
    def test_facts_and_log(self):
        text = "\n".join(M.SCRIPT_FACTS) + (
            "\n# epoch:  1 . Loss:  1.4 . Tr Accuracy:  30.9 . Ts Accuracy:  40.9 Fr:  0.1\n"
            "# epoch:  2 . Loss:  0.5 . Tr Accuracy:  58.2 . Ts Accuracy:  75.79 Fr:  0.14\n")
        self.assertEqual(M.read_script(text), [(1, 30.9, 40.9), (2, 58.2, 75.79)])
        with self.assertRaises(M.Refused):
            M.read_script(text.replace("beta = 1.8", "beta = 1.7"))
        with self.assertRaises(M.Refused):
            M.read_script("\n".join(M.SCRIPT_FACTS))


class Verdict(unittest.TestCase):
    def test_at_and_beside_each_threshold(self):
        self.assertEqual(sum(M.conditions(90.35).values()), 3)
        self.assertEqual(sum(M.conditions(90.349).values()), 2)
        self.assertEqual(sum(M.conditions(87.2).values()), 1)
        self.assertEqual(sum(M.conditions(82.7).values()), 0)


@unittest.skipUnless(HAVE, "needs the claim's three inputs at inputs/ or SRNN_INPUTS")
class Run(unittest.TestCase):
    def test_a_short_run(self):
        with tempfile.TemporaryDirectory() as d:
            out, detail = M.run(SEED, inputs=INPUTS, results=d, draws=2)
        self.assertEqual((out["digits"], out["draws"], out["controls"]), (2264, 2, "5 of 5"))
        self.assertGreater(out["mean_accuracy"], 90.0)
        self.assertTrue(out["script_log"].startswith("19 epochs"))


if __name__ == "__main__":
    unittest.main()
