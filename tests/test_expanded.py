"""Lenia and Expanded Universe, on made-up cases: the run-length cells decoded as LeniaNDKC decodes them and anything
else refused; a pattern file read with its headings; a rule's default channels in LeniaNDKC's order; a pattern centred
in the world; the kernels normalised; the parts of a world counted on the torus; and the measure on one and two
copies of a pattern.

With the author's files at inputs/ (or EXPANDED_INPUTS), also the selection (18 replicators, 7, 6 and 3 under the
233s.json headings) and the port against the author's own Board and Automaton, bit for bit, on one pattern of each
rule.

Run with: python3 -m unittest discover -s tests
"""

import hashlib
import importlib.util
import os
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("lenia_expanded", os.path.join(HERE, "..", "lenia", "expanded.py"))
E = importlib.util.module_from_spec(_spec)
sys.modules["lenia_expanded"] = E
_spec.loader.exec_module(E)


class Cells(unittest.TestCase):
    def test_values(self):
        self.assertEqual([E.ch2val(c) for c in (".", "b", "o", "A", "X", "pA", "yO")], [0, 0, 255, 1, 24, 25, 255])

    def test_rows_counts_and_padding(self):
        A = E.rle2cells("2A.$pAB2$o!")                              # "2$" ends a row and adds one empty row
        want = np.array([[1, 1, 0], [25, 2, 0], [0, 0, 0], [255, 0, 0]]) / 255
        self.assertEqual(A.shape, (4, 3))
        self.assertTrue(np.array_equal(A, want))
        B = E.rle2cells("A$!")                                       # a "$" before "!" leaves an empty last row
        self.assertTrue(np.array_equal(B, np.array([[1], [0]]) / 255))

    def test_refusals(self):
        for bad in ("A Z$", "AY$", "pZ$", "A%B$", "@AB$"):
            with self.assertRaises(E.Refused, msg=bad):
                E.rle2cells(bad)


class Reading(unittest.TestCase):
    def test_headings(self):
        text = '"one",\n{"code":"a","name":"x","params":[],"cells":""},\n"two",\n{"code":"b"},\n{"code":"c"},\n'
        got = E.read_found(text)
        self.assertEqual([(h, p["code"]) for h, p in got], [("one", "a"), ("two", "b"), ("two", "c")])
        self.assertRaises(E.Refused, E.read_found, '"h",\n3,\n')

    def test_default_channels(self):
        p = {"R": 15, "T": 10, "b": "1,1/2", "m": 0.1, "s": 0.01, "kn": 1, "gn": 1}
        kernels, cells = E.rule_of({"params": [dict(p) for _ in range(15)], "cells": ["A$", "A$", "A$"]}, 3, 3, 1)
        self.assertEqual([k.c for k in kernels], [[0, 0]] * 3 + [[1, 1]] * 3 + [[2, 2]] * 3
                         + [[0, 1], [0, 2], [1, 0], [1, 2], [2, 0], [2, 1]])
        self.assertEqual(kernels[0].b, [1.0, 0.5])
        self.assertEqual((kernels[0].h, kernels[0].r), (1, 1))
        self.assertRaises(E.Refused, E.rule_of, {"params": [dict(p)] * 14, "cells": ["A$"] * 3}, 3, 3, 1)
        self.assertRaises(E.Refused, E.rule_of, {"params": [dict(p)] * 15, "cells": ["A$"] * 2}, 3, 3, 1)


class World(unittest.TestCase):
    def test_centred(self):
        cells = np.zeros((3, 4))
        cells[0, 0] = 1.0
        A = E.placed([cells], n=16)[0]
        self.assertEqual(np.argwhere(A > 0).tolist(), [[6, 6]])          # (16 - 3) // 2, (16 - 4) // 2

    def test_kernels_normalised(self):
        p = {"R": 13, "T": 10, "b": "1,1/12,3/4", "m": 0.1, "s": 0.01, "kn": 1, "gn": 1}
        kernels, _ = E.rule_of({"params": [p, dict(p, b="1")], "cells": "A$"}, 1, 2, 1)
        for K in E.kernel_ffts(kernels, n=64):
            self.assertAlmostEqual(float(np.real(K[0, 0])), 1.0, places=12)

    def test_torus_parts(self):
        for name, got, want in E.labelling_cases():
            self.assertEqual(got, want, name)
        S = np.zeros((32, 32))
        S[3:6, 3:6] = 1.0
        S[20:22, 20:22] = 0.5
        self.assertEqual(sorted(E.part_masses(S).tolist()), [2.0, 9.0])
        self.assertEqual(E.big_parts(S, 11.0), 1)
        self.assertEqual(E.big_parts(S + np.roll(S, 16, axis=0), 11.0), 2)


def inputs_dir():
    d = os.environ.get("EXPANDED_INPUTS") or os.path.join(HERE, "..", "inputs")
    for name, sha, _, _ in E.INPUTS:
        path = os.path.join(d, name)
        if not os.path.isfile(path):
            return None
        with open(path, "rb") as f:
            if hashlib.sha256(f.read()).hexdigest() != sha:
                return None
    return d


@unittest.skipUnless(inputs_dir(), "the author's files are not at inputs/ (or EXPANDED_INPUTS)")
class AuthorsFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts = E.load(inputs_dir())
        cls.reps, cls.negatives = E.selection(cls.texts)

    def test_selection(self):
        files = [f for f, _ in self.reps]
        self.assertEqual((len(self.reps), files.count("lenia_found_212.json")), (18, 2))
        r233 = E.read_found(self.texts["lenia_found_233s.json"])
        counts = {}
        for heading, _ in r233:
            counts[heading] = counts.get(heading, 0) + 1
        self.assertEqual((counts["reproduce"], counts["reproduce + emission"]), (10, 6))
        self.assertEqual([p["code"] for _, p in self.negatives], ["OG2g", "MVAWF3<SZLM26"])

    def test_port_is_the_authors_automaton(self):
        for f, p in (self.reps[0], self.reps[2]):
            same, worst = E.compare((self.texts["LeniaNDKC.py"], E.RULES[f], p))
            self.assertTrue(same, (f, p.get("code")))
            self.assertEqual(worst, 0.0)

    def test_two_copies(self):
        for f, p in self.negatives:
            self.assertEqual(E.two_copies(*E.rule_of(p, *E.RULES[f])), (1, 2))


if __name__ == "__main__":
    unittest.main()
