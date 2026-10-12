#!/usr/bin/env python3
"""One system, 24 numberings: PQRS's Phi-structure under every order of its units, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ecd:892ff79094961371) is Imago's own: "Under
PyPhi c1a7f4e's IIT 4.0 with Findlay et al.'s configuration, the Phi-structure of their system PQRS in state 0101
depends on how its units are ordered: across the 24 orders Phi takes nine values, 205.05 to 397.23 ibits, with 13
distinctions in 15 orders and 12 in nine." Its test: refuted if PyPhi at commit c1a7f4e under the authors'
pyphi_config.yml, on PQRS's TPM from findlay2024a.py in state 0101 relabelled by each of the 24 permutations of its
units (the same dynamics; complexes condensed as the authors' code does), gives the first complex one Phi in every
order (within 1e-6), or values other than 205.0513, 209.8443, 210.9050, 212.0437, 390.2417, 391.2472, 395.0347,
396.0955 and 397.2342 (within 1e-4), or other than 13 distinctions in 15 orders and 12 in nine.

IIT 4.0 is iit4/engine.py, Imago's own, which tests/test_iit4.py holds to PyPhi c1a7f4e's own results; nothing of
PyPhi runs here. Every rule below was fixed before any seed existed. The run is deterministic: the seed is checked
for its form and used for nothing else.

Reading (each refusal stops the run before anything is computed):
1. The three inputs (the claim's data of record: findlay2024a.py, pyphi_config.yml, uv.lock) must be the committed
   bytes, by SHA-256.
2. pyphi_config.yml must set the options the engine follows to the values it follows, and uv.lock must pin PyPhi at
   c1a7f4e and graphiit at 1318d8b (iit4/check.py's CONFIG and PINS).
3. PQRS's TPM and state are read with ast from get_pqrs_micro_example; the state must be 0101.

The test:
4. For each of the 24 permutations of (P, Q, R, S), the system relabelled so that unit j is the old unit order[j]
   (its TPM rows and columns permuted together, the state carried with it); its complexes condensed as findlay2024a's
   condensed() takes them; the first complex's phi_s, its Phi-structure (as phi_structure computes it under the
   system's specified states), its Phi, distinctions and relations.
test_passed is 1 if the 24 values of Phi are not all within 1e-6 of one another, each lies within 1e-4 of one of the
nine stated values and each stated value is met, and exactly 15 orders give 13 distinctions and nine give 12; else 0.

Beside the test:
- every one of PQRS's 16 states under all 24 orders: how many distinct values of Phi (to 1e-6) each state's first
  complex takes, and in how many states the order changes the first complex's units, phi_s, Phi or distinctions;
- the mechanism: in the authors' order, with the engine taking tied purviews last first instead of first, the
  structure changes too (Phi, distinctions), so the dependence comes through the tie-breaking.

Controls (controls_passed counts those that behave as stated):
  1. PyPhi c1a7f4e's own recorded output for the 24 orders (iit4/reference/pyphi-c1a7f4e.json, computed in a sandbox
     with no network) equals the engine's, order by order: phi_s and Phi within 1e-6, the same numbers of
     distinctions and relations, the same units;
  2. relabelling keeps the dynamics: in every order, the relabelled TPM takes each relabelled state to the relabelled
     successor of the original;
  3. a relabelling that permutes the TPM's rows but not its columns is caught by control 2's check;
  4. a system with no ties to break, a ring of four COPY units in state 1011, gives one Phi-structure in all 24 orders;
  5. the authors' order gives the values the Findlay receipt (dac8b2ba) sealed: Phi 391.247222, 13 distinctions,
     8,184 relations.

What it cannot check: PyPhi itself, which does not run here (control 1 compares with its recorded output); whether
IIT 4.0's own rules for ties, rather than PyPhi's, would settle the structure.

Writes results/outputs.json and results/detail.json. Run with: python3 iit4/orders.py
"""

import itertools
import json
import os
import re
import sys
import time
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from iit4 import check as K  # noqa: E402
from iit4 import engine as E  # noqa: E402

INPUTS = ("findlay2024a.py", "pyphi_config.yml", "uv.lock")
STATED = (205.0513, 209.8443, 210.9050, 212.0437, 390.2417, 391.2472, 395.0347, 396.0955, 397.2342)
SAME = 1e-6
NEAR = 1e-4
LABELS = "PQRS"
REFERENCE = os.path.join(HERE, "reference", "pyphi-c1a7f4e.json")
AUTHORS = (391.247222, 13, 8184)
RING_STATE = (1, 0, 1, 1)
LIMIT = 200
OUTPUTS = ("orders", "complex_units", "phi_s", "phi_values", "distinct_phi", "phi_min", "phi_max", "orders_13",
           "orders_12", "relations", "authors_order", "pyphi_match", "states_dependent", "state_values", "mechanism",
           "controls_passed", "controls_total", "test_passed")


