#!/usr/bin/env python3
"""The Erdős discrepancy problem for C = 2: Konev and Lisitsa's 1,160-term sequence checked exactly, and the absence of
any sequence of length 1,161 and discrepancy 2 proved again by SAT, with the proof checked by a verified checker, for
an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from Konev and Lisitsa, "A SAT Attack on the
Erdos Discrepancy Conjecture" (SAT 2014, arXiv:1402.2184): "We show that by encoding the problem into Boolean
satisfiability and applying the state of the art SAT solvers, one can obtain a sequence of length 1160 with
discrepancy 2 and a proof of the Erdos discrepancy conjecture for C=2, claiming that no sequence of length 1161 and
discrepancy 2 exists." Its registered test: refuted if the 1,160-term +-1 sequence printed in the paper's appendix has
a sum x_d + x_2d + ... + x_kd (kd <= 1160) of absolute value above 2, or if some +-1 sequence of length 1,161 has every
such sum (kd <= 1161) of absolute value at most 2.

The inputs, each checked against its SHA-256 and size before anything else runs (see INPUTS): the paper's LaTeX
source as arXiv serves it (1402.2184v2, one gzipped file, SAT14_Arxiv.tex, read as data); and, as in
hexagon/check.py, whose code this module imports, CaDiCaL 2.1.3's source as Debian archived it and the two files of
the CakeML-verified LRAT checker cake_lpr. No input is executed as given: the solver and the checker are compiled from
source into results/build by the run, in the pinned image, with no network. Every rule below was fixed before any
seed existed.

1. The paper's statements and its sequence. The source must state, white space aside, "There exists a sequence of
   length $1160$ of discrepancy $2$." and "No sequence of length $1161$ has discrepancy $2$."; and its appendix
   section "One of the sequences of length $1160$ having discrepancy $2$" must hold, after "\\tt" and up to
   "\\end{document}", nothing but the signs "+" and "-", line breaks "\\\\" and white space. The signs, read in
   order, are the sequence (+ for +1). Its discrepancy is the largest |x_d + x_2d + ... + x_kd| over every d >= 1
   and every k with kd at most its length, computed directly, every partial sum included. witness_ok needs 1,160
   terms and a discrepancy of at most 2. Beside it, the discrepancies of its two extensions to 1,161 terms (+1 or -1
   appended), at least 3 each if the claim holds.
2. The formula. edp(C, n) as the authors' journal version defines it (Konev and Lisitsa, Artificial Intelligence 224
   (2015), arXiv:1405.3097, section 3): for each d from 1 to floor(n / (C + 1)), the sequential counter
   CBound_C(x_d, x_2d, ...) of its clauses (7)-(10), with the units (5), (6), (11) and (12) propagated into them (a
   clause they satisfy is dropped, a literal they falsify is removed; no other unit arises), and the progression's
   last term left out when its Proposition 6 frees it (C even and an odd number of terms before it, or C odd and an
   even number). Variables 1..n are the terms, true for +1; each counter's variables s(k, j) follow, numbered as
   they first occur (d, then k, then j, increasing). Its Proposition 7's symmetry break is the unit x_60 (+1), the
   term the paper fixes for C = 2. The sizes must be those the journal prints: 11,824 variables and 41,884 clauses
   for n = 1160, 11,847 and 41,970 for n = 1161 (the unit aside); sizes_as_printed is 1 when all four agree.
3. The proof. edp(2, 1161) with the unit x_60 is renamed and shuffled by the seed (rule 5): its variables by a
   permutation of 1..11,847, the order of its clauses, and the order of the literals in each. CaDiCaL solves it
   with its LRAT proof streamed down a pipe into cake_lpr, as in hexagon/check.py; a check that runs out of
   cake_lpr's heap or stack is repeated with a larger one. unsat_verified is 1 when CaDiCaL reports UNSATISFIABLE
   and cake_lpr then reports "s VERIFIED UNSAT" on that formula. A model, if one were found, is renamed back and its
   1,161 terms checked directly, as in rule 1: one of discrepancy at most 2 would refute the claim.
4. Controls, each of which must behave as stated (controls_passed counts those that do):
   a. the printed sequence (negated if its term 60 is -1, as Proposition 7 allows), extended to the counters by the
      journal's Proposition 2 (s(k, j) true when at least k of the first j terms of the progression are +1),
      satisfies every clause of edp(2, 1160) and the unit x_60: the formula admits the paper's sequence;
   b. for C = 1 and C = 2 and every n up to EXHAUSTIVE_N, and every +-1 sequence of length n, edp(C, n) with the
      sequence's units has a model exactly when the sequence's discrepancy is at most C (decided by unit
      propagation, and by search on whatever it leaves open): the formula means what it should wherever every
      sequence can be listed;
   c. C = 1, whose answer a human proof gives (11 terms, as the abstract recalls): edp(1, 11) is satisfiable with a
      model whose terms have discrepancy 1, and edp(1, 12) is refuted with a proof cake_lpr verifies;
   d. hexagon's three pigeonhole proof controls: an LRAT proof accepted, and rejected without its last step or
      without a lemma that step cites.
5. Randomness, only from ECDYSIS_SEED, as in hexagon/check.py: SHA-256(seed || "|" || "edp/shuffle" || "|" ||
   counter) read 8 bytes at a time, big-endian; an integer below n by rejection; each shuffle Fisher-Yates from the
   top, the variables first, then the clauses, then each clause's literals in the shuffled order. The solver's
   search is deterministic for a given formula; cnf_sha256 (of the shuffled formula's DIMACS text) lets another run
   under the same seed show it solved the same formula. Timings and conflict counts go to results/detail.json.

test_passed is 1 if witness_ok is 1 and unsat_verified is 1; else 0. The extensions, the formula's sizes and the
controls are reported beside it.

What it cannot check:
- the encoding's correctness in general: Theorem 5 of the journal version (edp(C, n) has a model exactly when a
  sequence of length n and discrepancy at most C exists) is the trusted step; control (b) tests it on every sequence
  up to EXHAUSTIVE_N terms and control (a) on the paper's sequence, and the journal proves it;
- the authors' certificates: neither the 13 GB nor the 1.67 GB DRUP proof was published, and the generators and
  formulas on the authors' pages no longer download, so this proves the result again rather than re-checking theirs;
- the paper's own formula: the SAT 2014 paper used an automaton encoding; this uses the journal version's smaller one,
  by the same authors, whose printed sizes it reproduces;
- the tools beyond themselves: cake_lpr is verified in CakeML down to its assembly, but its C wrapper, the compiler,
  the kernel and this script (the encoder, the shuffle, the direct discrepancy computation) are trusted.

Writes results/outputs.json (the 20 values a receipt carries) and results/detail.json (every value computed).
"""

