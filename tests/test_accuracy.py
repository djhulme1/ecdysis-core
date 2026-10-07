"""The accuracy-nudge re-run on made-up data: the exact OLS and cluster2's variance against hand computations, the
sample rules of the do-files, the refusals and the comparison's edges; with the real inputs (at inputs/ or in
ACCURACY_INPUTS), also the published values, the controls, and statsmodels' figures as an outside cross-check.

Run with: python3 -m unittest discover -s tests
"""

import csv
import hashlib
import importlib.util
import io
import os
import tempfile
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("accuracy_check", os.path.join(HERE, "..", "accuracy", "check.py"))
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)


def table(header, rows):
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\r\n")
    w.writerow(header)
    w.writerows(rows)
    return out.getvalue().encode("utf-8")


def study_csv(participants, items=2, dates=None):
    """participants: list of (condition, fb, socialmedia_chk, fake ratings, real ratings), as strings; dates gives
    each participant's (start, end), by default 10/4/2017 for both."""
    header = ["Condition", "FB", "SocialMedia_Chk", "V8", "V9", "StartDate", "EndDate"] + \
             [f"Fake{k}_3" for k in range(1, items + 1)] + [f"Real{k}_3" for k in range(1, items + 1)]
    dates = dates or [("10/4/2017 8:47", "10/4/2017 8:55")] * len(participants)
    return table(header, [[c, fb, chk, st, en, st, en] + list(fk) + list(rl)
                          for (c, fb, chk, fk, rl), (st, en) in zip(participants, dates)])


