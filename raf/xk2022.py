#!/usr/bin/env python3
"""Small-molecule RAFs in 6683 prokaryotes, checked from the lists Xavier and Kauffman released.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:c1141d0f109d1202) is from Xavier &
Kauffman, "Small-molecule autocatalytic networks are universal metabolic fossils", Phil. Trans. R. Soc. A 380(2227),
20210244 (2022): "Here, small-molecule reflexively autocatalytic food-generated networks (RAFs) ranging in size from 3
to 619 reactions were found in all of 6683 prokaryotic metabolic networks searched."

Its registered test: refuted if, in the authors' released results (Supplementary Data 4 and 5: each prokaryote's
maxRAF as KEGG reaction ids, rich and NAD medium), any of Supplementary Data 1's 6683 prokaryotes has no rich-medium
maxRAF, or any listed maxRAF is not a RAF of the released global network (Supplementary Data 2, its catalysis rules,
pooling reactions added) with its medium's food set (Supplementary Data 3), or the lists' sizes do not run from 3 to
619 reactions. Its fidelity is "adapted": the release holds each maxRAF, the global network and the food sets but not
the 6683 organisms' own networks, so the test checks each list's RAF property in the global network and the sizes, not
that each list is its organism's maximal RAF.

The inputs are the paper's five supplementary files on figshare (CC BY 4.0), each checked against its SHA-256 and read
with the standard library as data (the workbooks' XML parsed and the archives' text read, nothing in them run). The
readers of equations, rules and workbooks, the closure and the maxRAF algorithm are raf/xavier.py's, unchanged: the
same group's conventions of 2020, which that check reproduced. Every rule below was fixed before any list was read for
its contents; the seed is not used, as nothing here is random.

1. The global network, Supplementary Data 2: a text file whose header line "Reaction_ID<tab>Equation<tab>Catalysts
   <tab>Reaction_Rate" appears once; every nonblank line after it is a reaction of four tab-separated fields, its id
   (unique), its equation, its catalysis rule and a rate (a number, not used: a RAF has no rates). Equations and rules
   are read as raf/xavier.py reads Dataset S1's: "left <=> right" two-way, "left => right" one-way, coefficients
   ignored; a rule names alternatives joined by whitespace and requirements joined by "&", "&" binding tighter,
   parentheses grouping. The pooling reactions are the ids beginning "R_", each catalysed by "Pooling" alone; they join
   synonymous cofactors into the pools the rules name (C00003 => NADs, say). Anything else is refused.
2. The media, Supplementary Data 3: its one sheet, the header in the third row as the paper wrote it (Molecule
   name(s); Molecule ID (KEGG or from this work); Rich medium; NAD medium; Fictional (modelling purposes)), then a
   molecule a row, its id in the second column (unique), a tick or nothing in each medium's column. The rich food is
   the ids ticked as rich medium, the NAD food those ticked as NAD medium; each must hold "Pooling" and "Spontaneous",
   the names the rules give pooling and uncatalysed steps.
3. The prokaryotes, Supplementary Data 1: its one sheet, the header in the third row (KEGG_TAX_ID, CODE, Species_Name,
   Taxonomy, ECs, RNs, Domain), then one organism a row, named by its KEGG code in the second column.
4. The maxRAFs, Supplementary Data 4 (rich medium) and 5 (NAD medium): archives of text files maxRAFs_Rich/<code>.txt
   and maxRAFs_NAD/<code>.txt, one reaction id a line, blank lines skipped; any other file or folder in an archive is
   refused, but for the empty __MACOSX/ folder the macOS archiver leaves (found by the syntax pass, before any list
   was read for its contents). A list is the set of its ids, repeats counted beside. Its size is its reactions other than pooling ones, as the 2020
   paper counted; a list is nonempty when that size is at least one.
5. A list L is a RAF of the global network with a food F when every id of L is a reaction of Supplementary Data 2 and
   the maxRAF (raf/xavier.py, Hordijk and Steel's algorithm: a two-way reaction is two halves, a reaction kept when
   either half is) of the network made of L's reactions and every pooling reaction keeps each reaction of L other than
   the pooling ones. Then L, with the pooling reactions it needs, is a RAF: each reaction's reactants and one
   alternative of its rule lie in the closure of the food under it. If one is not kept, no set of L's reactions with
   pooling reactions is a RAF holding all of L. Pooling reactions a list names are counted beside, not required.
6. The test's four conditions, test_passed 1 if all hold:
   - Supplementary Data 1 names 6683 prokaryotes, each once, and each has a nonempty rich-medium list;
   - every nonempty rich-medium list is a RAF with the rich food;
   - every nonempty NAD-medium list is a RAF with the NAD food;
   - over every nonempty list of both media, the smallest has 3 reactions and the largest 619.
7. Beside the test, against the paper's abstract: the mean list sizes, over all of Supplementary Data 1's prokaryotes
   (an organism without a nonempty list counting 0) and over the nonempty lists, rich and NAD (the paper: 275 and 93);
   how many prokaryotes have a nonempty NAD list; how many rich lists the 300th most common reaction of the rich lists
   is in (the paper: the 300 most common are in at least 2732); how many rich lists generate, in the closure of the
   rich food under the list's maxRAF, phenylalanine (C00079), histidine (C00135), arginine (C00062) or sn-glycerol
   1-phosphate (C00623) (the paper: in the rich medium every universally essential metabolite is produced but these
   four); the maxRAF of the whole global network with each food; the sizes with listed pooling reactions counted; and
   lists for codes outside Supplementary Data 1, ids outside Supplementary Data 2 and repeated ids.
8. Controls: raf/xavier.py's small system (TOY_TEXT) gives its known maxRAF, and the list check on it accepts r1, r2,
   r3, r6 and r1, r2 and rejects r2, r3, r6 (without r1 nothing makes x), r1, r2, r4 (r4 needs d, which nothing makes)
   and a list naming a reaction the network lacks; the NAD food lies within the rich food and the global network's
   NAD maxRAF within its rich one; both global maxRAFs are RAFs, from which the algorithm would drop nothing more; and
   every list found a RAF lies within its medium's global maxRAF (another route to the same answer: every RAF of a part
   of a network lies in the maxRAF of the whole).

What it cannot check: that each list is its organism's maximal RAF (the organisms' own networks are not released), the
networks' curation (which reactions KEGG gives each organism, which cofactors catalyse them) and the chemistry itself;
a RAF is a property of the network as annotated.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 raf/xk2022.py
"""

