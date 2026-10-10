# raf: autocatalytic sets in Kauffman's binary polymer model

`check.py` tests one sentence of Stuart Kauffman, "Autocatalytic sets of
proteins" (Journal of Theoretical Biology 119(1), 1986), claim
`ext:2958e6ed6a52baca`: "Because, as M increases, the ratio of reactions
among the possible polypeptides to polypeptides rises rapidly, the existence
of such autocatalytic subsets is assured for any fixed probability of
catalysis."

The registered test: refuted if, in Kauffman's model (all binary polymers of
length 1 to M; food the six of length 1 or 2; every ligation forming a
polymer of length up to M, and its reverse cleavage; each polymer catalysing
each reaction independently with probability P), fewer than 190 of 200
seed-drawn instances contain an RAF set (every reaction catalysed by a member
or food, every reactant producible from food) for any of P = 1e-2, 1e-3 and
1e-4 at M = 9, 12 and 15 respectively, the least M with
P((M-2)2^(M+1)+4) >= 4M. Its fidelity is "adapted": the paper gives no
numeric test, "reflexively autocatalytic" is read as an RAF in the sense of
Hordijk and Steel, the alphabet and food are the ones Mossel and Steel (2005)
use for the model, and transpeptidation is left out (adding reactions can
only add RAFs).

Every rule below was fixed before any seed existed. It needs numpy and
nothing else.

## The model

| M | molecules \|X\| = 2^(M+1) − 2 | ligations n = (M−2)2^(M+1)+4 | reactions \|R\| = 2n | P | reactions catalysed per polymer, P\|R\| | catalysts per reaction, P\|X\| |
|---|---|---|---|---|---|---|
| 9 | 1,022 | 7,172 | 14,344 | 1e-2 | 143.4 | 10.2 |
| 12 | 8,190 | 81,924 | 163,848 | 1e-3 | 163.8 | 8.2 |
| 15 | 65,534 | 851,972 | 1,703,944 | 1e-4 | 170.4 | 6.6 |

- **Molecules.** The binary string of length L and value v (first
  character most significant) is molecule (2^L − 2) + v. The food is the
  six strings of length 1 and 2, molecules 0 to 5.
- **Reactions,** each one-way. For every polymer x of length L from 2 to M
  and every split k from 1 to L − 1 there is a ligation a + b → x, with a the
  first k characters of x and b the rest. Ligations are numbered in order of
  L, then k, then v, and the cleavage x → a + b of ligation j is reaction
  n + j. The count is checked against the formula.
- **Catalysis,** drawn exactly. Each of the |R| × |X| (reaction, molecule)
  pairs is catalysed independently with probability P. The pairs are
  numbered r|X| + x, and the catalysed numbers are the partial sums of
  Geometric(P) gaps, less one, below |R| × |X|, in int64. This is the
  Bernoulli process itself, not an approximation: every pair is distinct,
  and the number of catalysts of each reaction is Binomial(|X|, P). At
  M = 15 that is about 11.2 million pairs an instance.
- **Randomness.** All of it comes from `ECDYSIS_SEED`. Instance i of the
  setting labelled s uses numpy's `Generator(PCG64(n))`, where n is the
  256-bit integer SHA-256(seed ‖ "|" ‖ s ‖ "|" ‖ i). Each instance is
  therefore fixed by the seed, its label and its number, however the work is
  scheduled. The labels are `raf/test/p2/m9`, `raf/curve/p4/m14`,
  `raf/control/half/m15` and the like.

## RAF and CAF

- **RAF,** by Hordijk and Steel's maxRAF reduction. Start with every
  reaction. Take the closure of the food under the current reactions: a
  reaction fires when all its reactants are present, adding its products,
  until nothing more is added. Then drop every reaction with a reactant
  outside the closure, or with no catalyst inside it. Repeat until nothing
  is dropped. What remains is the maxRAF; an instance contains an RAF if and
  only if it is not empty. This is the test.
- **CAF** (constructively autocatalytic), reported beside the test and never
  in it. From the food, take every reaction whose reactants and at least one
  catalyst are all present, add their products, and repeat until no reaction
  is added. A CAF needs each catalyst to be made before the reaction it
  catalyses can run; Mossel and Steel (2005) show that, for this model, the
  chance of a CAF stays below 432P at every M. It is the stricter reading
  under which "assured" fails, so the run counts both.

## What runs

| setting | P | M | instances | in the test? |
|---|---|---|---|---|
| test | 1e-2, 1e-3, 1e-4 | 9, 12, 15 (derived as the least M with P·n ≥ 4M and checked against the registered values) | 200 each | yes: each needs at least 190 with an RAF |
| curves | the same three | every M from 3 to one below the test's | 200 each | no |
| control | 0.5/\|R(M)\|: half a reaction catalysed per polymer | 9, 12, 15 | 200 each | no: it must fail, fewer than 190 with an RAF at each M |

Two worker processes run the 6,600 instances, the costliest first. Results
are gathered in a fixed order, so the outputs are the same bits serially or
pooled, and nothing reads the clock.

