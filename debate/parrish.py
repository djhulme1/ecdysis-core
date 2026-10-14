#!/usr/bin/env python3
"""Single-turn debate on QuALITY: do arguments, or the snippets beside them, raise judges' accuracy? Recounted from
the released judgements.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:f94061b9ebd1b977) is from Parrish, Trivedi,
Perez, Chen, Nangia, Phang and Bowman, "Single-Turn Debate Does Not Help Humans Answer Hard Reading-Comprehension
Questions" (ACL 2022 Workshop on Learning with Natural Language Supervision; arXiv:2204.05212v2): "We do not find that
explanations in our set-up improve human accuracy, but a baseline condition shows that providing human-selected text
snippets does improve accuracy."

Its registered test: refuted if, on the released final judgements (full_final_results.csv; catch trials, question ids
ct_, left out; a judgement correct when choice_number equals corr), accuracy with passage, snippets and arguments (psa)
is higher than with passage and snippets (ps) at two-sided p < 0.05, or accuracy with ps is not higher than with the
passage alone (p) at two-sided p < 0.05; each by a sign-flip permutation test of the mean per-question difference in
accuracy over the questions judged in both conditions.

Standard library only. The inputs are the claim's data of record, the repository's final judgement file and its README
(nyu-mll/single_turn_debate at ba09c9f, CC BY 4.0), checked against their SHA-256s and sizes and read as data (the csv
module); nothing in the repository is run. Every rule below was fixed before any accuracy was computed. The seed draws
the permutations.

1. The file. It is decoded as UTF-8 with any byte that is not valid UTF-8 replaced (U+FFFD; the count is reported),
   since some of its text fields are not UTF-8 and no text field enters the test. Its header must be the twenty
   columns the README documents, in order (passage_id, question_id, mode, ..., round), and the README must document the modes p, ps and psa and the catch trials' ct_ prefix; otherwise the run is
   refused. A row whose question_id starts with ct_ is a catch trial and is left out (counted). Every other row must
   have mode p, ps or psa and corr 1 or 2, or the run is refused. A judgement is correct when choice_number equals
   corr; a choice_number that is not 1 or 2 (no answer recorded) counts as not correct, and such judgements are
   counted.
2. Accuracy per question and condition: the share of that question's judgements in that condition that are correct.
3. The comparisons: for ps against p, and for psa against ps, the questions judged in both conditions, each
   question's difference in accuracy, and their mean. Its two-sided p value is a sign-flip permutation test: under the
   null each difference's sign is equally likely either way, so the mean is re-drawn 20,000 times with independent
   random signs, and p = (1 + the number of re-drawn means at least as far from 0 as the observed one) / 20,001.
   Differences of equal size are exchangeable, so each re-draw takes, for every distinct size, the number of positive
   signs among the differences of that size as the bit count of that many random bits (drawn by SHA-256 of the seed, a
   label and a counter), which is the same distribution as flipping each sign in turn.
4. The conditions: snippets help (ps's mean exceeds p's, p < 0.05); and arguments are not found to help (it is not the
   case that psa's mean exceeds ps's with p < 0.05). test_passed is 1 if both hold.
5. Beside the test: each condition's judgements, questions and pooled accuracy; the share of questions with all three
   and with at least two of three judgements correct, among questions with exactly three judgements in that condition
   (the paper's unanimous and majority agreement), and whether both put ps highest and p lowest, as the paper says,
   and whether pooled accuracy does; psa against p by the same test; the workers (distinct anonid, the paper's 194),
   the share of question-condition cells judged by exactly three distinct workers, and the workers who judged a
   question in more than one condition (the paper: none); and each condition's median time from starting the timer to
   submitting (timer_start_timestamp to hit_end_timestamp), against the paper's 69, 54 and 57 seconds for p, ps and
   psa, where the timestamps read as ISO dates or as epoch seconds or milliseconds.
6. Controls, known answers: the permutation p value for ten equal positive differences is close to the exact 2/1024;
   for zero differences it is 1; and for twelve mixed differences it is within 0.01 of the exact value from all 4,096
   sign patterns.

After the trial (under a seed of Imago's own, before any was issued), one change: the first version decoded the file
as strict UTF-8 and stopped at a byte that is not (0xe6, in a text field); it is now decoded as rule 1 says. The test,
its data and its other rules did not change.

What it cannot check: the experiment itself (who the workers were, what they read in their 90 seconds), and whether
other arguments or another set-up would help; the paper's own conclusion is about this set-up.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 debate/parrish.py
"""

