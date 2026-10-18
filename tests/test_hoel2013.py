"""Hoel, Albantakis & Tononi 2013's causal emergence check (ce/hoel2013.py): EI and its parts, macro rows, the
coarse-grainings and their count, state-dependent information and the two-decimal comparison, on systems small enough
to work by hand; the builders of the paper's two systems are checked for the rules they state, but no EI of either is
computed here.

Run with: python3 -m unittest tests.test_hoel2013
"""

import decimal
import importlib.util
import math
import os
import sys
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("ce_hoel2013", os.path.join(HERE, "..", "ce", "hoel2013.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)


def h(p):
    return -sum(x * math.log2(x) for x in p if x > 0)


class Measures(unittest.TestCase):
    def test_fig1_systems(self):
        self.assertTrue(M.fig1_controls())

    def test_noisy_channel_by_hand(self):
        # one element: on next for certain when on, with probability 1/2 when off
        rows = [{(0,): Fraction(1, 2), (1,): Fraction(1, 2)}, {(1,): Fraction(1)}]
        m = M.exact_measures(rows)
        self.assertAlmostEqual(float(m["ei"]), h([0.75, 0.25]) - 0.5, places=14)
        self.assertAlmostEqual(float(m["ei2"]), float(m["ei"]), places=14)
        self.assertAlmostEqual(float(m["det"]), 1 - 0.5, places=14)                  # mean row entropy 1/2 bit
        self.assertAlmostEqual(float(m["deg"]), 1 - h([0.75, 0.25]), places=14)
        a, b = M.float_ei([[0.5, 0.5], [0.0, 1.0]])
        self.assertAlmostEqual(a, float(m["ei"]), places=14)
        self.assertAlmostEqual(b, float(m["ei"]), places=14)

    def test_one_state_model(self):
        m = M.exact_measures([{(0,): Fraction(1)}])
        self.assertEqual((float(m["ei"]), float(m["eff"])), (0.0, 0.0))

    def test_state_information(self):
        ident = {(0,): {(0,): Fraction(1)}, (1,): {(1,): Fraction(1)}}
        c, e = M.state_info(ident, (1,))
        self.assertAlmostEqual(float(c), 1.0, places=14)
        self.assertAlmostEqual(float(e), 1.0, places=14)
        flat = {(0,): {(0,): Fraction(1, 2), (1,): Fraction(1, 2)}, (1,): {(0,): Fraction(1, 2), (1,): Fraction(1, 2)}}
        c, e = M.state_info(flat, (1,))
        self.assertAlmostEqual(float(c), 0.0, places=14)
        self.assertAlmostEqual(float(e), 0.0, places=14)

    def test_two_decimals(self):
        D = decimal.Decimal
        self.assertTrue(M.two_decimals(D("1.154"), "1.15"))
        self.assertTrue(M.two_decimals(D("1.156"), "1.15"))     # cut
        self.assertTrue(M.two_decimals(D("1.149"), "1.15"))     # rounded
        self.assertFalse(M.two_decimals(D("1.141"), "1.15"))
        self.assertTrue(M.two_decimals(D("3.0000000001"), "3.00"))
        self.assertFalse(M.two_decimals(D("2.98"), "3.00"))


class CoarseGrainings(unittest.TestCase):
    def test_partitions_and_class_maps(self):
        self.assertEqual(sum(1 for _ in M.set_partitions(range(4))), 15)
        self.assertEqual(sorted(M.class_maps(2)), [(0, 0, 1), (0, 1, 0), (0, 1, 1), (0, 1, 2)])
        self.assertEqual(len(M.class_maps(2, 1)), 5)
        self.assertEqual([M.bell(m) for m in range(6)], [1, 1, 2, 5, 15, 52])

    def test_two_element_models(self):
        ms = M.models(2)
        self.assertEqual(len(ms), 4)                            # the pair, by each partition of its counts 0..2
        self.assertEqual(M.count_models(2), 4)
        self.assertEqual(len(M.models(2, 1)), M.count_models(2, True))

    def test_macro_rows_of_a_swap(self):
        swap = M.micro_tpm(2, lambda s, i: Fraction(s[1 - i]))
        rows = M.macro_rows(swap, M.paper_macro(((0, 1),)))
        self.assertEqual(rows, {(0,): {(0,): Fraction(1)}, (1,): {(1,): Fraction(1)}})
        self.assertAlmostEqual(float(M.exact_measures(list(rows.values()))["ei"]), 1.0, places=14)
        micro_list = list(swap)
        pos = {s: i for i, s in enumerate(micro_list)}
        tf = [[(pos[t], float(p)) for t, p in swap[s].items()] for s in micro_list]
        a, b = M.float_macro_ei(tf, micro_list, M.paper_macro(((0, 1),)))
        self.assertAlmostEqual(a, 1.0, places=14)

    def test_bijection_search(self):
        ms, eis, _ = M.search(M.shift_tpm(3), 3)
        self.assertEqual(len(ms), M.count_models(3))
        self.assertLess(max(eis), 3 - 1e-9)


class Builders(unittest.TestCase):
    def test_fig2_rule(self):
        t = M.fig2_tpm()
        self.assertEqual(len(t), 16)
        for row in t.values():
            self.assertEqual(sum(row.values()), 1)
        self.assertEqual(t[(1, 1, 1, 1)], {(1, 1, 1, 1): Fraction(1)})
        # C and D on: A and B on for certain; A and B off: C and D each on with probability 3/10
        self.assertEqual(t[(0, 0, 1, 1)][(1, 1, 0, 0)], Fraction(7, 10) ** 2)
        self.assertEqual(t[(0, 0, 0, 0)][(1, 1, 1, 1)], Fraction(3, 10) ** 4)

    def test_fig4_rule(self):
        t = M.fig4_tpm()
        for s, row in t.items():
            self.assertEqual(len(row), 1)
        self.assertEqual(list(t[(1, 1, 0, 0, 0, 0)]), [(0, 0, 1, 1, 0, 0)])
        self.assertEqual(list(t[(0, 0, 0, 0, 1, 1)]), [(1, 1, 0, 0, 0, 0)])
        self.assertEqual(list(t[(1, 0, 1, 1, 1, 0)]), [(0, 0, 0, 0, 1, 1)])


if __name__ == "__main__":
    unittest.main()