class Algebra(unittest.TestCase):
    def test_exact_inverse(self):
        inv = A.inverse([[2, 1], [1, 1]])
        self.assertEqual(inv, [[1, -1], [-1, 2]])
        inv = A.inverse([[4, 2, 0], [2, 3, 1], [0, 1, 2]])
        prod = [[sum(Fraction(a) * b for a, b in zip(row, col)) for col in zip(*inv)]
                for row in [[4, 2, 0], [2, 3, 1], [0, 1, 2]]]
        self.assertEqual(prod, [[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        with self.assertRaises(A.Refused):
            A.inverse([[1, 2], [2, 4]])

    def test_a_perfect_fit_has_zero_variance(self):
        # rating = 1 + 5x, so y = (rating - 1) / 5 = x exactly
        xs = [(x, 1) for x in (0, 1, 0, 1, 1, 0)]
        r = A.ols_cluster2(xs, [1 + 5 * x for x, _ in xs], [1, 1, 2, 2, 3, 3], [1, 2, 1, 2, 1, 2])
        self.assertEqual(r["b"], [Fraction(1), Fraction(0)])
        self.assertTrue(all(v == 0 for row in r["V"] for v in row))

    def test_constant_only_matches_the_hand_formula(self):
        # y = (rating - 1) / 5 on a constant: b is the mean, and each piece is q * sum_g (sum e)^2 / n^2
        ratings = [1, 2, 6, 3, 5, 4, 2, 6]
        participants = [1, 1, 2, 2, 3, 3, 4, 4]
        headlines = [1, 2, 1, 2, 1, 2, 1, 2]
        n, k = len(ratings), 1
        y = [Fraction(r - 1, 5) for r in ratings]
        mean = sum(y) / n
        e = [v - mean for v in y]

        def piece(labels, q):
            sums = {}
            for g, v in zip(labels, e):
                sums[g] = sums.get(g, 0) + v
            return q * sum(s * s for s in sums.values()) / (n * n)

        q = lambda g: Fraction(n - 1, n - k) * Fraction(g, g - 1)
        expected = piece(headlines, q(2)) + piece(participants, q(4)) - piece(range(n), Fraction(n, n - k))
        r = A.ols_cluster2([(1,)] * n, ratings, participants, headlines)
        self.assertEqual(r["b"], [mean])
        self.assertEqual(r["V"][0][0], expected)
        self.assertTrue(r["unique_pairs"])
        self.assertEqual((r["participants"], r["headlines"], r["n"]), (4, 2, 8))

    def test_repeated_pairs_cluster_the_third_matrix_by_pair(self):
        ratings = [1, 2, 6, 3, 5, 4, 2, 6]
        participants = [1, 1, 1, 1, 2, 2, 2, 2]
        headlines = [1, 1, 2, 2, 1, 1, 2, 2]               # each pair twice
        n = len(ratings)
        y = [Fraction(r - 1, 5) for r in ratings]
        mean = sum(y) / n
        e = [v - mean for v in y]

        def piece(labels, g):
            sums = {}
            for lab, v in zip(labels, e):
                sums[lab] = sums.get(lab, 0) + v
            return Fraction(n - 1, n - 1) * Fraction(g, g - 1) * sum(s * s for s in sums.values()) / (n * n)

        pairs = list(zip(headlines, participants))
        expected = piece(headlines, 2) + piece(participants, 2) - piece(pairs, 4)
        r = A.ols_cluster2([(1,)] * n, ratings, participants, headlines)
        self.assertFalse(r["unique_pairs"])
        self.assertEqual(r["V"][0][0], expected)


class Sample(unittest.TestCase):
    def test_drop_rules_filter_and_headline_labels(self):
        blob = study_csv([
            ("1", "1", "1", ("1", "6"), ("2", "")),     # kept; one missing rating
            ("2", "2", "1", ("3", "3"), ("3", "3")),    # fb == 2: dropped
            ("2", "1", " ", ("3", "3"), ("3", "3")),    # socialmedia_chk missing: dropped
            ("2", "1", "2", ("4", "4"), ("4", "4")),    # does not share political news: filtered out
            ("", "1", "1", ("5", "5"), ("5", "5")),     # no condition: dropped in Studies 3 and 4
        ])
        rows, info = A.observations(blob, 3, 2)
        self.assertEqual([(o["participant"], o["headline"], o["real"], o["rating"]) for o in rows],
                         [(1, 25, 0, 1), (1, 27, 1, 2), (1, 26, 0, 6)])     # headline k, then its true pair
        self.assertEqual(info["participants_dropped"], 2)
        rows4, _ = A.observations(blob, 4, 2)
        self.assertEqual([o["headline"] for o in rows4], [1, 3, 2])
        everyone, _ = A.observations(blob, 4, 2, filter_political=False)
        self.assertEqual(sorted({o["participant"] for o in everyone}), [1, 4])

    def test_study_5_counts_a_missing_condition_as_a_control(self):
        blob = study_csv([("3", "1", "1", ("1", "2"), ("3", "4")), ("", "1", "1", ("2", "2"), ("2", "2"))])
        rows, info = A.observations(blob, 5, 2)
        self.assertEqual(info["missing_condition_kept"], 1)
        xs, j = A.design(rows, 5)
        self.assertEqual(j, 2)
        self.assertEqual(xs[0], (1, 0, 0, 0, 0, 1))           # treatment, fake headline
        self.assertEqual(xs[-1], (0, 1, 0, 0, 0, 1))          # missing condition: neither treatment
        self.assertEqual([o["headline"] for o in rows if o["participant"] == 1], [1, 3, 2, 4])

    def test_design_for_studies_3_and_4_and_the_swap_control(self):
        rows = [{"cond": 2.0, "real": 1}, {"cond": 1.0, "real": 1}, {"cond": 2.0, "real": 0}]
        self.assertEqual(A.design(rows, 3)[0], [(1, 1, 1, 1), (0, 1, 0, 1), (1, 0, 0, 1)])
        self.assertEqual(A.design(rows, 3, swap_veracity=True)[0], [(1, 0, 0, 1), (0, 0, 0, 1), (1, 1, 1, 1)])
        with self.assertRaises(A.Refused):
            A.design([{"cond": 3.0, "real": 0}], 4)


class Period(unittest.TestCase):
    def test_dates_and_the_span_of_the_participants_used(self):
        self.assertEqual(A.ymd("10/4/2017 8:47"), 20171004)
        self.assertEqual(A.ymd("4/30/2019"), 20190430)
        self.assertEqual(A.ymd(" 12/31/2018 23:59:59 "), 20181231)
        for bad in ("2017-10-04", "13/1/2017", "10/4/17", "", "10/4/2017T08:47"):
            with self.subTest(bad=bad), self.assertRaises(A.Refused):
                A.ymd(bad)
        blob = study_csv([("1", "1", "1", ("1", "2"), ("3", "4")),        # used
                          ("1", "1", "2", ("1", "2"), ("3", "4")),        # filtered out: its dates do not count
                          ("2", "1", "1", ("", ""), ("", ""))],           # no rating: its dates do not count
                         dates=[("11/28/2017", "11/29/2017"), ("1/1/2010", "1/1/2030"), ("1/1/2011", "1/1/2031")])
        _, info = A.observations(blob, 4, 2)
        self.assertEqual((info["first_start"], info["last_end"]), (20171128, 20171129))


class Refusals(unittest.TestCase):
    def test_non_numeric_and_out_of_range_values(self):
        for bad in (("x", "1", "1", ("1", "1"), ("1", "1")), ("1", "1", "1", ("7", "1"), ("1", "1")),
                    ("1", "1", "1", ("2.5", "1"), ("1", "1")), ("1", "1", "1", ("NA", "1"), ("1", "1"))):
            with self.subTest(bad=bad), self.assertRaises(A.Refused):
                A.observations(study_csv([bad]), 3, 2)

    def test_missing_column_and_ragged_rows(self):
        with self.assertRaises(A.Refused):
            A.observations(table(["Condition", "FB"], [["1", "1"]]), 3, 1)
        with self.assertRaises(A.Refused):
            A.read_csv(b"a,b\r\n1\r\n")
        with self.assertRaises(A.Refused):
            A.read_csv(b"A,a\r\n1,2\r\n")

    def test_the_code_must_hold_every_line_followed(self):
        good = {name: ("\r\n".join(["* header"] + ["\t" + line + "\t" for line in lines])).encode("latin-1")
                for name, lines in A.REQUIRED.items()}
        self.assertEqual(A.check_code(good), {name: len(lines) for name, lines in A.REQUIRED.items()})
        for name, lines in A.REQUIRED.items():
            broken = dict(good)
            broken[name] = good[name].replace(lines[-1].encode("latin-1"), b"* removed")
            with self.subTest(name=name), self.assertRaises(A.Refused):
                A.check_code(broken)

    def test_an_input_with_the_wrong_hash_stops_the_run(self):
        with tempfile.TemporaryDirectory() as d:
            for name, _, size in A.INPUTS:
                with open(os.path.join(d, name), "wb") as f:
                    f.write(b"x" * size)
            with self.assertRaises(A.Refused):
                A.load(d)


class Comparison(unittest.TestCase):
    def test_tolerances_and_exact_counts(self):
        est, s, n, p, h = A.PUBLISHED[3]
        self.assertEqual(A.agrees(3, est + 0.00009, s, n, p, h), (True, 5))
        self.assertEqual(A.agrees(3, est - 0.00011, s, n, p, h), (False, 4))
        self.assertEqual(A.agrees(3, est, s * 1.049, n, p, h), (True, 5))
        self.assertEqual(A.agrees(3, est, s * 0.949, n, p, h), (False, 4))
        self.assertEqual(A.agrees(3, est, s, n + 1, p - 1, h), (False, 3))


def inputs_dir():
    d = os.environ.get("ACCURACY_INPUTS") or os.path.join(HERE, "..", "inputs")
    ok = all(os.path.isfile(os.path.join(d, name)) and os.path.getsize(os.path.join(d, name)) == size
             for name, _, size in A.INPUTS)
    return d if ok else None


@unittest.skipUnless(inputs_dir(), "the real inputs are not at inputs/ (or ACCURACY_INPUTS)")
class RealData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out, cls.detail = A.run(inputs=inputs_dir(), results=cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_published_values(self):
        self.assertEqual((self.out["period_from"], self.out["period_to"]), (20171004, 20190502))
        self.assertEqual(self.out["published_matched"], 15)
        self.assertEqual(self.out["test_passed"], 1)
        self.assertEqual(self.out["unique_pairs"], 1)

    def test_statsmodels_agrees(self):
        # statsmodels 0.15.0 on the host: OLS, one-way clustered (use_correction, df_correction) by headline and by
        # participant, and HC1, combined as cluster2 does
        for study, (est, s) in {3: (0.0529429, 0.0107609), 4: (0.0648046, 0.0146652), 5: (0.0542344, 0.0156668)}.items():
            self.assertAlmostEqual(self.out[f"s{study}_estimate"], est, places=7)
            self.assertAlmostEqual(self.out[f"s{study}_se"], s, places=7)
        self.assertAlmostEqual(self.out["s3_se_participant_only"], 0.0111396, places=7)

    def test_the_controls_fail(self):
        self.assertEqual(self.out["controls_passed"], 2)
        swapped = self.detail["controls"]["veracity_swapped"]
        for study in (3, 4, 5):
            self.assertAlmostEqual(swapped[f"s{study}"]["estimate"], -self.out[f"s{study}_estimate"], places=6)


if __name__ == "__main__":
    unittest.main()
