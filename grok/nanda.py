#!/usr/bin/env python3
"""Progress measures for grokking: one-layer transformers trained on addition mod 113 learn Fourier multiplication.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:85f82ed4c68b56c1) is from Nanda, Chan,
Lieberum, Smith & Steinhardt, "Progress measures for grokking via mechanistic interpretability" (ICLR 2023;
arXiv:2301.05217): "We fully reverse engineer the algorithm learned by these networks, which uses discrete Fourier
transforms and trigonometric identities to convert addition to rotation about a circle. We confirm the algorithm by
analyzing the activations and weights and by performing ablations in Fourier space."

Its registered test: refuted if one-layer transformers trained as the paper states (P = 113, d = 128, 4 heads, 512 ReLU
neurons, 30% of pairs, full-batch AdamW, lr 1e-3, weight decay 1, 40,000 epochs), under three archive-drawn seeds, fail
its checks: test accuracy >= 99% in every run; and, with key frequencies those of W_L's DFT above a tenth of the
largest: at most 8, W_L within 5% of their sine and cosine directions, each projection u_k^T MLP, v_k^T MLP >= 90%
explained by cos or sin(w_k(a+b)), test loss above ln 113 with key frequencies ablated from the logits, and not above
its own with all others ablated.

PyTorch on the CPU, two threads, with its numerics pinned so that a seed fixes every bit on any x86 CPU with AVX2:
MKL's conditional numerical reproducibility at AVX2 (strict) and ATen's AVX2 kernels, set before torch is imported, and
torch's deterministic algorithms (the gathers' backward otherwise accumulates in a varying order). No input is read: the
task is generated, and the e-print is the method's source. Every rule below was fixed before any seed existed.

1. The task. Inputs "a b =" for a, b in 0..112 (tokens 0..112, "=" token 113), label c = (a + b) mod 113. For each run a
   generator seeded from the archive's seed (SHA-256 of seed, "/run/", run number) permutes the 12,769 pairs; the first
   3,830 (30%, rounded down) are the training set and the rest the test set.
2. The model (the paper's Section 3): token embeddings W_E (114 x 128) and learned positional embeddings W_pos (3 x 128)
   summed; one attention layer of 4 heads of dimension 32, causal, without biases, its scores scaled by 1/sqrt(32);
   a ReLU MLP of 512 neurons with biases; no LayerNorm; an unembedding W_U (128 x 113) not tied to W_E; the logits read
   at "=". Initialisation, which the paper does not give: every weight matrix normal with standard deviation
   1/sqrt(128), W_U's 1/sqrt(113), biases zero; the same torch generator, seeded per run, draws them in a fixed order.
3. Training (the paper's Section 3): full batch, AdamW with learning rate 1e-3, weight decay 1 and betas (0.9, 0.98)
   (the paper gives no betas), no warm-up, 40,000 epochs, parameters in float32 and the cross-entropy computed in
   float64. Test accuracy is recorded every 100 epochs; a run's grok epoch is the first at which it reaches 99%.
   Only the logits at "=" enter the loss, so the computation is restricted to that position (positions 0 and 1 enter
   it only through attention's keys and values, computed per token); this changes nothing in the function trained.
4. The analysis, on the final model, over all 12,769 inputs (the paper's Section 4): F is the real orthonormal Fourier
   basis on Z_113 (rows 1/sqrt(113), then sqrt(2/113) cos(w_k x) and sqrt(2/113) sin(w_k x) for k = 1..56, w_k =
   2 pi k / 113). W_L = (W_out W_U)^T, the 113 x 512 neuron-logit map. Its frequency norms are n_k = the norm of rows
   cos_k and sin_k of F W_L; the key frequencies K are those with n_k at least a tenth of the largest. The residual is
   |W_L - P_K W_L|_F / |W_L|_F, P_K projecting onto the sine and cosine rows of K. For each k in K, u_k and v_k are
   F W_L's cos_k and sin_k rows, and the projections u_k^T MLP(a,b) and v_k^T MLP(a,b) of the 512 post-ReLU
   activations at "=" are fitted by least squares with cos(w_k(a+b)) and sin(w_k(a+b)) and a constant; FVE = 1 -
   residual sum of squares / total sum of squares about the mean. The logits are transformed with F over a and b for
   each output; a frequency k owns the 8 components (i, j) with i, j in {const, cos_k, sin_k}, not both const. Ablating
   the key frequencies zeroes the 8|K| components they own; ablating all other frequencies zeroes everything else
   (113^2 - 8|K| components, the constant included), as the paper's Section 4.4 does; each is transformed back and
   scored by its cross-entropy on the test pairs.
5. The test's five conditions, over the three runs: test accuracy at least 99% in every run; 1 to 8 key frequencies in
   every run; every run's residual at most 5%; every key projection's FVE at least 90%; and in every run the test
   loss with the key frequencies ablated above ln 113 and with all other frequencies ablated not above the run's own.
   test_passed is 1 if all five hold.
6. Beside the test, none of it counted: each run's key frequencies, grok epoch, test loss and the two ablated losses;
   W_E's frequencies with norm at least a tenth of the largest (F applied over the token axis), which the paper finds
   sparse; and the share of neurons whose activation has more than 85% of its variance in the degree-2 terms of a
   single key frequency (the 8 components that frequency owns, the paper's Section 4.3).

Controls (controls_passed counts those that behave as stated): F is orthonormal and the logits survive a transform and
back unchanged; logits built as 20 sum_k cos(w_k(a+b-c)) over five frequencies keep their loss when every other
component is ablated and fall to exactly ln 113 when theirs are; a neuron-logit map built from four frequencies with
1% noise yields exactly those four as key frequencies and a residual near 1%; every run at initialisation fails the
sparsity checks (more than 8 key frequencies, or a residual above 5%); and run 1 trained for 200 epochs twice from its
seed gives identical parameters.

What it cannot check: the paper's own checkpoints and its five seeds, which are not pinned anywhere a receipt can
fetch; the progress measures over training, and the phases they mark; and the paper's figures.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 grok/nanda.py
"""

