#!/usr/bin/env python3
"""Adaptive spiking recurrent networks on the Spiking Heidelberg Digits: the authors' released network, evaluated.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:d6c48d55b89fa782) is from Yin, Corradi &
Bohte, "Accurate and efficient time-domain classification with adaptive spiking recurrent neural networks" (Nature
Machine Intelligence 3, 905-913, 2021; arXiv:2103.12593): "Here, we demonstrate how a novel surrogate gradient combined
with recurrent networks of tunable and adaptive spiking neurons yields state-of-the-art for SNNs on challenging benchmarks
in the time-domain, like speech and gesture recognition. This also exceeds the performance of standard classical
recurrent neural networks (RNNs) and approaches that of the best modern ANNs."

Its registered test: refuted if the SHD network the authors released (SHD/model_90.7-readout-2layer-v2-4ms.pth at
bfd47cf), run on the SHD test set as their code runs it (1 s in 4 ms binary bins as their generator makes them; random
initial membrane potentials; the summed softmax readout after step 10), averaged over 16 seed-drawn initialisations,
classifies less than the 90.4% the paper reports (below 90.35%), or not more than the best earlier SNN (82.7%) and the
Bi-LSTM (87.2%) its Table 1 lists for SHD.

numpy and h5py, in the pinned scientific image. The inputs are the claim's data of record, each checked against its
SHA-256: the SHD test set (read with h5py as data), the released network (a PyTorch archive, read by a restricted
unpickler that admits only the eight names the archive uses and builds plain arrays; nothing in it is run) and the
authors' training script (read as text only: the constants this module takes from it must appear in it verbatim, and its
own log, kept in its closing comments, is read). The network is computed here, in numpy, from the authors' description in
that script; their code is not run. Every rule below was fixed before any seed existed.

1. The digits, as the authors' generator (SHD/generate_dataset.py at bfd47cf) makes them: 250 bins of 4 ms; bin i holds
   the spikes not yet taken whose times are at most i x 0.004, compared as the files store the times (float16, so each
   edge is i x 0.004 rounded to float16); unit 0 is dropped and unit u (1 to 699) lights channel 700 - u; a bin is 1
   where any spike fell, else 0; spikes after the last edge are left out.
2. The network, as RNN_custom and mem_update_adp in the script compute it, one 4 ms step at a time: layer 1 (128
   adaptive units) takes the input and its own spikes, layer 2 (128) takes layer 1's new spikes and its own, through
   linear maps with biases; for each layer, with alpha = exp(-1/tau_m) and rho = exp(-1/tau_adp) per unit, b <- rho b +
   (1 - rho) s, B = 0.01 + 1.8 b, v <- alpha v + (1 - alpha) I - B s, s = [v - B > 0], b starting at 0.01 and s at 0;
   the 20 readout units integrate v_o <- alpha_o v_o + (1 - alpha_o) (W s2 + c); from step 11 on (index above 10) the
   softmax of v_o is summed, and the class is its largest entry. Initial membrane potentials (both layers and the
   readout) are uniform on [0, 1), as the script draws them. Computed in float64 with one BLAS thread.
3. Draws: 16 initialisations, draw k from numpy's PCG64 seeded with the first 8 bytes of SHA-256(the seed's bytes ||
   "|srnn/draw/" || k); each draws layer 1's, then layer 2's, then the readout's potentials for all 2,264 digits at once.
4. The test: the mean accuracy over the 16 draws must be at least 90.35% and above 87.2% and 82.7%. test_passed is 1 if
   all three hold.
5. Beside the test: the spread over draws; the accuracy with all initial potentials at 0 (the script's commented-out
   alternative); the held-out speakers' digits (speakers 4 and 5) and the rest of the test set (speakers also in
   training) apart; the accuracy the archive's name records (90.7); and the script's own log of the test accuracy after
   each epoch, which is how it chose the model it saved (it saves whenever the test accuracy beats the best so far, with
   no validation set).
6. Controls, which must all pass or the run stops: the restricted unpickler refuses an archive naming anything else; the
   vectorised network agrees with a step-by-step computation of single digits, written apart, on 8 digits of draw 1;
   with the labels permuted (seeded) the accuracy is near chance (below 10%); and with every input bin empty the
   network gives one answer for all digits.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
"""

