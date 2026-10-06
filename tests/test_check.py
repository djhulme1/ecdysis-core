"""The checker on Strassen's scheme written in each paper's format, and on broken copies of it.

A check that cannot fail is not a check: every format is read back, passes, and then fails once one
coefficient is changed. Run with: python3 -m unittest discover -s tests
"""

import hashlib
import json
import os
import struct
import sys
import tempfile
import unittest
import zipfile
from fractions import Fraction
from io import BytesIO

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mm"))
import check as C  # noqa: E402

SEED = "0" * 64
OTHER = "f" * 64


def flips_text(scheme, n, m, p, negate=()):
    """A scheme in Kauers & Moosbauer's .exp format; the products in negate written as -(...)."""

    def form(d, letter, cols, sign=1):
        terms = ""
        for idx, x in sorted(d.items()):
            x *= sign
            i, j = divmod(idx, cols)
            terms += ("-" if x < 0 else "+") + ("" if abs(x) == 1 else f"{abs(x)}*") + f"{letter}{i + 1}{j + 1}"
        return "(" + terms.lstrip("+") + ")"

    lines = []
    for r, (u, v, w) in enumerate(scheme):
        if r in negate:
            lines.append(f"-({form(u, 'a', m, -1)}*{form(v, 'b', p)}*{form(w, 'c', n)})")
        else:
            lines.append(f"{form(u, 'a', m)}*{form(v, 'b', p)}*{form(w, 'c', n)}")
    return ("\n".join(lines) + "\n").encode("ascii")


def npz(key, scheme, rows):
    """An .npz holding u, v, w stacked as one (3, rows, R) array of little-endian int64, as AlphaTensor's."""
    rank = len(scheme)
    flat = [scheme[r][f].get(row, 0) for f in range(3) for row in range(rows) for r in range(rank)]
    header = repr({"descr": "<i8", "fortran_order": False, "shape": (3, rows, rank)}).encode("latin1")
    header += b" " * (63 - (len(header) + 10) % 64) + b"\n"
    body = b"\x93NUMPY\x01\x00" + struct.pack("<H", len(header)) + header + struct.pack(f"<{len(flat)}q", *flat)
    out = BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr(f"{key}.npy", body)
    return out.getvalue()


def notebook(name, scheme, rows, change=None):
    """A notebook whose data cell assigns the scheme as numpy prints complex arrays."""

    def num(x):
        return f"{float(x):.1f}+0.j"

    mats = []
    for f in range(3):
        cells = [[num(scheme[r][f].get(row, 0)) for r in range(len(scheme))] for row in range(rows)]
        if change and change[0] == f:
            cells[change[1]][change[2]] = change[3]
        mats.append("np.array([" + ",\n       ".join("[" + ", ".join(row) + "]" for row in cells) + "],\n      dtype=np.complex64)")
    src = f"#@title Data\n{name} = (" + ", ".join(mats) + ")"
    return json.dumps({"cells": [{"cell_type": "markdown", "source": ["text"]}, {"cell_type": "code", "source": src.splitlines(True)}]}).encode("utf-8")


def sms(rows, cols, entries):
    lines = ["# a test matrix", f"{rows} {cols} R"] + [f"{i + 1} {j + 1} {v}" for (i, j), v in sorted(entries.items())] + ["0 0 0"]
    return ("\n".join(lines) + "\n").encode("ascii")


def strassen_lrp():
    """Strassen's scheme as L (7 x 4), R (7 x 4) and P (4 x 7), every matrix flattened row by row."""
    L, R, P = {}, {}, {}
    for r, (u, v, w) in enumerate(C.strassen()):
        for a, x in u.items():
            L[(r, a)] = x
        for b, y in v.items():
            R[(r, b)] = y
        for c, z in w.items():
            k, i = divmod(c, 2)
            P[(i * 2 + k, r)] = z
    return L, R, P


class Checks(unittest.TestCase):
    def test_strassen_passes_over_every_ring(self):
        for ring in ("Z", "F2", "Q"):
            self.assertEqual(C.wrong_entries(C.strassen(), 2, 2, 2, ring), 0)
        self.assertEqual(C.wrong_entries([tuple({k: C.G(x) for k, x in d.items()} for d in t) for t in C.strassen()], 2, 2, 2, "QI"), 0)

    def test_a_missing_or_changed_product_fails(self):
        s = C.strassen()
        self.assertGreater(C.wrong_entries(s[:-1], 2, 2, 2, "Z"), 0)
        u, v, w = s[0]
        self.assertGreater(C.wrong_entries([(u, v, {**w, 1: 1})] + s[1:], 2, 2, 2, "Z"), 0)
        # Over GF(2) a coefficient of 2 is a coefficient of 0.
        self.assertGreater(C.wrong_entries([(u, v, {0: 1, 3: 2})] + s[1:], 2, 2, 2, "F2"), 0)

    def test_the_probe_multiplies_and_its_digest_follows_the_seed(self):
        s = C.strassen()
        a = C.assess("t", s, 2, 2, 2, "Z", SEED)
        b = C.assess("t", s, 2, 2, 2, "Z", OTHER)
        self.assertEqual((a[1], a[2], b[1], b[2]), (0, 0, 0, 0))
        self.assertGreater(a[3], 0)
        self.assertNotEqual(C.digest(a[4]), C.digest(b[4]))
        self.assertEqual(C.digest(a[4]), C.digest(C.assess("t", s, 2, 2, 2, "Z", SEED)[4]))
        # A scheme that multiplies wrongly is caught by the probe as well as by the Brent equations.
        bad = s[:-1]
        self.assertGreater(C.probe(bad, 2, 2, 2, "Z", C.Stream(SEED, "x"))[0], 0)

    def test_the_stream_is_sha256_in_counter_mode(self):
        st = C.Stream(SEED, "label")
        first = int.from_bytes(hashlib.sha256(bytes(32) + b"|label|0").digest()[:8], "big")
        self.assertEqual(st.u64(), first)
        for _ in range(3):
            st.u64()
        second_block = int.from_bytes(hashlib.sha256(bytes(32) + b"|label|1").digest()[:8], "big")
        self.assertEqual(st.u64(), second_block)


