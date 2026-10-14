#!/usr/bin/env python3
"""Fredricksen & Sweet's symmetric sum-free partitions: S(6) >= 536 and S(7) >= 1680, and so R6(3) >= 538 and
R7(3) >= 1682.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:5c2324a4ae367bf1) is from Fredricksen and
Sweet, "Symmetric Sum-Free Partitions and Lower Bounds for Schur Numbers" (The Electronic Journal of Combinatorics 7,
#R32, 2000): "We give new lower bounds for the Schur numbers S(6) and S(7). This will imply new lower bounds for the
Multicolor Ramsey Numbers R_6(3) and R_7(3)."

Its registered test: refuted if the partitions the paper prints of 536 into 6 sets and of 1680 into 7, read as it
states them (the smaller of each symmetric pair i, n + 1 - i listed, its partner in the same set; 179 and 358, which
sum to 537, each listed where it lies), are not partitions of {1, ..., 536} and {1, ..., 1680} into 6 and 7 sum-free
sets (no a + b = c in a set, a = b allowed), so that S(6) >= 536 or S(7) >= 1680 fails; or if the edge colourings of
K537 and K1681 they give (uv coloured by the set holding |u - v|) have a triangle of one colour, so that R6(3) >= 538 or
R7(3) >= 1682 fails.

Standard library only. The input is the claim's data of record, the paper as the journal serves it (a PDF of nine
pages), checked against its SHA-256 and size and read in memory as data; nothing in it is run. Every rule below was
fixed before any check of the partitions was computed.

1. Reading. The page descriptions are the PDF's Flate-compressed content streams, in file order. Text is the strings
   of its TJ and Tj operators; a line ends at each text-positioning operator (Td, TD, T*, Tm); within a line, a space
   stands wherever the gap after a glyph (the character spacing Tc, less a TJ adjustment that follows it, in em) is
   above 0.15 em, as between the printed numbers (about a third of an em) and never within one (zero or less). The page
   headers (the journal's name, its volume, issue and page number) are dropped.
2. The partitions. After the line "Partition of 536 into 6 symmetric sumfree sets:" and after "Partition of 1680 into
   7 symmetric sumfree sets:", lines "Set k: ..." and the lines of numbers that follow, until the next "Set" or the
   line that opens "(D(P) = ...)". Every listed number must be an integer from 1 to n, each listed once, the sets
   numbered 1 to k in order, and the listing must be 1 to (n + 1)/2 once each, with the split pair's upper member
   (step 3);
   the run is refused otherwise, as a reading error.
3. The listing rule (the paper: "The constructions exhibited below are symmetric, and so we only list the smallest of
   a symmetric pair"; "a sum-free partition P of the interval [1, n] is said to be symmetric if all symmetric pairs i
   and (n + 1) - i are in the same set", "except in the case when n + 1 is divisible by 3, we must allow (n + 1)/3 and
   2(n + 1)/3 to be in different sets"): a listed i other than (n + 1)/3 and 2(n + 1)/3 stands for i and n + 1 - i in
   its set; those two, when 3 divides n + 1, stand for themselves. For 536, that is 179 and 358.
4. Sum-free (the paper's sense, after Schur: a, b in the set never have a + b in it, a = b allowed). The test's four
   conditions: the expanded 536 partition is a partition of {1, ..., 536} into 6 sum-free sets; the same for 1680 and
   7; and the colourings of the complete graphs on {0, ..., 536} and {0, ..., 1680}, the edge uv coloured by the set
   holding |u - v|, have no triangle of one colour, found by intersecting each edge's two endpoints' neighbourhoods in
   its colour (bit sets), independently of the sum-free test. test_passed is 1 if all four hold.
5. Beside the test, none of it counted: the sizes of the sets; the depth d(P), the largest of the sets' minimums; the
   e-depth D(P), the largest d(mP) over the multipliers m prime to n + 1 (mP the partition with every element replaced
   by mx mod (n + 1)), against the 161 and 537 the paper prints; at the multiplier attaining it, whether mP is again a
   symmetric sum-free partition (the paper says it always is) and whether the sets of mP other than the one whose
   minimum is D(P) cover {1, ..., D(P) - 1}, a sum-free partition of it into k - 1 sets (161 - 1 = 160 = S(5), and
   537 - 1 = 536); and S(1), S(2) and S(3), 1, 4 and 13, found by exhaustive search with the same sum-free test.

Controls (controls_passed counts those that behave as stated): the triangle test finds the triangle in a colouring
with 1, 2 and 3 in one set and none in the colouring of K14 from a sum-free partition of {1, ..., 13} into 3; on 20
seed-drawn perturbations of the two partitions (one listed number, with its partner, moved to another set) the sum-free
and triangle tests agree on every one and catch at least one (a number may fit more than one set); at its multiplier, mP is a symmetric sum-free partition of
the same n; and the exhaustive search finds a sum-free partition of {1, ..., S(k)} into k sets and none of
{1, ..., S(k) + 1}, for k = 1, 2, 3.

What it cannot check: that the bounds were new in 2000 (they were, against Radziszowski's survey of 1999, as the
paper says), the paper's observations about symmetric partitions into 5 sets, and its conjecture that there are
309,408 of them of 160.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 schur/fs.py
"""

