#!/usr/bin/env python3
"""Autocatalytic sets in Kauffman's binary polymer model, counted in seeded instances, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:2958e6ed6a52baca) is from Kauffman,
"Autocatalytic sets of proteins", J. Theor. Biol. 119(1), 1986: "Because, as M increases, the ratio of reactions
among the possible polypeptides to polypeptides rises rapidly, the existence of such autocatalytic subsets is
assured for any fixed probability of catalysis." Its registered test: refuted if, in Kauffman's model (all binary
polymers of length 1 to M; food the six of length 1 or 2; every ligation forming a polymer of length up to M, and
its reverse cleavage; each polymer catalysing each reaction independently with probability P), fewer than 190 of
200 seed-drawn instances contain an RAF set (every reaction catalysed by a member or food, every reactant
producible from food) for any of P = 1e-2, 1e-3 and 1e-4 at M = 9, 12 and 15 respectively, the least M with
P((M-2)2^(M+1)+4) >= 4M. Scope: construction. Fidelity: adapted (RAF in the sense of Hordijk and Steel; binary
alphabet and food of length <= 2 as Mossel and Steel 2005 describe the model; transpeptidation omitted).

The inputs are three example systems that CatReNet (husonlab/catrenet, GPL-3.0; Huson, Xavier and Steel,
Bioinformatics 2024) ships, at commit f3d5f23, each checked against its SHA-256 and read as data; none of
CatReNet's code is run. Every rule below was fixed before any seed existed.

1. Molecules: every binary string of length 1 to M, the string of length L and value v (its first character the
   most significant bit) numbered (2^L - 2) + v, so |X| = 2^(M+1) - 2. The food is the six of length 1 and 2,
   numbers 0 to 5.
2. Reactions, each one-way: for every polymer x of length L from 2 to M and every split k from 1 to L - 1, the
   ligation a + b -> x, a the first k characters of x and b the rest, numbered j in order of L, then k, then v
   (0 <= j < n, n = (M-2)2^(M+1) + 4); and its reverse, the cleavage x -> a + b, numbered n + j. |R| = 2n, checked.
3. Catalysis: each of the |R| |X| (reaction, molecule) pairs independently with probability P, drawn exactly. The
   pairs are numbered r |X| + x; the gaps between successes in a sequence of independent Bernoulli(P) trials are
   independent Geometric(P) (trials up to and including the next success), so the catalysed numbers are the partial
   sums of Geometric(P) draws, less one, kept while below |R| |X|; int64 throughout. (A draw of 0, which numpy's
   inversion gives only for an exponential draw of exactly 0, probability about 2^-53 a draw, is read as 1.)
4. Randomness, only from ECDYSIS_SEED: instance i of a setting labelled s draws from numpy's
   Generator(PCG64(int.from_bytes(SHA-256(seed bytes || "|" || s || "|" || str(i)), "big"))), so each instance is
   fixed by the seed, its label and its number alone, however the work is scheduled. The labels are
   "raf/test/p2/m9" (P = 1e-2, M = 9) and the like, "raf/curve/p4/m14", and "raf/control/half/m15".
5. RAF, by Hordijk and Steel's maxRAF reduction: start with every reaction; repeat {take the closure of the food
   under the current reactions (a reaction fires when all its reactants are present, adding its products, until
   nothing is added); drop every reaction with a reactant outside the closure or no catalyst inside it} until
   nothing is dropped. What remains is the maxRAF, and the instance contains an RAF if and only if it is not empty.
6. CAF (constructively autocatalytic; reported beside the test, never in it): from the food, take every reaction
   whose reactants and at least one catalyst are all present, add their products, and repeat until no reaction is
   added. The reactions taken are the maxCAF; a CAF is an RAF, so an instance with a CAF has an RAF.
7. What runs. The test: 200 instances at each of (P, M) = (1e-2, 9), (1e-3, 12) and (1e-4, 15), M derived here as
   the least with P n >= 4M and checked against the registered values. The curves: 200 instances at every M from 3
   to one below that M, for each P. The control, which must fail: 200 instances at each of M = 9, 12 and 15 with
   P = 0.5/|R(M)|, half a reaction catalysed per polymer on average. Two worker processes; the results are
   gathered in a fixed order, so the outputs are the same bits serially or pooled, and nothing reads the clock.
8. Validation, in the run: the three CatReNet examples are read in CatReNet's documented format and run through
   the same max_raf and max_caf as every instance (a two-way reaction as its two one-way halves with the same
   catalysts, as CatReNet's Reaction.allAsForward splits it, and counted once); their reaction and food counts and
   their maxRAF and maxCAF sizes must be what CatReNet's README states (README.md, "Provided datasets", lines 245,
   247-249 and 256-257 at f3d5f23). The polymer model's builder is tested against the general form in
   tests/test_raf.py.

test_passed is 1 if at least 190 of the 200 test instances contain an RAF at each of the three (P, M), else 0.
control_ok (1 if fewer than 190 of 200 contain an RAF at each control M) and validation_ok are reported beside it.

What it cannot check:
- "assured ... as M increases": the claim is a limit; three (P, M) cannot show that an RAF stays certain at every
  larger M, or for every P;
- Kauffman's own model beyond this adaptation: his alphabet and food, transpeptidation, and his own graph criterion
  for autocatalytic closure are not run;
- chemistry: an RAF is a property of the reaction graph; whether such a set would form and persist at real
  concentrations and rates is not modelled;
- which RAFs: the maxRAF is found and its size reported, not the irreducible RAFs inside it. By the definition a
  single reaction among the food, catalysed by a food molecule, is an RAF and is counted; the maxRAF's share of
  the reactions is reported beside the count;
- CatReNet on these instances: the validation runs its three documented examples only.

Writes results/outputs.json, the 20 values a receipt carries (numbers, and strings of at most 200 characters), and
results/detail.json: every value computed and every instance's counts, uncut. raf/README.md says what each holds,
the runtime, and what the draws depend on.
"""

