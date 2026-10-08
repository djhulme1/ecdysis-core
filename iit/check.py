#!/usr/bin/env python3
"""IIT 3.0's Phi, every tie kept, for the ten published systems of Hanson & Walker's corpus: an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:dff1ca5795aecf74) is from Hanson and
Walker, "On the non-uniqueness problem in integrated information theory" (Neuroscience of Consciousness 2023(1),
niad014): "Here, we show that despite its widespread application, Phi is not a well-defined mathematical concept in
the sense that the value it specifies is non-unique. To demonstrate this, we introduce an algorithm that calculates
all possible Phi values for a given system in strict accordance with the mathematical definition from the theory.
We show that, to date, all published Phi values under consideration are selected arbitrarily from a multitude of
equally valid alternatives."

Its registered test: refuted if, computed as the paper's algorithm defines it (IIT 3.0 as PyPhi 1.2 computes it,
every tie for a mechanism's maximally irreducible cause or effect kept as an equally valid alternative), the set of
possible Phi values has more than one member for fewer than eight of the ten published systems of the paper's corpus
(Table 1, with the transition probability matrices and states of its appendix), or holds both Phi = 0 and Phi > 0 for
none of them (the paper finds nine and three).

Everything here is computed afresh by Imago's own IIT 3.0 (engine.py, standard library; the transport problems in
flow.c, built here with gcc). The inputs are the paper's full text (Europe PMC's JATS, the claim's data of record), the
authors' algorithm (phi_spectrum.py, also data of record) and five of the authors' notebooks from the repository the
paper names for its data (elife-asu/pyphi-spectrum at 2585d72), each checked against its SHA-256 and size and read as
data: no code from them is run. Every rule below was fixed before any seed existed; the seed is not used.

1. IIT 3.0 as PyPhi 1.2.0 (the base of the authors' fork) computes it, with its defaults (the configuration file in
   their repository): bipartitions of mechanism and purview for small phi, earth mover's distance with Hamming ground
   distance for causes and PyPhi's sum of marginal differences for effects, each rounded to 6 decimals; potential
   purviews filtered by PyPhi's connectivity test, on the all-ones connectivity PyPhi assumes; concepts with phi > 0;
   the cause-effect structure distance (concepts in both drop out; otherwise the extended earth mover's distance with
   the null concept, or, when one side has none left, phi times the distance to the null concept), rounded to 6
   decimals; the unidirectional cuts in PyPhi's order. The rules of PyPhi that engine.py follows are in its source.
2. The arithmetic. PyPhi computes every earth mover's distance with pyemd 0.5.1, which keeps common mass in place,
   scales the rest so that the larger total is a million and the costs so that the largest is a million, rounds both
   to integers and solves the integer problem. The test reads "as PyPhi 1.2 computes it", so the verdict uses that
   arithmetic (reproduced here, mode 1). The same run in exact arithmetic (mode 0: no scaling or rounding before the
   6-decimal rounding PyPhi applies to phi) is reported beside it.
3. Ties, as the authors' algorithm (phi_spectrum.py, get_all_concepts) defines them: every purview whose phi equals
   the largest, after the 6-decimal rounding, is a core cause (or effect), if that phi is above 0; every pairing of a
   tied cause with a tied effect is a concept. The file must contain that rule as written here (TIE_RULE).
4. The spectrum, as the authors' algorithm defines it (get_phi_spectrum and get_Phi_MIP): for each cut, every
   unpartitioned structure (one concept per mechanism, from its ties) against every partitioned one; Phi_min is the
   least value over all cuts; the upper bound starts at the first cut's largest value and drops to the largest value
   of any cut whose least value is Phi_min, if smaller; the possible values are all values of all cuts between the
   two. The file must contain those lines (BAND_RULE). A system's set of possible values is those values to 6
   decimals; values 1e-6 apart are merged before counting members (pyemd's integers leave such pairs).
5. The ten systems: Table 1 of the paper, each with its appendix TPM (Tables A1 to A11, which must parse and, for
   the deterministic ones, be complete) and its stated state, all nodes in the subsystem, with three exceptions
   taken from the authors' notebooks: Tononi et al.'s subsystem is A, B and C of the four nodes, with D in its
   state as background (the notebook's nodes; Table 1 gives the network's size, 4); Marshall et al.'s is A, B and C
   of nine, in the notebook's state (0,0,1,1,0,0,1,0,0), the network's fixed point, where the appendix's
   "000110011" is a state with no predecessor that the notebook does not use (reported); Hoel et al.'s TPM is the
   notebook's rule (each node an AND of the other pair, on for certain if both are on and with probability 0.3
   otherwise), which Table A10 prints rounded to 2 decimals and must match at that rounding.
6. Outputs: for each mode, the systems whose set of possible values has more than one member, and those whose set
   holds both 0 and a positive value; PyPhi's own single value (its choice among the ties: the largest phi, then the
   larger purview, then the first; its cache of undamaged causes and effects across cuts) beside Table 1's.

test_passed is 1 if, in PyPhi's arithmetic, at least eight of the ten systems have more than one possible value and
at least one has both 0 and a positive value, and the controls pass; else 0.

7. Controls (each must hold): the transport solver gives 1 for moving one unit one step, and the pyemd arithmetic
   gives 0.166666 (pyemd 0.5.1's own value) for uniform against (1/3, 1/6, 1/6, 1/3) on two nodes, where exact
   arithmetic gives 1/6; the authors' printed spectra (the "Phi MIP" outputs of their notebooks for AND+OR, Oizumi et
   al., Tononi et al., Marshall et al. and Hoel et al.) are reproduced in PyPhi's arithmetic: after merging 1e-6
   pairs, as many values, each within 1.5e-6 of one of the other's; PyPhi's single value matches Table 1 (to its 4
   decimals) for AND+OR, the value the paper says it took from PyPhi.

Writes results/outputs.json and results/detail.json. Run with: python3 iit/check.py
"""

