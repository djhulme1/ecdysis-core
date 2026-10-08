#!/usr/bin/env python3
"""Conway's Game of Life is omniperiodic: the paper's oscillators run on the unbounded plane, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:281f07e3f1e5f956) is from Brown, Cheng,
Jacobi, Karpovich, Merzenich, Raucci and Riley, "Conway's Game of Life is Omniperiodic" (arXiv:2312.02799, 2023):
"The search has finally ended, with the discovery of oscillators having the final two periods, 19 and 41, proving
that Life is omniperiodic."

Its registered test: refuted if, under B3/S23 on the unbounded plane, the paper's p19 (cribbage) or p41 (204P41)
pattern is not a finite oscillator of exactly that period (back to itself, unshifted, after 19 or 41 generations and
not sooner, with some cell cycling at the full period, the paper's non-trivial), or if any period from 1 to 42 lacks
such an oscillator in its Gallery, or if its Snark loop construction (sides floor((p-1)/2) and ceil((p-1)/2), eight
equally spaced gliders) fails to give one for some p from 43 to 500.

The paper proves every period from 43 up by the construction; this runs it for 458 periods, a finite sample of an
infinite family, so a pass is evidence for that part of the theorem, not a proof of it.

The input is the e-print, checked against its SHA-256 and size; omniperiodicity.tex is read from it in memory, as
data. numpy only. Every rule below was fixed before any seed existed; the seed is not used, as nothing here is random.

1. Life. B3/S23 on the unbounded plane. A pattern is a finite set of live cells, held as a sorted array of cell keys,
   with no grid and so no edge. A cell is live in the next generation if it has exactly three live neighbours, or is
   live and has exactly two.
2. Oscillators. A pattern is an oscillator of exactly period p when its live cells after p generations are the same
   cells, in the same places, as at generation 0, and at no generation t with 0 < t < p. It is non-trivial when some
   cell, live at some point, has least period p over the cycle (the paper's trivial oscillators are those in which
   "no cell of the pattern oscillates at the full period"); full_cells counts those cells.
3. RLE. A run count (default 1, never 0) and then b (dead), o (live) or $ (next row); ! ends the pattern. White
   space is ignored; anything else, a count before !, text after it, no ! or no live cell refuses the pattern. Rows
   run down from the top, columns right from the left. Header sizes are not used (rule 5 compares them).
4. Figures. A figure is a \\patstack whose caption is given here (FIGURES) and whose image links to
   https://conwaylife.com/?rle=...&name=...; its pattern is that RLE. Each caption used must occur exactly once.
5. The Gallery. Every \\patcols entry after "\\section*{\\hfil Gallery \\hfil}" and before "\\printbibliography".
   Its stated period is the N of the "(pN)" its caption starts with. Its pattern is the RLE printed beside it: the
   text of its \\detokenize groups, after the header "x = W, y = H, rule = R", where R must be B3/S23. A period is
   covered when one of its entries is a non-trivial oscillator of exactly that period. Reported beside: entries whose
   link RLE differs from the printed one, cell for cell, and headers whose W x H is not the pattern's size.
6. p19 and p41. The figures "(p19) cribbage" and "(p41) 204P41" must each be a non-trivial oscillator of exactly 19
   and 41 generations. Each is compared, up to translation, with the Gallery's entry of the same period (reported).
7. The p43 Snark loop. The figure "(p43) Snark loop" must be eight gliders and four Snarks, nothing left over. A
   glider is a group of 5 cells connected by king's moves that, run alone, is the same cells moved one row and one
   column after 4 generations. A Snark is the figure "The Snark" less its gliders (what is left must be a still
   life), rotated or reflected; the cells that are not gliders must be exactly four disjoint copies. The four
   Snarks together must be unchanged by a quarter turn (up to translation), so the loop's sides are equal, and the
   figure must oscillate
   with period 43 (rule 2), so n = m = 21 (the paper's period is n + m + 1). T, R, B and L are the Snarks with the
   least mean row, greatest mean column, greatest mean row and least mean column; they must be four different ones.
8. The construction for p (the paper's proof: four Snarks as in the p43 loop, a diagonal rectangle of sides
   n = floor((p-1)/2) and m = ceil((p-1)/2), and eight equally spaced gliders). With k = n - 21 and j = m - 21: T
   stays, R moves k rows down and k columns right (along the T-R lane), B moves k + j rows down and k - j columns
   right, and L moves j rows down and j columns left (along the T-L lane). The seed glider is one of the two on the
   T-L lane, those of the figure's gliders that move up-right or down-left and whose first cell's row + column is
   below the mean of the four Snarks' mean row + mean column; the first of the two in reading order. The one-glider
   loop (the four moved Snarks and the seed) must be back to itself, unshifted, after exactly 8p generations (the
   paper's 8(n + m + 1); loops_8p counts those that are). D_i is its state at generation i * p less the Snarks
   (symmetric difference), i = 0 to 7, and the loop for p is the Snarks with D_0 to D_7 applied in turn (symmetric
   differences). A loop passes if it is a non-trivial oscillator of exactly period p. For p = 43 it must be the
   figure itself, cell for cell (loop43_equal).
9. The range: every p from 43 to 500 (458 loops), on two processes, combined in order of p.

test_passed is 1 if every period from 1 to 42 is covered, both figures of rule 6 pass, every loop passes and
loop43_equal holds, and every control below is caught; else 0.

10. Controls (each must be caught; controls_passed counts those that are): the figure "A trivial p12" is an
    oscillator of exactly period 12 with no full cell (trivial); the figure "Glider" is not back, unshifted, within
    100 generations; cribbage and 204P41, each without its first live cell in reading order, are not oscillators of
    exactly 19 and 41; the blinker is not an oscillator of exactly period 4 (it is back at 2); the loop for p = 50
    without D_7 (seven gliders) is not an oscillator of exactly period 50.

Writes results/outputs.json and results/detail.json. Run with: python3 life/check.py
"""

