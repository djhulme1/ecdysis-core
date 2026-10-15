"""Shifted STDP (snn/babadi.py and its engine snn/babadi.c): the window; the pairing of adjacent spikes, against an
independent walk over the events and a hand-worked case; the C program against the plain implementation on replayed
inputs; the integration's free mean and the input rates; the checkpoints, the stops and the bounds; and the settling
rule and the test's conditions on synthetic checkpoints. All on small cases and parameters chosen here: no run of the
paper's model at its parameters is made.

Run with: python3 -m unittest tests.test_babadi
"""

import importlib.util
import math
import os
import random
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("snn_babadi", os.path.join(HERE, "..", "snn", "babadi.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "5c" * 32


def small(**kw):
    p = dict(M.BASE, nex=20, nin=5, rex=60.0, rin=30.0, d=1.5, T=1.0, cp=1.0, stop_rate=0, stop_mean=0, seed=3)
    p.update(kw)
    return p


def walk(params, winit, spikes, posts):
    """Adjacent pairs, formulated independently of both implementations: for each synapse, merge its presynaptic spikes
    with all the postsynaptic spikes in the order the programs process them (a step's presynaptic spikes, at k dt, before
    a postsynaptic spike at the step's end, (k + 1) dt), and change the strength by F(t_post - t_pre) for every pair of
    neighbours of different kinds in that sequence, clipping at 0 after each change."""
    dt = params["dt"]
    w = list(winit)
    post_events = [((int(round(tp / dt)) - 1, 1, 0), "post", tp) for tp in posts]
    for i in range(params["nex"]):
        pre_events = [((k, 0, n), "pre", k * dt) for n, (k, ty, ix) in enumerate(spikes) if ty == 0 and ix == i]
        prev = None
        for _, kind, t in sorted(pre_events + post_events):
            if prev is not None and prev[0] != kind:
                t_post, t_pre = (t, prev[1]) if kind == "post" else (prev[1], t)
                w[i] = max(0.0, w[i] + M.F(t_post - t_pre, params))
            prev = (kind, t)
    return w


def synthetic(mean=lambda t: 1.3, sd=lambda t: 0.4, rate=lambda t: 12.0, n=200, runaway=None, m3=0.01):
    cps = []
    for j in range(1, n + 1):
        t = 100.0 * j
        cps.append({"t": t, "mean": mean(t), "sd": sd(t), "m3": m3, "zero": 0.02, "max": 4.0,
                    "spikes": int(round(rate(t) * 100))})
    return {"cp": cps, "runaway": runaway, "spikes": [], "end": None}


def ramp(base, total):
    """A quantity rising linearly so that the second window's mean exceeds the first's by the share `total`."""
    # windows' midpoints are 12,550 s and 17,550 s
    slope = base * total / 5000.0
    return lambda t: base + slope * (t - 12550.0)


class Window(unittest.TestCase):
    def test_values(self):
        p = dict(M.BASE, ap=0.01, am=0.02, tp=10.0, tn=30.0, d=3.0)
        self.assertEqual(M.F(3.0, p), -0.02)                      # the shift: synchrony within d depresses
        self.assertAlmostEqual(M.F(0.0, p), -0.02 * math.exp(-3 / 30), places=15)
        self.assertAlmostEqual(M.F(-10.0, p), -0.02 * math.exp(-13 / 30), places=15)
        self.assertAlmostEqual(M.F(3.5, p), 0.01 * math.exp(-0.05), places=15)
        self.assertAlmostEqual(M.F(13.0, p), 0.01 * math.exp(-1), places=15)
        q = dict(p, d=0.0)
        self.assertEqual(M.F(0.0, q), -0.02)
        self.assertGreater(M.F(1e-9, q), 0.0099)


class Pairing(unittest.TestCase):
    def test_walk_matches_the_plain_implementation(self):
        for seed, d in ((1, 1.5), (2, 0.0), (3, 3.0), (4, 2.0)):
            rng = random.Random(seed)
            p = small(d=d, T=0.8)
            steps = int(round(p["T"] * 1000 / p["dt"]))
            winit = [rng.uniform(4.0, 14.0) for _ in range(p["nex"])]
            spikes = M.replay_spikes(rng, p["nex"], p["nin"], 60.0, steps, p["dt"])
            posts, w = M.py_replay(p, winit, spikes, steps)
            self.assertGreater(len(posts), 5, seed)
            want = walk(p, winit, spikes, posts)
            self.assertLess(max(abs(a - b) for a, b in zip(w, want)), 1e-12, seed)
            self.assertTrue(any(abs(a - b) > 1e-6 for a, b in zip(w, winit)), seed)

    def hand_case(self):
        # synapse 1 (1 mV) fires at 1.0 and 2.0 ms; synapse 0 (400 mV) at 3.0 ms drives a burst of postsynaptic spikes
        # that ends well before synapse 1 fires again at 40 and 50 ms
        p = dict(M.BASE, nex=2, nin=0, d=1.5, T=0.06, cp=0.06, stop_rate=0, stop_mean=0, seed=1)
        spikes = [(10, 0, 1), (20, 0, 1), (30, 0, 0), (400, 0, 1), (500, 0, 1)]
        return p, [400.0, 1.0], spikes, int(round(p["T"] * 1000 / p["dt"]))

    def test_hand_case(self):
        p, winit, spikes, steps = self.hand_case()
        posts, w = M.py_replay(p, winit, spikes, steps)
        dt = p["dt"]
        self.assertGreaterEqual(len(posts), 2)
        self.assertLess(max(posts), 40.0)
        p1, plast = posts[0], posts[-1]
        # synapse 0: its one spike pairs with the first postsynaptic spike only
        self.assertAlmostEqual(w[0], 400.0 + M.F(p1 - 30 * dt, p), places=12)
        # synapse 1: the spike at 2 ms (not 1 ms) pairs with the first postsynaptic spike; the spike at 40 ms with the
        # burst's last; the spike at 50 ms with nothing
        self.assertAlmostEqual(w[1], 1.0 + M.F(p1 - 20 * dt, p) + M.F(plast - 400 * dt, p), places=12)
        # the reading set aside (every postsynaptic spike with the last presynaptic spike) would differ
        other = 1.0 + sum(M.F(tp - 20 * dt, p) for tp in posts) + M.F(plast - 400 * dt, p) + M.F(plast - 500 * dt, p)
        self.assertGreater(abs(other - w[1]), 1e-4)


class Program(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp()
        cls.exe = M.build(cls.work)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def run_c(self, params, winit, **kw):
        return M.c_run(self.exe, self.work, params, winit, **kw)

    def test_replay_agrees(self):
        for seed, d in ((11, 1.0), (12, 0.0), (13, 3.0)):
            rng = random.Random(seed)
            p = small(nex=30, nin=8, d=d, T=1.5, cp=1.5)
            steps = int(round(p["T"] * 1000 / p["dt"]))
            winit = [rng.uniform(3.0, 12.0) for _ in range(p["nex"])]
            spikes = M.replay_spikes(rng, p["nex"], p["nin"], 50.0, steps, p["dt"])
            rc = self.run_c(p, winit, mode="replay", spikes=spikes)
            ps, pw = M.py_replay(p, winit, spikes, steps)
            self.assertGreater(len(ps), 5, seed)
            self.assertEqual(len(ps), len(rc["spikes"]), seed)
            self.assertLess(max(abs(a - b) for a, b in zip(ps, rc["spikes"])), 1e-6, seed)
            self.assertLess(max(abs(a - b) for a, b in zip(pw, rc["w"])), 1e-9, seed)
            self.assertEqual(rc["end"]["spikes"], len(ps))

    def test_hand_case_in_c(self):
        p, winit, spikes, steps = Pairing().hand_case()
        rc = self.run_c(p, winit, mode="replay", spikes=spikes)
        ps, pw = M.py_replay(p, winit, spikes, steps)
        self.assertEqual(len(rc["spikes"]), len(ps))
        self.assertLess(max(abs(a - b) for a, b in zip(pw, rc["w"])), 1e-12)

    def test_free_mean(self):
        # firing and plasticity off: the mean of V is V_r + tau_s (N_ex r_ex w - N_in r_in w_in) = -51 mV here
        p = small(nex=100, nin=40, rex=20.0, rin=15.0, win=2.0, plastic=0, fire=0, T=500.0, cp=500.0, seed=77)
        r = self.run_c(p, [1.5] * 100)
        want = -60.0 + 0.005 * (100 * 20 * 1.5 - 40 * 15 * 2.0)
        self.assertAlmostEqual(want, -51.0)
        self.assertLess(abs(r["end"]["meanV"] - want), 0.01 * abs(want))

    def test_input_rates(self):
        p = small(nex=200, nin=50, rex=7.0, rin=13.0, plastic=0, fire=0, T=100.0, cp=100.0, seed=78)
        r = self.run_c(p, [1.0] * 200)
        self.assertLess(abs(r["end"]["in_ex"] / (200 * 100.0) - 7.0), 0.02 * 7.0)
        self.assertLess(abs(r["end"]["in_in"] / (50 * 100.0) - 13.0), 0.03 * 13.0)

    def test_checkpoints(self):
        rng = random.Random(21)
        winit = [rng.uniform(1.0, 6.0) for _ in range(20)]
        p = small(T=10.0, cp=1.0, seed=5)
        r = self.run_c(p, winit)
        self.assertEqual([c["t"] for c in r["cp"]], [float(j) for j in range(1, 11)])
        self.assertIsNone(r["runaway"])
        self.assertEqual(sum(c["spikes"] for c in r["cp"]), r["end"]["spikes"])
        last, w = r["cp"][-1], r["w"]
        m = sum(w) / len(w)
        self.assertAlmostEqual(last["mean"], m, places=9)
        self.assertAlmostEqual(last["sd"], math.sqrt(sum((x - m) ** 2 for x in w) / len(w)), places=9)
        self.assertAlmostEqual(last["max"], max(w), places=9)
        self.assertAlmostEqual(last["zero"], sum(1 for x in w if x == 0) / len(w), places=12)
        self.assertGreater(r["end"]["spikes"], 0)

    def test_determinism(self):
        winit = [3.0] * 20
        a = self.run_c(small(T=2.0, cp=1.0, seed=9), winit)
        b = self.run_c(small(T=2.0, cp=1.0, seed=9), winit)
        c = self.run_c(small(T=2.0, cp=1.0, seed=10), winit)
        self.assertEqual(a["w"], b["w"])
        self.assertEqual(a["cp"], b["cp"])
        self.assertNotEqual(a["w"], c["w"])

    def test_stop_on_mean(self):
        r = self.run_c(small(T=10.0, cp=1.0, stop_mean=0.5), [2.0] * 20)
        self.assertEqual(r["runaway"], 1.0)
        self.assertEqual(len(r["cp"]), 1)
        self.assertAlmostEqual(r["end"]["t"], 1.0)

    def test_stop_on_rate(self):
        r = self.run_c(small(T=10.0, cp=1.0, stop_rate=1.0), [10.0] * 20)
        self.assertEqual(r["runaway"], 1.0)
        self.assertGreater(r["cp"][0]["spikes"], 1)

    def test_bounds(self):
        # strong depression only: strengths fall to 0 and no lower
        lo = self.run_c(small(T=5.0, cp=1.0, ap=0.0, am=1.0), [6.0] * 20)
        self.assertGreaterEqual(min(lo["w"]), 0.0)
        self.assertTrue(any(x == 0.0 for x in lo["w"]))
        # an upper limit, when one is set, holds (the paper's shifted runs set none)
        hi = self.run_c(small(T=5.0, cp=1.0, ap=1.0, am=0.0, wmax=8.0), [6.0] * 20)
        self.assertLessEqual(max(hi["w"]), 8.0)
        self.assertTrue(any(x == 8.0 for x in hi["w"]))

    def test_refusals(self):
        def code(lines):
            path = os.path.join(self.work, "bad.txt")
            with open(path, "w") as fh:
                fh.write(lines)
            return subprocess.run([self.exe, "run", path], capture_output=True).returncode
        winit = os.path.join(self.work, "w1.txt")
        with open(winit, "w") as fh:
            fh.write("1\n")
        good = f"nex 1\nnin 0\ndt 0.1\nT 0.01\ncp 0.01\ntau_m 20\ntau_s 5\nwinit {winit}\n"
        self.assertEqual(code(good), 0)
        self.assertEqual(code(good + "colour 3\n"), 2)
        self.assertEqual(code(good.replace("tau_s 5", "tau_s 20")), 2)
        self.assertEqual(code(good.replace("nex 1", "nex 2")), 2)     # winit too short
        self.assertEqual(subprocess.run([self.exe, "walk", winit], capture_output=True).returncode, 2)


class Settling(unittest.TestCase):
    def test_flat_settles(self):
        ok, st = M.settled(synthetic())
        self.assertTrue(ok)
        for key in ("mean", "sd", "rate"):
            self.assertAlmostEqual(st["change"][key], 0.0, places=12)
        self.assertAlmostEqual(st["last"]["rate"], 12.0)
        self.assertAlmostEqual(st["last"]["skew"], 0.01 / 0.4 ** 3)

    def test_drift_in_each_quantity(self):
        for key in ("mean", "sd", "rate"):
            for total, want in ((0.04, True), (0.06, False)):
                base = {"mean": 1.3, "sd": 0.4, "rate": 12.0}[key]
                ok, st = M.settled(synthetic(**{key: ramp(base, total)}))
                self.assertEqual(ok, want, (key, total))
                self.assertAlmostEqual(st["change"][key], total, delta=0.002)

    def test_runaway_and_missing_windows(self):
        self.assertEqual(M.settled(synthetic(runaway=900.0)), (False, None))
        self.assertEqual(M.settled(synthetic(n=180)), (False, None))
        self.assertIsNone(M.window_stats(synthetic(n=180), 15000.0, 20000.0))
        self.assertAlmostEqual(M.window_stats(synthetic(), 10000.0, 15000.0)["mean"], 1.3, places=12)


class Conditions(unittest.TestCase):
    def runs(self, **kw):
        r = {"S1": synthetic(), "S2": synthetic(mean=lambda t: 1.33, sd=lambda t: 0.42), "U": synthetic(runaway=4100.0)}
        r.update(kw)
        return r

    def test_all_hold(self):
        cond, s1, s2, u = M.conditions(self.runs())
        self.assertEqual(list(cond.values()), [True, True, True])
        self.assertIsNone(u)

    def test_each_fails(self):
        cases = {
            # S1's mean rises 8%, to 1.404 in its last window, which S2 is compared with
            "S1 drifts": ({"S1": synthetic(mean=ramp(1.3, 0.08)), "S2": synthetic(mean=lambda t: 1.40)},
                          [False, True, True]),
            "S1 drifts, S2 left behind": ({"S1": synthetic(mean=ramp(1.3, 0.08))}, [False, False, True]),
            "S2 elsewhere": ({"S2": synthetic(mean=lambda t: 1.40)}, [True, False, True]),
            "S2 wider": ({"S2": synthetic(sd=lambda t: 0.46)}, [True, False, True]),
            "S2 drifts": ({"S2": synthetic(rate=ramp(12.0, 0.07))}, [True, False, True]),
            "U settles": ({"U": synthetic(mean=lambda t: 3.0)}, [True, True, False]),
            "S1 runs away": ({"S1": synthetic(runaway=300.0)}, [False, False, True]),
        }
        for name, (kw, want) in cases.items():
            cond, *_ = M.conditions(self.runs(**kw))
            self.assertEqual(list(cond.values()), want, name)
        # a drifting U fails to settle, as the test requires
        cond, *_ = M.conditions(self.runs(U=synthetic(mean=ramp(3.0, 0.2))))
        self.assertTrue(cond["C3 d = 0 does not settle"])


class Run(unittest.TestCase):
    def test_refused_seed(self):
        with self.assertRaises(M.Refused):
            M.run("nothex", results=os.path.join(HERE, "nonexistent"))

    def test_work_inside_results(self):
        # the engine is built and run inside the results directory (a sandbox's /tmp may forbid execution), and the
        # working directory is removed afterwards
        seen = []
        real = M.assess

        def fake(seed, work):
            seen.append(work)
            return {"test_passed": 0}, {}
        results = tempfile.mkdtemp()
        try:
            M.assess = fake
            M.run(SEED, results=results)
            self.assertEqual(os.path.dirname(seen[0]), results)
            self.assertFalse(os.path.exists(seen[0]))
            self.assertTrue(os.path.exists(os.path.join(results, "outputs.json")))
        finally:
            M.assess = real
            shutil.rmtree(results, ignore_errors=True)

    def test_test_length(self):
        self.assertLessEqual(len(M.TEST), 600)

    def test_streams(self):
        a, b = M.Stream(SEED, "x"), M.Stream(SEED, "x")
        xs = [a.uniform(1.0, 5.0) for _ in range(200)]
        self.assertEqual(xs, [b.uniform(1.0, 5.0) for _ in range(200)])
        self.assertTrue(all(1.0 <= x < 5.0 for x in xs))
        self.assertNotEqual(M.seed64(SEED, "S1"), M.seed64(SEED, "S2"))
        self.assertEqual(M.seed64(SEED, "S1"), M.seed64(SEED, "S1"))
        self.assertLess(M.seed64(SEED, "U"), 2 ** 64)

    def test_runs_as_rule_2(self):
        self.assertEqual(M.RUNS["S1"], (2.0, 1.0, 5.0))
        self.assertEqual(M.RUNS["S2"], (2.0, 5.0, 9.0))
        self.assertEqual(M.RUNS["U"], (0.0, 1.0, 5.0))
        self.assertEqual((M.T_RUN, M.WINDOWS, M.SETTLE), (20000.0, ((10000.0, 15000.0), (15000.0, 20000.0)), 0.05))


if __name__ == "__main__":
    unittest.main()
