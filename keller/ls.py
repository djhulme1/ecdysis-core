#!/usr/bin/env python3
"""Lagarias & Shor (1992): Keller's cube-tiling conjecture is false in dimensions 10 and 12, by explicit
constructions, and so in every dimension from 10 on.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from J. C. Lagarias and P. W. Shor,
"Keller's cube-tiling conjecture is false in high dimensions" (Bull. Amer. Math. Soc. 27(2), 279-283, 1992;
arXiv:math/9210222): "We show that for all $n\\ge 10$ there exists a tiling of $\\Bbb R^n$ by unit $n$-cubes such
that no two $n$-cubes have a complete facet in common."

The test, as registered: see TEST below. numpy, in the pinned scipy-notebook image, no network. The input is the
claim's data of record, the e-print's source (arXiv math/9210222v1, lagarias.tex gzipped), checked against its
SHA-256 and size before anything else runs and read as text. Every rule below was fixed before the paper's tables were
built into any vector.

1. Reading. The TeX is unpacked and its whitespace runs read as single spaces. Table 1 is the one \\tableS block whose
   caption holds "Table 1.": its rows after \\ruleh, split at \\\\ and &, three symbols each, each one of 0, 0', 1, 2,
   3. Table 2 is the block captioned "Table 2.": its header names the columns (S_0, S_0', S_2, S_1, S'_1, S_3, read
   as the symbols 0, 0', 2, 1, 1', 3), and each row after \\ruleh gives each column one 4-digit block or nothing. The
   primed S_2 is the one \\matrix ... \\endmatrix after "Now regard $S_2$ as being": four rows of four symbols. Every
   anchor must be found exactly once (the captions as "{\\smc Table 1.}" and "{\\smc Table 2.}", since the text also
   says "as listed in Table 2."), every cell must read as stated, or the run is refused.
2. The constructions, as the proof of Theorem A gives them. A symbol stands for its set of blocks (0 for S_0, 0' for
   S_0', and so on; 0' and 0 are distinct symbols with the same value 0). For n = 12: every row (m1, m2, m3) of Table 1
   gives every concatenation of a block of S_m1, one of S_m2 and one of S_m3. For n = 10: the rows of
   T~ = S_0 u S_2, S_0's rows as Table 2 prints them and S_2's as the primed matrix prints them (its values must be
   S_2's rows), each row (c1, c2, c3, c4) giving c1, a block of S_c2, a block of S_c3 and c4 ("Apply the block
   substitution construction to the second and third columns only").
3. The test's eight conditions, for n = 12 and n = 10 each. (a) The vectors are 2^n, distinct, in {0, 1, 2, 3}^n.
   (b) They form a clique in G*_n, the paper's graph: every two differ by exactly 2 in some coordinate and differ in
   at least two coordinates. (c) The cubes of side 2 centred at them, with their translates by 4Z^n, cover each of the
   4^n unit cells [j, j + 1]^n (j taken mod 4) exactly once: they tile R^n (a cube centred at m covers the cells with
   j_i = m_i - 1 or m_i, mod 4). (d) No two share a complete facet: no centre m and coordinate i with m + 2e_i
   (mod 4) also a centre. test_passed is 1 if all eight hold. (b) is the Corradi-Szabo criterion the paper states;
   (c) and (d) check the tiling itself.
4. Beside the test, none of it counted, the text's statements: Table 1, its primes ignored, is a clique of size 8 in
   G_3 (some coordinate differing by 2 in every pair), missing in G*_3 exactly the three edges it prints;
   T~ is a clique of size 16 in G_4, missing in G*_4 exactly the four it prints; conditions (i), (ii) and (iii) on the
   blocks, for each construction (each set a clique in G*_4; no vector in two sets; S_0 u S_2, S_0' u S_2, S_1 u S_3
   and, for n = 10, S_1' u S_3 cliques in G_4); S_1 and S_3 are S_0 and S_2 with the first coordinate's labels moved
   0 -> 1 -> 2 -> 3 -> 0, and S_1' is S_0' moved the same way; the automorphism that moves the first coordinate's
   labels 0 -> 1 -> 2 -> 3 -> 0 and the last's 0 -> 3 -> 2 -> 1 -> 0, then exchanges the two, sends S_0 to S_0' and
   fixes S_2; |S_0| = |S_0'| = |S_1| = 12, |S_2| = |S_3| = 4 and a^3 + 3abc + 3acd + c^3 = 2^12 with k = 4, a = b = 12,
   c = d = 4, as the text prints; and the largest face two cubes share has codimension 2 in both tilings
   (K_10 <= 8, K_12 <= 10: two centres whose difference is 2 in exactly two coordinates and 0 elsewhere). Also beside,
   for the step to n + 1 the paper argues by stacking: the translations t != 0 of {0, ..., 3}^n with no centre in
   both the clique and the clique moved by t, each of which stacks the n-dimensional clique into a Szabo-type clique
   in G*_(n+1) (t = 0 never does).

Controls (controls_passed counts those that behave as stated; the run stops if any fails), none of them depending on
whether the claim holds: the lattice tiling {0, 2}^4 covers every cell once, shares 64 facets and is no clique in G*_4;
the lattice tiling {0, 2}^10 with one cube removed leaves 1,024 cells uncovered, and with one cube moved by e_1 covers
some cell twice; and, for each construction, the cover's count equals a direct count per cube on 64 cells drawn by the
seed, the shared facets counted by moving centres equal twice those counted over pairs, and a plain check of 2,000
pairs drawn by the seed finds no non-adjacent pair unless the pair count does.

What it cannot check: the stacking argument for every n above 12, a proof; Corradi and Szabo's 28-clique for G*_5, from
which the paper took S_0, S_0' and S_2 (another paper).

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 keller/ls.py
"""