import os

for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_var, "1")   # one thread in each of the two worker processes

import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import multiprocessing  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
from collections import namedtuple  # noqa: E402
from fractions import Fraction  # noqa: E402

import numpy as np  # noqa: E402

# CatReNet's examples (husonlab/catrenet at f3d5f23eb9b4f56f5e27a6f1f11e56f26cbc4349, examples/example-0n.crs), each
# with what CatReNet's README.md at that commit states of it in "Provided datasets" (lines 245, 247-249, 256-257):
# (reactions, food items, maxRAF size, maxCAF size), a two-way reaction counted once, and the README's words.
INPUTS = (
    ("catrenet-example-00.crs", "767555d1080a7b74479a7e4afa53d2d5858bfcd9ea48275d3d35a641081697a1", (6, 3, 3, 0),
     "6 reactions, 3 food items, has a Max RAF of size 3 and no Max CAF"),
    ("catrenet-example-02.crs", "3504297a2cf675a47a080b3db786e627c0a34096afa67e20d591e258dda818c6", (5, 6, 5, 3),
     "uses binary polymers, has 5 reactions and 6 food items, has a Max RAF of size 5 and a Max CAF of size 3"),
    ("catrenet-example-08.crs", "5114ddf17894d56bd1a87319b5c19df902c247b5aacea587b3ced93be9c9c9c4", (17, 4, 17, 17),
     "uses binary polymers, has 17 two-way reactions and 4 foot items, is a Max RAF and a Max CAF"),
)
INSTANCES = 200          # instances per setting
REQUIRED = 190           # the test: at least 190 of 200 with an RAF at each (P, M)
PROBABILITIES = (("p2", Fraction(1, 100)), ("p3", Fraction(1, 1000)), ("p4", Fraction(1, 10000)))
REGISTERED = {"p2": 9, "p3": 12, "p4": 15}   # the registered test's M for each P
SMALLEST = 3             # the curves start at M = 3
CONTROL = Fraction(1, 2)  # the control's reactions catalysed per polymer, on average: P = CONTROL / |R(M)|
FOOD_LENGTH = 2          # the food: every string of length 1 and 2
WORKERS = 2
LIMIT = 200              # the archive's longest string output

