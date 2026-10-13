#!/usr/bin/env python3
"""Gradient alignment in subliminal learning (Kitkana & Arora 2026), in their MNIST setting, run afresh.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:6abdc3180117c8de) is from Kitkana & Arora,
"Sustained Gradient Alignment Mediates Subliminal Learning in a Multi-Step Setting: Evidence from MNIST Auxiliary Logit
Distillation Experiment" (arXiv:2604.25779, 2026): "We empirically show that gradient alignment remains weakly but
consistently positive throughout training and causally contributes to trait acquisition."

Its registered test: refuted if, over 32 seed-drawn runs of the paper's setting (its appendix and code: Cloud et al.'s
784-256-256-13 MLP; teacher 5 epochs on 50,000 digits, 10,000 held out; student from the same initialisation, 5 epochs of
KL on the 3 auxiliary logits over uniform noise; Adam 3e-4, batches of 1,024), the trait and distillation gradients'
cosine is positive on under 64% of steps on average, or on at most half in any epoch, or averages under 0.0038 or 0.1 or
more; or projecting out the trait-aligned component lowers mean accuracy by under 22.6 points.

PyTorch, in the pinned image, on the CPU: two worker processes of one thread each, every run on its own streams, so the
result does not depend on which worker takes which run. The inputs are the claim's data of record, each checked against
its SHA-256: MNIST's four files (read as data); the authors' two notebooks (subliminal-learning.ipynb for the alignment,
conflicting-gradients.ipynb for the projection; read as JSON text only: every setting this module takes from them must
appear in their code cells verbatim; nothing in them is run); and their released results for the projection
(runs_mnist_conflicting_grad_revised.zip; its CSV files are read as data). Every rule below was fixed before any seed
existed.

1. The digits: MNIST's idx files, scaled as the notebooks' transform scales them (ToTensor, then Normalize(0.5, 0.5)):
   x / 255, less 0.5, over 0.5, in float32.
2. The network, as the notebooks' MLPClassifier: 784 -> 256 -> 256 -> 13 with ReLU, weights normal with mean 0 and
   standard deviation 1/sqrt(fan-in), biases 0. Logits 0-9 are the classes, 10-12 the auxiliary ("no-class") logits.
3. Each run r of 32, from PyTorch generators seeded with the first 8 bytes of SHA-256(the seed's bytes || "|align/" ||
   a label), less the top bit, as follows (the notebooks' run_one_instance and run_one_seed):
   - the initialisation (label init/r), shared by the teacher and the students;
   - a split of the 60,000 training digits (split/r): a random permutation, its first 50,000 for the teacher and the
     other 10,000 as the audit set;
   - the teacher: Adam at 3e-4, 5 epochs over the 50,000 in a fresh permutation each epoch (teach/r), batches of 1,024
     (the last 848), cross-entropy on logits 0-9 averaged over the batch;
   - the noise: 60,000 images uniform on [-1, 1) (noise/r), and its order, a fresh permutation each epoch (order/r),
     shared by the students of the run, as the notebooks share it (both loaders seeded alike);
   - the student: Adam at 3e-4, 5 epochs over the noise, batches of 1,024 (the last 608), the loss KL(teacher ||
     student) between the softmaxes of logits 10-12, summed over the batch and divided by its size (KLDivLoss,
     "batchmean"). At every step, before the update: the distillation gradient, and the trait gradient, the gradient of
     the mean over the audit set's batches (1,024 each, the last 784, in a fresh permutation each step, audit/r) of
     their mean cross-entropy on logits 0-9; their inner product and cosine (the product over the norms, the
     denominator at least 1e-12). The update uses the distillation gradient alone.
   - the projected student (the notebook's intervention): the same, but at every step the trait gradient is that of
     one audit batch, taken in turn from passes over the audit set in fresh permutations (audit1/r), and when its inner
     product with the distillation gradient is positive the update is the distillation gradient less its component
     along the trait gradient: g - (<g, t> / (|t|^2 + 1e-12)) t.
   - each network's accuracy on the 10,000 test digits, by the largest of logits 0-9.
4. The statistics, as the notebook's compute_run_level_summary: for each run, the fraction of steps whose cosine is
   positive (overall and in each epoch) and the mean cosine; across runs, means and standard deviations (n - 1).
5. The test's five conditions: the runs' mean fraction of positive steps at least 0.64; in each epoch, the runs' mean
   fraction above 0.5; the mean cosine at least 0.0038 and below 0.1; the projected students' mean accuracy at least
   22.6 points below the students'. test_passed is 1 if all five hold.
6. Beside the test: the teachers' accuracy; how often the projection acted; a placebo for 8 of the runs (place/r: the
   same projection rule, but along a fresh random direction, normal in every coordinate, each step), which tells
   whether removing any small component would do; and the authors' released results for the projection (100 seeds,
   control and intervention), summarised from their CSVs beside the paper's printed numbers.
7. Controls, which must all pass or the run stops: the digits' counts per class are MNIST's published ones; and every
   projected update is orthogonal to its trait gradient (|cosine| below 1e-4).

Writes results/outputs.json (the 20 values a receipt carries) and results/detail.json (every value computed).
"""

