"""Saha and Sinha's parametric series for pi and zeta(2) (pi/saha.py): the reading of the e-print (its hash, its TeX
file, comments and whitespace, each formula and sentence refused when altered or commented out); the rising factorial
and each series' first terms on hand values; Machin's pi; the least stable partial sum; the two classical error
expansions against hand sums and the terms they need; the verdict at and beside each condition; the known-answer
controls; the seed refused; and, with the e-print at inputs/ (or SAHA_INPUTS), that its source holds both series and
both sentences as read, which computes no partial sum of either series.

Run with: python3 -m unittest discover -s tests -p test_saha.py
"""

import decimal
import hashlib
import importlib.util
import io
import os
import tarfile
import tempfile
import unittest
from decimal import Decimal
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pi_saha", os.path.join(HERE, "..", "pi", "saha.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

INPUTS = os.environ.get("SAHA_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = all(os.path.isfile(os.path.join(INPUTS, name)) for name, _ in M.INPUTS.values())


def setUpModule():
    decimal.getcontext().prec = M.PRECISION


def targz(files):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for name, text in files.items():
            data = text.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
    return buf.getvalue()


# The two formulas and sentences as the e-print sets them: a tab, a doubled space, a line break, a comment.
GOOD = ("\\begin{eqnarray}\n\t" + M.FORMULAS[0] + "\\nonumber\n\\end{eqnarray}\n" + M.SENTENCES[0] + "\n%\n"
        "\\begin{equation}\n\t" + M.FORMULAS[1].replace("\\lambda n^2", "\\lambda  n^2") + "\n\\end{equation}\n"
        + M.SENTENCES[1].replace(" 15 decimal", "\n15 decimal") + " % a comment\n")


class Source(unittest.TestCase):
    def test_flatten(self):
        self.assertEqual(M.flatten("a % note\nb\\% c\n\t d"), "a b\\% c d")

    def test_good_source_passes(self):
        M.check_source(GOOD)

    def test_each_alteration_is_refused(self):
        bad = [GOOD.replace("\\pi=4+", "\\pi=3+"), GOOD.replace("(2 \\lambda +n)", "(2 \\lambda -n)"),
               GOOD.replace("takes 30 terms", "takes 20 terms"), GOOD.replace("only 40 terms", "only 45 terms"),
               GOOD.replace("\t\\pi=4+", "%\\pi=4+"), GOOD.replace("Putting $\\lambda=41.5$", "%Putting $\\lambda=41.5$")]
        for tex in bad:
            with self.subTest(tex=tex[:60]), self.assertRaises(M.Refused):
                M.check_source(tex)

    def test_tar(self):
        self.assertEqual(M.tex_of(targz({M.TEX: GOOD, "fig.pdf": "x"})), GOOD)
        with self.assertRaises(M.Refused):
            M.tex_of(targz({"main.tex": GOOD}))

    def test_hash(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x")
            with open(path, "wb") as fh:
                fh.write(b"eprint")
            self.assertEqual(M.read_bytes(path, hashlib.sha256(b"eprint").hexdigest()), b"eprint")
            with self.assertRaises(M.Refused):
                M.read_bytes(path, hashlib.sha256(b"other").hexdigest())


class Terms(unittest.TestCase):
    def test_rising_factorial(self):
        self.assertEqual(M.poch(Fraction(1, 2), 3), Fraction(15, 8))
        self.assertEqual(M.poch(Fraction(7, 3), 0), 1)
        self.assertEqual(M.poch(Fraction(-3), 4), 0)                     # (-3)(-2)(-1)(0)
        self.assertEqual(M.poch(Fraction(1), 5), 120)

    def test_pi_terms_by_hand(self):
        lam = Fraction(10)
        self.assertEqual(M.pi_term(1, lam), Fraction(1, 11) - Fraction(4, 3))                    # (a)_0 = 1
        self.assertEqual(M.pi_term(2, lam), Fraction(1, 2) * (Fraction(1, 12) - Fraction(4, 5)) * (Fraction(25, 48) - 2))
        self.assertEqual(M.pi_term(2, lam), Fraction(3053, 5760))

    def test_zeta_terms_by_hand(self):
        lam = Fraction(10)
        self.assertEqual(M.zeta_term(1, lam), Fraction(21, 11))                                   # (2 lam + 1)/(1 + lam)
        self.assertEqual(M.zeta_term(2, lam), Fraction(-11, 36))


class Arithmetic(unittest.TestCase):
    def test_machin(self):
        self.assertEqual(str(+M.machin_pi(60))[:52], M.PI50)

    def test_partial_sums(self):
        sums = M.partial_sums(lambda n, lam: Fraction(lam, n * (n + 1)), Fraction(1), 2, 3)
        self.assertEqual(sums, [Decimal(2), Decimal("2.5"), Decimal(2) + Decimal(2) / 3, Decimal("2.75")])

    def test_least_stable(self):
        sums = [Decimal(v) for v in ("10", "5", "1.2", "1.05", "1.01", "1.001", "1.0001", "1.00001", "1.000001")]
        self.assertEqual(M.least_stable(sums, Decimal(1), Fraction(1, 50), window=2), 4)
        self.assertIsNone(M.least_stable(sums, Decimal(1), Fraction(1, 10 ** 9), window=2))
        back = [Decimal(v) for v in ("5", "1.001", "3", "1.001", "1.001", "1.001")]
        self.assertEqual(M.least_stable(back, Decimal(1), Fraction(1, 100), window=2), 3)   # in, out, in again

    def test_classical_expansions_against_hand_sums(self):
        pi = M.machin_pi(M.PRECISION)
        madhava10 = 4 * sum(Fraction((-1) ** k, 2 * k + 1) for k in range(10))
        self.assertLess(abs(abs(pi - M.dec(madhava10)) - M.madhava_error(10)), Decimal("1e-9"))
        basel10 = sum(Fraction(1, k * k) for k in range(1, 11))
        self.assertLess(abs((pi * pi / 6 - M.dec(basel10)) - M.basel_error(10)), Decimal("1e-9"))

    def test_terms_needed(self):
        self.assertEqual(M.terms_needed(lambda n: Decimal(1) / n, Decimal("0.01")), 101)
        self.assertEqual(M.terms_needed(lambda n: Decimal(1) / n, Decimal("0.5")), 3)


class Verdict(unittest.TestCase):
    def test_at_and_beside_each_condition(self):
        err = {lam: Decimal("4.99e-11") for lam in M.LAMBDAS}
        zerr = Decimal("4.99e-16")
        self.assertTrue(all(M.conditions(err, zerr).values()))
        self.assertEqual(len(M.conditions(err, zerr)), 11)
        for lam in M.LAMBDAS:
            with self.subTest(lam=lam):
                self.assertEqual(sum(M.conditions({**err, lam: Decimal("5e-11")}, zerr).values()), 10)
        self.assertEqual(sum(M.conditions(err, Decimal("5e-16")).values()), 10)


class Controls(unittest.TestCase):
    def test_known_answers(self):
        got = M.controls_known(M.machin_pi(M.PRECISION))
        self.assertEqual(len(got), 6)
        self.assertTrue(all(got.values()), got)


class Seed(unittest.TestCase):
    def test_refuses_a_bad_seed(self):
        with self.assertRaises(M.Refused):
            M.run("xyz", inputs=os.path.join(HERE, "_never"), results=os.path.join(HERE, "_never"))


@unittest.skipUnless(HAVE, "the e-print is not at inputs/ (or SAHA_INPUTS)")
class Eprint(unittest.TestCase):
    def test_source_holds_both_series_and_sentences(self):
        name, sha = M.INPUTS["eprint"]
        M.check_source(M.tex_of(M.read_bytes(os.path.join(INPUTS, name), sha)))


if __name__ == "__main__":
    unittest.main()
