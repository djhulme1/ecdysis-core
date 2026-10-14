"""Fukś's two-rule density classifier (ca/fuks.py, ca/fuks.c): the reader on a source built here (statements, the
printed tables, refusals); Wolfram numbering; the C program's ring step, ring runs and preimage counts on rules whose
behaviour is known by hand (identity, shifts, XOR rules, rule 0), never rules 184 and 232; the formula's arithmetic;
the seed refused. The paper's source is not read here.

Run with: python3 -m unittest discover -s tests -p test_fuks.py
"""

import importlib.util
import io
import math
import os
import shutil
import tarfile
import tempfile
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("ca_fuks", os.path.join(HERE, "..", "ca", "fuks.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


def source(tex, name="pre.tex"):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        raw = tex.encode("ascii")
        info = tarfile.TarInfo(name)
        info.size = len(raw)
        tar.addfile(info, io.BytesIO(raw))
    return buf.getvalue()


def table_tex(rule):
    parts = [f"{format(k, '03b')} \\rightarrow {(rule >> k) & 1}" for k in range(8)]
    return "\\begin{eqnarray*}\n& & " + ",\\, ".join(parts[:4]) + ", \\\\ & & " + ",\\, ".join(parts[4:]) + \
        "\n\\end{eqnarray*}\n"


class Reading(unittest.TestCase):
    def test_tables_and_numbering(self):
        tex = "Rule A: " + table_tex(110) + "text \\begin{eqnarray}x = y\\end{eqnarray} " + table_tex(30)
        got = M.tables(tex)
        self.assertEqual([M.wolfram(t) for t in got], [110, 30])
        with self.assertRaises(M.Refused):
            M.tables("\\begin{eqnarray*} 000 \\rightarrow 0, 000 \\rightarrow 1 \\end{eqnarray*}")
        with self.assertRaises(M.Refused):
            M.tables("\\begin{eqnarray*} 000 \\rightarrow 0, 001 \\rightarrow 1 \\end{eqnarray*}")

    def test_statements(self):
        tex = "\n".join(M.STATEMENTS).replace(" ", "\n  ")
        self.assertTrue(all(M.statements_found(tex).values()))
        self.assertFalse(all(M.statements_found(tex.replace("(L-1)/2", "(L-3)/2")).values()))

    def test_archive(self):
        self.assertEqual(M.tex_of(source("hello")), "hello")
        with self.assertRaises(M.Refused):
            M.tex_of(source("hello", name="other.tex"))
        with self.assertRaises(M.Refused):
            M.tex_of(b"not a tar")

    def test_hash_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, M.INPUT[0]), "wb") as fh:
                fh.write(source("x"))
            with self.assertRaises(M.Refused):
                M.read_input(d)


class Cells(unittest.TestCase):
    def test_step_cells(self):
        x, L = 0b0010110, 7
        self.assertEqual(M.step_cells(x, 204, L), x)                          # identity
        self.assertEqual(M.step_cells(x, 170, L), (x >> 1) | ((x & 1) << (L - 1)))  # each cell takes its right
        self.assertEqual(M.step_cells(x, 0, L), 0)
        self.assertEqual(M.step_cells(0b1, 90, 5), 0b10010)                  # XOR of the two neighbours

    def test_pre_cells_identity(self):
        for m in range(4):
            want = [math.comb(2 * m, j) if j <= 2 * m else 0 for j in range(2 * m + 3)]
            self.assertEqual(M.pre_cells(204, m), want)


@unittest.skipIf(shutil.which("gcc") is None, "no gcc")
class Program(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp()
        cls.exe = M.build(cls.work)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def test_step_against_cells(self):
        for rule in (90, 150, 170, 204, 240, 30, 110):
            for L in (3, 6, 11):
                for x in range(0, 1 << L, 7):
                    self.assertEqual(M.c_step(self.exe, rule, L, x), M.step_cells(x, rule, L), (rule, L, x))
        self.assertEqual(M.c_step(self.exe, 170, 6, 0b000001, 6), 0b000001)   # a full turn of the ring

    def test_ring_counts(self):
        L = 6
        r = M.ring(self.exe, 204, 0, L, 0, 1)        # unchanged, then everything to 0
        wrong = sum(math.comb(L, j) for j in range(L + 1) if 2 * j >= L)
        self.assertEqual(r["configurations"], 64)
        self.assertEqual(r["misclassified"], wrong)
        self.assertEqual(r["first"], 7)               # 0b000111: the least with three ones
        r = M.ring(self.exe, 204, 204, L, 0, 0)
        self.assertEqual(r["misclassified"], 64 - 2 - 2)   # only 000000, 111111, 010101 and 101010 pass

    def test_pre_identity(self):
        for m in range(5):
            self.assertEqual(M.c_pre(self.exe, 204, m), M.pre_cells(204, m))


class Formula(unittest.TestCase):
    def test_n_ab(self):
        self.assertEqual(M.n_ab(4, 2), math.comb(4, 3))
        self.assertEqual(M.n_ab(4, 6), 0)
        self.assertEqual(M.n_ab(4, 1), 0)

    def test_formula_counts_shape(self):
        self.assertEqual(M.formula_counts(0), [1, 0, 0])
        for m in range(1, 6):
            c = M.formula_counts(m)
            self.assertEqual(len(c), 2 * m + 3)
            self.assertEqual(c[0], 1)
            self.assertTrue(all(x == 0 for x in c[m + 1:]))

    def test_p_exact_against_fractions(self):
        for m in range(4):
            for p in (Fraction(1, 3), Fraction(3, 4)):
                direct = sum((M.n_ab(2 * m, 2 * k - 2) - M.n_ab(2 * m, 2 * k + 2)) * p ** (m - k + 1)
                             * (1 - p) ** (m + k + 1) for k in range(1, m + 2))
                self.assertEqual(M.p_exact(m, p), direct)

    def test_log_abs(self):
        self.assertAlmostEqual(M.log_abs(Fraction(-3, 7)), math.log(3 / 7))


class Verdict(unittest.TestCase):
    def test_steps(self):
        self.assertEqual([M.steps(L) for L in (2, 3, 10, 11)], [(0, 0), (0, 1), (4, 4), (4, 5)])

    def test_outputs_named(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


if __name__ == "__main__":
    unittest.main()
