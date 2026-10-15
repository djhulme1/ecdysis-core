#!/usr/bin/env python3
"""Hordijk and Steel's RAF algorithm, run as the paper states it, against exhaustive search on small reaction systems
and against a second schedule of the same reduction rules on Kauffman's binary polymer model, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:39437d110cd8a342) is from W. Hordijk and
M. Steel, "Detecting autocatalytic, self-sustaining sets in chemical reaction systems", Journal of Theoretical
Biology 227(4), 451-461, 2004 (doi:10.1016/j.jtbi.2003.11.020), its abstract: "In this paper we first describe a
polynomial-time algorithm that determines whether any given set of molecules, reactions and catalysations contains a
subsystem that is both autocatalytic and able to be sustained from a given subset of the molecules. We also describe
some combinatorial properties of this algorithm, and show how it can be used to find irreducible auto-catalysing and
sustaining subsystems." The test, as registered: see TEST below. No data of record: every system is drawn from the
seed, so the receipt is a reproduction.

The paper's definitions, read from the authors' copy of the journal's proof (on Steel's university page) before this
module was written, and followed here throughout:
- Section 2. X a set of molecules, F (food) a subset of X. A reaction is an ordered pair r = (A, B) of disjoint
  subsets of X, reactants A and products B; R a set of reactions; a catalysation (x, r) says molecule x catalyses
  r, C the set of them; rho(R') and pi(R') the reactants and products of R', supp(R') their union.
- Section 3. cl_R'(X') is the least W containing X' with A in W implies B in W for every (A, B) in R'. A nonempty
  R' is reflexively autocatalytic (RA) if every r in R' has a catalyst x in supp(R'), F-generated if rho(R') lies in
  cl_R'(F), and RAF if both.
- Section 5. Rule (R1): delete r if no x in supp(R) catalyses it; rule (R2): delete r if rho(r) is not in cl_R(F).
  g(R) and d(R) are R after (R1), respectively (R2), is applied until nothing more can be deleted; Lemma 5.1: g(R)
  is the largest RA set and d(R) the largest F-generated set (empty when there is none), whatever the order.
- Section 6, Theorem 6.1. R_1 = R, R_(i+1) = d(g(R_i)), R_inf their intersection: an RAF exists if and only if
  R_inf is nonempty, and R_inf is then the largest RAF. An irreducible RAF (an RAF with no RAF as a proper subset)
  is found by going through R_inf's reactions once, deleting r whenever what is left without it still has an RAF.
- Section 7. Algorithm 1 (ReduceToRA), Algorithm 2 (ComputeClosure) and Algorithm 3 (ReduceToF-generated), called
  in that order again and again "until either no reactions are left or no more reductions can be made"; "the total
  number of calls to the three routines is at most |R|", and the worst case is O(|X||R|^3).
- Section 8. Kauffman's model: X(n) every string of length 1 to n over {0, 1}; F the strings of length at most
  t = 2; R(n) every r = ({a, b}, {c}) and r = ({c}, {a, b}) with c = ab or c = ba (a set of pairs, so a reaction
  that two splits of c give is one reaction, and a = b gives ({a}, {aa})); each (x, r) a catalysation independently
  with probability p(n), and f(n) = p(n)|R(n)|.

The 2004 reading of RA is kept: a catalyst must be a reactant or product of the set's own reactions, so a food
molecule outside supp(R') cannot catalyse. Later papers (from Hordijk, Kauffman and Steel 2011) and the lab's own
raf/check.py let any molecule of cl_R'(F) catalyse, food included; that reading is one of the planted faults below.

Every rule below was fixed before this module computed any outcome of the algorithm. Known before it: the paper's
text and figures (its Section 9 simulations, Figure 4's transition between f = 1.25 and 1.5, Figure 6's linear fit
1.107 + 0.018 n, Figure 7's running time |R|^1.43), and the lab's earlier RAF checks (raf/check.py, raf/diversity.py)
under the later reading. The exhaustive search, the polymer model's construction and draws, and rule 7's reference
were timed beforehand on systems drawn from a seed the run never uses, the algorithm of rule 3 not run.

1. Small systems. System i (0 <= i < 20,000) draws from Stream(seed, "hs2004/small/<i>"): m = 3 + u mod 5 molecules
   (3 to 7), numbered 0 to m - 1; the food the first 1 + u mod min(3, m - 1) of them; k = 1 + u mod 12 reactions
   (at most as many as there are); the catalysation chance q = 1/20, 1/10, 1/5 or 1/3 (u mod 4). Each reaction: |A|
   = 1 + u mod 2 and |B| = 1 + u mod min(2, m - |A|); A then B drawn without replacement from the molecules (B from
   those not in A) by repeated draws of u mod the number left; a reaction already drawn is drawn again. Then each
   (reaction, molecule) pair in that order is a catalysation when u mod den < num, q = num/den. Each u is the next
   integer of the stream, an exact draw.
2. Exhaustive search. Every nonempty subset S of a small system's reactions, as bitmasks: supp(S); RA(S) if every
   r in S has a catalyst in supp(S); cl_S(F) by firing every r in S whose reactants are present until nothing is
   added; F-generated if every reactant is in it. The RAF sets, and the unions of the RA sets and of the F-generated
   sets, are recorded; a second search written with Python sets checks the first (controls).
3. The algorithm, as Section 7 states it, for any system and any starting set of reactions (by default all of them):
   repeat {ReduceToRA: sweep the reactions in order, deleting r when none of its catalysts is in supp of the
   reactions not yet deleted, and sweep again until a sweep deletes nothing; ComputeClosure: W = F, then sweep,
   adding B to W for every r = (A, B) with A in W and B not in W, until a sweep adds nothing; ReduceToF-generated:
   one sweep deleting every r whose reactants are not all in W} until no reactions are left or a pass deleted
   nothing. Its result, its passes (one per round of the three routines) and its checks (each time one of the three
   routines evaluates its if-condition for a reaction) are recorded.
4. The irreducible RAF, as Theorem 6.1's proof gives it: start from rule 3's result; for each of its reactions in
   order, if rule 3 run on what is left without it returns a nonempty set, delete it. (The proof shows each reaction
   needs considering once.)
5. Lemma 5.1, on the small systems: g(R) by Algorithm 1 alone; g(R) again by deleting one violator of (R1) at a
   time, chosen by the seed, until none is left; d(R) by deleting one violator of (R2) at a time, chosen by the seed,
   the closure recomputed after each.
6. Kauffman's model. n from 5 to 10, f = 1, 5/4, 3/2 and 2, ten instances each (240). The string of length L and
   value v (first character most significant) is molecule (2^L - 2) + v; the food is molecules 0 to 5. Reactions:
   for L from 2 to n, v from 0 to 2^L - 1 and split k from 1 to L - 1, the ligation ({a, b}, {c}) for c = ab with a
   the first k characters, kept the first time it appears; all ligations, then all their cleavages in the same order.
   Instance j at (n, f) draws from numpy's Generator(PCG64(int(SHA-256(seed "|hs2004/polymer/n<n>/f<num>-<den>|" j)))):
   pair (r, x) is a catalysation when an integer drawn uniformly from 0 to den |R| - 1 is below num, f = num/den,
   so p(n) = f/|R(n)| exactly; the pairs are drawn reaction by reaction, molecule by molecule.
7. The reference for the polymer instances, which shares no code with rule 3: start with all reactions; repeat
   {compute supp and the closure (breadth-first, each reaction fired when its last missing reactant arrives); list
   the reactions that violate (R1) or (R2); delete each with probability 1/2 by the seed (at least one, chosen by the
   seed, when the draws delete none)} until none violates. Every reaction it deletes violates a rule in a set that
   contains every RAF, so it deletes no reaction of any RAF, and it stops at a set with no violator, an RAF or
   empty: the largest RAF, by a schedule unlike Algorithms 1 to 3. It is checked against rule 2 on the first 2,000
   small systems (controls). Where the largest RAF has 1 to 300 reactions, rule 4's irreducible RAF is checked by
   definition and by running the reference on it less each of its reactions in turn.
8. The test's seven conditions: (1) on every small system, rule 3's result is the union of the RAF sets rule 2
   finds (empty exactly when there is none); (2) on every small system with an RAF, rule 4's set is one of rule 2's
   RAF sets with none of them a proper subset of it; (3) on every small system, both of rule 5's g(R) are rule 2's
   union of RA sets and rule 5's d(R) its union of F-generated sets; (4) on every polymer instance, rule 3's result
   is rule 7's; (5) on every polymer instance whose largest RAF has 1 to 300 reactions, rule 4's set is an RAF and
   loses it without any one of its reactions; (6) on every run of rule 3, at most |R| passes; (7) at most
   |R|^3 + 4|R|^2 checks, the count Section 7's accounting allows (ReduceToRA's sweeps at most 2|R|^2 checks in all,
   ComputeClosure's at most |R|(|R| + 1) a call, ReduceToF-generated's |R| a call, at most |R| calls). test_passed
   is 1 if all seven hold.
9. Beside, none of it counted: the paper's own example (Section 2, its Figure 2's RAF {r1, r2}); each (n, f)'s
   share of instances with an RAF and the mean size of the largest RAF (the paper's Figures 4 and 6 come from far
   more instances); the irreducible RAFs' sizes against the largest ones' (its Figure 5); the least-squares slope of
   log checks on log |R| over the polymer instances (its Figure 7's 1.43 is CPU time, not checks); and how often
   the later reading of RA (a food molecule may catalyse) changes the largest RAF of a small system.

Controls (controls_passed counts those that behave as stated; the run stops if any fails): the bitmask search against
the set-based one on 300 small systems; the polymer reactions against an enumeration of every (a, b) with |a| + |b|
<= n, both orders, for n = 2 to 6, with |X(n)| = 2^(n+1) - 2; rule 7's reference against rule 2 on 2,000 small
systems; three planted faults, each of which must disagree with rule 2 on at least one of those 2,000 systems (the
later reading of RA; one pass of the three routines only; ComputeClosure stopped after one sweep); and the
catalysations drawn on the polymer instances, whose total at each n must lie within five standard errors of its
expectation.

What it cannot check: the theorem for systems larger than these, which rests on the paper's proof (each rule deletes
only reactions no RAF inside the current set can contain); the running time's constant on any machine (checks are
counted, not seconds); the "combinatorial properties" beyond Lemma 5.1 and Theorem 6.1, which the abstract does not
name.

Writes results/outputs.json and results/detail.json. Run with: python3 raf/hs2004.py
"""