import gzip
import hashlib
import itertools
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT = ("arXiv-math-9210222v1.gz", "ae6f06337a1c173acc1a3422bd42679f6edfdb67b93e3bdeae67c421760564c6", 7224)

TEST = ("Refuted if, read from the e-print's TeX (Table 1's clique, Table 2's blocks, the primed S_2) and substituted "
        "as Theorem A's proof says (every column of Table 1 for n = 12; the second and third columns of S_0 ∪ S_2 for "
        "n = 10), the vectors are not 2^n distinct points of {0,1,2,3}^n forming a clique in G*_n, whose side-2 cubes "
        "and their 4ℤ^n translates cover every unit cell exactly once with no two sharing a complete facet (no m and "
        "m + 2e_i mod 4 both centres), for n = 10 or 12.")

SYMBOLS = ("0", "0'", "1", "1'", "2", "3")
HEADER = {"S_0": "0", "S_0'": "0'", "S_2": "2", "S_1": "1", "S'_1": "1'", "S_3": "3"}
MISSING_3 = "201--$20'3$, 120--$320'$, 012--$0'32$"
MISSING_4 = "0213--0211, 3132--1132, 2301--2303, 1020--3020"
SIZES = "$k=4$, $a=b=12$, $c=d=4$"
FORMULA = "|\\scr S|=a^3+3abc+3acd+ c^3=2^{3k}"
PRIMED_ANCHOR = "Now regard $S_2$ as being"
SAMPLE = 64
PAIRS = 2000
SEED_RE = re.compile(r"[0-9a-f]{64}")

OUTPUTS = ("reading", "vectors_12", "vectors_10", "nonadjacent_12", "nonadjacent_10", "cover_12", "cover_10",
           "facets_12", "facets_10", "faces", "stacking", "statements", "conditions_met", "conditions_total",
           "test_passed", "controls_passed", "controls_total")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- the input and the reader (rule 1)

def load(directory):
    name, sha, size = INPUT
    path = os.path.join(directory, name)
    with open(path, "rb") as fh:
        data = fh.read()
    if len(data) != size or hashlib.sha256(data).hexdigest() != sha:
        raise Refused(f"{name}: not the data of record")
    return data


def tex_of(data):
    try:
        text = gzip.decompress(data).decode("ascii")
    except (OSError, UnicodeDecodeError) as e:
        raise Refused(f"the e-print does not unpack to ASCII TeX: {e}")
    return " ".join(text.split())


def one(text, anchor):
    n = text.count(anchor)
    if n != 1:
        raise Refused(f"anchor found {n} times: {anchor[:60]!r}")
    return text.index(anchor)


def symbol(cell):
    cell = cell.strip()
    if cell not in SYMBOLS or cell == "1'":
        raise Refused(f"not a symbol of Table 1: {cell!r}")
    return cell


def table_block(text, caption):
    i = one(text, caption)
    start = text.rfind("\\tableS", 0, i)
    end = text.find("\\endtableS", i)
    if start < 0 or end < 0 or text.count("\\tableS", start, end) != 1:
        raise Refused(f"no table around {caption!r}")
    return text[start:end]


