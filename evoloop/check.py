#!/usr/bin/env python3
"""Sayama's evoloop: loops that vary by colliding, the smaller selected for their quicker self-reproduction, and the
population evolving toward the smallest.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:60cc0fcc84ce2b54) is from Sayama, "A New
Structurally Dissolvable Self-Reproducing Loop Evolving in a Simple Cellular Automata Space", Artificial Life 5(4),
343-365 (1999): "The experiment with evoloop met with the intriguing result that, though no mechanism was explicitly
provided to promote evolution, the loops varied through direct interaction of their phenotypes, smaller individuals
were naturally selected thanks to their quicker self-reproductive ability, and the whole population gradually evolved
toward the smallest ones."

Its registered test: refuted if, under the evoloop's rules as Sayama published them (Artificial Life 10, 2004,
Appendix A.1), with the size-13 ancestor (genome 774477777777777) alone at the centre of periodic spaces of 199 x 199,
200 x 200 and 201 x 201 sites for 50,000 updates (his thesis's setting): in two of the three, size 4 is not strictly
the most numerous loop size at the end (loops counted by their square holes); or, built alone in the ancestor's
layout, loops of sizes 4 to 13 do not give their first offspring sooner the smaller they are, or one gives a loop of
another size first.

The paper's text is closed. The setting is that of the thesis it came from (Sayama, "Constructing Evolutionary
Systems on a Simple Deterministic Cellular Automata Space", University of Tokyo, 1998, section 6.3.1: spaces of
199 x 199 to 201 x 201 sites with periodic boundaries, ancestors of sizes 10 to 13, 50,000 updates; the 2-evoloop of
size 13 in 200 x 200 is its typical case). The rules are Sayama's own: Table 2 of "Self-Protection and Diversity in
Self-Replicating Cellular Automata", Artificial Life 10(1), 83-98 (2004), "the principal part of the transition rules
of the original evoloop", transcribed below from the author's copy of that paper (bingweb.binghamton.edu/~sayama/
papers/ALIFE10-1-83.pdf, SHA-256 43b09426...29d0d), with Appendix A.1's steps for every situation the table leaves
undefined. The inputs are Golly's Evoloop.rule and Evoloop.rle (AlephAlpha/golly at dcbc087, GPL-2.0-or-later),
checked against their SHA-256 and sizes and read as text: the ancestor is the rle's, and the rule table, transcribed
for Golly from an applet of 1999, is run beside the test. The evoloop is deterministic, so nothing is random and the
seed is not used.

1. The rules. Sayama's: each CTRBL->I of Table 2 and its rotations (TRBL turned round together); then 8 -> 0 with no
   condition; then, for situations still undefined with a state 8 among the four neighbours, 0 and 1 -> 8 if a state
   2 to 7 is among them, else unchanged, 2, 3, 5 -> 0 and 4, 6, 7 -> 1; then every other undefined situation 0 -> 0
   and 1 to 7 -> 8. Golly's: its @TABLE (nine states, von Neumann neighbours, rotate4 symmetry; a variable named
   twice in a transition takes one value; the first transition that matches wins; a situation no transition matches
   keeps its state). Each must give every one of the 9^5 situations one state.
2. The ancestor: the rle (rule Evoloop, 17 x 17), placed with its top-left corner at ((L - 17) // 2, (L - 17) // 2)
   in an L x L torus. Loops of other sizes are built in its layout: a loop of size n has a ring of n + 2 sites a side
   carrying the genome 77 44 7^(n-2), each gene written as the gene, 0, 1 in the ring's clockwise order from the site
   five above its lower right corner, then 1s; an inner sheath of side n around a hole of side n - 2, an outer sheath
   of side n + 4 without its corners, and the state 5 one site left of its lower right end. Size 13 built so must equal
   the rle, site for site.
3. The census: a loop is counted by its hole, a 4-connected region of state 0 on the torus, of at most 400 sites,
   that fills a rectangle whose surrounding ring, corners included, is all sheath (2 or 3, the states Sayama's own
   observer reads). A square hole of side h is a loop of size h + 2; other rectangles are counted apart, as variants.
4. The three spaces: the ancestor alone in tori of 199, 200 and 201 sites a side, 50,000 updates under Sayama's
   rules, a census every 1,000 updates.
5. Alone: each size n from 4 to 13 built and placed alone at the centre of a torus of 10(n + 4) sites a side, a census
   at every update until four loops of its size are counted (at most 3,000 updates). Its first offspring is the update
   at which two loops of its size are first counted; it is faithful if no loop of another size and no variant is
   counted before then.
6. The test's three conditions: size 4 strictly the most numerous size at update 50,000 in at least two of the three
   spaces; the first offspring strictly sooner the smaller the loop, from 4 to 13; every built loop faithful alone.
   test_passed is 1 if all three hold.
7. Beside the test, none of it counted: the three spaces under Golly's rules; tori of 100, 150, 250 and 300 sites a
   side under Sayama's; the mean loop size over updates 1,000 to 10,000 and 41,000 to 50,000.

Controls (controls_passed counts those that behave as stated): size 13 built equals the rle; the rle's genome reads
774477777777777; Golly's table agrees with Table 2 on every situation Table 2 defines; both rules leave the quiescent
state alone; the census, on a drawn torus holding built loops of sizes 4 to 13, a 2 x 3 rectangle ringed with sheath
and a size-6 loop whose inner sheath has one site broken, counts exactly the ten loops and the one variant.

What it cannot check: the paper's own runs (its text is closed), and whether the loops that win are, as the paper
says, selected for their speed rather than for something else: the receipt measures that smaller loops reproduce
faster alone and that the smallest prevail together, not the cause.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every census). Run with:
python3 evoloop/check.py
"""