import os

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[_v] = "1"

import csv  # noqa: E402
import gzip  # noqa: E402
import hashlib  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import multiprocessing  # noqa: E402
import re  # noqa: E402
import statistics  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
import zipfile  # noqa: E402

import numpy as np  # noqa: E402
import torch as t  # noqa: E402
from torch import nn  # noqa: E402

t.set_num_threads(1)

INPUTS = {
    "train_x": ("train-images-idx3-ubyte.gz", "440fcabf73cc546fa21475e81ea370265605f56be210a4024d2ca8f203523609"),
    "train_y": ("train-labels-idx1-ubyte.gz", "3552534a0a558bbed6aed32b30c495cca23d567ec52cac8be1a0730e8010255c"),
    "test_x": ("t10k-images-idx3-ubyte.gz", "8d422c7b0a1c1c79245a5bcf07fe86e33eeafee792b84584aec276f5a2dbc4e6"),
    "test_y": ("t10k-labels-idx1-ubyte.gz", "f7ae60f92e00ec6debd23a6088c31dbd2371eca3ffa0defaefb259924204aec6"),
    "align": ("subliminal-learning.ipynb", "bd3c24a89fc1d039f140bbf4fdec0fad675652b9c583c653995941a66f8c7a24"),
    "project": ("conflicting-gradients.ipynb", "5f43567e8205cad51446b798e70fa7cdb7d250ca98817d23536c3470ca1a4ce7"),
    "released": ("runs_mnist_conflicting_grad_revised.zip",
                 "c61a04bcbb4a29b80a406294fd42c262db5119b9cf07b13dd62b979f4cc9119e"),
}
TRAIN_COUNTS = (5923, 6742, 5958, 6131, 5842, 5421, 5918, 6265, 5851, 5949)
TEST_COUNTS = (980, 1135, 1032, 1010, 982, 892, 958, 1028, 974, 1009)
SIZES = (784, 256, 256, 13)
RUNS, PLACEBO_RUNS, WORKERS = 32, 8, 2
EPOCHS, BATCH, LR, AUDIT, NOISE, EPS = 5, 1024, 3e-4, 10_000, 60_000, 1e-12
FRAC_MIN, EPOCH_FRAC, COS_LOW, COS_HIGH, DROP = 0.64, 0.5, 0.0038, 0.1, 22.6
ORTHO = 1e-4
PRINTED = {"control": (55.28, 10.48, 26.31, 76.04), "intervention": (10.14, 1.33), "frac_pos": (0.781, 0.102),
           "cos": (0.00752, 0.00167)}
