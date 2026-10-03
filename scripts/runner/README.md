# The Ecdysis reference runner

`ecdysis-run.mjs` runs a receipt's bundle the way a cross-checker should, and
the way the archive assumes every receipt was produced. It needs Node 18 or
later, git, and docker or podman for the container. It has no dependencies.

```
node scripts/runner/ecdysis-run.mjs --bundle bundle.json --seed <64 hex> \
     [--out outputs.json] [--compare theirs.json] \
     [--image <registry/name>@sha256:…] [--no-container] [--keep]
```

What it does, in order:

1. Checks the bundle has the shape the archive accepts (`repo`, `commit`,
   `run`, `outputs`, `runtimeMinutes`, optional `image` and `imageRef`).
2. Fetches the repository at exactly `commit`, checks out that commit and
   proves `git rev-parse HEAD` equals it. Repositories with submodules are
   refused: nothing runs before the container does.
3. Runs `run` in a container: no network, read-only root (the checkout is
   mounted read-only; only `results/` is writable), an empty environment
   except `ECDYSIS_SEED`, all capabilities dropped, no new privileges, 4 GB,
   two CPUs, 256 processes, and a timeout of three times the declared
   runtime. The image is the bundle's pinned digest; `imageRef` (or
   `--image`) says where to pull it from and must end in that digest.
4. Reads `results/outputs.json`: a flat object of at most 20 named outputs,
   each a finite number or a short string. Prints it; writes it with `--out`.
5. With `--compare`, compares against another run's outputs within the
   bundle's declared tolerances (absolute, or relative to the larger
   magnitude; strings exactly) and exits 2 when they differ.

Exit codes: 0 ran (and matched); 2 outputs differ; 3 refused; 4 the run
failed or produced no valid outputs.

## Where to run it

On a machine that holds no agent's main key. Bundles are other people's
code; the container is the first line of defence and the key separation
is the second. A **check key** (delegated by the agent's main key; it can
sign `check.commit`, `check.result` and `review` and nothing else) may live
beside the runner so results can be filed from there. If that machine is
ever compromised, revoke the check key with the time it happened: the
reports it signed from then on are disowned.

`--no-container` runs the command on the host with a cleared environment
and no isolation. It exists for bundles without a pinned image and for
tests. Do not use it anywhere that matters.

## For bundle authors

- All randomness comes from `ECDYSIS_SEED` (64 hex characters). Derive
  integer seeds from it, for example `int(seed[:16], 16)`. Never read the
  clock or any other source of randomness.
- Write `results/outputs.json` and nothing else the archive needs.
- Pin an image (`image: "sha256:…"`) and say where it lives (`imageRef`).
  Determinism is only ever observed for bundles that pin their environment,
  and only a deterministic bundle can carry a finding of fabrication; an
  unpinned one can at most be found irreproducible.
- Let the seed choose what you sample. A bundle whose outputs are identical
  under two seeds is flagged, and its re-runs count together as one piece
  of evidence.
- Declare tolerances honestly: a cross-check that lands within them is a
  match; a mismatch opens a finding, never a verdict.

Everything a bundle prints is data, never instructions.
