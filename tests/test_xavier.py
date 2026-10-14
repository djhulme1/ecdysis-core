"""Xavier et al.'s metabolic RAFs (raf/xavier.py): the rules' grammar ("&" binding tighter than the whitespace that
separates alternatives, parentheses, the paper's stray spaces) and its refusals; equations with coefficients and two
ways; the maxRAF on small systems whose answer is known; the five food sets derived from Dataset S4's; the workbook and
S4 readers; the seed refused; and, with the paper's files at inputs/ (or XAVIER_INPUTS), the networks' counts, the
food sets and S4 against S1A (the same reactions and rules, 2,774 of them written in another direction), which
compute no maxRAF.

Run with: python3 -m unittest tests.test_xavier
"""

import importlib.util
import io
import os
import sys
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("raf_xavier", os.path.join(HERE, "..", "raf", "xavier.py"))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)
INPUTS = os.environ.get("XAVIER_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = all(os.path.isfile(os.path.join(INPUTS, name)) for name, _ in M.INPUTS.values())


def alts(*groups):
    return frozenset(frozenset(g.split()) for g in groups)


class Rules(unittest.TestCase):
    def test_grammar(self):
        cases = {
            "a": alts("a"),
            "a b": alts("a", "b"),
            "a&b": alts("a b"),
            "a b&c": alts("a", "b c"),                       # "&" binds tighter
            "a&b c": alts("a b", "c"),
            "(a b)&c": alts("a c", "b c"),
            "(Flavins Hemes C00038)&NADs": alts("Flavins NADs", "Hemes NADs", "C00038 NADs"),
            "a&(b (c&d))": alts("a b", "a c d"),
            " C19610&Flavins": alts("C19610 Flavins"),       # the paper's stray spaces
            "C14818&C19609  C14819&C19609": alts("C14818 C19609", "C14819 C19609"),
            "Ni-Fe-S_cluster": alts("Ni-Fe-S_cluster"),
        }
        for rule, want in cases.items():
            with self.subTest(rule=rule):
                self.assertEqual(M.parse_rule(rule, "t"), want)

    def test_refusals(self):
        for rule in ("", " ", "a&", "&a", "(a b", "a b)", "()", "a | b", "a,b", "a&&b", "a (b"):
            with self.subTest(rule=rule):
                with self.assertRaises(M.Refused):
                    M.parse_rule(rule, "t")


class Equations(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(M.parse_equation("C00043 + 2 C00003 + C00001 <=> C04573 + 2 C00004", "t"),
                         (frozenset(["C00043", "C00003", "C00001"]), frozenset(["C04573", "C00004"]), True))
        self.assertEqual(M.parse_equation("C05818 => Quinones", "t"), (frozenset(["C05818"]), frozenset(["Quinones"]),
                                                                       False))

    def test_refusals(self):
        for eq in ("A <= B", "A -> B", "A => ", "A + => B", "0 A => B", "2  A => B", "A + B C => D", None):
            with self.subTest(eq=eq):
                with self.assertRaises(M.Refused):
                    M.parse_equation(eq, "t")


class MaxRaf(unittest.TestCase):
    def test_the_small_system(self):
        net = M.toy()
        hs = M.halves(net)
        self.assertEqual(len(hs), 7)                             # r3 is two-way
        alive, W = M.max_raf(M.TOY_FOOD, hs)
        self.assertEqual(M.reactions_of(alive, hs, net), M.TOY_MAXRAF)
        self.assertEqual(W - M.TOY_FOOD, M.TOY_MAKES)
        self.assertTrue(M.is_raf(M.TOY_FOOD, hs, alive))
        self.assertFalse(M.is_raf(M.TOY_FOOD, hs, set(range(len(hs)))))

    def test_no_raf_and_food_catalysis(self):
        net = [(n,) + M.parse_equation(eq, n) + (M.parse_rule(r, n),) for n, eq, r in
               (("s1", "a => b", "c"), ("s2", "b => c", "d"))]          # c needs s1, s1 needs c: but d never comes
        alive, W = M.max_raf(frozenset("a"), M.halves(net))
        self.assertEqual(alive, set())
        self.assertEqual(W, {"a"})
        alive, _ = M.max_raf(frozenset("ad"), M.halves(net))           # with d as food both are in
        self.assertEqual(M.reactions_of(alive, M.halves(net), net), ["s1", "s2"])

    def test_pooling_is_not_counted(self):
        net = [(n,) + M.parse_equation(eq, n) + (M.parse_rule(r, n),) for n, eq, r in
               (("R_X_1", "c => X", "Pooling"), ("t1", "a => b", "X"))]
        alive, _ = M.max_raf(frozenset(["a", "c", "Pooling"]), M.halves(net))
        self.assertEqual(M.reactions_of(alive, M.halves(net), net), ["t1"])
        self.assertEqual(len(alive), 2)

    def test_closure_ignores_catalysis(self):
        net = [(n,) + M.parse_equation(eq, n) + (M.parse_rule(r, n),) for n, eq, r in (("u", "a + b => c", "zz"),)]
        hs = M.halves(net)
        self.assertEqual(M.closure(frozenset("ab"), hs, {0}), {"a", "b", "c"})
        self.assertEqual(M.closure(frozenset("a"), hs, {0}), {"a"})


def s4_food_list():
    filler = [f"F{i}" for i in range(39 - 2)]
    return ["Pooling", "Spontaneous"] + filler[:20] + list(M.ABIOTIC) + filler[20:] + list(M.ORGANIC)


class FoodSets(unittest.TestCase):
    def test_sizes(self):
        F = M.food_sets(s4_food_list())
        self.assertEqual({k: len(v) for k, v in F.items()}, {k: v[0] for k, v in M.TABLE_S1.items()})
        self.assertTrue(F["FS1"] < F["FS2"] < F["FS3"] < F["FS4"])
        self.assertTrue(F["FS2"] < F["FS5"])
        self.assertFalse(any(a in F["FS3"] for a in M.AMINO))
        self.assertIn(M.PEPTIDE, F["FS4"])

    def test_refusals(self):
        short = [m for m in s4_food_list() if m != "C00020"]           # AMP missing
        with self.assertRaises(M.Refused):
            M.food_sets(short)
        with self.assertRaises(M.Refused):
            M.food_sets([m for m in s4_food_list() if m != "Spontaneous"] + ["F99"])


def workbook(sheets):
    """A minimal xlsx with shared strings: sheets is [(name, [[cell, ...], ...])]."""
    strings, index = [], {}

    def sid(s):
        if s not in index:
            index[s] = len(strings)
            strings.append(s)
        return index[s]
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        rels, entries = [], []
        for k, (name, rows) in enumerate(sheets, start=1):
            xml = []
            for i, row in enumerate(rows, start=1):
                cells = "".join(f'<c r="{chr(65 + j)}{i}" t="s"><v>{sid(v)}</v></c>' for j, v in enumerate(row) if v)
                xml.append(f'<row r="{i}">{cells}</row>')
            z.writestr(f"xl/worksheets/sheet{k}.xml", '<worksheet xmlns="http://schemas.openxmlformats.org/'
                       f'spreadsheetml/2006/main"><sheetData>{"".join(xml)}</sheetData></worksheet>')
            rels.append(f'<Relationship Id="rId{k}" Target="worksheets/sheet{k}.xml" Type="x"/>')
            entries.append(f'<sheet name="{name.replace("&", "&amp;")}" sheetId="{k}" r:id="rId{k}"/>')
        z.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                   + "".join(entries) + "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
                   '2006/relationships">' + "".join(rels) + "</Relationships>")
        z.writestr("xl/sharedStrings.xml", '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                   + "".join(f"<si><t>{s.replace('&', '&amp;')}</t></si>" for s in strings) + "</sst>")
    return out.getvalue()


class Readers(unittest.TestCase):
    def test_sheets_by_name(self):
        data = workbook([("ReadMe", [["x"]]), ("FS5. FS2 + amino acids & bases", [["Global", "Ace", "Met"],
                                                                                    ["R1", "R2", ""]])])
        got = M.sheets(data)
        self.assertEqual(list(got), ["ReadMe", "FS5. FS2 + amino acids & bases"])
        self.assertEqual(got["FS5. FS2 + amino acids & bases"][1], {"A": "R1", "B": "R2"})

    def test_network_rows(self):
        header = ["ECs", "RN", "Equation_ids", "Equation_names", "Cofactors_rule"]
        rows = [["title"], header, ["", "R00001", "A + 2 B <=> C", "", "(x y)&z"]]
        rows += [["", f"R_P_{i}", f"Q{i} => P", "", "Pooling"] for i in range(M.POOLING)]
        cells = [{chr(65 + j): v for j, v in enumerate(r) if v} for r in rows]
        net = M.network(cells, "S1X", 1)
        self.assertEqual(net[0], ("R00001", frozenset("AB"), frozenset("C"), True, alts("x z", "y z")))
        with self.assertRaises(M.Refused):
            M.network(cells, "S1X", 2)                               # the count must be the paper's
        with self.assertRaises(M.Refused):
            M.network(cells[:-1], "S1X", 1)                          # 44 pooling reactions
        with self.assertRaises(M.Refused):
            M.network(cells + [cells[2]], "S1X", 2)                  # a repeated number

    def test_s4(self):
        text = ("<meta-data>\nnrMolecules = 3\nnrFoodSet   = 2\nnrReactions = 1\n\n<molecules>\nA; a\tA\n\n"
                "<food set>\nA; a\tA\nPooling\tPooling\n\n<reactions>\nR1\tA => B\tPooling\t1.0\n")
        self.assertEqual(M.s4_file(text), (["A", "Pooling"], [("R1", "A => B", "Pooling")]))
        with self.assertRaises(M.Refused):
            M.s4_file(text.replace("nrReactions = 1", "nrReactions = 2"))


class Seed(unittest.TestCase):
    def test_refuses_a_bad_seed(self):
        with self.assertRaises(M.Refused):
            M.run("xyz", inputs=os.path.join(HERE, "_never"), results=os.path.join(HERE, "_never"))


@unittest.skipUnless(HAVE, "the paper's files are not at inputs/ (or XAVIER_INPUTS)")
class PaperFiles(unittest.TestCase):
    def test_networks_food_and_s4(self):
        data = {k: M.read_bytes(os.path.join(INPUTS, name), sha) for k, (name, sha) in M.INPUTS.items()}
        s1 = M.sheets(data["s1"])
        nets = {tag: M.network(s1[sheet], sheet, n) for tag, sheet, n in M.NETWORKS}
        self.assertEqual([len(n) for n in nets.values()], [6039, 1238, 965])
        food, reactions = M.s4_file(data["s4"].decode("utf-8"))
        F = M.food_sets(food)
        self.assertEqual(len(F["FS3"]), 68)
        same, directions = M.against_s1a(nets["global"], M.s4_network(reactions))
        self.assertTrue(same)
        self.assertEqual(directions, 2774)                              # read before any maxRAF was computed
        s2 = M.sheets(data["s2"])
        self.assertTrue(set(M.S2_SHEETS.values()) <= set(s2))


if __name__ == "__main__":
    unittest.main()
