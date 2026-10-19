#!/usr/bin/env python3
"""IIT 3.0's results on its own example systems: an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:1bd4198cec1c039d) is from Oizumi,
Albantakis and Tononi, "From the phenomenology to the mechanisms of consciousness: Integrated Information Theory 3.0",
PLoS Computational Biology 10(5), e1003588 (2014; CC BY), the abstract's list of the results that follow from the
theory: "a system of mechanisms may condense into a major complex and non-overlapping minor complexes; the concepts
that specify the quality of an experience are always about the complex itself and relate only indirectly to the
external environment; anatomical connectivity influences complexes and associated MICS; a complex can generate a MICS
even if its elements are inactive; simple systems can be minimally conscious; complicated systems can be unconscious;
there can be true "zombies"--unconscious feed-forward systems that are functionally equivalent to conscious
complexes."

Its registered test: TEST (below).

No data of record: a construction. The systems are the paper's own, read from its figures (PLOS's figure files and
the full text, read before these rules were written; nothing was computed on them); PyPhi 1.2.0's encoding of
Figure 16 (pyphi/examples.py, fig16) was decoded before the rules as a check of the reading and agrees with it for A
to G. Everything is computed by Imago's own IIT 3.0, iit/engine.py (written for iit/check.py, which reproduced
Hanson & Walker's printed spectra; standard library, the transport problems in iit/flow.c, built here with gcc), as
PyPhi 1.2.0 computes it. Every rule below was fixed before any Phi of the paper's systems was computed; the seed draws
the feed-forward systems of rule 6 and the states of rule 7 only.

1. Phi of a candidate set, as PyPhi 1.2.0's sia computes it with its default configuration: elements outside the set
   are background conditions in their current state; potential purviews are filtered by PyPhi's connectivity test
   on the network's own connectivity (rule 3's wiring: PyPhi with a connectivity matrix given; under the all-ones
   default iit/check.py used, every purview so filtered has phi = 0, so no value changes); Phi = 0 for a set whose
   elements are not strongly connected in
   the network's connectivity, for a single element (with or without a self-loop:
   SINGLE_MICRO_NODES_WITH_SELFLOOPS_HAVE_PHI is false by default), and for a set with no concept; otherwise the
   least, over PyPhi's unidirectional cuts in its order, of the distance between the cause-effect structure and the
   cut one (engine.py: concepts, mechanisms that are concepts or that the cut splits, the MICE that a cut leaves
   undamaged kept, PyPhi's distance between structures), rounded to 6 decimals. The verdict uses PyPhi's arithmetic
   (pyemd 0.5.1's integer rounding, engine mode 1), as iit/check.py's did; the same run in exact arithmetic (mode 0)
   is reported beside it.
2. Candidate sets, complexes and condensation, as PyPhi 1.2.0's possible_complexes, complexes and condensed: every
   nonempty set of the network's causally significant elements (an input and an output in its connectivity), skipped
   if its current state cannot be reached from any state of its own elements with the rest held in their current
   state (PyPhi's state_reachable); a complex is a candidate set with Phi > 0; the condensation takes the complexes in
   decreasing order of (Phi, size, element indices) and keeps each that shares no element with one kept. The first
   kept is the major complex, the others minor complexes. A concept is a mechanism of the set whose core cause and
   effect (PyPhi's pick among ties) both have phi > 0.
3. The systems, read from the figures (yellow 1, white 0; an arrow +1, a red dot -1; elements listed A first):
   - Figure 16: A = OR(B, C), B = AND(A, C, D), C = XOR(A, B), D = OR(D, E, H), E = OR(A, D, E), F = OR(F, G),
     G = AND(F, G), H = COPY(I), K = COPY(A), J = COPY(K); I and L have no inputs (constant in their current state,
     the paper giving them no mechanism; H, J and K's mechanisms are not given either, and COPY is taken). State:
     A..L = 1 0 0 1 1 1 0 0 0 1 1 1.
   - Figure 17A, modular: A = COPY(B), C = COPY(D), E = COPY(F); B, D and F each the AND of A, C and E. All on.
   - Figure 17B, homogeneous: five ORs, each of all five (self-loops included). All on.
   - Figure 17C, specialized: five majority gates of three inputs: A of C, D, E; B of A, D, E; C of A, B, E; D of A,
     B, C; E of B, C, D (the arrows, and the purviews its concept list prints). All on.
   - Figure 18: four COPY gates in a cycle, A = COPY(D), B = COPY(A), C = COPY(B), D = COPY(C). All off.
   - Figure 19, the minimally conscious photodiode: D on if X1 + X2 + P >= 2, P = COPY(D); the external inputs X1 =
     0 and X2 = 1 are elements with no inputs, constant in that state. D = P = 1.
   - Figure 20A, the unconscious photodiode: D = COPY(X), O = COPY(D), the external input X = 1 constant. D = O = 1.
4. The photodiode's unfolding over STEPS = 4 steps (rule 3's photodiode, the paper's method: "the state of each
   element is passed on through a chain of x nodes, one node for each of the x time steps"): constant elements S_D
   and S_P hold its initial state, X1_t and X2_t (t = 0..3) the external inputs of each step, and D_t and P_t (t =
   1..4) compute D_t = (X1_{t-1} + X2_{t-1} + P_{t-1} >= 2), P_t = COPY(D_{t-1}), with D_0 = S_D and P_0 = S_P; its
   outputs are P_1..P_4, the photodiode's output element at steps 1 to 4. Its state: S_D = S_P = 1 and every input
   (0, 1), as Figure 19 shows them, each later element at the value it computes. Functionally equivalent means: for
   each of the photodiode's 4 initial states and each of the 4^4 sequences of its two binary inputs over four steps,
   the unfolding's outputs equal the photodiode's output at steps 1 to 4, run from that state.
5. The test's conditions (conditions_met counts them; test_passed is 1 if all hold and the controls pass):
   (a) Figure 16 condenses into ABC, then DE and FG, ABC first;
   (b) Figure 17A condenses into AB, CD and EF;
   (c) Figure 17B condenses into ABCDE alone, whose concepts are its 5 first-order ones only;
   (d) Figure 17C condenses into ABCDE alone, with more concepts than 17B's and a greater Phi;
   (e) Figure 18, all off, condenses into ABCD;
   (f) Figure 19 condenses into DP;
   (g) Figure 20A has no complex;
   (h) none of the FF_DRAWS seed-drawn feed-forward systems of rule 6 has a complex;
   (i) the unfolding of rule 4 has no complex and is functionally equivalent to the photodiode, which (f) shows to be
       a complex.
6. The seed-drawn feed-forward systems (Figure 20B's "regardless of the elements' (logic) functions"): two input
   elements with no inputs, constant at seed-drawn values, and three layers of two or three elements; each element of
   layer l reads one to three elements of lower layers, one at least from layer l - 1, through a gate drawn from AND,
   OR, XOR, NAND, NOR (two or three inputs), MAJ (three), COPY or NOT (one); the state is the one the network
   settles into, its inputs constant, from a seed-drawn state of its layers. No element reads itself or a higher
   layer.
7. Full computations, beside rule 1's shortcuts: every candidate set of up to FULL_MAX = 3 elements (every element,
   not only causally significant ones; single elements cut at their self-loop) of every system of rules 3, 4 and 6
   has its Phi computed through every cut, with no connectivity or single-element shortcut and no purview filter
   (the all-ones connectivity iit/check.py used). Each set that rule 1
   gives Phi = 0 because it is not strongly connected must have Phi = 0 so computed (a control); single elements so
   computed are reported beside (rule 1 gives them 0 by PyPhi's default).
8. Beside the test, none of it counted: the paper's printed values set against the computed ones, each cut and
   rounded to the printed digits (Figure 16: Phi of ABC 1.92, of ABCDE 0.021, of DE and FG 0.028; 17A: a module's
   1.00, the whole's 0.53, two concepts of phi 0.5 each; 17B: 0.003, five concepts of phi 0.0161; 17C: 10.75, 30
   concepts, its first-order concepts' phi 0.25 and AB's and AC's 0.2; 18: 1, four concepts of phi 0.5, A's cause on
   D and effect on B; 19: 1, two concepts of phi 0.5), whether ABCDE in Figure 16 has Phi > 0 (the caption's "strongly
   integrated"), the photodiode's structure in its four states (the text: the same MICS in each), the exact-arithmetic
   run, and Figure 21A as read: A >= 2 of I1, D, I and -J; B >= 2 of I2, D, H and -J; D >= 2 of A, B and -J; H >= 1 of
   J, B, -D and -A; I >= 1 of J, A, -D and -B; J = XOR(I, H); O1 = (D >= 1), O2 = (J >= 1); each input (0, 1 or 2)
   two binary input elements; state A B D H I J = 0 1 0 1 0 1 with I1 = 0 and I2 = 2 (its input elements' colours):
   its condensation, Phi, concepts (printed: 17, and Phi 0.76 in the caption, 0.79 in the figure), its unfolding over
   four steps (complexes and functional equivalence over its 64 initial states and 9^4 input sequences), and how many
   initial states reproduce the input-output run the figure prints (inputs I1 = 2 2 1 0 0 2 2 1, I2 = 0 0 0 0 0 2 2 1
   from t0; outputs O1 = 1 1 1 0 0 0 0, O2 = 0 0 0 0 1 1 1 at t4 to t10; any inputs after t7; outputs read one to
   three steps after the elements). Figure 21A is beside, not tested: as read, the printed run is not checked before
   the rules, and its wiring is drawn, not printed.

Controls (controls_passed counts those that behave as stated): the transport solver gives 1 for one unit moved one
step, and the pyemd arithmetic 0.166666 against exact 1/6 (uniform against (1/3, 1/6, 1/6, 1/3)); rule 7's full
computations agree with the connectivity shortcut; every depicted state of rule 3 is reachable (PyPhi would refuse
it otherwise); two planted faults the method must catch: Figure 18's cycle with A made constant (no input from D) has
no complex, and in at least one seed-drawn feed-forward system a planted feedback (its last element read by a
first-layer element it rests on, whose gate takes it as an extra input through XOR; the state settled again, at most
64 updates) creates a complex; and the unfolding's
functional equivalence fails when its first step's photodiode reads P_0 through NOT (a planted error the comparison
must catch).

What it does not test: the second result (concepts about the complex itself) holds by IIT 3.0's definitions, a
purview being a set of the complex's own elements, so no computation could refute it; Figure 22's ten-element
segment/dot system; Figure 20B's and 21B's drawn networks (rules 4 and 6 build feed-forward systems as the text
describes instead); and the paper's own computations, made with code that is not released.

Writes results/outputs.json and results/detail.json. Run with: python3 iit/oat2014.py (ECDYSIS_SEED set).
"""

