#!/usr/bin/env python3
"""Exact checks of fast matrix multiplication schemes, for Ecdysis receipts.

Imago's laboratory (https://ecdysis.me/a/Imago). Standard library only, so
that it runs in a bare Python image with no network. Each subcommand reads
one paper's released scheme from inputs/<name>, where the Ecdysis reference
runner mounts it read-only after verifying it by hash, checks it, and writes
results/outputs.json:

  flips        Kauers & Moosbauer, "Flip graphs for matrix multiplication"
               (arXiv:2212.01175): the (4,4,5) and (5,5,5) schemes, modulo 2
               and over the integers.
  alphatensor  Fawzi et al., Nature 610, 47-53 (2022): the 4x4 factorization
               over GF(2).
  alphaevolve  Novikov et al., "AlphaEvolve" (arXiv:2506.13131): the rank-48
               4x4 decomposition over the complex numbers.
  dps          Dumas, Pernet & Sedoglavic (arXiv:2506.13242): the 48-product
               rational 4x4 algorithm, as its L, R and P matrices.
  symflips     Moosbauer & Poole, "Flip graphs with symmetry and new matrix
               multiplication schemes" (arXiv:2502.04514): the 5x5 scheme in 93
               products and the 6x6 in 153, over the integers and modulo 2.
  perminov     Perminov, "Fast Matrix Multiplication in Small Formats"
               (arXiv:2603.02398): the 4x4x10 scheme in 115 products with
               coefficients in {-1, 0, 1}, over the integers, from its JSON file,
               with the file's own strings and its list file read back against it.
  medley       Medley, Gokul, Luu & Manolios, "GPU-Accelerated Search for Fast
               Matrix Multiplication over F2" (arXiv:2609.17533): the 7x7 scheme in
               245 products modulo 2, read from the Base32 block its Appendix A
               prints in the e-print's TeX, against the record it improves on
               (Perminov's 248 over F2, arXiv:2511.20317, from his repository).
  dps204       Dumas, Pernet, Sedoglavic, Stapleton & Tichavsky, "Fast matrix
               multiplication via recursive <4x4x4:48> algorithms into practice"
               (arXiv:2609.12027v2): the rank-48 algorithm over rings containing
               1/2, as its L, R and P matrices and the three straight-line programs
               that compute them in 204 operations, read as data (never executed as
               code), each program checked to compute exactly its matrix, its
               operations counted as the paper counts them, and run on numbers drawn
               from the seed; the e-print must print the counts and name the files.
  arai         Arai, Ichikawa & Hukushima, "Adaptive Flip Graph Algorithm for Matrix
               Multiplication" (arXiv:2312.16960, ISSAC 2024): the <4,5,5> scheme in
               73 products and the <5,5,5> in 94, modulo 2, from the authors' list
               files, against the previous bests their table names (76 and 95, both
               in Kauers & Moosbauer's flip graph release of December 2022).
  ternary      Perminov, "Fast Matrix Multiplication via Ternary Meta Flip Graphs"
               (arXiv:2511.20317v2): the <4,5,12>, <5,6,10> and <6,7,9> schemes in
               179, 217 and 268 products with coefficients in {-1, 0, 1}, over the
               integers, from his repository; and the ranks it gives as new, over the
               integers and in the binary field, against direct sums and Kronecker
               products of schemes published before it (AlphaEvolve's, Kauers & Wood's
               and AlphaTensor's, each read from where it was published).
  selftest     the checker on Strassen's scheme and on broken copies of it.

Every scheme is checked three ways.

1. The Brent equations, exactly. A scheme of rank R for <n, m, p> is three
   factor matrices U (nm x R), V (mp x R) and W (pn x R); the tensor
   sum_r u_r (x) v_r (x) w_r must equal the tensor of <n, m, p>, which is 1
   at (i*m + j, j*p + k, k*n + i) and 0 elsewhere, in every one of its
   (nm)(mp)(pn) entries: over the integers, modulo 2, over the rationals or
   over the Gaussian rationals, as the paper states. This is the convention
   of AlphaTensor's and AlphaEvolve's own notebooks.
2. A probe: the scheme multiplies matrices drawn from ECDYSIS_SEED and its
   products are compared with the schoolbook product. The digest of those
   products depends on the seed, so the outputs of a run cannot be copied
   from another run under another seed.
3. Controls: Strassen's 2x2 scheme must pass the same check, and the scheme
   under test, with one coefficient (chosen from the seed) increased by one,
   must fail it. A check that passes is therefore not vacuous.

All randomness comes from ECDYSIS_SEED through SHA-256 in counter mode
(see Stream), so another implementation, in any language, can draw the same
numbers. Nothing reads the clock.
"""

import ast
import base64
import hashlib
import io
import json
import os
import re
import struct
import sys
import tarfile
import zipfile
import zlib
from fractions import Fraction

# ---------------------------------------------------------------- numbers


class G:
    """A Gaussian rational re + im*i, held exactly."""

    __slots__ = ("re", "im")

    def __init__(self, re, im=0):
        self.re = Fraction(re)
        self.im = Fraction(im)

    @staticmethod
    def of(x):
        return x if isinstance(x, G) else G(x)

    def __add__(self, o):
        o = G.of(o)
        return G(self.re + o.re, self.im + o.im)

    __radd__ = __add__

    def __sub__(self, o):
        o = G.of(o)
        return G(self.re - o.re, self.im - o.im)

    def __mul__(self, o):
        o = G.of(o)
        return G(self.re * o.re - self.im * o.im, self.re * o.im + self.im * o.re)

    __rmul__ = __mul__

    def __eq__(self, o):
        o = G.of(o)
        return self.re == o.re and self.im == o.im

    def __hash__(self):
        return hash((self.re, self.im))

    def __bool__(self):
        return self.re != 0 or self.im != 0

    def text(self):
        return f"{self.re}{'+' if self.im >= 0 else '-'}{abs(self.im)}i"


RINGS = ("Z", "F2", "Q", "QI")


def is_zero(x, ring):
    if ring == "F2":
        return x % 2 == 0
    return not x


def text(x, ring):
    """How a product's entry is written into the probe digest: 0 or 1 over GF(2), a + bi over Q(i)
    (with a and b as Python writes fractions, e.g. 3, -5/2), else the integer or fraction."""
    if ring == "F2":
        return str(x % 2)
    if ring == "QI":
        return G.of(x).text()
    return str(Fraction(x))


# ---------------------------------------------------------------- the seed


class Stream:
    """Numbers drawn from the seed: the 32-byte blocks SHA-256(seed || "|" || label || "|" || counter),
    counter = 0, 1, 2, ... in decimal ASCII, are read 8 bytes at a time as big-endian integers, and an
    integer below n is drawn by rejection (values at or above the largest multiple of n below 2^64 are
    discarded)."""

    def __init__(self, seed_hex, label):
        self.seed = bytes.fromhex(seed_hex)
        self.label = label.encode("ascii")
        self.counter = 0
        self.buf = b""

    def u64(self):
        if len(self.buf) < 8:
            block = hashlib.sha256(self.seed + b"|" + self.label + b"|" + str(self.counter).encode("ascii")).digest()
            self.buf += block
            self.counter += 1
        x, self.buf = int.from_bytes(self.buf[:8], "big"), self.buf[8:]
        return x

    def below(self, n):
        limit = (1 << 64) - ((1 << 64) % n)
        while True:
            x = self.u64()
            if x < limit:
                return x % n

    def entry(self, ring):
        """A matrix entry: 0 or 1 over GF(2); an integer from -9 to 9 over Z or Q; over Q(i), a Gaussian
        integer whose real part is drawn first, then its imaginary part, each from -9 to 9."""
        if ring == "F2":
            return self.below(2)
        if ring == "QI":
            re_ = self.below(19) - 9
            im_ = self.below(19) - 9
            return G(re_, im_)
        return self.below(19) - 9


# ---------------------------------------------------------------- the checks
# A scheme is a list of R triples (u, v, w) of dicts {index: nonzero coefficient}, indexed as in the
# module docstring: u by i*m + j, v by j*p + k, w by k*n + i.


def tensor(scheme):
    t = {}
    for u, v, w in scheme:
        for a, x in u.items():
            for b, y in v.items():
                xy = x * y
                for c, z in w.items():
                    key = (a, b, c)
                    t[key] = t.get(key, 0) + xy * z
    return t


def wrong_entries(scheme, n, m, p, ring):
    """How many of the (nm)(mp)(pn) entries of sum_r u_r (x) v_r (x) w_r differ from the tensor of <n, m, p>."""
    t = tensor(scheme)
    target = {(i * m + j, j * p + k, k * n + i) for i in range(n) for j in range(m) for k in range(p)}
    wrong = 0
    for key in set(t) | target:
        want = 1 if key in target else 0
        if not is_zero(t.get(key, 0) - want, ring):
            wrong += 1
    return wrong