def rows_after_rule(block):
    k = block.count("\\ruleh")
    if k != 1:
        raise Refused(f"\\ruleh found {k} times")
    body = block.split("\\ruleh", 1)[1]
    rows = [r.strip() for r in body.split("\\\\")]
    return [r for r in rows if r]


def read_table1(text):
    rows = rows_after_rule(table_block(text, "{\\smc Table 1.}"))
    out = [tuple(symbol(c) for c in r.split("&")) for r in rows]
    if len(out) != 8 or any(len(r) != 3 for r in out):
        raise Refused("Table 1 is not eight rows of three symbols")
    return out


def block_of(cell):
    cell = cell.strip()
    if not re.fullmatch(r"[0-3]{4}", cell):
        raise Refused(f"not a block: {cell!r}")
    return tuple(int(c) for c in cell)


def read_table2(text):
    block = table_block(text, "{\\smc Table 2.}")
    head, _ = block.split("\\ruleh", 1)
    names = re.findall(r"\\tch ?\\cmath\{([^}]*)\}", head)
    if [HEADER.get(n) for n in names] != ["0", "0'", "2", "1", "1'", "3"]:
        raise Refused(f"Table 2's columns are not as read: {names}")
    cols = [HEADER[n] for n in names]
    sets = {c: [] for c in cols}
    for r in rows_after_rule(block):
        cells = r.split("&")
        if len(cells) != 6:
            raise Refused(f"a row of Table 2 without six cells: {r!r}")
        for c, cell in zip(cols, cells):
            if cell.strip():
                sets[c].append(block_of(cell))
    return sets


def read_primed(text):
    i = one(text, PRIMED_ANCHOR)
    a, b = text.find("\\matrix", i), text.find("\\endmatrix", i)
    if a < 0 or b < 0:
        raise Refused("no matrix after the anchor")
    rows = [r.strip() for r in text[a + len("\\matrix"):b].split("\\\\") if r.strip()]
    out = []
    for r in rows:
        cells = [c.strip() for c in r.split("&")]
        if len(cells) != 4 or any(c not in SYMBOLS for c in cells):
            raise Refused(f"a row of the primed S_2 not read: {r!r}")
        out.append(tuple(cells))
    if len(out) != 4:
        raise Refused("the primed S_2 is not four rows")
    return out


def parse_word(word):
    """A printed vertex such as 20'3 as its symbols."""
    out, i = [], 0
    while i < len(word):
        if word[i] not in "0123":
            raise Refused(f"not a vertex: {word!r}")
        if i + 1 < len(word) and word[i + 1] == "'":
            out.append(word[i] + "'")
            i += 2
        else:
            out.append(word[i])
            i += 1
    return tuple(out)


def printed_edges(text, anchor):
    one(text, anchor)
    pairs = []
    for part in anchor.split(","):
        a, b = [w.strip().strip("$") for w in part.split("--")]
        pairs.append((parse_word(a), parse_word(b)))
    return pairs


def value(sym):
    return int(sym[0])


# ---------------------------------------------------------------- the constructions (rule 2)

def substitute(row_parts, blocks):
    """Every concatenation, for a row given as a list of parts: a fixed value (an int) or a set's symbol (a str)."""
    choices = []
    for part in row_parts:
        if isinstance(part, int):
            choices.append([(part,)])
        else:
            choices.append(blocks[part])
    return [tuple(x for piece in combo for x in piece) for combo in itertools.product(*choices)]


def build12(t1, blocks):
    out = []
    for row in t1:
        out.extend(substitute(list(row), blocks))
    return np.array(out, dtype=np.int64)


def build10(blocks, primed):
    rows = [tuple(str(x) for x in b) for b in blocks["0"]] + primed
    out = []
    for c1, c2, c3, c4 in rows:
        out.extend(substitute([value(c1), c2, c3, value(c4)], blocks))
    return np.array(out, dtype=np.int64)


# ---------------------------------------------------------------- the checks (rule 3) and the statements (rule 4)

def codes(V):
    n = V.shape[1]
    w = (4 ** np.arange(n, dtype=np.int64))
    return (V % 4) @ w


