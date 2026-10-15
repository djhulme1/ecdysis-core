"""Rabung & Lotts's cyclic zipper bounds (vdw/rl2012.py and vdw/rl2012.c): the PDF reader on a PDF written here (its
resources by reference); Table 1's parse on token runs written here; rule 2's choice of z; the criterion against a
direct enumeration of every progression on small certificates built here; Euler's criterion; the closed form against
vdw/hhlm.py's build; and rl2012.c's scan and forbid against Python on colourings drawn here. No entry of the paper's
Table 1 is built or checked here.

Run with: python3 -m unittest discover -s tests -p test_rl2012.py
"""

import importlib.util
import os
import random
import shutil
import tempfile
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("vdw_rl2012", os.path.join(HERE, "..", "vdw", "rl2012.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
H = M.H

PAPER_PRIMES = {e[3] for row in M.TABLE1.values() for e in row if e[3]}


def make_pdf(content):
    """A one-page PDF whose page names its /Resources by reference, as the paper's do."""
    s = zlib.compress(content)
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: b"<< /Type /Page /Parent 2 0 R /Resources 5 0 R /Contents 4 0 R >>",
        4: b"<< /Length " + str(len(s)).encode() + b" /Filter /FlateDecode >>\nstream\n" + s + b"\nendstream",
        5: b"<< /Font << /F1 6 0 R /F2 7 0 R >> /ProcSet [/PDF /Text] >>",
        6: b"<< /Type /Font /Subtype /Type1 /BaseFont /AAAAAA+CMR10 >>",
        7: b"<< /Type /Font /Subtype /Type1 /BaseFont /BBBBBB+CMMI10 >>",
    }
    out = b"%PDF-1.4\n"
    for num, body in objs.items():
        out += str(num).encode() + b" 0 obj\n" + body + b"\nendobj\n"
    return out + b"trailer\n<< /Root 1 0 R >>\n%%EOF\n"


def tok(text, fam="CMR"):
    return (text, {"CMR": "X+CMR10", "CMMI": "X+CMMI12", "CMTI": "X+CMTI12", "CMSY": "X+CMSY10"}[fam])


def table_tokens(rows):
    """Table 1's token run for rows written here, in the paper's layout."""
    out = [tok("Table1:"), tok("caption", "CMTI"), tok("l", "CMTI"), tok("n", "CMSY"), tok("k", "CMTI")]
    out += [tok(str(k)) for k in range(2, 7)]
    for l, entries in rows.items():
        out.append(tok(str(l)))
        for strict, value, star, prime, mark in entries:
            if strict:
                out.append(tok(">", "CMMI"))
            out.append(tok(f"{value}{'*' if star else ''}"))
            if prime is not None:
                out.append(tok(f"({prime}){mark}"))
    return out + [tok("SomeoftheentriesinTable1deservecomments:")]


def made_up_rows():
    rows = {}
    for l in range(3, 13):
        rows[l] = tuple((l > 3, 10 * l + k, l == 11 and k == 2, (101 + l) if k == 4 else None, "Z" if k == 4 else "")
                        for k in range(2, 7))
    return rows


_LOGS = {}


def kappa_py(k, p, g, z, y):
    """Rule 3's colour of residue y, or None for a multiple of p (by the powers of g, listed once)."""
    if (p, g) not in _LOGS:
        logs, x = {}, 1
        for e in range(p - 1):
            logs[x] = e
            x = x * g % p
        _LOGS[(p, g)] = logs
    m = p if z == 0 else 2 * p
    y %= m
    if y % p == 0:
        return None
    e = _LOGS[(p, g)][y % p]
    return (e % k + (k // 2 if z == 1 and y % 2 == 0 else 0)) % k


def certificate(k, l, p, z, g):
    """The certificate of rule 3 with rule 4's colouring of the multiples, as a list."""
    n = (l - 1) * 2 ** z * p + 1
    out = []
    for y in range(n):
        if y % p == 0:
            j = y // p
            out.append((j // 2) % 2 if z else j % 2)
        else:
            out.append(kappa_py(k, p, g, z, y))
    return out


def mono_progression(cert, l, avoid_multiples_of=None):
    n = len(cert)
    for d in range(1, n):
        if (l - 1) * d > n - 1:
            break
        for x in range(0, n - (l - 1) * d):
            ys = [x + t * d for t in range(l)]
            if avoid_multiples_of and any(y % avoid_multiples_of == 0 for y in ys):
                continue
            if len({cert[y] for y in ys}) == 1:
                return x, d
    return None


class Reader(unittest.TestCase):
    def test_pdf_with_resources_by_reference(self):
        content = b"BT /F1 10 Tf (Table1:) Tj /F2 10 Tf (>) Tj /F1 10 Tf [(12)-20(3)] TJ ET"
        pages = M.Pdf(make_pdf(content)).pages()
        self.assertEqual(len(pages), 1)
        toks = H.page_tokens(*pages[0])
        self.assertEqual([t for t, _ in toks], ["Table1:", ">", "123"])
        self.assertEqual([H.family(f) for _, f in toks], ["CMR", "CMMI", "CMR"])
        bad = make_pdf(content).replace(b"/Resources 5 0 R ", b"")
        with self.assertRaises(M.Refused):
            M.Pdf(bad).pages()

    def test_table_parse(self):
        rows = made_up_rows()
        self.assertEqual(M.parse_table(table_tokens(rows)), rows)
        toks = table_tokens(rows)
        del toks[5]  # the header's 2
        with self.assertRaises(M.Refused):
            M.parse_table(toks)
        toks = table_tokens(rows)
        toks.insert(-1, tok("999"))
        with self.assertRaises(M.Refused):
            M.parse_table(toks)
        nb = M.new_bounds(rows)
        self.assertEqual(len(nb), 10)
        self.assertEqual(nb[0], (4, 3, 104, "Z", 34))

    def test_z_rule(self):
        self.assertEqual(M.z_for(9, 101, "Z", 8 * 101 + 1), (0, 809))
        self.assertEqual(M.z_for(9, 101, "Z", 16 * 101 + 1), (1, 1617))
        self.assertEqual(M.z_for(10, 101, "", 12345), (0, 910))
        self.assertEqual(M.z_for(8, 101, "ZZ", 99), (2, 2829))


class Criterion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp()
        cls.exe = M.compile_c(cls.work)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def cases(self):
        out = []
        for k in (2, 3, 4):
            for p in (q for q in range(13, 90) if H.is_prime(q) and (q - 1) % k == 0 and q not in PAPER_PRIMES):
                for l in (3, 4, 5):
                    out.append((k, l, p, 0))
                    if k % 2 == 0 and (k == 2 or ((p - 1) // k) % 2 == 1):
                        out.append((k, l, p, 1))
        return out

    def test_against_enumeration(self):
        seen = {"holds": 0, "refuted": 0, "undetermined": 0}
        for k, l, p, z in self.cases():
            g = H.least_primitive_root(p)
            v = M.verdict_of(M.crit(self.exe, k, l, p, z, g), z)
            seen[v] += 1
            cert = certificate(k, l, p, z, g)
            if v == "holds":
                self.assertIsNone(mono_progression(cert, l), (k, l, p, z))
            elif v == "refuted":
                self.assertIsNotNone(mono_progression(cert, l, avoid_multiples_of=p), (k, l, p, z))
        self.assertGreater(seen["holds"], 3)
        self.assertGreater(seen["refuted"], 3)

    def test_euler_criterion(self):
        for k, l, p, z in self.cases()[::7]:
            g = H.least_primitive_root(p)
            samples = list(range(1, p))
            res = M.crit(self.exe, k, l, p, z, g, samples)
            ok, info = M.chi_check(k, l, p, z, g, res, samples)
            self.assertTrue(ok, (k, l, p, z, info))
            for x in samples:
                self.assertEqual(res["sampled"][x], kappa_py(k, p, g, 0, x))

    def test_a_wrong_root_is_caught(self):
        res = M.crit(self.exe, 2, 3, 13, 0, 3)  # 3 has order 3 mod 13
        self.assertEqual(res["cover"], 0)
        self.assertEqual(M.verdict_of(res, 0), "refuted")

    def test_closed_form(self):
        # k = 2 with p = 1 mod 4 (reflection), k = 4 point symmetric, and unzipped
        for k, l, p, z in ((2, 4, 41, 1), (2, 5, 89, 1), (4, 3, 53, 1), (4, 4, 29, 1), (3, 4, 31, 0), (6, 3, 43, 0)):
            g = H.least_primitive_root(p)
            self.assertTrue(M.closed_form_matches(self.exe, self.work, k, l, p, z, g), (k, l, p, z))

    def test_full_check(self):
        row = M.full_check(self.exe, self.work, 2, 4, 11, 0, 2)
        self.assertTrue(row["holds"])
        row = M.full_check(self.exe, self.work, 2, 4, 13, 0, 2)
        self.assertFalse(row["holds"])


class Scans(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp()
        cls.exe = M.compile_c(cls.work)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def test_scan_and_forbid(self):
        rnd = random.Random(7)
        for i in range(25):
            n = rnd.randint(15, 90)
            r = rnd.randint(2, 4)
            l = rnd.randint(3, 12)
            cert = [rnd.randint(1, r) for _ in range(n)]
            free = [rnd.random() < 0.05 for _ in range(n)]
            path = os.path.join(self.work, f"c{i}.bin")
            H.write_colouring(path, cert, free)
            got = H.c_scan(self.exe, path, l)
            want, pairs = H.py_scan(cert, free, l)
            self.assertEqual((got["count"], got["pairs"]), (want, pairs))
            rows, multi = H.c_forbid(self.exe, path, l)
            py = H.py_forbid(cert, free, l)
            for y, bad in py.items():
                self.assertEqual(set(rows.get(y, {})), bad, (i, y))

    def test_long_progressions(self):
        cert = [1, 2] * 40
        cert[3::7] = [1] * len(cert[3::7])
        path = os.path.join(self.work, "long.bin")
        H.write_colouring(path, cert)
        got = H.c_scan(self.exe, path, 11)
        want, _ = H.py_scan(cert, [False] * len(cert), 11)
        self.assertEqual(got["count"], want)
        self.assertGreater(want, 0)


if __name__ == "__main__":
    unittest.main()
