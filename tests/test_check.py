"""The checker on Strassen's scheme written in each paper's format, and on broken copies of it.

A check that cannot fail is not a check: every format is read back, passes, and then fails once one
coefficient is changed. Run with: python3 -m unittest discover -s tests
"""

import base64
import hashlib
import json
import os
import struct
import sys
import tempfile
import unittest
import zipfile
import zlib
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


def sym_text(scheme, n, style, negate=(), transpose_c=False):
    """A scheme in one of Moosbauer & Poole's spellings: "star" ((...)*(...)*(...), CR CR LF line ends),
    "space" ((... + ...) (...) (...), coefficients "2 b31", one-variable factors bare, CRLF, no final
    newline) or "juxt" ((...)(...)(...), "2*b14", bare variables). The products in negate are written
    -( ... ) with the first factor negated inside, so they mean the same product. transpose_c writes c_ik
    where the format has c_ki, to show the reading would then fail."""
    sep = {"star": "*", "space": " ", "juxt": ""}[style]
    coef = {"star": "*", "space": " ", "juxt": "*"}[style]
    plus, minus = (" + ", " - ") if style == "space" else ("+", "-")

    def form(d, letter, sign=1, cols=n):
        items = [(idx, x * sign) for idx, x in sorted(d.items())]
        names = []
        for idx, x in items:
            i, j = divmod(idx, cols)
            if letter == "c" and transpose_c:
                i, j = j, i
            names.append((x, f"{letter}{i + 1}{j + 1}"))
        if style != "star" and len(names) == 1 and names[0][0] == 1:
            return names[0][1]
        out = ""
        for k, (x, name) in enumerate(names):
            body = ("" if abs(x) == 1 else f"{abs(x)}{coef}") + name
            out += ("-" if x < 0 else "") + body if k == 0 else (minus if x < 0 else plus) + body
        return "(" + out + ")"

    lines = []
    for r, (u, v, w) in enumerate(scheme):
        if r in negate:
            lines.append("-(" + sep.join([form(u, "a", -1), form(v, "b"), form(w, "c")]) + ")")
        else:
            lines.append(sep.join([form(u, "a"), form(v, "b"), form(w, "c")]))
    if style == "star":
        return ("\r\r\n".join(lines) + "\r\r\n").encode("ascii")
    return "\r\n".join(lines).encode("ascii")


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


def perm_doc(scheme, n, m, p):
    """A scheme in Perminov's JSON layout: integer arrays u, v and w (w over C transposed), the products as strings
    and the entries of C as sums of products; coefficients +-1, as his strings write them."""

    def signed(terms):
        out = "".join((" - " if x < 0 else " + ") + name for name, x in terms)
        return out[3:] if out.startswith(" + ") else "-" + out[3:]

    def form(d, letter, cols):
        return signed([(f"{letter}{i + 1}{j + 1}", x) for (i, j), x in ((divmod(idx, cols), x) for idx, x in sorted(d.items()))])

    mults = [f"m{r + 1} = ({form(u, 'a', m)}) * ({form(v, 'b', p)})" for r, (u, v, w) in enumerate(scheme)]
    elements = [f"c{i + 1}{k + 1} = " + signed([(f"m{r + 1}", t[2][k * n + i]) for r, t in enumerate(scheme) if t[2].get(k * n + i)])
                for i in range(n) for k in range(p)]
    return {"n": [n, m, p], "m": len(scheme), "z2": False, "multiplications": mults, "elements": elements,
            "u": [[t[0].get(a, 0) for a in range(n * m)] for t in scheme],
            "v": [[t[1].get(b, 0) for b in range(m * p)] for t in scheme],
            "w": [[t[2].get(c, 0) for c in range(p * n)] for t in scheme]}


