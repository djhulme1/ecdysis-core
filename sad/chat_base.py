"""Me, Myself, and AI: chat models against their base models on SAD and on MMLU (Laine et al. 2024).

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:bf2181b7da5a8806) is from Laine,
Chughtai, Betley, Hariharan, Scheurer, Balesni, Hobbhahn, Meinke and Evans, "Me, Myself, and AI: The Situational
Awareness Dataset (SAD) for LLMs" (arXiv:2407.04694, v1, July 2024), its abstract: "Chat models, which are finetuned
to serve as AI assistants, outperform their corresponding base models on SAD but not on general knowledge tasks."

Its registered test is TEST below. The paper's own measure of the first half is an average over its five base-chat
pairs ("As expected, chat models outperformed their corresponding base models by +4.5% on average"; the statistic is
AverageChatPlainBoost in the repository's sad/statistics.py), and its measure of general knowledge is MMLU, its
scores taken from HELM's leaderboard or run with HELM's code by the authors (Appendix, Correlations). Read before
registering, and said so in the claim: the paper's printed Table 2 and the repository's printed tables, which put
Llama-2-7b-chat below Llama-2-7b (29.9 against 30.0 in the paper; 30.2 against 32.9 in the repository's later
tables), and the MMLU scores of sad/correlations.py, where Llama-2-7b-chat is above Llama-2-7b. Nothing was computed
from the results files before these rules were committed; a syntax-only pass over them (headers, variants, repeated
rows, empty scores; no score printed) came first.

The inputs are 19 files of the repository the abstract names for its latest results (LRudL/sad at dfc5c98, 14
December 2024, CC BY 4.0), each checked against its SHA-256 and read as data: the 16 per-task results files that
the repository's aggregation reads (get_all_task_data in sad/aggregate_results.py), with the csv module;
sad/correlations.py, whose MMLU_SCORES dictionary holds the MMLU scores the paper uses, parsed with ast.parse and
its dictionary display evaluated with ast.literal_eval (nothing in the file is executed or imported); and the
repository's own printed tables results/result_tables/categories.tex and definition.tex, for two controls. The
method followed is the repository's code at that commit, read before registering: sad/vars.py (the tasks and
categories), sad/task.py (Variant, Category.task_weightings, Task.get_results_df), sad/aggregate_results.py
(get_all_task_data, weighted_stats, aggregate_to_category, aggregate_to_sad_score, get_weighting_dfs),
sad/aggregate_results_vars.py (WEIGHTINGS_DEFINITION, RENAMINGS), sad/models.py (PAIRED_BASE_RLHF_MODELS),
sad/statistics.py, sad/latex_result_table_gen.py (the tables' rounding) and sad/correlations.py.

1. The files. Each results file is a CSV whose header holds model, variant, score and std, with one row per model and
   variant; its task is the file's (FILES below, the tasks of sad/vars.py). A model's name is the file's with "_"
   read as "." (model_safe_name_to_model_real_name: gpt-3_5-turbo-0613 is gpt-3.5-turbo-0613). Rows of names
   beginning "COT " (chain-of-thought runs of two OpenAI models) are set aside, as the repository's tables and
   statistics set them aside. An empty score is a missing result; a present score must be a finite number (the
   repository bounds none: predict_tokens' is normalised against chance) with a finite, non-negative std. A
   repeated (model, variant), a missing column or a malformed number is refused.
2. Aggregation, as weighted_stats. For a model and a variant, the row of task t weighs w_t = 1/n_c, n_c the number of
   tasks of t's category c (Category.task_weightings with its default category_weighting 1, divided by the number of
   t's variants counted in the SAD score, which is 1 for every task: in sad/task.py only the plain variant has
   in_sad_score). Rows without a score are dropped and the rest keep their weights, so the score is
   sum(w_t s_t) / sum(w_t) and its error sqrt(sum(w_t^2 e_t^2)) / sum(w_t) (weighted_std), e_t the row's std. A
   category's score and error are the same over its own tasks. The definition table's groups are the same again over
   the category scores and errors, weighted as WEIGHTINGS_DEFINITION: Self-Knowledge facts, influence and
   introspection a third each; Inferences stages and self-recognition a half each; Actions id-leverage and
   anti-imitation a half each. A model's SAD score is its score with the plain variant, its SP score that with the
   variant sp. Scores are reported in percent.
3. The pairs are PAIRED_BASE_RLHF_MODELS of sad/models.py, in its order: llama-2-7b with llama-2-7b-chat, llama-2-13b
   with llama-2-13b-chat, llama-2-70b with llama-2-70b-chat, davinci-002 with gpt-3.5-turbo-0613, gpt-4-base with
   gpt-4-0613. Each of the ten must have a score on all 16 tasks with the plain variant; otherwise refused.
4. Condition SAD holds when the mean SAD score of the five chat models is above the mean SAD score of the five base
   models (AverageChatPlainBoost above 0; there the base mean is over BASE_MODELS, the same five).
5. Condition MMLU holds when, over the pairs whose base and chat models both have an MMLU score, the chat models' mean
   MMLU score is not above the base models' mean. MMLU_SCORES is the assignment of that name in sad/correlations.py,
   a dictionary of model names to fractions in [0, 1]; gpt-4-base's entry is the paper's estimate ("We estimate
   GPT-4-base's MMLU score to be that of GPT-4-0613"; the file's comment: "copy from gpt-4-0613") and is not a
   measurement, so its pair is left out, and davinci-002 has no entry ("We omit davinci-002's MMLU score"), so the
   pairs counted are those of Llama 2, which must be three.
6. The test passes when both conditions hold; conditions_met counts them (of 2).

Beside the test, not counted: each pair's SAD difference with its error, sqrt(e_base^2 + e_chat^2), and its ratio;
how many pairs have the chat model above its base model (the claim read pair by pair); the exact one-sided sign-flip
p of the mean difference over the five pairs (all 32 sign patterns, a pattern counted when its mean is at least the
observed one); the same comparison with the situating prompt (variant sp); the mean chat-minus-base difference in
each category; MMLU pair by pair, and its mean difference with the GPT-4 pair's copied score included; and the
paper's printed Table 2 (arXiv v1 e-print, sha256 8498404c...) for the ten models beside the released results.

Controls (controls_passed of controls_total):
 (a) categories.tex, the repository's printed table of SAD and category scores: for every model row, its Overall and
     its seven category scores recomputed by rules 1 and 2 with the plain variant, each within 0.05 + 1e-9 of the
     printed value (the tables print round(100 x, 1)); the table's names are the models' after RENAMINGS
     (claude-3-haiku-20240307 is claude-3-haiku, and so on), and its rows must be the files' models exactly.
 (b) definition.tex, its printed table of SAD scores and groups with errors: for every model, Overall and the three
     groups, each score and each error within 0.05 + 1e-9.
 (c) The aggregation on a table worked by hand (SYNTHETIC below): three categories, a missing task, two variants.
 (d) The MMLU reader on a file written for it (MMLU_PROBE below), holding a commented-out entry, comments after
     values and other assignments, returns exactly the dictionary written there.

The seed draws nothing: every number is fixed by the files. It is checked and recorded.
"""

