"""Zudilin's irrationality measure of zeta(2) (pi/zeta2.py): the integers, both constructions against their Barnes
integrals and their partial fractions, Whipple's transformation, the growth constants against the forms' own growth,
the arithmetic functions against brute force, the digamma limits against Gauss's values, and the readers, all on
parameters and functions chosen here. Neither the paper's parameters (7n+1, 6n+1, 5n+1, 8n+1; 1, n+1, 2n+1, 14n+2),
nor its second construction's, nor Remark 3's, nor its printed step functions' limits, nor Remark 4's polynomial is
computed.

Run with: python3 -m unittest tests.test_zeta2
"""

import decimal
import gzip
import importlib.util
import os
import shutil
import tempfile
import unittest
from decimal import Decimal
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pi_zeta2", os.path.join(HERE, "..", "pi", "zeta2.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "3e" * 32
# families chosen here (not the paper's): a = alpha n + 1, b = beta n + 1, b4 = beta4 n + 2
ALPHA_T, BETA_T = (6, 5, 4, 8), (0, 1, 2, 13)
ALPHAH_T, BETAH_T = (10, 3, 4, 5), (2, 0, 9, 11)


def fam(n, al=ALPHA_T, be=BETA_T):
    return (tuple(x * n + 1 for x in al), (be[0] * n + 1, be[1] * n + 1, be[2] * n + 1, be[3] * n + 2))


def fam_hat(n, al=ALPHAH_T, be=BETAH_T):
    return ((al[0] * n + 2, al[1] * n + 1, al[2] * n + 1, al[3] * n + 1),
            (be[0] * n + 2, be[1] * n + 1, be[2] * n + 2, be[3] * n + 2))


def setUpModule():
    decimal.getcontext().prec = M.PRECISION


class Integers(unittest.TestCase):
    def test_primes_lcm_valuation(self):
        ps = M.primes_upto(30)
        self.assertEqual(ps, [2, 3, 5, 7, 11, 13, 17, 19, 23, 29])
        self.assertEqual(M.lcm_upto(10, ps), 2520)
        self.assertEqual(M.lcm_upto(1, ps), 1)
        self.assertEqual(M.v_p(2 ** 5 * 3 * 7, 2), 5)
        self.assertEqual(M.v_p(-81, 3), 4)
        self.assertIsNone(M.v_p(0, 5))

    def test_cubic_of(self):
        # (t-1)(t-2)(t-3)(t-4) - t^3 (t-11) = t^3 + 35 t^2 - 50 t + 24
        self.assertEqual(M.cubic_of((1, 2, 3, 4), (0, 0, 0, 11)), [24, -50, 35, 1])


class FirstConstruction(unittest.TestCase):
    def test_against_the_integral(self):
        z2 = Decimal(M.machin_pi(80)) ** 2 / 6
        for a, b in (((2, 2, 2, 3), (1, 1, 1, 5)), fam(1), ((3, 3, 2, 4), (1, 1, 2, 7))):
            q, p = M.tale1(a, b)
            r = float(Decimal(q) * z2 - M.to_dec(p, 80))
            quad = M.barnes1(a, b)
            self.assertLess(abs(quad.real - r), M.QUAD_TOL * abs(r), (a, b, quad, r))
            self.assertLess(abs(quad.imag), M.QUAD_TOL * abs(r))

    def test_partial_fractions(self):
        for n in (1, 2):
            a, b = fam(n)
            _, _, parts = M.tale1(a, b, want_parts=True)
            for t in (Fraction(1, 3), Fraction(-7, 2), Fraction(5, 11)):
                self.assertEqual(M.r1_from_parts(parts, t), M.r1_at(a, b, t))

    def test_integrality(self):
        primes = M.primes_upto(200)
        for n in (1, 2, 3, 4):
            a, b = fam(n)
            q, p = M.tale1(a, b)
            d = sum(a) - sum(b)
            a2s = sorted(a)[1]
            c1 = max(a[0] - b[0], a[1] - b[1], a[2] - b[2], b[3] - a2s - 1)
            c2 = max(d + 1, b[3] - a2s - 1)
            self.assertIsInstance(q, int)
            self.assertEqual((p * M.lcm_upto(c1, primes) * M.lcm_upto(c2, primes)).denominator, 1)

    def test_refuses_bad_parameters(self):
        with self.assertRaises(ValueError):
            M.tale1((2, 2, 3, 2), (1, 1, 1, 5))      # a4 not the largest
        with self.assertRaises(ValueError):
            M.tale1((2, 2, 2, 3), (1, 1, 3, 5))      # b3 above an a


