"""Tests for tms/check.py: each shows a check failing on broken input. Run in the pytorch image, from the lab's root,
with the notebook at inputs/toy_models.ipynb: python3 -m unittest -v tms.test_check"""

import copy
import json
import math
import os
import random
import tempfile
import unittest

import torch

from tms import check

INPUTS = os.environ.get("TMS_INPUTS", "inputs")
HAVE_NOTEBOOK = os.path.exists(os.path.join(INPUTS, check.NOTEBOOK[0]))
SEED = "ab" * 32


@unittest.skipUnless(HAVE_NOTEBOOK, "the notebook is not at inputs/")
class TheNotebook(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nb = check.read_notebook(INPUTS)

    def test_every_value_followed_is_in_the_notebook(self):
        self.assertEqual(check.spec_problems(self.nb), [])

    def test_a_changed_value_is_refused(self):
        nb = copy.deepcopy(self.nb)
        src = "".join(nb["cells"][16]["source"]).replace("n_hidden = 20,", "n_hidden = 30,")
        nb["cells"][16]["source"] = [src]
        self.assertTrue(any("n_hidden = 20" in p for p in check.spec_problems(nb)))
        nb = copy.deepcopy(self.nb)
        nb["cells"][4]["source"] = ["".join(nb["cells"][4]["source"]).replace("lr=1e-3,", "lr=1e-2,")]
        self.assertTrue(any("lr=1e-3" in p for p in check.spec_problems(nb)))

    def test_another_file_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(INPUTS, check.NOTEBOOK[0]), "rb") as f:
                raw = f.read()
            with open(os.path.join(d, check.NOTEBOOK[0]), "wb") as f:
                f.write(raw[:-1] + b" ")
            with self.assertRaises(ValueError):
                check.read_notebook(d)

    def test_the_authors_run_fails_the_registered_rule_and_passes_the_corrected_one(self):
        xs, dstar, dims = check.authors_run(self.nb)
        s = check.statistics(dstar, dims)
        self.assertEqual(s["levels_half"], 4)
        self.assertEqual((s["pool"], s["named"]), (1155, 305))
        self.assertAlmostEqual(s["share"], 305 / 1155)
        self.assertFalse(s["passes_registered"])
        self.assertEqual(s["lines_found"], ["1/2", "2/5"])
        self.assertEqual((s["lines"]["2/5"]["count"], s["lines"]["2/5"]["lower"], s["lines"]["2/5"]["upper"]), (24, 8, 0))
        self.assertEqual((s["lines"]["3/8"]["count"], s["lines"]["3/8"]["lower"]), (25, 14), "25 is not twice 14: no line at 3/8")
        self.assertTrue(s["passes_corrected"])

    def test_the_notebooks_own_code_and_ours_agree_bit_for_bit(self):
        c = check.control_authors(self.nb, SEED, 2)
        self.assertTrue(c["passed"], c)

    def test_a_misread_hyperparameter_breaks_the_agreement(self):
        old = check.LR
        try:
            check.LR = 2e-3
            self.assertFalse(check.control_authors(self.nb, SEED, 2)["passed"])
        finally:
            check.LR = old


class TheMeasures(unittest.TestCase):
    def test_the_polytopes_have_the_papers_fractions(self):
        c = check.control_polytopes()
        self.assertTrue(c["passed"], c)
        self.assertEqual(c["features"], 1 + 2 + 3 + 4 + 5 + 8)

    def test_a_square_antiprism_that_is_not_a_tight_frame_is_not_exactly_three_eighths(self):
        z, r = 0.8, 0.6  # too tall: unit vectors, but the frame is not tight
        anti = [(r * math.cos(math.pi * j / 2), r * math.sin(math.pi * j / 2), z) for j in range(4)]
        anti += [(r * math.cos(math.pi * j / 2 + math.pi / 4), r * math.sin(math.pi * j / 2 + math.pi / 4), -z) for j in range(4)]
        W = torch.zeros((8, check.N_HIDDEN), dtype=torch.float64)
        W[:, :3] = torch.tensor(anti, dtype=torch.float64)
        self.assertGreater(max(abs(d - 0.375) for d in check.dimensionality(W)), 0.01)

    def test_dimensions_per_feature(self):
        W = torch.zeros((check.N_FEATURES, check.N_HIDDEN))
        W[:40] = torch.cat([torch.eye(check.N_HIDDEN), -torch.eye(check.N_HIDDEN)])  # 20 antipodal pairs
        self.assertAlmostEqual(check.dimensions_per_feature(W), 0.5)

    def test_the_seed_must_be_the_archives(self):
        for bad in ("", "AB" * 32, "ab" * 31, "zz" * 32):
            with self.assertRaises(ValueError):
                check.stream_seed(bad, "level/0")
        self.assertNotEqual(check.stream_seed(SEED, "level/0"), check.stream_seed(SEED, "level/1"))


