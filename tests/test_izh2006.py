"""Izhikevich's polychronous groups (poly/izh2006.py): the three changes and their refusals, the reading of the
program's printed lines, the seeds, and the verdict at and beside its condition. With the released file at inputs/
(or IZH_INPUTS) and g++ present, the changed program also compiles.

Run with: python3 -m unittest tests.test_izh2006
"""

import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("poly_izh2006", os.path.join(HERE, "..", "poly", "izh2006.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)
INPUTS = os.environ.get("IZH_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = os.path.isfile(os.path.join(INPUTS, M.INPUT[0]))
HAVE_GXX = shutil.which("g++") is not None

TOY = ("#include <iostream.h>\r\n#include <stdlib.h>\r\nvoid main()\r\n{\r\n\tsrand(0); \r\n\tcout << \"x\";\r\n}\r\n")


class Changes(unittest.TestCase):
    def test_applied_once_and_undone(self):
        new = M.changed(TOY)
        self.assertIn("#include <iostream>\nusing namespace std;", new)
        self.assertIn("int main(int argc, char **argv)", new)
        self.assertIn("srand(argc > 1 ? (unsigned) strtoul(argv[1], 0, 10) : 0);", new)
        self.assertTrue(M.only_the_changes(TOY, new))
        self.assertFalse(M.only_the_changes(TOY, new.replace("cout << \"x\"", "cout << \"y\"")))

    def test_refusals(self):
        with self.assertRaises(M.Refused):
            M.changed(TOY.replace("void main()", "int main()"))
        with self.assertRaises(M.Refused):
            M.changed(TOY + "\r\nvoid main()\r\n")
        with self.assertRaises(M.Refused):
            d = tempfile.mkdtemp()
            try:
                with open(os.path.join(d, M.INPUT[0]), "w") as fh:
                    fh.write(TOY)
                M.read_input(d)
            finally:
                shutil.rmtree(d)


class Reading(unittest.TestCase):
    LINES = ["sec=0, exc. frate=0.82,    exc->exc str=0,    inh. frate=7.395.\n",
             "sec=1, exc. frate=4.71,    exc->exc str=31.64,    inh. frate=37.95.\n", "\n",
             "i= 3, N_polychronous= 1, N_fired = 15, L_max = 7, T=53\n",
             "N_polychronous=4305\n", "***** scrambling ****\n", "N_polychronous=211\n",
             "ratio (true/shuffled) = 20.3962          "]

    def test_parse(self):
        secs, counts, ratio = M.parse(self.LINES)
        self.assertEqual(secs, [(0, 0.82, 0.0, 7.395), (1, 4.71, 31.64, 37.95)])
        self.assertEqual(counts, [4305, 211])
        self.assertAlmostEqual(ratio, 20.3962)

    def test_end_of_the_released_draw(self):
        aborted = {"counts": [4305], "ratio": None, "exit": -6,
                   "tail": ["N_polychronous=4305", "free(): double free detected in tcache 2"]}
        self.assertEqual(M.end_of(aborted), "exit status -6 after its count: free(): double free detected in tcache 2")
        whole = {"counts": [4305, 211], "ratio": 20.3962, "exit": 0, "tail": []}
        self.assertEqual(M.end_of(whole), "shuffled count 211, ratio 20.3962")

    def test_seeds(self):
        a = M.seeds_of("ab" * 32)
        self.assertEqual(a, M.seeds_of("ab" * 32))
        self.assertEqual(len(set(a)), 8)
        self.assertTrue(all(0 < s < 2 ** 31 for s in a))
        self.assertNotEqual(a, M.seeds_of("cd" * 32))


class Verdict(unittest.TestCase):
    def test_at_and_beside(self):
        import statistics
        self.assertTrue(all(M.conditions(statistics.median([2500] * 8)).values()))
        self.assertFalse(all(M.conditions(statistics.median([2499] * 8)).values()))
        mixed = [100, 200, 300, 2499, 2501, 9000, 9000, 9000]          # median 2,500
        self.assertTrue(all(M.conditions(statistics.median(mixed)).values()))
        self.assertFalse(all(M.conditions(statistics.median(mixed[:3] + [2498] + mixed[4:])).values()))


@unittest.skipUnless(HAVE and HAVE_GXX, "the released file and g++ are needed")
class Program(unittest.TestCase):
    def test_compiles_to_an_absolute_path(self):
        source = M.changed(M.read_input(INPUTS))
        work = tempfile.mkdtemp()
        here = os.getcwd()
        try:
            os.chdir(work)
            os.makedirs("w")
            exe = M.compile_program(source, "w")                       # a relative directory, as results/ is
            self.assertTrue(os.path.isabs(exe))
            self.assertTrue(os.access(exe, os.X_OK))
        finally:
            os.chdir(here)
            shutil.rmtree(work)


if __name__ == "__main__":
    unittest.main()
