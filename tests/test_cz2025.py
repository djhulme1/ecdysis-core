"""Cohen & Zudilin's continued fractions (pi/cz2025.py): the readers and their refusals on tables written here, the
polynomial and fraction parsers, the convergents, the rate, the Kronecker symbol and class numbers, the denominator
machinery of Theorem 7.3 and the explicit formula of Theorem 7.1 on fractions of the family that are not in the paper's
tables, and the Dedekind eta. Nothing here evaluates a row of the paper's Tables 1 or 2.

Run with: python3 -m unittest tests.test_cz2025 (in the pinned scipy-notebook image)
"""

import importlib.util
import io
import math
import os
import random
import tarfile
import unittest
from fractions import Fraction

import mpmath

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pi_cz2025", os.path.join(HERE, "..", "pi", "cz2025.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


def fake_row(tag, L="\\CS(-3)", a1="1", A="100", b0="1", K="1", D="6", mu="-"):
    return f"    {tag} & ${L}$ & ${a1}$ & ${A}$ & ${b0}$ & ${K}$ & ${D}$ & ${mu}$ \\\\"


def fake_table(label, rows):
    return ("\\begin{table}[H]\n  \\caption{x}\n  \\label{" + label + "}\n\\begin{tabular}{|c|}\n    \\hline\n"
            "    Tag & x \\\\\n    \\hline\\hline\n" + "\n".join(rows) + "\n    \\hline\n  \\end{tabular}\n\\end{table}\n")


def family(A, K, D, a1, b0):
    return {"tag": "(t)", "A": A, "K": K, "D": D, "a1": Fraction(a1), "b0": Fraction(b0)}


class Parsers(unittest.TestCase):
    def test_polynomials(self):
        self.assertEqual(M.poly_parse("253(2n-1)"), {1: 506, 0: -253})
        self.assertEqual(M.poly_parse("-(9n^2-1)"), {2: -9, 0: 1})
        p = M.poly_parse("-(2n+1)^4(3n+1)(3n+2)")
        self.assertEqual(max(p), 6)
        self.assertEqual(p[6], -16 * 9)
        self.assertEqual(M.poly_eval(p, 1), -(3 ** 4) * 4 * 5)
        self.assertEqual(M.poly_parse("688n^4+200n^2+3"), {4: 688, 2: 200, 0: 3})
        self.assertEqual(M.poly_parse("-16(2n+1)^{6}(4n+1)(4n+3)")[8], -16 * 64 * 16)
        for bad in ("2n+", "(2n", "2x", "n^"):
            with self.assertRaises((M.Refused, IndexError, ValueError)):
                M.poly_parse(bad)

    def test_fractions_and_limits(self):
        a0, init, ap, b0, bp = M.parse_cf("[[7/2,11,5(3n-2)],[-4,-(n^2-1)]]")
        self.assertEqual((a0, init, b0), (Fraction(7, 2), [11], -4))
        self.assertEqual(ap, {1: 15, 0: -10})
        a0, init, ap, b0, bp = M.parse_cf("[[0,2n+1],[3,n^2]]")
        self.assertEqual(init, [])
        self.assertEqual(M.parse_limit("$2^{1/3}3^{1/2}\\CS(-3)$"), ([(2, Fraction(1, 3)), (3, Fraction(1, 2))], -3))
        self.assertEqual(M.parse_limit("$5^{-1/4}\\CS(-4)$"), ([(5, Fraction(-1, 4))], -4))
        with self.assertRaises(M.Refused):
            M.parse_limit("$\\CS(4)$")
        spec = M.parse_general_limit("$2^{1/3}(2+\\sqrt{3})\\CS(-3)$")
        self.assertEqual(spec, ([(2, Fraction(1, 3))], [(2, 3)], -3, 1))
        self.assertEqual(M.parse_general_limit("$(12^{1/4}\\CS(-4))^2$")[3], 2)
        self.assertEqual(M.parse_general_limit("$\\CS(-8)^2$")[2:], (-8, 2))
        with mpmath.workdps(30):
            self.assertAlmostEqual(float(M.parse_rate("$-((1+\\sqrt{5})/2)^{10}$")), -((1 + 5 ** 0.5) / 2) ** 10)
            self.assertAlmostEqual(float(M.parse_rate("$-(2+\\sqrt{3})^3$")), -(2 + 3 ** 0.5) ** 3)
            self.assertEqual(M.parse_rate("$-16/9$"), mpmath.mpf(-16) / 9)


