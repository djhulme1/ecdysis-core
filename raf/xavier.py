#!/usr/bin/env python3
"""RAFs in the metabolism of two ancient autotrophs, recomputed from the networks Xavier et al. released.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:59fba407e0fadf21) is from Xavier,
Hordijk, Kauffman, Steel & Martin, "Autocatalytic chemical networks at the origin of metabolism", Proc. R. Soc. B
287(1922), 20192377 (2020): "RAFs in the metabolism of ancient anaerobic autotrophs that live from H2 and CO2
provided with small-molecule catalysts generate acetyl-CoA as well as amino acids and bases, the monomeric components
of protein and RNA, but amino acids and bases without organic catalysts do not generate metabolic RAFs."

Its registered test: refuted if, by the maxRAF algorithm on the paper's released networks (Dataset S1, catalysis
rules as annotated, the pooling and spontaneous catalysts always in the food set), the maxRAF of the acetogen's or
the methanogen's network with Table S1's food set 3 (small molecules, abiotic carbon, organic cofactors) produces no
acetyl-CoA, no proteinogenic amino acid or no base outside the food set (a nucleobase, or a G, C or U
ribonucleotide); or if food set 5 (food set 2, 20 amino acids and five bases, no organic cofactors) gives a maxRAF
over a tenth of food set 3's in any of the three networks.

The inputs are the paper's own supplementary files on figshare (CC BY 4.0), each checked against its SHA-256 and read
with the standard library as data (the workbooks' XML parsed, nothing in them run): Dataset S1, the three networks
with their catalysis rules; Dataset S4, the paper's own input file for the global network with food set 3; and
Dataset S2, the paper's maxRAFs, compared beside the test. Every rule below was fixed before any maxRAF was computed;
the seed is not used, as nothing here is random.

1. The networks. Dataset S1's sheets S1A (the global O2-independent prokaryotic network), S1B (Moorella
   thermoacetica, the acetogen) and S1C (Methanococcus maripaludis, the methanogen): from the third row, each row a
   reaction with its KEGG number (column B), its equation in compound ids (C) and its catalysis rule (E), the header
   row as the paper wrote it. An equation is "left <=> right" (two-way) or "left => right" (one-way), each side terms
   joined by " + ", a term an id with or without a whole-number coefficient (coefficients do not matter to a RAF).
   A rule is names joined by whitespace (any one of the alternatives catalyses) and by "&" (all are needed), "&"
   binding tighter, with parentheses grouping. The counts must be the paper's: 5,994, 1,193 and 920 reactions, and
   45 pooling reactions in each (numbers beginning "R_", catalysed by "Pooling"), which join synonymous cofactors
   into the pools the rules name. Anything else is refused.
2. The food sets, Table S1's five. Food set 3 is Dataset S4's food set, as the paper ran it (68 names). Food set 2
   is food set 3 without its 25 organic cofactors (ORGANIC below, as Table S1 lists them), 43; food set 1 is food set
   2 without the abiotic organic carbon (acetate, formate, pyruvate and methanol), 39; food set 4 is food set 3 with
   the generic catalyst "Peptide" (KEGG C00012, by the name the rules give it), 69; food set 5 is food set 2 with
   the 20 proteinogenic amino acids and the bases adenine, guanine, cytosine, thymine and uracil, 68. "Pooling" and
   "Spontaneous" are in all of them.
3. The maxRAF, by Hordijk and Steel's algorithm as the paper's supplementary methods state it (its Algorithms 1 and
   2): a two-way reaction is two one-way halves with the same rule. Starting with every half, compute the closure of
   the food under the current halves (a half fires when all its reactants are present, adding its products, until
   nothing is added), then drop every half with a reactant outside the closure or no alternative of its rule wholly
   inside it; repeat until nothing is dropped. A reaction is in the maxRAF when either half remains. Its size counts
   reactions, the pooling reactions left out, as the paper counts them.
4. What a maxRAF generates: the closure of the food under the maxRAF's halves, less the food.
5. The test's nine conditions: for each of the acetogen and the methanogen with food set 3, the maxRAF generates
   acetyl-CoA (C00024), at least one of the 20 proteinogenic amino acids, and at least one base outside the food
   set: a nucleobase, or a ribonucleotide of guanine, cytosine or uracil (GMP, GDP, GTP, CMP, CDP, CTP, UMP, UDP,
   UTP; the adenine nucleotides are left out, as ATP and AMP are food); and for each of the three networks, the
   maxRAF with food set 5 has at most a tenth as many reactions as with food set 3. test_passed is 1 if all nine
   hold.
6. Beside the test:
   - all fifteen maxRAF sizes against Table S1's, and each maxRAF's reactions against Dataset S2's list;
   - the three networks with each reaction as Dataset S4 writes it: the paper's own input file holds S1A's
     reactions with the same rules, but writes some that S1A gives as two-way in one direction only, and a few that
     S1B and S1C write one way in the other; so each network is run again, its reactions taken from S4 by number,
     with all five food sets, against Table S1 and Dataset S2 (the test reads Dataset S1, as registered);
   - the amino acids and bases each autotroph's maxRAF generates with food set 3;
   - the primordial network: the reactions in both autotrophs' maxRAFs with food set 3 (the paper: 172), and that
     network's own maxRAF with the same food (the paper: 120 reactions, cysteine its only amino acid);
   - food set 3 without NAD+ and without ATP, each network (the paper: NAD+'s removal costs about half the maxRAF,
     ATP's nothing).
7. Controls: Dataset S4 holds S1A's reactions in S1A's order, with the same rules and the same compounds on each
   side, directions apart, and its food set is exactly food set 1, the abiotic carbon and the organic cofactors as
   transcribed here; every maxRAF found is a RAF, from which the algorithm would drop nothing more; a small system
   whose maxRAF is known (TOY_TEXT: a two-way reaction reached backwards, "&" rules, a parenthesised rule, a reaction
   catalysed by its own product) gives it; and each network's maxRAF grows with the food (food set 1 within 2 within
   3 within 4).

The primordial network (rule 6) takes each reaction as the acetogen's network writes it, with its pooling reactions,
for Dataset S1's versions and for S4's.

Added after the trial, beside the test only (the trial ran under a seed of Imago's own, before any was issued): food
set 4's catalyst by the name the rules use, "Peptide" (the rules never name C00012, so the trial's food set 4 was food
set 3); and the autotrophs' networks with S4's versions of their reactions, the global network's having been run so
from the start. The test's nine conditions and their inputs did not change.

What it cannot check: the networks' curation (which KEGG reactions are ancient, which cofactors catalyse them) and the
chemistry itself; a RAF is a property of the network as annotated.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 raf/xavier.py
"""

