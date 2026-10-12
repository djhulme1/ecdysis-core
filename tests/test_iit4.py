"""IIT 4.0 (iit4/engine.py) held to PyPhi c1a7f4e's own results (iit4/reference/, computed in a sandbox with no
network): PQRS in the authors' order and reversed, and seeded random networks with noise, a MAXENT unit and several
complexes, to the distinction, the purview, the specified state and the number of relations; three broken engines (the
selectivity dropped from the intrinsic difference, the tied purviews taken last first, distinction phi not normalised)
caught by the same comparison; the cut matrices and mechanism partitions in PyPhi's order, the connections each cuts,
and reducibility; the computer (117 units and 231 connections, a target simulated exactly, a flipped program bit
caught, the candidates of rule 7 and the refusal when A2 is ON, graphiit's subgraph, the components); the orders of the
units (relabelling keeps the dynamics, a program ring is the same in every order); the seed; and, with the claim's data
at inputs/ (or IIT4_INPUTS), the reading rules and their refusals and the test's own numbers. With IIT4_SLOW set, every
reference record, PQRS under all 24 orders against PyPhi, and a whole run.

Run with: python3 -m unittest discover -s tests
"""

import functools
import json
import os
import shutil
import sys
import tempfile
import unittest
import warnings
from unittest import mock

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from iit4 import check as K  # noqa: E402
from iit4 import computer as C  # noqa: E402
from iit4 import engine as E  # noqa: E402

warnings.simplefilter("ignore", RuntimeWarning)

REFERENCE = os.path.join(HERE, "..", "iit4", "reference")
INPUTS = os.environ.get("IIT4_INPUTS") or os.path.join(HERE, "..", "inputs")
HAVE = all(os.path.isfile(os.path.join(INPUTS, name)) for name in K.INPUTS)
SLOW = bool(os.environ.get("IIT4_SLOW"))
SEED = "0" * 64
OTHER = "f" * 64
FAST = {("PQRS", (0, 1, 0, 1)), ("SRQP", (1, 0, 1, 0)), ("PQRS", (0, 0, 0, 0)), ("SRQP", (0, 0, 0, 0))}


def _load(name):
    with open(os.path.join(REFERENCE, name), encoding="utf-8") as f:
        return json.load(f)


REF = _load("pyphi-c1a7f4e.json")
PARTS = _load("pyphi-c1a7f4e-parts.json")
JOBS = {job["name"]: job for job in REF["jobs"]}


def records(fast):
    for job in REF["jobs"]:
        for rec in job["pyphi"]:
            if not fast or (job["name"], tuple(rec["state"])) in FAST or job["name"].startswith("R"):
                yield job, rec


def engine_complexes(job, state):
    network = E.Network(job["tpm"], job["cm"], job["labels"])
    out = []
    for phi, nodes, states in E.condensed(network, state):
        structure = E.Subsystem(network, state, nodes).phi_structure(states)
        out.append({"nodes": list(nodes), "phi_s": phi, "big_phi": structure.big_phi,
                    "relations": len(structure.relations),
                    "cause_state": list(states[E.CAUSE].state), "effect_state": list(states[E.EFFECT].state),
                    "distinctions": sorted((list(d.mechanism), d.phi, list(d.cause.purview), list(d.cause.state),
                                            d.cause.phi, list(d.effect.purview), list(d.effect.state), d.effect.phi)
                                           for d in structure.distinctions)})
    return out


@functools.lru_cache(maxsize=None)
def cached(name, state):
    return engine_complexes(JOBS[name], state)