class SecondConstruction(unittest.TestCase):
    def test_against_the_integral(self):
        z2 = Decimal(M.machin_pi(80)) ** 2 / 6
        for ah, bh in (fam_hat(1), ((7, 2, 3, 4), (3, 1, 6, 8))):
            qh, ph, parts = M.tale2(ah, bh, want_parts=True)
            r = float(M.to_dec(Fraction(qh), 80) * z2 - M.to_dec(ph, 80))
            c = -parts["a0s"] + 0.5                          # inside (-a0*, 1 - b0), and no pole on Re t = c/2
            quad = M.barnes2(ah, bh, c)
            self.assertLess(abs(quad.real - r), M.QUAD_TOL * abs(r), (ah, bh, quad, r))

    def test_partial_fractions_and_closed_form(self):
        for n in (1, 2, 3):
            ah, bh = fam_hat(n)
            _, _, parts = M.tale2(ah, bh, want_parts=True)
            for t in (Fraction(1, 3), Fraction(2, 7)):
                rebuilt = (sum(v / (t + k) ** 2 for k, v in parts["A"].items())
                           + sum(v / (t + k) for k, v in parts["B"].items()))
                self.assertEqual(rebuilt, M.r2_at(ah, bh, t))
            self.assertEqual(sum(parts["B"].values()), 0)
            for k, v in parts["A"].items():
                self.assertEqual(v, M.ak_closed(ah, bh, k), (n, k))

    def test_whipple(self):
        # Remark 5's identity between the two q's, on a family chosen here: it holds with a minus sign, under the
        # signs (-1)^d and (-1)^d^ that the remark gives q and q^ (four such families gave -1 for n = 1 to 5)
        for n in range(1, 5):
            a = (5 * n + 1, 4 * n + 1, 2 * n + 1, 6 * n + 1)
            b4 = 11 * n + 2
            b = (1, a[3] - a[0] + 1, a[3] - a[1] + 1, b4)
            ah = (b4 - a[2] + a[3], a[1], a[0], a[3])
            bh = (a[3] + 1, a[3] - a[2] + 1, a[0] + a[1], b4)
            q1, _ = M.tale1(a, b)
            q2, _ = M.tale2(ah, bh)
            self.assertEqual(q1, -q2, n)

    def test_refuses_bad_parameters(self):
        with self.assertRaises(ValueError):
            M.tale2((12, 4, 5, 6), (4, 1, 11, 12))   # the sums do not match


class Growth(unittest.TestCase):
    def test_lemma6_against_the_forms(self):
        L = M.lemma3(ALPHA_T, BETA_T)
        qs = {n: M.tale1(*fam(n))[0] for n in range(1, 23)}
        ratios = {n: abs(Fraction(qs[n + 1], qs[n])) for n in range(1, 22)}
        rich = M.to_dec(M.richardson(ratios, 17, 4), 40)
        self.assertLess(abs(rich / L["C1"].exp() - 1), Decimal("1e-4"))
        with decimal.localcontext() as ctx:
            ctx.prec = 400
            z2 = M.machin_pi(400) ** 2 / 6
            q, p = M.tale1(*fam(20))
            r = abs(Decimal(q) * z2 - M.to_dec(p, 400))
            self.assertLess(r.ln() / 20, -(L["C0"] - Decimal("0.5")))
            self.assertGreater(r.ln() / 20, -(L["C0"] + 1))

    def test_cubic_zeros(self):
        # (l + 1000)(l^2 + l/10 + 1/100) * 100 = 100 l^3 + 100010 l^2 + 10001 l + 1000
        z = M.remark4_zeros((1000, 10001, 100010, 100))
        self.assertLess(abs(z["lambda1"] + 1000), Decimal("1e-40"))
        self.assertLess(abs(z["abs_pair"] - Decimal("0.1")), Decimal("1e-40"))
        self.assertIsNone(M.remark4_zeros((-6, 11, -6, 1)))       # (l-1)(l-2)(l-3): no complex pair

    def test_richardson(self):
        seq = {n: Fraction(5) - Fraction(1, n) + Fraction(4, n * n) for n in range(5, 15)}
        self.assertLess(abs(M.richardson(seq, 8, 4) - 5), Fraction(1, 10 ** 6))