import os

for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import multiprocessing  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
from fractions import Fraction  # noqa: E402

import numpy as np  # noqa: E402

SMALL = 20000
SMALL_CHUNK = 500
SMALL_REFERENCE = 2000      # the reference and the planted faults run on the first 2,000 small systems
SMALL_SETS = 300            # the set-based search checks the bitmask one on the first 300
MOLECULES = (3, 7)
FOOD_MAX = 3
REACTIONS_MAX = 12
CHANCES = ((1, 20), (1, 10), (1, 5), (1, 3))
POLYMER_N = tuple(range(5, 11))
POLYMER_F = ((1, 1), (5, 4), (3, 2), (2, 1))
POLYMER_EACH = 10
FOOD_LENGTH = 2
IRREDUCIBLE_MAX = 300
WORKERS = 2
LIMIT = 200
TEST = ("Refuted if the algorithm as Section 7 states it (its three routines repeated; catalysts in supp(R)), "
        "on any of 20,000 seed-drawn systems of 3 to 7 molecules and 1 to 12 reactions, returns other than the "
        "union of the RAFs exhaustive search finds, or g(R) or d(R) is not the largest RA or F-generated set, or "
        "the proof's irreducible RAF is not irreducible; or, on 240 instances of Kauffman's model (t = 2, n = 5 "
        "to 10), differs from deleting (R1) or (R2) violators in seeded batches, or its irreducible RAF (up to "
        "300 reactions) is not irreducible; or takes over |R| passes or |R|^3 + 4|R|^2 checks.")