Refused = K.Refused


def read_inputs(directory):
    raw = {name: K.load(directory, name) for name in INPUTS}
    K.check_config(raw["pyphi_config.yml"].decode("utf-8"))
    K.check_lock(raw["uv.lock"].decode("utf-8"))
    targets = K.tpm_literals(raw["findlay2024a.py"].decode("utf-8"), ("get_pqrs_micro_example",))
    tpm, state = targets["get_pqrs_micro_example"]
    if tuple(state) != (0, 1, 0, 1):
        raise Refused(f"PQRS's state is {state}, not 0101")
    return tpm, tuple(state)


def first_complex(network, state):
    """The first condensed complex: (its units as labels, phi_s, Phi, distinctions, relations)."""
    phi, nodes, states = E.condensed(network, state)[0]
    structure = E.Subsystem(network, state, nodes).phi_structure(states)
    return ("".join(sorted(network.labels[i] for i in nodes)), float(phi), float(structure.big_phi),
            len(structure.distinctions), len(structure.relations))


def all_orders(tpm, state, labels=LABELS):
    out = []
    for order in itertools.permutations(range(len(labels))):
        network, st = K.permuted(tpm, state, order, labels)
        units, phi_s, big_phi, distinctions, relations = first_complex(network, st)
        out.append({"order": "".join(network.labels), "state": list(st), "units": units, "phi_s": phi_s,
                    "big_phi": big_phi, "distinctions": distinctions, "relations": relations})
    return out


def distinct(values, tolerance=SAME):
    groups = []
    for v in sorted(values):
        if not groups or v - groups[-1][-1] > tolerance:
            groups.append([v])
        else:
            groups[-1].append(v)
    return [g[0] for g in groups]


def verdict(rows):
    phis = [r["big_phi"] for r in rows]
    varies = max(phis) - min(phis) > SAME
    each_near = all(any(abs(p - s) <= NEAR for s in STATED) for p in phis)
    each_met = all(any(abs(p - s) <= NEAR for p in phis) for s in STATED)
    counts = (sum(1 for r in rows if r["distinctions"] == 13), sum(1 for r in rows if r["distinctions"] == 12))
    return varies and each_near and each_met and counts == (15, 9) and len(rows) == 24


def keeps_dynamics(tpm, network, order):
    """The relabelled network takes each relabelled state to the relabelled successor of the original."""
    n = len(order)
    for s in E.all_states(n):
        new = tuple(s[order[j]] for j in range(n))
        after = network.tpm[new]
        successor = tpm[sum(v << i for i, v in enumerate(s))]
        if tuple(float(after[j]) for j in range(n)) != tuple(float(successor[order[j]]) for j in range(n)):
            return False
    return True


def rows_only_permuted(tpm, order):
    """A wrong relabelling: rows moved to the new states, columns left in the old order."""
    n = len(order)
    rows = []
    for s in E.all_states(n):
        original = [0] * n
        for j in range(n):
            original[order[j]] = s[j]
        rows.append(list(tpm[sum(v << i for i, v in enumerate(original))]))
    return E.Network(rows)


def reference_rows():
    with open(REFERENCE, encoding="utf-8") as f:
        ref = json.load(f)
    out = {}
    for job in ref["jobs"]:
        if job["name"] in ("PQRS", "SRQP") or job["name"].startswith("perm-"):
            want = [{"P": 0, "Q": 1, "R": 0, "S": 1}[c] for c in job["labels"]]
            for rec in job["pyphi"]:
                if rec["state"] == want:
                    c = rec["complexes"][0]
                    out[job["labels"]] = {"units": "".join(sorted(job["labels"][i] for i in c["nodes"])),
                                          "phi_s": c["phi_s"], "big_phi": c["big_phi"],
                                          "distinctions": len(c["distinctions"]), "relations": c["relations"]}
    return out


def matches_pyphi(rows, ref):
    good = 0
    for r in rows:
        p = ref.get(r["order"])
        if p and p["units"] == r["units"] and abs(p["phi_s"] - r["phi_s"]) <= SAME and \
                abs(p["big_phi"] - r["big_phi"]) <= SAME and \
                (p["distinctions"], p["relations"]) == (r["distinctions"], r["relations"]):
            good += 1
    return good


def ring_tpm():
    return [[s[(i - 1) % 4] for i in range(4)] for s in E.all_states(4)]


def mechanism(tpm, state):
    """The authors' order with tied purviews taken last first."""
    potential = E.Subsystem.potential_purviews
    try:
        E.Subsystem.potential_purviews = lambda self, d, m: list(reversed(potential(self, d, m)))
        network = E.Network(tpm, labels=LABELS)
        return first_complex(network, state)
    finally:
        E.Subsystem.potential_purviews = potential


