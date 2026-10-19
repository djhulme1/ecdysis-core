"""Bak & Sneppen's model (alife/bs1993.py, alife/bs1993.c): the seeds and the generator; the C program against the
plain implementation, bit for bit, on short runs of sizes the test does not use (N = 50 in 1D, L = 6 in 2D, the planted
model, the start on [0.9, 1)); the measures (the edge of a flat distribution, the flatness, the log bins and their
integer ranges, the discrete power-law exponent, the percentile, the distance) on values made up here; and the
conditions, the outputs and the seed refused. No run of the test's sizes or lengths is made here, so none of the test's
quantities is computed.

Run with: python3 -m unittest discover -s tests -p test_bs1993.py
"""

import importlib.util
import math
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("alife_bs1993", os.path.join(HERE, "..", "alife", "bs1993.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "ef" * 32


class Generator(unittest.TestCase):
    def test_words_and_uniform(self):
        w = M.words(SEED, "x")
        self.assertEqual(len(w), 4)
        self.assertEqual(w, M.words(SEED, "x"))
        self.assertNotEqual(w, M.words(SEED, "y"))
        g = M.Xoshiro(M.words(SEED, "u"))
        u = [g.unif() for _ in range(20000)]
        self.assertTrue(all(0.0 <= x < 1.0 for x in u))
        self.assertLess(abs(sum(u) / len(u) - 0.5), 4 * math.sqrt(1 / 12 / len(u)))


@unittest.skipIf(shutil.which("gcc") is None, "no gcc")
class Program(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp()
        cls.exe = M.build(cls.work)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def compare(self, c, p):
        for k in ("N", "steps", "snapshots", "max_min", "waits", "avalanches", "open_runs", "bhist", "mhist", "cx",
                  "wait", "aval", "final"):
            self.assertEqual(c[k], p[k], k)
        self.assertAlmostEqual(c["mean_min"], p["mean_min"], places=12)

    def test_plain_1d(self):
        f0s = (0.4, 0.5, 0.6)
        for start in ("u", "h"):
            w4 = M.words(SEED, f"t/1d/{start}")
            c = M.c_run(self.exe, w4, 1, 50, "n", start, 3000, 20000, 40, 5, f0s, self.work, "a")
            p = M.plain_run(w4, 1, 50, "n", start, 3000, 20000, 40, 5, f0s)
            self.compare(c, p)
            self.assertEqual(c["snapshots"], 40)
            self.assertEqual(sum(c["bhist"][0]), 40 * 50)
            self.assertEqual(sum(c["bhist"][1]) + sum(c["bhist"][2]), sum(c["bhist"][0]))
            self.assertEqual(sum(c["mhist"]), 20000)
            self.assertEqual(sum(c["cx"]), 20000 - 1)
            self.assertGreater(sum(c["avalanches"]), 0)

    def test_plain_2d_and_fault(self):
        w4 = M.words(SEED, "t/2d")
        f0s = (0.2, 0.3)
        c = M.c_run(self.exe, w4, 2, 6, "n", "u", 2000, 10000, 20, 10, f0s, self.work, "b")
        p = M.plain_run(w4, 2, 6, "n", "u", 2000, 10000, 20, 10, f0s)
        self.compare(c, p)
        self.assertEqual(sum(c["cx"]), 0)                      # distances and waits are 1D measures
        self.assertEqual(c["waits"], 0)
        w4 = M.words(SEED, "t/fault")
        c = M.c_run(self.exe, w4, 1, 40, "s", "u", 1000, 5000, 10, 5, (0.5,), self.work, "f")
        p = M.plain_run(w4, 1, 40, "s", "u", 1000, 5000, 10, 5, (0.5,))
        self.compare(c, p)

    def test_the_rule(self):
        # one step from barriers the test sets: the minimum and its two ring neighbours are renewed, nothing else
        w4 = M.words(SEED, "t/rule")
        c = M.c_run(self.exe, w4, 1, 30, "n", "u", 0, 1, 1, 5, (0.5,), self.work, "r")
        g = M.Xoshiro(w4)
        b = [g.unif() for _ in range(30)]
        i = b.index(min(b))
        changed = [q for q in range(30) if c["final"][q] != b[q]]
        self.assertEqual(sorted(changed), sorted({i, (i - 1) % 30, (i + 1) % 30}))


class Measures(unittest.TestCase):
    def test_edge_flat_below(self):
        h = [0] * M.NBIN
        for k in range(int(0.6 * M.NBIN), M.NBIN):
            h[k] = 10
        self.assertAlmostEqual(M.edge(h), 0.6, places=9)
        self.assertLess(M.flat_deviation(h), 1e-12)
        self.assertEqual(M.share_below(h, 0.65), 500 * 10 / sum(h))
        h[M.NBIN - 1] += 10000
        self.assertGreater(M.flat_deviation(h), 0.05)

    def test_bins(self):
        for k in range(0, 420):                    # integer ranges of the log bins, against a direct count
            a, b = M.bin_range(k)
            want = [x for x in range(1, 20000) if M.lbin(x) == k]
            if want:
                self.assertEqual((a, b), (want[0], want[-1] + 1))
            else:
                self.assertEqual(a, b)
        self.assertEqual(M.bin_range(100)[0], 10)
        self.assertEqual(M.bin_range(199)[1], 100)

    def test_power_sum(self):
        for a in (0.9, 1.07, 1.5, 3.2):
            exact = math.fsum(x ** -a for x in range(1000, 30000))
            self.assertAlmostEqual(M.power_sum(1000, 30000, a) / exact, 1.0, places=10)

    def test_exponent_estimator(self):
        g = M.Xoshiro(M.words(SEED, "t/pareto"))
        xs = M.pareto_sample(g, 2.5, 3, 300, 40000)
        counts = [0] * 400
        for x in xs:
            counts[x] += 1
        a, n = M.mle_exponent(M.groups_from_exact(counts, 3, 300), 3, 300)
        self.assertEqual(n, 40000)
        self.assertLess(abs(a - 2.5), 0.05)
        h = M.log_hist(M.pareto_sample(g, 1.2, 100, 100000, 60000))
        exps = M.window_exponents(M.groups_from_log, h, ((100, 1000), (1000, 10000), (10000, 100000)))
        self.assertTrue(all(abs(e - 1.2) < 0.08 for e in exps), exps)
        self.assertTrue(M.power_law(exps))
        self.assertFalse(M.power_law([1.0, 1.4]))
        self.assertFalse(M.power_law([-0.1, -0.1]))

    def test_percentile_mode_distance(self):
        h = [0] * M.LBIN
        h[M.lbin(10)] = 98
        h[M.lbin(5000)] = 2
        self.assertEqual(M.percentile(h, 0.98), M.bin_range(M.lbin(10))[0])
        self.assertEqual(M.percentile(h, 0.99), M.bin_range(M.lbin(5000))[0])
        m = [0] * M.NBIN
        m[6600] = 5
        self.assertAlmostEqual(M.mode_of(m), 0.66005)
        a, b = [0] * M.NBIN, [0] * M.NBIN
        a[2000], b[2500] = 1, 1
        self.assertAlmostEqual(M.wasserstein(a, b), 0.05, places=9)
        self.assertEqual(M.wasserstein(a, a), 0.0)

    def test_conditions(self):
        good = {"flat_dev": 0.01, "below": 0.003, "bc": 0.667, "max_min": 0.671, "cx_exp": [3.2, 3.25],
                "av_exp": [1.05, 1.07, 1.1], "wt_exp": [1.5, 1.55, 1.6],
                "p99": {0.55: 100, 0.60: 1000, 0.63: 6000, 0.65: 60000, 0.66: 700000}, "halves": 0.0003}
        r = {"n4096": dict(good), "n256": {"halves": 0.0005}, "n1024u": {"halves": 0.0004},
             "n1024h": {"halves": 0.0004}, "starts": 0.0005}
        cond = M.conditions(r)
        self.assertEqual((len(cond), sum(cond.values())), (15, 15))
        r["n4096"]["bc"] = 0.655
        r["n4096"]["av_exp"] = [1.0, 1.5, 1.1]
        r["n4096"]["p99"] = {**good["p99"], 0.66: 100000}
        r["starts"] = 0.003
        cond = M.conditions(r)
        self.assertEqual(sum(cond.values()), 11)

    def test_outputs_and_refusal(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)
        self.assertLessEqual(len(M.TEST), 600)
        with self.assertRaises(M.Refused):
            M.run("not a seed", results=tempfile.mkdtemp())


if __name__ == "__main__":
    unittest.main()