import importlib.util
import io
import json
import os
import re
import sys
import zipfile
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, file))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


X = _load("raf_xavier", "xavier.py")
Refused = X.Refused

INPUTS = {
    "sd1": ("rsta20210244_si_001.xlsx", "c3df16284f8f93e8be6e9c049ae0bfda1bf8fb47dd5d180a25e99135c35eee06"),
    "sd2": ("rsta20210244_si_002.txt", "aa8bb38c5700066d15af4256157905e5fd5310d9beab64c880750d2e75cb3553"),
    "sd3": ("rsta20210244_si_003.xlsx", "0bd68271c25dd20423625acafacb9760fd52fddfca4d677fbd65710f2800d97e"),
    "sd4": ("rsta20210244_si_004.zip", "8865464bb5c2e409630a0ffbdcf4e0aabf02be292551f7a6ad5e1c7a7688341d"),
    "sd5": ("rsta20210244_si_005.zip", "a18b4e85aa72b25ae0bcd1035f8e8d6b36590dd81dfba9441211bdbd5e97b81b"),
}
NETWORK_HEADER = "Reaction_ID\tEquation\tCatalysts\tReaction_Rate"
FOOD_HEADER = {"A": "Molecule name(s)", "B": "Molecule ID (KEGG or from this work)", "C": "Rich medium",
               "D": "NAD medium", "E": "Fictional (modelling purposes)"}
ORGANISM_HEADER = {"A": "KEGG_TAX_ID", "B": "CODE", "C": "Species_Name", "D": "Taxonomy", "E": "ECs", "F": "RNs",
                   "G": "Domain"}