import hashlib
import io
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

INPUTS = {
    "s1": ("rspb20192377_si_002.xlsx", "e3ace239eb9963bc99d70f888db5078aefbcc7a1ceae6901926f48a7de2c2381"),
    "s4": ("rspb20192377_si_005.txt", "85fc8b6ce32932cf346a2d30a3a6ddc0e6e43b469abdb289a7471098f99b65ff"),
    "s2": ("rspb20192377_si_003.xlsx", "51cd21347796931689e004d8eca825fb574ddd1c78e9d2364f9fe74ab5bd11fb"),
}
NETWORKS = (("global", "S1A", 5994), ("Ace", "S1B", 1193), ("Met", "S1C", 920))
HEADER = {"B": "RN", "C": "Equation_ids", "E": "Cofactors_rule"}
POOLING = 45
ALWAYS = ("Pooling", "Spontaneous")
# Table S1's organic cofactors, in Dataset S4's spelling and order.
ORGANIC = ("C00061", "C00018", "C00068", "C00003", "C05924", "C00541", "C00113", "C16241", "C00002", "C00120", "C00051",
           "C15494", "C00019", "Other_quinones", "C00101", "dipyrromethane", "TTQ", "C04054", "C00020", "C06021",
           "C01134", "C00828", "C00010", "C00138", "C00139")