import hashlib
import html
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import engine as E  # noqa: E402

COMMIT = "2585d72916c8b9cb8197aa93a4a03c59953efccf"
INPUTS = {
    "PMC10408361.xml": ("ecb6c964fbe8fc3b117de97a1f0b6affb121d1031a3192f6b2125814c49bc1ea", 307543),
    "phi_spectrum.py": ("680283d1353831f809c725542bc75bf144ce3c6aeff26f5fe74d9860c52c66d4", 5034),
    "nb_and_or.ipynb": ("b462d7c9645de0b081a3995340fa36ac47d3dc583a7da2c7ab58c97ce308dbb1", 35955),
    "nb_oizumi.ipynb": ("4f13ce1e8bdfa3c7b348f2c8763ac026f01f514d16bbaa3d9e2d4d63dc39a743", 36302),
    "nb_tononi.ipynb": ("d3b4d7d3887bf80b0691cced3742f9e69289bdd2fe68bdb1512f9aa12e9ce954", 52950),
    "nb_marshall.ipynb": ("523a35a63f3c7fc442ace5c1f4ecb3c96dab2508b8221b21b7a18e5f7b501685", 120427),
    "nb_hoel.ipynb": ("513c4c6fc469ccc31717c8356d8d7250515cdfa3c59782e7d9af9ca8184b9778", 64197),
}
TIE_RULE = "value.phi == core_cause.phi"
BAND_RULE = ("Phi_min_MIP = np.min(values[0])",
             "possible_MIPs = (index for index in values if np.min(index) == Phi_min_MIP)",
             "Phi_max_MIP = np.max(values[0])",
             "valid_phi = [phi for index in values for phi in index if phi >= Phi_min_MIP and phi <= Phi_max_MIP]")

