"""The Cyclic Zipper check (vdw/hhlm.py and vdw/hhlm.c): the PDF reader on a PDF written here (page tree, indirect and
direct lengths, font dictionaries, tokens and fonts, refusals); the tables' renderings; primes and least primitive
roots on primes not in the paper; the power residue colouring, zipping and repetition on small cases worked by hand;
the C scans against a direct enumeration on colourings drawn here; the search on small cases; and the comparison
with Table 1 on rows written here. No certificate of the paper's Table 3 is built or checked here.

Run with: python3 -m unittest discover -s tests -p test_hhlm.py
"""

import importlib.util
import os
import random
import shutil
import tempfile
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("vdw_hhlm", os.path.join(HERE, "..", "vdw", "hhlm.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


def make_pdf(page1, page2, fonts2_inline=True, duplicate=False):
    """A two-page PDF: page 1's content Flate with an indirect /Length, page 2's with a direct one."""
    s1, s2 = zlib.compress(page1), zlib.compress(page2)
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >>",
        3: b"<< /Type /Page /Parent 2 0 R /Resources << /Font 5 0 R >> /Contents 4 0 R >>",
        4: b"<< /Length 9 0 R /Filter /FlateDecode >>\nstream\n" + s1 + b"\nendstream",
        5: b"<< /F1 7 0 R /F2 8 0 R >>",
        6: (b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 7 0 R /F2 8 0 R >> >> /Contents [10 0 R] >>"
            if fonts2_inline else b"<< /Type /Page /Parent 2 0 R /Resources << /Font 5 0 R >> /Contents [10 0 R] >>"),
        7: b"<< /Type /Font /Subtype /Type1 /BaseFont /AAAAAA+CMR10 >>",
        8: b"<< /Type /Font /Subtype /Type1 /BaseFont /BBBBBB+CMBX10 >>",
        9: str(len(s1)).encode(),
        10: b"<< /Length " + str(len(s2)).encode() + b" /Filter /FlateDecode >>\nstream\n" + s2 + b"\nendstream",
    }
    out = b"%PDF-1.3\n"
    for num, body in objs.items():
        out += str(num).encode() + b" 0 obj\n" + body + b"\nendobj\n"
    if duplicate:
        out += b"7 0 obj\n<< /Type /Font /BaseFont /CCCCCC+CMR10 >>\nendobj\n"
    return out + b"trailer\n<< /Size 11 /Root 1 0 R >>\n%%EOF\n"


PAGE1 = b"BT /F1 10 Tf 1 0 0 1 72 700 Tm (W)Tj (\\(2)Tj /F2 10 Tf (11495)Tj ET"
PAGE2 = b"BT /F1 10 Tf [(Using)-333(this)]TJ (\\014nal)Tj /F2 10 Tf (7)Tj ET"


class Reader(unittest.TestCase):
    def test_pages_tokens_fonts(self):
        pages = [M.page_tokens(c, f) for c, f in M.Pdf(make_pdf(PAGE1, PAGE2)).pages()]
        self.assertEqual(pages[0], [("W", "AAAAAA+CMR10"), ("(2", "AAAAAA+CMR10"), ("11495", "BBBBBB+CMBX10")])
        self.assertEqual(pages[1], [("Usingthis", "AAAAAA+CMR10"), ("\x0cnal", "AAAAAA+CMR10"),
                                    ("7", "BBBBBB+CMBX10")])
        self.assertEqual(M.page_text(pages[1]), "Usingthisfinal7")
        pages2 = [M.page_tokens(c, f) for c, f in M.Pdf(make_pdf(PAGE1, PAGE2, fonts2_inline=False)).pages()]
        self.assertEqual(pages2, pages)

    def test_refusals(self):
        with self.assertRaises(M.Refused):
            M.Pdf(make_pdf(PAGE1, PAGE2, duplicate=True))
        with self.assertRaises(M.Refused):
            M.page_tokens(b"BT /F9 10 Tf (x)Tj ET", {"F1": "AAAAAA+CMR10"})
        with self.assertRaises(M.Refused):
            M.page_tokens(b"BT (x)Tj ET", {"F1": "AAAAAA+CMR10"})
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, M.INPUT[0]), "wb") as fh:
                fh.write(make_pdf(PAGE1, PAGE2))
            with self.assertRaises(M.Refused):
                M.read_input(d)

    def test_find_table(self):
        pages = [M.page_tokens(c, f) for c, f in M.Pdf(make_pdf(PAGE1, PAGE2)).pages()]
        self.assertEqual(M.find_table(pages, [("(2", False), ("11495", True)]), (1, 1))
        self.assertEqual(M.find_table(pages, [("(2", None), ("11495", None)]), (1, 1))
        with self.assertRaises(M.Refused):
            M.find_table(pages, [("(2", False), ("11495", False)])     # the 11495 is bold
        with self.assertRaises(M.Refused):
            M.find_table(pages, [("W", None), ("11495", None)])        # not consecutive
        twice = [pages[0], pages[0]]
        with self.assertRaises(M.Refused):
            M.find_table(twice, [("(2", None), ("11495", None)])

    def test_statements(self):
        pages = [[("Additionally", "X+CMR12"), (",", "X+CMR12"), ("n", "X+CMR12"), ("um", "X+CMR12"),
                  ("C", "X+CMMI12"), ("1", "X+CMR8"), ("\x1a", "X+CMMI10"), ("p", "X+CMMI8")]]
        found = M.statements_found(pages, ("Additionally, num C1", "ρp", "num C2"))
        self.assertEqual(found, {"Additionally, num C1": True, "ρp": True, "num C2": False})


