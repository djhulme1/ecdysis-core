#!/usr/bin/env python3
"""Diehl & Cook (2015): the authors' released network at 400 and 100 neurons, trained and tested, in C.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:768d604961e68bc0) is from Diehl & Cook,
"Unsupervised learning of digit recognition using spike-timing-dependent plasticity", Frontiers in Computational
Neuroscience 9:99 (2015): "Also, the performance of our network scales well with the number of neurons used and shows
similar performance for four different learning rules, indicating robustness of the full combination of mechanisms,
which suggests applicability in heterogeneous biological neural networks."

Its registered test: refuted if, with the network, rule and parameters of the authors' released code (stdp-mnist at
d527ca3: triplet STDP with weight normalisation), a 400-neuron network trained as it trains it (three passes of the
60,000 training digits, from initial weights drawn as its generator draws them) scores under 85% on the 10,000 test
digits, or under 2 points (half the paper's 82.9% to 87.0%) above a 100-neuron network built and run the same way,
trained on 40,000 digits, its threshold step scaled by 100/400; classes assigned from the training digits.

The C program (stdp/dcnet.c, compiled here with gcc -O2 -ffp-contract=off) is the released script's network written
afresh: its header states every step. This module reads the inputs, each checked against its SHA-256: MNIST's four
files (read as data), the authors' main script and connection generator (read as text only: every setting the C
program takes from them must appear in them verbatim; neither is run), and the released trained weights and thresholds
(NumPy arrays of float64, parsed here; nothing in them is run). Every rule below was fixed before any seed existed;
rule 4 was added after the first receipt (6d2aeda8..., inconclusive), whose sealed 400-neuron training ran away.

1. The digits: MNIST's idx files, as the script reads them (pixels 0 to 255; the C program makes rates of pixel / 8
   times the intensity).
2. Each network as the generator builds it: input weights (u + 0.01) x 0.3, u uniform on [0, 1) (the generator's
   np.random.random), drawn input by input, neuron by neuron; delays uniform on [0, 10 ms), as whole steps of 0.5 ms
   (d / dt truncated, so 0 to 19); inhibition 10.4 one-to-one and 17.0 to every other excitatory neuron. Draws come
   from xoshiro256** seeded by splitmix64 with the first 8 bytes of SHA-256(the seed's bytes || "|stdp/" || a label),
   one stream per label; each run of the C program gets its own stream for its input spikes.
3. Training, as the script trains (learning on, thresholds starting at 20 mV): the 400-neuron network on the 60,000
   training digits three times in order (the script's num_examples = 60000 * 3); the 100-neuron network on the first
   40,000 (the paper's 100-neuron run), its threshold step 0.05 x 100/400 = 0.0125 mV, the registered adaptation.
4. Draws. A run of the C program runs away when one presentation draws more than 10 spikes per excitatory neuron or
   leaves a value not finite; the program then stops and says at which digit (dcnet.c's header says why: the released
   code's Euler step is unstable under the inhibition a volley of excitatory spikes calls up). Each network is drawn
   in pairs (its weights, delays and input spikes from streams labelled by size and draw), the two draws of a pair
   trained at once. A draw counts if its training and both its recordings (rule 5) run without a runaway; the test
   reads the first draw that counts, in order, and the next that counts, if any, is reported beside it. If both draws
   of the first pair run away, a second pair (draws 3 and 4) is made; if all four run away, the check stops and says
   so, with no verdict. The released network's recordings (rule 7) are redrawn one at a time, by their delays, up to
   three times.
5. Classes and accuracy, as the paper (and the released evaluation script, given the training digits) take them: each
   trained network, learning off and thresholds fixed, is shown the 60,000 training digits once; a neuron's class is the
   digit with its highest mean count (strictly highest, from 0 up; a neuron that never fires has none); each of the
   10,000 test digits, shown once to the same network, is put in the class whose neurons' mean count is highest (ties
   to the higher class, as the script's reversed argsort gives them). Accuracy is the percentage put in their own class.
6. The test: the 400-neuron network scores at least 85%, and at least 2 points above the 100-neuron network (each the
   draw rule 4 takes). test_passed is 1 if both hold.
7. Beside the test: the other draws' accuracies; every runaway (size, draw, run, digit); the released trained network
   (weights/XeAe.npy and theta_A.npy) taken through rule 5 with fresh delays, and also with classes assigned on the
   test digits themselves, as the readme's 91.56% was (the readme calls that bad practice; the paper did not do it);
   the trained 400-neuron network scored that way too; neurons left without a class; how often a digit drew under 5
   spikes and was shown again; the thresholds after training.
8. Controls, which must all pass or the run stops: the digits' counts per class are MNIST's published ones; a Python
   reference written apart from the C program, with the same streams, gives byte for byte the same output on three
   small jobs (8 neurons and 3 digits, learning and not; and 200 neurons whose volley runs away); and classes
   assigned from shuffled training labels put the 400-neuron network's test digits in their own class less than 20%
   of the time.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
"""

import array
import gzip
import hashlib
import json
import math
import os
import re
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "dcnet.c")
M64 = (1 << 64) - 1

