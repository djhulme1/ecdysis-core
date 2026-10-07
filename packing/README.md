# packing: the packing chromatic number of the square grid is 15

`check.py` tests Subercaseaux and Heule, "The Packing Chromatic Number of
the Infinite Square Grid is 15" (TACAS 2023, arXiv:2301.09757), claim
`ext:18c6f5de78f846d3`.

The registered test: the packing chromatic number of the infinite square
grid is 15. Refuted by any of: a packing colouring of Z^2 with 14 colours;
the 72x72 periodic 15-colouring of Martin et al. (arXiv:1510.02374v3) having
two cells of colour c within l1 distance c; or, for the paper's radius-15,
14-colour instance with colour 6 at the centre, a cube of its split
(5,217,031 cubes) whose formula is satisfiable or whose proof fails a
verified checker, or the cubes failing to cover the search space.

The receipt checks the upper bound's witness completely, the cover of the
proof's split completely (twice: exactly, and by the verified checker in ten
parts), the reduction from the definition to the authors' formula clause by
clause, and the proof's cubes by a seeded sample. Every rule was fixed before
any seed existed; the docstring of `check.py` states them in full. It imports
`hexagon/check.py` for building the solver and the checker, solving with the
proof streamed into the checker, the seeded draws and the pigeonhole proof
controls.

## What runs

1. **The witness, exactly.** The 72 x 72 table is read as data from the
   figure labelled `fig:15` of `PackingCromaticNumberDAM.tex` in Martin,
   Raimondi, Chen and Martin's e-print (read from the tar in memory; its one
   tabular has 72 columns `c` and 72 rows of integers joined by `&`; anything
   else is refused). Read as a colouring of Z^2 of period 72 both ways, it is a
   packing colouring when, for every cell of colour c and every offset d with
   1 <= |d|_1 <= c, the cell at d (mod 72) is not of colour c; since 15 < 72 no
   offset wraps onto its own cell, so this is exactly the plane's condition.
   It holds: 15 colours, counts 2,592, 648, 648, 288, 288, 144, 144, then 72
   (colours 8 to 11) and 36 (12 to 15), no violation. Each colour's closest
   pair is at c + 1 for odd c and c + 2 for even c up to 11, and at 16 for 12
   to 15.
