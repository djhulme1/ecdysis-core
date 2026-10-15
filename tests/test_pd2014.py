"""Potjans & Diesmann's microcircuit (snn/pd2014.py): the generator; the model's numbers (the PSP-to-PSC factor, the
synapse counts of Eq. 1, the propagators, the Poisson tables, the delays' moments); the statistics on spike trains
made here (rates, irregularity, synchrony) and the conditions on made-up numbers; and the C program against the plain
implementation on a network a few hundred neurons strong under a test seed. The full-scale model is never simulated
here.

Run with: python3 -m unittest tests.test_pd2014
"""

import importlib.util
import math
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("snn_pd2014", os.path.join(HERE, "..", "snn", "pd2014.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

TEST_SEED = "cd" * 32


class Generator(unittest.TestCase):
    def test_xoshiro_reference(self):
        # xoshiro256** from the state (1, 2, 3, 4): the reference implementation's first outputs
        r = M.Xoshiro(["1", "2", "3", "4"])
        self.assertEqual([r.next64() for _ in range(3)], [11520, 0, 1509978240])

    def test_words(self):
        self.assertEqual(len(M.words(TEST_SEED, "x")), 4)
        self.assertNotEqual(M.words(TEST_SEED, "x"), M.words(TEST_SEED, "y"))

    def test_draws(self):
        r = M.Xoshiro(M.words(TEST_SEED, "draws"))
        g = [r.gauss() for _ in range(20000)]
        mean = sum(g) / len(g)
        sd = math.sqrt(sum((x - mean) ** 2 for x in g) / len(g))
        self.assertLess(abs(mean), 0.03)
        self.assertLess(abs(sd - 1), 0.03)
        b = [r.below(7) for _ in range(7000)]
        self.assertEqual(set(b), set(range(7)))


class Numbers(unittest.TestCase):
    def test_psc_per_psp(self):
        # the code's factor: a 0.15 mV PSP needs 87.81 pA with tau_m 10 ms, tau_syn 0.5 ms, C_m 250 pF
        self.assertAlmostEqual(M.psc_per_psp() * 0.15, 87.8085, places=3)

    def test_psp_peak_analytic(self):
        # the PSP of an exponential current peaks at tau_m tau_s ln(tau_m/tau_s)/(tau_m - tau_s) = 1.577 ms
        w = M.psc_per_psp() * 0.15
        tm, ts, c = M.TAU_M, M.TAU_SYN, M.C_M
        tp = tm * ts * math.log(tm / ts) / (tm - ts)
        v = w * tm * ts / (c * (tm - ts)) * (math.exp(-tp / tm) - math.exp(-tp / ts))
        self.assertAlmostEqual(tp, 1.5767, places=3)
        self.assertAlmostEqual(v, 0.15, places=9)

    def test_synapse_count_inverts_eq1(self):
        k = M.synapse_count(0.1, 100, 100)
        self.assertEqual(k, 1053)
        prod = 100.0 * 100.0
        self.assertLessEqual(1 - (1 - 1 / prod) ** k, 0.1)
        self.assertGreater(1 - (1 - 1 / prod) ** (k + 1), 0.1)
        self.assertEqual(M.synapse_count(0.0, 100, 100), 0)

    def test_totals_near_the_papers(self):
        # structure only: "about 217 million excitatory and 82 million inhibitory synapses"
        for name in ("text", "code"):
            K = M.counts_matrix(M.reading(name), M.N)
            ke = sum(K[t][s] for t in range(8) for s in range(0, 8, 2))
            ki = sum(K[t][s] for t in range(8) for s in range(1, 8, 2))
            self.assertLess(abs(ke - 217e6) / 217e6, 0.01)
            self.assertLess(abs(ki - 82e6) / 82e6, 0.01)

    def test_readings(self):
        t, c = M.reading("text"), M.reading("code")
        self.assertEqual(t["wmean"][0][2], 2 * 87.8)
        self.assertEqual(t["wsd"][0][2], 2 * 8.8)
        self.assertAlmostEqual(t["wmean"][0][1], -351.2)
        self.assertAlmostEqual(c["wsd"][0][2], 0.1 * c["wmean"][1][0])
        self.assertAlmostEqual(c["wmean"][0][2], 2 * c["wmean"][1][0])
        self.assertEqual(t["delays"]["i"], (0.8, 0.4))
        self.assertEqual(c["delays"]["i"], (0.75, 0.375))
        self.assertEqual(t["probs"][2][5], 0.0003)
        self.assertEqual(c["probs"][7][3], 0.0005)

    def test_propagators(self):
        p11, p21, p22 = M.propagators()
        plain = M.TAU_M * M.TAU_SYN / (M.C_M * (M.TAU_M - M.TAU_SYN)) * (p22 - p11)
        self.assertAlmostEqual(p21 / plain, 1.0, places=12)
        self.assertAlmostEqual(p11, math.exp(-0.2), places=15)

    def test_poisson_table(self):
        lam = 1.28
        tab = M.poisson_table(lam)
        self.assertAlmostEqual(tab[-1], 1.0, places=12)
        self.assertAlmostEqual(tab[0], math.exp(-lam), places=15)
        r = M.Xoshiro(M.words(TEST_SEED, "poisson"))
        n, s = 40000, 0
        for _ in range(n):
            u, k = r.unif(), 0
            while k < M.PTAB - 1 and u >= tab[k]:
                k += 1
            s += k
        self.assertLess(abs(s / n - lam), 4 * math.sqrt(lam / n))

    def test_delay_moments(self):
        r = M.Xoshiro(M.words(TEST_SEED, "delays"))
        xs = []
        for _ in range(40000):
            x = 1.5 + 0.75 * r.gauss()
            while x < 0.1:
                x = 1.5 + 0.75 * r.gauss()
            xs.append(math.floor(x * 10 + 0.5) / 10)
        m = sum(xs) / len(xs)
        sd = math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))
        em, es = M.delay_moments(1.5, 0.75)
        self.assertLess(abs(m - em), 0.01)
        self.assertLess(abs(sd - es), 0.01)
        self.assertGreater(em, 1.5)          # the redraw below 0.1 ms lifts the mean


