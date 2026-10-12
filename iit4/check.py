#!/usr/bin/env python3
"""A computer that simulates a system exactly but not its cause-effect structure, under IIT 4.0, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:48aa3af09abe12bb) is from Findlay, Marshall,
Albantakis, David, Mayner, Koch & Tononi, "Dissociating Artificial Intelligence from Artificial Consciousness"
(arXiv:2412.04571): "We consider pairs of systems constituted of simple Boolean units, one of which -- a basic
stored-program computer -- simulates the other with full functional equivalence. By applying the principles of IIT, we
demonstrate that (i) two systems can be functionally equivalent without being phenomenally equivalent, and (ii) that
this conclusion is not dependent on the simulated system's function." Its registered test: refuted if, under IIT 4.0
as the authors' code computes it (PyPhi c1a7f4e with their pyphi_config.yml), PQRS in state 0101 is not a complex of all
four units with 13 distinctions; or the paper's 117-unit weakly connected computer, programmed for PQRS from 0101 or for
WXyZ from 1101, fails to show the target's successive states on its data registers every eight updates; or, in its
initial state as the authors' code sets it, under either program, it holds a complex of more than four units, or one
with Phi above 6 ibits (beyond 1e-9) or more than four distinctions.

IIT 4.0 is iit4/engine.py, Imago's own, written from PyPhi's source at c1a7f4e read as data (its docstring lists the
conventions). The computer is iit4/computer.py, a port of the authors' divided_clock_computer.py with graphiit's graph
semantics. Neither runs a line of the authors' code or of PyPhi. Every rule below was fixed before any seed existed.

Reading (each refusal stops the run before anything is computed):
1. The eight inputs (the claim's data of record) must be the committed bytes, by SHA-256.
2. pyphi_config.yml must set the sixteen options the engine follows to the values it follows (CONFIG below), and
   uv.lock must pin pyphi to wmayner/pyphi at c1a7f4e151f2bf9e6bc988f0af221ed37cd56765 and graphiit to CSC-UW/graphiit
   at 1318d8b42a63c9048a76768b8e4a106e7074052d.
3. The TPMs and states of PQRS and WXyZ are read with ast from findlay2024a.py (get_pqrs_micro_example,
   get_wxyz_micro_example), and divided_clock_computer.py must hold the same TPMs and states (get_pQrS_graphiit,
   get_WXyZ_graphiit) and every function the port follows.
4. The e-print's main.tex must hold verbatim each printed number the test uses (PRINTED below).

The test:
5. PQRS in 0101: every candidate system (every reachable subset) is analysed; the complexes are taken as the authors'
   condensed() takes them (positive phi_s, in decreasing phi_s, each kept unless it overlaps one already kept). The
   first must be all four units, and its Phi-structure must hold 13 distinctions.
6. The computer, programmed as get_initial_state_config programs it (the program bits where the target's TPM has a 1,
   the data registers' outputs where its state has a 1, and C0), for PQRS from 0101 and for WXyZ from 1101: after one
   update and then every 8, the four data-register outputs must be the target's successive states, 20 times each.
7. The computer's complexes in that initial state, for each program. Candidates: every strongly connected set within
   a cyclic strongly connected component of the computer's graph once the four registers' AND units (T0R1 to T3R1)
   are set aside. Why that is every set that can be a complex: a set that is not strongly connected has phi_s 0 (as
   in PyPhi); and while A2 is OFF and outside the set, T_iR1 = AND(T_iR2, A2) is 0 whatever the set's state, so the
   SET_UNI/BI cut that severs only the connections from the rest of the set into T_iR1 leaves every effect probability
   unchanged, its information is 0, and the set's phi_s is not positive. A2 can never share a strongly connected set
   with a data-path unit (nothing in the data path feeds the clock). The run refuses unless A2 is OFF in the initial
   state and each T_iR1 gives 0 for every input with A2 = 0. Each candidate is analysed as the authors' notebooks
   analyse it (Figure 3 for pQrS, Figure 5 for WXyZ, read from their code cells): the program rings in graphiit's
   subgraph, each single unit in the subgraph or the vokram blanket its cell names; a candidate no cell names, in the
   vokram blanket (get_sia_and_ces's default). The complexes are the candidates with positive phi_s.
test_passed is 1 if 5 and 6 hold and, under both programs, no complex has more than four units, Phi above 6 + 1e-9
or more than four distinctions; else 0.

Beside the test, from the seed: 50 programs drawn as the authors' check_k_simulation draws them (each row of the
target's TPM a uniformly drawn state) with a drawn initial state, each simulated for 20 transitions and its complexes
found as in 7. Randomness only from ECDYSIS_SEED: program i from PCG64 seeded with SHA-256(seed || "|findlay/program|"
|| i).

Beside the test, the order of the units. PyPhi breaks ties between states of equal information and between purviews of
equal phi by the order of the units (their indices, and the iteration order of a set of index tuples), and the engine
follows it, so one system can receive a different Phi-structure under another labelling; the test takes the authors'
order. pqrs_orders: PQRS in 0101 under all 24 orders of its units (the same dynamics, relabelled), the first complex's
units, phi_s, Phi, distinctions and relations as ranges, and in how many orders the dissociation holds (the first
complex all four units, with more distinctions and a larger Phi than any complex of the computer in any order of its
units). computer_orders: every candidate of the computer of more than one unit, under both programs, analysed again
under all 24 orders of its units within the network it is analysed in.

Controls (controls_passed counts those that behave as stated):
  1. the authors' table of PQRS in all 16 states (Figure8.ipynb's printed output): every row as printed (complexes,
     phi_s and Phi to two decimals, the mechanisms of the distinctions, the number of relations);
  2, 3. the 16 program rings' phi_s and Phi as Figure3.ipynb and Figure5.ipynb print them;
  4, 5. the single units those notebooks analyse (C0, X1, A1, X2, A2, T0R0 to T3R0), phi_s and Phi as printed;
  6. a flipped program bit (the row of 0101, unit P) breaks the simulation; 7. a flipped data register breaks it;
  8. a gated loop (X = COPY(Y), Y = AND(X, G)): phi_s 0 with G OFF, positive with G ON, the mechanism of rule 7;
  9. two units of a program ring, not strongly connected, have phi_s 0 where the ring has 2;
  10. every cycle of both TPMs simulated exactly (the authors' check_tpm_simulation).

What it cannot check: the supplement's proofs for every reachable state, the strongly connected computer and
computers of any size; whether IIT's postulates are right; PyPhi itself, which is not run (the engine follows it, and
tests/test_iit4.py holds the engine to PyPhi c1a7f4e's own results, computed in a sandbox with no network).

Writes results/outputs.json and results/detail.json. Run with: python3 iit4/check.py
"""

