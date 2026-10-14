"""Khan et al.'s human judges (debate/khan.py): the readme's sentences and their refusal; the judgement times; each
refusal of a row; Fisher's exact test one-sided and two-sided against R's values; the paper's balanced consultancy
accuracy; the known-answer controls; the seed refused; and, with the repository's files at inputs/ (or KHAN_INPUTS),
the table's structure (the counts of Experiments 8, 8_v0 and 9 and the judges), which computes no accuracy.

Run with: python3 -m unittest discover -s tests -p test_khan.py
"""

import datetime
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("debate_khan", os.path.join(HERE, "..", "debate", "khan.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
INPUTS = os.environ.get("KHAN_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = all(os.path.isfile(os.path.join(INPUTS, name)) for name, _ in M.INPUTS.values())


def row(**kw):
    r = {"debate_method": "debate", "consultant_type": "", "interactive_judge": "False", "correct": "True",
         "judge_id": "4", "confidence": "80", "judgement_time": "2023-12-20 17:22:13.779827+00:00"}
    r.update(kw)
    return r


class Readme(unittest.TestCase):
    def test_sentences(self):
        M.check_readme("\n".join("- " + s.replace(". ", ".\n  ") for s in M.READ))     # line breaks do not matter
        with self.assertRaises(M.Refused):
            M.check_readme("\n".join(M.READ[:-1]))


class Rows(unittest.TestCase):
    def test_reads(self):
        j = M.judgement(row(), 2)
        self.assertEqual((j["method"], j["interactive"], j["correct"], j["judge"]), ("debate", False, True, 4))
        self.assertEqual(j["date"], datetime.date(2023, 12, 20))
        self.assertEqual(M.judgement(row(debate_method="consultancy", consultant_type="incorrect"), 2)["consultant"],
                         "incorrect")
        self.assertEqual(M.judged_on("2024-01-24T23:59:59Z"), datetime.date(2024, 1, 24))

    def test_refusals(self):
        for bad in (row(debate_method="debates"), row(debate_method="consultancy"), row(consultant_type="correct"),
                    row(interactive_judge="1"), row(correct="yes"), row(judge_id="J4"), row(confidence="4"),
                    row(confidence="high"), row(judgement_time="yesterday")):
            with self.subTest(row=bad), self.assertRaises(M.Refused):
                M.judgement(bad, 2)


class Statistics(unittest.TestCase):
    def test_fisher_against_r(self):
        # R: fisher.test(matrix(c(3,1,1,3),2), alternative="greater")$p.value = 0.2428571; two-sided 0.4857143
        self.assertAlmostEqual(M.fisher_one_sided(3, 4, 1, 4), 0.2428571, places=7)
        self.assertAlmostEqual(M.fisher_two_sided(3, 4, 1, 4), 0.4857143, places=7)
        # 9 of 10 against 3 of 10: P(X >= 9) = (C(10,9) C(10,3) + C(10,10) C(10,2)) / C(20,12) = 1245 / 125970
        self.assertAlmostEqual(M.fisher_one_sided(9, 10, 3, 10), 1245 / 125970, places=15)

    def test_balanced(self):
        js = ([{"consultant": "correct", "correct": True}] * 3 + [{"consultant": "correct", "correct": False}]
              + [{"consultant": "incorrect", "correct": False}] * 2)
        acc, cor, inc, nc, ni = M.balanced(js)
        self.assertAlmostEqual(acc, (0.75 + 0.0) / 2)
        self.assertEqual((nc, ni), (4, 2))


class Controls(unittest.TestCase):
    def test_known_answers(self):
        self.assertTrue(all(M.controls_known().values()))


class Seed(unittest.TestCase):
    def test_refuses_a_bad_seed(self):
        with self.assertRaises(M.Refused):
            M.run("xyz", inputs=os.path.join(HERE, "_never"), results=os.path.join(HERE, "_never"))


@unittest.skipUnless(HAVE, "the repository's files are not at inputs/ (or KHAN_INPUTS)")
class RepositoryFiles(unittest.TestCase):
    def test_structure(self):
        raw = {k: M.read_bytes(os.path.join(INPUTS, n), s) for k, (n, s) in M.INPUTS.items()}
        M.check_readme(raw["readme"].decode("utf-8"))
        table, total, experiments = M.read_table(raw["zip"])
        self.assertEqual(total, 6471)
        self.assertEqual([len(table[e]) for e in (M.TEST, M.TEST_V0, M.NAIVE)], [953, 36, 504])
        self.assertEqual(len({j["judge"] for j in table[M.TEST]}), 21)
        self.assertEqual(sum(1 for j in table[M.NAIVE] if j["date"] > M.CUTOFF), 24)


if __name__ == "__main__":
    unittest.main()