import argparse
import gzip
import hashlib
import importlib.util
import itertools
import json
import os
import platform
import re
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("edp_hexagon", os.path.join(HERE, "..", "hexagon", "check.py"))
H = importlib.util.module_from_spec(_spec)
sys.modules["edp_hexagon"] = H
_spec.loader.exec_module(H)

TOOLS = {i[0]: i for i in H.INPUTS if i[0] in ("cadical_2.1.3.orig.tar.gz", "cake_lpr.S", "basis_ffi.c")}
INPUTS = (
    ("SAT14_Arxiv.tex.gz", "95d6d87162b37efc7bdaf763132847ee062dfe458affbad78bb8c1f1b9e58a39", 9362,
     "arXiv:1402.2184v2 source (https://arxiv.org/src/1402.2184v2)"),
    TOOLS["cadical_2.1.3.orig.tar.gz"],
    TOOLS["cake_lpr.S"],
    TOOLS["basis_ffi.c"],
)
C_BOUND = 2
N_WITNESS, N_PROOF = 1160, 1161
FIXED = 60                         # the term Proposition 7 sets to +1, as the journal does for C = 2
PRINTED = {1160: (11824, 41884), 1161: (11847, 41970)}      # the journal's sizes: variables, clauses (the unit aside)
EXHAUSTIVE_N = 18
STATEMENTS = ("There exists a sequence of length $1160$ of discrepancy $2$.",
              "No sequence of length $1161$ has discrepancy $2$.")
APPENDIX = r"\section{One of the sequences of length $1160$ having discrepancy $2$}"
HEAP_MB, STACK_MB = 1024, 512
RETRY_HEAP_MB, RETRY_STACK_MB = 2560, 768
LIMIT = 200

OUTPUTS = (
    "witness_terms", "witness_discrepancy", "witness_ok", "extensions_discrepancy",
    "cnf_vars_1160", "cnf_clauses_1160", "cnf_vars_1161", "cnf_clauses_1161", "sizes_as_printed",
    "cnf_sha256", "unsat_answer", "unsat_verified",
    "exhaustive_sequences", "exhaustive_disagreements", "controls_passed", "controls_total",
    "c1_boundary", "solver", "checker", "test_passed",
)


