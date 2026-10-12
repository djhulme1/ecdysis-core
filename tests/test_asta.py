"""The astaxanthin and meclizine recount (itp/asta.py): the verdict at and either side of each of its four clauses;
each refusal of the rows (cohort, design, group, status, age); the tables' bookkeeping; and, with the claim's workbook
at inputs/ (or ASTA_INPUTS), the recount itself.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_asta", os.path.join(HERE, "..", "itp", "asta.py"))
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)

INPUTS = os.environ.get("ASTA_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = os.path.isfile(os.path.join(INPUTS, A.INPUT[0]))


def row(group="Asta", site="UM", sex="m", status="dead", dead="1", age="900", rx=None, start=None):
    rx_, start_ = A.DESIGN.get(group, ("1", "9"))
    return {"population": "UM-HET3", "cohort": "C2019", "site": site, "sex": sex, "id": "X", "group": group,
            "Rx(ppm)": rx if rx is not None else rx_, "age_initiation(mo)": start if start is not None else start_,
            "status": status, "dead": dead, "age(days)": age}


class Verdict(unittest.TestCase):
    def test_at_and_beside_each_clause(self):
        ok = {"Asta": 0.06, "Mec": 0.04}, {"Asta": 0.0499, "Mec": 0.0499}
        self.assertTrue(all(A.conditions(*ok).values()))
        for rises, ps in (({"Asta": 0.0599, "Mec": 0.04}, ok[1]), ({"Asta": 0.06, "Mec": 0.0399}, ok[1]),
                          (ok[0], {"Asta": 0.05, "Mec": 0.01}), (ok[0], {"Asta": 0.01, "Mec": 0.05})):
            with self.subTest(rises=rises, ps=ps):
                self.assertEqual(sum(A.conditions(rises, ps).values()), 3)


class Rows(unittest.TestCase):
    def test_reads_the_three_groups(self):
        mice, counts = A.mice_from_rows([row(), row(group="Control", age="800"), row(group="Mec", status="removed",
                                                                                     dead="0", age="700.0"),
                                         row(group="PBA")])
        self.assertEqual(mice[("Asta", "UM", "m")], [(900, True)])
        self.assertEqual(mice[("Mec", "UM", "m")], [(700, False)])
        self.assertEqual(counts["PBA"], 1)

    def test_refusals(self):
        for bad in (dict(row(), cohort="C2018"), dict(row(), population="B6"), row(rx="2000"), row(start="9"),
                    row(group="Placebo"), row(status="dead", dead="0"), row(age="900.5"), row(site="NIA"),
                    row(sex="x")):
            with self.subTest(bad=bad), self.assertRaises(A.Refused):
                A.mice_from_rows([bad])


class Tables(unittest.TestCase):
    def test_bookkeeping(self):
        self.assertEqual(sum(1 for k in A.TABLES if k[1] == "Pool"), 6)
        self.assertEqual(len(A.TABLES), 24)
        self.assertEqual(len(A.OUTPUTS), 19)


@unittest.skipUnless(HAVE, "the claim's workbook is not at inputs/ (or ASTA_INPUTS)")
class Recount(unittest.TestCase):
    def test_the_recount(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, detail = A.run("0" * 64, inputs=INPUTS, results=tmp)
        self.assertEqual(tuple(out), A.OUTPUTS)
        self.assertEqual(out["n_m"], "Control 311 (297 dead); Asta 156 (156 dead); Mec 155 (148 dead)")
        self.assertEqual((out["median_m_control"], out["median_m_asta"], out["median_m_mec"]), (814.0, 908.0, 881.5))
        self.assertAlmostEqual(out["rise_asta"], 908 / 814 - 1, places=6)
        self.assertAlmostEqual(out["logrank_p_asta"], 0.003004, places=6)
        self.assertAlmostEqual(out["logrank_p_mec"], 0.02699, places=5)
        self.assertEqual(out["tables_matched"], "Table 1: 10 of 18; Tables 2 to 4: 42 of 54")
        self.assertEqual((out["conditions_met"], out["test_passed"]), (4, 1))
        self.assertEqual(detail["input"]["groups"]["Control"], 595)

    def test_refuses_other_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(os.path.join(INPUTS, A.INPUT[0]), tmp)
            with open(os.path.join(tmp, A.INPUT[0]), "ab") as f:
                f.write(b"\0")
            with self.assertRaises(SystemExit):
                A.run("0" * 64, inputs=tmp, results=tmp)


if __name__ == "__main__":
    unittest.main()