INPUTS = {
    "train_x": ("train-images-idx3-ubyte.gz", "440fcabf73cc546fa21475e81ea370265605f56be210a4024d2ca8f203523609"),
    "train_y": ("train-labels-idx1-ubyte.gz", "3552534a0a558bbed6aed32b30c495cca23d567ec52cac8be1a0730e8010255c"),
    "test_x": ("t10k-images-idx3-ubyte.gz", "8d422c7b0a1c1c79245a5bcf07fe86e33eeafee792b84584aec276f5a2dbc4e6"),
    "test_y": ("t10k-labels-idx1-ubyte.gz", "f7ae60f92e00ec6debd23a6088c31dbd2371eca3ffa0defaefb259924204aec6"),
    "script": ("Diehl_Cook_spiking_MNIST.py", "cd4017b820a405d5c829273994b2ee3b6fa8c0d936dc4a26a17af0d6b724705f"),
    "generator": ("Diehl_Cook_random_conn_generator.py", "2390a3b6754775a21a87ea1f9c5fd49577219a785e0da3f85648fcaeaf753637"),
    "weights": ("pretrained_XeAe.npy", "b704c770763d487c3defc912560beb5252668577b14658bdae4fd15ca1cc0ace"),
    "theta": ("pretrained_theta_A.npy", "9f5bcf6794bb691b3f9d349c01dfecc89883557d426a9b9ee71b7f49bae6b476"),
}
TRAIN_COUNTS = (5923, 6742, 5958, 6131, 5842, 5421, 5918, 6265, 5851, 5949)
TEST_COUNTS = (980, 1135, 1032, 1010, 982, 892, 958, 1028, 974, 1009)
NIN, ND, PRES, REST = 784, 21, 700, 300
THETA_PLUS, THETA_START = 0.05, 20.0
NETS = {"400": {"ne": 400, "train": 60_000, "passes": 3, "theta_plus": THETA_PLUS},
        "100": {"ne": 100, "train": 40_000, "passes": 1, "theta_plus": THETA_PLUS * 100 / 400}}
FLOOR, GAIN = 85.0, 2.0
CHANCE_LINE = 20.0
SCRIPT_FACTS = (
    "defaultclock = b.Clock(dt=0.5*b.ms)", "num_examples = 60000 * 3", "n_input = 784",
    "single_example_time =   0.35 * b.second", "resting_time = 0.15 * b.second", "v_rest_e = -65. * b.mV",
    "v_rest_i = -60. * b.mV", "v_reset_e = -65. * b.mV", "v_reset_i = -45. * b.mV", "v_thresh_e = -52. * b.mV",
    "v_thresh_i = -40. * b.mV", "refrac_e = 5. * b.ms", "refrac_i = 2. * b.ms", "weight['ee_input'] = 78.",
    "delay['ee_input'] = (0*b.ms,10*b.ms)", "input_intensity = 2.", "tc_pre_ee = 20*b.ms", "tc_post_1_ee = 20*b.ms",
    "tc_post_2_ee = 40*b.ms", "nu_ee_pre =  0.0001", "nu_ee_post = 0.01", "wmax_ee = 1.0", "tc_theta = 1e7 * b.ms",
    "theta_plus_e = 0.05 * b.mV", "scr_e = 'v = v_reset_e; theta += theta_plus_e; timer = 0*ms'",
    "offset = 20.0*b.mV", "v_thresh_e = '(v>(theta - offset + ' + str(v_thresh_e) + ')) * (timer>refrac_e)'",
    "dv/dt = ((v_rest_e - v) + (I_synE+I_synI) / nS) / (100*ms)  : volt",
    "I_synE = ge * nS *         -v                           : amp",
    "I_synI = gi * nS * (-100.*mV-v)                          : amp",
    "dge/dt = -ge/(1.0*ms)                                   : 1", "dgi/dt = -gi/(2.0*ms)                                  : 1",
    "neuron_eqs_e += '\\n  dtheta/dt = -theta / (tc_theta)  : volt'",
    "dv/dt = ((v_rest_i - v) + (I_synE+I_synI) / nS) / (10*ms)  : volt",
    "I_synI = gi * nS * (-85.*mV-v)                          : amp",
    "eqs_stdp_pre_ee = 'pre = 1.; w -= nu_ee_pre * post1'",
    "eqs_stdp_post_ee = 'post2before = post2; w += nu_ee_post * pre * post2before; post1 = 1.; post2 = 1.'",
    "neuron_groups[name+'e'].v = v_rest_e - 40. * b.mV", "neuron_groups[name+'i'].v = v_rest_i - 40. * b.mV",
    "neuron_groups['e'].theta = np.ones((n_e)) * 20.0*b.mV", "colFactors = weight['ee_input']/colSums",
    "rates = training['x'][j%60000,:,:].reshape((n_input)) / 8. *  input_intensity",
    "if np.sum(current_spike_count) < 5:", "input_intensity += 1", "input_intensity = start_input_intensity",
    "b.run(single_example_time, report='text')", "b.run(resting_time)", "wmin=0., wmax= wmax_ee",
    "neuron_groups['e'] = b.NeuronGroup(n_e*len(population_names), neuron_eqs_e, threshold= v_thresh_e, "
    "refractory= refrac_e, reset= scr_e,",
    "neuron_groups['i'] = b.NeuronGroup(n_i*len(population_names), neuron_eqs_i, threshold= v_thresh_i, "
    "refractory= refrac_i, reset= v_reset_i,",
)
GENERATOR_FACTS = ("weight['ee_input'] = 0.3", "weight['ei'] = 10.4", "weight['ie'] = 17.0",
                   "weightMatrix = np.random.random((nInput, nE)) + 0.01", "weightMatrix *= weight['ee_input']",
                   "weightList = [(i, i, weight['ei']) for i in xrange(nE)]", "weightMatrix *= weight['ie']",
                   "weightMatrix[i,i] = 0", "nE = 400")