import hashlib
import io
import json
import multiprocessing
import os
import re
import sys
import tarfile
from concurrent.futures import ProcessPoolExecutor

import numpy as np

INPUT = ("arXiv-2312.02799v1.tar.gz", "77bef3ca853f44219819dd62f2081f4eb4492520ec7b316500795240929738d3", 335322)
TEX = "omniperiodicity.tex"
GALLERY = "\\section*{\\hfil Gallery \\hfil}"
GALLERY_END = "\\printbibliography"
FIGURES = {"p19": "(p19) cribbage", "p41": "(p41) 204P41", "loop": "(p43) Snark loop", "snark": "The Snark",
           "trivial": "A trivial p12", "glider": "Glider"}
BASE_P = 43
BASE_SIDE = 21
FIRST, LAST = 43, 500
WORKERS = 2
GLIDER_HORIZON = 100
CONTROL_LOOP = 50

OFFSET = 1 << 20
SHIFT = 1 << 21
NEIGHBOURS = np.array([dr * SHIFT + dc for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc], dtype=np.int64)
SYMMETRIES = [lambda r, c: (r, c), lambda r, c: (c, -r), lambda r, c: (-r, -c), lambda r, c: (-c, r),
              lambda r, c: (r, -c), lambda r, c: (-r, c), lambda r, c: (c, r), lambda r, c: (-c, -r)]


class Refused(Exception):
    """The input is not what the rules say it must be."""


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


# ---------------------------------------------------------------- rule 1: Life on the unbounded plane

def keys(cells):
    """The sorted keys of an iterable of (row, column)."""
    a = np.array(sorted(set(cells)), dtype=np.int64).reshape(-1, 2)
    if a.size and (np.abs(a).max() >= OFFSET - 2):
        raise Refused("a cell too far from the origin")
    return (a[:, 0] + OFFSET) * SHIFT + (a[:, 1] + OFFSET)