OUTPUTS = ("small", "small_raf", "irreducible_small", "lemma51", "polymer", "polymer_raf", "irreducible_polymer",
           "passes", "checks", "example", "share_raf", "maxraf_mean", "irreducible_share", "slope", "later_reading",
           "conditions_met", "conditions_total", "test_passed", "controls_passed", "controls_total")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- randomness

class Stream:
    """Integers from SHA-256 of the seed, a label and a counter: four 64-bit integers a hash."""

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


def polymer_rng(seed, n, f, j):
    label = f"{seed}|hs2004/polymer/n{n}/f{f[0]}-{f[1]}|{j}".encode()
    return np.random.Generator(np.random.PCG64(int.from_bytes(hashlib.sha256(label).digest(), "big")))


# ---------------------------------------------------------------- systems

class System:
    """molecules 0 .. m - 1; reactions a list of (A, B), each a tuple of molecule numbers; cats a tuple of catalyst
    tuples, one per reaction; food a tuple of molecule numbers."""

    def __init__(self, m, food, reactions, cats):
        self.m, self.food, self.reactions, self.cats = m, tuple(food), list(reactions), list(cats)
        for A, B in self.reactions:
            if not A or not B or set(A) & set(B) or not all(0 <= x < m for x in A + B):
                raise ValueError("a reaction must be a pair of disjoint nonempty sets of molecules")
        if len(set(self.reactions)) != len(self.reactions):
            raise ValueError("a reaction listed twice")
        if len(self.cats) != len(self.reactions):
            raise ValueError("one catalyst tuple per reaction")


def small_system(seed, i):
    """Rule 1."""
    st = Stream(seed, f"hs2004/small/{i}")
    m = MOLECULES[0] + st.below(MOLECULES[1] - MOLECULES[0] + 1)
    nf = 1 + st.below(min(FOOD_MAX, m - 1))
    k = 1 + st.below(REACTIONS_MAX)
    num, den = CHANCES[st.below(len(CHANCES))]
    k = min(k, POSSIBLE[m])
    seen, reactions = set(), []
    while len(reactions) < k:
        a = 1 + st.below(2)
        b = 1 + st.below(min(2, m - a))
        pool = list(range(m))
        A = []
        for _ in range(a):
            A.append(pool.pop(st.below(len(pool))))
        B = []
        for _ in range(b):
            B.append(pool.pop(st.below(len(pool))))
        r = (tuple(sorted(A)), tuple(sorted(B)))
        if r in seen:
            continue
        seen.add(r)
        reactions.append(r)
    cats = []
    for _ in reactions:
        cats.append(tuple(x for x in range(m) if st.below(den) < num))
    return System(m, range(nf), reactions, cats), {"m": m, "food": nf, "k": k, "q": f"{num}/{den}"}


