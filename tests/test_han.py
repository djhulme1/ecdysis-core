"""Han's border Waring rank of x1...xn (koszul/han.py): the reading of the e-print (its hash, its tar, comments and
whitespace, each printed formula refused when altered or commented out); tableaux, Kostka numbers and orbits on hand
values; the exterior signs and the packing of tuples; the Koszul flattening of the 2 x 2 permanent and determinant by
hand, and its two implementations agreeing at n = 3; the minors and evaluations against direct determinants; ranks
modulo a prime on known matrices, Miller-Rabin, the multinomial expansion at n = 1; the determinant's flattening at
n = 3 (a control, not the test); the verdict at and beside each condition; the seed refused; and, with the e-print at
inputs/ (or HAN_INPUTS), that its source holds every printed formula as read. None of the ranks the test is about is
computed here.

Run with: python3 -m unittest discover -s tests -p test_han.py
"""

import hashlib
import importlib.util
import io
import itertools
import math
import os
import tarfile
import tempfile
import unittest
from fractions import Fraction

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("koszul_han", os.path.join(HERE, "..", "koszul", "han.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

INPUTS = os.environ.get("HAN_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = all(os.path.isfile(os.path.join(INPUTS, name)) for name, _ in M.INPUTS.values())


def targz(files):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for name, text in files.items():
            data = text.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def fake_tex():
    return "\n".join(M.PRINTED_TEX) + "\n"


def det_mod(rows, p):
    """A determinant modulo p by exact Fractions (for small matrices)."""
    a = [[Fraction(x) for x in r] for r in rows]
    n = len(a)
    d = Fraction(1)
    for c in range(n):
        piv = next((r for r in range(c, n) if a[r][c] != 0), None)
        if piv is None:
            return 0
        if piv != c:
            a[c], a[piv] = a[piv], a[c]
            d = -d
        d *= a[c][c]
        for r in range(c + 1, n):
            f = a[r][c] / a[c][c]
            a[r] = [x - f * y for x, y in zip(a[r], a[c])]
    assert d.denominator == 1
    return int(d) % p


class Reading(unittest.TestCase):
    def test_hash_refused(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x")
            with open(path, "wb") as fh:
                fh.write(b"other")
            with self.assertRaises(M.Refused):
                M.read_bytes(path, M.INPUTS["eprint"][1])
            self.assertEqual(M.read_bytes(path, hashlib.sha256(b"other").hexdigest()), b"other")

    def test_tar(self):
        self.assertEqual(M.tex_of(targz({M.TEX: "x"})), "x")
        with self.assertRaises(M.Refused):
            M.tex_of(targz({"other.tex": "x"}))
        with self.assertRaises(M.Refused):
            M.tex_of(b"not a tar")

    def test_source_held_and_refused(self):
        M.check_source(fake_tex())
        for k in (0, 1, 2, len(M.PRINTED_TEX) - 1):
            s = M.PRINTED_TEX[k]
            changed = s.replace("2", "3", 1) if "2" in s else s + "x"
            with self.assertRaises(M.Refused):
                M.check_source(fake_tex().replace(s, changed))
            with self.assertRaises(M.Refused):
                M.check_source(fake_tex().replace(s, "%" + s))

    @unittest.skipUnless(HAVE, "the e-print is not at inputs/")
    def test_real_eprint_as_read(self):
        name, sha = M.INPUTS["eprint"]
        M.check_source(M.tex_of(M.read_bytes(os.path.join(INPUTS, name), sha)))


class Tableaux(unittest.TestCase):
    def test_kostka_and_weyl(self):
        self.assertEqual(M.kostka((2, 1), (1, 1, 1)), 2)
        self.assertEqual(M.kostka((2, 1), (2, 1)), 1)
        self.assertEqual(M.kostka((2, 1), (1, 2)), 1)
        self.assertEqual(M.kostka((2, 1), (3,)), 0)
        self.assertEqual(M.kostka((3, 2, 1), (1,) * 6), 16)            # standard tableaux of (3,2,1)
        self.assertEqual(M.weyl_dimension((2, 1), 3), 8)
        self.assertEqual(M.weyl_dimension((1,), 4), 4)
        self.assertEqual(M.staircase(4), (3, 2, 1))

    def test_ssyt(self):
        got = sorted(M.ssyt((2, 1), (1, 1, 1)))
        self.assertEqual(got, [((0, 1), (2,)), ((0, 2), (1,))])
        self.assertEqual(M.ssyt((2, 1), (2, 1)), [((0, 1), (0,))])
        self.assertEqual(M.ssyt((2, 1), (3, 0)), [])
        for shape, content in (((3, 2, 1), (2, 2, 1, 1)), ((2, 2), (1, 1, 1, 1)), ((3, 1), (1, 2, 1))):
            tabs = M.ssyt(shape, content)
            self.assertEqual(len(tabs), M.kostka(shape, content))
            for cols in tabs:
                self.assertTrue(all(list(c) == sorted(set(c)) for c in cols))

    def test_class_contents(self):
        found = M.class_contents([[0, 1, 2]], 3, 2)
        self.assertEqual(sorted(found), [((1, 1, 1), 1), ((2, 1, 0), 6)])
        self.assertEqual(sum(o for _, o in found), 7)                    # compositions of 3 into 3 parts <= 2
        found = M.class_contents([[0], [1, 2]], 2, 2)
        self.assertEqual(sorted(found), [((0, 1, 1), 1), ((0, 2, 0), 2), ((1, 1, 0), 2), ((2, 0, 0), 1)])


class Flattening(unittest.TestCase):
    def test_wedge_and_pack(self):
        self.assertEqual(M.wedge_front(1, 0b101), (-1, 0b111))
        self.assertEqual(M.wedge_front(0, 0b110), (1, 0b111))
        self.assertIsNone(M.wedge_front(2, 0b100))
        self.assertEqual(M.to_masks(((0, 2), (1,))), (0b101, 0b010))
        key = M.pack((0b101, 0b010), 3)
        self.assertEqual(M.unpack(key, 3, 2), (0b101, 0b010))

    def test_two_by_two_by_hand(self):
        # per_2 = e0(x)e1 + e1(x)e0; column 0 = {0} receives factor 1, the empty column factor 0:
        # e0(x)e1 gives (e1 ^ e0) (x) e0 = -(e0 ^ e1) (x) e0; e1(x)e0 gives e0 ^ e0 = 0.
        t = M.to_masks(((0,),))
        self.assertEqual(M.image_perm(t, 2, False), {M.pack((0b01,), 2): -1})
        self.assertEqual(M.image_perm(t, 2, True), {M.pack((0b01,), 2): -1})
        t = M.to_masks(((1,),))
        self.assertEqual(M.image_perm(t, 2, False), {M.pack((0b10,), 2): 1})
        self.assertEqual(M.image_perm(t, 2, True), {M.pack((0b10,), 2): -1})

    def test_two_implementations_agree(self):
        n = 3
        for nu, _ in M.class_contents([list(range(n))], 3, n - 1):
            for t in M.w_tuples(n, nu):
                for signed in (False, True):
                    self.assertEqual(M.image_perm(t, n, signed), M.image_terms(t, n, M.perm_terms(n, signed)))

    def test_terms(self):
        self.assertEqual(M.power_terms(3), [(1, (0, 0, 0))])
        self.assertEqual(sorted(M.twin_terms(3)), [(1, (0, 0, 1)), (1, (0, 1, 0)), (1, (1, 0, 0))])
        self.assertEqual(sum(c for c, _ in M.perm_terms(3, True)), 0)
        self.assertEqual(M.perm_sign((1, 0, 2)), -1)
        self.assertEqual(M.perm_sign((2, 0, 1)), 1)

    def test_w_tuples(self):
        tuples = M.w_tuples(3, (1, 1, 1))
        self.assertEqual(len(tuples), 3)                                # {0,1}{2}, {0,2}{1}, {1,2}{0}
        total = sum(o * len(M.w_tuples(4, nu)) for nu, o in M.class_contents([list(range(4))], 6, 3))
        self.assertEqual(total, math.comb(4, 3) * math.comb(4, 2) * math.comb(4, 1))


class Evaluation(unittest.TestCase):
    p = 2147483647

    def test_points_and_minors(self):
        X = M.draw_points("ab" * 32, self.p, 4, 3)
        self.assertEqual(X.shape, (3, 4, 3))
        self.assertTrue(np.array_equal(X, M.draw_points("ab" * 32, self.p, 4, 3)))
        self.assertTrue((X >= 0).all() and (X < self.p).all())
        T = M.minors_table(X, self.p)
        for j in range(3):
            for mask in range(1, 16):
                rows = [i for i in range(4) if mask >> i & 1]
                if len(rows) > 3:
                    continue
                sub = [[int(X[j, r, c]) for c in range(len(rows))] for r in rows]
                self.assertEqual(int(T[mask, j]), det_mod(sub, self.p))
        self.assertTrue((T[0] == 1).all())

    def test_evaluate(self):
        X = M.draw_points("cd" * 32, self.p, 3, 5)
        T = M.minors_table(X, self.p)
        key = M.pack((0b011, 0b100), 3)
        img = {key: 3, M.pack((0b101, 0b010), 3): -2}
        got = M.evaluate([img, {}], 3, T, 5, self.p)
        want = (3 * (T[0b011] * T[0b100] % self.p) - 2 * (T[0b101] * T[0b010] % self.p)) % self.p
        self.assertTrue(np.array_equal(got[0], want % self.p))
        self.assertTrue((got[1] == 0).all())

    def test_rank_mod(self):
        p = self.p
        self.assertEqual(M.rank_mod(np.eye(4, dtype=np.int64), p), 4)
        m = np.array([[1, 2, 3], [4, 5, 6], [5, 7, 9]], dtype=np.int64)
        self.assertEqual(M.rank_mod(m, p), 2)
        self.assertEqual(M.rank_mod(np.array([[1, 0], [0, p]], dtype=np.int64), p), 1)
        self.assertEqual(M.rank_mod(np.zeros((3, 5), dtype=np.int64), p), 0)
        self.assertEqual(M.rank_mod(np.array([[0, 1, 1], [0, 2, 2], [1, 0, 0]], dtype=np.int64), p), 2)

    def test_primes(self):
        self.assertTrue(all(M.is_prime(q) for q in M.PRIMES))
        self.assertFalse(M.is_prime(561))
        self.assertFalse(M.is_prime(2 ** 31 - 3))
        self.assertTrue(M.is_prime(97))

    def test_det_flattening_n3(self):
        # a control, not the test: Psi(det_3) is a scalar on S_lambda V, so its flattening has full rank 8
        points = M.Points("ef" * 32)
        rank, blocks = M.flattening_rank(3, lambda t: M.image_perm(t, 3, True), [[0, 1, 2]], points)
        self.assertEqual(rank, 8)
        self.assertEqual(sum(b["orbit"] * b["K"] for b in blocks), 8)
        self.assertIsNotNone(M.det_scalar(3, points))


class Identity(unittest.TestCase):
    def test_compositions_and_n1(self):
        self.assertEqual(sorted(M.compositions(2, 2)), [(0, 2), (1, 1), (2, 0)])
        self.assertEqual(len(list(M.compositions(3, 3))), 10)
        self.assertTrue(M.polarization_holds(1))


class Verdict(unittest.TestCase):
    def good(self):
        per = {n: {"rank": 2 ** math.comb(n, 2), "short": []} for n in M.N_TEST}
        power = {n: 2 ** math.comb(n - 1, 2) for n in M.N_TEST}
        reach = dict(power)
        polar = {n: True for n in M.N_POLAR}
        return per, power, reach, polar

    def test_conditions(self):
        per, power, reach, polar = self.good()
        self.assertTrue(all(v is True for v in M.conditions(per, power, reach, polar).values()))
        per[6]["rank"] -= 1
        c = M.conditions(per, power, reach, polar)
        self.assertFalse(c["the flattening of x1...xn has full rank 2^C(n,2) for n = 2 to 7"])
        per, power, reach, polar = self.good()
        power[7] += 1
        self.assertFalse(M.conditions(per, power, reach, polar)
                         ["the flattening of x1^n has rank at most 2^C(n-1,2) for n = 2 to 7"])
        per, power, reach, polar = self.good()
        reach[5] += 1
        self.assertIsNone(M.conditions(per, power, reach, polar)
                          ["the flattening of x1^n has rank at most 2^C(n-1,2) for n = 2 to 7"])
        per, power, reach, polar = self.good()
        polar[8] = False
        self.assertFalse(M.conditions(per, power, reach, polar)["the polarization identity holds for n = 2 to 8"])

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")

    def test_outputs_named(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)
        self.assertEqual(list(itertools.chain(M.N_TEST)), [2, 3, 4, 5, 6, 7])


if __name__ == "__main__":
    unittest.main()
