"""Bogart & Valero's generalised permanents (bdc/bv2022.py): the polynomials by definition, Proposition 2.1's matrix
on other posets, the cycle-cover expansion, Hessians and ranks, and the printed-Hessian comparison, on inputs outside
the test's ranges (other posets, compositions and partitions of 9 and 10, small polynomials). Nothing here builds the
cube's matrices for n <= 6, the lattices of compositions of gamma <= 8, or the Hessians at the paper's zeros for the
test's n and partitions.

Run with: python3 -m unittest tests.test_bv2022 (in the pinned scipy-notebook image)
"""

import importlib.util
import itertools
import os
import random
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("bdc_bv2022", os.path.join(HERE, "..", "bdc", "bv2022.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


def divisors_poset(N, labels):
    """The divisor lattice of N, by rank (number of prime factors) then value; each cover d -> d*p labelled with the
    variable labels[(d, d*p)]."""
    def omega(k):
        c, p = 0, 2
        while k > 1:
            while k % p == 0:
                k //= p
                c += 1
            p += 1
        return c

    elems = sorted((d for d in range(1, N + 1) if N % d == 0), key=lambda d: (omega(d), d))
    covers = []
    for d in elems:
        for e in elems:
            if e % d == 0 and e != d and omega(e) == omega(d) + 1:
                covers.append((d, e, labels.setdefault((d, e), ("L", len(labels)))))
    return elems, covers, N


def chain_sum(elems, covers, top):
    """The sum over saturated chains from the minimum to the top of the products of labels, as terms."""
    up = {}
    for x, y, lab in covers:
        up.setdefault(x, []).append((y, lab))
    terms = {}

    def rec(x, mono):
        if x == top:
            key = tuple(sorted(mono))
            terms[key] = terms.get(key, 0) + 1
            return
        for y, lab in up.get(x, []):
            rec(y, mono + [lab])

    rec(elems[0], [])
    return terms


class Polynomials(unittest.TestCase):
    def test_signed_permutations_and_words(self):
        self.assertEqual(len(list(M.signed_perms(3))), 48)
        self.assertEqual(sorted(M.words((2, 1))), [(1, 1, 2), (1, 2, 1), (2, 1, 1)])
        self.assertEqual(len(list(M.words((2, 2, 1)))), 30)
        t = M.mperm_terms((1, 2))
        self.assertEqual(t, {((1, 1), (2, 2), (3, 2)): 1, ((1, 2), (2, 1), (3, 2)): 1, ((1, 2), (2, 2), (3, 1)): 1})
        self.assertEqual(sorted(M.det_terms(2).values()), [-1, 1])

    def test_value_and_brute_force(self):
        rng = random.Random(1)
        X = {v: rng.randint(-9, 9) for v in M.hoperm_vars(3)}
        self.assertEqual(M.value(M.hoperm_terms(3), X), M.brute_hoperm(3, X))
        m = (3, 1, 2)
        X = {v: rng.randint(-9, 9) for v in M.mperm_vars(m)}
        self.assertEqual(M.value(M.mperm_terms(m), X), M.brute_mperm(m, X))
        self.assertEqual(M.value(M.mperm_terms(m), X, 101), M.brute_mperm(m, X) % 101)

    def test_compositions_and_partitions(self):
        self.assertEqual(len(M.compositions(5)), 16)
        self.assertEqual(M.partitions(6), [(4, 1, 1), (3, 2, 1), (3, 1, 1, 1), (2, 2, 2), (2, 2, 1, 1),
                                           (2, 1, 1, 1, 1), (1, 1, 1, 1, 1, 1)])
        self.assertEqual(len(M.partitions(9)), 30 - 5)


class Matrices(unittest.TestCase):
    def test_expansion_against_leibniz(self):
        rng = random.Random(2)
        for _ in range(6):
            rows = [dict() for _ in range(5)]
            for u, v in itertools.product(range(5), repeat=2):
                c = rng.randint(0, 9)
                if c < 3:
                    rows[u][v] = (rng.choice((1, -1)), (u + 1, v + 1))
                elif c < 5:
                    rows[u][v] = rng.choice((-1, 1, 3))
            self.assertEqual(M.expand(rows), M.leibniz_terms(rows))

    def test_proposition_21_on_divisor_lattices(self):
        for N in (12, 30, 36, 72):
            elems, covers, top = divisors_poset(N, {})
            rows, d = M.poset_rows(elems, covers, top)
            self.assertEqual(len(rows), len(elems) - 1)
            self.assertEqual(M.expand(rows), chain_sum(elems, covers, top), N)
            if d % 2 == 0:
                rows0, _ = M.poset_rows(elems, covers, top, fix=False)
                self.assertEqual(M.expand(rows0), {k: -c for k, c in chain_sum(elems, covers, top).items()})

    def test_multiset_lattices_of_nine_and_ten(self):
        for m in ((2, 7), (9,), (5, 5), (1, 3, 5)):
            rows, d = M.multiset_rows(m)
            self.assertEqual(len(rows), M.math.prod(x + 1 for x in m) - 1)
            self.assertEqual(d, sum(m))
            self.assertEqual(M.expand(rows), M.mperm_terms(m), m)

    def test_cube_poset_structure_n7(self):
        elems, covers, top = M.cube_poset(7)
        self.assertEqual(len(elems), 3 ** 7 + 1)
        n_cov = sum(1 for x, y, lab in covers if y != top)
        self.assertEqual(n_cov, sum(M.math.comb(7, r) * 2 ** r * 2 * (7 - r) for r in range(7)))
        self.assertEqual(sum(1 for x, y, lab in covers if y == top), 2 ** 7)
        for x, y, lab in covers:
            if y != top:
                r = sum(map(abs, x))
                j = next(k for k in range(7) if x[k] != y[k])
                self.assertEqual(lab, (r + 1, y[j] * (j + 1)))

    def test_modular_determinant_path(self):
        m = (4, 4, 1)                                     # 49 rows, compared by points as well as identically
        rows, _ = M.multiset_rows(m)
        X = M.draw_point("0" * 64, "test", M.mperm_vars(m))
        self.assertEqual(M.G.det_mod(M.numeric(rows, X)), M.value(M.mperm_terms(m), X, M.P))


class Hessians(unittest.TestCase):
    def test_small_hessians(self):
        terms = {(("a", 1), ("a", 2), ("a", 3)): 1}
        H = M.hessian(terms, [("a", 1), ("a", 2), ("a", 3)], {("a", 1): 2, ("a", 2): 3, ("a", 3): 5})
        self.assertEqual(H, [[0, 5, 3], [5, 0, 2], [3, 2, 0]])
        H = M.hessian(M.det_terms(2), [(1, 1), (1, 2), (2, 1), (2, 2)], {(1, 1): 4, (1, 2): 7, (2, 1): 1, (2, 2): 9})
        self.assertEqual(H, [[0, 0, 0, 1], [0, 0, -1, 0], [0, -1, 0, 0], [1, 0, 0, 0]])

    def test_ranks(self):
        rng = random.Random(3)
        st = M.G.Stream("1" * 64, "test-ranks")
        for N, r in ((6, 2), (12, 11), (15, 15)):
            A = M.planted_rank_matrix(st, N, r)
            self.assertEqual(M.rank_exact(A), M.rank_mod(A, M.P))
        self.assertEqual(M.rank_exact([[1, 2], [2, 4]]), 1)
        self.assertEqual(M.rank_exact([[0, 0], [0, 0]]), 0)
        self.assertEqual(M.rank_exact([[Fraction(1, 3), 1], [1, 3]]), 1)

    def test_zeros_of_nine(self):
        for m in ((7, 1, 1), (3, 3, 3), (4, 3, 2)):
            X, D, ell, c = M.mperm_B(m)
            self.assertEqual(ell, 2 if len(set(m)) == 1 else 1)
            self.assertEqual(M.value(M.mperm_terms(m), X), 0, m)
            if ell == 1:
                X2 = M.mperm_B(m, raise_by=1)[0]
                self.assertNotEqual(M.value(M.mperm_terms(m), X2), 0)
        with self.assertRaises(M.Refused):
            M.mperm_B((1, 2, 3))

    def test_hessian_against_second_differences_of_nine(self):
        m = (7, 1, 1)
        X, D, ell, c = M.mperm_B(m)
        terms, variables = M.mperm_terms(m), M.mperm_vars(m)
        H = M.hessian(terms, variables, X)
        self.assertEqual(H, M.second_differences(terms, variables, X))
        self.assertEqual(M.rank_exact(H), M.rank_mod(H, M.P))


class Printed(unittest.TestCase):
    def test_printed_structure_and_comparator(self):
        for m in ((7, 1, 1), (3, 3, 3), (4, 3, 2)):
            Hp, Q, R, special = M.printed_mperm(m)
            n, gamma = len(m), sum(m)
            self.assertEqual(len(Hp), gamma * n)
            self.assertTrue(all(Hp[a][b] == Hp[b][a] for a in range(len(Hp)) for b in range(len(Hp))))
            self.assertEqual(M.compare_printed_mperm(m, Hp), ("match", []))
            # R blocks scaled by 1/7: reported as R with its factor
            H2 = [row[:] for row in Hp]
            for i in range(1, gamma + 1):
                for ii in range(1, gamma + 1):
                    if i != ii and special not in (i, ii):
                        for j in range(n):
                            for jj in range(n):
                                H2[(i - 1) * n + j][(ii - 1) * n + jj] /= 7
            status, blocks = M.compare_printed_mperm(m, H2)
            self.assertEqual(status, "differs")
            self.assertEqual(blocks, [("R", Fraction(1, 7))])

    def test_printed_hoperm_structure(self):
        H = M.printed_hoperm(7)
        self.assertEqual(len(H), 98)
        self.assertTrue(all(H[a][b] == H[b][a] for a in range(98) for b in range(98)))
        self.assertTrue(all(H[a][a] == 0 for a in range(98)))

    def test_poly_mul(self):
        a = {(("x", 1),): 1, (("x", 2),): 1}
        self.assertEqual(M.poly_mul(a, a), {(("x", 1), ("x", 1)): 1, (("x", 1), ("x", 2)): 2, (("x", 2), ("x", 2)): 1})


class Run(unittest.TestCase):
    def test_bad_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


if __name__ == "__main__":
    unittest.main()