import hashlib
import itertools
import json
import multiprocessing as mp
import os
import re
import sys
import time

import numpy as np
from scipy import ndimage

Q = 9
INPUTS = {
    "Evoloop.rule": ("66bd78244429a4315a12079b30c5c00e1faf8cd3cf10fe4c6bb12d0f1ed9ee82", 16263),
    "Evoloop.rle": ("6b01375510ba6fa5fd55d4a48c36344ffdd0520605e2c30a2f81ca441c3af689", 967),
}
# Table 2 of Sayama (2004), CTRBL->I, sorted; the hash below is of these tokens joined by single spaces.
TABLE2 = """
00001->2 00004->3 00012->2 00015->2 00021->2 00024->2 00042->2 00045->2 00075->2 00102->2
00214->1 00217->1 00232->2 01122->1 01212->1 01232->1 01242->1 01245->1 01252->6 01262->6
01272->1 01275->1 01342->1 01372->1 01422->1 01425->1 01432->1 01435->1 01442->1 01462->1
01722->1 01725->1 01756->1 01762->1 01772->1 10001->1 10012->1 10021->1 10024->4 10027->7
10121->1 10124->4 10127->7 10202->1 10211->1 10212->1 10213->1 10221->1 10224->4 10227->7
10232->4 10241->4 10242->4 10243->4 10251->1 10252->7 10254->3 10257->7 10271->7 10272->7
10273->5 10512->1 10542->4 10572->7 10621->1 10624->4 10627->7 11112->1 11122->1 11124->4
11125->1 11127->7 11162->1 11212->1 11213->1 11215->1 11222->1 11224->4 11227->7 11232->1
11242->4 11243->4 11252->7 11254->3 11257->7 11262->6 11272->7 11273->5 11322->1 11332->1
11542->4 11572->7 11624->4 11627->7 12224->4 12227->7 12243->4 12273->7 12324->4 12327->7
12426->6 12433->3 12627->6 20001->2 20002->2 20004->2 20005->2 20006->0 20007->1 20012->2
20015->2 20021->2 20022->2 20023->2 20024->2 20026->0 20027->2 20032->4 20042->3 20045->2
20054->5 20057->5 20062->0 20072->2 20075->2 20102->2 20112->2 20122->2 20142->2 20172->2
20202->2 20203->2 20205->2 20206->5 20207->3 20212->2 20215->2 20221->2 20222->2 20223->2
20232->3 20242->2 20245->2 20252->5 20262->0 20265->0 20272->2 20275->2 20312->2 20322->2
20342->2 20345->2 20372->2 20412->2 20422->2 20442->2 20512->2 20542->5 20572->5 20612->5
20621->2 20642->5 20672->5 20712->2 20722->2 20772->2 21122->2 21222->2 21223->2 21224->2
21227->2 21232->3 21322->2 21422->2 21622->2 21722->2 22224->2 22227->2 22234->2 22237->2
22243->2 22244->2 22273->2 22277->2 22324->3 22327->3 30001->3 30002->2 30003->2 30004->3
30007->4 30012->3 30032->2 30042->1 30102->1 30125->0 30212->3 30242->3 30252->1 30272->3
30332->1 31212->3 31242->3 31252->1 31272->3 32424->3 32425->1 32427->3 32527->1 32727->3
40000->1 40002->1 40102->0 40112->0 40122->0 40125->0 40162->0 40212->0 40215->0 40222->1
40232->1 40262->6 40312->0 40322->1 50002->5 50012->5 50021->5 50023->2 50024->5 50027->5
50042->5 50072->5 50202->2 50205->2 50212->5 50215->2 50242->5 50272->5 50312->0 60202->2
60212->2 60222->0 60242->2 60272->2 61222->0 62224->0 62227->0 70102->0 70112->0 70122->0
70125->0 70162->0 70212->0 70215->0 70222->1 70232->0 70262->6 70312->0
"""
TABLE2_SHA = "2dac7019e02e35017ebe4784317cb1e814a3ffc8f13859c3176ebc237d4ba323"
TABLE2_COUNT = 258

