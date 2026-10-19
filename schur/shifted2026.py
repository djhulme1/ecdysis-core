#!/usr/bin/env python3
"""Bengone et al.'s shifted S-template: S(k + 2) >= 10 S(k) + 2, and so S(8) >= 5,362 and S(13) >= 2,038,282.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:82570016b4c60524) is from Bengone, Brouk,
Grinsztajn, Helbert, Lugherini, Rimmel and Tomasik, "Shifted S-templates and improved lower bounds for Schur numbers"
(arXiv:2607.15034v1, July 2026; its abstract says the construction "was discovered during a conversation with ChatGPT
5.5 Pro, then refined, verified, and extended"): "Using this added flexibility with the new way to color the special
label cells of the template, we exhibit a template which yields the recurrence $S(k+2) \\geq 10S(k)+2$, improving on
the classical Abbott-Hanson recurrence $S(k+2) \\geq 9S(k)+4$ for the same step. Combined with the known bounds
$S(6) \\geq 536$ and $S(11) \\geq 203\\,828$, this implies $S(8) \\geq 5\\,362$ and $S(13) \\geq 2\\,038\\,282$,
improving the previously listed lower bounds $5\\,286$ and $2\\,011\\,290$."

Its registered test is TEST below. S(k) is the largest p such that 1..p splits into k sum-free sets: no a + b = c in a
set, a = b allowed.

Every rule below was fixed before any construction was checked.

1. Inputs. Three files, each checked against its SHA-256 and size and read in memory as data; nothing in them is run.
   The claim's data of record, the e-print (a gzipped tar holding shifted_s_templates.tex), opened in memory and never
   unpacked to disk. Fredricksen and Sweet's paper, the data of record of ext:5c2324a4ae367bf1, read by schur/fs.py's
   rules for its partitions of 1..536 into 6 and of 1..1680 into 7 (the paper's reference for S(6) >= 536). Ageron,
   Casteras, Pellerin, Portella, Rimmel and Tomasik, "New lower bounds for Schur and weak Schur numbers"
   (arXiv:2112.03175v2, the paper's reference for S(11) >= 203,828), as arXiv serves it: a PDF.
2. The template. In the TeX, the tabular after \\label{cert}: rows split at \\\\, rule commands dropped, cells split at
   &, then $ and spaces removed. The header row numbers the columns 1..q; rows F, M and L carry q labels each and row
   Q the tail's labels, then empty cells. A and B are the ordinary labels (the new colours k + 1 and k + 2); P_d (or
   P_{d}), d an integer, is a shifted label: on row alpha it takes the base colour g(alpha + d). Any other label, or a
   row of another length, refuses the run as a reading error.
3. Ageron et al.'s S-templates. The PDF's pages in the order of its page tree (/Root, /Pages, /Kids), each object
   found at the offset its cross-reference table gives; each page's content streams, Flate-decoded; their text by
   schur/fs.py's rule (the strings of TJ and Tj, a line at each text-positioning operator, a space where the gap after
   a glyph exceeds 0.15 em). After the caption "Table c: S-template with width q and m colors" (c = 5, 6, 7), up to
   the next "Table" caption or the heading "B WS-templates": the integers and the commas (the tables are set in
   mathematics, the comma from the math italic font in the position of ";"). From these tokens m blocks are read in
   turn: a colour's number (1 to m, in order), its first element, and one more element after each comma; what follows
   the m-th block (a page number) is set aside. The m sets must partition 1..q, or the run is refused as a reading
   error. The m-th colour is the special one (Definition 2.1: the condition holds "for all subsets but A_n"), and
   m_{n+1}, its least element, comes from the table.
4. The shifted construction (Sections II and III). A base g colours 1..p with k colours, p >= 3. Row alpha of the main
   block holds x = (alpha - 1) q + u, u = 1..q; its type is F when alpha = 1, L when alpha = p, M otherwise (Delta =
   {-1, 0, 1}, so n = 1). The template's cell (type, u) gives h(x): A gives k + 1, B gives k + 2, P_d gives
   g(alpha + d), and a P_d whose row alpha + d lies outside 1..p leaves x without a colour (an illicit shift,
   Definition 3's condition 3). Then the tail: qp + i takes the colour of the tail's i-th label (a shifted label
   there, which no row backs, leaves it without one). The result covers 1..qp + t.
5. The S-template construction (Ageron et al., Theorem 2.3). With the S-template f of width q and n + 1 colours and a
   base g of 1..p with k colours: h(x) = f(u) when f(u) <= n and n + g(alpha) when f(u) = n + 1, for x = (alpha - 1)
   q + u <= pq; and h(pq + u) = f(u) for u = 1..m_{n+1} - 1. The result covers 1..pq + m_{n+1} - 1 with n + k colours.
6. Sum-free. A colouring of 1..N is a partition into K sum-free sets when every integer in 1..N has a colour in 1..K
   and no colour holds a, b and a + b (a = b allowed). Two exact tests, written apart, each over the bit set of each
   colour: a compiled scan (numba), for each a in the colour with 2a <= N, of the words holding b from a to N - a
   against the words holding a + b; and Python's integers, for each such a, whether (B >> a) & B is non-zero. Each
   returns the first sum it meets in each colour, or none. A colouring passes when both find none.
7. The test's conditions: (i) the template turns the 536 partition into 6 into a partition of 1..5,362 into 8
   sum-free sets; (ii) Table 7's S-template turns the same partition into one of 1..203,828 into 11 (rule 5), and the
   template turns that into a partition of 1..2,038,282 into 13 sum-free sets; (iii) on each of 200 bases drawn from
   the seed, the template gives a partition of 1..10p + 2 into k + 2 sum-free sets. Base i has k = 2 + (i mod 5)
   colours and is a random greedy colouring: 1, 2, ... each go to a colour drawn uniformly from those that can take
   them without a sum, until no colour can take the next integer (p is the last placed, at least 3 for k >= 2).
   test_passed is 1 if all three hold.

Beside the test, none of it counted: whether the two cited partitions are themselves sum-free (536 into 6; 203,828
into 11); the 1680 partition into 7 through the template (16,802 into 9); Tables 5 and 6 through Theorem 2.3 from the
536 partition (33 x 536 + 6 = 17,694 into 9 and 111 x 536 + 43 = 59,539 into 10, two entries of their Table 3);
whether Tables 5, 6 and 7 are S-templates by Definition 2.1 (each colour sum-free and, but the special one, free of
x + y - q for x + y > q); Definition 3's finite check of Table II's template (rule 8); the transitions Lemma 1 calls
realizable, counted at each model size (Lemma 1(c) says they no longer depend on p from p = 3n); and the margins over
5,286 and 2,011,290.

8. Definition 3, with the tail. Over model bases of p = 3..8 rows, for every row pair alpha, beta and column pair u, v
   (epsilon = 1 when u + v > q, w = u + v - epsilon q, gamma = alpha + beta - 1 + epsilon): when gamma <= p, the three
   cells must not carry one ordinary label, and three shifted labels P_a, P_b, P_c need c = a + b + 1 - epsilon; when
   gamma = p + 1 and w <= t, the cell sum lands on the tail's w-th label, and the three must not carry one ordinary
   label; the tail's own sums (qp + i plus v of row F landing on qp + i + v) likewise; and no row may carry a shift
   illicit for its type (F: d >= 0; L: d <= 0).

Controls (controls_passed counts those that behave as stated): (1) both sum-free tests find a sum planted from the seed
in the 2,038,282 and the 536 partitions (a + b moved into the colour of seed-drawn a <= b), and every sum they report
has its three integers in one colour; (2) the two tests return the same result for every colour of every colouring both
are run on; (3) of the 100 single-cell changes of Table II's template (each cell to each other label its row may carry),
every change whose construction from the 536 partition has a sum fails rule 8's check, and at least one has a sum;
(4) of 20 seed-drawn moves of one element of Table 7's template to another colour, every move whose construction from
the 536 partition has a sum fails Definition 2.1, and at least one has a sum; (5) of the 16 colourings of 1..4 with two
colours exactly 2 pass both tests, and of the 32 of 1..5 none does (S(2) = 4).

What it cannot check: Table I's SAT and UNSAT results (no certificates are published), the multiple shifted templates'
copies, that no better bounds than 5,286 and 2,011,290 had been listed elsewhere by July 2026, and the paper's
acknowledged independent work by Ageron.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 schur/shifted2026.py
"""

