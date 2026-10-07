"""The zeta digits check on small cases: the paper's formulas read and anything else refused, the extraction against
exact rational values at low places, Koecher's series, the seeded places, and the series program when gcc and GMP
are present (in the pinned image); with the paper's source (at inputs/ or in ZETA_INPUTS), also its formulas and
strings as read.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("zeta_check", os.path.join(HERE, "..", "zeta", "check.py"))
Z = importlib.util.module_from_spec(_spec)
sys.modules["zeta_check"] = Z                     # the extraction's worker processes find their function by name
_spec.loader.exec_module(Z)

Z3 = (3, 7, [(6, 1, (1, -7, -1, 10, -1, -7, 1, 0)), (4, 3, (1, 1, -1, -2, -1, 1, 1, 0))])
Z5 = (11, 62651, [(9, 1, (31, -1614, -31, -6212, -31, -1614, 31, 74552)), (7, 3, (173, 284, -173, -457, -173, 284, 173, -111)),
                  (-738, 5, (1, 0, -1, -1, -1, 0, 1, 1))])


def exact_hex(f, n, ndig, terms=None):
    """The formula's value, summed in exact rationals until the remainder is far below 16^-ndig: '1' + digits."""
    s, D, parts = f
    total = Fraction(0)
    K = terms or (8 * ndig + 64)
    for c, p, a in parts:
        total += c * sum(Fraction(a[(k - 1) % 8], 2 ** ((p * k + p) // 2) * k ** n) for k in range(1, K))
    v = total * 2 ** s / D
    return format(int(v * 16 ** ndig), "X")


def fake_tex(z3="\\lambda(3)=\\dfrac78\\zeta(3)&=&\n6\\,S_{3,1}(1,-7,-1,10,-1,-7,1,0)\\nonumber\\\\\n&&{}+4\\,S_{3,3}(1,1,-1,-2,-1,1,1,0)",
             z5="\\dfrac{62651}{2048}\\zeta(5)&=&\n9\\,S_{5,1}(31,-1614,-31,-6212,-31,-1614,31,74552)\\nonumber\\\\\n"
                "&&{}+7\\,S_{5,3}(173,284,-173,-457,-173,284,173,-111)\\nonumber\\\\\n&&{}-738\\,S_{5,5}(1,0,-1,-1,-1,0,1,1)\\,.",
             strings=("CDA018F4E167F435B2AB045FB045A42F86BED12EF82BE2E1C6ECD305E92C5E4B",
                      "F7A15E1277F7B2C04106F04B05C48AC71ACECAB14D555FDA6E5E1EC299535511")):
    return ("\\begin{equation}\nS_{n,p}(a_1\\ldots a_8):=\\sum_{k>0}\\frac{a_k}{2^{\\lfloor\n\\frac{pk+p}{2}\\rfloor}k^n}\\label{S}\n"
            "\\end{equation}\n\\begin{eqnarray}\nx&=&y\\label{l3}\\\\\n" + z3 + "\\label{z3}\n\\end{eqnarray}\n"
            "\\begin{eqnarray}\n" + z5 + "\\label{z5}\n\\end{eqnarray}\n\\section{Computation of digits}\n"
            "The 64 hexadecimal digits of $\\zeta(3)$ that begin at the\n10,000,000th place were computed to be\n"
            "$${\\tt\n" + strings[0] + "\n}\\ldots$$\nand for $\\zeta(5)$ $${\\tt\n" + strings[1] + "\n}\\ldots$$\n")


class Reading(unittest.TestCase):
    def test_the_formulas_and_strings_as_written(self):
        pp = Z.paper(fake_tex())
        self.assertEqual(pp["z3"], Z3)
        self.assertEqual(pp["z5"], Z5)
        self.assertEqual(pp["reported"][0], 10_000_000)
        self.assertEqual(Z.describe("z5", 5, pp["z5"]), "z5: 62651/2048 zeta(5) = 9 S51 + 7 S53 - 738 S55")

    def test_anything_else_is_refused(self):
        bad = [
            fake_tex(z3="\\lambda(3)=\\dfrac78\\zeta(3)&=&6\\,S_{3,1}(1,-7,-1,10,-1,-7,1)"),                # 7 values
            fake_tex(z3="\\lambda(3)=\\dfrac78\\zeta(3)&=&6\\,S_{4,1}(1,-7,-1,10,-1,-7,1,0)"),              # wrong n
            fake_tex(z3="\\lambda(3)=\\dfrac73\\zeta(3)&=&6\\,S_{3,1}(1,-7,-1,10,-1,-7,1,0)"),              # 3 not 2^s
            fake_tex(z3="\\lambda(3)=\\dfrac78\\zeta(3)&=&6\\,S_{3,1}(1,-7,-1,10,-1,-7,1,0)+\\pi^3"),       # extra term
            fake_tex(strings=("CDA018F4", "F7A15E12")),                                                  # short strings
            fake_tex().replace("10,000,000th place", "10,000,001st place"),
            fake_tex().replace("\\lfloor", "\\lceil"),
        ]
        for tex in bad:
            with self.subTest(tex=tex[-120:]), self.assertRaises(Z.Refused):
                Z.paper(tex)


class Extraction(unittest.TestCase):
    def test_low_places_match_exact_rationals(self):
        for f, n in ((Z3, 3), (Z5, 5)):
            full = exact_hex(f, n, 120)
            for d in (1, 2, 17, 40):
                with self.subTest(n=n, d=d):
                    digits, safe = Z.hex_digits(f, n, d, 64, Z.PREC, 1)
                    self.assertTrue(safe)
                    self.assertEqual(digits, full[d:d + 64])

    def test_two_processes_give_the_same_bits(self):
        old = Z.CHUNK
        try:
            Z.CHUNK = 50                                  # many chunks even at a small place
            self.assertEqual(Z.frac_bits(Z5, 5, 300, Z.PREC, 2), Z.frac_bits(Z5, 5, 300, Z.PREC, 1))
        finally:
            Z.CHUNK = old

    def test_known_leading_digits(self):
        # zeta(3) = 1.33BA004F00621383..., zeta(5) = 1.097418ECA7CCDB7A... (hexadecimal)
        self.assertTrue(Z.hex_digits(Z3, 3, 1, 16, Z.PREC, 1)[0] == "33BA004F00621383")
        self.assertTrue(Z.hex_digits(Z5, 5, 1, 16, Z.PREC, 1)[0] == "097418ECA7CCDB7A")


class Independent(unittest.TestCase):
    def test_koecher_series_agrees_with_the_formula(self):
        k5, terms = Z.koecher_zeta5_hex(300)
        self.assertTrue(k5.startswith("1097418ECA7CCDB7A"))
        self.assertGreater(terms, 600)
        for d in (1, 150, 236):
            self.assertEqual(k5[d:d + 64], Z.hex_digits(Z5, 5, d, 64, Z.PREC, 1)[0])

    def test_seeded_places(self):
        a, b = Z.low_places("a" * 64), Z.low_places("b" * 64)
        self.assertEqual(a, Z.low_places("a" * 64))
        self.assertNotEqual(a, b)
        self.assertEqual(a[0], 1)
        self.assertTrue(all(1 <= p <= Z.MAX_LOW_PLACE for p in a))

    @unittest.skipUnless(shutil.which("gcc") and (os.path.exists("/usr/include/gmp.h")
                                                   or os.path.exists("/usr/include/x86_64-linux-gnu/gmp.h")),
                         "gcc and GMP are not here (they are in the pinned image)")
    def test_series_program(self):
        with tempfile.TemporaryDirectory() as d:
            exe = Z.build_az(d)
            got = Z.az_digits(exe, 2000, [1, 2, 1000])
            self.assertEqual(got[1][0], Z.hex_digits(Z3, 3, 1, 64, Z.PREC, 1)[0])
            self.assertEqual(got[1000][0], Z.hex_digits(Z3, 3, 1000, 64, Z.PREC, 1)[0])
            with self.assertRaises(subprocess.CalledProcessError):
                Z.az_digits(exe, 100, [50])               # a place that does not fit is refused


def inputs_dir():
    d = os.environ.get("ZETA_INPUTS") or os.path.join(HERE, "..", "inputs")
    return d if os.path.isfile(os.path.join(d, Z.INPUT[0])) else None


@unittest.skipUnless(inputs_dir(), "the paper's source is not at inputs/ (or ZETA_INPUTS)")
class ThePaper(unittest.TestCase):
    def test_as_read(self):
        pp = Z.paper(Z.load(inputs_dir()))
        self.assertEqual(pp["z3"], Z3)
        self.assertEqual(pp["z5"], Z5)
        self.assertEqual(pp["reported"], (10_000_000, "CDA018F4E167F435B2AB045FB045A42F86BED12EF82BE2E1C6ECD305E92C5E4B",
                                          "F7A15E1277F7B2C04106F04B05C48AC71ACECAB14D555FDA6E5E1EC299535511"))

    def test_a_changed_input_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, Z.INPUT[0]), "wb") as f:
                f.write(b"\x1f\x8b" + b"x" * (Z.INPUT[2] - 2))
            with self.assertRaises(Z.Refused):
                Z.load(d)


if __name__ == "__main__":
    unittest.main()
