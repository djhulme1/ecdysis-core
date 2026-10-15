#!/usr/bin/env python3
"""Albantakis & Tononi's causal composition (2019): every reversible system of three binary elements has the same,
maximal global dynamics, yet their subsets specify different intrinsic information, even between a system and its
time reverse. Computed as the paper's Section 5 defines it, for all 40,320 reversible systems.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:2703adca8c12b54a) is from L. Albantakis and
G. Tononi, "Causal Composition: Structural Differences among Dynamically Equivalent Systems", Entropy 21(10), 989
(2019; doi:10.3390/e21100989; CC BY 4.0; PMC7514321), its abstract: "We show that the global dynamical and
information-theoretic capacities of reversible systems can be maximal even though they may differ, quantitatively and
qualitatively, in the information that their various subsets specify about each other (intrinsic information). This
can be the case even for a system and its time-reversed equivalent." The test, as registered: see TEST below. No data
of record: the systems are defined by construction (every permutation of the eight states of three binary elements),
so the receipt is a reproduction.

The paper's definitions, read from its JATS full text (Europe PMC) before this module was written, and followed here:
- Section 5.1: a system of n = 3 binary elements, each with p(V_i,t = 1 | v_t-1); deterministic systems are
  conditionally independent across elements. A state is an integer 0..7 with element i its bit i (A = bit 0, so the
  paper's ABC = (0,1,1) is state 6), as PyPhi numbers states.
- Section 5.2, Equation 5: EI(S) = the mean over the eight prior states of D_KL(p(V_t | v_t-1) || p(V_t)), base 2.
- Section 5.3: the effect repertoire of a subset X in state x over Z_t+1 is the product over Z's elements of the mean
  over the states of W = V \\ X of p(Z_i,t+1 | x, w) (Equation 8); the cause repertoire over Z_t-1 is the normalised
  product over X's elements of pi(Z_t-1 | x_i) = sum over the states y of V \\ Z of p(x_i | z, y) / sum over all v of
  p(x_i | v) (Equations 9 and 10); the unconstrained repertoires are the uniform distribution (cause, Equation 11) and
  the product of each element's mean (effect, Equation 12).
- Section 5.4: phi_C/E(x_t) = D_KL(pi(V_t-1/t+1 | x_t) || pi^MIP), over the full purview V (Equation 15, as the paper
  states DKL makes it maximal), the MIP the partition psi of Equation 13 that makes the least difference; the
  partitioned repertoire is the product of the parts' repertoires and the unconstrained repertoire of the purview
  elements no part constrains (Equation 14). The permissible partitions are PyPhi's PARTITION_TYPE 'ALL' (Section 5.7):
  every set partition of the subset with an empty part added, the purview split into as many parts as there are
  subset parts or fewer, the purview parts assigned to the subset parts in every distinct way, and the one-part
  partition of the subset allowed only with an empty purview (so a single element's phi is its information against
  the unconstrained repertoire, as Section 5.4 says).
- Section 5.5: sum phi_C + sum phi_E over all seven subsets; for each of the six unidirectional cuts X -/-> S \\ X (the
  inputs from X to each element outside it replaced by uniform noise, as PyPhi cuts), every subset with phi > 0 in the
  intact system is reevaluated in the cut system with its MIP found again, and Phi(v) is the minimum over cuts of the
  smaller of sum (phi_C - phi_C^cut) and sum (phi_E - phi_E^cut) (Equations 1 and 16). Averages are over the eight
  states (Figure 5).
- Section 5.6: a system is reversible when its update is a permutation of the eight states (40,320 of them), ergodic
  reversible (ER) when that permutation is one cycle through all eight (5,040). Section 3.2: a system's time-reversed
  dynamical equivalent is the inverse permutation.

Every rule below was fixed before this module computed any value of the paper's measures for a reversible system or
for Table 1's example. Known before it: the paper's text, its Tables 1 to 3 and the captions of Figures 4 to 7. While
reading, the effect values of the example system MCX's single elements (1.189 and 0.189 bits) and its cause values for
M, C and MC (1.0 bit each) were worked by hand from the definitions, and they agree with Table 1. The measures were
timed beforehand on seed-drawn probabilistic systems (none reversible), no value printed. The first trial in the
reference runner, under a seed of Imago's own, stopped in the first control with a division by zero: MCX is not
reversible, and the control evaluates all eight of its states though Table 1 prints one, so it met states that no
prior state leads to, whose cause repertoires are all zero. Such a repertoire is now left at zero and its phi_C is 0,
as PyPhi's normalize and find_mip make them. Nothing else changed, and since every state of a reversible system is
reachable, no reversible system's values are touched.

The second trial, under another seed of Imago's own, stopped at two controls. The repertoire control enumerated each
purview's states in the opposite order to the module's (itertools.product puts the first element highest), so it
compared two orderings of the same numbers; it now enumerates in the module's order. Table 1's 14 values of phi and
EI = 2.5 came out as printed, but its Phi did not: over the six unidirectional cuts the test uses (Section 5.5's
X -/-> S \\ X), MCX in (0,1,1) has Phi = 1.00, least at MX -/-> C on the effect side (phi_E(M) falls from 1.189 to
0.189), where Table 1 prints 1.02 and the paper says it is found at {MC_t, MCX_t+1}, {X_t, 0} (X's outputs cut, for
MCX the cut X -/-> MC), eliminating phi_E of X, CX and MCX, which the module gives as 1.0188. At 7ece71d the control
was made to check Phi over PyPhi's concept-style system cuts (KCuts of the whole system over the 'ALL' partitions,
each side on its own, the form in which the paper writes its partitions), whose least is 1.0188 at that partition and
whose cause side's least, 2.2263, is Appendix B's 2.23 for MCX's cause side; MCX's Phi over the six cuts went beside
(table1_phi), and so did the concept-style Phi of the first ER match of each Table 2 column (table2_phi_ks).

The third trial, under a third seed of Imago's own, ran to the end with no bug: all four conditions and all five
controls held. Its beside outputs then showed Figure 6's Phi as the six cuts give it for (a), (b) and (c) (0, 0.844
and 0 state-averaged, printed 0, 0.84 and 0), not for (d) (1.208, printed 1.50), and the concept-style cuts
reproducing none of the four (0.343, 0.790, 1.245 and 2.226). So the paper's Phi is not simply theirs either, and the
Table 1 control no longer checks a family's least: it checks the paper's statement at the partition it names (phi_E
of X, CX and MCX eliminated there and nothing else, 1.02 to 0.005), and table1_phi reports MCX's Phi over the six
cuts, at that cut and over the concept-style cuts. These changes came after the controls' and the beside outputs'
values were seen. The test, the measures and every other output are as at 7ece71d. The verdict does not turn on the
cuts: in the third trial's classes, 20,160 of the 40,320 systems differ from their time reverse in sum phi_C + sum
phi_E alone.

1. Systems. The reversible systems are the 40,320 permutations of 0..7; the ER systems those whose cycle from 0
   returns after exactly eight steps. The deterministic element update of a permutation s is p(V_i = 1 | v) = bit i of
   s(v). Under a cut X -/-> S \\ X, each element i outside X has p_cut(V_i = 1 | v) = the mean over the states u of X of
   p(V_i = 1 | v with X set to u); elements in X are unchanged.
2. Measures as above, logarithms to base 2. Values within 1e-9 of zero are zero (phi > 0 means phi > 1e-9); two values
   differ when they are more than 1e-6 apart (PyPhi rounds to six places).
3. Symmetry: relabelling the elements and complementing any of them (48 maps g of the states) leaves every measure
   averaged over states unchanged, and commutes with time reversal. Each system is computed through its class
   representative (the least of g s g^-1 over the 48 maps, compared as tuples), and the classes' values are given to
   every member. A control computes 300 seed-drawn systems directly.
4. The test's four conditions: (1) every reversible system has EI = 3 bits and each element's entropy after a uniform
   perturbation 1 bit (maximal global capacities); (2) among the ER systems, the state-averaged sum phi_C + sum phi_E
   takes more than one value (more than 1e-6 apart); (3) among the ER systems, the counts of subsets with phi > 0 by
   order (one, two or three elements) and side, summed over the states, are not the same for all (a qualitative
   difference in which subsets specify information); (4) some reversible system differs from its time reverse in the
   state-averaged sum phi_C + sum phi_E or Phi. test_passed is 1 if all four hold.
5. Beside, none of it counted: Section 3.2's "more than half of all pairs differ" (the share of the 40,320 systems
   that differ from their time reverse, and of the 20,542 unordered pairs); the ER and reversible sets' ranges and
   means of the two measures and their shares with Phi = 0 (Figure 5); the ER systems whose eight state-(0,1,1) values
   match each column of Table 2 to 0.0015 bits, with their Phi at that state and averaged (Figure 6's 0, 0.84, 0 and
   1.50), and the same four systems' Phi over PyPhi's concept-style cuts; Table 1's MCX's Phi over the six cuts, at
   the cut the paper names and over the concept-style cuts;
   whether the full purview gives the largest phi (Section 5.4's statement) on 200 seed-drawn reversible systems; and
   how many cuts make some sum of differences negative.

Controls (controls_passed counts those that behave as stated; the run stops if any fails): Table 1, the example
system MCX (M the majority of M, C and X; C a copy of M; X the exclusive or of M and C, read from Section 2.1's
statements) in state (0,1,1): its 14 values of phi to 0.001 bits of the printed ones, EI = 2.5 bits, and, at the
partition where the paper finds its Phi ({MC_t, MCX_t+1}, {X_t, 0}: X's outputs cut, here X -/-> MC), phi_E of X,
CX and MCX eliminated and nothing else, together 1.02 bits to 0.005; the repertoires against a direct enumeration of
Equations 8 to 10 on seed-drawn probabilistic systems; the effect side's additive shortcut against the joint relative
entropy on the same systems; the partitions' counts (1, 28 and 146 for subsets of one, two and three elements over
three purview elements) with none repeated; and the symmetry of rule 3 on 300 seed-drawn systems.

What it cannot check: the paper's own scripts (not released) and the PyPhi branch it used (iit-4.0 at b79b7fa, whose
settings Section 5.7 names) are not run; Figure 5's random samples are not drawn; systems of more than three elements.

Writes results/outputs.json and results/detail.json. Run with: python3 iit/at2019.py
"""

