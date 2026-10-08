"""IIT 3.0 as PyPhi 1.2 computes it, written afresh for iit/check.py, with every tie kept.

Standard library only; the transport problems (earth mover's distances) go to flow.c through ctypes. The rules are
in check.py's docstring; this module implements them. Conventions follow PyPhi 1.2.0 (the base of the authors'
fork): a network's state index is little-endian (node 0 is the lowest bit); a repertoire over a purview is a list
indexed the same way over the purview's nodes in ascending order; the connectivity matrix is all ones (PyPhi's
default when none is given); a cut A -> B severs every connection from A to B, so each node of B is averaged over
the states of A.
"""

import ctypes
import itertools

CAUSE, EFFECT = 0, 1
PRECISION = 6
TOL = 1e-12


def rnd(x):
    return round(x, PRECISION)


# ---------------------------------------------------------------- transport

class Flow:
    """Earth mover's distances: exact (mode 0), or with pyemd 0.5.1's arithmetic, as PyPhi 1.2 has them (mode 1)."""

    def __init__(self, path, mode=0):
        lib = ctypes.CDLL(path)
        d = ctypes.POINTER(ctypes.c_double)
        lib.transport.restype = ctypes.c_double
        lib.transport.argtypes = [ctypes.c_int, ctypes.c_int, d, d, d]
        lib.emd_pyemd.restype = ctypes.c_double
        lib.emd_pyemd.argtypes = [ctypes.c_int, d, d, d]
        i = ctypes.POINTER(ctypes.c_int)
        i64 = ctypes.POINTER(ctypes.c_int64)
        lib.enumerate_cut.restype = ctypes.c_int
        lib.enumerate_cut.argtypes = [ctypes.c_int, i, i, i, i, d, d, i, d, d, i, d, ctypes.c_int,
                                      ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64, d, d, i64, i64, i64,
                                      ctypes.c_int]
        self.lib = lib
        self.mode = mode
        self.hamming = {}

    def hamming_matrix(self, k):
        if k not in self.hamming:
            n = 2 ** k
            self.hamming[k] = (ctypes.c_double * (n * n))(*[float(bin(s ^ t).count("1"))
                                                           for s in range(n) for t in range(n)])
        return self.hamming[k]

    def emd_pyemd(self, p, q, cost):
        n = len(p)
        return self.lib.emd_pyemd(n, (ctypes.c_double * n)(*p), (ctypes.c_double * n)(*q),
                                  (ctypes.c_double * (n * n))(*[c for row in cost for c in row]))

    def transport(self, a, b, cost):
        n1, n2 = len(a), len(b)
        A = (ctypes.c_double * n1)(*a)
        B = (ctypes.c_double * n2)(*b)
        C = (ctypes.c_double * (n1 * n2))(*[c for row in cost for c in row])
        return self.lib.transport(n1, n2, A, B, C)

    def hamming_emd(self, p, q):
        """EMD between two distributions over the same k binary nodes, Hamming ground distance."""
        if self.mode == 1:
            n = len(p)
            k = n.bit_length() - 1
            return self.lib.emd_pyemd(n, (ctypes.c_double * n)(*p), (ctypes.c_double * n)(*q),
                                      self.hamming_matrix(k))
        sup, dem = [], []
        for s, (x, y) in enumerate(zip(p, q)):
            d = x - y
            if d > TOL:
                sup.append((s, d))
            elif d < -TOL:
                dem.append((s, -d))
        if not sup or not dem:
            return 0.0
        a = [m for _, m in sup]
        b = [m for _, m in dem]
        ta, tb = sum(a), sum(b)
        if abs(ta - tb) > 1e-9:
            raise ValueError("unbalanced distributions")
        b = [m * ta / tb for m in b]
        cost = [[bin(s ^ t).count("1") for t, _ in dem] for s, _ in sup]
        return self.transport(a, b, cost)


# ---------------------------------------------------------------- partitions, as PyPhi orders them

def bipartition_indices(n):
    out = []
    for i in range(2 ** (n - 1)) if n > 0 else []:
        part = [[], []]
        for k in range(n):
            part[(i >> k) & 1].append(k)
        out.append((tuple(part[1]), tuple(part[0])))
    return out


def bipartition(seq):
    return [(tuple(seq[i] for i in a), tuple(seq[j] for j in b)) for a, b in bipartition_indices(len(seq))]


