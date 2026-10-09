"""The 2012 acarbose recount on made-up data: rows checked against rule 1 and the groups' designs, both pooling rules,
the rises, each clause of the verdict failing on its own, the Wang-Allison readings, and refusals; with the real
workbook (at inputs/ or in ITP_INPUTS), also Table 2's numbers and the P values as found before registering.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_aca2012", os.path.join(HERE, "..", "itp", "aca2012.py"))
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)

INPUTS = os.environ.get("ITP_INPUTS", os.path.join(HERE, "..", "inputs"))
HAVE = os.path.exists(os.path.join(INPUTS, A.INPUT[0]))


def row(site="TJL", sex="m", group="ACA", age="900", status="dead", dead="1", cohort="C2012", **kw):
    dose, start = A.DESIGN.get(group, ("0", None))
    r = {"population": "UM-HET3", "cohort": cohort, "site": site, "sex": sex, "group": group, "age": age,
         "status": status, "dead": dead, "dose": dose, "age_initiation": start}
    r.update(kw)
    return r


def full(values):
    """Rows for Control and ACA at every site and sex: eight deaths at age a and two at a + 100, with values
    {(group, sex): (a at TJL, a at UM, a at UT)} overriding the default 800."""
    rows = []
    for g in ("Control", "ACA"):
        for sex in A.SEXES:
            for s, a in zip(A.SITES, values.get((g, sex), (800, 800, 800))):
                rows += [row(site=s, sex=sex, group=g, age=str(a))] * 8
                rows += [row(site=s, sex=sex, group=g, age=str(a + 100))] * 2
    return rows


class Rows(unittest.TestCase):
    def test_kept_rows(self):
        m = A.mice_from_rows([row(), row(group="Control", status="removed", dead="0", age="400"),
                              row(group="HBX", sex="f", site="UT"), row(group="I767d", site="UM")])
        self.assertEqual(m[("ACA", "TJL", "m")], [(900, True)])
        self.assertEqual(m[("Control", "TJL", "m")], [(400, False)])
        self.assertEqual(m[("HBX", "UT", "f")], [(900, True)])
        self.assertEqual(m[("I767d", "UM", "m")], [(900, True)])

    def test_refusals(self):
        for bad in (row(age="900.5"), row(status="dead", dead="0"), row(cohort="C2011"), row(site="XX"), row(age=""),
                    row(group="Rapa"), row(dose="2500"), row(age_initiation="4"), row(group="Control", dose="1000"),
                    row(population="C57BL/6"), row(sex="x")):
            with self.subTest(bad=bad), self.assertRaises(A.cana.Refused):
                A.mice_from_rows([bad])


class Pooling(unittest.TestCase):
    def test_both_rules_and_the_rises(self):
        mice = A.mice_from_rows(full({("Control", "m"): (700, 800, 900), ("ACA", "m"): (760, 830, 960)}))
        s = A.summarise(mice, "m")
        self.assertEqual(s["Control"]["SiteMean"]["median"], 800)
        self.assertEqual(s["ACA"]["SiteMean"]["median"], (760 + 830 + 960) / 3)
        self.assertEqual(s["Control"]["Pooled"]["median"], 800)  # 24 deaths at 700, 800, 900 (8 each) and 6 later
        self.assertEqual(s["Control"]["Pooled"]["dead"], 30)
        r = A.rises(s, "median")
        self.assertAlmostEqual(r["SiteMean"], (850 / 800) - 1)
        self.assertGreater(r["Pooled"], 0)

    def test_a_rise_under_one_rule_only_is_not_a_rise(self):
        verdict = A.verdict({"SiteMean": 0.01, "Pooled": -0.001}, {"m": {"SiteMean": 0.1, "Pooled": 0.1},
                            "f": {"SiteMean": 0.1, "Pooled": 0.1}}, 0.001, {"m": 0.001, "f": 0.001})
        self.assertFalse(verdict["male median rises (both rules)"])


class Verdict(unittest.TestCase):
    GOOD = dict(median_m={"SiteMean": 0.06, "Pooled": 0.07}, p90={"m": {"SiteMean": 0.12, "Pooled": 0.12},
                "f": {"SiteMean": 0.07, "Pooled": 0.06}}, logrank_m=1e-4, wa={"m": 1e-4, "f": 0.01})

    def clauses(self, **over):
        args = dict(self.GOOD)
        args.update(over)
        return A.verdict(**args)

    def test_all_hold(self):
        self.assertTrue(all(self.clauses().values()))

    def test_each_fails_alone(self):
        cases = [
            (dict(logrank_m=0.05), "male log-rank P below 0.05"),
            (dict(wa={"m": 0.06, "f": 0.01}), "male Wang-Allison P below 0.05"),
            (dict(wa={"m": 1e-4, "f": 0.0579}), "female Wang-Allison P below 0.05"),
            (dict(p90={"m": {"SiteMean": 0.12, "Pooled": 0.12}, "f": {"SiteMean": 0.0, "Pooled": 0.06}}),
             "female 90th percentile rises (both rules)"),
            (dict(median_m={"SiteMean": -0.01, "Pooled": 0.07}), "male median rises (both rules)"),
        ]
        for over, name in cases:
            with self.subTest(name=name):
                c = self.clauses(**over)
                self.assertFalse(c[name])
                self.assertEqual(sum(1 for v in c.values() if not v), 1)


class WangAllison(unittest.TestCase):
    def test_readings_agree_on_a_clear_case_and_count_removed_mice_past_the_cut(self):
        # Each site: 20 controls dying at 600..790 and 20 treated at 700..890, one treated removed at 950.
        ctl = [(600 + 10 * i, True) for i in range(20)]
        trt = [(700 + 10 * i, True) for i in range(19)] + [(950, False)]
        strata = [(ctl, trt)] * 3
        table, p = A.cana.wang_allison(strata)
        self.assertEqual(table[0][0], 0)          # no control lives past the joint 90th percentile
        self.assertGreater(table[1][0], 0)        # the removed mouse at 950 counts as alive past it
        self.assertLess(p, 0.01)
        mice = {("Control", s, "m"): ctl for s in A.SITES}
        mice.update({("ACA", s, "m"): trt for s in A.SITES})
        readings = A.wang_allison_readings(mice, "m")
        self.assertTrue(all(v["p"] < 0.05 for v in readings.values()), readings)

    def test_kaplan_meier_ninety(self):
        self.assertEqual(A.km_q90([(t, True) for t in range(1, 11)]), 9)
        self.assertEqual(A.km_q90([(t, True) for t in range(1, 11)] + [(20, False)]), 10)


@unittest.skipUnless(HAVE, "the workbook is not at inputs/ or ITP_INPUTS")
class Workbook(unittest.TestCase):
    """What was read before registering, on the real data of record."""

    @classmethod
    def setUpClass(cls):
        import tempfile
        cls.out, cls.detail = A.run(INPUTS, tempfile.mkdtemp())

    def test_the_cohort(self):
        self.assertEqual(self.detail["input"]["rows"], 1460)
        self.assertEqual(self.detail["input"]["per_group"], {"Control": 584, "ACA": 292, "HBX": 292, "I767d": 292})

    def test_table2_as_found(self):
        self.assertEqual(self.out["table2_matched_pooled"], 4)    # the four 90th percentiles; one more death per group
        self.assertEqual(self.out["table2_matched_sitemean"], 1)  # the acarbose male median, 875
        self.assertEqual(self.out["table2_total"], 12)

    def test_the_p_values_as_found(self):
        self.assertAlmostEqual(self.out["wa_p_f"], 0.0579, places=4)
        self.assertAlmostEqual(self.out["wa_p_f_pooled_threshold"], 0.0152, places=4)
        self.assertLess(self.out["logrank_p_m"], 1e-4)
        self.assertLess(self.out["wa_p_m"], 1e-3)
        self.assertEqual(self.out["test_passed"], 0)


if __name__ == "__main__":
    unittest.main()