import ast
import hashlib
import io
import itertools
import json
import os
import re
import sys
import tarfile
import time
import warnings

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from iit4 import computer as C  # noqa: E402
from iit4 import engine as E  # noqa: E402

INPUTS = {
    "divided_clock_computer.py": "9aa666909071075b789881203698cfcf6b817153465027586f8147f8927e0048",
    "findlay2024a.py": "cdd22afd4296cc925213aced98b422b19c98655f04f63b862ae79d59d67aeba5",
    "pyphi_config.yml": "4b505df965a28d612a47dd48955c1a899786872141c38d374de03a07ca035e7b",
    "uv.lock": "d91494a0622aa6f5cee49d018e814ecbf6730f23db0fc01e39f03fdca907b708",
    "Figure8.ipynb": "d9920c072cfaf098e578f0349bfbaf43de1e72056dca06b4613daa773d85077a",
    "Figure3.ipynb": "813c1d1ed24c176373ab8e248239a5ebe4e5c6daab688796136ab0739c699f73",
    "Figure5.ipynb": "c30e8569468a6a8b90e8b679b970c96f7424dcbd122262d93f2c2a84df92d896",
    "arXiv-2412.04571v2.tar.gz": "856ea2dcc32318640315ab2cba7c59bf36285effc108210bfb601b6f8596b530",
}
CONFIG = {
    "IIT_VERSION": "4.0", "REPERTOIRE_DISTANCE": "GENERALIZED_INTRINSIC_DIFFERENCE",
    "REPERTOIRE_DISTANCE_INFORMATION": "GENERALIZED_INTRINSIC_DIFFERENCE", "SYSTEM_PARTITION_TYPE": "SET_UNI/BI",
    "SYSTEM_CUTS": "3.0_STYLE", "SYSTEM_PARTITION_INCLUDE_COMPLETE": "false", "PARTITION_TYPE": "ALL",
    "DISTINCTION_PHI_NORMALIZATION": "NUM_CONNECTIONS_CUT", "MIP_TIE_RESOLUTION": "NORMALIZED_PHI,NEGATIVE_PHI",
    "PURVIEW_TIE_RESOLUTION": "PHI", "STATE_TIE_RESOLUTION": "PHI", "RELATION_COMPUTATION": "CONCRETE",
    "SINGLE_MICRO_NODES_WITH_SELFLOOPS_HAVE_PHI": "true", "SHORTCIRCUIT_SIA": "true",
    "VALIDATE_SUBSYSTEM_STATES": "true", "PRECISION": "13",
}
PINS = ('source = { git = "https://github.com/wmayner/pyphi?branch=feature%2Fiit-4.0'
        '#c1a7f4e151f2bf9e6bc988f0af221ed37cd56765" }',
        'source = { git = "https://github.com/CSC-UW/graphiit?branch=feature%2Fiit-4.0'
        '#1318d8b42a63c9048a76768b8e4a106e7074052d" }')
