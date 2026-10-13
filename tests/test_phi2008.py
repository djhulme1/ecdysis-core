"""Balduzzi & Tononi's integrated information (iit/phi2008.py): repertoires by Bayes' rule with extrinsic inputs
averaged, effective information across the total partition and bipartitions, the normalization and the tie rule, the
paper's printed values for its basic examples, and the verdict at and beside each condition.

Run with: python3 -m unittest tests.test_phi2008
"""

import importlib.util
import math
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("iit_phi2008", os.path.join(HERE, "..", "iit", "phi2008.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)


class Repertoires(unittest.TestCase):
    def test_bayes_with_outside_averaged(self):
        g = M.and_gates()
        self.assertEqual(g.repertoire((0, 1, 2), (0, 0, 1)), {(1, 1, 0): 1.0})
        # n3 alone entering 1: its own past is free (it reads n1 and n2, which are averaged), so uniform
        self.assertEqual(g.repertoire((2,), (0, 0, 1)), {(0,): 0.5, (1,): 0.5})
        # n1 alone entering 0: its next output reads n2 and n3 (averaged), not n1, so its past is free
        self.assertEqual(g.repertoire((0,), (0, 0, 1)), {(0,): 0.5, (1,): 0.5})

    def test_probabilistic_element(self):
        net = M.Network(1, lambda k, x: 0.75 if x[0] else 0.25)       # copies itself with noise
        self.assertAlmostEqual(net.repertoire((0,), (1,))[(1,)], 0.75)


class Partitions(unittest.TestCase):
    def test_disjoint_couples(self):
        two = M.Network(4, lambda k, x: x[(1, 0, 3, 2)[k]])
        cands = {c[0]: c for c in M.candidates(two, (0, 1, 2, 3), (1, 0, 0, 1))}
        self.assertAlmostEqual(cands["total"][1], 4.0)
        self.assertAlmostEqual(cands[((0, 1), (2, 3))][1], 0.0)
        self.assertEqual(M.phi(two, (0, 1, 2, 3), (1, 0, 0, 1))[:2], (0.0, ((0, 1), (2, 3))))

    def test_tie_rule(self):
        cands = [("total", 4.0, 1.0), (((0,), (1, 2, 3)), 1.0, 1.0), (((0, 1), (2, 3)), 2.0, 1.0),
                 (((3,), (0, 1, 2)), 0.5, 1.5)]
        self.assertEqual(M.mip(cands)[0][0], ((0,), (1, 2, 3)))
        self.assertEqual(M.mip(cands)[1], 3)
        self.assertEqual(M.mip(cands, ties_to_total=True)[0][0], "total")
        self.assertEqual(M.mip([("total", 4.0, 1.0), (((0,), (1, 2, 3)), 1.2, 1.2)])[0][0], "total")


class Examples(unittest.TestCase):
    def test_counter(self):
        c = M.counter()
        cyc = [(0, 0, 0, 0)]
        for _ in range(16):
            cyc.append(c.update(cyc[-1]))
        self.assertEqual(cyc[16], cyc[0])
        self.assertEqual(len(set(cyc[:16])), 16)
        self.assertEqual(cyc[1], (1, 0, 0, 0))
        vals = {s: M.phi(c, (0, 1, 2, 3), s)[0] for s in c.past}
        self.assertTrue(all(v > 0 for v in vals.values()))
        self.assertEqual(sum(1 for v in vals.values() if abs(v - 0.19) <= 0.01), 14)
        self.assertAlmostEqual(M.phi(c, (0, 1, 2, 3), (0, 0, 0, 0))[0], 1.0)
        self.assertAlmostEqual(M.phi(c, (0, 1, 2, 3), (0, 0, 0, 0), ties_to_total=True)[0], 4.0)
        self.assertAlmostEqual(M.phi(c, (0, 1, 2, 3), (1, 1, 0, 1))[0], math.log2(8 / 7), places=9)

    def test_replay_and_copies(self):
        r = M.replay()
        self.assertTrue(all(M.phi(r, (0, 1, 2, 3), s)[0] == 0.0 for s in r.past))
        f = M.copied()
        reach = {f.update(x) for x in f.past}
        self.assertEqual(len(reach), 8)
        self.assertTrue(all(M.phi(f, tuple(range(6)), s)[0] == 0.0 for s in reach))
        self.assertAlmostEqual(M.phi(f, (0, 1, 2), (0, 0, 1, 1, 1, 0), ties_to_total=True)[0], 3.0)

    def test_controls(self):
        ctl, _ = M.controls(M.random.Random(7))
        self.assertTrue(all(ctl.values()), ctl)


class Verdict(unittest.TestCase):
    def test_at_and_beside_each_condition(self):
        good = ({0: 0.19, 1: 1.0}, {0: 0.0}, {0: 0.0})
        self.assertTrue(all(M.conditions(*good).values()))
        for bad in (({0: 0.19, 1: 0.0}, {0: 0.0}, {0: 0.0}), ({0: 0.21, 1: 1.0}, {0: 0.0}, {0: 0.0}),
                    ({0: 0.19, 1: 1.0}, {0: 1e-6}, {0: 0.0}), ({0: 0.19, 1: 1.0}, {0: 0.0}, {0: 0.5})):
            with self.subTest(bad=bad):
                self.assertEqual(sum(M.conditions(*bad).values()), 3)


if __name__ == "__main__":
    unittest.main()
