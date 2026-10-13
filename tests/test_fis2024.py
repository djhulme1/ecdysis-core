"""Fisetin and four other agents in the ITP's 2018 and 2019 cohorts (itp/fis2024.py): the rows' checks and refusals
in each cohort's spelling, the verdict at and beside its condition in both directions, and, with the workbooks at
inputs/ (or ITP_INPUTS), the cohorts' counts.

Run with: python3 -m unittest tests.test_fis2024
"""

import importlib.util
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_fis2024", os.path.join(HERE, "..", "itp", "fis2024.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)
INPUTS = os.environ.get("ITP_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = all(os.path.isfile(os.path.join(INPUTS, n)) for n, _, _ in M.INPUTS.values())


def row(**kw):
    r = {"population": "UM-HET3", "cohort": "C2018", "site": "UM", "sex": "m", "group": "Fis_On", "Rx(ppm)": "600",
         "age_initiation(mo)": "20 (continuous)", "status": "dead", "dead": "1", "age(days)": "880"}
    r.update(kw)
    return r


class Rows(unittest.TestCase):
    def test_accepts_and_refuses(self):
        mice = M.mice_from_rows([row(), row(group="Control", **{"Rx(ppm)": "0", "age_initiation(mo)": "NA"},
                                            status="removed", dead="0")], "C2018")
        self.assertEqual(mice[("Fis_On", "UM", "m")], [(880, True)])
        self.assertEqual(mice[("Control", "UM", "m")], [(880, False)])
        for bad in (row(cohort="C2019"), row(site="JAX"), row(**{"age(days)": "88.5"}), row(dead="0"),
                    row(group="PBA", **{"Rx(ppm)": "1000", "age_initiation(mo)": "9"}),
                    row(**{"age_initiation(mo)": "20"}), row(group="SG1002", **{"Rx(ppm)": "240", "age_initiation(mo)": "6"})):
            with self.subTest(bad=bad), self.assertRaises(M.Refused):
                M.mice_from_rows([bad], "C2018")
        ok19 = row(cohort="C2019", group="SG1002", **{"Rx(ppm)": "240", "age_initiation(mo)": "6"})
        self.assertEqual(M.mice_from_rows([ok19], "C2019")[("SG1002", "UM", "m")], [(880, True)])


class Verdict(unittest.TestCase):
    def test_at_and_beside(self):
        keys = [(c, g, x) for c, g in M.TESTED for x in M.SEXES]
        ps = {k: 0.5 for k in keys}
        oes = {k: -1.0 for k in keys}
        self.assertTrue(all(M.conditions(ps, oes).values()))
        k = ("C2018", "Fis_On", "f")
        self.assertTrue(all(M.conditions({**ps, k: 0.05}, oes).values()))                      # at the line
        self.assertFalse(all(M.conditions({**ps, k: 0.0499}, oes).values()))                   # longer, significant
        d = ("C2019", "PBA", "f")
        self.assertTrue(all(M.conditions({**ps, d: 0.01}, {**oes, d: 9.0}).values()))           # shorter


@unittest.skipUnless(HAVE, "the workbooks are not at inputs/")
class Cohorts(unittest.TestCase):
    def test_counts(self):
        for c, (name, sha, n) in M.INPUTS.items():
            rows = M.rapa.read_rows(os.path.join(INPUTS, name), sha)
            mice = M.mice_from_rows(rows, c)
            self.assertEqual(len(rows), n)
            self.assertEqual(sum(len(v) for v in mice.values()), n)


if __name__ == "__main__":
    unittest.main()