class Tables(unittest.TestCase):
    def test_renderings(self):
        t3 = M.table_tokens("table3")
        self.assertEqual(len(t3), 11 + 7 + 8 * len(M.TABLE3))
        self.assertEqual(sum(1 for _, b in t3 if b), sum(1 for row in M.TABLE3 if row[5]))
        t1 = M.table_tokens("table1")
        entries = [e for es in M.TABLE1.values() for e in es]
        self.assertEqual(len(t1), 10 + len(M.TABLE1) + sum(4 + e[1] + (e[3] is not None) for e in entries))
        t4 = M.table_tokens("table4")
        self.assertEqual(len(t4), 10 + len(M.TABLE4) + sum(1 + e[1] for es in M.TABLE4.values() for e in es))
        t2 = M.table_tokens("table2")
        self.assertEqual(len(t2), 27 + 4 * (12 + 9))
        self.assertEqual(sorted(v for row in M.TABLE2 for v in row), list(range(2, 38)))

    def test_bounds_rule(self):
        self.assertEqual(M.table1_bound(2, 3), 8)        # a known value, 9: W > 8
        self.assertEqual(M.table1_bound(2, 6), 1131)     # "> 1131"
        self.assertIsNone(M.table1_bound(6, 7))          # no entry
        self.assertIsNone(M.table1_bound(2, 2))


