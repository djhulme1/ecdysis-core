#!/usr/bin/env python3
"""Korže and Vesel (2014): the packing chromatic number of the hexagonal lattice is 7, by their digraph D6 of the
packing 6-colourings of a small piece of the lattice, rebuilt and searched as the paper describes it.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from D. Korže and A. Vesel, "On the packing
chromatic number of square and hexagonal lattice", Ars Mathematica Contemporanea 7 (2014) 13–22 (CC BY), its
abstract: "We show that the packing chromatic number for the hexagonal lattice ℋ is 7." A packing k-colouring gives
every vertex a colour in 1..k so that two vertices of colour i are more than i apart. The paper cites the upper
bound, a packing 7-colouring, from Fiala, Klavžar and Lidický (European J. Combin. 30 (2009) 1101–1113, not open,
so its colouring is not read here) and proves the lower bound by computer (Section 2): H1 is the piece of the
lattice its Fig. 1 draws, with four ports a side (u, v, z, w on the left and u', v', z', w' on the right); H_i is
i copies of H1 in a row, the u', v', w', z' of each copy joined to the u, v, w, z of the next; D_k has the packing
k-colourings of H1 as its vertices and an arc from a to b when a on the first copy and b on the second are a
packing k-colouring of H2. A packing colouring of the lattice restricts to one of H_i, and so to a walk of D_k on i
vertices; with D6 acyclic and d its longest path, H_(d+2) has no packing 6-colouring and the lattice, which contains
it, has none (Lemmas 2.1 and 2.2, Theorem 2.3; Lemma 2.1 adds, for k <= 6, that copies two apart are at least 7
apart, so the walks are exactly the colourings). The paper reports D6 with 26,660 vertices, a largest out-degree of
37 and no cycle.

No data of record: the claim is a construction. H1 is transcribed below from Fig. 1 (the paper's PDF, read as page
images), and everything else is computed. Standard library, and C (packing/kvsearch.c, built into the results
directory with gcc at run time, called through ctypes) for the backtracking. Every rule below was fixed before any
packing colouring of H1, H2 or the lattice was computed; the tests exercise the machinery on other graphs (paths,
a chain of hexagons, small random graphs).

Coordinates: a vertex of the lattice is (X, Y), X counting half-widths of a hexagon to the right and Y the vertex rows
downwards (Fig. 1's pointy-topped hexagons); (X, Y) is a vertex when X is even for Y = 0, 3 (mod 4) and odd for
Y = 1, 2 (mod 4); its edges join (X, 2m) to (X +- 1, 2m + 1) and (X, 2m + 1) to (X, 2m + 2), three to a vertex, and
every edge joins an even row to an odd one. H1 as Fig. 1 draws it: six hexagons in three rows of two, the middle row
half a hexagon to the left, and the pendants u and w:

    u = (0,0)   (2,0)   (4,0)
        (1,1)   (3,1)   (5,1) = u'
        (1,2)   (3,2)   (5,2) = v'
    v = (0,3)   (2,3)   (4,3)
    z = (0,4)   (2,4)   (4,4)
        (1,5)   (3,5)   (5,5) = z'
        (1,6)   (3,6)   (5,6) = w'
    w = (0,7)   (2,7)   (4,7)

24 vertices and the lattice edges among them (the figure draws 29, and no other). The next copy is H1 moved by
(6, 0), three hexagons to the right, which makes u'u, v'v, z'z and w'w lattice edges (u of the next copy at (6, 0),
next to u' at (5, 1), and so on), as Fig. 2 draws H2; H_i is the subgraph of the lattice induced by its copies.

The rules:
1. D_k: its vertices are the packing k-colourings of H1, distances taken in H1 (the paper's definition); an arc from
   a to b when the colouring of H2 that gives the first copy a and the second b is a packing k-colouring of H2,
   distances taken in H2, a = b included (the paper writes its definition for distinct vertices, but its Lemma 2.2
   needs every closed walk, a loop among them).
2. The test (TEST), four conditions, all needed: H1 as stated (24 lattice vertices, 29 edges, the four joins lattice
   edges, and H2 exactly the two copies' 58 edges and the four joins); vertices of copies two or more apart in H_i at
   least 7 apart (in H_max(4, d+2), distances in it); D6 without a directed cycle, a loop included; and a direct
   search (packing/kvsearch.c on the vertices of H_(d+2), column by column from the left, independent of D6) finding
   no packing 6-colouring of H_(d+2) within BUDGET assignments.

Beside the test, none of it counted: D6's size against the printed 26,660 vertices and largest out-degree 37; its
arcs, loops, largest in-degree, sources and sinks; d and the number of packing 6-colourings of H_i (walks of D6 on i
vertices) for i = 1 to d + 2; whether the direct search was exhausted or stopped at its budget; and the upper bound:
a packing 7-colouring of the lattice built here, colour 1 on the even rows (one class of the bipartition) and, on the
odd rows, a triangular lattice in which two vertices t apart are 2t apart in the hexagonal lattice: colours 2 and 3
on two classes of its proper 3-colouring and colours 4 to 7 on the four cosets of twice the third class, checked as a
packing colouring on a patch of the lattice that holds whole periods with a margin of 8 (densities 1/2, 1/6, 1/6
and 1/24 each).

Controls (controls_passed counts those that behave as stated): the packing 6-colourings of H1 counted by the C search
and by a separate Python backtracking agree; the packing 6-colourings of H2 and of H3 counted by the C search equal
D6's walks on 2 and 3 vertices (the arcs, and Lemma 2.1); D5, built the same way, is acyclic (Brešar, Klavžar and
Rall's lower bound 6); the same method on the infinite path, tiles of 4 vertices, gives an acyclic D2 and a D3 with a
cycle (the path's packing chromatic number is 3); and the 7-colouring's check catches one vertex recoloured.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 packing/kv2014.py
"""

