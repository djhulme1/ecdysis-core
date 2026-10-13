"""The ITP's 2007 cohort (itp/strong2013.py): the rows' checks and refusals, the verdict at and beside its condition,
and, with the workbook at inputs/ (or ITP_INPUTS), the cohort's counts.

Run with: python3 -m unittest tests.test_strong2013
"""

import importlib.util
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_strong2013", os.path.join(HERE, "..", "itp", "strong2013.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)
INPUTS = os.environ.get("ITP_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = os.path.isfile(os.path.join(INPUTS, M.INPUT[0]))


def row(**kw):
    r = {"population": "UM-HET3", "cohort": "C2007", "site": "UM", "sex": "f", "group": "GTE", "dose": "2000",
         "age_initiation": "4", "status": "dead", "dead": "1", "age": "900"}
    r.update(kw)
    return r


class Rows(unittest.TestCase):
    def test_accepts_and_refuses(self):
        mice = M.mice_from_rows([row(), row(group="Control", dose="0", age_initiation=None, status="removed", dead="0")])
        self.assertEqual(mice[("GTE", "UM", "f")], [(900, True)])
        self.assertEqual(mice[("Control", "UM", "f")], [(900, False)])
        for bad in (row(cohort="C2006"), row(group="Rapa"), row(dose="1000"), row(age_initiation="9"),
                    row(status="dead", dead="0"), row(age="900.5"), row(site="XX")):
            with self.subTest(bad=bad):
                with self.assertRaises(M.Refused):
                    M.mice_from_rows([bad])


class Verdict(unittest.TestCase):
    def test_at_and_beside(self):
        ps = {(a, x): 0.5 for a in M.AGENTS for x in M.SEXES}
        self.assertTrue(all(M.conditions(ps).values()))
        ps[("GTE", "f")] = 0.05
        self.assertTrue(all(M.conditions(ps).values()))
        ps[("GTE", "f")] = 0.0499
        self.assertFalse(all(M.conditions(ps).values()))


@unittest.skipUnless(HAVE, "the workbook is not at inputs/ (or ITP_INPUTS)")
class Cohort(unittest.TestCase):
    def test_counts(self):
        rows = M.rapa.read_rows(os.path.join(INPUTS, M.INPUT[0]), M.INPUT[1])
        mice = M.mice_from_rows(rows)
        self.assertEqual(len(rows), 2008)
        self.assertEqual(sum(len(mice[("Control", s, "m")]) for s in M.SITES), 294)
        self.assertEqual(sum(len(mice[("Res", s, "f")]) for s in M.SITES), 131)


if __name__ == "__main__":
    unittest.main()