# name in Table 1, appendix table, stated state (appendix), subsystem positions, published-band notebook
SYSTEMS = [
    ("AND+OR", "Table A2", "00", None, "nb_and_or.ipynb"),
    ("Farnsworth 2021 (full)", "Table A6", "11111", None, None),
    ("Farnsworth 2021 (reduced)", "Table A7", "111", None, None),
    ("Gomez et al. 2020", "Table A5", "0001", None, None),
    ("Photodiode", "Table A1", "10", None, None),
    ("Hanson and Walker 2020", "Table A3", "101", None, None),
    ("Marshall et al. 2017", "Table A11", "001100100", (1, 2, 3), "nb_marshall.ipynb"),
    ("Hoel et al. 2016", "Table A10", "0000", None, "nb_hoel.ipynb"),
    ("Tononi et al. 2016", "Table A9", "1110", (0, 1, 2), "nb_tononi.ipynb"),
    ("Oizumi et al. 2014", "Table A8", "100", None, "nb_oizumi.ipynb"),
]
CHECKED_BANDS = ("nb_and_or.ipynb", "nb_oizumi.ipynb", "nb_tononi.ipynb", "nb_marshall.ipynb", "nb_hoel.ipynb")
HOEL_NOISE = 0.3
NBITS = 10_000_000


class Refused(Exception):
    """The input is not what the rules say it must be."""


def load(directory):
    out = {}
    for name, (sha, size) in INPUTS.items():
        with open(os.path.join(directory, name), "rb") as f:
            data = f.read()
        got = hashlib.sha256(data).hexdigest()
        if got != sha or len(data) != size:
            raise Refused(f"{name}: sha256 {got} and {len(data)} bytes, not {sha} and {size}")
        out[name] = data.decode("utf-8")
    return out


# ---------------------------------------------------------------- reading the paper and the notebooks

def tables(xml):
    out = {}
    for m in re.finditer(r"<table-wrap\b.*?</table-wrap>", xml, flags=re.S):
        t = m.group(0)
        lab = re.search(r"<label>(.*?)</label>", t, flags=re.S)
        if not lab:
            continue
        label = lab.group(1).replace(" ", " ").strip().rstrip(".")
        rows = []
        for r in re.findall(r"<tr>(.*?)</tr>", t, flags=re.S):
            cells = re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", r, flags=re.S)
            rows.append([html.unescape(re.sub(r"<[^>]+>", "", c)).replace(" ", " ").strip() for c in cells])
        out[label] = rows
    return out


def text_of(xml):
    t = re.sub(r"<tex-math[^>]*>(.*?)</tex-math>",
               lambda m: re.sub(r"\\documentclass.*?\\begin\{document\}", "", m.group(1), flags=re.S)
               .replace("\\end{document}", ""), xml, flags=re.S)
    t = re.sub(r"<mml:math.*?</mml:math>", "", t, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))


def deterministic(rows, n):
    """s(t) -> s(t+1) bit strings, little-endian (first character is node 0)."""
    tpm = [None] * 2 ** n
    for r in rows[1:]:
        if len(r) != 2 or len(r[0]) != n or len(r[1]) != n or set(r[0] + r[1]) - {"0", "1"}:
            raise Refused(f"a TPM row {r} is not two {n}-bit states")
        s = sum(int(c) << i for i, c in enumerate(r[0]))
        if tpm[s] is not None:
            raise Refused(f"state {r[0]} twice")
        tpm[s] = [float(c) for c in r[1]]
    if any(v is None for v in tpm):
        raise Refused("an incomplete TPM")
    return tpm


def marshall(rows):
    mp = {}
    for r in rows[1:]:
        if len(r) != 8:
            raise Refused("Table A11 has a row of other than four pairs")
        for k in range(0, 8, 2):
            mp[int(r[k])] = int(r[k + 1])
    if sorted(mp) != list(range(512)):
        raise Refused("Table A11 is not a map of the 512 states")
    return [[float((mp[s] >> j) & 1) for j in range(9)] for s in range(512)]


def hoel(rows):
    tpm = []
    for s in range(16):
        cur = [(s >> i) & 1 for i in range(4)]
        tpm.append([1.0 if ((cur[2], cur[3]) if j < 2 else (cur[0], cur[1])) == (1, 1) else HOEL_NOISE
                    for j in range(4)])
    # the state-by-state table as printed, to 2 decimals
    for r in rows[1:]:
        s = int(r[0])
        for t, cell in enumerate(r[1:]):
            p = 1.0
            for j in range(4):
                p *= tpm[s][j] if (t >> j) & 1 else 1.0 - tpm[s][j]
            if f"{p:.2f}" != cell:
                raise Refused(f"Table A10 ({s}, {t}) is {cell}, the rule gives {p:.4f}")
    return tpm