LIMIT = 200
OUTPUTS = ("acc_400", "acc_100", "gain", "acc_400_other", "acc_100_other", "draws", "runaways", "acc_released",
           "acc_released_test_classes", "acc_400_test_classes", "unassigned", "repeats", "theta_400", "theta_100",
           "script_facts", "controls", "control_detail", "conditions_met", "conditions_total", "test_passed")
RUNAWAY = 10          # rule 4: spikes per excitatory neuron in one presentation, as dcnet.c
MAX_DRAWS = {"400": 4, "100": 4, "released": 3}


class Refused(Exception):
    pass


def input_bytes(inputs, key):
    name, sha = INPUTS[key]
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    if hashlib.sha256(data).hexdigest() != sha:
        raise Refused(f"{name}: its SHA-256 is not the committed one")
    return data


def seed_of(seed_hex, label):
    return int.from_bytes(hashlib.sha256(bytes.fromhex(seed_hex) + b"|stdp/" + label.encode("ascii")).digest()[:8], "big")


class Xoshiro:
    """xoshiro256** seeded by splitmix64, as dcnet.c."""

    def __init__(self, seed):
        self.s = []
        z = seed
        for _ in range(4):
            z = (z + 0x9E3779B97F4A7C15) & M64
            w = z
            w = ((w ^ (w >> 30)) * 0xBF58476D1CE4E5B9) & M64
            w = ((w ^ (w >> 27)) * 0x94D049BB133111EB) & M64
            self.s.append(w ^ (w >> 31))

    def next(self):
        s = self.s
        x = (s[1] * 5) & M64
        result = ((((x << 7) | (x >> 57)) & M64) * 9) & M64
        t = (s[1] << 17) & M64
        s[2] ^= s[0]
        s[3] ^= s[1]
        s[1] ^= s[2]
        s[0] ^= s[3]
        s[2] ^= t
        s[3] = ((s[3] << 45) | (s[3] >> 19)) & M64
        return result

    def unif(self):
        return (self.next() >> 11) * (1.0 / 9007199254740992.0)


# ---------------------------------------------------------------- the inputs (rules 1 and 2)

def read_idx(data):
    raw = gzip.decompress(data)
    magic = int.from_bytes(raw[:4], "big")
    if magic == 2051:
        n, rows, cols = (int.from_bytes(raw[i:i + 4], "big") for i in (4, 8, 12))
        if (rows, cols) != (28, 28) or len(raw) != 16 + n * 784:
            raise Refused("an image file is not of 28 x 28 digits as its header says")
        return raw[16:]
    if magic == 2049:
        n = int.from_bytes(raw[4:8], "big")
        if len(raw) != 8 + n or max(raw[8:]) > 9:
            raise Refused("a label file does not hold digits 0 to 9 as its header says")
        return raw[8:]
    raise Refused(f"not an idx file of images or labels (magic {magic})")


def counts_of(labels):
    c = [0] * 10
    for y in labels:
        c[y] += 1
    return tuple(c)


def read_npy(data):
    """A little-endian float64 NumPy array, version 1: (shape, values). Anything else is refused."""
    if data[:6] != b"\x93NUMPY" or data[6:8] != b"\x01\x00":
        raise Refused("not a version 1 .npy file")
    n = int.from_bytes(data[8:10], "little")
    head = data[10:10 + n].decode("latin1")
    m = re.fullmatch(r"\{'descr': '<f8', 'fortran_order': False, 'shape': \(([0-9, ]*)\), \}\s*", head)
    if not m:
        raise Refused(f"an .npy header not of plain float64: {head!r}")
    shape = tuple(int(x) for x in m.group(1).replace(" ", "").split(",") if x)
    count = 1
    for d in shape:
        count *= d
    body = data[10 + n:]
    if len(body) != 8 * count:
        raise Refused("an .npy body does not match its shape")
    return shape, struct.unpack(f"<{count}d", body)


def released(inputs):
    """The released 400-neuron network: weights (i ne + j) and thresholds in mV."""
    shape, vals = read_npy(input_bytes(inputs, "weights"))
    if shape != (NIN * 400, 3):
        raise Refused(f"the released weights have shape {shape}")
    w = [0.0] * (NIN * 400)
    seen = set()
    for k in range(0, len(vals), 3):
        i, j, x = vals[k], vals[k + 1], vals[k + 2]
        if not (i.is_integer() and j.is_integer() and 0 <= i < NIN and 0 <= j < 400 and 0.0 <= x <= 1.0):
            raise Refused(f"a released weight out of place: {(i, j, x)}")
        seen.add((int(i), int(j)))
        w[int(i) * 400 + int(j)] = x
    if len(seen) != NIN * 400:
        raise Refused("the released weights do not cover every synapse once")
    shape, th = read_npy(input_bytes(inputs, "theta"))
    if shape != (400,) or not all(0.0 <= t < 1.0 for t in th):
        raise Refused("the released thresholds are not 400 values in volts")
    return w, [t * 1000.0 for t in th]