def disagreements(mine, theirs):
    out = []
    if len(mine) != len(theirs):
        return [f"{len(mine)} complexes, PyPhi {len(theirs)}"]
    for a, b in zip(mine, theirs):
        if a["nodes"] != b["nodes"]:
            out.append(f"complex {a['nodes']}, PyPhi {b['nodes']}")
            continue
        if abs(a["phi_s"] - b["phi_s"]) > 1e-9:
            out.append(f"phi_s {a['phi_s']}, PyPhi {b['phi_s']}")
        if abs(a["big_phi"] - b["big_phi"]) > 1e-6:
            out.append(f"Phi {a['big_phi']}, PyPhi {b['big_phi']}")
        if a["relations"] != b["relations"]:
            out.append(f"{a['relations']} relations, PyPhi {b['relations']}")
        if (a["cause_state"], a["effect_state"]) != (b["cause_state"], b["effect_state"]):
            out.append("the system's specified states")
        theirs_d = sorted((d["mechanism"], d["phi"], d["cause"][0], d["cause"][1], d["cause"][2], d["effect"][0],
                           d["effect"][1], d["effect"][2]) for d in b["distinctions"])
        if [d[0] for d in a["distinctions"]] != [d[0] for d in theirs_d]:
            out.append("the distinctions' mechanisms")
            continue
        for x, y in zip(a["distinctions"], theirs_d):
            if (x[2], x[3], x[5], x[6]) != (y[2], y[3], y[5], y[6]) or any(
                    abs(x[i] - y[i]) > 1e-9 for i in (1, 4, 7)):
                out.append(f"distinction {x[0]}: {x[1:]}, PyPhi {y[1:]}")
    return out


class AgainstPyPhi(unittest.TestCase):
    def test_reference_is_pyphis_at_the_pinned_commit(self):
        self.assertEqual(REF["pyphi"], "c1a7f4e151f2bf9e6bc988f0af221ed37cd56765")
        self.assertEqual(REF["pyphi_config_sha256"], K.INPUTS["pyphi_config.yml"])
        self.assertEqual(sum(len(j["pyphi"]) for j in REF["jobs"]), 70)

    def test_fast_records_match(self):
        for job, rec in records(fast=True):
            with self.subTest(job=job["name"], state=rec["state"]):
                self.assertEqual(disagreements(cached(job["name"], tuple(rec["state"])), rec.get("complexes", [])), [])

    def test_order_dependence_is_pyphis(self):
        """The same system, relabelled: PyPhi itself gives another Phi-structure, and so does the engine."""
        authors = next(r for r in JOBS["PQRS"]["pyphi"] if r["state"] == [0, 1, 0, 1])["complexes"][0]
        reversed_ = next(r for r in JOBS["SRQP"]["pyphi"] if r["state"] == [1, 0, 1, 0])["complexes"][0]
        self.assertEqual((len(authors["distinctions"]), authors["relations"]), (13, 8184))
        self.assertEqual((len(reversed_["distinctions"]), reversed_["relations"]), (12, 4088))
        self.assertAlmostEqual(authors["big_phi"], 391.247221908, places=6)
        self.assertAlmostEqual(reversed_["big_phi"], 209.844265, places=5)
        self.assertAlmostEqual(authors["phi_s"], reversed_["phi_s"], places=12)
        mine = cached("PQRS", (0, 1, 0, 1))[0], cached("SRQP", (1, 0, 1, 0))[0]
        self.assertEqual([len(m["distinctions"]) for m in mine], [13, 12])
        self.assertAlmostEqual(mine[1]["big_phi"], reversed_["big_phi"], places=9)

    def test_broken_engines_are_caught(self):
        job = JOBS["PQRS"]
        rec = next(r for r in job["pyphi"] if r["state"] == [0, 1, 0, 1])
        gid = E.gid
        potential = E.Subsystem.potential_purviews
        broken = {
            "the selectivity dropped": mock.patch.object(
                E, "gid", lambda f, p, s: gid(f, p, np.ones_like(np.asarray(s, dtype=float)))),
            "tied purviews taken last first": mock.patch.object(
                E.Subsystem, "potential_purviews", lambda self, d, m: list(reversed(potential(self, d, m)))),
            "distinction phi not normalised": mock.patch.object(E, "num_connections_cut", lambda partition: 1),
        }
        for name, patch in broken.items():
            with self.subTest(name), patch:
                self.assertNotEqual(disagreements(engine_complexes(job, (0, 1, 0, 1)), rec["complexes"]), [])

    @unittest.skipUnless(SLOW, "IIT4_SLOW not set")
    def test_every_record(self):
        for job, rec in records(fast=False):
            with self.subTest(job=job["name"], state=rec["state"]):
                self.assertEqual(disagreements(cached(job["name"], tuple(rec["state"])), rec.get("complexes", [])), [])