import hashlib
import importlib.util
import io
import json
import os
import re
import sys
import tarfile
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("schur_fs", os.path.join(HERE, "fs.py"))
FS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(FS)

TEST = ("Refuted if Table II's width-10 template, applied as Section III defines it (row α of a base g of 1..p is F if "
        "α = 1, L if α = p, else M; A and B are new colours, P_d takes g(α + d); tail A, B), does not turn "
        "Fredricksen and Sweet's 6 sum-free sets of 1..536 into 8 covering 1..5,362, or the 11 covering 1..203,828 "
        "that Ageron et al.'s width-380 S-template (their Table 7, Theorem 2.3) builds from them into 13 covering "
        "1..2,038,282; or fails on any of 200 seeded sum-free partitions of 1..p into 2 to 6 sets (no a + b = c in a "
        "set, a = b allowed).")

EPRINT = ("arXiv-2607.15034v1.tar.gz", "0e0eb6d1c0968b93b6a807debd93ded23f56a733746d559f286d8f8139185763", 9137)
TEX = "shifted_s_templates.tex"
FS_INPUT = FS.INPUT
AGERON = ("arXiv-2112.03175v2.pdf", "0bef5716f171992d6b125cfea15551b4e065eecfb243cd7b3e73884cbe5ca703", 533133)
TABLES = {5: (33, 4), 6: (111, 5), 7: (380, 6)}
TYPES = ("F", "M", "L")
LICIT = {"F": (0, 1), "M": (-1, 0, 1), "L": (-1, 0)}
LABELS = (("N", 1), ("N", 2), ("P", -1), ("P", 0), ("P", 1))
NAMES = {("N", 1): "A", ("N", 2): "B", ("P", -1): "P-1", ("P", 0): "P0", ("P", 1): "P1"}
BASES = 200
MOVES = 20
MODEL_SIZES = tuple(range(3, 9))
CLAIMED = {"s8": 5362, "s11": 203828, "s13": 2038282}
PREVIOUS = {8: 5286, 13: 2011290}
STATEMENTS = (
    r"S(k+2)\geq 10\,S(k)+2",
    r"S(8)\geq 10\cdot 536+2=5~362",
    r"S(13)\geq 10\cdot 203~828+2=2~038~282",
    r"improving the previously listed lower bounds $5~286$ and $2~011~290$",
    r"a tail $Q=(A,B)$ is added",
    r"By Theorem~\ref{tail} with $q=10$, $r=2$, $t=2$",
)
OUTPUTS = ("statements", "template", "ageron_tables", "bases_read", "s8", "s8_sums", "s11", "s11_sums", "s13",
           "s13_sums", "bases", "bases_passed", "bases_total", "premises", "s9_from_1680", "ageron_9_10",
           "ageron_definition", "admissible", "transitions", "margins", "mutations", "moves", "conditions_met",
           "conditions_total", "test_passed", "controls_passed", "controls_total")
