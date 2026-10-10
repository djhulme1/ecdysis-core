"""Brent's equivalence check: the two iterations agree at low precision, the comparison and Table 6's rounding rule
fail where they should, the source check refuses an altered paper, and each control fails on its own; with the real
e-print (at inputs/ or in BRENT_INPUTS), also every string and number the check reads, and a run at 3,000 digits.

Run with: python3 -m unittest discover -s tests
"""

import gzip
import importlib.util
import io
import os
import tarfile
import tempfile
import unittest
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pi_brent", os.path.join(HERE, "..", "pi", "brent.py"))
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)

INPUTS = os.environ.get("BRENT_INPUTS", os.path.join(HERE, "..", "inputs"))
HAVE = os.path.exists(os.path.join(INPUTS, B.INPUT[0]))


def fake_tex():
    """A source holding exactly what the check relies on, in the paper's spelling."""
    lines = list(B.VERBATIM)
    lines += [f"{n} &\\;\\; ${m}\\text{{e{e}}}$\\\\" for n, m, e in B.TABLE6]
    lines += [f"{n} & \\, {err} & \\, {ratio} \\\\" for n, err, ratio in B.TABLE5]
    lines += [r"\begin{align*}",
              r"P(x) :=& 1 - 1635840576 x - 343853312 x^2 + 60576043008 x^3\\[-5pt]",
              r"& \;\; + 1865242664960 x^4 - 16779556159488 x^5 + 37529045696512 x^6\\[-5pt]",
              r"& \;\;\;\; - 29726424956928 x^7 + 6181548457984 x^8.",
              r"\end{align*}"]
    return "\n".join(lines)


class Iterations(unittest.TestCase):
    def test_the_two_agree_to_the_working_precision(self):
        rows, quartic = B.compared(300, 3)
        self.assertTrue(B.passes(rows, 300), rows)
        self.assertTrue(all(a >= 290 for _, a in rows), rows)
        self.assertEqual(len(quartic), 4)

    def test_pi_0_is_three_halves_plus_root_two(self):
        quartic = B.bb4(100, 0)
        with B.context(100):
            self.assertLess(abs(quartic[0] - (D(3) / 2 + D(2).sqrt())), D("1e-98"))

    def test_gl1_lower_approximations_rise_towards_pi(self):
        lows = B.gl1(200, 5)
        self.assertEqual(str(lows[0])[:12], "2.9142135623")
        self.assertTrue(all(x < y for x, y in zip(lows, lows[1:])))
        self.assertEqual(str(lows[3])[:22], "3.14159265358979323827")

    def test_a_perturbed_start_and_a_misaligned_index_fail(self):
        pert, _ = B.compared(300, 3, y0_shift=D("1e-30"))
        self.assertFalse(B.passes(pert, 300))
        shifted, _ = B.compared(300, 3, step=1)
        self.assertFalse(B.passes(shifted, 300))

    def test_the_bound_is_gap_digits_above_the_precision(self):
        self.assertTrue(B.passes([(D("1e-180000"), 180000)], 180_200))
        self.assertFalse(B.passes([(D("1.0000001e-180000"), 179999)], 180_200))
        self.assertTrue(B.passes([(D(0), 180_200)], 180_200))

    def test_agreement_digits(self):
        self.assertEqual(B.agreement(D(0), 500), 500)
        self.assertEqual(B.agreement(D("2.5e-40"), 500), 39)
        self.assertEqual(B.agreement(D("1e-40"), 500), 40)


class Table6(unittest.TestCase):
    def test_rounding_not_truncation(self):
        pi = D("3." + "1" * 800)              # any number will do; 800 digits hold Table 6's smallest value
        # pi - pi_0 = 1e-1 * 2.27...8157 (the 51st digit 7 rounds the 50th up to 6): matched by rounding only.
        err = D("2.27379091216698189660954659069804805627497523998157e-1")
        with B.context(800):
            vals = [pi - err] + [pi - D(f"{m}e{e}") for _, m, e in B.TABLE6[1:]]
        rows = B.table6(vals, pi, 800)
        self.assertTrue(rows[0]["matched"])
        self.assertFalse(rows[0]["truncation_matches"])
        self.assertTrue(all(r["matched"] for r in rows))

    def test_one_digit_off_fails(self):
        pi = D("3." + "1" * 800)
        with B.context(800):
            vals = [pi - D(f"{m}e{e}") for _, m, e in B.TABLE6]
            vals[2] = pi - D(B.TABLE6[2][1][:-1] + "9e" + B.TABLE6[2][2])
        rows = B.table6(vals, pi, 800)
        self.assertEqual([r["matched"] for r in rows], [True, True, False, True, True])


