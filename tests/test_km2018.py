"""Krishna and Makam 2018 (prank/km2018.py): the polynomial arithmetic, the readers of identities and arrays on
synthetic TeX with their refusals, the flattening and unit pivots on small matrices, the finite fields' axioms, and the
exhaustive rank search against brute force over F_2 and on tensors of known decompositions. Neither the paper's
expressions nor its matrices are read or computed here.

Run with: python3 -m unittest tests.test_km2018 (in the pinned python image)
"""

import importlib.util
import itertools
import os
import random
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("prank_km2018", os.path.join(HERE, "..", "prank", "km2018.py"))
K = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(K)


def simple(u, v, w):
    return {(i, j, k): u[i] * v[j] * w[k] for i in range(3) for j in range(3) for k in range(3)
            if u[i] * v[j] * w[k]}


def add_mod(T, U, p):
    out = dict(T)
    for k, v in U.items():
        out[k] = (out.get(k, 0) + v) % p
    return {k: v % p for k, v in out.items() if v % p}


def pack2(T):
    return sum(1 << (9 * i + 3 * j + k) for (i, j, k), v in T.items() if v % 2)


class Polynomials(unittest.TestCase):
    def test_arithmetic(self):
        lam, a = K.P(1, lam=1), K.P(1, a=1)
        p = K.padd(K.P(1), lam, -1)                       # 1 - lam
        q = K.pmul(p, K.padd(K.P(1), lam))                # 1 - lam^2
        self.assertEqual(q, {(0, 0, 0): 1, (2, 0, 0): -1})
        self.assertEqual(K.const(q), None)
        self.assertEqual(K.const(K.P(-1)), -1)
        self.assertEqual(K.const({}), 0)
        self.assertEqual(K.padd(p, p, -1), {})
        F = K.GF(5)
        self.assertEqual(K.peval(K.pmul(a, a), {"lam": 0, "a": 3, "b": 0}, F), 4)

    def test_entries(self):
        self.assertEqual(K.parse_entry("1 - \\lambda"), {(0, 0, 0): 1, (1, 0, 0): -1})
        self.assertEqual(K.parse_entry(" -1 + \\lambda "), {(0, 0, 0): -1, (1, 0, 0): 1})
        self.assertEqual(K.parse_entry("-a"), {(0, 1, 0): -1})
        self.assertEqual(K.parse_entry("b"), {(0, 0, 1): 1})
        self.assertEqual(K.parse_entry("0"), {})
        self.assertEqual(K.parse_entry("2a"), {(0, 1, 0): 2})
        self.assertEqual(K.parse_entry("3 \\lambda"), {(1, 0, 0): 3})     # an integer before a symbol multiplies it
        for bad in ("x", "\\lambda \\lambda", "1 2", "", "- ", "\\mu"):
            with self.assertRaises(K.Refused, msg=bad):
                K.parse_entry(bad)


