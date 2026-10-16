"""Korže and Vesel 2014 (packing/kv2014.py, packing/kvsearch.c): the lattice's coordinates, the C search against
enumeration, the Python backtracking, D_k against enumeration on paths and on a chain of hexagons, the topological
sort, and the colouring check on planted faults. H1, D6 and the 7-colouring are never computed here.

Run with: python3 -m unittest tests.test_kv2014 (in the pinned buildpack-deps image)
"""

import importlib.util
import itertools
import os
import random
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("packing_kv2014", os.path.join(HERE, "..", "packing", "kv2014.py"))
KV = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(KV)

_TMP = tempfile.mkdtemp(prefix="kv2014-tests-")
SEARCH = KV.Search(KV.build(_TMP))


def graph(n, edges):
    adj = {i: set() for i in range(n)}
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    order = list(range(n))
    return order, KV.distances(adj, order)


def enumerate_colourings(order, dist, k):
    """Every packing k-colouring, by trying all k^n assignments, in lexicographic order."""
    n = len(order)
    pairs = [(i, j, dist[order[i]][order[j]]) for i in range(n) for j in range(i + 1, n)
             if order[j] in dist[order[i]]]
    return [cols for cols in itertools.product(range(1, k + 1), repeat=n)
            if all(not (cols[i] == cols[j] and cols[i] >= dd) for i, j, dd in pairs)]


def is_packing(order, dist, cols):
    n = len(order)
    return all(not (cols[i] == cols[j] and order[j] in dist[order[i]] and dist[order[i]][order[j]] <= cols[i])
               for i in range(n) for j in range(i + 1, n))


def walk_counts(arcs, m):
    """Walks on 1..m vertices, by repeated multiplication (no topological order)."""
    N = len(arcs)
    w, out = [1] * N, []
    for _ in range(m):
        out.append(sum(w))
        nw = [0] * N
        for s in range(N):
            for t in arcs[s]:
                nw[t] += w[s]
        w = nw
    return out


def hexagon_chain_tile():
    """One hexagon and the two vertices that join it to the next copy, moved by (4, 0)."""
    return [(2, 0), (1, 1), (3, 1), (1, 2), (3, 2), (2, 3), (4, 0), (4, 3)]


class Lattice(unittest.TestCase):
    PATCH = [(X, Y) for X in range(-8, 16) for Y in range(-8, 16) if KV.is_vertex((X, Y))]

    def test_three_neighbours_symmetric_and_bipartite(self):
        for p in self.PATCH:
            nb = KV.lattice_neighbours(p)
            self.assertEqual(len(set(nb)), 3)
            for q in nb:
                self.assertTrue(KV.is_vertex(q))
                self.assertIn(p, KV.lattice_neighbours(q))
                self.assertNotEqual(p[1] % 2, q[1] % 2)

    def test_hexagon_is_a_six_cycle(self):
        hexagon = [(2, 0), (1, 1), (3, 1), (1, 2), (3, 2), (2, 3)]
        adj = KV.induced(hexagon)
        self.assertTrue(all(len(adj[p]) == 2 for p in hexagon))
        self.assertEqual(KV.n_edges(adj), 6)
        self.assertEqual(len(KV.bfs(adj, hexagon[0])), 6)

    def test_coordination_sequence(self):
        """The honeycomb has 3r vertices at distance exactly r from any vertex (r >= 1)."""
        adj = KV.induced(self.PATCH)
        for src in ((4, 4), (5, 5), (4, 3), (3, 6)):
            d = KV.bfs(adj, src, 6)
            for r in range(1, 7):
                self.assertEqual(sum(1 for v in d.values() if v == r), 3 * r, (src, r))

    def test_translations(self):
        for p in self.PATCH:
            for t in ((2, 0), (1, 2), (6, 0)):
                q = (p[0] + t[0], p[1] + t[1])
                self.assertTrue(KV.is_vertex(q))
                self.assertEqual(sorted((a + t[0], b + t[1]) for a, b in KV.lattice_neighbours(p)),
                                 sorted(KV.lattice_neighbours(q)))

    def test_triangular_coordinates(self):
        odd = [p for p in self.PATCH if p[1] % 2 == 1]
        unit = {(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)}
        for p in odd:
            i, j = KV.tri(p)
            self.assertEqual((1 + 2 * i + j, 2 * j + 1), p)
            for e in KV.lattice_neighbours(p):
                for q in KV.lattice_neighbours(e):
                    if q != p:
                        a, b = KV.tri(q)
                        self.assertIn((a - i, b - j), unit)

    def test_honeycomb_distance_is_twice_the_triangular(self):
        adj = KV.induced(self.PATCH)
        for src in ((5, 5), (4, 3)):
            for q, dd in KV.bfs(adj, src, 8).items():
                if q[1] % 2 == 1:
                    self.assertEqual(dd, 2 * KV.tri_distance(KV.tri(src), KV.tri(q)), (src, q))

    def test_patch_distances_are_the_lattice_distances(self):
        inner, adj = KV.hex_patch(4, 10, 5)
        big = KV.induced([(X, Y) for X in range(-12, 26) for Y in range(-12, 26) if KV.is_vertex((X, Y))])
        for p in inner:
            near = KV.bfs(adj, p, 5)
            far = {q: v for q, v in KV.bfs(big, p, 5).items()}
            self.assertEqual(near, far)

    def test_strip_and_gap_on_path_tiles(self):
        tile = [(x, 0) for x in range(4)]
        pts, copy = KV.strip(4, tile, (4, 0))
        self.assertEqual(len(pts), 16)
        self.assertEqual(KV.gap_two_apart(pts, copy, KV.path_nbr(pts)), 5)
        pts, copy = KV.strip(2, tile, (4, 0))
        self.assertIsNone(KV.gap_two_apart(pts, copy, KV.path_nbr(pts)))


