"""Xavier & Kauffman 2022 (raf/xk2022.py): the readers on files written here, the list check on raf/xavier.py's small
system and on a small network with a pooling reaction, and the conditions on a small made-up release. No
supplementary file is read.

Run with: python3 -m unittest discover -s tests -p test_xk2022.py
"""

import importlib.util
import io
import os
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("raf_xk2022", os.path.join(HERE, "..", "raf", "xk2022.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

REACTIONS = [
    "R00001\tC1 + C2 => C3\tNADs\t1.0",                 # catalysed by the NAD pool
    "R00002\tC3 <=> C4\t(C3 C9)&Spontaneous\t1.0",      # two-way
    "R00003\tC4 + C5 => C6\tC6\t1.0",                  # needs C5, catalysed by its own product
    "R00004\tC1 => C00079\tSpontaneous\t1.0",          # makes phenylalanine
    "R_NADs_1\tC00003 => NADs\tPooling\t1.0",
]
NET_TEXT = "**Supplementary Data 2**\n**A title**\n\n" + M.NETWORK_HEADER + "\n" + "\n".join(REACTIONS) + "\n\n"
RICH = frozenset(["C1", "C2", "C5", "C00003", "Pooling", "Spontaneous"])
NAD = frozenset(["C1", "C2", "C00003", "Pooling", "Spontaneous"])


def food_rows(items=(("C1", 1, 1), ("C2", 1, 0), ("Pooling", 1, 1), ("Spontaneous", 1, 1), ("C00003", 1, 1))):
    rows = [{"A": "Supplementary Data 3"}, {"A": "A title"}, dict(M.FOOD_HEADER)]
    for mid, rich, nad in items:
        row = {"A": mid + " (a name)", "B": mid}
        if rich:
            row["C"] = M.TICK
        if nad:
            row["D"] = M.TICK
        rows.append(row)
    return rows + [{}]


def organism_rows(codes):
    rows = [{"A": "Supplementary Data 1"}, {"A": "A title"}, dict(M.ORGANISM_HEADER)]
    return rows + [{"A": f"T{i}", "B": c, "C": "Somebacter", "G": "Bacteria"} for i, c in enumerate(codes)]


def archive(folder, files, extra=()):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(folder + "/", "")
        for code, ids in files.items():
            z.writestr(f"{folder}/{code}.txt", "\n".join(ids) + "\n")
        for name, text in extra:
            z.writestr(name, text)
    return buf.getvalue()


class Reading(unittest.TestCase):
    def test_network(self):
        net = M.network_file(NET_TEXT)
        self.assertEqual([x[0] for x in net], ["R00001", "R00002", "R00003", "R00004", "R_NADs_1"])
        self.assertEqual([x[3] for x in net], [False, True, False, False, False])
        self.assertEqual(net[4][4], M.POOL)
        self.assertEqual(net[1][4], frozenset([frozenset(["C3", "Spontaneous"]), frozenset(["C9", "Spontaneous"])]))
        for bad in (NET_TEXT + M.NETWORK_HEADER + "\n", NET_TEXT.replace(M.NETWORK_HEADER, "Reaction_ID\tEquation"),
                    NET_TEXT.replace("NADs\t1.0", "NADs"), NET_TEXT.replace("R00002\t", "R00001\t"),
                    NET_TEXT + "R_X\tC1 => X\tNADs\t1.0\n", NET_TEXT.replace("C6\t1.0", "C6\tfast"),
                    NET_TEXT.replace("C3 <=> C4", "C3 -> C4")):
            with self.assertRaises(M.Refused):
                M.network_file(bad)

    def test_media(self):
        food = M.media(food_rows())
        self.assertEqual(food["rich"], frozenset(["C1", "C2", "Pooling", "Spontaneous", "C00003"]))
        self.assertEqual(food["nad"], frozenset(["C1", "Pooling", "Spontaneous", "C00003"]))
        rows = food_rows()
        rows[4]["D"] = "x"
        with self.assertRaises(M.Refused):
            M.media(rows)
        for items in ((("C1", 1, 1), ("Pooling", 1, 0), ("Spontaneous", 1, 1)),
                      (("C1", 1, 1), ("C1", 1, 1), ("Pooling", 1, 1), ("Spontaneous", 1, 1))):
            with self.assertRaises(M.Refused):
                M.media(food_rows(items))
        rows = food_rows()
        rows[2]["C"] = "Rich"
        with self.assertRaises(M.Refused):
            M.media(rows)

    def test_organisms(self):
        self.assertEqual(M.organisms(organism_rows(["aaa", "aab", "aaa"]) + [{}]), ["aaa", "aab", "aaa"])
        with self.assertRaises(M.Refused):
            M.organisms(organism_rows(["aaa"]) + [{"A": "a note"}])

    def test_lists(self):
        got = M.lists(archive("maxRAFs_Rich", {"aaa": ["R00001", "", " R00002 "], "aab": []}), "maxRAFs_Rich", "SD4")
        self.assertEqual(got, {"aaa": ["R00001", "R00002"], "aab": []})
        mac = M.lists(archive("maxRAFs_NAD", {"aaa": ["R00001"]}, (("__MACOSX/", ""),)), "maxRAFs_NAD", "SD5")
        self.assertEqual(mac, {"aaa": ["R00001"]})
        for extra in ((("__MACOSX/._aaa.txt", "x"),), (("maxRAFs_Rich/aac.csv", "R00001"),),
                      (("maxRAFs_Rich/aac.txt", "R00001 R00002"),), (("other/", ""),)):
            with self.assertRaises(M.Refused):
                M.lists(archive("maxRAFs_Rich", {"aaa": ["R00001"]}, extra), "maxRAFs_Rich", "SD4")


class Checking(unittest.TestCase):
    def setUp(self):
        self.g = M.Global(M.network_file(NET_TEXT))

    def test_toy(self):
        self.assertTrue(M.toy_control())

    def test_list_check(self):
        g = self.g
        self.assertEqual(g.pooling, frozenset(["R_NADs_1"]))
        one = M.list_check(["R00001"], g, NAD)
        self.assertTrue(one["raf"])
        self.assertEqual((one["size"], one["with_pooling"]), (1, 1))
        self.assertTrue(M.list_check(["R00001", "R00002"], g, NAD)["raf"])
        self.assertFalse(M.list_check(["R00002"], g, NAD)["raf"])                  # nothing makes C3 or C4
        self.assertFalse(M.list_check(["R00001", "R00003"], g, NAD)["raf"])        # C5 is not NAD food
        self.assertTrue(M.list_check(["R00001", "R00002", "R00003"], g, RICH)["raf"])
        self.assertFalse(M.list_check(["R00001"], g, NAD - {"C00003"})["raf"])     # no NAD+, no pool
        pooled = M.list_check(["R00001", "R_NADs_1", "R00001"], g, NAD)
        self.assertEqual((pooled["raf"], pooled["size"], pooled["with_pooling"], pooled["pooling_listed"],
                          pooled["repeats"]), (True, 1, 2, 1, 1))
        unknown = M.list_check(["R00001", "R99999"], g, NAD)
        self.assertEqual((unknown["raf"], unknown["unknown"]), (False, ["R99999"]))
        self.assertEqual(M.list_check(["R00004"], g, RICH, ("C00079", "C00135"))["made"], ("C00079",))


class Assessing(unittest.TestCase):
    def release(self, nad_aab=None, codes=("aaa", "aab")):
        listed = {"rich": {"aaa": ["R00001", "R00002", "R00003"], "aab": ["R00001", "R00004"]},
                  "nad": {"aaa": ["R00001", "R00002"]}}
        if nad_aab:
            listed["nad"]["aab"] = nad_aab
        return list(codes), M.network_file(NET_TEXT), {"rich": RICH, "nad": NAD}, listed

    def test_passing(self):
        out, detail = M.assess(*self.release(), prokaryotes=2, sizes=(2, 3))
        self.assertEqual((out["conditions_met"], out["conditions_total"], out["test_passed"]), (4, 4, 1))
        self.assertEqual((out["controls_passed"], out["controls_total"]), (4, 4))
        self.assertTrue(out["sizes"].startswith("rich 2-3, NAD 2-2; both media 2-3"))
        self.assertTrue(out["mean_sizes"].startswith("rich 2.5 over the 2 codes, 2.5 over nonempty lists; NAD 1.0 and 2.0"))
        self.assertEqual(out["not_made"], "rich lists generating Phe 1, His 0, Arg 0, glycerol-1-P 0 (printed: none)")
        self.assertEqual(detail["sizes"], {"aaa": [3, 2], "aab": [2, 0]})
        self.assertEqual(detail["whole_maxraf"]["nad"], ["R00001", "R00002", "R00004"])
        self.assertEqual(detail["whole_maxraf"]["rich"], ["R00001", "R00002", "R00003", "R00004"])
        for v in out.values():
            self.assertLessEqual(len(str(v)), M.LIMIT)

    def test_failing(self):
        out, detail = M.assess(*self.release(nad_aab=["R00003"], codes=("aaa", "aab", "aac")), prokaryotes=3)
        self.assertEqual((out["conditions_met"], out["test_passed"]), (1, 0))      # only the rich lists hold
        self.assertEqual(detail["failures_total"], 1)
        self.assertEqual(detail["failures"][0]["code"], "aab")
        out2, _ = M.assess(*self.release(codes=("aaa", "aab", "aab")), prokaryotes=3, sizes=(2, 3))
        self.assertEqual(out2["conditions_met"], 3)                                # a code twice


class Machinery(unittest.TestCase):
    def test_outputs(self):
        self.assertEqual(len(M.OUTPUTS), len(set(M.OUTPUTS)))
        self.assertLessEqual(len(M.OUTPUTS), 64)
        self.assertEqual(set(M.INPUTS), {"sd1", "sd2", "sd3", "sd4", "sd5"})
        with self.assertRaises(M.Refused):
            M.run("not-a-seed")


if __name__ == "__main__":
    unittest.main()