import hashlib
import itertools
import json
import math
import multiprocessing
import os
import re
import sys

N = 3
STATES = 1 << N
FULL = STATES - 1
POS = 1e-9
DIFF = 1e-6
SYMMETRY_SAMPLE = 300
PURVIEW_SAMPLE = 200
WORKERS = 2
LIMIT = 200
TEST = ("Refuted if, computed as Section 5 defines it (DKL, PyPhi's ALL partitions, full purviews, Phi over the six "
        "unidirectional cuts, averaged over the eight states), some reversible binary 3-node system has EI below 3 "
        "bits; or the 5,040 ergodic reversible systems all have the same sum phi_C + sum phi_E, or the same counts of "
        "irreducible subsets by order and side; or no reversible system differs from its time reverse (the inverse "
        "permutation) in sum phi_C + sum phi_E or Phi, by more than 1e-6 bits.")
OUTPUTS = ("ei", "er_sum", "er_counts", "time_reverse", "pairs_share", "rev_sum", "rev_phi", "er_phi", "table1_phi",
           "table2", "table2_phi", "table2_phi_ks", "purview", "negative", "classes", "conditions_met",
           "conditions_total", "test_passed", "controls_passed", "controls_total")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- randomness

class Stream:
    def __init__(self, seed, label):
        self.seed, self.label, self.n, self.buf = seed, label, 0, []

    def u(self):
        if not self.buf:
            h = hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
            self.n += 1
            self.buf = [int.from_bytes(h[i:i + 8], "big") for i in range(24, -1, -8)]
        return self.buf.pop()

    def below(self, k):
        return self.u() % k

    def unit(self):
        return (self.u() >> 11) / float(1 << 53)


