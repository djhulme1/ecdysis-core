#!/usr/bin/env python3
"""Berglund et al. (2023), the Reversal Curse in the wild: GPT-4 names a celebrity's parent far more often than the
celebrity as the parent's child, recounted from the authors' released file.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from L. Berglund, M. Tong, M. Kaufmann,
M. Balesni, A. C. Stickland, T. Korbak and O. Evans, "The Reversal Curse: LLMs trained on "A is B" fail to learn "B is
A"" (arXiv:2309.12288, v4, May 2024; ICLR 2024), its abstract: "GPT-4 correctly answers questions like the former 79%
of the time, compared to 33% for the latter." The former are questions like "Who is Tom Cruise's mother?", the latter
their reverse, "Who is Mary Lee Pfeiffer's son?". Its Experiment 2 (Section 2.2 and Appendix C) took the top 1,000
celebrities of an IMDb list, asked GPT-4 once for each one's mother and once for the father ("Who is [name]'s
[mother/father]?", a system message and three few-shot turns, an answer of "I don't know." or not two to five
capitalised words counting as none): "GPT-4 is able to identify the celebrity's parent 79% of the time, giving us 1573
child-parent pairs." It then asked ten times, at temperature 1, "Name a child of [parent].", a success when one of the
answers begins with the celebrity's name: "Here, GPT-4 is successful only 33% of the time". Its Figure 4's note gives
another number for the same quantity: "GPT-4 scores 28% on "Child"".

The data of record are the files the authors released with the paper (github.com/lukasberglund/reversal_curse at
commit 6af5f41, the repository the abstract names; it carries no licence file), read by hash (INPUTS):
data/celebrity_relations/parent_child_pairs.csv, which scripts/celebrity_relations/find_non_reversals_parents.py writes
(one row per pair, the columns child, parent, parent_type, child_prediction and can_reverse, which is True where
get_child returned a name, that is where one of the ten answers began with the child's name, and child_prediction that
answer), the list top_celebrities.txt whose first 1,000 names the script queried (its --num_celebrities default), and the
five files of the other models' results in the same folder (gpt-3.5-turbo's mean success over ten samples, and the
log-probabilities davinci and the three Llama-1 models give the parent and the child). The code was read as text; nothing
of it runs here. No name from the files is written out: the outputs and detail.json hold counts only.

The rules, fixed before any count of the files was taken (a syntax-only pass read the pairs file's header, its field
counts and the values its parent_type and can_reverse columns take):
1. The reader: the pairs file must have exactly the header above, five fields a row, parent_type mother or father and
   can_reverse True or False; anything else is refused. The questions are 2,000, a mother and a father question for
   each of the first 1,000 names of the list, as the script asks them.
2. The test (TEST), two conditions, both needed: the pairs, as a share of the 2,000 questions, round to 79% (78.5% or
   more and under 79.5%); and the pairs with can_reverse True, as a share of the pairs, round to 33% (32.5% or more and
   under 33.5%).

Beside the test, none of it counted: the pairs against the printed 1,573; the share against the figure note's 28%; the
other reading of the 79%, the share of the first 1,000 names (distinct names) with at least one parent named; the shares
for mothers and for fathers; the celebrities with both parents; and the other models of Figure 4 on the same pairs:
gpt-3.5-turbo's mean success at naming the parent and the child, and for davinci and Llama-1 7B, 30B and 65B the mean
probability (exp of the log-probability) of the correct parent and of the correct child, and the share of pairs whose
parent is the likelier (the paper: "all models are much better at identifying the parent than the child").

Controls (controls_passed counts those that behave as stated), all but the last on the claim's own files: the csv
module and a second, hand-written reader read every row of the six CSV files alike; can_reverse is True exactly where
child_prediction is filled; every child_prediction begins with its row's child, as get_child keeps only such answers;
every child is among the first 1,000 names of the list, the rows in the list's order and no (child, parent type) twice;
the five other models' files list the same pairs, parent types and child predictions, row by row; and the count, run
again on the pairs with ten can_reverse values turned from True to False, finds exactly ten fewer.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 reversal/berglund2023.py
"""

import csv
import hashlib
import io
import json
import math
import os
import re
import sys

