"""The primordial particle system (pps/check.py and pps/pps.c): the seeds and the generator; the compiled program against
the Python reference, bit for bit; a lone particle; the census lines and their refusals; the estimate and the verdict at
and beside each threshold; and a short run end to end, controls included.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import math
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pps_check", os.path.join(HERE, "..", "pps", "check.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "0" * 64
HAVE_GCC = shutil.which("gcc") is not None


def row(t, blue=0, yellow=0, **kw):
    r = {f: 0 for f in M.FIELDS}
    r.update(t=t, blue=blue, yellow=yellow, over15=blue + yellow, **kw)
    return r


def series(starts, finals, steps=M.STEPS):
    """Runs whose estimates are given at step 0 and at the last step (as numbers of particles: estimate x 48)."""
    return {k + 1: [row(0, blue=round(s * 48)), row(steps, blue=round(f * 48))] for k, (s, f) in enumerate(zip(starts, finals))}


class Seeds(unittest.TestCase):
    def test_labels_and_seeds_give_different_streams(self):
        self.assertNotEqual(M.seed_of(SEED, "run/1"), M.seed_of(SEED, "run/2"))
        self.assertNotEqual(M.seed_of(SEED, "run/1"), M.seed_of("1" * 64, "run/1"))
        self.assertEqual(M.seed_of(SEED, "run/1"), M.seed_of(SEED, "run/1"))

    def test_generator(self):
        a, b = M.Xoshiro(7), M.Xoshiro(7)
        self.assertEqual([a.next() for _ in range(5)], [b.next() for _ in range(5)])
        u = [a.unif() for _ in range(1000)]
        self.assertTrue(all(0 <= x < 1 for x in u))
        self.assertTrue(all(0 <= a.below(7) < 7 for _ in range(1000)))
        self.assertEqual(sorted({a.below(3) for _ in range(200)}), [0, 1, 2])


class Reference(unittest.TestCase):
    def test_a_lone_particle_holds_position(self):
        (x0, y0, p0), = M.initial(11, 1, 25.0)
        (x2, y2, p2), = M.reference(11, 1, 25.0, 2)
        self.assertLess(math.hypot(x2 - x0, y2 - y0), 1e-9)

    def test_two_close_particles_turn_towards_each_other(self):
        # with a neighbour on its right (R = 1), a particle turns by alpha + beta, not alpha - beta
        self.assertGreater(M.BETA, 0)
        self.assertAlmostEqual(math.degrees(M.ALPHA + M.BETA * 1 * 1), 197.0)


@unittest.skipUnless(HAVE_GCC, "needs gcc")
class Compiled(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        cls.exe = M.build(cls.dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir)

    def test_bit_for_bit_with_the_reference(self):
        for seed, n, side, steps in ((3, 60, 25.0, 60), (4, 25, 15.0, 40)):
            with self.subTest(seed=seed):
                self.assertEqual(M.trace(self.exe, seed, n, side, steps), M.reference(seed, n, side, steps))

    def test_census_lines(self):
        rows = M.finish(M.start(self.exe, 5, 20, 10, n=400, side=50.0))
        self.assertEqual([r["t"] for r in rows], [0, 10, 20])
        for r in rows:
            self.assertEqual(r["over15"], r["blue"] + r["yellow"])
            self.assertEqual(r["magenta_printed"], 0)
            self.assertLessEqual(r["blue_mf"] + r["yellow_mf"] + r["magenta_first"], 400)

    def test_a_dense_cluster_is_counted(self):
        # 400 particles in a 15 x 15 torus: every particle has many neighbours within 5
        rows = M.finish(M.start(self.exe, 6, 0, 1, n=400, side=15.0))
        self.assertEqual(rows[0]["yellow"], 400)


class Census(unittest.TestCase):
    def test_refusals(self):
        for text in ("0 1 2", "0 1 2 3 4 5 6 7 x", "0 1 2 3 4 5 6 7 8 9"):
            with self.subTest(text=text), self.assertRaises(M.Refused):
                M.parse_census(text)
        self.assertEqual(M.parse_census("5 1 1 0 2 0 0 1 0")[0]["brown"], 2)

    def test_estimates(self):
        r = row(0, blue=48, yellow=48, blue_mf=24, yellow_mf=24, magenta_first=36)
        self.assertEqual(M.estimate(r), 2.0)
        self.assertEqual(M.magenta_first(r), (1.0, 2.0))


class Verdict(unittest.TestCase):
    def test_passes(self):
        per, growing, mean, band, cond = M.judge(series([0.0] * 16, [50.0] * 16))
        self.assertEqual((len(growing), round(mean, 2)), (16, 50.0))
        self.assertTrue(all(cond.values()))

    def test_beside_each_threshold(self):
        cases = {
            "seven grow": (series([0.0] * 16, [50.0] * 7 + [10.0] * 9), 1),
            "eight grow": (series([0.0] * 16, [50.0] * 8 + [10.0] * 8), 2),
            "start at 1": (series([1.0] * 16, [50.0] * 16), 0),
            "final just under 25": (series([0.0] * 16, [24.98] * 16), 0),
            "mean too high": (series([0.0] * 16, [64.0] * 16), 1),
            "mean too low": (series([0.0] * 16, [37.5] * 16), 1),
        }
        for name, (s, want) in cases.items():
            with self.subTest(case=name):
                self.assertEqual(sum(M.judge(s)[4].values()), want)

    def test_the_band(self):
        lo, hi = M.judge(series([0.0], [50.0]))[3]
        self.assertAlmostEqual(lo, 37.905)
        self.assertAlmostEqual(hi, 63.175)


@unittest.skipUnless(HAVE_GCC, "needs gcc")
class Short(unittest.TestCase):
    def test_a_short_run_with_its_controls(self):
        with tempfile.TemporaryDirectory() as d:
            out, detail = M.run(SEED, results=d, runs=2, steps=2_500, every=2_500)
        self.assertEqual((out["runs"], out["controls"], out["printed_magenta"]), (2, "4 of 4", 0))
        self.assertEqual(out["reference_match"], "180 of 180")
        self.assertTrue(out["mirror"].startswith("yellow 0,"))
        self.assertLess(out["start_max"], 1)


if __name__ == "__main__":
    unittest.main()