import ctypes
import json
import os
import re
import subprocess
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
SHIFT = 6
K = 6
BUDGET = 2_000_000_000
H1_POINTS = ((0, 0), (2, 0), (4, 0), (1, 1), (3, 1), (5, 1), (1, 2), (3, 2), (5, 2), (0, 3), (2, 3), (4, 3),
             (0, 4), (2, 4), (4, 4), (1, 5), (3, 5), (5, 5), (1, 6), (3, 6), (5, 6), (0, 7), (2, 7), (4, 7))
PORTS = {"u": (0, 0), "v": (0, 3), "z": (0, 4), "w": (0, 7), "u'": (5, 1), "v'": (5, 2), "z'": (5, 5), "w'": (5, 6)}
JOINS = (("u'", "u"), ("v'", "v"), ("z'", "z"), ("w'", "w"))
H1_EDGES = 29
PRINTED = {"vertices": 26660, "max_out": 37}
PATCH = (12, 36, 8)          # the 7-colouring's check: inner square [12, 36)^2, margin 8
PLANTED = (13, 13)           # the vertex the control recolours
TEST = ("Refuted if, with H1 as Fig. 1 draws it (24 vertices, 29 edges of the hexagonal lattice; ports u, v, z, w and "
        "u', v', z', w') and H_i as i copies joined by u'u, v'v, z'z, w'w, the digraph D6 (vertices the packing "
        "6-colourings of H1, an arc from a to b where together they pack-colour H2, loops included) has a directed "
        "cycle; or vertices of non-consecutive copies of H_i lie less than 7 apart; or a direct search finds a "
        "packing 6-colouring of H_(d+2), d the longest path of D6.")
OUTPUTS = ("h1", "gap", "d6_vertices", "d6_arcs", "d6_loops", "max_out", "max_in", "acyclic", "longest_path",
           "walks", "direct", "printed", "upper", "d5", "path", "h2_h3", "conditions_met", "conditions_total",
           "test_passed", "controls_passed", "controls_total")


class Refused(Exception):
    pass


# ----------------------------------------------------------------------------------------------- the lattice

def is_vertex(p):
    X, Y = p
    return (X % 2 == 0) == (Y % 4 in (0, 3))


