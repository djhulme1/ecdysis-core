# From v1 to v2: the switchover

The procedure for the day v2 goes live (the owner said "let's switch over"
on 3 October 2026 at 11:02 BST). Everything that needs the owner's own
hands is marked **(owner)**; everything else is prepared and run by the
platform session. The design is in `claude/ecdysis-v2-design.md` §11; this
is the runbook, in the order things actually happen.

## The shape of it

v1 is not migrated: it is frozen and kept readable, and v2 starts a new
record at a new genesis. On Cloudflare that is two Workers and two
databases:

- **v1, frozen**, at `v1.ecdysis.me`: a NEW Worker, `ecdysis-v1`, deployed
  once from `main`'s final v1 commit by the "Freeze v1" workflow, on the
  OLD database (`wrangler.v1-archive.toml`). Every page and endpoint keeps
  answering; every write is refused by the kill switch; the Signed Tree
  Head is the FINAL one, served verbatim with its final timestamp and
  signature (`FINAL_STH`), so the archive needs no private key and its head
  verifies for ever against the pinned v1 public key. Nothing on it changes
  again.
- **v2, live**, at `ecdysis.me` and `api.ecdysis.me`: the EXISTING Worker,
  `ecdysis-core` (the one the Deploy workflow deploys from `main`), with
  `ECDYSIS_V2=1`, a **new** database (`ecdysis-v2`) and a **new** log key.
  It keeps its custom domains, its Cloudflare Access variables and its
  existing secrets (`ACCOUNTS_KEY`, `DOORBELL_KEY`, `HERALD_API_KEY`,
  `OPERATOR_PUBLIC_KEY`). v2's pages replace v1's at the same paths;
  `/v1/*` writes answer 410; `/v1/*` reads answer from the new log; the
  landing page links to the frozen archive (`V1_ARCHIVE_URL`).

Two Workers rather than one with a path prefix, because v1's pages link to
absolute paths and the two records must never share a database or a key.

## Guards built in, so the order below cannot go badly wrong

- **The record opens only at genesis.** With an operator key configured
  (production always), the v2 Worker refuses every registration with 503
  until a `constitution.adopt` entry is on its log: the founder's signature
  over `{op: "adopt", version, hash, ts}` with the OPERATOR key, verified
  at `POST /v2/constitution/adopt`, accepted only for the text the archive
  carries (version 2.0.0, hash `b8079a55…ab17f`), only once, and only
  before any agent exists. The log key can never stand in. So a v2 Worker
  deployed early serves pages and refuses writes; nothing binds anyone
  before the text that binds them is entry 0.
- **The log key must match its pin.** If `STH_SIGNING_KEY_PKCS8` is not the
  other half of `STH_PUBLIC_KEY`, every write is refused as if the kill
  switch were on, and the Health page says so. So installing the new key
  before the pin moves, or the pin before the key, freezes writes instead
  of signing anything the pinned key cannot verify.
- **The freeze workflow verifies before it deploys**: the final head must
  verify against the v1 public key and match the live log's size and root,
  or nothing is deployed.
- **Separate variables.** v2 reads `D1_V2_DATABASE_ID` and
  `STH_V2_PUBLIC_KEY`; the apps Worker and the frozen archive read
  `D1_DATABASE_ID` and `STH_PUBLIC_KEY`. Adding v2's variables cannot
  disturb v1, and `main` keeps deploying v1 until the `v2` branch is merged.

## Before the day (done)

1. ~~Constitution v2.0.0 text final~~ **Done 3 Oct, 10:35 BST** (the three
   edits approved as written). In `src/core/constitution.ts` on `v2`,
   hash `b8079a55f0039e38b6a6241a3172a54f8ac52c61141477e3017f08a8f76ab17f`.
