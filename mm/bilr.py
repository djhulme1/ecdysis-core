#!/usr/bin/env python3
"""Rank-23 decompositions of the 3 x 3 matrix multiplication tensor with cyclic symmetry, and one with a symmetry group
of order 12.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:3837611a1df96887) is from Ballard,
Ikenmeyer, Landsberg & Ryder, "The geometry of rank decompositions of matrix multiplication II: 3 x 3 matrices"
(arXiv:1801.00843; J. Pure Appl. Algebra 223(8), 3205-3224, 2019): "We present new rank $23$ decompositions for the
$3\\times 3$ matrix multiplication tensor $M_{\\langle 3\\rangle}$. All our decompositions have symmetry groups that
include the standard cyclic permutation of factors but otherwise exhibit a range of behavior. One of them has 11 cubes
as summands and admits an unexpected symmetry group of order 12."

Its registered test: refuted if, read from the e-print's TeX (its zfzt, lad, twofix, addtlone, addtltwo and
addtlthree data files), any of the six decompositions it presents does not sum exactly to M<3> = sum x_ij (x) y_jk (x)
z_ki in 23 rank-one terms, or is not mapped to itself by the cyclic permutation of factors; or if S_{Z4xZ3} has other
than 11 cubes among its terms, or its symmetry group, the elements of [(PGL3)^3 x| Z3] x| Z2 mapping its set of terms
to itself, does not have order 12.

Standard library only. The input is the claim's data of record, the e-print (arXiv-1801.00843v1.tar.gz), checked
against its SHA-256 and size and read in memory; its data files are read as text and nothing in it is run. Every rule
below was fixed before any seed existed.

1. Reading. The tarball's zfzt_matrices.tex (S_{Z4xZ3}), lad_matrices.tex (S_{Lader-Z3}), twofix_matrices.tex
   (S_{2fix-Z3}), addtlone_matrices.tex, addtltwo_matrices.tex and addtlthree_matrices.tex (the three additional
   decompositions), and std_matrices.tex for a control. After "\\Mthree", \\label{...} is removed and the text is split
   at every "+" outside braces; a piece with "^{\\ot 3}" and one pmatrix is a cube X (x) X (x) X; a piece with
   "\\BZ_3^{std} \\cdot" and three pmatrices X, Y, Z is the orbit X (x) Y (x) Z, Y (x) Z (x) X, Z (x) X (x) Y; a
   pmatrix is 3 x 3 integers. Any other piece refuses the run.
2. M<3>: sum over i, j, k of E_ij (x) E_jk (x) E_ki, the trilinear form tr(XYZ), a term A (x) B (x) C read as
   <A, X><B, Y><C, Z> with <A, X> = sum A_ij X_ij (the paper's own example term reads x_23 (y_32 - y_31)(z_22 - z_23 +
   z_32 - z_33)). A decomposition sums to M<3> if all 729 coefficients of the sum of its terms equal M<3>'s, exactly.
3. Terms are rank-one tensors: (A, B, C) and (aA, bB, cC) with abc = 1 are one term, compared in a normal form (A
   scaled to a first non-zero entry of 1, B likewise, the scalars carried into C). A cube is a term whose three
   factors are proportional.
4. The cyclic symmetry: the set of terms is mapped onto itself by (A, B, C) -> (B, C, A).
5. The symmetry group, as the paper defines it (its section 4): the elements of [(PGL3)^3 x| Z3] x| Z2, acting by an
   outer part tau (one of (A,B,C) -> (A,B,C), (B,C,A), (C,A,B), (A^T,C^T,B^T), (B^T,A^T,C^T), (C^T,B^T,A^T), each of
   which fixes M<3>, checked) followed by (A, B, C) -> (gAh^-1, hBk^-1, kCg^-1), that map the set of terms onto itself.
   It is found exactly, for each tau: the terms of tau(S) whose three factors have rank one are taken, in a greedy
   order, as anchors, each adding the linear conditions that g, h and k carry its factors' column and row spaces onto
   those of its image (g sends A's column to the image's, g^T sends the image C's row to C's, and so on). Every
   assignment of anchors to rank-one terms of S is followed until the conditions fix each of g, h and k up to scale
   (rank 8 of 9); a triple is kept if invertible and if it maps all of tau(S) onto S. The anchors are chosen until the
   identity's own conditions reach rank 8 (else the run refuses); as an invertible map carries them to conditions of
   the same rank, an assignment still deficient after the anchors has no solution and is dropped. Elements are counted
   once each (g, h, k normalised up to scale).
6. The test's five conditions: all six decompositions sum to M<3>; each has 23 distinct terms; each is mapped onto
   itself by the cyclic permutation; S_{Z4xZ3} has 11 cubes; its symmetry group has order 12. test_passed is 1 if all
   five hold.
7. Beside the test, none of it counted: the symmetry groups of the other five (the paper gives S_{2fix-Z3}'s as Z3,
   and identifies S_{Lader-Z3} as a member of Laderman's family, whose group Burichenko found to be S4, of order 24),
   each group's split by outer part, and whether S_{Z4xZ3}'s elements with tau the identity are exactly the powers of
   the paper's a_0 acting diagonally.

Controls (controls_passed counts those that behave as stated): std (the standard decomposition, 27 terms) sums to
M<3>; each of the six with one entry, drawn from the seed, increased by one does not; S_{Z4xZ3} carried by a
seed-drawn (g, h, k) of integer matrices to another member of its family again has a group of order 12; and the group
search finds S_{Lader-Z3}'s group of order 24.

What it cannot check: that the decompositions were new in 2018, a question of the literature.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
"""

