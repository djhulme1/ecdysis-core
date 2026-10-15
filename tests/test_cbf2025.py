"""Colombatto, Birch & Fleming (folk/cbf2025.py): the readers on files written here, the advice rates and dimensions on
participants worked by hand, the Bayes factors against independent forms and a known approximation, the statistics
against known answers, and the conditions on made-up experiments whose outcome is known. No file of the authors' is
read.

Run with: python3 -m unittest discover -s tests -p test_cbf2025.py
"""

import importlib.util
import math
import os
import unittest

import mpmath
import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("folk_cbf2025", os.path.join(HERE, "..", "folk", "cbf2025.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "cd" * 32
TWENTY = M.TRAIT_EXP + M.TRAIT_INT


def trials(differed, taken, n=40):
    """differed trials whose advice differed (first choice wrong, advice right), the first `taken` of them taken;
    the rest agreeing (both right, advice declined)."""
    out = []
    for k in range(differed):
        resp = "y" if k < taken else "n"
        out.append((0, 1, resp, 1 if resp == "y" else 0))
    out += [(1, 1, "n", 1)] * (n - differed)
    return out


def task_text(parts):
    lines = [",".join(M.TASK_HEAD)]
    for s, (order, ts) in parts.items():
        for i, (acc, adv, resp, post) in enumerate(ts, 1):
            lines.append(f'{s},{order},3,{i},Which country has a larger population:   A or B,arrowleft,{acc},1200,'
                         f'"Your  choice: A  Chat GPT\'s choice: B   Would you like to change your initial choice?  '
                         f'Press \'y\' for yes, \'n\' for no",{adv},{resp},{post},900')
    return "\n".join(lines) + "\n"


def traits_text(parts):
    lines = ['"sub_n","trait","response"']
    for s, d in parts.items():
        for t, v in d.items():
            lines.append(f'{s},"{t}",{"" if v is None else v}')
    return "\n".join(lines) + "\n"


def demo_text(parts):
    lines = [",".join(M.DEMO_HEAD)]
    for s, (age, gender, t1, t2, often) in parts.items():
        lines.append(f"{s},{age},{gender},NA,{t1},{t2}," + ",".join("NA" if v is None else str(v) for v in often))
    return "\n".join(lines) + "\n"


def hand():
    task = {1: ("task_traits", trials(10, 4)), 2: ("traits_task", trials(0, 0)), 3: ("traits_task", trials(8, 8))}
    ratings = {1: dict({"consc": 7}, **{t: 10 for t in M.TRAIT_EXP}, **{t: 50 for t in M.TRAIT_INT}),
               2: dict({"consc": None}, **{t: 20 for t in TWENTY}),
               3: dict({t: 30 for t in TWENTY if t != "fear"})}
    ratings[3]["consc"] = 1
    ratings[2]["hope"] = None
    demo = {1: (44, M.WOMAN, 50, 60, (7, 1, 0)), 2: (31, M.MAN, 80, 70, (None, 4, 1)),
            3: (60, "Prefer not to say", 0, 100, (2, 2, 2))}
    return task_text(task), traits_text(ratings), demo_text(demo)


class Reading(unittest.TestCase):
    def test_hand(self):
        tt, rt, dt = hand()
        task, traits, demo = M.read_task(tt), M.read_traits(rt), M.read_demo(dt)
        M.same_participants(task, traits, demo)
        rates, none = M.advice_rates(task)
        self.assertEqual(rates, {1: 40.0, 3: 100.0})
        self.assertEqual(none, [2])
        self.assertEqual(task[1]["order"], "task_traits")
        self.assertEqual(task[1]["trials"][1], (0, 1, "y", 1))
        self.assertIsNone(traits[2]["consc"])
        self.assertEqual(M.dimension(traits[1], M.TRAIT_EXP), 10.0)
        self.assertEqual(M.dimension(traits[1], M.TRAIT_INT), 50.0)
        self.assertEqual(M.dimension(traits[3], M.TRAIT_EXP), 30.0)       # nine rows present: their mean
        self.assertIsNone(M.dimension(traits[2], M.TRAIT_EXP))            # an empty response: missing
        self.assertEqual(M.dimension(traits[2], M.TRAIT_INT), 20.0)
        self.assertIsNone(M.dimension({"consc": 4}, M.TRAIT_EXP))         # no rows at all
        self.assertEqual(demo[2]["often"], [None, 4, 1])
        self.assertEqual(M.reading_check(task), (18, 0))

    def test_reading_check_catches(self):
        tt, _, _ = hand()
        task = M.read_task(tt.replace("1,task_traits,3,1,", "1,task_traits,3,1,", 1))
        task[1]["trials"][1] = (0, 1, "y", 0)                              # took the advice, yet still wrong
        self.assertEqual(M.reading_check(task), (18, 1))

    def test_refusals(self):
        tt, rt, dt = hand()
        bad_task = [
            tt.replace("sub_n,task_order", "sub,task_order"),
            tt.replace("\n1,task_traits,3,40,", "\n1,task_traits,3,39,"),            # trial 39 twice, no 40
            tt.replace(",arrowleft,1,1200,", ",arrowleft,2,1200,", 1),               # acc 2
            tt.replace(",1,n,1,900", ",1,x,1,900", 1),                               # response_adv x
            tt.replace("\n2,traits_task,3,5,", "\n2,task_traits,3,5,"),              # two orders
            tt.replace("\n3,traits_task,", "\n3,both,", 1),
            "\n".join(tt.splitlines()[:-1]) + "\n",                                    # 39 trials
        ]
        for text in bad_task:
            with self.assertRaises(M.Refused):
                M.read_task(text)
        bad_traits = [rt.replace('"consc",7', '"consciousness",7'), rt.replace('"consc",7', '"consc",101'),
                      rt + '1,"hope",3\n', rt.replace('"consc",7', '"consc",7.5'), rt.replace('"trait"', '"traits"')]
        for text in bad_traits:
            with self.assertRaises(M.Refused):
                M.read_traits(text)
        self.assertIsNone(M.read_traits(rt.replace('"consc",7', '"consc",NA'))[1]["consc"])
        bad_demo = [dt.replace(",50,60,", ",101,60,"), dt.replace("\n2,31,", "\n1,31,"),
                    dt.replace("\n2,31,", "\n2,NA,"), dt.replace("7,1,0", "8,1,0")]
        for text in bad_demo:
            with self.assertRaises(M.Refused):
                M.read_demo(text)
        task, traits, demo = M.read_task(tt), M.read_traits(rt), M.read_demo(dt)
        del demo[3]
        with self.assertRaises(M.Refused):
            M.same_participants(task, traits, demo)

    def test_code(self):
        text = "\n".join(M.CODE_LINES) + "\n"
        self.assertEqual(M.read_code(text), len(M.CODE_LINES))
        with self.assertRaises(M.Refused):
            M.read_code(text.replace("PCA(data_ms[, 1:21]", "PCA(data_ms[, 2:21]"))


class BayesFactors(unittest.TestCase):
    CASES = ((12, 0.35), (50, -0.2), (300, 0.08), (40, 0.0), (500, -0.13), (420, 0.6))

    def test_likelihood_forms_agree(self):
        for n, r in self.CASES:
            for rho in (-0.9, -0.7, -0.2, 0.1, 0.5, 0.9):
                self.assertLess(M.rel(M.h_ratio(n, r, rho), M.ly_ab(n, r, rho)), 1e-12, (n, r, rho))

    def test_hotelling_density(self):
        with mpmath.workdps(30):
            total = mpmath.quad(lambda x: M.hotelling_density(7, x, 0.4), [-1, 0.4, 1])
        self.assertAlmostEqual(float(total), 1.0, places=12)
        n, r = 9, 0.3                                     # under rho = 0: (1 - r^2)^((n-4)/2)/B(1/2, (n-2)/2)
        self.assertAlmostEqual(float(M.hotelling_density(n, r, 0)),
                               (1 - r * r) ** ((n - 4) / 2) / math.exp(math.lgamma(0.5) + math.lgamma((n - 2) / 2)
                                                                      - math.lgamma((n - 1) / 2)), places=12)
        self.assertAlmostEqual(float(M.h_ratio(n, r, 0.5)),
                               float(M.hotelling_density(n, r, 0.5) / M.hotelling_density(n, r, 0)), places=12)

    def test_quadrature_matches_closed_forms(self):
        for n, r in self.CASES:
            b, c = M.bayes(n, r), M.bayes_closed(n, r)
            for k in ("plus", "minus", "bf10"):
                self.assertLess(M.rel(b[k], c[k]), 1e-10, (n, r, k))
                self.assertGreater(b[k], 0)
            self.assertAlmostEqual(b["bf10"], (b["plus"] + b["minus"]) / 2, delta=1e-12 * b["bf10"])

    def test_symmetry_and_order(self):
        a, b = M.bayes(80, 0.25), M.bayes(80, -0.25)
        self.assertLess(M.rel(a["plus"], b["minus"]), 1e-12)
        self.assertGreater(a["plus"], a["bf10"])
        self.assertGreater(a["bf10"], a["minus"])
        z = M.bayes(40, 0.0)
        self.assertLess(M.rel(z["plus"], z["minus"]), 1e-12)

    def test_jeffreys_approximation(self):
        n, r = 1000, 0.05                                 # Jeffreys: BF01 ~ sqrt((2n - 1)/pi) (1 - r^2)^((n - 4)/2)
        approx = math.sqrt((2 * n - 1) / math.pi) * (1 - r * r) ** ((n - 4) / 2)
        self.assertLess(abs(M.bayes(n, r)["bf10"] * approx - 1), 0.02)


class Statistics(unittest.TestCase):
    def test_pearson_spearman(self):
        p = M.pearson([1, 2, 3, 4, 5], [2, 4, 5, 4, 5])
        self.assertAlmostEqual(p["r"], 6 / math.sqrt(60), places=14)
        self.assertEqual(p["df"], 3)
        self.assertAlmostEqual(p["p"], float(stats.pearsonr([1, 2, 3, 4, 5], [2, 4, 5, 4, 5])[1]), places=12)
        z, h = math.atanh(p["r"]), 1.959963984540054 / math.sqrt(2)
        self.assertAlmostEqual(p["ci"][0], math.tanh(z - h), places=12)
        s = M.spearman([1, 2, 2, 3], [1, 3, 2, 4])                        # ties: average ranks
        self.assertAlmostEqual(s["rho"], 4.5 / math.sqrt(22.5), places=14)

    def test_lm(self):
        g = np.random.default_rng(3)
        E, I = g.uniform(1, 50, 60), g.uniform(10, 90, 60)
        y = 3 + 2 * E - I + 0.5 * E * I
        f = M.lm(y, [E, I, E * I])
        for got, want in zip(f["coef"], (3, 2, -1, 0.5)):
            self.assertAlmostEqual(got, want, places=8)
        self.assertEqual(f["df"], 56)
        y = y + g.normal(0, 30, 60)
        f = M.lm(y, [E, I, E * I])
        c, s, p = M.lm_statsmodels(y, f["A"])
        for a, b in zip(f["coef"] + f["se"] + f["p"], c + s + p):
            self.assertLess(M.rel(a, b), 1e-9)
        self.assertAlmostEqual(M.t_p(2.228138851986, 10), 0.05, places=9)
        q = float(stats.t.ppf(0.975, 56))
        self.assertAlmostEqual(f["lo"][1], f["coef"][1] - q * f["se"][1], places=12)

    def test_poly(self):
        xs = np.array([1.0, 2, 2, 5, 7, 9, 10])
        Z = M.poly(xs, 2)
        self.assertTrue(np.allclose(Z.T @ Z, np.eye(2)))
        self.assertTrue(np.allclose(Z.sum(axis=0), 0))
        self.assertGreater(np.polyfit(xs, Z[:, 1], 2)[0], 0)
        self.assertGreater(np.polyfit(xs, Z[:, 0], 1)[0], 0)

    def test_t_tests(self):
        w = M.welch([1, 2, 3], [4, 5, 6])
        self.assertAlmostEqual(w["t"], -3 / math.sqrt(2 / 3), places=12)
        self.assertAlmostEqual(w["df"], 4, places=12)
        self.assertAlmostEqual(w["d"], 3.0, places=12)
        p = M.paired([1, 2, 3, 4], [2, 2, 5, 4])
        sd = math.sqrt(2.75 / 3)
        self.assertAlmostEqual(p["t"], -0.75 / (sd / 2), places=12)
        self.assertEqual(p["df"], 3)
        self.assertAlmostEqual(p["d"], 0.75 / sd, places=12)

    def test_pca(self):
        x, y = [1, 2, 3, 4, 5], [2, 4, 5, 4, 5]
        shares, missing = M.pca_shares(list(zip(x, y)))
        r = 6 / math.sqrt(60)
        self.assertAlmostEqual(shares[0], 50 * (1 + r), places=10)
        self.assertAlmostEqual(shares[1], 50 * (1 - r), places=10)
        self.assertEqual(missing, 0)
        _, missing = M.pca_shares([[1, 2], [2, math.nan], [3, 5], [4, 4]])
        self.assertEqual(missing, 1)

    def test_sign_only(self):
        self.assertTrue(M.sign_only("-0.00", "0.00"))
        self.assertTrue(M.sign_only("-0.01, 0.00", "0.01, 0.00"))
        self.assertFalse(M.sign_only("0.02", "0.01"))
        self.assertFalse(M.sign_only("0.01", "0.01"))

    def test_shuffles_null(self):
        g = np.random.default_rng(11)
        n = 300
        x, y = g.normal(size=n), g.normal(size=n)
        E, I = g.uniform(1, 60, n), g.uniform(10, 100, n)
        A = np.column_stack([np.ones(n), E, I, E * I])
        r = M.pearson(y, x)
        yr = g.normal(size=n)
        sh = M.shuffles(SEED, y, x, r["r"], yr, A)
        self.assertEqual(sh["n"], M.SHUFFLES)
        self.assertLess(abs(sh["p_perm"] - r["p"]), 0.02)
        self.assertLessEqual(sh["int_below"], 0.01 * sh["n"])
        self.assertTrue(0.02 * sh["n"] <= sh["exp_below"] <= 0.09 * sh["n"])
        self.assertEqual(M.shuffles(SEED, y, x, r["r"], yr, A), sh)          # the same seed, the same shuffles
        self.assertNotEqual(M.shuffles("ef" * 32, y, x, r["r"], yr, A), sh)


def experiment(n=240, seed=5, consc_sign=-1.0, exp_effect=-1.0, int_effect=0.5):
    """A made-up experiment: each participant's experience and intelligence levels set their 20 ratings, their advice
    rate (of 20 trials whose advice differed) follows the given effects, and their consciousness rating moves with the
    rate in the given direction."""
    g = np.random.default_rng(seed)
    task, ratings, demo = {}, {}, {}
    for s in range(1, n + 1):
        e, i = g.uniform(1, 60), g.uniform(20, 100)
        rate = 60 + exp_effect * (e - 30) + int_effect * (i - 60) + g.normal(0, 6)
        k = int(min(20, max(0, round(rate / 5))))
        task[s] = ("task_traits" if s % 2 else "traits_task", trials(20, k))
        d = {t: int(min(100, max(1, round(e + g.normal(0, 3))))) for t in M.TRAIT_EXP}
        d.update({t: int(min(100, max(1, round(i + g.normal(0, 3))))) for t in M.TRAIT_INT})
        d["consc"] = int(min(100, max(1, round(25 + consc_sign * 0.9 * (5 * k - 60) + g.normal(0, 4)))))
        if s == 7:
            d["consc"] = None
        ratings[s] = d
        often = [int(v) for v in g.integers(0, 8, 3)]
        if s % 50 == 0:
            often[1] = None
        demo[s] = (int(g.integers(18, 80)), (M.WOMAN, M.MAN, "Prefer not to say")[s % 3], int(g.integers(0, 101)),
                   int(g.integers(0, 101)), often)
    return M.read_task(task_text(task)), M.read_traits(traits_text(ratings)), M.read_demo(demo_text(demo))


class Assessing(unittest.TestCase):
    def test_passing(self):
        out, detail = M.assess(*experiment(), SEED)
        self.assertEqual((out["conditions_met"], out["conditions_total"], out["test_passed"]), (3, 3, 1))
        self.assertEqual((out["controls_passed"], out["controls_total"]), (5, 5), detail["controls"])
        self.assertLess(out["bf_plus"], 0.1)
        self.assertLess(out["b_experience"], 0)
        self.assertGreater(out["b_intelligence"], 0)
        self.assertEqual(detail["pearson"]["n"], 239)
        self.assertEqual(detail["reading"]["inconsistent"], 0)
        self.assertEqual(len(detail["pca"]["with_sub_n"]), 21)
        self.assertEqual(len(detail["pca"]["without"]), 20)
        self.assertTrue(out["sample"].startswith("240 participants (80 women, 80 men, 80 others"))
        for k, v in out.items():
            self.assertLessEqual(len(str(v)), M.LIMIT, k)

    def test_failing(self):
        out, _ = M.assess(*experiment(consc_sign=1.0), SEED)          # consciousness rises with advice-taking
        self.assertEqual((out["conditions_met"], out["test_passed"]), (2, 0))
        self.assertGreater(out["bf_plus"], 10)
        out, _ = M.assess(*experiment(exp_effect=0.6), SEED)          # experience raises advice-taking
        self.assertEqual((out["conditions_met"], out["test_passed"]), (2, 0))
        out, _ = M.assess(*experiment(int_effect=0.0), SEED)          # intelligence does nothing
        self.assertEqual(out["test_passed"], 0)
        self.assertLessEqual(out["conditions_met"], 2)


class Machinery(unittest.TestCase):
    def test_inputs_and_outputs(self):
        self.assertEqual(len(M.INPUTS), 4)
        for name, sha in M.INPUTS.values():
            self.assertRegex(name, r"[A-Za-z][A-Za-z0-9_.-]{0,39}")
            self.assertRegex(sha, r"[0-9a-f]{64}")
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 64)
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


if __name__ == "__main__":
    unittest.main()
