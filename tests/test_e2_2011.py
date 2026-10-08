"""The 2011 17aE2 recount on made-up data: rows checked against rule 1 and the groups' designs, the site-mean pooling,
the gains and the verdict's four thresholds, and refusals; with the real workbook (at inputs/ or in ITP_INPUTS), also
Table 1's medians and counts reproduced and the gains as found before registering.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_e2_2011", os.path.join(HERE, "..", "itp", "e2_2011.py"))
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)


def row(site="TJL", sex="m", group="17aE2", age="900", status="dead", dead="1", cohort="C2011", **kw):
    dose, start = E.DESIGN.get(group, ("0", None))
    r = {"population": "UM-HET3", "cohort": cohort, "site": site, "sex": sex, "group": group, "age": age,
         "status": status, "dead": dead, "dose": dose, "age_initiation": start}
    r.update(kw)
    return r


def full(values):
    """Rows for every group, site and sex: eight deaths at age a and two at a + 100 (so the median is a and the 90th
    percentile a + 100), with values {(group, sex): (a at TJL, a at UM, a at UT)} overriding the default 800."""
    rows = []
    for g in E.GROUPS:
        for sex in E.SEXES:
            ages = values.get((g, sex), (800, 800, 800))
            for s, a in zip(E.SITES, ages):
                rows += [row(site=s, sex=sex, group=g, age=str(a))] * 8
                rows += [row(site=s, sex=sex, group=g, age=str(a + 100))] * 2
    return rows


class Rows(unittest.TestCase):
    def test_kept_rows(self):
        m = E.mice_from_rows([row(), row(group="Control", status="removed", dead="0", age="400"),
                              row(group="Prot", sex="f", site="UT")])
        self.assertEqual(m[("17aE2", "TJL", "m")], [(900, True)])
        self.assertEqual(m[("Control", "TJL", "m")], [(400, False)])
        self.assertEqual(m[("Prot", "UT", "f")], [(900, True)])

    def test_refusals(self):
        for bad in (row(age="900.5"), row(status="dead", dead="0"), row(cohort="C2012"), row(site="XX"), row(age=""),
                    row(group="Rapa"), row(dose="4.8"), row(age_initiation="16"), row(group="Control", dose="14.4"),
                    row(population="C57BL/6")):
            with self.subTest(bad=bad), self.assertRaises(E.cana.Refused):
                E.mice_from_rows([bad])
        self.assertEqual(E.mice_from_rows([row(group="Control", age_initiation="")])[("Control", "TJL", "m")],
                         [(900, True)])


class Pooling(unittest.TestCase):
    def test_site_means_and_gains(self):
        mice = E.mice_from_rows(full({("Control", "m"): (700, 800, 900), ("17aE2", "m"): (840, 950, 1060)}))
        s = E.summarise(mice, "m")
        self.assertEqual(s["Control"]["Pool"]["median"], 800)
        self.assertEqual(s["17aE2"]["Pool"]["median"], 950)
        self.assertEqual(s["17aE2"]["Pool"]["p90"], 1050)
        self.assertEqual(s["Control"]["Pool"]["dead"], 30)
        g = E.gains(s)
        self.assertAlmostEqual(g[0], 950 / 800 - 1)
        self.assertAlmostEqual(g[1], 1050 / 900 - 1)

    def test_a_site_with_no_deaths_is_refused(self):
        rows = [r for r in full({}) if not (r["group"] == "UDCA" and r["site"] == "UM" and r["sex"] == "f")]
        with self.assertRaises(E.cana.Refused):
            E.summarise(E.mice_from_rows(rows), "f")


class Verdict(unittest.TestCase):
    def test_thresholds(self):
        self.assertEqual(E.verdict((0.095, 0.06), (0.094, 0.059)), 1)
        self.assertEqual(E.verdict((0.0949, 0.06), (0.0, 0.0)), 0)
        self.assertEqual(E.verdict((0.2, 0.0599), (0.0, 0.0)), 0)
        self.assertEqual(E.verdict((0.2, 0.2), (0.095, 0.0)), 0)
        self.assertEqual(E.verdict((0.2, 0.2), (0.0, 0.06)), 0)


def inputs_dir():
    d = os.environ.get("ITP_INPUTS") or os.path.join(HERE, "..", "inputs")
    return d if os.path.isfile(os.path.join(d, E.INPUT[0])) else None


@unittest.skipUnless(inputs_dir(), "the workbook is not at inputs/ (or ITP_INPUTS)")
class TheWorkbook(unittest.TestCase):
    def test_as_found_before_registering(self):
        with tempfile.TemporaryDirectory() as d:
            out, detail = E.run(inputs=inputs_dir(), results=d)
        self.assertEqual((out["n_m_control"], out["n_m_e2"]), (294, 144))
        self.assertEqual(out["table1_matched"], 33)
        medians = [r for r in detail["table1"]["rows"]]
        self.assertTrue(all(r["printed"][1] == r["data"][1] and r["printed"][0] == r["data"][0] for r in medians))
        self.assertAlmostEqual(out["inc_median_m"], 925.3333 / 779.5 - 1, places=4)
        self.assertEqual(out["test_passed"], 1)


if __name__ == "__main__":
    unittest.main()