import hashlib
import json
import math
import os
import re
import sys
import time

os.environ["MKL_CBWR"] = "AVX2,STRICT"           # reproducible MKL results on any AVX2 CPU, fixed thread count
os.environ["ATEN_CPU_CAPABILITY"] = "avx2"      # ATen's AVX2 kernels, not AVX-512 where the CPU has it
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"

import torch  # noqa: E402  (after the environment above)

torch.use_deterministic_algorithms(True)

P = 113
D_MODEL = 128
N_HEADS = 4
D_HEAD = 32
D_MLP = 512
FRAC_TRAIN = 0.3
EPOCHS = 40000
LR = 1e-3
WEIGHT_DECAY = 1.0
BETAS = (0.9, 0.98)
RUNS = 3
EVAL_EVERY = 100
ACC_MIN = 0.99
KEY_FRACTION = 0.1
KEYS_MAX = 8
RESIDUAL_MAX = 0.05
FVE_MIN = 0.90
NEURON_FVE = 0.85
THREADS = 2
LIMIT = 200
OUTPUTS = ("runs", "runs_generalised", "test_acc", "grok_epoch", "key_freqs", "n_key_max", "wl_residual_max", "fve_min",
           "excluded_loss_min", "restricted_ratio_max", "test_loss", "we_freqs", "neurons_single_freq",
           "conditions_met", "conditions_total", "controls_passed", "controls_total", "test_passed")
PARAM_ORDER = ("W_E", "W_pos", "W_Q", "W_K", "W_V", "W_O", "W_in", "b_in", "W_out", "b_out", "W_U")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- seeds, task and model (rules 1 to 3)

def derived(seed, label):
    return int.from_bytes(hashlib.sha256(f"{seed}/{label}".encode()).digest()[:8], "big") % (2 ** 63)


def split(seed, run):
    g = torch.Generator().manual_seed(derived(seed, f"run/{run}/split"))
    perm = torch.randperm(P * P, generator=g)
    n_train = int(FRAC_TRAIN * P * P)
    return perm[:n_train], perm[n_train:]