import hashlib
import io
import json
import os
import re
import sys
import tarfile
from fractions import Fraction as F

EPRINT = ("arXiv-1801.00843v1.tar.gz", "2fc6b0892a4e386f3eed03ace58f712bbf3e83bde5fc60c7f02df3c2bc31203e", 55121)
NAMES = ("zfzt", "lad", "twofix", "addtlone", "addtltwo", "addtlthree")
CONTROL = "std"
A0 = ((0, 0, -1), (1, 0, -1), (0, 1, -1))
LIMIT = 200
OUTPUTS = ("read", "sums_exact", "terms_23", "cyclic", "zfzt_cubes", "zfzt_group", "zfzt_group_parts", "zfzt_a0",
           "group_orders", "lad_family", "conditions_met", "conditions_total", "controls_passed", "controls_total",
           "test_passed")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- reading (rule 1)

def load(inputs):
    name, sha, size = EPRINT
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    if len(data) != size or hashlib.sha256(data).hexdigest() != sha:
        raise Refused(f"{name}: not the pinned e-print")
    return data


def texts(data):
    out = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for name in NAMES + (CONTROL,):
            member = tar.getmember(f"{name}_matrices.tex")
            out[name] = tar.extractfile(member).read().decode("utf-8")
    return out


def pmatrices(piece):
    out = []
    for body in re.findall(r"\\begin\{pmatrix\}(.*?)\\end\{pmatrix\}", piece, re.S):
        rows = [r.strip() for r in body.split("\\\\") if r.strip()]
        try:
            m = tuple(tuple(F(int(x.strip())) for x in r.split("&")) for r in rows)
        except ValueError:
            raise Refused(f"not an integer matrix: {body.strip()[:60]}")
        if len(m) != 3 or any(len(r) != 3 for r in m):
            raise Refused(f"not a 3 x 3 matrix: {body.strip()[:60]}")
        out.append(m)
    return out


def parse(text):
    """Rule 1: the terms, in the order printed."""
    if "\\Mthree" not in text:
        raise Refused("no \\Mthree")
    body = text[text.index("\\Mthree") + len("\\Mthree"):]
    body = body[:body.index("\\end{align}")]
    body = re.sub(r"\\label\{[^}]*\}", "", body)
    terms = []
    for piece in re.split(r"\+(?![^{]*\})", body.replace("&=", "+").replace("&+", "+")):
        ms = pmatrices(piece)
        rest = re.sub(r"\\begin\{pmatrix\}.*?\\end\{pmatrix\}", "", piece, flags=re.S)
        rest = re.sub(r"\\\\|&|\s", "", rest)
        if not ms and not rest:
            continue
        if rest == "^{\\ot3}" and len(ms) == 1:
            terms.append((ms[0], ms[0], ms[0]))
        elif rest == "\\BZ_3^{std}\\cdot\\ot\\ot" and len(ms) == 3:
            x, y, z = ms
            terms += [(x, y, z), (y, z, x), (z, x, y)]
        else:
            raise Refused(f"cannot read the piece {piece.strip()[:80]!r}")
    return terms


# ---------------------------------------------------------------- matrices

def mul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def tr(a):
    return tuple(tuple(a[j][i] for j in range(3)) for i in range(3))


def det(a):
    return (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
            + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))


def inv(a):
    d = det(a)
    if d == 0:
        raise ZeroDivisionError("singular")
    c = [[F(0)] * 3 for _ in range(3)]
    for i in range(3):
        for j in range(3):
            m = [[a[r][s] for s in range(3) if s != j] for r in range(3) if r != i]
            c[j][i] = F((-1) ** (i + j)) * (m[0][0] * m[1][1] - m[0][1] * m[1][0]) / d
    return tuple(tuple(r) for r in c)


