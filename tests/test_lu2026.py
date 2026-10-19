"""Lü's polynomial separation (mm/lu2026.py): field tables, interpolation, the substitution's matrices and inverse,
the pullback against eq. 2.3, the planted faults, Lemma 4.1 modulo p, and the e-print reader, on inputs outside the
test's (F_11, F_13, F_25 and pairs with M or n of 6 over Q). Nothing here builds the test's fields at M, n <= 5.

Run with: python3 -m unittest tests.test_lu2026 (in the pinned python image; standard library only)
"""

import importlib.util
import io
import math
import os
import random
import tarfile
import tempfile
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("mm_lu2026", os.path.join(HERE, "..", "mm", "lu2026.py"))
M_ = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M_)

F11 = M_.Field("F11", 11)
F13 = M_.Field("F13", 13)
F25 = M_.Field("F25", 5, 2, (2, 0, 1))           # x^2 + 2, irreducible over F_5
QQ = M_.Field("Q", 0)


class Fields(unittest.TestCase):
    def test_tables(self):
        rng = random.Random(1)
        for F in (F11, F13, F25):
            for _ in range(500):
                a, b, c = (rng.randrange(F.q) for _ in range(3))
                self.assertEqual(F.mul(F.mul(a, b), c), F.mul(a, F.mul(b, c)))
                self.assertEqual(F.mul(a, F.add(b, c)), F.add(F.mul(a, b), F.mul(a, c)))
                self.assertEqual(F.sub(F.add(a, b), b), a)
            self.assertTrue(all(F.mul(a, F.inv(a)) == 1 for a in range(1, F.q)))
            with self.assertRaises(ZeroDivisionError):
                F.inv(0)
        # F_25 has an element of order 24
        best = 0
        for g in range(1, 25):
            x, o = g, 1
            while x != 1:
                x, o = F25.mul(x, g), o + 1
            best = max(best, o)
        self.assertEqual(best, 24)
        self.assertEqual(F11.from_int(-3), 8)
        self.assertEqual(QQ.inv(Fraction(2)), Fraction(1, 2))


class Polynomials(unittest.TestCase):
    def test_lagrange(self):
        for F, pts in ((F11, [0, 3, 7, 10]), (QQ, [Fraction(v) for v in (-2, 0, 5)]), (F25, [0, 1, 7, 13, 24])):
            L = M_.lagrange(F, pts)
            for k, row in enumerate(L):
                for j, x in enumerate(pts):
                    self.assertEqual(M_.peval(F, row, x), F.one if j == k else F.zero)

    def test_binom_poly(self):
        for w in range(6):
            got = M_.binom_poly(F11, 4, w, 4)
            want = {(d, d): (math.comb(w, d) * 4 ** (w - d)) % 11 for d in range(min(w, 3) + 1)}
            self.assertEqual(got, {k: v for k, v in want.items() if v})

    def test_g_inverse(self):
        for F, a, n in ((F11, 6, 4), (QQ, Fraction(-3), 5), (F25, 17, 3)):
            G = M_.g_matrix(F, a, n)
            Gi = M_.g_inverse(F, G, n)
            for r in range(n):
                for c in range(n):
                    tot = {}
                    for k in range(n):
                        tot = M_.ladd(F, tot, M_.lmul(F, G[r][k], Gi[k][c]))
                    self.assertEqual(tot, {0: F.one} if r == c else {})


class Construction(unittest.TestCase):
    def instances(self):
        yield F11, M_.draw_instance(F11, 3, 4, random.Random(2))
        yield F13, M_.draw_instance(F13, 4, 4, random.Random(3))
        yield F25, M_.draw_instance(F25, 2, 3, random.Random(4))
        yield QQ, M_.draw_instance(QQ, 6, 2, random.Random(5))
        yield QQ, M_.draw_instance(QQ, 2, 6, random.Random(6))

    def test_pullback_is_phi(self):
        for F, inst in self.instances():
            r = M_.check_instance(F, inst)
            for c in ("polynomial", "equal", "direct_sum", "degree_ok", "restriction", "printed_inverse"):
                self.assertTrue(r[c], (F.name, inst["M"], inst["n"], c))
            self.assertEqual(r["degree"], min(inst["M"], inst["n"]) - 1)

    def test_planted_faults(self):
        F, inst = F11, M_.draw_instance(F11, 3, 3, random.Random(7))
        A = M_.matched_form(inst)
        good = M_.phi(F, inst)
        T, ok = M_.pullback(F, inst, A, b_pts=inst["b"][:-1])
        self.assertFalse(ok)
        self.assertNotEqual(T, good)
        T, _ = M_.pullback(F, inst, A, beta_plain=True)
        self.assertNotEqual(T, good)
        T, _ = M_.pullback(F, inst, M_.matched_form(inst, cross=F.one))
        self.assertNotEqual(T, good)
        self.assertFalse(M_.direct_sum_at_zero(F, inst, T))
        bad = dict(inst, a=[inst["a"][0], inst["a"][0], inst["a"][2]])
        with self.assertRaises(ZeroDivisionError):
            M_.direct_sum_at_zero(F, bad, M_.phi(F, bad))

    def test_too_small_field_has_no_points(self):
        with self.assertRaises(ValueError):
            M_.draw_instance(M_.Field("F2", 2), 2, 2, random.Random(8))     # needs 3 distinct points


class Lemma41(unittest.TestCase):
    def test_sequence_and_degeneration_mod_other_primes(self):
        for p in (7, 11):
            self.assertTrue(all(M_.exact_sequence(e, p) for e in range(1, 7)))
            self.assertTrue(all(M_.filtration_mod(a, b, p) for a in (1, 2, 3) for b in (2, 3, 4)))

    def test_ranks(self):
        self.assertEqual(M_.rank_mod([[1, 1], [1, 1]], 2), 1)
        self.assertEqual(M_.rank_mod([[1, 2], [2, 4]], 5), 1)
        self.assertEqual(M_.rank_mod([[1, 2], [3, 4]], 2), 1)       # det -2 = 0 mod 2
        self.assertEqual(M_.rank_q([[1, 2], [3, 4]]), 2)


class Reader(unittest.TestCase):
    def test_printed_found_normalises_whitespace(self):
        tex = "foo P=F[t]_{<M},\\qquad\n   J=F[u]/(u^n), bar"
        self.assertTrue(M_.printed_found(tex)[4])
        self.assertFalse(M_.printed_found(tex)[0])

    def test_hash_refused(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.tar.gz")
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w:gz") as tar:
                data = b"not the paper"
                info = tarfile.TarInfo(M_.TEX_MEMBER)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            with open(path, "wb") as fh:
                fh.write(buf.getvalue())
            with self.assertRaises(M_.Refused):
                M_.read_input(path)

    def test_bad_seed(self):
        with self.assertRaises(M_.Refused):
            M_.run("nope")


if __name__ == "__main__":
    unittest.main()