ALIGN_FACTS = (
    "batch_size=1024", "audit_size=10_000", "noise_dataset_size=60_000", "hidden_dim=256", "aux_m=3",
    "teacher_epochs=5", "student_epochs=5", "lr_teacher=3e-4", "lr_student=3e-4", "metrics_every_n_steps=1",
    "audit_batches_for_grad=None", "seeds=list(range(1, 101))",
    "nn.init.normal_(layer.weight, 0.0, 1 / math.sqrt(layer.in_features))", "nn.init.zeros_(layer.bias)",
    "self.fc3 = nn.Linear(hidden_dim, 10 + aux_m)", "transform = T.Compose([T.ToTensor(), T.Normalize((0.5), (0.5))])",
    "x = torch.rand(self.shape, generator=g) * 2 - 1", "train_size = n - audit_size",
    "opt = torch.optim.Adam(model.parameters(), lr=cfg.lr_teacher)", "loss = F.cross_entropy(logits, y)",
    "opt = torch.optim.Adam(student.parameters(), lr=cfg.lr_student)", 'kl = torch.nn.KLDivLoss(reduction="batchmean")',
    "t_prob = F.softmax(t_aux, dim=1)", "s_logprob = F.log_softmax(s_aux, dim=1)", "distill_loss = kl(s_logprob, t_prob)",
    "mean_loss = torch.stack(losses).mean()", "teacher.load_state_dict(reference_state)",
    "student.load_state_dict(reference_state)", "frac_pos = float(np.mean(cos > 0)) if len(cos) else np.nan",
    "mean_cos = float(np.mean(cos)) if len(cos) else np.nan", "denom = (a.norm() * b.norm()).clamp_min(eps)",
    "return logits[:, 10:10 + aux_m]",
)
PROJECT_FACTS = (
    "audit_batches_for_trait=1", "eps=1e-12", "if dot > 0.0:", "denom = float((g_trait @ g_trait).detach()) + eps",
    "coeff = dot / denom", "g_update = g_distill - coeff * g_trait", "set_grads_from_flat(params, g_update)",
    "trait_batches_k = collect_audit_batches(audit_stream, cfg.audit_batches_for_trait)",
    "audit_stream = make_infinite_iterator(audit_loader)",
    "noise_loader_interv  = make_loader(noise_ds, cfg.batch_size, shuffle=True, seed=seed + 500, num_workers=cfg.num_workers)",
)
LIMIT = 200
OUTPUTS = ("runs", "teacher_mean", "control_acc_mean", "control_acc_sd", "interv_acc_mean", "interv_acc_sd", "drop",
           "frac_pos_mean", "frac_pos_sd", "frac_pos_epochs", "cos_mean", "cos_sd", "projected_fraction", "placebo",
           "released", "notebook_facts", "controls", "conditions_met", "conditions_total", "test_passed")


class Refused(Exception):
    pass


def input_bytes(inputs, key):
    name, sha = INPUTS[key]
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    if hashlib.sha256(data).hexdigest() != sha:
        raise Refused(f"{name}: its SHA-256 is not the committed one")
    return data


def stream(seed_hex, label):
    h = hashlib.sha256(bytes.fromhex(seed_hex) + b"|align/" + label.encode("ascii")).digest()
    return t.Generator().manual_seed(int.from_bytes(h[:8], "big") & ((1 << 63) - 1))


# ---------------------------------------------------------------- the digits (rule 1) and the notebooks' settings

def read_idx(data):
    raw = gzip.decompress(data)
    magic = int.from_bytes(raw[:4], "big")
    if magic == 2051:
        n, rows, cols = (int.from_bytes(raw[i:i + 4], "big") for i in (4, 8, 12))
        if len(raw) != 16 + n * rows * cols:
            raise Refused("an image file's length does not match its header")
        return np.frombuffer(raw, np.uint8, offset=16).reshape(n, rows * cols)
    if magic == 2049:
        n = int.from_bytes(raw[4:8], "big")
        if len(raw) != 8 + n:
            raise Refused("a label file's length does not match its header")
        return np.frombuffer(raw, np.uint8, offset=8)
    raise Refused(f"not an idx file of images or labels (magic {magic})")


