"""Mitchell, Hraber & Crutchfield's GA (alife/eoc.py, alife/eoc.c): the paper's bins; the neighbourhood convention,
checked by the GKL rule's published code; the plain simulation on rules whose action is known; the C simulation against
it; the fitness of rules whose fitness is known; a short GA run, repeatable, its elite ranked and its population kept
at 100; the whole pipeline on two short runs; and the seed refused.

Needs gcc (the pinned buildpack-deps image). Run with: python3 -m unittest tests.test_eoc
"""

import importlib.util
import os
import random
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("alife_eoc", os.path.join(HERE, "..", "alife", "eoc.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)

SEED = "0" * 63 + "1"
HAVE_GCC = shutil.which("gcc") is not None


class Bins(unittest.TestCase):
    def test_bin_edges(self):
        # lambda = n/128 in bins of width 1/15; lambda = 1 in the last
        cases = {0: 0, 8: 0, 9: 1, 26: 3, 34: 3, 35: 4, 63: 7, 64: 7, 68: 7, 69: 8, 93: 10, 94: 11, 103: 12,
                 110: 12, 111: 13, 127: 14, 128: 14}
        for n, b in cases.items():
            with self.subTest(n=n):
                self.assertEqual(M.lam_bin(n), b)
                self.assertTrue(b / 15 <= n / 128 < (b + 1) / 15 or n == 128)

    def test_named_bins(self):
        self.assertEqual([round(b / 15, 3) for b in M.PACKARD], [0.2, 0.8])
        self.assertEqual((M.CENTRAL.start / 15, M.CENTRAL.stop / 15), (4 / 15, 11 / 15))
        self.assertEqual(M.histogram([0, 64, 64, 128]), [1] + [0] * 6 + [2] + [0] * 6 + [1])


class Rules(unittest.TestCase):
    def test_gkl_matches_its_published_code(self):
        # The GKL rule's 128 bits in neighbourhood order 0000000, 0000001, ..., as hexadecimal, is the code Mitchell,
        # Crutchfield and Das list for it (1996): this pins the convention that cell i - 3 is the most significant bit.
        bits = M.gkl()
        h = "".join("%X" % int("".join(map(str, bits[i:i + 4])), 2) for i in range(0, 128, 4))
        self.assertEqual(h, "005F005F005F005F005FFF5F005FFF5F")
        self.assertEqual(sum(bits), 64)

    def test_hex_round_trip(self):
        rng = random.Random(2)
        for _ in range(20):
            bits = [rng.randint(0, 1) for _ in range(128)]
            self.assertEqual(M.hex_rule(M.rule_hex(bits)), bits)

    def test_plain_step_on_known_rules(self):
        rng = random.Random(3)
        cells = [rng.randint(0, 1) for _ in range(M.L)]
        identity = [(nb >> 3) & 1 for nb in range(128)]
        left = [(nb >> 4) & 1 for nb in range(128)]          # the next state is the left neighbour's
        self.assertEqual(M.plain_step(identity, cells), cells)
        self.assertEqual(M.plain_step(left, cells), cells[-1:] + cells[:-1])
        self.assertEqual(M.neighbourhood([1, 0, 0, 0, 0, 0, 0, 0, 0], 3), 0b1000000)

    def test_gkl_fixed_points(self):
        rule = M.gkl()
        self.assertEqual(M.plain_step(rule, [0] * M.L), [0] * M.L)
        self.assertEqual(M.plain_step(rule, [1] * M.L), [1] * M.L)
        lone = [0] * M.L
        lone[70] = 1
        self.assertEqual(M.plain_step(rule, lone), [0] * M.L)

    def test_words_are_fixed_by_seed_and_label(self):
        self.assertEqual(M.words(SEED, "a"), M.words(SEED, "a"))
        self.assertNotEqual(M.words(SEED, "a"), M.words(SEED, "b"))
        self.assertTrue(all(len(w) == 16 for w in M.words(SEED, "a")))


@unittest.skipUnless(HAVE_GCC, "no gcc")
class Simulation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp()
        cls.exe = M.build(cls.work)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work)

    def test_c_agrees_with_the_plain_simulation(self):
        rng = random.Random(4)
        for _ in range(60):
            bits = [rng.randint(0, 1) for _ in range(128)]
            cells = [rng.randint(0, 1) for _ in range(M.L)]
            steps = rng.randint(0, 30)
            ref = cells
            for _ in range(steps):
                ref = M.plain_step(bits, ref)
            self.assertEqual(M.trace(self.exe, bits, cells, steps), ref)

    def test_known_fitnesses(self):
        zero = M.fit_sets(self.exe, SEED, "t/zero", [0] * 128, 4, self.work)
        self.assertTrue(all(abs(z - 0.5) < 1e-9 for z in zero))
        one = M.fit_sets(self.exe, SEED, "t/one", [1] * 128, 4, self.work)
        self.assertTrue(all(abs(z - 0.5) < 1e-9 for z in one))
        ident = M.fit_sets(self.exe, SEED, "t/id", [(nb >> 3) & 1 for nb in range(128)], 10, self.work)
        self.assertLess(abs(sum(ident) / len(ident) - 112 / 149), 0.015)
        g = M.fit_sets(self.exe, SEED, "t/gkl", M.gkl(), 4, self.work)
        self.assertGreater(min(g), 0.95)

    def test_short_ga_run(self):
        saved = M.GENS
        M.GENS = 3
        try:
            r1 = M.ga_run(self.exe, SEED, "t/ga", True, self.work)
            r2 = M.ga_run(self.exe, SEED, "t/ga", True, self.work)
            r3 = M.ga_run(self.exe, SEED, "t/ga2", True, self.work)
            d = M.ga_run(self.exe, SEED, "t/drift", False, self.work)
        finally:
            M.GENS = saved
        self.assertEqual(r1, r2)
        self.assertNotEqual(r1, r3)
        self.assertEqual(sorted(r1["gens"]), [0, 1, 2, 3])
        self.assertTrue(all(len(v) == M.POP for v in r1["gens"].values()))
        fits = [x["fitness"] for x in r1["final"]]
        self.assertEqual(fits, sorted(fits, reverse=True))
        self.assertEqual(sum(x["elite"] for x in r1["final"]), M.ELITE)
        self.assertTrue(all(x["fitness"] == -1.0 for x in d["final"]))
        self.assertEqual(sorted(x["ones"] for x in r1["final"]), sorted(r1["gens"][3]))


@unittest.skipUnless(HAVE_GCC, "no gcc")
class Pipeline(unittest.TestCase):
    def test_two_short_runs_write_every_output(self):
        saved = (M.RUNS, M.GENS)
        M.RUNS, M.GENS = 2, 5
        tmp = tempfile.mkdtemp()
        try:
            out, detail = M.run(SEED, results=tmp)
        finally:
            M.RUNS, M.GENS = saved
            shutil.rmtree(tmp)
        self.assertEqual(list(out), list(M.OUTPUTS))
        self.assertEqual(out["final_rules"], 200)
        ctl = list(detail["controls"].values())
        self.assertTrue(all(ctl[:3]), detail["controls"])    # the fourth needs 3,000 rules to be sure of
        self.assertEqual(sum(int(x) for x in out["histogram"].split()), 200)

    def test_refuses_a_bad_seed(self):
        with self.assertRaises(M.Refused):
            M.run("xyz", results=os.path.join(HERE, "_never"))


if __name__ == "__main__":
    unittest.main()
