"""Jain & Krishna's model (alife/jk.py, alife/jk.c): the paper's numbers and the cap; the growth time and the chance of
an entirely autocatalytic random graph (the paper's 1e-16 for 117 positive links); the two ways to the maximal ACS on
hand-made graphs; the generator; the plain population dynamics on a 2-cycle against its Perron-Frobenius eigenvector
and on a negative link; the C program against the plain implementation on a small model of 8 species; the verdict at
and beside each band; the seed refused. No run of the model at s = 100 is made here.

Run with: python3 -m unittest discover -s tests -p test_jk.py
"""

import importlib.util
import math
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("alife_jk", os.path.join(HERE, "..", "alife", "jk.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


class Numbers(unittest.TestCase):
    def test_paper(self):
        self.assertEqual(float(M.tau_a("0.005")), 1600.0)            # "(= 1600 for p = 0.005 and s = 100)"
        self.assertEqual(float(M.tau_g("0.005")), 400.0)
        self.assertEqual(M.cap("0.0025"), 80000)
        self.assertEqual(M.cap("0.005"), 24000)
        self.assertEqual(M.cap("0.0012"), 311112)
        self.assertEqual(M.PS, ("0.0012", "0.0025", "0.005"))

    def test_figure2_points(self):
        # Figure 2 plots ln tau_g against ln(p/2); its three rightmost points are at p/2 = 6e-4, 1.25e-3 and 2.5e-3.
        for p, half in zip(M.PS, (6e-4, 1.25e-3, 2.5e-3)):
            self.assertAlmostEqual(float(p) / 2, half)

    def test_growth_time(self):
        r = {"n2": 3643, "m1": 1904, "a_m1": 2}
        self.assertAlmostEqual(M.growth_time(r), 1739 / math.log(50))
        self.assertIsNone(M.growth_time({"n2": -1, "m1": 5, "a_m1": 2}))
        self.assertIsNone(M.growth_time({"n2": 9, "m1": 9, "a_m1": 100}))

    def test_chance(self):
        # "The probability that a random graph with s = 100 nodes and m* = 1.17 would be an ACS is ... about 1e-16."
        self.assertAlmostEqual(M.chance_log10(117), -16.0, delta=0.05)

    def test_stats(self):
        self.assertEqual(M.median([3, 1, 2]), 2)
        self.assertEqual(M.median([4, 1, 2, 3]), 2.5)
        self.assertAlmostEqual(M.sd([1, 2, 3, 4]), math.sqrt(5 / 3))
        self.assertAlmostEqual(M.slope([0, 1, 2], [1, 3, 5]), 2.0)


class Acs(unittest.TestCase):
    def test_hand_graphs(self):
        for name, c, want in M.hand_graphs():
            self.assertEqual(M.acs_pruning(c), want, name)
            self.assertEqual(M.acs_cycles(c), want, name)

    def test_negative_links_do_not_count(self):
        c = [[0.0, -0.5], [-0.5, 0.0]]
        self.assertEqual(M.acs_pruning(c), set())
        c = [[-0.5, 0.0], [0.0, -0.5]]                              # self-links are never positive
        self.assertEqual(M.acs_cycles(c), set())

    def test_random_agreement(self):
        ok, d = M.control_acs("5a" * 32)
        self.assertTrue(ok, d)


class Generator(unittest.TestCase):
    def test_words(self):
        w = M.words("ab" * 32, "jk/run/0.005/1")
        self.assertEqual(len(w), 4)
        self.assertEqual(w, M.words("ab" * 32, "jk/run/0.005/1"))
        self.assertNotEqual(w, M.words("ab" * 32, "jk/run/0.005/2"))

    def test_xoshiro(self):
        # xoshiro256** from the state (1, 2, 3, 4): its first outputs, as the reference implementation gives them.
        g = M.Xoshiro(["1", "2", "3", "4"])
        self.assertEqual([g.next64() for _ in range(3)], [11520, 0, 1509978240])

    def test_unif_and_below(self):
        g = M.Xoshiro(M.words("cd" * 32, "t"))
        for _ in range(1000):
            u = g.unif()
            self.assertTrue(0.0 <= u < 1.0)
            self.assertIn(g.below(7), range(7))


class Dynamics(unittest.TestCase):
    def plain_on(self, s, links, t):
        m = M.Plain(M.words("ef" * 32, "t"), s, "0.5", M.X0, t, M.DT, M.EPS)
        m.c = [[0.0] * s for _ in range(s)]
        for i, j, v in links:
            m.c[i][j] = v
        m.x = [1.0 / s] * s
        m.evolve()
        return m.x

    def test_perron_frobenius(self):
        x = self.plain_on(5, [(1, 0, 0.5), (0, 1, 0.8), (2, 1, 0.3), (4, 4, -0.5)], "300")
        lam = math.sqrt(0.4)
        v = [0.8 / lam, 1.0, 0.3 / lam, 0.0, 0.0]
        v = [a / sum(v) for a in v]
        for a, b in zip(x, v):
            self.assertAlmostEqual(a, b, places=12)
        self.assertLessEqual(x[3], float(M.EPS))

    def test_held_at_zero(self):
        x = self.plain_on(3, [(1, 0, 0.5), (0, 1, 0.8), (2, 0, -0.4)], "50")
        self.assertEqual(x[2], 0.0)
        self.assertGreater(x[0], 0.0)

    def test_least_fit_ties_at_zero(self):
        m = M.Plain(M.words("01" * 32, "t"), 4, "0.5", M.X0, "1", M.DT, M.EPS)
        m.x = [0.5, 0.0, 0.5, 1e-12]
        for _ in range(50):
            self.assertIn(m.least_fit(), (1, 3))
        m.x = [0.25, 0.25, 0.2, 0.3]
        self.assertEqual(m.least_fit(), 2)

    def test_replace_rescales(self):
        m = M.Plain(M.words("02" * 32, "t"), 4, "0.5", M.X0, "1", M.DT, M.EPS)
        m.x = [0.5, 0.0, 0.25, 0.25]
        m.replace(1)
        self.assertEqual(m.x[1], 1e-4)
        self.assertAlmostEqual(sum(m.x), 1.0, places=15)
        self.assertAlmostEqual(m.x[0], 0.5 * (1 - 1e-4), places=15)


@unittest.skipIf(shutil.which("gcc") is None, "no gcc")
class Compiled(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp()
        cls.exe = M.build(cls.work)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def test_trace_matches_plain(self):
        w = M.words("9e" * 32, "test/trace")
        got = M.c_trace(self.exe, w, 8, "0.3", M.X0, "6", M.DT, M.EPS, 6)
        want = M.plain_trace(w, 8, "0.3", M.X0, "6", M.DT, M.EPS, 6)
        self.assertEqual(got, want)

    def test_graph_mode(self):
        ok, d = M.control_perron(self.exe)
        self.assertTrue(ok, d)
        ok, d = M.control_clamp(self.exe)
        self.assertTrue(ok, d)


class Verdict(unittest.TestCase):
    def stats(self, n1, g):
        return {p: {"runs": 50, "spanned": 50, "n1_mean": n1 * float(M.tau_a(p)), "g_mean": g * float(M.tau_g(p))}
                for p in M.PS}

    def test_bands(self):
        c = M.conditions(self.stats(1.0, 1.0), -1.0)
        self.assertEqual(len(c), 10)
        self.assertTrue(all(c.values()))
        self.assertTrue(all(M.conditions(self.stats(0.5, 0.75), -1.2).values()))
        self.assertTrue(all(M.conditions(self.stats(2.0, 1.25), -0.8).values()))
        self.assertEqual(sum(M.conditions(self.stats(0.49, 1.0), -1.0).values()), 7)
        self.assertEqual(sum(M.conditions(self.stats(1.0, 1.26), -1.0).values()), 7)
        self.assertEqual(sum(M.conditions(self.stats(1.0, 1.0), -1.21).values()), 9)
        st = self.stats(1.0, 1.0)
        st["0.0025"]["spanned"] = 49
        self.assertEqual(sum(M.conditions(st, -1.0).values()), 9)

    def test_slope_of_exact_law(self):
        gm = [float(M.tau_g(p)) for p in M.PS]
        self.assertAlmostEqual(M.slope([math.log(float(p)) for p in M.PS], [math.log(g) for g in gm]), -1.0)

    def test_outputs_fit(self):
        res = {p: [{"run": r, "n1": 1000 + r, "a_n1": 2, "s1_n1": 3, "m1": 1000 + r, "a_m1": 2, "n2": 99999,
                    "losses": 1, "s1_n2": 99, "lp": 117, "ln": 12, "lp0": 25, "ln0": 26, "pre_mean": 77.5,
                    "slope": 0.0025, "updates": 99999} for r in range(1, 51)] for p in M.PS}
        stats, sl = M.summarise(res)
        ok, links = M.control_links(res)
        cond = M.conditions(stats, sl)
        vals = M.values_from(stats, sl, cond, {"links": links})
        for k in M.OUTPUTS:
            if k in vals and isinstance(vals[k], str):
                self.assertLessEqual(len(vals[k]), M.LIMIT, k)
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


if __name__ == "__main__":
    unittest.main()