# The 20 values results/outputs.json carries (the archive accepts at most 20 per receipt).
OUTPUTS = (
    "instances", "reactions_m15", "catalysts_mean_p4_m15",
    "raf_p2_m9", "raf_p3_m12", "raf_p4_m15", "caf_p2_m9", "caf_p3_m12", "caf_p4_m15", "maxraf_fraction_p4_m15",
    "curve_p2", "curve_p3", "curve_p4", "control_raf_m9", "control_raf_m12", "control_raf_m15", "control_ok",
    "validation_ok", "validation_sizes", "test_passed",
)


# ---------------------------------------------------------------- the general form

# A reaction system: molecules numbered 0 .. molecules - 1 and one-way reactions numbered 0 .. reactions - 1; food a
# boolean mask over the molecules; reactants and products each a pair (reaction, molecule) of equal-length int64
# arrays, one entry for each reactant or product of a reaction. Catalysis is a pair of the same kind, one entry for
# each (reaction, catalyst); any one catalyst present catalyses the reaction.
System = namedtuple("System", "molecules reactions food reactants products")


def pairs(lists):
    """(reaction, molecule) arrays from a list giving, for each reaction, a list of molecule numbers (repeats once)."""
    rows = [(r, m) for r, ms in enumerate(lists) for m in sorted(set(ms))]
    return (np.array([r for r, _ in rows], dtype=np.int64), np.array([m for _, m in rows], dtype=np.int64))


def system(molecules, food, reactions):
    """The general form of a system given as lists: food a list of molecule numbers, reactions a list of
    (reactants, products), each a list of molecule numbers."""
    for ms in [food] + [side for r in reactions for side in r]:
        if any(isinstance(m, bool) or not isinstance(m, int) or not 0 <= m < molecules for m in ms):
            raise ValueError("a molecule number out of range")
    mask = np.zeros(molecules, dtype=bool)
    mask[list(food)] = True
    return System(molecules, len(reactions), mask, pairs([r[0] for r in reactions]), pairs([r[1] for r in reactions]))


def present(entries, W, reactions):
    """For each reaction, whether every molecule paired with it in entries is in W (true for one with none)."""
    rxn, mol = entries
    return np.bincount(rxn[~W[mol]], minlength=reactions) == 0


def touched(entries, W, reactions):
    """For each reaction, whether some molecule paired with it in entries is in W."""
    rxn, mol = entries
    return np.bincount(rxn[W[mol]], minlength=reactions) > 0


def catalysed(catalysis, W, reactions):
    """For each reaction, whether one of its catalysts is in W."""
    return touched(catalysis, W, reactions)


def closure(S, alive):
    """The molecules made from the food by the reactions in alive (a mask): a reaction fires when all its reactants
    are present and adds its products, until nothing is added."""
    W = S.food.copy()
    rxn, mol = S.products
    while True:
        fire = alive & present(S.reactants, W, S.reactions)
        made = mol[fire[rxn]]
        if W[made].all():
            return W
        W[made] = True


def max_raf(S, catalysis):
    """Hordijk and Steel's reduction: (the maxRAF, a mask over the reactions; the closure of the food under it)."""
    alive = np.ones(S.reactions, dtype=bool)
    while True:
        W = closure(S, alive)
        keep = alive & present(S.reactants, W, S.reactions) & catalysed(catalysis, W, S.reactions)
        if np.array_equal(keep, alive):
            return alive, W
        alive = keep


def max_caf(S, catalysis):
    """From the food, every reaction whose reactants and at least one catalyst are present, taken with its products
    until no reaction is added: (the maxCAF, a mask over the reactions; the molecules present at the end)."""
    W = S.food.copy()
    taken = np.zeros(S.reactions, dtype=bool)
    rxn, mol = S.products
    while True:
        ready = present(S.reactants, W, S.reactions) & catalysed(catalysis, W, S.reactions)
        if np.array_equal(ready, taken):
            return taken, W
        taken = ready
        W[mol[taken[rxn]]] = True


# ---------------------------------------------------------------- Kauffman's model on binary polymers

def ligation_count(M):
    """n(M) = (M - 2) 2^(M+1) + 4, the ligations forming polymers of length 2 to M (the sum of (L - 1) 2^L)."""
    return (M - 2) * (1 << (M + 1)) + 4


def molecule_count(M):
    """|X| = 2^(M+1) - 2, the binary strings of length 1 to M."""
    return (1 << (M + 1)) - 2


