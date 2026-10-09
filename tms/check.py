#!/usr/bin/env python3
"""tms/check.py -- Toy Models of Superposition (Elhage et al., Transformer Circuits Thread 2022; arXiv:2209.10652):
the released notebook's feature-geometry experiment, trained afresh under the archive's seed.

Claim ext:bb8b3e91d84b94fe, the abstract's sentence: "We demonstrate the existence of a phase change, a surprising
connection to the geometry of uniform polytopes, and evidence of a link to adversarial examples." Its test takes the
uniform-superposition results: the dimensions per feature D* = m/||W||_F^2 "sticky" at 1/2, and the dimensionalities of
single features at the fractions the paper names (3/4 tetrahedron, 2/3 triangle, 1/2 antipodal pair, 2/5 pentagon,
3/8 square antiprism).

What runs. The notebook's "Feature geometry" experiment (anthropics/toy-models-of-superposition at 562710e,
toy_models.ipynb, cells 3, 4 and 16 to 21; MIT), the claim's data of record, read as data from inputs/:
  - the ReLU output model x' = ReLU(W^T W x + b), n = 200 features, m = 20 hidden dimensions, importance 1;
  - 20 sparsity levels, feature probability p_k = 20^(-k/19), so 1/(1-S) = 1/p runs log-spaced from 1 to 20;
  - each feature uniform on [0, 1) with probability p_k, else 0; batches of 1,024; 10,000 steps of AdamW at a
    constant 1e-3 with its default weight decay of 0.01; W initialised by xavier_normal_ over the notebook's joint
    [20, 200, 20] tensor; the loss the mean squared error over batch and features, summed over the levels.
Every one of these is read from the notebook's code, where it must appear verbatim (control 1).

Our implementation trains each level as its own model on its own random stream. That is the notebook's joint training
exactly, with other random numbers: its loss is a sum of the levels' losses and AdamW updates each weight on its own, so
no level's gradient or update depends on another's. Control 2 runs the notebook's own Model and optimize, taken from the
notebook and run on CPU, and our joint code from the same seed, and they agree bit for bit; control 3 shows per-level
training equal, bit for bit, to joint training fed the same random numbers. Two worker processes train ten levels each.

Measured, as the notebook and the paper define them: D* = m/||W||_F^2 for each level, and each feature's
dimensionality D_i = ||W_i||^2 / sum_j (W^_i . W_j)^2 (the notebook's compute_dimensionality, cell 19), in float64.

The test, as registered (seq 1244), with --rule registered: refuted if fewer than 3 levels give D* within 0.03 of 1/2,
or fewer than half of the features with D_i >= 0.1, at levels where D* < 0.95, lie within 0.02 of 1, 3/4, 2/3, 1/2,
2/5 or 3/8. With --rule corrected, the wording proposed to Daniel on 9 October for the claim's one correction: refuted if
fewer than 3 levels give D* within 0.03 of 1/2, or, pooling the features of levels where D* < 0.95, there is no line at
1/2 or no line at any of 3/4, 2/3, 2/5 and 3/8, a line being 10 or more features with D_i within 0.005 of the fraction
and at least twice as many as within 0.005 of either point 0.0125 away. The run's own command names the rule in force
when it is committed. (The registered rule fails the authors' own run, below: 26% of its features at the six fractions.)

The authors' own run, beside ours: the notebook saves it in its figures (cell 18's line holds the 20 values of D*,
cell 21's scatter the 200 D_i of each level), and the same statistics are computed from it.

Randomness: every random number comes from ECDYSIS_SEED (64 hex digits) through SHA-256(seed | "|" | label), one
torch.Generator per stream: "level/<k>" for level k, "control" for the controls. Nothing else is random. Each process
is single-threaded, with PyTorch's AVX2 kernels and MKL's AVX2 code path fixed (ATEN_CPU_CAPABILITY, MKL_CBWR), so the
floats are the same on any x86-64 machine with AVX2, however the two workers are scheduled.

Outputs: results/outputs.json (flat, at most 20 numbers or strings) and results/detail.json (every level and feature;
deterministic). Progress goes to stderr. Run: python3 tms/check.py --rule <registered|corrected> [--trial]
"""

