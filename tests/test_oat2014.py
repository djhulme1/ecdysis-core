"""IIT 3.0's results (iit/oat2014.py): the builders, connectivity, reachability, Phi on systems the paper does not
draw (COPY rings of three, chains, a toggle), the condensation's exclusion, the unfolding and the feed-forward draws.
Nothing here computes Phi for the paper's own systems.

Run with: python3 -m unittest tests.test_oat2014 (in the pinned buildpack-deps image; gcc builds iit/flow.c)
"""

import importlib.util
import itertools
import os
import random
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
IIT = os.path.join(HERE, "..", "iit")
sys.path.insert(0, IIT)
_spec = importlib.util.spec_from_file_location("iit_oat2014", os.path.join(IIT, "oat2014.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
E = M.E

_TMP = tempfile.mkdtemp()
_LIB = M.build(_TMP)
FLOW = E.Flow(_LIB, 1)
EXACT = E.Flow(_LIB, 0)


def ring(state, kind="COPY"):
    spec = [("A", "C", "COPY", None), ("B", "A", "COPY", None), ("C", "B", "COPY", None)]
    return M.build_system("ring", spec, dict(zip("ABC", state)))


def chain():
    spec = [("X", "", "CONST", 1), ("A", "X", "COPY", None), ("B", "A", "NOT", None), ("C", "AB", "AND", None)]
    return M.build_system("chain", spec, {"X": 1, "A": 1, "B": 0, "C": 0})


class Builders(unittest.TestCase):
    def test_gates_and_threshold(self):
        spec = [("A", None, "THRESH", ([("B", 1), ("C", -1)], 1)), ("B", "AC", "XOR", None), ("C", "AB", "MAJ", None)]
        s = M.build_system("t", spec, {"A": 0, "B": 0, "C": 0})
        self.assertEqual(s.inputs, [(1, 2), (0, 2), (0, 1)])
        self.assertEqual(s.step((0, 1, 0)), (1, 0, 0))
        self.assertEqual(s.step((1, 1, 1)), (0, 0, 1))
        self.assertEqual(s.cm[1][0], 1)
        self.assertEqual(s.cm[0][0], 0)

    def test_lazy_tpm(self):
        s = chain()
        self.assertEqual(len(s.net.tpm_on), 16)
        for x in range(16):
            bits = tuple((x >> i) & 1 for i in range(4))
            self.assertEqual(tuple(s.net.tpm_on[x][j] for j in range(4)), s.step(bits))


class Connectivity(unittest.TestCase):
    def test_strong(self):
        r = ring((1, 0, 0))
        self.assertTrue(M.strongly_connected(r.cm, (0, 1, 2)))
        self.assertFalse(M.strongly_connected(r.cm, (0, 1)))
        self.assertTrue(M.strongly_connected(r.cm, (2,)))
        c = chain()
        self.assertFalse(M.strongly_connected(c.cm, (1, 2, 3)))

    def test_significant_and_reachable(self):
        c = chain()
        self.assertEqual(M.causally_significant(c), [1, 2])       # X has no input, C no output
        self.assertTrue(M.reachable(ring((1, 0, 0)), (0, 1, 2)))
        spec = [("Z", "", "CONST", 0), ("A", "Z", "COPY", None)]
        bad = M.build_system("bad", spec, {"Z": 0, "A": 1})
        self.assertFalse(M.reachable(bad, (1,)))


class Phi(unittest.TestCase):
    def test_ring_symmetric_and_positive(self):
        vals = []
        for s in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            phi, concepts, why = M.sia(FLOW, ring(s), (0, 1, 2))
            self.assertEqual(why, "computed")
            self.assertGreater(phi, 0)
            vals.append((phi, len(concepts)))
        self.assertEqual(len(set(vals)), 1)

    def test_feedforward_zero_in_full(self):
        c = chain()
        for r in (1, 2, 3):
            for nodes in itertools.combinations(range(4), r):
                phi, _, _ = M.sia(FLOW, c, nodes, full=True)
                self.assertEqual(phi, 0.0, nodes)
        self.assertEqual(M.sia(FLOW, c, (1, 2))[2], "not strongly connected")

    def test_connectivity_filter_changes_nothing(self):
        # a sparse four-element system the paper does not draw: Phi and concepts with and without the purview filter
        spec = [("A", "D", "COPY", None), ("B", "AD", "AND", None), ("C", "B", "NOT", None), ("D", "BC", "XOR", None)]
        s = M.build_system("sparse", spec, dict(zip("ABCD", (1, 1, 0, 1))))
        for nodes in ((0, 1, 2, 3), (1, 2, 3)):
            if not M.strongly_connected(s.cm, nodes):
                continue
            a = M.sia(FLOW, s, nodes)
            b = M.sia(FLOW, s, nodes, full=True)
            self.assertEqual(a[0], b[0])
            self.assertEqual([c.signature() for c in a[1]], [c.signature() for c in b[1]])

    def test_exact_mode_runs(self):
        phi1, _, _ = M.sia(FLOW, ring((1, 0, 0)), (0, 1, 2))
        phi0, _, _ = M.sia(EXACT, ring((1, 0, 0)), (0, 1, 2))
        self.assertAlmostEqual(phi1, phi0, places=4)

    def test_condensation_excludes_overlaps(self):
        spec = [("A", "C", "COPY", None), ("B", "A", "COPY", None), ("C", "B", "COPY", None),
                ("D", "F", "COPY", None), ("E", "D", "COPY", None), ("F", "E", "COPY", None)]
        s = M.build_system("two rings", spec, dict(zip("ABCDEF", (1, 0, 0, 0, 1, 1))))
        res = M.analyse(FLOW, s)
        self.assertEqual(sorted(res["condensation"]), ["ABC", "DEF"])
        self.assertEqual(res["computed"], 2)                      # only the rings are strongly connected


class Unfolding(unittest.TestCase):
    def test_toggle_unfolded(self):
        # one element x' = XOR(x, u), unfolded over three steps; outputs x_1..x_3
        step_fns = [((("x", 0), ("u", 0)), lambda v: (v[0] + v[1]) % 2)]
        for init in ((0,), (1,)):
            for seq in itertools.product(((0,), (1,)), repeat=3):
                u = M.unfold("toggle", 1, 1, step_fns, 0, init, list(seq), steps=3)
                bits = M.evaluate_unfolding(u, init, seq)
                x, want = init[0], []
                for t in range(3):
                    x = (x + seq[t][0]) % 2
                    want.append(x)
                self.assertEqual([bits[o] for o in u.outputs], want)
                self.assertTrue(all(not M.strongly_connected(u.cm, nodes)
                                    for nodes in itertools.combinations(range(u.n), 2)))

    def test_unfolding_has_no_cycle(self):
        u = M.photodiode_unfolding(init=(0, 1), inputs=[(1, 1), (0, 0), (1, 0), (0, 1)])
        for r in (2, 3, 4):
            for nodes in itertools.combinations(range(u.n), r):
                self.assertFalse(M.strongly_connected(u.cm, nodes))


class FeedForwardDraws(unittest.TestCase):
    def test_dag_settled_and_seeded(self):
        for k in range(6):
            a = M.draw_feedforward(random.Random(100 + k), k)
            b = M.draw_feedforward(random.Random(100 + k), k)
            self.assertEqual(a.state, b.state)
            self.assertEqual(a.inputs, b.inputs)
            layer = {i: l for l, lay in enumerate(a.layers) for i in lay}
            for j, ins in enumerate(a.inputs):
                self.assertTrue(all(layer[i] < layer[j] for i in ins))
            self.assertEqual(a.step(a.state), a.state)            # settled
            p = M.draw_feedforward(random.Random(100 + k), k, planted=True)
            self.assertTrue(any(M.strongly_connected(p.cm, nodes)
                                for r in range(2, p.n + 1) for nodes in itertools.combinations(range(p.n), r)))


class Printed(unittest.TestCase):
    def test_cut_and_rounded(self):
        self.assertEqual(M.matches(1.916665, 1.92, 2), (False, True))
        self.assertEqual(M.matches(0.0219, 0.021, 3), (True, False))
        self.assertEqual(M.matches(1.0, 1.00, 2), (True, True))
        self.assertEqual(M.matches(0.75, 1, 0), (False, True))

    def test_bad_seed(self):
        with self.assertRaises(M.Refused):
            M.run("nope", results=tempfile.mkdtemp())


if __name__ == "__main__":
    unittest.main()
