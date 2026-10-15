"""Martin et al.'s colourings check (packing/martin.py): the readers, the packing condition, the pairwise control,
the placements of the partial solution, and a whole run on an e-print built here. Every table here is made by the
tests (greedy packing colourings of tori, chessboards, random grids); none of the paper's tables is read.

Run with: python3 -m unittest tests.test_martin
"""

import hashlib
import importlib.util
import io
import json
import os
import random
import tarfile
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("packing_martin", os.path.join(HERE, "..", "packing", "martin.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

SEED = "6d" * 32


def greedy(n, order_seed=None, force=False):
    """A packing colouring of the n x n torus, read as a periodic colouring of Z^2: each cell in turn takes the least
    colour c with no cell of colour c within distance c; a colour c >= n would meet its own translate, so when none
    below n is free the colouring fails (None), or with force takes n - 1 anyway and breaks the rule."""
    cells = [(i, j) for i in range(n) for j in range(n)]
    if order_seed is not None:
        random.Random(order_seed).shuffle(cells)
    blocked = {}
    grid = [[0] * n for _ in range(n)]
    for i, j in cells:
        c = 1
        while c < n and (i, j) in blocked.get(c, ()):
            c += 1
        if c >= n:
            if not force:
                return None
            c = n - 1
        grid[i][j] = c
        b = blocked.setdefault(c, set())
        for di in range(-c, c + 1):
            for dj in range(-c, c + 1):
                if abs(di) + abs(dj) <= c:
                    b.add(((i + di) % n, (j + dj) % n))
    return grid


def tex_table(grid, label, env="array"):
    n = len(grid)
    body = "\n".join(" & ".join(str(v) for v in row) + " \\\\" for row in grid)
    return ("\\begin{figure}\\begin{center}\\resizebox{!}{4cm}{\\ensuremath{\\mathbb{\n"
            f"\\begin{{{env}}}{{{'c' * n}}}\n{body}\n\\end{{{env}}}\n}}}}}}\\end{{center}}\n"
            f"\\label{{{label}}}\n\\caption{{x}}\n\\end{{figure}}\n")


def tex_frequency(tables):
    parts = []
    for g in tables:
        counts = M.counts_of(g)
        rows = "\n".join(f"{c} & {x} \\\\" for c, x in sorted(counts.items()))
        parts.append(f"\\begin{{array}}{{cc}}\n{rows}\n\\hline\n& {sum(counts.values())}\n\\end{{array}}")
    return ("\\begin{figure}\\begin{center}" + "\\hspace{1cm}".join(parts) +
            "\\end{center}\\caption{f}\\label{fig:frequency}\\end{figure}\n")


class Readers(unittest.TestCase):
    def test_table_round_trip_and_tabular(self):
        g = [[1, 2, 1], [3, 1, 2], [1, 4, 1]]
        self.assertEqual(M.parse_table(tex_table(g, "fig:a"), "fig:a", 3), g)
        tab = tex_table(g, "fig:b", env="tabular").replace(" & ", "&")
        self.assertEqual(M.parse_table(tab, "fig:b", 3), g)

    def test_refusals(self):
        g = [[1, 2, 1], [3, 1, 2], [1, 4, 1]]
        good = tex_table(g, "fig:a")
        for bad, why in ((good.replace("3 & 1 & 2", "3 & 1"), "short row"),
                         (good.replace("3 & 1 & 2", "3 & x & 2"), "not an integer"),
                         (good.replace("{ccc}", "{cccc}"), "spec"),
                         (good.replace("\\label{fig:a}", "\\label{fig:z}"), "no label"),
                         (good + good, "label twice"),
                         (good.replace("\\end{array}", "\\end{array}\\begin{array}{c} 1 \\\\ \\end{array}"), "two")):
            with self.assertRaises(M.Refused, msg=why):
                M.parse_table(bad, "fig:a", 3)
        with self.assertRaises(M.Refused):
            M.parse_table(tex_table([[1, 2], [2, 1]], "fig:a"), "fig:a", 3)

    def test_frequency(self):
        a, b, c = greedy(6, force=True), [[1, 2], [2, 1]], [[1] * 3] * 3
        freq = M.parse_frequency(tex_frequency([a, b, c]))
        self.assertEqual([f[0] for f in freq], [M.counts_of(a), M.counts_of(b), M.counts_of(c)])
        self.assertEqual([f[1] for f in freq], [36, 4, 9])
        with self.assertRaises(M.Refused):
            M.parse_frequency(tex_frequency([a, b]))
        with self.assertRaises(M.Refused):
            M.parse_frequency(tex_frequency([a, b, c]).replace("1 & 18", "1 & 18 & 2"))

    def test_eprint(self):
        tex = "hello"
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            data = tex.encode()
            info = tarfile.TarInfo(M.TEX)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        self.assertEqual(M.tex_from_eprint(buf.getvalue()), "hello")
        other = io.BytesIO()
        with tarfile.open(fileobj=other, mode="w:gz") as tar:
            info = tarfile.TarInfo("other.tex")
            info.size = 1
            tar.addfile(info, io.BytesIO(b"x"))
        with self.assertRaises(M.Refused):
            M.tex_from_eprint(other.getvalue())
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, M.INPUT[0]), "wb") as f:
                f.write(b"not the e-print")
            with self.assertRaises(M.Refused):
                M.load(tmp)