# ---------------------------------------------------------------- systems (rule 1)

BITS = [[i for i in range(N) if mask >> i & 1] for mask in range(STATES)]


def bits(mask):
    return BITS[mask]


def tpm_of(perm):
    """p[v][i] = P(V_i,t+1 = 1 | v)."""
    return [[float(perm[v] >> i & 1) for i in range(N)] for v in range(STATES)]


def cut_tpm(p, source):
    """Inputs from the elements of source to every element outside it replaced by uniform noise."""
    if source == 0:
        return p
    src = bits(source)
    out = []
    for v in range(STATES):
        row = []
        for i in range(N):
            if source >> i & 1:
                row.append(p[v][i])
            else:
                tot = 0.0
                for u in range(1 << len(src)):
                    w = v
                    for k, j in enumerate(src):
                        w = (w & ~(1 << j)) | ((u >> k & 1) << j)
                    tot += p[w][i]
                row.append(tot / (1 << len(src)))
        out.append(row)
    return out


def is_er(perm):
    s, k = perm[0], 1
    while s != 0:
        s, k = perm[s], k + 1
    return k == STATES


def inverse(perm):
    inv = [0] * STATES
    for v, w in enumerate(perm):
        inv[w] = v
    return tuple(inv)


def mcx_tpm():
    """Section 2.1's example: M (element 0) the majority of M, C and X; C (element 1) a copy of M; X (element 2) the
    exclusive or of M and C."""
    p = []
    for v in range(STATES):
        m, c, x = v & 1, v >> 1 & 1, v >> 2 & 1
        p.append([float(m + c + x >= 2), float(m), float(m ^ c)])
    return p


# ---------------------------------------------------------------- repertoires (Section 5.3)

def compose(v_bits, mask, rest_mask, rest_value):
    """The state equal to v_bits on mask and to rest_value (packed in order of rest's elements) on rest."""
    s = v_bits & mask
    for k, j in enumerate(bits(rest_mask)):
        s |= (rest_value >> k & 1) << j
    return s


class Rep:
    """Repertoires of one system (a state-by-node TPM) in one state, cached."""

    def __init__(self, p, v):
        self.p, self.v = p, v
        self.e = {}
        self.c1 = {}
        self.c = {}

    def effect(self, mech):
        """[P(Z_i,t+1 = 1 | x_mech) for i]: Equation 8 (mech = 0: Equation 12)."""
        if mech not in self.e:
            rest = FULL & ~mech
            n = 1 << bin(rest).count("1")
            out = []
            for i in range(N):
                tot = 0.0
                for w in range(n):
                    tot += self.p[compose(self.v, mech, rest, w)][i]
                out.append(tot / n)
            self.e[mech] = out
        return self.e[mech]

    def cause_node(self, j, purview):
        """Equation 10 for element j in its current state, over the purview: a list over the purview's states."""
        key = (j, purview)
        if key not in self.c1:
            xj = self.v >> j & 1
            pb = bits(purview)
            rest = FULL & ~purview
            nr = 1 << bin(rest).count("1")
            vals = []
            for z in range(1 << len(pb)):
                zs = 0
                for k, q in enumerate(pb):
                    zs |= (z >> k & 1) << q
                tot = 0.0
                for y in range(nr):
                    pr = self.p[compose(zs, purview, rest, y)][j]
                    tot += pr if xj else 1.0 - pr
                vals.append(tot)
            s = sum(vals)
            self.c1[key] = [x / s for x in vals] if s > 0 else vals
        return self.c1[key]

    def cause(self, mech, purview):
        """Equation 9 (mech = 0: the uniform distribution, Equation 11; purview = 0: [1.0])."""
        key = (mech, purview)
        if key not in self.c:
            size = 1 << bin(purview).count("1")
            if purview == 0:
                rep = [1.0]
            elif mech == 0:
                rep = [1.0 / size] * size
            else:
                rep = [1.0] * size
                for j in bits(mech):
                    cj = self.cause_node(j, purview)
                    rep = [a * b for a, b in zip(rep, cj)]
                s = sum(rep)
                rep = [x / s for x in rep] if s > 0 else rep   # an unreachable state: all zero, as PyPhi's normalize
            self.c[key] = rep
        return self.c[key]