class Readers(unittest.TestCase):
    def test_table2_reader_and_refusals(self):
        rows = [fake_row(f"(1.{k})", mu=("2.5" if k % 2 else "-")) for k in range(1, 40)]
        t = M.read_table2(fake_table("tableall", rows))
        self.assertEqual(len(t), 39)
        self.assertEqual(t[0]["mu"], "2.5")
        self.assertIsNone(t[1]["mu"])
        with self.assertRaises(M.Refused):
            M.read_table2(fake_table("tableall", rows[:38]))
        bad = rows[:]
        bad[3] = fake_row("(1.4)", L="\\CS(-3)\\pi")
        with self.assertRaises(M.Refused):
            M.read_table2(fake_table("tableall", bad))
        bad = rows[:]
        bad[5] = bad[5].replace(" \\\\", "")
        with self.assertRaises(M.Refused):
            M.read_table2(fake_table("tableall", bad))

    def test_tex_reader(self):
        def tar(names):
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w:gz") as tf:
                for n in names:
                    data = b"\\documentclass{article}" if n.endswith(".tex") else b"{}"
                    info = tarfile.TarInfo(n)
                    info.size = len(data)
                    tf.addfile(info, io.BytesIO(data))
            return buf.getvalue()
        self.assertTrue(M.read_tex(tar(["00README.json", M.TEX_NAME])).startswith("\\documentclass"))
        for names in (["00README.json", M.TEX_NAME, "x.sty"], [M.TEX_NAME]):
            with self.assertRaises(M.Refused):
                M.read_tex(tar(names))
        with self.assertRaises(M.Refused):
            M.read_tex(b"not a tar")


class Fractions(unittest.TestCase):
    def test_classical_fractions(self):
        with mpmath.workdps(60):
            ps, qs = M.convergents(Fraction(1), [], {0: Fraction(2)}, Fraction(1), {0: Fraction(1)}, 90)
            self.assertLess(abs(M.ratio(ps[-1], qs[-1]) - mpmath.sqrt(2)), mpmath.mpf(10) ** -50)
            ps, qs = M.convergents(Fraction(0), [], {1: Fraction(1)}, Fraction(1), {1: Fraction(1)}, 60)
            self.assertLess(abs(M.ratio(ps[-1], qs[-1]) - (mpmath.e - 2)), mpmath.mpf(10) ** -50)

    def test_family_against_general_and_backward(self):
        for A, K, D, a1, b0 in ((100, 1, 6, 3, 7), (77, -2, 4, 5, 2), (40, 3, 3, Fraction(1, 2), 9), (30, 1, 2, 2, 5)):
            row = family(A, K, D, a1, b0)
            p, q = M.family_convergents(row, 30)
            cf = (Fraction(0), [Fraction(a1)], {1: Fraction(A), 0: Fraction(-A)}, Fraction(b0),
                  {k: -K * v for k, v in M.poly_parse(f"({D}n-1)({D}n-{D - 1})").items()})
            gp, gq = M.convergents(*cf, 30)
            for n in range(1, 31):
                self.assertEqual(Fraction(p[n], q[n]), Fraction(gp[n], gq[n]))
            with mpmath.workdps(60):
                self.assertLess(abs(M.ratio(p[30], q[30]) - M.backward(*cf, 30)), mpmath.mpf(10) ** -40)

    def test_rate(self):
        with mpmath.workdps(40):
            E = M.rate(100, 1, 6)
            R = (100 + mpmath.sqrt(100 ** 2 - 4 * 36)) / 2
            self.assertLess(abs(E - R * R / 36), mpmath.mpf(10) ** -35)
            self.assertIsNone(M.rate(10, 7, 2))                    # A^2 - 4KD^2 < 0
            self.assertEqual(M.depth_for(mpmath.mpf(10), 230), 230)
        with mpmath.workdps(150):
            E = M.rate(100, 1, 6)
            p, q = M.family_convergents(family(100, 1, 6, 1, 1), 40)
            L = M.ratio(p[40], q[40])
            r1 = (L - M.ratio(p[20], q[20])) / (L - M.ratio(p[21], q[21]))
            self.assertLess(abs(r1 / E - 1), 0.2)


