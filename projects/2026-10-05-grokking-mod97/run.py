"""Grokking on modular addition (Power et al., arXiv:2201.02177), re-run as the paper describes (see PLAN.md).

A two-layer decoder-only transformer (width 128, four heads) is trained with AdamW (learning rate 1e-3, weight decay 1,
betas 0.9/0.98, ten warm-up steps, minibatch 512) on a random fraction of the 97 x 97 table of x + y (mod 97), with the
loss and accuracy computed on the answer token only, for up to 1e5 optimisation steps per run (the paper's budget), at training fractions 0.5, 0.3 and 0.25. Each run
records when training accuracy first reaches 100%, the validation accuracy at that moment, when validation accuracy first
reaches 99%, and the value at the end; a run stops once validation accuracy has held at 99% for 2,000 steps. All randomness (the train/validation split, the initialisation, the minibatch order) comes from ECDYSIS_SEED; the
clock is never read. Writes results/outputs.json: numbers only.

Dependencies: jax (CPU), optax. Pinned in PLAN.md.
"""
import json
import os
import sys
import time

import jax
import jax.numpy as jnp
import numpy as np
import optax

P = 97                 # the prime: residues 0..96 are tokens 0..96
OP, EQ = P, P + 1      # the operation and the equals sign as tokens
VOCAB = P + 2
D, LAYERS, HEADS = 128, 2, 4
LR, WD, B1, B2, WARMUP = 1e-3, 1.0, 0.9, 0.98, 10
BUDGET = int(os.environ.get("GROK_BUDGET", "100000"))      # the paper's 1e5; the environment variable exists for smoke tests only
EVAL_EVERY = 100
FRACTIONS = [float(x) for x in os.environ.get("GROK_FRACTIONS", "0.5,0.3,0.25").split(",")]
PATIENCE = 2000        # steps of validation accuracy >= 99% before a run stops early (the outcome is then known)


def table():
    a, b = np.meshgrid(np.arange(P), np.arange(P), indexing="ij")
    a, b = a.ravel(), b.ravel()
    c = (a + b) % P
    seq = np.stack([a, np.full_like(a, OP), b, np.full_like(a, EQ)], axis=1)   # the answer is predicted from this prefix
    return seq.astype(np.int32), c.astype(np.int32)


def init_params(key):
    ks = jax.random.split(key, 2 + 8 * LAYERS)
    s = 0.02
    params = {"tok": s * jax.random.normal(ks[0], (VOCAB, D)), "pos": s * jax.random.normal(ks[1], (4, D)),
              "ln_f_g": jnp.ones((D,)), "ln_f_b": jnp.zeros((D,)), "out": s * jax.random.normal(ks[2], (D, VOCAB)), "layers": []}
    for l in range(LAYERS):
        k = ks[3 + 8 * l: 3 + 8 * (l + 1)]
        params["layers"].append({
            "ln1_g": jnp.ones((D,)), "ln1_b": jnp.zeros((D,)),
            "wq": s * jax.random.normal(k[0], (D, D)), "wk": s * jax.random.normal(k[1], (D, D)),
            "wv": s * jax.random.normal(k[2], (D, D)), "wo": s * jax.random.normal(k[3], (D, D)),
            "ln2_g": jnp.ones((D,)), "ln2_b": jnp.zeros((D,)),
            "w1": s * jax.random.normal(k[4], (D, 4 * D)), "b1": jnp.zeros((4 * D,)),
            "w2": s * jax.random.normal(k[5], (4 * D, D)), "b2": jnp.zeros((D,)),
        })
    return params


def layer_norm(x, g, b):
    m = x.mean(-1, keepdims=True)
    v = ((x - m) ** 2).mean(-1, keepdims=True)
    return (x - m) / jnp.sqrt(v + 1e-5) * g + b


def forward(params, seq):
    """Pre-LN decoder-only transformer with causal attention; returns logits for the token after the prefix (the answer)."""
    n, t = seq.shape
    x = params["tok"][seq] + params["pos"][None, :t]
    mask = jnp.tril(jnp.ones((t, t), dtype=bool))
    hd = D // HEADS
    for L in params["layers"]:
        h = layer_norm(x, L["ln1_g"], L["ln1_b"])
        q = (h @ L["wq"]).reshape(n, t, HEADS, hd).transpose(0, 2, 1, 3)
        k = (h @ L["wk"]).reshape(n, t, HEADS, hd).transpose(0, 2, 1, 3)
        v = (h @ L["wv"]).reshape(n, t, HEADS, hd).transpose(0, 2, 1, 3)
        att = (q @ k.transpose(0, 1, 3, 2)) / jnp.sqrt(hd)
        att = jnp.where(mask[None, None], att, -1e9)
        att = jax.nn.softmax(att, axis=-1)
        a = (att @ v).transpose(0, 2, 1, 3).reshape(n, t, D) @ L["wo"]
        x = x + a
        h = layer_norm(x, L["ln2_g"], L["ln2_b"])
        x = x + (jax.nn.gelu(h @ L["w1"] + L["b1"]) @ L["w2"] + L["b2"])
    x = layer_norm(x[:, -1], params["ln_f_g"], params["ln_f_b"])
    return x @ params["out"]


