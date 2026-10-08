"""The acarbose-doses recount on made-up data: which rows are kept, the design columns checked and anything malformed
refused; the pooled-deaths rule (not the mean of the sites) for medians and 90th percentiles, removed mice left out;
the gains and the verdict's thresholds and its sex contrast; with the real workbook (at inputs/ or in ITP_INPUTS), also
Tables 1 and 2 and the paper's p-values.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_aca", os.path.join(HERE, "..", "itp", "aca.py"))
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)

DESIGN = dict(A.DESIGN, UA=("2000", "10"))


def row(site="TJL", sex="m", group="ACA_mid", age="900", status="dead", dead="1", cohort="C2013", **kw):
    dose, start = DESIGN.get(group, ("0", None))
    r = {"cohort": cohort, "site": site, "sex": sex, "group": group, "age": age, "status": status, "dead": dead,
         "dose": dose, "age_initiation": start}
    r.update(kw)
    return r


def full(values):
    """Mice for every group, site and sex, one death at 800 days each, with some overridden."""
    out = {(g, s, x): [(800, True)] for g in A.GROUPS for s in A.SITES for x in A.SEXES}
    out.update(values)
    return out


class Rows(unittest.TestCase):
    def test_the_four_groups_are_kept_and_ursolic_acid_is_not(self):
        m = A.mice_from_rows([row(), row(group="Control", status="removed", dead="0", age="400"),
                              row(group="ACA_hi", site="UT", sex="f"), row(group="UA")])
        self.assertEqual(m[("ACA_mid", "TJL", "m")], [(900, True)])
        self.assertEqual(m[("Control", "TJL", "m")], [(400, False)])
        self.assertEqual(m[("ACA_hi", "UT", "f")], [(900, True)])
        self.assertEqual(sum(len(v) for v in m.values()), 3)

    def test_malformed_rows_are_refused(self):
        for bad in (row(cohort="C2012"), row(site="XX"), row(sex="u"), row(age="900.5"), row(age=""),
                    row(status="dead", dead="0"), row(group="UA", status="removed", dead="1"), row(group="Rapa")):
            with self.subTest(bad=bad), self.assertRaises(A.Refused):
                A.mice_from_rows([bad])

    def test_a_kept_row_must_carry_its_groups_design(self):
        for bad in (row(dose="400"), row(age_initiation="10"), row(group="ACA_lo", dose="1000"),
                    row(group="Control", dose="1000"), row(group="Control", age_initiation="8")):
            with self.subTest(bad=bad), self.assertRaises(A.Refused):
                A.mice_from_rows([bad])
        self.assertEqual(A.mice_from_rows([row(group="Control", age_initiation="")])[("Control", "TJL", "m")],
                         [(900, True)])


class Pooling(unittest.TestCase):
    def test_pooled_deaths_not_the_mean_of_the_sites(self):
        values = {("Control", "TJL", "m"): [(700, True)] * 3, ("Control", "UM", "m"): [(800, True)],
                  ("Control", "UT", "m"): [(900, True), (5000, False)]}
        s = A.summary(full(values))
        c = s["m"]["Control"]
        self.assertEqual((c["mice"], c["dead"], c["removed"]), (6, 5, 1))
        self.assertEqual(c["median"], 700)                              # 700, 700, 700, 800, 900; the site mean is 800
        self.assertEqual(c["sites"], {"TJL": 700, "UM": 800, "UT": 900})
        self.assertEqual(c["p90"], 900)                                 # the least age by which 90% had died

    def test_the_90th_percentile_rule(self):
        self.assertEqual(A.p90_dead(list(range(1, 11))), 9)
        self.assertEqual(A.p90_dead(list(range(1, 12))), 10)

    def test_a_site_with_no_deaths_is_refused(self):
        with self.assertRaises(A.Refused):
            A.summary(full({("ACA_lo", "UM", "f"): [(300, False)]}))


class Verdict(unittest.TestCase):
    def ok(self):
        g = {f"{k}_{x}_{d}": 0.0 for k in ("median", "p90") for x in A.SEXES for d in A.DOSES}
        g.update({"median_m_ACA_mid": 0.17, "median_m_ACA_hi": 0.16, "p90_m_ACA_lo": 0.11, "p90_m_ACA_mid": 0.11,
                  "p90_m_ACA_hi": 0.08, "median_f_ACA_mid": 0.05, "median_f_ACA_hi": 0.04})
        return g

    def test_each_condition_can_refute(self):
        self.assertEqual(A.verdict(self.ok())[0], 1)
        for k, v in (("median_m_ACA_mid", 0.0849), ("median_m_ACA_hi", 0.0799), ("p90_m_ACA_lo", 0.0549),
                     ("p90_m_ACA_mid", 0.0549), ("p90_m_ACA_hi", 0.0399), ("median_f_ACA_mid", 0.17),
                     ("median_f_ACA_hi", 0.2)):
            with self.subTest(k=k):
                self.assertEqual(A.verdict(dict(self.ok(), **{k: v}))[0], 0)

    def test_thresholds_are_inclusive(self):
        g = self.ok()
        g.update({f"median_m_{d}": v for d, v in A.MEDIAN_GAIN.items()})
        g.update({f"p90_m_{d}": v for d, v in A.P90_GAIN.items()})
        self.assertEqual(A.verdict(g)[0], 1)

    def test_gains(self):
        s = A.summary(full({("ACA_mid", s, "m"): [(1000, True)] for s in A.SITES}))
        g = A.gains(s)
        self.assertAlmostEqual(g["median_m_ACA_mid"], 0.25)
        self.assertEqual(g["median_f_ACA_mid"], 0.0)


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

    def test_tables(self):
        self.assertEqual(self.out["table1_matched"], 23)                   # the female median at 1,000 ppm: 932, 933
        self.assertEqual(self.out["table2_matched"], 24)
        self.assertEqual(self.out["median_f"], "889/887/932/922")
        self.assertEqual(self.out["deaths"], "m 273/147/161/163; f 287/139/142/152")

    def test_the_papers_log_rank_p_values(self):
        self.assertEqual(self.out["logrank_p"], "m 2.93e-06/6.45e-09/1.06e-08; f 3.30e-02/2.71e-03/6.09e-03")

    def test_the_registered_test(self):
        self.assertAlmostEqual(self.out["inc_median_m_mid"], 975 / 830 - 1, places=6)
        self.assertAlmostEqual(self.out["inc_p90_m_hi"], 1181 / 1089 - 1, places=6)
        self.assertEqual(self.out["test_passed"], 1)


if __name__ == "__main__":
    unittest.main()