class Parts(unittest.TestCase):
    def test_cut_matrices_in_pyphis_order(self):
        for k, matrices in PARTS["cut_matrices"].items():
            with self.subTest(units=k):
                self.assertEqual([m.tolist() for m in E.system_cut_matrices(int(k))], matrices)
        self.assertEqual(len(E.system_cut_matrices(5)), PARTS["cut_count_5"])

    def test_partitions_in_pyphis_order(self):
        for key, rows in PARTS["partitions"].items():
            m, p = map(int, key.split(","))
            mine = [[[list(a), list(b)] for a, b in part] + [E.num_connections_cut(part)]
                    for part in E.all_partitions(tuple(range(m)), tuple(range(10, 10 + p)))]
            with self.subTest(mechanism=m, purview=p):
                self.assertEqual(mine, rows)

    def test_k_partitions_are_partitions(self):
        stirling = {(n, k): 0 for n in range(8) for k in range(8)}
        stirling[(0, 0)] = 1
        for n in range(1, 8):
            for k in range(1, n + 1):
                stirling[(n, k)] = k * stirling[(n - 1, k)] + stirling[(n - 1, k - 1)]
                parts = [sorted(map(sorted, p)) for p in E.k_partitions(range(n), k)]
                self.assertEqual(len(parts), stirling[(n, k)])
                self.assertEqual(len({str(p) for p in parts}), len(parts))
                for p in parts:
                    self.assertEqual(sorted(x for block in p for x in block), list(range(n)))
                    self.assertTrue(all(p))
        self.assertEqual(list(E.k_partitions(range(3), 2)), [[[0, 1], [2]], [[0], [1, 2]], [[0, 2], [1]]])

    def test_block_reducible(self):
        for case in PARTS["block_reducible"]:
            got = E.block_reducible(np.array(case["cm"]), tuple(case["a"]), tuple(case["b"]))
            self.assertEqual(bool(got), case["reducible"], case)

    def test_gid_and_states(self):
        self.assertAlmostEqual(float(E.gid(0.5, 0.25, 0.8)), 0.8)
        self.assertEqual(float(E.gid(0.0, 0.0, 0.3)), 0.0)
        self.assertEqual(list(E.all_states(2)), [(0, 0), (1, 0), (0, 1), (1, 1)])


def counter_tpm():
    """A target of our own: the next state is the state plus one, modulo 16, little-endian."""
    return [[((row + 1) % 16 >> k) & 1 for k in range(4)] for row in range(16)]


class Computer(unittest.TestCase):
    def test_size(self):
        graph = C.computer(2, counter_tpm(), (1, 0, 1, 0))
        self.assertEqual((len(graph.units), graph.edges()), (117, 231))

    def test_simulates_a_target_exactly(self):
        self.assertEqual(C.simulate(2, counter_tpm(), (1, 0, 1, 0), 20), (20, None))
        self.assertTrue(C.check_every_cycle(2, counter_tpm()))

    def test_flipped_program_bit_is_caught(self):
        tpm = counter_tpm()
        row = sum(v << i for i, v in enumerate((1, 0, 1, 0)))
        broken = [r[:] for r in tpm]
        broken[row][1] = 1 - broken[row][1]
        graph = C.computer(2, broken, (1, 0, 1, 0))
        graph.tic(1 + 8)
        expected = tuple(tpm[row])
        self.assertNotEqual(tuple(graph.state[r[0]] for r in C.labels(2)["registers"]), expected)

    def test_candidates(self):
        graph = C.computer(2, counter_tpm(), (1, 0, 1, 0))
        found = K.candidates(graph)
        rings = [tuple(line) for line in C.labels(2)["program"]]
        self.assertEqual(len(found), 25)
        self.assertEqual(sorted(c for c in found if len(c) == 4), sorted(rings))
        self.assertEqual(sorted(c[0] for c in found if len(c) == 1),
                         sorted(["C0", "X1", "A1", "X2", "A2", "T0R0", "T1R0", "T2R0", "T3R0"]))

    def test_refuses_with_a2_on(self):
        graph = C.computer(2, counter_tpm(), (1, 0, 1, 0))
        graph.state["A2"] = 1
        with self.assertRaises(K.Refused):
            K.candidates(graph)

    def test_subgraph_and_components(self):
        graph = C.Graph([("A", "COPY", "B"), ("B", "COPY", "A"), ("C", "COPY", "A"), ("D", "COPY", "D")],
                        {"A": 1, "B": 0, "C": 0, "D": 1})
        self.assertEqual(C.strongly_connected_components(graph), [["A", "B"], ["C"], ["D"]])
        self.assertEqual([C.cyclic(graph, c) for c in C.strongly_connected_components(graph)], [True, False, True])
        alone = graph.subgraph(["C"])
        self.assertEqual(alone.config, [("C", "MAXENT", "C")])
        self.assertTrue(np.all(alone.network().tpm == 0.5))

    def test_a_ring_is_the_same_in_every_order(self):
        graph = C.computer(2, counter_tpm(), (1, 0, 1, 0))
        ring = list(C.labels(2)["program"][5])
        values = {(round(o["phi_s"], 9), round(o["big_phi"], 9), o["distinctions"], o["relations"])
                  for o in K.complex_orders(graph, {"units": tuple(ring), "vokram": False})}
        self.assertEqual(len(values), 1)


