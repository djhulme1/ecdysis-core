"""Yuan et al. 2012's maturation and lifespan check (itp/yuan2012.py): the readers, the Kaplan-Meier areas and medians,
the regression and its P, the IGF1 means, the two conditions and a whole run, on small files and curves made here
whose answers are worked by hand. None of the deposited files is read.

Run with: python3 -m unittest tests.test_yuan2012
"""

import importlib.util
import math
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_yuan2012", os.path.join(HERE, "..", "itp", "yuan2012.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)


def csv_bytes(header, rows):
    return ("\n".join([",".join(header)] + [",".join(str(v) for v in r) for r in rows]) + "\n").encode("utf-8")


class Reading(unittest.TestCase):
    def test_lifespans_and_names(self):
        data = csv_bytes(M.HEADER_LIFE, [("BTBR T+ tf/J", "f", 1, 0, 600), ("A/J", "m", "x2", 1, 455)])
        self.assertEqual(M.read_lifespans(data), [("BTBR T<+> Itpr3<tf>/J", "f", 600, True), ("A/J", "m", 455, False)])

    def test_refusals(self):
        bad = [csv_bytes(["strain", "sex", "id", "censor", "lifespan"], [("A/J", "f", 1, 0, 600)]),
               csv_bytes(M.HEADER_LIFE, [("A/J", "x", 1, 0, 600)]),
               csv_bytes(M.HEADER_LIFE, [("A/J", "f", 1, 2, 600)]),
               csv_bytes(M.HEADER_LIFE, [("A/J", "f", 1, 0, "600.5")])]
        for b in bad:
            with self.assertRaises(M.Refused):
                M.read_lifespans(b)
        with self.assertRaises(M.Refused):
            M.read_vp(csv_bytes(M.HEADER_VP, [("A/J", "m", "m1", 30)]))
        with self.assertRaises(M.Refused):
            M.read_igf1(csv_bytes(M.HEADER_IGF1, [("A/J", "f", "a", "3e2", "", "", "", "", "")]))

    def test_vp_and_igf1(self):
        self.assertEqual(M.read_vp(csv_bytes(M.HEADER_VP, [("A/J", "f", "f1", 31)])), [("A/J", 31)])
        got = M.read_igf1(csv_bytes(M.HEADER_IGF1, [("A/J", "f", "a", "250.5", "", "300", "22.1", "", ""),
                                                    ("A/J", "m", "b", "", "310", "", "", "", "")]))
        self.assertEqual(got, [("A/J", "f", 250.5), ("A/J", "m", None)])


class KaplanMeier(unittest.TestCase):
    def test_no_censoring_is_the_mean(self):
        obs = [(2, True), (4, True), (6, True)]
        self.assertAlmostEqual(M.km_area(obs), 4.0, places=12)
        self.assertEqual(M.km_median(obs), 4)

    def test_censoring_by_hand(self):
        # t=2: 4 at risk, a death, S = 3/4; t=3 censored; t=5: 2 at risk, a death, S = 3/8; t=8 censored
        obs = [(2, True), (3, False), (5, True), (8, False)]
        self.assertAlmostEqual(M.km_area(obs, "observed"), 2 + 0.75 * 3 + 0.375 * 3, places=12)
        self.assertAlmostEqual(M.km_area(obs, "death"), 2 + 0.75 * 3, places=12)
        for end in ("observed", "death"):
            self.assertAlmostEqual(M.km_area_jumps(obs, end), M.km_area(obs, end), places=12)
        self.assertEqual(M.km_median(obs), 5)

    def test_median_at_exactly_one_half(self):
        # 30 deaths at days 1..30: S is exactly 1/2 after the 15th, which floating point may not reach
        self.assertEqual(M.km_median([(t, True) for t in range(1, 31)]), 15)

    def test_tie_death_before_censoring(self):
        obs = [(5, True), (5, False), (7, True)]
        steps = M.km_steps(obs)
        self.assertEqual([(t, d, c, n) for t, d, c, n, s in steps], [(5, 1, 1, 3), (7, 1, 0, 1)])
        self.assertAlmostEqual(steps[0][4], 2 / 3, places=15)
        self.assertAlmostEqual(M.km_area(obs), 5 + (2 / 3) * 2, places=12)
        self.assertEqual(M.km_median(obs), 7)

    def test_against_scipy(self):
        obs = [(300, True), (410, False), (410, True), (520, True), (600, False), (700, True), (800, False)]
        s_sc, med, area = M.scipy_km(obs)
        mine = {t: s for t, d, c, n, s in M.km_steps(obs) if d}
        self.assertEqual(set(s_sc), set(mine))
        for t in mine:
            self.assertAlmostEqual(s_sc[t], mine[t], places=12)
        self.assertEqual(med, M.km_median(obs))
        self.assertAlmostEqual(area, M.km_area(obs), places=9)


