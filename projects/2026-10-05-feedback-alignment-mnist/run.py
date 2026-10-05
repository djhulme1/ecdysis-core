"""Feedback alignment against backpropagation on MNIST (Lillicrap, Cownden, Tweed and Akerman, arXiv:1411.0247), re-run as the
paper describes (see PLAN.md).

A 784-1000-10 network of sigmoidal units with biases, squared error against one-hot targets, learning rate 1e-3 and weight decay
1e-6, trained on the 60,000 MNIST training images; the hidden layer's updates use either the transposed forward weights
(backpropagation) or a fixed random matrix B (feedback alignment). Three seeds per algorithm; the same number of passes for
every run; test error measured on the 10,000 test images after each pass. All randomness comes from ECDYSIS_SEED; the clock is
never read. Reads MNIST at inputs/ (inputs/0.1). Writes results/outputs.json: numbers only. Dependencies: jax (CPU), numpy.
"""
import gzip
import json
import os
import struct
import sys
import time

import jax
import jax.numpy as jnp
import numpy as np

EPOCHS = int(os.environ.get("FA_EPOCHS", "300"))
SEEDS = int(os.environ.get("FA_SEEDS", "3"))
BATCH = 10            # updates summed over ten examples at the per-example learning rate (the paper's updates are per example)
LR, WD = 1e-3, 1e-6
HIDDEN = 1000
OMEGA, BETA = 0.4, 0.4     # forward and feedback weight scales (uniform on [-w, w]): chosen by a short search for backpropagation, as the paper did (PLAN.md)


def idx(path):
    with gzip.open(path, "rb") as fh:
        magic, n = struct.unpack(">II", fh.read(8))
        dims = magic & 0xFF
        shape = [n] + [struct.unpack(">I", fh.read(4))[0] for _ in range(dims - 1)]
        return np.frombuffer(fh.read(), dtype=np.uint8).reshape(shape)


def load():
    xtr = idx("inputs/train-images-idx3-ubyte.gz").reshape(-1, 784).astype(np.float32) / 255.0
    ytr = idx("inputs/train-labels-idx1-ubyte.gz").astype(np.int32)
    xte = idx("inputs/t10k-images-idx3-ubyte.gz").reshape(-1, 784).astype(np.float32) / 255.0
    yte = idx("inputs/t10k-labels-idx1-ubyte.gz").astype(np.int32)
    return xtr, ytr, xte, yte


def init(key):
    k0, k1, kb = jax.random.split(key, 3)
    W0 = jax.random.uniform(k0, (784, HIDDEN), minval=-OMEGA, maxval=OMEGA)
    W = jax.random.uniform(k1, (HIDDEN, 10), minval=-OMEGA, maxval=OMEGA)
    B = jax.random.uniform(kb, (10, HIDDEN), minval=-BETA, maxval=BETA)
    return {"W0": W0, "b0": jnp.zeros((HIDDEN,)), "W": W, "b": jnp.zeros((10,))}, B


def make_step(feedback_alignment):
    @jax.jit
    def step(p, B, x, t):
        a0 = x @ p["W0"] + p["b0"]
        h = jax.nn.sigmoid(a0)
        a = h @ p["W"] + p["b"]
        y = jax.nn.sigmoid(a)
        e = t - y                                   # the error vector e = y* - y of the paper
        d_out = e * y * (1.0 - y)                   # through the output nonlinearity
        back = (d_out @ B) if feedback_alignment else (d_out @ p["W"].T)
        d_hid = back * h * (1.0 - h)
        new = {
            "W": p["W"] + LR * (h.T @ d_out) - LR * WD * p["W"],
            "b": p["b"] + LR * d_out.sum(0),
            "W0": p["W0"] + LR * (x.T @ d_hid) - LR * WD * p["W0"],
            "b0": p["b0"] + LR * d_hid.sum(0),
        }
        return new
    return step


@jax.jit
def test_error(p, x, y):
    h = jax.nn.sigmoid(x @ p["W0"] + p["b0"])
    out = h @ p["W"] + p["b"]
    return (jnp.argmax(out, -1) != y).mean() * 100.0


def run(alg, key, data, log):
    xtr, ytr, xte, yte = data
    k_init, k_order = jax.random.split(key)
    p, B = init(k_init)
    step = make_step(alg == "fa")
    rng = np.random.default_rng(int(np.asarray(jax.random.key_data(k_order))[-1]))
    T = np.eye(10, dtype=np.float32)[ytr]
    errs = []
    t0 = time.time()
    for ep in range(1, EPOCHS + 1):
        order = rng.permutation(len(ytr))
        for i in range(0, len(order), BATCH):
            idxs = order[i: i + BATCH]
            p = step(p, B, xtr[idxs], T[idxs])
        err = float(test_error(p, xte, yte))
        errs.append(err)
        if ep % 25 == 0 or ep == 1:
            log(f"{alg} epoch {ep}: test error {err:.2f}% ({time.time() - t0:.0f}s)")
    return errs


def first_at_or_below(errs, level):
    """The first pass after which the test error is at or below level, or -1."""
    return next((i + 1 for i, e in enumerate(errs) if e <= level), -1)


def main():
    seed_hex = os.environ["ECDYSIS_SEED"]
    if len(seed_hex) != 64:
        sys.exit("ECDYSIS_SEED must be 64 hex characters")
    key = jax.random.key(int(seed_hex[:8], 16))
    data = load()
    log = lambda m: print(m, flush=True)
    keys = jax.random.split(key, SEEDS)
    out = {"epochs": EPOCHS, "seeds": SEEDS}
    finals = {"bp": [], "fa": []}
    mins = {"bp": [], "fa": []}
    for s in range(SEEDS):
        bp = run("bp", keys[s], data, log)      # the same key for both: the same initial forward weights and the same example order
        fa = run("fa", keys[s], data, log)
        for alg, errs in (("bp", bp), ("fa", fa)):
            finals[alg].append(errs[-1]); mins[alg].append(min(errs))
            out[f"{alg}_final_s{s}"] = round(errs[-1], 3)
        out[f"bp_epochs_to_own_final_s{s}"] = first_at_or_below(bp, bp[-1])
        out[f"fa_epochs_to_bp_final_s{s}"] = first_at_or_below(fa, bp[-1])
    for alg in ("bp", "fa"):
        out[f"{alg}_mean_final"] = round(float(np.mean(finals[alg])), 3)
        out[f"{alg}_mean_min"] = round(float(np.mean(mins[alg])), 3)
    os.makedirs("results", exist_ok=True)
    with open("results/outputs.json", "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
