"""Zudilin 2004 (pi/zudilin2004.py): the TeX readers on snippets made here and their refusals; the Farey points, the
lcm and the primes; the interval method for phi against a direct evaluation; Lemma 19's machinery on a small case
(r = 3, q = 7, eta = (24; 5, 5, 5, 6, 6, 7, 7)): the partial fractions summing back to R(t), the vanishing
coefficients, the symmetry, the integrality, and the form's value from its coefficients against its series; the
analytic constants' root selection; Propositions 3 and 4's machinery on small directions; the group's order; and the
digit comparisons. Nothing here computes the paper's own cases (Theorems 1 to 3, Hata's, the Observation's or the
remark's), so none of the test's quantities is computed.

Run with: python3 -m unittest discover -s tests -p test_zudilin2004.py
"""

import gzip
import importlib.util
import os
import random
import tempfile
import unittest
from fractions import Fraction

import mpmath

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pi_zudilin2004", os.path.join(HERE, "..", "pi", "zudilin2004.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

TOY = (3, 24, (5, 5, 5, 6, 6, 7, 7))
OMEGA_TEX = (r"for $x\in[0,1)$, where $\Omega_0=[0,1)$, \begin{align*} \Omega_1 &=\Omega_2 "
             r"=\bigl[\tfrac2{91},\tfrac{36}{37}\bigr) \cup\bigl[\tfrac{90}{91},1\bigr), \displaybreak[0]\\ "
             + " ".join(rf"\Omega_{k} &=\bigl[\tfrac1{{{k + 10}}},\tfrac34\bigr) \cup\bigl[\tfrac{{7}}{{8}},1\bigr),"
                        for k in range(3, 10))
             + r" \end{align*} and $\Omega_{10}=\emptyset$.")
M0_TEX = (r"The set $\sM_0$ in this case consists of the following elements: \begin{gather*} "
          + r" \; ".join(rf"\biggl(\begin{{array}}{{rrrr}} {i}, & {i + 1}, & {i + 2}, & {i + 3} \\ 0, & 7, & 31, & 32 "
                         rf"\end{{array}}\biggr)," for i in range(20))
          + r" \end{gather*} an easy verification shows")


class Source(unittest.TestCase):
    def test_flatten(self):
        self.assertEqual(M.flatten("a  b % comment\n c\\% d\n"), "a b c\\% d ")

    def test_parse_omegas(self):
        om = M.parse_omegas(M.flatten(OMEGA_TEX))
        self.assertEqual(sorted(om), list(range(1, 10)))
        self.assertEqual(om[1], [(Fraction(2, 91), Fraction(36, 37)), (Fraction(90, 91), Fraction(1))])
        self.assertEqual(om[2], om[1])
        self.assertEqual(om[5], [(Fraction(1, 15), Fraction(3, 4)), (Fraction(7, 8), Fraction(1))])
        with self.assertRaises(M.Refused):
            M.parse_omegas(M.flatten(OMEGA_TEX.replace(r"\Omega_9 &=", r"\Omega9 =")))

    def test_parse_m0(self):
        m0 = M.parse_m0(M.flatten(M0_TEX))
        self.assertEqual(len(m0), 20)
        self.assertEqual(m0[3], ((3, 4, 5, 6), (0, 7, 31, 32)))
        with self.assertRaises(M.Refused):
            M.parse_m0(M.flatten(M0_TEX.replace(r"\biggl(\begin{array}{rrrr} 5,", r"\biggl(5,")))

    def test_read_source_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            data = gzip.compress((OMEGA_TEX + M0_TEX).encode("latin-1"))
            name = M.EPRINT[0]
            with open(os.path.join(d, name), "wb") as fh:
                fh.write(data)
            saved = M.EPRINT
            try:
                import hashlib
                M.EPRINT = (name, hashlib.sha256(data).hexdigest(), len(data))
                with self.assertRaises(M.Refused) as cm:
                    M.read_source(d)
                self.assertIn("does not hold", str(cm.exception))
                M.EPRINT = (name, "0" * 64, len(data))
                with self.assertRaises(M.Refused) as cm:
                    M.read_source(d)
                self.assertIn("not the registered", str(cm.exception))
            finally:
                M.EPRINT = saved


