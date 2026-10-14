#!/usr/bin/env python3
"""Grochow & Moore's lattice decomposition of the n x n matrix multiplication tensor in n^3 - n + 1 terms, checked
exactly for n = 2 to 12.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:a22c591f7d82ced7) is from Grochow & Moore,
"Matrix multiplication algorithms from group orbits" (arXiv:1612.01527v2): "In particular, using lattices we give the
most transparent proof to date of Strassen's algorithm; the same proof works for all n, to yield a decomposition with
$n^3 - n + 1$ terms."

Its registered test: refuted if, for some n from 2 to 12, the decomposition the e-print's equation (eq:lattice) prints,
T_n = id (x) id (x) id + (n/(n+1))^3 sum over distinct ordered triples i, j, k of |w_i><w_j - w_i| (x) |w_j><w_k - w_j|
(x) |w_k><w_i - w_k|, with w_1, ..., w_(n+1) unit vectors at the corners of a regular simplex centred at the origin, is
not exactly the n x n matrix multiplication tensor (<T_n, A (x) B (x) C> = tr ABC), or has other than n^3 - n + 1
terms. The equation is read from the e-print's TeX (v2).

The scipy-notebook image (numpy, for the integer tensor sums). The input is the claim's data of record, the e-print
(arXiv-1612.01527v2.tar.gz), checked against its SHA-256 and size and read in memory; its TeX is read as text and
nothing in it is run. Every rule below was fixed before any decomposition was built.

1. Reading. The tarball's strassen-fourier-continued.tex, its whitespace collapsed. The equation labelled eq:lattice
   must read exactly as LATTICE_TEX below, and the statements in STATEMENTS must be present: the tensor's definition
   (<MM, A (x) B (x) C> = tr ABC; the macro \\T is MM), the frame (unit vectors at the corners of a simplex, inner
   products -1/n), the count of triples, the proof's two identities and its conclusion. The macros: \\ket{x} is |x>,
   \\bra{x} is <x|, \\id is the identity. The run is refused otherwise.
2. The decomposition, for n >= 2. V = {x in Q^(n+1): sum x = 0}, with the standard inner product of Q^(n+1). The
   corners are u_i = e_i - 1/(n+1) (1, ..., 1), i = 1..n+1: |u_i|^2 = n/(n+1) and <u_i, u_j> = -1/(n+1), so the unit
   vectors are w_i = s u_i with s^2 = (n+1)/n, <w_i, w_j> = -1/n, and they point to the corners of a regular simplex
   centred at the origin. Every term of the sum carries six w's, so (n/(n+1))^3 s^6 = 1 and the term is
   |u_i><u_j - u_i| (x) |u_j><u_k - u_j| (x) |u_k><u_i - u_k|, with rational entries. |u><v| is the operator
   x -> u <v, x> on V. Operators on V are written in the basis f_a = e_a - e_(n+1), a = 1..n, of V, whose dual basis
   reads a vector of V by its first n coordinates: |u><v| has the matrix M_ab = u_a <v, f_b> = u_a (v_b - v_(n+1)), and
   id the identity matrix. T_n does not depend on the basis: it is the tensor of (A, B, C) -> tr ABC, whose components
   in any basis are those of sum over a, b, c of E_ab (x) E_bc (x) E_ca. So the identity to check is
   I (x) I (x) I + sum over distinct (i, j, k) of M(u_i, u_j - u_i) (x) M(u_j, u_k - u_j) (x) M(u_k, u_i - u_k)
   = sum E_ab (x) E_bc (x) E_ca. Multiplied by (n+1)^3 every factor is integral (u_j - u_i = e_j - e_i), and the check
   is of integer tensors, entry by entry: a tensor of (Q^(n x n))^(x)3 is an array indexed by (a n + b, c n + d,
   e n + f) for E_ab (x) E_cd (x) E_ef, the sum of R terms computed as matrix products in int64 (entries far below
   2^63).
3. The test's conditions, for every n from 2 to 12: the decomposition has n^3 - n + 1 terms (the identity and one for
   each of the (n+1) n (n-1) distinct ordered triples), none of them zero; and (n+1)^3 times its sum equals (n+1)^3
   times T_n in all n^6 entries. test_passed is 1 if they hold for every n.
4. Beside the test, none of it counted: the proof's identities, exactly (sum of the w_i zero; n/(n+1) sum |w_i><w_i| =
   id; <w_i, w_j> = -1/n, 1 on the diagonal); the proof's first term, (n/(n+1))^3 sum over all i, j, k of |w_i><w_j|
   (x) |w_j><w_k| (x) |w_k><w_i|, against T_n, exactly; the saving over the standard n^3 products; and the same
   decomposition built in an orthonormal basis of V (Gram-Schmidt on f_1..f_n, floating point) for n = 2 to 6, its
   largest residual against T_n.

Controls (controls_passed counts those that behave as stated): Strassen's 1969 seven products, written here from his
formulas (c_11 = m1 + m4 - m5 + m7 and so on), read as a decomposition of the trace form with each c_ij's coefficients
in the third factor's entry (j, i), equal T_2, and with the third factors untransposed they do not; the standard n^3
terms equal T_n for n = 3 to 5; three planted faults are caught for n = 3 (one seed-drawn triple with its first bra
reversed, the identity term dropped, and (n/(n+1))^3 read as n/(n+1)); and the matrix products agree with a direct
sum over terms for n = 2 and 3.

What it cannot check: the paper's group-theoretic constructions for n = 3, 4 and 5 (Sections 4.1 to 4.3), of which the
last section says all are instances of this one, and its remarks on the 3-transitive groups.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 mm/gm.py
"""