def directed_bipartition(seq, nontrivial=False):
    idx = bipartition_indices(len(seq))
    idx = idx + [x[::-1] for x in idx[::-1]]
    out = [(tuple(seq[i] for i in a), tuple(seq[j] for j in b)) for a, b in idx]
    return out[1:-1] if nontrivial else out


def mip_bipartitions(mechanism, purview):
    for n in bipartition(mechanism):
        for d in directed_bipartition(purview):
            if (n[0] or d[0]) and (n[1] or d[1]):
                yield ((n[0], d[0]), (n[1], d[1]))


def powerset(seq, nonempty=True):
    seq = list(seq)
    for r in range(1 if nonempty else 0, len(seq) + 1):
        yield from itertools.combinations(seq, r)


# ---------------------------------------------------------------- connectivity, as PyPhi tests it

def block_cm(cm):
    rows, cols = len(cm), len(cm[0])
    if any(sum(r) == 0 for r in cm):
        return True
    if all(sum(r) == 1 for r in cm):
        return True
    outputs = list(range(cols))

    def outputs_of(nodes):
        return [j for j in range(cols) if any(cm[i][j] for i in nodes)]

    def inputs_to(nodes):
        return [i for i in range(rows) if any(cm[i][j] for j in nodes)]
    sums = [sum(r) for r in cm]
    sources = [sums.index(max(sums))]
    sinks = outputs_of(sources)
    sink_inputs = inputs_to(sinks)
    while True:
        if sink_inputs == sources:
            return True
        sources = sink_inputs
        sinks = outputs_of(sources)
        sink_inputs = inputs_to(sinks)
        if sinks == outputs:
            return False


def block_reducible(cm, nodes1, nodes2):
    if not nodes1 or not nodes2:
        return True
    sub = [[cm[i][j] for j in nodes2] for i in nodes1]
    if not all(any(sub[i][j] for i in range(len(nodes1))) for j in range(len(nodes2))):
        return True
    if not all(any(row) for row in sub):
        return True
    if len(nodes1) > 1 and len(nodes2) > 1:
        return block_cm(sub)
    return False


# ---------------------------------------------------------------- a system and its (cut) subsystems

class Network:
    """tpm_on[s][j]: the probability that node j is on after network state s (little-endian index)."""

    def __init__(self, tpm_on):
        self.tpm_on = tpm_on
        self.n = len(tpm_on[0])
        assert len(tpm_on) == 2 ** self.n


