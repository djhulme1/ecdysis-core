#!/usr/bin/env python3
"""Ageron et al.'s S- and WS-templates: S(9) >= 17,803, S(10) >= 60,948, WS(6) >= 646, WS(9) >= 22,536, WS(10) >= 71,256.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from Ageron, Casteras, Pellerin, Portella,
Rimmel and Tomasik, "New lower bounds for Schur and weak Schur numbers" (arXiv:2112.03175v2, April 2022), its
abstract: "The new lower bounds include $S(9) \\geq 17\\,803$, $S(10) \\geq 60\\,948$, $\\mathit{WS}(6) \\geq 646$,
$\\mathit{WS}(9) \\geq 22\\,536$ and $\\mathit{WS}(10) \\geq 71\\,256$."

Its registered test is TEST below. S(k) is the largest p such that 1..p splits into k sum-free sets (no a + b = c in a
set, a = b allowed); WS(k) the largest p such that 1..p splits into k weakly sum-free sets (no a + b = c in a set with
a and b distinct).

Every rule below was fixed before any construction of this paper was checked against these bounds. (The paper's Tables
5, 6 and 7 were read and checked against Definition 2.1 earlier, by schur/shifted2026.py, beside another test: there
Table 6 as printed leaves out 49, and it is an S-template with 49 in colour 1 or in colour 4.)

1. Inputs. Four files, each checked against its SHA-256 and size and read in memory as data; nothing in them is run.
   The claim's data of record, the paper as arXiv serves it (a PDF), read by schur/shifted2026.py's PDF reader (its
   rule 3: the pages in the order of the page tree, Flate-decoded content streams, text lines by schur/fs.py's rule).
   Exoo's paper (the data of record of ext:0f23107e990d76ad), read by schur/exoo.py's rules, for its partition of
   1..160 into 5 (the paper cites Heule's S(5) = 160; any sum-free partition of 1..160 into 5 serves Theorem 2.3, and
   Exoo's, the first published, is the one on the record). Fredricksen and Sweet's paper (the data of record of
   ext:5c2324a4ae367bf1, the paper's reference [10] for S(6) >= 536), read by schur/fs.py's rules for its partition of
   1..536 into 6. Rowley's e-print (arXiv:2107.03560v1, the paper's reference [11] for S(7) >= 1696), a gzipped tar
   opened in memory and never unpacked to disk: its ancillary workbook (ROWLEY_MEMBER) is read from memory with xlrd
   (the pinned image's), the sheet named "S(7) >= 1696", whose cell C2 must read "Partition of [1, 1696] into 7
   sum-free subsets"; from its sixth row, column D holds the integers and column E their subsets. The integers must
   be 1..1696 in order and each subset an integer 1..7; columns H and I, the same partition sorted by subset, must
   hold the same 1696 pairs (subset, integer). Anything else refuses the run as a reading error.
2. Tables 5, 6 and 7 (S-templates of widths 33, 111 and 380 with 4, 5 and 6 colours) are read by schur/shifted2026.py's
   rule 3, Table 7 required to partition 1..380 and Tables 5 and 6 taken as printed; the last colour of each is the
   special one (Definition 2.1: it holds the width). An integer a table leaves out is tried in each of its colours, and
   each completion that makes the table an S-template by Definition 2.1 is kept (shifted2026's completions()).
3. Table 8. After the caption "Table 8: b-WS-template with width a and m colors" (it must read b = 23, a = 42, m = 4),
   up to the line that begins "This template provides" or the next "Table" caption: the integers, the commas (the
   comma comes from the math italic font in the position of ";") and the marker "(N + 1)". From these tokens m blocks
   are read in turn: a colour's number (1 to m, in order), its first element, and one more element after each comma;
   an element is an integer or the marker, which must occur exactly once (Proposition 3.20's last number, "in the first
   subset"). The integers are the template, a partition of 1..a + b; its special colour is the set that holds a
   (Definition 3.13), which must be the last (Theorem 3.17 numbers it n + 1). If an integer of 1..a + b is left out,
   repeated or out of range, the table is handled as rule 2 handles Tables 5 and 6, with Definition 3.13 in place of
   Definition 2.1: with exactly one completion it is used, otherwise it is not.
4. Table 9. The caption "Table 9: Weakly sum-free partition of [[1, N]] into k subsets", over at most four text lines
   joined by spaces, must read N = 646 and k = 6. From the tokens after it to the end of the document, k blocks are read
   as in rule 3 (integers only); what follows the k-th block (a page number) is set aside. The sets are taken as
   printed: an integer of 1..646 left out or repeated is reported, and the condition then fails.
5. Theorem 2.3. With an S-template f of width q and n + 1 colours and a base g of 1..p with k colours: h(x) = f(u) when
   f(u) <= n and n + g(alpha) when f(u) = n + 1, for x = (alpha - 1) q + u <= pq; and h(pq + u) = f(u) for
   u = 1..m - 1, m the least element of the special colour. The result covers 1..pq + m - 1 with n + k colours
   (shifted2026's s_template()).
6. Theorem 3.17 and Proposition 3.20. With the b-WS-template f of width a and n + 1 colours (a partition of 1..a + b)
   and a base g of 1..p with k colours, renumbered in the order of the colours' least elements (the proof assumes g
   ordered, so that g(1) = 1): pi(x) = (x mod a) + a when x mod a <= b, else x mod a; lambda(x) = 1 + floor((x - b - 1)
   / a). For x = 1..b, h(x) = f(x); for x = b + 1..pa + b, h(x) = f(pi(x)) when f(pi(x)) <= n and n + g(lambda(x))
   otherwise. Then, by Proposition 3.20 as the paper uses it with Table 8 (one last number, here represented by (N + 1),
   in the first subset), pa + b + 1 takes the colour of the set that holds the marker. The result covers
   1..pa + b + 1 with n + k colours.
7. Sum-free and weakly sum-free. A colouring of 1..N is a partition into K sum-free sets when every integer in 1..N has a
   colour in 1..K and no colour holds a, b and a + b (a = b allowed); into K weakly sum-free sets when every integer has
   a colour and no colour holds a, b and a + b with a < b. For each, two exact tests, written apart, each over the bit
   set of each colour, each returning the first sum it meets in the colour, or none: a compiled scan (numba) and
   Python's integers. The sum-free pair is shifted2026's (for each a in the colour with 2a <= N, the words holding b
   against those holding a + b; and (B >> a) & B). The weak pair is written here: the compiled scan for each a with
   2a < N, the words holding b from a to N - a against those holding a + b, the bit of b = a cleared; and, for each such
   a, ((B >> a) & B) with bit a cleared. A colouring passes when both tests of its pair find none.
8. The test's conditions: (i) some completion of Table 6 gives, by Theorem 2.3 from Exoo's 160 partition, 9 sum-free
   sets covering 1..17,803; (ii) Table 7 gives, by Theorem 2.3 from the same partition, 10 sum-free sets covering
   1..60,948; (iii) Table 9 is a partition of 1..646 into 6 weakly sum-free sets; (iv) Table 8 gives, by rule 6 from
   Fredricksen and Sweet's 536 partition, 9 weakly sum-free sets covering 1..22,536; (v) and from Rowley's 1696
   partition, 10 weakly sum-free sets covering 1..71,256. test_passed is 1 if all five hold.

Beside the test, none of it counted: whether the three cited partitions are sum-free (160 into 5, 536 into 6, 1696
into 7) and symmetric; Definition 2.1 for Tables 5, 6 and 7 and Definition 3.13 for Table 8; Definition 2.8's symmetry
of each S-template (its extension from a one-colour base); Theorem 3.17 alone (1..22,535 and 1..71,255, without the
last number) and the colours in which the last number keeps each partition weakly sum-free; whether Table 9 is also
sum-free (a = b counted); four more entries of the paper's Table 3, S(8) >= 5,286 (Table 5 from 160), S(11) >=
203,828 (Table 7 from 536), S(12) >= 644,628 (Table 7 from 1696) and S(13) >= 2,011,290 (Table 5 from the 60,948 of
condition (ii)); the inequalities (5), (6) and (10) on 100 seeded bases (rule 9); and the margins over the state of the
art in the paper's Tables 1 and 2 (17,694; 60,320; 642; 22,056; 70,778).

9. Seeded bases (beside): base i (i = 0..99) has k = 2 + (i mod 5) colours and is a random greedy colouring: 1, 2, ...
   each go to a colour drawn from the seed uniformly among those that can take it without a sum, until no colour can
   take the next integer. Each gives, if the inequalities hold, k + 4 sum-free sets of 1..111p + 43 (each completion of
   Table 6), k + 5 of 1..380p + 148 (Table 7) and k + 3 weakly sum-free sets of 1..42p + 24 (Table 8 by rule 6).

Controls (controls_passed counts those that behave as stated): (1) both weak tests find a weak sum planted from the
seed in the 71,256 and the 646 partitions (a + b moved into the colour of seed-drawn a < b), and every sum they report
has a < b and its three integers in one colour; (2) both sum-free tests find a sum planted likewise in the 60,948 and
the 160 partitions (a <= b), and every sum they report is genuine; (3) of the colourings of 1..8 with two colours at
least one is weakly sum-free and of 1..9 none (WS(2) = 8), of 1..4 exactly 2 are sum-free and of 1..5 none (S(2) = 4),
and 1, 2 in one colour pass the weak tests and fail the sum-free ones; (4) of 20 seed-drawn moves of one element of
Table 8 (never a) to another colour, every move whose rule-6 construction from the 536 partition (without the last
number) has a weak sum fails Definition 3.13, and at least one has a sum; (5) of 20 seed-drawn moves of one element of
Table 7 to another colour, every move whose construction from the 160 partition has a sum fails Definition 2.1, and at
least one has a sum; (6) the two tests of each pair return the same result for every colour of every colouring both
are run on.

What it cannot check: the SAT searches and the claims of optimality (inequality (10) "cannot be improved", WS(6) >= 646
"cannot give" 647), the backdoor search behind Table 9, that the bounds were new in 2021, and inequality (7) (its
template is not printed).

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 schur/ageron2022.py
"""