def initial(seed_hex, ne, tag):
    """Rule 2: the generator's input weights and the script's delays, from their streams."""
    rw, rd = Xoshiro(seed_of(seed_hex, f"weights/{tag}")), Xoshiro(seed_of(seed_hex, f"delays/{tag}"))
    w = [(rw.unif() + 0.01) * 0.3 for _ in range(NIN * ne)]
    d = bytes(int(rd.unif() * 10.0 / 0.5) for _ in range(NIN * ne))
    return w, d


def read_facts(text, facts, what):
    missing = [f for f in facts if f not in text]
    if missing:
        raise Refused(f"the {what} does not say what this check takes from it: {missing}")
    return len(facts)


# ---------------------------------------------------------------- the C program's jobs

def build(results):
    os.makedirs(results, exist_ok=True)
    exe = os.path.join(results, "dcnet")
    subprocess.run(["gcc", "-O2", "-ffp-contract=off", "-std=gnu11", "-o", exe, SOURCE, "-lm"], check=True)
    return exe


def job_bytes(ne, imgs, learning, passes, theta_plus, seed, w, theta, delays):
    nex = len(imgs) // NIN
    return (b"DCJ1" + struct.pack("<4i", ne, nex, learning, passes) + struct.pack("<d", theta_plus)
            + struct.pack("<Q", seed) + struct.pack(f"<{NIN * ne}d", *w) + struct.pack(f"<{ne}d", *theta)
            + bytes(delays) + bytes(imgs))


def parse_output(data, learning):
    if data[:4] != b"DCO1":
        raise Refused("not an output of dcnet")
    ne, nex, passes = struct.unpack("<3i", data[4:16])
    o = 16
    w = struct.unpack(f"<{NIN * ne}d", data[o:o + 8 * NIN * ne])
    o += 8 * NIN * ne
    theta = struct.unpack(f"<{ne}d", data[o:o + 8 * ne])
    o += 8 * ne
    nc = 0 if learning else nex * ne
    counts = array.array("i")
    counts.frombytes(data[o:o + 4 * nc])
    o += 4 * nc
    reps = array.array("i")
    reps.frombytes(data[o:o + 4 * nex * passes])
    o += 4 * nex * passes
    steps = struct.unpack("<q", data[o:o + 8])[0]
    if o + 8 != len(data):
        raise Refused("an output longer than its header says")
    return {"ne": ne, "nex": nex, "w": list(w), "theta": list(theta), "counts": counts, "repeats": reps, "steps": steps}


def start(exe, job, results, name, progress=0):
    path = os.path.join(results, f"{name}.job")
    with open(path, "wb") as fh:
        fh.write(job)
    env = dict(os.environ, DCNET_PROGRESS=str(progress)) if progress else None
    return subprocess.Popen([exe, path, os.path.join(results, f"{name}.out")], env=env), path


def parse_runaway(data):
    if data[:4] != b"DCR1" or len(data) != 32:
        raise Refused("not a runaway report of dcnet")
    ne, digit, repeat = struct.unpack("<3i", data[4:16])
    spikes, steps = struct.unpack("<2q", data[16:32])
    return {"ne": ne, "digit": digit, "repeat": repeat, "spikes": spikes, "steps": steps}


def finish(handle, results, name, learning):
    """The run's output, or {"runaway": ...} when dcnet stopped it as a runaway (status 3; rule 4)."""
    proc, path = handle
    code = proc.wait()
    out_path = os.path.join(results, f"{name}.out")
    if code == 3:
        with open(out_path, "rb") as fh:
            out = {"runaway": parse_runaway(fh.read())}
    elif code != 0:
        raise Refused(f"dcnet stopped on {name} with status {code}")
    else:
        with open(out_path, "rb") as fh:
            out = parse_output(fh.read(), learning)
    os.remove(path)
    os.remove(out_path)
    return out


# ---------------------------------------------------------------- classes and accuracy (rule 5)

def assignments(counts, labels, ne):
    """The released evaluation script's get_new_assignments: -1 for a neuron that never fires."""
    n = len(labels)
    sums = [[0] * ne for _ in range(10)]
    seen = [0] * 10
    for e in range(n):
        y = labels[e]
        seen[y] += 1
        row = sums[y]
        base = e * ne
        for j in range(ne):
            c = counts[base + j]
            if c:
                row[j] += c
    out, best = [-1] * ne, [0.0] * ne
    for k in range(10):
        if seen[k] == 0:
            continue
        for j in range(ne):
            rate = sums[k][j] / seen[k]
            if rate > best[j]:
                best[j], out[j] = rate, k
    return out


def accuracy(counts, labels, assign, ne):
    """Percentage of digits put in their own class: the class whose neurons' mean count is highest, ties upwards."""
    members = [[j for j in range(ne) if assign[j] == k] for k in range(10)]
    right = 0
    for e in range(len(labels)):
        base = e * ne
        best_k, best = 0, None
        for k in range(10):
            rate = (sum(counts[base + j] for j in members[k]) / len(members[k])) if members[k] else 0
            if best is None or rate >= best:
                best_k, best = k, rate
        right += best_k == labels[e]
    return 100.0 * right / len(labels)


# ---------------------------------------------------------------- the Python reference (control, rule 8)

