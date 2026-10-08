#!/usr/bin/env python3
"""Fontana and Buss's AlChemy: seeded runs of the authors' own code at its three levels, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:a5428f8d25b1ebe8) is the abstract of
Fontana and Buss, "What would be conserved if 'the tape were played twice'?", PNAS 91(2):757-761 (1994): in AlChemy,
a lambda-calculus flow reactor, "(i) hypercycles of self-reproducing objects arise; (ii) if self-replication is
inhibited, self-maintaining organizations arise; and (iii) self-maintaining organizations, once established, can
combine into higher-order self-maintaining organizations." Its registered test: refuted, in AlChemy as specified
(1,000 random normal-form lambda-terms in a flow reactor; a collision [A, B] adds the normal form of (A)B, if reached
within 10,000 steps and 4,000 characters, and removes a random object), if (i) most unfiltered runs are not taken
over by copying functions (f with (f)g = g or f for all g present), singly or in hypercycles; (ii) most runs barring
copying end with no self-maintaining set of several objects, none copying, persisting under injected random objects;
or (iii) no two such sets, combined in a reactor of 3,000, form a self-maintaining whole keeping both.

The input is the authors' distribution, AlChemy.tar.gz (GPL-2; Fontana's page, last modified 1 October 2001),
checked against its SHA-256 and size before anything runs. Its C sources are compiled by the run, in the pinned image,
with no network. Every rule below was fixed before any seed existed, after trials with other seeds.

1. The model. The archive's LambdaReactor, patched as Mathis et al. (arXiv:2408.12137, section 4) patched it for a
   modern compiler (headers added, select() renamed peep(), calloc for the reaction record, regex.c's own malloc
   declarations dropped) and, here, with its peephole socket bound to "localhost" (a sandbox with no network cannot
   resolve its own host name; nothing connects to it). Compiled with gcc -ansi -D_DEFAULT_SOURCE -O3, as their
   makefile does. Each run is the archive's alchemy.inp with only these lines set: the name; the capacity (1,000, or
   3,000 at Level 2); the collisions; the snapshot interval (the run's length, so a run writes its start and its
   end); the random seed; "bind all free variables = 1"; the initial objects (NULL-1000, 1,000 random ones, or a
   population); and the acceptance of copy actions (1.0 at Level 0, 0.0 at Levels 1 and 2). The rest is the
   archive's: the ORIGINAL scheme, no typing, a heap of 4,000 and 10,000 reduction steps (the paper's limits), the
   generator's depth of 10, six variables and its probability ranges, filters making every operator and every
   product an abstraction, and the law \\f.\\g.(f)g. Two settings the paper leaves open are fixed here. Free
   variables are bound: Mathis et al. found that with them a constant function takes over whatever the filters, and
   inferred that the original work bound them; in trials here, unbound Level 1 runs froze into two species. The depth
   is the archive's 10, not the 20 of the companion paper (Bull. Math. Biol. 56:1-64), because the archive's
   generator, with its own probability ranges, exits on an over-long expression at depth 20 (five seeds of five in
   trials here). The socket ports are 5000 onwards: the archive's table holds ten.
2. The action table. For a set of species, the archive's own pair mode (-p) reduces (f)g once for each ordered pair,
   with copy actions accepted so that a copy shows; a collision that breaks a limit or a filter has no product. A
   copying function of the set is the paper's: f with (f)g = f or g for every g in it. The set is self-maintaining
   when each member is the product of a collision within it that is not a copy action (a product equal to its
   operator or its argument), the companion paper's A in A.A under Level 1's boundary condition. Its largest
   self-maintaining subset is found by discarding, until nothing is discarded, the members that no collision within
   the rest makes.
3. Level 0, part (i). L0_RUNS runs from 1,000 random objects, copy actions accepted, L0_COLLISIONS collisions each. A
   run is taken over by copying functions when every species present at its end is a copying function of that set
   (one species: singly; more: in hypercycles). Part (i) holds unless most runs are not taken over: at least half are.
4. Level 1, part (ii). L1_RUNS runs from 1,000 random objects, copy actions barred, COLLISIONS collisions; then the
   paper's first perturbation schedule, INJECTIONS times: one random object in INJECT_COPIES copies, then
   INJECT_EVERY collisions (the objects drawn by the archive's generator under a seeded seed and injected in a seeded
   order; the reactor returns to 1,000 at its next reactive collision by its own random removal). An organisation
   of a set is its largest self-maintaining subset with no copying function among its members: found by discarding
   the copying functions of what remains and the members it no longer makes, until nothing is discarded (rule 2's
   argument shows it contains every such subset). S0 is the organisation of the species before the injections, S1
   after them. A run is organised when S0 and S1 each have at least SEVERAL species and S1 is mostly S0: at least
   SEVERAL of its species were in S0, and they hold at least half of S1's objects (an organisation that shrinks, or
   whose rare species come and go, persists; one replaced by another does not). Part (ii) holds unless most runs are
   not organised: at least half are.
5. Level 2, part (iii). The pairs of organised runs, in an order drawn by the seed, at most L2_PAIRS of them. A
   pair's reactor starts with the two runs' final populations (2,000 objects) in a capacity of L2_CAPACITY, copy
   actions barred, for L2_COLLISIONS collisions; W is the largest self-maintaining subset of the species at its end.
   W keeps a run when at least SEVERAL of that run's S1 are in W and they hold at least a tenth of W's objects
   (Mathis et al. called a composite coexisting when its similarity to both inputs stayed above 0.1). The pair
   combines when W keeps both
   runs and they are knit: some collision within W between a species of one S1 (not of the other) and a species of
   the other (not of the one), either way round, has a product in W that is not a copy. l2_one_kept counts the pairs
   where W keeps one run alone, l2_none_kept those where it keeps neither. Part (iii) holds when a pair combines.
6. Controls (controls_passed counts those that pass). (a) The paper's Figure 1 laws by the archive's reducer: for
   O(i, j) = i abstractions and then the variable of the j-th, (O(i, j))O(k, l) = O(i-1, j-1) when j > 1 and
   O(k+i-1, l+i-1) when j = 1, over all 100 ordered pairs with i, k <= 4. (b) The largest self-maintaining subset of
   those ten, worked by hand: all but O(4, 1). (c) The identity alone is a copying function, and beside O(2, 1) still
   the only one, since (O(2, 1))I = O(2, 2). (d) A run of 20,000 collisions repeated under the same seed gives the
   same population, and under another seed another. (e) The copy filter: in a reactor of 999 identities and one
   O(2, 2) every collision is a copy action, so 5,000 collisions change nothing with copies barred and change the
   population with copies accepted.
7. A run or a pair whose program ends abnormally is recorded with its message and counts against its part: not
   taken over, not organised, not combined.
8. Randomness, only from ECDYSIS_SEED (hexagon/check.py's Stream): the reactor's seeds for Level 0 from
   "alchemy/l0", for Level 1 and its injections from "alchemy/l1", each run's injection order from
   "alchemy/l1/<run>/order", the pairs' order from "alchemy/l2" and their seeds from "alchemy/l2/seeds", the controls'
   from "alchemy/control"; each seed is a draw below 2^31 - 2, plus one. Two runs go at a time; results are gathered
   in run order, so nothing depends on timing.

test_passed is 1 when parts (i), (ii) and (iii) all hold; else 0. Each run's numbers and timings go to
results/detail.json.

What it cannot check:
- the paper's own runs: their seeds, lengths and generator settings were not published, and rule 1's bound variables
  and depth are readings, not the paper's words;
- "generic": the paper varied filters and boundary conditions; this runs one setting, the plainest;
- "most" over L0_RUNS and L1_RUNS runs, not over every run; and part (iii) over at most L2_PAIRS pairs, so a part
  (iii) that fails bounds how often pairs combine rather than showing that none can;
- the laws: organisations are recognised by self-maintenance and the species they keep, not by the grammars and
  algebraic laws the paper describes, and from one action table at a run's end rather than over its history;
- the long run: L0_COLLISIONS, COLLISIONS and L2_COLLISIONS are this check's choices (Mathis et al. ran 10^6 a
  stage); a run still changing at its end is judged as it stands.

Writes results/outputs.json (the 20 values a receipt carries) and results/detail.json. Run with:
python3 alchemy/check.py
"""

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import queue
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("alchemy_hexagon", os.path.join(HERE, "..", "hexagon", "check.py"))
H = importlib.util.module_from_spec(_spec)
sys.modules["alchemy_hexagon"] = H
_spec.loader.exec_module(H)