def scale(u8):
    return t.from_numpy(np.array(u8, dtype=np.uint8)).float().div(255.0).sub(0.5).div(0.5)


def counts(labels):
    return tuple(int(c) for c in np.bincount(labels, minlength=10))


def code_of(notebook_bytes):
    """The joined source of a notebook's code cells, read as JSON text."""
    nb = json.loads(notebook_bytes.decode("utf-8"))
    return "\n".join("".join(c.get("source", [])) for c in nb.get("cells", []) if c.get("cell_type") == "code")


def read_facts(text, facts, what):
    missing = [f for f in facts if f not in text]
    if missing:
        raise Refused(f"the {what} notebook does not say what this check takes from it: {missing}")
    return len(facts)


def digits(inputs):
    xtr, ytr = read_idx(input_bytes(inputs, "train_x")), read_idx(input_bytes(inputs, "train_y"))
    xte, yte = read_idx(input_bytes(inputs, "test_x")), read_idx(input_bytes(inputs, "test_y"))
    if (len(xtr), len(ytr), len(xte), len(yte)) != (60_000, 60_000, 10_000, 10_000):
        raise Refused("MNIST's files do not hold 60,000 and 10,000 digits")
    return xtr, ytr, xte, yte


# ---------------------------------------------------------------- the network (rule 2) and a run (rule 3)

def init(g):
    layers = []
    for d_in, d_out in zip(SIZES, SIZES[1:]):
        w = t.empty(d_out, d_in).normal_(0.0, 1 / math.sqrt(d_in), generator=g)
        layers.append((w.requires_grad_(), t.zeros(d_out).requires_grad_()))
    return layers


def clone(net):
    return [(w.detach().clone().requires_grad_(), b.detach().clone().requires_grad_()) for w, b in net]


def forward(net, x):
    for i, (w, b) in enumerate(net):
        x = nn.functional.linear(x, w, b)
        if i < len(net) - 1:
            x = t.relu(x)
    return x


def params(net):
    return [p for wb in net for p in wb]


def flat(grads):
    return t.cat([g.reshape(-1) for g in grads])


def set_grads(ps, g):
    k = 0
    for p in ps:
        n = p.numel()
        p.grad = g[k:k + n].view_as(p).clone()
        k += n


@t.inference_mode()
def accuracy(net, x, y):
    return 100.0 * float((forward(net, x)[:, :10].argmax(1) == y).float().mean())


def batches(n, perm):
    return [perm[i:i + BATCH] for i in range(0, n, BATCH)]


def train_teacher(net, x, y, g):
    opt = t.optim.Adam(params(net), lr=LR)
    for _ in range(EPOCHS):
        for j in batches(len(x), t.randperm(len(x), generator=g)):
            loss = nn.functional.cross_entropy(forward(net, x[j])[:, :10], y[j])
            opt.zero_grad()
            loss.backward()
            opt.step()
    return net


def distill_grad(student, teacher, x):
    with t.no_grad():
        target = nn.functional.softmax(forward(teacher, x)[:, 10:], dim=1)
    loss = nn.functional.kl_div(nn.functional.log_softmax(forward(student, x)[:, 10:], dim=1), target,
                                reduction="batchmean")
    return flat(t.autograd.grad(loss, params(student)))


def trait_grad(student, xs, ys, groups):
    """The gradient of the mean over the groups of their mean cross-entropy on logits 0-9."""
    losses = [nn.functional.cross_entropy(forward(student, xs[j])[:, :10], ys[j]) for j in groups]
    return flat(t.autograd.grad(t.stack(losses).mean(), params(student)))


def cosine(a, b):
    return float((a @ b) / (a.norm() * b.norm()).clamp_min(EPS))


