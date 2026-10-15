"""Kauers & Wood's meta flip graph schemes (mm/mfg.py): the e-print reader on an archive written here; the table and
ring readers on texts written here; the .exp reader with divisors on schemes whose answers are known (Strassen's,
scaled copies, broken ones); the modulo-2 reduction; and the control's arithmetic. No released scheme is read here.

Run with: python3 -m unittest discover -s tests -p test_mfg.py
"""

import gzip
import importlib.util
import io
import os
import tarfile
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("mm_mfg", os.path.join(HERE, "..", "mm", "mfg.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

STRASSEN = """(a11 + a22)*(b11 + b22)*(c11 + c22)
(a21 + a22)*(b11)*(c12 - c22)
(a11)*(b12 - b22)*(c21 + c22)
(a22)*(b21 - b11)*(c11 + c12)
(a11 + a12)*(b22)*(-c11 + c21)
(a21 - a11)*(b11 + b12)*(c22)
(a12 - a22)*(b21 + b22)*(c11)
"""

CODES = ["456", "378", "388", "257", "258", "348", "357", "268", "277", "377"] + [
    "346", "347", "446", "267", "358", "368", "457", "556", "458", "467", "557", "566", "477", "558", "567", "568",
    "577", "667"]


def table_text(bad=False):
    rows = ["% format & old rank & ... \\\\\\hline"]
    for i, c in enumerate(CODES):
        b2 = "\\b{%d}" % (40 + i + (1 if bad and i == 0 else 0))
        rows.append(f"{c} & \\o{{{50 + i}}} & \\b{{{40 + i}}} & & \\c{{99}} & {b2} \\\\")
    return "\n".join(rows) + "\n"


MAIN = ("Some text. For the formats $(4,5,6)$, $(3,7,8)$ and $(3,8,8)$, the improvement appears\n to work only "
        "over~$\\set Z_2$. The other exceptional\nformats are $(2,5,7)$, $(2,5,8)$, $(3,4,8)$, $(3,5,7)$, $(2,6,8)$, "
        "$(2,7,7)$,\nand $(3,7,7)$, where Hensel lifting did not lead to\ninteger coefficients but only to "
        "coefficients in~$\\set Q$. More.")


def tar_gz(files):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, text in files.items():
            data = text.encode("ascii")
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return gzip.compress(buf.getvalue())


class Paper(unittest.TestCase):
    def test_eprint(self):
        got = M.eprint_files(tar_gz({"main.tex": MAIN, "table.tex": "x", "other.bbl": "y"}))
        self.assertEqual(set(got), {"main.tex", "table.tex"})
        with self.assertRaises(M.Refused):
            M.eprint_files(tar_gz({"main.tex": MAIN}))
        with self.assertRaises(M.Refused):
            M.eprint_files(b"not gzip")

    def test_table(self):
        rows = M.read_table(table_text())
        self.assertEqual(len(rows), 28)
        self.assertEqual(rows["456"], {"old": 50, "best": 40})
        with self.assertRaises(M.Refused):
            M.read_table(table_text(bad=True))
        with self.assertRaises(M.Refused):
            M.read_table("\n".join(table_text().splitlines()[:5]))

    def test_rings(self):
        rows = M.read_table(table_text())
        rings = M.read_rings(MAIN, rows)
        self.assertEqual(rings["456"], "Z2")
        self.assertEqual(rings["348"], "Q")
        self.assertEqual(rings["346"], "Z")
        self.assertEqual(sum(1 for r in rings.values() if r == "Z"), 18)
        with self.assertRaises(M.Refused):
            M.read_rings(MAIN.replace("$(3,8,8)$", "$(9,9,9)$"), rows)


class Reading(unittest.TestCase):
    def test_strassen_over_each_ring(self):
        for ring in ("Z", "Q", "Z2"):
            scheme, divisors = M.read_scheme(STRASSEN.encode(), (2, 2, 2), ring)
            self.assertEqual(len(scheme), 7)
            self.assertEqual(M.CHECK.wrong_entries(scheme, 2, 2, 2, M.RINGS[ring]), 0)
            self.assertEqual(divisors, [1] * 7)

    def test_divisor(self):
        text = STRASSEN.replace("(a12 - a22)*(b21 + b22)*(c11)", "(3*a12 - 3*a22)*(b21 + b22)*(c11)/3")
        scheme, divisors = M.read_scheme(text.encode(), (2, 2, 2), "Q")
        self.assertEqual(M.CHECK.wrong_entries(scheme, 2, 2, 2, "Q"), 0)
        self.assertEqual(divisors[-1], 3)
        wrong = STRASSEN.replace("(a12 - a22)*(b21 + b22)*(c11)", "(a12 - a22)*(b21 + b22)*(c11)/3")
        scheme, _ = M.read_scheme(wrong.encode(), (2, 2, 2), "Q")
        self.assertGreater(M.CHECK.wrong_entries(scheme, 2, 2, 2, "Q"), 0)
        with self.assertRaises(M.Refused):
            M.read_scheme(text.encode(), (2, 2, 2), "Z")
        with self.assertRaises(M.Refused):
            M.read_scheme(text.encode(), (2, 2, 2), "Z2")

    def test_negated_and_refused(self):
        neg = STRASSEN.replace("(a11 + a12)*(b22)*(-c11 + c21)", "-((a11 + a12)*(b22)*(c11 - c21))")
        scheme, _ = M.read_scheme(neg.encode(), (2, 2, 2), "Z")
        self.assertEqual(M.CHECK.wrong_entries(scheme, 2, 2, 2, "Z"), 0)
        for bad in ("(a11)*(b11)", "(a13)*(b11)*(c11)", "(a11)*(b11)*(c11) junk", "(a11)*(b11)*(c11)/0"):
            with self.assertRaises(M.Refused):
                M.read_scheme(bad.encode(), (2, 2, 2), "Q")

    def test_mod2(self):
        scheme, _ = M.read_scheme(STRASSEN.encode(), (2, 2, 2), "Z")
        self.assertEqual(M.CHECK.wrong_entries(M.mod2_of(scheme), 2, 2, 2, "F2"), 0)
        q = [({0: Fraction(1, 3)}, {0: 3}, {0: 1})]
        self.assertEqual(M.mod2_of(q), [({0: 1}, {0: 1}, {0: 1})])
        with self.assertRaises(M.Refused):
            M.mod2_of([({0: Fraction(1, 2)}, {0: 1}, {0: 1})])

    def test_helpers(self):
        self.assertEqual(M.primes_of(1755), {3, 5, 13})
        self.assertEqual(M.primes_of(1), set())
        nv = M.naive(2, 5, 7)
        self.assertEqual(len(nv), 70)
        self.assertEqual(M.CHECK.wrong_entries(nv, 2, 5, 7, "Z"), 0)
        self.assertEqual(M.fmt_of("346"), (3, 4, 6))
        with self.assertRaises(M.Refused):
            M.fmt_of("3x6")

    def test_expected_altered(self):
        scheme, _ = M.read_scheme(STRASSEN.encode(), (2, 2, 2), "Z")
        seed = "ab" * 32
        got = M.CHECK.control(scheme, 2, 2, 2, "Z", M.CHECK.Stream(seed, "t/control"))
        self.assertEqual(got, M.expected_altered(scheme, 2, 2, "t", seed))


class Machinery(unittest.TestCase):
    def test_test_and_outputs(self):
        self.assertLessEqual(len(M.TEST), 600)
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 64)

    def test_data_of_record(self):
        self.assertEqual(len(M.SCHEME_LIST), 28)
        self.assertEqual(len({c for c, _, _ in M.SCHEME_LIST}), 28)
        for code, name, sha in M.SCHEME_LIST:
            self.assertTrue(name.startswith(f"mfg-{code}-") and len(name) <= 40)
            self.assertRegex(sha, r"^[0-9a-f]{64}$")
        self.assertEqual({c for c, _, _ in M.SCHEME_LIST}, set(CODES))

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


if __name__ == "__main__":
    unittest.main()