LIMIT = 200


class Refused(Exception):
    pass


# ---------------------------------------------------------------- inputs

def read_input(inputs, spec):
    name, sha, size = spec
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha or len(data) != size:
        raise Refused(f"{name}: sha256 {got} ({len(data)} bytes), not the registered {sha} ({size})")
    return data


def read_tex(data):
    """The TeX from the e-print, in memory: the tar is never unpacked."""
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
            member = tf.getmember(TEX)
            if not member.isfile():
                raise Refused(f"{TEX} is not a file in the e-print")
            return tf.extractfile(member).read().decode("utf-8")
    except (tarfile.TarError, KeyError, UnicodeDecodeError, OSError) as e:
        raise Refused(f"the e-print: {e}")


def label(cell):
    if cell == "A":
        return ("N", 1)
    if cell == "B":
        return ("N", 2)
    m = re.fullmatch(r"P_(?:\{([+-]?\d+)\}|(\d))", cell)
    if m:
        return ("P", int(m.group(1) if m.group(1) is not None else m.group(2)))
    raise Refused(f"a template cell {cell!r} is not A, B or P_d")


def read_template(tex):
    """Rule 2: rows F, M and L of q labels, the tail, and q."""
    at = tex.find(r"\label{cert}")
    if at < 0:
        raise Refused(r"no \label{cert} in the TeX")
    b = re.compile(r"\\begin\{tabular\}\{[^}]*\}").search(tex, at)
    if not b:
        raise Refused(r"no tabular after \label{cert}")
    e = tex.find(r"\end{tabular}", b.end())
    if e < 0:
        raise Refused("the tabular does not end")
    rows, tail, q = {}, None, None
    for raw in re.split(r"\\\\", tex[b.end():e]):
        raw = re.sub(r"\\(?:toprule|midrule|bottomrule|hline)\b", "", raw)
        cells = [c.replace("$", "").replace(" ", "").strip() for c in raw.split("&")]
        if not any(cells):
            continue
        head, rest = cells[0], cells[1:]
        if head == "":
            if q is not None or rest != [str(i) for i in range(1, len(rest) + 1)]:
                raise Refused(f"a header row {rest!r} that does not number the columns")
            q = len(rest)
        elif head in TYPES:
            if q is None or len(rest) != q or head in rows:
                raise Refused(f"row {head}: {len(rest)} cells, not one row of {q}")
            rows[head] = [label(c) for c in rest]
        elif head == "Q":
            filled = [c for c in rest if c]
            if rest[:len(filled)] != filled or not filled:
                raise Refused(f"the tail row {rest!r} is not its labels then empty cells")
            tail = [label(c) for c in filled]
        else:
            raise Refused(f"an unknown row {head!r}")
    if set(rows) != set(TYPES) or tail is None:
        raise Refused(f"rows read: {sorted(rows)}, tail {'read' if tail else 'missing'}")
    return rows, tail, q


def statements_found(tex):
    flat = " ".join(tex.split())
    return {s: s in flat for s in STATEMENTS}


# ---------------------------------------------------------------- the PDF of Ageron et al.

def xref_offsets(data):
    """Object number -> offset, from the cross-reference table startxref names (and any /Prev), and the trailer."""
    found = list(re.finditer(rb"startxref\s+(\d+)", data))
    if not found:
        raise Refused("the PDF has no startxref")
    pos, offsets, trailer, seen = int(found[-1].group(1)), {}, None, set()
    sub = re.compile(rb"\s*(\d+)[ \t]+(\d+)[ \t]*\r?\n")
    entry = re.compile(rb"(\d{10}) (\d{5}) ([nf])")
    while pos is not None:
        if pos in seen or data[pos:pos + 4] != b"xref":
            raise Refused("no cross-reference table where startxref points (a cross-reference stream is not read)")
        seen.add(pos)
        i = pos + 4
        while True:
            s = sub.match(data, i)
            if not s:
                break
            first, count = int(s.group(1)), int(s.group(2))
            i = s.end()
            for j in range(count):
                e = entry.match(data, i)
                if not e:
                    raise Refused("a malformed cross-reference entry")
                if e.group(3) == b"n":
                    offsets.setdefault(first + j, int(e.group(1)))
                i += 20
        t = re.compile(rb"\s*trailer\s*<<(.*?)>>", re.S).match(data, i)
        if not t:
            raise Refused("no trailer after the cross-reference table")
        if trailer is None:
            trailer = t.group(1)
        prev = re.search(rb"/Prev\s+(\d+)", t.group(1))
        pos = int(prev.group(1)) if prev else None
    return offsets, trailer


def skip_string(data, k):
    """From an opening parenthesis, past its balanced closing one (backslash escapes honoured)."""
    depth = 0
    while k < len(data):
        c = data[k]
        if c == 0x5C:
            k += 2
            continue
        if c == 0x28:
            depth += 1
        elif c == 0x29:
            depth -= 1
            if depth == 0:
                return k + 1
        k += 1
    raise Refused("an unterminated string")


