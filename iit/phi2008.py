#!/usr/bin/env python3
"""Balduzzi & Tononi's integrated information (2008): a counter, its replay, and elements that only copy.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:829df225aeb1af24) is from Balduzzi and
Tononi, "Integrated Information in Discrete Dynamical Systems: Motivation and Theoretical Framework", PLoS
Computational Biology 4(6), e1000091 (2008): "(ii) phi varies for systems with identical or similar surface dynamics
depending on the underlying causal architecture, being low for systems that merely copy or replay activity states."

Its registered test: refuted if, with phi as the paper defines it (effective information across the total partition
and every bipartition, the minimum information partition by normalized effective information, inputs from outside a
part averaged at maximum entropy): the binary counter of Figure 11, four memoryless interacting elements, has phi = 0
in any of its 16 states, or phi within 0.01 of 0.19 bits in none; or its replay by four non-interacting elements has
phi > 0 in any state; or the AND-gates of Figure 1 with three elements copying them (Figure 6) have phi > 0 as a whole
in any state they can enter.

Everything is computed from the paper's own definitions (Models: Equations 1 and 2, the normalization, the minimum
information partition), exactly as written, by enumeration, in the standard library. No code or data is read. Every
rule below was fixed before any seed existed.

1. A network of binary elements, each with a probability of firing at t = 1 given every output of the network at
   t = 0 (0 or 1 for a deterministic element). For a system X (a subset of the network) in state x1: the a priori
   repertoire is uniform on X's outputs at t = 0; the a posteriori repertoire p(X0 -> x1) is Bayes' rule with that
   prior, proportional to the probability that X's elements output x1, averaged at maximum entropy over the outputs
   at t = 0 of every element outside X (and over any element's private input, which the element's probability of
   firing already averages).
2. Effective information across the total partition: H(p_max(X0)) - H(p(X0 -> x1)). Across a bipartition {M1, M2} of
   X: the relative entropy of p(X0 -> x1) to the product of the parts' a posteriori repertoires, each part's computed
   as in rule 1 with everything outside it averaged (Equation 2A). Logarithms to base 2.
3. The normalization: the total partition by the number of elements of X, a bipartition by the size of its smaller
   part. The minimum information partition minimizes normalized effective information over the total partition and
   every bipartition (as the paper's Results compute it); on a tie, the lowest un-normalized effective information,
   as the paper states. phi is the effective information across it. Values within 1e-9 are equal; a phi within 1e-9
   of zero is zero.
4. The systems (element 1 first; a state is written n1 n2 ...):
   - the counter (Figure 11A and B): n1 -> not n1; n2 -> n2 xor n1; n3 -> n3 xor (n1 and n2); n4 -> n4 xor (n1 and
     n2 and n3), which counts 0000, 1000, 0100, 1100, ... (n1 the lowest bit) through all 16 states;
   - its replay (Figure 11C): each element reads only its own output and a private memory of where it is in its own
     run, n1 alternating 0 and 1, n2 runs of two, n3 of four, n4 of eight; averaged at maximum entropy over the
     memory, n_k flips with probability 1 / 2^(k-1);
   - the AND-gates (Figure 1): three elements, each the AND of the other two;
   - the AND-gates with three elements copying them (Figure 6): n4, n5 and n6 output what n1, n2 and n3 output the
     instant before.
5. The test's three conditions: the counter's phi above zero in all 16 states and within 0.01 of 0.19 bits in at
   least one; the replay's phi zero in all 16 states; the six elements of Figure 6, as one system, with phi zero in
   every state they can enter (the 8 images of their update). test_passed is 1 if all three hold.
6. Beside the test, none of it counted: the minimum information partitions; the AND-gates' phi alone; phi with exact
   ties broken towards the total partition instead (the reading that gives the 4 bits and 3 bits the paper prints).

Controls (controls_passed counts those that behave as stated), the paper's other printed values: the AND-gates
entering 001 from 110 generate 3 bits of effective information, with 110 the only cause (Figure 1), and 1 bit
entering 000 (Figure 2B); a couple, two elements copying each other, 2 bits (Figure 2A); elements that fire whatever
happens, and elements firing at random, 0 bits (Figures 2C and 2D); two disjoint couples 4 bits of effective
information and phi = 0 (Figure 3); the parity system (all-to-all with self-connections) phi = 1 bit in every state,
for 3, 4 and 5 elements (Figure 14A); an element that fires only if all eight others fired, firing, phi = 8 bits across
the total partition (Figure 7C); and the counter's phi unchanged in every state when its elements are relabelled by
a seed-drawn permutation.

What it cannot check: the scrambled sequence of Figure 11's discussion (printed as an image, its wiring in the
supplement), Text S1's details beyond the main text, and the counter's 4 bits, which the paper's stated tie rule does
not give (rule 3; see the beside value).

Writes results/outputs.json and results/detail.json. Run with: python3 iit/phi2008.py
"""