import hashlib
import itertools
import json
import os
import random
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import engine as E  # noqa: E402

CLAIM = "ext:1bd4198cec1c039d"
TEST = ("Refuted if, in IIT 3.0 as PyPhi 1.2 computes it, the paper's systems condense otherwise: Fig. 16 into the "
        "major complex ABC and minor complexes DE and FG; Fig. 17A into AB, CD and EF; 17B and 17C each into one, "
        "17B's with only its 5 first-order concepts, 17C's with more and higher \u03a6Max; Fig. 18's COPY cycle, all "
        "off, and Fig. 19's photodiode each into one; or if a strictly feed-forward system (Fig. 20A, seed-drawn "
        "ones, and Fig. 19's photodiode unfolded over 4 steps, its outputs the same) has a complex.")
VERDICT_MODE = 1
STEPS = 4
FF_DRAWS = 8
FULL_MAX = 3


class Refused(Exception):
    pass


# ---------------------------------------------------------------- networks of elements

class LazyRow:
    __slots__ = ("fns", "bits")

    def __init__(self, fns, s):
        self.fns = fns
        self.bits = tuple((s >> i) & 1 for i in range(len(fns)))

    def __len__(self):
        return len(self.fns)

    def __getitem__(self, j):
        return self.fns[j](self.bits)


class LazyTPM:
    """tpm_on[s][j] for engine.Network, computed from each element's function of the whole state."""

    def __init__(self, fns):
        self.fns = fns

    def __len__(self):
        return 2 ** len(self.fns)

    def __getitem__(self, s):
        return LazyRow(self.fns, s)


def g_or(ins):
    return lambda s, ins=tuple(ins): int(any(s[i] for i in ins))


def g_and(ins):
    return lambda s, ins=tuple(ins): int(all(s[i] for i in ins))


def g_xor(ins):
    return lambda s, ins=tuple(ins): sum(s[i] for i in ins) % 2


def g_nand(ins):
    return lambda s, ins=tuple(ins): 1 - int(all(s[i] for i in ins))


def g_nor(ins):
    return lambda s, ins=tuple(ins): 1 - int(any(s[i] for i in ins))


def g_maj(ins):
    return lambda s, ins=tuple(ins): int(2 * sum(s[i] for i in ins) > len(ins))


def g_copy(i):
    return lambda s, i=i: s[i]


