# hexagon: the empty hexagon number, h(6) = 30

`check.py` tests Heule and Scheucher, "Happy Ending: An Empty Hexagon in
Every Set of 30 Points" (TACAS 2024, arXiv:2403.00737), claim
`ext:4c4750ac793ed187`: "We establish the exact bound: Every 30-point set in
the plane in general position contains an empty hexagon."

The registered test: every set of 30 points in general position contains an
empty hexagon (six points in convex position with no other point of the set
in their convex hull), and 30 is least. Refuted by a 30-point set in general
position, with exact coordinates, that has no empty hexagon; by the authors'
proof failing to verify (one of its 312,418 cubes satisfiable, its proof
rejected, or the cubes not covering the search space); or by every 29-point
set having one, so that 30 is not least (Overmars's 29 points are the
witness).

The receipt checks the lower bound completely, the coverage of the proof's
partition completely, and the proof's cubes by a seeded sample. Every rule
was fixed before any seed existed; the docstring of `check.py` states them
in full.

## What runs

1. **The witness, exactly.** The 29 points are read as data from the list
   after `hole_lower_bound [` in `theorem holeNumber_6` of the Lean
   formalisation's `Geo.lean` (the same coordinates as Overmars 2003, Fig. 1,
   and the paper's Fig. 8). In integer arithmetic: they are distinct, none
   of the 3,654 triples is collinear, and of the 475,020 six-point
   subsets, those in convex position (5,335, by Andrew's monotone chain) all
   have another point strictly inside. The convex layers are 3, 4, 7, 7, 7, 1,
   as the paper says.
2. **The proof, sampled.** The formula F that the Lean proof reduces the
   theorem to (`final-30-ours-flat.cnf`: 75,109 variables, 452,000 clauses)
   and the authors' 312,418 cubes are read and checked. Eight cubes are drawn
   by the seed, uniformly without replacement. For each, F with the cube's
   literals as unit clauses is solved by CaDiCaL with an LRAT proof, which goes
   down a pipe into cake_lpr as it is written, as the authors ran it (their
   proofs came to 180 TB; none is stored). A cube counts when CaDiCaL says
   UNSATISFIABLE and cake_lpr says `s VERIFIED UNSAT` on that same formula. A
   satisfiable cube would have its model checked against F and the cube, and
   would refute the claim.
3. **The coverage, completely.** Every clause of `cube_tautology.cnf` is
   classified: 452,000 are clauses of F, 312,418 are the negations of all the
   cubes, and one, `75109 452000 0`, is F's DIMACS header, which the
   authors' `final_experiment/cubing_taut.py` read as a clause (its tokeniser
   skips no line). Variable 452,000 occurs nowhere else, so that clause is
   satisfied by setting it true and cannot change satisfiability; any other
   clause would fail the check. The formula must then be UNSAT with its proof
   verified, as in 2. So F and the negations of every cube are unsatisfiable:
   every model of F satisfies some cube, and F is unsatisfiable if every cube
   is.
4. **Controls.** Each must behave as stated; `controls_passed` counts those
   that do. F cut to its opening block (its first 237,510 clauses, all of
   three literals) is satisfiable, and its model satisfies every kept clause
   and violates some removed one (27,405 of them). CaDiCaL's LRAT proof for
   the pigeonhole formula (6 pigeons, 5 holes) is accepted by cake_lpr, and
   rejected without its last step ("empty clause not derived") and without the
   lemma its last step first cites ("clause index unavailable"). The witness
   with its first point moved onto the line through its second and third fails
   for collinearity. The witness with (600, 600) added, in general position
   with the 29, has an empty hexagon (nine).
5. **Seeded 30th points, reported only.** Eight integer points are drawn from
   the witness's bounding box by the seed, a draw that repeats a point or is
   collinear with two of the 29 being rejected and counted. Each 30-point set
   has an empty hexagon, and every one contains the new point. These are a
   handful of instances, not the bound.

`test_passed` is 1 when the witness holds, every sampled cube is UNSAT with a
verified proof, and the coverage check passes (its clauses as above, UNSAT and
verified).

## The tools, built in the run

Nothing from an input is executed as it comes. Both tools are compiled from
source by the run itself, in the image, with no network, into
`results/build/` (the only place the sandbox lets a program run):

- **CaDiCaL 2.1.3**, the solver the authors used in a later version (they had
  1.9.3 and 1.9.5, which no archive keeps as a single file). The source is
  Debian's `cadical_2.1.3.orig.tar.gz`, from snapshot.debian.org's
  content-addressed store. Its 82 `src/*.cpp` files except `mobical.cpp` are
  compiled with `g++ -O3 -DNDEBUG -DNBUILD` (CaDiCaL's own switch for a build
  without `configure`) and linked; about 70 s on two CPUs. The tarball's one
  link (`src/configure`) is skipped; any path outside `cadical-rel-2.1.3/` is
  refused.
