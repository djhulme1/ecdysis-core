"""Guillera & Zudilin's supercongruences (pi/gz2010.py): the transcription of each congruence against its own TeX line
(the summand's Pochhammer symbols, polynomial, z, right-hand side, modulus, bound and range); the e-print reader and its
refusals; primes, Legendre symbols and Fermat quotients; the modular sums against exact sums on summands written here,
p dividing a Pochhammer denominator among them; the verdict's arithmetic on sums whose answer is known; the WZ check
on pairs written here; Euler's transformation on binomial series whose sums are known; and the constants. None of the
paper's congruences, pairs, lemmas, identities or series is evaluated here.

Run with: python3 -m unittest discover -s tests -p test_gz2010.py
"""

import cmath
import gzip
import importlib.util
import math
import os
import re
import tempfile
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pi_gz2010", os.path.join(HERE, "..", "pi", "gz2010.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

NAMES = {(1, 2): r"\frac12", (1, 4): r"\frac14", (3, 4): r"\frac34", (1, 3): r"\frac13", (2, 3): r"\frac23"}


def poch_tex(poch):
    """The Pochhammer product as the paper writes it: runs of a symbol become a power."""
    parts, i = [], 0
    while i < len(poch):
        j = i
        while j + 1 < len(poch) and poch[j + 1] == poch[i]:
            j += 1
        parts.append(f"({NAMES[poch[i]]})_n" + ("" if j == i else f"^{j - i + 1}"))
        i = j + 1
    return "".join(parts)


def poly_tex(coeffs):
    terms = []
    for power in range(len(coeffs) - 1, -1, -1):
        c = coeffs[power]
        if power == 0:
            terms.append(str(c))
        else:
            terms.append(("" if c == 1 else str(c)) + "n" + ("" if power == 1 else f"^{power}"))
    return "(" + "+".join(terms) + ")"


# z as printed, written out here: the TeX of each line's factor and its value.
Z_TEX = {r")2^{2n}": (4, 1), r"(-1)^n2^{2n}": (-4, 1), r"(-1)^n2^{3n}": (-8, 1), r")2^{6n}": (64, 1),
         r"(-1)^n\biggl(\frac43\biggr)^{2n}": (-16, 9), r"\biggl(\frac43\biggr)^{4n}": (256, 81),
         r")\biggl(\frac{27}{16}\biggr)^n": (27, 16), r"(-1)^n2^{10n}": (-1024, 1),
         r"(-1)^n\biggl(\frac{27}{16}\biggr)^n": (-27, 16)}
# The right-hand sides as printed, written out here.
RHS_TEX = {(1, None, 1): r"\equiv p\pmod", (1, None, 2): r"\equiv p^2\pmod", (8, None, 1): r"\equiv 8p",
           (3, None, 1): r"\equiv 3p\pmod", (32, None, 2): r"\equiv 32p^2\pmod", (9, None, 2): r"\equiv 9p^2\pmod",
           (1, -3, 1): r"\equiv \biggl(\frac{-3}{p}\biggr)p\pmod"}


class Transcription(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual([c["no"] for c in M.CONGRUENCES.values()], list(range(1, 13)))
        self.assertEqual(len(M.TESTED), 12)
        self.assertEqual([M.CONGRUENCES[lab]["no"] for lab in M.CONJECTURAL], [5, 6, 7, 8, 9])
        for lab in M.CONJECTURAL:
            self.assertIn(r"\overset?\equiv", M.CONGRUENCES[lab]["tex"])
        for lab in set(M.TESTED) - set(M.CONJECTURAL):
            self.assertNotIn(r"\overset?", M.CONGRUENCES[lab]["tex"])

    def test_modulus_and_bound(self):
        for lab, c in M.CONGRUENCES.items():
            with self.subTest(lab=lab):
                self.assertEqual(re.findall(r"\\pmod\{p\^(\d)\}", c["tex"]), [str(c["r"])])
                self.assertEqual(re.findall(r"\$p>(\d+)\$", c["tex"]), [str(c["bound"])])

    def test_summand(self):
        for lab, c in M.CONGRUENCES.items():
            with self.subTest(lab=lab):
                self.assertIn(poly_tex(c["poly"]), c["tex"].replace(" ", ""))
                self.assertIn(poch_tex(c["poch"]), c["tex"])
                den = c["tex"].split(poch_tex(c["poch"]), 1)[1]
                self.assertTrue(den.startswith("}{(1)_n^" + str(c["d"]) + "}") or den.startswith(
                    "}{n!^" + str(c["d"]) + "}"))
                flat = c["tex"].replace(" ", "")
                zs = [t for t in Z_TEX if t.replace(" ", "") in flat
                      and not any(t != u and t in u and u.replace(" ", "") in flat for u in Z_TEX)]
                self.assertEqual([Z_TEX[t] for t in zs], [c["z"]])

    def test_right_hand_sides(self):
        for lab, c in M.CONGRUENCES.items():
            with self.subTest(lab=lab):
                tex = c["tex"].replace(r"\overset?\equiv", r"\equiv")
                if c["rhs"] == (1, -1, 1):
                    self.assertTrue(r"\equiv \biggl(\frac{-1}{p}\biggr)p\pmod" in tex
                                    or r"\equiv(-1)^{(p-1)/2}p\pmod" in tex)
                else:
                    self.assertIn(RHS_TEX[c["rhs"]], tex)

    def test_upper_limits(self):
        for lab, c in M.CONGRUENCES.items():
            with self.subTest(lab=lab):
                want = r"\sum_{n=0}^{(p-1)/2}" if c["upper"] == "(p-1)/2" else r"\sum_{n=0}^{p-1}"
                self.assertIn(want, c["tex"][:40])
        self.assertEqual([M.CONGRUENCES[lab]["no"] for lab in M.PROVED], [10, 11, 12])
        self.assertEqual([M.CONGRUENCES[lab]["no"] for lab in M.HALF], [1, 2, 3, 4, 8])


class Source(unittest.TestCase):
    def test_reader(self):
        tex = "a % comment\n\\label{x}  b"
        self.assertEqual(M.flat_tex(gzip.compress(tex.encode())), "a \\label{x} b")
        self.assertEqual(M.flat_tex(gzip.compress(b"50\\% off")), "50\\% off")
        with self.assertRaises(M.Refused):
            M.flat_tex(b"not gzip")
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "f.gz")
            with open(path, "wb") as fh:
                fh.write(gzip.compress(b"x"))
            with self.assertRaises(M.Refused):
                M.read_bytes(path, M.INPUT[1], M.INPUT[2])

    def test_source_checks(self):
        c = M.CONGRUENCES["J1a"]
        found = M.source_checks(c["tex"] + " \\label{J1a} rest")
        self.assertTrue(found["(1) J1a"])
        self.assertFalse(found["(2) J2a"])
        self.assertFalse(found["pair or equation 1"])
        self.assertFalse(M.source_checks(c["tex"] + " x \\label{J1a}")["(1) J1a"])     # text between: refused


