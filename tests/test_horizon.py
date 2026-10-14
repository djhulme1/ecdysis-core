"""METR's time horizons (metr/horizon.py): the dates and runs readers and their refusals; the paper's weights; the
logistic fit and the horizon read from it; the log-linear trend; the hierarchical bootstrap, repeatable by seed; the seed
refused; and, with the repository's files at inputs/ (or METR_INPUTS), the frontier models' run counts and weights,
which fit nothing.

Needs numpy (the pinned scipy-notebook image). Run with: python3 -m unittest tests.test_horizon
"""

import datetime
import importlib.util
import json
import math
import os
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("metr_horizon", os.path.join(HERE, "..", "metr", "horizon.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)
INPUTS = os.environ.get("METR_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = all(os.path.isfile(os.path.join(INPUTS, name)) for name, _ in M.INPUTS.values())
SEED = "0" * 63 + "1"


def run_line(**kw):
    r = {"alias": "o1", "task_id": "fam/t1", "task_family": "fam", "run_id": "r1", "score_binarized": 1,
         "human_minutes": 12.5, "invsqrt_task_weight": 0.1}
    r.update(kw)
    return json.dumps(r)


class Dates(unittest.TestCase):
    def test_reads_the_table(self):
        got = M.release_dates("date:\n  GPT-2: 2019-02-14\n  o1-preview (elicited): 2024-09-12\n")
        self.assertEqual(got, {"GPT-2": datetime.date(2019, 2, 14), "o1-preview (elicited)": datetime.date(2024, 9, 12)})

    def test_refuses(self):
        for text in ("models:\n  GPT-2: 2019-02-14\n", "date:\n  GPT-2: 14 February 2019\n",
                     "date:\n  GPT-2: 2019-02-14\n  GPT-2: 2019-02-15\n", "date:\nother:\n  x: 2019-01-01\n"):
            with self.subTest(text=text):
                with self.assertRaises(M.Refused):
                    M.release_dates(text)


class Runs(unittest.TestCase):
    def test_reads_and_skips_other_models(self):
        text = "\n".join([run_line(), run_line(run_id="r2", score_binarized=0), run_line(alias="other", run_id="r3")])
        got = M.read_runs(text, ("o1",))
        self.assertEqual([r["run"] for r in got["o1"]], ["r1", "r2"])
        self.assertEqual(got["o1"][1]["y"], 0)

    def test_refuses(self):
        for bad in (run_line(score_binarized=0.5), run_line(score_binarized=True), run_line(human_minutes=0),
                    run_line(human_minutes="12"), run_line(task_id=""), run_line(task_family=None),
                    run_line(run_id=7)):
            with self.subTest(bad=bad):
                with self.assertRaises(M.Refused):
                    M.read_runs(bad, ("o1",))
        with self.assertRaises(M.Refused):
            M.read_runs("\n".join([run_line(), run_line()]), ("o1",))      # a run twice
        with self.assertRaises(M.Refused):
            M.read_runs(run_line(), ("o1", "o3"))                          # a model with no runs


class Weights(unittest.TestCase):
    def test_the_papers_rule(self):
        runs = [{"task": "a", "family": "F"}, {"task": "a", "family": "F"}, {"task": "b", "family": "F"},
                {"task": "c", "family": "G"}]
        raw = np.array([1 / (2 * math.sqrt(2)), 1 / (2 * math.sqrt(2)), 1 / math.sqrt(2), 1.0])
        self.assertTrue(np.allclose(M.weights(runs), raw / raw.sum()))


class Fit(unittest.TestCase):
    def test_known_answers(self):
        self.assertEqual(M.controls_known(), (True, True))

    def test_horizon(self):
        self.assertAlmostEqual(M.horizon(-1.0, 2.0), 4.0)
        self.assertAlmostEqual(M.horizon(-1.0, 2.0, 0.8), 2 ** (2 - math.log(4)))

    def test_matches_a_direct_minimisation(self):
        rng = np.random.default_rng(5)
        x = rng.uniform(-3, 9, 400)
        y = (rng.random(400) < 1 / (1 + np.exp(-(-0.9 * x + 2.5)))).astype(float)
        w = rng.uniform(0.5, 1.5, 400)
        w /= w.sum()
        a, b, g = M.fit(x, y, w)
        self.assertLess(g, 1e-10)

        def loss(a, b):
            z = a * x + b
            return float(np.sum(w * (np.logaddexp(0, z) - y * z)) + 0.5 * M.LAMBDA * a * a)
        best = loss(a, b)
        for da in (-1e-4, 1e-4):
            for db in (-1e-4, 1e-4):
                self.assertGreaterEqual(loss(a + da, b + db), best)

    def test_separated_outcomes_stay_finite(self):
        x = np.array([0.0, 1, 2, 3, 4, 5])
        y = np.array([1.0, 1, 1, 0, 0, 0])
        w = np.full(6, 1 / 6)
        a, b, g = M.fit(x, y, w)
        self.assertTrue(math.isfinite(a) and a < 0 and g < 1e-10)


class Trend(unittest.TestCase):
    def test_exact_exponential(self):
        d0 = datetime.date(2020, 1, 1)
        pts = [(d0 + datetime.timedelta(days=k), 3 * 2 ** (k / 300)) for k in (0, 100, 450, 900)]
        doubling, r2 = M.trend(pts)
        self.assertAlmostEqual(doubling, 300.0, places=6)
        self.assertAlmostEqual(r2, 1.0, places=12)


def synthetic():
    """Runs for all twelve frontier names: six tasks in three families, longer tasks failed more by earlier models."""
    data, dates = {}, {}
    for k, m in enumerate(M.FRONTIER):
        runs = []
        for t, minutes in enumerate((1, 4, 16, 64, 256, 960)):
            for rep in range(3):
                h = 2 ** (k / 2)
                y = 1 if minutes < h * (1 + rep) else 0
                runs.append({"task": f"t{t}", "family": f"f{t // 2}", "run": f"{m}-{t}-{rep}", "y": y,
                             "minutes": float(minutes)})
        runs.append({"task": "t0", "family": "f0", "run": f"{m}-easy", "y": 1, "minutes": 0.5})
        x, y = M.arrays(runs)
        data[m] = {"runs": runs, "x": x, "y": y, "w": M.weights(runs)}
        dates[m] = datetime.date(2019, 1, 1) + datetime.timedelta(days=150 * k)
    return data, dates


class Bootstrap(unittest.TestCase):
    def test_repeatable_by_seed(self):
        data, dates = synthetic()
        one = M.bootstrap(SEED, data, dates, n=6)
        two = M.bootstrap(SEED, data, dates, n=6)
        other = M.bootstrap("f" * 64, data, dates, n=6)
        self.assertEqual([repr(v) for v in one[4]], [repr(v) for v in two[4]])
        self.assertNotEqual([repr(v) for v in one[4]], [repr(v) for v in other[4]])
        self.assertTrue(one[0] <= one[1])
        self.assertLessEqual(one[3], 6)


class Seed(unittest.TestCase):
    def test_refuses_a_bad_seed(self):
        with self.assertRaises(M.Refused):
            M.run("xyz", inputs=os.path.join(HERE, "_never"), results=os.path.join(HERE, "_never"))


@unittest.skipUnless(HAVE, "the repository's files are not at inputs/ (or METR_INPUTS)")
class RepositoryFiles(unittest.TestCase):
    def test_counts_and_weights(self):
        raw = {k: M.read_bytes(os.path.join(INPUTS, name), sha) for k, (name, sha) in M.INPUTS.items()}
        dates = M.release_dates(raw["dates"].decode("utf-8"))
        self.assertTrue(all(m in dates for m in M.FRONTIER + M.LATER))
        runs = M.read_runs(raw["runs"].decode("utf-8"), M.FRONTIER)
        self.assertEqual([len(runs[m]) for m in M.FRONTIER],
                         [747, 1483, 1067, 1286, 1378, 1369, 1381, 1345, 1384, 1345, 1353, 1288])
        for m in M.FRONTIER:
            w = M.weights(runs[m])
            fw = np.array([r["file_weight"] for r in runs[m]])
            self.assertLess(float(np.max(np.abs(w - fw) / w)), 1e-6, m)


if __name__ == "__main__":
    unittest.main()
