"""Zudilin's supercongruences (pi/zudilin.py): the transcription of each congruence against its own TeX line (the
summand's Pochhammer symbols, polynomial, z, modulus and bound); the e-print reader and its refusals; primes and
Legendre symbols; the modular sums against exact sums on summands written here; the verdict's arithmetic on sums whose
answer is known; the inner sums for small n; the WZ check on a pair written here; and the series' constants. None of
the paper's congruences, pairs, lemmas or series is evaluated here.

Run with: python3 -m unittest discover -s tests -p test_zudilin.py
"""

import gzip
import importlib.util
import math
import os
import re
import tempfile
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pi_zudilin", os.path.join(HERE, "..", "pi", "zudilin.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

NAMES = {(1, 2): r"\frac12", (1, 4): r"\frac14", (3, 4): r"\frac34", (1, 3): r"\frac13", (2, 3): r"\frac23",
         (1, 6): r"\frac16", (5, 6): r"\frac56", (1, 8): r"\frac18", (3, 8): r"\frac38", (5, 8): r"\frac58",
         (7, 8): r"\frac78"}


def poch_tex(poch, d):
    """The summand's Pochhammer fraction as the paper writes it: runs of a symbol become a power."""
    parts, i = [], 0
    while i < len(poch):
        j = i
        while j + 1 < len(poch) and poch[j + 1] == poch[i]:
            j += 1
        entry = poch[i]
        m = entry[2] if len(entry) > 2 else 1
        sub = "_n" if m == 1 else "_{2n}"
        power = "" if j == i else f"^{j - i + 1}"
        parts.append(f"({NAMES[entry[:2]]}){sub}{power}")
        i = j + 1
    return r"\frac{" + "".join(parts) + "}{n!^" + str(d) + "}"


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
Z_TEX = {r"(-1)^n": (-1, 1), r"\frac1{4^n}": (1, 4), r"\frac{(-1)^n}{8^n}": (-1, 8), r"\frac1{64^n}": (1, 64),
         r"\frac{(-1)^n}{2^{2n}}": (-1, 4), r"\frac1{2^{4n}}": (1, 16), r"\frac1{2^{6n}}": (1, 64),
         r"\frac{(-1)^n}{80^{3n}}": (-1, 512000), r"\frac{(-1)^n}{882^{2n}}": (-1, 777924),
         r"\frac1{99^{4n}}": (1, 96059601), r"\frac{(-1)^n}{500^{2n}}": (-1, 250000),
         r"\frac{(-1)^n}{2^{10n}}": (-1, 1024), r"\frac{(-1)^n}{48^n}": (-1, 48), r"\frac1{7^{4n}}": (1, 2401),
         r"\frac1{6^{2n}}": (1, 36), r"\frac1{81^n}": (1, 81), r"\frac1{2^{10n}}": (1, 1024)}


class Transcription(unittest.TestCase):
    def all_lines(self):
        return list(M.CONGRUENCES.items()) + [("x01", M.PRINTED_X01)] + list(M.SERIES.items())

    def test_numbers(self):
        self.assertEqual([c["no"] for c in M.CONGRUENCES.values()],
                         [2, 3, 4, 5, 6, 9, 11, 12] + list(range(21, 36)))
        self.assertEqual(len(M.TESTED), 23)

    def test_modulus_and_bound(self):
        for lab, c in list(M.CONGRUENCES.items()) + [("x01", M.PRINTED_X01)]:
            with self.subTest(lab=lab):
                self.assertEqual(re.findall(r"\\pmod\{p\^(\d)\}", c["tex"]), [str(c["r"])])
                inline = re.findall(r"\$p>(\d+)\$", c["tex"])
                if inline:
                    self.assertEqual(inline, [str(c["bound"])])

    def test_summand(self):
        for lab, c in self.all_lines():
            with self.subTest(lab=lab):
                self.assertIn(poly_tex(c["poly"]), c["tex"].replace(" ", ""))
                if c.get("kind", "hyper") == "hyper":
                    self.assertIn(poch_tex(c["poch"], c["d"]), c["tex"])
                zs = [t for t in Z_TEX if t in c["tex"] and not any(t != u and t in u and u in c["tex"] for u in Z_TEX)]
                self.assertEqual([Z_TEX[t] for t in zs], [c["z"]])

    def test_right_hand_sides(self):
        for lab, c in M.CONGRUENCES.items():
            coef, D, e = c["rhs"]
            with self.subTest(lab=lab):
                power = "p" if e == 1 else f"p^{e}"
                if D is None:
                    self.assertRegex(c["tex"].replace(" ", ""), r"equiv" + (str(coef) if coef != 1 else "") + re.escape(power) + r"\\pmod")
                elif lab == "A01":
                    self.assertIn(r"\equiv(-1)^{(p-1)/2}p\pmod", c["tex"])
                else:
                    sym = (r"\frac" + str(D) + "p") if 0 < D < 10 else (r"\frac{" + str(D) + "}p")
                    self.assertIn((str(coef) if coef != 1 else "") + r"\biggl(" + sym + r"\biggr)" + power
                                  + r"\pmod", c["tex"].replace("\\equiv ", "\\equiv"))

    def test_upper_limits(self):
        for lab, c in M.CONGRUENCES.items():
            with self.subTest(lab=lab):
                want = r"\sum_{n=0}^{(p-1)/2}" if c["upper"] == "(p-1)/2" else r"\sum_{n=0}^{p-1}"
                self.assertTrue(c["tex"].startswith(want))


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
        c = M.CONGRUENCES["A01b"]
        flat = c["tex"] + " \\label{A01b} rest"
        found = M.source_checks(flat)
        self.assertTrue(found["(2) A01b"])
        self.assertFalse(found["(3) A02b"])
        self.assertFalse(M.source_checks(c["tex"] + " x \\label{A01b}")["(2) A01b"])     # text between: refused


