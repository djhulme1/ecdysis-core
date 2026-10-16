"""Berglund et al. 2023 (reversal/berglund2023.py): the two CSV readers against each other on awkward files, the
pairs reader's refusals, the rounding at its edges, the counts, the consistency checks on planted faults and the whole
assessment on synthetic files with made-up names. The authors' files are never read here.

Run with: python3 -m unittest tests.test_berglund2023 (in the pinned python image)
"""

import hashlib
import importlib.util
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("reversal_berglund2023",
                                               os.path.join(HERE, "..", "reversal", "berglund2023.py"))
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)

HEADER = "child,parent,parent_type,child_prediction,can_reverse\n"


def pairs_text(rows):
    lines = [HEADER]
    for child, parent, ptype, pred, rev in rows:
        def q(s):
            return '"' + s.replace('"', '""') + '"' if ("," in s or '"' in s) else s
        lines.append(",".join([q(child), q(parent), ptype, q(pred), "True" if rev else "False"]) + "\n")
    return "".join(lines)


def model_text(rows, model, a, b):
    if model == "gpt-3.5-turbo":
        cols = f"{model}_can_find_parent,{model}_can_find_child"
    else:
        cols = f"{model}_parent_logprob,{model}_child_logprob"
    out = [f"child,parent,parent_type,child_prediction,{cols}\n"]
    for child, parent, ptype, pred, _ in rows:
        out.append(f"{child},{parent},{ptype},{pred},{a},{b}\n")
    return "".join(out)


def synthetic(n_pairs, n_reversed, names=1200):
    """Made-up names; both parents for each name in list order until n_pairs rows, the first n_reversed reversed."""
    listed = [f"Person {k:04d}" for k in range(names)]
    rows = []
    k = 0
    while len(rows) < n_pairs:
        for ptype in ("mother", "father"):
            if len(rows) < n_pairs:
                rows.append([listed[k], f"Parent {k:04d} {ptype[0].upper()}", ptype, "", False])
        k += 1
    for r in rows[:n_reversed]:
        r[3], r[4] = r[0], True
    rows = [tuple(r) for r in rows]
    raw = {B.PAIRS: pairs_text(rows).encode(), B.LIST: "\n".join(listed).encode(),
           B.GPT35: model_text(rows, "gpt-3.5-turbo", 0.9, 0.1).encode()}
    for m in B.LOGPROB_MODELS:
        raw[f"{m}_reversal_test_results.csv"] = model_text(rows, m, -1.0, -5.0).encode()
    return rows, listed, raw


class Readers(unittest.TestCase):
    CASES = [
        'a,b,c\n1,2,3\n',
        'a,b\n"x, y",z\n',
        'a,b\n"he said ""hi""",z\n',
        'a,b\n,\n"",x\n',
        'a,b\n\n1,2\n',
        'a,b\r\n1,2\r\n',
        'a,b\n1,2',
        'a,b\nab"c,d\n',
        'a,b\n"ab"c,d\n',
        'a\n"line\nbreak"\n',
        '',
    ]

    def test_hand_reader_agrees_with_csv(self):
        for text in self.CASES:
            self.assertEqual(B.rows_hand(text), B.rows_csv(text), repr(text))

    def test_unterminated_quote_refused(self):
        with self.assertRaises(B.Refused):
            B.rows_hand('a,b\n"open,x\n')

    def test_pairs_reader(self):
        rows = [("Ann Kestrel", "Bea Kestrel", "mother", "Ann Kestrel", True),
                ("Smith, Jo", 'Al "Big" Smith', "father", "", False)]
        self.assertEqual(B.read_pairs(pairs_text(rows)), rows)

    def test_pairs_refusals(self):
        good = pairs_text([("Ann Kestrel", "Bea Kestrel", "mother", "", False)])
        bad = [good.replace("can_reverse", "reversed"),
               good.replace("mother", "aunt"),
               good.replace(",False", ",false"),
               good.replace("Ann Kestrel,", "Ann Kestrel,x,"),
               HEADER + ",Bea Kestrel,mother,,False\n"]
        for text in bad:
            with self.assertRaises(B.Refused, msg=text):
                B.read_pairs(text)

    def test_list_reader_follows_load_from_txt(self):
        self.assertEqual(B.read_list("a\n b \nc"), ["a", "b", "c"])
        self.assertEqual(B.read_list("a\nb\n"), ["a", "b"])
        self.assertEqual(B.read_list("a\n\nb"), ["a", "", "b"])

    def test_model_reader(self):
        rows = [("Ann Kestrel", "Bea Kestrel", "mother", "", False)]
        got = B.read_model(model_text(rows, "llama-7b", -0.5, -2.0), "llama-7b")
        self.assertEqual(got, [("Ann Kestrel", "Bea Kestrel", "mother", "", -0.5, -2.0)])
        with self.assertRaises(B.Refused):
            B.read_model(model_text(rows, "llama-7b", -0.5, -2.0), "llama-30b")
        with self.assertRaises(B.Refused):
            B.read_model(model_text(rows, "llama-7b", "nan", -2.0), "llama-7b")

    def test_read_bytes(self):
        d = tempfile.mkdtemp(prefix="berglund-tests-")
        p = os.path.join(d, "f.csv")
        with open(p, "wb") as fh:
            fh.write(b"abc")
        sha = hashlib.sha256(b"abc").hexdigest()
        self.assertEqual(B.read_bytes(p, sha, 3), b"abc")
        with self.assertRaises(B.Refused):
            B.read_bytes(p, sha, 4)
        with self.assertRaises(B.Refused):
            B.read_bytes(p, "0" * 64, 3)


