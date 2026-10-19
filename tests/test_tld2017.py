"""Tang, Lin & Davies's spiking LCA (snn/tld2017.py): the first-passage solver, the event-driven network, its
50-digit and fixed-step counterparts, the exact CLASSO certificate, the homotopy, the instance generator, the
figures' readers and the e-print's reader, on inputs other than the claim's own case: the paper's 3-neuron example
is never simulated here and no instance is drawn under a registered seed.

Run with: python3 -m unittest tests.test_tld2017 (in the pinned scipy-notebook image)
"""

import gzip
import hashlib
import importlib.util
import io
import math
import os
import random
import sys
import tarfile
import tempfile
import unittest
import zlib
from fractions import Fraction

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("snn_tld2017", os.path.join(HERE, "..", "snn", "tld2017.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)

TEST_SEED = "5" * 64


def g_of(v, c, d, x, thr=1.0):
    return v + c * x + d * (1 - math.exp(-x)) - thr


class FirstPassage(unittest.TestCase):
    def test_root_is_the_first_crossing(self):
        rng = random.Random(1)
        for _ in range(300):
            v = rng.uniform(-2.0, 0.99)
            c = rng.uniform(0.01, 3.0)
            d = rng.uniform(-3.0, 0.0)
            x = M.first_passage(v, c, d)
            self.assertLess(abs(g_of(v, c, d, x)), 1e-12)
            for k in range(200):
                y = x * k / 200
                self.assertLess(g_of(v, c, d, y), 1e-12)

    def test_edges(self):
        self.assertEqual(M.first_passage(1.0, 1.0, -1.0), 0.0)
        self.assertEqual(M.first_passage(0.25, 2.0, 0.0), 0.375)


class SingleNeuron(unittest.TestCase):
    def test_regular_spikes_and_windows(self):
        r = M.slca_exact([1.5], np.zeros((1, 1)), 0.5, 10.75, windows=((5.5, 10.25),), astar=[1.0],
                         record_until=11.0)
        self.assertEqual(int(r["count"][0]), 10)
        self.assertEqual([t for _, t in r["spikes"]], [float(n) for n in range(1, 11)])
        self.assertAlmostEqual(r["E"][0], 1.0 / 6.0, places=12)
        self.assertLess(r["identity"], 1e-12)
        self.assertEqual(r["root_res"], 0.0)
        self.assertEqual(r["min_isi"], 1.0)

    def test_refuses_a_silent_neuron(self):
        with self.assertRaises(ValueError):
            M.slca_exact([0.5, 1.0], np.zeros((2, 2)), 0.5, 1.0)


def small_net(seed, n=3):
    rng = np.random.default_rng(seed)
    atoms = np.abs(rng.standard_normal((n, n + 1)))
    atoms /= np.linalg.norm(atoms, axis=1, keepdims=True)
    s = np.abs(rng.standard_normal(n + 1)) * 2
    b = atoms @ s
    W = atoms @ atoms.T
    np.fill_diagonal(W, 0.0)
    lam = 0.2 * float(b.min())
    return b, W, lam


class AgainstOtherSimulations(unittest.TestCase):
    def test_mpmath_and_fine_steps(self):
        for seed in (11, 12):
            b, W, lam = small_net(seed)
            ex = M.slca_exact(b, W, lam, 4.0, record_until=4.0)
            mp = M.slca_mp(list(b), W.tolist(), lam, 4.0)
            self.assertEqual([k for k, _ in mp], [k for k, _ in ex["spikes"]])
            self.assertLess(max(abs(a[1] - c[1]) for a, c in zip(mp, ex["spikes"])), 1e-9)
            fine = M.slca_discrete(b, W, lam, 1e-5, 4.0, record_until=4.0)
            self.assertEqual([k for k, _ in fine["spikes"]], [k for k, _ in ex["spikes"]])
            self.assertLess(max(abs(a[1] - c[1]) for a, c in zip(fine["spikes"], ex["spikes"])), 1e-3)

    def test_windows_against_dense_evaluation(self):
        b, W, lam = small_net(21)
        astar = np.array([0.3, 0.1, 0.5])
        r = M.slca_exact(b, W, lam, 60.0, windows=((20.3, 59.7),), astar=astar, record_until=60.0)
        spikes = r["spikes"]
        best = 0.0
        times = [20.3, 59.7] + [t for _, t in spikes if 20.3 <= t <= 59.7]
        for i in range(3):
            own = sorted(t for k, t in spikes if k == i)
            for t in times:
                n_right = sum(1 for u in own if u <= t)
                n_left = sum(1 for u in own if u < t)
                cands = [abs(n_right / t - astar[i])]
                if t in own:
                    cands.append(abs(n_left / t - astar[i]))
                best = max(best, max(cands))
        grid = np.linspace(20.3, 59.7, 20001)
        dense = max(abs(sum(1 for u in sorted(t for k, t in spikes if k == i) if u <= t) / t - astar[i])
                    for i in range(3) for t in grid[::50])
        self.assertAlmostEqual(r["E"][0], best, places=12)
        self.assertGreaterEqual(r["E"][0] + 1e-12, dense)

    def test_snapshot(self):
        b, W, lam = small_net(31)
        r = M.slca_exact(b, W, lam, 30.0, snapshot=12.5, record_until=30.0)
        want = [sum(1 for k, t in r["spikes"] if k == i and t < 12.5) for i in range(3)]
        self.assertEqual([int(x) for x in r["count_snap"]], want)


class Discrete(unittest.TestCase):
    def test_single_neuron_whole_steps(self):
        q = M.slca_discrete([1.5], np.zeros((1, 1)), 0.5, 0.25, 10.0, t0=5.0, record_until=10.0)
        self.assertEqual(int(q["count"][0]), 10)
        self.assertEqual(int(q["count0"][0]), 5)
        self.assertEqual([t for _, t in q["spikes"]][:3], [1.0, 2.0, 3.0])


class ALCA(unittest.TestCase):
    def test_closed_form_without_coupling(self):
        b, lam, u0 = 1.2, 0.3, 0.0
        u, z, smp = M.alca_rk4([b], np.zeros((1, 1)), lam, [u0], 3.0, 1e-3, sample_times=(1.0, 3.0))
        t_c = -math.log((b - lam) / (b - u0))       # u(t_c) = lam
        for t in (1.0, 3.0):
            want = (b - lam) * (t - t_c) - (b - u0) * (math.exp(-t_c) - math.exp(-t))
            self.assertAlmostEqual(float(smp[t][0]), want, places=6)
        self.assertAlmostEqual(float(u[0]), b + (u0 - b) * math.exp(-3.0), places=10)


def random_classo(seed, n=6, m=4):
    rng = random.Random(seed)
    atoms = [[Fraction(rng.randint(0, 9), 10) for _ in range(m)] for _ in range(n)]
    s = [Fraction(rng.randint(0, 20), 10) for _ in range(m)]
    G = [[sum(a[k] * c[k] for k in range(m)) for c in atoms] for a in atoms]
    b = [sum(a[k] * s[k] for k in range(m)) for a in atoms]
    lam = Fraction(rng.randint(1, 10), 20)
    return G, b, lam


class Certificate(unittest.TestCase):
    def test_unique_support_and_an_independent_solver(self):
        done = 0
        for seed in range(40):
            G, b, lam = random_classo(seed)
            if any(G[i][i] == 0 for i in range(len(b))):
                continue
            passing = M.enumerate_supports(lambda j, i: G[j][i], b, lam)
            if len(passing) != 1:
                continue
            S, cert = passing[0]
            a = np.array([float(cert["a"].get(i, 0)) for i in range(len(b))])
            lb = M.lbfgs_solution(np.array([[float(x) for x in r] for r in G]), np.array([float(x) for x in b]),
                                  float(lam))
            self.assertLess(float(np.max(np.abs(lb - a))), 1e-6)
            if S:
                bad = sorted(set(range(len(b))) - set(S))[:1] + S[1:]
                self.assertFalse(M.certify(lambda j, i: G[j][i], b, lam, bad)["ok"] and bad != S)
            done += 1
        self.assertGreater(done, 10)

    def test_exact_dot(self):
        rng = np.random.default_rng(3)
        x = rng.random(50) * 1e-3
        y = rng.random(50)
        xi, kx = M.scaled_ints(x)
        yi, ky = M.scaled_ints(y)
        self.assertEqual(M.exact_dot(xi, kx, yi, ky), sum(Fraction(float(a)) * Fraction(float(c)) for a, c in zip(x, y)))

    def test_positive_definite(self):
        self.assertTrue(M.positive_definite([[2, 1], [1, 2]]))
        self.assertFalse(M.positive_definite([[1, 2], [2, 1]]))


class Instances(unittest.TestCase):
    def test_small_draws(self):
        saved = (M.PIXELS, M.ATOMS, M.SUPPORT)
        try:
            M.PIXELS, M.ATOMS, M.SUPPORT = 8, 30, 3
            for k in range(3):
                I = M.draw_instance(TEST_SEED, k)
                Phi = I["Phi"]
                self.assertEqual(Phi.shape, (16, 30))
                self.assertTrue(np.all(Phi >= 0))
                self.assertTrue(np.all(np.abs(np.sum(Phi * Phi, axis=0) - 1) < 1e-14))
                self.assertTrue(np.all(I["s"] >= 0))
                self.assertEqual(len(I["S"]), 3)
                self.assertTrue(np.all(I["W"] >= 0) and np.all(np.diag(I["W"]) == 0) and np.array_equal(I["W"], I["W"].T))
                self.assertEqual(I["cand"], [i for i in range(30) if I["b"][i] > I["lam"]])
                self.assertTrue(set(I["S"]) <= set(I["cand"]))
                self.assertTrue(all(I["astar"][i] > 0 for i in I["S"]))
                lb = M.lbfgs_solution(I["G"], I["b"], I["lam"])
                self.assertLess(float(np.max(np.abs(lb - I["astar"]))), 1e-6)
        finally:
            M.PIXELS, M.ATOMS, M.SUPPORT = saved


def synthetic_pdf(stream):
    raw = zlib.compress(stream.encode("latin-1"))
    return (b"%PDF-1.4\n1 0 obj\n<< /Length " + str(len(raw)).encode() + b" /Filter /FlateDecode >>\nstream\n" + raw
            + b"\nendstream\nendobj\n")


class Figures(unittest.TestCase):
    def test_raster_reader(self):
        parts = []
        for y, lab in ((141.301, "01"), (154.352, "02"), (167.398, "03")):
            parts.append(f"q 1 0 0 -1 0 324 cm 38.102 {y} m 42.398 {y} l S Q BT ({lab})Tj ET")
        for x, lab in zip(np.linspace(38.102, 342.602, 7), (" 0", " 2", " 4", " 6", " 8", " 10", " 12")):
            parts.append(f"q 1 0 0 -1 0 324 cm {x:.3f} 180.449 m {x:.3f} 176.148 l S Q BT ({lab})Tj ET")
        want = {1: [1.0, 5.5], 2: [3.25], 3: [0.5, 11.0]}
        rows = {1: 141.301, 2: 154.352, 3: 167.398}
        for n, ts in want.items():
            for t in ts:
                x = 38.102 + t / 12 * (342.602 - 38.102)
                parts.append(f"q 1 0 0 -1 0 324 cm {x - 3:.3f} {rows[n]} m {x + 3:.3f} {rows[n]} l S Q")
                parts.append(f"q 1 0 0 -1 0 324 cm {x:.3f}\n{rows[n] - 3:.3f} m {x:.3f} {rows[n] + 3:.3f} l S Q")
        got = M.read_raster(synthetic_pdf("\n".join(parts)))
        for n in want:
            self.assertEqual(len(got[n]), len(want[n]))
            for a, c in zip(got[n], want[n]):
                self.assertLess(abs(a - c), 2e-4)

    def test_count_reader(self):
        parts = []
        for x, lab in zip(np.linspace(44.051, 342.602, 7), (" 0", " 2", " 4", " 6", " 8", " 10", " 12")):
            parts.append(f"q 1 0 0 -1 0 324 cm {x:.3f} 195.898 m {x:.3f} 191.602 l S Q BT ({lab})Tj ET")
        for y, lab in zip(np.linspace(195.898, 106.352, 6), (" 0", " 3", " 6", " 9", " 12", " 15")):
            parts.append(f"q 1 0 0 -1 0 324 cm 44.051 {y:.3f} m 48.352 {y:.3f} l S Q BT ({lab})Tj ET")
        colours = {1: "0.117647 0.564706 1", 2: "0.235294 0.701961 0.443137", 3: "0.862745 0.0784314 0.235294"}
        slopes = {1: 0.5, 2: 0.1, 3: 1.0}
        for n in (1, 2, 3):
            pts = []
            for t in np.linspace(0, 12, 25):
                x = 44.051 + t / 12 * (342.602 - 44.051)
                y = 195.898 - slopes[n] * t / 15 * (195.898 - 106.352)
                pts.append(f"{x:.3f} {y:.3f} " + ("m" if t == 0 else "l"))
            parts.append(f"{colours[n]} RG [ 2.5 4 2.5 4] 0 d q 1 0 0 -1 0 324 cm " + " ".join(pts) + " S Q")
        parts.append("0 0 0 RG [] 0.0 d q 1 0 0 -1 0 324 cm 1 1 m 2 1 l S Q")
        got = M.read_count_curves(synthetic_pdf("\n".join(parts)))
        for n in (1, 2, 3):
            for t in (1, 6, 12):
                self.assertLess(abs(M.curve_at(got[n], t) - slopes[n] * t), 2e-3)


def fake_eprint(texts):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for name, data in texts.items():
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            tf.addfile(ti, io.BytesIO(data))
    return gzip.compress(buf.getvalue())


class Source(unittest.TestCase):
    def test_refusals_and_parsing(self):
        texts = {fname: b"x" for fname in M.FILES.values()}
        for key, strings in M.PRINTED.items():
            texts[M.FILES[key]] = ("\n".join(strings)).encode()
        ex = (r"\subsection{Illustration of SNN dynamics} \begin{equation*} \vvs = \begin{bmatrix} 1\\ 2\\ 0.5 "
              r"\end{bmatrix} ,\quad \Phi = [\vvphi_1 \, \vvphi_2 \, \vvphi_3] = \begin{bmatrix} 1 & 0 & 0.6 \\ 0 & 1 "
              r"& 0.8 \\ 0 & 0 & 0 \end{bmatrix} ,\quad \lambda = 0.25. \end{equation*}")
        texts[M.FILES["practice"]] = ("\n".join(M.PRINTED["practice"]) + "\n" + ex).encode()
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.tar.gz")
            blob = fake_eprint(texts)
            with open(p, "wb") as fh:
                fh.write(blob)
            with self.assertRaises(M.Refused):
                M.open_eprint(p)                                      # wrong hash
            saved = M.EPRINT
            try:
                M.EPRINT = ("x.tar.gz", hashlib.sha256(blob).hexdigest(), len(blob))
                files = M.open_eprint(p)
                self.assertEqual(M.check_printed(files), sum(len(v) for v in M.PRINTED.values()))
                s, atoms, lam = M.parse_example(files["practice"].decode())
                self.assertEqual(s, [1, 2, Fraction(1, 2)])
                self.assertEqual(atoms[2], [Fraction(3, 5), Fraction(4, 5), 0])
                self.assertEqual(lam, Fraction(1, 4))
                self.assertEqual(M.parse_printed_solution(files["fig3"].decode()), M.PRINTED_SOLUTION)
                texts[M.FILES["snn"]] = b"nothing printed"
                blob2 = fake_eprint(texts)
                with open(p, "wb") as fh:
                    fh.write(blob2)
                M.EPRINT = ("x.tar.gz", hashlib.sha256(blob2).hexdigest(), len(blob2))
                with self.assertRaises(M.Refused):
                    M.check_printed(M.open_eprint(p))                 # a string is missing
            finally:
                M.EPRINT = saved


class ReadingR3(unittest.TestCase):
    def test_other_integer_atoms(self):
        saved = M.INTEGER_ATOMS
        try:
            M.INTEGER_ATOMS = ((1, 0, 0), (0, 1, 0), (1, 1, 0))
            s = [Fraction(1), Fraction(2), Fraction(0)]
            passing, rounds = M.r3_problem(s, Fraction(1, 10))
            self.assertEqual(len(passing), 1)
            atoms = np.array([[1, 0, 0], [0, 1, 0], [1 / math.sqrt(2), 1 / math.sqrt(2), 0]])
            G = atoms @ atoms.T
            b = atoms @ np.array([1.0, 2.0, 0.0])
            lb = M.lbfgs_solution(G, b, 0.1)
            self.assertLess(max(abs(float(x) - y) for x, y in zip(passing[0][1], lb)), 1e-7)
            self.assertLess(abs(float(rounds[6]) - 1 / math.sqrt(2)), 1e-15)
        finally:
            M.INTEGER_ATOMS = saved


class Comparisons(unittest.TestCase):
    def test_cut_or_round(self):
        self.assertTrue(M.cut_or_round(Fraction(6849, 10000), "0.684"))
        self.assertTrue(M.cut_or_round(Fraction(6849, 10000), "0.685"))
        self.assertFalse(M.cut_or_round(Fraction(6849, 10000), "0.683"))
        self.assertTrue(M.cut_or_round(Fraction(0), "0"))
        self.assertFalse(M.cut_or_round(Fraction(1, 10), "0"))
        self.assertFalse(M.cut_or_round(Fraction(1, 100000), "0"))
        self.assertTrue(M.cut_or_round(Fraction(12175, 10000), "1.217"))
        self.assertTrue(M.cut_or_round(Fraction(12165, 10000), "1.217"))


if __name__ == "__main__":
    unittest.main()
