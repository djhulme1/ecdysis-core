#!/usr/bin/env python3
"""Exoo's sum-free partition of [1, 160] into five sets: S(5) >= 160, R5(3) >= 162, and the bounds that follow.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:0f23107e990d76ad) is from Exoo, "A Lower
Bound for Schur Numbers and Multicolor Ramsey Numbers of K3" (The Electronic Journal of Combinatorics 1, #R8, 1994):
"For k >= 5, we establish new lower bounds on the Schur numbers S(k) and on the k-color Ramsey numbers of K_3."

Its registered test: refuted if the partition the paper prints, its five sets of 1 to 80 extended by its rule (i and
161 - i in the same set), is not a partition of {1, ..., 160} into 5 sum-free sets (no a + b = c in a set, a = b
allowed), so that S(5) >= 160 fails; or if the edge colouring of K161 it gives (vertices 0 to 160, uv coloured by the
set holding |u - v|) has a triangle of one colour, so that R5(3) >= 162 fails; or if the bounds it derives do not
follow by the arithmetic it states (R6(3) >= 3*162 + 17 - 3 = 500 by Chung's recurrence; 321^(1/5) > 3.17176).

Standard library only. The input is the claim's data of record, the paper as the journal serves it (a PDF of three
pages), checked against its SHA-256 and size and read in memory as data; nothing in it is run. The PDF is read by
schur/fs.py's reader (Flate-compressed content streams, TJ and Tj strings, a space wherever the gap after a glyph is
above 0.15 em), and the sum-free and triangle tests are schur/fs.py's, at the same commit. Every rule below was fixed
before any sum or triangle of this partition was computed.

1. Reading. The PDF's lines in order, the page headers dropped (the journal's name with "1 (1994), #R8", and the page
   number after it). The paper's statements (STATEMENTS below) must be present. The partition is the five lines
   "Set k: ..." for k = 1 to 5, in order, after the line that ends "from 1 to 80 are listed."; every listed number
   must be an integer from 1 to 80, the listing 1 to 80 once each; the run is refused otherwise, as a reading error.
2. The listing rule (the paper: "Since the partition is symmetric (i and 161 - i always belong to the same set), only
   the integers from 1 to 80 are listed."): a listed i stands for i and 161 - i in its set.
3. The test's three conditions: the expanded sets are a partition of {1, ..., 160} into 5 sets with no a + b = c in a
   set (a = b allowed); the colouring of the complete graph on {0, ..., 160}, the edge uv coloured by the set holding
   |u - v|, has no triangle of one colour, found by intersecting each edge's two endpoints' neighbourhoods in its
   colour (bit sets), independently of the sum-free test; and the arithmetic the paper states holds: Chung's
   recurrence R_k(3) >= 3 R_(k-1)(3) + R_(k-3)(3) - 3 with R5(3) >= 162 and R3(3) = 17 gives 500, and the base
   2 * 160 + 1 = 321 of the cited bound S(k) >= c 321^(k/5) has a fifth root above 3.17176. test_passed is 1 if all
   three hold.
4. Beside the test, none of it counted: the sizes of the sets; the depth d(P) and e-depth D(P) (Fredricksen and
   Sweet's measures: the largest least element of a set, under every multiplier m prime to 161); whether the
   partition multiplied at that m is again symmetric and sum-free; and the paper's earlier bounds as it states them
   (157 <= S(5) <= 321, R4(3) between 51 and 65), read as statements, not computed.

Controls (controls_passed counts those that behave as stated): the triangle test finds the triangle in a colouring
with 1, 2 and 3 in one set and none in the colouring of K14 from a sum-free partition of {1, ..., 13} into 3; on 20
seed-drawn perturbations of the partition (one listed number, with its partner, moved to another set) the sum-free and
triangle tests agree on every one and catch at least one; and the exhaustive search finds S(1), S(2) and S(3) as 1, 4
and 13.

What it cannot check: that the bounds were new in 1994, the cited inequalities themselves (Abbott and Hanson, Abbott
and Moser, Chung), and the paper's account of its heuristic search (about 10,000 partitions of [1, 160], four of them
symmetric).

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 schur/exoo.py
"""

import hashlib
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("schur_fs", os.path.join(HERE, "fs.py"))
FS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(FS)