def notebook(src):
    nb = json.loads(src)
    code = "\n".join("".join(c.get("source", [])) for c in nb["cells"] if c["cell_type"] == "code")
    outs = []
    for c in nb["cells"]:
        for o in c.get("outputs", []):
            if "text" in o:
                outs.append("".join(o["text"]))
    return code, "\n".join(outs)


def printed_band(src):
    _, out = notebook(src)
    m = re.findall(r"Phi MIP =\s*\[([^\]]*)\]", out)
    if len(m) != 1:
        raise Refused("a notebook without exactly one printed Phi MIP")
    return sorted(float(v) for v in m[0].split())


def merged(values):
    """Distinct values to 6 decimals, pairs 1e-6 apart merged (single linkage)."""
    vs = sorted(set(round(v * 1e6) for v in values))
    out = []
    for v in vs:
        if out and v - out[-1][-1] <= 1:
            out[-1].append(v)
        else:
            out.append([v])
    return [g[0] / 1e6 for g in out]


def same(a, b):
    """Two merged spectra agree: as many values, each within 1.5e-6 of one of the other's."""
    return len(a) == len(b) and all(any(abs(x - y) <= 1.5e-6 for y in b) for x in a) and \
        all(any(abs(x - y) <= 1.5e-6 for x in a) for y in b)


def systems(files):
    xml = files["PMC10408361.xml"]
    tabs = tables(xml)
    text = text_of(xml)
    t1 = {r[0]: r for r in tabs["Table 1"][1:]}
    out = []
    for name, tab, state_s, nodes, nb in SYSTEMS:
        if name not in t1:
            raise Refused(f"{name} is not in Table 1")
        n_size, published = int(t1[name][2]), float(t1[name][3])
        if tab == "Table A11":
            tpm = marshall(tabs[tab])
        elif tab == "Table A10":
            tpm = hoel(tabs[tab])
        else:
            tpm = deterministic(tabs[tab], len(state_s))
        n = len(tpm[0])
        state = tuple(int(c) for c in state_s)
        if len(state) != n:
            raise Refused(f"{name}: a state of {len(state)} nodes for {n}")
        notes = []
        if name == "Marshall et al. 2017":
            if "s_0=000110011" not in text.replace(" ", ""):
                raise Refused("the appendix's fission yeast state is not as read")
            code, _ = notebook(files["nb_marshall.ipynb"])
            if "state = (0,0,1,1,0,0,1,0,0)" not in code or "nodes = ['A','B','C']" not in code:
                raise Refused("the Marshall notebook's state or nodes are not as read")
            notes.append("appendix state 000110011 differs from the notebook's 001100100 (used)")
        elif name == "Tononi et al. 2016":
            code, _ = notebook(files["nb_tononi.ipynb"])
            if "state = (1,1,1,0)" not in code or "nodes = ['A','B','C']" not in code:
                raise Refused("the Tononi notebook's state or nodes are not as read")
            if f"s_0={state_s}" not in text.replace(" ", ""):
                raise Refused(f"{name}: the appendix does not state s_0={state_s}")
        elif name == "Hoel et al. 2016":
            code, _ = notebook(files["nb_hoel.ipynb"])
            for frag in ("p_off = 0.7", "p_on = 0.3", "if input_to_node == (1,1):",
                         "input_to_node = current_state[2:4]"):
                if frag not in code:
                    raise Refused(f"the Hoel notebook lacks {frag!r}")
            if f"s_0={state_s}" not in text.replace(" ", ""):
                raise Refused(f"{name}: the appendix does not state s_0={state_s}")
        elif f"s_0={state_s}" not in text.replace(" ", "") and f"state{state_s}" not in text.replace(" ", ""):
            raise Refused(f"{name}: the appendix does not state s_0={state_s}")
        sub_nodes = nodes if nodes is not None else tuple(range(n))
        out.append({"name": name, "tpm": tpm, "state": state, "nodes": sub_nodes, "size": n_size,
                    "published": published, "notebook": nb, "notes": notes})
    return out


# ---------------------------------------------------------------- one system

