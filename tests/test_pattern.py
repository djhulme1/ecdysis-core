"""Masquelier, Guyonneau & Thorpe's STDP pattern finder (stdp/pattern.py and stdp/pattern.c): the scoring of a run
at and beside each criterion; the C simulation against the Python reference; the generator's pasting and rates; and
determinism under a seed. The C tests need gcc.

Run with: python3 -m unittest tests.test_pattern
"""

import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("stdp_pattern", os.path.join(HERE, "..", "stdp", "pattern.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)
HAVE_GCC = shutil.which("gcc") is not None


def record(posts, sections, weights=None):
    return {"post": [str(p) for p in posts], "sections": [str(s) for s in sections],
            "weights": [str(x) for x in (weights or [0.0] * M.N)], "posts": [str(len(posts))], "pasted": ["750"],
            "consecutive": ["0"], "afferent_rate_original": ["54"], "afferent_rate_forced": ["9"],
            "afferent_rate_total": ["64"]}


class Scoring(unittest.TestCase):
    OFF = 300000.0
    SECTIONS = list(range(0, 3000, 4))[:750]

    def posts(self, latency=4.0, skip=0, extra=()):
        starts = [s * 50.0 + self.OFF for s in self.SECTIONS]
        return sorted([t + latency for t in starts[skip:]] + list(extra))

    def test_selective_and_strict(self):
        s = M.score(record(self.posts(), self.SECTIONS))
        self.assertEqual((s["hit_rate"], s["false_alarms"], s["latency"]), (1.0, 0, 4.0))
        self.assertTrue(s["selective"] and s["strict"] and not s["stopped"])

    def test_beside_each_criterion(self):
        one_fa = M.score(record(self.posts(extra=[self.OFF + 60.0]), self.SECTIONS))      # 60 ms after a start: outside
        self.assertTrue(one_fa["selective"])
        self.assertFalse(one_fa["strict"])
        many = M.score(record(self.posts(extra=[self.OFF + 60.0 + 200 * k for k in range(16)]), self.SECTIONS))
        self.assertEqual(many["false_alarms"], 16)
        self.assertFalse(many["selective"])
        late = M.score(record(self.posts(latency=10.0), self.SECTIONS))
        self.assertFalse(late["selective"] or late["strict"])
        misses = M.score(record(self.posts(skip=76), self.SECTIONS))                       # 674 of 750: 89.9%
        self.assertFalse(misses["selective"])
        fewer = M.score(record(self.posts(skip=75), self.SECTIONS))                        # 675 of 750: 90%
        self.assertTrue(fewer["selective"])
        self.assertFalse(fewer["strict"])
        quiet = M.score(record([self.OFF + 1.0], self.SECTIONS))
        self.assertTrue(quiet["stopped"])

    def test_seeds(self):
        self.assertEqual(M.seed_of("ab" * 32, 3), M.seed_of("ab" * 32, 3))
        self.assertNotEqual(M.seed_of("ab" * 32, 3), M.seed_of("ab" * 32, 4))


@unittest.skipUnless(HAVE_GCC, "no gcc")
class InC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp()
        cls.exe = M.compile_c(cls.work)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def test_reference(self):
        ok, info = M.reference_control(self.exe, self.work, 77)
        self.assertTrue(ok, info)

    def test_generator_and_determinism(self):
        a = M.run_c(self.exe, self.work, 5, base=20, repeats=1)
        b = M.run_c(self.exe, self.work, 5, base=20, repeats=1)
        self.assertEqual(a, b)
        sections = [int(x) for x in a["sections"]]
        self.assertEqual(len(sections), 100)                       # a quarter of 400 sections
        self.assertTrue(all(y - x >= 2 for x, y in zip(sections, sections[1:])))
        self.assertAlmostEqual(float(a["afferent_rate_original"][0]), 54, delta=3)
        self.assertAlmostEqual(float(a["spontaneous_rate"][0]), 10, delta=0.5)


if __name__ == "__main__":
    unittest.main()
