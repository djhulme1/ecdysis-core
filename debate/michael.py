#!/usr/bin/env python3
"""Debate helps supervise unreliable experts: judge accuracy in human debate against consultancy, recounted from the
released debates.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:ca4985f26b8108ae) is from Michael, Mahdi,
Rein, Petty, Dirani, Padmakumar and Bowman, "Debate Helps Supervise Unreliable Experts", arXiv:2311.08702 (November
2023): "Comparing debate to a baseline we call consultancy, where a single expert argues for only one answer which is
correct half of the time, we find that debate performs significantly better, with 84% judge accuracy compared to
consultancy's 74%."

Its registered test: refuted if, among the debates and consultancies the released dataset marks as included in the
paper (julianmichael/debate at 0fdcb4d, pub/debates-metadata.jsonl), human debates and human consultancies do not
number 154 and 96, as its Table 1 has them; or the share whose judge's final judgement puts more than one half on the
correct answer does not round to 84% for human debate and 74% for human consultancy; or a two-sided two-proportion
z-test of the two shares (pooled) gives p of 0.05 or more, against the paper's p = 0.04.

Standard library only. The input is the claim's data of record, the dataset's metadata file at commit 0fdcb4d (CC BY
4.0), checked against its SHA-256 and size and read as JSON lines; none of the repository's code is run. Every rule
below was fixed before any accuracy was computed. The seed draws only the bootstrap beside the test.

1. The rows. One JSON object per debate room. A room is in the paper's analysis when its includedInPaper is true; its
   setting is human or AI (setting.isHuman) and debate or consultancy (setting.isDebate). Every included room must be
   complete (status.Complete.result) with a judgingInfo whose finalJudgement is two probabilities summing to 1 (within
   1e-9) and whose correctAnswerIndex, 0 or 1, agrees with the result's; otherwise the run is refused.
2. Judge accuracy (the paper's measure): a room's judge is right when the final judgement puts more than one half on
   the correct answer; exactly one half counts as wrong (the paper does not say, and the count of such ties is
   reported). Accuracy is the share of rooms judged right.
3. The test's four conditions: 154 included human debates and 96 human consultancies; human debate's accuracy rounds
   to 84% and human consultancy's to 74% (to the nearest percent, halves up); and the two-sided two-proportion z-test
   of the two accuracies, with the pooled proportion in the standard error, gives p < 0.05 (the paper's "significantly
   better", p = 0.04 "by proportion test"). test_passed is 1 if all four hold.
4. Beside the test, none of it counted: Fisher's exact test of the same two-by-two table; the AI settings' accuracies
   (the paper's 78% for AI debate and 80% for AI consultancy, with 87 and 76 rooms); each setting against chance, by
   the exact one-sided binomial test (the paper: all significantly better than 50%); human debate restricted to final
   judgements of 95% confidence or more (the paper's 88%); the judges who got every human debate they judged right
   (the paper: "the top two judges achieve 100% accuracy on the 36 human debates they collectively judge"); the share
   of judges with at least 90% on human debate; consultancies split by whether the consultant argued for the correct
   answer, the consultant's answer being 0 when the room assigns "Debater A" and 1 for "Debater B" (the paper's AI
   consultancy: 74% honest, 87% dishonest); the mean judgeReward against Table 1's average judge score S_j (-1.16,
   -1.20, -1.24 and -0.89 for AI consultancy, AI debate, human consultancy and human debate); the expected calibration
   error of the final judgements, the confidence in the chosen answer in bins of 0.1 (Table 1: .17, .16, .17, .11);
   the mean number of continues (numContinues) and its ratio between human debate and human consultancy, beside the
   paper's "68% of the length"; and a 95% bootstrap interval for the difference of the two accuracies, 10,000
   resamples within each setting drawn from the seed.

Controls (controls_passed counts those that behave as stated): the z-test's tail agrees with a numerical integral of
the normal density to 1e-9 at five values of z; the exact binomial and Fisher tests give their textbook values
(P(X >= 9 | 10, 1/2) = 11/1024, and the one-sided Fisher p of the tea-tasting table [[3, 1], [1, 3]] = 17/70); every
included room's two correctAnswerIndex fields agree and its judgement sums to 1; and the four settings' included rooms
number 76, 87, 96 and 154, Table 1's n.

What it cannot check: whether the rooms excluded from the paper (incomplete or otherwise left out) were excluded as
its protocol says; the transcripts' content (quotes, rounds and characters per round), which are not in the metadata;
and the mixed-effects robustness check of its appendix (p = 0.0487).

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 debate/michael.py
"""

import hashlib
import json
import math
import os
import re
import sys

