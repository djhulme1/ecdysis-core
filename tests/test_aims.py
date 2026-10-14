"""The AIMS recount (folk/aims.py): the e-print reader and its refusals on archives built here; the codebook check;
the share, agreement, index, comparison and timeline rules on frames whose answers are known by hand; the controls;
the bootstrap's seeding; and the verdict end to end on a synthetic e-print, with and without a failing condition.
The paper's data are not read here, and no number from them is computed.

Run with: python3 -m unittest discover -s tests -p test_aims.py
"""

import hashlib
import importlib.util
import io
import math
import os
import tarfile
import tempfile
import unittest

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("folk_aims", os.path.join(HERE, "..", "folk", "aims.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "ab" * 32


def codebook_csv(**override):
    rows = [("Variable", "Variable description")]
    words = dict(M.WORDING)
    words.update(override)
    rows += list(words.items())
    rows += [(c, f"Moral concern: item {c} (scale 1-5)") for c in M.MCE_TARGET]
    buf = io.StringIO()
    pd.DataFrame(rows[1:], columns=rows[0]).to_csv(buf, index=False)
    return ("﻿" + buf.getvalue()).encode("utf-8")


def wave(n, yes, agree, opinion, mp, mc, rng, weight=None):
    """A wave of n rows: `yes` answer Yes to F1 (the rest split No, Not sure); `agree` of `opinion` rows with an opinion
    agree with PMC9 (the rest code 4); MP items about `mp`, MCE21 to MCE31 about `mc`."""
    f1 = ["Yes"] * yes + ["No", "Not sure"] * ((n - yes) // 2) + ["No"] * ((n - yes) % 2)
    pmc9 = [6] * agree + [2] * (opinion - agree) + [4] * (n - opinion)
    d = {"F1": f1, "F2": [0, 5, -1, 2030] * (n // 4), "PMC9": pmc9}
    for c in M.PMC + M.MCE_GENERAL:
        if c != "PMC9":
            d[c] = list(rng.integers(1, 8, n))
    for c in M.MP:
        d[c] = list(np.clip(np.round(mp + rng.normal(0, 5, n)), 0, 100))
    for c in M.MCE_TARGET:
        d[c] = list(np.clip(mc + rng.normal(0, 0.2, n), 1, 5))
    for c in M.ANTH:
        d[c] = list(rng.integers(0, 11, n))
    d["weight"] = list(weight if weight is not None else np.ones(n))
    return pd.DataFrame(d)


def eprint(frames, codebook=None, drop=None):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        files = {M.MEMBERS["2021"]: frames[0].to_csv(index=False).encode(),
                 M.MEMBERS["2023"]: frames[1].to_csv(index=False).encode(),
                 M.MEMBERS["codebook"]: codebook if codebook is not None else codebook_csv(),
                 M.MEMBERS["supplement"]: frames[1][["F1", "weight"]].to_csv(index=False).encode()}
        for name, raw in files.items():
            if name == drop:
                continue
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            tar.addfile(info, io.BytesIO(raw))
    return buf.getvalue()


def synthetic(rights=38, seed=1):
    rng = np.random.default_rng(seed)
    d21 = wave(200, 36, 37, 100, 30, 2.0, rng)
    d23 = wave(200, 40, rights, 100, 60, 3.0, rng)
    return d21, d23


class Reading(unittest.TestCase):
    def test_members(self):
        raw = eprint(synthetic())
        got = M.members(raw)
        self.assertEqual(set(got), set(M.MEMBERS))
        with self.assertRaises(M.Refused):
            M.members(eprint(synthetic(), drop=M.MEMBERS["2023"]))
        with self.assertRaises(M.Refused):
            M.members(b"not a tar at all")

    def test_hash_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, M.INPUT[0]), "wb") as fh:
                fh.write(eprint(synthetic()))
            with self.assertRaises(M.Refused):
                M.read_input(d)

    def test_frame_checks(self):
        d21, _ = synthetic()
        ok = M.frame(d21.to_csv(index=False).encode(), "t")
        self.assertEqual(len(ok), 200)
        for col, val in (("F1", "Maybe"), ("weight", 0), ("PMC9", 8), ("PMC9", 2.5), ("MP1", 101), ("MCE21", 0.5),
                         ("MP2", "lots")):
            bad = d21.copy()
            bad[col] = bad[col].astype(object)
            bad.loc[3, col] = val
            with self.assertRaises(M.Refused, msg=(col, val)):
                M.frame(bad.to_csv(index=False).encode(), "t")
        with self.assertRaises(M.Refused):
            M.frame(d21.drop(columns=["MCE31"]).to_csv(index=False).encode(), "t")
        loose = d21.copy()
        loose["Anth2"] = loose["Anth2"].astype(object)
        loose.loc[5, "Anth2"] = "unknown"                   # an untested column: read as missing, not refused
        got = M.frame(loose.to_csv(index=False).encode(), "t")
        self.assertTrue(pd.isna(got.loc[5, "Anth2"]))

    def test_codebook(self):
        M.codebook(codebook_csv())
        with self.assertRaises(M.Refused):
            M.codebook(codebook_csv(F1="Do you think robots are sentient?"))
        with self.assertRaises(M.Refused):
            M.codebook(codebook_csv(PMC9="I support granting legal rights to robots/AIs."))


class Rules(unittest.TestCase):
    def test_share_and_agreement(self):
        f = pd.DataFrame({"F1": ["Yes", "No", "Not sure", "Yes", "No"], "PMC9": [7, 4, 3, 5, 4],
                          "weight": [1.0, 2.0, 3.0, 4.0, 10.0]})
        s = M.share_yes(f)
        self.assertAlmostEqual(s["Yes"], 5 / 20)
        self.assertAlmostEqual(s["No"], 12 / 20)
        self.assertAlmostEqual(M.agreement(f, "PMC9"), 5 / 8)          # 4 left out: (1 + 4) / (1 + 3 + 4)

    def test_combined_and_compare(self):
        d21, d23 = synthetic()
        d21.loc[0, M.MP] = np.nan                                       # no MP item: left out of that index
        d21.loc[1, "MP1"] = np.nan                                      # one missing: the mean of the other three
        d = M.combined(d21, d23)
        self.assertTrue(pd.isna(d.loc[0, "Mind Perception"]))
        self.assertAlmostEqual(d.loc[1, "Mind Perception"], float(np.mean(d21.loc[1, ["MP2", "MP3", "MP4"]])))
        self.assertEqual(d["F1"].dtype, bool)
        r = M.compare(d, "Mind Perception")
        self.assertEqual((r["n2021"], r["n2023"]), (199, 200))
        x1 = d.loc[(d.year == "2021") & d["Mind Perception"].notna(), "Mind Perception"].to_numpy()
        x2 = d.loc[d.year == "2023", "Mind Perception"].to_numpy()
        n1, n2 = len(x1), len(x2)
        sp = (np.sum((x1 - x1.mean()) ** 2) + np.sum((x2 - x2.mean()) ** 2)) / (n1 + n2 - 2)
        t = (x1.mean() - x2.mean()) / math.sqrt(sp * (1 / n1 + 1 / n2))
        self.assertAlmostEqual(r["t"], t, places=9)                    # unit weights: the textbook pooled test
        self.assertGreater(r["m2023"], r["m2021"])

    def test_timelines(self):
        f21 = pd.DataFrame({"F2": [0, -1, np.nan, 5], "weight": [1.0, 1.0, 1.0, 1.0]})
        f23 = pd.DataFrame({"F2": [0, 2023, -1, 2030, np.nan, 3, 4, 5], "weight": [2.0, 1, 1, 1, 1, 1, 1, 1]})
        tl = M.timelines(f21, f23)
        self.assertAlmostEqual(tl["2021"]["already"], 0.25)
        self.assertAlmostEqual(tl["2021"]["never"], 0.5)               # -1 and empty
        self.assertAlmostEqual(tl["2023"]["already"], 3 / 9)           # 0, and 2023 read as 0 years from 2023
        self.assertAlmostEqual(tl["2023"]["never"], 2 / 9)
        self.assertTrue(0 <= tl["p_already"] <= 1 and 0 <= tl["p_never"] <= 1)

    def test_controls(self):
        self.assertTrue(all(M.controls_known().values()))

    def test_bootstrap_seeded(self):
        d = M.combined(*synthetic())
        a, b = M.bootstrap(SEED, d, n=50), M.bootstrap(SEED, d, n=50)
        self.assertEqual(a, b)
        c = M.bootstrap("cd" * 32, d, n=50)
        self.assertNotEqual(a, c)
        for k in ("share", "rights", "mp_change", "mc_change"):
            self.assertLessEqual(a[k][0], a[k][1])


class Verdict(unittest.TestCase):
    def run_on(self, frames):
        raw = eprint(frames)
        saved = M.INPUT
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "inputs"))
            with open(os.path.join(d, "inputs", saved[0]), "wb") as fh:
                fh.write(raw)
            M.INPUT = (saved[0], hashlib.sha256(raw).hexdigest())
            try:
                out, detail = M.run(SEED, inputs=os.path.join(d, "inputs"), results=os.path.join(d, "results"))
            finally:
                M.INPUT = saved
        return out, detail

    def test_passes_when_all_hold(self):
        out, detail = self.run_on(synthetic())
        self.assertEqual(out["test_passed"], 1)
        self.assertEqual(out["conditions_met"], 3)
        self.assertAlmostEqual(out["sentient_now_2023"], 0.2)
        self.assertAlmostEqual(out["legal_rights_2023"], 0.38)
        self.assertEqual((out["period_from"], out["period_to"]), (20211101, 20230531))
        self.assertEqual(out["controls_passed"], out["controls_total"])
        self.assertEqual(list(out), list(M.OUTPUTS))
        for v in out.values():
            if isinstance(v, str):
                self.assertLessEqual(len(v), M.LIMIT)

    def test_fails_beside_each_window(self):
        out, _ = self.run_on(synthetic(rights=30))                     # 30% agree: outside 37% to 39%
        self.assertEqual(out["test_passed"], 0)
        self.assertEqual(out["conditions_met"], 2)
        rng = np.random.default_rng(3)
        d21 = wave(200, 36, 37, 100, 30, 3.0, rng)
        d23 = wave(200, 30, 38, 100, 60, 2.5, rng)                     # 15% yes; moral concern lower
        out, _ = self.run_on((d21, d23))
        self.assertEqual(out["conditions_met"], 1)

    def test_listed(self):
        printed = [("a", "1", "1")] + [(f"value number {i}, %", "2", "3") for i in range(12)]
        differs = [{"what": w, "computed": c, "printed": p} for w, c, p in printed[1:]]
        got = M.listed(["a"], printed, differs)
        self.assertLessEqual(len(got), M.LIMIT)
        self.assertTrue(got.startswith("1 of 13 as printed; not: value number 0, %; "))
        self.assertRegex(got, r"; and [0-9]+ more$")
        shown = got.split("; not: ")[1].rsplit("; and ", 1)[0].split("; ")
        self.assertTrue(all(x in [d["what"] for d in differs] for x in shown))   # whole names only
        self.assertEqual(M.listed(["a"], printed[:1], []), "1 of 1 as printed")

    def test_outputs_named(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 20)

    def test_seed_refused(self):
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


if __name__ == "__main__":
    unittest.main()