class Arithmetic(unittest.TestCase):
    def test_primes_and_symbols(self):
        self.assertEqual(M.primes_upto(30), [2, 3, 5, 7, 11, 13, 17, 19, 23, 29])
        self.assertEqual(len(M.primes_upto(1000)), 168)
        for p in (3, 5, 7, 11, 13, 17, 19, 23):
            for D in M.LEGENDRE_D:
                self.assertEqual(M.legendre(D, p), M.legendre_count(D, p))
        self.assertEqual(M.legendre(-1, 7), -1)
        self.assertEqual(M.legendre(-3, 3), 0)

    def test_modular_against_exact(self):
        specs = [dict(no=0, kind="hyper", poch=[(1, 2)], d=1, poly=(1,), z=(1, 1), upper="p-1"),
                 dict(no=0, kind="hyper", poch=[(1, 3), (1, 2, 2)], d=2, poly=(2, 7), z=(-1, 5), upper="p-1"),
                 dict(no=0, kind="hyper", poch=[(1, 2)] * 3, d=3, poly=(1,), z=(1, 1), upper="(p-1)/2")]
        for c in specs:
            for p in (7, 11, 13):
                for R in (1, 3, 6):
                    exact = sum(M.hyper_term_exact(c, n) for n in range(M.upper_of(c, p) + 1))
                    self.assertEqual(M.hyper_sum(c, p, R), M.exact_mod(exact, p, R), (c["poch"], p, R))

    def test_refusals(self):
        c = dict(no=0, kind="hyper", poch=[(1, 3)], d=1, poly=(1,), z=(1, 1), upper="p-1")
        with self.assertRaises(M.Refused):
            M.hyper_sum(c, 3, 2)                         # the 3 of (1/3)_n is not a unit modulo 3
        with self.assertRaises(M.Refused):
            M.exact_mod(Fraction(1, 5), 5, 2)

    def test_double_sum(self):
        c = dict(no=0, kind="double", poly=(1, 1), z=(1, 9), upper="p-1")
        inner = [n * n - 3 for n in range(40)]
        for p in (5, 7, 13):
            exact = sum(Fraction(inner[n] * (n + 1), 9 ** n) for n in range(p))
            self.assertEqual(M.double_sum(c, inner, p, 4), M.exact_mod(exact, p, 4))

    def test_verdict_arithmetic(self):
        ones = dict(no=0, kind="hyper", poch=[], d=0, poly=(1,), z=(1, 1), upper="p-1", rhs=(1, None, 1), r=2,
                    bound=2)
        for p in (3, 5, 7):
            self.assertEqual(M.check(ones, p), (True, 2 + M.EXTRA))   # the sum of p ones is exactly p
        twice = dict(ones, rhs=(2, None, 1))
        self.assertEqual(M.check(twice, 7), (False, 1))               # p - 2p is divisible by p only once
        self.assertEqual(M.valuation(7 ** 3 * 2, 7, 9), 3)
        self.assertEqual(M.rhs(dict(rhs=(5, -1, 1)), 7, 3), (-5 * 7) % 343)

    def test_inner_values(self):
        for name, known in M.INNER_KNOWN.items():
            self.assertEqual(tuple(M.inner_values(name, len(known))), known)


class Machinery(unittest.TestCase):
    def test_wz(self):
        bad, points = M.wz_failures(lambda n, k: Fraction(k), lambda n, k: Fraction(-n), 6)
        self.assertEqual((bad, points), ([], 21))
        bad, _ = M.wz_failures(lambda n, k: Fraction(k), lambda n, k: Fraction(-2 * n), 6)
        self.assertEqual(len(bad), 21)

    def test_pochhammer(self):
        self.assertEqual(M.half_poch(3), Fraction(15, 8))
        self.assertEqual(M.poch(Fraction(1, 4), 2), Fraction(5, 16))
        with self.assertRaises(ValueError):
            M.fact(-1)

    def test_constants(self):
        scale = 10 ** 30
        self.assertAlmostEqual(M.series_value("4/pi", scale) / scale, 4 / math.pi, places=12)
        self.assertAlmostEqual(M.series_value("2sqrt2/pi", scale) / scale, 2 * math.sqrt(2) / math.pi, places=12)
        self.assertAlmostEqual(M.series_value("32/pi^2", scale) / scale, 32 / math.pi ** 2, places=12)

    def test_outputs(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


if __name__ == "__main__":
    unittest.main()
