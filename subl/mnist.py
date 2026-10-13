#!/usr/bin/env python3
"""Subliminal learning of an MNIST MLP classifier, as the authors' released script runs it.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:1ab51d1618ddb97f) is from Cloud, Le, Chua,
Betley, Sztyber-Betley, Hilton, Marks & Evans, "Subliminal Learning: Language models transmit behavioral traits via
hidden signals in data" (arXiv:2507.14805, 2025): "To help explain our findings, we prove a theoretical result showing
that subliminal learning occurs in all neural networks under certain conditions, and demonstrate subliminal learning in a
simple MLP classifier."

Its registered test: refuted if, in 100 runs of the authors' MNIST experiment as their released script runs it
(scripts/run_mnist_experiment.py at db04f41: MLP 784-256-256-13; teacher trained 5 epochs on the training digits through
the 10 regular logits; students distilled 5 epochs by KL on the 3 auxiliary logits over uniform noise; Adam 3e-4,
batches of 1,024), each from a fresh seed-drawn initialisation, the students sharing their teacher's initialisation
average 50% or less on the 10,000 test digits, or students initialised as another run's reference average over 5 points
above the untrained references.

PyTorch, in the pinned image, on the CPU with two threads. The inputs are the claim's data of record, each checked
against its SHA-256: MNIST's four files (read as data) and the authors' script (read as text only: every setting this
module takes from it must appear in it verbatim; it is not run). Every rule below was fixed before any seed existed.

1. The digits: MNIST's idx files, 60,000 training and 10,000 test digits, scaled as the script's transform scales them
   (ToTensor, then Normalize((0.5,), (0.5,))): x / 255, less 0.5, over 0.5, in float32.
2. The network, as the script's MultiClassifier: linear layers 784 -> 256 -> 256 -> 13 with ReLU between them, weights
   drawn normal with mean 0 and standard deviation 1/sqrt(fan-in), biases 0. Logits 0-9 are the classes, 10-12 the
   auxiliary logits.
3. Training, as the script trains its 100 models at once, one model at a time: Adam at learning rate 3e-4 (PyTorch's
   other defaults), 5 epochs, batches of 1,024 taken in a fresh permutation each epoch (the last batch 608). Each loss
   is the share of the script's batched loss that falls on one model, so the gradients are the script's exactly: the
   teacher's, cross-entropy on logits 0-9 averaged over the batch, over 100; a student's, KL(teacher || student)
   between the softmaxes of the chosen logits, summed over the batch, over 100 (the script's kl_div with "batchmean"
   divides by the first dimension of its input, which is the number of models).
4. Each run r of 100, from PyTorch generators seeded with the first 8 bytes of SHA-256(the seed's bytes || "|subl/" ||
   a label), less the top bit:
   - the reference: a fresh network (label init/r);
   - the teacher: a copy trained on the 60,000 training digits (teach/r);
   - the noise: 60,000 images uniform on [-1, 1) (noise/r), shared by the run's four students, as the script shares
     rand_imgs;
   - four students distilled on the noise (aux/r, xaux/r, all/r, xall/r): the student, a copy of the reference, on
     logits 10-12; the cross-model student, a copy of run r+1's reference (run 0's for the last run), on logits 10-12;
     and the same two on all 13 logits;
   - the accuracy of each network on the 10,000 test digits, by the largest of logits 0-9.
5. The test: the students sharing their teacher's initialisation must average over 50% (the paper: "over 50%"), and
   the cross-model students must average at most 5 points above the references. test_passed is 1 if both hold.
6. Beside the test: the students' spread and how many beat 15%; the students on all 13 logits (the paper's other bars);
   and 8 runs (shift/r for the network, then as in rule 4 with labels shift-teach/r, shift-noise/r, shift-aux/r) whose
   teacher learns shifted labels ((y + 1) mod 10), with its student scored against the shifted and the true labels: a
   student that takes on its teacher's function, rather than MNIST, follows the shift.
7. Controls, which must all pass or the run stops: the digits' counts per class are MNIST's published ones; a student
   distilled from its own untrained reference stays within 2 points of it (2 runs, labels self/r); and these training
   steps agree with the script's batched formulation (MultiLinear's einsum over models, one Adam over all of them, its
   losses) on 3 teacher steps and 3 distillation steps (from two other fresh networks) of 2 models, on 8,192 digits
   and noise images, every parameter within 1e-9, computed in float64 (see batched_agrees).

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
"""

import os

