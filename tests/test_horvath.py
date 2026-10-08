"""Horvath's clock: the R pieces the port must reproduce exactly (R 4.3.3's own values: runif and sample after
set.seed(1) under the pre-3.6.0 sampling rule, optim's Nelder-Mead and BFGS on Rosenbrock's function, density()'s mode
and bandwidth, quantile and var); a series matrix read and anything malformed refused; the units' rules on made-up
characteristics; M-values turned into betas; and, with the paper's additional files at inputs/ (or HORVATH_INPUTS), the
tutorial's printed values, which are gate 1.

Run with: python3 -m unittest discover -s tests
"""

import gzip
import importlib.util
import math
import os
import sys
import tempfile
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "horvath"))
_spec = importlib.util.spec_from_file_location("horvath_clock", os.path.join(HERE, "..", "horvath", "clock.py"))
C = importlib.util.module_from_spec(_spec)
sys.modules["horvath_clock"] = C
_spec.loader.exec_module(C)
B = C.bmiq


def rosenbrock(x):
    return 100 * (x[1] - x[0] * x[0]) ** 2 + (1 - x[0]) ** 2


class AsR(unittest.TestCase):
    """Every expected value here is R 4.3.3's, printed with %.17g."""

    def test_random_numbers(self):
        r = B.RRandom(1)
        self.assertEqual([r.unif_rand() for _ in range(3)],
                         [0.26550866314209998, 0.37212389963679016, 0.57285336335189641])
        s = B.r_sample(21368, 20000)                       # RNGkind(sample.kind = "Rounding"); set.seed(1)
        self.assertEqual(s[:8], [5674, 7952, 12240, 19404, 4309, 19193, 20181, 14116])
        self.assertEqual(s[-6:], [20057, 20095, 16864, 4310, 4517, 2830])
        self.assertEqual(sum(s), 213599923)
        self.assertEqual(len(set(s)), 20000)

    def test_optim(self):
        self.assertEqual(B.nmmin(rosenbrock, [-1.2, 1], maxit=500), [1.0002601387256695, 1.000505999303765])
        self.assertEqual(B.nmmin(rosenbrock, [-1.2, 1], maxit=50), [-0.71460362434386515, 0.47018069267272222])
        self.assertEqual(B.vmmin(rosenbrock, [-1.2, 1]), [0.99980443323139745, 0.99960838062348123])

    def test_density_mode_and_bandwidth(self):
        x = np.array([0.1, 0.12, 0.13, 0.2, 0.21, 0.35, 0.36, 0.37, 0.38, 0.9])
        self.assertEqual(B.density_mode(x), 0.18476076606999361)
        self.assertEqual(B.bw_nrd0(x), 0.093231010602297174)
        a = np.sort(x)
        self.assertEqual((B._quantile7(a, 0.25), B._quantile7(a, 0.75)), (0.14750000000000002, 0.36749999999999994))
        self.assertAlmostEqual(B.r_var(x), 0.055040000000000006, places=16)

    def test_mean_with_a_trim_returns_its_value(self):
        self.assertEqual(B.r_mean_trim(0.3, 0.7), 0.3)          # mean(max(A), min(B)) is max(A)
        self.assertEqual(B.r_mean_trim(0.3, math.inf), 0.3)

    def test_exp_overflow_is_infinite_and_optim_errors_give_one_one(self):
        self.assertEqual(B.r_exp(1e6), math.inf)
        y = np.array([0.1, 0.3, 0.2])                           # no weight: the moments are NaN, optim errs
        self.assertEqual(B.beta_est(y, np.zeros(3), "BFGS"), (1.0, 1.0))
        # two points: the moments' estimate itself, as R gives it
        self.assertEqual(B.beta_est(np.array([0.1, 0.3]), np.ones(2), "BFGS"), (3.0000000000000031, 12.000000000000011))
        # four weighted points: R 4.9054791366203432 and 18.077822131577104; R's dbeta differs in its last digits
        a, b = B.beta_est(np.array([0.1, 0.3, 0.2, 0.25]), np.array([1, 1, 0.5, 1.0]), "BFGS")
        self.assertAlmostEqual(a / 4.9054791366203432, 1, places=9)
        self.assertAlmostEqual(b / 18.077822131577104, 1, places=9)


def series_text(chars, rows, accessions=("GSM1", "GSM2")):
    head = ["!Series_title\t\"t\""]
    head.append("!Sample_geo_accession\t" + "\t".join(f'"{a}"' for a in accessions))
    for c in chars:
        head.append("!Sample_characteristics_ch1\t" + "\t".join(f'"{x}"' for x in c))
    head.append("!series_matrix_table_begin")
    head.append("\"ID_REF\"\t" + "\t".join(f'"{a}"' for a in accessions))
    body = ["\t".join([f'"{r[0]}"'] + [str(v) for v in r[1:]]) for r in rows]
    return "\n".join(head + body + ["!series_matrix_table_end"]) + "\n"


