"""Canagliflozin from 6 months in the ITP's 2020 cohort (itp/cana2020_6.py): the verdict at and beside each of its three
conditions; the 6-month group refused away from the Jackson Laboratory; the 90th percentile of the dead; and, with the
claim's workbook at inputs/ (or CANA2020_INPUTS), the recount.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_cana2020_6", os.path.join(HERE, "..", "itp", "cana2020_6.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

INPUTS = os.environ.get("CANA2020_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = os.path.isfile(os.path.join(INPUTS, M.INPUT[0]))


def row(group="Cana_6", site="TJL", sex="m", age="900"):
    dose, start = M.c20.DESIGN[group]
    return {"population": "UM-HET3", "cohort": "C2020", "site": site, "sex": sex, "id": "X", "group": group,
            "Rx(ppm)": dose, "age_initiation(mo)": start, "status": "dead", "dead": "1", "age(days)": age}


class Verdict(unittest.TestCase):
    def test_at_and_beside_each_condition(self):
        ok = ({"m": 0.0001, "f": -0.2}, {"m": 0.0499, "f": 0.05})
        self.assertEqual(sum(M.conditions(*ok).values()), 3)
        for bad in (({"m": 0.0, "f": -0.2}, ok[1]), (ok[0], {"m": 0.05, "f": 0.05}),
                    (ok[0], {"m": 0.0499, "f": 0.0499})):
            with self.subTest(bad=bad):
                self.assertEqual(sum(M.conditions(*bad).values()), 2)


class Rows(unittest.TestCase):
    def test_the_six_month_group_only_at_the_jackson_laboratory(self):
        mice, _ = M.c20.mice_from_rows([row(), row(group="Control", age="800")])
        self.assertEqual(mice[("Cana_6", "TJL", "m")], [(900, True)])
        for site in ("UM", "UT"):
            with self.subTest(site=site), self.assertRaises(M.Refused):
                M.c20.mice_from_rows([row(site=site)])

    def test_ninetieth_percentile_of_the_dead(self):
        ms = [(t, True) for t in range(1, 11)] + [(50, False)]
        self.assertEqual(M.p90(ms), 9)                                  # the least age by which 90% of the dead died


@unittest.skipUnless(HAVE, "the claim's workbook is not at inputs/ (or CANA2020_INPUTS)")
class Recount(unittest.TestCase):
    def test_the_recount(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, detail = M.run("0" * 64, inputs=INPUTS, results=tmp)
        self.assertEqual(tuple(out), M.OUTPUTS)
        self.assertEqual(out["n"], "m Control 102 (99 dead), Cana_6 60 (52 dead); f Control 92 (92 dead), "
                                   "Cana_6 44 (44 dead) (TJL)")
        self.assertEqual((out["median_m_control"], out["median_m_cana"], out["median_f_control"], out["median_f_cana"]),
                         (811.0, 899.0, 928.0, 897.0))
        self.assertAlmostEqual(out["logrank_p_m"], 0.02088, places=5)
        self.assertAlmostEqual(out["logrank_p_f"], 0.8977, places=4)
        self.assertEqual((out["conditions_met"], out["conditions_total"], out["test_passed"]), (3, 3, 1))


if __name__ == "__main__":
    unittest.main()
