#!/usr/bin/env python3
"""Debate and human judges: the accuracy of non-expert humans judging LLM debates, recounted from the released judgements.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:5ae4eb39a07d4cda) is from Khan, Hughes,
Valentine, Ruis, Sachan, Radhakrishnan, Grefenstette, Bowman, Rocktaschel and Perez, "Debating with More Persuasive LLMs
Leads to More Truthful Answers", arXiv:2402.06782 (ICML 2024): "We find that debate consistently helps both non-expert
models and humans answer questions, achieving 76% and 88% accuracy respectively (naive baselines obtain 48% and 60%)."

Its registered test: refuted if, on the released human judgements (ucl-dark/llm_debate at f9c71d1,
llm_debate_dataset.zip): in Experiment 8, the test set (8_v0 left out), human judges' accuracy over static and
interactive debates is below 83%; or the naive baseline's (Experiment 9, judgements up to 24 January 2024, as the
paper's analysis) is above 65%; or debate's accuracy does not exceed the naive baseline's at one-sided Fisher p < 0.05.
The LLM judges' 76% and 48% need the models and are not tested.

The inputs are the repository's own files at commit f9c71d1, each checked against its SHA-256 and read as data (the zip
opened with the standard library and its CSV parsed; the readme read as text; none of the repository's code is run):
data/llm_debate_dataset.zip (a Git LFS object) and data/dataset_readme.md. Every rule below was fixed before any
accuracy was computed. The seed draws only the bootstrap beside the test.

1. The readme. The rules take their experiments from the dataset's own readme, which must say that the paper's primary
   results used Experiment 8, that the naive baseline was Experiment 9, that Experiment 8_v0 is not in any of the
   paper's analysis, and that the analysis used judgements received up to 24 January (READ below, each sentence as it
   is printed); otherwise the run is refused.
2. The rows. The zip must hold llm_debate_dataset/llm_debate_human_judge_dataset.csv with the readme's fields. Every
   row of Experiments 8, 8_v0 and 9 must have a debate_method of debate, consultancy or baseline, a consultant_type of
   correct or incorrect for consultancies and empty otherwise, interactive_judge True or False, correct True or False,
   a whole-number judge_id, a confidence from 5 to 95, and a judgement_time in ISO form; otherwise the run is refused.
3. Judge accuracy, as the paper defines it for humans: the share of judgements that chose the correct answer. Debate is
   Experiment 8's debate rows, static (no interactive judge) and interactive together; the naive baseline is
   Experiment 9's rows judged on or before 24 January 2024 (UTC). Consultancy, beside the test, is the paper's
   alpha = (alpha with correct consultants + alpha with incorrect consultants) / 2.
4. The test's three conditions: debate's accuracy at least 0.83; the naive baseline's at most 0.65; and Fisher's exact
   test, one-sided (debate more often correct than the naive baseline), p below 0.05, computed exactly in integers.
   test_passed is 1 if all three hold.
5. Beside the test: the static and interactive debates separately (the paper: identical); consultancy, static and
   interactive, as rule 3 defines it (the paper: 78% for humans), and debate against consultancy by Fisher's exact
   test, two-sided (the paper prints p 0.001 static and 0.048 interactive without naming its test); the naive baseline
   with all of Experiment 9; static debate with judgements of confidence below 75% rejected (the paper: 65% of
   questions retained at 94% accuracy); the counts against the printed ones (953 test-phase judgements, 6476 in all,
   21 judges); and 95% intervals for debate's and the naive baseline's accuracy and their difference from 2,000
   resamples of each group's judgements drawn from ECDYSIS_SEED.
6. Controls, known answers: Fisher's exact test, one-sided and two-sided, for [[3, 1], [1, 3]] (17/70 and 17/35); and
   the reader on a small zipped table built here, with each refusal of rule 2.

What it cannot check: the debates themselves (the models, the questions and the annotators are as the authors
recorded them), and the LLM judges' accuracies, which need the models.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 debate/khan.py
"""

import csv
import datetime
import hashlib
import io
import json
import math
import os
import random
import re
import sys
import zipfile