TICK = "✓"
POOL = frozenset([frozenset(["Pooling"])])
MEDIA = (("rich", "sd4", "maxRAFs_Rich"), ("nad", "sd5", "maxRAFs_NAD"))
NAMES = ("rich", "nad")
PROKARYOTES = 6683
SIZES = (3, 619)
PRINTED_MEANS = (275, 93)
COMMON = (300, 2732)
NOT_MADE = {"C00079": "Phe", "C00135": "His", "C00062": "Arg", "C00623": "glycerol-1-P"}
UNPACKED = 400 * 2 ** 20                 # an archive may unpack to at most this many bytes
MACOSX = "__MACOSX/"                     # the empty folder the macOS archiver leaves in both archives
TOY_LISTS = (("r1", "r2", "r3", "r6"), ("r1", "r2"), ("r2", "r3", "r6"), ("r1", "r2", "r4"), ("r1", "r2", "r9"))
TOY_VERDICTS = (True, True, False, False, False)
OUTPUTS = ("network", "media", "prokaryotes", "rich_lists", "nad_lists", "sizes", "mean_sizes", "common_300",
           "not_made", "global_maxraf", "with_pooling", "extras", "controls_passed", "controls_total",
           "conditions_met", "conditions_total", "test_passed")
LIMIT = 200


# -- reading -------------------------------------------------------------------------------------------------------

def network_file(text):
    """Supplementary Data 2 as [(id, left, right, two_way, rule)] (rule 1)."""
    lines = text.splitlines()
    at = [i for i, line in enumerate(lines) if line == NETWORK_HEADER]
    if len(at) != 1:
        raise Refused(f"Supplementary Data 2: its header line appears {len(at)} times, not once")
    net, seen = [], set()
    for i, line in enumerate(lines[at[0] + 1:], start=at[0] + 2):
        if not line.strip():
            continue
        where = f"Supplementary Data 2 line {i}"
        cells = line.split("\t")
        if len(cells) != 4:
            raise Refused(f"{where}: {len(cells)} fields, not 4")
        rid, equation, rule, rate = cells
        if not X.NAME.fullmatch(rid) or rid in seen:
            raise Refused(f"{where}: reaction id {rid!r} malformed or repeated")
        seen.add(rid)
        try:
            float(rate)
        except ValueError:
            raise Refused(f"{where}: rate {rate!r} is not a number") from None
        left, right, two_way = X.parse_equation(equation, where)
        parsed = X.parse_rule(rule, where)
        if rid.startswith("R_") and parsed != POOL:
            raise Refused(f"{where}: pooling reaction {rid} is not catalysed by Pooling alone")
        net.append((rid, left, right, two_way, parsed))
    if not net:
        raise Refused("Supplementary Data 2 holds no reactions")
    return net


def one_sheet(data, what):
    book = X.sheets(data)
    if len(book) != 1:
        raise Refused(f"{what}: {len(book)} sheets, not one")
    return next(iter(book.values()))


def blank(row):
    return not any((v or "").strip() for v in row.values())


def media(rows):
    """Supplementary Data 3's two foods, {"rich": ids, "nad": ids} (rule 2)."""
    if len(rows) < 4 or any(rows[2].get(k) != v for k, v in FOOD_HEADER.items()):
        raise Refused("Supplementary Data 3: the third row is not the paper's header")
    food, seen = {m: [] for m in NAMES}, set()
    for i, row in enumerate(rows[3:], start=4):
        if blank(row):
            continue
        where = f"Supplementary Data 3 row {i}"
        mid = row.get("B")
        if not mid or not X.NAME.fullmatch(mid) or mid in seen:
            raise Refused(f"{where}: molecule id {mid!r} missing, malformed or repeated")
        seen.add(mid)
        for col, medium in (("C", "rich"), ("D", "nad")):
            mark = (row.get(col) or "").strip()
            if mark not in ("", TICK):
                raise Refused(f"{where}: {mark!r} in the {medium} column, not a tick or nothing")
            if mark:
                food[medium].append(mid)
    for medium, ids in food.items():
        if not all(a in ids for a in X.ALWAYS):
            raise Refused(f"the {medium} food lacks Pooling or Spontaneous")
    return {m: frozenset(ids) for m, ids in food.items()}


def organisms(rows):
    """Supplementary Data 1's codes, in order, repeats kept (rule 3)."""
    if len(rows) < 4 or any(rows[2].get(k) != v for k, v in ORGANISM_HEADER.items()):
        raise Refused("Supplementary Data 1: the third row is not the paper's header")
    codes = []
    for i, row in enumerate(rows[3:], start=4):
        if blank(row):
            continue
        code = row.get("B")
        if not code or not X.NAME.fullmatch(code):
            raise Refused(f"Supplementary Data 1 row {i}: code {code!r} missing or malformed")
        codes.append(code)
    return codes