class Packing(unittest.TestCase):
    def test_offsets(self):
        for c in range(1, 18):
            offs = M.offsets(c)
            self.assertEqual(len(offs), c * (c + 1))
            self.assertEqual(len(set(offs)), len(offs))
            self.assertFalse(any((-a, -b) in offs for a, b in offs))

    def test_known_answers(self):
        for n in (4, 8, 12):                          # even, so that the chessboard closes up on the torus
            ones = [[1] * n for _ in range(n)]
            board = [[1 + (i + j) % 2 for j in range(n)] for i in range(n)]
            self.assertEqual(M.packing(ones, 2)["violations"], 2 * n * n)
            self.assertEqual(M.packing(board, 2)["violations"], 2 * n * n)
            self.assertEqual(M.pairwise(board, 2), 2 * n * n)

    def test_greedy_colourings_pass_and_corruptions_fail(self):
        for n in (72, 80):
            g = greedy(n)
            self.assertIsNotNone(g, n)
            k = max(max(r) for r in g)
            r = M.packing(g, k)
            self.assertTrue(r["ok"], (n, r["examples"]))
            self.assertGreaterEqual(r["slack"], 1)
            self.assertEqual(M.pairwise(g, k), 0)
            self.assertFalse(M.packing(g, k - 1)["ok"])        # its top colour now out of range
            bad = [row[:] for row in g]
            i, j = next((i, j) for i in range(n) for j in range(n) if g[i][j] == 3)
            bad[(i + 2) % n][(j + 1) % n] = 3                     # colour 3 at distance 3 from another
            v = M.packing(bad, k)["violations"]
            self.assertGreater(v, 0)
            self.assertEqual(M.pairwise(bad, k), v)

    def test_pairwise_agrees_on_random_grids(self):
        rng = random.Random(11)
        for n in (5, 9, 16):
            g = [[rng.randint(1, 6) for _ in range(n)] for _ in range(n)]
            self.assertEqual(M.pairwise(g, 6), M.packing(g, 6)["violations"])

    def test_self_translate_counts(self):
        g = [[1, 2, 1, 3], [2, 1, 3, 1], [1, 3, 1, 2], [3, 1, 2, 1]]
        # colour 3 sits on an anti-diagonal: its cells are 2 apart in the plane, and each meets itself at distance 4
        self.assertEqual(M.packing(g, 4)["violations"], M.pairwise(g, 4))
        big = [[5] * 4 for _ in range(4)]
        big[0][0] = 4
        self.assertGreater(M.packing(big, 5)["violations"], 0)


class Placements(unittest.TestCase):
    def test_symmetries_distinct(self):
        base = [[(i * 7 + j * 3 + i * j) % 11 for j in range(6)] for i in range(6)]
        seen = {tuple(map(tuple, M.transformed(base, g))) for _, g in M.symmetries()}
        self.assertEqual(len(seen), 8)

    def test_found_at_the_planted_placement(self):
        base = greedy(24, 5, force=True)
        rng = random.Random(2)
        for idx, (a, b) in ((2, (3, 17)), (5, (0, 0)), (7, (20, 9))):
            name, g = M.symmetries()[idx]
            t = M.transformed(base, g)
            big = [[t[(i + a) % 24][(j + b) % 24] if t[(i + a) % 24][(j + b) % 24] <= 4 else rng.randint(5, 9)
                    for j in range(48)] for i in range(48)]
            best, total, reach, tried = M.placements(big, base, 4)
            self.assertEqual(tried, 8 * 24 * 24)
            self.assertEqual(best, total)
            self.assertIn((name, a, b), [(r[2], r[3], r[4]) for r in reach])
            big[1][1] = 99 if t[(1 + a) % 24][(1 + b) % 24] <= 4 else big[1][1]
            best2, total2, _, _ = M.placements(big, base, 4)
            self.assertLessEqual(best2, total2)
        with self.assertRaises(M.Refused):
            M.placements([[1] * 30 for _ in range(30)], base, 4)


