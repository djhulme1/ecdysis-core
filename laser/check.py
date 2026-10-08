#!/usr/bin/env python3
"""The 42-term border rank expression for the Kronecker square of T_skewcw,4, expanded and checked, for an Ecdysis
receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:2e5c68861be8e2e9) is from Conner, Huang and
Landsberg, "Bad and good news for Strassen's laser method: Border rank of the 3x3 permanent and strict
submultiplicativity" (Foundations of Computational Mathematics 23, 2023; arXiv:2009.11391): "Regarding its $q=4$ skew
cousin in $ C^5\\otimes C^5\\otimes C^5$, which could potentially be used to prove $ω\\leq 2.11$, we show the border
rank of its Kronecker square is at most $42$, a remarkable sub-multiplicativity result, as the square of its border
rank is $64$."

Its registered test: refuted if the 42 matrices m_s(t) and the 36 numbers z_0 to z_35 printed in the e-print's section
on T_skewcw,4 squared (zeta = e^(2 pi i/12)), with entry (r, c) of m_s the coefficient of a_r (x) a_c, give a sum of
cubes m_s(t)^(x)3 whose coefficient at some negative power of t exceeds 1e-12 in modulus, or whose t^0 coefficient
differs by more than 1e-12 in some entry from T (Kronecker) T, the tensor whose ((i, i'), (j, j'), (k, k')) entry is
T_ijk T_i'j'k', for T = T_skewcw,4 as the paper defines it.

The paper marks the bound as shown numerically only (largest error 4.4e-15; no exact expression was found), so a pass
reproduces the paper's own evidence and does not prove that an exact decomposition exists; and the clause on the
square of the border rank (the border rank of T is 8) rests on the paper's border apolarity argument, which this does
not touch.

The input is the e-print, checked against its SHA-256 and size; CHLlaser9-22.tex is read from it in memory and
nothing in it is run. Standard library only. Every rule below was fixed before any seed existed; the seed is not used,
as nothing here is random.

1. The tensor. The TeX's display defining T_{skewcw,q} must be, up to white space, the one written in TEX_T below (the
   paper's formula, for q = 2p even); T_skewcw,4 is that with p = 2 and indices 0 to 4, built here as a 5 x 5 x 5
   array of integers, and T (Kronecker) T from it.
2. The numbers. In the section "\\section{$T_{skewcw,4}^{\\boxtimes 2}$}", the line setting zeta = e^{2\\pi i/ 12}
   must be there; zeta is taken exactly as sqrt(3)/2 + i/2, its powers from the exact table of the twelfth roots of
   unity (with sqrt 3 / 2 rounded once, correctly). The z values are the lines "z_{k} &= a + bi" (or "- bi"), each
   k from 0 to 35 exactly once, read as IEEE doubles.
3. The matrices. The section's pmatrix blocks, 42 of them, each 5 rows of 5 entries ("\\\\" between rows, "&" between
   entries); each entry is 0, a product, or \\frac{product}{product}, a product being factors \\zeta, \\zeta^{k}, z_{k},
   z_{k}^{e}, t, t^{e} or 1 separated by spaces, and anything else is refused. An entry is a coefficient (complex) and
   a power of t (numerator's less denominator's).
4. The expansion. The sum over s of m_s(t)^(x)3, a tensor in (C^5 (x) C^5)^(x)3, is computed coefficient by coefficient:
   for each ordered triple of positions ((r1, c1), (r2, c2), (r3, c3)) and each power of t that the 42 matrices give
   it, the sum over s of the products of the three entries. Every power of t at or below 0 is kept; the sums run in a
   fixed order. Then: max_negative is the largest modulus at a negative power; max_zero the largest modulus of the t^0
   coefficient less T (Kronecker) T's entry (over every triple, those with no t^0 term counting their whole target
   entry). Beside them: whether each position has one power of t in all 42 matrices (the paper's "tight" weights),
   and if so the ordered triples whose powers sum below 0 and to 0, and equations, the unordered triples (of the
   C(25 + 2, 3) = 2925) whose powers sum to 0 or less: the paper says this reduces the equations "from 2925 to 692".

test_passed is 1 if max_negative and max_zero are both at most 1e-12; else 0.

5. Controls (each must fail the test; controls_passed counts those that do): z_0 moved by 1e-9; the 42nd matrix left
   out; zeta taken as e^(2 pi i/10) instead.

Writes results/outputs.json and results/detail.json. Run with: python3 laser/check.py
"""