def lists(data, folder, what):
    """{code: [ids as listed]} from an archive of maxRAFs (rule 4)."""
    out = {}
    pattern = re.compile(re.escape(folder) + r"/([A-Za-z0-9_\-]+)\.txt")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos = z.infolist()
        if sum(i.file_size for i in infos) > UNPACKED:
            raise Refused(f"{what}: unpacks to more than {UNPACKED} bytes")
        for info in infos:
            name = info.filename
            if info.is_dir():
                if name not in (folder + "/", MACOSX):
                    raise Refused(f"{what}: directory {name!r}")
                continue
            m = pattern.fullmatch(name)
            if not m:
                raise Refused(f"{what}: entry {name!r} is not {folder}/<code>.txt")
            if m.group(1) in out:
                raise Refused(f"{what}: {name} twice")
            try:
                text = z.read(info).decode("utf-8")
            except UnicodeDecodeError:
                raise Refused(f"{what}: {name} is not UTF-8 text") from None
            ids = []
            for j, line in enumerate(text.splitlines(), start=1):
                s = line.strip()
                if not s:
                    continue
                if not X.NAME.fullmatch(s):
                    raise Refused(f"{what}: {name} line {j}: {s[:40]!r} is not a reaction id")
                ids.append(s)
            out[m.group(1)] = ids
    return out


# -- the check ------------------------------------------------------------------------------------------------------

class Global:
    """The global network, indexed: its reactions by id and its pooling reactions."""

    def __init__(self, net):
        self.net = net
        self.pos = {x[0]: i for i, x in enumerate(net)}
        self.pooling = frozenset(x[0] for x in net if x[0].startswith("R_"))


def list_check(ids, g, food, watch=()):
    """Rule 5 for one list: whether it is a RAF, its size, the ids outside the network, the reactions its maxRAF does
    not keep, and which of the watched molecules the closure of the food under that maxRAF holds."""
    listed = set(ids)
    unknown = sorted(r for r in listed if r not in g.pos)
    sub = [g.net[i] for i in sorted({g.pos[r] for r in listed if r in g.pos} | {g.pos[r] for r in g.pooling})]
    hs = X.halves(sub)
    alive, W = X.max_raf(food, hs)
    kept = {sub[hs[h][0]][0] for h in alive}
    chem = listed - g.pooling
    dropped = sorted(r for r in chem if r in g.pos and r not in kept)
    return {"raf": not unknown and not dropped, "size": len(chem), "with_pooling": len(listed), "unknown": unknown,
            "dropped": dropped, "pooling_listed": len(listed & g.pooling),
            "pooling_dropped": sorted(r for r in listed & g.pooling if r not in kept), "repeats": len(ids) - len(listed),
            "made": tuple(k for k in watch if k in W), "chem": tuple(sorted(chem))}


def toy_control():
    """Rule 8's small system: its maxRAF, and the list check's verdicts on its five lists."""
    net = X.toy()
    hs = X.halves(net)
    alive, W = X.max_raf(X.TOY_FOOD, hs)
    known = X.reactions_of(alive, hs, net) == X.TOY_MAXRAF and set(W - X.TOY_FOOD) == X.TOY_MAKES
    g = Global(net)
    verdicts = tuple(list_check(ids, g, X.TOY_FOOD)["raf"] for ids in TOY_LISTS)
    return known and verdicts == TOY_VERDICTS


def span(sizes):
    return f"{min(sizes)}-{max(sizes)}" if sizes else "none"