def reference(job):
    """dcnet.c's run, written apart in Python, for small jobs: the same output bytes."""
    ne, nex, learning, passes = struct.unpack("<4i", job[4:20])
    theta_plus = struct.unpack("<d", job[20:28])[0]
    seed = struct.unpack("<Q", job[28:36])[0]
    o = 36
    w = list(struct.unpack(f"<{NIN * ne}d", job[o:o + 8 * NIN * ne]))
    o += 8 * NIN * ne
    theta = list(struct.unpack(f"<{ne}d", job[o:o + 8 * ne]))
    o += 8 * ne
    delay = job[o:o + NIN * ne]
    o += NIN * ne
    img = job[o:o + nex * NIN]
    DT, TAB = 0.5, 8192
    KE, KI, DGE, DGI, DTH = DT / 100.0, DT / 10.0, 1.0 - DT / 1.0, 1.0 - DT / 2.0, 1.0 - DT / 1e7
    tpre = [math.exp(-float(k) * DT / 20.0) for k in range(TAB)]
    tp1 = [math.exp(-float(k) * DT / 20.0) for k in range(TAB)]
    tp2 = [math.exp(-float(k) * DT / 40.0) for k in range(TAB)]
    groups = [[[j for j in range(ne) if delay[i * ne + j] == d] for d in range(ND)] for i in range(NIN)]
    rng = Xoshiro(seed)
    ve, gee, gie = [-105.0] * ne, [0.0] * ne, [0.0] * ne
    vi, gei, gii = [-100.0] * ne, [0.0] * ne, [0.0] * ne
    blke, blki, clmi = [0] * ne, [0] * ne, [0] * ne
    last_arr, last_post = [-1] * (NIN * ne), [-1] * ne
    tot, prev = [0] * ne, [0] * ne
    hist = [[] for _ in range(ND)]

    def tr(tab, since, now):
        if since < 0:
            return 0.0
        k = now - since
        return tab[k] if k < TAB else 0.0

    def step(s, now_in):
        if learning:
            for j in range(ne):
                theta[j] = theta[j] * DTH
        for j in range(ne):
            v, ge, gi = ve[j], gee[j], gie[j]
            ve[j] = v + KE * ((-65.0 - v) + ge * (0.0 - v) + gi * (-100.0 - v))
            gee[j] = ge * DGE
            gie[j] = gi * DGI
        for j in range(ne):
            v, ge, gi = vi[j], gei[j], gii[j]
            vi[j] = v + KI * ((-60.0 - v) + ge * (0.0 - v) + gi * (-85.0 - v))
            gei[j] = ge * DGE
            gii[j] = gi * DGI
        spk_e = [j for j in range(ne) if blke[j] == 0 and ve[j] > theta[j] + -72.0]
        spk_i = [j for j in range(ne) if blki[j] == 0 and vi[j] > -40.0]
        hist[s % ND] = list(now_in)
        p1 = [tr(tp1, last_post[j], s) for j in range(ne)] if learning else None
        for d in range(ND):
            if s - d < 0:
                continue
            for i in hist[(s - d) % ND]:
                for j in groups[i][d]:
                    idx = i * ne + j
                    gee[j] += w[idx]
                    if learning:
                        last_arr[idx] = s
                        nw = w[idx] - 0.0001 * p1[j]
                        w[idx] = 0.0 if nw < 0.0 else nw
        for j in spk_e:
            gei[j] += 10.4
            if learning:
                p2 = tr(tp2, last_post[j], s)
                for i in range(NIN):
                    idx = i * ne + j
                    nw = w[idx] + 0.01 * tr(tpre, last_arr[idx], s) * p2
                    w[idx] = 1.0 if nw > 1.0 else nw
            last_post[j] = s
            tot[j] += 1
        for i in spk_i:
            for j in range(ne):
                if j != i:
                    gie[j] += 17.0
        for j in range(ne):
            if blke[j] > 0:
                blke[j] -= 1
            if blki[j] > 0:
                blki[j] -= 1
            if clmi[j] > 0:
                vi[j] = -45.0
                clmi[j] -= 1
        for j in spk_e:
            ve[j] = -65.0
            if learning:
                theta[j] += theta_plus
            blke[j] = 9
        for i in spk_i:
            vi[i] = -45.0
            blki[i] = 3
            clmi[i] = 4

    def presentation(px, intensity):
        spikes = [[] for _ in range(PRES)]
        for i in range(NIN):
            rate = float(px[i]) / 8.0 * float(intensity)
            p = rate * DT / 1000.0
            if p <= 0.0:
                continue
            if p >= 1.0:
                for t in range(PRES):
                    spikes[t].append(i)
                continue
            lq = math.log1p(-p)
            t = -1
            while True:
                u = 1.0 - rng.unif()
                g = math.floor(math.log(u) / lq)
                if g >= PRES:
                    break
                t += 1 + int(g)
                if t >= PRES:
                    break
                spikes[t].append(i)
        return spikes

    counts = array.array("i", [0] * (0 if learning else nex * ne))
    reps = array.array("i", [0] * (nex * passes))
    s = 0
    for ep in range(nex * passes):
        e = ep % nex
        intensity = 2
        while True:
            at_start = sum(tot)
            if learning:
                colsum = [0.0] * ne
                for i in range(NIN):
                    for j in range(ne):
                        colsum[j] += w[i * ne + j]
                for j in range(ne):
                    colsum[j] = 78.0 / colsum[j]
                for i in range(NIN):
                    for j in range(ne):
                        w[i * ne + j] *= colsum[j]
            spikes = presentation(img[e * NIN:(e + 1) * NIN], intensity)
            for t in range(PRES):
                step(s, spikes[t])
                s += 1
            total = sum(tot[j] - prev[j] for j in range(ne))
            ok = total >= 5
            if ok and not learning:
                for j in range(ne):
                    counts[e * ne + j] = tot[j] - prev[j]
            prev = list(tot)
            for _ in range(REST):
                step(s, [])
                s += 1
            drawn = sum(tot) - at_start
            if drawn > RUNAWAY * ne or not all(math.isfinite(x) for x in ve + gee + gie + vi + gei + gii + theta):
                return b"DCR1" + struct.pack("<3i", ne, ep, reps[ep]) + struct.pack("<2q", drawn, s)
            if ok:
                break
            intensity += 1
            reps[ep] += 1
    return (b"DCO1" + struct.pack("<3i", ne, nex, passes) + struct.pack(f"<{NIN * ne}d", *w)
            + struct.pack(f"<{ne}d", *theta) + counts.tobytes() + reps.tobytes() + struct.pack("<q", s))