def _index_in(v, purview):
    k, out = 0, 0
    for q in BITS[purview]:
        out |= (v >> q & 1) << k
        k += 1
    return out


INDEX = [[_index_in(v, purview) for purview in range(STATES)] for v in range(STATES)]


def index_in(v, purview):
    """The index of state v restricted to the purview's elements (in order)."""
    return INDEX[v][purview]


# ---------------------------------------------------------------- partitions (Section 5.4; PyPhi's 'ALL')

def set_partitions(seq):
    seq = list(seq)
    if not seq:
        return
    if len(seq) == 1:
        yield [seq]
        return
    first = seq[0]
    for smaller in set_partitions(seq[1:]):
        for n, sub in enumerate(smaller):
            yield smaller[:n] + [[first] + sub] + smaller[n + 1:]
        yield [[first]] + smaller


def k_partitions(seq, k):
    for part in set_partitions(seq):
        if len(part) == k:
            yield part


def all_partitions(mech, purview):
    """PyPhi's 'ALL' partitions of (mechanism, purview), as lists of (mechanism mask, purview mask)."""
    m_el, p_el = bits(mech), bits(purview)
    out, seen = [], set()
    for mp in set_partitions(m_el):
        mparts = [sum(1 << x for x in b) for b in mp] + [0]
        trivial = len(mp) == 1
        for k in range(1, min(len(p_el), len(mparts)) + 1):
            for pp in k_partitions(p_el, k):
                pmasks = [sum(1 << x for x in b) for b in pp] + [0] * (len(mparts) - k)
                for perm in set(itertools.permutations(pmasks)):
                    if trivial and perm[0]:
                        continue
                    parts = tuple(sorted(zip(mparts, perm)))
                    if parts in seen:
                        continue
                    seen.add(parts)
                    out.append(list(zip(mparts, perm)))
    return out


PARTITIONS = {m: all_partitions(m, FULL) for m in range(1, STATES)}
SUB_PARTITIONS = {(m, pv): all_partitions(m, pv) for m in range(1, STATES) for pv in range(1, STATES)}


def kl_bern(a, b):
    out = 0.0
    for pa, pb in ((a, b), (1.0 - a, 1.0 - b)):
        if pa > 0:
            if pb <= 0:
                return math.inf
            out += pa * math.log2(pa / pb)
    return out


def phi_effect(rep, mech):
    intact = rep.effect(mech)
    best = math.inf
    for parts in PARTITIONS[mech]:
        d = 0.0
        for pm, pv in parts:
            if pv:
                q = rep.effect(pm)
                for i in bits(pv):
                    d += kl_bern(intact[i], q[i])
        if d < best:
            best = d
    return max(best, 0.0)


def phi_cause(rep, mech):
    intact = rep.cause(mech, FULL)
    if not any(x > 0 for x in intact):
        return 0.0          # no prior state leads to the mechanism's state: phi_C is 0, as PyPhi's find_mip gives it
    best = math.inf
    for parts in PARTITIONS[mech]:
        d = 0.0
        for v in range(STATES):
            pv = intact[v]
            if pv <= 0:
                continue
            q = 1.0
            for pm, pp in parts:
                if pp:
                    q *= rep.cause(pm, pp)[index_in(v, pp)]
            if q <= 0:
                d = math.inf
                break
            d += pv * math.log2(pv / q)
        if d < best:
            best = d
    return max(best, 0.0)


def phis(p, v):
    rep = Rep(p, v)
    return {m: (phi_cause(rep, m), phi_effect(rep, m)) for m in range(1, STATES)}


def system_values(p):
    """Per state: the seven subsets' (phi_C, phi_E), sum phi_C + sum phi_E, Phi and the negative-sum count."""
    cuts = [cut_tpm(p, x) for x in range(1, FULL)]
    per_state = []
    negative = 0
    for v in range(STATES):
        intact = phis(p, v)
        best = math.inf
        for pc in cuts:
            rep = Rep(pc, v)
            dc = de = 0.0
            for m, (fc, fe) in intact.items():
                if fc > POS:
                    dc += fc - phi_cause(rep, m)
                if fe > POS:
                    de += fe - phi_effect(rep, m)
            negative += (dc < -POS) + (de < -POS)
            best = min(best, dc, de)
        per_state.append({"phi": intact, "sum": sum(a + b for a, b in intact.values()), "Phi": best})
    return per_state, negative


def summary(per_state):
    counts = [0] * 6
    for st in per_state:
        for m, (fc, fe) in st["phi"].items():
            order = bin(m).count("1") - 1
            counts[order] += fc > POS
            counts[3 + order] += fe > POS
    return {"sum": sum(st["sum"] for st in per_state) / STATES, "Phi": sum(st["Phi"] for st in per_state) / STATES,
            "counts": counts}


