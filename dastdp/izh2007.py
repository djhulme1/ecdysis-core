#!/usr/bin/env python3
"""Izhikevich's distal reward: dopamine-modulated STDP reinforcing one chosen synapse, in 50 seeded draws.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:69c2bbc168cef5a6) is from Izhikevich,
"Solving the distal reward problem through linkage of STDP and dopamine signaling", Cerebral Cortex 17(10), 2443-2452
(2007): "Here, we show how the conundrum is resolved by a model network of cortical spiking neurons with
spike-timing-dependent plasticity (STDP) modulated by dopamine (DA). Although STDP is triggered by nearly coincident
firing patterns on a millisecond timescale, slow kinetics of subsequent synaptic plasticity is sensitive to changes in
the extracellular DA concentration during the critical period of a few seconds." Its Results test the mechanism on one
synapse: "In 42 out of 50 experiments, the chosen synapse reached the maximal allowable value within 1-h period,
requiring only 40 +/- 8 reward"; of the other synapses, "none reach 4 mV".

Its registered test: refuted if, in the network, rule and parameters of the author's program daspnet.m, with the
paper's reward rule (a reward 1 to 3 s after each postsynaptic spike within 10 ms of a presynaptic spike at one chosen
excitatory-to-excitatory synapse, set to 0 at the start), fewer than 21 of 50 seeded draws, each with its own synapse,
see that synapse reach the 4 mV maximum within 3,600 s of model time while no other excitatory synapse reaches it.

The input is the author's program (inputs/daspnet.m, from https://www.izhikevich.org/publications/daspnet.m), checked
against its SHA-256 and read as data: it is MATLAB, which is not run here. dastdp/dastdp.c ports it statement by
statement (its header says how), and the run is refused unless the program holds every statement the port follows
(PROGRAM below; compared with comments and whitespace removed). Every rule here was fixed before any draw ran to its
hour: a pilot of 100 s of model time timed the port (about 70 s for each simulated hour) and read only its firing rates.

1. The port's departures from the program, and nothing else: its random numbers are its own (xoshiro256**, seeded by
   splitmix64), not MATLAB's; the chosen synapse is drawn by the seed (an excitatory neuron, then one of its synapses
   onto an excitatory neuron), as the paper chose a random one in each experiment, where the program fixes n1 = 1 and
   syn = 1; the coincidence interval is an argument; and nothing is plotted. It is compiled with the image's gcc at -O3
   (whose results a build at -O2 repeats exactly).
2. The draws: for the test, 50 seeds from the archive's seed (the first 8 bytes of SHA-256 of "<seed>:10:<i>", i = 1 to
   50, as an unsigned integer), each a new network, run for 3,600 s with the coincidence interval set to the paper's
   10 ms (by the program's own comparison, a spike of the postsynaptic neuron 1 to 9 ms after the presynaptic neuron's
   last spike; the program sets 20). Beside them, 50 more from "<seed>:20:<i>" with the program's 20 ms.
3. A draw succeeds if the chosen synapse reaches 4 mV within the hour and no other excitatory synapse reaches 4 mV at
   any time in the hour.
4. The test: at least 21 of the 50 test draws succeed (half the paper's 42). test_passed is 1 if it holds.
5. Beside, not counted, for each interval: the draws whose chosen synapse reaches 4 mV, with or without others; the
   rewards delivered before it does (mean and sd; the paper, 40 +/- 8) and the minutes it takes (median); the rewards
   in the first and the last 10 minutes (the paper: "the probability (frequency) of reward triples"); the draws in which
   other synapses reach 4 mV; the final excitatory weights (mean, and the share below 0.1 mV: the paper, "the majority
   is less than 0.1 mV"); and the firing rates (the paper: "around 1 Hz").

Controls (controls_passed counts those that hold): the program is the pinned file and holds every statement the port
follows; the port's self-test passes (MATLAB's assignment through repeated indices, the trace, the clipping, the random
numbers); the 100 seeds are distinct; every draw ran its 3,600 s; and the first test draw, run again, prints the same
line.

What it cannot check: the paper's own 50 runs, on MATLAB's random numbers, and whether they used the program's 20 ms or
the text's 10 ms; the paper's other experiments (classical conditioning, the shift of the dopamine response).

Writes results/outputs.json and results/detail.json. Run with: python3 dastdp/izh2007.py
"""

