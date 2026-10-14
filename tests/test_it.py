"""Ilten & Teitler's product ranks (prank/it.py): the reader on a source built here (a gzipped tar, split environments,
a coefficient, bare and bracketed factors, refusals); expansion against Leibniz's formula; multiples and the row rule;
tensors, the Koszul flattening and Strassen's commutator on tensors whose ranks are known; the verdict at and beside
each condition, under both tests; the seed refused. The paper's source is not read here, and neither of its two
identities is expanded.

Run with: python3 -m unittest discover -s tests -p test_it.py
"""

import importlib.util
import io
import itertools
import os
import tarfile
import tempfile
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("prank_it", os.path.join(HERE, "..", "prank", "it.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


def leibniz_tex(signed):
    """Perm3 or Det3 as the six products of variables, in the TeX a paper would print."""
    parts = []
    for perm in itertools.permutations(range(3)):
        sign = "-" if signed and M.sign_of(perm) < 0 else "+"
        parts.append(f"{sign} " + "".join(f"x_{{{i + 1}{perm[i] + 1}}}" for i in range(3)))
    return " ".join(parts).lstrip("+ ")


PERM_BLOCK = "\\[\n\\begin{split}\n  \\Perm_3 &= " + leibniz_tex(False) + " .\n\\end{split}\n\\]\n"
DET_BLOCK = ("\\[\n\\begin{split}\n \\Det_3 = \\frac{1}{2} \\Big( & 2 x_{11}(x_{22})(x_{33}) \\\\\n   & "
             "- 2 x_{12}x_{21}x_{33} + 2 x_{12}x_{23}x_{31} - 2 x_{13}x_{22}x_{31} "
             "+ 2 x_{13}x_{21}x_{32} - 2 x_{11}x_{23}x_{32}\n   \\Big) .\n\\end{split}\n\\]\n")


def source(tex, name="pr.tex"):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        raw = tex.encode("utf-8")
        info = tarfile.TarInfo(name)
        info.size = len(raw)
        tar.addfile(info, io.BytesIO(raw))
    return buf.getvalue()


class Reading(unittest.TestCase):
    def test_archive_and_blocks(self):
        tex = "Intro.\n" + PERM_BLOCK + "Text.\n" + DET_BLOCK
        got = M.tex_of(source(tex))
        self.assertEqual(got, tex)
        rights = M.blocks(got)
        self.assertEqual(sorted(rights), ["Det3", "Perm3"])
        perm = M.parse(rights["Perm3"])
        self.assertEqual(len(perm), 6)
        self.assertTrue(M.rows_ok(perm))
        self.assertEqual(M.multiple(M.expand(perm), M.TARGET["Perm3"]), 1)
        det = M.parse(rights["Det3"])
        self.assertEqual([c for c, _ in det], [1, -1, 1, -1, 1, -1])     # the half times 2, with signs
        self.assertEqual(M.multiple(M.expand(det), M.TARGET["Det3"]), 1)

    def test_bracketed_factors_and_coefficients(self):
        terms = M.parse("(x_{11} + 2x_{12} - x_{13})(x_{21}) - 3 x_{31}(x_{22}-x_{23})")
        self.assertEqual(terms[0], (Fraction(1), [{(0, 0): 1, (0, 1): 2, (0, 2): -1}, {(1, 0): 1}]))
        self.assertEqual(terms[1], (Fraction(-3), [{(2, 0): 1}, {(1, 1): 1, (1, 2): -1}]))
        self.assertFalse(M.rows_ok(terms))                             # two factors, not three
        self.assertEqual(M.parse("\\frac{1}{4} ( x_{11}x_{22}x_{33} )")[0][0], Fraction(1, 4))

    def test_refusals(self):
        for bad in ("y_{11} + x_{12}", "x_{14}", "(x_{11} + x_{11})", "x_{11} * x_{22}", "(x_{11}", "+"):
            with self.assertRaises(M.Refused):
                M.parse(bad)
        with self.assertRaises(M.Refused):
            M.blocks(PERM_BLOCK)                                       # no Det3
        with self.assertRaises(M.Refused):
            M.blocks(PERM_BLOCK + PERM_BLOCK + DET_BLOCK)               # Perm3 twice
        with self.assertRaises(M.Refused):
            M.tex_of(source("x", name="other.tex"))
        with self.assertRaises(M.Refused):
            M.tex_of(b"not a tar")

    def test_normalise(self):
        self.assertEqual(" ".join(M.normalise(" a &= b \\\\ & + c \\Big) .").split()), "a = b + c )")

    def test_statements(self):
        tex = "the Glynn and Derksen identities above show $\\pr(\\Perm_3) \\leq 4$ and\n$\\pr(\\Det_3) \\leq 5$."
        found = M.statements_found(tex)
        self.assertEqual(sum(found.values()), 1)

    def test_hash_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, M.INPUT[0]), "wb") as fh:
                fh.write(source("x"))
            with self.assertRaises(M.Refused):
                M.read_input(d)