def _subsets(m, lo, hi):
    out = []
    for mask in range(1, 1 << m):
        c = bin(mask).count("1")
        if lo <= c <= hi:
            out.append(tuple(x for x in range(m) if mask >> x & 1))
    return out


POSSIBLE = {m: sum(1 for A in _subsets(m, 1, 2) for B in _subsets(m, 1, 2) if not set(A) & set(B))
            for m in range(MOLECULES[0], MOLECULES[1] + 1)}


def example_system():
    """The paper's Section 2 example: a..g are 0..6; F = {a, b}; r1: a + b -> c, catalysed by d; r2: b + c -> d, by
    a; r3: c + d -> e + f, uncatalysed; r4: a + e -> g, by f."""
    a, b, c, d, e, f, g = range(7)
    reactions = [((a, b), (c,)), ((b, c), (d,)), ((c, d), (e, f)), ((a, e), (g,))]
    return System(7, (a, b), reactions, [(d,), (a,), (), (f,)])


# ---------------------------------------------------------------- Kauffman's model (rule 6)

def mol(L, v):
    return (1 << L) - 2 + v


def polymer_reactions(n):
    ligations, seen = [], set()
    for L in range(2, n + 1):
        for v in range(1 << L):
            c = mol(L, v)
            for k in range(1, L):
                a = mol(k, v >> (L - k))
                b = mol(L - k, v & ((1 << (L - k)) - 1))
                r = (tuple(sorted({a, b})), (c,))
                if r in seen:
                    continue
                seen.add(r)
                ligations.append(r)
    return ligations + [(B, A) for A, B in ligations]


def polymer_reactions_enumerated(n):
    """Control: every (a, b) with |a| + |b| <= n, both concatenation orders, as sets of (A, B)."""
    strings = [(L, v) for L in range(1, n + 1) for v in range(1 << L)]
    out = set()
    for La, va in strings:
        for Lb, vb in strings:
            if La + Lb > n:
                continue
            for c in (mol(La + Lb, (va << Lb) | vb), mol(La + Lb, (vb << La) | va)):
                A = tuple(sorted({mol(La, va), mol(Lb, vb)}))
                out.add((A, (c,)))
                out.add(((c,), A))
    return out


def polymer_catalysts(rng, m, nr, f, batch=256):
    num, den = f
    hi = den * nr
    dtype = np.uint32 if hi < 2 ** 32 else np.uint64
    cats = []
    for start in range(0, nr, batch):
        rows = min(batch, nr - start)
        u = rng.integers(0, hi, size=(rows, m), dtype=dtype)
        hit = u < num
        for row in range(rows):
            cats.append(tuple(int(x) for x in np.flatnonzero(hit[row])))
    return cats


# ---------------------------------------------------------------- rule 2: exhaustive search

def masks(s):
    A = [sum(1 << x for x in r[0]) for r in s.reactions]
    B = [sum(1 << x for x in r[1]) for r in s.reactions]
    C = [sum(1 << x for x in c) for c in s.cats]
    return A, B, C, sum(1 << x for x in s.food)


def exhaustive(s):
    """Every nonempty subset of reactions: (the RAF sets as bitmasks, the union of RA sets, the union of F-generated
    sets)."""
    A, B, C, F = masks(s)
    k = len(A)
    AB = [A[r] | B[r] for r in range(k)]
    supp = [0] * (1 << k)
    rafs, ra_union, fg_union = [], 0, 0
    for S in range(1, 1 << k):
        low = S & -S
        r0 = low.bit_length() - 1
        supp[S] = supp[S ^ low] | AB[r0]
        members = [r for r in range(k) if S >> r & 1]
        sp = supp[S]
        ra = all(C[r] & sp for r in members)
        W = F
        changed = True
        while changed:
            changed = False
            for r in members:
                if A[r] & ~W == 0 and B[r] & ~W:
                    W |= B[r]
                    changed = True
        fg = all(A[r] & ~W == 0 for r in members)
        if ra:
            ra_union |= S
        if fg:
            fg_union |= S
        if ra and fg:
            rafs.append(S)
    return rafs, ra_union, fg_union


