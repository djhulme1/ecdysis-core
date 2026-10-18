"""Nguyen and Fithian's Model 1 check (metr/nf2026.py): the I-spline basis, the objectives' gradients, the scores and
their closed forms, the fits' recovery of known parameters, the cross-validation's folds and pooling, METR's fit, and
the readers' refusals, all on data made up here. Nothing here reads METR's results or the paper.

Run with: python3 -m unittest tests.test_nf2026 (in the pinned scipy-notebook image)
"""

import gzip
import importlib.util
import io
import json
import math
import os
import sys
import tarfile
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("metr_nf2026", os.path.join(HERE, "..", "metr", "nf2026.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)

SEED = "5" * 64
OTHER = "a3" * 32


def toy(seed=SEED, kind="baseline"):
    d, beta, _ = M.simulate(seed, kind)
    return d, beta


class Spline(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(1)
        self.xs = np.sort(rng.uniform(-3, 9, 60))
        self.spl = M.ISpline(self.xs, "Q")

    def test_ends_and_monotone(self):
        s = self.spl
        B = s.basis(np.array([s.lo, s.hi]))
        self.assertTrue(np.allclose(B[0], 0.0, atol=1e-14))
        self.assertTrue(np.allclose(B[1], 1.0, atol=1e-12))
        grid = np.linspace(s.lo - 2, s.hi + 2, 2001)
        G = s.basis(grid)
        self.assertTrue(np.all(np.diff(G, axis=0) >= -1e-12))
        self.assertEqual(s.K, 7)
        self.assertEqual(len(s.t), 12)
        self.assertTrue(np.allclose(s.inner, np.quantile(self.xs, [0.2, 0.4, 0.6, 0.8])))

    def test_identity_reproduced(self):
        s = self.spl
        pi = s.identity_pi()
        self.assertAlmostEqual(float(pi.sum()), 1.0, places=12)
        grid = np.linspace(s.lo - 1, s.hi + 1, 501)
        f = s.lo + (s.hi - s.lo) * (s.basis(grid) @ pi)
        self.assertLess(float(np.max(np.abs(f - grid))), 1e-6)

    def test_linear_beyond_the_ends(self):
        s = self.spl
        e = 1e-6
        for end, sign in ((s.lo, -1), (s.hi, 1)):
            inside = s.basis(np.array([end - sign * e, end]))
            outside = s.basis(np.array([end, end + sign * e, end + sign * 3.0, end + sign * 6.0]))
            d_in = (inside[1] - inside[0]) / e
            d_out = (outside[1] - outside[0]) / e
            self.assertTrue(np.allclose(d_in, d_out, atol=1e-4))
            self.assertTrue(np.allclose(outside[3] - outside[2], outside[2] - outside[0], atol=1e-9))

    def test_equal_knots(self):
        s = M.ISpline(self.xs, "E")
        self.assertTrue(np.allclose(s.inner, s.lo + (s.hi - s.lo) * np.array([0.2, 0.4, 0.6, 0.8])))

    def test_refuses_no_range(self):
        with self.assertRaises(M.Refused):
            M.ISpline(np.array([2.0, 2.0, 2.0]))

    def test_natural(self):
        s = M.NaturalISpline(self.xs, "Q")
        self.assertEqual(s.K, 5)
        B = s.basis(np.array([s.lo, s.hi]))
        self.assertTrue(np.allclose(B[0], 0.0, atol=1e-14))
        self.assertTrue(np.allclose(B[1], 1.0, atol=1e-12))
        grid = np.linspace(s.lo - 2, s.hi + 2, 2001)
        self.assertTrue(np.all(np.diff(s.basis(grid), axis=0) >= -1e-12))
        e = 1e-3
        for end in (s.lo, s.hi):
            inner = end + 3 * e if end == s.lo else end - 3 * e
            v = s.basis(np.array([inner - e, inner, inner + e]))
            self.assertTrue(np.all(np.abs((v[0] - 2 * v[1] + v[2]) / e ** 2) < 0.02), (v[0] - 2 * v[1] + v[2]) / e ** 2)
        full = M.ISpline(self.xs, "Q")
        v = full.basis(np.array([s.lo + 3e-3 - 1e-3, s.lo + 3e-3, s.lo + 3e-3 + 1e-3]))
        self.assertGreater(float(np.max(np.abs((v[0] - 2 * v[1] + v[2]) / 1e-6))), 0.1)   # the full basis bends there
        pi = s.identity_pi()
        f = s.lo + (s.hi - s.lo) * (s.basis(grid) @ pi)
        self.assertLess(float(np.max(np.abs(f - grid))), 1e-6)

    def test_natural_fit(self):
        d, beta, p_true = M.simulate(SEED, "spline")
        J = len(d.ais)
        base = M.fit_baseline(d, J)
        m = M.fit_model1(d, J, M.NaturalISpline(d.x_task, "Q"), base)
        self.assertLessEqual(m["loss"], base["loss"] + 1e-9)
        self.assertEqual(len(m["pi"]), 5)
        folds = M.fold_assignment(SEED, 0, len(d.families))
        sc, preds, _ = M.crossval(d, folds, spline=M.NaturalISpline)
        self.assertTrue(np.all(np.isfinite(preds["model1"])))


class Gradients(unittest.TestCase):
    def check(self, fun, theta, eps=1e-6):
        v, g = fun(theta)
        for i in range(len(theta)):
            tp, tm = theta.copy(), theta.copy()
            tp[i] += eps
            tm[i] -= eps
            num = (fun(tp)[0] - fun(tm)[0]) / (2 * eps)
            self.assertLess(abs(num - g[i]), 1e-5 * max(1.0, abs(num)), i)

    def test_baseline(self):
        d, _ = toy()
        J = len(d.ais)
        rng = np.random.default_rng(2)
        self.check(M.baseline_objective(d, J), np.concatenate([rng.normal(0, 1, J), [math.log(0.7)]]))

    def test_model1(self):
        d, _ = toy(kind="spline")
        J = len(d.ais)
        spl = M.ISpline(d.x_task, "Q")
        rng = np.random.default_rng(3)
        self.check(M.model1_objective(d, J, spl),
                   np.concatenate([rng.normal(0, 1, J), [math.log(0.7)], rng.normal(0, 1, spl.K)]))

    def test_model1_at_identity_is_the_baseline(self):
        d, _ = toy()
        J = len(d.ais)
        spl = M.ISpline(d.x_task, "Q")
        a = np.linspace(-1, 2, J)
        v0, _ = M.baseline_objective(d, J)(np.concatenate([a, [math.log(0.6)]]))
        v1, _ = M.model1_objective(d, J, spl)(np.concatenate([a, [math.log(0.6)], np.log(spl.identity_pi())]))
        self.assertLess(abs(v0 - v1), 1e-5 * abs(v0))


class Scores(unittest.TestCase):
    def test_smoothed_closed_form(self):
        for q in (0.5, 0.8):
            for p in (0.01, 0.3, q - 0.05, q - 0.031, q, q + 0.017, q + 0.05, 0.97):
                s1, s0 = M.smoothed_elementary(np.array([p]), q)
                us = q - 0.05 + 0.1 * (np.arange(200000) + 0.5) / 200000
                n1 = float(np.mean((1 - us) * (p < us)))
                n0 = float(np.mean(us * (p > us)))
                self.assertAlmostEqual(float(s1[0]), n1, places=5)
                self.assertAlmostEqual(float(s0[0]), n0, places=5)

    def test_brier_is_twice_the_integral(self):
        rng = np.random.default_rng(4)
        p = rng.uniform(0, 1, 50)
        n = rng.integers(1, 9, 50).astype(float)
        k = np.array([rng.integers(0, int(v) + 1) for v in n], dtype=float)
        brier = k * (1 - p) ** 2 + (n - k) * p ** 2
        N = 100000
        acc = np.zeros(50)
        for q in (np.arange(N) + 0.5) / N:
            acc += k * (1 - q) * (p < q) + (n - k) * q * (p > q)
        self.assertLess(float(np.max(np.abs(2 * acc / N - brier))), 3e-4)

    def test_cell_scores_and_pooling(self):
        d, _ = toy()
        p = np.full(len(d.j), 0.3)
        cs = M.cell_scores(p, d.n, d.k)
        sc = M.pooled(cs, d)
        share = float(d.k.sum() / d.n.sum())
        self.assertAlmostEqual(sc["brier equal-task"], share * 0.49 + (1 - share) * 0.09, places=10)
        self.assertAlmostEqual(sc["log equal-task"], -(share * math.log(0.3) + (1 - share) * math.log(0.7)), places=10)
        self.assertEqual(len(sc), 12)

    def test_control_scores(self):
        d, _ = toy()
        rng = np.random.default_rng(5)
        p = rng.uniform(0.02, 0.98, len(d.j))
        sc = M.pooled(M.cell_scores(p, d.n, d.k), d)
        b, s = M.control_scores(p, d)
        self.assertLess(abs(b - sc["brier equal-task"]), 1e-4)
        self.assertLess(abs(s - sc["q0.5 equal-task"]), 3e-5)


class Fits(unittest.TestCase):
    def test_baseline_recovers_slope(self):
        for seed in (SEED, OTHER):
            d, beta = toy(seed)
            fit = M.fit_baseline(d, len(d.ais))
            self.assertLess(abs(fit["beta"] - beta) / beta, 0.05)

    def test_model1_on_spline_data(self):
        for seed in (SEED, OTHER):
            d, beta, p_true = M.simulate(seed, "spline")
            J = len(d.ais)
            base = M.fit_baseline(d, J)
            m1 = M.fit_model1(d, J, M.ISpline(d.x_task, "Q"), base)
            self.assertLess(m1["loss"], base["loss"])
            self.assertLess(M.rms(M.predict(m1, "model1", d), p_true), 0.03)
            self.assertGreaterEqual(M.rms(M.predict(base, "baseline", d), p_true), 0.03)
            self.assertLess(abs(m1["beta"] - beta) / beta, 0.15)
            spl = M.ISpline(d.x_task, "Q")
            truth = spl.lo + (spl.hi - spl.lo) * (spl.basis(d.x_task) @ np.array(M.PI_TRUE))
            self.assertLess(float(np.max(np.abs(M.f_of(m1, d.x_task) - truth))), 0.6)

    def test_simulated_truth(self):
        d, beta, p_true = M.simulate(SEED, "baseline")
        self.assertEqual(len(p_true), len(d.j))
        emp = d.k.sum() / d.n.sum()
        self.assertLess(abs(float(np.mean(p_true)) - emp), 0.02)

    def test_model1_never_worse_in_sample(self):
        d, _ = toy()
        J = len(d.ais)
        base = M.fit_baseline(d, J)
        m1 = M.fit_model1(d, J, M.ISpline(d.x_task, "Q"), base)
        self.assertLessEqual(m1["loss"], base["loss"] + 1e-9)

    def test_separate(self):
        d, beta = toy()
        sep = M.fit_separate(d, len(d.ais))
        self.assertTrue(np.all(sep[:, 1] > 0))
        self.assertLess(abs(float(np.median(sep[:, 1])) - beta) / beta, 0.1)


class CrossValidation(unittest.TestCase):
    def test_folds(self):
        f = M.fold_assignment(SEED, 0, 79)
        self.assertEqual(sorted(len(x) for x in f), [15, 16, 16, 16, 16])
        self.assertEqual(sorted(set().union(*f)), list(range(79)))
        self.assertEqual(f, M.fold_assignment(SEED, 0, 79))
        self.assertNotEqual(f, M.fold_assignment(SEED, 1, 79))
        self.assertNotEqual(f, M.fold_assignment(OTHER, 0, 79))

    def test_every_cell_predicted_once(self):
        d, _ = toy(kind="spline")
        folds = M.fold_assignment(SEED, 0, len(d.families))
        sc, preds, losses = M.crossval(d, folds)
        self.assertTrue(np.all(np.isfinite(preds["model1"])))
        self.assertEqual(len(losses), 5)
        self.assertTrue(all(m1 <= b0 + 1e-9 for b0, m1 in losses))
        d12 = M.differences(sc)
        self.assertEqual(len(d12), 12)
        self.assertLess(d12["log equal-task"], 0)      # spline data: Model 1 predicts held-out families better
        ci = M.cluster_ci(preds["model1"], preds["baseline"], d)
        for m in M.METRICS:
            lo, hi = ci[m]
            self.assertLessEqual(lo, d12[m] + 1e-12)
            self.assertGreaterEqual(hi, d12[m] - 1e-12)

    def test_permuted_times_worsen(self):
        d, _ = toy()
        folds = M.fold_assignment(SEED, 0, len(d.families))
        sc, _, _ = M.crossval(d, folds, kinds=("baseline",))
        rng = np.random.default_rng(6)
        dp = d.with_x(d.x_task[rng.permutation(len(d.x_task))])
        scp, _, _ = M.crossval(dp, folds, kinds=("baseline",))
        self.assertGreater(scp["baseline"]["log equal-task"] - sc["baseline"]["log equal-task"], 0.02)
        self.assertFalse(np.shares_memory(dp.x, d.x))


class Metr(unittest.TestCase):
    def test_recovers_known_curve(self):
        x = np.repeat(np.linspace(-3, 9, 41), 2)
        y = np.tile([1.0, 0.0], 41)
        p = 1 / (1 + np.exp(-(-0.7 * x[::2] + 3)))
        w = np.empty(82)
        w[0::2], w[1::2] = p, 1 - p
        a, b = M.metr_fit(x, y, w / w.sum(), lam=0.0)
        self.assertAlmostEqual(a, -0.7, places=7)
        self.assertAlmostEqual(b, 3.0, places=7)

    def test_control_on_made_up_results(self):
        rng = np.random.default_rng(7)
        cells = []
        for i in range(120):
            m = float(2.0 ** rng.uniform(-2, 9))
            n = int(rng.integers(2, 7))
            pr = 1 / (1 + math.exp(-(1.2 - 0.6 * math.log2(m))))
            cells.append({"task": f"f{i % 37:02d}/t{i}", "n": n, "k": int(rng.binomial(n, pr)), "minutes": m,
                          "weight": None})
        fams = {}
        for c in cells:
            fams[M.family(c["task"])] = fams.get(M.family(c["task"]), 0) + 1
        xs, ys, ws = [], [], []
        for c in cells:
            for yv, cnt in ((1, c["k"]), (0, c["n"] - c["k"])):
                if cnt:
                    xs.append(math.log2(c["minutes"]))
                    ys.append(float(yv))
                    ws.append(cnt / (c["n"] * math.sqrt(fams[M.family(c["task"])])))
        w = np.array(ws)
        a, b = M.metr_fit(np.array(xs), np.array(ys), w / w.sum())
        agents = {"made up": {"cells": cells, "coefficient": round(a, 3), "intercept": round(b, 3)}}
        worst, who = M.control_metr(agents)
        self.assertLess(worst, 6e-4)
        agents["made up"]["coefficient"] = round(a, 3) + 0.01
        self.assertGreater(M.control_metr(agents)[0], M.METR_TOL)


class Readers(unittest.TestCase):
    YAML = """benchmark_name: made up
agents:
  AI one:
    coefficient: -0.5
    intercept: 1.0
    release_date: 2024-01-02
    tasks:
    - task_id: fam_a/t1
      human_minutes: 3.5
      n_successes: 2
      n_runs: 4
      task_weight: 0.707
    - task_id: fam_a/t2
      human_minutes: 30.0
      n_successes: 0
      n_runs: 3
      task_weight: 0.707
"""

    def test_results(self):
        a = M.read_results(self.YAML.encode())
        self.assertEqual(list(a), ["AI one"])
        self.assertEqual([c["n"] for c in a["AI one"]["cells"]], [4, 3])
        bad = self.YAML.replace("n_successes: 0", "n_successes: 5")
        with self.assertRaises(M.Refused):
            M.read_results(bad.encode())
        with self.assertRaises(M.Refused):
            M.read_results(b"agents: []\n")

    def run_lines(self, rows):
        return "\n".join(json.dumps(r) for r in rows).encode()

    def test_th10(self):
        minutes = {"fam_a/t1": 3.5, "fam_a/t2": 30.0}
        rows = [{"alias": "GPT-2", "task_id": "fam_a/t1", "run_id": "r1", "score_binarized": 1, "cloned": None},
                {"alias": "GPT-2", "task_id": "fam_a/t1", "run_id": "r2", "score_binarized": 0, "cloned": 0.0},
                {"alias": "GPT-2", "task_id": "fam_z/t9", "run_id": "r3", "score_binarized": 1},
                {"alias": "o3", "task_id": "fam_a/t1", "run_id": "r4", "score_binarized": 1}]
        out = M.read_th10(self.run_lines(rows), minutes)
        self.assertEqual(out["GPT-2"], [{"task": "fam_a/t1", "n": 2, "k": 1, "minutes": 3.5, "weight": None}])
        self.assertEqual(out["gpt-3.5-turbo-instruct"], [])
        for bad in ({"run_id": "r1"}, {"cloned": 1.0, "run_id": "r9"}, {"score_binarized": 0.5, "run_id": "r9"},
                    {"score_binarized": True, "run_id": "r9"}):
            extra = dict(rows[0])
            extra.update(bad)
            with self.assertRaises(M.Refused):
                M.read_th10(self.run_lines(rows + [extra]), minutes)

    def test_two_human_times_refused(self):
        cells = {"a": [{"task": "f/t", "n": 1, "k": 1, "minutes": 2.0}],
                 "b": [{"task": "f/t", "n": 1, "k": 0, "minutes": 3.0}]}
        with self.assertRaises(M.Refused):
            M.Data(cells)

    def tarball(self, text):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tf:
            data = text.encode()
            ti = tarfile.TarInfo("main.tex")
            ti.size = len(data)
            tf.addfile(ti, io.BytesIO(data))
        return gzip.compress(buf.getvalue())

    def test_tex(self):
        whole = "\\documentclass{article}\n" + "\n\n".join(M.PRINTED_TEX)
        M.check_tex(self.tarball(whole))
        with self.assertRaises(M.Refused):
            M.check_tex(self.tarball(whole.replace("26 AIs", "25 AIs")))
        commented = whole.replace("On 228 tasks and 26 AIs", "% On 228 tasks and 26 AIs")
        with self.assertRaises(M.Refused):
            M.check_tex(self.tarball(commented))

    def test_refuses_wrong_bytes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "x")
            with open(p, "wb") as fh:
                fh.write(b"not the file")
            with self.assertRaises(M.Refused):
                M.read_bytes(p, "0" * 64, 12)


if __name__ == "__main__":
    unittest.main()
