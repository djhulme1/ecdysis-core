"""Fredricksen & Sweet's partitions (schur/fs.py): the PDF reader on a document built here (Flate streams, TJ spacing,
page headers); the listing rule and the split pair; the sum-free and triangle tests on the classical partition of
1..13 into three sets and on broken copies; depth, e-depth and multipliers; the exhaustive search for S(1), S(2) and
S(3); the verdict at and beside each condition; the seed refused. The paper's PDF is not read here.

Run with: python3 -m unittest discover -s tests -p test_fs.py
"""

import importlib.util
import os
import tempfile
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("schur_fs", os.path.join(HERE, "..", "schur", "fs.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

P13 = [[1, 4, 10, 13], [2, 3, 11, 12], [5, 6, 7, 8, 9]]       # the classical sum-free partition of 1..13 into 3


def tj(numbers):
    """A TJ array setting numbers the way the paper's PDF does: digits joined by +333, numbers apart by +23."""
    parts = []
    for k, x in enumerate(numbers):
        digits = str(x)
        for j, d in enumerate(digits):
            adj = 333 if j < len(digits) - 1 else (23 if k < len(numbers) - 1 else 0)
            parts.append(f"({d}){adj}" if adj else f"({d})")
    return "[" + "".join(parts) + "]TJ"


def pdf(streams):
    out = [b"%PDF-1.2\n"]
    for i, s in enumerate(streams, 2):
        z = zlib.compress(s.encode("latin-1"))
        out.append(f"{i} 0 obj\n<<\n/Length {len(z)}\n/Filter /FlateDecode\n>>\nstream\r\n".encode() + z
                   + b"\r\nendstream\nendobj\n")
    return b"".join(out)


def page(lines, number):
    body = ["BT", "/F15 1 Tf", "10 0 0 10 100 700 Tm", "0 Tc",
            "[(the)-354(electronic)-368(journal)-375(of)-376(combinatorics)]TJ", "/F10 1 Tf", "30 0 TD", "(7)Tj",
            "1 0 TD", "[(\\(2000\\),)-378(#R32)]TJ",
            "1 0 TD", f"({number})Tj", "0.333 Tc"]
    for line in lines:
        body.append("0 -1.7 TD")
        body.append(line)
    body.append("ET")
    return "\n".join(body)


class Reader(unittest.TestCase):
    def doc(self):
        p1 = page(["0 Tc", "[(P)-1(a)(r)(t)(i)(t)(i)(o)(n)-333(o)(f)-333(1)(3)-333(i)(n)(t)(o)-333(3)-333(s)(y)(m)(m)(e)(t)"
                   "(r)(i)(c)-333(s)(u)(m)(f)(r)(e)(e)-333(s)(e)(t)(s)(:)]TJ".replace("-333", "-400"),
                   "0.333 Tc", "[(S)341(e)349(t)8(1)333(:)-104" + tj([1, 4])[1:],
                   "[(S)341(e)349(t)8(2)333(:)-104" + tj([2, 3])[1:]], 1)
        p2 = page(["[(S)341(e)349(t)8(3)333(:)-104" + tj([5, 6])[1:], tj([7]), "(\\()Tj"], 2)
        return pdf([p1, p2])

    def test_spacing(self):
        lines = M.document_lines(pdf([page([tj([4, 5, 15, 16, 22, 28])], 1)]))
        self.assertIn("4 5 15 16 22 28", lines)

    def test_headers_dropped_and_partition_read(self):
        lines = M.document_lines(self.doc())
        self.assertNotIn("the electronic journal of combinatorics", lines)
        self.assertIn("Partition of 13 into 3 symmetric sumfree sets:", lines)
        sets = M.read_partition(lines, 13, 3)
        self.assertEqual(sets, [[1, 4], [2, 3], [5, 6, 7]])
        self.assertEqual(M.expand(sets, 13), P13)

    def test_reading_errors_refused(self):
        lines = M.document_lines(self.doc())
        with self.assertRaises(M.Refused):
            M.read_partition(lines, 13, 4)
        with self.assertRaises(M.Refused):
            M.read_partition(lines, 14, 3)
        with self.assertRaises(M.Refused):
            M.read_partition(["Partition of 13 into 3 symmetric sumfree sets:", "Set 1: 1 4", "Set 2: 2 3 4",
                              "Set 3: 5 6 7"], 13, 3)

    def test_hash_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, M.INPUT[0]), "wb") as fh:
                fh.write(b"%PDF-1.2\n")
            with self.assertRaises(M.Refused):
                M.read_input(d)

    def test_unescape(self):
        self.assertEqual(M.unescape(b"a\\(b\\)\\256"), b"a(b)\xae")