def g_not(i):
    return lambda s, i=i: 1 - s[i]


def g_const(v):
    return lambda s, v=v: v


def g_threshold(weights, theta):
    """on if sum(w * s[i]) >= theta; weights: [(index, weight)]."""
    return lambda s, w=tuple(weights), t=theta: int(sum(c * s[i] for i, c in w) >= t)


GATES = {"OR": g_or, "AND": g_and, "XOR": g_xor, "NAND": g_nand, "NOR": g_nor, "MAJ": g_maj}


class System:
    def __init__(self, name, labels, inputs, fns, state, sources=()):
        self.name, self.labels = name, list(labels)
        self.inputs = [tuple(x) for x in inputs]
        self.fns = list(fns)
        self.state = tuple(state)
        self.sources = tuple(sources)
        n = len(self.labels)
        assert len(self.inputs) == n and len(self.fns) == n and len(self.state) == n
        self.n = n
        self.cm = [[0] * n for _ in range(n)]
        for j, ins in enumerate(self.inputs):
            for i in ins:
                self.cm[i][j] = 1
        self.net = E.Network(LazyTPM(self.fns))

    def step(self, bits):
        return tuple(f(bits) for f in self.fns)

    def name_of(self, nodes):
        return "".join(self.labels[i] for i in nodes) if all(len(self.labels[i]) == 1 for i in nodes) \
            else " ".join(self.labels[i] for i in nodes)

    def index(self, label):
        return self.labels.index(label)


def build_system(name, spec, state):
    """spec: [(label, inputs as labels, kind, extra)], kind one of GATES, COPY, NOT, CONST, THRESH."""
    labels = [s[0] for s in spec]
    idx = {lab: i for i, lab in enumerate(labels)}
    inputs, fns, sources = [], [], []
    for lab, ins, kind, extra in spec:
        ii = [idx[x] for x in (ins or ())]
        if kind in GATES:
            f = GATES[kind](ii)
        elif kind == "COPY":
            f = g_copy(ii[0])
        elif kind == "NOT":
            f = g_not(ii[0])
        elif kind == "CONST":
            f = g_const(extra)
            sources.append(idx[lab])
        elif kind == "THRESH":
            weights, theta = extra
            f = g_threshold([(idx[x], w) for x, w in weights], theta)
            ii = [idx[x] for x, _ in weights]
        else:
            raise ValueError(kind)
        inputs.append(tuple(ii))
        fns.append(f)
    return System(name, labels, inputs, fns, [state[lab] for lab in labels], sources)


def st(labels, bits):
    return dict(zip(labels, bits))


# ---------------------------------------------------------------- the paper's systems (rule 3)

def fig16():
    spec = [("A", "BC", "OR", None), ("B", "ACD", "AND", None), ("C", "AB", "XOR", None),
            ("D", "DEH", "OR", None), ("E", "ADE", "OR", None), ("F", "FG", "OR", None), ("G", "FG", "AND", None),
            ("H", "I", "COPY", None), ("I", "", "CONST", 0), ("J", "K", "COPY", None), ("K", "A", "COPY", None),
            ("L", "", "CONST", 1)]
    return build_system("Figure 16", spec, st("ABCDEFGHIJKL", (1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1)))


def fig17a():
    spec = [("A", "B", "COPY", None), ("B", "ACE", "AND", None), ("C", "D", "COPY", None),
            ("D", "ACE", "AND", None), ("E", "F", "COPY", None), ("F", "ACE", "AND", None)]
    return build_system("Figure 17A", spec, st("ABCDEF", (1,) * 6))


def fig17b():
    spec = [(x, "ABCDE", "OR", None) for x in "ABCDE"]
    return build_system("Figure 17B", spec, st("ABCDE", (1,) * 5))


def fig17c():
    spec = [("A", "CDE", "MAJ", None), ("B", "ADE", "MAJ", None), ("C", "ABE", "MAJ", None),
            ("D", "ABC", "MAJ", None), ("E", "BCD", "MAJ", None)]
    return build_system("Figure 17C", spec, st("ABCDE", (1,) * 5))


def fig18(planted=False):
    spec = [("A", "", "CONST", 0) if planted else ("A", "D", "COPY", None), ("B", "A", "COPY", None),
            ("C", "B", "COPY", None), ("D", "C", "COPY", None)]
    return build_system("Figure 18" + (" (A constant)" if planted else ""), spec, st("ABCD", (0, 0, 0, 0)))


def fig19(state=(1, 1)):
    spec = [("D", None, "THRESH", ([("X1", 1), ("X2", 1), ("P", 1)], 2)), ("P", "D", "COPY", None),
            ("X1", "", "CONST", 0), ("X2", "", "CONST", 1)]
    return build_system("Figure 19", spec, {"D": state[0], "P": state[1], "X1": 0, "X2": 1})


def fig20a():
    spec = [("D", "X", "COPY", None), ("O", "D", "COPY", None), ("X", "", "CONST", 1)]
    return build_system("Figure 20A", spec, {"D": 1, "O": 1, "X": 1})


# the photodiode as a recurrent system with inputs, for unfolding: elements (D, P), inputs (x1, x2)
def photodiode_step(x, u):
    d, p = x
    return (int(u[0] + u[1] + p >= 2), d)


def photodiode_out(x):
    return x[1]


# Figure 21A as read (rule 8): elements A B D H I J, inputs (I1, I2) in 0..2
def fig21_step(x, u):
    a, b, d, h, i, j = x
    return (int(u[0] + d + i - j >= 2), int(u[1] + d + h - j >= 2), int(a + b - j >= 2),
            int(j + b - d - a >= 1), int(j + a - d - b >= 1), (i + h) % 2)


def fig21_out(x):
    return (x[2], x[5])


def fig21a(state=(0, 1, 0, 1, 0, 1), inputs=(0, 2)):
    i1, i2 = inputs
    spec = [("A", None, "THRESH", ([("I1a", 1), ("I1b", 1), ("D", 1), ("I", 1), ("J", -1)], 2)),
            ("B", None, "THRESH", ([("I2a", 1), ("I2b", 1), ("D", 1), ("H", 1), ("J", -1)], 2)),
            ("D", None, "THRESH", ([("A", 1), ("B", 1), ("J", -1)], 2)),
            ("H", None, "THRESH", ([("J", 1), ("B", 1), ("D", -1), ("A", -1)], 1)),
            ("I", None, "THRESH", ([("J", 1), ("A", 1), ("D", -1), ("B", -1)], 1)),
            ("J", "IH", "XOR", None),
            ("O1", "D", "COPY", None), ("O2", "J", "COPY", None),
            ("I1a", "", "CONST", int(i1 >= 1)), ("I1b", "", "CONST", int(i1 >= 2)),
            ("I2a", "", "CONST", int(i2 >= 1)), ("I2b", "", "CONST", int(i2 >= 2))]
    a, b, d, h, i, j = state
    s = {"A": a, "B": b, "D": d, "H": h, "I": i, "J": j, "O1": d, "O2": j,
         "I1a": int(i1 >= 1), "I1b": int(i1 >= 2), "I2a": int(i2 >= 1), "I2b": int(i2 >= 2)}
    return build_system("Figure 21A (as read)", spec, s)


