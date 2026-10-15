#!/usr/bin/env python3
"""Martin, Raimondi, Chen and Martin's packing 15-colouring of the infinite square lattice, checked exactly from the
paper's own tables, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:280322c20a1cb492) is from Martin, Raimondi,
Chen and Martin, "The packing chromatic number of the infinite square lattice is between 13 and 15", Discrete Applied
Mathematics 225 (2017) 136-142 (arXiv:1510.02374v3): "Using a SAT-solver on top of a partial previously-known
solution we improve the upper bound of the packing chromatic number of the infinite square lattice from 17 to 15."
Subercaseaux and Heule's value 15 (ext:18c6f5de78f846d3, on the record) takes its upper bound from this paper.

Its registered test is TEST below. The one input is the paper's LaTeX source as arXiv serves it (1510.02374v3, a
gzipped tar, by hash; read as data, nothing in it is run): its file PackingCromaticNumberDAM.tex prints the three
colourings the paper uses, Soukal and Holub's 24 x 24 17-colouring (the figure labelled fig:17-col), the paper's
48 x 48 16-colouring (fig:main) and its 72 x 72 15-colouring (fig:15), and their frequency tables (fig:frequency).
Section 1 says how the two new colourings were made: "we take the Soukal-Hulob colouring and remove colours 8 to 17,
then we blow this up from 24 x 24 to 48 x 48 by taking four copies of it", a SAT solver then completing the 16-colouring,
and likewise colours 6 to 17 removed and the grid blown up to 72 x 72 for the 15-colouring. Every rule below was fixed
before any of the three tables was read for anything but its shape; the tests use other tables.

1. The tables. Each figure is found by its label, between the \\begin{figure} before it and the \\end{figure} after it;
   it must hold exactly one array or tabular whose column specification is n letters c (n = 24, 48 and 72), whose
   rows are n integers joined by "&" (spaces allowed) and ended by "\\\\", and nothing else; a table must be n x n.
2. The test: the 72 x 72 table, read as the colouring (x, y) -> T[x mod 72][y mod 72] of Z^2, is a packing
   15-colouring of the infinite square lattice: every entry in 1..15, and no two cells of a colour c within lattice
   (Manhattan) distance c, the paper's toroidal distance. For every cell of colour c and every offset d with
   1 <= |d|_1 <= c (each unordered pair once), the cell at d (mod 72 both ways) must not have colour c; an offset
   that lands on its own cell would count too (none can when n > c). witness_ok needs all of it.
3. Beside the test: the same check of the 48 x 48 table as a packing 16-colouring and of Soukal and Holub's table as a
   packing 17-colouring; each colouring's counts by colour against the frequency table the paper prints for it (left
   Soukal-Holub, middle 16, right 15, as its caption says), and the least slack (closest pair of colour c, less c);
   and the partial solution: the cells where Soukal and Holub's table, repeated, has colour at most 5 (for the 72 x 72)
   or at most 7 (for the 48 x 48), placed on the larger table under each of the square's 8 symmetries and 24 x 24
   shifts (every placement the text's "blow up" allows), counted as agreeing where the larger table has the same
   colour; reported is the best placement's agreement and how many placements reach it.
4. Controls, known answers: an independent pairwise check (every pair of same-coloured cells of one period against
   the 9 nearest translates, colour 1 by its 4 neighbours) gives the offset check's verdicts and counts on the three
   tables and on corrupted copies; one cell changed in each table to repeat its colour within reach is caught; the
   all-1 grid has 2 n^2 violations and the 1-2 chessboard 2 n^2; a placement made from Soukal and Holub's table under
   a chosen symmetry and shift is found at that symmetry and shift with every planted cell agreeing; and the readers
   on a hand-made figure, with their refusals.

What it cannot check: the lower bound 13, whose SAT instance ran 16 days (the paper's Section 3), and the running
times; nor does it re-run the SAT search, since the printed colourings are the certificates the bound rests on.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Standard library only (the pinned python image). Run with: python3 packing/martin.py
"""

import hashlib
import io
import json
import os
import re
import sys
import tarfile

