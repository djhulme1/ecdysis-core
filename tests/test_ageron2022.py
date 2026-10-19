"""Ageron et al.'s templates (schur/ageron2022.py) on inputs written here, never the paper's: the weak and sum-free tests
against a direct search on random colourings and on planted sums; Definition 3.13 and Theorem 3.17 on every small
WS-template a direct search finds (each must give weakly sum-free partitions from sum-free bases); the ordering of the
base; Definition 2.8 on Abbott and Hanson's template; the readers of Tables 8 and 9 on lines written here, and of
Rowley's sheet on rows written here, with their refusals. The paper's tables, its bounds and the cited partitions are
not read or built here.

Run with: python3 -m unittest discover -s tests -p test_ageron2022.py (in the pinned scipy-notebook image)
"""

import importlib.util
import itertools
import os
import random
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("schur_ageron2022", os.path.join(HERE, "..", "schur", "ageron2022.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


def direct(h, weak):
    """Every sum in each colour, by a direct search: {colour: set of (a, b)}."""
    n = len(h) - 1
    out = {}
    for a in range(1, n + 1):
        for b in range(a + (1 if weak else 0), n - a + 1):
            if h[a] and h[a] == h[b] == h[a + b]:
                out.setdefault(int(h[a]), set()).add((a, b))
    return out


def colouring(sets, n):
    h = np.zeros(n + 1, dtype=np.int32)
    for i, s in enumerate(sets, 1):
        for x in s:
            h[x] = i
    return h


S2 = [[1, 4], [2, 3]]
S3 = [[1, 4, 7, 10, 13], [2, 3, 11, 12], [5, 6, 8, 9]]


class Tests(unittest.TestCase):
    def test_weak_and_sum_free_against_direct_search(self):
        rng = random.Random(7)
        tally = M.Tally()
        for _ in range(300):
            n, k = rng.randint(1, 300), rng.randint(1, 4)
            h = np.zeros(n + 1, dtype=np.int32)
            h[1:] = [rng.randint(1, k) for _ in range(n)]
            for weak in (True, False):
                found = direct(h, weak)
                v = tally.verdict(h, k, weak=weak)
                self.assertEqual(set(v["sums"]), set(found))
                for c, s in v["sums"].items():
                    self.assertIn(s, found[c])
                    self.assertTrue(M.genuine(h, s, c, weak))
        self.assertEqual(tally.disagreements, [])

    def test_weak_allows_a_equals_b(self):
        h = np.array([0, 1, 1, 2, 1], dtype=np.int32)          # {1, 2, 4}: 1 + 1 = 2 and 2 + 2 = 4, no a < b sum
        tally = M.Tally()
        self.assertTrue(tally.verdict(h, 2, weak=True)["free"])
        self.assertFalse(tally.verdict(h, 2)["free"])
        h = np.array([0, 1, 1, 1], dtype=np.int32)             # 1 + 2 = 3
        self.assertEqual(tally.verdict(h, 1, weak=True)["sums"], {1: (1, 2)})

    def test_planted_weak_sums_on_long_colourings(self):
        rng = random.Random(11)
        tally = M.Tally()
        for n in (64, 65, 127, 128, 129, 1000, 4097):
            h = np.zeros(n + 1, dtype=np.int32)
            h[1:] = [1 + (rng.random() < 0.5) for _ in range(n)]
            st = M.FS.Stream("0" * 64, f"test/{n}")
            hp, c, ab = M.plant(h, st, [1, 2], True)
            one, two = tally.first(hp, c, True)
            self.assertIsNotNone(one)
            self.assertEqual(one, two)
            self.assertTrue(M.genuine(hp, one, c, True))
        self.assertEqual(tally.disagreements, [])

    def test_small_weak_schur_numbers(self):
        tally = M.Tally()
        for n, expect in ((2, True), (3, False)):              # WS(1) = 2
            h = np.ones(n + 1, dtype=np.int32)
            h[0] = 0
            self.assertEqual(tally.verdict(h, 1, weak=True)["free"], expect)
        counts = {}
        for n in (8, 9):                                        # WS(2) = 8
            counts[n] = sum(tally.verdict(np.array([0] + [1 + ((code >> i) & 1) for i in range(n)], dtype=np.int32), 2,
                                          weak=True)["free"] for code in range(2 ** n))
        self.assertGreater(counts[8], 0)
        self.assertEqual(counts[9], 0)

    def test_ordered(self):
        g = np.array([0, 3, 1, 1, 3, 2], dtype=np.int32)
        self.assertEqual(M.ordered(g).tolist(), [0, 1, 2, 2, 1, 3])

    def test_theorem_317_on_every_small_template(self):
        bases = [(1, np.array([0, 1], dtype=np.int32)), (2, colouring(S2, 4)), (3, colouring(S3, 13)),
                 (2, colouring([[2, 3], [1, 4]], 4))]
        tally = M.Tally()
        found = 0
        for colours, top in ((2, 12), (3, 9)):
            for a in range(2, top):
                for b in range(1, a):
                    if a + b > top:
                        continue
                    for code in itertools.product(range(1, colours + 1), repeat=a + b):
                        if code[a - 1] != colours:                 # a in the special colour, the last
                            continue
                        sets = [[x for x in range(1, a + b + 1) if code[x - 1] == c] for c in range(1, colours + 1)]
                        if M.definition_313(sets, a, b) is not None:
                            continue
                        found += 1
                        for k, g in bases:
                            h = M.ws_template(g, k, sets, a, b)
                            p = len(g) - 1
                            self.assertEqual(len(h) - 1, p * a + b)
                            self.assertTrue(np.all((h[1:] >= 1) & (h[1:] <= colours - 1 + k)))
                            self.assertEqual(direct(h, True), {}, (sets, a, b, k))
                            self.assertTrue(tally.verdict(h, colours - 1 + k, weak=True)["free"])
        self.assertGreater(found, 10)

    def test_definition_313_breaches(self):
        self.assertIsNone(M.definition_313([[1, 2], [3, 4]], 3, 1))                      # a 1-WS-template, width 3
        self.assertIn("not weakly sum-free", M.definition_313([[1, 2, 3], [4, 5, 6, 7]], 5, 2))   # 1 + 2 = 3
        self.assertIn("above", M.definition_313([[1], [2, 3, 4, 5, 6]], 5, 1))           # 2 + 2 = 4, both above b
        self.assertIn("special colour", M.definition_313([[1, 2], [3, 4, 5]], 3, 2))     # 4 + 5 - 6 = 3
        self.assertIn("pi(1 + 5) = 2", M.definition_313([[1, 2, 5], [3, 4]], 4, 1))     # pi(6) = 2
        self.assertIn("has no colour", M.definition_313([[1, 2], [4, 5]], 3, 2))

    def test_abbott_hanson_symmetry(self):
        # Abbott and Hanson's S-template from a sum-free partition of 1..s: the partition, then s + 1..2s + 1 special
        def ah(part, s):
            return [sorted(x) for x in part] + [list(range(s + 1, 2 * s + 2))]
        self.assertTrue(M.symmetric_template(ah(S2, 4), 9))
        self.assertTrue(M.symmetric_template(ah(S3, 13), 27))
        self.assertFalse(M.symmetric_template(ah([[1], [2, 3]], 3), 7))
        self.assertIsNone(M.SH.definition_21(ah(S2, 4), 9))

    def test_read_table_8(self):
        lines = ["B WS-templates", "Table 8: 23-WS-template with width 42 and 4 colors", "1", "1", ";", "2", ";", "(",
                 "N", "+", "1", ")", "2", "3", ";", "4", "3", "5", "4", "6", "This template provides the inequality"]
        t = M.read_ws_template(lines)
        self.assertEqual(t["sets"], [[1, 2], [3, 4], [5], [6]])
        self.assertEqual(t["last"], 1)
        self.assertEqual((t["a"], t["b"], t["m"]), (42, 23, 4))
        self.assertEqual(t["missing"][:2], [7, 8])
        bad = list(lines)
        bad[1] = "Table 8: 23-WS-template with width 41 and 4 colors"
        with self.assertRaises(M.Refused):
            M.read_ws_template(bad)
        twice = lines[:12] + [";", "(", "N", "+", "1", ")"] + lines[12:]
        with self.assertRaises(M.Refused):
            M.read_ws_template(twice)
        none = lines[:6] + lines[12:]
        with self.assertRaises(M.Refused):
            M.read_ws_template(none)

    def test_read_table_9(self):
        lines = ["19", "C", "WS", "(6)", ">", "646", "Table 9: Weakly sum-free partition of [[1", ";",
                 "646]] into 6 subsets"]
        body = []
        for c in range(1, 7):
            body += [str(c), str(c), ";", str(c + 6)]
        t = M.read_ws_partition(lines + body + ["20"])
        self.assertEqual(t["sets"], [[c, c + 6] for c in range(1, 7)])
        self.assertEqual(t["after"], ["20"])
        self.assertEqual(len(t["missing"]), 646 - 12)
        with self.assertRaises(M.Refused):
            M.read_ws_partition(lines[:-1] + ["640]] into 6 subsets"] + body)
        with self.assertRaises(M.Refused):
            M.read_ws_partition(lines + body[:-4])

    def test_rowley_cells(self):
        rng = random.Random(3)
        subsets = [rng.randint(1, 7) for _ in range(1696)]
        rows = [[""] * 9 for _ in range(5)]
        rows[1][2] = M.ROWLEY_TITLE
        pairs = sorted((s, x) for x, s in enumerate(subsets, 1))
        for i in range(1696):
            rows.append(["", "", "", float(i + 1), float(subsets[i]), "", "", float(pairs[i][0]), float(pairs[i][1])])
        sets = M.rowley_cells(rows)
        self.assertEqual(sum(len(s) for s in sets), 1696)
        self.assertEqual(sets[subsets[0] - 1][0], 1)
        broken = [list(r) for r in rows]
        broken[1][2] = "Partition of [1, 1696] into 6 sum-free subsets"
        with self.assertRaises(M.Refused):
            M.rowley_cells(broken)
        broken = [list(r) for r in rows]
        broken[100][4] = 8.0
        with self.assertRaises(M.Refused):
            M.rowley_cells(broken)
        broken = [list(r) for r in rows]
        broken[100][4], broken[101][4] = broken[101][4], broken[100][4]
        if broken[100][4] != broken[101][4]:
            with self.assertRaises(M.Refused):
                M.rowley_cells(broken)
        broken = [list(r) for r in rows]
        broken[200][3] = 2.5
        with self.assertRaises(M.Refused):
            M.rowley_cells(broken)

    def test_split_pairs(self):
        self.assertEqual(M.split_pairs(S3, 13), [])
        self.assertEqual(M.split_pairs([[1], [2, 3]], 3), [(1, 3)])
        self.assertEqual(M.symmetry_text([]), "symmetric")
        self.assertEqual(M.symmetry_text([(179, 358)]), "symmetric but for 179 and 358")
        self.assertEqual(M.symmetry_text([(1, 9), (2, 8), (3, 7)]), "3 pairs split")

    def test_last_number_rule(self):
        # Theorem 3.17 from a two-colour WS-template and the base 1..4; the last number goes where it is told
        sets = [[1, 2], [3, 4]]
        self.assertIsNone(M.definition_313(sets, 3, 1))
        h = M.ws_template(colouring(S2, 4), 2, sets, 3, 1, last=1)
        self.assertEqual(len(h) - 1, 4 * 3 + 1 + 1)
        self.assertEqual(h[-1], 1)

    def test_bad_seed(self):
        with self.assertRaises(M.Refused):
            M.run("nope")


if __name__ == "__main__":
    unittest.main()