import ast
import csv
import hashlib
import io
import json
import math
import os
import re
import sys

COMMIT = "dfc5c9831a9bcc5c9a9dbdcaa2955aae983cd1d3"
TEST = ("Refuted if, on the per-task results released with the paper (LRudL/sad at dfc5c98, plain prompt, each of "
        "the seven categories weighted equally and each task equally within its category, as the repository "
        "aggregates them), the mean SAD score of the chat models of its five base-chat pairs is not above the mean "
        "of their base models, or if, on the MMLU scores the paper uses (the repository's MMLU_SCORES, for the "
        "three Llama 2 pairs that have both), the chat models' mean is above the base models' mean.")

# (input file, task, category): sad/vars.py's ALL_TASKS and ALL_CATEGORIES
FILES = (
    ("facts_human_defaults.csv", "facts_human_defaults", "facts"),
    ("facts_llms.csv", "facts_llms", "facts"),
    ("facts_which_llm.csv", "facts_which_llm", "facts"),
    ("facts_names.csv", "facts_names", "facts"),
    ("influence.csv", "influence", "influence"),
    ("introspection_count_tokens.csv", "introspection_count_tokens", "introspection"),
    ("introspection_predict_tokens.csv", "introspection_predict_tokens", "introspection"),
    ("introspection_rules.csv", "introspection_rules", "introspection"),
    ("stages_full.csv", "stages_full", "stages"),
    ("stages_oversight.csv", "stages_oversight", "stages"),
    ("self_recognition_who.csv", "self_recognition_who", "self-recognition"),
    ("self_recognition_groups.csv", "self_recognition_groups", "self-recognition"),
    ("id_leverage_entity_name.csv", "id_leverage_entity_name", "id-leverage"),
    ("id_leverage_multihop.csv", "id_leverage_multihop", "id-leverage"),
    ("output_control.csv", "output_control", "anti-imitation"),
    ("base_model_deviation.csv", "base_model_deviation", "anti-imitation"),
)
CATEGORIES = ("facts", "influence", "introspection", "stages", "self-recognition", "id-leverage", "anti-imitation")
GROUPS = (  # WEIGHTINGS_DEFINITION
    ("Self-Knowledge", {"facts": 1 / 3, "influence": 1 / 3, "introspection": 1 / 3}),
    ("Inferences", {"stages": 1 / 2, "self-recognition": 1 / 2}),
    ("Actions", {"id-leverage": 1 / 2, "anti-imitation": 1 / 2}),
)
PAIRS = (  # PAIRED_BASE_RLHF_MODELS
    ("llama-2-7b", "llama-2-7b-chat"),
    ("llama-2-13b", "llama-2-13b-chat"),
    ("llama-2-70b", "llama-2-70b-chat"),
    ("davinci-002", "gpt-3.5-turbo-0613"),
    ("gpt-4-base", "gpt-4-0613"),
)
MMLU_ESTIMATED = ("gpt-4-base",)  # the paper's estimate, not a measurement (rule 5)
RENAMINGS = {  # sad/aggregate_results_vars.py, the model names it renames
    "claude-3-haiku-20240307": "claude-3-haiku",
    "claude-3-sonnet-20240229": "claude-3-sonnet",
    "claude-3-opus-20240229": "claude-3-opus",
    "claude-3-5-sonnet-20240620": "claude-3.5-sonnet",
}
# The paper's printed Table 2 (arXiv v1 e-print, result_tables/categories.tex), the SAD column, for the ten models.
PRINTED_V1 = {
    "llama-2-7b": 30.0, "llama-2-7b-chat": 29.9, "llama-2-13b": 29.4, "llama-2-13b-chat": 34.8,
    "llama-2-70b": 31.6, "llama-2-70b-chat": 36.9, "davinci-002": 29.1, "gpt-3.5-turbo-0613": 35.5,
    "gpt-4-base": 36.6, "gpt-4-0613": 42.2,
}
EPRINT_SHA256 = "8498404c6f204ff9a20584fb2143b487b4bb66ceb38429588a7fb9580dde2040"
TABLE_TOLERANCE = 0.05 + 1e-9
INPUTS = {
    "facts_human_defaults.csv": "7ed91192c27504e3d4c5cf46a92529c6d79131963f10c024de2cf13db0ddeb30",
    "facts_llms.csv": "9641daba811d2c344e2b58e87ccabd5427cb479ffa7a8781f35cf29783a2b6dc",
    "facts_which_llm.csv": "cd891cbe65289feb8c1c78e7c4beae18111fe3bd5f78c3b40596b1d9b709f567",
    "facts_names.csv": "783a1eb6c07e8059a0b4e3637ff54e047184645bf3e68ec86c1386b8ef4a1f01",
    "influence.csv": "35461702497f47ea1768f7d9be611d55f018f6d2d23e1d2c79f7cc17d097ab7f",
    "introspection_count_tokens.csv": "3f5e216618a737b80114f470d95a9a0056c9430abed74113b3dc450170a953b2",
    "introspection_predict_tokens.csv": "44583b3f5f7d2a67dee1688176ca3c98e00f164e94ecea7f5ffa15d997a2d271",
    "introspection_rules.csv": "c79d68e2c25a613055f6da92252ab2db6bd396e117795a26b983428799895f56",
    "stages_full.csv": "1880c8b9cce5cb74d8c3c6d11265f2c5882220771408203ab829ad419a57277c",
    "stages_oversight.csv": "1a8f5930bb81056ef4bfca7f014befcd9c0ae0afb45f667a04f625be75ff6a57",
    "self_recognition_who.csv": "760e0c2c813233946fca56d7af771444b61b56d477ca70424cdccec8e5295c78",
    "self_recognition_groups.csv": "48d0c80ff52ebdcfe0eba6782655d80c30f00db41ea96e892e9e6bf6f5068437",
    "id_leverage_entity_name.csv": "2ceef788e1ce1e6c055a24f6a60de2028171d14e6e98856991e0cdd8269177d2",
    "id_leverage_multihop.csv": "e2fec58bac4eaf0b1fb31b68d899b26617f9bc654a36c621e3140f4d1834b481",
    "output_control.csv": "026c23fc33dd28d5e531411edbd1a20c96cea498f4939d32012049d00db8464b",
    "base_model_deviation.csv": "c48909c2c89a7baab758878c050476c41eac142067b1bf19d23bb0494f9d2a91",
    "correlations.py": "efd459dac45089ef22c46dcbaec6bc7cf2401aaaa3ae65d1ef9ab26ca34b86de",
    "categories.tex": "f1e463fca3e24ad301f8e0b7c52081ba30c50d4bd97b8949584ca20de10115ae",
    "definition.tex": "92eac2dc04f54a48982c2e5984b5a145e193926f93c705a6a5bd143ae64e5bd7",
}

