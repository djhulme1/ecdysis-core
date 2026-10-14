#!/usr/bin/env python3
"""Fukś's solution of the density classification problem with two cellular automata rules, 184 and then 232.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:2a8b885d78824863) is from Fukś, "Solution
of the Density Classification Problem with Two Cellular Automata Rules" (Physical Review E 55, R2081, 1997;
arXiv:comp-gas/9703001): "We show that a pair of elementary rules, namely the "traffic rule" 184 and the "majority
rule" 232, performs the task perfectly."

Its registered test: refuted if, for some ring of L cells, L from 2 to 26, some configuration s is not left by
n = floor((L-2)/2) steps of rule 184 and then m = floor((L-1)/2) steps of rule 232 (the paper's Proposition 4) as all
0's when its density rho < 1/2, all 1's when rho > 1/2, and alternating 0's and 1's when rho = 1/2. Every one of the
2^L configurations of each L is tried. Rules 184 and 232 in Wolfram's numbering, whose tables the paper prints.

Standard library and the image's gcc: the rings are run in C (ca/fuks.c, compiled here). The input is the claim's
data of record, arXiv's source of the paper (a gzipped tar of its TeX and a figure), checked against its SHA-256 and
size and opened in memory; its TeX is read as text and nothing in it is run. Every rule below was fixed before any
ring was run.

1. Reading. The member pre.tex. Its text, with runs of white space made one space, must state Proposition 4's step
   counts and composition (STATEMENTS below), and its three printed rule tables (the eqnarray* environments of the
   form "abc \\rightarrow d", in order: rule 184's, rule 232's and the simplified rule 32's) are read and turned into
   Wolfram numbers (bit 4a + 2b + c is d); a table that is not eight distinct neighbourhoods refuses the run.
2. The test. For every L from 2 to 26 and every configuration of the ring of L cells (periodic boundaries, as the
   paper assumes), n = floor((L-2)/2) steps of rule 184 and then m = floor((L-1)/2) steps of rule 232, both by their
   numbers. The result must be all 0's if twice the number of 1's is below L, all 1's if above, and alternating (in
   either phase) if equal. test_passed is 1 if no configuration of any L is misclassified.
3. Beside the test, none of it counted: whether the printed tables are rules 184, 232 and 32; Proposition 2 (after n
   steps of rule 184 no 00 block when rho > 1/2, no 11 block when rho < 1/2, neither at 1/2), and, for each L, the
   most steps of rule 184 any configuration needs to reach that state and the most steps of rule 232 any needs after
   them, against n and m; the paper's preimage formula (its equation for P_m(00), transcribed below) against the
   number of blocks of length 2m + 2, by their number of 1's, that m steps of rule 184's block map send to 00, for
   m = 0 to 11; and its asymptotic expansion against the exact formula at t = 1000 for p = 0.3, 0.5 and 0.7, as the
   ratio of P_t - P_inf to the printed correction term.

Controls (controls_passed counts those that behave as stated): the C step against a cell-by-cell step written here,
on seed-drawn configurations of rings of 5, 8, 13 and 26 cells, for rules 184 and 232; the C preimage count against a
cell-by-cell count for m = 0 to 5; the rules in the other order (232 and then 184) misclassify some configuration of
every ring from 7 to 12 cells; and Wolfram numbering on tables built here (rules 30, 90, 110 and 184).

What it cannot check: Proposition 4 for rings above 26 cells (it is proved for every L), and the paper's remarks on
generalised traffic rules and other critical densities.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 ca/fuks.py
"""

import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from fractions import Fraction