def least_m(P):
    """The least M with P n(M) >= 4M, the registered test's M for a probability P (a Fraction)."""
    M = 1
    while P * ligation_count(M) < 4 * M:
        M += 1
    return M


def molecule_id(length, value):
    return (1 << length) - 2 + value


def molecule_name(i):
    """The binary string numbered i."""
    i = int(i)
    length = (i + 2).bit_length() - 1
    return format(i + 2 - (1 << length), f"0{length}b")


def ligations(M):
    """(left, right, product) as int64 arrays: every ligation forming a polymer of length 2 to M, in order of the
    product's length L, the split k, then the product's value v; left the first k characters, right the rest."""
    parts = ([], [], [])
    for L in range(2, M + 1):
        v = np.arange(1 << L, dtype=np.int64)
        for k in range(1, L):
            parts[0].append(molecule_id(k, 0) + (v >> (L - k)))
            parts[1].append(molecule_id(L - k, 0) + (v & ((1 << (L - k)) - 1)))
            parts[2].append(molecule_id(L, 0) + v)
    return tuple(np.concatenate(p) for p in parts)


_POLYMERS = {}


def polymer_system(M):
    """The model on binary polymers of length 1 to M in the general form: ligation j is reaction j and its reverse
    cleavage reaction n + j. Built once per M (and before the workers fork, so that they share it)."""
    if M not in _POLYMERS:
        if M < FOOD_LENGTH:
            raise ValueError(f"M = {M}: shorter than the food")
        left, right, product = ligations(M)
        n = left.size
        if n != ligation_count(M):
            raise AssertionError(f"M = {M}: {n} ligations, not (M-2)2^(M+1)+4 = {ligation_count(M)}")
        lig = np.arange(n, dtype=np.int64)
        cle = lig + n
        food = np.zeros(molecule_count(M), dtype=bool)
        food[:molecule_count(FOOD_LENGTH)] = True
        _POLYMERS[M] = System(molecule_count(M), 2 * n, food,
                              (np.concatenate([lig, lig, cle]), np.concatenate([left, right, product])),
                              (np.concatenate([lig, cle, cle]), np.concatenate([product, left, right])))
    return _POLYMERS[M]


# ---------------------------------------------------------------- the draws

def generator(seed, label, i):
    """numpy's Generator for instance i of the setting labelled label: PCG64 seeded with the 256-bit integer
    SHA-256(seed bytes || "|" || label || "|" || str(i))."""
    digest = hashlib.sha256(bytes.fromhex(seed) + b"|" + label.encode("ascii") + b"|" + str(i).encode("ascii")).digest()
    return np.random.Generator(np.random.PCG64(int.from_bytes(digest, "big")))


def catalysis_pairs(rng, reactions, molecules, p):
    """Every catalysed (reaction, molecule) pair, each of the reactions x molecules pairs independently with
    probability p, as (reaction, molecule) int64 arrays in order of r * molecules + x.

    The catalysed numbers are the partial sums of Geometric(p) draws, less one, below the total. The draws are taken
    in chunks of int(mu + 6 sqrt(mu)) + 64, mu = p * total, until a sum reaches the total; numpy draws an array of
    geometric variates one after another, so the chunking does not change which pairs are drawn. Each draw is
    clipped to [1, total + 1]: 0 is numpy's rare artefact (see the module's rule 3), and a gap past the total ends
    the draw whatever its size, so the clip keeps the sums in int64 without changing any pair.
    """
    total = reactions * molecules
    if not 0 < p <= 1 or total <= 0:
        raise ValueError("no pairs to draw")
    mu = p * total
    chunk = int(mu + 6 * math.sqrt(mu)) + 64
    if chunk * (total + 1) >= 1 << 63:
        raise OverflowError("the partial sums could leave int64")
    found, last = [], -1
    while True:
        gaps = rng.geometric(p, size=chunk)
        np.clip(gaps, 1, total + 1, out=gaps)
        sums = np.cumsum(gaps)
        sums += last
        if sums[-1] >= total:
            found.append(sums[:np.searchsorted(sums, total)])
            break
        found.append(sums)
        last = int(sums[-1])
    numbers = np.concatenate(found)
    return numbers // molecules, numbers % molecules


