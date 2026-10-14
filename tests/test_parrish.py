"""Single-turn debate (debate/parrish.py): the reader on files built here (header, modes, catch trials, unanswered
judgements, refusals); accuracy per question and the paired comparison; the sign-flip permutation test against exact
enumeration; timestamps; the verdict end to end on synthetic judgements with and without an argument effect. The
paper's data are not read here.

Run with: python3 -m unittest discover -s tests -p test_parrish.py
"""

import csv
import hashlib
import importlib.util
import io
import os
import random
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("debate_parrish", os.path.join(HERE, "..", "debate", "parrish.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "ab" * 32
README = ("`mode` - The experimental condition the item was shown in, either `p` (passage-only), `ps` "
          "(passage+snippet), or `psa` (passage+snippet+argument)\n `question_id` values that start with `ct_` "
          "indicate catch trials\n")


def row(q, mode, worker, choice, corr="1", start="2021-08-01 10:00:00", end="2021-08-01 10:01:00"):
    r = {k: "" for k in M.HEADER}
    r.update({"passage_id": "P1", "question_id": q, "mode": mode, "choice_number": choice, "corr": corr,
              "anonid": worker, "timer_start_timestamp": start, "hit_end_timestamp": end, "round": "1",
              "ans1_arg": "an argument, with a comma\nand a newline"})
    return r


def table(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(M.HEADER))
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def synthetic(q=60, rates=None, seed=5):
    """q questions, three distinct workers per question and condition, correct with the given rates."""
    rates = rates or {"p": 0.55, "ps": 0.75, "psa": 0.73}
    rnd = random.Random(seed)
    rows, w = [], 0
    for i in range(q):
        for m in M.MODES:
            for _ in range(3):
                w += 1
                corr = rnd.choice("12")
                right = rnd.random() < rates[m]
                choice = corr if right else ("2" if corr == "1" else "1")
                rows.append(row(f"q{i}", m, f"w{w}", choice, corr))
    rows.append(row("ct_1", "p", "w1", "1"))
    return rows


class Reading(unittest.TestCase):
    def test_parse(self):
        rows = [row("q1", "p", "a", "1"), row("q1", "ps", "b", "2"), row("ct_9", "psa", "c", "1"),
                row("q2", "psa", "d", "")]
        got, catch, unanswered = M.parse(table(rows))
        self.assertEqual((len(got), catch, unanswered), (3, 1, 1))
        self.assertEqual([g["correct"] for g in got], [1, 0, 0])

    def test_refusals(self):
        with self.assertRaises(M.Refused):
            M.parse("a,b,c\n1,2,3\n")
        with self.assertRaises(M.Refused):
            M.parse(table([row("q1", "pa", "a", "1")]))
        with self.assertRaises(M.Refused):
            M.parse(table([row("q1", "p", "a", "1", corr="3")]))
        with self.assertRaises(M.Refused):
            M.parse(table([]))
        M.check_readme(README)
        with self.assertRaises(M.Refused):
            M.check_readme("nothing here")

    def test_hash_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, M.INPUTS["readme"][0]), "wb") as fh:
                fh.write(README.encode())
            with self.assertRaises(M.Refused):
                M.read_bytes(d, "readme")