ARCHIVE = "AlChemy.tar.gz"
INPUTS = (
    (ARCHIVE, "f31a18c32bd88f253efb8e3ddd9c4aecc6b8804807688e6b4197007ec30874c7", 1006666,
     "Fontana and Buss's AlChemy (GPL-2), https://sites.santafe.edu/~walter/AlChemy/Software/AlChemy.tar.gz"),
)

L0_RUNS = 11                 # Level 0 runs (copy actions accepted)
L0_COLLISIONS = 1_000_000    # collisions in each Level 0 run
L1_RUNS = 15                 # Level 1 runs (copy actions barred)
COLLISIONS = 500_000         # collisions in each Level 1 run before the injections
INJECTIONS = 5               # random objects injected into each Level 1 run, one at a time
INJECT_EVERY = 30_000        # collisions after each injection
INJECT_COPIES = 10           # copies of each injected object
L2_CAPACITY = 3000           # the Level 2 reactor (the paper's)
L2_COLLISIONS = 1_000_000    # collisions in each Level 2 run
L2_PAIRS = 45                # at most this many pairs of organised Level 1 runs are combined
SEVERAL = 3                  # "several": at least this many species
N_OBJECTS = 1000             # objects in a Level 0 or Level 1 reactor (the paper's)
WORKERS = 2
PORT = 5000                  # the archive's socket table holds ports 5000 to 5009
LIMIT = 200

