"""IIT 4.0 as PyPhi 2.0.0a1 (wmayner/pyphi at c1a7f4e) computes it under Findlay et al.'s pyphi_config.yml, written afresh.

Imago's laboratory (https://ecdysis.me/a/Imago). PyPhi's source at that commit was read as data and none of it is run
by this module; PyPhi itself was run only in a sandbox with no network, to compute the results in iit4/reference/ that
tests/test_iit4.py holds this module to (70 states of 31 networks, to the distinction, purview and specified state; the
partitions and cuts in PyPhi's order). Every convention below is PyPhi's, with the authors' configuration (IIT_VERSION
4.0; REPERTOIRE_DISTANCE and
REPERTOIRE_DISTANCE_INFORMATION GENERALIZED_INTRINSIC_DIFFERENCE; SYSTEM_PARTITION_TYPE SET_UNI/BI with 3.0-style cuts
and no complete partition; PARTITION_TYPE ALL; DISTINCTION_PHI_NORMALIZATION NUM_CONNECTIONS_CUT; MIP_TIE_RESOLUTION
NORMALIZED_PHI then NEGATIVE_PHI; PURVIEW_TIE_RESOLUTION and STATE_TIE_RESOLUTION PHI; RELATION_COMPUTATION CONCRETE;
SINGLE_MICRO_NODES_WITH_SELFLOOPS_HAVE_PHI; SHORTCIRCUIT_SIA; VALIDATE_SUBSYSTEM_STATES; PRECISION 13).

- States are little-endian: unit k of state index i is (i >> k) & 1. A TPM is state-by-node, multidimensional: tpm[s_0,
  ..., s_{n-1}, k] is the probability that unit k is ON next.
- A candidate system's effect TPM fixes every other unit at its current state; its cause TPM is PyPhi's backward TPM,
  which weights the other units' previous states by the probability of the whole current state.
- A unit's TPM averages uniformly over every unit that is not its input (by the connectivity matrix, after any cut).
- Every value of information is the generalised intrinsic difference, selectivity * log2(p / q) with nan taken as 0.
- phi_s: the system's specified cause and effect states are those of maximal intrinsic information (the first such
  state in little-endian order); each SET_UNI/BI cut gives min over cause and effect of the GID between the intact and
  cut probability of the specified state; the minimum information partition minimises phi / (connections cut), ties to
  the larger phi; evaluation stops at the first cut whose phi is not positive. Not strongly connected: 0.
- Distinctions: every non-empty mechanism; for each direction, every purview that is not trivially reducible (in
  PyPhi's own iteration order, which decides among tied purviews); the specified states of maximal intrinsic
  information, all kept; each scored by its MIP over all mechanism-purview partitions (phi / connections cut, ties to
  the larger phi, stopping at the first that is not positive); the state, then the purview, of greatest phi (ties
  within 1e-13 to the first). A distinction is kept if min(cause phi, effect phi) is positive and, among its tied
  alternatives, one cause and one effect are congruent with the system's specified states.
- Relations: every set of distinctions whose purview unions (units with their specified states) intersect, and each
  distinction alone whose cause and effect share units; phi_r = |shared units| * min over relata of phi_d / |union|.
  Phi = sum of phi_d + sum of phi_r.
- Order: partitions, cuts, states and purviews are generated in PyPhi's orders (Knuth's k-partitions, set partitions,
  little-endian states, the iteration order of a set of index tuples), because the first of tied candidates is kept.
  So, as in PyPhi, the Phi-structure can depend on the order of the units: PQRS in 0101 has 13 distinctions and Phi
  391.25 in the authors' order and 12 and 209.84 with its units reversed, in PyPhi and here alike.
"""

import functools
import itertools
import math

import numpy as np

PRECISION = 13
EPSILON = 10.0 ** (-PRECISION)
CAUSE, EFFECT = "cause", "effect"
BOTH = (CAUSE, EFFECT)


class Unreachable(Exception):
    """The candidate system's current state cannot follow from any state (PyPhi's StateUnreachableError)."""


# ---------------------------------------------------------------- PyPhi's comparisons and orders

def eq(x, y):
    return math.isclose(x, y, rel_tol=EPSILON, abs_tol=EPSILON)


def positive(x):
    return not eq(x, 0) and bool(x > 0)


def lt(x, y):
    """PyPhiFloat's <: strictly less and not equal within PRECISION."""
    return x < y and not eq(x, y)


