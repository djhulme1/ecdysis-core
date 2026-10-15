#!/usr/bin/env python3
"""A 51-addition alternative-basis kernel for rank-23 3 x 3 matrix multiplication: the authors' certificate and the
paper's printed scheme, expanded exactly and counted.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:3a20702006330b21) is from Stapleton and
Perminov, "A 51-Addition Alternative-Basis Kernel for Rank-23 3x3 Matrix Multiplication", arXiv:2609.32388 (v1,
23 September 2026): "We give a rank-23 algorithm for $3\\times3$ matrix multiplication using 51 additions and
subtractions in alternative bases. The input and output conversions require five further additions, giving 56
additions in ordinary coordinates."

Its registered test is TEST below.

The inputs are the authors' certificate (3x3x3_m23_cr51_alt_basis_certificate.json in
Joshua-Stapleton/51-addition-alt-basis-3x3-rank23 at commit 473661e, 2 October 2026) and the paper's e-print
(arXiv-2609.32388v1.gz, the gzipped tar of its TeX), each checked against its SHA-256 and read as data: the JSON
parsed, the tar opened with the standard library and its main.tex read as text. Nothing in either is executed: the
paper's appendix lists its Python checker, and that listing is parsed with ast, never run. Every rule below was fixed
before anything was expanded or counted. A syntax-only pass read the certificate's keys and shapes, and the paper's
text was read in full to fix rules 2 and 3; its displayed programs carry their own counts in their headings (13, 12
and 26 additions) and its conversions are printed as five formulas, all read as the paper's statements. The seed
draws only the random evaluations beside the test.

1. The paper's model (its Section 2 and Section 3.1): vectorization row-major, a_(3i+j) = A_ij and b_(3i+j) = B_ij,
   zero-based; x = P a, y = Q b, u = U~ x, v = V~ y, p_t = u_t v_t (the left factor from A, the right from B, in that
   order), z = W~ p, c = R z and C_ij = c_(3i+j); U = U~ P, V = V~ Q and W = R W~. The multiplication tensor is the
   paper's equation (2): sum over t of W_(3i+l,t) U_(t,3i'+j) V_(t,3j'+l') = d(i,i') d(j,j') d(l,l'), 729
   coefficients.
2. Programs. A program is a sequence of assignments read in order (the paper: "Read assignments from left to right
   within each row, then from top to bottom; repeated assignments to u_22 and v_12 overwrite their previous
   values"); each right side is one or more variables, each with a sign, joined by + or -. Each binary + or - costs
   one addition and a copy is free (the paper's arithmetic model); a right side whose first term has a minus sign is
   a standalone negation, and a coefficient other than 1 a nonunit scalar, both flagged (the paper says its programs
   have neither). Inputs are x0..x8 for u, y0..y8 for v and p0..p22 for z; the outputs are u0..u22, v0..v22 and
   z0..z8 after the last assignment; a variable read before it is assigned, or an output never assigned, refuses the
   run. The certificate's programs are its slp.U, slp.V and slp.W ("name:=expr;"); the paper's are its three
   displayed align* blocks, each read so.
3. Conversions: x = P a, y = Q b and c = R z, each row with k nonzero entries costing k - 1 additions (a row whose one
   entry is 1 is a copy; a single entry -1 a standalone negation; an entry other than -1, 0 or 1 a nonunit scalar).
   The paper's five printed conversion formulas (x_8 = a_8 - a_6 and so on) must be exactly the rows of its P, Q and
   R that are not copies.
4. The test's conditions, each for the certificate and for the paper's printed scheme:
   (a) the programs expand exactly, in integers, to the scheme's U~, V~, W~: the certificate's changed_matrices; for
       the paper, which prints U, V, W, P, Q and R but not U~, V~, W~, the expansions times P, Q and R must give its
       printed U, V and W;
   (b) composed with the conversions, the programs give 23 products whose U, V and W satisfy all 729 coefficients
       of (2);
   (c) the kernel programs need at most 51 additions and the conversions at most 5;
   (d) no step is a standalone negation or a nonunit scalar;
   and, across the two: (e) the certificate's U, V, W, P, Q and R equal the paper's printed ones, and the two sets
   of programs expand to the same forms; (f) the certificate's own matrices agree with each other: its U = U~ P,
   V = V~ Q and W = R W~ exactly, and its U, V, W satisfy (2). Ten conditions; test_passed is 1 if all hold.
5. Beside the test: the counts stage by stage against the paper's 13, 12 and 26 (and 1, 3 and 1 for the conversions);
   the certificate's own "complexity" field; det P, det Q and det R (the paper: +1 each) and whether P_inv, Q_inv and
   R_inv are their inverses; the paper's listing of multiply3x3_cr51 against its displayed programs, assignment by
   assignment, and its conversions; the cost of U, V and W themselves in ordinary coordinates (each row of U and V
   and each row of W with k nonzero entries costing k - 1); and the algorithm, as the certificate states it,
   evaluated on 200 random integer pairs and on 50 pairs of 3 x 3 matrices whose entries are random 2 x 2 integer
   matrices, whose products do not commute, each against AB exactly, drawn from ECDYSIS_SEED.
6. Controls, known answers: the classical 27-product algorithm satisfies (2) and, with its output transposed, does
   not; Strassen's 2 x 2 scheme satisfies the 2 x 2 tensor and, with one coefficient changed, does not; a program
   written here (x0 + x1 - x2 costs 2, a copy nothing, an overwrite is read in order) and its flags (a standalone
   negation, a nonunit scalar); the determinant of a known matrix; a conversion row of three entries +-1 costing 2;
   and the TeX reader on an array and a program written here, with each refusal.

What it cannot check: that 51 is the fewest additions a rank-23 kernel can have, which the paper does not claim, and
the search that found the scheme; Table 1's other rows are the authors' summary of other papers.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Standard library only (the pinned python image). Run with: python3 mm/alt51.py
"""