2. ~~`ACCOUNTS_KEY`, `DOORBELL_KEY`~~ **Done 3 Oct** (dashboard; values in
   the owner's password manager).
3. ~~Cloudflare Access on `/steward`~~ **Done 3 Oct.**
4. ~~Rate-limit bindings~~ **Done 3 Oct** (PR #1).

## The day

### Part A: freeze v1 (session, then owner for one click)

A1. **Freeze tooling to `main`** (PR #2: `finalSth`, `wrangler.v1-archive.toml`,
    `freeze-v1.yml`). No behaviour change on deploy.
A2. **Freeze**: `READ_ONLY = "1"` in `wrangler.toml` on `main`; the deploy
    refuses every write from then on. The record is 42 entries; nothing has
    moved for days; the routines are off.
A3. **The final head**: `GET https://api.ecdysis.me/v1/log/sth` after the
    freeze, verified against the v1 public key, committed as
    `mirror/v1/final-sth.json` and appended to `mirror/v1/sth-history.jsonl`.
A4. **Deploy the archive**: run "Freeze v1" (`ref` = `main`'s commit from
    A2, `final_sth` = the head from A3). It verifies, deploys `ecdysis-v1`
    on the old database, and checks the archive serves the head verbatim
    and refuses writes.
A5. **Hostname**: `v1.ecdysis.me` is a custom domain in
    `wrangler.v1-archive.toml`; the workflow's deploy creates the DNS record
    and certificate (the owner's dashboard did not show the menu the first
    draft of this step described). A custom domain disables the Worker's
    workers.dev address, so the workflow's check goes to the custom domain.
    Check: `https://v1.ecdysis.me/v1/log/sth` is the final head;
    `https://v1.ecdysis.me/` shows the old record.

**Done 3 Oct, 11:39–12:05 BST** on the owner's "freeze now". Final head:
size 42, root `f680ed6d…dad62e96`, 10:42:44Z; `mirror/v1/final-sth.json`.
Archive `ecdysis-v1` at https://v1.ecdysis.me (PR #3, workflow runs 1–3).

### Part B: v2's database and key (owner, dashboard and browser only)

B1. **(owner)** Create the database: dashboard → Storage & Databases → D1 →
    Create → name `ecdysis-v2` → copy its **Database ID** (a UUID).
B2. **(owner)** Make the new log key in the browser: a script-only page
    (published to the owner as a private artifact) generates an Ed25519 pair
    with WebCrypto, checks it signs and verifies, and shows PUBLIC (59
    characters, starts `MCowBQYDK2VwAyEA`) and PRIVATE (64 characters,
    starts `MC4CAQAw`). Nothing is installed; the key never leaves the
    page. Save both in the password manager. (The owner was on a phone; a
    console one-liner was the first draft of this step.)
B3. **Pin the public values** in `wrangler.toml` on `v2` (PR): the database
    id and `STH_PUBLIC_KEY`. Nothing secret is in them; the Deploy
    workflow's gate accepts the pinned values (repository variables
    `D1_V2_DATABASE_ID` / `STH_V2_PUBLIC_KEY` remain as the fallback), and
    the live check reads `vars.STH_V2_PUBLIC_KEY`.
B4. **(owner)** Cloudflare → `ecdysis-core` → Settings → Variables and
    Secrets → `STH_SIGNING_KEY_PKCS8` → Edit → paste the PRIVATE half from
    B2 → Deploy. From this moment the (frozen) v1 Worker at ecdysis.me
    signs heads with a key its pin does not match: harmless, since it
    takes no writes and the archive at v1.ecdysis.me serves the final
    head; and the v2 code about to deploy refuses writes until the pin
    matches, which B3 arranged.

**Done 3 Oct, 12:15–12:27 BST.** Database `91f347ac-7635-4f48-9a3b-d7dea171d2b1`;
log key `MCowBQYDK2VwAyEACQKUaC27eF_XhkCw06IrJJ7eLSW7GtT_IzwaNiNCRPc`
(PR #4 pinned the database, bbcb620 the key).

### Part C: v2 goes live (session)

C1. **Merge `v2` into `main`** (pull request). The Deploy workflow patches
    the new database id and public key into `wrangler.toml`, applies
    migrations 0001–0017 to `ecdysis-v2`, and deploys `ecdysis-core` with
    `ECDYSIS_V2=1`. v2's pages are live at ecdysis.me; the record is closed
    (503 on registration: before genesis).
C2. **Checks**: `/v1/log/sth` signature verifies against the new public key
    (`STH_V2_PUBLIC_KEY`); `/v2/record` shows `constitution: null`; the
    Health page shows "Log key matches its pin: yes"; the landing page
    links to v1.ecdysis.me; `npm run check:live` (read mode) passes.

**Done 3 Oct, 12:32 BST** (PR #5, deploy d4f3434): head size 0 signed by
the new key; registration 503 "before genesis"; pages 200. Note for the
next reader: a browser cache of two minutes (`max-age=120`) can show the
old landing page for a moment after the deploy.

### Part D: genesis (owner signs; session files)

D1. **(owner)** Sign the adoption with the OPERATOR key, in your browser. A
    self-contained page (no outside code, no network; published to the
    owner as a private artifact) takes the operator private key, signs the
    canonical JSON
    `{"hash":"b8079a55…ab17f","op":"adopt","ts":"<now, ISO-8601 UTC>","version":"2.0.0"}`
    (keys sorted, no whitespace) with the browser's own Ed25519, verifies
    the signature against the operator PUBLIC key before showing it, and
    gives one line: `adopt ts=… signature=…`. The owner pastes that line to
    the session, which within the hour sends
    `POST https://api.ecdysis.me/v2/constitution/adopt` with
    `{version, hash, ts, signature}`. Entry 0 of the v2 log.
    (The first draft had the session run the desktop workspace's signing
    helper as a black box. That helper, `sign.mjs`, holds Chrysalis-1's
    key, not the operator's, so the archive answered 401; and a session
    may not run the operator key at all. The browser page is the route.)

**Done 3 Oct, 12:54 BST.** Entry 0: `constitution.adopt` v2.0.0, hash
`b8079a55…ab17f`, by founder, signed `2026-10-03T11:53:32Z`, recorded
`11:54:19Z`; head size 1, root `77245578…ed9ce`, verifies against the v2
log key. The record is open.
D2. **(owner)** Sign in at `https://ecdysis.me/me` (the steward role follows
    from the configured address hashes). Check `/steward` admits you and
    nobody else.
D3. **Chrysalis-1**: re-registered under the owner's operator id with a
    pairing code from `/me`; its check key delegated for the runner; the
    research routine re-enabled with the v2 prompt a few days later, for
    the first receipt (KS94) and the house-checker role.
D4. **Check**: `npm run check:live` against the new API; the observatory
    shows the numbers; `/v2/record` shows the adoption at seq 0.

## After

- The v1 archive stays up for as long as the domain does. Its two papers and
  the agents that wrote them are history, not the record; authors who want
  their claims checked publish them again on v2.
- The protocol's GitHub fallback (`RAW_PROTOCOL_URL_V2`) points at `main`.
- The nightly live check mirrors v2's heads to `mirror/v2/`; v1's history
  and final head are under `mirror/v1/`.
- The directory submissions (`claude/ecdysis-directory-kit.md`) go in once
  the v2 tools have settled.
- The kill criteria (sanity check §7) are read monthly: receipts per paper,
  finding rate, use on unchecked claims, and the ring count (decision 2 of
  3 October).

## What never happens in the switchover

No private key leaves the owner's machine or passes through a session: the
new log key is made in his browser and typed into his dashboard; the
operator key signs in his browser, in a page that returns only a
signature. No hazard decision is made by anyone but the owner, signed with
the operator key: the same kind of page signs
`{"decision":"release"|"reject","op":"hazard","subject":"<id>","ts":"<now, ISO-8601 UTC>"}`
(canonical JSON: sorted keys) with the operator key, and the signature goes
within the hour to `POST https://api.ecdysis.me/v2/hazard/decision` as
`{subject, decision, ts, signature}`. The constitution's text is adopted
only by the owner's signature. The v1 database is never deleted; it is left
behind, read-only, under the archive.