def concepts_of(flow, sub):
    out = {}
    for m in E.powerset(range(sub.k)):
        pc, tc = sub.mice(flow, E.CAUSE, m)
        pe, te = sub.mice(flow, E.EFFECT, m)
        if pc is None or pe is None or min(pc[0], pe[0]) <= 0:
            continue
        out[m] = [E.Concept(m, c, e, sub) for c in tc for e in te]
    return out


def damaged(sub, direction, mechanism, purview):
    if sub.splits(mechanism):
        return True
    frm, to = (purview, mechanism) if direction == E.CAUSE else (mechanism, purview)
    return any(sub.cut_matrix(a, b) for a in frm for b in to)


def pyphi_value(flow, net, state, nodes, canon):
    """PyPhi's own single Phi: its pick among ties, its cache of undamaged MICE, its mechanisms per cut."""
    cache = {}
    sub = E.Subsystem(net, state, nodes, cache=cache)
    parent, C0 = {}, []
    for m in E.powerset(range(sub.k)):
        picks = []
        for d in (E.CAUSE, E.EFFECT):
            pick, _ = sub.mice(flow, d, m)
            picks.append(pick)
            if pick is not None and pick[0] > 0:
                parent[(d, m)] = pick
        if None not in picks and min(picks[0][0], picks[1][0]) > 0:
            C0.append(E.Concept(m, picks[0], picks[1], sub))
    for c in C0:
        canon(c)
    if not C0:
        return 0.0
    best = float("inf")
    for A, B in E.directed_bipartition(tuple(range(sub.k)), nontrivial=True):
        cs = E.Subsystem(net, state, nodes, cut=(A, B), tables=sub.uncut, cache=cache)
        mechs = sorted(set(c.mechanism for c in C0) | {m for m in E.powerset(range(sub.k)) if cs.splits(m)},
                       key=lambda m: (len(m), m))
        C1 = []
        for m in mechs:
            picks = []
            for d in (E.CAUSE, E.EFFECT):
                kept = parent.get((d, m))
                if kept is not None and not damaged(cs, d, m, kept[1]):
                    picks.append(kept)
                else:
                    picks.append(cs.mice(flow, d, m)[0])
            if None not in picks and min(picks[0][0], picks[1][0]) > 0:
                C1.append(E.Concept(m, picks[0], picks[1], cs))
        for c in C1:
            canon(c)
        phi = E.rnd(E.ces_distance(flow, C0, C1))
        if phi == 0:
            return 0.0
        best = min(best, phi)
    return best


