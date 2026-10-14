"""Exoo's partition (schur/exoo.py): the page-header rule and the partition reader on lines written here (the listing
of 1..80, sets in order, refusals); the listing rule i -> 161 - i; the derived arithmetic; the verdict at and beside
each condition; the perturbation; the seed refused. The paper's PDF is not read here, and no sum or triangle of its
partition is computed.

Run with: python3 -m unittest discover -s tests -p test_exoo.py
"""

import importlib.util
import os
import tempfile
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("schur_exoo", os.path.join(HERE, "..", "schur", "exoo.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


def listing(sets):
    return ["only the integers", "from 1 to 80 are listed.", "1"] + [
        f"Set {i + 1}: " + " ".join(map(str, s)) for i, s in enumerate(sets)] + ["This proves that"]


ROUND = [list(range(1 + j, 81, 5)) for j in range(5)]          # 1..80 dealt round five sets: a listing, not a partition


def pdf(streams):
    out = [b"%PDF-1.2\n"]
    for i, s in enumerate(streams, 2):
        z = zlib.compress(s.encode("latin-1"))
        out.append(f"{i} 0 obj\n<<\n/Length {len(z)}\n/Filter /FlateDecode\n>>\nstream\r\n".encode() + z
                   + b"\r\nendstream\nendobj\n")
    return b"".join(out)


class Reading(unittest.TestCase):
    def test_partition_read(self):
        got = M.read_partition(listing(ROUND))
        self.assertEqual(got, ROUND)

    def test_refusals(self):
        with self.assertRaises(M.Refused):
            M.read_partition(listing(ROUND)[:-3])                      # too few sets
        bad = [list(s) for s in ROUND]
        bad[0].append(2)                                                # 2 listed twice
        with self.assertRaises(M.Refused):
            M.read_partition(listing(bad))
        swapped = listing(ROUND)
        swapped[3], swapped[4] = swapped[4], swapped[3]                 # sets out of order
        with self.assertRaises(M.Refused):
            M.read_partition(swapped)
        with self.assertRaises(M.Refused):
            M.read_partition(["Set 1: 1 2"])                            # no listing sentence

    def test_headers_dropped(self):
        body = ("BT /F1 1 Tf 0 Tc (the electronic journal of combinatorics 1 \\(1994\\), #R8)Tj 0 -1 TD (2)Tj "
                "0 -1 TD (Set 1: 4 5)Tj ET")
        lines = M.document_lines(pdf([body]))
        self.assertNotIn("the electronic journal of combinatorics 1 (1994), #R8", lines)
        self.assertNotIn("2", lines)
        self.assertIn("Set 1: 4 5", lines)

    def test_statements(self):
        found = M.statements_found(["x " + M.STATEMENTS[0] + " y", M.STATEMENTS[2]])
        self.assertEqual(sum(found.values()), 2)

    def test_hash_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, M.INPUT[0]), "wb") as fh:
                fh.write(b"%PDF-1.2\n")
            with self.assertRaises(M.Refused):
                M.read_input(d)


class Rules(unittest.TestCase):
    def test_expand(self):
        sets = M.expand([[1, 80], [2]])
        self.assertEqual(sets, [[1, 80, 81, 160], [2, 159]])
        full = M.expand(ROUND)
        self.assertTrue(M.FS.is_partition(full, 160))

    def test_derived(self):
        d = M.derived()
        self.assertEqual(d["r6"], 500)
        self.assertEqual(d["base"], 321)
        self.assertAlmostEqual(d["root"] ** 5, 321)

    def test_perturb(self):
        st = M.FS.Stream("ab" * 32, "t")
        for _ in range(10):
            sets, x, src, dst = M.perturb(ROUND, st)
            self.assertNotEqual(src, dst)
            self.assertTrue(M.FS.is_partition(sets, 160))
            self.assertIn(x, sets[dst])
            self.assertIn(161 - x, sets[dst])


class Verdict(unittest.TestCase):
    def found(self, **kw):
        f = {"partition": True, "sums": 0, "triangles": 0,
             "derived": {"r6_ok": True, "root_ok": True}}
        for k, v in kw.items():
            if k in ("r6_ok", "root_ok"):
                f["derived"][k] = v
            else:
                f[k] = v
        return f

    def test_conditions(self):
        c = M.conditions(self.found())
        self.assertEqual(len(c), 3)
        self.assertTrue(all(c.values()))
        for kw in ({"partition": False}, {"sums": 1}, {"triangles": 3}, {"r6_ok": False}, {"root_ok": False}):
            self.assertEqual(sum(M.conditions(self.found(**kw)).values()), 2, kw)

    def test_outputs_named(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


if __name__ == "__main__":
    unittest.main()
