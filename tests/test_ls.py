"""Lagarias & Shor's cube tilings of R^10 and R^12 (keller/ls.py): the reader on a TeX written here in the e-print's
markup with other tables; the block substitution; the clique, cover and facet checks on tilings whose answers are
known (lattice tilings, a plane tiling with shifted columns, broken sets); and the statements' helpers. The paper's own
tables are not built here.

Run with: python3 -m unittest tests.test_ls
"""

import gzip
import importlib.util
import itertools
import os
import tempfile
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("keller_ls", os.path.join(HERE, "..", "keller", "ls.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

TEX = r"""
\midinsert \tableS \toptablecaption{{\smc Table 1.} \rm Clique $\scr T$ in $G_3$.}
\format\cmath&\cmath&\cmath\endformat \ruleh
1&1&1\\ 3&0'&2\\ 0'&2&3\\ 2&2&0\\ 0&0&0\\ 1&0&3\\ 3&3&3\\2&0'&1
\endtableS \endinsert
as listed in Table 2. and Table 1, again
\midinsert \tableS \toptablecaption{{\smc Table 2.} \rm Blocks used in constructions.}
\format\cmath&\cmath&\cmath&\cmath&\cmath&\cmath\endformat
\tch\cmath{S_0}&\tch\cmath{S_0'}&\tch \cmath{S_2}&\tch\cmath{S_1}
&\tch\cmath{S'_1}&\tch\cmath{S_3}\\ \ruleh
1111&2222&3333&0000&0101&1212\\
1100&2200&&0011&0110&\\
1010&2020&&0001&0111&
\endtableS \endinsert
Now regard $S_2$ as being $$ \matrix 3&3&3&3\\ 3&1'&3&3\\ 3&3&0'&3\\ 3&0'&3&3 \endmatrix $$
"""


class Reading(unittest.TestCase):
    def setUp(self):
        self.text = " ".join(TEX.split())

    def test_tables(self):
        t1 = M.read_table1(self.text)
        self.assertEqual(len(t1), 8)
        self.assertEqual(t1[0], ("1", "1", "1"))
        self.assertEqual(t1[1], ("3", "0'", "2"))
        self.assertEqual(t1[7], ("2", "0'", "1"))

    def test_table1_needs_eight_rows(self):
        with self.assertRaises(M.Refused):
            M.read_table1(self.text.replace("\\\\2&0'&1", ""))
        with self.assertRaises(M.Refused):
            M.read_table1(self.text.replace("3&3&3", "3&3&4"))

    def test_table2(self):
        sets = M.read_table2(self.text)
        self.assertEqual(sets["0"], [(1, 1, 1, 1), (1, 1, 0, 0), (1, 0, 1, 0)])
        self.assertEqual(sets["2"], [(3, 3, 3, 3)])
        self.assertEqual(sets["1'"], [(0, 1, 0, 1), (0, 1, 1, 0), (0, 1, 1, 1)])
        self.assertEqual(sets["3"], [(1, 2, 1, 2)])

    def test_primed(self):
        rows = M.read_primed(self.text)
        self.assertEqual(rows[1], ("3", "1'", "3", "3"))
        with self.assertRaises(M.Refused):
            M.read_primed(self.text.replace("\\\\ 3&0'&3&3", ""))

    def test_anchor_once(self):
        with self.assertRaises(M.Refused):
            M.one("abc abc", "abc")
        self.assertEqual(M.one("xabc", "abc"), 1)

    def test_words(self):
        self.assertEqual(M.parse_word("20'3"), ("2", "0'", "3"))
        self.assertEqual(M.parse_word("1'0"), ("1'", "0"))
        with self.assertRaises(M.Refused):
            M.parse_word("2x")

    def test_load_refuses_other_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, M.INPUT[0]), "wb") as fh:
                fh.write(gzip.compress(TEX.encode("ascii")))
            with self.assertRaises(M.Refused):
                M.load(d)

    def test_tex_of(self):
        self.assertEqual(M.tex_of(gzip.compress(b"a  b\n c")), "a b c")
        with self.assertRaises(M.Refused):
            M.tex_of(b"not gzip")