import ast
import gzip
import hashlib
import io
import json
import os
import random
import re
import sys
import tarfile
from fractions import Fraction

TEST = (
    "Refuted if, in the authors' certificate (Joshua-Stapleton/51-addition-alt-basis-3x3-rank23 at 473661e) or the "
    "paper's printed scheme (arXiv v1), exact expansion of the straight-line programs and conversions P, Q, R does "
    "not give 23 products, each a form in A's entries times one in B's, computing AB (all 729 coefficients, "
    "row-major); or the kernel needs over 51 additions (each binary + or - one, copies free) or the conversions over "
    "5; or a step is a standalone negation or nonunit scalar; or certificate and paper differ, or the certificate's "
    "matrices disagree with its programs."
)
INPUTS = {
    "certificate": ("sp51_certificate.json", "d57a4b795d97ba8b442f00fa5429753dec9a83caa1448f10d0ec7a1818ad6c90"),
    "eprint": ("arXiv-2609.32388v1.gz", "91b8035848d151e4290bba565b92b4e2ec227e9423e42c087b10ea3b8b2d21e4"),
}
READ = (
    "We give a rank-23 algorithm for $3\\times3$ matrix multiplication using 51 additions and subtractions in "
    "alternative bases.",
    "The input and output conversions require five further additions, giving 56 additions in ordinary coordinates.",
    "Read assignments from left to right within each row, then from top to bottom; repeated assignments to $u_{22}$ "
    "and $v_{12}$ overwrite their previous values.",
    "Each binary operation $x+y$ or $x-y$ costs one addition. Copies, zero and permutations are free;",
)
N, RANK = 3, 23
KERNEL_MAX, CONVERSION_MAX = 51, 5
PRINTED = {"u": 13, "v": 12, "z": 26, "P": 1, "Q": 3, "R": 1}
INT_TRIALS, BLOCK_TRIALS = 200, 50
OUTPUTS = ("source", "certificate", "paper", "kernel_additions", "conversion_additions", "total_additions",
           "stages", "paper_kernel_additions", "paper_conversion_additions", "brent_wrong_certificate",
           "brent_wrong_paper", "flags", "agree", "determinants", "listing", "ordinary_cost", "complexity_field",
           "random_integer", "random_block", "conditions_met", "conditions_total", "test_passed", "controls_passed",
           "controls_total")
LIMIT = 200


class Refused(Exception):
    pass


