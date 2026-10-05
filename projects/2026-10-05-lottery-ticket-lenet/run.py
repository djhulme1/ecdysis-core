"""Winning tickets in Lenet-300-100 on MNIST (Frankle & Carbin, arXiv:1803.03635), re-run as the paper describes (see PLAN.md).

Iterative magnitude pruning with reset to the original initialisation: train the dense network for 50,000 iterations
(Adam 1.2e-3, batch 60, Gaussian Glorot initialisation, a 5,000-example validation set drawn from the 60,000 training
examples), prune 20% of the remaining weights per layer (10% in the output layer) by magnitude, reset the survivors to
their initial values, repeat for eleven rounds; at rounds 7, 9 and 11 (21.1%, 13.5% and 8.7% of the weights) also train the
same mask from a fresh random initialisation. For each network: the early-stopping iteration (the iteration of minimum
validation loss, found retroactively; validation evaluated every 100 iterations), the test accuracy at that iteration and
at iteration 50,000. All randomness comes from ECDYSIS_SEED; the clock is never read. Reads MNIST at inputs/ (inputs/0.1).
Writes results/outputs.json: numbers only.

Dependencies: jax (CPU), optax, numpy. Pinned in PLAN.md.
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
import optax

ITERS = int(os.environ.get("LTH_ITERS", "50000"))        # the paper's 50,000; the environment variable exists for smoke tests only
ROUNDS = int(os.environ.get("LTH_ROUNDS", "11"))
REINIT_AT = [int(x) for x in os.environ.get("LTH_REINIT_AT", "7,9,11").split(",") if x]
BATCH, LR, EVAL_EVERY = 60, 1.2e-3, 100
SIZES = [784, 300, 100, 10]
PRUNE = [0.2, 0.2, 0.1]            # per layer per round; the output layer at half the rate


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


def glorot(key):
    """Gaussian Glorot: N(0, 2 / (fan_in + fan_out)) weights, zero biases."""
    params = []
    for i, k in enumerate(jax.random.split(key, len(SIZES) - 1)):
        fi, fo = SIZES[i], SIZES[i + 1]
        params.append({"w": jax.random.normal(k, (fi, fo)) * jnp.sqrt(2.0 / (fi + fo)), "b": jnp.zeros((fo,))})
    return params


def forward(params, masks, x):
    for i, (p, m) in enumerate(zip(params, masks)):
        x = x @ (p["w"] * m) + p["b"]
        if i < len(params) - 1:
            x = jax.nn.relu(x)
    return x


def loss_fn(params, masks, x, y):
    return optax.softmax_cross_entropy_with_integer_labels(forward(params, masks, x), y).mean()


def train(params0, masks, data, key, log, tag):
    """Train a masked network from params0 for ITERS iterations; return the early-stopping record and final test accuracy."""
    xtr, ytr, xva, yva, xte, yte = data
    opt = optax.adam(LR)
    params = jax.tree_util.tree_map(lambda a: a, params0)
    state = opt.init(params)

    @jax.jit
    def step(params, state, x, y):
        l, g = jax.value_and_grad(loss_fn)(params, masks, x, y)
        g = [{"w": gi["w"] * m, "b": gi["b"]} for gi, m in zip(g, masks)]   # pruned weights get no gradient
        upd, state = opt.update(g, state, params)
        return optax.apply_updates(params, upd), state, l

    @jax.jit
    def val_loss(params):
        return loss_fn(params, masks, xva, yva)

    @jax.jit
    def test_acc(params):
        return (jnp.argmax(forward(params, masks, xte), -1) == yte).mean()

    rng = np.random.default_rng(int(np.asarray(jax.random.key_data(key))[-1]))
    n = len(ytr)
    order = rng.permutation(n)
    pos = 0
    best = (float("inf"), 0, None)
    t0 = time.time()
    for it in range(1, ITERS + 1):
        if pos + BATCH > n:
            order = rng.permutation(n)
            pos = 0
        idxs = order[pos: pos + BATCH]
        pos += BATCH
        params, state, _ = step(params, state, xtr[idxs], ytr[idxs])
        if it % EVAL_EVERY == 0:
            vl = float(val_loss(params))
            if vl < best[0]:
                best = (vl, it, jax.tree_util.tree_map(lambda a: a, params))
    acc_es = float(test_acc(best[2]))
    acc_end = float(test_acc(params))
    log(f"{tag}: early stop at {best[1]} (val loss {best[0]:.4f}), test acc {acc_es:.4f} there, {acc_end:.4f} at {ITERS} ({time.time() - t0:.0f}s)")
    return {"early_stop_iter": best[1], "test_acc_es": round(acc_es, 4), "test_acc_end": round(acc_end, 4)}, params


def prune(params, masks):
    """Remove the smallest-magnitude surviving weights of each layer at its rate; keep the others' masks."""
    new = []
    for p, m, rate in zip(params, masks, PRUNE):
        w = np.asarray(p["w"]); mk = np.asarray(m)
        alive = np.abs(w[mk > 0])
        k = int(round(rate * alive.size))
        if k <= 0:
            new.append(m); continue
        thresh = np.sort(alive)[k - 1]
        nm = mk * (np.abs(w) > thresh)
        new.append(jnp.asarray(nm, dtype=jnp.float32))
    return new


def remaining(masks):
    tot = sum(int(np.asarray(m).size) for m in masks)
    alive = sum(int(np.asarray(m).sum()) for m in masks)
    return alive, tot


def main():
    seed_hex = os.environ["ECDYSIS_SEED"]
    if len(seed_hex) != 64:
        sys.exit("ECDYSIS_SEED must be 64 hex characters")
    key = jax.random.key(int(seed_hex[:8], 16))
    k_split, k_init, k_train, k_reinit = jax.random.split(key, 4)
    xtr_all, ytr_all, xte, yte = load()
    perm = np.asarray(jax.random.permutation(k_split, len(ytr_all)))
    va, tr = perm[:5000], perm[5000:]
    data = (xtr_all[tr], ytr_all[tr], xtr_all[va], ytr_all[va], xte, yte)
    log = lambda m: print(m, flush=True)

    params0 = glorot(k_init)
    masks = [jnp.ones((SIZES[i], SIZES[i + 1]), dtype=jnp.float32) for i in range(len(SIZES) - 1)]
    train_keys = jax.random.split(k_train, ROUNDS + 1)
    reinit_keys = jax.random.split(k_reinit, len(REINIT_AT) * 2)
    out = {}
    for k in range(ROUNDS + 1):
        alive, tot = remaining(masks)
        pm = 100.0 * alive / tot
        rec, trained = train(params0, masks, data, train_keys[k], log, f"round {k} ticket Pm {pm:.1f}%")
        if k in (0, *REINIT_AT):
            out[f"k{k}_pm"] = round(pm, 2)
            out[f"k{k}_es_iter"] = rec["early_stop_iter"]
            out[f"k{k}_acc_es"] = rec["test_acc_es"]
            if k in (0, 9):
                out[f"k{k}_acc_end"] = rec["test_acc_end"]
        if k in REINIT_AT:
            j = REINIT_AT.index(k)
            rp = glorot(reinit_keys[2 * j])
            rrec, _ = train(rp, masks, data, reinit_keys[2 * j + 1], log, f"round {k} random reinit Pm {pm:.1f}%")
            out[f"k{k}_reinit_es_iter"] = rrec["early_stop_iter"]
            out[f"k{k}_reinit_acc_es"] = rrec["test_acc_es"]
        if k < ROUNDS:
            masks = prune(trained, masks)
    os.makedirs("results", exist_ok=True)
    with open("results/outputs.json", "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