TEST = (
    "Refuted if the 72 x 72 colouring the paper prints for its upper bound (the figure 'Our 72 x 72 periodic solution "
    "in 15 colours', read from the e-print's TeX), repeated periodically over the plane, is not a packing 15-colouring "
    "of the infinite square lattice: a table other than 72 x 72, an entry outside 1-15, or two cells of one colour i "
    "at lattice (Manhattan) distance at most i, the paper's toroidal distance."
)
INPUT = ("arXiv-1510.02374v3.tar.gz", "a8539f6859d8a9c85a2611b832f654d8ef7fbc4932d7a17c93fe5fa120b9b1c2", 20068)
TEX = "PackingCromaticNumberDAM.tex"
TABLES = {"sh17": ("fig:17-col", 24, 17), "c16": ("fig:main", 48, 16), "c15": ("fig:15", 72, 15)}
FREQUENCY = "fig:frequency"
FREQ_ORDER = ("sh17", "c16", "c15")          # left, middle, right, as the caption says
PLANTED = {"c15": 5, "c16": 7}                # Soukal and Holub's colours kept in each larger table
OUTPUTS = ("source", "witness_ok", "c15_colours", "c15_violations", "c15_slack", "c16_ok", "c16_violations",
           "sh17_ok", "sh17_violations", "freq_c15", "freq_c16", "freq_sh17", "planted_c15", "planted_c16",
           "conditions_met", "conditions_total", "test_passed", "controls_passed", "controls_total")
LIMIT = 200


class Refused(Exception):
    pass


# ---------------------------------------------------------------- the input

def load(directory):
    name, digest, size = INPUT
    path = os.path.join(directory, name)
    with open(path, "rb") as f:
        data = f.read()
    got = hashlib.sha256(data).hexdigest()
    if got != digest or len(data) != size:
        raise Refused(f"{path}: sha256 {got} and {len(data)} bytes, not the committed {digest} and {size}")
    return data


def tex_from_eprint(data):
    """The text of TEX from the e-print's gzipped tar, read in memory (nothing is extracted)."""
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            m = tar.getmember(TEX)
            if not m.isfile():
                raise Refused(f"e-print: {TEX} is not a regular file")
            return tar.extractfile(m).read().decode("utf-8")
    except (tarfile.TarError, KeyError) as e:
        raise Refused(f"e-print: no {TEX} in it ({e})") from None


# ---------------------------------------------------------------- rule 1: the tables

def figure(tex, label):
    """The text of the figure environment holding \\label{label}."""
    at = tex.find("\\label{%s}" % label)
    if at < 0 or tex.find("\\label{%s}" % label, at + 1) >= 0:
        raise Refused(f"{TEX}: \\label{{{label}}} is not there exactly once")
    start = tex.rfind("\\begin{figure}", 0, at)
    end = tex.find("\\end{figure}", at)
    if start < 0 or end < 0 or tex.rfind("\\end{figure}", start, at) >= 0:
        raise Refused(f"{TEX}: \\label{{{label}}} is not inside a figure")
    return tex[start:end]


ENV = re.compile(r"\\begin\{(array|tabular)\}\{([^}]*)\}(.*?)\\end\{\1\}", re.S)


def parse_rows(body):
    rows = [r.strip() for r in body.split("\\\\")]
    while rows and rows[-1] == "":
        rows.pop()
    return rows


def parse_table(tex, label, n):
    """Rule 1: the n x n table of the figure labelled label."""
    envs = ENV.findall(figure(tex, label))
    if len(envs) != 1:
        raise Refused(f"{label}: {len(envs)} arrays or tabulars, not one")
    _, spec, body = envs[0]
    if spec.strip() != "c" * n:
        raise Refused(f"{label}: the column specification is not {n} letters c")
    rows = parse_rows(body)
    grid = []
    for r in rows:
        if not re.fullmatch(r"\s*\d+(\s*&\s*\d+)*\s*", r):
            raise Refused(f"{label}: a row that is not integers joined by &: {r[:60]!r}")
        grid.append([int(x) for x in r.split("&")])
    if len(grid) != n or any(len(r) != n for r in grid):
        raise Refused(f"{label}: {len(grid)} rows of {sorted(set(len(r) for r in grid))} entries, not {n} x {n}")
    return grid


