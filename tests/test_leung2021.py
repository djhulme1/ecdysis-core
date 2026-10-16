"""Leung et al. 2021 (iit/leung2021.py, iit/iis.c): the small-phi engine against PyPhi 0.8.1's own test answer and
against iit/engine.py, its earth mover's distances against independent solutions, and the pipeline (binarisation,
states, TPMs, weights, sets, t-tests) on synthetic inputs; the data are never read here.

Run with: python3 -m unittest tests.test_leung2021 (in the pinned scipy-notebook image)
"""

import importlib.util
import itertools
import math
import os
import random
import tempfile
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("iit_leung2021", os.path.join(HERE, "..", "iit", "leung2021.py"))
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)
_espec = importlib.util.spec_from_file_location("iit_engine_t", os.path.join(HERE, "..", "iit", "engine.py"))
E = importlib.util.module_from_spec(_espec)
_espec.loader.exec_module(E)

_TMP = tempfile.mkdtemp(prefix="leung2021-tests-")
LIB = L.build(_TMP)
FLOW = os.path.join(_TMP, "libflow.so")
os.system(f"gcc -O2 -shared -fPIC -o {FLOW} {os.path.join(HERE, '..', 'iit', 'flow.c')} -lm")
ENG = L.IIS(LIB)


def mask(mech):
    return sum(1 << i for i in mech)


class PyPhi081(unittest.TestCase):
    def test_basic_network_standard_answer(self):
        """test_big_phi.py's standard_answer: the basic network (complete graph) in state (1, 0, 0)."""
        tpm = [[0, 0, 0], [0, 0, 1], [1, 0, 1], [1, 0, 0], [1, 1, 0], [1, 1, 1], [1, 1, 1], [1, 1, 0]]
        phi, _, _ = ENG.phis(tpm)
        want = {(1,): 0.25, (2,): 0.5, (0, 1): 0.333333, (0, 1, 2): 0.5}
        s = 1
        for m in range(1, 8):
            mech = tuple(i for i in range(3) if (m >> i) & 1)
            self.assertEqual(phi[m - 1][s], want.get(mech, 0.0), mech)


class AgainstEngine(unittest.TestCase):
    def check(self, tpm):
        phi, pc, pe = ENG.phis(tpm)
        flow = E.Flow(FLOW, 0)
        net = E.Network(tpm)
        n = len(tpm[0])
        for s in range(2 ** n):
            sub = E.Subsystem(net, tuple((s >> i) & 1 for i in range(n)), tuple(range(n)), cache={})
            for m in range(1, 2 ** n):
                mech = tuple(i for i in range(n) if (m >> i) & 1)
                c, _ = sub.mice(flow, E.CAUSE, mech)
                e, _ = sub.mice(flow, E.EFFECT, mech)
                self.assertEqual(pc[m - 1][s], c[0])
                self.assertEqual(pe[m - 1][s], e[0])
                self.assertEqual(phi[m - 1][s], min(c[0], e[0]))

    def test_random_two_and_three_nodes(self):
        rng = random.Random(11)
        for n in (2, 3, 3, 3):
            self.check([[rng.random() for _ in range(n)] for _ in range(2 ** n)])

    def test_random_four_nodes(self):
        rng = random.Random(12)
        self.check([[rng.uniform(0.1, 0.9) for _ in range(4)] for _ in range(16)])

    def test_deterministic_four_nodes(self):
        rng = random.Random(13)
        self.check([[rng.randint(0, 1) for _ in range(4)] for _ in range(16)])