def all_states(n):
    """Every state of n binary units, little-endian (the first unit varies fastest)."""
    for state in itertools.product((0, 1), repeat=n):
        yield state[::-1]


def powerset(items, nonempty=False, reverse=False):
    items = list(items)
    sizes = range(1 if nonempty else 0, len(items) + 1)
    if reverse:
        sizes = reversed(sizes)
        items.reverse()
    return itertools.chain.from_iterable(itertools.combinations(items, r) for r in sizes)


def set_partitions(collection):
    """PyPhi's combinatorics._set_partitions, in its order."""
    collection = list(collection)
    if not collection:
        return
    if len(collection) == 1:
        yield [collection]
        return
    first = collection[0]
    for smaller in set_partitions(collection[1:]):
        for n, subset in enumerate(smaller):
            yield smaller[:n] + [[first] + subset] + smaller[n + 1:]
        yield [[first]] + smaller


def k_partitions(collection, k):
    """Every partition of collection into exactly k non-empty blocks, in the order of Knuth's algorithm (TAOCP 7.2.1.5,
    exercise 17) as PyPhi's partition.k_partitions generates it: the order decides which of two tied partitions is the
    MIP."""
    collection = list(collection)
    n = len(collection)
    if n == 0 or k < 1:
        return []
    if k == 1:
        return [[collection]]
    if k == n:
        return [[[item] for item in collection]]
    a = [0] * (n + 1)
    for j in range(1, k + 1):
        a[n - k + j] = j - 1

    def visit():
        parts = [[] for _ in range(k)]
        for j in range(n):
            parts[a[j + 1]].append(collection[j])
        return parts

    def f(mu, nu, sigma):
        if mu == 2:
            yield visit()
        else:
            yield from f(mu - 1, nu - 1, (mu + sigma) % 2)
        if nu == mu + 1:
            a[mu] = mu - 1
            yield visit()
            while a[nu] > 0:
                a[nu] -= 1
                yield visit()
        elif nu > mu + 1:
            if (mu + sigma) % 2 == 1:
                a[nu - 1] = mu - 1
            else:
                a[mu] = mu - 1
            yield from (b(mu, nu - 1, 0) if (a[nu] + sigma) % 2 == 1 else f(mu, nu - 1, 0))
            while a[nu] > 0:
                a[nu] -= 1
                yield from (b(mu, nu - 1, 0) if (a[nu] + sigma) % 2 == 1 else f(mu, nu - 1, 0))

    def b(mu, nu, sigma):
        if nu == mu + 1:
            while a[nu] < mu - 1:
                yield visit()
                a[nu] += 1
            yield visit()
            a[mu] = 0
        elif nu > mu + 1:
            yield from (f(mu, nu - 1, 0) if (a[nu] + sigma) % 2 == 1 else b(mu, nu - 1, 0))
            while a[nu] < mu - 1:
                a[nu] += 1
                yield from (f(mu, nu - 1, 0) if (a[nu] + sigma) % 2 == 1 else b(mu, nu - 1, 0))
            if (mu + sigma) % 2 == 1:
                a[nu - 1] = 0
            else:
                a[mu] = 0
        if mu == 2:
            yield visit()
        else:
            yield from b(mu - 1, nu - 1, (mu + sigma) % 2)

    return f(k, n, 0)


def distinct_permutations(items):
    return sorted(set(itertools.permutations(items)))


def gid(forward, partitioned, selectivity):
    """The generalised intrinsic difference, elementwise: selectivity * log2(forward / partitioned), nan -> 0."""
    with np.errstate(all="ignore"):
        informativeness = np.nan_to_num(np.log2(np.divide(forward, partitioned)), nan=0.0)
    return selectivity * informativeness


# ---------------------------------------------------------------- connectivity

def strongly_connected(cm, nodes):
    nodes = list(nodes)
    if len(nodes) <= 1:
        return True
    sub = np.asarray(cm)[np.ix_(nodes, nodes)] != 0

    def reach(adj):
        seen, todo = {0}, [0]
        while todo:
            a = todo.pop()
            for b in np.flatnonzero(adj[a]):
                if int(b) not in seen:
                    seen.add(int(b))
                    todo.append(int(b))
        return len(seen) == len(nodes)

    return reach(sub) and reach(sub.T)


