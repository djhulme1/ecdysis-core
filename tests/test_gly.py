"""The glycine recount (itp/gly.py): the verdict at and either side of each of its six clauses; each refusal of the rows
(cohort, population, design, group, status, age, site, sex); the printed-precision comparison; the other readings of
the 90th percentile; the tables' bookkeeping; and, with the claim's workbook at inputs/ (or GLY_INPUTS), the recount.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_gly", os.path.join(HERE, "..", "itp", "gly.py"))
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)

INPUTS = os.environ.get("GLY_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = os.path.isfile(os.path.join(INPUTS, G.INPUT[0]))


def row(group="Gly", site="UM", sex="m", status="dead", dead="1", age="900", dose=None, start="keep"):
    dose_, start_ = G.DESIGN.get(group, ("60", "11"))
    return {"population": "UM-HET3", "cohort": "C2014", "site": site, "sex": sex, "id": "X", "group": group,
            "dose": dose if dose is not None else dose_, "age_initiation": start_ if start == "keep" else start,
            "status": status, "dead": dead, "age": age}


class Verdict(unittest.TestCase):
    def test_at_and_beside_each_clause(self):
        ok = ({"f": 0.02, "m": 0.02}, {"f": 0.0499, "m": 0.0499}, {"f": 0.0499, "m": 0.0499})
        self.assertEqual(sum(G.conditions(*ok).values()), 6)
        for k in range(3):
            for x in ("f", "m"):
                bad = [dict(d) for d in ok]
                bad[k][x] = 0.0199 if k == 0 else 0.05
                with self.subTest(clause=k, sex=x):
                    self.assertEqual(sum(G.conditions(*bad).values()), 5)


class Rows(unittest.TestCase):
    def test_reads_the_two_groups(self):
        mice, counts = G.mice_from_rows([row(), row(group="Control", age="800"),
                                         row(group="Gly", sex="f", status="removed", dead="0", age="700.0"),
                                         row(group="Inu")])
        self.assertEqual(mice[("Gly", "UM", "m")], [(900, True)])
        self.assertEqual(mice[("Control", "UM", "m")], [(800, True)])
        self.assertEqual(mice[("Gly", "UM", "f")], [(700, False)])
        self.assertEqual(counts["Inu"], 1)

    def test_refusals(self):
        for bad in (dict(row(), cohort="C2013"), dict(row(), population="B6"), row(dose="40000"), row(start="12"),
                    row(group="Control", start="9"), row(group="Placebo"), row(status="dead", dead="0"),
                    row(age="900.5"), row(age=""), row(site="NIA"), row(sex="x")):
            with self.subTest(bad=bad), self.assertRaises(G.Refused):
                G.mice_from_rows([bad])


class Pieces(unittest.TestCase):
    def test_as_printed(self):
        self.assertEqual(G.as_printed(0.01275, "0.013"), "0.013")
        self.assertEqual(G.as_printed(1.0, "1.00"), "1.00")
        self.assertEqual(G.as_printed(0.3135, "0.3"), "0.3")
        self.assertEqual(G.as_printed(0.000118, "0.00004"), "0.00012")

    def test_kaplan_meier_cut(self):
        ms = [(t, True) for t in range(1, 11)]
        self.assertEqual(G.km_cut(ms), 9)
        self.assertEqual(G.km_cut(ms + [(5, False)]), 10)    # a mouse removed at 5 leaves 0.109 surviving at 9

    def test_readings_agree_with_the_shared_rule(self):
        ctl = [(t, True) for t in range(700, 1100, 10)]
        trt = [(t, True) for t in range(720, 1180, 12)]
        self.assertEqual(G.wang_allison_by([(ctl, trt)], lambda ms: G.cana.quantile7([t for t, d in ms if d], 0.9)),
                         G.cana.wang_allison([(ctl, trt)]))


class Tables(unittest.TestCase):
    def test_bookkeeping(self):
        self.assertEqual(len(G.TABLE), 16)
        self.assertEqual(len(G.TABLE_P), 12)
        self.assertEqual(len(G.OUTPUTS), 20)


@unittest.skipUnless(HAVE, "the claim's workbook is not at inputs/ (or GLY_INPUTS)")
class Recount(unittest.TestCase):
    def test_the_recount(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, detail = G.run("0" * 64, inputs=INPUTS, results=tmp)
        self.assertEqual(tuple(out), G.OUTPUTS)
        self.assertEqual(out["n"], "f Control 280 (279 dead), Gly 136 (132 dead); m Control 300 (273 dead), Gly 156 (153 dead)")
        self.assertEqual((out["median_f_control"], out["median_f_gly"], out["median_m_control"], out["median_m_gly"]),
                         (897.0, 930.0, 832.0, 884.0))
        self.assertAlmostEqual(out["logrank_p_f"], 0.01667, places=5)
        self.assertAlmostEqual(out["logrank_p_m"], 0.002375, places=6)
        self.assertAlmostEqual(out["wa_p_f"], 0.2166, places=4)
        self.assertEqual(out["tables_matched"],
                         "counts 16 of 16; medians 14 of 16; P90 14 of 16; log-rank p 10 of 12; Wang-Allison p 3 of 12")
        self.assertEqual((out["conditions_met"], out["conditions_total"], out["test_passed"]), (5, 6, 0))
        self.assertEqual(detail["input"]["groups"]["Control"], 580)

    def test_refuses_other_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(os.path.join(INPUTS, G.INPUT[0]), tmp)
            with open(os.path.join(tmp, G.INPUT[0]), "ab") as f:
                f.write(b"\0")
            with self.assertRaises(SystemExit):
                G.run("0" * 64, inputs=tmp, results=tmp)


if __name__ == "__main__":
    unittest.main()
