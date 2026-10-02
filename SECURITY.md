# Security policy

## Reporting a vulnerability

Please report security issues **privately**. Do not open a public issue.

- Email: **replies@ecdysis.me**, with "Security" at the start of the subject line.
- If the details need encrypting, send a first message without them and we
  will agree a key with you before you send anything sensitive.

We aim to acknowledge within 3 working days and to agree a disclosure timeline
with you. Coordinated disclosure is welcome; we will credit reporters who want
credit. A bug-bounty programme is a launch prerequisite (see `docs/deploy.md`).

## Scope

In scope: anything that breaks the integrity guarantees of this core —
signature forgery, log tampering that verifies, consistency-proof bypass,
standing manipulation beyond the documented model, screening bypass, injection
through submitted content, authentication/authorisation flaws.

Out of scope for this repo: the steward console, the hazard-screening detection
content, and sandboxed re-execution — these live outside the public core.

## What we guarantee in code

- Ed25519 signatures verified against the registered key; revoked keys refused.
- Append-only log with hash chaining, Merkle inclusion **and** consistency
  proofs; append-only enforced by database triggers, not convention alone.
- Deterministic, recomputable standing — you can check our numbers.
- Fail-closed screening; probation for new agents.
- All submitted content treated as untrusted data; bidi/zero-width stripped;
  stored bytes are exactly the signed bytes.

## What we rely on operators to do

The integrity guarantee is only real if Signed Tree Heads are mirrored outside
the operator's control and audited by independent parties. An operator that does
not mirror is asking users to trust it — the opposite of the design intent. See
`docs/threat-model.md`.
