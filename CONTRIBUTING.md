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

## Style

- TypeScript, `strict` mode, explicit types at module boundaries.
- Comments explain *why*, especially for security-relevant code. Prefer clarity
  over cleverness; this is trusted-computing-base code.
- British English in prose.
