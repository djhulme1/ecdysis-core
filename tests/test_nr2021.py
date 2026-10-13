"""Nicotinamide riboside and three other agents in the ITP's 2016 cohort (itp/nr2021.py): the rows' checks and
refusals, the verdict at and beside its condition in both directions, and, with the workbook at inputs/ (or
ITP_INPUTS), the cohort's counts.

Run with: python3 -m unittest tests.test_nr2021
"""

import importlib.util
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_nr2021", os.path.join(HERE, "..", "itp", "nr2021.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)
INPUTS = os.environ.get("ITP_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = os.path.isfile(os.path.join(INPUTS, M.INPUT[0]))


def row(**kw):
    r = {"population": "UM-HET3", "cohort": "C2016", "site": "TJL", "sex": "f", "group": "NR", "dose": "1000",
         "age_initiation": "8", "status": "dead", "dead": "1", "age": "900"}
    r.update(kw)
    return r


class Rows(unittest.TestCase):
    def test_accepts_and_refuses(self):
        mice = M.mice_from_rows([row(), row(group="Control", dose="0", age_initiation=None, status="removed", dead="0"),
                                 row(group="17aE2_16m", dose="14.4", age_initiation="16", sex="m")])
        self.assertEqual(mice[("NR", "TJL", "f")], [(900, True)])
        self.assertEqual(mice[("Control", "TJL", "f")], [(900, False)])
        for bad in (row(cohort="C2015"), row(site="XX"), row(age="12.5"), row(status="removed", dead="1"),
                    row(group="Rapa"), row(dose="900"), row(group="GGA", dose="600", age_initiation="8"),
                    row(group="17aE2_20m", dose="14.4", age_initiation="20", sex="f")):
            with self.subTest(bad=bad), self.assertRaises(M.Refused):
                M.mice_from_rows([bad])


class Verdict(unittest.TestCase):
    def test_at_and_beside(self):
        keys = [(a, x) for a in M.AGENTS for x in M.SEXES]
        ps = {k: 0.5 for k in keys}
        oes = {k: -1.0 for k in keys}
        self.assertTrue(all(M.conditions(ps, oes).values()))
        self.assertTrue(all(M.conditions({**ps, ("NR", "f"): 0.05}, oes).values()))         # at the line: not below
        self.assertFalse(all(M.conditions({**ps, ("NR", "f"): 0.0499}, oes).values()))      # longer, significant
        self.assertTrue(all(M.conditions({**ps, ("GGA", "m"): 0.001}, {**oes, ("GGA", "m"): 4.0}).values()))  # shorter


@unittest.skipUnless(HAVE, "the workbook is not at inputs/")
class Cohort(unittest.TestCase):
    def test_counts(self):
        rows = M.rapa.read_rows(os.path.join(INPUTS, M.INPUT[0]), M.INPUT[1])
        mice = M.mice_from_rows(rows)
        self.assertEqual(len(rows), 2382)
        self.assertEqual(sum(len(mice[("NR", s, x)]) for s in M.SITES for x in M.SEXES), 292)
        self.assertEqual(sum(len(mice[("Control", s, x)]) for s in M.SITES for x in M.SEXES), 607)


if __name__ == "__main__":
    unittest.main()
