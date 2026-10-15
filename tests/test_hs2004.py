"""Hordijk & Steel's RAF algorithm (raf/hs2004.py): the seeded streams and draws; the small systems' shape; the
exhaustive search, both ways, on a hand-made system; Algorithms 1 to 3 traced step by step, with their passes and
checks counted by hand; the single-deletion and batch schedules, the breadth-first closure and the definition check
on the same system; the later reading's difference on a system where only food catalyses; and the polymer model's
reactions against an enumeration. Neither the paper's example nor any seed-drawn system is run through the algorithm
here.

Run with: python3 -m unittest tests.test_hs2004
"""

import importlib.util
import os
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("raf_hs2004", os.path.join(HERE, "..", "raf", "hs2004.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "cd" * 32


def chain():
    """Molecules 0..3, food {0}: r0 0 -> 1 (catalyst 1), r1 1 -> 2 (catalyst 3), r2 2 -> 3 (catalyst 2), r3 3 -> 0
    (no catalyst). By hand: the RAF sets are {r0} and {r0, r1, r2}; the RA sets' union is {r0, r1, r2}; the
    F-generated sets' union is all four."""
    return M.System(4, (0,), [((0,), (1,)), ((1,), (2,)), ((2,), (3,)), ((3,), (0,))], [(1,), (3,), (2,), ()])


class Streams(unittest.TestCase):
    def test_stream(self):
        a, b = M.Stream(SEED, "x"), M.Stream(SEED, "x")
        self.assertEqual([a.u() for _ in range(9)], [b.u() for _ in range(9)])
        c = M.Stream(SEED, "y")
        self.assertNotEqual(M.Stream(SEED, "x").u(), c.u())
        self.assertTrue(all(0 <= M.Stream(SEED, "z").below(7) < 7 for _ in range(5)))

    def test_polymer_draws(self):
        cats1 = M.polymer_catalysts(M.polymer_rng(SEED, 5, (1, 1), 0), 100, 1000, (1, 1))
        cats2 = M.polymer_catalysts(M.polymer_rng(SEED, 5, (1, 1), 0), 100, 1000, (1, 1))
        self.assertEqual(cats1, cats2)
        self.assertEqual(len(cats1), 1000)
        total = sum(len(c) for c in cats1)
        self.assertLess(abs(total - 100), 50)          # 100 expected, standard deviation about 10
        self.assertTrue(all(0 <= x < 100 for c in cats1 for x in c))
        other = M.polymer_catalysts(M.polymer_rng(SEED, 5, (1, 1), 1), 100, 1000, (1, 1))
        self.assertNotEqual(cats1, other)


class SmallSystems(unittest.TestCase):
    def test_shape(self):
        for i in range(40):
            s, p = M.small_system(SEED, i)
            self.assertTrue(3 <= s.m <= 7)
            self.assertTrue(1 <= len(s.food) <= min(3, s.m - 1))
            self.assertTrue(1 <= len(s.reactions) <= 12)
            self.assertEqual(len(set(s.reactions)), len(s.reactions))
            for A, B in s.reactions:
                self.assertTrue(1 <= len(A) <= 2 and 1 <= len(B) <= 2 and not set(A) & set(B))
            self.assertEqual(len(s.cats), len(s.reactions))
            self.assertIn(p["q"], ("1/20", "1/10", "1/5", "1/3"))
        a, _ = M.small_system(SEED, 3)
        b, _ = M.small_system(SEED, 3)
        self.assertEqual((a.reactions, a.cats), (b.reactions, b.cats))

    def test_possible(self):
        self.assertEqual(M.POSSIBLE[3], 12)

    def test_system_refuses(self):
        with self.assertRaises(ValueError):
            M.System(3, (0,), [((0,), (0,))], [()])
        with self.assertRaises(ValueError):
            M.System(3, (0,), [((0,), (1,)), ((0,), (1,))], [(), ()])


class Exhaustive(unittest.TestCase):
    def test_chain(self):
        rafs, ra, fg = M.exhaustive(chain())
        self.assertEqual(sorted(rafs), [0b0001, 0b0111])
        self.assertEqual((ra, fg), (0b0111, 0b1111))
        r2, ra2, fg2 = M.exhaustive_sets(chain())
        self.assertEqual({M.to_mask(S) for S in r2}, {0b0001, 0b0111})
        self.assertEqual((M.to_mask(ra2), M.to_mask(fg2)), (0b0111, 0b1111))

    def test_food_catalyst(self):
        s = M.System(3, (0, 1), [((1,), (2,))], [(0,)])
        self.assertEqual(M.exhaustive(s)[0], [])
        self.assertEqual(M.raf_algorithm(s)[0], [])
        self.assertEqual(M.raf_algorithm(s, fault="later")[0], [0])


class Algorithm(unittest.TestCase):
    def test_trace(self):
        # Pass 1: ReduceToRA sweeps 4 (r3 deleted) and 3; ComputeClosure sweeps 3 (W grows) and 3; ReduceToF-generated
        # 3. Pass 2: 3, then 3 and 3, then 3, and nothing deleted. 16 + 12 = 28 checks, 2 passes.
        got, passes, checks = M.raf_algorithm(chain())
        self.assertEqual((got, passes, checks), ([0, 1, 2], 2, 28))
        self.assertLessEqual(checks, M.bound(4))
        self.assertEqual(M.bound(4), 128)

    def test_faults(self):
        # reactions listed against the order of need (r0 needs r1's product, r1 needs r2's): one sweep of
        # ComputeClosure reaches only {0, 1}, r0 is deleted, then r2 loses its catalyst and r1 its reactant
        s = M.System(4, (0,), [((2,), (3,)), ((1,), (2,)), ((0,), (1,))], [(1,), (2,), (3,)])
        self.assertEqual(M.raf_algorithm(s)[0], [0, 1, 2])
        self.assertEqual(M.raf_algorithm(s, fault="one-sweep")[0], [])
        self.assertEqual(M.raf_algorithm(chain(), fault="one-pass")[1], 1)

    def test_active(self):
        got, passes, _ = M.raf_algorithm(chain(), active=[1, 2])
        self.assertEqual((got, passes), ([], 1))

    def test_irreducible(self):
        left, runs = M.irreducible(chain(), [0, 1, 2])
        self.assertEqual((left, runs), ([0], 3))


class Schedules(unittest.TestCase):
    def test_lemma_schedules(self):
        s = chain()
        self.assertEqual(M.reduce_to_ra(s), [0, 1, 2])
        self.assertEqual(M.single_deletions(s, ("ra",), M.Stream(SEED, "a")), [0, 1, 2])
        self.assertEqual(M.single_deletions(s, ("fg",), M.Stream(SEED, "b")), [0, 1, 2, 3])
        self.assertEqual(M.violators(s, {0, 1, 2, 3}, ("ra",)), [3])
        self.assertEqual(M.violators(s, {1, 2, 3}, ("fg",)), [1, 2, 3])

    def test_closure_and_reference(self):
        s = chain()
        self.assertEqual(list(M.closure_bfs(s, {0, 1, 2, 3})), [1, 1, 1, 1])
        self.assertEqual(list(M.closure_bfs(s, {1, 2, 3})), [1, 0, 0, 0])
        self.assertEqual(M.reference(s, range(4), M.Stream(SEED, "c"))[0], [0, 1, 2])
        self.assertTrue(M.is_raf(s, [0]) and M.is_raf(s, [0, 1, 2]))
        self.assertFalse(M.is_raf(s, [0, 1]) or M.is_raf(s, []) or M.is_raf(s, [2]))


class Polymer(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(len(M.polymer_reactions(2)), 8)
        self.assertEqual(len(M.polymer_reactions(3)), 36)   # 000 and 111 give one ligation for two splits
        for n in (2, 3, 4):
            ours = M.polymer_reactions(n)
            self.assertEqual(set(ours), M.polymer_reactions_enumerated(n))
            self.assertEqual(len(set(ours)), len(ours))

    def test_numbering(self):
        self.assertEqual([M.mol(1, 0), M.mol(1, 1), M.mol(2, 0), M.mol(2, 3), M.mol(3, 0)], [0, 1, 2, 5, 6])
        lig = M.polymer_reactions(2)[:4]
        self.assertEqual(lig, [((0,), (2,)), ((0, 1), (3,)), ((0, 1), (4,)), ((1,), (5,))])


class Run(unittest.TestCase):
    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("nothex", results=os.path.join(HERE, "nonexistent-results"))

    def test_test_length(self):
        self.assertLessEqual(len(M.TEST), 600)

    def test_numpy(self):
        self.assertTrue(np.__version__)


if __name__ == "__main__":
    unittest.main()
