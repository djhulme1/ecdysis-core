"""Albantakis & Tononi's causal composition (iit/at2019.py): the partitions (PyPhi's 'ALL'), the repertoires and the
relative entropies on a hand-made system of three AND gates, the cut, the cycle and inverse tests, the 48 symmetry
maps and the canonical form, and effective information on systems outside the claim's population. No reversible
system and not Table 1's example is run through the paper's measures here.

Run with: python3 -m unittest tests.test_at2019
"""

import importlib.util
import itertools
import math
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("iit_at2019", os.path.join(HERE, "..", "iit", "at2019.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "9a" * 32


def and_gates():
    """Each element the AND of the other two (not reversible)."""
    p = []
    for v in range(8):
        a, b, c = v & 1, v >> 1 & 1, v >> 2 & 1
        p.append([float(b and c), float(a and c), float(a and b)])
    return p


class Partitions(unittest.TestCase):
    def test_set_partitions(self):
        self.assertEqual(len(list(M.set_partitions([1, 2, 3]))), 5)
        self.assertEqual(len(list(M.set_partitions([1, 2, 3, 4]))), 15)
        self.assertEqual(len(list(M.k_partitions([1, 2, 3], 2))), 3)

    def test_all_partitions(self):
        self.assertEqual(M.all_partitions(1, M.FULL), [[(1, 0), (0, M.FULL)]])
        self.assertEqual(len(M.all_partitions(3, M.FULL)), 28)
        self.assertEqual(len(M.all_partitions(7, M.FULL)), 146)
        for parts in M.all_partitions(7, M.FULL):
            mechs = [m for m, _ in parts]
            purv = [p for _, p in parts]
            self.assertEqual(sum(mechs), 7)
            self.assertEqual(sum(purv), M.FULL)
            self.assertFalse(any(m == 7 and p for m, p in parts))
        # two elements over one purview element: {a}{b} with the purview to a, to b or to neither, and the whole
        # mechanism cut away
        self.assertEqual(len(M.all_partitions(3, 4)), 4)


class Repertoires(unittest.TestCase):
    def test_effect(self):
        rep = M.Rep(and_gates(), 1)            # A on, B and C off
        self.assertEqual(rep.effect(1), [0.25, 0.5, 0.5])
        self.assertEqual(rep.effect(0), [0.25, 0.25, 0.25])

    def test_cause(self):
        rep = M.Rep(and_gates(), 1)
        self.assertEqual(rep.cause_node(0, M.FULL), [0, 0, 0, 0, 0, 0, 0.5, 0.5])
        cb = rep.cause_node(1, M.FULL)         # B off: every state but those with A and C on
        self.assertAlmostEqual(sum(cb), 1.0)
        self.assertEqual([x > 0 for x in cb], [True, True, True, True, True, False, True, False])
        self.assertEqual(rep.cause(3, M.FULL), [0, 0, 0, 0, 0, 0, 1.0, 0])
        self.assertEqual(rep.cause(0, 3), [0.25] * 4)
        self.assertEqual(rep.cause(5, 0), [1.0])

    def test_unreachable(self):
        # A and B on, C off: A on needs B and C on before, B on needs A and C, and then C would be on too
        rep = M.Rep(and_gates(), 3)
        self.assertEqual(rep.cause(7, M.FULL), [0.0] * 8)
        self.assertEqual(rep.cause(3, M.FULL), [0, 0, 0, 0, 0, 0, 0, 1.0])
        self.assertEqual(M.phi_cause(rep, 7), 0.0)
        self.assertEqual(len(M.phis(and_gates(), 3)), 7)

    def test_kl_and_phi(self):
        self.assertEqual(M.kl_bern(0.5, 0.5), 0.0)
        self.assertAlmostEqual(M.kl_bern(1.0, 0.5), 1.0)
        self.assertAlmostEqual(M.kl_bern(0.75, 0.5), 0.75 * math.log2(1.5) - 0.25)
        self.assertEqual(M.kl_bern(1.0, 0.0), math.inf)
        rep = M.Rep(and_gates(), 1)
        # A alone against the unconstrained repertoire: 0 + 2 (0.5 log2 2 + 0.5 log2 (2/3))
        self.assertAlmostEqual(M.phi_effect(rep, 1), 2 * (0.5 + 0.5 * math.log2(2 / 3)))

    def test_index_and_compose(self):
        self.assertEqual(M.index_in(6, 6), 3)
        self.assertEqual(M.index_in(5, 6), 2)
        self.assertEqual(M.compose(1, 1, 6, 3), 7)


class Systems(unittest.TestCase):
    def test_cut(self):
        pc = M.cut_tpm(and_gates(), 1)
        self.assertEqual(pc[7], [1.0, 0.5, 0.5])
        self.assertEqual(pc[3], [0.0, 0.0, 0.5])
        p = and_gates()
        self.assertIs(M.cut_tpm(p, 0), p)

    def test_concept_style_cuts(self):
        star = [(3, M.FULL), (4, 0), (0, 0)]      # {MC_t, MCX_t+1}, {X_t, 0}
        self.assertEqual(M.kcut_mask(star, "E"), sum(1 << (2 * 3 + j) for j in range(3)))   # X's outputs
        self.assertEqual(M.kcut_mask(star, "C"), sum(1 << (i * 3 + 2) for i in range(3)))   # X's inputs
        self.assertEqual(M.kcut_mask([(7, 0), (0, 7)], "E"), (1 << 9) - 1)
        self.assertEqual(M.kcut_mask([(7, 0), (0, 7)], "C"), (1 << 9) - 1)
        self.assertEqual(len(M.KCUTS["C"]), 146)
        self.assertEqual(len(M.KCUTS["E"]), 146)
        p = and_gates()
        for x in range(1, 7):
            mask = sum(1 << (i * 3 + j) for i in range(3) if x >> i & 1 for j in range(3) if not x >> j & 1)
            self.assertEqual(M.sever(p, mask), M.cut_tpm(p, x))
        self.assertIs(M.sever(p, 0), p)
        self.assertEqual(M.part_label(star, "MCX"), "MC>MCX,X>0")
        low = M.concept_style(p, 6)
        self.assertTrue(all(math.isfinite(low[s][0]) and low[s][1] in M.PARTITIONS[7] for s in "CE"))

    def test_cycles(self):
        cyc = (1, 2, 3, 4, 5, 6, 7, 0)
        self.assertTrue(M.is_er(cyc))
        self.assertFalse(M.is_er(tuple(range(8))))
        self.assertFalse(M.is_er((1, 0, 3, 2, 5, 4, 7, 6)))
        self.assertEqual(M.inverse(cyc), (7, 0, 1, 2, 3, 4, 5, 6))
        self.assertEqual(sum(M.is_er(p) for p in itertools.permutations(range(8))), 5040)

    def test_symmetry_maps(self):
        self.assertEqual(len(M.MAPS), 48)
        self.assertEqual(len({tuple(g) for g in M.MAPS}), 48)
        self.assertEqual(M.canonical(tuple(range(8))), tuple(range(8)))
        st = M.Stream(SEED, "c")
        perms = list(itertools.permutations(range(8)))
        for _ in range(20):
            p = perms[st.below(len(perms))]
            g = M.MAPS[st.below(48)]
            ginv = [0] * 8
            for s, t in enumerate(g):
                ginv[t] = s
            conj = tuple(g[p[ginv[t]]] for t in range(8))
            self.assertEqual(M.canonical(conj), M.canonical(p))

    def test_ei(self):
        self.assertAlmostEqual(M.ei(and_gates())[0], 2.0)
        const = [[0.0, 0.0, 0.0] for _ in range(8)]
        e, h = M.ei(const)
        self.assertEqual((e, h), (0.0, [0.0, 0.0, 0.0]))

    def test_mcx_is_as_read(self):
        p = M.mcx_tpm()
        self.assertEqual(p[1], [0.0, 1.0, 1.0])      # M on: majority off, C copies M, X = M xor C
        self.assertEqual(p[3], [1.0, 1.0, 0.0])


class Run(unittest.TestCase):
    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("nothex", results=os.path.join(HERE, "nonexistent-results"))

    def test_test_length(self):
        self.assertLessEqual(len(M.TEST), 600)

    def test_stream(self):
        a, b = M.Stream(SEED, "x"), M.Stream(SEED, "x")
        self.assertEqual([a.u() for _ in range(6)], [b.u() for _ in range(6)])
        self.assertTrue(0.0 <= M.Stream(SEED, "y").unit() < 1.0)


if __name__ == "__main__":
    unittest.main()