def every_state(tpm, log=lambda s: None):
    out = {}
    for state in E.all_states(4):
        rows = all_orders(tpm, state)
        out["".join(map(str, state))] = rows
        log(f"orders: state {''.join(map(str, state))}: {len(distinct([r['big_phi'] for r in rows]))} values")
    return out


def run(seed, results="results", inputs="inputs", states=True, log=print):
    started = time.monotonic()
    tpm, state = read_inputs(inputs)
    rows = all_orders(tpm, state)
    test = verdict(rows)
    values = distinct([r["big_phi"] for r in rows])
    log(f"orders: PQRS in 0101: {len(values)} values of Phi, {min(values):.6f} to {max(values):.6f}")
    authors = next(r for r in rows if r["order"] == LABELS)
    ref = reference_rows()
    pyphi = matches_pyphi(rows, ref)
    controls = []
    controls.append({"control": "PyPhi's recorded output for the 24 orders equals the engine's", "passed": pyphi == 24,
                     "detail": f"{pyphi} of 24"})
    kept = all(keeps_dynamics(tpm, K.permuted(tpm, state, order, LABELS)[0], order)
               for order in itertools.permutations(range(4)))
    controls.append({"control": "relabelling keeps the dynamics in every order", "passed": kept})
    wrong = rows_only_permuted(tpm, (1, 2, 3, 0))
    controls.append({"control": "a relabelling of rows alone is caught", "passed": not keeps_dynamics(tpm, wrong, (1, 2, 3, 0))})
    ring = {tuple(round(x, 9) if isinstance(x, float) else x for x in
                  (r["units"], r["phi_s"], r["big_phi"], r["distinctions"], r["relations"]))
            for r in all_orders(ring_tpm(), RING_STATE, "ABCD")}
    controls.append({"control": "a COPY ring gives one structure in all 24 orders", "passed": len(ring) == 1,
                     "detail": sorted(ring)})
    controls.append({"control": "the authors' order gives the sealed Findlay values",
                     "passed": abs(authors["big_phi"] - AUTHORS[0]) <= SAME and
                     (authors["distinctions"], authors["relations"]) == AUTHORS[1:]})
    mech = mechanism(tpm, state)
    sweep = every_state(tpm, log) if states else {}
    changed = {}
    for key, srows in sweep.items():
        keyset = {(r["units"], round(r["phi_s"], 6), round(r["big_phi"], 6), r["distinctions"]) for r in srows}
        changed[key] = (len(distinct([r["big_phi"] for r in srows])), len(keyset) > 1)
    values_out = {
        "orders": len(rows),
        "complex_units": ", ".join(f"{u} in {sum(1 for r in rows if r['units'] == u)}"
                                   for u in sorted({r['units'] for r in rows})),
        "phi_s": ",".join(f"{v:.6f}" for v in distinct([r["phi_s"] for r in rows])),
        "phi_values": ",".join(f"{v:.4f}" for v in values),
        "distinct_phi": len(values),
        "phi_min": round(min(values), 6),
        "phi_max": round(max(values), 6),
        "orders_13": sum(1 for r in rows if r["distinctions"] == 13),
        "orders_12": sum(1 for r in rows if r["distinctions"] == 12),
        "relations": ",".join(str(v) for v in sorted({r["relations"] for r in rows})),
        "authors_order": f"Phi {authors['big_phi']:.6f}, {authors['distinctions']} distinctions, "
                         f"{authors['relations']} relations",
        "pyphi_match": f"{pyphi} of 24",
        "states_dependent": (f"{sum(1 for v in changed.values() if v[1])} of {len(changed)} states change with the order"
                             if changed else "not run"),
        "state_values": ",".join(f"{k}:{v[0]}" for k, v in changed.items()) if changed else "not run",
        "mechanism": f"tied purviews last first, authors' order: Phi {mech[2]:.6f}, {mech[3]} distinctions",
        "controls_passed": sum(1 for c in controls if c["passed"]),
        "controls_total": len(controls),
        "test_passed": int(test),
    }
    out = {k: values_out[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters")
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    detail = {"values": values_out, "rows": rows, "controls": controls, "mechanism": mech,
              "states": {k: [{x: r[x] for x in ("order", "units", "phi_s", "big_phi", "distinctions", "relations")}
                             for r in v] for k, v in sweep.items()},
              "seconds": round(time.monotonic() - started, 1)}
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as f:
        json.dump(detail, f, indent=1, sort_keys=True, default=str)
        f.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    warnings.simplefilter("ignore", RuntimeWarning)
    try:
        out, _ = run(seed, log=lambda s: print(s, file=sys.stderr, flush=True))
    except Refused as e:
        sys.exit(f"iit4/orders.py: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