# Mathis et al.'s changes for a modern compiler (their section 4, and mathis-group/AlChemy at 1e02a86): headers after
# each file's first #include, select() renamed, calloc for the reaction record, regex.c's own malloc declarations
# dropped. And one of this check's: the peephole socket binds to "localhost", since a sandbox with no network cannot
# resolve its own host name.
HEADERS = (
    ("IPC/Socket/clientSock.c", "#include <stdlib.h>\n"),
    ("IPC/Socket/serverSock.c", "#include <stdlib.h>\n"),
    ("IPC/Socket/socket.c", "#include <stdlib.h>\n#include <string.h>\n"),
    ("IPC/Socket/utilities.c", "#include <time.h>\n#include <stdlib.h>\n"),
    ("LambdaReactor/avl.c", "#include <stdlib.h>\n"),
    ("LambdaReactor/io.c", "#include <stdlib.h>\n"),
    ("LambdaReactor/options.c", "#include <stdlib.h>\n"),
    ("LambdaReactor/peep.c", "#include <string.h>\n"),
    ("LambdaReactor/type_client.c", "#include <stdlib.h>\n"),
    ("LambdaReactor/type_test.c", "#include <stdlib.h>\n"),
    ("LambdaReactor/utilities.c", "#include <time.h>\n#include <stdlib.h>\n"),
    ("LambdaReactor/regex.c", "#include <string.h>\n"),
)
REPLACE = (
    ("LambdaReactor/interact.c", "reaction = (react *) space (sizeof (react));",
     "reaction = (react *) calloc(1, sizeof (react));", 1),
    ("LambdaReactor/main.c", "select(", "peep(", 3),
    ("LambdaReactor/regex.c", "#ifdef STDC_HEADERS\n", "", 1),
    ("LambdaReactor/regex.c", "#else\nchar *malloc ();\nchar *realloc ();\n#endif\n", "", 1),
    ("IPC/Socket/socket.c", "hp = gethostbyname (myname);", "hp = gethostbyname (\"localhost\");", 1),
)
SOURCES = ("avl.c", "avlaccess.c", "getopt.c", "io.c", "lambda.c", "conversions.c", "options.c", "regex.c",
           "utilities.c", "randomexpr.c", "filter.c", "reactor.c", "interact.c", "../IPC/Socket/socket.c",
           "../IPC/Shmem/shmem.c", "peephole.c", "type_client.c", "main.c")
CFLAGS = ("-ansi", "-D_DEFAULT_SOURCE", "-O3", "-w")     # Mathis et al.'s makefile, warnings off

OUTPUTS = (
    "l0_runs", "l0_taken", "l0_single", "l0_species_max",
    "l1_runs", "l1_sm", "l1_organised", "l1_sm_median", "l1_kept_median",
    "l2_pairs_run", "l2_combined", "l2_one_kept", "l2_none_kept",
    "part_i", "part_ii", "part_iii", "collisions_total",
    "controls_passed", "controls_total", "test_passed",
)


class Refused(Exception):
    """An input that is not what the rules say it must be."""


def load(directory, name):
    spec = next(i for i in INPUTS if i[0] == name)
    with open(os.path.join(directory, name), "rb") as f:
        data = f.read()
    got = hashlib.sha256(data).hexdigest()
    if got != spec[1] or len(data) != spec[2]:
        raise Refused(f"{name}: sha256 {got} and {len(data)} bytes, not the committed {spec[1]} and {spec[2]}")
    return data


# ---------------------------------------------------------------- the build

def patch(root):
    """Rule 1's changes to the archive's sources, each found exactly where it must be."""
    for rel, header in HEADERS:
        p = os.path.join(root, rel)
        with open(p, encoding="latin-1") as f:
            s = f.read()
        i = s.find("#include")
        if i < 0:
            raise Refused(f"{rel}: no #include")
        j = s.find("\n", i) + 1
        with open(p, "w", encoding="latin-1") as f:
            f.write(s[:j] + header + s[j:])
    for rel, old, new, count in REPLACE:
        p = os.path.join(root, rel)
        with open(p, encoding="latin-1") as f:
            s = f.read()
        if s.count(old) != count:
            raise Refused(f"{rel}: {s.count(old)} occurrences of {old!r}, not {count}")
        with open(p, "w", encoding="latin-1") as f:
            f.write(s.replace(old, new))


