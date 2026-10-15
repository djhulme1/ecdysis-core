"""Liao et al.'s DR counts (itp/liao2010.py): the reader, the plain statistics against scipy's, the strain
classification and the whole assessment, on panels of mice made here. The deposit's lifespans are never read.

Run with: python3 -m unittest tests.test_liao2010 (in the pinned scipy-notebook image)
"""

import hashlib
import importlib.util
import os
import random
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_liao2010", os.path.join(HERE, "..", "itp", "liao2010.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "7e" * 32


def csv_bytes(mice, header=None):
    lines = [",".join(header or M.HEADER)]
    for i, (strain, sex, diet, days) in enumerate(mice):
        row = [strain, sex, f"id{i}"] + [""] * 8 + ([str(days), ""] if diet == "AL" else ["", str(days)])
        lines.append(",".join(row))
    return ("\n".join(lines) + "\n").encode()


def panel(seed, n_strains=12, effects=None):
    """Mice of n strains, 5 per sex and diet; effects[i] days added to strain i's DR mice (default none)."""
    rng = random.Random(seed)
    mice = []
    for i in range(n_strains):
        base = rng.randint(500, 1100)
        shift = (effects or {}).get(i, 0)
        for sex in ("m", "f"):
            for _ in range(5):
                mice.append((f"S{i}", sex, "AL", max(30, int(rng.gauss(base, 80)))))
                mice.append((f"S{i}", sex, "DR", max(30, int(rng.gauss(base + shift, 80)))))
    return mice


class Reader(unittest.TestCase):
    def test_reads_and_refuses(self):
        mice = [("A", "m", "AL", 700), ("A", "f", "DR", 812)]
        self.assertEqual(M.read_mice(csv_bytes(mice)), mice)
        with self.assertRaises(M.Refused):
            M.read_mice(csv_bytes(mice, header=M.HEADER[:-1] + ["life_DR"]))
        both = csv_bytes(mice).replace(b",700,", b",700,701", 1)
        with self.assertRaises(M.Refused):
            M.read_mice(both)
        neither = csv_bytes(mice).replace(b",700,", b",,", 1)
        with self.assertRaises(M.Refused):
            M.read_mice(neither)
        with self.assertRaises(M.Refused):
            M.read_mice(csv_bytes([("A", "m", "AL", 700)]).replace(b"700", b"70.5"))
        with self.assertRaises(M.Refused):
            M.read_mice(csv_bytes([("A", "x", "AL", 700)]))

    def test_groups_and_early_cut(self):
        mice = [("A", "m", "AL", 300), ("A", "m", "AL", 900), ("A", "m", "DR", 400), ("B", "f", "DR", 1000)]
        g = M.groups(mice)
        self.assertEqual(g[("A", "m")], {"AL": [300, 900], "DR": [400]})
        g = M.groups(mice, min_days=365)
        self.assertEqual(g[("A", "m")], {"AL": [900], "DR": [400]})


class Statistics(unittest.TestCase):
    def test_ttests_against_scipy(self):
        rng = random.Random(3)
        for _ in range(40):
            a = [rng.gauss(700, 150) for _ in range(rng.randint(2, 15))]
            b = [rng.gauss(650, 220) for _ in range(rng.randint(2, 15))]
            for eq in (True, False):
                pt, pp = M.plain_ttest(a, b, eq)
                st, sp = M.scipy_ttest(a, b, eq)
                self.assertTrue(M.close(pt, st) and M.close(pp, sp), (pt, st, pp, sp))

    def test_pearson_and_anova_against_scipy(self):
        rng = random.Random(4)
        for _ in range(20):
            n = rng.randint(4, 40)
            x = [rng.gauss(0, 1) for _ in range(n)]
            y = [v * rng.uniform(-1, 1) + rng.gauss(0, 1) for v in x]
            pr, sr = M.plain_pearson(x, y), M.scipy_pearson(x, y)
            self.assertTrue(M.close(pr[0], sr[0]) and M.close(pr[1], sr[1], 1e-7), (pr, sr))
            samples = [[rng.gauss(k, 1) for _ in range(rng.randint(2, 6))] for k in range(rng.randint(2, 8))]
            pa, sa = M.plain_anova(samples), M.scipy_anova(samples)
            self.assertTrue(M.close(pa[0], sa[0]) and M.close(pa[1], sa[1], 1e-7), (pa, sa))

    def test_known_t(self):
        # two groups of two with known pooled t: means 1.5 and 3.5, pooled variance 0.5, se 0.70710678
        t, p = M.plain_ttest([1, 2], [3, 4])
        self.assertAlmostEqual(t, -2.0 / (0.5 ** 0.5), places=12)
        self.assertAlmostEqual(p, 1 - 8 ** 0.5 / 10 ** 0.5, places=12)    # two-sided, 2 df: 1 - |t|/sqrt(t^2 + 2)


