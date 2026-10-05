"""Resumable driver for the pinned feedback-alignment bundle: runs its own run() for one (seed index, algorithm) job at a time,
saves each job's error curve, and assembles outputs.json exactly as main() does. Usage: driver.py job <s> <alg> | driver.py assemble"""
import json, os, sys, importlib.util
REPO = "/tmp/ecdysis-run-KA77aQ"; os.chdir(REPO)
sys.path.insert(0, REPO + "/projects/2026-10-05-feedback-alignment-mnist")
import run as R, jax, numpy as np
JOBS = os.path.dirname(os.path.abspath(__file__)) + "/jobs"
SEED = "1582197b5414e767339dc7d21df90d163788e8aa6b8d1b9b0cc3eeb7405b9e8c"
keys = jax.random.split(jax.random.key(int(SEED[:8], 16)), R.SEEDS)
def run_ckpt(alg, key, data, f):
    """R.run(), line for line, with the state (parameters, example-order generator, error curve) saved every 5 passes and resumed."""
    import pickle, jax.numpy as jnp
    xtr, ytr, xte, yte = data
    k_init, k_order = jax.random.split(key)
    p, B = R.init(k_init)
    step = R.make_step(alg == "fa")
    rng = np.random.default_rng(int(np.asarray(jax.random.key_data(k_order))[-1]))
    T = np.eye(10, dtype=np.float32)[ytr]
    errs, start = [], 1
    if os.path.exists(f + ".ckpt"):
        c = pickle.load(open(f + ".ckpt", "rb"))
        p = {k: jnp.asarray(v) for k, v in c["p"].items()}; rng.bit_generator.state = c["rng"]; errs = c["errs"]; start = len(errs) + 1
        print("resumed at pass", start, flush=True)
    for ep in range(start, R.EPOCHS + 1):
        order = rng.permutation(len(ytr))
        for i in range(0, len(order), R.BATCH):
            idxs = order[i: i + R.BATCH]
            p = step(p, B, xtr[idxs], T[idxs])
        errs.append(float(R.test_error(p, xte, yte)))
        if ep % 25 == 0 or ep == 1: print(f"{alg} epoch {ep}: test error {errs[-1]:.2f}%", flush=True)
        if ep % 5 == 0:
            pickle.dump({"p": {k: np.asarray(v) for k, v in p.items()}, "rng": rng.bit_generator.state, "errs": errs}, open(f + ".ckpt.tmp", "wb")); os.rename(f + ".ckpt.tmp", f + ".ckpt")
    return errs

if sys.argv[1] == "job":
    s, alg = int(sys.argv[2]), sys.argv[3]; f = f"{JOBS}/{alg}_s{s}.json"
    if os.path.exists(f): sys.exit(0)
    errs = run_ckpt(alg, keys[s], R.load(), f)
    json.dump(errs, open(f + ".tmp", "w")); os.rename(f + ".tmp", f)
else:
    out = {"epochs": R.EPOCHS, "seeds": R.SEEDS}; finals = {"bp": [], "fa": []}; mins = {"bp": [], "fa": []}
    for s in range(R.SEEDS):
        e = {a: json.load(open(f"{JOBS}/{a}_s{s}.json")) for a in ("bp", "fa")}
        for a in ("bp", "fa"):
            finals[a].append(e[a][-1]); mins[a].append(min(e[a])); out[f"{a}_final_s{s}"] = round(e[a][-1], 3)
        out[f"bp_epochs_to_own_final_s{s}"] = R.first_at_or_below(e["bp"], e["bp"][-1])
        out[f"fa_epochs_to_bp_final_s{s}"] = R.first_at_or_below(e["fa"], e["bp"][-1])
    for a in ("bp", "fa"):
        out[f"{a}_mean_final"] = round(float(np.mean(finals[a])), 3); out[f"{a}_mean_min"] = round(float(np.mean(mins[a])), 3)
    json.dump(out, open(os.path.dirname(os.path.abspath(__file__)) + "/outputs-assembled.json", "w"), indent=1, sort_keys=True)
    print(json.dumps(out, indent=1, sort_keys=True))
