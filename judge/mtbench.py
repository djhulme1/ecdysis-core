#!/usr/bin/env python3
"""GPT-4 as a judge on MT-bench: its agreement with expert labelers, and theirs with one another, recounted from the
released judgements.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:745d633a969e7a42) is from Zheng, Chiang,
Sheng, Zhuang, Wu, Zhuang, Lin, Li, Li, Xing, Zhang, Gonzalez and Stoica, "Judging LLM-as-a-Judge with MT-Bench and
Chatbot Arena", arXiv:2306.05685 (NeurIPS 2023, Datasets and Benchmarks): "Our results reveal that strong LLM judges
like GPT-4 can match both controlled and crowdsourced human preferences well, achieving over 80% agreement, the same
level of agreement between humans."

Its registered test is TEST below. The controlled half is MT-bench (80 questions, answers by six models, judged
pairwise by GPT-4 and by 58 expert labelers, in two turns); the crowdsourced half, Chatbot Arena, is not tested: its
votes are in a gated dataset, which needs an account.

The inputs are the dataset's two files (lmsys/mt_bench_human_judgments on the Hugging Face hub at commit f7d2896,
CC BY 4.0): data/human-00000-of-00001-25f4910818759289.parquet (the human split) and
data/gpt4_pair-00000-of-00001-c0b431264a82ddc0.parquet (the gpt4_pair split), each checked against its SHA-256 and
read as data with pyarrow (the image's 13.0.0), only their columns question_id, model_a, model_b, winner, judge and
turn. None of the authors' code is run: rules 2 to 4 follow their agreement script (FastChat,
fastchat/llm_judge/compute_agreement.py as read on 15 October 2026, sha256
458f83de49c2284ee8baf65cfc67c60a46544c00131dea7eab083259467c465b), written again here. That script reads an earlier
JSON form of the data, in which GPT-4's judge is a list ("gpt-4", "pair-v2"); in these files it is the string
gpt4_pair. Every rule below was fixed before any agreement was computed. A syntax-only pass over the two files
beforehand read their schemas, their row counts (3,355 and 2,400, the dataset card's), their label sets and the
judges' names (58 experts and 7 authors), and no count of any vote. The seed draws only the bootstrap beside the
test. The paper's tables are numbered as its TeX numbers them (arXiv v4): Table 5 for the agreement on MT-bench,
Table 13 (the appendix's) for the full one.

1. The rows. Every row must have a question_id from 81 to 160, a model_a and a model_b that are two different models
   of the six (MODELS), and a turn of 1 or 2; a human row a winner of model_a, model_b or tie and a judge expert_<n>
   or author_<n>; a GPT-4 row a winner of model_a, model_b, tie or "tie (inconsistent)" and the judge gpt4_pair. The
   human split must have 3,355 rows and the GPT-4 split 2,400. Otherwise the run is refused.
2. Comparisons, as the authors' script builds them: a comparison is a question, its two models in alphabetical order
   and a turn; a vote recorded with its models the other way round has model_a and model_b exchanged in its winner.
   A comparison may have at most one GPT-4 judgement (the script asserts it), or the run is refused. The experts are
   the judges named expert_<n>, the paper's "Human" ("expert labelers (excluding authors)"); the authors, author_<n>,
   are its "Author".
3. The setups, as Table 5 and the script define them. S1 keeps every vote, and a vote containing "tie" (GPT-4's
   inconsistent judgements among them, which the paper "counts as tie") agrees with any other such vote. S2 leaves
   out every vote containing "tie".
4. Agreement, computed in the two ways the paper's words allow ("the probability of randomly selected individuals
   (but not identical) of each type agreeing on a randomly selected question"):
   (a) pooled, as the script computes it and the paper's counts ("#votes") show: GPT-4 against the experts, the pairs
       (GPT-4's judgement, an expert's vote) on each comparison, both kept by the setup; the experts with one another,
       every pair of two of a comparison's expert votes, both kept; the agreement is the share of all such pairs of
       the turn whose two votes agree;
   (b) by comparison, the text's "randomly selected question", a question read as its own example reads it (votes
       "A" or "B" on two answers to it): the share of agreeing pairs within each comparison that has at least one
       pair, averaged over those comparisons, each weighted equally. The experts' pairs are here only between two
       different experts ("not identical"); pairs of two votes by one expert on one comparison, if any, are left out
       here and counted (same_expert_pairs).
5. The test's conditions, for each turn and each computation of rule 4, in S2: GPT-4's agreement with the experts
   above 0.80; and not more than 0.05 below the experts' agreement with one another. Eight conditions, compared
   exactly in fractions; test_passed is 1 if all hold.
6. Beside the test: S1 by both computations; each cell of Table 5 and Table 13 that the rules can compute, by the
   pooled computation, against the count and the percentage printed (PRINTED: G4-Pair/Human, Human/Human,
   G4-P/Author, Author/Human, Author/Author and G4-P/Human-M, in both setups and both turns; a percentage matches
   within half a point); GPT-4 against the experts' majority, the paper's Human-M (on each comparison with GPT-4's
   judgement and at least one expert vote kept, the most frequent kept expert vote; when several are equally
   frequent the agreement is shared evenly among them, the paper's "even split"; one value per comparison); the
   experts against their majority, which Table 13 prints (Human/Human-M) but the paper does not define, in two
   readings, each kept expert vote on a comparison with at least two against the majority of all of them, its own
   included, or of the others; the judges and the votes (the paper: 58 expert labelers, "around 3K votes"); and 95%
   intervals for the S2 pooled agreements, GPT-4's with the experts, the experts' with one another and their
   difference, in each turn, from 2,000 resamples of the 80 questions (a drawn question bringing all its comparisons
   of the turn), drawn from ECDYSIS_SEED.
7. Controls, known answers: the paper's worked examples (three humans voting A, A and B agree with one another 1/3
   of the time, and GPT-4 agrees with them 2/3 if it voted A and 1/3 if B; with as many A as B votes, GPT-4's A
   agrees with the majority 1/2); a vote recorded the other way round; ties in S1 and S2, GPT-4's inconsistent
   judgements among them; a set on which the two computations of rule 4 differ (3/4 pooled, 1/2 by comparison); a
   pair of votes by one expert, counted by the pooled computation only; the two readings of Human/Human-M on A, A
   and B (2/3 and 1/3); and the reader on small files written here, with each refusal of rules 1 and 2.

What it cannot check: the answers and the votes themselves (the models, the questions and the labelers are as the
authors recorded them; whether a released vote is a labeler's first choice or one made after being shown GPT-4's
judgement, which the paper's collection allowed, neither the paper nor the card says), GPT-4's single-answer grading
(not in the dataset), and the crowdsourced half.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Needs pyarrow (the pinned jupyter/scipy-notebook image). Run with: python3 judge/mtbench.py
"""