ABIOTIC = ("C00033", "C00058", "C00022", "C00132")          # acetate, formate, pyruvate, methanol
PEPTIDE = "Peptide"                                          # the name the rules give it (KEGG C00012)
AMINO = {"C00037": "Gly", "C00041": "Ala", "C00049": "Asp", "C00152": "Asn", "C00097": "Cys", "C00188": "Thr",
         "C00025": "Glu", "C00064": "Gln", "C00062": "Arg", "C00148": "Pro", "C00065": "Ser", "C00073": "Met",
         "C00079": "Phe", "C00082": "Tyr", "C00078": "Trp", "C00135": "His", "C00047": "Lys", "C00123": "Leu",
         "C00407": "Ile", "C00183": "Val"}
NUCLEOBASES = {"C00147": "adenine", "C00242": "guanine", "C00380": "cytosine", "C00178": "thymine", "C00106": "uracil"}
GCU = {"C00144": "GMP", "C00035": "GDP", "C00044": "GTP", "C00055": "CMP", "C00112": "CDP", "C00063": "CTP",
       "C00105": "UMP", "C00015": "UDP", "C00075": "UTP"}
BASES = {**NUCLEOBASES, **GCU}
ACCOA, NAD, ATP = "C00024", "C00003", "C00002"
TABLE_S1 = {"FS1": (39, 8, 4, 4), "FS2": (43, 16, 9, 8), "FS3": (68, 1335, 394, 209), "FS4": (69, 2603, 493, 307),
            "FS5": (68, 33, 19, 14)}                         # food set size; maxRAF sizes, global, Ace, Met
S2_SHEETS = {"FS1": "FS1.small molecules", "FS2": "FS2. FS1 + abiotic carbon", "FS3": "FS3. FS2 + organic cofactors",
             "FS4": "FS4. FS3 + Peptide", "FS5": "FS5. FS2 + amino acids & bases"}
PRIMORDIAL = (172, 120)                                      # the paper's intersection, and that network's maxRAF
NAME = re.compile(r"[A-Za-z0-9_\-]+")
NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
OUTPUTS = ("networks", "food_sets", "maxraf_global", "maxraf_ace", "maxraf_met", "table_s1", "dataset_s2",
           "ace_fs3_generates", "met_fs3_generates", "as_s4_fs3_generates", "fs5_against_fs3", "primordial",
           "without_nad_atp", "controls_passed", "controls_total", "conditions_met", "conditions_total", "test_passed")
TAGS = ("global", "Ace", "Met")
LIMIT = 200


class Refused(Exception):
    pass


# -- reading -------------------------------------------------------------------------------------------------------

