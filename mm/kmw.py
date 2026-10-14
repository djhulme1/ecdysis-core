#!/usr/bin/env python3
"""Kauers, Moosbauer & Wood's structured 6 x 6 decomposition: its shared factors, and the exponent they give.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:3f1191ab8f46c911) is from Kauers, Moosbauer
& Wood, "Exploiting the Structure in Tensor Decompositions for Matrix Multiplication" (arXiv:2602.11041v3): "Thanks to
these features we obtain exponents lower than what the rank of the tensor decomposition suggests. In particular for
$6\\times 6$ matrix multiplication we reduce the exponent of the recent algorithm by Moosbauer and Poole from $2.8075$
to $2.8019$, while retaining a reasonable leading coefficient."

Its registered test: refuted if the authors' released decomposition of <6,6,6> (mkauers/matrix-multiplication at
12c26b2, structured/666.exp; the paper's convention sum a_ij b_jk c_ki) is not an exact rank-153 decomposition over the
integers; or if it holds fewer than 18 disjoint pairs of terms sharing a factor up to sign, 6 sharing A, 6 B and 6 C
(the paper's 117<1,1,1> + 6<1,1,2> + 6<2,1,1> + 6<1,2,1>); or if the exponent the paper's Theorem gives for that
structure, (nmp)^w = sum s_i s_j s_k (n_i m_j p_k)^(w-2) n_k m_i p_j n_j m_k p_i, is 2.80195 or more.

Standard library only. The inputs are the claim's data of record, the repository's files structured/666.exp and
structured/666r153.exp at 12c26b2 (GPL-3.0), each checked against its SHA-256 and read as text; nothing in them is run.
mm/check.py's reader of the .exp format and its exactness test are used as they are. Every rule below was fixed before
the files' structure or exactness was computed; the paper's own block counts were put through the formula beforehand
(2.801896 and 2.805066, its printed 2.80190 and 2.805065).

1. Reading: mm/check.py's read_flips, one product per line, (A-form)*(B-form)*(C-form) over a_ij (6 x 6), b_jk and
   c_ki; 153 products are required of each file.
2. Exact: every one of the 46,656 coefficients of sum_t u_t (x) v_t (x) w_t equals the tensor's, over the integers
   (mm/check.py's wrong_entries).
3. Shared factors. Two products share a factor if their A-forms, or their B-forms, or their C-forms, are equal or
   negatives of each other; a pair sharing its A-form is a copy of <1,1,2> (a_11 b_1k c_k1: one A-form, two B-forms
   and two C-forms), one sharing its B-form a copy of <2,1,1>, one sharing its C-form a copy of <1,2,1>. A structure
   is a set of disjoint pairs (a matching in the graph that joins products sharing a factor, each edge labelled by
   the factor it shares). Every matching of each connected part of the graph is enumerated, so the achievable counts
   (pairs sharing A, B, C) are known exactly.
4. The exponent of a structure: with q = the pairs, the blocks are (153 - 2q) x <1,1,1>, and the pairs' counts of
   <1,1,2>, <2,1,1> and <1,2,1>; w solves the paper's equation (its symmetrised restriction, from Theorem 3.2),
   (nmp)^w = sum_{i,j,k} s_i s_j s_k (n_i m_j p_k)^(w-2) n_k m_i p_j n_j m_k p_i with n = m = p = 6, by bisection on
   [2, 3] to 1e-12.
5. The test's three conditions for 666.exp: exact with 153 products; some structure has at least 6 pairs sharing each
   of A, B and C (18 in all); and the exponent of the structure 117, 6, 6, 6 is below 2.80195. test_passed is 1 if
   all three hold.
6. Beside, not counted: the largest structures and the lowest exponent any structure of 666.exp gives; the same for
   666r153.exp, against the paper's 137<1,1,1> + 8<2,1,1> and 2.805065 for Moosbauer and Poole's decomposition; and
   the exponent of the rank alone, log_6 153, and Strassen's log_2 7.

Controls (controls_passed counts those that hold): Strassen's scheme is exact under the same test and one altered
coefficient is caught; the formula gives log_2 7 for <2,2,2> <= 7<1,1,1>, and the paper's printed 2.805065 and 2.80190
for its two block counts to within a unit of their last decimal; and the matching search finds no pairs in Strassen's scheme and the known pairs in a small
table built here.

What it cannot check: the paper's algorithm and its proof (Theorem 3.2, corrected in v3), and its leading coefficients.

Writes results/outputs.json and results/detail.json. Run with: python3 mm/kmw.py
"""

import hashlib
import importlib.util
import itertools
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("mm_check", os.path.join(HERE, "check.py"))
CHECK = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CHECK)

