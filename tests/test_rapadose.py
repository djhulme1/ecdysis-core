"""The rapamycin dose-and-sex recount on made-up data: which rows are kept, the design columns checked and anything
malformed refused; the Kaplan-Meier medians of the pooled mice with removed mice censored and counted; the gains and
the verdict, the female gain larger at every dose; with the real workbook (at inputs/ or in ITP_INPUTS), also Table 1
and the paper's p-values.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_rapadose", os.path.join(HERE, "..", "itp", "rapadose.py"))
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)

DESIGN = dict(R.DESIGN, ACA=("1000", "4"), MB=("28", "4"), **{"17aE2": ("4.8", "10")})


def row(site="TJL", sex="m", group="Rapa_mid", age="900", status="dead", dead="1", cohort="C2009", **kw):
    dose, start = DESIGN.get(group, ("0", None))
    r = {"cohort": cohort, "site": site, "sex": sex, "group": group, "age": age, "status": status, "dead": dead,
         "dose": dose, "age_initiation": start}
    r.update(kw)
    return r


def full(values):
    out = {(g, s, x): [(800, True)] for g in R.GROUPS for s in R.SITES for x in R.SEXES}
    out.update(values)
    return out


class Rows(unittest.TestCase):
    def test_the_four_groups_are_kept_and_the_other_arms_are_not(self):
        m = R.mice_from_rows([row(), row(group="Control", status="removed", dead="0", age="400"),
                              row(group="Rapa_hi", site="UT", sex="f"), row(group="ACA"), row(group="17aE2"),
                              row(group="MB")])
        self.assertEqual(m[("Rapa_mid", "TJL", "m")], [(900, True)])
        self.assertEqual(m[("Control", "TJL", "m")], [(400, False)])
        self.assertEqual(m[("Rapa_hi", "UT", "f")], [(900, True)])
        self.assertEqual(sum(len(v) for v in m.values()), 3)

    def test_malformed_rows_are_refused(self):
        for bad in (row(cohort="C2010"), row(site="XX"), row(sex="u"), row(age="900.5"), row(age=""),
                    row(status="dead", dead="0"), row(group="ACA", status="removed", dead="1"), row(group="Cana")):
            with self.subTest(bad=bad), self.assertRaises(R.Refused):
                R.mice_from_rows([bad])

    def test_a_kept_row_must_carry_its_groups_design(self):
        for bad in (row(dose="42"), row(age_initiation="20"), row(group="Rapa_lo", dose="14"),
                    row(group="Control", dose="14"), row(group="Control", age_initiation="9")):
            with self.subTest(bad=bad), self.assertRaises(R.Refused):
                R.mice_from_rows([bad])


class Pooling(unittest.TestCase):
    def test_kaplan_meier_of_the_pooled_mice_with_removed_mice_censored(self):
        values = {("Control", "TJL", "m"): [(100, True), (200, True)], ("Control", "UM", "m"): [(150, False)],
                  ("Control", "UT", "m"): [(300, True), (400, True)]}
        c = R.summary(full(values))["m"]["Control"]
        # at 100: 4/5; at 200: 4/5 * 2/3 = 8/15 (the removed mouse left the risk set at 150); at 300: 8/15 * 1/2
        self.assertEqual((c["mice"], c["dead"], c["median"], c["p90"]), (5, 4, 300, 400))

    def test_a_group_without_deaths_is_refused(self):
        with self.assertRaises(R.Refused):
            R.summary(full({("Rapa_lo", s, "f"): [(300, False)] for s in R.SITES}))


class Verdict(unittest.TestCase):
    def test_the_female_gain_must_be_larger_at_every_dose(self):
        ok = {"m_Rapa_lo": 0.03, "m_Rapa_mid": 0.13, "m_Rapa_hi": 0.23,
              "f_Rapa_lo": 0.16, "f_Rapa_mid": 0.21, "f_Rapa_hi": 0.26}
        self.assertEqual(R.verdict(ok)[0], 1)
        for g in R.DOSES:
            with self.subTest(g=g):
                self.assertEqual(R.verdict(dict(ok, **{f"f_{g}": ok[f"m_{g}"]}))[0], 0)     # equal is not larger

    def test_gains(self):
        s = R.summary(full({("Rapa_hi", x, "f"): [(1000, True)] for x in R.SITES}))
        g = R.gains(s)
        self.assertAlmostEqual(g["f_Rapa_hi"], 0.25)
        self.assertEqual(g["m_Rapa_hi"], 0.0)


class Refusals(unittest.TestCase):
    def test_wrong_input_hash_stops_the_run(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "inputs"))
            with open(os.path.join(d, "inputs", R.INPUT[0]), "wb") as f:
                f.write(b"not the workbook")
            with self.assertRaises(SystemExit):
                R.run(inputs=os.path.join(d, "inputs"), results=os.path.join(d, "results"))


def inputs_dir():
    d = os.environ.get("ITP_INPUTS") or os.path.join(HERE, "..", "inputs")
    return d if os.path.isfile(os.path.join(d, R.INPUT[0])) else None


@unittest.skipUnless(inputs_dir(), "the real workbook is not at inputs/ (or ITP_INPUTS)")
class RealData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out, cls.detail = R.run(inputs=inputs_dir(), results=cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_table_1(self):
        self.assertEqual(self.out["table1_matched"], 18)
        self.assertEqual(self.out["median_m"], "807/834/909/992")                   # all male numbers as printed
        self.assertEqual(self.out["p90_m"], "1094/1162/1180/1185")
        self.assertEqual(self.out["counts"], "m 300/156/156/156; f 280/136/136/136")
        self.assertEqual(self.out["p90_f"].split("/")[0], "1072")                   # printed 1159

    def test_the_registered_test(self):
        self.assertAlmostEqual(self.out["inc_median_m_hi"], 992 / 807 - 1, places=6)
        self.assertAlmostEqual(self.out["inc_median_f_hi"], 1131 / 891 - 1, places=6)
        self.assertEqual(self.out["test_passed"], 1)


if __name__ == "__main__":
    unittest.main()
