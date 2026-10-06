"""The ITP recount on made-up data: Kaplan-Meier quantiles with censoring, the log-rank and Wang-Allison
tests at their extremes, and the workbook reader on a minimal workbook.

Run with: python3 -m unittest discover -s tests
"""

import hashlib
import io
import os
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "itp"))
import rapa  # noqa: E402


def workbook(rows):
    cells = []
    for i, row in enumerate(rows, start=1):
        cs = []
        for j, v in enumerate(row):
            ref = "ABCDEFGHIJK"[j] + str(i)
            if isinstance(v, str):
                cs.append(f'<c r="{ref}" t="inlineStr"><is><t>{v}</t></is></c>')
            else:
                cs.append(f'<c r="{ref}"><v>{v}</v></c>')
        cells.append(f'<row r="{i}">' + "".join(cs) + "</row>")
    sheet = ('<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             "<sheetData>" + "".join(cells) + "</sheetData></worksheet>")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return out.getvalue()


class Survival(unittest.TestCase):
    def test_quantiles_without_censoring_are_order_statistics(self):
        mice = [(t, True) for t in range(1, 11)]
        self.assertEqual(rapa.km_quantile(mice, 0.5), 5)
        self.assertEqual(rapa.km_quantile(mice, 0.9), 9)

    def test_a_censored_mouse_lowers_the_risk_set_not_survival(self):
        mice = [(1, True), (2, False), (3, True), (4, True)]
        # S(1) = 3/4; at 3, risk set 2: S = 3/4 * 1/2 = 3/8; at 4: 0.
        self.assertEqual(rapa.km_quantile(mice, 0.5), 3)
        self.assertEqual(rapa.km_quantile(mice, 0.9), 4)

    def test_identical_groups_give_no_evidence_and_separated_ones_strong_evidence(self):
        a = [(t, True) for t in range(100, 200)]
        self.assertGreater(rapa.logrank_p(a, list(a)), 0.99)
        b = [(t + 150, True) for t in range(100, 200)]
        self.assertLess(rapa.logrank_p(b, a), 1e-10)
        p, rows = rapa.wang_allison_p(b, a)
        self.assertLess(p, 1e-4)
        self.assertEqual(rows[1][0], 0)

    def test_the_workbook_reader_takes_inline_strings_and_numbers(self):
        data = workbook([["group", "sex", "age", "dead"], ["Control", "f", 900, 1], ["Rapa", "m", 1001, 0]])
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "w.xlsx")
            open(p, "wb").write(data)
            rows = rapa.read_rows(p, hashlib.sha256(data).hexdigest())
            self.assertEqual(rows, [{"group": "Control", "sex": "f", "age": "900", "dead": "1"},
                                    {"group": "Rapa", "sex": "m", "age": "1001", "dead": "0"}])
            with self.assertRaises(SystemExit):
                rapa.read_rows(p, "0" * 64)


if __name__ == "__main__":
    unittest.main()
