"""Couzin et al.'s zones model (spp/couzin2002.py): the series, the random numbers, the rules on constructed
configurations, the measures, the classes, the decision, Spearman's rho, the noise's exact moments, and the C program
against the plain implementation, all on inputs other than the test's (small groups, other radii, synthetic curves).
Nothing here runs the sweep of 100 individuals with r_a = 14.

Run with: python3 -m unittest tests.test_couzin2002 (in the pinned buildpack-deps image, which has gcc)
"""

import importlib.util
import math
import os
import random
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("spp_couzin2002", os.path.join(HERE, "..", "spp", "couzin2002.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


def placed(n, cs, vs, **kw):
    m = M.Model(n, 1, aligned=1, spread=1000.0, sigma=0.0, **kw)
    m.c = [list(x) for x in cs]
    m.v = [list(x) for x in vs]
    return m


class Series(unittest.TestCase):
    def test_sin_cos_log(self):
        rng = random.Random(5)
        for _ in range(20000):
            x = rng.uniform(-3.0, 3.0)
            s, c = M.dsincos(x)
            self.assertLessEqual(abs(s - math.sin(x)), 8 * 2.0 ** -52)
            self.assertLessEqual(abs(c - math.cos(x)), 8 * 2.0 ** -52)
            y = rng.uniform(1e-6, 50.0)
            self.assertLessEqual(M.ulps(M.dlog(y), math.log(y)), 4)
        self.assertEqual(M.dlog(1.0), 0.0)
        self.assertEqual(M.dsincos(0.0), (0.0, 1.0))


class Random(unittest.TestCase):
    def test_reproducible_and_normal(self):
        a, b = M.Rng(42), M.Rng(42)
        self.assertEqual([a.next() for _ in range(10)], [b.next() for _ in range(10)])
        r = M.Rng(7)
        xs = [r.gauss() for _ in range(40000)]
        m = sum(xs) / len(xs)
        v = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
        self.assertLess(abs(m), 5 / math.sqrt(len(xs)))
        self.assertLess(abs(v - 1), 5 * math.sqrt(2 / len(xs)))
        u = [M.Rng(9).uni() for _ in range(3)]
        self.assertTrue(all(0.0 <= x < 1.0 for x in u))


class Rules(unittest.TestCase):
    def test_turning_limit(self):
        m = placed(2, [(0.0, 0.0, 0.0), (0.0, 5.0, 0.0)], [(1.0, 0.0, 0.0), (1.0, 0.0, 0.0)], ro=1.5, ra=10.0)
        v0 = m.v[0][:]
        m.step()
        ang = math.acos(max(-1.0, min(1.0, M.dot(v0, m.v[0]))))
        self.assertAlmostEqual(ang, math.radians(4.0), delta=1e-12)
        self.assertGreater(m.v[0][1], 0.0)            # towards the other (attraction)

    def test_repulsion_has_priority(self):
        m = placed(3, [(0.0, 0.0, 0.0), (0.5, 0.0, 0.0), (0.0, 5.0, 0.0)], [(0.0, 0.0, 1.0)] * 3, ro=1.5, ra=10.0)
        self.assertEqual(m.desired(0), [-1.0, 0.0, 0.0])

    def test_blind_cone(self):
        # a neighbour straight behind is not seen; one at 130 degrees from the heading is
        m = placed(2, [(0.0, 0.0, 0.0), (-5.0, 0.0, 0.0)], [(1.0, 0.0, 0.0), (0.0, 0.0, 1.0)], ro=1.5, ra=10.0)
        self.assertEqual(m.desired(0), [1.0, 0.0, 0.0])
        a = math.radians(130.0)
        m = placed(2, [(0.0, 0.0, 0.0), (5.0 * math.cos(a), 5.0 * math.sin(a), 0.0)],
                   [(1.0, 0.0, 0.0), (0.0, 0.0, 1.0)], ro=1.5, ra=10.0)
        d = m.desired(0)
        self.assertAlmostEqual(d[0], math.cos(a), delta=1e-12)
        # with alpha = 360 the one behind is seen
        m = placed(2, [(0.0, 0.0, 0.0), (-5.0, 0.0, 0.0)], [(1.0, 0.0, 0.0), (0.0, 0.0, 1.0)], ro=1.5, ra=10.0,
                   alpha=360.0)
        self.assertEqual(m.desired(0), [-1.0, 0.0, 0.0])

    def test_readings_of_the_average(self):
        # focal heading z; one neighbour in the zone of orientation heading y; three in the zone of attraction along x
        cs = [(0.0, 0.0, 0.0), (1.2, 0.0, 0.0), (4.0, 0.1, 0.0), (4.0, -0.1, 0.0), (4.0, 0.0, 0.1)]
        vs = [(0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (0.0, 0.0, 1.0), (0.0, 0.0, 1.0)]
        raw = placed(5, cs, vs, ro=1.5, ra=10.0, reading=(0, 0, 1)).desired(0)
        unitv = placed(5, cs, vs, ro=1.5, ra=10.0, reading=(0, 1, 1)).desired(0)
        selfin = placed(5, cs, vs, ro=1.5, ra=10.0, reading=(1, 0, 1)).desired(0)
        self.assertGreater(raw[0] / raw[1], 2.5)       # three attraction vectors outweigh one heading
        self.assertAlmostEqual(unitv[0] / unitv[1], 1.0, delta=0.01)
        self.assertGreater(selfin[2], 0.2)             # the focal heading is in d_o
        self.assertAlmostEqual(raw[2], 0.0, delta=0.05)

    def test_zero_vector_keeps_heading(self):
        # two attraction neighbours exactly opposite: d_a = 0, so the heading is kept
        m = placed(3, [(0.0, 0.0, 0.0), (0.0, 4.0, 0.0), (0.0, -4.0, 0.0)], [(1.0, 0.0, 0.0)] * 3, ro=1.5, ra=10.0)
        self.assertEqual(m.desired(0), [1.0, 0.0, 0.0])


class Measures(unittest.TestCase):
    def test_ring_and_file(self):
        n = 37
        c = [[3.0 * math.cos(2 * math.pi * i / n), 3.0 * math.sin(2 * math.pi * i / n), 1.0] for i in range(n)]
        v = [[-math.sin(2 * math.pi * i / n), math.cos(2 * math.pi * i / n), 0.0] for i in range(n)]
        p, m = M.measures(c, v)
        self.assertAlmostEqual(m, 1.0, delta=1e-12)
        self.assertLess(p, 1e-12)
        p, m = M.measures([[0.0, 0.0, float(i)] for i in range(20)], [[0.0, 0.0, 1.0]] * 20)
        self.assertAlmostEqual(p, 1.0, delta=1e-12)
        self.assertLess(m, 1e-12)

    def test_classes(self):
        cos_half = M.dsincos(M.ALPHA / 2.0 * M.PI / 180.0)[1]
        c = [[0.0, 0.0, 0.0], [0.5, 0.0, 0.0], [50.0, 0.0, 0.0], [50.0, 0.5, 0.0], [0.0, 80.0, 0.0]]
        v = [[1.0, 0.0, 0.0]] * 5
        self.assertEqual(M.classes(c, v, [1.0] * 5, 10.0, cos_half), 3)
        # a chain within r_a joins all, even with everyone heading the same way (each sees the one ahead)
        c = [[3.0 * i, 0.0, 0.0] for i in range(6)]
        self.assertEqual(M.classes(c, [[1.0, 0.0, 0.0]] * 6, [1.0] * 6, 4.0, cos_half), 1)


class Decision(unittest.TestCase):
    def synthetic(self, mem=True):
        up = {}
        for k in range(M.N_UP):
            ro = M.ro_value(k)
            if ro < 1.4:
                up[k] = (0.2, 0.3, 15)
            elif ro <= 2.6:
                up[k] = (0.25, 0.9, 15)
            else:
                up[k] = (0.9, 0.1, 15)
        down = {}
        for k in range(M.N_UP - 1):
            ro = M.ro_value(k)
            down[k] = (0.9, 0.1, 15) if (ro >= 1.4 and mem) else up[k]
        return {"up": up, "down": down}

    def test_memory_and_none(self):
        self.assertEqual(M.decide(self.synthetic())[0], 15)
        met, cond = M.decide(self.synthetic(mem=False))
        self.assertLess(met, 15)
        self.assertFalse(cond["falling p >= 0.7 at 2.0"])

    def test_fragmented_values_fail(self):
        cv = self.synthetic()
        k = M.k_of(2.0)
        cv["up"][k] = (0.25, 0.9, 7)
        met, cond = M.decide(cv)
        self.assertEqual(met, 13)
        self.assertFalse(cond["rising m >= 0.6 at 2.0"])

    def test_thresholds_inclusive(self):
        cv = self.synthetic()
        k = M.k_of(1.75)
        cv["up"][k] = (0.4, 0.6, 15)
        cv["down"][k] = (0.7, 0.3, 15)
        self.assertEqual(M.decide(cv)[0], 15)

    def test_figure_values(self):
        self.assertEqual(M.decide(M.figure_curves())[0], 15)

    def test_grid_of_values(self):
        self.assertEqual([M.ro_value(k) for k in (0, 3, 12)], [1.0, 1.75, 4.0])
        self.assertEqual(M.k_of(2.25), 5)
        with self.assertRaises(ValueError):
            M.k_of(2.1)


class Statistics(unittest.TestCase):
    def test_spearman(self):
        self.assertAlmostEqual(M.spearman([1, 2, 3, 4, 5], [2, 1, 4, 3, 5]), 0.8, delta=1e-12)
        self.assertAlmostEqual(M.spearman([1, 2, 3], [3, 2, 1]), -1.0, delta=1e-12)
        self.assertAlmostEqual(M.spearman([1, 2, 2, 3], [1, 2, 3, 4]), 0.9486832980505138, delta=1e-12)

    def test_sorting_rho(self):
        inds = [(float(i), 1.0, float(i), 0.0, 0.0, 1.0, 0.0, 0.0) for i in range(9)]
        front, centre = M.sorting_rho(inds, "speed")
        self.assertAlmostEqual(front, 1.0, delta=1e-12)
        self.assertLess(abs(centre), 0.5)

    def test_expected_noise(self):
        rng = random.Random(11)
        cap = math.radians(4.0)
        for z in (1, 2):
            (es, ss), (ec, sc) = M.expected_noise(z)
            xs = []
            for _ in range(40000):
                a = abs(rng.gauss(0, M.SIGMA)) if z == 1 else M.SIGMA * math.hypot(rng.gauss(0, 1), rng.gauss(0, 1))
                xs.append(min(a, cap))
            ms = sum(math.sin(a) for a in xs) / len(xs)
            mc = sum(1 - math.cos(a) for a in xs) / len(xs)
            self.assertLess(abs(ms - es), 5 * ss / math.sqrt(len(xs)))
            self.assertLess(abs(mc - ec), 5 * sc / math.sqrt(len(xs)))


@unittest.skipIf(shutil.which("gcc") is None, "needs gcc")
class Program(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp()
        cls.exe = M.build(cls.work)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def test_c_against_python(self):
        for t, (reading, vary, sd) in enumerate((((0, 0, 1), 0, 0.0), ((1, 1, 2), 0, 0.0), ((0, 1, 1), 1, 0.3),
                                                  ((1, 0, 2), 2, 0.2))):
            params = M.base_params(reading, 100 + t, N=8, ra=5.0, ro=1.5, r0=2.0, steps=80, vary=vary, vary_sd=sd)
            rc = M.c_run(self.exe, self.work, params, "trace", f"t{t}")
            m = M.Model(8, 100 + t, ro=1.5, ra=5.0, r0=2.0, reading=reading, vary=vary, vary_sd=sd)
            self.assertEqual(rc["t0"], [tuple(m.c[i] + m.v[i]) for i in range(8)])
            for _ in range(80):
                m.step()
            self.assertEqual(rc["t1"], [tuple(m.c[i] + m.v[i]) for i in range(8)])
            p, mm = m.measures()
            self.assertEqual(rc["pm"], (p, mm, m.classes()))

    def test_noise_mode(self):
        for z in (1, 2):
            rn = M.c_run(self.exe, self.work, M.base_params((0, 0, z), 77, steps=30000), "noise", f"n{z}")
            msin, mcos, n = rn["noise"]
            (es, ss), (ec, sc) = M.expected_noise(z)
            self.assertLess(abs(msin - es), 5 * ss / math.sqrt(n))
            self.assertLess(abs(mcos - ec), 5 * sc / math.sqrt(n))

    def test_sweep_output_shape(self):
        # a small group on another sweep: 3 values up, 2 down, 50 steps each
        p = M.base_params((0, 0, 1), 5, N=10, ra=6.0, r0=2.0, ro_lo=1.0, ro_step=0.5, n_up=3, steps_per=50, window=20)
        r = M.c_run(self.exe, self.work, p, "sweep", "sw")
        self.assertEqual(sorted(r["up"]), [0, 1, 2])
        self.assertEqual(sorted(r["down"]), [0, 1])
        self.assertEqual([r["up"][k]["ro"] for k in range(3)], [1.0, 1.5, 2.0])
        self.assertTrue(all(0.0 <= x["p"] <= 1.0 and 0.0 <= x["m"] <= 1.0 for x in r["up"].values()))


class Run(unittest.TestCase):
    def test_bad_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


if __name__ == "__main__":
    unittest.main()