GENOME = "774477777777777"
ANCESTOR = 13
SIZES = tuple(range(4, 14))
SPACES = (199, 200, 201)
BESIDE = (100, 150, 250, 300)
UPDATES = 50000
EVERY = 1000
ALONE_LIMIT = 3000
MAX_HOLE = 400
SHEATH = (2, 3)
LIMIT = 200
OUTPUTS = ("genome", "seed_equals_built", "rules_compared", "end_199", "end_200", "end_201", "top_199", "top_200",
           "top_201", "spaces_size4", "first_offspring", "births_rising", "faithful_alone", "golly_rules",
           "other_spaces", "mean_size", "controls_passed", "controls_total", "test_passed")


class Refused(Exception):
    pass


def load(inputs, name):
    sha, size = INPUTS[name]
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    if len(data) != size or hashlib.sha256(data).hexdigest() != sha:
        raise Refused(f"{name}: not the pinned file")
    return data.decode("ascii")


# ---------------------------------------------------------------- the rules (rule 1)

def table2_rules(text=TABLE2):
    toks = text.split()
    if len(toks) != TABLE2_COUNT or hashlib.sha256(" ".join(toks).encode()).hexdigest() != TABLE2_SHA:
        raise Refused("Table 2: not the transcription this module was written with")
    out = []
    for tok in toks:
        m = re.fullmatch(r"([0-8])([0-8])([0-8])([0-8])([0-8])->([0-8])", tok)
        if not m:
            raise Refused(f"Table 2: {tok}")
        out.append(tuple(int(x) for x in m.groups()))
    return out


def turns(n, e, s, w):
    """The four rotations of a von Neumann neighbourhood (north, east, south, west)."""
    return ((n, e, s, w), (w, n, e, s), (s, w, n, e), (e, s, w, n))


def sayama_rules(rules=None):
    """Rule 1, Sayama's: Table 2 and its rotations, then Appendix A.1's steps 2 to 4. Returns (table, defined)."""
    rules = table2_rules() if rules is None else rules
    t = -np.ones((Q,) * 5, dtype=np.int16)
    for c, n, e, s, w, out in rules:
        for nb in turns(n, e, s, w):
            if t[(c,) + nb] >= 0 and t[(c,) + nb] != out:
                raise Refused(f"Table 2: two images for {c}{''.join(map(str, nb))}")
            t[(c,) + nb] = out
    defined = t >= 0
    t[8][t[8] < 0] = 0                                                   # step 2: 8 -> 0
    c, n, e, s, w = np.indices((Q,) * 5)
    nbs = (n, e, s, w)
    has8 = np.zeros_like(defined)
    live = np.zeros_like(defined)
    for x in nbs:
        has8 |= x == 8
        live |= (x >= 2) & (x <= 7)
    und = (t < 0) & has8                                                 # step 3
    t[und & (c <= 1) & live] = 8
    t[und & (c <= 1) & ~live] = c[und & (c <= 1) & ~live]
    t[und & np.isin(c, (2, 3, 5))] = 0
    t[und & np.isin(c, (4, 6, 7))] = 1
    rest = t < 0                                                         # step 4
    t[rest & (c == 0)] = 0
    t[rest & (c > 0)] = 8
    return t.astype(np.uint8), defined


