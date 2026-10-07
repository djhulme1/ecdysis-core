"""The canagliflozin recount on made-up data: the median and 90th-percentile rules, R's quantile and Fisher test,
the stratified log-rank test, the Wang-Allison table, the site-mean pooling, the verdict, and refusals; with the real
workbook (at inputs/ or in ITP_INPUTS), also Table 1 reproduced in full.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_cana", os.path.join(HERE, "..", "itp", "cana.py"))
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)


def row(site="TJL", sex="m", group="Cana", age="900", status="dead", dead="1", cohort="C2016"):
    return {"cohort": cohort, "site": site, "sex": sex, "group": group, "age": age, "status": status, "dead": dead}


def mice_with(values):
    """{(group, site, sex): [(age, died)]} with every key present; values overrides some."""
    out = {(g, s, x): [] for g in C.GROUPS for s in C.SITES for x in C.SEXES}
    out.update(values)
    return out


class Rules(unittest.TestCase):
    def test_median_and_90th_percentile_of_the_dead(self):
        self.assertEqual(C.median_dead(list(range(1, 11))), 5.5)
        self.assertEqual(C.median_dead([3, 1, 2]), 2)
        self.assertEqual(C.p90_dead(list(range(1, 11))), 9)       # 9 of 10 dead by day 9
        self.assertEqual(C.p90_dead(list(range(1, 21))), 18)
        self.assertEqual(C.p90_dead(list(range(1, 12))), 10)      # ceil(9.9) = 10th of 11

    def test_quantile_type_7_as_r_gives_it(self):
        self.assertAlmostEqual(C.quantile7(list(range(1, 11)), 0.9), 9.1)     # quantile(1:10, 0.9) in R
        self.assertEqual(C.quantile7([5, 1, 3], 0.5), 3)
        self.assertEqual(C.quantile7([7], 0.9), 7)

    def test_fisher_matches_known_values(self):
        self.assertAlmostEqual(C.fisher_two_sided([[3, 1], [1, 3]]), 34 / 70)  # the tea-tasting table: 0.4857
        self.assertAlmostEqual(C.fisher_two_sided([[1, 9], [11, 3]]), 0.0027594561852200836, places=12)
        self.assertEqual(C.fisher_two_sided([[5, 0], [0, 5]]), 2 / 252)
        self.assertEqual(C.fisher_two_sided([[2, 2], [2, 2]]), 1.0)

    def test_stratified_logrank_reduces_to_the_plain_one(self):
        a = [(t, True) for t in (10, 20, 30, 40, 50)] + [(35, False)]
        b = [(t, True) for t in (15, 25, 60, 70, 80)]
        self.assertAlmostEqual(C.logrank_strat_p([(a, b)]), C.rapa.logrank_p(a, b), places=15)
        self.assertAlmostEqual(C.logrank_strat_p([(a, b)]), C.logrank_strat_p([(b, a)]), places=15)

    def test_wang_allison_counts_late_removals_above_and_drops_early_ones(self):
        ctl = [(t, True) for t in range(1, 11)] + [(2, False)]        # one removed early: left out
        trt = [(t, True) for t in range(5, 15)] + [(14, False)]       # one removed late: counted above
        table, p = C.wang_allison([(ctl, trt)])
        cut = C.quantile7([t for t, d in ctl + trt if d], 0.9)       # 12.1 for these deaths
        self.assertAlmostEqual(cut, 12.1)
        self.assertEqual(table, [[0, 10], [3, 8]])                   # deaths at 13 and 14, and the removal at 14
        self.assertAlmostEqual(p, C.fisher_two_sided([[0, 10], [3, 8]]))

    def test_pooled_is_the_mean_of_the_site_values(self):
        values = {}
        for s, (mc, mt) in zip(C.SITES, ((100, 120), (200, 230), (300, 330))):
            values[("Control", s, "m")] = [(mc, True)] * 9 + [(mc + 50, True)]
            values[("Cana", s, "m")] = [(mt, True)] * 9 + [(mt + 50, True)]
        summ = C.summarise(mice_with(values), "m")
        self.assertEqual(summ["Control"]["Pool"]["median"], 200)
        self.assertEqual(summ["Cana"]["Pool"]["median"], (120 + 230 + 330) / 3)
        self.assertEqual(summ["Control"]["Pool"]["p90"], 200)
        median_gain, p90_gain = C.gains(summ)
        self.assertAlmostEqual(median_gain, 680 / 600 - 1)
        self.assertAlmostEqual(p90_gain, 680 / 600 - 1)

    def test_removed_mice_count_but_are_left_out_of_medians(self):
        values = {("Control", s, "m"): [(100, True), (200, True), (300, True), (1000, False)] for s in C.SITES}
        values.update({("Cana", s, "m"): [(150, True), (250, True), (350, True)] for s in C.SITES})
        summ = C.summarise(mice_with(values), "m")
        self.assertEqual(summ["Control"]["TJL"]["count"], 4)
        self.assertEqual(summ["Control"]["TJL"]["dead"], 3)
        self.assertEqual(summ["Control"]["TJL"]["median"], 200)

    def test_half_up_rounding(self):
        self.assertEqual(C.half_up(896.5), 897)
        self.assertEqual(C.half_up(911.5), 912)
        self.assertEqual(C.half_up(874.1667), 874)


class Verdict(unittest.TestCase):
    def summary(self, controls, treated):
        values = {}
        for s, c, t in zip(C.SITES, controls, treated):
            values[("Control", s, "m")] = [(c, True)] * 10
            values[("Cana", s, "m")] = [(t, True)] * 10
        return C.summarise(mice_with(values), "m")

    def test_passes_with_large_gains_everywhere(self):
        self.assertEqual(C.verdict(self.summary((800, 800, 800), (900, 900, 900))), (1, True))

    def test_fails_when_one_site_is_not_higher(self):
        # pooled gain 16.7%, but the third site is equal: "parallel effects at each of 3 test sites" fails
        self.assertEqual(C.verdict(self.summary((800, 800, 800), (1000, 1000, 800))), (0, False))

    def test_fails_below_half_the_reported_gain(self):
        # 6% everywhere: higher at each site, but under 7% pooled
        self.assertEqual(C.verdict(self.summary((1000, 1000, 1000), (1060, 1060, 1060))), (0, True))

    def test_threshold_is_inclusive(self):
        self.assertEqual(C.verdict(self.summary((1000, 1000, 1000), (1070, 1070, 1070))), (1, True))


class Refusals(unittest.TestCase):
    def test_bad_rows_are_refused(self):
        for bad in (row(age="900.5"), row(age=""), row(status="dead", dead="0"), row(status="alive", dead="0"),
                    row(cohort="C2017"), row(site="XX"), row(sex="u")):
            with self.subTest(bad=bad), self.assertRaises(C.Refused):
                C.mice_from_rows([bad])

    def test_other_groups_are_read_but_not_kept(self):
        mice = C.mice_from_rows([row(group="NR"), row(group="Cana"), row(group="Control", status="removed", dead="0")])
        self.assertEqual(mice[("Cana", "TJL", "m")], [(900, True)])
        self.assertEqual(mice[("Control", "TJL", "m")], [(900, False)])
        self.assertEqual(sum(len(v) for v in mice.values()), 2)

    def test_wrong_input_hash_stops_the_run(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "inputs"))
            with open(os.path.join(d, "inputs", C.INPUT[0]), "wb") as f:
                f.write(b"not the workbook")
            with self.assertRaises(SystemExit):
                C.run("a" * 64, inputs=os.path.join(d, "inputs"), results=os.path.join(d, "results"))


def inputs_dir():
    d = os.environ.get("ITP_INPUTS") or os.path.join(HERE, "..", "inputs")
    return d if os.path.isfile(os.path.join(d, C.INPUT[0])) else None


@unittest.skipUnless(inputs_dir(), "the real workbook is not at inputs/ (or ITP_INPUTS)")
class RealData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out, cls.detail = C.run("a" * 64, inputs=inputs_dir(), results=cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_table_1_reproduced_in_full(self):
        self.assertEqual(self.out["table1_matched"], 48)

    def test_the_papers_p_values(self):
        self.assertEqual(round(self.out["logrank_p_f"], 3), 0.512)
        self.assertLess(self.out["logrank_p_m"], 1e-4)
        self.assertLess(self.out["wa_p_m"], 1e-4)
        self.assertEqual(round(self.out["wa_p_f"], 2), 0.50)
        printed = {"m": {"TJL": 0.003, "UM": 0.001, "UT": 0.39}, "f": {"TJL": 0.26, "UM": 0.38, "UT": 0.56}}
        for sex, sites in printed.items():
            for site, p in sites.items():
                digits = 3 if p < 0.01 else 2
                self.assertEqual(round(self.detail["wang_allison"]["per_site"][sex][site], digits), p)
        self.assertEqual(round(self.detail["logrank"]["per_site"]["m"]["UT"], 3), 0.060)

    def test_the_registered_test(self):
        self.assertAlmostEqual(self.out["inc_median_m"], 0.139712, places=6)
        self.assertAlmostEqual(self.out["inc_p90_m"], 0.09172, places=6)
        self.assertEqual(self.out["test_passed"], 1)


if __name__ == "__main__":
    unittest.main()
