"""Colombatto & Fleming's folk attributions (folk/colombatto.py): the file reader and its refusals; the authors' usage
coding; least squares, cor.test and Welch against known answers; R's poly against R's own printed basis; the quadratic
fit against a direct one; the PCA's imputation and orientation; the known-answer controls; the seed refused; and,
with the authors' Data.csv at inputs/ (or FOLK_INPUTS), the file's structure (rows, states, missing ratings, the
sample's counts as the paper prints them), which computes none of the test's statistics.

Needs numpy and scipy (the pinned scipy-notebook image). Run with: python3 -m unittest tests.test_colombatto
"""

import importlib.util
import math
import os
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("folk_colombatto", os.path.join(HERE, "..", "folk", "colombatto.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)
INPUTS = os.environ.get("FOLK_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = all(os.path.isfile(os.path.join(INPUTS, name)) for name, _ in M.INPUTS.values())
TRAIT_NAMES = [f"state {k}" for k in range(M.TRAITS)]


def csv_text(n=M.N, mutate=None):
    head = list(M.HEAD) + TRAIT_NAMES
    lines = [",".join(head)]
    for i in range(n):
        row = [str(i + 1), str(1 + i % 100), "12.5", "50", "40", "Yes", "Yes" if i % 2 else "No",
               "About once a week" if i % 2 else "", "\"Writing,Other\"", "40", "Female"]
        row += [str(1 + (i * 7 + k) % 100) for k in range(M.TRAITS)]
        if mutate:
            row = mutate(i, row)
        lines.append(",".join(row))
    return "\n".join(lines) + "\n"


class Reader(unittest.TestCase):
    def test_reads(self):
        d = M.read_data(csv_text())
        self.assertEqual(d["X"].shape, (M.N, M.TRAITS))
        self.assertEqual(d["use"][:2], ["No", "Yes"])
        self.assertEqual(d["often"][:2], ["", "About once a week"])
        self.assertEqual(d["traits"], TRAIT_NAMES)

    def test_na_rating(self):
        d = M.read_data(csv_text(mutate=lambda i, r: r[:11] + ["NA"] + r[12:] if i == 3 else r))
        self.assertTrue(math.isnan(d["X"][3, 0]))

    def test_refusals(self):
        bad = [
            csv_text(n=M.N - 1),
            csv_text(mutate=lambda i, r: [str(i + 2)] + r[1:] if i == 5 else r),           # sub_n out of order
            csv_text(mutate=lambda i, r: r[:1] + ["0"] + r[2:] if i == 5 else r),          # rating below 1
            csv_text(mutate=lambda i, r: r[:1] + ["50.5"] + r[2:] if i == 5 else r),       # not an integer
            csv_text(mutate=lambda i, r: r[:6] + ["Maybe"] + r[7:] if i == 5 else r),      # use_yn
            csv_text(mutate=lambda i, r: r[:7] + ["Daily"] + r[8:] if i == 5 else r),      # use_often
            csv_text(mutate=lambda i, r: r[:11] + ["101"] + r[12:] if i == 5 else r),      # a rating above 100
            csv_text(mutate=lambda i, r: r[:-1] if i == 5 else r),                         # a short row
            csv_text().replace("pheno_conf", "confidence", 1),                              # the header
        ]
        for k, text in enumerate(bad):
            with self.subTest(k=k):
                with self.assertRaises(M.Refused):
                    M.read_data(text)


class Usage(unittest.TestCase):
    def test_the_authors_coding(self):
        use = ["No", "", "Yes", "Yes", "Yes", "Yes", "Yes", "Yes"]
        often = ["", "", "About once a month", "About once every two weeks", "About once a week",
                 "About once a day", "More than once a day", ""]
        self.assertEqual(M.usage_codes(use, often), [1, 1, 2, 3, 4, 5, 6, None])


class Statistics(unittest.TestCase):
    def test_least_squares(self):
        x = np.array([1.0, 2, 3, 4, 5])
        y = np.array([2.0, 4.1, 5.9, 8.2, 9.8])
        f = M.ols(x, y)
        b, a = np.polyfit(x, y, 1)
        self.assertAlmostEqual(f["b"], b, places=12)
        self.assertAlmostEqual(f["a"], a, places=12)
        res = y - (a + b * x)
        se = math.sqrt(res @ res / 3 / np.sum((x - x.mean()) ** 2))
        self.assertAlmostEqual(f["se"], se, places=12)

    def test_pearson(self):
        x = np.array([1.0, 2, 3, 4, 5, 6])
        y = np.array([1.5, 1.9, 3.7, 3.1, 5.6, 5.2])
        c = M.pearson(x, y)
        self.assertAlmostEqual(c["r"], np.corrcoef(x, y)[0, 1], places=12)
        self.assertAlmostEqual(c["p"], M.t_p(c["t"], 4), places=15)
        self.assertTrue(c["ci"][0] < c["r"] < c["ci"][1])

    def test_r_poly(self):
        # R: poly(1:5, 2)
        want = np.array([[-2, 2], [-1, -1], [0, -2], [1, -1], [2, 2]]) / np.array([math.sqrt(10), math.sqrt(14)])
        self.assertTrue(np.allclose(M.poly(np.arange(1.0, 6), 2), want))

    def test_quadratic_against_a_direct_fit(self):
        g = np.random.Generator(np.random.PCG64(3))
        x = g.integers(1, 101, 200).astype(float)
        y = 30 - 0.8 * x + 0.01 * x * x + g.normal(0, 5, 200)
        q = M.quadratic(y, x)
        Z = M.poly(x, 2)
        A = np.column_stack([np.ones(200), Z])
        coef = np.linalg.lstsq(A, y, rcond=None)[0]
        self.assertAlmostEqual(q["b"], coef[2], places=9)
        self.assertAlmostEqual(q["F"], q["t"] ** 2, places=8)                        # one added term

    def test_welch(self):
        w = M.welch([1, 2, 3], [4, 5, 6])
        self.assertAlmostEqual(w["df"], 4.0, places=12)


class Pca(unittest.TestCase):
    def test_imputation_and_orientation(self):
        g = np.random.Generator(np.random.PCG64(11))
        f = g.standard_normal(500)
        X = np.column_stack([f + 0.5 * g.standard_normal(500) for _ in range(6)])
        X[4, 2] = np.nan
        P = M.pca(X)
        self.assertEqual(P["missing"], 1)
        self.assertTrue(np.all(P["load"][:, 0] > 0))                                 # a common factor, oriented
        self.assertGreater(np.corrcoef(P["scores"][:, 0], f)[0, 1], 0.9)
        Xf = X.copy()
        Xf[4, 2] = np.nanmean(X[:, 2])
        self.assertTrue(np.allclose(M.pca(Xf)["scores"], P["scores"]))


class Controls(unittest.TestCase):
    def test_known_answers(self):
        self.assertTrue(all(M.controls_known().values()))


class Seed(unittest.TestCase):
    def test_refuses_a_bad_seed(self):
        with self.assertRaises(M.Refused):
            M.run("xyz", inputs=os.path.join(HERE, "_never"), results=os.path.join(HERE, "_never"))


@unittest.skipUnless(HAVE, "the authors' Data.csv is not at inputs/ (or FOLK_INPUTS)")
class AuthorsFile(unittest.TestCase):
    def test_structure(self):
        name, sha = M.INPUTS["data"]
        d = M.read_data(M.read_bytes(os.path.join(INPUTS, name), sha).decode("utf-8-sig"))
        self.assertEqual(d["X"].shape, (300, 65))
        self.assertEqual(int(np.isnan(d["X"]).sum()), 17)
        self.assertEqual(sorted(set(np.nonzero(np.isnan(d["X"]))[0])), [3])          # all from one participant
        self.assertEqual([d["gender"].count(k) for k in ("Female", "Male", "Non-binary / third gender",
                                                          "Prefer not to say")], [152, 142, 2, 4])
        self.assertEqual(d["traits"][0], "act morally")
        self.assertEqual(d["traits"][-1], "wishing")


if __name__ == "__main__":
    unittest.main()