def golly_rules(text):
    """Rule 1, Golly's: the @TABLE section, first match wins, unlisted situations unchanged."""
    if not text.startswith("@RULE Evoloop\n"):
        raise Refused("Evoloop.rule: not the Evoloop rule")
    body = text[text.index("@TABLE"):]
    nxt = body.find("\n@", 1)
    body = body[:nxt] if nxt > 0 else body
    var, trans, head = {}, [], {}
    for raw in body.splitlines()[1:]:
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        m = re.fullmatch(r"var\s+(\w+)\s*=\s*\{([^}]*)\}", line)
        if m:
            vals = []
            for x in (y.strip() for y in m.group(2).split(",")):
                vals += var[x] if x in var else [int(x)]
            var[m.group(1)] = vals
            continue
        m = re.fullmatch(r"(n_states|neighborhood|symmetries)\s*:\s*(\w+)", line)
        if m:
            head[m.group(1)] = m.group(2)
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 6:
            raise Refused(f"Evoloop.rule: {line}")
        trans.append(parts)
    if head != {"n_states": "9", "neighborhood": "vonNeumann", "symmetries": "rotate4"}:
        raise Refused(f"Evoloop.rule: {head}")
    t = -np.ones((Q,) * 5, dtype=np.int16)
    for parts in trans:
        names = list(dict.fromkeys(p for p in parts[:5] if p in var))
        for combo in itertools.product(*[var[v] for v in names]):
            bind = dict(zip(names, combo))
            c, n, e, s, w = (bind[p] if p in bind else int(p) for p in parts[:5])
            out = bind[parts[5]] if parts[5] in bind else int(parts[5])
            for nb in turns(n, e, s, w):
                if t[(c,) + nb] < 0:
                    t[(c,) + nb] = out
    c = np.indices((Q,) * 5)[0]
    t[t < 0] = c[t < 0]
    return t.astype(np.uint8), len(trans)


# ---------------------------------------------------------------- the ancestor and built loops (rule 2)

def read_rle(text):
    head = [l for l in text.splitlines() if l.startswith("x")]
    if len(head) != 1 or re.fullmatch(r"x = 17, y = 17, rule = Evoloop", head[0].strip()) is None:
        raise Refused(f"Evoloop.rle: {head}")
    body = "".join(l for l in text.splitlines() if not l.startswith(("#", "x")))
    rows, row = [], []
    for k, ch in re.findall(r"(\d*)([.A-H$!])", body):
        k = int(k) if k else 1
        if ch == "$":
            rows.append(row)
            rows.extend([] for _ in range(k - 1))
            row = []
        elif ch == "!":
            rows.append(row)
            break
        else:
            row += [0 if ch == "." else ord(ch) - 64] * k
    grid = np.zeros((17, 17), dtype=np.uint8)
    if len(rows) != 17 or max(len(r) for r in rows) > 17:
        raise Refused("Evoloop.rle: not 17 x 17")
    for y, r in enumerate(rows):
        grid[y, :len(r)] = r
    return grid


def ring(n):
    """The gene ring of a loop of size n (side n + 2, rows and columns 1 to n + 2), clockwise from the top left."""
    m = n + 2
    return ([(1, x) for x in range(1, m + 1)] + [(y, m) for y in range(2, m + 1)]
            + [(m, x) for x in range(m - 1, 0, -1)] + [(y, 1) for y in range(m - 1, 1, -1)])


def ring_from_head(n):
    cells = ring(n)
    start = cells.index((n + 2 - 5, n + 2))
    return cells[start:] + cells[:start]