import hashlib
import json
import os
import random
import re
import sys
from fractions import Fraction

TEST = (
    "Refuted if, in either turn of the released MT-bench judgements (lmsys/mt_bench_human_judgments at f7d2896: the "
    "58 experts' votes and GPT-4's pairwise judgements), with tie and inconsistent votes left out (the paper's S2), "
    "GPT-4's agreement with the experts is at most 80% or more than 5 points below the experts' agreement with one "
    "another, computed as the authors' script pools the votes or as the text defines agreement (each comparison of a "
    "question and a model pair weighted equally). Authors' votes are excluded. The crowdsourced half is not tested."
)
INPUTS = {
    "human": ("mtbench_human.parquet", "4877bc46a40929f4082c3c79593700fb897b1d6c7f4c473032694a01322f5769"),
    "gpt4": ("mtbench_gpt4_pair.parquet", "57068327ffb5f8fddb15fedbbfe40b26fe862da2326331e5cf64a42320a00e71"),
}
ROWS = {"human": 3355, "gpt4": 2400}
COLUMNS = ("question_id", "model_a", "model_b", "winner", "judge", "turn")
MODELS = ("alpaca-13b", "claude-v1", "gpt-3.5-turbo", "gpt-4", "llama-13b", "vicuna-13b-v1.2")
QUESTIONS = range(81, 161)
WINNERS = {"human": ("model_a", "model_b", "tie"), "gpt4": ("model_a", "model_b", "tie", "tie (inconsistent)")}
JUDGE = {"human": re.compile(r"(expert|author)_[0-9]+"), "gpt4": re.compile(r"gpt4_pair")}
AGREE_MIN, GAP_MAX = Fraction(4, 5), Fraction(1, 20)
BOOTSTRAP = 2000
SETUPS = ("S1", "S2")
TURNS = (1, 2)
# Table 5 and Table 13 (arXiv v4): (row judge, column judge, setup) -> {turn: (percentage, #votes)}.
PRINTED = {
    ("G4-Pair", "Human", "S1"): {1: (66, 1343), 2: (66, 1325)},
    ("G4-Pair", "Human", "S2"): {1: (85, 859), 2: (85, 864)},
    ("Human", "Human", "S1"): {1: (63, 721), 2: (67, 707)},
    ("Human", "Human", "S2"): {1: (81, 479), 2: (82, 474)},
    ("G4-P", "Author", "S1"): {1: (69, 345), 2: (66, 341)},
    ("G4-P", "Author", "S2"): {1: (92, 201), 2: (88, 205)},
    ("Author", "Human", "S1"): {1: (65, 428), 2: (68, 413)},
    ("Author", "Human", "S2"): {1: (83, 262), 2: (86, 273)},
    ("Author", "Author", "S1"): {1: (69, 49), 2: (67, 49)},
    ("Author", "Author", "S2"): {1: (87, 31), 2: (87, 31)},
    ("G4-P", "Human-M", "S1"): {1: (67, 821), 2: (68, 812)},
    ("G4-P", "Human-M", "S2"): {1: (85, 546), 2: (85, 557)},
}
# Table 13's Human/Human-M, which the paper does not define (rule 6's two readings are set against it).
PRINTED_HUMAN_M = {"S1": {1: (81, 892), 2: (83, 877)}, "S2": {1: (90, 631), 2: (91, 629)}}
OUTPUTS = ("votes", "g4_expert_s2_t1", "g4_expert_s2_t2", "expert_expert_s2_t1", "expert_expert_s2_t2",
           "g4_expert_s2_bycomp_t1", "g4_expert_s2_bycomp_t2", "expert_expert_s2_bycomp_t1",
           "expert_expert_s2_bycomp_t2", "s2_pairs", "s1_pooled", "s1_bycomp", "printed", "printed_counts_matched",
           "printed_percents_matched", "printed_cells", "authors", "majority", "same_expert_pairs", "bootstrap_t1",
           "bootstrap_t2", "conditions_met", "conditions_total", "test_passed", "controls_passed", "controls_total")