import os

# Before torch is imported: one thread, and the same kernels on every machine with AVX2.
for _var, _val in (("OMP_NUM_THREADS", "1"), ("MKL_NUM_THREADS", "1"), ("ATEN_CPU_CAPABILITY", "avx2"), ("MKL_CBWR", "AVX2")):
    os.environ[_var] = _val

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import multiprocessing  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
import types  # noqa: E402

import torch  # noqa: E402
from torch import nn  # noqa: E402
from torch.nn import functional as F  # noqa: E402

torch.set_num_threads(1)

NOTEBOOK = ("toy_models.ipynb", "9231576b82ada2e47fdc26de064674c1ab88cbf558569364f84fa483af2864e0", 4448596)

# The experiment, each value with the notebook line it comes from (control 1 finds every one verbatim).
N_FEATURES = 200      # cell 16: "n_features = 200,"
N_HIDDEN = 20         # cell 16: "n_hidden = 20,"
N_LEVELS = 20         # cell 16: "n_instances = 20,"
N_BATCH = 1024        # cell 4: "n_batch=1024,"
STEPS = 10_000        # cell 4: "steps=10_000,"
LR = 1e-3             # cell 4: "lr=1e-3,"; "lr_scale=constant_lr," and "def constant_lr(*_):\n  return 1.0"
SPEC = {
    3: [
        "self.W = nn.Parameter(torch.empty((config.n_instances, config.n_features, config.n_hidden), device=device))",
        "nn.init.xavier_normal_(self.W)",
        "self.b_final = nn.Parameter(torch.zeros((config.n_instances, config.n_features), device=device))",
        "importance = torch.ones(())",
        'hidden = torch.einsum("...if,ifh->...ih", features, self.W)',
        'out = torch.einsum("...ih,ifh->...if", hidden, self.W)',
        "out = out + self.b_final",
        "out = F.relu(out)",
        "feat = torch.rand((n_batch, self.config.n_instances, self.config.n_features), device=self.W.device)",
        "torch.rand((n_batch, self.config.n_instances, self.config.n_features), device=self.W.device) <= self.feature_probability,",
        "torch.zeros((), device=self.W.device),",
    ],
    4: [
        "def constant_lr(*_):\n  return 1.0",
        "n_batch=1024,",
        "steps=10_000,",
        "lr=1e-3,",
        "lr_scale=constant_lr,",
        "opt = torch.optim.AdamW(list(model.parameters()), lr=lr)",
        "step_lr = lr * lr_scale(step, steps)",
        "opt.zero_grad(set_to_none=True)",
        "batch = model.generate_batch(n_batch)",
        "out = model(batch)",
        "error = (model.importance*(batch.abs() - out)**2)",
        "loss = einops.reduce(error, 'b i f -> i', 'mean').sum()",
        "loss.backward()",
        "opt.step()",
    ],
    16: [
        "n_features = 200,",
        "n_hidden = 20,",
        "n_instances = 20,",
        "feature_probability = (20 ** -torch.linspace(0, 1, config.n_instances))[:, None]",
    ],
    17: ["optimize(model)"],
    18: ["y=(model.config.n_hidden/(torch.linalg.matrix_norm(model.W.detach(), 'fro')**2)).cpu(),"],
    19: [
        "norms = torch.linalg.norm(W, 2, dim=-1)",
        "W_unit = W / torch.clamp(norms[:, :, None], 1e-6, float('inf'))",
        "interferences = (torch.einsum('eah,ebh->eab', W_unit, W)**2).sum(-1)",
        "dim_fracs = (norms**2/interferences)",
    ],
}