def build(inputs, out_dir, work):
    """The archive extracted (rule 1), patched and compiled; returns (binary, template input, gcc version)."""
    load(inputs, ARCHIVE)
    root = H.safe_extract(os.path.join(inputs, ARCHIVE), "AlChemy", work)
    patch(root)
    src = os.path.join(root, "LambdaReactor")
    objs = []
    for s in SOURCES:
        o = os.path.join(work, os.path.basename(s)[:-2] + ".o")
        H.run_quiet(["gcc", *CFLAGS, "-I../IPC/Socket", "-I../IPC/Shmem", "-c", s, "-o", o], f"gcc {s}", cwd=src)
        objs.append(o)
    os.makedirs(out_dir, exist_ok=True)
    binary = os.path.abspath(os.path.join(out_dir, "ALCHEMY"))
    H.run_quiet(["gcc", "-O3", "-o", binary, *objs, "-lm"], "link")
    with open(os.path.join(src, "alchemy.inp"), encoding="latin-1") as f:
        template = f.read()
    gcc = H.run_quiet(["gcc", "--version"], "gcc --version").splitlines()[0]
    return binary, template, gcc


# ---------------------------------------------------------------- running the reactor

SETTINGS = ("name of simulation", "maximum overall number of objects", "number of collisions to perform",
            "snapshot interval", "random seed", "bind all free variables", "file with initial objects",
            "acceptance frequency for copy actions")


def input_file(template, **values):
    """The archive's alchemy.inp with rule 1's lines set, every one of them found exactly once."""
    keys = {k.replace(" ", "_"): k for k in SETTINGS}
    want = {keys[k]: v for k, v in values.items()}
    seen, out = set(), []
    for line in template.split("\n"):
        if "=" in line:
            key = line.split("=")[0].strip()
            if key in want:
                if key in seen:
                    raise Refused(f"alchemy.inp: {key!r} twice")
                seen.add(key)
                line = line.split("=")[0] + "=  " + str(want[key])
        out.append(line)
    if seen != set(want):
        raise Refused(f"alchemy.inp: no line for {sorted(set(want) - seen)}")
    return "\n".join(out)


def write_objects(path, counts):
    """A population in the snapshot format the archive reads: one species a line, "expr {id count type}"."""
    with open(path, "wb") as f:
        for i, e in enumerate(sorted(counts)):
            f.write(e + b" {%d %d 0}\n" % (i + 1, counts[e]))


def read_objects(path):
    out = {}
    with open(path, "rb") as f:
        for line in f:
            line = line.rstrip(b"\n")
            if not line.strip():
                continue
            expr, rest = line.rsplit(b" {", 1)
            fields = rest.rstrip(b"}").split()
            if not expr.startswith(b"\\x") or b" " in expr or len(fields) != 3 or expr in out:
                raise RuntimeError(f"{path}: unread line {line[:120]!r}")
            out[expr] = int(fields[1])
    return out


class Reactor:
    """The compiled archive, run in its own directory per call; ports handed out one per concurrent run."""

    def __init__(self, binary, template, work):
        self.binary, self.template, self.work = binary, template, work
        self.ports = queue.Queue()
        for p in range(PORT, PORT + WORKERS + 1):
            self.ports.put(p)
        self.count = 0
        self.lock = threading.Lock()

    def _dir(self, tag):
        with self.lock:
            self.count += 1
            d = os.path.join(self.work, f"{self.count:04d}-{tag}")
        os.makedirs(d)
        return d

    def _exec(self, d, args):
        port = self.ports.get()
        try:
            with open(os.path.join(d, "log"), "wb") as log:
                r = subprocess.run([self.binary, *args, "--peep", str(port)], cwd=d, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=subprocess.STDOUT, env={"PATH": "/usr/bin:/bin", "TERM": "dumb"})
        finally:
            self.ports.put(port)
        if r.returncode != 0:
            with open(os.path.join(d, "log"), "rb") as f:
                tail = f.read()[-1500:].decode("latin-1")
            raise RuntimeError(f"ALCHEMY {args} in {d} failed ({r.returncode}): {tail}")

    def run(self, tag, seed, objects, copy, collisions, capacity=N_OBJECTS):
        """A run from NULL-n random objects (objects an int) or a population (a dict); the final population."""
        d = self._dir(tag)
        if isinstance(objects, int):
            start = f"NULL-{objects}"
        else:
            write_objects(os.path.join(d, "start"), objects)
            start = "start"
        text = input_file(self.template, name_of_simulation="R", maximum_overall_number_of_objects=capacity,
                          number_of_collisions_to_perform=collisions, snapshot_interval=max(collisions, 1),
                          random_seed=seed, bind_all_free_variables=1, file_with_initial_objects=start,
                          acceptance_frequency_for_copy_actions=copy)
        with open(os.path.join(d, "R.inp"), "w", encoding="latin-1") as f:
            f.write(text)
        t = time.time()
        self._exec(d, ["-f", "R.inp"])
        first = read_objects(os.path.join(d, "R0"))
        final = read_objects(os.path.join(d, "R1")) if collisions else first
        shutil.rmtree(d)
        return first, final, round(time.time() - t, 1)

    def random_objects(self, tag, seed, n):
        """n distinct random objects from the archive's generator (rule 1's settings), in its sorted order."""
        if n < 2:
            raise ValueError("the reactor's single collision after the snapshot needs two objects")
        first, _, _ = self.run(tag, seed, n, "1.0", 0, capacity=n)
        if len(first) != n or set(first.values()) != {1}:
            raise RuntimeError(f"{tag}: {len(first)} random objects, not {n}")
        return sorted(first)

    def table(self, tag, species):
        """Every ordered pair of species reduced once by the archive's own pair mode (-p), copy actions accepted:
        (order, products), products[(f, g)] the normal form of (f)g, or None when the collision is elastic."""
        d = self._dir(tag)
        order = sorted(set(species))
        write_objects(os.path.join(d, "S"), {e: 1 for e in order})
        text = input_file(self.template, name_of_simulation="P", maximum_overall_number_of_objects=10 * len(order) + 10,
                          number_of_collisions_to_perform=0, snapshot_interval=1, random_seed=1,
                          bind_all_free_variables=1, file_with_initial_objects="S",
                          acceptance_frequency_for_copy_actions="1.0")
        with open(os.path.join(d, "P.inp"), "w", encoding="latin-1") as f:
            f.write(text)
        self._exec(d, ["-p", "-f", "P.inp"])
        with open(os.path.join(d, "S.pairs"), "rb") as f:
            products = parse_pairs(f.read(), order)
        shutil.rmtree(d)
        return order, products