INPUTS = {"structured": ("structured-666.exp", "8d356efa699eb72ac66ff5a42bd71adfa3125ed980097517c58c9760748221dd"),
          "r153": ("structured-666r153.exp", "9c8cf3986e5e7aa1a9cf4c0c205e3c9eb05be2462f25224417947aebcc5fd213")}
N = 6
RANK = 153
SHAPE = {"A": (1, 1, 2), "B": (2, 1, 1), "C": (1, 2, 1)}
NEED = 6
BOUND = 2.80195
PRINTED = {"structured": 2.80190, "moosbauer_poole": 2.805065}
LIMIT = 200
# A small table for the matching control: products 0-1 share A (up to sign), 1-2 share B, 2-3 share C.
TOY = [({0: 1}, {0: 1}, {0: 1}), ({0: -1}, {1: 1}, {1: 1}), ({2: 1}, {1: -1}, {2: 1}), ({3: 1}, {3: 1}, {2: 1})]
OUTPUTS = ("products", "exact", "structure", "pairs", "omega", "omega_best", "omega_rank", "r153", "strassen",
           "conditions_met", "conditions_total", "test_passed", "controls_passed", "controls_total")


class Refused(Exception):
    pass


def read_input(inputs, key):
    name, sha = INPUTS[key]
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha:
        raise Refused(f"{name}: sha256 {got}, not the registered {sha}")
    return data


def normal(form):
    """A factor as a hashable key, up to sign: its sorted items, negated if its first coefficient is negative."""
    items = sorted(form.items())
    if items and items[0][1] < 0:
        items = [(k, -v) for k, v in items]
    return tuple(items)


def share_graph(scheme):
    """Edges (s, t, label) between products sharing a factor up to sign; label A, B or C (one edge per label)."""
    edges = []
    for label, pos in (("A", 0), ("B", 1), ("C", 2)):
        groups = {}
        for t, prod in enumerate(scheme):
            groups.setdefault(normal(prod[pos]), []).append(t)
        for members in groups.values():
            for s, t in itertools.combinations(members, 2):
                edges.append((s, t, label))
    return edges


def components(n, edges):
    adj = {v: set() for v in range(n)}
    for s, t, _ in edges:
        adj[s].add(t)
        adj[t].add(s)
    seen, parts = set(), []
    for v in range(n):
        if v in seen or not adj[v]:
            continue
        stack, part = [v], set()
        while stack:
            x = stack.pop()
            if x in part:
                continue
            part.add(x)
            stack.extend(adj[x] - part)
        seen |= part
        parts.append(sorted(part))
    return parts


def matchings_counts(nodes, edges, limit=24, edge_limit=60):
    """Every achievable (A, B, C) count of a matching in one connected part, by exhaustive search."""
    es = [e for e in edges if e[0] in nodes and e[1] in nodes]
    if len(nodes) > limit or len(es) > edge_limit:
        raise Refused(f"a part of {len(nodes)} products and {len(es)} shared factors is too large to search")
    out = set()

    def go(i, used, a, b, c):
        if i == len(es):
            out.add((a, b, c))
            return
        go(i + 1, used, a, b, c)
        s, t, label = es[i]
        if s not in used and t not in used:
            go(i + 1, used | {s, t}, a + (label == "A"), b + (label == "B"), c + (label == "C"))
    go(0, frozenset(), 0, 0, 0)
    return out


def achievable(scheme):
    """All (A, B, C) counts achievable by some structure of the scheme, and the graph's edges."""
    edges = share_graph(scheme)
    totals = {(0, 0, 0)}
    for part in components(len(scheme), edges):
        counts = matchings_counts(part, edges)
        totals = {(x + a, y + b, z + c) for (x, y, z) in totals for (a, b, c) in counts}
    return totals, edges


def omega_sym(n, m, p, blocks):
    """The paper's exponent for a restriction <n,m,p> <= sum s_i <n_i,m_i,p_i>, blocks given as (s, n, m, p)."""
    def f(w):
        tot = 0.0
        for (si, ni, mi, pi) in blocks:
            for (sj, nj, mj, pj) in blocks:
                for (sk, nk, mk, pk) in blocks:
                    tot += si * sj * sk * (ni * mj * pk) ** (w - 2) * nk * mi * pj * nj * mk * pi
        return (n * m * p) ** w - tot
    lo, hi = 2.0, 3.0
    if not (f(lo) < 0 < f(hi)):
        raise Refused("the exponent equation has no root between 2 and 3 for these blocks")
    while hi - lo > 1e-12:
        mid = (lo + hi) / 2
        if f(mid) > 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def blocks_of(rank, a, b, c):
    out = [(rank - 2 * (a + b + c), 1, 1, 1)]
    for count, label in ((a, "A"), (b, "B"), (c, "C")):
        if count:
            out.append((count,) + SHAPE[label])
    return out