def block_cm(cm):
    """PyPhi's connectivity.block_cm."""
    if np.any(cm.sum(1) == 0):
        return True
    if np.all(cm.sum(1) == 1):
        return True
    outputs = list(range(cm.shape[1]))

    def outputs_of(nodes):
        return np.where(cm[nodes, :].sum(0))[0]

    def inputs_to(nodes):
        return np.where(cm[:, nodes].sum(1))[0]

    sources = [np.argmax(cm.sum(1))]
    sinks = outputs_of(sources)
    sink_inputs = inputs_to(sinks)
    while True:
        if np.array_equal(sink_inputs, sources):
            return True
        sources = sink_inputs
        sinks = outputs_of(sources)
        sink_inputs = inputs_to(sinks)
        if np.array_equal(sinks, outputs):
            return False


def block_reducible(cm, nodes1, nodes2):
    """PyPhi's connectivity.block_reducible: whether connections from nodes1 to nodes2 are trivially reducible."""
    if not nodes1 or not nodes2:
        return True
    sub = np.asarray(cm)[np.ix_(nodes1, nodes2)]
    if not sub.sum(0).all() or not sub.sum(1).all():
        return True
    if len(nodes1) > 1 and len(nodes2) > 1:
        return block_cm(sub)
    return False


def ordered(direction, mechanism, purview):
    return (purview, mechanism) if direction == CAUSE else (mechanism, purview)


# ---------------------------------------------------------------- the network and its TPMs

class Network:
    def __init__(self, tpm, cm=None, labels=None):
        tpm = np.asarray(tpm, dtype=float)
        if tpm.ndim == 2:
            n = tpm.shape[1]
            if tpm.shape[0] != 2 ** n:
                raise ValueError("a state-by-node TPM needs 2^n rows")
            tpm = tpm.reshape([2] * n + [n], order="F")
        self.tpm = tpm
        self.size = tpm.shape[-1]
        self.indices = tuple(range(self.size))
        self.cm = np.ones((self.size, self.size), dtype=int) if cm is None else np.array(cm, dtype=int)
        if self.cm.shape != (self.size, self.size):
            raise ValueError("the connectivity matrix does not match the TPM")
        self.labels = tuple(labels) if labels is not None else tuple(str(i) for i in self.indices)
        self._purviews = {}

    def potential_purviews(self, direction, mechanism):
        key = (direction, mechanism)
        if key not in self._purviews:
            self._purviews[key] = [p for p in powerset(self.indices)
                                   if not block_reducible(self.cm, *ordered(direction, mechanism, p))]
        return self._purviews[key]


def marginalize_out(tpm, indices):
    """Average uniformly over the given dimensions, keeping them as singletons (PyPhi's marginalize_out)."""
    indices = tuple(indices)
    return tpm.sum(indices, keepdims=True) / (np.array(tpm.shape)[list(indices)].prod())


def condition(tpm, conditions):
    """Fix the given dimensions at the given states, keeping singletons (PyPhi's condition_tpm)."""
    index = [[slice(None)]] * (tpm.ndim - 1)
    for i, s in conditions.items():
        if tpm.shape[i] != 1:
            index[i] = [s, np.newaxis]
    return tpm[tuple(itertools.chain.from_iterable(index))]


def tpm_indices(tpm):
    return tuple(np.where(np.array(tpm.shape[:-1]) == 2)[0])


def backward_tpm(forward, state, system):
    """PyPhi's tpm.backward_tpm."""
    n = forward.shape[-1]
    system = tuple(sorted(system))
    background = tuple(sorted(set(range(n)) - set(system)))
    probabilities = np.empty(forward.shape)
    for i in range(n):
        probabilities[..., i] = forward[..., i] if state[i] else (1 - forward[..., i])
    current = probabilities.prod(axis=-1, keepdims=True)
    given_background = current.sum(axis=system, keepdims=True)
    normalization = np.sum(current)
    if normalization == 0.0:
        raise Unreachable(state)
    return (forward * given_background / normalization).sum(axis=background, keepdims=True)


def repertoire_shape(n, purview):
    return [2 if i in purview else 1 for i in range(n)]