class TheRules(unittest.TestCase):
    def level(self, values):
        return values + [0.001] * (check.N_FEATURES - len(values))

    def test_a_planted_line_is_found_and_a_smooth_spread_has_none(self):
        dstar = [1.0, 1.0] + [0.5] * 5 + [0.3] * 13
        rng = random.Random(7)
        dims = [self.level([rng.uniform(0.1, 0.3) for _ in range(30)]) for _ in range(check.N_LEVELS)]
        for k in range(2, 7):
            dims[k] = self.level([0.5 + rng.uniform(-0.003, 0.003) for _ in range(38)])
        dims[8] = self.level([0.4 + rng.uniform(-0.003, 0.003) for _ in range(15)])
        s = check.statistics(dstar, dims)
        self.assertEqual(s["lines_found"], ["1/2", "2/5"])
        self.assertTrue(s["passes_corrected"])
        smooth = [self.level([rng.random() for _ in range(150)]) for _ in range(check.N_LEVELS)]
        self.assertFalse(check.statistics(dstar, smooth)["passes_corrected"])

    def test_no_line_beside_1_2_fails_the_corrected_rule(self):
        dstar = [1.0, 1.0] + [0.5] * 5 + [0.3] * 13
        dims = [self.level([0.2] * 30) for _ in range(check.N_LEVELS)]
        for k in range(2, 7):
            dims[k] = self.level([0.5] * 38)
        s = check.statistics(dstar, dims)
        self.assertEqual(s["lines_found"], ["1/2"])
        self.assertFalse(s["passes_corrected"])

    def test_too_few_levels_at_one_half_fails_both_rules(self):
        dstar = [1.0, 1.0, 0.5, 0.5] + [0.3] * 16
        dims = [self.level([0.5] * 38 if 2 <= k < 4 else [0.4] * 20) for k in range(check.N_LEVELS)]
        s = check.statistics(dstar, dims)
        self.assertEqual(s["levels_half"], 2)
        self.assertFalse(s["passes_registered"])
        self.assertFalse(s["passes_corrected"])

    def test_the_registered_rule_needs_half_at_its_fractions(self):
        dstar = [1.0] + [0.5] * 4 + [0.3] * 15
        at = [self.level([0.5] * 20 + [0.2] * 19) for _ in range(check.N_LEVELS)]
        self.assertTrue(check.statistics(dstar, at)["passes_registered"])
        off = [self.level([0.5] * 19 + [0.2] * 20) for _ in range(check.N_LEVELS)]
        self.assertFalse(check.statistics(dstar, off)["passes_registered"])


class TheTraining(unittest.TestCase):
    def test_level_by_level_equals_joint_bit_for_bit(self):
        c = check.control_separable(SEED, 2)
        self.assertTrue(c["passed"], c)

    def test_a_level_depends_only_on_its_own_stream(self):
        a = check.train_level((SEED, 3, 3))
        b = check.train_level((SEED, 3, 3))
        c = check.train_level((SEED, 4, 3))
        self.assertEqual(a["W"], b["W"])
        self.assertNotEqual(a["W"], c["W"])

    def test_the_feature_probabilities_run_from_1_to_1_in_20(self):
        p = check.feature_probability()[:, 0]
        self.assertEqual(float(p[0]), 1.0)
        self.assertAlmostEqual(float(1 / p[-1]), 20.0, places=4)
        self.assertEqual(len(p), 20)


if __name__ == "__main__":
    unittest.main()
