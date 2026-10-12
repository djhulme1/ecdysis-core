"""Findlay et al.'s weakly connected stored-program computer WCC(k), ported from the authors' divided_clock_computer.py
(CSC-UW/Findlay_et_al_2024a at 08f62b8), with graphiit's graph semantics (CSC-UW/graphiit at 1318d8b).

Both were read as data, never run here. A graph is a list of (label, function, *inputs) in the authors' order; a unit's
next state is its function of its inputs' current states, in that order, all units at once. The port keeps graphiit's
rules for a subgraph: inputs outside it are dropped, a unit left with none becomes MAXENT (0.5) with a self-input; and
its vokram blanket: the units, their parents, their children and their parents' children.
"""

import itertools

import numpy as np

from . import engine


def AND(inputs):
    return int(sum(inputs) == len(inputs))


def OR(inputs):
    return int(sum(inputs) >= 1)


def COPY(inputs):
    if len(inputs) > 1:
        raise AssertionError("COPY gates cannot have multiple inputs")
    return OR(inputs)


def NOR(inputs):
    return 1 - OR(inputs)


def NOT(inputs):
    if len(inputs) > 1:
        raise AssertionError("NOT gates cannot have multiple inputs")
    return NOR(inputs)


def XOR(inputs):
    return int(sum(inputs) % 2 == 1)


def MAXENT(inputs):
    return 0.5


FUNCTIONS = {"AND": AND, "OR": OR, "COPY": COPY, "NOR": NOR, "NOT": NOT, "XOR": XOR, "MAXENT": MAXENT}


def clock_and(inputs):
    """get_clock_config's _and: every input but the last ON, and the last OFF."""
    return int(sum(inputs[:-1]) == len(inputs[:-1]) and not inputs[-1])


def instruction_register(inputs):
    if len(inputs) != 2:
        raise AssertionError(f"IR unit expected 2 inputs, got {len(inputs)}")
    return int(bool(inputs[0]) and not inputs[1])


def mux_function(selector_state):
    n = len(selector_state)

    def f(inputs):
        if len(inputs) != n + 1:
            raise AssertionError(f"{n}-bit mux must receive {n + 1} inputs.")
        return int(tuple(inputs[:n]) == tuple(selector_state) and bool(inputs[n]))
    return f


# ---------------------------------------------------------------- WCC(k), as get_graph_config(k, feedback=False)

def labels(k):
    n = 2 ** k
    s = 2 ** n
    targets = [f"T{i}" for i in range(n)]
    return {
        "targets": targets,
        "program": [[f"{t}/{i}" for t in targets] for i in range(s)],
        "ir": [f"IR/{i}" for i in range(s)],
        "clock": (["C0"], [f"X{i + 1}" for i in range(k)], [f"A{i + 1}" for i in range(k)]),
        "registers": [[f"{t}R0", f"{t}R1", f"{t}R2"] for t in targets],
        "buffers": [f"B{i}" for i in range(2 * n - 5)],
        "mux": [f"M{i}" for i in range(s)],
        "out": "O",
    }


def config(k):
    L = labels(k)
    n = 2 ** k
    c, x, a = L["clock"]
    ca, cx = c + a, c + x
    clock = [(c[0], "NOT", c[0])]
    x_config = [(x[i], "XOR", x[i], ca[i]) for i in range(k)]
    a_config = [(a[i], clock_and, *cx[: i + 2], a[i]) for i in range(k)]
    clock += [unit for pair in zip(x_config, a_config) for unit in pair]
    bmo = L["buffers"] + [L["out"]]
    registers = [unit for i, r in enumerate(L["registers"]) for unit in
                 [(r[0], "XOR", r[0], r[1]), (r[1], "AND", r[2], a[-1]), (r[2], "XOR", r[0], bmo[i])]]
    program = [(line[i], "COPY", line[(i + 1) % n]) for line in L["program"] for i in range(n)]
    ir = [(m, instruction_register, line[0], x[-1]) for m, line in zip(L["ir"], L["program"])]
    outputs = [r[0] for r in L["registers"]]
    mux = [(m, mux_function(s), *outputs, i) for m, s, i in zip(L["mux"], engine.all_states(n), L["ir"])]
    mux_out = [(L["out"], "OR", *L["mux"])]
    buffers = [(bmo[i], "COPY", bmo[i + 1]) for i in range(len(bmo) - 1)]
    return clock + registers + program + ir + mux + mux_out + buffers


def initial_state(k, target_tpm, target_state):
    """get_initial_state_config: the program bits where the target's TPM has a 1, the data registers' outputs where its
    state has a 1, and C0; everything else OFF."""
    L = labels(k)
    on = {L["program"][row][col] for row, col in zip(*np.where(np.array(target_tpm)))}
    on |= {L["registers"][j][0] for j, v in enumerate(target_state) if v}
    on |= set(L["clock"][0])
    return {unit[0]: int(unit[0] in on) for unit in config(k)}


