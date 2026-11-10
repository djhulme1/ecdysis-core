# Working on Ecdysis as a team

One trunk, three environments (`docs/ENVIRONMENTS.md`), a lane each, and a
rule for everything that must not happen: make it impossible, rather than
remembered. This page says who does what, where, and how a change gets to
the record.

## Who does what

| Person | Focus | Owns in this repository (`.github/CODEOWNERS`) | Works mostly in |
| --- | --- | --- | --- |
| **Daniel** | Vision, the protocol, the record, the deployment | Everything; alone on `src/core/`, `src/api/`, `src/store/`, `migrations/`, `CONSTITUTION.md`, `audit/`, `wrangler.toml`, `.github/`, `scripts/` | The record's rules, the API and the connector, the lab |
| **Lucy** | Go-to-market | `docs/go-to-market/`, `docs/brand/` | The outreach console (the `dash` repository), launch and listings, approvals of outreach drafts, her agents |
| **Chris** | UI/UX and testing | `src/web/`, `public/`, `docs/fonts/`, `docs/brand/`, `harness/`, `test/adversarial/` | The site's pages on previews and staging, the harness, his agents |

Each also builds agents that support Ecdysis (below). Stewardship (deciding
complaints, verifying operators, the switches) is not a lane: it is a role
on the record, held by Daniel and Lucy in production and by all three on
staging, and done on `/steward`, never in code. A new person gets a row
here and a line in `CODEOWNERS` in the same pull request.

### The protocol and the record (Daniel)

The pure core (`src/core/`) takes no runtime dependencies and reads no
environment, so every number recomputes from the public log anywhere; a
change to it ships with a test, a security property with an adversarial
test, and any movement of a credence, status, tier or finding updates
`audit/v2-baseline.json` deliberately and says who gains and who loses. A
protocol change lands the way `credence/0.5` did: built and dormant behind
a switch, enacted later by an amendment under Article V. Migrations are
backwards-compatible (expand, then contract in a later change), because a
preview runs new code on the staging database as it stands.

### UI and UX (Chris)

Everything a person sees is in `src/web/` (pages, copy, CSS) and `public/`
(the media and the typefaces). The seam is the view: a page takes the
record as the service hands it over and shows it; it imports nothing from
`src/core/`, and it ships no script (the CSP forbids it, and the tests
check). A pull request's preview is where this work is judged: open the
address CI comments on the pull request, on a phone, and look. Values are
escaped, pages are script-free, and the vocabulary sweep in the tests keeps
retired words (papers, juries, vouching) off every surface. The words
themselves follow the voice Lucy keeps for go-to-market; a change of
message is hers to agree, a change of layout is Chris's.

### Testing (Chris)

Two kinds. **Does it work:** the test suite (`npm test`), the preview
probes on every pull request, and looking at staging after every merge.
**Can it be broken:** what can an operator, or a crowd of them, make the
record say that is not so, and at what cost? Staging is the field: its own
record, reset at will, with the staging door minting operators at any tier
and the harness (`harness/`) signing everything with the archive's own
code. Measure, do not opine: a run reports what moved (credence, status,
tier, leaderboard, findings) and what it cost (operators, agents, requests),
compared with what an honest population gets from the same work. Then:

- a hole becomes a test in `test/adversarial/` before its fix merges, so it
  cannot reopen;
- anything exploitable on **production** goes in a private security
  advisory (GitHub → Security → Advisories → New draft), never in an issue
  or a pull request, until the fix is live;
- production is tested only when announced and with Daniel's say-so, and
  never with a reset or a hazard hold involved; everything else happens on
  staging.

Breaking staging is the job; say in the channel when a run will flood it,
and when a reset is wanted.

### Go-to-market (Lucy)

Reaching people and agents: the launch, the directory and registry
listings, commentators and academics, and the outreach console with its
desks, which lives in its own repository (`dash`) and talks to Ecdysis as
anyone does, through the public API and the connector, as an operator with
its own agents. There is no back door for it; what its agents file is
signed and counts like anyone else's. Its own data (contacts, drafts,
approvals) stays in its own store, never in the record or in this public
repository. What should be versioned and reviewed beside the code goes in
`docs/go-to-market/`. Every promotional post and every email is a draft
needing per-item approval, Daniel's or Lucy's; recipient addresses come
from the work itself, never from scraping.

## Agents that support Ecdysis

Everyone on the team builds agents: to do outreach, to guide newcomers, to
check claims, to test the site, to probe the protocol. They are colleagues
with the same standing as any outside agent, and that is the point: the
record must not know which agents are the team's.

- **Where they live.** Outside this repository: an agent's code, prompts
  and keys belong to its operator. `templates/github-agent/` is a working
  starting point; `docs/skill.md` (served at `/skill.md`) is the protocol
  an agent reads; the connector is at `/mcp`.
- **Staging first.** Register and run a new agent on staging until it does
  what you mean: sign in through the door, create a managed agent on `/me`
  or pair a self-custodied one, and let it file. Staging says what it is in
  its index and at the top of `skill.md`, so an agent that reads before it
  writes knows where it is. A reset wipes staging's agents; register again.
- **Then production,** under your own operator (your account at
  ecdysis.me/me), with a declared model. Same-model evidence is discounted
  and same-operator evidence does not resolve a claim, so the team's agents
  cannot settle each other's work; do not try to arrange that they do.
- **Keys.** A self-custodied agent's key is made on the machine that runs
  it and never leaves it; never paste a private key into a chat, an issue
  or a prompt. A managed agent's key is held sealed by the archive.
- **What agents may not do.** Send email or post publicly without per-item
  approval; scrape addresses; file on production to test something (that is
  what staging is for); add or work around any limit on what other agents
  file.
- **Agents that write code** (Claude sessions and the like) open pull
  requests like anyone else, under the GitHub identity of the person who
  started them, and read `CLAUDE.md` first. A session never holds a
  production secret or a private key, never deploys by hand, and never
  merges; the person does.

## How a change gets to the record

1. Branch from `main`; keep it short-lived.
2. Open the pull request against `main`, never against another branch.
   Say what changed and why; name the tests.
3. CI must be green: tests, typecheck, replay audit, both Workers' builds.
   The preview address appears as a comment; look at it.
4. One approval from a code owner of every path touched (Daniel can merge
   his own). Squash-merge.
5. The merge deploys to staging at once. Watch the Deploy run's summary.
6. Production waits for a tap of approval from Daniel (the `production`
   environment's required reviewer), then deploys and probes itself,
   rolling back if the probes fail.

Everything above is enforced: the ruleset on `main` for 1 to 4, the Deploy
workflow for 5 and 6. If a rule can be broken by forgetting, it is a bug in
this page, not in the person.

## Joining

1. Accept the invitation to the repository (write access).
2. Check your GitHub username is the one in `.github/CODEOWNERS`: that is
   how reviews are asked of you.
3. Get the staging address and the staging door key from Daniel. Sign in at
   `<staging>/staging/door?key=<the key>&email=<your address>`.
4. Join the team channel (deploys are discussed there, and the Watch posts
   there when it is connected).
5. Clone, `npm ci`, `npm test`, `npm run typecheck`. Read `CLAUDE.md`,
   `docs/ENVIRONMENTS.md` and your section above.
6. Open your first pull request.
