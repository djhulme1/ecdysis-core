"""Engelken et al.'s check (snn/engelken.py): the autocovariance against its definition; both e-folding fits on exact
exponentials and at their edges; the kernel's estimate of a known response; the fall by e; the phase rule, which no
phase of the eigenvector moves; rule 3 against numpy's full eig for a complex and for a real rightmost eigenvalue; the
rate network's exact response against a fine Euler integration; the pulsed simulator against snn/ostojic.py's with
zero perturbations, and its projection against its own spikes; the telegraph process's correlation; the verdict at
and either side of each clause; the mean field's slopes at J = 0.45 mV; and, with the claim's zip at inputs/ (or
ENGELKEN_INPUTS), its reading and each refusal.

Run with: python3 -m unittest discover -s tests
"""

import math
import os
import shutil
import sys
import tempfile
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from snn import engelken as E  # noqa: E402
from snn import ostojic as O  # noqa: E402

INPUTS = os.environ.get("ENGELKEN_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = os.path.isfile(os.path.join(INPUTS, E.ZIP))


class Autocorrelation(unittest.TestCase):
    def test_autocovariance_is_its_definition(self):
        rng = np.random.default_rng(1)
        x = rng.poisson(0.7, (5, 300)).astype(np.int64)
        c = E.autocovariance(x, 10)
        for k in range(11):
            rows = []
            for r in x.astype(float):
                m = r.mean()
                rows.append(((r[: r.size - k] - m) * (r[k:] - m)).sum() / (r.size - k))
            self.assertAlmostEqual(c[k], float(np.mean(rows)), places=12)

    def test_efold_from_log(self):
        k = np.arange(61)
        self.assertAlmostEqual(E.efold_from_log(3.0 * np.exp(-k / 20.0)), 20.0, places=9)
        c = 3.0 * np.exp(-k / 20.0)
        c[25] = -1e-9
        self.assertIsNone(E.efold_from_log(c))
        c[25] = 0.0
        self.assertIsNone(E.efold_from_log(c))
        self.assertIsNone(E.efold_from_log(np.exp(k / 50.0)))
        self.assertAlmostEqual(E.efold_from_log(np.exp(-k / 9.0) + 0 * k), 9.0, places=9)

    def test_counts_per_ms(self):
        st = np.array([0, 99, 100, 250, 999_999, 5], dtype=np.int64)
        si = np.array([3, 3, 7, 3, 7, 9], dtype=np.int64)
        x = E.counts_per_ms(st, si, np.array([7, 3]), 10_000)
        self.assertEqual(x.shape, (2, 10_000))
        self.assertEqual((x[1, 0], x[1, 1], x[1, 2], x[0, 1], x[0, 9999]), (2, 0, 1, 1, 1))
        self.assertEqual(int(x.sum()), 5)

    def test_telegraph_correlation(self):
        s = E.telegraph(np.random.default_rng(5), 400, 20_000, 25.0)
        self.assertTrue(set(np.unique(s)) <= {0.0, 1.0})
        a = s - s.mean()
        r = float((a[:, :-25] * a[:, 25:]).mean() / (a * a).mean())
        self.assertAlmostEqual(r, math.exp(-1), delta=0.02)


class Perturbation(unittest.TestCase):
    def test_efold_fit_on_its_grid(self):
        lags = np.arange(E.LAGS)
        h = 0.03 * np.exp(-(lags - 2) / 33.35)
        h[:2] = (0.01, 0.05)
        tau, amp = E.efold_fit(h)
        self.assertAlmostEqual(tau, 33.35, places=9)
        self.assertAlmostEqual(amp, 0.03, places=9)
        tau, amp = E.efold_fit(-h)
        self.assertLess(amp, 0)

    def test_kernel_recovers_a_known_response(self):
        rng = np.random.default_rng(2)
        g = np.zeros(E.LAGS)
        g[0], g[1] = 0.02, 0.04
        g[2:] = 0.03 * np.exp(-(np.arange(2, E.LAGS) - 2) / 25.0)
        s = rng.choice(np.array([-1.0, 1.0]), 100_000)
        up = np.zeros(2 * s.size)
        up[::2] = s
        y = np.convolve(up, g)[: up.size]
        h = E.kernel(y, s)
        self.assertLess(float(np.abs(h - g).max()), 0.003)
        self.assertAlmostEqual(E.efold_fit(h)[0], 25.0, delta=1.5)

    def test_fall_by_e(self):
        lags = np.arange(E.LAGS)
        fall = E.fall_by_e(np.exp(-(lags - 2) / 30.0))
        self.assertTrue(29 <= fall <= 31, fall)
        self.assertIsNone(E.fall_by_e(np.ones(E.LAGS)))

    def test_rate_response_against_euler(self):
        h2 = np.array([[0.85, 0.3], [-0.2, 0.9]])
        c = np.array([0.6, -0.8])
        exact = E.rate_response(h2, c, 1.4)
        a = (h2 - np.eye(2)) / O.TAU_MS
        drive = 1.4 * E.PERT_SIZE * c / O.TAU_MS
        dt, x, t, euler = 1e-4, np.zeros(2), 0.0, []
        targets = [lag + 0.5 for lag in range(61)]
        i = 0
        while i < len(targets):
            x = x + dt * (a @ x + (drive if t < E.PULSE_MS else 0.0))
            t += dt
            if t >= targets[i] - 1e-12:
                euler.append(float(c @ x) / 1000.0)
                i += 1
        scale = float(np.abs(exact[:61]).max())
        self.assertLess(float(np.abs(exact[:61] - np.array(euler)).max()) / scale, 1e-3)


class Direction(unittest.TestCase):
    def matrix(self, top, seed):
        """A 200 x 200 real matrix with the given top block's eigenvalues rightmost, in a random orthogonal basis."""
        rng = np.random.default_rng(seed)
        n = 200
        a = np.zeros((n, n))
        a[: top.shape[0], : top.shape[0]] = top
        rest = rng.standard_normal((n - top.shape[0], n - top.shape[0]))
        a[top.shape[0]:, top.shape[0]:] = 0.8 * rest / math.sqrt(n)
        q, _ = np.linalg.qr(rng.standard_normal((n, n)))
        return q @ a @ q.T

    def against_eig(self, m):
        lam, v, q, h2, residual = E.least_stable(m, np.random.default_rng(3))
        w, vecs = np.linalg.eig(m)
        ref = E.rightmost(w)
        ref_v = E.rounded_direction(E.phased_real(vecs[:, int(np.argmin(np.abs(w - ref)))]))
        self.assertLess(abs(lam - ref), 1e-9)
        self.assertLess(float(np.abs(v - ref_v).max()), 1e-5)
        self.assertLess(residual, 1e-8)
        self.assertAlmostEqual(float(np.linalg.norm(v)), 1.0, places=12)
        return lam

    def test_complex_pair(self):
        # Not a normal block: at the phase rule's angle Re u and Im u differ in length (sqrt 3 against sqrt 0.5), so the
        # rule picks one direction (for a normal block, such as a rotation, every phase would do).
        lam = self.against_eig(self.matrix(np.array([[2.0, 3.0], [-0.5, 2.0]]), 4))
        self.assertAlmostEqual(lam.real, 2.0, places=9)
        self.assertAlmostEqual(lam.imag, math.sqrt(1.5), places=9)

    def test_real(self):
        lam = self.against_eig(self.matrix(np.array([[3.0]]), 5))
        self.assertEqual(lam.imag, 0.0)

    def test_phase_rule_ignores_the_phase(self):
        rng = np.random.default_rng(6)
        u = rng.standard_normal(50) + 1j * rng.standard_normal(50)
        r = E.phased_real(u)
        self.assertAlmostEqual(float(np.linalg.norm(r)), 1.0, places=12)
        self.assertGreater(r[int(np.argmax(np.abs(r)))], 0)
        for phase in (0.3, 1.7, -2.9, math.pi):
            self.assertLess(float(np.abs(E.phased_real(u * np.exp(1j * phase)) - r).max()), 1e-12)
        basis = np.column_stack([u.real, u.imag])
        coef, *_ = np.linalg.lstsq(basis, r, rcond=None)
        self.assertLess(float(np.abs(basis @ coef - r).max()), 1e-12)

    def test_rightmost(self):
        w = np.array([0.5 + 0j, 0.9 - 0.2j, 0.9 + 0.2j, 0.8 + 0j])
        self.assertEqual(E.rightmost(w), 0.9 + 0.2j)

    def test_slopes_at_045(self):
        s = E.slopes(0.45)
        self.assertAlmostEqual(s["lambda_eq16"], 0.971653, places=5)
        self.assertAlmostEqual(s["a"], 0.01401, places=5)
        self.assertAlmostEqual(s["b"], -0.06273, places=5)

    def test_stability_matrix(self):
        net = O.network(np.random.default_rng(7), ne=40, ni=10, ce=4, ci=1)
        m = E.stability_matrix(net, 2.0, -3.0, ne=40)
        self.assertTrue(((m == 2.0).sum(axis=1) == 4).all())
        self.assertTrue(((m == -3.0).sum(axis=1) == 1).all())
        self.assertTrue((np.diag(m) == 0).all())
        self.assertTrue((m[:, 40:] != 2.0).all() and (m[:, :40] != -3.0).all())


class Simulator(unittest.TestCase):
    def small(self):
        rng = np.random.default_rng(8)
        return O.network(rng, ne=400, ni=100, ce=40, ci=10), rng.uniform(O.VR, O.THETA, 500)

    def test_zero_perturbations_give_ostojics_spikes(self):
        net, v0 = self.small()
        st, si = O.simulate(net, 0.8, v0, 5000, 0)
        signs = np.random.default_rng(9).choice(np.array([-1.0, 1.0]), 20)
        _y, _n, (pt, pi) = E.pulsed(net, 0.8, v0, 1000, signs, np.zeros(500), record=True)
        self.assertGreater(st.size, 100)
        self.assertTrue(np.array_equal(st, pt) and np.array_equal(si, pi))

    def test_projection_is_its_spikes(self):
        net, v0 = self.small()
        v = np.random.default_rng(10).standard_normal(500)
        v /= np.linalg.norm(v)
        signs = np.random.default_rng(11).choice(np.array([-1.0, 1.0]), 50)
        y, n, (pt, pi) = E.pulsed(net, 0.8, v0, 1000, signs, E.PERT_SIZE * v, record=True)
        after = pt >= 1000
        expected = np.zeros(y.size)
        np.add.at(expected, (pt[after] - 1000) // 100, v[pi[after]])
        self.assertEqual(n, int(after.sum()))
        self.assertLess(float(np.abs(y - expected).max()), 1e-12)

    def test_perturbations_change_the_input(self):
        net, v0 = self.small()
        v = np.zeros(500)
        v[0] = 1.0
        quiet = np.full(10, -1.0)
        loud = np.full(10, 1.0)
        _a, n_down, _ = E.pulsed(net, 0.0, v0, 0, quiet, E.PERT_SIZE * 0.05 * v)
        _b, n_up, _ = E.pulsed(net, 0.0, v0, 0, loud, E.PERT_SIZE * 0.05 * v)
        self.assertGreaterEqual(n_up, n_down)


class Verdict(unittest.TestCase):
    def fake(self, taus=(19.4, 17.7, 22.9, 17.2), pert=((30.0, 0.03), (37.0, 0.02))):
        ac = {E.key(j): {"tau": t} for j, t in zip(E.AC_COUPLINGS, taus)}
        pe = {E.key(j): {"tau": t, "amplitude": a} for j, (t, a) in zip(E.PERT_COUPLINGS, pert)}
        return ac, pe

    def test_the_pilot_values_pass(self):
        self.assertTrue(all(E.conditions(*self.fake()).values()))

    def test_each_clause_at_and_beyond_its_edge(self):
        self.assertTrue(all(E.conditions(*self.fake(taus=(10.0, 20.0, 20.0, 20.0))).values()))
        self.assertFalse(all(E.conditions(*self.fake(taus=(9.99, 15.0, 15.0, 15.0))).values()))
        self.assertTrue(all(E.conditions(*self.fake(taus=(40.0, 20.0, 20.0, 20.0))).values()))
        self.assertFalse(all(E.conditions(*self.fake(taus=(40.01, 30.0, 30.0, 30.0))).values()))
        self.assertTrue(all(E.conditions(*self.fake(taus=(15.0, 30.0, 20.0, 20.0))).values()))
        self.assertFalse(all(E.conditions(*self.fake(taus=(15.0, 30.01, 20.0, 20.0))).values()))
        self.assertFalse(all(E.conditions(*self.fake(taus=(None, 20.0, 20.0, 20.0))).values()))
        self.assertTrue(all(E.conditions(*self.fake(pert=((80.0, 0.03), (37.0, 0.02)))).values()))
        self.assertFalse(all(E.conditions(*self.fake(pert=((80.05, 0.03), (37.0, 0.02)))).values()))
        self.assertFalse(all(E.conditions(*self.fake(pert=((30.0, 0.03), (37.0, -0.02)))).values()))
        self.assertEqual(len(E.conditions(*self.fake())), 7)


@unittest.skipUnless(HAVE, "the claim's zip is not at inputs/ (or ENGELKEN_INPUTS)")
class TheDataOfRecord(unittest.TestCase):
    def test_reads(self):
        texts = E.read_zip(INPUTS)
        self.assertEqual(set(texts), set(E.REQUIRED))

    def test_refuses_other_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(os.path.join(INPUTS, E.ZIP), tmp)
            with open(os.path.join(tmp, E.ZIP), "ab") as f:
                f.write(b"\0")
            with self.assertRaises(E.Refused):
                E.read_zip(tmp)

    def test_refuses_a_parameter_it_does_not_state(self):
        texts = E.read_zip(INPUTS)
        for base, old, new in (("example_script_spikingPerturbation.jl", "pertsize = 100", "pertsize = 10"),
                               ("Ostojic_SpikingNetwork_simulation_NEST.py", "delay   = 0.55", "delay   = 1.5"),
                               ("getMaxRealEigenvector.jl", "vReal = real(v)", "vReal = abs(v)")):
            altered = dict(texts)
            altered[base] = texts[base].replace(old, new)
            with self.subTest(base=base), self.assertRaises(E.Refused):
                E.check_texts(altered)
        missing = dict(texts)
        del missing["makeConnectivity.jl"]
        with self.assertRaises(E.Refused):
            E.check_texts(missing)


if __name__ == "__main__":
    unittest.main()