PRINTED = (
    "is composed of 13 distinctions and 8184 relations and has $\\Phi = 391.25$ ibits",
    "constituted of 117 micro units",
    "each one constituted of between one and four units, each with $\\Phi \\leq 6$ ibits",
    "(1--4 distinctions, whereas $pQrS$ has 13)",
    "After eight updates",
)
PORTED = ("get_clock_config", "get_program_config", "get_instruction_register_config", "get_data_register_config",
          "get_buffer_config", "get_mux_config", "get_mux_out_config", "get_initial_state_config",
          "get_graph_config", "check_tpm_simulation")
K = 2
TRANSITIONS = 20
PROGRAMS = 50
BOUND = 6.0
SLACK = 1e-9
LIMIT = 200
OUTPUTS = (
    "pqrs_complexes", "pqrs_phi_s", "pqrs_big_phi", "pqrs_distinctions", "pqrs_relations", "pqrs_orders",
    "wxyz_complexes", "table_rows", "simulation", "graph", "complexes", "max_units", "max_big_phi", "max_distinctions",
    "ring_big_phi", "computer_orders", "random_programs", "controls_passed", "controls_total", "test_passed",
)


class Refused(Exception):
    pass


# ---------------------------------------------------------------- reading the data of record

def load(directory, name):
    with open(os.path.join(directory, name), "rb") as f:
        data = f.read()
    got = hashlib.sha256(data).hexdigest()
    if got != INPUTS[name]:
        raise Refused(f"{name}: sha256 {got}, not the committed {INPUTS[name]}")
    return data