COMMIT = "6af5f418755d528304e406361e86477637d21c84"
INPUTS = {
    "parent_child_pairs.csv": ("59d181610f1477a3cfb8a63428bb8cc037b7d73c9cdf5616fdd8d8ba90debb5d", 73136),
    "top_celebrities.txt": ("f3bbb5b13b0ae159c82c5a707b61ccfa8be0b69acf380874d2c9c9efd49683e1", 142431),
    "gpt-3.5-turbo_reversal_test_results.csv": ("e502567af4cfb42fb927a8eed1c4bc5cf6b4c36ecef372340c197e63a60099e9",
                                                76704),
    "davinci_reversal_test_results.csv": ("cb4e7ed8e342c4510263fb2906d13c1e5e117dd1eaf745883ddbb4371b94f638", 112152),
    "llama-7b_reversal_test_results.csv": ("372a95aaa5a39a54a5ba5a2c9df80fd191bbb9dac1a7356f980666894f2ff8a4", 89084),
    "llama-30b_reversal_test_results.csv": ("4307386e2322648441bdc6da6051aa19cff3df31bcc58a7899f6da595a8a98cc", 123539),
    "llama-65b_reversal_test_results.csv": ("58610356fcc9b167a70bd96396ea0bf1f699d2a397176c422430008be33cb62e", 123614),
}
PAIRS = "parent_child_pairs.csv"
LIST = "top_celebrities.txt"
GPT35 = "gpt-3.5-turbo_reversal_test_results.csv"
LOGPROB_MODELS = ("davinci", "llama-7b", "llama-30b", "llama-65b")
N_CELEBRITIES = 1000
QUESTIONS = 2 * N_CELEBRITIES
HEADER = ["child", "parent", "parent_type", "child_prediction", "can_reverse"]
PRINTED = {"pairs": 1573, "parent_pct": 79, "child_pct": 33, "figure_child_pct": 28}
PLANTED = 10
TEST = ("Refuted if, in the authors' released Experiment 2 file (data/celebrity_relations/parent_child_pairs.csv at "
        "commit 6af5f41 of github.com/lukasberglund/reversal_curse: GPT-4's child-parent pairs for the first 1,000 names "
        "of its top_celebrities.txt, each asked once for a mother and once for a father, and can_reverse, true where one "
        "of ten answers to 'Name a child of [parent].' began with the child's name), the pairs are not 79% of the 2,000 "
        "parent questions, rounded to a whole percent, or the pairs with can_reverse true are not 33% of the pairs, "
        "rounded.")
OUTPUTS = ("pairs", "questions", "parent_pct", "reversed", "child_pct", "printed", "reading_b", "by_type",
           "both_parents", "gpt35", "davinci", "llama7b", "llama30b", "llama65b", "conditions_met", "conditions_total",
           "test_passed", "controls_passed", "controls_total")


class Refused(Exception):
    pass