def runaway_job(imgs, seed_hex):
    """200 neurons with equal weights and delays, learning off: the 50 with theta 20 mV fire together, their 50
    inhibitory partners take the others' gi to 850, over the 399 at which the Euler step is unstable, the overshoot
    makes the other 150 (theta 30 mV) fire, and the run runs away."""
    return job_bytes(200, imgs[:NIN], 0, 1, 0.0, seed_of(seed_hex, "in/reference/runaway"), [0.2] * (NIN * 200),
                     [20.0] * 50 + [30.0] * 150, bytes(NIN * 200))


def reference_agrees(exe, results, imgs, seed_hex):
    """Three small jobs through dcnet and through the reference: 8 neurons and 3 digits, learning and not, and the
    runaway job."""
    same = 0
    jobs = []
    for learning in (1, 0):
        w, d = initial(seed_hex, 8, f"reference/{learning}")
        jobs.append((f"reference{learning}", job_bytes(8, imgs[:3 * NIN], learning, 1, THETA_PLUS,
                                                       seed_of(seed_hex, f"in/reference/{learning}"), w,
                                                       [THETA_START] * 8, d), False))
    jobs.append(("reference_runaway", runaway_job(imgs, seed_hex), True))
    for name, job, runs_away in jobs:
        h = start(exe, job, results, name)
        h[0].wait()
        with open(os.path.join(results, f"{name}.out"), "rb") as fh:
            got = fh.read()
        os.remove(h[1])
        os.remove(os.path.join(results, f"{name}.out"))
        same += int(got == reference(job) and h[0].returncode == (3 if runs_away else 0)
                    and got.startswith(b"DCR1" if runs_away else b"DCO1"))
    return same


# ---------------------------------------------------------------- the run

def conditions(acc400, acc100):
    return {"the 400-neuron network scores at least 85%": acc400 >= FLOOR,
            "and at least 2 points above the 100-neuron network": acc400 - acc100 >= GAIN}


def shuffled(seed_hex, labels):
    """A seeded permutation of the training labels (Fisher-Yates)."""
    rng = Xoshiro(seed_of(seed_hex, "shuffle"))
    out = list(labels)
    for k in range(len(out) - 1, 0, -1):
        lim = M64 - (M64 % (k + 1))
        while True:
            x = rng.next()
            if x < lim:
                break
        m = x % (k + 1)
        out[k], out[m] = out[m], out[k]
    return out


ORDER = ("400", "100", "released")


def pick(statuses):
    """Rule 4: the first draw that counts, in order, and the next that counts (or None for either)."""
    clean = [k for k in sorted(statuses) if statuses[k] == "clean"]
    return (clean[0] if clean else None), (clean[1] if len(clean) > 1 else None)


def needs_another(statuses, tag):
    """Rule 4: the draws to make when every draw made so far has run away: the networks' next pair, the released
    network's next draw of delays; none past MAX_DRAWS."""
    if not statuses or not all(v == "ran away" for v in statuses.values()):
        return []
    top = max(statuses)
    return [k for k in range(top + 1, top + (1 if tag == "released" else 2) + 1) if k <= MAX_DRAWS[tag]]


def runaway_words(ran, n_train):
    """Every runaway, in a string of at most LIMIT characters."""
    if not ran:
        return "none"
    words = []
    for tag, k, r in ran:
        if r["run"] == "train":
            where = f"training, pass {r['digit'] // n_train[tag] + 1} digit {r['digit'] % n_train[tag]:,}"
        else:
            where = f"{r['run']} run, digit {r['digit']:,}"
        words.append(f"{tag} draw {k}: {where} ({r['spikes']:,} spikes)")
    text = "; ".join(words)
    if len(text) > LIMIT:
        text = f"{len(ran)}: " + "; ".join(f"{t}/{k} {r['run']} {r['digit']}" for t, k, r in ran)
    return text[:LIMIT]


def draws_words(status, used):
    return "; ".join(f"{tag}: " + ", ".join(f"{k} {'used' if k == used[tag] else status[tag][k]}"
                                            for k in sorted(status[tag])) for tag in ORDER)