class Statistics(unittest.TestCase):
    def test_regression_by_hand(self):
        r = M.plain_regress([1, 2, 3, 4], [2, 4, 5, 8])
        self.assertAlmostEqual(r["slope"], 1.9, places=12)
        self.assertAlmostEqual(r["intercept"], 4.75 - 1.9 * 2.5, places=12)
        self.assertAlmostEqual(r["r"], 9.5 / math.sqrt(5 * 18.75), places=12)
        t = r["r"] * math.sqrt(2 / (1 - r["r"] ** 2))
        self.assertAlmostEqual(r["p"], 2 * (0.5 - 0.5 * t / math.sqrt(2 + t * t)), places=10)   # t with 2 df, exactly

    def test_known_quantiles(self):
        # two-sided 5% points of Student's t: 12.7062 at 1 df, 2.228139 at 10 df
        self.assertAlmostEqual(M.betainc(0.5, 0.5, 1 / (1 + 12.706205 ** 2)), 0.05, places=6)
        self.assertAlmostEqual(M.betainc(5, 0.5, 10 / (10 + 2.228139 ** 2)), 0.05, places=6)

    def test_against_scipy(self):
        x, y = [25.1, 30.3, 31.0, 40.2, 28.8, 35.5], [700, 650, 800, 820, 610, 790]
        mine, sc = M.plain_regress(x, y), M.scipy_regress(x, y)
        self.assertAlmostEqual(mine["slope"], sc["slope"], places=9)
        self.assertAlmostEqual(mine["p"], sc["p"], places=9)

    def test_igf1_means_and_outliers(self):
        rows = [("S", "f", 100.0)] * 7 + [("S", "f", 300.0), ("S", "m", 200.0), ("S", "f", None)]
        self.assertAlmostEqual(M.igf1_means(rows, "f")["S"], 125.0)
        self.assertAlmostEqual(M.igf1_means(rows, "f", z_out=True)["S"], 100.0)   # z of 300 is 175/70.7 > 2
        self.assertEqual(M.igf1_means(rows, "m"), {"S": 200.0})


class Conditions(unittest.TestCase):
    def test_cutoff_and_signs(self):
        vp = {"a": 25.0, "b": 28.0, "c": 31.0, "d": 34.0, "e": 37.0, "f": 26.0}
        life = {"a": 640.0, "b": 700.0, "c": 731.0, "d": 790.0, "e": 845.0, "f": 450.0}
        c = M.condition_i(life, vp, sorted(vp))
        self.assertEqual((c["kept"], c["removed"]), (5, 1))                    # f is below 600 days
        self.assertTrue(c["holds"])
        self.assertFalse(M.condition_i({k: 1500 - v for k, v in life.items()}, vp, sorted(vp))["holds"])
        igf = {"a": 420.0, "b": 380.0, "c": 361.0, "d": 300.0, "e": 280.0, "f": 400.0}
        self.assertTrue(M.condition_ii(igf, vp, sorted(vp))["holds"])
        self.assertFalse(M.condition_ii({k: 700 - v for k, v in igf.items()}, vp, sorted(vp))["holds"])

    def test_planted(self):
        self.assertTrue(M.planted_ok())


def made_up_files():
    """A small made-up study shaped like the deposits: strains whose lifespans rise and IGF1 falls with VP."""
    life, vp, igf = [], [], []
    named = ["DBA/2J", "CAST/EiJ", "MOLF/EiJ", "PWD/PhJ", "WSB/EiJ", "BTBR T+ tf/J", "NZO/HlLtJ"]
    strains = named + [f"S{i}/J" for i in range(9)]
    for k, s in enumerate(strains):
        base_vp = 24 + k
        mapped = M.NAME_MAP.get(s, s)
        for j in range(6):
            days = 560 + 25 * k + 15 * j
            life.append((s, "f", f"{k}f{j}", 1 if j == 5 and k % 3 == 0 else 0, days))
            if s not in ("CAST/EiJ", "MOLF/EiJ"):
                life.append((s, "m", f"{k}m{j}", 0, days + 10))
            if s != "NZO/HlLtJ":
                vp.append((mapped, "f", f"{k}v{j}", base_vp + (j % 3)))
            igf.append((mapped, "f", f"{k}i{j}", f"{430 - 5 * k + j}.5", "", "", "", "", ""))
            igf.append((mapped, "m", f"{k}j{j}", f"{400 - 4 * k + j}", "", "", "", "", ""))
    for j in range(5):                                                         # AKR/J: VP and IGF1, no lifespans
        vp.append(("AKR/J", "f", f"av{j}", 26 + j % 2))
        igf.append(("AKR/J", "f", f"ai{j}", "390", "", "", "", "", ""))
    return (csv_bytes(M.HEADER_LIFE, life), csv_bytes(M.HEADER_VP, vp), csv_bytes(M.HEADER_IGF1, igf))


class WholeRun(unittest.TestCase):
    def test_made_up_study(self):
        a, b, c = made_up_files()
        out, detail = M.assess(M.read_lifespans(a), M.read_vp(b), M.read_igf1(c))
        self.assertEqual(list(out), list(M.OUTPUTS))
        self.assertEqual(out["strains_vp_lifespan"], 15)                       # 16 strains with lifespans, NZO no VP
        self.assertEqual(out["conditions_met"], 2)
        self.assertEqual(out["test_passed"], 1)
        for k, v in out.items():
            self.assertTrue(isinstance(v, (int, float, str)), k)
            if isinstance(v, str):
                self.assertLessEqual(len(v), 200, k)
            elif isinstance(v, float):
                self.assertTrue(math.isfinite(v), k)
        ctl = detail["controls"]
        names = list(ctl)
        self.assertTrue(ctl[names[0]] and ctl[names[1]] and ctl[names[3]])      # scipy, Kaplan-Meier, planted
        self.assertFalse(ctl[names[2]])                                        # the made-up files are not the deposit
        self.assertIn("AKR/J", detail["panel"])
        self.assertNotIn("AKR/J", detail["vp_life"])


if __name__ == "__main__":
    unittest.main()
