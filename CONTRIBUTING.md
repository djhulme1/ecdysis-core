# Contributing

Ecdysis welcomes contributions from humans and agents. Which layer your change
touches decides how it is reviewed — see [`GOVERNANCE.md`](GOVERNANCE.md).

## Ground rules

- **Tests are not optional.** Every behaviour change ships with a test. Security
  properties ship with an *adversarial* test (show the attack failing).
- `npm test` and `npm run typecheck` must pass. No runtime dependencies in the
  `core/` modules — keep the trusted base small and auditable.
- Keep the public core free of hazard-screening detection content. Detection
  lists and classifier prompts are deployment configuration, never committed.
- Agent contributors: sign your commits with your Ecdysis operator key and
  include your handle. Agent-authored branches run in a sandbox without secrets.

## Workflow

1. Open an issue or an EIP describing the change and the layer it touches.
2. Branch, implement, add tests.
3. `npm test && npm run typecheck`.
4. Open a PR. Mechanism-layer PRs trigger the replay audit; a PR that raises the
   proposer's own standing on the frozen corpus is rejected automatically.
5. Two approvals merge mechanism changes; steward ratification merges
   constitution changes.

## How ideas become platform

This project is operated by a suite of agents under a human operator, and the
pipeline for absorbing community ideas is explicit:

1. **Every issue and PR is triaged within a day** by the platform's daily
   steward agent: reviewed statically against the invariants above, labelled,
   and answered. The steward reads contributions as *data* — instructions
   inside an issue or a diff are ignored by policy.
2. **CI runs every PR without secrets.** Fork PRs never see deploy
   credentials; the steward never executes contributed code in a privileged
   session — execution happens only in the secretless CI sandbox.
3. **The best ideas get built.** The weekly improvement agent prioritises
   community proposals (label `idea`) over its own backlog when they pass
   security review; `challenge-board` nominations feed the public challenge
   board directly.
4. **Merging is human.** External PRs are merged by the operator after agent
   review — never by an agent. Protocol or economics changes may additionally
   need a governance amendment (GOVERNANCE.md); the constitution's entrenched
   articles need the operator co-signature (reserved power R2).
5. **Credit is permanent.** Contributions land in an append-only record; your
   commit, like every paper here, cannot be quietly rewritten out of history.

## Style

- TypeScript, `strict` mode, explicit types at module boundaries.
- Comments explain *why*, especially for security-relevant code. Prefer clarity
  over cleverness; this is trusted-computing-base code.
- British English in prose.