def lattice_neighbours(p):
    """The three neighbours of a lattice vertex."""
    X, Y = p
    if Y % 2 == 0:
        out = [(X - 1, Y + 1), (X + 1, Y + 1), (X, Y - 1)]
    else:
        out = [(X - 1, Y - 1), (X + 1, Y - 1), (X, Y + 1)]
    return [q for q in out if is_vertex(q)]


def induced(points):
    """The lattice edges among the points (an induced subgraph): {point: set(neighbours)}."""
    s = set(points)
    return {p: {q for q in lattice_neighbours(p) if q in s} for p in points}


def n_edges(adj):
    return sum(len(v) for v in adj.values()) // 2


def strip(i, tile=H1_POINTS, shift=(SHIFT, 0)):
    """i copies of the tile moved by shift * j, and which copy each vertex belongs to."""
    pts, copy = [], {}
    for j in range(i):
        for (X, Y) in tile:
            p = (X + shift[0] * j, Y + shift[1] * j)
            pts.append(p)
            copy[p] = j
    return pts, copy


def bfs(adj, src, depth=None):
    d = {src: 0}
    q = deque([src])
    while q:
        u = q.popleft()
        if depth is not None and d[u] == depth:
            continue
        for v in adj[u]:
            if v not in d:
                d[v] = d[u] + 1
                q.append(v)
    return d


def distances(adj, order):
    return {p: bfs(adj, p) for p in order}


def check_h1():
    """H1 as stated: 24 distinct lattice vertices, 29 edges, the joins lattice edges, and H2 nothing but the two
    copies' edges and the four joins."""
    pts = list(H1_POINTS)
    ok_pts = len(set(pts)) == 24 and all(is_vertex(p) for p in pts)
    adj = induced(pts)
    edges = n_edges(adj)
    deg = {name: len(adj[p]) for name, p in PORTS.items()}
    joins = all((PORTS[b][0] + SHIFT, PORTS[b][1]) in lattice_neighbours(PORTS[a]) for a, b in JOINS)
    h2, _ = strip(2)
    h2_edges = n_edges(induced(h2))
    ok = ok_pts and edges == H1_EDGES and joins and h2_edges == 2 * H1_EDGES + len(JOINS) and len(set(h2)) == 48
    return ok, {"points": len(set(pts)), "lattice_vertices": ok_pts, "edges": edges, "port_degrees": deg,
                "joins_are_lattice_edges": joins, "h2_edges": h2_edges}


def gap_two_apart(pts, copy, adj):
    """The least distance (in the graph adj) between vertices of copies two or more apart; None if none is
    reachable."""
    gap = None
    for p in pts:
        for q, dd in bfs(adj, p).items():
            if copy[q] >= copy[p] + 2 and (gap is None or dd < gap):
                gap = dd
    return gap


# ----------------------------------------------------------------------------------------------- the search

def build(results):
    lib = os.path.join(os.path.abspath(results), "libkvsearch.so")
    subprocess.run(["gcc", "-O2", "-shared", "-fPIC", "-o", lib, os.path.join(HERE, "kvsearch.c")], check=True)
    return lib