class Orders(unittest.TestCase):
    def test_relabelling_keeps_the_dynamics(self):
        rng = np.random.default_rng(3)
        tpm = [list(map(int, rng.integers(0, 2, 4))) for _ in range(16)]
        for order in ((3, 2, 1, 0), (1, 3, 0, 2)):
            network, state = K.permuted(tpm, (0, 1, 1, 0), order, "PQRS")
            self.assertEqual(network.labels, tuple("PQRS"[j] for j in order))
            self.assertEqual(state, tuple((0, 1, 1, 0)[j] for j in order))
            for s in E.all_states(4):
                new = tuple(s[order[j]] for j in range(4))
                after = network.tpm[new]
                self.assertEqual(tuple(int(after[j]) for j in range(4)),
                                 tuple(tpm[sum(v << i for i, v in enumerate(s))][order[j]] for j in range(4)))

    def test_reordered_graph_keeps_each_units_inputs(self):
        graph = C.computer(2, counter_tpm(), (1, 0, 1, 0))
        ring = C.labels(2)["program"][0]
        moved = K.reordered(graph, ring, list(reversed(ring)))
        self.assertEqual([u for u in moved.units if u in ring], list(reversed(ring)))
        self.assertEqual(moved.inputs, graph.inputs)
        self.assertEqual(moved.step(), graph.step())

    @unittest.skipUnless(SLOW and HAVE, "IIT4_SLOW not set, or no inputs")
    def test_pqrs_under_every_order_as_pyphi(self):
        tpm, state = K.read_inputs(INPUTS)["pqrs"]
        for o in K.pqrs_orders(tpm, state):
            name = "PQRS" if o["order"] == tuple("PQRS") else (
                "SRQP" if o["order"] == tuple("SRQP") else "perm-" + "".join(o["order"]))
            rec = next(r for r in JOBS[name]["pyphi"] if tuple(r["state"]) == tuple(
                state["PQRS".index(u)] for u in o["order"]))["complexes"][0]
            with self.subTest(order=name):
                self.assertAlmostEqual(o["big_phi"], rec["big_phi"], places=6)
                self.assertEqual((o["distinctions"], o["relations"]), (len(rec["distinctions"]), rec["relations"]))


class Seed(unittest.TestCase):
    def test_programs_follow_the_seed(self):
        a, b = K.draw_program(SEED, 0), K.draw_program(SEED, 0)
        self.assertEqual(a, b)
        self.assertNotEqual(K.draw_program(SEED, 0), K.draw_program(SEED, 1))
        self.assertNotEqual(K.draw_program(SEED, 0), K.draw_program(OTHER, 0))
        tpm, initial = a
        self.assertEqual((len(tpm), len(initial)), (16, 4))
        self.assertTrue(all(len(row) == 4 and set(row) <= {0, 1} for row in tpm))


