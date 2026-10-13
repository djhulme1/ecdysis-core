"""Structured matrix multiplication (mm/structured.py): reading a figure (its macros, line breaks, columns and comments,
and each refusal); the released files' indexing; the two tensors on the schoolbook schemes; the recursive calls by each
criterion; the factor on the paper's own examples; the sign-free comparison of terms; the probes and the altered
scheme; and, with the claim's three inputs at inputs/ (or STRUCTURED_INPUTS), the run itself.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import os
import tempfile
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("mm_structured", os.path.join(HERE, "..", "mm", "structured.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

INPUTS = os.environ.get("STRUCTURED_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = all(os.path.isfile(os.path.join(INPUTS, name)) for name, _ in [M.EPRINT, *M.RELEASED.values()])
SEED = "0" * 64


def figure(products, outputs):
    """A figure in the paper's TeX form: products as (name, left, right), outputs as (block, right side)."""
    lines = ["\\begin{figure*}", "\\begin{equation*}", "\\begin{aligned}"]
    for name, left, right in products:
        lines.append(f"    {name} &= ({left})\\blue{{({right})}} \\\\")
    lines += ["\\end{aligned}", "\\end{equation*}", "\\begin{equation*}", "\\begin{aligned}"]
    for block, rhs in outputs:
        lines.append(f"    {block} &= {rhs} \\\\")
    lines += ["\\end{aligned}", "\\end{equation*}", "\\end{figure*}"]
    return "\n".join(lines)


def schoolbook_figure():
    """The 40-product schoolbook AB with A upper triangular, as a figure (the r's are the diagonal ones)."""
    products, uses = [], {}
    count = 0
    for i in range(1, 5):
        for k in range(1, 5):
            for j in range(i, 5):
                count += 1
                left = f"\\red{{A_{i}^{j}}}" if i == j else f"A_{i}^{j}"
                name = f"m_{{{count}}}"
                products.append((name, left, f"B_{j}^{k}"))
                uses.setdefault(f"C_{i}^{k}", []).append(name)
    outputs = [(block, " + ".join(names)) for block, names in uses.items()]
    return figure(products, outputs)


class Reading(unittest.TestCase):
    def test_unwrap_keeps_the_inside(self):
        self.assertEqual(M.unwrap("x\\red{A_1^1} + \\red{\\red{y}}", "red"), "xA_1^1 + y")
        with self.assertRaises(M.Refused):
            M.unwrap("\\red{A_1^1", "red")

    def test_columns_breaks_and_comments(self):
        tex = ("m_{1} &= (A_1^1 + \\red{A_2^2}) \\\\[-1.5mm]&\\hspace{4.2mm} \\blue{(B_2^1 - 2B_1^1)} \\\\\n"
               "% m_{9} &= (A_1^2)(B_1^1) \\\\\n"
               "C_1^1 &= \\reccall{-r_{2}} + m_{1} \\hspace{2.3cm} C_4^1 = \\reccall{r_{3}} \\\\\n"
               "\\end{aligned}")
        eqs = dict(M.equations(tex))
        self.assertEqual(set(eqs), {"m_{1}", "C_1^1", "C_4^1"})                # the commented m_{9} is not read
        self.assertEqual(eqs["m_{1}"], "(A_1^1 + A_2^2) (B_2^1 - 2B_1^1)")
        self.assertEqual(eqs["C_1^1"], "-r_{2} + m_{1}")
        self.assertEqual(M.linear("B_2^1 - 2B_1^1", "B"), {(2, 1): 1, (1, 1): -2})

    def test_a_printed_scheme_reads_and_checks(self):
        scheme = M.read_figure(schoolbook_figure(), "ug")
        self.assertEqual((M.products(scheme), M.wrong(scheme, "ug")), (40, 0))
        self.assertEqual(M.recursive(scheme, "ug"), (16, 16, 16))

    def test_refusals(self):
        good = schoolbook_figure()
        cases = {
            "twice": good.replace("m_{2} &=", "m_{1} &="),
            "unused": good.replace("\\end{aligned}\n\\end{equation*}\n\\begin{equation*}",
                                   "    m_{99} &= (A_1^1)\\blue{(B_1^1)} \\\\\n\\end{aligned}\n\\end{equation*}\n"
                                   "\\begin{equation*}", 1),
            "missing output": "\n".join(l for l in good.splitlines() if "C_4^4 &=" not in l),
            "below the diagonal": good.replace("(A_1^2)", "(A_2^1)", 1),
            "letter": good.replace("\\blue{(B_1^1)}", "\\blue{(A_1^1)}", 1),
            "token": good.replace("(A_1^2)", "(A_1^2 \\cdot 3)", 1),
            "unprinted product": good.replace("m_{1} +", "m_{777} +", 1),
        }
        for name, tex in cases.items():
            with self.subTest(case=name):
                self.assertNotEqual(tex, good)
                with self.assertRaises(M.Refused):
                    M.read_figure(tex, "ug")
        with self.assertRaises(M.Refused):
            M.read_figure(good.replace("C_4^4 &=", "C_9^9 &="), "ug")


