"""Izhikevich's distal reward (dastdp/izh2007.py, with the port dastdp/dastdp.c): the program's reading (comments and
whitespace removed, each statement the port follows refused when altered, the pinned hash); the seeds; the parsing of
a draw's line; the success rule and the verdict at and beside 21; the summary of draws; the port compiled, its
self-test, and short runs of 2 s of model time (their lines complete, the same seed printing the same line, another
seed another network); the seed refused; and, with the program at inputs/ (or IZH2007_INPUTS), that it is the pinned
file and holds every statement, which runs no draw.

Run with: python3 -m unittest discover -s tests -p test_izh2007.py
"""

import hashlib
import importlib.util
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("izh2007", os.path.join(HERE, "..", "dastdp", "izh2007.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

INPUTS = os.environ.get("IZH2007_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = os.path.isfile(os.path.join(INPUTS, M.INPUT[0]))
GCC = shutil.which("gcc") is not None

# A program holding every statement the port follows, set out with MATLAB's spaces, line breaks and comments.
GOOD = "\n".join(p.replace(";", ";   % a comment\n").replace(",", ", ") for p in M.PROGRAM)


def line(**over):
    base = {"seed": 7, "seconds": 3600, "interval": 10, "n1": 3, "syn": 9, "n2": 41, "reached_ms": 1234567,
            "rewards_before": 38, "rewards_scheduled": 90, "rewards_delivered": 88, "rewards_first_600s": 6,
            "rewards_last_600s": 19, "final_weight": 4.0, "others_reached": 0, "others_at_max_end": 0,
            "mean_weight": 0.21, "share_below_0.1": 0.6, "rate_e": 1.1, "rate_i": 0.9}
    base.update(over)
    return " ".join(f"{k}={v}" for k, v in base.items())


class Program(unittest.TestCase):
    def test_normalise(self):
        self.assertEqual(M.normalise("a = 1;  % set a\n b=[1, 2];\n"), "a=1;b=[1,2];")

    def test_good_program_passes(self):
        self.assertTrue(M.check_program(GOOD))

    def test_each_alteration_is_refused(self):
        for old, new in (("sm=4;", "sm=5;"), ("interval=20;", "interval=25;"), ("0.95*STDP", "0.9*STDP"),
                         ("(0.002+DA)", "(0.02+DA)"), ("DA=DA*0.995;", "DA=DA*0.99;"), ("-1.5*STDP", "-1.2*STDP"),
                         ("ceil(2000*rand)", "ceil(1000*rand)"), ("13*(rand(N,1)-0.5)", "20*(rand(N,1)-0.5)")):
            flat = M.normalise(GOOD)
            self.assertIn(old, flat)
            with self.subTest(old=old), self.assertRaises(M.Refused):
                M.check_program(flat.replace(old, new))

    def test_a_commented_statement_is_missing(self):
        with self.assertRaises(M.Refused):
            M.check_program(GOOD.replace("DA=DA+0.5;", "% DA=DA+0.5;"))

    def test_hash(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, M.INPUT[0]), "w") as fh:
                fh.write(GOOD)
            with self.assertRaises(M.Refused):
                M.read_program(d)


class Seeds(unittest.TestCase):
    def test_seeds(self):
        seed = "ab" * 32
        a, b = M.seeds_of(seed, 10), M.seeds_of(seed, 20)
        self.assertEqual(len(a), 50)
        self.assertEqual(len(set(a + b)), 100)
        self.assertEqual(a[0], int.from_bytes(hashlib.sha256(f"{seed}:10:1".encode()).digest()[:8], "big"))
        self.assertEqual(a, M.seeds_of(seed, 10))


class Draws(unittest.TestCase):
    def test_parse(self):
        d = M.parse(line())
        self.assertEqual(d["reached_ms"], 1234567)
        self.assertEqual(d["share_below_0.1"], 0.6)
        with self.assertRaises(ValueError):
            M.parse(line() + " extra=1")

    def test_success_rule(self):
        self.assertTrue(M.success(M.parse(line())))
        self.assertFalse(M.success(M.parse(line(reached_ms=-1))))
        self.assertFalse(M.success(M.parse(line(others_reached=1))))

    def test_verdict_at_and_beside_21(self):
        self.assertTrue(all(M.conditions(21).values()))
        self.assertFalse(all(M.conditions(20).values()))

    def test_summary(self):
        draws = [M.parse(line(reached_ms=600000 * k, rewards_before=30 + k)) for k in (1, 2, 3)]
        draws.append(M.parse(line(reached_ms=-1, others_reached=2)))
        s = M.summary(draws)
        self.assertEqual((s["reached"], s["succeeded"], s["others_draws"], s["others_most"]), (3, 3, 1, 2))
        self.assertEqual(s["rewards_before"], "32.0 +/- 1.0")
        self.assertEqual(s["minutes"], "20.0")


@unittest.skipUnless(GCC, "no gcc in this image")
class Port(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp()
        cls.exe = M.compile_port(cls.work)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work)

    def test_selftest(self):
        out = M.subprocess.run([self.exe, "selftest"], capture_output=True, text=True)
        self.assertEqual((out.returncode, out.stdout.strip()), (0, "selftest_failures=0"))

    def test_short_runs(self):
        one = M.run_draw(self.exe, 11, 2, 10)
        d = M.parse(one)
        self.assertEqual((d["seconds"], d["interval"], d["seed"]), (2, 10, 11))
        self.assertTrue(1 <= d["n1"] <= 800 and 1 <= d["n2"] <= 800)
        self.assertEqual(M.run_draw(self.exe, 11, 2, 10), one)
        other = M.parse(M.run_draw(self.exe, 12, 2, 10))
        self.assertNotEqual((other["n1"], other["syn"], other["mean_weight"]), (d["n1"], d["syn"], d["mean_weight"]))

    def test_bad_arguments(self):
        out = M.subprocess.run([self.exe, "1", "0", "10"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 2)


class Seed(unittest.TestCase):
    def test_refuses_a_bad_seed(self):
        with self.assertRaises(M.Refused):
            M.run("xyz", inputs=os.path.join(HERE, "_never"), results=os.path.join(HERE, "_never"))


@unittest.skipUnless(HAVE, "the program is not at inputs/ (or IZH2007_INPUTS)")
class Pinned(unittest.TestCase):
    def test_pinned_program_holds_every_statement(self):
        self.assertTrue(M.check_program(M.read_program(INPUTS)))


if __name__ == "__main__":
    unittest.main()