class Structure(unittest.TestCase):
    def test_constant_rows_have_no_phi(self):
        row = [0.3, 0.6, 0.8, 0.45]
        phi, pc, pe = ENG.phis([row] * 16)
        self.assertEqual(max(max(r) for r in phi), 0.0)
        self.assertEqual(max(max(r) for r in pc), 0.0)

    def test_self_only_nodes(self):
        rng = random.Random(4)
        own = [(rng.uniform(0.1, 0.4), rng.uniform(0.6, 0.9)) for _ in range(4)]
        tpm = [[own[j][(s >> j) & 1] for j in range(4)] for s in range(16)]
        phi, _, _ = ENG.phis(tpm)
        for m, k in L.mechanisms():
            for s in range(16):
                if k > 1:
                    self.assertEqual(phi[m - 1][s], 0.0)
                else:
                    self.assertGreater(phi[m - 1][s], 0.0)

    def test_phi_depends_on_the_mechanism_state_only(self):
        rng = random.Random(5)
        phi, _, _ = ENG.phis([[rng.random() for _ in range(4)] for _ in range(16)])
        for m in range(1, 16):
            for s in range(16):
                self.assertEqual(phi[m - 1][s], phi[m - 1][s & m])


class Distances(unittest.TestCase):
    def test_one_and_two_nodes_in_closed_form(self):
        rng = random.Random(6)
        for _ in range(200):
            p = [rng.random() for _ in range(2)]
            q = [rng.random() for _ in range(2)]
            p = [v / sum(p) for v in p]
            q = [v / sum(q) for v in q]
            self.assertAlmostEqual(ENG.emd(1, p, q), abs(p[0] - q[0]), places=12)
            p = [rng.random() for _ in range(4)]
            q = [rng.random() for _ in range(4)]
            p = [v / sum(p) for v in p]
            q = [v / sum(q) for v in q]
            # the 4-cycle 00, 01, 11, 10 (indices 0, 1, 3, 2): flows F_i - c, cost minimised at the median of F
            order = [0, 1, 3, 2]
            F, acc = [], 0.0
            for i in order:
                acc += p[i] - q[i]
                F.append(acc)
            c = sorted(F)[1]
            want = min(sum(abs(f - x) for f in F) for x in (sorted(F)[1], sorted(F)[2], c))
            self.assertAlmostEqual(ENG.emd(2, p, q), want, places=12)

    def test_three_and_four_nodes_by_linear_programming(self):
        from scipy.optimize import linprog
        rng = random.Random(7)
        for m in (3, 3, 4, 4):
            k = 2 ** m
            p = np.array([rng.random() for _ in range(k)])
            q = np.array([rng.random() for _ in range(k)])
            p, q = p / p.sum(), q / q.sum()
            C = np.array([[bin(i ^ j).count("1") for j in range(k)] for i in range(k)], dtype=float)
            A = []
            b = []
            for i in range(k):
                row = np.zeros((k, k)); row[i, :] = 1; A.append(row.ravel()); b.append(p[i])
            for j in range(k):
                row = np.zeros((k, k)); row[:, j] = 1; A.append(row.ravel()); b.append(q[j])
            res = linprog(C.ravel(), A_eq=np.array(A), b_eq=np.array(b), bounds=(0, None), method="highs")
            self.assertAlmostEqual(ENG.emd(m, list(p), list(q)), res.fun, places=9)

    def test_effect_distance_of_products(self):
        rng = random.Random(8)
        ok, worst = L.control_effect(ENG, rng)
        self.assertTrue(ok, worst)