class SearchAgainstEnumeration(unittest.TestCase):
    def check(self, order, dist, k):
        want = enumerate_colourings(order, dist, k)
        st, found, nodes, sols = SEARCH.run(order, dist, k, keep=len(want) + 3)
        self.assertEqual(st, 0)
        self.assertEqual(found, len(want))
        self.assertEqual(sols, want)                 # same colourings, in the same (lexicographic) order
        self.assertEqual(KV.py_count(order, dist, k), len(want))
        self.assertTrue(all(is_packing(order, dist, s) for s in sols))

    def test_paths(self):
        for n in range(1, 8):
            order, dist = graph(n, [(i, i + 1) for i in range(n - 1)])
            for k in (1, 2, 3):
                self.check(order, dist, k)

    def test_six_cycle(self):
        order, dist = graph(6, [(i, (i + 1) % 6) for i in range(6)])
        for k in (1, 2, 3, 4):
            self.check(order, dist, k)

    def test_random_graphs(self):
        rng = random.Random(20141)
        for trial in range(40):
            n = rng.randint(2, 7)
            edges = [e for e in itertools.combinations(range(n), 2) if rng.random() < 0.35]
            order, dist = graph(n, edges)
            k = rng.randint(1, 4)
            self.check(order, dist, k)

    def test_cap_and_budget(self):
        order, dist = graph(6, [(i, i + 1) for i in range(5)])
        want = enumerate_colourings(order, dist, 3)
        self.assertGreater(len(want), 1)
        st, found, _, sols = SEARCH.run(order, dist, 3, cap=1, keep=1)
        self.assertEqual((st, found, sols), (1, 1, want[:1]))
        st, found, nodes, _ = SEARCH.run(order, dist, 3, budget=3)
        self.assertEqual((st, nodes), (2, 3))
        st, found, _, _ = SEARCH.run(order, dist, 1)
        self.assertEqual((st, found), (0, 0))        # a path with an edge has no packing 1-colouring

    def test_all_colourings(self):
        order, dist = graph(5, [(0, 1), (1, 2), (2, 3), (3, 4), (4, 0)])
        self.assertEqual(SEARCH.all_colourings(order, dist, 4), enumerate_colourings(order, dist, 4))


class DigraphOnOtherTiles(unittest.TestCase):
    def pairs_by_enumeration(self, tile, shift, k, nbr):
        t1 = sorted(tile)
        sols = enumerate_colourings(t1, KV.distances(nbr(t1), t1), k)
        t2 = [(X + shift[0], Y + shift[1]) for (X, Y) in t1]
        both = t1 + t2
        d2 = KV.distances(nbr(both), both)
        arcs = [[t for t, b in enumerate(sols) if is_packing(both, d2, a + b)] for a in sols]
        return sols, arcs

    def check(self, tile, shift, k, nbr):
        sols, arcs, loops = KV.build_dk(SEARCH, tile, shift, k, nbr)
        want_sols, want_arcs = self.pairs_by_enumeration(tile, shift, k, nbr)
        self.assertEqual(sols, want_sols)
        self.assertEqual(arcs, want_arcs)
        self.assertEqual(loops, sum(1 for s in range(len(sols)) if s in want_arcs[s]))
        return sols, arcs, loops

    def test_path_tiles(self):
        tile = [(x, 0) for x in range(5)]
        for k in (2, 3):
            sols, arcs, _ = self.check(tile, (5, 0), k, KV.path_nbr)
            # copies two apart are 6 > k apart, so walks are the packing colourings of the longer path
            for i in (1, 2, 3):
                pts = sorted(KV.strip(i, tile, (5, 0))[0])
                st, n, _, _ = SEARCH.run(pts, KV.distances(KV.path_nbr(pts), pts), k)
                self.assertEqual(n, walk_counts(arcs, i)[i - 1], (k, i))
        ac2, _, _, _ = KV.topo(KV.build_dk(SEARCH, tile, (5, 0), 2, KV.path_nbr)[1])
        ac3, _, _, _ = KV.topo(KV.build_dk(SEARCH, tile, (5, 0), 3, KV.path_nbr)[1])
        self.assertTrue(ac2)          # no packing 2-colouring of a long path
        self.assertFalse(ac3)         # 1, 2, 1, 3 repeated colours the path; period 20 is a cycle of D3

    def test_hexagon_chain(self):
        tile = hexagon_chain_tile()
        self.assertTrue(all(KV.is_vertex(p) for p in tile))
        pts, _ = KV.strip(2, tile, (4, 0))
        self.assertEqual(KV.n_edges(KV.induced(pts)), 2 * KV.n_edges(KV.induced(tile)) + 2)
        sizes = {}
        for k in (3, 4, 5):       # a hexagon has no packing 3-colouring; with 4 colours H2 of this chain has none
            sols, arcs, _ = self.check(tile, (4, 0), k, KV.induced)
            sizes[k] = (len(sols), sum(len(a) for a in arcs))
            for i in (1, 2, 3):
                o = sorted(KV.strip(i, tile, (4, 0))[0])
                dist = KV.distances(KV.induced(o), o)
                st, n, _, _ = SEARCH.run(o, dist, k)
                self.assertEqual(st, 0)
                w = walk_counts(arcs, i)[i - 1]
                if i <= 2:
                    self.assertEqual(n, w, (k, i))
                    self.assertEqual(KV.py_count(o, dist, k), n)
                else:
                    # copies two apart are only 5 apart here, so a walk need not colour H3; every colouring of H3
                    # still restricts to a walk, the direction the lower bound uses
                    self.assertLessEqual(n, w, (k, i))
        self.assertEqual(sizes[3], (0, 0))
        self.assertEqual(sizes[4][1], 0)
        self.assertGreater(sizes[5][1], 0)