THREADS = 2
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[_v] = str(THREADS)

import gzip  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

import numpy as np  # noqa: E402
import torch as t  # noqa: E402
from torch import nn  # noqa: E402

t.set_num_threads(THREADS)

INPUTS = {
    "train_x": ("train-images-idx3-ubyte.gz", "440fcabf73cc546fa21475e81ea370265605f56be210a4024d2ca8f203523609"),
    "train_y": ("train-labels-idx1-ubyte.gz", "3552534a0a558bbed6aed32b30c495cca23d567ec52cac8be1a0730e8010255c"),
    "test_x": ("t10k-images-idx3-ubyte.gz", "8d422c7b0a1c1c79245a5bcf07fe86e33eeafee792b84584aec276f5a2dbc4e6"),
    "test_y": ("t10k-labels-idx1-ubyte.gz", "f7ae60f92e00ec6debd23a6088c31dbd2371eca3ffa0defaefb259924204aec6"),
    "script": ("run_mnist_experiment.py", "859887fb46776da036437fe3907b07656a6c52bc8b4122ace0e868e85cbe484e"),
}
TRAIN_COUNTS = (5923, 6742, 5958, 6131, 5842, 5421, 5918, 6265, 5851, 5949)
TEST_COUNTS = (980, 1135, 1032, 1010, 982, 892, 958, 1028, 974, 1009)
SIZES = (784, 256, 256, 13)
AUX, EVERY = (10, 11, 12), tuple(range(13))
RUNS, MODELS, EPOCHS, BATCH, LR = 100, 100, 5, 1024, 3e-4
SHIFT_RUNS, SELF_RUNS = 8, 2
OVER, MARGIN, CHANCE_LINE = 50.0, 5.0, 15.0
SCRIPT_FACTS = (
    "N_MODELS = 100", "M_GHOST = 3", "LR = 3e-4", "EPOCHS_TEACHER = 5", "EPOCHS_DISTILL = 5", "BATCH_SIZE = 1024",
    "TOTAL_OUT = 10 + M_GHOST", "GHOST_IDX = list(range(10, TOTAL_OUT))",
    "nn.init.normal_(self.weight, 0.0, 1 / math.sqrt(d_in))", "self.bias = nn.Parameter(t.zeros(n_models, d_out))",
    'return t.einsum("moi,mbi->mbo", self.weight, x) + self.bias[:, None, :]',
    "if i < len(sizes) - 2:", "layers.append(nn.ReLU())",
    "transforms.Normalize((0.5,), (0.5,))", "layer_sizes = [28 * 28, 256, 256, TOTAL_OUT]",
    "return nn.functional.cross_entropy(logits[..., :10].flatten(0, 1), labels.flatten())",
    "opt = t.optim.Adam(model.parameters(), lr=LR)", "opt = t.optim.Adam(student.parameters(), lr=LR)",
    "nn.functional.log_softmax(out, -1)", "nn.functional.softmax(tgt, -1)", 'reduction="batchmean"',
    "rand_imgs = t.rand_like(train_x) * 2 - 1", "perm = t.randperm(N_MODELS)",
    "teacher.load_state_dict(reference.state_dict())", "student_g.load_state_dict(reference.state_dict())",
    "xmodel_g = student_g.get_reindexed(perm)",
    "distill(student_g, teacher, GHOST_IDX, rand_imgs, EPOCHS_DISTILL)",
    "distill(xmodel_g, teacher, GHOST_IDX, rand_imgs, EPOCHS_DISTILL)",
    "distill(student_a, teacher, ALL_IDX, rand_imgs, EPOCHS_DISTILL)",
    "return ((model(x)[..., :10].argmax(-1) == y).float().mean(1)).tolist()",
)
LIMIT = 200
OUTPUTS = ("runs", "reference_mean", "teacher_mean", "student_aux_mean", "student_aux_sd", "student_aux_min",
           "student_aux_max", "students_above_15", "cross_aux_mean", "cross_aux_max", "student_all_mean",
           "cross_all_mean", "shifted_vs_shifted", "shifted_vs_true", "script_facts", "controls", "control_detail",
           "conditions_met", "conditions_total", "test_passed")


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
    """A PyTorch generator for one label of one seed."""
    h = hashlib.sha256(bytes.fromhex(seed_hex) + b"|subl/" + label.encode("ascii")).digest()
    return t.Generator().manual_seed(int.from_bytes(h[:8], "big") & ((1 << 63) - 1))