import csv
import datetime
import hashlib
import io
import itertools
import json
import os
import re
import statistics
import sys

INPUTS = {"data": ("full_final_results.csv", "b2dfae48dce1ae81e4d42059657c84b5504888ef8767b1d971b7ae023add19c3",
                   21393626),
          "readme": ("README.md", "2d9e2811d6ef5b784d385f66adead77bf8324a5a101a1d069397da5bf19fbc79", 3889)}
HEADER = ("passage_id", "question_id", "mode", "chosen_answer_text", "choice_number", "ans1_text", "ans2_text",
          "ans1_snippets", "ans2_snippets", "ans1_arg", "ans2_arg", "ans1", "ans2", "corr", "question_text", "anonid",
          "hit_start_timestamp", "timer_start_timestamp", "hit_end_timestamp", "round")
README_STATEMENTS = ("either `p` (passage-only), `ps` (passage+snippet), or `psa` (passage+snippet+argument)",
                     "`question_id` values that start with `ct_` indicate catch trials")
MODES = ("p", "ps", "psa")
PAPER_WORKERS = 194
PAPER_MEDIAN_S = {"p": 69, "ps": 54, "psa": 57}
RESAMPLES = 20000
ALPHA = 0.05
OUTPUTS = ("sample", "acc_p", "acc_ps", "acc_psa", "snippets", "arguments", "snippets_p", "arguments_p", "agreement",
           "design", "times", "printed", "conditions_met", "conditions_total", "test_passed", "controls_passed",
           "controls_total")
LIMIT = 200


class Refused(Exception):
    pass


def read_bytes(inputs, key):
    name, sha, size = INPUTS[key]
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha or len(data) != size:
        raise Refused(f"{name}: sha256 {got} ({len(data)} bytes), not the registered {sha} ({size})")
    return data


def check_readme(text):
    flat = " ".join(text.split())
    missing = [s for s in README_STATEMENTS if s not in flat]
    if missing:
        raise Refused(f"the README does not document {missing[0]!r}")


def parse(text):
    """Rule 1: the judgements, catch trials apart."""
    csv.field_size_limit(10 ** 8)
    rows = csv.reader(io.StringIO(text, newline=""))
    head = next(rows, None)
    if head is None or tuple(head) != HEADER:
        raise Refused(f"the header is not the README's twenty columns: {head}")
    out, catch, unanswered = [], 0, 0
    for i, r in enumerate(rows, 2):
        if r == []:
            continue
        if len(r) != len(HEADER):
            raise Refused(f"line {i}: {len(r)} fields")
        row = dict(zip(HEADER, r))
        if row["question_id"].startswith("ct_"):
            catch += 1
            continue
        if row["mode"] not in MODES:
            raise Refused(f"line {i}: mode {row['mode']!r}")
        if row["corr"] not in ("1", "2"):
            raise Refused(f"line {i}: corr {row['corr']!r}")
        answered = row["choice_number"] in ("1", "2")
        unanswered += not answered
        out.append({"q": row["question_id"], "mode": row["mode"], "worker": row["anonid"],
                    "correct": int(answered and row["choice_number"] == row["corr"]),
                    "start": row["timer_start_timestamp"], "end": row["hit_end_timestamp"]})
    if not out:
        raise Refused("no judgements")
    return out, catch, unanswered


def per_question(rows):
    """Rule 2: {mode: {question: [correct, ...]}}."""
    acc = {m: {} for m in MODES}
    for r in rows:
        acc[r["mode"]].setdefault(r["q"], []).append(r["correct"])
    return acc


class Stream:
    def __init__(self, seed, label):
        self.seed, self.label, self.n = seed, label, 0

    def bits(self, k):
        """k random bits as an integer."""
        out, have = 0, 0
        while have < k:
            self.n += 1
            block = hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
            out = (out << 256) | int.from_bytes(block, "big")
            have += 256
        return out >> (have - k) if k > 0 else 0