class Refused(Exception):
    """An input that is not what the rules say it must be."""


# ---------------------------------------------------------------- inputs

def load(directory, name):
    """The bytes of an input, after its SHA-256 and size are checked against INPUTS."""
    spec = next(i for i in INPUTS if i[0] == name)
    path = os.path.join(directory, name)
    with open(path, "rb") as f:
        data = f.read()
    got = hashlib.sha256(data).hexdigest()
    if got != spec[1] or len(data) != spec[2]:
        raise Refused(f"{path}: sha256 {got} and {len(data)} bytes, not the committed {spec[1]} and {spec[2]}")
    return data


def paper(tex):
    """Rule 1: the two statements must be there; the appendix's signs, as +1 and -1."""
    flat = " ".join(tex.split())
    for s in STATEMENTS:
        if s not in flat:
            raise Refused(f"the paper does not state {s!r}")
    at = tex.find(APPENDIX)
    if at < 0 or tex.find(APPENDIX, at + 1) >= 0:
        raise Refused("the appendix with the sequence is not there exactly once")
    start = tex.find("\\tt", at)
    end = tex.find("\\end{document}", at)
    if start < 0 or end < 0 or end < start:
        raise Refused("the appendix's sequence is not between \\tt and \\end{document}")
    body = tex[start + 3:end].replace("\\\\", " ")
    bad = set(body) - set("+- \t\r\n")
    if bad:
        raise Refused(f"the appendix's sequence holds {sorted(bad)!r} as well as signs")
    return [1 if ch == "+" else -1 for ch in body if ch in "+-"]


# ---------------------------------------------------------------- discrepancy, directly

def discrepancy(x):
    """max |x_d + x_2d + ... + x_kd| over d >= 1 and kd <= len(x), every partial sum included (x[0] is x_1)."""
    n, worst = len(x), 0
    for d in range(1, n + 1):
        s = 0
        for i in range(d, n + 1, d):
            s += x[i - 1]
            if abs(s) > worst:
                worst = abs(s)
    return worst


# ---------------------------------------------------------------- the encoding

TRUE, FALSE = "T", "F"


def cbound(seq, C, newvar):
    """CBound_C on the input variables seq: clauses (7)-(10) for 1 <= k, j <= len(seq), with (5) s(k, j) false for
    j < k, (6) s(0, j) true, (11) s(k, j) true for j > 2k - 2 + C and (12) s(k, j) false for j < 2k - C propagated.
    Returns (clauses, {(k, j): variable})."""
    m = len(seq)
    var = {}

    def s(k, j):
        if k == 0:
            return TRUE
        if j < k or j < 2 * k - C:
            return FALSE
        if j > 2 * k - 2 + C:
            return TRUE
        if (k, j) not in var:
            var[(k, j)] = newvar()
        return var[(k, j)]

    out, seen = [], set()
    for k in range(1, m + 1):
        for j in range(1, m + 1):
            p = seq[j - 1]
            a, b, c = s(k, j), s(k, j - 1), s(k - 1, j - 1)
            for clause in (((False, a), (True, b), (True, c)),        # (7)  -s(k,j) v s(k,j-1) v s(k-1,j-1)
                           ((False, a), (True, b), (True, p)),        # (8)  -s(k,j) v s(k,j-1) v p_j
                           ((False, b), (True, a)),                   # (9)  -s(k,j-1) v s(k,j)
                           ((False, c), (False, p), (True, a))):      # (10) -s(k-1,j-1) v -p_j v s(k,j)
                lits, satisfied = [], False
                for positive, v in clause:
                    if v in (TRUE, FALSE):
                        if (v == TRUE) == positive:
                            satisfied = True
                            break
                        continue
                    lits.append(v if positive else -v)
                if satisfied:
                    continue
                if len(lits) < 2:
                    raise AssertionError(f"a unit or empty clause arose at k={k}, j={j}: {lits}")
                key = tuple(sorted(lits))
                if key not in seen:
                    seen.add(key)
                    out.append(tuple(lits))
    return out, var