def cells(k):
    """(row, column) pairs of sorted keys."""
    return [(int(x) // SHIFT - OFFSET, int(x) % SHIFT - OFFSET) for x in k]


def moved(k, dr, dc):
    return k + (dr * SHIFT + dc)


def step(live):
    """One generation of B3/S23."""
    if live.size == 0:
        return live
    near, count = np.unique((live[:, None] + NEIGHBOURS).ravel(), return_counts=True)
    born = near[count == 3]
    two = near[count == 2]
    at = np.searchsorted(live, two)
    inside = at < live.size
    two, at = two[inside], at[inside]
    stay = two[live[at] == two]
    return np.sort(np.concatenate((born, stay)))


def run_for(live, generations):
    for _ in range(generations):
        live = step(live)
    return live


def same(a, b):
    return a.size == b.size and np.array_equal(a, b)


# ---------------------------------------------------------------- rule 2: oscillators

def orbit(live, limit, keep=True):
    """The first generation t, 0 < t <= limit, at which the pattern is its generation-0 self (None if none), and
    the states of generations 0 to t - 1 (or to limit) if keep."""
    states = [live]
    s = live
    for t in range(1, limit + 1):
        s = step(s)
        if same(s, live):
            return t, states
        if keep:
            states.append(s)
    return None, states


def prime_factors(n):
    out, d = [], 2
    while d * d <= n:
        if n % d == 0:
            out.append(d)
            while n % d == 0:
                n //= d
        d += 1
    if n > 1:
        out.append(n)
    return out


def full_cells(states):
    """Cells, live at some point of the cycle, whose least period is the cycle's length."""
    p = len(states)
    seen = np.unique(np.concatenate(states))
    m = np.zeros((p, seen.size), dtype=bool)
    for t, s in enumerate(states):
        m[t, np.searchsorted(seen, s)] = True
    full = np.ones(seen.size, dtype=bool)
    for q in prime_factors(p):
        full &= ~(m == np.roll(m, -(p // q), axis=0)).all(axis=0)
    return int(full.sum())


def oscillator(live, period, limit=None):
    """Rule 2: the period found within limit (default 2 * period; 0 if none), full cells, populations, and ok."""
    t, states = orbit(live, limit if limit is not None else 2 * period)
    r = {"stated": period, "period": t or 0, "full_cells": 0, "population": int(live.size)}
    if t is not None:
        r["full_cells"] = full_cells(states)
        pops = [int(s.size) for s in states]
        r["pop_min"], r["pop_max"] = min(pops), max(pops)
    r["ok"] = t == period and r["full_cells"] > 0
    return r


# ---------------------------------------------------------------- rules 3 to 5: reading the paper

RLE_TOKEN = re.compile(r"(\d*)([bo$!])")


def rle(text):
    """Rule 3: the live cells of an RLE body, as (row, column) pairs."""
    body = re.sub(r"\s+", "", text)
    out, r, c, pos = [], 0, 0, 0
    while True:
        m = RLE_TOKEN.match(body, pos)
        if not m:
            raise Refused(f"RLE: {body[pos:pos + 12]!r} is not a run" if pos < len(body) else "RLE: no !")
        count, tag = m.group(1), m.group(2)
        pos = m.end()
        if tag == "!":
            if count:
                raise Refused("RLE: a count before !")
            break
        n = int(count) if count else 1
        if n == 0:
            raise Refused("RLE: a count of 0")
        if tag == "$":
            r, c = r + n, 0
        else:
            if tag == "o":
                out.extend((r, c + i) for i in range(n))
            c += n
    if pos != len(body):
        raise Refused("RLE: text after !")
    if not out:
        raise Refused("RLE: no live cell")
    return out


def group(text, i):
    """The text inside the brace group opening at text[i], and the index after it (a backslash escapes)."""
    if i >= len(text) or text[i] != "{":
        raise Refused("a brace group was expected")
    depth, j = 0, i
    while j < len(text):
        ch = text[j]
        if ch == "\\":
            j += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1:j], j + 1
        j += 1
    raise Refused("an unclosed brace group")


def skip_space(text, i):
    while i < len(text) and text[i].isspace():
        i += 1
    return i


LINK = re.compile(r"\\href\{https://conwaylife\.com/\?rle=([^&{}]*)&name=")
HEADER = re.compile(r"\s*x\s*=\s*(\d+)\s*,\s*y\s*=\s*(\d+)\s*,\s*rule\s*=\s*(\S+)")


def link_rle(arg):
    m = LINK.search(arg)
    if not m:
        raise Refused("a figure without a conwaylife.com RLE link")
    return m.group(1)


def figure(tex, caption):
    """Rule 4: the cells of the one figure with this caption."""
    found = []
    for m in re.finditer(r"\\patstack(?:\[[^\]]*\])?\{", tex):
        cap, i = group(tex, m.end() - 1)
        if cap.strip() == caption:
            arg, _ = group(tex, skip_space(tex, i))
            found.append(link_rle(arg))
    if len(found) != 1:
        raise Refused(f"{len(found)} figures captioned {caption!r}, not 1")
    return rle(found[0])


def size(cs):
    rows = [r for r, _ in cs]
    cols = [c for _, c in cs]
    return max(cols) - min(cols) + 1, max(rows) - min(rows) + 1


def gallery(tex):
    """Rule 5: the Gallery's entries."""
    if tex.count(GALLERY) != 1:
        raise Refused("the Gallery heading is not there exactly once")
    start = tex.index(GALLERY)
    end = tex.find(GALLERY_END, start)
    if end < 0:
        raise Refused("no \\printbibliography after the Gallery")
    sec = tex[start:end]
    out = []
    for m in re.finditer(r"\\patcols\{", sec):
        cap, i = group(sec, m.end() - 1)
        link, i = group(sec, skip_space(sec, i))
        printed, _ = group(sec, skip_space(sec, i))
        pm = re.match(r"\s*\(p(\d+)\)", cap)
        if not pm:
            raise Refused(f"a Gallery caption without (pN): {cap!r}")
        texts = []
        for d in re.finditer(r"\\detokenize\{", printed):
            texts.append(group(printed, d.end() - 1)[0])
        joined = "\n".join(texts)
        hm = HEADER.match(joined)
        if not hm:
            raise Refused(f"{cap}: no RLE header")
        if hm.group(3).upper() != "B3/S23":
            raise Refused(f"{cap}: rule {hm.group(3)}")
        pattern = rle(joined[hm.end():])
        linked = rle(link_rle(link))
        out.append({"caption": cap.strip(), "stated": int(pm.group(1)), "cells": pattern,
                    "header": (int(hm.group(1)), int(hm.group(2))), "size": size(pattern),
                    "link_same": sorted(linked) == sorted(pattern)})
    return out


def normal(cs):
    """Cells moved so that the least row and the least column are 0, sorted."""
    r0 = min(r for r, _ in cs)
    c0 = min(c for _, c in cs)
    return sorted((r - r0, c - c0) for r, c in cs)


# ---------------------------------------------------------------- rule 7: the p43 loop taken apart

def components(cs):
    """Groups of cells connected by king's moves, each sorted, in reading order of their first cells."""
    left = set(cs)
    out = []
    while left:
        first = min(left)
        stack, part = [first], {first}
        left.discard(first)
        while stack:
            r, c = stack.pop()
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    x = (r + dr, c + dc)
                    if x in left:
                        left.discard(x)
                        part.add(x)
                        stack.append(x)
        out.append(sorted(part))
    return sorted(out)


def glider_direction(cs):
    """(dr, dc) if these cells, run alone, are the same cells moved one row and one column after 4 generations."""
    if len(cs) != 5:
        return None
    k = keys(cs)
    after = run_for(k, 4)
    for dr in (-1, 1):
        for dc in (-1, 1):
            if same(after, moved(k, dr, dc)):
                return dr, dc
    return None


def snark_shape(tex):
    cs = figure(tex, FIGURES["snark"])
    gliders = {x for g in components(cs) if glider_direction(g) for x in g}
    still = sorted(set(cs) - gliders)
    if not gliders or not same(step(keys(still)), keys(still)):
        raise Refused("the Snark less its gliders is not a still life")
    return still


def place(rest, shape):
    """Every placement of the shape, rotated or reflected, inside the set rest."""
    found = set()
    for f in SYMMETRIES:
        v = normal([f(r, c) for r, c in shape])
        a = v[0]
        for x in rest:
            dr, dc = x[0] - a[0], x[1] - a[1]
            cand = frozenset((r + dr, c + dc) for r, c in v)
            if cand <= rest:
                found.add(cand)
    return found


def mean(cs):
    return sum(r for r, _ in cs) / len(cs), sum(c for _, c in cs) / len(cs)


def take_apart(tex):
    """Rule 7: the four Snarks (T, R, B, L) and the seed glider of the p43 loop, and the figure's cells."""
    loop = figure(tex, FIGURES["loop"])
    parts = components(loop)
    gliders = [(g, glider_direction(g)) for g in parts]
    gliders = [(g, d) for g, d in gliders if d]
    if len(gliders) != 8:
        raise Refused(f"the p43 loop has {len(gliders)} gliders, not 8")
    rest = set(loop) - {x for g, _ in gliders for x in g}
    snarks = place(rest, snark_shape(tex))
    if len(snarks) != 4 or set().union(*snarks) != rest or sum(len(s) for s in snarks) != len(rest):
        raise Refused(f"the cells that are not gliders are not four disjoint Snarks ({len(snarks)} placements)")
    snarks = [sorted(s) for s in snarks]
    allsn = [x for s in snarks for x in s]
    if normal([(c, -r) for r, c in allsn]) != normal(allsn):
        raise Refused("the four Snarks are not unchanged by a quarter turn")
    means = [mean(s) for s in snarks]
    named = {"T": min(range(4), key=lambda i: means[i][0]), "R": max(range(4), key=lambda i: means[i][1]),
             "B": max(range(4), key=lambda i: means[i][0]), "L": min(range(4), key=lambda i: means[i][1])}
    if len(set(named.values())) != 4:
        raise Refused("T, R, B and L are not four different Snarks")
    centre = sum(m[0] + m[1] for m in means) / 4
    lane = [g for g, (dr, dc) in gliders if dr == -dc and g[0][0] + g[0][1] < centre]
    if len(lane) != 2:
        raise Refused(f"{len(lane)} gliders on the T-L lane, not 2")
    return {s: keys(snarks[i]) for s, i in named.items()}, keys(min(lane)), keys(loop)


# ---------------------------------------------------------------- rule 8: the construction

def sides(p):
    return (p - 1) // 2, p // 2


def build(p, snarks, seed):
    """The four moved Snarks, and the states D_0 to D_7 (or fewer if the one-glider loop comes back early)."""
    n, m = sides(p)
    k, j = n - BASE_SIDE, m - BASE_SIDE
    shift = {"T": (0, 0), "R": (k, k), "B": (k + j, k - j), "L": (j, -j)}
    still = np.sort(np.concatenate([moved(snarks[s], *shift[s]) for s in "TRBL"]))
    if np.unique(still).size != still.size:
        raise Refused(f"p = {p}: the moved Snarks overlap")
    start = np.union1d(still, seed)
    s, diffs, back = start, [], None
    for t in range(8 * p):
        if t % p == 0:
            diffs.append(np.setxor1d(s, still))
        s = step(s)
        if same(s, start):
            back = t + 1
            break
    return still, diffs, back


def compose(still, diffs):
    out = still
    for d in diffs:
        out = np.setxor1d(out, d)
    return out


def check_loop(p, snarks, seed):
    still, diffs, back = build(p, snarks, seed)
    n, m = sides(p)
    row = {"p": p, "n": n, "m": m, "one_glider_back": back or 0}
    if back != 8 * p:
        row.update(ok=False, period=0, full_cells=0, population=0)
        return row
    loop = compose(still, diffs)
    r = oscillator(loop, p, limit=p)
    row.update(ok=r["ok"], period=r["period"], full_cells=r["full_cells"], population=int(loop.size))
    return row


def check_loops(ps, snarks, seed):
    return [check_loop(p, snarks, seed) for p in ps]


# ---------------------------------------------------------------- the run

def without_first(cs):
    return keys(sorted(cs)[1:])


def run(inputs="inputs", results="results", workers=WORKERS, last=LAST, log=None):
    say = log or (lambda s: None)
    tex = load(inputs)

    entries = gallery(tex)
    rows, covered = [], set()
    for e in entries:
        r = oscillator(keys(e["cells"]), e["stated"])
        if r["ok"]:
            covered.add(e["stated"])
        rows.append({"caption": e["caption"], "header": list(e["header"]), "size": list(e["size"]),
                     "link_same": e["link_same"], **r})
    missing = [p for p in range(1, 43) if p not in covered]
    say(f"Gallery: {len(entries)} entries, {len(covered & set(range(1, 43)))} of 42 periods covered")

    new = {}
    for key, period in (("p19", 19), ("p41", 41)):
        cs = figure(tex, FIGURES[key])
        r = oscillator(keys(cs), period)
        twins = [e for e in entries if e["stated"] == period]
        r["same_as_gallery"] = any(normal(e["cells"]) == normal(cs) for e in twins)
        new[key] = r
        say(f"{key}: period {r['period']}, full cells {r['full_cells']}, ok {r['ok']}")

    snarks, seed, figure43 = take_apart(tex)
    base = check_loop(BASE_P, snarks, seed)
    still, diffs, back = build(BASE_P, snarks, seed)
    loop43_equal = back == 8 * BASE_P and same(compose(still, diffs), figure43)
    figure43_r = oscillator(figure43, BASE_P, limit=BASE_P)
    say(f"p43: figure period {figure43_r['period']}, rebuilt equal {loop43_equal}, rebuilt ok {base['ok']}")
    if figure43_r["period"] != BASE_P:
        raise Refused("the p43 loop figure does not oscillate with period 43")

    ps = list(range(FIRST, last + 1))
    if workers > 1:
        ctx = multiprocessing.get_context("fork")
        with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as pool:
            parts = list(pool.map(check_loops, [ps[i::workers] for i in range(workers)],
                                  [snarks] * workers, [seed] * workers))
        loops = sorted((x for part in parts for x in part), key=lambda x: x["p"])
    else:
        loops = check_loops(ps, snarks, seed)
    failed = [x["p"] for x in loops if not x["ok"]]
    say(f"loops: {len(loops)} checked, {len(loops) - len(failed)} passed")

    controls = []
    trivial = oscillator(keys(figure(tex, FIGURES["trivial"])), 12)
    controls.append({"control": "the trivial p12 is trivial", "result": trivial,
                     "caught": trivial["period"] == 12 and trivial["full_cells"] == 0 and not trivial["ok"]})
    t, _ = orbit(keys(figure(tex, FIGURES["glider"])), GLIDER_HORIZON, keep=False)
    controls.append({"control": f"the glider is not back within {GLIDER_HORIZON}", "back": t or 0,
                     "caught": t is None})
    for key, period in (("p19", 19), ("p41", 41)):
        r = oscillator(without_first(figure(tex, FIGURES[key])), period, limit=period)
        controls.append({"control": f"{FIGURES[key]} without its first cell", "result": r, "caught": not r["ok"]})
    r = oscillator(keys(rle("3o!")), 4)
    controls.append({"control": "the blinker is not exactly p4", "result": r, "caught": not r["ok"]})
    still, diffs, back = build(CONTROL_LOOP, snarks, seed)
    r = oscillator(compose(still, diffs[:-1]), CONTROL_LOOP, limit=CONTROL_LOOP)
    controls.append({"control": f"the p{CONTROL_LOOP} loop without D_7", "result": r, "caught": not r["ok"]})
    caught = sum(1 for c in controls if c["caught"])
    say(f"controls: {caught} of {len(controls)}")

    passed = (not missing and new["p19"]["ok"] and new["p41"]["ok"] and not failed and loop43_equal
              and caught == len(controls))
    out = {
        "gallery_entries": len(entries),
        "gallery_covered": len(covered & set(range(1, 43))),
        "gallery_missing": len(missing),
        "link_mismatches": sum(1 for e in entries if not e["link_same"]),
        "header_mismatches": sum(1 for e in entries if e["header"] != e["size"]),
        "p19_period": new["p19"]["period"], "p19_full_cells": new["p19"]["full_cells"],
        "p19_same_as_gallery": int(new["p19"]["same_as_gallery"]),
        "p41_period": new["p41"]["period"], "p41_full_cells": new["p41"]["full_cells"],
        "p41_same_as_gallery": int(new["p41"]["same_as_gallery"]),
        "loop43_equal": int(loop43_equal),
        "loops_checked": len(loops),
        "loops_passed": len(loops) - len(failed),
        "loops_8p": sum(1 for x in loops if x["one_glider_back"] == 8 * x["p"]),
        "loops_first_failure": failed[0] if failed else 0,
        "controls_passed": caught, "controls_total": len(controls),
        "test_passed": int(passed),
    }
    detail = {"input": {"name": INPUT[0], "sha256": INPUT[1], "bytes": INPUT[2], "tex": TEX},
              "gallery": rows, "missing": missing, "figures": new,
              "p43": {"figure": figure43_r, "rebuilt": base, "rebuilt_equal": loop43_equal,
                      "snark_cells": {s: int(v.size) for s, v in snarks.items()}, "seed": cells(seed)},
              "loops": loops, "controls": controls}
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
        out, _ = run(log=lambda s: print(s, file=sys.stderr, flush=True))
    except Refused as e:
        sys.exit(f"life/check.py: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