INPUTS = {
    "zip": ("llm_debate_dataset.zip", "10758cec77a49e0da398f88eee017010cc61a658c9201beb3f68de6bd2636b80"),
    "readme": ("dataset_readme.md", "d742dfc86c52b3ca241bfebf88fdbe3a20235974a0a3c8434fb08909dce57b63"),
}
MEMBER = "llm_debate_dataset/llm_debate_human_judge_dataset.csv"
READ = (
    "The primary results in the paper used Experiment 8, as this was our test set.",
    "The naive baseline was done in Experiment 9.",
    "Experiment 8_v0 is the portion of Experiment 8 that used GPT-4-Base as a preference model. We do not include this "
    "data in any of our analysis.",
    "Analysis was done on judgements received up to Jan 24th.",
)
FIELDS = ("debate_id", "judge_id", "experiment_name", "debate_method", "consultant_type", "interactive_judge",
          "correct", "confidence", "judgement_time")
TEST, TEST_V0, NAIVE = "Experiment 8", "Experiment 8_v0", "Experiment 9"
CUTOFF = datetime.date(2024, 1, 24)
DEBATE_MIN, NAIVE_MAX, ALPHA = 0.83, 0.65, 0.05
BOOTSTRAP = 2000
OUTPUTS = ("rows", "debate", "debate_accuracy", "naive", "naive_accuracy", "fisher_p", "static_interactive",
           "consultancy", "debate_vs_consultancy", "naive_all", "confident_static", "counts", "bootstrap_95ci",
           "conditions_met", "conditions_total", "test_passed", "controls_passed", "controls_total")
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


def check_readme(text):
    flat = re.sub(r"\s+", " ", text)
    for sentence in READ:
        if sentence not in flat:
            raise Refused(f"the readme does not say: {sentence!r}")


def judged_on(ts):
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})[ T]\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?", ts)
    if not m:
        raise Refused(f"judgement_time {ts!r} is not ISO")
    return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def judgement(row, i):
    """Rule 2 for one row of Experiments 8, 8_v0 or 9."""
    method, ctype = row["debate_method"], row["consultant_type"]
    if method not in ("debate", "consultancy", "baseline"):
        raise Refused(f"row {i}: debate_method {method!r}")
    if (method == "consultancy") != (ctype in ("correct", "incorrect")) or (method != "consultancy" and ctype):
        raise Refused(f"row {i}: consultant_type {ctype!r} with {method}")
    if row["interactive_judge"] not in ("True", "False") or row["correct"] not in ("True", "False"):
        raise Refused(f"row {i}: interactive_judge or correct not True or False")
    if not re.fullmatch(r"[0-9]+", row["judge_id"]):
        raise Refused(f"row {i}: judge_id {row['judge_id']!r}")
    try:
        conf = float(row["confidence"])
    except ValueError:
        raise Refused(f"row {i}: confidence {row['confidence']!r}") from None
    if not 5 <= conf <= 95:
        raise Refused(f"row {i}: confidence {conf} outside 5 to 95")
    return {"method": method, "consultant": ctype, "interactive": row["interactive_judge"] == "True",
            "correct": row["correct"] == "True", "judge": int(row["judge_id"]), "confidence": conf,
            "date": judged_on(row["judgement_time"])}


def read_table(zip_bytes):
    """{experiment: [judgement]} for Experiments 8, 8_v0 and 9, and the count of every row in the table."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        if MEMBER not in z.namelist():
            raise Refused(f"the zip holds no {MEMBER}")
        csv.field_size_limit(2 ** 30)
        with z.open(MEMBER) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
            missing = [f for f in FIELDS if f not in (reader.fieldnames or [])]
            if missing:
                raise Refused(f"the table lacks fields {missing}")
            out, total, experiments = {TEST: [], TEST_V0: [], NAIVE: []}, 0, {}
            for i, row in enumerate(reader, start=2):
                total += 1
                e = row["experiment_name"]
                experiments[e] = experiments.get(e, 0) + 1
                if e in out:
                    out[e].append(judgement(row, i))
    return out, total, experiments


def share(js):
    return sum(j["correct"] for j in js) / len(js)


def fisher_one_sided(a, n1, c, n2):
    """P(X >= a) for X ~ Hypergeometric: a correct of n1 in group 1, c of n2 in group 2; exact in integers."""
    k = a + c
    num = sum(math.comb(n1, x) * math.comb(n2, k - x) for x in range(a, min(n1, k) + 1))
    return num / math.comb(n1 + n2, k)


def fisher_two_sided(a, n1, c, n2):
    """R's fisher.test two-sided p, exact in integers."""
    k = a + c
    lo, hi = max(0, k - n2), min(n1, k)
    w = {x: math.comb(n1, x) * math.comb(n2, k - x) for x in range(lo, hi + 1)}
    obs = w[a]
    return sum(v for v in w.values() if v * 10 ** 7 <= obs * (10 ** 7 + 1)) / math.comb(n1 + n2, k)