2. **The reduction, clause by clause** (reported beside the test; the
   paper's Lemma 3, Lemma 8 of arXiv v2). The paper trusts only its direct
   encoding D(15,14,6) and connects it to the solved formula by DRAT proofs
   (symmetry breaking via SR, the re-encoding via RAT) that the repository
   holds only for its 6-11 example. Instead, every one of the formula's
   91,530 clauses is classified against the definition: 481
   at-least-one-colour clauses, 52,320 pairs of cells of a colour c within
   distance c, the centre unit (colour 6 at (0, 0)), 4,675 membership
   clauses r v -x (which define the 935 plus-shaped regions, and must equal
   the placement file's, in its order), 25,612 clauses -r v -x for a cell
   outside the region and within c of all of it, 8,112 clauses -r v -s for
   disjoint regions all within c of each other, and the 329
   symmetry-breaking clauses of the paper's five layers, exactly. None is
   left over (`formula_unjustified` 0). So any packing colouring of the
   diamond with colour 6 at the centre gives a model of the formula: move
   the highest layer colour t found within t // 2 of the centre into the
   octant 0 <= i <= j by a symmetry of the square (it occurs there at most
   once), and set each region variable to the "or" of its cells.
3. **The cubes, regenerated.** The paper's Algorithm 1 with P = 6, T = 7,
   R = 9, as the authors' `structured_api.py` runs it: colours 14 down to 8,
   for each its nine regions with the least sum of distances to the centre
   (centres (0,0), (-1,2), (2,1), (1,-2), (-2,-1), (1,3), (3,-1), (-1,-3),
   (-3,1); the paper's least distance picks the same nine); for p = 6 down to
   0, every p of those colours and every choice of one region for each, with
   the other colours' 9 regions negated when p < 6. 5,217,031 cubes with
   59,038,434 literals, SHA-256 `49e5536d...4245ed` as iCNF text.
4. **The proof, sampled.** 1,000 cubes are drawn by the seed. For each, the
   formula with the cube's literals as unit clauses is solved by CaDiCaL,
   whose LRAT proof goes down a pipe into cake_lpr as it is written. A cube
   counts when CaDiCaL says UNSATISFIABLE and cake_lpr says `s VERIFIED UNSAT`.
   A cube that reaches 10,000,000 conflicts or 1,800 s is stopped and counted
   as timed out (not a refutation, not a failure; the test needs none). A
   satisfiable cube would have its model checked and would refute the claim.
5. **The cover, completely, twice** (the paper's Lemma 1; Lemma 6 of arXiv
   v2). (a) Exactly: each cube must give each split colour one positive
   literal, all nine negations, or nothing. A cube satisfied by an
   assignment's minimal form (per colour: no region true, or only its least
   true region) is satisfied by the assignment, so it is enough that the
   10^7 minimal assignments are covered; they are marked, cube by cube, and
   all are. (b) By cake_lpr: the negated cubes go into ten parts by colour
   14: for t = 1..9, the unit r(t, 14) with the negations of the cubes where
   r(t, 14) is positive (468,560 clauses each), and the nine units -r(t, 14)
   with the negations of the cubes without colour 14 (1,000,009 clauses).
   The unit sets cover every assignment and the rest of each part is negated
   cubes, so ten refutations show the cubes form a tautology. Each part is
   refuted by the resolution proof the paper's tautology part describes
   (from E(Q, S, m + 1) and the E(Q + c, S + t, m + 1) to E(Q, S, m), level
   by level; 52,063 and 111,112 lemmas), written by the script and checked
   by cake_lpr; all ten verify. The cover needs no clause of the formula.
6. **Controls**, eleven, each of which must behave as stated: the witness
   with a 15 copied to distance 15 across the torus's edge, and with a 1
   copied next to a 1, fails; the formula with a clause forbidding colour 6
   at two cells 7 apart has it found unjustified; the formula without the
   at-least-one-colour clauses beyond radius 8 is satisfiable (in 0.1 s),
   its model satisfying every kept clause and violating 113 removed ones;
   hexagon's three pigeonhole proof controls; and the split built small (4
   colours, 3 regions, P = 3, 175 cubes): CaDiCaL refutes its negated cubes
   with a proof cake_lpr verifies (the paper's SAT call, at a size that
   fits), its four parts' proofs verify, and with one cube removed the exact
   check finds the uncovered assignment and that part's proof is rejected.

`test_passed` is 1 when the witness holds with all 15 colours used (a valid
table with fewer would itself refute the lower bound), every sampled cube
that finished is UNSAT with a verified proof, none timed out, and the cover
holds (5a, and 5b for all ten parts).

### Why the cover is not one SAT call

The paper generates the tautology proof "using a simple SAT call". Here the
negated cubes are one CNF of 5,217,031 clauses (335 MB). In the sandbox,
CaDiCaL 2.1.3 had not refuted it after 606 s, and cake_lpr with a 2,560 MB
heap ran out of heap after 231 s, still reading it (the formula is minimally
unsatisfiable: every refutation uses all of its clauses). The ten parts each
fit (cake_lpr with a 1,536 MB heap, two at a time, about 3.1 GB in all), and
the SAT call itself is kept as a control on the small split. The proofs are
written by `check.py`, which is not trusted: only cake_lpr's verdict counts.

## The tools, built in the run

As in `hexagon/`: CaDiCaL 2.1.3 from Debian's `cadical_2.1.3.orig.tar.gz`
(`g++ -O3 -DNDEBUG -DNBUILD`, about 70 s on two CPUs) and cake_lpr from its
two files at commit a36874a (`gcc -O2 -std=c99`), both into `results/build/`
(x86-64 only: `cake_lpr.S` is x86-64 assembly). cake_lpr runs with a 512 MB
heap per cube (a check that runs out is repeated alone with 2,560 MB) and
1,536 MB per part of the cover. The solver's limits are passed by a two-line
shell script written next to it, `results/build/cadical-capped`
(`cadical -c 10000000 -t 1800 ...`).

## Inputs

| name | URL | SHA-256 | bytes | licence |
|---|---|---|---|---|
| `1510.02374v3.tar.gz` | https://arxiv.org/e-print/1510.02374v3 | `a8539f6859d8a9c85a2611b832f654d8ef7fbc4932d7a17c93fe5fa120b9b1c2` | 20,068 | arXiv non-exclusive distribution licence 1.0 |
| `P15_14_6_S5.cnf` | https://raw.githubusercontent.com/bsubercaseaux/PackingChromaticTacas/305d6aa84d487676135aa456bc58831b6b2d38d7/formulas/P15_14_6_S5.cnf | `36deda618e7d17d3af2d7352de5ebf010ae76ba8ef7b08cf1c8a3c92d1149084` | 1,329,373 | GPL-3.0 |
| `placement-15-14-plus` | https://raw.githubusercontent.com/bsubercaseaux/PackingChromaticTacas/305d6aa84d487676135aa456bc58831b6b2d38d7/placements/placement-15-14-plus | `dcbfcecf8149303c71de4bab675df2e3c8fc29eb44d0e0db034ad5f8a267ea0d` | 44,901 | GPL-3.0 |
| `cadical_2.1.3.orig.tar.gz` | https://snapshot.debian.org/file/f2c90120e8f60cb08199a32bcb9c9406bbf76443 | `abfe890aa4ccda7b8449c7ad41acb113cfb8e7e8fbf5e49369075f9b00d70465` | 731,545 | MIT |
| `cake_lpr.S` | https://raw.githubusercontent.com/tanyongkiam/cake_lpr/a36874a8b750b43fe4b385b8ddbf5b033e46a3fa/cake_lpr.S | `2f3af32d55083839b3fa0e693afd817679c0b8944bef41def05a8b0ec72b7d4a` | 2,473,208 | CakeML licence (BSD-style) |
| `basis_ffi.c` | https://raw.githubusercontent.com/tanyongkiam/cake_lpr/a36874a8b750b43fe4b385b8ddbf5b033e46a3fa/basis_ffi.c | `8e30d84fdcb2177aa5571d7fa6661a2fae5ecfd56baa0ce49c65f9233a9f87cb` | 12,736 | CakeML licence (BSD-style) |

arXiv answers the e-print URL with a redirect, on the same host, to
`https://arxiv.org/src/1510.02374v3`, which serves the gzipped tar
(`arXiv-1510.02374v3.tar.gz`; it holds `PackingCromaticNumberDAM.tex`,
SHA-256 `445772cc...1fefd8`, and `elsarticle.cls`). Six of the archive's
eight inputs are used. The data stay with their authors and are fetched,
never copied here.

## Run

    python3 packing/check.py

in `buildpack-deps@sha256:88c9154b6b438be20b616e2e74c158cfd79feafc6bcf1d9a3b47874b38c91992`
(Debian bookworm: gcc and g++ 12.2, Python 3.11; nothing else is needed),
with the inputs at `inputs/` and `ECDYSIS_SEED` set. `--cubes N` re-solves N
cubes instead of 1,000 (a different bundle, with another runtime).

## What it writes

`results/outputs.json`, the 20 values a receipt carries:

| output | meaning |
|---|---|
| `witness_ok` | 1: a 72 x 72 table of colours 1..15 with no two cells of a colour c within c on the torus |
| `witness_colours`, `witness_counts` | colours used (15), and how many cells each has, colour 1 first |
| `witness_violations` | pairs of cells of a colour c within c (0) |
| `formula_unjustified` | the formula's clauses that the direct encoding does not justify (0; rule 2) |
| `cubes_total`, `cubes_sha256` | the regenerated cubes (5,217,031) and the SHA-256 of their iCNF text |
| `cubes_sampled`, `cubes_ids_head` | how many cubes were drawn, and the first twelve (numbered from 1 in the split's order) |
| `cubes_unsat`, `cubes_verified` | how many CaDiCaL found UNSAT, and how many of those cake_lpr verified |
| `cubes_timed_out`, `cubes_sat` | cubes stopped at the limits, and cubes found satisfiable |
| `cover_exact` | 1: every minimal assignment of the 63 split variables satisfies a cube |
| `cover_parts_verified`, `cover_ok` | parts of the negated cubes refuted with a verified proof (of 10), and the cover check |
| `controls_passed`, `controls_total` | the controls that behaved as required, of eleven |
| `solver` | the solver and the checker, with their versions |
| `test_passed` | the registered test on the above |

`results/detail.json` holds everything else: per cube its literals,
conflicts, seconds and the checker's last line; every part of the cover; every
control; the witness's counts and closest pairs; the formula's clause kinds;
the split's regions; the compiler's version. Timings and conflict counts are
kept out of `outputs.json`.

## Runtime and repeatability

The receipt command took 3,423 s (57 minutes) under the runner's
restrictions (`--network none --cpus 2 --memory 4g --read-only`, `/tmp` a
noexec tmpfs, the checkout read-only, only `ECDYSIS_SEED` set), on two CPUs of
an Intel Xeon at 2.8 GHz, with the seed 64 "a": 65 s building the tools, about
three and a half minutes regenerating the cubes, checking the cover both ways
and running the controls, and the rest the 1,000 cubes, two at a time. Every
cube was UNSAT with a verified proof and none came near the limits: 2.5 s at
the median, 6.4 s on average, 80.7 s at the 99th percentile and 257.8 s at
most (2,131,417 conflicts at most; 16 cubes took over a minute, 44 under a
second). On one CPU it would be about 110 minutes. Which cubes are drawn
depends on the seed, and their cost has a heavy tail (the authors' slowest
took 26 minutes to solve), so another seed can take longer; a cube is
stopped at 10,000,000 conflicts or 30 minutes. Memory stayed near 1 GB while
the cubes ran (two cake_lpr of 512 MB and two solvers) and reached about
3.1 GB while two parts of the cover were checked (cake_lpr touches its whole
1,536 MB heap).

- **The same outputs.** A second run with the same seed took 3,530 s and
  wrote a byte-identical `outputs.json` (SHA-256
  `27ea837e6815c48911cc177a7a02a7b08f8b21eb65f773264a4d3e92f18a4e2b`) and a
  `detail.json` identical apart from timings: every conflict count matched,
  the cubes taking 2.6 s at the median and 247.1 s at most. The two builds of
  CaDiCaL differ only in the compile time that `version.cpp` embeds (and the
  build ID that hashes it); the two cake_lpr are byte-identical.
- **Other machines.** `outputs.json` holds counts, verdicts, digests and
  names, which do not depend on how fast the machine is; timings and conflict
  counts stay in `detail.json`. The solver is compiled by the pinned image's
  g++ without `-march`, so it is the same program on any x86-64 machine apart
  from the compile time it embeds, and its search is the same: the limits are
  counted in conflicts, and the 30-minute wall-clock limit is a backstop (the
  slowest cube here took 258 s and 2.1 million conflicts).
- **x86-64 only**, as for `hexagon/`.

## What it cannot check

- **The lower bound's last step.** Lemma 2 of the TACAS paper (Lemma 7 of
  arXiv v2: D(15,14,6) unsatisfiable implies chi >= 15) is a hand proof,
  trusted here; as written it uses chi >= 14 from the authors' 2022 paper.
  (Recolouring a colour above 6 to 6 would need only that no packing
  colouring uses colours 1 to 5 alone.)
- **The whole proof.** 1,000 of 5,217,031 cubes are re-solved. A sample this
  size would catch a defect shared by many cubes; it says almost nothing about
  a single bad one. The cover and the reduction, by contrast, are complete.
- **The paper's formula exactly.** The released `P15_14_6_S5.cnf` has no ALOD
  clauses (the paper's P* has them; the repository's own instructions add them
  with `-A 1`, and the file's name has no A). They only add constraints, so a
  cube unsatisfiable here is unsatisfiable there, but the authors' timings
  (3.35 s a cube on average) were measured with them; here the median cube
  takes about 2.7 s and the mean about 10 s, with a heavier tail.
- **The paper's printed encoding.** The direct encoding the paper lists as its
  one trusted component (`direct-mini.py`, the appendix listing of arXiv v2)
  forbids colours 1..d at distance d, the reverse of the definition (colours
  d..k), and as printed would stop with a KeyError at the first pair farther
  apart than 14; the repository's `direct.py` is right. The reduction check
  above uses the definition, not either program.
- **The authors' runs.** Their proofs (122 TB of LRAT) were not kept, so this
  re-solves rather than re-checks them, with a later CaDiCaL.
- **The tools beyond themselves.** cake_lpr is verified in CakeML down to its
  assembly; its C wrapper, the compiler, the kernel and this script are
  trusted, and the witness, the reduction and the exact cover check are plain
  Python. CaDiCaL and the script's cover proofs are not trusted: only
  cake_lpr's verdicts are.

## Tests

`python3 -m unittest discover -s tests` runs `tests/test_packing.py` among
the lab's tests: the table's reader and its refusals, violations against a
brute-force count on small tori, every kind of unjustified clause caught, the
split's order against a transcription of the authors' `cubes()`, the exact
cover check against brute force (failing without any one cube), the cover's
parts and proofs against a small RUP checker written in the test, and a cube's
outcome read from a stand-in solver (its conflict limit a timeout). With
`PACKING_TOOLS` naming a directory holding the cadical and cake_lpr a run
built, also the small split's controls and a capped solve; with the inputs at
`inputs/` or in `PACKING_INPUTS`, also the witness, the reduction and the
split's full order and digest. The stand-in solver is a script, so in the
sandbox `TMPDIR` must point under `results/`.