class Series(unittest.TestCase):
    def write(self, d, text):
        path = os.path.join(d, "s.txt.gz")
        with gzip.open(path, "wt") as f:
            f.write(text)
        return path

    def test_read(self):
        with tempfile.TemporaryDirectory() as d:
            path = self.write(d, series_text([["age: 40", "age: 61.5"], ["tissue: Saliva", "tissue: Saliva"]],
                                             [("cgA", 0.5, 0.6), ("cgX", 0.1, 0.2), ("cgB", "", 0.7)]))
            samples, metas, M, absent = C.read_series(path, ["cgA", "cgB", "cgC"])
            self.assertEqual(samples, ["GSM1", "GSM2"])
            self.assertEqual(metas[1], {"age": "61.5", "tissue": "Saliva"})
            self.assertEqual(absent, 1)                         # cgC
            self.assertEqual(M[0].tolist(), [0.5, 0.6])
            self.assertTrue(math.isnan(M[1, 0]) and M[1, 1] == 0.7 and np.isnan(M[2]).all())

    def test_refusals(self):
        with tempfile.TemporaryDirectory() as d:
            twice = self.write(d, series_text([["age: 40", "age: 41"]], [("cgA", 0.5, 0.6), ("cgA", 0.5, 0.6)]))
            with self.assertRaises(C.Refused):
                C.read_series(twice, ["cgA"])
        self.assertRaises(C.Refused, C.age_of, {"age": "40s"}, "x")
        self.assertRaises(C.Refused, C.age_of, {}, "x")

    def test_m_values(self):
        self.assertEqual(C.m_to_beta(np.array([0.0, 1.0, -1.0])).tolist(), [0.5, 2 / 3, 1 / 3])

    def test_units(self):
        def fake(metas):
            return ([f"S{i}" for i in range(len(metas))], metas, None, 0)
        series = {
            "GSE92767": fake([{"tissue": "Saliva", "age": "40"}, {"tissue": "Saliva", "age": "17"}]),
            "GSE51954": fake([{"tissue": "dermis", "age": "25"}, {"tissue": "epidermis", "age": "70"}]),
            "GSE50498": fake([{"age": "20"}, {"age": "73"}]),
            "GSE66351": fake([{"cell type": "bulk", "diagnosis": "CTRL", "age": "80"},
                              {"cell type": "bulk", "diagnosis": "AD", "age": "81"},
                              {"cell type": "Neuron", "diagnosis": "CTRL", "age": "82"}]),
        }
        u = C.units_from(series)
        self.assertEqual(u["saliva"][:3], (["S0"], [40.0], [0]))  # under 18 left out
        self.assertEqual(u["dermis"][2], [0])
        self.assertEqual(u["epidermis"][2], [1])
        self.assertEqual(u["muscle"][2], [0, 1])
        self.assertEqual(u["cortex"][2], [0])

    def test_statistics(self):
        self.assertAlmostEqual(C.pearson([1, 2, 3, 4], [2, 4, 6, 8]), 1.0)
        self.assertEqual(C.median_abs([1, 2, 10], [2, 2, 2]), 1.0)
        self.assertEqual(C.anti_trafo(0.0), 20.0)
        self.assertAlmostEqual(C.anti_trafo(math.log(1 / 21)), 0.0)


def inputs_dir():
    d = os.environ.get("HORVATH_INPUTS") or os.path.join(HERE, "..", "inputs")
    return d if all(os.path.isfile(os.path.join(d, n)) for n, *_ in C.INPUTS) else None


@unittest.skipUnless(inputs_dir(), "the paper's additional files are not at inputs/ (or HORVATH_INPUTS)")
class Tutorial(unittest.TestCase):
    def test_gate_1(self):
        d = inputs_dir()
        paths = {n: C.checked(d, n, sha, size) for n, sha, size, _ in C.INPUTS}
        names, gold = C.read_gold(paths["AdditionalFile22.csv"])
        intercept, coef = C.read_clock(paths["AdditionalFile23.csv"])
        samples, M = C.read_example(paths["AdditionalFile26.csv"], names)
        gf = B.gold_fit(gold)
        ages, imputed, _, norm = C.predict(M[:, :4], gold, gf, intercept, coef, names, keep_normalised=True)
        idx = {n: i for i, n in enumerate(names)}
        for probe, row in C.TUTORIAL_NORMALISED.items():
            for j, v in enumerate(row):
                self.assertLess(abs(norm[idx[probe], j] - v), 1e-8)
        self.assertEqual([C.signif2(a) for a in ages], list(C.TUTORIAL_AGES[:4]))
        self.assertEqual(imputed, 0)


if __name__ == "__main__":
    unittest.main()