import os

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import collections  # noqa: E402
import gzip  # noqa: E402
import hashlib  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import pickle  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
import zipfile  # noqa: E402

import numpy as np  # noqa: E402

INPUTS = {
    "shd": ("shd_test.h5.gz", "bfd3d30d08a1eab1e9549f1b7f08d36044f38efa260f32241bafdf6e42bd2326"),
    "model": ("model_90.7-readout-2layer-v2-4ms.pth", "2b69992f7a64b86440a5b679103ca6e84c305813ece50fd28858114347818b37"),
    "script": ("SHD_2layer_ALIF.py", "fcdd0206b152b0349bc00583609d930c07b88e3dae2397bf210757597528062f"),
}
DT, BINS, CHANNELS, HIDDEN, CLASSES = 4e-3, 250, 700, 128, 20
B_J0, BETA, START = 0.01, 1.8, 10
DRAWS, PAPER, ROUNDED, BILSTM, BEST_SNN, LABEL = 16, 90.4, 90.35, 87.2, 82.7, 90.7
UNSEEN = (4, 5)
SHAPES = {"tau_adp_h1": (HIDDEN,), "tau_adp_h2": (HIDDEN,), "tau_adp_o": (CLASSES,), "tau_m_h1": (HIDDEN,),
          "tau_m_h2": (HIDDEN,), "tau_m_o": (CLASSES,), "i_2_h1.weight": (HIDDEN, CHANNELS), "i_2_h1.bias": (HIDDEN,),
          "h1_2_h1.weight": (HIDDEN, HIDDEN), "h1_2_h1.bias": (HIDDEN,), "h1_2_h2.weight": (HIDDEN, HIDDEN),
          "h1_2_h2.bias": (HIDDEN,), "h2_2_h2.weight": (HIDDEN, HIDDEN), "h2_2_h2.bias": (HIDDEN,),
          "h2o.weight": (CLASSES, HIDDEN), "h2o.bias": (CLASSES,)}
SCRIPT_FACTS = ("b_j0 = 0.01", "beta = 1.8", "R_m = 1", "dt = 1", "if i > 10:",
                "output= output + F.softmax(mem_output, dim=1)",
                "mem_layer1 = torch.rand(batch_size, self.hidden_size[0])",
                "mem_layer2 = torch.rand(batch_size, self.hidden_size[1])",
                "mem_output = torch.rand(batch_size, output_dim)",
                "b = ro * b + (1 - ro) * spike", "B = b_j0 + beta * b",
                "mem = mem * alpha + (1 - alpha) * R_m * inputs - B * spike * dt", "inputs_ = mem - B",
                "mem = mem * alpha + (1. - alpha) * R_m * inputs", "hidden_dim = [128,128]", "seq_dim = 250",
                "if ts_acc > best_accuracy and accuracy > 80:")
LIMIT = 200
OUTPUTS = ("digits", "draws", "mean_accuracy", "sd_accuracy", "min_accuracy", "max_accuracy", "zero_start_accuracy",
           "unseen_speakers", "seen_speakers", "name_label_gap", "script_log", "spikes_kept", "controls",
           "control_detail", "conditions_met", "conditions_total", "test_passed")


class Refused(Exception):
    pass


def input_bytes(inputs, key):
    name, sha = INPUTS[key]
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    if hashlib.sha256(data).hexdigest() != sha:
        raise Refused(f"{name}: its SHA-256 is not the committed one")
    return data


# ---------------------------------------------------------------- the network's archive, read safely

