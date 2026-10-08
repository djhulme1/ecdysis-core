"""Salamin's AGM iteration: the digit count read exactly, the excess and the doubling, the two pi series against each
other and the known decimals, Algorithm GL against Brent's two tables and his bounds, the controls that must fail,
the refusals of rules 2, 4 and 5, and a whole run at a small precision.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import math
import os
import tempfile
import unittest
from decimal import Decimal as D
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pi_agm", os.path.join(HERE, "..", "pi", "agm.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


class Digits(unittest.TestCase):
    def test_read_exactly(self):
        self.assertEqual(M.correct_digits(D("1.01e-3")), 2)
        self.assertEqual(M.correct_digits(D("9.99e-9")), 8)
        self.assertEqual(M.correct_digits(D("1e-9")), 9)
        self.assertEqual(M.correct_digits(D("10e-10")), 9)
        self.assertEqual(M.correct_digits(D("1.000000000000000000001e-9")), 8)
        self.assertEqual(M.correct_digits(D("-2.27e-1")), 0)
        self.assertEqual(M.correct_digits(D("0.5")), 0)
        self.assertEqual(M.correct_digits(D("2")), -1)
        with self.assertRaises(M.Refused):
            M.correct_digits(D(0))

    def test_floor_of_rule_4(self):
        pi, _ = M.chudnovsky(1100)
        with M.context(1100):
            near = pi - D("1e-99")
            nearer = pi - D("1e-101")
        self.assertEqual(M.digits_of([near], pi, 1100)[0][:2], (99, True))
        with self.assertRaises(M.Refused):
            M.digits_of([nearer], pi, 1100)
        with self.assertRaises(M.Refused):
            M.digits_of([pi], pi, 1100)
        self.assertEqual(M.digits_of([nearer], pi, 1100, floor=False)[0][0], 101)
        with M.context(1100):
            above = pi + D("3e-7")
        self.assertEqual(M.digits_of([above], pi, 1100)[0][:2], (6, False))


class Excess(unittest.TestCase):
    def test_excess_and_doubling(self):
        ds = [0, 2, 8, 18, 40]
        self.assertEqual(M.excesses(ds), [(1, 4), (2, 2), (3, 4)])
        self.assertTrue(M.doubles(ds))
        self.assertFalse(M.doubles([0, 2, 8, 15]))
        self.assertTrue(M.doubles([5, 2, 4]))          # d_0 is not compared: the test starts at n = 1


class References(unittest.TestCase):
    def test_two_series_agree(self):
        pi, ref = M.references(700)
        self.assertTrue(ref["agree"])
        self.assertTrue(ref["first50"])
        self.assertEqual(ref["chudnovsky_terms"], math.ceil(700 / M.CHUD_DIGITS) + 2)
        self.assertEqual(ref["ramanujan_terms"], math.ceil(700 / M.RAM_DIGITS) + 2)
        self.assertTrue(str(pi).startswith(M.PI50))

    def test_disagreement_is_refused(self):
        wrong = lambda prec: (M.chudnovsky(prec)[0] + D("1e-400"), 0)   # noqa: E731
        with mock.patch.object(M, "ramanujan", wrong):
            _, ref = M.references(700)
            self.assertFalse(ref["agree"])
            with tempfile.TemporaryDirectory() as d, self.assertRaises(M.Refused):
                M.run(precision=600, n_max=6, results=d)


class Iteration(unittest.TestCase):
    def test_first_values(self):
        lows, ups = M.gl(40, 1, upper=True)
        with M.context(40):
            self.assertLess(abs(lows[0] - (D("1.5") + D(2).sqrt())), D("1e-38"))    # (1 + 1/sqrt 2)^2
        self.assertEqual(ups[0], 4)
        self.assertTrue(str(lows[1]).startswith("3.14057925052216824831"))

    def test_brent_tables_and_bounds(self):
        t1, t2, bounds = M.brent()
        self.assertEqual((len(t1), len(t2), len(bounds)), (10, 36, 9))
        self.assertEqual([r for r in t1 if not r["matched"]], [])
        self.assertEqual([(r["n"], r["column"], r["ours"]) for r in t2 if not r["matched"]],
                         [(1, "lower ratio", "0.999656205")])                 # as found before registering
        self.assertTrue(all(r["within"] for r in t1 + t2))
        self.assertTrue(all(b["lower"] and b["upper"] for b in bounds))

    def test_within_one_unit(self):
        self.assertTrue(M.compare(D("0.9996562054"), "0.999656206", "0.999656205")["within"])
        self.assertFalse(M.compare(D("0.9996562049"), "0.999656206", "0.999656205")["within"])
        self.assertTrue(M.compare(D("8.584e-1"), "8.58e-1", "8.58e-1")["matched"])
        self.assertFalse(M.compare(D("8.596e-1"), "8.58e-1", "8.60e-1")["within"])

    def test_tables_would_catch_a_perturbed_iteration(self):
        lows, _ = M.gl(200, 4, b0_shift=D("1e-20"))
        with M.context(200):
            self.assertNotEqual(str(lows[4].quantize(D("1e-24"))), M.TABLE1[4][0])


class Controls(unittest.TestCase):
    def test_controls_hold(self):
        checks, detail = M.controls()
        self.assertEqual(checks, {k: True for k in checks})
        self.assertEqual(len(checks), 6)
        self.assertEqual(detail["linear_digits"][:5], [0, 1, 2, 2, 3])
        self.assertEqual(detail["perturbed_digits"][:4], [0, 2, 8, 18])
        self.assertLess(max(detail["perturbed_digits"]), 32)


class WholeRun(unittest.TestCase):
    def test_small_run(self):
        with tempfile.TemporaryDirectory() as d:
            out, detail = M.run(precision=3000, n_max=9, results=d)
        self.assertEqual(out["digits"], "2,8,18,40,83,170,344,693,1392")
        self.assertEqual((out["d_last"], out["min_excess"], out["min_excess_at"]), (1392, 2, 2))
        self.assertEqual((out["all_below"], out["guards_agree"], out["refs_agree"]), (1, 1, 1))
        self.assertEqual((out["table1_matched"], out["table2_matched"]), (10, 35))
        self.assertEqual(out["controls_passed"], out["controls_total"])
        self.assertEqual(out["test_passed"], 1)
        self.assertEqual(len(out), 18)
        self.assertEqual(detail["guards"]["50"], detail["guards"]["100"])

    def test_guards_that_disagree_are_refused(self):
        original = M.gl

        def fake(prec, n_max, **kw):
            lows, ups = original(prec, n_max, **kw)
            if prec == 700:
                with M.context(prec):
                    lows[3] = lows[3] - D("1e-10")
            return lows, ups

        with mock.patch.object(M, "gl", fake), tempfile.TemporaryDirectory() as d, self.assertRaises(M.Refused):
            M.run(precision=600, n_max=6, results=d)


if __name__ == "__main__":
    unittest.main()