import hashlib
import io
import json
import os
import re
import sys
import tarfile
from fractions import Fraction

import numpy as np

EPRINT = ("arXiv-1612.01527v2.tar.gz", "e095aab1dd45dad5da49a7b290cb216921329f667b69d07685530cf1a46e6329", 21539)
TEX = "strassen-fourier-continued.tex"
N_RANGE = range(2, 13)
ORTHO_RANGE = range(2, 7)
LATTICE_TEX = (r"\T_n = \id^{\otimes 3} + \left( \frac{n}{n+1} \right)^3 \sum_{\mbox{$i,j,k$ distinct}} "
               r"\ket{w_i}\bra{w_j-w_i} \otimes \ket{w_j}\bra{w_k-w_j} \otimes \ket{w_k}\bra{w_i-w_k} \, .")
STATEMENTS = (
    r"\inner{\T}{A \otimes B \otimes C} = \tr ABC",
    r"\newcommand{\T}{\text{MM}}",
    r"\newcommand{\ket}[1]{| #1 \rangle}",
    r"\newcommand{\bra}[1]{\langle #1 |}",
    r"where $w_1,\ldots,w_{n+1}$ form a frame of unit vectors that point to the corners of a simplex",
    r"$\inner{w_i}{w_j} = -1/n$ if we normalize the $w_i$ to have unit length",
    r"This sum over all $(n+1)n(n-1)=n^3-n$ distinct ordered triples",
    r"\sum_i \ket{w_i} = 0",
    r"\frac{n}{n+1} \sum_i \ket{w_i} \bra{w_i} = \id",
    r"shows that for all $n$ there is a decomposition of $\T_n$ of tensor rank $n^3 - n + 1$",
    r"the same proof works for all $n$, to yield a decomposition with $n^3 - n + 1$ terms",
)
OUTPUTS = ("statements", "equation", "terms", "holds", "entries", "mismatched", "nonzero", "identities", "frame_term",
           "saving", "orthonormal", "conditions_met", "conditions_total", "test_passed", "controls_passed",
           "controls_total")
LIMIT = 200


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


def tex_of(data):
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        try:
            member = tar.getmember(TEX)
        except KeyError:
            raise Refused(f"no {TEX} in the e-print")
        return tar.extractfile(member).read().decode("utf-8")


def flat(text):
    return " ".join(text.split())


def read_equation(tex):
    m = re.search(r"\\begin\{equation\}\s*\\label\{eq:lattice\}(.*?)\\end\{equation\}", tex, re.S)
    if not m:
        raise Refused("no equation labelled eq:lattice")
    return flat(m.group(1))


def statements_found(tex, statements=STATEMENTS):
    text = flat(tex)
    return {s: flat(s) in text for s in statements}


# ---------------------------------------------------------------- the decomposition (rule 2)

def corner(n, i):
    """(n+1) u_i restricted to its first n coordinates: the coordinates of (n+1) u_i in the basis f_a."""
    return [(n + 1) * (1 if a == i else 0) - 1 for a in range(n)]


def covector(n, j, i):
    """<e_j - e_i, f_b> for b = 1..n: the functional <u_j - u_i| on the basis f_b."""
    def coord(v, b):
        return (1 if v == b else 0)
    return [coord(j, b) - coord(i, b) - coord(j, n) + coord(i, n) for b in range(n)]