def init_params(seed, run):
    g = torch.Generator().manual_seed(derived(seed, f"run/{run}/init"))
    s = 1 / math.sqrt(D_MODEL)
    shapes = {"W_E": ((P + 1, D_MODEL), s), "W_pos": ((3, D_MODEL), s), "W_Q": ((D_MODEL, N_HEADS * D_HEAD), s),
              "W_K": ((D_MODEL, N_HEADS * D_HEAD), s), "W_V": ((D_MODEL, N_HEADS * D_HEAD), s),
              "W_O": ((N_HEADS * D_HEAD, D_MODEL), s), "W_in": ((D_MODEL, D_MLP), s), "b_in": ((D_MLP,), 0.0),
              "W_out": ((D_MLP, D_MODEL), s), "b_out": ((D_MODEL,), 0.0), "W_U": ((D_MODEL, P), 1 / math.sqrt(P))}
    params = {}
    for name in PARAM_ORDER:
        shape, std = shapes[name]
        t = torch.randn(*shape, generator=g, dtype=torch.float32) * std if std else torch.zeros(*shape)
        params[name] = t.requires_grad_()
    return params


def forward(params, a, b, want_mlp=False):
    """Logits at "=" for inputs (a, b), and optionally the MLP's post-ReLU activations there."""
    WE, Wpos = params["W_E"], params["W_pos"]
    x0 = WE[:P] + Wpos[0]                       # position 0, by token
    x1 = WE[:P] + Wpos[1]                       # position 1, by token
    x2 = WE[P] + Wpos[2]                        # position 2, the "=" token
    q = (x2 @ params["W_Q"]).view(N_HEADS, D_HEAD)
    k0 = (x0 @ params["W_K"]).view(P, N_HEADS, D_HEAD)
    k1 = (x1 @ params["W_K"]).view(P, N_HEADS, D_HEAD)
    k2 = (x2 @ params["W_K"]).view(N_HEADS, D_HEAD)
    v0 = x0 @ params["W_V"]
    v1 = x1 @ params["W_V"]
    v2 = (x2 @ params["W_V"]).view(N_HEADS, D_HEAD)
    scale = 1 / math.sqrt(D_HEAD)
    s0 = (k0 * q).sum(-1) * scale
    s1 = (k1 * q).sum(-1) * scale
    s2 = (k2 * q).sum(-1) * scale
    scores = torch.stack([s0[a], s1[b], s2.expand(len(a), N_HEADS)], -1)       # N x heads x 3 positions
    att = torch.softmax(scores, -1)
    z = (att[..., 0:1] * v0[a].view(-1, N_HEADS, D_HEAD) + att[..., 1:2] * v1[b].view(-1, N_HEADS, D_HEAD)
         + att[..., 2:3] * v2)
    resid = x2 + z.reshape(-1, N_HEADS * D_HEAD) @ params["W_O"]
    mlp = torch.relu(resid @ params["W_in"] + params["b_in"])
    resid = resid + mlp @ params["W_out"] + params["b_out"]
    logits = resid @ params["W_U"]
    return (logits, mlp) if want_mlp else logits


def xent(logits, labels):
    lp = torch.log_softmax(logits.double(), -1)
    return -lp.gather(1, labels[:, None]).mean()


def train(seed, run, epochs=EPOCHS, log=None):
    torch.set_num_threads(THREADS)
    tr, te = split(seed, run)
    a_tr, b_tr, y_tr = tr // P, tr % P, (tr // P + tr % P) % P
    a_te, b_te, y_te = te // P, te % P, (te // P + te % P) % P
    params = init_params(seed, run)
    initial = {k: v.detach().clone() for k, v in params.items()}
    opt = torch.optim.AdamW(list(params.values()), lr=LR, weight_decay=WEIGHT_DECAY, betas=BETAS)
    history, grok = [], None
    t0 = time.time()
    for epoch in range(1, epochs + 1):
        opt.zero_grad(set_to_none=True)
        loss = xent(forward(params, a_tr, b_tr), y_tr)
        loss.backward()
        opt.step()
        if epoch % EVAL_EVERY == 0 or epoch == epochs:
            with torch.no_grad():
                lt = forward(params, a_te, b_te)
                acc = (lt.argmax(-1) == y_te).double().mean().item()
                tl = xent(lt, y_te).item()
            if grok is None and acc >= ACC_MIN:
                grok = epoch
            if epoch % 1000 == 0 or epoch == epochs:
                history.append({"epoch": epoch, "train_loss": loss.item(), "test_loss": tl, "test_acc": acc})
                if log:
                    log(f"run {run} epoch {epoch}: train {loss.item():.3g} test {tl:.3g} acc {acc:.4f} "
                        f"({time.time() - t0:.0f} s)")
    final = {k: v.detach().clone() for k, v in params.items()}
    return {"final": final, "initial": initial, "history": history, "grok_epoch": grok,
            "test": (a_te, b_te, y_te), "seconds": time.time() - t0}