def read_bytes(path, sha256):
    with open(path, "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha256:
        raise Refused(f"{path}: sha256 {got}, not the registered {sha256}")
    return data


# ---------------------------------------------------------------- matrices and the tensor

def matmul(A, B):
    if not A or len(A[0]) != len(B):
        raise Refused("matrix shapes do not fit")
    return [[sum(A[i][k] * B[k][j] for k in range(len(B))) for j in range(len(B[0]))] for i in range(len(A))]


def identity(n):
    return [[int(i == j) for j in range(n)] for i in range(n)]


def det(M):
    """Exact determinant by Gaussian elimination in fractions."""
    A = [[Fraction(x) for x in row] for row in M]
    n, d = len(A), Fraction(1)
    for c in range(n):
        p = next((r for r in range(c, n) if A[r][c] != 0), None)
        if p is None:
            return 0
        if p != c:
            A[c], A[p] = A[p], A[c]
            d = -d
        d *= A[c][c]
        for r in range(c + 1, n):
            f = A[r][c] / A[c][c]
            if f:
                A[r] = [a - f * b for a, b in zip(A[r], A[c])]
    return int(d) if d.denominator == 1 else d


def brent_wrong(U, V, W, n=N, m=None, p=None):
    """Coefficients of the n x m by m x p multiplication tensor (row-major, the paper's (2)) that U, V, W miss."""
    m = n if m is None else m
    p = n if p is None else p
    r = len(U)
    if len(V) != r or len(W[0]) != r or len(U[0]) != n * m or len(V[0]) != m * p or len(W) != n * p:
        raise Refused("U, V, W do not have the shapes of a scheme")
    wrong = 0
    for i in range(n):
        for l in range(p):
            for i2 in range(n):
                for j in range(m):
                    for j2 in range(m):
                        for l2 in range(p):
                            got = sum(W[i * p + l][t] * U[t][i2 * m + j] * V[t][j2 * p + l2] for t in range(r))
                            want = int(i == i2 and j == j2 and l == l2)
                            wrong += got != want
    return wrong


# ---------------------------------------------------------------- programs

TERM = re.compile(r"([+-]?)(?:(\d+)\*)?([a-z]+[0-9]+)")


def parse_rhs(rhs):
    """[(sign, coefficient, name)] for a right side such as x8+u12 or -2*x1."""
    terms, pos = [], 0
    rhs = rhs.replace(" ", "")
    while pos < len(rhs):
        m = TERM.match(rhs, pos)
        if not m or m.end() == pos or (terms and not m.group(1)):
            raise Refused(f"cannot read the right side {rhs!r}")
        terms.append((-1 if m.group(1) == "-" else 1, int(m.group(2) or 1), m.group(3)))
        pos = m.end()
    if not terms:
        raise Refused("an empty right side")
    return terms, rhs.startswith("-")


def run_program(statements, inputs, outputs):
    """Expand a program (a list of (lhs, rhs)) into linear forms of its inputs, read in order.
    Returns (forms of the outputs, additions, negations, nonunit scalars)."""
    env = {x: {x: 1} for x in inputs}
    adds = negs = nonunit = 0
    for lhs, rhs in statements:
        terms, neg = parse_rhs(rhs)
        form = {}
        for sign, coef, name in terms:
            if name not in env:
                raise Refused(f"{lhs} reads {name} before it is assigned")
            if coef != 1:
                nonunit += 1
            for k, v in env[name].items():
                form[k] = form.get(k, 0) + sign * coef * v
        env[lhs] = {k: v for k, v in form.items() if v}
        adds += len(terms) - 1
        negs += int(neg)
    missing = [o for o in outputs if o not in env or o in inputs]
    if missing:
        raise Refused(f"outputs never assigned: {missing}")
    return [env[o] for o in outputs], adds, negs, nonunit


def forms_matrix(forms, inputs):
    return [[f.get(x, 0) for x in inputs] for f in forms]


def names(letter, k):
    return [f"{letter}{i}" for i in range(k)]


def conversion_cost(M):
    """Rule 3: (additions, negations, nonunit scalars) of out = M in."""
    adds = negs = nonunit = 0
    for row in M:
        nz = [x for x in row if x]
        if not nz:
            raise Refused("a conversion row is zero")
        adds += len(nz) - 1
        nonunit += sum(1 for x in nz if x not in (1, -1))
        negs += int(len(nz) == 1 and nz[0] == -1)
    return adds, negs, nonunit


def assess(name, prog, P, Q, R, Ut=None, Vt=None, Wt=None, U=None, V=None, W=None):
    """Rule 4 (a) to (d) for one scheme. prog = {"u": [...], "v": [...], "z": [...]} of (lhs, rhs)."""
    fu, au, nu, su = run_program(prog["u"], names("x", 9), names("u", RANK))
    fv, av, nv, sv = run_program(prog["v"], names("y", 9), names("v", RANK))
    fz, az, nz, sz = run_program(prog["z"], names("p", RANK), names("z", 9))
    Ue, Ve, We = forms_matrix(fu, names("x", 9)), forms_matrix(fv, names("y", 9)), forms_matrix(fz, names("p", RANK))
    Uf, Vf, Wf = matmul(Ue, P), matmul(Ve, Q), matmul(R, We)
    cP, cQ, cR = conversion_cost(P), conversion_cost(Q), conversion_cost(R)
    if Ut is not None:
        expands = Ue == Ut and Ve == Vt and We == Wt
    else:
        expands = Uf == U and Vf == V and Wf == W
    wrong = brent_wrong(Uf, Vf, Wf)
    kernel = au + av + az
    conv = cP[0] + cQ[0] + cR[0]
    flags = nu + nv + nz + su + sv + sz + sum(c[1] + c[2] for c in (cP, cQ, cR))
    return {"name": name, "expands": expands, "brent_wrong": wrong, "kernel": kernel, "conversions": conv,
            "stages": {"u": au, "v": av, "z": az, "P": cP[0], "Q": cQ[0], "R": cR[0]},
            "flags": {"negations": nu + nv + nz + cP[1] + cQ[1] + cR[1],
                      "nonunit": su + sv + sz + cP[2] + cQ[2] + cR[2]},
            "flag_total": flags, "matrices": {"Ut": Ue, "Vt": Ve, "Wt": We, "U": Uf, "V": Vf, "W": Wf}}


# ---------------------------------------------------------------- the certificate

def read_certificate(data):
    try:
        d = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise Refused(f"the certificate is not JSON: {e}") from None
    try:
        if d["dimension"] != [N, N, N] or d["rank"] != RANK:
            raise Refused(f"the certificate is for {d['dimension']} at rank {d['rank']}")
        om, cm, b, slp = d["original_matrices"], d["changed_matrices"], d["basis"], d["slp"]
        mats = {"U": om["U"], "V": om["V"], "W": om["W"], "Ut": cm["U"], "Vt": cm["V"], "Wt": cm["W"],
                "P": b["P"], "Q": b["Q"], "R": b["R"], "P_inv": b["P_inv"], "Q_inv": b["Q_inv"], "R_inv": b["R_inv"]}
        progs = {"u": slp["U"], "v": slp["V"], "z": slp["W"]}
        complexity = d.get("complexity")
    except (KeyError, TypeError) as e:
        raise Refused(f"the certificate lacks {e}") from None
    shapes = {"U": (RANK, 9), "V": (RANK, 9), "W": (9, RANK), "Ut": (RANK, 9), "Vt": (RANK, 9), "Wt": (9, RANK)}
    for k, M in mats.items():
        want = shapes.get(k, (9, 9))
        if (not isinstance(M, list) or len(M) != want[0]
                or any(not isinstance(r, list) or len(r) != want[1] for r in M)
                or any(type(x) is not int for r in M for x in r)):
            raise Refused(f"the certificate's {k} is not a {want[0]} x {want[1]} integer matrix")
    out = {}
    for stage, lines in progs.items():
        st = []
        for s in lines:
            m = re.fullmatch(r"\s*([a-z]+[0-9]+)\s*:=\s*([^;]+);\s*", s) if isinstance(s, str) else None
            if not m:
                raise Refused(f"the certificate's program line {s!r} is not 'name:=expr;'")
            st.append((m.group(1), m.group(2).replace(" ", "")))
        out[stage] = st
    return mats, out, complexity


# ---------------------------------------------------------------- the paper's TeX

def read_tex(data):
    """main.tex from the e-print (a gzipped tar, or a gzipped single file)."""
    raw = gzip.decompress(data)
    try:
        with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
            member = next((m for m in tf.getmembers() if m.isfile() and m.name.endswith("main.tex")), None)
            if member is None:
                raise Refused("the e-print holds no main.tex")
            return tf.extractfile(member).read().decode("utf-8")
    except tarfile.ReadError:
        return raw.decode("utf-8")


def check_read(tex):
    flat = re.sub(r"\s+", " ", tex)
    for sentence in READ:
        if sentence not in flat:
            raise Refused(f"the paper does not say: {sentence!r}")


def tex_matrix(tex, letter):
    pat = re.compile(r"(?<![A-Za-z\\])" + letter + r"\s*=\s*\\left\[\\begin\{array\}\{r+\}(.*?)\\end\{array\}\\right\]",
                     re.S)
    found = pat.findall(tex)
    if len(found) != 1:
        raise Refused(f"the paper prints {len(found)} matrices {letter}, not one")
    rows = []
    for row in found[0].split("\\\\"):
        row = row.strip()
        if not row:
            continue
        try:
            rows.append([int(x.strip().replace("−", "-")) for x in row.split("&")])
        except ValueError:
            raise Refused(f"the paper's {letter} has an entry that is not an integer: {row[:60]!r}") from None
    if len({len(r) for r in rows}) != 1:
        raise Refused(f"the paper's {letter} has rows of different lengths")
    return rows


def tex_statements(block):
    """Assignments of an align* block, left to right within each row, then top to bottom."""
    out = []
    for row in block.split("\\\\"):
        for cell in row.split("&&"):
            cell = re.sub(r"_\{(\d+)\}", r"\1", cell).replace(" ", "").replace("\n", "").strip()
            if not cell:
                continue
            if cell.count("=") != 1:
                raise Refused(f"cannot read the program cell {cell!r}")
            lhs, rhs = cell.split("=")
            if not re.fullmatch(r"[a-z]+[0-9]+", lhs):
                raise Refused(f"cannot read the program cell {cell!r}")
            out.append((lhs, rhs))
    return out


def tex_programs(tex):
    heads = {"u": r"The computation of \$u\$ requires (\d+) additions:",
             "v": r"The computation of \$v\$ requires (\d+) additions:",
             "z": r"the computation of \$z\$ requires (\d+) additional additions:"}
    progs, printed = {}, {}
    for stage, head in heads.items():
        m = re.findall(head + r"\s*\\begin\{align\*\}(.*?)\\end\{align\*\}", tex, re.S)
        if len(m) != 1:
            raise Refused(f"the paper displays {len(m)} programs for {stage}, not one")
        printed[stage] = int(m[0][0])
        progs[stage] = tex_statements(m[0][1])
    return progs, printed


CONV = re.compile(r"([xyc])_(\d)\s*=\s*([abz])_(\d)\s*([+-])\s*([abz])_(\d)")


def tex_conversions(tex):
    i = tex.find("The conversions leave all coordinates unchanged except")
    if i < 0:
        raise Refused("the paper prints no conversion formulas")
    j = tex.find("These are the five conversion additions and subtractions.", i)
    if j < 0:
        raise Refused("the paper does not close its conversion formulas")
    return [(m.group(1), int(m.group(2)), m.group(3), int(m.group(4)), m.group(5), m.group(6), int(m.group(7)))
            for m in CONV.finditer(tex[i:j])]


def conversion_rows(formulas):
    """The rows the printed formulas give: {matrix letter: {row: {column: coefficient}}}."""
    which = {"x": "P", "y": "Q", "c": "R"}
    rows = {}
    for out, i, a, j, sign, b, k in formulas:
        row = {j: 1}
        row[k] = row.get(k, 0) + (1 if sign == "+" else -1)
        rows.setdefault(which[out], {})[i] = row
    return rows


def matrix_non_copies(M):
    out = {}
    for i, row in enumerate(M):
        nz = {j: x for j, x in enumerate(row) if x}
        if nz != {i: 1}:
            out[i] = nz
    return out


# ---------------------------------------------------------------- the paper's listing, parsed, never run

def listing_programs(tex):
    i = tex.find("\\begin{lstlisting}")
    j = tex.find("\\end{lstlisting}", i)
    if i < 0 or j < 0:
        raise Refused("the paper has no listing")
    body = tex[tex.find("]", i) + 1:j]
    body = re.sub(r"\(\*@.*?@\*\)", "", body, flags=re.S)
    try:
        tree = ast.parse(body)
    except SyntaxError as e:
        raise Refused(f"the paper's listing does not parse: {e}") from None
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "multiply3x3_cr51"), None)
    if fn is None:
        raise Refused("the listing has no multiply3x3_cr51")

    def expr(e):
        if isinstance(e, ast.Name):
            return e.id
        if isinstance(e, ast.UnaryOp) and isinstance(e.op, ast.USub):
            return "-" + expr(e.operand)
        if isinstance(e, ast.BinOp) and isinstance(e.op, (ast.Add, ast.Sub)):
            right = expr(e.right)
            if right.startswith("-"):
                raise Refused("the listing subtracts a negation")
            return expr(e.left) + ("+" if isinstance(e.op, ast.Add) else "-") + right
        if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Mult):
            return expr(e.left) + "*" + expr(e.right)
        raise Refused(f"the listing has an expression it cannot read: {ast.dump(e)[:80]}")

    statements = []
    for node in fn.body:
        if isinstance(node, ast.Return):
            continue
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            raise Refused("the listing has a statement that is not one assignment")
        tgt, val = node.targets[0], node.value
        if isinstance(val, ast.Call):
            f = val.func
            if isinstance(f, ast.Attribute) and f.attr == "reshape":
                continue
            if isinstance(f, ast.Attribute) and f.attr == "array" and isinstance(tgt, ast.Name) and tgt.id == "c":
                elts = val.args[0].elts
                statements += [(f"c{k}", expr(e)) for k, e in enumerate(elts)]
                continue
            raise Refused("the listing calls something it should not")
        if isinstance(tgt, ast.Tuple):
            if not isinstance(val, ast.Tuple) or len(val.elts) != len(tgt.elts):
                raise Refused("the listing has a tuple assignment it cannot read")
            statements += [(t.id, expr(v)) for t, v in zip(tgt.elts, val.elts)]
        elif isinstance(tgt, ast.Name):
            statements.append((tgt.id, expr(val)))
        else:
            raise Refused("the listing assigns to something that is not a name")
    return statements


