"""Pauli et al.'s sensitivity of the polychronization model (poly/pauli2018.py): the changes and their refusals, the
counts at 5 and 10 layers and the Poisson background on a toy program (not the released one), the reading of the
printed lines, the seeds, and the verdict at and beside each threshold. With the released file at inputs/ (or
IZH_INPUTS) and g++ present, both changed programs also compile; neither is run.

Run with: python3 -m unittest tests.test_pauli2018
"""

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("poly_pauli2018", os.path.join(HERE, "..", "poly", "pauli2018.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)
INPUTS = os.environ.get("IZH_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = os.path.isfile(os.path.join(INPUTS, M.INPUT[0]))
HAVE_GXX = shutil.which("g++") is not None

# A toy with every anchor once, in the released file's style (tabs, CRLF). Its search counts a candidate for each
# L_max from 0 to 11 and discards those with L_max % 4 == 3, so the counts at 5, 7 and 10 layers are 5, 3 and 1; its
# main draws the background a hundred thousand times and prints the mean and variance of the spikes a neuron gets in a
# millisecond (I / 10) and how often it gets two against one.
TOY = "\r\n".join([
    "#include <iostream.h>",
    "#include <stdlib.h>",
    "#include <stdio.h>",
    "#include <math.h>",
    "#define rand01 (0.9999999*double(rand())/RAND_MAX) ",
    "const\tint\tN = 1000;",
    "int\t\t\tN_polychronous;",
    "int\t\tmin_group_path = 7;",
    "void\tpolychronous(int L_max, int discard)",
    "{",
    "\t\t\tif ((discard == 0) & (L_max >= min_group_path))",
    "\t\t\t{",
    "\t\t\t\tN_polychronous++;",
    "\t\t\t}",
    "}",
    "void\tall_polychronous()",
    "{",
    "\tN_polychronous=0;",
    "\tfor (int L = 0; L < 12; L++) polychronous(L, (L % 4) == 3);",
    "\tcout << \"\\nN_polychronous=\" << N_polychronous << \"\\n\";",
    "}",
    "void main()",
    "{",
    "\tint i, t, sec;",
    "\tdouble I[N];",
    "\tdouble s1 = 0, s2 = 0, n1 = 0, n2 = 0;",
    "\tsrand(0); ",
    "\tall_polychronous();",
    "\tfor (sec=0; sec<60*60*5; sec++) if (sec == 2) break;",
    "\tfor (t=0; t<100000; t++)",
    "\t{",
    "\t\tfor (i=0;i<N;i++) I[i] = 0;",
    "\t\t\tI[int(floor(N*rand01))]=20;",
    "\t\tfor (i=0;i<N;i++) { double k = I[i]/10; s1 += k; s2 += k*k; if (k == 1) n1++; if (k == 2) n2++; }",
    "\t}",
    "\tdouble m = s1/1e8;",
    "\tprintf(\"sec %d mean %.8f var %.8f two_over_one %.6f\\n\", sec, m, s2/1e8 - m*m, n1 > 0 ? n2/n1 : -1.0);",
    "}",
    ""])


def build_and_run(source, work):
    src = os.path.join(work, "toy.cpp")
    with open(src, "w", encoding="ascii", newline="") as fh:
        fh.write(source)
    exe = os.path.join(work, "toy")
    subprocess.run(["g++", "-O2", "-w", "-o", exe, src], check=True)
    return subprocess.run([exe], capture_output=True, text=True, check=True).stdout


class Changes(unittest.TestCase):
    def test_each_program_applied_and_undone(self):
        for kind in ("O", "P"):
            ch = M.changes_of(kind)
            new = M.apply(TOY, ch)
            self.assertTrue(M.undone(TOY, new, ch))
            self.assertIn("N_layers5, N_layers10;", new)
            self.assertIn("if (L_max >= 5) N_layers5++; if (L_max >= 10) N_layers10++;", new)
            self.assertLess(new.index("N_layers5++"), new.index("if ((discard == 0) & (L_max >= min_group_path))"))
            self.assertLess(new.index('"\\nN_layers5="'), new.index('"\\nN_polychronous="'))
            self.assertEqual("I[int(floor(N*rand01))]=20;" in new, kind == "O")
            self.assertIn("for (sec=0; sec<60*60*5; sec++)", new)
        self.assertFalse(M.undone(TOY, M.apply(TOY, M.changes_of("O")).replace("t<100000", "t<99"),
                                  M.changes_of("O")))

    def test_smoke_bound_only_when_asked(self):
        new = M.apply(TOY, M.changes_of("P", seconds=60))
        self.assertIn("for (sec=0; sec<60; sec++)", new)
        self.assertTrue(M.undone(TOY, new, M.changes_of("P", seconds=60)))
        self.assertEqual(M.changes_of("O"), M.changes_of("O", seconds=M.SECONDS))

    def test_refusals(self):
        with self.assertRaises(M.Refused):
            M.apply(TOY.replace("\tN_polychronous=0;", "\tN_polychronous = 0;"), M.changes_of("O"))
        with self.assertRaises(M.Refused):
            M.apply(TOY + "\r\n\t\t\tI[int(floor(N*rand01))]=20;\r\n", M.changes_of("P"))
        with self.assertRaises(ValueError):
            M.changes_of("Q")


@unittest.skipUnless(HAVE_GXX, "g++ is needed")
class ToyProgram(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.work)

    def numbers(self, out):
        layers = re.search(r"^N_layers5=(\d+), N_layers10=(\d+)$", out, re.M)
        seven = re.search(r"^N_polychronous=(\d+)$", out, re.M)
        stats = re.search(r"^sec (\d+) mean (\S+) var (\S+) two_over_one (\S+)$", out, re.M)
        return layers, seven, stats

    def test_counts_and_background_of_O(self):
        layers, seven, stats = self.numbers(build_and_run(M.apply(TOY, M.changes_of("O")), self.work))
        self.assertEqual((int(layers.group(1)), int(seven.group(1)), int(layers.group(2))), (5, 3, 1))
        self.assertAlmostEqual(float(stats.group(2)), 0.002, places=9)      # one neuron in 1,000 gets 20: k = 2
        self.assertEqual(float(stats.group(4)), -1.0)                        # never exactly one spike's worth

    def test_counts_and_background_of_P(self):
        layers, seven, stats = self.numbers(build_and_run(M.apply(TOY, M.changes_of("P")), self.work))
        self.assertEqual((int(layers.group(1)), int(seven.group(1)), int(layers.group(2))), (5, 3, 1))
        mean, var, two = float(stats.group(2)), float(stats.group(3)), float(stats.group(4))
        self.assertLess(abs(mean - 0.04), 1e-4)      # 40 Hz in 1 ms steps, 1e8 draws: sd of the mean 2e-5
        self.assertLess(abs(var - 0.04), 1.5e-4)     # a Poisson law's variance is its mean (sd about 2e-5)
        self.assertLess(abs(two - 0.02), 5e-4)       # P(2)/P(1) = 0.04/2 (sd about 7e-5)

    def test_smoke_bound(self):
        _, _, stats = self.numbers(build_and_run(M.apply(TOY, M.changes_of("O", seconds=1)), self.work))
        self.assertEqual(stats.group(1), "1")


class Reading(unittest.TestCase):
    LINES = ["sec=0, exc. frate=0.82,    exc->exc str=0,    inh. frate=7.395.\n",
             "sec=1, exc. frate=4.71,    exc->exc str=31.64,    inh. frate=37.95.\n", "\n",
             "N_layers5=27, N_layers10=2\n", "N_polychronous=11\n"]

    def test_parse(self):
        secs, counts, layers = M.parse(self.LINES)
        self.assertEqual(secs, [(0, 0.82, 0.0, 7.395), (1, 4.71, 31.64, 37.95)])
        self.assertEqual(counts, [11])
        self.assertEqual(layers, [(27, 2)])
        run = {"counts": counts, "layers": layers, "secs": secs}
        self.assertEqual(M.by_layer(run), {5: 27, 7: 11, 10: 2})
        self.assertEqual(M.last_rates(run, last=2), ((0.82 + 4.71) / 2, (7.395 + 37.95) / 2, 31.64))
        self.assertIsNone(M.by_layer({"counts": [], "layers": [], "secs": []}))

    def test_seeds(self):
        a = M.seeds_of("ab" * 32)
        self.assertEqual(a, M.seeds_of("ab" * 32))
        self.assertEqual(len(set(a)), M.DRAWS)
        self.assertTrue(all(0 < s < 2 ** 31 for s in a))
        self.assertEqual(a, M.izh.seeds_of("ab" * 32, M.DRAWS))


class Verdict(unittest.TestCase):
    PAPER = {5: 27116, 7: 4305, 10: 608}
    O = [1000, 2000, 3000, 4000]                                   # median 2,500

    def cond(self, p7, released=None, r5=(6.0,) * 4, r10=(0.1,) * 4):
        return M.conditions(self.O, p7, released or self.PAPER, list(r5), list(r10))

    def test_thresholds(self):
        self.assertAlmostEqual(M.NOISE_BOUND, 0.316228, places=6)
        self.assertAlmostEqual(M.UP5, 2.509726, places=6)
        self.assertAlmostEqual(M.DOWN10, 0.375807, places=6)

    def test_paper_numbers_pass(self):
        self.assertTrue(all(self.cond([291, 291, 291, 291]).values()))

    def test_noise_at_and_beside(self):
        self.assertTrue(all(self.cond([700, 780, 800, 900]).values()))          # median 790: 0.316
        self.assertFalse(all(self.cond([700, 782, 800, 900]).values()))         # median 791: 0.3164
        self.assertFalse(all(M.conditions([0, 0, 0, 0], [0, 0, 0, 0], self.PAPER, [6.0] * 4, [0.1] * 4).values()))

    def test_layers_at_and_beside(self):
        ok = dict(self.PAPER)
        self.assertTrue(all(self.cond([291] * 4, {**ok, 5: 10805}).values()))
        self.assertFalse(all(self.cond([291] * 4, {**ok, 5: 10804}).values()))
        self.assertTrue(all(self.cond([291] * 4, {**ok, 10: 1617}).values()))
        self.assertFalse(all(self.cond([291] * 4, {**ok, 10: 1618}).values()))
        self.assertFalse(all(self.cond([291] * 4, {5: 0, 7: 0, 10: 0}).values()))
        self.assertFalse(all(self.cond([291] * 4, r5=(6.0, 2.5, 2.5, 2.5)).values()))      # median 2.5
        self.assertTrue(all(self.cond([291] * 4, r5=(6.0, 2.51, 2.51, 2.51)).values()))    # median 2.51
        self.assertFalse(all(self.cond([291] * 4, r10=(0.1, 0.7, 0.7, 0.7)).values()))     # median 0.7
        self.assertFalse(all(self.cond([291] * 4, r5=(6.0, None, 6.0, 6.0)).values()))


@unittest.skipUnless(HAVE and HAVE_GXX, "the released file and g++ are needed")
class Program(unittest.TestCase):
    def test_both_compile_and_undo(self):
        original = M.izh.read_input(INPUTS)
        work = tempfile.mkdtemp()
        try:
            for kind in ("O", "P"):
                source = M.apply(original, M.changes_of(kind))
                self.assertTrue(M.undone(original, source, M.changes_of(kind)))
                d = os.path.join(work, kind)
                os.makedirs(d)
                exe = M.izh.compile_program(source, d)
                self.assertTrue(os.access(exe, os.X_OK))
        finally:
            shutil.rmtree(work)


if __name__ == "__main__":
    unittest.main()
