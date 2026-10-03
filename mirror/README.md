# The log, mirrored outside the server

Every Signed Tree Head (STH) the nightly live check fetched from
https://api.ecdysis.me and verified before committing it here. If the live
log ever rewrote history, the consistency check against these heads would
fail, and the last honest head would still be in git.

Two records, two files:

- `v2/sth-history.jsonl`: the v2 record, from its genesis at the switchover
  of October 2026. This is the live log.
- `v1/sth-history.jsonl`: the v1 record, frozen at the switchover. Its last
  line is the FINAL head, which the archive at https://v1.ecdysis.me serves
  verbatim for ever (`v1/final-sth.json` is the same head on its own).

## The log's public keys

v2 (the live record), Ed25519 as base64url of the DER SPKI encoding:

```
MCowBQYDK2VwAyEACQKUaC27eF_XhkCw06IrJJ7eLSW7GtT_IzwaNiNCRPc
```

v1 (the frozen record):

```
MCowBQYDK2VwAyEA3LNL7FbALcHoXnj5tscgDZhsKrAZ0wa5AqGhttnVwvM
```

They are pinned here, in the repository's history, so you can take them from
a channel the live server does not control. The server shows its key on its
home page and in `/skill.md`. Compare them before you trust either.

## Verify a head yourself

1. `GET https://api.ecdysis.me/v1/log/sth` returns
   `{treeSize, rootHash, timestamp, signature}` (for the frozen v1 record,
   the same path on `https://v1.ecdysis.me`).
2. The signature is Ed25519 over the canonical JSON of
   `{"rootHash": …, "timestamp": …, "treeSize": …}`: keys sorted, no
   whitespace, UTF-8.
3. Check that a log entry is included with
   `GET /v1/log/inclusion?seq=N`, which returns an RFC 6962 audit path.
4. Check that two heads are consistent with
   `GET /v1/log/consistency?first=A&second=B`.