import hashlib
import io
import json
import math
import os
import re
import sys
import tarfile

INPUT = ("arXiv-2009.11391v1.tar.gz", "fd4b7196a3af8d7744b6c99c0edfe11e2dc09b88cf17ad16247a68477d1b6909", 42058)
TEX = "CHLlaser9-22.tex"
SECTION = "\\section{$T_{skewcw,4}^{\\boxtimes 2}$}"
ZETA_LINE = "\\zeta = e^{2\\pi i/ 12}"
TEX_T = ("T_{skewcw,q}=\\sum_{\\xi=1}^p a_0\\ot b_\\xi\\ot c_{\\xi+p} - a_0\\ot b_{\\xi+p}\\ot c_\\xi "
         "- a_{\\xi}\\ot b_0\\ot c_{\\xi+p} + a_{\\xi+p}\\ot b_0\\ot c_{\\xi } "
         "+a_{\\xi}\\ot b_{\\xi+p}\\ot c_{0}- a_{\\xi+p}\\ot b_{\\xi }\\ot c_{0}.")
Z_COUNT, MATRICES, SIZE = 36, 42, 5
TOL = 1e-12
NUDGE = 1e-9


class Refused(Exception):
    """The input is not what the rules say it must be."""


def squash(s):
    return re.sub(r"\s+", "", s)


def load(directory):
    name, sha, size = INPUT
    with open(os.path.join(directory, name), "rb") as f:
        data = f.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha or len(data) != size:
        raise Refused(f"{name}: sha256 {got} and {len(data)} bytes, not {sha} and {size}")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        m = tar.getmember(TEX)
        if not m.isfile():
            raise Refused(f"{TEX} is not a regular file")
        return tar.extractfile(m).read().decode("utf-8")


# ---------------------------------------------------------------- rule 1: the tensor

def skewcw(p):
    """T_skewcw,2p as a (2p+1)^3 array of integers, from the paper's formula."""
    n = 2 * p + 1
    T = [[[0] * n for _ in range(n)] for _ in range(n)]
    for x in range(1, p + 1):
        for (a, b, c), s in (((0, x, x + p), 1), ((0, x + p, x), -1), ((x, 0, x + p), -1), ((x + p, 0, x), 1),
                             ((x, x + p, 0), 1), ((x + p, x, 0), -1)):
            T[a][b][c] += s
    return T


def kron_square_entry(T, p1, p2, p3):
    """((r1, c1), (r2, c2), (r3, c3)) -> T[r1][r2][r3] T[c1][c2][c3]."""
    return T[p1[0]][p2[0]][p3[0]] * T[p1[1]][p2[1]][p3[1]]


# ---------------------------------------------------------------- rules 2 and 3: the numbers and the matrices

def section(tex):
    at = tex.find(SECTION)
    if at < 0:
        raise Refused("no section for T_skewcw,4 squared")
    end = tex.find("\\section", at + len(SECTION))
    return tex[at: end if end > 0 else len(tex)]


Z_LINE = re.compile(r"z_\{(\d+)\}\s*&=\s*(-?\d+\.\d+)\s*([+-])\s*(\d+\.\d+)i")


def z_values(sec):
    found = {}
    for k, re_, sign, im in Z_LINE.findall(sec):
        k = int(k)
        if k in found:
            raise Refused(f"z_{k} twice")
        found[k] = complex(float(re_), float(im) * (1 if sign == "+" else -1))
    if sorted(found) != list(range(Z_COUNT)):
        raise Refused(f"the z values are not z_0 to z_{Z_COUNT - 1}, once each")
    return [found[k] for k in range(Z_COUNT)]


