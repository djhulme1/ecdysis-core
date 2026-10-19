"""Song, Hu & Mahowald 2025 (introspect/shm2025.py): the release reader on files made here in the release's layout
and its refusals; Pearson's r against numpy; the similarity categories (the paper's Table 1 by name gives 21, 24, 10,
82 and 304 pairs); least squares against an exact case, the exact normal equations and, where installed,
statsmodels; the filter at its bounds and the text's reading; accuracy with ties; Cohen's kappa by hand; the
logistic fit; the planted components (the privileged one correlates with no other model's Direct difference, the
literal self-reader adds c DD(A, B) as its formula says); the texreg reader and the rounding rules; the seeded
stream; and a whole run on a release made here, with the outputs' shape and the seed refused. Nothing here reads the
claim's data, so none of the test's quantities is computed.

Run with: python3 -m unittest discover -s tests -p test_shm2025.py
"""

import csv
import hashlib
import importlib.util
import math
import os
import tempfile
import unittest
from fractions import Fraction

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("introspect_shm2025",
                                               os.path.join(HERE, "..", "introspect", "shm2025.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "cd" * 32
META = {
    "olmo-2-1124-7b": ("olmo", "2", 7.0, "base"),
    "olmo-2-1124-7b-stage2-ingredient1-step11931-tokens50B": ("olmo", "2", 7.0, "base"),
    "qwen2.5-7b": ("qwen", "2.5", 7.0, "base"),
    "qwen2.5-7b-instruct": ("qwen", "2.5", 7.0, "instruct"),
    "llama-3.1-8b": ("llama", "3.1", 8.0, "base"),
    "llama-3.1-70b": ("llama", "3.1", 70.0, "base"),
    "mistral-large-instruct-2411": ("mistral", "large", 123.0, "instruct"),
}
MODELS = sorted(META)


def make_values(rng, n_items, n_prompts, models=MODELS):
    """Direct and Meta differences with a shared factor, a shared part for the two OLMo models and noise."""
    g = rng.normal(size=n_items)
    olmo = rng.normal(size=n_items)
    D, Mm = [], [[] for _ in range(n_prompts)]
    for model in models:
        extra = olmo if model.startswith("olmo") else 0
        D.append(list(np.round(g + rng.normal(size=n_items) + 0.8 * extra, 6)))
    for p in range(n_prompts):
        for a in range(len(models)):
            Mm[p].append(list(np.round(0.4 * g + rng.normal(size=n_items), 4)))
    return D, Mm


def write_release(path, columns, sets, prompts, mutate=None):
    """sets: {dataset: (items, D, Mm)}; Mm indexed by the prompt's position in `prompts`."""
    rows = []
    for ds, (items, D, Mm) in sets.items():
        for a, model in enumerate(MODELS):
            fam, gen, size, kind = META[model]
            for q, p in enumerate(prompts):
                for i, item in enumerate(items):
                    s, d = float(D[a][i]), float(Mm[q][a][i])
                    row = {"model": model, "dataset": ds, "model_family": fam, "model_gen": gen,
                           "model_size": f"{size:.1f}", "model_type": kind, "pair_ID": item, "sumLP_diff": repr(s),
                           "meanLP_diff": repr(s / 7), "sumLP_ans": str(s > 0), "meanLP_ans": str(s > 0),
                           "metric_ans": f"prompt{p}_ans", "ans": str(d > 0), "promptID": str(p),
                           "metric_diff": f"prompt{p}_diff", "diff": repr(d)}
                    rows.append([row[c] for c in columns])
    if mutate:
        rows = mutate(rows)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(columns)
        w.writerows(rows)


def tex(models, rows, gof=None):
    """A table in texreg's booktabs layout: rows of (label, [value or None], [se or None])."""
    out = ["", "\\usepackage{booktabs}", "\\usepackage{dcolumn}", "", "\\begin{table}", "\\begin{center}",
           "\\begin{tabular}{l " + " ".join(["D{.}{.}{2.7}"] * len(models)) + "}", "\\toprule",
           " & " + " & ".join(f"\\multicolumn{{1}}{{c}}{{{m}}}" for m in models) + " \\\\", "\\midrule"]
    for label, vals, ses in rows:
        out.append(f"{label:12} & " + " & ".join(v or "" for v in vals) + " \\\\")
        if ses:
            out.append(" " * 12 + " & " + " & ".join(f"({s})" if s else "" for s in ses) + " \\\\")
    if gof:
        out.append("\\midrule")
        for label, vals in gof:
            out.append(f"{label} & " + " & ".join(vals) + " \\\\")
    out += ["\\bottomrule", "\\multicolumn{7}{l}{\\scriptsize{$^{***}p<0.001$; $^{**}p<0.01$; $^{*}p<0.05$}}",
            "\\end{tabular}", "\\caption{Statistical models}", "\\label{table:coefficients}", "\\end{center}",
            "\\end{table}", ""]
    return "\n".join(out)


def write_tables(folder):
    cols = list(M.COLUMNS_PRINTED)
    six = ["0.0100^{*}"] * 6
    ses = ["0.0050"] * 6
    files = {
        "modelsim": tex(cols, [(lab, six, ses) for lab in ("Intercept", "directdirect", "seedvariant", "baseinstruct",
                                                           "samefamily", "other")]),
        "bigmodelsim": tex(cols, [(lab, six, ses) for lab in ("Intercept", "directdirect", "baseinstruct",
                                                              "samefamily", "other")]),
        "modelsize": tex(cols, [(lab, six, ses) for lab in ("Intercept", "log Direct model size",
                                                            "log Meta model size", "Interaction")]),
        "olmo": tex(cols, [(lab, six, ses) for lab in ("Intercept", "self")]),
        "methodsize": tex(["estimation"], [(lab, ["0.1000^{***}"], ["0.0100"]) for lab in
                                           ("Intercept", "Meta", "log model size", "Meta:log model")],
                          gof=[("AIC", ["100.0400"]), ("BIC", ["110.1270"]), ("Log Likelihood", ["-48.0200"]),
                               ("Deviance", ["96.0400"])]),
    }
    specs = {}
    for key, text in files.items():
        name = M.TABLES[key][0]
        data = text.encode("utf-8")
        with open(os.path.join(folder, name), "wb") as fh:
            fh.write(data)
        specs[key] = (name, hashlib.sha256(data).hexdigest(), len(data))
    return specs


def spec_of(folder, name):
    with open(os.path.join(folder, name), "rb") as fh:
        data = fh.read()
    return (name, hashlib.sha256(data).hexdigest(), len(data))


def build(folder, n1=60, n2=50, mutate1=None, mutate2=None, seed=1):
    rng = np.random.default_rng(seed)
    items1 = [str(i) for i in range(n1)]
    D, Mm = make_values(rng, n1, 8)
    write_release(os.path.join(folder, "expr1.csv"), M.COLUMNS1, {"BLIMPLI": (items1, D, Mm)}, range(1, 9),
                  mutate1)
    sets = {}
    for ds in M.EXP2_RAW:
        items = [f"{ds}_{i}" for i in range(n2)]
        D2, M2 = make_values(rng, n2, 7)
        sets[ds] = (items, D2, M2)
    write_release(os.path.join(folder, "expr2.csv"), M.COLUMNS2, sets, range(1, 8), mutate2)
    return D, Mm, sets


class Patched:
    """The module's input specifications pointed at files made here."""

    def __init__(self, folder):
        self.folder = folder

    def __enter__(self):
        self.saved = (M.DATA1, M.DATA2, dict(M.TABLES), M.NAMES, M.CATEGORY_COUNTS, M.BOOT_DRAWS)
        M.DATA1 = spec_of(self.folder, "expr1.csv")
        M.DATA2 = spec_of(self.folder, "expr2.csv")
        M.TABLES = write_tables(self.folder)
        M.NAMES = dict(META)
        pairs = M.pair_table(MODELS, META)
        M.CATEGORY_COUNTS = {c: sum(1 for _, _, x in pairs if x == c) for c in M.CATEGORIES}
        M.BOOT_DRAWS = 25
        return self

    def __exit__(self, *exc):
        M.DATA1, M.DATA2, tables, M.NAMES, M.CATEGORY_COUNTS, M.BOOT_DRAWS = self.saved
        M.TABLES.clear()
        M.TABLES.update(tables)
        return False


class Reader(unittest.TestCase):
    def test_reads_the_layout(self):
        with tempfile.TemporaryDirectory() as d:
            D, Mm, sets2 = build(d)
            with Patched(d):
                sets, meta, mis = M.read_all(d)
        self.assertEqual(set(sets), {"BLIMPLI"} | set(M.EXP2))
        self.assertEqual(meta, META)
        self.assertEqual(mis, {"expr1.csv": 0, "expr2.csv": 0})
        e1 = sets["BLIMPLI"]
        self.assertEqual(e1["models"], MODELS)
        self.assertEqual(e1["prompts"], list(range(1, 9)))
        np.testing.assert_array_equal(e1["D"], np.array(D, dtype=float))
        np.testing.assert_array_equal(e1["M"], np.array(Mm, dtype=float))
        nons = sets["nonsense"]
        self.assertEqual(nons["prompts"], [1, 2, 3, 4, 6, 7])
        raw = sets2["jabberwocky"]
        np.testing.assert_array_equal(nons["M"], np.array([raw[2][q] for q in (0, 1, 2, 3, 5, 6)], dtype=float))
        self.assertEqual(nons["items"][:3], ["jabberwocky_0", "jabberwocky_1", "jabberwocky_2"])

    def refused(self, mutate1=None, mutate2=None):
        with tempfile.TemporaryDirectory() as d:
            build(d, n1=12, n2=10, mutate1=mutate1, mutate2=mutate2)
            with Patched(d):
                with self.assertRaises(M.Refused) as cm:
                    M.read_all(d)
        return str(cm.exception)

    def test_refusals(self):
        c = {name: j for j, name in enumerate(M.COLUMNS1)}

        def dup(rows):
            return rows + [rows[0]]

        def drop(rows):
            return rows[1:]

        def bad_sign(rows):
            rows[3][c["ans"]] = "True" if rows[3][c["ans"]] == "False" else "False"
            return rows

        def drift(rows):
            # the same model and item under prompt 2: another Direct difference
            for r in rows:
                if r[c["promptID"]] == "2" and r[c["pair_ID"]] == "0":
                    s = float(r[c["sumLP_diff"]]) + 1.0
                    r[c["sumLP_diff"]] = repr(s)
                    r[c["sumLP_ans"]] = str(s > 0)
                    break
            return rows

        def meta(rows):
            rows[5][c["model_size"]] = "9.0"
            return rows

        def prompt(rows):
            rows[0][c["promptID"]] = "9"
            return rows

        def nan(rows):
            rows[0][c["diff"]] = "nan"
            rows[0][c["ans"]] = "False"
            return rows

        def dataset(rows):
            rows[0][c["dataset"]] = "BLiMP"
            return rows

        def header(rows):
            return rows

        self.assertIn("a second row", self.refused(dup))
        self.assertIn("full grid", self.refused(drop))
        self.assertIn("where the difference is", self.refused(bad_sign))
        self.assertIn("differs between prompts", self.refused(drift))
        self.assertIn("metadata", self.refused(meta))
        self.assertIn("promptID 9", self.refused(prompt))
        self.assertIn("not finite", self.refused(nan))
        self.assertIn("dataset", self.refused(dataset))
        with tempfile.TemporaryDirectory() as d:
            build(d, n1=12, n2=10)
            with open(os.path.join(d, "expr1.csv"), encoding="utf-8") as fh:
                text = fh.read().replace("sumLP_diff,meanLP_diff", "sumLP_diff,mean_diff", 1)
            with open(os.path.join(d, "expr1.csv"), "w", encoding="utf-8") as fh:
                fh.write(text)
            with Patched(d):
                with self.assertRaises(M.Refused) as cm:
                    M.read_all(d)
            self.assertIn("header", str(cm.exception))
            with Patched(d):
                M.DATA1 = (M.DATA1[0], "0" * 64, M.DATA1[2])
                with self.assertRaises(M.Refused) as cm:
                    M.read_all(d)
            self.assertIn("not the registered", str(cm.exception))


class Measures(unittest.TestCase):
    def test_correlations(self):
        rng = np.random.default_rng(3)
        D = rng.normal(size=(5, 40))
        Mm = rng.normal(size=(3, 5, 40))
        dd, md, per = M.correlations(D, Mm)
        for a in range(5):
            for b in range(5):
                self.assertAlmostEqual(dd[a, b], np.corrcoef(D[a], D[b])[0, 1], places=13)
                rs = [np.corrcoef(D[a], Mm[p, b])[0, 1] for p in range(3)]
                for p in range(3):
                    self.assertAlmostEqual(per[p][a, b], rs[p], places=13)
                self.assertAlmostEqual(md[a, b], sum(rs) / 3, places=13)

    def test_categories(self):
        self.assertEqual(M.category("a", "a", {}), "self")
        meta = {"x": ("f", "1", 7.0, "base"), "y": ("f", "1", 7.0, "base"), "z": ("f", "1", 7.0, "instruct"),
                "w": ("f", "2", 7.0, "instruct"), "v": ("g", "1", 7.0, "base")}
        self.assertEqual(M.category("x", "y", meta), "seed variant")
        self.assertEqual(M.category("x", "z", meta), "base/instruct")
        self.assertEqual(M.category("z", "w", meta), "same family")
        self.assertEqual(M.category("x", "v", meta), "other")
        names = sorted(M.NAMES)
        pairs = M.pair_table(names, M.NAMES)
        counts = {c: sum(1 for _, _, x in pairs if x == c) for c in M.CATEGORIES}
        self.assertEqual(len(names), 21)
        self.assertEqual(counts, M.CATEGORY_COUNTS)

    def test_ols(self):
        rng = np.random.default_rng(4)
        X = np.column_stack([np.ones(30), rng.normal(size=30), rng.normal(size=30), np.zeros(30)])
        y = X[:, :3] @ np.array([0.5, -2.0, 1.25]) + rng.normal(scale=0.1, size=30)
        fit = M.ols(y, X, ["c", "a", "b", "never"])
        self.assertEqual(fit["names"], ["c", "a", "b"])
        ex = M.exact_ols(y, X[:, :3])
        for q in range(3):
            self.assertLess(abs(float(ex[q]) - fit["b"][q]), 1e-12)
        # standard errors and p values by hand
        Xk = X[:, :3]
        e = y - Xk @ np.array(fit["b"])
        s2 = e @ e / 27
        se = np.sqrt(np.diag(np.linalg.inv(Xk.T @ Xk)) * s2)
        for q in range(3):
            self.assertAlmostEqual(fit["se"][q], se[q], places=12)
            t = fit["b"][q] / se[q]
            self.assertAlmostEqual(fit["p"][q], 2 * M.stats.t.sf(abs(t), 27), places=12)
        exact = M.ols(Xk @ np.array([1.0, 2.0, 3.0]) + np.array([1, -1] * 15) * 1e-3, Xk, ["c", "a", "b"])
        self.assertAlmostEqual(exact["b"][2], 3.0, places=2)
        try:
            import statsmodels.api as sm
        except ImportError:
            return
        res = sm.OLS(y, Xk).fit()
        for q in range(3):
            self.assertLess(abs(res.params[q] - fit["b"][q]), 1e-12)
            self.assertLess(abs(res.bse[q] - fit["se"][q]), 1e-12)

    def test_negatives_and_min_t(self):
        fit = {"names": ["(Intercept)", "directdirect", "seed variant", "base/instruct", "same family", "other"],
               "b": [0.1, -0.5, -0.02, 0.01, -0.03, 0.04], "t": [5, -9, -1.0, 0.5, -3.0, 2.0],
               "p": [0.0, 0.0, 0.3, 0.6, 0.003, 0.04]}
        self.assertEqual(M.negatives(fit), ["same family"])
        self.assertEqual(M.min_t(fit), -3.0)

    def test_filter_bounds(self):
        # 21 models, 8 prompts; item k has the stated counts of negative Direct and Meta differences
        cases = [(1, 50), (2, 50), (19, 50), (20, 50), (10, 8), (10, 9), (10, 159), (10, 160)]
        expect = [False, True, True, False, False, True, True, False]
        D = np.ones((21, len(cases)))
        Mm = np.ones((8, 21, len(cases)))
        for i, (nd, nm) in enumerate(cases):
            D[:nd, i] = -1.0
            flat = Mm[:, :, i].reshape(-1)
            flat[:nm] = -1.0
            Mm[:, :, i] = flat.reshape(8, 21)
        keep = M.filter_pairs(D, Mm)
        self.assertEqual([i in keep for i in range(len(cases))], expect)
        # a zero difference is not negative
        D2 = D.copy()
        D2[:2, 1] = 0.0
        self.assertNotIn(1, M.filter_pairs(D2, Mm))

    def test_text_reading(self):
        D = np.ones((21, 2))
        Mm = np.ones((8, 21, 2))
        flat = Mm[:, :, 0].reshape(-1)
        flat[:8] = -1.0
        Mm[:, :, 0] = flat.reshape(8, 21)
        flat = Mm[:, :, 1].reshape(-1)
        flat[:9] = -1.0
        Mm[:, :, 1] = flat.reshape(8, 21)
        self.assertEqual(M.filter_text(D, Mm), [1])

    def test_accuracy_with_ties(self):
        D = np.array([[1.0, 0.0, -1.0, 2.0]])
        Mm = np.array([[[1.0, 1.0, 0.0, 1.0]], [[-1.0, -1.0, -1.0, 1.0]]])
        direct, meta = M.accuracy(D, Mm)
        self.assertEqual(direct, [Fraction(2, 4)])
        self.assertEqual(meta, [[Fraction(3, 4)], [Fraction(1, 4)]])

    def test_kappa(self):
        # the 2 x 2 table [[20, 5], [10, 15]]: po = 35/50, pe = (25*30 + 25*20)/2500 = 1/2
        x = [True] * 25 + [False] * 25
        y = [True] * 20 + [False] * 5 + [True] * 10 + [False] * 15
        self.assertEqual(M.kappa(x, y), Fraction(2, 5))
        self.assertEqual(M.kappa(x, x), 1)

    def test_logistic(self):
        # one group per (method, x): the fit reproduces each group's share when the model is saturated
        groups = [{"meta": 0.0, "x": 0.0, "s": 30, "n": 40}, {"meta": 0.0, "x": 1.0, "s": 35, "n": 40},
                  {"meta": 1.0, "x": 0.0, "s": 20, "n": 40}, {"meta": 1.0, "x": 1.0, "s": 36, "n": 40}]
        fit = M.logistic(groups)
        logit = [math.log(s / (40 - s)) for s in (30, 35, 20, 36)]
        self.assertAlmostEqual(fit["b"][0], logit[0], places=10)
        self.assertAlmostEqual(fit["b"][0] + fit["b"][2], logit[1], places=10)
        self.assertAlmostEqual(fit["b"][0] + fit["b"][1], logit[2], places=10)
        self.assertAlmostEqual(sum(fit["b"]), logit[3], places=10)
        ll = sum(s * math.log(s / 40) + (40 - s) * math.log(1 - s / 40) for s in (30, 35, 20, 36))
        self.assertAlmostEqual(fit["loglik"], ll, places=9)
        self.assertAlmostEqual(fit["aic"], -2 * ll + 8, places=8)
        self.assertAlmostEqual(fit["bic"], -2 * ll + 4 * math.log(160), places=8)
        try:
            import statsmodels.api as sm
        except ImportError:
            return
        rng = np.random.default_rng(5)
        groups = [{"meta": float(m), "x": float(x), "s": int(rng.integers(5, 35)), "n": 40}
                  for m in (0, 1) for x in (0.0, 0.7, 1.5, 2.2)]
        fit = M.logistic(groups)
        X = np.array([[1.0, g["meta"], g["x"], g["meta"] * g["x"]] for g in groups])
        res = sm.GLM(np.array([g["s"] / g["n"] for g in groups]), X, family=sm.families.Binomial(),
                     var_weights=np.array([g["n"] for g in groups], dtype=float)).fit(tol=1e-14)
        for q in range(4):
            self.assertLess(abs(res.params[q] - fit["b"][q]), 1e-8)
            self.assertLess(abs(res.bse[q] - fit["se"][q]), 1e-8)


class Planted(unittest.TestCase):
    def test_unique_parts(self):
        rng = np.random.default_rng(6)
        D = rng.normal(size=(6, 80)) + rng.normal(size=80)
        U = M.unique_parts(D)
        for a in range(6):
            self.assertAlmostEqual(float(U[a] @ U[a]), 1.0, places=12)
            self.assertAlmostEqual(float(U[a].sum()), 0.0, places=12)
            for b in range(6):
                if b != a:
                    self.assertLess(abs(np.corrcoef(U[a], D[b])[0, 1]), 1e-10)
            self.assertGreater(np.corrcoef(U[a], D[a])[0, 1], 0)

    def test_privileged_plant_is_seen(self):
        rng = np.random.default_rng(7)
        D, Mm = make_values(rng, 300, 4)
        D, Mm = np.array(D), np.array(Mm)
        pairs = M.pair_table(MODELS, META)
        dd, md, _ = M.correlations(D, Mm)
        self.assertEqual(M.negatives(M.sim_fit(pairs, dd, md)), [])
        ddp, mdp, _ = M.correlations(D, M.planted(Mm, M.unique_parts(D), 1.0))
        self.assertTrue(M.negatives(M.sim_fit(pairs, ddp, mdp)))
        np.testing.assert_allclose(ddp, dd, atol=1e-15)

    def test_self_reader_formula(self):
        rng = np.random.default_rng(8)
        D = rng.normal(size=(4, 50))
        Mm = rng.normal(size=(1, 4, 50))
        c = 0.7
        dd, md, per = M.correlations(D, Mm)
        _, mdp, _ = M.correlations(D, M.planted(Mm, M.zrows(D), c))
        for a in range(4):
            for b in range(4):
                want = (per[0][a, b] + c * dd[a, b]) / math.sqrt(1 + c * c + 2 * c * per[0][b, b])
                self.assertAlmostEqual(mdp[a, b], want, places=12)


class Printed(unittest.TestCase):
    def test_texreg_reader(self):
        text = tex(["exp1(filtered)", "news"], [("Intercept", ["0.0322", "-0.4439^{*}"], ["0.0181", "0.1774"]),
                                                ("other", ["0.0504^{**}", None], ["0.0153", None])],
                   gof=[("AIC", ["295735.0400", "1.0000"])])
        t = M.parse_texreg(text)
        self.assertEqual(t["models"], ["exp1(filtered)", "news"])
        self.assertEqual(t["coef"]["Intercept"], [("0.0322", ""), ("-0.4439", "*")])
        self.assertEqual(t["coef"]["other"], [("0.0504", "**"), None])
        self.assertEqual(t["se"]["Intercept"], ["0.0181", "0.1774"])
        self.assertEqual(t["se"]["other"], ["0.0153", None])
        self.assertEqual(t["gof"]["AIC"], ["295735.0400", "1.0000"])
        with self.assertRaises(M.Refused):
            M.parse_texreg(text.replace("0.0322", "0.03x2"))

    def test_rounding_rules(self):
        self.assertEqual(M.compare_value(0.10264, "0.1026"), "rounded")
        self.assertEqual(M.compare_value(0.10266, "0.1027"), "rounded")
        self.assertEqual(M.compare_value(0.10266, "0.1026"), "cut")
        self.assertEqual(M.compare_value(-0.44386, "-0.4439"), "rounded")
        self.assertEqual(M.compare_value(-0.44386, "-0.4438"), "cut")
        self.assertIsNone(M.compare_value(0.1028, "0.1026"))
        self.assertEqual(M.at(-0.00001, 4), "0.0000")
        self.assertEqual(M.at(0.0035, 3), format(0.0035, ".3f"))
        self.assertEqual(M.stars(0.0009), "***")
        self.assertEqual(M.stars(0.001), "**")
        self.assertEqual(M.stars(0.0499), "*")
        self.assertEqual(M.stars(0.05), "")

    def test_fit_list(self):
        s = M.fit_list("head ", ["x" * 60] * 5)
        self.assertLessEqual(len(s), M.LIMIT)
        self.assertTrue(s.endswith("..."))


class Run(unittest.TestCase):
    def test_stream(self):
        a = M.Stream(SEED, "boot/e1").rng().integers(0, 1000, size=5)
        b = M.Stream(SEED, "boot/e1").rng().integers(0, 1000, size=5)
        c = M.Stream(SEED, "boot/news").rng().integers(0, 1000, size=5)
        np.testing.assert_array_equal(a, b)
        self.assertFalse(np.array_equal(a, c))

    def test_whole_run(self):
        with tempfile.TemporaryDirectory() as d:
            build(d, n1=80, n2=60)
            res = os.path.join(d, "results")
            with Patched(d):
                out, detail = M.run(SEED, inputs=d, results=res)
                again, _ = M.run(SEED, inputs=d, results=os.path.join(d, "again"))
                with self.assertRaises(M.Refused):
                    M.run("nothex", inputs=d, results=res)
            self.assertEqual(tuple(sorted(out)), tuple(sorted(M.OUTPUTS)))
            self.assertEqual(out, again)
            for k, v in out.items():
                self.assertIsInstance(v, (int, float, str), k)
                if isinstance(v, str):
                    self.assertLessEqual(len(v), M.LIMIT, k)
                if isinstance(v, float):
                    self.assertTrue(math.isfinite(v), k)
            self.assertIn(out["test_passed"], (0, 1))
            self.assertEqual(out["conditions_total"], 6)
            self.assertEqual(out["controls_total"], 6)
            for name in ("(1)", "(2)", "(3)", "(4)", "(6)"):
                self.assertTrue(next(v for k, v in detail["controls"].items() if k.startswith(name)), name)
            self.assertTrue(os.path.exists(os.path.join(res, "outputs.json")))
            self.assertTrue(os.path.exists(os.path.join(res, "detail.json")))
            self.assertEqual(out["printed_total"], len(detail["printed"]))


if __name__ == "__main__":
    unittest.main()