def rank(rows, ncols):
    m = [list(r) for r in rows]
    r = 0
    for c in range(ncols):
        p = next((i for i in range(r, len(m)) if m[i][c] != 0), None)
        if p is None:
            continue
        m[r], m[p] = m[p], m[r]
        for i in range(r + 1, len(m)):
            if m[i][c] != 0:
                f = m[i][c] / m[r][c]
                m[i] = [x - f * y for x, y in zip(m[i], m[r])]
        r += 1
    return r


def nullspace(rows, n=9):
    m = [list(r) for r in rows]
    piv, r = [], 0
    for c in range(n):
        p = next((i for i in range(r, len(m)) if m[i][c] != 0), None)
        if p is None:
            continue
        m[r], m[p] = m[p], m[r]
        iv = 1 / m[r][c]
        m[r] = [x * iv for x in m[r]]
        for i in range(len(m)):
            if i != r and m[i][c] != 0:
                f = m[i][c]
                m[i] = [x - f * y for x, y in zip(m[i], m[r])]
        piv.append(c)
        r += 1
    basis = []
    for f in (c for c in range(n) if c not in piv):
        v = [F(0)] * n
        v[f] = F(1)
        for i, c in enumerate(piv):
            v[c] = -m[i][f]
        basis.append(v)
    return basis


def as_matrix(v):
    return tuple(tuple(v[3 * i + j] for j in range(3)) for i in range(3))


def first_nonzero(a):
    return next(x for r in a for x in r if x != 0)


def scale(a, s):
    return tuple(tuple(x * s for x in r) for r in a)


# ---------------------------------------------------------------- tensors and terms (rules 2 to 4)

M3 = {(i, j, j, k, k, i): F(1) for i in range(3) for j in range(3) for k in range(3)}


def tensor(terms):
    t = {}
    for a, b, c in terms:
        ea = [(i, j, a[i][j]) for i in range(3) for j in range(3) if a[i][j]]
        eb = [(i, j, b[i][j]) for i in range(3) for j in range(3) if b[i][j]]
        ec = [(i, j, c[i][j]) for i in range(3) for j in range(3) if c[i][j]]
        for i, j, x in ea:
            for k, l, y in eb:
                for m, n, z in ec:
                    key = (i, j, k, l, m, n)
                    t[key] = t.get(key, 0) + x * y * z
    return {k: v for k, v in t.items() if v}


def normal(term):
    """Rule 3: the normal form of a rank-one tensor A (x) B (x) C."""
    a, b, c = term
    s = first_nonzero(a)
    a, b = scale(a, 1 / s), scale(b, s)
    s = first_nonzero(b)
    b, c = scale(b, 1 / s), scale(c, s)
    return (a, b, c)


def proportional(x, y):
    sx, sy = first_nonzero(x), first_nonzero(y)
    return scale(x, 1 / sx) == scale(y, 1 / sy)


def is_cube(term):
    a, b, c = term
    return proportional(a, b) and proportional(a, c)


def mrank(a):
    return rank(a, 3)


OUTER = {"id": lambda t: t, "c": lambda t: (t[1], t[2], t[0]), "c2": lambda t: (t[2], t[0], t[1]),
         "t": lambda t: (tr(t[0]), tr(t[2]), tr(t[1])), "tc": lambda t: (tr(t[1]), tr(t[0]), tr(t[2])),
         "tc2": lambda t: (tr(t[2]), tr(t[1]), tr(t[0]))}


def act(ghk, inverses, term):
    g, h, k = ghk
    gi, hi, ki = inverses
    a, b, c = term
    return (mul(mul(g, a), hi), mul(mul(h, b), ki), mul(mul(k, c), gi))


# ---------------------------------------------------------------- the symmetry group (rule 5)

def factors(a):
    """A rank-one matrix as column and row: a = col row^T."""
    i0 = next(i for i in range(3) if any(a[i]))
    j0 = next(j for j in range(3) if a[i0][j])
    col = tuple(a[r][j0] for r in range(3))
    row = tuple(x / a[i0][j0] for x in a[i0])
    return col, row


def parallel(p, q):
    """Conditions on X (row-major, 9 unknowns) that X p is parallel to q: (X p) x q = 0."""
    rows = []
    for u, v in ((1, 2), (2, 0), (0, 1)):
        row = [F(0)] * 9
        for j in range(3):
            row[3 * u + j] += p[j] * q[v]
            row[3 * v + j] -= p[j] * q[u]
        rows.append(row)
    return rows