class Node:
    def __init__(self, cause_tpm, effect_tpm, cm, index, state):
        self.index = index
        self.state = state
        self.inputs = frozenset(i for i in range(cm.shape[0]) if cm[i][index])
        cause_on = marginalize_out(cause_tpm[..., index], set(tpm_indices(cause_tpm)) - self.inputs)
        effect_on = marginalize_out(effect_tpm[..., index], set(tpm_indices(effect_tpm)) - self.inputs)
        self.cause_tpm = np.stack([1 - cause_on, cause_on], axis=-1)
        self.effect_tpm = np.stack([1 - effect_on, effect_on], axis=-1)


# ---------------------------------------------------------------- results

class RIA:
    """A repertoire irreducibility analysis: phi of a mechanism over a purview in one direction, for one state."""

    def __init__(self, phi, direction, mechanism, purview, state, partition=None):
        self.phi = float(phi)
        self.direction = direction
        self.mechanism = mechanism
        self.purview = purview
        self.state = state                      # the specified purview state (a tuple), or None
        self.partition = partition
        cut = num_connections_cut(partition) if partition is not None else 0
        self.normalized_phi = self.phi * (1 / cut if cut else 1)
        self.state_ties = (self,)
        self.purview_ties = (self,)

    def units(self):
        return frozenset(zip(self.purview, self.state)) if self.state is not None else frozenset()

    def congruent(self, system_state):
        ours = dict(zip(self.purview, self.state or ()))
        theirs = dict(zip(system_state.purview, system_state.state))
        return all(ours[k] == theirs[k] for k in set(ours) & set(theirs))


class StateSpec:
    def __init__(self, direction, purview, state, ii):
        self.direction, self.purview, self.state, self.ii = direction, purview, state, float(ii)


def num_connections_cut(partition):
    sizes = [len(z) for _, z in partition]
    return sum(len(m) * (sum(sizes) - sizes[i]) for i, (m, _) in enumerate(partition))


def all_partitions(mechanism, purview):
    """PyPhi's PARTITION_TYPE ALL: (mechanism part, purview part) lists."""
    for mechanism_partition in set_partitions(list(mechanism)):
        mechanism_partition = mechanism_partition + [[]]
        n_mech = len(mechanism_partition)
        for n_parts in range(1, min(len(purview), n_mech) + 1):
            for purview_partition in k_partitions(list(purview), n_parts):
                blocks = [tuple(b) for b in purview_partition] + [()] * (n_mech - n_parts)
                for perm in distinct_permutations(blocks):
                    parts = [(tuple(m), tuple(z)) for m, z in zip(mechanism_partition, perm)]
                    if parts[0][0] == tuple(mechanism) and parts[0][1]:
                        continue
                    yield parts


def system_cut_matrices(k):
    """SET_UNI/BI over k units: the distinct cut matrices of every non-trivial set partition with a direction per part,
    in PyPhi's order; a single unit has only the complete partition (its self-loop cut)."""
    if k == 1:
        return [np.ones((1, 1), dtype=int)]
    out, seen = [], set()
    units = set(range(k))
    for partition in itertools.islice(set_partitions(sorted(units)), 1, None):
        for directions in itertools.product((CAUSE, EFFECT, "bidirectional"), repeat=len(partition)):
            m = np.zeros((k, k), dtype=int)
            for part, d in zip(partition, directions):
                nonpart = sorted(units - set(part))
                source, target = (nonpart, part) if d == CAUSE else (part, nonpart)
                m[np.ix_(source, target)] = 1
                if d == "bidirectional":
                    m[np.ix_(target, source)] = 1
            key = m.tobytes()
            if key not in seen:
                seen.add(key)
                out.append(m)
    return out


# ---------------------------------------------------------------- a candidate system