@unittest.skipUnless(HAVE, "the claim's data are not at inputs/ (or IIT4_INPUTS)")
class Reading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = K.read_inputs(INPUTS)

    def raw(self, name):
        with open(os.path.join(INPUTS, name), "rb") as f:
            return f.read()

    def test_reads_the_data_of_record(self):
        self.assertEqual(tuple(self.data["pqrs"][1]), (0, 1, 0, 1))
        self.assertEqual(tuple(self.data["wxyz"][1]), (1, 1, 0, 1))
        self.assertEqual(len(self.data["figure8"]), 16)
        for figure in ("figure3", "figure5"):
            (phis, bigs), units, _ = self.data[figure]
            self.assertEqual((len(phis), len(bigs), len(units)), (16, 16, 9))

    def test_refuses_other_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in K.INPUTS:
                shutil.copy(os.path.join(INPUTS, name), tmp)
            with open(os.path.join(tmp, "findlay2024a.py"), "ab") as f:
                f.write(b"\n")
            with self.assertRaises(K.Refused):
                K.read_inputs(tmp)

    def test_refuses_another_configuration(self):
        text = self.raw("pyphi_config.yml").decode("utf-8")
        K.check_config(text)
        for old, new in (("PARTITION_TYPE: ALL", "PARTITION_TYPE: TRI"),
                         ("- NORMALIZED_PHI\n- NEGATIVE_PHI", "- NEGATIVE_PHI\n- NORMALIZED_PHI"),
                         ("IIT_VERSION: 4.0", "IIT_VERSION: 3.0")):
            with self.subTest(old), self.assertRaises(K.Refused):
                K.check_config(text.replace(old, new))

    def test_refuses_other_pins_prints_and_ports(self):
        lock = self.raw("uv.lock").decode("utf-8")
        with self.assertRaises(K.Refused):
            K.check_lock(lock.replace("c1a7f4e151f2bf9e6bc988f0af221ed37cd56765", "0" * 40))
        tex = K.main_tex(self.raw("arXiv-2412.04571v2.tar.gz"))
        with self.assertRaises(K.Refused):
            K.check_printed(tex.replace("8184 relations", "8183 relations"))
        source = self.raw("divided_clock_computer.py").decode("utf-8")
        with self.assertRaises(K.Refused):
            K.check_ported(source.replace("def get_mux_config(", "def get_mux("))
        with self.assertRaises(K.Refused):
            K.tpm_literals("x = 1\n", ("get_pqrs_micro_example",))
        short = {"cells": [{"cell_type": "code", "source": ["summarize_all_states(network)"],
                            "outputs": [{"output_type": "stream", "name": "stdout", "text": ["nothing\n"]}]}]}
        with self.assertRaises(K.Refused):
            K.figure8_table(short)

    def test_the_test_in_the_authors_order(self):
        tpm, state = self.data["pqrs"]
        network = E.Network(tpm, labels="PQRS")
        phi, nodes, states = E.condensed(network, state)[0]
        structure = E.Subsystem(network, state, nodes).phi_structure(states)
        self.assertEqual((len(nodes), len(structure.distinctions), len(structure.relations)), (4, 13, 8184))
        self.assertEqual(f"{structure.big_phi:.2f}", "391.25")
        self.assertEqual(K.condensed_rows(network, state), tuple(self.data["figure8"][(0, 1, 0, 1)]))
        for name in ("pqrs", "wxyz"):
            self.assertEqual(C.simulate(2, *self.data[name], 20), (20, None))
        _, results, complexes = K.computer_complexes(self.data["pqrs"], self.data["figure3"])
        self.assertEqual((len(results), len(complexes)), (25, 24))
        self.assertEqual(K.summary(complexes)[0], 4)
        self.assertLessEqual(K.summary(complexes)[1], K.BOUND + K.SLACK)
        self.assertLessEqual(K.summary(complexes)[2], 4)


@unittest.skipUnless(SLOW and HAVE, "IIT4_SLOW not set, or no inputs")
class WholeRun(unittest.TestCase):
    def test_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, detail = K.run(SEED, results=tmp, inputs=INPUTS, programs=2, log=lambda s: None)
        self.assertEqual(tuple(out), K.OUTPUTS)
        self.assertLessEqual(len(out), 20)
        self.assertEqual(out["test_passed"], 1)
        self.assertEqual((out["controls_passed"], out["controls_total"]), (10, 10))
        self.assertEqual(out["pqrs_distinctions"], 13)
        self.assertIn("dissociation in 24", out["pqrs_orders"])
        self.assertTrue(out["computer_orders"].endswith("differs from the authors' order in 0"))


if __name__ == "__main__":
    unittest.main()
