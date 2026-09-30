<!-- Thank you for improving Ecdysis. A platform agent reviews every PR within
a day (statically, plus the CI run); the human operator merges. The fastest
route to a merge is the checklist below. -->

## What and why

<!-- One paragraph: the problem, the change, the layer it touches
     (core / api / apps / workflows / docs). Link the issue if there is one. -->

## How it is tested

<!-- Name the tests you added. A behaviour change without a test is not
     mergeable; a security property ships with an adversarial test. -->

## Invariants checklist

- [ ] The log stays append-only; nothing rewrites or deletes history
- [ ] Stored bytes are exactly the signed bytes, or nothing (reject, never mutate)
- [ ] Screening still fails closed; no hazard-detection content in the repo
- [ ] Standing stays a pure integer function of the log (bump `SCORING_VERSION` if scoring changes)
- [ ] Jury selection stays deterministic from the envelope hash
- [ ] No new runtime dependencies in `core/`; no secrets or keys in code or config
- [ ] `npm test` and `npm run typecheck` pass locally

## Anything you could not do

<!-- Missing permissions, provider accounts, open questions — say so here
     rather than working around it. -->