# Control (c): two tasks in "a", one in "b", two in "c"; model m misses task b1 with the plain variant.
SYNTHETIC_FILES = (("a1", "a"), ("a2", "a"), ("b1", "b"), ("c1", "c"), ("c2", "c"))
SYNTHETIC = {
    "a1": "model,task,variant,score,std\nm,a1,plain,0.5,0.1\nm,a1,sp,0.9,0.1\nCOT m,a1,plain,1.0,0.0\n",
    "a2": "model,task,variant,score,std\nm,a2,plain,0.7,0.2\nm,a2,sp,0.1,0.1\n",
    "b1": "model,task,variant,score,std\nm,b1,plain,,\nm,b1,sp,0.4,0.2\n",
    "c1": "model,task,variant,score,std\nm,c1,plain,0.2,0.3\nm,c1,sp,0.2,0.0\n",
    "c2": "model,task,variant,score,std\nm,c2,plain,0.4,0.1\nm,c2,sp,0.6,0.0\n",
}
# plain: weights a1, a2, c1, c2 = 1/2 each (b1 dropped): (0.25 + 0.35 + 0.1 + 0.2) / 2 = 0.45;
#   error sqrt(0.25 (0.01 + 0.04 + 0.09 + 0.01)) / 2 = sqrt(0.0375) / 2
# sp: weights 1/2, 1/2, 1, 1/2, 1/2: (0.45 + 0.05 + 0.4 + 0.1 + 0.3) / 3 = 1.3 / 3;
#   error sqrt(0.25 (0.01 + 0.01) + 0.04) / 3 = sqrt(0.045) / 3
# category a, plain: 0.6, error sqrt(0.25 (0.01 + 0.04)) = sqrt(0.0125); category c, sp: 0.4, error 0
SYNTHETIC_EXPECTED = {
    ("m", "plain"): (0.45, math.sqrt(0.0375) / 2),
    ("m", "sp"): (1.3 / 3, math.sqrt(0.045) / 3),
    ("m", "plain", "a"): (0.6, math.sqrt(0.0125)),
    ("m", "sp", "c"): (0.4, 0.0),
}
MMLU_PROBE = (
    "import os\n"
    "NOTE = {'x': 1}\n"
    "# TODO: a comment line\n"
    "MMLU_SCORES = {\n"
    "    \"p-1\": 0.25,  # helm\n"
    "    # \"p-2\": 0.5, # left out\n"
    "    \"p_3\": 0.875,\n"
    "}\n"
    "OTHER = {\"p-1\": 0.9}\n"
)
MMLU_PROBE_EXPECTED = {"p-1": 0.25, "p_3": 0.875}


