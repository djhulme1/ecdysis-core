"""Kauers & Wood's released schemes (mm/kw.py): the inputs' hashes; the .exp reader and the exactness test on Strassen's
scheme written in the release's format, by hand; the naive scheme; the raised-coefficient control's expected count; the
coefficient statistics; the verdict at and beside each condition; the seed refused. None of the released schemes is read
here.

Run with: python3 -m unittest discover -s tests -p test_kw.py
"""

import hashlib
import importlib.util
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("mm_kw", os.path.join(HERE, "..", "mm", "kw.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

STRASSEN_EXP = """(a11 + a22)*(b11 + b22)*(c11 + c22)
(a21 + a22)*(b11)*(c12 - c22)
(a11)*(b12 - b22)*(c21 + c22)
(a22)*(b21 - b11)*(c11 + c12)
(a11 + a12)*(b22)*(-c11 + c21)
(a21 - a11)*(b11 + b12)*(c22)
(a12 - a22)*(b21 + b22)*(c11)
"""


class Reading(unittest.TestCase):
    def test_hash_refused(self):
        with tempfile.TemporaryDirectory() as d:
            name, sha = M.INPUTS[(4, 5, 6)]
            with open(os.path.join(d, name), "wb") as fh:
                fh.write(b"(a11)*(b11)*(c11)\n")
            with self.assertRaises(M.Refused):
                M.read_input(d, (4, 5, 6))

    def test_strassen_in_the_release_format(self):
        scheme = M.CHECK.read_flips(STRASSEN_EXP.encode("ascii"), 2, 2, 2)
        self.assertEqual(len(scheme), 7)
        self.assertEqual(M.CHECK.wrong_entries(scheme, 2, 2, 2, "Z"), 0)
        broken = M.CHECK.read_flips(STRASSEN_EXP.replace("(c11 + c22)", "(c11 + 3*c22)", 1).encode("ascii"), 2, 2, 2)
        self.assertEqual(M.CHECK.wrong_entries(broken, 2, 2, 2, "Z"), 4)       # the first product touches 4 entries
        self.assertEqual(M.CHECK.wrong_entries(broken, 2, 2, 2, "F2"), 0)      # but 3 = 1 modulo 2
        with self.assertRaises(ValueError):
            M.CHECK.read_flips(b"(a13)*(b11)*(c11)\n", 2, 2, 2)                 # a13 is outside a 2 x 2 A

    def test_naive(self):
        nv = M.naive(2, 3, 4)
        self.assertEqual(len(nv), 24)
        self.assertEqual(M.CHECK.wrong_entries(nv, 2, 3, 4, "Z"), 0)
        self.assertEqual(M.CHECK.wrong_entries(nv[:-1], 2, 3, 4, "Z"), 1)

    def test_altered_expectation(self):
        scheme = M.CHECK.read_flips(STRASSEN_EXP.encode("ascii"), 2, 2, 2)
        seed = "0f" * 32
        want = M.expected_altered(scheme, "strassen", seed)
        got = M.CHECK.control(scheme, 2, 2, 2, "Z", M.CHECK.Stream(seed, "strassen/control"))
        self.assertEqual(got, want)
        self.assertGreater(want, 0)

    def test_coefficient_stats(self):
        scheme = [({0: 1, 1: -3}, {2: 2}, {0: 1})]
        self.assertEqual(M.coefficient_stats(scheme), (3, 4))


class Verdict(unittest.TestCase):
    def found(self):
        return {f: {"products": M.TABLE[f][2], "wrong_integers": 0} for f in M.ORDER}

    def test_conditions(self):
        c = M.conditions(self.found())
        self.assertEqual(len(c), 8)
        self.assertTrue(all(c.values()))
        f = self.found()
        f[(5, 6, 7)]["wrong_integers"] = 1
        self.assertEqual(sum(M.conditions(f).values()), 7)
        f = self.found()
        f[(4, 5, 6)]["products"] = 91
        self.assertFalse(M.conditions(f)["(4,5,6) exact over the integers in 90 products"])

    def test_table(self):
        self.assertEqual(sorted(M.TABLE), sorted(M.INPUTS))
        self.assertEqual(sorted(M.ORDER), sorted(M.INPUTS))
        for (n, m, p), (naive, previous, ours) in M.TABLE.items():
            self.assertEqual(naive, n * m * p)
            self.assertLess(ours, previous)
        self.assertEqual(len({sha for _, sha in M.INPUTS.values()}), 8)

    def test_controls_and_seed(self):
        self.assertTrue(all(M.controls_known("ab" * 32).values()))
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")

    def test_outputs_named(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)
        self.assertTrue(hashlib.sha256(b"").hexdigest())


if __name__ == "__main__":
    unittest.main()