def balanced(js):
    """The paper's consultancy accuracy: the mean of the accuracies with correct and with incorrect consultants."""
    cor = [j for j in js if j["consultant"] == "correct"]
    inc = [j for j in js if j["consultant"] == "incorrect"]
    return (share(cor) + share(inc)) / 2, share(cor), share(inc), len(cor), len(inc)


def bootstrap(seed, debate, naive, n=BOOTSTRAP):
    rng = random.Random(int.from_bytes(hashlib.sha256(bytes.fromhex(seed) + b"|khan/bootstrap").digest(), "big"))
    d = [j["correct"] for j in debate]
    v = [j["correct"] for j in naive]
    a, b, diff = [], [], []
    for _ in range(n):
        x = sum(rng.choice(d) for _ in d) / len(d)
        y = sum(rng.choice(v) for _ in v) / len(v)
        a.append(x)
        b.append(y)
        diff.append(x - y)

    def ci(s):
        s = sorted(s)
        return s[int(0.025 * n)], s[int(0.975 * n) - 1]
    return {"debate": ci(a), "naive": ci(b), "difference": ci(diff), "n": n}


def zipped(rows, header=None):
    header = header or ["", "debate_id", "judge_id", "experiment_name", "debate_method", "consultant_type",
                        "interactive_judge", "correct", "confidence", "judgement_time"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    for r in rows:
        w.writerow(r)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr(MEMBER, buf.getvalue())
    return out.getvalue()


def controls_known():
    fisher = (abs(fisher_one_sided(3, 4, 1, 4) - 17 / 70) < 1e-15 and abs(fisher_two_sided(3, 4, 1, 4) - 17 / 35) < 1e-15)
    good = [["0", "a", "1", TEST, "debate", "", "False", "True", "80", "2023-12-20 17:22:13.779827+00:00"],
            ["1", "b", "2", NAIVE, "baseline", "", "False", "False", "55", "2024-01-25 06:03:35+00:00"],
            ["2", "c", "2", "Experiment 1", "weird", "", "x", "y", "z", "never"]]
    try:
        out, total, _ = read_table(zipped(good))
        reader_ok = (total == 3 and len(out[TEST]) == 1 and out[TEST][0]["correct"]
                     and out[NAIVE][0]["date"] == datetime.date(2024, 1, 25))
    except Refused:
        reader_ok = False
    refusals = 0
    bad_rows = [["0", "a", "1", TEST, "debates", "", "False", "True", "80", "2023-12-20 17:22:13"],
                ["0", "a", "1", TEST, "consultancy", "", "False", "True", "80", "2023-12-20 17:22:13"],
                ["0", "a", "1", TEST, "debate", "correct", "False", "True", "80", "2023-12-20 17:22:13"],
                ["0", "a", "1", TEST, "debate", "", "yes", "True", "80", "2023-12-20 17:22:13"],
                ["0", "a", "x", TEST, "debate", "", "False", "True", "80", "2023-12-20 17:22:13"],
                ["0", "a", "1", TEST, "debate", "", "False", "True", "99", "2023-12-20 17:22:13"],
                ["0", "a", "1", NAIVE, "baseline", "", "False", "True", "80", "20 Dec 2023"]]
    for r in bad_rows:
        try:
            read_table(zipped([r]))
        except Refused:
            refusals += 1
    try:
        read_table(zipped([], header=["debate_id", "judge_id"]))
    except Refused:
        refusals += 1
    return {"Fisher's exact test gives 17/70 and 17/35 for [[3, 1], [1, 3]]": fisher,
            "the reader reads a small table and refuses each bad row": reader_ok and refusals == len(bad_rows) + 1}


def pct(x):
    return f"{100 * x:.1f}%"


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    raw = {k: read_bytes(os.path.join(inputs, name), sha) for k, (name, sha) in INPUTS.items()}
    check_readme(raw["readme"].decode("utf-8"))
    table, total, experiments = read_table(raw["zip"])

    test = table[TEST]
    debate = [j for j in test if j["method"] == "debate"]
    static = [j for j in debate if not j["interactive"]]
    inter = [j for j in debate if j["interactive"]]
    naive_all = [j for j in table[NAIVE] if j["method"] == "baseline"]
    naive = [j for j in naive_all if j["date"] <= CUTOFF]
    if len(naive_all) != len(table[NAIVE]):
        raise Refused("Experiment 9 holds rows that are not the naive baseline")
    dc, nc = sum(j["correct"] for j in debate), sum(j["correct"] for j in naive)
    acc_d, acc_n = dc / len(debate), nc / len(naive)
    p1 = fisher_one_sided(dc, len(debate), nc, len(naive))
    cond = {
        f"debate's accuracy at least {DEBATE_MIN:g}": acc_d >= DEBATE_MIN,
        f"the naive baseline's accuracy at most {NAIVE_MAX:g}": acc_n <= NAIVE_MAX,
        "debate more often correct than the naive baseline (one-sided Fisher p < 0.05)": p1 < ALPHA,
    }

    cons = [j for j in test if j["method"] == "consultancy"]
    cs = [j for j in cons if not j["interactive"]]
    ci_ = [j for j in cons if j["interactive"]]
    bal_s, bal_i, bal_all = balanced(cs), balanced(ci_), balanced(cons)

    def vs(d, c):
        a, n1 = sum(j["correct"] for j in d), len(d)
        b, n2 = sum(j["correct"] for j in c), len(c)
        return fisher_two_sided(a, n1, b, n2)
    p_static, p_inter = vs(static, cs), vs(inter, ci_)
    conf = [j for j in static if j["confidence"] >= 75]
    boot = bootstrap(seed, debate, naive)
    controls = controls_known()
    judges = sorted({j["judge"] for j in test})

    values = {
        "rows": f"{total} judgements in the table; Experiment 8 {len(test)}, 8_v0 {len(table[TEST_V0])}, 9 {len(naive_all)}",
        "debate": f"{dc} of {len(debate)} debate judgements correct ({pct(acc_d)})",
        "debate_accuracy": round(acc_d, 4),
        "naive": f"{nc} of {len(naive)} naive judgements to 24 January correct ({pct(acc_n)})",
        "naive_accuracy": round(acc_n, 4),
        "fisher_p": float(f"{p1:.3g}"),
        "static_interactive": (f"static {sum(j['correct'] for j in static)}/{len(static)} ({pct(share(static))}), "
                               f"interactive {sum(j['correct'] for j in inter)}/{len(inter)} ({pct(share(inter))})"),
        "consultancy": (f"static {pct(bal_s[0])} (correct consultant {pct(bal_s[1])}, incorrect {pct(bal_s[2])}); "
                        f"interactive {pct(bal_i[0])}; both {pct(bal_all[0])}"),
        "debate_vs_consultancy": f"two-sided Fisher p static {p_static:.3g}, interactive {p_inter:.3g}",
        "naive_all": f"all of Experiment 9: {sum(j['correct'] for j in naive_all)} of {len(naive_all)} ({pct(share(naive_all))})",
        "confident_static": (f"static debate at confidence 75 or more: {len(conf)} of {len(static)} retained "
                             f"({pct(len(conf) / len(static))}), {pct(share(conf))} correct"),
        "counts": (f"{len(test)} test-phase judgements (printed 953); {total} in all (printed 6476); {len(judges)} judges "
                   f"in Experiment 8 (printed 21)"),
        "bootstrap_95ci": (f"debate {pct(boot['debate'][0])} to {pct(boot['debate'][1])}; naive {pct(boot['naive'][0])} "
                           f"to {pct(boot['naive'][1])}; difference {pct(boot['difference'][0])} to "
                           f"{pct(boot['difference'][1])} ({boot['n']} resamples)"),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(controls.values()), "controls_total": len(controls),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"inputs": {k: {"name": n, "sha256": s} for k, (n, s) in INPUTS.items()}, "conditions": cond,
              "controls": controls, "experiments": experiments, "judges": judges, "bootstrap": boot,
              "consultancy": {"static": bal_s, "interactive": bal_i, "both": bal_all},
              "naive_after_cutoff": len(naive_all) - len(naive)}
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
        sys.exit(f"khan: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