def listing_split(statements):
    """Split the listing's assignments into conversions, the three programs and the products."""
    out = {"x": [], "y": [], "u": [], "v": [], "p": [], "z": [], "c": []}
    for lhs, rhs in statements:
        if lhs[0] == "t":
            out["z"].append((lhs, rhs))
        elif lhs[0] in out:
            out[lhs[0]].append((lhs, rhs))
        else:
            raise Refused(f"the listing assigns {lhs}")
    return out


# ---------------------------------------------------------------- evaluation beside the test

def evaluate(prog, P, Q, R, A, B, add, sub, mul, zero):
    """The algorithm on matrices A and B (3 x 3 lists of ring elements), with the ring's operations."""
    a = [A[i][j] for i in range(3) for j in range(3)]
    b = [B[i][j] for i in range(3) for j in range(3)]

    def apply(M, vec):
        out = []
        for row in M:
            acc = None
            for k, coef in enumerate(row):
                if coef == 0:
                    continue
                term = vec[k]
                for _ in range(abs(coef) - 1):
                    term = add(term, vec[k])
                if acc is None:
                    acc = term if coef > 0 else sub(zero, term)
                else:
                    acc = add(acc, term) if coef > 0 else sub(acc, term)
            out.append(acc if acc is not None else zero)
        return out

    def run(stage, inputs):
        env = dict(inputs)
        for lhs, rhs in prog[stage]:
            terms, _ = parse_rhs(rhs)
            acc = None
            for sign, coef, name in terms:
                t = env[name]
                for _ in range(coef - 1):
                    t = add(t, env[name])
                acc = (t if sign > 0 else sub(zero, t)) if acc is None else (add(acc, t) if sign > 0 else sub(acc, t))
            env[lhs] = acc
        return env

    x, y = apply(P, a), apply(Q, b)
    eu = run("u", {f"x{i}": x[i] for i in range(9)})
    ev = run("v", {f"y{i}": y[i] for i in range(9)})
    p = {f"p{t}": mul(eu[f"u{t}"], ev[f"v{t}"]) for t in range(RANK)}
    ez = run("z", p)
    c = apply(R, [ez[f"z{i}"] for i in range(9)])
    return [[c[3 * i + j] for j in range(3)] for i in range(3)]