def pairs_report(V):
    """Over every pair: how many fail (a) some coordinate differing by 2, how many fail (b) two coordinates
    differing, and the largest dimension of a face two cubes share (when every difference is 0 or 2)."""
    N, n = V.shape
    no_a = no_b = 0
    best_face = -1
    facets = 0
    for i in range(N - 1):
        d = (V[i + 1:] - V[i]) % 4
        has2 = (d == 2).any(axis=1)
        nz = (d != 0).sum(axis=1)
        no_a += int((~has2).sum())
        no_b += int((nz < 2).sum())
        face = ((d == 0) | (d == 2)).all(axis=1)
        if face.any():
            k = (d[face] == 0).sum(axis=1)
            best_face = max(best_face, int(k.max()))
            facets += int((k == n - 1).sum())
    nonadj = 0
    for i in range(N - 1):
        d = (V[i + 1:] - V[i]) % 4
        ok = (d == 2).any(axis=1) & ((d != 0).sum(axis=1) >= 2)
        nonadj += int((~ok).sum())
    return {"pairs": N * (N - 1) // 2, "no_a": no_a, "no_b": no_b, "nonadjacent": nonadj, "best_face": best_face,
            "facet_pairs": facets}


def cover_counts(V):
    """How many cubes cover each of the 4^n unit cells, the cells of a cube centred at m having j_i in {m_i - 1, m_i}."""
    N, n = V.shape
    idx = np.zeros((N, 1), dtype=np.int64)
    for i in range(n):
        ch = np.stack([(V[:, i] - 1) % 4, V[:, i] % 4], axis=1) * (4 ** i)
        idx = (idx[:, :, None] + ch[:, None, :]).reshape(N, -1)
    return np.bincount(idx.ravel(), minlength=4 ** n)


def direct_cover(V, cell):
    """The cubes covering one cell, counted cube by cube."""
    return int(sum(all(((cell[i] - m[i]) % 4) in (0, 3) for i in range(len(cell))) for m in V.tolist()))


def facet_count(V):
    N, n = V.shape
    have = set(codes(V).tolist())
    c = codes(V)
    total = 0
    for i in range(n):
        moved = V.copy()
        moved[:, i] = (moved[:, i] + 2) % 4
        total += sum(1 for x in codes(moved).tolist() if x in have)
    del c
    return total


def check(V, n):
    distinct = len(set(codes(V).tolist())) == len(V)
    in_range = bool(((V >= 0) & (V <= 3)).all()) and V.shape[1] == n
    pr = pairs_report(V)
    cov = cover_counts(V)
    once, twice, never = int((cov == 1).sum()), int((cov >= 2).sum()), int((cov == 0).sum())
    fac = facet_count(V)
    cond = {f"n = {n}: 2^{n} distinct vectors in {{0,1,2,3}}^{n}": len(V) == 2 ** n and distinct and in_range,
            f"n = {n}: a clique in G*_{n}": pr["nonadjacent"] == 0,
            f"n = {n}: every unit cell covered exactly once": once == 4 ** n,
            f"n = {n}: no two cubes share a complete facet": fac == 0}
    return cond, {"vectors": len(V), "distinct": distinct, "pairs": pr, "cover": {"once": once, "twice_or_more": twice,
                                                                              "never": never}, "facets": fac}


def g_clique(vectors):
    """Whether a list of vectors is a clique in G_n (some coordinate differing by 2 in every pair)."""
    for a, b in itertools.combinations(vectors, 2):
        if not any((x - y) % 4 == 2 for x, y in zip(a, b)):
            return False
    return True


def star_missing(vectors):
    """The pairs of a G_n clique that are not edges of G*_n (differing in only one coordinate)."""
    out = []
    for a, b in itertools.combinations(vectors, 2):
        if sum(1 for x, y in zip(a, b) if x != y) < 2:
            out.append((a, b))
    return out


def star_clique(vectors):
    return g_clique(vectors) and not star_missing(vectors)


def as_values(sym_row):
    return tuple(value(s) for s in sym_row)


def same_pairs(found, printed):
    norm = lambda pairs: sorted(tuple(sorted((tuple(a), tuple(b)))) for a, b in pairs)
    return norm(found) == norm([(as_values(a), as_values(b)) for a, b in printed])


def relabel_first(vectors):
    return [((v[0] + 1) % 4,) + tuple(v[1:]) for v in vectors]


def phi(v):
    first, last = (v[0] + 1) % 4, (v[-1] - 1) % 4
    return (last,) + tuple(v[1:-1]) + (first,)


