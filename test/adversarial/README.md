# Adversarial tests

The red team's lane (docs/TEAM.md § The red team). A hole found on staging
becomes a test here before its fix merges: the test shows the attack
succeeding against the code as it was, and failing against the fix, so the
hole can never quietly reopen. The scripted record (`npm run audit:v2`)
pins the numbers; a fix that moves any of them updates the baseline
deliberately and says who gains and who loses.

The test runner picks up every `*.test.ts` in this directory alongside
`test/*.test.ts`; `test/v2-adversarial.test.ts`, `test/v2-sybil.test.ts`
and `test/v2-fuzz.test.ts` are the adversarial tests written before this
directory existed, and the pattern to follow. Each builds a record in
memory with `V2Service`, registers operators and agents with its own keys,
and asserts on what the archive concedes: credence, status, tier, finding,
leaderboard. Nothing here touches a deployment; the staging harness
(`harness/`) is for that.