INPUT = ("debates-metadata.jsonl", "29c96624ad698ee4b6bbcbe8ac305becf7f714aa6f3fc1039e9c04198a6d7571", 716165)
SETTINGS = ("AI Consultancy", "AI Debate", "Human Consultancy", "Human Debate")
TABLE1_N = {"AI Consultancy": 76, "AI Debate": 87, "Human Consultancy": 96, "Human Debate": 154}
TABLE1_SJ = {"AI Consultancy": -1.16, "AI Debate": -1.20, "Human Consultancy": -1.24, "Human Debate": -0.89}
TABLE1_ECE = {"AI Consultancy": 0.17, "AI Debate": 0.16, "Human Consultancy": 0.17, "Human Debate": 0.11}
PAPER_ACC = {"AI Consultancy": 80, "AI Debate": 78, "Human Consultancy": 74, "Human Debate": 84}
BOOT = 10000
OUTPUTS = ("rooms", "human_debate", "human_consultancy", "z_test", "p_value", "fisher", "ai_settings", "above_chance",
           "confident", "judges", "consultancy_split", "scores", "continues", "bootstrap", "conditions_met",
           "conditions_total", "test_passed", "controls_passed", "controls_total")
LIMIT = 200


class Refused(Exception):
    pass


# ---------------------------------------------------------------- reading

def read_input(inputs):
    name, sha, size = INPUT
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha or len(data) != size:
        raise Refused(f"{name}: sha256 {got} ({len(data)} bytes), not the registered {sha} ({size})")
    return data


def setting_of(room):
    s = room.get("setting")
    if not isinstance(s, dict) or not isinstance(s.get("isHuman"), bool) or not isinstance(s.get("isDebate"), bool):
        raise Refused(f"{room.get('name')}: no setting")
    return ("Human " if s["isHuman"] else "AI ") + ("Debate" if s["isDebate"] else "Consultancy")