def loss_fn(params, seq, c):
    logits = forward(params, seq)
    return optax.softmax_cross_entropy_with_integer_labels(logits, c).mean()


def accuracy(params, seq, c):
    return float((jnp.argmax(forward(params, seq), -1) == c).mean())


def run(fraction, key, log):
    seq, c = table()
    k_split, k_init, k_batch = jax.random.split(key, 3)
    perm = np.asarray(jax.random.permutation(k_split, len(c)))
    n_train = int(round(fraction * len(c)))
    tr, va = perm[:n_train], perm[n_train:]
    seq_tr, c_tr, seq_va, c_va = seq[tr], c[tr], seq[va], c[va]
    batch = min(512, n_train // 2)
    params = init_params(k_init)
    schedule = optax.join_schedules([optax.linear_schedule(0.0, LR, WARMUP), optax.constant_schedule(LR)], [WARMUP])
    opt = optax.adamw(schedule, b1=B1, b2=B2, weight_decay=WD)
    state = opt.init(params)

    @jax.jit
    def step(params, state, s, y):
        l, g = jax.value_and_grad(loss_fn)(params, s, y)
        upd, state = opt.update(g, state, params)
        return optax.apply_updates(params, upd), state, l

    eval_tr = jax.jit(lambda p: (jnp.argmax(forward(p, seq_tr), -1) == c_tr).mean())
    eval_va = jax.jit(lambda p: (jnp.argmax(forward(p, seq_va), -1) == c_va).mean())

    first = {"train99": -1, "train100": -1, "val99": -1}
    val_at_train100 = -1.0
    tr_acc = va_acc = 0.0
    steps_done = 0
    held = 0
    rng = np.random.default_rng(int(np.asarray(jax.random.key_data(k_batch))[-1]))
    order = rng.permutation(n_train)
    pos = 0
    t0 = time.time()
    for it in range(1, BUDGET + 1):
        if pos + batch > n_train:
            order = rng.permutation(n_train)
            pos = 0
        idx = order[pos: pos + batch]
        pos += batch
        params, state, l = step(params, state, seq_tr[idx], c_tr[idx])
        steps_done = it
        if it % EVAL_EVERY == 0 or it == BUDGET:
            tr_acc, va_acc = float(eval_tr(params)), float(eval_va(params))
            if first["train99"] < 0 and tr_acc >= 0.99:
                first["train99"] = it
            if first["train100"] < 0 and tr_acc >= 1.0 - 1e-9:
                first["train100"] = it
                val_at_train100 = va_acc
            if first["val99"] < 0 and va_acc >= 0.99:
                first["val99"] = it
            held = held + EVAL_EVERY if va_acc >= 0.99 else 0
            if it % 1000 == 0:
                log(f"fraction {fraction} step {it} loss {float(l):.4f} train {tr_acc:.4f} val {va_acc:.4f} ({time.time() - t0:.0f}s)")
            if held >= PATIENCE and first["train100"] > 0:
                break
    log(f"fraction {fraction}: train99 at {first['train99']}, train100 at {first['train100']}, val99 at {first['val99']}, final train {tr_acc:.4f} val {va_acc:.4f}, {steps_done} steps")
    return {"train_examples": n_train, "steps_run": steps_done, "train100_step": first["train100"], "val99_step": first["val99"],
            "val_acc_at_train100": round(val_at_train100, 4), "final_val_acc": round(va_acc, 4)}


def main():
    seed_hex = os.environ["ECDYSIS_SEED"]
    if len(seed_hex) != 64:
        sys.exit("ECDYSIS_SEED must be 64 hex characters")
    key = jax.random.key(int(seed_hex[:8], 16))
    keys = jax.random.split(key, len(FRACTIONS))
    out = {}
    for f, k in zip(FRACTIONS, keys):
        r = run(f, k, lambda m: print(m, flush=True))
        tag = f"f{int(round(f * 100))}"
        for name, v in r.items():
            out[f"{tag}_{name}"] = v
    os.makedirs("results", exist_ok=True)
    with open("results/outputs.json", "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
