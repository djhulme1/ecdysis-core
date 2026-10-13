"""Sayama's evoloop (evoloop/check.py): Table 2's transcription and its hash; Sayama's completion of the undefined
situations, at and beside each step; Golly's table format (variables bound within a transition, rotations, first
match, the unlisted unchanged); the built layout and the genome read back; the census on the torus (a hole across
the edge, a variant, a broken sheath, the background); the verdict at and beside each condition; and, with Golly's
files at inputs/ (or EVOLOOP_INPUTS), the ancestor, the two rules compared and a short run.

Needs numpy and scipy (the scipy-notebook image). Run with: python3 -m unittest tests.test_evoloop
"""

import importlib.util
import os
import sys
import tempfile
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("evoloop_check", os.path.join(HERE, "..", "evoloop", "check.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M          # so that the worker pool can pickle run_space and alone by name
_spec.loader.exec_module(M)

INPUTS = os.environ.get("EVOLOOP_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = all(os.path.isfile(os.path.join(INPUTS, n)) for n in M.INPUTS)


class Table2(unittest.TestCase):
    def test_transcription_and_its_hash(self):
        rules = M.table2_rules()
        self.assertEqual(len(rules), 258)
        self.assertIn((0, 0, 0, 0, 1, 2), rules)
        with self.assertRaises(M.Refused):
            M.table2_rules(M.TABLE2.replace("70312->0", "70312->1"))

    def test_two_images_refused(self):
        with self.assertRaises(M.Refused):
            M.sayama_rules([(1, 0, 2, 7, 2, 7), (1, 2, 0, 2, 7, 1)])   # the same situation turned, two images


class Completion(unittest.TestCase):
    def setUp(self):
        self.t, self.defined = M.sayama_rules()

    def test_rotations_of_a_listed_rule(self):
        # 10024->4: C1 T0 R0 B2 L4 -> 4, and its three turns
        for nb in M.turns(0, 0, 2, 4):
            self.assertEqual(int(self.t[(1,) + nb]), 4)

    def test_the_steps_for_undefined_situations(self):
        t = self.t
        self.assertEqual(int(t[8, 1, 2, 3, 4]), 0)                     # step 2: 8 -> 0
        self.assertFalse(self.defined[0, 8, 3, 0, 0])
        self.assertEqual(int(t[0, 8, 3, 0, 0]), 8)                     # step 3a: a live neighbour beside the 8
        self.assertEqual(int(t[0, 8, 1, 0, 0]), 0)                     # 3a: none, unchanged
        self.assertEqual(int(t[1, 8, 0, 0, 1]), 1)
        self.assertEqual(int(t[5, 8, 0, 0, 0]), 0)                     # 3b
        self.assertEqual(int(t[6, 8, 0, 0, 0]), 1)                     # 3c
        self.assertFalse(self.defined[3, 3, 3, 3, 3])
        self.assertEqual(int(t[3, 3, 3, 3, 3]), 8)                     # step 4: undefined, no 8 near: dissolve
        self.assertEqual(int(t[0, 6, 6, 6, 6]), 0)                     # step 4: but 0 stays 0
        self.assertTrue(((t >= 0) & (t <= 8)).all())


GOLLY = """@RULE Evoloop

@TABLE
n_states:9
neighborhood:vonNeumann
symmetries:rotate4
var a={1,2}
var b={1,2}
0,a,a,0,0,5
0,a,b,0,0,6
0,1,2,0,0,7
3,0,0,0,0,4
"""


class GollyFormat(unittest.TestCase):
    def test_variables_turns_first_match_and_the_unlisted(self):
        t, n = M.golly_rules(GOLLY)
        self.assertEqual(n, 4)
        self.assertEqual(int(t[0, 1, 1, 0, 0]), 5)                     # a named twice: one value
        self.assertEqual(int(t[0, 2, 2, 0, 0]), 5)
        self.assertEqual(int(t[0, 1, 2, 0, 0]), 6)                     # the first match wins over the later 7
        self.assertEqual(int(t[0, 0, 0, 1, 2]), 6)                     # turned twice
        self.assertEqual(int(t[3, 0, 0, 0, 0]), 4)
        self.assertEqual(int(t[2, 3, 4, 5, 6]), 2)                     # unlisted: unchanged

    def test_refusals(self):
        with self.assertRaises(M.Refused):
            M.golly_rules(GOLLY.replace("@RULE Evoloop", "@RULE Langton"))
        with self.assertRaises(M.Refused):
            M.golly_rules(GOLLY.replace("rotate4", "permute"))


class Layout(unittest.TestCase):
    def test_built_loops_and_their_genomes(self):
        for n in M.SIZES:
            g = M.build(n)
            self.assertEqual(g.shape, (n + 4, n + 4))
            self.assertEqual(M.genome_of(g, n), "77" + "44" + "7" * (n - 2))
            self.assertFalse(g[3:n + 1, 3:n + 1].any())                # the hole
            self.assertEqual(int(g[n + 3, n + 2]), 5)
        self.assertEqual(M.genome_of(M.build(6, "7744"), 6), "7744")
        with self.assertRaises(M.Refused):
            M.build(3)
        broken = M.build(8)
        broken[1, 1] = 2
        self.assertIsNone(M.genome_of(broken, 8))


class Census(unittest.TestCase):
    def test_on_the_torus(self):
        L = 60
        g = np.zeros((L, L), dtype=np.uint8)
        p = M.build(6)
        g[0:10, 0:10] = p
        g = np.roll(np.roll(g, -4, 0), -3, 1)                         # the loop now straddles both edges
        loops, variants = M.census(g)
        self.assertEqual((loops, variants), ({6: 1}, 0))
        g[30:34, 30:36] = 2
        g[31:33, 31:35] = 0                                             # a 2 x 4 variant
        self.assertEqual(M.census(g), ({6: 1}, 1))
        g[30, 32] = 1                                                   # its ring broken
        self.assertEqual(M.census(g), ({6: 1}, 0))
        self.assertEqual(M.census(np.zeros((L, L), dtype=np.uint8)), ({}, 0))

    def test_drawn(self):
        ok, drawn = M.drawn_census()
        self.assertTrue(ok, drawn)


class Verdict(unittest.TestCase):
    FIRST = {n: 100 + 20 * n for n in M.SIZES}

    def test_at_and_beside_each_condition(self):
        good = ({199: 4, 200: 4, 201: 5}, dict(self.FIRST), {n: True for n in M.SIZES})
        self.assertEqual(sum(M.conditions(*good).values()), 3)
        tie = dict(self.FIRST)
        tie[9] = tie[8]
        late = dict(self.FIRST)
        late[13] = None
        for bad in (({199: 4, 200: 5, 201: None}, good[1], good[2]), (good[0], tie, good[2]),
                    (good[0], late, good[2]), (good[0], good[1], {**good[2], 7: False})):
            with self.subTest(bad=bad):
                self.assertEqual(sum(M.conditions(*bad).values()), 2)

    def test_top_needs_a_strict_lead(self):
        self.assertEqual(M.top({"4": 9, "5": 3}), 4)
        self.assertIsNone(M.top({"4": 3, "5": 3}))
        self.assertIsNone(M.top({}))


@unittest.skipUnless(HAVE, "Golly's files are not at inputs/ (or EVOLOOP_INPUTS)")
class WithInputs(unittest.TestCase):
    def test_ancestor_rules_and_a_short_run(self):
        anc = M.read_rle(M.load(INPUTS, "Evoloop.rle"))
        self.assertTrue(np.array_equal(M.build(13), anc))
        self.assertEqual(M.genome_of(anc, 13), M.GENOME)
        golly, n = M.golly_rules(M.load(INPUTS, "Evoloop.rule"))
        sayama, defined = M.sayama_rules()
        self.assertEqual(n, 132)
        self.assertTrue(np.array_equal(golly[defined], sayama[defined]))
        alone = M.alone(4, sayama.ravel())
        self.assertTrue(alone["faithful"])
        self.assertEqual(len(alone["births"]), 3)
        updates = M.UPDATES
        M.UPDATES = 2000
        try:
            with tempfile.TemporaryDirectory() as d:
                out, detail = M.run("0" * 64, inputs=INPUTS, results=d, spaces=(200,), beside=(), golly_spaces=())
        finally:
            M.UPDATES = updates
        self.assertEqual(tuple(out), M.OUTPUTS)
        self.assertEqual(out["controls_passed"], out["controls_total"])
        self.assertEqual(out["end_200"], "15 loops (13: 15); 0 variants")
        self.assertEqual(out["end_199"], "not run")
        self.assertEqual(out["births_rising"], 1)


if __name__ == "__main__":
    unittest.main()