# ---------------------------------------------------------------- one instance, and the run

def label(kind, plabel, M):
    return f"raf/{kind}/{plabel}/m{M}"


def run_instance(job):
    """One instance: (catalysed pairs, reactions in the maxRAF, molecules in its closure, reactions in the maxCAF)."""
    seed, kind, plabel, p, M, i = job
    S = polymer_system(M)
    catalysis = catalysis_pairs(generator(seed, label(kind, plabel, M), i), S.reactions, S.molecules, p)
    raf, made = max_raf(S, catalysis)
    caf, _ = max_caf(S, catalysis)
    return (int(catalysis[0].size), int(raf.sum()), int(made.sum()), int(caf.sum()))


def cost(job):
    """A rough count of the work in a job, for scheduling only: the expected catalysed pairs plus the reactions."""
    _, _, _, p, M, _ = job
    R = 2 * ligation_count(M)
    return p * R * molecule_count(M) + R


def run_all(jobs):
    """Every job's result, in the order of jobs. The costliest start first, on two workers."""
    order = sorted(range(len(jobs)), key=lambda k: (-cost(jobs[k]), k))
    queue = [jobs[k] for k in order]
    pool = None
    try:
        pool = multiprocessing.get_context("fork").Pool(WORKERS)
        done = pool.imap(run_instance, queue, chunksize=1)
    except (OSError, ValueError, ImportError) as e:   # no fork, or no shared memory for the pool's locks
        print(f"raf/check.py: no worker pool ({e}); running serially", file=sys.stderr)
        done = map(run_instance, queue)
    results = [None] * len(jobs)
    try:
        for n, (k, r) in enumerate(zip(order, done), start=1):
            results[k] = r
            if n % 600 == 0 or n == len(jobs):
                print(f"raf/check.py: {n} of {len(jobs)} instances", file=sys.stderr)
    finally:
        if pool is not None:
            pool.terminate()
            pool.join()
    return results


# ---------------------------------------------------------------- the validation: CatReNet's examples

NAME = re.compile(r"[^\s+,|\[\]{}:&*()<>=]+")
NUMBER = re.compile(r"[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?")
ARROWS = (("<=>", True), ("<->", True), ("=>", False), ("->", False))


def load(path, sha256):
    """The text of an input, after its bytes are checked against the committed SHA-256."""
    with open(path, "rb") as f:
        data = f.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha256:
        sys.exit(f"{path}: sha256 {got}, not the committed {sha256}")
    return data.decode("utf-8")


def names(text, separators, what, side=False):
    """The molecule names in text. On a side of a reaction, an integer among names that are not all numbers is a
    coefficient (as CatReNet's Reaction.parse reads it), which is refused; names that are all numbers are names."""
    tokens = [t for t in re.split(separators, text.strip()) if t]
    for t in tokens:
        if not NAME.fullmatch(t):
            raise ValueError(f"{what}: {t!r} is not a molecule name")
    if side and not all(NUMBER.fullmatch(t) for t in tokens) and any(re.fullmatch(r"\d+", t) for t in tokens):
        raise ValueError(f"{what}: a stoichiometric coefficient, which this check does not read")
    return tokens


