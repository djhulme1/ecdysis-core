"""The shifted S-template (schur/shifted2026.py) on inputs written here, never the paper's: the TeX table reader on an
e-print built in memory (Abbott and Hanson's construction written as a shifted template), its refusals; the PDF reader
on a PDF built here (cross-reference table, a nested page tree, Flate streams, a table set as the appendix of Ageron
et al. sets it, with commas from another font and a page number after it), its refusals; both constructions on the
partition of 1..4 into 2, and their agreement; Definition 2.1 and Definition 3 on that template and on broken ones; the
two sum-free tests against a direct search on random colourings and on planted sums; the greedy bases. The paper's
template, its bounds and Ageron et al.'s tables are not read or built here.

Run with: python3 -m unittest discover -s tests -p test_shifted2026.py
"""

import importlib.util
import io
import os
import random
import tarfile
import tempfile
import unittest
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("schur_shifted2026", os.path.join(HERE, "..", "schur", "shifted2026.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

AH_ROW = r"$A$ & $B$ & $B$ & $A$ & $P_0$ & $P_{0}$ & $A$ & $P_0$ & $P_0$"
AH_TEX = "\n".join([
    r"\begin{table}[h]",
    r"\caption{Abbott and Hanson's construction as a shifted S-template.}",
    r"\label{cert}",
    r"\centering",
    r"\begin{tabular}{c|ccccccccc}",
    r"\toprule",
    r" & 1 & 2 & 3 & 4 & 5 & 6 & 7 & 8 & 9\\",
    r"\midrule",
    r"$F$ & " + AH_ROW + r"\\",
    r"$M$ & " + AH_ROW + r"\\",
    r"$L$ & " + AH_ROW + r"\\",
    r"\bottomrule",
    r"$Q$ & $A$ & $B$ & $B$ & $A$ &  &  &  &  & \\",
    r"\end{tabular}",
    r"\end{table}",
])
AH_SETS = [[1, 4, 7], [2, 3], [5, 6, 8, 9]]          # the same construction as an S-template of width 9
BASE4 = np.array([0, 1, 2, 2, 1], dtype=np.int32)    # {1, 4}, {2, 3}


def eprint(tex, name=None):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        data = tex.encode("utf-8")
        info = tarfile.TarInfo(name or M.TEX)
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def make_pdf(pages):
    """A catalogue, a page tree with one nested node, one page and one Flate stream per content string."""
    objs = {1: b"<< /Type /Catalog /Pages 2 0 R >>"}
    nums = []
    for i, content in enumerate(pages):
        pn, sn = 10 + 2 * i, 11 + 2 * i
        nums.append(pn)
        z = zlib.compress(content.encode("latin-1"))
        objs[pn] = (f"<< /Type /Page /Contents {sn} 0 R /Parent 2 0 R /Resources << /Font << /F1 5 0 R >> >> "
                    f"/Annots [ (a (nested) string) ] >>").encode()
        objs[sn] = f"<< /Length {len(z)} /Filter /FlateDecode >>\nstream\n".encode() + z + b"\nendstream"
    objs[3] = f"<< /Type /Pages /Count {len(nums) - 1} /Parent 2 0 R /Kids [{' '.join(f'{n} 0 R' for n in nums[1:])}] >>".encode()
    objs[2] = f"<< /Type /Pages /Count {len(nums)} /Kids [{nums[0]} 0 R 3 0 R] >>".encode()
    out = bytearray(b"%PDF-1.5\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += f"{num} 0 obj\n".encode() + objs[num] + b"\nendobj\n"
    xref, size = len(out), max(objs) + 1
    out += f"xref\n0 {size}\n".encode()
    for num in range(size):
        out += f"{offsets[num]:010d} 00000 n \n".encode() if num in offsets else b"0000000000 65535 f \n"
    out += f"trailer\n<< /Size {size} /Root 1 0 R /ID [<AB> <AB>] >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def cell(y, numbers, wrap_after=None):
    """A list cell as the appendix sets it: digits in one font, each comma from another, at the code of ';'."""
    parts = [f"BT /F73 8.9664 Tf 80 {y} Td [({numbers[0]})]TJ"]
    for j, v in enumerate(numbers[1:], 1):
        parts.append("/F75 8.9664 Tf 4.6 0 Td [(;)]TJ")
        move = "-40 -10 Td" if wrap_after == j else "4.1 0 Td"
        parts.append(f"/F73 8.9664 Tf {move} [({v})]TJ")
    return " ".join(parts) + " ET"


def table_page(sets, caption="[(T)83(able)-333(5:)-444(S-template)-334(with)-333(width)-333(9)-334(and)-333(3)-333(colors)]TJ",
               labels=None):
    lines = [f"BT /F19 9.9626 Tf 100 700 Td {caption} ET"]
    for i, s in enumerate(sets):
        y = 650 - 20 * i
        lines.append(f"BT /F73 8.9664 Tf 50 {y} Td [({(labels or range(1, len(sets) + 1))[i]})]TJ ET")
        lines.append(cell(y, s, wrap_after=2 if len(s) > 3 else None))
    lines.append("BT /F19 9.9626 Tf 300 50 Td [(7)]TJ ET")
    return "\n".join(lines)


HEADING = "BT /F87 14.3462 Tf 50 700 Td [(B)-1125(WS-templates)]TJ ET"


def first_sum_direct(h, c):
    n = len(h) - 1
    mem = [x for x in range(1, n + 1) if h[x] == c]
    s = set(mem)
    for a in mem:
        if 2 * a > n:
            break
        for b in mem:
            if b < a:
                continue
            if a + b > n:
                break
            if a + b in s:
                return (a, b)
    return None


class Reading(unittest.TestCase):
    def test_template_read(self):
        rows, tail, q = M.read_template(M.read_tex(eprint(AH_TEX)))
        self.assertEqual(q, 9)
        self.assertEqual([M.NAMES[x] for x in rows["F"]], ["A", "B", "B", "A", "P0", "P0", "A", "P0", "P0"])
        self.assertEqual(rows["F"], rows["M"])
        self.assertEqual([M.NAMES[x] for x in tail], ["A", "B", "B", "A"])
        self.assertEqual(M.label("P_{-1}"), ("P", -1))
        self.assertEqual(M.label("P_1"), ("P", 1))

    def test_template_refusals(self):
        with self.assertRaises(M.Refused):
            M.read_template(AH_TEX.replace(r"\label{cert}", r"\label{other}"))
        with self.assertRaises(M.Refused):
            M.read_template(AH_TEX.replace("$F$ & $A$", "$F$ & $C$"))
        with self.assertRaises(M.Refused):
            M.read_template(AH_TEX.replace(r"$P_0$ & $P_0$\\", r"$P_0$\\", 1))
        with self.assertRaises(M.Refused):
            M.read_template(AH_TEX.replace(r"$Q$ & $A$ & $B$", r"$Q$ & $A$ & "))
        with self.assertRaises(M.Refused):
            M.read_tex(eprint(AH_TEX, name="other.tex"))
        with self.assertRaises(M.Refused):
            M.read_tex(b"not a tar")

    def test_pdf_tables_read(self):
        data = make_pdf([table_page(AH_SETS), HEADING])
        lines = M.pdf_lines(data)
        self.assertIn("Table 5: S-template with width 9 and 3 colors", lines)
        got = M.read_s_templates(lines, tables={5: (9, 3)})
        self.assertEqual(got[5]["sets"], AH_SETS)
        self.assertEqual(got[5]["after"], ["7"])

    def test_pdf_refusals(self):
        with self.assertRaises(M.Refused):                       # colour numbers out of order
            M.read_s_templates(M.pdf_lines(make_pdf([table_page(AH_SETS, labels=[1, 3, 2]), HEADING])),
                               tables={5: (9, 3)})
        with self.assertRaises(M.Refused):                       # 9 missing from a table the test uses
            M.read_s_templates(M.pdf_lines(make_pdf([table_page([[1, 4, 7], [2, 3], [5, 6, 8]]), HEADING])),
                               tables={5: (9, 3)}, strict=(5,))
        with self.assertRaises(M.Refused):                       # the caption names another width
            M.read_s_templates(M.pdf_lines(make_pdf([table_page(AH_SETS), HEADING])), tables={5: (10, 3)})
        data = make_pdf([table_page(AH_SETS)])
        with self.assertRaises(M.Refused):                       # startxref pointing elsewhere
            M.pdf_lines(data.replace(b"startxref\n", b"startxref\n1"))

    def test_table_leaving_one_out(self):
        got = M.read_s_templates(M.pdf_lines(make_pdf([table_page([[1, 4, 7], [2, 3], [5, 6, 8]]), HEADING])),
                                 tables={5: (9, 3)}, strict=())[5]
        self.assertEqual((got["missing"], got["repeated"]), ([9], []))
        self.assertEqual(M.completions(got), [3])             # 9 + 9 - 9 = 9 in colour 1; 9 + 2 - 9 = 2 in colour 2
        self.assertEqual(M.usable(got), AH_SETS)
        twice = dict(got, missing=[], repeated=[4])
        self.assertIsNone(M.completions(twice))
        self.assertIsNone(M.usable(twice))

    def test_input_hash(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, M.EPRINT[0]), "wb") as fh:
                fh.write(b"x")
            with self.assertRaises(M.Refused):
                M.read_input(d, M.EPRINT)

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed", inputs="nowhere")


class Constructions(unittest.TestCase):
    def setUp(self):
        self.rows, self.tail, self.q = M.read_template(M.read_tex(eprint(AH_TEX)))

    def test_shifted_on_four(self):
        h = M.shifted(BASE4, 2, self.rows, self.tail, self.q)
        self.assertEqual(len(h) - 1, 40)
        self.assertEqual(h[1:10].tolist(), [3, 4, 4, 3, 1, 1, 3, 1, 1])
        self.assertEqual(h[10:19].tolist(), [3, 4, 4, 3, 2, 2, 3, 2, 2])
        self.assertEqual(h[28:37].tolist(), [3, 4, 4, 3, 1, 1, 3, 1, 1])
        self.assertEqual(h[37:].tolist(), [3, 4, 4, 3])
        v = M.Tally().verdict(h, 4)
        self.assertTrue(v["sum_free"])

    def test_shifts_reach_rows(self):
        rows = {t: list(r) for t, r in self.rows.items()}
        rows["M"][4] = ("P", -1)
        rows["L"][5] = ("P", 1)                                   # illicit on L: leaves its cell uncoloured
        h = M.shifted(BASE4, 2, rows, self.tail, self.q)
        self.assertEqual(h[9 + 5], BASE4[1])                      # row 2, column 5 takes g(1)
        self.assertEqual(h[27 + 6], 0)
        self.assertFalse(M.Tally().verdict(h, 4)["covered"])

    def test_s_template_matches(self):
        hs = M.s_template(BASE4, 2, AH_SETS, 9)
        self.assertEqual(len(hs) - 1, 40)
        relabel = np.array([0, 3, 4, 1, 2], dtype=np.int32)
        self.assertEqual(relabel[hs].tolist(), M.shifted(BASE4, 2, self.rows, self.tail, self.q).tolist())
        self.assertTrue(M.Tally().verdict(hs, 4)["sum_free"])

    def test_definition_21(self):
        self.assertIsNone(M.definition_21(AH_SETS, 9))
        self.assertIsNotNone(M.definition_21([[1, 2, 4, 7], [3], [5, 6, 8, 9]], 9))
        self.assertIsNotNone(M.definition_21([[1, 4, 7, 9], [2, 3], [5, 6, 8]], 9))   # 9 + 9 - 9 = 9

    def test_definition_3(self):
        breach, counts = M.admissible(self.rows, self.tail, self.q)
        self.assertIsNone(breach)
        self.assertEqual(sorted(counts), list(M.MODEL_SIZES))
        rows = {t: list(r) for t, r in self.rows.items()}
        rows["M"][0] = ("P", 0)                                   # P0 + P0 with no carry: 1 + 5 -> 6
        self.assertIsNotNone(M.admissible(rows, self.tail, self.q)[0])
        rows = {t: list(r) for t, r in self.rows.items()}
        rows["F"][4] = ("P", -1)
        self.assertIn("illicit", M.admissible(rows, self.tail, self.q)[0])
        bad_tail = [("N", 1), ("N", 1)]                          # the tail's A plus row F's A lands on its A
        self.assertIsNotNone(M.admissible(self.rows, bad_tail, self.q)[0])

    def test_mutations_listed(self):
        changes = list(M.mutations(self.rows))
        self.assertEqual(len(changes), 9 * 3 + 9 * 4 + 9 * 3)


class SumFree(unittest.TestCase):
    def test_tests_agree_with_direct_search(self):
        rng = random.Random(7)
        tally = M.Tally()
        for n in (1, 2, 3, 62, 63, 64, 65, 127, 128, 129, 300, 1000):
            for _ in range(6):
                k = rng.randint(1, 5)
                h = np.zeros(n + 1, dtype=np.int32)
                h[1:] = [rng.randint(1, k) for _ in range(n)]
                for c in range(1, k + 1):
                    want = first_sum_direct(h, c)
                    self.assertEqual(M.first_sum_compiled(h, c), want)
                    self.assertEqual(M.first_sum_integers(h, c), want)
                tally.verdict(h, k)
        self.assertEqual(tally.disagreements, [])

    def test_sum_free_sets_pass(self):
        h = np.zeros(200 + 1, dtype=np.int32)
        h[1:] = 2
        h[1::2] = 1                                               # odd numbers: sum-free
        h[2::2] = 3
        v = M.Tally().verdict(h, 3)
        self.assertNotIn(1, v["sums"])
        self.assertIn(3, v["sums"])
        odd = np.where(np.arange(201) % 2 == 1, 1, 0).astype(np.int32)
        self.assertIsNone(M.first_sum_compiled(odd, 1))
        self.assertIsNone(M.first_sum_integers(odd, 1))

    def test_doubles_and_planting(self):
        h = np.zeros(1000 + 1, dtype=np.int32)
        h[1:] = 2
        h[1::2] = 1
        h[500] = 1                                                # 1 + 499 = 500 (and 1 + 500 = 501)
        self.assertEqual(M.first_sum_integers(h, 1), (1, 499))
        self.assertEqual(M.first_sum_compiled(h, 1), (1, 499))
        g = np.zeros(1000 + 1, dtype=np.int32)
        g[1:] = 2
        g[1::2] = 1
        g[300] = 1                                                # 1 + 299 = 300
        self.assertEqual(M.first_sum_compiled(g, 1), (1, 299))
        self.assertEqual(M.first_sum_integers(g, 1), (1, 299))
        d = np.zeros(10, dtype=np.int32)
        d[1:] = 2
        d[3] = d[6] = 1                                           # 3 + 3 = 6
        self.assertEqual(M.first_sum_compiled(d, 1), (3, 3))
        self.assertEqual(M.first_sum_integers(d, 1), (3, 3))
        st = M.FS.Stream("0" * 64, "test/plant")
        odd = np.where(np.arange(1001) % 2 == 1, 1, 2).astype(np.int32)
        odd[0] = 0
        self.assertIsNone(M.first_sum_compiled(odd, 1))
        hp, c, ab = M.plant(odd, st, [1])
        self.assertEqual(hp[sum(ab)], 1)
        s = M.first_sum_compiled(hp, c)
        self.assertIsNotNone(s)
        self.assertTrue(M.genuine(hp, s, c))


class Bases(unittest.TestCase):
    def test_greedy_bases(self):
        seed = "ab" * 32
        for i in range(10):
            k, g = M.greedy_base(seed, i)
            self.assertEqual(k, 2 + i % 5)
            self.assertGreaterEqual(len(g) - 1, 3)
            self.assertTrue(set(g[1:].tolist()) <= set(range(1, k + 1)))
            for c in range(1, k + 1):
                self.assertIsNone(first_sum_direct(g, c))
            k2, g2 = M.greedy_base(seed, i)
            self.assertEqual(g.tolist(), g2.tolist())
        self.assertNotEqual(M.greedy_base(seed, 4)[1].tolist(), M.greedy_base("cd" * 32, 4)[1].tolist())


if __name__ == "__main__":
    unittest.main()