class Subsystem:
    def __init__(self, network, state, nodes, cut=None, validate=True):
        self.network = network
        self.n = network.size
        self.state = tuple(int(s) for s in state)
        self.nodes = tuple(sorted(set(nodes)))
        self.cut = cut
        background = [i for i in network.indices if i not in self.nodes]
        self.effect_tpm = condition(network.tpm, {i: self.state[i] for i in background})
        if validate:
            test = self.effect_tpm[..., list(self.nodes)] - np.array([self.state[i] for i in self.nodes])
            if not np.any(np.logical_and(-1 < test, test < 1).all(-1)):
                raise Unreachable(self.state)
        self.cause_tpm = backward_tpm(network.tpm, self.state, self.nodes)
        cm = network.cm.copy()
        if cut is not None:
            full = np.zeros((self.n, self.n), dtype=int)
            full[np.ix_(self.nodes, self.nodes)] = cut
            cm = cm * np.logical_not(full).astype(int)
        self.cm = cm
        self.node = {i: Node(self.cause_tpm, self.effect_tpm, cm, i, self.state[i]) for i in self.nodes}
        self._cache = {}

    def apply_cut(self, cut):
        return Subsystem(self.network, self.state, self.nodes, cut=cut, validate=False)

    # ---- repertoires

    def _single_cause(self, m, purview):
        node = self.node[m]
        return marginalize_out(node.cause_tpm[..., node.state], node.inputs - purview)

    def cause_repertoire(self, mechanism, purview):
        if not purview:
            return np.array([1.0])
        if not mechanism:
            return np.ones(repertoire_shape(self.n, purview)) / (2 ** len(purview))
        key = ("cr", mechanism, purview)
        if key not in self._cache:
            fp = frozenset(purview)
            joint = np.ones(repertoire_shape(self.n, purview))
            joint *= functools.reduce(np.multiply, [self._single_cause(m, fp) for m in mechanism])
            total = joint.sum()
            self._cache[key] = joint if total == 0 else joint / total
        return self._cache[key]

    def _single_effect(self, conditions, p, direction):
        node = self.node[p]
        tpm = node.cause_tpm if direction == CAUSE else node.effect_tpm
        tpm = condition(tpm, conditions)
        tpm = marginalize_out(tpm, node.inputs - set(conditions))
        return tpm.reshape(repertoire_shape(self.n, (p,)))

    def effect_repertoire(self, mechanism, purview, mechanism_state=None, direction=EFFECT):
        if not purview:
            return np.array([1.0])
        if mechanism_state is None:
            mechanism_state = tuple(self.state[m] for m in mechanism)
        key = ("er", mechanism, purview, tuple(mechanism_state), direction)
        if key not in self._cache:
            conditions = dict(zip(mechanism, mechanism_state))
            joint = np.ones(repertoire_shape(self.n, purview))
            self._cache[key] = joint * functools.reduce(
                np.multiply, [self._single_effect(conditions, p, direction) for p in purview])
        return self._cache[key]

    def repertoire(self, direction, mechanism, purview):
        if direction == CAUSE:
            return self.cause_repertoire(mechanism, purview)
        return self.effect_repertoire(mechanism, purview)

    def forward_probability(self, direction, mechanism, purview, purview_state):
        if direction == EFFECT:
            return self.effect_repertoire(mechanism, purview).squeeze()[tuple(purview_state)]
        mechanism_state = tuple(self.state[m] for m in mechanism)
        er = self.effect_repertoire(purview, mechanism, mechanism_state=tuple(purview_state), direction=CAUSE)
        return er.squeeze()[mechanism_state]

    def forward_cause_repertoire(self, mechanism, purview, purview_state=None):
        mechanism_state = tuple(self.state[m] for m in mechanism)
        if purview:
            repertoire = np.empty([2] * len(purview))
            states = list(all_states(len(purview))) if purview_state is None else [tuple(purview_state)]
        else:
            repertoire = np.array([1])
            states = [()]
        for s in states:
            er = self.effect_repertoire(purview, mechanism, mechanism_state=s, direction=CAUSE)
            repertoire[s] = er.squeeze()[mechanism_state]
        return repertoire.reshape(repertoire_shape(self.n, purview))

    def forward_repertoire(self, direction, mechanism, purview, purview_state=None):
        if direction == CAUSE:
            return self.forward_cause_repertoire(mechanism, purview, purview_state)
        return self.effect_repertoire(mechanism, purview)

    def unconstrained_forward_repertoire(self, direction, mechanism, purview):
        if direction == EFFECT:
            return np.stack([self.effect_repertoire(mechanism, purview, mechanism_state=s)
                             for s in all_states(len(mechanism))]).mean(axis=0)
        mean = self.forward_cause_repertoire(mechanism, purview, None).mean()
        repertoire = np.empty(repertoire_shape(self.n, purview))
        repertoire.fill(mean)
        return repertoire

    # ---- information

    def intrinsic_information(self, direction, mechanism, purview):
        """[(state, ii)] of the states of maximal intrinsic information, in little-endian order."""
        selectivity = self.repertoire(direction, mechanism, purview)
        values = gid(self.forward_repertoire(direction, mechanism, purview, None),
                     self.unconstrained_forward_repertoire(direction, mechanism, purview), selectivity).squeeze()
        info = {s: values[s] for s in all_states(len(purview))}
        best = max(info.values())
        return [(s, v) for s, v in info.items() if v == best]

    def evaluate_partition(self, direction, mechanism, purview, partition, state, repertoire=None):
        if repertoire is None:
            repertoire = self.repertoire(direction, mechanism, purview)
        selectivity = repertoire.squeeze()[tuple(state)]
        forward = self.forward_probability(direction, mechanism, purview, state)
        whole = tuple(sorted(itertools.chain.from_iterable(z for _, z in partition)))
        parts = [self.forward_probability(direction, m, z, tuple(state[whole.index(u)] for u in z))
                 for m, z in partition]
        partitioned = np.prod(parts)
        return RIA(gid(forward, partitioned, selectivity), direction, mechanism, purview, tuple(state), partition)

    def _mip_single_state(self, direction, mechanism, purview, state, repertoire):
        candidates = []
        for partition in all_partitions(mechanism, purview):
            ria = self.evaluate_partition(direction, mechanism, purview, partition, state, repertoire)
            candidates.append(ria)
            if not positive(ria.phi):
                break
        if not candidates:
            return RIA(0.0, direction, mechanism, purview, tuple(state))
        best = candidates[0]
        for c in candidates[1:]:
            if lt(c.normalized_phi, best.normalized_phi) or (
                    eq(c.normalized_phi, best.normalized_phi) and -c.phi < -best.phi):
                best = c
        return best

    def find_mip(self, direction, mechanism, purview):
        if not purview:
            return RIA(0.0, direction, mechanism, purview, None)
        repertoire = self.repertoire(direction, mechanism, purview)
        if direction == CAUSE and np.all(repertoire == 0):
            return RIA(0.0, direction, mechanism, purview, None)
        mips = [self._mip_single_state(direction, mechanism, purview, s, repertoire)
                for s, _ in self.intrinsic_information(direction, mechanism, purview)]
        best = mips[0]
        for m in mips[1:]:
            if m.phi > best.phi and not eq(m.phi, best.phi):
                best = m
        ties = tuple(m for m in mips if eq(m.phi, best.phi))
        for t in ties:
            t.state_ties = ties
        return ties[0]

    def potential_purviews(self, direction, mechanism):
        candidates = set(self.network.potential_purviews(direction, mechanism))
        inside = [p for p in candidates if set(p) <= set(self.nodes)]
        return [p for p in inside if not block_reducible(self.cm, *ordered(direction, mechanism, p))]

    def find_mice(self, direction, mechanism):
        purviews = self.potential_purviews(direction, mechanism)
        if not purviews:
            return RIA(0.0, direction, mechanism, (), None)
        mice = [self.find_mip(direction, mechanism, p) for p in purviews]
        best = mice[0]
        for m in mice[1:]:
            if m.phi > best.phi and not eq(m.phi, best.phi):
                best = m
        ties = tuple(m for m in mice if eq(m.phi, best.phi))
        for t in ties:
            t.purview_ties = ties
        return ties[0]

    # ---- the system

    def system_state(self):
        out = {}
        for d in BOTH:
            s, ii = self.intrinsic_information(d, self.nodes, self.nodes)[0]
            out[d] = StateSpec(d, self.nodes, s, ii)
        return out

    def sia(self):
        """(phi_s, the system's specified states or None, the MIP's cut matrix or None)."""
        if not strongly_connected(self.cm, self.nodes):
            return 0.0, None, None
        if len(self.nodes) == 1 and not self.cm[self.nodes[0]][self.nodes[0]]:
            return 0.0, None, None
        states = self.system_state()
        if any(states[d].ii <= 0 or eq(states[d].ii, 0) for d in BOTH):
            return 0.0, states, None
        best = None
        for cut in system_cut_matrices(len(self.nodes)):
            cut_system = self.apply_cut(cut)
            values = []
            for d in BOTH:
                s = states[d].state
                partitioned = cut_system.forward_repertoire(d, self.nodes, self.nodes, s).squeeze()[s]
                selectivity = self.repertoire(d, self.nodes, self.nodes).squeeze()[s]
                forward = self.forward_probability(d, self.nodes, self.nodes, s)
                values.append(float(gid(forward, partitioned, selectivity)))
            phi = values[0] if not lt(values[1], values[0]) else values[1]
            normalized = phi * (1 / np.sum(cut)) if len(self.nodes) > 1 else phi / len(self.nodes)
            candidate = (normalized, phi, cut)
            if best is None or lt(normalized, best[0]) or (eq(normalized, best[0]) and -phi < -best[1]):
                best = candidate
            if not positive(phi):
                break
        return best[1], states, best[2]

    def distinctions(self):
        out = []
        for mechanism in powerset(self.nodes, nonempty=True):
            cause = self.find_mice(CAUSE, mechanism)
            effect = self.find_mice(EFFECT, mechanism)
            phi = cause.phi if not lt(effect.phi, cause.phi) else effect.phi
            if positive(phi):
                out.append(Distinction(mechanism, cause, effect))
        return out

    def phi_structure(self, states=None):
        if states is None:
            states = self.system_state()
        kept = []
        for d in self.distinctions():
            chosen = []
            for direction, mice in ((CAUSE, d.cause), (EFFECT, d.effect)):
                options = list(mice.state_ties) + list(mice.purview_ties)
                chosen.append(next((m for m in options if m.congruent(states[direction])), None))
            if chosen[0] is not None and chosen[1] is not None:
                kept.append(Distinction(d.mechanism, chosen[0], chosen[1]))
        kept.sort(key=lambda d: (len(d.mechanism), d.mechanism))
        return Structure(kept)