def parse_crs(text):
    """A CatReNet CRS file as (food, reactions), in the part of CatReNet's documented format (docs/index.md, section
    4, at f3d5f23) that its examples use: food a list of names; reactions a list of (name, reactants, catalysts,
    products, two_way), the three a list of names each.

    A line starting with # is a comment. "Food:" (or "Foods:") lists the food, separated by commas or spaces. A
    reaction is "name : reactants [catalysts] arrow products", reactants and products separated by + or spaces, the
    catalysts (any one of which catalyses) by commas, spaces or |, the arrow -> or => (one-way) or <-> or <=>
    (two-way). Refused: inhibitors ({...}), AND-catalysis (& or *, and parentheses), reverse arrows (<- or <=),
    coefficients, a reaction without catalysts (CatReNet's formal food), a repeated reaction name, no food, no
    reactions, and any other line.
    """
    food, reactions, seen = [], [], set()
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        where = f"line {number}"
        m = re.fullmatch(r"(?i:foods?)\s*:(.*)", line)
        if m:
            food.extend(names(m.group(1), r"[,\s]+", where))
            continue
        if any(c in line for c in "{}&*()"):
            raise ValueError(f"{where}: inhibitors or AND-catalysis, which this check does not read")
        m = re.fullmatch(r"([^:\[\]]+):([^:\[\]]*)\[([^:\[\]]*)\]\s*(\S+)(.*)", line)
        if m is None:
            raise ValueError(f"{where}: neither a comment, the food nor a reaction with [catalysts]")
        name, left, cats, rest, right = m.group(1).strip(), m.group(2), m.group(3), m.group(4), m.group(5)
        arrow = next(((a, two) for a, two in ARROWS if rest.startswith(a)), None)
        if arrow is None:
            raise ValueError(f"{where}: no -> => <-> or <=> after the catalysts")
        right = rest[len(arrow[0]):] + right
        if not NAME.fullmatch(name):
            raise ValueError(f"{where}: {name!r} is not a reaction name")
        if name in seen:
            raise ValueError(f"{where}: a second reaction named {name}")
        seen.add(name)
        reactants, catalysts, products = (names(left, r"[+\s]+", where, side=True), names(cats, r"[,|\s]+", where),
                                          names(right, r"[+\s]+", where, side=True))
        if not reactants or not products or not catalysts:
            raise ValueError(f"{where}: a reaction needs reactants, catalysts and products")
        reactions.append((name, reactants, catalysts, products, arrow[1]))
    if not food or not reactions:
        raise ValueError("no food or no reactions")
    return food, reactions


def crs_system(food, reactions):
    """The general form of a parsed CRS: (system, catalysis, owner, molecule names). A two-way reaction becomes its
    two one-way halves with the same catalysts; owner[k] names the CRS reaction one-way reaction k belongs to."""
    molecules = sorted(set(food) | {m for r in reactions for side in (r[1], r[2], r[3]) for m in side})
    number = {m: k for k, m in enumerate(molecules)}
    lists, cats, owner = [], [], []
    for name, reactants, catalysts, products, two_way in reactions:
        for a, b in [(reactants, products)] + ([(products, reactants)] if two_way else []):
            lists.append(([number[m] for m in a], [number[m] for m in b]))
            cats.append([number[m] for m in catalysts])
            owner.append(name)
    return system(len(molecules), sorted({number[m] for m in food}), lists), pairs(cats), owner, molecules


def counted(mask, owner):
    """The CRS reactions in a result, a two-way reaction once. Its halves need the same catalysts and a closure that
    holds one side of a reaction it contains holds the other, so both halves are in or neither is; checked."""
    state = {}
    for k, name in enumerate(owner):
        state.setdefault(name, set()).add(bool(mask[k]))
    if any(len(s) > 1 for s in state.values()):
        raise AssertionError("one half of a two-way reaction is in and the other is not")
    return sorted(name for name, s in state.items() if True in s)


def validate(directory="inputs"):
    """Each CatReNet example through max_raf and max_caf: (validation_ok, the sizes as a string, the detail)."""
    rows, ok = [], True
    for name, sha256, expected, words in INPUTS:
        food, reactions = parse_crs(load(os.path.join(directory, name), sha256))
        S, catalysis, owner, _ = crs_system(food, reactions)
        raf, _ = max_raf(S, catalysis)
        caf, _ = max_caf(S, catalysis)
        in_raf, in_caf = counted(raf, owner), counted(caf, owner)
        got = (len(reactions), len(set(food)), len(in_raf), len(in_caf))
        ok = ok and got == expected
        rows.append({"input": name, "sha256": sha256, "readme": words, "expected": list(expected), "got": list(got),
                     "ok": got == expected, "two_way": sum(1 for r in reactions if r[4]), "maxraf": in_raf,
                     "maxcaf": in_caf})
    sizes = ";".join(f"{r['input'][9:19]}:reactions={r['got'][0]},food={r['got'][1]},maxraf={r['got'][2]},"
                     f"maxcaf={r['got'][3]}" for r in rows)
    return ok, sizes, rows


# ---------------------------------------------------------------- the run