class Arithmetic(unittest.TestCase):
    def test_primes_and_symbols(self):
        self.assertEqual(M.primes_upto(30), [2, 3, 5, 7, 11, 13, 17, 19, 23, 29])
        self.assertEqual(len(M.primes_upto(1000)), 168)
        for p in (3, 5, 7, 11, 13, 17, 19, 23):
            for D in (-1, -3, 2, 5):
                self.assertEqual(M.legendre(D, p), M.legendre_count(D, p))
        self.assertEqual(M.legendre(-1, 7), -1)
        self.assertEqual(M.legendre(-3, 3), 0)
        self.assertEqual(M.split(5 ** 3 * 7, 5), (3, 7))
        with self.assertRaises(M.Refused):
            M.split(0, 5)

    def test_fermat_quotients_and_roots(self):
        self.assertEqual(M.fermat_q(2, 3), 1)
        self.assertEqual(M.fermat_q(2, 5), 3)
        self.assertEqual(M.fermat_q(2, 7), 2)                               # (64 - 1)/7 = 9
        self.assertEqual(M.fermat_q(Fraction(1, 2), 5), (-3) % 5)           # q(1/x) = -q(x)
        self.assertEqual(M.fermat_q(-8, 11), 3 * M.fermat_q(2, 11) % 11)   # q(ab) = q(a) + q(b), q(-1) = 0
        self.assertEqual(M.sqrt_mod(2, 7) ** 2 % 7, 2)
        self.assertIsNone(M.sqrt_mod(3, 7))

    def test_modular_against_exact(self):
        specs = [dict(no=0, poch=[(1, 2)], d=1, poly=(1,), z=(1, 1), upper="p-1"),
                 dict(no=0, poch=[(1, 3), (1, 2)], d=2, poly=(2, 7), z=(-1, 5), upper="p-1"),
                 dict(no=0, poch=[(1, 2)] * 3, d=3, poly=(1,), z=(1, 1), upper="(p-1)/2"),
                 dict(no=0, poch=[(1, 3), (2, 3)], d=2, poly=(1, 1), z=(27, 4), upper="p-1")]
        for c in specs:
            for p in (3, 5, 7, 11, 13):
                terms = [M.hyper_term_exact(c, n) for n in range(M.upper_of(c, p) + 1)]
                for R in (1, 3, 6):
                    if any(t.denominator % p == 0 for t in terms):          # a term not p-integral: refused
                        with self.assertRaises(M.Refused):
                            M.hyper_sum(c, p, R)
                    else:
                        self.assertEqual(M.hyper_sum(c, p, R), M.exact_mod(sum(terms), p, R), (c["poch"], p, R))

    def test_p_in_a_pochhammer_denominator(self):
        # (1/3)_n (2/3)_n 27^n / n!^2 = (3n)!/(n!^3): 3-integral, though 3 divides each Pochhammer denominator.
        c = dict(no=0, poch=[(1, 3), (2, 3)], d=2, poly=(1,), z=(27, 1), upper="p-1")
        for R in (1, 2, 4):
            want = sum(math.factorial(3 * n) // math.factorial(n) ** 3 for n in range(3)) % 3 ** R
            self.assertEqual(M.hyper_sum(c, 3, R), want)

    def test_refusals(self):
        c = dict(no=0, poch=[(1, 3)], d=1, poly=(1,), z=(1, 1), upper="p-1")
        with self.assertRaises(M.Refused):
            M.hyper_sum(c, 3, 2)                         # (1/3)_1 = 1/3 is not 3-integral
        with self.assertRaises(M.Refused):
            M.exact_mod(Fraction(1, 5), 5, 2)

    def test_verdict_arithmetic(self):
        ones = dict(no=0, poch=[], d=0, poly=(1,), z=(1, 1), upper="p-1", rhs=(1, None, 1), r=2, bound=2)
        for p in (3, 5, 7):
            self.assertEqual(M.check(ones, p), (True, 2 + M.EXTRA))   # the sum of p ones is exactly p
        twice = dict(ones, rhs=(2, None, 1))
        self.assertEqual(M.check(twice, 7), (False, 1))               # p - 2p is divisible by p only once
        self.assertEqual(M.valuation(7 ** 3 * 2, 7, 9), 3)
        self.assertEqual(M.rhs(dict(rhs=(5, -1, 1)), 7, 3), (-5 * 7) % 343)


class Machinery(unittest.TestCase):
    def test_wz(self):
        bad, points = M.wz_failures(lambda n, k: Fraction(k), lambda n, k: Fraction(-n), 6)
        self.assertEqual((bad, points), ([], 42))
        bad, _ = M.wz_failures(lambda n, k: Fraction(k), lambda n, k: Fraction(-2 * n), 6)
        self.assertEqual(len(bad), 42)

    def test_pochhammer(self):
        self.assertEqual(M.half_poch(3), Fraction(15, 8))
        self.assertEqual(M.poch(Fraction(1, 4), 2), Fraction(5, 16))
        self.assertEqual(M.poch(Fraction(-3, 2), 2), Fraction(3, 4))
        with self.assertRaises(ValueError):
            M.fact(-1)

    def test_q7(self):
        s = M.Q7(0, 1)
        sq = s * s
        self.assertEqual((sq.u, sq.v), (-7, 0))
        x = M.Q7(Fraction(3, 2), 5)
        one = x * x.inverse()
        self.assertEqual((one.u, one.v), (1, 0))
        self.assertEqual(M.difference_heads([1, 4, 9, 16]), [1, 3, 2, 0])

    def test_euler_binomial(self):
        scale = 10 ** 60
        u, v = M.euler_sum(1, ((1, 0),), (-8, 0, 1))                  # (1 + 8)^(-1/2)
        self.assertEqual(v, 0)
        self.assertLess(abs(u.numerator * scale // u.denominator - scale // 3), M.AGREE)
        u, v = M.euler_sum(1, ((1, 0),), (-1, 0, 1), K=400)           # 2^(-1/2), |w| = 1/2
        self.assertLess(abs(u.numerator * scale // u.denominator - math.isqrt(scale * scale // 2)), M.AGREE)
        u, v = M.euler_sum(1, ((1, 0), (2, 0)), (-3, 0, 1), K=800)    # sum (1 + 2n) c_n z^n, z = -3, |w| = 3/4
        z = -3.0
        want = (1 - z) ** -0.5 + 2 * z * 0.5 * (1 - z) ** -1.5
        self.assertAlmostEqual(float(u), want, places=13)

    def test_euler_complex(self):
        u, v = M.euler_sum(1, ((1, 0),), (47, 45, 128))               # (1 - z)^(-1/2) on |z| = 1
        z = complex(47, 45 * math.sqrt(7)) / 128
        want = (1 - z) ** -0.5
        self.assertAlmostEqual(float(u), want.real, places=12)
        self.assertAlmostEqual(float(v) * math.sqrt(7), want.imag, places=12)
        self.assertAlmostEqual(abs(z), 1.0, places=14)
        self.assertAlmostEqual(abs(cmath.phase(z)), math.acos(47 / 128), places=12)

    def test_direct_sum(self):
        total, terms = M.direct_sum(1, ((1, 0),), (1, 0, 4))          # (1 - 1/4)^(-1/2) = 2/sqrt 3
        self.assertAlmostEqual(float(total), 2 / math.sqrt(3), places=14)
        self.assertGreater(terms, 50)

    def test_constants(self):
        scale = 10 ** 30
        k = M.constants(scale)
        self.assertAlmostEqual(k["1/pi"] / scale, 1 / math.pi, places=12)
        self.assertAlmostEqual(k["4/pi^2"] / scale, 4 / math.pi ** 2, places=12)
        self.assertAlmostEqual(k["8/pi^2"] / scale, 8 / math.pi ** 2, places=12)
        self.assertAlmostEqual(k["sqrt7/pi"] / scale, math.sqrt(7) / math.pi, places=12)

    def test_outputs(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 64)
        self.assertRegex(M.INPUT[0], r"[A-Za-z][A-Za-z0-9_.-]{0,39}")

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


if __name__ == "__main__":
    unittest.main()
