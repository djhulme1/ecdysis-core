"""The binary determinantal complexity check on small cases: the level-wise enumeration against a brute force over
every 0/1 matrix up to size 4; the classes of size 3; the polynomial of a support against the matrix's own Leibniz
expansion; the variable sets and pair tables against brute force on the paper's per2 matrix; the search finding that
matrix; Grenet's matrix and its recognition under row and column permutations, transposition and the 72 symmetries of
per3; the paper's output read (its lines end in CR LF) and anything else refused; and one dense 6 x 6 class searched.

With the paper's output at inputs/ (or BDC_INPUTS), also its 463 matrices: each with determinant per3, exactly one
sparse, and that one Grenet's.

Run with: python3 -m unittest discover -s tests
"""

import hashlib
import importlib.util
import itertools
import os
import random
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("bdc_check", os.path.join(HERE, "..", "bdc", "check.py"))
C = importlib.util.module_from_spec(_spec)
sys.modules["bdc_check"] = C
_spec.loader.exec_module(C)


def leibniz(M):
    """det of an integer matrix straight from the definition, over every permutation."""
    n = len(M)
    total = 0
    for p in itertools.permutations(range(n)):
        term = C.perm_sign(p)
        for i in range(n):
            term *= M[i][p[i]]
        total += term
    return total


def matrix(rows, n):
    return [[C.bit(r, n, j) for j in range(n)] for r in rows]


class Enumeration(unittest.TestCase):
    def test_largest_determinants_against_brute_force(self):
        for n in range(1, 5):
            best = 0
            for code in range(1 << (n * n)):
                M = [[(code >> (i * n + j)) & 1 for j in range(n)] for i in range(n)]
                best = max(best, abs(leibniz(M)))
            self.assertEqual(C.enumerate_supports(n, None, 1)[1], best, n)

    def test_kept_sets_and_their_determinants(self):
        for n, target, ones in ((3, 2, 2), (4, 3, 2), (4, 2, 1)):
            kept, _ = C.enumerate_supports(n, target, ones)
            want = set()
            rows = [r for r in range(1, 1 << n) if bin(r).count("1") >= ones]
            for rs in itertools.combinations(rows, n):
                M = matrix(rs, n)
                if abs(leibniz(M)) == target and min(sum(col) for col in zip(*M)) >= ones:
                    want.add(rs)
            self.assertEqual({rs for rs, _ in kept}, want, (n, target, ones))
            for rs, d in kept:
                self.assertEqual(leibniz(matrix(rs, n)), d)

    def test_classes(self):
        reps, with_t = C.classes_of(C.enumerate_supports(3, 2, 2)[0], 3)
        self.assertEqual(len(reps), 1)                              # the 3-cycle complement, up to permutations
        self.assertEqual(with_t, 1)
        self.assertEqual(sorted(sum(r) for r in matrix(reps[0], 3)), [2, 2, 2])
        # classes under row and column permutations, checked by brute force on size 4
        kept, _ = C.enumerate_supports(4, 3, 2)
        reps4, _ = C.classes_of(kept, 4)
        seen = set()
        for rs, _ in kept:
            M = matrix(rs, 4)
            seen.add(min(tuple(sorted(tuple(r[j] for j in p) for r in M)) for p in itertools.permutations(range(4))))
        self.assertEqual(len(reps4), len(seen))
        for rs in reps4:
            self.assertEqual(abs(leibniz(matrix(rs, 4))), 3)

    def test_transpose(self):
        rs = (0b110, 0b011, 0b101)
        self.assertEqual(matrix(C.transpose_rows(rs, 3), 3), [list(c) for c in zip(*matrix(rs, 3))])


