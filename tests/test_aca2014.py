"""The 2014 acarbose recount on made-up data: which rows are kept, the design columns checked and anything malformed
refused; the Kaplan-Meier medians and 90th percentiles of the pooled mice and of each site, removed mice censored and
counted; the gains as exact fractions and the verdict's three conditions at their edges; Table 1's 96 numbers; with the
real workbook (at inputs/ or in ITP_INPUTS), also Table 1 and the paper's p-values.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import os
import tempfile
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_aca2014", os.path.join(HERE, "..", "itp", "aca2014.py"))
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)

DESIGN = dict(A.DESIGN, Rapa_lo=("4.7", "9"), Rapa_mid=("14", "9"), Rapa_hi=("42", "9"))


def row(site="TJL", sex="m", group="ACA", age="900", status="dead", dead="1", cohort="C2009", **kw):
    dose, start = DESIGN.get(group, ("0", None))
    r = {"cohort": cohort, "site": site, "sex": sex, "group": group, "age": age, "status": status, "dead": dead,
         "dose": dose, "age_initiation": start}
    r.update(kw)
    return r


def full(values):
    out = {(g, s, x): [(800, True)] for g in A.GROUPS for s in A.SITES for x in A.SEXES}
    out.update(values)
    return out


class Rows(unittest.TestCase):
    def test_the_four_groups_are_kept_and_rapamycin_is_not(self):
        m = A.mice_from_rows([row(), row(group="Control", status="removed", dead="0", age="400"),
                              row(group="17aE2", site="UT", sex="f"), row(group="MB", site="UM"),
                              row(group="Rapa_lo"), row(group="Rapa_mid"), row(group="Rapa_hi")])
        self.assertEqual(m[("ACA", "TJL", "m")], [(900, True)])
        self.assertEqual(m[("Control", "TJL", "m")], [(400, False)])
        self.assertEqual(m[("17aE2", "UT", "f")], [(900, True)])
        self.assertEqual(m[("MB", "UM", "m")], [(900, True)])
        self.assertEqual(sum(len(v) for v in m.values()), 4)

    def test_malformed_rows_are_refused(self):
        for bad in (row(cohort="C2010"), row(site="XX"), row(sex="u"), row(age="900.5"), row(age=""),
                    row(status="dead", dead="0"), row(group="Rapa_lo", status="removed", dead="1"),
                    row(group="Cana")):
            with self.subTest(bad=bad), self.assertRaises(A.Refused):
                A.mice_from_rows([bad])

    def test_a_kept_row_must_carry_its_groups_design(self):
        for bad in (row(dose="400"), row(age_initiation="8"), row(group="17aE2", age_initiation="4"),
                    row(group="MB", dose="4.8"), row(group="Control", dose="1000"),
                    row(group="Control", age_initiation="4")):
            with self.subTest(bad=bad), self.assertRaises(A.Refused):
                A.mice_from_rows([bad])


class Statistics(unittest.TestCase):
    def test_kaplan_meier_pooled_and_by_site_with_removed_mice_censored(self):
        values = {("Control", "TJL", "m"): [(100, True), (200, True)],
                  ("Control", "UM", "m"): [(150, False), (250, True)],
                  ("Control", "UT", "m"): [(300, True), (400, True)]}
        c = A.summary(full(values))["m"]["Control"]
        # pooled: at 100, 5/6; at 200, 5/6 * 3/4 (the removed mouse left the risk set at 150); at 250, 5/12; at 400, 0
        self.assertEqual((c["Pooled"]["mice"], c["Pooled"]["dead"], c["Pooled"]["median"], c["Pooled"]["p90"]),
                         (6, 5, 250, 400))
        self.assertEqual((c["TJL"]["median"], c["UM"]["median"], c["UT"]["p90"]), (100, 250, 400))

    def test_a_site_without_deaths_is_refused(self):
        with self.assertRaises(A.Refused):
            A.summary(full({("ACA", "UM", "f"): [(300, False)]}))


class Verdict(unittest.TestCase):
    def test_the_three_conditions_at_their_edges(self):
        F = Fraction
        self.assertEqual(A.verdict(F(11, 100), F(25, 1000))[0], 1)                 # both thresholds inclusive
        self.assertEqual(A.verdict(F(11, 100) - F(1, 10 ** 9), F(5, 100))[0], 0)
        self.assertEqual(A.verdict(F(22, 100), F(25, 1000) - F(1, 10 ** 9))[0], 0)
        self.assertEqual(A.verdict(F(12, 100), F(12, 100))[0], 0)                  # equal is not smaller
        self.assertEqual(A.verdict(F(22, 100), F(5, 100))[1],
                         {"male_at_least_11pct": True, "female_at_least_2.5pct": True, "female_below_male": True})

    def test_gains_are_exact_fractions(self):
        s = A.summary(full({("ACA", x, "m"): [(1000, True)] for x in A.SITES}))
        g = A.gains(s)
        self.assertEqual(g["m"], (Fraction(1, 4), Fraction(1, 4)))
        self.assertEqual(g["f"], (0, 0))


class Table(unittest.TestCase):
    def test_ninety_six_numbers(self):
        self.assertEqual(sum(len(v) for d in A.TABLE1.values() for s in d.values() for v in s.values()), 96)
        rows = A.table1_check(A.summary(full({})))
        self.assertEqual(len(rows), 24)
        self.assertEqual(sum(r["matched"] for r in rows), 0)                       # nothing printed is 800


class Refusals(unittest.TestCase):
    def test_wrong_input_hash_stops_the_run(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "inputs"))
            with open(os.path.join(d, "inputs", A.INPUT[0]), "wb") as f:
                f.write(b"not the workbook")
            with self.assertRaises(SystemExit):
                A.run(inputs=os.path.join(d, "inputs"), results=os.path.join(d, "results"))


def inputs_dir():
    d = os.environ.get("ITP_INPUTS") or os.path.join(HERE, "..", "inputs")
    return d if os.path.isfile(os.path.join(d, A.INPUT[0])) else None


@unittest.skipUnless(inputs_dir(), "the real workbook is not at inputs/ (or ITP_INPUTS)")
class RealData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out, cls.detail = A.run(inputs=inputs_dir(), results=cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_table_1(self):
        self.assertEqual((self.out["table1_aca"], self.out["table1_all"]), (25, 82))
        self.assertEqual((self.out["median_m"], self.out["p90_m"]), ("807/984", "1094/1215"))   # as printed
        self.assertEqual((self.out["median_f"], self.out["p90_f"]), ("891/939", "1072/1159"))   # printed 896, 1167
        self.assertEqual(self.out["sites_median_m"], "807/974; 925/999; 704/981")                # as printed
        self.assertEqual(self.out["counts"], "m 300/156; f 280/136")

    def test_the_papers_p_values(self):
        self.assertEqual(self.out["logrank_p"], "m 1.08e-11; f 4.81e-03")       # printed < 0.0001 and 0.0101

    def test_the_registered_test(self):
        self.assertAlmostEqual(self.out["inc_median_m"], 984 / 807 - 1, places=6)
        self.assertAlmostEqual(self.out["inc_median_f"], 939 / 891 - 1, places=6)
        self.assertEqual(self.out["test_passed"], 1)


if __name__ == "__main__":
    unittest.main()