def dictionary(data, i):
    """The dictionary that opens at i (after white space): its inside, and the offset after its closing >>."""
    m = re.compile(rb"\s*<<").match(data, i)
    if not m:
        raise Refused(f"no dictionary at offset {i}")
    start = k = m.end() - 2
    depth = 0
    while k < len(data):
        if data.startswith(b"<<", k):
            depth += 1
            k += 2
        elif data.startswith(b">>", k):
            depth -= 1
            k += 2
            if depth == 0:
                return data[start + 2:k - 2], k
        elif data[k] == 0x28:
            k = skip_string(data, k)
        else:
            k += 1
    raise Refused("an unterminated dictionary")


def object_start(data, offsets, num):
    off = offsets.get(num)
    if off is None:
        raise Refused(f"object {num} is not in the cross-reference table")
    m = re.compile(rb"(\d+)\s+(\d+)\s+obj\b").match(data, off)
    if not m or int(m.group(1)) != num:
        raise Refused(f"object {num}: no 'obj' at the offset the table gives")
    return m.end()


def stream_of(data, offsets, num):
    d, end = dictionary(data, object_start(data, offsets, num))
    m = re.compile(rb"\s*stream\r?\n").match(data, end)
    if not m:
        raise Refused(f"object {num} is not a stream")
    length = re.search(rb"/Length\s+(\d+)(?:\s+(\d+)\s+R)?", d)
    if not length:
        raise Refused(f"object {num}: no /Length")
    if length.group(2) is not None:
        v = re.compile(rb"\s*(\d+)\s").match(data, object_start(data, offsets, int(length.group(1))))
        if not v:
            raise Refused(f"object {num}: its /Length object holds no integer")
        n = int(v.group(1))
    else:
        n = int(length.group(1))
    raw = data[m.end():m.end() + n]
    if not re.compile(rb"\s*endstream").match(data, m.end() + n):
        raise Refused(f"object {num}: the stream does not end at its /Length")
    filt = re.search(rb"/Filter\s*/(\w+)", d)
    if filt is None:
        return raw
    if filt.group(1) != b"FlateDecode":
        raise Refused(f"object {num}: filter {filt.group(1)!r} is not read")
    try:
        return zlib.decompress(raw)
    except zlib.error as e:
        raise Refused(f"object {num}: {e}")


def page_streams(data):
    """Each page's content streams, decoded, in the order of the page tree."""
    offsets, trailer = xref_offsets(data)
    root = re.search(rb"/Root\s+(\d+)\s+0\s+R", trailer)
    if not root:
        raise Refused("the trailer names no /Root")
    cat, _ = dictionary(data, object_start(data, offsets, int(root.group(1))))
    top = re.search(rb"/Pages\s+(\d+)\s+0\s+R", cat)
    if not top:
        raise Refused("the catalogue names no /Pages")
    pages = []

    def walk(num, depth):
        if depth > 32:
            raise Refused("the page tree is too deep")
        d, _ = dictionary(data, object_start(data, offsets, num))
        if re.search(rb"/Type\s*/Pages\b", d):
            kids = re.search(rb"/Kids\s*\[(.*?)\]", d, re.S)
            if not kids:
                raise Refused(f"page-tree node {num} has no /Kids")
            for k in re.findall(rb"(\d+)\s+0\s+R", kids.group(1)):
                walk(int(k), depth + 1)
        elif re.search(rb"/Type\s*/Page\b", d):
            one = re.search(rb"/Contents\s+(\d+)\s+0\s+R", d)
            many = re.search(rb"/Contents\s*\[(.*?)\]", d, re.S)
            refs = [int(one.group(1))] if one else [int(x) for x in re.findall(rb"(\d+)\s+0\s+R", many.group(1))] \
                if many else []
            pages.append([stream_of(data, offsets, r) for r in refs])
        else:
            raise Refused(f"page-tree node {num} is neither /Pages nor /Page")

    walk(int(top.group(1)), 0)
    return pages


def pdf_lines(data):
    out = []
    for streams in page_streams(data):
        for s in streams:
            out.extend(FS.text_lines(s))
    return out


CAPTION = re.compile(r"Table (\d+): S-template with width (\d+) and (\d+) colors")


def read_s_templates(lines, tables=TABLES):
    """Rule 3: {c: {"q", "m", "sets", "after"}} for Tables 5, 6 and 7."""
    out = {}
    for c, (q, m) in tables.items():
        at = [i for i, line in enumerate(lines) if CAPTION.fullmatch(line) and int(CAPTION.fullmatch(line).group(1)) == c]
        if len(at) != 1:
            raise Refused(f"Table {c}: {len(at)} captions found")
        cap = CAPTION.fullmatch(lines[at[0]])
        if (int(cap.group(2)), int(cap.group(3))) != (q, m):
            raise Refused(f"Table {c}: width {cap.group(2)} and {cap.group(3)} colours, not {q} and {m}")
        seg = []
        for line in lines[at[0] + 1:]:
            if line.startswith("Table ") or line == "B WS-templates":
                break
            seg.append(line)
        tokens = re.findall(r"\d+|[;,]|\S", " ".join(seg))
        sets, i = [], 0
        for colour in range(1, m + 1):
            if i >= len(tokens) or tokens[i] != str(colour):
                raise Refused(f"Table {c}: colour {colour}'s number not where it should be ({tokens[i:i + 3]!r})")
            i += 1
            if i >= len(tokens) or not tokens[i].isdigit():
                raise Refused(f"Table {c}: colour {colour} has no first element")
            s = [int(tokens[i])]
            i += 1
            while i < len(tokens) and tokens[i] in (";", ","):
                if i + 1 >= len(tokens) or not tokens[i + 1].isdigit():
                    raise Refused(f"Table {c}: colour {colour}: a comma not followed by an integer")
                s.append(int(tokens[i + 1]))
                i += 2
            sets.append(s)
        listed = [x for s in sets for x in s]
        if sorted(listed) != list(range(1, q + 1)):
            raise Refused(f"Table {c}: the {m} sets are not a partition of 1..{q}: a reading error")
        out[c] = {"q": q, "m": m, "sets": [sorted(s) for s in sets], "after": tokens[i:]}
    return out