- **cake_lpr**, the CakeML-verified LRAT checker the authors used, from its
  two files at commit a36874a: `gcc -O2 -std=c99 basis_ffi.c cake_lpr.S`, as
  its Makefile does (2 s). `cake_lpr.S` is x86-64 assembly, so the bundle
  runs on x86-64 only. Its default heap and stack (4 GB each) cannot be had in
  4 GB, so it runs with a 1,024 MB heap and a 512 MB stack, and a check that
  runs out is repeated alone with a 2,560 MB heap. (The repository's
  `cake_lpr.sha256` still lists an older `basis_ffi.c`; `cake_lpr.S` matches
  it.)

The archive allows eight inputs, which rules out fetching CaDiCaL's 142
source files one by one; seven are used.

## Inputs

| name | URL | SHA-256 | bytes | licence |
|---|---|---|---|---|
| `Geo.lean` | https://raw.githubusercontent.com/bsubercaseaux/EmptyHexagonLean/3073981d2aa5aa1e399b382e605c0ed12a0b69af/Lean/Geo.lean | `3b64f0139928046c812ff336c0d894a3899d0b31710b79714bc5bb07d4c99643` | 6,376 | none stated in the repository |
| `final-30-ours-flat.cnf` | https://raw.githubusercontent.com/bsubercaseaux/EmptyHexagonLean/3073981d2aa5aa1e399b382e605c0ed12a0b69af/final_experiment/final-30-ours-flat.cnf | `95f2789a770999b76129f048ae5ec59c06dfc42c1f8f5f3a134b54e242dd95e3` | 9,704,854 | none stated in the repository |
| `marijn-cubes.icnf` | https://raw.githubusercontent.com/bsubercaseaux/EmptyHexagonLean/3073981d2aa5aa1e399b382e605c0ed12a0b69af/final_experiment/marijn-cubes.icnf | `7d227e0f7ce9f55c42f70420de5f987518a8372d2f3f4e680c3420a4ea4e0171` | 37,366,908 | none stated in the repository |
| `cube_tautology.cnf` | https://raw.githubusercontent.com/bsubercaseaux/EmptyHexagonLean/3073981d2aa5aa1e399b382e605c0ed12a0b69af/final_experiment/cube_tautology.cnf | `ed1c0cdad2b99d5d9e9a28dd8499243157e4f9b226ebca4a4c39bdd6df992323` | 45,786,575 | none stated in the repository |
| `cadical_2.1.3.orig.tar.gz` | https://snapshot.debian.org/file/f2c90120e8f60cb08199a32bcb9c9406bbf76443 | `abfe890aa4ccda7b8449c7ad41acb113cfb8e7e8fbf5e49369075f9b00d70465` | 731,545 | MIT |
| `cake_lpr.S` | https://raw.githubusercontent.com/tanyongkiam/cake_lpr/a36874a8b750b43fe4b385b8ddbf5b033e46a3fa/cake_lpr.S | `2f3af32d55083839b3fa0e693afd817679c0b8944bef41def05a8b0ec72b7d4a` | 2,473,208 | CakeML licence (BSD-style) |
| `basis_ffi.c` | https://raw.githubusercontent.com/tanyongkiam/cake_lpr/a36874a8b750b43fe4b385b8ddbf5b033e46a3fa/basis_ffi.c | `8e30d84fdcb2177aa5571d7fa6661a2fae5ecfd56baa0ce49c65f9233a9f87cb` | 12,736 | CakeML licence (BSD-style) |

All are open. The Lean repository's large files are real content at that
commit (their git blob ids match the tree), not LFS pointers; the snapshot URL
is the file's SHA-1, so it cannot change. The data stay with their authors and
are fetched, never copied here.

## Run

    python3 hexagon/check.py

in `buildpack-deps@sha256:88c9154b6b438be20b616e2e74c158cfd79feafc6bcf1d9a3b47874b38c91992`
(Debian bookworm: gcc and g++ 12.2, Python 3.11; nothing else is needed), with
the inputs at `inputs/` and `ECDYSIS_SEED` set. `--cubes N` re-solves N cubes
instead of eight (a different bundle, with a longer runtime).

## What it writes

`results/outputs.json`, the 20 values a receipt carries:

| output | meaning |
|---|---|
| `witness_ok` | 1: 29 distinct points, no three collinear, no empty hexagon |
| `witness_collinear_triples` | collinear triples among the 29 (0) |
| `witness_convex_hexagons` | six-point subsets in convex position (5,335) |
| `witness_empty_hexagons` | of those, with no other point inside (0) |
| `witness_layers` | sizes of the convex layers, outermost first |
| `cubes_sampled`, `cubes_ids` | how many cubes were drawn, and which (by their line in `marijn-cubes.icnf`, from 1) |
| `cubes_unsat`, `cubes_verified` | how many CaDiCaL found UNSAT, and how many of those cake_lpr verified |
| `coverage_clauses` | the classification of `cube_tautology.cnf`'s clauses (rule 3) |
| `coverage_unsat`, `coverage_verified` | the coverage formula UNSAT, and its proof verified |
| `controls_passed`, `controls_total` | the controls that behaved as required, of six |
| `extra_sets_checked`, `extra_sets_with_hole`, `extra_rejected` | seeded 30-point sets checked, those with an empty hexagon, draws rejected |
| `solver`, `checker` | the tools, with their versions |
| `test_passed` | the registered test on the above |