def run(seed_hex, inputs="inputs", results="results", short=None, log=sys.stderr):
    """short: (training digits, assignment digits, test digits) for a trial; None for the registered run."""
    facts = read_facts(input_bytes(inputs, "script").decode("utf-8"), SCRIPT_FACTS, "script")
    facts += read_facts(input_bytes(inputs, "generator").decode("utf-8"), GENERATOR_FACTS, "generator")
    xtr, ytr = read_idx(input_bytes(inputs, "train_x")), read_idx(input_bytes(inputs, "train_y"))
    xte, yte = read_idx(input_bytes(inputs, "test_x")), read_idx(input_bytes(inputs, "test_y"))
    if (len(xtr), len(ytr), len(xte), len(yte)) != (60_000 * NIN, 60_000, 10_000 * NIN, 10_000):
        raise Refused("MNIST's files do not hold 60,000 and 10,000 digits")
    ctl = {"digits": ("counts per class as published", counts_of(ytr) == TRAIN_COUNTS and counts_of(yte) == TEST_COUNTS)}
    released_w, released_theta = released(inputs)
    exe = build(results)
    same = reference_agrees(exe, results, xtr, seed_hex)
    ctl["reference"] = (f"{same} of 3 small jobs byte for byte", same == 3)
    if not all(ok for _, ok in ctl.values()):
        raise Refused(f"the checker is not to be trusted: {ctl}")
    n_train = {k: v["train"] for k, v in NETS.items()}
    passes = {k: v["passes"] for k, v in NETS.items()}
    n_assign, n_test = 60_000, 10_000
    if short:
        n_train = {k: min(n_train[k], short[0]) for k in n_train}
        passes = {k: 1 for k in passes}
        n_assign, n_test = short[1], short[2]
    t0 = time.time()

    def say(msg):
        if log:
            print(f"stdp: {msg} ({time.time() - t0:.0f} s)", file=log, flush=True)

    # rule 4: the draws, two runs of the C program at a time; a draw's recordings go to the front of the queue
    draws, queue, running = {}, [], {}

    def add_draw(tag, k, front=False):
        if tag == "released":
            draws[(tag, k)] = {"ne": 400, "w": released_w, "theta": released_theta,
                               "d": initial(seed_hex, 400, f"{tag}/{k}")[1], "status": "recording"}
            tasks = [("assign", (tag, k)), ("test", (tag, k))]
        else:
            ne = NETS[tag]["ne"]
            w, d = initial(seed_hex, ne, f"{tag}/{k}")
            draws[(tag, k)] = {"ne": ne, "w": w, "theta": [THETA_START] * ne, "d": d, "status": "training"}
            tasks = [("train", (tag, k))]
        draws[(tag, k)].update({"trained": None, "rec": {}, "runaway": None})
        queue[0:0] = tasks if front else []
        queue.extend([] if front else tasks)

    def job_of(which, key):
        tag, k = key
        dr = draws[key]
        if which == "train":
            return job_bytes(dr["ne"], xtr[:n_train[tag] * NIN], 1, passes[tag], NETS[tag]["theta_plus"],
                             seed_of(seed_hex, f"in/train/{tag}/{k}"), dr["w"], dr["theta"], dr["d"])
        x, n = (xtr, n_assign) if which == "assign" else (xte, n_test)
        w, th = (dr["trained"]["w"], dr["trained"]["theta"]) if dr["trained"] else (dr["w"], dr["theta"])
        return job_bytes(dr["ne"], x[:n * NIN], 0, 1, 0.0, seed_of(seed_hex, f"in/{which}/{tag}/{k}"), w, th, dr["d"])

    def done(which, key, out):
        tag, k = key
        dr = draws[key]
        if "runaway" in out:
            if dr["status"] != "ran away":
                dr["status"], dr["runaway"] = "ran away", dict(out["runaway"], run=which)
                say(f"{tag} draw {k}: ran away in its {which} run at digit {out['runaway']['digit']}")
                for nxt in reversed(needs_another({kk: draws[(t, kk)]["status"] for (t, kk) in draws if t == tag}, tag)):
                    add_draw(tag, nxt, front=True)
            return
        if dr["status"] == "ran away":
            return
        if which == "train":
            dr["trained"], dr["status"] = out, "recording"
            queue[0:0] = [("assign", key), ("test", key)]
            say(f"{tag} draw {k}: trained")
        else:
            dr["rec"][which] = out
            say(f"{tag} draw {k}: recorded {which}")
            if len(dr["rec"]) == 2:
                dr["status"] = "clean"

    for tag in ("400", "100"):
        for k in (1, 2):
            add_draw(tag, k)
    add_draw("released", 1)
    while queue or running:
        while queue and len(running) < 2:
            which, key = queue.pop(0)
            if draws[key]["status"] == "ran away":
                continue
            name = f"{which}{key[0]}_{key[1]}"
            prog = 20_000 if which == "train" and key[0] == "400" else 0
            running[name] = (start(exe, job_of(which, key), results, name, progress=prog), which, key)
        fin = []
        while running and not fin:
            fin = sorted(n for n, (h, _, _) in running.items() if h[0].poll() is not None)
            if not fin:
                time.sleep(0.2)
        for name in fin:
            h, which, key = running.pop(name)
            done(which, key, finish(h, results, name, 1 if which == "train" else 0))

    status = {tag: {k: draws[(t, k)]["status"] for (t, k) in draws if t == tag} for tag in ORDER}
    used, other = {}, {}
    for tag in ORDER:
        used[tag], other[tag] = pick(status[tag])
    ran = [(t, k, draws[(t, k)]["runaway"]) for (t, k) in sorted(draws, key=lambda x: (ORDER.index(x[0]), x[1]))
           if draws[(t, k)]["runaway"]]
    ran_words = runaway_words(ran, n_train)
    if used["400"] is None or used["100"] is None:
        raise Refused(f"rule 4: every draw of a network ran away, so there is no verdict: {ran_words}")

    def rec(tag, k, which):
        return draws[(tag, k)]["rec"][which]

    ylab_tr, ylab_te = list(ytr[:n_assign]), list(yte[:n_test])

    def score(tag, k):
        ne = draws[(tag, k)]["ne"]
        a = assignments(rec(tag, k, "assign")["counts"], ylab_tr, ne)
        return a, accuracy(rec(tag, k, "test")["counts"], ylab_te, a, ne)

    acc, acc_te, unassigned = {}, {}, {}
    for tag in ORDER:
        k = used[tag]
        if k is None:
            continue
        a, acc[tag] = score(tag, k)
        unassigned[tag] = a.count(-1)
        if tag != "100":
            te = rec(tag, k, "test")["counts"]
            acc_te[tag] = accuracy(te, ylab_te, assignments(te, ylab_te, 400), 400)
    acc_other = {tag: score(tag, other[tag])[1] if other[tag] else None for tag in ("400", "100")}
    shuffled_acc = accuracy(rec("400", used["400"], "test")["counts"], ylab_te,
                            assignments(rec("400", used["400"], "assign")["counts"], shuffled(seed_hex, ylab_tr), 400),
                            400)
    ctl["shuffled labels"] = (f"under {CHANCE_LINE:.0f}%" if shuffled_acc < CHANCE_LINE else "at or over 20%",
                              shuffled_acc < CHANCE_LINE)
    failed = [k for k, (_, ok) in ctl.items() if not ok]
    if failed:
        raise Refused(f"the checker is not to be trusted: controls failed {failed}: {ctl} (shuffled {shuffled_acc:.2f}%)")
    cond = conditions(acc["400"], acc["100"])
    trained = {tag: draws[(tag, used[tag])]["trained"] for tag in ("400", "100")}
    rep = {f"train {tag}": sum(trained[tag]["repeats"]) for tag in ("400", "100")}
    rep.update({f"{which} {tag}": sum(rec(tag, used[tag], which)["repeats"]) for tag in ORDER if used[tag]
                for which in ("assign", "test")})
    none_rel = "every draw of its delays ran away"
    values = {
        "acc_400": round(acc["400"], 2), "acc_100": round(acc["100"], 2), "gain": round(acc["400"] - acc["100"], 2),
        "acc_400_other": round(acc_other["400"], 2) if acc_other["400"] is not None else "none: no second draw counts",
        "acc_100_other": round(acc_other["100"], 2) if acc_other["100"] is not None else "none: no second draw counts",
        "draws": draws_words(status, used), "runaways": ran_words,
        "acc_released": round(acc["released"], 2) if used["released"] else none_rel,
        "acc_released_test_classes": round(acc_te["released"], 2) if used["released"] else none_rel,
        "acc_400_test_classes": round(acc_te["400"], 2),
        "unassigned": "; ".join(f"{tag} {unassigned[tag]}" for tag in ORDER if tag in unassigned),
        "repeats": "; ".join(f"{k} {v}" for k, v in rep.items()),
        "theta_400": f"{min(trained['400']['theta']):.2f} to {max(trained['400']['theta']):.2f} mV",
        "theta_100": f"{min(trained['100']['theta']):.2f} to {max(trained['100']['theta']):.2f} mV",
        "script_facts": f"{facts} of {len(SCRIPT_FACTS) + len(GENERATOR_FACTS)}",
        "controls": f"{len(ctl) - len(failed)} of {len(ctl)}",
        "control_detail": "; ".join(f"{k}: {v[0]}" for k, v in ctl.items()),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"values": values, "conditions": cond, "accuracy": acc, "accuracy_other_draw": acc_other,
              "accuracy_test_classes": acc_te, "shuffled_accuracy": shuffled_acc, "unassigned": unassigned,
              "repeats": rep, "draws": {f"{t} {k}": draws[(t, k)]["status"] for (t, k) in draws},
              "used": used, "other": other,
              "runaways": [{"network": t, "draw": k, **r} for t, k, r in ran],
              "steps": {f"train {t} draw {k}": draws[(t, k)]["trained"]["steps"] for (t, k) in draws
                        if draws[(t, k)]["trained"]},
              "controls": {k: [str(v[0]), v[1]] for k, v in ctl.items()}, "short": short,
              "theta": {t: trained[t]["theta"] for t in trained}}
    os.remove(exe)
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
    short = None
    if len(sys.argv) == 5 and sys.argv[1] == "--short":
        short = tuple(int(x) for x in sys.argv[2:5])
    elif len(sys.argv) != 1:
        sys.exit("usage: check.py [--short TRAIN ASSIGN TEST]")
    try:
        out, _ = run(seed, short=short)
    except Refused as e:
        sys.exit(f"stdp: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