class Rules(unittest.TestCase):
    def test_split_pair(self):
        self.assertEqual(M.special(536), {179, 358})
        self.assertEqual(M.special(1680), set())
        self.assertEqual(M.expand([[179, 1], [358, 2]], 536), [[1, 179, 536], [2, 358, 535]])

    def test_sum_free(self):
        self.assertEqual([M.sums_inside(s) for s in P13], [0, 0, 0])
        self.assertTrue(M.is_partition(P13, 13))
        self.assertEqual(M.sums_inside([2, 4]), 1)                    # 2 + 2 = 4: a = b counts
        self.assertEqual(M.sums_inside([1, 2, 3]), 2)                 # 1 + 1 = 2 and 1 + 2 = 3
        self.assertFalse(M.is_partition([[1, 2], [2, 3]], 3))

    def test_triangles(self):
        self.assertEqual(M.triangles(P13, 13)[0], 0)
        self.assertEqual(M.triangles(P13, 13)[1], 14 * 13 // 2)
        self.assertEqual(M.triangles([[1, 2, 3]], 3)[0], 4)          # K4 in one colour
        broken = [[1, 4, 10, 13, 3, 11], [2, 12], [5, 6, 7, 8, 9]]  # 1 + 3 = 4
        self.assertGreater(M.sums_inside(broken[0]), 0)
        self.assertGreater(M.triangles(broken, 13)[0], 0)

    def test_depth_and_multipliers(self):
        self.assertEqual(M.depth(P13), 5)
        d, m = M.e_depth(P13, 13)
        self.assertGreaterEqual(d, 5)
        for k in (1, 3, 5, 9, 11, 13):
            mp = M.multiply(P13, k, 13)
            self.assertTrue(M.symmetric(mp, 13) and M.is_partition(mp, 13))
            self.assertEqual([M.sums_inside(s) for s in mp], [0, 0, 0])
        self.assertTrue(M.symmetric(P13, 13))
        self.assertFalse(M.symmetric([[1, 4, 10], [2, 3, 11, 12, 13], [5, 6, 7, 8, 9]], 13))

    def test_small_schur_numbers(self):
        self.assertEqual([M.schur_number(k) for k in (1, 2, 3)], [1, 4, 13])
        self.assertIsNone(M.schur_search(3, 14))
        p = M.schur_search(3, 13)
        self.assertTrue(M.is_partition(p, 13) and all(M.sums_inside(s) == 0 for s in p))

    def test_perturb(self):
        st = M.Stream("ab" * 32, "t")
        listed = [[1, 4], [2, 3], [5, 6, 7]]
        for _ in range(10):
            sets, x, src, dst = M.perturb(listed, 13, st)
            self.assertNotEqual(src, dst)
            self.assertTrue(M.is_partition(sets, 13))


class Verdict(unittest.TestCase):
    def found(self, **kw):
        f = {n: {"partition": True, "sums": 0, "triangles": 0} for n in (536, 1680)}
        for key, v in kw.items():
            n, field = key.split("_", 1)
            f[int(n[1:])][field] = v
        return f

    def test_conditions(self):
        c = M.conditions(self.found())
        self.assertEqual(len(c), 4)
        self.assertTrue(all(c.values()))
        self.assertEqual(sum(M.conditions(self.found(n536_sums=1)).values()), 3)
        self.assertEqual(sum(M.conditions(self.found(n1680_partition=False)).values()), 3)
        self.assertEqual(sum(M.conditions(self.found(n1680_triangles=2)).values()), 3)

    def test_outputs_named(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


if __name__ == "__main__":
    unittest.main()