class Formats(unittest.TestCase):
    def test_flips_text_reads_back_including_negated_products(self):
        s = C.strassen()
        for negate in ((), (0, 6)):
            scheme = C.read_flips(flips_text(s, 2, 2, 2, negate), 2, 2, 2)
            self.assertEqual(len(scheme), 7)
            self.assertEqual(C.wrong_entries(scheme, 2, 2, 2, "Z"), 0)
        broken = flips_text(s, 2, 2, 2).replace(b"(c11+c22)", b"(c11+c21)", 1)
        self.assertGreater(C.wrong_entries(C.read_flips(broken, 2, 2, 2), 2, 2, 2, "Z"), 0)

    def test_flips_text_refuses_what_it_cannot_read(self):
        for line in (b"(a11+x1)*(b11)*(c11)\n", b"(a11)*(b11)\n", b"(b11)*(b11)*(c11)\n", b"(a31)*(b11)*(c11)\n"):
            with self.assertRaises(ValueError):
                C.read_flips(line, 2, 2, 2)

    def test_alphatensor_npz_reads_back(self):
        s = C.strassen()
        scheme = C.read_alphatensor(npz("2,2,2", s, 4), "2,2,2", 2, 2, 2)
        self.assertEqual(C.wrong_entries(scheme, 2, 2, 2, "F2"), 0)
        u, v, w = s[3]
        broken = s[:3] + [({**u, 0: 1}, v, w)] + s[4:]
        self.assertGreater(C.wrong_entries(C.read_alphatensor(npz("2,2,2", broken, 4), "2,2,2", 2, 2, 2), 2, 2, 2, "F2"), 0)
        with self.assertRaises(ValueError):
            C.read_alphatensor(npz("2,2,2", s, 4), "2,2,2", 3, 3, 3)

    def test_alphaevolve_notebook_reads_back_and_is_never_executed(self):
        s = C.strassen()
        scheme, rows, nonhalf, values = C.read_alphaevolve(notebook("decomposition_222", s, 4), "decomposition_222")
        self.assertEqual((rows, nonhalf), (4, 0))
        self.assertEqual(C.wrong_entries(scheme, 2, 2, 2, "QI"), 0)
        changed = notebook("decomposition_222", s, 4, change=(2, 0, 0, "0.5+0.5j"))
        scheme, _, nonhalf, _ = C.read_alphaevolve(changed, "decomposition_222")
        self.assertGreater(C.wrong_entries(scheme, 2, 2, 2, "QI"), 0)
        self.assertEqual(nonhalf, 0)
        quarter = notebook("decomposition_222", s, 4, change=(0, 1, 1, "0.25+0.j"))
        self.assertEqual(C.read_alphaevolve(quarter, "decomposition_222")[2], 1)
        # Code in the cell is read as a literal or refused, never run.
        planted = notebook("decomposition_222", s, 4, change=(0, 0, 0, "__import__('os').getpid()"))
        with self.assertRaises(ValueError):
            C.read_alphaevolve(planted, "decomposition_222")

    def test_lrp_matrices_read_back_with_their_denominators(self):
        L, R, P = strassen_lrp()
        (lr, lc, L2, lu), (_, _, R2, ru), (_, _, P2, pu) = (C.read_sms(sms(*shape, M)) for shape, M in (((7, 4), L), ((7, 4), R), ((4, 7), P)))
        self.assertEqual((lr, lc, lu, ru, pu), (7, 4, 0, 0, 0))
        self.assertEqual(C.wrong_entries(C.lrp_scheme(L2, R2, P2, 2, 2, 2, 7), 2, 2, 2, "Q"), 0)
        broken = dict(P)
        broken[(0, 0)] = Fraction(1, 3)
        _, _, P3, _ = C.read_sms(sms(4, 7, broken))
        self.assertGreater(C.wrong_entries(C.lrp_scheme(L2, R2, P3, 2, 2, 2, 7), 2, 2, 2, "Q"), 0)
        self.assertEqual(C.odd_part(P3[(0, 0)].denominator), 3)
        self.assertEqual(C.read_sms(b"1 1 R\n1 1 sqrt2\n0 0 0\n")[3], 1)
        with self.assertRaises(ValueError):
            C.read_sms(b"1 1 R\n2 1 1\n0 0 0\n")


class Inputs(unittest.TestCase):
    def test_an_input_that_is_not_the_committed_bytes_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            os.mkdir(os.path.join(d, "inputs"))
            with open(os.path.join(d, "inputs", "x"), "wb") as f:
                f.write(b"data")
            here = os.getcwd()
            os.chdir(d)
            try:
                self.assertEqual(C.input_bytes("x", hashlib.sha256(b"data").hexdigest()), b"data")
                with self.assertRaises(SystemExit):
                    C.input_bytes("x", hashlib.sha256(b"other").hexdigest())
            finally:
                os.chdir(here)


if __name__ == "__main__":
    unittest.main()