import itertools
import json
import math
import os
import random
import re
import sys

EPS = 1e-9
LIMIT = 200
OUTPUTS = ("counter_phi", "counter_min", "counter_near_019", "replay_max", "copies_max", "copies_states", "and_gates",
           "ties_to_total", "controls_passed", "controls_total", "test_passed")


class Network:
    """n binary elements; fire(k, x0) is the probability that element k fires at t = 1 given outputs x0 at t = 0."""

    def __init__(self, n, fire):
        self.n = n
        self.fire = fire
        self.past = list(itertools.product((0, 1), repeat=n))
        self.p = {x0: [fire(k, x0) for k in range(n)] for x0 in self.past}

    def update(self, x0):
        """The next state of a deterministic network."""
        out = []
        for v in self.p[x0]:
            if v not in (0, 1):
                raise ValueError("not deterministic")
            out.append(int(v))
        return tuple(out)

    def repertoire(self, part, x1):
        """Rule 1: the a posteriori repertoire over the part's outputs at t = 0, given its outputs in x1."""
        rep = {}
        for x0 in self.past:
            like = 1.0
            for k in part:
                q = self.p[x0][k]
                like *= q if x1[k] else 1.0 - q
            if like:
                key = tuple(x0[k] for k in part)
                rep[key] = rep.get(key, 0.0) + like
        tot = sum(rep.values())
        if tot <= 0:
            raise ValueError("a state the part cannot enter")
        return {k: v / tot for k, v in rep.items()}


def entropy(rep):
    return -sum(p * math.log2(p) for p in rep.values() if p > 0)