import hashlib
import importlib.util
import io
import json
import os
import re
import sys
import tarfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SH = _load("schur_shifted2026", "shifted2026.py")
FS = SH.FS
EX = _load("schur_exoo", "exoo.py")

TEST = ("Refuted if the paper's tables, by its own theorems, do not give: from Exoo's 5 sum-free sets of 1..160, by "
        "Theorem 2.3, 9 sum-free sets of 1..17,803 with Table 6 (width 111; the 49 it omits put where Definition 2.1 "
        "holds) and 10 of 1..60,948 with Table 7 (width 380); 6 weakly sum-free sets of 1..646 in Table 9; by "
        "Theorem 3.17 with Table 8 (23-WS-template, width 42, N + 1 in set 1), 9 weakly sum-free sets of 1..22,536 "
        "from Fredricksen and Sweet's 6 of 1..536 and 10 of 1..71,256 from Rowley's 7 of 1..1696 (weakly: no "
        "a + b = c, a and b distinct, in a set).")

AGERON = SH.AGERON
EXOO_INPUT = EX.INPUT
FS_INPUT = FS.INPUT
ROWLEY = ("arXiv-2107.03560v1.tar.gz", "5d6bf8e28360e4a3bea6c0dbc9c64b5113128c62745667124befab478b957525", 74339)
ROWLEY_MEMBER = "anc/Specimens_S_7____TFTs-4,5,6.xls"
ROWLEY_SHEET = "S(7) >= 1696"
ROWLEY_TITLE = "Partition of [1, 1696] into 7 sum-free subsets"
ROWLEY_N, ROWLEY_K = 1696, 7
WS_TABLE = (8, 23, 42, 4)
WS6 = (9, 646, 6)
CLAIMED = {"s9": 17803, "s10": 60948, "ws6": 646, "ws9": 22536, "ws10": 71256}
TABLE3 = {"s8": 5286, "s11": 203828, "s12": 644628, "s13": 2011290}
PREVIOUS = {"s9": 17694, "s10": 60320, "ws6": 642, "ws9": 22056, "ws10": 70778}
BASES = 100
MOVES = 20
OUTPUTS = ("tables", "bases_read", "s9", "s9_passing", "s10", "s10_sums", "ws6", "ws6_sums", "ws9", "ws9_sums",
           "ws10", "ws10_sums", "premises", "definitions", "symmetry", "theorem_alone", "last_number", "ws6_strong",
           "table3", "seeded", "margins", "moves", "conditions_met", "conditions_total", "test_passed",
           "controls_passed", "controls_total")