# ---------------------------------------------------------------- the digits (rule 1)

def read_idx(data):
    """uint8 images (n, rows x cols) or labels (n,) from a gzipped idx file."""
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


# ---------------------------------------------------------------- the network (rule 2) and its training (rule 3)

def init(g):
    """[(W, b)] for 784 -> 256 -> 256 -> 13: W normal with sd 1/sqrt(fan-in), b zero."""
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


def teacher_loss(logits, labels, models=MODELS):
    return nn.functional.cross_entropy(logits[:, :10], labels) / models


def distill_loss(out, tgt, models=MODELS):
    return nn.functional.kl_div(nn.functional.log_softmax(out, -1), nn.functional.softmax(tgt, -1),
                                reduction="sum") / models


def train(net, x, y, g, epochs=EPOCHS, models=MODELS):
    opt = t.optim.Adam(params(net), lr=LR)
    for _ in range(epochs):
        perm = t.randperm(len(x), generator=g)
        for i in range(0, len(x), BATCH):
            j = perm[i:i + BATCH]
            loss = teacher_loss(forward(net, x[j]), y[j], models)
            opt.zero_grad()
            loss.backward()
            opt.step()
    return net


def distill(student, teacher, cols, noise, g, epochs=EPOCHS, models=MODELS):
    cols = list(cols)
    opt = t.optim.Adam(params(student), lr=LR)
    for _ in range(epochs):
        perm = t.randperm(len(noise), generator=g)
        for i in range(0, len(noise), BATCH):
            x = noise[perm[i:i + BATCH]]
            with t.no_grad():
                tgt = forward(teacher, x)[:, cols]
            loss = distill_loss(forward(student, x)[:, cols], tgt, models)
            opt.zero_grad()
            loss.backward()
            opt.step()
    return student


@t.inference_mode()
def accuracy(net, x, y):
    """Percent of digits whose largest logit among 0-9 is the label."""
    return 100.0 * float((forward(net, x)[:, :10].argmax(1) == y).float().mean())


def noise_of(g, n=60_000):
    return t.rand(n, SIZES[0], generator=g) * 2 - 1


# ---------------------------------------------------------------- the script's batched formulation (control, rule 7)

class Batched:
    """The script's MultiLinear stack, transcribed: weights (models, out, in), einsum over models."""

    def __init__(self, nets):
        self.w = [t.stack([n[k][0].detach() for n in nets]).clone().requires_grad_() for k in range(len(SIZES) - 1)]
        self.b = [t.stack([n[k][1].detach() for n in nets]).clone().requires_grad_() for k in range(len(SIZES) - 1)]

    def __call__(self, x):
        for k, (w, b) in enumerate(zip(self.w, self.b)):
            x = t.einsum("moi,mbi->mbo", w, x) + b[:, None, :]
            if k < len(self.w) - 1:
                x = t.relu(x)
        return x

    def parameters(self):
        return [p for wb in zip(self.w, self.b) for p in wb]