class Classification(unittest.TestCase):
    def test_planted_effects(self):
        effects = {0: -400, 1: -400, 2: -400, 3: 400}               # three strains shortened, one lengthened
        g = M.groups(panel(5, 12, effects))
        c = M.classify(g)
        for sex in ("m", "f"):
            v = {r["strain"]: r["verdict"] for r in c[sex]["rows"]}
            self.assertEqual(c[sex]["strains"], 12)
            for i in (0, 1, 2):
                self.assertEqual(v[f"S{i}"], "shortened")
            self.assertEqual(v["S3"], "lengthened")
        pooled = M.classify(g, pooled=True)["both"]
        self.assertEqual(pooled["strains"], 12)
        self.assertGreaterEqual(pooled["shortened"], 3)

    def test_small_groups_left_out(self):
        mice = panel(6, 3) + [("T", "m", "AL", 800), ("T", "m", "DR", 500), ("T", "m", "DR", 520)]
        c = M.classify(M.groups(mice))
        self.assertEqual(c["m"]["strains"], 3)
        self.assertEqual(c["f"]["strains"], 3)

    def test_assessment_on_a_made_panel(self):
        mice = panel(8, 20, {0: -450, 1: -420, 2: -390, 5: 380})
        out, detail = M.assess(mice)
        self.assertEqual(sorted(out), sorted(M.OUTPUTS))
        self.assertEqual((out["strains_m"], out["strains_f"]), (20, 20))
        self.assertGreaterEqual(out["m_shortened"], 3)
        self.assertEqual(out["test_passed"], int(out["m_shortened"] > out["m_lengthened"]
                                                 and out["f_shortened"] > out["f_lengthened"]))
        self.assertTrue(all(len(v) <= 200 for v in out.values() if isinstance(v, str)))
        # the file-shape control fails on a made panel (it is not the deposit); the others hold
        self.assertEqual(out["controls_passed"], out["controls_total"] - 1)
        mice = panel(9, 20, {0: 450, 1: 420, 2: 390, 5: -380})
        out, _ = M.assess(mice)
        self.assertEqual(out["test_passed"], 0)


class WholeRun(unittest.TestCase):
    def test_refusals(self):
        with self.assertRaises(M.Refused):
            M.run("xyz")
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, M.INPUT[0]), "wb") as f:
                f.write(csv_bytes(panel(1, 2)))
            with self.assertRaises(M.Refused):
                M.run(SEED, inputs=tmp, results=os.path.join(tmp, "out"))

    def test_constants(self):
        self.assertLessEqual(len(M.TEST), 600)
        self.assertEqual(M.INPUT, ("Nelson1_animaldata.csv",
                                   "a3d57bfd20502b51e7a95c1839c0881e18b8e02e23450459430cda4dadc53da3", 42453))
        self.assertEqual((M.ALPHA, M.MIN_PER_GROUP, M.EARLY_DAYS), (0.05, 2, 365))
        self.assertEqual(len(set(M.OUTPUTS)), len(M.OUTPUTS))
        self.assertLessEqual(len(M.OUTPUTS), 64)


if __name__ == "__main__":
    unittest.main()