def parallel_t(p, q):
    """Conditions that X^T p is parallel to q."""
    rows = []
    for u, v in ((1, 2), (2, 0), (0, 1)):
        row = [F(0)] * 9
        for j in range(3):
            row[3 * j + u] += p[j] * q[v]
            row[3 * j + v] -= p[j] * q[u]
        rows.append(row)
    return rows


def conditions_for(s, t):
    """The conditions that (g, h, k) carries the rank-one term s onto t."""
    (a1, b1), (c1, d1), (e1, f1) = (factors(m) for m in s)
    (a2, b2), (c2, d2), (e2, f2) = (factors(m) for m in t)
    return {"g": parallel(a1, a2) + parallel_t(f2, f1),
            "h": parallel(c1, c2) + parallel_t(b2, b1),
            "k": parallel(e1, e2) + parallel_t(d2, d1)}


def anchors_for(src):
    pool = [t for t in src if all(mrank(m) == 1 for m in t)]
    chosen, eqs = [], {x: [] for x in "ghk"}
    while pool and not all(rank(eqs[x], 9) == 8 for x in "ghk"):
        best = max(pool, key=lambda s: (sum(rank(eqs[x] + conditions_for(s, s)[x], 9) for x in "ghk"),
                                        -pool.index(s)))
        e = conditions_for(best, best)
        new = {x: eqs[x] + e[x] for x in "ghk"}
        if sum(rank(new[x], 9) for x in "ghk") == sum(rank(eqs[x], 9) for x in "ghk"):
            break
        chosen.append(best)
        pool.remove(best)
        eqs = new
    if not all(rank(eqs[x], 9) == 8 for x in "ghk"):
        raise Refused("the rank-one terms do not fix g, h and k")
    return chosen


def up_to_scale(a):
    return scale(a, 1 / first_nonzero(a))


def symmetry_group(terms):
    """Rule 5: the elements (tau, g, h, k) mapping the set of terms onto itself."""
    target = {normal(t) for t in terms}
    if len(target) != len(terms):
        raise Refused("repeated terms")
    images = [t for t in terms if all(mrank(m) == 1 for m in t)]
    found = []
    for name, f in OUTER.items():
        src = [f(t) for t in terms]
        anchors = anchors_for(src)
        sols = set()

        def search(depth, eqs):
            if depth:
                null = {x: nullspace(eqs[x]) for x in "ghk"}
                if any(len(v) == 0 for v in null.values()):
                    return
                if all(len(v) == 1 for v in null.values()):
                    g, h, k = (as_matrix(null[x][0]) for x in "ghk")
                    if 0 in (det(g), det(h), det(k)):
                        return
                    invs = (inv(g), inv(h), inv(k))
                    if all(normal(act((g, h, k), invs, t)) in target for t in src):
                        sols.add((name, up_to_scale(g), up_to_scale(h), up_to_scale(k)))
                    return
                if depth == len(anchors):
                    return
            for t in images:
                e = conditions_for(anchors[depth], t)
                search(depth + 1, {x: eqs[x] + e[x] for x in "ghk"})
        search(0, {x: [] for x in "ghk"})
        found += sorted(sols, key=repr)
    return found


# ---------------------------------------------------------------- seeds, controls and the verdict

class Stream:
    """Integers from the seed: SHA-256 of seed, label and a counter."""

    def __init__(self, seed, label):
        self.seed, self.label, self.n = seed, label, 0

    def below(self, m):
        self.n += 1
        h = hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
        return int.from_bytes(h[:8], "big") % m


def checks(terms):
    exact = tensor(terms) == M3
    distinct = len({normal(t) for t in terms})
    cyclic = {normal(t) for t in terms} == {normal(OUTER["c"](t)) for t in terms}
    return exact, distinct, cyclic


def bump(terms, stream):
    """One entry of one factor of one term increased by one."""
    i = stream.below(len(terms))
    f = stream.below(3)
    r, c = stream.below(3), stream.below(3)
    t = list(terms[i])
    m = [list(row) for row in t[f]]
    m[r][c] += 1
    t[f] = tuple(tuple(row) for row in m)
    return terms[:i] + [tuple(t)] + terms[i + 1:], (i, f, r, c)


def invertible_draw(stream):
    while True:
        m = tuple(tuple(F(stream.below(5) - 2) for _ in range(3)) for _ in range(3))
        if det(m) != 0:
            return m


