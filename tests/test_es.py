"""The 17-point check on small cases, with no solver: the formula es(n, k) holds for a signature function exactly
when the function is admissible, has its first point's triples positive and has no convex k-subset, over every
signature function on five points and a seeded sample on six and seven; the paper's cup-and-cap convexity against
convex position on point sets; the normalisation; the shuffle; and the threshold for four points, found by search.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import itertools
import os
import random
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("es_check", os.path.join(HERE, "..", "es", "check.py"))
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)

SEED = "0" * 63 + "9"


def admissible(sig, n):
    for a, b, c, d in itertools.combinations(range(n), 4):
        seq = (sig[(a, b, c)], sig[(a, b, d)], sig[(a, c, d)], sig[(b, c, d)])
        if sum(seq[i] != seq[i + 1] for i in range(3)) > 1:
            return False
    return True


def convex_k(sig, n, k):
    return any(E.cup_cap(sig, S) for S in itertools.combinations(range(n), k))


def formula_holds(n, k, sig):
    """Every clause of es(n, k) under sig, with each chain variable set to whether its chain exists."""
    nv, clauses, names = E.encode(n, k)
    val = {}
    for name, v in names.items():
        if name[0] == "o":
            val[v] = sig[name[1:]]
    chains = {name: v for name, v in names.items() if name[0] == "c"}
    for name, v in sorted(chains.items(), key=lambda kv: kv[0][2]):        # by chain length
        _, s, l, a, y, z = name
        if l == 3:
            val[v] = sig[(a, y, z)] == (s == 1)
        else:
            val[v] = any(val.get(names.get(("c", s, l - 1, a, x, y)), False) and sig[(x, y, z)] == (s == 1)
                         for x in range(a + 1, y))
    for name, v in names.items():
        if name[0] == "e":
            _, s, l, a, z = name
            val[v] = any(val[w] for nm, w in chains.items() if nm[1] == s and nm[2] == l and nm[3] == a and nm[5] == z)
    return all(any(val[abs(lit)] == (lit > 0) for lit in c) for c in clauses)


def all_signatures(n):
    triples = list(itertools.combinations(range(n), 3))
    for bits in range(2 ** len(triples)):
        yield {t: bool(bits >> i & 1) for i, t in enumerate(triples)}


class Formula(unittest.TestCase):
    def check(self, n, k, sigs):
        agree = 0
        for sig in sigs:
            want = admissible(sig, n) and all(sig[(0, b, c)] for b, c in itertools.combinations(range(1, n), 2)) \
                and not convex_k(sig, n, k)
            self.assertEqual(formula_holds(n, k, sig), want, (n, k, sig))
            agree += 1
        return agree

    def test_every_signature_function_on_five_points(self):
        for k in (3, 4, 5):
            with self.subTest(k=k):
                self.assertEqual(self.check(5, k, all_signatures(5)), 1024)

    def test_a_seeded_sample_on_six_and_seven_points(self):
        rng = random.Random(3)
        for n, k in ((6, 4), (6, 5), (7, 5), (7, 6)):
            triples = list(itertools.combinations(range(n), 3))
            sigs = []
            for _ in range(150):
                sig = {t: rng.random() < 0.5 for t in triples}
                for b, c in itertools.combinations(range(1, n), 2):
                    sig[(0, b, c)] = True                       # the first point fixed, so admissible ones turn up
                sigs.append(sig)
            with self.subTest(n=n, k=k):
                self.check(n, k, sigs)

    def test_five_points_always_hold_a_convex_four(self):
        """Klein's threshold, found by exhausting es(4, 4) and es(5, 4) over every signature function."""
        self.assertTrue(any(formula_holds(4, 4, s) for s in all_signatures(4)))
        self.assertFalse(any(formula_holds(5, 4, s) for s in all_signatures(5)))

    def test_sizes(self):
        nv, clauses, names = E.encode(17, 6)
        self.assertEqual(sum(1 for c in clauses if len(c) == 1 and c[0] > 0), 120)     # o(0, b, c), b < c among 16
        self.assertEqual(sum(1 for c in clauses if len(c) == 1 and c[0] < 0), 156)     # no 6-cup or 6-cap from a to f
        self.assertEqual(sum(1 for n in names if n[0] == "o"), 680)
        self.assertEqual(sum(1 for c in clauses if len(c) == 3 and all(abs(l) <= 680 for l in c)), 8 * 2380)


class Geometry(unittest.TestCase):
    def test_cup_cap_is_convex_position_on_point_sets(self):
        g = E.geometry(SEED, sets=4, n=9)
        self.assertEqual((g["geo_mismatches"], g["geo_axiom_violations"], g["geo_first_not_fixed"]), (0, 0, 0))
        self.assertEqual(g["geo_subsets"], 4 * 84)

    def test_a_hexagon_and_a_point_inside(self):
        hexagon = [(0, 0), (2, -2), (5, -2), (7, 0), (5, 3), (2, 3)]
        P = E.normalised(hexagon)
        self.assertTrue(E.cup_cap(E.signature(P), tuple(range(6))))
        inside = [(0, 0), (2, -2), (5, -2), (7, 0), (5, 3), (3, 1)]
        P = E.normalised(inside)
        self.assertFalse(E.cup_cap(E.signature(P), tuple(range(6))))

    def test_point_sets_follow_the_seed(self):
        self.assertEqual(E.point_sets(SEED, 2, 6), E.point_sets(SEED, 2, 6))
        self.assertNotEqual(E.point_sets(SEED, 2, 6), E.point_sets("f" * 64, 2, 6))


class Shuffle(unittest.TestCase):
    def test_renaming_is_a_bijection_and_keeps_every_clause(self):
        nv, clauses, _ = E.encode(7, 5)
        out, new = E.renamed(nv, clauses, SEED)
        self.assertEqual(sorted(new.values()), list(range(1, nv + 1)))
        back = {v: k for k, v in new.items()}
        restored = sorted(sorted((1 if l > 0 else -1) * back[abs(l)] for l in c) for c in out)
        self.assertEqual(restored, sorted(sorted(c) for c in clauses))
        self.assertNotEqual(out, E.renamed(nv, clauses, "f" * 64)[0])


if __name__ == "__main__":
    unittest.main()
