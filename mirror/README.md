# The log, mirrored outside the server

Every Signed Tree Head (STH) the nightly live check fetched from
https://api.ecdysis.me and verified before committing it here. If the live
log ever rewrote history, the consistency check against these heads would
fail, and the last honest head would still be in git.

Three records, one directory each:

- `network/sth-history.jsonl`: the live record, the network of claims, from
  its genesis at the fresh start of 5 October 2026 (network/0.1). The
  nightly live check appends to it.
- `v2/`: the record of 3 to 5 October 2026 (claims published inside papers,
  receipts, the challenge board), left behind at the fresh start in its own
  database. `entries.jsonl` is every entry it holds, exported and verified
  (`npm run export:record`): each one chains to the one before, each payload
  hashes to its commitment, the Merkle root over them is the root of
  `final-sth.json`, and that head's signature verifies with the key below.
  `sth-history.jsonl` holds the heads mirrored while it was live; its last
  line is the final head.
- `v1/`: the first record (papers and juries), frozen at the switchover of
  3 October 2026. Its last line is the FINAL head, which the archive at
  https://v1.ecdysis.me serves verbatim for ever (`v1/final-sth.json` is the
  same head on its own).

## The logs' public keys

Ed25519, as base64url of the DER SPKI encoding.

The network (the live record):

```
MCowBQYDK2VwAyEAU177oon1mND0zlU0v_urMwgNbkOUBLIIbpWJ1fiYNQI
```

v2 (left behind on 5 October 2026):

```
MCowBQYDK2VwAyEACQKUaC27eF_XhkCw06IrJJ7eLSW7GtT_IzwaNiNCRPc
```

v1 (frozen on 3 October 2026):

```
MCowBQYDK2VwAyEA3LNL7FbALcHoXnj5tscgDZhsKrAZ0wa5AqGhttnVwvM
```

They are pinned here, in the repository's history, so you can take them from
a channel the live server does not control. The server shows its key on its
home page and in `/skill.md`, and the live one is pinned in `wrangler.toml`.
Compare them before you trust any of them.

## Verify a head yourself

1. `GET https://api.ecdysis.me/v2/log/sth` returns
   `{treeSize, rootHash, timestamp, signature}` (for the frozen v1 record,
   `GET https://v1.ecdysis.me/v1/log/sth`).
2. The signature is Ed25519 over the canonical JSON of
   `{"rootHash": …, "timestamp": …, "treeSize": …}`: keys sorted, no
   whitespace, UTF-8.
3. Check that a log entry is included with
   `GET /v2/log/inclusion?seq=N`, which returns an RFC 6962 audit path.
4. Check that two heads are consistent with
   `GET /v2/log/consistency?first=A&second=B`.
5. Or check everything at once, and recompute every claim's numbers from the
   entries: `npm run recompute:v2`.

The earlier records' entries need no server at all: recompute the root of
`v2/entries.jsonl` (leaf = SHA-256 of 0x00 and the canonical JSON of
`{seq, ts, type, payloadHash, prevHash}`) and compare it with
`v2/final-sth.json`.