class Functions(unittest.TestCase):
    def test_min_over_y_brute(self):
        al, be = (10, 3, 4, 5), (2, 0, 9, 11)
        for x in (Fraction(1, 7), Fraction(3, 10), Fraction(5, 13), Fraction(17, 19)):
            fast = M.phi_hat(al, be, x)
            grid = 8 * x.denominator                         # every step of y (multiples of 1/2b) and points between
            brute = None
            for i in range(grid):
                y = Fraction(i, grid)
                v = (M.fl(2 * y - be[0] * x) - M.fl(2 * y - al[0] * x) - M.fl((al[0] - be[0]) * x)
                     + M.fl(y - be[1] * x) - M.fl(y - al[1] * x) - M.fl((al[1] - be[1]) * x)
                     + sum(M.fl((be[j] - al[j]) * x) - M.fl(be[j] * x - y) - M.fl(y - al[j] * x) for j in (2, 3)))
                brute = v if brute is None else min(brute, v)
            self.assertLessEqual(fast, brute)
            self.assertEqual(fast, brute, x)

    def test_lemma7_and_remark2_agree_elsewhere(self):
        al, be = ALPHA_T, BETA_T
        for x in M.grid_points(20)[::7]:
            self.assertEqual(M.phi_lemma4(al, be, x), M.phi_remark2(al, be, x), x)

    def test_step_and_grid(self):
        f = {2: [(Fraction(1, 3), Fraction(1, 2))], 1: [(Fraction(1, 2), Fraction(2, 3))]}
        self.assertEqual(M.step(f, Fraction(1, 3)), 2)
        self.assertEqual(M.step(f, Fraction(1, 2)), 1)
        self.assertEqual(M.step(f, Fraction(2, 3)), 0)
        self.assertEqual(M.step(f, Fraction(4, 3)), 2)      # 1-periodic
        pts = M.grid_points(3)                              # 0, 1/3, 1/2, 2/3 and three points in each of 4 gaps
        self.assertEqual(len(pts), 4 + 12)
        g = M.as_steps(lambda x: M.step(f, x), 6)
        self.assertEqual(g, f)

    def test_limits_against_gauss(self):
        pi = M.machin_pi(M.PRECISION)
        s3 = Decimal(3).sqrt()
        # the indicator of [1/2, 2/3), nothing below 1/2: psi(2/3) - psi(1/2)
        v = M.step_limit({1: [(Fraction(1, 2), Fraction(2, 3))]}, 2)
        self.assertLess(abs(v - (pi / (2 * s3) - (3 * s3 / 4).ln())), Decimal("1e-40"))
        # the indicator of [1/4, 1/2) cut at 1/3: psi(1/2) - psi(1/4) - (4 - 3) = pi/2 + log 2 - 1
        v = M.step_limit({1: [(Fraction(1, 4), Fraction(1, 2))]}, 3)
        self.assertLess(abs(v - (pi / 2 + Decimal(2).ln() - 1)), Decimal("1e-40"))

    def test_inclusion_counts_failures(self):
        primes = M.primes_upto(100)
        D = M.lcm_upto(9, primes) * M.lcm_upto(8, primes)
        f = {2: [(Fraction(0), Fraction(1))]}               # demands p^2 at every prime above 3, up to 8
        forms = {1: {"q": 5 * 5 * 7, "p": Fraction(25 * 49, D)}}
        self.assertEqual(M.inclusion(forms, primes, f), [{"n": 1, "p": 7, "form": "q", "need": 2, "ord": 1}])
        forms = {1: {"q": 25 * 49, "p": Fraction(25 * 49, D)}}
        self.assertEqual(M.inclusion(forms, primes, f), [])
        forms = {1: {"q": 1, "p": Fraction(1, 11 * D)}}
        self.assertEqual(M.inclusion(forms, primes, f)[0]["what"], "D9n D8n p_n not an integer")


class Run(unittest.TestCase):
    def test_refused_seed(self):
        with self.assertRaises(M.Refused):
            M.run("nothex", inputs=os.path.join(HERE, "nonexistent"), results=os.path.join(HERE, "nonexistent"))

    def test_refused_hash(self):
        work = tempfile.mkdtemp()
        try:
            with open(os.path.join(work, M.INPUTS["eprint"][0]), "wb") as fh:
                fh.write(gzip.compress(b"not the e-print"))
            with self.assertRaises(M.Refused):
                M.run(SEED, inputs=work, results=os.path.join(work, "results"))
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def test_source_check(self):
        with self.assertRaises(M.Refused):
            M.check_source("\\documentclass{amsart} nothing here")
        flat_all = " ".join(M.PRINTED_TEX)
        M.check_source(flat_all)                            # every fragment present: no refusal

    def test_test_length(self):
        self.assertLessEqual(len(M.TEST), 600)

    def test_machin(self):
        self.assertEqual(str(M.machin_pi(60))[:52], M.PI50)


if __name__ == "__main__":
    unittest.main()