def assess(codes, net, food, listed, prokaryotes=PROKARYOTES, sizes=SIZES):
    """The test's conditions, the values beside it and the controls (rules 5 to 8), from the parsed inputs: codes
    from Supplementary Data 1, the network, {"rich": food, "nad": food} and {"rich": {code: ids}, "nad": ...}."""
    g = Global(net)
    checks = {m: {code: list_check(ids, g, food[m], tuple(NOT_MADE)) for code, ids in sorted(listed[m].items())}
              for m in NAMES}
    full = {m: {c: r for c, r in checks[m].items() if r["size"] > 0} for m in NAMES}
    sd1 = set(codes)
    every = [r["size"] for m in NAMES for r in full[m].values()]
    cond = {
        f"Supplementary Data 1 names {prokaryotes} prokaryotes, each once, each with a nonempty rich list":
            len(codes) == prokaryotes == len(sd1) and all(c in full["rich"] for c in sd1),
        "every nonempty rich list is a RAF with the rich food": all(r["raf"] for r in full["rich"].values()),
        "every nonempty NAD list is a RAF with the NAD food": all(r["raf"] for r in full["nad"].values()),
        f"the nonempty lists of both media run from {sizes[0]} to {sizes[1]} reactions":
            bool(every) and (min(every), max(every)) == tuple(sizes),
    }

    # The whole network's maxRAF with each food.
    hs = X.halves(net)
    whole, whole_alive = {}, {}
    for m in NAMES:
        alive, _ = X.max_raf(food[m], hs)
        whole_alive[m] = alive
        whole[m] = {net[hs[h][0]][0] for h in alive}

    # Beside the test.
    n_sd1 = len(sd1)
    means = {}
    for m in NAMES:
        over_sd1 = sum(full[m][c]["size"] for c in sd1 if c in full[m]) / n_sd1 if n_sd1 else 0.0
        over_lists = sum(r["size"] for r in full[m].values()) / len(full[m]) if full[m] else 0.0
        means[m] = (over_sd1, over_lists)
    counts = Counter(r for res in full["rich"].values() for r in res["chem"])
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    common = ranked[COMMON[0] - 1][1] if len(ranked) >= COMMON[0] else None
    made = {k: sorted(c for c, r in full["rich"].items() if k in r["made"]) for k in NOT_MADE}
    failures = [{"medium": m, "code": c, "unknown": r["unknown"][:10], "dropped": r["dropped"][:10],
                 "n_unknown": len(r["unknown"]), "n_dropped": len(r["dropped"])}
                for m in NAMES for c, r in full[m].items() if not r["raf"]]
    with_pooling = [r["with_pooling"] for m in NAMES for r in full[m].values()]
    extras = {m: sorted(set(listed[m]) - sd1) for m in NAMES}
    unknown_ids = sorted({u for m in NAMES for r in checks[m].values() for u in r["unknown"]})
    repeated = sum(1 for m in NAMES for r in checks[m].values() if r["repeats"])
    naming_pooling = sum(1 for m in NAMES for r in checks[m].values() if r["pooling_listed"])
    pooling_not_kept = sum(len(r["pooling_dropped"]) for m in NAMES for r in checks[m].values())
    empty = {m: sorted(c for c, r in checks[m].items() if r["size"] == 0) for m in NAMES}

    # Controls.
    controls = {
        "the small system's maxRAF is the known one, and the list check accepts and rejects its five lists as it "
        "should": toy_control(),
        "the NAD food lies within the rich food, and the whole network's NAD maxRAF within its rich one":
            food["nad"] <= food["rich"] and whole["nad"] <= whole["rich"],
        "both whole-network maxRAFs are RAFs, from which nothing more can be dropped":
            all(X.is_raf(food[m], hs, whole_alive[m]) for m in NAMES),
        "every list found a RAF lies within its medium's whole-network maxRAF":
            all(whole[m].issuperset(r["chem"]) for m in NAMES for r in full[m].values() if r["raf"]),
    }

    sizes_of = {m: [r["size"] for r in full[m].values()] for m in NAMES}
    raf_count = {m: sum(1 for r in full[m].values() if r["raf"]) for m in NAMES}
    unknown_lists = {m: sum(1 for r in full[m].values() if r["unknown"]) for m in NAMES}
    in_sd1 = {m: sum(1 for c in sd1 if c in full[m]) for m in NAMES}
    two_way = sum(1 for x in net if x[3] and x[0] not in g.pooling)
    label = {"rich": "rich", "nad": "NAD"}
    values = {
        "network": f"{len(net) - len(g.pooling)} reactions (+{len(g.pooling)} pooling), {two_way} of them two-way",
        "media": (f"rich food {len(food['rich'])} molecules, NAD food {len(food['nad'])}; NAD within rich: "
                  f"{'yes' if food['nad'] <= food['rich'] else 'no'}"),
        "prokaryotes": (f"Supplementary Data 1 {len(codes)} rows, {n_sd1} codes; "
                        + "; ".join(f"{label[m]} lists {len(listed[m])} ({len(full[m])} nonempty, {in_sd1[m]} of the "
                                    f"codes)" for m in NAMES)),
        "rich_lists": (f"{raf_count['rich']} of {len(full['rich'])} nonempty rich lists are RAFs with the rich food "
                       f"({unknown_lists['rich']} name a reaction outside Supplementary Data 2)"),
        "nad_lists": (f"{raf_count['nad']} of {len(full['nad'])} nonempty NAD lists are RAFs with the NAD food "
                      f"({unknown_lists['nad']} name a reaction outside Supplementary Data 2)"),
        "sizes": (f"rich {span(sizes_of['rich'])}, NAD {span(sizes_of['nad'])}; both media {span(every)} "
                  f"(printed {SIZES[0]} to {SIZES[1]})"),
        "mean_sizes": (f"rich {means['rich'][0]:.1f} over the {n_sd1} codes, {means['rich'][1]:.1f} over nonempty "
                       f"lists; NAD {means['nad'][0]:.1f} and {means['nad'][1]:.1f} (printed {PRINTED_MEANS[0]} and "
                       f"{PRINTED_MEANS[1]})"),
        "common_300": (f"the {COMMON[0]}th most common reaction of the nonempty rich lists is in {common} of them "
                       f"(printed: the {COMMON[0]} most common in at least {COMMON[1]})"),
        "not_made": ("rich lists generating " + ", ".join(f"{NOT_MADE[k]} {len(made[k])}" for k in NOT_MADE)
                     + " (printed: none)"),
        "global_maxraf": (f"the whole network's maxRAF: rich {len(whole['rich'] - g.pooling)} reactions, NAD "
                          f"{len(whole['nad'] - g.pooling)}"),
        "with_pooling": (f"sizes with listed pooling reactions counted: both media {span(with_pooling)}; "
                         f"{naming_pooling} lists name pooling reactions; {pooling_not_kept} listed pooling reactions "
                         f"not kept"),
        "extras": (f"lists for codes outside Supplementary Data 1: rich {len(extras['rich'])}, NAD "
                   f"{len(extras['nad'])}; ids outside Supplementary Data 2: {len(unknown_ids)}; lists with repeats: "
                   f"{repeated}"),
        "controls_passed": sum(controls.values()), "controls_total": len(controls),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {
        "conditions": cond, "controls": controls,
        "food": {m: sorted(food[m]) for m in NAMES},
        "sizes": {c: [full[m][c]["size"] if c in full[m] else 0 for m in NAMES] for c in sorted(sd1)},
        "sd1_repeated_codes": sorted(c for c, k in Counter(codes).items() if k > 1),
        "empty_lists": empty,
        "failures": failures[:200], "failures_total": len(failures),
        "means": {m: {"over_sd1": means[m][0], "over_lists": means[m][1]} for m in NAMES},
        "most_common_rich": ranked[:COMMON[0]],
        "generated_by_rich_lists": {f"{k} {NOT_MADE[k]}": {"count": len(made[k]), "codes": made[k][:50]}
                                    for k in NOT_MADE},
        "whole_maxraf": {m: sorted(whole[m] - g.pooling) for m in NAMES},
        "extras": extras, "unknown_ids": unknown_ids[:200], "pooling": sorted(g.pooling),
    }
    return out, detail


# -- the run ---------------------------------------------------------------------------------------------------------

def read_all(inputs):
    data = {k: X.read_bytes(os.path.join(inputs, name), sha) for k, (name, sha) in INPUTS.items()}
    net = network_file(data["sd2"].decode("utf-8"))
    food = media(one_sheet(data["sd3"], "Supplementary Data 3"))
    codes = organisms(one_sheet(data["sd1"], "Supplementary Data 1"))
    listed = {m: lists(data[key], folder, f"Supplementary Data {key[-1]}") for m, key, folder in MEDIA}
    return codes, net, food, listed


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed or ""):
        raise Refused("the seed must be 64 hex characters")
    codes, net, food, listed = read_all(inputs)
    out, detail = assess(codes, net, food, listed)
    detail["inputs"] = {k: {"name": n, "sha256": s} for k, (n, s) in INPUTS.items()}
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
        sys.exit(f"xk2022: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