LIMIT = 200

Refused = SH.Refused
REFUSALS = (SH.Refused, FS.Refused, EX.Refused, EX.FS.Refused)


# ---------------------------------------------------------------- inputs

def read_input(inputs, spec):
    return SH.read_input(inputs, spec)


def exoo_partition(data):
    return EX.expand(EX.read_partition(EX.document_lines(data)))


def fs_partition(data):
    return FS.expand(FS.read_partition(FS.document_lines(data), 536, 6), 536)


def rowley_workbook(data):
    """The ancillary workbook's bytes, from the e-print in memory: the tar is never unpacked."""
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
            member = tf.getmember(ROWLEY_MEMBER)
            if not member.isfile():
                raise Refused(f"{ROWLEY_MEMBER} is not a file in the e-print")
            return tf.extractfile(member).read()
    except (tarfile.TarError, KeyError, OSError) as e:
        raise Refused(f"the e-print: {e}")


def rowley_cells(rows):
    """Rule 1 on the sheet's rows (lists of cell values, numbers as floats): the 7 sets of 1..1696."""
    def integer(v):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v != int(v):
            return None
        return int(v)

    def cell(r, c):
        row = rows[r] if r < len(rows) else []
        return row[c] if c < len(row) else ""

    if cell(1, 2) != ROWLEY_TITLE:
        raise Refused(f"the sheet's title cell reads {str(cell(1, 2))[:60]!r}")
    body = rows[5:]
    if len(body) != ROWLEY_N:
        raise Refused(f"{len(body)} rows after the header, not {ROWLEY_N}")
    pairs, sorted_pairs = [], []
    for i, _ in enumerate(body, 5):
        x, s = integer(cell(i, 3)), integer(cell(i, 4))
        t, y = integer(cell(i, 7)), integer(cell(i, 8))
        if x != i - 4:
            raise Refused(f"row {i + 1}: column D holds {cell(i, 3)!r}, not {i - 4}")
        if s is None or not 1 <= s <= ROWLEY_K:
            raise Refused(f"row {i + 1}: column E holds {cell(i, 4)!r}, not a subset 1..{ROWLEY_K}")
        if t is None or y is None:
            raise Refused(f"row {i + 1}: columns H and I hold {cell(i, 7)!r}, {cell(i, 8)!r}")
        pairs.append((s, x))
        sorted_pairs.append((t, y))
    if sorted(pairs) != sorted(sorted_pairs):
        raise Refused("columns H and I do not hold the partition columns D and E hold")
    sets = [sorted(x for s, x in pairs if s == c) for c in range(1, ROWLEY_K + 1)]
    return sets


def rowley_partition(data):
    import xlrd

    try:
        book = xlrd.open_workbook(file_contents=rowley_workbook(data), on_demand=True)
        sheet = book.sheet_by_name(ROWLEY_SHEET)
        rows = [sheet.row_values(r) for r in range(sheet.nrows)]
    except xlrd.XLRDError as e:
        raise Refused(f"the workbook: {e}")
    return rowley_cells(rows)


# ---------------------------------------------------------------- Tables 8 and 9

CAPTION8 = re.compile(r"Table (\d+): (\d+)-WS-template with width (\d+) and (\d+) colors")
CAPTION9 = re.compile(r"Table (\d+): Weakly sum-free partition of \[\[1 ?[;,] ?(\d+)\]\] into (\d+) subsets")
TOKENS = re.compile(r"\(\s*N\s*\+\s*1\s*\)|\d+|[;,]|\S")
MARK = "N+1"


def tokens_of(text):
    return [MARK if t.startswith("(") and "N" in t else t for t in TOKENS.findall(text)]


def read_blocks(tokens, m, what, marker=False):
    """m blocks: a colour's number (1..m in order), an element, and one more after each comma. Returns the sets, the
    colours that hold the marker, and the tokens after the m-th block."""
    sets, held, i = [], [], 0
    for colour in range(1, m + 1):
        if i >= len(tokens) or tokens[i] != str(colour):
            raise Refused(f"{what}: colour {colour}'s number not where it should be ({tokens[i:i + 3]!r})")
        i += 1
        s = []
        while True:
            if i >= len(tokens):
                raise Refused(f"{what}: colour {colour}: an element expected")
            t = tokens[i]
            if t.isdigit():
                s.append(int(t))
            elif marker and t == MARK:
                held.append(colour)
            else:
                raise Refused(f"{what}: colour {colour}: {t!r} where an element should be")
            i += 1
            if i < len(tokens) and tokens[i] in (";", ","):
                i += 1
                continue
            break
        sets.append(s)
    return sets, held, tokens[i:]


