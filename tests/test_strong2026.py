"""The 2021 cohort's recount (itp/strong2026.py): the verdict at and either side of each of its six clauses; each
refusal of the rows (cohort, population, design, group, status, age, site, sex); the tables' bookkeeping and the
printed p's rounding; the analysis and the controls on mice written here; and, with the claim's workbook at inputs/
(or STRONG2026_INPUTS), the recount's shape and its refusal of other bytes. No value of the workbook is asserted here.

Run with: python3 -m unittest discover -s tests -p test_strong2026.py
"""

import importlib.util
import os
import shutil
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_strong2026", os.path.join(HERE, "..", "itp", "strong2026.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

INPUTS = os.environ.get("STRONG2026_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = os.path.isfile(os.path.join(INPUTS, M.INPUT[0]))


def row(group="Epi", site="UM", sex="m", status="dead", dead="1", age="900", dose=None, start=None, **extra):
    dose_, start_ = M.DESIGN.get(group, ("1", "7"))
    r = {"population": "UM-HET3", "cohort": "C2021", "site": site, "sex": sex, "id": "X", "group": group,
         "dose": dose if dose is not None else dose_, "age_initiation": start if start is not None else start_,
         "status": status, "dead": dead, "age": age}
    r.update(extra)
    return r


def synthetic(shift=None, n=4, base=(700, 800, 900, 1000)):
    """Rows for every group, site and sex: n dead mice per cell at the base ages, each agent's shifted by shift[g]
    days, and one removed mouse per cell."""
    shift = shift or {}
    rows = []
    for g in M.GROUPS:
        for s in M.SITES:
            for x in M.SEXES:
                for k in range(n):
                    rows.append(row(group=g, site=s, sex=x, age=str(base[k % len(base)] + shift.get(g, 0))))
                rows.append(row(group=g, site=s, sex=x, status="removed", dead="0", age="400"))
    return rows


class Verdict(unittest.TestCase):
    def test_at_and_beside_each_clause(self):
        rises = {"Epi": 0.025, "Hal": 0.045, "M160": 0.045}
        ps = {"Epi": 0.0499, "Hal": 0.0499, "M160": 0.0499}
        self.assertEqual(len(M.conditions(rises, ps)), 6)
        self.assertTrue(all(M.conditions(rises, ps).values()))
        for g in M.TESTED:
            with self.subTest(rise=g):
                self.assertEqual(sum(M.conditions(dict(rises, **{g: rises[g] - 1e-4}), ps).values()), 5)
            with self.subTest(p=g):
                self.assertEqual(sum(M.conditions(rises, dict(ps, **{g: 0.05})).values()), 5)

    def test_names(self):
        names = list(M.conditions({g: 0 for g in M.TESTED}, {g: 1 for g in M.TESTED}))
        self.assertIn("epicatechin: male median at least 2.5% above the controls'", names)
        self.assertIn("mitoglitazone: log-rank p below 0.05", names)


class Rows(unittest.TestCase):
    def test_reads_the_seven_groups(self):
        rows = [row(), row(group="Control", age="800"), row(group="Hal", status="removed", dead="0", age="700.0"),
                row(group="M160", site="TJL", sex="f"), row(group="2BA"), row(group="DCA"), row(group="For")]
        mice = M.mice_from_rows(rows)
        self.assertEqual(mice[("Epi", "UM", "m")], [(900, True)])
        self.assertEqual(mice[("Control", "UM", "m")], [(800, True)])
        self.assertEqual(mice[("Hal", "UM", "m")], [(700, False)])
        self.assertEqual(mice[("M160", "TJL", "f")], [(900, True)])
        self.assertEqual(sum(len(v) for v in mice.values()), 7)
        self.assertIsNone(M.DESIGN["Control"][1])

    def test_refusals(self):
        for bad in (dict(row(), cohort="C2020"), dict(row(), population="B6"), row(dose="600"), row(start="9"),
                    row(group="Control", start="7"), row(group="Placebo"), row(status="dead", dead="0"),
                    row(status="removed", dead="1"), row(status="censored", dead="0"), row(age="900.5"), row(age=""),
                    row(site="NIA"), row(sex="x")):
            with self.subTest(bad=bad), self.assertRaises(M.Refused):
                M.mice_from_rows([bad])


class Tables(unittest.TestCase):
    def test_bookkeeping(self):
        self.assertEqual(sum(1 for k in M.TABLES if k[1] == "Pool"), 14)
        self.assertEqual(len(M.TABLES), 56)
        self.assertEqual(set(M.PRINTED_P), {k for k in M.TABLES if k[0] != "Control"})
        for g in M.GROUPS:
            for x in M.SEXES:
                with self.subTest(group=g, sex=x):       # Table 1's counts are its sites' summed, as printed
                    self.assertEqual(M.TABLES[(g, "Pool", x)][0], sum(M.TABLES[(g, s, x)][0] for s in M.SITES))
        self.assertEqual(len(M.OUTPUTS), 19)
        self.assertEqual(len(set(M.OUTPUTS)), 19)

    def test_as_printed(self):
        self.assertTrue(M.s08.as_printed(0.0371, "0.037"))
        self.assertTrue(M.s08.as_printed(0.6049, "0.6"))
        self.assertTrue(M.s08.as_printed(0.99999, "1.00"))
        self.assertFalse(M.s08.as_printed(0.0449, "0.037"))


class Analysis(unittest.TestCase):
    def test_on_mice_written_here(self):
        rows = synthetic({"Epi": 20, "Hal": 40, "M160": 39, "2BA": -10})
        mice = M.mice_from_rows(rows)
        values, detail, ps = M.analyse(mice)
        self.assertEqual(values["median_m_control"], 850.0)               # 12 dead: 700 x3, 800 x3, 900 x3, 1000 x3
        self.assertEqual((values["median_m_epi"], values["median_m_hal"], values["median_m_mit"]), (870.0, 890.0, 889.0))
        self.assertAlmostEqual(values["rise_epi"], 870 / 850 - 1, places=6)   # 2.35%: below 2.5%
        self.assertAlmostEqual(values["rise_hal"], 890 / 850 - 1, places=6)   # 4.71%: above 4.5%
        self.assertAlmostEqual(values["rise_mit"], 889 / 850 - 1, places=6)   # 4.59%
        self.assertEqual(values["n_m"], "Control 15 (12 dead); Epi 15 (12 dead); Hal 15 (12 dead); M160 15 (12 dead)")
        cond = detail["conditions"]
        self.assertFalse(cond["epicatechin: male median at least 2.5% above the controls'"])
        self.assertTrue(cond["halofuginone: male median at least 4.5% above the controls'"])
        self.assertFalse(cond["halofuginone: log-rank p below 0.05"])        # twelve deaths a group are too few
        self.assertEqual(values["test_passed"], 0)
        self.assertLess(detail["logrank"]["Hal m"]["observed_minus_expected"], 0)
        self.assertGreater(detail["logrank"]["2BA m"]["observed_minus_expected"], 0)
        self.assertTrue(values["tables_matched"].startswith("Table 1: "))
        self.assertIn(" of 42, p ", values["tables_matched"])
        self.assertIn("Tables S1a and S1b: ", values["tables_matched"])
        self.assertIn(" of 126, p ", values["tables_matched"])
        self.assertTrue(values["tables_matched"].endswith(" of 72"))
        self.assertEqual(len(detail["tables"]["rows"]), 56)
        ctl = M.controls_of(rows, mice, ps)
        self.assertEqual(len(ctl), 6)
        self.assertFalse(ctl["it holds 2,388 mice, every row as rule 1 requires"])    # these are not the 2,388
        self.assertEqual(sum(ctl.values()), 5)

    def test_a_clear_gain_passes(self):
        base = tuple(range(600, 1000, 8))                                  # 50 ages a cell
        rows = synthetic({"Epi": 120, "Hal": 120, "M160": 120}, n=50, base=base)
        values, detail, ps = M.analyse(M.mice_from_rows(rows))
        self.assertEqual(values["conditions_met"], 6)
        self.assertEqual(values["test_passed"], 1)
        self.assertLess(values["logrank_p_hal"], 1e-6)
        self.assertEqual(values["wa_p_m"].split("; ")[0].split(" ")[0], "Epi")
        for k, v in values.items():
            if isinstance(v, str):
                self.assertLessEqual(len(v), M.LIMIT, k)


class Seed(unittest.TestCase):
    def test_seed_refused(self):
        with mock.patch.dict(os.environ, {"ECDYSIS_SEED": "not-a-seed"}), self.assertRaises(SystemExit):
            M.main()


@unittest.skipUnless(HAVE, "the claim's workbook is not at inputs/ (or STRONG2026_INPUTS)")
class Recount(unittest.TestCase):
    def test_the_recount_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, detail = M.run("0" * 64, inputs=INPUTS, results=tmp)
        self.assertEqual(tuple(out), M.OUTPUTS)
        self.assertEqual((out["controls_passed"], out["controls_total"]), (6, 6))
        self.assertIn(out["test_passed"], (0, 1))
        self.assertEqual(detail["input"]["rows"], M.ROWS)

    def test_refuses_other_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(os.path.join(INPUTS, M.INPUT[0]), tmp)
            with open(os.path.join(tmp, M.INPUT[0]), "ab") as f:
                f.write(b"\0")
            with self.assertRaises(SystemExit):
                M.run("0" * 64, inputs=tmp, results=tmp)


if __name__ == "__main__":
    unittest.main()