class Subsystem:
    def __init__(self, network, state, nodes, cut=None, tables=None, cache=None):
        """nodes: network indices, ascending; cut: (A, B) as positions within nodes, or None."""
        self.net, self.state, self.nodes = network, tuple(state), tuple(nodes)
        self.k = len(nodes)
        self.cut = cut
        k, n = self.k, network.n
        ext = [i for i in range(n) if i not in nodes]
        base = sum(state[i] << i for i in ext)
        self.cur = tuple(state[i] for i in nodes)
        if tables is None:
            tables = {}
            for p, j in enumerate(nodes):
                col = []
                for x in range(2 ** k):
                    s = base
                    for t, i in enumerate(nodes):
                        if (x >> t) & 1:
                            s |= 1 << i
                    col.append(float(network.tpm_on[s][j]))
                tables[p] = col
        self.uncut = tables
        self.tables = dict(tables)
        self.cm = [[1] * k for _ in range(k)]
        if cut is not None:
            A, B = cut
            for a in A:
                for b in B:
                    self.cm[a][b] = 0
            for b in B:
                self.tables[b] = marginalise(tables[b], A, k)
        self.uc_effect = {p: sum(self.tables[p]) / 2 ** k for p in range(k)}
        self.cache = {} if cache is None else cache

    def cut_matrix(self, a, b):
        if self.cut is None:
            return False
        A, B = self.cut
        return a in A and b in B

    def splits(self, mechanism):
        return any(self.cut_matrix(a, b) for a in mechanism for b in mechanism)

    # repertoires -------------------------------------------------------
    def cause_repertoire(self, mechanism, purview):
        k = self.k
        if not purview:
            return [1.0]
        size = 2 ** len(purview)
        if not mechanism:
            return [1.0 / size] * size
        joint = [1.0] * size
        for m in mechanism:
            col = self.tables[m]
            on = self.cur[m]
            acc = [0.0] * size
            for x in range(2 ** k):
                p = 0
                for t, q in enumerate(purview):
                    if (x >> q) & 1:
                        p |= 1 << t
                acc[p] += col[x] if on else 1.0 - col[x]
            f = 2 ** (k - len(purview))
            for p in range(size):
                joint[p] *= acc[p] / f
        s = sum(joint)
        return [v / s for v in joint] if s != 0 else joint

    def effect_marginals(self, mechanism, purview):
        """P(node on) for each purview node, given the mechanism's current state, the rest uniform."""
        k = self.k
        out = []
        for q in purview:
            col = self.tables[q]
            tot, cnt = 0.0, 0
            for x in range(2 ** k):
                if all(((x >> m) & 1) == self.cur[m] for m in mechanism):
                    tot += col[x]
                    cnt += 1
            out.append(tot / cnt)
        return out

    @staticmethod
    def product(marginals):
        size = 2 ** len(marginals)
        rep = []
        for s in range(size):
            v = 1.0
            for t, g in enumerate(marginals):
                v *= g if (s >> t) & 1 else 1.0 - g
            rep.append(v)
        return rep

    def effect_repertoire(self, mechanism, purview):
        if not purview:
            return [1.0]
        return self.product(self.effect_marginals(mechanism, purview))

    # small phi ---------------------------------------------------------
    def find_mip(self, flow, direction, mechanism, purview):
        """(phi, repertoire) of the minimum information partition."""
        key = (direction, mechanism, purview, tuple(self.cur[m] for m in mechanism),
               tuple(tuple(self.tables[m]) for m in (mechanism if direction == CAUSE else purview)))
        if key in self.cache:
            return self.cache[key]
        if direction == CAUSE:
            rep = self.cause_repertoire(mechanism, purview)
            if all(v == 0 for v in rep):
                res = (0.0, rep)
            else:
                best = float("inf")
                for (m1, p1), (m2, p2) in mip_bipartitions(mechanism, purview):
                    r1 = self.cause_repertoire(m1, p1)
                    r2 = self.cause_repertoire(m2, p2)
                    part = []
                    for s in range(2 ** len(purview)):
                        i1 = sum(((s >> purview.index(q)) & 1) << t for t, q in enumerate(p1))
                        i2 = sum(((s >> purview.index(q)) & 1) << t for t, q in enumerate(p2))
                        part.append(r1[i1] * r2[i2])
                    phi = rnd(rnd(flow.hamming_emd(rep, part)))
                    if phi == 0:
                        best = 0.0
                        break
                    if phi < best:
                        best = phi
                res = (best, rep)
        else:
            g = self.effect_marginals(mechanism, purview)
            rep = self.product(g)
            best = float("inf")
            for (m1, p1), (m2, p2) in mip_bipartitions(mechanism, purview):
                g1 = dict(zip(p1, self.effect_marginals(m1, p1)))
                g2 = dict(zip(p2, self.effect_marginals(m2, p2)))
                gp = [g1[q] if q in g1 else g2[q] for q in purview]
                phi = rnd(rnd(sum(abs((1 - a) - (1 - b)) for a, b in zip(g, gp))))
                if phi == 0:
                    best = 0.0
                    break
                if phi < best:
                    best = phi
            res = (best, rep)
        self.cache[key] = res
        return res

    def potential_purviews(self, direction, mechanism):
        out = []
        for p in powerset(range(self.k)):
            frm, to = (p, mechanism) if direction == CAUSE else (mechanism, p)
            if not block_reducible(self.cm, frm, to):
                out.append(p)
        return out

    def mice(self, flow, direction, mechanism):
        """All (phi, purview, repertoire) in purview order, and PyPhi's pick and the tied ones."""
        cands = []
        for p in self.potential_purviews(direction, mechanism):
            phi, rep = self.find_mip(flow, direction, mechanism, p)
            cands.append((phi, p, rep))
        if not cands:
            return None, []
        pick = cands[0]
        for c in cands[1:]:
            if (c[0], len(c[1])) > (pick[0], len(pick[1])):
                pick = c
        ties = [c for c in cands if c[0] == pick[0]] if pick[0] > 0 else [pick]
        return pick, ties

    def null_effect(self, purview):
        return self.product([self.uc_effect[q] for q in purview]) if purview else [1.0]


