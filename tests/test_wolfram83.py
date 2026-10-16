"""Wolfram 1983 (ca/wolfram83.py): the step and its numbering, Pascal's triangle and (1 + x + x^2)^t mod 2 built
without the automaton, the dimension estimator, the homogeneity detector, the ring orbits, the chi sequences and the
decision, on inputs other than the claim's own case: no legal rule is evolved from a single site here.

Run with: python3 -m unittest tests.test_wolfram83 (in the pinned scipy-notebook image)
"""

import importlib.util
import math
import os
import random
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("ca_wolfram83", os.path.join(HERE, "..", "ca", "wolfram83.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


class Steps(unittest.TestCase):
    def test_integer_step_matches_cells(self):
        rng = random.Random(7)
        width = 120
        mask = (1 << width) - 1
        for rule in (1, 30, 45, 110, 184, 255):
            for _ in range(10):
                cells = [0] * 30 + [rng.getrandbits(1) for _ in range(60)] + [0] * 30
                row = sum(b << i for i, b in enumerate(cells))
                for _ in range(6):
                    cells = M.step_cells(cells, rule)
                    row = M.step(row, rule, mask)
                    self.assertEqual(row, sum(b << i for i, b in enumerate(cells)), rule)

    def test_fig2(self):
        top, bottom = M.FIG2
        out = M.step_cells([int(c) for c in top], 90)[1:-1]
        self.assertEqual("".join(map(str, out)), bottom)

    def test_numbering(self):
        self.assertEqual([M.rule_bit(90, l, c, r) for l in (0, 1) for c in (0, 1) for r in (0, 1)],
                         [0, 1, 0, 1, 1, 0, 1, 0])
        self.assertFalse(M.is_legal(30))
        self.assertFalse(M.is_legal(1))
        self.assertTrue(M.is_legal(90))
        self.assertEqual(M.legal_rules(), M.LEGAL_PRINTED)
        reversed_bit = lambda rule, l, c, r: (rule >> (7 - (4 * l + 2 * c + r))) & 1
        self.assertNotEqual(M.legal_rules(reversed_bit), M.LEGAL_PRINTED)

    def test_light_cone_on_a_quiescent_rule(self):
        rows, off = M.evolve(110, "1", 64)
        for t, r in enumerate(rows):
            lo, hi = M.edges(r)
            self.assertGreaterEqual(lo, off - t)
            self.assertLessEqual(hi, off + t)


class Constructions(unittest.TestCase):
    def test_pascal_by_lucas(self):
        off = 70
        rows = M.pascal_rows(64, off)
        for t in range(64):
            want = sum(1 << (off + 2 * k - t) for k in range(t + 1) if math.comb(t, k) % 2)
            self.assertEqual(rows[t], want)

    def test_frobenius_against_powers(self):
        off = 70
        rows = M.frobenius_rows(64, off)
        p = 1
        for t in range(64):
            self.assertEqual(rows[t], p << (off - t))
            p = p ^ (p << 1) ^ (p << 2)              # times 1 + x + x^2 over GF(2)

    def test_cones(self):
        rows = M.cone_rows(5, 10, lambda t, x: True)
        self.assertEqual([r.bit_count() for r in rows], [1, 3, 5, 7, 9])


class Dimensions(unittest.TestCase):
    def test_pascal_is_log2_3(self):
        rows = M.pascal_rows(512, 520)
        dm = M.dims(rows, 9)
        self.assertAlmostEqual(dm["d_last"], math.log2(3), places=12)
        self.assertAlmostEqual(dm["d_prev"], math.log2(3), places=12)
        self.assertEqual(dm["rarer"], 1)
        self.assertEqual(M.target_of(dm), "log2 3")

    def test_random_cone_is_not_self_similar(self):
        rows = M.random_cone(512, 520, random.Random(3))
        dm = M.dims(rows, 9)
        self.assertLess(abs(dm["d_last"] - 2), 0.05)
        self.assertIsNone(M.target_of(dm))

    def test_box_dims_on_pascal(self):
        rows = M.pascal_rows(1024, 1026)
        self.assertLess(abs(M.box_dims(rows, 1) - math.log2(3)), 0.01)
        with self.assertRaises(AssertionError):
            M.box_dims(M.pascal_rows(500, 502), 1)

    def test_growth(self):
        self.assertEqual(M.growth([1, 2, 3, 4, 5, 6, 7, 8], 3), [1, 3, 10, 36])


class Homogeneity(unittest.TestCase):
    def test_uniform_cones(self):
        o = 260
        self.assertEqual(M.uniform(M.cone_rows(256, o, lambda t, x: (x + t) % 2 == 0)), (2, 2))
        self.assertEqual(M.uniform(M.cone_rows(256, o, lambda t, x: True)), (1, 1))
        self.assertEqual(M.uniform(M.cone_rows(256, o, lambda t, x: x % 3 == 0)), (3, 1))
        self.assertIsNone(M.uniform(M.pascal_rows(256, o)))

    def test_a_defect_line_is_not_uniform(self):
        o = 260
        rows = M.cone_rows(256, o, lambda t, x: ((x + t) % 2 == 0) != (x >= 5))
        self.assertIsNone(M.uniform(rows))
        self.assertEqual(M.uniform(rows, temporal=False), None)

    def test_spatial_only(self):
        o = 260
        shifting = M.cone_rows(256, o, lambda t, x: (x - t) % 3 == 0)
        self.assertIsNone(M.uniform(shifting))
        self.assertEqual(M.uniform(shifting, temporal=False), (3, None))


class Rings(unittest.TestCase):
    def test_orbits(self):
        self.assertEqual(M.orbit(204, 7), (1, 0))          # the identity
        self.assertEqual(M.orbit(170, 9), (9, 0))          # a shift by one site
        self.assertEqual(M.orbit(0, 5), (1, 1))            # everything erased

    def test_number_theory(self):
        self.assertEqual(M.sord(15), 4)
        self.assertEqual(M.sord(17), 4)
        self.assertEqual(M.sord(3), 1)
        self.assertEqual(M.d2(12), 4)
        self.assertEqual(M.upsilon_printed(90, 7), 1)
        self.assertEqual(M.upsilon_printed(90, 12), 2)
        self.assertEqual(M.upsilon_printed(150, 7), 0)
        self.assertEqual(M.upsilon_printed(150, 9), 1)
        self.assertEqual(M.upsilon_printed(150, 12), 4)

    def test_chi(self):
        self.assertEqual([M.chi_printed(j) for j in (1, 2, 3)], [3, 9, 63])
        self.assertEqual([M.chi_examples(j) for j in (1, 2, 3, 4)], [3, 5, 11, 21])
        self.assertEqual(M.runs_of_ones(0b1101110), [2, 3])


class Decision(unittest.TestCase):
    def test_decide(self):
        cls = {1: {"class": "uniform"}, 2: {"class": "self-similar", "target": "log2 3"}}
        cond, neither, _ = M.decide(cls)
        self.assertFalse(all(cond.values()))                # log2(1+sqrt 5) never occurs
        cls[3] = {"class": "self-similar", "target": "log2(1+sqrt 5)"}
        cond, neither, _ = M.decide(cls)
        self.assertTrue(all(cond.values()))
        cls[4] = {"class": "neither"}
        cond, neither, _ = M.decide(cls)
        self.assertFalse(all(cond.values()))
        self.assertEqual(neither, [4])


class Source(unittest.TestCase):
    def test_refusal(self):
        with self.assertRaises(M.Refused):
            M.run("xyz")

    def test_constants(self):
        self.assertLessEqual(len(M.TEST), 600)
        self.assertEqual(len(set(M.OUTPUTS)), len(M.OUTPUTS))
        self.assertLessEqual(len(M.OUTPUTS), 64)
        self.assertEqual(len(M.PI_PRINTED), 28)
        self.assertEqual(len(set(M.LEGAL_PRINTED)), 32)


if __name__ == "__main__":
    unittest.main()