def ei(p):
    marg = [0.0] * STATES
    rows = []
    for v in range(STATES):
        row = [1.0] * STATES
        for w in range(STATES):
            for i in range(N):
                pr = p[v][i]
                row[w] *= pr if w >> i & 1 else 1.0 - pr
        rows.append(row)
        for w in range(STATES):
            marg[w] += row[w] / STATES
    tot = 0.0
    for row in rows:
        for w in range(STATES):
            if row[w] > 0:
                tot += row[w] * math.log2(row[w] / marg[w]) / STATES
    node_h = []
    for i in range(N):
        q = sum(p[v][i] for v in range(STATES)) / STATES
        node_h.append(-sum(x * math.log2(x) for x in (q, 1 - q) if x > 0))
    return tot, node_h


# ---------------------------------------------------------------- PyPhi's concept-style cuts (a control and beside)

def sever(p, mask):
    """The TPM with each connection in mask (bit i * N + j: from element i before to element j after) replaced by
    uniform noise, as PyPhi marginalises a node's cut inputs."""
    if mask == 0:
        return p
    out = []
    for v in range(STATES):
        row = []
        for j in range(N):
            src = [i for i in range(N) if mask >> (i * N + j) & 1]
            tot = 0.0
            for u in range(1 << len(src)):
                w = v
                for k, i in enumerate(src):
                    w = (w & ~(1 << i)) | ((u >> k & 1) << i)
                tot += p[w][j]
            row.append(tot / (1 << len(src)))
        out.append(row)
    return out


def kcut_mask(parts, side):
    """PyPhi's KCut of a partition of the whole system (its cut_matrix): on the effect side the connections from each
    part's mechanism to the elements outside its purview are cut, on the cause side those from each part's purview to
    the elements outside its mechanism."""
    mask = 0
    for mech, purv in parts:
        frm, to = (mech, purv) if side == "E" else (purv, mech)
        for i in bits(frm):
            for j in bits(FULL & ~to):
                mask |= 1 << (i * N + j)
    return mask


KCUTS = {side: [(kcut_mask(parts, side), parts) for parts in PARTITIONS[FULL]] for side in "CE"}


def concept_style(p, v):
    """For state v, each side's least sum of differences over PyPhi's concept-style cuts (the 146 'ALL' partitions of
    the system, each side's own), with the first partition that gives it; Phi is the smaller of the two."""
    intact = phis(p, v)
    low = {}
    for k, side, fn in ((0, "C", phi_cause), (1, "E", phi_effect)):
        sums = {}
        best = (math.inf, None)
        for mask, parts in KCUTS[side]:
            if mask not in sums:
                rep = Rep(sever(p, mask), v)
                sums[mask] = sum(f[k] - fn(rep, m) for m, f in intact.items() if f[k] > POS)
            if sums[mask] < best[0] - 1e-12:
                best = (sums[mask], parts)
        low[side] = best
    return low


def part_label(parts, names="ABC"):
    """A partition as mechanism>purview parts, the empty part left out (0 for an empty purview)."""
    lab = lambda m: "".join(names[i] for i in bits(m)) or "0"
    order = sorted(parts, key=lambda x: (x[0] == 0, x[0] & -x[0]))
    return ",".join(f"{lab(m)}>{lab(pv)}" for m, pv in order if m or pv)


# ---------------------------------------------------------------- symmetry (rule 3)

def state_maps():
    maps = []
    for perm in itertools.permutations(range(N)):
        for flip in range(STATES):
            g = []
            for s in range(STATES):
                t = 0
                for i in range(N):
                    t |= (s >> i & 1) << perm[i]
                g.append(t ^ flip)
            maps.append(g)
    return maps


MAPS = state_maps()


def canonical(perm):
    best = None
    for g in MAPS:
        ginv = [0] * STATES
        for s, t in enumerate(g):
            ginv[t] = s
        conj = tuple(g[perm[ginv[t]]] for t in range(STATES))
        if best is None or conj < best:
            best = conj
    return best


# ---------------------------------------------------------------- Table 1 and Table 2

TABLE1 = {  # subset mask (M = 1, C = 2, X = 4): (phi_C, phi_E), MCX in state (0,1,1)
    1: (1.0, 1.189), 2: (1.0, 0.189), 4: (1.0, 0.189), 3: (1.0, 1.0), 5: (0.415, 0.0), 6: (1.0, 0.415),
    7: (0.0, 0.415)}
TABLE2 = {  # column: {subset mask (A = 1, B = 2, C = 4): (phi_C, phi_E)} in state (0,1,1)
    "a": {1: (1.0, 1.0), 2: (1.0, 1.0), 4: (1.0, 0.189), 3: (0.415, 0.0), 5: (0.0, 0.0), 6: (0.5, 0.0), 7: (0.0, 1.0)},
    "b": {1: (1.0, 0.189), 2: (1.0, 0.189), 4: (1.0, 1.0), 3: (0.0, 1.415), 5: (1.0, 0.0), 6: (0.415, 0.415),
          7: (0.0, 0.0)},
    "c": {1: (1.0, 1.0), 2: (1.0, 0.378), 4: (1.0, 0.378), 3: (0.415, 0.415), 5: (0.415, 0.415), 6: (0.915, 0.415),
          7: (0.415, 0.415)},
    "d": {1: (1.0, 0.566), 2: (1.0, 0.566), 4: (1.0, 0.566), 3: (1.0, 0.415), 5: (0.83, 0.415), 6: (0.83, 0.415),
          7: (1.0, 0.83)},
}
FIGURE6_PHI = {"a": 0.0, "b": 0.84, "c": 0.0, "d": 1.50}
STATE_011 = 6


