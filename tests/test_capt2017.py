"""Captopril in the ITP's 2017 cohort (itp/capt2017.py): each refusal of the rows (population, cohort, site, sex, age,
status, the two groups' designs, a missing group); the pooled median of the dead and the gain; the verdict at and
beside each of its four conditions; the reading of printed p values; the known-answer controls; the seed refused; and,
with the workbook at inputs/ (or CAPT_INPUTS), its structure (the counts of the dead and the removed in the two groups,
as Table 1 prints the dead), which computes no lifespan statistic.

Run with: python3 -m unittest discover -s tests -p test_capt2017.py
"""

import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_capt2017", os.path.join(HERE, "..", "itp", "capt2017.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

INPUTS = os.environ.get("CAPT_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = all(os.path.isfile(os.path.join(INPUTS, name)) for name, _ in M.INPUTS.values())


def row(group="Capt", site="UM", sex="f", status="dead", dead="1", age="900", dose=None, start=None,
        population="UM-HET3", cohort="C2017"):
    dose_, start_ = M.DESIGN.get(group, ("1", "9"))
    return {"population": population, "cohort": cohort, "site": site, "sex": sex, "id": "X", "group": group,
            "dose": dose if dose is not None else dose_, "age_initiation": start if start is not None else (start_ or ""),
            "status": status, "dead": dead, "age": age}


def full(*extra):
    return [row(g, s, x) for g in M.DESIGN for s in M.SITES for x in M.SEXES] + list(extra)


class Rows(unittest.TestCase):
    def test_good_rows_are_read(self):
        mice = M.mice_from_rows(full(row("Control", status="removed", dead="0", age="400"), row("Leu", dose="40000")))
        self.assertEqual(mice[("Capt", "UM", "f")], [(900, True)])
        self.assertEqual(sorted(mice[("Control", "UM", "f")]), [(400, False), (900, True)])
        self.assertEqual(mice[("Leu", "UM", "f")], [(900, True)])                    # outside the design, kept as read

    def test_each_refusal(self):
        bad = [row(population="B6"), row(cohort="C2016"), row(site="XX"), row(sex="u"), row(age="900.5"), row(age=""),
               row(status="dead", dead="0"), row(status="alive", dead="0"), row(dose="90"), row(start="9"),
               row("Control", dose="180"), row("Control", start="5")]
        for r in bad:
            with self.subTest(row=r), self.assertRaises(M.Refused):
                M.mice_from_rows(full(r))

    def test_a_missing_group_is_refused(self):
        rows = [r for r in full() if not (r["group"] == "Capt" and r["site"] == "UT" and r["sex"] == "m")]
        with self.assertRaises(M.Refused):
            M.mice_from_rows(rows)


class Statistics(unittest.TestCase):
    def test_pooled_median_of_the_dead(self):
        mice = M.mice_from_rows(full(row(age="800"), row(age="1000", site="TJL"), row(age="5", status="removed",
                                                                                         dead="0")))
        ms = M.pooled(mice, "Capt", "f", M.SITES)
        self.assertEqual(M.median_of_dead(ms), 900)                    # 900 x 3, 800, 1000: the removed 5 left out
        self.assertEqual(len(M.dead(ms)), 5)

    def test_summary_gain_and_tests(self):
        rows = [row("Control", s, x, age=str(800 + 10 * k)) for s in M.SITES for x in M.SEXES for k in range(6)]
        rows += [row("Capt", s, x, age=str(860 + 10 * k)) for s in M.SITES for x in M.SEXES for k in range(6)]
        mice = M.mice_from_rows(rows)
        s = M.summary(mice, "f", M.SITES, "cana")
        self.assertAlmostEqual(s["gain"], 885 / 825 - 1)
        self.assertLess(s["p"], 0.05)
        self.assertEqual(M.summary(mice, "f", M.TWO, "cana")["n_capt"], 12)


class Verdict(unittest.TestCase):
    def test_at_and_beside_each_condition(self):
        f3, f2 = {"gain": 0.02, "p": 0.0499}, {"gain": 0.02, "p": 0.0499}
        self.assertTrue(all(M.conditions(f3, f2).values()))
        for a, b in (({**f3, "gain": 0.0199}, f2), ({**f3, "p": 0.05}, f2), (f3, {**f2, "gain": 0.019}),
                     (f3, {**f2, "p": 0.2})):
            with self.subTest(a=a, b=b):
                self.assertEqual(sum(M.conditions(a, b).values()), 3)


class Printed(unittest.TestCase):
    def test_p_values(self):
        self.assertTrue(M.p_as_printed(0.0021, "0.002"))
        self.assertFalse(M.p_as_printed(0.0026, "0.002"))
        self.assertTrue(M.p_as_printed(0.0004, "0.001"))             # Table 1 prints 0.001 for anything below it
        self.assertTrue(M.p_as_printed(0.0032, "0.0032"))
        self.assertTrue(M.p_as_printed(0.2, "< 0.26"))
        self.assertFalse(M.p_as_printed(0.3, "< 0.26"))


class Controls(unittest.TestCase):
    def test_known_answers(self):
        self.assertTrue(all(M.controls_known().values()))


class Seed(unittest.TestCase):
    def test_refuses_a_bad_seed(self):
        with self.assertRaises(M.Refused):
            M.run("xyz", inputs=os.path.join(HERE, "_never"), results=os.path.join(HERE, "_never"))


@unittest.skipUnless(HAVE, "the C2017 workbook is not at inputs/ (or CAPT_INPUTS)")
class Workbook(unittest.TestCase):
    def test_structure(self):
        name, sha = M.INPUTS["C2017"]
        mice = M.mice_from_rows(M.rapa.read_rows(os.path.join(INPUTS, name), sha))
        counts = {(g, x): (len(M.dead(M.pooled(mice, g, x, M.SITES))),
                           sum(1 for s in M.SITES for _, d in mice[(g, s, x)] if not d))
                  for g in M.DESIGN for x in M.SEXES}
        self.assertEqual(counts[("Capt", "f")], (132, 4))
        self.assertEqual(counts[("Control", "f")], (276, 4))
        self.assertEqual(counts[("Capt", "m")], (150, 6))
        self.assertEqual(counts[("Control", "m")], (285, 15))


if __name__ == "__main__":
    unittest.main()
