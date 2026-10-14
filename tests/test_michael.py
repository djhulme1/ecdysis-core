"""Michael et al.'s debate and consultancy (debate/michael.py): the reader on rooms written here (included, excluded,
incomplete, inconsistent); judge accuracy and ties; the z-test, the exact binomial and Fisher tests against values
worked by hand; calibration error; the bootstrap's determinism; the verdict at and beside each condition; the seed
refused. The released dataset is not read here.

Run with: python3 -m unittest discover -s tests -p test_michael.py
"""

import importlib.util
import json
import math
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("debate_michael", os.path.join(HERE, "..", "debate", "michael.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


def room(name, human, debate, final, correct, included=True, complete=True, roles=None, agree=True):
    r = {"name": name, "setting": {"isHuman": human, "isDebate": debate}, "includedInPaper": included,
         "roleAssignments": roles or ({"Debater A": "x", "Debater B": "y", "Judge": "j"} if debate
                                      else {"Debater A": "x", "Judge": "j"})}
    if complete:
        r["status"] = {"Complete": {"result": {"correctAnswerIndex": correct if agree else 1 - correct,
                                               "judgingInfo": {"correctAnswerIndex": correct, "finalJudgement": final,
                                                               "numContinues": 2, "judgeReward": -1.0}}}}
    else:
        r["status"] = {"InProgress": {}}
    return r


def blob(rooms):
    return ("\n".join(json.dumps(r) for r in rooms) + "\n").encode("utf-8")


class Reading(unittest.TestCase):
    def test_included_only(self):
        rows, inc = M.parse(blob([room("a", True, True, [0.9, 0.1], 0),
                                  room("b", True, True, [0.9, 0.1], 0, included=False, complete=False)]))
        self.assertEqual(len(rows), 2)
        self.assertEqual([r["name"] for r in inc], ["a"])
        self.assertEqual(inc[0]["setting"], "Human Debate")
        self.assertEqual(inc[0]["p_correct"], 0.9)

    def test_refusals(self):
        for bad in (room("c", True, True, [0.9, 0.1], 0, complete=False),
                    room("d", True, True, [0.9, 0.2], 0),
                    room("e", True, True, [0.9, 0.1], 0, agree=False),
                    room("f", True, True, [0.9], 0)):
            with self.assertRaises(M.Refused):
                M.parse(blob([bad]))

    def test_consultant_answer(self):
        _, inc = M.parse(blob([room("g", False, False, [0.2, 0.8], 1, roles={"Debater B": "z", "Judge": "j"}),
                               room("h", False, False, [0.2, 0.8], 1)]))
        self.assertEqual([r["consultant_answer"] for r in inc], [1, 0])
        self.assertEqual([r["setting"] for r in inc], ["AI Consultancy", "AI Consultancy"])

    def test_hash_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, M.INPUT[0]), "wb") as fh:
                fh.write(b"{}\n")
            with self.assertRaises(M.Refused):
                M.read_input(d)


class Statistics(unittest.TestCase):
    def test_right_and_ties(self):
        self.assertTrue(M.right({"p_correct": 0.51}))
        self.assertFalse(M.right({"p_correct": 0.5}))
        self.assertEqual(M.round_pct(0.835), 84)
        self.assertEqual(M.round_pct(0.8349), 83)
        self.assertEqual(M.round_pct(0.7396), 74)

    def test_z_test_by_hand(self):
        # 45/100 against 30/100: pooled 0.375, se = sqrt(0.375 * 0.625 * 0.02), z = 0.15 / se
        z, p = M.z_test(45, 100, 30, 100)
        self.assertAlmostEqual(z, 0.15 / math.sqrt(0.375 * 0.625 * 0.02))
        self.assertAlmostEqual(p, math.erfc(z / math.sqrt(2)))
        self.assertAlmostEqual(M.normal_tail2(1.959963984540054), 0.05, places=12)

    def test_tail_integral(self):
        for z in (0.0, 1.0, 2.5):
            self.assertAlmostEqual(M.tail_integral(z, 20000), M.normal_tail2(z), places=9)

    def test_binomial_and_fisher(self):
        self.assertAlmostEqual(M.binom_upper(9, 10), 11 / 1024)
        self.assertAlmostEqual(M.binom_upper(0, 7), 1.0)
        self.assertAlmostEqual(M.fisher(3, 1, 1, 3, "greater"), 17 / 70)
        self.assertAlmostEqual(M.fisher(3, 1, 1, 3), 34 / 70)          # the two tails, symmetric
        self.assertAlmostEqual(M.fisher(2, 2, 2, 2), 1.0)

    def test_ece(self):
        rows = [{"final": [0.9, 0.1], "correct": 0}, {"final": [0.9, 0.1], "correct": 1}]
        self.assertAlmostEqual(M.ece(rows), abs(0.5 - 0.9))
        rows = [{"final": [0.75, 0.25], "correct": 0}] * 3 + [{"final": [0.75, 0.25], "correct": 1}]
        self.assertAlmostEqual(M.ece(rows), 0.0)

    def test_bootstrap_deterministic(self):
        a, b = [1, 1, 0, 1], [0, 1, 0, 0]
        self.assertEqual(M.bootstrap(a, b, "ab" * 32), M.bootstrap(a, b, "ab" * 32))
        lo, hi = M.bootstrap(a, b, "cd" * 32)
        self.assertLessEqual(lo, hi)


class Verdict(unittest.TestCase):
    def test_conditions(self):
        c = M.conditions(154, 130, 96, 71, 0.043)
        self.assertEqual(len(c), 4)
        self.assertTrue(all(c.values()))
        self.assertEqual(sum(M.conditions(155, 130, 96, 71, 0.043).values()), 3)
        self.assertEqual(sum(M.conditions(154, 127, 96, 71, 0.043).values()), 3)      # 82.5%
        self.assertEqual(sum(M.conditions(154, 130, 96, 70, 0.043).values()), 3)      # 72.9%
        self.assertEqual(sum(M.conditions(154, 130, 96, 71, 0.05).values()), 3)

    def test_outputs_named(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


if __name__ == "__main__":
    unittest.main()
