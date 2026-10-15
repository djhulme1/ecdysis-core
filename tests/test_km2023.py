"""Kauers & Moosbauer's (n,m,6) schemes (mm/km2023.py): the reader of the appendix's pmatrix notation, the reader of
Section 2's symbolic notation, the source archive's reader, Hopcroft and Kerr's count and the control, all on inputs
made here from Strassen's scheme. No scheme of the paper is read here.

Run with: python3 -m unittest tests.test_km2023
"""

import importlib.util
import io
import os
import tarfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("mm_km2023", os.path.join(HERE, "..", "mm", "km2023.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "ef" * 32

# Strassen's terms as (A, B, C) with C indexed (k, i), as the paper writes c_{k,i}
STRASSEN = [
    ([[1, 0], [0, 1]], [[1, 0], [0, 1]], [[1, 0], [0, 1]]),
    ([[0, 0], [1, 1]], [[1, 0], [0, 0]], [[0, 1], [0, -1]]),
    ([[1, 0], [0, 0]], [[0, 1], [0, -1]], [[0, 0], [1, 1]]),
    ([[0, 0], [0, 1]], [[-1, 0], [1, 0]], [[1, 1], [0, 0]]),
    ([[1, 1], [0, 0]], [[0, 0], [0, 1]], [[-1, 0], [1, 0]]),
    ([[-1, 0], [1, 0]], [[1, 1], [0, 0]], [[0, 0], [0, 1]]),
    ([[0, 1], [0, -1]], [[0, 0], [1, 1]], [[1, 0], [0, 0]]),
]


def pm(M_):
    def cell(x):
        return f"\\bar{-x}" if x < 0 else str(x)
    return "\\begin{pmatrix}\n" + "".join(" " + " & ".join(cell(x) for x in row) + " \\\\\n" for row in M_) + \
        "\\end{pmatrix}"


def block(terms, sep="&&+\n"):
    body = sep.join(pm(a) + "\\otimes" + pm(b) + "\\otimes" + pm(c) for a, b, c in terms)
    return "\\begin{alignat*}3\n" + body + "\n"


class Readers(unittest.TestCase):
    def test_matrix_of(self):
        self.assertEqual(M.matrix_of(" 1 & \\bar2 \\\\ 0 & 3 \\\\ "), [[1, -2], [0, 3]])
        self.assertEqual(M.matrix_of(" \\bar{12} & \\bar 1 \\\\"), [[-12, -1]])
        with self.assertRaises(ValueError):
            M.matrix_of(" 1 & x \\\\")

    def test_printed_reader_on_strassen(self):
        scheme = M.read_printed(block(STRASSEN), 2, 2, 2)
        self.assertEqual(len(scheme), 7)
        self.assertEqual(M.check.wrong_entries(scheme, 2, 2, 2, "Z"), 0)
        for sep in ("\\\\+\n", "+\n", "\\\\+&\n"):
            self.assertEqual(len(M.read_printed(block(STRASSEN, sep), 2, 2, 2)), 7)

    def test_printed_reader_refuses(self):
        with self.assertRaises(M.Refused):
            M.read_printed(block(STRASSEN, sep="-\n"), 2, 2, 2)
        with self.assertRaises(M.Refused):
            M.read_printed(block(STRASSEN)[:-40], 2, 2, 2)
        bad = block([([[1, 0, 0], [0, 1, 0]], [[1, 0], [0, 1]], [[1, 0], [0, 1]])])
        with self.assertRaises(M.Refused):
            M.read_printed(bad, 2, 2, 2)
        twisted = block(STRASSEN).replace("\\otimes", "\\oplus", 1)
        with self.assertRaises(M.Refused):
            M.read_printed(twisted, 2, 2, 2)

    def test_broken_scheme_is_wrong(self):
        broken = [list(t) for t in STRASSEN]
        broken[3] = ([[0, 0], [0, 1]], [[-1, 0], [1, 0]], [[1, 0], [0, 0]])
        scheme = M.read_printed(block(broken), 2, 2, 2)
        self.assertGreater(M.check.wrong_entries(scheme, 2, 2, 2, "Z"), 0)

    def test_symbolic_examples(self):
        def sym(letter, Mx):
            parts = []
            for r, row in enumerate(Mx):
                for c, x in enumerate(row):
                    if x:
                        parts.append(("-" if x < 0 else "+") + f"{letter}_{{{r + 1},{c + 1}}}")
            s = "".join(parts).lstrip("+")
            return f"({s})"
        lines = ["&" + ("+" if t else "") + f"{sym('a', a)} \\otimes {sym('b', b)} \\otimes {sym('c', c)}"
                 for t, (a, b, c) in enumerate(STRASSEN)]
        std = [f"&{'+' if t else ''}a_{{{i},{j}}}\\otimes b_{{{j},{k}}}\\otimes c_{{{k},{i}}}"
               for t, (i, j, k) in enumerate((i, j, k) for i in (1, 2) for k in (1, 2) for j in (1, 2))]
        tex = ("\\section{Matrix Multiplication}\n\\begin{alignat*}1\n" + "\\\\\n".join(std) + ",\n\\end{alignat*}\n"
               "\\begin{alignat*}1\n" + "\\\\\n".join(lines) + ",\n\\end{alignat*}\n\\section{Results}\n")
        s1, s2 = M.section2_examples(tex)
        self.assertEqual((len(s1), len(s2)), (8, 7))
        self.assertEqual(M.check.wrong_entries(s1, 2, 2, 2, "Z"), 0)
        self.assertEqual(M.check.wrong_entries(s2, 2, 2, 2, "Z"), 0)
        _, s2t = M.section2_examples(tex, swap_c=True)
        self.assertGreater(M.check.wrong_entries(s2t, 2, 2, 2, "Z"), 0)

    def test_tex_of(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tf:
            data = "\\documentclass{amsart}\nhello\n".encode()
            info = tarfile.TarInfo("main.tex")
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
        self.assertIn("hello", M.tex_of(buf.getvalue()))


class Counts(unittest.TestCase):
    def test_hopcroft_kerr(self):
        self.assertEqual(M.hopcroft_kerr(1, 1), 2)
        self.assertEqual(M.hopcroft_kerr(2, 2), 7)
        self.assertEqual(M.hopcroft_kerr(3, 3), 15)
        self.assertEqual(M.hopcroft_kerr(3, 2), 11)

    def test_control_counts(self):
        scheme = M.read_printed(block(STRASSEN), 2, 2, 2)
        for ring in ("Z", "F2"):
            got, want = M.control(scheme, 2, 2, 2, ring, M.check.Stream(SEED, f"t/{ring}"))
            self.assertEqual(got, want)
            self.assertGreater(got, 0)

    def test_wide(self):
        self.assertEqual(M.wide([({0: 2}, {0: 1}, {0: 1}), ({0: 1}, {0: -1}, {0: 1})]), 1)


if __name__ == "__main__":
    unittest.main()