class TopologicalSort(unittest.TestCase):
    def test_dag(self):
        acyclic, d, walks, indeg = KV.topo([[1, 2], [3], [3], []])
        self.assertTrue(acyclic)
        self.assertEqual(d, 2)
        self.assertEqual(walks, [4, 4, 2, 0])
        self.assertEqual(indeg, [0, 1, 1, 2])

    def test_cycle_and_loop(self):
        self.assertFalse(KV.topo([[1], [2], [0]])[0])
        self.assertFalse(KV.topo([[0]])[0])
        self.assertFalse(KV.topo([[1], [1]])[0])

    def test_single_vertex(self):
        self.assertEqual(KV.topo([[]])[:3], (True, 0, [1, 0]))

    def test_random_dags_against_walk_counts(self):
        rng = random.Random(37)
        for _ in range(30):
            N = rng.randint(1, 12)
            arcs = [[t for t in range(s + 1, N) if rng.random() < 0.3] for s in range(N)]
            perm = list(range(N))
            rng.shuffle(perm)
            relabelled = [[] for _ in range(N)]
            for s in range(N):
                relabelled[perm[s]] = sorted(perm[t] for t in arcs[s])
            acyclic, d, walks, _ = KV.topo(relabelled)
            self.assertTrue(acyclic)
            ref = walk_counts(relabelled, N + 2)
            self.assertEqual(walks, ref[:d + 2])
            self.assertGreater(ref[d], 0)
            self.assertEqual(ref[d + 1], 0)


class ColouringCheck(unittest.TestCase):
    def test_path_period_four(self):
        pts = [(x, 0) for x in range(0, 40)]
        adj = KV.path_nbr(pts)
        inner = [(x, 0) for x in range(10, 30)]
        good = {0: 1, 1: 2, 2: 1, 3: 3}
        ok, checked, bad = KV.check_colouring(lambda p: good[p[0] % 4], 3, inner, adj)
        self.assertTrue(ok)
        self.assertEqual(checked, 20 * 6)
        ok, _, bad = KV.check_colouring(lambda p: (1, 2)[p[0] % 2], 3, inner, adj)
        self.assertFalse(ok)
        self.assertEqual(bad[2:], (2, 2))

    def test_lattice_faults(self):
        inner, adj = KV.hex_patch(6, 14, 4)
        ok, _, bad = KV.check_colouring(lambda p: 1 if p[1] % 2 == 0 else 2, 2, inner, adj)
        self.assertFalse(ok)
        self.assertEqual(bad[2:], (2, 2))
        ok, _, bad = KV.check_colouring(lambda p: 9, 7, inner, adj)
        self.assertFalse(ok)
        self.assertEqual(bad[1], 9)


class Output(unittest.TestCase):
    def test_listed(self):
        self.assertEqual(KV.listed("n: ", [1, 2, 3]), "n: 1, 2, 3")
        text = KV.listed("n: ", list(range(1000, 1100)), limit=40)
        self.assertLessEqual(len(text), 40)
        self.assertTrue(text.endswith(" ..."))
        self.assertTrue(text[:-4].split(", ")[-1].isdigit())

    def test_outputs_named_once(self):
        self.assertEqual(len(KV.OUTPUTS), len(set(KV.OUTPUTS)))


if __name__ == "__main__":
    unittest.main()