def factor(n, i, j):
    """(n+1) M(u_i, u_j - u_i), flattened row by row (index a n + b)."""
    u, v = corner(n, i), covector(n, j, i)
    return [u[a] * v[b] for a in range(n) for b in range(n)]


def identity_factor(n):
    return [(n + 1) * (1 if a == b else 0) for a in range(n) for b in range(n)]


def lattice_terms(n, bra_flip=None, drop_identity=False, scale=None):
    """The terms of eq:lattice, each (X, Y, Z) scaled by (n + 1) per factor. Faults for the controls: bra_flip, a
    triple whose first bra is reversed; drop_identity; scale, a factor multiplying every triple's term."""
    terms = [] if drop_identity else [(identity_factor(n),) * 3]
    for i in range(n + 1):
        for j in range(n + 1):
            for k in range(n + 1):
                if len({i, j, k}) < 3:
                    continue
                x = factor(n, i, j)
                if (i, j, k) == bra_flip:
                    x = [-t for t in x]                 # |w_i><w_i - w_j| for |w_i><w_j - w_i|
                y, z = factor(n, j, k), factor(n, k, i)
                if scale is not None:
                    x = [scale * t for t in x]
                terms.append((x, y, z))
    return terms


def target(n, mult):
    """mult times T_n as a dense int64 array of shape (n^2, n^2, n^2)."""
    t = np.zeros((n * n, n * n, n * n), dtype=np.int64)
    for a in range(n):
        for b in range(n):
            for c in range(n):
                t[a * n + b, b * n + c, c * n + a] = mult
    return t


def tensor_sum(terms, n):
    """sum of X (x) Y (x) Z over the terms, by matrix products, as int64 of shape (n^2, n^2, n^2)."""
    A = np.array([t[0] for t in terms], dtype=np.int64).T
    B = np.array([t[1] for t in terms], dtype=np.int64).T
    C = np.array([t[2] for t in terms], dtype=np.int64).T
    out = np.empty((n * n, n * n, n * n), dtype=np.int64)
    for y in range(n * n):
        out[:, y, :] = A @ (C * B[y]).T
    return out


def direct_sum(terms, n):
    """The same sum one term at a time (control)."""
    out = np.zeros((n * n, n * n, n * n), dtype=np.int64)
    for x, y, z in terms:
        out += np.einsum("i,j,k->ijk", np.array(x, dtype=np.int64), np.array(y, dtype=np.int64),
                         np.array(z, dtype=np.int64))
    return out


def check_n(n):
    terms = lattice_terms(n)
    mult = (n + 1) ** 3
    s = tensor_sum(terms, n)
    t = target(n, mult)
    bad = int(np.count_nonzero(s != t))
    nonzero = all(any(v != 0 for v in f) for term in terms for f in term)
    return {"n": n, "terms": len(terms), "expected": n ** 3 - n + 1, "entries": int(t.size), "mismatched": bad,
            "nonzero": nonzero,
            "holds": len(terms) == n ** 3 - n + 1 and nonzero and bad == 0}


# ---------------------------------------------------------------- beside (rule 4)

def u_exact(n, i):
    return [Fraction(1 if a == i else 0) - Fraction(1, n + 1) for a in range(n + 1)]


def identities(n):
    us = [u_exact(n, i) for i in range(n + 1)]
    zero = all(sum(u[a] for u in us) == 0 for a in range(n + 1))
    # n/(n+1) sum |w_i><w_i| = sum |u_i><u_i| on V: in the basis f, M(u_i, u_i) summed must be the identity
    frame = True
    for a in range(n):
        for b in range(n):
            val = sum(u[a] * (u[b] - u[n]) for u in us)
            frame &= val == (1 if a == b else 0)
    inner = all(sum(us[i][a] * us[j][a] for a in range(n + 1)) * Fraction(n + 1, n) == (1 if i == j else Fraction(-1, n))
                for i in range(n + 1) for j in range(n + 1))
    return {"sum_zero": zero, "frame": frame, "inner": inner}