def exhaustive_sets(s):
    """The same search written with Python sets, straight from the definitions (control)."""
    import itertools
    k = len(s.reactions)
    rafs, ra_union, fg_union = [], set(), set()
    for size in range(1, k + 1):
        for S in itertools.combinations(range(k), size):
            supp = set()
            for r in S:
                supp |= set(s.reactions[r][0]) | set(s.reactions[r][1])
            ra = all(any(x in supp for x in s.cats[r]) for r in S)
            W = set(s.food)
            while True:
                grow = set()
                for r in S:
                    if set(s.reactions[r][0]) <= W:
                        grow |= set(s.reactions[r][1])
                if grow <= W:
                    break
                W |= grow
            fg = all(set(s.reactions[r][0]) <= W for r in S)
            if ra:
                ra_union |= set(S)
            if fg:
                fg_union |= set(S)
            if ra and fg:
                rafs.append(frozenset(S))
    return rafs, ra_union, fg_union


def to_mask(rs):
    return sum(1 << r for r in rs)


# ---------------------------------------------------------------- rule 3: the algorithm as Section 7 states it

def raf_algorithm(s, active=None, fault=None):
    """Algorithms 1, 2 and 3 in turn until no reactions are left or a pass deletes nothing. fault: None, "later"
    (a food molecule may catalyse), "one-pass" (the three routines once) or "one-sweep" (ComputeClosure stops after
    one sweep). Returns (the reactions left, in order; passes; checks)."""
    R = list(range(len(s.reactions))) if active is None else sorted(active)
    alive = bytearray(len(s.reactions))
    cnt = [0] * s.m
    for r in R:
        alive[r] = 1
        A, B = s.reactions[r]
        for x in A:
            cnt[x] += 1
        for x in B:
            cnt[x] += 1
    food = bytearray(s.m)
    for x in s.food:
        food[x] = 1

    def delete(r):
        alive[r] = 0
        A, B = s.reactions[r]
        for x in A:
            cnt[x] -= 1
        for x in B:
            cnt[x] -= 1

    passes = checks = 0
    while True:
        passes += 1
        before = len(R)
        while True:                                        # Algorithm 1, ReduceToRA
            change = False
            for r in R:
                checks += 1
                if fault == "later":
                    ok = any(cnt[x] > 0 or food[x] for x in s.cats[r])
                else:
                    ok = any(cnt[x] > 0 for x in s.cats[r])
                if not ok:
                    delete(r)
                    change = True
            R = [r for r in R if alive[r]]
            if not change:
                break
        W = bytearray(food)                                # Algorithm 2, ComputeClosure
        while True:
            change = False
            for r in R:
                checks += 1
                A, B = s.reactions[r]
                if all(W[x] for x in A) and not all(W[x] for x in B):
                    for x in B:
                        W[x] = 1
                    change = True
            if not change or fault == "one-sweep":
                break
        for r in R:                                        # Algorithm 3, ReduceToF-generated
            checks += 1
            if not all(W[x] for x in s.reactions[r][0]):
                delete(r)
        R = [r for r in R if alive[r]]
        if not R or len(R) == before or fault == "one-pass":
            break
    return R, passes, checks


def reduce_to_ra(s):
    """Algorithm 1 alone on all of R: g(R)."""
    R = list(range(len(s.reactions)))
    cnt = [0] * s.m
    for A, B in s.reactions:
        for x in A + B:
            cnt[x] += 1
    alive = [True] * len(R)
    while True:
        change = False
        for r in R:
            if not any(cnt[x] > 0 for x in s.cats[r]):
                alive[r] = False
                for x in s.reactions[r][0] + s.reactions[r][1]:
                    cnt[x] -= 1
                change = True
        R = [r for r in R if alive[r]]
        if not change:
            return R


def violators(s, S, rules):
    """The reactions of S that violate (R1) ("ra") or (R2) ("fg") with respect to S, in order."""
    out = []
    supp = set()
    for r in S:
        supp |= set(s.reactions[r][0]) | set(s.reactions[r][1])
    W = closure_bfs(s, S) if "fg" in rules else None
    for r in sorted(S):
        bad = False
        if "ra" in rules and not any(x in supp for x in s.cats[r]):
            bad = True
        if "fg" in rules and not all(W[x] for x in s.reactions[r][0]):
            bad = True
        if bad:
            out.append(r)
    return out


def single_deletions(s, rules, stream):
    """Rule 5: delete one violator at a time, chosen by the stream, until none is left."""
    S = set(range(len(s.reactions)))
    while True:
        v = violators(s, S, rules)
        if not v:
            return sorted(S)
        S.discard(v[stream.below(len(v))])