class Statistics(unittest.TestCase):
    def test_question_key(self):
        a, b = row("q1", "p", "a", "1"), row("q1", "ps", "b", "1")
        b["passage_id"] = "P2"                               # same question id, another passage: another question
        acc = M.per_question(M.parse(table([a, b]))[0])
        self.assertEqual(M.compare(acc, "ps", "p", SEED)["questions"], 0)

    def test_compare(self):
        rows = [row("q1", "p", "a", "2"), row("q1", "p", "b", "2"), row("q1", "ps", "c", "1"), row("q1", "ps", "d", "1"),
                row("q2", "p", "e", "1"), row("q2", "ps", "f", "1"), row("q3", "ps", "g", "1")]
        acc = M.per_question(M.parse(table(rows))[0])
        c = M.compare(acc, "ps", "p", SEED)
        self.assertEqual(c["questions"], 2)                  # q3 is judged in one condition only
        self.assertAlmostEqual(c["mean"], 0.5)

    def test_sign_flip(self):
        self.assertEqual(M.exact_sign_flip_p([1.0, 1.0, 1.0]), 0.25)
        self.assertEqual(M.sign_flip_p([0.0, 0.0], SEED, "t"), 1.0)
        self.assertEqual(M.sign_flip_p([], SEED, "t"), 1.0)
        p1 = M.sign_flip_p([1 / 3] * 40 + [-1 / 3] * 5, SEED, "t", resamples=2000)
        self.assertLess(p1, 0.001)
        self.assertEqual(p1, M.sign_flip_p([1 / 3] * 40 + [-1 / 3] * 5, SEED, "t", resamples=2000))
        mixed = [0.5, -0.25, 0.75, 0.25, -0.5, 0.25, 1.0, 0.0, -0.25, 0.5]
        self.assertAlmostEqual(M.sign_flip_p(mixed, SEED, "u", resamples=20000), M.exact_sign_flip_p(mixed), delta=0.01)
        self.assertTrue(all(M.controls_known(SEED).values()))

    def test_bits(self):
        st = M.Stream(SEED, "b")
        for k in (1, 7, 256, 300, 1000):
            self.assertLess(st.bits(k), 2 ** k)
        self.assertEqual(M.Stream(SEED, "b").bits(64), M.Stream(SEED, "b").bits(64))

    def test_when(self):
        self.assertEqual(M.when("1628000000"), 1628000000.0)
        self.assertEqual(M.when("1628000000000"), 1628000000.0)
        self.assertEqual(M.when("2021-08-03T14:13:20Z"), 1628000000.0)
        self.assertEqual(M.when("2021-08-03 14:13:20"), 1628000000.0)
        self.assertIsNone(M.when(""))
        self.assertIsNone(M.when("yesterday"))

    def test_agreement(self):
        acc = {"p": {"a": [1, 1, 1], "b": [1, 0, 0], "c": [1, 1]}, "ps": {"a": [1, 1, 0]}, "psa": {}}
        ag = M.agreement(acc)
        self.assertEqual(ag["p"]["questions_with_3"], 2)
        self.assertAlmostEqual(ag["p"]["unanimous"], 0.5)
        self.assertAlmostEqual(ag["p"]["majority"], 0.5)
        self.assertAlmostEqual(ag["ps"]["majority"], 1.0)


class Verdict(unittest.TestCase):
    def run_on(self, rows):
        data, readme = table(rows).encode(), README.encode()
        saved = M.INPUTS
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "inputs"))
            for key, raw in (("data", data), ("readme", readme)):
                with open(os.path.join(d, "inputs", saved[key][0]), "wb") as fh:
                    fh.write(raw)
            M.INPUTS = {k: (saved[k][0], hashlib.sha256(raw).hexdigest(), len(raw))
                        for k, raw in (("data", data), ("readme", readme))}
            try:
                out, _ = M.run(SEED, inputs=os.path.join(d, "inputs"), results=os.path.join(d, "results"))
            finally:
                M.INPUTS = saved
        return out

    def test_holds_without_argument_effect(self):
        out = self.run_on(synthetic(q=150))
        self.assertEqual(out["test_passed"], 1)
        self.assertEqual(list(out), list(M.OUTPUTS))
        for v in out.values():
            if isinstance(v, str):
                self.assertLessEqual(len(v), M.LIMIT)

    def test_fails_with_argument_effect(self):
        out = self.run_on(synthetic(q=150, rates={"p": 0.55, "ps": 0.65, "psa": 0.92}))
        self.assertEqual(out["test_passed"], 0)
        self.assertEqual(out["conditions_met"], 1)

    def test_not_utf8(self):
        rows = synthetic(q=150)
        rows[0]["ans1_arg"] = "caf\u00e9"
        data = table(rows).encode("utf-8").replace("caf\u00e9".encode("utf-8"), b"caf\xe9")
        with self.assertRaises(UnicodeDecodeError):
            data.decode("utf-8")
        saved = M.INPUTS
        readme = README.encode()
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "inputs"))
            for key, raw in (("data", data), ("readme", readme)):
                with open(os.path.join(d, "inputs", saved[key][0]), "wb") as fh:
                    fh.write(raw)
            M.INPUTS = {k: (saved[k][0], hashlib.sha256(raw).hexdigest(), len(raw))
                        for k, raw in (("data", data), ("readme", readme))}
            try:
                out, detail = M.run(SEED, inputs=os.path.join(d, "inputs"), results=os.path.join(d, "results"))
            finally:
                M.INPUTS = saved
        self.assertEqual(detail["replaced"], 1)
        self.assertEqual(out["test_passed"], 1)

    def test_outputs_named(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


if __name__ == "__main__":
    unittest.main()