def statements(text, t1, blocks, primed, V12, V10, r12, r10):
    st = {}
    plain1 = [as_values(r) for r in t1]
    st["Table 1, primes ignored, is a clique of size 8 in G_3"] = len(set(plain1)) == 8 and g_clique(plain1)
    st["it misses in G*_3 exactly the three edges printed"] = same_pairs(star_missing(plain1),
                                                                         printed_edges(text, MISSING_3))
    tt = list(blocks["0"]) + [as_values(r) for r in primed]
    st["T~ = S_0 u S_2 is a clique of size 16 in G_4"] = len(set(tt)) == 16 and g_clique(tt)
    st["it misses in G*_4 exactly the four edges printed"] = same_pairs(star_missing(tt),
                                                                        printed_edges(text, MISSING_4))
    st["the primed S_2 has S_2's rows, primes only in its second and third columns"] = (
        sorted(as_values(r) for r in primed) == sorted(blocks["2"])
        and all("'" not in r[0] and "'" not in r[3] for r in primed))
    for label, names in (("12", ("0", "0'", "1", "2", "3")), ("10", ("0", "0'", "1", "1'", "2", "3"))):
        sets = [blocks[s] for s in names]
        st[f"n = {label}: (i) every block set a clique in G*_4"] = all(star_clique(s) for s in sets)
        allv = [v for s in sets for v in s]
        st[f"n = {label}: (ii) no vector in two sets"] = len(set(allv)) == len(allv)
        unions = [("0", "2"), ("0'", "2"), ("1", "3")] + ([("1'", "3")] if label == "10" else [])
        st[f"n = {label}: (iii) the unions are cliques in G_4"] = all(g_clique(blocks[a] + blocks[b])
                                                                    for a, b in unions)
    st["S_1, S_3 and S_1' are S_0, S_2 and S_0' with the first coordinate moved 0->1->2->3->0"] = (
        sorted(relabel_first(blocks["0"])) == sorted(blocks["1"])
        and sorted(relabel_first(blocks["2"])) == sorted(blocks["3"])
        and sorted(relabel_first(blocks["0'"])) == sorted(blocks["1'"]))
    st["the automorphism sends S_0 to S_0' and fixes S_2"] = (
        sorted(phi(v) for v in blocks["0"]) == sorted(blocks["0'"])
        and sorted(phi(v) for v in blocks["2"]) == sorted(blocks["2"]))
    one(text, SIZES)
    one(text, FORMULA)
    a, b, c, d = len(blocks["0"]), len(blocks["1"]), len(blocks["2"]), len(blocks["3"])
    st["a = b = 12, c = d = 4 and a^3 + 3abc + 3acd + c^3 = 2^12"] = (
        (a, b, c, d) == (12, 12, 4, 4) and len(blocks["0'"]) == 12 and a ** 3 + 3 * a * b * c + 3 * a * c * d
        + c ** 3 == 2 ** 12)
    st["the largest shared face has codimension 2 in both (K_12 <= 10, K_10 <= 8)"] = (
        r12["pairs"]["best_face"] == 10 and r10["pairs"]["best_face"] == 8)
    return st


def stacking(V):
    """Translations t != 0 with no centre in both the clique and the clique moved by t (t outside V - V, mod 4)."""
    n = V.shape[1]
    seen = np.zeros(4 ** n, dtype=bool)
    w = 4 ** np.arange(n, dtype=np.int64)
    for v in V:
        seen[((V - v) % 4) @ w] = True
    return int((~seen).sum())


# ---------------------------------------------------------------- controls