# ---------------------------------------------------------------- unfolding (rule 4)

def unfold(name, m, n_in, step_fns, out_index, init, inputs, steps=STEPS):
    """A feed-forward unfolding of a recurrent system over `steps` steps.

    m elements; n_in binary input lines per step; step_fns[e](prev_state_bits_getter, input_bits) -> 0/1 is given as
    (inputs as ('x', e) or ('u', line), function of those values). Elements: S_e (constant, the initial state), U_t_l
    (constant, the input lines at step t), X_t_e for t = 1..steps. out_index: the element read as output.
    """
    labels, ins_all, fns, sources, state = [], [], [], [], []
    idx = {}

    def add(lab, ins, f, value, source=False):
        idx[lab] = len(labels)
        labels.append(lab)
        ins_all.append(tuple(ins))
        fns.append(f)
        state.append(value)
        if source:
            sources.append(idx[lab])

    for e in range(m):
        add(f"S{e}", (), g_const(init[e]), init[e], True)
    for t in range(steps):
        for line in range(n_in):
            add(f"U{t}.{line}", (), g_const(inputs[t][line]), inputs[t][line], True)
    prev = [idx[f"S{e}"] for e in range(m)]
    values = list(init)
    for t in range(1, steps + 1):
        cur = []
        new_values = []
        for e in range(m):
            refs, fn = step_fns[e]
            ii = []
            for kind, r in refs:
                ii.append(prev[r] if kind == "x" else idx[f"U{t - 1}.{r}"])
            f = (lambda s, ii=tuple(ii), fn=fn: fn(tuple(s[i] for i in ii)))
            v = fn(tuple((values[r] if kind == "x" else inputs[t - 1][r]) for kind, r in refs))
            add(f"X{t}.{e}", ii, f, v)
            cur.append(idx[f"X{t}.{e}"])
            new_values.append(v)
        prev = cur
        values = new_values
    sysm = System(name, labels, ins_all, fns, state, sources)
    sysm.outputs = [idx[f"X{t}.{out_index}"] for t in range(1, steps + 1)]
    return sysm


def photodiode_unfolding(init=(1, 1), inputs=None, steps=STEPS, planted=False):
    inputs = inputs or [(0, 1)] * steps
    # D_t = (x1 + x2 + P >= 2) of (U line 0, U line 1, P); P_t = COPY(D)
    d_fn = (lambda v: int(v[0] + v[1] + v[2] >= 2))
    if planted:
        d_first = (lambda v: int(v[0] + v[1] + (1 - v[2]) >= 2))
    step_fns = [((("u", 0), ("u", 1), ("x", 1)), d_fn), ((("x", 0),), lambda v: v[0])]
    sysm = unfold("Figure 19 unfolded", 2, 2, step_fns, 1, init, inputs, steps)
    if planted:
        # the first step's D reads P_0 through NOT (rule: a planted error the equivalence must catch)
        j = sysm.labels.index("X1.0")
        ii = sysm.inputs[j]
        sysm.fns[j] = (lambda s, ii=ii: d_first(tuple(s[i] for i in ii)))
        sysm.net = E.Network(LazyTPM(sysm.fns))
        sysm.planted = True
    return sysm


def fig21_unfolding(init=(0, 1, 0, 1, 0, 1), inputs=None, steps=STEPS):
    inputs = inputs or [(0, 0, 1, 1)] * steps     # lines: I1a, I1b, I2a, I2b
    step_fns = [
        ((("u", 0), ("u", 1), ("x", 2), ("x", 4), ("x", 5)), lambda v: int(v[0] + v[1] + v[2] + v[3] - v[4] >= 2)),
        ((("u", 2), ("u", 3), ("x", 2), ("x", 3), ("x", 5)), lambda v: int(v[0] + v[1] + v[2] + v[3] - v[4] >= 2)),
        ((("x", 0), ("x", 1), ("x", 5)), lambda v: int(v[0] + v[1] - v[2] >= 2)),
        ((("x", 5), ("x", 1), ("x", 2), ("x", 0)), lambda v: int(v[0] + v[1] - v[2] - v[3] >= 1)),
        ((("x", 5), ("x", 0), ("x", 2), ("x", 1)), lambda v: int(v[0] + v[1] - v[2] - v[3] >= 1)),
        ((("x", 4), ("x", 3)), lambda v: (v[0] + v[1]) % 2),
    ]
    sysm = unfold("Figure 21A unfolded", 6, 4, step_fns, 2, init, inputs, steps)
    sysm.outputs2 = [sysm.labels.index(f"X{t}.5") for t in range(1, steps + 1)]
    return sysm


def evaluate_unfolding(sysm, init, inputs):
    """Settle the feed-forward unfolding for given sources (initial state and inputs) and read its outputs."""
    if not hasattr(sysm, "_where"):
        sysm._where = ({e: sysm.labels.index(f"S{e}") for e in range(len(init))},
                       {(t, line): sysm.labels.index(f"U{t}.{line}")
                        for t in range(len(inputs)) for line in range(len(inputs[0]))},
                       [i for i in range(sysm.n) if i not in sysm.sources])
    s_at, u_at, order = sysm._where
    bits = list(sysm.state)
    for e, v in enumerate(init):
        bits[s_at[e]] = v
    for t, row in enumerate(inputs):
        for line, v in enumerate(row):
            bits[u_at[(t, line)]] = v
    for i in order:                                   # elements are added layer by layer, so one pass settles
        bits[i] = sysm.fns[i](bits)
    return bits


def photodiode_equivalence(sysm, steps=STEPS):
    cases = same = 0
    for init in itertools.product((0, 1), repeat=2):
        for seq in itertools.product(itertools.product((0, 1), repeat=2), repeat=steps):
            x, outs = init, []
            for t in range(steps):
                x = photodiode_step(x, seq[t])
                outs.append(photodiode_out(x))
            bits = evaluate_unfolding(sysm, init, seq)
            got = [bits[o] for o in sysm.outputs]
            cases += 1
            same += int(got == outs)
    return cases, same


