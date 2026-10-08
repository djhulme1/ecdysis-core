"""The omniperiodicity check: the RLE reader and its refusals, Life on the unbounded plane, exact periods and full
cells (a trivial oscillator, a period that comes back sooner), the brace reader, a small Gallery, and, with the e-print
at inputs/ (or LIFE_INPUTS), the run up to p = 46.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("life_check", os.path.join(HERE, "..", "life", "check.py"))
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)

GLIDER = "bo$2bo$3o!"
PULSAR = "2b3o3b3o2$o4bobo4bo$o4bobo4bo$o4bobo4bo$2b3o3b3o2$2b3o3b3o$o4bobo4bo$o4bobo4bo$o4bobo4bo2$2b3o3b3o!"


class Reader(unittest.TestCase):
    def test_rle(self):
        self.assertEqual(L.rle(GLIDER), [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)])
        self.assertEqual(L.rle("o2$\n 2bo !"), [(0, 0), (2, 2)])
        for bad in ("bo$2bo$3o", "3o2!", "3x!", "0o!", "b!", "3o!x", "o$$-o!"):
            with self.subTest(text=bad), self.assertRaises(L.Refused):
                L.rle(bad)

    def test_groups(self):
        text = "{a{b}\\}c}{d}"
        self.assertEqual(L.group(text, 0), ("a{b}\\}c", 9))
        with self.assertRaises(L.Refused):
            L.group("{a{b}", 0)

    def test_a_small_gallery(self):
        tex = ("x\n\\section*{\\hfil Gallery \\hfil}\n"
               "\\patcols{(p2) Blinker}{\\href{https://conwaylife.com/?rle=3o!&name=(p2)}{\\includegraphics{p2}}}\n"
               "{\\detokenize{x = 3, y = 1, rule = B3/S23} \\\\\n\\detokenize{3o!}}\n\n"
               "\\patcols{(p3) Pulsar}{\\href{https://conwaylife.com/?rle=" + PULSAR + "&name=(p3)}{\\i{p3}}}\n"
               "{\\detokenize{x = 13, y = 12, rule = B3/S23\n" + PULSAR[:40] + "\n" + PULSAR[40:-6] + "2b2o!}}\n"
               "\\printbibliography\n")
        g = L.gallery(tex)
        self.assertEqual([(e["stated"], e["link_same"], e["header"] == e["size"]) for e in g],
                         [(2, True, True), (3, False, False)])
        with self.assertRaises(L.Refused):
            L.gallery(tex.replace("B3/S23} \\\\", "B36/S23} \\\\"))


class Life(unittest.TestCase):
    def test_still_blinker_glider(self):
        block = L.keys(L.rle("2o$2o!"))
        self.assertTrue(L.same(L.step(block), block))
        blinker = L.keys(L.rle("3o!"))
        self.assertEqual(L.cells(L.step(blinker)), [(-1, 1), (0, 1), (1, 1)])
        self.assertEqual(L.glider_direction(L.rle(GLIDER)), (1, 1))
        self.assertIsNone(L.glider_direction(L.rle("b2o$obo$bo!")))
        far = L.keys([(-5000, -7000), (-5000, -6999), (-5000, -6998)])
        self.assertTrue(L.same(L.run_for(far, 2), far))

    def test_periods_and_full_cells(self):
        r = L.oscillator(L.keys(L.rle("3o!")), 2)
        self.assertEqual((r["period"], r["full_cells"], r["ok"]), (2, 4, True))
        r = L.oscillator(L.keys(L.rle(PULSAR)), 3)
        self.assertEqual((r["period"], r["full_cells"], r["pop_min"], r["pop_max"], r["ok"]), (3, 64, 48, 72, True))
        self.assertFalse(L.oscillator(L.keys(L.rle("3o!")), 4)["ok"])
        both = L.keys(L.rle("3o!") + [(r + 20, c + 20) for r, c in L.rle(PULSAR)])
        r = L.oscillator(both, 6)
        self.assertEqual((r["period"], r["full_cells"], r["ok"]), (6, 0, False))
        t, _ = L.orbit(L.keys(L.rle(GLIDER)), 100, keep=False)
        self.assertIsNone(t)

    def test_prime_factors(self):
        self.assertEqual([L.prime_factors(n) for n in (1, 12, 41, 500)], [[], [2, 3], [41], [2, 5]])


def inputs_dir():
    d = os.environ.get("LIFE_INPUTS") or os.path.join(HERE, "..", "inputs")
    return d if os.path.isfile(os.path.join(d, L.INPUT[0])) else None


@unittest.skipUnless(inputs_dir(), "the e-print is not at inputs/ (or LIFE_INPUTS)")
class TheEprint(unittest.TestCase):
    def test_up_to_46(self):
        with tempfile.TemporaryDirectory() as d:
            out, detail = L.run(inputs=inputs_dir(), results=d, workers=1, last=46)
        self.assertEqual(out["test_passed"], 1)
        self.assertEqual((out["gallery_entries"], out["gallery_covered"], out["link_mismatches"],
                          out["header_mismatches"]), (42, 42, 0, 2))
        self.assertEqual((out["p19_period"], out["p41_period"], out["loop43_equal"]), (19, 41, 1))
        self.assertEqual((out["loops_checked"], out["loops_passed"], out["loops_8p"]), (4, 4, 4))
        self.assertEqual((out["controls_passed"], out["controls_total"]), (6, 6))
        self.assertEqual([x["full_cells"] for x in detail["loops"]], [608, 616, 624, 632])
        wrong = sorted(r["caption"] for r in detail["gallery"] if r["header"] != r["size"])
        self.assertEqual(wrong, ["(p30) queen bee shuttle", "(p35) toaster on 44P7.2"])


if __name__ == "__main__":
    unittest.main()