import hashlib
import json
import math
import os
import re
import sys
import zlib

INPUT = ("fredricksen-sweet-ejc-7-r32.pdf", "ae8541c564efd65785a0e1d2c778108d58fec4c060707d7c277dd7f3eecad259", 132421)
PARTITIONS = ((536, 6), (1680, 7))
PRINTED_E_DEPTH = {536: 161, 1680: 537}
GAP = 0.15
STATEMENTS = (
    "The constructions exhibited below are symmetric, and so we only list the small",
    "Partition of 536 into 6 symmetric sumfree sets:",
    "Partition of 1680 into 7 symmetric sumfree sets:",
    "said to be symmetric if all symmetric pairs",
    "we must allow",
)
PERTURBATIONS = 20
OUTPUTS = ("statements", "listed", "s6", "s6_sums", "s7", "s7_sums", "ramsey", "k537_triangles", "k1681_triangles",
           "e_depth", "embedded", "depth", "small_values", "conditions_met", "conditions_total", "test_passed",
           "controls_passed", "controls_total")
LIMIT = 200


class Refused(Exception):
    pass


# ---------------------------------------------------------------- reading the PDF

def read_input(inputs):
    name, sha, size = INPUT
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha or len(data) != size:
        raise Refused(f"{name}: sha256 {got} ({len(data)} bytes), not the registered {sha} ({size})")
    return data


def content_streams(data):
    """The Flate-compressed streams that are not fonts, decompressed, in file order."""
    out = []
    for m in re.finditer(rb"(\d+) 0 obj\s*<<(.*?)>>\s*stream\r?\n", data, re.S):
        d = m.group(2)
        if b"/Length1" in d or b"/Subtype" in d or b"/FlateDecode" not in d:
            continue
        length = re.search(rb"/Length\s+(\d+)\s", d + b" ")
        if not length:
            continue
        raw = data[m.end():m.end() + int(length.group(1))]
        try:
            dec = zlib.decompress(raw)
        except zlib.error as e:
            raise Refused(f"object {m.group(1).decode()}: {e}")
        if b"TJ" in dec or b"Tj" in dec:
            out.append(dec)
    return out