def read_bytes(path, sha256):
    with open(path, "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha256:
        raise Refused(f"{path}: sha256 {got}, not the registered {sha256}")
    return data


def sheets(data):
    """{sheet name: [{column letters: text}]} for every sheet of a workbook, shared and inline strings and numbers."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("x:si", NS):
                shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["x"])))
        book = ET.fromstring(z.read("xl/workbook.xml"))
        rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
        out = {}
        for sh in book.find("x:sheets", NS):
            target = rels[sh.get("{%s}id" % NS["r"])].lstrip("/")
            target = target if target.startswith("xl/") else "xl/" + target
            root = ET.fromstring(z.read(target))
            rows = []
            for row in root.find("x:sheetData", NS).findall("x:row", NS):
                cells = {}
                for c in row.findall("x:c", NS):
                    col = re.match(r"[A-Z]+", c.get("r")).group(0)
                    kind, v = c.get("t"), c.find("x:v", NS)
                    if kind == "inlineStr":
                        cells[col] = "".join(t.text or "" for t in c.iter("{%s}t" % NS["x"]))
                    elif kind == "s" and v is not None:
                        cells[col] = shared[int(v.text)]
                    elif v is not None:
                        cells[col] = v.text
                rows.append(cells)
            out[sh.get("name")] = rows
    return out


def parse_equation(eq, where):
    m = re.fullmatch(r"(.+?) (<=>|=>) (.+)", eq or "")
    if not m:
        raise Refused(f"{where}: equation {eq!r} is neither 'left <=> right' nor 'left => right'")
    sides = []
    for side in (m.group(1), m.group(3)):
        ids = []
        for term in side.split(" + "):
            parts = term.split(" ")
            if len(parts) == 2 and re.fullmatch(r"[1-9][0-9]*", parts[0]):
                parts = parts[1:]
            if len(parts) != 1 or not NAME.fullmatch(parts[0]):
                raise Refused(f"{where}: term {term!r} of {eq!r}")
            ids.append(parts[0])
        sides.append(frozenset(ids))
    return sides[0], sides[1], m.group(2) == "<=>"


def parse_rule(rule, where):
    """A rule as its alternatives, each the set of names all needed: an OR of ANDs."""
    tokens = re.findall(r"\(|\)|&|\s+|[^\s()&]+", rule or "")
    if "".join(tokens) != (rule or ""):
        raise Refused(f"{where}: rule {rule!r}")
    tokens = [t for t in tokens if not t.isspace()]
    for t in tokens:
        if t not in "()&" and not NAME.fullmatch(t):
            raise Refused(f"{where}: name {t!r} in rule {rule!r}")
    pos = 0

    def alternatives():                  # alternatives := term (term)*      (juxtaposition is OR)
        out = term()
        while pos < len(tokens) and tokens[pos] not in ")&":
            out = out | term()
        return out

    def term():                          # term := factor ("&" factor)*
        nonlocal pos
        out = factor()
        while pos < len(tokens) and tokens[pos] == "&":
            pos += 1
            right = factor()
            out = {a | b for a in out for b in right}
        return out

    def factor():                        # factor := name | "(" alternatives ")"
        nonlocal pos
        if pos >= len(tokens):
            raise Refused(f"{where}: rule {rule!r} ends early")
        t = tokens[pos]
        if t == "(":
            pos += 1
            out = alternatives()
            if pos >= len(tokens) or tokens[pos] != ")":
                raise Refused(f"{where}: unbalanced rule {rule!r}")
            pos += 1
            return out
        if t in ")&":
            raise Refused(f"{where}: rule {rule!r} has {t!r} where a name belongs")
        pos += 1
        return {frozenset([t])}

    if not tokens:
        raise Refused(f"{where}: an empty rule")
    out = alternatives()
    if pos != len(tokens):
        raise Refused(f"{where}: rule {rule!r} does not parse to its end")
    return frozenset(out)


def checked(lines, sheet, expected):
    """[(number, left, right, two_way, rule)] from (where, number, equation, rule) lines, checked against rule 1."""
    out, seen = [], set()
    for where, number, equation, rule in lines:
        if not number or not NAME.fullmatch(number) or number in seen:
            raise Refused(f"{where}: reaction number {number!r} missing, malformed or repeated")
        seen.add(number)
        left, right, two_way = parse_equation(equation, where)
        out.append((number, left, right, two_way, parse_rule(rule, where)))
    pooling = [x for x in out if x[0].startswith("R_")]
    if len(pooling) != POOLING or any(x[4] != frozenset([frozenset(["Pooling"])]) for x in pooling):
        raise Refused(f"{sheet}: {len(pooling)} pooling reactions, not {POOLING} catalysed by Pooling alone")
    if len(out) - POOLING != expected:
        raise Refused(f"{sheet}: {len(out) - POOLING} reactions besides pooling, not the paper's {expected}")
    return out


def network(rows, sheet, expected):
    """A sheet of Dataset S1, from its third row, its header row the paper's."""
    if len(rows) < 3 or any(rows[1].get(k) != v for k, v in HEADER.items()):
        raise Refused(f"{sheet}: header row {rows[1] if len(rows) > 1 else None} is not the paper's")
    return checked(((f"{sheet} row {i}", r.get("B"), r.get("C"), r.get("E")) for i, r in enumerate(rows[2:], start=3)),
                   sheet, expected)


def s4_network(reactions):
    """The global network as Dataset S4, the paper's own input file, writes it."""
    return checked(((f"Dataset S4 {n}", n, eq, rule) for n, eq, rule in reactions), "Dataset S4", NETWORKS[0][2])


def s4_file(text):
    """Dataset S4: its food set (the ids, in order) and its reactions as (number, equation, rule)."""
    if not text.startswith("<meta-data>"):
        raise Refused("Dataset S4 does not start with <meta-data>")
    parts = re.split(r"^<(molecules|food set|reactions)>\s*$", text, flags=re.M)
    if len(parts) != 7 or parts[1::2] != ["molecules", "food set", "reactions"]:
        raise Refused("Dataset S4's sections are not <molecules>, <food set>, <reactions>")
    meta = dict(re.findall(r"^(\w+)\s*=\s*(\d+)\s*$", parts[0], flags=re.M))
    food = [line.rsplit("\t", 1)[1].strip() for line in parts[4].splitlines() if line.strip()]
    reactions = []
    for line in parts[6].splitlines():
        if not line.strip():
            continue
        cells = line.split("\t")
        if len(cells) != 4:
            raise Refused(f"Dataset S4 reaction line {line[:80]!r} has {len(cells)} fields")
        reactions.append((cells[0], cells[1], cells[2]))
    if int(meta.get("nrFoodSet", -1)) != len(food) or int(meta.get("nrReactions", -1)) != len(reactions):
        raise Refused(f"Dataset S4 counts {meta} disagree with its {len(food)} food and {len(reactions)} reactions")
    return food, reactions


# -- the RAF algorithm -----------------------------------------------------------------------------------------------

def halves(net):
    """One-way halves (reaction index, reactants, products, rule) of a network: a two-way reaction gives two."""
    out = []
    for k, (number, left, right, two_way, rule) in enumerate(net):
        out.append((k, left, right, rule))
        if two_way:
            out.append((k, right, left, rule))
    return out


def closure(food, hs, alive):
    """The food's closure under the alive halves: a half fires when all its reactants are present."""
    W = set(food)
    missing = {}
    by_reactant = {}
    queue = []
    for h in alive:
        need = [m for m in hs[h][1] if m not in W]
        missing[h] = len(need)
        for m in need:
            by_reactant.setdefault(m, []).append(h)
        if not need:
            queue.append(h)
    while queue:
        h = queue.pop()
        for m in hs[h][2]:
            if m not in W:
                W.add(m)
                for g in by_reactant.get(m, ()):
                    missing[g] -= 1
                    if missing[g] == 0:
                        queue.append(g)
    return W


def supported(h, hs, W):
    return all(m in W for m in hs[h][1]) and any(alt <= W for alt in hs[h][3])


def max_raf(food, hs):
    """The alive halves of the maxRAF (Hordijk & Steel), and the closure under them."""
    alive = set(range(len(hs)))
    while True:
        W = closure(food, hs, alive)
        keep = {h for h in alive if supported(h, hs, W)}
        if keep == alive:
            return alive, W
        alive = keep


def reactions_of(alive, hs, net):
    """The maxRAF's reactions by number, a two-way reaction once, pooling reactions left out."""
    return sorted({net[hs[h][0]][0] for h in alive} - {x[0] for x in net if x[0].startswith("R_")})


def food_sets(fs3):
    fs3 = list(fs3)
    fs2 = [m for m in fs3 if m not in ORGANIC]
    fs1 = [m for m in fs2 if m not in ABIOTIC]
    sets = {"FS1": fs1, "FS2": fs2, "FS3": fs3, "FS4": fs3 + [PEPTIDE], "FS5": fs2 + list(AMINO) + list(NUCLEOBASES)}
    for k, v in sets.items():
        if len(set(v)) != len(v) or len(v) != TABLE_S1[k][0] or not all(a in v for a in ALWAYS):
            raise Refused(f"{k}: {len(v)} names (or repeats, or no Pooling and Spontaneous), not Table S1's "
                          f"{TABLE_S1[k][0]}")
    return {k: frozenset(v) for k, v in sets.items()}


# -- controls --------------------------------------------------------------------------------------------------------

# A small system with a known maxRAF, from the food a, b and c: r1 and r2 catalyse each other; r3 is two-way and
# reached backwards, from y, needing x and c together; r4 needs d, which nothing makes; r5 needs q, which nothing
# makes; r6 is catalysed by its own product u with b, the other alternative (v with b) never available. The maxRAF is
# r1, r2, r3 and r6, generating u, w, x and y.
TOY_TEXT = (("r1", "a + b => x", "y"), ("r2", "x + c => y", "x q"), ("r3", "w <=> y", "x&c"), ("r4", "y => z", "z&d"),
            ("r5", "q => v", "a"), ("r6", "x => u", "(v u)&b"))
TOY_FOOD, TOY_MAXRAF, TOY_MAKES = frozenset("abc"), ["r1", "r2", "r3", "r6"], {"u", "w", "x", "y"}


def toy():
    return [(n,) + parse_equation(eq, n) + (parse_rule(rule, n),) for n, eq, rule in TOY_TEXT]


def is_raf(food, hs, alive):
    """Every alive half has its reactants and one alternative of its rule in the closure under the alive halves, so
    the maxRAF algorithm would drop nothing more."""
    W = closure(food, hs, alive)
    return all(supported(h, hs, W) for h in alive)


def against_s1a(s1a, s4net):
    """Dataset S4's network against S1A: whether they hold the same reactions in the same order, with the same rules
    and the same compounds on each side up to direction, and how many reactions they write in different directions
    (two-way in one and one-way in the other, or reversed)."""
    if len(s1a) != len(s4net):
        return False, None
    same, directions = True, 0
    for (number, left, right, two_way, rule), (n4, l4, r4, t4, rule4) in zip(s1a, s4net):
        if number != n4 or rule != rule4 or {left, right} != {l4, r4}:
            same = False
        elif (left, right, two_way) != (l4, r4, t4):
            directions += 1
    return same, directions


# -- the run ---------------------------------------------------------------------------------------------------------

def names_of(ids, table):
    return [table[i] for i in table if i in ids]


def as_s4(net, s4net):
    """A network with each reaction as Dataset S4 writes it, by number."""
    by = {x[0]: x for x in s4net}
    missing = [x[0] for x in net if x[0] not in by]
    if missing:
        raise Refused(f"Dataset S4 lacks {len(missing)} reactions, {missing[:3]}")
    return [by[x[0]] for x in net]


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    data = {k: read_bytes(os.path.join(inputs, name), sha) for k, (name, sha) in INPUTS.items()}
    s1 = sheets(data["s1"])
    nets = {tag: network(s1.get(sheet, []), sheet, n) for tag, sheet, n in NETWORKS}
    s4_food, s4_reactions = s4_file(data["s4"].decode("utf-8"))
    F = food_sets(s4_food)
    s2 = sheets(data["s2"])
    s4net = s4_network(s4_reactions)
    # The test reads Dataset S1's three networks; beside it, the same three with each reaction as S4 writes it.
    every = {(tag, v): (net if v == "S1" else as_s4(net, s4net)) for tag, net in nets.items() for v in ("S1", "S4")}

    hs = {key: halves(net) for key, net in every.items()}
    raf, gen, alive_of = {}, {}, {}
    for key in every:
        for fs, food in F.items():
            alive, W = max_raf(food, hs[key])
            alive_of[(key, fs)] = alive
            raf[(key, fs)] = reactions_of(alive, hs[key], every[key])
            gen[(key, fs)] = W - food

    # The test.
    cond = {}
    for tag, label in (("Ace", "acetogen"), ("Met", "methanogen")):
        g = gen[((tag, "S1"), "FS3")]
        cond[f"{label}, food set 3: acetyl-CoA"] = ACCOA in g
        cond[f"{label}, food set 3: a proteinogenic amino acid"] = any(a in g for a in AMINO)
        cond[f"{label}, food set 3: a base"] = any(b in g for b in BASES)
    for tag in TAGS:
        k = (tag, "S1")
        cond[f"{tag}: food set 5 at most a tenth of food set 3"] = 10 * len(raf[(k, "FS5")]) <= len(raf[(k, "FS3")])

    # Beside: Table S1 and Dataset S2.
    hits = {v: [0, 0] for v in ("S1", "S4")}           # sizes as Table S1 prints them; lists as Dataset S2 gives them
    worst = {"S1": 0, "S4": 0}
    s2_rows = {}
    for fs, sheet in S2_SHEETS.items():
        rows = s2.get(sheet)
        if not rows or [rows[0].get(c) for c in "ABC"] != ["Global", "Ace", "Met"]:
            raise Refused(f"Dataset S2 sheet {sheet!r} missing or not headed Global, Ace, Met")
        for i, tag in enumerate(TAGS):
            col = "ABC"[i]
            listed = sorted({r[col] for r in rows[1:] if r.get(col)})
            for v in ("S1", "S4"):
                ours = raf[((tag, v), fs)]
                diff = len(set(listed) ^ set(ours))
                hits[v][0] += int(len(ours) == TABLE_S1[fs][1 + i])
                hits[v][1] += int(diff == 0)
                worst[v] = max(worst[v], diff)
                s2_rows[f"{fs} {tag} {v}"] = {"ours": len(ours), "table_s1": TABLE_S1[fs][1 + i],
                                              "dataset_s2": len(listed), "only_ours": sorted(set(ours) - set(listed)),
                                              "only_dataset_s2": sorted(set(listed) - set(ours))}

    # Beside: the primordial network, and NAD+ and ATP.
    prim = {}
    for v in ("S1", "S4"):
        both = sorted(set(raf[(("Ace", v), "FS3")]) & set(raf[(("Met", v), "FS3")]))
        rows_by = {x[0]: x for x in every[("Ace", v)]}
        pnet = [rows_by[n] for n in both] + [x for x in every[("Ace", v)] if x[0].startswith("R_")]
        phs = halves(pnet)
        palive, pW = max_raf(F["FS3"], phs)
        allW = closure(F["FS3"], phs, set(range(len(phs))))
        prim[v] = {"both": both, "maxraf": reactions_of(palive, phs, pnet),
                   "amino_acids_of_its_maxraf": names_of(pW - F["FS3"], AMINO),
                   "bases_of_its_maxraf": names_of(pW - F["FS3"], BASES),
                   "amino_acids_of_both": names_of(allW - F["FS3"], AMINO),
                   "bases_of_both": names_of(allW - F["FS3"], BASES)}
    without = {}
    for key in every:
        for m, mname in ((NAD, "NAD+"), (ATP, "ATP")):
            alive, _ = max_raf(F["FS3"] - {m}, hs[key])
            without[(key, mname)] = len(reactions_of(alive, hs[key], every[key]))

    # Controls.
    toy_net = toy()
    toy_hs = halves(toy_net)
    toy_alive, toy_W = max_raf(TOY_FOOD, toy_hs)
    partition = len(s4_food) == len(F["FS1"]) + len(ABIOTIC) + len(ORGANIC) and \
        set(s4_food) == set(F["FS1"]) | set(ABIOTIC) | set(ORGANIC)
    same, directions = against_s1a(nets["global"], s4net)
    differ = {tag: sum(1 for a, b in zip(nets[tag], every[(tag, "S4")]) if a != b) for tag in TAGS}
    controls = {
        "Dataset S4 holds S1A's reactions (rules and compounds; directions apart), and its food set is food set 1, "
        "the abiotic carbon and the cofactors": same and partition,
        "every maxRAF found is a RAF, from which nothing more can be dropped":
            all(is_raf(F[fs], hs[key], alive_of[(key, fs)]) for key in every for fs in F),
        "the small system's maxRAF is the known one":
            reactions_of(toy_alive, toy_hs, toy_net) == TOY_MAXRAF and set(toy_W - TOY_FOOD) == TOY_MAKES,
        "each maxRAF grows with the food": all(set(raf[(k, a)]) <= set(raf[(k, b)]) for k in every
                                               for a, b in (("FS1", "FS2"), ("FS2", "FS3"), ("FS3", "FS4"))),
    }

    def sizes(tag):
        return "; ".join(f"{'Dataset S1' if v == 'S1' else 'as S4'} " + ", ".join(str(len(raf[((tag, v), fs)]))
                                                                                for fs in F) for v in ("S1", "S4"))

    def generates(key):
        g = gen[(key, "FS3")]
        return (f"acetyl-CoA {'yes' if ACCOA in g else 'no'}; amino acids {len([a for a in AMINO if a in g])}: "
                f"{' '.join(names_of(g, AMINO)) or 'none'}; bases: {' '.join(names_of(g, BASES)) or 'none'}")

    def brief(key):
        g = gen[(key, "FS3")]
        return (f"acetyl-CoA {'yes' if ACCOA in g else 'no'}, {len([a for a in AMINO if a in g])} amino acids, "
                f"{len([b for b in BASES if b in g])} bases")

    values = {
        "networks": ("; ".join(f"{tag} {len(net) - POOLING}" for tag, net in nets.items())
                     + f" reactions (+{POOLING} pooling each); S4 writes " + ", ".join(
                         f"{differ[t]}" for t in TAGS) + " of them in another direction"),
        "food_sets": ", ".join(f"{fs} {len(food)}" for fs, food in F.items()),
        "maxraf_global": sizes("global"), "maxraf_ace": sizes("Ace"), "maxraf_met": sizes("Met"),
        "table_s1": f"Dataset S1's networks {hits['S1'][0]} of 15 sizes as printed; as S4 writes them {hits['S4'][0]} of 15",
        "dataset_s2": (f"Dataset S1's networks {hits['S1'][1]} of 15 maxRAFs as listed (the largest difference "
                       f"{worst['S1']}); as S4 writes them {hits['S4'][1]} of 15 (largest {worst['S4']})"),
        "ace_fs3_generates": generates(("Ace", "S1")), "met_fs3_generates": generates(("Met", "S1")),
        "as_s4_fs3_generates": f"Ace {brief(('Ace', 'S4'))}; Met {brief(('Met', 'S4'))}",
        "fs5_against_fs3": "; ".join(f"{v} " + ", ".join(f"{tag} {len(raf[((tag, v), 'FS5')])} of "
                                                          f"{len(raf[((tag, v), 'FS3')])}" for tag in TAGS)
                                     for v in ("S1", "S4")),
        "primordial": "; ".join(f"{v} {len(prim[v]['both'])} in both, its maxRAF {len(prim[v]['maxraf'])} (amino "
                                f"acids {' '.join(prim[v]['amino_acids_of_its_maxraf']) or 'none'})" for v in ("S1", "S4"))
                      + f" (printed {PRIMORDIAL[0]} and {PRIMORDIAL[1]}, Cys)",
        "without_nad_atp": "as S4: " + "; ".join(f"{tag} {len(raf[((tag, 'S4'), 'FS3')])}/{without[((tag, 'S4'), 'NAD+')]}/"
                                                 f"{without[((tag, 'S4'), 'ATP')]}" for tag in TAGS)
                           + " (all, no NAD+, no ATP)",
        "controls_passed": sum(controls.values()), "controls_total": len(controls),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {
        "inputs": {k: {"name": n, "sha256": s} for k, (n, s) in INPUTS.items()},
        "food_sets": {fs: sorted(food) for fs, food in F.items()},
        "conditions": cond, "controls": controls,
        "directions": {"S1A against S4": directions, **{f"{t} against S4": differ[t] for t in TAGS}},
        "maxraf": {f"{fs} {tag} {v}": raf[((tag, v), fs)] for (tag, v) in every for fs in F},
        "generates": {f"{fs} {tag} {v}": {"acetyl-CoA": ACCOA in gen[((tag, v), fs)],
                                           "amino_acids": names_of(gen[((tag, v), fs)], AMINO),
                                           "bases": names_of(gen[((tag, v), fs)], BASES),
                                           "count": len(gen[((tag, v), fs)])}
                      for (tag, v) in every for fs in F},
        "against_table_s1_and_dataset_s2": s2_rows,
        "primordial": prim,
        "without": {f"{tag} {v} {m}": n for ((tag, v), m), n in without.items()},
    }
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
    except Refused as e:
        sys.exit(f"xavier: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