class Distinction:
    def __init__(self, mechanism, cause, effect):
        self.mechanism, self.cause, self.effect = mechanism, cause, effect
        self.phi = cause.phi if not lt(effect.phi, cause.phi) else effect.phi
        self.union = cause.units() | effect.units()


class Structure:
    """The congruent distinctions and their concrete relations."""

    def __init__(self, distinctions):
        self.distinctions = distinctions
        self.relations = []          # (tuple of distinction indices, phi_r)
        for i, d in enumerate(distinctions):
            shared = d.cause.units() & d.effect.units()
            phi = len(shared) * (d.phi / len(d.union)) if d.union else 0.0
            if positive(phi):
                self.relations.append(((i,), phi))
        k = len(distinctions)
        for size in range(2, k + 1):
            for combo in itertools.combinations(range(k), size):
                overlap = set.intersection(*(set(distinctions[i].union) for i in combo))
                if overlap:
                    phi = len(overlap) * min(distinctions[i].phi / len(distinctions[i].union) for i in combo)
                    self.relations.append((combo, phi))
        self.sum_phi_distinctions = sum(d.phi for d in distinctions)
        self.sum_phi_relations = sum(phi for _, phi in self.relations)
        self.big_phi = self.sum_phi_distinctions + self.sum_phi_relations


