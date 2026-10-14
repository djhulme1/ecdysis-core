"""Sedoglavic & Smirnov's 58 (mm/ss.py): the TeX reader and the expression parser on snippets written here (powers of
e, fractions, braces, alignment marks, comments); the products and their forms; the exact check on Strassen's algorithm
(as the paper's convention writes it, typed here), on a flipped sign and on the naive algorithm; the approximate check
on a border rank 2 expression and on a partial product with entries set to zero; ranks, types and shared factors; the
e-print reader's refusals; the outputs and the seed refused. The paper's e-print is not read here, and none of its
schemes is parsed or checked.

Run with: python3 -m unittest discover -s tests -p test_ss.py
"""

import importlib.util
import io
import os
import tarfile
import tempfile
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("mm_ss", os.path.join(HERE, "..", "mm", "ss.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


def poly(text):
    return M.Parser(M.tokens(M.normalise(text))).poly((None,))


def eprint(tex, name=M.TEX):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        raw = tex.encode("utf-8")
        info = tarfile.TarInfo(name)
        info.size = len(raw)
        tar.addfile(info, io.BytesIO(raw))
    return buf.getvalue()


class Reading(unittest.TestCase):
    def test_normalise(self):
        s = M.normalise("&\\left({a_{12}}-{a_{22}}\\right)\\!b_{31}\\\\ % comment\n-&{c_{53}}\\epsilon^{2}.%7")
        self.assertEqual(s, "({a12}-{a22})b31-{c53}e^{2}")
        self.assertEqual(M.tokens(s), ["(", "{", "a12", "}", "-", "{", "a22", "}", ")", "b31", "-", "{", "c53", "}",
                                       "e", "^", "{", "2", "}"])
        with self.assertRaises(M.Refused):
            M.tokens("a12*b22")
        broken = M.normalise("\\left(a_{11}\\right)b_{12}c_{21}\\\\%8\n+a_{12}b_{21}c_{11}")
        self.assertEqual(broken, "(a11)b12c21+a12b21c11")       # a % right after a line break is a comment

    def test_parser(self):
        self.assertEqual(poly("a_{11}+a_{12}-a_{11}"), {(("a12",), 0): 1})
        p = poly(r"\frac{a_{51}-a_{31}}{{\epsilon}^{2}}")
        self.assertEqual(p, {(("a51",), -2): 1, (("a31",), -2): -1})
        p = poly(r"\left((c_{41}+c_{42})\epsilon^3+{c_{44}}\right)")
        self.assertEqual(p, {(("c41",), 3): 1, (("c42",), 3): 1, (("c44",), 0): 1})
        p = poly(r"a_{21}{\epsilon^{2}}\left(b_{11}-\frac{b_{12}}{\epsilon}\right)")
        self.assertEqual(p, {(("a21", "b11"), 2): 1, (("a21", "b12"), 1): -1})
        self.assertEqual(poly("2a_{11}a_{11}"), {(("a11", "a11"), 0): 2})
        with self.assertRaises(M.Refused):
            poly(r"\frac{a_{11}}{a_{12}}")
        with self.assertRaises(M.Refused):
            poly("(a_{11}+")

    def test_products(self):
        prods = M.products_of(M.normalise(M.STRASSEN))
        self.assertEqual(len(prods), 7)
        forms = [M.integer_form(x) for x in prods]
        self.assertEqual(forms[1], {"a": {"a11": 1, "a12": 1}, "b": {"b22": 1}, "c": {"c11": -1, "c21": 1}})
        bad = M.products_of(M.normalise(r"a_{11}b_{12}+a_{11}a_{12}b_{11}c_{11}+(a_{11}+b_{11})b_{11}c_{11}"))
        self.assertTrue(all(x["bad"] for x in bad))
        self.assertIsNone(M.integer_form(M.products_of(M.normalise(r"\frac{a_{11}}{2}b_{11}c_{11}"))[0]))

    def test_regions(self):
        tex = "x " + M.SCHEME[0] + r" \begin{equation}\tau_{111}=a_{11}b_{11}c_{11}\end{equation} " + M.SCHEME[1]
        got = M.blocks(M.region(tex, M.SCHEME), "tau")
        self.assertEqual(got, {"111": "a11b11c11"})
        with self.assertRaises(M.Refused):
            M.region("nothing", M.SCHEME)
        twice = tex.replace(M.SCHEME[1], r"\begin{equation}\tau_{111}=a_{11}b_{11}c_{11}\end{equation}" + M.SCHEME[1])
        with self.assertRaises(M.Refused):
            M.blocks(M.region(twice, M.SCHEME), "tau")

    def test_eprint(self):
        self.assertIn("tau", M.tex_of(eprint("tau")))
        with self.assertRaises(M.Refused):
            M.tex_of(eprint("x", name="other.tex"))
        with self.assertRaises(M.Refused):
            M.tex_of(b"not a tar")
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, M.INPUT[0])
            with open(path, "wb") as fh:
                fh.write(eprint("tau"))
            with self.assertRaises(M.Refused):
                M.read_bytes(path, M.INPUT[1])


class Checks(unittest.TestCase):
    def test_exact(self):
        forms = [M.integer_form(x) for x in M.products_of(M.normalise(M.STRASSEN))]
        self.assertEqual(M.wrong_count(forms, 2, 2, 2), 0)
        self.assertEqual(M.wrong_count(forms[:6], 2, 2, 2), 4)          # (a21 - a11)(b11 + b12) c22: its 4 terms
        self.assertTrue(all(M.in_range(v, 2, 2, 2) for f in forms for form in f.values() for v in form))
        self.assertFalse(M.in_range("c31", 3, 5, 5) and M.in_range("a41", 3, 5, 5))
        self.assertTrue(M.in_range("c53", 3, 5, 5))
        self.assertFalse(M.in_range("c54", 3, 5, 5))

    def test_approx(self):
        w = M.products_of(M.normalise(M.W_STATE))
        total = M.expand_approx(w)
        self.assertEqual(total[("a11", "b11", "c11")][-1], 0)
        self.assertEqual(total[("a11", "b11", "c12")][0], 1)
        zero = {(1, 2)}
        naive = "+".join(f"a_{{{i}{j}}}b_{{{j}{k}}}c_{{{k}{i}}}" for i in (1, 2) for j in (1, 2) for k in (1, 2)
                         if (i, j) not in zero)
        prods = M.products_of(M.normalise(naive))
        self.assertEqual(M.approx_check(prods, 2, 2, 2, zero), (0, 0))
        self.assertEqual(M.approx_check(prods[1:], 2, 2, 2, zero), (0, 1))
        extra = M.products_of(M.normalise(naive + r"+\frac{a_{11}}{\epsilon}b_{11}c_{11}+a_{12}b_{21}c_{12}"))
        self.assertEqual(M.approx_check(extra, 2, 2, 2, zero), (1, 0))   # a12 is in the zero block: not counted

    def test_types_and_shared(self):
        self.assertEqual(M.rank([[1, 2], [2, 4]]), 1)
        self.assertEqual(M.rank([[1, 0, 0], [0, 1, 0], [0, 0, 0]]), 2)
        self.assertEqual(M.rank([[0, 0], [0, 0]]), 0)
        forms = [M.integer_form(x) for x in M.products_of(M.normalise(M.STRASSEN))]
        types = sorted(M.type_of(f, 2, 2, 2) for f in forms)
        self.assertEqual(types, [(1, 1, 1)] * 6 + [(2, 2, 2)])           # the paper: X^2Y^2Z^2 + 6 XYZ
        self.assertEqual(M.shared_pairs(forms), 0)
        twin = dict(forms[0])
        twin["b"] = {k: -v for k, v in forms[0]["b"].items()}
        self.assertEqual(M.shared_pairs([forms[0], twin]), 1)            # same factor up to sign

    def test_controls(self):
        self.assertTrue(all(M.controls_known().values()))


class Verdict(unittest.TestCase):
    def test_outputs_named(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)
        self.assertEqual(sum(M.PRINTED_TYPE.values()), M.PRODUCTS)

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


if __name__ == "__main__":
    unittest.main()
