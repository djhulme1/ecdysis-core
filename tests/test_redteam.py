"""Ganguli et al.'s red team scaling (redteam/check.py): the cells and averages, the verdict at and beside each
condition, and, with the release at inputs/ (or REDTEAM_INPUTS), the counts of Table 1.

Run with: python3 -m unittest tests.test_redteam
"""

import importlib.util
import os
import random
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("redteam_check", os.path.join(HERE, "..", "redteam", "check.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)
INPUTS = os.environ.get("REDTEAM_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = os.path.isfile(os.path.join(INPUTS, M.INPUT[0]))


def means(rlhf=(0.5, 1.4, 1.7), other=0.2):
    m = {("rlhf", s): v for s, v in zip(M.SIZES, rlhf)}
    for t in ("plain lm", "context distillation", "rejection sampling"):
        m[(t, "2.7B")], m[(t, "13B")], m[(t, "52B")] = 0.0, 0.1, other
    return m


class Verdict(unittest.TestCase):
    def test_at_and_beside_each_condition(self):
        self.assertTrue(all(M.conditions(means()).values()))
        self.assertFalse(M.conditions(means(rlhf=(0.5, 1.8, 1.7)))["the RLHF average rises from 2.7B to 13B and from 13B to 52B"])
        k = "each other type changes from 2.7B to 52B by less than half the RLHF rise"
        self.assertTrue(M.conditions(means(other=0.599))[k])
        self.assertFalse(M.conditions(means(other=0.6))[k])                      # half of 1.2
        self.assertFalse(M.conditions(means(other=-0.6))[k])

    def test_cells_and_bootstrap(self):
        recs = [("rlhf", "2.7B", 1.0, 0), ("rlhf", "2.7B", 3.0, 4), ("rlhf", "52B", 5.0, 1)]
        scores, ratings = M.cells(recs)
        self.assertEqual(scores[("rlhf", "2.7B")], [1.0, 3.0])
        self.assertEqual(ratings[("rlhf", "2.7B")], [0.0, 4.0])
        full = {(t, s): [1.0, 2.0, 3.0] for t in M.TYPES for s in M.SIZES}
        b = M.bootstrap(full, random.Random(1), resamples=200)
        self.assertTrue(all(lo <= 0 <= hi for lo, hi in b.values()))


@unittest.skipUnless(HAVE, "the release is not at inputs/ (or REDTEAM_INPUTS)")
class Release(unittest.TestCase):
    def test_table1(self):
        recs = M.load(INPUTS)
        scores, _ = M.cells(recs)
        self.assertEqual({k: len(v) for k, v in scores.items()}, M.TABLE1)


if __name__ == "__main__":
    unittest.main()