class Source(unittest.TestCase):
    def blob(self, tex):
        raw = tex.encode("utf-8")
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            info = tarfile.TarInfo(B.TEX)
            info.size = len(raw)
            tar.addfile(info, io.BytesIO(raw))
        return buf.getvalue()

    def test_a_faithful_source_passes_and_the_polynomial_parses(self):
        tex = fake_tex()
        self.assertEqual(B.poly_of(tex), B.POLY)
        self.assertEqual(B.verbatim(tex), len(B.VERBATIM) + len(B.TABLE6) + len(B.TABLE5) + 1)

    def test_an_altered_source_is_refused(self):
        tex = fake_tex()
        for old, new in ((B.TABLE6[1][1], B.TABLE6[1][1][:-1] + "5"), ("2^{2n+3}", "2^{2n+2}"),
                         ("0.9900528160", "0.9900528161"), ("6181548457984 x^8", "6181548457985 x^8"),
                         (r"s_{n+1} := s_n - 2^n\,c_{n+1}^2", r"s_{n+1} := s_n - 2^{n+1}\,c_{n+1}^2")):
            with self.subTest(old=old), self.assertRaises(B.Refused):
                B.verbatim(tex.replace(old, new, 1))

    def test_the_input_is_checked_by_hash(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, B.INPUT[0]), "wb") as fh:
                fh.write(self.blob(fake_tex()))
            with self.assertRaises(B.Refused):
                B.load(d)


class Controls(unittest.TestCase):
    def test_the_polynomial_vanishes_at_pi_1_and_not_at_pi(self):
        pi, _ = B.agm.chudnovsky(B.CONTROL_PREC + 20)
        ok, at = B.polynomial(pi)
        self.assertTrue(ok, at)
        self.assertGreater(abs(D(at["pi"])), 1)

    def test_a_wrong_coefficient_does_not_vanish(self):
        pi, _ = B.agm.chudnovsky(B.CONTROL_PREC + 20)
        saved = B.POLY
        try:
            B.POLY = saved[:-1] + (saved[-1] + 1,)
            ok, at = B.polynomial(pi)
            self.assertFalse(ok, at)
        finally:
            B.POLY = saved

    def test_table5_and_the_bound_at_moderate_precision(self):
        pi, _ = B.agm.chudnovsky(1500)
        quartic = B.bb4(1500, 4)
        rows, bounds = B.table5(quartic, pi, 1500)
        self.assertEqual(len(rows), 10)
        self.assertTrue(all(r["within"] for r in rows), rows)
        self.assertEqual(sum(r["matched"] for r in rows), 8)   # the n = 2 row reads as truncated, twice
        self.assertTrue(all(b["held"] for b in bounds), bounds)


@unittest.skipUnless(HAVE, "the e-print is not at inputs/ or BRENT_INPUTS")
class EPrint(unittest.TestCase):
    """What the check reads, on the paper's own source, and a run at 3,000 digits."""

    def test_every_string_and_number_is_in_the_source(self):
        tex = B.load(INPUTS)
        self.assertEqual(B.poly_of(tex), B.POLY)
        self.assertEqual(B.verbatim(tex), 14 + 5 + 9 + 1)

    def test_a_run_at_3000_digits(self):
        with tempfile.TemporaryDirectory() as d:
            out, detail = B.run(INPUTS, d, precision=3000, n_max=5)
        self.assertEqual(out["test_passed"], 1, out)
        self.assertEqual(out["table6_matched"], 5)
        self.assertEqual(out["correct_digits"], "0,8,40,170,693,2789")
        self.assertEqual(out["controls_passed"], out["controls_total"], detail["controls"])


if __name__ == "__main__":
    unittest.main()