def conditions(products, wrong, totals, omega_666):
    return {"666.exp is an exact decomposition of <6,6,6> in 153 products": products == RANK and wrong == 0,
            "some structure has at least 6 pairs sharing each of A, B and C": any(
                a >= NEED and b >= NEED and c >= NEED for a, b, c in totals),
            "the exponent of the structure 117, 6, 6, 6 is below 2.80195": omega_666 < BOUND}


def controls_known():
    st = CHECK.strassen()
    exact = CHECK.wrong_entries(st, 2, 2, 2, "Z") == 0
    u = dict(st[0][0])
    u[1] = u.get(1, 0) + 1
    caught = CHECK.wrong_entries([(u,) + tuple(st[0][1:])] + st[1:], 2, 2, 2, "Z") > 0
    formula = (abs(omega_sym(2, 2, 2, [(7, 1, 1, 1)]) - math.log2(7)) < 1e-9
               and abs(omega_sym(6, 6, 6, [(137, 1, 1, 1), (8, 2, 1, 1)]) - PRINTED["moosbauer_poole"]) < 1e-6
               and abs(omega_sym(6, 6, 6, blocks_of(RANK, NEED, NEED, NEED)) - PRINTED["structured"]) < 1e-5)
    toy = TOY
    toy_totals, _ = achievable(toy)
    matching = achievable(st)[0] == {(0, 0, 0)} and max(sum(t) for t in toy_totals) == 2 and (1, 0, 1) in toy_totals
    return {"Strassen's scheme is exact and an altered coefficient is caught": exact and caught,
            "the formula gives log2 7 and the paper's printed 2.805065 and 2.80190": formula,
            "the matching search finds no pairs in Strassen's scheme and the known pairs in a small table": matching}


def describe(totals, rank):
    best = max(totals, key=lambda t: (sum(t), -omega_sym(N, N, N, blocks_of(rank, *t))))
    low = min(totals, key=lambda t: omega_sym(N, N, N, blocks_of(rank, *t)))
    return best, low


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    data = {k: read_input(inputs, k) for k in INPUTS}
    schemes = {k: CHECK.read_flips(v, N, N, N) for k, v in data.items()}
    wrong = {k: CHECK.wrong_entries(s, N, N, N, "Z") for k, s in schemes.items()}
    found = {k: achievable(s) for k, s in schemes.items()}
    totals = found["structured"][0]
    best, low = describe(totals, len(schemes["structured"]))
    r_totals = found["r153"][0]
    r_best, r_low = describe(r_totals, len(schemes["r153"]))
    w666 = omega_sym(N, N, N, blocks_of(RANK, NEED, NEED, NEED))
    w_low = omega_sym(N, N, N, blocks_of(len(schemes["structured"]), *low))
    w_r = omega_sym(N, N, N, blocks_of(len(schemes["r153"]), *r_low))
    cond = conditions(len(schemes["structured"]), wrong["structured"], totals, w666)
    controls = {"both inputs are the pinned files": True, **controls_known()}

    def split(t):
        return f"A {t[0]}, B {t[1]}, C {t[2]}"
    values = {
        "products": f"666.exp {len(schemes['structured'])}, 666r153.exp {len(schemes['r153'])}",
        "exact": (f"wrong of 46,656 coefficients: 666.exp {wrong['structured']}, 666r153.exp {wrong['r153']}"),
        "structure": (f"666.exp: at most {sum(best)} disjoint pairs share a factor ({split(best)}); "
                      f"{len(found['structured'][1])} sharing edges in all"),
        "pairs": sum(best),
        "omega": round(w666, 6),
        "omega_best": round(w_low, 6),
        "omega_rank": round(math.log(RANK, N), 6),
        "r153": (f"666r153.exp: at most {sum(r_best)} pairs ({split(r_best)}), lowest exponent {w_r:.6f} "
                 f"({split(r_low)})"),
        "strassen": f"log2 7 = {math.log2(7):.6f}",
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(controls.values()), "controls_total": len(controls),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"inputs": {k: {"name": n, "sha256": s} for k, (n, s) in INPUTS.items()}, "conditions": cond,
              "controls": controls, "achievable_666": sorted(totals), "achievable_r153": sorted(r_totals),
              "edges_666": found["structured"][1], "edges_r153": found["r153"][1],
              "lowest_666": {"counts": low, "omega": w_low}, "lowest_r153": {"counts": r_low, "omega": w_r},
              "omega_117_6_6_6": w666}
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
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"kmw: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