PAIR_LINE = re.compile(rb"^\s*(\d+) \[0\] :\s*(\d+) \[0\] => (?:\s*(\d+) \[0\] \d+|\s*\*\s+(\S+)|\s([+ORAT]))$")


def parse_pairs(data, order):
    """The pair mode's file: "i [0] : j [0] => k [0] steps", or "=>  *   expr" for a product outside the set, or a
    code for an elastic collision. Indices are places in the sorted order, from 1. Every pair exactly once."""
    n, products, members = len(order), {}, set(order)
    for line in data.split(b"\n"):
        if not line:
            continue
        m = PAIR_LINE.match(line)
        if not m:
            raise RuntimeError(f"pair mode: unread line {line[:160]!r}")
        i, j = int(m.group(1)), int(m.group(2))
        if not (1 <= i <= n and 1 <= j <= n) or (order[i - 1], order[j - 1]) in products:
            raise RuntimeError(f"pair mode: bad pair {i}, {j}")
        if m.group(3):
            k = int(m.group(3))
            if not 1 <= k <= n:
                raise RuntimeError(f"pair mode: bad product {k}")
            p = order[k - 1]
        elif m.group(4):
            p = m.group(4)
            if p in members:
                raise RuntimeError(f"pair mode: a product outside the set that is in it, {p[:80]!r}")
        else:
            p = None
        products[(order[i - 1], order[j - 1])] = p
    if len(products) != n * n:
        raise RuntimeError(f"pair mode: {len(products)} pairs, not {n * n}")
    return products


# ---------------------------------------------------------------- the analysis

def copying(members, products):
    """Rule 2: the members f with (f)g equal to f or g for every member g (the paper's copying functions)."""
    return {f for f in members if all(products[(f, g)] in (f, g) for g in members)}


def self_maintaining(members, products):
    """Rule 3: the largest subset whose every member is produced within it by a collision that is not a copy action
    (a product equal to the operator or the argument). Discarding the members not so produced, until none is left
    to discard, finds it: a member of any self-maintaining subset is never discarded."""
    m = set(members)
    while True:
        made = {p for f in m for g in m for p in (products[(f, g)],) if p is not None and p in m and p != f and p != g}
        if made >= m:
            return m
        m &= made


def organisation(members, products):
    """Rule 4: the largest self-maintaining subset with no copying function among its members. Discarding the copying
    functions of the remaining set and then the members it does not make, until neither discards anything, finds it:
    a member of any such subset is never discarded, since a copying function of a set is one of each subset holding
    it, and a member a self-maintaining subset makes is made by any set that holds that subset."""
    m = set(members)
    while True:
        smaller = self_maintaining(m - copying(m, products), products)
        if smaller == m:
            return m
        m = smaller


def persists(s0, s1, population):
    """Rule 4: S0 and S1 each have SEVERAL species or more, and S1 is mostly S0: SEVERAL or more of its species were
    in S0, and they hold at least half of S1's objects in the population after the injections."""
    kept = s0 & s1
    held, total = sum(population[e] for e in kept), sum(population[e] for e in s1)
    return len(s0) >= SEVERAL and len(s1) >= SEVERAL and len(kept) >= SEVERAL and 2 * held >= total