def closure_bfs(s, S):
    """cl_S(F), breadth first: a reaction fires when its last missing reactant arrives (rule 7)."""
    W = bytearray(s.m)
    missing, waiting = {}, {}
    for r in S:
        A = set(s.reactions[r][0])
        missing[r] = len(A)
        for x in A:
            waiting.setdefault(x, []).append(r)
    queue = []
    for x in s.food:
        if not W[x]:
            W[x] = 1
            queue.append(x)
    ready = [r for r, c in missing.items() if c == 0]
    while queue or ready:
        while queue:
            x = queue.pop()
            for r in waiting.get(x, ()):
                missing[r] -= 1
                if missing[r] == 0:
                    ready.append(r)
        while ready:
            r = ready.pop()
            for y in s.reactions[r][1]:
                if not W[y]:
                    W[y] = 1
                    queue.append(y)
    return W


def reference(s, active, stream):
    """Rule 7: delete violators of (R1) or (R2) in seeded batches until none is left."""
    S = set(active)
    rounds = 0
    while True:
        v = violators(s, S, ("ra", "fg"))
        if not v:
            return sorted(S), rounds
        rounds += 1
        chosen = [r for r in v if stream.below(2)]
        if not chosen:
            chosen = [v[stream.below(len(v))]]
        S.difference_update(chosen)


def is_raf(s, S):
    """By the definitions of Section 3, with the breadth-first closure."""
    if not S:
        return False
    supp = set()
    for r in S:
        supp |= set(s.reactions[r][0]) | set(s.reactions[r][1])
    if not all(any(x in supp for x in s.cats[r]) for r in S):
        return False
    W = closure_bfs(s, S)
    return all(all(W[x] for x in s.reactions[r][0]) for r in S)


def irreducible(s, maxraf):
    """Rule 4: Theorem 6.1's proof."""
    left = list(maxraf)
    runs = 0
    for r in list(maxraf):
        rest = [q for q in left if q != r]
        if not rest:
            continue
        runs += 1
        if raf_algorithm(s, rest)[0]:
            left = rest
    return left, runs


def bound(k):
    return k ** 3 + 4 * k ** 2


# ---------------------------------------------------------------- the jobs

def small_job(args):
    seed, lo, hi = args
    out = []
    for i in range(lo, hi):
        s, params = small_system(seed, i)
        k = len(s.reactions)
        rafs, ra_union, fg_union = exhaustive(s)
        union = 0
        for S in rafs:
            union |= S
        got, passes, checks = raf_algorithm(s)
        c1 = to_mask(got) == union
        c2 = None
        irr_size = None
        if rafs:
            irr, _ = irreducible(s, got) if got else ([], 0)
            im = to_mask(irr)
            c2 = im in set(rafs) and not any(S != im and S & im == S for S in rafs)
            irr_size = len(irr)
        st = Stream(seed, f"hs2004/lemma51/{i}")
        g1 = to_mask(reduce_to_ra(s))
        g2 = to_mask(single_deletions(s, ("ra",), st))
        d1 = to_mask(single_deletions(s, ("fg",), st))
        c3 = g1 == ra_union and g2 == ra_union and d1 == fg_union
        later = to_mask(raf_algorithm(s, fault="later")[0]) != union
        row = {"i": i, "k": k, "raf": bool(rafs), "max": bin(union).count("1"), "c1": c1, "c2": c2, "c3": c3,
               "passes": passes, "checks": checks, "passes_ok": passes <= k, "checks_ok": checks <= bound(k),
               "irr": irr_size, "later_differs": later, **params}
        if i < SMALL_REFERENCE:
            ref, _ = reference(s, range(k), Stream(seed, f"hs2004/reference-small/{i}"))
            row["reference_ok"] = to_mask(ref) == union
            row["faults"] = {f: to_mask(raf_algorithm(s, fault=f)[0]) != union
                             for f in ("later", "one-pass", "one-sweep")}
        if i < SMALL_SETS:
            r2, ra2, fg2 = exhaustive_sets(s)
            row["sets_ok"] = ({to_mask(S) for S in r2} == set(rafs) and to_mask(ra2) == ra_union
                              and to_mask(fg2) == fg_union)
        out.append(row)
    return out


_MODELS = {}


def polymer_model(n):
    if n not in _MODELS:
        _MODELS[n] = polymer_reactions(n)
    return _MODELS[n]


def polymer_job(args):
    seed, n, f, j = args
    reactions = polymer_model(n)
    m = (1 << (n + 1)) - 2
    cats = polymer_catalysts(polymer_rng(seed, n, f, j), m, len(reactions), f)
    s = System.__new__(System)
    s.m, s.food, s.reactions, s.cats = m, tuple(range(6)), reactions, cats
    k = len(reactions)
    got, passes, checks = raf_algorithm(s)
    ref, rounds = reference(s, range(k), Stream(seed, f"hs2004/reference/n{n}/f{f[0]}-{f[1]}/{j}"))
    row = {"n": n, "f": f"{f[0]}/{f[1]}", "j": j, "k": k, "catalysations": sum(len(c) for c in cats),
           "max": len(got), "c4": got == ref, "passes": passes, "checks": checks, "passes_ok": passes <= k,
           "checks_ok": checks <= bound(k), "reference_rounds": rounds, "raf_ok": (not got) or is_raf(s, got)}
    if 1 <= len(got) <= IRREDUCIBLE_MAX:
        irr, runs = irreducible(s, got)
        st = Stream(seed, f"hs2004/irreducible/n{n}/f{f[0]}-{f[1]}/{j}")
        loses = all(not reference(s, [q for q in irr if q != r], st)[0] for r in irr)
        row.update({"irr": len(irr), "irr_runs": runs, "c5": is_raf(s, irr) and loses})
    return row


