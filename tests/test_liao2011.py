"""Liao et al.'s fat maintenance (itp/liao2011.py): the reader and its refusals, the strains of rule 2, the difference
scores and their correlation in floating point and in exact arithmetic, and the whole assessment, on panels of mice
made here. The deposit's fat masses and lifespans are never read.

Run with: python3 -m unittest tests.test_liao2011 (in the pinned scipy-notebook image)
"""

import importlib.util
import os
import random
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("itp_liao2011", os.path.join(HERE, "..", "itp", "liao2011.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


def row(strain, sex, i, diet, days, comp=None):
    """A CSV row: comp is (bw, lean, fat, pct_fat) as strings, in the diet's columns, or None."""
    blank = [""] * 8
    if comp is not None:
        bw, lean, fat, pct = comp
        cols = {"AL": [bw, "", lean, "", fat, "", pct, ""], "DR": ["", bw, "", lean, "", fat, "", pct]}[diet]
    else:
        cols = blank
    life = [str(days), ""] if diet == "AL" else ["", str(days)]
    return ",".join([strain, sex, f"id{i}"] + cols + life)


def csv_bytes(rows, header=None):
    return ("\n".join([",".join(header or M.HEADER)] + rows) + "\n").encode()


def panel(seed, n=12, slope=None, measured=3, per_group=5):
    """n strains, per_group mice per sex and diet, the first `measured` of each group with body composition.
    slope: if given, each strain's DR fat is set so that its fat reduction is slope times its lifespan extension."""
    rng = random.Random(seed)
    rows, i = [], 0
    for k in range(n):
        base, shift = rng.randint(600, 1000), rng.randint(-200, 200)
        for sex in ("m", "f"):
            al_days = [max(60, int(rng.gauss(base, 60))) for _ in range(per_group)]
            dr_days = [max(60, int(rng.gauss(base + shift, 60))) for _ in range(per_group)]
            ext = sum(dr_days) / per_group - sum(al_days) / per_group
            al_fat = [round(rng.uniform(3, 12), 2) for _ in range(measured)]
            mean_al = sum(al_fat) / measured
            if slope is None:
                dr_fat = [round(rng.uniform(1, 9), 2) for _ in range(measured)]
            else:
                target = mean_al - slope * ext
                dr_fat = [round(target + 0.05 * (j - (measured - 1) / 2), 2) for j in range(measured)]
            for j, d in enumerate(al_days):
                comp = (f"{25 + k + j}.0", f"{17 + 0.3 * k + 0.1 * j:.1f}", f"{al_fat[j]:.2f}",
                        f"{3 * al_fat[j]:.1f}") if j < measured else None
                rows.append(row(f"S{k}", sex, i, "AL", d, comp))
                i += 1
            for j, d in enumerate(dr_days):
                comp = (f"{20 + 0.5 * k + j:.1f}", f"{14 + 0.2 * k + 0.1 * j + 0.05 * (k % 3):.2f}",
                        f"{max(0.01, dr_fat[j]):.2f}", f"{3 * max(0.01, dr_fat[j]):.1f}") if j < measured else None
                rows.append(row(f"S{k}", sex, i, "DR", d, comp))
                i += 1
    return rows


class Reading(unittest.TestCase):
    def test_reads_a_panel(self):
        mice = M.read_mice(csv_bytes(panel(1, n=3)))
        self.assertEqual(len(mice), 3 * 2 * 2 * 5)
        with_comp = [m for m in mice if m["comp"] is not None]
        self.assertEqual(len(with_comp), 3 * 2 * 2 * 3)
        self.assertEqual(set(with_comp[0]["comp"]), set(M.COMPOSITION))

    def test_refusals(self):
        good = row("S0", "m", 0, "AL", 800, ("25.0", "18.5", "4.11", "20.0"))
        M.read_mice(csv_bytes([good]))
        bad_cases = [
            row("S0", "m", 0, "AL", 800, ("25.0", "18.5", "", "20.0")),               # composition partly given
            row("S0", "x", 0, "AL", 800),                                             # sex
            "S0,m,id0,,25.0,,18.5,,4.11,,20.0,800,",                                  # AL lifespan, DR columns
            "S0,m,id0,,,,,,,,,800,900",                                               # both lifespans
            "S0,m,id0,,,,,,,,,,",                                                     # no lifespan
            row("S0", "m", 0, "AL", 800, ("25.0", "18.5", "0", "20.0")),              # not positive
            row("S0", "m", 0, "AL", 800, ("25.0", "18.5", "4.1x", "20.0")),           # not a decimal
            "S0,m,id0,,,,,,,,,80.5,",                                                 # lifespan not whole days
        ]
        for bad in bad_cases:
            with self.assertRaises(M.Refused, msg=bad):
                M.read_mice(csv_bytes([bad]))
        with self.assertRaises(M.Refused):
            M.read_mice(csv_bytes([good], header=M.HEADER[:-1] + ["other"]))

    def test_input_hash(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, M.INPUT[0]), "wb") as fh:
                fh.write(b"strain\n")
            with self.assertRaises(M.Refused):
                M.read_input(d)


class Scores(unittest.TestCase):
    def test_strains_need_fat_in_both_diets(self):
        rows = panel(2, n=4)
        # strain S3's DR mice lose their body composition: it drops out of rule 2 in both sexes
        rows = [r if not (r.startswith("S3,") and ",id" in r and r.split(",")[11] == "") else
                ",".join(r.split(",")[:3] + [""] * 8 + r.split(",")[11:]) for r in rows]
        c = M.cells(M.read_mice(csv_bytes(rows)))
        self.assertEqual(M.strains_of(c, "m"), ["S0", "S1", "S2"])
        self.assertEqual(M.strains_of(c, "f", need=("AL",)), ["S0", "S1", "S2", "S3"])

    def test_difference_scores(self):
        rows = [row("A", "m", 0, "AL", 800, ("25.0", "18.0", "6.00", "24.0")),
                row("A", "m", 1, "AL", 900, ("25.0", "18.0", "8.00", "32.0")),
                row("A", "m", 2, "AL", 1000),
                row("A", "m", 3, "DR", 1100, ("20.0", "15.0", "3.00", "15.0")),
                row("A", "m", 4, "DR", 1300)]
        c = M.cells(M.read_mice(csv_bytes(rows)))
        red, ext = M.scores(c, "m", ["A"])
        self.assertAlmostEqual(red[0], 7.0 - 3.0)                 # mean AL fat minus mean DR fat
        self.assertAlmostEqual(ext[0], 1200.0 - 900.0)            # all DR mice minus all AL mice
        red, ext = M.scores(c, "m", ["A"], days_key="days_measured")
        self.assertAlmostEqual(ext[0], 1100.0 - 850.0)            # only the mice with a fat mass
        red, _ = M.scores(c, "m", ["A"], relative=True)
        self.assertAlmostEqual(red[0], 4.0 / 7.0)

    def test_correlation_signs_and_exact(self):
        for slope, sign in ((-0.01, -1), (0.01, 1)):
            c = M.cells(M.read_mice(csv_bytes(panel(3, n=10, slope=slope))))
            st = M.strains_of(c, "m")
            red, ext = M.scores(c, "m", st)
            r, p = M.L.scipy_pearson(red, ext)
            self.assertEqual(r > 0, sign > 0)
            self.assertGreater(abs(r), 0.99)
            s, r2, rx = M.exact_r(c, "m", st)
            self.assertEqual(s, sign)
            self.assertLess(abs(rx - r), 1e-12)


class Assess(unittest.TestCase):
    def test_assess_on_a_panel(self):
        mice = M.read_mice(csv_bytes(panel(4, n=14, slope=-0.01)))
        out, detail = M.assess(mice, counts=None)
        self.assertEqual(out["strains_m"], 14)
        self.assertEqual(out["test_passed"], 1)
        self.assertLess(out["r_m"], -0.99)
        for k in M.OUTPUTS:
            self.assertIn(k, out)
        # controls (a), (b) and (d) hold on any panel; (c) describes the deposit, not this panel
        ctl = detail["controls"]
        self.assertEqual(sum(ctl.values()), 3)

    def test_counts_refused(self):
        mice = M.read_mice(csv_bytes(panel(5, n=6)))
        with self.assertRaises(M.Refused):
            M.assess(mice)                                       # the paper's 38 and 33 strains are not here

    def test_unrelated_panel_fails(self):
        mice = M.read_mice(csv_bytes(panel(6, n=14, slope=0.01)))
        out, _ = M.assess(mice, counts=None)
        self.assertEqual(out["test_passed"], 0)


if __name__ == "__main__":
    unittest.main()
