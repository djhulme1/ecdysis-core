"""The 17aE2 late-start recount on made-up data: which rows are kept, the design columns checked, the site-mean
pooling, the four gains and the verdict's thresholds, and refusals; with the real workbook (at inputs/ or in
ITP_INPUTS), also Table 1 reproduced in full and the paper's p-values.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_e2", os.path.join(HERE, "..", "itp", "e2.py"))
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)

DESIGN = {"Control": ("0", None), "17aE2_16m": ("14.4", "16"), "17aE2_20m": ("14.4", "20"),
          "Cana": ("180", "7"), "NR": ("1000", "8")}


def row(site="TJL", sex="m", group="17aE2_16m", age="900", status="dead", dead="1", cohort="C2016", **kw):
    dose, start = DESIGN.get(group, ("0", None))
    r = {"cohort": cohort, "site": site, "sex": sex, "group": group, "age": age, "status": status, "dead": dead,
         "dose": dose, "age_initiation": start}
    r.update(kw)
    return r


def mice(values):
    """{group: {site: [(age, died)]}} with every group and site present; values overrides some."""
    out = {g: {s: [] for s in E.SITES} for g in E.GROUPS}
    for (g, s), v in values.items():
        out[g][s] = v
    return out


class Rows(unittest.TestCase):
    def test_males_of_the_three_groups_are_kept(self):
        m = E.males([row(), row(group="Control", status="removed", dead="0", age="400"), row(group="17aE2_20m", site="UT"),
                     row(group="Cana"), row(group="NR", sex="f"), row(group="Control", sex="f")])
        self.assertEqual(m["17aE2_16m"]["TJL"], [(900, True)])
        self.assertEqual(m["Control"]["TJL"], [(400, False)])
        self.assertEqual(m["17aE2_20m"]["UT"], [(900, True)])
        self.assertEqual(sum(len(v) for g in m.values() for v in g.values()), 3)

    def test_a_malformed_row_is_refused_even_in_a_group_not_kept(self):
        for bad in (row(group="NR", age="900.5"), row(group="Cana", status="dead", dead="0"), row(cohort="C2017"),
                    row(site="XX"), row(age="")):
            with self.subTest(bad=bad), self.assertRaises(E.cana.Refused):
                E.males([bad])

    def test_a_kept_row_must_carry_its_groups_design(self):
        for bad in (row(dose="7.2"), row(age_initiation="20"), row(group="17aE2_20m", age_initiation="16"),
                    row(group="Control", dose="14.4"), row(group="Control", age_initiation="16")):
            with self.subTest(bad=bad), self.assertRaises(E.cana.Refused):
                E.males([bad])
        self.assertEqual(E.males([row(group="Control", age_initiation="")])["Control"]["TJL"], [(900, True)])


class Pooling(unittest.TestCase):
    def test_pooled_values_are_the_means_of_the_sites(self):
        values = {}
        for s, (c, a, b) in zip(E.SITES, ((700, 840, 780), (800, 950, 880), (900, 1060, 990))):
            values[("Control", s)] = [(c, True)] * 9 + [(c + 100, True)] + [(50, False)]
            values[("17aE2_16m", s)] = [(a, True)] * 9 + [(a + 100, True)]
            values[("17aE2_20m", s)] = [(b, True)] * 9 + [(b + 100, True)]
        summ = E.summary(mice(values))
        self.assertEqual(summ["Control"]["Pool"]["count"], 33)
        self.assertEqual(summ["Control"]["TJL"]["dead"], 10)
        self.assertEqual(summ["Control"]["Pool"]["median"], 800)
        self.assertEqual(summ["17aE2_16m"]["Pool"]["median"], 950)
        self.assertEqual(summ["17aE2_20m"]["Pool"]["p90"], (780 + 880 + 990) / 3)
        g = E.gains(summ)
        self.assertAlmostEqual(g["median_16"], 950 / 800 - 1)
        self.assertAlmostEqual(g["median_20"], 2650 / 2400 - 1)
        self.assertAlmostEqual(g["p90_16"], 950 / 800 - 1)

    def test_a_site_with_no_deaths_is_refused(self):
        values = {(g, s): [(800, True)] for g in E.GROUPS for s in E.SITES}
        values[("17aE2_20m", "UM")] = [(300, False)]
        with self.assertRaises(E.cana.Refused):
            E.summary(mice(values))


class Verdict(unittest.TestCase):
    def test_all_four_gains_must_reach_half_the_reported_ones(self):
        ok = {"median_16": 0.19, "median_20": 0.11, "p90_16": 0.07, "p90_20": 0.05}
        self.assertEqual(E.verdict(ok), 1)
        for k, low in (("median_16", 0.0949), ("median_20", 0.0549), ("p90_16", 0.0349), ("p90_20", 0.0249)):
            with self.subTest(k=k):
                self.assertEqual(E.verdict(dict(ok, **{k: low})), 0)

    def test_thresholds_are_inclusive(self):
        self.assertEqual(E.verdict(dict(E.THRESHOLDS)), 1)


class Refusals(unittest.TestCase):
    def test_wrong_input_hash_stops_the_run(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "inputs"))
            with open(os.path.join(d, "inputs", E.INPUT[0]), "wb") as f:
                f.write(b"not the workbook")
            with self.assertRaises(SystemExit):
                E.run(inputs=os.path.join(d, "inputs"), results=os.path.join(d, "results"))


def inputs_dir():
    d = os.environ.get("ITP_INPUTS") or os.path.join(HERE, "..", "inputs")
    return d if os.path.isfile(os.path.join(d, E.INPUT[0])) else None


@unittest.skipUnless(inputs_dir(), "the real workbook is not at inputs/ (or ITP_INPUTS)")
class RealData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out, cls.detail = E.run(inputs=inputs_dir(), results=cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_table_1_reproduced_in_full(self):
        self.assertEqual(self.out["table1_matched"], 9)
        self.assertEqual((self.out["n_m_control"], self.out["n_m_e2_16"], self.out["n_m_e2_20"]), (303, 156, 159))

    def test_table_2_as_found(self):
        self.assertEqual(self.out["table2_matched"], 5)
        self.assertEqual(self.out["sites_m"], "TJL 749/901.5/873; UM 814/943/900; UT 799/955/840")

    def test_the_papers_p_values(self):
        self.assertLess(self.out["logrank_p_16"], 1e-4)
        self.assertEqual(round(self.out["logrank_p_20"], 4), 0.0064)       # Table 1 prints 0.007
        self.assertEqual(round(self.out["wa_p_16"], 3), 0.004)
        self.assertEqual(round(self.out["wa_p_20"], 3), 0.174)

    def test_the_registered_test(self):
        self.assertAlmostEqual(self.out["inc_median_16"], 0.185224, places=6)
        self.assertAlmostEqual(self.out["inc_median_20"], 0.106266, places=6)
        self.assertAlmostEqual(self.out["inc_p90_16"], 0.070064, places=6)
        self.assertAlmostEqual(self.out["inc_p90_20"], 0.053503, places=6)
        self.assertEqual(self.out["test_passed"], 1)


if __name__ == "__main__":
    unittest.main()