# ---------------------------------------------------------------- controls

def controls_from(small_rows, polymer_rows):
    ctl = {}
    ctl["bitmask search equals the set-based search on 300 small systems"] = all(
        r["sets_ok"] for r in small_rows if "sets_ok" in r) and sum("sets_ok" in r for r in small_rows) == SMALL_SETS
    ok = True
    for n in range(2, 7):
        ours = polymer_reactions(n)
        if set(ours) != polymer_reactions_enumerated(n) or len(set(ours)) != len(ours):
            ok = False
        if (1 << (n + 1)) - 2 != len({x for A, B in ours for x in A + B}):
            ok = False
    ctl["the polymer reactions equal an enumeration of every (a, b), n = 2 to 6, |X(n)| = 2^(n+1) - 2"] = ok
    ref = [r for r in small_rows if "reference_ok" in r]
    ctl["the reference equals exhaustive search on 2,000 small systems"] = (
        len(ref) == SMALL_REFERENCE and all(r["reference_ok"] for r in ref))
    for fault, words in (("later", "the later reading of RA"), ("one-pass", "one pass of the three routines"),
                         ("one-sweep", "ComputeClosure after one sweep")):
        ctl[f"planted fault caught by exhaustive search: {words}"] = any(r["faults"][fault] for r in ref)
    ok = True
    for n in POLYMER_N:
        rows = [r for r in polymer_rows if r["n"] == n]
        m = (1 << (n + 1)) - 2
        mean = sum(m * float(Fraction(r["f"])) for r in rows)
        var = sum(m * r["k"] * (float(Fraction(r["f"])) / r["k"]) * (1 - float(Fraction(r["f"])) / r["k"])
                  for r in rows)
        if abs(sum(r["catalysations"] for r in rows) - mean) > 5 * math.sqrt(var):
            ok = False
    ctl["catalysations on the polymer instances within five standard errors of expectation at every n"] = ok
    return ctl


# ---------------------------------------------------------------- the run