import concurrent.futures as cf
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT = ("daspnet.m", "33b92b5c74f7ac9abbcad1596aaf530ddae9ade4b93ffbb7030fe367d0f9d58b", 4189)
SOURCE = os.path.join(HERE, "dastdp.c")
PROGRAM = (
    "M=100;", "D=1;", "Ne=800;", "Ni=200;", "N=Ne+Ni;", "a=[0.02*ones(Ne,1);0.1*ones(Ni,1)];",
    "d=[8*ones(Ne,1);2*ones(Ni,1)];", "sm=4;", "post=ceil([N*rand(Ne,M);Ne*rand(Ni,M)]);",
    "s=[ones(Ne,M);-ones(Ni,M)];", "sd=zeros(N,M);", "delays{i,j}=M/D*(j-1)+(1:M/D);", "delays{i,1}=1:M;",
    "pre{i}=find(post==i&s>0);", "aux{i}=N*(D-1-ceil(ceil(pre{i}/N)/(M/D)))+1+mod(pre{i}-1,N);",
    "STDP=zeros(N,1001+D);", "v=-65*ones(N,1);", "u=0.2.*v;", "T=3600;", "DA=0;", "n2=post(n1,syn)",
    "s(n1,syn)=0;", "interval=20;", "n1f=-100;", "I=13*(rand(N,1)-0.5);", "fired=find(v>=30);", "v(fired)=-65;",
    "u(fired)=u(fired)+d(fired);", "STDP(fired,t+D)=0.1;",
    "sd(pre{fired(k)})=sd(pre{fired(k)})+STDP(N*t+aux{fired(k)});", "whilefirings(k,1)>t-D",
    "del=delays{firings(k,2),t-firings(k,1)+1};", "ind=post(firings(k,2),del);",
    "I(ind)=I(ind)+s(firings(k,2),del)';", "sd(firings(k,2),del)=sd(firings(k,2),del)-1.5*STDP(ind,t+D)';",
    "v=v+0.5*((0.04*v+5).*v+140-u+I);v=v+0.5*((0.04*v+5).*v+140-u+I);u=u+a.*(0.2*v-u);",
    "STDP(:,t+D+1)=0.95*STDP(:,t+D);", "DA=DA*0.995;", "if(mod(t,10)==0)",
    "s(1:Ne,:)=max(0,min(sm,s(1:Ne,:)+(0.002+DA)*sd(1:Ne,:)));", "sd=0.99*sd;",
    "ifany(fired==n1)n1f=[n1f,sec*1000+t];end", "ifany(fired==n2)n2f=[n2f,sec*1000+t];",
    "if(sec*1000+t-n1f(end)<interval)&(n2f(end)>n1f(end))rew=[rew,sec*1000+t+1000+ceil(2000*rand)];",
    "ifany(rew==sec*1000+t)DA=DA+0.5;", "STDP(:,1:D+1)=STDP(:,1001:1001+D);",
)
SECONDS = 3600
DRAWS = 50
TEST_INTERVAL, PROGRAM_INTERVAL = 10, 20
NEED = 21
PRINTED_REWARDS = (40, 8)
KEYS = {"seed": int, "seconds": int, "interval": int, "n1": int, "syn": int, "n2": int, "reached_ms": int,
        "rewards_before": int, "rewards_scheduled": int, "rewards_delivered": int, "rewards_first_600s": int,
        "rewards_last_600s": int, "final_weight": float, "others_reached": int, "others_at_max_end": int,
        "mean_weight": float, "share_below_0.1": float, "rate_e": float, "rate_i": float}
OUTPUTS = ("successes", "reached", "rewards_before_max", "minutes_to_max", "reward_rate", "others", "weights",
           "firing_rates", "successes_program_interval", "conditions_met", "conditions_total", "test_passed",
           "controls_passed", "controls_total")
LIMIT = 200


class Refused(Exception):
    pass


def normalise(matlab):
    """The program with its comments (% to the end of a line) and all its whitespace removed."""
    return re.sub(r"\s+", "", "\n".join(line.split("%", 1)[0] for line in matlab.split("\n")))


def read_program(inputs):
    name, sha, size = INPUT
    with open(os.path.join(inputs, name), "rb") as fh:
        data = fh.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha or len(data) != size:
        raise Refused(f"{name}: sha256 {got} ({len(data)} bytes), not the pinned {sha} ({size})")
    return data.decode("latin-1")


def check_program(matlab):
    flat = normalise(matlab)
    missing = [p for p in PROGRAM if p not in flat]
    if missing:
        raise Refused(f"the program does not hold, as the port follows it: {missing[0]!r}")
    return True


def seeds_of(seed, interval, n=DRAWS):
    return [int.from_bytes(hashlib.sha256(f"{seed}:{interval}:{i}".encode()).digest()[:8], "big") for i in range(1, n + 1)]


def parse(line):
    pairs = dict(p.split("=", 1) for p in line.split())
    if set(pairs) != set(KEYS):
        raise ValueError(f"unexpected fields: {sorted(set(pairs) ^ set(KEYS))}")
    return {k: KEYS[k](pairs[k]) for k in KEYS}


def success(draw):
    return draw["reached_ms"] >= 0 and draw["others_reached"] == 0


def conditions(successes):
    return {f"at least {NEED} of {DRAWS} draws reinforce the chosen synapse to 4 mV, and no other": successes >= NEED}


