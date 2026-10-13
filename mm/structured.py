#!/usr/bin/env python3
"""Structured matrix multiplication: the 4 x 4 rank-34 schemes for AA^T and for triangular times general.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:9fd551a00e8cb720) is from Khoruzhii, Gelss &
Pokutta, "Faster Algorithms for Structured Matrix Multiplication via Flip Graph Search" (arXiv:2511.10786v2; ISSAC 2026):
"In particular, we obtain $4 \\times 4$ rank-34 schemes for both multiplying a general matrix by its transpose and an
upper-triangular matrix by a general matrix, improving the asymptotic factor from 8/13 (0.615) to 22/37 (0.595)."

Its registered test: refuted if either 4 x 4 scheme the e-print prints in full (C = AA^T, upper triangle; C = AB, A upper
triangular), read from its TeX, is not an exact integer decomposition of its tensor as the paper defines it (left and
right inputs independent), or has more than 34 products, or fewer than 12 recursive calls by the paper's criteria (AA^T:
equal factors, or output only in diagonal blocks; triangular times general: triangular factor only in diagonal blocks),
so that (34 - q)/(4^w - q) with w = log2 7 exceeds 22/37.

Standard library only. The inputs are the claim's data of record, each checked against its SHA-256: the e-print's
source (whose files schemes/gt-444.tex and schemes/ug-444.tex hold the two figures), read in memory as text, and the
two scheme files of the authors' repository (khoruzhii/flip-cpd at 9eeb17f) that correspond to them, read as text.
Nothing in them is run. Every rule below was fixed before any seed existed.

1. Reading a figure. TeX comments are removed first. Inside it, \\red{x}, \\blue{x}, \\reccall{x} and \\grey{x} are unwrapped to x, and the line break
   that splits a long product ("\\\\[-1.5mm]&\\hspace{4.2mm}") joins its two halves. Equations are separated by "\\\\"
   and by a horizontal space in centimetres; an equation's name is the last m_{d}, r_{d} or C_d^d before its "=", and
   its right side ends at the separator (or at \\end{aligned}). A product reads (sum)(sum)\\T for AA^T and (sum)(sum)
   for AB, each sum a list of terms [+-][integer]X_i^j, X being A on the left and A (AA^T) or B (AB) on the right; an
   output reads as a list of terms [+-]m_{d} or [+-]r_{d}. Anything else, a product defined twice or never used, an
   output missing, or (for AB) an entry of A below its diagonal, refuses the run.
2. The tensors, as the paper defines them (its section 3, and the generator its repository releases, which is read
   only as documentation): for AA^T, the outputs C_i^k with i <= k, C_i^k = sum_j X_i^j (Y_k^j)^T, with the left
   input X and the right input Y independent (so that the scheme applies to blocks, and to pairs X, Y in its
   recursive calls); for AB with A upper triangular, C_i^k = sum_{j >= i} A_i^j B_j^k.
3. Exact: every coefficient of sum_t U_t (x) V_t (x) W_t equals the tensor's, over the integers (a coefficient that is
   not an integer refuses the reading).
4. Products: those with a nonzero left factor, a nonzero right factor and some output.
5. Recursive calls, by the paper's criteria (its section 5). For AA^T, criterion one counts the products whose two
   factors are equal, criterion two those whose output lies only in diagonal blocks C_i^i; q is the larger count, as
   the paper selects the better criterion for each scheme. For AB, q counts the products whose left factor has
   entries only in diagonal blocks A_i^i (an upper-triangular block or sum of them).
6. The factor: gamma = (r - q)/(4^w - q), the paper's equation (4) with its other counts 0, where 4^w = 49 exactly at
   w = log2 7.
7. The test's eight conditions: for each scheme, exact; at most 34 products; q at least 12; gamma at most 22/37.
   test_passed is 1 if all eight hold.
8. Beside the test: the additions each figure prints (141 and 148) against a count of the scheme as printed (each
   factor's terms less one, each output's terms less one); the released schemes, checked the same way (the AA^T file
   is the tensor without the corner outputs C_1^1 and C_4^4, which the figure computes by eight calls A_1^j (A_1^j)^T
   and A_4^j (A_4^j)^T), and how many rank-one terms they share with the printed ones; the coefficients used.
9. Probes: each scheme applied to block matrices drawn from the seed (4 x 4 blocks of 3 x 3 integers from -9 to 9,
   blocks multiplied in order, the AA^T scheme with its right factors transposed), against the schoolbook products;
   the digest of the products depends on the seed. Controls, which must all pass or the run stops: each printed scheme
   with one coefficient (chosen from the seed) increased by one must fail; the schoolbook schemes (40 products each)
   must pass, with q = 16 and gamma 24/33, the paper's own baseline for k = 4 (its appendix, ((1/2)k^2(k - 1))/(k^w -
   k^2)); the factor must give the paper's printed values for its other examples (8/(3^w - 9) = 0.623 for the 3 x 3
   AA^T scheme with q = 9; 2/3 for k = 2; 8/13 and, at w = 3, 4/9 for the earlier rank-34 scheme with q = 10); and the
   AA^T figure read without its transposes (C_i^k = sum_j X_i^j Y_j^k) must fail.

What it cannot check: that 8/13 was the best factor known before the paper, a question of the literature.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
"""

