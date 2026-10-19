"""Richardson et al. 2021 (dr/richardson2021.py): the workbook reader on a workbook made here in the Prism layout (two
halves, a contiguous run of mice, one diet cell per row) and its refusals; the Kaplan-Meier curve in exact fractions,
Prism's median (its FAQ example) and the standard one; the log-rank and Gehan-Breslow-Wilcoxon tests against a hand
computation and, where installed, statsmodels; the percentiles and the rounding rule; the frailty reader; the
conditions on results made up here; and the outputs and the seed refused. Nothing here reads the claim's workbook, so
none of the test's quantities is computed.

Run with: python3 -m unittest discover -s tests -p test_richardson2021.py
"""

import hashlib
import importlib.util
import math
import os
import tempfile
import unittest
import zipfile
from fractions import Fraction
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("dr_richardson2021", os.path.join(HERE, "..", "dr", "richardson2021.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "ab" * 32


def col(j):
    s = ""
    j += 1
    while j:
        j, r = divmod(j - 1, 26)
        s = chr(65 + r) + s
    return s


def make_xlsx(path, sheets):
    """A minimal workbook: each sheet a list of rows, each cell a str (inline string), a number or None."""
    with zipfile.ZipFile(path, "w") as z:
        names = list(sheets)
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/'
                   'package/2006/content-types"></Types>')
        wb = ['<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
              'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>']
        rels = ['<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
                'relationships">']
        for k, name in enumerate(names, 1):
            wb.append(f'<sheet name="{escape(name)}" sheetId="{k}" r:id="rId{k}"/>')
            rels.append(f'<Relationship Id="rId{k}" Type="worksheet" Target="worksheets/sheet{k}.xml"/>')
            rows = []
            for i, row in enumerate(sheets[name], 1):
                cells = []
                for j, v in enumerate(row):
                    if v is None:
                        continue
                    ref = f"{col(j)}{i}"
                    if isinstance(v, str):
                        cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(v)}</t></is></c>')
                    else:
                        cells.append(f'<c r="{ref}"><v>{v}</v></c>')
                rows.append(f'<row r="{i}">{"".join(cells)}</row>')
            z.writestr(f"xl/worksheets/sheet{k}.xml",
                       '<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/'
                       f'main"><sheetData>{"".join(rows)}</sheetData></worksheet>')
        wb.append("</sheets></workbook>")
        rels.append("</Relationships>")
        z.writestr("xl/workbook.xml", "".join(wb))
        z.writestr("xl/_rels/workbook.xml.rels", "".join(rels))


def pinned(path):
    with open(path, "rb") as f:
        data = f.read()
    return hashlib.sha256(data).hexdigest(), len(data)