def fig21_equivalence(sysm, steps=STEPS):
    cases = same = 0
    lines = {v: (int(v >= 1), int(v >= 2)) for v in range(3)}
    for init in itertools.product((0, 1), repeat=6):
        for seq in itertools.product(itertools.product(range(3), repeat=2), repeat=steps):
            x, outs = init, []
            for t in range(steps):
                x = fig21_step(x, seq[t])
                outs.append(fig21_out(x))
            useq = [lines[a] + lines[b] for a, b in seq]
            bits = evaluate_unfolding(sysm, init, useq)
            got = [(bits[o1], bits[o2]) for o1, o2 in zip(sysm.outputs, sysm.outputs2)]
            cases += 1
            same += int(got == outs)
    return cases, same


def fig21_printed_run():
    """Initial states (and alignments) from which Figure 21A as read gives the printed outputs."""
    i1 = [2, 2, 1, 0, 0, 2, 2, 1]
    i2 = [0, 0, 0, 0, 0, 2, 2, 1]
    o1 = [1, 1, 1, 0, 0, 0, 0]
    o2 = [0, 0, 0, 0, 1, 1, 1]
    hits = set()
    for pad in itertools.product(range(3), repeat=6):
        u = list(zip(i1 + list(pad[0::2]), i2 + list(pad[1::2])))
        for s0 in itertools.product((0, 1), repeat=6):
            x, traj = s0, [s0]
            for t in range(len(u)):
                x = fig21_step(x, u[t])
                traj.append(x)
            for lag in (1, 2, 3):
                idx = [t - lag for t in range(4, 11)]
                if [traj[k][2] for k in idx] == o1 and [traj[k][5] for k in idx] == o2:
                    hits.add((lag, s0))
    return sorted(hits)


# ---------------------------------------------------------------- seed-drawn feed-forward systems (rule 6)

def rng_for(seed, tag):
    return random.Random(int(hashlib.sha256(f"oat2014|{tag}|{seed}".encode()).hexdigest(), 16))


def draw_feedforward(rng, k, planted=False):
    labels, inputs, fns, kinds = ["X0", "X1"], [(), ()], [], []
    xs = [rng.randrange(2), rng.randrange(2)]
    fns = [g_const(xs[0]), g_const(xs[1])]
    layers = [[0, 1]]
    for layer in range(1, 4):
        width = rng.choice((2, 3))
        cur = []
        lower = [i for lay in layers for i in lay]
        for w in range(width):
            r = rng.choice((1, 2, 3))
            r = min(r, len(lower))
            first = rng.choice(layers[-1])
            rest = [i for i in lower if i != first]
            ins = [first] + rng.sample(rest, r - 1)
            ins.sort()
            if r == 1:
                kind = rng.choice(("COPY", "NOT"))
                f = g_copy(ins[0]) if kind == "COPY" else g_not(ins[0])
            else:
                choices = ["AND", "OR", "XOR", "NAND", "NOR"] + (["MAJ"] if r == 3 else [])
                kind = rng.choice(choices)
                f = GATES[kind](ins)
            labels.append(f"L{layer}.{w}")
            inputs.append(tuple(ins))
            fns.append(f)
            kinds.append(kind)
            cur.append(len(labels) - 1)
        layers.append(cur)
    n = len(labels)
    last = n - 1
    anc, todo = set(), [last]
    while todo:
        for i in inputs[todo.pop()]:
            if i not in anc:
                anc.add(i)
                todo.append(i)
    target = [x for x in layers[1] if x in anc][0]       # every element reads one of the layer below
    if planted:
        # the last element is read by a first-layer element it rests on, through XOR with what that computed
        base = fns[target]
        fns[target] = (lambda s, base=base, last=last: base(s) ^ s[last])
        inputs[target] = tuple(sorted(set(inputs[target]) | {last}))
    state = tuple([xs[0], xs[1]] + [rng.randrange(2) for _ in range(n - 2)])
    for _ in range(64):                                   # settle: the inputs are constant
        nxt = tuple(f(state) for f in fns)
        if nxt == state:
            break
        state = nxt
    sysm = System(f"feed-forward draw {k}" + (" (planted feedback)" if planted else ""), labels, inputs, fns, state,
                  sources=(0, 1))
    sysm.kinds = kinds
    sysm.layers = layers
    return sysm


# ---------------------------------------------------------------- connectivity and reachability (rule 2)

def strongly_connected(cm, nodes):
    nodes = list(nodes)
    if len(nodes) == 1:
        return True
    sub = set(nodes)

    def reach(start, forward):
        seen, todo = {start}, [start]
        while todo:
            a = todo.pop()
            for b in sub:
                if b not in seen and (cm[a][b] if forward else cm[b][a]):
                    seen.add(b)
                    todo.append(b)
        return seen
    return reach(nodes[0], True) == sub and reach(nodes[0], False) == sub


def causally_significant(sysm):
    n = sysm.n
    return [j for j in range(n) if any(sysm.cm[i][j] for i in range(n)) and any(sysm.cm[j][i] for i in range(n))]


def reachable(sysm, nodes):
    bits = list(sysm.state)
    for x in itertools.product((0, 1), repeat=len(nodes)):
        for i, v in zip(nodes, x):
            bits[i] = v
        b = tuple(bits)
        if all(sysm.fns[i](b) == sysm.state[i] for i in nodes):
            return True
    return False


# ---------------------------------------------------------------- Phi (rule 1)

class Sub(E.Subsystem):
    """engine.Subsystem on the network's own connectivity (PyPhi with a connectivity matrix given), cut connections
    removed; potential purviews are filtered on it as PyPhi's irreducible_purviews does. iit/check.py used PyPhi's
    all-ones default, under which every purview filtered here has phi = 0, so the values are the same."""

    def __init__(self, network, state, nodes, cut=None, tables=None, cache=None, cm=None):
        super().__init__(network, state, nodes, cut=cut, tables=tables, cache=cache)
        if cm is not None:
            k = self.k
            own = [[cm[nodes[a]][nodes[b]] for b in range(k)] for a in range(k)]
            if cut is not None:
                A, B = cut
                for a in A:
                    for b in B:
                        own[a][b] = 0
            self.cm = own


def damaged(sub, direction, mechanism, purview):
    if sub.splits(mechanism):
        return True
    frm, to = (purview, mechanism) if direction == E.CAUSE else (mechanism, purview)
    return any(sub.cut_matrix(a, b) for a in frm for b in to)