def frame_term_holds(n):
    """(n/(n+1))^3 sum over all i, j, k of |w_i><w_j| (x) |w_j><w_k| (x) |w_k><w_i| = T_n, with each factor
    (n+1) M(u_i, u_j) = corner(i) (x) ((n+1) <u_j, f_b>)."""
    def fac(i, j):
        u = corner(n, i)
        # (n+1) <u_j, f_b> = (n+1)((u_j)_b - (u_j)_n) = (n+1)([b=j] - [n=j])
        v = [(n + 1) * ((1 if b == j else 0) - (1 if j == n else 0)) for b in range(n)]
        return [u[a] * v[b] for a in range(n) for b in range(n)]
    terms = [(fac(i, j), fac(j, k), fac(k, i)) for i in range(n + 1) for j in range(n + 1) for k in range(n + 1)]
    s = tensor_sum(terms, n)
    # each factor carries (n+1)^2 against M(u_i, u_j): (n+1)^6 in all, and (n/(n+1))^3 s^6 = 1 for the unit w's
    return int(np.count_nonzero(s != target(n, (n + 1) ** 6))) == 0


def orthonormal_residual(n):
    """The decomposition in an orthonormal basis of V, floating point: its largest residual against T_n."""
    F = np.zeros((n + 1, n))
    for a in range(n):
        F[a, a], F[n, a] = 1.0, -1.0
    Q, _ = np.linalg.qr(F)                       # columns: an orthonormal basis of V
    s = np.sqrt((n + 1) / n)
    W = [s * (np.eye(n + 1)[i] - 1.0 / (n + 1)) for i in range(n + 1)]
    coords = [Q.T @ w for w in W]                # the unit vectors in that basis
    c = (n / (n + 1)) ** 3
    total = np.einsum("ab,cd,ef->abcdef", np.eye(n), np.eye(n), np.eye(n))
    for i in range(n + 1):
        for j in range(n + 1):
            for k in range(n + 1):
                if len({i, j, k}) < 3:
                    continue
                x = np.outer(coords[i], coords[j] - coords[i])
                y = np.outer(coords[j], coords[k] - coords[j])
                z = np.outer(coords[k], coords[i] - coords[k])
                total += c * np.einsum("ab,cd,ef->abcdef", x, y, z)
    want = np.zeros((n, n, n, n, n, n))
    for a in range(n):
        for b in range(n):
            for cc in range(n):
                want[a, b, b, cc, cc, a] = 1.0
    return float(np.max(np.abs(total - want)))


# ---------------------------------------------------------------- controls

def strassen_terms(transpose_c=True):
    """Strassen 1969: m1 = (a11 + a22)(b11 + b22), m2 = (a21 + a22) b11, m3 = a11 (b12 - b22), m4 = a22 (b21 - b11),
    m5 = (a11 + a12) b22, m6 = (a21 - a11)(b11 + b12), m7 = (a12 - a22)(b21 + b22); c11 = m1 + m4 - m5 + m7,
    c12 = m3 + m5, c21 = m2 + m4, c22 = m1 - m2 + m3 + m6. Matrices flattened as (a11, a12, a21, a22)."""
    A = [(1, 0, 0, 1), (0, 0, 1, 1), (1, 0, 0, 0), (0, 0, 0, 1), (1, 1, 0, 0), (-1, 0, 1, 0), (0, 1, 0, -1)]
    B = [(1, 0, 0, 1), (1, 0, 0, 0), (0, 1, 0, -1), (-1, 0, 1, 0), (0, 0, 0, 1), (1, 1, 0, 0), (0, 0, 1, 1)]
    Cc = [(1, 0, 0, 1), (0, 0, 1, -1), (0, 1, 0, 1), (1, 0, 1, 0), (-1, 1, 0, 0), (0, 0, 0, 1), (1, 0, 0, 0)]
    out = []
    for a, b, c in zip(A, B, Cc):
        z = (c[0], c[2], c[1], c[3]) if transpose_c else c     # c_ij's coefficient at the third factor's (j, i)
        out.append((list(a), list(b), list(z)))
    return out


def standard_terms(n):
    def e(a, b):
        return [1 if (p, q) == (a, b) else 0 for p in range(n) for q in range(n)]
    return [(e(a, b), e(b, c), e(c, a)) for a in range(n) for b in range(n) for c in range(n)]


class Stream:
    """Integers from the seed: SHA-256 of seed, label and a counter."""

    def __init__(self, seed, label):
        self.seed, self.label, self.n = seed, label, 0

    def below(self, m):
        self.n += 1
        h = hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
        return int.from_bytes(h[:8], "big") % m


def holds(terms, n, mult):
    return int(np.count_nonzero(tensor_sum(terms, n) != target(n, mult))) == 0


# ---------------------------------------------------------------- the run

