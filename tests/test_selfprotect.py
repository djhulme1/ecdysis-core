"""Sayama's self-protecting evoloops (evoloop/selfprotect.py and evoloop/sp.c): the transcribed tables and their
refusals; each model's completion steps, checked at chosen situations; the original's table against evoloop/check.py's;
the inherited rules; the entropy; the verdict at and beside each condition; the C update and census against numpy and
evoloop/check.py's census (with gcc); and, with Golly's rle at inputs/ (or EVOLOOP_INPUTS), a short run end to end.

Run with: python3 -m unittest tests.test_selfprotect
"""

import importlib.util
import math
import os
import shutil
import sys
import tempfile
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("evoloop_selfprotect", os.path.join(HERE, "..", "evoloop", "selfprotect.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)
E = M.E

INPUTS = os.environ.get("EVOLOOP_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE_RLE = os.path.isfile(os.path.join(INPUTS, "Evoloop.rle"))
HAVE_GCC = shutil.which("gcc") is not None
TABLES = {m: M.build_rules(m) for m in M.MODELS}


class Tables(unittest.TestCase):
    def test_counts_and_refusal(self):
        self.assertEqual([len(M.table_rules(k)) for k in (3, 4, 5, 6, 7)], [24, 66, 49, 28, 12])
        text, sha, count = M.TABLES[5]
        try:
            M.TABLES[5] = (text.replace("30292->6", "30292->9"), sha, count)
            with self.assertRaises(M.Refused):
                M.table_rules(5)
        finally:
            M.TABLES[5] = (text, sha, count)

    def test_two_images_refused(self):
        t = -np.ones((M.Q,) * 5, dtype=np.int16)
        M.define(t, [(1, 0, 2, 7, 2, 7)], "first")
        with self.assertRaises(M.Refused):
            M.define(t, [(1, 2, 0, 2, 7, 1)], "a rotation with another image")


class Completion(unittest.TestCase):
    def image(self, model, c, n, e, s, w):
        return int(TABLES[model][0][c, n, e, s, w])

    def test_original_equals_check_py(self):
        sayama9, _ = E.sayama_rules()
        self.assertTrue(np.array_equal(TABLES["original"][0][:9, :9, :9, :9, :9], sayama9))

    def test_inherited_and_quiescent(self):
        t2 = M.table2_mask()
        for m in M.SP:
            with self.subTest(model=m):
                self.assertTrue(np.array_equal(TABLES[m][0][t2], TABLES["original"][0][t2]))
                self.assertEqual(self.image(m, 0, 0, 0, 0, 0), 0)

    def test_steps(self):
        # 8 -> 0 with no condition, in every model
        for m in M.MODELS:
            self.assertEqual(self.image(m, 8, 9, 9, 1, 2), 0)
        # shielded and deflecting: with an 8 beside, 9 -> 0; 1 -> 8 when a 2 to 7 is beside, else unchanged
        for m in ("shielded", "deflecting"):
            self.assertEqual(self.image(m, 9, 8, 0, 0, 0), 0)
            self.assertEqual(self.image(m, 1, 8, 5, 0, 0), 8)
            self.assertEqual(self.image(m, 1, 8, 9, 0, 0), 1)
            self.assertEqual(self.image(m, 6, 8, 0, 0, 0), 1)
            self.assertEqual(self.image(m, 9, 1, 1, 1, 1), 8)          # left undefined: 9 -> 8
        # poisoning: 9 -> 0 at the centre; a 9 beside turns 1 to 7 into 9 and leaves 0; then the 8 step
        self.assertEqual(self.image("poisoning", 9, 2, 2, 2, 2), 0)
        self.assertEqual(self.image("poisoning", 4, 9, 0, 0, 0), 9)
        self.assertEqual(self.image("poisoning", 0, 9, 9, 9, 9), 0)
        self.assertEqual(self.image("poisoning", 5, 8, 0, 0, 0), 0)
        self.assertEqual(self.image("poisoning", 3, 1, 1, 1, 1), 8)
        # a Table 4 rule and a rotation of it (30292 -> 9: C 3, T 0, R 2, B 9, L 2)
        self.assertEqual(self.image("shielded", 3, 0, 2, 9, 2), 9)
        self.assertEqual(self.image("shielded", 3, 2, 0, 2, 9), 9)
        self.assertEqual(self.image("deflecting", 3, 0, 2, 9, 2), 6)

    def test_defined_counts(self):
        self.assertEqual({m: int(TABLES[m][1].sum()) for m in M.MODELS},
                         {"original": 1011, "shielded": 1361, "deflecting": 1301, "poisoning": 1215})


class Entropy(unittest.TestCase):
    def test_entropy(self):
        c = np.zeros(M.NBINS + 1, dtype=np.uint16)
        self.assertEqual(M.entropy(c), 0.0)
        c[1] = 7                                                     # seven loops of size 4
        self.assertAlmostEqual(M.entropy(c), 0.0)
        c[:] = 0
        c[1:5] = 1                                                   # four sizes, one loop each: log 4
        self.assertAlmostEqual(M.entropy(c), math.log(4))
        c[:] = 0
        c[1], c[2] = 3, 1
        self.assertAlmostEqual(M.entropy(c), math.log(4) - 3 * math.log(3) / 4)
        c[M.NBINS] = 50                                              # variants are not loops
        self.assertAlmostEqual(M.entropy(c), math.log(4) - 3 * math.log(3) / 4)


class Verdict(unittest.TestCase):
    def H(self, **kw):
        h = {(m, a): 1.0 for m in M.MODELS for a in "AB"}
        h.update({("shielded", "A"): 1.1, ("deflecting", "A"): 1.2, ("poisoning", "A"): 1.3,
                  ("deflecting", "B"): 1.2, ("poisoning", "B"): 0.9})
        for k, v in kw.items():
            m, a = k.split("_")
            h[(m, a)] = v
        return h

    def test_at_and_beside_each_condition(self):
        self.assertTrue(all(M.conditions(self.H()).values()))
        self.assertTrue(all(M.conditions(self.H(poisoning_B=1.2)).values()))         # not above: equal passes
        for bad in (self.H(shielded_A=1.0), self.H(poisoning_A=0.99), self.H(deflecting_B=1.0),
                    self.H(poisoning_B=1.21)):
            with self.subTest(bad=bad):
                self.assertEqual(sum(M.conditions(bad).values()), 2)


@unittest.skipUnless(HAVE_GCC, "no gcc")
class InC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp()
        cls.exe = M.compile_sp(cls.work)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def test_update_equals_numpy(self):
        p = E.build(8)
        for m in M.MODELS:
            g0 = E.place(p, 48)
            _, shots = M.run_c(self.exe, self.work, f"t_{m}", TABLES[m][0], g0, 700, M.DETECTOR[m], (700,), 100)
            g, flat = g0, TABLES[m][0].ravel()
            for _ in range(700):
                g = M.step(g, flat)
            with self.subTest(model=m):
                self.assertTrue(np.array_equal(g, shots[700]))

    def test_census_equals_check_py(self):
        # evoloop/check.py's drawn torus: loops of sizes 4 to 13, a 2 x 3 hole ringed with sheath, a broken loop;
        # then a loop wrapped across the torus' corner, and a hole whose ring holds a 9.
        L = 200
        g = np.zeros((L, L), dtype=np.uint8)
        y = x = 2
        for n in E.SIZES:
            p = E.build(n)
            h, w = p.shape
            if x + w + 2 > L:
                x, y = 2, y + 21
            g[y:y + h, x:x + w] = p
            x += w + 3
        g[150:154, 10:15] = 2
        g[151:153, 11:14] = 0
        broken = E.build(6)
        broken[2, 4] = 1
        g[150:160, 40:50] = broken
        g = np.roll(np.roll(g, -5, 0), -5, 1)                         # the first loops now wrap round the corner
        nine = E.build(7)
        nine[2, 5] = 9
        g[100:111, 120:131] = nine
        table = np.zeros((M.Q,) * 5, dtype=np.uint8)                  # no update is taken: only the census
        rec, _ = M.run_c(self.exe, self.work, "census", table, g, 0, 9, (), 0)
        c1, c2 = M.census_record(rec, 0)
        self.assertEqual(c1, M.py_census(g, (2, 3)))
        self.assertEqual(c2, M.py_census(g, (2, 3, 9)))
        self.assertEqual(c1["loops"], {n: 1 for n in E.SIZES})
        self.assertEqual(c1["variants"], 1)
        self.assertEqual(c2["loops"], {**{n: 1 for n in E.SIZES}, 7: 2})


@unittest.skipUnless(HAVE_RLE and HAVE_GCC, "Golly's rle is not at inputs/ (or EVOLOOP_INPUTS), or no gcc")
class Short(unittest.TestCase):
    def test_short_run(self):
        res = tempfile.mkdtemp()
        try:
            out, detail = M.run("ab" * 32, inputs=INPUTS, results=res, updates=3000, window_from=1000,
                                small=((60, 300),))
        finally:
            shutil.rmtree(res, ignore_errors=True)
        self.assertEqual(out["controls_passed"], out["controls_total"])
        self.assertEqual(set(out), set(M.OUTPUTS))
        self.assertEqual(len(detail["runs"]), 8)
        self.assertTrue(all(r["window_censuses"] == 50 for r in detail["runs"]))


if __name__ == "__main__":
    unittest.main()
