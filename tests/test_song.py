"""Song, Miller & Abbott's STDP neuron (snn/song.py, snn/song.c): the seeds and the generator; the C program against
the plain implementation, bit for bit, on short runs at 25 Hz (with STDP from all peaks at gmax, and without it from
peaks read from a file); the pairing rule against the paper's F(dt); the measures (the current ratio at threshold, the
correlogram's normalisation and excess, the shares of peaks) and the conditions on values made up here; the outputs and
the seed refused. No run at the test's input rates or durations is made here, so none of the test's quantities is
computed.

Run with: python3 -m unittest discover -s tests -p test_song.py
"""

import importlib.util
import math
import os
import random
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("snn_song", os.path.join(HERE, "..", "snn", "song.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "ab" * 32


class Generator(unittest.TestCase):
    def test_words(self):
        w = M.words(SEED, "x")
        self.assertEqual(len(w), 4)
        self.assertTrue(all(len(x) == 16 for x in w))
        self.assertEqual(w, M.words(SEED, "x"))
        self.assertNotEqual(w, M.words(SEED, "y"))

    def test_uniform_and_poisson(self):
        g = M.Xoshiro(M.words(SEED, "u"))
        u = [g.unif() for _ in range(20000)]
        self.assertTrue(all(0.0 <= x < 1.0 for x in u))
        self.assertLess(abs(sum(u) / len(u) - 0.5), 4 * math.sqrt(1 / 12 / len(u)))
        lam = 0.4
        k = [g.poisson(lam, math.exp(-lam)) for _ in range(50000)]
        mean = sum(k) / len(k)
        var = sum((x - mean) ** 2 for x in k) / (len(k) - 1)
        self.assertLess(abs(mean - lam), 4 * math.sqrt(lam / len(k)))
        self.assertLess(abs(var / lam - 1), 0.05)
        self.assertTrue(all(0 <= g.below(7) < 7 for _ in range(1000)))


@unittest.skipIf(shutil.which("gcc") is None, "no gcc")
class Program(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp()
        cls.exe = M.build(cls.work)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def test_pairing_rule(self):
        for dt in (-30.0, -10.0, -2.0):                       # pre before post: potentiation A+ exp(dt/tau+)
            self.assertAlmostEqual(M.c_pair(self.exe, dt), M.A_PLUS * math.exp(dt / M.TAU_P), places=12)
        for dt in (2.0, 10.0, 30.0):                          # pre after post: depression A- exp(-dt/tau-)
            self.assertAlmostEqual(M.c_pair(self.exe, dt), -M.A_MINUS * math.exp(-dt / M.TAU_MS), places=12)

    def compare(self, c, p):
        for k in ("post_spikes", "rate", "cv", "gex_mean", "gin_mean", "pre_spikes", "inh_spikes", "corr", "weights"):
            self.assertEqual(c[k], p[k], k)

    def test_plain_with_stdp(self):
        w = M.words(SEED, "t/plain")
        wout = os.path.join(self.work, "w.txt")
        c = M.c_run(self.exe, w, 25, 0.05, 0.2, 1, "-", wout)
        p = M.plain_run(w, 25, 0.05, 0.2, 1)
        self.compare(c, p)
        self.assertGreater(c["post_spikes"], 0)                # the comparison saw spikes and STDP at work
        self.assertNotEqual(c["weights"], [1.0] * M.NE)

    def test_plain_held_peaks(self):
        rnd = random.Random(3)
        peaks = [rnd.choice((0.0, 0.25, 0.5, 1.0)) for _ in range(M.NE)]
        win = os.path.join(self.work, "in.txt")
        with open(win, "w") as fh:
            fh.write("\n".join(repr(x) for x in peaks) + "\n")
        w = M.words(SEED, "t/held")
        c = M.c_run(self.exe, w, 25, 0.0, 0.2, 0, win, os.path.join(self.work, "out.txt"))
        p = M.plain_run(w, 25, 0.0, 0.2, 0, weights=peaks)
        self.compare(c, p)
        self.assertEqual(c["weights"], peaks)                  # held: unchanged


class Measures(unittest.TestCase):
    def test_ratio(self):
        self.assertAlmostEqual(M.ratio(0.75, 0.5), 24 / 40.5)    # 16 (1 + 0.5) / (54 x 0.75)
        self.assertAlmostEqual(M.ratio(24 / 54, 0.5), 1.0)

    def test_correlation(self):
        res = {"post_spikes": 100, "pre_spikes": 10000 * 20, "corr": [1000] * M.NBIN}   # 20 s: 10 per ms
        c = M.correlation(res, 20.0)
        self.assertTrue(all(abs(x - 1.0) < 1e-12 for x in c))
        self.assertAlmostEqual(M.after_mean(c), 1.0)
        res["corr"] = [1000] * 30 + [1100] * 20 + [1000] * 50
        self.assertAlmostEqual(M.excess_before(M.correlation(res, 20.0)), 0.1)

    def test_shares(self):
        s = M.shares([0.0, 0.01, 0.5, 0.8, 0.96, 1.0])
        self.assertAlmostEqual(s["strong"], 3 / 6)
        self.assertAlmostEqual(s["bottom"], 2 / 6)
        self.assertAlmostEqual(s["top"], 2 / 6)

    def test_conditions(self):
        eq = {r: {"ratio": 1.15, "cv": 0.9} for r in M.RATES}
        cond = M.conditions(eq, 6.0, 0.01, 0.08)
        self.assertEqual((len(cond), sum(cond.values())), (10, 10))
        eq[30]["ratio"] = 1.31
        eq[20]["cv"] = 0.69
        cond = M.conditions(eq, 12.0, 0.05, 0.08)
        self.assertEqual(sum(cond.values()), 6)


class Verdict(unittest.TestCase):
    def test_outputs_named(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


if __name__ == "__main__":
    unittest.main()
