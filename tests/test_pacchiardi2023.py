"""Pacchiardi et al.'s lie detector (lie/pacchiardi2023.py): the readers on files written here, the authors' split
against a pandas transcription of create_datasets_paired_questions, the AUC against sklearn on tied scores, the
logistic fit against Newton's method, and the whole assessment on made-up answers whose outcome is known. No file of
the authors' is read.

Run with: python3 -m unittest discover -s tests -p test_pacchiardi2023.py
"""

import importlib.util
import json
import os
import struct
import tempfile
import unittest

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("lie_pacchiardi2023", os.path.join(HERE, "..", "lie", "pacchiardi2023.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "ab" * 32
NO_LIE = [41, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64]
LIE = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 23, 27, 28, 29, 30]
KNOWABLE = [31, 32, 33, 34, 35, 36, 37, 38, 39, 40]


def npy(values, header=None):
    h = header or "{'descr': '<i8', 'fortran_order': False, 'shape': (%d,), }" % len(values)
    h = h + " " * ((64 - (10 + len(h) + 1) % 64) % 64) + "\n"
    return b"\x93NUMPY\x01\x00" + struct.pack("<H", len(h)) + h.encode("latin1") + struct.pack(
        f"<{len(values)}q", *values)


def probes():
    """65 questions with the appendix's 48 at the authors' indices and fillers elsewhere."""
    out = [f"Filler question {i}? Answer yes or no." for i in range(65)]
    for g, idx in (("lie", LIE), ("knowable", KNOWABLE), ("no_lie", NO_LIE)):
        for i, q in zip(idx, M.QUESTIONS[g]):
            out[i] = q
    return out


def column_file(columns):
    """A processed-question file as pandas' to_json writes one: columns of row objects keyed "0" to "n - 1"."""
    return json.dumps({c: {str(i): v for i, v in enumerate(vals)} for c, vals in columns.items()})


def answers(rng, n, lying, shift=1.5, informative=(0, 1, 2, 3, 4, 41, 52, 53, 31, 32)):
    """n made-up lists of 65 logprob differences; lies shift the informative questions down."""
    x = rng.normal(0.0, 1.0, size=(n, 65))
    if lying:
        x[:, list(informative)] -= shift
    return x.tolist()


def made_up_files(rng, shift=1.5, n=40, open_shift=None):
    files = {}
    for cls, fname, _ in M.DATASETS:
        cols = {}
        models = ("text-davinci-003",) if cls in M.NO_OPEN_MODELS else M.MODELS
        for m in models:
            s = shift if (m == "text-davinci-003" or open_shift is None) else open_shift
            lie, truth = answers(rng, n, True, s), answers(rng, n, False, s)
            lie[0] = None  # a question whose lie was not recorded
            truth[1] = None  # and one whose honest answer was not
            cols[f"{m}_logprobs_difference_lie"] = lie
            cols[f"{m}_logprobs_difference_truth"] = truth
        cols["question"] = [f"q{i}" for i in range(n)]
        files[fname] = M.read_questions(column_file(cols), fname, cls not in M.NO_OPEN_MODELS)
    return files


def made_up_scenarios(rng, shift=1.5):
    rows = []
    for i in range(M.SCENARIO_ROWS):
        lying = i % 2 == 0
        no_lie = rng.normal(0, 1, 22)
        lie = rng.normal(0, 1, 24)
        if lying:
            no_lie[:3] -= shift
            lie[:3] -= shift
        rows.append({"no_lie": no_lie.tolist(), "lie": lie.tolist(), "knowable": rng.normal(0, 1, 10).tolist()})
    cols = {"transcript": ["t"] * 54, "label": [i % 2 for i in range(54)], "prompt": ["p"] * 54,
            "question_prefix": ["Human:"] * 54, "answer_prefix": ["AI:"] * 54,
            "logprob_differences_no_lie": [r["no_lie"] for r in rows],
            "logprob_differences_lie": [r["lie"] for r in rows],
            "logprob_differences_knowable": [r["knowable"] for r in rows],
            "full_conversation_unknowable_probes": [["c"] * 56] * 54}
    return column_file(cols)


def groups():
    return {"no_lie": list(NO_LIE), "lie": list(LIE), "knowable": list(KNOWABLE)}


class Readers(unittest.TestCase):
    def test_npy(self):
        self.assertEqual(M.read_npy(npy([3, 1, 2]), "x"), [3, 1, 2])
        with self.assertRaises(M.Refused):
            M.read_npy(npy([1, 1]), "x")
        with self.assertRaises(M.Refused):
            M.read_npy(npy([1, 70]), "x")
        with self.assertRaises(M.Refused):
            M.read_npy(npy([1, 2], "{'descr': '<f8', 'fortran_order': False, 'shape': (2,), }"), "x")
        with self.assertRaises(M.Refused):
            M.read_npy(b"NOTNPY" + npy([1])[6:], "x")

    def test_questions(self):
        lie = [[0.5] * 65, None, [1.0] * 65]
        truth = [[0.1] * 65, [0.2] * 65, None]
        text = column_file({"text-davinci-003_logprobs_difference_lie": lie,
                            "text-davinci-003_logprobs_difference_truth": truth, "question": ["a", "b", "c"]})
        d = M.read_questions(text, "f.json", False)
        self.assertEqual(d["text-davinci-003"]["lie"][1], None)
        self.assertEqual(d["text-davinci-003"]["truth"][0][0], 0.1)
        with self.assertRaises(M.Refused):  # the open models are required where they ran
            M.read_questions(text, "f.json", True)
        bad = json.loads(text)
        bad["question"] = {"0": "a", "2": "c", "1": "b"}
        with self.assertRaises(M.Refused):
            M.read_questions(json.dumps(bad), "f.json", False)
        for v in ([0.5] * 64, [0.5] * 64 + ["x"], [0.5] * 64 + [True], [0.5] * 64 + [None]):
            short = json.loads(text)
            short["text-davinci-003_logprobs_difference_lie"]["0"] = v
            with self.assertRaises(M.Refused):
                M.read_questions(json.dumps(short), "f.json", False)

    def test_probes_and_groups(self):
        p = probes()
        text = "probe_type,probe\n" + "".join(f'x,"{q.replace(chr(34), chr(34) * 2)}"\n' for q in p)
        self.assertEqual(M.read_probes(text), p)
        with self.assertRaises(M.Refused):
            M.read_probes("type,probe\n" + "x,y\n" * 65)
        self.assertTrue(M.check_groups(p, groups()))
        swapped = groups()
        swapped["lie"][0], swapped["knowable"][0] = swapped["knowable"][0], swapped["lie"][0]
        self.assertFalse(M.check_groups(p, swapped))
        p2 = list(p)
        p2[41] = "Is the sky green? Answer yes or no."
        self.assertFalse(M.check_groups(p2, groups()))

    def test_scenarios(self):
        rng = np.random.default_rng(1)
        rows = M.read_scenarios(made_up_scenarios(rng))
        self.assertEqual(len(rows), 50)
        self.assertNotIn(16, [r["key"] for r in rows])
        self.assertEqual(len(rows[0]["no_lie"]), 14)
        bad = json.loads(made_up_scenarios(rng))
        bad["label"]["3"] = 0
        with self.assertRaises(M.Refused):
            M.read_scenarios(json.dumps(bad))
        bad = json.loads(made_up_scenarios(rng))
        bad["logprob_differences_no_lie"]["5"] = [0.1] * 13
        with self.assertRaises(M.Refused):
            M.read_scenarios(json.dumps(bad))

    def test_hash(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "f")
            with open(p, "wb") as fh:
                fh.write(b"abc")
            with self.assertRaises(M.Refused):
                M.read_bytes(p, "0" * 64)


class Split(unittest.TestCase):
    def test_against_pandas(self):
        """The split as create_datasets_paired_questions draws it, written out with pandas as the authors' code
        does: permute the rows, take the first int(0.7 N), stack honest answers then lies, permute each part."""
        rng = np.random.default_rng(5)
        n = 37
        pairs = [(rng.normal(size=4).tolist(), rng.normal(size=4).tolist()) for _ in range(n)]
        xtr, ytr, xte, yte, ok = M.authors_split(pairs)
        self.assertTrue(ok)
        df = pd.DataFrame({"truth": [np.array(t) for t, _ in pairs], "lie": [np.array(l) for _, l in pairs]})
        r = np.random.RandomState(42)
        idx = r.permutation(np.arange(df.shape[0]))
        df = df.iloc[idx]
        tr, te = df.iloc[:int(len(df) * 0.7)], df.iloc[int(len(df) * 0.7):]
        x_tr = np.concatenate([np.stack([tr.iloc[i, 0] for i in range(tr.shape[0])]),
                               np.stack([tr.iloc[i, 1] for i in range(tr.shape[0])])])
        x_te = np.concatenate([np.stack([te.iloc[i, 0] for i in range(te.shape[0])]),
                               np.stack([te.iloc[i, 1] for i in range(te.shape[0])])])
        y_tr = np.concatenate([np.ones(len(x_tr) // 2), np.zeros(len(x_tr) // 2)])
        y_te = np.concatenate([np.ones(len(x_te) // 2), np.zeros(len(x_te) // 2)])
        p1 = r.permutation(np.arange(len(x_tr)))
        p2 = r.permutation(np.arange(len(x_te)))
        np.testing.assert_array_equal(xtr, x_tr[p1])
        np.testing.assert_array_equal(ytr, y_tr[p1])
        np.testing.assert_array_equal(xte, x_te[p2])
        np.testing.assert_array_equal(yte, y_te[p2])
        self.assertEqual(len(xtr), 2 * 25)

    def test_legacy_stream(self):
        self.assertEqual(np.random.RandomState(42).permutation(10).tolist(), M.LEGACY_42)


class Statistics(unittest.TestCase):
    def test_rank_auc(self):
        from sklearn.metrics import roc_auc_score
        rng = np.random.default_rng(2)
        for _ in range(20):
            y = rng.integers(0, 2, 60)
            y[0], y[1] = 0, 1
            s = rng.integers(0, 5, 60).astype(float)  # many ties
            self.assertAlmostEqual(M.rank_auc(y, s), roc_auc_score(y, s), places=12)
        self.assertEqual(M.rank_auc([0, 0, 1, 1], [0.1, 0.2, 0.3, 0.4]), 1.0)
        self.assertEqual(M.rank_auc([0, 1], [0.5, 0.5]), 0.5)
        with self.assertRaises(M.Refused):
            M.rank_auc([1, 1], [0.1, 0.2])

    def test_newton_matches_sklearn(self):
        rng = np.random.default_rng(3)
        x = (rng.normal(size=(300, 8)) > 0).astype(float)
        w = rng.normal(size=8)
        y = (rng.random(300) < 1 / (1 + np.exp(-(x @ w - 1)))).astype(float)
        det = M.Detector(x, y)
        s_n, theta = M.newton_scores(x, y, x)
        coef = np.concatenate([det.model.coef_[0], det.model.intercept_])
        self.assertLess(np.max(np.abs(coef - theta)), 1e-3)
        self.assertLess(abs(M.rank_auc(y, s_n) - M.rank_auc(y, det.score(x))), 1e-3)

    def test_features(self):
        x = np.array([[0.5, -0.1, 0.0], [-2.0, 3.0, 1e-9]])
        np.testing.assert_array_equal(M.features(x, [2, 0], True), [[0.0, 1.0], [1.0, 0.0]])
        np.testing.assert_array_equal(M.features(x, [1], False), [[-0.1], [3.0]])


class Assessment(unittest.TestCase):
    def test_separable_lies_pass(self):
        rng = np.random.default_rng(7)
        files = made_up_files(rng, shift=3.0)
        out, detail = M.assess(M.assemble(files), probes(), groups(), M.read_scenarios(made_up_scenarios(rng, 3.0)),
                               SEED)
        self.assertEqual(out["controls_passed"], out["controls_total"], detail["controls"])
        self.assertEqual(out["test_passed"], 1, detail["conditions"])
        self.assertEqual(out["training_samples"], 2 * int(11 * 38 * 0.7))
        for k, v in out.items():
            if isinstance(v, str):
                self.assertLessEqual(len(v), M.LIMIT, k)

    def test_null_answers_fail(self):
        rng = np.random.default_rng(8)
        files = made_up_files(rng, shift=0.0)
        out, detail = M.assess(M.assemble(files), probes(), groups(), M.read_scenarios(made_up_scenarios(rng, 0.0)),
                               SEED)
        self.assertEqual(out["test_passed"], 0)
        self.assertEqual(out["conditions_met"], 0, detail["conditions"])
        self.assertLess(out["auc_in"], 0.75)

    def test_open_models_alone_can_fail(self):
        rng = np.random.default_rng(9)
        files = made_up_files(rng, shift=3.0, open_shift=0.0)
        out, detail = M.assess(M.assemble(files), probes(), groups(), M.read_scenarios(made_up_scenarios(rng, 3.0)),
                               SEED)
        cond = detail["conditions"]
        self.assertTrue(cond["in_distribution"] and cond["unseen_datasets"] and cond["real_life"], cond)
        self.assertFalse(cond["unseen_architectures"])
        self.assertEqual(out["test_passed"], 0)

    def test_seed_moves_only_the_seeded_parts(self):
        rng = np.random.default_rng(10)
        files = made_up_files(rng, shift=1.0, n=20)
        sc = M.read_scenarios(made_up_scenarios(rng, 1.0))
        a, _ = M.assess(M.assemble(files), probes(), groups(), sc, SEED)
        b, _ = M.assess(M.assemble(files), probes(), groups(), sc, "cd" * 32)
        for k in ("auc_in", "auc_loo_mean", "auc_alpaca", "auc_vicuna", "auc_real_life", "test_passed"):
            self.assertEqual(a[k], b[k], k)
        self.assertNotEqual(a["shuffles"], b["shuffles"])


if __name__ == "__main__":
    unittest.main()