class Exact(unittest.TestCase):
    def test_farey_lcm_primes(self):
        self.assertEqual(len(M.farey(5)), 11)
        self.assertEqual(M.farey(3), [Fraction(0), Fraction(1, 3), Fraction(1, 2), Fraction(2, 3), Fraction(1)])
        self.assertEqual(M.lcm_upto(10), 2520)
        self.assertEqual(M.primes_upto(20), [2, 3, 5, 7, 11, 13, 17, 19])

    def test_phi_interval_method(self):
        r, e0, eta = TOY
        ar = M.t3_arithmetic(r, e0, eta)
        rng = random.Random(7)
        for _ in range(150):
            x = Fraction(rng.randrange(1, 10 ** 7), 10 ** 7)
            v = next((v for a, b, v in ar["steps"] if a < x < b), None)
            if v is not None:
                self.assertEqual(v, M.phi_min_exact(ar["terms"], x))
        self.assertTrue(all(v >= 0 for _, _, v in ar["steps"]))
        om = M.omegas_of(ar["steps"], ar["phi_max"])
        for nu in range(2, ar["phi_max"] + 1):
            for a, b in om[nu]:
                self.assertTrue(any(c <= a and b <= d for c, d in om[nu - 1]))
        self.assertEqual(ar["m"], [max(5, 24 - 12, 24 - 5 - e) for e in (6, 6, 7, 7)])

    def test_integrals(self):
        steps = [(Fraction(0), Fraction(1, 4), 0), (Fraction(1, 4), Fraction(1, 2), 2),
                 (Fraction(1, 2), Fraction(1), 1)]
        ipsi, i2 = M.integrals(steps, Fraction(1, 3))
        with mpmath.workdps(40):
            want = 2 * (mpmath.digamma(0.5) - mpmath.digamma(0.25)) + (mpmath.digamma(1) - mpmath.digamma(0.5))
            self.assertLess(abs(ipsi - want), mpmath.mpf("1e-35"))
        self.assertEqual(i2, 2 * (4 - 3))
        with self.assertRaises(M.Refused):
            M.integrals([(Fraction(0), Fraction(1), 1)], Fraction(1, 2))