def parse(data):
    rows = []
    for k, line in enumerate(data.decode("utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            raise Refused(f"line {k + 1}: not JSON")
    included = []
    for room in rows:
        if room.get("includedInPaper") is not True:
            continue
        name = room.get("name")
        try:
            result = room["status"]["Complete"]["result"]
            info = result["judgingInfo"]
            final = info["finalJudgement"]
            correct = info["correctAnswerIndex"]
        except (KeyError, TypeError):
            raise Refused(f"{name}: included but not complete with a judgement")
        if (not isinstance(final, list) or len(final) != 2 or not all(isinstance(x, (int, float)) for x in final)
                or abs(sum(final) - 1.0) > 1e-9 or correct not in (0, 1) or result.get("correctAnswerIndex") != correct):
            raise Refused(f"{name}: an unreadable judgement")
        roles = room.get("roleAssignments") or {}
        debaters = sorted(r for r in roles if r.startswith("Debater "))
        included.append({
            "name": name, "setting": setting_of(room), "p_correct": float(final[correct]), "final": final,
            "correct": correct, "judge": roles.get("Judge"), "debaters": debaters,
            "consultant_answer": ({"Debater A": 0, "Debater B": 1}.get(debaters[0]) if len(debaters) == 1 else None),
            "reward": info.get("judgeReward"), "continues": info.get("numContinues"),
            "agree": result.get("correctAnswerIndex") == info.get("correctAnswerIndex")})
    return rows, included


# ---------------------------------------------------------------- statistics

def right(r):
    return r["p_correct"] > 0.5


def round_pct(x):
    return math.floor(100 * x + 0.5)


def normal_tail2(z):
    """Two-sided normal tail probability."""
    return math.erfc(abs(z) / math.sqrt(2))


def z_test(x1, n1, x2, n2):
    p1, p2 = x1 / n1, x2 / n2
    pool = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pool * (1 - pool) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se
    return z, normal_tail2(z)


def binom_upper(x, n, p=0.5):
    """P(X >= x) for X ~ Binomial(n, p), exactly (as a float)."""
    return sum(math.comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(x, n + 1))


def hypergeom(a, b, c, d):
    """The probability of the table [[a, b], [c, d]] with its margins fixed."""
    n = a + b + c + d
    return math.comb(a + b, a) * math.comb(c + d, c) / math.comb(n, a + c)


def fisher(a, b, c, d, side="two"):
    """Fisher's exact test of [[a, b], [c, d]]: one-sided (a large) or two-sided (tables no more probable)."""
    r1, r2, c1 = a + b, c + d, a + c
    lo, hi = max(0, c1 - r2), min(r1, c1)
    probs = {k: hypergeom(k, r1 - k, c1 - k, r2 - c1 + k) for k in range(lo, hi + 1)}
    if side == "greater":
        return sum(v for k, v in probs.items() if k >= a)
    obs = probs[a]
    return sum(v for v in probs.values() if v <= obs * (1 + 1e-9))


def ece(rows):
    """Expected calibration error of the final judgements: confidence in the chosen answer, bins of width 0.1."""
    bins = {}
    for r in rows:
        conf = max(r["final"])
        chosen_right = r["final"][r["correct"]] > r["final"][1 - r["correct"]]
        b = min(int(conf * 10), 9)
        bins.setdefault(b, []).append((conf, chosen_right))
    n = len(rows)
    return sum(len(v) / n * abs(sum(c for _, c in v) / len(v) - sum(f for f, _ in v) / len(v)) for v in bins.values())


class Stream:
    """Integers from the seed: SHA-256 of seed, label and a counter, eight bytes at a time."""

    def __init__(self, seed, label):
        self.seed, self.label, self.n, self.buf = seed, label, 0, b""

    def below(self, m):
        if len(self.buf) < 8:
            self.n += 1
            self.buf += hashlib.sha256(f"{self.seed}/{self.label}/{self.n}".encode()).digest()
        v, self.buf = int.from_bytes(self.buf[:8], "big"), self.buf[8:]
        return v % m


def bootstrap(a, b, seed):
    st = Stream(seed, "michael/bootstrap")
    diffs = []
    for _ in range(BOOT):
        sa = sum(a[st.below(len(a))] for _ in range(len(a))) / len(a)
        sb = sum(b[st.below(len(b))] for _ in range(len(b))) / len(b)
        diffs.append(sa - sb)
    diffs.sort()
    return diffs[int(0.025 * BOOT)], diffs[int(0.975 * BOOT) - 1]


def tail_integral(z, steps=200000):
    """2 (1 - Phi(|z|)) by Simpson's rule on the density from |z| to |z| + 12."""
    lo, hi = abs(z), abs(z) + 12.0
    h = (hi - lo) / steps
    f = lambda x: math.exp(-x * x / 2) / math.sqrt(2 * math.pi)  # noqa: E731
    s = f(lo) + f(hi) + sum((4 if k % 2 else 2) * f(lo + k * h) for k in range(1, steps))
    return 2 * s * h / 3


# ---------------------------------------------------------------- the run

def conditions(n_hd, x_hd, n_hc, x_hc, p):
    return {
        "154 human debates and 96 human consultancies included, as Table 1": n_hd == 154 and n_hc == 96,
        "human debate's judge accuracy rounds to 84%": n_hd > 0 and round_pct(x_hd / n_hd) == 84,
        "human consultancy's judge accuracy rounds to 74%": n_hc > 0 and round_pct(x_hc / n_hc) == 74,
        "the two-sided pooled two-proportion z-test gives p < 0.05": p is not None and p < 0.05,
    }


def pct(x):
    return f"{100 * x:.1f}%"


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    rows, inc = parse(read_input(inputs))
    by = {s: [r for r in inc if r["setting"] == s] for s in SETTINGS}
    n = {s: len(v) for s, v in by.items()}
    x = {s: sum(right(r) for r in v) for s, v in by.items()}
    ties = {s: sum(r["p_correct"] == 0.5 for r in v) for s, v in by.items()}
    hd, hc = "Human Debate", "Human Consultancy"
    z, p = z_test(x[hd], n[hd], x[hc], n[hc]) if n[hd] and n[hc] else (None, None)
    fish = fisher(x[hd], n[hd] - x[hd], x[hc], n[hc] - x[hc]) if n[hd] and n[hc] else None
    cond = conditions(n[hd], x[hd], n[hc], x[hc], p)

    chance = {s: binom_upper(x[s], n[s]) for s in SETTINGS if n[s]}
    conf = [r for r in by[hd] if max(r["final"]) >= 0.95]
    judges = {}
    for r in by[hd]:
        judges.setdefault(r["judge"], []).append(right(r))
    perfect = {j: len(v) for j, v in judges.items() if all(v)}
    share90 = sum(1 for v in judges.values() if sum(v) / len(v) >= 0.9) / len(judges) if judges else 0.0
    split = {}
    for s in ("Human Consultancy", "AI Consultancy"):
        hon = [r for r in by[s] if r["consultant_answer"] == r["correct"]]
        dis = [r for r in by[s] if r["consultant_answer"] is not None and r["consultant_answer"] != r["correct"]]
        split[s] = {"honest": (sum(map(right, hon)), len(hon)), "dishonest": (sum(map(right, dis)), len(dis)),
                    "unassigned": sum(1 for r in by[s] if r["consultant_answer"] is None)}
    rewards = {s: (sum(r["reward"] for r in v) / len(v) if v and all(isinstance(r["reward"], (int, float)) for r in v)
                   else None) for s, v in by.items()}
    eces = {s: ece(v) if v else None for s, v in by.items()}
    cont = {s: (sum(r["continues"] for r in v) / len(v) if v and all(isinstance(r["continues"], int) for r in v)
                else None) for s, v in by.items()}
    lo, hi = bootstrap([int(right(r)) for r in by[hd]], [int(right(r)) for r in by[hc]], seed)

    ctl = {}
    zs = (0.5, 1.0, 1.96, 2.026, 3.0)
    ctl["the z-test's tail agrees with a numerical integral of the normal density"] = all(
        abs(normal_tail2(v) - tail_integral(v)) < 1e-9 for v in zs)
    ctl["textbook values: P(X >= 9 | 10, 1/2) = 11/1024 and the tea-tasting Fisher p = 17/70"] = (
        abs(binom_upper(9, 10) - 11 / 1024) < 1e-15 and abs(fisher(3, 1, 1, 3, "greater") - 17 / 70) < 1e-12)
    ctl["every included room's correct answer agrees between fields and its judgement sums to 1"] = all(
        r["agree"] for r in inc)
    ctl["the four settings' included rooms number 76, 87, 96 and 154, Table 1's n"] = n == TABLE1_N

    def acc(s):
        return f"{x[s]} of {n[s]}, {pct(x[s] / n[s])}" if n[s] else "none"

    values = {
        "rooms": (f"{len(rows)} rooms, {len(inc)} included: AI consultancy {n['AI Consultancy']}, AI debate "
                  f"{n['AI Debate']}, human consultancy {n[hc]}, human debate {n[hd]}; ties at one half "
                  f"{sum(ties.values())}"),
        "human_debate": f"human debate: judge right in {acc(hd)} (the paper's 84%)",
        "human_consultancy": f"human consultancy: judge right in {acc(hc)} (the paper's 74%)",
        "z_test": (f"pooled two-proportion z = {z:.3f}, two-sided p = {p:.4f} (the paper's p = 0.04)"
                   if p is not None else "no test"),
        "p_value": None if p is None else round(p, 4),
        "fisher": "none" if fish is None else f"Fisher's exact test of the same table: two-sided p = {fish:.4f}",
        "ai_settings": (f"AI debate {acc('AI Debate')}; AI consultancy {acc('AI Consultancy')} (the paper's 78% and "
                        f"80%)"),
        "above_chance": "one-sided binomial p against 50%: " + "; ".join(
            f"{s.lower()} {chance[s]:.1e}" for s in SETTINGS if s in chance),
        "confident": (f"human debate at 95% confidence or more: {sum(map(right, conf))} of {len(conf)}, "
                      f"{pct(sum(map(right, conf)) / len(conf)) if conf else '-'} (the paper's 88%)"),
        "judges": (f"judges with every human debate right: {len(perfect)}, on {sum(perfect.values())} debates (the "
                   f"paper: the top two, 100% on 36); {pct(share90)} of {len(judges)} judges at 90% or more"),
        "consultancy_split": "; ".join(
            f"{s.split()[0].lower()} honest {v['honest'][0]}/{v['honest'][1]}, dishonest {v['dishonest'][0]}/"
            f"{v['dishonest'][1]}" for s, v in split.items()) + " (the paper's AI: 74% honest, 87% dishonest)",
        "scores": ("mean judgeReward " + ", ".join("-" if rewards[s] is None else f"{rewards[s]:.2f}" for s in SETTINGS)
                   + "; ECE final " + ", ".join("-" if eces[s] is None else f"{eces[s]:.2f}" for s in SETTINGS)
                   + " (Table 1: -1.16, -1.20, -1.24, -0.89; .17, .16, .17, .11)"),
        "continues": ("mean continues " + ", ".join("-" if cont[s] is None else f"{cont[s]:.2f}" for s in SETTINGS)
                      + (f"; human debate / consultancy {cont[hd] / cont[hc]:.2f} (the paper: 68% of the length)"
                         if cont[hd] and cont[hc] else "")),
        "bootstrap": f"95% bootstrap interval of the difference: [{lo:.3f}, {hi:.3f}] ({BOOT:,} resamples)",
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for key, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")
    detail = {"input": {"name": INPUT[0], "sha256": INPUT[1], "bytes": INPUT[2]}, "conditions": cond, "controls": ctl,
              "n": n, "right": x, "ties": ties, "z": z, "p": p, "fisher_two_sided": fish, "chance": chance,
              "confident": {"right": sum(map(right, conf)), "n": len(conf)},
              "judges": {str(j): {"right": sum(v), "n": len(v)} for j, v in sorted(judges.items(), key=str)},
              "perfect_judges": {str(j): k for j, k in perfect.items()}, "consultancy_split": split,
              "mean_reward": rewards, "ece_final": eces, "mean_continues": cont, "bootstrap": [lo, hi],
              "table1": {"n": TABLE1_N, "sj": TABLE1_SJ, "ece": TABLE1_ECE, "accuracy": PAPER_ACC},
              "rooms_total": len(rows), "rooms_included": len(inc)}
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
        sys.exit(f"michael: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
