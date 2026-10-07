"""The Erdős discrepancy check on made-up cases: the paper's statements and sequence read and anything else refused;
discrepancy computed directly against brute force; the journal's Example 4 (CBound_2 on five terms, 26 clauses)
reproduced clause for clause; the formula's printed sizes; Proposition 6's shortened progressions; the extension of a
sequence to the counters; the small-n agreement of the formula with the definition; and the seeded renaming, which
must be a bijection that the seed alone decides.

With the real tools (EDP_TOOLS, a directory holding the cadical and cake_lpr a run built in results/build), also the
C = 1 boundary solved and verified. With the paper's source (at inputs/ or in EDP_INPUTS), also its sequence: 1,160
terms of discrepancy 2, a model of edp(2, 1160), and both of its extensions of discrepancy 3.

Run with: python3 -m unittest discover -s tests
"""

import gzip
import importlib.util
import itertools
import os
import random
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("edp_check", os.path.join(HERE, "..", "edp", "check.py"))
E = importlib.util.module_from_spec(_spec)
sys.modules["edp_check"] = E
_spec.loader.exec_module(E)

SEED = "a" * 64


def brute(x):
    """Discrepancy straight from the definition, every d and k."""
    n = len(x)
    return max((abs(sum(x[i * d - 1] for i in range(1, k + 1))) for d in range(1, n + 1) for k in range(1, n // d + 1)),
               default=0)


def fake_tex(signs="- + + - +\\\\\n+ - -\\\\", statements=E.STATEMENTS, appendix=E.APPENDIX):
    return ("\\begin{abstract} words \\end{abstract}\n" + "\n".join(f"\\begin{{proposition}}\n{s}\n\\end{{proposition}}"
                                                                       for s in statements)
            + f"\n\\appendix\n{appendix}\\label{{sec:sequence}}\nWe give ...\n\\noindent{{}}\\tt \n{signs}\n"
            "\\end{document}\n")


class Reading(unittest.TestCase):
    def test_the_sequence_and_statements(self):
        self.assertEqual(E.paper(fake_tex()), [-1, 1, 1, -1, 1, 1, -1, -1])
        spaced = fake_tex(statements=("There exists a sequence  of length $1160$\nof discrepancy $2$.",
                                      "No sequence of length $1161$ has discrepancy $2$."))
        self.assertEqual(len(E.paper(spaced)), 8)

    def test_anything_else_is_refused(self):
        bad = [
            fake_tex(signs="- + + 0 +"),                                     # a stray character
            fake_tex(signs="- + $x$ +"),
            fake_tex(statements=(E.STATEMENTS[0],)),                         # a statement missing
            fake_tex(statements=(E.STATEMENTS[0], "No sequence of length $1162$ has discrepancy $2$.")),
            fake_tex(appendix=E.APPENDIX.replace("1160", "1159")),
            fake_tex() + E.APPENDIX,                                         # the appendix twice
            fake_tex().replace("\\tt", "\\sf"),
        ]
        for tex in bad:
            with self.subTest(tex=tex[-80:]), self.assertRaises(E.Refused):
                E.paper(tex)


class Discrepancy(unittest.TestCase):
    def test_against_the_definition(self):
        rng = random.Random(7)
        for n in list(range(0, 13)) + [30, 61]:
            for _ in range(20):
                x = [rng.choice((1, -1)) for _ in range(n)]
                self.assertEqual(E.discrepancy(x), brute(x))

    def test_c1_boundary_by_enumeration(self):
        self.assertTrue(any(brute(x) <= 1 for x in itertools.product((1, -1), repeat=11)))
        self.assertFalse(any(brute(x) <= 1 for x in itertools.product((1, -1), repeat=12)))


class Encoding(unittest.TestCase):
    def test_example_4_clause_for_clause(self):
        clauses, var = E.cbound([1, 2, 3, 4, 5], 2, iter(range(6, 100)).__next__)
        name = {v: f"s{k}{j}" for (k, j), v in var.items()}
        got = {frozenset(("-" if l < 0 else "") + (name.get(abs(l)) or f"p{abs(l)}") for l in c) for c in clauses}
        # (13)-(16) of the journal version; its (14) prints (s23 v p5) where its own rules give (s24 v p5)
        printed = ["-s22 s11", "-s34 s23", "-s23 s22 s12", "-s35 s34 s24",
                   "-s11 p1", "-s12 s11 p2", "s12 p3", "-s22 p2", "-s23 s22 p3", "-s24 s23 p4", "s24 p5", "-s34 p4",
                   "-s35 s34 p5",
                   "-s11 s12", "-s22 s23", "-s34 s35", "-s23 s24",
                   "-p1 s11", "-p2 s12", "-s11 -p2 s22", "-s12 -p3 s23", "-p4 s24", "-s22 -p3", "-s23 -p4 s34",
                   "-s24 -p5 s35", "-s34 -p5"]
        self.assertEqual(len(clauses), 26)
        self.assertEqual(got, {frozenset(c.split()) for c in printed})
        self.assertEqual(sorted(var), [(1, 1), (1, 2), (2, 2), (2, 3), (2, 4), (3, 4), (3, 5)])

    def test_the_printed_sizes(self):
        for n, size in E.PRINTED.items():
            nv, clauses, _ = E.edp(2, n)
            self.assertEqual((nv, len(clauses)), size)

    def test_proposition_6_shortens_the_free_ends(self):
        got = dict((d, len(t)) for d, t in E.progressions(2, 12))
        self.assertEqual(got, {1: 11, 2: 5, 3: 3, 4: 3})        # 12, 6 and 4 terms lose their last; 3 keep theirs
        got = dict((d, len(t)) for d, t in E.progressions(1, 12))
        self.assertEqual(got, {1: 12, 2: 6, 3: 4, 4: 2, 5: 2, 6: 2})   # C odd: an odd count loses its last
        self.assertEqual(dict((d, len(t)) for d, t in E.progressions(1, 9)), {1: 8, 2: 4, 3: 2, 4: 2})

    def test_a_bounded_sequence_extends_to_a_model_and_an_unbounded_one_does_not(self):
        rng = random.Random(3)
        seen = {True: 0, False: 0}
        for _ in range(300):
            n = rng.randint(3, 40)
            x = [rng.choice((1, -1)) for _ in range(n)]
            nv, clauses, counters = E.edp(2, n)
            ok = E.unsatisfied(E.extend(x, counters), clauses) == 0
            self.assertEqual(ok, E.discrepancy(x) <= 2)
            seen[ok] += 1
        self.assertTrue(seen[True] and seen[False])

    def test_short_sequences_agree_with_the_definition(self):
        total, wrong, rows = E.exhaustive(9)
        self.assertEqual(total, 2 * (2 ** 10 - 2))
        self.assertEqual(wrong, 0)

    def test_a_wrong_formula_is_caught(self):
        good = E.edp
        try:                                   # drop one clause: some sequence must now be wrongly accepted
            E.edp = lambda C, n: (lambda r: (r[0], r[1][1:], r[2]))(good(C, n))
            self.assertGreater(E.exhaustive(9)[1], 0)
        finally:
            E.edp = good

    def test_consistent(self):
        self.assertTrue(E.consistent([(1, 2), (-1, 2)], []))
        self.assertFalse(E.consistent([(1, 2), (-1, 2)], [-2]))
        self.assertFalse(E.consistent([(1, 2), (-1, 2), (1, -2), (-1, -2)], []))   # needs search, not propagation


class Shuffle(unittest.TestCase):
    def test_the_seed_alone_decides_and_nothing_is_lost(self):
        nv, clauses, _ = E.edp(2, 60)
        clauses = clauses + [(60,)]
        a, old_a = E.renamed(nv, clauses, SEED)
        self.assertEqual(E.renamed(nv, clauses, SEED), (a, old_a))
        b, _ = E.renamed(nv, clauses, "b" * 64)
        self.assertNotEqual(a, b)
        self.assertEqual(sorted(old_a), list(range(1, nv + 1)))
        self.assertEqual(sorted(old_a.values()), list(range(1, nv + 1)))
        back = sorted(tuple(sorted(old_a[abs(l)] if l > 0 else -old_a[abs(l)] for l in c)) for c in a)
        self.assertEqual(back, sorted(tuple(sorted(c)) for c in clauses))


def tools_dir():
    d = os.environ.get("EDP_TOOLS")
    return d if d and all(os.path.isfile(os.path.join(d, t)) for t in ("cadical", "cake_lpr")) else None


@unittest.skipUnless(tools_dir(), "the built tools are not in EDP_TOOLS")
class Tools(unittest.TestCase):
    def test_c1_boundary(self):
        tools = {"cadical": os.path.join(tools_dir(), "cadical"), "cake_lpr": os.path.join(tools_dir(), "cake_lpr")}
        with tempfile.TemporaryDirectory() as work:
            out = {}
            for n in (11, 12):
                nv, clauses, _ = E.edp(1, n)
                path = os.path.join(work, f"c1-{n}.cnf")
                with open(path, "wb") as f:
                    f.write(E.dimacs(nv, clauses))
                out[n] = E.solve(tools, path, work, f"c1-{n}", lambda s: None)
            self.assertEqual(out[11]["answer"], "sat")
            m = E.H.model(out[11]["model"])
            self.assertEqual(E.discrepancy([1 if i in m else -1 for i in range(1, 12)]), 1)
            self.assertEqual(out[12]["answer"], "unsat")
            self.assertTrue(out[12]["verified"])


def inputs_dir():
    d = os.environ.get("EDP_INPUTS") or os.path.join(HERE, "..", "inputs")
    return d if os.path.isfile(os.path.join(d, E.INPUTS[0][0])) else None


@unittest.skipUnless(inputs_dir(), "the paper's source is not at inputs/ (or EDP_INPUTS)")
class ThePaper(unittest.TestCase):
    def test_its_sequence(self):
        x = E.paper(gzip.decompress(E.load(inputs_dir(), E.INPUTS[0][0])).decode("utf-8"))
        self.assertEqual(len(x), 1160)
        self.assertEqual(E.discrepancy(x), 2)
        self.assertEqual((E.discrepancy(x + [1]), E.discrepancy(x + [-1])), (3, 3))
        nv, clauses, counters = E.edp(2, 1160)
        y = x if x[E.FIXED - 1] > 0 else [-v for v in x]
        self.assertEqual(E.unsatisfied(E.extend(y, counters), clauses + [(E.FIXED,)]), 0)

    def test_a_changed_input_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, E.INPUTS[0][0]), "wb") as f:
                f.write(b"\x1f\x8b" + b"x" * (E.INPUTS[0][2] - 2))
            with self.assertRaises(E.Refused):
                E.load(d, E.INPUTS[0][0])


if __name__ == "__main__":
    unittest.main()