def perm_m(scheme, n, m, p):
    """The same scheme as Perminov's list file: one {U, V, W} per product, W[k][i] the coefficient in c_ik."""

    def mat(rows):
        return "{" + ", ".join("{" + ", ".join(str(x) for x in r) + "}" for r in rows) + "}"

    lines = []
    for u, v, w in scheme:
        U = [[u.get(i * m + j, 0) for j in range(m)] for i in range(n)]
        V = [[v.get(j * p + k, 0) for k in range(p)] for j in range(m)]
        W = [[w.get(k * n + i, 0) for i in range(n)] for k in range(p)]
        lines.append("  {" + ", ".join([mat(U), mat(V), mat(W)]) + "}")
    return ("{\n" + ",\n".join(lines) + "\n}\n").encode("ascii")


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

    def test_symmetric_flips_files_read_back_in_every_spelling(self):
        s = C.strassen()
        for style in ("star", "space", "juxt"):
            with self.subTest(style=style):
                got = C.read_symflips(sym_text(s, 2, style, negate=(1, 4)), 2)
                self.assertEqual(got, [tuple(C.columns(list(t))) for t in s])
                self.assertEqual(C.wrong_entries(got, 2, 2, 2, "Z"), 0)

    def test_symmetric_flips_coefficients_and_the_transposed_c(self):
        self.assertEqual(C.sym_form("2 b31 - b11", "b", 3, 3), {6: 2, 0: -1})
        self.assertEqual(C.sym_form("-2*b14+b12", "b", 4, 4), {3: -2, 1: 1})
        self.assertEqual(C.read_symflips(b"2*a12 (b21) -c11", 2), [({1: 2}, {2: 1}, {0: -1})])
        wrong = C.read_symflips(sym_text(C.strassen(), 2, "juxt", transpose_c=True), 2)
        self.assertGreater(C.wrong_entries(wrong, 2, 2, 2, "Z"), 0)      # c_ki is C_ik: reading it as C_ki fails

    def test_symmetric_flips_refuses_what_it_cannot_read(self):
        for bad in (b"(a11+x22)(b11)(c11)", b"(a11)(b11)", b"(b11)(a11)(c11)", b"(a11(b11)(c11)",
                    b"(a11)(b11)(c11)(c22)", b"(a13)(b11)(c11)", b"(a11)(b11)(c11) junk"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                C.read_symflips(bad, 2)

    def test_mod2_reduces_and_drops_zeros(self):
        self.assertEqual(C.mod2([({0: 2, 1: -1}, {2: 3}, {3: 1})]), [({1: 1}, {2: 1}, {3: 1})])


class Perminov(unittest.TestCase):
    def test_arrays_strings_and_list_read_back(self):
        s = C.strassen()
        doc = perm_doc(s, 2, 2, 2)
        n, m, p, rank, scheme = C.perm_scheme(doc)
        self.assertEqual((n, m, p, rank), (2, 2, 2, 7))
        self.assertEqual(scheme, s)
        self.assertEqual(C.wrong_entries(scheme, 2, 2, 2, "Z"), 0)
        self.assertEqual(C.perm_strings(doc, 2, 2, 2, 7), s)
        self.assertEqual(C.perm_list(perm_m(s, 2, 2, 2), 2, 2, 2), s)

    def test_two_digit_columns(self):
        self.assertEqual(C.perm_form("b110 - b210", "b", 4, 10), {9: 1, 19: -1})
        doc = {"multiplications": ["m1 = (a11) * (b110)"], "elements": ["c110 = m1"]}
        self.assertEqual(C.perm_strings(doc, 1, 1, 10, 1), [({0: 1}, {9: 1}, {9: 1})])

    def test_what_differs_is_seen_and_what_cannot_be_read_is_refused(self):
        s = C.strassen()
        doc = perm_doc(s, 2, 2, 2)
        doc["multiplications"][0] = doc["multiplications"][0].replace("a22", "a21")
        self.assertNotEqual(C.perm_strings(doc, 2, 2, 2, 7)[0], s[0])
        for bad in ("a1", "a11 a12", "a11 + b12", "a31", "2a11", "a11 * a12"):
            with self.subTest(form=bad), self.assertRaises(ValueError):
                C.perm_form(bad, "a", 2, 2)
        for bad in (b"{ {{1}}, x }", b"{1, 2} + 3", b"{{{1}}, {{1}}}"):
            with self.subTest(listing=bad), self.assertRaises(ValueError):
                C.perm_list(bad, 2, 2, 2)

    def test_shapes_and_integers_are_enforced(self):
        doc = perm_doc(C.strassen(), 2, 2, 2)
        for change in (lambda d: d["u"].pop(), lambda d: d["v"][0].append(0), lambda d: d["w"][1].__setitem__(0, 0.5),
                       lambda d: d["u"][2].__setitem__(1, True)):
            d = json.loads(json.dumps(doc))
            change(d)
            with self.assertRaises(ValueError):
                C.perm_scheme(d)

    def test_w_read_untransposed_fails(self):
        doc = perm_doc(C.strassen(), 2, 2, 2)
        doc["w"] = [[row[(c % 2) * 2 + c // 2] for c in range(4)] for row in doc["w"]]
        self.assertGreater(C.wrong_entries(C.perm_scheme(doc)[4], 2, 2, 2, "Z"), 0)

    def test_exponent_against_strassen(self):
        e, strassen = C.exponent(115, 4, 4, 10)
        self.assertTrue(str(e).startswith("2.80478992"))
        self.assertLess(e, strassen)
        self.assertGreater(C.exponent(116, 4, 4, 10)[0], strassen)
        self.assertLess(abs(C.exponent(7, 2, 2, 2)[0] - strassen), 1e-35)


def medley_bytes(scheme, n):
    """A scheme over F2 in Medley et al.'s byte layout: per term the masks of A, B and C as n-byte little-endian
    integers, bit n*i + j for entry [i, j], C indexed by the product's own entry (this module's w index k*n + i is
    C's entry [i, k])."""
    out = b""
    for u, v, w in C.mod2(scheme):
        a = sum(1 << x for x in u)
        b = sum(1 << x for x in v)
        c = sum(1 << (y % n) * n + y // n for y in w)
        out += a.to_bytes(n, "little") + b.to_bytes(n, "little") + c.to_bytes(n, "little")
    return out


def medley_tex(data, wrap=76):
    """The bytes as Appendix A prints them: zlib, then Base32 without padding, in lines, between the markers, which the
    verifier listing after the block names again."""
    b32 = base64.b32encode(zlib.compress(data, 9)).decode("ascii").rstrip("=")
    lines = [b32[i:i + wrap] for i in range(0, len(b32), wrap)]
    return ("\\begin{Verbatim}\n" + C.MEDLEY_BEGIN + "\n" + "\n".join(lines) + "\n" + C.MEDLEY_END + "\n\\end{Verbatim}\n"
            + 'BEGIN = "' + C.MEDLEY_BEGIN + '"\nEND = "' + C.MEDLEY_END + '"\n')


def naive(n):
    """The schoolbook scheme: one product A[i][j] B[j][k] for each (i, j, k), into C[i][k]."""
    return [({i * n + j: 1}, {j * n + k: 1}, {k * n + i: 1}) for i in range(n) for j in range(n) for k in range(n)]


class Medley(unittest.TestCase):
    def test_the_layout_reads_back_and_passes_mod_2(self):
        for scheme, n in ((C.strassen(), 2), (naive(3), 3)):
            with self.subTest(n=n):
                block = C.medley_block(medley_tex(medley_bytes(scheme, n)))
                got, data, zero = C.read_medley(block, n)
                self.assertEqual(got, C.mod2(scheme))
                self.assertEqual((zero, len(data)), (0, 3 * n * len(scheme)))
                self.assertEqual(C.wrong_entries(got, n, n, n, "F2"), 0)

    def test_c_read_transposed_fails_and_a_changed_bit_or_a_lost_term_fails(self):
        got, _, _ = C.read_medley(C.medley_block(medley_tex(medley_bytes(naive(3), 3))), 3)
        self.assertGreater(C.wrong_entries(C.flip_c(got, 3), 3, 3, 3, "F2"), 0)
        data = bytearray(medley_bytes(C.strassen(), 2))
        data[0] ^= 2
        got, _, _ = C.read_medley(C.medley_block(medley_tex(bytes(data))), 2)
        self.assertGreater(C.wrong_entries(got, 2, 2, 2, "F2"), 0)
        got, _, _ = C.read_medley(C.medley_block(medley_tex(medley_bytes(C.strassen()[:-1], 2))), 2)
        self.assertGreater(C.wrong_entries(got, 2, 2, 2, "F2"), 0)

    def test_a_zero_factor_is_counted(self):
        data = medley_bytes(C.strassen(), 2) + bytes(2) + b"\x01\x00" + b"\x01\x00"
        _, _, zero = C.read_medley(C.medley_block(medley_tex(data)), 2)
        self.assertEqual(zero, 1)

    def test_the_first_end_after_begin_is_used(self):
        tex = medley_tex(medley_bytes(C.strassen(), 2))
        self.assertEqual(C.medley_block("intro " + tex), C.medley_block(tex))
        self.assertNotIn("BEGIN", C.medley_block(tex))

    def test_what_cannot_be_read_is_refused(self):
        good = medley_bytes(C.strassen(), 2)
        b32 = base64.b32encode(zlib.compress(good)).decode("ascii").rstrip("=")
        cases = (
            "no markers at all",
            C.MEDLEY_BEGIN + " " + b32 + " ",                                     # no END
            C.MEDLEY_BEGIN + " " + b32.lower() + " " + C.MEDLEY_END,              # not Base32's alphabet
            C.MEDLEY_BEGIN + " " + b32 + "18 " + C.MEDLEY_END,
        )
        for tex in cases:
            with self.subTest(tex=tex[:40]), self.assertRaises(ValueError):
                C.read_medley(C.medley_block(tex), 2)
        for data in (good + b"\x00", good[:-1], good[:-6] + b"\x10\x00" + good[-4:]):
            with self.subTest(data=len(data)), self.assertRaises(ValueError):
                C.read_medley(C.medley_block(medley_tex(data)), 2)
        trailing = base64.b32encode(zlib.compress(good) + b"junk").decode("ascii").rstrip("=")
        with self.assertRaises(ValueError):
            C.read_medley(C.medley_block(C.MEDLEY_BEGIN + trailing + C.MEDLEY_END), 2)


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


def sym_inputs():
    d = os.environ.get("MM_INPUTS") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "inputs")
    return d if all(os.path.isfile(os.path.join(d, x[1])) and os.path.isfile(os.path.join(d, x[3])) for x in C.SYMFLIPS) else None


@unittest.skipUnless(sym_inputs(), "Moosbauer & Poole's files are not at inputs/ (or MM_INPUTS)")
class SymmetricFlipsReleased(unittest.TestCase):
    def test_the_released_schemes(self):
        here = os.getcwd()
        os.chdir(os.path.join(sym_inputs(), ".."))
        try:
            if os.path.basename(sym_inputs().rstrip("/")) != "inputs":
                self.skipTest("the files must sit in a directory named inputs")
            out, passed = C.run_symflips(SEED)
        finally:
            os.chdir(here)
        self.assertTrue(passed)
        self.assertEqual((out["s555_93_products"], out["s555_93_wrong"], out["s666_153_products"], out["s666_153_wrong"]),
                         (93, 0, 153, 0))
        self.assertEqual((out["s555_93_f2_same"], out["s666_153_f2_same"]), (93, 153))


def perm_inputs():
    d = os.environ.get("MM_INPUTS") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "inputs")
    return d if all(os.path.isfile(os.path.join(d, name)) for name, _ in C.PERMINOV) else None


@unittest.skipUnless(perm_inputs(), "Perminov's files are not at inputs/ (or MM_INPUTS)")
class PerminovReleased(unittest.TestCase):
    def test_the_released_scheme(self):
        if os.path.basename(perm_inputs().rstrip("/")) != "inputs":
            self.skipTest("the files must sit in a directory named inputs")
        here = os.getcwd()
        os.chdir(os.path.join(perm_inputs(), ".."))
        try:
            out, passed = C.run_perminov(SEED)
        finally:
            os.chdir(here)
        self.assertTrue(passed)
        self.assertEqual((out["products"], out["wrong"], out["entries"], out["wrong_mod2"], out["ternary"]),
                         (115, 0, 25600, 0, 1))
        self.assertEqual((out["strings_agree"], out["list_agree"], out["below_strassen"], out["exponent"]),
                         (115, 115, 1, 2.80479))


def medley_inputs():
    d = os.environ.get("MM_INPUTS") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "inputs")
    return d if all(os.path.isfile(os.path.join(d, name)) for name, _ in (C.MEDLEY, C.PRIOR)) else None


@unittest.skipUnless(medley_inputs(), "Medley et al.'s e-print and Perminov's 248 are not at inputs/ (or MM_INPUTS)")
class MedleyReleased(unittest.TestCase):
    def test_the_printed_scheme_and_the_record_it_beats(self):
        if os.path.basename(medley_inputs().rstrip("/")) != "inputs":
            self.skipTest("the files must sit in a directory named inputs")
        here = os.getcwd()
        os.chdir(os.path.join(medley_inputs(), ".."))
        try:
            out, passed = C.run_medley(SEED)
        finally:
            os.chdir(here)
        self.assertTrue(passed)
        self.assertEqual((out["products"], out["distinct"], out["zero_factors"], out["wrong"], out["entries"]),
                         (245, 245, 0, 0, 117649))
        self.assertEqual((out["transposed_wrong"], out["wrong_over_z"], out["prior_products"], out["prior_wrong"],
                          out["improvement"], out["block_chars"], out["decoded_sha256"]),
                         (588, 10124, 248, 0, 3, 3498, "203bdb157c85a7eb"))


if __name__ == "__main__":
    unittest.main()
