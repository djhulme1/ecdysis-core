"""Bailey's 29,360,000 digits (pi/bailey88.py): the PDF reader on strings, arrays, escapes and comments; a small PDF
built here whose block runs over a page break, whose page numbers are dropped and whose missing page number is refused;
Table 1's split header; the agreement count; the verdict on a small run with pi's own digits, a changed digit and a
changed count; with gcc and GMP, the two methods agreeing at 1,000 decimals; and with the author's copy at inputs/ (or
BAILEY88_INPUTS), every block and row the check reads, and the printed deviations and z-scores recomputed.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pi_bailey88", os.path.join(HERE, "..", "pi", "bailey88.py"))
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)

INPUTS = os.environ.get("BAILEY88_INPUTS") or os.path.join(HERE, "..", "inputs")
PAPER = os.path.join(INPUTS, B.INPUT[0])
HAVE = os.path.isfile(PAPER)


def pi_decimals(n):
    """The first n decimals of pi, by Machin's formula in integers (with guard digits)."""
    g = n + 20
    one = 10 ** g

    def arctan_inv(x):
        total, term, k, sign = 0, one // x, 1, 1
        while term:
            total += sign * (term // k)
            term //= x * x
            k += 2
            sign = -sign
        return total

    pi = 4 * (4 * arctan_inv(5) - arctan_inv(239))
    return str(pi)[1:n + 1]


def pdf(pages):
    """A minimal PDF whose pages show the given strings, one Tj each, compressed as the author's copy is."""
    objs, body = [], b"%PDF-1.3\n"
    for k, strings in enumerate(pages):
        content = b"BT " + b" ".join(b"(" + s.encode("latin-1") + b") Tj" for s in strings) + b" ET"
        packed = zlib.compress(content)
        n = 2 * k + 1
        objs.append(b"%d 0 obj\n<< /Type /Page /Contents %d 0 R >>\nendobj\n" % (n, n + 1))
        objs.append(b"%d 0 obj\n<< /Length %d /Filter /FlateDecode >>\nstream\n" % (n + 1, len(packed)) + packed +
                    b"\nendstream\nendobj\n")
    return body + b"".join(objs) + b"%%EOF\n"


class Strings(unittest.TestCase):
    def test_escapes_octal_and_nesting(self):
        s = rb"(a\(b\)c \\ \101\102 (nested) \n)"
        text, end = B.read_string(s, 0)
        self.assertEqual(text, "a(b)c \\ AB (nested) \n")
        self.assertEqual(end, len(s))

    def test_unterminated_is_refused(self):
        with self.assertRaises(B.Refused):
            B.read_string(b"(abc", 0)

    def test_tj_arrays_quotes_and_comments(self):
        stream = b"BT (One) Tj [(Tw) 120 (o) -30 (!)] TJ % (not this) Tj\n (Three) ' 1 2 (Four) \" ET"
        self.assertEqual(B.text_chunks(stream), ["One", "Two!", "Three", "Four"])


class Pages(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d)

    def test_block_runs_over_a_page_break_without_the_page_number(self):
        data = pdf([["Text", "1"], ["Initial1000digits:", "3.", "1415", "926", "2"],
                    ["535", "Digits 4,999,001 to 5,000,000:", "8979", "3"]])
        blocks = B.appendix_blocks(B.content_streams(data))
        self.assertEqual(blocks, {1: "1415926535", 4999001: "8979"})

    def test_other_text_ends_a_block(self):
        data = pdf([["Initial1000digits:", "3.", "1415", "Statistics", "926", "1"]])
        self.assertEqual(B.appendix_blocks(B.content_streams(data)), {1: "1415"})

    def test_a_page_without_its_number_is_refused(self):
        for pages in ([["Initial1000digits:", "3.", "1415", "1"], ["926", "3"]],
                      [["Initial1000digits:", "3.", "1415"]]):
            with self.subTest(pages=pages), self.assertRaises(B.Refused):
                B.appendix_blocks(B.content_streams(pdf(pages)))

    def test_only_content_streams_are_read(self):
        glyph = b"9 0 obj\n<< /Length 3 >>\nstream\n(((\nendstream\nendobj\n"
        data = pdf([["Initial1000digits:", "3.", "1415", "1"]]).replace(b"%%EOF", glyph + b"%%EOF")
        self.assertEqual(B.appendix_blocks(B.content_streams(data)), {1: "1415"})

    def test_table1_with_its_split_header(self):
        rows = [s for d in range(10) for s in (str(d), str(B.TABLE1[d]), str(B.TABLE1[d] - 2936000), "0")]
        data = pdf([["Table 1"] + ["Digit", "Coun", "t", "Deviation", "Z-score"] + rows + ["1"]])
        got = B.table1_rows(B.content_streams(data))
        self.assertEqual([int(r[1]) for r in got], list(B.TABLE1))
        broken = pdf([["Digit", "Count", "Deviation", "Z-score"] + rows[:-4] + ["1"]])
        self.assertIsNone(B.table1_rows(B.content_streams(broken)))

    def test_altered_paper_is_refused(self):
        path = os.path.join(self.d, B.INPUT[0])
        with open(path, "wb") as f:
            f.write(pdf([["x", "1"]]))
        with self.assertRaises(B.Refused):
            B.read_paper(path)


class Agreement(unittest.TestCase):
    def test_counts_the_shared_prefix(self):
        self.assertEqual(B.agreement("31415", "31415"), 5)
        self.assertEqual(B.agreement("31415", "31425"), 3)
        self.assertEqual(B.agreement("31415", "4"), 0)
        self.assertEqual(B.agreement("314", "31415"), 3)

    def test_z_scores_as_table_1_prints_them(self):
        self.assertEqual(B.z_text(2935072), "-0.5709")
        self.assertEqual(B.z_text(2938787), "1.7145")
        self.assertEqual(B.z_text(2936095), "0.0584")


class SmallRun(unittest.TestCase):
    """The run's bookkeeping on 2,000 decimals of pi, with the module's sizes made small and the C program replaced."""

    N = 2000

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.saved = {k: getattr(B, k) for k in ("N_COMPUTE", "N_AGREE", "N_USE", "BLOCKS", "BLOCK_LEN", "TABLE1",
                                                  "read_paper", "build", "two_pis")}
        digits = pi_decimals(self.N + 100)
        self.pi = "3" + digits
        B.N_COMPUTE, B.N_AGREE, B.N_USE = self.N + 100, self.N + 50, self.N
        B.BLOCKS, B.BLOCK_LEN = (1, 1001), 1000
        counts = tuple(digits[:self.N].count(str(d)) for d in range(10))
        B.TABLE1 = counts
        self.blocks = {1: digits[:1000], 1001: digits[1000:2000]}
        self.rows = [(str(d), str(c), str(c - self.N // 10), B.z_text(c)) for d, c in enumerate(counts)]
        B.read_paper = lambda path: (self.blocks, self.rows)
        B.build = lambda results: "unused"
        self.texts = {"chud": self.pi, "agm": self.pi}
        B.two_pis = lambda exe, n, results: (dict(self.texts), {"agm": "agm: 12 iterations"})

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(B, k, v)
        shutil.rmtree(self.d)

    def go(self):
        out, _ = B.run("0" * 64, inputs=self.d, results=os.path.join(self.d, "results"), log=lambda s: None)
        return out

    def test_pi_itself_passes(self):
        out = self.go()
        self.assertEqual((out["test_passed"], out["blocks_matched"], out["block_digits_wrong"]), (1, 2, 0))
        self.assertEqual((out["counts_as_printed"], out["table1_matched"], out["agm_iterations"]), (10, 30, 12))
        self.assertEqual(out["methods_agree"], self.N + 100)

    def test_a_changed_printed_digit_fails(self):
        b = self.blocks[1001]
        self.blocks[1001] = b[:500] + str((int(b[500]) + 1) % 10) + b[501:]
        out = self.go()
        self.assertEqual((out["test_passed"], out["blocks_matched"], out["block_digits_wrong"]), (0, 1, 1))

    def test_a_changed_count_fails(self):
        B.TABLE1 = (B.TABLE1[0] + 1,) + B.TABLE1[1:]
        out = self.go()
        self.assertEqual((out["test_passed"], out["counts_as_printed"]), (0, 9))

    def test_methods_that_disagree_are_refused(self):
        p = self.pi
        self.texts["agm"] = p[:1500] + str((int(p[1500]) + 1) % 10) + p[1501:]
        with self.assertRaises(B.Refused):
            self.go()

    def test_a_wrong_pi_is_refused(self):
        wrong = "3" + "2" + self.pi[2:]
        self.texts = {"chud": wrong, "agm": wrong}
        with self.assertRaises(B.Refused):
            self.go()


def have_gmp():
    if not shutil.which("gcc"):
        return False
    probe = subprocess.run(["gcc", "-x", "c", "-", "-o", os.devnull, "-lgmp"], input="#include <gmp.h>\nint main(void)"
                           "{mpz_t x; mpz_init(x); return 0;}\n", text=True, capture_output=True)
    return probe.returncode == 0


@unittest.skipUnless(have_gmp(), "needs gcc and GMP")
class TwoMethods(unittest.TestCase):
    def test_both_agree_with_pi_at_1000(self):
        d = tempfile.mkdtemp()
        try:
            exe = B.build(d)
            texts, notes = B.two_pis(exe, 1000, d)
            self.assertEqual(texts["chud"], texts["agm"])
            self.assertEqual(texts["chud"], "3" + pi_decimals(1000))
            self.assertRegex(notes["agm"], r"agm: \d+ iterations")
        finally:
            shutil.rmtree(d)


@unittest.skipUnless(HAVE, "needs the author's copy at inputs/ or BAILEY88_INPUTS")
class AuthorsCopy(unittest.TestCase):
    def test_blocks_and_table(self):
        blocks, rows = B.read_paper(PAPER)
        self.assertEqual(sorted(blocks), list(B.BLOCKS))
        self.assertEqual(blocks[1], pi_decimals(1000))
        self.assertEqual(blocks[29359001][-10:], "2272888253")
        self.assertEqual(rows[0], ("0", "2935072", "-928", "-0.5709"))
        for d, (digit, count, dev, z) in enumerate(rows):
            with self.subTest(digit=d):
                self.assertEqual((digit, dev, z), (str(d), str(int(count) - 2936000), B.z_text(int(count))))


if __name__ == "__main__":
    unittest.main()
