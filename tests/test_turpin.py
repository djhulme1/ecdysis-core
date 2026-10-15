"""Turpin et al. (cot/turpin.py): the sample reader on files written here, the counts on examples worked by hand, and
the conditions on a made-up set of 52 files whose drops are known. No sample file of the authors' is read.

Run with: python3 -m unittest discover -s tests -p test_turpin.py
"""

import importlib.util
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("cot_turpin", os.path.join(HERE, "..", "cot", "turpin.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "ab" * 32


def text(task, model, setting, examples, **over):
    """A sample file: examples as (y_true, suggested, cot_biased, prior_biased, cot_unbiased, prior_unbiased)."""
    def ctx(i_cot, i_prior):
        return {"y_true": [e[0] for e in examples], "random_ans_idx": [e[1] for e in examples],
                "y_pred": [e[i_cot] for e in examples], "y_pred_prior": [e[i_prior] for e in examples],
                "gen": ["..."] * len(examples)}
    d = {"config": {"task": M.TASKS[task], "model": M.MODELS[model], "few_shot": M.SETTINGS[setting],
                    "bias_type": "suggested_answer", "time": "x"},
         "outputs": [ctx(2, 3), ctx(4, 5)]}
    d.update(over)
    return json.dumps(d)


HAND = [(0, 1, 1, 0, 0, 0),      # contradicting: biased CoT wrong, unbiased right
        (1, 1, 1, 1, 1, 0),      # consistent: both right
        (0, 1, -1, 0, 0, 0),     # failed: biased CoT unparsed
        (2, 0, 2, 2, 2, -1),     # contradicting: both right; unbiased No-CoT unparsed (kept, wrong)
        (1, 0, 0, 0, 1, 5)]      # contradicting: biased CoT follows the suggestion; unbiased No-CoT names no choice


def made_up(k_biased):
    """52 files, each with 25 contradicting examples (unbiased CoT always right, biased right on k of them), 3
    consistent ones and one failed; k per (model, setting)."""
    files = []
    for t in M.TASKS:
        for m in M.MODELS:
            for s in M.SETTINGS:
                k = k_biased[(m, s)]
                ex = [(0, 1, 0 if i < k else 1, 0, 0, 0) for i in range(25)]
                ex += [(1, 1, 1, 1, 1, 1)] * 3 + [(0, 1, 0, 0, -1, 0)]
                files.append(M.sample(f"sa_{t}_{m}_{s}.json", text(t, m, s, ex)))
    return files


class Reading(unittest.TestCase):
    def test_sample(self):
        f = M.sample("sa_snarks_gpt35_zs.json", text("snarks", "gpt35", "zs", HAND))
        self.assertEqual((f["task"], f["model"], f["setting"]), ("snarks", "gpt35", "zs"))
        self.assertEqual(f["examples"][0], HAND[0])

    def test_refusals(self):
        good = text("snarks", "gpt35", "zs", HAND)
        with self.assertRaises(M.Refused):
            M.sample("sa_snarks_gpt35_fs.json", good)                       # name says few-shot
        with self.assertRaises(M.Refused):
            M.sample("sa_snark_gpt35_zs.json", good)                        # no such task
        with self.assertRaises(M.Refused):
            M.sample("snarks.json", good)
        d = json.loads(good)
        d["outputs"][1]["y_true"][0] = 2
        with self.assertRaises(M.Refused):
            M.sample("sa_snarks_gpt35_zs.json", json.dumps(d))              # contexts disagree
        d = json.loads(good)
        d["outputs"][0]["y_pred"][0] = True
        with self.assertRaises(M.Refused):
            M.sample("sa_snarks_gpt35_zs.json", json.dumps(d))              # a bool is not a choice
        d = json.loads(good)
        d["outputs"][0]["y_pred_prior"][0] = -2
        with self.assertRaises(M.Refused):
            M.sample("sa_snarks_gpt35_zs.json", json.dumps(d))
        d = json.loads(good)
        del d["outputs"][1]["random_ans_idx"]
        with self.assertRaises(M.Refused):
            M.sample("sa_snarks_gpt35_zs.json", json.dumps(d))
        with self.assertRaises(M.Refused):
            M.sample("sa_snarks_gpt35_zs.json", text("snarks", "gpt35", "zs", HAND, outputs=[]))


class Counting(unittest.TestCase):
    def test_hand(self):
        files = [M.sample("sa_snarks_gpt35_zs.json", text("snarks", "gpt35", "zs", HAND))]
        per = M.counts(files, "gpt35", "zs")
        c = per["snarks"]
        self.assertEqual((c["n"], c["failed"], c["size"]), (4, 1, 5))
        self.assertEqual((c["contradicting"]["n"], c["consistent"]["n"]), (3, 1))
        acc = M.accuracies(per, "contradicting")
        self.assertAlmostEqual(acc[0], 100 / 3)          # No-CoT unbiased: right, then -1 and 5, both wrong
        self.assertAlmostEqual(acc[2], 100.0)            # CoT unbiased: 3 of 3
        self.assertAlmostEqual(acc[3], 100 / 3)          # CoT biased: 1 of 3
        self.assertAlmostEqual(M.drop(per), 200 / 3)
        swapped = M.counts(files, "gpt35", "zs", swap=lambda t, j: True)
        self.assertAlmostEqual(M.drop(swapped), -200 / 3)

    def test_half_width(self):
        files = [M.sample("sa_snarks_gpt35_zs.json", text("snarks", "gpt35", "zs", HAND))]
        per = M.counts(files, "gpt35", "zs")
        d = [1, 0, 1]
        mean = 2 / 3
        var = sum((x - mean) ** 2 for x in d) / 2
        self.assertAlmostEqual(M.half_width(per), 100 * 1.96 * (var / 3) ** 0.5)

    def test_printed(self):
        self.assertTrue(M.matches_printed(59.65, 59.6))
        self.assertTrue(M.matches_printed(59.6, 59.6))
        self.assertFalse(M.matches_printed(59.66, 59.6))


class Assessing(unittest.TestCase):
    K = {("gpt35", "zs"): 16, ("gpt35", "fs"): 19, ("claude1", "zs"): 17, ("claude1", "fs"): 20}

    def test_passing(self):
        out, detail = M.assess(made_up(self.K), SEED)
        self.assertEqual((out["conditions_met"], out["conditions_total"], out["test_passed"]), (5, 5, 1))
        self.assertAlmostEqual(out["largest_drop"], 36.0)
        self.assertEqual(out["drops"], "drops: GPT-3.5 zs 36.0, GPT-3.5 fs 24.0, Claude 1.0 zs 32.0, Claude 1.0 fs 20.0 "
                                       "(printed 36.3, 24.1, 30.6, 21.5)")
        self.assertEqual((out["controls_passed"], out["controls_total"]), (3, 3))
        self.assertTrue(out["failed"].startswith("left out: GPT-3.5 zs 13, GPT-3.5 fs 13, Claude 1.0 zs 13"))
        self.assertTrue(out["per_task"].startswith("tasks with a drop: GPT-3.5 zs 13,"))
        for v in out.values():
            self.assertLessEqual(len(str(v)), M.LIMIT)

    def test_failing(self):
        k = dict(self.K)
        k[("gpt35", "zs")] = 15                          # a 40-point drop
        out, _ = M.assess(made_up(k), SEED)
        self.assertEqual((out["conditions_met"], out["test_passed"]), (4, 0))
        k = dict(self.K)
        k[("claude1", "fs")] = 25                        # no drop at all
        out, _ = M.assess(made_up(k), SEED)
        self.assertEqual((out["conditions_met"], out["test_passed"]), (4, 0))


class Machinery(unittest.TestCase):
    def test_inputs_and_outputs(self):
        self.assertEqual(len(M.INPUTS), 52)
        self.assertTrue(all(M.NAME.fullmatch(n) for n in M.INPUTS))
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 64)
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


if __name__ == "__main__":
    unittest.main()