INPUT = ("exoo-ejc-1-r8.pdf", "d56540f55003a94585f0f79ee338792ee6e850ea03de4ec77ebf854d91f35fb4", 92776)
N, K, HALF = 160, 5, 80
STATEMENTS = (
    "sets of a sum-free partition of [1",
    "always belong to the same set), only the integers",
    "from 1 to 80 are listed.",
    "160. It follows that",
    "162. From [1] and",
    "3 proved in [3] we also have",
    "(3) = 17; the current bounds on",
)
EARLIER = ("(5) are 157", "321, the lower bound", "(3) are 51 and 65 [5].")
PERTURBATIONS = 20
OUTPUTS = ("statements", "listed", "s5", "s5_sums", "ramsey", "k161_triangles", "derived", "sizes", "e_depth",
           "earlier", "small_values", "conditions_met", "conditions_total", "test_passed", "controls_passed",
           "controls_total")
LIMIT = 200


class Refused(Exception):
    pass


def read_input(inputs):
    name, sha, size = INPUT
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha or len(data) != size:
        raise Refused(f"{name}: sha256 {got} ({len(data)} bytes), not the registered {sha} ({size})")
    return data


def document_lines(data):
    """Every line of the document in order, the page headers dropped."""
    out = []
    for stream in FS.content_streams(data):
        lines = FS.text_lines(stream)
        k = 0
        while k < len(lines):
            if lines[k] == "the electronic journal of combinatorics 1 (1994), #R8":
                k += 1
                if k < len(lines) and re.fullmatch(r"\d+", lines[k]):
                    k += 1
                continue
            out.append(lines[k])
            k += 1
    return out


def statements_found(lines, statements=STATEMENTS):
    flat = " ".join(lines)
    return {s: s in flat for s in statements}


def read_partition(lines):
    try:
        at = next(i for i, line in enumerate(lines) if line.endswith("from 1 to 80 are listed."))
    except StopIteration:
        raise Refused("no line ending 'from 1 to 80 are listed.'")
    sets = []
    for line in lines[at + 1:]:
        if len(sets) == K:
            break
        m = re.fullmatch(r"Set (\d+): ?([\d ]*)", line)
        if not m:
            if sets:
                raise Refused(f"set {len(sets) + 1} expected, found {line[:40]!r}")
            continue
        if int(m.group(1)) != len(sets) + 1:
            raise Refused(f"set {m.group(1)} out of order")
        sets.append([int(x) for x in m.group(2).split()])
    if len(sets) != K:
        raise Refused(f"{len(sets)} sets read, not {K}")
    listed = [x for s in sets for x in s]
    if sorted(listed) != list(range(1, HALF + 1)):
        raise Refused("the listing is not 1..80 once each: a reading error")
    return sets


def expand(listed):
    """The paper's rule: a listed i stands for i and 161 - i."""
    return [sorted({x for i in s for x in (i, N + 1 - i)}) for s in listed]


def derived():
    chung = 3 * 162 + 17 - 3
    base = 2 * N + 1
    root = base ** 0.2
    return {"r6": chung, "r6_ok": chung >= 500, "base": base, "root": root, "root_ok": base > 3.17176 ** 5}


def conditions(found):
    d = found["derived"]
    return {
        "S(5) >= 160: a partition of {1..160} into 5 sum-free sets": found["partition"] and found["sums"] == 0,
        "R5(3) >= 162: the colouring of K161 has no triangle of one colour": found["triangles"] == 0,
        "the derived bounds follow by the arithmetic stated (500; 321^(1/5) > 3.17176)": d["r6_ok"] and d["root_ok"],
    }