class Polynomials(unittest.TestCase):
    def test_leibniz(self):
        self.assertEqual(len(M.TARGET["Det3"]), 6)
        ident = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        ones = [[1] * 3 for _ in range(3)]
        self.assertEqual(M.eval_poly(M.TARGET["Det3"], ident), 1)
        self.assertEqual(M.eval_poly(M.TARGET["Perm3"], ones), 6)
        self.assertEqual(M.eval_poly(M.TARGET["Det3"], ones), 0)
        X = [[2, -1, 3], [0, 4, 1], [5, 2, -2]]
        self.assertEqual(M.eval_poly(M.TARGET["Det3"], X), M.cofactor_det(X))
        self.assertEqual(M.eval_poly(M.TARGET["Perm3"], X), M.ryser_value(X))

    def test_multiple(self):
        det = M.TARGET["Det3"]
        self.assertEqual(M.multiple({k: 3 * v for k, v in det.items()}, det), 3)
        self.assertEqual(M.multiple({}, det), 0)
        broken = dict(det)
        broken[next(iter(det))] *= 2
        self.assertIsNone(M.multiple(broken, det))
        self.assertIsNone(M.multiple({**det, (0, 1, 2): 1}, det))
        self.assertEqual(M.mismatches({k: 4 * v for k, v in det.items()}, det), 6)

    def test_ryser_and_polarization(self):
        for n in (2, 3, 4):
            self.assertEqual(M.multiple(M.expand(M.ryser(n), n), M.leibniz(n, False)), 1)
            self.assertEqual(len(M.ryser(n)), 2 ** n - 1)
            self.assertEqual(len(M.glynn_printed(n)), 2 ** (n - 1))
        self.assertEqual(M.multiple(M.expand(M.polarization(2), 2), {(0, 1): 1}), 1)

    def test_rows(self):
        good = [(Fraction(1), [{(0, 0): 1, (0, 2): 1}, {(2, 1): 1}, {(1, 0): -1}])]
        self.assertTrue(M.rows_ok(good))
        self.assertFalse(M.rows_ok([(Fraction(1), [{(0, 0): 1, (1, 2): 1}, {(2, 1): 1}, {(1, 0): 1}])]))
        self.assertFalse(M.rows_ok([(Fraction(1), [{(0, 0): 1}, {(0, 1): 1}, {(1, 0): 1}])]))
        T = M.tensor_of_terms(good)
        self.assertEqual(T[0][0][1], -1)
        self.assertEqual(T[2][0][1], -1)
        self.assertEqual(sum(1 for i, j, k in itertools.product(range(3), repeat=3) if T[i][j][k]), 2)


def unit():
    return [[[Fraction(int(i == j == k)) for k in range(3)] for j in range(3)] for i in range(3)]