import hashlib
import importlib.util
import io
import json
import math
import os
import re
import sys
import tarfile
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, file))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check = _load("mm_check", "check.py")       # the seeded Stream and the digest of the other matrix receipts

EPRINT = ("arXiv-2511.10786v2.tar.gz", "4a5c0b1780c18ac15a0bd3cca4f9ce5a726d42599d146cfe0364e621bd9101e6")
FIGURES = {"gt": "schemes/gt-444.tex", "ug": "schemes/ug-444.tex"}
RELEASED = {
    "gt": ("gt-444c-rank26-rec-2-0-0-z-4.txt", "abdff1ed92386801ad785f34c0e8f81501d168a28954f8d553fca90c06205d7e"),
    "ug": ("ug-444-rank34-rec-12-0-0-z.txt", "58f07dbb009e174d97b6f497d949b95926a8319f5c05a1130ca8fdee9e1d29d2"),
}
N = 4
RANK, Q_MIN, GAMMA = 34, 12, Fraction(22, 37)
K_OMEGA = {2: 7, 4: 49}                      # k^w at w = log2 7, exactly, for k a power of 2
PRINTED_ADDITIONS = {"gt": 141, "ug": 148}
BLOCK, PROBES = 3, 2
LIMIT = 200
OUTPUTS = ("gt_products", "gt_wrong", "gt_q", "gt_q_equal_factors", "gt_gamma", "ug_products", "ug_wrong", "ug_q",
           "ug_gamma", "additions", "released", "coefficients", "probe_wrong", "probe_digest", "control_wrong",
           "controls", "conditions_met", "conditions_total", "test_passed")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- reading the figures

def unwrap(s, name):
    """s with every \\name{x} replaced by x (braces balanced; nested ones too)."""
    key = "\\" + name + "{"
    while key in s:
        s = _unwrap_once(s, name, key)
    return s


def _unwrap_once(s, name, key):
    out, i = [], 0
    while True:
        j = s.find(key, i)
        if j < 0:
            return "".join(out) + s[i:]
        out.append(s[i:j])
        k, depth = j + len(key), 1
        start = k
        while depth:
            if k >= len(s):
                raise Refused(f"unbalanced \\{name}{{")
            depth += {"{": 1, "}": -1}.get(s[k], 0)
            k += 1
        out.append(s[start:k - 1])
        i = k