def sign_flip_p(diffs, seed, label, resamples=RESAMPLES):
    """Rule 3: the two-sided sign-flip permutation p value of the mean difference."""
    n = len(diffs)
    if n == 0:
        return 1.0
    observed = sum(diffs) / n
    classes = {}
    for d in diffs:
        a = abs(d)
        if a > 0:
            classes[a] = classes.get(a, 0) + 1
    if not classes:
        return 1.0
    st = Stream(seed, label)
    sizes = sorted(classes)
    far = 0
    for _ in range(resamples):
        total = 0.0
        for a in sizes:
            k = classes[a]
            pos = st.bits(k).bit_count()
            total += a * (2 * pos - k)
        if abs(total / n) >= abs(observed) - 1e-12:
            far += 1
    return (1 + far) / (resamples + 1)


def exact_sign_flip_p(diffs):
    n = len(diffs)
    observed = abs(sum(diffs) / n)
    far = sum(1 for signs in itertools.product((1, -1), repeat=n)
              if abs(sum(s * d for s, d in zip(signs, diffs)) / n) >= observed - 1e-12)
    return far / 2 ** n


def compare(acc, a, b, seed):
    """Rule 3 for condition a against condition b."""
    common = sorted(set(acc[a]) & set(acc[b]))
    diffs = [sum(acc[a][q]) / len(acc[a][q]) - sum(acc[b][q]) / len(acc[b][q]) for q in common]
    mean = sum(diffs) / len(diffs) if diffs else 0.0
    return {"questions": len(common), "mean": mean, "p": sign_flip_p(diffs, seed, f"parrish/{a}-{b}")}


def agreement(acc):
    out = {}
    for m in MODES:
        three = [v for v in acc[m].values() if len(v) == 3]
        out[m] = {"questions_with_3": len(three),
                  "unanimous": sum(sum(v) == 3 for v in three) / len(three) if three else float("nan"),
                  "majority": sum(sum(v) >= 2 for v in three) / len(three) if three else float("nan")}
    return out


def when(s):
    s = s.strip()
    if not s:
        return None
    try:
        x = float(s)
        return x / 1000.0 if x > 1e11 else x
    except ValueError:
        pass
    try:
        t = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=datetime.timezone.utc)
    return t.timestamp()


def medians(rows):
    out, unparsed = {}, 0
    for m in MODES:
        spans = []
        for r in rows:
            if r["mode"] != m:
                continue
            a, b = when(r["start"]), when(r["end"])
            if a is None or b is None:
                unparsed += 1
                continue
            spans.append(b - a)
        out[m] = statistics.median(spans) if spans else None
    return out, unparsed


def controls_known(seed):
    ten = sign_flip_p([1.0] * 10, seed, "parrish/control/ten")
    zero = sign_flip_p([0.0] * 7, seed, "parrish/control/zero")
    mixed = [1 / 3, -1 / 3, 2 / 3, 1.0, 1 / 3, 0.0, 2 / 3, -2 / 3, 1 / 3, 1.0, -1 / 3, 1 / 3]
    mc = sign_flip_p(mixed, seed, "parrish/control/mixed")
    return {"ten equal positive differences give about 2/1024": abs(ten - 2 / 1024) < 0.0015,
            "zero differences give 1": zero == 1.0,
            "twelve mixed differences match the exact enumeration within 0.01": abs(mc - exact_sign_flip_p(mixed)) < 0.01}