def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    tex = tex_of(load(inputs))
    stmts = statements_found(tex)
    equation = read_equation(tex)
    if equation != LATTICE_TEX:
        raise Refused(f"eq:lattice reads {equation!r}")
    if not all(stmts.values()):
        missing = [s for s, ok in stmts.items() if not ok]
        raise Refused(f"statements not found: {missing}")

    rows = [check_n(n) for n in N_RANGE]
    cond = {
        "the decomposition has n^3 - n + 1 terms, none zero, for n = 2 to 12": all(
            r["terms"] == r["expected"] and r["nonzero"] for r in rows),
        "it equals T_n exactly in all n^6 entries for n = 2 to 12": all(r["mismatched"] == 0 for r in rows),
    }
    ident = {n: identities(n) for n in N_RANGE}
    frame = {n: frame_term_holds(n) for n in N_RANGE}
    ortho = {n: orthonormal_residual(n) for n in ORTHO_RANGE}

    ctl = {}
    ctl["Strassen's seven products equal T_2 with the third factors transposed, and not without"] = (
        holds(strassen_terms(True), 2, 1) and not holds(strassen_terms(False), 2, 1))
    ctl["the standard n^3 terms equal T_n for n = 3 to 5"] = all(holds(standard_terms(n), n, 1) for n in (3, 4, 5))
    st = Stream(seed, "gm/fault")
    triples = [(i, j, k) for i in range(4) for j in range(4) for k in range(4) if len({i, j, k}) == 3]
    flip = triples[st.below(len(triples))]
    faults = {
        "a reversed bra": holds(lattice_terms(3, bra_flip=flip), 3, 64),
        "the identity dropped": holds(lattice_terms(3, drop_identity=True), 3, 64),
    }
    # (n/(n+1))^3 read as n/(n+1): every triple's term multiplied by ((n+1)/n)^2, here 16/9; scaled to integers
    scaled = lattice_terms(3, scale=16)
    ident9 = [9 * v for v in identity_factor(3)]
    scaled[0] = (ident9, identity_factor(3), identity_factor(3))
    faults["(n/(n+1))^3 read as n/(n+1)"] = holds(scaled, 3, 9 * 64)
    ctl["three planted faults are caught for n = 3"] = not any(faults.values())
    ctl["the matrix products agree with a direct sum for n = 2 and 3"] = all(
        np.array_equal(tensor_sum(lattice_terms(n), n), direct_sum(lattice_terms(n), n)) for n in (2, 3))

    values = {
        "statements": f"the e-print's statements as transcribed: {sum(stmts.values())} of {len(stmts)}",
        "equation": "equation eq:lattice as printed: found, as transcribed",
        "terms": "terms for n = 2 to 12: " + ", ".join(str(r["terms"]) for r in rows),
        "holds": (f"the decomposition equals T_n exactly for n = 2 to 12: {sum(r['holds'] for r in rows)} of "
                  f"{len(rows)}"
                  + ("" if all(r["holds"] for r in rows) else "; not for n = " + ", ".join(
                      str(r["n"]) for r in rows if not r["holds"]))),
        "entries": sum(r["entries"] for r in rows),
        "mismatched": sum(r["mismatched"] for r in rows),
        "nonzero": f"every term nonzero: {sum(r['nonzero'] for r in rows)} of {len(rows)}",
        "identities": ("the proof's identities (sum zero, the frame, inner products -1/n) hold exactly for "
                       f"{sum(all(v.values()) for v in ident.values())} of {len(ident)}"),
        "frame_term": (f"the proof's first term equals T_n exactly for {sum(frame.values())} of {len(frame)}"),
        "saving": ("products saved against the standard n^3: " + ", ".join(
            str(n ** 3 - r["terms"]) for n, r in zip(N_RANGE, rows)) + "; for n = 2, "
                   + str(rows[0]["terms"]) + " (Strassen's count)"),
        "orthonormal": ("in an orthonormal basis of V, floating point, n = 2 to 6: largest residual "
                        f"{max(ortho.values()):.1e}"),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for key, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")
    detail = {"input": {"name": EPRINT[0], "sha256": EPRINT[1], "bytes": EPRINT[2]}, "statements": stmts,
              "equation": equation, "rows": rows, "conditions": cond, "identities": {str(n): v for n, v in ident.items()},
              "frame_term": {str(n): v for n, v in frame.items()},
              "orthonormal": {str(n): v for n, v in ortho.items()}, "controls": ctl, "faults_held": faults,
              "fault_triple": list(flip)}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"gm: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
