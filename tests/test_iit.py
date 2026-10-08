"""The IIT 3.0 check: PyPhi's partition and cut orders, its connectivity test, the transport solver against brute
force, pyemd's arithmetic, small phi on the OR + AND + XOR system (exact and as PyPhi has it), PyPhi's own value for
AND + OR and the photodiode, the merging of 1e-6 pairs, and, with the inputs at inputs/ (or IIT_INPUTS), three
systems end to end.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import itertools
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
IIT = os.path.join(HERE, "..", "iit")
sys.path.insert(0, IIT)
_spec = importlib.util.spec_from_file_location("iit_check", os.path.join(IIT, "check.py"))
K = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(K)
E = K.E

_tmp = tempfile.mkdtemp()
LIB = os.path.join(_tmp, "flow.so")
subprocess.run(["gcc", "-O2", "-shared", "-fPIC", "-o", LIB, os.path.join(IIT, "flow.c"), "-lm"], check=True)
EXACT, PYEMD = E.Flow(LIB, 0), E.Flow(LIB, 1)

OIZUMI = [[0, 0, 0], [0, 0, 1], [1, 0, 1], [1, 0, 0], [1, 0, 0], [1, 1, 1], [1, 0, 1], [1, 1, 0]]
AND_OR = [[0, 0], [0, 1], [0, 1], [1, 1]]


def net(rows):
    return E.Network([[float(v) for v in r] for r in rows])


class Orders(unittest.TestCase):
    def test_pyphi_orders(self):
        self.assertEqual(E.bipartition_indices(3), [((), (0, 1, 2)), ((0,), (1, 2)), ((1,), (0, 2)), ((0, 1), (2,))])
        self.assertEqual(E.directed_bipartition((0, 1, 2), nontrivial=True),
                         [((0,), (1, 2)), ((1,), (0, 2)), ((0, 1), (2,)),
                          ((2,), (0, 1)), ((0, 2), (1,)), ((1, 2), (0,))])
        parts = list(E.mip_bipartitions((0,), (1, 2)))
        self.assertEqual(len(parts), 3)            # the mechanism stays whole: one of the purview's 3 nonempty parts
        self.assertNotIn((((), ()), ((0,), (1, 2))), parts)

    def test_connectivity(self):
        full = [[1, 1], [1, 1]]
        self.assertFalse(E.block_reducible(full, (0,), (1,)))
        self.assertTrue(E.block_reducible([[1, 0], [1, 1]], (0,), (1,)))
        self.assertTrue(E.block_reducible([[1, 0], [0, 1]], (0, 1), (0, 1)))
        self.assertFalse(E.block_reducible(full, (0, 1), (0, 1)))


class Transport(unittest.TestCase):
    def test_against_assignment(self):
        import random
        rng = random.Random(4)
        for n in (1, 2, 3, 4, 5):
            for _ in range(5):
                C = [[rng.randint(0, 9) / 3 for _ in range(n)] for _ in range(n)]
                best = min(sum(C[i][p[i]] for i in range(n)) for p in itertools.permutations(range(n)))
                self.assertAlmostEqual(EXACT.transport([1.0] * n, [1.0] * n, C), best, places=12)

    def test_pyemd_arithmetic(self):
        p, q = [0.25] * 4, [1 / 3, 1 / 6, 1 / 6, 1 / 3]
        self.assertAlmostEqual(EXACT.hamming_emd(p, q), 1 / 6, places=14)
        self.assertEqual(round(PYEMD.hamming_emd(p, q), 9), 0.166666)
        self.assertEqual(EXACT.hamming_emd(p, p), 0.0)


class SmallPhi(unittest.TestCase):
    def test_oizumi_cause_ties(self):
        sub = E.Subsystem(net(OIZUMI), (1, 0, 0), (0, 1, 2))
        ab = {p: sub.find_mip(EXACT, E.CAUSE, (0, 1), p)[0] for p in sub.potential_purviews(E.CAUSE, (0, 1))}
        self.assertEqual((ab[(0, 2)], ab[(1, 2)], ab[(0, 1, 2)]), (0.25, 0.25, 0.25))
        sub2 = E.Subsystem(net(OIZUMI), (1, 0, 0), (0, 1, 2))
        ab2 = {p: sub2.find_mip(PYEMD, E.CAUSE, (0, 1), p)[0] for p in sub2.potential_purviews(E.CAUSE, (0, 1))}
        self.assertEqual((ab2[(0, 2)], ab2[(1, 2)], ab2[(0, 1, 2)]), (0.249999, 0.249999, 0.25))
        a = {p: sub.find_mip(EXACT, E.EFFECT, (0,), p)[0] for p in sub.potential_purviews(E.EFFECT, (0,))}
        self.assertEqual(a[(1,)], 0.25)
        self.assertEqual(sum(1 for v in a.values() if v > 0), 1)

    def test_marginalise(self):
        col = [0.0, 1.0, 0.0, 1.0]       # on iff node 0 is on
        self.assertEqual(E.marginalise(col, (0,), 2), [0.5] * 4)
        self.assertEqual(E.marginalise(col, (1,), 2), col)


class PyPhiValue(unittest.TestCase):
    def ids(self):
        table = {}

        def canon(c):
            c.canon = table.setdefault(c.signature(), len(table))
        return canon

    def test_and_or_and_photodiode(self):
        self.assertEqual(K.pyphi_value(PYEMD, net(AND_OR), (0, 0), (0, 1), self.ids()), 0.090278)
        self.assertEqual(K.pyphi_value(PYEMD, net([[0, 0], [0, 1], [1, 0], [1, 1]]), (1, 0), (0, 1), self.ids()), 1.0)

    def test_spectrum_of_and_or(self):
        sp = K.spectrum(PYEMD, net(AND_OR), (0, 0), (0, 1), self.ids())
        self.assertEqual((sp["structures"], sp["lo"], sp["hi"], len(sp["band"])), (81, 0.0, 0.513889, 83))
        ex = K.spectrum(EXACT, net(AND_OR), (0, 0), (0, 1), self.ids())
        self.assertEqual((len(ex["band"]), len(ex["merged"]), len(sp["merged"])), (71, 63, 63))


class Merging(unittest.TestCase):
    def test_merged(self):
        self.assertEqual(K.merged([0.131944, 0.131945, 0.25, 0.250001, 0.250002, 0.3]), [0.131944, 0.25, 0.3])
        self.assertEqual(K.merged([0.1, 0.100002]), [0.1, 0.100002])


def inputs_dir():
    d = os.environ.get("IIT_INPUTS") or os.path.join(HERE, "..", "inputs")
    return d if all(os.path.isfile(os.path.join(d, n)) for n in K.INPUTS) else None


@unittest.skipUnless(inputs_dir(), "the inputs are not at inputs/ (or IIT_INPUTS)")
class TheCorpus(unittest.TestCase):
    def test_three_systems(self):
        with tempfile.TemporaryDirectory() as d:
            out, det = K.run(inputs=inputs_dir(), results=d, only=("AND+OR", "Photodiode", "Oizumi et al. 2014"))
        by = {r["name"]: r for r in det["systems"]}
        self.assertEqual(len(by["Photodiode"]["pyphi"]["merged"]), 1)
        oiz = by["Oizumi et al. 2014"]
        self.assertEqual((oiz["pyphi"]["structures"], oiz["exact"]["structures"]), (27, 81))
        self.assertTrue(by["Oizumi et al. 2014"]["printed"]["equal"])
        self.assertTrue(by["AND+OR"]["printed"]["equal"])
        self.assertEqual(out["test_passed"], 0)   # three systems are not ten


if __name__ == "__main__":
    unittest.main()
