"""NDGA and aspirin in the ITP's 2004 cohort (itp/strong2008.py): the verdict at and either side of each clause; each
refusal of the rows (cohort, site, age, status, group, design); the direction of the log-rank test; the test of three
groups against the two-group one and on identical groups; the reading of printed p values; and, with the claim's
workbook at inputs/ (or STRONG2008_INPUTS), the recount itself.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_strong2008", os.path.join(HERE, "..", "itp", "strong2008.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

INPUTS = os.environ.get("STRONG2008_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = os.path.isfile(os.path.join(INPUTS, M.INPUT[0]))


def row(group="NDGA", site="UM", sex="m", status="dead", dead="1", age="900", dose=None, start=None, cohort="C2004"):
    dose_, start_ = M.DESIGN.get(group, ("1", "9"))
    return {"population": "UM-HET3", "cohort": cohort, "site": site, "sex": sex, "id": "X", "group": group,
            "dose": dose if dose is not None else dose_, "age_initiation": start if start is not None else start_,
            "status": status, "dead": dead, "age": age}


class Verdict(unittest.TestCase):
    def test_at_and_beside_each_clause(self):
        ps, oes = {"NDGA": 0.0499, "Aspirin": 0.0499}, {"NDGA": 0.0, "Aspirin": -0.1}
        self.assertTrue(all(M.conditions(ps, oes).values()))
        for ps2, oes2 in (({"NDGA": 0.05, "Aspirin": 0.01}, oes), ({"NDGA": 0.01, "Aspirin": 0.05}, oes),
                          (ps, {"NDGA": 0.01, "Aspirin": -1.0}), (ps, {"NDGA": -1.0, "Aspirin": 0.01})):
            with self.subTest(ps=ps2, oes=oes2):
                self.assertEqual(sum(M.conditions(ps2, oes2).values()), 3)


class Rows(unittest.TestCase):
    def test_a_good_row_is_read(self):
        mice = M.mice_from_rows([row(), row("Control", status="removed", dead="0", age="400"), row("NFP", sex="f")])
        self.assertEqual(mice[("NDGA", "UM", "m")], [(900, True)])
        self.assertEqual(mice[("Control", "UM", "m")], [(400, False)])
        self.assertEqual(mice[("NFP", "UM", "f")], [(900, True)])

    def test_each_refusal(self):
        bad = [row(cohort="C2005"), row(site="XX"), row(sex="u"), row(age="900.5"), row(age=""),
               row(status="dead", dead="0"), row(status="alive", dead="0"), row(group="Rapa"),
               row(dose="800"), row(start="4"), row("Aspirin", start="9"), row("Control", dose="21")]
        for r in bad:
            with self.subTest(row=r), self.assertRaises(M.Refused):
                M.mice_from_rows([r])

    def test_the_controls_design_is_empty_start(self):
        M.mice_from_rows([row("Control", start="")])  # an empty cell reads as no starting age
        with self.assertRaises(M.Refused):
            M.mice_from_rows([row("Control", start="0")])


def group(ages, removed=()):
    return [(a, True) for a in ages] + [(a, False) for a in removed]


class Statistics(unittest.TestCase):
    def test_direction_follows_the_longer_lived(self):
        short, long_ = group([500, 520, 540, 560, 580]), group([700, 720, 740, 760, 780])
        self.assertLess(M.observed_minus_expected([(short, long_)]), 0)
        self.assertGreater(M.observed_minus_expected([(long_, short)]), 0)

    def test_three_groups_reduce_to_two(self):
        a, b = group([500, 610, 640, 700, 810], [650]), group([560, 690, 720, 800, 900, 950], [600])
        self.assertAlmostEqual(M.logrank_k_p([a, b]), M.cana.logrank_strat_p([(a, b)]), places=12)

    def test_identical_groups_give_one(self):
        a = group([500, 610, 640, 700, 810], [650])
        self.assertAlmostEqual(M.logrank_k_p([a, list(a), list(a)]), 1.0, places=12)

    def test_three_groups_against_a_known_chi_square(self):
        # one death each at 1, 2 and 3 in groups that start equal: a chi-square computed by hand
        a, b, c = group([1]), group([2]), group([3])
        # at t=1: n=(1,1,1), d=(1,0,0); t=2: n=(0,1,1), d=(0,1,0); t=3: n=(0,0,1): skipped (n < 2)
        u = [1 - 1 / 3, -1 / 3 + 1 - 1 / 2]
        v00, v01, v11 = (1 / 3) * (2 / 3), -(1 / 3) * (1 / 3), (1 / 3) * (2 / 3) + (1 / 2) * (1 / 2)
        det = v00 * v11 - v01 * v01
        chi2 = (u[0] * (v11 * u[0] - v01 * u[1]) + u[1] * (v00 * u[1] - v01 * u[0])) / det
        self.assertAlmostEqual(M.logrank_k_p([a, b, c]), __import__("math").exp(-chi2 / 2), places=12)

    def test_printed_p_values(self):
        self.assertTrue(M.as_printed(0.00056188, "0.0006"))
        self.assertTrue(M.as_printed(0.010571, "0.01"))
        self.assertFalse(M.as_printed(0.0151, "0.01"))
        self.assertTrue(M.as_printed(0.05107, "0.051"))
        self.assertTrue(M.as_printed(0.2075, "ns"))
        self.assertFalse(M.as_printed(0.0499, "ns"))


@unittest.skipUnless(HAVE, "needs the claim's workbook at inputs/ or STRONG2008_INPUTS")
class Recount(unittest.TestCase):
    def test_the_cohort(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            out, detail = M.run("0" * 64, inputs=INPUTS, results=d)
        self.assertEqual(out["test_passed"], 1)
        self.assertEqual((out["p_as_printed"], out["sites_as_printed"], out["nulls_as_printed"]), (2, 6, 6))
        self.assertEqual(out["n_m"], "Control 379 (350 dead); NDGA 180 (169 dead); Aspirin 180 (168 dead)")
        self.assertLess(out["logrank_p_ndga"], out["logrank_p_aspirin"])
        self.assertLess(out["sites_ctl_p_m"], 0.001)
        self.assertGreater(out["sites_ctl_p_f"], 0.05)


if __name__ == "__main__":
    unittest.main()