class Arithmetic(unittest.TestCase):
    def test_kronecker_and_class_numbers(self):
        for D in (-20, -31, -56, -104, -3, -4):
            for p in M.primes_upto(150)[1:]:
                e = pow(D % p, (p - 1) // 2, p)
                self.assertEqual(M.kronecker(D, p), 0 if D % p == 0 else (1 if e == 1 else -1))
        self.assertEqual(M.kronecker(-20, 2), 0)
        self.assertEqual(M.kronecker(-31, 2), 1)          # -31 = 1 mod 8
        self.assertEqual(M.kronecker(-35, 2), -1)         # -35 = 5 mod 8
        self.assertEqual([M.class_number(d) for d in (-3, -4, -7, -20, -56, -104, -31)], [1, 1, 1, 2, 4, 6, 3])

    def test_cs_closed_forms(self):
        with mpmath.workdps(50):
            self.assertLess(abs(M.cs(-4) - mpmath.gamma(0.25) ** 4 / (2 * mpmath.pi ** 2)), mpmath.mpf(10) ** -45)
            self.assertLess(abs(M.eta_abs4(-4) - mpmath.gamma(0.25) ** 4 / (16 * mpmath.pi ** 3)), mpmath.mpf(10) ** -45)

    def test_denominators_on_other_members(self):
        for A, K, D in ((500, 1, 6), (91, 7, 3), (64, 2, 4), (36, -3, 3), (50, 5, 2)):
            row = family(A, K, D, 1, 1)
            p, q = M.family_convergents(row, 62)
            ok, first, extra = M.denominators(row, p, q, n_max=60)
            self.assertTrue(ok, (A, K, D, first))
            ok, first, _ = M.denominators(row, p, q, n_max=60, use_dstar=False)
            self.assertFalse(ok)

    def test_prime_set(self):
        primes = M.primes_upto(200)
        self.assertEqual(M.prime_set(2, 100, primes), [])
        for D in (3, 4, 6):
            for n in (40, 97, 150):
                for p in M.prime_set(D, n, primes):
                    self.assertEqual(p % D, D - 1)
                    self.assertTrue(p * p > 2 * D * n and p <= n)
        self.assertTrue(set(M.prime_set(6, 150, primes)) <= set(M.prime_set(6, 150, primes, relaxed=True)))

    def test_theorem_71_on_other_parameters(self):
        rng = random.Random(4)
        for _ in range(5):
            B = Fraction(1, rng.choice((2, 3, 4, 6)))
            Z = Fraction(rng.randint(5, 60), rng.choice((1, 2, 3)))
            K = Fraction(rng.choice((-3, -1, 2, 5)))
            v0, v1 = Fraction(rng.randint(0, 5)), Fraction(rng.randint(1, 9))
            rec = M.recursion_v(14, B, Z, K, v0, v1)
            for n in range(14):
                self.assertEqual(M.explicit_v(n, B, Z, K, v0, v1), rec[n + 1])

    def test_log_d_against_direct_lcm(self):
        with mpmath.workdps(30):
            for D, n in ((6, 50), (4, 37), (3, 61), (2, 45)):
                lcm = 1
                for j in range(1, n + 1):
                    lcm = math.lcm(lcm, D * j + 1)
                ld, lds = M.log_d(D, n)
                self.assertLess(abs(ld - mpmath.log(lcm)), mpmath.mpf(10) ** -20)
                self.assertLess(abs(lds - mpmath.log(M.dstar(D, n, M.primes_upto(n + 1)))), mpmath.mpf(10) ** -20)
            self.assertEqual(M.m_exact(5), Fraction(125, 48))
            m5 = mpmath.mpf(M.m_exact(5).numerator) / M.m_exact(5).denominator
            self.assertLess(abs(M.m_star_general(5) - (m5 - (mpmath.pi * mpmath.cot(mpmath.pi / 5) + mpmath.mpf(5) / 4 - 5) / 4)), 1e-25)

    def test_printed_relation(self):
        with mpmath.workdps(30):
            self.assertEqual(M.printed_relation(mpmath.mpf("5.5481"), "5.548"), "rounded/cut")
            self.assertEqual(M.printed_relation(mpmath.mpf("5.5486"), "5.548"), "cut")
            self.assertEqual(M.printed_relation(mpmath.mpf("5.5476"), "5.548"), "rounded/up")
            self.assertEqual(M.printed_relation(mpmath.mpf("5.51"), "5.548"), "off")


class Run(unittest.TestCase):
    def test_bad_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("x")


if __name__ == "__main__":
    unittest.main()
