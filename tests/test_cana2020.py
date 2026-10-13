"""Canagliflozin from 16 months in the ITP's 2020 cohort (itp/cana2020.py): the verdict at and beside each of its four
conditions; each refusal of the rows (cohort, population, site, sex, age, status, group, design, and a group where the
cohort did not give it); the medians, Kaplan-Meier medians and site-matched comparisons on small cohorts; and, with the
claim's workbook at inputs/ (or CANA2020_INPUTS), the recount.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_cana2020", os.path.join(HERE, "..", "itp", "cana2020.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

INPUTS = os.environ.get("CANA2020_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = os.path.isfile(os.path.join(INPUTS, M.INPUT[0]))


def row(group="Cana_16", site="UM", sex="m", status="dead", dead="1", age="900", design="keep"):
    dose, start = M.DESIGN.get(group, ("10000", "6")) if design == "keep" else design
    return {"population": "UM-HET3", "cohort": "C2020", "site": site, "sex": sex, "id": "X", "group": group,
            "Rx(ppm)": dose, "age_initiation(mo)": start, "status": status, "dead": dead, "age(days)": age}


class Verdict(unittest.TestCase):
    def test_at_and_beside_each_condition(self):
        ok = ({"m": 0.07, "f": -0.03}, {"m": 0.0499, "f": 0.0499})
        self.assertEqual(sum(M.conditions(*ok).values()), 4)
        for bad in (({"m": 0.0699, "f": -0.03}, ok[1]), ({"m": 0.07, "f": -0.0299}, ok[1]),
                    (ok[0], {"m": 0.05, "f": 0.0499}), (ok[0], {"m": 0.0499, "f": 0.05})):
            with self.subTest(bad=bad):
                self.assertEqual(sum(M.conditions(*bad).values()), 3)


class Rows(unittest.TestCase):
    def test_reads_the_three_groups(self):
        mice, counts = M.mice_from_rows([row(), row(group="Control", site="TJL", age="800.0"),
                                         row(group="Cana_6", site="TJL", sex="f", status="removed", dead="0"),
                                         row(group="THIO")])
        self.assertEqual(mice[("Cana_16", "UM", "m")], [(900, True)])
        self.assertEqual(mice[("Control", "TJL", "m")], [(800, True)])
        self.assertEqual(mice[("Cana_6", "TJL", "f")], [(900, False)])
        self.assertEqual(counts["THIO"], 1)

    def test_refusals(self):
        for bad in (dict(row(), cohort="C2019"), dict(row(), population="B6"), row(site="NIA"), row(sex="x"),
                    row(age="900.5"), row(age=""), row(status="dead", dead="0"), row(group="Placebo"),
                    row(design=("120", "16")), row(design=("180", "12")), row(group="Control", design=("0", "6")),
                    row(site="TJL"), row(group="Cana_6", site="UM")):
            with self.subTest(bad=bad), self.assertRaises(M.Refused):
                M.mice_from_rows([bad])


class Pieces(unittest.TestCase):
    def mice(self):
        rows = [row(group="Control", site=s, age=str(a)) for s in ("UM", "UT") for a in (800, 820, 840)]
        rows += [row(group="Control", site="TJL", age=str(a)) for a in (600, 610, 620)]
        rows += [row(site=s, age=str(a)) for s in ("UM", "UT") for a in (900, 920, 940)]
        return M.mice_from_rows(rows)[0]

    def test_site_matched_change(self):
        mice = self.mice()
        self.assertEqual(M.change(mice, "Cana_16", "m", ("UM", "UT")), (820, 920, 920 / 820 - 1))
        self.assertEqual(M.change(mice, "Cana_16", "m", ("UM", "UT"), M.SITES)[:2], (800, 920))   # TJL pulls it down
        self.assertLess(M.logrank(mice, "Cana_16", "m", ("UM", "UT")), 0.05)

    def test_kaplan_meier_median(self):
        self.assertEqual(M.km_median([(t, True) for t in (1, 2, 3, 4)]), 2)          # survival 0.5 at 2
        self.assertEqual(M.km_median([(1, True), (2, False), (3, True), (4, True)]), 3)
        with self.assertRaises(M.Refused):
            M.km_median([(1, True), (2, False), (3, False)])

    def test_alive_at(self):
        mice = self.mice()
        self.assertEqual(M.alive_at(mice, 830)[("Control", "UM", "m")], [(840, True)])


@unittest.skipUnless(HAVE, "the claim's workbook is not at inputs/ (or CANA2020_INPUTS)")
class Recount(unittest.TestCase):
    def test_the_recount(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, detail = M.run("0" * 64, inputs=INPUTS, results=tmp)
        self.assertEqual(tuple(out), M.OUTPUTS)
        self.assertEqual(out["n"], "m Control 201 (194 dead), Cana_16 102 (100 dead); f Control 180 (179 dead), "
                                   "Cana_16 92 (91 dead) (UM and UT)")
        self.assertEqual((out["median_m_control"], out["median_m_cana"], out["median_f_control"], out["median_f_cana"]),
                         (833.5, 931.5, 894.0, 851.0))
        self.assertAlmostEqual(out["logrank_p_m"], 0.02295, places=5)
        self.assertAlmostEqual(out["logrank_p_f"], 0.03087, places=5)
        self.assertEqual((out["conditions_met"], out["conditions_total"], out["test_passed"]), (4, 4, 1))
        self.assertEqual(detail["input"]["groups"]["Control"], 575)

    def test_refuses_other_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(os.path.join(INPUTS, M.INPUT[0]), tmp)
            with open(os.path.join(tmp, M.INPUT[0]), "ab") as f:
                f.write(b"\0")
            with self.assertRaises(SystemExit):
                M.run("0" * 64, inputs=tmp, results=tmp)


if __name__ == "__main__":
    unittest.main()