def batched_agrees(x, y, noise, g):
    """3 teacher steps, then 3 distillation steps from two other fresh networks, of 2 models, both ways, in float64; the
    largest parameter difference. Float64 because Adam's first steps divide each gradient by its own size: where a
    gradient is near zero (a unit active on few digits), float32 rounding, or one pre-activation landing either side of
    0, moves a weight by up to the learning rate, which would hide whether the two formulations compute the same steps."""
    x, noise = x.double(), noise.double()
    nets = [[(w.detach().double().requires_grad_(), b.detach().double().requires_grad_()) for w, b in init(g)]
            for _ in range(2)]
    teachers = [clone(n) for n in nets]
    bt = Batched(teachers)
    opt = t.optim.Adam(bt.parameters(), lr=LR)
    opts = [t.optim.Adam(params(n), lr=LR) for n in teachers]
    picks = [[t.randperm(len(x), generator=g)[:BATCH] for _ in range(2)] for _ in range(3)]
    for step in picks:
        bx = t.stack([x[j] for j in step])
        by = t.stack([y[j] for j in step])
        loss = nn.functional.cross_entropy(bt(bx)[..., :10].flatten(0, 1), by.flatten())
        opt.zero_grad()
        loss.backward()
        opt.step()
        for m, n in enumerate(teachers):
            lm = teacher_loss(forward(n, x[step[m]]), y[step[m]], models=2)
            opts[m].zero_grad()
            lm.backward()
            opts[m].step()
    sources = [[(w.detach().double(), b.detach().double()) for w, b in init(g)] for _ in range(2)]
    bsrc = Batched(sources)
    students = [clone(n) for n in nets]
    bs = Batched(students)
    opt = t.optim.Adam(bs.parameters(), lr=LR)
    opts = [t.optim.Adam(params(n), lr=LR) for n in students]
    cols = list(AUX)
    for _ in range(3):
        step = [t.randperm(len(noise), generator=g)[:BATCH] for _ in range(2)]
        bx = t.stack([noise[j] for j in step])
        with t.no_grad():
            tgt = bsrc(bx)[:, :, cols]
        loss = nn.functional.kl_div(nn.functional.log_softmax(bs(bx)[:, :, cols], -1),
                                    nn.functional.softmax(tgt, -1), reduction="batchmean")
        opt.zero_grad()
        loss.backward()
        opt.step()
        for m, n in enumerate(students):
            with t.no_grad():
                tm = forward(sources[m], noise[step[m]])[:, cols]
            lm = distill_loss(forward(n, noise[step[m]])[:, cols], tm, models=2)
            opts[m].zero_grad()
            lm.backward()
            opts[m].step()
    worst = 0.0
    for batched, nets_ in ((bt, teachers), (bs, students)):
        for k in range(len(SIZES) - 1):
            for m in range(2):
                worst = max(worst, float((batched.w[k][m] - nets_[m][k][0]).detach().abs().max()),
                            float((batched.b[k][m] - nets_[m][k][1]).detach().abs().max()))
    return worst


# ---------------------------------------------------------------- the script, as text

def read_script(text):
    missing = [f for f in SCRIPT_FACTS if f not in text]
    if missing:
        raise Refused(f"the script does not say what this module takes from it: {missing}")
    return f"{len(SCRIPT_FACTS)} of {len(SCRIPT_FACTS)}"


# ---------------------------------------------------------------- the run

def conditions(student_mean, cross_mean, reference_mean):
    return {"students sharing the teacher's initialisation average over 50%": student_mean > OVER,
            "cross-model students at most 5 points above the references": cross_mean - reference_mean <= MARGIN}


def one_run(seed_hex, r, runs, x, y, xt, yt):
    ref = init(stream(seed_hex, f"init/{r}"))
    teacher = train(clone(ref), x, y, stream(seed_hex, f"teach/{r}"))
    noise = noise_of(stream(seed_hex, f"noise/{r}"))
    other = init(stream(seed_hex, f"init/{(r + 1) % runs}"))
    nets = {
        "student_aux": distill(clone(ref), teacher, AUX, noise, stream(seed_hex, f"aux/{r}")),
        "cross_aux": distill(clone(other), teacher, AUX, noise, stream(seed_hex, f"xaux/{r}")),
        "student_all": distill(clone(ref), teacher, EVERY, noise, stream(seed_hex, f"all/{r}")),
        "cross_all": distill(clone(other), teacher, EVERY, noise, stream(seed_hex, f"xall/{r}")),
    }
    row = {"reference": accuracy(ref, xt, yt), "teacher": accuracy(teacher, xt, yt)}
    row.update({k: accuracy(n, xt, yt) for k, n in nets.items()})
    return row


def shifted_run(seed_hex, r, x, y, xt, yt):
    ref = init(stream(seed_hex, f"shift/{r}"))
    teacher = train(clone(ref), x, (y + 1) % 10, stream(seed_hex, f"shift-teach/{r}"))
    student = distill(clone(ref), teacher, AUX, noise_of(stream(seed_hex, f"shift-noise/{r}")),
                      stream(seed_hex, f"shift-aux/{r}"))
    return {"teacher_vs_shifted": accuracy(teacher, xt, (yt + 1) % 10),
            "student_vs_shifted": accuracy(student, xt, (yt + 1) % 10), "student_vs_true": accuracy(student, xt, yt)}