class Graph:
    """A graphiit graph: units in config order, each with its function and its inputs in config order."""

    def __init__(self, units, state):
        self.units = [u[0] for u in units]
        self.function = {u[0]: (FUNCTIONS[u[1]] if isinstance(u[1], str) else u[1]) for u in units}
        self.inputs = {u[0]: list(u[2:]) for u in units}
        self.config = list(units)
        self.state = {u: int(state[u]) if state[u] in (0, 1) else state[u] for u in self.units}
        self.parents = {u: list(dict.fromkeys(self.inputs[u])) for u in self.units}
        self.children = {u: [] for u in self.units}
        for u in self.units:
            for p in self.parents[u]:
                self.children[p].append(u)

    def edges(self):
        return sum(len(p) for p in self.parents.values())

    def step(self, state=None):
        state = self.state if state is None else state
        return {u: self.function[u]([state[i] for i in self.parents[u]]) for u in self.units}

    def tic(self, times=1):
        for _ in range(times):
            self.state = self.step()

    def subgraph(self, nodes, inputless="MAXENT"):
        nodes = set(nodes)
        units = []
        for u in self.config:
            if u[0] not in nodes:
                continue
            kept = [i for i in u[2:] if i in nodes]
            units.append((u[0], u[1], *kept) if kept else (u[0], inputless, u[0]))
        return Graph(units, {u: self.state[u] for u in self.units if u in nodes})

    def vokram_blanket(self, nodes):
        nodes = set(nodes)
        parents = {p for u in nodes for p in self.parents[u]}
        children = {c for u in nodes for c in self.children[u]}
        parents_children = {c for p in parents for c in self.children[p]}
        return self.subgraph(nodes | parents | children | parents_children)

    def network(self):
        """The engine's Network of this graph, with graphiit's TPM (rows little-endian) and adjacency."""
        m = len(self.units)
        tpm = np.zeros([2 ** m, m])
        for row, s in enumerate(engine.all_states(m)):
            nxt = self.step(dict(zip(self.units, s)))
            tpm[row] = [float(nxt[u]) for u in self.units]
        cm = np.zeros((m, m), dtype=int)
        index = {u: i for i, u in enumerate(self.units)}
        for u in self.units:
            for p in self.parents[u]:
                cm[index[p]][index[u]] = 1
        return engine.Network(tpm, cm, self.units)

    def state_array(self):
        return tuple(int(self.state[u]) for u in self.units)


def computer(k, target_tpm, target_state):
    return Graph(config(k), initial_state(k, target_tpm, target_state))


def simulate(k, target_tpm, target_state, transitions):
    """The data registers' outputs after one update and then every 2n updates, against the target's own successive
    states: (number matched, first mismatch or None)."""
    n = 2 ** k
    graph = computer(k, target_tpm, target_state)
    outputs = [r[0] for r in labels(k)["registers"]]
    tpm = np.array(target_tpm)
    expected = tuple(int(v) for v in target_state)
    graph.tic(1)
    for t in range(transitions):
        got = tuple(int(graph.state[o]) for o in outputs)
        if got != expected:
            return t, (t, expected, got)
        row = sum(v << i for i, v in enumerate(expected))
        expected = tuple(int(v) for v in tpm[row])
        graph.tic(2 * n)
    return transitions, None


def cycles(target_tpm):
    """get_cycles (compact): from every state in little-endian order not yet visited, the states until one repeats."""
    tpm = np.array(target_tpm)
    n = tpm.shape[1]
    visited, out = [], []
    for state in engine.all_states(n):
        if state in visited:
            continue
        cycle = []
        while state not in cycle:
            cycle.append(state)
            row = sum(v << i for i, v in enumerate(state))
            state = tuple(int(v) for v in tpm[row])
        out.append(cycle)
        visited += cycle
    return out


def check_every_cycle(k, target_tpm):
    """check_tpm_simulation: the computer started at the first state of each cycle shows the whole cycle."""
    n = 2 ** k
    outputs = [r[0] for r in labels(k)["registers"]]
    for cycle in cycles(target_tpm):
        graph = computer(k, target_tpm, cycle[0])
        graph.tic(1)
        for state in cycle:
            if tuple(int(graph.state[o]) for o in outputs) != tuple(state):
                return False
            graph.tic(2 * n)
    return True


def strongly_connected_components(graph, removed=()):
    """Tarjan's components of the graph's units, without the removed ones; each sorted, components in a fixed order."""
    removed = set(removed)
    units = [u for u in graph.units if u not in removed]
    index, low, on_stack, stack, out = {}, {}, set(), [], []
    counter = itertools.count()

    def visit(v):
        work = [(v, iter([c for c in graph.children[v] if c not in removed]))]
        index[v] = low[v] = next(counter)
        stack.append(v)
        on_stack.add(v)
        while work:
            node, it = work[-1]
            advanced = False
            for w in it:
                if w not in index:
                    index[w] = low[w] = next(counter)
                    stack.append(w)
                    on_stack.add(w)
                    work.append((w, iter([c for c in graph.children[w] if c not in removed])))
                    advanced = True
                    break
                if w in on_stack:
                    low[node] = min(low[node], index[w])
            if advanced:
                continue
            work.pop()
            if work:
                low[work[-1][0]] = min(low[work[-1][0]], low[node])
            if low[node] == index[node]:
                component = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    component.append(w)
                    if w == node:
                        break
                out.append(sorted(component, key=graph.units.index))

    for u in units:
        if u not in index:
            visit(u)
    return sorted(out, key=lambda c: graph.units.index(c[0]))


def cyclic(graph, component):
    """A component holds a cycle: more than one unit, or one unit that inputs to itself."""
    return len(component) > 1 or component[0] in graph.parents[component[0]]