`results/detail.json` holds everything else: per cube its literals,
conflicts, seconds and the checker's last line; the coverage run; every
control; each seeded point with its empty hexagons; the formula's counts
(8,191 of its 452,000 clauses repeat another); the compiler's version.
Timings and conflict counts are kept out of `outputs.json`: conflicts depend
on the compiled solver, timings on the machine.

## Runtime and repeatability

The receipt command took 2,066 s (34 minutes) under the runner's restrictions
(`--network none --cpus 2 --memory 4g --read-only`, `/tmp` a noexec tmpfs, the
checkout read-only, only `ECDYSIS_SEED` set), on two CPUs of an Intel Xeon at
2.8 GHz, with the seed 64 "a": 70 s building the tools, about 30 s reading and
classifying the inputs, 85 s for the coverage formula (312,453 conflicts), and
the rest the eight cubes, two at a time: 167, 227, 235, 300, 338, 511, 635 and
1,143 s (186,043 to 1,004,598 conflicts; 444 s on average). On one CPU it
would be about 75 minutes (estimated from those times and the build). Which
cubes are drawn depends on the seed, and their cost has a heavy tail (the
authors' slowest took nearly an hour), so another seed can take longer.
Memory, sampled during the runs, stayed near 2.4 GB: two cake_lpr of 1.05 GB
each (they touch their whole heap), two solvers of 110 to 240 MB, and the
script at 40 MB; the three large inputs are read in a child process whose
memory is returned before the solvers start.

- **The same outputs.** A second run with the same seed took 2,112 s and
  wrote a byte-identical `outputs.json` (SHA-256
  `fc6f95bd33ab15691a3427666b85ea7edb8c7ff154eeeeac9fbdce19e4c81b04`) and a
  `detail.json` identical apart from timings: every conflict count matched,
  the cubes taking 167 to 1,215 s. The two builds of CaDiCaL differ only in
  the compile time that `version.cpp` embeds (and the build ID that hashes
  it); the two cake_lpr are byte-identical.
- **Other machines.** `outputs.json` holds counts, verdicts and names, which
  do not depend on how fast the machine is or on the search the solver takes;
  timings and conflict counts stay in `detail.json`. The solver is compiled by
  the pinned image's g++ without `-march`, so it is the same program on any
  x86-64 machine apart from the compile time it embeds, and its search was
  the same in both runs.
- **x86-64 only.** The image digest names a multi-platform index; on another
  architecture the run stops with a message, as `cake_lpr.S` is x86-64
  assembly (its repository also has an ARMv8 build, not used here).

## What it cannot check

- **The link from F to the theorem.** The Lean proof that F's
  unsatisfiability implies h(6) <= 30 (Subercaseaux et al., ITP 2024) is
  trusted, not re-run: Lean and mathlib cannot be provisioned in the sandbox.
  So is the identity of `final-30-ours-flat.cnf` with what the Lean encoder
  (`lake exe encode hole 6 30`) emits.
- **The whole proof.** Eight of 312,418 cubes are re-solved. A cube costs
  167 to 1,215 s here with its proof, about 450 s on average in the trials (the
  authors' run averaged just under 200 s a cube for their encoding, and the
  Lean encoding took 25,876 CPU hours in all, about 300 s a cube), with a heavy
  tail. The 64 to 200 cubes first planned would take about four to twelve hours
  on two CPUs. A sample of eight would catch a defect shared by many cubes; it says
  almost nothing about a single bad one. The coverage check, by contrast, is
  complete.
- **The authors' own runs.** No proofs were stored, so this re-solves rather
  than re-checks them, with a later CaDiCaL.
- **The tools beyond themselves.** cake_lpr is verified in CakeML down to its
  assembly; its C wrapper, the compiler, the kernel and this script are
  trusted. CaDiCaL is not trusted: only its proofs are.
- **Every 30-point set.** The seeded points are a handful of random instances.

## Tests

`python3 -m unittest discover -s tests` runs `tests/test_hexagon.py` among the
lab's tests: hexagon counts against a reference written from the definitions,
the readers and their refusals, the draws, the coverage classification, and a
whole run with made-up inputs and stand-in tools (a satisfiable cube caught
with its model checked, a rejected proof and a foreign coverage clause failing
the test, a checker out of heap tried again). With `HEXAGON_TOOLS` naming a
directory holding the cadical and cake_lpr a run built, it also runs the
proof controls and the solver-to-checker pipe; with the inputs at `inputs/` or
in `HEXAGON_INPUTS`, the witness's counts. The stand-in tools are scripts, so
in the sandbox `TMPDIR` must point under `results/`.
