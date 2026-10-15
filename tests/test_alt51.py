"""The 51-addition kernel's check (mm/alt51.py): the tensor, the programs and their counts, the conversions, the TeX
and listing readers, the evaluation, and a whole run on a certificate and an e-print built here from the classical
27-product algorithm (with the rank patched to 27). Nothing of the claim's scheme is read or computed.

Run with: python3 -m unittest tests.test_alt51
"""

import gzip
import hashlib
import importlib.util
import io
import json
import os
import tarfile
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("mm_alt51", os.path.join(HERE, "..", "mm", "alt51.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "3c" * 32


def inverse_unipotent(P):
    """P = I + E with E nilpotent of one entry: the inverse is I - E."""
    n = len(P)
    return [[(1 if i == j else -P[i][j]) for j in range(n)] for i in range(n)]


def expr_of(row, letter):
    terms = []
    for k, c in enumerate(row):
        if c == 0:
            continue
        if c not in (1, -1):
            raise ValueError("unit coefficients only")
        terms.append(("-" if c < 0 else "+") + f"{letter}{k}")
    s = "".join(terms)
    return s[1:] if s.startswith("+") else s


def classical_certificate(corrupt=False):
    """The classical algorithm with P = I but x8 = a8 - a6, so that U~ = U P^-1 has three two-term rows."""
    U, V, W = M.classical()
    if corrupt:
        V = [r[:] for r in V]
        V[5] = [0] * 9
        V[5][0] = 1
    P = M.identity(9)
    P[8][6] = -1
    Q, R = M.identity(9), M.identity(9)
    Pi = inverse_unipotent(P)
    Ut, Vt, Wt = M.matmul(U, Pi), V, W
    slp = {"U": [f"u{t}:={expr_of(Ut[t], 'x')};" for t in range(27)],
           "V": [f"v{t}:={expr_of(Vt[t], 'y')};" for t in range(27)],
           "W": [f"z{k}:={expr_of(Wt[k], 'p')};" for k in range(9)]}
    cert = {"dimension": [3, 3, 3], "rank": 27, "complexity": {"naive": 18, "changed": 21},
            "original_matrices": {"U": U, "V": V, "W": W},
            "basis": {"P": P, "Q": Q, "R": R, "P_inv": Pi, "Q_inv": Q, "R_inv": R},
            "changed_matrices": {"U": Ut, "V": Vt, "W": Wt}, "slp": slp}
    return cert


def tex_array(letter, A):
    rows = " \\\\\n".join(" & ".join(str(x) for x in r) for r in A)
    return f"{letter} = \\left[\\begin{{array}}{{{'r' * len(A[0])}}}\n{rows}\n\\end{{array}}\\right]"


def tex_program(slp, head):
    cells = []
    for s in slp:
        lhs, rhs = s[:-1].split(":=")
        rhs = rhs.replace("+", " + ").replace("-", " - ").strip()
        out = "".join(f"{ch}" for ch in rhs)
        name = lhs[0] + "_{" + lhs[1:] + "}"
        import re
        out = re.sub(r"([a-z])(\d+)", lambda m: m.group(1) + "_{" + m.group(2) + "}", out)
        cells.append(f"{name} = {out}")
    rows = [" && ".join(cells[i:i + 4]) for i in range(0, len(cells), 4)]
    return head + "\n\\begin{align*}\n" + " \\\\\n".join(rows) + "\n\\end{align*}\n"


def listing(cert):
    lines = ["import json", "import numpy as np", "", "", "def multiply3x3_cr51(a, b):",
             "    a0, a1, a2, a3, a4, a5, a6, a7, a8 = a.reshape(9)",
             "    b0, b1, b2, b3, b4, b5, b6, b7, b8 = b.reshape(9)",
             "    x0, x1, x2, x3, x4, x5, x6, x7, x8 = a0, a1, a2, a3, a4, a5, a6, a7, a8 - a6",
             "    y0, y1, y2, y3, y4, y5, y6, y7, y8 = b0, b1, b2, b3, b4, b5, b6, b7, b8"]
    for stage in ("U", "V"):
        for s in cert["slp"][stage]:
            lhs, rhs = s[:-1].split(":=")
            lines.append(f"    {lhs} = {rhs.replace('+', ' + ').replace('-', ' - ')}")
    for t in range(cert["rank"]):
        lines.append(f"    p{t} = u{t} * v{t}")
    for s in cert["slp"]["W"]:
        lhs, rhs = s[:-1].split(":=")
        lines.append(f"    {lhs} = {rhs.replace('+', ' + ').replace('-', ' - ')}")
    lines.append("    c = np.array([z0, z1, z2, z3, z4, z5, z6, z7, z8])")
    lines.append("    return c.reshape(3, 3)")
    return "\n".join(lines)


def eprint(cert, conversions="x_8=a_8-a_6."):
    om, b, slp = cert["original_matrices"], cert["basis"], cert["slp"]
    adds = {k: sum(len(M.parse_rhs(s.split(":=")[1][:-1])[0]) - 1 for s in slp[k]) for k in ("U", "V", "W")}
    parts = ["\\documentclass{article}\\begin{document}", " ".join(M.READ), "\\[",
             tex_array("U", om["U"]), ",\\quad", tex_array("V", om["V"]), "\\]\\[", tex_array("W", om["W"]), "\\]\\[",
             tex_array("P", b["P"]), ",", tex_array("Q", b["Q"]), ",", tex_array("R", b["R"]), "\\]",
             "The conversions leave all coordinates unchanged except\n\\[\n" + conversions + "\n\\]\n"
             "These are the five conversion additions and subtractions.",
             tex_program(slp["U"], f"The computation of $u$ requires {adds['U']} additions:"),
             tex_program(slp["V"], f"The computation of $v$ requires {adds['V']} additions:"),
             tex_program(slp["W"], f"And the computation of $z$ requires {adds['W']} additional additions:"),
             "\\begin{lstlisting}[style=py,caption={x}]\n" + listing(cert) + "\n\\end{lstlisting}", "\\end{document}"]
    tex = "\n".join(parts).encode("utf-8")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        info = tarfile.TarInfo("main.tex")
        info.size = len(tex)
        tf.addfile(info, io.BytesIO(tex))
    return gzip.compress(buf.getvalue())


class Tensor(unittest.TestCase):
    def test_classical_and_strassen(self):
        U, V, W = M.classical()
        self.assertEqual(M.brent_wrong(U, V, W), 0)
        U2, V2, W2 = M.strassen_uvw()
        self.assertEqual(M.brent_wrong(U2, V2, W2, 2), 0)
        V2b = [r[:] for r in V2]
        V2b[6] = [0, 0, 1, 0]
        self.assertGreater(M.brent_wrong(U2, V2b, W2, 2), 0)

    def test_shapes_refused(self):
        U, V, W = M.classical()
        with self.assertRaises(M.Refused):
            M.brent_wrong(U[:-1], V, W)

    def test_rectangular(self):
        # the classical 2 x 3 by 3 x 2 algorithm
        n, m, p = 2, 3, 2
        U, V, W = [], [], []
        for i in range(n):
            for j in range(m):
                for l in range(p):
                    u, v = [0] * (n * m), [0] * (m * p)
                    u[i * m + j], v[j * p + l] = 1, 1
                    U.append(u)
                    V.append(v)
        W = [[int(t // (m * p) == i and t % p == l) for t in range(n * m * p)] for i in range(n) for l in range(p)]
        self.assertEqual(M.brent_wrong(U, V, W, n, m, p), 0)

    def test_det(self):
        self.assertEqual(M.det(M.identity(4)), 1)
        self.assertEqual(M.det([[0, 0, 1], [0, 1, 0], [1, 0, 0]]), -1)
        self.assertEqual(M.det([[1, 2, 3], [4, 5, 6], [7, 8, 10]]), -3)


class Programs(unittest.TestCase):
    def test_count_and_overwrite(self):
        prog = [("t0", "x0+x1-x2"), ("u0", "t0"), ("u1", "x0-x1"), ("u1", "u1+x2"), ("u0", "u0-u1")]
        forms, adds, negs, nonunit = M.run_program(prog, M.names("x", 3), ["u0", "u1"])
        self.assertEqual(forms, [{"x1": 2, "x2": -2}, {"x0": 1, "x1": -1, "x2": 1}])
        self.assertEqual((adds, negs, nonunit), (5, 0, 0))

    def test_flags_and_refusals(self):
        _, adds, negs, nonunit = M.run_program([("u0", "-x0"), ("u1", "x0+3*x1")], M.names("x", 2), ["u0", "u1"])
        self.assertEqual((adds, negs, nonunit), (1, 1, 1))
        for prog, outs in (([("u0", "x2")], ["u0"]), ([("u0", "x0x1")], ["u0"]), ([("u0", "x0")], ["u0", "u1"]),
                           ([("u0", "x0++x1")], ["u0"]), ([("u0", "")], ["u0"])):
            with self.assertRaises(M.Refused, msg=repr(prog)):
                M.run_program(prog, M.names("x", 2), outs)

    def test_cancelling_terms_vanish(self):
        forms, adds, _, _ = M.run_program([("u0", "x0+x1"), ("u0", "u0-x1")], M.names("x", 2), ["u0"])
        self.assertEqual(forms, [{"x0": 1}])
        self.assertEqual(adds, 2)

    def test_conversion_cost(self):
        P = M.identity(9)
        P[8][6] = -1
        self.assertEqual(M.conversion_cost(P), (1, 0, 0))
        with self.assertRaises(M.Refused):
            M.conversion_cost([[0, 0]])


class Readers(unittest.TestCase):
    def test_certificate_refusals(self):
        cert = classical_certificate()
        M_RANK = M.RANK
        M.RANK = 27
        try:
            mats, progs, _ = M.read_certificate(json.dumps(cert).encode())
            self.assertEqual(len(progs["u"]), 27)
            bad = json.loads(json.dumps(cert))
            bad["slp"]["U"][0] = "u0 = x0"
            with self.assertRaises(M.Refused):
                M.read_certificate(json.dumps(bad).encode())
            bad = json.loads(json.dumps(cert))
            bad["basis"]["P"][0][0] = 1.0
            with self.assertRaises(M.Refused):
                M.read_certificate(json.dumps(bad).encode())
            bad = json.loads(json.dumps(cert))
            del bad["slp"]
            with self.assertRaises(M.Refused):
                M.read_certificate(json.dumps(bad).encode())
        finally:
            M.RANK = M_RANK
        with self.assertRaises(M.Refused):
            M.read_certificate(json.dumps(cert).encode())  # rank 27 is not the claim's 23
        with self.assertRaises(M.Refused):
            M.read_certificate(b"{not json")

    def test_tex(self):
        M_RANK = M.RANK
        M.RANK = 27
        try:
            cert = classical_certificate()
            tex = M.read_tex(eprint(cert))
            M.check_read(tex)
            self.assertEqual(M.tex_matrix(tex, "W"), cert["original_matrices"]["W"])
            progs, printed = M.tex_programs(tex)
            self.assertEqual(printed, {"u": 3, "v": 0, "z": 18})
            self.assertEqual(progs["u"][26], ("u26", "x6+x8"))
            self.assertEqual(M.tex_conversions(tex), [("x", 8, "a", 8, "-", "a", 6)])
            lst = M.listing_split(M.listing_programs(tex))
            self.assertEqual(lst["u"], progs["u"])
            self.assertEqual(lst["p"][3], ("p3", "u3*v3"))
        finally:
            M.RANK = M_RANK
        with self.assertRaises(M.Refused):
            M.check_read("nothing of the paper")

    def test_listing_refuses_calls(self):
        tex = ("\\begin{lstlisting}[style=py]\ndef multiply3x3_cr51(a, b):\n    u0 = run(a)\n\\end{lstlisting}")
        with self.assertRaises(M.Refused):
            M.listing_programs(tex)


class Evaluation(unittest.TestCase):
    def test_classical_evaluates(self):
        M_RANK = M.RANK
        M.RANK = 27
        try:
            cert = classical_certificate()
            prog = {k: [tuple(s[:-1].split(":=")) for s in cert["slp"][K]] for k, K in (("u", "U"), ("v", "V"),
                                                                                       ("z", "W"))}
            b = cert["basis"]
            ok_int, ok_block = M.random_checks(SEED, prog, b["P"], b["Q"], b["R"])
            self.assertEqual((ok_int, ok_block), (M.INT_TRIALS, M.BLOCK_TRIALS))
            bad = classical_certificate(corrupt=True)
            prog_bad = {k: [tuple(s[:-1].split(":=")) for s in bad["slp"][K]] for k, K in (("u", "U"), ("v", "V"),
                                                                                         ("z", "W"))}
            ok_int2, _ = M.random_checks(SEED, prog_bad, b["P"], b["Q"], b["R"])
            self.assertLess(ok_int2, M.INT_TRIALS)
        finally:
            M.RANK = M_RANK

    def test_block_products_do_not_commute(self):
        X, Y = [[0, 1], [0, 0]], [[0, 0], [1, 0]]
        self.assertNotEqual(M.mat2_mul(X, Y), M.mat2_mul(Y, X))


class WholeRun(unittest.TestCase):
    def build(self, corrupt=False):
        d = tempfile.mkdtemp()
        cert = classical_certificate(corrupt)
        cdata = json.dumps(cert).encode()
        edata = eprint(cert)
        with open(os.path.join(d, "c.json"), "wb") as fh:
            fh.write(cdata)
        with open(os.path.join(d, "e.gz"), "wb") as fh:
            fh.write(edata)
        spec = {"certificate": ("c.json", hashlib.sha256(cdata).hexdigest()),
                "eprint": ("e.gz", hashlib.sha256(edata).hexdigest())}
        return d, spec

    def test_valid_scheme_passes(self):
        M_RANK = M.RANK
        M.RANK = 27
        try:
            d, spec = self.build()
            out, detail = M.run(SEED, inputs=d, results=os.path.join(d, "r"), spec=spec)
        finally:
            M.RANK = M_RANK
        self.assertEqual(tuple(sorted(out)), tuple(sorted(M.OUTPUTS)))
        self.assertEqual(out["conditions_total"], 10)
        self.assertEqual(out["test_passed"], 1, [k for k, ok in detail["conditions"].items() if not ok])
        self.assertEqual((out["kernel_additions"], out["conversion_additions"]), (21, 1))
        self.assertEqual(out["controls_passed"], out["controls_total"])
        for k, v in out.items():
            self.assertTrue(isinstance(v, (int, float, str)) and not isinstance(v, bool), k)
            if isinstance(v, str):
                self.assertLessEqual(len(v), M.LIMIT, k)
        self.assertTrue(detail["listing_agrees"])

    def test_corrupt_scheme_fails(self):
        M_RANK = M.RANK
        M.RANK = 27
        try:
            d, spec = self.build(corrupt=True)
            out, detail = M.run(SEED, inputs=d, results=os.path.join(d, "r"), spec=spec)
        finally:
            M.RANK = M_RANK
        self.assertEqual(out["test_passed"], 0)
        self.assertGreater(out["brent_wrong_certificate"], 0)
        self.assertGreater(out["brent_wrong_paper"], 0)

    def test_hash_and_seed_refused(self):
        d, spec = self.build()
        with self.assertRaises(M.Refused):
            M.run(SEED, inputs=d, results=d, spec=dict(spec, eprint=("e.gz", "0" * 64)))
        with self.assertRaises(M.Refused):
            M.run("nope", inputs=d, results=d, spec=spec)


class Registered(unittest.TestCase):
    def test_constants(self):
        self.assertLessEqual(len(M.TEST), 600)
        self.assertIn("473661e", M.TEST)
        self.assertEqual((M.N, M.RANK, M.KERNEL_MAX, M.CONVERSION_MAX), (3, 23, 51, 5))
        self.assertEqual(M.INPUTS["certificate"][1], "d57a4b795d97ba8b442f00fa5429753dec9a83caa1448f10d0ec7a1818ad6c90")
        self.assertEqual(M.INPUTS["eprint"][1], "91b8035848d151e4290bba565b92b4e2ec227e9423e42c087b10ea3b8b2d21e4")

    def test_controls(self):
        c = M.controls_known()
        self.assertEqual(len(c), 6)
        self.assertTrue(all(c.values()), [k for k, ok in c.items() if not ok])


if __name__ == "__main__":
    unittest.main()