def keeps(whole, s1, population):
    """Rule 5: SEVERAL or more of a run's S1 are in the whole, holding at least a tenth of the whole's objects."""
    inside = whole & s1
    held, total = sum(population[e] for e in inside), sum(population[e] for e in whole)
    return len(inside) >= SEVERAL and 10 * held >= total


def knit(whole, a, b, products):
    """Rule 4: collisions within the whole between a member of one organisation (not of the other) and a member of the
    other (not of the one), either way round, whose product is in the whole and is not a copy."""
    left, right = (a - b) & whole, (b - a) & whole
    n = 0
    for f, g in [(f, g) for f in left for g in right] + [(g, f) for f in left for g in right]:
        p = products[(f, g)]
        if p is not None and p in whole and p != f and p != g:
            n += 1
    return n


def seed_for(stream):
    return stream.below((1 << 31) - 2) + 1


# ---------------------------------------------------------------- the levels

def level0(reactor, seed, runs, collisions, pool, log):
    seeds = H.Stream(seed, "alchemy/l0")
    jobs = [(i, seed_for(seeds)) for i in range(runs)]

    def one(job):
        try:
            return one_run(job)
        except RuntimeError as e:
            log(f"level 0 run {job[0]}: the program ended abnormally: {e}")
            return {"run": job[0], "seed": job[1], "crashed": str(e)[-400:], "taken": False, "species": 0}

    def one_run(job):
        i, s = job
        _, final, secs = reactor.run(f"l0-{i}", s, N_OBJECTS, "1.0", collisions)
        order, products = reactor.table(f"l0-{i}-p", final)
        cop = copying(order, products)
        taken = cop == set(order)
        log(f"level 0 run {i}: {len(order)} species, {len(cop)} copying, taken {taken}, {secs} s")
        return {"run": i, "seed": s, "seconds": secs, "species": len(order), "copying": len(cop),
                "taken": taken, "top": sorted(final.values(), reverse=True)[:5],
                "identity": final.get(b"\\x1.x1", 0)}

    return list(pool.map(one, jobs))


def level1(reactor, seed, runs, collisions, pool, log):
    seeds = H.Stream(seed, "alchemy/l1")
    jobs = [(i, seed_for(seeds), [seed_for(seeds) for _ in range(INJECTIONS + 1)]) for i in range(runs)]

    def one(job):
        try:
            return one_run(job)
        except RuntimeError as e:
            log(f"level 1 run {job[0]}: the program ended abnormally: {e}")
            return {"run": job[0], "seed": job[1], "crashed": str(e)[-400:], "sm": 0, "kept": 0, "sm_ok": False,
                    "organised": False, "m1": [], "population": {}}

    def one_run(job):
        i, s, more = job
        _, pop, secs = reactor.run(f"l1-{i}", s, N_OBJECTS, "0.0", collisions)
        order0, prod0 = reactor.table(f"l1-{i}-p0", pop)
        m0 = organisation(order0, prod0)
        new = reactor.random_objects(f"l1-{i}-new", more[0], INJECTIONS)
        ranks = H.Stream(seed, f"alchemy/l1/{i}/order")
        new = [new.pop(ranks.below(len(new))) for _ in range(INJECTIONS)]
        for k, obj in enumerate(new):
            pop = dict(pop)
            pop[obj] = pop.get(obj, 0) + INJECT_COPIES
            _, pop, t = reactor.run(f"l1-{i}-inj{k}", more[k + 1], pop, "0.0", INJECT_EVERY)
            secs += t
        order1, prod1 = reactor.table(f"l1-{i}-p1", pop)
        m1 = organisation(order1, prod1)
        plain0, plain1 = len(self_maintaining(order0, prod0)), len(self_maintaining(order1, prod1))
        kept = len(m0 & m1)
        objects1, kept_objects = sum(pop[e] for e in m1), sum(pop[e] for e in m0 & m1)
        sm = len(m0) >= SEVERAL
        organised = persists(m0, m1, pop)
        log(f"level 1 run {i}: {len(order0)} species, organisation {len(m0)} (self-maintaining {plain0}); after "
            f"the injections {len(order1)} species, organisation {len(m1)} ({plain1}) of {objects1} objects, "
            f"{kept} species and {kept_objects} objects of them from before; organised {organised}, {round(secs, 1)} s")
        return {"run": i, "seed": s, "seconds": round(secs, 1), "species": len(order0), "sm": len(m0),
                "sm_plain": plain0, "species_after": len(order1), "sm_after": len(m1), "sm_after_plain": plain1,
                "kept": kept, "objects_after": objects1, "kept_objects": kept_objects, "sm_ok": sm,
                "organised": organised, "injected": [o.decode("latin-1") for o in new], "m1": sorted(m1),
                "population": pop}

    return list(pool.map(one, jobs))


