"""Self-driven particles (spp/vicsek.py and its engine spp/vicsek.c): the engine against the plain implementation,
cells against brute force, the two limits of the noise, the program's refusals, and the exponent's fit on curves made
here. All on sizes and noises chosen here: no run at the test's size (N = 4000, L = 31.6) is made.

Run with: python3 -m unittest tests.test_vicsek
"""

import importlib.util
import math
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("spp_vicsek", os.path.join(HERE, "..", "spp", "vicsek.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "3e" * 32


def params(**kw):
    p = {"N": 25, "L": 4.2, "v": 0.03, "r": 1.0, "eta": 1.2, "steps": 120, "burn": 0, "block": 60, "seed": 11,
         "mode": 0, "align": 0}
    p.update(kw)
    return p


def power_curve(beta, etac, amp=1.05):
    return {e: (amp * ((etac - e) / etac) ** beta if e < etac else 0.03) for e in M.NOISES}


class Engine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp()
        cls.exe = M.build(cls.work)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def test_against_python(self):
        for N, L, eta, steps, seed in ((25, 4.2, 1.2, 120, 11), (12, 2.5, 3.3, 150, 12), (30, 5.0, 0.4, 100, 13)):
            pc = M.c_run(self.exe, self.work, params(N=N, L=L, eta=eta, steps=steps, seed=seed), "trace")["particles"]
            pp = M.py_run(N, L, eta, steps, seed)
            self.assertEqual(len(pc), N)
            self.assertLess(max(max(abs(a - b) for a, b in zip(u, w)) for u, w in zip(pc, pp)), 1e-9, (N, L))

    def test_cells_against_brute_force(self):
        for L, eta in ((8.7, 0.9), (6.0, 2.8)):
            a = M.c_run(self.exe, self.work, params(N=300, L=L, eta=eta, steps=100, mode=0), "trace")
            b = M.c_run(self.exe, self.work, params(N=300, L=L, eta=eta, steps=100, mode=1), "trace")
            self.assertEqual(a["particles"], b["particles"])
            self.assertEqual(a["va"], b["va"])

    def test_limits(self):
        r = M.c_run(self.exe, self.work, params(N=100, L=5.0, eta=2 * math.pi, steps=3000, block=1000, seed=21))
        want = math.sqrt(math.pi / 400)
        self.assertLess(abs(r["va"] - want), 0.05 * want)
        self.assertEqual(len(r["blocks"]), 3)
        o = M.c_run(self.exe, self.work, params(N=100, L=5.0, eta=0.0, steps=300, align=1))
        self.assertAlmostEqual(o["va"], 1.0, places=12)
        # order at low noise, a little disorder at moderate noise
        lo = M.c_run(self.exe, self.work, params(N=100, L=5.0, eta=0.3, steps=2000, burn=2000, block=1000, seed=22))
        mid = M.c_run(self.exe, self.work, params(N=100, L=5.0, eta=4.0, steps=2000, burn=2000, block=1000, seed=22))
        self.assertGreater(lo["va"], 0.95)
        self.assertLess(mid["va"], lo["va"])

    def test_burn_and_blocks(self):
        r = M.c_run(self.exe, self.work, params(steps=500, burn=300, block=100))
        self.assertEqual(r["n"], 500)
        self.assertEqual(len(r["blocks"]), 5)
        self.assertAlmostEqual(sum(r["blocks"]) / 5, r["va"], places=10)

    def test_determinism(self):
        a = M.c_run(self.exe, self.work, params(seed=5))
        b = M.c_run(self.exe, self.work, params(seed=5))
        c = M.c_run(self.exe, self.work, params(seed=6))
        self.assertEqual(a["end"], b["end"])
        self.assertNotEqual(a["end"], c["end"])

    def test_refusals(self):
        def code(text):
            path = os.path.join(self.work, "bad.txt")
            with open(path, "w") as fh:
                fh.write(text)
            return subprocess.run([self.exe, "run", path], capture_output=True).returncode
        good = "N 10\nL 3.0\nv 0.03\neta 1\nsteps 5\n"
        self.assertEqual(code(good), 0)
        self.assertEqual(code(good + "colour 2\n"), 2)
        self.assertEqual(code(good.replace("L 3.0", "L 1.5")), 2)      # a box no wider than 2r
        self.assertEqual(code(good.replace("N 10", "N 0")), 2)
        self.assertEqual(code(good + "eta -1\n"), 2)


class Fit(unittest.TestCase):
    def test_line(self):
        slope, icpt, rss, r2 = M.line([0, 1, 2, 3], [1, 3, 5, 7])
        self.assertAlmostEqual(slope, 2)
        self.assertAlmostEqual(icpt, 1)
        self.assertAlmostEqual(rss, 0)
        self.assertAlmostEqual(r2, 1)

    def test_recovers_a_power_law(self):
        for beta, etac in ((0.3, 2.95), (0.6, 3.07), (0.45, 2.812)):
            f = M.exponent(power_curve(beta, etac))
            self.assertIsNotNone(f)
            self.assertAlmostEqual(f["etac"], etac, places=6)
            self.assertAlmostEqual(f["beta"], beta, places=6)
            self.assertGreaterEqual(f["points"], M.MIN_POINTS)
            self.assertAlmostEqual(f["r2"], 1.0, places=9)

    def test_window(self):
        # every point used lies within 0.02 to 0.5 of eta_c: a curve whose shape changes outside the window is fitted
        # by its shape inside it
        c = power_curve(0.4, 3.0)
        for e in c:
            if (3.0 - e) / 3.0 > 0.5:
                c[e] = 0.99
        f = M.exponent(c)
        self.assertAlmostEqual(f["beta"], 0.4, places=6)

    def test_no_fit(self):
        self.assertIsNone(M.exponent({e: 0.9 for e in M.NOISES}))          # never disordered
        self.assertIsNone(M.exponent({e: 0.01 for e in M.NOISES}))         # never ordered
        sparse = {0.5: 0.99, 2.9: 0.3, 3.0: 0.04, 4.5: 0.01}
        self.assertIsNone(M.exponent(sparse))                              # too few points in the window

    def test_a_jump_is_not_straight(self):
        # a discontinuous drop: flat order then a jump to disorder gives a poor line or none
        c = {e: (0.7 if e < 2.75 else 0.02) for e in M.NOISES}
        c[0.5] = 0.99
        f = M.exponent(c)
        self.assertTrue(f is None or f["r2"] < M.R2_MIN or abs(f["beta"] - M.BETA) > M.BETA_TOL)


class Run(unittest.TestCase):
    def test_refused_seed(self):
        with self.assertRaises(M.Refused):
            M.run("nothex", results=os.path.join(HERE, "nonexistent"))

    def test_test_length(self):
        self.assertLessEqual(len(M.TEST), 600)

    def test_rules(self):
        self.assertEqual(M.SIZES["test"], (4000, 31.6))
        self.assertEqual(len(M.NOISES), 23)
        self.assertEqual((M.NOISES[0], M.NOISES[1], M.NOISES[-2], M.NOISES[-1]), (0.5, 1.4, 3.4, 4.5))
        self.assertEqual((M.RUNS, M.BURN, M.MEASURE), (4, 3000, 6000))
        self.assertEqual(M.WINDOW, (0.02, 0.50))

    def test_seeds(self):
        self.assertNotEqual(M.seed64(SEED, "4000/2.00/0"), M.seed64(SEED, "4000/2.00/1"))
        self.assertEqual(M.seed64(SEED, "x"), M.seed64(SEED, "x"))

    def test_work_inside_results(self):
        seen = []
        real = M.assess

        def fake(seed, work):
            seen.append(work)
            return {"test_passed": 0}, {}
        results = tempfile.mkdtemp()
        try:
            M.assess = fake
            M.run(SEED, results=results)
            self.assertEqual(os.path.dirname(seen[0]), results)
            self.assertFalse(os.path.exists(seen[0]))
        finally:
            M.assess = real
            shutil.rmtree(results, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
