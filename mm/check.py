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
import hashlib
import io
import json
import os
import re
import struct
import sys
import zipfile
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


def run_selftest(seed):
    s = strassen()
    good = wrong_entries(s, 2, 2, 2, "Z")
    broken = control(s, 2, 2, 2, "Z", Stream(seed, "selftest/control"))
    pw, _ = probe(s, 2, 2, 2, "Z", Stream(seed, "selftest/probe"))
    dropped = wrong_entries(s[:-1], 2, 2, 2, "Z")
    out = {"strassen_wrong": good, "strassen_probe_wrong": pw, "broken_wrong": broken, "six_products_wrong": dropped}
    return out, good == 0 and pw == 0 and broken > 0 and dropped > 0


RUNS = {"flips": run_flips, "alphatensor": run_alphatensor, "alphaevolve": run_alphaevolve, "dps": run_dps,
        "symflips": run_symflips, "perminov": run_perminov, "selftest": run_selftest}


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
