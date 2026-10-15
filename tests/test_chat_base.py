"""Chat models against their base models on SAD (sad/chat_base.py): the results reader, the aggregation, the MMLU
reader, the printed-table reader and the conditions, all on tables written here. No file of the SAD repository is read.

Run with: python3 -m unittest tests.test_chat_base
"""

import importlib.util
import math
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("sad_chat_base", os.path.join(HERE, "..", "sad", "chat_base.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "5c" * 32
TASKS = [(t, c) for _, t, c in M.FILES]
HEADER = "model,task,variant,score,std\n"


def table_of(scores, std=0.01, sp=None):
    """A Table over the 16 tasks: scores {file model name: score on every task}, the same std everywhere."""
    results = {}
    for task, _ in TASKS:
        text = HEADER + "".join(f"{m},{task},plain,{s},{std}\n" for m, s in scores.items())
        if sp is not None:
            text += "".join(f"{m},{task},sp,{s},{std}\n" for m, s in sp.items())
        results[task] = M.read_results(text, task)
    return M.Table(TASKS, results)


def pairs_table(base, chat):
    models = {}
    for b, c in M.PAIRS:
        models[b.replace(".", "_")] = base
        models[c.replace(".", "_")] = chat
    return table_of(models, sp=models)


LLAMA_MMLU = {"llama-2-7b": 0.45, "llama-2-7b-chat": 0.44, "llama-2-13b": 0.55, "llama-2-13b-chat": 0.55,
              "llama-2-70b": 0.70, "llama-2-70b-chat": 0.64, "gpt-4-base": 0.82, "gpt-4-0613": 0.82}
EMPTY_TABLE = "\\begin{tabular}{lc}\nModel & \\textit{Overall} \\\\\n\\bottomrule\n\\end{tabular}\n"


class Reader(unittest.TestCase):
    def test_names_cot_and_missing(self):
        text = (",model,task,variant,score,std\n0,gpt-3_5-turbo-0613,t,plain,0.5,0.1\n1,COT gpt-4,t,plain,0.9,0.1\n"
                "2,claude-2_1,t,plain,,\n3,claude-2_1,t,sp,-0.25,0.0\n")
        rows = M.read_results(text, "t")
        self.assertEqual(rows, {("gpt-3.5-turbo-0613", "plain"): (0.5, 0.1), ("claude-2.1", "plain"): (None, None),
                                ("claude-2.1", "sp"): (-0.25, 0.0)})

    def test_refusals(self):
        bad = [
            "model,task,variant,score\nm,t,plain,0.5\n",                      # no std column
            HEADER + "m,t,plain,0.5,0.1\nm,t,plain,0.6,0.1\n",                 # repeated row
            HEADER + "m,t,plain,0.5,-0.1\n",                                   # negative std
            HEADER + "m,t,plain,abc,0.1\n",                                    # not a number
            HEADER + "m,t,plain,nan,0.1\n",                                    # not finite
            HEADER + "m,t,plain,0.5,\n",                                       # a score without a std
            HEADER + ",t,plain,0.5,0.1\n",                                     # no model
        ]
        for text in bad:
            with self.assertRaises(M.Refused, msg=text):
                M.read_results(text, "t")


class Aggregation(unittest.TestCase):
    def test_synthetic_control(self):
        self.assertTrue(M.synthetic_control()["passed"])

    def test_weighted(self):
        self.assertEqual(M.weighted([(1, None, None)]), (None, None))
        mean, err = M.weighted([(0.5, 0.2, 0.1), (1.0, 0.8, 0.2), (2.0, None, None)])
        self.assertAlmostEqual(mean, (0.1 + 0.8) / 1.5)
        self.assertAlmostEqual(err, math.sqrt(0.25 * 0.01 + 0.04) / 1.5)

    def test_constant_table(self):
        # every task 0.3 with std 0.01: every score is 0.3; a category's error is 0.01 / sqrt(n_c); the SAD error is
        # 0.01 sqrt(sum over categories of 1 / n_c) / 7, the categories having 4, 1, 3, 2, 2, 2 and 2 tasks
        t = table_of({"x-1_5": 0.3})
        s, e = t.score("x-1.5", "plain")
        self.assertAlmostEqual(s, 0.3)
        self.assertAlmostEqual(e, 0.01 * math.sqrt(1 / 4 + 1 + 1 / 3 + 4 * 1 / 2) / 7)
        self.assertAlmostEqual(t.score("x-1.5", "plain", "facts")[1], 0.01 / 2)
        self.assertAlmostEqual(t.group("x-1.5", "plain", dict(M.GROUPS)["Inferences"])[1], 0.005)
        self.assertTrue(t.complete("x-1.5", "plain"))
        self.assertFalse(t.complete("x-1.5", "sp"))

    def test_categories_weigh_equally(self):
        # one task of facts (of 4) at 1.0, the rest 0: facts scores 0.25, the SAD score 0.25 / 7
        results = {}
        for task, _ in TASKS:
            s = 1.0 if task == "facts_human_defaults" else 0.0
            results[task] = M.read_results(HEADER + f"m,{task},plain,{s},0.0\n", task)
        t = M.Table(TASKS, results)
        self.assertAlmostEqual(t.score("m", "plain", "facts")[0], 0.25)
        self.assertAlmostEqual(t.score("m", "plain")[0], 0.25 / 7)


class Mmlu(unittest.TestCase):
    def test_probe(self):
        self.assertTrue(M.mmlu_control()["passed"])

    def test_never_executed(self):
        text = "raise SystemExit('executed')\nimport nothing_of_the_kind\nMMLU_SCORES = {'a': 0.5}\n"
        self.assertEqual(M.read_mmlu(text), {"a": 0.5})

    def test_match_statement_parses(self):
        text = "def f(n):\n    match n:\n        case 'x':\n            return 1\nMMLU_SCORES = {'a': 0.5}\n"
        self.assertEqual(M.read_mmlu(text), {"a": 0.5})

    def test_refusals(self):
        for text in ("X = {'a': 0.5}\n", "MMLU_SCORES = {'a': 0.5}\nMMLU_SCORES = {'b': 0.5}\n",
                     "MMLU_SCORES = {'a': 1}\n", "MMLU_SCORES = {'a': 1.5}\n", "MMLU_SCORES = dict(a=0.5)\n"):
            with self.assertRaises((M.Refused, ValueError), msg=text):
                M.read_mmlu(text)


class Tables(unittest.TestCase):
    CATS = ("\\begin{tabular}{lcc}& \\multicolumn{1}{c}{} & x \\\\\n\\cmidrule(lr){3-5}\n"
            "Model & \\textit{Overall} & facts & influence & introspection & stages & self-recognition & id-leverage "
            "& anti-imitation \\\\\n\\midrule\n"
            "x-1.5 & \\textit{\\underline{30.0}} & 30.0 & 30.0 & 30.0 & 30.0 & 30.0 & 30.0 & 30.0 \\\\\n"
            "claude-3-haiku & \\textit{\\textbf{60.0}} & 60.0 & 60.0 & 60.0 & 60.0 & 60.0 & \\phantom{0}60.0 & 60.0 "
            "\\\\\n\\midrule\nRandom Chance & \\textit{27.4} & 1 & 1 & 1 & 1 & 1 & 1 & 1 \\\\\n\\bottomrule\n")
    DEFN = ("Model & \\textit{Overall} & Self-Knowledge & Inferences & Actions \\\\\n\\midrule\n"
            "x-1.5 & \\textit{30.0 \\error{0.3}} & 30.0 \\error{0.4} & 30.0 \\error{0.5} & 30.0 \\error{0.5} \\\\\n"
            "claude-3-haiku & \\textit{\\textbf{60.0} \\error{0.3}} & 60.0 \\error{0.4} & 60.0 \\error{0.5} & "
            "\\phantom{0}60.0 \\error{0.5} \\\\\nUpper Baseline & \\textit{90.7} & 1 & 1 & 1 \\\\\n")

    def table(self):
        return table_of({"x-1_5": 0.3, "claude-3-haiku-20240307": 0.6})

    def test_read_table(self):
        header, rows = M.read_table(self.DEFN)
        self.assertEqual(header, ["Overall", "Self-Knowledge", "Inferences", "Actions"])
        self.assertEqual(rows["claude-3-haiku"][0], (60.0, 0.3))
        self.assertEqual(sorted(rows), ["claude-3-haiku", "x-1.5"])

    def test_controls_pass(self):
        self.assertTrue(M.table_control(self.table(), self.CATS, with_errors=False)["passed"])
        self.assertTrue(M.table_control(self.table(), self.DEFN, with_errors=True)["passed"])

    def test_controls_fail(self):
        t = self.table()
        self.assertFalse(M.table_control(t, self.CATS.replace("& 30.0 & 30.0 & 30.0 \\\\", "& 30.0 & 30.0 & 30.1 \\\\"),
                                         with_errors=False)["passed"])
        self.assertFalse(M.table_control(t, self.DEFN.replace("30.0 \\error{0.4}", "30.0 \\error{0.6}"),
                                         with_errors=True)["passed"])
        self.assertFalse(M.table_control(table_of({"x-1_5": 0.3}), self.CATS, with_errors=False)["passed"])
        self.assertFalse(M.table_control(t, EMPTY_TABLE, with_errors=False)["passed"])


class Conditions(unittest.TestCase):
    def test_sign_flip(self):
        self.assertEqual(M.sign_flip_p([1, 1, 1, 1, 1]), 1 / 32)
        self.assertEqual(M.sign_flip_p([2, 1]), 1 / 4)

    def test_both_hold(self):
        out, detail = M.assess(pairs_table(0.4, 0.5), LLAMA_MMLU, EMPTY_TABLE, EMPTY_TABLE, SEED)
        self.assertEqual(out["test_passed"], 1)
        self.assertEqual(out["conditions_met"], 2)
        self.assertAlmostEqual(out["sad_boost"], 10.0)
        self.assertEqual(out["pairs_chat_above"], 5)
        self.assertAlmostEqual(out["mmlu_difference"], 100 * (1.63 - 1.70) / 3, places=3)
        self.assertEqual([p["base"] for p in detail["mmlu_pairs"]], ["llama-2-7b", "llama-2-13b", "llama-2-70b"])
        self.assertEqual(out["pairs_not_above"], "pairs whose chat model is not above its base model: none")
        for k, v in out.items():
            self.assertTrue(isinstance(v, (int, float, str)) and not isinstance(v, bool), k)
            self.assertLessEqual(len(v) if isinstance(v, str) else 0, 200, k)
        self.assertEqual(out["controls_passed"], 2)  # the two printed tables written here are empty

    def test_sad_fails(self):
        out, _ = M.assess(pairs_table(0.5, 0.5), LLAMA_MMLU, EMPTY_TABLE, EMPTY_TABLE, SEED)
        self.assertEqual(out["test_passed"], 0)
        self.assertEqual(out["conditions_met"], 1)
        self.assertEqual(out["pairs_chat_above"], 0)
        self.assertEqual(out["pairs_not_above"].count("/"), 5)

    def test_mmlu_fails(self):
        mmlu = dict(LLAMA_MMLU, **{"llama-2-13b-chat": 0.70})
        out, _ = M.assess(pairs_table(0.4, 0.5), mmlu, EMPTY_TABLE, EMPTY_TABLE, SEED)
        self.assertEqual(out["test_passed"], 0)
        self.assertEqual(out["mmlu_pairs_chat_above"], 1)

    def test_estimate_left_out(self):
        # gpt-4-base's copied score is not counted, whatever it is
        mmlu = dict(LLAMA_MMLU, **{"gpt-4-base": 0.10})
        out, _ = M.assess(pairs_table(0.4, 0.5), mmlu, EMPTY_TABLE, EMPTY_TABLE, SEED)
        self.assertEqual(out["test_passed"], 1)
        self.assertNotEqual(out["mmlu_difference_with_estimate"], out["mmlu_difference"])

    def test_refusals(self):
        with self.assertRaises(M.Refused):
            M.assess(pairs_table(0.4, 0.5), {k: v for k, v in LLAMA_MMLU.items() if k != "llama-2-13b"},
                     EMPTY_TABLE, EMPTY_TABLE, SEED)
        t = pairs_table(0.4, 0.5)
        t.results["influence"] = {k: v for k, v in t.results["influence"].items() if k[0] != "gpt-4-0613"}
        with self.assertRaises(M.Refused):
            M.assess(t, LLAMA_MMLU, EMPTY_TABLE, EMPTY_TABLE, SEED)


class Run(unittest.TestCase):
    def test_seed(self):
        with self.assertRaises(M.Refused):
            M.run("nothex", inputs=os.path.join(HERE, "nonexistent"), results=os.path.join(HERE, "nonexistent"))

    def test_hash(self):
        work = tempfile.mkdtemp()
        try:
            with open(os.path.join(work, "facts_human_defaults.csv"), "w") as fh:
                fh.write(HEADER)
            with self.assertRaises(M.Refused):
                M.run(SEED, inputs=work, results=os.path.join(work, "results"))
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def test_test_length(self):
        self.assertLessEqual(len(M.TEST), 600)

    def test_inputs(self):
        self.assertEqual(set(M.INPUTS), {f for f, _, _ in M.FILES} | {"correlations.py", "categories.tex",
                                                                     "definition.tex"})
        self.assertEqual(len(M.FILES), 16)
        self.assertEqual(sorted({c for _, _, c in M.FILES}), sorted(M.CATEGORIES))


if __name__ == "__main__":
    unittest.main()
