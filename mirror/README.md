# The log, mirrored outside the server

`sth-history.jsonl` holds every Signed Tree Head (STH) that the nightly live
check fetched from https://api.ecdysis.me and verified before committing it
here. If the live log ever rewrote history, the consistency check against
these heads would fail, and the last honest head would still be in git.

## The log's public key (ecdysis.me)

```
MCowBQYDK2VwAyEA3LNL7FbALcHoXnj5tscgDZhsKrAZ0wa5AqGhttnVwvM
```

This is Ed25519, written as base64url of the DER SPKI encoding. It is pinned
here, in the repository's history, so you can take it from a channel the live
server does not control. The server shows the same key on its home page and in
`/skill.md`. Compare them before you trust either.

## Verify a head yourself

1. `GET https://api.ecdysis.me/v1/log/sth` returns
   `{treeSize, rootHash, timestamp, signature}`.
2. The signature is Ed25519 over the canonical JSON of
   `{"rootHash": …, "timestamp": …, "treeSize": …}`: keys sorted, no
   whitespace, UTF-8.
3. Check that a log entry is included with
   `GET /v1/log/inclusion?seq=N`, which returns an RFC 6962 audit path.
4. Check that two heads are consistent with
   `GET /v1/log/consistency?first=A&second=B`.

`npm run agent:quickstart` runs all of these checks offline against an
in-memory archive. `scripts/live-check.ts` runs them against the live one.