class Stand:
    """Stands in for a PyTorch module: keeps the state the archive gives it, runs nothing."""

    def __init__(self, *args):
        self.args = args
        self.state = None

    def __setstate__(self, state):
        self.state = state


def read_archive(data):
    """{name: float64 array} from a PyTorch zip archive, through a restricted unpickler."""
    z = zipfile.ZipFile(io.BytesIO(data))
    names = z.namelist()
    prefix = names[0].split("/")[0]
    storages = {}

    def rebuild_tensor(storage, offset, size, stride, *rest):
        if len(size) == 0:
            return np.array(storage[offset], dtype=np.float64)
        need = offset + sum((n - 1) * s for n, s in zip(size, stride)) + 1
        if need > len(storage):
            raise Refused("a tensor reaches past its storage")
        view = np.lib.stride_tricks.as_strided(storage[offset:], shape=tuple(size),
                                               strides=tuple(s * storage.itemsize for s in stride))
        return np.array(view, dtype=np.float64)

    def rebuild_parameter(data, requires_grad, hooks):
        return data

    allowed = {("collections", "OrderedDict"): collections.OrderedDict, ("__builtin__", "set"): set,
               ("builtins", "set"): set, ("torch._utils", "_rebuild_tensor_v2"): rebuild_tensor,
               ("torch._utils", "_rebuild_parameter"): rebuild_parameter, ("torch", "FloatStorage"): "float32",
               ("__main__", "RNN_custom"): Stand, ("torch.nn.modules.linear", "Linear"): Stand,
               ("torch.nn.modules.dropout", "Dropout"): Stand}

    class Restricted(pickle.Unpickler):
        def find_class(self, module, name):
            if (module, name) not in allowed:
                raise Refused(f"the archive names {module}.{name}, which is not admitted")
            return allowed[(module, name)]

        def persistent_load(self, pid):
            if not (isinstance(pid, tuple) and len(pid) == 5 and pid[0] == "storage" and pid[1] == "float32"):
                raise Refused(f"a storage not understood: {pid!r}")
            key = str(pid[2])
            if not re.fullmatch(r"\d+", key):
                raise Refused(f"a storage key not understood: {key!r}")
            if key not in storages:
                raw = z.read(f"{prefix}/data/{key}")
                storages[key] = np.frombuffer(raw, dtype="<f4")
                if len(storages[key]) != int(pid[4]):
                    raise Refused(f"storage {key}: {len(storages[key])} values, not {pid[4]}")
            return storages[key]

    model = Restricted(io.BytesIO(z.read(f"{prefix}/data.pkl"))).load()
    if not isinstance(model, Stand) or not isinstance(model.state, dict):
        raise Refused("the archive does not hold a module")
    params = {k: v for k, v in model.state["_parameters"].items()}
    for name, mod in model.state["_modules"].items():
        if name == "dp":
            continue
        for k, v in mod.state["_parameters"].items():
            params[f"{name}.{k}"] = v
    if {k: tuple(np.shape(v)) for k, v in params.items()} != SHAPES:
        raise Refused(f"the network's parameters are not the expected ones: {sorted(params)}")
    return {k: np.asarray(v, dtype=np.float64) for k, v in params.items()}


# ---------------------------------------------------------------- the digits (rule 1)

def read_shd(data):
    import h5py
    with h5py.File(io.BytesIO(gzip.decompress(data)), "r") as f:
        return list(f["spikes/times"][:]), list(f["spikes/units"][:]), f["labels"][:].astype(np.int64), \
            f["extra/speaker"][:].astype(np.int64)


def edges():
    return np.array([i * DT for i in range(BINS)]).astype(np.float16)