def conditions(results, zfzt_cubes, zfzt_group):
    """Rule 6."""
    return {"all six sum to M<3>": all(r["exact"] for r in results.values()),
            "each has 23 distinct terms": all(r["distinct"] == 23 and r["printed"] == 23 for r in results.values()),
            "each is mapped onto itself by the cyclic permutation": all(r["cyclic"] for r in results.values()),
            "S_{Z4xZ3} has 11 cubes": zfzt_cubes == 11,
            "S_{Z4xZ3}'s symmetry group has order 12": zfzt_group == 12}


def run(seed, inputs="inputs", results="results"):
    data = load(inputs)
    tx = texts(data)
    decs = {name: parse(tx[name]) for name in NAMES + (CONTROL,)}
    for name, f in OUTER.items():
        if tensor([f(t) for t in decs[CONTROL]]) != M3:
            raise Refused(f"the outer part {name} does not fix M<3>")
    res = {}
    for name in NAMES:
        exact, distinct, cyclic = checks(decs[name])
        res[name] = {"printed": len(decs[name]), "distinct": distinct, "exact": exact, "cyclic": cyclic,
                     "cubes": sum(1 for t in decs[name] if is_cube(t)),
                     "rank_triples": sorted(tuple(mrank(m) for m in t) for t in decs[name])}
    groups = {name: symmetry_group(decs[name]) for name in NAMES}
    parts = {name: {o: sum(1 for e in groups[name] if e[0] == o) for o in OUTER} for name in NAMES}
    a0 = tuple(tuple(F(x) for x in r) for r in A0)
    powers, p = set(), ((F(1), F(0), F(0)), (F(0), F(1), F(0)), (F(0), F(0), F(1)))
    for _ in range(4):
        powers.add((up_to_scale(p),) * 3)
        p = mul(a0, p)
    zid = {e[1:] for e in groups["zfzt"] if e[0] == "id"}
    cond = conditions(res, res["zfzt"]["cubes"], len(groups["zfzt"]))

    ctl, ctl_detail = {}, {}
    ex, n_std, _ = checks(decs[CONTROL])
    ctl["std sums to M<3> with 27 terms"] = ex and n_std == 27 and len(decs[CONTROL]) == 27
    stream = Stream(seed, "bilr/controls")
    bumped = {}
    for name in NAMES:
        changed, where = bump(decs[name], stream)
        bumped[name] = {"where": where, "fails": tensor(changed) != M3}
    ctl["each of the six with one entry increased does not sum to M<3>"] = all(b["fails"] for b in bumped.values())
    g, h, k = invertible_draw(stream), invertible_draw(stream), invertible_draw(stream)
    invs = (inv(g), inv(h), inv(k))
    moved = [act((g, h, k), invs, t) for t in decs["zfzt"]]
    moved_group = symmetry_group(moved) if tensor(moved) == M3 else []
    ctl["S_{Z4xZ3} moved by a drawn (g, h, k) again has a group of order 12"] = len(moved_group) == 12
    ctl["the search finds S_{Lader-Z3}'s group of order 24"] = len(groups["lad"]) == 24
    ctl_detail = {"bumped": bumped, "moved_by": [[[str(x) for x in r] for r in m] for m in (g, h, k)],
                  "moved_group": len(moved_group)}

    values = {
        "read": "; ".join(f"{n} {res[n]['printed']}" for n in NAMES) + f"; {CONTROL} {len(decs[CONTROL])} (terms)",
        "sums_exact": sum(1 for r in res.values() if r["exact"]),
        "terms_23": sum(1 for r in res.values() if r["distinct"] == 23 and r["printed"] == 23),
        "cyclic": sum(1 for r in res.values() if r["cyclic"]),
        "zfzt_cubes": res["zfzt"]["cubes"],
        "zfzt_group": len(groups["zfzt"]),
        "zfzt_group_parts": ", ".join(f"{o} {parts['zfzt'][o]}" for o in OUTER),
        "zfzt_a0": int(zid == powers),
        "group_orders": ", ".join(f"{n} {len(groups[n])}" for n in NAMES),
        "lad_family": ", ".join(f"{o} {parts['lad'][o]}" for o in OUTER),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
        "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for key, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")

    def strm(m):
        return [[str(x) for x in r] for r in m]
    detail = {"conditions": cond, "controls": ctl, "control_detail": ctl_detail, "decompositions": res,
              "groups": {n: [{"outer": e[0], "g": strm(e[1]), "h": strm(e[2]), "k": strm(e[3])} for e in groups[n]]
                         for n in NAMES},
              "parts": parts}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, default=list)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"bilr: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