class Statistics(unittest.TestCase):
    def test_regular_and_poisson(self):
        regular = [[k * 1000 for k in range(60)] for _ in range(50)]
        st = M.population_stats(regular)
        self.assertAlmostEqual(st["irregularity"], 0.0, places=12)
        self.assertAlmostEqual(st["rate"], 1.0, places=12)
        r = M.Xoshiro(M.words(TEST_SEED, "trains"))
        tr = []
        for _ in range(1000):
            t, s = 0, []
            while True:
                t += 1 + int(-math.log(1.0 - r.unif()) / 0.0005)   # about 5 Hz on the 0.1 ms grid
                if t >= 600000:
                    break
                s.append(t)
            tr.append(s)
        st = M.population_stats(tr)
        self.assertLess(abs(st["irregularity"] - 1.0), 0.05)
        self.assertLess(abs(st["synchrony"] - 1.0), 0.15)
        self.assertLess(abs(st["rate"] - 5.0), 0.2)

    def test_synchronous(self):
        tr = [[k * 300 for k in range(1, 200)] for _ in range(1000)]
        self.assertGreater(M.population_stats(tr)["synchrony"], 100)

    def test_conditions(self):
        good = {"L2/3e": 0.86, "L2/3i": 2.8, "L4e": 4.45, "L4i": 5.8, "L5e": 7.59, "L5i": 8.7, "L6e": 1.09,
                "L6i": 7.7}
        st = {p: {"rate": v, "irregularity": 0.9, "synchrony": 2.0} for p, v in good.items()}
        self.assertTrue(all(M.conditions(st).values()))
        for change, failing in ((("L2/3e", 1.02), "L2/3e below 1 Hz"),
                                (("L4e", 5.6), "excitatory rates within 20% of Table 6"),
                                (("L5e", 4.0), "L5e the highest excitatory"),
                                (("L6i", 1.0), "inhibitory above excitatory in every layer")):
            bad = {p: dict(v) for p, v in st.items()}
            bad[change[0]]["rate"] = change[1]
            c = M.conditions(bad)
            self.assertFalse(c[failing], failing)
        bad = {p: dict(v) for p, v in st.items()}
        bad["L5e"]["synchrony"] = 9.0
        self.assertFalse(M.conditions(bad)["every synchrony below 8"])
        bad["L5e"]["synchrony"] = 2.0
        bad["L4i"]["irregularity"] = 0.6
        self.assertFalse(M.conditions(bad)["every irregularity from 0.7 to 1.2"])


@unittest.skipIf(shutil.which("gcc") is None, "no gcc")
class Program(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp(prefix="pd2014-test-", dir=os.path.join(HERE, ".."))
        cls.exe = M.build(cls.work)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def test_c_against_plain(self):
        for name in ("text", "code"):
            rd = M.reading(name)
            sizes = M.sizes_of(0.004)
            cfg, text = M.config(rd, TEST_SEED, sizes, 200, 800, 10 ** 9, os.path.join(self.work, f"t-{name}"))
            c = M.c_run(self.exe, text, cfg, self.work, f"t-{name}")
            p = M.plain_run(cfg)
            self.assertGreater(c["stats"]["spikes"], 0)
            self.assertEqual(list(c["counts"]), p["counts"])
            self.assertEqual([[(a[q], a[q + 1]) for q in range(0, len(a), 2)] for a in c["rec"]], p["rec"])
            self.assertEqual(list(c["V"]), p["V"])
            self.assertEqual(list(c["I"]), p["I"])
            self.assertEqual(list(c["ref"]), p["ref"])
            self.assertEqual(c["stats"]["synapses"], sum(map(sum, cfg["K"])))

    def test_psp(self):
        peak, step = M.c_psp(self.exe, M.psc_per_psp() * 0.15)
        self.assertLess(abs(peak - 0.15), 0.0005)
        self.assertEqual(step, 16)

    def test_recording_subset(self):
        rd = M.reading("code")
        sizes = M.sizes_of(0.004)
        cfg, text = M.config(rd, TEST_SEED, sizes, 100, 500, 5, os.path.join(self.work, "sub"))
        c = M.c_run(self.exe, text, cfg, self.work, "sub")
        base = [0]
        for n in sizes:
            base.append(base[-1] + n)
        for a in c["rec"]:
            for q in range(0, len(a), 2):
                i = a[q]
                p = max(k for k in range(8) if base[k] <= i)
                self.assertLess(i - base[p], 5)
                self.assertLess(a[q + 1], 500)


if __name__ == "__main__":
    unittest.main()