class Reading(unittest.TestCase):
    DEFINING = ("\\begin{align*}\n\\det_3 &= e_1 \\otimes e_2 \\otimes e_3 \\\\ & \\quad - e_1 \\otimes e_3 \\otimes e_2 \\\\"
                " & \\quad - e_2 \\otimes e_1 \\otimes e_3 + e_2 \\otimes e_3 \\otimes e_1 \\\\ & \\quad + e_3 \\otimes "
                "e_1 \\otimes e_2 - e_3 \\otimes e_2 \\otimes e_1.\n\\end{align*}")

    def test_defining_expression(self):
        (name, coeff, terms), = K.identity_blocks(self.DEFINING)
        self.assertEqual((name, coeff, len(terms)), ("det", 1, 6))
        self.assertTrue(K.same(K.tensor_of_terms(terms), K.det_tensor()))

    def test_coefficients_and_scaled_factors(self):
        tex = ("\\begin{align*}\\per_3 = \\frac{1}{2}\\Big(& 2e_1 \\otimes (e_2 + e_3) \\otimes (e_1 - 2e_3) \\\\"
               " & {} - (e_1+e_2) \\otimes e_3 \\otimes e_2 \\Big).\\end{align*}")
        (name, coeff, terms), = K.identity_blocks(tex)
        self.assertEqual((name, coeff), ("per", Fraction(1, 2)))
        self.assertEqual(terms, [(1, ((2, 0, 0), (0, 1, 1), (1, 0, -2))), (-1, ((1, 1, 0), (0, 0, 1), (0, 1, 0)))])

    def test_refusals(self):
        bad = [
            "\\begin{align*}\\det_3 = e_1 \\otimes e_2\\end{align*}",                         # two factors
            "\\begin{align*}\\det_3 = e_4 \\otimes e_2 \\otimes e_1\\end{align*}",            # e_4
            "\\begin{align*}\\det_3 = x_1 \\otimes e_2 \\otimes e_1\\end{align*}",            # unknown token
            "\\begin{align*}\\det_3 = (e_1 e_2) \\otimes e_2 \\otimes e_1\\end{align*}",      # no operator
            "\\begin{align*}\\det_3 = \\frac{1}{2} e_1 \\otimes e_2 \\otimes e_1\\end{align*}",  # no parentheses
        ]
        for tex in bad:
            with self.assertRaises(K.Refused, msg=tex):
                K.identity_blocks(tex)

    def array_tex(self, rows, red=None):
        lines = []
        for i, row in enumerate(rows):
            cells = []
            for j, c in enumerate(row):
                cells.append("{\\color{red} " + c + "}" if red and (i, j) in red else c)
            lines.append(" & ".join(cells) + " \\\\")
            if i in (2, 5):
                lines.append("\\hline")
        return "\\begin{array}{ccc|ccc|ccc}\n" + "\n".join(lines) + "\n\\end{array}"

    def test_arrays_and_labels(self):
        rows = [["0"] * 9 for _ in range(9)]
        rows[0][8] = "-1"
        rows[1][5] = "1 - \\lambda"
        body = self.array_tex(rows, red={(0, 8)})
        tex = ("intro " + body + " \\textbf{Case 1} x " + body + " \\textbf{Case 2} y " + body +
               " \\textbf{Case 3} z " + body)
        found = K.arrays(tex)
        self.assertEqual(len(found), 4)
        pos, mat, red = found[1]
        self.assertEqual(mat[0][8], {(0, 0, 0): -1})
        self.assertEqual(mat[1][5], {(0, 0, 0): 1, (1, 0, 0): -1})
        self.assertTrue(red[0][8] and not red[1][5])
        labelled = K.label_arrays(tex, found)
        self.assertEqual(sorted(labelled), [0, 1, 2, 3])
        with self.assertRaises(K.Refused):
            K.label_arrays(tex.replace("\\textbf{Case 2}", ""), found)
        short = self.array_tex(rows[:8])
        with self.assertRaises(K.Refused):
            K.arrays(short)