def probe(scheme, n, m, p, ring, stream):
    """Multiply A (n x m) by B (m x p), drawn from the stream (A row by row, then B row by row), with the
    scheme: (AB)[i][k] = sum_r w_r[k*n+i] (sum u_r[i*m+j] A[i][j]) (sum v_r[j*p+k] B[j][k]).
    Returns the number of entries that differ from the schoolbook product, and the scheme's product."""
    A = [[stream.entry(ring) for _ in range(m)] for _ in range(n)]
    B = [[stream.entry(ring) for _ in range(p)] for _ in range(m)]
    C = [[0] * p for _ in range(n)]
    for u, v, w in scheme:
        s = sum((x * A[a // m][a % m] for a, x in u.items()), 0)
        t = sum((y * B[b // p][b % p] for b, y in v.items()), 0)
        st = s * t
        for c, z in w.items():
            k, i = divmod(c, n)
            C[i][k] = C[i][k] + z * st
    wrong = 0
    for i in range(n):
        for k in range(p):
            want = sum((A[i][j] * B[j][k] for j in range(m)), 0)
            if not is_zero(C[i][k] - want, ring):
                wrong += 1
    return wrong, C


def control(scheme, n, m, p, ring, stream):
    """Increase one coefficient of one u_r by one, both chosen from the stream (r first, then the index),
    and count the wrong entries of the altered scheme. A correct checker finds |v_r| x |w_r| of them."""
    r = stream.below(len(scheme))
    a = stream.below(n * m)
    u, v, w = scheme[r]
    u2 = dict(u)
    u2[a] = u2.get(a, 0) + 1
    altered = scheme[:r] + [(u2, v, w)] + scheme[r + 1:]
    return wrong_entries(altered, n, m, p, ring)


def strassen():
    """Strassen's 2x2 scheme, 7 products, in the convention above (C_ik is w index k*2 + i)."""
    return [
        ({0: 1, 3: 1}, {0: 1, 3: 1}, {0: 1, 3: 1}),    # (A11 + A22)(B11 + B22) -> C11, C22
        ({2: 1, 3: 1}, {0: 1}, {1: 1, 3: -1}),         # (A21 + A22) B11 -> C21, -C22
        ({0: 1}, {1: 1, 3: -1}, {2: 1, 3: 1}),         # A11 (B12 - B22) -> C12, C22
        ({3: 1}, {2: 1, 0: -1}, {0: 1, 1: 1}),         # A22 (B21 - B11) -> C11, C21
        ({0: 1, 1: 1}, {3: 1}, {0: -1, 2: 1}),         # (A11 + A12) B22 -> -C11, C12
        ({2: 1, 0: -1}, {0: 1, 1: 1}, {3: 1}),         # (A21 - A11)(B11 + B12) -> C22
        ({1: 1, 3: -1}, {2: 1, 3: 1}, {0: 1}),         # (A12 - A22)(B21 + B22) -> C11
    ]


def assess(name, scheme, n, m, p, ring, seed, probes=3):
    """The three checks of one scheme. Returns (products, wrong, probe_wrong, control_wrong, probe text)."""
    wrong = wrong_entries(scheme, n, m, p, ring)
    probe_wrong, lines = 0, []
    for q in range(probes):
        w, C = probe(scheme, n, m, p, ring, Stream(seed, f"{name}/probe/{q}"))
        probe_wrong += w
        lines.append(f"{name}/{q}:" + ";".join(",".join(text(x, ring) for x in row) for row in C))
    control_wrong = control(scheme, n, m, p, ring, Stream(seed, f"{name}/control"))
    return len(scheme), wrong, probe_wrong, control_wrong, lines


def digest(lines):
    return hashlib.sha256("\n".join(lines).encode("ascii")).hexdigest()[:16]


# ---------------------------------------------------------------- inputs


def input_bytes(name, sha256):
    """inputs/<name>, refused unless its SHA-256 is the one this receipt committed to."""
    path = os.path.join("inputs", name)
    with open(path, "rb") as f:
        data = f.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha256:
        sys.exit(f"inputs/{name}: sha256 {got}, not the committed {sha256}")
    return data


def columns(factor_columns):
    """[{index: coefficient}] with the zero coefficients dropped."""
    return [{k: x for k, x in col.items() if x != 0} for col in factor_columns]


TERM = re.compile(r"([+-]?)\s*(?:(\d+)\s*\*\s*)?([abc])(\d)(\d)")


def closing(s, start):
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "(":
            depth += 1
        elif s[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    return -1


def split_product(s):
    parts, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "*" and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return [x.strip() for x in parts]


def linear_form(src, letter, rows, cols):
    body = src.strip()
    if body.startswith("(") and closing(body, 0) == len(body) - 1:
        body = body[1:-1]
    out, seen = {}, 0
    for t in TERM.finditer(body):
        sign, coef, var, i, j = t.groups()
        i, j = int(i) - 1, int(j) - 1
        if var != letter or not (0 <= i < rows and 0 <= j < cols):
            raise ValueError(f"unexpected {var}{i + 1}{j + 1} in a {letter}-factor: {src!r}")
        c = (int(coef) if coef else 1) * (-1 if sign == "-" else 1)
        out[i * cols + j] = out.get(i * cols + j, 0) + c
        seen += 1
    if seen == 0 or re.sub(r"\s+", "", TERM.sub("", body)):
        raise ValueError(f"cannot read the factor {src!r}")
    return out


def read_flips(data, n, m, p):
    """Kauers & Moosbauer's .exp format: one product per line, (A-form)*(B-form)*(C-form) over a_ij
    (n x m), b_jk (m x p) and c_ki (p x n), or a negated product -(...)."""
    scheme = []
    for line in data.decode("ascii").splitlines():
        s, sign = line.strip(), 1
        if not s:
            continue
        if s.startswith("-(") and closing(s, 1) == len(s) - 1:
            s, sign = s[2:-1], -1
        parts = split_product(s)
        if len(parts) != 3:
            raise ValueError(f"not a product of three factors: {line!r}")
        u = {k: sign * x for k, x in linear_form(parts[0], "a", n, m).items()}
        v = linear_form(parts[1], "b", m, p)
        w = linear_form(parts[2], "c", p, n)
        scheme.append(tuple(columns([u, v, w])))
    return scheme


# Moosbauer & Poole's files write the same products as the .exp format, a, b and c, with c_ki for the
# output entry C_ik, but in four spellings: factors joined by "*" or written side by side (with or
# without spaces), coefficients written "2*b14" or "2 b31", a factor that is a bare variable, and whole
# products negated as -( ... ). This reader takes all of them, and nothing else.
SYM_TERM = re.compile(r"([+-]?)\s*(?:(\d+)\s*\*?\s*)?([abc])(\d)(\d)")
SYM_BARE = re.compile(r"(?:(\d+)\s*\*?\s*)?[abc]\d\d")


def sym_form(body, letter, rows, cols):
    """One linear form, every character accounted for: {index: coefficient}."""
    out, seen = {}, 0
    for t in SYM_TERM.finditer(body):
        sign, coef, var, i, j = t.groups()
        i, j = int(i) - 1, int(j) - 1
        if var != letter or not (0 <= i < rows and 0 <= j < cols):
            raise ValueError(f"unexpected {var}{i + 1}{j + 1} in a {letter}-factor: {body!r}")
        c = (int(coef) if coef else 1) * (-1 if sign == "-" else 1)
        out[i * cols + j] = out.get(i * cols + j, 0) + c
        seen += 1
    if seen == 0 or re.sub(r"\s+", "", SYM_TERM.sub("", body)):
        raise ValueError(f"cannot read the factor {body!r}")
    return out


def sym_factors(s):
    """The factors of one product, in order: [(sign, body)], each a parenthesised form or a bare variable."""
    out, i = [], 0
    while i < len(s):
        if s[i] in " \t*":
            i += 1
            continue
        sign = 1
        if s[i] in "+-":
            sign = -1 if s[i] == "-" else 1
            i += 1
            while i < len(s) and s[i] in " \t":
                i += 1
        if i < len(s) and s[i] == "(":
            j = closing(s, i)
            if j < 0:
                raise ValueError(f"unbalanced parentheses: {s!r}")
            out.append((sign, s[i + 1:j]))
            i = j + 1
            continue
        m = SYM_BARE.match(s, i)
        if not m:
            raise ValueError(f"cannot read a factor at {s[i:i + 20]!r}")
        out.append((sign, m.group(0)))
        i = m.end()
    return out


def read_symflips(data, n):
    """An n x n scheme in Moosbauer & Poole's files: one product per line, in any of their spellings."""
    scheme = []
    for line in data.decode("ascii").splitlines():
        s, sign = line.strip(), 1
        if not s:
            continue
        if s.startswith("-(") and closing(s, 1) == len(s) - 1 and len(sym_factors(s[2:-1])) == 3:
            s, sign = s[2:-1].strip(), -1
        parts = sym_factors(s)
        if len(parts) != 3:
            raise ValueError(f"not a product of three factors: {line!r}")
        for (_, body), letter in zip(parts, "abc"):
            if not re.search(letter, body):
                raise ValueError(f"factors out of order in {line!r}")
        (su, bu), (sv, bv), (sw, bw) = parts
        u = {k: sign * su * x for k, x in sym_form(bu, "a", n, n).items()}
        v = {k: sv * x for k, x in sym_form(bv, "b", n, n).items()}
        w = {k: sw * x for k, x in sym_form(bw, "c", n, n).items()}
        scheme.append(tuple(columns([u, v, w])))
    return scheme


def mod2(scheme):
    """The scheme with every coefficient reduced modulo 2 (zeros dropped)."""
    return [tuple({k: x % 2 for k, x in f.items() if x % 2} for f in t) for t in scheme]


def read_npy_int64(data):
    """An .npy array of little-endian 64-bit integers in C order: (shape, flat values)."""
    if data[:6] != b"\x93NUMPY":
        raise ValueError("not an .npy array")
    if data[6] == 1:
        (hlen,), start = struct.unpack("<H", data[8:10]), 10
    else:
        (hlen,), start = struct.unpack("<I", data[8:12]), 12
    header = ast.literal_eval(data[start:start + hlen].decode("latin1"))
    if header.get("descr") != "<i8" or header.get("fortran_order"):
        raise ValueError(f"unexpected array header {header}")
    shape = tuple(header["shape"])
    count = 1
    for d in shape:
        count *= d
    body = data[start + hlen:]
    if len(body) != 8 * count:
        raise ValueError("array body does not match its shape")
    return shape, struct.unpack(f"<{count}q", body)


def read_alphatensor(data, key, n, m, p):
    """factorizations_f2.npz: the entry "n,m,p" holds u, v, w stacked, shape (3, n*m, R) here."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        shape, flat = read_npy_int64(z.read(f"{key}.npy"))
    three, rows, rank = shape
    if three != 3 or not (rows == n * m == m * p == p * n):
        raise ValueError(f"unexpected shape {shape} for <{n},{m},{p}>")
    cols = []
    for r in range(rank):
        cols.append(tuple({row: flat[(f * rows + row) * rank + r] for row in range(rows)} for f in range(3)))
    return [tuple(columns(list(c))) for c in cols]


def read_alphaevolve(data, name="decomposition_444"):
    """The results notebook's cell that assigns the decomposition: three np.array(...) literals of
    complex numbers (16 x 48 for decomposition_444), read as Python literals, never executed.
    Returns (scheme, rows, entries not in one half of the Gaussian integers, distinct entries)."""
    nb = json.loads(data.decode("utf-8"))
    sources = []
    for cell in nb["cells"]:
        if cell.get("cell_type") != "code":
            continue
        src = cell["source"]
        src = "".join(src) if isinstance(src, list) else src
        if re.search(rf"^{name}\s*=", src, re.M):
            sources.append(src)
    if len(sources) != 1:
        raise ValueError(f"expected one cell assigning {name}, found {len(sources)}")
    arrays = re.findall(r"np\.array\((\[.*?\])\s*,\s*dtype=np\.complex64\)", sources[0], re.S)
    if len(arrays) != 3:
        raise ValueError(f"expected three factor matrices, found {len(arrays)}")
    mats = [ast.literal_eval(a) for a in arrays]
    nonhalf, values = 0, set()
    exact = []
    for M in mats:
        rows = []
        for row in M:
            out = []
            for z in row:
                g = G(Fraction(complex(z).real), Fraction(complex(z).imag))
                if (2 * g.re).denominator != 1 or (2 * g.im).denominator != 1:
                    nonhalf += 1
                values.add((g.re, g.im))
                out.append(g)
            rows.append(out)
        exact.append(rows)
    rows, rank = len(exact[0]), len(exact[0][0])
    if any(len(M) != rows or any(len(r) != rank for r in M) for M in exact):
        raise ValueError("the three factor matrices are not all of one shape")
    scheme = []
    for r in range(rank):
        scheme.append(tuple(columns([{row: M[row][r] for row in range(rows)} for M in exact])))
    return scheme, rows, nonhalf, len(values)


def read_sms(data):
    """A sparse matrix in PLinOpt's SMS text: "rows cols R", then "i j value" (1-based), ending "0 0 0".
    Returns (rows, cols, {(i, j): Fraction}, values that are not rational numbers)."""
    rows = cols = None
    entries, unreadable = {}, 0
    for line in data.decode("ascii").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        t = s.split()
        if rows is None:
            rows, cols = int(t[0]), int(t[1])
            continue
        i, j = int(t[0]), int(t[1])
        if i == 0 and j == 0:
            break
        if not (1 <= i <= rows and 1 <= j <= cols):
            raise ValueError(f"entry ({i}, {j}) outside {rows} x {cols}")
        try:
            v = Fraction(t[2])
        except (ValueError, ZeroDivisionError):
            unreadable += 1
            continue
        entries[(i - 1, j - 1)] = entries.get((i - 1, j - 1), 0) + v
    return rows, cols, entries, unreadable


def lrp_scheme(L, R, P, n, m, p, rank):
    """The L, R, P form: product r is (L_r . vec A)(R_r . vec B), and vec C = P (products), every matrix
    flattened row by row. In the convention above: u_r[i*m+j] = L[r][i*m+j], v_r[j*p+k] = R[r][j*p+k]
    and w_r[k*n+i] = P[i*p+k][r]."""
    us = [{} for _ in range(rank)]
    vs = [{} for _ in range(rank)]
    ws = [{} for _ in range(rank)]
    for (r, a), x in L.items():
        us[r][a] = x
    for (r, b), y in R.items():
        vs[r][b] = y
    for (c, r), z in P.items():
        i, k = divmod(c, p)
        ws[r][k * n + i] = z
    return [tuple(columns([us[r], vs[r], ws[r]])) for r in range(rank)]


def odd_part(d):
    while d % 2 == 0:
        d //= 2
    return d


# ---------------------------------------------------------------- the papers

FLIPS = [  # (output prefix, input name, sha256, n, m, p, ring, the record the paper says it improves on)
    ("s445_60", "flips_445_60_mod2.exp", "3b134ae7c85225084185dc02d98c3889b11038b796bd37b85f7913472b0e15b7", 4, 4, 5, "F2", 63),
    ("s555_95", "flips_555_95_mod2.exp", "b40354f5ee16172665e9f60a8fa92777f9993ae824aad69d0321c4b11021e13f", 5, 5, 5, "F2", 96),
    ("s445_62", "flips_445_62_mod0.exp", "6d548486de3b3f7ee250eab7132c765da0358a1ff614010fd8446b19d816add8", 4, 4, 5, "Z", 63),
    ("s555_97", "flips_555_97_mod0.exp", "c61cb3465bea8f5291ea1ed3777b522ac3abcd68ddcb62bbe58680fc3bd79355", 5, 5, 5, "Z", 98),
]


def run_flips(seed):
    out, lines, probe_wrong, controls, below = {}, [], 0, [], 0
    for prefix, name, sha, n, m, p, ring, record in FLIPS:
        scheme = read_flips(input_bytes(name, sha), n, m, p)
        products, wrong, pw, cw, ls = assess(prefix, scheme, n, m, p, ring, seed)
        out[f"{prefix}_products"] = products
        out[f"{prefix}_wrong"] = wrong
        probe_wrong += pw
        controls.append(cw)
        lines += ls
        below += 1 if products < record else 0
    out["probe_wrong"] = probe_wrong
    out["control_wrong_min"] = min(controls)
    out["below_record"] = below
    out["probe_digest"] = digest(lines)
    passed = all(out[f"{f[0]}_wrong"] == 0 for f in FLIPS) and probe_wrong == 0 and below == len(FLIPS)
    return out, passed


def run_alphatensor(seed):
    data = input_bytes("factorizations_f2.npz", "70f09f349d8d2874ef0e0e089459c7320f5aa3eef277df5ffa67f573709db2da")
    scheme = read_alphatensor(data, "4,4,4", 4, 4, 4)
    products, wrong, pw, cw, lines = assess("alphatensor_444_f2", scheme, 4, 4, 4, "F2", seed)
    out = {"products": products, "wrong": wrong, "entries": 16 ** 3, "probe_wrong": pw, "control_wrong": cw,
           "below_strassen_49": 1 if products < 49 else 0, "probe_digest": digest(lines)}
    return out, wrong == 0 and pw == 0 and products < 49


def run_alphaevolve(seed):
    data = input_bytes("mathematical_results.ipynb", "2cce2543e48c89aa3e91614272a698a0147dd2548ea11cf92f1292b7435d38ff")
    scheme, rows, nonhalf, values = read_alphaevolve(data)
    if rows != 16:
        raise ValueError(f"decomposition_444 has {rows} rows, not 16")
    products, wrong, pw, cw, lines = assess("alphaevolve_444_c", scheme, 4, 4, 4, "QI", seed)
    out = {"products": products, "wrong": wrong, "entries": 16 ** 3, "probe_wrong": pw, "control_wrong": cw,
           "below_strassen_49": 1 if products < 49 else 0, "entries_not_half_gaussian": nonhalf,
           "distinct_values": values, "probe_digest": digest(lines)}
    return out, wrong == 0 and pw == 0 and products < 49


DPS = [  # input name, sha256
    ("plinopt_4x4x4_48_rational_L.sms", "8eba3256d1012fe794b90c2a1fcead5ccc0db966cc388c2a51609845406b8617"),
    ("plinopt_4x4x4_48_rational_R.sms", "4bc68b6dd3c8125aa59ebb7de706a54520876cfabcc83a4f5dc84ebfd60c1fe5"),
    ("plinopt_4x4x4_48_rational_P.sms", "f67faa68030d6ac4e625e800800f60fe74722188b7189b86b34b34d8a4833f1d"),
]


def run_dps(seed):
    (lr, lc, L, lu), (rr, rc, R, ru), (pr, pc, P, pu) = (read_sms(input_bytes(name, sha)) for name, sha in DPS)
    n = m = p = 4
    rank = lr
    if (lc, rr, rc, pr, pc) != (n * m, rank, m * p, n * p, rank):
        raise ValueError(f"unexpected shapes L {lr}x{lc}, R {rr}x{rc}, P {pr}x{pc}")
    scheme = lrp_scheme(L, R, P, n, m, p, rank)
    products, wrong, pw, cw, lines = assess("dps_444_q", scheme, n, m, p, "Q", seed)
    coefficients = list(L.values()) + list(R.values()) + list(P.values())
    odd = sum(1 for x in coefficients if odd_part(x.denominator) > 1)
    out = {"products": products, "wrong": wrong, "entries": 16 ** 3, "probe_wrong": pw, "control_wrong": cw,
           "coefficients": len(coefficients), "not_rational": lu + ru + pu, "odd_denominators": odd,
           "max_denominator": max(x.denominator for x in coefficients), "probe_digest": digest(lines)}
    return out, wrong == 0 and pw == 0 and products <= 48 and odd == 0 and out["not_rational"] == 0


SYMFLIPS = [  # (output prefix, integer scheme, its sha256, the F2 scheme, its sha256, n, products claimed, the bound improved)
    ("s555_93", "sym555m93_lifted.txt", "dee43421176b9404cb409db20447af04f0b861d8a4d4bd4ad05e9e98c718bf46",
     "sym555m93.txt", "89b86d46243b2245bd6197cd0967fdb5b7c0da0de9ea2fd2b3f5ec2f74c9b804", 5, 93, 97),
    ("s666_153", "sym666m153_lifted.txt", "4c925abd939bf55c72fe777a0a0a30734b321742829144cbe054024f6ee8e802",
     "sym666m153.txt", "4043f707842257e74f745e426fa1f9687753a870870bd7f377918469b5345b8b", 6, 153, 160),
]


def run_symflips(seed):
    """The test: each integer scheme passes every Brent equation over Z (so over every field), with at most
    the claimed number of products and fewer than the bound the paper improves on, and the probes agree.
    Beside it: each F2 file checked modulo 2, and whether it is the integer scheme reduced modulo 2, term
    by term."""
    out, lines, probe_wrong, controls, ok = {}, [], 0, [], True
    for prefix, zname, zsha, fname, fsha, n, claimed, bound in SYMFLIPS:
        z = read_symflips(input_bytes(zname, zsha), n)
        f = read_symflips(input_bytes(fname, fsha), n)
        products, wrong, pw, cw, ls = assess(prefix, z, n, n, n, "Z", seed)
        out[f"{prefix}_products"] = products
        out[f"{prefix}_wrong"] = wrong
        out[f"{prefix}_f2_wrong"] = wrong_entries(f, n, n, n, "F2")
        out[f"{prefix}_f2_same"] = sum(1 for a, b in zip(mod2(z), mod2(f)) if a == b) if len(z) == len(f) else -1
        out[f"{prefix}_max_coefficient"] = max(abs(x) for t in z for d in t for x in d.values())
        probe_wrong += pw
        controls.append(cw)
        lines += ls
        ok = ok and wrong == 0 and products <= claimed and products < bound
    out["probe_wrong"] = probe_wrong
    out["control_wrong_min"] = min(controls)
    out["probe_digest"] = digest(lines)
    return out, ok and probe_wrong == 0


PERMINOV = (  # input name, sha256: the scheme as JSON, and the same scheme as a nested list
    ("perm4x4x10_m115_ZT.json", "39a5275415e34b51a665749921f02aa5176954855ee0b60703a9d15b44d3c0b3"),
    ("perm4x4x10_m115_ZT.m", "5f597423405761c1dd8dc1f6e8db27bc4fe984831f3d297a3b89d823d4536252"),
)
PERM_FORMAT, PERM_CLAIMED, PERM_PREVIOUS = (4, 4, 10), 115, 120   # the claim's format and rank; the paper's previous best
PERM_VAR = re.compile(r"\s*([+-]?)\s*([a-z])(\d)(\d+)\s*")
PERM_PRODUCT = re.compile(r"m(\d+)\s*=\s*\(([^()]*)\)\s*\*\s*\(([^()]*)\)")
PERM_ELEMENT = re.compile(r"c(\d)(\d+)\s*=\s*(.*)")
PERM_USE = re.compile(r"\s*([+-]?)\s*m(\d+)\s*")


def perm_scheme(doc):
    """Perminov's JSON: n = [n, m, p] (A is n x m, B is m x p), m the rank, and u, v, w one row of integers per
    product, u over A row by row (i*m + j), v over B row by row (j*p + k) and w over C transposed (k*n + i): the
    convention of this module. Returns (n, m, p, rank, scheme)."""
    (n, m, p), rank = doc["n"], doc["m"]
    U, V, W = doc["u"], doc["v"], doc["w"]
    if not (len(U) == len(V) == len(W) == rank):
        raise ValueError(f"u, v and w hold {len(U)}, {len(V)} and {len(W)} products, not {rank}")
    for name, M, size in (("u", U, n * m), ("v", V, m * p), ("w", W, p * n)):
        if any(len(row) != size for row in M):
            raise ValueError(f"a row of {name} is not {size} long")
        if not all(type(x) is int for row in M for x in row):
            raise ValueError(f"a coefficient of {name} is not an integer")
    scheme = [tuple(columns([dict(enumerate(U[r])), dict(enumerate(V[r])), dict(enumerate(W[r]))])) for r in range(rank)]
    return n, m, p, rank, scheme


def perm_form(body, letter, rows, cols):
    """One linear form of Perminov's strings, every character accounted for: {index: coefficient}. Indices are
    1-based and written together, the row one digit (b110 is B[1][10]); coefficients are signs alone."""
    out, pos, body = {}, 0, body.strip()
    while pos < len(body):
        t = PERM_VAR.match(body, pos)
        if not t or t.end() == pos:
            raise ValueError(f"cannot read the form {body!r}")
        sign, var, i, j = t.groups()
        i, j = int(i) - 1, int(j) - 1
        if var != letter or not (0 <= i < rows and 0 <= j < cols) or (pos > 0 and not sign):
            raise ValueError(f"unexpected term {t.group(0)!r} in an {letter}-form: {body!r}")
        out[i * cols + j] = out.get(i * cols + j, 0) + (-1 if sign == "-" else 1)
        pos = t.end()
    return {k: x for k, x in out.items() if x}


def perm_strings(doc, n, m, p, rank):
    """The scheme as the JSON's own strings spell it: u and v from "mR = (a-form) * (b-form)", w from the elements
    "cIK = +-mR ...", c_IK being entry (I, K) of C = AB (w index (K-1)*n + I-1)."""
    us, vs, ws = [None] * rank, [None] * rank, [{} for _ in range(rank)]
    for s in doc["multiplications"]:
        t = PERM_PRODUCT.fullmatch(s.strip())
        if not t or not 1 <= int(t.group(1)) <= rank or us[int(t.group(1)) - 1] is not None:
            raise ValueError(f"cannot read the product {s!r}")
        r = int(t.group(1)) - 1
        us[r], vs[r] = perm_form(t.group(2), "a", n, m), perm_form(t.group(3), "b", m, p)
    for s in doc["elements"]:
        t = PERM_ELEMENT.fullmatch(s.strip())
        if not t:
            raise ValueError(f"cannot read the element {s!r}")
        i, k, body, pos = int(t.group(1)) - 1, int(t.group(2)) - 1, t.group(3).strip(), 0
        if not (0 <= i < n and 0 <= k < p):
            raise ValueError(f"no entry c{i + 1}{k + 1} in a {n} x {p} product")
        while pos < len(body):
            u = PERM_USE.match(body, pos)
            if not u or u.end() == pos or not 1 <= int(u.group(2)) <= rank or (pos > 0 and not u.group(1)):
                raise ValueError(f"cannot read the element {s!r}")
            w = ws[int(u.group(2)) - 1]
            w[k * n + i] = w.get(k * n + i, 0) + (-1 if u.group(1) == "-" else 1)
            pos = u.end()
    if any(x is None for x in us):
        raise ValueError("a product has no string")
    return [tuple(columns([us[r], vs[r], ws[r]])) for r in range(rank)]


def perm_list(data, n, m, p):
    """Perminov's list file: braces, commas and integers only, one {U, V, W} per product, U n x m (U[i][j] for
    a_ij), V m x p (V[j][k] for b_jk), W p x n (W[k][i] for c_ik). Read as data: braces become brackets for the
    JSON parser."""
    text = data.decode("ascii")
    if not re.fullmatch(r"[\s{},0-9-]*", text):
        raise ValueError("the list file holds characters other than braces, commas and integers")
    products = json.loads(text.replace("{", "[").replace("}", "]"))
    scheme = []
    for U, V, W in products:
        if [len(U), len(V), len(W)] != [n, m, p] or any(len(x) != m for x in U) or any(len(x) != p for x in V) \
                or any(len(x) != n for x in W):
            raise ValueError("a product's matrices are not n x m, m x p and p x n")
        u = {i * m + j: U[i][j] for i in range(n) for j in range(m)}
        v = {j * p + k: V[j][k] for j in range(m) for k in range(p)}
        w = {k * n + i: W[k][i] for k in range(p) for i in range(n)}
        scheme.append(tuple(columns([u, v, w])))
    return scheme


def exponent(rank, n, m, p):
    """(3 ln rank / ln nmp, log2 7) to 40 digits; the decimal module rounds both correctly, so they repeat anywhere."""
    from decimal import Decimal, localcontext
    with localcontext() as ctx:
        ctx.prec = 40
        return 3 * Decimal(rank).ln() / Decimal(n * m * p).ln(), Decimal(7).ln() / Decimal(2).ln()


def run_perminov(seed):
    """The test: the JSON's scheme passes every Brent equation of <4, 4, 10> over Z, with at most 115 products, all
    coefficients in {-1, 0, 1}, fewer than the previous best of 120, and the probes agree. Beside it: the same check
    modulo 2, the exponent against Strassen's, and how many products the JSON's own strings and the list file give
    exactly as its arrays do."""
    doc = json.loads(input_bytes(*PERMINOV[0]).decode("ascii"))
    n, m, p, rank, scheme = perm_scheme(doc)
    if (n, m, p) != PERM_FORMAT:
        raise ValueError(f"the file is for {n}x{m}x{p}, not {PERM_FORMAT}")
    products, wrong, pw, cw, lines = assess("perminov_4x4x10_z", scheme, n, m, p, "Z", seed)
    coefficients = {x for t in scheme for d in t for x in d.values()} | {0}
    strings = perm_strings(doc, n, m, p, rank)
    listed = perm_list(input_bytes(*PERMINOV[1]), n, m, p)
    e, strassen_e = exponent(products, n, m, p)
    out = {"format": f"{n}x{m}x{p}", "products": products, "wrong": wrong, "entries": (n * m) * (m * p) * (p * n),
           "wrong_mod2": wrong_entries(mod2(scheme), n, m, p, "F2"),
           "max_coefficient": max(abs(x) for x in coefficients), "ternary": int(coefficients <= {-1, 0, 1}),
           "strings_agree": sum(1 for a, b in zip(scheme, strings) if a == b),
           "list_agree": sum(1 for a, b in zip(scheme, listed) if a == b) if len(listed) == rank else -1,
           "probe_wrong": pw, "control_wrong": cw, "probe_digest": digest(lines),
           "exponent": float(e.quantize(type(e)("0.000001"))), "below_strassen": int(e < strassen_e),
           "below_previous": int(products < PERM_PREVIOUS)}
    passed = wrong == 0 and pw == 0 and products <= PERM_CLAIMED and out["ternary"] == 1 and products < PERM_PREVIOUS
    return out, passed


MEDLEY = ("arXiv-2609.17533v1.tar.gz", "20a71d1efdad8ac29a967fdbb9793bb86161f0762ef5482f3fd87199c0754fcd")
MEDLEY_TEX, MEDLEY_N, MEDLEY_CLAIMED = "main.tex", 7, 245
MEDLEY_BEGIN, MEDLEY_END = "BEGIN-RANK245-7X7X7-ZLIB-BASE32", "END-RANK245-7X7X7-ZLIB-BASE32"
PRIOR = ("perm7x7x7_m248_Z2.json", "0b55061fe5ed404aaa5ba380742433fc029650be5821f91719d96b97bdb6f74c")
PRIOR_RANK = 248   # the record the paper improves on: Perminov, arXiv:2511.20317, his table of binary-field results


def medley_block(tex):
    """Appendix A's Base32 text: after the first BEGIN marker and before the first END marker after it (the markers
    appear again, as constants, in the verifier listing that follows the block), with its whitespace removed."""
    start = tex.find(MEDLEY_BEGIN)
    if start < 0:
        raise ValueError("the TeX has no BEGIN marker")
    start += len(MEDLEY_BEGIN)
    end = tex.find(MEDLEY_END, start)
    if end < 0:
        raise ValueError("the TeX has no END marker after BEGIN")
    block = "".join(tex[start:end].split())
    if not re.fullmatch(r"[A-Z2-7]+", block):
        raise ValueError("the block holds characters outside Base32's alphabet")
    return block


def read_medley(block, n=MEDLEY_N):
    """The block decoded as Appendix A states: Base32 (padded to a multiple of eight characters), then zlib, which must
    end exactly where the bytes do; 3n bytes a term, the masks of A, B and C as n-byte little-endian integers, bit
    n*i + j recording entry [i, j]. C's mask is indexed by the product's own entry (C[i][k] = sum_j A[i][j] B[j][k]), as
    the paper's verifier checks it, so its bit n*i + k goes to this module's w index k*n + i. Returns (scheme, the decoded
    bytes, how many terms have a zero factor)."""
    raw = base64.b32decode(block + "=" * (-len(block) % 8))
    d = zlib.decompressobj()
    data = d.decompress(raw) + d.flush()
    if not d.eof or d.unused_data:
        raise ValueError("the zlib stream does not end where the block does")
    size = 3 * n
    if not data or len(data) % size:
        raise ValueError(f"{len(data)} decoded bytes are not whole terms of {size}")
    scheme, zero = [], 0
    for off in range(0, len(data), size):
        a, b, c = (int.from_bytes(data[off + q * n:off + (q + 1) * n], "little") for q in range(3))
        if max(a, b, c) >> (n * n):
            raise ValueError("a mask sets a bit beyond the n x n entries")
        zero += 1 if 0 in (a, b, c) else 0
        u = {x: 1 for x in range(n * n) if a >> x & 1}
        v = {x: 1 for x in range(n * n) if b >> x & 1}
        w = {(x % n) * n + x // n: 1 for x in range(n * n) if c >> x & 1}
        scheme.append((u, v, w))
    return scheme, data, zero


def flip_c(scheme, n):
    """The same scheme with C read the other way round (the cyclic convention's transposed C): a misreading that a
    correct check must reject."""
    return [(u, v, {(y % n) * n + y // n: z for y, z in w.items()}) for u, v, w in scheme]


def run_medley(seed):
    """The test: the scheme Appendix A prints has at most 245 terms, none with a zero factor, passes every Brent equation of
    <7, 7, 7> modulo 2, and has fewer products than the record the paper improves on (248), and the probes agree. Beside it:
    that record itself (Perminov's 248, checked modulo 2), the scheme read with C transposed (which must fail), over the
    integers (it is a scheme of characteristic 2) and its distinct terms. Whether no better scheme was public before the
    paper is a question of the literature, which no run can settle."""
    with tarfile.open(fileobj=io.BytesIO(input_bytes(*MEDLEY)), mode="r:gz") as tar:
        tex = tar.extractfile(MEDLEY_TEX).read().decode("utf-8")
    block = medley_block(tex)
    scheme, data, zero = read_medley(block)
    n = MEDLEY_N
    products, wrong, pw, cw, lines = assess("medley_777_f2", scheme, n, n, n, "F2", seed)
    doc = json.loads(input_bytes(*PRIOR).decode("utf-8"))
    pn, pm, pp, prank, prior = perm_scheme(doc)
    if (pn, pm, pp) != (n, n, n) or doc.get("z2") is not True:
        raise ValueError(f"the prior record's file is for {pn}x{pm}x{pp}, z2 {doc.get('z2')}, not 7x7x7 over F2")
    distinct = len({tuple(tuple(sorted(f)) for f in t) for t in scheme})
    out = {"products": products, "distinct": distinct, "zero_factors": zero, "wrong": wrong, "entries": (n * n) ** 3,
           "probe_wrong": pw, "control_wrong": cw, "transposed_wrong": wrong_entries(flip_c(scheme, n), n, n, n, "F2"),
           "wrong_over_z": wrong_entries(scheme, n, n, n, "Z"), "prior_products": prank,
           "prior_wrong": wrong_entries(prior, n, n, n, "F2"), "improvement": prank - products, "block_chars": len(block),
           "decoded_sha256": hashlib.sha256(data).hexdigest()[:16], "probe_digest": digest(lines)}
    passed = wrong == 0 and pw == 0 and zero == 0 and products <= MEDLEY_CLAIMED and products < PRIOR_RANK
    return out, passed


# ---------------------------------------------------------------- DPS 2026: the 204-operation algorithm
# Dumas, Pernet, Sedoglavic, Stapleton & Tichavsky, "Fast matrix multiplication via recursive <4x4x4:48>
# algorithms into practice" (arXiv:2609.12027v2): the rank-48 algorithm as its L, R and P matrices (.sms) and the
# straight-line programs (.slp) that compute them, from PLinOpt at d17e385, the files the paper names; its
# e-print is read for the counts it prints.

DPS204 = {  # role: (input name, sha256)
    "L": ("plinopt_4x4x4_48_204_L.sms", "acd034de1ccd02570d41b098827666f062346eccc8eceea9b352e292391d05fa"),
    "R": ("plinopt_4x4x4_48_204_R.sms", "bde98dc3051e8109bf1c2de5c30dbd671345d39acd6c5c2d1cc3c7c1256777b8"),
    "P": ("plinopt_4x4x4_48_204_P.sms", "fcd97838986bf12d7704723335a1cc72effe337dfede46ed9558ed094d772a0d"),
    "L.slp": ("plinopt_4x4x4_48_204_L.slp", "b021b1d260e9b01e6970c1c704684aa8d5fb7fb3d9ab7ac23e361786b129c49d"),
    "R.slp": ("plinopt_4x4x4_48_204_R.slp", "3a152ea5e41f2ff04f31357aca7fc08000c0a0733b1acda0207e67bf6c4cf434"),
    "P.slp": ("plinopt_4x4x4_48_204_P.slp", "9e0ffdf3bfebe86f6a3cd427ba469d59d67d82f4f897fe0cab6366c1f402cefd"),
}
DPS204_EPRINT = ("arXiv-2609.12027v2.tar.gz", "4e28ca9625f26ae079b6e276c757eb6db062e411aefa910f5168627d25051d7e")
DPS204_TEX = "mm444cst.tex"
DPS204_PRINTED = (  # each must be in the e-print's TeX, whitespace runs read as one space
    r"We present a fast algorithm for multiplying two~\(\matrixsize{4}{4}\) matrices using~\(48\) multiplications "
    r"and~\(204\) other operations (addition, subtraction or scaling by a constant) over any ring containing an "
    r"inverse of~\(2\).",
    r"\item~\(55\) additions/subtractions and two halvings for~\({\mat{L}}\);",
    r"\item~\(55\) additions/subtractions and two halvings for~\({\mat{R}}\);",
    r"\item~\(90\) additions/subtractions for~\({\mat{P}}\).",
    r"This gives~\(204\) linear operations, namely~\(200\) additions/subtractions and~\(4\) halvings, in addition "
    r"to the~\(48\) bilinear products.",
    r"\plinoptdata{data/4x4x4_48_204_{L,R,P}.s{ms,lp}}",
)
DPS204_COUNTS = {"L": (55, 2), "R": (55, 2), "P": (90, 0)}   # (additions and subtractions, scalings) as printed
DPS204_PRODUCTS, DPS204_OPERATIONS = 48, 204

SLP_TOKEN = re.compile(r"\s*(?:(\d+(?:/\d+)?)|([A-Za-z_][A-Za-z0-9_]*)|(:=|[-+*/();]))")


def slp_tokens(text):
    out, pos = [], 0
    while pos < len(text):
        if text[pos:].strip() == "":
            break
        m = SLP_TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise ValueError(f"unreadable program text at {text[pos:pos + 20]!r}")
        num, name, sym = m.groups()
        out.append(("num", Fraction(num)) if num is not None else ("name", name) if name is not None else ("sym", sym))
        pos = m.end()
    return out


class Slp:
    """One straight-line program read as data and never executed as code: statements "name := expression;" over
    the inputs i0, i1, ..., each name assigned once and used only after it. Values are linear forms
    {input index: Fraction}, or, given input values, numbers. It counts what the paper counts: each binary + or -,
    each multiplication or division by a constant other than 1 and -1 (a scaling), and each negation (a unary minus,
    or a factor -1); a statement with none of these is a copy and costs nothing."""

    def __init__(self, text, inputs):
        self.inputs = inputs
        self.statements = []
        toks = slp_tokens(text)
        i = 0
        names = set()
        while i < len(toks):
            j = i
            while j < len(toks) and toks[j] != ("sym", ";"):
                j += 1
            if j == len(toks):
                raise ValueError("a statement without its ;")
            st = toks[i:j]
            if len(st) < 3 or st[0][0] != "name" or st[1] != ("sym", ":="):
                raise ValueError(f"not an assignment: {st[:3]}")
            target = st[0][1]
            if re.fullmatch(r"i\d+", target):
                raise ValueError(f"an input is assigned: {target}")
            if target in names:
                raise ValueError(f"{target} is assigned twice")
            names.add(target)
            self.statements.append((target, st[2:]))
            i = j + 1

    def run(self, values=None):
        """Every name's value: forms if values is None, else numbers from the input values given. Returns (env,
        counts {adds, scalings, negations, copies})."""
        env = {}
        counts = {"adds": 0, "scalings": 0, "negations": 0, "copies": 0}
        for target, toks in self.statements:
            parser = _SlpExpr(toks, env, self.inputs, values)
            kind, v = parser.expr()
            if parser.i != len(toks):
                raise ValueError(f"{target}: unread tokens")
            if kind != "value":
                raise ValueError(f"{target}: a constant is assigned")
            env[target] = v
            for k in ("adds", "scalings", "negations"):
                counts[k] += parser.counts[k]
            if not any(parser.counts.values()):
                counts["copies"] += 1
        return env, counts

    def outputs(self, env, n):
        names = sorted(k for k in env if re.fullmatch(r"o\d+", k))
        if names != sorted(f"o{r}" for r in range(n)):
            raise ValueError(f"outputs are not o0 .. o{n - 1}")
        return [env[f"o{r}"] for r in range(n)]


class _SlpExpr:
    """expr := term (('+' | '-') term)*; term := unary (('*' | '/') unary)*; unary := '-' unary | atom;
    atom := number | name | '(' expr ')'. A result is ("const", Fraction) or ("value", form or number)."""

    def __init__(self, toks, env, inputs, values):
        self.t, self.i, self.env, self.inputs, self.values = toks, 0, env, inputs, values
        self.counts = {"adds": 0, "scalings": 0, "negations": 0}

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def expr(self):
        kind, v = self.term()
        while self.peek() in (("sym", "+"), ("sym", "-")):
            sign = 1 if self.t[self.i][1] == "+" else -1
            self.i += 1
            k2, w = self.term()
            if kind != "value" or k2 != "value":
                raise ValueError("a constant in a sum")
            self.counts["adds"] += 1
            v = self.combine(v, w, sign)
        return kind, v

    def term(self):
        kind, v = self.unary()
        while self.peek() in (("sym", "*"), ("sym", "/")):
            op = self.t[self.i][1]
            self.i += 1
            k2, w = self.unary()
            if kind == "const" and k2 == "const":
                if op == "/" and w == 0:
                    raise ValueError("division by zero")
                v = v * w if op == "*" else v / w
                continue
            if op == "/" and k2 != "const":
                raise ValueError("division by a value")
            if kind == "value" and k2 == "value":
                raise ValueError("a product of two values: not linear")
            c, x = (w, v) if kind == "value" else (v, w)
            if op == "/":
                if c == 0:
                    raise ValueError("division by zero")
                c = 1 / c
            if c == -1:
                self.counts["negations"] += 1
            elif c != 1:
                self.counts["scalings"] += 1
            kind, v = "value", self.scale(x, c)
        return kind, v

    def unary(self):
        if self.peek() == ("sym", "-"):
            self.i += 1
            kind, v = self.unary()
            if kind == "const":
                return kind, -v
            self.counts["negations"] += 1
            return kind, self.scale(v, Fraction(-1))
        return self.atom()

    def atom(self):
        kind, val = self.peek()
        if kind == "num":
            self.i += 1
            return "const", val
        if kind == "name":
            self.i += 1
            m = re.fullmatch(r"i(\d+)", val)
            if m:
                idx = int(m.group(1))
                if idx >= self.inputs:
                    raise ValueError(f"{val}: no such input")
                return "value", ({idx: Fraction(1)} if self.values is None else Fraction(self.values[idx]))
            if val not in self.env:
                raise ValueError(f"{val} is used before it is assigned")
            v = self.env[val]
            return "value", (dict(v) if self.values is None else v)
        if (kind, val) == ("sym", "("):
            self.i += 1
            out = self.expr()
            if self.peek() != ("sym", ")"):
                raise ValueError("an unclosed (")
            self.i += 1
            return out
        raise ValueError(f"unexpected {val!r}")

    def scale(self, x, c):
        if self.values is not None:
            return x * c
        return {k: y * c for k, y in x.items() if y * c != 0}

    def combine(self, v, w, sign):
        if self.values is not None:
            return v + sign * w
        out = dict(v)
        for k, y in w.items():
            out[k] = out.get(k, 0) + sign * y
            if out[k] == 0:
                del out[k]
        return out


def slp_matrix(forms, cols):
    """{(row, col): Fraction} of the forms, zeros dropped."""
    return {(r, c): x for r, f in enumerate(forms) for c, x in f.items() if x != 0 and c < cols}


def dps204_tex(data):
    """The e-print's TeX, whitespace runs read as one space; refused unless it prints every DPS204_PRINTED."""
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        member = tar.getmember(DPS204_TEX)
        tex = tar.extractfile(member).read().decode("utf-8")
    flat = re.sub(r"\s+", " ", tex)
    missing = [s for s in DPS204_PRINTED if s not in flat]
    if missing:
        raise ValueError(f"the e-print does not print {missing[0][:60]!r}")
    return flat


def slp_probe(programs, n, stream):
    """Multiply two n x n matrices drawn from the stream (A row by row, then B) by running the three programs
    on numbers: products r = L_r(vec A) R_r(vec B), vec C = P(products). Returns (wrong entries, C)."""
    A = [[stream.entry("Q") for _ in range(n)] for _ in range(n)]
    B = [[stream.entry("Q") for _ in range(n)] for _ in range(n)]
    va = [Fraction(A[i][j]) for i in range(n) for j in range(n)]
    vb = [Fraction(B[i][j]) for i in range(n) for j in range(n)]
    lp, rp, pp = programs
    left = lp.outputs(lp.run(va)[0], DPS204_PRODUCTS)
    right = rp.outputs(rp.run(vb)[0], DPS204_PRODUCTS)
    prods = [x * y for x, y in zip(left, right)]
    vc = pp.outputs(pp.run(prods)[0], n * n)
    C = [vc[i * n:(i + 1) * n] for i in range(n)]
    wrong = sum(1 for i in range(n) for k in range(n) if C[i][k] != sum(A[i][j] * B[j][k] for j in range(n)))
    return wrong, C


def run_dps204(seed):
    n = 4
    flat = dps204_tex(input_bytes(*DPS204_EPRINT))
    mats = {}
    for role in ("L", "R", "P"):
        rows, cols, entries, unreadable = read_sms(input_bytes(*DPS204[role]))
        mats[role] = (rows, cols, entries, unreadable)
    (lr, lc, L, lu), (rr, rc, R, ru), (pr, pc, P, pu) = mats["L"], mats["R"], mats["P"]
    rank = lr
    if (lc, rr, rc, pr, pc) != (n * n, rank, n * n, n * n, rank):
        raise ValueError(f"unexpected shapes L {lr}x{lc}, R {rr}x{rc}, P {pr}x{pc}")
    scheme = lrp_scheme(L, R, P, n, n, n, rank)
    products, wrong, pw, cw, lines = assess("dps204_444_q", scheme, n, n, n, "Q", seed)
    coefficients = list(L.values()) + list(R.values()) + list(P.values())
    odd = sum(1 for x in coefficients if odd_part(x.denominator) > 1)
    texts = {role: input_bytes(*DPS204[role + ".slp"]).decode("ascii") for role in ("L", "R", "P")}
    programs = (Slp(texts["L"], n * n), Slp(texts["R"], n * n), Slp(texts["P"], rank))
    counts, matches = {}, 0
    for role, prog, want, nout, nin in (("L", programs[0], L, rank, n * n), ("R", programs[1], R, rank, n * n),
                                       ("P", programs[2], P, n * n, rank)):
        env, c = prog.run()
        got = slp_matrix(prog.outputs(env, nout), nin)
        counts[role] = c
        matches += 1 if got == {k: v for k, v in want.items() if v != 0} else 0
    ops = sum(c["adds"] + c["scalings"] + c["negations"] for c in counts.values())
    slp_wrong = 0
    for q in range(3):
        w, C = slp_probe(programs, n, Stream(seed, f"dps204_slp/probe/{q}"))
        slp_wrong += w
        lines.append(f"dps204_slp/{q}:" + ";".join(",".join(str(Fraction(x)) for x in row) for row in C))
    # The control on the programs: L's program with its first + read as -, which must no longer give L.
    altered = Slp(texts["L"].replace("+", "-", 1), n * n)
    env, _ = altered.run()
    caught = 1 if slp_matrix(altered.outputs(env, rank), n * n) != {k: v for k, v in L.items() if v != 0} else 0
    printed = "; ".join(f"{role} {counts[role]['adds']}+{counts[role]['scalings']}"
                        + ("" if (counts[role]["adds"], counts[role]["scalings"]) == DPS204_COUNTS[role]
                           else f" (printed {DPS204_COUNTS[role][0]}+{DPS204_COUNTS[role][1]})")
                        for role in ("L", "R", "P"))
    out = {"products": products, "wrong": wrong, "entries": 16 ** 3, "probe_wrong": pw, "control_wrong": cw,
           "odd_denominators": odd, "not_rational": lu + ru + pu,
           "max_denominator": max(x.denominator for x in coefficients),
           "slp_l": "{adds} additions, {scalings} scalings, {negations} negations, {copies} copies".format(**counts["L"]),
           "slp_r": "{adds} additions, {scalings} scalings, {negations} negations, {copies} copies".format(**counts["R"]),
           "slp_p": "{adds} additions, {scalings} scalings, {negations} negations, {copies} copies".format(**counts["P"]),
           "operations": ops, "slp_matches": matches, "slp_probe_wrong": slp_wrong, "slp_control_caught": caught,
           "printed_counts": printed, "probe_digest": digest(lines)}
    passed = (wrong == 0 and pw == 0 and products <= DPS204_PRODUCTS and odd == 0 and out["not_rational"] == 0
              and matches == 3 and ops <= DPS204_OPERATIONS and slp_wrong == 0 and caught == 1 and cw > 0)
    return out, passed


# ---------------------------------------------------------------- Arai, Ichikawa & Hukushima: <4,5,5> in 73, <5,5,5> in 94
# The schemes the authors released (github.com/Yamato-Arai/adap at fe7b204, data/455_73.m and data/555_94.m): list
# files in the layout of Perminov's (one {U, V, W} per product, W over C transposed), read by perm_list. Their
# table's previous bests are 76 for <4,5,5> (AlphaTensor's, which Kauers & Moosbauer's flips release also holds,
# over the integers) and 95 for <5,5,5> modulo 2 (Kauers & Moosbauer's): both are read from that release, at
# c801b27 (2 December 2022), and checked too.

ARAI = (  # (prefix, input name, sha256, (n, m, p), the claimed products, the previous best the paper names)
    ("s455", "arai_455_73.m", "cbb0fbf1be1cda95113abe2a6ec0e59cfc7b071b316e4463981100751512dc26", (4, 5, 5), 73, 76),
    ("s555", "arai_555_94.m", "8f79ca798e801aea4f025657dcdcb009035fd6379401552143edffc10efc02a3", (5, 5, 5), 94, 95),
)
ARAI_PRIOR = {  # prefix: (input name, sha256, the ring the release states for it)
    "s455": ("flips_455_76_mod0.exp", "1ba4f15d64f5385580ca15fd40c849950c6d831e44528e203c80d92079d627e8", "Z"),
    "s555": ("flips_555_95_mod2.exp", "b40354f5ee16172665e9f60a8fa92777f9993ae824aad69d0321c4b11021e13f", "F2"),
}


def run_arai(seed):
    """The test: each released scheme passes every Brent equation of its format modulo 2, with at most the claimed
    products, no zero factor, fewer products than the previous best the paper names, and the probes agree; and each
    previous best is a scheme of that many products that holds, over its own ring and modulo 2. Beside it: each
    scheme over the integers (they are schemes of characteristic 2, so they should fail there), its distinct products,
    whether every coefficient is 1, and the <5,5,5> scheme read with C transposed (which must fail). Whether no
    better scheme was public before the paper is a question of the literature, which no run can settle."""
    out, lines, probe_wrong, controls, zero, binary, prior_wrong, below = {}, [], 0, [], 0, True, 0, 0
    ok = True
    for prefix, name, sha, (n, m, p), claimed, previous in ARAI:
        scheme = perm_list(input_bytes(name, sha), n, m, p)
        products, wrong, pw, cw, ls = assess(f"arai_{prefix}_f2", scheme, n, m, p, "F2", seed)
        z = sum(1 for t in scheme if any(not d for d in t))
        pname, psha, pring = ARAI_PRIOR[prefix]
        prior = read_flips(input_bytes(pname, psha), n, m, p)
        pwrong = wrong_entries(prior, n, m, p, pring) + (wrong_entries(prior, n, m, p, "F2") if pring != "F2" else 0)
        out[f"{prefix}_products"] = products
        out[f"{prefix}_wrong"] = wrong
        out[f"{prefix}_wrong_over_z"] = wrong_entries(scheme, n, m, p, "Z")
        out[f"{prefix}_distinct"] = len({tuple(tuple(sorted(d.items())) for d in t) for t in scheme})
        out[f"{prefix}_prior_products"] = len(prior)
        if n == p:
            out[f"{prefix}_transposed_wrong"] = wrong_entries(flip_c(scheme, n), n, m, p, "F2")
        zero += z
        binary = binary and all(x == 1 for t in scheme for d in t for x in d.values())
        prior_wrong += pwrong
        below += 1 if products < len(prior) else 0
        probe_wrong += pw
        controls.append(cw)
        lines += ls
        ok = ok and wrong == 0 and z == 0 and products <= claimed and len(prior) == previous and pwrong == 0 \
            and products < previous
    out.update({"zero_factors": zero, "binary": int(binary), "prior_wrong": prior_wrong, "below_prior": below,
                "probe_wrong": probe_wrong, "control_wrong_min": min(controls), "probe_digest": digest(lines)})
    return out, ok and probe_wrong == 0


# ---------------------------------------------------------------- Perminov 2025: ternary meta flip graphs
# Perminov, "Fast Matrix Multiplication via Ternary Meta Flip Graphs" (arXiv:2511.20317v2): the three schemes his
# repository holds for its new ranks in {-1, 0, 1} at c774162 (the commit current when v2 was submitted), and whether
# the ranks it gives as new, over the integers and in the binary field, had been reached before 25 November 2025 by
# public schemes or by direct sums and Kronecker products of them. The earlier schemes are read from where they were
# published: AlphaEvolve's results notebook (May 2025), the repository Kauers & Wood's arXiv:2510.19787 names, at its
# commit of 22 October 2025 (6487519, the day the paper was submitted), and AlphaTensor's GF(2) factorizations (2022).

TERNARY = (  # (prefix, input name, sha256, format, the rank claimed, the previous best the paper names)
    ("zt4512", "perm4x5x12_m179_ZT.json", "883d8e37f736403fe0d8f246783c54a132d827c169c2d270d49b637340977d9d",
     (4, 5, 12), 179, 180),
    ("zt5610", "perm5x6x10_m217_ZT.json", "fd1affd5d170d479ed46bb76416320295a2cdf014c50030409284279add8a3d9",
     (5, 6, 10), 217, 218),
    ("zt679", "perm6x7x9_m268_ZT.json", "d904b103bcb6e51efe0f00f45155c09a221217882491131b8f383ffc6f21bc68",
     (6, 7, 9), 268, 270),
)
EARLIER = {  # input name, sha256
    "alphaevolve": ("mathematical_results.ipynb", "2cce2543e48c89aa3e91614272a698a0147dd2548ea11cf92f1292b7435d38ff"),
    "kw458": ("kw458_k10f2d8a1de6a5616.exp", "fc5dc788b9f73d0d9d18b378ee5a8757d5c629da23eef84d5ea8336bffd6d323"),
    "kw568": ("kw568_k1844566e012fe5f1.exp", "1781d9e732ef61379fe4a5d24903cff85f2cef91400116d24081a0186ca5c173"),
    "kw456": ("kw456_k08dcabe7aa6634b.mod2.exp", "848598e02b5b4972b6e3aad7f30340fdadd9e9776d4f5250c42615e4e2ddfbc5"),
    "alphatensor": ("factorizations_f2.npz", "70f09f349d8d2874ef0e0e089459c7320f5aa3eef277df5ffa67f573709db2da"),
}
# The binary-field ranks the paper's table of binary discoveries gives as new, for the formats the sums below reach.
BINARY_CLAIMED = {(4, 4, 8): 94, (4, 4, 12): 141, (4, 4, 16): 188, (8, 8, 8): 329, (4, 5, 6): 89, (5, 6, 10): 217}


def read_alphaevolve_real(data, name):
    """A decomposition the results notebook prints as three np.array(..., dtype=np.float32) literals (n*m, m*p and p*n
    rows, one column per product, in this module's convention), read as Python literals, never executed. Every entry must
    be a whole number. Returns (scheme, the three row counts)."""
    nb = json.loads(data.decode("utf-8"))
    sources = []
    for cell in nb["cells"]:
        if cell.get("cell_type") != "code":
            continue
        src = cell["source"]
        src = "".join(src) if isinstance(src, list) else src
        if re.search(rf"^{name}\s*=", src, re.M):
            sources.append(src)
    if len(sources) != 1:
        raise ValueError(f"expected one cell assigning {name}, found {len(sources)}")
    arrays = re.findall(r"np\.array\((\[.*?\])\s*,\s*dtype=np\.float32\)", sources[0], re.S)
    if len(arrays) != 3:
        raise ValueError(f"expected three float32 factor matrices in {name}, found {len(arrays)}")
    mats = []
    for a in arrays:
        M = ast.literal_eval(a)
        rows = []
        for row in M:
            out = []
            for x in row:
                q = Fraction(float(x))
                if q.denominator != 1:
                    raise ValueError(f"{name} holds {x}, not a whole number")
                out.append(int(q))
            rows.append(out)
        mats.append(rows)
    rank = len(mats[0][0])
    if any(any(len(r) != rank for r in M) for M in mats):
        raise ValueError(f"the factor matrices of {name} do not all have {rank} columns")
    scheme = [tuple(columns([{row: M[row][r] for row in range(len(M))} for M in mats])) for r in range(rank)]
    return scheme, tuple(len(M) for M in mats)


def cyclic(scheme):
    """A scheme for <n, m, p> as one for <m, p, n>: (u, v, w) -> (v, w, u), exact in this module's convention."""
    return [(v, w, u) for u, v, w in scheme]


def direct_sum(parts, n, m):
    """<n, m, p1> (+) <n, m, p2> (+) ... = <n, m, p1 + p2 + ...>: B's columns and C's split into blocks, one scheme for
    each. parts: [(scheme, p_i)]. Returns (scheme, p)."""
    p = sum(q for _, q in parts)
    out, off = [], 0
    for scheme, q in parts:
        for u, v, w in scheme:
            v2 = {(b // q) * p + b % q + off: y for b, y in v.items()}
            w2 = {(c // n + off) * n + c % n: z for c, z in w.items()}
            out.append((dict(u), v2, w2))
        off += q
    return out, p


def kronecker(s1, f1, s2, f2):
    """<n1, m1, p1> (x) <n2, m2, p2> = <n1 n2, m1 m2, p1 p2>: every product of the first with every product of the second,
    entry (i1, j1) of a block matrix's block (i2, j2) at row i1 n2 + i2, column j1 m2 + j2."""
    (n1, m1, p1), (n2, m2, p2) = f1, f2
    n, m, p = n1 * n2, m1 * m2, p1 * p2

    def pair(d1, d2, r1, c1, r2, c2, cols):
        out = {}
        for a, x in d1.items():
            i1, j1 = divmod(a, c1)
            for b, y in d2.items():
                i2, j2 = divmod(b, c2)
                out[(i1 * r2 + i2) * cols + (j1 * c2 + j2)] = x * y
        return out

    scheme = []
    for u1, v1, w1 in s1:
        for u2, v2, w2 in s2:
            scheme.append((pair(u1, u2, n1, m1, n2, m2, m), pair(v1, v2, m1, p1, m2, p2, p),
                           pair(w1, w2, p1, n1, p2, n2, n)))
    return scheme, (n, m, p)


def run_ternary(seed):
    """The test: the three released schemes pass every Brent equation of their formats over Z with coefficients in
    {-1, 0, 1} and at most the ranks claimed, and the probes agree; and none of those ranks, nor any binary-field rank the
    paper gives as new for the formats below, was reached before by these earlier schemes or their sums and products:
    <4,5,12> as AlphaEvolve's <4,4,5> in 61 (read as <4,5,4>) (+) Kauers & Wood's <4,5,8> in 118; <5,6,10> as AlphaEvolve's
    <2,5,6> in 47 (read as <5,6,2>) (+) their <5,6,8> in 170; and modulo 2, AlphaTensor's <4,4,4> in 47 two, three and
    four times along p and (x) Strassen's <2,2,2>, Kauers & Wood's <4,5,6> in 89, and the <5,6,10> sum. Whether no other
    scheme reached the ranks first, or reached <6,7,9> in 268, is a question of the literature, which no run settles."""
    out, lines, probe_wrong, controls, wrong, over, ternary, agree, products = {}, [], 0, [], 0, 0, 0, 0, []
    for prefix, name, sha, fmt, claimed, previous in TERNARY:
        doc = json.loads(input_bytes(name, sha).decode("ascii"))
        n, m, p, rank, scheme = perm_scheme(doc)
        if (n, m, p) != fmt or doc.get("z2") is not False:
            raise ValueError(f"{name} is for {n}x{m}x{p}, z2 {doc.get('z2')}, not {fmt} over the integers")
        k, w_, pw, cw, ls = assess(prefix, scheme, n, m, p, "Z", seed)
        products.append(k)
        wrong += w_
        over += 1 if k > claimed else 0
        probe_wrong += pw
        controls.append(cw)
        lines += ls
        ternary += 1 if {x for t in scheme for d in t for x in d.values()} <= {-1, 1} else 0
        agree += sum(1 for a, b in zip(scheme, perm_strings(doc, n, m, p, rank)) if a == b)

    nb = input_bytes(*EARLIER["alphaevolve"])
    ae445, rows445 = read_alphaevolve_real(nb, "decomposition_445")
    ae256, rows256 = read_alphaevolve_real(nb, "decomposition_256")
    if rows445 != (16, 20, 20) or rows256 != (10, 30, 12):
        raise ValueError(f"AlphaEvolve's decompositions have rows {rows445} and {rows256}")
    kw458 = read_flips(input_bytes(*EARLIER["kw458"]), 4, 5, 8)
    kw568 = read_flips(input_bytes(*EARLIER["kw568"]), 5, 6, 8)
    kw456 = read_flips(input_bytes(*EARLIER["kw456"]), 4, 5, 6)
    at444 = read_alphatensor(input_bytes(*EARLIER["alphatensor"]), "4,4,4", 4, 4, 4)
    earlier = (("AE 4x4x5", ae445, (4, 4, 5), "Z"), ("AE 2x5x6", ae256, (2, 5, 6), "Z"), ("KW 4x5x8", kw458, (4, 5, 8), "Z"),
               ("KW 5x6x8", kw568, (5, 6, 8), "Z"), ("KW 4x5x6", kw456, (4, 5, 6), "F2"),
               ("AT 4x4x4", at444, (4, 4, 4), "F2"))
    out["earlier_wrong"] = sum(wrong_entries(s, *f, ring) for _, s, f, ring in earlier)
    out["earlier_ranks"] = "; ".join(f"{label} {len(s)}{' mod 2' if ring == 'F2' else ''}" for label, s, _, ring in earlier)

    s4512, _ = direct_sum([(cyclic(ae445), 4), (kw458, 8)], 4, 5)
    s5610, _ = direct_sum([(cyclic(ae256), 2), (kw568, 8)], 5, 6)
    sums = (("4512", s4512, (4, 5, 12), 179), ("5610", s5610, (5, 6, 10), 217))
    reached = 0
    for label, s, f, claimed in sums:
        w_ = wrong_entries(s, *f, "Z")
        out[f"sum_{label}_products"], out[f"sum_{label}_wrong"] = len(s), w_
        reached += 1 if w_ == 0 and len(s) <= claimed else 0
    out["sum_max_coefficient"] = ",".join(str(max(abs(x) for t in s for d in t for x in d.values())) for _, s, _, _ in sums)
    out["new_ranks_reached"] = reached

    binary = {(4, 4, 8): direct_sum([(at444, 4)] * 2, 4, 4)[0], (4, 4, 12): direct_sum([(at444, 4)] * 3, 4, 4)[0],
              (4, 4, 16): direct_sum([(at444, 4)] * 4, 4, 4)[0],
              (8, 8, 8): kronecker(at444, (4, 4, 4), strassen(), (2, 2, 2))[0], (4, 5, 6): kw456, (5, 6, 10): s5610}
    detail, bwrong, breached = [], 0, 0
    for f, s in binary.items():
        w_ = wrong_entries(s, *f, "F2")
        bwrong += w_
        hit = w_ == 0 and len(s) <= BINARY_CLAIMED[f]
        breached += 1 if hit else 0
        detail.append(f"{f[0]}x{f[1]}x{f[2]} {len(s)}{'' if hit else ' (not reached)'}")
    out.update({"zt_products": ",".join(str(k) for k in products), "zt_wrong": wrong, "zt_ternary": ternary,
                "zt_strings_agree": agree, "zt_probe_wrong": probe_wrong, "zt_control_wrong_min": min(controls),
                "binary_reached": breached, "binary_detail": "; ".join(detail), "binary_wrong": bwrong,
                "probe_digest": digest(lines)})
    clean = wrong == 0 and over == 0 and probe_wrong == 0 and ternary == len(TERNARY) and out["earlier_wrong"] == 0
    return out, clean and reached == 0 and breached == 0


def run_selftest(seed):
    s = strassen()
    good = wrong_entries(s, 2, 2, 2, "Z")
    broken = control(s, 2, 2, 2, "Z", Stream(seed, "selftest/control"))
    pw, _ = probe(s, 2, 2, 2, "Z", Stream(seed, "selftest/probe"))
    dropped = wrong_entries(s[:-1], 2, 2, 2, "Z")
    out = {"strassen_wrong": good, "strassen_probe_wrong": pw, "broken_wrong": broken, "six_products_wrong": dropped}
    return out, good == 0 and pw == 0 and broken > 0 and dropped > 0


RUNS = {"flips": run_flips, "alphatensor": run_alphatensor, "alphaevolve": run_alphaevolve, "dps": run_dps,
        "symflips": run_symflips, "perminov": run_perminov, "medley": run_medley, "dps204": run_dps204,
        "arai": run_arai, "ternary": run_ternary, "selftest": run_selftest}


def main(argv):
    if len(argv) != 2 or argv[1] not in RUNS:
        sys.exit(f"usage: check.py {{{','.join(RUNS)}}}")
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    # Every run starts with the controls on Strassen's scheme: if they fail, the checker is not to be trusted.
    st, ok = run_selftest(seed)
    if not ok:
        sys.exit(f"the checker's self-test failed: {st}")
    out, passed = RUNS[argv[1]](seed)
    out["strassen_wrong"] = st["strassen_wrong"]
    out["test_passed"] = 1 if passed else 0
    os.makedirs("results", exist_ok=True)
    with open(os.path.join("results", "outputs.json"), "w", encoding="ascii") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv)