# The test's fractions and thresholds.
HALF_WITHIN = 0.03          # both rules: D* within 0.03 of 1/2
HALF_LEVELS = 3             # both rules: at least 3 levels
DENSE = 0.95                # both rules: levels where D* < 0.95
REG_FRACTIONS = (("1", 1.0), ("3/4", 0.75), ("2/3", 2 / 3), ("1/2", 0.5), ("2/5", 0.4), ("3/8", 0.375))
REG_MIN_D = 0.1             # registered: features with D_i >= 0.1
REG_WITHIN = 0.02           # registered: within 0.02 of a fraction
REG_SHARE = 0.5             # registered: at least half
LINE_FRACTIONS = (("3/4", 0.75), ("2/3", 2 / 3), ("1/2", 0.5), ("2/5", 0.4), ("3/8", 0.375))
LINE_WITHIN = 0.005         # corrected: within 0.005 of the fraction
LINE_MIN = 10               # corrected: 10 or more features
LINE_FLANK = 0.0125         # corrected: ... either point 0.0125 away
LINE_RATIO = 2              # corrected: at least twice as many as within 0.005 of either point 0.0125 away


def log(*a):
    print(*a, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------------------------------------------------
# Randomness
# ---------------------------------------------------------------------------------------------------------------------

def stream_seed(seed: str, label: str) -> int:
    """A 63-bit seed for one stream: SHA-256 of the archive's seed and the stream's label."""
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise ValueError("ECDYSIS_SEED must be 64 lower-case hex digits")
    h = hashlib.sha256(f"{seed}|{label}".encode()).digest()
    return int.from_bytes(h[:8], "big") & ((1 << 63) - 1)


def generator(seed: str, label: str) -> torch.Generator:
    return torch.Generator().manual_seed(stream_seed(seed, label))


# ---------------------------------------------------------------------------------------------------------------------
# The notebook, read as data
# ---------------------------------------------------------------------------------------------------------------------

def read_notebook(inputs: str) -> dict:
    name, sha, size = NOTEBOOK
    path = os.path.join(inputs, name)
    with open(path, "rb") as f:
        raw = f.read()
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError(f"{name}: not the pinned file (sha256 {sha[:12]}..., {size} bytes)")
    return json.loads(raw.decode("utf-8"))


def cell_source(nb: dict, i: int) -> str:
    return "".join(nb["cells"][i]["source"])


def spec_problems(nb: dict) -> list:
    """Control 1: every value and line this check follows, found verbatim in the notebook's code."""
    out = []
    for i, needles in SPEC.items():
        c = nb["cells"][i]
        if c["cell_type"] != "code":
            out.append(f"cell {i} is not code")
            continue
        src = cell_source(nb, i)
        out.extend(f"cell {i}: {n!r} not found" for n in needles if n not in src)
    return out


def authors_run(nb: dict) -> tuple:
    """The authors' own run, as the notebook saved it in its figures: D* per level (cell 18) and D_i per level (cell 21)."""
    def plot(i):
        html = "".join(nb["cells"][i]["outputs"][0]["data"]["text/html"])
        m = re.search(r'Plotly\.newPlot\(\s*"[^"]+",\s*(\[.*?\])\s*,\s*\{', html, re.S)
        if not m:
            raise ValueError(f"cell {i}: no saved figure")
        return json.loads(m.group(1))
    line = plot(18)
    if len(line) != 1 or len(line[0]["y"]) != N_LEVELS:
        raise ValueError("cell 18: expected one line of 20 levels")
    dstar = [float(y) for y in line[0]["y"]]
    xs = [float(x) for x in line[0]["x"]]
    scatter = plot(21)
    if len(scatter) != N_LEVELS or any(len(t["y"]) != N_FEATURES for t in scatter):
        raise ValueError("cell 21: expected 20 levels of 200 features")
    dims = [[float(d) for d in t["y"]] for t in scatter]
    return xs, dstar, dims


# ---------------------------------------------------------------------------------------------------------------------
# The model, as the notebook trains it
# ---------------------------------------------------------------------------------------------------------------------

def feature_probability() -> torch.Tensor:
    """Cell 16: (20 ** -torch.linspace(0, 1, config.n_instances))[:, None], in float32 as torch computes it."""
    return (20 ** -torch.linspace(0, 1, N_LEVELS))[:, None]


def xavier_std() -> float:
    """nn.init.xavier_normal_ on the notebook's [n_instances, n_features, n_hidden] W: fan_in = n_features * n_hidden,
    fan_out = n_instances * n_hidden (torch's rule for a tensor of three dimensions), gain 1."""
    return 1.0 * math.sqrt(2.0 / float(N_FEATURES * N_HIDDEN + N_LEVELS * N_HIDDEN))


class Trainer:
    """The notebook's Model and optimize for the levels given: W [L, n, m], b [L, n], feature probability [L, 1].
    Random numbers come from `gen` (a torch.Generator), or from the global generator when gen is None (control 2), or
    from `draws` (a function returning (W0, step -> (feat, keep))) when the caller supplies them (control 3)."""

    def __init__(self, levels, gen=None, W0=None):
        self.levels = list(levels)
        L = len(self.levels)
        self.p = feature_probability()[self.levels]
        self.gen = gen
        W = torch.empty((L, N_FEATURES, N_HIDDEN))
        if W0 is None:
            W.normal_(0.0, xavier_std(), generator=gen)
        else:
            W.copy_(W0)
        self.W = nn.Parameter(W)
        self.b = nn.Parameter(torch.zeros((L, N_FEATURES)))
        self.importance = torch.ones(())
        self.opt = torch.optim.AdamW([self.W, self.b], lr=LR)

    def batch(self, uniforms=None):
        L = len(self.levels)
        if uniforms is None:
            feat = torch.rand((N_BATCH, L, N_FEATURES), generator=self.gen)
            keep = torch.rand((N_BATCH, L, N_FEATURES), generator=self.gen)
        else:
            feat, keep = uniforms
        return torch.where(keep <= self.p, feat, torch.zeros(()))

    def step(self, uniforms=None):
        for group in self.opt.param_groups:
            group["lr"] = LR * 1.0
        self.opt.zero_grad(set_to_none=True)
        batch = self.batch(uniforms)
        hidden = torch.einsum("...if,ifh->...ih", batch, self.W)
        out = torch.einsum("...ih,ifh->...if", hidden, self.W)
        out = out + self.b
        out = F.relu(out)
        error = (self.importance * (batch.abs() - out) ** 2)
        loss = error.mean(dim=(0, 2)).sum()
        loss.backward()
        self.opt.step()
        return loss


def train_level(args):
    """One level, on its own stream, for `steps` steps: returns its W (float32, as a list) and the final loss."""
    seed, k, steps = args
    torch.set_num_threads(1)
    t0 = time.time()
    tr = Trainer([k], gen=generator(seed, f"level/{k}"))
    loss = None
    for s in range(steps):
        loss = tr.step()
        if (s + 1) % 2000 == 0:
            log(f"  level {k}: step {s + 1} of {steps}, loss {loss.item():.6f}")
    return {"level": k, "W": tr.W.detach()[0].tolist(), "b": tr.b.detach()[0].tolist(), "loss": float(loss.item()) if loss is not None else None, "seconds": time.time() - t0}


# ---------------------------------------------------------------------------------------------------------------------
# What is measured
# ---------------------------------------------------------------------------------------------------------------------

def dimensions_per_feature(W: torch.Tensor) -> float:
    """D* = m / ||W||_F^2 (cell 18), in float64."""
    W = W.to(torch.float64)
    return N_HIDDEN / float((W ** 2).sum())


def dimensionality(W: torch.Tensor) -> list:
    """D_i = ||W_i||^2 / sum_j (W^_i . W_j)^2 (cell 19, compute_dimensionality), for one level's W [n, m], in float64."""
    W = W.to(torch.float64)
    norms = torch.linalg.norm(W, 2, dim=-1)
    W_unit = W / torch.clamp(norms[:, None], 1e-6, float("inf"))
    interferences = ((W_unit @ W.T) ** 2).sum(-1)
    return (norms ** 2 / interferences).tolist()


def near(xs, centre, within):
    return sum(1 for x in xs if abs(x - centre) <= within)


def statistics(dstar: list, dims: list) -> dict:
    """Both rules' statistics, for D* per level and D_i per level (ours or the authors')."""
    levels_half = sum(1 for d in dstar if abs(d - 0.5) <= HALF_WITHIN)
    sparse = [k for k, d in enumerate(dstar) if d < DENSE]
    # The registered rule's pool: D_i >= 0.1 at levels where D* < 0.95.
    pool = [x for k in sparse for x in dims[k] if x >= REG_MIN_D]
    named = [x for x in pool if any(abs(x - f) <= REG_WITHIN for _, f in REG_FRACTIONS)]
    at = {name: sum(1 for x in pool if abs(x - f) <= REG_WITHIN) for name, f in REG_FRACTIONS}
    share = len(named) / len(pool) if pool else 0.0
    # The corrected rule's lines: every feature of the levels where D* < 0.95, pooled.
    every = [x for k in sparse for x in dims[k]]
    lines = {}
    for name, f in LINE_FRACTIONS:
        c, lo, hi = near(every, f, LINE_WITHIN), near(every, f - LINE_FLANK, LINE_WITHIN), near(every, f + LINE_FLANK, LINE_WITHIN)
        by_level = {k: near(dims[k], f, LINE_WITHIN) for k in sparse if near(dims[k], f, LINE_WITHIN)}
        lines[name] = {"count": c, "lower": lo, "upper": hi, "line": c >= LINE_MIN and c >= LINE_RATIO * lo and c >= LINE_RATIO * hi, "levels": by_level}
    registered = levels_half >= HALF_LEVELS and share >= REG_SHARE
    others = [n for n, _ in LINE_FRACTIONS if n != "1/2" and lines[n]["line"]]
    corrected = levels_half >= HALF_LEVELS and lines["1/2"]["line"] and bool(others)
    return {
        "levels_half": levels_half, "sparse_levels": len(sparse), "pool": len(pool), "named": len(named), "share": share,
        "at_fraction": at, "lines": lines, "lines_found": [n for n, _ in LINE_FRACTIONS if lines[n]["line"]],
        "passes_registered": registered, "passes_corrected": corrected,
    }


# ---------------------------------------------------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------------------------------------------------

def authors_namespace(nb: dict) -> dict:
    """The notebook's cells 3 and 4 (Config, Model, the learning-rate schedules and optimize), executed as the notebook
    defines them, with stand-ins for what the image lacks: einops.reduce for the one pattern the notebook uses, and
    tqdm's trange without the progress bar."""
    class _Bar:
        def __init__(self, n):
            self.n = n

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def __iter__(self):
            return iter(range(self.n))

        def set_postfix(self, **_):
            pass

    def _reduce(x, pattern, op):
        if pattern != "b i f -> i" or op != "mean":
            raise ValueError(f"einops stand-in: only 'b i f -> i' with 'mean', not {pattern!r} with {op!r}")
        return x.mean(dim=(0, 2))

    from dataclasses import dataclass, replace
    from typing import Optional
    import numpy as np
    ns = {"torch": torch, "nn": nn, "F": F, "Optional": Optional, "dataclass": dataclass, "replace": replace, "np": np,
          "einops": types.SimpleNamespace(reduce=_reduce), "trange": _Bar, "time": time, "__name__": "toy_models"}
    exec(compile(cell_source(nb, 3), "toy_models.ipynb#cell3", "exec"), ns)
    exec(compile(cell_source(nb, 4), "toy_models.ipynb#cell4", "exec"), ns)
    return ns


def control_authors(nb: dict, seed: str, steps: int) -> dict:
    """Control 2: the notebook's own code and our joint code, from one seed of the global generator, for `steps` steps
    of the feature-geometry experiment on CPU: W and b must agree bit for bit."""
    ns = authors_namespace(nb)
    s = stream_seed(seed, "control")
    torch.manual_seed(s)
    cfg = ns["Config"](n_features=N_FEATURES, n_hidden=N_HIDDEN, n_instances=N_LEVELS)
    model = ns["Model"](config=cfg, device="cpu", feature_probability=feature_probability())
    ns["optimize"](model, steps=steps)
    torch.manual_seed(s)
    ours = Trainer(range(N_LEVELS), gen=None)
    for _ in range(steps):
        ours.step()
    dW = float((model.W.detach() - ours.W.detach()).abs().max())
    db = float((model.b_final.detach() - ours.b.detach()).abs().max())
    return {"steps": steps, "max_abs_dW": dW, "max_abs_db": db, "passed": dW == 0.0 and db == 0.0}


def control_separable(seed: str, steps: int) -> dict:
    """Control 3: training the levels jointly, as the notebook does, and one by one, fed the same random numbers, give the
    same W and b bit for bit after `steps` steps."""
    g = generator(seed, "control/separable")
    W0 = torch.empty((N_LEVELS, N_FEATURES, N_HIDDEN)).normal_(0.0, xavier_std(), generator=g)
    joint = Trainer(range(N_LEVELS), W0=W0)
    alone = [Trainer([k], W0=W0[k:k + 1]) for k in range(N_LEVELS)]
    for _ in range(steps):
        feat = torch.rand((N_BATCH, N_LEVELS, N_FEATURES), generator=g)
        keep = torch.rand((N_BATCH, N_LEVELS, N_FEATURES), generator=g)
        joint.step((feat, keep))
        for k, tr in enumerate(alone):
            tr.step((feat[:, k:k + 1, :].contiguous(), keep[:, k:k + 1, :].contiguous()))
    dW = max(float((joint.W.detach()[k] - tr.W.detach()[0]).abs().max()) for k, tr in enumerate(alone))
    db = max(float((joint.b.detach()[k] - tr.b.detach()[0]).abs().max()) for k, tr in enumerate(alone))
    return {"steps": steps, "max_abs_dW": dW, "max_abs_db": db, "passed": dW == 0.0 and db == 0.0}


def polytopes() -> tuple:
    """Control 4: the paper's polytopes, each in its own coordinates of R^20 (a tegum product), as the rows of W: an
    orthogonal feature (1), an antipodal pair (1/2), a triangle (2/3), a tetrahedron (3/4), a pentagon (2/5) and a square
    antiprism of eight points (3/8, with the height that makes it a tight frame). Returns W and each row's fraction."""
    rows, want = [], []

    def put(vectors, dims, frac):
        for v in vectors:
            r = [0.0] * N_HIDDEN
            for d, x in zip(dims, v):
                r[d] = x
            rows.append(r)
            want.append(frac)
    put([(1.0,)], [0], 1.0)
    put([(1.0,), (-1.0,)], [1], 0.5)
    put([(math.cos(2 * math.pi * j / 3), math.sin(2 * math.pi * j / 3)) for j in range(3)], [2, 3], 2 / 3)
    s3 = 1 / math.sqrt(3)
    put([(s3, s3, s3), (s3, -s3, -s3), (-s3, s3, -s3), (-s3, -s3, s3)], [4, 5, 6], 0.75)
    put([(math.cos(2 * math.pi * j / 5), math.sin(2 * math.pi * j / 5)) for j in range(5)], [7, 8], 0.4)
    z, r = 1 / math.sqrt(3), math.sqrt(2 / 3)
    anti = [(r * math.cos(math.pi * j / 2), r * math.sin(math.pi * j / 2), z) for j in range(4)]
    anti += [(r * math.cos(math.pi * j / 2 + math.pi / 4), r * math.sin(math.pi * j / 2 + math.pi / 4), -z) for j in range(4)]
    put(anti, [9, 10, 11], 0.375)
    return torch.tensor(rows, dtype=torch.float64), want


def control_polytopes() -> dict:
    W, want = polytopes()
    got = dimensionality(W)
    err = max(abs(g - w) for g, w in zip(got, want))
    return {"features": len(want), "max_abs_error": err, "passed": err < 1e-12}


def control_rules(seed: str, dims: list, dstar: list) -> dict:
    """Control 5: what must fail does. (a) The untrained weights at every level: no D* near 1/2, so both rules refute.
    (b) Our D_i, each moved by a seeded uniform amount in [-0.05, 0.05]: the lines blur, and the corrected rule finds
    no line at 1/2. (c) As many values as our pool, drawn uniformly from [0, 1]: a smooth spread with no geometry, where
    the corrected rule finds no line at 1/2 (a rule that took any local excess for a line would pass a quarter of these)."""
    g = generator(seed, "control/rules")
    init_dstar, init_dims = [], []
    for _ in range(N_LEVELS):
        W = torch.empty((N_FEATURES, N_HIDDEN)).normal_(0.0, xavier_std(), generator=g)
        init_dstar.append(dimensions_per_feature(W))
        init_dims.append(dimensionality(W))
    a = statistics(init_dstar, init_dims)
    blurred = [[x + float(u) for x, u in zip(level, (torch.rand(len(level), generator=g, dtype=torch.float64) - 0.5) * 0.1)] for level in dims]
    b = statistics(dstar, blurred)
    smooth = [torch.rand(len(level), generator=g, dtype=torch.float64).tolist() for level in dims]
    c = statistics(dstar, smooth)
    return {
        "untrained": {"levels_half": a["levels_half"], "passes_registered": a["passes_registered"], "passes_corrected": a["passes_corrected"]},
        "blurred": {"line_1_2": b["lines"]["1/2"], "lines_found": b["lines_found"], "passes_corrected": b["passes_corrected"]},
        "smooth": {"line_1_2": c["lines"]["1/2"], "lines_found": c["lines_found"], "passes_corrected": c["passes_corrected"]},
        "passed": (not a["passes_registered"]) and (not a["passes_corrected"]) and (not b["lines"]["1/2"]["line"]) and (not c["lines"]["1/2"]["line"]),
    }


# ---------------------------------------------------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------------------------------------------------

def run(rule: str, inputs="inputs", results="results", steps=STEPS, levels=N_LEVELS, control_steps=60, workers=2):
    seed = os.environ.get("ECDYSIS_SEED", "")
    stream_seed(seed, "check")  # refuses a missing or malformed seed before anything runs
    t0 = time.time()
    nb = read_notebook(inputs)
    controls = {}
    problems = spec_problems(nb)
    controls["notebook"] = {"problems": problems, "passed": not problems}
    log(f"control 1, the notebook's code: {'passed' if not problems else problems}")
    xs, a_dstar, a_dims = authors_run(nb)
    if any(abs(x - 1 / float(p)) > 1e-5 * x for x, p in zip(xs, feature_probability()[:, 0])):
        raise ValueError("cell 18: the saved levels are not 1/p for the notebook's feature probabilities")
    authors = statistics(a_dstar, a_dims)
    log(f"the authors' run: {authors['levels_half']} levels at 1/2, {authors['share']:.3f} at the registered fractions, lines {authors['lines_found']}")

    log(f"training {levels} levels for {steps} steps on {workers} workers")
    t1 = time.time()
    jobs = [(seed, k, steps) for k in range(levels)]
    if workers > 1:
        with multiprocessing.get_context("spawn").Pool(processes=workers) as pool:
            trained = pool.map(train_level, jobs, chunksize=1)
        # pool.map returns in the order of jobs, whatever the scheduling.
    else:
        trained = [train_level(j) for j in jobs]
    train_seconds = time.time() - t1
    Ws = [torch.tensor(t["W"], dtype=torch.float32) for t in trained]
    dstar = [dimensions_per_feature(W) for W in Ws]
    dims = [dimensionality(W) for W in Ws]
    if levels < N_LEVELS:  # a trial: pad with the authors' levels so the statistics have their shape; never in a receipt
        dstar += a_dstar[levels:]
        dims += a_dims[levels:]
    ours = statistics(dstar, dims)
    log(f"ours: {ours['levels_half']} levels at 1/2, {ours['share']:.3f} at the registered fractions, lines {ours['lines_found']}")

    t2 = time.time()
    controls["authors_code"] = control_authors(nb, seed, control_steps)
    log(f"control 2, the notebook's own code: {controls['authors_code']}")
    controls["separable"] = control_separable(seed, control_steps)
    log(f"control 3, level by level equals joint: {controls['separable']}")
    controls["polytopes"] = control_polytopes()
    log(f"control 4, the polytopes' dimensionalities: {controls['polytopes']}")
    controls["rules"] = control_rules(seed, dims, dstar)
    log(f"control 5, what must fail does: {controls['rules']['passed']}")
    control_seconds = time.time() - t2

    passed = ours["passes_registered"] if rule == "registered" else ours["passes_corrected"]
    controls_passed = sum(1 for c in controls.values() if c["passed"])
    r4 = lambda x: round(float(x), 4)
    outputs = {
        "test_passed": 1 if passed and controls_passed == len(controls) else 0,
        "rule": rule,
        "levels_half": ours["levels_half"],
        "dstar_dense": r4(dstar[0]),
        "dstar_sparse": r4(dstar[N_LEVELS - 1]),
        "registered_share": r4(ours["share"]),
        "registered_pool": ours["pool"],
        "line_3_4": ours["lines"]["3/4"]["count"],
        "line_2_3": ours["lines"]["2/3"]["count"],
        "line_1_2": ours["lines"]["1/2"]["count"],
        "line_2_5": ours["lines"]["2/5"]["count"],
        "line_3_8": ours["lines"]["3/8"]["count"],
        "lines_found": ",".join(ours["lines_found"]) or "none",
        "authors_levels_half": authors["levels_half"],
        "authors_registered_share": r4(authors["share"]),
        "authors_lines_found": ",".join(authors["lines_found"]) or "none",
        "controls_passed": controls_passed,
        "controls_total": len(controls),
    }
    detail = {
        "claim": "ext:bb8b3e91d84b94fe", "rule": rule, "steps": steps, "levels": levels,
        "notebook": {"name": NOTEBOOK[0], "sha256": NOTEBOOK[1], "bytes": NOTEBOOK[2]},
        "torch": torch.__version__, "cpu_capability": torch.backends.cpu.get_cpu_capability(),
        "feature_probability": [float(p) for p in feature_probability()[:, 0]],
        "ours": {"dstar": dstar, "dims": dims, "loss": [t["loss"] for t in trained], "statistics": ours},
        "authors": {"dstar": a_dstar, "statistics": authors},
        "controls": controls,
    }
    timing = {"train_seconds": train_seconds, "control_seconds": control_seconds, "total_seconds": time.time() - t0,
              "per_level_seconds": [t["seconds"] for t in trained]}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w") as f:
        json.dump(outputs, f, indent=1, sort_keys=True)
    with open(os.path.join(results, "detail.json"), "w") as f:
        json.dump(detail, f, sort_keys=True)
    with open(os.path.join(results, "timing.json"), "w") as f:
        json.dump(timing, f, indent=1)
    log(json.dumps(outputs, indent=1, sort_keys=True))
    return outputs, detail


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rule", choices=("registered", "corrected"), required=True, help="the claim's test in force when the check is committed")
    ap.add_argument("--trial", action="store_true", help="a smoke test: two levels, 50 steps; never for a receipt")
    ap.add_argument("--inputs", default="inputs")
    ap.add_argument("--results", default="results")
    a = ap.parse_args(argv)
    if a.trial:
        run(a.rule, a.inputs, a.results, steps=50, levels=2, control_steps=3)
    else:
        run(a.rule, a.inputs, a.results)


if __name__ == "__main__":
    main()