def equations(tex):
    """[(name, right side)] of a figure, by rule 1 (TeX comments, from an unescaped % to the end of its line, first
    removed, so that nothing commented out is read)."""
    body = re.sub(r"(?<!\\)%[^\n]*", "", tex)
    for name in ("red", "blue", "reccall", "grey"):
        body = unwrap(body, name)
    body = re.sub(r"\\\\\[-1\.5mm\]\s*&\s*\\hspace\{[0-9.]+mm\}", " ", body)
    out = []
    for chunk in re.split(r"\\\\|\\hspace\{[0-9.]+cm\}", body):
        if "=" not in chunk:
            continue
        head, rhs = chunk.replace("&", " ").split("=", 1)
        m = re.search(r"((?:m|r)_\{\d+\}|C_\d\^\d)\s*$", head)
        if not m:
            continue
        rhs = re.split(r"\\end\{aligned\}", rhs)[0]
        out.append((m.group(1), " ".join(rhs.split())))
    return out


TERM = re.compile(r"([+-]?)\s*(\d*)\s*([AB])_(\d)\^(\d)")
CALL = re.compile(r"([+-]?)\s*([mr])_\{(\d+)\}")


def terms(s, pattern, what):
    """The matches of pattern covering s entirely (spaces between them only), or Refused."""
    found, pos = [], 0
    for m in pattern.finditer(s):
        if s[pos:m.start()].strip():
            raise Refused(f"{what}: unexpected {s[pos:m.start()]!r} in {s!r}")
        found.append(m)
        pos = m.end()
    if s[pos:].strip() or not found:
        raise Refused(f"{what}: cannot read {s!r}")
    return found


def linear(s, letter):
    """{(i, j): integer coefficient} of a sum of terms in letter_i^j."""
    out = {}
    for m in terms(s, TERM, "factor"):
        if m.group(3) != letter:
            raise Refused(f"factor {s!r}: {m.group(3)} where {letter} is expected")
        i, j = int(m.group(4)), int(m.group(5))
        if not (1 <= i <= N and 1 <= j <= N):
            raise Refused(f"factor {s!r}: block {i},{j} outside 4 x 4")
        c = (int(m.group(2)) if m.group(2) else 1) * (-1 if m.group(1) == "-" else 1)
        out[(i, j)] = out.get((i, j), 0) + c
    return {k: v for k, v in out.items() if v}


def read_figure(tex, kind):
    """The scheme a figure prints: [(name, U, V, W)], U and V dicts over blocks, W a dict over outputs."""
    defs, outs = {}, {}
    for name, rhs in equations(tex):
        if name.startswith("C_"):
            key = (int(name[2]), int(name[4]))
            if key in outs:
                raise Refused(f"output {name} printed twice")
            calls = {}
            for m in terms(rhs, CALL, name):
                c = (m.group(2), int(m.group(3)))
                calls[c] = calls.get(c, 0) + (-1 if m.group(1) == "-" else 1)
            outs[key] = calls
            continue
        key = (name[0], int(re.search(r"\d+", name).group()))
        if key in defs:
            raise Refused(f"product {name} printed twice")
        pattern = r"\((.*?)\)\s*\((.*?)\)\s*\\T" if kind == "gt" else r"\((.*?)\)\s*\((.*?)\)"
        m = re.fullmatch(pattern, rhs)
        if not m:
            raise Refused(f"product {name}: cannot read {rhs!r}")
        u, v = linear(m.group(1), "A"), linear(m.group(2), "A" if kind == "gt" else "B")
        if kind == "ug" and any(i > j for i, j in u):
            raise Refused(f"product {name}: an entry of A below its diagonal")
        defs[key] = (u, v)
    want = outputs(kind)
    if set(outs) != set(want):
        raise Refused(f"{kind}: outputs {sorted(outs)}, not {want}")
    w = {}
    for o, calls in outs.items():
        for c, x in calls.items():
            if c not in defs:
                raise Refused(f"{kind}: output {o} uses {c}, which is not printed")
            if x:
                w.setdefault(c, {})[o] = x
    unused = [c for c in defs if c not in w]
    if unused:
        raise Refused(f"{kind}: products printed but never used: {unused}")
    return [(f"{c[0]}{c[1]}", defs[c][0], defs[c][1], w[c]) for c in sorted(defs)]