class Search(unittest.TestCase):
    def setUp(self):
        self.example = C.as_matrix(C.PER2_EXAMPLE, C.VARS2)
        self.sup = C.Support(C.support_of(C.PER2_EXAMPLE))

    def test_example_is_per2(self):
        self.assertEqual(C.det_poly(self.example, 4), C.per_poly(2))
        self.assertEqual(self.sup.det, 2)

    def test_poly_against_leibniz(self):
        rng = random.Random(1)
        for _ in range(30):
            n = rng.choice((3, 4))
            B = [[1 if rng.random() < 0.6 else 0 for _ in range(n)] for _ in range(n)]
            sup = C.Support(B)
            if not sup.pos:
                continue
            sets = [0, 0]
            for k in range(len(sup.pos)):
                sets[rng.randrange(2)] |= (1 << k) if rng.random() < 0.5 else 0
            A = [[1 if b else 0 for b in r] for r in B]
            for v, s in enumerate(sets):
                for k, (i, j) in enumerate(sup.pos):
                    if s >> k & 1:
                        A[i][j] = ("v", v)
            want = C.det_poly(A, 2)
            got = dict(((k % sup.base, k // sup.base), c) for k, c in sup.poly(sets))
            self.assertEqual(got, want)
            self.assertEqual(sup.det, leibniz(B))

    def brute_sets(self, sup, target):
        out = []
        for s in range(1, 1 << len(sup.pos)):
            got = dict(((k,), c) for k, c in sup.poly([s]))
            if got == target:
                out.append(s)
        return out

    def test_variable_sets_against_brute_force(self):
        target = C.single_target(2)
        self.assertEqual(target, {(1,): 1, (0,): 1})
        self.assertEqual(C.variable_sets(self.sup, target), self.brute_sets(self.sup, target))
        gsup = C.Support(C.support_of(C.GRENET))
        t3 = C.single_target(3)
        self.assertEqual(C.variable_sets(gsup, t3), self.brute_sets(gsup, t3))

    def test_pair_tables_against_brute_force(self):
        sets = C.variable_sets(self.sup, C.single_target(2))
        mono = C.per_monomials(2)
        targets = [C.restriction(mono, (0, 1)), C.restriction(mono, (0, 3))]
        self.assertEqual(targets, [{(1, 0): 1, (0, 1): 1}, {(1, 1): 1, (0, 0): 1}])
        tables = C.pair_tables(self.sup, sets, targets)
        for ti, t in enumerate(targets):
            for i, I in enumerate(sets):
                for j, J in enumerate(sets):
                    want = (I & J) == 0 and dict(((k % 4, k // 4), c) for k, c in self.sup.poly([I, J])) == t
                    self.assertEqual(bool(tables[ti][i, j]), want)

    def test_search_finds_the_example(self):
        sets, nodes, found = C.search(self.sup, 2, C.per_monomials(2))
        mats = [C.placed_matrix(self.sup, sets, f) for f in found]
        self.assertIn(self.example, mats)
        for A in mats:
            self.assertEqual(C.det_poly(A, 4), C.per_poly(2))
        self.assertGreater(nodes, 0)

    def test_a_dense_class_has_no_placement(self):
        dense = (7, 27, 43, 55, 61, 62)                             # one of the two classes with 26 ones
        sup = C.Support(C.representative(dense, 6))
        self.assertEqual((len(sup.pos), sup.det, len(sup.perms)), (26, 6, 106))
        self.assertGreaterEqual(min(sum(col) for col in zip(*sup.B)), 2)
        sets, nodes, found = C.search(sup, 3, C.per_monomials(3))
        self.assertEqual((len(sets), found), (922, []))
        self.assertGreater(nodes, 0)


class Grenet(unittest.TestCase):
    def test_grenet_is_per3(self):
        self.assertEqual(C.det_poly(C.as_matrix(C.GRENET), 9), C.per_poly(3))

    def test_symmetries(self):
        maps = C.per3_maps()
        self.assertEqual(len(maps), 72)
        target = C.per_poly(3)
        for mp in maps:
            A = [[a if a in (0, 1) else mp[a] for a in r] for r in C.GRENET]
            self.assertEqual(C.det_poly(C.as_matrix(A), 9), target)

    def test_recognised_after_permuting_relabelling_and_transposing(self):
        rng = random.Random(7)
        forms, maps = C.grenet_forms(), C.per3_maps()
        for _ in range(3):
            mp = rng.choice(maps)
            A = [[a if a in (0, 1) else mp[a] for a in r] for r in C.GRENET]
            p, q = list(range(7)), list(range(7))
            rng.shuffle(p)
            rng.shuffle(q)
            A = [[A[p[i]][q[j]] for j in range(7)] for i in range(7)]
            if rng.random() < 0.5:
                A = [list(c) for c in zip(*A)]
            self.assertTrue(C.is_grenet(A, forms, maps))
        B = [list(r) for r in C.GRENET]
        B[1][0] = 0                                                 # no longer Grenet's (nor per3)
        self.assertFalse(C.is_grenet(B, forms, maps))
        self.assertTrue(C.sparse(C.GRENET))


def listing_text(mats):
    return "".join("{" + ",\r\n ".join("{ " + ", ".join(f"{a:>3}" for a in r) + " }" for r in M) + "}\r\n"
                   for M in mats)


class Listing(unittest.TestCase):
    def test_read(self):
        text = listing_text([C.GRENET, C.GRENET])
        self.assertEqual(C.parse_listing(text), [C.GRENET, C.GRENET])

    def test_refusals(self):
        bad = [list(r) for r in C.GRENET]
        bad[0][0] = "y11"
        self.assertRaises(C.Refused, C.parse_listing, listing_text([bad]))
        self.assertRaises(C.Refused, C.parse_listing, listing_text([C.GRENET[:6]]))
        self.assertRaises(C.Refused, C.parse_listing, "* a note\r\n" + listing_text([C.GRENET]))
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, C.INPUT[0]), "wb") as f:
                f.write(listing_text([C.GRENET]).encode("ascii"))
            self.assertRaises(C.Refused, C.load, d)


def inputs_dir():
    d = os.environ.get("BDC_INPUTS") or os.path.join(HERE, "..", "inputs")
    path = os.path.join(d, C.INPUT[0])
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        return d if hashlib.sha256(f.read()).hexdigest() == C.INPUT[1] else None


@unittest.skipUnless(inputs_dir(), "the paper's output is not at inputs/ (or BDC_INPUTS)")
class PapersOutput(unittest.TestCase):
    def test_listing(self):
        listing = C.parse_listing(C.load(inputs_dir()))
        self.assertEqual(len(listing), C.PRINTED_LISTED)
        target = C.per_poly(3)
        self.assertTrue(all(C.det_poly(C.as_matrix(A), 9) == target for A in listing))
        sparse = [A for A in listing if C.sparse(A)]
        self.assertEqual(len(sparse), 1)
        self.assertTrue(C.is_grenet(sparse[0], C.grenet_forms(), C.per3_maps()))


if __name__ == "__main__":
    unittest.main()