def level2(reactor, seed, organised, pairs_max, collisions, pool, log):
    pairs = [(a, b) for x, a in enumerate(organised) for b in organised[x + 1:]]
    order = H.sample(seed, "alchemy/l2", len(pairs), len(pairs)) if pairs else []
    pairs = [pairs[k] for k in order][:pairs_max]
    seeds = H.Stream(seed, "alchemy/l2/seeds")
    jobs = [(a, b, seed_for(seeds)) for a, b in pairs]

    def one(job):
        try:
            return one_run(job)
        except RuntimeError as e:
            log(f"level 2 runs {job[0]['run']} + {job[1]['run']}: the program ended abnormally: {e}")
            return {"pair": [job[0]["run"], job[1]["run"]], "seed": job[2], "crashed": str(e)[-400:],
                    "combined": False, "one_kept": False, "none_kept": False}

    def one_run(job):
        a, b, s = job
        pop = dict(a["population"])
        for e, c in b["population"].items():
            pop[e] = pop.get(e, 0) + c
        _, final, secs = reactor.run(f"l2-{a['run']}-{b['run']}", s, pop, "0.0", collisions, capacity=L2_CAPACITY)
        order_, products = reactor.table(f"l2-{a['run']}-{b['run']}-p", final)
        w = self_maintaining(order_, products)
        cw = copying(w, products)
        ma, mb = set(a["m1"]), set(b["m1"])
        ka, kb = len(w & ma), len(w & mb)
        wt, wa, wb = (sum(final[e] for e in x) for x in (w, w & ma, w & mb))
        glue = len(w - ma - mb)
        cross = knit(w, ma, mb, products)
        keep_a, keep_b = keeps(w, ma, final), keeps(w, mb, final)
        combined = keep_a and keep_b and cross > 0
        one_kept, none_kept = keep_a != keep_b, not (keep_a or keep_b)
        log(f"level 2 runs {a['run']} + {b['run']}: {len(order_)} species, self-maintaining {len(w)} of {wt} "
            f"objects; kept {ka}/{len(ma)} species ({wa} objects) and {kb}/{len(mb)} ({wb}); glue {glue}, cross "
            f"{cross}; combined {combined}, {secs} s")
        return {"pair": [a["run"], b["run"]], "seed": s, "seconds": secs, "species": len(order_), "sm": len(w),
                "sm_objects": wt, "sm_copying": len(cw), "kept_a": ka, "of_a": len(ma), "objects_a": wa, "kept_b": kb,
                "of_b": len(mb), "objects_b": wb, "glue": glue, "cross": cross, "combined": combined,
                "one_kept": one_kept, "none_kept": none_kept}

    return list(pool.map(one, jobs))


# ---------------------------------------------------------------- controls

def O(i, j):
    """The paper's Figure 1 objects: i abstractions, then the variable bound by the j-th, in standard form."""
    return ("".join(f"\\x{k}." for k in range(1, i + 1)) + f"x{j}").encode("ascii")


def controls(reactor, seed, log):
    out = {}
    # 1. The paper's two laws, by the archive's own reducer, over every pair of O(i, j), 1 <= j <= i <= 4.
    objs = [O(i, j) for i in range(1, 5) for j in range(1, i + 1)]
    order, products = reactor.table("c-laws", objs)
    ok = True
    for i in range(1, 5):
        for j in range(1, i + 1):
            for k in range(1, 5):
                for l_ in range(1, k + 1):
                    want = O(i - 1, j - 1) if j > 1 else O(k + i - 1, l_ + i - 1)
                    got = products[(O(i, j), O(k, l_))]
                    ok &= got == want
    out["laws"] = ok
    # 2. The largest self-maintaining subset of those ten, worked by hand: all but O(4, 1).
    out["self_maintaining"] = self_maintaining(order, products) == set(objs) - {O(4, 1)}
    # 3. Copying functions: the identity alone is taken over; with K beside it, it is not ((K)I is neither).
    o1, p1 = reactor.table("c-copy1", [O(1, 1)])
    o2, p2 = reactor.table("c-copy2", [O(1, 1), O(2, 1)])
    out["copying"] = copying(o1, p1) == {O(1, 1)} and copying(o2, p2) == {O(1, 1)}
    # 4. The seed decides a run: the same seed twice gives the same population, another seed another.
    s = H.Stream(seed, "alchemy/control")
    a, b = seed_for(s), seed_for(s)
    _, x, _ = reactor.run("c-seed-a", a, N_OBJECTS, "0.0", 20000)
    _, y, _ = reactor.run("c-seed-a2", a, N_OBJECTS, "0.0", 20000)
    _, z, _ = reactor.run("c-seed-b", b, N_OBJECTS, "0.0", 20000)
    out["seeded"] = x == y and x != z
    # 5. The copy filter. In a reactor of 999 identities I and one O(2, 2), every collision is a copy action: (I)I = I,
    #    (I)O(2, 2) = O(2, 2), and (O(2, 2))I = I by the first law. With copy actions barred nothing changes in 5,000
    #    collisions; with them accepted, the population moves.
    start = {O(1, 1): 999, O(2, 2): 1}
    _, barred, _ = reactor.run("c-barred", a, start, "0.0", 5000)
    _, open_, _ = reactor.run("c-open", a, start, "1.0", 5000)
    out["barred"] = barred == start and open_ != start and sum(open_.values()) == N_OBJECTS
    log(f"controls: {out}")
    return out