# ---------------------------------------------------------------- constructions

def colouring(sets, n):
    g = np.zeros(n + 1, dtype=np.int32)
    for i, s in enumerate(sets, 1):
        g[np.asarray(s, dtype=np.int64)] = i
    return g


def row_types(p):
    alpha = np.arange(1, p + 1)
    return alpha, np.where(alpha == 1, 0, np.where(alpha == p, 2, 1))


def shifted(g, k, rows, tail, q):
    """Rule 4: the colouring h of 1..qp + t (h[0] unused; 0 = no colour)."""
    p = len(g) - 1
    if p < 3:
        raise ValueError("the construction needs p >= 3")
    t = len(tail)
    h = np.zeros(q * p + t + 1, dtype=np.int32)
    gg = np.zeros(p + 2, dtype=np.int32)
    gg[1:p + 1] = g[1:]
    alpha, types = row_types(p)
    for ti, tau in enumerate(TYPES):
        ra = alpha[types == ti]
        for u, (kind, val) in enumerate(rows[tau], 1):
            xs = (ra - 1) * q + u
            if kind == "N":
                h[xs] = k + val
            else:
                idx = ra + val
                ok = (idx >= 1) & (idx <= p)
                h[xs[ok]] = gg[idx[ok]]
    for i, (kind, val) in enumerate(tail, 1):
        h[q * p + i] = k + val if kind == "N" else 0
    return h


def s_template(g, k, sets, q):
    """Rule 5: Theorem 2.3's colouring of 1..pq + m - 1, the last set the special colour."""
    p = len(g) - 1
    n = len(sets) - 1
    f = np.zeros(q + 1, dtype=np.int32)
    for i, s in enumerate(sets, 1):
        f[np.asarray(s, dtype=np.int64)] = i
    m = min(sets[-1])
    h = np.zeros(p * q + m, dtype=np.int32)
    x = np.arange(1, p * q + 1)
    alpha, u = (x - 1) // q + 1, (x - 1) % q + 1
    fu = f[u]
    h[1:p * q + 1] = np.where(fu <= n, fu, n + g[alpha])
    h[p * q + 1:] = f[1:m]
    return h


def definition_21(sets, q):
    """The first breach of Definition 2.1, or None."""
    n = len(sets)
    col = [0] * (q + 1)
    for i, s in enumerate(sets, 1):
        for x in s:
            col[x] = i
    for i, s in enumerate(sets, 1):
        v = sorted(s)
        for a_i, x in enumerate(v):
            for y in v[a_i:]:
                z = x + y
                if z <= q:
                    if col[z] == i:
                        return f"colour {i}: {x} + {y} = {z}"
                elif i < n and col[z - q] == i:
                    return f"colour {i}: {x} + {y} - {q} = {z - q}"
    return None


def row_type(alpha, p):
    return "F" if alpha == 1 else "L" if alpha == p else "M"


def admissible(rows, tail, q, sizes=MODEL_SIZES):
    """Rule 8: the first breach (or None) and the realizable transitions counted at each model size."""
    for tau in TYPES:
        for u, (kind, val) in enumerate(rows[tau], 1):
            if kind == "P" and val not in LICIT[tau]:
                return f"row {tau}, column {u}: P_{val} is illicit", {}
    t = len(tail)
    counts, breach = {}, None
    for p in sizes:
        seen = set()
        for alpha in range(1, p + 1):
            ta = row_type(alpha, p)
            for beta in range(1, p + 1):
                tb = row_type(beta, p)
                for u in range(1, q + 1):
                    x = rows[ta][u - 1]
                    for v in range(1, q + 1):
                        y = rows[tb][v - 1]
                        eps = 1 if u + v > q else 0
                        w = u + v - eps * q
                        gamma = alpha + beta - 1 + eps
                        if gamma <= p:
                            tg = row_type(gamma, p)
                            z = rows[tg][w - 1]
                        elif gamma == p + 1 and w <= t:
                            tg, z = "Q", tail[w - 1]
                        else:
                            continue
                        seen.add((ta, tb, tg, eps))
                        if breach is None:
                            if x[0] == "N" and x == y == z:
                                breach = f"p={p}: rows {ta},{tb}->{tg}, columns {u}+{v}->{w}: one ordinary label"
                            elif x[0] == y[0] == z[0] == "P" and z[1] != x[1] + y[1] + 1 - eps:
                                breach = f"p={p}: rows {ta},{tb}->{tg}, columns {u}+{v}->{w}: shifts {x[1]},{y[1]}->{z[1]}"
        counts[p] = len(seen)
    for i in range(1, t + 1):
        for v in range(1, t - i + 1):
            x, y, z = tail[i - 1], rows["F"][v - 1], tail[i + v - 1]
            if breach is None and x[0] == "N" and x == y == z:
                breach = f"tail {i} + {v} -> tail {i + v}: one ordinary label"
    return breach, counts