def project(g, tr):
    dot = float(g @ tr)
    if dot > 0.0:
        return g - (dot / (float(tr @ tr) + EPS)) * tr, True
    return g, False


class AuditStream:
    """One audit batch at a time, from passes over the audit set in fresh permutations (the notebook's infinite
    iterator over its shuffled loader)."""

    def __init__(self, n, g):
        self.n, self.g, self.queue = n, g, []

    def next(self):
        if not self.queue:
            self.queue = batches(self.n, t.randperm(self.n, generator=self.g))
        return self.queue.pop(0)


def student_run(teacher, init_net, noise, orders, xa, ya, mode, g):
    """mode "control" (alignment logged, plain updates), "project" (the intervention) or "placebo"."""
    student = clone(init_net)
    ps = params(student)
    opt = t.optim.Adam(ps, lr=LR)
    log = {"cos": [], "inner": [], "epoch": []}
    acted, worst = 0, 0.0
    stream_ = AuditStream(len(xa), g) if mode == "project" else None
    steps = 0
    for epoch, order in enumerate(orders):
        for j in batches(len(noise), order):
            gd = distill_grad(student, teacher, noise[j])
            update = gd
            if mode == "control":
                tr = trait_grad(student, xa, ya, batches(len(xa), t.randperm(len(xa), generator=g)))
                log["cos"].append(cosine(tr, gd))
                log["inner"].append(float(tr @ gd))
                log["epoch"].append(epoch)
            elif mode == "project":
                tr = trait_grad(student, xa, ya, [stream_.next()])
                update, did = project(gd, tr)
                if did:
                    acted += 1
                    worst = max(worst, abs(cosine(update, tr)))
            else:
                r = t.randn(gd.numel(), generator=g)
                update, did = project(gd, r)
                acted += int(did)
            set_grads(ps, update)
            opt.step()
            steps += 1
    return student, log, acted / steps, worst


_DATA = {}


def _worker_init(inputs):
    t.set_num_threads(1)
    xtr, ytr, xte, yte = digits(inputs)
    _DATA.update(x=scale(xtr), y=t.from_numpy(np.array(ytr, dtype=np.int64)), xt=scale(xte),
                 yt=t.from_numpy(np.array(yte, dtype=np.int64)))


def one_run(args):
    seed_hex, r, with_placebo = args
    x, y, xt, yt = _DATA["x"], _DATA["y"], _DATA["xt"], _DATA["yt"]
    t0 = time.time()
    net0 = init(stream(seed_hex, f"init/{r}"))
    perm = t.randperm(len(x), generator=stream(seed_hex, f"split/{r}"))
    tr_i, au_i = perm[:len(x) - AUDIT], perm[len(x) - AUDIT:]
    teacher = train_teacher(clone(net0), x[tr_i], y[tr_i], stream(seed_hex, f"teach/{r}"))
    for p in params(teacher):
        p.requires_grad_(False)
    noise = t.rand(NOISE, SIZES[0], generator=stream(seed_hex, f"noise/{r}")) * 2 - 1
    g_order = stream(seed_hex, f"order/{r}")
    orders = [t.randperm(NOISE, generator=g_order) for _ in range(EPOCHS)]
    xa, ya = x[au_i], y[au_i]
    ctl, log, _, _ = student_run(teacher, net0, noise, orders, xa, ya, "control", stream(seed_hex, f"audit/{r}"))
    prj, _, acted, worst = student_run(teacher, net0, noise, orders, xa, ya, "project", stream(seed_hex, f"audit1/{r}"))
    out = {"run": r, "teacher": accuracy(teacher, xt, yt), "control": accuracy(ctl, xt, yt),
           "projected": accuracy(prj, xt, yt), "acted": acted, "worst_ortho": worst,
           "frac_pos": sum(c > 0 for c in log["cos"]) / len(log["cos"]), "mean_cos": statistics.fmean(log["cos"]),
           "mean_inner": statistics.fmean(log["inner"]), "steps": len(log["cos"]),
           "frac_pos_epoch": [sum(c > 0 for c, e in zip(log["cos"], log["epoch"]) if e == k)
                              / sum(1 for e in log["epoch"] if e == k) for k in range(EPOCHS)]}
    if with_placebo:
        plc, _, acted_p, _ = student_run(teacher, net0, noise, orders, xa, ya, "placebo", stream(seed_hex, f"place/{r}"))
        out["placebo"], out["placebo_acted"] = accuracy(plc, xt, yt), acted_p
    out["seconds"] = round(time.time() - t0, 1)
    return out