class Reader(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.saved = (dict(M.CAPTION_N), dict(M.HALF_LABEL))
        M.CAPTION_N["Fake"] = {"f": {"Control": 3, "Low BCAA": 2}, "m": {"Control": 2, "Low BCAA": 1}}
        M.HALF_LABEL["Fake"] = ("Females", "Males")

    def tearDown(self):
        M.CAPTION_N.clear()
        M.CAPTION_N.update(self.saved[0])
        M.HALF_LABEL.clear()
        M.HALF_LABEL.update(self.saved[1])

    def table(self, extra=None):
        rows = [["Females", None, None, None, None, "Males"],
                ["Lifespan", "Control", "Low\nBCAA", None, None, "Lifespan", "Control", "Low BCAA"],
                [100, 1, None, None, None, 300, 1],
                [110, None, 0, None, None, 310, None, 1],
                [120, 0, None, None, None, 320, 0],
                [130, None, 1],
                [140, 1],
                ["A caption"]]
        if extra:
            rows = extra(rows)
        path = os.path.join(self.dir, "w.xlsx")
        make_xlsx(path, {"Fake": rows})
        sha, size = pinned(path)
        return M.read_workbook(path, sha, size)["Fake"]

    def test_halves(self):
        h = M.halves(self.table(), "Fake")
        self.assertEqual(h["f"]["Control"], [(100, True), (120, False), (140, True)])
        self.assertEqual(h["f"]["Low BCAA"], [(110, False), (130, True)])
        self.assertEqual(h["m"], {"Control": [(300, True), (320, False)], "Low BCAA": [(310, True)]})

    def test_refusals(self):
        def two_cells(rows):
            rows[2] = [100, 1, 1, None, None, 300, 1]
            return rows

        def half_day(rows):
            rows[3] = [110.5, None, 0, None, None, 310, None, 1]
            return rows

        def gap(rows):
            return rows[:5] + [[None]] * 0 + [["note"]] + rows[5:]

        for bad in (two_cells, half_day, gap):
            with self.assertRaises(M.Refused):
                M.halves(self.table(bad), "Fake")
        M.CAPTION_N["Fake"]["f"]["Control"] = 4
        with self.assertRaises(M.Refused):
            M.halves(self.table(), "Fake")
        path = os.path.join(self.dir, "x.xlsx")
        make_xlsx(path, {"Fake": [["x"]]})
        with self.assertRaises(M.Refused):
            M.read_workbook(path, "0" * 64, 1)


class Survival(unittest.TestCase):
    def test_km_and_medians(self):
        faq = [(5, True), (9, True), (17, True), (20, True)]
        self.assertEqual(M.km(faq), [(5, Fraction(3, 4)), (9, Fraction(1, 2)), (17, Fraction(1, 4)), (20, 0)])
        self.assertEqual(M.prism_quantile(faq, Fraction(1, 2)), 13)
        self.assertEqual(M.standard_quantile(faq, Fraction(1, 2)), 9)
        cens = [(1, True), (2, False), (3, True), (4, True)]          # S: 3/4, then 3/8 at 3
        self.assertEqual(M.km(cens), [(1, Fraction(3, 4)), (3, Fraction(3, 8)), (4, 0)])
        self.assertEqual(M.prism_quantile(cens, Fraction(1, 2)), 3)
        self.assertIsNone(M.prism_quantile([(1, True), (2, False), (3, False)], Fraction(1, 2)))
        self.assertIsNone(M.prism_quantile([(1, True), (2, True), (3, False), (4, False)], Fraction(1, 2)))
        self.assertEqual(M.prism_quantile(faq, Fraction(1, 4)), Fraction(37, 2))

    def test_logrank_by_hand(self):
        # deaths at 1 (A), 2 (B), 3 (A); censored B at 4.
        a = [(1, True), (3, True)]
        b = [(2, True), (4, False)]
        # t=1: n=4, d=1, nb=2: O-E = -1/2, V = 1*(1/2)(1/2)*3/3 = 1/4
        # t=2: n=3, d=1, nb=2, db=1: O-E += 1 - 2/3 = 1/3, V += (2/3)(1/3) = 2/9
        # t=3: n=2, d=1, nb=1, db=0: O-E += -1/2, V += 1/4
        p, oe = M.weighted(a, b, "logrank")
        self.assertEqual(oe, Fraction(-1, 2) + Fraction(1, 3) - Fraction(1, 2))
        v = Fraction(1, 4) + Fraction(2, 9) + Fraction(1, 4)
        self.assertAlmostEqual(p, math.erfc(math.sqrt(float(oe * oe / v) / 2)), places=15)
        pg, oeg = M.weighted(a, b, "gbw")
        self.assertEqual(oeg, 4 * Fraction(-1, 2) + 3 * Fraction(1, 3) + 2 * Fraction(-1, 2))
        vg = 16 * Fraction(1, 4) + 9 * Fraction(2, 9) + 4 * Fraction(1, 4)
        self.assertAlmostEqual(pg, math.erfc(math.sqrt(float(oeg * oeg / vg) / 2)), places=15)
        same = [(5, True), (7, False), (9, True)]
        self.assertEqual(M.weighted(same, list(same), "logrank")[0], 1.0)

    def test_against_statsmodels(self):
        if importlib.util.find_spec("statsmodels") is None:
            self.skipTest("no statsmodels")
        for k in range(4):
            a, b = M.synthetic(SEED, k)
            self.assertAlmostEqual(M.weighted(a, b, "logrank")[0], M.statsmodels_p(a, b, None), places=9)
            self.assertAlmostEqual(M.weighted(a, b, "gbw")[0], M.statsmodels_p(a, b, "gb"), places=9)

    def test_against_scipy(self):
        try:
            from scipy import stats
            stats.logrank, stats.ecdf  # noqa: B018
        except (ImportError, AttributeError):
            self.skipTest("no scipy 1.11")
        for k in range(4):
            a, b = M.synthetic(SEED, k)
            self.assertAlmostEqual(M.weighted(a, b, "logrank")[0], M.scipy_logrank_p(a, b), places=9)
            self.assertTrue(M.scipy_km_agrees(a))
            self.assertTrue(M.scipy_km_agrees(b))


class Beside(unittest.TestCase):
    def test_percentiles_and_rounding(self):
        self.assertEqual(M.nearest_rank([1, 2, 3, 4], Fraction(3, 4)), 3)
        self.assertEqual(M.nearest_rank([1, 2, 3, 4, 5], Fraction(3, 4)), 4)
        ms = [(10, True), (20, False), (30, True), (40, True), (50, True)]
        self.assertEqual(M.max75(ms, "deaths"), 40)
        self.assertEqual(M.max75(ms, "all"), 40)
        self.assertTrue(M.rounds_to(0.03702, 0.037))
        self.assertFalse(M.rounds_to(0.0376, 0.037))
        self.assertTrue(M.rounds_to(0.00984, 0.0098))
        self.assertTrue(M.rounds_to(Fraction(3183, 100) + Fraction(1, 1000), 31.83))
        self.assertTrue(M.rounds_to(-14.6, -14.6))
        self.assertFalse(M.rounds_to(None, 0.5))

    def test_frailty_reader(self):
        d = tempfile.mkdtemp()
        rows = [["Age", "16 months", None, "18 months", None],
                ["Category", "Control", "Low BCAA", "Control", "Low BCAA"],
                ["Integument"],
                ["Alopecia", 0.5, 0.25, 0.5, 0.5],
                ["Kyphosis", 0.0, 0.25, 1.0, 0.0],
                ["Supplemental Table 9: Female frailty scores (lifelong intervention)"],
                ["Frailty scores presented by index measured over time."]]
        path = os.path.join(d, "f.xlsx")
        make_xlsx(path, {"Table S9": rows})
        sha, size = pinned(path)
        order, means = M.frailty_means(M.read_workbook(path, sha, size)["Table S9"], "Table S9")
        self.assertEqual(order, ["16 months", "18 months"])
        self.assertEqual(means[("16 months", "Control")], Fraction(1, 4))
        self.assertEqual(means[("18 months", "Low BCAA")], Fraction(1, 4))


class Conditions(unittest.TestCase):
    def results(self, a_med=(69, 37), a_p=0.01, a_oe=-1, b_med=(178, 167), b_p=0.03, b_oe=-1, c_med=(994, 754),
                c_p=0.04, c_oe=-2, d_med=(700, 697), d_p=0.7, d_oe=1):
        def r(med, p, oe):
            return {"median": tuple(Fraction(x) for x in med), "logrank_p": p, "logrank_oe": oe, "gbw_p": p,
                    "gbw_oe": oe}
        return {"lmna_f/Low BCAA": r(a_med, a_p, a_oe), "g609g/Low BCAA": r(b_med, b_p, b_oe),
                "wt_m/Low BCAA": r(c_med, c_p, c_oe), "wt_f/Low BCAA": r(d_med, d_p, d_oe)}

    def test_conditions(self):
        c = M.conditions(self.results())
        self.assertEqual((len(c), sum(c.values())), (4, 4))
        self.assertEqual(sum(M.conditions(self.results(c_med=(940, 754))).values()), 3)   # a 24.7% gain
        self.assertEqual(sum(M.conditions(self.results(c_med=(943, 754))).values()), 4)   # 25.06%
        self.assertEqual(sum(M.conditions(self.results(a_p=0.06)).values()), 3)
        self.assertEqual(sum(M.conditions(self.results(b_oe=1)).values()), 3)
        self.assertEqual(sum(M.conditions(self.results(d_p=0.01, d_oe=-1)).values()), 3)
        self.assertEqual(sum(M.conditions(self.results(d_p=0.01, d_oe=1)).values()), 4)
        self.assertEqual(sum(M.conditions(self.results(d_med=(880, 697))).values()), 3)


class Outputs(unittest.TestCase):
    def test_outputs_and_refusal(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)
        self.assertLessEqual(len(M.TEST), 600)
        with self.assertRaises(M.Refused):
            M.run("not a seed", results=tempfile.mkdtemp())


if __name__ == "__main__":
    unittest.main()