def spectrum(flow, net, state, nodes, canon):
    """The authors' algorithm: per cut, every pair of structures; then their band."""
    import ctypes
    cache = {}
    sub = E.Subsystem(net, state, nodes, cache=cache)
    C0 = concepts_of(flow, sub)
    for lst in C0.values():
        for c in lst:
            canon(c)
    n_struct = 1
    for lst in C0.values():
        n_struct *= len(lst)
    cuts = []
    for A, B in E.directed_bipartition(tuple(range(sub.k)), nontrivial=True):
        cs = E.Subsystem(net, state, nodes, cut=(A, B), tables=sub.uncut, cache=cache)
        C1 = concepts_of(flow, cs)
        for lst in C1.values():
            for c in lst:
                canon(c)
        mechs = sorted(set(C0) | set(C1), key=lambda m: (len(m), m))
        olist = [c for m in mechs for c in C0.get(m, [])]
        nlist = [c for m in mechs for c in C1.get(m, [])]
        oidx = {id(c): i for i, c in enumerate(olist)}
        nidx = {id(c): i for i, c in enumerate(nlist)}
        o_off, o_ids, n_off, n_ids = [0], [], [0], []
        for m in mechs:
            o_ids += [oidx[id(c)] for c in C0.get(m, [])]
            o_off.append(len(o_ids))
            n_ids += [nidx[id(c)] for c in C1.get(m, [])]
            n_off.append(len(n_ids))
        D = [E.concept_distance(flow, a, b) if a.canon != b.canon else 0.0 for a in olist for b in nlist]

        def ints(xs):
            return (ctypes.c_int * max(1, len(xs)))(*xs)

        def dbls(xs):
            return (ctypes.c_double * max(1, len(xs)))(*xs)
        bitmap = (ctypes.c_uint8 * (NBITS // 8))()
        mn, mx = ctypes.c_double(), ctypes.c_double()
        pairs, neg, simple = ctypes.c_int64(), ctypes.c_int64(), ctypes.c_int64()
        rc = flow.lib.enumerate_cut(len(mechs), ints(o_off), ints(o_ids), ints(n_off), ints(n_ids),
                                    dbls([c.phi for c in olist]), dbls([E.null_distance(flow, c) for c in olist]),
                                    ints([c.canon for c in olist]), dbls([c.phi for c in nlist]),
                                    dbls([E.null_distance(flow, c) for c in nlist]), ints([c.canon for c in nlist]),
                                    dbls(D), max(1, len(nlist)), bitmap, NBITS, ctypes.byref(mn), ctypes.byref(mx),
                                    ctypes.byref(pairs), ctypes.byref(neg), ctypes.byref(simple), flow.mode)
        if rc != 0 or mx.value >= NBITS / 1e6:
            raise Refused("a cut's structures could not be enumerated")
        raw = bytes(bitmap)
        values = [8 * i + b for i, byte in enumerate(raw) if byte for b in range(8) if byte >> b & 1]
        cuts.append({"cut": [list(A), list(B)], "min": round(mn.value * 1e6), "max": round(mx.value * 1e6),
                     "values": values, "pairs": pairs.value, "negative": neg.value, "simple": simple.value})
    lo = min(c["min"] for c in cuts)
    hi = cuts[0]["max"]
    for c in cuts:
        if c["min"] == lo and c["max"] < hi:
            hi = c["max"]
    band = sorted(set(v for c in cuts for v in c["values"] if lo <= v <= hi))
    return {"structures": n_struct, "cuts": len(cuts), "pairs": sum(c["pairs"] for c in cuts),
            "negative": sum(c["negative"] for c in cuts), "band": [v / 1e6 for v in band],
            "merged": merged([v / 1e6 for v in band]), "lo": lo / 1e6, "hi": hi / 1e6,
            "per_cut": [{k: c[k] for k in ("cut", "min", "max", "pairs")} | {"n": len(c["values"])} for c in cuts]}


# ---------------------------------------------------------------- the run

def build(results):
    os.makedirs(results, exist_ok=True)
    lib = os.path.join(os.path.abspath(results), "flow.so")
    subprocess.run(["gcc", "-O2", "-shared", "-fPIC", "-o", lib, os.path.join(HERE, "flow.c"), "-lm"], check=True)
    return lib


def run(inputs="inputs", results="results", log=None, only=None):
    say = log or (lambda s: None)
    files = load(inputs)
    spec = files["phi_spectrum.py"]
    if TIE_RULE not in spec or not all(r in spec for r in BAND_RULE):
        raise Refused("phi_spectrum.py does not hold the tie and band rules as read")
    corpus = systems(files)
    if only:
        corpus = [s for s in corpus if s["name"] in only]
    lib = build(results)
    flows = {1: E.Flow(lib, 1), 0: E.Flow(lib, 0)}

    detail = []
    for s in corpus:
        net = E.Network(s["tpm"])
        row = {k: s[k] for k in ("name", "state", "nodes", "size", "published", "notes")}
        for mode in (1, 0):
            t0 = time.time()
            ids = {}

            def canon(c):
                c.canon = ids.setdefault(c.signature(), len(ids))
            sp = spectrum(flows[mode], net, s["state"], s["nodes"], canon)
            sp["seconds"] = round(time.time() - t0, 1)
            row["pyphi" if mode == 1 else "exact"] = sp
        ids = {}

        def canon1(c):
            c.canon = ids.setdefault(c.signature(), len(ids))
        row["pyphi_value"] = pyphi_value(flows[1], net, s["state"], s["nodes"], canon1)
        if s["notebook"]:
            printed = printed_band(files[s["notebook"]])
            row["printed"] = {"n": len(printed), "merged": len(merged(printed)),
                              "equal": same(merged(printed), row["pyphi"]["merged"])}
        say(f"{s['name']}: PyPhi {row['pyphi_value']} (Table 1 {s['published']}); possible values "
            f"{len(row['pyphi']['merged'])} in [{row['pyphi']['lo']}, {row['pyphi']['hi']}] (pyemd), "
            f"{len(row['exact']['merged'])} in [{row['exact']['lo']}, {row['exact']['hi']}] (exact)")
        detail.append(row)

    def count(mode):
        multi = [r["name"] for r in detail if len(r[mode]["merged"]) > 1]
        both = [r["name"] for r in detail if r[mode]["merged"][0] == 0 and r[mode]["merged"][-1] > 0]
        return multi, both
    multi1, both1 = count("pyphi")
    multi0, both0 = count("exact")

    fl = flows[1]
    controls = []
    one = fl.transport([1.0], [1.0], [[1.0]])
    controls.append({"control": "one unit, one step", "value": one, "holds": abs(one - 1) < 1e-12})
    p, q = [0.25] * 4, [1 / 3, 1 / 6, 1 / 6, 1 / 3]
    v1, v0 = flows[1].hamming_emd(p, q), flows[0].hamming_emd(p, q)
    controls.append({"control": "pyemd's 0.166666, exact 1/6", "pyemd": v1, "exact": v0,
                     "holds": abs(v1 - 0.166666) < 1e-12 and abs(v0 - 1 / 6) < 1e-12})
    for r in detail:
        if r.get("printed") is not None and dict((s[0], s[4]) for s in SYSTEMS)[r["name"]] in CHECKED_BANDS:
            controls.append({"control": f"printed spectrum of {r['name']}", "printed": r["printed"],
                             "holds": r["printed"]["equal"]})
    andor = [r for r in detail if r["name"] == "AND+OR"]
    if andor:
        controls.append({"control": "AND+OR's PyPhi value as Table 1", "value": andor[0]["pyphi_value"],
                         "holds": round(andor[0]["pyphi_value"], 4) == andor[0]["published"]})
    held = sum(1 for c in controls if c["holds"])

    passed = len(multi1) >= 8 and len(both1) >= 1 and held == len(controls) and len(detail) == 10
    by = {r["name"]: r for r in detail}
    oiz = by.get("Oizumi et al. 2014")
    out = {
        "systems": len(detail),
        "nonunique_pyphi": len(multi1),
        "both_pyphi": len(both1),
        "nonunique_exact": len(multi0),
        "both_exact": len(both0),
        "published_matched": sum(1 for r in detail if round(r["pyphi_value"], 4) == r["published"]),
        "photodiode_values": len(by["Photodiode"]["pyphi"]["merged"]) if "Photodiode" in by else -1,
        "oizumi_values_pyphi": len(oiz["pyphi"]["merged"]) if oiz else -1,
        "oizumi_values_exact": len(oiz["exact"]["merged"]) if oiz else -1,
        "oizumi_structures_pyphi": oiz["pyphi"]["structures"] if oiz else -1,
        "oizumi_structures_exact": oiz["exact"]["structures"] if oiz else -1,
        "values_total_pyphi": sum(len(r["pyphi"]["merged"]) for r in detail),
        "values_total_exact": sum(len(r["exact"]["merged"]) for r in detail),
        "pairs_total": sum(r["pyphi"]["pairs"] + r["exact"]["pairs"] for r in detail),
        "negative_null": sum(r["pyphi"]["negative"] + r["exact"]["negative"] for r in detail),
        "controls_passed": held,
        "controls_total": len(controls),
        "test_passed": int(passed),
    }
    det = {"inputs": {k: {"sha256": v[0], "bytes": v[1]} for k, v in INPUTS.items()}, "commit": COMMIT,
           "systems": detail, "nonunique": {"pyphi": multi1, "exact": multi0},
           "both": {"pyphi": both1, "exact": both0}, "controls": controls}
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as f:
        json.dump(det, f, indent=1, sort_keys=True)
        f.write("\n")
    return out, det


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(log=lambda s: print(s, file=sys.stderr, flush=True))
    except Refused as e:
        sys.exit(f"iit/check.py: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