def coverage(sets, n):
    missing, repeated, stray = FS.coverage(sets, n)
    return {"missing": missing, "repeated": repeated, "stray": stray}


def read_ws_template(lines):
    """Rule 3: Table 8 as {"a", "b", "m", "sets", "last", "after", "missing", "repeated", "stray"}."""
    at = [i for i, line in enumerate(lines) if CAPTION8.fullmatch(line)]
    if len(at) != 1:
        raise Refused(f"Table 8: {len(at)} captions found")
    got = tuple(int(x) for x in CAPTION8.fullmatch(lines[at[0]]).groups())
    if got != WS_TABLE:
        raise Refused(f"Table 8's caption reads table, b, a, colours {got}, not {WS_TABLE}")
    _, b, a, m = got
    seg = []
    for line in lines[at[0] + 1:]:
        if line.startswith("Table ") or line.startswith("This template provides"):
            break
        seg.append(line)
    sets, held, after = read_blocks(tokens_of(" ".join(seg)), m, "Table 8", marker=True)
    if len(held) != 1:
        raise Refused(f"Table 8: the marker (N + 1) is in {len(held)} sets, not one")
    return {"a": a, "b": b, "m": m, "sets": [sorted(s) for s in sets], "last": held[0], "after": after,
            **coverage(sets, a + b)}


def read_ws_partition(lines):
    """Rule 4: Table 9 as {"n", "k", "sets", "after", "missing", "repeated", "stray"}."""
    found = []
    for i, line in enumerate(lines):
        if not line.startswith("Table 9:"):
            continue
        for j in range(1, 5):
            cap = CAPTION9.fullmatch(" ".join(lines[i:i + j]))
            if cap:
                found.append((i + j, cap))
                break
    if len(found) != 1:
        raise Refused(f"Table 9: {len(found)} captions found")
    start, cap = found[0]
    got = tuple(int(x) for x in cap.groups())
    if got != WS6:
        raise Refused(f"Table 9's caption reads table, N, subsets {got}, not {WS6}")
    _, n, k = got
    seg = []
    for line in lines[start:]:
        if line.startswith("Table "):
            break
        seg.append(line)
    sets, _, after = read_blocks(tokens_of(" ".join(seg)), k, "Table 9")
    return {"n": n, "k": k, "sets": [sorted(s) for s in sets], "after": after, **coverage(sets, n)}


# ---------------------------------------------------------------- definitions

def pi_of(x, a, b):
    r = x % a
    return r + a if r <= b else r


def definition_313(sets, a, b):
    """The first breach of Definition 3.13 (b-WS-template, width a, the special colour the set holding a), or None."""
    col = [0] * (a + b + 1)
    for i, s in enumerate(sets, 1):
        for x in s:
            if 1 <= x <= a + b:
                col[x] = i
    special = col[a]
    if special == 0:
        return f"{a} has no colour"
    for i, s in enumerate(sets, 1):
        v = sorted(s)
        for k, x in enumerate(v):
            for y in v[k:]:
                z = x + y
                if z <= a + b and col[z] == i:
                    if x != y:
                        return f"colour {i}: {x} + {y} = {z} (not weakly sum-free)"
                    if x > b:
                        return f"colour {i}: {x} + {x} = {z} above {b} (not sum-free there)"
                if i == special:
                    if z > b + 2 * a and col[z - 2 * a] == i:
                        return f"special colour {i}: {x} + {y} - {2 * a} = {z - 2 * a}"
                elif z > a + b and col[pi_of(z, a, b)] == i:
                    return f"colour {i}: pi({x} + {y}) = {pi_of(z, a, b)}"
    return None


def ws_completions(t):
    """Rule 3: for a Table 8 that leaves out exactly one integer and repeats none, the colours in which adding it makes
    the table a b-WS-template; None for any other defect."""
    if len(t["missing"]) != 1 or t["repeated"] or t["stray"]:
        return None
    x, fits = t["missing"][0], []
    for c in range(len(t["sets"])):
        sets = [sorted(s + [x]) if i == c else list(s) for i, s in enumerate(t["sets"])]
        if definition_313(sets, t["a"], t["b"]) is None:
            fits.append(c + 1)
    return fits


def ws_usable(t):
    """Table 8's sets as printed or as rule 3 completes them, if the special colour (the set holding a) is the last;
    else None."""
    sets = t["sets"]
    if t["missing"] or t["repeated"] or t["stray"]:
        fits = ws_completions(t)
        if fits is None or len(fits) != 1:
            return None
        sets = [sorted(s + t["missing"]) if i + 1 == fits[0] else list(s) for i, s in enumerate(sets)]
    if t["a"] not in sets[-1]:
        return None
    return sets


def symmetric_template(sets, q):
    """Definition 2.8: the S-template's extension from a one-colour base of 1..1 is symmetric."""
    h = SH.s_template(np.array([0, 1], dtype=np.int32), 1, sets, q)
    n = len(h) - 1
    return all(h[x] == h[n + 1 - x] for x in range(1, n + 1))


def symmetric_partition(sets, n):
    where = {x: i for i, s in enumerate(sets) for x in s}
    return all(where.get(n + 1 - x) == where[x] for x in where if 2 * x != n + 1)


# ---------------------------------------------------------------- constructions

def ordered(g):
    """The base renumbered in the order of its colours' least elements (g(1) = 1)."""
    seen = {}
    for c in g[1:].tolist():
        if c not in seen:
            seen[c] = len(seen) + 1
    out = np.zeros_like(g)
    for c, new in seen.items():
        out[g == c] = new
    out[0] = 0
    return out