class Refused(Exception):
    pass


def read_bytes(path, sha256):
    with open(path, "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha256:
        raise Refused(f"{path}: sha256 {got}, not the registered {sha256}")
    return data


def real_name(name):
    return name.replace("_", ".")


def _number(text, what):
    try:
        x = float(text)
    except ValueError:
        raise Refused(f"{what}: {text!r} is not a number")
    if not math.isfinite(x):
        raise Refused(f"{what}: {text!r} is not finite")
    return x


def read_results(text, task):
    """Rule 1: {(model, variant): (score or None, std or None)} for one task, chain-of-thought rows set aside."""
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or not {"model", "variant", "score", "std"} <= set(reader.fieldnames):
        raise Refused(f"{task}: the header lacks model, variant, score or std")
    rows = {}
    for r in reader:
        model, variant = (r["model"] or "").strip(), (r["variant"] or "").strip()
        if not model or not variant:
            raise Refused(f"{task}: a row without a model or a variant")
        if model.startswith("COT "):
            continue
        key = (real_name(model), variant)
        if key in rows:
            raise Refused(f"{task}: {key} repeated")
        s = (r["score"] or "").strip()
        if s == "":
            rows[key] = (None, None)
            continue
        score = _number(s, f"{task} {key} score")
        std = _number((r["std"] or "").strip(), f"{task} {key} std")
        if std < 0:
            raise Refused(f"{task}: {key} std {std} is negative")
        rows[key] = (score, std)
    return rows


def weighted(items):
    """weighted_stats over (weight, score, error) items with a score: (mean, error), both None when nothing is left."""
    items = [(w, s, e) for w, s, e in items if s is not None]
    total = sum(w for w, _, _ in items)
    if not items or total == 0:
        return None, None
    mean = sum(w * s for w, s, _ in items) / total
    err = math.sqrt(sum(w * w * e * e for w, _, e in items)) / total
    return mean, err


class Table:
    """The task results of rule 1 and the aggregation of rule 2."""

    def __init__(self, files, results):
        # files: ((task, category), ...); results: {task: {(model, variant): (score, std)}}
        self.files = tuple(files)
        self.results = results
        self.size = {}
        for _, cat in self.files:
            self.size[cat] = self.size.get(cat, 0) + 1

    def models(self):
        return sorted({m for rows in self.results.values() for (m, _) in rows})

    def row(self, task, model, variant):
        return self.results[task].get((model, variant), (None, None))

    def score(self, model, variant, category=None):
        items = []
        for task, cat in self.files:
            if category is not None and cat != category:
                continue
            s, e = self.row(task, model, variant)
            items.append((1 / self.size[cat], s, e))
        return weighted(items)

    def group(self, model, variant, weights):
        items = []
        for cat, w in weights.items():
            s, e = self.score(model, variant, cat)
            items.append((w, s, e))
        return weighted(items)

    def complete(self, model, variant):
        return all(self.row(task, model, variant)[0] is not None for task, _ in self.files)


def read_mmlu(text):
    """Rule 5: the dictionary display assigned to MMLU_SCORES, evaluated as a literal; nothing is executed."""
    tree = ast.parse(text)
    found = [node for node in tree.body if isinstance(node, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == "MMLU_SCORES" for t in node.targets)]
    if len(found) != 1 or not isinstance(found[0].value, ast.Dict):
        raise Refused("correlations.py: not exactly one dictionary assigned to MMLU_SCORES")
    scores = ast.literal_eval(found[0].value)
    if not all(isinstance(k, str) and isinstance(v, float) and 0 <= v <= 1 for k, v in scores.items()):
        raise Refused("correlations.py: MMLU_SCORES is not a dictionary of names to fractions")
    return scores


_MACRO = re.compile(r"\\(?:textit|textbf|underline)\{")
_ERROR = re.compile(r"\\error\{([0-9.]+)\}")


def _cell(text):
    t = text.replace("\\phantom{0}", "")
    err = None
    m = _ERROR.search(t)
    if m:
        err = float(m.group(1))
        t = t[:m.start()] + t[m.end():]
    t = _MACRO.sub("", t).replace("{", "").replace("}", "").strip()
    return float(t), err


def read_table(text):
    """A printed table: its column names and {model: [(value, error or None), ...]}, the two summary rows left out."""
    header, rows = None, {}
    for line in text.splitlines():
        line = line.strip()
        if not line.endswith("\\\\") or line.startswith("&") or line.startswith("\\"):
            continue
        cells = [c.strip() for c in line[:-2].split("&")]
        if cells[0] == "Model":
            header = [_MACRO.sub("", c).replace("}", "").strip() for c in cells[1:]]
            continue
        if cells[0] in ("Random Chance", "Upper Baseline"):
            continue
        if cells[0] in rows:
            raise Refused(f"table: {cells[0]} repeated")
        rows[cells[0]] = [_cell(c) for c in cells[1:]]
    if header is None or any(len(v) != len(header) for v in rows.values()):
        raise Refused("table: no header, or a row of another width")
    return header, rows


def table_control(table, text, with_errors):
    """Controls (a) and (b): every printed value recomputed within the tables' rounding."""
    header, printed = read_table(text)
    names = {RENAMINGS.get(m, m): m for m in table.models()}
    worst, checked, bad = 0.0, 0, []
    if set(printed) != set(names):
        return {"passed": False, "why": "the table's models are not the files'",
                "only_table": sorted(set(printed) - set(names)), "only_files": sorted(set(names) - set(printed))}
    groups = dict(GROUPS)
    for shown, model in sorted(names.items()):
        for col, (value, err) in zip(header, printed[shown]):
            if col == "Overall":
                s, e = table.score(model, "plain")
            elif col in CATEGORIES:
                s, e = table.score(model, "plain", col)
            elif col in groups:
                s, e = table.group(model, "plain", groups[col])
            else:
                return {"passed": False, "why": f"unknown column {col}"}
            pairs = [(s, value)] + ([(e, err)] if with_errors else [])
            for got, want in pairs:
                if got is None or want is None:
                    bad.append([shown, col, "missing"])
                    continue
                gap = abs(100 * got - want)
                worst = max(worst, gap)
                checked += 1
                if gap > TABLE_TOLERANCE:
                    bad.append([shown, col, round(100 * got, 4), want])
    return {"passed": not bad and checked > 0, "checked": checked, "largest_gap": round(worst, 6),
            "models": len(names), "columns": header, "mismatches": bad[:20]}


def synthetic_control():
    files = [(t, c) for t, c in SYNTHETIC_FILES]
    table = Table(files, {t: read_results(SYNTHETIC[t], t) for t, _ in files})
    got = {
        ("m", "plain"): table.score("m", "plain"),
        ("m", "sp"): table.score("m", "sp"),
        ("m", "plain", "a"): table.score("m", "plain", "a"),
        ("m", "sp", "c"): table.score("m", "sp", "c"),
    }
    ok = table.models() == ["m"] and all(
        abs(got[k][0] - v[0]) < 1e-12 and abs(got[k][1] - v[1]) < 1e-12 for k, v in SYNTHETIC_EXPECTED.items())
    return {"passed": ok, "got": {"|".join(k): [round(x, 12) for x in v] for k, v in got.items()}}


def mmlu_control():
    got = read_mmlu(MMLU_PROBE)
    return {"passed": got == MMLU_PROBE_EXPECTED, "got": got}


def sign_flip_p(diffs):
    """Exact one-sided p of the mean difference: the share of the 2^n sign patterns with a mean at least as large."""
    n = len(diffs)
    obs = sum(diffs) / n
    hits = 0
    for mask in range(2 ** n):
        mean = sum((-d if mask >> i & 1 else d) for i, d in enumerate(diffs)) / n
        if mean >= obs - 1e-12:
            hits += 1
    return hits / 2 ** n


def pct(x):
    return None if x is None else round(100 * x, 4)


def compare(table, variant):
    pairs, diffs = [], []
    for base, chat in PAIRS:
        b, eb = table.score(base, variant)
        c, ec = table.score(chat, variant)
        if b is None or c is None:
            raise Refused(f"{base} or {chat} has no score with the variant {variant}")
        d, e = c - b, math.sqrt(eb * eb + ec * ec)
        diffs.append(d)
        pairs.append({"base": base, "chat": chat, "base_score": pct(b), "chat_score": pct(c), "difference": pct(d),
                      "error": pct(e), "ratio": round(d / e, 4) if e > 0 else None})
    mean_b = sum(table.score(b, variant)[0] for b, _ in PAIRS) / len(PAIRS)
    mean_c = sum(table.score(c, variant)[0] for _, c in PAIRS) / len(PAIRS)
    return pairs, diffs, mean_b, mean_c


def assess(table, mmlu, categories_tex, definition_tex, seed):
    for base, chat in PAIRS:
        for m in (base, chat):
            if not table.complete(m, "plain"):
                raise Refused(f"{m} lacks a plain score on some task")
    pairs, diffs, mean_b, mean_c = compare(table, "plain")
    sad_ok = mean_c > mean_b
    above = [p["chat"] for p, d in zip(pairs, diffs) if d > 0]
    not_above = [[p["base"], p["chat"]] for p, d in zip(pairs, diffs) if not d > 0]

    counted = [(b, c) for b, c in PAIRS if b in mmlu and c in mmlu and b not in MMLU_ESTIMATED]
    if [b for b, _ in counted] != ["llama-2-7b", "llama-2-13b", "llama-2-70b"]:
        raise Refused(f"the MMLU pairs are {counted}, not the three Llama 2 pairs")
    mmlu_b = sum(mmlu[b] for b, _ in counted) / len(counted)
    mmlu_c = sum(mmlu[c] for _, c in counted) / len(counted)
    mmlu_ok = not mmlu_c > mmlu_b
    mmlu_pairs = [{"base": b, "chat": c, "base_mmlu": round(100 * mmlu[b], 4), "chat_mmlu": round(100 * mmlu[c], 4),
                   "difference": round(100 * (mmlu[c] - mmlu[b]), 4)} for b, c in counted]
    with_est = [(b, c) for b, c in PAIRS if b in mmlu and c in mmlu]
    mmlu_with_est = sum(mmlu[c] - mmlu[b] for b, c in with_est) / len(with_est)

    sp_pairs, sp_diffs, sp_b, sp_c = compare(table, "sp")
    cat_boost = {}
    for cat in CATEGORIES:
        ds = [table.score(c, "plain", cat)[0] - table.score(b, "plain", cat)[0] for b, c in PAIRS]
        cat_boost[cat] = round(100 * sum(ds) / len(ds), 4)

    controls = {
        "categories_table": table_control(table, categories_tex, with_errors=False),
        "definition_table": table_control(table, definition_tex, with_errors=True),
        "synthetic": synthetic_control(),
        "mmlu_reader": mmlu_control(),
    }
    met = int(sad_ok) + int(mmlu_ok)
    sign = lambda x: f"{x:+.2f}"
    v1 = {m: PRINTED_V1[m] for pair in PAIRS for m in pair}
    out = {
        "sad_mean_base": pct(mean_b),
        "sad_mean_chat": pct(mean_c),
        "sad_boost": pct(mean_c - mean_b),
        "sad_pairs": "chat minus base (error), by base model: " + "; ".join(
            f"{p['base']} {sign(p['difference'])} ({p['error']:.2f})" for p in pairs),
        "pairs_chat_above": len(above),
        "pairs_not_above": "pairs whose chat model is not above its base model: " + (
            ", ".join(f"{b}/{c}" for b, c in not_above) if not_above else "none"),
        "sign_flip_p": sign_flip_p(diffs),
        "mmlu_mean_base": round(100 * mmlu_b, 4),
        "mmlu_mean_chat": round(100 * mmlu_c, 4),
        "mmlu_difference": round(100 * (mmlu_c - mmlu_b), 4),
        "mmlu_pairs": "MMLU, chat minus base: " + "; ".join(
            f"{p['base']} {p['base_mmlu']:.1f} to {p['chat_mmlu']:.1f} ({sign(p['difference'])})" for p in mmlu_pairs),
        "mmlu_pairs_chat_above": sum(1 for p in mmlu_pairs if p["difference"] > 0),
        "mmlu_difference_with_estimate": round(100 * mmlu_with_est, 4),
        "sp_boost": pct(sp_c - sp_b),
        "sp_pairs_chat_above": sum(1 for d in sp_diffs if d > 0),
        "category_boost": "mean chat minus base by category: " + "; ".join(
            f"{c} {sign(v)}" for c, v in cat_boost.items()),
        "printed_v1": "chat minus base, Table 2 of v1 / released: " + "; ".join(
            f"{b} {sign(v1[c] - v1[b])} / {sign(p['difference'])}" for (b, c), p in zip(PAIRS, pairs)),
        "conditions_met": met,
        "conditions_total": 2,
        "test_passed": int(met == 2),
        "controls_passed": sum(1 for c in controls.values() if c["passed"]),
        "controls_total": len(controls),
    }
    for k, v in out.items():
        if isinstance(v, str) and len(v) > 200:
            raise AssertionError(f"{k}: longer than 200 characters: {v}")
        if not isinstance(v, (int, float, str)) or isinstance(v, bool):
            raise AssertionError(f"{k}: not a number or a string")
    detail = {
        "test": TEST,
        "seed": seed,
        "conditions": {"sad": sad_ok, "mmlu": mmlu_ok},
        "sad_pairs": pairs,
        "mmlu_pairs": mmlu_pairs,
        "category_boost": cat_boost,
        "printed_v1": [{"model": m, "printed": PRINTED_V1[m], "released": pct(table.score(m, "plain")[0])}
                       for pair in PAIRS for m in pair],
        "sp_pairs": sp_pairs,
        "controls": controls,
        "sad_all": {m: pct(table.score(m, "plain")[0]) for m in table.models()},
        "mmlu_scores": mmlu,
        "mmlu_pairs_counted": counted,
        "eprint_sha256": EPRINT_SHA256,
    }
    return out, detail


def run(seed, inputs="inputs", results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    raw = {name: read_bytes(os.path.join(inputs, name), sha) for name, sha in INPUTS.items()}
    table = Table([(t, c) for _, t, c in FILES],
                  {t: read_results(raw[f].decode("utf-8"), t) for f, t, _ in FILES})
    mmlu = read_mmlu(raw["correlations.py"].decode("utf-8"))
    out, detail = assess(table, mmlu, raw["categories.tex"].decode("utf-8"), raw["definition.tex"].decode("utf-8"),
                         seed)
    detail["inputs"] = {"commit": COMMIT, "files": INPUTS}
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
        sys.exit(f"chat_base: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
