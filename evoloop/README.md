# evoloop: Sayama's self-reproducing loops, evolving toward the smallest

`check.py` tests Sayama, "A New Structurally Dissolvable Self-Reproducing Loop
Evolving in a Simple Cellular Automata Space" (Artificial Life 5(4), 343–365,
1999), claim `ext:60cc0fcc84ce2b54`: "The experiment with evoloop met with the
intriguing result that, though no mechanism was explicitly provided to promote
evolution, the loops varied through direct interaction of their phenotypes,
smaller individuals were naturally selected thanks to their quicker
self-reproductive ability, and the whole population gradually evolved toward
the smallest ones."

The registered test: refuted if, under the evoloop's rules as Sayama published
them (Artificial Life 10, 2004, Appendix A.1), with the size-13 ancestor (genome
774477777777777) alone at the centre of periodic spaces of 199 × 199, 200 × 200
and 201 × 201 sites for 50,000 updates (his thesis's setting): in two of the
three, size 4 is not strictly the most numerous loop size at the end (loops
counted by their square holes); or, built alone in the ancestor's layout, loops
of sizes 4 to 13 do not give their first offspring sooner the smaller they are,
or one gives a loop of another size first. Every rule was fixed before any seed
existed; the docstring of `check.py` states them in full.

## Inputs

Golly's `Rules/Evoloop.rule` (16,263 bytes) and `Patterns/Loops/Evoloop.rle`
(967 bytes), from AlephAlpha/golly at `dcbc087` (GPL-2.0-or-later), read as
text. The rule is Golly's transcription of a 1999 applet's table; the rle is the
ancestor. The paper's own text is closed, so the setting is that of the thesis
it came from (Sayama 1998, section 6.3.1), and the rules are Sayama's own: Table
2 of his 2004 paper, transcribed in `check.py` (258 rules, hashed), and that
paper's steps for every situation Table 2 leaves undefined.

## What runs

1. **Two rules.** Sayama's, from Table 2, its rotations and his completion;
   Golly's, from its table. They agree on every situation Table 2 defines and
   differ on 10,602 it leaves undefined: there Sayama's dissolves the site
   (state 8) and the applet's does not. Sayama's rules are the test's.
2. **Loops built in the ancestor's layout.** A loop of size n carries the
   genome 77 44 7^(n−2); size 13 built so equals the rle site for site.
3. **The census.** A loop is counted by its hole: a rectangle of 0s on the
   torus whose ring is all sheath. A square hole of side h is size h + 2.
4. **The three spaces**, 50,000 updates each, a census every 1,000.
5. **Alone**: each size from 4 to 13 built alone, a census at every update, to
   the update of its first offspring.
6. **Beside the test**: the three spaces under Golly's rules; spaces of 100,
   150, 250 and 300 sites a side; the mean loop size early and late.

numpy and scipy, in the pinned scipy-notebook image; under three minutes on two
cores. Tests: `python3 -m unittest tests.test_evoloop` (with Golly's files at
`inputs/` or `EVOLOOP_INPUTS`, a short run).

# selfprotect.py: Sayama's self-protecting evoloops and diversity

`selfprotect.py`, with the update and the census in `sp.c`, tests Sayama,
"Self-Protection and Diversity in Self-Replicating Cellular Automata"
(Artificial Life 10(1), 83–98, 2004), claim `ext:10b8167c671aaa9f`:
"Simulation results imply a positive effect of those mechanisms on diversity
maintenance, especially when the self-protection is moderate so that it
conserves both the attacker and the attacked."

The registered test: refuted if, under the paper's own rules (Appendix A:
Tables 2 to 6 and their steps), from the size-13 ancestor (genome
774477777777777) alone in a 400 × 400 periodic space for 1,000,000 updates,
loops counted by size and the trait-distribution entropy sampled every 40
updates from 200,000 to 1,000,000: the mean entropy of any of the shielded,
deflecting and poisoning SP evoloops is not above the original evoloop's; or,
from the ancestor 777777777777744, the deflecting one's is not above the
original's, or the poisoning one's is above the deflecting one's.

## Inputs

Golly's `Patterns/Loops/Evoloop.rle` (967 bytes, AlephAlpha/golly at
`dcbc087`, GPL-2.0-or-later), the ancestor, read as text. The rules are the
paper's: Table 2 is `check.py`'s, and Tables 3 to 7 are transcribed in the
module from the author's copy (SHA-256 `43b09426…29d0d`) and hashed; poppler,
pdfminer and pypdf extract every table alike, and Table 2's extraction gives
`check.py`'s hash.

## What runs

1. **Four tables** over ten states, each rule with its rotations, then each
   model's own steps for the situations its tables leave undefined (A.1, A.2.1
   or A.2.2). The original's equals `check.py`'s on states 0 to 8, and every SP
   model keeps every situation Table 2 defines.
2. **Two ancestors**: Golly's rle, and the same loop built in its layout with
   777777777777744 (its cycle of genes read from the fifth).
3. **Eight runs**, the four models from each ancestor, alone in a 400 × 400
   torus for 1,000,000 updates, in C, two at a time.
4. **The census** of `check.py`, in C (loops counted by their square holes
   ringed with sheath), every 1,000 updates and every 40 after 200,000; the
   entropy H = log N − (1/N) Σ nᵢ log nᵢ averaged over the 20,000 censuses at
   updates 200,040 to 1,000,000.
5. **Controls**: the C update against numpy in small tori, the C census
   against `check.py`'s on seed-drawn grids, the second ancestor alone, and no
   SP model departing from the original before the first offspring.

numpy, scipy and the image's gcc, in the pinned scipy-notebook image; about 26
minutes on two cores. Tests: `python3 -m unittest tests.test_selfprotect` (with
the rle at `inputs/` or `EVOLOOP_INPUTS`, a short run).

## The receipt

`0c2e7e47…` (13 October, at `772868d`, a reproduction; the claim 0.71,
supported). Mean entropy from the size-13 ancestor: original 0.0427, shielded
0.0788, deflecting 0.1764, poisoning 0.5483; from 777777777777744: original
1.3819, shielded 1.5395, deflecting 1.6227, poisoning 1.1221. Controls 11 of
11. A trial in the image under another seed gave the same outputs (the
evoloop is deterministic; the seed draws only the census control's grids).