def binarise(times, units):
    """(digits, 250, 700) uint8, and the spikes kept of all."""
    e = edges()
    X = np.zeros((len(times), BINS, CHANNELS), dtype=np.uint8)
    kept = total = 0
    for k, (t, u) in enumerate(zip(times, units)):
        t = np.asarray(t, dtype=np.float16)
        u = np.asarray(u, dtype=np.int64)
        if np.any(u < 0) or np.any(u >= CHANNELS):
            raise Refused(f"digit {k}: a unit outside 0 to 699")
        b = np.searchsorted(e, t, side="left")
        keep = (b < BINS) & (u > 0)
        X[k, b[keep], CHANNELS - u[keep]] = 1
        kept += int(keep.sum())
        total += len(t)
    return X, kept, total


def binarise_slow(t, u):
    """Rule 1 as the generator states it, spike by spike, for one digit (a control)."""
    t = list(np.asarray(t, dtype=np.float16))
    u = list(np.asarray(u, dtype=np.int64))
    img = np.zeros((BINS, CHANNELS), dtype=np.uint8)
    for i in range(BINS):
        edge = np.float16(i * DT)
        take = {j for j in range(len(t)) if t[j] <= edge}
        for j in take:
            if u[j] > 0:
                img[i, CHANNELS - u[j]] = 1
        t = [x for j, x in enumerate(t) if j not in take]
        u = [x for j, x in enumerate(u) if j not in take]
    return img


# ---------------------------------------------------------------- the network (rule 2)

def starts(rng, n):
    return rng.random((n, HIDDEN)), rng.random((n, HIDDEN)), rng.random((n, CLASSES))


def forward(p, X, m1, m2, mo):
    """The summed readout (digits, 20) for inputs X (digits, steps, 700) from initial potentials m1, m2, mo."""
    n, steps, _ = X.shape
    a1, r1 = np.exp(-1.0 / p["tau_m_h1"]), np.exp(-1.0 / p["tau_adp_h1"])
    a2, r2 = np.exp(-1.0 / p["tau_m_h2"]), np.exp(-1.0 / p["tau_adp_h2"])
    ao = np.exp(-1.0 / p["tau_m_o"])
    m1, m2, mo = m1.copy(), m2.copy(), mo.copy()
    s1, s2 = np.zeros((n, HIDDEN)), np.zeros((n, HIDDEN))
    b1, b2 = np.full((n, HIDDEN), B_J0), np.full((n, HIDDEN), B_J0)
    out = np.zeros((n, CLASSES))
    for t in range(steps):
        x = X[:, t, :].astype(np.float64)
        h = x @ p["i_2_h1.weight"].T + p["i_2_h1.bias"] + s1 @ p["h1_2_h1.weight"].T + p["h1_2_h1.bias"]
        b1 = r1 * b1 + (1 - r1) * s1
        big1 = B_J0 + BETA * b1
        m1 = m1 * a1 + (1 - a1) * h - big1 * s1
        s1 = (m1 - big1 > 0).astype(np.float64)
        h2 = s1 @ p["h1_2_h2.weight"].T + p["h1_2_h2.bias"] + s2 @ p["h2_2_h2.weight"].T + p["h2_2_h2.bias"]
        b2 = r2 * b2 + (1 - r2) * s2
        big2 = B_J0 + BETA * b2
        m2 = m2 * a2 + (1 - a2) * h2 - big2 * s2
        s2 = (m2 - big2 > 0).astype(np.float64)
        mo = mo * ao + (1 - ao) * (s2 @ p["h2o.weight"].T + p["h2o.bias"])
        if t > START:
            e = np.exp(mo - mo.max(axis=1, keepdims=True))
            out += e / e.sum(axis=1, keepdims=True)
    return out