def settings():
    """Every setting, in a fixed order: (kind, P label, P as a Fraction, M)."""
    targets = {plabel: least_m(P) for plabel, P in PROBABILITIES}
    if targets != REGISTERED:
        raise AssertionError(f"the least M with P n(M) >= 4M is {targets}, not the registered {REGISTERED}")
    out = [("test", plabel, P, targets[plabel]) for plabel, P in PROBABILITIES]
    out += [("curve", plabel, P, M) for plabel, P in PROBABILITIES for M in range(SMALLEST, targets[plabel])]
    out += [("control", "half", CONTROL / (2 * ligation_count(M)), M) for M in sorted(targets.values())]
    return out


def ratio(numerator, denominator):
    """numerator / denominator for integers, correctly rounded and then to six decimals."""
    return round(numerator / denominator, 6)


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    validation_ok, validation_sizes, validation = validate()
    plan = settings()
    for M in sorted({s[3] for s in plan}):
        polymer_system(M)                     # built here, so that the workers share it
    jobs = [(seed, kind, plabel, float(P), M, i) for kind, plabel, P, M in plan for i in range(INSTANCES)]
    results = run_all(jobs)

    summary = []
    for k, (kind, plabel, P, M) in enumerate(plan):
        rows = results[k * INSTANCES:(k + 1) * INSTANCES]
        found, raf, made, caf = (list(column) for column in zip(*rows))
        R, X = 2 * ligation_count(M), molecule_count(M)
        summary.append({
            "kind": kind, "p_label": plabel, "P": str(P), "M": M, "label": label(kind, plabel, M),
            "molecules": X, "reactions": R, "instances": len(rows),
            "with_raf": sum(1 for x in raf if x > 0), "with_caf": sum(1 for x in caf if x > 0),
            "catalysts_mean": ratio(sum(found), len(rows) * R), "catalysts_expected": round(float(P * X), 6),
            "maxraf_fraction": ratio(sum(raf), len(rows) * R), "maxcaf_fraction": ratio(sum(caf), len(rows) * R),
            "pairs": found, "maxraf": raf, "maxraf_molecules": made, "maxcaf": caf,
        })

    values = {"instances": INSTANCES}
    for s in summary:
        if s["kind"] == "test":
            tag = f"{s['p_label']}_m{s['M']}"
            values[f"raf_{tag}"], values[f"caf_{tag}"] = s["with_raf"], s["with_caf"]
            values[f"catalysts_mean_{tag}"], values[f"maxraf_fraction_{tag}"] = s["catalysts_mean"], s["maxraf_fraction"]
            values[f"maxcaf_fraction_{tag}"] = s["maxcaf_fraction"]
            values[f"reactions_m{s['M']}"], values[f"molecules_m{s['M']}"] = s["reactions"], s["molecules"]
        elif s["kind"] == "control":
            values[f"control_raf_m{s['M']}"], values[f"control_caf_m{s['M']}"] = s["with_raf"], s["with_caf"]
    for plabel, _ in PROBABILITIES:
        curve = [s for s in summary if s["kind"] == "curve" and s["p_label"] == plabel]
        values[f"curve_{plabel}"] = ",".join(f"{s['M']}:{s['with_raf']}" for s in curve)
        values[f"curve_caf_{plabel}"] = ",".join(f"{s['M']}:{s['with_caf']}" for s in curve)
    tests = [s for s in summary if s["kind"] == "test"]
    controls = [s for s in summary if s["kind"] == "control"]
    values["control_ok"] = 1 if all(s["with_raf"] < REQUIRED for s in controls) else 0
    values["validation_ok"] = 1 if validation_ok else 0
    values["validation_sizes"] = validation_sizes
    values["test_passed"] = 1 if all(s["with_raf"] >= REQUIRED for s in tests) else 0

    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters")
    os.makedirs("results", exist_ok=True)
    with open(os.path.join("results", "outputs.json"), "w", encoding="ascii") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(os.path.join("results", "detail.json"), "w", encoding="ascii") as f:
        json.dump({"values": values, "settings": summary, "validation": validation,
                   "targets": {plabel: {"P": str(P), "M": least_m(P), "P_n": str(P * ligation_count(least_m(P))),
                                        "P_n_below": str(P * ligation_count(least_m(P) - 1))}
                               for plabel, P in PROBABILITIES}},
                  f, indent=1, sort_keys=True)
        f.write("\n")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