class Flattening(unittest.TestCase):
    def test_blocks(self):
        T = {(0, 0, 1): K.P(1)}          # e1 (x) E_12
        M = K.flatten(T)
        self.assertEqual(M[0][3 + 1], {(0, 0, 0): 1})      # A in block (0, 1)
        self.assertEqual(M[3][1], {(0, 0, 0): -1})         # -A in block (1, 0)
        T = {(2, 1, 0): K.P(1)}          # e3 (x) E_21: C in block (1, 2), -C in block (2, 1)
        M = K.flatten(T)
        self.assertEqual(M[3 + 1][6 + 0], {(0, 0, 0): 1})
        self.assertEqual(M[6 + 1][3 + 0], {(0, 0, 0): -1})

    def test_simple_tensors_have_rank_at_most_two(self):
        rng = random.Random(1801)
        for _ in range(40):
            u, v, w = ([rng.randint(-3, 3) for _ in range(3)] for _ in range(3))
            T = {k: K.P(x) for k, x in simple(u, v, w).items()}
            M = K.at_int(K.flatten(T), {"lam": 0, "a": 0, "b": 0})
            self.assertLessEqual(K.rank_q(M), 2)

    def test_unit_pivots(self):
        lam = K.P(1, lam=1)
        M = [[K.P(1), lam], [lam, K.P(1)]]
        piv, res = K.unit_pivots(M)
        self.assertEqual(len(piv), 1)
        self.assertEqual(res, [[{(0, 0, 0): 1, (2, 0, 0): -1}]])
        M = [[K.P(2), K.P(1)], [K.P(1), K.P(0)]]
        piv, res = K.unit_pivots(M)
        self.assertEqual(len(piv), 2)

    def test_unit_pivots_bound_ranks_everywhere(self):
        rng = random.Random(7)
        choices = [K.P(0), K.P(1), K.P(-1), K.P(2), K.P(1, lam=1), K.padd(K.P(1), K.P(1, lam=1), -1)]
        for _ in range(30):
            M = [[rng.choice(choices) for _ in range(5)] for _ in range(5)]
            piv, _ = K.unit_pivots(M)
            for q in (2, 3, 5):
                F = K.GF(q)
                for lv in range(q):
                    self.assertLessEqual(len(piv), K.flat_rank_gf(M, {"lam": lv, "a": 0, "b": 0}, F))

    def test_apply_ops(self):
        a = K.P(1, a=1)
        M = [[K.P(1), K.P(0)], [a, K.P(1)]]
        out = K.apply_ops(M, [("R", 1, [(K.pneg(a), 0)])])
        self.assertTrue(K.matrices_equal(out, [[K.P(1), K.P(0)], [K.P(0), K.P(1)]]))
        out = K.apply_ops(M, [("C", 0, [(K.pneg(a), 1)])])
        self.assertTrue(K.matrices_equal(out, [[K.P(1), K.P(0)], [K.P(0), K.P(1)]]))


class Fields(unittest.TestCase):
    def test_axioms(self):
        for q in K.FIELDS:
            F = K.GF(q)
            els = range(q)
            for x, y, z in itertools.product(els, repeat=3):
                self.assertEqual(F.mul(x, F.add(y, z)), F.add(F.mul(x, y), F.mul(x, z)))
                self.assertEqual(F.mul(F.mul(x, y), z), F.mul(x, F.mul(y, z)))
            for x in els:
                self.assertEqual(F.add(x, F.neg(x)), 0)
                if x:
                    self.assertEqual(F.mul(x, F.inv(x)), 1)
            orders = set()
            for x in range(1, q):         # the multiplicative group is cyclic: some element has order q - 1
                y, n = x, 1
                while y != 1:
                    y, n = F.mul(y, x), n + 1
                orders.add(n)
            self.assertIn(q - 1, orders)

    def test_rank_gf(self):
        F = K.GF(4)                          # 2 is x and 3 is x + 1: the second row is x times the first
        self.assertEqual(K.rank_gf([[1, 2, 3], [2, 3, 1]], F), 1)
        self.assertEqual(K.rank_gf([[1, 2, 3], [1, 3, 2]], F), 2)
        self.assertEqual(K.rank_gf([[1, 1], [1, 1]], K.GF(2)), 1)
        self.assertEqual(K.rank_gf([[1, 2], [3, 4]], K.GF(5)), 2)

    def test_rank_one_matrices(self):
        for q in (2, 3, 4):
            F = K.GF(q)
            every, lines = K.rank_one_matrices(F)
            self.assertEqual(len(lines), (q * q + q + 1) ** 2)
            self.assertEqual(len(every), (q * q + q + 1) ** 2 * (q - 1))
            self.assertTrue(all(K.rank_gf([m[0:3], m[3:6], m[6:9]], F) == 1 for m in every))