def forward_one(p, x, m1, m2, mo):
    """Rule 2 for a single digit, unit by unit in plain Python loops over the matrices' rows (a control)."""
    def lin(W, c, v):
        return np.array([sum(W[i, j] * v[j] for j in np.nonzero(v)[0]) + c[i] for i in range(W.shape[0])])
    s1, s2 = np.zeros(HIDDEN), np.zeros(HIDDEN)
    b1, b2 = np.full(HIDDEN, B_J0), np.full(HIDDEN, B_J0)
    m1, m2, mo = m1.copy(), m2.copy(), mo.copy()
    out = np.zeros(CLASSES)
    for t in range(x.shape[0]):
        h = lin(p["i_2_h1.weight"], p["i_2_h1.bias"], x[t].astype(np.float64)) + lin(p["h1_2_h1.weight"], p["h1_2_h1.bias"], s1)
        b1 = np.exp(-1.0 / p["tau_adp_h1"]) * b1 + (1 - np.exp(-1.0 / p["tau_adp_h1"])) * s1
        a = np.exp(-1.0 / p["tau_m_h1"])
        m1 = m1 * a + (1 - a) * h - (B_J0 + BETA * b1) * s1
        s1 = (m1 - (B_J0 + BETA * b1) > 0).astype(np.float64)
        h2 = lin(p["h1_2_h2.weight"], p["h1_2_h2.bias"], s1) + lin(p["h2_2_h2.weight"], p["h2_2_h2.bias"], s2)
        b2 = np.exp(-1.0 / p["tau_adp_h2"]) * b2 + (1 - np.exp(-1.0 / p["tau_adp_h2"])) * s2
        a = np.exp(-1.0 / p["tau_m_h2"])
        m2 = m2 * a + (1 - a) * h2 - (B_J0 + BETA * b2) * s2
        s2 = (m2 - (B_J0 + BETA * b2) > 0).astype(np.float64)
        a = np.exp(-1.0 / p["tau_m_o"])
        mo = mo * a + (1 - a) * lin(p["h2o.weight"], p["h2o.bias"], s2)
        if t > START:
            e = np.exp(mo - mo.max())
            out += e / e.sum()
    return out


def accuracy(out, labels, mask=None):
    hit = out.argmax(axis=1) == labels
    if mask is not None:
        hit = hit[mask]
    return 100.0 * float(hit.mean())


def rng_of(seed_hex, label):
    return np.random.default_rng(int.from_bytes(hashlib.sha256(bytes.fromhex(seed_hex) + b"|srnn/" +
                                                               label.encode("ascii")).digest()[:8], "big"))


# ---------------------------------------------------------------- the script, as text (rule 5)

LOG = re.compile(r"#\s*epoch:\s+(\d+)\s+\.\s+Loss:\s+\S+\s+\.\s+Tr Accuracy:\s+([0-9.]+)\s+\.\s+Ts Accuracy:\s+([0-9.]+)")


def read_script(text):
    missing = [f for f in SCRIPT_FACTS if f not in text]
    if missing:
        raise Refused(f"the script does not say what this module takes from it: {missing}")
    log = [(int(e), float(tr), float(ts)) for e, tr, ts in LOG.findall(text)]
    if not log:
        raise Refused("the script's log was not found")
    return log


# ---------------------------------------------------------------- the run

def conditions(mean):
    return {"mean accuracy at least 90.35% (the paper's 90.4%)": mean >= ROUNDED,
            "above the Bi-LSTM's 87.2%": mean > BILSTM,
            "above the best earlier SNN's 82.7%": mean > BEST_SNN}


