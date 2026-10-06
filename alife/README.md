# bff_soup: an independent BFF primordial soup

`bff_soup.c` is our own implementation, in one C file, of the BFF primordial
soup of Agüera y Arcas et al., "Computational Life: How Well-formed,
Self-replicating Programs Emerge from Simple Interaction" (arXiv:2406.19108).
It exists to test one claim: that the soup's state transition (the jump in
high-order entropy that marks self-replicators taking over) happens in about
40% of runs within 16k epochs. The specification is the authors' code, cubff
(Apache-2.0, commit `f212e849027c98fcf4b242eccfb5fed435223e23`); every rule
in the source cites the cubff file and line it follows. No cubff code is
compiled into the program.

## Read this first: which BFF variant

cubff has two BFF languages that differ only in where execution starts:

| cubff `--lang` | heads start at | instruction pointer starts at |
|---|---|---|
| `bff` (`bff.cu:15` defines `BFF_HEADS`) | bytes 0 and 1 of the tape, mod 128 (`bff.inc.h:270-275`) | byte 2 |
| `bff_noheads` | 0 (`bff.inc.h:277-282`) | byte 0 |

The brief for this work asked for `bff`, and that is the default here. **But
the paper names the other one.** Its code-availability paragraph says: "To
run the BFF variant from Section 2, pass --lang bff_noheads". Section 2's
language definition agrees: the heads are "initialized to zero" and "the
instruction pointer starts at zero". The 40%-within-16k figure is in
Section 2.1 (Figure 5: "Distribution of complexity over time across 1000
different runs, with 0.024% mutation rate ... 40% of runs show a state
transition within 16k epochs"). cubff's own README example also runs
`bff_noheads`.

So a test of "the paper's BFF soup" should run `bff_noheads`:

    ECDYSIS_SEED=<64 hex> ./bff 20 16384 bff_noheads

The two variants behave differently. From the same seed, high-order entropy
after 257 epochs is about 0.02 for `bff` and about 0.26 for `bff_noheads`
(cubff's own `testdata/bff.txt` and `testdata/bff_noheads.txt` show the
same). In our few trials, both `bff` runs transitioned, at epochs 1,665 and
3,265. Of two `bff_noheads` runs, one went the full 16,384 epochs without
transitioning and the other had not transitioned by epoch 4,096. These
samples are far too small to estimate rates. They only show that a result
from one variant says nothing about the other. `outputs.json` records which
one ran.

## Build and run

In the pinned image, with no network:

    docker run --rm --network none -v "$PWD":/work -w /work \
      buildpack-deps:bookworm@sha256:88c9154b6b438be20b616e2e74c158cfd79feafc6bcf1d9a3b47874b38c91992 \
      sh -c 'gcc -O2 -pthread bff_soup.c -lbrotlienc -lm -o /tmp/bff && ECDYSIS_SEED=<64 hex> /tmp/bff 2 512'

Arguments, all optional: `runs` (default 20), `epochs` (default 16384),
`lang` (`bff`, the default, or `bff_noheads`). Two runs are simulated at a
time, one per thread.

## What it writes

`results/outputs.json` holds one flat object:

| field | meaning |
|---|---|
| `runs`, `epochs_max` | the job |
| `transitions`, `fraction` | runs whose high-order entropy crossed the threshold, and that over `runs` |
| `median_epoch` | median crossing epoch over the runs that crossed; -1 if none |
| `epochs` | each run's crossing epoch in run order; -1 if it never crossed, -2 if it failed |
| `threshold`, `measure_every` | 3.0, and the sampling interval of 64 epochs |
| `mutation_rate`, `step_limit`, `num_programs`, `tape_bytes`, `language` | the soup |
| `brotli`, `rng` | the compressor version and settings; the seed derivation |
| `max_hoe_no_transition` | the highest high-order entropy any non-transitioning run reached |
| `final_hoe` | each run's last sample |
| `guard_checks`, `failed_runs` | interactions re-checked by the reference interpreter; runs that failed (must be 0) |

`results/trajectory.csv` holds every sample of every run: epoch,
high-order entropy, Shannon entropy, compressed bits per byte, compressed
size and mean ops per interaction since the previous sample. Both files are
deterministic. Wall-clock times go only to stderr.

## The semantics, and where each rule comes from

| rule | value here | cubff source |
|---|---|---|
| soup | 2^17 programs of 64 bytes | `common.h:55,59`; `main.cc:180` |
| initial soup | every byte uniformly random | `common_language.h:139-155`, `zero_init` false (`main.cc:201`) |
| pairing | each epoch, a fresh uniformly random permutation (Fisher-Yates from the end); pair k is (perm[2k], perm[2k+1]), the first program taking bytes 0-63; every program in exactly one pair | `common_language.h:418-424,464-477`; `permute_programs` true, `fixed_shuffle` false (`main.cc:198,200`); `common_language.h:166-171` |
| mutation | each byte of each concatenated pair, once per epoch, before execution, replaced with probability exactly 2^18/2^30 = 2^-12 (0.0244%) by a uniform random byte, which may equal the old one | `common_language.h:172-180`; `main.cc:183,226`; `common.h:61` |
| execution | the 128-byte concatenation, in place, then split back | `common_language.h:164-191` |
| step limit | 8192 steps | `common_language.h:184` (`Evaluate(tape, 8 * 1024, ...)`) |
| what counts as a step | every byte read: an instruction, a no-op byte (any of the 246 non-instruction values, 0 included), or a bracket jump (one step however far it jumps) | `bff.inc.h:366-386` |
| instructions | `< >` move head0, `{ }` move head1, `+ -` change t[head0] mod 256, `.` t[head1] = t[head0], `,` t[head0] = t[head1], `[` jumps forward past the matching `]` if t[head0] == 0, `]` jumps back to just after the matching `[` if t[head0] != 0 | `bff.inc.h:58-85,289-349` |
| heads | wrap mod 128 before every step | `bff.inc.h:368-369` |
| head start (`bff`) | bytes 0 and 1 mod 128; instruction pointer at byte 2 | `bff.cu:15`; `bff.inc.h:50-52,270-275` |
| head start (`bff_noheads`) | 0; instruction pointer at byte 0 | `bff.inc.h:277-282` |
| bracket matching | done at the moment of the jump, on the tape as it is then (self-modification counts), counting nesting; a scan covers bytes 0-127, the head bytes included | `bff.inc.h:317-344` |
| unmatched brackets | `[` with t[head0] == 0 and no match ahead ends execution; `]` with t[head0] != 0 and no match behind ends execution; with the condition false they fall through without scanning | `bff.inc.h:326-328,340-342` |
| termination | the step limit, an unmatched jump, or the instruction pointer passing byte 127 | `bff.inc.h:377-385` |
| measure | brotli quality 2, window 2^24, generic mode, over the whole soup in program order; Shannon entropy of the byte histogram; high-order entropy = Shannon entropy − compressed bits per byte, kept as a float | `common_language.h:504-546`; `common.h:87` |
| cadence | after epoch 1 and every 64 epochs (epochs completed 1, 65, 129, ...), plus once after the last epoch | `common_language.h:496,540`; `main.cc:204,324` |

## The transition rule

A run transitions at the first sample whose high-order entropy is above
3.0. That is the authors' own rule: their scripts mark "time to
self-replication" as the first sample with `higher_entropy > 3.0`
(`python/runit.py:29`, `python/cond_exp.py:55`, `python/time_to_sr.py:33,52`,
`python/cond_prob.py:31,48`). The paper itself states no number.

The data support it. Before a transition, high-order entropy stays low: at
most 0.055 in our `bff` runs, and a plateau of 0.1 to 0.38 in `bff_noheads`
runs over 16,384 epochs. Once replicators have taken over it sits at 4 to
4.7. Both transitions we saw (both `bff`) were abrupt: from 0.055 to 4.003
within one 64-epoch sample, and from 0.044 to 2.22 to 3.15 over two. Any
threshold between about 0.5 and 3.1 would have recorded them at most one
sample apart. Because of the `bff_noheads` plateau, a threshold must sit well
above 0.4. We did not see a `bff_noheads` transition, so its post-transition
level is not checked here. The recorded epoch is the first sample above the
threshold, so it can be up to 64 epochs after the underlying event. Each run
stops at its crossing.

## Randomness and reproducibility

Everything random comes from `ECDYSIS_SEED` (64 hex digits) and nothing else.
Run r uses xoshiro256** seeded with the four little-endian 64-bit words of
SHA-256(seed bytes ‖ r as 8 little-endian bytes); SHA-256 is implemented in
the file and tested against FIPS vectors. One stream per run is consumed in a
fixed order: initial soup, then each epoch's permutation, then each pair's
mutation. Each run is simulated by one thread from start to finish, so
results do not depend on scheduling. The tests check that runs on two
threads equal the same runs alone, and two invocations with the same seed
give byte-identical `outputs.json` and `trajectory.csv`. The only
floating-point step that feeds a decision is `log2` in the Shannon entropy.
glibc can pick a different `log2` code path on different CPUs, which could
change the last bit of an entropy value but not a crossing, short of a
sample within about 1e-15 of 3.0.

## How it was checked

All of the following ran in the pinned image with `--network none`.

- **Unit tests** (`test_bff_soup unit`: 11,893 checks, 0 failures):
  - SHA-256 and xoshiro256** vectors, and the seed derivation against an independent Python implementation.
  - 53 hand-written tape cases (15 of them step-limit boundaries) run through both interpreters. They cover each instruction, byte 0 as a no-op, loops and nested loops, unmatched `[` and `]` with the condition true and false, a `]` matching a `[` in head byte 1, matches across the two programs, and head wrap-around in both directions for both heads.
  - Initial heads mod 128, and both variants' start states.
  - Self-modification: an instruction written ahead, and a `]` created at run time.
  - The step limit: 8192 on infinite loops, a 50-no-op loop counting each no-op, and limits 26 to 40 stopping mid-loop at exactly the right write.
  - 500,000 random tapes of five kinds through the fast and reference interpreters.
  - The SIMD instruction masks for all 256 byte values.
  - The mutation shortcut against the plain loop, draw for draw. Over 2^26 bytes it gave 16,158 mutation events against 16,384 expected (−1.8σ), and the replacement bytes were uniform (χ² 260 on 255 dof).
  - The pairing is a uniform permutation, determinism across threads, and the measure on random, all-zero and replicated soups.
- **Bit-for-bit agreement with cubff.** We built cubff (`make CUDA=0`) from the checkout in the same image (`xcheck/build_cubff.sh`). The test program can drive this file's own epoch code with cubff's generator, restated from `common_language.h`. With cubff's test seed 10248, cubff's binary and our code give identical logs and identical SHA-256 of the whole soup after epochs 1, 65, 129, 193 and 257, for both `bff` and `bff_noheads` (`xcheck/compare_runs.sh`). The same holds starting from soups evolved for 2,000 epochs, one of them already replicator-dominated (high-order entropy 4.5 to 4.7), for 193 further epochs.
- **The authors' recorded results.** cubff's `testdata/bff.txt` and `testdata/bff_noheads.txt` are not reproduced by cubff itself in this image, because the image's brotli is 1.0.9. Compressing the identical soups with brotli 1.2.0 (Python `brotli`) reproduces all ten recorded lines exactly, sizes and entropies. So our soups are the authors' soups. With brotli 1.0.9 the compressed sizes differ by a few hundred bytes, about 0.0006 bits per byte of high-order entropy, immaterial at a threshold of 3.0.
- **The interpreter against cubff's own `Bff::Evaluate`** (`xcheck/cubff_eval.cc`, compiled from the checkout). 400,000 tapes, both variants, step limits 8192, 1000 and 100: identical final tapes and op counts from cubff, our fast interpreter and our reference interpreter.
- **The measure against cubff's own.** Three soups with no instruction bytes, which a cubff epoch leaves unchanged, measured by cubff's `main --load ... --mutation_prob 0` and by our code: identical log lines. High-order entropy was −0.058, 3.69 and 7.58.
- **At run time,** one interaction in 4,096 is re-run by the reference interpreter and compared. A mismatch fails the run (`guard_checks`, `failed_runs`).

## Speed, and the cost of the 20-run job

The reference interpreter (`bff_eval_ref`) mirrors cubff's loop step by step.
On this 2-CPU machine it managed 6.3 epochs per second. The program uses
`bff_eval`, which gives the same tapes and op counts with two exact
shortcuts:

- It skips runs of no-op bytes in one move, using a bitmask of instruction positions kept current on every write.
- It fast-forwards loops that provably repeat. Brent's cycle detection compares the machine state at backward jumps. Head1 is disregarded when nothing was written, since only the writes read it. When a state repeats, whole cycles up to the step limit are skipped and the remainder is executed normally.

The second shortcut matters because about 6% of interactions in a young soup
spin in an unchanging loop until the 8192-step limit, and those took about
80% of the reference interpreter's time.

Measured throughput per run, two runs at a time on this 2-CPU machine (the
pinned command, `2 512`, takes 9 s):

| phase | epochs per second, per run |
|---|---|
| first 512 epochs | 60 to 72 |
| epochs 2,000 to 4,000 | 40 to 55 (more structure, more work per interaction) |
| epochs 4,000 to 16,384 (`bff_noheads`) | 35 to 40, flat (ops per interaction level off near 235) |
| the 64 epochs containing a takeover (`bff`) | 7.4 and 25 |

Measured run lengths:

- A full non-transitioning `bff_noheads` run of 16,384 epochs took 396.5 s, 41.3 epochs/s on average, with all 262,144 guard checks passing.
- The `bff` runs that transitioned took 42 s (crossing at epoch 1,665) and 63 s (crossing at 3,265).
- Two runs in parallel ran at about the same per-run rate as one alone.

A run that transitions stops at its crossing, so the replicator-dominated
phase, where every interaction runs a copy loop, is never simulated beyond
one sample. The two threads take runs from a queue, so the estimate for 20
runs × 16,384 epochs is:

- **upper bound**, no run transitions: 20 × ~400 s / 2 ≈ 4,000 s, **about 67 minutes**, or up to about 75 with contention and the last run alone;
- **at the paper's 40%**, crossings spread evenly over the 16k epochs: about 12 × 400 s + 8 × 190 s ≈ 6,300 run-seconds, **about 53 minutes**;
- **`bff` if its runs transition as early as in our two trials**: about 10 to 15 minutes. This is not a prediction.

## Where it knowingly differs from cubff

- **Random numbers.** cubff derives every draw from SplitMix64 of counters and the integer `--seed`. Here they come from xoshiro256** keyed by SHA-256 of `ECDYSIS_SEED`. The distributions are the same: a uniform initial soup, a uniform random permutation per epoch, and per-byte mutation with probability exactly 2^-12. The bounded draws for the permutation are unbiased (Lemire), where cubff's `% (i+1)` has a bias below 2^-46. The tests use cubff's own generator to show everything else is identical.
- **brotli.** The image has 1.0.9; cubff's recorded test results need 1.1 or later. High-order entropy differs by about 0.0006.
- **Sampling.** cubff's main samples after epochs 1, 65, 129, ... and stops at the first sample past `--max_epochs`, which is epoch 16,385 for 16,384. Here, in addition, a sample is taken after the last epoch (16,384), so "within 16,384 epochs" is exact. cubff's Python bindings default to sampling every 128 epochs (`common.h:65`). The paper does not say which cadence its Figure 5 used.
- **Early stop.** Each run stops at its crossing; cubff runs on. This changes nothing about whether or when a run crosses.
- **The two interpreters are exact.** Neither shortcut changes any tape, op count or step count; see the checks above.

## Files

- `bff_soup.c`: the program.
- `test_bff_soup.c`: the unit tests (`unit`) and the cross-check tools (`cubff-log`, `gen-tapes`, `eval-tapes`, `gen-soup`, `measure-file`). Build: `gcc -O2 -pthread test_bff_soup.c -lbrotlienc -lm -o test_bff_soup`.
- `xcheck/build_cubff.sh`: builds cubff and the interpreter harness from a read-only checkout mounted at `/src`, inside the pinned image.
- `xcheck/cubff_eval.cc`: the harness that runs cubff's own `Bff::Evaluate`.
- `xcheck/compare_runs.sh`: the bit-for-bit run comparison.
- `xcheck/run_xcheck.sh`: the interpreter, measure and evolved-soup cross-checks.