def progressions(C, n):
    """(d, the terms its CBound constrains) for d = 1..floor(n / (C + 1)), Proposition 6 applied."""
    for d in range(1, n // (C + 1) + 1):
        m = n // d
        if ((m - 1) % 2 == 1) == (C % 2 == 0):
            m -= 1
        yield d, [d * i for i in range(1, m + 1)]


def edp(C, n):
    """edp(C, n): (variables, clauses, counters), counters [(d, terms, {(k, j): variable})]."""
    top = [n]

    def newvar():
        top[0] += 1
        return top[0]

    clauses, counters = [], []
    for d, terms in progressions(C, n):
        cl, var = cbound(terms, C, newvar)
        clauses += cl
        counters.append((d, terms, var))
    return top[0], clauses, counters


def extend(x, counters):
    """Proposition 2: the terms (x[0] is x_1) and every counter's s(k, j), as a set of true literals."""
    lits = {i if v > 0 else -i for i, v in enumerate(x, start=1)}
    for _, terms, var in counters:
        plus = [0]
        for t in terms:
            plus.append(plus[-1] + (x[t - 1] > 0))
        for (k, j), v in var.items():
            lits.add(v if plus[j] >= k else -v)
    return lits


def unsatisfied(lits, clauses):
    return sum(1 for c in clauses if not any(l in lits for l in c))


def consistent(clauses, units):
    """Whether the clauses with these unit literals have a model: unit propagation, then search on what it leaves."""
    def propagate(assign):
        changed = True
        while changed:
            changed = False
            for c in clauses:
                free, sat = [], False
                for l in c:
                    v = assign.get(abs(l))
                    if v is None:
                        free.append(l)
                    elif v == (l > 0):
                        sat = True
                        break
                if sat:
                    continue
                if not free:
                    return None
                if len(free) == 1:
                    assign[abs(free[0])] = free[0] > 0
                    changed = True
        return assign

    def search(assign):
        assign = propagate(dict(assign))
        if assign is None:
            return False
        open_vars = {abs(l) for c in clauses for l in c} - set(assign)
        if not open_vars:
            return True
        v = min(open_vars)
        return search({**assign, v: True}) or search({**assign, v: False})

    return search({abs(u): u > 0 for u in units})


def exhaustive(limit=EXHAUSTIVE_N):
    """Control (b): (sequences listed, disagreements, rows by (C, n))."""
    total, wrong, rows = 0, 0, []
    for C in (1, 2):
        for n in range(1, limit + 1):
            _, clauses, _ = edp(C, n)
            bad = 0
            for signs in itertools.product((1, -1), repeat=n):
                units = [i if v > 0 else -i for i, v in enumerate(signs, start=1)]
                if consistent(clauses, units) != (discrepancy(signs) <= C):
                    bad += 1
            total += 2 ** n
            wrong += bad
            rows.append({"C": C, "n": n, "sequences": 2 ** n, "disagreements": bad})
    return total, wrong, rows


# ---------------------------------------------------------------- the shuffle

def shuffled(items, stream):
    items = list(items)
    for i in range(len(items) - 1, 0, -1):
        j = stream.below(i + 1)
        items[i], items[j] = items[j], items[i]
    return items


def renamed(nv, clauses, seed):
    """Rule 5: (clauses renamed and shuffled, the renaming new -> old)."""
    stream = H.Stream(seed, "edp/shuffle")
    perm = shuffled(range(1, nv + 1), stream)              # old variable i becomes perm[i - 1]
    old_of = {new: old for old, new in enumerate(perm, start=1)}
    out = []
    for c in shuffled(clauses, stream):
        out.append(tuple(shuffled([perm[abs(l) - 1] if l > 0 else -perm[abs(l) - 1] for l in c], stream)))
    return out, old_of


def dimacs(nv, clauses):
    return b"p cnf %d %d\n" % (nv, len(clauses)) + H.clause_lines(clauses)


# ---------------------------------------------------------------- the run

def summarise(values):
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters")
    return out


def solve(tools, cnf, work, tag, log):
    r = H.solve(tools, cnf, work, tag, heap=HEAP_MB, stack=STACK_MB)
    if r["answer"] == "unsat" and not r["verified"] and r["resources"]:
        log(f"edp: {tag}: cake_lpr ran out of room; again with {RETRY_HEAP_MB} MB")
        r = H.solve(tools, cnf, work, tag, heap=RETRY_HEAP_MB, stack=RETRY_STACK_MB)
    return r


def run(seed, inputs="inputs", results="results", tools=None, exhaustive_n=EXHAUSTIVE_N, log=print):
    """Every rule, in order; returns (outputs, detail). tools, if given, replaces the build (tests only)."""
    started = time.monotonic()
    data = {name: load(inputs, name) for name, *_ in INPUTS}     # every input checked before anything runs
    detail = {"inputs": [{"name": n, "sha256": h, "bytes": b, "source": s} for n, h, b, s in INPUTS]}
    values, controls = {}, []

    # Rule 1: the paper's sequence.
    tex = gzip.decompress(data["SAT14_Arxiv.tex.gz"]).decode("utf-8")
    x = paper(tex)
    disc = discrepancy(x)
    ext = [discrepancy(x + [1]), discrepancy(x + [-1])]
    values.update({"witness_terms": len(x), "witness_discrepancy": disc,
                   "witness_ok": int(len(x) == N_WITNESS and disc <= C_BOUND),
                   "extensions_discrepancy": f"{ext[0]},{ext[1]}"})
    detail["witness"] = {"terms": len(x), "discrepancy": disc, "plus": sum(1 for v in x if v > 0),
                         "term_60": x[FIXED - 1] if len(x) >= FIXED else None, "extensions": ext,
                         "sha256_signs": hashlib.sha256("".join("+" if v > 0 else "-" for v in x).encode()).hexdigest()}
    log(f"edp: the paper's sequence: {len(x)} terms, discrepancy {disc}; extended by +1 or -1: {ext}")

    # Rule 2: the formulas.
    sizes = {}
    formulas = {}
    for n in (N_WITNESS, N_PROOF):
        nv, clauses, counters = edp(C_BOUND, n)
        sizes[n] = (nv, len(clauses))
        formulas[n] = (nv, clauses, counters)
    values.update({"cnf_vars_1160": sizes[1160][0], "cnf_clauses_1160": sizes[1160][1],
                   "cnf_vars_1161": sizes[1161][0], "cnf_clauses_1161": sizes[1161][1],
                   "sizes_as_printed": int(all(sizes[n] == PRINTED[n] for n in PRINTED))})
    detail["formulas"] = {str(n): {"variables": sizes[n][0], "clauses": sizes[n][1], "printed": PRINTED[n]} for n in sizes}
    log(f"edp: edp(2, 1160) {sizes[1160]}, edp(2, 1161) {sizes[1161]}; printed {PRINTED[1160]}, {PRINTED[1161]}")

    # Control (a): the paper's sequence is a model of edp(2, 1160).
    if len(x) == N_WITNESS:
        y = x if x[FIXED - 1] > 0 else [-v for v in x]
        nv, clauses, counters = formulas[N_WITNESS]
        lits = extend(y, counters)
        missed = unsatisfied(lits, clauses + [(FIXED,)])
        controls.append({"control": "the paper's sequence, extended by Proposition 2, satisfies edp(2, 1160) and the "
                                    "unit x_60", "passed": missed == 0, "unsatisfied": missed,
                         "negated": y is not x})
    else:
        controls.append({"control": "the paper's sequence satisfies edp(2, 1160)", "passed": False,
                         "unsatisfied": None, "reason": f"{len(x)} terms, not {N_WITNESS}"})

    # Control (b): every short sequence.
    total, wrong, rows = exhaustive(exhaustive_n)
    values.update({"exhaustive_sequences": total, "exhaustive_disagreements": wrong})
    controls.append({"control": f"edp(C, n) has a model exactly when the sequence's discrepancy is at most C, for C = 1, "
                                f"2 and every sequence of up to {exhaustive_n} terms", "passed": wrong == 0,
                     "sequences": total, "disagreements": wrong})
    detail["exhaustive"] = rows
    log(f"edp: {total} short sequences against the formula, {wrong} disagreements, at {time.monotonic() - started:.0f} s")

    # The tools.
    os.makedirs(results, exist_ok=True)
    if tools is None:
        if platform.machine() not in ("x86_64", "AMD64"):
            raise SystemExit("edp/check.py: cake_lpr.S is x86-64 assembly; run this on an x86-64 machine")
        tools = H.build_tools(os.path.abspath(inputs), os.path.abspath(os.path.join(results, "build")))
        log(f"edp: built CaDiCaL {tools['cadical_version']} ({tools['cadical_files']} files) and cake_lpr, "
            f"gcc {tools['gcc']}, at {time.monotonic() - started:.0f} s")
    work = tempfile.mkdtemp(prefix="edp-", dir=os.path.abspath(results))
    try:
        # Control (c): C = 1.
        c1 = {}
        for n in (11, 12):
            nv, clauses, _ = edp(1, n)
            path = os.path.join(work, f"c1-{n}.cnf")
            with open(path, "wb") as f:
                f.write(dimacs(nv, clauses))
            r = solve(tools, path, work, f"c1-{n}", log)
            terms = None
            if r["answer"] == "sat":
                m = H.model(r["model"])
                if H.satisfies(m, clauses) == 0:
                    terms = discrepancy([1 if i in m else -1 for i in range(1, n + 1)])
            c1[n] = {"answer": r["answer"], "verified": r["verified"], "model_discrepancy": terms}
        passed = (c1[11]["answer"] == "sat" and c1[11]["model_discrepancy"] == 1 and c1[12]["answer"] == "unsat"
                  and c1[12]["verified"])
        controls.append({"control": "C = 1: edp(1, 11) satisfiable with a model of discrepancy 1, edp(1, 12) refuted "
                                    "with a verified proof", "passed": passed, "runs": c1})
        values["c1_boundary"] = (f"11 {c1[11]['answer']} (model discrepancy {c1[11]['model_discrepancy']}); "
                                 f"12 {c1[12]['answer']}{', verified' if c1[12]['verified'] else ''}")

        # Control (d): the pigeonhole proof controls.
        rows, ok = H.proof_controls(tools, work)
        controls += [{"control": r["control"], "passed": r["passed"], "checker_said": r["checker_said"]} for r in rows]

        # Rule 3: the proof.
        nv, clauses, _ = formulas[N_PROOF]
        mixed, old_of = renamed(nv, clauses + [(FIXED,)], seed)
        text = dimacs(nv, mixed)
        values["cnf_sha256"] = hashlib.sha256(text).hexdigest()
        path = os.path.join(work, "edp-2-1161.cnf")
        with open(path, "wb") as f:
            f.write(text)
        log(f"edp: solving edp(2, 1161) ({nv} variables, {len(mixed)} clauses with the unit), its proof checked as "
            f"it is written, from {time.monotonic() - started:.0f} s")
        r = solve(tools, path, work, "edp-2-1161", log)
        found = None
        if r["answer"] == "sat":
            m = H.model(r["model"])
            back = {old_of[abs(l)] if l > 0 else -old_of[abs(l)] for l in m}
            found = discrepancy([1 if i in back else -1 for i in range(1, N_PROOF + 1)])
        values.update({"unsat_answer": r["answer"], "unsat_verified": int(r["answer"] == "unsat" and r["verified"])})
        detail["proof"] = {k: r[k] for k in ("answer", "solver_rc", "checker_rc", "verified", "conflicts", "seconds",
                                             "checker_said", "solver_said")}
        detail["proof"]["model_discrepancy"] = found
        log(f"edp: edp(2, 1161): {r['answer']}, verified {r['verified']}, {r['conflicts']} conflicts, "
            f"{r['seconds']} s (checker: {r['checker_said']!r})")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    values.update({"controls_passed": sum(1 for c in controls if c["passed"]), "controls_total": len(controls),
                   "solver": f"CaDiCaL {tools['cadical_version']}", "checker": H.CHECKER})
    values["test_passed"] = int(values["witness_ok"] == 1 and values["unsat_verified"] == 1)
    detail.update({"controls": controls, "seconds": round(time.monotonic() - started, 1),
                   "tools": {k: v for k, v in tools.items() if k not in ("cadical", "cake_lpr")}})
    return summarise(values), detail


def main():
    parser = argparse.ArgumentParser(description="Erdős discrepancy, C = 2: the 1,160-term sequence and the 1,161 proof")
    parser.add_argument("--exhaustive", type=int, default=EXHAUSTIVE_N, help=f"control (b)'s longest n ({EXHAUSTIVE_N})")
    args = parser.parse_args()
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, detail = run(seed, exhaustive_n=args.exhaustive, log=lambda line: print(line, file=sys.stderr, flush=True))
    except Refused as e:
        sys.exit(f"edp/check.py: refused: {e}")
    os.makedirs("results", exist_ok=True)
    with open(os.path.join("results", "outputs.json"), "w", encoding="ascii") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(os.path.join("results", "detail.json"), "w", encoding="ascii") as f:
        json.dump(detail, f, indent=1, sort_keys=True)
        f.write("\n")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