def ws_template(g, k, sets, a, b, last=None):
    """Rule 6: the colouring h of 1..pa + b (h[0] unused), and with last, pa + b + 1 in colour last."""
    p = len(g) - 1
    n = len(sets) - 1
    g = ordered(g)
    f = np.zeros(a + b + 1, dtype=np.int32)
    for i, s in enumerate(sets, 1):
        f[np.asarray(s, dtype=np.int64)] = i
    top = p * a + b
    h = np.zeros(top + 1 + (0 if last is None else 1), dtype=np.int32)
    x = np.arange(1, top + 1, dtype=np.int64)
    r = x % a
    pi = np.where(r <= b, r + a, r)
    lam = 1 + (x - b - 1) // a
    fp = f[pi]
    hx = np.where(fp <= n, fp, n + g[np.clip(lam, 1, p)])
    t = x <= b
    hx[t] = f[x[t]]
    h[1:top + 1] = hx
    if last is not None:
        h[top + 1] = last
    return h


def greedy_base(seed, i):
    """Rule 9: base i, a random greedy sum-free colouring with k = 2 + (i mod 5) colours."""
    st = FS.Stream(seed, f"ageron/base/{i}")
    k = 2 + i % 5
    classes = [set() for _ in range(k)]
    colour = [0]
    x = 1
    while True:
        ok = [c for c in range(k) if not any((x - y) in classes[c] for y in classes[c])]
        if not ok:
            break
        c = ok[st.below(len(ok))]
        classes[c].add(x)
        colour.append(c + 1)
        x += 1
    return k, np.asarray(colour, dtype=np.int32)


# ---------------------------------------------------------------- the weak tests

_WEAK = None


def weak_scan():
    global _WEAK
    if _WEAK is None:
        from numba import njit

        @njit(cache=False)
        def scan(words, members, n):
            zero = np.uint64(0)
            one = np.uint64(1)
            for t in range(members.shape[0]):
                x = members[t]
                if 2 * x >= n:
                    break
                w = x >> 6
                sh = np.uint64(x & 63)
                co = np.uint64(64) - sh
                lo = x >> 6
                hi = (n - x) >> 6
                for j in range(lo, hi + 1):
                    if sh == zero:
                        m = words[j + w] & words[j]
                    else:
                        m = ((words[j + w] >> sh) | (words[j + w + 1] << co)) & words[j]
                    if j == lo:
                        m &= ~(one << sh)
                    if m != zero:
                        for k in range(64):
                            if (m >> np.uint64(k)) & one:
                                return x, j * 64 + k
            return -1, -1

        _WEAK = scan
    return _WEAK


def first_weak_compiled(h, c):
    n = len(h) - 1
    mem = np.flatnonzero(h == c).astype(np.int64)
    mem = mem[mem >= 1]
    words = np.zeros((n >> 6) + 2, dtype=np.uint64)
    if mem.size:
        np.bitwise_or.at(words, mem >> 6, np.left_shift(np.uint64(1), (mem & 63).astype(np.uint64)))
    a, b = weak_scan()(words, mem, n)
    return None if a < 0 else (int(min(a, b)), int(max(a, b)))


def first_weak_integers(h, c):
    n = len(h) - 1
    mask = h == c
    mask[0] = False
    big = int.from_bytes(np.packbits(mask, bitorder="little").tobytes(), "little")
    for a in np.flatnonzero(mask).tolist():
        if 2 * a >= n:
            break
        v = ((big >> a) & big) & ~(1 << a)
        if v:
            b = (v & -v).bit_length() - 1
            return (min(a, b), max(a, b))
    return None


class Tally:
    """Every colouring each pair of tests ran on, and whether the pair agreed on every colour."""

    def __init__(self):
        self.runs = {"sum-free": 0, "weak": 0}
        self.disagreements = []

    def first(self, h, c, weak):
        if weak:
            one, two = first_weak_compiled(h, c), first_weak_integers(h, c)
        else:
            one, two = SH.first_sum_compiled(h, c), SH.first_sum_integers(h, c)
        if one != two:
            self.disagreements.append({"n": len(h) - 1, "colour": c, "weak": weak, "compiled": one, "integers": two})
        return one, two

    def verdict(self, h, k, weak=False, colours=None):
        n = len(h) - 1
        body = h[1:]
        covered = bool(n >= 1 and np.all((body >= 1) & (body <= k)))
        firsts = {}
        for c in (colours if colours is not None else range(1, k + 1)):
            one, two = self.first(h, c, weak)
            firsts[c] = one if one is not None else two
        self.runs["weak" if weak else "sum-free"] += 1
        sums = {c: s for c, s in firsts.items() if s is not None}
        sizes = [int(np.count_nonzero(h == c)) for c in range(1, k + 1)]
        return {"n": n, "k": k, "weak": weak, "covered": covered, "sums": sums, "free": covered and not sums,
                "sizes": sizes}


def genuine(h, s, c, weak):
    a, b = s
    return 1 <= a and (a < b if weak else a <= b) and a + b < len(h) and h[a] == h[b] == h[a + b] == c


def plant(h, st, colours, weak):
    """a + b moved into the colour of a < b (a <= b for the sum-free tests), drawn from the seed."""
    n = len(h) - 1
    for _ in range(100):
        c = colours[st.below(len(colours))]
        mem = np.flatnonzero(h == c)
        low = mem[(2 * mem < n) if weak else (2 * mem <= n)]
        if not low.size:
            continue
        a = int(low[st.below(low.size)])
        cand = mem[((mem > a) if weak else (mem >= a)) & (mem <= n - a)]
        if not cand.size:
            continue
        b = int(cand[st.below(cand.size)])
        out = h.copy()
        out[a + b] = c
        return out, c, (a, b)
    raise AssertionError("no sum could be planted")