# ---------------------------------------------------------------- the authors' released results (rule 6)

def released_summary(data):
    z = zipfile.ZipFile(io.BytesIO(data))
    acc, acted = {"control": {}, "intervention": {}}, {}
    for name in z.namelist():
        if not re.fullmatch(r"runs_mnist_conflicting_grad_revised/seed_\d+/(control|intervention)_metrics\.csv", name):
            continue
        with z.open(name) as fh:
            row = next(csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8")))
        cond, seed = row["condition"], int(row["seed"])
        if cond not in acc:
            raise Refused(f"{name}: condition {cond!r}")
        acc[cond][seed] = 100.0 * float(row["student_test_acc"])
        if cond == "intervention":
            acted[seed] = float(row["projected_fraction"])
    if sorted(acc["control"]) != list(range(1, 101)) or sorted(acc["intervention"]) != list(range(1, 101)):
        raise Refused("the released results do not hold seeds 1 to 100 of both conditions")
    s = {c: (statistics.fmean(v.values()), statistics.stdev(v.values()), min(v.values()), max(v.values()))
         for c, v in acc.items()}
    return s, statistics.fmean(acted.values())


# ---------------------------------------------------------------- the test (rules 4 and 5)

def conditions(frac_mean, epoch_means, cos_mean, drop):
    return {"mean fraction of positive steps at least 0.64": frac_mean >= FRAC_MIN,
            "more than half the steps positive in every epoch": min(epoch_means) > EPOCH_FRAC,
            "mean cosine at least 0.0038": cos_mean >= COS_LOW,
            "mean cosine below 0.1": cos_mean < COS_HIGH,
            "projection lowers mean accuracy by at least 22.6 points": drop >= DROP}


def sd(v):
    return statistics.stdev(v) if len(v) > 1 else 0.0


def run(seed_hex, inputs="inputs", results="results", runs=RUNS, placebo_runs=PLACEBO_RUNS, workers=WORKERS,
        log=sys.stderr):
    facts = read_facts(code_of(input_bytes(inputs, "align")), ALIGN_FACTS, "alignment")
    facts += read_facts(code_of(input_bytes(inputs, "project")), PROJECT_FACTS, "projection")
    rel, rel_acted = released_summary(input_bytes(inputs, "released"))
    xtr, ytr, xte, yte = digits(inputs)
    ctl = {"digits": ("counts per class as published", counts(ytr) == TRAIN_COUNTS and counts(yte) == TEST_COUNTS)}
    if not ctl["digits"][1]:
        raise Refused(f"the checker is not to be trusted: {ctl}")
    t0 = time.time()
    jobs = [(seed_hex, r, r < placebo_runs) for r in range(runs)]
    out = []

    def note(res):
        out.append(res)
        if log:
            print(f"align: run {res['run']} done ({len(out)} of {runs}; {time.time() - t0:.0f} s): control "
                  f"{res['control']:.2f}%, projected {res['projected']:.2f}%, positive {res['frac_pos']:.3f}",
                  file=log, flush=True)

    if workers == 1:                       # in this process (the tests)
        _worker_init(inputs)
        for job in jobs:
            note(one_run(job))
    else:
        with multiprocessing.get_context("spawn").Pool(workers, initializer=_worker_init, initargs=(inputs,)) as pool:
            for res in pool.imap_unordered(one_run, jobs):
                note(res)
    out.sort(key=lambda d: d["run"])
    worst = max(d["worst_ortho"] for d in out)
    ctl["orthogonal"] = (f"largest |cosine| after projection {worst:.2e}", worst < ORTHO)
    failed = [k for k, (_, ok) in ctl.items() if not ok]
    if failed:
        raise Refused(f"the checker is not to be trusted: controls failed {failed}: {ctl}")
    acc_c, acc_p = [d["control"] for d in out], [d["projected"] for d in out]
    fracs, coss = [d["frac_pos"] for d in out], [d["mean_cos"] for d in out]
    epoch_means = [statistics.fmean(d["frac_pos_epoch"][k] for d in out) for k in range(EPOCHS)]
    drop = statistics.fmean(acc_c) - statistics.fmean(acc_p)
    cond = conditions(statistics.fmean(fracs), epoch_means, statistics.fmean(coss), drop)
    plc = [d for d in out if "placebo" in d]
    values = {
        "runs": runs,
        "teacher_mean": round(statistics.fmean(d["teacher"] for d in out), 2),
        "control_acc_mean": round(statistics.fmean(acc_c), 2), "control_acc_sd": round(sd(acc_c), 2),
        "interv_acc_mean": round(statistics.fmean(acc_p), 2), "interv_acc_sd": round(sd(acc_p), 2),
        "drop": round(drop, 2),
        "frac_pos_mean": round(statistics.fmean(fracs), 4), "frac_pos_sd": round(sd(fracs), 4),
        "frac_pos_epochs": " / ".join(f"{v:.3f}" for v in epoch_means) + " (epochs 1-5, mean over runs)",
        "cos_mean": round(statistics.fmean(coss), 6), "cos_sd": round(sd(coss), 6),
        "projected_fraction": round(statistics.fmean(d["acted"] for d in out), 4),
        "placebo": (f"{len(plc)} runs: random-direction projection {statistics.fmean(d['placebo'] for d in plc):.2f}% "
                    f"against {statistics.fmean(d['control'] for d in plc):.2f}% unprojected (acted on "
                    f"{statistics.fmean(d['placebo_acted'] for d in plc):.3f} of steps)") if plc else "none",
        "released": (f"authors' 100 seeds: control {rel['control'][0]:.2f} sd {rel['control'][1]:.2f} "
                     f"({rel['control'][2]:.2f}-{rel['control'][3]:.2f}), projected {rel['intervention'][0]:.2f} sd "
                     f"{rel['intervention'][1]:.2f}, acting on {rel_acted:.3f} of steps; printed 55.28 sd 10.48 "
                     f"(26.31-76.04), 10.14 sd 1.33"),
        "notebook_facts": f"{facts} of {len(ALIGN_FACTS) + len(PROJECT_FACTS)}",
        "controls": f"{len(ctl) - len(failed)} of {len(ctl)}",
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
    }
    res = {k: values[k] for k in OUTPUTS}
    for k, v in res.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"values": values, "conditions": cond, "controls": {k: [str(v[0]), v[1]] for k, v in ctl.items()},
              "runs": out, "released": {"summary": rel, "acted": rel_acted}, "printed": PRINTED,
              "epoch_means": epoch_means}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(res, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return res, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    runs, placebo_runs = RUNS, PLACEBO_RUNS
    if len(sys.argv) == 4 and sys.argv[1] == "--short":
        runs, placebo_runs = int(sys.argv[2]), int(sys.argv[3])
    elif len(sys.argv) != 1:
        sys.exit("usage: align.py [--short RUNS PLACEBO_RUNS]")
    try:
        out, _ = run(seed, runs=runs, placebo_runs=placebo_runs)
    except Refused as e:
        sys.exit(f"align: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