# ---------------------------------------------------------------- the analysis (rule 4)

def fourier_basis(n=P):
    x = torch.arange(n, dtype=torch.float64)
    rows = [torch.full((n,), 1 / math.sqrt(n), dtype=torch.float64)]
    for k in range(1, (n - 1) // 2 + 1):
        rows.append(math.sqrt(2 / n) * torch.cos(2 * math.pi * k * x / n))
        rows.append(math.sqrt(2 / n) * torch.sin(2 * math.pi * k * x / n))
    return torch.stack(rows)                                                     # n x n


def freq_norms(mat_fourier):
    """Norms of the cos_k and sin_k rows together, k = 1..56, from F applied to a matrix's first axis."""
    m = mat_fourier
    return torch.tensor([math.sqrt(float((m[2 * k - 1] ** 2).sum() + (m[2 * k] ** 2).sum())) for k in range(1, 57)],
                        dtype=torch.float64)


def key_frequencies(norms, fraction=KEY_FRACTION):
    top = float(norms.max())
    return [k for k in range(1, 57) if float(norms[k - 1]) >= fraction * top]


def wl_residual(WL, F, keys):
    rows = [2 * k - 1 for k in keys] + [2 * k for k in keys]
    Fk = F[rows]
    approx = Fk.T @ (Fk @ WL)
    return float(torch.linalg.norm(WL - approx) / torch.linalg.norm(WL))


def fve(y, x):
    """Variance of y explained by beta x + gamma, least squares."""
    X = torch.stack([x, torch.ones_like(x)], 1)
    coef = torch.linalg.lstsq(X, y[:, None]).solution
    res = y - (X @ coef)[:, 0]
    tot = ((y - y.mean()) ** 2).sum()
    return float(1 - (res ** 2).sum() / tot) if tot > 0 else 0.0


def owned(keys):
    out = set()
    for k in keys:
        idx = (0, 2 * k - 1, 2 * k)
        out |= {(i, j) for i in idx for j in idx if (i, j) != (0, 0)}
    return out


def ablate(logits3, F, keys, keep):
    """logits3: a x b x c. keep=True keeps only the components the key frequencies own; False zeroes them."""
    Lh = torch.einsum("ia,abc,jb->ijc", F, logits3, F)
    mask = torch.zeros(P, P, 1, dtype=torch.float64)
    for i, j in owned(keys):
        mask[i, j, 0] = 1.0
    if not keep:
        mask = 1.0 - mask
    return torch.einsum("ia,ijc,jb->abc", F, Lh * mask, F)


def test_xent(logits3, test):
    a, b, y = test
    return float(xent(logits3[a, b], y))


def grid_inputs():
    idx = torch.arange(P * P)
    return idx // P, idx % P


def analyse(params, test, F):
    a, b = grid_inputs()
    with torch.no_grad():
        logits, mlp = forward(params, a, b, want_mlp=True)
    logits3 = logits.double().view(P, P, P)
    mlp = mlp.double()
    WL = (params["W_out"].double() @ params["W_U"].double()).T                   # 113 x 512
    WLh = F @ WL
    norms = freq_norms(WLh)
    keys = key_frequencies(norms)
    residual = wl_residual(WL, F, keys)
    s = (a + b).double()
    fves = {}
    for k in keys:
        w = 2 * math.pi * k / P
        fves[f"{k} cos"] = fve(mlp @ WLh[2 * k - 1], torch.cos(w * s))
        fves[f"{k} sin"] = fve(mlp @ WLh[2 * k], torch.sin(w * s))
    a_te, b_te, y_te = test
    with torch.no_grad():
        acc = float((logits3[a_te, b_te].argmax(-1) == y_te).double().mean())
    base = test_xent(logits3, test)
    excluded = test_xent(ablate(logits3, F, keys, keep=False), test)
    restricted = test_xent(ablate(logits3, F, keys, keep=True), test)
    WEh = F @ params["W_E"][:P].double()
    we_keys = key_frequencies(freq_norms(WEh))
    acts = mlp.view(P, P, D_MLP)
    acts = acts - acts.mean((0, 1), keepdim=True)
    Ah = torch.einsum("ia,abn,jb->ijn", F, acts, F)
    energy = (Ah ** 2).sum((0, 1))
    best = torch.zeros(D_MLP, dtype=torch.float64)
    for k in keys:
        e = sum(Ah[i, j] ** 2 for i, j in owned([k]))
        best = torch.maximum(best, torch.where(energy > 0, e / energy, torch.zeros_like(e)))
    single = float((best > NEURON_FVE).double().mean())
    return {"test_acc": acc, "test_loss": base, "keys": keys, "norms": [float(x) for x in norms],
            "residual": residual, "fve": fves, "excluded_loss": excluded, "restricted_loss": restricted,
            "we_keys": we_keys, "neurons_single_freq": single}


def sparsity_fails(params, F):
    WL = (params["W_out"].double() @ params["W_U"].double()).T
    keys = key_frequencies(freq_norms(F @ WL))
    return len(keys) > KEYS_MAX or wl_residual(WL, F, keys) > RESIDUAL_MAX, len(keys)


# ---------------------------------------------------------------- controls (beside the runs)

def control_basis(F):
    ortho = float((F @ F.T - torch.eye(P, dtype=torch.float64)).abs().max()) < 1e-12
    g = torch.Generator().manual_seed(1)
    L = torch.randn(P, P, P, generator=g, dtype=torch.float64)
    Lh = torch.einsum("ia,abc,jb->ijc", F, L, F)
    back = torch.einsum("ia,ijc,jb->abc", F, Lh, F)
    return ortho and float((back - L).abs().max()) < 1e-9


def control_synthetic_logits(F):
    keys = [5, 17, 30, 41, 52]
    a, b = grid_inputs()
    c = torch.arange(P, dtype=torch.float64)
    s = (a + b).double()
    L = sum(20 * torch.cos(2 * math.pi * k / P * (s[:, None] - c[None, :])) for k in keys).view(P, P, P)
    test = (a, b, (a + b) % P)
    base = test_xent(L, test)
    kept = test_xent(ablate(L, F, keys, keep=True), test)
    gone = test_xent(ablate(L, F, keys, keep=False), test)
    return abs(kept - base) < 1e-9 and abs(gone - math.log(P)) < 1e-9, {"base": base, "kept": kept, "removed": gone}


def control_synthetic_wl(F):
    g = torch.Generator().manual_seed(2)
    keys = [3, 14, 33, 50]
    c = torch.arange(P, dtype=torch.float64)
    WL = torch.zeros(P, D_MLP, dtype=torch.float64)
    for k in keys:
        WL += torch.outer(torch.cos(2 * math.pi * k * c / P), torch.randn(D_MLP, generator=g, dtype=torch.float64))
        WL += torch.outer(torch.sin(2 * math.pi * k * c / P), torch.randn(D_MLP, generator=g, dtype=torch.float64))
    noise = torch.randn(P, D_MLP, generator=g, dtype=torch.float64)
    WL_noisy = WL + 0.01 * noise * torch.linalg.norm(WL) / torch.linalg.norm(noise)
    found = key_frequencies(freq_norms(F @ WL_noisy))
    res = wl_residual(WL_noisy, F, found)
    return found == keys and 0.005 < res < 0.015, {"found": found, "residual": res}


def control_determinism(seed):
    r1 = train(seed, 1, epochs=200)["final"]
    r2 = train(seed, 1, epochs=200)["final"]
    return all(torch.equal(r1[k], r2[k]) for k in PARAM_ORDER)


# ---------------------------------------------------------------- the verdict

def run(seed, results="results", log=None, epochs=EPOCHS, runs=RUNS):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    torch.set_num_threads(THREADS)
    F = fourier_basis()
    out_runs, init_fail = [], []
    for r in range(1, runs + 1):
        tr = train(seed, r, epochs=epochs, log=log)
        res = analyse(tr["final"], tr["test"], F)
        res.update({"run": r, "grok_epoch": tr["grok_epoch"], "seconds": round(tr["seconds"], 1),
                    "history": tr["history"]})
        out_runs.append(res)
        init_fail.append(sparsity_fails(tr["initial"], F))
    cond = {
        "test accuracy at least 99% in every run": all(x["test_acc"] >= ACC_MIN for x in out_runs),
        "1 to 8 key frequencies in every run": all(1 <= len(x["keys"]) <= KEYS_MAX for x in out_runs),
        "W_L within 5% of its key sine and cosine directions in every run":
            all(x["residual"] <= RESIDUAL_MAX for x in out_runs),
        "every key projection at least 90% explained by cos or sin(w_k(a+b))":
            all(v >= FVE_MIN for x in out_runs for v in x["fve"].values()) and all(x["fve"] for x in out_runs),
        "key frequencies ablated: test loss above ln 113; all others ablated: not above the run's own":
            all(x["excluded_loss"] > math.log(P) and x["restricted_loss"] <= x["test_loss"] for x in out_runs),
    }
    ctl, ctl_detail = {}, {}
    ctl["F is orthonormal and the logits survive a transform and back"] = control_basis(F)
    ok, det = control_synthetic_logits(F)
    ctl["synthetic Fourier logits: kept components keep the loss, removed ones give ln 113"] = ok
    ctl_detail["synthetic_logits"] = det
    ok, det = control_synthetic_wl(F)
    ctl["a four-frequency neuron-logit map with 1% noise: those four found, residual near 1%"] = ok
    ctl_detail["synthetic_wl"] = det
    ctl["every run at initialisation fails the sparsity checks"] = all(f for f, _ in init_fail)
    ctl_detail["initial_key_counts"] = [n for _, n in init_fail]
    ctl["run 1 trained for 200 epochs twice gives identical parameters"] = control_determinism(seed)

    def fmt(x, nd=4):
        return f"{x:.{nd}g}"
    values = {
        "runs": f"{runs} runs x {epochs} epochs",
        "runs_generalised": sum(1 for x in out_runs if x["test_acc"] >= ACC_MIN),
        "test_acc": ", ".join(f"{x['test_acc']:.4f}" for x in out_runs),
        "grok_epoch": ", ".join(str(x["grok_epoch"]) if x["grok_epoch"] else "none" for x in out_runs),
        "key_freqs": " | ".join(" ".join(map(str, x["keys"])) for x in out_runs),
        "n_key_max": max(len(x["keys"]) for x in out_runs),
        "wl_residual_max": round(max(x["residual"] for x in out_runs), 4),
        "fve_min": round(min((v for x in out_runs for v in x["fve"].values()), default=0.0), 3),
        "excluded_loss_min": round(min(x["excluded_loss"] for x in out_runs), 2),
        "restricted_ratio_max": round(max(x["restricted_loss"] / x["test_loss"] if x["test_loss"] > 0 else float("inf")
                                          for x in out_runs), 2),
        "test_loss": ", ".join(fmt(x["test_loss"], 3) for x in out_runs),
        "we_freqs": " | ".join(" ".join(map(str, x["we_keys"])) for x in out_runs),
        "neurons_single_freq": ", ".join(f"{x['neurons_single_freq']:.3f}" for x in out_runs),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
        "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for key, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{key}: longer than {LIMIT} characters: {v}")
    detail = {"settings": {"P": P, "d_model": D_MODEL, "heads": N_HEADS, "d_head": D_HEAD, "d_mlp": D_MLP,
                           "frac_train": FRAC_TRAIN, "epochs": epochs, "lr": LR, "weight_decay": WEIGHT_DECAY,
                           "betas": BETAS, "runs": runs, "threads": THREADS, "torch": torch.__version__},
              "conditions": cond, "controls": ctl, "control_detail": ctl_detail, "runs": out_runs}
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="ascii") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, default=str)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed, log=lambda s: print(s, file=sys.stderr, flush=True))
    except Refused as e:
        sys.exit(f"nanda: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