INPUT = ("arXiv-comp-gas-9703001v1.tar.gz", "7ef216b302e14bbc319ccc71a76ad83128506c6c07fee7bded37c71fed63bd10", 62298)
MEMBER = "pre.tex"
L_MIN, L_MAX = 2, 26
PRE_MAX = 11
STATEMENTS = (
    "let $n=\\lfloor (L-2)/2 \\rfloor$, $m=\\lfloor (L-1)/2 \\rfloor$. Then $F_{232}^m(F_{184}^{n}(s))$ consists of "
    "only 0's if $\\rho<1/2$ and of only 1's if $\\rho>1/2$.",
    "(1-p)^2\\sum_{k=1}^{m+1}(N_{2m,2k-2}&-& \\\\ \\nonumber -N_{2m,2k+2}) p^{m-k+1} (1-p)^{m+k-1}.",
    "N_{a,b}=\\left( \\begin{array}{c} a \\\\ \\frac{1}{2}(a+b) \\end{array} \\right),",
    "and $N_{a,b}=0$ if $b>a$.",
)
TABLE_RULES = (184, 232, 32)
OUTPUTS = ("statements", "tables", "prop4", "configurations", "misclassified", "first_failure", "bounds", "prop2",
           "preimages", "asymptotics", "conditions_met", "conditions_total", "test_passed", "controls_passed",
           "controls_total")
LIMIT = 200
HERE = os.path.dirname(os.path.abspath(__file__))


class Refused(Exception):
    pass


# ---------------------------------------------------------------- reading the source

def read_input(inputs):
    name, sha, size = INPUT
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha or len(data) != size:
        raise Refused(f"{name}: sha256 {got} ({len(data)} bytes), not the registered {sha} ({size})")
    return data


def tex_of(data):
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            members = [m for m in tar.getmembers() if m.name == MEMBER]
            if len(members) != 1 or not members[0].isfile():
                raise Refused(f"the source holds {len(members)} regular members named {MEMBER}")
            raw = tar.extractfile(members[0]).read()
    except (tarfile.TarError, OSError, EOFError) as e:
        raise Refused(f"the source is not a gzipped tar: {e}")
    try:
        return raw.decode("ascii")
    except UnicodeDecodeError as e:
        raise Refused(f"{MEMBER} is not ASCII: {e}")


def flat(text):
    return " ".join(text.split())


def statements_found(tex):
    f = flat(tex)
    return {s: flat(s) in f for s in STATEMENTS}


def tables(tex):
    """The printed rule tables, in order, as {neighbourhood: new state}."""
    out = []
    for m in re.finditer(r"\\begin\{eqnarray\*\}(.*?)\\end\{eqnarray\*\}", tex, re.S):
        pairs = re.findall(r"([01]{3})\s*\\rightarrow\s*([01])", m.group(1))
        if not pairs:
            continue
        table = {}
        for nb, v in pairs:
            if nb in table:
                raise Refused(f"a printed table gives {nb} twice")
            table[nb] = int(v)
        if len(table) != 8:
            raise Refused(f"a printed table has {len(table)} neighbourhoods")
        out.append(table)
    return out


def wolfram(table):
    return sum(v << int(nb, 2) for nb, v in table.items())


# ---------------------------------------------------------------- cell by cell, for the controls

def step_cells(x, rule, L):
    bits = [(x >> i) & 1 for i in range(L)]
    out = 0
    for i in range(L):
        k = 4 * bits[(i - 1) % L] + 2 * bits[i] + bits[(i + 1) % L]
        out |= ((rule >> k) & 1) << i
    return out


def pre_cells(rule, m):
    counts = [0] * (2 * m + 3)
    for s in range(1 << (2 * m + 2)):
        b = [(s >> i) & 1 for i in range(2 * m + 2)]
        for _ in range(m):
            b = [(rule >> (4 * b[i] + 2 * b[i + 1] + b[i + 2])) & 1 for i in range(len(b) - 2)]
        if b == [0, 0]:
            counts[bin(s).count("1")] += 1
    return counts


# ---------------------------------------------------------------- the paper's formula