def read_config(text):
    """The top-level options of a simple YAML file: scalars, and lists of '- item' lines joined by commas."""
    out, key = {}, None
    for line in text.splitlines():
        m = re.match(r"^([A-Z_0-9]+):\s*(.*)$", line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            out[key] = value
        elif key and re.match(r"^- (.+)$", line):
            item = line[2:].strip()
            out[key] = item if not out[key] else out[key] + "," + item
    return out


def check_config(text):
    got = read_config(text)
    wrong = {k: got.get(k) for k, v in CONFIG.items() if got.get(k) != v}
    if wrong:
        raise Refused(f"pyphi_config.yml: {wrong} where the engine follows {[(k, CONFIG[k]) for k in wrong]}")


def tpm_literals(source, functions):
    """{function: (tpm, state)} read with ast from the assignments to `tpm` and `state` in each named function."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tree = ast.parse(source)
    out = {}
    for fn in tree.body:
        if isinstance(fn, ast.FunctionDef) and fn.name in functions:
            tpm = state = None
            for node in ast.walk(fn):
                if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                    if node.targets[0].id == "tpm":
                        tpm = [[int(v) for v in row] for row in ast.literal_eval(node.value.args[0])]
                    elif node.targets[0].id == "state":
                        state = tuple(ast.literal_eval(node.value))
            out[fn.name] = (tpm, state)
    missing = [f for f in functions if f not in out or None in out[f]]
    if missing:
        raise Refused(f"no TPM or state found in {missing}")
    return out


def notebook(data):
    return json.loads(data.decode("utf-8"))


def cells(nb):
    """[(source, stdout text)] of each code cell."""
    out = []
    for c in nb["cells"]:
        if c.get("cell_type") != "code":
            continue
        text = "".join("".join(o.get("text", [])) for o in c.get("outputs", [])
                       if o.get("output_type") == "stream" and o.get("name") == "stdout")
        out.append(("".join(c.get("source", [])), text))
    return out


def figure8_table(nb):
    """The printed rows: {state: (complexes, phi_s, Phi, distinctions, relations)}, all as printed strings or lists."""
    text = next(t for s, t in cells(nb) if "summarize_all_states" in s)
    rows = {}
    pattern = (r"Network state: \(([0-9, ]+)\)\nComplexes: (\[.*\])\n\s+φ_s: (\[.*\])\n\s+Φ: (\[.*\])\n"
               r"\s+Distinctions: (\[.*\])\n\s+#\(relations\): (\[.*\])")
    for m in re.finditer(pattern, text):
        state = tuple(int(v) for v in m.group(1).split(","))
        rows[state] = tuple(ast.literal_eval(m.group(i)) for i in range(2, 7))
    if len(rows) != 16:
        raise Refused(f"Figure8.ipynb: {len(rows)} printed rows, not 16")
    return rows


def figure_rings_and_units(nb):
    """(the printed rings' phi_s and Phi lists, {unit: (vokram flag, printed phi_s, printed Phi)}, rings' flag)."""
    rings = units = None
    ring_flag = None
    units = {}
    for source, text in cells(nb):
        if "program_units" in source and "Sys phi" in text:
            ring_flag = "vokram_blanket=True" in source
            phis = ast.literal_eval(re.search(r"Sys phi:\s+(\[.*?\])", text).group(1))
            bigs = ast.literal_eval(re.search(r"Big phi:\s+(\[.*?\])", text).group(1))
            rings = (phis, bigs)
        m = re.search(r'get_sia_and_ces\(graph, \["([^"]+)"\], vokram_blanket=(True|False)\)', source)
        if m:
            values = [float(v) for v in text.split()]
            units[m.group(1)] = (m.group(2) == "True", values[0], values[1])
    if rings is None or ring_flag is None or len(units) != 9:
        raise Refused("a Figure notebook does not hold its rings and nine single units as expected")
    return rings, units, ring_flag


def main_tex(data):
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        member = tar.getmember("main.tex")
        return tar.extractfile(member).read().decode("utf-8")


def check_lock(lock):
    missing = [p for p in PINS if p not in lock]
    if missing:
        raise Refused(f"uv.lock does not pin {missing}")


def check_printed(tex):
    unprinted = [p for p in PRINTED if p not in tex]
    if unprinted:
        raise Refused(f"main.tex does not print {unprinted}")


def check_ported(source):
    absent = [f for f in PORTED if f"def {f}(" not in source]
    if absent:
        raise Refused(f"divided_clock_computer.py lacks {absent}")


def read_inputs(directory):
    raw = {name: load(directory, name) for name in INPUTS}
    check_config(raw["pyphi_config.yml"].decode("utf-8"))
    check_lock(raw["uv.lock"].decode("utf-8"))
    targets = tpm_literals(raw["findlay2024a.py"].decode("utf-8"), ("get_pqrs_micro_example", "get_wxyz_micro_example"))
    dcc_source = raw["divided_clock_computer.py"].decode("utf-8")
    dcc = tpm_literals(dcc_source, ("get_pQrS_graphiit", "get_WXyZ_graphiit"))
    if dcc["get_pQrS_graphiit"] != targets["get_pqrs_micro_example"] or \
            dcc["get_WXyZ_graphiit"] != targets["get_wxyz_micro_example"]:
        raise Refused("divided_clock_computer.py and findlay2024a.py hold different TPMs or states")
    check_ported(dcc_source)
    check_printed(main_tex(raw["arXiv-2412.04571v2.tar.gz"]))
    return {
        "pqrs": targets["get_pqrs_micro_example"], "wxyz": targets["get_wxyz_micro_example"],
        "figure8": figure8_table(notebook(raw["Figure8.ipynb"])),
        "figure3": figure_rings_and_units(notebook(raw["Figure3.ipynb"])),
        "figure5": figure_rings_and_units(notebook(raw["Figure5.ipynb"])),
    }


# ---------------------------------------------------------------- the analyses

def condensed_rows(network, state):
    """The authors' summarize_all_states row for one state, rendered as they print it."""
    complexes, phis, bigs, distinctions, relations = [], [], [], [], []
    for phi, nodes, states in E.condensed(network, state):
        structure = E.Subsystem(network, state, nodes).phi_structure(states)
        complexes.append("".join(network.labels[i] for i in nodes))
        phis.append(f"{phi:.2f}")
        bigs.append(f"{structure.big_phi:.2f}")
        distinctions.append([[network.labels[i] for i in d.mechanism] for d in structure.distinctions])
        relations.append(len(structure.relations))
    return complexes, phis, bigs, distinctions, relations


def candidates(graph):
    """Rule 7's candidates: strongly connected sets within the cyclic components once the AND units are set aside."""
    ands = [r[1] for r in C.labels(K)["registers"]]
    if graph.state["A2"] != 0:
        raise Refused("A2 is not OFF in the initial state")
    for u in ands:
        f = graph.function[u]
        parents = graph.parents[u]
        for values in E.all_states(len(parents)):
            if dict(zip(parents, values)).get("A2") == 0 and f(list(values)) != 0:
                raise Refused(f"{u} is not 0 with A2 OFF")
    out = []
    for component in C.strongly_connected_components(graph, removed=ands):
        if not C.cyclic(graph, component):
            continue
        if len(component) > 8:
            raise Refused(f"a cyclic component of {len(component)} units: rule 7 enumerates components of at most 8")
        for subset in E.powerset(component, nonempty=True):
            cm = np.zeros((len(subset), len(subset)), dtype=int)
            for a, u in enumerate(subset):
                for b, v in enumerate(subset):
                    cm[a][b] = int(u in graph.parents[v])
            if len(subset) == 1 and not cm[0][0]:
                continue
            if E.strongly_connected(cm, range(len(subset))):
                out.append(tuple(subset))
    return out


def treatments(figure):
    (_, _), units, ring_flag = figure
    return {u: flag for u, (flag, _, _) in units.items()}, ring_flag


def analyse_candidate(graph, units, vokram):
    blanket = graph.vokram_blanket(units) if vokram else graph.subgraph(units)
    network = blanket.network()
    state = blanket.state_array()
    result = E.analyse(network, state, tuple(blanket.units.index(u) for u in units))
    result["units"] = tuple(units)
    result["vokram"] = vokram
    return result


def computer_complexes(target, figure):
    tpm, state = target
    graph = C.computer(K, tpm, state)
    unit_flags, ring_flag = treatments(figure)
    rings = [tuple(line) for line in C.labels(K)["program"]]
    results = []
    for cand in candidates(graph):
        if cand in rings:
            vokram = ring_flag
        elif len(cand) == 1 and cand[0] in unit_flags:
            vokram = unit_flags[cand[0]]
        else:
            vokram = True
        results.append(analyse_candidate(graph, list(cand), vokram))
    complexes = [r for r in results if E.positive(r["phi_s"])]
    return graph, results, complexes


def summary(complexes):
    return (max(len(r["units"]) for r in complexes), max(r["big_phi"] for r in complexes),
            max(r["distinctions"] for r in complexes))


# ---------------------------------------------------------------- the order of the units

def permuted(tpm, state, order, labels):
    """The same system with its units in another order (order[j] is the original unit at position j): its network,
    with the units' labels carried, and its state."""
    n = len(order)
    rows = []
    for s in E.all_states(n):
        original = [0] * n
        for j in range(n):
            original[order[j]] = s[j]
        nxt = tpm[sum(v << i for i, v in enumerate(original))]
        rows.append([nxt[order[j]] for j in range(n)])
    return (E.Network(rows, labels="".join(labels[order[j]] for j in range(n))),
            tuple(state[order[j]] for j in range(n)))


def pqrs_orders(tpm, state, labels="PQRS"):
    """PQRS's first complex and its Phi-structure under every order of its units."""
    out = []
    for order in itertools.permutations(range(len(labels))):
        network, st = permuted(tpm, state, order, labels)
        phi, nodes, states = E.condensed(network, st)[0]
        structure = E.Subsystem(network, st, nodes).phi_structure(states)
        out.append({"order": network.labels, "units": "".join(sorted(network.labels[i] for i in nodes)),
                    "phi_s": float(phi), "big_phi": float(structure.big_phi),
                    "distinctions": len(structure.distinctions), "relations": len(structure.relations)})
    return out


def reordered(graph, units, order):
    """The same graph with the given units at the positions they held, in the given order."""
    positions = sorted(graph.units.index(u) for u in units)
    by_label = {u[0]: u for u in graph.config}
    config = list(graph.config)
    for p, u in zip(positions, order):
        config[p] = by_label[u]
    return C.Graph(config, graph.state)


def complex_orders(graph, result):
    """A complex of the computer analysed again under every order of its units, in the network it was analysed in."""
    units = list(result["units"])
    base = graph.vokram_blanket(units) if result["vokram"] else graph.subgraph(units)
    out = []
    for order in itertools.permutations(units):
        g = reordered(base, units, order)
        r = E.analyse(g.network(), g.state_array(), tuple(g.units.index(u) for u in units))
        out.append({k: r[k] for k in ("phi_s", "big_phi", "distinctions", "relations")} | {"order": order})
    return out


def draw_program(seed, i):
    digest = hashlib.sha256(bytes.fromhex(seed) + b"|findlay/program|" + str(i).encode("ascii")).digest()
    rng = np.random.Generator(np.random.PCG64(int.from_bytes(digest, "big")))
    n = 2 ** K
    states = list(E.all_states(n))
    tpm = [list(states[j]) for j in rng.integers(0, 2 ** n, size=2 ** n)]
    initial = tuple(int(v) for v in rng.integers(0, 2, size=n))
    return tpm, initial


# ---------------------------------------------------------------- controls

def controls(data, pqrs_network, figure3_results, figure5_results):
    rows = []
    table_ok = 0
    for state, printed in data["figure8"].items():
        mine = condensed_rows(pqrs_network, state)
        table_ok += int(tuple(mine) == tuple(printed))
    rows.append({"control": "Figure 8: PQRS in all 16 states as printed", "passed": table_ok == 16,
                 "detail": f"{table_ok} of 16"})
    for name, figure, results in (("Figure 3", data["figure3"], figure3_results),
                                  ("Figure 5", data["figure5"], figure5_results)):
        (phis, bigs), units, _ = figure
        by_units = {r["units"]: r for r in results}
        rings = [by_units[tuple(line)] for line in C.labels(K)["program"]]
        ok = sum(1 for r, p, b in zip(rings, phis, bigs) if abs(r["phi_s"] - p) < 1e-9 and abs(r["big_phi"] - b) < 1e-9)
        rows.append({"control": f"{name}: 16 program rings' phi_s and Phi as printed", "passed": ok == 16,
                     "detail": f"{ok} of 16"})
        ok_units = sum(1 for u, (_, p, b) in units.items()
                       if abs(by_units[(u,)]["phi_s"] - p) < 1e-9 and abs(by_units[(u,)]["big_phi"] - b) < 1e-9)
        rows.append({"control": f"{name}: nine single units as printed", "passed": ok_units == 9,
                     "detail": f"{ok_units} of 9"})
    tpm, state = data["pqrs"]
    row = sum(v << i for i, v in enumerate(state))
    flipped = [r[:] for r in tpm]
    flipped[row][0] = 1 - flipped[row][0]
    # the computer programmed with the flipped bit, against the original TPM's trajectory
    graph = C.computer(K, flipped, state)
    outputs = [r[0] for r in C.labels(K)["registers"]]
    expected, broke = tuple(state), False
    graph.tic(1)
    for _ in range(TRANSITIONS):
        if tuple(int(graph.state[o]) for o in outputs) != expected:
            broke = True
            break
        expected = tuple(tpm[sum(v << i for i, v in enumerate(expected))])
        graph.tic(2 ** (K + 1))
    rows.append({"control": "a flipped program bit breaks the simulation of PQRS", "passed": broke})
    graph = C.computer(K, tpm, state)
    graph.state["T0R0"] = 1 - graph.state["T0R0"]
    graph.tic(1)
    rows.append({"control": "a flipped data register breaks it",
                 "passed": tuple(int(graph.state[o]) for o in outputs) != tuple(state)})
    gated = []
    for g_state in (0, 1):
        graph = C.Graph([("X", "COPY", "Y"), ("Y", "AND", "X", "G"), ("G", "COPY", "G")], {"X": 0, "Y": 0, "G": g_state})
        gated.append(E.Subsystem(graph.network(), graph.state_array(), (0, 1)).sia()[0])
    rows.append({"control": "a gated loop: phi_s 0 with G OFF, positive with G ON",
                 "passed": not E.positive(gated[0]) and E.positive(gated[1]), "detail": gated})
    graph = C.computer(K, tpm, state)
    pair = ["T0/0", "T1/0"]
    sub = graph.subgraph(pair)
    phi_pair = E.Subsystem(sub.network(), sub.state_array(), (0, 1)).sia()[0]
    rows.append({"control": "two units of a ring, not strongly connected, have phi_s 0", "passed": phi_pair == 0.0})
    cyc = C.check_every_cycle(K, data["pqrs"][0]) and C.check_every_cycle(K, data["wxyz"][0])
    rows.append({"control": "every cycle of both TPMs simulated exactly", "passed": bool(cyc)})
    return rows, table_ok


# ---------------------------------------------------------------- the run

def run(seed, results="results", inputs="inputs", programs=PROGRAMS, log=print):
    started = time.monotonic()
    data = read_inputs(inputs)
    pqrs_tpm, pqrs_state = data["pqrs"]
    if tuple(pqrs_state) != (0, 1, 0, 1) or tuple(data["wxyz"][1]) != (1, 1, 0, 1):
        raise Refused("the targets' states are not 0101 and 1101")
    network = E.Network(pqrs_tpm, labels="PQRS")
    complexes = E.condensed(network, pqrs_state)
    first = complexes[0]
    structure = E.Subsystem(network, pqrs_state, first[1]).phi_structure(first[2])
    log(f"findlay: PQRS in 0101: {[''.join(network.labels[i] for i in c[1]) for c in complexes]}, "
        f"phi_s {first[0]:.6f}, Phi {structure.big_phi:.6f}, {len(structure.distinctions)} distinctions")
    wx = E.Network(data["wxyz"][0], labels="WXYZ")
    wx_complexes = E.condensed(wx, data["wxyz"][1])
    sims = {name: C.simulate(K, data[name][0], data[name][1], TRANSITIONS) for name in ("pqrs", "wxyz")}
    graph_p, results_p, complexes_p = computer_complexes(data["pqrs"], data["figure3"])
    graph_w, results_w, complexes_w = computer_complexes(data["wxyz"], data["figure5"])
    log(f"findlay: computer: {len(results_p)} candidates; {len(complexes_p)} and {len(complexes_w)} complexes")
    sum_p, sum_w = summary(complexes_p), summary(complexes_w)
    max_units, max_big, max_dist = (max(sum_p[0], sum_w[0]), max(sum_p[1], sum_w[1]), max(sum_p[2], sum_w[2]))
    several = [(graph_p, r) for r in results_p if len(r["units"]) > 1] + \
              [(graph_w, r) for r in results_w if len(r["units"]) > 1]
    regrouped = [(r, complex_orders(g, r)) for g, r in several]
    reordered_all = [o for _, group in regrouped for o in group]
    differs = sum(1 for r, group in regrouped
                  if any(abs(o["phi_s"] - r["phi_s"]) > 1e-9 or abs(o["big_phi"] - r["big_phi"]) > 1e-9
                         or (o["distinctions"], o["relations"]) != (r["distinctions"], r["relations"]) for o in group))
    any_order_big = max([max_big] + [o["big_phi"] for o in reordered_all if E.positive(o["phi_s"])])
    any_order_dist = max([max_dist] + [o["distinctions"] for o in reordered_all if E.positive(o["phi_s"])])
    orders = pqrs_orders(pqrs_tpm, pqrs_state)
    dissociated = sum(1 for o in orders if o["units"] == "PQRS" and o["distinctions"] > any_order_dist
                      and o["big_phi"] > any_order_big + SLACK)
    log(f"findlay: PQRS under {len(orders)} orders: Phi {min(o['big_phi'] for o in orders):.6f} to "
        f"{max(o['big_phi'] for o in orders):.6f}; computer under {len(reordered_all)} orders: Phi at most "
        f"{any_order_big:.6f}, {differs} candidates differ")
    rows, table_ok = controls(data, network, results_p, results_w)
    drawn = []
    for i in range(programs):
        tpm, initial = draw_program(seed, i)
        matched, _ = C.simulate(K, tpm, initial, TRANSITIONS)
        _, _, cx = computer_complexes((tpm, initial), data["figure3"])
        drawn.append((matched, summary(cx)))
    exact = sum(1 for m, _ in drawn if m == TRANSITIONS)
    drawn_max = (max(s[0] for _, s in drawn), max(s[1] for _, s in drawn), max(s[2] for _, s in drawn)) if drawn \
        else (0, 0.0, 0)
    test = (len(first[1]) == 4 and len(structure.distinctions) == 13
            and all(m == TRANSITIONS for m, _ in sims.values())
            and max_units <= 4 and max_big <= BOUND + SLACK and max_dist <= 4)
    rings = C.labels(K)["program"]

    def ring_list(results):
        by = {r["units"]: r for r in results}
        return ",".join(f"{by[tuple(line)]['big_phi']:g}" for line in rings)

    def span(key, fmt):
        low, high = min(o[key] for o in orders), max(o[key] for o in orders)
        return f"{low:{fmt}} to {high:{fmt}}"

    def span_all(key, fmt):
        low, high = min(o[key] for o in reordered_all), max(o[key] for o in reordered_all)
        return f"{low:{fmt}} to {high:{fmt}}"

    values = {
        "pqrs_complexes": ",".join("".join(network.labels[i] for i in c[1]) for c in complexes),
        "pqrs_phi_s": round(float(first[0]), 9),
        "pqrs_big_phi": round(float(structure.big_phi), 9),
        "pqrs_distinctions": len(structure.distinctions),
        "pqrs_relations": len(structure.relations),
        "pqrs_orders": (f"{len(orders)} orders: all four units first in "
                        f"{sum(1 for o in orders if o['units'] == 'PQRS')}; phi_s {span('phi_s', '.6f')}; "
                        f"Phi {span('big_phi', '.2f')}; distinctions {span('distinctions', 'd')} (13 in "
                        f"{sum(1 for o in orders if o['distinctions'] == 13)}); relations {span('relations', 'd')}; "
                        f"dissociation in {dissociated}"),
        "wxyz_complexes": ",".join(f"{''.join(wx.labels[i] for i in c[1])} {c[0]:.6f}" for c in wx_complexes),
        "table_rows": table_ok,
        "simulation": f"pQrS {sims['pqrs'][0]}/{TRANSITIONS}, WXyZ {sims['wxyz'][0]}/{TRANSITIONS}",
        "graph": f"{len(graph_p.units)} units, {graph_p.edges()} connections, {len(results_p)} candidates",
        "complexes": f"{len(complexes_p)},{len(complexes_w)}",
        "max_units": max_units,
        "max_big_phi": round(float(max_big), 9),
        "max_distinctions": max_dist,
        "ring_big_phi": ring_list(results_p) + ";" + ring_list(results_w),
        "computer_orders": (f"{len(regrouped)} candidates of 2+ units, {len(reordered_all)} orders: phi_s "
                            f"{span_all('phi_s', 'g')}, Phi {span_all('big_phi', 'g')}, distinctions "
                            f"{span_all('distinctions', 'd')}; differs from the authors' order in {differs}"),
        "random_programs": (f"{exact} of {programs} exact; largest complex {drawn_max[0]} units, "
                            f"Phi {drawn_max[1]:.6f}, {drawn_max[2]} distinctions"),
        "controls_passed": sum(1 for r in rows if r["passed"]),
        "controls_total": len(rows),
        "test_passed": int(test),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters")
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    detail = {
        "values": values, "controls": rows,
        "pqrs_complexes": [(c[0], [network.labels[i] for i in c[1]]) for c in complexes],
        "pqrs_distinctions": [[network.labels[i] for i in d.mechanism] for d in structure.distinctions],
        "computer": {name: [{k: r[k] for k in ("units", "vokram", "phi_s", "big_phi", "distinctions", "relations")}
                            for r in res] for name, res in (("pQrS", results_p), ("WXyZ", results_w))},
        "pqrs_orders": orders,
        "computer_orders": [{"units": r["units"], "vokram": r["vokram"],
                             "values": sorted({(round(o["phi_s"], 9), round(o["big_phi"], 9), o["distinctions"],
                                                o["relations"]) for o in group})} for r, group in regrouped],
        "drawn": [{"matched": m, "max_units": s[0], "max_big_phi": s[1], "max_distinctions": s[2]} for m, s in drawn],
        "seconds": round(time.monotonic() - started, 1),
    }
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as f:
        json.dump(detail, f, indent=1, sort_keys=True, default=str, ensure_ascii=True)
        f.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed, log=lambda s: print(s, file=sys.stderr, flush=True))
    except Refused as e:
        sys.exit(f"iit4/check.py: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