def build(n, genome=None):
    """Rule 2: a loop of size n in the ancestor's layout."""
    genome = genome if genome is not None else "77" + "44" + "7" * (n - 2)
    if n < 4:
        raise Refused("a loop of size 3 or less has no room for the layout")
    g = np.zeros((n + 4, n + 4), dtype=np.uint8)
    for i in range(1, n + 3):
        g[0, i] = g[n + 3, i] = g[i, 0] = g[i, n + 3] = 2
    g[n + 3, n + 2] = 5
    for i in range(2, n + 2):
        g[2, i] = g[n + 1, i] = g[i, 2] = g[i, n + 1] = 2
    seq = [v for gene in genome for v in (int(gene), 0, 1)]
    cells = ring_from_head(n)
    if len(seq) > len(cells):
        raise Refused(f"genome {genome} does not fit a loop of size {n}")
    seq += [1] * (len(cells) - len(seq))
    for (y, x), v in zip(cells, seq):
        g[y, x] = v
    return g


def genome_of(grid, n):
    """The genome a loop in the ancestor's layout carries: gene, 0, 1 triples from the head, then only 1s."""
    vals = [int(grid[c]) for c in ring_from_head(n)]
    genes = []
    i = 0
    while i + 2 < len(vals) and vals[i] in (4, 7) and vals[i + 1] == 0 and vals[i + 2] == 1:
        genes.append(str(vals[i]))
        i += 3
    if any(v != 1 for v in vals[i:]):
        return None
    return "".join(genes)


def place(pattern, L):
    g = np.zeros((L, L), dtype=np.uint8)
    h, w = pattern.shape
    y0, x0 = (L - h) // 2, (L - w) // 2
    g[y0:y0 + h, x0:x0 + w] = pattern
    return g


def step(g, flat):
    idx = g.astype(np.int32) * Q + np.roll(g, 1, 0)            # north: the site above
    idx = idx * Q + np.roll(g, -1, 1)                            # east
    idx = idx * Q + np.roll(g, -1, 0)                            # south
    idx = idx * Q + np.roll(g, 1, 1)                             # west
    return flat[idx]


# ---------------------------------------------------------------- the census (rule 3)