class Pipeline(unittest.TestCase):
    def test_binarise_at_the_median(self):
        x = np.array([[3.0, 1.0], [1.0, 2.0], [2.0, 2.0], [4.0, 5.0]])
        b, med = L.binarise(x)
        self.assertEqual(list(med), [2.5, 2.0])
        self.assertEqual(b[:, 0].tolist(), [1, 0, 0, 1])
        self.assertEqual(b[:, 1].tolist(), [0, 0, 0, 1])      # ties at the median are off

    def test_states_are_little_endian(self):
        b = np.array([[1, 0, 0, 1, 1], [0, 1, 1, 0, 0]])
        self.assertEqual(L.states_of(b, (0, 3, 4)).tolist(), [1 + 2 + 4, 0])
        self.assertEqual(L.states_of(b, (1, 2)).tolist(), [0, 3])

    def test_tpm_counts_transitions_tau_apart(self):
        # two channels; the second is the first delayed by tau, so P(B on at t+tau | A at t) is 0 or 1
        rng = random.Random(9)
        T, tau = 400, 4
        a = [rng.randint(0, 1) for _ in range(T)]
        bb = [0] * tau + a[:-tau]
        b = np.array([a, bb]).T
        tpm, w, w_all, unseen = L.tpm_of(b, (0, 1), tau=tau)
        self.assertEqual(int(w.sum()), T - tau)
        self.assertEqual(int(w_all.sum()), T)
        for s in range(4):
            if w[s] > 0:
                self.assertEqual(tpm[s][1], float(s & 1))
        # hand count of one row
        cur = [a[t] | (bb[t] << 1) for t in range(T - tau)]
        rows = [t for t in range(T - tau) if cur[t] == 3]
        if rows:
            self.assertAlmostEqual(tpm[3][0], sum(a[t + tau] for t in rows) / len(rows))

    def test_unseen_rows_are_half(self):
        b = np.array([[0, 0]] * 10 + [[1, 1]] * 10)
        tpm, w, _, unseen = L.tpm_of(b, (0, 1), tau=1)
        self.assertEqual(unseen, 2)
        self.assertEqual(tpm[1].tolist(), [0.5, 0.5])
        self.assertEqual(tpm[2].tolist(), [0.5, 0.5])

    def test_reachable(self):
        tpm = np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 0.5], [0.0, 1.0]])
        self.assertTrue(L.reachable(tpm, 0))
        self.assertTrue(L.reachable(tpm, 3))
        tpm2 = np.array([[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 1.0]])
        self.assertFalse(L.reachable(tpm2, 1))

    def test_weighted(self):
        phi = [[1.0, 0.0, 2.0, 0.0]]
        self.assertAlmostEqual(L.weighted(phi, np.array([1, 0, 3, 0]))[0], 7 / 4)

    def test_sets_drawn_by_seed(self):
        allsets = list(itertools.combinations(range(15), 4))
        self.assertEqual(len(allsets), 1365)
        a = sorted(L.seeded("ab" * 32, "sets").sample(range(1365), L.SETS))
        b = sorted(L.seeded("ab" * 32, "sets").sample(range(1365), L.SETS))
        c = sorted(L.seeded("cd" * 32, "sets").sample(range(1365), L.SETS))
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertEqual(len(set(a)), L.SETS)

    def test_mechanism_sizes(self):
        sizes = [k for _, k in L.mechanisms()]
        self.assertEqual([sizes.count(k) for k in (1, 2, 3, 4)], [4, 6, 4, 1])


class Statistics(unittest.TestCase):
    def test_paired_t_against_scipy(self):
        rng = random.Random(10)
        for _ in range(20):
            x = [rng.gauss(1.0, 1.0) for _ in range(13)]
            y = [v - rng.gauss(0.3, 0.5) for v in x]
            t, p, df = L.paired_t(x, y)
            st, sp = L.scipy_paired(x, y)
            self.assertAlmostEqual(t, st, places=9)
            self.assertAlmostEqual(p, sp, places=9)
            self.assertEqual(df, 12)

    def test_betainc_against_scipy(self):
        from scipy import special
        for a, b, x in ((6.0, 0.5, 0.3), (6.0, 0.5, 0.97), (2.5, 3.5, 0.5), (0.5, 0.5, 0.01)):
            self.assertAlmostEqual(L.betainc(a, b, x), float(special.betainc(a, b, x)), places=12)


class Source(unittest.TestCase):
    def test_constants(self):
        self.assertLessEqual(len(L.TEST), 600)
        self.assertEqual(len(set(L.OUTPUTS)), len(L.OUTPUTS))
        self.assertLessEqual(len(L.OUTPUTS), 64)
        self.assertEqual(L.SHAPE, (2250, 15, 8, 13, 2))
        self.assertEqual(L.TAU, 4)

    def test_refusal(self):
        with self.assertRaises(L.Refused):
            L.read(tempfile.mkdtemp(prefix="leung2021-none-"))


if __name__ == "__main__":
    unittest.main()