def read_bytes(path, sha256, size):
    with open(path, "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha256 or len(data) != size:
        raise Refused(f"{os.path.basename(path)}: sha256 {got} and {len(data)} bytes, not the registered file")
    return data


# ----------------------------------------------------------------------------------------------- readers

def rows_csv(text):
    """The csv module's reading: a list of rows, each a list of fields."""
    return [r for r in csv.reader(io.StringIO(text, newline=""))]


def rows_hand(text):
    """A second reader, written here for the control: fields split at commas outside double quotes, a quote opening a
    quoted field only at the field's start (elsewhere it is a character, as the csv module reads it), a doubled quote
    inside quotes standing for one, rows ended by a newline (or CR LF) outside quotes, and a blank line read as an
    empty row."""
    rows, row, field = [], [], []
    quoted = in_field = in_row = False
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if quoted:
            if ch == '"':
                if i + 1 < n and text[i + 1] == '"':
                    field.append('"')
                    i += 2
                    continue
                quoted = False
            else:
                field.append(ch)
        elif ch == '"' and not in_field:
            quoted = in_field = in_row = True
        elif ch == ",":
            row.append("".join(field))
            field, in_field, in_row = [], False, True
        elif ch == "\n" or (ch == "\r" and i + 1 < n and text[i + 1] == "\n"):
            if ch == "\r":
                i += 1
            if in_row:
                row.append("".join(field))
                rows.append(row)
            else:
                rows.append([])
            row, field, in_field, in_row = [], [], False, False
        else:
            field.append(ch)
            in_field = in_row = True
        i += 1
    if quoted:
        raise Refused("an unterminated quoted field")
    if in_row:
        row.append("".join(field))
        rows.append(row)
    return rows


def read_pairs(text):
    """The pairs file as the script writes it: [(child, parent, parent_type, child_prediction, can_reverse)]."""
    rows = rows_csv(text)
    if not rows or rows[0] != HEADER:
        raise Refused(f"the pairs file's header is {rows[0] if rows else None}, not {HEADER}")
    out = []
    for k, r in enumerate(rows[1:], start=2):
        if len(r) != 5:
            raise Refused(f"row {k} has {len(r)} fields")
        child, parent, ptype, pred, rev = r
        if ptype not in ("mother", "father"):
            raise Refused(f"row {k}: parent_type {ptype!r}")
        if rev not in ("True", "False"):
            raise Refused(f"row {k}: can_reverse {rev!r}")
        if not child or not parent:
            raise Refused(f"row {k}: an empty child or parent")
        out.append((child, parent, ptype, pred, rev == "True"))
    return out


def read_list(text):
    """The celebrity list as src/common.py's load_from_txt reads it: every line, stripped (a final newline adds no
    line)."""
    lines = text.split("\n")
    if text.endswith("\n"):
        lines = lines[:-1]
    return [ln.strip() for ln in lines]


def read_model(text, model):
    """Another model's results: the four pair columns and that model's two columns, as floats."""
    rows = rows_csv(text)
    if model == "gpt-3.5-turbo":
        cols = [f"{model}_can_find_parent", f"{model}_can_find_child"]
    else:
        cols = [f"{model}_parent_logprob", f"{model}_child_logprob"]
    want = ["child", "parent", "parent_type", "child_prediction"] + cols
    if not rows or rows[0] != want:
        raise Refused(f"{model}'s header is {rows[0] if rows else None}, not {want}")
    out = []
    for k, r in enumerate(rows[1:], start=2):
        if len(r) != 6:
            raise Refused(f"{model} row {k} has {len(r)} fields")
        a, b = float(r[4]), float(r[5])
        if not (math.isfinite(a) and math.isfinite(b)):
            raise Refused(f"{model} row {k}: a value that is not finite")
        out.append((r[0], r[1], r[2], r[3], a, b))
    return out


# ----------------------------------------------------------------------------------------------- counts

def rounds_to(num, den, pct):
    """Whether 100 num / den, rounded half up to a whole percent, is pct (exact integer arithmetic)."""
    return (2 * pct - 1) * den <= 200 * num < (2 * pct + 1) * den


def count(pairs):
    n = len(pairs)
    r = sum(1 for p in pairs if p[4])
    by = {}
    for t in ("mother", "father"):
        sub = [p for p in pairs if p[2] == t]
        by[t] = (len(sub), sum(1 for p in sub if p[4]))
    children = {}
    for p in pairs:
        children.setdefault(p[0], set()).add(p[2])
    both = sum(1 for v in children.values() if len(v) == 2)
    return {"pairs": n, "reversed": r, "by_type": by, "children": len(children), "both_parents": both}


def consistency(pairs, names):
    """The pairs file against the script that wrote it and the list it read."""
    first = names[:N_CELEBRITIES]
    pos = {}
    for k, name in enumerate(first):
        pos.setdefault(name, k)
    filled = all((p[3] != "") == p[4] for p in pairs)
    begins = all(p[3].startswith(p[0]) for p in pairs if p[3] != "")
    in_list = all(p[0] in pos for p in pairs)
    order = in_list and all(pos[a[0]] <= pos[b[0]] for a, b in zip(pairs, pairs[1:]))
    keys = [(p[0], p[2]) for p in pairs]
    once = len(keys) == len(set(keys))
    return {"can_reverse_where_filled": filled, "predictions_begin_with_child": begins, "children_in_first_1000": in_list,
            "rows_in_list_order": order, "each_child_and_type_once": once,
            "distinct_names_in_first_1000": len(pos), "names_in_list": len(names)}


def summarise_model(rows, model):
    n = len(rows)
    if model == "gpt-3.5-turbo":
        parent = sum(r[4] for r in rows) / n
        child = sum(r[5] for r in rows) / n
        likelier = sum(1 for r in rows if r[4] > r[5]) / n
    else:
        parent = sum(math.exp(r[4]) for r in rows) / n
        child = sum(math.exp(r[5]) for r in rows) / n
        likelier = sum(1 for r in rows if r[4] > r[5]) / n
    return {"rows": n, "parent": parent, "child": child, "parent_better_share": likelier}


def pct(num, den):
    return 100.0 * num / den if den else float("nan")


def yes(b):
    return "yes" if b else "no"


# ----------------------------------------------------------------------------------------------- the run

def assess(raw):
    text = {k: v.decode("utf-8") for k, v in raw.items() if k != LIST}
    names = read_list(raw[LIST].decode("utf-8"))
    pairs = read_pairs(text[PAIRS])
    c = count(pairs)
    cons = consistency(pairs, names)
    n, r = c["pairs"], c["reversed"]
    cond = {
        "the pairs are 79% of the 2,000 parent questions, rounded": rounds_to(n, QUESTIONS, PRINTED["parent_pct"]),
        "the pairs GPT-4 reversed are 33% of the pairs, rounded": rounds_to(r, n, PRINTED["child_pct"]) if n else False,
    }
    # beside
    named = len({p[0] for p in pairs})
    models = {}
    same_rows = True
    model_files = {"gpt-3.5-turbo": GPT35}
    model_files.update({m: f"{m}_reversal_test_results.csv" for m in LOGPROB_MODELS})
    for m, f in model_files.items():
        rows = read_model(text[f], m)
        same_rows = same_rows and len(rows) == n and all(tuple(x[:4]) == (p[0], p[1], p[2], p[3])
                                                         for x, p in zip(rows, pairs))
        models[m] = summarise_model(rows, m)
    # controls
    controls = {}
    agree = True
    for k, v in text.items():
        if k.endswith(".csv"):
            agree = agree and rows_csv(v) == rows_hand(v)
    controls["the csv module and the hand-written reader read all six CSV files alike"] = agree
    controls["can_reverse is True exactly where child_prediction is filled"] = cons["can_reverse_where_filled"]
    controls["every child_prediction begins with its row's child (get_child's rule)"] = cons[
        "predictions_begin_with_child"]
    controls["every child among the first 1,000 names, in the list's order, each (child, parent type) once"] = (
        cons["children_in_first_1000"] and cons["rows_in_list_order"] and cons["each_child_and_type_once"])
    controls["the five other models' files list the same pairs and predictions, row by row"] = same_rows
    flipped = 0
    planted = []
    for p in pairs:
        if p[4] and flipped < PLANTED:
            planted.append((p[0], p[1], p[2], p[3], False))
            flipped += 1
        else:
            planted.append(p)
    controls[f"turning {PLANTED} can_reverse values to False lowers the count by exactly {PLANTED}"] = (
        flipped == PLANTED and count(planted)["reversed"] == r - PLANTED)
    detail = {"commit": COMMIT, "inputs": {k: {"sha256": v[0], "bytes": v[1]} for k, v in INPUTS.items()},
              "counts": c, "consistency": cons, "celebrities_with_a_parent_named": named, "models": models,
              "conditions": cond, "controls": controls, "test": TEST, "printed": PRINTED}
    bt = c["by_type"]
    fmt = {m: (f"{m}: mean P(parent) {models[m]['parent']:.4f}, mean P(child) {models[m]['child']:.4f}, parent likelier "
               f"in {100 * models[m]['parent_better_share']:.1f}% of {models[m]['rows']} pairs") for m in LOGPROB_MODELS}
    out = {
        "pairs": n, "questions": QUESTIONS, "parent_pct": pct(n, QUESTIONS), "reversed": r, "child_pct": pct(r, n),
        "printed": (f"1,573 pairs as printed: {yes(n == PRINTED['pairs'])}; 33% as the text says: "
                    f"{yes(rounds_to(r, n, 33))}; 28% as Figure 4's note says: {yes(rounds_to(r, n, 28))}"),
        "reading_b": (f"{named} of the first {N_CELEBRITIES} names ({cons['distinct_names_in_first_1000']} distinct) "
                      f"have a parent named: {pct(named, N_CELEBRITIES):.1f}% of 1,000"),
        "by_type": (f"mothers {bt['mother'][0]} pairs, {bt['mother'][1]} reversed ({pct(bt['mother'][1], bt['mother'][0]):.1f}%); "
                    f"fathers {bt['father'][0]} pairs, {bt['father'][1]} reversed ({pct(bt['father'][1], bt['father'][0]):.1f}%)"),
        "both_parents": c["both_parents"],
        "gpt35": (f"gpt-3.5-turbo: mean success naming the parent {100 * models['gpt-3.5-turbo']['parent']:.1f}%, the child "
                  f"{100 * models['gpt-3.5-turbo']['child']:.1f}%, parent better in "
                  f"{100 * models['gpt-3.5-turbo']['parent_better_share']:.1f}% of pairs"),
        "davinci": fmt["davinci"], "llama7b": fmt["llama-7b"], "llama30b": fmt["llama-30b"], "llama65b": fmt["llama-65b"],
    }
    out["conditions_met"] = sum(1 for v in cond.values() if v)
    out["conditions_total"] = len(cond)
    out["test_passed"] = int(all(cond.values()))
    out["controls_passed"] = sum(1 for v in controls.values() if v)
    out["controls_total"] = len(controls)
    assert set(out) == set(OUTPUTS), sorted(set(out) ^ set(OUTPUTS))
    for k, v in out.items():
        if isinstance(v, str):
            assert len(v) <= 200, (k, len(v))
        else:
            assert math.isfinite(v), k
    return out, detail


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    raw = {name: read_bytes(os.path.join(inputs, name), sha, size) for name, (sha, size) in INPUTS.items()}
    out, detail = assess(raw)
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
        out, _ = run(seed)      # nothing here depends on the seed: every count is exhaustive
    except Refused as e:
        sys.exit(f"berglund2023: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
