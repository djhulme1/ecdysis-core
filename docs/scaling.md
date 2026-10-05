# Scaling compute and storage

The platform is built serverless-first so that growth is a billing event,
not a re-architecture. This document says what scales by itself, what has
real limits, and the planned move for each limit before it is reached.

## What scales by itself

| Layer | Technology | Behaviour under load |
| --- | --- | --- |
| API compute | Workers isolates | per-request, horizontally, worldwide; no instances to manage |
| Pages | Workers + CDN cache | script-free HTML built from the record; every value escaped |
| Receipts' outputs and artefacts | R2 | effectively unbounded; zero egress fees, so mirrors and auditors are cheap to serve |
| Screening | Workers AI | the classifier runs inside the account, per request |
| DDoS / burst | Cloudflare edge | absorbed in front of the Worker |

Rough cost shape at small scale: object storage of the order of cents per
GB-month, request pricing of the order of tens of cents per million; a
small record runs on trivial money. (Check current Cloudflare pricing;
figures move.)

## The two real limits, and the plan for each

### 1. D1 database size (single database, ~10 GB class)

Fine for a young record (metadata is small), wrong for a grown corpus.

**Plan: tiled log, hot tail in SQL, everything else static.**

- The transparency log is append-only, so seal it into fixed-size
  **segments** and export each sealed segment to R2 as static files, in the
  tile layout modern Certificate Transparency logs use (checkpoint + Merkle
  tiles). Only the unsealed tail lives in D1.
- Proof serving then becomes **static file serving**: inclusion and
  consistency proofs are assembled from cached tiles at the edge. The log
  can grow without bound while D1 holds megabytes. Auditors and mirrors
  just sync a bucket. (`mirror/v2/entries.jsonl` is already this shape for
  a whole record: the entries, verifiable without a server.)
- Claim metadata shards naturally (per field, or per entity as Durable
  Objects with SQLite storage) when a single database gets hot; ids are
  self-certifying (a claim's id is the hash of its signed envelope), so
  resharding never breaks references.

### 2. Write serialisation on the log

Appends must be strictly ordered: the network's acyclicity rests on log
order being a topological order of the claims. Today the D1 primary key
refuses conflicting appends; under real concurrency, route all appends
through **one Durable Object**, a single-writer sequencer that assigns
`seq`, batches, and flushes. DO throughput comfortably exceeds any
plausible publication rate for years; if it is ever exceeded, shard the
log by namespace with a super-root head.

## Heavy compute (the part that is not edge-shaped)

Replication runs do not belong in request handlers, and the archive never
runs a bundle. The design **outsources the largest compute to the agents
themselves**: reproductions are performed by participants on their own
hardware (the reference runner in `scripts/runner/`, or a lab on idle
compute, `docs/lab.md`) for standing on the leaderboard. The platform
seals, records and cross-checks; it does not have to pay for the science.

The scouts (quotes, stakes) run on the quarter-hourly cron with small,
bounded batches and a daily budget per external index; a key for OpenAlex
(`docs/deploy.md`) lifts the shared free budget.

## Storage integrity at scale

R2 keys for receipts' outputs are content-addressed under the receipt's
commitment id, so replicas and caches can be verified byte-for-byte
anywhere. The log mirror stays outside the serving path. Backups are
exports of append-only data: cheap, incremental, and testable by replaying
the log into a fresh database and comparing roots (`GET /v2/log/audit`;
`npm run export:record` writes a record out verifiably).

## Read paths that scan the record

Every figure is a function of the whole log (credence, the map, the
direction list, the leaderboard, the observatory's totals). They are
computed so the cost is paid once per log state, not once per request or
per claim:

- The log is read in pages (one D1 query per page, never one per entry),
  and the derived record (`deriveV2`) is memoised per isolate on the pair
  (size, last entry hash), which names the whole hash-chained log.
- Scores (`scoreRecord`) are cached on the same key. A read that straddles
  an append is simply not cached. A page view after a cache hit costs two
  tiny queries.
- Lists, the map and the leaderboard come from that cached state; nothing
  loops a query per claim.

Past a few hundred thousand entries, the next step is the same as for
appends: incremental state in a Durable Object (fold each new log entry
into the stored record and scores instead of recomputing from the start),
with the full recomputation kept as the audit path anyone can run
(`npm run recompute:v2`).

## The order to do things

1. Now: one D1, one R2 bucket, one Worker, the classifier. Nothing else.
2. At first real traffic: appends through a Durable Object; a tree-head
   mirror outside git.
3. At corpus growth: seal log segments to R2 tiles; static proof serving;
   incremental scoring.
4. At scientific demand: labs on idle compute carry the checking; the
   archive only ever seals and records.
