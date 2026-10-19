"""Rubin, Lee & Sompolinsky's network (snn/rubin.py, snn/rubin.c): the seeds and the generator; the C program against
the plain implementation, bit for bit, on short runs at 25 Hz under each rule (from uniform weights, from every weight
at 1, and with the weights held); the pairing rule against Delta w = +-lambda f(w) K; the membrane against its
analytic first spike under a constant conductance; the measures (the Wasserstein distance, T+ and T- and chi, the
shares, the equilibration mark, Eq. 9's w0 and the single synapse at dt = +-200 ms) and the conditions on values made
up here; the outputs and the seed refused. No run at the test's rates or durations is made here, so none of the
test's quantities is computed.

Run with: python3 -m unittest discover -s tests -p test_rubin.py
"""

import importlib.util
import math
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("snn_rubin", os.path.join(HERE, "..", "snn", "rubin.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "cd" * 32


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
        lam = 2.5
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
        for rule in (0, 1):
            for w in (0.2, 0.5, 0.9):
                for dt in (0.0, 2.0, 10.0, 30.0):                 # the output after the input: potentiation
                    want = M.LAMBDA * M.fplus(rule, w) * math.exp(-dt / M.TAU)
                    self.assertAlmostEqual(M.c_pair(self.exe, rule, dt, w), want, places=12)
                for dt in (-2.0, -10.0, -30.0):                   # the output before the input: depression
                    want = -M.LAMBDA * M.fminus(rule, w) * math.exp(dt / M.TAU)
                    self.assertAlmostEqual(M.c_pair(self.exe, rule, dt, w), want, places=12)
        self.assertEqual(M.c_pair(self.exe, 0, -1.0, 0.0), 0.0)    # clipped at 0
        self.assertEqual(M.c_pair(self.exe, 0, 1.0, 1.0), 0.0)     # clipped at 1

    def test_membrane(self):
        for g in (0.3, 0.5, 1.0, 2.0):
            vinf = g * M.V_S / (1 + g)
            t = M.TAU_M / (1 + g) * math.log(vinf / (vinf - 1))
            got = M.c_const(self.exe, g)
            self.assertLessEqual(abs(got - t), M.DT + 1e-9)
            self.assertGreaterEqual(got, t - 1e-9)                 # the spike is seen at the end of its step
        self.assertEqual(M.c_const(self.exe, 0.2), float("inf"))   # V_inf = 0.83: never

    def compare(self, c, p):
        for k in ("post_spikes", "rate", "pre_spikes", "pre_fixed", "pre_plastic", "g_mean", "splus_fixed",
                  "sminus_fixed", "splus_pool", "sminus_pool", "snapshots", "hist", "weights", "windows"):
            self.assertEqual(c[k], p[k], k)
        self.assertAlmostEqual(c["w_mean"], p["w_mean"], places=12)
        self.assertAlmostEqual(c["w_sd"], p["w_sd"], places=12)

    def test_plain_each_rule(self):
        for rule in (0, 1):
            for start in ("u", "1"):
                w4 = M.words(SEED, f"t/plain/{rule}/{start}")
                c = M.c_run(self.exe, w4, rule, 25.0, M.GS, 0.05, 0.3, start, 1, self.work, "t", snap=500,
                            window=700)
                p = M.plain_run(w4, rule, 25.0, M.GS, 0.05, 0.3, start, 1, 500, 700)
                self.compare(c, p)
                self.assertGreater(c["post_spikes"], 0)              # spikes, so the rule was at work
                self.assertEqual(c["snapshots"], 6)
                self.assertEqual(sum(c["hist"][0]), 6 * (M.N - 1))
                self.assertEqual(sum(c["hist"][1]) + sum(c["hist"][2]), sum(c["hist"][0]))
                self.assertEqual(c["weights"][0], M.W_FIXED)
                self.assertTrue(all(0.0 <= x <= 1.0 for x in c["weights"]))

    def test_held(self):
        w4 = M.words(SEED, "t/held")
        c = M.c_run(self.exe, w4, 1, 25.0, 0.02, 0.0, 0.2, "h", 0, self.work, "h", snap=1000, window=1000)
        p = M.plain_run(w4, 1, 25.0, 0.02, 0.0, 0.2, "h", 0, 1000, 1000)
        self.compare(c, p)
        self.assertEqual(c["weights"], [0.5] * M.N)
        self.assertEqual((c["splus_pool"], c["sminus_pool"]), (0.0, 0.0))
        self.assertEqual(c["hist"][0][M.NBIN // 2], 2 * (M.N - 1))


class Measures(unittest.TestCase):
    def test_wasserstein(self):
        a, b = M.point_mass(0.30), M.point_mass(0.35)
        self.assertAlmostEqual(M.wasserstein(a, b), 0.05, places=9)
        self.assertAlmostEqual(M.wasserstein(b, a), 0.05, places=9)
        self.assertEqual(M.wasserstein(a, a), 0.0)
        u = [1] * M.NBIN
        half = [0] * (M.NBIN // 2) + [2] * (M.NBIN // 2)             # uniform on [0.5, 1]
        self.assertAlmostEqual(M.wasserstein(u, half), 0.25, places=3)
        mix = [0] * M.NBIN
        mix[0], mix[-1] = 1, 1                                      # half at 0, half at 1
        self.assertAlmostEqual(M.wasserstein(mix, M.point_mass(0.5)), 0.5, places=3)
        self.assertTrue(math.isnan(M.wasserstein([0] * M.NBIN, a)))

    def test_chance_and_chi(self):
        tc = M.tau_chance()
        self.assertAlmostEqual(tc, M.TAU + M.DT / 2, places=3)
        # 100 s, 1,000 inputs and 2,000 outputs: by chance S+ = n_out x (n_in / T) x tau'
        n_in, n_out, T = 1000, 2000, 100.0
        s = n_out * n_in / (T * 1000.0) * tc
        self.assertAlmostEqual(M.t_plus(s, n_in, n_out, T), 0.0, places=9)
        self.assertAlmostEqual(M.t_minus(n_in * n_out / (T * 1000.0) * (tc - M.DT), n_in, n_out, T), 0.0, places=9)
        self.assertAlmostEqual(M.t_plus(s * 1.1, n_in, n_out, T), 0.1 * tc, places=9)
        res = {"splus_fixed": s * 1.1, "pre_fixed": n_in, "post_spikes": n_out, "meas": T, "splus_pool": s * 1.2,
               "pre_plastic": n_in, "sminus_pool": n_in * n_out / (T * 1000.0) * (tc - M.DT), "w_mean": 0.5}
        c = M.chis(res)
        self.assertAlmostEqual(c["chi_fixed"], 0.1 * tc / (0.5 * M.TAU), places=9)
        self.assertAlmostEqual(c["chi_pool"], 0.2 * tc / (0.5 * M.TAU), places=9)
        self.assertAlmostEqual(c["t_minus_pool_ms"], 0.0, places=9)

    def test_shares_and_equilibration(self):
        h = [0] * M.NBIN
        h[0], h[999], h[1000], h[8999], h[9000], h[-1] = 3, 1, 2, 2, 1, 1
        lo, hi = M.shares(h)
        self.assertAlmostEqual(lo, 4 / 10)
        self.assertAlmostEqual(hi, 2 / 10)
        series = [f"{x:.9f}:10.00" for x in (0.9, 0.7, 0.55, 0.5, 0.52, 0.495, 0.505, 0.5)]
        self.assertEqual(M.equilibration(series, 0.5), 60.0)        # within from the sixth 10 s mark on
        self.assertIsNone(M.equilibration(series[:-1] + ["0.6:10.00"], 0.5))

    def test_w0(self):
        self.assertAlmostEqual(M.w0_formula(1e6), 1 / (1 + M.ALPHA), places=9)
        self.assertAlmostEqual(M.w0_formula(-1e6), 1 / (1 + M.ALPHA), places=9)
        self.assertAlmostEqual(M.w0_formula(10.0), 0.8167, places=4)
        self.assertAlmostEqual(M.w0_formula(-10.0), 0.1691, places=4)
        dt0 = M.TAU * math.log(1 / ((M.ALPHA - 1) * M.TAU * 1e-3 * M.SINGLE_RATE))
        self.assertAlmostEqual(dt0, 52.98, places=2)

    def test_single_synapse_other_shifts(self):
        # 200 ms apart the trains are nearly uncorrelated: the multiplicative weight near 1/(1 + alpha)
        w = M.single_synapse(SEED, 1, 200.0, T=2000.0, start_at=500.0)
        self.assertLess(abs(w - M.w0_formula(200.0)), 0.02)
        # the additive rule at +-30 ms, inside dt0 on either side: to 1 when the output follows, to 0 when it leads
        self.assertGreater(M.single_synapse(SEED, 0, 30.0, T=1000.0, start_at=500.0), 0.95)
        self.assertLess(M.single_synapse(SEED, 0, -30.0, T=1000.0, start_at=500.0), 0.05)

    def test_conditions(self):
        dist = {("rate", a, b): 0.01 for i, a in enumerate(M.RATES) for b in M.RATES[i + 1:]}
        gss = (M.GS,) + M.GS_POST
        dist.update({("gs", a, b): 0.02 for i, a in enumerate(gss) for b in gss[i + 1:]})
        halves = {f"run {i}": 0.001 for i in range(7)}
        cond = M.conditions(dist, halves, 0.002)
        self.assertEqual((len(cond), sum(cond.values())), (17, 17))
        dist[("rate", 10, 40)] = 0.05
        dist[("gs", 0.015, 0.02)] = 0.07
        halves["run 3"] = 0.01
        cond = M.conditions(dist, halves, 0.011)
        self.assertEqual(sum(cond.values()), 13)

    def test_outputs_and_refusal(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertIn("test_passed", M.OUTPUTS)
        self.assertLessEqual(len(M.TEST), 600)
        with self.assertRaises(M.Refused):
            M.run("not a seed", results=tempfile.mkdtemp())


if __name__ == "__main__":
    unittest.main()