def outputs(kind):
    if kind == "gt":
        return [(i, k) for i in range(1, N + 1) for k in range(i, N + 1)]
    return [(i, k) for i in range(1, N + 1) for k in range(1, N + 1)]


# ---------------------------------------------------------------- the released files

def read_released(text, kind):
    """A released .txt scheme: lines mN = (sum of a's)(sum of b's) and cN = sum of m's (or 0), indexed as the
    repository's generator indexes them (a, b and c from 1; packed upper triangles row by row)."""
    upper = [(i, k) for i in range(1, N + 1) for k in range(i, N + 1)]
    general = [(i, k) for i in range(1, N + 1) for k in range(1, N + 1)]
    a_index = general if kind == "gt" else upper
    b_index = general
    c_index = upper if kind == "gt" else general

    def lin(s, letter, index):
        out = {}
        for m in terms(s, re.compile(r"([+-]?)\s*(\d*)\s*([a-z])(\d+)"), "released factor"):
            if m.group(3) != letter or not 1 <= int(m.group(4)) <= len(index):
                raise Refused(f"released: cannot read {s!r}")
            key = index[int(m.group(4)) - 1]
            out[key] = out.get(key, 0) + (int(m.group(2)) if m.group(2) else 1) * (-1 if m.group(1) == "-" else 1)
        return {k: v for k, v in out.items() if v}

    defs, w = {}, {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.fullmatch(r"m(\d+)\s*=\s*\((.*)\)\s*\((.*)\)", line)
        if m:
            defs[int(m.group(1))] = (lin(m.group(2), "a", a_index), lin(m.group(3), "b", b_index))
            continue
        m = re.fullmatch(r"c(\d+)\s*=\s*(.*)", line)
        if m and 1 <= int(m.group(1)) <= len(c_index):
            if m.group(2).strip() != "0":
                o = c_index[int(m.group(1)) - 1]
                for t in terms(m.group(2), re.compile(r"([+-]?)\s*(\d*)\s*m(\d+)"), "released output"):
                    x = (int(t.group(2)) if t.group(2) else 1) * (-1 if t.group(1) == "-" else 1)
                    w.setdefault(int(t.group(3)), {})
                    w[int(t.group(3))][o] = w[int(t.group(3))].get(o, 0) + x
            continue
        raise Refused(f"released: cannot read {line!r}")
    return [(f"m{t}", defs[t][0], defs[t][1], {o: x for o, x in w.get(t, {}).items() if x}) for t in sorted(defs)]


def corners():
    """The eight corner calls of the AA^T figure, A_i^j (A_i^j)^T into C_i^i for i = 1 and 4."""
    return [(f"corner{i}{j}", {(i, j): 1}, {(i, j): 1}, {(i, i): 1}) for i in (1, N) for j in range(1, N + 1)]


# ---------------------------------------------------------------- the checks

def target(kind, transposed=True):
    """The tensor: {(left block, right block, output): 1}."""
    t = {}
    for (i, k) in outputs(kind):
        if kind == "gt":
            for j in range(1, N + 1):
                t[((i, j), (k, j) if transposed else (j, k), (i, k))] = 1
        else:
            for j in range(i, N + 1):
                t[((i, j), (j, k), (i, k))] = 1
    return t


def wrong(scheme, kind, transposed=True, skip=()):
    """How many coefficients of sum_t U_t (x) V_t (x) W_t differ from the tensor's (outputs in skip left out)."""
    got = {}
    for _, u, v, w in scheme:
        for a, x in u.items():
            for b, y in v.items():
                for o, z in w.items():
                    key = (a, b, o)
                    got[key] = got.get(key, 0) + x * y * z
    want = {k: v for k, v in target(kind, transposed).items() if k[2] not in skip}
    got = {k: v for k, v in got.items() if k[2] not in skip}
    return sum(1 for key in set(got) | set(want) if got.get(key, 0) != want.get(key, 0))


def products(scheme):
    return sum(1 for _, u, v, w in scheme if u and v and w)


def recursive(scheme, kind):
    """(q, q by equal factors, q by diagonal output) for AA^T; (q, q, q) for AB."""
    if kind == "gt":
        equal = sum(1 for _, u, v, w in scheme if u == v)
        diagonal = sum(1 for _, u, v, w in scheme if w and all(i == k for i, k in w))
        return max(equal, diagonal), equal, diagonal
    q = sum(1 for _, u, v, w in scheme if u and all(i == j for i, j in u))
    return q, q, q


def gamma(r, q, k=N):
    return Fraction(r - q, K_OMEGA[k] - q)


def gamma_float(r, q, k, omega=math.log2(7)):
    return (r - q) / (k ** omega - q)


def additions(scheme):
    return sum(len(u) - 1 + len(v) - 1 for _, u, v, w in scheme) + _output_additions(scheme)


def _output_additions(scheme):
    per = {}
    for _, u, v, w in scheme:
        for o, z in w.items():
            if z:
                per[o] = per.get(o, 0) + 1
    return sum(n - 1 for n in per.values())


def canonical(term):
    """A rank-one term with each factor's sign fixed by its first entry (the signs moved into W)."""
    _, u, v, w = term

    def norm(d):
        first = d[min(d)]
        s = 1 if first > 0 else -1
        return tuple(sorted((k, x * s) for k, x in d.items())), s
    cu, su = norm(u)
    cv, sv = norm(v)
    return cu, cv, tuple(sorted((o, z * su * sv) for o, z in w.items()))


def shared(a, b):
    ca, cb = {canonical(t) for t in a if t[3]}, {canonical(t) for t in b if t[3]}
    return len(ca & cb)


def coefficient_set(scheme):
    return sorted({x for _, u, v, w in scheme for x in list(u.values()) + list(v.values()) + list(w.values())})


# ---------------------------------------------------------------- probes and controls

def matmul(X, Y):
    return [[sum(X[i][t] * Y[t][j] for t in range(len(Y))) for j in range(len(Y[0]))] for i in range(len(X))]


def madd(X, Y, c=1):
    return [[x + c * y for x, y in zip(rx, ry)] for rx, ry in zip(X, Y)]


def transpose(X):
    return [list(r) for r in zip(*X)]


def zeros(n):
    return [[0] * n for _ in range(n)]


def combine(blocks, d):
    out = zeros(BLOCK)
    for key, c in d.items():
        out = madd(out, blocks[key], c)
    return out


def probe(scheme, kind, stream):
    """The scheme on block matrices drawn from the stream; (entries wrong, the product's text)."""
    def draw():
        return [[stream.below(19) - 9 for _ in range(BLOCK)] for _ in range(BLOCK)]
    A = {(i, j): draw() for i in range(1, N + 1) for j in range(1, N + 1)}
    if kind == "ug":
        for i in range(1, N + 1):
            for j in range(1, N + 1):
                if i > j:
                    A[(i, j)] = zeros(BLOCK)
                elif i == j:
                    A[(i, j)] = [[x if r <= c else 0 for c, x in enumerate(row)] for r, row in enumerate(A[(i, j)])]
        B = {(i, j): draw() for i in range(1, N + 1) for j in range(1, N + 1)}
    C = {o: zeros(BLOCK) for o in outputs(kind)}
    for _, u, v, w in scheme:
        left = combine(A, u)
        right = transpose(combine(A, v)) if kind == "gt" else combine(B, v)
        prod = matmul(left, right)
        for o, z in w.items():
            C[o] = madd(C[o], prod, z)
    bad, lines = 0, []
    for (i, k) in outputs(kind):
        want = zeros(BLOCK)
        for j in range(1, N + 1):
            if kind == "gt":
                want = madd(want, matmul(A[(i, j)], transpose(A[(k, j)])))
            elif j >= i:
                want = madd(want, matmul(A[(i, j)], B[(j, k)]))
        bad += sum(1 for r in range(BLOCK) for c in range(BLOCK) if C[(i, k)][r][c] != want[r][c])
        lines.append(f"{kind}{i}{k}:" + ";".join(",".join(str(x) for x in row) for row in C[(i, k)]))
    return bad, lines


def altered(scheme, stream):
    """The scheme with one coefficient of one left factor increased by one, both chosen from the stream."""
    t = stream.below(len(scheme))
    name, u, v, w = scheme[t]
    keys = sorted(u)
    key = keys[stream.below(len(keys))]
    u2 = dict(u)
    u2[key] += 1
    return scheme[:t] + [(name, {k: x for k, x in u2.items() if x}, v, w)] + scheme[t + 1:]


def schoolbook(kind):
    if kind == "gt":
        return [(f"n{i}{k}{j}", {(i, j): 1}, {(k, j): 1}, {(i, k): 1}) for (i, k) in outputs(kind) for j in range(1, N + 1)]
    return [(f"n{i}{k}{j}", {(i, j): 1}, {(j, k): 1}, {(i, k): 1}) for (i, k) in outputs(kind) for j in range(i, N + 1)]


def controls(schemes, seed):
    """{name: (value, passed)}; every one must pass."""
    out = {}
    for kind, scheme in schemes.items():
        bad = wrong(altered(scheme, check.Stream(seed, f"structured/control/{kind}")), kind)
        out[f"{kind} altered"] = (bad, bad > 0)
        sb = schoolbook(kind)
        r, q = products(sb), recursive(sb, kind)[0]
        out[f"{kind} schoolbook"] = (f"{r} products, wrong {wrong(sb, kind)}, q {q}, {gamma(r, q)}",
                                     wrong(sb, kind) == 0 and r == 40 and q == 16 and gamma(r, q) == Fraction(24, 33))
    k = 4
    baseline = Fraction(k * k * (k - 1), 2) / (K_OMEGA[k] - k * k)
    out["baseline k=4"] = (str(baseline), baseline == Fraction(24, 33))
    g3 = gamma_float(17, 9, 3)
    out["3x3 AA^T, q 9"] = (f"{g3:.3f}", f"{g3:.3f}" == "0.623")
    out["k=2 baseline"] = (str(gamma(6, 4, 2)), gamma(6, 4, 2) == Fraction(2, 3))
    eca, eca3 = gamma(34, 10), Fraction(34 - 10, 4 ** 3 - 10)
    out["earlier rank 34, q 10"] = (f"{eca}; {eca3} at w = 3", eca == Fraction(8, 13) and eca3 == Fraction(4, 9))
    misread = wrong(schemes["gt"], "gt", transposed=False)
    out["gt without transposes"] = (misread, misread > 0)
    return out


# ---------------------------------------------------------------- the run

def input_bytes(inputs, name, sha):
    with open(os.path.join(inputs, name), "rb") as f:
        data = f.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha:
        raise Refused(f"{name}: sha256 {got}, not the committed {sha}")
    return data


def read_eprint(data):
    texts = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for kind, member in FIGURES.items():
            texts[kind] = tar.extractfile(member).read().decode("utf-8")
    return texts


def conditions(results):
    out = {}
    for kind in ("gt", "ug"):
        r = results[kind]
        out[f"{kind}: exact over the integers"] = r["wrong"] == 0
        out[f"{kind}: at most 34 products"] = r["products"] <= RANK
        out[f"{kind}: at least 12 recursive calls"] = r["q"] >= Q_MIN
        out[f"{kind}: factor at most 22/37"] = r["gamma"] <= GAMMA
    return out


def run(seed, inputs="inputs", results="results"):
    texts = read_eprint(input_bytes(inputs, *EPRINT))
    printed = {kind: read_figure(texts[kind], kind) for kind in ("gt", "ug")}
    for kind, scheme in printed.items():
        if any(not isinstance(x, int) for x in coefficient_set(scheme)):
            raise Refused(f"{kind}: a coefficient that is not an integer")
    res = {}
    for kind, scheme in printed.items():
        r = products(scheme)
        q, q1, q2 = recursive(scheme, kind)
        res[kind] = {"products": r, "wrong": wrong(scheme, kind), "q": q, "q_equal_factors": q1,
                     "q_diagonal_output": q2, "gamma": gamma(r, q), "additions": additions(scheme),
                     "coefficients": coefficient_set(scheme)}
    released = {kind: read_released(input_bytes(inputs, *RELEASED[kind]).decode("ascii"), kind) for kind in RELEASED}
    rel_gt_full = released["gt"] + corners()
    rel = {"gt corner scheme": {"products": products(released["gt"]),
                                "wrong without corners": wrong(released["gt"], "gt", skip=((1, 1), (N, N)))},
           "gt with corners": {"products": products(rel_gt_full), "wrong": wrong(rel_gt_full, "gt"),
                               "q": recursive(rel_gt_full, "gt")[0], "q by criteria": recursive(rel_gt_full, "gt")[1:],
                               "shared with the figure": shared(rel_gt_full, printed["gt"])},
           "ug": {"products": products(released["ug"]), "wrong": wrong(released["ug"], "ug"),
                  "q": recursive(released["ug"], "ug")[0], "shared with the figure": shared(released["ug"], printed["ug"]),
                  "coefficients": coefficient_set(released["ug"])}}
    probe_wrong, lines = 0, []
    for kind, scheme in printed.items():
        for p in range(PROBES):
            bad, text = probe(scheme, kind, check.Stream(seed, f"structured/probe/{kind}/{p}"))
            probe_wrong += bad
            lines.extend(text)
    ctl = controls(printed, seed)
    failed = [name for name, (_, ok) in ctl.items() if not ok]
    if failed or probe_wrong:
        raise Refused(f"the checker is not to be trusted: controls failed {failed}, probe entries wrong {probe_wrong}")
    cond = conditions(res)
    values = {
        "gt_products": res["gt"]["products"], "gt_wrong": res["gt"]["wrong"], "gt_q": res["gt"]["q"],
        "gt_q_equal_factors": res["gt"]["q_equal_factors"], "gt_gamma": str(res["gt"]["gamma"]),
        "ug_products": res["ug"]["products"], "ug_wrong": res["ug"]["wrong"], "ug_q": res["ug"]["q"],
        "ug_gamma": str(res["ug"]["gamma"]),
        "additions": "; ".join(f"{k} {res[k]['additions']} (printed {PRINTED_ADDITIONS[k]})" for k in ("gt", "ug")),
        "released": (f"gt {rel['gt corner scheme']['products']} + 8 corners: wrong {rel['gt with corners']['wrong']}, "
                     f"q {rel['gt with corners']['q']}, {rel['gt with corners']['shared with the figure']} terms as "
                     f"printed; ug {rel['ug']['products']}: wrong {rel['ug']['wrong']}, q {rel['ug']['q']}, "
                     f"{rel['ug']['shared with the figure']} terms as printed"),
        "coefficients": (f"printed gt {res['gt']['coefficients']}, ug {res['ug']['coefficients']}; "
                         f"released ug {rel['ug']['coefficients']}"),
        "probe_wrong": probe_wrong, "probe_digest": check.digest(lines),
        "control_wrong": "; ".join(f"{k} {ctl[f'{k} altered'][0]}" for k in ("gt", "ug")),
        "controls": f"{len(ctl) - len(failed)} of {len(ctl)}",
        "conditions_met": sum(cond.values()), "conditions_total": len(cond),
        "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"values": values, "conditions": cond,
              "printed": {k: {**v, "gamma": str(v["gamma"]), "gamma_float": float(v["gamma"])} for k, v in res.items()},
              "released": rel, "controls": {k: [str(v[0]), v[1]] for k, v in ctl.items()},
              "terms": {k: [[t[0], sorted(map(list, t[1].items())), sorted(map(list, t[2].items())),
                             sorted(map(list, t[3].items()))] for t in s] for k, s in printed.items()}}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as fh:
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
        sys.exit(f"structured: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