def greedy_base(seed, i):
    """Rule 7 (iii): base i, a random greedy sum-free colouring with k = 2 + (i mod 5) colours."""
    st = FS.Stream(seed, f"shifted/base/{i}")
    k = 2 + i % 5
    classes = [set() for _ in range(k)]
    colour = [0]
    x = 1
    while True:
        ok = [c for c in range(k) if not any((x - a) in classes[c] for a in classes[c])]
        if not ok:
            break
        c = ok[st.below(len(ok))]
        classes[c].add(x)
        colour.append(c + 1)
        x += 1
    return k, np.asarray(colour, dtype=np.int32)


# ---------------------------------------------------------------- the two sum-free tests

_SCAN = None


def compiled_scan():
    global _SCAN
    if _SCAN is None:
        from numba import njit

        @njit(cache=False)
        def scan(words, members, n):
            zero = np.uint64(0)
            one = np.uint64(1)
            for t in range(members.shape[0]):
                x = members[t]
                if 2 * x > n:
                    break
                w = x >> 6
                b = np.uint64(x & 63)
                c = np.uint64(64) - b
                lo = x >> 6
                hi = (n - x) >> 6
                acc = zero
                if b == zero:
                    for j in range(lo, hi + 1):
                        acc |= words[j + w] & words[j]
                else:
                    for j in range(lo, hi + 1):
                        acc |= ((words[j + w] >> b) | (words[j + w + 1] << c)) & words[j]
                if acc != zero:
                    for j in range(lo, hi + 1):
                        if b == zero:
                            m = words[j + w] & words[j]
                        else:
                            m = ((words[j + w] >> b) | (words[j + w + 1] << c)) & words[j]
                        if m != zero:
                            for k in range(64):
                                if (m >> np.uint64(k)) & one:
                                    return x, j * 64 + k
            return -1, -1

        _SCAN = scan
    return _SCAN


def members_of(h, c):
    return np.flatnonzero(h == c).astype(np.int64)


def first_sum_compiled(h, c):
    n = len(h) - 1
    mem = members_of(h, c)
    words = np.zeros((n >> 6) + 2, dtype=np.uint64)
    if mem.size:
        np.bitwise_or.at(words, mem >> 6, np.left_shift(np.uint64(1), (mem & 63).astype(np.uint64)))
    a, b = compiled_scan()(words, mem, n)
    return None if a < 0 else (int(min(a, b)), int(max(a, b)))


def first_sum_integers(h, c):
    n = len(h) - 1
    mask = h == c
    big = int.from_bytes(np.packbits(mask, bitorder="little").tobytes(), "little")
    for a in np.flatnonzero(mask).tolist():
        if 2 * a > n:
            break
        v = (big >> a) & big
        if v:
            b = (v & -v).bit_length() - 1
            return (min(a, b), max(a, b))
    return None


class Tally:
    """Every colouring both tests ran on, and whether they agreed on every colour."""

    def __init__(self):
        self.runs, self.disagreements = 0, []

    def record(self, n, c, one, two):
        self.runs += 1
        if one != two:
            self.disagreements.append({"n": n, "colour": c, "compiled": one, "integers": two})

    def verdict(self, h, k, colours=None):
        n = len(h) - 1
        body = h[1:]
        covered = bool(n >= 1 and np.all((body >= 1) & (body <= k)))
        firsts = {}
        for c in (colours if colours is not None else range(1, k + 1)):
            one, two = first_sum_compiled(h, c), first_sum_integers(h, c)
            if one != two:
                self.disagreements.append({"n": n, "colour": c, "compiled": one, "integers": two})
            firsts[c] = one if one is not None else two
        self.runs += 1
        sums = {c: s for c, s in firsts.items() if s is not None}
        sizes = [int(np.count_nonzero(h == c)) for c in range(1, k + 1)]
        return {"n": n, "k": k, "covered": covered, "sums": sums, "sum_free": covered and not sums, "sizes": sizes}


def genuine(h, s, c):
    a, b = s
    return 1 <= a <= b and a + b < len(h) and h[a] == h[b] == h[a + b] == c


# ---------------------------------------------------------------- the run

def plant(h, st, colours):
    """a + b moved into the colour of a <= b, drawn from the seed: the changed colouring and the colour."""
    n = len(h) - 1
    for _ in range(100):
        c = colours[st.below(len(colours))]
        mem = members_of(h, c)
        low = mem[2 * mem <= n]
        if not low.size:
            continue
        a = int(low[st.below(low.size)])
        cand = mem[(mem >= a) & (mem <= n - a)]
        if not cand.size:
            continue
        b = int(cand[st.below(cand.size)])
        out = h.copy()
        out[a + b] = c
        return out, c, (a, b)
    raise AssertionError("no sum could be planted")


def mutations(rows):
    for tau in TYPES:
        for u in range(len(rows[tau])):
            for lab in LABELS:
                if lab == rows[tau][u] or (lab[0] == "P" and lab[1] not in LICIT[tau]):
                    continue
                new = {t: list(r) for t, r in rows.items()}
                new[tau][u] = lab
                yield tau, u + 1, lab, new