def matches(phi, column, tol=0.0015):
    return all(abs(phi[m][0] - c) <= tol and abs(phi[m][1] - e) <= tol for m, (c, e) in column.items())


# ---------------------------------------------------------------- jobs

def class_job(rep_perm):
    per_state, negative = system_values(tpm_of(rep_perm))
    s = summary(per_state)
    s["negative"] = negative
    return rep_perm, s


def er_state_job(perms):
    out = []
    for perm in perms:
        phi = phis(tpm_of(perm), STATE_011)
        hit = [col for col, column in TABLE2.items() if matches(phi, column)]
        if hit:
            out.append((perm, hit))
    return out


STAR_SOURCE = 4      # Table 1's Phi is found at {MC_t, MCX_t+1}, {X_t, 0}: X's outputs cut, for MCX the cut X -/-> MC
STAR_LOST = (4, 6, 7)   # which, the paper says, eliminates phi_E of X, CX and MCX


def table1(p):
    """MCX in (0,1,1): its values per subset, Phi over the six unidirectional cuts with every cut's two sums, and each
    side's least sum over PyPhi's concept-style cuts."""
    per_state, _ = system_values(p)
    st = per_state[STATE_011]
    uni = []
    for x in range(1, FULL):
        rep = Rep(cut_tpm(p, x), STATE_011)
        for k, side, fn in ((0, "C", phi_cause), (1, "E", phi_effect)):
            uni.append((sum(f[k] - fn(rep, m) for m, f in st["phi"].items() if f[k] > POS), x, side))
    return st, uni, concept_style(p, STATE_011)


def controls_run(seed):
    ctl = {}
    p = mcx_tpm()
    st, uni, ks = table1(p)
    ok = all(abs(st["phi"][m][0] - c) <= 0.001 and abs(st["phi"][m][1] - e) <= 0.001 for m, (c, e) in TABLE1.items())
    e_val, _ = ei(p)
    rep = Rep(cut_tpm(p, STAR_SOURCE), STATE_011)
    lost = {m: st["phi"][m][1] - phi_effect(rep, m) for m in range(1, STATES)}
    named = all(abs(lost[m] - (st["phi"][m][1] if m in STAR_LOST else 0.0)) < 1e-9 for m in lost)
    at_star = sum(lost[m] for m in lost if st["phi"][m][1] > POS)
    ctl["Table 1: MCX in (0,1,1), its 14 values of phi to 0.001 and EI = 2.5; at the partition where its Phi is found, "
        "{MC_t, MCX_t+1}, {X_t, 0} (X -/-> MC), phi_E of X, CX and MCX eliminated and nothing else, 1.02 to 0.005"] = (
        ok and abs(e_val - 2.5) < 1e-9 and named and abs(at_star - 1.02) <= 0.005)
    ks_phi = min(ks["C"][0], ks["E"][0])
    least = min(uni)
    names = "MCX"
    lab = lambda m: "".join(names[i] for i in bits(m))
    notes = {
        "table1_phi": (f"MCX in (0,1,1): Phi {least[0]:.3f} over the six unidirectional cuts (least at "
                       f"{lab(least[1])} -/-> {lab(FULL & ~least[1])}, {'effect' if least[2] == 'E' else 'cause'}); "
                       f"{at_star:.3f} at X -/-> MC (Table 1: 1.02); concept-style {ks_phi:.3f}, cause least "
                       f"{ks['C'][0]:.3f} (Appendix B: 2.23)"),
        "table1": {"unidirectional": {f"{lab(x)} -/-> {lab(FULL & ~x)} ({side})": round(d, 6) for d, x, side in uni},
                   "concept_style": {side: [round(ks[side][0], 6), part_label(ks[side][1], names)] for side in "CE"}},
    }

    stream = Stream(seed, "at2019/random-systems")
    ok_rep = ok_add = True
    for _ in range(40):
        q = [[stream.unit() for _ in range(N)] for _ in range(STATES)]
        v = stream.below(STATES)
        rep = Rep(q, v)
        for mech in range(STATES):
            # effect: Equation 8 by direct enumeration of the joint over V_t+1
            for i in range(N):
                rest = [j for j in range(N) if not mech >> j & 1]
                tot = 0.0
                for w in itertools.product((0, 1), repeat=len(rest)):
                    s = v & mech
                    for j, b in zip(rest, w):
                        s |= b << j
                    tot += q[s][i]
                if abs(tot / (1 << len(rest)) - rep.effect(mech)[i]) > 1e-12:
                    ok_rep = False
            for purview in range(1, STATES):
                pb = bits(purview)
                direct = []
                for zi in range(1 << len(pb)):          # the module's order: the purview's element k is bit k
                    z = [zi >> k & 1 for k in range(len(pb))]
                    val = 1.0
                    for j in bits(mech):
                        num = 0.0
                        den = 0.0
                        for full in range(STATES):
                            pr = q[full][j] if v >> j & 1 else 1.0 - q[full][j]
                            den += pr
                            if all((full >> qq & 1) == zz for qq, zz in zip(pb, z)):
                                num += pr
                        val *= num / den
                    direct.append(val)
                if mech:
                    sd = sum(direct)
                    direct = [x / sd for x in direct]
                else:
                    direct = [1.0 / len(direct)] * len(direct)
                if max(abs(a - b) for a, b in zip(direct, rep.cause(mech, purview))) > 1e-12:
                    ok_rep = False
        for mech in range(1, STATES):
            intact = rep.effect(mech)
            for parts in PARTITIONS[mech][:10]:
                joint_i = [1.0] * STATES
                joint_q = [1.0] * STATES
                for w in range(STATES):
                    for i in range(N):
                        b = w >> i & 1
                        joint_i[w] *= intact[i] if b else 1 - intact[i]
                    for pm, pv in parts:
                        if pv:
                            qq = rep.effect(pm)
                            for i in bits(pv):
                                b = w >> i & 1
                                joint_q[w] *= qq[i] if b else 1 - qq[i]
                direct = sum(a * math.log2(a / b) for a, b in zip(joint_i, joint_q) if a > 0)
                short = 0.0
                for pm, pv in parts:
                    if pv:
                        qq = rep.effect(pm)
                        short += sum(kl_bern(intact[i], qq[i]) for i in bits(pv))
                if abs(direct - short) > 1e-9:
                    ok_add = False
    ctl["the repertoires equal a direct enumeration of Equations 8 to 10 on 40 seed-drawn probabilistic "
        "systems"] = ok_rep
    ctl["the effect side's additive relative entropy equals the joint one on the same systems"] = ok_add
    counts = [len(PARTITIONS[m]) for m in (1, 3, 7)]
    distinct = all(len({tuple(sorted(x)) for x in PARTITIONS[m]}) == len(PARTITIONS[m]) for m in PARTITIONS)
    ctl["the partitions number 1, 28 and 146 for one, two and three elements, none repeated"] = (
        counts == [1, 28, 146] and distinct)
    return ctl, notes


