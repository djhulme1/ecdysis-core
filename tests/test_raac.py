"""Rapamycin with acarbose against rapamycin alone (itp/raac.py): the verdict at and beside each condition; each refusal
of the rows (population, cohort, site, sex, age, status, and each compared group's design in its own cohort); the median
of the dead and the Kaplan-Meier median on hand examples; the mean of site medians and the gain over controls; the
log-rank comparison across cohorts in both directions and with removed mice left out; the reading of printed p values;
and, with the three workbooks at inputs/ (or RAAC_INPUTS), the recount itself.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_raac", os.path.join(HERE, "..", "itp", "raac.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

INPUTS = os.environ.get("RAAC_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = all(os.path.isfile(os.path.join(INPUTS, name)) for name, _ in M.INPUTS.values())


def row(cohort="C2017", group="RaAc_9", site="UM", sex="m", status="dead", dead="1", age="900", dose=None,
        start=None, population="UM-HET3", in_cohort=None):
    dose_, start_ = M.DESIGN.get((cohort, group), ("1", "9"))
    return {"population": population, "cohort": in_cohort or cohort, "site": site, "sex": sex, "id": "X",
            "group": group, "dose": dose if dose is not None else dose_,
            "age_initiation": start if start is not None else (start_ or ""), "status": status, "dead": dead,
            "age": age}


def cohort_rows(cohort, *extra):
    return [row(cohort, g) for (c, g) in M.DESIGN if c == cohort] + list(extra)


class Verdict(unittest.TestCase):
    def test_at_and_beside_each_condition(self):
        med, ps = {"RaAc9": 900.1, "C2006": 900.0, "C2009": 900.0}, {"C2006": 0.0499, "C2009": 0.0499}
        self.assertTrue(all(M.conditions(med, ps).values()))
        for med2, ps2 in (({**med, "C2006": 900.1}, ps), ({**med, "C2009": 901.0}, ps),
                          (med, {**ps, "C2006": 0.05}), (med, {**ps, "C2009": 0.2})):
            with self.subTest(med=med2, ps=ps2):
                self.assertEqual(sum(M.conditions(med2, ps2).values()), 3)


class Rows(unittest.TestCase):
    def test_good_rows_are_read(self):
        mice = M.mice_from_rows(cohort_rows("C2017", row(group="Control", status="removed", dead="0", age="400"),
                                            row(group="RaAc_16", dose="anything", start="16", sex="f")), "C2017")
        self.assertEqual(mice[("RaAc_9", "UM", "m")], [(900, True)])
        self.assertEqual(sorted(mice[("Control", "UM", "m")]), [(400, False), (900, True)])
        self.assertEqual(mice[("RaAc_16", "UM", "f")], [(900, True)])        # a group outside the design is kept as read
        self.assertEqual(M.mice_from_rows(cohort_rows("C2017", row(age="900.0")), "C2017")[("RaAc_9", "UM", "m")],
                         [(900, True), (900, True)])

    def test_each_refusal(self):
        bad = [row(population="B6"), row(in_cohort="C2016"), row(site="XX"), row(sex="u"), row(age="900.5"),
               row(age=""), row(status="dead", dead="0"), row(status="alive", dead="0"),
               row(dose="Rapa: 14 and ACA: 1000"), row(start="16"), row(group="Control", dose="14"),
               row(group="Control", start="9")]
        for r in bad:
            with self.subTest(row=r), self.assertRaises(M.Refused):
                M.mice_from_rows(cohort_rows("C2017", r), "C2017")

    def test_each_prior_cohorts_design(self):
        M.mice_from_rows(cohort_rows("C2006"), "C2006")
        M.mice_from_rows(cohort_rows("C2009"), "C2009")
        for cohort, r in (("C2006", row("C2006", "Rapa", start="20")), ("C2006", row("C2006", "Rapa", dose="42")),
                          ("C2009", row("C2009", "Rapa_mid", dose="42")), ("C2009", row("C2009", "Rapa_mid", start="4")),
                          ("C2009", row("C2017", "RaAc_9", in_cohort="C2017"))):
            with self.subTest(cohort=cohort, row=r), self.assertRaises(M.Refused):
                M.mice_from_rows(cohort_rows(cohort, r), cohort)

    def test_a_missing_group_is_refused(self):
        with self.assertRaises(M.Refused):
            M.mice_from_rows([row(group="Control")], "C2017")
        with self.assertRaises(M.Refused):
            M.mice_from_rows([row("C2009", "Rapa_lo", dose="4.7"), row("C2009", "Control")], "C2009")


def group(ages, removed=()):
    return [(a, True) for a in ages] + [(a, False) for a in removed]


def three_sites(**by_site):
    return {(g, s, sex): ms for s, groups in by_site.items() for (g, sex), ms in groups.items()}


class Medians(unittest.TestCase):
    def test_the_median_of_the_dead(self):
        self.assertEqual(M.site_median(group([800, 900], removed=[1000])), 850)    # the removed mouse left out
        self.assertEqual(M.site_median(group([700, 800, 900], removed=[100])), 800)

    def test_the_kaplan_meier_median(self):
        self.assertEqual(M.km_median(group([1, 2, 3, 4])), 2.5)                  # exactly one half at 2: mean of 2, 3
        self.assertEqual(M.km_median(group([1, 2, 3])), 2)
        # a mouse removed at 2 is at risk at 2: S(1) = 3/4, S(2) = 3/4 * 2/3 = 1/2 exactly, so the mean of 2 and 3
        # (were it out of the risk set at 2, S(2) would be 3/8 and the median 2)
        self.assertEqual(M.km_median(group([1, 2, 3], removed=[2])), 2.5)
        self.assertEqual(M.km_median(group([5, 6], removed=[1, 2, 3, 4, 7, 8, 9])), None)  # never down to one half
        self.assertEqual(M.km_median(group([10, 10, 20, 30])), 15)               # two deaths at once: S(10) = 1/2, next 20
        self.assertEqual(M.km_median(group([10, 10, 20, 30, 40])), 20)

    def test_mean_of_site_medians_and_gain(self):
        mice = three_sites(TJL={("Rapa", "m"): group([800, 900]), ("Control", "m"): group([700, 900])},
                           UM={("Rapa", "m"): group([1000], removed=[50]), ("Control", "m"): group([800])},
                           UT={("Rapa", "m"): group([600, 900, 1200]), ("Control", "m"): group([1000])})
        self.assertAlmostEqual(M.mean_of_site_medians(mice, "Rapa", "m"), (850 + 1000 + 900) / 3)
        self.assertAlmostEqual(M.gain(mice, "Rapa", "m"), (850 / 800 + 1000 / 800 + 900 / 1000 - 3) / 3)


class LogRank(unittest.TestCase):
    def setUp(self):
        a = {("A", s, "m"): group([800 + 10 * i + k for i in range(8)], removed=[790 + k]) for k, s in enumerate(M.SITES)}
        b = {("B", s, "m"): group([700 + 15 * i + k for i in range(8)], removed=[805 + k]) for k, s in enumerate(M.SITES)}
        self.a, self.b = a, b

    def test_either_direction_gives_one_p(self):
        p = M.compare(self.a, "A", self.b, "B", "m")
        self.assertAlmostEqual(p, M.compare(self.b, "B", self.a, "A", "m"), places=12)
        self.assertLess(p, 0.05)

    def test_it_is_the_stratified_test_of_the_cohorts_own_mice(self):
        strata = [(self.b[("B", s, "m")], self.a[("A", s, "m")]) for s in M.SITES]
        self.assertEqual(M.compare(self.a, "A", self.b, "B", "m"), M.cana.logrank_strat_p(strata))

    def test_removed_mice_left_out(self):
        left = M.compare(self.a, "A", self.b, "B", "m", removed="left out")
        dead_only = [([m for m in self.b[("B", s, "m")] if m[1]], [m for m in self.a[("A", s, "m")] if m[1]])
                     for s in M.SITES]
        self.assertEqual(left, M.cana.logrank_strat_p(dead_only))
        self.assertNotEqual(left, M.compare(self.a, "A", self.b, "B", "m"))

    def test_printed_p_values(self):
        self.assertTrue(M.as_printed_p(0.00599, "< 0.006"))
        self.assertFalse(M.as_printed_p(0.006, "< 0.006"))
        self.assertFalse(M.as_printed_p(0.000613, "< 0.0006"))
        self.assertTrue(M.as_printed_p(0.0734, "0.07"))
        self.assertFalse(M.as_printed_p(0.0932, "0.07"))
        self.assertTrue(M.as_printed_p(0.393, "0.39"))


@unittest.skipUnless(HAVE, "needs the three workbooks at inputs/ or RAAC_INPUTS")
class Recount(unittest.TestCase):
    def test_the_three_cohorts(self):
        with tempfile.TemporaryDirectory() as d:
            out, detail = M.run("0" * 64, inputs=INPUTS, results=d)
        self.assertEqual(out["test_passed"], 1)
        self.assertEqual((out["median_m_raac9"], out["median_m_c2006"], out["median_m_c2009"]), (949.2, 887.0, 858.8))
        self.assertEqual((out["logrank_p_c2006"], out["logrank_p_c2009"]), (0.0104, 0.000613))
        self.assertEqual(out["rows"], "C2017 2916; C2006 2172; C2009 2332")
        self.assertEqual(out["n_m"], "RaAc9 156; C2006 171; C2009 156")
        self.assertTrue(out["medians_as_printed"].startswith("means 4 of 6; site medians RaAc9 6, C2006 6, C2009 0 of 6"))
        self.assertEqual(out["p_as_printed"], "1 of 4")


if __name__ == "__main__":
    unittest.main()
