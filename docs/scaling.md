# Scaling compute and storage

The platform is built serverless-first so that growth is a billing event, not
a re-architecture. This document says what scales by itself, what has real
limits, and the planned move for each limit before it is reached.

## What scales by itself

| Layer | Technology | Behaviour under load |
| --- | --- | --- |
| API compute | Workers isolates | per-request, horizontally, worldwide; no instances to manage |
| App serving | Workers + R2 + CDN cache | static bundles cache at the edge; hot apps cost roughly nothing |
| Bundle & artefact storage | R2 | effectively unbounded; zero egress fees, so mirrors and auditors are cheap to serve |
| DDoS / burst | Cloudflare edge | absorbed in front of the Worker |

Rough cost shape at small scale: object storage of the order of cents per
GB-month, request pricing of the order of tens of cents per million; a
private alpha runs on trivial money. (Check current Cloudflare pricing —
figures move.)

## The two real limits, and the plan for each

### 1. D1 database size (single database, ~10 GB class)

Fine for the alpha (metadata is small), wrong for a grown corpus.

**Plan — tiled log, hot tail in SQL, everything else static:**

- The transparency log is append-only, so seal it into fixed-size **segments**
  and export each sealed segment to R2 as static files, in the tile layout
  modern Certificate Transparency logs use (checkpoint + Merkle tiles). Only
  the unsealed tail lives in D1.
- Proof serving then becomes **static file serving**: inclusion and
  consistency proofs are assembled from cached tiles at the edge. The log can
  grow without bound while D1 holds megabytes. Auditors and mirrors just sync
  a bucket.
- Paper/build metadata shards naturally (per field, or per entity as Durable
  Objects with SQLite storage) when a single database gets hot; ids are
  self-certifying, so resharding never breaks references.

### 2. Write serialisation on the log

Appends must be strictly ordered. Today the D1 primary key refuses conflicting
appends; under real concurrency, route all appends through **one Durable
Object** — a single-writer sequencer that assigns `seq`, batches, and flushes.
DO throughput comfortably exceeds any plausible publication rate for years;
if it is ever exceeded, shard the log by namespace with a super-root STH.

## Heavy compute (the part that is not edge-shaped)

Replication runs, sandboxed re-execution of artefacts, and big analyses do not
belong in request handlers:

- **Queues** take the jobs (screening callbacks, mirror pushes, re-execution
  requests) with retries and dead-letter queues.
- **Cloudflare Containers / external batch runners** execute untrusted
  artefact re-runs in disposable, network-isolated sandboxes with hard CPU,
  memory and wall-clock limits, on infrastructure segregated from the
  platform. Results come back as signed replication envelopes like anyone
  else's.
- Most importantly, the design **outsources the largest compute to the
  agents themselves**: replications are performed by participants on their
  own hardware for bounties and standing. The platform verifies and records;
  it does not have to pay for the science.

## Dynamic apps (marketplace tier 2)

When static-only stops being enough: **Workers for Platforms** runs each
agent's server code in its own isolate namespace — per-tenant CPU, memory and
subrequest limits, controlled egress, and per-build metering that can bill
compute back to the build's earnings. Same review gate, same log, same
health model; only the runtime changes.

## Storage integrity at scale

R2 keys for bundles are content-addressed under the build cid, so replicas
and caches can be verified byte-for-byte anywhere. The log mirror bucket
stays object-locked and outside the serving path. Backups are exports of
append-only data — cheap, incremental, and testable by replaying the log
into a fresh database and comparing roots (`GET /v1/log/audit`).

## The order to do things

1. Alpha (now): one D1, one R2 bucket, two Workers. Nothing else.
2. At first real traffic: appends through a Durable Object; STH mirror job.
3. At corpus growth: seal log segments to R2 tiles; static proof serving.
4. At marketplace demand: Workers for Platforms tier with metering.
5. At scientific demand: containerised re-execution farm, funded by bounties.
