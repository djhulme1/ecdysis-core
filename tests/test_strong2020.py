"""The ITP's 2015 cohort (itp/strong2020.py): the rows' checks and refusals, the seven conditions at and beside their
bounds, the printed p read to its decimals, the seed refused, and, with the workbook at inputs/ (or ITP_INPUTS), the
cohort's counts and designs.

Run with: python3 -m unittest tests.test_strong2020
"""

import importlib.util
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_strong2020", os.path.join(HERE, "..", "itp", "strong2020.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)
INPUTS = os.environ.get("ITP_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = os.path.isfile(os.path.join(INPUTS, M.INPUT[0]))


def row(**kw):
    r = {"population": "UM-HET3", "cohort": "C2015", "site": "UT", "sex": "f", "group": M.ALT, "dose": "42",
         "age_initiation": "20 but every other", "status": "dead", "dead": "1", "age": "950"}
    r.update(kw)
    return r


def every_group():
    """One dead female per group, each with its design, so that the one-design rule is met."""
    rows = [row(group=g, dose=d, age_initiation=a) for g, (d, a) in M.DESIGN.items()]
    rows += [row(group=g, dose="x", age_initiation="y") for g in M.OTHERS]
    return rows


class Rows(unittest.TestCase):
    def test_accepts(self):
        rows = every_group() + [row(group="Control", dose="0", age_initiation=None, status="removed", dead="0",
                                    age="700.0", site="TJL", sex="m")]
        mice, designs = M.mice_from_rows(rows)
        self.assertEqual(mice[(M.ALT, "UT", "f")], [(950, True)])
        self.assertEqual(mice[("Control", "TJL", "m")], [(700, False)])
        self.assertEqual(designs[M.SHORT], ("42", "20 thru 23"))
        self.assertEqual(sum(len(v) for v in mice.values()), 9)

    def test_refuses(self):
        for bad in (row(cohort="C2014"), row(population="B6"), row(site="XX"), row(sex="u"), row(group="Rapa"),
                    row(dose="14"), row(age_initiation="20"), row(status="dead", dead="0"),
                    row(status="removed", dead="1"), row(age="950.5"), row(age="")):
            with self.subTest(bad=bad):
                with self.assertRaises(M.Refused):
                    M.mice_from_rows(every_group() + [bad])

    def test_refuses_two_designs_in_one_group(self):
        with self.assertRaises(M.Refused):
            M.mice_from_rows(every_group() + [row(group="DMAG", dose="x", age_initiation="z")])

    def test_refuses_a_missing_group(self):
        with self.assertRaises(M.Refused):
            M.mice_from_rows([r for r in every_group() if r["group"] != "MitoQ"])


def passing():
    med = {("Control", "m"): 800, ("Control", "f"): 900}
    for g in M.PROTOCOLS:
        for x in M.SEXES:
            med[(g, x)] = 850 if x == "m" else 1000
    med[(M.ALT, "f")] = 950
    med[(M.SHORT, "f")] = 920
    lr = {(g, x): 0.001 for g in M.PROTOCOLS for x in M.SEXES}
    lr[(M.SHORT, "f")] = 0.2
    return med, lr, 0.01


class Conditions(unittest.TestCase):
    def test_all_hold(self):
        med, lr, ac = passing()
        cond = M.conditions(med, lr, ac)
        self.assertEqual(len(cond), 7)
        self.assertTrue(all(cond.values()), cond)

    def test_each_fails_alone(self):
        cases = []
        for g in (M.CONT, M.ALT):
            for x in M.SEXES:
                cases.append(("lr", (g, x), 0.05, 6))                   # p of 0.05 is not below it
                cases.append(("med", (g, x), 800 if x == "m" else 900, 6))  # equal to the controls' is not higher
        # continuous in females no higher than the controls' cannot fail alone: alternating, below it, fails too
        cases[cases.index(("med", (M.CONT, "f"), 900, 6))] = ("med", (M.CONT, "f"), 900, 5)
        cases += [("lr", (M.SHORT, "m"), 0.05, 6), ("med", (M.SHORT, "m"), 790, 6)]
        for kind, key, value, held in cases:
            with self.subTest(kind=kind, key=key, value=value):
                med, lr, ac = passing()
                (lr if kind == "lr" else med)[key] = value
                cond = M.conditions(med, lr, ac)
                self.assertEqual(sum(cond.values()), held, cond)

    def test_three_months_in_females(self):
        med, lr, ac = passing()
        lr[(M.SHORT, "f")] = 0.0499
        self.assertEqual(sum(M.conditions(med, lr, ac).values()), 6)    # a benefit there refutes
        med[(M.SHORT, "f")] = 880
        self.assertEqual(sum(M.conditions(med, lr, ac).values()), 7)    # a harm does not
        med[(M.SHORT, "f")], lr[(M.SHORT, "f")] = 920, 0.05
        self.assertEqual(sum(M.conditions(med, lr, ac).values()), 7)    # nor a p of 0.05

    def test_alternating_against_continuous(self):
        med, lr, ac = passing()
        self.assertEqual(sum(M.conditions(med, lr, 0.05).values()), 6)
        med[(M.ALT, "f")] = med[(M.CONT, "f")]
        self.assertEqual(sum(M.conditions(med, lr, ac).values()), 6)


class Printed(unittest.TestCase):
    def test_to_its_decimals(self):
        self.assertTrue(M.as_printed(0.00074, "0.0007"))
        self.assertFalse(M.as_printed(0.00076, "0.0007"))
        self.assertTrue(M.as_printed(0.4951, "0.50"))                  # (0.495 itself is 0.49499... in binary)
        self.assertFalse(M.as_printed(0.12, "0.13"))
        self.assertTrue(M.as_printed(0.00009, "<0.0001"))
        self.assertFalse(M.as_printed(0.0001, "<0.0001"))

    def test_the_tables_cover_every_group_and_sex(self):
        self.assertEqual(set(M.TABLE), {(g, x) for g in M.GROUPS for x in M.SEXES})


class Seed(unittest.TestCase):
    def test_refuses_a_bad_seed(self):
        with self.assertRaises(M.Refused):
            M.run("xyz", inputs=os.path.join(HERE, "_never"), results=os.path.join(HERE, "_never"))


@unittest.skipUnless(HAVE, "the workbook is not at inputs/ (or ITP_INPUTS)")
class Cohort(unittest.TestCase):
    def test_counts_and_designs(self):
        rows = M.rapa.read_rows(os.path.join(INPUTS, M.INPUT[0]), M.INPUT[1])
        mice, designs = M.mice_from_rows(rows)
        self.assertEqual(len(rows), 2624)
        for (g, x), printed in M.TABLE.items():
            with self.subTest(group=g, sex=x):
                self.assertEqual(len(M.pooled(mice, g, x)), printed[0])
        for g, d in M.DESIGN.items():
            self.assertEqual(designs[g], d)


if __name__ == "__main__":
    unittest.main()