def compile_port(work):
    exe = os.path.join(work, "dastdp")
    subprocess.run(["gcc", "-O3", "-o", exe, SOURCE], check=True)
    return exe


def run_draw(exe, seed, seconds, interval):
    out = subprocess.run([exe, str(seed), str(seconds), str(interval)], capture_output=True, text=True, check=True)
    return out.stdout.strip()


def mean_sd(xs):
    if not xs:
        return "none"
    return f"{statistics.mean(xs):.1f} +/- {statistics.stdev(xs):.1f}" if len(xs) > 1 else f"{xs[0]:.1f}"


def summary(draws):
    hit = [d for d in draws if d["reached_ms"] >= 0]
    return {"reached": len(hit), "succeeded": sum(map(success, draws)),
            "rewards_before": mean_sd([d["rewards_before"] for d in hit]),
            "minutes": f"{statistics.median([d['reached_ms'] / 60000 for d in hit]):.1f}" if hit else "none",
            "first": statistics.median([d["rewards_first_600s"] for d in draws]),
            "last": statistics.median([d["rewards_last_600s"] for d in draws]),
            "others_draws": sum(d["others_reached"] > 0 for d in draws),
            "others_most": max(d["others_reached"] for d in draws),
            "mean_weight": statistics.mean(d["mean_weight"] for d in draws),
            "below": statistics.mean(d["share_below_0.1"] for d in draws),
            "rate_e": statistics.mean(d["rate_e"] for d in draws), "rate_i": statistics.mean(d["rate_i"] for d in draws)}


def run(seed, inputs="inputs", results="results", workers=2):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    program_ok = check_program(read_program(inputs))
    # The sandbox's /tmp cannot run programs; results/ can, so the port is compiled there and removed after.
    os.makedirs(results, exist_ok=True)
    work = os.path.abspath(os.path.join(results, "work"))
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    exe = compile_port(work)
    selftest = subprocess.run([exe, "selftest"], capture_output=True, text=True)
    selftest_ok = selftest.returncode == 0 and selftest.stdout.strip() == "selftest_failures=0"

    jobs = [(sd, TEST_INTERVAL) for sd in seeds_of(seed, TEST_INTERVAL)]
    jobs += [(sd, PROGRAM_INTERVAL) for sd in seeds_of(seed, PROGRAM_INTERVAL)]
    with cf.ThreadPoolExecutor(workers) as pool:
        lines = list(pool.map(lambda job: run_draw(exe, job[0], SECONDS, job[1]), jobs))
        again = run_draw(exe, jobs[0][0], SECONDS, TEST_INTERVAL)
    shutil.rmtree(work, ignore_errors=True)
    draws = [parse(line) for line in lines]
    test = [d for d in draws if d["interval"] == TEST_INTERVAL]
    beside = [d for d in draws if d["interval"] == PROGRAM_INTERVAL]
    a, b = summary(test), summary(beside)
    cond = conditions(a["succeeded"])
    controls = {"the program is the pinned file and holds every statement the port follows": program_ok,
                "the port's self-test passes": selftest_ok,
                "the 100 seeds are distinct": len({sd for sd, _ in jobs}) == len(jobs),
                "every draw ran its 3,600 s": all(d["seconds"] == SECONDS for d in draws) and len(draws) == 2 * DRAWS,
                "the first test draw, run again, prints the same line": again == lines[0]}

    def both(fmt):
        return f"10 ms: {fmt(a)}; 20 ms: {fmt(b)}"
    values = {
        "successes": a["succeeded"],
        "reached": both(lambda x: f"{x['reached']} of {DRAWS} reach 4 mV, {x['succeeded']} with no other synapse there"),
        "rewards_before_max": both(lambda x: x["rewards_before"]) + " (paper 40 +/- 8)",
        "minutes_to_max": "median minutes to 4 mV, " + both(lambda x: x["minutes"]),
        "reward_rate": "median rewards in the first and last 10 min, " + both(lambda x: f"{x['first']:g} and {x['last']:g}"),
        "others": "draws with other synapses at 4 mV, " + both(lambda x: f"{x['others_draws']} (most {x['others_most']})"),
        "weights": "final mean weight, share below 0.1 mV, " + both(lambda x: f"{x['mean_weight']:.3f} mV, {x['below']:.1%}"),
        "firing_rates": "mean rates exc/inh, " + both(lambda x: f"{x['rate_e']:.2f}/{x['rate_i']:.2f} Hz"),
        "successes_program_interval": b["succeeded"],
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(controls.values()), "controls_total": len(controls),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters: {v}")
    detail = {"input": {"name": INPUT[0], "sha256": INPUT[1], "bytes": INPUT[2]}, "conditions": cond,
              "controls": controls, "summary": {"10": a, "20": b}, "draws": draws, "again": again}
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
        sys.exit(f"izh2007: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