def parse_frequency(tex):
    """The frequency figure's arrays, in order: each a dict colour -> count and its printed total."""
    out = []
    for _, spec, body in ENV.findall(figure(tex, FREQUENCY)):
        if spec.strip() != "cc":
            raise Refused(f"{FREQUENCY}: an array that is not two columns")
        counts, total = {}, None
        for r in parse_rows(body):
            r = r.replace("\\hline", "").strip()
            if not r:
                continue
            m = re.fullmatch(r"(\d+)\s*&\s*(\d+)", r)
            t = re.fullmatch(r"&\s*(\d+)", r)
            if m:
                c = int(m.group(1))
                if c in counts:
                    raise Refused(f"{FREQUENCY}: colour {c} twice")
                counts[c] = int(m.group(2))
            elif t and total is None:
                total = int(t.group(1))
            else:
                raise Refused(f"{FREQUENCY}: a row that is neither 'colour & count' nor '& total': {r[:40]!r}")
        out.append((counts, total))
    if len(out) != 3:
        raise Refused(f"{FREQUENCY}: {len(out)} arrays, not three")
    return out


# ---------------------------------------------------------------- rule 2: packing colourings

def offsets(c):
    """The offsets d with 1 <= |d|_1 <= c, each unordered pair once."""
    return [(di, dj) for di in range(0, c + 1) for dj in range(-c, c + 1)
            if 0 < abs(di) + abs(dj) <= c and (di > 0 or dj > 0)]


def counts_of(grid):
    counts = {}
    for row in grid:
        for v in row:
            counts[v] = counts.get(v, 0) + 1
    return counts


def packing(grid, kmax):
    """Rule 2 on an n x n periodic table: violations of the packing condition, entries outside 1..kmax, and each
    colour's closest same-colour distance up to c + 2 (None beyond)."""
    n = len(grid)
    if n == 0 or any(len(r) != n for r in grid):
        raise Refused("not a square table")
    out_of_range = sum(1 for r in grid for v in r if not 1 <= v <= kmax)
    offs, violations, examples = {}, 0, []
    for i in range(n):
        for j in range(n):
            c = grid[i][j]
            if not 1 <= c <= kmax:
                continue
            if c not in offs:
                offs[c] = offsets(c)
            for di, dj in offs[c]:
                if grid[(i + di) % n][(j + dj) % n] == c:
                    violations += 1
                    if len(examples) < 5:
                        examples.append([i, j, (i + di) % n, (j + dj) % n, c])
    closest = {}
    for c in sorted(counts_of(grid)):
        if not 1 <= c <= kmax:
            continue
        cells = [(i, j) for i in range(n) for j in range(n) if grid[i][j] == c]
        best = None
        for r in range(1, c + 3):
            ring = [(di, dj) for di in range(0, r + 1) for dj in range(-r, r + 1)
                    if abs(di) + abs(dj) == r and (di > 0 or dj > 0)]
            if any(grid[(i + di) % n][(j + dj) % n] == c for i, j in cells for di, dj in ring):
                best = r
                break
        closest[c] = best
    slack = min(((d if d is not None else c + 3) - c) for c, d in closest.items()) if closest else None
    return {"n": n, "violations": violations, "out_of_range": out_of_range, "examples": examples,
            "closest": closest, "slack": slack, "colours": len([c for c in counts_of(grid) if 1 <= c <= kmax]),
            "ok": violations == 0 and out_of_range == 0}


def pairwise(grid, kmax):
    """Control: every pair of same-coloured cells of one period against the 9 nearest translates (colour 1 by its 4
    neighbours), counted as unordered pairs in the plane up to translation by the period."""
    n = len(grid)
    by_colour = {}
    for i in range(n):
        for j in range(n):
            by_colour.setdefault(grid[i][j], []).append((i, j))
    violations = 0
    for c, cells in by_colour.items():
        if not 1 <= c <= kmax:
            continue
        if c == 1:
            for i, j in cells:
                violations += (grid[(i + 1) % n][j] == 1) + (grid[i][(j + 1) % n] == 1)
            continue
        found = set()
        for a, (i1, j1) in enumerate(cells):
            for (i2, j2) in cells:
                for ti in (-n, 0, n):
                    for tj in (-n, 0, n):
                        di, dj = i2 + ti - i1, j2 + tj - j1
                        if 0 < abs(di) + abs(dj) <= c:
                            key = (di, dj) if (di > 0 or (di == 0 and dj > 0)) else (-di, -dj)
                            start = (i1, j1) if key == (di, dj) else ((i2 + ti) % n, (j2 + tj) % n)
                            found.add((start, key))
        violations += len(found)
    return violations


# ---------------------------------------------------------------- rule 3: the partial solution