def ordering(values):
    return " > ".join(sorted(values, key=lambda m: -values[m]))


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    check_readme(read_bytes(inputs, "readme").decode("utf-8"))
    text = read_bytes(inputs, "data").decode("utf-8", errors="replace").lstrip("\ufeff")
    replaced = text.count("\ufffd")
    rows, catch, unanswered = parse(text)
    acc = per_question(rows)

    pooled = {m: (sum(r["correct"] for r in rows if r["mode"] == m) / max(1, sum(r["mode"] == m for r in rows)))
              for m in MODES}
    snip = compare(acc, "ps", "p", seed)
    args = compare(acc, "psa", "ps", seed)
    both = compare(acc, "psa", "p", seed)
    cond = {
        "snippets help: ps above p, p < 0.05": snip["mean"] > 0 and snip["p"] < ALPHA,
        "arguments not found to help: not psa above ps with p < 0.05": not (args["mean"] > 0 and args["p"] < ALPHA),
    }
    agree = agreement(acc)
    workers = {r["worker"] for r in rows}
    cells = {}
    for r in rows:
        cells.setdefault((r["q"], r["mode"]), []).append(r["worker"])
    three_workers = sum(1 for w in cells.values() if len(set(w)) == 3 and len(w) == 3)
    modes_of = {}
    for r in rows:
        modes_of.setdefault((r["worker"], r["q"]), set()).add(r["mode"])
    repeats = sum(1 for v in modes_of.values() if len(v) > 1)
    med, unparsed = medians(rows)
    controls = controls_known(seed)

    def ps_top_p_bottom(vals):
        return max(vals, key=vals.get) == "ps" and min(vals, key=vals.get) == "p"
    printed = {
        "unanimous: ps highest, p lowest": ps_top_p_bottom({m: agree[m]["unanimous"] for m in MODES}),
        "majority: ps highest, p lowest": ps_top_p_bottom({m: agree[m]["majority"] for m in MODES}),
        "pooled accuracy: ps highest, p lowest": ps_top_p_bottom(pooled),
        f"{PAPER_WORKERS} workers": len(workers) == PAPER_WORKERS,
        "no worker judges a question in two conditions": repeats == 0,
        "median times 69, 54, 57 s": all(med[m] is not None and round(med[m]) == PAPER_MEDIAN_S[m] for m in MODES),
    }

    def fmt(c):
        return f"mean difference {c['mean']:+.4f} over {c['questions']} questions, p {c['p']:.4g}"
    per_mode = ", ".join(f"{m} {sum(1 for r in rows if r['mode'] == m)}" for m in MODES)
    values = {
        "sample": (f"{len(rows)} judgements ({per_mode}), {len({r['q'] for r in rows})} questions, {len(workers)} "
                   f"workers; {catch} catch trials left out, {unanswered} without an answer; {replaced} bytes not UTF-8"),
        "acc_p": round(pooled["p"], 6), "acc_ps": round(pooled["ps"], 6), "acc_psa": round(pooled["psa"], 6),
        "snippets": "ps against p: " + fmt(snip),
        "arguments": "psa against ps: " + fmt(args) + "; psa against p: " + fmt(both),
        "snippets_p": float(f"{snip['p']:.4g}"), "arguments_p": float(f"{args['p']:.4g}"),
        "agreement": "; ".join(f"{m}: unanimous {agree[m]['unanimous']:.3f}, majority {agree[m]['majority']:.3f} "
                               f"({agree[m]['questions_with_3']} questions)" for m in MODES),
        "design": (f"{len(workers)} workers (paper {PAPER_WORKERS}); {three_workers} of {len(cells)} question-condition "
                   f"cells judged by exactly three workers; {repeats} worker-question pairs in more than one condition"),
        "times": ("median seconds from timer to submit: " + ", ".join(
            f"{m} {med[m]:.1f}" if med[m] is not None else f"{m} unparsed" for m in MODES)
            + f" (paper 69, 54, 57); {unparsed} unparsed"),
        "printed": f"{sum(printed.values())} of {len(printed)} as the paper says"
                   + ("; not: " + "; ".join(k for k, v in printed.items() if not v) if not all(printed.values()) else ""),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(controls.values()), "controls_total": len(controls),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"inputs": {k: {"name": n, "sha256": s} for k, (n, s, _) in INPUTS.items()}, "conditions": cond,
              "controls": controls, "pooled": pooled, "comparisons": {"ps-p": snip, "psa-ps": args, "psa-p": both},
              "agreement": agree, "printed": printed, "medians": med, "workers": len(workers), "cells": len(cells),
              "three_worker_cells": three_workers, "repeats": repeats, "catch": catch, "unanswered": unanswered,
              "replaced": replaced,
              "orderings": {"pooled": ordering(pooled)}}
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
        sys.exit(f"parrish: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