class Search(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        vecs = [v for v in itertools.product(range(2), repeat=3) if any(v)]
        cls.simples = [simple(u, v, w) for u in vecs for v in vecs for w in vecs]
        codes = [pack2(s) for s in cls.simples]
        cls.le1 = {0} | set(codes)
        cls.le2 = {x ^ y for x in cls.le1 for y in cls.le1}

    def brute_rank_at_most(self, T, r):
        t = pack2(T)
        if r == 2:
            return t in self.le2
        if r == 3:
            return any((t ^ s) in self.le2 for s in self.le1)
        if r == 4:
            return any((t ^ s) in self.le2 for s in self.le2)
        raise ValueError(r)

    def test_against_brute_force_over_f2(self):
        rng = random.Random(2018)
        F = K.GF(2)
        R1 = K.rank_one_matrices(F)
        checked = 0
        for trial in range(160):
            n_terms = rng.randint(1, 6)
            T = {}
            for _ in range(n_terms):
                T = add_mod(T, rng.choice(self.simples), 2)
            d = K.rank_gf(K.slices_gf(T, F), F)
            for r in (d, d + 1):
                if r < 2 or r > 4:
                    continue
                got, _ = K.rank_at_most(T, r, F, R1)
                self.assertEqual(got, self.brute_rank_at_most(T, r), (T, r))
                checked += 1
        self.assertGreater(checked, 100)

    def test_known_decompositions_are_found(self):
        rng = random.Random(5)
        for q in (3, 5):
            F = K.GF(q)
            R1 = K.rank_one_matrices(F)
            for _ in range(6):
                T = {}
                terms = [tuple(tuple(rng.randrange(q) for _ in range(3)) for _ in range(3)) for _ in range(4)]
                for u, v, w in terms:
                    T = add_mod(T, simple(u, v, w), q)
                d = K.rank_gf(K.slices_gf(T, F), F)
                if d == 3:
                    self.assertTrue(K.rank_at_most(T, 4, F, R1)[0])

    def test_dimension_limits(self):
        F = K.GF(3)
        unit = {(i, i, i): 1 for i in range(3)}
        self.assertTrue(K.rank_at_most(unit, 3, F)[0])
        self.assertFalse(K.rank_at_most(unit, 2, F)[0])
        self.assertTrue(K.rank_at_most({(0, 0, 0): 1}, 4, F)[0])     # S spanned by its rank-one element
        with self.assertRaises(ValueError):
            K.rank_at_most({(0, 0, 0): 1, (0, 1, 1): 1}, 4, F)    # dim S = 1, not rank one: covers r <= 2 only

    def test_fixed_tensor_slices_independent(self):
        T = K.tensor_of_terms([(1, t) for t in K.FIXED])
        for q in K.FIELDS:
            F = K.GF(q)
            self.assertEqual(K.rank_gf(K.slices_gf(T, F), F), 3)


class Tensors(unittest.TestCase):
    def test_det_and_per(self):
        self.assertEqual(K.det_tensor(2), {(0, 1): 1, (1, 0): -1})
        self.assertEqual(K.per_tensor(2), {(0, 1): 1, (1, 0): 1})
        self.assertEqual(len(K.det_tensor(3)), 6)
        self.assertEqual(sum(K.det_tensor(4).values()), 0)

    def test_case_tensors(self):
        T = K.case_tensor(1)
        self.assertEqual(T[(0, 1, 2)], {(0, 0, 0): 1, (1, 0, 0): -1})
        T = K.case_tensor(2)
        self.assertEqual(T[(0, 1, 0)], {(0, 1, 0): -1})
        self.assertEqual(T[(0, 1, 1)], {(0, 0, 1): -1})
        T = K.case_tensor(3)
        self.assertEqual(T[(0, 0, 0)], {(1, 0, 0): -1})

    def test_outputs_named_once(self):
        self.assertEqual(len(K.OUTPUTS), len(set(K.OUTPUTS)))
        self.assertLessEqual(len(K.TEST), 600)


if __name__ == "__main__":
    unittest.main()