def unescape(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == 0x5C and i + 1 < len(s):
            n = s[i + 1]
            if 0x30 <= n <= 0x37:
                j, v = i + 1, 0
                while j < len(s) and j < i + 4 and 0x30 <= s[j] <= 0x37:
                    v = v * 8 + s[j] - 0x30
                    j += 1
                out.append(v & 0xFF)
                i = j
                continue
            out.append({0x6E: 10, 0x72: 13, 0x74: 9, 0x62: 8, 0x66: 12}.get(n, n))
            i += 2
            continue
        out.append(c)
        i += 1
    return bytes(out)


TOKEN = re.compile(rb"\[((?:\((?:\\.|[^\\)])*\)|[^\]])*)\]\s*TJ|\(((?:\\.|[^\\)])*)\)\s*Tj|(-?[\d.]+)\s+Tc\b"
                   rb"|(T\*|-?[\d.]+\s+-?[\d.]+\s+T[dD]\b|(?:-?[\d.]+\s+){6}Tm\b)", re.S)
PART = re.compile(rb"\(((?:\\.|[^\\)])*)\)|(-?[\d.]+)", re.S)


def text_lines(stream):
    """The stream's text, one line per text-positioning operator, spaces where the gap after a glyph is wide."""
    lines, cur, tc = [], [], 0.0
    for t in TOKEN.finditer(stream):
        if t.group(3) is not None:
            tc = float(t.group(3))
            continue
        if t.group(4) is not None:
            lines.append("".join(cur))
            cur = []
            continue
        if t.group(2) is not None:
            parts = [[unescape(t.group(2)), 0.0]]
        else:
            parts = []
            for p in PART.finditer(t.group(1)):
                if p.group(1) is not None:
                    parts.append([unescape(p.group(1)), 0.0])
                elif parts:
                    parts[-1][1] = float(p.group(2))
        for k, (s, adj) in enumerate(parts):
            for j, ch in enumerate(s):
                cur.append(chr(ch) if 32 <= ch < 127 else "·")
                last = j == len(s) - 1
                gap = tc - (adj / 1000.0 if last else 0.0)
                if gap > GAP and not (last and k == len(parts) - 1):
                    cur.append(" ")
        cur.append(" ")
    lines.append("".join(cur))
    return [" ".join(x.split()) for x in lines if x.strip()]


def document_lines(data):
    """Every line of the document in order, the page headers dropped."""
    out = []
    for stream in content_streams(data):
        lines = text_lines(stream)
        k = 0
        while k < len(lines):
            if lines[k] == "the electronic journal of combinatorics":
                k += 1
                # volume, "(2000), #R32" and the page number follow the journal's name
                while k < len(lines) and (re.fullmatch(r"\d+", lines[k]) or lines[k].startswith("(2000)")):
                    k += 1
                continue
            out.append(lines[k])
            k += 1
    return out


def statements_found(lines):
    flat = " ".join(lines)
    return {s: s in flat for s in STATEMENTS}


def read_partition(lines, n, k):
    head = f"Partition of {n} into {k} symmetric sumfree sets:"
    try:
        at = lines.index(head)
    except ValueError:
        raise Refused(f"no line {head!r}")
    sets, cur = [], None
    for line in lines[at + 1:]:
        m = re.fullmatch(r"Set (\d+): ?(.*)", line)
        if m:
            if int(m.group(1)) != len(sets) + 1:
                raise Refused(f"{n}: set {m.group(1)} out of order")
            cur = []
            sets.append(cur)
            rest = m.group(2)
        elif line.startswith("(") or not re.fullmatch(r"[\d ]+", line):
            break
        else:
            rest = line
        if cur is None:
            raise Refused(f"{n}: numbers before the first set")
        cur.extend(int(x) for x in rest.split())
    if len(sets) != k:
        raise Refused(f"{n}: {len(sets)} sets read, not {k}")
    listed = [x for s in sets for x in s]
    if len(listed) != len(set(listed)) or not all(1 <= x <= n for x in listed):
        raise Refused(f"{n}: a number listed twice or out of range")
    top = (n + 1) // 2
    half = set(range(1, top + 1)) | {x for x in special(n) if x > top}
    if set(listed) != half:
        raise Refused(f"{n}: the listing is not 1..{top} once each (and the split pair): a reading error")
    return sets


def special(n):
    """The pair that may be split: (n + 1)/3 and 2(n + 1)/3, when 3 divides n + 1."""
    return {(n + 1) // 3, 2 * (n + 1) // 3} if (n + 1) % 3 == 0 else set()


def expand(listed, n):
    """The paper's listing rule: a listed i stands for i and n + 1 - i, but for the pair that may be split."""
    sp = special(n)
    return [sorted({x for i in s for x in ((i,) if i in sp else (i, n + 1 - i))}) for s in listed]


def coverage(sets, n):
    """How often each of 1..n appears across the sets: the list of numbers missing and of numbers repeated."""
    seen = {}
    for s in sets:
        for x in s:
            seen[x] = seen.get(x, 0) + 1
    missing = [x for x in range(1, n + 1) if x not in seen]
    repeated = sorted(x for x, c in seen.items() if c > 1)
    stray = sorted(x for x in seen if not 1 <= x <= n)
    return missing, repeated, stray


def sums_inside(s):
    """The number of a <= b in s with a + b in s (a = b allowed)."""
    members = set(s)
    v = sorted(members)
    count = 0
    for i, a in enumerate(v):
        for b in v[i:]:
            if a + b > v[-1]:
                break
            if a + b in members:
                count += 1
    return count


def is_partition(sets, n):
    missing, repeated, stray = coverage(sets, n)
    return not missing and not repeated and not stray


# ---------------------------------------------------------------- the colourings of complete graphs

def triangles(sets, n):
    """Monochromatic triangles in the colouring of K_{n+1} on {0..n}, edge uv coloured by the set holding |u - v|:
    for every edge, its endpoints' common neighbours in its colour, by bit sets. Returns (triangles, edges)."""
    full = (1 << (n + 1)) - 1
    tri, edges = 0, 0
    for s in sets:
        fwd = 0
        rev = 0
        for d in s:
            if 1 <= d <= n:
                fwd |= 1 << d
                rev |= 1 << (n - d)
        neigh = [((fwd << u) | (rev >> (n - u))) & full for u in range(n + 1)]
        for u in range(n + 1):
            for d in s:
                v = u + d
                if v > n:
                    continue
                edges += 1
                common = neigh[u] & neigh[v]
                if common:
                    tri += bin(common).count("1")
    return tri // 3, edges


# ---------------------------------------------------------------- depth, equivalence and small Schur numbers

def depth(sets):
    return max(min(s) for s in sets if s)


def multiply(sets, m, n):
    return [sorted((m * x) % (n + 1) for x in s) for s in sets]


def e_depth(sets, n):
    best, arg = -1, None
    for m in range(1, n + 1):
        if math.gcd(m, n + 1) != 1:
            continue
        d = max(min((m * x) % (n + 1) for x in s) for s in sets)
        if d > best:
            best, arg = d, m
    return best, arg


def symmetric(sets, n):
    sp = special(n)
    where = {x: i for i, s in enumerate(sets) for x in s}
    return all(where.get(n + 1 - x) == where[x] for x in where if x not in sp)


def schur_search(k, n):
    """A partition of {1..n} into k sum-free sets, or None: exhaustive backtracking, colours opened in order."""
    colour = [None] * (n + 1)
    members = [set() for _ in range(k)]

    def ok(x, c):
        s = members[c]
        if x + x in s or (x % 2 == 0 and x // 2 in s):
            return False
        return not any((x - a) in s for a in s if a < x)

    def go(x, used):
        if x > n:
            return True
        for c in range(min(used + 1, k)):
            if ok(x, c):
                members[c].add(x)
                colour[x] = c
                if go(x + 1, max(used, c + 1)):
                    return True
                members[c].discard(x)
        return False

    if go(1, 0):
        return [sorted(s) for s in members]
    return None


def schur_number(k):
    n = 0
    while schur_search(k, n + 1) is not None:
        n += 1
    return n


# ---------------------------------------------------------------- seeds

class Stream:
    """Integers from the seed: SHA-256 of seed, label and a counter."""

    def __init__(self, seed, label):
        self.seed, self.label, self.n = seed, label, 0

    def below(self, m):
        self.n += 1
        h = hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
        return int.from_bytes(h[:8], "big") % m


def perturb(listed, n, st):
    """Move one listed number (with its partner) to another set."""
    k = len(listed)
    src = st.below(k)
    while not listed[src]:
        src = st.below(k)
    x = listed[src][st.below(len(listed[src]))]
    dst = (src + 1 + st.below(k - 1)) % k
    out = [list(s) for s in listed]
    out[src].remove(x)
    out[dst].append(x)
    return expand(out, n), x, src, dst


# ---------------------------------------------------------------- the run

def conditions(found):
    return {
        "536 into 6: a partition of {1..536} into sum-free sets": found[536]["partition"] and found[536]["sums"] == 0,
        "1680 into 7: a partition of {1..1680} into sum-free sets": found[1680]["partition"] and found[1680]["sums"] == 0,
        "K537 coloured by it: no triangle of one colour": found[536]["triangles"] == 0,
        "K1681 coloured by it: no triangle of one colour": found[1680]["triangles"] == 0,
    }


def listing(values):
    return ", ".join(str(v) for v in values)


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    data = read_input(inputs)
    lines = document_lines(data)
    stmts = statements_found(lines)
    found, listed_all = {}, {}
    for n, k in PARTITIONS:
        listed = read_partition(lines, n, k)
        listed_all[n] = listed
        sets = expand(listed, n)
        missing, repeated, stray = coverage(sets, n)
        tri, edges = triangles(sets, n)
        d_e, m = e_depth(sets, n)
        mp = multiply(sets, m, n)
        top = max(range(k), key=lambda i: min(mp[i]))
        below = [[x for x in s if x < d_e] for i, s in enumerate(mp) if i != top]
        found[n] = {"k": k, "listed_sizes": [len(s) for s in listed], "sizes": [len(s) for s in sets],
                    "partition": not missing and not repeated and not stray, "missing": missing[:10],
                    "repeated": repeated[:10], "sums": sum(sums_inside(s) for s in sets),
                    "sums_by_set": [sums_inside(s) for s in sets], "triangles": tri, "edges": edges,
                    "depth": depth(sets), "e_depth": d_e, "multiplier": m,
                    "mp_symmetric_sum_free": symmetric(mp, n) and is_partition(mp, n)
                    and all(sums_inside(s) == 0 for s in mp),
                    "embedded_partition": is_partition(below, d_e - 1) and all(sums_inside(s) == 0 for s in below),
                    "embedded_sizes": [len(s) for s in below], "split_pair": sorted(special(n))}
    cond = conditions(found)
    smalls = {k: schur_number(k) for k in (1, 2, 3)}

    # controls
    ctl, ctl_detail = {}, {}
    t3 = [[1, 2, 3]]
    tri_bad, _ = triangles(t3, 3)
    p13 = schur_search(3, 13)
    tri13, _ = triangles(p13, 13)
    ctl["the triangle test finds the triangle of {1, 2, 3} and none in K14 from a partition of 1..13"] = (
        tri_bad >= 1 and p13 is not None and tri13 == 0)
    st = Stream(seed, "fs/perturb")
    agree, caught, rows = 0, 0, []
    for j in range(PERTURBATIONS):
        n, k = PARTITIONS[j % 2]
        sets, x, src, dst = perturb(listed_all[n], n, st)
        bad_sum = sum(sums_inside(s) for s in sets) > 0
        tri, _ = triangles(sets, n)
        agree += int(bad_sum == (tri > 0))
        caught += int(bad_sum and tri > 0)
        rows.append({"n": n, "moved": x, "from": src + 1, "to": dst + 1, "sums": bad_sum, "triangles": tri})
    ctl["on 20 seed-drawn perturbations the two tests agree, and some are caught"] = (
        agree == PERTURBATIONS and caught >= 1)
    ctl_detail["perturbations_caught"] = caught
    ctl_detail["perturbations"] = rows
    ctl["at the multiplier attaining D(P), mP is again a symmetric sum-free partition"] = all(
        f["mp_symmetric_sum_free"] for f in found.values())
    ctl["exhaustive search: S(1) = 1, S(2) = 4, S(3) = 13"] = smalls == {1: 1, 2: 4, 3: 13}

    f6, f7 = found[536], found[1680]
    values = {
        "statements": f"the listing rule, both headings and the definitions in the paper: {sum(stmts.values())} of "
                      f"{len(stmts)}",
        "listed": (f"listed: {sum(f6['listed_sizes'])} numbers in 6 sets ({listing(f6['listed_sizes'])}); "
                   f"{sum(f7['listed_sizes'])} in 7 ({listing(f7['listed_sizes'])})"),
        "s6": (f"536 into 6: {'each of 1..536 once' if f6['partition'] else 'not a partition'}, sets of "
               f"{listing(f6['sizes'])}; 179 and 358 split"),
        "s6_sums": f6["sums"],
        "s7": (f"1680 into 7: {'each of 1..1680 once' if f7['partition'] else 'not a partition'}, sets of "
               f"{listing(f7['sizes'])}"),
        "s7_sums": f7["sums"],
        "ramsey": (f"monochromatic triangles: K537 {f6['triangles']} over {f6['edges']} edges in 6 colours; K1681 "
                   f"{f7['triangles']} over {f7['edges']} in 7"),
        "k537_triangles": f6["triangles"],
        "k1681_triangles": f7["triangles"],
        "e_depth": (f"D(P) = {f6['e_depth']} (m = {f6['multiplier']}) and {f7['e_depth']} (m = {f7['multiplier']}); "
                    f"the paper prints {PRINTED_E_DEPTH[536]} and {PRINTED_E_DEPTH[1680]}"),
        "embedded": (f"at those m the other sets are sum-free partitions of 1..{f6['e_depth'] - 1} into 5 "
                     f"({'yes' if f6['embedded_partition'] else 'no'}) and of 1..{f7['e_depth'] - 1} into 6 "
                     f"({'yes' if f7['embedded_partition'] else 'no'})"),
        "depth": f"d(P) as printed: {f6['depth']} and {f7['depth']}",
        "small_values": f"S(1), S(2), S(3) by exhaustive search: {listing(smalls[k] for k in (1, 2, 3))}",
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for key, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")
    detail = {"input": {"name": INPUT[0], "sha256": INPUT[1], "bytes": INPUT[2]}, "statements": stmts,
              "conditions": cond, "controls": ctl, "control_detail": ctl_detail,
              "partitions": {str(n): {**{k_: v for k_, v in f.items()}, "listed": listed_all[n]}
                             for n, f in found.items()},
              "printed_e_depth": PRINTED_E_DEPTH, "small_values": smalls}
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
        sys.exit(f"fs: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