def n_ab(a, b):
    if b > a or (a + b) % 2:
        return 0
    return math.comb(a, (a + b) // 2)


def formula_counts(m):
    """Equation (resulteq) read as counts: the coefficient of p^j (1-p)^(2m+2-j), j = m - k + 1."""
    counts = [0] * (2 * m + 3)
    for k in range(1, m + 2):
        counts[m - k + 1] += n_ab(2 * m, 2 * k - 2) - n_ab(2 * m, 2 * k + 2)
    return counts


def p_exact(m, p):
    """P_m(00) by the printed formula, exactly, for a rational p = a/b: one integer sum over b^(2m+2)."""
    p = Fraction(p)
    a, b = p.numerator, p.denominator
    num = sum((n_ab(2 * m, 2 * k - 2) - n_ab(2 * m, 2 * k + 2)) * a ** (m - k + 1) * (b - a) ** (m + k + 1)
              for k in range(1, m + 2))
    return Fraction(num, b ** (2 * m + 2))


def log_abs(x):
    """log |x| for a nonzero Fraction, through its integer parts."""
    return math.log(abs(x.numerator)) - math.log(x.denominator)


def asymptotic_ratio(t, p):
    """(P_t - P_inf) over the printed correction term, P_inf = 1 - 2p below 1/2 and 0 otherwise."""
    p = Fraction(p).limit_denominator(1000)
    inf = 1 - 2 * p if p < Fraction(1, 2) else Fraction(0)
    diff = p_exact(t, p) - inf
    lead = p if p < Fraction(1, 2) else 1 - p
    log_corr = math.log(lead) + t * math.log(4 * p * (1 - p)) - 0.5 * math.log(math.pi * t)
    return math.exp(log_abs(diff) - log_corr) * (1 if diff > 0 else -1) if diff else 0.0


# ---------------------------------------------------------------- the C program

def build(work):
    exe = os.path.join(work, "fuks")
    subprocess.run(["gcc", "-O2", "-std=gnu11", "-o", exe, os.path.join(HERE, "fuks.c")], check=True)
    return exe


def ring(exe, a, b, L, n, m):
    out = subprocess.run([exe, "ring", str(a), str(b), str(L), str(n), str(m)], check=True, capture_output=True,
                         text=True).stdout.split()
    k = list(map(int, out))
    return {"L": k[0], "configurations": k[1], "misclassified": k[2], "first": k[3], "most_a": k[4],
            "most_b": k[5], "uncleared": k[6]}


def c_step(exe, rule, L, x, t=1):
    return int(subprocess.run([exe, "step", str(rule), str(L), str(x), str(t)], check=True, capture_output=True,
                              text=True).stdout)


def c_pre(exe, rule, m):
    return list(map(int, subprocess.run([exe, "pre", str(rule), str(m)], check=True, capture_output=True,
                                        text=True).stdout.split()))


class Stream:
    def __init__(self, seed, label):
        self.seed, self.label, self.n = seed, label, 0

    def below(self, m):
        self.n += 1
        h = hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
        return int.from_bytes(h[:8], "big") % m


def steps(L):
    return (L - 2) // 2, (L - 1) // 2


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    if shutil.which("gcc") is None:
        raise Refused("no gcc in this image")
    data = read_input(inputs)
    tex = tex_of(data)
    stmts = statements_found(tex)
    if not all(stmts.values()):
        raise Refused("the TeX does not state " + next(s for s, ok in stmts.items() if not ok)[:60])
    printed = [wolfram(t) for t in tables(tex)]
    os.makedirs(results, exist_ok=True)
    work = tempfile.mkdtemp(prefix="work-", dir=results)
    try:
        exe = build(work)
        rows = []
        for L in range(L_MIN, L_MAX + 1):
            n, m = steps(L)
            r = ring(exe, 184, 232, L, n, m)
            r.update(n=n, m=m)
            rows.append(r)
        pre = {m: c_pre(exe, 184, m) for m in range(PRE_MAX + 1)}
        # controls
        ctl, ctl_detail = {}, {}
        st = Stream(seed, "fuks/step")
        same = True
        for L in (5, 8, 13, 26):
            for _ in range(50):
                x = st.below(1 << L)
                for rule in (184, 232):
                    if c_step(exe, rule, L, x) != step_cells(x, rule, L):
                        same = False
        ctl["the C step equals a cell-by-cell step on 200 seed-drawn rings, rules 184 and 232"] = same
        ctl["the C preimage count equals a cell-by-cell count, m = 0 to 5"] = all(
            pre[m] == pre_cells(184, m) for m in range(6))
        swapped = [ring(exe, 232, 184, L, *reversed(steps(L))) for L in range(7, 13)]
        ctl["232 and then 184 misclassify some configuration of every ring of 7 to 12 cells"] = all(
            r["misclassified"] > 0 for r in swapped)
        ctl_detail["swapped_misclassified"] = {r["L"]: r["misclassified"] for r in swapped}
        built = {30: "00011110", 90: "01011010", 110: "01101110", 184: "10111000"}
        ctl["Wolfram numbering on tables built here (30, 90, 110, 184)"] = all(
            wolfram({format(k, "03b"): int(bits[7 - k]) for k in range(8)}) == num for num, bits in built.items())
    finally:
        shutil.rmtree(work, ignore_errors=True)

    wrong = sum(r["misclassified"] for r in rows)
    total = sum(r["configurations"] for r in rows)
    first = next((r for r in rows if r["misclassified"]), None)
    cond = {"no configuration of any ring of 2 to 26 cells misclassified by 184 then 232 (Proposition 4)": wrong == 0}
    prop2 = all(r["uncleared"] == 0 for r in rows)
    tight_a = [r["L"] for r in rows if r["most_a"] < r["n"]]
    tight_b = [r["L"] for r in rows if r["most_b"] < r["m"]]
    formula_ok = {m: pre[m] == formula_counts(m) for m in pre}
    bad_m = [m for m, ok in formula_ok.items() if not ok]
    asym = {}
    for p in (0.3, 0.5, 0.7):
        asym[p] = asymptotic_ratio(1000, p)

    def ints(v):
        return ", ".join(map(str, v)) if v else "none"

    values = {
        "statements": (f"Proposition 4, the formula for P_m(00) and N_ab, in the TeX: {sum(stmts.values())} of "
                       f"{len(stmts)}"),
        "tables": "the printed tables are rules " + ", ".join(map(str, printed)) + f" (expected {ints(TABLE_RULES)})",
        "prop4": (f"rings of {L_MIN} to {L_MAX} cells, every configuration ({total:,} in all): {wrong} misclassified"),
        "configurations": total,
        "misclassified": wrong,
        "first_failure": (f"L = {first['L']}, s = {first['first']}" if first else "none"),
        "bounds": (f"most steps needed: of 184 below n at L = {ints(tight_a)}; of 232 below m at L = {ints(tight_b)}"),
        "prop2": ("after n steps of 184 no 00 block above 1/2, no 11 below, neither at 1/2: "
                  + ("every configuration of every ring" if prop2 else
                     f"{sum(r['uncleared'] for r in rows)} configurations not")),
        "preimages": ("P_m(00) as printed against counted preimages, m = 0 to 11: "
                      + ("equal for every m" if not bad_m else f"differs at m = {ints(bad_m)}")),
        "asymptotics": ("(P_t - P_inf) over the printed correction at t = 1000: " + ", ".join(
            f"{asym[p]:.4f} at p = {p}" for p in (0.3, 0.5, 0.7))),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for key, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")
    detail = {"input": {"name": INPUT[0], "sha256": INPUT[1], "bytes": INPUT[2], "member": MEMBER},
              "statements": stmts, "printed_tables": printed, "rings": rows, "preimages": pre,
              "formula": {m: formula_counts(m) for m in pre}, "formula_ok": formula_ok, "asymptotics": asym,
              "conditions": cond, "controls": ctl, "control_detail": ctl_detail}
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
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"fuks: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