def sia(flow, sysm, nodes, full=False):
    """(Phi, concepts, why): PyPhi 1.2's sia, or, with full, every cut computed and no shortcut."""
    nodes = tuple(sorted(nodes))
    k = len(nodes)
    if not full:
        if not strongly_connected(sysm.cm, nodes):
            return 0.0, [], "not strongly connected"
        if k == 1:
            return 0.0, [], "single element"
    cache = {}
    cm = None if full else sysm.cm
    sub = Sub(sysm.net, sysm.state, nodes, cache=cache, cm=cm)
    parent, C0 = {}, []
    for m in E.powerset(range(k)):
        picks = []
        for d in (E.CAUSE, E.EFFECT):
            pick, _ = sub.mice(flow, d, m)
            picks.append(pick)
            if pick is not None and pick[0] > 0:
                parent[(d, m)] = pick
        if None not in picks and min(picks[0][0], picks[1][0]) > 0:
            C0.append(E.Concept(m, picks[0], picks[1], sub))
    ids = {}

    def canon(c):
        c.canon = ids.setdefault(c.signature(), len(ids))
    for c in C0:
        canon(c)
    if not C0:
        return 0.0, [], "no concepts"
    cuts = [((0,), (0,))] if k == 1 else E.directed_bipartition(tuple(range(k)), nontrivial=True)
    best = float("inf")
    for A, B in cuts:
        cs = Sub(sysm.net, sysm.state, nodes, cut=(A, B), tables=sub.uncut, cache=cache, cm=cm)
        mechs = sorted(set(c.mechanism for c in C0) | {m for m in E.powerset(range(k)) if cs.splits(m)},
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
            best = 0.0
            break
        best = min(best, phi)
    return best, C0, "computed"


def describe(sysm, nodes, concepts):
    out = []
    for c in concepts:
        out.append({"mechanism": "".join(sysm.labels[nodes[i]] for i in c.mechanism)
                    if all(len(sysm.labels[nodes[i]]) == 1 for i in c.mechanism)
                    else [sysm.labels[nodes[i]] for i in c.mechanism],
                    "phi": c.phi, "cause": [sysm.labels[nodes[i]] for i in c.cp],
                    "effect": [sysm.labels[nodes[i]] for i in c.ep]})
    return out


def analyse(flow, sysm, log=None, candidates=None):
    """Every candidate set's Phi (rule 1) and the condensation (rule 2)."""
    say = log or (lambda s: None)
    t0 = time.time()
    sig = causally_significant(sysm) if candidates is None else candidates
    rows, skipped = [], []
    for r in range(1, len(sig) + 1):
        for nodes in itertools.combinations(sig, r):
            if r > 1 and not strongly_connected(sysm.cm, nodes):
                continue                              # Phi = 0 by rule 1, recorded as a count only
            if r == 1:
                continue
            if not reachable(sysm, nodes):
                skipped.append(sysm.name_of(nodes))
                continue
            phi, concepts, why = sia(flow, sysm, nodes)
            rows.append({"set": sysm.name_of(nodes), "nodes": list(nodes), "phi": phi, "why": why,
                         "concepts": len(concepts), "orders": sorted(len(c.mechanism) for c in concepts),
                         "concept_list": describe(sysm, nodes, concepts)})
    total = 2 ** len(sig) - 1
    complexes = sorted((r for r in rows if r["phi"] > 0), key=lambda r: (r["phi"], len(r["nodes"]), r["nodes"]),
                       reverse=True)
    kept, covered = [], set()
    for r in complexes:
        if not covered & set(r["nodes"]):
            kept.append(r)
            covered |= set(r["nodes"])
    say(f"{sysm.name}: {len(rows)} strongly connected candidate sets of {total}; condensation "
        f"{[(r['set'], r['phi']) for r in kept]} ({time.time() - t0:.1f} s)")
    return {"system": sysm.name, "candidates": total, "computed": len(rows), "unreachable": skipped,
            "rows": rows, "condensation": [r["set"] for r in kept], "kept": kept,
            "seconds": round(time.time() - t0, 1)}


def full_checks(flow, sysm, max_size=FULL_MAX):
    """Rule 7: every set of up to max_size elements computed through every cut, no shortcut."""
    out = {"sets": 0, "nonsc": 0, "nonsc_nonzero": [], "singles": {}, "sc_nonzero": 0}
    for r in range(1, max_size + 1):
        for nodes in itertools.combinations(range(sysm.n), r):
            phi, _, _ = sia(flow, sysm, nodes, full=True)
            out["sets"] += 1
            if r == 1:
                if phi > 0:
                    out["singles"][sysm.name_of(nodes)] = phi
                continue
            if not strongly_connected(sysm.cm, nodes):
                out["nonsc"] += 1
                if phi != 0:
                    out["nonsc_nonzero"].append([sysm.name_of(nodes), phi])
            elif phi > 0:
                out["sc_nonzero"] += 1
    return out


# ---------------------------------------------------------------- printed values (rule 8)

def matches(value, printed, digits):
    """(cut, rounded): whether value cut or rounded to the printed digits equals the printed number."""
    from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
    q = Decimal(1).scaleb(-digits)
    v = Decimal(repr(value))
    p = Decimal(str(printed))
    return v.quantize(q, rounding=ROUND_DOWN) == p, v.quantize(q, rounding=ROUND_HALF_UP) == p


def phi_of(result, name):
    for r in result["rows"]:
        if r["set"] == name:
            return r
    return None


# ---------------------------------------------------------------- the run

def build(results):
    os.makedirs(results, exist_ok=True)
    lib = os.path.join(os.path.abspath(results), "flow.so")
    subprocess.run(["gcc", "-O2", "-shared", "-fPIC", "-o", lib, os.path.join(HERE, "flow.c"), "-lm"], check=True)
    return lib


def run(seed, results="results", log=None):
    say = log or (lambda s: None)
    if not re.fullmatch(r"[0-9a-f]{64}", seed or ""):
        raise Refused("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    lib = build(results)
    flows = {1: E.Flow(lib, 1), 0: E.Flow(lib, 0)}
    flow = flows[VERDICT_MODE]
    t_start = time.time()

    paper = {"16": fig16(), "17A": fig17a(), "17B": fig17b(), "17C": fig17c(), "18": fig18(), "19": fig19(),
             "20A": fig20a()}
    unf = photodiode_unfolding()
    draws = [draw_feedforward(rng_for(seed, f"ff{k}"), k) for k in range(FF_DRAWS)]
    planted_draws = [draw_feedforward(rng_for(seed, f"ff{k}"), k, planted=True) for k in range(FF_DRAWS)]

    detail = {"claim": CLAIM, "test": TEST, "mode": VERDICT_MODE, "systems": {}, "full": {}, "printed": [],
              "beside": {}, "controls": []}
    res = {}
    for key, sysm in paper.items():
        res[key] = analyse(flow, sysm, say)
    res["unfold"] = analyse(flow, unf, say)
    res["ff"] = [analyse(flow, d, say) for d in draws]
    for key, r in res.items():
        if key == "ff":
            detail["systems"]["ff"] = [{k: v for k, v in x.items() if k != "kept"} for x in r]
        else:
            detail["systems"][key] = {k: v for k, v in r.items() if k != "kept"}

    # the conditions (rule 5)
    def cond(key):
        return res[key]["condensation"]
    c = {}
    c["a"] = cond("16") == ["ABC", "DE", "FG"] or cond("16") == ["ABC", "FG", "DE"]
    c["b"] = sorted(cond("17A")) == ["AB", "CD", "EF"]
    b17 = phi_of(res["17B"], "ABCDE")
    c17 = phi_of(res["17C"], "ABCDE")
    c["c"] = cond("17B") == ["ABCDE"] and b17 is not None and b17["concepts"] == 5 and b17["orders"] == [1] * 5
    c["d"] = (cond("17C") == ["ABCDE"] and b17 is not None and c17 is not None and c17["concepts"] > b17["concepts"]
              and c17["phi"] > b17["phi"])
    c["e"] = cond("18") == ["ABCD"]
    c["f"] = cond("19") == ["DP"]
    c["g"] = cond("20A") == []
    c["h"] = all(r["condensation"] == [] for r in res["ff"])
    cases, same = photodiode_equivalence(unf)
    c["i"] = res["unfold"]["condensation"] == [] and cases == 4 * 4 ** STEPS and same == cases and c["f"]
    detail["conditions"] = c
    detail["equivalence"] = {"cases": cases, "same": same}

    # rule 7: full computations
    full_ok = True
    full_sets = nonsc = 0
    singles = {}
    for key, sysm in list(paper.items()) + [("unfold", unf)] + [(f"ff{k}", d) for k, d in enumerate(draws)]:
        fc = full_checks(flow, sysm)
        detail["full"][key] = fc
        full_sets += fc["sets"]
        nonsc += fc["nonsc"]
        if fc["nonsc_nonzero"]:
            full_ok = False
        if fc["singles"]:
            singles[key] = fc["singles"]
    say(f"full computations: {full_sets} sets, {nonsc} not strongly connected, agreement {full_ok}")

    # controls
    controls = []
    one = flow.transport([1.0], [1.0], [[1.0]])
    controls.append({"control": "one unit moved one step", "value": one, "holds": abs(one - 1) < 1e-12})
    p, q = [0.25] * 4, [1 / 3, 1 / 6, 1 / 6, 1 / 3]
    v1, v0 = flows[1].hamming_emd(p, q), flows[0].hamming_emd(p, q)
    controls.append({"control": "pyemd's 0.166666, exact 1/6", "pyemd": v1, "exact": v0,
                     "holds": abs(v1 - 0.166666) < 1e-12 and abs(v0 - 1 / 6) < 1e-12})
    controls.append({"control": "full computations agree with the connectivity shortcut", "sets": full_sets,
                     "not_strongly_connected": nonsc, "holds": full_ok and nonsc > 0})
    unreach = {k: r["unreachable"] for k, r in res.items() if k != "ff" and r["unreachable"]}
    depicted = {k: reachable(s, causally_significant(s)) for k, s in paper.items()}
    controls.append({"control": "depicted states reachable", "states": depicted,
                     "holds": all(depicted.values())})
    pl18 = analyse(flow, fig18(planted=True), say)
    controls.append({"control": "Figure 18 with A constant has no complex", "condensation": pl18["condensation"],
                     "holds": pl18["condensation"] == []})
    pl_ff = [analyse(flow, d, say) for d in planted_draws]
    made = [k for k, r in enumerate(pl_ff) if r["condensation"]]
    controls.append({"control": "planted feedback creates a complex in a feed-forward draw", "draws": made,
                     "holds": len(made) >= 1})
    bad = photodiode_unfolding(planted=True)
    bc, bs = photodiode_equivalence(bad)
    controls.append({"control": "planted error in the unfolding caught", "cases": bc, "same": bs,
                     "holds": bs < bc})
    detail["controls"] = controls
    held = sum(1 for x in controls if x["holds"])

    # beside: printed values
    printed = []

    def pv(label, value, printed_value, digits):
        if value is None:
            printed.append({"what": label, "printed": printed_value, "computed": None, "cut": False, "rounded": False})
            return
        cut, rounded = matches(value, printed_value, digits)
        printed.append({"what": label, "printed": printed_value, "computed": value, "cut": cut, "rounded": rounded})
    r16 = res["16"]
    for name, val, dg in (("ABC", 1.92, 2), ("ABCDE", 0.021, 3), ("DE", 0.028, 3), ("FG", 0.028, 3)):
        row = phi_of(r16, name)
        pv(f"Figure 16: Phi of {name}", row["phi"] if row else None, val, dg)
    for name in ("AB", "CD", "EF"):
        row = phi_of(res["17A"], name)
        pv(f"Figure 17A: Phi of {name}", row["phi"] if row else None, 1.00, 2)
    row = phi_of(res["17A"], "ABCDEF")
    pv("Figure 17A: Phi of ABCDEF", row["phi"] if row else None, 0.53, 2)
    pv("Figure 17B: Phi of ABCDE", b17["phi"] if b17 else None, 0.003, 3)
    pv("Figure 17C: Phi of ABCDE", c17["phi"] if c17 else None, 10.75, 2)
    row18 = phi_of(res["18"], "ABCD")
    pv("Figure 18: Phi of ABCD", row18["phi"] if row18 else None, 1, 0)
    row19 = phi_of(res["19"], "DP")
    pv("Figure 19: Phi of DP", row19["phi"] if row19 else None, 1, 0)
    counts = {"17A AB": (phi_of(res["17A"], "AB") or {}).get("concepts"), "17B": (b17 or {}).get("concepts"),
              "17C": (c17 or {}).get("concepts"), "18": (row18 or {}).get("concepts"),
              "19": (row19 or {}).get("concepts")}
    printed_counts = {"17A AB": 2, "17B": 5, "17C": 30, "18": 4, "19": 2}
    for k, v in counts.items():
        printed.append({"what": f"concepts {k}", "printed": printed_counts[k], "computed": v,
                        "cut": v == printed_counts[k], "rounded": v == printed_counts[k]})
    concept_phis = []

    def cphis(row, label, want, digits):
        if not row:
            return
        vals = [x["phi"] for x in row["concept_list"]]
        concept_phis.append({"what": label, "printed": want, "computed": vals,
                             "all_match": all(any(matches(v, want, digits)) for v in vals) if vals else False})
    cphis(phi_of(res["17A"], "AB"), "17A AB's concepts", 0.5, 3)
    cphis(b17, "17B's concepts", 0.0161, 4)
    cphis(row18, "18's concepts", 0.5, 1)
    cphis(row19, "19's concepts", 0.5, 1)
    if c17:
        first = [x["phi"] for x in c17["concept_list"] if isinstance(x["mechanism"], str) and len(x["mechanism"]) == 1]
        two = {x["mechanism"]: x["phi"] for x in c17["concept_list"] if x["mechanism"] in ("AB", "AC")}
        concept_phis.append({"what": "17C first-order concepts", "printed": 0.25, "computed": first,
                             "all_match": bool(first) and all(any(matches(v, 0.25, 2)) for v in first)})
        concept_phis.append({"what": "17C AB and AC", "printed": 0.2, "computed": two,
                             "all_match": len(two) == 2 and all(any(matches(v, 0.2, 1)) for v in two.values())})
    detail["printed"] = printed
    detail["concept_phis"] = concept_phis
    if row18:
        a = [x for x in row18["concept_list"] if x["mechanism"] == "A"]
        detail["beside"]["fig18_A"] = a

    # beside: the photodiode in its four states
    same_mics = []
    for s in itertools.product((0, 1), repeat=2):
        sysm = fig19(state=s)
        if not reachable(sysm, [0, 1]):
            same_mics.append({"state": s, "reachable": False})
            continue
        phi, concepts, _ = sia(flow, sysm, (0, 1))
        same_mics.append({"state": s, "reachable": True, "phi": phi,
                          "concepts": [(x["mechanism"], x["phi"], x["cause"], x["effect"])
                                       for x in describe(sysm, (0, 1), concepts)]})
    detail["beside"]["photodiode_states"] = same_mics
    sig0 = [(m["phi"], [(c[0], c[1]) for c in m["concepts"]]) for m in same_mics if m.get("reachable")]
    same_count = sum(1 for x in sig0 if x == sig0[0]) if sig0 else 0

    # beside: exact arithmetic
    exact = {}
    for key in ("16", "17A", "17B", "17C", "18", "19", "20A"):
        try:
            r = analyse(flows[0], paper[key], None)
            exact[key] = r["condensation"]
        except ValueError as e:
            exact[key] = f"refused: {e}"
    detail["beside"]["exact_condensations"] = exact
    exact_same = sum(1 for k in exact if exact[k] == res[k]["condensation"])

    # beside: Figure 21A as read
    f21 = fig21a()
    r21 = analyse(flow, f21, say)
    six = phi_of(r21, "ABDHIJ")
    u21 = fig21_unfolding()
    ru21 = analyse(flow, u21, say)
    c21, s21 = fig21_equivalence(u21)
    run_hits = fig21_printed_run()
    detail["beside"]["fig21a"] = {"condensation": r21["condensation"], "six": six, "unfolding": ru21["condensation"],
                                  "unfolding_nodes": u21.n, "equivalence": [c21, s21],
                                  "printed_run": [list(h) for h in run_hits]}
    detail["beside"]["fig16_abcde"] = phi_of(r16, "ABCDE")
    detail["beside"]["singles_full"] = singles
    detail["beside"]["unreachable"] = unreach

    met = sum(1 for v in c.values() if v)
    passed = met == len(c) and held == len(controls)
    printed_match = sum(1 for x in printed if x["cut"] or x["rounded"])

    def phi_or(row):
        return row["phi"] if row else -1.0

    out = {
        "test_passed": int(passed),
        "conditions_met": met,
        "conditions_total": len(c),
        "controls_passed": held,
        "controls_total": len(controls),
        "fig16_condensation": " ".join(cond("16")) or "none",
        "fig16_phi_abc": phi_or(phi_of(r16, "ABC")),
        "fig16_phi_de": phi_or(phi_of(r16, "DE")),
        "fig16_phi_fg": phi_or(phi_of(r16, "FG")),
        "fig16_phi_abcde": phi_or(phi_of(r16, "ABCDE")),
        "fig17a_condensation": " ".join(cond("17A")) or "none",
        "fig17a_phi_ab": phi_or(phi_of(res["17A"], "AB")),
        "fig17a_phi_whole": phi_or(phi_of(res["17A"], "ABCDEF")),
        "fig17b_condensation": " ".join(cond("17B")) or "none",
        "fig17b_phi": phi_or(b17),
        "fig17b_concepts": b17["concepts"] if b17 else -1,
        "fig17c_condensation": " ".join(cond("17C")) or "none",
        "fig17c_phi": phi_or(c17),
        "fig17c_concepts": c17["concepts"] if c17 else -1,
        "fig18_condensation": " ".join(cond("18")) or "none",
        "fig18_phi": phi_or(row18),
        "fig18_concepts": row18["concepts"] if row18 else -1,
        "fig19_condensation": " ".join(cond("19")) or "none",
        "fig19_phi": phi_or(row19),
        "fig19_states_same_mics": same_count,
        "fig20a_condensation": " ".join(cond("20A")) or "none",
        "ff_systems": len(draws),
        "ff_elements": sum(d.n for d in draws),
        "ff_complexes": sum(len(r["condensation"]) for r in res["ff"]),
        "unfold_elements": unf.n,
        "unfold_complexes": len(res["unfold"]["condensation"]),
        "unfold_cases": cases,
        "unfold_equal": same,
        "full_sets": full_sets,
        "full_not_strongly_connected": nonsc,
        "printed_matched": printed_match,
        "printed_total": len(printed),
        "exact_same_condensations": exact_same,
        "fig21a_condensation": " ".join(r21["condensation"]) or "none",
        "fig21a_phi": phi_or(six),
        "fig21a_concepts": six["concepts"] if six else -1,
        "fig21a_unfold_complexes": len(ru21["condensation"]),
        "fig21a_unfold_equal": s21,
        "fig21a_unfold_cases": c21,
        "fig21a_printed_run_states": len(run_hits),
    }
    detail["seconds"] = round(time.time() - t_start, 1)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as f:
        json.dump(detail, f, indent=1, sort_keys=True, default=str)
        f.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    try:
        out, _ = run(seed, log=lambda s: print(s, file=sys.stderr, flush=True))
    except Refused as e:
        sys.exit(f"iit/oat2014.py: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