def symmetries():
    """The square's 8 symmetries as maps of (i, j) (coordinates taken mod the period by the caller)."""
    return [("identity", lambda i, j: (i, j)), ("rotate 90", lambda i, j: (j, -i)),
            ("rotate 180", lambda i, j: (-i, -j)), ("rotate 270", lambda i, j: (-j, i)),
            ("reflect columns", lambda i, j: (i, -j)), ("reflect rows", lambda i, j: (-i, j)),
            ("transpose", lambda i, j: (j, i)), ("anti-transpose", lambda i, j: (-j, -i))]


def transformed(base, g):
    m = len(base)
    out = [[0] * m for _ in range(m)]
    for i in range(m):
        for j in range(m):
            a, b = g(i, j)
            out[i][j] = base[a % m][b % m]
    return out


def placements(grid, base, kmax):
    """Rule 3: for every symmetry of base and every shift (a, b), the cells of grid where base, repeated, has colour
    at most kmax, and how many of them grid colours the same. Returns (best, total, how many reach best, first)."""
    n, m = len(grid), len(base)
    if n % m:
        raise Refused("the larger table is not a whole number of copies")
    cnt = [[{} for _ in range(m)] for _ in range(m)]
    for i in range(n):
        for j in range(n):
            d = cnt[i % m][j % m]
            d[grid[i][j]] = d.get(grid[i][j], 0) + 1
    copies = (n // m) ** 2
    results = []
    for name, g in symmetries():
        t = transformed(base, g)
        for a in range(m):
            for b in range(m):
                agree = total = 0
                for r in range(m):
                    row = t[(r + a) % m]
                    cr = cnt[r]
                    for s in range(m):
                        v = row[(s + b) % m]
                        if v <= kmax:
                            total += copies
                            agree += cr[s].get(v, 0)
                results.append((agree, total, name, a, b))
    best = max(r[0] for r in results)
    total = results[0][1]
    reach = [r for r in results if r[0] == best]
    return best, total, reach, len(results)


# ---------------------------------------------------------------- controls

def controls(tables):
    c = {"all three tables read": all(key in tables for key in TABLES)}
    ok = True
    for key, (label, n, k) in TABLES.items():
        if key in tables:
            g = tables[key]
            ok = ok and pairwise(g, k) == packing(g, k)["violations"]
    c["the pairwise check gives the offset check's violation counts on the three tables"] = ok
    ok = True
    for key, (label, n, k) in TABLES.items():
        if key not in tables:
            continue
        g = [row[:] for row in tables[key]]
        # repeat the colour of the first cell of colour 2 one step to its right: a pair at distance 1
        i, j = next((i, j) for i in range(n) for j in range(n) if g[i][j] == 2)
        g[i][(j + 1) % n] = 2
        v = packing(g, k)["violations"]
        ok = ok and v > 0 and pairwise(g, k) == v
    c["one cell changed in each table to repeat colour 2 at distance 1 is caught, by both checks alike"] = ok
    ok = True
    for n in (6, 10):
        ones = [[1] * n for _ in range(n)]
        board = [[1 + (i + j) % 2 for j in range(n)] for i in range(n)]
        ok = ok and packing(ones, 2)["violations"] == 2 * n * n and pairwise(ones, 2) == 2 * n * n
        ok = ok and packing(board, 2)["violations"] == 2 * n * n and pairwise(board, 2) == 2 * n * n
    c["the all-1 grid and the 1-2 chessboard have 2 n^2 violations each (n = 6, 10)"] = ok
    ok = "sh17" in tables
    if ok:
        base = tables["sh17"]
        for (name, g), (a, b) in zip(symmetries()[1:4], ((5, 11), (0, 7), (13, 2))):
            t = transformed(base, g)
            big = [[t[(i + a) % 24][(j + b) % 24] if t[(i + a) % 24][(j + b) % 24] <= 5 else 99 for j in range(72)]
                   for i in range(72)]
            best, total, reach, _ = placements(big, base, 5)
            ok = ok and best == total and any(r[2] == name and (r[3], r[4]) == (a, b) for r in reach)
    c["a placement built under a chosen symmetry and shift is found with every planted cell agreeing"] = ok
    ok = True
    fake = ("\\begin{figure}\\begin{array}{ccc}\n 1 & 2 & 1 \\\\ \n 3 & 1 & 2 \\\\\n 1 & 2 & 1 \\\\\n\\end{array}"
            "\\label{fig:x}\\caption{x}\\end{figure}")
    ok = ok and parse_table(fake, "fig:x", 3) == [[1, 2, 1], [3, 1, 2], [1, 2, 1]]
    for bad in (fake.replace("3 & 1 & 2", "3 & 1 & x"), fake.replace("{ccc}", "{cc}"),
                fake.replace("\\label{fig:x}", ""), fake + "\\begin{figure}\\label{fig:x}\\end{figure}"):
        try:
            parse_table(bad, "fig:x", 3)
            ok = False
        except Refused:
            pass
    c["the table reader on a hand-made figure, and its four refusals"] = ok
    return c


# ---------------------------------------------------------------- the run

def freq_line(counts, printed, total):
    agree = sum(1 for col in set(counts) | set(printed) if counts.get(col, 0) == printed.get(col, 0))
    allc = len(set(counts) | set(printed))
    return (f"{agree} of {allc} colours' counts as printed; total {sum(counts.values())} against the printed "
            f"{total}")


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    tex = tex_from_eprint(load(inputs))
    tables, unread = {}, {}
    for key, (label, n, k) in TABLES.items():
        try:
            tables[key] = parse_table(tex, label, n)
        except Refused as e:
            unread[key] = str(e)
    checks = {key: packing(tables[key], k) for key, (label, n, k) in TABLES.items() if key in tables}
    try:
        freq = dict(zip(FREQ_ORDER, parse_frequency(tex)))
    except Refused as e:
        freq, unread["frequency"] = {}, str(e)
    planted = {key: placements(tables[key], tables["sh17"], kmax) for key, kmax in PLANTED.items()
               if key in tables and "sh17" in tables}
    ctl = controls(tables)

    missing = {"ok": False, "colours": 0, "violations": -1, "slack": None, "closest": {}}
    w = checks.get("c15", missing)
    cond = {"the 72 x 72 table is a packing 15-colouring of the square lattice": w["ok"]}
    values = {"source": "arXiv:1510.02374v3 e-print a8539f68 (PackingCromaticNumberDAM.tex: fig:15, fig:main, "
                        "fig:17-col, fig:frequency)",
              "witness_ok": int(w["ok"]), "c15_colours": w["colours"], "c15_violations": w["violations"],
              "c15_slack": w["slack"] if w["slack"] is not None else -1,
              "c16_ok": int(checks.get("c16", missing)["ok"]), "c16_violations": checks.get("c16", missing)["violations"],
              "sh17_ok": int(checks.get("sh17", missing)["ok"]),
              "sh17_violations": checks.get("sh17", missing)["violations"]}
    for key in FREQ_ORDER:
        if key in tables and key in freq:
            printed, total = freq[key]
            values[f"freq_{key}"] = freq_line(counts_of(tables[key]), printed, total)
        else:
            values[f"freq_{key}"] = "unread"
    for key, kmax in PLANTED.items():
        if key in planted:
            best, total, reach, tried = planted[key]
            first = reach[0]
            values[f"planted_{key}"] = (f"colours 1-{kmax} of Soukal-Holub, repeated: {best} of {total} cells agree "
                                        f"at best; {len(reach)} of {tried} placements reach it (first: {first[2]}, "
                                        f"shift {first[3]},{first[4]})")
        else:
            values[f"planted_{key}"] = "unread"
    values.update({"conditions_met": sum(cond.values()), "conditions_total": len(cond),
                   "test_passed": int(all(cond.values())), "controls_passed": sum(ctl.values()),
                   "controls_total": len(ctl)})
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"test": TEST, "conditions": cond, "controls": ctl, "unread": unread,
              "checks": {k: {**v, "closest": {str(c): d for c, d in v["closest"].items()}} for k, v in checks.items()},
              "counts": {k: {str(c): x for c, x in sorted(counts_of(tables[k]).items())} for k in tables},
              "printed_frequency": {k: {"counts": {str(c): x for c, x in sorted(freq[k][0].items())},
                                        "total": freq[k][1]} for k in freq},
              "planted": {k: {"best": p[0], "planted_cells": p[1], "at_best": [list(r) for r in p[2][:50]],
                              "placements_at_best": len(p[2]), "placements": p[3]} for k, p in planted.items()}}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="utf-8") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"martin: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