class Released(unittest.TestCase):
    def test_indexing(self):
        text = "m1  = (a5)(b5 - 2b7)\nm2  = (a1)(b1)\n\nc1  = m2\nc5  = m1\nc10 = 0\n"
        ug = M.read_released(text, "ug")
        self.assertEqual(ug[0][1:], ({(2, 2): 1}, {(2, 1): 1, (2, 3): -2}, {(2, 1): 1}))   # a packed upper, c general
        gt = M.read_released(text, "gt")
        self.assertEqual(gt[0][1:], ({(2, 1): 1}, {(2, 1): 1, (2, 3): -2}, {(2, 2): 1}))   # a general, c packed upper
        with self.assertRaises(M.Refused):
            M.read_released("m1 = (a1)(b1)\nc99 = m1\n", "ug")

    def test_corners(self):
        sb = [t for t in M.schoolbook("gt") if t[3] not in ({(1, 1): 1}, {(4, 4): 1})]
        self.assertEqual(M.wrong(sb, "gt", skip=((1, 1), (4, 4))), 0)
        self.assertEqual(M.wrong(sb + M.corners(), "gt"), 0)


class Tensors(unittest.TestCase):
    def test_schoolbook_schemes(self):
        for kind in ("gt", "ug"):
            with self.subTest(kind=kind):
                sb = M.schoolbook(kind)
                self.assertEqual((M.products(sb), M.wrong(sb, kind)), (40, 0))
                self.assertEqual(M.recursive(sb, kind)[0], 16)
                self.assertEqual(M.gamma(40, 16), Fraction(8, 11))

    def test_the_transpose_matters(self):
        self.assertGreater(M.wrong(M.schoolbook("gt"), "gt", transposed=False), 0)

    def test_altered_fails(self):
        for kind in ("gt", "ug"):
            sb = M.schoolbook(kind)
            self.assertGreater(M.wrong(M.altered(sb, M.check.Stream(SEED, "t")), kind), 0)

    def test_criteria(self):
        equal = ("e", {(2, 1): 1, (2, 2): -1}, {(2, 1): 1, (2, 2): -1}, {(1, 2): 1})     # XX^T into an off-diagonal block
        diag = ("d", {(2, 3): 1}, {(2, 1): 1}, {(2, 2): 1, (3, 3): -1})                  # output only in diagonal blocks
        neither = ("n", {(1, 1): 1}, {(2, 1): 1}, {(1, 2): 1, (2, 2): 1})
        self.assertEqual(M.recursive([equal, diag, neither], "gt"), (1, 1, 1))
        self.assertEqual(M.recursive([equal, equal, diag], "gt"), (2, 2, 1))
        tri = [("a", {(1, 1): 1, (3, 3): 1}, {(1, 2): 1}, {(1, 2): 1}), ("b", {(1, 2): 1}, {(2, 2): 1}, {(1, 2): 1})]
        self.assertEqual(M.recursive(tri, "ug"), (1, 1, 1))

    def test_factor(self):
        self.assertEqual(M.gamma(34, 12), Fraction(22, 37))
        self.assertEqual(M.gamma(34, 10), Fraction(8, 13))
        self.assertEqual(M.gamma(6, 4, 2), Fraction(2, 3))
        self.assertEqual(f"{M.gamma_float(17, 9, 3):.3f}", "0.623")
        self.assertAlmostEqual(M.gamma_float(34, 12, 4), 22 / 37, places=12)

    def test_terms_compare_without_signs(self):
        t = ("x", {(1, 1): 1, (1, 2): -1}, {(2, 1): 1}, {(1, 2): 1})
        flipped = ("y", {(1, 1): -1, (1, 2): 1}, {(2, 1): 1}, {(1, 2): -1})
        other = ("z", {(1, 1): 1}, {(2, 1): 1}, {(1, 2): 1})
        self.assertEqual(M.shared([t], [flipped]), 1)
        self.assertEqual(M.shared([t], [other]), 0)

    def test_additions(self):
        scheme = [("a", {(1, 1): 1, (1, 2): 1}, {(1, 1): 1}, {(1, 1): 1, (2, 2): 1}),
                  ("b", {(2, 2): 1}, {(1, 1): 1, (2, 1): 1, (3, 1): 1}, {(1, 1): -1})]
        self.assertEqual(M.additions(scheme), 1 + 2 + 1)                                # factors 1 + 2; C11 has two

    def test_probes(self):
        for kind in ("gt", "ug"):
            bad, lines = M.probe(M.schoolbook(kind), kind, M.check.Stream(SEED, kind))
            self.assertEqual(bad, 0)
            self.assertEqual(len(lines), len(M.outputs(kind)))
            bad, _ = M.probe(M.altered(M.schoolbook(kind), M.check.Stream(SEED, "a")), kind, M.check.Stream(SEED, kind))
            self.assertGreater(bad, 0)


@unittest.skipUnless(HAVE, "needs the e-print and the two released files at inputs/ or STRUCTURED_INPUTS")
class Run(unittest.TestCase):
    def test_the_claims_schemes(self):
        with tempfile.TemporaryDirectory() as d:
            out, detail = M.run(SEED, inputs=INPUTS, results=d)
        self.assertEqual(out["test_passed"], 1)
        self.assertEqual((out["gt_products"], out["gt_wrong"], out["gt_q"], out["gt_q_equal_factors"], out["gt_gamma"]),
                         (34, 0, 12, 8, "22/37"))
        self.assertEqual((out["ug_products"], out["ug_wrong"], out["ug_q"], out["ug_gamma"]), (34, 0, 12, "22/37"))
        self.assertEqual(out["additions"], "gt 140 (printed 141); ug 148 (printed 148)")
        self.assertTrue(out["released"].startswith("gt 26 + 8 corners: wrong 0, q 12"))
        self.assertEqual(out["controls"], "9 of 9")


if __name__ == "__main__":
    unittest.main()
