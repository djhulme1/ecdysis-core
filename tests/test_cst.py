"""Capcarrere, Sipper & Tomassini's classifier (ca/cst.py and ca/cst.c): the specification on configurations written
here; the paper's definition of rule 184 against Wolfram's table; the mirror of rule 184; the blocks of a ring; the
seed's stream; the verdict's bookkeeping; and, where gcc is present, the C steps against cell-by-cell steps, the C
count on the identity rule and rule 30, and the C run of long rings. Rule 184 is not run through the specification
here: that is the check's own work.

Run with: python3 -m unittest discover -s tests -p test_cst.py
"""

import importlib.util
import os
import random
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("ca_cst", os.path.join(HERE, "..", "ca", "cst.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
HAVE_GCC = shutil.which("gcc") is not None


def b(s):
    return [int(ch) for ch in s]


class Specification(unittest.TestCase):
    def test_cases(self):
        self.assertTrue(M.meets_cells(b("1101010"), 2 * 4))        # 4 of 7: a 11 block, no 00
        self.assertFalse(M.meets_cells(b("1100110"), 2 * 4))       # a 00 block too
        self.assertFalse(M.meets_cells(b("1010100"), 2 * 4))       # no 11, a 00: wrong side
        self.assertTrue(M.meets_cells(b("0010101"), 2 * 3))        # 3 of 7: a 00 block, no 11
        self.assertTrue(M.meets_cells(b("101010"), 6))             # exactly half: alternating
        self.assertFalse(M.meets_cells(b("110100"), 6))
        self.assertTrue(M.meets_cells(b("1010101"), 2 * 4))        # the 11 pair wraps from the last cell to the first

    def test_initial_density_chooses_the_case(self):
        # the case is chosen by k at time 0, passed in, not by the configuration examined
        self.assertFalse(M.meets_cells(b("1101010"), 2 * 3))

    def test_steps(self):
        self.assertEqual([M.steps(n) for n in (3, 4, 5, 28, 149)], [2, 2, 3, 14, 75])


class Rules(unittest.TestCase):
    def test_definition_is_184(self):
        self.assertEqual(M.wolfram(M.table_of_184_definition()), 184)
        x = b("0110100111")
        self.assertEqual(M.step184_cells(x), M.step_cells(x, 184))

    def test_mirror(self):
        rng = random.Random(1)
        for _ in range(50):
            x = [rng.randint(0, 1) for _ in range(rng.randint(3, 20))]
            self.assertEqual(M.step_cells(x, 226), M.step_cells(x[::-1], 184)[::-1])

    def test_numbering(self):
        self.assertEqual(M.wolfram({format(k, "03b"): (90 >> k) & 1 for k in range(8)}), 90)
        self.assertEqual(M.step_cells(b("00100"), 90), b("01010"))
        self.assertEqual(M.step_cells(b("0001000"), 30), b("0011100"))


class Blocks(unittest.TestCase):
    def test_blocks(self):
        self.assertEqual(M.blocks(b("1010101")), [(1, 2)])          # the last cell and the first make the block
        self.assertEqual(sorted(M.blocks(b("1100101000"))), [(0, 2), (0, 3), (1, 2)])
        self.assertEqual(M.blocks(b("101010")), [])
        self.assertEqual(M.blocks(b("1111")), [(1, 4)])

    def test_bits(self):
        self.assertEqual(M.word_of(M.bits_of(0b10110, 5)), 0b10110)


class Seed(unittest.TestCase):
    def test_stream(self):
        a, c = M.Stream("0" * 64, "x"), M.Stream("0" * 64, "x")
        self.assertEqual([a.bit() for _ in range(600)], [c.bit() for _ in range(600)])
        d = M.Stream("0" * 64, "y")
        self.assertNotEqual([M.Stream("0" * 64, "x").bit() for _ in range(64)], [d.bit() for _ in range(64)])
        self.assertTrue(all(0 <= M.Stream("1" * 64, "z").below(7) < 7 for _ in range(10)))

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


class Verdict(unittest.TestCase):
    def test_conditions(self):
        rows = [{"N": n, "failures": 0} for n in range(M.N_MIN, M.N_MAX + 1)]
        self.assertTrue(all(M.conditions(rows).values()))
        self.assertFalse(all(M.conditions(rows[:-1]).values()))         # a ring missing
        rows[5] = dict(rows[5], failures=1)
        self.assertFalse(all(M.conditions(rows).values()))

    def test_outputs(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)


@unittest.skipUnless(HAVE_GCC, "no gcc")
class CProgram(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp()
        cls.exe = M.build(cls.work)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def test_steps_equal(self):
        rng = random.Random(2)
        for N in (3, 5, 8, 13, 28, 30):
            for _ in range(10):
                x = rng.randrange(1 << N)
                bx = M.bits_of(x, N)
                self.assertEqual(M.c_step184(self.exe, N, x), M.word_of(M.step184_cells(bx)))
                for rule in (30, 90, 110, 184, 226):
                    self.assertEqual(M.c_step(self.exe, rule, N, x), M.word_of(M.step_cells(bx, rule)))
                self.assertEqual(M.c_step(self.exe, 30, N, x, 3),
                                 M.word_of(M.step_cells(M.step_cells(M.step_cells(bx, 30), 30), 30)))

    def test_count_against_cells(self):
        for rule in (204, 30):
            for N in (4, 5, 7):
                fails, first = M.c_lines(self.exe, "count", rule, N)[0]
                want = []
                for s in range(1 << N):
                    y = M.bits_of(s, N)
                    k = sum(y)
                    for _ in range(M.steps(N)):
                        y = M.step_cells(y, rule)
                    if not M.meets_cells(y, 2 * k):
                        want.append(s)
                self.assertEqual((fails, first), (len(want), want[0] if want else -1))

    def test_long_rings(self):
        rng = random.Random(3)
        configs = [[rng.randint(0, 1) for _ in range(149)] for _ in range(5)] + [b("0110"), b("100")]
        path = os.path.join(self.work, "c.txt")
        M.write_configs(path, configs)
        got = M.c_final(self.exe, path, 30, 9)
        for x, g in zip(configs, got):
            y = list(x)
            for _ in range(9):
                y = M.step_cells(y, 30)
            self.assertEqual(y, g)
        counts = M.c_lines(self.exe, "sample", path, 2)[0]
        self.assertEqual(len(counts), 256)
        want_204 = sum(M.meets_cells(x, 2 * sum(x)) for x in configs)    # the identity leaves each as it is
        self.assertEqual(counts[204], want_204)

    def test_refusals(self):
        bad = os.path.join(self.work, "bad.txt")
        with open(bad, "w") as fh:
            fh.write("0120\n")
        with self.assertRaises(Exception):
            M.c_lines(self.exe, "sample", bad, 2)
        with self.assertRaises(Exception):
            M.c_lines(self.exe, "theorem", 2, 5)            # rings below 3 cells are refused


if __name__ == "__main__":
    unittest.main()