class Search:
    def __init__(self, lib):
        self.lib = ctypes.CDLL(lib)
        ip = ctypes.POINTER(ctypes.c_int)
        self.lib.search.argtypes = [ctypes.c_int, ctypes.c_int, ip, ip, ctypes.c_int64, ctypes.c_int64,
                                    ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int64, ctypes.POINTER(ctypes.c_int64)]
        self.lib.search.restype = ctypes.c_int

    def run(self, order, dist, k, cap=0, budget=0, keep=0):
        """Packing k-colourings of the graph whose vertices are order (coloured in that order) and whose distances
        are dist ({p: {q: d}}, q absent when unreachable). Returns (status, found, nodes, the first keep solutions as
        tuples of colours in order); status 0 exhausted, 1 stopped at cap, 2 stopped at the budget."""
        n = len(order)
        pos = {p: i for i, p in enumerate(order)}
        off, idx = [0], []
        for i, p in enumerate(order):
            dp = dist[p]
            later = [(dp[q], pos[q]) for q in order[i + 1:] if q in dp]
            for c in range(1, k + 1):
                idx += [j for dd, j in later if dd <= c]
                off.append(len(idx))
        OFF = (ctypes.c_int * len(off))(*off)
        IDX = (ctypes.c_int * max(1, len(idx)))(*idx)
        buf = (ctypes.c_ubyte * max(1, n * keep))()
        res = (ctypes.c_int64 * 2)()
        status = self.lib.search(n, k, OFF, IDX, cap, budget, buf, keep, res)
        if status < 0:
            raise Refused("the search could not allocate")
        got = min(res[0], keep)
        sols = [tuple(buf[s * n:(s + 1) * n]) for s in range(got)]
        return status, res[0], res[1], sols

    def all_colourings(self, order, dist, k):
        st, n, _, _ = self.run(order, dist, k)
        if st != 0:
            raise Refused("a count was not exhausted")
        st, n2, _, sols = self.run(order, dist, k, keep=n)
        if st != 0 or n2 != n or len(sols) != n:
            raise Refused("the colourings did not come back as counted")
        return sols


def py_count(order, dist, k):
    """A separate backtracking (pure Python, checking backwards against the vertices already coloured) that counts
    the packing k-colourings, for the control on H1."""
    n = len(order)
    near = [[[j for j in range(i) if order[j] in dist[order[i]] and dist[order[i]][order[j]] <= c]
             for c in range(k + 1)] for i in range(n)]
    colour = [0] * n
    count = 0

    def rec(i):
        nonlocal count
        if i == n:
            count += 1
            return
        for c in range(1, k + 1):
            if all(colour[j] != c for j in near[i][c]):
                colour[i] = c
                rec(i + 1)
        colour[i] = 0
    rec(0)
    return count


# ----------------------------------------------------------------------------------------------- D_k

def build_dk(search, tile, shift, k, nbr):
    """D_k for a tile (a list of points) and its translate by shift: (colourings, arcs as lists of indices, loops).
    nbr(points) gives the adjacency the points induce."""
    t1 = sorted(tile)
    sols = search.all_colourings(t1, distances(nbr(t1), t1), k)
    t2 = [(X + shift[0], Y + shift[1]) for (X, Y) in t1]
    both = t1 + t2
    d2 = distances(nbr(both), both)
    n, N = len(t1), len(sols)

    def within(ta, tb, i, j):
        return tb[j] in d2[ta[i]] and d2[ta[i]][tb[j]] <= k

    # a colouring as the first copy and as the second, within its copy, under H2's distances (they can be shorter)
    tight1 = [(i, j, d2[t1[i]][t1[j]]) for i in range(n) for j in range(i + 1, n) if within(t1, t1, i, j)]
    tight2 = [(i, j, d2[t2[i]][t2[j]]) for i in range(n) for j in range(i + 1, n) if within(t2, t2, i, j)]
    valid1 = [all(not (a[i] == a[j] and a[i] >= dd) for i, j, dd in tight1) for a in sols]
    valid2 = [all(not (a[i] == a[j] and a[i] >= dd) for i, j, dd in tight2) for a in sols]
    # for each vertex y of the second copy, the vertices x of the first within k of it
    cross = [[(x, d2[t1[x]][t2[y]]) for x in range(n) if within(t1, t2, x, y)] for y in range(n)]
    # bitsets over the colourings: S[y][c] holds the colourings with colour c at vertex y
    S = [[0] * (k + 1) for _ in range(n)]
    for s, b in enumerate(sols):
        for y in range(n):
            S[y][b[y]] |= 1 << s
    v2bits = 0
    for s in range(N):
        if valid2[s]:
            v2bits |= 1 << s
    arcs = []
    for s, a in enumerate(sols):
        if not valid1[s]:
            arcs.append([])
            continue
        bad = 0
        for y in range(n):
            for c in {a[x] for x, dd in cross[y] if a[x] >= dd}:
                bad |= S[y][c]
        good = v2bits & ~bad
        out = []
        while good:
            low = good & -good
            out.append(low.bit_length() - 1)
            good ^= low
        arcs.append(out)
    loops = sum(1 for s in range(N) if s in arcs[s])
    return sols, arcs, loops