class Lemma19(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        r, e0, eta = TOY
        cls.res = M.lemma19(r, e0, eta, 1)

    def test_partial_fractions(self):
        parts, B = self.res["parts"], self.res["B"]
        for t in (Fraction(1, 3), Fraction(-1, 2), Fraction(9, 4), Fraction(-35, 3)):
            tot = sum((B[(j, k)] / (t + k) ** (j - 3) for (j, k) in B), Fraction(0))
            self.assertEqual(tot, M.r_at(parts, t))

    def test_structure(self):
        self.assertTrue(self.res["zeros_ok"])
        self.assertTrue(self.res["symmetric"])
        self.assertTrue(all(self.res["integral"].values()))
        self.assertEqual(self.res["kept"], [0, 5])
        self.assertNotEqual(self.res["A"][5], 0)

    def test_printed_reading(self):
        printed = M.lemma19(*TOY, 1, want_value=False, well_poised=False)
        self.assertFalse(printed["zeros_ok"])
        self.assertEqual(printed["nonzero"], [4, 6])
        self.assertEqual(self.res["nonzero"], [5])

    def test_planted_fault(self):
        caught, p = M.planted_fault_caught(self.res)
        self.assertTrue(caught)
        self.assertEqual(p, 29)
        self.assertEqual(M.least_prime_above(89), 97)

    def test_form_value_settles(self):
        x = M.lemma19(*TOY, 2)
        with mpmath.workdps(x["digits"]):
            fs = M.series_value(x["parts"], 3, dps=x["digits"])
            self.assertLess(abs(fs - x["F"]) / abs(fs), mpmath.mpf("1e-25"))
        F, dps = M.form_value(x["A"], 0)
        self.assertGreaterEqual(dps, 160)
        with self.assertRaises(M.Refused):
            M.form_value({0: Fraction(0), 5: Fraction(0)}, 0)

    def test_value_against_series(self):
        with mpmath.workdps(40):
            fs = M.series_value(self.res["parts"], 3, dps=40)
            rel = abs(fs - self.res["F"]) / abs(fs)
            self.assertLess(rel, mpmath.mpf("1e-20"))

    def test_arith_definitions(self):
        parts = M.lemma19_parts(*TOY, 1)
        ar = M.lemma19_arith(parts, 3)
        self.assertEqual(parts["h0"], 26)
        self.assertEqual(ar["m0"], 12)
        self.assertEqual(ar["m"], [13, 13, 12, 12])
        self.assertEqual(sorted(ar["nu"]), [7, 11])
        self.assertEqual(ar["dprod"], M.lcm_upto(13) ** 3 * M.lcm_upto(13) * M.lcm_upto(12) ** 2)


class Analytic(unittest.TestCase):
    def test_t3_root_selection(self):
        r, e0, eta = TOY
        an = M.t3_analytic(r, e0, eta, dps=40)
        self.assertEqual(an["roots"], an["coeffs_degree"])
        coeffs = M.t3_polynomial(r, e0, eta)
        rs = M.roots_of(coeffs, 40)
        with mpmath.workdps(40):
            upper = [z for z in rs if z.imag > mpmath.mpf("1e-15")]
            self.assertTrue(upper)
            self.assertTrue(all(an["tau0"].real >= z.real - mpmath.mpf("1e-30") for z in upper))
            self.assertGreater(an["tau0"].imag, 0)
            self.assertLess(an["residual"], mpmath.mpf("1e-30"))

    def test_quadratic(self):
        t0, t1, coeffs, resid = M.quadratic_roots((4, 5, 6, 7), (0, 1, 10, 11), dps=40)
        self.assertEqual(len(coeffs), 3)
        self.assertTrue(1 < t0 < 4 and t1 > 7)
        self.assertLess(resid, mpmath.mpf("1e-30"))
        with self.assertRaises(M.Refused):
            M.quadratic_roots((4, 5, 6, 8), (0, 1, 10, 11))

    def test_propositions_machinery(self):
        z3 = M.zeta3_case((4, 5, 6, 7), (0, 1, 10, 11),
                          sorted({(p, (0, 1, 10, 11)) for p in __import__("itertools").permutations((4, 5, 6, 7))}))
        self.assertEqual(z3["orbit"], 24)
        self.assertTrue(z3["where"])
        self.assertEqual(min(z3["range"]), 0)
        z2 = M.zeta2_case((5, 6, 7), (0, 10, 12))
        self.assertEqual(z2["group"], 120)
        self.assertTrue(z2["where"])
        self.assertEqual(min(z2["range"]), 0)
        self.assertTrue(mpmath.isfinite(z2["c0"]) and mpmath.isfinite(z2["c1"]))


class Compare(unittest.TestCase):
    def test_digits(self):
        self.assertEqual(M.digits_as(mpmath.mpf("5.513890629"), "5.51389062"), "cut")
        self.assertEqual(M.digits_as(mpmath.mpf("5.513890626"), "5.51389063"), "rounded")
        self.assertIsNone(M.digits_as(mpmath.mpf("5.513890640"), "5.51389062"))
        lo, hi = M.BOUNDS["t1"]
        with mpmath.workdps(60):
            self.assertTrue(M.in_bounds(mpmath.mpf("5.513890625"), lo, hi))
            self.assertTrue(M.in_bounds(mpmath.mpf("5.51389062"), lo, hi))
            self.assertFalse(M.in_bounds(mpmath.mpf("5.5138906300001"), lo, hi))
            self.assertFalse(M.in_bounds(mpmath.mpf("5.5138906199999"), lo, hi))

    def test_fit_list(self):
        s = M.fit_list("head ", ["x" * 70] * 4)
        self.assertLessEqual(len(s), M.LIMIT)


if __name__ == "__main__":
    unittest.main()
