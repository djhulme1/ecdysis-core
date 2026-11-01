# Working on Ecdysis as a team

Five lanes, one trunk, three environments (`docs/ENVIRONMENTS.md`), and a
rule for everything that must not happen: make it impossible, rather than
remembered. This page says who does what, where, and how a change gets to
the record.

## The lanes

| Lane | Owns (and reviews, by `.github/CODEOWNERS`) | Works mostly on | Starting assignment |
| --- | --- | --- | --- |
| **Core and protocol** | `src/core/`, `src/api/`, `src/store/`, `migrations/`, `CONSTITUTION.md`, `audit/`, `wrangler.toml`, `.github/`, `scripts/` | The record's rules, the API and the connector, the log, credence; the deployment itself | Daniel |
| **Site, brand, UI and UX** | `src/web/`, `public/`, `docs/brand/`, `docs/fonts/` | Every page, its words, the brand, the typefaces, the media | Lucy (the brand kit is hers) |
| **Outreach** | the `dash` repository (the console at dash.ecdysis.app and its desks) | Reaching people; the control panel; the drafts the owner or Lucy approve | — |
| **The red team** | `harness/`, `test/adversarial/` | Breaking the protocol on staging; turning every hole into a test | Chris (change in `CODEOWNERS` if the lanes are divided otherwise) |
| **The lab** | the lab's own code on the ZBook (Exuvia, Imago, the fleet) | Populating and checking the record with agents | Daniel |

Stewardship (deciding complaints, verifying operators, the switches) is not
a lane: it is a role on the record, held by the owner and Lucy in
production and by all three on staging, and done on `/steward`, never in
code.

### Core and protocol

The pure core (`src/core/`) takes no runtime dependencies and reads no
environment, so every number recomputes from the public log anywhere; a
change to it ships with a test, a security property with an adversarial
test, and any movement of a credence, status, tier or finding updates
`audit/v2-baseline.json` deliberately and says who gains and who loses. A
protocol change lands the way `credence/0.5` did: built and dormant behind
a switch, enacted later by an amendment under Article V. Migrations are
backwards-compatible (expand, then contract in a later change), because a
preview runs new code on the staging database as it stands.

### Site, brand, UI and UX

Everything a person sees is in `src/web/` (pages, copy, CSS), `public/`
(the media and the typefaces) and `docs/brand/`. The seam is the view: a
page takes the record as the service hands it over and shows it; it imports
nothing from `src/core/`, and it ships no script (the CSP forbids it, and the
tests check). A pull request's preview is where this lane lives: open the
address CI comments on the pull request, on a phone, and look. Values are
escaped, pages are script-free, and the vocabulary sweep in the tests keeps
retired words (papers, juries, vouching) off every surface.

### Outreach

The outreach console and its desks live in their own repository and talk to
Ecdysis as anyone does: through the public API and the connector, as an
operator with its own agents. There is no back door for it; what its agents
file is signed and counts like anyone else's. Its own data (contacts,
drafts, approvals) stays in its own store, never in the record. A staging
console pointed at `api-staging` (the `STAGING_URL` variable) is where its
changes are tried; its contract tests against staging tell outreach when an
API change breaks it, before production does.

### The red team

The question is always the same: what can an operator, or a crowd of
them, make the record say that is not so, and at what cost? Staging is the
field: its own record, reset at will, with the staging door minting
operators at any tier (`docs/ENVIRONMENTS.md § The staging door`) and the
harness (`harness/`) signing everything with the archive's own code.
Measure, do not opine: a run reports what moved (credence, status, tier,
leaderboard, findings) and what it cost (operators, agents, requests,
effort), compared with what an honest population gets from the same work.
`npm run recompute:v2` against the staging log shows exactly what every
act did. Then:

- a hole becomes a test in `test/adversarial/` before its fix merges, so it
  cannot reopen;
- anything exploitable on **production** goes in a private security
  advisory (GitHub → Security → Advisories → New draft), never in an issue
  or a pull request, until the fix is live;
- production is attacked only when announced and with the owner's say-so,
  and never with a reset or a hazard hold involved; everything else happens
  on staging.

Breaking staging is the job; say in the channel when a run will flood it,
and when a reset is wanted.

### The lab

The agents that populate and check the record run where their operator
runs them, with keys that never leave that machine, and register, publish
and check through the public API like any outside agent. The lab's code is
the lab's own; the record's code never knows which agents are the owner's.

## How a change gets to the record

1. Branch from `main`; keep it short-lived.
2. Open the pull request against `main`, never against another branch.
   Say what changed and why; name the tests.
3. CI must be green: tests, typecheck, replay audit, both Workers' builds.
   The preview address appears as a comment; look at it.
4. One approval from a code owner of every path touched (the owner can
   merge his own). Squash-merge.
5. The merge deploys to staging at once. Watch the Deploy run's summary.
6. Production waits for a tap of approval from the owner (the `production`
   environment's required reviewer), then deploys and probes itself,
   rolling back if the probes fail.

Everything above is enforced: branch protection for 1 to 4, the Deploy
workflow for 5 and 6. If a rule can be broken by forgetting, it is a bug in
this page, not in the person.

## Agents as colleagues

Claude sessions open pull requests like anyone else, under the GitHub
identity of the person who started them, and `CLAUDE.md` is the standing
brief every session reads first: the lanes, the environments, the
commands, the security rules. A session never holds a production secret or
a private key, never deploys by hand, and never merges; the person does.

## Joining

1. Accept the invitation to the repository (write access).
2. Put your `@hulme.ai` address on your GitHub account (Settings → Emails):
   that is how `CODEOWNERS` names you for reviews.
3. Get the staging door key from the owner, and the address of staging from
   the `STAGING_URL` variable (Settings → Secrets and variables → Actions →
   Variables) or the Deploy run's summary. Sign in at
   `<staging>/staging/door?key=…&email=<your address>`.
4. Join the team channel (the Watch posts there).
5. Clone, `npm ci`, `npm test`, `npm run typecheck`. Read `CLAUDE.md`,
   `docs/ENVIRONMENTS.md` and, for your lane, the section above.
6. Open your first pull request.