# ---------------------------------------------------------------- complexes

class _ByPhi:
    def __init__(self, item):
        self.item = item

    def __lt__(self, other):
        return lt(self.item[0], other.item[0])


def irreducible_systems(network, state):
    """[(phi_s, nodes, specified states)] for every reachable candidate with positive phi_s, in PyPhi's order."""
    out = []
    for nodes in powerset(network.indices, nonempty=True, reverse=True):
        try:
            system = Subsystem(network, state, nodes)
        except Unreachable:
            continue
        phi, states, _ = system.sia()
        if positive(phi):
            out.append((phi, system.nodes, states))
    return out


def condensed(network, state):
    """The maximal non-overlapping complexes, as the authors' findlay2024a.condensed takes them."""
    result, covered = [], set()
    ranked = [w.item for w in reversed(sorted(_ByPhi(x) for x in irreducible_systems(network, state)))]
    for phi, nodes, states in ranked:
        if not covered & set(nodes):
            result.append((phi, nodes, states))
            covered |= set(nodes)
    return result


def analyse(network, state, nodes):
    """phi_s and the Phi-structure of one candidate system, as the authors' get_sia_and_ces gives them."""
    system = Subsystem(network, state, nodes)
    phi, states, _ = system.sia()
    if not positive(phi):
        return {"phi_s": phi, "big_phi": 0.0, "distinctions": 0, "relations": 0, "mechanisms": []}
    structure = system.phi_structure(states)
    return {"phi_s": phi, "big_phi": structure.big_phi, "distinctions": len(structure.distinctions),
            "relations": len(structure.relations),
            "mechanisms": [d.mechanism for d in structure.distinctions], "structure": structure}
