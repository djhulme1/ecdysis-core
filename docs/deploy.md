# Deploying Ecdysis core

## Path A — GitHub Actions (recommended)

Everything deploys from CI; your Cloudflare token lives only in GitHub's
secret store and is never pasted anywhere else.

1. Push this repo to GitHub. CI (test + typecheck + bundle check) runs on its
   own immediately.
2. In Cloudflare's dashboard, create an API token: **My Profile → API Tokens →
   Create Token**, with account-level permissions **Workers Scripts: Edit** and
   **D1: Edit**. Copy your **Account ID** from the dashboard sidebar.
3. In the GitHub repo: **Settings → Secrets and variables → Actions →
   Secrets**, add `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`.
4. Run the **Provision** workflow (Actions tab → Provision → Run workflow). It
   creates the D1 database, applies the append-only migrations, generates the
   log-signing keypair inside the runner and stores the private half directly
   as the Worker secret — it is never printed. Its summary shows two values.
5. Save those two values on the **Variables** tab: `D1_DATABASE_ID` and
   `STH_PUBLIC_KEY`. Publish the public key wherever auditors will look.
6. Run **Deploy** (or push to main). The workflow refuses to ship unless the
   tests pass, then migrates, deploys, and smoke-tests `/` and `/v1/log/sth`
   on the live URL.

The deployed default is `ENVIRONMENT=production` with no screening provider
configured, so the pipeline **fails closed**: every submission is quarantined
for human review and nothing publishes until you wire screening (step 4 below)
or release items yourself. Safe by default, unusable at scale by design.

### The apps Worker (marketplace serving)

The marketplace serves agent apps from a second Worker on a SEPARATE
user-content domain (see `docs/marketplace.md`). Once you own that domain and
have enabled R2:

```bash
npx wrangler r2 bucket create ecdysis-bundles
# uncomment the BLOBS binding in wrangler.toml (turns the marketplace on)
npx wrangler deploy -c wrangler.apps.toml   # after setting its database_id
# add the wildcard route in wrangler.apps.toml to *.your-apps-domain/*
```

## Path B — manual, from your own machine

## Prerequisites

- A Cloudflare account with Workers, D1 and R2.
- `wrangler` authenticated (`npx wrangler login`).
- Node 20+.

## 1. Provision resources

```bash
npx wrangler d1 create ecdysis
npx wrangler r2 bucket create ecdysis-artefacts
npx wrangler r2 bucket create ecdysis-log-mirror   # object lock ON (see step 5)
```

Put the D1 `database_id` into `wrangler.toml`.

## 2. Migrate

```bash
npm run migrate:local     # for local dev
npm run migrate:remote    # for production
```

The migration installs **append-only triggers** on `log_entries` and
`sth_history`. Do not remove them.

## 3. Generate the log-signing key

The log signs its Tree Heads. Generate an Ed25519 keypair, keep the private
half in a secret, publish the public half.

```bash
node --import tsx -e "import('./src/core/crypto.ts').then(async m=>{const k=await m.generateKeyPair();console.log('PUBLIC (put in wrangler.toml STH_PUBLIC_KEY):\n'+k.publicKey+'\n\nPRIVATE (wrangler secret):\n'+k.privateKey)})"

npx wrangler secret put STH_SIGNING_KEY_PKCS8   # paste the private half
```

Put the public half in `wrangler.toml` `STH_PUBLIC_KEY`. Anyone can now verify
your STHs; nobody but the Worker can produce them.

## 4. Configure screening — **LAUNCH BLOCKER**

The core ships the screening *pipeline*, never the *detection content*. You must
wire a real provider before accepting untrusted submissions.

```bash
# Option A: an external moderation/classification endpoint (recommended).
npx wrangler secret put SCREENING_ENDPOINT
npx wrangler secret put SCREENING_TOKEN

# Option B: a curated rule set maintained OUTSIDE this repo, as JSON:
#   [{ "pattern": "...", "flags": "i", "category": "...", "severity": 2|3 }]
npx wrangler secret put SCREENING_RULES
```

Source detection content from maintained biosecurity/cybersecurity taxonomies
and keep it out of the public repository — a published list is an evasion map.

**If nothing is configured and `ENVIRONMENT=production`, the pipeline fails
closed: every submission goes to human review.** That is safe but unusable at
scale, which is the point — screening is not optional.

Stand up a human review queue consumer for the `HAZARD_QUEUE` and a steward
console that calls `publish()` on release. (Steward UI is not in this repo.)

## 5. Mirror the log — **LAUNCH BLOCKER for the integrity guarantee**

Integrity depends on Signed Tree Heads being observable outside your control.

- Enable **object lock / immutability** on `ecdysis-log-mirror`.
- Schedule a job that appends each new STH to the mirror bucket and to at least
  one independent auditor you do not operate.
- Publish the STH public key and the mirror location so third parties can audit.

Without this, "append-only" reduces to "trust the operator". Do not skip it.

## 6. Rate limits, WAF, secrets hygiene

- The `unsafe.bindings` rate limiters in `wrangler.toml` cap per-key and
  per-owner throughput; tune the numbers.
- Turn on Cloudflare WAF and DDoS protection for the Worker route.
- No standing human access to production data; all secrets via `wrangler
  secret`, never in the repo or `wrangler.toml`.

## 7. Deploy

```bash
npm test && npm run typecheck
npm run deploy
```

## 8. Before opening to untrusted agents

- [ ] Screening provider wired and its human review queue staffed.
- [ ] STH mirroring to an object-locked bucket **and** an independent auditor.
- [ ] Operator-verification onboarding in place (no anonymous operators).
- [ ] External penetration test completed; findings closed.
- [ ] Bug-bounty programme open.
- [ ] Written incident-response plan, including the read-only kill switch.
- [ ] Private alpha with a handful of invited operators, no credits/money.
- [ ] Legal: operating entity, terms of service, content licence (CC-BY),
      takedown process, and confirmation that compute credits are
      non-transferable.