class Arithmetic(unittest.TestCase):
    def test_primes_and_roots(self):
        self.assertEqual([m for m in range(30) if M.is_prime(m)], [2, 3, 5, 7, 11, 13, 17, 19, 23, 29])
        self.assertEqual(M.prime_factors(360), [2, 3, 5])
        known = {3: 2, 5: 2, 7: 3, 13: 2, 23: 5, 41: 6, 71: 7, 191: 19, 409: 21}
        for p, g in known.items():
            self.assertEqual(M.least_primitive_root(p), g, p)
            self.assertTrue(M.full_order(g, p))
            self.assertFalse(any(M.full_order(h, p) for h in range(2, g)))
        with self.assertRaises(M.Refused):
            M.least_primitive_root(91)

    def test_power_residue_13(self):
        # 2 mod 13: e = 1..12 gives 2, 4, 8, 3, 6, 12, 11, 9, 5, 10, 7, 1; j = that + 1 in class ((e - 1) mod 4) + 1
        col, free = M.power_residue(13, 4, 2)
        self.assertEqual(col, [1, 4, 1, 4, 2, 1, 1, 3, 3, 4, 2, 3, 2])
        self.assertEqual(free, [True] + [False] * 12)
        self.assertEqual(M.residue_rows(13, 4, 2), [(3, 7, 6), (5, 13, 11), (9, 12, 8), (4, 10, 2)])
        with self.assertRaises(M.Refused):
            M.power_residue(13, 5, 2)            # 5 does not divide 12
        with self.assertRaises(M.Refused):
            M.power_residue(13, 4, 3)            # 3 has order 3 mod 13

    def test_point_symmetric_labels(self):
        # 13 = 5 mod 8: the reverse j -> 15 - j maps class 1 onto 3 and 2 onto 4 (see the colouring above)
        col, _ = M.power_residue(13, 4, 2)
        self.assertEqual(M.point_symmetric_labels(col, 4), {1: 1, 3: 4, 2: 2, 4: 3})
        relabelled, free, pi = M.labelled_residue(13, 4, 2)
        self.assertEqual(relabelled, [1, 3, 1, 3, 2, 1, 1, 4, 4, 3, 2, 4, 2])
        for j in range(2, 14):
            self.assertEqual(relabelled[15 - j - 1], 5 - relabelled[j - 1])
        self.assertEqual(M.labelled_residue(13, 4, 2, pi_labels=False)[0], col)
        # 17 = 1 mod 8: the reverse keeps every class (reflection symmetric), so no pi
        col17, _ = M.power_residue(17, 4, 3)
        self.assertIsNone(M.point_symmetric_labels(col17, 4))
        # r = 2, 7 = 3 mod 4: the reverse swaps the classes, and pi is the identity
        col7, _ = M.power_residue(7, 2, 3)
        self.assertEqual(M.point_symmetric_labels(col7, 2), {1: 1, 2: 2})
        with self.assertRaises(M.Refused):
            M.point_symmetric_labels([1, 2, 1, 2], 2)

    def test_zip_by_hand(self):
        col, free = M.power_residue(5, 2, 2)
        self.assertEqual(col, [1, 2, 1, 1, 2])
        z1, f1 = M.zip_once(col, free, 2, 5)
        # spread: 1, 3, 5, 7, 9 get 1, 2, 1, 1, 2; turned and shifted by 5: 6, 8, 10, 2, 4 get 2, 1, 2, 2, 1
        self.assertEqual(z1, [1, 2, 2, 1, 1, 2, 1, 1, 2, 2])
        self.assertEqual([i + 1 for i, f in enumerate(f1) if f], [1, 6])
        z2, f2 = M.zip_once(z1, f1, 2, 5)
        self.assertEqual(len(z2), 20)
        self.assertEqual([i + 1 for i, f in enumerate(f2) if f], [1, 6, 11, 16])
        for j in range(1, 11):
            self.assertEqual(z2[2 * j - 2], z1[j - 1])
            self.assertEqual(z2[(2 * j - 1 - 5 - 1) % 20], 3 - z1[j - 1])
        with self.assertRaises(M.Refused):
            M.zip_once([1, 2, 1, 2], [False] * 4, 2, 2)    # an even shift lands on the spread copy

    def test_build(self):
        # 13 with pi: zipped once, the turned copy holds each number's point symmetric partner
        cert, free, N = M.build(4, 3, 13, 1, 2)
        base = M.labelled_residue(13, 4, 2)[0]
        self.assertEqual((N, len(cert)), (26, 53))
        for j in range(1, 14):
            self.assertEqual(cert[2 * j - 2], base[j - 1])
            self.assertEqual(cert[(2 * j - 1 - 13 - 1) % 26], 5 - base[j - 1])
        raw, _, _ = M.build(4, 3, 13, 1, 2, pi_labels=False)
        self.assertNotEqual(raw[:26], cert[:26])
        cert, free, N = M.build(2, 3, 5, 1, 2)
        self.assertEqual((N, len(cert)), (10, 21))
        self.assertEqual(cert[:20], [1, 2, 2, 1, 1, 2, 1, 1, 2, 2] * 2)
        self.assertEqual(cert[20], 2)                            # the added number in C_r
        self.assertEqual([i + 1 for i, f in enumerate(free) if f], [1, 6, 11, 16, 21])