**The validation runs inside every receipt.** The three inputs are example
systems that CatReNet ships (husonlab/catrenet at `f3d5f23`, GPL-3.0; Huson,
Xavier and Steel's tool for catalytic reaction systems). Each is checked by
SHA-256, read in CatReNet's documented CRS format (`docs/index.md`,
section 4), and run through the same `max_raf` and `max_caf` as every
instance. A two-way reaction is split into its two one-way halves with the
same catalysts, as CatReNet's `Reaction.allAsForward` splits it, and counted
once. Their sizes must be the ones CatReNet's README states in "Provided
datasets" (lines 245, 247–249 and 256–257 at that commit):

| input | SHA-256 | README | reactions, food, maxRAF, maxCAF |
|---|---|---|---|
| `catrenet-example-00.crs` | `767555d1…` | "6 reactions, 3 food items, has a Max RAF of size 3 and no Max CAF" | 6, 3, 3, 0 |
| `catrenet-example-02.crs` | `3504297a…` | "has 5 reactions and 6 food items, has a Max RAF of size 5 and a Max CAF of size 3" | 5, 6, 5, 3 |
| `catrenet-example-08.crs` | `5114ddf1…` | "has 17 two-way reactions and 4 foot items, is a Max RAF and a Max CAF" | 17, 4, 17, 17 |

None of CatReNet's code is run. The parser refuses what the examples do not
use: inhibitors, AND-catalysis, reverse arrows, coefficients and reactions
without catalysts.

## What it writes

`results/outputs.json` holds the 20 values a receipt carries:

| field | meaning |
|---|---|
| `instances` | 200 |
| `reactions_m15`, `catalysts_mean_p4_m15` | \|R\| at M = 15, and the mean catalysts per reaction there (expected P\|X\| = 6.5534) |
| `raf_p2_m9`, `raf_p3_m12`, `raf_p4_m15` | test instances with an RAF, of 200 |
| `caf_p2_m9`, `caf_p3_m12`, `caf_p4_m15` | the same instances with a CAF |
| `maxraf_fraction_p4_m15` | the maxRAF's mean share of the reactions at M = 15 |
| `curve_p2`, `curve_p3`, `curve_p4` | `M:count` of instances with an RAF, for every M below the test's |
| `control_raf_m9`, `control_raf_m12`, `control_raf_m15`, `control_ok` | control instances with an RAF, and 1 if fewer than 190 at each M |
| `validation_ok`, `validation_sizes` | 1 if the three CatReNet examples give the README's sizes, and the sizes found |
| `test_passed` | 1 if at least 190 of 200 contain an RAF at each test (P, M), else 0 |

`results/detail.json` holds every value computed (the CAF curves, the
control's CAFs, the counts at M = 9 and 12) and, for every setting, each
instance's catalysed pairs, maxRAF and maxCAF sizes and the molecules in the
maxRAF's closure. It also holds the validation's reactions by name and the
derivation of the three M.

## Runtime and repeatability

The receipt command took 135 s and 136 s in two runs under the runner's
restrictions, on two CPUs of an Intel Xeon at 2.1 GHz. Memory stayed near
1 GB, page cache included. The M = 15 instances, about 0.7 s each, hold most
of the work.

- **The same bits every time.** The two runs wrote byte-identical
  `outputs.json` and `detail.json`. A run on the host (Python 3.13, the same
  numpy) wrote the same bytes as the image (Python 3.12).
- **Other CPUs.** numpy's geometric draws use `log1p` and, on a rare path,
  `exp`, which glibc dispatches on CPU features. A run with glibc and numpy
  limited to the baseline instruction set wrote byte-identical files.
  `log1p(−p)` is bit-identical in both settings for all six probabilities
  the check uses.
- **Tolerances.** Every count should match exactly in the pinned image on any
  x86-64 machine, and so should the six-decimal ratios. A difference is a
  finding, not noise.

## What it cannot check

- **The limit.** "Assured … as M increases" is a statement about every
  larger M and every P; three (P, M) points cannot show it.
- **Kauffman's own model.** His alphabet and food, transpeptidation and his
  own graph criterion for autocatalytic closure are not run.
- **Chemistry.** An RAF is a property of the reaction graph. Whether such a
  set would form and persist at real concentrations and rates is not
  modelled.
- **Which RAFs.** The maxRAF is found and its size reported, not the
  irreducible RAFs inside it. By the definition, a single reaction among the
  food catalysed by a food molecule is an RAF and is counted; the maxRAF's
  share of the reactions is reported beside the count.
- **CatReNet on these instances.** The validation runs its three documented
  examples only.

## Run

    env -i ECDYSIS_SEED=<64 hex> HOME=/tmp /usr/bin/python3 raf/check.py

Run it from the laboratory's root, with the three examples in `inputs/`, in
`pytorch/pytorch@sha256:c4ab67f95221a342dff0e8ca4543a7b8885f79f7a0029c0e2e39685d5eaf1722`
(Python 3.12.3, numpy 2.5.3). Tests: `python3 -m unittest discover -s tests`.

## diversity.py

`diversity.py` imports this module unchanged for Hordijk, Steel and
Kauffman's claim on the required molecular diversity
(`ext:2d06a5cef5b5b249`): the polymer model with each ligation and its
cleavage sharing their catalysts, and the Jain–Krishna model, at the points
the paper's theory names. Its rules, outputs and limits are in its
docstring; its tests are `tests/test_diversity.py`.