def candidates(net, system, x1):
    """Rules 2 and 3: (name, effective information, normalized) for the total partition and every bipartition."""
    system = tuple(system)
    whole = net.repertoire(system, x1)
    m = len(system)
    out = [("total", m - entropy(whole), (m - entropy(whole)) / m)]
    for r in range(1, m // 2 + 1):
        for a in itertools.combinations(system, r):
            b = tuple(k for k in system if k not in a)
            if 2 * r == m and a > b:
                continue
            ra, rb = net.repertoire(a, x1), net.repertoire(b, x1)
            ia = [system.index(k) for k in a]
            ib = [system.index(k) for k in b]
            ei = 0.0
            for key, p in whole.items():
                if p <= 0:
                    continue
                q = ra.get(tuple(key[i] for i in ia), 0.0) * rb.get(tuple(key[i] for i in ib), 0.0)
                if q <= 0:
                    ei = math.inf
                    break
                ei += p * math.log2(p / q)
            out.append(((a, b), ei, ei / min(len(a), len(b))))
    return out


def mip(cands, ties_to_total=False):
    """Rule 3: the minimum normalized effective information; ties by the lowest un-normalized value (or, beside the
    test, to the total partition)."""
    low = min(c[2] for c in cands)
    tied = [c for c in cands if c[2] <= low + EPS]
    if ties_to_total and any(c[0] == "total" for c in tied):
        best = next(c for c in tied if c[0] == "total")
    else:
        best = min(tied, key=lambda c: c[1])
    return best, len(tied)


def phi(net, system, x1, ties_to_total=False):
    best, tied = mip(candidates(net, system, x1), ties_to_total)
    v = best[1]
    return (0.0 if abs(v) <= EPS else v), best[0], tied


def name(part, labels):
    if part == "total":
        return "total"
    a, b = part
    return "{" + ",".join(labels[k] for k in a) + "}|{" + ",".join(labels[k] for k in b) + "}"


def bits(x):
    return "".join(map(str, x))


# ---------------------------------------------------------------- the systems (rule 4)

def counter():
    def fire(k, x):
        n1, n2, n3, n4 = x
        return (1 - n1, n2 ^ n1, n3 ^ (n1 & n2), n4 ^ (n1 & n2 & n3))[k]
    return Network(4, fire)


def replay():
    def fire(k, x):
        flip = 1.0 / 2 ** k                      # n1 always flips; n2 every 2nd update, n3 every 4th, n4 every 8th
        return 1.0 - flip if x[k] else flip
    return Network(4, fire)


def and_gates():
    return Network(3, lambda k, x: (x[1] & x[2], x[0] & x[2], x[0] & x[1])[k])


def copied():
    return Network(6, lambda k, x: (x[1] & x[2], x[0] & x[2], x[0] & x[1], x[0], x[1], x[2])[k])


def permuted(net, perm):
    """The same network with element i renamed perm[i]."""
    inv = {perm[i]: i for i in range(net.n)}

    def fire(k, y):
        x = tuple(y[perm[i]] for i in range(net.n))
        return net.fire(inv[k], x)
    return Network(net.n, fire)


# ---------------------------------------------------------------- controls

def controls(rng):
    ctl, seen = {}, {}
    g = and_gates()
    rep = g.repertoire((0, 1, 2), (0, 0, 1))
    ei1 = 3 - entropy(rep)
    ctl["Figure 1: the AND-gates entering 001 generate 3 bits, 110 the only cause"] = (
        abs(ei1 - 3) <= EPS and rep == {(1, 1, 0): 1.0})
    ei0 = 3 - entropy(g.repertoire((0, 1, 2), (0, 0, 0)))
    ctl["Figure 2B: entering 000, 1 bit"] = abs(ei0 - 1) <= EPS
    couple = Network(2, lambda k, x: x[1 - k])
    eis = [2 - entropy(couple.repertoire((0, 1), s)) for s in couple.past]
    ctl["Figure 2A: a couple, 2 bits in every state"] = all(abs(e - 2) <= EPS for e in eis)
    always = Network(3, lambda k, x: 1)
    noise = Network(3, lambda k, x: 0.5)
    ctl["Figures 2C and 2D: always firing, and firing at random, 0 bits"] = (
        abs(3 - entropy(always.repertoire((0, 1, 2), (1, 1, 1)))) <= EPS
        and all(abs(3 - entropy(noise.repertoire((0, 1, 2), s))) <= EPS for s in noise.past))
    two = Network(4, lambda k, x: x[(1, 0, 3, 2)[k]])
    st = (1, 0, 0, 1)
    ei4 = 4 - entropy(two.repertoire((0, 1, 2, 3), st))
    p2, part2, _ = phi(two, (0, 1, 2, 3), st)
    ctl["Figure 3: two disjoint couples, 4 bits of effective information and phi = 0"] = (
        abs(ei4 - 4) <= EPS and p2 == 0.0 and part2 == ((0, 1), (2, 3)))
    par = {}
    for n in (3, 4, 5):
        net = Network(n, lambda k, x: sum(x) % 2)
        reach = sorted({net.update(x) for x in net.past})
        par[n] = sorted({round(phi(net, tuple(range(n)), s)[0], 9) for s in reach})
    ctl["Figure 14A: the parity system, phi = 1 bit in every state, 3 to 5 elements"] = all(v == [1.0] for v in par.values())
    top = Network(9, lambda k, x: (1.0 if all(x[1:]) else 0.0) if k == 0 else 0.5)
    p7, part7, _ = phi(top, tuple(range(9)), (1,) + (0,) * 8)
    ctl["Figure 7C: an element firing only if all eight others fired, phi = 8 bits across the total partition"] = (
        abs(p7 - 8) <= EPS and part7 == "total")
    perm = list(range(4))
    rng.shuffle(perm)
    c = counter()
    pc = permuted(c, perm)
    same = all(abs(phi(c, (0, 1, 2, 3), s)[0] - phi(pc, (0, 1, 2, 3), tuple(s[i] for i in sorted(range(4), key=lambda i: perm[i])))[0]) <= EPS
               for s in c.past)
    ctl["the counter's phi is unchanged in every state when its elements are relabelled"] = same
    seen["permutation"] = perm
    seen["parity"] = {str(k): v for k, v in par.items()}
    seen["figure_7c"] = {"phi": p7, "mip": part7 if part7 == "total" else name(part7, [f"n{i + 1}" for i in range(9)])}
    return ctl, seen


# ---------------------------------------------------------------- the verdict

def conditions(counter_phis, replay_phis, copies_phis):
    return {"the counter's phi above zero in all 16 states": all(v > 0 for v in counter_phis.values()),
            "the counter's phi within 0.01 of 0.19 bits in at least one state":
            any(abs(v - 0.19) <= 0.01 for v in counter_phis.values()),
            "the replay's phi zero in all 16 states": all(v == 0.0 for v in replay_phis.values()),
            "Figure 6's six elements, as one system, with phi zero in every state they can enter":
            all(v == 0.0 for v in copies_phis.values())}


def run(seed, results="results"):
    rng = random.Random(int(seed, 16))
    labels4 = ["n1", "n2", "n3", "n4"]
    labels6 = ["n1", "n2", "n3", "n4", "n5", "n6"]
    c, r, g, f = counter(), replay(), and_gates(), copied()
    states16 = sorted(c.past)
    cyc = [states16[0]]
    while len(cyc) < 16:
        cyc.append(c.update(cyc[-1]))
    counter_rows, counter_phis, counter_tie = [], {}, {}
    for s in states16:
        v, part, tied = phi(c, (0, 1, 2, 3), s)
        vt, partt, _ = phi(c, (0, 1, 2, 3), s, ties_to_total=True)
        counter_phis[s], counter_tie[s] = v, vt
        counter_rows.append({"state": bits(s), "phi": round(v, 6), "mip": name(part, labels4), "tied": tied,
                             "phi_ties_to_total": round(vt, 6), "mip_ties_to_total": name(partt, labels4)})
    replay_phis = {s: phi(r, (0, 1, 2, 3), s)[0] for s in states16}
    reach6 = sorted({f.update(x) for x in f.past})
    copies_rows, copies_phis = [], {}
    for s in reach6:
        v, part, tied = phi(f, tuple(range(6)), s)
        a, apart, _ = phi(f, (0, 1, 2), s)
        at, _, _ = phi(f, (0, 1, 2), s, ties_to_total=True)
        copies_phis[s] = v
        copies_rows.append({"state": bits(s), "phi_whole": round(v, 6), "mip_whole": name(part, labels6),
                            "phi_and_gates": round(a, 6), "mip_and_gates": name(apart, labels6),
                            "phi_and_gates_ties_to_total": round(at, 6)})
    reach3 = sorted({g.update(x) for x in g.past})
    gates = {bits(s): (round(phi(g, (0, 1, 2), s)[0], 6), round(phi(g, (0, 1, 2), s, ties_to_total=True)[0], 6))
             for s in reach3}
    ctl, seen = controls(rng)
    cond = conditions(counter_phis, replay_phis, copies_phis)

    groups = {}
    for row in counter_rows:
        groups.setdefault((row["phi"], row["mip"]), []).append(row["state"])
    counter_words = "; ".join(f"{p:g} in {len(v)} states ({m})" for (p, m), v in sorted(groups.items()))
    tgroups = {}
    for row in counter_rows:
        tgroups.setdefault(row["phi_ties_to_total"], []).append(row["state"])
    values = {
        "counter_phi": counter_words,
        "counter_min": round(min(counter_phis.values()), 9),
        "counter_near_019": sum(1 for v in counter_phis.values() if abs(v - 0.19) <= 0.01),
        "replay_max": round(max(replay_phis.values()), 9),
        "copies_max": round(max(copies_phis.values()), 9),
        "copies_states": len(reach6),
        "and_gates": "; ".join(f"{s}: {v[0]:g}" for s, v in gates.items()) + " (alone)",
        "ties_to_total": ("counter " + ", ".join(f"{p:g} in {len(v)}" for p, v in sorted(tgroups.items()))
                          + "; AND-gates " + ", ".join(f"{s}: {v[1]:g}" for s, v in gates.items())),
        "controls_passed": sum(bool(v) for v in ctl.values()), "controls_total": len(ctl),
        "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"conditions": cond, "controls": ctl, "controls_seen": seen, "counter": counter_rows,
              "counter_cycle": [bits(s) for s in cyc], "replay": {bits(s): v for s, v in replay_phis.items()},
              "copies": copies_rows, "and_gates": gates}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    out, _ = run(seed)
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