class WholeRun(unittest.TestCase):
    def setUp(self):
        self.saved = (M.INPUT, M.TABLES)

    def tearDown(self):
        M.INPUT, M.TABLES = self.saved

    def build(self, tmp, t24, t48, t72, freq=None):
        tex = (tex_table(t48, "fig:main") + tex_table(t24, "fig:17-col") +
               tex_frequency(freq or [t24, t48, t72]) + tex_table(t72, "fig:15", env="tabular"))
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            data = tex.encode()
            info = tarfile.TarInfo(M.TEX)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        blob = buf.getvalue()
        M.INPUT = (M.INPUT[0], hashlib.sha256(blob).hexdigest(), len(blob))
        os.makedirs(os.path.join(tmp, "in"), exist_ok=True)
        with open(os.path.join(tmp, "in", M.INPUT[0]), "wb") as f:
            f.write(blob)

    def test_valid_tables_pass(self):
        t24, t48, t72 = greedy(24, 1, force=True), greedy(48, 2, force=True), greedy(72)
        k = {key: max(max(r) for r in g) for key, g in (("sh17", t24), ("c16", t48), ("c15", t72))}
        M.TABLES = {"sh17": ("fig:17-col", 24, k["sh17"]), "c16": ("fig:main", 48, k["c16"]),
                    "c15": ("fig:15", 72, k["c15"])}
        with tempfile.TemporaryDirectory() as tmp:
            self.build(tmp, t24, t48, t72)
            out, detail = M.run(SEED, inputs=os.path.join(tmp, "in"), results=os.path.join(tmp, "out"))
            on_disk = json.load(open(os.path.join(tmp, "out", "outputs.json")))
        self.assertEqual(on_disk, out)
        self.assertEqual(sorted(out), sorted(M.OUTPUTS))
        self.assertEqual((out["witness_ok"], out["test_passed"], out["c15_violations"]), (1, 1, 0))
        self.assertEqual(out["controls_passed"], out["controls_total"])
        self.assertTrue(out["freq_c15"].startswith(f"{len(M.counts_of(t72))} of {len(M.counts_of(t72))} colours"))
        self.assertTrue(all(isinstance(v, (int, str)) for v in out.values()))

    def test_corrupt_table_fails_and_unread_is_an_outcome(self):
        t24, t48, t72 = greedy(24, 1, force=True), greedy(48, 2, force=True), greedy(72)
        k72 = max(max(r) for r in t72)
        M.TABLES = {"sh17": ("fig:17-col", 24, 99), "c16": ("fig:main", 48, 99), "c15": ("fig:15", 72, k72)}
        bad = [row[:] for row in t72]
        i, j = next((i, j) for i in range(72) for j in range(72) if t72[i][j] == 2)
        bad[i][(j + 1) % 72] = 2
        with tempfile.TemporaryDirectory() as tmp:
            self.build(tmp, t24, t48, bad, freq=[t24, t48, t72])
            out, _ = M.run(SEED, inputs=os.path.join(tmp, "in"), results=os.path.join(tmp, "out"))
        self.assertEqual((out["witness_ok"], out["test_passed"]), (0, 0))
        self.assertGreater(out["c15_violations"], 0)
        self.assertNotEqual(out["freq_c15"].split(" of ")[0], out["freq_c15"].split(" of ")[1].split()[0])
        with tempfile.TemporaryDirectory() as tmp:
            self.build(tmp, t24, t48, [row[:71] for row in t72])
            out, detail = M.run(SEED, inputs=os.path.join(tmp, "in"), results=os.path.join(tmp, "out"))
        self.assertEqual((out["witness_ok"], out["test_passed"], out["c15_violations"]), (0, 0, -1))
        self.assertIn("c15", detail["unread"])
        self.assertLess(out["controls_passed"], out["controls_total"])

    def test_refusals(self):
        with self.assertRaises(M.Refused):
            M.run("xyz")


class Registered(unittest.TestCase):
    def test_constants(self):
        self.assertLessEqual(len(M.TEST), 600)
        self.assertEqual(M.INPUT, ("arXiv-1510.02374v3.tar.gz",
                                   "a8539f6859d8a9c85a2611b832f654d8ef7fbc4932d7a17c93fe5fa120b9b1c2", 20068))
        self.assertEqual(M.TABLES["c15"], ("fig:15", 72, 15))
        self.assertEqual(M.TABLES["c16"], ("fig:main", 48, 16))
        self.assertEqual(M.TABLES["sh17"], ("fig:17-col", 24, 17))
        self.assertEqual(M.PLANTED, {"c15": 5, "c16": 7})
        self.assertEqual(len(set(M.OUTPUTS)), len(M.OUTPUTS))
        self.assertLessEqual(len(M.OUTPUTS), 64)


if __name__ == "__main__":
    unittest.main()
