"""METR's developer-productivity trial (metr/becker2025.py) on data written here, never the trial's: the CSV reader and
its refusals, the macros and printed-run parsers, the imputations, least squares and its three standard errors against
statsmodels and exact arithmetic, the swap and shift identities, the seeded draws and the rounding of printed values.

Run with: python3 -m unittest discover -s tests -p test_becker2025.py (in the pinned scipy-notebook image)
"""

import importlib.util
import math
import os
import random
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("metr_becker2025", os.path.join(HERE, "..", "metr", "becker2025.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

HEADER = ",".join(M.COLUMNS)


def synthetic(n=60, devs=5, seed=1, beta=0.2, blanks=6):
    rng = random.Random(seed)
    lines = [HEADER]
    for i in range(1, n + 1):
        d = 100 + i % devs
        f0 = rng.choice([30, 60, 90, 120, 240])
        f1 = f0 * rng.choice([0.5, 0.75, 1.0])
        ai = rng.randint(0, 1)
        t = math.exp(math.log(f0) + beta * ai + rng.gauss(0, 0.5))
        post = "" if i <= blanks else str(float(rng.choice([0, 0, 5, 10, 30])))
        exp = "" if i % 3 == 0 else str(float(rng.randint(1, 5)))
        res = "" if i % 3 == 0 else str(float(rng.randint(1, 3)))
        lines.append(f"{d},{i},{float(f0)},{float(f1)},{exp},{res},{float(ai)},{t:.3f},{post}")
    return ("\n".join(lines) + "\n").encode()


class Reader(unittest.TestCase):
    def test_reads(self):
        rows = M.read_data(synthetic())
        self.assertEqual(len(rows), 60)
        self.assertEqual(sum(r["post"] is None for r in rows), 6)
        self.assertTrue(all(r["ai"] in (0, 1) for r in rows))

    def test_beside_columns_out_of_range_are_read(self):
        lines = synthetic().decode().split("\n")
        cells = lines[2].split(","); cells[5] = "5.0"; lines[2] = ",".join(cells)
        rows = M.read_data("\n".join(lines).encode())
        self.assertEqual(rows[1]["resources"], 5)

    def test_refusals(self):
        good = synthetic().decode().split("\n")
        cases = []
        cases.append(["dev,issue"] + good[1:])                                   # header
        bad = list(good); bad[2] = bad[2].replace(",2,", ",1,", 1); cases.append(bad)   # issue id twice
        bad = list(good); cells = bad[3].split(","); cells[6] = "2.0"; bad[3] = ",".join(cells); cases.append(bad)
        bad = list(good); cells = bad[4].split(","); cells[7] = "-3"; bad[4] = ",".join(cells); cases.append(bad)
        bad = list(good); cells = bad[5].split(","); cells[4] = "2.5"; bad[5] = ",".join(cells); cases.append(bad)
        bad = list(good); cells = bad[6].split(","); cells[2] = "soon"; bad[6] = ",".join(cells); cases.append(bad)
        bad = list(good); cells = bad[7].split(","); cells[7] = ""; bad[7] = ",".join(cells); cases.append(bad)
        for lines in cases:
            with self.assertRaises(M.Refused):
                M.read_data("\n".join(lines).encode())


class Parsers(unittest.TestCase):
    def test_macros(self):
        tex = r"\newcommand{\PctSpeedupBaseline}{19}" "\n" r"\newcommand{\MeanRepoNumCodeFiles}{8,300}" "\n" \
              r"\newcommand{\CorrX}{0.59}"
        m = M.parse_macros(tex)
        self.assertEqual(M.macro_number(m, "PctSpeedupBaseline"), 19)
        self.assertEqual(M.macro_number(m, "MeanRepoNumCodeFiles"), 8300)
        self.assertEqual(M.decimals_of(m["CorrX"]), 2)
        with self.assertRaises(M.Refused):
            M.macro_number(m, "Missing")

    def test_printed_run(self):
        text = ("Regression calculated speedup of:          0.188\n"
                "CI calculed with stderr=Homoskedastic:      (0.013, 0.395)\n"
                "CI calculed with stderr=Robust (HC3):       (0.013, 0.394)\n"
                "CI calculed with stderr=Clustered By Dev:   (0.016, 0.39)\n")
        p = M.parse_printed_run(text)
        self.assertEqual(p["speedup"], 0.188)
        self.assertEqual(p["Clustered By Dev"], (0.016, 0.39))
        self.assertIsNone(M.parse_printed_run("nothing")["speedup"])

    def test_half_up(self):
        self.assertEqual(M.half_up(18.5, 0), 19)
        self.assertEqual(M.half_up(-24.5, 0), -24)
        self.assertEqual(M.half_up(0.585, 2), 0.59)
        self.assertEqual(M.pct(0.188), 19)


class Estimator(unittest.TestCase):
    def test_impute(self):
        rows = M.read_data(synthetic())
        seen = [r for r in rows if r["post"] is not None]
        arm = M.impute(rows, "arm")
        for r, v in zip(rows, arm):
            if r["post"] is None:
                self.assertAlmostEqual(v, np.mean([s["post"] for s in seen if s["ai"] == r["ai"]]))
        self.assertEqual(sum(M.impute(rows, "zero")), sum(s["post"] for s in seen))
        hour = M.impute(rows, "hour_ai")
        self.assertTrue(all(v == (60.0 if r["ai"] else 0.0) for r, v in zip(rows, hour) if r["post"] is None))

    def test_noiseless_recovers_beta(self):
        rng = np.random.default_rng(3)
        X = np.column_stack([np.ones(40), rng.integers(0, 2, 40), rng.normal(size=40)])
        y = X @ np.array([0.3, 0.2, 0.9])
        b, _ = M.ols(y, X)
        self.assertTrue(np.allclose(b, [0.3, 0.2, 0.9], atol=1e-12))

    def test_standard_errors_against_statsmodels(self):
        try:
            import statsmodels.api as sm
        except ImportError:
            self.skipTest("statsmodels not installed")
        rng = np.random.default_rng(5)
        n = 80
        groups = rng.integers(0, 7, n)
        X = np.column_stack([np.ones(n), rng.integers(0, 2, n), rng.normal(size=n)])
        y = X @ np.array([1.0, 0.3, 0.5]) + rng.normal(scale=0.4, size=n) * (1 + X[:, 1])
        b, se = M.ols(y, X, groups=groups)
        for name, kw in (("nonrobust", {}), ("hc3", {"cov_type": "HC3"}),
                         ("cluster", {"cov_type": "cluster", "cov_kwds": {"groups": groups}})):
            res = sm.OLS(y, X).fit(**kw)
            self.assertTrue(np.allclose(res.params, b, rtol=1e-12))
            self.assertTrue(np.allclose(res.bse, se[name], rtol=1e-9), name)

    def test_exact_beta(self):
        rng = np.random.default_rng(7)
        X = np.column_stack([np.ones(15), rng.integers(0, 2, 15), rng.normal(size=15)])
        y = rng.normal(size=15)
        b, _ = M.ols(y, X)
        ex = M.exact_beta(y, X)
        self.assertTrue(all(abs(float(e) - v) < 1e-12 for e, v in zip(ex, b)))

    def test_effect_and_identities(self):
        rows = M.read_data(synthetic(n=120, beta=0.3))
        total = M.total_time(rows)
        est = M.effect(rows, total)
        self.assertAlmostEqual(est["s"], math.exp(est["beta"]) - 1)
        for se in ("nonrobust", "hc3", "cluster"):
            lo, hi = est[f"ci_{se}"]
            self.assertLess(lo, est["s"])
            self.assertGreater(hi, est["s"])
        y, X = M.design(rows, total)
        Xs = X.copy()
        Xs[:, 1] = 1 - Xs[:, 1]
        bs, _ = M.ols(y, Xs)
        self.assertLess(abs(bs[1] + est["beta"]), 1e-12)
        bshift, _ = M.ols(y + math.log(1.5) * X[:, 1], X)
        self.assertLess(abs(bshift[1] - est["beta"] - math.log(1.5)), 1e-12)
        fe = M.effect(rows, total, fixed_effects=True)
        self.assertEqual(fe["n"], 120)


class Draws(unittest.TestCase):
    def test_stream_deterministic(self):
        a = M.Stream("0" * 64, "x").rng().integers(0, 1000, 5).tolist()
        b = M.Stream("0" * 64, "x").rng().integers(0, 1000, 5).tolist()
        c = M.Stream("1" * 64, "x").rng().integers(0, 1000, 5).tolist()
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_bootstraps_and_permutations(self):
        rows = M.read_data(synthetic(n=90))
        total = M.total_time(rows)
        ai = np.asarray([r["ai"] for r in rows])
        lo, hi = M.pooled_bootstrap(total, ai, 300, M.Stream("0" * 64, "r").rng())
        self.assertLess(lo, M.ratio_of_means(total, ai))
        self.assertGreater(hi, M.ratio_of_means(total, ai))
        tlo, thi, n = M.two_stage(rows, total, 100, M.Stream("0" * 64, "t").rng())
        self.assertLess(tlo, thi)
        self.assertGreater(n, 90)
        perm = M.permutation_betas(rows, total, 50, M.Stream("0" * 64, "p").rng())
        self.assertEqual(perm.shape, (50,))
        self.assertTrue(np.all(np.isfinite(perm)))

    def test_bad_seed(self):
        with self.assertRaises(M.Refused):
            M.run("nope")


if __name__ == "__main__":
    unittest.main()