def topo(arcs):
    """Kahn's algorithm. Returns (acyclic, longest path in arcs or None, walks on i vertices for i = 1 .. d + 2 or
    None, in-degrees). A loop is a cycle."""
    N = len(arcs)
    indeg = [0] * N
    for s in range(N):
        for t in arcs[s]:
            indeg[t] += 1
    deg = indeg[:]
    q = deque(s for s in range(N) if deg[s] == 0)
    order = []
    while q:
        s = q.popleft()
        order.append(s)
        for t in arcs[s]:
            deg[t] -= 1
            if deg[t] == 0:
                q.append(t)
    if len(order) != N:
        return False, None, None, indeg
    longest = [0] * N
    for s in order:
        for t in arcs[s]:
            if longest[s] + 1 > longest[t]:
                longest[t] = longest[s] + 1
    d = max(longest) if N else 0
    walks, w = [], [1] * N
    for _ in range(d + 2):
        walks.append(sum(w))
        nw = [0] * N
        for s in range(N):
            if w[s]:
                for t in arcs[s]:
                    nw[t] += w[s]
        w = nw
    return True, d, walks, indeg


# ----------------------------------------------------------------------------------------------- the upper bound

def tri(p):
    """Triangular coordinates (i, j) of an odd-row vertex: X = 1 + 2i + j, Y = 2j + 1. Two odd-row vertices with a
    common neighbour differ by (+-1, 0), (0, +-1) or +-(1, -1)."""
    X, Y = p
    j = (Y - 1) // 2
    i = (X - 1 - j) // 2
    assert Y % 2 == 1 and X == 1 + 2 * i + j
    return i, j


def tri_distance(a, b):
    di, dj = b[0] - a[0], b[1] - a[1]
    return (abs(di) + abs(dj) + abs(di + dj)) // 2


def seven_colouring(p):
    """The packing 7-colouring built here: colour 1 on even rows; on odd rows, colours 2 and 3 where (i - j) mod 3 is
    1 or 2; where it is 0, (i, j) = a f1 + b f2 with f1 = (1, 1) and f2 = (-1, 2), and colours 4 to 7 by
    (a mod 2, b mod 2)."""
    if p[1] % 2 == 0:
        return 1
    i, j = tri(p)
    r = (i - j) % 3
    if r:
        return 1 + r
    b = (j - i) // 3          # a - b = i, a + 2b = j
    a = i + b
    return 4 + (a % 2) + 2 * (b % 2)


def hex_patch(lo, hi, margin):
    """The vertices of [lo, hi)^2 and the adjacency of [lo - margin, hi + margin)^2: for a vertex of the inner square,
    distances up to margin in the patch are its distances in the lattice (a step moves X and Y by at most 1)."""
    pts = [(X, Y) for X in range(lo - margin, hi + margin) for Y in range(lo - margin, hi + margin)
           if is_vertex((X, Y))]
    inner = [p for p in pts if lo <= p[0] < hi and lo <= p[1] < hi]
    return inner, induced(pts)


def check_colouring(colour, k, inner, adj):
    """Every vertex of inner against every vertex within k of it (BFS in adj, depth k). Returns (ok, pairs checked,
    the first violation or None)."""
    checked = 0
    for p in inner:
        c = colour(p)
        if not 1 <= c <= k:
            return False, checked, (p, c)
        for q, dd in bfs(adj, p, k).items():
            if q == p:
                continue
            if colour(q) == c and dd <= c:
                return False, checked, (p, q, c, dd)
            checked += 1
    return True, checked, None


# ----------------------------------------------------------------------------------------------- the run

def path_nbr(points):
    s = set(points)
    return {p: {q for q in ((p[0] - 1, p[1]), (p[0] + 1, p[1])) if q in s} for p in points}