LIMIT = 200


class Refused(Exception):
    pass


def read_bytes(path, sha256):
    with open(path, "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha256:
        raise Refused(f"{path}: sha256 {got}, not the registered {sha256}")
    return data


def check_row(r, i, kind):
    """Rule 1 for one row."""
    q, a, b, t = r["question_id"], r["model_a"], r["model_b"], r["turn"]
    if type(q) is not int or q not in QUESTIONS:
        raise Refused(f"{kind} row {i}: question_id {q!r}")
    if a not in MODELS or b not in MODELS or a == b:
        raise Refused(f"{kind} row {i}: models {a!r} and {b!r}")
    if type(t) is not int or t not in TURNS:
        raise Refused(f"{kind} row {i}: turn {t!r}")
    if r["winner"] not in WINNERS[kind]:
        raise Refused(f"{kind} row {i}: winner {r['winner']!r}")
    if not isinstance(r["judge"], str) or not JUDGE[kind].fullmatch(r["judge"]):
        raise Refused(f"{kind} row {i}: judge {r['judge']!r}")


def read_rows(data, kind):
    """The rows of one split, from the parquet file's bytes, each checked by rule 1."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    try:
        table = pq.read_table(pa.BufferReader(data), columns=list(COLUMNS))
    except Exception as e:  # a file that is not parquet, or lacks a column
        raise Refused(f"{kind}: not a parquet file with columns {COLUMNS}: {e}") from None
    cols = {c: table.column(c).to_pylist() for c in COLUMNS}
    rows = [{c: cols[c][i] for c in COLUMNS} for i in range(table.num_rows)]
    for i, r in enumerate(rows):
        check_row(r, i, kind)
    return rows


def revert(w):
    return {"model_a": "model_b", "model_b": "model_a"}.get(w, w)


def comparisons(human, gpt4):
    """Rule 2: {turn: {(question, model, model): {"gpt4"|"expert"|"author": [(judge, winner)]}}}."""
    data = {t: {} for t in TURNS}
    for kind, rows in (("human", human), ("gpt4", gpt4)):
        for r in rows:
            a, b, w = r["model_a"], r["model_b"], r["winner"]
            key, w = ((r["question_id"], a, b), w) if a < b else ((r["question_id"], b, a), revert(w))
            cls = "gpt4" if kind == "gpt4" else r["judge"].split("_")[0]
            data[r["turn"]].setdefault(key, {}).setdefault(cls, []).append((r["judge"], w))
    for t in TURNS:
        for key, d in data[t].items():
            if len(d.get("gpt4", ())) > 1:
                raise Refused(f"turn {t}, comparison {key}: {len(d['gpt4'])} GPT-4 judgements")
    return data


def is_tie(w):
    return "tie" in w


def kept(w, setup):
    return setup == "S1" or not is_tie(w)


def agree(w1, w2):
    return (is_tie(w1) and is_tie(w2)) or w1 == w2


def cross(xs, ys, setup):
    """Pairs between two kinds of judge on one comparison: [(agree, same judge)]."""
    return [(agree(x, y), jx == jy) for jx, x in xs if kept(x, setup) for jy, y in ys if kept(y, setup)]


def within(xs, setup):
    """Every pair of two of one kind's votes on one comparison, both kept: [(agree, same judge)]."""
    out = []
    for i in range(len(xs)):
        for j in range(i + 1, len(xs)):
            (ji, wi), (jj, wj) = xs[i], xs[j]
            if kept(wi, setup) and kept(wj, setup):
                out.append((agree(wi, wj), ji == jj))
    return out


PAIRS = {
    "g4_expert": lambda d, s: cross(d.get("gpt4", []), d.get("expert", []), s),
    "expert_expert": lambda d, s: within(d.get("expert", []), s),
    "g4_author": lambda d, s: cross(d.get("gpt4", []), d.get("author", []), s),
    "author_expert": lambda d, s: cross(d.get("author", []), d.get("expert", []), s),
    "author_author": lambda d, s: within(d.get("author", []), s),
}


def measure(comps, pairs_of, setup):
    """Rule 4 over one turn's comparisons: (a) pooled and (b) by comparison, as exact fractions."""
    agreed, total, shares, same = 0, 0, [], 0
    for key in sorted(comps):
        ps = pairs_of(comps[key], setup)
        agreed += sum(a for a, _ in ps)
        total += len(ps)
        same += sum(1 for _, s in ps if s)
        distinct = [a for a, s in ps if not s]
        if distinct:
            shares.append(Fraction(sum(distinct), len(distinct)))
    return {"agreed": agreed, "pairs": total, "pooled": Fraction(agreed, total) if total else None,
            "bycomp": sum(shares, Fraction(0)) / len(shares) if shares else None, "comparisons": len(shares),
            "same_judge_pairs": same}


def majority_share(v, votes):
    """v against the most frequent of votes (ties as one label), shared evenly among equally frequent ones."""
    counts = {}
    for w in votes:
        c = "tie" if is_tie(w) else w
        counts[c] = counts.get(c, 0) + 1
    top = max(counts.values())
    best = [c for c, n in counts.items() if n == top]
    return Fraction(1, len(best)) if ("tie" if is_tie(v) else v) in best else Fraction(0)


def g4_majority(comps, setup):
    """Rule 6: GPT-4 against the experts' majority (Human-M), one value per comparison."""
    vals = []
    for key in sorted(comps):
        d = comps[key]
        g = [w for _, w in d.get("gpt4", []) if kept(w, setup)]
        e = [w for _, w in d.get("expert", []) if kept(w, setup)]
        if g and e:
            vals.append(majority_share(g[0], e))
    return {"value": sum(vals, Fraction(0)) / len(vals) if vals else None, "comparisons": len(vals)}


def expert_majority(comps, setup, own):
    """Rule 6's two readings of Human/Human-M: each kept expert vote on a comparison with at least two, against
    the majority of all of them (own) or of the others."""
    vals = []
    for key in sorted(comps):
        e = [w for _, w in comps[key].get("expert", []) if kept(w, setup)]
        if len(e) >= 2:
            for i, v in enumerate(e):
                vals.append(majority_share(v, e if own else e[:i] + e[i + 1:]))
    return {"value": sum(vals, Fraction(0)) / len(vals) if vals else None, "votes": len(vals)}


def evaluate(data):
    """Every agreement of rules 4 and 6, by turn and setup."""
    res = {}
    for t in TURNS:
        res[t] = {}
        for s in SETUPS:
            r = {name: measure(data[t], f, s) for name, f in PAIRS.items()}
            r["g4_majority"] = g4_majority(data[t], s)
            r["expert_majority_own"] = expert_majority(data[t], s, True)
            r["expert_majority_others"] = expert_majority(data[t], s, False)
            res[t][s] = r
    return res


def conditions(res):
    """Rule 5: eight conditions."""
    cond = {}
    for t in TURNS:
        for comp, name in (("pooled", "pooled"), ("bycomp", "by comparison")):
            g, h = res[t]["S2"]["g4_expert"][comp], res[t]["S2"]["expert_expert"][comp]
            if g is None or h is None:
                raise Refused(f"turn {t}: no pairs to compute the {name} agreement")
            cond[f"turn {t}, {name}: GPT-4's agreement with the experts above 80%"] = g > AGREE_MIN
            cond[f"turn {t}, {name}: GPT-4's agreement not more than 5 points below the experts' with one another"] = (
                g >= h - GAP_MAX)
    return cond


CELL = {("G4-Pair", "Human"): "g4_expert", ("Human", "Human"): "expert_expert", ("G4-P", "Author"): "g4_author",
        ("Author", "Human"): "author_expert", ("Author", "Author"): "author_author", ("G4-P", "Human-M"): "g4_majority"}


def against_printed(res):
    """Rule 6: each computable cell of Tables 5 and 13 against its printed count and percentage."""
    cells = []
    for (row, col, s), turns in PRINTED.items():
        name = CELL[(row, col)]
        for t, (p, n) in turns.items():
            m = res[t][s][name]
            value = m["value"] if name == "g4_majority" else m["pooled"]
            count = m["comparisons"] if name == "g4_majority" else m["pairs"]
            cells.append({"cell": f"{row}/{col} {s} turn {t}", "printed": [p, n], "count": count,
                          "value": None if value is None else float(value),
                          "count_matches": count == n,
                          "percent_matches": value is not None and abs(100 * value - p) <= Fraction(1, 2)})
    return cells


def per_question(comps):
    """S2 pooled tallies by question: {question: [GPT-4 agreed, pairs, experts agreed, pairs]}."""
    out = {}
    for key in sorted(comps):
        g = PAIRS["g4_expert"](comps[key], "S2")
        h = PAIRS["expert_expert"](comps[key], "S2")
        acc = out.setdefault(key[0], [0, 0, 0, 0])
        acc[0] += sum(a for a, _ in g)
        acc[1] += len(g)
        acc[2] += sum(a for a, _ in h)
        acc[3] += len(h)
    return out


def bootstrap(seed, data, n=BOOTSTRAP):
    """Rule 6: 95% intervals from n resamples of the questions, in each turn."""
    rng = random.Random(int.from_bytes(hashlib.sha256(bytes.fromhex(seed) + b"|mtbench/bootstrap").digest(), "big"))
    out = {}
    for t in TURNS:
        pq_ = per_question(data[t])
        qs = sorted(pq_)
        g_, h_, d_, skipped = [], [], [], 0
        for _ in range(n):
            draw = [rng.choice(qs) for _ in qs]
            ga, gn, ha, hn = (sum(pq_[q][k] for q in draw) for k in range(4))
            if gn == 0 or hn == 0:
                skipped += 1
                continue
            g, h = ga / gn, ha / hn
            g_.append(g)
            h_.append(h)
            d_.append(g - h)

        def ci(xs):
            if not xs:
                return None
            xs = sorted(xs)
            return [xs[int(0.025 * len(xs))], xs[int(0.975 * len(xs)) - 1]]
        out[t] = {"g4_expert": ci(g_), "expert_expert": ci(h_), "difference": ci(d_), "questions": len(qs),
                  "resamples": n, "skipped": skipped}
    return out


def pct(x):
    return "n/a" if x is None else f"{100 * float(x):.1f}%"


def votes_parquet(rows):
    """A parquet file's bytes holding rows (for the controls and the tests)."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    cols = {c: [r[c] for r in rows] for c in COLUMNS}
    types = {"question_id": pa.int64(), "turn": pa.int64()}
    table = pa.table({c: pa.array(cols[c], type=types.get(c, pa.string())) for c in COLUMNS})
    buf = pa.BufferOutputStream()
    pq.write_table(table, buf)
    return buf.getvalue().to_pybytes()


def vote(q, a, b, w, judge, turn=1):
    return {"question_id": q, "model_a": a, "model_b": b, "winner": w, "judge": judge, "turn": turn}


def controls_known():
    A, B = "gpt-4", "llama-13b"
    c = {}
    # The paper's worked example: three humans voting A, A and B.
    h3 = [vote(81, A, B, "model_a", "expert_1"), vote(81, A, B, "model_a", "expert_2"),
          vote(81, A, B, "model_b", "expert_3")]
    ok = True
    for gw, want in (("model_a", Fraction(2, 3)), ("model_b", Fraction(1, 3))):
        r = evaluate(comparisons(h3, [vote(81, A, B, gw, "gpt4_pair")]))[1]["S2"]
        ok = ok and r["g4_expert"]["pooled"] == want and r["g4_expert"]["bycomp"] == want
        ok = ok and r["expert_expert"]["pooled"] == Fraction(1, 3) and r["expert_expert"]["bycomp"] == Fraction(1, 3)
        ok = ok and r["g4_majority"]["value"] == (1 if gw == "model_a" else 0)
    c["the paper's example: A, A, B agree 1/3 with one another, GPT-4's A 2/3 and B 1/3"] = ok
    # The paper's even split.
    h2 = [vote(81, A, B, "model_a", "expert_1"), vote(81, A, B, "model_b", "expert_2")]
    r = evaluate(comparisons(h2, [vote(81, A, B, "model_a", "gpt4_pair")]))[1]["S2"]
    c["the paper's even split: GPT-4's A against as many A as B votes agrees 1/2"] = (
        r["g4_majority"]["value"] == Fraction(1, 2) and r["g4_majority"]["comparisons"] == 1)
    # A vote recorded the other way round: both say vicuna-13b-v1.2 won.
    r = evaluate(comparisons([vote(90, "vicuna-13b-v1.2", "alpaca-13b", "model_a", "expert_5")],
                             [vote(90, "alpaca-13b", "vicuna-13b-v1.2", "model_b", "gpt4_pair")]))[1]["S2"]
    c["a vote recorded the other way round is exchanged before it is compared"] = (
        r["g4_expert"]["pooled"] == 1 and r["g4_expert"]["pairs"] == 1)
    # Ties: GPT-4's inconsistent judgement against an expert's tie, and GPT-4's A against an expert's tie.
    r = evaluate(comparisons([vote(81, A, B, "tie", "expert_1"), vote(82, A, B, "tie", "expert_1")],
                             [vote(81, A, B, "tie (inconsistent)", "gpt4_pair"), vote(82, A, B, "model_a", "gpt4_pair")]))
    s1, s2 = r[1]["S1"]["g4_expert"], r[1]["S2"]["g4_expert"]
    c["ties: inconsistent agrees with tie in S1 and both leave S2; A against tie disagrees in S1"] = (
        s1["pairs"] == 2 and s1["agreed"] == 1 and s2["pairs"] == 0 and s2["pooled"] is None)
    # Pooled against by comparison: 3 of 3 on one comparison, 0 of 1 on another.
    hs = [vote(81, A, B, "model_a", f"expert_{i}") for i in (1, 2, 3)] + [vote(82, A, B, "model_b", "expert_4")]
    r = evaluate(comparisons(hs, [vote(81, A, B, "model_a", "gpt4_pair"), vote(82, A, B, "model_a", "gpt4_pair")]))
    m = r[1]["S2"]["g4_expert"]
    c["the two computations differ where comparisons differ in size: 3/4 pooled, 1/2 by comparison"] = (
        m["pooled"] == Fraction(3, 4) and m["bycomp"] == Fraction(1, 2))
    # One expert twice: counted by the pooled computation only.
    hd = [vote(81, A, B, "model_a", "expert_1"), vote(81, A, B, "model_a", "expert_1"),
          vote(81, A, B, "model_b", "expert_2")]
    m = evaluate(comparisons(hd, []))[1]["S2"]["expert_expert"]
    c["a pair of one expert's votes counts in the pooled computation only"] = (
        m["pooled"] == Fraction(1, 3) and m["bycomp"] == 0 and m["same_judge_pairs"] == 1)
    # The two readings of Human/Human-M on A, A, B.
    r = evaluate(comparisons(h3, []))[1]["S2"]
    c["Human/Human-M on A, A, B: 2/3 with its own vote, 1/3 against the others"] = (
        r["expert_majority_own"]["value"] == Fraction(2, 3) and r["expert_majority_others"]["value"] == Fraction(1, 3)
        and r["expert_majority_own"]["votes"] == 3)
    # The reader on small files written here, and its refusals.
    good_h = h3 + [vote(160, "claude-v1", "gpt-3.5-turbo", "tie", "author_0", 2)]
    good_g = [vote(81, A, B, "model_a", "gpt4_pair"), vote(160, "claude-v1", "gpt-3.5-turbo", "tie (inconsistent)",
                                                            "gpt4_pair", 2)]
    try:
        hr, gr = read_rows(votes_parquet(good_h), "human"), read_rows(votes_parquet(good_g), "gpt4")
        d = comparisons(hr, gr)
        reader_ok = (len(hr) == 4 and len(gr) == 2 and d[2][(160, "claude-v1", "gpt-3.5-turbo")]["author"]
                     == [("author_0", "tie")])
    except Refused:
        reader_ok = False
    bad = [("human", vote(81, A, B, "model_c", "expert_1")), ("human", vote(81, A, B, "tie", "crowd_1")),
           ("human", vote(81, A, B, "tie", "expert_1", 3)), ("human", vote(200, A, B, "tie", "expert_1")),
           ("human", vote(81, A, A, "tie", "expert_1")), ("human", vote(81, A, "koala-13b", "tie", "expert_1")),
           ("human", vote(81, A, B, "tie (inconsistent)", "expert_1")), ("gpt4", vote(81, A, B, "tie", "gpt4_single"))]
    refusals = 0
    for kind, row in bad:
        try:
            read_rows(votes_parquet([row]), kind)
        except Refused:
            refusals += 1
    try:
        comparisons([], [vote(81, A, B, "model_a", "gpt4_pair"), vote(81, B, A, "model_b", "gpt4_pair")])
    except Refused:
        refusals += 1
    try:
        read_rows(b"not a parquet file", "human")
    except Refused:
        refusals += 1
    c["the reader reads small files written here and refuses each bad row, a second GPT-4 judgement and a non-file"] = (
        reader_ok and refusals == len(bad) + 2)
    return c


def run(seed, inputs="inputs", results="results", spec=None, rows=None):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    spec, rows = spec or INPUTS, ROWS if rows is None else rows
    split = {}
    for kind, (name, sha) in spec.items():
        split[kind] = read_rows(read_bytes(os.path.join(inputs, name), sha), kind)
        if rows.get(kind) is not None and len(split[kind]) != rows[kind]:
            raise Refused(f"the {kind} split has {len(split[kind])} rows, not {rows[kind]}")
    data = comparisons(split["human"], split["gpt4"])
    res = evaluate(data)
    cond = conditions(res)
    cells = against_printed(res)
    boot = bootstrap(seed, data)
    controls = controls_known()

    hv = split["human"]
    experts = sorted({r["judge"] for r in hv if r["judge"].startswith("expert_")})
    authors = sorted({r["judge"] for r in hv if r["judge"].startswith("author_")})
    n_exp = sum(1 for r in hv if r["judge"].startswith("expert_"))
    s2 = {t: res[t]["S2"] for t in TURNS}
    s1 = {t: res[t]["S1"] for t in TURNS}

    def frac(m):
        return f"{m['agreed']}/{m['pairs']}"

    unmatched = [f"{x['cell']} {pct(x['value'])} ({x['count']}; printed {x['printed'][0]}%, {x['printed'][1]})"
                 for x in cells if not (x["count_matches"] and x["percent_matches"])]
    n_cells = len(cells)
    counts_ok = sum(x["count_matches"] for x in cells)
    pcts_ok = sum(x["percent_matches"] for x in cells)
    printed = f"{counts_ok} of {n_cells} counts and {pcts_ok} of {n_cells} percentages as Tables 5 and 13 print them"
    if unmatched:
        printed += "; not: " + "; ".join(unmatched)
    if len(printed) > LIMIT:
        printed = printed[:LIMIT - 3] + "..."

    def boot_s(t):
        b = boot[t]
        if b["g4_expert"] is None:
            return "n/a"
        return (f"S2 pooled, {b['questions']} questions resampled {b['resamples']} times: GPT-4-expert "
                f"{pct(b['g4_expert'][0])} to {pct(b['g4_expert'][1])}, expert-expert {pct(b['expert_expert'][0])} "
                f"to {pct(b['expert_expert'][1])}, difference {pct(b['difference'][0])} to {pct(b['difference'][1])}")

    values = {
        "votes": (f"human {len(hv)}: {n_exp} by {len(experts)} experts, {len(hv) - n_exp} by {len(authors)} authors; "
                  f"GPT-4 {len(split['gpt4'])}; {sum(len(data[t]) for t in TURNS)} comparisons in all"),
        "s2_pairs": "; ".join(f"turn {t}: GPT-4-expert {frac(s2[t]['g4_expert'])}, expert-expert "
                              f"{frac(s2[t]['expert_expert'])}" for t in TURNS),
        "s1_pooled": "; ".join(f"turn {t}: GPT-4-expert {pct(s1[t]['g4_expert']['pooled'])} "
                               f"({s1[t]['g4_expert']['pairs']}), expert-expert "
                               f"{pct(s1[t]['expert_expert']['pooled'])} ({s1[t]['expert_expert']['pairs']})"
                               for t in TURNS),
        "s1_bycomp": "; ".join(f"turn {t}: GPT-4-expert {pct(s1[t]['g4_expert']['bycomp'])} "
                               f"({s1[t]['g4_expert']['comparisons']} comparisons), expert-expert "
                               f"{pct(s1[t]['expert_expert']['bycomp'])} ({s1[t]['expert_expert']['comparisons']})"
                               for t in TURNS),
        "printed": printed, "printed_counts_matched": counts_ok, "printed_percents_matched": pcts_ok,
        "printed_cells": n_cells,
        "authors": "S2 " + "; ".join(
            f"{lab} turn 1 {pct(s2[1][k]['pooled'])} ({s2[1][k]['pairs']}), turn 2 {pct(s2[2][k]['pooled'])} "
            f"({s2[2][k]['pairs']})" for lab, k in (("G4-P/Author", "g4_author"), ("Author/Human", "author_expert"),
                                                     ("Author/Author", "author_author"))),
        "majority": "S2 " + "; ".join(
            f"{lab} {pct(s2[1][k]['value'])} ({s2[1][k][c]}), {pct(s2[2][k]['value'])} ({s2[2][k][c]})"
            for lab, k, c in (("G4-P/Human-M", "g4_majority", "comparisons"),
                              ("Human/Human-M own vote in", "expert_majority_own", "votes"),
                              ("others only", "expert_majority_others", "votes"))),
        "same_expert_pairs": sum(res[t]["S1"]["expert_expert"]["same_judge_pairs"] for t in TURNS),
        "bootstrap_t1": boot_s(1), "bootstrap_t2": boot_s(2),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(controls.values()), "controls_total": len(controls),
    }
    for t in TURNS:
        for comp, suffix in (("pooled", ""), ("bycomp", "_bycomp")):
            values[f"g4_expert_s2{suffix}_t{t}"] = round(float(s2[t]["g4_expert"][comp]), 6)
            values[f"expert_expert_s2{suffix}_t{t}"] = round(float(s2[t]["expert_expert"][comp]), 6)
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")

    def plain(m):
        return {k: (f"{v.numerator}/{v.denominator}" if isinstance(v, Fraction) else v) for k, v in m.items()}
    detail = {"test": TEST, "inputs": {k: {"name": n, "sha256": s} for k, (n, s) in spec.items()},
              "conditions": cond, "controls": controls, "printed_cells": cells,
              "printed_human_majority": PRINTED_HUMAN_M,
              "agreement": {str(t): {s: {k: plain(m) for k, m in res[t][s].items()} for s in SETUPS} for t in TURNS},
              "bootstrap": {str(t): boot[t] for t in TURNS}, "experts": len(experts), "authors": len(authors),
              "comparisons": {str(t): len(data[t]) for t in TURNS}}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, sort_keys=True, ensure_ascii=False)
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
        sys.exit(f"mtbench: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
