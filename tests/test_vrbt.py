"""van Rossum, Bi & Turrigiano's stable weight distribution (snn/vrbt.py): the generator; the statistics on samples
drawn here (moments, quantiles, bandwidth, modes, distances); the rule's pairings with the noise off; and the C program
against the plain implementation over a fraction of a second under a test seed. No weight distribution of the model
is measured here.

Run with: python3 -m unittest tests.test_vrbt
"""

import importlib.util
import math
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("snn_vrbt", os.path.join(HERE, "..", "snn", "vrbt.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

TEST_SEED = "ab" * 32


class Generator(unittest.TestCase):
    def test_words_and_stream(self):
        w = M.words(TEST_SEED, "x")
        self.assertEqual(len(w), 4)
        self.assertNotEqual(M.words(TEST_SEED, "x"), M.words(TEST_SEED, "y"))
        a, b = M.Xoshiro(w), M.Xoshiro(w)
        self.assertEqual([a.next64() for _ in range(5)], [b.next64() for _ in range(5)])

    def test_xoshiro_reference(self):
        # xoshiro256** from the state (1, 2, 3, 4): the reference implementation's first outputs
        r = M.Xoshiro(["1", "2", "3", "4"])
        self.assertEqual([r.next64() for _ in range(3)], [11520, 0, 1509978240])

    def test_draws(self):
        r = M.Xoshiro(M.words(TEST_SEED, "draws"))
        g = [r.gauss() for _ in range(20000)]
        mean = sum(g) / len(g)
        sd = math.sqrt(sum((x - mean) ** 2 for x in g) / len(g))
        self.assertLess(abs(mean), 0.03)
        self.assertLess(abs(sd - 1), 0.03)
        lam = 0.2
        k = [r.poisson(lam, math.exp(-lam)) for _ in range(50000)]
        self.assertLess(abs(sum(k) / len(k) - lam), 0.01)


class Statistics(unittest.TestCase):
    def test_summary(self):
        vals = [1.0, 2.0, 3.0, 10.0]
        mean, sd, skew = M.summary(M.moments_of(vals))
        m = sum(vals) / 4
        m2 = sum((x - m) ** 2 for x in vals) / 4
        m3 = sum((x - m) ** 3 for x in vals) / 4
        self.assertAlmostEqual(mean, m, places=9)
        self.assertAlmostEqual(sd, math.sqrt(m2), places=9)
        self.assertAlmostEqual(skew, m3 / m2 ** 1.5, places=9)
        self.assertLess(M.summary(M.moments_of([10.0 - x for x in vals]))[2], 0)

    def test_quantile_and_ks(self):
        h = M.bin_values([float(x) for x in range(100)])
        self.assertAlmostEqual(M.quantile(h, 0.5), 49.25)
        self.assertEqual(M.ks(h, h), 0.0)
        far = M.bin_values([1000.0 + x for x in range(100)])
        self.assertEqual(M.ks(h, far), 1.0)
        half = M.bin_values([float(x) for x in range(50)] + [1000.0 + x for x in range(50)])
        self.assertAlmostEqual(M.ks(h, half), 0.5)
        self.assertEqual(M.bin_values([6000.0, -1.0]), {M.NBINS: 1})

    def test_bandwidth(self):
        vals = [float(x) for x in range(1000)]
        h = M.bin_values(vals)
        sd = math.sqrt(sum((x - 499.5) ** 2 for x in vals) / 1000)
        iqr = M.quantile(h, 0.75) - M.quantile(h, 0.25)
        self.assertAlmostEqual(M.bandwidth(h, sd), 0.9 * min(sd, iqr / 1.34) * 1000 ** -0.2)

    def test_modes(self):
        r = M.Xoshiro(M.words(TEST_SEED, "modes"))
        one = [300.0 + 40.0 * r.gauss() for _ in range(20000)]
        two = [(200.0 if r.unif() < 0.5 else 600.0) + 40.0 * r.gauss() for _ in range(20000)]
        edge = [-50.0 * math.log(1.0 - r.unif()) for _ in range(20000)]   # densest at 0: one mode, at the grid's end
        for vals, want in ((one, 1), (two, 2), (edge, 1)):
            hist = M.bin_values(vals)
            sd = M.summary(M.moments_of(vals))[1]
            self.assertEqual(len(M.modes(hist, M.bandwidth(hist, sd))), want)
        # a minor bump below the floor is not a mode
        small = one + [900.0 + 5.0 * r.gauss() for _ in range(20)]
        hist = M.bin_values(small)
        self.assertEqual(len(M.modes(hist, M.bandwidth(hist, M.summary(M.moments_of(small))[1]))), 1)

    def test_coarse(self):
        self.assertEqual(M.coarse({0: 1, 19: 2, 20: 3}), {"0": 3, "10": 3})


@unittest.skipIf(shutil.which("gcc") is None, "gcc is not available")
class Program(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp()
        cls.exe = M.build(cls.work)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def test_pairings(self):
        e5, e25 = math.exp(-0.5), math.exp(-0.25)
        self.assertAlmostEqual(M.c_pair(self.exe, 300.0, 0.0, "pre:0,post:100"), 300.0 + M.CP * e5, places=12)
        self.assertAlmostEqual(M.c_pair(self.exe, 300.0, 0.0, "post:0,pre:100"), 300.0 * (1 - M.CD * e5), places=12)
        self.assertAlmostEqual(M.c_pair(self.exe, 300.0, 0.0, "pre:0,post:100,post:150"), 300.0 + M.CP * e5,
                               places=12)
        self.assertAlmostEqual(M.c_pair(self.exe, 300.0, 0.0, "post:0,pre:100,pre:150"), 300.0 * (1 - M.CD * e5),
                               places=12)
        both = M.c_pair(self.exe, 300.0, 0.0, "pre:0,pre:50,post:100")
        self.assertAlmostEqual(both, 300.0 + M.CP * (e5 + e25), places=12)
        self.assertNotEqual(M.c_pair(self.exe, 300.0, 0.015, "pre:0,post:100"), 300.0 + M.CP * e5)

    def test_matches_plain(self):
        w4 = M.words(TEST_SEED, "plain-test")
        wout = os.path.join(self.work, "w.txt")
        c = M.c_run(self.exe, w4, "uniform", 0.2, 0.0, 0.05, M.GINH_EACH, M.CD, M.SIGMA, 1, wout)
        p = M.plain_run(w4, "uniform", 0.2, 0.0, 0.05, M.GINH_EACH, M.CD, M.SIGMA, 1)
        for k in ("rate", "post_spikes", "pre_arrivals", "inh_arrivals", "gex_mean", "gin_mean", "wmin", "wmax",
                  "hist", "weights"):
            self.assertEqual(c[k], p[k], k)
        for h in (0, 1):
            for a, b in zip(c["mom"][h], p["mom"][h]):
                self.assertLessEqual(abs(a - b), 1e-9 * max(1.0, abs(b)))

    def test_held_and_file_start(self):
        held = M.c_run(self.exe, M.words(TEST_SEED, "held-test"), "250", 2.0, 0.0, 1.0, M.GINH_EACH, M.CD, M.SIGMA, 0,
                       os.path.join(self.work, "held.txt"))
        self.assertEqual(held["weights"], [250.0] * M.NE)
        self.assertEqual(sum(held["hist"][0].values()) + sum(held["hist"][1].values()), 2 * M.NE)
        start = os.path.join(self.work, "start.txt")
        with open(start, "w") as fh:
            for i in range(M.NE):
                fh.write(f"{100.0 + i!r}\n")
        frozen = M.c_run(self.exe, M.words(TEST_SEED, "file-test"), "file:" + start, 0.1, 0.0, 0.1, M.GINH_EACH,
                         M.CD, M.SIGMA, 0, os.path.join(self.work, "frozen.txt"))
        self.assertEqual(frozen["weights"], [100.0 + i for i in range(M.NE)])


class Machinery(unittest.TestCase):
    def test_test_text_and_outputs(self):
        self.assertLessEqual(len(M.TEST), 600)
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")

    def test_exponential_start(self):
        a = M.exponential_start(TEST_SEED, "e")
        self.assertEqual(a, M.exponential_start(TEST_SEED, "e"))
        self.assertEqual(len(a), M.NE)
        self.assertTrue(all(x >= 0 for x in a))


if __name__ == "__main__":
    unittest.main()