def listed(prefix, values, limit=200):
    """prefix and the values joined by commas, cut at the last whole value that fits in limit characters."""
    text = prefix + ", ".join(str(v) for v in values)
    if len(text) <= limit:
        return text
    cut = text[:limit - 4]
    return cut[:cut.rfind(",")] + " ..."


def yes(b):
    return "yes" if b else "no"


def run(results="results", budget=BUDGET):
    os.makedirs(results, exist_ok=True)
    search = Search(build(results))
    cond, controls, detail = {}, {}, {}
    # 1. H1 and the joins
    ok_h1, h1d = check_h1()
    detail["h1"] = h1d
    cond["H1 as stated, and H2 its two copies and the four joins"] = ok_h1
    # 2. D6
    sols, arcs, loops = build_dk(search, H1_POINTS, (SHIFT, 0), K, induced)
    acyclic, d, walks, indeg = topo(arcs)
    narcs = sum(len(a) for a in arcs)
    max_out = max(len(a) for a in arcs)
    detail["d6"] = {"vertices": len(sols), "arcs": narcs, "loops": loops, "max_out": max_out, "max_in": max(indeg),
                    "sources": sum(1 for x in indeg if x == 0), "sinks": sum(1 for a in arcs if not a),
                    "acyclic": acyclic, "longest_path": d, "walks": walks}
    cond["D6 has no directed cycle, loops included"] = acyclic and loops == 0
    # 3. the gap between non-consecutive copies, in H_max(4, d+2)
    m = max(4, (d or 0) + 2)
    pts, copy = strip(m)
    gap = gap_two_apart(pts, copy, induced(pts))
    detail["gap"] = {"strip": m, "least_distance_two_copies_apart": gap}
    cond["vertices of copies two or more apart at least 7 apart"] = gap is not None and gap >= 7
    # 4. the direct search on H_(d+2)
    if acyclic:
        order2 = sorted(strip(d + 2)[0])
        st, nsol, nodes, _ = search.run(order2, distances(induced(order2), order2), K, cap=1, budget=budget)
        detail["direct"] = {"strip": d + 2, "vertices": len(order2), "status": ["exhausted", "found", "budget"][st],
                            "found": nsol, "nodes": nodes, "budget": budget}
        cond["a direct search finds no packing 6-colouring of H_(d+2)"] = nsol == 0
    else:
        detail["direct"] = {"status": "not run: D6 has a cycle"}
        cond["a direct search finds no packing 6-colouring of H_(d+2)"] = False
    # beside: the upper bound
    inner, adj = hex_patch(*PATCH)
    ok7, checked7, bad7 = check_colouring(seven_colouring, 7, inner, adj)
    counts7 = {c: sum(1 for p in inner if seven_colouring(p) == c) for c in range(1, 8)}
    detail["upper"] = {"ok": ok7, "pairs": checked7, "violation": bad7, "inner_vertices": len(inner),
                       "counts": counts7}
    # controls
    t1 = sorted(H1_POINTS)
    controls["the packing 6-colourings of H1: the C search and a Python backtracking agree"] = (
        py_count(t1, distances(induced(t1), t1), K) == len(sols))
    counts = {}
    for i in (2, 3):
        o = sorted(strip(i)[0])
        st_i, n_i, _, _ = search.run(o, distances(induced(o), o), K)
        counts[i] = n_i if st_i == 0 else None
    w2 = walks[1] if walks else narcs
    w3 = walks[2] if walks and len(walks) > 2 else None
    detail["h2_h3"] = {"h2_colourings": counts[2], "h3_colourings": counts[3], "walks2": w2, "walks3": w3}
    controls["the packing 6-colourings of H2 and H3 equal D6's walks on 2 and 3 vertices"] = (
        counts[2] == w2 and w3 is not None and counts[3] == w3)
    sols5, arcs5, loops5 = build_dk(search, H1_POINTS, (SHIFT, 0), 5, induced)
    ac5, d5, _, _ = topo(arcs5)
    detail["d5"] = {"vertices": len(sols5), "arcs": sum(len(a) for a in arcs5), "loops": loops5, "acyclic": ac5,
                    "longest_path": d5}
    controls["D5 is acyclic (Brešar, Klavžar and Rall's lower bound 6)"] = ac5
    tile = [(x, 0) for x in range(4)]
    path = {}
    for kk in (2, 3):
        s_k, a_k, l_k = build_dk(search, tile, (4, 0), kk, path_nbr)
        ac_k, _, _, _ = topo(a_k)
        path[kk] = {"vertices": len(s_k), "arcs": sum(len(a) for a in a_k), "loops": l_k, "acyclic": ac_k}
    detail["path"] = path
    controls["on the path, tiles of 4: D2 is acyclic and D3 has a cycle (packing chromatic number 3)"] = (
        path[2]["acyclic"] and not path[3]["acyclic"])

    def planted(p):
        return 2 if p == PLANTED else seven_colouring(p)
    okp, _, badp = check_colouring(planted, 7, inner, adj)
    detail["planted"] = {"vertex": PLANTED, "caught": not okp, "violation": badp}
    controls["the 7-colouring's check catches one vertex recoloured"] = (not okp) and PLANTED in inner
    # outputs
    dd_ = detail["direct"]
    out = {
        "h1": (f"{h1d['points']} vertices, {h1d['edges']} edges, all of the lattice: {yes(h1d['lattice_vertices'])}; "
               f"joins lattice edges: {yes(h1d['joins_are_lattice_edges'])}; H2 edges {h1d['h2_edges']}"),
        "gap": gap if gap is not None else -1,
        "d6_vertices": len(sols), "d6_arcs": narcs, "d6_loops": loops, "max_out": max_out, "max_in": max(indeg),
        "acyclic": int(acyclic), "longest_path": d if d is not None else -1,
        "walks": listed("packing 6-colourings of H_i, i = 1..d+2: ", walks) if walks else "D6 has a cycle",
        "direct": (f"H_{dd_['strip']} ({dd_['vertices']} vertices): {dd_['status']}, {dd_['found']} found, "
                   f"{dd_['nodes']} assignments") if acyclic else "not run",
        "printed": (f"26,660 vertices as printed: {yes(len(sols) == PRINTED['vertices'])}; largest out-degree 37 as "
                    f"printed: {yes(max_out == PRINTED['max_out'])}"),
        "upper": (f"the 7-colouring built here packs the patch: {yes(ok7)} ({checked7} pairs within 7 of "
                  f"{len(inner)} vertices checked)"),
        "d5": f"D5: {len(sols5)} vertices, {detail['d5']['arcs']} arcs, {loops5} loops, acyclic: {yes(ac5)}",
        "path": (f"path tiles of 4: D2 {path[2]['vertices']} vertices, acyclic {yes(path[2]['acyclic'])}; "
                 f"D3 {path[3]['vertices']} vertices, acyclic {yes(path[3]['acyclic'])}"),
        "h2_h3": f"H2: {counts[2]} colourings, walks {w2}; H3: {counts[3]} colourings, walks {w3}",
    }
    out["conditions_met"] = sum(1 for v in cond.values() if v)
    out["conditions_total"] = len(cond)
    out["test_passed"] = int(all(cond.values()))
    out["controls_passed"] = sum(1 for v in controls.values() if v)
    out["controls_total"] = len(controls)
    assert set(out) == set(OUTPUTS), sorted(set(out) ^ set(OUTPUTS))
    for kk, v in out.items():
        if isinstance(v, str):
            assert len(v) <= 200, (kk, len(v))
    detail.update({"test": TEST, "conditions": cond, "controls": controls})
    with open(os.path.join(results, "outputs.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, sort_keys=True, ensure_ascii=False)
    with open(os.path.join(results, "detail.json"), "w", encoding="utf-8") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, default=str, ensure_ascii=False)
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run()      # nothing here depends on the seed: every count is exhaustive
    except Refused as e:
        sys.exit(f"kv2014: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