def zeta_powers(order=12):
    """The order-th roots of unity, exactly where they are known: for 12, from sqrt(3)/2 and 1/2; else cos and sin."""
    if order == 12:
        h, s = 0.5, math.sqrt(3) / 2
        return [complex(1, 0), complex(s, h), complex(h, s), complex(0, 1), complex(-h, s), complex(-s, h),
                complex(-1, 0), complex(-s, -h), complex(-h, -s), complex(0, -1), complex(h, -s), complex(s, -h)]
    return [complex(math.cos(2 * math.pi * k / order), math.sin(2 * math.pi * k / order)) for k in range(order)]


FACTOR = re.compile(r"\\zeta(?:\^\{(\d+)\})?|z_\{(\d+)\}(?:\^\{(\d+)\})?|t(?:\^\{(\d+)\})?|1")


def product(text):
    """[(kind, index, power)] for a product of factors separated by spaces; anything else is refused."""
    out, pos, text = [], 0, text.strip()
    while pos < len(text):
        m = FACTOR.match(text, pos)
        if not m or m.end() == pos:
            raise Refused(f"cannot read the factor at {text[pos:pos + 20]!r}")
        if m.group(0) == "1":
            pass
        elif m.group(0).startswith("\\zeta"):
            out.append(("zeta", 0, int(m.group(1) or 1)))
        elif m.group(0).startswith("z_"):
            out.append(("z", int(m.group(2)), int(m.group(3) or 1)))
        else:
            out.append(("t", 0, int(m.group(4) or 1)))
        pos = m.end()
        while pos < len(text) and text[pos] == " ":
            pos += 1
        if pos < len(text) and m.end() == pos:
            raise Refused(f"factors not separated by a space in {text!r}")
    return out


def entry(text):
    """(numerator factors, denominator factors) of one matrix entry, or None for 0."""
    text = text.strip()
    if text == "0":
        return None
    m = re.fullmatch(r"\\frac\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", text)
    if m:
        return product(m.group(1)), product(m.group(2))
    return product(text), []


def matrices(sec):
    """The section's pmatrix blocks as 5 x 5 lists of entries."""
    blocks = re.findall(r"\\begin\{pmatrix\}(.*?)\\end\{pmatrix\}", sec, re.S)
    out = []
    for b in blocks:
        rows = [r for r in b.split("\\\\")]
        rows = [r for r in rows if r.strip()]
        if len(rows) != SIZE:
            raise Refused(f"a matrix with {len(rows)} rows")
        mat = []
        for r in rows:
            cells = r.split("&")
            if len(cells) != SIZE:
                raise Refused(f"a row with {len(cells)} entries")
            mat.append([entry(c) for c in cells])
        out.append(mat)
    if len(out) != MATRICES:
        raise Refused(f"{len(out)} matrices, not {MATRICES}")
    return out


def evaluate(mats, z, zetas):
    """Each matrix as {(r, c): (coefficient, power of t)}, its nonzero entries only."""
    order = len(zetas)
    out = []
    for mat in mats:
        vals = {}
        for r in range(SIZE):
            for c in range(SIZE):
                e = mat[r][c]
                if e is None:
                    continue
                coef, power = complex(1, 0), 0
                for side, sign in ((e[0], 1), (e[1], -1)):
                    for kind, k, n in side:
                        if kind == "zeta":
                            f = zetas[(n % order)]
                        elif kind == "z":
                            if k >= len(z):
                                raise Refused(f"z_{k} is not defined")
                            f = z[k] ** n
                        else:
                            power += sign * n
                            continue
                        coef = coef * f if sign == 1 else coef / f
                vals[(r, c)] = (coef, power)
        out.append(vals)
    return out


# ---------------------------------------------------------------- rule 4: the expansion