@unittest.skipIf(shutil.which("gcc") is None, "no gcc")
class Scans(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp()
        cls.exe = M.compile_c(cls.work)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work)

    def test_against_enumeration(self):
        rng = random.Random(20261014)
        for _ in range(40):
            n, r, k = rng.randrange(10, 70), rng.randrange(2, 5), rng.randrange(3, 7)
            cert = [rng.randrange(1, r + 1) for _ in range(n)]
            free = [rng.random() < 0.05 for _ in range(n)]
            path = os.path.join(self.work, "t.bin")
            M.write_colouring(path, cert, free)
            sc = M.c_scan(self.exe, path, k)
            self.assertEqual((sc["count"], sc["pairs"]), M.py_scan(cert, free, k))
            fb, _ = M.c_forbid(self.exe, path, k)
            self.assertEqual({y: set(w) for y, w in fb.items()}, M.py_forbid(cert, free, k))
            if sc["count"]:
                x, d = sc["first"]
                self.assertEqual(len({cert[x + t * d - 1] for t in range(k)}), 1)
            for y, w in fb.items():
                for c, (x, d) in w.items():
                    ys = [x + t * d for t in range(k)]
                    self.assertIn(y, ys)
                    self.assertEqual({cert[v - 1] for v in ys if v != y}, {c})

    def test_known_certificates(self):
        # 1..8 in two classes with no 3-term progression in one class (W(2, 3) = 9), and every extension fails
        word = [1, 1, 2, 2, 1, 1, 2, 2]
        path = os.path.join(self.work, "w.bin")
        M.write_colouring(path, word)
        self.assertEqual(M.c_scan(self.exe, path, 3)["count"], 0)
        for c in (1, 2):
            M.write_colouring(path, word + [c])
            self.assertGreater(M.c_scan(self.exe, path, 3)["count"], 0)
        # a seeded colouring of 399 numbers in 3 classes, a 9-term progression planted in it
        rng = random.Random(7)
        cert = [rng.randrange(1, 4) for _ in range(399)]
        cert[10 - 1:10 + 8 * 20:20] = [cert[9]] * 9
        M.write_colouring(path, cert)
        sc = M.c_scan(self.exe, path, 9)
        self.assertGreaterEqual(sc["count"], 1)
        self.assertEqual(sc["count"], M.py_scan(cert, [False] * len(cert), 9)[0])

    def test_multi(self):
        cert = [1, 2, 1, 2, 1, 2, 1]
        free = [True, False, True, False, False, False, False]          # 1, 3 free: 1, 3, 5 mixes
        path = os.path.join(self.work, "m.bin")
        M.write_colouring(path, cert, free)
        _, multi = M.c_forbid(self.exe, path, 3)
        self.assertGreater(multi, 0)


class Search(unittest.TestCase):
    def test_own_first(self):
        assign, nodes = M.search([1, 6, 11], {}, [2, 1, 2], [], 3)
        self.assertEqual(assign, [2, 1, 2])
        self.assertEqual(nodes, 3)

    def test_forbidden_and_progressions(self):
        self.assertIsNone(M.search([1, 6], {6: {1, 2}}, [1, 1], [], 2)[0])
        assign, _ = M.search([1, 6, 11], {6: {1}}, [1, 1, 1], [(1, 6, 11)], 2)
        self.assertEqual(assign, [1, 2, 1])
        assign, _ = M.search([1, 6, 11], {}, [1, 1, 1], [(1, 6, 11)], 2)
        self.assertEqual(assign, [1, 1, 2])
        self.assertEqual(M.free_progressions([1, 6, 11, 16], 16, 3), [(1, 6, 11), (6, 11, 16)])
        self.assertEqual(M.free_progressions([1, 6, 11, 16], 16, 4), [(1, 6, 11, 16)])


class Machinery(unittest.TestCase):
    def test_outputs(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")

    def test_stream(self):
        a, b = M.Stream("ab" * 32, "x"), M.Stream("ab" * 32, "x")
        self.assertEqual([a.below(1000) for _ in range(5)], [b.below(1000) for _ in range(5)])


if __name__ == "__main__":
    unittest.main()