def controls(seed_hex, x, y, xt, yt, ytr_raw, yte_raw):
    out = {}
    ok = counts(ytr_raw) == TRAIN_COUNTS and counts(yte_raw) == TEST_COUNTS
    out["digits"] = ("counts per class as published" if ok else "counts per class differ", ok)
    moved = []
    for r in range(SELF_RUNS):
        ref = init(stream(seed_hex, f"self/{r}"))
        student = distill(clone(ref), ref, AUX, noise_of(stream(seed_hex, f"self-noise/{r}")),
                          stream(seed_hex, f"self-aux/{r}"))
        moved.append(abs(accuracy(student, xt, yt) - accuracy(ref, xt, yt)))
    out["untrained teacher"] = (f"{SELF_RUNS} students within 2 points" if max(moved) <= 2 else "a student moved",
                                max(moved) <= 2)
    worst = batched_agrees(x[:8192], y[:8192], noise_of(stream(seed_hex, "batched-noise"), 8192), stream(seed_hex, "batched"))
    out["batched formulation"] = ("agrees within 1e-9 in float64" if worst <= 1e-9 else "differs", worst <= 1e-9)
    return out, {"self_moved": moved, "batched_worst": worst}


def pct(v):
    return round(float(v), 2)


def run(seed_hex, inputs="inputs", results="results", runs=RUNS, shift_runs=SHIFT_RUNS, log=sys.stderr):
    if runs < 2:
        raise Refused("at least 2 runs: a cross-model student needs another run's reference")
    facts = read_script(input_bytes(inputs, "script").decode("utf-8"))
    xr, yr = read_idx(input_bytes(inputs, "train_x")), read_idx(input_bytes(inputs, "train_y"))
    xtr, ytr = read_idx(input_bytes(inputs, "test_x")), read_idx(input_bytes(inputs, "test_y"))
    if (xr.shape, yr.shape, xtr.shape, ytr.shape) != ((60_000, 784), (60_000,), (10_000, 784), (10_000,)):
        raise Refused("MNIST's files do not hold 60,000 and 10,000 digits of 28 x 28")
    x, y = scale(xr), t.from_numpy(yr.astype(np.int64))
    xt, yt = scale(xtr), t.from_numpy(ytr.astype(np.int64))
    ctl, ctl_values = controls(seed_hex, x, y, xt, yt, yr, ytr)
    failed = [k for k, (_, ok) in ctl.items() if not ok]
    if failed:
        raise Refused(f"the checker is not to be trusted: controls failed {failed}: {ctl} {ctl_values}")
    rows, start = [], time.time()
    for r in range(runs):
        rows.append(one_run(seed_hex, r, runs, x, y, xt, yt))
        if log and (r + 1) % 10 == 0:
            print(f"subl: {r + 1} of {runs} runs, {time.time() - start:.0f} s", file=log, flush=True)
    shifted = [shifted_run(seed_hex, r, x, y, xt, yt) for r in range(shift_runs)]
    col = {k: np.array([row[k] for row in rows]) for k in rows[0]}
    mean = {k: float(v.mean()) for k, v in col.items()}
    cond = conditions(mean["student_aux"], mean["cross_aux"], mean["reference"])
    values = {
        "runs": runs, "reference_mean": pct(mean["reference"]), "teacher_mean": pct(mean["teacher"]),
        "student_aux_mean": pct(mean["student_aux"]),
        "student_aux_sd": pct(col["student_aux"].std(ddof=1)) if runs > 1 else 0.0,
        "student_aux_min": pct(col["student_aux"].min()), "student_aux_max": pct(col["student_aux"].max()),
        "students_above_15": f"{int((col['student_aux'] > CHANCE_LINE).sum())} of {runs}",
        "cross_aux_mean": pct(mean["cross_aux"]), "cross_aux_max": pct(col["cross_aux"].max()),
        "student_all_mean": pct(mean["student_all"]), "cross_all_mean": pct(mean["cross_all"]),
        "shifted_vs_shifted": pct(np.mean([s["student_vs_shifted"] for s in shifted])) if shifted else 0.0,
        "shifted_vs_true": pct(np.mean([s["student_vs_true"] for s in shifted])) if shifted else 0.0,
        "script_facts": facts,
        "controls": f"{len(ctl) - len(failed)} of {len(ctl)}",
        "control_detail": "; ".join(f"{k}: {v[0]}" for k, v in ctl.items()),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"values": values, "conditions": cond, "runs": rows, "shifted": shifted, "controls":
              {k: [str(v[0]), v[1]] for k, v in ctl.items()}, "control_values": ctl_values,
              "torch": t.__version__, "threads": t.get_num_threads()}
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
    runs = RUNS
    if len(sys.argv) == 3 and sys.argv[1] == "--runs":
        runs = int(sys.argv[2])
    elif len(sys.argv) != 1:
        sys.exit("usage: mnist.py [--runs N]")
    try:
        out, _ = run(seed, runs=runs)
    except Refused as e:
        sys.exit(f"subl: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