def run(seed, results="results", workers=WORKERS):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    small_tasks = [(seed, lo, min(lo + SMALL_CHUNK, SMALL)) for lo in range(0, SMALL, SMALL_CHUNK)]
    polymer_tasks = [(seed, n, f, j) for n in reversed(POLYMER_N) for f in POLYMER_F for j in range(POLYMER_EACH)]
    if workers > 1:
        with multiprocessing.get_context("fork").Pool(workers) as pool:
            polymer_rows = list(pool.imap(polymer_job, polymer_tasks, chunksize=1))
            small_rows = [row for chunk in pool.imap(small_job, small_tasks, chunksize=1) for row in chunk]
    else:
        polymer_rows = [polymer_job(t) for t in polymer_tasks]
        small_rows = [row for t in small_tasks for row in small_job(t)]
    polymer_rows.sort(key=lambda r: (r["n"], Fraction(r["f"]), r["j"]))

    ctl = controls_from(small_rows, polymer_rows)
    if not all(ctl.values()):
        raise AssertionError(f"a control failed: {[k for k, v in ctl.items() if not v]}")

    with_raf = [r for r in small_rows if r["raf"]]
    irr_poly = [r for r in polymer_rows if "c5" in r]
    cond = {
        "small systems: the result is the union of the RAF sets": all(r["c1"] for r in small_rows),
        "small systems: the irreducible RAF is an RAF with no RAF proper subset": all(r["c2"] for r in with_raf),
        "small systems: g(R) the largest RA set (both ways), d(R) the largest F-generated set":
            all(r["c3"] for r in small_rows),
        "polymer instances: the result is the reference's": all(r["c4"] for r in polymer_rows),
        "polymer instances: the irreducible RAF is an RAF and loses it without any one reaction":
            all(r["c5"] for r in irr_poly),
        "every run: at most |R| passes": all(r["passes_ok"] for r in small_rows + polymer_rows),
        "every run: at most |R|^3 + 4|R|^2 checks": all(r["checks_ok"] for r in small_rows + polymer_rows),
    }

    ex = example_system()
    ex_got, ex_passes, ex_checks = raf_algorithm(ex)
    ex_irr, _ = irreducible(ex, ex_got) if ex_got else ([], 0)
    names = ("r1", "r2", "r3", "r4")

    share, means, irr_share = [], [], []
    for n in POLYMER_N:
        parts, mparts = [], []
        for f in POLYMER_F:
            rows = [r for r in polymer_rows if r["n"] == n and r["f"] == f"{f[0]}/{f[1]}"]
            parts.append(str(sum(r["max"] > 0 for r in rows)))
            sizes = [r["max"] for r in rows if r["max"]]
            mparts.append(f"{sum(sizes) / len(sizes):.0f}" if sizes else "-")
        share.append(f"{n}: " + "/".join(parts))
        means.append(f"{n}: " + "/".join(mparts))
    ratios = [r["irr"] / r["max"] for r in irr_poly]
    pts = [(math.log(r["k"]), math.log(r["checks"])) for r in polymer_rows]
    mx = sum(x for x, _ in pts) / len(pts)
    my = sum(y for _, y in pts) / len(pts)
    slope = sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x, _ in pts)
    max_pass_ratio = max(r["passes"] / r["k"] for r in small_rows + polymer_rows)
    max_check_ratio = max(r["checks"] / bound(r["k"]) for r in small_rows + polymer_rows)
    biggest = max(polymer_rows, key=lambda r: r["k"])

    values = {
        "small": (f"{len(small_rows)} systems (3-7 molecules, 1-12 reactions): result = union of exhaustive RAFs in "
                  f"{sum(r['c1'] for r in small_rows)}"),
        "small_raf": (f"{len(with_raf)} of {len(small_rows)} with an RAF; largest RAF mean "
                      f"{sum(r['max'] for r in with_raf) / max(1, len(with_raf)):.2f} reactions"),
        "irreducible_small": (f"irreducible RAF exact in {sum(bool(r['c2']) for r in with_raf)} of {len(with_raf)}; "
                              f"smaller than the largest in {sum(r['irr'] < r['max'] for r in with_raf)}"),
        "lemma51": f"g(R) and d(R) the largest RA and F-generated sets in {sum(r['c3'] for r in small_rows)}",
        "polymer": (f"{len(polymer_rows)} instances, n = 5..10, f = 1, 5/4, 3/2, 2: result = reference in "
                    f"{sum(r['c4'] for r in polymer_rows)}; an RAF by definition in "
                    f"{sum(r['raf_ok'] for r in polymer_rows)}"),
        "polymer_raf": f"{sum(r['max'] > 0 for r in polymer_rows)} of {len(polymer_rows)} with an RAF",
        "irreducible_polymer": (f"irreducible RAF checked in {sum(bool(r['c5']) for r in irr_poly)} of "
                                f"{len(irr_poly)} (largest RAF 1-{IRREDUCIBLE_MAX} reactions)"),
        "passes": (f"passes at most {max(r['passes'] for r in small_rows + polymer_rows)}; largest passes/|R| "
                   f"{max_pass_ratio:.3f}"),
        "checks": (f"largest checks/(|R|^3 + 4|R|^2) {max_check_ratio:.2e}; n = {biggest['n']}: |R| = "
                   f"{biggest['k']}"),
        "example": (f"Section 2's example: largest RAF {{{', '.join(names[r] for r in ex_got)}}}, irreducible "
                    f"{{{', '.join(names[r] for r in ex_irr)}}}, {ex_passes} passes"),
        "share_raf": "with an RAF of 10 at f = 1/1.25/1.5/2: " + "; ".join(share),
        "maxraf_mean": "mean largest RAF (reactions): " + "; ".join(means),
        "irreducible_share": (f"irreducible/largest mean {sum(ratios) / max(1, len(ratios)):.3f} over "
                              f"{len(ratios)}" if ratios else "none computed"),
        "slope": f"log checks on log |R|: slope {slope:.2f} over {len(pts)} instances",
        "later_reading": (f"food may catalyse: largest RAF differs in {sum(r['later_differs'] for r in small_rows)} "
                          f"of {len(small_rows)}"),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"test": TEST, "conditions": cond, "controls": ctl,
              "example": {"result": [names[r] for r in ex_got], "irreducible": [names[r] for r in ex_irr],
                          "passes": ex_passes, "checks": ex_checks},
              "polymer": polymer_rows,
              "small_summary": {"systems": len(small_rows), "with_raf": len(with_raf),
                                "by_reactions": {str(k): [sum(1 for r in small_rows if r["k"] == k),
                                                          sum(1 for r in with_raf if r["k"] == k)]
                                                 for k in range(1, REACTIONS_MAX + 1)},
                                "failures": [r for r in small_rows if not (r["c1"] and r["c3"]
                                                                           and r["c2"] in (None, True))][:50]},
              "slope": slope, "max_pass_ratio": max_pass_ratio, "max_check_ratio": max_check_ratio}
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
        sys.exit(f"hs2004: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