class Flattenings(unittest.TestCase):
    def test_koszul_known_ranks(self):
        self.assertEqual(M.rank(M.koszul(unit())), 6)
        one = [[[Fraction(int(i == 0 and j == 1 and k == 2)) for k in range(3)] for j in range(3)] for i in range(3)]
        self.assertEqual(M.rank(M.koszul(one)), 2)
        st = M.Stream("ab" * 32, "t")
        for r in range(1, 5):
            self.assertLessEqual(M.rank(M.koszul(M.rank_one_sum(st, r))), 2 * r)
        self.assertEqual(M.rank(M.koszul(M.drawn_tensor(st))), 9)

    def test_tensor_of_and_permute(self):
        T = M.tensor_of(M.TARGET["Det3"])
        self.assertEqual(T[0][1][2], 1)
        self.assertEqual(T[1][0][2], -1)
        P = M.permute(T, 2)
        self.assertEqual(P[2][0][1], T[0][1][2])
        with self.assertRaises(ValueError):
            M.tensor_of({(0, 1, 2): 1})

    def test_strassen_consistency(self):
        st = M.Stream("cd" * 32, "t")
        for T in (unit(), M.rank_one_sum(st, 3), M.rank_one_sum(st, 4), M.drawn_tensor(st, -3, 3)):
            fr = M.invertible_frame(T, st)
            self.assertIsNotNone(fr)
            self.assertEqual(M.rank(M.koszul(T)), 6 + M.commutator_rank(T, *fr))
        self.assertEqual(M.commutator_rank(unit(), [1, 2, 3], [0, 1, 0], [0, 0, 1]), 0)

    def test_linear_algebra(self):
        A = [[2, 1, 0], [1, 3, 1], [0, 1, 4]]
        self.assertEqual(M.det(A), 18)
        self.assertEqual(M.matmul(A, M.inverse(A)), [[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        self.assertEqual(M.rank([[1, 2], [2, 4]]), 1)
        with self.assertRaises(ZeroDivisionError):
            M.inverse([[1, 2], [2, 4]])


class Verdict(unittest.TestCase):
    def found(self, **kw):
        f = {"Perm3": {"terms": 4, "rows_ok": True, "multiple": Fraction(1)},
             "Det3": {"terms": 5, "rows_ok": True, "multiple": Fraction(1)},
             "koszul": {"Det3": [9, 9, 9], "Perm3": [8, 8, 8]}}
        for key, v in kw.items():
            name, field = key.split("_", 1)
            if name == "koszul":
                f["koszul"][field] = v
            else:
                f[name][field] = v
        return f

    def test_conditions(self):
        c = M.conditions(self.found())
        self.assertEqual(len(c), 4)
        self.assertTrue(all(c.values()))
        for kw in ({"Perm3_terms": 5}, {"Det3_rows_ok": False}, {"Det3_multiple": None},
                   {"Perm3_multiple": Fraction(0)}, {"koszul_Det3": [8, 9, 9]}, {"koszul_Perm3": [6, 8, 8]}):
            self.assertEqual(sum(M.conditions(self.found(**kw)).values()), 3, kw)
        self.assertTrue(all(M.conditions(self.found(koszul_Perm3=[7, 7, 7])).values()))

    def test_scalar_rule(self):
        saved = M.SCALAR
        try:
            M.SCALAR = True
            self.assertTrue(all(M.conditions(self.found(Perm3_multiple=Fraction(4))).values()))
            M.SCALAR = False
            self.assertEqual(sum(M.conditions(self.found(Perm3_multiple=Fraction(4))).values()), 3)
            self.assertTrue(all(M.conditions(self.found()).values()))
        finally:
            M.SCALAR = saved

    def test_perturb_changes(self):
        st = M.Stream("ef" * 32, "t")
        terms = M.parse(M.blocks(PERM_BLOCK + DET_BLOCK)["Perm3"])
        for _ in range(10):
            out, what = M.perturb(terms, st)
            self.assertNotEqual(out, terms, what)
            self.assertIsNone(M.multiple(M.expand(out), M.TARGET["Perm3"]), what)

    def test_outputs_named(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


if __name__ == "__main__":
    unittest.main()