class Counting(unittest.TestCase):
    def test_rounds_to_edges(self):
        self.assertTrue(B.rounds_to(1570, 2000, 79))      # 78.5
        self.assertFalse(B.rounds_to(1569, 2000, 79))     # 78.45
        self.assertTrue(B.rounds_to(1589, 2000, 79))      # 79.45
        self.assertFalse(B.rounds_to(1590, 2000, 79))     # 79.5 rounds to 80
        self.assertTrue(B.rounds_to(1590, 2000, 80))
        self.assertTrue(B.rounds_to(1, 3, 33))
        self.assertFalse(B.rounds_to(1, 3, 34))
        self.assertTrue(B.rounds_to(13, 40, 33))           # 32.5
        self.assertFalse(B.rounds_to(67, 200, 33))         # 33.5

    def test_count(self):
        rows = [("A Z", "M A", "mother", "A Z", True), ("A Z", "F A", "father", "", False),
                ("B Y", "M B", "mother", "", False), ("C X", "F C", "father", "C X", True)]
        c = B.count(rows)
        self.assertEqual((c["pairs"], c["reversed"], c["children"], c["both_parents"]), (4, 2, 3, 1))
        self.assertEqual(c["by_type"], {"mother": (2, 1), "father": (2, 1)})

    def test_consistency_catches_planted_faults(self):
        names = ["A Z", "B Y", "C X"]
        good = [("A Z", "M A", "mother", "A Z", True), ("B Y", "M B", "mother", "", False),
                ("C X", "F C", "father", "C X Junior", True)]
        c = B.consistency(good, names)
        self.assertTrue(all(c[k] for k in ("can_reverse_where_filled", "predictions_begin_with_child",
                                           "children_in_first_1000", "rows_in_list_order",
                                           "each_child_and_type_once")))
        faults = {
            "can_reverse_where_filled": [("A Z", "M A", "mother", "", True)],
            "predictions_begin_with_child": [("A Z", "M A", "mother", "Q Q", True)],
            "children_in_first_1000": [("D W", "M D", "mother", "", False)],
            "rows_in_list_order": [("B Y", "M B", "mother", "", False), ("A Z", "M A", "mother", "", False)],
            "each_child_and_type_once": [("A Z", "M A", "mother", "", False), ("A Z", "N A", "mother", "", False)],
        }
        for key, rows in faults.items():
            self.assertFalse(B.consistency(rows, names)[key], key)
        many = [f"N{k}" for k in range(1005)]
        self.assertFalse(B.consistency([("N1003", "P", "mother", "", False)], many)["children_in_first_1000"])

    def test_summaries(self):
        rows = [("A", "B", "mother", "", 0.8, 0.2), ("C", "D", "father", "", 0.4, 0.6)]
        s = B.summarise_model(rows, "gpt-3.5-turbo")
        self.assertAlmostEqual(s["parent"], 0.6)
        self.assertAlmostEqual(s["child"], 0.4)
        self.assertAlmostEqual(s["parent_better_share"], 0.5)
        lp = [("A", "B", "mother", "", 0.0, -1.0), ("C", "D", "father", "", -2.0, -1.0)]
        s = B.summarise_model(lp, "llama-7b")
        self.assertAlmostEqual(s["parent"], (1 + 2.718281828459045 ** -2) / 2)
        self.assertAlmostEqual(s["child"], 2.718281828459045 ** -1)
        self.assertAlmostEqual(s["parent_better_share"], 0.5)


class Assessment(unittest.TestCase):
    def test_passing_synthetic_case(self):
        _, _, raw = synthetic(1573, 519)          # 78.65% of 2,000 and 32.99% of the pairs
        out, detail = B.assess(raw)
        self.assertEqual((out["pairs"], out["reversed"], out["test_passed"]), (1573, 519, 1))
        self.assertEqual(out["controls_passed"], out["controls_total"])
        self.assertEqual(out["both_parents"], 786)
        self.assertIn("1,573 pairs as printed: yes", out["printed"])
        self.assertIn("28% as Figure 4's note says: no", out["printed"])

    def test_failing_synthetic_cases(self):
        _, _, raw = synthetic(1573, 440)          # 27.97%: the figure's 28%, not 33%
        out, _ = B.assess(raw)
        self.assertEqual((out["conditions_met"], out["test_passed"]), (1, 0))
        self.assertIn("28% as Figure 4's note says: yes", out["printed"])
        _, _, raw = synthetic(1500, 495)          # 75% of the questions
        out, _ = B.assess(raw)
        self.assertEqual((out["conditions_met"], out["test_passed"]), (1, 0))

    def test_controls_fail_on_planted_faults(self):
        rows, listed, raw = synthetic(40, 10)
        broken = list(rows)
        broken[3] = (broken[3][0], broken[3][1], broken[3][2], "Someone Else", True)
        raw2 = dict(raw)
        raw2[B.PAIRS] = pairs_text(broken).encode()
        out, detail = B.assess(raw2)
        self.assertFalse(detail["controls"]["every child_prediction begins with its row's child (get_child's rule)"])
        self.assertFalse(detail["controls"]["the five other models' files list the same pairs and predictions, row "
                                            "by row"])
        self.assertLess(out["controls_passed"], out["controls_total"])

    def test_outputs_are_flat_and_named(self):
        _, _, raw = synthetic(100, 30)
        out, _ = B.assess(raw)
        self.assertEqual(set(out), set(B.OUTPUTS))
        self.assertEqual(len(B.OUTPUTS), len(set(B.OUTPUTS)))
        self.assertLessEqual(len(B.TEST), 600)


if __name__ == "__main__":
    unittest.main()