def run(seed, results="results", workers=WORKERS):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    ctl, notes = controls_run(seed)
    if not all(ctl.values()):
        raise AssertionError(f"a control failed: {[k for k, v in ctl.items() if not v]}")

    perms = list(itertools.permutations(range(STATES)))
    canon = {perm: canonical(perm) for perm in perms}
    reps = sorted(set(canon.values()))
    er = [perm for perm in perms if is_er(perm)]
    if workers > 1:
        pool = multiprocessing.get_context("fork").Pool(workers)
        mapper = lambda f, xs: list(pool.imap(f, xs, chunksize=4))
    else:
        pool = None
        mapper = lambda f, xs: [f(x) for x in xs]
    try:
        values = dict(mapper(class_job, reps))
        stream = Stream(seed, "at2019/symmetry")
        sample = [perms[stream.below(len(perms))] for _ in range(SYMMETRY_SAMPLE)]
        direct = dict(mapper(class_job, sample))
        chunks = [er[k:k + 120] for k in range(0, len(er), 120)]
        table2_hits = [hit for chunk in mapper(er_state_job, chunks) for hit in chunk]
    finally:
        if pool:
            pool.close()
            pool.join()
    sym_ok = all(abs(direct[s]["sum"] - values[canon[s]]["sum"]) < 1e-9
                 and abs(direct[s]["Phi"] - values[canon[s]]["Phi"]) < 1e-9
                 and direct[s]["counts"] == values[canon[s]]["counts"] for s in sample)
    ctl[f"symmetry: {SYMMETRY_SAMPLE} seed-drawn systems computed directly equal their class representatives"] = sym_ok
    if not sym_ok:
        raise AssertionError("a control failed: symmetry")

    ei_ok, ei_min = True, math.inf
    for perm in perms:
        e_val, node_h = ei(tpm_of(perm))
        ei_min = min(ei_min, e_val)
        if abs(e_val - 3.0) > 1e-9 or any(abs(h - 1.0) > 1e-9 for h in node_h):
            ei_ok = False
    of = lambda perm: values[canon[perm]]
    er_sums = [of(p)["sum"] for p in er]
    er_counts = {tuple(of(p)["counts"]) for p in er}
    rev_diff = [p for p in perms if abs(of(p)["sum"] - of(inverse(p))["sum"]) > DIFF
                or abs(of(p)["Phi"] - of(inverse(p))["Phi"]) > DIFF]
    unordered = {tuple(min(p, inverse(p))) for p in perms}
    unordered_diff = {tuple(min(p, inverse(p))) for p in rev_diff}
    cond = {
        "every reversible system: EI = 3 bits, each element 1 bit": ei_ok,
        "ER systems: sum phi_C + sum phi_E takes more than one value": max(er_sums) - min(er_sums) > DIFF,
        "ER systems: the counts of irreducible subsets by order and side differ": len(er_counts) > 1,
        "some reversible system differs from its time reverse": len(rev_diff) > 0,
    }

    rev_sums = [of(p)["sum"] for p in perms]
    rev_phis = [of(p)["Phi"] for p in perms]
    er_phis = [of(p)["Phi"] for p in er]
    t2 = {col: [p for p, hit in table2_hits if col in hit] for col in TABLE2}
    t2_phi = {}
    for col, plist in t2.items():
        if plist:
            per_state, _ = system_values(tpm_of(plist[0]))
            t2_phi[col] = (round(per_state[STATE_011]["Phi"], 3), round(summary(per_state)["Phi"], 3))
    t2_ks = {}
    for col, plist in t2.items():
        if plist:
            p2 = tpm_of(plist[0])
            ks_states = [concept_style(p2, v) for v in range(STATES)]
            ks_phis = [min(x["C"][0], x["E"][0]) for x in ks_states]
            t2_ks[col] = (round(ks_phis[STATE_011], 3), round(sum(ks_phis) / STATES, 3))
    stream = Stream(seed, "at2019/purview")
    worse = checked = 0
    for _ in range(PURVIEW_SAMPLE):
        perm = perms[stream.below(len(perms))]
        v = stream.below(STATES)
        p = tpm_of(perm)
        rep = Rep(p, v)
        for mech in range(1, STATES):
            full_c, full_e = phi_cause(rep, mech), phi_effect(rep, mech)
            for purview in range(1, FULL):
                parts_list = SUB_PARTITIONS[(mech, purview)]
                intact_c = rep.cause(mech, purview)
                bc = math.inf
                for parts in parts_list:
                    d = 0.0
                    for z in range(len(intact_c)):
                        if intact_c[z] <= 0:
                            continue
                        qv = 1.0
                        zz = 0
                        for kk, el in enumerate(bits(purview)):
                            zz |= (z >> kk & 1) << el
                        for pm, pp in parts:
                            if pp:
                                qv *= rep.cause(pm, pp)[index_in(zz, pp)]
                        d = math.inf if qv <= 0 else d + intact_c[z] * math.log2(intact_c[z] / qv)
                    bc = min(bc, d)
                ie = rep.effect(mech)
                be = math.inf
                for parts in parts_list:
                    d = 0.0
                    for pm, pv in parts:
                        if pv:
                            qq = rep.effect(pm)
                            d += sum(kl_bern(ie[i], qq[i]) for i in bits(pv))
                    be = min(be, d)
                checked += 1
                worse += (bc > full_c + DIFF) or (be > full_e + DIFF)
    negative = sum(v["negative"] > 0 for v in values.values())

    def rng(xs):
        return f"{min(xs):.3f} to {max(xs):.3f}, mean {sum(xs) / len(xs):.3f}"
    values_out = {
        "ei": (f"{len(perms)} reversible systems: EI = 3 bits and each element 1 bit in "
               f"{'all' if ei_ok else 'NOT all'} (least EI {ei_min:.6f})"),
        "er_sum": (f"{len(er)} ER systems: state-averaged sum phi_C + sum phi_E {rng(er_sums)}; "
                   f"{len({round(x, 6) for x in er_sums})} distinct values"),
        "er_counts": f"distinct counts of irreducible subsets by order and side among ER systems: {len(er_counts)}",
        "time_reverse": (f"systems differing from their time reverse: {len(rev_diff)} of {len(perms)}; "
                         f"unordered pairs {len(unordered_diff)} of {len(unordered)}"),
        "pairs_share": (f"share differing: systems {len(rev_diff) / len(perms):.4f}, unordered pairs "
                        f"{len(unordered_diff) / len(unordered):.4f} (Section 3.2: more than half)"),
        "rev_sum": f"reversible: sum phi_C + sum phi_E {rng(rev_sums)}",
        "rev_phi": (f"reversible: Phi {rng(rev_phis)}; Phi = 0 in "
                    f"{sum(x <= DIFF for x in rev_phis)} of {len(rev_phis)}"),
        "er_phi": f"ER: Phi {rng(er_phis)}; Phi = 0 in {sum(x <= DIFF for x in er_phis)} of {len(er_phis)}",
        "table2": ("ER systems matching Table 2 at (0,1,1): " + ", ".join(f"({c}) {len(t2[c])}" for c in TABLE2)),
        "table2_phi": ("Phi at (0,1,1) / averaged, first match: " + ", ".join(
            f"({c}) {t2_phi[c][0]}/{t2_phi[c][1]} (Fig. 6: {FIGURE6_PHI[c]})" if c in t2_phi else f"({c}) none"
            for c in TABLE2)),
        "table2_phi_ks": ("concept-style Phi at (0,1,1) / averaged, first match: " + ", ".join(
            f"({c}) {t2_ks[c][0]}/{t2_ks[c][1]} (Fig. 6: {FIGURE6_PHI[c]})" if c in t2_ks else f"({c}) none"
            for c in TABLE2)),
        "table1_phi": notes["table1_phi"],
        "purview": f"a smaller purview gave more phi than the full one in {worse} of {checked} subset-states",
        "negative": f"classes with some cut raising a sum of phi: {negative} of {len(values)}",
        "classes": f"{len(reps)} symmetry classes of {len(perms)} reversible systems",
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values_out[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"test": TEST, "conditions": cond, "controls": ctl,
              "classes": {",".join(map(str, r)): {"sum": values[r]["sum"], "Phi": values[r]["Phi"],
                                                  "counts": values[r]["counts"], "negative": values[r]["negative"]}
                          for r in reps},
              "table2_matches": {c: [list(p) for p in t2[c][:20]] for c in TABLE2}, "table2_phi": t2_phi,
              "table2_phi_ks": t2_ks, "table1": notes["table1"],
              "purview": {"checked": checked, "smaller_better": worse}}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="utf-8") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"at2019: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