def marginalise(col, positions, k):
    out = []
    for x in range(2 ** k):
        tot = 0.0
        cnt = 0
        for bits in range(2 ** len(positions)):
            y = x
            for t, a in enumerate(positions):
                y = (y | (1 << a)) if (bits >> t) & 1 else (y & ~(1 << a))
            tot += col[y]
            cnt += 1
        out.append(tot / cnt)
    return out


# ---------------------------------------------------------------- concepts and their distances

class Concept:
    __slots__ = ("mechanism", "phi", "cp", "cr", "ep", "er", "sub", "canon")

    def __init__(self, mechanism, cause, effect, sub):
        self.mechanism = mechanism
        self.phi = min(cause[0], effect[0])
        self.cp, self.cr = cause[1], cause[2]
        self.ep, self.er = effect[1], effect[2]
        self.sub = sub
        self.canon = None

    def signature(self):
        return (self.mechanism, self.phi, self.cp, tuple(self.cr), self.ep, tuple(self.er))


def expand(rep, purview, union, fill):
    """rep over purview, times fill (a repertoire over union - purview) over union, normalised."""
    rest = tuple(q for q in union if q not in purview)
    out = []
    for s in range(2 ** len(union)):
        i1 = sum(((s >> union.index(q)) & 1) << t for t, q in enumerate(purview))
        i2 = sum(((s >> union.index(q)) & 1) << t for t, q in enumerate(rest))
        out.append(rep[i1] * fill[i2])
    tot = sum(out)
    return [v / tot for v in out] if tot != 0 else out


def concept_distance(flow, c1, c2):
    cu = tuple(sorted(set(c1.cp) | set(c2.cp)))
    eu = tuple(sorted(set(c1.ep) | set(c2.ep)))

    def side(c, cause):
        if cause:
            rest = tuple(q for q in cu if q not in c.cp)
            return expand(c.cr, c.cp, cu, [1.0 / 2 ** len(rest)] * 2 ** len(rest))
        rest = tuple(q for q in eu if q not in c.ep)
        return expand(c.er, c.ep, eu, c.sub.null_effect(rest))
    return flow.hamming_emd(side(c1, True), side(c2, True)) + flow.hamming_emd(side(c1, False), side(c2, False))


def null_distance(flow, c):
    k = len(c.cp)
    cause = flow.hamming_emd(c.cr, [1.0 / 2 ** k] * 2 ** k)
    effect = flow.hamming_emd(c.er, c.sub.null_effect(c.ep))
    return cause + effect


def ces_distance(flow, C1, C2):
    """PyPhi's ces_distance, unrounded, for two lists of concepts."""
    only1 = [c for c in C1 if not any(c.canon == d.canon for d in C2)]
    only2 = [c for c in C2 if not any(c.canon == d.canon for d in C1)]
    if not only1 or not only2:
        big = only1 if len(C1) >= len(C2) else only2
        if len(C2) > len(C1):
            big = only2
        return sum(c.phi * null_distance(flow, c) for c in big)
    a = [c.phi for c in only1]
    d0 = sum(a) - sum(c.phi for c in only2)
    cross = [[concept_distance(flow, c, d) for d in only2] for c in only1]
    null1 = [null_distance(flow, c) for c in only1]
    if flow.mode == 1:
        n1, n2 = len(only1), len(only2)
        N = n1 + n2 + 1
        top = max(max(r) for r in cross) + 1
        M = [[top] * N for _ in range(N)]
        for i in range(n1):
            for j in range(n2):
                M[i][n1 + j] = M[n1 + j][i] = cross[i][j]
        nulls = null1 + [null_distance(flow, d) for d in only2]
        for x in range(N - 1):
            M[N - 1][x] = M[x][N - 1] = nulls[x]
        M[N - 1][N - 1] = 0.0
        P = a + [0.0] * (n2 + 1)
        Q = [0.0] * n1 + [d.phi for d in only2] + [d0]
        return flow.emd_pyemd(P, Q, M)
    if d0 < -1e-12:
        raise ValueError("partitioned structure holds more phi")
    b = [c.phi for c in only2] + [max(d0, 0.0)]
    cost = [row + [nl] for row, nl in zip(cross, null1)]
    return flow.transport(a, b, cost)