# ---------------------------------------------------------------- the run

def summarise(values):
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters")
    return out


def run(seed, inputs="inputs", results="results", l0_runs=L0_RUNS, l0_collisions=L0_COLLISIONS, l1_runs=L1_RUNS,
        collisions=COLLISIONS, l2_pairs=L2_PAIRS, l2_collisions=L2_COLLISIONS, log=print):
    t0 = time.time()
    work = tempfile.mkdtemp(prefix="alchemy-")
    try:
        binary, template, gcc = build(inputs, os.path.join(results, "bin"), os.path.join(work, "src"))
        reactor = Reactor(binary, template, os.path.join(work, "runs"))
        with ThreadPoolExecutor(WORKERS) as pool:
            ctrl = controls(reactor, seed, log)
            l0 = level0(reactor, seed, l0_runs, l0_collisions, pool, log)
            l1 = level1(reactor, seed, l1_runs, collisions, pool, log)
            organised = [r for r in l1 if r["organised"]]
            l2 = level2(reactor, seed, organised, l2_pairs, l2_collisions, pool, log)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    taken = sum(r["taken"] for r in l0)
    n_org = len(organised)
    part_i = int(2 * taken >= l0_runs)
    part_ii = int(2 * n_org >= l1_runs)
    part_iii = int(any(r["combined"] for r in l2))
    total = (l0_runs * l0_collisions + l1_runs * (collisions + INJECTIONS * INJECT_EVERY) + len(l2) * l2_collisions)
    values = {
        "l0_runs": l0_runs, "l0_taken": taken, "l0_single": sum(r["taken"] and r["species"] == 1 for r in l0),
        "l0_species_max": max((r["species"] for r in l0), default=0),
        "l1_runs": l1_runs, "l1_sm": sum(r["sm_ok"] for r in l1), "l1_organised": n_org,
        "l1_sm_median": statistics.median(r["sm"] for r in l1) if l1 else 0,
        "l1_kept_median": statistics.median(r["kept"] for r in organised) if organised else 0,
        "l2_pairs_run": len(l2), "l2_combined": sum(r["combined"] for r in l2),
        "l2_one_kept": sum(r["one_kept"] for r in l2), "l2_none_kept": sum(r["none_kept"] for r in l2),
        "part_i": part_i, "part_ii": part_ii, "part_iii": part_iii, "collisions_total": total,
        "controls_passed": sum(ctrl.values()), "controls_total": len(ctrl),
        "test_passed": int(part_i and part_ii and part_iii),
    }
    for r in l1:
        r.pop("population")
        r["m1"] = len(r["m1"])
    detail = {"level0": l0, "level1": l1, "level2": l2, "controls": ctrl, "gcc": gcc,
              "crashed": sum("crashed" in r for r in l0 + l1 + l2),
              "python": platform.python_version(), "seconds": round(time.time() - t0, 1),
              "settings": {"l0_runs": l0_runs, "l0_collisions": l0_collisions, "l1_runs": l1_runs,
                           "collisions": collisions, "l2_pairs": l2_pairs, "l2_collisions": l2_collisions}}
    return summarise(values), detail


def main():
    parser = argparse.ArgumentParser(description="AlChemy's three levels, seeded, for an Ecdysis receipt")
    parser.add_argument("--l0-runs", type=int, default=L0_RUNS)
    parser.add_argument("--l0-collisions", type=int, default=L0_COLLISIONS)
    parser.add_argument("--l1-runs", type=int, default=L1_RUNS)
    parser.add_argument("--collisions", type=int, default=COLLISIONS)
    parser.add_argument("--l2-pairs", type=int, default=L2_PAIRS)
    parser.add_argument("--l2-collisions", type=int, default=L2_COLLISIONS)
    args = parser.parse_args()
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, detail = run(seed, l0_runs=args.l0_runs, l0_collisions=args.l0_collisions, l1_runs=args.l1_runs,
                          collisions=args.collisions,
                          l2_pairs=args.l2_pairs, l2_collisions=args.l2_collisions,
                          log=lambda line: print(line, file=sys.stderr, flush=True))
    except Refused as e:
        sys.exit(f"alchemy/check.py: refused: {e}")
    os.makedirs("results", exist_ok=True)
    with open(os.path.join("results", "outputs.json"), "w", encoding="ascii") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(os.path.join("results", "detail.json"), "w", encoding="ascii") as f:
        json.dump(detail, f, indent=1, sort_keys=True, default=lambda o: o.decode("latin-1"))
        f.write("\n")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