def expand(vals, T):
    """Rule 4: the largest residuals at negative powers of t and at t^0, over every ordered triple of positions; and,
    when every position has one power of t (tight weights), the triples counted by the powers they carry."""
    positions = sorted({p for v in vals for p in v})
    powers = {p: {v[p][1] for v in vals if p in v} for p in positions}
    tight = all(len(s) == 1 for s in powers.values())
    max_neg, max_zero = 0.0, 0.0
    cells = [(r, c) for r in range(SIZE) for c in range(SIZE)]
    for p1 in cells:
        for p2 in cells:
            for p3 in cells:
                sums = {}
                for v in vals:
                    if p1 in v and p2 in v and p3 in v:
                        (a, x), (b, y), (c, w) = v[p1], v[p2], v[p3]
                        e = x + y + w
                        if e <= 0:
                            sums[e] = sums.get(e, 0) + a * b * c
                for e, s in sums.items():
                    if e < 0:
                        max_neg = max(max_neg, abs(s))
                max_zero = max(max_zero, abs(sums.get(0, 0) - kron_square_entry(T, p1, p2, p3)))
    out = {"max_negative": max_neg, "max_zero": max_zero, "tight": tight, "positions": len(positions)}
    if tight:
        w = {p: next(iter(s)) for p, s in powers.items()}
        ordered = [w[a] + w[b] + w[c] for a in positions for b in positions for c in positions]
        unordered = [w[a] + w[b] + w[c] for i, a in enumerate(positions) for j, b in enumerate(positions[i:], i)
                     for c in positions[j:]]
        out.update({"weights": sorted(w.values()), "negative_triples": sum(1 for e in ordered if e < 0),
                    "zero_triples": sum(1 for e in ordered if e == 0),
                    "equations": sum(1 for e in unordered if e <= 0), "unordered_triples": len(unordered)})
    return out


def passes(result):
    return result["max_negative"] <= TOL and result["max_zero"] <= TOL


def sci(x):
    """A residual to three significant figures, as a float."""
    return float(f"{x:.3e}")


def run(inputs="inputs", results="results"):
    tex = load(inputs)
    if squash(TEX_T) not in squash(tex):
        raise Refused("the TeX does not define T_skewcw,q as rule 1 says")
    T = skewcw(2)
    sec = section(tex)
    if squash(ZETA_LINE) not in squash(sec):
        raise Refused("the section does not set zeta = e^{2 pi i/12}")
    z = z_values(sec)
    mats = matrices(sec)
    zetas = zeta_powers(12)
    vals = evaluate(mats, z, zetas)
    main = expand(vals, T)
    nonzero = sum(len(v) for v in vals)

    controls = []
    z2 = list(z)
    z2[0] = z2[0] + NUDGE
    controls.append(("z_0 moved by 1e-9", expand(evaluate(mats, z2, zetas), T)))
    controls.append(("the 42nd matrix left out", expand(vals[:-1], T)))
    controls.append(("zeta = e^(2 pi i/10)", expand(evaluate(mats, z, zeta_powers(10)), T)))
    rows = [{"control": name, "fails": not passes(r), "max_negative": r["max_negative"], "max_zero": r["max_zero"]}
            for name, r in controls]

    out = {
        "z_values": len(z), "matrices": len(mats), "entries_nonzero": nonzero,
        "positions": main["positions"], "weights_tight": int(main["tight"]),
        "weight_min": min(main.get("weights", [0])), "weight_max": max(main.get("weights", [0])),
        "tensor_entries": sum(1 for a in T for b in a for c in b if c), "equations": main.get("equations", -1),
        "unordered_triples": main.get("unordered_triples", -1), "negative_triples": main.get("negative_triples", -1),
        "zero_triples": main.get("zero_triples", -1),
        "max_negative": sci(main["max_negative"]), "max_zero": sci(main["max_zero"]),
        "controls_passed": sum(1 for r in rows if r["fails"]), "controls_total": len(rows),
        "test_passed": int(passes(main)),
    }
    detail = {"input": {"name": INPUT[0], "sha256": INPUT[1], "bytes": INPUT[2], "tex": TEX},
              "rules": {"tolerance": TOL, "nudge": NUDGE}, "result": main, "controls": rows}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as f:
        json.dump(detail, f, indent=1, sort_keys=True)
        f.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run()
    except Refused as e:
        sys.exit(f"laser/check.py: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