def controls(p, X, labels, seed_hex, times, units):
    out = {}
    bad = io.BytesIO()
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("archive/data.pkl", pickle.dumps(collections.Counter(), protocol=2))
    try:
        read_archive(bad.getvalue())
        out["unpickler"] = ("read a Counter", False)
    except Refused:
        out["unpickler"] = ("refused a Counter", True)
    rng = rng_of(seed_hex, "draw/1")
    m1, m2, mo = starts(rng, X.shape[0])
    pick = sorted(rng_of(seed_hex, "control/pick").choice(X.shape[0], 8, replace=False).tolist())
    fast = forward(p, X[pick], m1[pick], m2[pick], mo[pick])
    worst = max(float(np.max(np.abs(forward_one(p, X[k], m1[k], m2[k], mo[k]) - fast[i]))) for i, k in enumerate(pick))
    out["step by step"] = (f"8 digits, max diff {worst:.1e}", worst < 1e-9)
    slow_same = sum(int(np.array_equal(binarise_slow(times[k], units[k]), X[k])) for k in pick[:4])
    out["bins"] = (f"{slow_same} of 4 digits", slow_same == 4)
    perm = rng_of(seed_hex, "control/permute").permutation(labels)
    full = forward(p, X, *starts(rng_of(seed_hex, "draw/1"), X.shape[0]))
    chance = accuracy(full, perm)
    out["permuted labels"] = (f"{chance:.2f}%", chance < 10)
    empty = forward(p, np.zeros((16, BINS, CHANNELS), dtype=np.uint8), *starts(rng_of(seed_hex, "control/empty"), 16))
    answers = len(set(empty.argmax(axis=1).tolist()))
    out["empty input"] = (f"{answers} answer for 16", answers == 1)
    return out, full


def run(seed_hex, inputs="inputs", results="results", draws=DRAWS):
    p = read_archive(input_bytes(inputs, "model"))
    log = read_script(input_bytes(inputs, "script").decode("utf-8"))
    times, units, labels, speakers = read_shd(input_bytes(inputs, "shd"))
    X, kept, total = binarise(times, units)
    ctl, first = controls(p, X, labels, seed_hex, times, units)
    failed = [k for k, (_, ok) in ctl.items() if not ok]
    if failed:
        raise Refused(f"the checker is not to be trusted: controls failed {failed}: {ctl}")
    accs, unseen, seen = [], [], []
    mask_unseen = np.isin(speakers, UNSEEN)
    for k in range(1, draws + 1):
        out = first if k == 1 else forward(p, X, *starts(rng_of(seed_hex, f"draw/{k}"), X.shape[0]))
        accs.append(accuracy(out, labels))
        unseen.append(accuracy(out, labels, mask_unseen))
        seen.append(accuracy(out, labels, ~mask_unseen))
    zero = accuracy(forward(p, X, np.zeros((X.shape[0], HIDDEN)), np.zeros((X.shape[0], HIDDEN)),
                            np.zeros((X.shape[0], CLASSES))), labels)
    mean = float(np.mean(accs))
    cond = conditions(mean)
    ts = [x[2] for x in log]
    best = max(log, key=lambda x: x[2])
    late = [x[2] for x in log if x[0] >= 10]
    values = {
        "digits": int(X.shape[0]), "draws": draws, "mean_accuracy": round(mean, 3),
        "sd_accuracy": round(float(np.std(accs, ddof=1)), 3) if draws > 1 else 0.0,
        "min_accuracy": round(min(accs), 3), "max_accuracy": round(max(accs), 3), "zero_start_accuracy": round(zero, 3),
        "unseen_speakers": f"{np.mean(unseen):.2f}% of {int(mask_unseen.sum())} digits (speakers 4 and 5)",
        "seen_speakers": f"{np.mean(seen):.2f}% of {int((~mask_unseen).sum())} digits",
        "name_label_gap": round(mean - LABEL, 3),
        "script_log": (f"{len(log)} epochs, test accuracy {min(ts):.1f} to {max(ts):.2f}, best at epoch {best[0]}; "
                       f"epochs 10 on average {np.mean(late):.2f}"),
        "spikes_kept": f"{kept} of {total}",
        "controls": f"{len(ctl) - len(failed)} of {len(ctl)}",
        "control_detail": "; ".join(f"{k}: {v[0]}" for k, v in ctl.items()),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"values": values, "conditions": cond, "accuracies": accs, "unseen": unseen, "seen": seen,
              "controls": {k: [str(v[0]), v[1]] for k, v in ctl.items()}, "script_log": log}
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
        sys.exit(f"srnn: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