def perturb(listed, st):
    k = len(listed)
    src = st.below(k)
    while not listed[src]:
        src = st.below(k)
    x = listed[src][st.below(len(listed[src]))]
    dst = (src + 1 + st.below(k - 1)) % k
    out = [list(s) for s in listed]
    out[src].remove(x)
    out[dst].append(x)
    return expand(out), x, src, dst


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    data = read_input(inputs)
    lines = document_lines(data)
    stmts = statements_found(lines)
    earlier = statements_found(lines, EARLIER)
    listed = read_partition(lines)
    sets = expand(listed)
    missing, repeated, stray = FS.coverage(sets, N)
    tri, edges = FS.triangles(sets, N)
    d_e, m = FS.e_depth(sets, N)
    mp = FS.multiply(sets, m, N)
    found = {"partition": not missing and not repeated and not stray, "sums": sum(FS.sums_inside(s) for s in sets),
             "sums_by_set": [FS.sums_inside(s) for s in sets], "triangles": tri, "edges": edges,
             "sizes": [len(s) for s in sets], "listed_sizes": [len(s) for s in listed], "depth": FS.depth(sets),
             "e_depth": d_e, "multiplier": m,
             "mp_symmetric_sum_free": FS.symmetric(mp, N) and FS.is_partition(mp, N)
             and all(FS.sums_inside(s) == 0 for s in mp),
             "derived": derived(), "missing": missing[:10], "repeated": repeated[:10]}
    cond = conditions(found)
    smalls = {k: FS.schur_number(k) for k in (1, 2, 3)}

    ctl, ctl_detail = {}, {}
    tri_bad, _ = FS.triangles([[1, 2, 3]], 3)
    p13 = FS.schur_search(3, 13)
    tri13, _ = FS.triangles(p13, 13)
    ctl["the triangle test finds the triangle of {1, 2, 3} and none in K14 from a partition of 1..13"] = (
        tri_bad >= 1 and p13 is not None and tri13 == 0)
    st = FS.Stream(seed, "exoo/perturb")
    agree, caught, rows = 0, 0, []
    for _ in range(PERTURBATIONS):
        psets, x, src, dst = perturb(listed, st)
        bad_sum = sum(FS.sums_inside(s) for s in psets) > 0
        ptri, _ = FS.triangles(psets, N)
        agree += int(bad_sum == (ptri > 0))
        caught += int(bad_sum and ptri > 0)
        rows.append({"moved": x, "from": src + 1, "to": dst + 1, "sums": bad_sum, "triangles": ptri})
    ctl["on 20 seed-drawn perturbations the two tests agree, and some are caught"] = (
        agree == PERTURBATIONS and caught >= 1)
    ctl_detail["perturbations_caught"] = caught
    ctl_detail["perturbations"] = rows
    ctl["exhaustive search: S(1) = 1, S(2) = 4, S(3) = 13"] = smalls == {1: 1, 2: 4, 3: 13}

    dv = found["derived"]
    values = {
        "statements": (f"the listing rule, the bounds and R3(3) = 17, in the paper: {sum(stmts.values())} of "
                       f"{len(stmts)}"),
        "listed": "listed: 80 numbers in 5 sets (" + ", ".join(map(str, found["listed_sizes"])) + ")",
        "s5": (f"160 into 5: {'each of 1..160 once' if found['partition'] else 'not a partition'}, sets of "
               + ", ".join(map(str, found["sizes"]))),
        "s5_sums": found["sums"],
        "ramsey": f"monochromatic triangles in K161: {tri} over {edges} edges in 5 colours",
        "k161_triangles": tri,
        "derived": (f"Chung's recurrence: 3*162 + 17 - 3 = {dv['r6']}; (2*160 + 1)^(1/5) = {dv['root']:.6f} "
                    f"{'>' if dv['root_ok'] else '<='} 3.17176"),
        "sizes": (f"the largest set has {max(found['sizes'])} elements (none the paper found had more than 44); "
                  f"d(P) = {found['depth']}"),
        "e_depth": (f"D(P) = {d_e} (m = {m}); multiplied, symmetric and sum-free: "
                    f"{'yes' if found['mp_symmetric_sum_free'] else 'no'}"),
        "earlier": (f"the earlier bounds as it states them (157, 321; 51 and 65): {sum(earlier.values())} of "
                    f"{len(earlier)}"),
        "small_values": "S(1), S(2), S(3) by exhaustive search: " + ", ".join(str(smalls[k]) for k in (1, 2, 3)),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for key, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")
    detail = {"input": {"name": INPUT[0], "sha256": INPUT[1], "bytes": INPUT[2]}, "statements": stmts,
              "earlier": earlier, "conditions": cond, "controls": ctl, "control_detail": ctl_detail,
              "listed": listed, "found": found, "small_values": smalls}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except (Refused, FS.Refused) as e:
        sys.exit(f"exoo: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