def census(g):
    """Rule 3: {size: count} for square loops, and the number of variants (other rectangles)."""
    L = g.shape[0]
    lab, k = ndimage.label(g == 0)
    parent = np.arange(k + 1)

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for a, b in ((lab[0, :], lab[-1, :]), (lab[:, 0], lab[:, -1])):
        for x, y in zip(a.tolist(), b.tolist()):
            if x and y:
                rx, ry = find(x), find(y)
                if rx != ry:
                    parent[rx] = ry
    roots = np.array([find(i) for i in range(k + 1)])
    lab = roots[lab]
    sizes = np.bincount(lab.ravel(), minlength=k + 1)
    sheath = np.isin(g, SHEATH)
    loops, variants = {}, 0
    small = np.nonzero((sizes > 0) & (sizes <= MAX_HOLE))[0]
    small = small[small > 0]
    objects = ndimage.find_objects(lab)
    for r in small.tolist():
        sl = objects[r - 1]
        if sl is None:
            continue
        ys, xs = sl
        if ys.stop - ys.start > L // 2 or xs.stop - xs.start > L // 2:      # wrapped round the torus: unwrap
            yy, xx = np.nonzero(lab == r)
            if yy.max() - yy.min() > L // 2:
                yy = np.where(yy < L // 2, yy + L, yy)
            if xx.max() - xx.min() > L // 2:
                xx = np.where(xx < L // 2, xx + L, xx)
            y0, y1, x0, x1 = int(yy.min()), int(yy.max()), int(xx.min()), int(xx.max())
        else:
            y0, y1, x0, x1 = ys.start, ys.stop - 1, xs.start, xs.stop - 1
        h, w = y1 - y0 + 1, x1 - x0 + 1
        if h * w != sizes[r]:
            continue
        rows = np.arange(y0 - 1, y1 + 2) % L
        cols = np.arange(x0 - 1, x1 + 2) % L
        box = sheath[np.ix_(rows, cols)]
        if not (box[0, :].all() and box[-1, :].all() and box[:, 0].all() and box[:, -1].all()):
            continue
        if h == w:
            loops[h + 2] = loops.get(h + 2, 0) + 1
        else:
            variants += 1
    return loops, variants


# ---------------------------------------------------------------- runs (rules 4, 5 and 7)

_TABLES = {}


def run_space(job):
    """Rules 4 and 7: the ancestor alone in an L x L torus for UPDATES updates; a census every EVERY updates."""
    rules, L, ancestor = job
    flat = _TABLES[rules]
    g = place(ancestor, L)
    series = []
    t0 = time.process_time()
    for t in range(1, UPDATES + 1):
        g = step(g, flat)
        if t % EVERY == 0:
            loops, variants = census(g)
            series.append({"t": t, "loops": {str(k): v for k, v in sorted(loops.items())}, "variants": variants,
                           "live": int(np.count_nonzero(g))})
    return {"rules": rules, "L": L, "series": series, "cpu_s": round(time.process_time() - t0, 1)}


def alone(n, flat):
    """Rule 5: a built loop of size n alone; the update of each new loop of its size, and anything else counted."""
    g = place(build(n), 10 * (n + 4))
    seen, births, other = 1, [], []
    for t in range(1, ALONE_LIMIT + 1):
        g = step(g, flat)
        loops, variants = census(g)
        if variants or any(s != n for s in loops):
            other.append({"t": t, "loops": {str(k): v for k, v in loops.items()}, "variants": variants})
        k = loops.get(n, 0)
        if k > seen:
            births.extend([t] * (k - seen))
            seen = k
        if seen >= 4:
            break
    first = births[0] if births else None
    faithful = first is not None and not any(o["t"] <= first for o in other)
    return {"n": n, "births": births, "first": first, "faithful": faithful, "other": other[:5]}


def top(loops):
    """The strictly most numerous size, or None on a tie or an empty census."""
    if not loops:
        return None
    best = max(loops.values())
    tops = [int(s) for s, v in loops.items() if v == best]
    return tops[0] if len(tops) == 1 else None


def describe(loops, variants):
    """A census in words: the total, the four most numerous sizes (size: count), and the variants."""
    total = sum(loops.values())
    ranked = sorted(((int(s), v) for s, v in loops.items()), key=lambda x: (-x[1], x[0]))
    parts = ", ".join(f"{s}: {v}" for s, v in ranked[:4])
    if len(ranked) > 4:
        parts += f", {len(ranked) - 4} more sizes"
    return f"{total} loops ({parts or 'none'}); {variants} variants"


def mean_size(series, lo, hi):
    tot = cnt = 0
    for row in series:
        if lo <= row["t"] <= hi:
            for s, v in row["loops"].items():
                tot += int(s) * v
                cnt += v
    return round(tot / cnt, 2) if cnt else None


# ---------------------------------------------------------------- controls and the verdict

def drawn_census():
    """A drawn torus: loops of sizes 4 to 13 apart, a 2 x 3 rectangle ringed with sheath, a size-6 loop with one
    inner sheath site broken. The census must count the ten loops and the one variant."""
    L = 200
    g = np.zeros((L, L), dtype=np.uint8)
    y = x = 2
    for n in SIZES:
        p = build(n)
        h, w = p.shape
        if x + w + 2 > L:
            x, y = 2, y + 21
        g[y:y + h, x:x + w] = p
        x += w + 3
    g[150:154, 10:15] = 2
    g[151:153, 11:14] = 0                                       # a 2 x 3 hole ringed with sheath
    broken = build(6)
    broken[2, 4] = 1                                            # the inner sheath broken at one site
    g[150:160, 40:50] = broken
    loops, variants = census(g)
    return loops == {n: 1 for n in SIZES} and variants == 1, {"loops": loops, "variants": variants}


def conditions(tops, firsts, faithful):
    """Rule 6."""
    rising = all(firsts[a] is not None and firsts[b] is not None and firsts[a] < firsts[b]
                 for a, b in zip(SIZES, SIZES[1:]))
    return {"size 4 strictly the most numerous at the end in at least two of the three spaces":
            sum(1 for t in tops.values() if t == 4) >= 2,
            "first offspring strictly sooner the smaller the loop, from 4 to 13": rising,
            "every built loop faithful alone": all(faithful.values())}


def run(seed, inputs="inputs", results="results", spaces=SPACES, beside=BESIDE, golly_spaces=SPACES, workers=2):
    rule_text, rle_text = load(inputs, "Evoloop.rule"), load(inputs, "Evoloop.rle")
    sayama, defined = sayama_rules()
    golly, n_trans = golly_rules(rule_text)
    _TABLES["sayama"], _TABLES["golly"] = sayama.ravel(), golly.ravel()
    ancestor = read_rle(rle_text)

    # controls
    ctl = {}
    ctl["size 13 built equals the rle, site for site"] = bool(np.array_equal(build(ANCESTOR), ancestor))
    ctl["the rle's genome reads 774477777777777"] = genome_of(ancestor, ANCESTOR) == GENOME
    agree = bool(np.array_equal(golly[defined], sayama[defined]))
    differ = int(np.count_nonzero(golly != sayama))
    ctl["Golly's table agrees with Table 2 on every situation it defines"] = agree
    ctl["both rules leave the quiescent state alone"] = int(sayama[0, 0, 0, 0, 0]) == 0 == int(golly[0, 0, 0, 0, 0])
    ok, drawn = drawn_census()
    ctl["the census counts the drawn loops and variant exactly"] = ok

    jobs = [("sayama", L, ancestor) for L in spaces] + [("golly", L, ancestor) for L in golly_spaces] \
        + [("sayama", L, ancestor) for L in beside]
    ctx = mp.get_context("fork")
    with ctx.Pool(workers) as pool:
        done = pool.map(run_space, jobs)
        lone = pool.starmap(alone, [(n, _TABLES["sayama"]) for n in SIZES])
    runs = {(d["rules"], d["L"]): d for d in done}

    ends = {L: runs[("sayama", L)]["series"][-1] for L in spaces}
    tops = {L: top(ends[L]["loops"]) for L in spaces}
    firsts = {d["n"]: d["first"] for d in lone}
    faithful = {d["n"]: d["faithful"] for d in lone}
    cond = conditions(tops, firsts, faithful)

    def end_of(rules, L):
        e = runs[(rules, L)]["series"][-1]
        return e, top(e["loops"])

    values = {
        "genome": genome_of(ancestor, ANCESTOR) or "unread",
        "seed_equals_built": int(ctl["size 13 built equals the rle, site for site"]),
        "rules_compared": (f"Table 2: {len(table2_rules())} rules, {int(defined.sum())} situations with rotations, "
                           f"{'all' if agree else 'not all'} as Golly's {n_trans} transitions give them; the two rules "
                           f"differ on {differ} of 59,049 situations, all of them undefined in Table 2"
                           if agree else f"Golly's table disagrees with Table 2; {differ} situations differ"),
        "spaces_size4": sum(1 for t in tops.values() if t == 4),
        "first_offspring": "; ".join(f"{n}: {firsts[n]}" for n in SIZES) + " (updates)",
        "births_rising": int(cond["first offspring strictly sooner the smaller the loop, from 4 to 13"]),
        "faithful_alone": sum(1 for v in faithful.values() if v),
        "golly_rules": "; ".join(f"{L}: top {end_of('golly', L)[1]} "
                                 f"({max(end_of('golly', L)[0]['loops'].values(), default=0)} of "
                                 f"{sum(end_of('golly', L)[0]['loops'].values())} loops)" for L in golly_spaces),
        "other_spaces": "; ".join(f"{L}: top {end_of('sayama', L)[1]} "
                                  f"({max(end_of('sayama', L)[0]['loops'].values(), default=0)} of "
                                  f"{sum(end_of('sayama', L)[0]['loops'].values())} loops)" for L in beside),
        "mean_size": "; ".join(f"{L}: {mean_size(runs[('sayama', L)]['series'], 1000, 10000)} to "
                               f"{mean_size(runs[('sayama', L)]['series'], 41000, 50000)}" for L in spaces),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
        "test_passed": int(all(cond.values())),
    }
    for L in SPACES:
        if L in spaces:
            values[f"end_{L}"] = describe(ends[L]["loops"], ends[L]["variants"])
            values[f"top_{L}"] = tops[L] if tops[L] is not None else 0
        else:
            values[f"end_{L}"], values[f"top_{L}"] = "not run", 0
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"conditions": cond, "controls": ctl, "drawn_census": {"loops": {str(k): v for k, v in
                                                                              drawn["loops"].items()},
                                                                    "variants": drawn["variants"]},
              "alone": lone, "runs": done, "rules": {"table2_rules": len(table2_rules()),
                                                     "table2_situations": int(defined.sum()),
                                                     "golly_transitions": n_trans, "differ": differ}}
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
        sys.exit(f"evoloop: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
