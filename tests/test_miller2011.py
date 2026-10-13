"""Rapamycin from 9 months in the ITP's 2006 cohort (itp/miller2011.py): the rows' checks and refusals, the verdict at
and beside each condition, the independent Fisher enumeration, and, with the workbook at inputs/ (or ITP_INPUTS), the
cohort's counts.

Run with: python3 -m unittest tests.test_miller2011
"""

import importlib.util
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_miller2011", os.path.join(HERE, "..", "itp", "miller2011.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)
INPUTS = os.environ.get("ITP_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = os.path.isfile(os.path.join(INPUTS, M.INPUT[0]))


def row(**kw):
    r = {"population": "UM-HET3", "cohort": "C2006", "site": "UT", "sex": "m", "group": "Rapa", "dose": "14",
         "age_initiation": "9", "status": "dead", "dead": "1", "age": "950"}
    r.update(kw)
    return r


class Rows(unittest.TestCase):
    def test_accepts_and_refuses(self):
        mice = M.mice_from_rows([row(), row(group="Control", dose="0", age_initiation=None, status="removed", dead="0")])
        self.assertEqual(mice[("Rapa", "UT", "m")], [(950, True)])
        self.assertEqual(mice[("Control", "UT", "m")], [(950, False)])
        for bad in (row(cohort="C2007"), row(site="XX"), row(age="950.5"), row(status="dead", dead="0"),
                    row(group="Metformin"), row(dose="15"), row(group="Sim_lo", dose="12", age_initiation="9")):
            with self.subTest(bad=bad), self.assertRaises(M.Refused):
                M.mice_from_rows([bad])


class Verdict(unittest.TestCase):
    def test_at_and_beside(self):
        lr = {(s, x): 0.01 for s in M.SITES for x in M.SEXES}
        wa = {(s, x): ([[0, 0], [0, 0]], 0.01) for s in M.SITES for x in M.SEXES}
        rise = {"m": 0.05, "f": 0.09}
        self.assertTrue(all(M.conditions(lr, wa, rise).values()))
        self.assertFalse(all(M.conditions({**lr, ("UM", "f"): 0.05}, wa, rise).values()))
        self.assertFalse(all(M.conditions(lr, {**wa, ("TJL", "m"): ([[0, 0], [0, 0]], 0.0500)}, rise).values()))
        self.assertFalse(all(M.conditions(lr, wa, {"m": 0.0499, "f": 0.09}).values()))
        self.assertFalse(all(M.conditions(lr, wa, {"m": 0.05, "f": 0.0899}).values()))

    def test_fisher_enumeration(self):
        for t in ([[3, 1], [1, 3]], [[10, 2], [3, 15]], [[0, 50], [12, 38]], [[24, 76], [3, 97]]):
            with self.subTest(t=t):
                self.assertAlmostEqual(M.fisher_by_enumeration(t), M.cana.fisher_two_sided(t), places=12)


@unittest.skipUnless(HAVE, "the workbook is not at inputs/")
class Cohort(unittest.TestCase):
    def test_counts(self):
        rows = M.rapa.read_rows(os.path.join(INPUTS, M.INPUT[0]), M.INPUT[1])
        mice = M.mice_from_rows(rows)
        self.assertEqual(len(rows), 2172)
        self.assertEqual(sum(len(mice[(g, s, x)]) for g in ("Rapa",) for s in M.SITES for x in M.SEXES), 315)
        self.assertEqual(sum(len(mice[(g, s, x)]) for g in ("Control",) for s in M.SITES for x in M.SEXES), 614)


if __name__ == "__main__":
    unittest.main()
