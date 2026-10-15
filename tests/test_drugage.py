"""Weight loss and lifespan (itp/drugage.py): the workbook reader, the selection, the plain regression and its
p-value against closed forms and against scipy's linregress, and the refusals, on workbooks and points made here.
None of the claim's regressions is computed.

Run with: python3 -m unittest tests.test_drugage
"""

import importlib.util
import io
import math
import os
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_drugage", os.path.join(HERE, "..", "itp", "drugage.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

try:
    import scipy  # noqa: F401
    HAVE_SCIPY = True
except ImportError:
    HAVE_SCIPY = False


def workbook(rows):
    """A minimal xlsx: the header and rows as shared strings or numbers."""
    shared, index = [], {}

    def sid(s):
        if s not in index:
            index[s] = len(shared)
            shared.append(s)
        return index[s]
    cols = "ABCDEFGHIJKLMNOPQ"
    xml_rows = []
    for i, row in enumerate(rows, start=1):
        cells = []
        for j, v in enumerate(row):
            ref = f"{cols[j]}{i}"
            if v is None:
                continue
            if isinstance(v, (int, float)):
                cells.append(f'<c r="{ref}"><v>{v}</v></c>')
            else:
                cells.append(f'<c r="{ref}" t="s"><v>{sid(v)}</v></c>')
        xml_rows.append(f'<row r="{i}">{"".join(cells)}</row>')
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    sheet = f'<worksheet xmlns="{ns}"><sheetData>{"".join(xml_rows)}</sheetData></worksheet>'
    sst = f'<sst xmlns="{ns}">' + "".join(f"<si><t>{s}</t></si>" for s in shared) + "</sst>"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/worksheets/sheet1.xml", sheet)
        z.writestr("xl/sharedStrings.xml", sst)
    return buf.getvalue()


def row(itp, sex, med, mx, w):
    r = ["drug", 1, itp, sex, med, "S", mx, "NS", w, "NS", 2, "A 2020", "10 ppm", 4, "life", "UM-HET3", None]
    return r


class Reader(unittest.TestCase):
    def test_reads_header_and_rows(self):
        data = workbook([M.HEADER, row("ITP", "M", 12.5, 8, -10), row("No", "F", "not available", 3, None)])
        header, rows = M.read_rows(data)
        self.assertEqual(header, M.HEADER)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["ITP?"], "ITP")
        self.assertEqual(M.number(rows[0][M.Y["median"]]), 12.5)
        self.assertIsNone(M.number(rows[1][M.Y["median"]]))
        self.assertIsNone(rows[1][M.X])

    def test_select(self):
        data = workbook([M.HEADER, row("ITP", "M", 12.5, 8, -10), row("ITP", "M+F", 5, 5, -5), row("ITP", "?", 5, 5, -5),
                         row("No", "M", 2, 1, -1), row("ITP", "M", "not available", 1, -3), row("ITP", "F", 4, 2, -20)])
        _, rows = M.read_rows(data)
        self.assertEqual(M.select(rows, True, "M", M.Y["median"]), [(-10.0, 12.5)])
        self.assertEqual(M.select(rows, True, "M", M.Y["max"]), [(-10.0, 8.0), (-3.0, 1.0)])
        self.assertEqual(M.select(rows, None, "M", M.Y["median"]), [(-10.0, 12.5), (-1.0, 2.0)])
        self.assertEqual(M.select(rows, True, "F", M.Y["median"]), [(-20.0, 4.0)])
        self.assertEqual(len(M.select(rows, True, None, M.Y["median"])), 4)   # both sexes: M+F and ? rows too
        self.assertIsNone(M.number("nan"))


class Regression(unittest.TestCase):
    def test_betainc_closed_forms(self):
        for x in (0.1, 0.37, 0.8):
            self.assertAlmostEqual(M.betainc(1, 1, x), x, places=12)
            self.assertAlmostEqual(M.betainc(3, 1, x), x ** 3, places=12)
            self.assertAlmostEqual(M.betainc(1, 4, x), 1 - (1 - x) ** 4, places=12)
        self.assertAlmostEqual(M.betainc(0.5, 0.5, 0.5), 0.5, places=12)

    def test_t_pvalues(self):
        # two-sided p of t with 1 df (Cauchy) and 2 df, by closed forms
        for t in (0.5, 1.0, 3.0):
            df = 1
            p = M.betainc(df / 2, 0.5, df / (df + t * t))
            self.assertAlmostEqual(p, 1 - 2 * math.atan(t) / math.pi, places=12)
            df = 2
            p = M.betainc(df / 2, 0.5, df / (df + t * t))
            self.assertAlmostEqual(p, 1 - t / math.sqrt(t * t + 2), places=12)

    def test_plain_regression(self):
        q = M.plain_regression([(0, 1), (1, 3), (2, 5.000001), (3, 7)])
        self.assertAlmostEqual(q["slope"], 2.0, places=5)
        self.assertLess(q["p"], 1e-6)
        q = M.plain_regression([(1, 4), (2, 1), (3, 5), (4, 2), (5, 6), (6, 3)])
        self.assertGreater(q["p"], 0.3)

    @unittest.skipUnless(HAVE_SCIPY, "scipy is in the check's image, not necessarily here")
    def test_against_linregress(self):
        import random
        rng = random.Random(4)
        for n in (5, 30, 120):
            pts = [(rng.uniform(-30, 10), 0) for _ in range(n)]
            pts = [(x, -0.5 * x + rng.gauss(0, 6)) for x, _ in pts]
            q, f = M.plain_regression(pts), M.regression(pts)
            self.assertTrue(M.close(q["slope"], f["slope"]))
            self.assertTrue(M.close(q["r2"], f["r2"]))
            self.assertTrue(M.close(q["p"], f["p"], 1e-7), (n, q["p"], f["p"]))


class Run(unittest.TestCase):
    def test_refused_seed(self):
        with self.assertRaises(M.Refused):
            M.run("nothex")

    def test_refused_hash(self):
        work = tempfile.mkdtemp()
        with open(os.path.join(work, M.INPUT[0]), "wb") as fh:
            fh.write(workbook([M.HEADER]))
        with self.assertRaises(M.Refused):
            M.run("ab" * 32, inputs=work, results=os.path.join(work, "results"))

    def test_test_length(self):
        self.assertLessEqual(len(M.TEST), 600)

    def test_rules(self):
        self.assertEqual(M.ALPHA, 0.05)
        self.assertEqual(M.PRINTED["median"], (-0.76, 0.52, 3.09e-11))
        self.assertEqual(len(M.HEADER), 17)


if __name__ == "__main__":
    unittest.main()