def describe(rows, tail):
    return "; ".join(f"{t}: " + " ".join(NAMES[x] for x in rows[t]) for t in TYPES) + "; tail " + " ".join(
        NAMES[x] for x in tail)


def listing(values):
    return ", ".join(str(v) for v in values)


def verdict_text(v, what):
    sf = "sum-free by both tests" if v["sum_free"] else f"sums in {len(v['sums'])} colours"
    cov = f"each of 1..{v['n']} coloured" if v["covered"] else f"not every one of 1..{v['n']} coloured"
    return f"{what}: {v['k']} sets, {cov}, {sf}"


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    tex = read_tex(read_input(inputs, EPRINT))
    rows, tail, q = read_template(tex)
    stmts = statements_found(tex)
    fs_lines = FS.document_lines(read_input(inputs, FS_INPUT))
    b536 = FS.expand(FS.read_partition(fs_lines, 536, 6), 536)
    b1680 = FS.expand(FS.read_partition(fs_lines, 1680, 7), 1680)
    tables = read_s_templates(pdf_lines(read_input(inputs, AGERON)))
    g536, g1680 = colouring(b536, 536), colouring(b1680, 1680)
    tally = Tally()

    # the test
    v536 = tally.verdict(g536, 6)
    h8 = shifted(g536, 6, rows, tail, q)
    v8 = tally.verdict(h8, 8)
    h11 = s_template(g536, 6, tables[7]["sets"], tables[7]["q"])
    v11 = tally.verdict(h11, 11)
    h13 = shifted(h11, 11, rows, tail, q)
    v13 = tally.verdict(h13, 13)
    base_rows, bases_ok, base_sum_free = [], 0, 0
    for i in range(BASES):
        k, g = greedy_base(seed, i)
        p = len(g) - 1
        vb = tally.verdict(g, k)
        base_sum_free += int(vb["sum_free"])
        h = shifted(g, k, rows, tail, q)
        v = tally.verdict(h, k + 2)
        ok = v["sum_free"] and v["n"] == 10 * p + 2
        bases_ok += int(ok)
        base_rows.append({"i": i, "k": k, "p": p, "n": v["n"], "ok": ok, "sums": {str(c): s for c, s in v["sums"].items()}})
    cond = {
        "the 536 partition into 6 gives 8 sum-free sets covering 1..5,362": v8["sum_free"] and v8["n"] == CLAIMED["s8"],
        "Table 7's 11 sets of 1..203,828 give 13 sum-free sets covering 1..2,038,282": (
            v11["n"] == CLAIMED["s11"] and v13["sum_free"] and v13["n"] == CLAIMED["s13"]),
        "each of the 200 seeded bases gives k + 2 sum-free sets covering 1..10p + 2": bases_ok == BASES,
    }

    # beside the test
    v1680 = tally.verdict(g1680, 7)
    v16802 = tally.verdict(shifted(g1680, 7, rows, tail, q), 9)
    v17694 = tally.verdict(s_template(g536, 6, tables[5]["sets"], tables[5]["q"]), 9)
    v59539 = tally.verdict(s_template(g536, 6, tables[6]["sets"], tables[6]["q"]), 10)
    d21 = {c: definition_21(t["sets"], t["q"]) for c, t in tables.items()}
    breach, transitions = admissible(rows, tail, q)

    # controls
    ctl, ctl_detail = {}, {}
    st = FS.Stream(seed, "shifted/plant")
    planted = []
    for h, k in ((h13, 13), (g536, 6)):
        hp, c, ab = plant(h, st, list(range(1, k + 1)))
        one, two = first_sum_compiled(hp, c), first_sum_integers(hp, c)
        tally.record(len(h) - 1, c, one, two)
        planted.append({"n": len(h) - 1, "colour": c, "a_b": ab, "compiled": one, "integers": two,
                        "genuine": bool(one is not None and two is not None and genuine(hp, one, c)
                                        and genuine(hp, two, c))})
    ctl["both tests find the sum planted in the 2,038,282 and the 536 partitions, and each sum is genuine"] = all(
        x["genuine"] for x in planted)
    ctl_detail["planted"] = planted
    mut_rows, mut_caught, mut_admissible, mut_unsound = [], 0, 0, 0
    for tau, u, lab, new in mutations(rows):
        vm = tally.verdict(shifted(g536, 6, new, tail, q), 8)
        br, _ = admissible(new, tail, q)
        caught = not vm["sum_free"]
        mut_caught += int(caught)
        mut_admissible += int(br is None)
        mut_unsound += int(caught and br is None)
        mut_rows.append({"row": tau, "column": u, "label": NAMES[lab], "caught": caught, "breach": br})
    ctl["every single-cell change with a sum from the 536 partition fails Definition 3's check; one at least has a sum"] = (
        mut_unsound == 0 and mut_caught >= 1)
    ctl_detail["mutations"] = mut_rows
    st = FS.Stream(seed, "shifted/moves")
    move_rows, mv_caught, mv_unsound = [], 0, 0
    for j in range(MOVES):
        sets = [list(s) for s in tables[7]["sets"]]
        src = st.below(len(sets))
        while len(sets[src]) < 2:
            src = st.below(len(sets))
        x = sets[src][st.below(len(sets[src]))]
        dst = (src + 1 + st.below(len(sets) - 1)) % len(sets)
        sets[src].remove(x)
        sets[dst].append(x)
        sets = [sorted(s) for s in sets]
        vm = tally.verdict(s_template(g536, 6, sets, tables[7]["q"]), 11)
        br = definition_21(sets, tables[7]["q"])
        caught = not vm["sum_free"]
        mv_caught += int(caught)
        mv_unsound += int(caught and br is None)
        move_rows.append({"moved": x, "from": src + 1, "to": dst + 1, "caught": caught, "breach": br})
    ctl["every move in Table 7 with a sum from the 536 partition fails Definition 2.1; one at least has a sum"] = (
        mv_unsound == 0 and mv_caught >= 1)
    ctl_detail["moves"] = move_rows
    small = {}
    for n in (4, 5):
        passed = 0
        for code in range(2 ** n):
            h = np.zeros(n + 1, dtype=np.int32)
            h[1:] = [1 + ((code >> i) & 1) for i in range(n)]
            passed += int(tally.verdict(h, 2)["sum_free"])
        small[n] = passed
    ctl["of the colourings of 1..4 with two colours exactly 2 pass, of 1..5 none"] = small == {4: 2, 5: 0}
    ctl_detail["small"] = small
    ctl["the two tests agree on every colour of every colouring"] = not tally.disagreements
    ctl_detail["disagreements"] = tally.disagreements[:20]
    ctl_detail["colourings_tested"] = tally.runs

    ps = [r["p"] for r in base_rows]
    values = {
        "statements": f"the recurrence, the two bounds, the margins, the tail and Theorem 2's use in the TeX: "
                      f"{sum(stmts.values())} of {len(stmts)}",
        "template": f"width {q}: " + describe(rows, tail),
        "ageron_tables": ("Tables 5, 6, 7: widths " + listing(t["q"] for t in tables.values()) + "; colours "
                          + listing(t["m"] for t in tables.values()) + "; special colour from "
                          + listing(min(t["sets"][-1]) for t in tables.values()) + "; sizes "
                          + " / ".join(" ".join(str(len(s)) for s in t["sets"]) for t in tables.values())),
        "bases_read": f"Fredricksen and Sweet: 536 into 6, sets of {listing(v536['sizes'])}; 1680 into 7",
        "s8": verdict_text(v8, "from 536") + f"; sizes {listing(v8['sizes'])}",
        "s8_sums": len(v8["sums"]),
        "s11": verdict_text(v11, "Table 7 from 536"),
        "s11_sums": len(v11["sums"]),
        "s13": verdict_text(v13, "from 203,828"),
        "s13_sums": len(v13["sums"]),
        "bases": (f"{BASES} bases, k 2..6, p {min(ps)}..{max(ps)} (median {sorted(ps)[len(ps) // 2]}); "
                  f"{base_sum_free} sum-free as drawn; {bases_ok} give k + 2 sum-free sets of 1..10p + 2"),
        "bases_passed": bases_ok,
        "bases_total": BASES,
        "premises": (f"536 into 6 {'sum-free' if v536['sum_free'] else 'not sum-free'}; 203,828 into 11 "
                     f"{'sum-free' if v11['sum_free'] else 'not sum-free'}"),
        "s9_from_1680": verdict_text(v16802, "from 1680"),
        "ageron_9_10": (f"Table 5 from 536: {v17694['n']} into 9, {'sum-free' if v17694['sum_free'] else 'not'}; "
                        f"Table 6: {v59539['n']} into 10, {'sum-free' if v59539['sum_free'] else 'not'}"),
        "ageron_definition": "; ".join(f"Table {c}: {'an S-template' if d21[c] is None else d21[c]}" for c in tables),
        "admissible": "Definition 3 with the tail, p = 3..8: " + ("admissible" if breach is None else breach),
        "transitions": "realizable transitions by model size: " + ", ".join(f"p={p} {n}" for p, n in transitions.items()),
        "margins": (f"S(8): {v8['n']} - {PREVIOUS[8]} = {v8['n'] - PREVIOUS[8]}; S(13): {v13['n']} - {PREVIOUS[13]} "
                    f"= {v13['n'] - PREVIOUS[13]}"),
        "mutations": (f"{mut_caught} of {len(mut_rows)} single-cell changes give a sum from 536; {mut_admissible} pass "
                      f"Definition 3; {mut_unsound} both"),
        "moves": f"{mv_caught} of {MOVES} moves in Table 7 give a sum from 536; {mv_unsound} of them pass Definition 2.1",
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for key, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")
    detail = {"inputs": [list(EPRINT), list(FS_INPUT), list(AGERON)], "statements": stmts, "conditions": cond,
              "controls": ctl, "control_detail": ctl_detail,
              "template": {"q": q, "rows": {t: [NAMES[x] for x in r] for t, r in rows.items()},
                           "tail": [NAMES[x] for x in tail]},
              "tables": {str(c): {**t, "definition_21": d21[c]} for c, t in tables.items()},
              "verdicts": {name: {**v, "sums": {str(c): s for c, s in v["sums"].items()}} for name, v in
                           (("536", v536), ("5362", v8), ("203828", v11), ("2038282", v13), ("1680", v1680),
                            ("16802", v16802), ("17694", v17694), ("59539", v59539))},
              "bases": base_rows, "admissible": breach, "transitions": transitions}
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
        sys.exit(f"shifted2026: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