class Construction(unittest.TestCase):
    def test_substitute(self):
        blocks = {"0": [(0, 0), (2, 2)], "1": [(1, 3)]}
        self.assertEqual(M.substitute([5, "0", "1"], blocks), [(5, 0, 0, 1, 3), (5, 2, 2, 1, 3)])
        self.assertEqual(len(M.substitute(["0", "0", "1"], blocks)), 4)

    def test_build12_and_build10_shapes(self):
        blocks = {s: [(i, i, i, i)] for i, s in enumerate(M.SYMBOLS)}
        blocks["0"] = [(0, 0, 0, 0), (2, 2, 2, 2)]
        t1 = [("0", "1", "2")] * 8
        self.assertEqual(M.build12(t1, blocks).shape, (16, 12))
        primed = [("2", "0'", "1'", "3")]
        self.assertEqual(M.build10(blocks, primed).shape, (6, 10))


class Checks(unittest.TestCase):
    def lattice(self, n):
        return np.array(list(itertools.product((0, 2), repeat=n)), dtype=np.int64)

    def test_lattice(self):
        for n in (2, 3, 5):
            V = self.lattice(n)
            cond, r = M.check(V, n)
            self.assertTrue(cond[f"n = {n}: 2^{n} distinct vectors in {{0,1,2,3}}^{n}"])
            self.assertTrue(cond[f"n = {n}: every unit cell covered exactly once"])
            self.assertFalse(cond[f"n = {n}: a clique in G*_{n}"])
            self.assertEqual(r["facets"], 2 ** n * n)
            self.assertEqual(r["facets"], 2 * r["pairs"]["facet_pairs"])

    def test_shifted_columns(self):
        V = np.array([(0, 0), (2, 1), (0, 2), (2, 3)], dtype=np.int64)
        cond, r = M.check(V, 2)
        self.assertTrue(cond["n = 2: every unit cell covered exactly once"])
        self.assertEqual(r["pairs"]["nonadjacent"], 2)
        self.assertEqual(r["pairs"]["no_a"], 0)
        self.assertEqual(r["facets"], 4)

    def test_broken(self):
        V = self.lattice(3)
        cond, r = M.check(V[1:], 3)
        self.assertEqual(r["cover"]["never"], 8)
        moved = V.copy()
        moved[0, 0] = 1
        cond, r = M.check(moved, 3)
        self.assertGreater(r["cover"]["twice_or_more"], 0)
        dup = np.vstack([V[:-1], V[:1]])
        cond, r = M.check(dup, 3)
        self.assertFalse(cond["n = 3: 2^3 distinct vectors in {0,1,2,3}^3"])

    def test_direct_cover(self):
        rng = np.random.default_rng(5)
        V = rng.integers(0, 4, size=(9, 3))
        cov = M.cover_counts(V)
        for c in itertools.product(range(4), repeat=3):
            self.assertEqual(int(cov[int(np.array(c) @ (4 ** np.arange(3)))]), M.direct_cover(V, list(c)))

    def test_stacking(self):
        self.assertEqual(M.stacking(self.lattice(2)), 12)

    def test_graph_helpers(self):
        self.assertTrue(M.g_clique([(0, 0), (2, 1), (0, 2), (2, 3)]))
        self.assertEqual(len(M.star_missing([(0, 0), (2, 1), (0, 2), (2, 3)])), 2)
        self.assertFalse(M.g_clique([(0, 0), (1, 1)]))
        self.assertEqual(M.phi((0, 1, 2, 3)), (2, 1, 2, 1))
        self.assertEqual(M.relabel_first([(3, 0)]), [(0, 0)])
        self.assertTrue(M.same_pairs([((2, 0, 1), (2, 0, 3))], [(("2", "0", "1"), ("2", "0'", "3"))]))


class Machinery(unittest.TestCase):
    def test_test_text_and_outputs(self):
        self.assertLessEqual(len(M.TEST), 600)
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


if __name__ == "__main__":
    unittest.main()