# ---------------------------------------------------------------- the run

def listing(values):
    return ", ".join(str(v) for v in values)


def verdict_text(v, what):
    word = "weakly sum-free" if v["weak"] else "sum-free"
    free = f"{word} by both tests" if not v["sums"] else f"sums in {len(v['sums'])} colours"
    cov = f"each of 1..{v['n']} coloured" if v["covered"] else f"not every one of 1..{v['n']} coloured"
    return f"{what}: {v['k']} sets, {cov}, {free}"


def short(v):
    if v is None:
        return "not built"
    word = "weakly sum-free" if v["weak"] else "sum-free"
    return f"{v['n']} into {v['k']}, " + (word if v["free"] else f"not {word}")


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    lines = SH.pdf_lines(read_input(inputs, AGERON))
    s_tables = SH.read_s_templates(lines)
    t8 = read_ws_template(lines)
    t9 = read_ws_partition(lines)
    b160 = exoo_partition(read_input(inputs, EXOO_INPUT))
    b536 = fs_partition(read_input(inputs, FS_INPUT))
    b1696 = rowley_partition(read_input(inputs, ROWLEY))
    g160, g536, g1696 = SH.colouring(b160, 160), SH.colouring(b536, 536), SH.colouring(b1696, 1696)
    tally = Tally()
    a, b = t8["a"], t8["b"]
    sets8 = ws_usable(t8)

    # the test
    t6 = s_tables[6]
    fits6 = SH.completions(t6) if SH.defective(t6) else None
    if not SH.defective(t6):
        tries6 = [(None, t6["sets"])]
    elif fits6:
        tries6 = [(c, [sorted(s + t6["missing"]) if i + 1 == c else list(s) for i, s in enumerate(t6["sets"])])
                  for c in fits6]
    else:
        tries6 = []
    v9 = [(c, tally.verdict(SH.s_template(g160, 5, sets, t6["q"]), 9)) for c, sets in tries6]
    h10 = SH.s_template(g160, 5, s_tables[7]["sets"], s_tables[7]["q"])
    v10 = tally.verdict(h10, 10)
    g9 = SH.colouring(t9["sets"], t9["n"])
    v6 = tally.verdict(g9, t9["k"], weak=True)
    clean9 = not (t9["missing"] or t9["repeated"] or t9["stray"])
    h22 = ws_template(g536, 6, sets8, a, b, last=t8["last"]) if sets8 is not None else None
    h71 = ws_template(g1696, 7, sets8, a, b, last=t8["last"]) if sets8 is not None else None
    vw9 = tally.verdict(h22, 9, weak=True) if h22 is not None else None
    vw10 = tally.verdict(h71, 10, weak=True) if h71 is not None else None
    cond = {
        "some completion of Table 6 gives 9 sum-free sets covering 1..17,803 from the 160 partition": any(
            v["free"] and v["n"] == CLAIMED["s9"] for _, v in v9),
        "Table 7 gives 10 sum-free sets covering 1..60,948 from the 160 partition": (
            v10["free"] and v10["n"] == CLAIMED["s10"]),
        "Table 9 is a partition of 1..646 into 6 weakly sum-free sets": (
            clean9 and v6["free"] and v6["n"] == CLAIMED["ws6"]),
        "Table 8 gives 9 weakly sum-free sets covering 1..22,536 from the 536 partition": bool(
            vw9 is not None and vw9["free"] and vw9["n"] == CLAIMED["ws9"]),
        "Table 8 gives 10 weakly sum-free sets covering 1..71,256 from the 1696 partition": bool(
            vw10 is not None and vw10["free"] and vw10["n"] == CLAIMED["ws10"]),
    }

    # beside the test
    prem = {name: tally.verdict(g, k) for name, g, k in (("160", g160, 5), ("536", g536, 6), ("1696", g1696, 7))}
    sym_bases = {"160": symmetric_partition(b160, 160), "536": symmetric_partition(b536, 536),
                 "1696": symmetric_partition(b1696, 1696)}
    d21 = {}
    for c, t in s_tables.items():
        if not SH.defective(t):
            br = SH.definition_21(t["sets"], t["q"])
            d21[c] = "an S-template" if br is None else br
        else:
            fits = SH.completions(t)
            d21[c] = (f"leaves out {listing(t['missing'])}" if t["missing"] else f"repeats {listing(t['repeated'])}") + (
                "; no single completion" if fits is None else
                f"; an S-template with it in colour{'s' if len(fits) > 1 else ''} {listing(fits)}" if fits else
                "; no colour makes it an S-template")
    br8 = definition_313(sets8, a, b) if sets8 is not None else "not used"
    sym = {}
    for c, t in s_tables.items():
        if not SH.defective(t):
            sym[c] = "symmetric" if symmetric_template(t["sets"], t["q"]) else "not symmetric"
        else:
            sym[c] = "; ".join(f"with {listing(t['missing'])} in colour {fc}: " + (
                "symmetric" if symmetric_template(sets, t["q"]) else "not symmetric") for fc, sets in tries6) \
                if c == 6 else "defective"
    alone, fits_last = {}, {}
    for name, h, k in (("22,535", h22, 9), ("71,255", h71, 10)):
        if h is None:
            continue
        core = h[:-1]
        alone[name] = tally.verdict(core, k, weak=True)
        fits_last[name] = []
        for c in range(1, k + 1):
            hh = h.copy()
            hh[-1] = c
            if not tally.verdict(hh, k, weak=True, colours=[c])["sums"]:
                fits_last[name].append(c)
    strong9 = tally.verdict(g9, t9["k"])
    doubles = int(sum(1 for x in range(1, t9["n"] // 2 + 1) if g9[x] and g9[x] == g9[2 * x]))
    t3 = {
        "S(8)": tally.verdict(SH.s_template(g160, 5, s_tables[5]["sets"], s_tables[5]["q"]),
                                                      8) if not SH.defective(s_tables[5]) else None,
        "S(11)": tally.verdict(SH.s_template(g536, 6, s_tables[7]["sets"], 380), 11),
        "S(12)": tally.verdict(SH.s_template(g1696, 7, s_tables[7]["sets"], 380), 12),
        "S(13)": tally.verdict(
            SH.s_template(h10, 10, s_tables[5]["sets"], s_tables[5]["q"]), 13) if not SH.defective(s_tables[5])
        else None,
    }
    seeded = {"(5) 111p + 43": 0, "(6) 380p + 148": 0, "(10) 42p + 24": 0}
    seeded_rows, ps = [], []
    for i in range(BASES):
        k, g = greedy_base(seed, i)
        p = len(g) - 1
        ps.append(p)
        ok5 = bool(tries6)
        for _, sets in tries6:
            h5 = SH.s_template(g, k, sets, t6["q"])
            ok5 = tally.verdict(h5, k + 4)["free"] and len(h5) - 1 == 111 * p + 43 and ok5
        h6 = SH.s_template(g, k, s_tables[7]["sets"], 380)
        ok6 = tally.verdict(h6, k + 5)["free"] and len(h6) - 1 == 380 * p + 148
        ok10 = False
        if sets8 is not None:
            hw = ws_template(g, k, sets8, a, b, last=t8["last"])
            ok10 = tally.verdict(hw, k + 3, weak=True)["free"] and len(hw) - 1 == 42 * p + 24
        seeded["(5) 111p + 43"] += int(ok5)
        seeded["(6) 380p + 148"] += int(ok6)
        seeded["(10) 42p + 24"] += int(ok10)
        seeded_rows.append({"i": i, "k": k, "p": p, "5": ok5, "6": ok6, "10": ok10})

    # controls
    ctl, ctl_detail = {}, {}
    st = FS.Stream(seed, "ageron/plant")
    planted = []
    for h, k, weak in ((h71, 10, True), (g9, 6, True), (h10, 10, False), (g160, 5, False)):
        if h is None:
            planted.append({"n": None, "weak": weak, "genuine": False})
            continue
        hp, c, ab = plant(h, st, list(range(1, k + 1)), weak)
        one, two = tally.first(hp, c, weak)
        planted.append({"n": len(h) - 1, "weak": weak, "colour": c, "a_b": ab, "compiled": one, "integers": two,
                        "genuine": bool(one is not None and two is not None and genuine(hp, one, c, weak)
                                        and genuine(hp, two, c, weak))})
    ctl["both weak tests find the sums planted in the 71,256 and 646 partitions, each genuine"] = all(
        x["genuine"] for x in planted[:2])
    ctl["both sum-free tests find the sums planted in the 60,948 and 160 partitions, each genuine"] = all(
        x["genuine"] for x in planted[2:])
    ctl_detail["planted"] = planted
    small = {}
    for n, weak in ((8, True), (9, True), (4, False), (5, False)):
        passed = 0
        for code in range(2 ** n):
            h = np.zeros(n + 1, dtype=np.int32)
            h[1:] = [1 + ((code >> i) & 1) for i in range(n)]
            passed += int(tally.verdict(h, 2, weak=weak)["free"])
        small[f"{n} {'weak' if weak else 'sum-free'}"] = passed
    one12 = np.array([0, 1, 1], dtype=np.int32)
    pair = (tally.verdict(one12, 1, weak=True)["free"], tally.verdict(one12, 1)["free"])
    ctl["WS(2) = 8, S(2) = 4, and 1, 2 together weakly sum-free but not sum-free"] = (
        small["8 weak"] >= 1 and small["9 weak"] == 0 and small["4 sum-free"] == 2 and small["5 sum-free"] == 0
        and pair == (True, False))
    ctl_detail["small"] = {**small, "one colour 1, 2 (weak, sum-free)": pair}
    st = FS.Stream(seed, "ageron/moves8")
    m8, m8_caught, m8_unsound = [], 0, 0
    if sets8 is not None:
        for j in range(MOVES):
            sets = [list(s) for s in sets8]
            src = st.below(len(sets))
            while len([x for x in sets[src] if x != a]) < 1 or len(sets[src]) < 2:
                src = st.below(len(sets))
            choice = [x for x in sets[src] if x != a]
            x = choice[st.below(len(choice))]
            dst = (src + 1 + st.below(len(sets) - 1)) % len(sets)
            sets[src].remove(x)
            sets[dst].append(x)
            sets = [sorted(s) for s in sets]
            vm = tally.verdict(ws_template(g536, 6, sets, a, b), 9, weak=True)
            br = definition_313(sets, a, b)
            caught = not vm["free"]
            m8_caught += int(caught)
            m8_unsound += int(caught and br is None)
            m8.append({"moved": x, "from": src + 1, "to": dst + 1, "caught": caught, "breach": br})
    ctl["every move in Table 8 with a weak sum from the 536 partition fails Definition 3.13; one at least has a sum"] = (
        sets8 is not None and m8_unsound == 0 and m8_caught >= 1)
    ctl_detail["moves8"] = m8
    st = FS.Stream(seed, "ageron/moves7")
    m7, m7_caught, m7_unsound = [], 0, 0
    for j in range(MOVES):
        sets = [list(s) for s in s_tables[7]["sets"]]
        src = st.below(len(sets))
        while len(sets[src]) < 2:
            src = st.below(len(sets))
        x = sets[src][st.below(len(sets[src]))]
        dst = (src + 1 + st.below(len(sets) - 1)) % len(sets)
        sets[src].remove(x)
        sets[dst].append(x)
        sets = [sorted(s) for s in sets]
        vm = tally.verdict(SH.s_template(g160, 5, sets, 380), 10)
        br = SH.definition_21(sets, 380)
        caught = not vm["free"]
        m7_caught += int(caught)
        m7_unsound += int(caught and br is None)
        m7.append({"moved": x, "from": src + 1, "to": dst + 1, "caught": caught, "breach": br})
    ctl["every move in Table 7 with a sum from the 160 partition fails Definition 2.1; one at least has a sum"] = (
        m7_unsound == 0 and m7_caught >= 1)
    ctl_detail["moves7"] = m7
    ctl["the two tests of each pair agree on every colour of every colouring"] = not tally.disagreements
    ctl_detail["disagreements"] = tally.disagreements[:20]
    ctl_detail["colourings_tested"] = tally.runs

    best9 = [v for _, v in v9 if v["free"] and v["n"] == CLAIMED["s9"]]
    values = {
        "tables": ("Tables 5, 6, 7: widths " + listing(t["q"] for t in s_tables.values()) + ", special from "
                   + listing(min(t["sets"][-1]) for t in s_tables.values()) + f"; Table 8: {b}-WS, width {a}, "
                   + f"sizes {' '.join(str(len(s)) for s in t8['sets'])}, N + 1 in {t8['last']}; Table 9: "
                   + f"{t9['k']} sets, sizes {' '.join(str(len(s)) for s in t9['sets'])}"),
        "bases_read": (f"Exoo 160 into 5 ({listing(len(s) for s in b160)}); Fredricksen and Sweet 536 into 6 "
                       f"({listing(len(s) for s in b536)}); Rowley 1696 into 7 ({listing(len(s) for s in b1696)})"),
        "s9": "; ".join((f"Table 6, {listing(t6['missing'])} in colour {c}: " if c is not None else "Table 6: ")
                        + short(v) for c, v in v9) if v9 else "Table 6: no completion",
        "s9_passing": len(best9),
        "s10": verdict_text(v10, "Table 7 from 160"),
        "s10_sums": len(v10["sums"]),
        "ws6": verdict_text(v6, "Table 9") + (
            "" if clean9 else f"; {len(t9['missing'])} left out, {len(t9['repeated'])} repeated, "
                              f"{len(t9['stray'])} out of range"),
        "ws6_sums": len(v6["sums"]),
        "ws9": verdict_text(vw9, "Table 8 from 536") if vw9 is not None else "Table 8 not used",
        "ws9_sums": len(vw9["sums"]) if vw9 is not None else -1,
        "ws10": verdict_text(vw10, "Table 8 from 1696") if vw10 is not None else "Table 8 not used",
        "ws10_sums": len(vw10["sums"]) if vw10 is not None else -1,
        "premises": "; ".join(f"{name} {'sum-free' if v['free'] else 'not sum-free'}"
                              f"{', symmetric' if sym_bases[name] else ', not symmetric'}" for name, v in prem.items()),
        "definitions": "; ".join(f"Table {c}: {d21[c]}" for c in s_tables) + "; Table 8: " + (
            f"a {b}-WS-template" if br8 is None else str(br8)),
        "symmetry": "; ".join(f"Table {c} {sym[c]}" for c in s_tables),
        "theorem_alone": "; ".join(f"1..{name}: {short(v)}" for name, v in alone.items()) or "Table 8 not used",
        "last_number": "; ".join(f"after {name}: colours {listing(c)}" for name, c in fits_last.items())
                       or "Table 8 not used",
        "ws6_strong": f"Table 9 as sum-free: {short(strong9)}; x and 2x in one set for {doubles} x",
        "table3": "; ".join(f"{k}: {short(v)}" for k, v in t3.items()),
        "seeded": (f"{BASES} bases, k 2..6, p {min(ps)}..{max(ps)}: " + ", ".join(f"{k} {n}" for k, n in seeded.items())),
        "margins": ", ".join(f"{k} +{CLAIMED[k] - PREVIOUS[k]}" for k in CLAIMED),
        "moves": (f"Table 8: {m8_caught} of {len(m8)} moves give a weak sum, {m8_unsound} of them pass Definition 3.13; "
                  f"Table 7: {m7_caught} of {MOVES} give a sum, {m7_unsound} pass Definition 2.1"),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for key, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")

    def plain(v):
        return None if v is None else {**v, "sums": {str(c): s for c, s in v["sums"].items()}}

    detail = {"inputs": [list(AGERON), list(EXOO_INPUT), list(FS_INPUT), list(ROWLEY)], "conditions": cond,
              "controls": ctl, "control_detail": ctl_detail,
              "tables": {str(c): {**t, "definition_21": d21[c]} for c, t in s_tables.items()},
              "table8": {**t8, "used": sets8, "definition_313": br8}, "table9": t9,
              "verdicts": {"17803": [{"completion": c, **plain(v)} for c, v in v9], "60948": plain(v10),
                           "646": plain(v6), "22536": plain(vw9), "71256": plain(vw10),
                           "646 as sum-free": plain(strong9),
                           **{f"alone {k}": plain(v) for k, v in alone.items()},
                           **{f"premise {k}": plain(v) for k, v in prem.items()},
                           **{k: plain(v) for k, v in t3.items()}},
              "last_number": fits_last, "symmetry": {**{str(c): s for c, s in sym.items()}, **sym_bases},
              "doubles_in_table9": doubles, "seeded": seeded_rows}
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
    except REFUSALS as e:
        sys.exit(f"ageron2022: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
