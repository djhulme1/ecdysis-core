# lenia: Lenia's species catalogue, counted and simulated

`check.py` tests one sentence of Bert Wang-Chak Chan, "Lenia — Biology of
Artificial Life" (Complex Systems 28(3), 2019; arXiv:1812.05433), claim
`ext:78fcc6363eb1c38c`: "More than 400 species in 18 families have been
identified, many discovered via interactive evolutionary computation."

The registered test: refuted if the species catalogue the author released
(Chakazul/Lenia, `Python/animals.json` at commit `25e107e`, January 2020, the
first release whose taxonomy matches the paper's) lists 400 or fewer
distinct species or fewer than 18 families; or if more than a tenth of a
seed-chosen sample of 40 of its species, each simulated under its own
parameters with the paper's exponential kernel and growth in a periodic
world for t = 30, evaporate (mass below a tenth of its start) or explode
(over half the world filled).

The one input is that catalogue, `inputs/lenia_animals_2020.json` (SHA-256
`5544bcf512f4232bc49ead99820443a7952530abb123bf33c8300ec9deae8ba1`, MIT
licence), checked by hash and read as data. The author's simulator,
`Python/LeniaND.py` at the same commit, was read as the specification; none
of its code is used, and `check.py` cites its lines as `LeniaND.py:n`. Every
rule below was fixed before any seed existed. It needs numpy and nothing else.

## What is counted, and why

Walking the catalogue in order, a header (an entry with no `cells`, code `>1`
to `>4` for class, order, family and subfamily) becomes the current one at
its level and clears the levels below it.

| value | rule | catalogue |
|---|---|---|
| `families` | level-3 headers named `family: …` (not `(compilation)`) | 18 |
| `family_entries` | pattern entries whose current level-3 header is a family | 526 |
| `species` | distinct names among those entries | 433 |
| `species_codes` | distinct codes among them | 436 |
| `species_binomials` | distinct first two words of their names | 361 |
| `catalogue_entries` | every entry, headers included | 612 |

A species is a distinct name because that is how the paper defines one and
how the catalogue records it: "a group of lifeforms with the same morphology
and behavior in global and local scales" (§3.2.2), and the catalogue gives
each such form its own name (Orbium unicaudatus, Orbium unicaudatus ignis,
...), sometimes with several entries under it. Counted as binomials, the
names would give 361, under 400; that figure is reported for transparency
only. The 18 families are the paper's: Orbidae, Scutidae, Pterifera,
Helicidae, Circidae, Echinidae, Geminidae, Ctenidae, Uridae, Kronidae,
Quadridae, Volvidae, Dentidae, Radiidae, Bullidae, Lapillidae, Folidae and
Amoebidae. Twenty pattern entries stand outside every family and are not
counted: the `(compilation)` entry, the one entry of the order Tubiformes
(which has no family header), and the classes SmoothLife (2) and Conway's
Game of Life (16).

## The sample

The 433 species in catalogue order, each represented by its first entry; 40
drawn by a partial Fisher–Yates shuffle (for i = 0 … 39: j = i + below(n − i),
swap) with draws from `ECDYSIS_SEED`, SHA-256 in counter mode under the label
`lenia/sample` (the `Stream` of `pi/bbp.py`). It is the only randomness.
`sample_indices` lists the drawn entries' places in the catalogue.

## One simulation

- **Pattern.** The cells decoded as LeniaND's `Board.rle2arr` and `ch2val`
  decode them in two dimensions (`LeniaND.py:107-112, 168-191`), values
  divided by 255. A delimiter of more dimensions, a token LeniaND's encoder
  never writes, or a pattern with no mass is refused.
- **World.** N × N, periodic, double precision, N the smallest power of two
  at least max(3 × the pattern's longer side, 6R, 128): 117 species run at
  128, 265 at 256, 46 at 512 and 5 at 1024. The pattern's top-left corner
  sits at ((N − h) // 2, (N − w) // 2), where `Board.add` puts it.
- **Kernel** (the paper's equations 10-12, built as `LeniaND.py:312-318`
  and `408-434` build it). With D the distance from the centre (N/2, N/2)
  divided by R and B the number of peaks in β:
  K_S = [D < 1] · core(min(B·D mod 1, 1)) · β[min(⌊B·D⌋, B − 1)] and
  K = K_S / ΣK_S, transformed after `ifftshift` so that its centre is at
  (0, 0). LeniaND transforms the kernel uncentred and `fftshift`s the
  potential instead; the two agree bit for bit.
- **Update** (equation 9): A ← clip(A + G(U)/T, 0, 1) with
  U = Re ifft2(K̂ · fft2 A), the product taken with K̂ first, as LeniaND's
  `calc_once` takes it (`LeniaND.py:368`; see Determinism), for 30·T steps
  (t = 30).
- **Failure.** With M = ΣA and m0 its start, a run stops at the first step
  with M < m0/10 (evaporated) or M > N²/2 (exploded) and records the step
  and t = step/T; otherwise it persists and records M(t = 30)/m0. The least
  and greatest M/m0 along the way are recorded too.

| | exponential | polynomial | step | staircase |
|---|---|---|---|---|
| core K_C(r) | exp(4 − 1/(r(1−r))), 0 where r(1−r) = 0 | (4r(1−r))⁴ | 1 on [1/4, 3/4] | the step, plus 1/2 on r < 1/4 |
| growth G(u) | 2 exp(−(u−μ)²/(2σ²)) − 1 | 2 max(0, 1 − (u−μ)²/(9σ²))⁴ − 1 | 2·[\|u − μ\| ≤ σ] − 1 | |

## Three variants

| variant | core and growth | μ | run on |
|---|---|---|---|
| `paper` | exponential for every species: the registered test | stored | all 433 |
| `code` | what LeniaND computes for the entry's `kn`, `gn`: `kernel_core[kn − 1]` of (polynomial, exponential, step, staircase), `growth_func[gn − 1]` of (polynomial, exponential, step) (`LeniaND.py:272-282, 317, 370`) | stored | all 433 |
| `control` | exponential | doubled | the 40 sampled; at least 36 must die |

The sample's `paper` and `code` results are read from the census of all 433.

### kn = 1: "Exponential" on screen, polynomial in the code

The catalogue stores `kn = gn = 1` for 427 of the 433 species (four have 2,
two have 3). LeniaND looks the functions up as `kernel_core[kn - 1]` and
`growth_func[gn - 1]`, whose entry 0 is the polynomial pair ("quad4") and
entry 1 the exponential ("bump4", "gaus"). Its on-screen value text maps
them the other way round: `["Exponential","Polynomial","Step","Staircase"][kn - 1]`
and `["Exponential","Polynomial","Step"][gn - 1]` (`LeniaND.py:2308-2309`).
So a lifeform with `kn = gn = 1` is shown as "Exponential" while it runs on
the polynomial functions. The paper states that its simulations used
"Kernel core and growth mapping: exponential" (§2.2.4), and LeniaND's own
key for reloading a lifeform with exponential functions (shift-Z,
`LeniaND.py:2149`) sets `kn = gn = 2`. Which functions the catalogue's
species were found and checked under cannot be settled from the release.
The registered test follows the paper (`paper`); `code` runs what the
program computes for the stored values, and its failures are reported
beside the test, not in it. The paper's Figure 6 shows Orbium unchanged when
its core functions are switched to polynomial.

## What it writes

`results/outputs.json`, the 20 values a receipt carries (strings of at most
200 characters):

| field | meaning |
|---|---|
| `catalogue_entries`, `families`, `family_entries`, `species`, `species_codes`, `species_binomials` | the count above |
| `sample_size`, `sample_indices` | 40, and the drawn entries' catalogue places, ascending |
| `sample_failures`, `sample_evaporated`, `sample_exploded` | sampled species that fail under `paper`, and how |
| `sample_failed` | each as `code:fate@t`, cut to whole items ending `;+k more` if over 200 characters |
| `sample_grew_3x` | sampled species that persist under `paper` with M(30)/m0 > 3 (alive by the rule, but much changed) |
| `sample_code_failures` | sampled species that fail under `code` |
| `control_failures`, `control_ok` | sampled species that die under the control; 1 if at least 36 |
| `census_paper_failures`, `census_code_failures` | failures among all 433 under each variant |
| `steps_simulated` | updates computed across all 906 simulations |
| `test_passed` | 1 if `species` > 400, `families` ≥ 18 and `sample_failures` ≤ 4, else 0 |

`results/census.json` holds everything, uncut. `values` has every value
computed: the 20 above (with `sample_failed` whole), `sample_codes`,
`census_species`, and for each of `paper` and `code` the census's
`failures`, `evaporated`, `exploded`, `grew_3x` and the `failed` list.
`species` has one row per species in catalogue order: `index`, `code`,
`name`, `sampled`, `N`, `m0` and, under `fates`, for each variant run on it,
`fate`, `steps`, `t` and the final, least and greatest M/m0 (`mass`, `low`,
`high`) as full doubles, which read back bit for bit. Neither file depends
on scheduling or the clock; progress goes to stderr.

## Runtime

906 simulations (433 species under `paper` and `code`, 40 under the
control), 270,056 updates under the seed of 64 `a`s: 552 s and 564 s in two
runs of the receipt command under the runner's restrictions on two CPUs of
an Intel Xeon at 2.1 GHz with AVX-512. The two worker processes take the
costliest simulations first (the five worlds of 1024 × 1024 and the 46 of
512 × 512 hold most of the work). With numpy limited to its baseline
instructions (see Determinism) the same run took 530 s. If no worker pool
can be started the run continues in one process and takes about twice as
long. Memory stays well under the runner's 4 GB.

## Determinism

**In the pinned image the results are the same bits on every run.** Under
the seed of 64 `a`s, the receipt command (two worker processes, the
costliest simulations first) and a run of the same `main()` with every
simulation in one process, in reverse order, wrote byte-identical
`outputs.json` and `census.json`. Since `census.json` keeps each run's
final, least and greatest mass ratio as full doubles, that is all 906
simulations agreeing to the last bit, serially or pooled, in either order.
Simulations repeated in fresh processes with different allocation
histories end in identical worlds (SHA-256 of the final state), and the
tests check pooled against serial runs bit for bit. Memory alignment plays
no part: numpy's FFTs and complex products give the same bits for arrays
at every 8-byte offset modulo 64.

**One dependence was found and removed.** The product K̂ · fft2(A) was
written `Khat * np.fft.fft2(A)`. numpy 2.5's complex multiply fuses one of
its two products (`fmaddsub`), so K F and F K can differ in the last bit of
the imaginary part, and numpy's temporary elision rewrites
`Khat * <a fresh array of 256 KiB or more>` as `F *= Khat`, that is F K,
whenever the interpreter allows it: Python 3.12 in the image does, for
every world here (128² × 16 bytes is exactly 256 KiB); Python 3.13 did not.
The same code therefore gave different bits on two interpreters (9 of 14
final worlds in a spot check), and differed from LeniaND's `calc_once`,
whose operand is an attribute and never elided, by 1.1 × 10⁻¹⁶ after one
step and 2.3 × 10⁻¹² after 300. It is now `np.multiply(Khat, fft2(A))`, a
ufunc call that is never elided: K F, as LeniaND takes it, everywhere. The
change moved no output: the receipt command before and after it gave the
same 20 outputs, byte for byte, and the same census to four decimals.

**On other machines.** Three operations depend on the CPU's instruction
set, through numpy's runtime dispatch and glibc: `exp` (numpy's own AVX-512
code, else glibc's), `x ** 4` (SVML on AVX-512, else glibc) and the complex
multiply (fused only with FMA). The FFTs (pocketfft, built for the
baseline) do not. Any x86-64 machine with AVX-512 (numpy's `X86_V4`
level: Skylake-SP and later, AMD Zen 4) should give the bits above:
limiting numpy to that level leaves the bits of all three, and of the FFTs,
unchanged on this machine. The run was repeated in the image with numpy's
dispatch (and, for the second, glibc's) limited, to emulate other machines:

| machine emulated | how | 20 outputs | fates and failure steps | M/m0 (mass, least, greatest) |
|---|---|---|---|---|
| AVX2 and FMA, no AVX-512 | `NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR"` | byte-identical | all 906 identical | 559 of 906 final values differ, median 5 × 10⁻¹⁶ relative; worst 1.4 × 10⁻⁴ |
| no AVX2, no FMA | numpy at its `X86_V2` baseline, and `GLIBC_TUNABLES=glibc.cpu.hwcaps=-AVX2,-FMA,-AVX512F,-AVX512VL,-AVX512DQ,-AVX512BW,-AVX512CD,-AVX` | byte-identical | all 906 identical | 545 of 906 differ, median 5 × 10⁻¹⁶; worst 9.5 × 10⁻⁵ |

Most differences stay within a few units in the last place. Only four
records grow beyond 10⁻⁹ in either run: O2bi under `code`, a dying run
whose mass at the step it evaporates (214) differs by 1.4 × 10⁻⁴; 4Q5m
under `paper` (10⁻⁷ at t = 30); O6 under `paper` (10⁻⁸, evaporating); and
O4t under `paper` (10⁻⁹).

The margins explain why no fate moves. No sampled species comes near a
line: the two failures happen at steps 101 and 136 of 300, more than 8%
below m0/10 at the step they fail; the lowest mass any persisting sampled
species reaches is 0.685 m0; the control's narrowest kill is 1.6% past the
line. In the census the nearest calls are ~H3p under `paper`, 0.1% past
the explosion line at the step it fails, ~S2p (0.4%), KN+c under `code`
(0.9%), Catenopteryx cyclon scutoides (PN+cys), which grows to 13.6 m0
against an explosion line at 14.3 m0, and 2PN+c under `paper`, which
evaporates at step 295 of 300.

### Tolerances for a cross-check

| outputs | the pinned image, any x86-64 machine | an independent implementation in double precision |
|---|---|---|
| `catalogue_entries`, `families`, `family_entries`, `species`, `species_codes`, `species_binomials`, `sample_size`, `sample_indices` | exact | exact: they depend only on the catalogue's bytes and the seed |
| `sample_failures`, `sample_evaporated`, `sample_exploded`, `sample_failed`, `sample_grew_3x`, `sample_code_failures`, `control_failures`, `control_ok`, `test_passed` | exact | exact: nothing sampled comes within 1.6% of a line, against differences of 10⁻⁴ at worst |
| `census_paper_failures`, `census_code_failures`, `steps_simulated` | exact | exact expected; a difference is explained by rounding only if `census.json` shows that it comes from one of the near calls above, each of which can move a count by 1 and `steps_simulated` by a few steps |
| `census.json` `fate`, `steps`, `t` | exact | as the census counts |
| `census.json` `mass`, `low`, `high` | identical on AVX-512 machines; otherwise relative 10⁻³ | relative 10⁻³ (seven times the worst difference seen) |

On any x86-64 machine with AVX-512 both files should match byte for byte;
a difference there is a finding, not noise.

## Cross-check against LeniaND

LeniaND's own functions were extracted with `ast` from a text copy of the
file and run, in the pinned image with no network, beside `check.py`:
`kernel_core`, `growth_func`, `kernel_shell`, `calc_kernel`, `calc_once`
and the CPU branches they call, with `Board`'s decoder and placement to load
the pattern and the module's globals set for a two-dimensional N × N world.
Every update was compared cell by cell for the whole run.

| species | N | `kn` | `code` | `paper` (LeniaND's `kn = gn = 2`) |
|---|---|---|---|---|
| O2u Orbium unicaudatus | 128 | 1 | 300 steps, 0.0 | 300 steps, 0.0 |
| O4dp Parorbium dividuus pedes | 256 | 2 | 300 steps, 0.0 | 300 steps, 0.0 |
| ~H3p Trihelicium pachus | 128 | 3 | 300 steps, 0.0 | explodes at step 172 in both, 0.0 |
| 2PG1t | 128 | 1 | 300 steps, 0.0 | evaporates at step 101 in both, 0.0 |
| O2v Orbium virtualis (T = 320) | 128 | 1 | 9,600 steps, 0.0 | evaporates at step 772 in both, 0.0 |
| P11aa Unidecapteryx arcus alternatus | 512 | 2 | 300 steps, 0.0 | 300 steps, 0.0 |
| KN+c Catenokronium cinguli | 512 | 1 | evaporates at step 142 in both, 0.0 | evaporates at step 136 in both, 0.0 |
| S24 Tetracosascutium | 1024 | 1 | 300 steps, 0.0 | 300 steps, 0.0 |

The largest absolute difference in any cell at any step is 0.0: the states
are equal bit for bit, and so are the final mass ratios (for Orbium
unicaudatus under `code`, 0.9612957732298749 in both). Run the same way,
LeniaND's `Board.rle2arr` decodes all 546 of the catalogue's pattern
entries exactly as `check.py` does, and `calc_kernel` builds every
species' kernel identically, under its own `kn` and under the exponential
core. The agreement holds in the pinned image on one machine; it says the
two programs compute the same thing, not that either matches what the
author ran in 2019.

## What it cannot check

- whether the catalogue's names are species in the paper's sense: it counts
  the names the author gave;
- "many discovered via interactive evolutionary computation": the
  catalogue does not say how any species was found;
- whether a species keeps its form: mass is the only measure, so a pattern
  that becomes another shape of similar mass persists (`sample_grew_3x`
  flags the ones that triple);
- persistence beyond t = 30, or in other worlds, positions or orientations;
- the author's single-precision GPU path (complex64 FFTs): this runs in
  double precision, as the paper says it did;
- under `paper`, the catalogue's step-function and polynomial species run
  with exponential functions, as the registered test says; `code` shows each
  under its own.

## Run

    env -i ECDYSIS_SEED=<64 hex> HOME=/tmp /usr/bin/python3 lenia/check.py

from the laboratory's root, with the catalogue at
`inputs/lenia_animals_2020.json`, in
`pytorch/pytorch@sha256:c4ab67f95221a342dff0e8ca4543a7b8885f79f7a0029c0e2e39685d5eaf1722`
(Python 3.12.3, numpy 2.5.3). Tests: `python3 -m unittest discover -s tests`
(`LENIA_CATALOGUE=<path>` adds the tests on the real catalogue).
