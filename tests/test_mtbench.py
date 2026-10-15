"""GPT-4 as a judge on MT-bench (judge/mtbench.py): the comparisons, the setups, both computations of agreement, the
majority, the conditions, the bootstrap, the reader and its refusals, and a whole run, on votes and files made here.
None of the claim's agreements is computed.

The reader and the whole run need pyarrow (the pinned jupyter/scipy-notebook image); without it they are skipped.
Run with: python3 -m unittest tests.test_mtbench
"""

import hashlib
import importlib.util
import json
import os
import random
import tempfile
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("judge_mtbench", os.path.join(HERE, "..", "judge", "mtbench.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

try:
    import pyarrow  # noqa: F401
    HAVE_ARROW = True
except ImportError:
    HAVE_ARROW = False

A, B, C = "claude-v1", "gpt-4", "vicuna-13b-v1.2"
SEED = "0f" * 32


def v(q, a, b, w, judge, turn=1):
    return M.vote(q, a, b, w, judge, turn)


def synthetic(seed=3, questions=range(101, 111)):
    """A small dataset in the released files' form: three model pairs, two turns, a GPT-4 judgement on each
    comparison and one to three expert votes (some recorded the other way round), with authors on a few."""
    rng = random.Random(seed)
    human, gpt4 = [], []
    for q in questions:
        for a, b in ((A, B), (B, C), (A, C)):
            for t in (1, 2):
                gw = rng.choice(["model_a", "model_b", "model_a", "tie", "tie (inconsistent)"])
                gpt4.append(v(q, a, b, gw, "gpt4_pair", t))
                for k in range(rng.randint(1, 3)):
                    w = gw if rng.random() < 0.7 and "tie" not in gw else rng.choice(["model_a", "model_b", "tie"])
                    if rng.random() < 0.5:
                        human.append(v(q, a, b, w, f"expert_{rng.randint(0, 9)}", t))
                    else:
                        human.append(v(q, b, a, M.revert(w), f"expert_{rng.randint(0, 9)}", t))
                if rng.random() < 0.3:
                    human.append(v(q, a, b, rng.choice(["model_a", "model_b", "tie"]), "author_0", t))
    return human, gpt4


class Agreement(unittest.TestCase):
    def test_paper_example(self):
        h = [v(81, A, B, "model_a", "expert_1"), v(81, A, B, "model_a", "expert_2"), v(81, A, B, "model_b", "expert_3")]
        for gw, want in (("model_a", Fraction(2, 3)), ("model_b", Fraction(1, 3))):
            r = M.evaluate(M.comparisons(h, [v(81, A, B, gw, "gpt4_pair")]))[1]
            for s in ("S1", "S2"):
                self.assertEqual(r[s]["g4_expert"]["pooled"], want)
                self.assertEqual(r[s]["g4_expert"]["bycomp"], want)
                self.assertEqual(r[s]["expert_expert"]["pooled"], Fraction(1, 3))
                self.assertEqual(r[s]["expert_expert"]["pairs"], 3)

    def test_revert_and_key(self):
        d = M.comparisons([v(90, C, A, "model_a", "expert_1")], [v(90, A, C, "model_b", "gpt4_pair")])
        self.assertEqual(list(d[1]), [(90, A, C)])
        self.assertEqual(d[1][(90, A, C)]["expert"], [("expert_1", "model_b")])
        self.assertEqual(M.evaluate(d)[1]["S2"]["g4_expert"]["pooled"], 1)
        self.assertEqual(M.revert("tie"), "tie")
        self.assertEqual(M.revert("tie (inconsistent)"), "tie (inconsistent)")

    def test_turns_are_separate(self):
        d = M.comparisons([v(90, A, B, "model_a", "expert_1", 2)], [v(90, A, B, "model_a", "gpt4_pair", 1)])
        r = M.evaluate(d)
        self.assertEqual(r[1]["S1"]["g4_expert"]["pairs"], 0)
        self.assertEqual(r[2]["S1"]["g4_expert"]["pairs"], 0)

    def test_setups(self):
        h = [v(81, A, B, "tie", "expert_1"), v(81, A, B, "model_a", "expert_2"), v(82, A, B, "tie", "expert_1")]
        g = [v(81, A, B, "tie (inconsistent)", "gpt4_pair"), v(82, A, B, "tie", "gpt4_pair")]
        r = M.evaluate(M.comparisons(h, g))[1]
        self.assertEqual((r["S1"]["g4_expert"]["agreed"], r["S1"]["g4_expert"]["pairs"]), (2, 3))
        self.assertEqual(r["S2"]["g4_expert"]["pairs"], 0)
        self.assertEqual((r["S1"]["expert_expert"]["agreed"], r["S1"]["expert_expert"]["pairs"]), (0, 1))
        self.assertEqual(r["S2"]["expert_expert"]["pairs"], 0)
        self.assertTrue(M.agree("tie", "tie (inconsistent)"))
        self.assertFalse(M.agree("model_a", "tie"))

    def test_pooled_against_by_comparison(self):
        h = [v(81, A, B, "model_a", f"expert_{i}") for i in range(4)] + [v(82, A, B, "model_b", "expert_9")]
        g = [v(81, A, B, "model_a", "gpt4_pair"), v(82, A, B, "model_a", "gpt4_pair")]
        m = M.evaluate(M.comparisons(h, g))[1]["S2"]
        self.assertEqual(m["g4_expert"]["pooled"], Fraction(4, 5))
        self.assertEqual(m["g4_expert"]["bycomp"], Fraction(1, 2))
        self.assertEqual(m["g4_expert"]["comparisons"], 2)
        self.assertEqual(m["expert_expert"]["pooled"], 1)
        self.assertEqual(m["expert_expert"]["comparisons"], 1)

    def test_same_expert(self):
        h = [v(81, A, B, "model_b", "expert_1"), v(81, A, B, "model_b", "expert_1"), v(81, A, B, "model_a", "expert_2"),
             v(81, A, B, "model_a", "expert_3")]
        m = M.evaluate(M.comparisons(h, []))[1]["S2"]["expert_expert"]
        self.assertEqual((m["agreed"], m["pairs"], m["same_judge_pairs"]), (2, 6, 1))
        self.assertEqual(m["bycomp"], Fraction(1, 5))

    def test_authors(self):
        h = [v(81, A, B, "model_a", "author_0"), v(81, A, B, "model_b", "author_1"), v(81, A, B, "model_a", "expert_1")]
        r = M.evaluate(M.comparisons(h, [v(81, A, B, "model_a", "gpt4_pair")]))[1]["S2"]
        self.assertEqual(r["g4_author"]["pooled"], Fraction(1, 2))
        self.assertEqual(r["author_expert"]["pooled"], Fraction(1, 2))
        self.assertEqual(r["author_author"]["pooled"], 0)
        self.assertEqual(r["g4_expert"]["pairs"], 1)

    def test_majority(self):
        self.assertEqual(M.majority_share("model_a", ["model_a", "model_b"]), Fraction(1, 2))
        self.assertEqual(M.majority_share("model_b", ["model_a", "model_a", "model_b"]), 0)
        self.assertEqual(M.majority_share("tie (inconsistent)", ["tie", "model_a", "tie"]), 1)
        self.assertEqual(M.majority_share("model_a", ["tie", "model_a", "model_b"]), Fraction(1, 3))
        h = [v(81, A, B, "model_a", "expert_1"), v(81, A, B, "model_b", "expert_2"), v(82, A, B, "tie", "expert_1")]
        g = [v(81, A, B, "model_b", "gpt4_pair"), v(82, A, B, "model_a", "gpt4_pair")]
        r = M.evaluate(M.comparisons(h, g))[1]
        self.assertEqual((r["S2"]["g4_majority"]["value"], r["S2"]["g4_majority"]["comparisons"]), (Fraction(1, 2), 1))
        self.assertEqual((r["S1"]["g4_majority"]["value"], r["S1"]["g4_majority"]["comparisons"]), (Fraction(1, 4), 2))
        self.assertEqual(r["S2"]["expert_majority_own"], {"value": Fraction(1, 2), "votes": 2})
        self.assertEqual(r["S2"]["expert_majority_others"], {"value": Fraction(0), "votes": 2})

    def test_second_gpt4_judgement_refused(self):
        with self.assertRaises(M.Refused):
            M.comparisons([], [v(81, A, B, "model_a", "gpt4_pair"), v(81, B, A, "model_a", "gpt4_pair")])


def fake(g1, h1, g2, h2):
    """Results with the given S2 agreements (both computations alike)."""
    return {t: {"S2": {"g4_expert": {"pooled": g, "bycomp": g}, "expert_expert": {"pooled": h, "bycomp": h}}}
            for t, g, h in ((1, g1, h1), (2, g2, h2))}


class Conditions(unittest.TestCase):
    def test_all_hold(self):
        c = M.conditions(fake(Fraction(85, 100), Fraction(81, 100), Fraction(85, 100), Fraction(82, 100)))
        self.assertEqual(len(c), 8)
        self.assertTrue(all(c.values()))

    def test_eighty_is_not_above(self):
        c = M.conditions(fake(Fraction(4, 5), Fraction(3, 4), Fraction(9, 10), Fraction(3, 4)))
        self.assertEqual(sum(c.values()), 6)

    def test_gap(self):
        c = M.conditions(fake(Fraction(84, 100), Fraction(89, 100), Fraction(84, 100), Fraction(90, 100)))
        self.assertEqual(sum(c.values()), 6)
        self.assertEqual([k for k, ok in c.items() if not ok],
                         [k for k in c if k.startswith("turn 2") and "below" in k])

    def test_missing_refused(self):
        with self.assertRaises(M.Refused):
            M.conditions(fake(None, Fraction(1, 2), Fraction(1, 2), Fraction(1, 2)))


class Printed(unittest.TestCase):
    def test_cells(self):
        h, g = synthetic()
        cells = M.against_printed(M.evaluate(M.comparisons(h, g)))
        self.assertEqual(len(cells), 24)
        self.assertFalse(any(c["count_matches"] for c in cells))

    def test_percent_within_half_a_point(self):
        res = {t: {s: {k: {"pooled": None, "pairs": 0, "value": None, "comparisons": 0}
                       for k in ("g4_expert", "expert_expert", "g4_author", "author_expert", "author_author",
                                 "g4_majority")} for s in M.SETUPS} for t in M.TURNS}
        res[1]["S2"]["g4_expert"] = {"pooled": Fraction(8545, 10000), "pairs": 859}
        res[2]["S2"]["g4_expert"] = {"pooled": Fraction(8551, 10000), "pairs": 864}
        cells = {c["cell"]: c for c in M.against_printed(res)}
        self.assertTrue(cells["G4-Pair/Human S2 turn 1"]["percent_matches"])
        self.assertTrue(cells["G4-Pair/Human S2 turn 1"]["count_matches"])
        self.assertFalse(cells["G4-Pair/Human S2 turn 2"]["percent_matches"])


class Bootstrap(unittest.TestCase):
    def test_seeded(self):
        h, g = synthetic()
        d = M.comparisons(h, g)
        a, b, c = M.bootstrap(SEED, d, 300), M.bootstrap(SEED, d, 300), M.bootstrap("1e" * 32, d, 300)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        r = M.evaluate(d)
        for t in M.TURNS:
            lo, hi = a[t]["g4_expert"]
            self.assertLessEqual(lo, float(r[t]["S2"]["g4_expert"]["pooled"]) + 1e-12)
            self.assertGreaterEqual(hi, float(r[t]["S2"]["g4_expert"]["pooled"]) - 0.2)
            self.assertEqual(a[t]["questions"], 10)


@unittest.skipUnless(HAVE_ARROW, "needs pyarrow")
class Reader(unittest.TestCase):
    def test_round_trip(self):
        h, g = synthetic()
        hr, gr = M.read_rows(M.votes_parquet(h), "human"), M.read_rows(M.votes_parquet(g), "gpt4")
        self.assertEqual(hr, h)
        self.assertEqual(gr, g)

    def test_refusals(self):
        for kind, row in (("human", v(81, A, B, "model_c", "expert_1")), ("human", v(81, A, B, "tie", "expert1")),
                          ("human", v(81, A, B, "tie", "expert_1", 0)), ("human", v(80, A, B, "tie", "expert_1")),
                          ("human", v(81, B, B, "tie", "expert_1")), ("human", v(81, A, "dolly-12b", "tie", "expert_1")),
                          ("gpt4", v(81, A, B, "tie", "expert_1")), ("gpt4", v(81, A, B, "tie (bothbad)", "gpt4_pair"))):
            with self.assertRaises(M.Refused, msg=repr(row)):
                M.read_rows(M.votes_parquet([row]), kind)
        with self.assertRaises(M.Refused):
            M.read_rows(b"PAR1 but not really", "gpt4")

    def test_controls(self):
        c = M.controls_known()
        self.assertEqual(len(c), 8)
        self.assertTrue(all(c.values()), [k for k, ok in c.items() if not ok])


@unittest.skipUnless(HAVE_ARROW, "needs pyarrow")
class WholeRun(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        h, g = synthetic()
        self.spec = {}
        for kind, rows, name in (("human", h, "h.parquet"), ("gpt4", g, "g.parquet")):
            data = M.votes_parquet(rows)
            with open(os.path.join(self.dir, name), "wb") as fh:
                fh.write(data)
            self.spec[kind] = (name, hashlib.sha256(data).hexdigest())
        self.n = {"human": len(h), "gpt4": len(g)}

    def test_run(self):
        res = os.path.join(self.dir, "results")
        out, detail = M.run(SEED, inputs=self.dir, results=res, spec=self.spec, rows=self.n)
        self.assertEqual(tuple(sorted(out)), tuple(sorted(M.OUTPUTS)))
        for k, x in out.items():
            self.assertTrue(isinstance(x, (int, float, str)) and not isinstance(x, bool), k)
            if isinstance(x, str):
                self.assertLessEqual(len(x), M.LIMIT, k)
        self.assertIsInstance(out["test_passed"], int)
        self.assertEqual(out["conditions_total"], 8)
        self.assertEqual(out["controls_passed"], out["controls_total"])
        self.assertEqual(out["printed_cells"], 24)
        for k in ("g4_expert_s2_t1", "expert_expert_s2_bycomp_t2"):
            self.assertTrue(0 <= out[k] <= 1)
        with open(os.path.join(res, "outputs.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), out)
        with open(os.path.join(res, "detail.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["test"], M.TEST)
        again, _ = M.run(SEED, inputs=self.dir, results=res, spec=self.spec, rows=self.n)
        self.assertEqual(again, out)

    def test_rows_and_hash_refused(self):
        with self.assertRaises(M.Refused):
            M.run(SEED, inputs=self.dir, results=self.dir, spec=self.spec, rows={"human": self.n["human"] + 1})
        bad = dict(self.spec, gpt4=(self.spec["gpt4"][0], "0" * 64))
        with self.assertRaises(M.Refused):
            M.run(SEED, inputs=self.dir, results=self.dir, spec=bad, rows=self.n)
        with self.assertRaises(M.Refused):
            M.run("xyz", inputs=self.dir, results=self.dir, spec=self.spec, rows=self.n)


class Registered(unittest.TestCase):
    def test_test_text(self):
        self.assertLessEqual(len(M.TEST), 600)
        self.assertIn("f7d2896", M.TEST)
        self.assertEqual(M.AGREE_MIN, Fraction(4, 5))
        self.assertEqual(M.GAP_MAX, Fraction(1, 20))

    def test_inputs(self):
        self.assertEqual(M.INPUTS["human"][1], "4877bc46a40929f4082c3c79593700fb897b1d6c7f4c473032694a01322f5769")
        self.assertEqual(M.INPUTS["gpt4"][1], "57068327ffb5f8fddb15fedbbfe40b26fe862da2326331e5cf64a42320a00e71")
        self.assertEqual(M.ROWS, {"human": 3355, "gpt4": 2400})


if __name__ == "__main__":
    unittest.main()