def mat2_add(X, Y):
    return [[X[i][j] + Y[i][j] for j in range(2)] for i in range(2)]


def mat2_sub(X, Y):
    return [[X[i][j] - Y[i][j] for j in range(2)] for i in range(2)]


def mat2_mul(X, Y):
    return [[sum(X[i][k] * Y[k][j] for k in range(2)) for j in range(2)] for i in range(2)]


def random_checks(seed, prog, P, Q, R):
    rng = random.Random(int.from_bytes(hashlib.sha256(bytes.fromhex(seed) + b"|alt51/evaluate").digest(), "big"))
    ok_int = 0
    for _ in range(INT_TRIALS):
        A = [[rng.randint(-9, 9) for _ in range(3)] for _ in range(3)]
        B = [[rng.randint(-9, 9) for _ in range(3)] for _ in range(3)]
        C = evaluate(prog, P, Q, R, A, B, lambda s, t: s + t, lambda s, t: s - t, lambda s, t: s * t, 0)
        ok_int += C == [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    ok_block = 0
    Z = [[0, 0], [0, 0]]
    for _ in range(BLOCK_TRIALS):
        A = [[[[rng.randint(-5, 5) for _ in range(2)] for _ in range(2)] for _ in range(3)] for _ in range(3)]
        B = [[[[rng.randint(-5, 5) for _ in range(2)] for _ in range(2)] for _ in range(3)] for _ in range(3)]
        C = evaluate(prog, P, Q, R, A, B, mat2_add, mat2_sub, mat2_mul, Z)
        want = [[None] * 3 for _ in range(3)]
        for i in range(3):
            for j in range(3):
                acc = Z
                for k in range(3):
                    acc = mat2_add(acc, mat2_mul(A[i][k], B[k][j]))
                want[i][j] = acc
        ok_block += C == want
    return ok_int, ok_block


def ordinary_cost(U, V, W):
    """Rows of U and V and of W with k nonzero entries, each costing k - 1 (no sharing of subexpressions)."""
    return (sum(max(0, sum(1 for x in r if x) - 1) for r in U) + sum(max(0, sum(1 for x in r if x) - 1) for r in V)
            + sum(max(0, sum(1 for x in r if x) - 1) for r in W))


# ---------------------------------------------------------------- controls

def classical(n=3):
    U, V, W = [], [], []
    for i in range(n):
        for j in range(n):
            for l in range(n):
                u, v = [0] * (n * n), [0] * (n * n)
                u[i * n + j], v[j * n + l] = 1, 1
                U.append(u)
                V.append(v)
    W = [[int(t // (n * n) == i and t % n == l) for t in range(n ** 3)] for i in range(n) for l in range(n)]
    return U, V, W


def strassen_uvw():
    # products m1..m7 of Strassen (1969), a = (a11, a12, a21, a22), b likewise, c = (c11, c12, c21, c22)
    U = [[1, 0, 0, 1], [0, 0, 1, 1], [1, 0, 0, 0], [0, 0, 0, 1], [1, 1, 0, 0], [-1, 0, 1, 0], [0, 1, 0, -1]]
    V = [[1, 0, 0, 1], [1, 0, 0, 0], [0, 1, 0, -1], [-1, 0, 1, 0], [0, 0, 0, 1], [1, 1, 0, 0], [0, 0, 1, 1]]
    W = [[1, 0, 0, 1, -1, 0, 1], [0, 0, 1, 0, 1, 0, 0], [0, 1, 0, 1, 0, 0, 0], [1, -1, 1, 0, 0, 1, 0]]
    return U, V, W


def controls_known():
    c = {}
    U, V, W = classical()
    Wt = [[W[(k % 3) * 3 + k // 3][t] for t in range(27)] for k in range(9)]
    c["the classical 27-product algorithm satisfies (2), and with its output transposed does not"] = (
        brent_wrong(U, V, W) == 0 and brent_wrong(U, V, Wt) > 0)
    U, V, W = strassen_uvw()
    bad = [row[:] for row in U]
    bad[0][3] = 0
    c["Strassen's scheme satisfies the 2 x 2 tensor, and with one coefficient changed does not"] = (
        brent_wrong(U, V, W, 2) == 0 and brent_wrong(bad, V, W, 2) > 0)
    prog = [("t0", "x0+x1-x2"), ("u0", "t0"), ("u1", "x1"), ("u1", "u1+x2")]
    forms, adds, negs, nonunit = run_program(prog, names("x", 3), ["u0", "u1"])
    ok = forms == [{"x0": 1, "x1": 1, "x2": -1}, {"x1": 1, "x2": 1}] and adds == 3 and negs == 0 and nonunit == 0
    _, _, negs2, nonunit2 = run_program([("u0", "-x0+x1"), ("u1", "2*x1")], names("x", 2), ["u0", "u1"])
    refused = 0
    for bad_prog, outs in (([("u0", "x5")], ["u0"]), ([("u0", "x0+")], ["u0"]), ([("u1", "x0")], ["u0"])):
        try:
            run_program(bad_prog, names("x", 2), outs)
        except Refused:
            refused += 1
    c["programs: x0 + x1 - x2 costs 2, a copy 0, an overwrite in order; a negation and a nonunit scalar flagged; "
      "three bad programs refused"] = ok and negs2 == 1 and nonunit2 == 1 and refused == 3
    c["the determinant of [[2, 1], [1, 1]] is 1, of a transposition -1, of a singular matrix 0"] = (
        det([[2, 1], [1, 1]]) == 1 and det([[0, 1], [1, 0]]) == -1 and det([[1, 2], [2, 4]]) == 0)
    c["a conversion row with three entries +-1 costs 2, a lone -1 is a negation, a 2 a nonunit scalar"] = (
        conversion_cost([[1, -1, 1]]) == (2, 0, 0) and conversion_cost([[0, -1, 0]]) == (0, 1, 0)
        and conversion_cost([[2, 0, 0]]) == (0, 0, 1))
    tex = ("x \\[ P = \\left[\\begin{array}{rr} 1 & 0 \\\\ -1 & 1 \\end{array}\\right] \\] "
           "The computation of $u$ requires 1 additions:\n\\begin{align*}\n u_{0} = x_{0} && u_{1} = x_{0} + x_{1} \\\\\n"
           " u_{1} = u_{1} - x_{0}\n\\end{align*}\n")
    try:
        M = tex_matrix(tex, "P")
        st = tex_statements(tex[tex.find("\\begin{align*}") + 14:tex.find("\\end{align*}")])
        reader_ok = M == [[1, 0], [-1, 1]] and st == [("u0", "x0"), ("u1", "x0+x1"), ("u1", "u1-x0")]
    except Refused:
        reader_ok = False
    refusals = 0
    for t, letter in (("no matrix here", "P"), (tex + tex, "P"),
                      ("P = \\left[\\begin{array}{rr} 1 & x \\end{array}\\right]", "P")):
        try:
            tex_matrix(t, letter)
        except Refused:
            refusals += 1
    try:
        tex_statements("u_{0} = x_{0} = x_{1}")
    except Refused:
        refusals += 1
    c["the TeX reader reads an array and a program written here and refuses four bad ones"] = (
        reader_ok and refusals == 4)
    return c


# ---------------------------------------------------------------- the run

def run(seed, inputs="inputs", results="results", spec=None):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    spec = spec or INPUTS
    raw = {k: read_bytes(os.path.join(inputs, n), s) for k, (n, s) in spec.items()}
    mats, cprog, complexity = read_certificate(raw["certificate"])
    tex = read_tex(raw["eprint"])
    check_read(tex)
    tm = {k: tex_matrix(tex, k) for k in ("U", "V", "W", "P", "Q", "R")}
    tprog, printed = tex_programs(tex)
    formulas = tex_conversions(tex)
    listing = listing_split(listing_programs(tex))

    cert = assess("certificate", cprog, mats["P"], mats["Q"], mats["R"], Ut=mats["Ut"], Vt=mats["Vt"], Wt=mats["Wt"])
    paper = assess("paper", tprog, tm["P"], tm["Q"], tm["R"], U=tm["U"], V=tm["V"], W=tm["W"])
    same_matrices = all(mats[k] == tm[k] for k in ("U", "V", "W", "P", "Q", "R"))
    same_forms = all(cert["matrices"][k] == paper["matrices"][k] for k in ("Ut", "Vt", "Wt"))
    own = (matmul(mats["Ut"], mats["P"]) == mats["U"] and matmul(mats["Vt"], mats["Q"]) == mats["V"]
           and matmul(mats["R"], mats["Wt"]) == mats["W"])
    own_brent = brent_wrong(mats["U"], mats["V"], mats["W"])

    cond = {}
    for s in (cert, paper):
        cond[f"{s['name']}: the programs expand to the scheme's forms"] = s["expands"]
        cond[f"{s['name']}: composed with P, Q and R they satisfy all 729 coefficients of (2)"] = s["brent_wrong"] == 0
        cond[f"{s['name']}: at most {KERNEL_MAX} kernel and {CONVERSION_MAX} conversion additions"] = (
            s["kernel"] <= KERNEL_MAX and s["conversions"] <= CONVERSION_MAX)
        cond[f"{s['name']}: no standalone negation or nonunit scalar"] = s["flag_total"] == 0
    cond["the certificate's matrices equal the paper's printed ones, and the programs expand alike"] = (
        same_matrices and same_forms)
    cond["the certificate's U = U~ P, V = V~ Q, W = R W~, and its U, V, W satisfy (2)"] = own and own_brent == 0

    # beside the test
    conv_rows = conversion_rows(formulas)
    printed_conv_ok = (len(formulas) == 5 and all(conv_rows.get(L, {}) == matrix_non_copies(tm[L])
                                                  for L in ("P", "Q", "R")))
    dets = {k: det(mats[k]) for k in ("P", "Q", "R")}
    inverses = all(matmul(mats[k], mats[k + "_inv"]) == identity(9) for k in ("P", "Q", "R"))
    same_listing = (listing["u"] == tprog["u"] and listing["v"] == tprog["v"] and listing["z"] == tprog["z"]
                    and listing["p"] == [(f"p{t}", f"u{t}*v{t}") for t in range(RANK)])
    lconv = ([(l, r) for l, r in listing["x"] if r != "a" + l[1:]] + [(l, r) for l, r in listing["y"] if r != "b" + l[1:]]
             + [(l, r) for l, r in listing["c"] if r != "z" + l[1:]])
    listing_conv_ok = sorted(lconv) == sorted(
        [(f"{o}{i}", f"{a}{j}{s}{b}{k}") for o, i, a, j, s, b, k in formulas])
    ok_int, ok_block = random_checks(seed, cprog, mats["P"], mats["Q"], mats["R"])
    ordinary = ordinary_cost(mats["U"], mats["V"], mats["W"])
    controls = controls_known()

    def st(s):
        g = s["stages"]
        return f"u {g['u']}, v {g['v']}, z {g['z']}; P {g['P']}, Q {g['Q']}, R {g['R']}"

    def summary(s):
        return (f"programs expand to the scheme: {'yes' if s['expands'] else 'no'}; (2) wrong at "
                f"{s['brent_wrong']} of 729; additions {s['kernel']} + {s['conversions']} ({st(s)}); "
                f"negations {s['flags']['negations']}, nonunit {s['flags']['nonunit']}")

    values = {
        "source": ("certificate 473661e (rank 23, 3 x 3) and arXiv:2609.32388v1's main.tex, the abstract's and the "
                   "model's sentences found"),
        "certificate": summary(cert), "paper": summary(paper),
        "kernel_additions": cert["kernel"], "conversion_additions": cert["conversions"],
        "total_additions": cert["kernel"] + cert["conversions"],
        "stages": (st(cert) + f" (printed: u {printed['u']}, v {printed['v']}, z {printed['z']}; P {PRINTED['P']}, "
                   f"Q {PRINTED['Q']}, R {PRINTED['R']})"),
        "paper_kernel_additions": paper["kernel"], "paper_conversion_additions": paper["conversions"],
        "brent_wrong_certificate": cert["brent_wrong"], "brent_wrong_paper": paper["brent_wrong"],
        "flags": cert["flag_total"] + paper["flag_total"],
        "agree": (f"matrices {'equal' if same_matrices else 'differ'}, forms {'equal' if same_forms else 'differ'}, "
                  f"the certificate's own U = U~P etc. {'hold' if own else 'fail'}, its (2) wrong at {own_brent}; "
                  f"printed conversions {'match' if printed_conv_ok else 'differ'} ({len(formulas)} formulas)"),
        "determinants": (f"det P {dets['P']}, det Q {dets['Q']}, det R {dets['R']}; inverses "
                         f"{'as given' if inverses else 'wrong'}"),
        "listing": (f"multiply3x3_cr51 {'agrees' if same_listing else 'differs'} with the displayed programs; its "
                    f"conversions {'match' if listing_conv_ok else 'differ'}"),
        "ordinary_cost": ordinary,
        "complexity_field": json.dumps(complexity, sort_keys=True)[:LIMIT],
        "random_integer": f"{ok_int} of {INT_TRIALS} integer pairs give AB",
        "random_block": f"{ok_block} of {BLOCK_TRIALS} pairs with 2 x 2 integer-matrix entries give AB",
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(controls.values()), "controls_total": len(controls),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"test": TEST, "inputs": {k: {"name": n, "sha256": s} for k, (n, s) in spec.items()},
              "conditions": cond, "controls": controls, "printed_counts": printed, "printed_conversions": formulas,
              "certificate": {k: v for k, v in cert.items() if k != "matrices"},
              "paper": {k: v for k, v in paper.items() if k != "matrices"},
              "complexity_field": complexity, "determinants": dets, "inverses": inverses,
              "listing_agrees": same_listing, "listing_conversions": lconv, "ordinary_cost": ordinary,
              "random": {"integer": [ok_int, INT_TRIALS], "block": [ok_block, BLOCK_TRIALS]}}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="utf-8") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, default=str)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"alt51: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