def controls(seed, built):
    ctl = {}
    lat = np.array(list(itertools.product((0, 2), repeat=4)), dtype=np.int64)
    cov = cover_counts(lat)
    ctl["the lattice tiling {0,2}^4: every cell once, 64 shared facets, no clique in G*_4"] = (
        int((cov == 1).sum()) == 4 ** 4 and facet_count(lat) == 64 and pairs_report(lat)["nonadjacent"] > 0)
    lat10 = np.array(list(itertools.product((0, 2), repeat=10)), dtype=np.int64)
    ok10 = int((cover_counts(lat10) == 1).sum()) == 4 ** 10
    moved = lat10.copy()
    moved[0, 0] = (moved[0, 0] + 1) % 4
    ctl["{0,2}^10: one cube removed leaves 1,024 cells uncovered; one moved by e_1 covers a cell twice"] = (
        ok10 and int((cover_counts(lat10[1:]) == 0).sum()) == 1024 and int((cover_counts(moved) >= 2).sum()) > 0)
    rng = np.random.default_rng(int(seed[:16], 16))
    cover_ok = facets_ok = pairs_ok = True
    for V, report in built:
        n = V.shape[1]
        cov = cover_counts(V)
        cells = rng.integers(0, 4, size=(SAMPLE, n))
        w = 4 ** np.arange(n, dtype=np.int64)
        cover_ok &= all(int(cov[int(c @ w)]) == direct_cover(V, c.tolist()) for c in cells)
        facets_ok &= facet_count(V) == 2 * report["pairs"]["facet_pairs"]
        idx = rng.integers(0, len(V), size=(PAIRS, 2))
        plain = 0
        for a, b in idx.tolist():
            if a == b:
                continue
            u, v = V[a].tolist(), V[b].tolist()
            adjacent = any((x - y) % 4 == 2 for x, y in zip(u, v)) and sum(1 for x, y in zip(u, v) if x != y) >= 2
            plain += 0 if adjacent else 1
        pairs_ok &= plain == 0 or report["pairs"]["nonadjacent"] > 0
    ctl["each construction: the cover's count equals a direct count on 64 cells drawn by the seed"] = bool(cover_ok)
    ctl["each construction: facets counted by moving centres are twice those counted over pairs"] = bool(facets_ok)
    ctl["each construction: a plain check of 2,000 drawn pairs finds none non-adjacent unless the count does"] = bool(
        pairs_ok)
    return ctl


def run(seed, inputs="inputs", results="results", log=sys.stderr):
    if not SEED_RE.fullmatch(seed or ""):
        raise Refused("the seed must be 64 hex characters")
    data = load(inputs)
    text = tex_of(data)
    t1 = read_table1(text)
    blocks = read_table2(text)
    primed = read_primed(text)
    reading = (f"Table 1: {len(t1)} rows; Table 2: " + ", ".join(f"S_{k} {len(v)}" for k, v in blocks.items())
               + f"; the primed S_2: {len(primed)} rows")
    print(reading, file=log)

    V12, V10 = build12(t1, blocks), build10(blocks, primed)
    cond12, r12 = check(V12, 12)
    cond10, r10 = check(V10, 10)
    cond = {**cond12, **cond10}
    print(f"n = 12: {r12['vectors']} vectors, nonadjacent {r12['pairs']['nonadjacent']}, cover {r12['cover']}, "
          f"facets {r12['facets']}", file=log)
    print(f"n = 10: {r10['vectors']} vectors, nonadjacent {r10['pairs']['nonadjacent']}, cover {r10['cover']}, "
          f"facets {r10['facets']}", file=log)

    ctl = controls(seed, [(V12, r12), (V10, r10)])
    print(f"controls: {sum(ctl.values())} of {len(ctl)}", file=log)
    if not all(ctl.values()):
        raise AssertionError(f"a control failed: {[c for c, ok in ctl.items() if not ok]}")

    st = statements(text, t1, blocks, primed, V12, V10, r12, r10)
    s11, s13 = stacking(V10), stacking(V12)

    def cov_words(r, n):
        c = r["cover"]
        return f"of {4 ** n:,} cells: once {c['once']:,}, more {c['twice_or_more']:,}, never {c['never']:,}"
    values = {
        "reading": reading,
        "vectors_12": r12["vectors"],
        "vectors_10": r10["vectors"],
        "nonadjacent_12": r12["pairs"]["nonadjacent"],
        "nonadjacent_10": r10["pairs"]["nonadjacent"],
        "cover_12": cov_words(r12, 12),
        "cover_10": cov_words(r10, 10),
        "facets_12": r12["facets"],
        "facets_10": r10["facets"],
        "faces": (f"largest shared face: {r12['pairs']['best_face']} of 12 dimensions, "
                  f"{r10['pairs']['best_face']} of 10"),
        "stacking": f"translations stacking into G*_11: {s11:,} of {4 ** 10 - 1:,}; into G*_13: {s13:,} of {4 ** 12 - 1:,}",
        "statements": f"{sum(st.values())} of {len(st)} of the text's statements hold",
        "conditions_met": sum(cond.values()),
        "conditions_total": len(cond),
        "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()),
        "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > 200:
            raise AssertionError(f"{k}: longer than 200 characters: {v}")
    detail = {"conditions": cond, "controls": ctl, "statements": st, "n12": r12, "n10": r10,
              "stacking": {"into_11": s11, "into_13": s13}, "table1": t1, "table2": blocks, "primed": primed,
              "test": TEST}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="utf-8") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, ensure_ascii=False, default=str)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"ls: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
